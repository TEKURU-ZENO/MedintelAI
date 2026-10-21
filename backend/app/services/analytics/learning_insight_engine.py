"""
app/services/analytics/learning_insight_engine.py — Educational Interpretation Layer

Converts raw telemetry signals into structured InsightItem objects.
This is what separates an analytics platform from an educational intelligence system.

Rules:
  - Never queries DB directly.
  - Never formats strings based on profile_type (that is UI responsibility).
  - Returns InsightItem dicts — analytics_service.py assembles them into DTOs.
  - All outputs are deterministic given the same inputs (pure functions).

InsightItem schema (matches schemas/analytics.py):
  { code: str, severity: str, message: str }
"""

from typing import TypedDict, Literal

SeverityType = Literal["positive", "low", "medium", "high"]


class InsightItem(TypedDict):
    code:     str
    severity: SeverityType
    message:  str


def _item(code: str, severity: SeverityType, message: str) -> InsightItem:
    return InsightItem(code=code, severity=severity, message=message)


# ──────────────────────────────────────────────────────────────────────────────
# Strength insights
# ──────────────────────────────────────────────────────────────────────────────

def generate_strength_insights(
    best_letters:      list[str],
    recovery:          dict,
    replay_dependence: dict,
    consistency:       dict,
) -> list[InsightItem]:
    """
    Generates positive InsightItems from strong signals.
    Never returns empty list if there are ANY positive signals.
    """
    items: list[InsightItem] = []

    # ── Best letters ──────────────────────────────────────────────────────────
    if best_letters:
        letters_str = ", ".join(best_letters[:3])
        items.append(_item(
            code     = "strong_letters",
            severity = "positive",
            message  = f"Excellent accuracy on letters {letters_str}",
        ))

    # ── Fast recovery ─────────────────────────────────────────────────────────
    if recovery.get("recovers_quickly") and recovery.get("avg_improvement_after_retry", 0) > 0.05:
        pct = round(recovery["avg_improvement_after_retry"] * 100)
        items.append(_item(
            code     = "fast_recovery",
            severity = "positive",
            message  = f"Improves by ~{pct}% on second attempt — fast learner",
        ))

    # ── Consistent practice ───────────────────────────────────────────────────
    score = consistency.get("consistency_score", 0.0)
    if score >= 0.70:
        items.append(_item(
            code     = "consistent_practice",
            severity = "positive",
            message  = f"Practices consistently ({round(score * 100)}% of days active)",
        ))
    elif score >= 0.50:
        items.append(_item(
            code     = "good_consistency",
            severity = "positive",
            message  = "Good practice rhythm — keep it up",
        ))

    # ── Replay beneficial ─────────────────────────────────────────────────────
    if replay_dependence.get("replay_beneficial") and recovery.get("recovers_quickly"):
        items.append(_item(
            code     = "replay_beneficial",
            severity = "positive",
            message  = "Guided replay assistance is working well",
        ))

    return items


# ──────────────────────────────────────────────────────────────────────────────
# Weakness insights
# ──────────────────────────────────────────────────────────────────────────────

def generate_weakness_insights(
    worst_letters:      list[str],
    direction_struggle: list[str],
    retry_pattern:      dict,
    trend:              str,
) -> list[InsightItem]:
    """
    Generates weakness InsightItems from low-accuracy and high-retry signals.
    Severity escalates with combined evidence.
    """
    items: list[InsightItem] = []

    # ── Worst letters ─────────────────────────────────────────────────────────
    if worst_letters:
        letters_str = ", ".join(worst_letters[:3])
        # Severity based on how many worst letters
        sev: SeverityType = "high" if len(worst_letters) >= 3 else "medium"
        items.append(_item(
            code     = "weak_letters",
            severity = sev,
            message  = f"Needs more practice on letters {letters_str}",
        ))

    # ── Direction struggles ───────────────────────────────────────────────────
    has_curve_struggle = any("curve" in d for d in direction_struggle)
    has_diag_struggle  = any(d in ("down-right", "down-left") for d in direction_struggle)

    if has_curve_struggle:
        items.append(_item(
            code     = "curved_strokes",
            severity = "medium",
            message  = "Curved strokes need more attention (letters like S, G, C)",
        ))
    if has_diag_struggle:
        items.append(_item(
            code     = "diagonal_strokes",
            severity = "medium",
            message  = "Diagonal strokes need practice (letters like X, W, V)",
        ))

    # ── High retry letters ────────────────────────────────────────────────────
    high_retry = retry_pattern.get("high_retry_letters", [])
    if high_retry and retry_pattern.get("avg_retries_per_stroke", 0) > 1.8:
        letters_str = ", ".join(high_retry[:3])
        items.append(_item(
            code     = "high_retry_rate",
            severity = "medium",
            message  = f"Frequently retries {letters_str} — extra practice recommended",
        ))

    # ── Declining trend ───────────────────────────────────────────────────────
    if trend == "declining":
        items.append(_item(
            code     = "declining_accuracy",
            severity = "high",
            message  = "Accuracy has been declining recently — review recent sessions",
        ))

    return items


# ──────────────────────────────────────────────────────────────────────────────
# Behavioral / observational insights
# ──────────────────────────────────────────────────────────────────────────────

def generate_behavioral_insights(
    hesitation:         dict,
    frustration_level:  str,
    replay_dependence:  dict,
    consistency:        dict,
    engagement_level:   str,
) -> list[InsightItem]:
    """
    Generates human-readable behavioral observations from telemetry signals.
    These are not evaluative — they are descriptive coaching notes.
    """
    items: list[InsightItem] = []

    # ── Hesitation patterns ───────────────────────────────────────────────────
    avg_pause = hesitation.get("avg_pause_between_strokes_ms", 0)
    high_hes  = hesitation.get("high_hesitation_letters", [])

    if hesitation.get("has_data"):
        if avg_pause > 2500 and high_hes:
            letters_str = ", ".join(high_hes[:3])
            items.append(_item(
                code     = "hesitation_curves",
                severity = "medium",
                message  = f"Shows hesitation before strokes in {letters_str}",
            ))
        elif avg_pause > 1500:
            items.append(_item(
                code     = "general_hesitation",
                severity = "low",
                message  = "Takes time to plan strokes — deliberate approach",
            ))

    # ── Frustration risk ──────────────────────────────────────────────────────
    if frustration_level == "high":
        items.append(_item(
            code     = "frustration_risk",
            severity = "high",
            message  = "Needs encouragement during complex letters — showing frustration signals",
        ))
    elif frustration_level == "medium":
        items.append(_item(
            code     = "mild_frustration",
            severity = "low",
            message  = "Occasional difficulty — benefits from short breaks between sessions",
        ))

    # ── Replay dependence ─────────────────────────────────────────────────────
    replay_rate = replay_dependence.get("replay_rate", 0.0)
    if replay_rate > 0.30:
        items.append(_item(
            code     = "high_replay_dependence",
            severity = "low",
            message  = "Frequently uses guided replay — this is working, but encourage independent practice",
        ))
    elif replay_dependence.get("replay_beneficial"):
        items.append(_item(
            code     = "replay_positive",
            severity = "positive",
            message  = "Confidence improves with guided replay assistance",
        ))

    # ── Consistency observations ──────────────────────────────────────────────
    pattern = consistency.get("pattern", "irregular")
    if pattern == "weekday_only":
        items.append(_item(
            code     = "weekday_pattern",
            severity = "low",
            message  = "Practices mainly on weekdays — weekend sessions would boost progress",
        ))
    elif pattern == "weekend_heavy":
        items.append(_item(
            code     = "weekend_pattern",
            severity = "low",
            message  = "Weekend-heavy practice — daily short sessions are more effective",
        ))
    elif pattern == "irregular" and consistency.get("consistency_score", 0) < 0.35:
        items.append(_item(
            code     = "irregular_practice",
            severity = "medium",
            message  = "Irregular practice schedule — consistent daily practice accelerates learning",
        ))

    # ── Engagement observation ────────────────────────────────────────────────
    if engagement_level == "low":
        items.append(_item(
            code     = "low_engagement",
            severity = "medium",
            message  = "Engagement has dropped — try shorter, more frequent sessions",
        ))

    return items


# ──────────────────────────────────────────────────────────────────────────────
# Recommended focus (for ModuleGrid)
# ──────────────────────────────────────────────────────────────────────────────

def generate_recommended_focus(
    worst_letters:       list[str],
    frustration_level:   str,
    promotion_readiness: float,
    trend:               str,
    avg_accuracy:        float,
) -> str:
    """
    Returns a single actionable directive string.

    Values:
      "ready_to_advance"     — promotion_readiness >= 0.85
      "needs_more_practice"  — accuracy < 0.60 OR high frustration
      "review_basics"        — declining trend OR accuracy < 0.45
      "maintain_consistency" — on track
    """
    if trend == "declining" or avg_accuracy < 0.45:
        return "review_basics"
    if promotion_readiness >= 0.85:
        return "ready_to_advance"
    if avg_accuracy < 0.60 or frustration_level == "high":
        return "needs_more_practice"
    return "maintain_consistency"
