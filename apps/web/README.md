# gRisk Web

The active gRisk frontend is **Next.js App Router + React + TypeScript**.

## Local development

```bash
npm install
API_BASE_URL=http://localhost:8000 GRISK_COOKIE_SECURE=false npm run dev
```

Open `http://localhost:3000`.

Browser API calls use `/api/proxy/*`; the Next.js server forwards them to the FastAPI `API_BASE_URL`. Authentication uses a server-managed **HttpOnly, SameSite=Strict session cookie**. The FastAPI bearer token is never written to browser `localStorage` or `sessionStorage`; only non-sensitive display identity is cached client-side for the navigation shell.

The frontend includes operational workspaces for customers, quotations, policies, claims, Medical Aid, bonds, risk, finance, documents, partners, notifications, customer portal, management reports and superuser administration.

## Validation

```bash
npm run typecheck
npm run build
```

The container exposes `GET /api/health` for health checks. Production must set `GRISK_COOKIE_SECURE=true` and be served behind HTTPS.
