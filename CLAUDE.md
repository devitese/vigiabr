# CLAUDE.md

This file is the routing trunk for Claude Code. It contains only behavior rules, guard rails, and pointers. All domain knowledge lives in service-level CLAUDE.md files and skills.

---

## General Behavior

- Execute immediately. Do not ask for confirmation unless there are multiple valid approaches.
- Use `AskUserQuestion` for decisions with multiple valid approaches.
- User restarts services manually — never restart Docker, Airflow, or dev servers on your own.
- Never create files unless absolutely necessary. Always prefer editing existing files.
- Use `TeamCreate` for 2+ independent tasks; direct execution for single tasks.
- Use direct `Glob`/`Grep`/`Read` for exploration, NOT `Task(Explore)`.

## Memory Retrieval (MANDATORY)

On **EVERY** user message, search memory using `mcp__plugin_claude-mem_mcp-search__search` **BEFORE** responding. Convert the user message into a semantic search query. Do not skip this step.

## Session Continuations

When continuing after context compaction, re-establish context by running:
1. `git log --oneline -5` — last 5 commits
2. `git status` — current working tree state

Then resume from where the previous context left off.

## Key Rules

| # | Rule |
|---|------|
| 1 | **ALWAYS FIX ROOT CAUSES, NEVER WORKAROUND** — if something is broken, fix the underlying problem. |
| 2 | **ALWAYS USE CONVENTIONAL COMMITS** — `type(scope): description`. Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`, `revert`. |
| 3 | **AFTER EVERY USER CORRECTION**, ask: "Should I add this as a rule to CLAUDE.md?" If approved, append with `<!-- [evolve] -->` marker. |
| 4 | **WHEN IMPLEMENTATION GOES SIDEWAYS** (2+ failed attempts), STOP. Switch to `EnterPlanMode`. |
| 5 | **NEVER MANUALLY EDIT AUTO-GENERATED FILES** — fix the generator, schema, or config instead. |
| 6 | **ALL PII (CPF) MUST BE SHA-256 HASHED** — never store reversible personal identifiers (LGPD compliance). |
| 7 | **USE `TeamCreate` FOR 2+ INDEPENDENT TASKS** — parallelize work across subagents. |
| 8 | **ONE PR PER WORKSTREAM** — never commit unrelated work to a feature branch. |
| 9 | **EVERY PIPELINE STAGE HAS A MEASUREMENT GATE** — plan=baseline, build=post-impl, ship=pre-ship delta. |
| 10 | **CREATE GITHUB ISSUE BEFORE BRANCH** — create issue first, reference issue number in branch name (e.g., `feat/42-add-sci-endpoint`). |

## Git Workflow (CRITICAL)

- **Always branch from `develop`**, NOT `main`. PRs always target `develop`.
- `main` = production (protected, deploy-only).
- `develop` = integration branch.
- Branch naming: `type/issue-number-short-description` (e.g., `feat/42-sci-endpoint`).
- Merge strategy: squash merge to `develop`, merge commit from `develop` to `main`.
- **Direct push to protected branches is allowed when the user explicitly requests it.** <!-- [evolve] -->

## Automation Architecture (Separation of Concerns)

| Layer | Location | Responsibility | Constraint |
|-------|----------|---------------|------------|
| Commands | `.claude/commands/*.md` | Thin routers | ~15 lines max |
| Skills | `.claude/skills/*/SKILL.md` | Knowledge (workflow steps, examples, expertise) | Read-only domain docs |
| Subagents | `Task` with `team_name` | Executors | Scoped to a single task |
| Tools | `allowed-tools` in frontmatter | Capabilities | Declared per command/skill |

## Slash Commands

| Command | Purpose |
|---------|---------|
| `/plan` | Plan -- explore, approach, write |
| `/build` | Build -- feature, fix, test |
| `/ship` | Ship -- review, respond, debug-ci, fix-ci, git |
| `/report` | Report -- weekly, metrics, compare |
| `/evolve` | Evolve -- status, audit, suggest |
| `/run` | Smart router -- asks what you need |
| `/help` | Command reference |

Shortcuts: `/fix` -> `/build fix`, `/git` -> `/ship git`

---

## Project Overview

VigiaBR is an open-source platform for transparency monitoring of Brazilian public officials. It collects official public data, calculates a **Score de Consistencia (SCI)** (0-1000 index measuring consistency between official records), and presents findings with full audit trails. The project is licensed under AGPL-3.0.

**Core principle**: Never accuse or infer. Only present facts (FATO), metrics (METRICA), and sources (FONTE) with direct links to official data.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Data Collection | Python + Scrapy |
| Pipeline Orchestration | Apache Airflow |
| Graph Database | Neo4j Community (Cypher) |
| Relational Database | PostgreSQL |
| ML / Scoring | scikit-learn + XGBoost |
| NLP (local) | Ollama + Mistral |
| Backend API | FastAPI (Python) |
| Frontend | Next.js + React |
| Graph Visualization | Cytoscape.js |
| CNPJ Local DB | SQLite + DuckDB |
| Infrastructure | Docker + Caddy |
| Monitoring | Grafana + Prometheus |

## Architecture

### Data Pipeline
Scrapy spiders -> Airflow DAGs -> PostgreSQL (tabular) + Neo4j (graph relationships)

### Graph Model (Neo4j)
Key node types: `:Mandatario` (politician), `:Partido`, `:Empresa`, `:BemPatrimonial` (assets), `:Emenda` (amendments), `:ContratoGov`, `:Votacao`, `:ProjetoLei`, `:ProcessoJudicial`, `:Inconsistencia`

Key relationships: `FILIADO_A`, `VOTOU`, `TEM_FAMILIAR`, `CONTRATOU`, `SOCIO_DE`, `RECEBEU_DOACAO`

### SCI Scoring Dimensions
Weights are being determined by statistical analysis and are not yet final.

| Dimension |
|-----------|
| Wealth evolution vs salary |
| Vote correlation with donor sector |
| Familiar company contracts |
| Amendment beneficiary linkage |
| Family office hiring |
| Vote change after donation |

### Data Sources (all public)
- **Camara dos Deputados**: dadosabertos.camara.leg.br (votes, CEAP expenses, bills)
- **Senado Federal**: legis.senado.leg.br/dadosabertos
- **TSE**: dadosabertos.tse.jus.br (wealth declarations, campaign donations)
- **Portal Transparencia/CGU**: portaldatransparencia.gov.br/api (amendments, contracts)
- **Receita Federal CNPJ**: arquivos.receitafederal.gov.br (company partnerships, ~30GB monthly dump)
- **Querido Diario**: queridodiario.ok.org.br (DAS appointments, official gazette)
- **CNJ DataJud**: datajud.cnj.jus.br (public lawsuits)

## Conventions

- Use **conventional commits**: `type(scope): description`. Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `ci`, `build`, `revert`
- Link issue numbers in commit messages
- Always run tests before pushing
- All PII (CPF) must be hashed with SHA-256 — never store reversible personal identifiers
- Language in user-facing content must be strictly neutral and factual (LGPD/LAI compliant)
- The PRD is at `VigiaBR-PRD-v1.0.html` — consult it for detailed specifications
- Create GitHub Issue before creating a branch — reference issue number in branch name

## Phased Rollout

- **MVP (Phase 1)**: Federal Congress only (Camara + Senado) -- pipelines, basic SCI, profiles, inconsistency cards
- **Phase 2**: Interactive graphs, family views, ML scoring, NLP discourse analysis
- **Phase 3**: State deputies, comparison/ranking, public API, PDF exports
- **Phase 4**: Municipal councilors, mobile app
