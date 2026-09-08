# gRisk Web

The active gRisk frontend is Next.js App Router with TypeScript.

## Local development

```bash
npm install
API_BASE_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000.

Browser API calls use `/api/proxy/*`; the Next.js server forwards them to `API_BASE_URL`. Authentication tokens remain in browser `sessionStorage`, matching the previous Blazor session behavior.
