---
description: "Build subtree -- feature, fix, test"
argument-hint: "[feature|fix|test] [args...]"
allowed-tools: Read, Grep, Glob, Task, AskUserQuestion, Skill
---

# /build $ARGUMENTS

## Routing

| Input starts with | Action |
|-------------------|--------|
| `feature` | `Skill("building-features", args)` |
| `fix` | `Skill("fixing-bugs", args)` |
| `test` | `Skill("writing-and-running-tests", args)` |
| `#123` | `Skill("building-features", args)` |
| `--quick`, `--finish`, `--refactor` | `Skill("building-features", args)` |
| `--diagnose`, `--types` | `Skill("fixing-bugs", args)` |
| `--unit`, `--e2e` | `Skill("writing-and-running-tests", args)` |
| Other text / description | `Skill("building-features", args)` |
| (empty) | `Skill("building-features")` (prompts user) |

## Examples

```
/build feature #42             -> building-features #42
/build fix auth.py             -> fixing-bugs auth.py
/build test --unit api.py      -> writing-and-running-tests --unit api.py
/build #42                     -> building-features #42
/build --types                 -> fixing-bugs --types
/build                         -> building-features (prompts user)
```
