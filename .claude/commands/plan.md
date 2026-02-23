---
description: "Planning subtree -- explore, approach, write"
argument-hint: "[explore|approach|write|#issue-number]"
allowed-tools: Read, Write, Glob, Grep, Bash, AskUserQuestion, Task, Skill, EnterPlanMode
---

# /plan $ARGUMENTS

## Pipeline

All planning follows a strict pipeline — no skippable steps:

```
GitHub Issue (mandatory) -> explore -> approach -> write -> plan document
```

## Gate Rules

1. **Issue gate**: A GitHub Issue must exist before planning. If none referenced, ask user to create one or provide an issue number.
2. **Explore gate**: `/plan approach` requires prior `/plan explore` context.
3. **Approach gate**: `/plan write` requires a selected approach from `/plan approach`.

## Gate Enforcement

Search conversation for output markers (Context Summary, Approach Selected, Plan Approved). If context was compacted, check git branch and log to recover state. Invoke missing steps directly via skills.

## Routing

| Input | Action |
|-------|--------|
| (empty) | Ask user what kind of planning needed |
| `explore` | Enforce issue gate, then `Skill("exploring-codebase", "$ARGUMENTS")` |
| `approach` | Enforce issue + explore gates, then `Skill("designing-approaches", "$ARGUMENTS")` |
| `write` | Enforce all gates, then `Skill("documenting-plans", "$ARGUMENTS")` |
| `#123` (issue number only) | `Skill("exploring-codebase", "$ARGUMENTS")` |
| Other text | Enforce issue gate, then `Skill("exploring-codebase", "$ARGUMENTS")` |
