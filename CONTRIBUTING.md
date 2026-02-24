# Contributing to VigiaBR

Thank you for your interest in VigiaBR! This project monitors the consistency of public records for Brazilian elected officials using exclusively official, public data. Every contribution strengthens democratic transparency.

**License**: VigiaBR is licensed under [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). By contributing, you agree that your work will be distributed under this license.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Repository Setup](#repository-setup)
  - [Infrastructure Services](#infrastructure-services)
  - [Running Tests](#running-tests)
  - [Linting](#linting)
- [Project Structure](#project-structure)
- [Git Workflow](#git-workflow)
  - [Branch Strategy](#branch-strategy)
  - [Issue-First Development](#issue-first-development)
  - [Commit Messages](#commit-messages)
  - [Pull Requests](#pull-requests)
- [Coding Standards](#coding-standards)
  - [Python](#python)
  - [Data Privacy (LGPD)](#data-privacy-lgpd)
  - [Editorial Neutrality](#editorial-neutrality)
- [Architecture Overview](#architecture-overview)
  - [Data Pipeline](#data-pipeline)
  - [Workspace Packages](#workspace-packages)
  - [Database Schemas](#database-schemas)
- [Adding a New Spider](#adding-a-new-spider)
- [Adding a New Processing Stage](#adding-a-new-processing-stage)
- [Database Migrations](#database-migrations)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Security Vulnerabilities](#security-vulnerabilities)

---

## Code of Conduct

Be respectful, constructive, and inclusive. We follow the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Harassment, discrimination, and bad-faith discourse will not be tolerated.

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.12 | Runtime for all pipeline code |
| [uv](https://docs.astral.sh/uv/) | latest | Package and workspace manager |
| Docker + Docker Compose | latest | PostgreSQL, Neo4j, Airflow, monitoring |
| Git | >= 2.40 | Version control |

### Repository Setup

```bash
# Clone the repository
git clone https://github.com/devitese/vigiabr.git
cd vigiabr

# Switch to the develop branch (all work starts here)
git checkout develop

# Create the virtual environment and install all workspace packages
cd pipeline
uv sync

# Verify the installation
uv run pytest
```

The `uv sync` command installs all three workspace packages (`schemas`, `extraction`, `processing`) along with their development dependencies in a single virtual environment at `pipeline/.venv`.

### Infrastructure Services

Start the local development stack:

```bash
cd pipeline/platform/docker

# Start all services (PostgreSQL, Neo4j, Airflow, Prometheus, Grafana)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Default development credentials (defined in `docker-compose.dev.yml`):

| Service | URL | User | Password |
|---------|-----|------|----------|
| PostgreSQL | `localhost:5432` | `vigiabr` | `vigiabr` |
| Neo4j Browser | `http://localhost:7474` | `neo4j` | `vigiabr` |
| Airflow | `http://localhost:8080` | `admin` | `admin` |
| Grafana | `http://localhost:3000` | `admin` | `vigiabr` |
| Prometheus | `http://localhost:9090` | — | — |

To stop services:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

Add `-v` to also remove persistent volumes (database data).

### Running Tests

```bash
cd pipeline

# Run all tests across all workspace packages
uv run pytest

# Run tests for a specific package
uv run pytest schemas/tests/
uv run pytest extraction/tests/
uv run pytest processing/tests/

# Run a single test file
uv run pytest extraction/tests/test_camara_deputados.py

# Verbose output
uv run pytest -v
```

### Linting

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting (target: Python 3.12, line length: 100).

```bash
cd pipeline

# Check for lint errors
uv run ruff check .

# Auto-fix fixable issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check formatting without modifying
uv run ruff format --check .
```

---

## Project Structure

```
vigiabr/
├── CLAUDE.md                 # AI assistant configuration
├── CONTRIBUTING.md            # This file
├── VigiaBR-PRD-v1.0.html     # Product Requirements Document
├── docs/
│   └── plans/                # Design & planning documents
├── pipeline/
│   ├── pyproject.toml        # Root workspace definition (uv)
│   ├── uv.lock               # Locked dependencies
│   ├── schemas/              # Database schemas, Pydantic models, shared types
│   │   ├── models/           # SQLAlchemy + Pydantic models
│   │   ├── pii/              # SHA-256 hashing utilities for PII
│   │   ├── alembic/          # PostgreSQL migrations
│   │   └── tests/
│   ├── extraction/           # Scrapy spiders & bulk downloaders
│   │   ├── vigiabr_spiders/  # Scrapy spider modules
│   │   ├── bulk/             # Bulk file downloaders (e.g., CNPJ dump)
│   │   └── tests/
│   ├── processing/           # Transform, validate, load stages
│   │   ├── processing/       # Processing module source
│   │   └── tests/
│   ├── contracts/            # Data contracts (DDL, Cypher constraints, data flow docs)
│   │   ├── pg_ddl.sql        # PostgreSQL DDL
│   │   ├── neo4j_constraints.cypher
│   │   ├── data_flow.md
│   │   └── raw_formats/      # Sample raw data format specifications
│   └── platform/
│       └── docker/           # Docker Compose files & Dockerfiles
└── data/                     # Local pipeline output (gitignored)
```

---

## Git Workflow

### Branch Strategy

```
main (production — protected, deploy-only)
 └── develop (integration branch — all PRs target here)
      ├── feat/42-sci-endpoint
      ├── fix/51-spider-timeout
      └── docs/55-api-reference
```

- **`main`**: Production branch. Only receives merge commits from `develop`. Never commit directly.
- **`develop`**: Integration branch. All feature branches originate here, all PRs target here.
- **Feature branches**: Named `type/issue-number-short-description`.

### Issue-First Development

**Always create a GitHub Issue before starting work.** This ensures:

1. The work is tracked and discoverable.
2. Others can see what you are working on.
3. The branch and PR link back to a clear description.

```bash
# Example workflow
# 1. Create an issue on GitHub (or via CLI)
gh issue create --title "Add TSE wealth declaration spider" --body "..."

# 2. Note the issue number (e.g., #42)

# 3. Create your branch from develop
git checkout develop
git pull origin develop
git checkout -b feat/42-tse-wealth-spider
```

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description

Optional body explaining the "why" behind the change.

Refs #42
```

**Types**: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`, `revert`

**Scopes** (examples): `extraction`, `processing`, `schemas`, `docker`, `ci`

Examples:

```
feat(extraction): add TSE wealth declaration spider

Scrapes dadosabertos.tse.jus.br for yearly asset declarations.
Outputs raw JSON to pipeline/data/tse_bens/.

Refs #42
```

```
fix(processing): handle null CNPJ in company loader

The Receita Federal dump occasionally has blank CNPJ fields
for companies under judicial protection. Skip these rows
instead of raising a validation error.

Fixes #51
```

### Pull Requests

1. **One PR per workstream** — do not mix unrelated changes.
2. **Target `develop`** — never open a PR against `main`.
3. **Squash merge** — PRs are squash-merged into `develop`.
4. **Run tests before pushing** — `uv run pytest` must pass.
5. **Run linter before pushing** — `uv run ruff check .` must be clean.

PR description template:

```markdown
## Summary
- Brief description of what changed and why

## Related Issue
Closes #<issue-number>

## Test Plan
- [ ] New/updated tests pass (`uv run pytest`)
- [ ] Linting passes (`uv run ruff check .`)
- [ ] Manual verification steps (if applicable)

## Screenshots / Logs
(if applicable)
```

---

## Coding Standards

### Python

- **Target version**: Python 3.12+
- **Line length**: 100 characters
- **Linter/Formatter**: Ruff (configured in each package's `pyproject.toml`)
- **Type hints**: Use type annotations for function signatures. Pydantic models enforce runtime validation.
- **Imports**: Ruff handles import sorting. Let it do its job.
- **Build system**: Hatchling for all packages.
- **Dependencies**: Managed via `uv`. Add runtime dependencies to the relevant package's `pyproject.toml` under `[project.dependencies]`. Add dev-only tools to `[dependency-groups.dev]`.

### Data Privacy (LGPD)

VigiaBR complies with Brazil's Lei Geral de Protecao de Dados (LGPD). **This is non-negotiable:**

- **CPF numbers must be SHA-256 hashed** before storage. Use the `pii` module in `pipeline/schemas/` for all hashing.
- **Never store reversible personal identifiers** in any database, log, or output file.
- **Never log PII** — not in Scrapy logs, not in Airflow task logs, not in error messages.
- If you need to debug with real data, hash it first or use synthetic test data.

### Editorial Neutrality

VigiaBR presents facts, never accusations. All user-facing text must follow these rules:

- Use **FATO** (fact), **METRICA** (metric), and **FONTE** (source) framing.
- Always include a direct link to the official data source.
- Never use language that implies guilt, wrongdoing, or intent.
- Never editorialize. If a metric looks suspicious, present the numbers and let readers draw conclusions.

---

## Architecture Overview

### Data Pipeline

```
Scrapy Spiders → Raw JSON/CSV → Airflow DAGs → Transform → Validate → Load
                                                              ↓           ↓
                                                         PostgreSQL    Neo4j
                                                         (tabular)    (graph)
```

1. **Extraction** (`pipeline/extraction/`): Scrapy spiders fetch data from official APIs and portals. Bulk downloaders handle large datasets (e.g., Receita Federal CNPJ dump).
2. **Processing** (`pipeline/processing/`): Transforms raw data into validated Pydantic models, then loads into PostgreSQL (tabular data) and Neo4j (graph relationships).
3. **Schemas** (`pipeline/schemas/`): Shared SQLAlchemy models, Pydantic types, PII hashing utilities, and Alembic migrations.

### Workspace Packages

The `pipeline/` directory is a [uv workspace](https://docs.astral.sh/uv/concepts/workspaces/) with three member packages:

| Package | PyPI Name | Description |
|---------|-----------|-------------|
| `schemas/` | `vigiabr-schemas` | SQLAlchemy models, Pydantic types, Alembic migrations, PII hashing |
| `extraction/` | `vigiabr-extraction` | Scrapy spiders, bulk downloaders |
| `processing/` | `vigiabr-processing` | Transform, validate, load stages |

Both `extraction` and `processing` depend on `schemas` as a workspace dependency.

### Database Schemas

- **PostgreSQL DDL**: `pipeline/contracts/pg_ddl.sql`
- **Neo4j Constraints**: `pipeline/contracts/neo4j_constraints.cypher`
- **Data flow documentation**: `pipeline/contracts/data_flow.md`
- **Alembic migrations**: `pipeline/schemas/alembic/`

---

## Adding a New Spider

1. **Create an issue** describing the data source, endpoints, and expected output format.
2. Check `pipeline/contracts/raw_formats/` for existing format specs. Add one if this is a new data source.
3. Create the spider in `pipeline/extraction/vigiabr_spiders/`:

```python
# pipeline/extraction/vigiabr_spiders/my_source.py
import scrapy
from models.raw import MyRawModel  # Pydantic model from schemas


class MySourceSpider(scrapy.Spider):
    name = "my_source"
    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {"Accept": "application/json"},
    }

    def start_requests(self):
        yield scrapy.Request("https://api.official-source.gov.br/endpoint")

    def parse(self, response):
        data = response.json()
        for item in data["results"]:
            yield MyRawModel(**item).model_dump()
```

4. Add tests in `pipeline/extraction/tests/`.
5. Run `uv run pytest extraction/tests/` and `uv run ruff check extraction/`.

---

## Adding a New Processing Stage

1. Define or update the Pydantic model in `pipeline/schemas/models/`.
2. If the stage writes to PostgreSQL, add or update the SQLAlchemy model and create an Alembic migration.
3. Implement the transform/load logic in `pipeline/processing/processing/`.
4. Add tests in `pipeline/processing/tests/`.
5. Document the data flow in `pipeline/contracts/data_flow.md` if adding a new pipeline path.

---

## Database Migrations

We use [Alembic](https://alembic.sqlalchemy.org/) for PostgreSQL schema migrations:

```bash
cd pipeline/schemas

# Generate a new migration after modifying SQLAlchemy models
uv run alembic -c alembic/alembic.ini revision --autogenerate -m "add wealth_declarations table"

# Apply migrations
uv run alembic -c alembic/alembic.ini upgrade head

# Rollback one migration
uv run alembic -c alembic/alembic.ini downgrade -1
```

For Neo4j constraint changes, update `pipeline/contracts/neo4j_constraints.cypher` and note the changes in your PR.

---

## Reporting Bugs

[Open an issue](https://github.com/devitese/vigiabr/issues/new) with:

- **Title**: Clear, concise description of the problem.
- **Steps to reproduce**: Exact commands, input data, or URLs.
- **Expected behavior**: What should happen.
- **Actual behavior**: What actually happens (include logs/tracebacks).
- **Environment**: OS, Python version, Docker version, relevant service versions.

---

## Suggesting Features

Open an issue with the `enhancement` label. Include:

- **Problem statement**: What user need or gap does this address?
- **Proposed solution**: How you envision it working.
- **Data source**: If it involves new data, link to the official API/portal.
- **Alternatives considered**: Other approaches you thought about.

For larger features, consider writing a design document in `docs/plans/` as part of your proposal.

---

## Security Vulnerabilities

**Do not open a public issue for security vulnerabilities.** Instead, email the maintainers directly. Include:

- Description of the vulnerability.
- Steps to reproduce.
- Potential impact.

We will respond within 48 hours and coordinate a fix before public disclosure.

---

Thank you for contributing to democratic transparency in Brazil.
