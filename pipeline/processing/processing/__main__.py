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
import unicodedata
from decimal import Decimal
from pathlib import Path
from typing import Any

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
# NOTE: bens_patrimoniais excluded — "tipo" is not unique; handled by _load_bens_neo4j
# with a composite key.
_NEO4J_NODE_MAP: dict[str, tuple[str, str]] = {
    "mandatarios": ("Mandatario", "id_tse"),
    "partidos": ("Partido", "sigla"),
    "empresas": ("Empresa", "cnpj"),
    "pessoas_fisicas": ("PessoaFisica", "cpf_hash"),
    "votacoes": ("Votacao", "id_externo"),
    "projetos_lei": ("ProjetoLei", "numero"),
    "emendas": ("Emenda", "numero"),
    "contratos_gov": ("ContratoGov", "numero"),
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
        # 1. Merge entity nodes (bens_patrimoniais handled separately in _load_bens_neo4j)
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

        # 2. Derive FILIADO_A from mandatario partido_sigla
        _load_filiacao_neo4j(result, neo4j)

        # 3. Merge VOTOU via _NEO4J_REL_MAP
        for rel_name, records in result.relationships.items():
            if not records:
                continue
            mapping = _NEO4J_REL_MAP.get(rel_name)
            if not mapping:
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

        # 4. Custom relationship loaders
        _load_doacoes_neo4j(result, neo4j)
        _load_socios_neo4j(result, neo4j)
        _load_empresa_enrichments_neo4j(result, neo4j)
        _load_processo_partes_neo4j(result, neo4j)
        _load_ceis_flags_neo4j(result, neo4j)
        _load_contratacoes_neo4j(result, neo4j)
        _load_bens_neo4j(result, neo4j)
        _load_emenda_autoria_neo4j(result, neo4j)
        _load_contrato_empresa_neo4j(result, neo4j)


# -------------------------------------------------------------------- #
# Individual Neo4j relationship loaders                                  #
# -------------------------------------------------------------------- #


def _load_filiacao_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Derive FILIADO_A relationships from mandatario partido_sigla."""
    mandatarios = result.entities.get("mandatarios", [])
    if not mandatarios:
        return

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
        partidos_seen = {r["to_id"] for r in filiacao_records}
        neo4j.merge_nodes("Partido", [{"sigla": s} for s in partidos_seen], "sigla")
        neo4j.merge_relationships(
            "FILIADO_A", "Mandatario", "Partido", "id_tse", "sigla",
            filiacao_records,
        )


def _load_doacoes_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Load RECEBEU_DOACAO: Mandatario -> PessoaFisica (PF donors only)."""
    doacoes = result.relationships.get("doacoes", [])
    if not doacoes:
        return

    rel_records = []
    pf_stubs: dict[str, dict] = {}  # cpf_hash -> stub node props
    skipped_pj = 0

    for doacao in doacoes:
        d = _to_neo4j_dict(doacao)
        origem = d.get("origem")
        doador_hash = d.get("doador_cpf_cnpj_hash")
        mandatario_id = d.get("mandatario_id_externo")

        if not doador_hash or not mandatario_id:
            continue

        if origem != "PF":
            skipped_pj += 1
            continue

        # Ensure stub PessoaFisica node exists
        if doador_hash not in pf_stubs:
            pf_stubs[doador_hash] = {
                "cpf_hash": doador_hash,
                "nome": d.get("doador_nome", "Desconhecido"),
                "tipo": "Doador",
            }

        props = {}
        for key in ("valor", "data", "eleicao_ano", "origem", "doador_nome"):
            val = d.get(key)
            if val is not None:
                props[key] = float(val) if isinstance(val, Decimal) else val

        rel_records.append({
            "from_id": mandatario_id,
            "to_id": doador_hash,
            "props": props,
        })

    if pf_stubs:
        neo4j.merge_nodes("PessoaFisica", list(pf_stubs.values()), "cpf_hash")

    if rel_records:
        neo4j.merge_relationships(
            "RECEBEU_DOACAO", "Mandatario", "PessoaFisica",
            "id_tse", "cpf_hash", rel_records,
        )

    if skipped_pj:
        logger.info("RECEBEU_DOACAO: skipped %d PJ/Partido/Candidato doacoes (Phase 2)", skipped_pj)


def _load_socios_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Load SOCIO_DE: PessoaFisica -> Empresa (PF socios only)."""
    socios = result.relationships.get("pessoa_empresa_socios", [])
    if not socios:
        return

    rel_records = []
    pf_stubs: dict[str, dict] = {}
    skipped_pj = 0

    for socio in socios:
        d = _to_neo4j_dict(socio)
        cpf_hash = d.get("pessoa_cpf_hash")
        cnpj = d.get("empresa_cnpj")

        if not cnpj:
            continue

        if not cpf_hash:
            # PJ socio (has socio_cnpj_hash) — skip for Phase 2
            skipped_pj += 1
            continue

        if cpf_hash not in pf_stubs:
            pf_stubs[cpf_hash] = {
                "cpf_hash": cpf_hash,
                "nome": d.get("pessoa_nome", "Desconhecido"),
                "tipo": "Socio",
            }

        props = {}
        for key in ("qualificacao", "data_entrada", "percentual_capital"):
            val = d.get(key)
            if val is not None:
                props[key] = float(val) if isinstance(val, Decimal) else val

        rel_records.append({
            "from_id": cpf_hash,
            "to_id": cnpj,
            "props": props,
        })

    if pf_stubs:
        neo4j.merge_nodes("PessoaFisica", list(pf_stubs.values()), "cpf_hash")

    if rel_records:
        neo4j.merge_relationships(
            "SOCIO_DE", "PessoaFisica", "Empresa",
            "cpf_hash", "cnpj", rel_records,
        )

    if skipped_pj:
        logger.info("SOCIO_DE: skipped %d PJ socios (Phase 2)", skipped_pj)


def _load_empresa_enrichments_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Merge additional properties onto Empresa nodes from CNPJ enrichments."""
    enrichments = result.relationships.get("empresa_enrichments", [])
    if not enrichments:
        return

    dicts = []
    for e in enrichments:
        d = _to_neo4j_dict(e)
        # Remap cnpj_basico -> cnpj for merge key alignment with Empresa nodes
        if "cnpj_basico" in d and "cnpj" not in d:
            d["cnpj"] = d.pop("cnpj_basico")
        dicts.append(d)

    neo4j.merge_nodes("Empresa", dicts, "cnpj")
    logger.info("Empresa enrichments: %d records merged", len(dicts))


def _load_processo_partes_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Load PARTE_EM: PessoaFisica -> ProcessoJudicial."""
    partes = result.relationships.get("processo_partes", [])
    if not partes:
        return

    rel_records = []
    pf_stubs: dict[str, dict] = {}

    for parte in partes:
        d = _to_neo4j_dict(parte)
        cpf_hash = d.get("cpf_cnpj_hash")
        numero_cnj = d.get("processo_numero_cnj")

        if not cpf_hash or not numero_cnj:
            continue

        if cpf_hash not in pf_stubs:
            pf_stubs[cpf_hash] = {
                "cpf_hash": cpf_hash,
                "nome": d.get("nome", "Desconhecido"),
                "tipo": "Outro",
            }

        props = {}
        for key in ("tipo_parte", "nome"):
            val = d.get(key)
            if val is not None:
                props[key] = val

        rel_records.append({
            "from_id": cpf_hash,
            "to_id": numero_cnj,
            "props": props,
        })

    if pf_stubs:
        neo4j.merge_nodes("PessoaFisica", list(pf_stubs.values()), "cpf_hash")

    if rel_records:
        neo4j.merge_relationships(
            "PARTE_EM", "PessoaFisica", "ProcessoJudicial",
            "cpf_hash", "numero_cnj", rel_records,
        )


def _load_ceis_flags_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Enrich PessoaFisica nodes with CEIS sanction flags."""
    flags = result.relationships.get("ceis_flags", [])
    if not flags:
        return

    enrichments = []
    for flag in flags:
        d = _to_neo4j_dict(flag)
        cpf_hash = d.get("cpf_cnpj_hash")
        if not cpf_hash:
            continue

        node = {
            "cpf_hash": cpf_hash,
            "nome": d.get("nome", "Desconhecido"),
            "tipo": "Outro",
            "ceis_sancionada": True,
            "ceis_tipo_sancao": d.get("tipo_sancao"),
            "ceis_orgao_sancionador": d.get("orgao_sancionador"),
        }
        enrichments.append({k: v for k, v in node.items() if v is not None})

    if enrichments:
        neo4j.merge_nodes("PessoaFisica", enrichments, "cpf_hash")
        logger.info("CEIS flags: enriched %d PessoaFisica nodes", len(enrichments))


def _load_contratacoes_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Load mandatario hiring records (deferred — no mandatario_id available)."""
    contratacoes = result.relationships.get("mandatario_contratacoes", [])
    if not contratacoes:
        return

    # Phase 2: requires orgao name parsing to resolve which mandatario hired.
    # PessoaFisica nodes are already created via entity merge.
    logger.info(
        "CONTRATOU: %d contratacao records found but mandatario resolution "
        "not yet implemented (Phase 2), skipping Neo4j relationship creation",
        len(contratacoes),
    )


def _load_bens_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Load BemPatrimonial nodes with composite key + DECLAROU relationships."""
    bens = result.entities.get("bens_patrimoniais", [])
    if not bens:
        return

    node_dicts = []
    rel_records = []

    for bem in bens:
        d = _to_neo4j_dict(bem)
        mandatario_id = d.get("mandatario_id_externo")
        tipo = d.get("tipo", "")
        ano = d.get("ano_eleicao", "")

        if not mandatario_id:
            continue

        # Generate composite merge key
        bem_id = f"{mandatario_id}_{tipo}_{ano}"

        node = {
            "bem_id": bem_id,
            "tipo": tipo,
            "descricao": d.get("descricao"),
            "ano_eleicao": ano,
        }
        valor = d.get("valor_declarado")
        if valor is not None:
            node["valor_declarado"] = float(valor) if isinstance(valor, Decimal) else valor
        node_dicts.append({k: v for k, v in node.items() if v is not None})

        rel_records.append({
            "from_id": mandatario_id,
            "to_id": bem_id,
            "props": {},
        })

    if node_dicts:
        neo4j.merge_nodes("BemPatrimonial", node_dicts, "bem_id")

    if rel_records:
        neo4j.merge_relationships(
            "DECLAROU", "Mandatario", "BemPatrimonial",
            "id_tse", "bem_id", rel_records,
        )


def _normalize_name(name: str) -> str:
    """Normalize a name for matching: uppercase, strip accents, strip whitespace."""
    name = name.upper().strip()
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _load_emenda_autoria_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Load AUTORIZOU: Mandatario -> Emenda (name-based resolution)."""
    autorias = result.relationships.get("emenda_autorias", [])
    if not autorias:
        return

    # Build nome -> id_tse lookup from mandatarios in current result
    mandatarios = result.entities.get("mandatarios", [])
    nome_to_id: dict[str, str] = {}
    for m in mandatarios:
        d = _to_neo4j_dict(m)
        nome = d.get("nome")
        id_tse = d.get("id_tse")
        if nome and id_tse:
            nome_to_id[_normalize_name(nome)] = id_tse

    rel_records = []
    unresolved = 0

    for autoria in autorias:
        d = _to_neo4j_dict(autoria)
        autor_nome = d.get("autor_nome", "")
        emenda_numero = d.get("emenda_numero")

        if not emenda_numero or not autor_nome:
            continue

        normalized = _normalize_name(autor_nome)
        id_tse = nome_to_id.get(normalized)

        if not id_tse:
            unresolved += 1
            continue

        rel_records.append({
            "from_id": id_tse,
            "to_id": emenda_numero,
            "props": {"autor_nome": autor_nome},
        })

    if rel_records:
        neo4j.merge_relationships(
            "AUTORIZOU", "Mandatario", "Emenda",
            "id_tse", "numero", rel_records,
        )

    if unresolved:
        logger.info(
            "AUTORIZOU: %d emenda autorias unresolved (autor not in current mandatarios)",
            unresolved,
        )


def _load_contrato_empresa_neo4j(result: TransformResult, neo4j: Any) -> None:
    """Load CONTRATOU_GOV: ContratoGov -> Empresa."""
    contratos = result.relationships.get("contrato_empresas", [])
    if not contratos:
        return

    rel_records = []
    for contrato in contratos:
        d = _to_neo4j_dict(contrato)
        numero = d.get("contrato_numero")
        cnpj = d.get("empresa_cnpj")

        if not numero or not cnpj:
            continue

        rel_records.append({
            "from_id": numero,
            "to_id": cnpj,
            "props": {},
        })

    if rel_records:
        neo4j.merge_relationships(
            "CONTRATOU_GOV", "ContratoGov", "Empresa",
            "numero", "cnpj", rel_records,
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
