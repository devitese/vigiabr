---
description: "Auto-evolving pipeline engine -- detect patterns, audit health, suggest automations"
argument-hint: "[status|audit|suggest]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion, Task
---

# /evolve $ARGUMENTS

## Routing

| Input | Action |
|-------|--------|
| (empty) or `status` | `Skill("evolve-engine", "status")` |
| `audit` | `Skill("evolve-engine", "audit")` |
| `suggest` | `Skill("evolve-engine", "suggest")` |
| Other text | Interpret as natural language |
