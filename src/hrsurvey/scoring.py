"""Stage 6: comparable scores (docs/05-standardization.md#scoring)."""

from __future__ import annotations

from hrsurvey.config import FavorabilityCutoffs, Polarity, ScaleSpec

FAVORABLE = "favorable"
NEUTRAL = "neutral"
UNFAVORABLE = "unfavorable"


def pomp(code: int, spec: ScaleSpec, polarity: Polarity) -> float:
    """Percent of maximum possible, 0–100, oriented so that higher is always healthier."""
    score = (code - spec.min) / (spec.max - spec.min) * 100
    return 100.0 - score if polarity == "-" else score


def favorability(score: float, cutoffs: FavorabilityCutoffs) -> str:
    if score >= cutoffs.favorable_min_pomp:
        return FAVORABLE
    if score <= cutoffs.unfavorable_max_pomp:
        return UNFAVORABLE
    return NEUTRAL
