---
name: reviewing-for-shipping
description: Self-review all changes before shipping
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Task, TeamCreate, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# Reviewing for Shipping

## Process

### Phase 1: Pre-flight

```bash
# Verify branch
git branch --show-current
# Get diff
git diff develop...HEAD --stat
git diff develop...HEAD
```

### Phase 2: Quality Checks

```bash
# Python
ruff check . 2>/dev/null || true
python3 -m pytest tests/ -v 2>/dev/null || true

# TypeScript (if applicable)
npx tsc --noEmit 2>/dev/null || true
```

### Phase 3: Self-Review

Review the diff for:
- **Security**: PII exposure, SQL injection, command injection, LGPD violations
- **Code quality**: Dead code, unclear naming, missing error handling
- **Test coverage**: Are new code paths tested?
- **Consistency**: Does it match existing patterns?

### Phase 4: Fix Issues

Fix any issues found during self-review. Re-run quality checks.

### Phase 5: Create PR

```bash
git push -u origin $(git branch --show-current)
gh pr create --base develop --draft --title "<title>" --body "<body>"
```

Use `Skill("superpowers:verification-before-completion")` before claiming done.

### Phase 6: Request Review

Report PR URL and summary of changes.
