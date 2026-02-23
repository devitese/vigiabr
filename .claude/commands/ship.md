---
description: "Delivery subtree -- review, respond, deploy, debug-ci, fix-ci, git"
argument-hint: "[review|respond|debug-ci|fix-ci|git]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill
---

# /ship $ARGUMENTS

## Routing

| Input | Action |
|-------|--------|
| `review` | `Skill("reviewing-for-shipping", args)` |
| `respond` | `Skill("responding-to-pr-feedback", args)` |
| `debug-ci`, `debug`, `ci` | `Skill("debugging-ci-failures", args)` |
| `fix-ci`, `fix ci`, `green`, `make ci pass` | `Skill("fixing-ci-checks", args)` |
| `git`, `commit`, `pr`, `revert`, `recover` | `Skill("managing-git-operations", args)` |
| (empty) | Auto-detect context |
| Other text | Interpret as natural language |

## Auto-Detection Logic

```
1. Check: git status --short
2. Check: git branch --show-current
3. Check: gh pr view --json number,state

IF uncommitted changes -> Skill("reviewing-for-shipping")
ELSE IF PR exists with failing checks -> Skill("fixing-ci-checks")
ELSE IF PR exists -> Skill("responding-to-pr-feedback")
ELSE IF feature branch with commits ahead -> Skill("reviewing-for-shipping")
ELSE -> Skill("superpowers:finishing-a-development-branch")
```
