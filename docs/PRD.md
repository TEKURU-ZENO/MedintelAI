# AksharabyasaAI — Product Requirements Document (PRD)

> **Version:** 2.0.0 | **Status:** Feature Complete, Hardening Phase

---

## 1. Product Vision

AksharabyasaAI is **not a gamified tracing app**.

It is a **multimodal, emotionally intelligent literacy learning platform** that bridges the gap between passive screen time and active cognitive development. The platform transforms tablet interactions into structured, personalized, and adaptive educational journeys.

### The Core Thesis
> A child learning to write needs more than a correct/incorrect signal. They need a system that understands *how they feel*, *why they're struggling*, and *exactly what to do next* — in real time.

---

## 2. Target Users

| User | Description |
|------|-------------|
| `early_learner` | Ages 2–5. Needs high visual reward, minimal text, audio-first interaction |
| `child` | Ages 6–15. Standard learner profile, progress-focused feedback |
| `adult` | Ages 16+. Analytical insights, professional tone, full data access |
| Parent/Guardian | Views child progress via Insights dashboard |

Profile type is derived from `date_of_birth` at registration, but can be overridden via `preferred_learning_mode` for special educational needs.

---

## 3. Core Educational Philosophy

The platform nurtures **four cognitive dimensions simultaneously**:

1. **Motor Control** — The physical act of tracing and forming letter shapes
2. **Cognitive Sequencing** — Understanding stroke order, directionality, spatial layout
3. **Phonetic Association** — Linking visual symbols to auditory sounds (letter names + phonics)
4. **Emotional Resilience** — Maintaining confidence, recovering from failure gracefully

No traditional tracing app addresses all four. AksharabyasaAI does.

---

## 4. Feature Set (V2 Complete)

### 4.1 Practice Modules

| Module | ID | Description |
|--------|-----|-------------|
| Alphabet Practice | `alphabet_practice` | Guided letter tracing with stroke-by-stroke validation |
| Word Practice | `word_practice` | Full word spelling: hear → trace each letter → celebrate |
| Free Draw | `free_draw` | Unguided creative practice with telemetry collection |

### 4.2 Guidance System
- Real-time stroke coverage, direction, and accuracy feedback
- Color-coded canvas feedback: green (on-path), amber (close), red (off-path)
- **Ghost Replay**: animated visual demonstration deployed on hesitation detection
- Configurable failsafe: auto-advances after N failed attempts

### 4.3 Audio & Coaching
- Per-letter and per-word pronunciation audio
- Emotionally-calibrated coaching: tone adapts to frustration level
- Cooldown enforcement prevents coaching fatigue
- Audio preloaded at session start — zero latency during practice

### 4.4 Analytics & Insights
- Weekly accuracy trend charts
- Streak tracking and at-risk detection
- Behavioral insights (strengths, weaknesses, behavioral patterns)
- Per-module performance cards with promotion readiness score

### 4.5 Adaptive Intelligence
- ML-driven difficulty prediction from rolling session history
- Item recommender picks the right letter/word for each session
- Adaptive session planner generates full practice sequences
- Recommendation feedback loop: accepted/completed/skipped signals improve future recommendations

### 4.6 Curriculum Management
- DAG curriculum graph enforces correct learning order
- Multi-dimensional mastery (motor + cognitive + retention)
- Spaced repetition reviews triggered by forgetting curve
- Confidence-gating prevents advancement without consistent mastery
- Plateau detection triggers intervention recommendations

### 4.7 Gamification
- XP earned on session completion (accuracy + duration weighted)
- Level progression with threshold table
- Streak tracking (daily practice detection)
- RewardBanner celebration overlay on completion

### 4.8 Showcase Mode
- `/showcase` route — no authentication required
- Visual curriculum graph with mastery percentages
- Next milestone card with recommendation context
- Suitable for stakeholder demos, parent onboarding, press

---

## 5. Non-Functional Requirements

| Requirement | Target | Status |
|-------------|--------|--------|
| Canvas render latency | < 16ms | ✅ Met (RAF loop) |
| Backend API response | < 200ms | ✅ Designed for |
| TypeScript compilation | 0 errors | ✅ Met |
| Backend test coverage | > 190 tests | ✅ 198 passing |
| Mobile/Tablet touch | Imperceptible latency | 🔄 Pending device testing |
| Audio overlap prevention | Cooldown enforced | ✅ Met |
| Session recovery on refresh | Graceful restore | 🔄 Pending |

---

## 6. Out of Scope (Explicitly Deferred)

The following are **Phase 10+ items**:
- Speech recognition / voice input
- Multilingual support (currently English phonetics only)
- Enterprise LMS integration
- Classroom management / teacher dashboard
- Generative AI lesson planning
- Neural network stroke evaluation (current: deterministic algorithms)

---

## 7. Success Criteria

### Technical (P0 — Must have for any deployment)
- [ ] Live PostgreSQL instance accessible to backend
- [ ] HTTPS with valid SSL certificate
- [ ] All auth flows functional end-to-end
- [x] Zero TypeScript compilation errors
- [x] 198/198 backend tests passing

### Educational (P1 — Must have for user testing)
- [ ] Child completes at least 3 letters in a single session without confusion
- [ ] Ghost Replay deploys correctly on hesitation
- [ ] Emotional coaching tone audibly softens when frustration is high
- [ ] Parent dashboard readable and trustworthy

### Demo (P2 — Required for stakeholder presentation)
- [x] Showcase mode loads without authentication
- [x] Curriculum graph renders with realistic mastery data
- [ ] Seed data produces believable 4-day progression story
- [ ] End-to-end demo flow completes in under 5 minutes
