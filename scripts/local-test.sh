#!/usr/bin/env bash
set -euo pipefail

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.local.yml)

echo "Starting gRisk local test stack..."
"${COMPOSE[@]}" up -d --build

echo "Waiting for gRisk health checks..."
for attempt in $(seq 1 30); do
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

echo "gRisk did not become healthy within 60 seconds." >&2
"${COMPOSE[@]}" ps >&2
exit 1
