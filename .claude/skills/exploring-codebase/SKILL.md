---
name: exploring-codebase
description: Mandatory codebase exploration — first step of the planning pipeline
allowed-tools: Read, Write, Glob, Grep, Bash, Task, AskUserQuestion
---

# Exploring Codebase

## Purpose

First step of the planning pipeline. Gather comprehensive context before designing any approach.

## Inputs

- GitHub Issue number (e.g., `#42`) or topic description
- Optional: specific files or areas to focus on

## Process

### Step 1: Understand the Request

If a GitHub Issue number is provided:
```bash
gh issue view <number> --json title,body,labels,assignees
```

Otherwise, use the topic description directly.

### Step 2: Parallel Exploration

Launch parallel searches to gather context:

1. **Find relevant files** — Glob for likely file patterns based on the topic
2. **Search for patterns** — Grep for key terms, function names, imports
3. **Map dependencies** — Trace imports and call chains
4. **Find existing tests** — Locate test files related to the area

Use direct `Glob`/`Grep`/`Read` tools — NOT Task(Explore) subagents.

### Step 3: Synthesize Context

Create a Context Summary with:
- **Core files**: Files that will need to change
- **Supporting files**: Files that provide context but won't change
- **Dependencies**: External libraries and internal modules involved
- **Test coverage**: Existing tests and gaps
- **Risks**: Potential issues or blockers

### Step 4: Save Artifact

Write exploration results to `docs/plans/explore-<topic>.md`:

```markdown
# Exploration: <topic>

## Context Summary
- Issue: #<number> — <title>
- Area: <affected area>
- Complexity: low | medium | high

## Core Files
- `path/to/file.py:L10-L50` — <what it does>

## Supporting Files
- `path/to/related.py` — <why relevant>

## Dependencies
- <library/module> — <how used>

## Test Coverage
- Existing: <tests found>
- Gaps: <what's missing>

## Risks
- <risk 1>
- <risk 2>
```

## Output Marker

End with: `**Context Summary complete.** Ready for `/plan approach`.`
