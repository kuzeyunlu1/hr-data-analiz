"""Respondent table: completion + quality flags (docs/04-data-quality.md#quality-flags-summary).

Flags are informational: nothing is corrected or removed here.
"""

from __future__ import annotations

import pandas as pd

from hrsurvey.config import Config, QualityConfig, SurveySchema
from hrsurvey.ingest import MULTIPLE_BRANCHES, IngestResult
from hrsurvey.status import Status


def respondent_columns(quality: QualityConfig) -> tuple[str, ...]:
    """Column order of the respondents table; straightline flags follow the configured grids."""
    return (
        "response_id",
        "wave_id",
        "branch",
        "core_completion",
        "qflag_low_completion",
        "qflag_inconsistent",
        *(f"qflag_straightline_{grid}" for grid in quality.straightline.grids),
        "qflag_duplicate",
        "qflag_multiple_branches",
    )


def core_completion(answers_long: pd.DataFrame, survey: SurveySchema) -> pd.Series:
    """Share of closed core items answered (any status except EMPTY)."""
    core_vars = {c.var_id for c in survey.closed_columns() if c.block in survey.core_blocks}
    core = answers_long[answers_long["var_id"].isin(core_vars)]
    return (core["status"] != Status.EMPTY).groupby(core["response_id"]).mean()


def _substantive(answers_long: pd.DataFrame, pattern: str) -> pd.DataFrame:
    mask = answers_long["var_id"].str.match(pattern) & (
        answers_long["status"] == Status.SUBSTANTIVE
    )
    return answers_long[mask]


def inconsistency_flags(answers_long: pd.DataFrame, quality: QualityConfig) -> pd.Series:
    cfg = quality.inconsistency
    target = answers_long[
        (answers_long["var_id"] == cfg.target_item) & (answers_long["status"] == Status.SUBSTANTIVE)
    ].set_index("response_id")["pomp"]
    comparison = _substantive(answers_long, cfg.comparison_pattern).groupby("response_id")["pomp"]
    enough = comparison.count() >= cfg.min_comparison_items
    gap = (target - comparison.mean()).abs()
    flags = (gap >= cfg.gap_pomp) & enough.reindex(gap.index, fill_value=False)
    return flags.fillna(False).astype(bool)


def straightline_flags(answers_long: pd.DataFrame, quality: QualityConfig) -> pd.DataFrame:
    cfg = quality.straightline
    flags = {}
    for grid, pattern in cfg.grids.items():
        codes = _substantive(answers_long, pattern).groupby("response_id")["code"]
        flags[f"qflag_straightline_{grid}"] = (codes.count() >= cfg.min_items) & (
            codes.nunique() == 1
        )
    return pd.DataFrame(flags)


def build_respondents(
    ingested: IngestResult, answers_long: pd.DataFrame, config: Config
) -> pd.DataFrame:
    base = ingested.respondents.set_index("response_id")
    ids = base.index
    completion = core_completion(answers_long, config.survey).reindex(ids, fill_value=0.0)
    straightline = pd.DataFrame(index=ids).join(straightline_flags(answers_long, config.quality))
    frame = base.assign(
        core_completion=completion,
        qflag_low_completion=completion < config.quality.min_core_completion,
        qflag_inconsistent=inconsistency_flags(answers_long, config.quality).reindex(
            ids, fill_value=False
        ),
        **{name: straightline[name].fillna(False).astype(bool) for name in straightline.columns},
        qflag_multiple_branches=base["branch"] == MULTIPLE_BRANCHES,
    )
    return frame.reset_index()[list(respondent_columns(config.quality))]
