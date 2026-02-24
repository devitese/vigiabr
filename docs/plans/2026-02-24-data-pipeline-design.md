# Data Pipeline Design — 4 Independent Fronts

**Issue:** #1
**Date:** 2026-02-24
**Status:** Approved
**Scope:** MVP (Phase 1) — Federal Congress (Camara + Senado) + supporting data sources

---

## Overview

The VigiaBR data pipeline is split into 4 independent fronts, each in its own git worktree, organized by pipeline phase. A pre-step commits shared contracts to `develop` before forking. Front 1 (schemas) merges first; Fronts 2, 3, 4 merge in any order after.

**Package manager:** uv (workspace monorepo)

---

## Directory Structure

All pipeline code lives under `pipeline/` to isolate it from future app directories (`backend/`, `frontend/`, etc.).

```
vigiabr/
├── pipeline/
│   ├── contracts/                  # PRE-STEP (committed before forking worktrees)
│   │   ├── raw_formats/           # JSON Schema defining spider output formats
│   │   │   ├── camara.schema.json
│   │   │   ├── senado.schema.json
│   │   │   ├── tse.schema.json
│   │   │   ├── transparencia.schema.json
│   │   │   ├── cnpj.schema.json
│   │   │   ├── querido_diario.schema.json
│   │   │   └── cnj.schema.json
│   │   ├── pg_ddl.sql             # Target PostgreSQL table definitions
│   │   ├── neo4j_constraints.cypher
│   │   └── data_flow.md           # Spec: what extraction outputs, what processing expects
│   │
│   ├── schemas/                    # FRONT 1
│   │   ├── alembic/
│   │   │   ├── alembic.ini
│   │   │   ├── env.py
│   │   │   └── versions/
│   │   ├── neo4j/
│   │   │   ├── constraints.cypher
│   │   │   └── indexes.cypher
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── mandatario.py
│   │   │   ├── partido.py
│   │   │   ├── empresa.py
│   │   │   ├── pessoa_fisica.py
│   │   │   ├── votacao.py
│   │   │   ├── projeto_lei.py
│   │   │   ├── emenda.py
│   │   │   ├── contrato_gov.py
│   │   │   ├── bem_patrimonial.py
│   │   │   ├── processo_judicial.py
│   │   │   ├── inconsistencia.py
│   │   │   └── raw/               # Raw extraction output models
│   │   │       ├── camara_raw.py
│   │   │       ├── senado_raw.py
│   │   │       ├── tse_raw.py
│   │   │       ├── transparencia_raw.py
│   │   │       ├── cnpj_raw.py
│   │   │       ├── querido_diario_raw.py
│   │   │       └── cnj_raw.py
│   │   ├── pyproject.toml         # Package: vigiabr-schemas
│   │   └── tests/
│   │
│   ├── extraction/                 # FRONT 2
│   │   ├── scrapy.cfg
│   │   ├── vigiabr_spiders/
│   │   │   ├── settings.py
│   │   │   ├── middlewares.py
│   │   │   ├── pipelines.py       # Write raw JSONL to data/raw/{source}/
│   │   │   └── spiders/
│   │   │       ├── camara_deputados.py
│   │   │       ├── senado_federal.py
│   │   │       ├── tse_patrimonio.py
│   │   │       ├── transparencia_cgu.py
│   │   │       ├── querido_diario.py
│   │   │       └── cnj_datajud.py
│   │   ├── bulk/
│   │   │   ├── cnpj_downloader.py
│   │   │   └── tse_dump_downloader.py
│   │   ├── pyproject.toml
│   │   └── tests/
│   │
│   ├── processing/                 # FRONT 3
│   │   ├── transformers/
│   │   │   ├── base.py
│   │   │   ├── camara.py
│   │   │   ├── senado.py
│   │   │   ├── tse.py
│   │   │   ├── transparencia.py
│   │   │   ├── cnpj.py
│   │   │   ├── querido_diario.py
│   │   │   └── cnj.py
│   │   ├── loaders/
│   │   │   ├── postgres_loader.py
│   │   │   ├── neo4j_loader.py
│   │   │   └── cnpj_local_loader.py  # SQLite/DuckDB
│   │   ├── validators/
│   │   │   ├── data_quality.py
│   │   │   └── pii_hasher.py        # CPF SHA-256 (LGPD)
│   │   ├── __main__.py              # CLI: python -m processing.run {source}
│   │   ├── pyproject.toml
│   │   └── tests/
│   │
│   ├── platform/                   # FRONT 4
│   │   ├── docker/
│   │   │   ├── docker-compose.yml
│   │   │   ├── docker-compose.dev.yml
│   │   │   └── dockerfiles/
│   │   │       ├── Dockerfile.airflow
│   │   │       ├── Dockerfile.spiders
│   │   │       └── Dockerfile.processing
│   │   ├── airflow/
│   │   │   ├── dags/
│   │   │   │   ├── dag_camara.py
│   │   │   │   ├── dag_senado.py
│   │   │   │   ├── dag_tse.py
│   │   │   │   ├── dag_transparencia.py
│   │   │   │   ├── dag_cnpj.py
│   │   │   │   ├── dag_querido_diario.py
│   │   │   │   └── dag_cnj.py
│   │   │   └── plugins/
│   │   ├── monitoring/
│   │   │   ├── grafana/dashboards/
│   │   │   └── prometheus/prometheus.yml
│   │   └── scripts/
│   │       └── setup-dev.sh
│   │
│   ├── data/                       # Gitignored, shared mount point
│   │   └── raw/                   # Spider output: data/raw/{source}/YYYY-MM-DD/*.jsonl
│   │
│   └── pyproject.toml             # Root workspace for pipeline
│
├── CLAUDE.md
└── .gitignore
```

---

## Data Flow

```
[Sources]                    [Front 2: Extraction]           [Front 3: Processing]         [Persistence]

Camara API ──────┐
Senado API ──────┤
TSE dumps ───────┤          Scrapy spiders &          →  data/raw/{source}/    →     Transformers        →  PostgreSQL
CGU API ─────────┤→         bulk downloaders                YYYY-MM-DD/                   Validators (dedup,      Neo4j
CNPJ dump ───────┤          (rate-limited,                  *.jsonl                       PII hash)               SQLite/DuckDB
Querido Diario ──┤           retried)                                                     Loaders (batch          (CNPJ only)
CNJ API ─────────┘                                                                        upsert)

                            [Front 4: Platform]
                            Airflow DAGs orchestrate: extract → process per source
                            Docker Compose runs all services
                            Grafana/Prometheus monitors health
```

### Boundary 1: Extraction → Processing

**Format:** JSONL files at `pipeline/data/raw/{source}/YYYY-MM-DD/*.jsonl`

Each line is a JSON object conforming to `pipeline/contracts/raw_formats/{source}.schema.json`. File-based contract — extraction writes, processing reads. No direct Python imports between them.

### Boundary 2: Processing → Persistence

Processing imports Pydantic models from `vigiabr-schemas` (Front 1) to validate and load into:

- **PostgreSQL** — tabular data (votes, expenses, declarations, contracts)
- **Neo4j** — graph relationships (`:Mandatario`→`:Empresa`, `:SOCIO_DE`, etc.)
- **SQLite/DuckDB** — CNPJ local database (huge dataset, query-optimized locally)

### Boundary 3: Orchestration

Airflow DAGs invoke extraction and processing as **subprocess calls**:

1. `uv run --project pipeline/extraction scrapy crawl {spider_name}`
2. `uv run --project pipeline/processing python -m processing.run {source}`

Front 4 is decoupled — it knows CLI entry points, not internals.

---

## uv Workspace Configuration

`pipeline/pyproject.toml` (workspace root):

```toml
[project]
name = "vigiabr-pipeline"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["schemas", "extraction", "processing"]
```

`pipeline/extraction/pyproject.toml`:

```toml
[project]
name = "vigiabr-extraction"
dependencies = ["vigiabr-schemas", "scrapy>=2.11"]

[tool.uv.sources]
vigiabr-schemas = { workspace = true }
```

`pipeline/processing/pyproject.toml`:

```toml
[project]
name = "vigiabr-processing"
dependencies = ["vigiabr-schemas", "psycopg[binary]>=3.1", "neo4j>=5.0", "duckdb>=1.0"]

[tool.uv.sources]
vigiabr-schemas = { workspace = true }
```

`pipeline/platform/` is NOT a Python package — Docker + Airflow config files only.

---

## Per-Front Scope

### Front 1: `pipeline/schemas/` — Database Schemas & Shared Types

| Deliverable | Detail |
|-------------|--------|
| Alembic migrations | PostgreSQL tables for all PRD entities |
| Neo4j Cypher scripts | Uniqueness constraints + indexes |
| Pydantic models | One model per entity + raw models (JSONL format) |
| PII utilities | `hash_cpf(cpf: str) -> str` — SHA-256 with salt |

Smallest front. ~20-30 files. Merges to `develop` first.

### Front 2: `pipeline/extraction/` — Scrapy Spiders & Bulk Downloaders

| Source | Spider Type | Notes |
|--------|------------|-------|
| Camara dos Deputados | REST API pagination | JSON, paginated by legislatura |
| Senado Federal | REST API pagination | XML/JSON |
| TSE | Bulk CSV download + parse | Per-election dumps |
| Portal Transparencia/CGU | REST API pagination | Emendas, contratos, CEIS |
| Receita Federal CNPJ | Bulk file download | ~85GB compressed, monthly |
| Querido Diario | REST API + text | DOU entries |
| CNJ DataJud | REST API pagination | Public lawsuits |

Key concerns: rate limiting, retry with backoff, `ROBOTSTXT_OBEY`, idempotent re-runs, tests with recorded HTTP fixtures.

### Front 3: `pipeline/processing/` — Transform, Validate, Load

| Component | Responsibility |
|-----------|---------------|
| `transformers/{source}.py` | Map raw JSON → Pydantic models |
| `validators/data_quality.py` | Dedup, null checks, range validation |
| `validators/pii_hasher.py` | SHA-256 hash all CPF fields (LGPD) |
| `loaders/postgres_loader.py` | Batch upsert via `psycopg` with `ON CONFLICT` |
| `loaders/neo4j_loader.py` | Batch `MERGE` via `neo4j` driver |
| `loaders/cnpj_local_loader.py` | CNPJ dump → SQLite/DuckDB |
| `__main__.py` | CLI: `python -m processing.run {source}` |

Key concerns: idempotent loads (upsert), batch sizes for Neo4j, CPF hashing before ANY write.

### Front 4: `pipeline/platform/` — Docker, Airflow, Monitoring

| Component | Responsibility |
|-----------|---------------|
| `docker-compose.yml` | PostgreSQL 16, Neo4j Community 5, Airflow 2.9, Grafana, Prometheus |
| `docker-compose.dev.yml` | Local volumes, debug ports, hot reload |
| `Dockerfile.*` | One per service (airflow, spiders, processing) |
| `dags/dag_{source}.py` | One DAG per source, daily schedule (CNPJ monthly, TSE per-election) |
| `monitoring/` | Grafana dashboards + Prometheus scrape config |
| `scripts/setup-dev.sh` | One-command local dev setup |

Key concerns: DAGs call subprocesses (not imports), health checks, alerting on failures.

---

## Merge Strategy

### Pre-step (before forking worktrees)

Committed to `develop`:

1. `pipeline/contracts/` — JSON Schemas, DDL, data flow spec
2. `pipeline/pyproject.toml` — uv workspace config
3. `.gitignore` — add `pipeline/data/`, `.venv`
4. Empty directory scaffolds with placeholder `pyproject.toml` per front under `pipeline/`

### Parallel Execution

```
Pre-step ──┐
           ├── Worktree 1: pipeline/schemas/     ──── PR #1 merges first ──┐
           ├── Worktree 2: pipeline/extraction/  ──── codes against         ├── rebase on #1 → PR #2
           ├── Worktree 3: pipeline/processing/  ──── contracts/ initially  ├── rebase on #1 → PR #3
           ├── Worktree 4: pipeline/platform/    ──── Docker + Airflow      ├── PR #4 (no rebase needed)
```

Front 1 merges first (smallest). Fronts 2, 3 rebase to pick up `vigiabr-schemas`. Front 4 merges independently.

### Integration Test

After all 4 PRs merge:

1. `docker compose up` (Front 4)
2. Trigger `dag_camara` manually
3. Verify: spider → JSONL → transformer → data in PG + Neo4j
4. Check Grafana dashboard shows the run
