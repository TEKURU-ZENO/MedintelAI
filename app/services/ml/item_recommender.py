"""
app/services/ml/item_recommender.py — Practice Item Recommendation

Ranks letters/items by priority using weighted behavioral signals.
Output: ordered list of ItemRecommendation with confidence + source.

Priority scoring formula (weighted sum):
  priority = retry_weight * retry_signal
           + direction_weight * direction_signal
           + worst_letter_weight * worst_signal
           + frustration_penalty

Each output item:
  {item, priority_score, reason, confidence, source}
"""

from __future__ import annotations


# ── Weights ───────────────────────────────────────────────────────────────────

WEIGHT_RETRY       = 0.40   # highest — retry = direct signal of difficulty
WEIGHT_WORST_LETTER = 0.30  # accuracy-based signal
WEIGHT_DIRECTION   = 0.20   # direction struggle contribution
WEIGHT_FRUSTRATION = 0.10   # frustration-amplified priority

MAX_RECOMMENDATIONS = 5


# ── Difficulty buckets ────────────────────────────────────────────────────────

_DIFFICULT_CURVES = {"S", "G", "C", "O", "Q", "B", "D", "J", "U"}
_DIFFICULT_DIAG   = {"X", "W", "V", "Y", "Z", "K", "N", "M"}
_EASY_LETTERS     = {"L", "I", "T", "F", "E", "H"}


def _direction_signal(letter: str, direction_struggles: list[str]) -> float:
    """0-1: how much this letter's stroke direction is a known struggle."""
    if not direction_struggles:
        return 0.0
    curve_struggle = any("curve" in d for d in direction_struggles)
    diag_struggle  = any(d in ("down-right", "down-left") for d in direction_struggles)
    if letter in _DIFFICULT_CURVES and curve_struggle:
        return 1.0
    if letter in _DIFFICULT_DIAG and diag_struggle:
        return 0.8
    return 0.0


def _frustration_amplifier(frustration_level: str) -> float:
    """Frustrated users benefit more from targeted easy wins + hard challenges."""
    return {"high": 1.3, "medium": 1.0, "low": 0.85}.get(frustration_level, 1.0)


def score_item(
    letter:             str,
    worst_letters:      list[str],
    high_retry_letters: list[str],
    direction_struggles: list[str],
    frustration_level:  str,
) -> float:
    """Weighted priority score for a single letter."""
    worst_rank  = 1.0 if letter in worst_letters[:3] else (0.5 if letter in worst_letters else 0.0)
    retry_rank  = 1.0 if letter in high_retry_letters[:3] else (0.5 if letter in high_retry_letters else 0.0)
    dir_signal  = _direction_signal(letter, direction_struggles)
    amp         = _frustration_amplifier(frustration_level)

    raw = (
        WEIGHT_RETRY        * retry_rank
        + WEIGHT_WORST_LETTER * worst_rank
        + WEIGHT_DIRECTION    * dir_signal
        + WEIGHT_FRUSTRATION  * (1.0 if frustration_level == "high" else 0.0)
    )
    return round(min(1.0, raw * amp), 4)


def _reason_for(
    letter:             str,
    worst_letters:      list[str],
    high_retry_letters: list[str],
    direction_struggles: list[str],
) -> str:
    reasons = []
    if letter in high_retry_letters[:3]:
        reasons.append("highest retry rate")
    elif letter in worst_letters[:3]:
        reasons.append("lowest accuracy")
    if any("curve" in d for d in direction_struggles) and letter in _DIFFICULT_CURVES:
        reasons.append("curved stroke struggle")
    if any(d in ("down-right", "down-left") for d in direction_struggles) and letter in _DIFFICULT_DIAG:
        reasons.append("diagonal stroke challenge")
    return ", ".join(reasons) if reasons else "needs attention"


def recommend_items(
    worst_letters:       list[str],
    high_retry_letters:  list[str],
    direction_struggles: list[str],
    frustration_level:   str,
    best_letters:        list[str],
    data_completeness:   float = 1.0,
) -> list[dict]:
    """
    Returns ordered list of ItemRecommendation dicts.
    Always includes:
      - Top struggle items (high priority)
      - One "reinforce strength" item (low priority) for motivation
    """
    # Candidate pool: all struggling letters
    candidates = set(worst_letters) | set(high_retry_letters)

    # Add direction-struggle letters if not already present
    for letter in list(_DIFFICULT_CURVES | _DIFFICULT_DIAG):
        if letter in high_retry_letters or letter in worst_letters:
            candidates.add(letter)

    if not candidates:
        # No data → recommend easy well-known letters to build confidence
        candidates = {"A", "L", "I", "T", "O"}

    # Score each candidate
    scored = []
    for letter in candidates:
        s = score_item(letter, worst_letters, high_retry_letters,
                       direction_struggles, frustration_level)
        reason = _reason_for(letter, worst_letters, high_retry_letters, direction_struggles)
        scored.append({
            "item":           letter,
            "priority_score": s,
            "reason":         reason,
            "priority":       "high" if s >= 0.6 else ("medium" if s >= 0.35 else "low"),
            "confidence":     round(data_completeness * min(0.95, 0.5 + s * 0.5), 4),
            "source":         "rule_weighted",
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["priority_score"], reverse=True)
    result = scored[:MAX_RECOMMENDATIONS - 1]   # leave room for strength item

    # Add one strength reinforcement item (motivation)
    if best_letters:
        strength = best_letters[0]
        result.append({
            "item":           strength,
            "priority_score": 0.1,
            "reason":         "reinforce recent strength",
            "priority":       "low",
            "confidence":     round(data_completeness * 0.70, 4),
            "source":         "rule_weighted",
        })

    return result
