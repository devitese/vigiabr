---
description: "Meta-router -- routes to /plan, /build, /ship, or /evolve"
argument-hint: "[task description or #issue-number]"
allowed-tools: Read, AskUserQuestion, Skill
---

# /run $ARGUMENTS

## Smart Routing

| Input | Action |
|-------|--------|
| (empty) | Ask what user needs |
| `#123` | `Skill("building-features", args)` |
| Text with "fix", "bug", "error" | `Skill("fixing-bugs", args)` |
| Text with "test", "verify" | `Skill("writing-and-running-tests", args)` |
| Text with "plan", "explore", "approach" | Route to `/plan` |
| Text with "review", "pr", "deploy", "commit" | Route to `/ship` |
| Text with "evolve", "audit", "suggest" | Route to `/evolve` |
| Other text / description | `Skill("building-features", args)` |

## Default Options (when empty)

Present with `AskUserQuestion`:
1. "Plan" -- Explore codebase, design approach, write plan
2. "Build" -- Implement feature, fix bug, write tests
3. "Ship" -- Review, create PR, deploy
4. "Evolve" -- Audit pipeline health, suggest automations
