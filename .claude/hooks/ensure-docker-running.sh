#!/usr/bin/env bash
# PreToolUse hook: auto-start Docker Desktop when docker commands are detected

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if ! echo "$COMMAND" | grep -qiE '(docker compose|docker-compose|docker build|docker exec|docker logs|docker ps)'; then
  exit 0
fi

if docker info >/dev/null 2>&1; then
  exit 0
fi

echo "Docker daemon not running. Starting Docker Desktop..." >&2
open -a Docker

MAX_WAIT=60
WAITED=0
while ! docker info >/dev/null 2>&1; do
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    echo "BLOCK: Docker Desktop failed to start within ${MAX_WAIT}s. Start it manually." >&2
    exit 1
  fi
  sleep 2
  WAITED=$((WAITED + 2))
done

echo "Docker Desktop started successfully (waited ${WAITED}s)." >&2
exit 0
