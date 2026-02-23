#!/bin/bash
# Cleanup stray CLAUDE.md files created by claude-mem plugin.

cd "$CLAUDE_PROJECT_DIR" || exit 0

# Find untracked CLAUDE.md files and delete them
git status --porcelain 2>/dev/null | grep '^??' | grep 'CLAUDE\.md$' | while IFS= read -r line; do
  file="${line#\?\? }"
  dir="$(dirname "$file")"

  case "$dir" in
    .|.claude|.claude/skills/*) continue ;;
  esac

  rm -f "$file" 2>/dev/null
done

# Find untracked directories that only contain CLAUDE.md files
git status --porcelain 2>/dev/null | grep '^??' | grep '/$' | while IFS= read -r line; do
  dir="${line#\?\? }"
  dir="${dir%/}"

  case "$dir" in
    .claude|.claude/*) continue ;;
  esac

  real_files=$(find "$dir" -type f -not -name "CLAUDE.md" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$real_files" -eq 0 ]; then
    rm -rf "$dir" 2>/dev/null
  fi
done

exit 0
