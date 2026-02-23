#!/bin/bash
# SubagentStart: inject project context into every subagent

INPUT=$(cat)
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // empty')

CONTEXT="Project: VigiaBR — transparency monitoring platform for Brazilian public officials (Python/Scrapy + FastAPI + Next.js + Neo4j + PostgreSQL). Branch from develop, PRs target develop. Never push to main."

case "$AGENT_TYPE" in
  git-operator)
    CONTEXT="$CONTEXT Git rules: PRs always --base develop. Never force push main. Always backup before destructive ops. Use GitHub Issues (not Linear)."
    ;;
  codebase-analyzer|codebase-explorer|Explore)
    CONTEXT="$CONTEXT Key dirs: scrapers/ (Python/Scrapy spiders), dags/ (Airflow DAGs), api/ (FastAPI backend), web/ (Next.js frontend), graph/ (Neo4j/Cypher queries)."
    ;;
  plan-executor)
    CONTEXT="$CONTEXT Execute precisely. Python: ruff check + mypy. TypeScript: tsc --noEmit. Always verify after edits. All PII (CPF) must be SHA-256 hashed."
    ;;
esac

jq -n --arg ctx "$CONTEXT" '{
  hookSpecificOutput: {
    hookEventName: "SubagentStart",
    additionalContext: $ctx
  }
}' 2>/dev/null

exit 0
