#!/bin/bash
# PostToolUse hook: Syntax-check Python files after Edit/Write
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path')

if [ "$FILE" != "null" ] && [ -n "$FILE" ] && echo "$FILE" | grep -q '\.py$'; then
  ERRORS=$(python3 -m py_compile "$FILE" 2>&1)
  if [ $? -ne 0 ]; then
    echo "Python syntax error in $FILE:" >&2
    echo "$ERRORS" >&2
    exit 2
  fi
fi
exit 0
