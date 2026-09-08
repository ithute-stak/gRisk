#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="grisk-local-test"
COMPOSE=(docker compose -p "$PROJECT_NAME" -f docker-compose.yml -f docker-compose.local.yml)
LEGACY_COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.local.yml)

if [[ "${1:-}" == "--reset" ]]; then
  echo "Resetting the isolated gRisk local-test stack and its test volumes..."
  "${COMPOSE[@]}" down -v --remove-orphans || true
fi

# Stop any stack previously started without the explicit local-test project name.
# Volumes are intentionally preserved; the isolated project below gets its own clean volumes.
"${LEGACY_COMPOSE[@]}" down --remove-orphans >/dev/null 2>&1 || true

echo "Starting gRisk local test stack using isolated Docker project: $PROJECT_NAME"
if ! "${COMPOSE[@]}" up -d --build; then
  echo >&2
  echo "gRisk startup failed. Current service state:" >&2
  "${COMPOSE[@]}" ps >&2 || true
  echo >&2
  echo "Migration logs:" >&2
  "${COMPOSE[@]}" logs --no-color migrate >&2 || true
  echo >&2
  echo "If this is a stale local-test database, retry with:" >&2
  echo "  bash scripts/local-test.sh --reset" >&2
  exit 1
fi

echo "Waiting for gRisk health checks..."
for attempt in $(seq 1 45); do
  if curl --fail --silent http://localhost:8080/api/health >/dev/null 2>&1 \
    && curl --fail --silent http://localhost:8000/api/v1/health/ready >/dev/null 2>&1; then
    echo "gRisk is ready."
    echo "Web:      http://localhost:8080"
    echo "API docs: http://localhost:8000/docs"
    echo "Login:    thekoetlisi@ithute.co.ls"
    echo "Password: use the local test password supplied separately; it is not stored in plaintext in Git."
    exit 0
  fi
  sleep 2
done

echo "gRisk did not become healthy within 90 seconds." >&2
"${COMPOSE[@]}" ps >&2 || true
echo >&2
echo "Migration logs:" >&2
"${COMPOSE[@]}" logs --no-color migrate >&2 || true
echo >&2
echo "API logs:" >&2
"${COMPOSE[@]}" logs --no-color --tail=120 api >&2 || true
echo >&2
echo "Web logs:" >&2
"${COMPOSE[@]}" logs --no-color --tail=120 web >&2 || true
exit 1
