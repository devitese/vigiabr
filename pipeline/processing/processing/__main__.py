"""CLI entry point: python -m processing {source}

Orchestrates the full pipeline for a single source:
  1. Transform raw JSONL -> domain Pydantic models
  2. Validate (data quality + PII safety check)
  3. Load into PostgreSQL, Neo4j, and/or local DuckDB
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from pydantic import BaseModel

from processing.transformers import TRANSFORMER_REGISTRY, TransformResult
from processing.validators import DataQualityValidator, PIIHasher

logger = logging.getLogger("processing")

VALID_SOURCES = list(TRANSFORMER_REGISTRY.keys())

# Mapping: entity table -> (conflict_columns) for PostgreSQL upsert
_PG_CONFLICT_KEYS: dict[str, list[str]] = {
    "mandatarios": ["id_tse"],
    "partidos": ["sigla"],
    "empresas": ["cnpj"],
    "pessoas_fisicas": ["cpf_hash"],
    "votacoes": ["id_externo"],
    "projetos_lei": ["tipo", "numero", "ano"],
    "emendas": ["numero"],
    "contratos_gov": ["numero"],
    "bens_patrimoniais": ["mandatario_id", "tipo", "ano_eleicao"],
    "processos_judiciais": ["numero_cnj"],
    "inconsistencias": ["tipo", "mandatario_id", "metrica"],
}


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m processing",
        description="VigiaBR processing pipeline — transform, validate, load.",
    )
    parser.add_argument(
        "source",
        choices=VALID_SOURCES,
        help="Data source to process (e.g. camara, senado, tse).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("pipeline/data"),
        help="Base data directory containing raw/{source}/YYYY-MM-DD/ (default: pipeline/data).",
    )
    parser.add_argument(
        "--pg-dsn",
        default=os.environ.get("VIGIABR_PG_URI", ""),
        help="PostgreSQL DSN. Falls back to $VIGIABR_PG_URI env var.",
    )
    parser.add_argument(
        "--neo4j-uri",
        default=os.environ.get("VIGIABR_NEO4J_URI", ""),
        help="Neo4j bolt URI. Falls back to $VIGIABR_NEO4J_URI env var.",
    )
    parser.add_argument(
        "--neo4j-user",
        default=os.environ.get("VIGIABR_NEO4J_USER", "neo4j"),
    )
    parser.add_argument(
        "--neo4j-pass",
        default=os.environ.get("VIGIABR_NEO4J_PASSWORD", ""),
    )
    parser.add_argument(
        "--cnpj-db",
        default=os.environ.get("VIGIABR_CNPJ_DB", "pipeline/data/cnpj_local.duckdb"),
        help="Path to local CNPJ DuckDB file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run transform + validate only, skip loading.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def _transform(source: str, data_dir: Path) -> TransformResult:
    """Run the transformer for the given source."""
    transformer_cls = TRANSFORMER_REGISTRY[source]
    transformer = transformer_cls()

    run_dir = transformer.find_latest_run(data_dir)
    if run_dir is None:
        logger.error("No data found for source '%s' under %s", source, data_dir)
        sys.exit(1)

    logger.info("Processing %s from %s", source, run_dir)

    # Collect all JSONL records from the run directory
    jsonl_files = sorted(run_dir.glob("*.jsonl"))
    if not jsonl_files:
        logger.error("No .jsonl files found in %s", run_dir)
        sys.exit(1)

    def all_records():
        for jf in jsonl_files:
            yield from transformer.read_jsonl(jf)

    result = transformer.transform(all_records())

    logger.info(
        "Transform complete — entities=%d relationships=%d errors=%d",
        result.total_entities,
        result.total_relationships,
        len(result.errors),
    )
    return result


def _validate(result: TransformResult) -> TransformResult:
    """Run data quality and PII checks on transform results."""
    dq = DataQualityValidator()
    pii = PIIHasher()

    for table, records in result.entities.items():
        vr = dq.validate_batch(records)
        if vr.rejected:
            logger.warning(
                "Table %s: %d records rejected (dupes=%d, invalid=%d)",
                table,
                len(vr.rejected),
                vr.stats.duplicate_count,
                vr.stats.invalid_count,
            )
        result.entities[table] = vr.valid

        violations = pii.validate(vr.valid)
        if violations:
            logger.error(
                "PII violations in %s: %d — PIPELINE HALTED for this table",
                table,
                len(violations),
            )
            for v in violations[:5]:
                logger.error("  [%s] field=%s: %s", v.violation_type, v.field_name, v.detail)
            result.entities[table] = []

    return result


def _load(
    result: TransformResult,
    source: str,
    pg_dsn: str,
    neo4j_uri: str,
    neo4j_auth: tuple[str, str],
    cnpj_db: str,
) -> None:
    """Load validated data into persistence stores."""
    # PostgreSQL
    if pg_dsn:
        from processing.loaders import PostgresLoader

        with PostgresLoader(pg_dsn) as pg:
            for table, records in result.entities.items():
                if not records:
                    continue
                conflict = _PG_CONFLICT_KEYS.get(table, [])
                if not conflict:
                    logger.warning("No conflict keys defined for table %s, skipping PG load", table)
                    continue
                pg.upsert_batch(table, records, conflict)
    else:
        logger.warning("No PG DSN provided — skipping PostgreSQL load")

    # Neo4j
    if neo4j_uri:
        _load_neo4j(result, neo4j_uri, neo4j_auth)
    else:
        logger.warning("No Neo4j URI provided — skipping Neo4j load")

    # CNPJ local DB (only for cnpj source)
    if source == "cnpj":
        from processing.loaders import CnpjLocalLoader

        with CnpjLocalLoader(cnpj_db) as local:
            local.create_tables()
            for table, records in result.entities.items():
                if not records:
                    continue
                dicts = [r.model_dump(mode="python") if hasattr(r, "model_dump") else r for r in records]
                if table == "empresas":
                    local.load_empresas(dicts)


# Neo4j node mapping: table_name -> (label, merge_key)
_NEO4J_NODE_MAP: dict[str, tuple[str, str]] = {
    "mandatarios": ("Mandatario", "id_tse"),
    "partidos": ("Partido", "sigla"),
    "empresas": ("Empresa", "cnpj"),
    "pessoas_fisicas": ("PessoaFisica", "cpf_hash"),
    "votacoes": ("Votacao", "id_externo"),
    "projetos_lei": ("ProjetoLei", "numero"),
    "emendas": ("Emenda", "numero"),
    "contratos_gov": ("ContratoGov", "numero"),
    "bens_patrimoniais": ("BemPatrimonial", "tipo"),
    "processos_judiciais": ("ProcessoJudicial", "numero_cnj"),
    "inconsistencias": ("Inconsistencia", "tipo"),
}

# Neo4j relationship mapping: rel_name -> (rel_type, from_label, to_label, from_key, to_key, from_field, to_field)
_NEO4J_REL_MAP: dict[str, tuple[str, str, str, str, str, str, str]] = {
    "mandatario_votos": ("VOTOU", "Mandatario", "Votacao", "id_tse", "id_externo",
                         "mandatario_id_externo", "votacao_id_externo"),
}


def _load_neo4j(
    result: TransformResult,
    neo4j_uri: str,
    neo4j_auth: tuple[str, str],
) -> None:
    """Load entities as nodes and relationships into Neo4j."""
    from processing.loaders import Neo4jLoader

    with Neo4jLoader(neo4j_uri, neo4j_auth) as neo4j:
        # 1. Merge entity nodes
        for table, records in result.entities.items():
            if not records:
                continue
            mapping = _NEO4J_NODE_MAP.get(table)
            if not mapping:
                logger.debug("No Neo4j mapping for table %s, skipping", table)
                continue
            label, merge_key = mapping
            dicts = [_to_neo4j_dict(r) for r in records]
            neo4j.merge_nodes(label, dicts, merge_key)

        # 2. Derive FILIADO_A relationships from mandatario partido_sigla
        mandatarios = result.entities.get("mandatarios", [])
        if mandatarios:
            filiacao_records = []
            for m in mandatarios:
                d = _to_neo4j_dict(m)
                sigla = d.get("partido_sigla")
                id_tse = d.get("id_tse")
                if sigla and id_tse:
                    filiacao_records.append({
                        "from_id": id_tse,
                        "to_id": sigla,
                        "props": {},
                    })
            if filiacao_records:
                # Ensure Partido nodes exist
                partidos_seen = {r["to_id"] for r in filiacao_records}
                neo4j.merge_nodes("Partido", [{"sigla": s} for s in partidos_seen], "sigla")
                neo4j.merge_relationships(
                    "FILIADO_A", "Mandatario", "Partido", "id_tse", "sigla",
                    filiacao_records,
                )

        # 3. Merge explicit relationships
        for rel_name, records in result.relationships.items():
            if not records:
                continue
            mapping = _NEO4J_REL_MAP.get(rel_name)
            if not mapping:
                logger.debug("No Neo4j mapping for relationship %s, skipping", rel_name)
                continue
            rel_type, from_label, to_label, from_key, to_key, from_field, to_field = mapping
            rel_records = []
            for r in records:
                d = _to_neo4j_dict(r)
                rel_records.append({
                    "from_id": d.get(from_field),
                    "to_id": d.get(to_field),
                    "props": {k: v for k, v in d.items()
                              if k not in (from_field, to_field) and v is not None},
                })
            neo4j.merge_relationships(
                rel_type, from_label, to_label, from_key, to_key, rel_records,
            )


def _to_neo4j_dict(record: object) -> dict:
    """Convert a Pydantic model or dict to a Neo4j-safe dict."""
    if isinstance(record, BaseModel):
        d = record.model_dump(mode="python")
    elif isinstance(record, dict):
        d = record
    else:
        d = dict(record)
    # Remove None values (Neo4j doesn't like null properties in SET)
    return {k: v for k, v in d.items() if v is not None}


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)

    logger.info("=== VigiaBR Processing: %s ===", args.source)

    # 1. Transform
    result = _transform(args.source, args.data_dir)

    # 2. Validate
    result = _validate(result)

    # 3. Load
    if args.dry_run:
        logger.info("Dry run — skipping load phase")
        _print_summary(result)
        return

    _load(
        result,
        args.source,
        args.pg_dsn,
        args.neo4j_uri,
        (args.neo4j_user, args.neo4j_pass),
        args.cnpj_db,
    )

    _print_summary(result)
    logger.info("=== Done ===")


def _print_summary(result: TransformResult) -> None:
    """Print a summary of the processing run."""
    logger.info("--- Summary ---")
    for table, records in result.entities.items():
        logger.info("  %s: %d records", table, len(records))
    for rel, records in result.relationships.items():
        logger.info("  [rel] %s: %d records", rel, len(records))
    if result.errors:
        logger.warning("  errors: %d", len(result.errors))


if __name__ == "__main__":
    main()
