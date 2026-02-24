# VigiaBR

Open-source transparency monitoring platform for Brazilian public officials. VigiaBR collects publicly available official data, calculates a **Score de Consistencia (SCI)** — a 0–1000 index measuring consistency between official records — and presents findings with full audit trails.

**Core principle:** Never accuse or infer. Only present facts (FATO), metrics (METRICA), and sources (FONTE) with direct links to official data.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Data Sources](#data-sources)
- [SCI Scoring](#sci-scoring)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running the Pipeline](#running-the-pipeline)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

Brazil publishes large volumes of public data about elected officials — wealth declarations, voting records, campaign donations, government contracts, corporate partnerships, and more. This data is spread across dozens of portals with different formats and no cross-referencing.

VigiaBR bridges that gap by:

1. **Extracting** data from 7 official public sources using Scrapy spiders and bulk downloaders
2. **Transforming** raw data into normalized, validated, LGPD-compliant records (all PII hashed with SHA-256)
3. **Loading** into PostgreSQL (tabular queries) and Neo4j (graph relationships)
4. **Scoring** consistency across records using the SCI algorithm
5. **Presenting** findings via a web interface with interactive graph visualizations

---

## Architecture

```
[Official Sources]          [Extraction]              [Processing]              [Persistence]

Camara API ──────┐
Senado API ──────┤
TSE dumps ───────┤          Scrapy spiders    →  data/raw/{source}/   →  Transformers     → PostgreSQL
CGU API ─────────┤→         & bulk               YYYY-MM-DD/             Validators          Neo4j
CNPJ dump ───────┤          downloaders          *.jsonl                 (dedup, PII hash)   SQLite/DuckDB
Querido Diario ──┤                                                       Loaders             (CNPJ)
CNJ API ─────────┘                                                       (batch upsert)

                            [Platform]
                            Airflow DAGs orchestrate: extract → process per source
                            Docker Compose runs all services
                            Grafana + Prometheus monitors health
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Data Collection | Python, Scrapy, httpx |
| Pipeline Orchestration | Apache Airflow |
| Graph Database | Neo4j Community (Cypher) |
| Relational Database | PostgreSQL 16 |
| ML / Scoring | scikit-learn, XGBoost |
| NLP (local) | Ollama, Mistral |
| Backend API | FastAPI |
| Frontend | Next.js, React |
| Graph Visualization | Cytoscape.js |
| CNPJ Local DB | SQLite, DuckDB |
| Infrastructure | Docker, Caddy |
| Monitoring | Grafana, Prometheus |
| Package Manager | uv (workspace monorepo) |

### Graph Model (Neo4j)

Key node types: `:Mandatario` (politician), `:Partido`, `:Empresa`, `:BemPatrimonial` (assets), `:Emenda` (amendments), `:ContratoGov`, `:Votacao`, `:ProjetoLei`, `:ProcessoJudicial`, `:Inconsistencia`

Key relationships: `FILIADO_A`, `VOTOU`, `TEM_FAMILIAR`, `CONTRATOU`, `SOCIO_DE`, `RECEBEU_DOACAO`

---

## Data Sources

All data is publicly available under Brazil's Access to Information Law (LAI).

| Source | Portal | Data |
|--------|--------|------|
| Camara dos Deputados | [dadosabertos.camara.leg.br](https://dadosabertos.camara.leg.br) | Votes, CEAP expenses, bills |
| Senado Federal | [legis.senado.leg.br/dadosabertos](https://legis.senado.leg.br/dadosabertos) | Votes, bills, committees |
| TSE | [dadosabertos.tse.jus.br](https://dadosabertos.tse.jus.br) | Wealth declarations, campaign donations |
| Portal Transparencia (CGU) | [portaldatransparencia.gov.br/api](https://portaldatransparencia.gov.br/api-de-dados) | Amendments, contracts, CEIS |
| Receita Federal CNPJ | [arquivos.receitafederal.gov.br](https://arquivos.receitafederal.gov.br) | Company partnerships (~30GB monthly dump) |
| Querido Diario | [queridodiario.ok.org.br](https://queridodiario.ok.org.br) | DAS appointments, official gazette |
| CNJ DataJud | [datajud.cnj.jus.br](https://datajud.cnj.jus.br) | Public lawsuits |

---

## SCI Scoring

The Score de Consistencia (SCI) is a composite index from 0 to 1000 measuring how consistent a politician's official records are across multiple dimensions.

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Wealth evolution vs salary | 25% | Does declared wealth growth align with known income? |
| Vote correlation with donor sector | 20% | Do voting patterns favor campaign donor industries? |
| Familiar company contracts | 20% | Do family-linked companies receive government contracts? |
| Amendment beneficiary linkage | 15% | Do amendment funds flow to connected entities? |
| Family office hiring | 12% | Are family members hired with public funds? |
| Vote change after donation | 8% | Did voting behavior shift after receiving donations? |

> The SCI does not imply wrongdoing. It surfaces statistical patterns for public scrutiny with full source traceability.

---

## Project Structure

```
vigiabr/
├── pipeline/
│   ├── pyproject.toml              # uv workspace root
│   ├── contracts/                  # Shared data contracts
│   │   ├── raw_formats/            # JSON Schema per source
│   │   ├── pg_ddl.sql              # PostgreSQL table definitions
│   │   ├── neo4j_constraints.cypher
│   │   └── data_flow.md
│   │
│   ├── schemas/                    # Database schemas & shared types
│   │   ├── models/                 # Pydantic models (one per entity)
│   │   ├── alembic/                # PostgreSQL migrations
│   │   ├── neo4j/                  # Cypher constraints & indexes
│   │   └── pii/                    # CPF hashing (SHA-256, LGPD)
│   │
│   ├── extraction/                 # Scrapy spiders & bulk downloaders
│   │   ├── vigiabr_spiders/        # Scrapy project
│   │   │   └── spiders/            # One spider per source
│   │   ├── bulk/                   # CNPJ & TSE bulk downloaders
│   │   └── tests/
│   │
│   ├── processing/                 # Transform, validate, load
│   │   ├── processing/
│   │   │   ├── transformers/       # Raw JSON → Pydantic models
│   │   │   ├── validators/         # Dedup, PII hashing
│   │   │   └── loaders/            # PostgreSQL, Neo4j, DuckDB batch upsert
│   │   └── tests/
│   │
│   └── platform/                   # Infrastructure & orchestration
│       ├── docker/                 # Docker Compose & Dockerfiles
│       ├── airflow/                # DAGs (one per source)
│       ├── monitoring/             # Grafana dashboards, Prometheus config
│       └── scripts/                # Dev setup scripts
│
├── CLAUDE.md
├── README.md
└── .gitignore
```

The pipeline uses a **uv workspace monorepo** with three Python packages:

| Package | Path | Description |
|---------|------|-------------|
| `vigiabr-schemas` | `pipeline/schemas/` | Pydantic models, Alembic migrations, PII utilities |
| `vigiabr-extraction` | `pipeline/extraction/` | Scrapy spiders and bulk downloaders |
| `vigiabr-processing` | `pipeline/processing/` | Transformers, validators, and database loaders |

Data flows through file-based contracts — extraction writes JSONL files to `pipeline/data/raw/`, processing reads them. No direct Python imports between the two.

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (package manager)
- **Docker** and **Docker Compose** (for databases and services)

### Installation

```bash
# Clone the repository
git clone https://github.com/devitese/vigiabr.git
cd vigiabr

# Install all pipeline dependencies (resolves the workspace)
cd pipeline
uv sync

# Start infrastructure services
cd platform/docker
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Run database migrations
uv run --project ../schemas alembic -c ../schemas/alembic/alembic.ini upgrade head

# Apply Neo4j constraints
# (requires Neo4j to be running via Docker Compose)
```

---

## Running the Pipeline

### Extraction — Run Spiders

```bash
# Run a specific spider
uv run --project pipeline/extraction scrapy crawl camara_deputados

# Available spiders:
#   camara_deputados    — Camara dos Deputados REST API
#   senado_federal      — Senado Federal REST API
#   tse_patrimonio      — TSE wealth declarations
#   transparencia_cgu   — Portal Transparencia/CGU
#   querido_diario      — Querido Diario gazette entries
#   cnj_datajud         — CNJ DataJud lawsuits
```

```bash
# Run bulk downloaders
uv run --project pipeline/extraction python -m bulk.cnpj_downloader
uv run --project pipeline/extraction python -m bulk.tse_dump_downloader
```

Spider output is written to `pipeline/data/raw/{source}/YYYY-MM-DD/*.jsonl`.

### Processing — Transform & Load

```bash
# Process a specific source
uv run --project pipeline/processing python -m processing.run camara

# Sources: camara, senado, tse, transparencia, cnpj, querido_diario, cnj
```

### Orchestration — Airflow DAGs

When running via Airflow (Docker Compose), each source has its own DAG that chains extraction and processing steps. Trigger DAGs from the Airflow UI or CLI.

---

## Testing

```bash
# Run all tests across the workspace
cd pipeline
uv run pytest

# Run tests for a specific package
uv run --project schemas pytest
uv run --project extraction pytest
uv run --project processing pytest
```

Extraction tests use recorded HTTP fixtures (no network calls). Processing tests use in-memory databases.

---

## Contributing

1. **Create a GitHub Issue** describing the change
2. **Branch from `develop`** using the naming convention: `type/issue-number-short-description`
   - Example: `feat/42-add-sci-endpoint`
3. **Use conventional commits**: `type(scope): description`
   - Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`, `revert`
4. **Run tests** before pushing
5. **Open a PR targeting `develop`** (never `master` directly)

### Git Workflow

- `master` — production (protected, deploy-only)
- `develop` — integration branch (all PRs target here)
- Merge strategy: squash merge to `develop`, merge commit from `develop` to `master`

### LGPD Compliance

All PII (particularly CPF numbers) **must** be SHA-256 hashed before storage. Never store reversible personal identifiers. See `pipeline/schemas/pii/` for the hashing utility.

---

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 1 (MVP)** | Federal Congress (Camara + Senado) — pipelines, basic SCI, profiles, inconsistency cards | In Progress |
| **Phase 2** | Interactive graphs, family views, ML scoring, NLP discourse analysis | Planned |
| **Phase 3** | State deputies, comparison/ranking, public API, PDF exports | Planned |
| **Phase 4** | Municipal councilors, mobile app | Planned |

---

## License

This project is licensed under the [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html) (AGPL-3.0).

You are free to use, modify, and distribute this software, provided that any modified versions made available over a network also make their source code available under the same license.
