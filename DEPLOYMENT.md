# gRisk production deployment guide

This guide is the baseline for a single-VPS production deployment of gRisk 1.0. Adapt the hostname, firewall, backup destination and provider integrations to the actual Guardrisk environment.

## 1. Host prerequisites

- current Linux server with Docker Engine and Docker Compose v2
- public DNS record for the production gRisk hostname
- HTTPS reverse proxy such as Caddy, Nginx or Traefik
- firewall allowing only the administration ports you require and public HTTP/HTTPS
- persistent encrypted backup destination outside the VPS
- system clock synchronisation enabled

`docker-compose.prod.yml` keeps PostgreSQL and Redis private. Next.js and FastAPI bind only to `127.0.0.1`, so public traffic must enter through the TLS reverse proxy.

## 2. Production environment

Copy `.env.production.example` to a deployment-only `.env.production` file and replace every `CHANGE_ME` value.

At minimum configure:

```text
POSTGRES_DB=grisk
POSTGRES_USER=<dedicated-database-user>
POSTGRES_PASSWORD=<strong-random-password>
GRISK_DATABASE_URL=postgresql+asyncpg://<url-encoded-user>:<url-encoded-password>@postgres:5432/grisk
GRISK_REDIS_URL=redis://redis:6379/0
GRISK_SECRET_KEY=<cryptographically-random-secret-at-least-32-characters>
GRISK_CORS_ORIGINS=https://grisk.example.com
GRISK_LOGIN_RATE_LIMIT_ATTEMPTS=10
GRISK_LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
GRISK_DOCUMENT_MAX_UPLOAD_MB=20
GRISK_WEB_PORT=8080
GRISK_API_PORT=8000
```

If the database password contains URL-special characters, URL-encode it in `GRISK_DATABASE_URL`. Never commit `.env.production`, database passwords, JWT signing secrets, provider credentials or backup credentials.

The production Compose configuration forces the Next.js authentication cookie to `Secure`; production therefore requires HTTPS.

## 3. Validate configuration before starting

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production config
```

FastAPI production validation rejects weak signing secrets, default `grisk/grisk` database credentials, wildcard CORS, non-HTTPS browser origins and invalid upload limits.

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

The script does not overwrite an existing user. Remove bootstrap credentials from shell history/environment where practical and reset the temporary password through Administration after first sign-in.

## 6. Reverse proxy and TLS

Use one public HTTPS hostname for the web application and realtime WebSockets. A matching example is provided in `Caddyfile.example`.

Routing requirements:

```text
https://grisk.example.com/ws/*   -> 127.0.0.1:8000  (FastAPI WebSocket upgrade)
https://grisk.example.com/*      -> 127.0.0.1:8080  (Next.js)
```

Normal browser API traffic goes through the Next.js BFF (`/api/session/*` and `/api/proxy/*`). The FastAPI access token is held in an **HttpOnly, SameSite=Strict, Secure** cookie and is never stored in browser local/session storage. The BFF injects the bearer token server-side.

Production WebSockets also authenticate from that HttpOnly cookie and enforce the configured HTTPS origin. Do not put access tokens in production WebSocket query strings.

Do not route `/api/v1/auth/login` directly to the public internet and do not expose PostgreSQL or Redis publicly.

## 7. Health and observability

Application checks:

```text
GET /api/health                     Next.js liveness
GET /api/v1/health/live             FastAPI liveness
GET /api/v1/health/ready            FastAPI + PostgreSQL + Redis readiness
```

FastAPI readiness returns HTTP 503 when a required backend dependency is unavailable. Every FastAPI HTTP response includes `X-Request-ID`; request logs contain request ID, method, path, status and duration without request bodies or passwords.

Next.js and FastAPI both apply defensive browser/security headers. Production API docs are disabled.

## 8. Database migrations

Alembic is mandatory for every application schema change. The production Compose stack runs a one-shot migration container before the API starts.

Check current state:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm api \
  python -m alembic current
```

Apply manually when required:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm api \
  python -m alembic upgrade head
```

Do not use ad-hoc SQL to modify production application tables.

## 9. Backups

The authoritative durable data is split between PostgreSQL and the `grisk_documents` Docker volume. Back up both.

Example PostgreSQL logical backup:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > grisk-$(date +%F-%H%M).dump
```

Example document-volume archive:

```bash
docker run --rm \
  -v grisk_grisk_documents:/source:ro \
  -v "$PWD/backups":/backup \
  alpine sh -c 'tar czf /backup/grisk-documents-$(date +%F-%H%M).tgz -C /source .'
```

The exact Docker volume name may differ if a custom Compose project name is used; confirm it with `docker volume ls`.

Schedule encrypted daily backups, retain multiple generations and keep at least one copy outside the application VPS. Redis is not the system of record.

## 10. Restore drill

Restore testing must be performed in a non-production environment on a regular schedule.

For PostgreSQL, restore the selected dump into a prepared database and then verify Alembic state:

```bash
cat grisk-backup.dump | docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists

docker compose -f docker-compose.prod.yml --env-file .env.production run --rm api \
  python -m alembic current
```

Restore the document archive into the document volume before reopening application traffic. Always rehearse the exact commands with the real backup destination and retention process.

## 11. Release checklist

Before promoting `development` to `main`:

- backend CI green: Ruff, Alembic upgrade/check/rollback, Pytest
- Next.js typecheck and production build green
- full Docker Compose/container smoke validation green
- production Compose validates with the real environment file
- production database and document backups captured before migration/deployment
- HTTPS reverse proxy configured with `/ws/*` routed to FastAPI and all other traffic to Next.js
- login/session, customer search, quotation/policy, claims, Medical Aid, finance, documents, reports and Administration smoke-tested
- health checks green after deployment
- no bootstrap, database, JWT or provider secrets stored in source control
- restore procedure has a named owner and a recent successful drill

## 12. Rollback

Application rollback and database rollback are separate decisions.

For an application-only regression where database changes are backward compatible, redeploy the previous known-good image/commit.

For migration-related rollback, inspect the specific Alembic revision before downgrading. Never automatically downgrade production when a revision may remove or transform data. Restore from a verified backup when data preservation requires it.

## 13. External integrations

The production platform includes a strategic-partner/integration registry, but insurer, bank/payment, SMS, WhatsApp, email and medical-provider connections are provider-specific. Enable each one only after Guardrisk supplies and approves:

- provider name and API documentation
- authentication method
- sandbox/test credentials
- callback/webhook requirements
- production endpoints
- data fields and reconciliation rules
- retry/idempotency expectations
- provider security and operational contacts

Do not invent production endpoints or put provider credentials in the repository. Use deployment secret injection and test each provider in its sandbox before activation.
