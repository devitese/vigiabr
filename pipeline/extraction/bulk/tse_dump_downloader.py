"""TSE election data bulk downloader.

Downloads and parses TSE (Tribunal Superior Eleitoral) open data dumps
for candidate information, declared assets, and campaign finance records.

Usage:
    python -m bulk.tse_dump_downloader --anos 2018,2022
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import tempfile
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele"

DOWNLOAD_URLS = {
    "candidatos": f"{BASE_URL}/consulta_cand/consulta_cand_{{ano}}.zip",
    "bens": f"{BASE_URL}/bem_candidato/bem_candidato_{{ano}}.zip",
    "receitas": (
        f"{BASE_URL}/prestacao_contas/"
        "prestacao_de_contas_eleitorais_candidatos_{ano}.zip"
    ),
}

FEDERAL_CARGOS = {"DEPUTADO FEDERAL", "SENADOR"}

DEFAULT_ANOS = [2018, 2022]

# Default output base relative to pipeline root
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "tse"


class _JSONEncoder(json.JSONEncoder):
    """Handle Decimal serialization."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _parse_decimal(value: str | None) -> float | None:
    """Parse a Brazilian decimal string (comma as decimal separator)."""
    if not value or not value.strip():
        return None
    try:
        cleaned = value.strip().replace(".", "").replace(",", ".")
        return float(Decimal(cleaned))
    except (InvalidOperation, ValueError):
        return None


def _parse_int(value: str | None) -> int | None:
    """Parse an integer string, returning None on failure."""
    if not value or not value.strip():
        return None
    try:
        return int(value.strip())
    except ValueError:
        return None


def _clean(value: str | None) -> str | None:
    """Strip whitespace and return None for empty/sentinel values."""
    if not value:
        return None
    v = value.strip().strip('"')
    if v in ("", "#NULO#", "#NULO", "#NE#", "#NE", "-1"):
        return None
    return v


def parse_candidatos_csv(content: str, ano: int) -> list[dict[str, Any]]:
    """Parse a TSE candidates CSV and return records matching federal cargos."""
    reader = csv.DictReader(StringIO(content), delimiter=";", quotechar='"')
    records: list[dict[str, Any]] = []

    for row in reader:
        cargo = _clean(row.get("DS_CARGO", ""))
        if not cargo or cargo.upper() not in FEDERAL_CARGOS:
            continue

        sequencial = _clean(row.get("SQ_CANDIDATO"))
        nome = _clean(row.get("NM_CANDIDATO"))
        cpf = _clean(row.get("NR_CPF_CANDIDATO"))
        if not sequencial or not nome or not cpf:
            continue

        records.append({
            "_type": "candidato",
            "sequencial": sequencial,
            "nome": nome,
            "cpf": cpf,
            "numero_candidato": _clean(row.get("NR_CANDIDATO")),
            "cargo": cargo.upper(),
            "sigla_partido": _clean(row.get("SG_PARTIDO")),
            "sigla_uf": _clean(row.get("SG_UF", "")),
            "ano_eleicao": _parse_int(row.get("ANO_ELEICAO")) or ano,
            "situacao": _clean(row.get("DS_SITUACAO_CANDIDATURA")),
            "resultado": _clean(row.get("DS_SIT_TOT_TURNO")),
        })

    return records


def parse_bens_csv(
    content: str, ano: int, federal_sequenciais: set[str]
) -> list[dict[str, Any]]:
    """Parse a TSE declared assets CSV."""
    reader = csv.DictReader(StringIO(content), delimiter=";", quotechar='"')
    records: list[dict[str, Any]] = []

    for row in reader:
        seq = _clean(row.get("SQ_CANDIDATO"))
        if not seq or (federal_sequenciais and seq not in federal_sequenciais):
            continue

        valor = _parse_decimal(row.get("VR_BEM_CANDIDATO"))
        tipo_bem = _clean(row.get("DS_TIPO_BEM_CANDIDATO"))
        if valor is None or not tipo_bem:
            continue

        records.append({
            "_type": "bem_declarado",
            "sequencial_candidato": seq,
            "ano_eleicao": _parse_int(row.get("ANO_ELEICAO")) or ano,
            "tipo_bem": tipo_bem,
            "descricao": _clean(row.get("DS_BEM_CANDIDATO")),
            "valor": valor,
        })

    return records


def _classify_donor_type(value: str | None) -> str | None:
    """Map TSE donor origin descriptions to enum values."""
    if not value:
        return None
    v = value.casefold().strip()
    if "fisic" in v or "físic" in v:
        return "PF"
    if "juríd" in v or "jurid" in v:
        return "PJ"
    if "partido" in v:
        return "Partido"
    if "candidato" in v:
        return "Candidato"
    return None


def parse_receitas_csv(
    content: str, ano: int, federal_sequenciais: set[str]
) -> list[dict[str, Any]]:
    """Parse a TSE campaign donations (receitas) CSV."""
    reader = csv.DictReader(StringIO(content), delimiter=";", quotechar='"')
    records: list[dict[str, Any]] = []

    for row in reader:
        seq = _clean(row.get("SQ_CANDIDATO"))
        if not seq or (federal_sequenciais and seq not in federal_sequenciais):
            continue

        valor = _parse_decimal(row.get("VR_RECEITA"))
        nome_doador = _clean(row.get("NM_DOADOR"))
        if valor is None or not nome_doador:
            continue

        records.append({
            "_type": "doacao",
            "sequencial_candidato": seq,
            "ano_eleicao": _parse_int(row.get("ANO_ELEICAO")) or ano,
            "valor": valor,
            "nome_doador": nome_doador,
            "cpf_cnpj_doador": _clean(row.get("NR_CPF_CNPJ_DOADOR")),
            "tipo_doador": _classify_donor_type(row.get("DS_ORIGEM_RECEITA")),
            "data_receita": _clean(row.get("DT_RECEITA")),
            "descricao": _clean(row.get("DS_RECEITA")),
        })

    return records


def parse_despesas_csv(
    content: str, ano: int, federal_sequenciais: set[str]
) -> list[dict[str, Any]]:
    """Parse a TSE campaign expenses (despesas) CSV."""
    reader = csv.DictReader(StringIO(content), delimiter=";", quotechar='"')
    records: list[dict[str, Any]] = []

    for row in reader:
        seq = _clean(row.get("SQ_CANDIDATO"))
        if not seq or (federal_sequenciais and seq not in federal_sequenciais):
            continue

        valor = _parse_decimal(row.get("VR_DESPESA_CONTRATADA"))
        tipo_despesa = _clean(row.get("DS_ORIGEM_DESPESA"))
        if valor is None or not tipo_despesa:
            continue

        records.append({
            "_type": "despesa_campanha",
            "sequencial_candidato": seq,
            "ano_eleicao": _parse_int(row.get("ANO_ELEICAO")) or ano,
            "valor": valor,
            "tipo_despesa": tipo_despesa,
            "nome_fornecedor": _clean(row.get("NM_FORNECEDOR")),
            "cnpj_cpf_fornecedor": _clean(row.get("NR_CPF_CNPJ_FORNECEDOR")),
            "data_despesa": _clean(row.get("DT_DESPESA")),
            "descricao": _clean(row.get("DS_DESPESA")),
        })

    return records


async def download_file(client: httpx.AsyncClient, url: str, dest: Path) -> Path:
    """Download a file with streaming to handle large ZIPs."""
    logger.info("Downloading %s", url)
    async with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            async for chunk in response.aiter_bytes(chunk_size=8192):
                f.write(chunk)
    logger.info("Downloaded %s (%d bytes)", dest.name, dest.stat().st_size)
    return dest


def extract_and_read_csvs(zip_path: Path, extract_dir: Path) -> list[str]:
    """Extract a ZIP and return contents of all CSV files inside."""
    contents: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
        for name in sorted(zf.namelist()):
            if name.lower().endswith(".csv"):
                csv_path = extract_dir / name
                contents.append(csv_path.read_text(encoding="latin-1", errors="replace"))
    return contents


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> int:
    """Append records to a JSONL file. Returns count written."""
    with open(output_path, "a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, cls=_JSONEncoder, ensure_ascii=False) + "\n")
    return len(records)


async def process_year(ano: int, output_dir: Path) -> dict[str, int]:
    """Download and process all TSE data for a given election year."""
    run_date = date.today().isoformat()
    out_dir = output_dir / run_date
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "tse.jsonl"

    counts: dict[str, int] = {
        "candidatos": 0,
        "bens": 0,
        "receitas": 0,
        "despesas": 0,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        with tempfile.TemporaryDirectory(prefix=f"tse_{ano}_") as tmpdir:
            tmp = Path(tmpdir)

            # Step 1: Download and parse candidates first (need sequenciais for filtering)
            cand_url = DOWNLOAD_URLS["candidatos"].format(ano=ano)
            cand_zip = tmp / f"candidatos_{ano}.zip"
            await download_file(client, cand_url, cand_zip)

            cand_extract = tmp / "candidatos"
            cand_extract.mkdir()
            csv_contents = extract_and_read_csvs(cand_zip, cand_extract)

            all_candidatos: list[dict[str, Any]] = []
            for content in csv_contents:
                all_candidatos.extend(parse_candidatos_csv(content, ano))

            counts["candidatos"] = write_jsonl(all_candidatos, output_path)
            federal_seqs = {c["sequencial"] for c in all_candidatos}
            logger.info(
                "Year %d: %d federal candidates extracted", ano, counts["candidatos"]
            )

            # Step 2: Download and parse declared assets
            bens_url = DOWNLOAD_URLS["bens"].format(ano=ano)
            bens_zip = tmp / f"bens_{ano}.zip"
            await download_file(client, bens_url, bens_zip)

            bens_extract = tmp / "bens"
            bens_extract.mkdir()
            csv_contents = extract_and_read_csvs(bens_zip, bens_extract)

            all_bens: list[dict[str, Any]] = []
            for content in csv_contents:
                all_bens.extend(parse_bens_csv(content, ano, federal_seqs))

            counts["bens"] = write_jsonl(all_bens, output_path)
            logger.info("Year %d: %d asset declarations extracted", ano, counts["bens"])

            # Step 3: Download campaign accounts (receitas + despesas)
            receitas_url = DOWNLOAD_URLS["receitas"].format(ano=ano)
            receitas_zip = tmp / f"receitas_{ano}.zip"
            await download_file(client, receitas_url, receitas_zip)

            receitas_extract = tmp / "receitas"
            receitas_extract.mkdir()
            csv_contents = extract_and_read_csvs(receitas_zip, receitas_extract)

            all_receitas: list[dict[str, Any]] = []
            all_despesas: list[dict[str, Any]] = []
            for content in csv_contents:
                # The campaign accounts ZIP may contain both receitas and despesas CSVs
                all_receitas.extend(parse_receitas_csv(content, ano, federal_seqs))
                all_despesas.extend(parse_despesas_csv(content, ano, federal_seqs))

            counts["receitas"] = write_jsonl(all_receitas, output_path)
            counts["despesas"] = write_jsonl(all_despesas, output_path)
            logger.info(
                "Year %d: %d donations, %d expenses extracted",
                ano,
                counts["receitas"],
                counts["despesas"],
            )

    logger.info("Year %d complete. Output: %s", ano, output_path)
    return counts


async def main(anos: list[int], output_dir: Path) -> None:
    """Process all requested election years."""
    for ano in anos:
        logger.info("Processing TSE data for year %d", ano)
        counts = await process_year(ano, output_dir)
        total = sum(counts.values())
        logger.info(
            "Year %d summary: %d total records (%s)",
            ano,
            total,
            ", ".join(f"{k}={v}" for k, v in counts.items()),
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download and parse TSE election data dumps"
    )
    parser.add_argument(
        "--anos",
        type=str,
        default=",".join(str(a) for a in DEFAULT_ANOS),
        help="Comma-separated election years (default: 2018,2022)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for JSONL files",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    anos = [int(a.strip()) for a in args.anos.split(",")]
    asyncio.run(main(anos, Path(args.output_dir)))
