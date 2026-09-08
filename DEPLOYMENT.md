# gRisk production deployment guide

This guide is the baseline for a single-VPS Docker Compose deployment. Adapt hostnames, firewall rules, backup destinations and provider integrations to the actual Guardrisk environment.

## 1. Host prerequisites

- current Linux server with Docker Engine and Docker Compose v2
- HTTPS reverse proxy in front of the Next.js service
- DNS for the production gRisk hostname
- firewall allowing only SSH administration and public HTTP/HTTPS as required
- persistent encrypted backup destination outside the VPS
- system clock synchronisation enabled

PostgreSQL and Redis should remain private to the Docker network. The production Compose file does not publish their ports.

## 2. Production environment

Create `.env.production` outside source control. At minimum provide:

```text
POSTGRES_DB=grisk
POSTGRES_USER=<dedicated-database-user>
POSTGRES_PASSWORD=<strong-random-password>
GRISK_DATABASE_URL=postgresql+asyncpg://<user>:<password>@postgres:5432/grisk
GRISK_REDIS_URL=redis://redis:6379/0
GRISK_SECRET_KEY=<cryptographically-random-secret-at-least-32-characters>
GRISK_CORS_ORIGINS=https://grisk.example.com
GRISK_LOGIN_RATE_LIMIT_ATTEMPTS=10
GRISK_LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
GRISK_WEB_PORT=8080
```

Never commit `.env.production`, database passwords, JWT signing secrets or provider credentials.

## 3. Validate configuration before starting

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production config
```

The FastAPI production configuration also rejects weak signing secrets, the development database URL, wildcard CORS and non-HTTPS browser origins.

## 4. Build and start

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Startup order is:

```text
PostgreSQL + Redis healthy
        |
        v
Alembic migration service completes
        |
        v
FastAPI readiness becomes healthy
        |
        v
Next.js starts and becomes healthy
```

Inspect status:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

## 5. Bootstrap the first superuser

Only for initial provisioning:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm \
  -e GRISK_BOOTSTRAP_ADMIN_EMAIL=admin@example.com \
  -e GRISK_BOOTSTRAP_ADMIN_PASSWORD='use-a-strong-temporary-password' \
  api python -m app.scripts.bootstrap_admin
```

The script does not overwrite an existing user. Remove bootstrap credentials from shell history/environment where practical and change the temporary password through the administration workflow.

## 6. Reverse proxy and TLS

Expose the Next.js service through an HTTPS reverse proxy. Proxy normal HTTP traffic to the configured gRisk web port. FastAPI is reached server-to-server through the Next.js `/api/proxy/*` route.

If realtime WebSockets are exposed through a reverse proxy, ensure WebSocket upgrade headers are forwarded. gRisk WebSocket connections require an access token and portal users can only subscribe to their own notification channel.

Do not expose PostgreSQL or Redis publicly.

## 7. Health checks

Application checks:

```text
GET /api/health                     Next.js liveness
GET /api/v1/health/live             FastAPI liveness
GET /api/v1/health/ready            FastAPI + PostgreSQL + Redis readiness
```

The readiness endpoint returns HTTP 503 when a required backend dependency is unavailable.

Every FastAPI HTTP response includes `X-Request-ID`. Server request logs contain request ID, method, path, response status and duration without request bodies.

## 8. Database migrations

Alembic is mandatory.

Check current migration state inside the API image:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm api \
  python -m alembic current
```

Apply migrations manually when required:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm api \
  python -m alembic upgrade head
```

Do not use ad-hoc SQL to modify the application schema.

## 9. Backup baseline

At minimum, schedule encrypted daily PostgreSQL backups and retain more than one generation. Keep a copy outside the application VPS.

Example logical backup:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > grisk-$(date +%F-%H%M).dump
```

Back up any future object/document storage independently. Redis is not the system of record and should not be treated as the authoritative backup source.

Test restore procedures periodically on a non-production environment.

## 10. Restore drill

For a controlled restore, stop application writes, create a fresh PostgreSQL database/container, restore the selected dump, then run Alembic to confirm the restored schema is at the expected revision before opening traffic.

Example restore into a prepared database:

```bash
cat grisk-backup.dump | docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists
```

Always rehearse the exact restore command with your real backup process before relying on it for disaster recovery.

## 11. Release checklist

Before promoting `development` to `main`:

- backend CI green: Ruff, Alembic upgrade/check/rollback, Pytest
- Next.js typecheck/build green
- manual Docker Compose/container build validation green
- production environment validated with `docker compose config`
- database backup captured before applying production migrations
- health checks green after deployment
- login, customer search, quotation/policy, claim, medical, finance, reports and administration smoke-tested
- no bootstrap or provider secrets left in source control or command files

## 12. Rollback approach

Application rollback and database rollback are separate decisions.

For application-only regressions where the database migration is backward-compatible, redeploy the previous known-good image/commit.

For a migration-related rollback, review the specific Alembic revision before running a downgrade. Never downgrade production automatically without confirming whether the downgrade removes or transforms data. Restore from a verified backup when data preservation requires it.

## 13. External integrations

Insurer, payment/bank, SMS, WhatsApp, email and medical-provider connections are provider-specific. Add them only when Guardrisk has confirmed:

- provider name and API documentation
- authentication method
- sandbox/test credentials
- callback/webhook requirements
- production endpoints
- data fields and reconciliation rules
- expected retry/idempotency behaviour

Do not place provider credentials in the repository. Use deployment secrets/environment injection.
