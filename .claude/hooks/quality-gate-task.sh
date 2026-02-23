#!/bin/bash
# Quality gate: blocks task completion if type-check or lint fails
# Exit 2 = block + feed stderr back to model
# Exit 0 = allow

INPUT=$(cat)
TASK_SUBJECT=$(echo "$INPUT" | jq -r '.task_subject // empty')

# Skip for non-code tasks
if echo "$TASK_SUBJECT" | grep -qiE "(document|plan|research|explore|investigate|review)"; then
  exit 0
fi

# Check changed TS/JS files
CHANGED_TS=$( (git diff --name-only HEAD 2>/dev/null; git diff --cached --name-only 2>/dev/null) | sort -u | grep -cE '\.(ts|tsx|js|jsx)$' || true)
CHANGED_TS=${CHANGED_TS:-0}
CHANGED_PY=$( (git diff --name-only HEAD 2>/dev/null; git diff --cached --name-only 2>/dev/null) | sort -u | grep -cE '\.py$' || true)
CHANGED_PY=${CHANGED_PY:-0}

# TypeScript check (if tsconfig.json exists and TS files changed)
if [ "$CHANGED_TS" -gt 0 ]; then
  if [ -f "tsconfig.json" ] || [ -f "web/tsconfig.json" ]; then
    if command -v npx &>/dev/null; then
      if ! npx tsc --noEmit > /dev/null 2>&1; then
        echo "Type-check failing. Fix type errors before completing: $TASK_SUBJECT" >&2
        exit 2
      fi
    fi
  fi
fi

# Python lint (if ruff available and Python files changed)
if [ "$CHANGED_PY" -gt 0 ]; then
  PY_DIRS=$( (git diff --name-only HEAD 2>/dev/null; git diff --cached --name-only 2>/dev/null) | sort -u | grep '\.py$' | xargs -I{} dirname {} 2>/dev/null | sort -u)
  RUFF=""
  for VENV_DIR in .venv venv; do
    if [ -x "$VENV_DIR/bin/ruff" ]; then
      RUFF="$VENV_DIR/bin/ruff"
      break
    fi
  done
  [ -z "$RUFF" ] && RUFF=$(command -v ruff 2>/dev/null || true)
  if [ -z "$RUFF" ]; then
    exit 0
  fi

  for PY_DIR in $PY_DIRS; do
    if [ -n "$PY_DIR" ] && [ -d "$PY_DIR" ]; then
      if ! "$RUFF" check "$PY_DIR" --quiet 2>&1; then
        echo "Python lint failing in $PY_DIR. Fix lint errors before completing: $TASK_SUBJECT" >&2
        exit 2
      fi
    fi
  done
fi

exit 0
