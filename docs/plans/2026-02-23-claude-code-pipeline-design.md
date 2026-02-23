# VigiaBR Claude Code Pipeline Design

**Date**: 2026-02-23
**Source**: Forked and adapted from max (EverythingCode/max) pipeline
**Approach**: Fork & Strip — copy max's battle-tested pipeline, remove CRM/Linear/Railway specifics, adapt for vigiaBR

## Requirements

| Aspect | Decision |
|--------|----------|
| Scope | Full pipeline (hooks, permissions, agents, commands, skills, CI/CD) |
| Issue tracker | GitHub Issues (not Linear) |
| Memory | claude-mem |
| Deployment | TBD |
| Git strategy | develop + main (feature → develop → main) |
| Quality gates | Match max (Python + TypeScript) |

## 1. CLAUDE.md (Routing Trunk)

Rewritten for vigiaBR. Key differences from max:

- GitHub Issues instead of Linear (`gh issue` commands)
- No Supabase/Drizzle — PostgreSQL + Neo4j direct
- No translation keys rule (Portuguese-only for now)
- Added LGPD/PII rules (SHA-256 CPF hashing)
- Branch from `develop`, PRs target `develop`
- Architecture reflects vigiaBR stack (Scrapy, Airflow, FastAPI, Next.js, Neo4j)
- Same automation architecture pattern (commands → skills → subagents)

## 2. Hooks & Settings

### settings.json hooks

| Hook | Script | Purpose | Changes from max |
|------|--------|---------|-----------------|
| SessionStart | `superpowers-session-start.sh` | Inject using-superpowers skill | None |
| PreToolUse (Bash) | `check-conflict-markers.sh` | Block commits with conflict markers | None |
| PreToolUse (Bash) | `ensure-docker-running.sh` | Auto-start Docker | None |
| PostToolUse (Edit\|Write) | `check-python-syntax.sh` | Validate .py after edits | None |
| Stop | Auto-format | Format code on stop | Adapt formatter command |
| Stop | `cleanup-stray-claude-md.sh` | Remove orphaned CLAUDE.md | None |
| Stop | `quality-gate-task.sh` | Type-check + lint gate | Adapt venv paths for vigiaBR |
| SubagentStart | `subagent-context.sh` | Inject project context | Rewrite for vigiaBR domain |

### Permissions

Same deny list as max (destructive git ops, gh deletes, force pushes). Remove `staging` branch references (vigiaBR uses develop + main only).

## 3. Agents

| Agent | Role | Changes from max |
|-------|------|-----------------|
| code-reviewer.md | Plan alignment & quality review | Minimal — generic enough as-is |
| codebase-analyzer.md | /todo, /clean, /deps, /explain, /review | Remove pnpm specifics, add Python equivalents |
| git-operator.md | /commit, /pr, /unfuck, /revert | GitHub Issue linking instead of Linear, remove staging |

## 4. Commands

### Routers

| Command | Sub-commands | Adaptation |
|---------|-------------|-----------|
| `/plan` | explore, approach, write | GitHub Issue gates instead of Linear |
| `/build` | feature, fix, test | Remove eval/max-test/test-auto |
| `/ship` | review, respond, deploy, debug-ci, fix-ci, git | Remove Railway deploy. Deploy TBD |
| `/report` | weekly, metrics, compare | vigiaBR metrics (pipeline coverage, SCI, data freshness) |
| `/evolve` | status, audit, suggest | No change |
| `/run` | Smart meta-router | `#123` instead of `DEA-###` |
| `/help` | Command reference | Updated for vigiaBR commands |

### Shortcuts

- `/fix` → `/build fix`
- `/git` → `/ship git`
- `/measure` → eval impact (placeholder)

### Removed from max

`/contract-check`, `/docker-restart`, `/lint-python`, `/debug-lead`, `/debug-trace`, `/linear`, `/linear-breakdown`, `/railway`

## 5. Skills

### Direct port (22 skills)

exploring-codebase, designing-approaches, documenting-plans, writing-plans, building-features, fixing-bugs, writing-and-running-tests, systematic-debugging, managing-git-operations, reviewing-for-shipping, responding-to-pr-feedback, finishing-a-development-branch, fixing-ci-checks, debugging-ci-failures, using-git-worktrees, using-superpowers, dispatching-parallel-agents, executing-plans, verification-before-completion, brainstorming, writing-skills, subagent-driven-development

### Adapt significantly (5 skills)

- reporting-metrics → vigiaBR metrics
- comparing-reports → vigiaBR dimensions
- measuring-impact → vigiaBR quality checks
- auditing-pipeline → vigiaBR pipeline
- evolve-engine → vigiaBR context

### Skipped (14 skills)

deploying-to-railway, linear-manager, breaking-down-linear-issues, analyzing-traces, debugging-lead-traces, testing-max-demo, testing-max-webhooks, managing-eval-datasets, running-evals, managing-braintrust-scorers, test-case-scorer-review, simulating-customer-interactions, training-coding-memory, creating-pdf

### New (create later)

- managing-github-issues — replacement for linear-manager

## 6. GitHub Actions Workflows

| Workflow | Purpose | Adaptation |
|----------|---------|-----------|
| ci.yml | Unified CI | Rewrite for vigiaBR: ruff + mypy, pytest, Next.js build + tsc. Keep parallel gate structure. Add Neo4j service container |
| claude-code-review.yml | Auto code review on PRs | Minimal change |
| claude.yml | Interactive @claude on issues/PRs | No change |
| auto-merge.yml | Auto-merge when checks pass | Adapt required checks. Remove staging |
| auto-merge-claude-config.yml | Instant merge for .claude/-only PRs | No change |

Skipped 12 max-specific workflows (bots, deploy, publish, cleanup).

## 7. Git Setup

- Create `develop` branch from current `master`
- `main` = production (protected, deploy-only)
- `develop` = integration branch
- Feature branches → develop → main

## Deliverable Summary

| Component | Count |
|-----------|-------|
| CLAUDE.md | 1 (rewritten) |
| settings.json | 1 (adapted) |
| Hook scripts | 8 (6 direct, 2 adapted) |
| Agents | 3 (adapted) |
| Commands | ~15 (7 routers + aliases) |
| Skills | 27 (22 ported + 5 adapted) |
| GitHub workflows | 5 |
| Git setup | create develop branch |

## Deferred

- vigiaBR-specific evals and scoring metrics (Phase 2)
- Deployment workflow (stack TBD)
- `managing-github-issues` skill (when issue workflow established)
