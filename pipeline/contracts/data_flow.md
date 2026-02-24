# Data Flow Specification

## Boundary 1: Extraction → Processing

**Format:** JSONL files at `pipeline/data/raw/{source}/YYYY-MM-DD/*.jsonl`

Each line is a JSON object conforming to `pipeline/contracts/raw_formats/{source}.schema.json`.
File-based contract — extraction writes, processing reads. No direct Python imports between them.

### Sources

| Source | Spider/Downloader | Output Path |
|--------|------------------|-------------|
| camara | `camara_deputados` spider | `data/raw/camara/YYYY-MM-DD/*.jsonl` |
| senado | `senado_federal` spider | `data/raw/senado/YYYY-MM-DD/*.jsonl` |
| tse | `tse_dump_downloader` | `data/raw/tse/YYYY-MM-DD/*.jsonl` |
| transparencia | `transparencia_cgu` spider | `data/raw/transparencia/YYYY-MM-DD/*.jsonl` |
| cnpj | `cnpj_downloader` | `data/raw/cnpj/YYYY-MM-DD/*.jsonl` |
| querido_diario | `querido_diario` spider | `data/raw/querido_diario/YYYY-MM-DD/*.jsonl` |
| cnj | `cnj_datajud` spider | `data/raw/cnj/YYYY-MM-DD/*.jsonl` |

## Boundary 2: Processing → Persistence

Processing imports Pydantic models from `vigiabr-schemas` (Front 1) to validate and load into:

- **PostgreSQL** — tabular data (votes, expenses, declarations, contracts)
- **Neo4j** — graph relationships (`:Mandatario`→`:Empresa`, `:SOCIO_DE`, etc.)
- **SQLite/DuckDB** — CNPJ local database (huge dataset, query-optimized locally)

## Boundary 3: Orchestration

Airflow DAGs invoke extraction and processing as subprocess calls:

1. `uv run --project pipeline/extraction scrapy crawl {spider_name}`
2. `uv run --project pipeline/processing python -m processing.run {source}`

Front 4 (platform) is decoupled — it knows CLI entry points, not internals.
