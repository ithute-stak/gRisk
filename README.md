# gRisk

gRisk is the Guardrisk operating platform built with **Next.js + FastAPI + PostgreSQL + Redis + WebSockets**.

## Release status

The current release line is **gRisk 1.0**. The core Guardrisk operating modules are implemented:

- authentication, staff roles and audit logging
- CRM and customer management
- insurance products, quotations and policies
- general insurance claims
- Medical Aid, dependants, benefits, prior authorisations and medical claims
- Health Cash Plan foundations
- bonds and guarantees
- enterprise risk assessments and risk registers
- finance, invoices and payments
- notifications and customer portal access
- management reporting
- superuser administration
- operational health, request IDs and structured request logging

Provider-specific insurer, bank/payment, SMS, WhatsApp, email and medical-provider integrations are intentionally not hard-coded. They require confirmed provider APIs and credentials.

## Architecture

```text
Browser
  |
  v
Next.js 16 / React
  |  /api/proxy/*
  v
FastAPI 1.0 application
  |-------------------|
  v                   v
PostgreSQL           Redis
(system of record)   cache/rate-limit/realtime foundation
```

Repository layout:

```text
apps/web        Next.js frontend
apps/api        FastAPI backend, Alembic migrations and tests
docker-compose.yml       local/development stack
docker-compose.prod.yml  production-oriented stack
```

The browser does not connect directly to PostgreSQL or Redis. Business rules remain in FastAPI.

## Security model

- passwords are hashed with the configured `pwdlib` Argon2 implementation
- JWT access tokens are issuer/audience validated
- inactive users are rejected on authenticated API requests
- portal-only users cannot access internal operational APIs
- viewer accounts are read-only
- operational writes are role-restricted by module
- superuser administration is separately protected
- login attempts are rate-limited through Redis
- production rejects weak JWT secrets, default database credentials, wildcard CORS and non-HTTPS CORS origins
- API responses receive no-store/security headers and request IDs
- WebSocket channels require authentication; customer accounts can only subscribe to their own notification channel
- client WebSocket messages are not rebroadcast into operational channels

Core staff roles seeded by Alembic are `superadmin`, `admin`, `broker`, `claims`, `medical`, `finance`, `risk` and `viewer`.

## Database migrations

**Alembic is mandatory for every PostgreSQL schema change.** Do not manually alter production application tables.

Current migration chain:

1. `20260907_0001_core_identity.py`
2. `20260907_0002_crm_customers.py`
3. `20260907_0003_insurance_quotes.py`
4. `20260907_0004_seed_general_insurance_products.py`
5. `20260907_0005_align_unique_indexes.py`
6. `20260907_0006_claims.py`
7. `20260908_0007_medical_aid.py`
8. `20260908_0008_seed_medical_plans.py`
9. `20260908_0009_align_medical_unique_indexes.py`
10. `20260908_0010_bonds_risk.py`
11. `20260908_0011_finance_notifications_portal.py`

From `apps/api`:

```bash
python -m alembic upgrade head
```

CI validates upgrade, model/migration drift, one-step rollback/upgrade and the backend test suite.

## Local development

Copy the example environment file and start the complete stack:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Web: `http://localhost:8080`
- API: `http://localhost:8000`
- API docs in non-production: `http://localhost:8000/docs`
- API readiness: `http://localhost:8000/api/v1/health/ready`
- Web health: `http://localhost:8080/api/health`

Docker Compose runs an explicit one-shot `migrate` service before FastAPI starts.

## Bootstrap the first administrator

After migrations are applied, set strong temporary bootstrap credentials in your environment and run:

```bash
docker compose run --rm \
  -e GRISK_BOOTSTRAP_ADMIN_EMAIL=admin@example.com \
  -e GRISK_BOOTSTRAP_ADMIN_PASSWORD='replace-with-a-strong-temporary-password' \
  api python -m app.scripts.bootstrap_admin
```

The command creates the account only when it does not already exist. Remove bootstrap credentials from the environment after first provisioning.

## Production deployment

Use the production Compose file as the baseline:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production config
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Production requires explicit PostgreSQL credentials, `GRISK_DATABASE_URL`, a strong `GRISK_SECRET_KEY` and HTTPS CORS origins. PostgreSQL and Redis are not published to host ports by the production Compose file.

See `DEPLOYMENT.md` for the deployment, backup, health-check and rollback checklist.

## GitHub Actions

Hosted CI is deliberately conservative to reduce Actions consumption:

- backend CI is path-filtered
- Next.js CI is path-filtered
- full Docker image validation is manual
- superseded runs are cancelled through workflow concurrency

Before merging a release candidate, run the relevant backend and frontend gates and the manual container validation once.

## Development workflow

```text
feature/* -> development -> main
```

Feature work is merged only after the relevant checks pass. `main` is reserved for release-ready code.
