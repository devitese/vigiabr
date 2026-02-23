---
name: fixing-ci-checks
description: Fix failing CI checks — diagnose, fix, verify, push
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill
---

# Fixing CI Checks

## Process

### Step 1: Identify Failure

```bash
# Get most recent failed run
gh run list --status failure --limit 1
gh run view <run-id> --log-failed
```

### Step 2: Categorize and Fix

| Category | Fix Strategy |
|----------|-------------|
| TypeScript errors | Fix type errors, run `npx tsc --noEmit` locally |
| Python lint (ruff) | Run `ruff check --fix .`, then manual fixes |
| Python type (mypy) | Fix type annotations |
| Test failures | Read test output, fix root cause |
| Build failures | Check imports, dependencies, config |

### Step 3: Verify Locally

Re-run the exact check that failed:
```bash
# Must pass locally before pushing
ruff check . 2>/dev/null || true
python3 -m pytest tests/ -v 2>/dev/null || true
npx tsc --noEmit 2>/dev/null || true
```

### Step 4: Commit and Push

```bash
git add <fixed-files>
git commit -m "fix: resolve CI failures in <category>"
git push
```

## Auto-fixable

- `ruff check --fix .` — Python lint auto-fix
- `npx eslint --fix .` — JS/TS lint auto-fix

## Not Auto-fixable

- Test regressions (need root cause analysis)
- Infrastructure flakes (need retry or config fix)
