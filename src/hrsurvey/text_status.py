"""Stage 5: normalize free text and classify its response status.

docs/05-standardization.md#response-status-taxonomy. Phase 2 adds an LLM fallback for cases the
patterns cannot decide; this module is the deterministic first pass.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from hrsurvey.config import NonAnswerConfig, ResidualConfig
from hrsurvey.status import PATTERN_STATUSES, Status

_APOSTROPHES = str.maketrans({"´": "'", "’": "'", "‘": "'", "`": "'"})
_WHITESPACE = re.compile(r"\s+")
_WORD = re.compile(r"\w+(?:'\w+)?")  # "i'll" is one word; punctuation is not a word


def normalize_text(raw: str) -> str:
    """NFC, unified apostrophes, collapsed whitespace. Meaning-preserving only."""
    text = unicodedata.normalize("NFC", raw).translate(_APOSTROPHES)
    return _WHITESPACE.sub(" ", text).strip()


@dataclass(frozen=True)
class PatternMatch:
    status: Status
    start: int
    end: int


class TextClassifier:
    def __init__(self, cfg: NonAnswerConfig) -> None:
        self._residual = cfg.residual
        self._placeholders = tuple(re.compile(p) for p in cfg.placeholder)
        self._patterns = tuple(
            (status, re.compile(pattern))
            for status in PATTERN_STATUSES
            for pattern in cfg.patterns.get(status.value, ())
        )

    def first_match(self, lowered: str) -> PatternMatch | None:
        for status, pattern in self._patterns:
            found = pattern.search(lowered)
            if found:
                return PatternMatch(status, found.start(), found.end())
        return None

    def classify(self, raw: str) -> Status:
        lowered = normalize_text(raw).lower()
        if not lowered:
            return Status.EMPTY
        if any(p.match(lowered) for p in self._placeholders):
            return Status.PLACEHOLDER
        match = self.first_match(lowered)
        if match is None:
            return Status.SUBSTANTIVE
        residual = lowered[: match.start] + " " + lowered[match.end :]
        return resolve_residual(match.status, residual, self._residual)


def resolve_residual(matched: Status, residual: str, cfg: ResidualConfig) -> Status:
    """Decide whether an answer that matched a non-answer pattern still carries real content.

    `matched`  — the non-answer status whose pattern matched (NO_ISSUE, NO_BASIS, NOTHING_TO_ADD)
    `residual` — the lower-cased text left after removing the matched phrase,
                 e.g. "No obstacle, but the VPN drops daily." -> ", but the vpn drops daily."
    `cfg`      — cfg.max_words (int) and cfg.contrast_markers (tuple of single lower-case words)

    Return `matched` if the answer is still a non-answer, otherwise Status.SUBSTANTIVE.
    Ambiguity resolves towards SUBSTANTIVE: losing a complaint costs more than a little noise,
    which the Phase 2 coder can still discard. Behaviour is pinned down in test_text_status.py.
    """
    words = _WORD.findall(residual.lower())
    if any(word in cfg.contrast_markers for word in words):
        return Status.SUBSTANTIVE  # "no obstacle, but …" pivots to a real complaint
    if len(words) > cfg.max_words:
        return Status.SUBSTANTIVE  # a long elaboration carries content of its own
    return matched
