# Application Layer Design — 4 Independent Fronts

**Issue:** #7
**Date:** 2026-02-24
**Status:** Draft
**Scope:** MVP (Phase 1) — SCI scoring, backend API, frontend, production deploy

---

## Overview

The VigiaBR application layer is split into 4 independent fronts, each in its own git worktree. This phase sits on top of the data pipeline (Issue #1) and delivers the user-facing MVP: SCI scoring, politician profiles, inconsistency cards, and a deployed web application.

Front 1 (scoring) merges first; Fronts 2 & 3 (backend, frontend) merge in any order after; Front 4 (deploy) merges last.

**Package managers:** uv (Python backend/scoring), pnpm (frontend)

---

## Directory Structure

Application code lives alongside `pipeline/` at the repository root, each in its own top-level directory.

```
vigiabr/
├── pipeline/                      # Already exists (data pipeline)
│   ├── schemas/                   # Shared models (vigiabr-schemas)
│   ├── extraction/
│   ├── processing/
│   └── platform/
│
├── scoring/                       # FRONT 1
│   ├── dimensions/
│   │   ├── __init__.py
│   │   ├── base.py               # Abstract base class for dimensions
│   │   ├── patrimonio.py         # Wealth evolution vs salary (25%)
│   │   ├── voto_doador.py        # Vote × donor sector correlation (20%)
│   │   ├── contrato_familiar.py  # Family company contracts (20%)
│   │   ├── emenda_vinculo.py     # Amendment beneficiary linkage (15%)
│   │   ├── gabinete_familiar.py  # Family office hiring (12%)
│   │   └── voto_pos_doacao.py    # Vote change after donation (8%)
│   ├── engine.py                 # SCIEngine — orchestrates all dimensions
│   ├── detector.py               # InconsistencyDetector — creates :Inconsistencia nodes
│   ├── history.py                # ScoreHistory — tracks score changes over time
│   ├── queries/
│   │   ├── neo4j_queries.py      # Cypher queries for graph traversals
│   │   └── pg_queries.py         # SQL queries for tabular aggregations
│   ├── pyproject.toml            # Package: vigiabr-scoring
│   └── tests/
│       ├── test_engine.py
│       ├── test_dimensions.py
│       └── test_detector.py
│
├── backend/                       # FRONT 2
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app factory
│   │   ├── config.py             # Settings (env-based via pydantic-settings)
│   │   ├── dependencies.py       # DB session providers (PG + Neo4j)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── mandatarios.py    # GET /mandatarios, GET /mandatarios/{id}
│   │   │   ├── sci.py            # GET /mandatarios/{id}/sci
│   │   │   ├── inconsistencias.py # GET /mandatarios/{id}/inconsistencias
│   │   │   ├── timeline.py       # GET /mandatarios/{id}/timeline
│   │   │   ├── search.py         # GET /search?q=...
│   │   │   └── health.py         # GET /health, GET /readiness
│   │   ├── services/
│   │   │   ├── mandatario_service.py
│   │   │   ├── sci_service.py
│   │   │   ├── inconsistencia_service.py
│   │   │   ├── timeline_service.py
│   │   │   └── search_service.py
│   │   ├── schemas/              # API response schemas (Pydantic)
│   │   │   ├── __init__.py
│   │   │   ├── mandatario.py
│   │   │   ├── sci.py
│   │   │   ├── inconsistencia.py
│   │   │   ├── timeline.py
│   │   │   └── common.py         # Pagination, error responses
│   │   └── db/
│   │       ├── postgres.py       # AsyncSession factory
│   │       └── neo4j.py          # Neo4j async driver wrapper
│   ├── pyproject.toml            # Package: vigiabr-backend
│   └── tests/
│       ├── conftest.py           # Fixtures: test DB, test client
│       ├── test_mandatarios.py
│       ├── test_sci.py
│       ├── test_inconsistencias.py
│       └── test_search.py
│
├── frontend/                      # FRONT 3
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx        # Root layout (nav, footer)
│   │   │   ├── page.tsx          # Home — search + featured mandatários
│   │   │   ├── mandatario/
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx  # Profile page
│   │   │   │       ├── loading.tsx
│   │   │   │       └── error.tsx
│   │   │   └── sobre/
│   │   │       └── page.tsx      # About — methodology, open-source, legal
│   │   ├── components/
│   │   │   ├── sci-gauge.tsx     # SCI score display (colored band + number)
│   │   │   ├── inconsistency-card.tsx  # FATO / MÉTRICA / FONTE card
│   │   │   ├── timeline.tsx      # Chronological timeline of public acts
│   │   │   ├── patrimony-chart.tsx     # Wealth evolution line chart
│   │   │   ├── search-bar.tsx
│   │   │   ├── mandatario-summary.tsx  # Card for search results
│   │   │   ├── nav.tsx
│   │   │   └── footer.tsx
│   │   ├── lib/
│   │   │   ├── api.ts            # API client (fetch wrapper)
│   │   │   └── types.ts          # TypeScript types matching API schemas
│   │   └── styles/
│   │       └── globals.css
│   └── public/
│       └── favicon.ico
│
├── deploy/                        # FRONT 4
│   ├── docker/
│   │   ├── docker-compose.prod.yml     # Production compose (all services)
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── Dockerfile.scoring
│   ├── caddy/
│   │   └── Caddyfile              # Reverse proxy + auto-HTTPS
│   ├── ci/
│   │   ├── ci.yml                 # GitHub Actions — lint, test, build
│   │   └── deploy.yml             # GitHub Actions — deploy to VPS
│   ├── e2e/
│   │   ├── test_smoke.py          # Smoke tests: API health, frontend loads
│   │   └── test_integration.py    # E2E: search → profile → SCI → inconsistencies
│   └── scripts/
│       ├── deploy.sh              # Production deploy script
│       └── seed-demo.py           # Seed demo data for staging
│
├── CLAUDE.md
└── .gitignore
```

---

## Data Flow

```
[Data Pipeline]                    [Front 1: Scoring]              [Front 2: Backend]            [Front 3: Frontend]

PostgreSQL  ──┐                    SCIEngine reads PG              FastAPI serves data            Next.js renders
Neo4j       ──┤→  Loaded data  →   + Neo4j queries   →  Writes     → REST endpoints    →  Fetch   → Profile pages
              │                    SCI scores +                      /mandatarios                    SCI gauge
              │                    :Inconsistencia                   /sci                            Timeline
              │                    nodes back to DBs                 /inconsistencias                Inconsistency cards
                                                                    /timeline                       Patrimony chart
                                                                    /search

                                   [Front 4: Deploy]
                                   Docker Compose (prod) runs all services
                                   Caddy handles HTTPS + reverse proxy
                                   GitHub Actions runs CI + deploy
```

### Boundary 1: Pipeline → Scoring

Scoring reads directly from PostgreSQL (via SQLAlchemy) and Neo4j (via `neo4j` driver). It imports Pydantic models from `vigiabr-schemas` (pipeline/schemas). Scoring writes results back: `sci_score` field on `mandatarios` table + new rows in `inconsistencias` table + `:Inconsistencia` nodes in Neo4j.

### Boundary 2: Scoring → Backend

Backend reads the same databases. It does NOT import scoring directly — it reads the pre-computed scores and inconsistencies from the DB. The scoring engine runs as a scheduled batch job (Airflow DAG), not on-demand.

### Boundary 3: Backend → Frontend

Frontend communicates with backend exclusively via REST API. No server-side DB access. The API contract is defined by Pydantic response schemas in `backend/app/schemas/`.

### Boundary 4: Orchestration

Scoring runs as an Airflow DAG (added to `pipeline/platform/airflow/dags/dag_scoring.py`) after data ingestion completes. Backend and frontend are long-running services in Docker Compose.

---

## uv / pnpm Configuration

### Python workspace

`scoring/pyproject.toml`:

```toml
[project]
name = "vigiabr-scoring"
requires-python = ">=3.12"
dependencies = [
    "vigiabr-schemas",
    "sqlalchemy>=2.0",
    "psycopg[binary]>=3.1",
    "neo4j>=5.0",
]

[tool.uv.sources]
vigiabr-schemas = { path = "../pipeline/schemas", editable = true }
```

`backend/pyproject.toml`:

```toml
[project]
name = "vigiabr-backend"
requires-python = ">=3.12"
dependencies = [
    "vigiabr-schemas",
    "vigiabr-scoring",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "psycopg[binary]>=3.1",
    "neo4j>=5.0",
    "pydantic-settings>=2.0",
]

[tool.uv.sources]
vigiabr-schemas = { path = "../pipeline/schemas", editable = true }
vigiabr-scoring = { path = "../scoring", editable = true }
```

### Frontend

`frontend/package.json` — standalone Next.js project, no workspace.

`deploy/` is NOT a Python/Node package — infrastructure config only.

---

## Per-Front Scope

### Front 1: `scoring/` — SCI Scoring Engine (Issue #8)

| Deliverable | Detail |
|-------------|--------|
| Dimension calculators | 6 classes (one per SCI dimension), each with `calculate(mandatario_id) → float` |
| SCIEngine | Orchestrates all 6 dimensions, applies weights, returns 0–1000 score |
| InconsistencyDetector | Creates `:Inconsistencia` nodes in PG + Neo4j with FATO/MÉTRICA/FONTE |
| ScoreHistory | Records score snapshots for audit trail |
| Neo4j queries | Cypher queries for graph traversals (family→company→contract paths) |
| PG queries | SQL aggregations (wealth sums, vote counts, donation totals) |
| CLI entry point | `python -m scoring.engine {mandatario_id | --all}` |

**Key concerns:**
- All scores must be deterministic and reproducible (same input → same output)
- Every deduction must produce an `:Inconsistencia` with clear FATO + MÉTRICA + FONTE
- Fixed weights for MVP (no ML yet — that's Phase 2)
- Score = 1000 − sum(deductions), clamped to [0, 1000]

**SCI Dimensions (fixed weights):**

| Dimension | Class | Weight | Max Deduction | Data Sources |
|-----------|-------|--------|---------------|-------------|
| Patrimônio vs renda | `patrimonio.py` | 25% | −250 pts | TSE bens + Portal Transparência salários |
| Voto × setor doador | `voto_doador.py` | 20% | −200 pts | Câmara votos + TSE doações |
| Contrato familiar | `contrato_familiar.py` | 20% | −200 pts | Receita CNPJ + Transparência contratos |
| Emenda × vínculo | `emenda_vinculo.py` | 15% | −150 pts | Transparência emendas + CNPJ |
| Gabinete familiar | `gabinete_familiar.py` | 12% | −120 pts | Câmara/Senado contratações + CPF hash |
| Voto pós-doação | `voto_pos_doacao.py` | 8% | −80 pts | Câmara votos + TSE doações (temporal) |

Smallest front. ~15-20 files. Merges to `develop` first.

### Front 2: `backend/` — FastAPI Backend API (Issue #9)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (DB connectivity) |
| `/readiness` | GET | Readiness probe (all deps ready) |
| `/mandatarios` | GET | List mandatários (paginated, filterable by UF, partido, cargo) |
| `/mandatarios/{id}` | GET | Full mandatário profile |
| `/mandatarios/{id}/sci` | GET | SCI score breakdown (total + per-dimension) |
| `/mandatarios/{id}/inconsistencias` | GET | Inconsistency cards (paginated, sortable) |
| `/mandatarios/{id}/timeline` | GET | Chronological timeline of public acts |
| `/mandatarios/{id}/patrimonio` | GET | Wealth evolution across elections |
| `/search` | GET | Full-text search by name (PG `tsvector`) |

**Key concerns:**
- Async all the way (asyncpg + async Neo4j driver)
- Pagination on all list endpoints (cursor-based preferred)
- Response schemas strictly follow FATO/MÉTRICA/FONTE pattern for inconsistencies
- No write endpoints in MVP (read-only API)
- Rate limiting (slowapi) to prevent abuse
- CORS configured for frontend origin

**Service layer pattern:**
- Routers → Services → DB queries
- Services contain business logic (assembling timeline events from multiple tables)
- DB layer handles raw queries (PG async sessions + Neo4j read transactions)

### Front 3: `frontend/` — Next.js + React Frontend (Issue #10)

| Page/Component | Description |
|----------------|-------------|
| Home (`/`) | Search bar + featured mandatários (highest/lowest SCI) |
| Profile (`/mandatario/[id]`) | Full profile: SCI gauge, timeline, inconsistency cards, patrimony chart |
| About (`/sobre`) | Methodology explanation, legal basis, open-source info |
| `sci-gauge` | Visual SCI score (colored band: red/orange/yellow/green + number) |
| `inconsistency-card` | Card with FATO, MÉTRICA, FONTE sections + source links |
| `timeline` | Chronological event list (votes, expenses, declarations, contracts) |
| `patrimony-chart` | Line chart: declared wealth per election year vs cumulative salary |
| `search-bar` | Debounced autocomplete search |
| `mandatario-summary` | Card for search result lists (name, party, UF, SCI score) |

**Key concerns:**
- Server-side rendering (SSR) for profile pages (SEO — politicians should be indexable)
- Client-side data fetching for interactive components (timeline filters, etc.)
- Responsive design (mobile-first — citizens access on phones)
- Accessibility (WCAG 2.1 AA)
- Neutral, factual language throughout (no emojis, no subjective adjectives)
- All source links open in new tab to official government portals
- Tailwind CSS for styling (consistency, no custom CSS bloat)
- Chart library: Recharts (lightweight, SSR-compatible)

**Design language:**
- Clean, newspaper-like aesthetic (similar to PRD styling)
- Navy + red + gold color palette
- Monospace for data/metrics, serif for body text
- Cards with left border accent for inconsistencies

### Front 4: `deploy/` — Production Deploy & CI/CD (Issue #11)

| Component | Responsibility |
|-----------|---------------|
| `docker-compose.prod.yml` | All services: PG, Neo4j, Airflow, backend, frontend, Caddy, Grafana, Prometheus |
| `Dockerfile.backend` | Multi-stage build for FastAPI (uv + uvicorn) |
| `Dockerfile.frontend` | Multi-stage build for Next.js (pnpm + standalone output) |
| `Dockerfile.scoring` | Reuses backend base + scoring deps |
| `Caddyfile` | Reverse proxy: `vigiabr.com.br → frontend`, `api.vigiabr.com.br → backend` |
| `ci.yml` | GitHub Actions: ruff + mypy (Python), tsc + eslint (TS), pytest, pnpm test |
| `deploy.yml` | GitHub Actions: build images → push → SSH deploy to VPS |
| `e2e/test_smoke.py` | API health + frontend 200 OK |
| `e2e/test_integration.py` | Search → profile → verify SCI + inconsistencies render |
| `seed-demo.py` | Generate realistic demo data for staging environment |

**Key concerns:**
- Zero-downtime deploy (blue-green with Docker Compose profiles)
- Caddy auto-HTTPS (Let's Encrypt)
- Resource limits in compose (the VPS has limited RAM)
- Health checks on all services
- Log aggregation (stdout → Docker → Grafana Loki later)
- Secrets via `.env` file (not committed)

---

## Merge Strategy

### Pre-step (before forking worktrees)

Committed to `develop`:

1. Scoring DAG stub in `pipeline/platform/airflow/dags/dag_scoring.py`
2. Empty directory scaffolds with placeholder `pyproject.toml` / `package.json`
3. `.gitignore` updates for `frontend/node_modules/`, `frontend/.next/`, `.env`

### Parallel Execution

```
Pre-step ──┐
           ├── Worktree 1: scoring/             ──── PR merges first ────────────┐
           ├── Worktree 2: backend/             ──── codes against schemas       ├── rebase on scoring → PR
           ├── Worktree 3: frontend/            ──── codes against API contract  ├── PR (no rebase needed)
           ├── Worktree 4: deploy/              ──── Docker + CI/CD             ├── PR merges last
```

Front 1 merges first (smallest). Front 2 rebases to pick up `vigiabr-scoring`. Front 3 codes against API contract (no Python imports). Front 4 merges last (needs all services to exist).

### Integration Test

After all 4 PRs merge:

1. `docker compose -f deploy/docker/docker-compose.prod.yml up`
2. Verify: backend `/health` returns 200
3. Trigger scoring DAG manually → verify SCI scores written
4. Open frontend → search → profile → verify SCI + inconsistency cards render
5. Check Grafana dashboard shows backend/frontend metrics
