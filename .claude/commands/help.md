---
description: "Show available commands"
argument-hint: "[command-name]"
model: opus
allowed-tools: Read
---

# /help $ARGUMENTS

Display the following command reference:

## Routers

```
/plan    -> explore | approach | write
/build   -> feature | fix | test
/ship    -> review | respond | debug-ci | fix-ci | git
/report  -> weekly | metrics | compare
/evolve  -> status | audit | suggest
/run     -> smart router (asks what you need)
```

## Shortcuts

```
/fix     -> /build fix
/git     -> /ship git
/measure -> eval impact measurement
```

## Usage

```
/plan explore #42         Explore codebase for issue #42
/plan approach            Design 2-3 approaches with tradeoffs
/plan write               Write implementation plan document

/build feature #42        Implement feature for issue #42
/build fix auth.py        Fix bug in auth.py
/build test --unit        Write and run unit tests

/ship review              Self-review + create PR
/ship respond 42          Address PR #42 feedback
/ship debug-ci            Debug CI failure
/ship fix-ci              Fix failing CI checks
/ship git --commit        Create commit
/ship git --pr            Create pull request

/report weekly            Weekly stakeholder report
/report metrics           Current metrics snapshot
/report compare           Compare two periods

/evolve status            Recent pipeline activity
/evolve audit             Health analysis
/evolve suggest           Propose new automations
```
