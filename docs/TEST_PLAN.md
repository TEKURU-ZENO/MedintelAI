# AksharabyasaAI — Testing Master Plan

> **Version:** 2.0.0 | **Backend Tests:** 198/198 ✅ | **TS Build:** 0 errors ✅

---

## Phase Overview

| Phase | Focus | Automated | Status |
|-------|-------|-----------|--------|
| T1 | Backend Core Validation | Partial | 🔄 Needs live DB |
| T2 | AI & Guidance Validation | ✅ Yes | ✅ Complete |
| T3 | Frontend Interaction Testing | Partial | ✅ Mostly done |
| T4 | Audio & Coaching Validation | ✅ Yes | ✅ Complete |
| T5 | Curriculum & Recommendation Validation | ✅ Yes | ✅ Complete |
| T6 | UX & Emotional Flow Testing | Manual | 🔄 Needs human testers |
| T7 | Stress & Performance Testing | Partial | ✅ Core done |
| T8 | Security & Reliability Testing | Manual | 🔄 Needs live env |
| T9 | Cross-Device & Responsive Testing | Manual | 🔄 Needs devices |
| T10 | End-to-End Demo Validation | Manual | 🔄 Needs seeded data |
| T11 | Advanced Product Hardening (14 Pillars) | Partial | 🔄 Ongoing |

---

## How to Run Automated Tests

```bash
# From project root
python -m pytest tests/test_analytics_service.py tests/test_ml_recommendations.py tests/test_phase2_learning_engine.py tests/test_profile_service.py tests/test_stroke_analyzer.py -v

# Expected output:
# ===================== 198 passed, 2 warnings in ~1.1s =====================
```

---

## T1 — Backend Core Validation

### Authentication System
- [x] JWT token issued on login
- [x] Profile type derived correctly from DOB
- [ ] Duplicate email rejected (needs live DB)
- [ ] JWT expiration and tampering (needs live env)
- [ ] Multiple concurrent sessions (needs live env)

### Database Integrity
- [ ] Foreign key constraints enforced (needs live DB)
- [ ] JSONB stroke_data serialization / deserialization
- [ ] Cascade delete: user → sessions → results
- [ ] No orphan rows after session abandon

### File Upload System
- [ ] Valid image upload succeeds
- [ ] >5MB image blocked
- [ ] Non-image MIME type rejected

---

## T2 — AI & Guidance Validation ✅

All tests in `tests/test_stroke_analyzer.py` (40 tests).

### Stroke Analyzer
- [x] Perfect trace scores near 1.0
- [x] Reversed direction scores near 0
- [x] Scribble input triggers retry coaching
- [x] All score components in [0.0, 1.0]

### Real-Time Guidance Engine
- [x] Stroke completion state advances correctly
- [x] Failsafe triggers at max_attempts
- [x] Good trace unlocks next stroke
- [x] Weighted trace_percent formula verified

### Direction Detector
- [x] Horizontal, vertical, diagonal detection accurate
- [x] Single-point stroke returns "unknown"
- [x] Confidence field present in all outputs

---

## T3 — Frontend Interaction Testing

### Dashboard UI
- [x] Empty state renders (EmptyJourneyState)
- [x] Long text does not overflow card bounds
- [x] Masonry grid reflows on narrow viewport

### Practice Flow
- [x] Session start → module loads correctly
- [x] Auto-save interval fires every 10s
- [x] Session complete → RewardBanner displayed
- [ ] Rapid retry (complete → new session) does not duplicate analytics
- [x] No memory leaks during extended tracing (RAF loop validated)

### Showcase Mode
- [x] Loads without authentication
- [x] Curriculum Graph renders with correct mastery data
- [x] "Start Journey" navigates to /login
- [x] Zero console errors

---

## T4 — Audio & Coaching Validation ✅

All tests in `tests/test_analytics_service.py` (coaching policy tests).

### Audio Engine
- [x] Pronunciation and coaching do not overlap (cooldown enforced)
- [x] Cooldown resets correctly after timeout
- [x] Audio preloaded before session start
- [ ] Missing/corrupted MP3 cache degrades gracefully (manual test)

### Emotional Coaching
- [x] Low frustration → brief, confident tone
- [x] High frustration → softer, longer pause, breathing prompt
- [x] Verbosity scales: methodical gets less, replay-dependent gets more
- [x] Cooldown prevents robotic repetition

---

## T5 — Curriculum & Recommendation Validation ✅

Tests in `tests/test_ml_recommendations.py` (33 tests) and `test_phase2_learning_engine.py` (46 tests).

### Curriculum DAG
- [x] Straight Lines must be mastered before Angular Capitals
- [x] Confidence gating rejects single-session lucky unlock
- [x] Plateau detection fires correctly on flat accuracy trend

### Mastery Engine
- [x] Mastery increases with good sessions
- [x] Mastery decays correctly over simulated time gaps
- [x] Retention review scheduling respects Ebbinghaus curve

### Recommendation Engine
- [x] Generates `confidence_boost` focus for near-mastery items
- [x] Generates `deep_mastery` focus for high-variance items
- [x] Feedback signals (completed/skipped) update future recommendations

---

## T6 — UX & Emotional Flow Testing 🔄

**These require real human testers. Cannot be automated.**

### Child Emotional Experience
- [ ] Pacing is calm — no audio overwhelm in first 2 minutes
- [ ] Retry feels safe — audio tone does not become punishing
- [ ] Ghost Replay deploys naturally without feeling robotic
- [ ] Early Learner profile shows emoji, large text, no data grids

### Parent/Guardian Experience
- [ ] Insights dashboard is readable without explanation
- [ ] Recommendations card is actionable (parent knows what to do next)
- [ ] Data feels trustworthy, not alarming

### Learning Loop Cohesion
- [ ] Emotional flow: Practice → Feedback → Dashboard feels unified
- [ ] Design tokens are consistent across all screens (spacing, shadows, typography)

---

## T7 — Stress & Performance Testing

### Frontend Performance
- [x] 60 FPS maintained during tracing (RAF loop, zero state updates during draw)
- [x] React rerenders: only on stroke lift, not during active drawing
- [x] Memory: no growth observed over 45-minute simulated session

### Backend Performance
- [ ] 10 concurrent session completions (needs load test tool)
- [ ] Analytics query under 200ms on 1000 results
- [ ] Recommendation engine under 500ms cold

### AI Pipeline Stability
- [ ] Corrupted telemetry (null stroke_data) fails gracefully with 422
- [ ] Missing features in ML pipeline returns fallback, not 500

---

## T8 — Security & Reliability Testing 🔄

**Requires live environment.**

### Security
- [ ] JWT with tampered payload returns 401
- [ ] JWT from another user cannot access protected routes
- [ ] SQL injection in query params returns 422 (Pydantic validates)
- [ ] File upload with `.exe` extension rejected

### Reliability
- [ ] Backend restart mid-session: client retries and recovers
- [ ] Network drop mid-autosave: strokes buffered and retried
- [ ] Database connection drop: returns 503, not 500

---

## T9 — Cross-Device & Responsive Testing 🔄

**Requires physical devices.**

### Tablet (iPad / Android)
- [ ] Touch precision: stroke stays under finger
- [ ] Palm rejection: canvas ignores incidental palm contact
- [ ] 60fps on 120Hz display (ProMotion iPad)
- [ ] Pinch-to-zoom disabled on canvas

### Layouts
- [ ] Masonry grid: 1 column on mobile, 2 on tablet, 3 on desktop
- [ ] Safe area insets respected on notched devices
- [ ] Keyboard avoidance on login/register forms

### Audio Restrictions
- [ ] Safari autoplay policy: audio plays only after first user gesture
- [ ] iOS mute switch does not break the coaching loop

---

## T10 — End-to-End Demo Validation 🔄

### Flow 1: Beginner Child (early_learner profile)
- [ ] Login as seeded demo child account
- [ ] Dashboard shows encouraging empty state or first recommendation
- [ ] Practice session loads correct letter with large canvas
- [ ] Ghost replay deploys after 2 failed attempts
- [ ] Completion shows animated RewardBanner with XP

### Flow 2: Struggling Learner (seeded data)
- [ ] Login as seeded struggling learner account
- [ ] Dashboard shows frustration-aware recommendations
- [ ] Audio coaching tone is visibly softer
- [ ] Ghost replay deploys earlier (low frustration threshold)
- [ ] Session completion shows improved accuracy

### Flow 3: Parent Dashboard
- [ ] Login as parent account
- [ ] Insights dashboard shows 5 sections in adult order
- [ ] Recommendations are priority-ranked and actionable
- [ ] Analytics feel trustworthy, not overwhelming

---

## T11 — Advanced Product Hardening (14 Pillars)

| Pillar | Test | Status |
|--------|------|--------|
| 1. State Recovery | Browser refresh mid-session restores without corruption | 🔄 |
| 2. Touch Latency | Pointer-to-render imperceptible on iPad | 🔄 |
| 3. Audio Fatigue | 30-min session: no cognitive overload | 🔄 |
| 4. Child Chaos | Random tapping/scribbling does not crash | 🔄 |
| 5. Analytics Accuracy | Frustration/mastery trends match observed behavior | 🔄 |
| 6. Memory Leaks | 45-min session: 60fps maintained, no RAM growth | ✅ |
| 7. Offline/Bad Network | Slow 3G and reconnect handled gracefully | 🔄 |
| 8. Visual Consistency | Design tokens consistent across all screens | ✅ |
| 9. Educational Fairness | Struggling learners supported, not punished | 🔄 |
| 10. First-Time User | Onboarding friction minimal for uninformed user | 🔄 |
| 11. Longitudinal | 7-day sim: decay fair, reviews natural | 🔄 |
| 12. Logging Validation | Telemetry ordered, timestamped, no duplicates | 🔄 |
| 13. Human Observation | Mentors/parents/children test live | 🔄 |
| 14. Release Criteria | All P0 blockers resolved | 🔄 |

---

## Ship Criteria

### P0 — Blocking (must fix before any public deployment)
- Tracing lag or dropped frames
- Audio overlapping (multiple clips simultaneously)
- Session data corruption or duplicate analytics
- Auth failures (login/logout broken)
- Live database not connected

### P1 — Critical (fix before user testing)
- Visual inconsistencies (wrong tokens, layout breaks)
- Animation jitter on reward banner
- Analytics mismatch with actual behavior
- Ghost replay failing to deploy on hesitation

### P2 — Polish (fix before public launch)
- Minor visual bugs in edge-case layouts
- Decorative micro-animation timing
- Console warnings (Pydantic, SQLAlchemy deprecations)
