---
name: managing-git-operations
description: Central hub for all git operations — commit, PR, recover, revert
allowed-tools: Bash, Read, Grep, Glob, Task, TodoWrite, AskUserQuestion, Skill
agent: git-operator
---

# Managing Git Operations

## Critical Rule

**PRs to main are FORBIDDEN.** All PRs target `develop`.

## Fast Paths

### `--commit`
Skip exploration. Go directly to commit workflow:
1. Check `git status` and `git diff --cached`
2. Generate conventional commit message
3. Commit

### `--pr`
1. Verify tests pass before creating PR
2. Push branch with `-u`
3. Create PR targeting `develop`: `gh pr create --base develop`
4. Include summary, test plan, and linked issues

## Full Routing

| Flag | Action |
|------|--------|
| `--commit` | Create commit |
| `--pr` | Create pull request |
| `--pr --skip-tests` | Create PR without running tests first |
| `--review` | Self-review changes (delegate to reviewing-for-shipping) |
| `--recover` | Recover from git disaster |
| `--revert` | Revert changes safely |
| `--no-push` | Commit but don't push |

## PR Template

```markdown
## Summary
- <change 1>
- <change 2>

## Test plan
- [ ] <test item>

Fixes #<issue-number>
```

## Self-Improvement

After every git operation, reflect:
- Did anything go wrong?
- Could the process be smoother?
- Should a new rule be added to CLAUDE.md?
