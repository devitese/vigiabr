---
name: finishing-a-development-branch
description: Complete development work — merge, PR, or cleanup
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Finishing a Development Branch

## Core Principle

Verify tests -> Present options -> Execute choice -> Clean up.

## Process

### Step 1: Verify

```bash
# Run tests
python3 -m pytest tests/ -v 2>/dev/null || true
npx tsc --noEmit 2>/dev/null || true

# Check git state
git status
git log --oneline develop..HEAD
```

### Step 2: Present Options

Use `AskUserQuestion` with exactly 4 options:

1. **Merge locally** — Merge into develop locally
2. **Push / Create PR** — Push branch and create PR targeting develop
3. **Keep as-is** — Leave branch for later
4. **Discard** — Delete branch and changes (requires typed confirmation)

### Step 3: Execute

Based on selection:
- **Merge**: `git checkout develop && git merge --no-ff <branch>`
- **PR**: `git push -u origin <branch> && gh pr create --base develop`
- **Keep**: Do nothing, report branch name
- **Discard**: Confirm, then `git checkout develop && git branch -D <branch>`

### Step 4: Clean Up

Only for merge or discard:
- Delete local branch
- Clean up worktree if applicable
