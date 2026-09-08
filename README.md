# gRisk

Guardrisk operating platform built with **Next.js + FastAPI + PostgreSQL + Redis + WebSockets**.

## Architecture

- `apps/web` — Next.js App Router frontend
- `apps/api` — FastAPI backend and business rules
- PostgreSQL — system of record
- Redis — cache, realtime/event infrastructure and background-work foundation
- Alembic — mandatory PostgreSQL schema and controlled reference-data migrations
- Docker Compose — local/application stack
- GitHub Actions — path-filtered backend and frontend validation

The browser talks to FastAPI through the Next.js `/api/proxy/*` route. The Next.js server uses `API_BASE_URL` at runtime, so the frontend image does not need an API URL baked into the browser bundle.

## Current delivery status

### Phase 1 — Foundation

Authentication, roles, audit logging, PostgreSQL/Redis connectivity, Docker and CI.

### Phase 2 — CRM

Customer management for individuals and companies, including the backend foundation for contacts, addresses and notes.

### Phase 3 — Insurance quotations and policies

Insurance products, quotation workflow, quote-to-policy conversion, policy register, audit events and realtime events.

### Phase 4 — Claims

In active development on `feature/phase-4-claims`:

- claim registration against a policy
- policy-cover incident-date validation
- claim triage and controlled status transitions
- assessment, insurer review, approval, settlement and closure
- approved-amount controls
- internal claim notes and timeline events
- audit and realtime claim events
- responsive Next.js claims workspace

## Frontend

The active frontend is Next.js. Blazor is no longer used by Docker or GitHub Actions.

Run it locally:

```bash
cd apps/web
npm install
API_BASE_URL=http://localhost:8000 npm run dev
```

The Next.js development server listens on `http://localhost:3000`.

## Database migrations

Alembic is mandatory for every PostgreSQL schema change. Do not create, alter or drop application tables manually in production.

Current migration chain:

1. `20260907_0001_core_identity`
2. `20260907_0002_crm_customers`
3. `20260907_0003_insurance_quotes`
4. `20260907_0004_seed_general_insurance_products`
5. `20260907_0005_align_unique_constraints`
6. `20260907_0006_claims`

Apply migrations from `apps/api`:

```bash
python -m alembic upgrade head
```

Backend CI validates:

```bash
python -m ruff check app tests
python -m alembic upgrade head
python -m alembic check
python -m alembic downgrade -1
python -m alembic upgrade head
python -m pytest -q
```

## GitHub Actions usage

CI is deliberately split to reduce hosted-runner usage:

- backend CI runs only when `apps/api/**` changes
- Next.js CI runs only when `apps/web/**` changes
- Docker image validation is manual through `workflow_dispatch`
- concurrency cancellation stops older runs when a newer commit supersedes them

This keeps expensive .NET restore/build work out of the project and avoids building Docker images on every pull request.

## Docker Compose

```bash
docker compose up --build
```

- Web: `http://localhost:8080`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Development workflow

```text
feature/* -> development -> main
```

Feature work is merged only after the relevant GitHub Actions checks pass.
