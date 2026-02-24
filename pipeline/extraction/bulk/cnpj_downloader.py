"""Receita Federal CNPJ open data bulk downloader.

Downloads and parses CNPJ company data from Receita Federal's open data portal.
Files are very large (~85GB total), so they are processed one part at a time
with incremental JSONL writes.

Usage:
    python -m bulk.cnpj_downloader --tipos empresas,socios,estabelecimentos
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
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://arquivos.receitafederal.gov.br/dados/cnpj/dados_abertos_cnpj"

FILE_TYPES = {
    "empresas": {"prefix": "Empresas", "parts": 10},
    "socios": {"prefix": "Socios", "parts": 10},
    "estabelecimentos": {"prefix": "Estabelecimentos", "parts": 10},
}

DEFAULT_TIPOS = ["empresas", "socios", "estabelecimentos"]

# Default output base relative to pipeline root
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "cnpj"

# Porte codes from Receita Federal
PORTE_MAP = {
    "00": "NAO_INFORMADO",
    "01": "ME",
    "03": "EPP",
    "05": "DEMAIS",
}


class _JSONEncoder(json.JSONEncoder):
    """Handle Decimal serialization."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _clean(value: str | None) -> str | None:
    """Strip whitespace and return None for empty values."""
    if not value:
        return None
    v = value.strip().strip('"')
    if v in ("", "0"):
        return None
    return v


def _parse_decimal(value: str | None) -> float | None:
    """Parse a Brazilian decimal string (comma as decimal separator)."""
    if not value or not value.strip():
        return None
    try:
        cleaned = value.strip().replace(".", "").replace(",", ".")
        return float(Decimal(cleaned))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: str | None) -> str | None:
    """Parse a date string in YYYYMMDD format to ISO date."""
    v = _clean(value)
    if not v or len(v) != 8 or not v.isdigit() or v == "00000000":
        return None
    try:
        return f"{v[:4]}-{v[4:6]}-{v[6:8]}"
    except (ValueError, IndexError):
        return None


def _parse_tipo_socio(value: str | None) -> int | None:
    """Parse tipo_socio: 1=PJ, 2=PF, 3=Estrangeiro."""
    v = _clean(value)
    if not v:
        return None
    try:
        t = int(v)
        return t if t in (1, 2, 3) else None
    except ValueError:
        return None


def parse_empresas_row(fields: list[str]) -> dict[str, Any] | None:
    """Parse a single row from an Empresas CSV (no header, position-based).

    Columns: cnpj_basico, razao_social, natureza_juridica,
             qualificacao_responsavel, capital_social, porte, ente_federativo
    """
    if len(fields) < 6:
        return None

    cnpj_basico = _clean(fields[0])
    razao_social = _clean(fields[1])
    natureza_juridica = _clean(fields[2])
    if not cnpj_basico or not razao_social or not natureza_juridica:
        return None

    porte_code = _clean(fields[5])
    porte = PORTE_MAP.get(porte_code, None) if porte_code else None

    return {
        "_type": "empresa",
        "cnpj_basico": cnpj_basico,
        "razao_social": razao_social,
        "natureza_juridica": natureza_juridica,
        "qualificacao_responsavel": _clean(fields[3]),
        "capital_social": _parse_decimal(fields[4]),
        "porte": porte,
    }


def parse_socios_row(fields: list[str]) -> dict[str, Any] | None:
    """Parse a single row from a Socios CSV (no header, position-based).

    Columns: cnpj_basico, tipo_socio, nome_socio, cpf_cnpj_socio,
             qualificacao, data_entrada, pais, representante_legal,
             nome_representante, qualificacao_representante, faixa_etaria
    """
    if len(fields) < 8:
        return None

    cnpj_basico = _clean(fields[0])
    tipo_socio = _parse_tipo_socio(fields[1])
    nome_socio = _clean(fields[2])
    if not cnpj_basico or tipo_socio is None or not nome_socio:
        return None

    return {
        "_type": "socio",
        "cnpj_basico": cnpj_basico,
        "tipo_socio": tipo_socio,
        "nome_socio": nome_socio,
        "cpf_cnpj_socio": _clean(fields[3]),
        "qualificacao": _clean(fields[4]),
        "data_entrada": _parse_date(fields[5]),
        "percentual_capital": None,  # Not present in CSV layout
        "representante_legal": _clean(fields[7]),
    }


def parse_estabelecimentos_row(fields: list[str]) -> dict[str, Any] | None:
    """Parse a single row from an Estabelecimentos CSV (no header, position-based).

    Columns: cnpj_basico, cnpj_ordem, cnpj_dv, identificador_matriz,
             nome_fantasia, situacao_cadastral, data_situacao, motivo_situacao,
             nome_cidade_exterior, pais, data_inicio_atividade, cnae_principal,
             cnae_secundario, tipo_logradouro, logradouro, numero, complemento,
             bairro, cep, uf, municipio, ddd1, telefone1, ddd2, telefone2,
             ddd_fax, fax, email, situacao_especial, data_situacao_especial
    """
    if len(fields) < 21:
        return None

    cnpj_basico = _clean(fields[0])
    cnpj_ordem = _clean(fields[1])
    cnpj_dv = _clean(fields[2])
    if not cnpj_basico or not cnpj_ordem or not cnpj_dv:
        return None

    # Parse secondary CNAEs (comma-separated in field 12)
    cnae_secundario_raw = _clean(fields[12])
    cnaes_secundarios = []
    if cnae_secundario_raw:
        cnaes_secundarios = [
            c.strip() for c in cnae_secundario_raw.split(",") if c.strip()
        ]

    # Build logradouro from type + logradouro fields
    tipo_logradouro = _clean(fields[13])
    logradouro_nome = _clean(fields[14])
    logradouro = None
    if tipo_logradouro and logradouro_nome:
        logradouro = f"{tipo_logradouro} {logradouro_nome}"
    elif logradouro_nome:
        logradouro = logradouro_nome

    return {
        "_type": "estabelecimento",
        "cnpj_basico": cnpj_basico,
        "cnpj_ordem": cnpj_ordem,
        "cnpj_dv": cnpj_dv,
        "situacao_cadastral": _clean(fields[5]),
        "data_situacao": _parse_date(fields[6]),
        "cnae_principal": _clean(fields[11]),
        "cnaes_secundarios": cnaes_secundarios,
        "logradouro": logradouro,
        "municipio": _clean(fields[20]),
        "uf": _clean(fields[19]),
        "cep": _clean(fields[18]),
    }


ROW_PARSERS = {
    "empresas": parse_empresas_row,
    "socios": parse_socios_row,
    "estabelecimentos": parse_estabelecimentos_row,
}


async def download_file(client: httpx.AsyncClient, url: str, dest: Path) -> Path:
    """Download a file with streaming for large files."""
    logger.info("Downloading %s", url)
    async with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        total = 0
        with open(dest, "wb") as f:
            async for chunk in response.aiter_bytes(chunk_size=65536):
                f.write(chunk)
                total += len(chunk)
    size_mb = total / (1024 * 1024)
    logger.info("Downloaded %s (%.1f MB)", dest.name, size_mb)
    return dest


def process_csv_file(
    csv_path: Path, tipo: str, output_path: Path
) -> int:
    """Parse a single CSV file and append records to JSONL. Returns count."""
    parser = ROW_PARSERS[tipo]
    count = 0

    with (
        open(csv_path, encoding="latin-1", errors="replace", newline="") as infile,
        open(output_path, "a", encoding="utf-8") as outfile,
    ):
        reader = csv.reader(infile, delimiter=";", quotechar='"')
        for row in reader:
            record = parser(row)
            if record:
                outfile.write(
                    json.dumps(record, cls=_JSONEncoder, ensure_ascii=False) + "\n"
                )
                count += 1

    return count


async def process_part(
    client: httpx.AsyncClient,
    tipo: str,
    part: int,
    output_path: Path,
) -> int:
    """Download one part file, extract, parse, and append to JSONL."""
    prefix = FILE_TYPES[tipo]["prefix"]
    filename = f"{prefix}{part}.zip"
    url = f"{BASE_URL}/{filename}"

    with tempfile.TemporaryDirectory(prefix=f"cnpj_{tipo}_{part}_") as tmpdir:
        tmp = Path(tmpdir)
        zip_path = tmp / filename

        await download_file(client, url, zip_path)

        # Extract
        extract_dir = tmp / "extracted"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Parse all CSV files in the extracted directory
        total = 0
        for csv_file in sorted(extract_dir.glob("*.csv")) + sorted(
            extract_dir.glob("*.CSV")
        ):
            count = process_csv_file(csv_file, tipo, output_path)
            total += count
            logger.info(
                "%s part %d / %s: %d records",
                tipo,
                part,
                csv_file.name,
                count,
            )

        # Also check for files without .csv extension (Receita sometimes omits it)
        for f in sorted(extract_dir.iterdir()):
            if f.suffix.lower() not in (".csv", ".zip") and f.is_file():
                count = process_csv_file(f, tipo, output_path)
                total += count
                if count > 0:
                    logger.info(
                        "%s part %d / %s: %d records",
                        tipo,
                        part,
                        f.name,
                        count,
                    )

    return total


async def process_tipo(tipo: str, output_dir: Path) -> int:
    """Process all parts of a given CNPJ file type."""
    run_date = date.today().isoformat()
    out_dir = output_dir / run_date
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "cnpj.jsonl"

    num_parts = FILE_TYPES[tipo]["parts"]
    total = 0

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        for part in range(num_parts):
            try:
                count = await process_part(client, tipo, part, output_path)
                total += count
                logger.info(
                    "%s: part %d/%d done (%d records, %d total so far)",
                    tipo,
                    part + 1,
                    num_parts,
                    count,
                    total,
                )
            except httpx.HTTPStatusError as e:
                logger.warning(
                    "%s part %d: HTTP %d — skipping", tipo, part, e.response.status_code
                )
            except Exception:
                logger.exception("%s part %d: unexpected error — skipping", tipo, part)

    logger.info("%s complete: %d total records", tipo, total)
    return total


async def main(tipos: list[str], output_dir: Path) -> None:
    """Process all requested CNPJ data types sequentially."""
    for tipo in tipos:
        if tipo not in FILE_TYPES:
            logger.error("Unknown type: %s (valid: %s)", tipo, list(FILE_TYPES.keys()))
            continue
        logger.info("Processing CNPJ %s data", tipo)
        total = await process_tipo(tipo, output_dir)
        logger.info("CNPJ %s: %d total records written", tipo, total)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download and parse Receita Federal CNPJ open data"
    )
    parser.add_argument(
        "--tipos",
        type=str,
        default=",".join(DEFAULT_TIPOS),
        help="Comma-separated data types: empresas,socios,estabelecimentos",
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

    tipos = [t.strip() for t in args.tipos.split(",")]
    asyncio.run(main(tipos, Path(args.output_dir)))
