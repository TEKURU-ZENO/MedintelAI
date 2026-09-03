# AksharabyasaAI — Technical Architecture

> **Version:** 2.0.0 | **Stack:** FastAPI + React + PostgreSQL + Tailwind CSS v4

---

## 1. System Architecture

AksharabyasaAI is a **decoupled, event-driven** educational platform. The architecture enforces a strict principle:

> **The frontend never owns educational logic. It is a state-driven renderer and telemetry collector.**

```
┌─────────────────────────────────┐
│         React Frontend          │
│  (Vite + Tailwind CSS v4)       │
│                                 │
│  ┌────────────┐ ┌─────────────┐ │
│  │ RAF Canvas │ │  Auth State  │ │
│  │  (60fps)   │ │  (Context)   │ │
│  └─────┬──────┘ └──────┬──────┘ │
│        │ Pointer Events │ JWT   │
└────────┼───────────────┼────────┘
         │               │
         ▼               ▼
┌──────────────────────────────────┐
│        FastAPI Gateway           │
│  (Uvicorn / port 8000)           │
│                                  │
│  /auth   /sessions  /analytics   │
│  /spelling  /recommendations     │
└────┬───────────┬──────────┬──────┘
     │           │          │
     ▼           ▼          ▼
┌─────────┐ ┌────────┐ ┌──────────┐
│ AI Layer│ │Services│ │PostgreSQL│
│(Stroke  │ │(Audio, │ │(SQLAlch. │
│Analysis)│ │Curriculum│ │  ORM)  │
└─────────┘ └────────┘ └──────────┘
```

---

## 2. Backend — FastAPI Application (`app/`)

### Entry Point: `app/main.py`
- Title: **AksharabyasaAI v2.0.0**
- CORS: Allows `localhost:5173`, `localhost:3000`
- Static audio served at `/audio/` (caches TTS output)
- All routers mounted with semantic prefixes

### API Routes

| Router | Prefix | Key Endpoints |
|--------|--------|---------------|
| `auth.py` | `/auth` | `POST /register`, `POST /login`, `GET /profile`, `PATCH /profile`, `GET /me/ui-config` |
| `sessions.py` | `/sessions` | `POST /start`, `POST /{id}/save_strokes`, `POST /{id}/complete`, `POST /{id}/abandon` |
| `analysis.py` | — | `POST /analysis/run` |
| `analytics.py` | — | `GET /analytics/history` |
| `analytics_v2.py` | — | `GET /analytics/summary`, `/progress`, `/engagement`, `/insights`, `/modules` |
| `recommendations.py` | — | `GET /recommendations/full`, `GET /recommendations/session`, `POST /recommendations/feedback` |
| `spelling.py` | `/spelling` | `GET /config`, `POST /attempt` |

---

## 3. Database Models (SQLAlchemy)

```
User
 ├── id, email, hashed_password
 ├── full_name, date_of_birth
 ├── profile_type: early_learner | child | adult
 ├── preferred_learning_mode (override for profile_type)
 ├── preferred_language
 ├── level, xp_points, user_streak
 └── is_active, pending_parent_link

PracticeSession
 ├── id, user_id (FK → User)
 ├── module_type: alphabet_practice | word_practice | free_draw
 ├── target_item, difficulty
 ├── status: active | completed | abandoned
 └── started_at, completed_at

Result
 ├── id, session_id (FK → PracticeSession)
 ├── accuracy_score, duration_seconds
 ├── stroke_data: JSONB (raw telemetry)
 └── total_strokes, total_points

RecommendationFeedback
 ├── id, user_id (FK → User)
 ├── item, module_type, action: accepted | completed | skipped
 └── outcome_accuracy, created_at
```

> **Key Design**: Mastery is **never stored as a flat score**. It is computed dynamically from `Result` history, ensuring the forgetting curve is always live.

---

## 4. The 4 AI Layers

### Layer 1: Deterministic Stroke Analysis (`app/ai/`)
Pure computational geometry — no neural networks, no cloud inference.

| Algorithm | File | Purpose |
|-----------|------|---------|
| Coverage Score | `features/` | Polygon intersection of drawn vs. reference path |
| Direction Score | `features/` | Vector cosine similarity against expected stroke vector |
| Smoothness Score | `features/` | Curvature variance across polyline segments |
| Path Error | `features/` | Hausdorff distance from reference |
| Guidance Handler | `services/guidance_handler.py` | State machine: tracks completed strokes, fires failsafe at max attempts |

**Latency**: `<16ms` — all analysis runs locally in the browser via the guidance engine hook; server analysis runs on completion only.

### Layer 2: Behavioral Analytics Engine (`app/services/analytics/`, `learning_engine.py`)
Reads session telemetry to classify the learner.

| Signal | Metric |
|--------|--------|
| Time before first stroke | Hesitation Latency |
| Ghost replay trigger count | Replay Dependency |
| Consecutive failsafe count | Frustration Index |
| Session accuracy trend | Confidence Level |

**Output**: `learner_style` ∈ `{methodical, replay_dependent, frustrated, confident}`

### Layer 3: Declarative Audio Coaching (`app/services/audio/`)
The frontend fires **semantic events**. The backend adjudicates.

```
Frontend: onCoachingEvent("direction_failure")
    ↓
audio_orchestrator.py
    ├── checks frustration_level
    ├── checks cooldown (last_coaching_at)
    ├── checks learner_style → picks audio intensity
    └── returns audio URL (or null if in cooldown)
```

Never fires audio blindly. Always filtered through policy.

### Layer 4: Adaptive Curriculum Engine (`app/services/curriculum/`)
Long-term educational progression management.

```
curriculum_graph.py  →  DAG of skill nodes
mastery_engine.py    →  Multi-dimensional mastery scoring
review_scheduler.py  →  Ebbinghaus forgetting curve scheduling
plateau_detector.py  →  Velocity-based plateau detection
progression_rules.py →  Confidence-gating (no lucky unlocks)
```

**Mastery = f(motor_mastery, cognitive_mastery, retention_mastery)**  
A child must demonstrate consistent, high-confidence mastery across multiple sessions to unlock the next curriculum node.

---

## 5. Frontend Architecture (React + Vite)

### State Architecture
```
AuthContext (src/auth/AuthContext.tsx)
 ├── token: string | null
 ├── user: UserProfile
 ├── uiConfig: UIConfig          ← drives per-profile UI behavior
 ├── profileType: ProfileType    ← early_learner | child | adult
 └── login / logout / refreshProfile
```

### Canvas Performance Architecture (`PracticeCanvas.tsx`)
The most critical performance boundary.

```
Pointer Events
    ↓
useStrokeTracker (hook)
    ├── currentPoints.current ← mutable ref (NO state update)
    └── onStrokeEnd → React state update (only on lift)

requestAnimationFrame loop (runs at 60fps)
    ├── reads currentPoints.current (zero GC pressure)
    ├── reads completedStrokes (from guidance engine)
    ├── reads activeStrokePath (SVG guide)
    └── renders to canvas directly (no React reconciliation)
```

**Result**: Zero React rerenders during active tracing. All 60fps is real.

### Routing (React Router v7)
```
/               → redirect to /login
/login          → Login.tsx
/register       → Register.tsx
/dashboard      → Dashboard.tsx (protected)
/practice       → Practice.tsx (protected, ?module=&item=&use_plan=)
/insights       → Insights.tsx (protected)
/showcase       → Showcase.tsx (public, no auth)
```

### Practice Session Lifecycle (`Practice.tsx`)
```
Mount
 ├── [use_plan=true] → GET /recommendations/session → resolves difficulty + items
 ├── GET /sessions/start → session_id
 └── setPageState("practicing")

During session
 ├── setInterval(10s) → POST /sessions/{id}/save_strokes (auto-save)
 └── Module fires onComplete(strokes, accuracy)

Completion
 ├── POST /sessions/{id}/complete → reward payload
 ├── POST /recommendations/feedback (if use_plan)
 ├── refreshProfile() → sync XP/level into AuthContext
 └── setPageState("reward") → RewardBanner overlay
```

---

## 6. Deployment Architecture

### Docker Services
```
docker-compose.yml
 ├── db        → postgres:15-alpine (volume: pgdata)
 ├── backend   → backend.Dockerfile
 │               CMD: alembic upgrade head && uvicorn app.main:app
 └── frontend  → frontend.Dockerfile
                 Stage 1: node → npm run build
                 Stage 2: nginx:alpine → serve /dist
```

### NGINX Configuration (`nginx.conf`)
```nginx
location /api/  { proxy_pass http://backend:8000/; }
location /audio/ { proxy_pass http://backend:8000/audio/; }
location /      { try_files $uri $uri/ /index.html; }  # SPA routing
```

This eliminates CORS entirely — all traffic goes through NGINX on port 80.

### Environment Variables
```env
DATABASE_URL=postgresql://user:pass@db:5432/aksharabyasa
SECRET_KEY=<secure-random-256bit>
ENVIRONMENT=production
```

---

## 7. CSS & Design System

### Tailwind CSS v4 (CSS-First)
The project uses **Tailwind v4** with the `@tailwindcss/vite` plugin.

```css
/* src/index.css */
@import "tailwindcss";

@theme {
  --color-background: #F0F2F5;
  --color-surface: #FFFFFF;
  --color-sage: #86EFAC;
  --color-coral: #FDA4AF;
  --color-lavender: #D8B4FE;
  --font-family-sans: "Inter", system-ui, sans-serif;
  --font-family-display: "Outfit", "Nunito", system-ui, sans-serif;
  --shadow-md: 0 8px 30px rgba(0, 0, 0, 0.06);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

> **Important**: There is NO `tailwind.config.ts` driving the build. All config lives in `index.css`. The `vite.config.ts` loads `@tailwindcss/vite` as a plugin.

---

## 8. Known Warnings (Non-Breaking)

| Warning | Source | Impact |
|---------|--------|--------|
| `PydanticDeprecatedSince20: class-based Config` | `app/core/config.py` | None — works in Pydantic v2, migrate to `model_config` when ready |
| `MovedIn20Warning: declarative_base()` | `app/core/database.py` | None — works in SQLAlchemy 2.x, cosmetic only |
| `[lightningcss] Unknown at-rule @tailwind` | Build output | None — these are v3 `@apply` directives in old CSS that lightningcss skips harmlessly |
