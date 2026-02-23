---
description: "Fix failing CI checks -- diagnose, fix, verify, push"
argument-hint: "[run-id]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill
---

# /ship fix-ci $ARGUMENTS

Invoke `Skill("fixing-ci-checks", "$ARGUMENTS")` and follow its instructions.
