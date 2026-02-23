#!/bin/bash
# PreToolUse hook: Block git commits if conflict markers exist in tracked files
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

if echo "$COMMAND" | grep -q 'git commit'; then
  cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
  MARKERS=$(grep -rn -E '^<<<<<<< |^>>>>>>> |^=======$' \
    --include='*.py' --include='*.ts' --include='*.tsx' \
    --include='*.js' --include='*.jsx' --include='*.json' \
    --include='*.yaml' --include='*.yml' \
    --exclude-dir=node_modules --exclude-dir=.git \
    --exclude-dir=dist --exclude-dir=.next \
    --exclude-dir=.venv --exclude-dir=venv \
    --exclude-dir=__tests__ --exclude-dir=tests \
    --exclude-dir=__snapshots__ --exclude-dir=fixtures \
    --exclude='*.test.ts' --exclude='*.test.tsx' \
    --exclude='*.test.py' --exclude='*.spec.ts' . 2>/dev/null)
  if [ -n "$MARKERS" ]; then
    echo "$MARKERS" >&2
    echo "CONFLICT MARKERS FOUND - resolve before committing" >&2
    exit 2
  fi
fi
exit 0
