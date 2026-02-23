---
description: "Git operations -- commit, PR, recover, revert"
argument-hint: "[--commit|--pr|--review|--recover|--revert|--no-push]"
model: opus
allowed-tools: Bash, Read, Grep, Glob, Task, TodoWrite, AskUserQuestion, Skill
agent: git-operator
---

# /git $ARGUMENTS

Invoke `Skill("managing-git-operations", "$ARGUMENTS")` and follow its instructions.
