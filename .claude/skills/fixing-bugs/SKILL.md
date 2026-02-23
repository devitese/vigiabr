---
name: fixing-bugs
description: Bug fix workflow — figure it out without hand-holding
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task
---

# Fixing Bugs

## Philosophy

Figure it out without hand-holding. Use direct tools (Glob/Grep/Read) to explore. Don't ask questions unless truly stuck.

## Process

### Step 1: Understand the Bug

If a GitHub Issue is referenced:
```bash
gh issue view <number> --json title,body,labels
```

Otherwise, understand from the error description or stack trace.

### Step 2: Diagnose

Use `Skill("superpowers:systematic-debugging")` for complex bugs.

For simple bugs:
1. Locate the error source with `Grep`
2. Read the relevant code with `Read`
3. Trace the data flow
4. Identify the root cause

### Step 3: Fix

Apply the minimal fix that addresses the root cause. Do NOT:
- Add unrelated improvements
- Refactor surrounding code
- Add defensive checks for unrelated scenarios

### Step 4: Verify

```bash
# Run related tests
python3 -m pytest tests/ -v -k "<test_name>" 2>/dev/null || true

# Check types/lint
ruff check <changed_files> 2>/dev/null || true
```

### Step 5: Summary

Report:
- Root cause identified
- Fix applied
- Tests passing
- Any follow-up issues discovered

## Flags

- `--diagnose` — Read-only diagnosis, don't apply fixes
- `--types` — Focus on type errors only
