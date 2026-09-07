# gRisk

gRisk is the Guardrisk integrated insurance, medical aid, claims, bonds, risk-management and customer-service platform.

## Target architecture

- **Frontend:** Blazor WebAssembly
- **Backend:** FastAPI
- **Database:** PostgreSQL
- **Cache / jobs / realtime coordination:** Redis
- **Realtime:** WebSockets
- **Authentication:** JWT/OIDC-ready
- **Document storage:** S3-compatible object storage
- **Deployment:** Docker + VPS + GitHub Actions

## Planned modules

1. Platform foundation, authentication, roles, audit and infrastructure
2. CRM and customer management
3. Quotations and policy administration
4. Claims management
5. Medical aid and health cash plan
6. Bonds, guarantees and risk management
7. Finance, notifications and customer/employer portals
8. Reporting, integrations, hardening and production release

## Repository layout

```text
apps/
  web/        # Blazor WebAssembly frontend
  api/        # FastAPI backend
  worker/     # background jobs
infra/        # Docker and deployment configuration
docs/         # architecture and product documentation
```

Development work is performed on the `development` branch and promoted to `main` after validation.
