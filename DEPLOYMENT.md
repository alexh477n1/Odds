# Deployment Guide

## Backend (Railway)

- Service: deploy this repo (backend entrypoint `backend/app/main.py`)
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment variables:
  - `DATABASE_URL` (Supabase Postgres connection string)
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY`
  - `SUPABASE_JWT_SECRET`
  - `REDIS_URL`
  - `ADMIN_API_KEY` (optional)
  - `ALLOWED_ORIGINS=https://bets.outsidegroup.co.uk,https://<your-pages-project>.pages.dev`
- `AUTO_CREATE_TABLES=true` (optional, run once to create missing tables)
Note: do not store secrets in this file. Keep credentials in Railway/Pages env vars.

### Celery worker

Create a separate Railway service:

- Start command: `celery -A app.workers.celery_app.celery_app worker --loglevel=INFO`
- Use same env vars as backend.

### Optional scheduled tasks

Use Railway cron to call:
- `POST /admin/tasks/scrape` (with `X-Admin-Key`)
- `POST /admin/tasks/seed` (with `X-Admin-Key`)

## Frontend (Cloudflare Pages)

- Repo: `frontend/`
- Build command: `npm install && npm run build`
- Output directory: `dist`
- Environment variables (set for Production and Preview):
  - `VITE_API_URL=https://api.outsidegroup.co.uk`
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`

## Domains

- `bets.outsidegroup.co.uk` → Cloudflare Pages
- `api.outsidegroup.co.uk` → Railway backend
