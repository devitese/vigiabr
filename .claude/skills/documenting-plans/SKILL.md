---
name: documenting-plans
description: Write comprehensive plan document — final step of the planning pipeline
allowed-tools: Read, Write, Glob, Grep, Bash, Skill
---

# Documenting Plans

## Purpose

Final step of the planning pipeline. Produce a complete implementation plan document.

## Prerequisites

- Exploration context (from `exploring-codebase`)
- Selected approach (from `designing-approaches`)

## Process

### Step 1: Gather Inputs

Read exploration and approach artifacts from `docs/plans/`.

### Step 2: Write Plan Document

Save to `docs/plans/YYYY-MM-DD-<topic>.md` with structure:

```markdown
# <Feature Name> Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** <one sentence>
**Architecture:** <2-3 sentences>
**Tech Stack:** <key technologies>

---

## Context
<Summary from exploration>

## Selected Approach
<From designing-approaches, with rationale>

## Alternatives Considered
<Brief summary of rejected approaches and why>

## Implementation Tasks

### Task 1: <Component>
**Files:** ...
**Steps:** ...
**Tests:** ...

### Task 2: ...

## Test Plan
<What to test and how>

## Risks and Mitigations
<From exploration, updated>
```

### Step 3: Commit

```bash
git add docs/plans/YYYY-MM-DD-<topic>.md
git commit -m "docs: add implementation plan for <topic>"
```

## Output Marker

End with: `**Plan Approved.** Ready for implementation.`
