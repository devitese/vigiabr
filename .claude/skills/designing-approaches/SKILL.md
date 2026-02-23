---
name: designing-approaches
description: Design 2-3 approaches with tradeoffs — second step of the planning pipeline
allowed-tools: Read, Write, Glob, Grep, Bash, AskUserQuestion, Task, EnterPlanMode
---

# Designing Approaches

## Purpose

Second step of the planning pipeline. Generate and evaluate multiple approaches before committing to one.

## Prerequisites

- Exploration context must exist (from `exploring-codebase` skill)
- If no exploration found in conversation, invoke `Skill("exploring-codebase")` first

## Process

### Step 1: Load Context

Read the exploration artifact from `docs/plans/explore-<topic>.md` or recover from conversation history.

### Step 2: Generate Approaches

Propose 2-3 distinct approaches. For each:

```markdown
### Approach N: <Name>

**Summary**: One sentence description

**How it works**:
1. Step 1
2. Step 2
3. Step 3

**Files to change**:
- `path/to/file.py` — <what changes>

**Effort**: Low | Medium | High
**Risk**: Low | Medium | High
**Tradeoffs**:
- Pro: <advantage>
- Con: <disadvantage>
```

### Step 3: Present for Selection

Use `AskUserQuestion` to present the approaches:
- Lead with the recommended option (add "(Recommended)" label)
- Include clear tradeoff descriptions

### Step 4: Expand Selected Approach

Once user selects, expand into a detailed plan outline:
- Specific files and line ranges
- Implementation order
- Testing strategy
- Migration steps (if applicable)

### Step 5: Save Artifact

Write to `docs/plans/approach-<topic>.md`

## Output Marker

End with: `**Approach Selected: <name>.** Ready for `/plan write`.`
