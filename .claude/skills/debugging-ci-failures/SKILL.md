---
name: debugging-ci-failures
description: Automatically diagnose GitHub Actions CI workflow failures
allowed-tools: Read, Bash, Glob, Grep
---

# Debugging CI Failures

## Process

### Step 1: Fetch Logs

```bash
# List recent workflow runs
gh run list --limit 5

# Get failed run details
gh run view <run-id>
gh run view <run-id> --log-failed
```

### Step 2: Parse Error Patterns

Look for common patterns:

| Pattern | Category |
|---------|----------|
| `error TS` | TypeScript compilation |
| `FAILED tests/` | Python test failure |
| `ruff check` | Python lint failure |
| `ModuleNotFoundError` | Missing dependency |
| `ImportError` | Import issue |
| `Connection refused` | Service not ready |
| `npm ERR!` | Node.js dependency issue |
| `docker` errors | Container/build issue |

### Step 3: Identify Root Cause

1. Read the failed job/step logs
2. Cross-reference with recent code changes: `git log --oneline -5`
3. Check if the failure is in changed code or pre-existing

### Step 4: Suggest Fixes

Provide:
- Root cause explanation
- Specific fix commands
- Quick actions via `AskUserQuestion`:
  1. "Fix it now" — Apply the fix
  2. "Show me the code" — Display the problematic code
  3. "Skip for now" — Move on

## Common Failures

### Python
- Missing imports → add to requirements
- Type errors → fix annotations
- Test failures → read assertion output

### TypeScript
- Type errors → fix type definitions
- Module not found → check imports/tsconfig
- Build errors → check Next.js config

### Infrastructure
- Docker build fails → check Dockerfile
- Service timeout → check health checks
- Permission denied → check file permissions
