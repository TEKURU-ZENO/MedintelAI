# AksharabyasaAI — Complete Phase History & Implementation Log

> **Platform Version:** 2.0.0  
> **Last Updated:** May 2026  
> **Status:** Product Hardening Phase (Post Phase 7)

This document is the canonical record of every phase, system, and architectural decision made during the development of AksharabyasaAI.

---

## 🗺️ Phase Overview

| Phase | Name | Status |
|-------|------|--------|
| Phase 1 | Core AI Pipeline & Stroke Analysis | ✅ Complete |
| Phase 2 | Behavioral Analytics & Frustration Engine | ✅ Complete |
| Phase 3 | Session Management & Auth System | ✅ Complete |
| Phase 3.5 | Dashboard, Profile & UI System | ✅ Complete |
| Phase 4 | Adaptive Difficulty & ML Intelligence | ✅ Complete |
| Phase 5 | Audio Orchestration & TTS | ✅ Complete |
| Phase 6.1 | Pronunciation & Preloading Engine | ✅ Complete |
| Phase 6.2 | Reactive Emotional Coaching | ✅ Complete |
| Phase 6.3 | Spelling MVP — Literacy State Machine | ✅ Complete |
| Phase 7 | Adaptive Curriculum Engine (DAG + Mastery) | ✅ Complete |
| Hardening | Deployment, Performance, Testing, Docs | ✅ Active |

---

## Phase 1 — Core AI Pipeline & Stroke Analysis

**Goal:** Transform raw canvas pointer events into a scored, structured stroke analysis.

### Backend Built
- `app/ai/pipeline/` — Full preprocessing + feature extraction pipeline
- `app/ai/features/` — Stroke feature extractor (coverage, smoothness, direction, path error)
- `app/ai/segmentation/` — Line and letter segmentation
- `app/ai/preprocessing/` — Grayscale, noise reduction, normalization
- `app/services/guidance_handler.py` — Core stroke evaluation handler with failsafe triggers
- `app/api/analysis.py` — `/analysis/run` endpoint

### Algorithms
- **FastDTW** — Dynamic Time Warping for stroke similarity scoring
- **Coverage Score** — Polygon-intersection-based trace coverage measurement
- **Direction Score** — Vector cosine similarity for stroke direction validation
- **Smoothness Score** — Curvature variance across polyline segments
- **Path Error** — Hausdorff-distance-derived distance from reference path

### Frontend Built
- `TracingCanvas.tsx` — First-generation canvas with pointer events
- `CanvasBoard.tsx` — Canvas wrapper with coordinate normalization
- `ResultPanel.tsx` — Per-stroke feedback display

### Tests Added
- `tests/test_stroke_analyzer.py` — 40+ unit tests covering all scoring algorithms

---

## Phase 2 — Behavioral Analytics & Frustration Engine

**Goal:** Look beyond *what* was drawn to understand *how* the learner feels.

### Backend Built
- `app/services/analytics/` — Full analytics engine
- `app/services/learning_engine.py` — Core behavioral learning engine
  - Hesitation Latency tracking
  - Failsafe trigger rate monitoring
  - Ghost Replay reliance scoring
  - Frustration Index calculation
  - Learner style classification: `methodical`, `replay_dependent`, `frustrated`, `confident`
- `app/api/analytics.py` — `/analytics/history` endpoint
- `app/api/analytics_v2.py` — V2 structured analytics (summary, progress, engagement, insights, modules)

### Analytics Endpoints (V2)
| Endpoint | Description |
|----------|-------------|
| `GET /analytics/summary` | Streak, XP, frustration level, confidence, accuracy trend |
| `GET /analytics/progress` | Weekly accuracy trend, velocity, best/worst letters |
| `GET /analytics/engagement` | Streak status, session consistency, abandon rate |
| `GET /analytics/insights` | Structured behavioral insights (strengths, weaknesses) |
| `GET /analytics/modules` | Per-module performance cards with promotion readiness |

### Tests Added
- `tests/test_analytics_service.py` — 44 unit tests
- `tests/test_phase2_learning_engine.py` — 46 unit tests

---

## Phase 3 — Session Management & Auth System

**Goal:** Give the platform a persistent identity system and a full session lifecycle.

### Backend Built
- `app/models/user.py` — User model with `profile_type`, `xp_points`, `level`, `user_streak`
- `app/models/practice_session.py` — Session model with JSONB stroke data storage
- `app/models/result.py` — Per-submission result with accuracy scores
- `app/models/submission.py` — Legacy image upload submission model
- `app/api/auth.py` — Full JWT auth: `/auth/register`, `/auth/login`, `/auth/profile`, `/auth/me/ui-config`
- `app/api/sessions.py` — Session lifecycle: `start`, `save_strokes`, `complete`, `abandon`
- `app/services/gamification.py` — XP calculation and level progression
- `app/services/reward_service.py` — Session completion reward generation
- `app/services/streak_service.py` — Streak tracking and at-risk detection
- Alembic migrations setup

### Auth Architecture
- JWT stored in `localStorage`
- `/auth/profile` is the source of truth (not JWT payload)
- UIConfig fetched separately from `/auth/me/ui-config` — drives per-profile UI behavior
- Profile types: `early_learner` (≤5), `child` (6–15), `adult` (16+)

### Frontend Built
- `src/auth/AuthContext.tsx` — V2 unified profile-aware auth context with `useAuth` hook
- `Login.tsx` — Styled login page with JWT hydration
- `Register.tsx` — Full registration with real-time profile type preview
- `src/api/client.ts` — Axios client with JWT interceptor + 401 auto-logout
- `src/api/sessions.ts` — Full session API client

---

## Phase 3.5 — Dashboard, Profile & UI System

**Goal:** Build the visual shell of the platform — profile-aware dashboards and the Zen Practice canvas.

### Frontend Built
- `Dashboard.tsx` — Profile-aware landing page with masonry grid layout
- `Insights.tsx` — Full analytics dashboard with 5 sections, profile-ordered layout, skeleton loading, and per-section graceful degradation
- `src/components/insights/SummaryCard.tsx` — Streak, accuracy, XP display
- `src/components/insights/ProgressSection.tsx` — Weekly accuracy chart (Recharts)
- `src/components/insights/EngagementSection.tsx` — Streak calendar + session consistency
- `src/components/insights/InsightsList.tsx` — AI-generated behavioral insights
- `src/components/insights/ModuleGrid.tsx` — Per-module performance cards
- `src/components/shared/PracticeCanvas.tsx` — Zen Mode canvas (60fps RAF loop)
- `src/components/shared/FeedbackPanel.tsx` — Profile-aware feedback messages
- `src/components/shared/RewardBanner.tsx` — XP + Level-up celebration overlay
- `src/components/shared/EmptyJourneyState.tsx` — Ambient empty state with micro-animations
- `Showcase.tsx` — Unauthenticated demo mode with Curriculum Graph

### Design System
- **Tailwind CSS v4** with `@theme` CSS-first configuration
- Custom color tokens: `background`, `surface`, `sage`, `coral`, `lavender`, `sunflower`, `skyBlue`
- Custom fonts: Inter (body), Outfit/Nunito (display headings)
- Pinterest-inspired masonry layout with soft diffuse shadows
- Zen Mode: full chrome removal, centered canvas, ambient glow on success

---

## Phase 4 — Adaptive Difficulty & ML Intelligence

**Goal:** Make the system learn from session history and adapt difficulty dynamically.

### Backend Built
- `app/services/ml/difficulty_predictor.py` — Predicts next session difficulty from rolling accuracy history
- `app/services/ml/pattern_classifier.py` — Classifies learner behavioral patterns
- `app/services/ml/feature_snapshot.py` — Extracts ML feature vectors from telemetry
- `app/services/ml/item_recommender.py` — Recommends next practice items
- `app/services/ml/recommendation_engine.py` — Full recommendation pipeline with confidence scoring
- `app/services/ml/adaptive_session_planner.py` — Plans full practice sessions with item sequencing
- `app/services/difficulty_adapter.py` — Promotes/demotes difficulty based on rolling window
- `app/services/profile_service.py` — Profile-type derivation, learning profiles, feedback tone mapping
- `app/api/recommendations.py` — `/recommendations/full`, `/recommendations/session`, `/recommendations/feedback`

### Frontend Built
- `src/components/insights/RecommendationsCard.tsx` — Priority-ranked recommendation display
- `src/api/recommendations.ts` — Recommendations API client
- `Practice.tsx` updated — `use_plan=true` mode fetches adaptive session plan before starting

### Tests Added
- `tests/test_ml_recommendations.py` — 33 unit tests
- `tests/test_profile_service.py` — 29 unit tests

---

## Phase 5 — Audio Orchestration & TTS

**Goal:** Give the platform a voice that is educationally aware and emotionally calibrated.

### Backend Built
- `app/services/audio/audio_orchestrator.py` — Central audio decision engine
- `app/services/audio/coaching_policy.py` — Declarative coaching rules with cooldown enforcement
- `app/services/audio/coaching_event_mapper.py` — Maps semantic events → audio payloads
- `app/services/audio/audio_profiles.py` — Per-profile audio intensity and verbosity settings
- `app/services/audio/pronunciation_service.py` — Letter/word pronunciation URL resolution
- `app/services/audio/phonetic_mapper.py` — Phoneme-to-audio mapping for 26 letters + blends
- `app/services/audio/coaching_audio_service.py` — Coaching audio clip selection
- `app/services/audio/celebration_audio.py` — Celebration and milestone audio clips
- `app/services/audio/audio_cache.py` — Local TTS audio caching to avoid redundant API calls
- `app/services/tts_service.py` — TTS API wrapper
- `app/ai/tts/` — TTS utilities

### Frontend Built
- `src/utils/audioPlayer.ts` — Singleton audio player with queue management and preloading
- `src/utils/coachingEngine.ts` — Frontend coaching event dispatcher

### Audio Architecture
The system is **declarative**: the frontend fires semantic events (`direction_failure`, `success_strong`, `hesitation_detected`). The backend adjudicates these against the user's frustration state and cooldown rules before generating audio — the UI never owns coaching logic.

---

## Phase 6.1 — Pronunciation & Preloading Engine

**Goal:** Ensure audio is always ready before the learner needs it.

### Built
- Session-level audio planning: all audio URLs are resolved and sent in the session start response
- `audioPlayer.preload(urls[])` — Preloads audio into browser cache at session start
- Pronunciation injection into session plan — every session response includes `audio_metadata` with `item_audio`, `coach_audio`, `celebration_audio`

---

## Phase 6.2 — Reactive Emotional Coaching

**Goal:** Make the tutor emotionally alive — adapting tone and content to the learner's real-time state.

### Built
- `src/hooks/useGuidanceEngine.ts` — Real-time guidance engine hook
  - Tracks stroke completion state machine
  - Fires `onCoachingEvent` callbacks on semantic events
  - Drives ghost replay deployment when hesitation detected
  - Manages `isSubmitting` lock to prevent double-submission
- `src/hooks/useGhostReplay.ts` — Ghost replay trigger logic
- `src/components/GhostReplay.tsx` — Animated canvas ghost guide (sky-blue glow)
- `AlphabetModule.tsx` — Wired to guidance engine with ghost replay integration
- Backend coaching policy enforces: frustration-aware tone, verbosity scaling, cooldowns

### Behavioral States Tracked
- Methodical learner → less intervention, more silence
- Replay-dependent → earlier ghost guide deployment  
- Frustrated → softer tone, longer cooldowns, breathing prompts
- Confident → brief affirmations only

---

## Phase 6.3 — Spelling MVP (Literacy State Machine)

**Goal:** Extend the platform from letter tracing to full word spelling.

### Backend Built
- `app/services/spelling/spelling_state_machine.py` — Literacy progression state machine
  - States: `idle → listening → attempting → partial_success → correct → retrying → celebrating`
- `app/services/spelling/literacy_orchestrator.py` — Full spelling session orchestrator
- `app/services/spelling/assist_profiles.py` — Forgiveness levels, ghost word, hint display configs
- `app/services/spelling/spelling_feedback.py` — Letter-level feedback generation
- `app/services/spelling/word_packs.py` — CVC words, sight words, double-letter words
- `app/api/spelling.py` — `/spelling/config`, `/spelling/attempt`

### Frontend Built
- `src/components/modules/WordModule.tsx` — Full spelling module
  - Fetches literacy orchestration config on mount
  - Loops through each letter: hear → trace → validate
  - Micro-celebration on each correct letter
  - Full-word celebration on completion
- `src/api/spelling.ts` — Spelling API client
- `Practice.tsx` updated — routes `module=word_practice` to `WordModule`

---

## Phase 7 — Adaptive Curriculum Engine

**Goal:** Evolve the platform from reactive tutoring into structured long-term educational progression.

### Backend Built
- `app/services/curriculum/curriculum_graph.py` — DAG curriculum graph
  - Nodes: `straight_lines → angular_caps → curved_letters → cvc_words → complex_words`
  - Prerequisite enforcement: nodes stay locked until dependencies are mastered
- `app/services/curriculum/mastery_engine.py` — Multi-dimensional mastery scoring
  - Motor mastery (stroke quality)
  - Cognitive mastery (sequencing accuracy)
  - Retention mastery (spaced repetition performance)
- `app/services/curriculum/review_scheduler.py` — Ebbinghaus forgetting curve review scheduling
- `app/services/curriculum/plateau_detector.py` — Detects learning plateaus from velocity trends
- `app/services/curriculum/progression_rules.py` — Confidence-gating rules (prevents lucky unlocks)
- `app/services/curriculum/educational_state_engine.py` — Overall educational state manager
- `app/services/curriculum/learning_journey_engine.py` — Journey orchestrator
- `app/services/curriculum/mastery_snapshot.py` — Point-in-time mastery snapshots
- `app/services/curriculum/skill_tree.py` — Skill dependency tree

### Frontend Built
- `Showcase.tsx` — Visual Curriculum Graph with mastery percentages
- `RecommendationsCard.tsx` — Shows next milestone with priority, reason, and session length

---

## Product Hardening Phase

**Goal:** Transition from prototype to production-grade deployable product.

### Deployment Infrastructure
- `backend.Dockerfile` — Python 3.10 slim, Alembic migrations on startup, Uvicorn
- `frontend.Dockerfile` — Multi-stage: Vite build → Alpine NGINX
- `docker-compose.yml` — Orchestrates PostgreSQL + Backend + Frontend
- `nginx.conf` — SPA routing + `/api/` and `/audio/` proxy pass to backend

### Performance Hardening
- `PracticeCanvas.tsx` refactored to `requestAnimationFrame` loop (zero React rerenders during tracing)
- `useStrokeTracker.ts` exposes `currentPoints` ref — pointer events mutate a ref array, not state
- Result: `<16ms` pointer-to-render latency on all tested devices

### Demo & Showcase
- `app/scripts/seed_demo.py` — Seeds a "Struggling Learner → Confident Learner" 4-day progression
- `Showcase.tsx` — Unauthenticated demo mode for stakeholder presentations
- `EmptyJourneyState.tsx` — Ambient encouraging empty state

### Dependency Fixes (Build Hardening)
- Migrated from Tailwind CSS v3 syntax to **v4 CSS-first `@theme` config**
- Added `@tailwindcss/vite` plugin — replaces PostCSS pipeline entirely
- Fixed all `apiClient` → `api` import mismatches across `spelling.ts`, `recommendations.ts`, `analytics.ts`
- Fixed `useAuth` import path across all pages (`../auth/AuthContext`)
- Fixed all TypeScript `noUnusedLocals` violations across 6 components
- Removed obsolete `Kids.tsx` (Phase 1 relic)

### Testing
- **198 backend unit tests** — 198/198 passing
- `python -m pytest tests/test_analytics_service.py tests/test_ml_recommendations.py tests/test_phase2_learning_engine.py tests/test_profile_service.py tests/test_stroke_analyzer.py`
- Production build: `npm run build` — 0 TypeScript errors

---

## Current File Tree (V2)

```
handwriting-ai-system/
├── app/
│   ├── ai/                     # Phase 1: pipeline, features, segmentation, tts
│   ├── api/                    # REST endpoints (auth, sessions, analytics, spelling, recommendations)
│   ├── core/                   # config, database, logging
│   ├── models/                 # SQLAlchemy models (user, session, result, submission, feedback)
│   ├── repositories/           # DB access layer
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/
│   │   ├── analytics/          # Phase 2: behavioral analytics engine
│   │   ├── audio/              # Phase 5: coaching + pronunciation + TTS cache
│   │   ├── curriculum/         # Phase 7: DAG, mastery, review scheduler
│   │   ├── ml/                 # Phase 4: difficulty predictor, recommender, planner
│   │   └── spelling/           # Phase 6.3: state machine, literacy orchestrator
│   └── scripts/
│       └── seed_demo.py        # Demo seeding script
├── frontend/
│   └── src/
│       ├── api/                # Typed API clients (sessions, analytics, recommendations, spelling)
│       ├── auth/               # AuthContext + useAuth hook
│       ├── components/
│       │   ├── insights/       # SummaryCard, ProgressSection, EngagementSection, etc.
│       │   ├── modules/        # AlphabetModule, WordModule, FreeDrawModule
│       │   └── shared/         # PracticeCanvas (RAF loop), FeedbackPanel, RewardBanner
│       ├── hooks/              # useStrokeTracker, useGuidanceEngine, useGhostReplay
│       ├── pages/              # Dashboard, Practice, Insights, Login, Register, Showcase
│       └── utils/              # audioPlayer, coachingEngine, ageUtils
├── tests/                      # 198 unit tests
├── docs/                       # This document + architecture, deployment, demo, test plan
├── backend.Dockerfile
├── frontend.Dockerfile
├── docker-compose.yml
└── nginx.conf
```

---

## Open Items (Remaining for Full Production)

| Item | Priority |
|------|----------|
| Live PostgreSQL (hosted DB for deployed environment) | P0 |
| HTTPS + domain via Caddy/Certbot | P0 |
| T6 — Human UX observation testing (child/parent) | P1 |
| T9 — Cross-device tablet testing (iPad, Android) | P1 |
| T10 — Full end-to-end demo walkthrough with seeded data | P1 |
| Pydantic V2 migration (`class Config` → `model_config`) | P2 |
| SQLAlchemy 2.0 migration (`declarative_base` deprecation) | P2 |
