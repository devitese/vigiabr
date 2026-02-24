# Claude Code Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Port and adapt a reference project's Claude Code pipeline to vigiaBR, giving the project a full development workflow from day one.

**Architecture:** Fork & Strip approach — copy the reference project's `.claude/` infrastructure and `.github/workflows/`, then adapt all references from automotive CRM to Brazilian transparency platform. Commands route to skills, skills contain knowledge, subagents execute.

**Tech Stack:** Shell (hooks), Markdown (commands/skills/agents), YAML (GitHub Actions), Python + TypeScript (quality gates)

---

## Phase 1: Foundation (settings.json + CLAUDE.md)

### Task 1: Rewrite CLAUDE.md as routing trunk

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Rewrite CLAUDE.md**

Replace the current CLAUDE.md with the routing trunk adapted from the reference project. Key sections:
- General Behavior (execute immediately, AskUserQuestion for decisions)
- Memory Retrieval (claude-mem mandatory search)
- Session Continuations (git log re-establish context)
- Key Rules (adapted: GitHub Issues not Linear, no Supabase rules, add LGPD/PII rules, conventional commits, develop branch workflow, TeamCreate for 2+ tasks, evolve markers)
- Architecture table (Scrapy, Airflow, FastAPI, Next.js, Neo4j, PostgreSQL)
- Git Workflow (branch from develop, PRs target develop, main = production)
- Automation Architecture (commands → skills → subagents → tools)
- Slash Commands table (plan/build/ship/report/evolve/run/help)
- Documentation Tree (placeholder paths for future service CLAUDE.md files)

Keep the existing Project Overview, Technology Stack, Architecture, SCI Scoring, Data Sources, Conventions, Agent Orchestrator, and Phased Rollout sections — they're good. Add the new routing trunk sections above them.

**Step 2: Verify CLAUDE.md renders correctly**

Read the file back and verify all markdown renders properly.

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: rewrite CLAUDE.md as routing trunk for Claude Code pipeline"
```

---

### Task 2: Update settings.json with hooks and permissions

**Files:**
- Modify: `.claude/settings.json`

**Step 1: Rewrite settings.json**

Merge the existing metadata-updater hook with the new hooks from the reference project. The final settings.json should have:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/superpowers-session-start.sh",
            "timeout": 10,
            "statusMessage": "Loading superpowers..."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-conflict-markers.sh",
            "timeout": 30,
            "statusMessage": "Checking for conflict markers..."
          },
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/ensure-docker-running.sh",
            "timeout": 75,
            "statusMessage": "Ensuring Docker is running..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-python-syntax.sh",
            "timeout": 15,
            "statusMessage": "Checking Python syntax..."
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/metadata-updater.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/cleanup-stray-claude-md.sh",
            "timeout": 10,
            "statusMessage": "Cleaning up stray CLAUDE.md files..."
          },
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/quality-gate-task.sh",
            "timeout": 60,
            "statusMessage": "Running quality gate checks..."
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/subagent-context.sh",
            "timeout": 5,
            "statusMessage": "Injecting project context..."
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": ["Bash"],
    "deny": [
      "Bash(command~=git push --force:*)",
      "Bash(command~=git push -f:*)",
      "Bash(command~=git push --force-with-lease:*)",
      "Bash(command~=git reset --hard:*)",
      "Bash(command~=git clean -f:*)",
      "Bash(command~=git clean -fd:*)",
      "Bash(command~=git clean -fx:*)",
      "Bash(command~=git checkout --force:*)",
      "Bash(command~=git checkout -f:*)",
      "Bash(command~=git branch -D:*)",
      "Bash(command~=git filter-branch:*)",
      "Bash(command~=git push --delete:*)",
      "Bash(command~=git rm -rf:*)",
      "Bash(command~=git rm -fr:*)",
      "Bash(command~=git stash drop:*)",
      "Bash(command~=git stash clear:*)",
      "Bash(command~=git reflog expire:*)",
      "Bash(command~=git gc --prune:*)",
      "Bash(command~=git update-ref -d:*)",
      "Bash(command~=git commit --amend:*)",
      "Bash(command~=git commit --no-verify:*)",
      "Bash(command~=git commit -n:*)",
      "Bash(command~=git --no-verify:*)",
      "Bash(command~=git --no-gpg-sign:*)",
      "Bash(command~=git config:*)",
      "Bash(command~=git rebase -i:*)",
      "Bash(command~=git rebase --interactive:*)",
      "Bash(command~=gh repo delete:*)",
      "Bash(command~=gh repo archive:*)",
      "Bash(command~=gh pr close --delete-branch:*)",
      "Bash(command~=gh pr close -d:*)",
      "Bash(command~=gh pr merge --delete-branch:*)",
      "Bash(command~=gh pr merge -d:*)",
      "Bash(command~=gh issue delete:*)",
      "Bash(command~=gh release delete:*)",
      "Bash(command~=gh run delete:*)",
      "Bash(command~=gh secret delete:*)",
      "Bash(command~=gh variable delete:*)",
      "Bash(command~=gh label delete:*)",
      "Bash(command~=gh workflow disable:*)",
      "Bash(command~=gh extension remove:*)",
      "Bash(command~=gh gpg-key delete:*)",
      "Bash(command~=gh ssh-key delete:*)",
      "Bash(command~=gh api -X DELETE:*)",
      "Bash(command~=gh api --method DELETE:*)",
      "Bash(command~=gh auth refresh --force:*)",
      "Bash(command~=gh pr create --base main:*)",
      "Bash(command~=gh pr create -B main:*)",
      "Bash(command~=gh pr create main:*)",
      "Bash(command~=git pull origin main:*)",
      "Bash(command~=git pull main:*)",
      "Bash(command~=git push origin main:*)",
      "Bash(command~=git push origin develop:*)",
      "Bash(command~=git push main:*)",
      "Bash(command~=git push develop:*)",
      "Bash(command~=git checkout main:*)",
      "Bash(command~=git checkout develop:*)",
      "Bash(command~=git switch main:*)",
      "Bash(command~=git switch develop:*)",
      "Bash(command~=git merge main:*)",
      "Bash(command~=git merge develop:*)",
      "Bash(command~=git merge origin/main:*)",
      "Bash(command~=git merge origin/develop:*)",
      "Bash(command~=git rebase origin main:*)",
      "Bash(command~=git rebase origin develop:*)",
      "Bash(command~=git rebase main:*)",
      "Bash(command~=git rebase develop:*)"
    ],
    "ask": ["Bash(command~=git push:*)"]
  }
}
```

Note: Removed `staging` branch references from the reference project. Kept metadata-updater.sh as PostToolUse for Bash. Removed `pnpm format` from Stop (vigiaBR doesn't have pnpm yet — will add formatter when project has code).

**Step 2: Commit**

```bash
git add .claude/settings.json
git commit -m "chore: add hooks and git safety permissions to settings.json"
```

---

## Phase 2: Hook Scripts

### Task 3: Create hook scripts

**Files:**
- Create: `.claude/hooks/superpowers-session-start.sh`
- Create: `.claude/hooks/check-conflict-markers.sh`
- Create: `.claude/hooks/ensure-docker-running.sh`
- Create: `.claude/hooks/check-python-syntax.sh`
- Create: `.claude/hooks/quality-gate-task.sh`
- Create: `.claude/hooks/cleanup-stray-claude-md.sh`
- Create: `.claude/hooks/subagent-context.sh`
- Create: `.claude/hooks/quality-gate-idle.sh`
- Keep: `.claude/metadata-updater.sh` (already exists, move to hooks/)

**Step 1: Create superpowers-session-start.sh**

Direct copy from the reference project — no changes needed. This reads the using-superpowers SKILL.md and injects it at session start.

**Step 2: Create check-conflict-markers.sh**

Direct copy from the reference project — scans for conflict markers before git commits. No changes needed.

**Step 3: Create ensure-docker-running.sh**

Direct copy from the reference project — auto-starts Docker Desktop when docker commands are detected. No changes needed (vigiaBR uses Docker + Caddy).

**Step 4: Create check-python-syntax.sh**

Direct copy from the reference project — validates Python files after Edit/Write. No changes needed.

**Step 5: Create quality-gate-task.sh**

Adapt from the reference project:
- Change venv paths from the reference project's layout to vigiaBR-appropriate paths (search common locations: `.venv`, `venv`)
- Remove `pnpm check-types` — replace with `npx tsc --noEmit` when a tsconfig.json exists (check first)
- Keep the logic: skip for non-code tasks, check changed files, run appropriate linters

**Step 6: Create cleanup-stray-claude-md.sh**

Direct copy from the reference project — removes untracked CLAUDE.md files from wrong directories. No changes needed.

**Step 7: Create subagent-context.sh**

Rewrite for vigiaBR domain:
```bash
CONTEXT="Project: VigiaBR — transparency monitoring platform for Brazilian public officials. Branch from develop, PRs target develop. Never push to main."

case "$AGENT_TYPE" in
  git-operator)
    CONTEXT="$CONTEXT Git rules: PRs always --base develop. Never force push main. Always backup before destructive ops."
    ;;
  codebase-analyzer|codebase-explorer|Explore)
    CONTEXT="$CONTEXT Key dirs: scrapers/ (Python/Scrapy), dags/ (Airflow), api/ (FastAPI), web/ (Next.js), graph/ (Neo4j/Cypher)."
    ;;
  plan-executor)
    CONTEXT="$CONTEXT Execute precisely. Python: ruff check + mypy. TypeScript: tsc --noEmit. Always verify after edits."
    ;;
esac
```

Note: Directory names are placeholders — update when project structure is created.

**Step 8: Create quality-gate-idle.sh**

Adapt from the reference project — same logic but with vigiaBR venv paths for ruff/mypy. Remove pnpm check-types, use tsc --noEmit with existence check.

**Step 9: Move metadata-updater.sh to hooks directory**

Move `.claude/metadata-updater.sh` to `.claude/hooks/metadata-updater.sh` and update the path in settings.json.

**Step 10: Make all hooks executable and commit**

```bash
chmod +x .claude/hooks/*.sh
git add .claude/hooks/ .claude/metadata-updater.sh .claude/settings.json
git commit -m "chore: add Claude Code hook scripts for quality gates and safety"
```

---

## Phase 3: Agents

### Task 4: Create agent definitions

**Files:**
- Create: `.claude/agents/code-reviewer.md`
- Create: `.claude/agents/codebase-analyzer.md`
- Create: `.claude/agents/git-operator.md`

**Step 1: Create code-reviewer.md**

Direct copy from the reference project — the agent is generic enough to work as-is. No domain-specific references.

**Step 2: Create codebase-analyzer.md**

Adapt from the reference project:
- Remove pnpm-specific commands, replace with Python equivalents
- Change `pnpm lint` → `ruff check .`
- Change `pnpm outdated` → `pip list --outdated`
- Change `pnpm audit` → `pip-audit` / `safety check`
- Keep the overall lifecycle structure (PLAN → EXECUTE → TEST → DOCUMENT)
- Remove Braintrust/MCP references
- Remove Linear/DEA references

**Step 3: Create git-operator.md**

Adapt from the reference project:
- Change all `--base develop` references (keep same — vigiaBR also uses develop)
- Remove Linear issue references, use GitHub Issue format (`Fixes #123`)
- Remove staging references
- Keep all safety rules, emergency commands, lifecycle structure

**Step 4: Commit**

```bash
git add .claude/agents/
git commit -m "chore: add code-reviewer, codebase-analyzer, git-operator agents"
```

---

## Phase 4: Slash Commands

### Task 5: Create command routers

**Files:**
- Create: `.claude/commands/plan.md`
- Create: `.claude/commands/build.md`
- Create: `.claude/commands/ship.md`
- Create: `.claude/commands/report.md`
- Create: `.claude/commands/evolve.md`
- Create: `.claude/commands/run.md`
- Create: `.claude/commands/help.md`

**Step 1: Create /plan router**

Adapt from the reference project:
- Replace Linear gates with GitHub Issue gates: `gh issue create` before branching
- Replace `DEA-###` detection with `#123` (GitHub Issue numbers)
- Remove `linear` and `breakdown` sub-commands
- Keep: explore → approach → write pipeline with gate enforcement
- Route: `Skill("exploring-codebase")`, `Skill("designing-approaches")`, `Skill("documenting-plans")`

**Step 2: Create /build router**

Adapt from the reference project:
- Remove `eval`, `eval-dataset`, `test-auto` routes
- Remove `mcp__linear__get_issue` from allowed-tools
- Replace `DEA-###` with `#123`
- Keep: feature, fix, test routes
- Route: `Skill("building-features")`, `Skill("fixing-bugs")`, `Skill("writing-and-running-tests")`

**Step 3: Create /ship router**

Adapt from the reference project:
- Remove `deploy` route (deployment TBD)
- Keep: review, respond, debug-ci, fix-ci, git
- Keep auto-detection logic (uncommitted changes → review, PR with failing checks → fix-ci, etc.)
- Route to respective skills

**Step 4: Create /report router**

Adapt from the reference project:
- Keep: weekly, metrics, compare
- Adapt context for vigiaBR metrics (pipeline coverage, data freshness, SCI accuracy)
- Route: `Skill("reporting-metrics")`, `Skill("comparing-reports")`

**Step 5: Create /evolve router**

Direct copy from the reference project — generic pipeline health auditing. No domain-specific changes needed.

**Step 6: Create /run meta-router**

Adapt from the reference project:
- Replace `DEA-###` with `#123`
- Remove Railway/Linear specific routes
- Keep smart routing: fix/bug → build-fix, test → build-test, plan → plan, review/pr → ship, evolve → evolve

**Step 7: Create /help**

Rewrite for vigiaBR command set. Show:
- Routers: /plan, /build, /ship, /report, /evolve, /run
- Shortcuts: /fix, /git, /measure
- No Railway, Linear, contract-check, debug-lead, debug-trace

**Step 8: Commit**

```bash
git add .claude/commands/
git commit -m "chore: add slash command routers (plan/build/ship/report/evolve/run/help)"
```

---

### Task 6: Create command sub-commands and aliases

**Files:**
- Create: `.claude/commands/plan-explore.md`
- Create: `.claude/commands/plan-approach.md`
- Create: `.claude/commands/plan-write.md`
- Create: `.claude/commands/build-feature.md`
- Create: `.claude/commands/build-fix.md`
- Create: `.claude/commands/build-test.md`
- Create: `.claude/commands/ship-review.md`
- Create: `.claude/commands/ship-respond.md`
- Create: `.claude/commands/ship-debug-ci.md`
- Create: `.claude/commands/ship-fix-ci.md`
- Create: `.claude/commands/fix.md`
- Create: `.claude/commands/git.md`
- Create: `.claude/commands/measure.md`

**Step 1: Create plan sub-commands**

These are thin routers — each is ~5 lines routing to a skill:
- `plan-explore.md` → `Skill("exploring-codebase", "$ARGUMENTS")`
- `plan-approach.md` → `Skill("designing-approaches", "$ARGUMENTS")`
- `plan-write.md` → `Skill("documenting-plans", "$ARGUMENTS")`

Adapt from the reference project: same structure, remove Linear references from argument-hint. Change `DEA-###` to `#123`.

**Step 2: Create build sub-commands**

- `build-feature.md` → `Skill("building-features", "$ARGUMENTS")`
- `build-fix.md` → `Skill("fixing-bugs", "$ARGUMENTS")`
- `build-test.md` → `Skill("writing-and-running-tests", "$ARGUMENTS")`

Adapt: remove `mcp__linear__get_issue` from allowed-tools in build-feature. Change DEA-### to #123.

**Step 3: Create ship sub-commands**

- `ship-review.md` → `Skill("reviewing-for-shipping", "$ARGUMENTS")`
- `ship-respond.md` → `Skill("responding-to-pr-feedback", "$ARGUMENTS")`
- `ship-debug-ci.md` → `Skill("debugging-ci-failures", "$ARGUMENTS")`
- `ship-fix-ci.md` → `Skill("fixing-ci-checks", "$ARGUMENTS")`

Direct copy from the reference project — these are thin routers with no domain-specific content.

**Step 4: Create aliases**

- `fix.md` → `Skill("fixing-bugs", "$ARGUMENTS")` (alias for /build fix)
- `git.md` → `Skill("managing-git-operations", "$ARGUMENTS")` (with git-operator agent)
- `measure.md` → `Skill("measuring-impact", "$ARGUMENTS")`

Adapt git.md: same structure as the reference project but remove Linear references.

**Step 5: Commit**

```bash
git add .claude/commands/
git commit -m "chore: add command sub-commands and aliases"
```

---

## Phase 5: Skills (Direct Port)

### Task 7: Port planning skills

**Files:**
- Create: `.claude/skills/exploring-codebase/SKILL.md`
- Create: `.claude/skills/designing-approaches/SKILL.md`
- Create: `.claude/skills/documenting-plans/SKILL.md`

**Step 1: Port exploring-codebase**

Adapt from the reference project:
- Remove Linear issue lookup, use `gh issue view #123` instead
- Remove DEA-### references, use #123
- Keep parallel exploration pattern (find files, search patterns, map deps, find tests)
- Update artifact paths to vigiaBR structure

**Step 2: Port designing-approaches**

Adapt from the reference project:
- Remove Linear references
- Remove Braintrust eval baseline capture
- Keep: load exploration context, generate 2-3 approaches, present for selection, expand into plan, enter plan mode

**Step 3: Port documenting-plans**

Adapt from the reference project:
- Remove Linear references
- Keep: gather plan content, write comprehensive doc, commit to docs/plans/

**Step 4: Commit**

```bash
git add .claude/skills/
git commit -m "chore: add planning skills (explore, approach, document)"
```

---

### Task 8: Port building skills

**Files:**
- Create: `.claude/skills/building-features/SKILL.md`
- Create: `.claude/skills/fixing-bugs/SKILL.md`
- Create: `.claude/skills/writing-and-running-tests/SKILL.md`

**Step 1: Port building-features**

Adapt from the reference project:
- Remove Linear issue lookup → `gh issue view #123`
- Remove DEA-### → #123
- Remove Braintrust eval measurement gates (defer to Phase 2)
- Remove translation key rules
- Keep: clarify ambiguities, explore codebase, synthesize, implement, validate
- Keep TeamCreate for complex features

**Step 2: Port fixing-bugs**

Adapt from the reference project:
- Remove DEA-### → #123
- Remove eval measurement gates
- Keep: direct exploration, systematic-debugging delegation, minimal fix, verify, summary
- Keep --diagnose and --types flags

**Step 3: Port writing-and-running-tests**

Adapt from the reference project:
- Keep auto-detect (Python/TypeScript/E2E)
- Change Vitest references to Jest (or keep generic — vigiaBR frontend testing TBD)
- Keep Pytest for Python tests
- Remove Playwright E2E specifics (defer)
- Keep TDD discipline via superpowers:test-driven-development

**Step 4: Commit**

```bash
git add .claude/skills/
git commit -m "chore: add building skills (features, bugs, tests)"
```

---

### Task 9: Port shipping skills

**Files:**
- Create: `.claude/skills/managing-git-operations/SKILL.md`
- Create: `.claude/skills/reviewing-for-shipping/SKILL.md`
- Create: `.claude/skills/responding-to-pr-feedback/SKILL.md`
- Create: `.claude/skills/finishing-a-development-branch/SKILL.md`
- Create: `.claude/skills/fixing-ci-checks/SKILL.md`
- Create: `.claude/skills/debugging-ci-failures/SKILL.md`

**Step 1: Port managing-git-operations**

Adapt from the reference project:
- Remove Linear issue linking → GitHub Issue linking (`Fixes #123`)
- Remove staging branch references
- Keep: commit, PR, recover, revert workflows
- Keep: PRs target develop, never main
- Keep git-operator agent delegation

**Step 2: Port reviewing-for-shipping**

Adapt from the reference project:
- Remove Linear issue extraction → GitHub Issue extraction from branch name
- Remove contract validation check
- Remove translation check
- Remove Braintrust eval measurement gate
- Keep: pre-flight, quality checks (Python + TS), self-review, fix issues, create PR, request reviewer

**Step 3: Port responding-to-pr-feedback**

Adapt from the reference project:
- Remove Linear references
- Keep: read PR feedback, categorize, implement fixes, validate, push, reply

**Step 4: Port finishing-a-development-branch**

Direct copy from the reference project — generic enough. Keep: verify tests → present 4 options → execute → clean up.

**Step 5: Port fixing-ci-checks**

Adapt from the reference project:
- Remove contract drift and eval failure categories
- Keep: identify failure, categorize (TypeScript, lint, tests, build), fix, verify locally, push
- Adapt ruff/mypy paths for vigiaBR

**Step 6: Port debugging-ci-failures**

Adapt from the reference project:
- Remove Railway deployment pattern
- Remove contract drift pattern
- Keep: fetch logs, parse errors, identify root cause, suggest fixes

**Step 7: Commit**

```bash
git add .claude/skills/
git commit -m "chore: add shipping skills (git, review, respond, finish, ci)"
```

---

### Task 10: Port infrastructure skills

**Files:**
- Create: `.claude/skills/using-superpowers/SKILL.md`
- Create: `.claude/skills/using-git-worktrees/SKILL.md`
- Create: `.claude/skills/dispatching-parallel-agents/SKILL.md`
- Create: `.claude/skills/executing-plans/SKILL.md`
- Create: `.claude/skills/verification-before-completion/SKILL.md`
- Create: `.claude/skills/brainstorming/SKILL.md`
- Create: `.claude/skills/writing-skills/SKILL.md`
- Create: `.claude/skills/subagent-driven-development/SKILL.md`
- Create: `.claude/skills/systematic-debugging/SKILL.md`

**Step 1: Check if these skills come from superpowers plugin**

These skills (`using-superpowers`, `brainstorming`, `writing-skills`, `verification-before-completion`, `dispatching-parallel-agents`, `executing-plans`, `subagent-driven-development`, `systematic-debugging`, `using-git-worktrees`) are likely provided by the superpowers plugin already installed at `~/.claude/plugins/cache/claude-plugins-official/superpowers/`. If so, they don't need to be ported — they're already available via `Skill("superpowers:skill-name")`.

Verify: check if the superpowers plugin provides these skills. If yes, skip creating them and just reference them as `superpowers:skill-name` in commands.

**Step 2: If skills are plugin-provided, skip creation. Otherwise, port them.**

Direct copies from the reference project — these are generic development workflow skills with no domain-specific content.

**Step 3: Commit (if any files created)**

```bash
git add .claude/skills/
git commit -m "chore: add infrastructure skills"
```

---

### Task 11: Port and adapt reporting/evolve skills

**Files:**
- Create: `.claude/skills/reporting-metrics/SKILL.md`
- Create: `.claude/skills/comparing-reports/SKILL.md`
- Create: `.claude/skills/measuring-impact/SKILL.md`
- Create: `.claude/skills/auditing-pipeline/SKILL.md`
- Create: `.claude/skills/evolve-engine/SKILL.md`
- Create: `.claude/skills/evolve-engine/reference/pattern-templates.md`

**Step 1: Create reporting-metrics**

Rewrite for vigiaBR:
- Remove Linear/Braintrust data sources
- Metrics: GitHub Issues (open/closed), PRs (open/merged), CI pass rate, data pipeline run count, spider success rate
- Display dashboard format (same style as the reference project)

**Step 2: Create comparing-reports**

Adapt from the reference project:
- Remove Linear sprint comparison
- Use date ranges and GitHub milestones instead
- Compare: issues resolved, PRs merged, CI health, pipeline runs

**Step 3: Create measuring-impact**

Adapt from the reference project:
- Remove Braintrust eval runner
- Replace with: pytest result comparison, type-check delta, lint delta
- Keep gate logic: ship (improvement), caution (neutral), warn (minor regression), block (major regression)
- Simplified version — expand when vigiaBR has its own eval framework

**Step 4: Create auditing-pipeline**

Adapt from the reference project:
- Enumerate vigiaBR artifacts (commands, skills, agents, hooks)
- Same health report format (healthy/ok/stale)
- Remove claude-mem usage tracking (use git log instead for now)

**Step 5: Create evolve-engine**

Adapt from the reference project:
- Same sub-commands: status, audit, suggest
- Same architecture: Observe → Detect Patterns → Generate → Apply
- Remove claude-mem references, use git log for observation
- Keep pattern-templates.md reference doc

**Step 6: Commit**

```bash
git add .claude/skills/
git commit -m "chore: add reporting and evolve skills adapted for vigiaBR"
```

---

## Phase 6: GitHub Actions Workflows

### Task 12: Create CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Write ci.yml**

Simplified CI for vigiaBR's current state (no source code yet, but ready for when code arrives):

```yaml
name: CI
on:
  push:
    branches: [develop, main]
  pull_request:
    branches: [develop, main]

jobs:
  check-branch-flow:
    # develop ← feature branches, main ← develop only

  static-checks:
    # Python: ruff check, mypy
    # TypeScript: tsc --noEmit, eslint (when applicable)

  test:
    # Python: pytest
    # TypeScript: jest/vitest (when applicable)

  build:
    # Next.js build (when web/ exists)
    # Docker build validation
```

Keep the parallel gate structure from the reference project. Add Neo4j and PostgreSQL service containers for integration tests.

**Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add unified CI workflow for Python and TypeScript"
```

---

### Task 13: Create Claude Code workflows

**Files:**
- Create: `.github/workflows/claude-code-review.yml`
- Create: `.github/workflows/claude.yml`

**Step 1: Create claude-code-review.yml**

Adapt from the reference project:
- Same structure: trigger on PR events, use `anthropics/claude-code-action@v1`
- Exclude `.claude/` path changes
- Use code-review plugin

**Step 2: Create claude.yml**

Direct copy from the reference project — trigger on @claude mentions in issues/PRs. Generic workflow.

**Step 3: Commit**

```bash
git add .github/workflows/
git commit -m "ci: add Claude Code review and interactive workflows"
```

---

### Task 14: Create auto-merge workflows

**Files:**
- Create: `.github/workflows/auto-merge.yml`
- Create: `.github/workflows/auto-merge-claude-config.yml`

**Step 1: Create auto-merge.yml**

Adapt from the reference project:
- Required checks: adapt to vigiaBR CI job names (static-checks, test, build)
- Remove staging references
- develop: auto-merge when all checks pass
- main: auto-merge when all checks pass + 1 approval
- Use squash merge, PAT_TOKEN

**Step 2: Create auto-merge-claude-config.yml**

Adapt from the reference project:
- Remove staging from target branches (just develop and main)
- Same logic: instantly merge .claude/-only PRs

**Step 3: Commit**

```bash
git add .github/workflows/
git commit -m "ci: add auto-merge workflows for PRs and .claude/ config changes"
```

---

## Phase 7: Git Setup

### Task 15: Create develop branch and update config

**Step 1: Create develop branch**

```bash
git checkout -b develop
git push -u origin develop
```

**Step 2: Update agent-orchestrator.yaml**

Change `defaultBranch: master` to `defaultBranch: develop` in agent-orchestrator.yaml.

**Step 3: Commit**

```bash
git add agent-orchestrator.yaml
git commit -m "chore: switch default branch to develop"
```

---

## Execution Summary

| Phase | Tasks | Commits | Estimated files |
|-------|-------|---------|----------------|
| 1. Foundation | 2 | 2 | 2 |
| 2. Hooks | 1 | 1 | 9 |
| 3. Agents | 1 | 1 | 3 |
| 4. Commands | 2 | 2 | 20 |
| 5. Skills | 5 | 5 | ~30 |
| 6. Workflows | 3 | 3 | 5 |
| 7. Git setup | 1 | 1 | 1 |
| **Total** | **15** | **15** | **~70** |
