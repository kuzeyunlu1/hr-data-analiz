from __future__ import annotations

import pandas as pd
import pytest

from hrsurvey.config import Config
from hrsurvey.ingest import IngestResult
from hrsurvey.quality import build_respondents, respondent_columns
from hrsurvey.standardize import build_answers_long

from conftest import N_PROFILES


@pytest.fixture(scope="module")
def table(ingested: IngestResult, config: Config) -> pd.DataFrame:
    long, _ = build_answers_long(ingested, config)
    return build_respondents(ingested, long, config)


@pytest.fixture(scope="module")
def respondents(table: pd.DataFrame) -> pd.DataFrame:
    return table.set_index("response_id")


def _flagged(respondents: pd.DataFrame, flag: str, profile_ids: dict[str, str]) -> set[str]:
    by_id = {rid: name for name, rid in profile_ids.items()}
    return {by_id[rid] for rid in respondents.index[respondents[flag]]}


def test_columns_follow_config(table: pd.DataFrame, config: Config) -> None:
    assert list(table.columns) == list(respondent_columns(config.quality))
    assert table["response_id"].is_monotonic_increasing
    assert len(table) == N_PROFILES


def test_inconsistent_recommendation_is_flagged(respondents, profile_ids) -> None:
    assert _flagged(respondents, "qflag_inconsistent", profile_ids) == {
        "none_inconsistent",
        "duplicate",
    }


def test_straightlining_per_grid(respondents, profile_ids) -> None:
    assert _flagged(respondents, "qflag_straightline_q16", profile_ids) == {"straightliner"}
    assert _flagged(respondents, "qflag_straightline_q17", profile_ids) == {"straightliner"}
    assert _flagged(respondents, "qflag_straightline_q18", profile_ids) == {"backoffice_mixed"}


def test_low_completion(respondents, profile_ids) -> None:
    assert _flagged(respondents, "qflag_low_completion", profile_ids) == {"low_completion"}
    assert respondents.loc[profile_ids["tech_positive"], "core_completion"] == 1.0
    assert respondents.loc[profile_ids["low_completion"], "core_completion"] == pytest.approx(
        2 / 51
    )


def test_duplicate_submission_flags_only_the_later_copy(respondents, profile_ids) -> None:
    assert _flagged(respondents, "qflag_duplicate", profile_ids) == {"duplicate"}


def test_multiple_branches_are_flagged(respondents, profile_ids) -> None:
    assert _flagged(respondents, "qflag_multiple_branches", profile_ids) == {"multi_branch"}
