# AksharabyasaAI — AI/ML Codebase Map

> **Version:** 2.0.0 | All files are Python (.py) unless noted.  
> All paths are relative to `handwriting-ai-system/`

---

## 🗺️ Folder Structure Overview

```
handwriting-ai-system/
│
├── app/ai/                        ← Layer 1: Core AI Pipeline (image/stroke analysis)
│   ├── features/                  ← Feature extraction algorithms
│   ├── intelligence/              ← Scoring, confidence, feedback
│   ├── learning/                  ← Gamification + user history
│   ├── models/                    ← Dataset collection
│   ├── pipeline/                  ← End-to-end processing pipeline
│   ├── preprocessing/             ← Image prep (grayscale, noise, deskew)
│   ├── segmentation/              ← Line/word/character detection
│   ├── tts/                       ← Text-to-speech feedback
│   └── utils/                     ← Geometry, I/O, logging helpers
│
├── app/services/                  ← Layer 2-4: Business + AI Services
│   ├── guidance_handler.py        ← Real-time stroke guidance engine
│   ├── learning_engine.py         ← Behavioral analytics + learner style classifier
│   ├── difficulty_adapter.py      ← Promotes/demotes difficulty from rolling window
│   ├── profile_service.py         ← Profile type derivation + coaching tone mapping
│   ├── reward_service.py          ← XP + reward calculation
│   │
│   ├── ml/                        ← Layer 3: ML Intelligence (adaptive recommendations)
│   ├── analytics/                 ← Layer 2: Behavioral Analytics Engine
│   ├── curriculum/                ← Layer 4: Adaptive Curriculum Engine (DAG + Mastery)
│   ├── audio/                     ← Declarative audio coaching system
│   └── spelling/                  ← Literacy state machine
│
└── tests/                         ← AI/ML unit tests (198 total)
```

---

## 📁 `app/ai/` — Core AI Pipeline (Layer 1)

Raw image and stroke processing. **Pure deterministic algorithms — no neural networks.**

### `app/ai/features/` — Feature Extraction

| File | What it does |
|------|-------------|
| [feature_pipeline.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\feature_pipeline.py) | Orchestrates full feature extraction from a stroke/image |
| [stroke_features.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\stroke_features.py) | **Coverage score, direction score, smoothness score, path error** — the 4 core stroke metrics |
| [character_features.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\character_features.py) | Per-character shape feature extraction |
| [line_features.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\line_features.py) | Line-level metrics (baseline, ascent, descent) |
| [slant_features.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\slant_features.py) | Writing slant angle detection |
| [spacing_features.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\spacing_features.py) | Inter-character and inter-word spacing |
| [word_features.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\word_features.py) | Word-level bounding box and density features |
| [baseline_features.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\baseline_features.py) | Writing baseline detection |
| [feature_schema.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\features\feature_schema.py) | Pydantic schema for feature vectors |

### `app/ai/intelligence/` — Scoring & Confidence

| File | What it does |
|------|-------------|
| [scoring.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\intelligence\scoring.py) | Weighted composite score from individual feature scores |
| [confidence.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\intelligence\confidence.py) | Confidence band calculation (high/medium/low) |
| [feedback_engine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\intelligence\feedback_engine.py) | Maps score ranges → actionable feedback messages |
| [normalization.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\intelligence\normalization.py) | Score normalization across feature dimensions |
| [validation.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\intelligence\validation.py) | Input validation before scoring pipeline |

### `app/ai/preprocessing/` — Image Preprocessing

| File | What it does |
|------|-------------|
| [preprocessing_pipeline.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\preprocessing\preprocessing_pipeline.py) | Orchestrates all preprocessing steps |
| [grayscale.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\preprocessing\grayscale.py) | RGB → grayscale conversion |
| [noise_removal.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\preprocessing\noise_removal.py) | Gaussian blur + morphological noise reduction |
| [thresholding.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\preprocessing\thresholding.py) | Adaptive Otsu thresholding → binary image |
| [deskew.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\preprocessing\deskew.py) | Rotation correction using Hough transform |
| [normalize.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\preprocessing\normalize.py) | Pixel normalization + canvas size standardization |

### `app/ai/segmentation/` — Line & Character Segmentation

| File | What it does |
|------|-------------|
| [segmentation_pipeline.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\segmentation\segmentation_pipeline.py) | Full segmentation orchestrator |
| [line_segmentation.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\segmentation\line_segmentation.py) | Horizontal projection profile → line detection |
| [word_segmentation.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\segmentation\word_segmentation.py) | Vertical projection → word bounding boxes |
| [contour_detection.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\segmentation\contour_detection.py) | OpenCV contour-based letter isolation |
| [projection_profiles.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\segmentation\projection_profiles.py) | Pixel density profiles for splitting lines/words |

### `app/ai/pipeline/` — End-to-End Pipeline

| File | What it does |
|------|-------------|
| [pipeline_controller.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\pipeline\pipeline_controller.py) | Runs: preprocess → segment → extract features → score |
| [batch_processor.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\pipeline\batch_processor.py) | Processes multiple submissions in parallel |

### `app/ai/learning/` — Gamification & History

| File | What it does |
|------|-------------|
| [gamification.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\learning\gamification.py) | XP calculation, level thresholds, streak bonuses |
| [user_history.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\ai\learning\user_history.py) | Session history aggregation for ML features |

---

## 📁 `app/services/guidance_handler.py` — Real-Time Stroke Engine

> **The most performance-critical file.** This is what runs on every stroke.

- State machine: tracks which stroke is active, how many attempts made
- Computes `trace_percent` (weighted coverage of completed strokes)
- Fires **failsafe** after `max_attempts` — auto-unlocks next stroke
- Returns `coaching_event` signal for audio engine

---

## 📁 `app/services/learning_engine.py` — Behavioral ML Engine

> Classifies HOW the learner behaves, not just WHAT they draw.

- Reads session telemetry (hesitation latency, failsafe triggers, replay count)
- Computes **Frustration Index** (0.0 → 1.0)
- Classifies `learner_style` ∈ `{methodical, replay_dependent, frustrated, confident}`
- Outputs behavioral analytics for the frontend Insights dashboard

---

## 📁 `app/services/ml/` — ML Intelligence Layer (Layer 3)

| File | What it does |
|------|-------------|
| [recommendation_engine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\ml\recommendation_engine.py) | **Master recommender** — outputs prioritized list of what to practice next |
| [adaptive_session_planner.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\ml\adaptive_session_planner.py) | Plans a full session: which items, what order, what difficulty |
| [difficulty_predictor.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\ml\difficulty_predictor.py) | Predicts optimal difficulty from rolling accuracy history |
| [item_recommender.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\ml\item_recommender.py) | Picks the right letter/word for the next session |
| [pattern_classifier.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\ml\pattern_classifier.py) | Classifies behavioral pattern from feature snapshot |
| [feature_snapshot.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\ml\feature_snapshot.py) | Extracts ML feature vector from raw session telemetry |

---

## 📁 `app/services/analytics/` — Behavioral Analytics Engine (Layer 2)

| File | What it does |
|------|-------------|
| [analytics_service.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\analytics\analytics_service.py) | Main analytics orchestrator — powers all `/analytics/*` endpoints |
| [confidence_analyzer.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\analytics\confidence_analyzer.py) | Confidence level derivation from accuracy + variance trends |
| [learning_insight_engine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\analytics\learning_insight_engine.py) | Generates human-readable insight cards (strengths, weaknesses, behavioral patterns) |
| [engagement_analyzer.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\analytics\engagement_analyzer.py) | Streak status, practice pattern (consistent/irregular/weekend-heavy) |
| [progress_aggregator.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\analytics\progress_aggregator.py) | Weekly accuracy rolling averages, velocity (fast/steady/slow) |
| [difficulty_trends.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\analytics\difficulty_trends.py) | Difficulty progression trend over time |

---

## 📁 `app/services/curriculum/` — Adaptive Curriculum Engine (Layer 4)

| File | What it does |
|------|-------------|
| [curriculum_graph.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\curriculum_graph.py) | **DAG graph** — defines all skill nodes and prerequisite edges |
| [mastery_engine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\mastery_engine.py) | Multi-dimensional mastery: motor + cognitive + retention |
| [review_scheduler.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\review_scheduler.py) | Ebbinghaus forgetting curve → schedules spaced repetition reviews |
| [plateau_detector.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\plateau_detector.py) | Detects flat accuracy velocity → triggers intervention |
| [progression_rules.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\progression_rules.py) | Confidence-gating rules (prevents lucky unlock) |
| [learning_journey_engine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\learning_journey_engine.py) | Orchestrates the full long-term learning journey |
| [educational_state_engine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\educational_state_engine.py) | Overall educational state manager |
| [mastery_snapshot.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\mastery_snapshot.py) | Point-in-time mastery snapshots for trend tracking |
| [skill_tree.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\curriculum\skill_tree.py) | Skill dependency tree (which skills unlock what) |

---

## 📁 `app/services/audio/` — Declarative Audio Coaching

| File | What it does |
|------|-------------|
| [audio_orchestrator.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\audio_orchestrator.py) | **Master audio decision engine** — adjudicates what audio to play |
| [coaching_policy.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\coaching_policy.py) | Cooldown rules, verbosity limits, frustration overrides |
| [coaching_event_mapper.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\coaching_event_mapper.py) | Maps `direction_failure` → audio clip URL |
| [audio_profiles.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\audio_profiles.py) | Per-profile audio intensity (early_learner gets more celebration) |
| [phonetic_mapper.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\phonetic_mapper.py) | 26 letters + blends → phoneme → audio URL |
| [pronunciation_service.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\pronunciation_service.py) | Resolves pronunciation URLs for letters and words |
| [coaching_audio_service.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\coaching_audio_service.py) | Selects appropriate coaching clip by event + frustration level |
| [celebration_audio.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\celebration_audio.py) | Milestone and completion celebration audio |
| [audio_cache.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\audio\audio_cache.py) | Local TTS audio caching |

---

## 📁 `app/services/spelling/` — Literacy State Machine

| File | What it does |
|------|-------------|
| [spelling_state_machine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\spelling\spelling_state_machine.py) | State transitions: idle→attempting→partial_success→correct |
| [literacy_orchestrator.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\spelling\literacy_orchestrator.py) | Full spelling session orchestration |
| [assist_profiles.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\spelling\assist_profiles.py) | Forgiveness levels, ghost word toggle, hint display |
| [spelling_feedback.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\spelling\spelling_feedback.py) | Per-letter feedback generation |
| [word_packs.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\app\services\spelling\word_packs.py) | CVC words, sight words, double-letter word packs |

---

## 📁 `tests/` — AI/ML Test Suite (198 Tests)

| File | Tests | What it covers |
|------|-------|----------------|
| [test_stroke_analyzer.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\tests\test_stroke_analyzer.py) | ~46 | Direction, coverage, smoothness, path error, guidance handler, difficulty adapter |
| [test_analytics_service.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\tests\test_analytics_service.py) | ~44 | Engagement analyzer, confidence analyzer, insight engine, progress aggregator |
| [test_phase2_learning_engine.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\tests\test_phase2_learning_engine.py) | ~46 | Behavioral analytics, frustration index, learner style classifier |
| [test_ml_recommendations.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\tests\test_ml_recommendations.py) | ~33 | Recommendation engine, difficulty predictor, item recommender |
| [test_profile_service.py](c:\Users\Dev Mehta\Desktop\Image Analysis\handwriting-ai-system\tests\test_profile_service.py) | ~29 | Profile type derivation, learning profiles, feedback tone |

---

## 🧠 The 4 AI Layers — Summary

```
Layer 1: app/ai/                    Pure geometry algorithms
         (preprocessing → segmentation → features → scoring)
         Runs on image upload and stroke submission

Layer 2: app/services/analytics/    Behavioral pattern recognition
         app/services/learning_engine.py
         Reads session history → frustration, confidence, learner style

Layer 3: app/services/ml/           Adaptive ML intelligence
         Predicts difficulty, recommends items, plans sessions
         Uses Layer 2 outputs as input features

Layer 4: app/services/curriculum/   Long-term educational progression
         DAG graph, mastery decay, spaced repetition
         Uses Layer 3 outputs to drive curriculum unlocks
```
