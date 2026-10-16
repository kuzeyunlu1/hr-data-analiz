from __future__ import annotations

import pandas as pd
import pytest

from hrsurvey.config import Config
from hrsurvey.ingest import IngestResult
from hrsurvey.status import Status
from hrsurvey.text_prep import TEXT_ANSWER_COLUMNS, build_text_answers

from conftest import N_PROFILES


@pytest.fixture(scope="module")
def text(ingested: IngestResult, config: Config) -> pd.DataFrame:
    return build_text_answers(ingested, config)


def _cell(text: pd.DataFrame, response_id: str, var_id: str) -> pd.Series:
    rows = text[(text["response_id"] == response_id) & (text["var_id"] == var_id)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_one_row_per_respondent_and_text_item(text: pd.DataFrame) -> None:
    assert list(text.columns) == list(TEXT_ANSWER_COLUMNS)
    assert len(text) == N_PROFILES * 28
    assert text["response_id"].is_monotonic_increasing


def test_branch_text_outside_own_branch_is_not_routed(text: pd.DataFrame) -> None:
    # 3 single-branch respondents x 10 foreign branch text items + 4 no-branch x 15
    assert (text["status"] == Status.NOT_ROUTED).sum() == 3 * 10 + 4 * 15


def test_text_is_normalized_not_raw(text: pd.DataFrame, profile_ids: dict[str, str]) -> None:
    cell = _cell(text, profile_ids["none_inconsistent"], "q01_customer_value_txt")
    assert cell["text_norm"] == "I don't have any direct customer contact."


@pytest.mark.parametrize(
    ("profile", "var_id", "status", "signal"),
    [
        ("tech_positive", "q12_obstacles_txt", Status.NO_ISSUE, True),
        ("sales_negative", "q06_coop_change_txt", Status.PLACEHOLDER, False),
        ("sales_negative", "q02_customer_problem_txt", Status.EMPTY, False),
        # "nothing" is itself a signal for pride / enjoyment questions ...
        ("sales_negative", "q14_pride_txt", Status.NOTHING_TO_ADD, True),
        # ... but not elsewhere
        ("sales_negative", "sal7_single_change_txt", Status.NOTHING_TO_ADD, False),
        ("none_inconsistent", "q01_customer_value_txt", Status.NO_BASIS, False),
        ("backoffice_mixed", "q12_obstacles_txt", Status.SUBSTANTIVE, True),
    ],
)
def test_status_and_signal(
    text: pd.DataFrame,
    profile_ids: dict[str, str],
    profile: str,
    var_id: str,
    status: Status,
    signal: bool,
) -> None:
    cell = _cell(text, profile_ids[profile], var_id)
    assert (cell["status"], bool(cell["counts_as_signal"])) == (status, signal)
