from __future__ import annotations

import pytest

from hrsurvey.config import Config
from hrsurvey.scoring import favorability, pomp


@pytest.mark.parametrize(
    ("scale_id", "code", "polarity", "expected"),
    [
        ("SAT5", 1, "+", 0.0),
        ("SAT5", 4, "+", 75.0),
        ("SAT5", 5, "+", 100.0),
        ("DIFFICULTY5", 1, "-", 100.0),  # "not difficult at all" is the healthy end
        ("EXTENT5", 3, "-", 50.0),
        ("NUM0_10", 7, "+", 70.0),
        ("NUM0_10", 0, "+", 0.0),
    ],
)
def test_pomp_is_polarity_corrected(
    config: Config, scale_id: str, code: int, polarity: str, expected: float
) -> None:
    assert pomp(code, config.scales[scale_id], polarity) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("scale_id", "score", "bucket"),
    [
        ("SAT5", 100.0, "favorable"),
        ("SAT5", 75.0, "favorable"),
        ("SAT5", 50.0, "neutral"),
        ("SAT5", 25.0, "unfavorable"),
        ("NUM0_10", 70.0, "favorable"),
        ("NUM0_10", 60.0, "neutral"),
        ("NUM0_10", 40.0, "unfavorable"),
    ],
)
def test_favorability_uses_configured_cutoffs(
    config: Config, scale_id: str, score: float, bucket: str
) -> None:
    assert favorability(score, config.scoring.cutoffs_for(scale_id)) == bucket
