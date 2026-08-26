# Project Command Center

## Open Nehal's dashboard

Double-click `افتح-داشبورد-نهال.cmd` or `start-dashboard.cmd` to start and open Nehal's private editable dashboard. It needs no Docker.

Use `Leader View.url` to open the separate read-only dashboard shared with the leader.

A production-oriented project-management monorepo that normalizes Odoo and Google Sheets work into PostgreSQL, exposes it through FastAPI, and presents it in a responsive Next.js dashboard. It includes JWT authentication, deadline intelligence, capacity planning, notifications, activity history, sync logs, conflict records, Celery scheduling, and real external-client implementations (no seeded business data).

## Architecture

- `frontend/`: Next.js 15, React 19, TypeScript, Tailwind, TanStack Query
- `backend/`: FastAPI, Pydantic, SQLAlchemy, Alembic
- PostgreSQL: normalized system of record
- Redis/Celery: periodic integration synchronization (five minutes by default)
- Odoo: XML-RPC `/xmlrpc/2/common` and `/xmlrpc/2/object`
- Google: OAuth 2.0 and Sheets API v4

## Quick start with Docker

1. Copy `.env.example` to `.env` and replace every security placeholder.
2. Add Odoo and Google credentials if those integrations will be enabled.
3. Run `docker compose up --build`.
4. Open the UI at `http://localhost:3000`, API docs at `http://localhost:8000/docs`, and health check at `http://localhost:8000/health`.
5. Create the first user from the UI. No demo data is inserted.

For a production deployment, terminate TLS at a reverse proxy, set `FRONTEND_URL` to the exact HTTPS origin, use managed PostgreSQL/Redis with backups, rotate all secrets, and run `alembic upgrade head` before the API is promoted.

## Local development

Python 3.12 and Node 22 are recommended.

```bash
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Run backend tests with `pytest backend/tests -q`; validate the frontend with `npm run build` in `frontend/`.

## Odoo setup

Create a dedicated Odoo service user with read/write access only to Projects, Tasks, Contacts, Users, and project stages. Set `ODOO_URL`, `ODOO_DATABASE`, `ODOO_USERNAME`, and `ODOO_PASSWORD` (an API key may be used as the password on supported editions). The connector uses Odoo's supported XML-RPC API, reads stable external IDs, and builds direct record URLs. Test the connection through `POST /api/integrations/odoo/test`.

## Google Cloud and Sheets setup

1. Create a Google Cloud project.
2. Enable **Google Sheets API** and **Google Drive API**.
3. Configure the OAuth consent screen, add the intended users while the app is in testing, and publish only after completing Google's requirements.
4. Create an OAuth 2.0 **Web application** client.
5. Add `http://localhost:8000/api/integrations/google/callback` as an authorized redirect URI (use the exact HTTPS API URL in production).
6. Put the client ID and secret in `.env`. Never expose the client secret or refresh token to the browser.
7. The scopes are Sheets read/write and Drive metadata read-only. Start OAuth at `GET /api/integrations/google/authorize`, select a spreadsheet/worksheet, then post the header mapping to `/api/integrations/google/configure`.

Column positions are not assumed. A mapping such as `{"Due Date":"deadline","Work Item":"name"}` is saved per integration and normalized by header name.

## Synchronization and conflicts

External rows are unique on `(source, source_id)`, preventing duplicate imports. Each run creates a `SyncLog`. Imported records retain the source, external ID, direct URL, and `last_synced_at`. The Odoo pull task retries with exponential backoff through Celery. Conflict records keep both provider values and support Odoo, Google Sheets, latest, and manual resolution through `/api/conflicts/{id}/resolve`; conflicting changes are never silently selected.

The integration credentials column is backend-only. In a production extension, provision `ENCRYPTION_KEY` from a secrets manager and encrypt credentials before persistence; database, Odoo, Google, and JWT secrets must never enter frontend environment variables.

## Planning and deadline intelligence

The backend calculates overdue, today, tomorrow, soon, on-track, and completed states. The planner scores overdue pressure, deadline proximity, priority, remaining work, and progress; schedules dependencies first where possible; respects daily capacity; and reports overflow tasks/hours. Dates are computed from the actual current workweek.

## API surface

FastAPI documents the complete schema at `/docs`. Main resources are `/api/auth`, `/api/projects`, `/api/tasks`, `/api/dashboard`, `/api/calendar`, `/api/planner`, `/api/notifications`, `/api/integrations`, `/api/sync/logs`, and `/api/conflicts`.

## Troubleshooting

- **401 from API:** sign in again and verify `JWT_SECRET` is stable across API replicas.
- **Odoo failure:** verify database name, service-user permissions, URL reachability, and API availability for the installed Odoo edition.
- **Google redirect mismatch:** the URI in Cloud Console must exactly equal `GOOGLE_REDIRECT_URI`.
- **Worker idle:** confirm Redis health and that worker/backend use the same `REDIS_URL`.
- **Database unavailable:** inspect `docker compose ps`, then verify the PostgreSQL password and URL agree.

## Security notes

Passwords are bcrypt hashed; access and refresh JWTs have separate types and lifetimes; API routes require authorization; schemas validate inputs; CORS is restricted to the configured frontend; and secrets come from environment variables. Use HTTPS and secure, HTTP-only refresh-token cookies at the edge for public production deployments.
