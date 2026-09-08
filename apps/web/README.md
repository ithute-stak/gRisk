# gRisk Web

The active gRisk frontend is **Next.js App Router + React + TypeScript**.

## Local development

```bash
npm install
API_BASE_URL=http://localhost:8000 npm run dev
```

Open `http://localhost:3000`.

Browser API calls use `/api/proxy/*`; the Next.js server forwards them to the FastAPI `API_BASE_URL`. The frontend includes operational workspaces for customers, quotations, policies, claims, Medical Aid, bonds, risk, finance, notifications, customer portal, management reports and superuser administration.

## Validation

```bash
npm run typecheck
npm run build
```

The container exposes `GET /api/health` for health checks.
