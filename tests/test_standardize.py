from __future__ import annotations

import pandas as pd
import pytest

from hrsurvey.config import Config
from hrsurvey.ingest import IngestResult
from hrsurvey.standardize import ANSWERS_LONG_COLUMNS, build_answers_long
from hrsurvey.status import Status

from conftest import N_PROFILES


@pytest.fixture(scope="module")
def standardized(ingested: IngestResult, config: Config) -> tuple[pd.DataFrame, tuple[str, ...]]:
    return build_answers_long(ingested, config)


@pytest.fixture(scope="module")
def long(standardized) -> pd.DataFrame:
    return standardized[0]


def _cell(long: pd.DataFrame, response_id: str, var_id: str) -> pd.Series:
    rows = long[(long["response_id"] == response_id) & (long["var_id"] == var_id)]
    assert len(rows) == 1
    return rows.iloc[0]


def test_one_row_per_respondent_and_closed_item(long: pd.DataFrame) -> None:
    assert len(long) == N_PROFILES * 57
    assert not long.duplicated(["response_id", "var_id"]).any()
    assert long["response_id"].is_monotonic_increasing  # no submission order


def test_output_contains_no_raw_labels_or_timestamps(long: pd.DataFrame) -> None:
    assert list(long.columns) == list(ANSWERS_LONG_COLUMNS)
    assert "submitted_at_raw" not in set(long["var_id"])


def test_statuses_come_from_the_taxonomy(long: pd.DataFrame) -> None:
    assert set(long["status"]) <= {s.value for s in Status}


def test_branch_items_outside_own_branch_are_not_routed(long: pd.DataFrame) -> None:
    # 3 single-branch respondents x 4 foreign branch items + 4 no-branch respondents x 6;
    # the multi-branch respondent is routed to every branch
    assert (long["status"] == Status.NOT_ROUTED).sum() == 3 * 4 + 4 * 6


def test_unanswered_item_in_own_branch_is_empty(
    long: pd.DataFrame, profile_ids: dict[str, str]
) -> None:
    assert _cell(long, profile_ids["tech_positive"], "tec2_needs_to_sales_eff")["status"] == (
        Status.EMPTY
    )
    assert _cell(long, profile_ids["tech_positive"], "sal3_internal_hindrance")["status"] == (
        Status.NOT_ROUTED
    )


def test_probability_scale(long: pd.DataFrame, profile_ids: dict[str, str]) -> None:
    cell = _cell(long, profile_ids["sales_negative"], "q19_expectancy")
    assert (cell["code"], cell["value"], cell["pomp"]) == (2, 0.25, 25.0)
    assert cell["favorability"] == "unfavorable"


def test_negative_polarity_items(long: pd.DataFrame, profile_ids: dict[str, str]) -> None:
    sales = profile_ids["sales_negative"]
    assert _cell(long, sales, "sal3_internal_hindrance")["pomp"] == 50.0
    not_difficult = _cell(long, sales, "sal5_value_convince_difficulty")
    assert (not_difficult["pomp"], not_difficult["favorability"]) == (100.0, "favorable")


def test_na_option_has_no_score(long: pd.DataFrame, profile_ids: dict[str, str]) -> None:
    cell = _cell(long, profile_ids["sales_negative"], "q04_coop_within_dept")
    assert cell["status"] == Status.NO_BASIS
    assert pd.isna(cell["code"]) and pd.isna(cell["pomp"]) and pd.isna(cell["favorability"])


def test_empty_core_item(long: pd.DataFrame, profile_ids: dict[str, str]) -> None:
    cell = _cell(long, profile_ids["low_completion"], "q07_info_access_sat")
    assert cell["status"] == Status.EMPTY


def test_unverified_labels_are_marked_and_reported(
    standardized, profile_ids: dict[str, str]
) -> None:
    long, warnings = standardized
    cell = _cell(long, profile_ids["backoffice_mixed"], "bo2_info_completeness")
    assert (cell["code"], bool(cell["label_unverified"])) == (4, True)
    assert long["label_unverified"].sum() == 1
    assert any("bo2_info_completeness" in w and "Complete / Vollständig" in w for w in warnings)


def test_numeric_items(long: pd.DataFrame, profile_ids: dict[str, str]) -> None:
    motivation = _cell(long, profile_ids["sales_negative"], "q22_motivation_2w")
    assert (motivation["code"], motivation["pomp"], motivation["favorability"]) == (
        0,
        0.0,
        "unfavorable",
    )
