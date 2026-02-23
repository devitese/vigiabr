---
description: "Stakeholder reporting -- weekly, metrics, compare"
argument-hint: "[weekly|metrics|compare]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion, Skill, Task
---

# /report $ARGUMENTS

## Routing

| Input | Action |
|-------|--------|
| `weekly` | `Skill("reporting-metrics", "weekly")` |
| `metrics` | `Skill("reporting-metrics", args)` |
| `compare` | `Skill("comparing-reports", args)` |
| (empty) | Auto-detect: Friday -> weekly, else ask |
| Other text | Interpret as natural language |

## Auto-Detection

Check day of week with `date +%u`. Friday (5) -> report-weekly. Else ask user with options:
1. "Weekly stakeholder report" -- Full report with before/after metrics
2. "Metrics snapshot" -- Current metrics without comparison
3. "Period comparison" -- Compare two custom periods
