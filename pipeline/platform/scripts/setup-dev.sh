#!/usr/bin/env bash
# VigiaBR — One-command local dev setup
# Usage: ./scripts/setup-dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PLATFORM_DIR/docker"
ENV_FILE="$DOCKER_DIR/.env"

echo "=== VigiaBR Dev Setup ==="
echo ""

# Check dependencies
for cmd in docker uv; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: '$cmd' is required but not installed."
        exit 1
    fi
done

if ! docker compose version &>/dev/null; then
    echo "ERROR: 'docker compose' plugin is required."
    exit 1
fi

# Create .env if missing
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating $ENV_FILE with defaults..."
    cat > "$ENV_FILE" <<'ENVEOF'
# VigiaBR — Local development environment variables
PG_USER=vigiabr
PG_PASSWORD=vigiabr
PG_DB=vigiabr
PG_PORT=5432

NEO4J_USER=neo4j
NEO4J_PASSWORD=vigiabr
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687

AIRFLOW_DB_USER=airflow
AIRFLOW_DB_PASSWORD=airflow
AIRFLOW_DB_NAME=airflow
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin
AIRFLOW_PORT=8080

GRAFANA_USER=admin
GRAFANA_PASSWORD=vigiabr
GRAFANA_PORT=3000

PROMETHEUS_PORT=9090
ENVEOF
    echo ".env created."
else
    echo ".env already exists, skipping."
fi

# Start services
echo ""
echo "Starting Docker services..."
cd "$DOCKER_DIR"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Wait for health
echo ""
echo "Waiting for services to become healthy..."

wait_for_service() {
    local service="$1"
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps "$service" 2>/dev/null | grep -q "healthy"; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    echo "WARNING: $service did not become healthy within timeout"
    return 1
}

wait_for_service "postgres" || true
wait_for_service "neo4j" || true

# Print URLs
echo ""
echo "=== VigiaBR Services ==="
echo "PostgreSQL:  localhost:${PG_PORT:-5432}"
echo "Neo4j:       http://localhost:${NEO4J_HTTP_PORT:-7474}"
echo "Airflow:     http://localhost:${AIRFLOW_PORT:-8080}  (admin/admin)"
echo "Grafana:     http://localhost:${GRAFANA_PORT:-3000}   (admin/vigiabr)"
echo "Prometheus:  http://localhost:${PROMETHEUS_PORT:-9090}"
echo ""
echo "To stop: cd $DOCKER_DIR && docker compose -f docker-compose.yml -f docker-compose.dev.yml down"
