"""
app/services/analytics/confidence_analyzer.py — Behavioral Confidence Analysis

Interprets hesitation, retry, frustration, replay dependence, and recovery
patterns from raw session telemetry stored in PracticeSession.detailed_scores.

Internal sub-domains:
  1. Hesitation      — pauses before/between strokes
  2. Retry           — stroke attempt counts + failsafe rate
  3. Frustration     — composite of hesitation + retries + replay triggers
  4. Replay          — how often ghost replay was triggered
  5. Recovery        — does accuracy improve after failed attempts?

All functions snapshot-ready.
"""

import statistics
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Literal

from app.models.practice_session import PracticeSession


# ── 1. Hesitation sub-domain ──────────────────────────────────────────────────

def get_hesitation_profile(
    user_id: int,
    db: Session,
    limit: int = 20,
    snapshot: dict | None = None,
) -> dict:
    """
    Reads `detailed_scores.hesitation_ms_per_stroke` from recent sessions.
    Returns empty profile (not None) if no guidance-event data exists yet.
    """
    if snapshot:
        return snapshot.get("hesitation_profile", _empty_hesitation())

    rows = (
        db.query(
            PracticeSession.target_item,
            PracticeSession.detailed_scores,
        )
        .filter(
            PracticeSession.user_id      == user_id,
            PracticeSession.module_type  == "alphabet_practice",
            PracticeSession.is_completed == True,           # noqa: E712
            PracticeSession.detailed_scores.isnot(None),
        )
        .order_by(PracticeSession.completed_at.desc())
        .limit(limit)
        .all()
    )

    first_stroke_pauses: list[int] = []
    between_stroke_pauses: list[int] = []
    letter_pauses: dict[str, list[int]] = {}

    for row in rows:
        ds = row.detailed_scores or {}
        letter = row.target_item or "?"

        # time_before_first_stroke_ms (if stored at session level)
        first_ms = ds.get("time_before_first_stroke_ms")
        if isinstance(first_ms, int) and first_ms > 0:
            first_stroke_pauses.append(first_ms)
            letter_pauses.setdefault(letter, []).append(first_ms)

        # hesitation_ms_per_stroke: list of {stroke_id, ms}
        for entry in ds.get("hesitation_ms_per_stroke", []):
            ms = entry.get("ms", 0)
            if isinstance(ms, int) and ms > 0:
                between_stroke_pauses.append(ms)
                letter_pauses.setdefault(letter, []).append(ms)

    avg_first   = _safe_mean(first_stroke_pauses)
    avg_between = _safe_mean(between_stroke_pauses)

    # Letters ranked by avg hesitation
    letter_avgs = {
        k: _safe_mean(v) for k, v in letter_pauses.items() if v
    }
    sorted_letters = sorted(letter_avgs, key=lambda k: letter_avgs[k])
    threshold = avg_between * 1.4 if avg_between > 0 else 1500

    high_hesitation  = [l for l in sorted_letters if letter_avgs[l] > threshold][-5:]
    low_hesitation   = [l for l in sorted_letters if letter_avgs[l] <= threshold][:5]

    return {
        "avg_pause_before_first_stroke_ms": avg_first,
        "avg_pause_between_strokes_ms":     avg_between,
        "high_hesitation_letters":          high_hesitation,
        "low_hesitation_letters":           low_hesitation,
        "has_data":                         len(first_stroke_pauses) > 0 or len(between_stroke_pauses) > 0,
    }


def _empty_hesitation() -> dict:
    return {
        "avg_pause_before_first_stroke_ms": 0,
        "avg_pause_between_strokes_ms":     0,
        "high_hesitation_letters":          [],
        "low_hesitation_letters":           [],
        "has_data":                         False,
    }


# ── 2. Retry sub-domain ───────────────────────────────────────────────────────

def get_retry_pattern(
    user_id: int,
    db: Session,
    limit: int = 20,
    snapshot: dict | None = None,
) -> dict:
    """
    Reads `detailed_scores.stroke_attempt_counts` from recent sessions.
    Returns avg retries, high-retry letters, and failsafe unlock rate.
    """
    if snapshot:
        return snapshot.get("retry_pattern", _empty_retry())

    rows = (
        db.query(
            PracticeSession.target_item,
            PracticeSession.detailed_scores,
        )
        .filter(
            PracticeSession.user_id      == user_id,
            PracticeSession.module_type  == "alphabet_practice",
            PracticeSession.is_completed == True,       # noqa: E712
            PracticeSession.detailed_scores.isnot(None),
        )
        .order_by(PracticeSession.completed_at.desc())
        .limit(limit)
        .all()
    )

    all_retries:    list[int]         = []
    letter_retries: dict[str, list[int]] = {}
    total_strokes   = 0
    failsafe_count  = 0

    for row in rows:
        ds     = row.detailed_scores or {}
        letter = row.target_item or "?"
        counts = ds.get("stroke_attempt_counts", {})
        if not counts:
            continue
        for stroke_id, attempts in counts.items():
            if isinstance(attempts, int):
                all_retries.append(attempts)
                letter_retries.setdefault(letter, []).append(attempts)
                total_strokes += 1
                if attempts > 3:    # MAX_ATTEMPTS_FAILSAFE = 3
                    failsafe_count += 1

    avg_retries = _safe_mean(all_retries)

    letter_avgs = {k: _safe_mean(v) for k, v in letter_retries.items() if v}
    high_retry  = sorted(letter_avgs, key=lambda k: letter_avgs[k], reverse=True)[:5]

    failsafe_rate = round(failsafe_count / total_strokes, 4) if total_strokes > 0 else 0.0

    return {
        "avg_retries_per_stroke": avg_retries,
        "high_retry_letters":     high_retry,
        "failsafe_unlock_rate":   failsafe_rate,
        "total_strokes_analyzed": total_strokes,
        "has_data":               total_strokes > 0,
    }


def _empty_retry() -> dict:
    return {
        "avg_retries_per_stroke": 0.0,
        "high_retry_letters":     [],
        "failsafe_unlock_rate":   0.0,
        "total_strokes_analyzed": 0,
        "has_data":               False,
    }


# ── 3. Frustration sub-domain ─────────────────────────────────────────────────

def get_frustration_level(
    hesitation_profile: dict,
    retry_pattern: dict,
    replay_usage: dict,
    snapshot: dict | None = None,
) -> Literal["high", "medium", "low"]:
    """
    Composite frustration classification.
    high:   avg_retries > 2.5 AND avg_pause > 2500ms AND replay_rate > 0.30
    low:    avg_retries < 1.5 AND avg_pause < 1200ms
    medium: otherwise
    """
    if snapshot:
        return snapshot.get("frustration_level", "low")

    retries    = retry_pattern.get("avg_retries_per_stroke", 0.0)
    pause      = hesitation_profile.get("avg_pause_between_strokes_ms", 0)
    replay_rate = replay_usage.get("replay_rate", 0.0)

    if not retry_pattern.get("has_data") and not hesitation_profile.get("has_data"):
        return "low"     # no telemetry → assume low (Phase 2 users)

    if retries > 2.5 and pause > 2500 and replay_rate > 0.30:
        return "high"
    if retries < 1.5 and pause < 1200:
        return "low"
    return "medium"


# ── 4. Replay dependence sub-domain ──────────────────────────────────────────

def get_replay_dependence(
    user_id: int,
    db: Session,
    limit: int = 20,
    snapshot: dict | None = None,
) -> dict:
    """
    Reads guidance event data embedded in detailed_scores to estimate how
    often ghost replay was triggered per session.

    Phase 3 stores stroke_attempt_counts — high attempt count on same stroke
    is a proxy for replay triggers (direct replay tracking in Phase 4+).
    """
    if snapshot:
        return snapshot.get("replay_dependence", _empty_replay())

    retry = get_retry_pattern(user_id, db, limit)
    if not retry["has_data"]:
        return _empty_replay()

    # Proxy: strokes with > 2 attempts indicate user likely saw ghost replay
    rows = (
        db.query(
            PracticeSession.target_item,
            PracticeSession.detailed_scores,
        )
        .filter(
            PracticeSession.user_id      == user_id,
            PracticeSession.module_type  == "alphabet_practice",
            PracticeSession.is_completed == True,       # noqa: E712
            PracticeSession.detailed_scores.isnot(None),
        )
        .order_by(PracticeSession.completed_at.desc())
        .limit(limit)
        .all()
    )

    total_strokes    = 0
    replay_triggered = 0
    letter_replays: dict[str, int] = {}

    for row in rows:
        ds     = row.detailed_scores or {}
        letter = row.target_item or "?"
        counts = ds.get("stroke_attempt_counts", {})
        for _, attempts in counts.items():
            total_strokes += 1
            if isinstance(attempts, int) and attempts > 2:
                replay_triggered += 1
                letter_replays[letter] = letter_replays.get(letter, 0) + 1

    replay_rate = round(replay_triggered / total_strokes, 4) if total_strokes > 0 else 0.0
    most_replayed = sorted(letter_replays, key=lambda k: letter_replays[k], reverse=True)[:3]

    return {
        "replay_rate":          replay_rate,
        "most_replayed_letters": most_replayed,
        "replay_beneficial":    replay_rate > 0.15,  # meaningful replay usage
        "has_data":             total_strokes > 0,
    }


def _empty_replay() -> dict:
    return {"replay_rate": 0.0, "most_replayed_letters": [],
            "replay_beneficial": False, "has_data": False}


# ── 5. Recovery patterns sub-domain ──────────────────────────────────────────

def get_recovery_patterns(
    user_id: int,
    db: Session,
    limit: int = 20,
    snapshot: dict | None = None,
) -> dict:
    """
    Detects whether accuracy improves after failed attempts.
    Uses attempt_number field in PracticeSession:
      attempt 1 vs attempt 2 on the same target_item.
    """
    if snapshot:
        return snapshot.get("recovery_patterns", _empty_recovery())

    # Get items practiced more than once
    pairs = (
        db.query(
            PracticeSession.target_item,
            PracticeSession.attempt_number,
            PracticeSession.accuracy_score,
        )
        .filter(
            PracticeSession.user_id       == user_id,
            PracticeSession.module_type   == "alphabet_practice",
            PracticeSession.is_completed  == True,          # noqa: E712
            PracticeSession.accuracy_score.isnot(None),
            PracticeSession.attempt_number <= 2,
        )
        .order_by(PracticeSession.target_item, PracticeSession.attempt_number)
        .limit(limit * 2)
        .all()
    )

    # Group by target_item
    by_item: dict[str, dict[int, float]] = {}
    for row in pairs:
        if row.target_item:
            by_item.setdefault(row.target_item, {})[row.attempt_number] = row.accuracy_score

    improvements = []
    for item, attempts in by_item.items():
        if 1 in attempts and 2 in attempts:
            improvements.append(attempts[2] - attempts[1])

    if not improvements:
        return _empty_recovery()

    avg_improvement = _safe_mean(improvements)
    recovers_quickly = avg_improvement > 0.05   # improved by > 5% on retry

    return {
        "recovers_quickly":           recovers_quickly,
        "avg_improvement_after_retry": round(avg_improvement, 4),
        "items_analyzed":             len(improvements),
        "has_data":                   True,
    }


def _empty_recovery() -> dict:
    return {"recovers_quickly": False, "avg_improvement_after_retry": 0.0,
            "items_analyzed": 0, "has_data": False}


# ── Confidence level (composite) ──────────────────────────────────────────────

def get_confidence_level(
    hesitation: dict,
    retries: dict,
    frustration: str,
    recovery: dict,
) -> Literal["high", "medium", "low", "unknown"]:
    """
    Composite confidence.
    Returns 'unknown' if no telemetry data is available (Phase 2 sessions).
    """
    if not hesitation.get("has_data") and not retries.get("has_data"):
        return "unknown"

    avg_pause   = hesitation.get("avg_pause_between_strokes_ms", 0)
    avg_retries = retries.get("avg_retries_per_stroke", 0.0)
    failsafe    = retries.get("failsafe_unlock_rate", 0.0)

    if frustration == "high":
        return "low"
    if avg_pause < 1000 and avg_retries < 1.2 and failsafe < 0.05:
        return "high"
    if avg_pause > 3000 or avg_retries > 2.5 or failsafe > 0.20:
        return "low"
    return "medium"


# ── Direction struggle ─────────────────────────────────────────────────────────

def get_direction_struggle(
    user_id: int,
    db: Session,
    limit: int = 20,
    snapshot: dict | None = None,
) -> list[str]:
    """
    Identifies which stroke directions have the worst combined_score.
    Reads from PracticeSession.detailed_scores.stroke_attempt_counts
    as a proxy (direct direction scores stored in Phase 4+).
    """
    if snapshot:
        return snapshot.get("direction_struggle", [])

    # High retry letters correlate with direction difficulty
    retry = get_retry_pattern(user_id, db, limit)
    # Map letters to likely stroke types based on known difficulty patterns
    difficult_curves = {"S", "G", "C", "O", "Q", "B", "D"}
    difficult_diag   = {"X", "W", "V", "Y", "Z", "K"}

    high_retry = set(retry.get("high_retry_letters", []))
    struggles  = []
    if high_retry & difficult_curves:
        struggles.append("curve-left")
        struggles.append("curve-right")
    if high_retry & difficult_diag:
        struggles.append("down-right")
        struggles.append("down-left")
    return struggles[:4]   # cap at 4 directions


# ── Utility ────────────────────────────────────────────────────────────────────

def _safe_mean(values: list) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)
