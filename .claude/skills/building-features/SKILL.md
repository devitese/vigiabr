---
name: building-features
description: Full feature implementation with mandatory clarification step
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, AskUserQuestion, Skill, TeamCreate, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# Building Features

## Philosophy

Clarify before implementing. Every feature starts with understanding, not coding.

## Process

### Step 1: Understand the Request

If a GitHub Issue number is provided:
```bash
gh issue view <number> --json title,body,labels,assignees
```

If the request is ambiguous, use `AskUserQuestion` with 2-4 concrete options before proceeding.

### Step 2: Explore Context

Use direct `Glob`/`Grep`/`Read` to understand:
- Existing patterns in the codebase
- Related code and dependencies
- Test patterns used in the project

Do NOT use Task(Explore) subagents for this — use direct tools.

### Step 3: Synthesize and Plan

Before writing code:
- List files that will be created or modified
- Identify the implementation order
- Note any dependencies or blockers

### Step 4: Implement

For complex features (3+ files, multiple components):
- Use `TeamCreate` to parallelize independent subtasks
- Dispatch subagents via `Task(team_name=...)` for each subtask

For simple features:
- Implement directly in sequence
- Write tests alongside implementation (TDD when possible)

### Step 5: Validate

After implementation:
```bash
# Python
ruff check . 2>/dev/null || true
python3 -m pytest tests/ -v 2>/dev/null || true

# TypeScript (if applicable)
npx tsc --noEmit 2>/dev/null || true
```

### Step 6: Summary

Report what was done:
- Files created/modified
- Tests added
- Issues discovered
- Suggested next steps

## Flags

- `--quick` — Skip exploration, implement directly (for trivial changes)
- `--finish` — Resume and complete an in-progress feature
- `--refactor` — Refactor existing code without changing behavior
