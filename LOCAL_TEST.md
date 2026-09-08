# gRisk local test profile

This branch adds an explicit local-only Docker Compose profile for testing the full gRisk stack with a repeatable administrator account.

## Start the stack

From the repository root:

```bash
cp .env.example .env
bash scripts/local-test.sh
```

The launcher uses:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

It applies Alembic migrations first, runs a one-shot local administrator bootstrap, waits for the FastAPI and Next.js health checks, and then leaves the complete stack running.

## Local URLs

- Web: `http://localhost:8080`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- API readiness: `http://localhost:8000/api/v1/health/ready`
- Web health: `http://localhost:8080/api/health`

## Local administrator

- Email: `thekoetlisi@ithute.co.ls`
- Password: use the local test password supplied separately.

The repository stores only an Argon2id password hash, never the plaintext local test password. The local bootstrap is guarded by `GRISK_ALLOW_LOCAL_DEFAULT_ADMIN=true` and refuses to run when `GRISK_ENVIRONMENT=production`.

If the local user already exists, the local bootstrap makes it active, restores the `superadmin` role and resets it to the same local test password so repeated local runs stay deterministic.

## Stop the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml down
```

To remove local test data as well:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml down -v
```

Do not use `docker-compose.local.yml` for production deployment. Production continues to use `docker-compose.prod.yml` and explicit production bootstrap credentials.
