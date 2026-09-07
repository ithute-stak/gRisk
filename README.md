# gRisk

Guardrisk operating platform built with **Blazor WebAssembly + FastAPI + PostgreSQL + Redis + WebSockets**.

## Architecture

- `apps/web` — Blazor WebAssembly frontend
- `apps/api` — FastAPI backend and business rules
- PostgreSQL — system of record
- Redis — cache, realtime/event infrastructure and background-work foundation
- Alembic — mandatory PostgreSQL schema and controlled reference-data migrations
- Docker Compose — local/application stack
- GitHub Actions — backend, migration, frontend and container validation

## Current delivery status

### Phase 1 — Foundation

Completed foundation includes authentication, roles, audit logging, PostgreSQL/Redis connectivity, Docker and CI.

### Phase 2 — CRM

Customer management is available for individuals and companies, including contacts, addresses, notes, search and audit events.

### Phase 3 — Insurance quotations and policies

In active development on `feature/phase-3-insurance`:

- insurance products
- quotations and quote items
- quote approval/status workflow
- quote-to-policy conversion
- policies
- realtime quotation/policy events
- responsive Blazor quotation and policy workspaces
- seeded Guardrisk general-insurance products

## Database migrations

Alembic is mandatory for every PostgreSQL schema change. Do not create, alter or drop application tables manually in production. Reference data that must exist consistently in every environment can also be delivered through a reviewed Alembic migration.

Current migration chain:

1. `20260907_0001_core_identity`
2. `20260907_0002_crm_customers`
3. `20260907_0003_insurance_quotes`
4. `20260907_0004_seed_general_insurance_products`

Apply migrations from `apps/api`:

```bash
python -m alembic upgrade head
```

CI validates the migration chain with:

```bash
python -m alembic upgrade head
python -m alembic check
python -m alembic downgrade -1
python -m alembic upgrade head
```

This catches unapplied model drift and basic migration rollback/forward failures before merge.

## Development workflow

```text
feature/* -> development -> main
```

Feature work is merged only after the GitHub Actions checks pass.
