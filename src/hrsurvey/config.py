"""Typed loading of config/*.yaml — tunable values live in YAML, not code (DECISIONS D-004)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from hrsurvey.errors import ConfigError
from hrsurvey.status import PATTERN_STATUSES

ColumnType = Literal["timestamp", "scale", "numeric", "text"]
Polarity = Literal["+", "-"]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ColumnSpec(_Frozen):
    idx: int
    var_id: str
    q_no: str
    block: str
    type: ColumnType
    header_hash: str
    scale_id: str | None = None
    polarity: Polarity | None = None

    @model_validator(mode="after")
    def _closed_items_need_scale(self) -> ColumnSpec:
        closed = self.type in ("scale", "numeric")
        if closed and (self.scale_id is None or self.polarity is None):
            raise ValueError(f"{self.var_id}: closed items need scale_id and polarity")
        if not closed and (self.scale_id is not None or self.polarity is not None):
            raise ValueError(f"{self.var_id}: only closed items may have scale_id/polarity")
        return self

    @property
    def is_closed(self) -> bool:
        return self.type in ("scale", "numeric")


class TimestampSpec(_Frozen):
    column_idx: int
    regex: str
    date_format: str
    am_tokens: tuple[str, ...]
    pm_tokens: tuple[str, ...]


class SurveySchema(_Frozen):
    survey_id: str
    expected_columns: int
    timestamp: TimestampSpec
    branches: dict[str, str]  # block code -> branch name, e.g. T -> technical
    core_blocks: tuple[str, ...]
    columns: tuple[ColumnSpec, ...]

    @model_validator(mode="after")
    def _columns_are_complete(self) -> SurveySchema:
        if len(self.columns) != self.expected_columns:
            raise ValueError(
                f"{len(self.columns)} columns listed, {self.expected_columns} expected"
            )
        if [c.idx for c in self.columns] != list(range(self.expected_columns)):
            raise ValueError("column idx values must be 0..n-1 in order")
        var_ids = [c.var_id for c in self.columns]
        if len(var_ids) != len(set(var_ids)):
            raise ValueError("duplicate var_id in survey schema")
        return self

    def closed_columns(self) -> tuple[ColumnSpec, ...]:
        return tuple(c for c in self.columns if c.is_closed)

    def text_columns(self) -> tuple[ColumnSpec, ...]:
        return tuple(c for c in self.columns if c.type == "text")

    def branch_of(self, column: ColumnSpec) -> str | None:
        return self.branches.get(column.block)


class ScaleSpec(_Frozen):
    kind: Literal["ordinal", "numeric"]
    min: int
    max: int
    labels: dict[str, int] = Field(default_factory=dict)
    expected_labels: dict[str, int] = Field(default_factory=dict)
    na_labels: tuple[str, ...] = ()
    values: dict[int, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _codes_in_range(self) -> ScaleSpec:
        if self.min >= self.max:
            raise ValueError("min must be < max")
        codes = list(self.labels.values()) + list(self.expected_labels.values())
        if any(not self.min <= code <= self.max for code in codes):
            raise ValueError("label code outside [min, max]")
        if set(self.labels) & set(self.expected_labels):
            raise ValueError("a label is listed as both observed and expected")
        if self.kind == "ordinal" and not self.labels:
            raise ValueError("ordinal scales need at least one observed label")
        if self.values and set(self.values) != set(range(self.min, self.max + 1)):
            raise ValueError("values must define every code from min to max")
        return self


class ResidualConfig(_Frozen):
    max_words: int
    contrast_markers: tuple[str, ...]


class NonAnswerConfig(_Frozen):
    placeholder: tuple[str, ...]
    patterns: dict[str, tuple[str, ...]]
    residual: ResidualConfig
    meaningful_nothing_vars: tuple[str, ...]

    @model_validator(mode="after")
    def _known_statuses(self) -> NonAnswerConfig:
        allowed = {s.value for s in PATTERN_STATUSES}
        unknown = set(self.patterns) - allowed
        if unknown:
            raise ValueError(f"unknown pattern statuses: {sorted(unknown)}")
        return self


class InconsistencyConfig(_Frozen):
    target_item: str
    comparison_pattern: str
    min_comparison_items: int
    gap_pomp: float


class StraightlineConfig(_Frozen):
    min_items: int
    grids: dict[str, str]  # flag suffix -> var_id regex


class QualityConfig(_Frozen):
    inconsistency: InconsistencyConfig
    straightline: StraightlineConfig
    min_core_completion: float
    duplicate_min_answered_cells: int


class FavorabilityCutoffs(_Frozen):
    favorable_min_pomp: float
    unfavorable_max_pomp: float


class ScoringConfig(_Frozen):
    favorability_default: FavorabilityCutoffs
    favorability_overrides: dict[str, FavorabilityCutoffs] = Field(default_factory=dict)

    def cutoffs_for(self, scale_id: str) -> FavorabilityCutoffs:
        return self.favorability_overrides.get(scale_id, self.favorability_default)


class Config(_Frozen):
    survey: SurveySchema
    scales: dict[str, ScaleSpec]
    nonanswer: NonAnswerConfig
    quality: QualityConfig
    scoring: ScoringConfig

    @model_validator(mode="after")
    def _cross_references(self) -> Config:
        """Typos in one file must not silently disable behaviour defined in another."""
        problems = [
            *self._scale_problems(),
            *self._quality_problems(),
        ]
        unknown_vars = set(self.nonanswer.meaningful_nothing_vars) - {
            c.var_id for c in self.survey.columns
        }
        if unknown_vars:
            problems.append(f"meaningful_nothing_vars not in schema: {sorted(unknown_vars)}")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def _scale_problems(self) -> list[str]:
        problems = []
        missing = sorted(
            {c.scale_id for c in self.survey.closed_columns() if c.scale_id not in self.scales}
        )
        if missing:
            problems.append(f"scale_id(s) not defined in scales.yaml: {missing}")
        unknown = sorted(set(self.scoring.favorability_overrides) - set(self.scales))
        if unknown:
            problems.append(f"favorability_overrides for unknown scales: {unknown}")
        return problems

    def _quality_problems(self) -> list[str]:
        closed = {c.var_id for c in self.survey.closed_columns()}
        problems = []
        cfg = self.quality.inconsistency
        if cfg.target_item not in closed:
            problems.append("quality.inconsistency.target_item is not a closed item")
        comparison = _matching(closed, cfg.comparison_pattern)
        if cfg.target_item in comparison:
            problems.append("quality.inconsistency.comparison_pattern matches the target item")
        if len(comparison) < cfg.min_comparison_items:
            problems.append("quality.inconsistency.comparison_pattern matches too few items")
        lines = self.quality.straightline
        for grid, pattern in lines.grids.items():
            if len(_matching(closed, pattern)) < lines.min_items:
                problems.append(f"quality.straightline.grids.{grid} matches too few items")
        return problems


def _matching(var_ids: set[str], pattern: str) -> set[str]:
    try:
        compiled = re.compile(pattern)
    except re.error as err:
        raise ValueError(f"invalid regex {pattern!r}: {err}") from err
    return {v for v in var_ids if compiled.match(v)}


_FILES = {
    "survey": "survey_schema.yaml",
    "scales": "scales.yaml",
    "nonanswer": "nonanswer_patterns.yaml",
    "quality": "quality.yaml",
    "scoring": "scoring.yaml",
}


def read_yaml(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError as err:
        raise ConfigError(f"missing config file: {path}") from err
    except yaml.YAMLError as err:
        raise ConfigError(f"invalid YAML in {path}: {err}") from err
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a mapping at top level")
    return data


def load_config(config_dir: Path) -> Config:
    """Load and cross-validate every config file. Raises ConfigError on any problem."""
    raw = {key: read_yaml(config_dir / name) for key, name in _FILES.items()}
    try:
        return Config.model_validate(raw)
    except ValidationError as err:
        raise ConfigError(f"invalid configuration in {config_dir}:\n{err}") from err
