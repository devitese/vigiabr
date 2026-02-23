#!/bin/bash
# Quality gate for TeammateIdle: prevents teammate from going idle if lint fails

INPUT=$(cat)
TEAMMATE=$(echo "$INPUT" | jq -r '.teammate_name // empty')

CHANGED_TS=$( (git diff --name-only HEAD 2>/dev/null; git diff --cached --name-only 2>/dev/null) | sort -u | grep -cE '\.(ts|tsx|js|jsx)$' || echo "0")

if [ "$CHANGED_TS" -gt 0 ]; then
  if [ -f "tsconfig.json" ] || [ -f "web/tsconfig.json" ]; then
    if command -v npx &>/dev/null; then
      if ! npx tsc --noEmit > /dev/null 2>&1; then
        echo "Type-check failing. $TEAMMATE: fix type errors before stopping." >&2
        exit 2
      fi
    fi
  fi
fi

exit 0
