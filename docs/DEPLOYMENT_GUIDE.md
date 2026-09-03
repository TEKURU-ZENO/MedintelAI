# AksharabyasaAI — Deployment Guide

> **Version:** 2.0.0 | **Stack:** Docker + FastAPI + Nginx + PostgreSQL

---

## 1. Prerequisites

| Tool | Version | Required For |
|------|---------|-------------|
| Docker | 24+ | Container orchestration |
| Docker Compose | 2.x+ | Multi-service orchestration |
| Python | 3.10+ | Local development only |
| Node.js | 20+ | Local frontend development only |

---

## 2. Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://akshar_user:akshar_password@db:5432/aksharabyasa

# Auth
SECRET_KEY=<generate a secure 256-bit random hex string>

# App
ENVIRONMENT=production
```

Generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ **Never commit a real SECRET_KEY to version control.**

---

## 3. Docker Architecture

```
docker-compose.yml
 ├── db        postgres:15-alpine
 │              Port: 5432 (internal only)
 │              Volume: pgdata (persistent)
 │
 ├── backend   backend.Dockerfile
 │              Port: 8000 (internal)
 │              Runs: alembic upgrade head → uvicorn app.main:app
 │              Volume: ./app/cache → /app/app/cache (TTS audio persistence)
 │
 └── frontend  frontend.Dockerfile
                Port: 80 (exposed to host)
                Stage 1: node:20-alpine → npm run build → /dist
                Stage 2: nginx:alpine → serves /dist + proxies /api/ and /audio/
```

---

## 4. Running Locally (Development)

### Backend

```bash
# From project root
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Requires a local PostgreSQL instance at `localhost:5432/akshara`.

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173 (or :5174 if port is busy)
```

> **Important**: If port 8000 is occupied by another project, find and kill it:
>
> ```powershell
> netstat -ano | findstr ":8000"
> Stop-Process -Id <PID> -Force
> ```

### Run Tests

```bash
python -m pytest tests/test_analytics_service.py tests/test_ml_recommendations.py tests/test_phase2_learning_engine.py tests/test_profile_service.py tests/test_stroke_analyzer.py -v
```

Expected: **198 passed**.

### Build Frontend (Production Validation)

```bash
cd frontend && npm run build
```

Expected: **Exit code 0, 0 TypeScript errors**.

---

## 5. Docker Deployment

### First Run

```bash
# Build and start all services
docker-compose up --build -d

# Verify all containers are healthy
docker-compose ps

# Check backend started correctly (migrations ran)
docker-compose logs backend
```

Look for:

```
INFO: Application startup complete.
```

### Seed Demo Data

After containers are running:

```bash
docker-compose exec backend python app/scripts/seed_demo.py
```

This creates a demo user with a 4-day "Struggling → Confident Learner" progression for showcase demos.

### Stopping

```bash
docker-compose down          # stop containers (data persists)
docker-compose down -v       # stop + delete all data volumes
```

---

## 6. Audio File Persistence

The backend TTS service caches generated audio files locally to avoid repeated API calls.

In `docker-compose.yml`:

```yaml
backend:
  volumes:
    - ./app/cache:/app/app/cache
```

This means audio files survive container restarts. Ensure the host has adequate disk space (estimate ~1MB per 100 unique TTS clips).

---

## 7. HTTPS (Production Deployment on a VPS)

Place **Caddy** or **NGINX** as a reverse proxy in front of the Docker stack.

### Option A: Caddy (Recommended — Auto SSL)

```caddyfile
yourdomain.com {
    reverse_proxy localhost:80
}
```

Caddy auto-manages Let's Encrypt certificates.

### Option B: NGINX + Certbot

```bash
certbot --nginx -d yourdomain.com
```

The Docker NGINX container only listens on port 80. Your host-level reverse proxy handles SSL termination and forwards HTTP to `localhost:80`.

---

## 8. Frontend API Base URL

The Vite frontend currently points to `http://localhost:8000` in development (`src/api/client.ts`).

For production, update this to your domain:

```typescript
// src/api/client.ts
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});
```

And set in your production `.env`:

```env
VITE_API_URL=https://api.yourdomain.com
```

Or, use the NGINX proxy approach (preferred) — all requests go to `/api/` on the same domain, eliminating CORS entirely.

---

## 9. Database Migrations

Migrations are handled by **Alembic** and run automatically on backend container startup.

To create a new migration after changing a model:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

To check current migration state:

```bash
alembic current
```

---

## 10. Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "2.0.0"}
```

The Swagger UI is available at:

```
http://localhost:8000/docs
```

Should show **AksharabyasaAI 2.0.0** — if it shows any other title, a different server is running on port 8000.
