---
name: responding-to-pr-feedback
description: Read PR review feedback, implement fixes, push updates
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Responding to PR Feedback

## Process

### Step 1: Identify PR

```bash
gh pr view --json number,title,url,reviewDecision
```

### Step 2: Gather Feedback

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments
gh pr view <number> --json reviews
```

### Step 3: Categorize Comments

For each comment, categorize:
- **Code fix** — Specific change requested
- **Bug report** — Reviewer found a bug
- **Style** — Formatting or naming suggestion
- **Architecture** — Design concern
- **Question** — Needs clarification (reply, don't code)

### Step 4: Implement Fixes

Use `Skill("superpowers:receiving-code-review")` for discipline — don't blindly implement, verify each suggestion is correct.

### Step 5: Validate

Run quality checks after fixes.

### Step 6: Push and Reply

```bash
git push
```

Reply to each comment explaining what was done.

### Step 7: Report

Summary of addressed comments and any disagreements.
