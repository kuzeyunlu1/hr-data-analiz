"""Typed loading of the Phase 2 config files (redaction.yaml, codebook.yaml, llm.yaml).

Kept apart from hrsurvey.config so Phase 1 commands never need spaCy, lingua or the LLM settings.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from hrsurvey.config import Config, read_yaml
from hrsurvey.errors import ConfigError
from hrsurvey.status import Status

NEW_THEME = "NEW"
Effort = Literal["low", "medium", "high", "xhigh", "max"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PatternRule(_Frozen):
    name: str
    regex: str
    placeholder: str
    min_digits: int = 0
    exclude_regex: str | None = None  # matches that fully match this are kept

    @model_validator(mode="after")
    def _compiles(self) -> PatternRule:
        try:
            re.compile(self.regex)
        except re.error as err:
            raise ValueError(f"redaction pattern {self.name}: {err}") from err
        return self


class RedactionConfig(_Frozen):
    spacy_models: dict[Literal["en", "de"], str]
    min_language_confidence: float
    entities: dict[str, str]
    patterns: tuple[PatternRule, ...]
    allowlist: tuple[str, ...] = ()


class CodebookExampleSegment(_Frozen):
    text_en: str
    theme: str
    locus: str
    valence: Literal[-1, 0, 1]
    intensity: Literal[1, 2, 3]
    secondary_theme: str | None = None
    sarcasm: bool = False


class CodebookExample(_Frozen):
    question: str
    answer: str
    segments: tuple[CodebookExampleSegment, ...]


class Codebook(_Frozen):
    version: str
    themes: dict[str, str]
    locus: dict[str, str]
    rules: tuple[str, ...]
    examples: tuple[CodebookExample, ...] = ()

    @model_validator(mode="after")
    def _examples_use_known_codes(self) -> Codebook:
        if NEW_THEME in self.themes:
            raise ValueError(f"{NEW_THEME!r} is reserved for unknown themes")
        for example in self.examples:
            for seg in example.segments:
                for theme in (seg.theme, seg.secondary_theme):
                    if theme is not None and theme not in self.themes:
                        raise ValueError(f"example uses unknown theme {theme}")
                if seg.locus not in self.locus:
                    raise ValueError(f"example uses unknown locus {seg.locus}")
        return self


class EngagementBandConfig(_Frozen):
    items: tuple[str, ...]
    favorable_min_pomp: float
    unfavorable_max_pomp: float


class LlmConfig(_Frozen):
    model: str
    effort: Effort
    max_tokens: int
    fallbacks: Literal["default"] | None = None
    fallback_beta: str | None = None
    max_workers: int = Field(default=4, ge=1, le=16)
    send_statuses: tuple[Status, ...]
    engagement_band: EngagementBandConfig
    deterministic_codes: dict[str, dict[Status, str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _fallback_needs_beta(self) -> LlmConfig:
        if self.fallbacks and not self.fallback_beta:
            raise ValueError("fallbacks requires fallback_beta")
        allowed = {Status.SUBSTANTIVE, Status.NO_ISSUE, Status.NOTHING_TO_ADD}
        if not set(self.send_statuses) <= allowed:
            raise ValueError(f"send_statuses must be a subset of {sorted(allowed)}")
        return self


class TextConfig(_Frozen):
    redaction: RedactionConfig
    codebook: Codebook
    llm: LlmConfig


_FILES = {"redaction": "redaction.yaml", "codebook": "codebook.yaml", "llm": "llm.yaml"}


def load_text_config(config_dir: Path, config: Config) -> TextConfig:
    """Load Phase 2 config and cross-check it against the survey schema and the codebook."""
    raw = {key: read_yaml(config_dir / name) for key, name in _FILES.items()}
    try:
        text = TextConfig.model_validate(raw)
    except ValidationError as err:
        raise ConfigError(f"invalid Phase 2 configuration in {config_dir}:\n{err}") from err
    var_ids = {c.var_id for c in config.survey.columns}
    problems = [
        f"engagement_band item {v} not in schema"
        for v in text.llm.engagement_band.items
        if v not in var_ids
    ]
    for var_id, by_status in text.llm.deterministic_codes.items():
        if var_id not in var_ids:
            problems.append(f"deterministic_codes var {var_id} not in schema")
        problems += [
            f"deterministic code {t} not in codebook"
            for t in by_status.values()
            if t not in text.codebook.themes
        ]
    if problems:
        raise ConfigError("; ".join(problems))
    return text
