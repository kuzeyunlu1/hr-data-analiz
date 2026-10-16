from __future__ import annotations

import pandas as pd
import pytest

from hrsurvey.config import Config
from hrsurvey.errors import ManifestError
from hrsurvey.ingest import IngestResult
from hrsurvey.standardize import build_answers_long
from hrsurvey.text.manifest import (
    MANIFEST_COLUMNS,
    approved_rows,
    build_manifest,
    read_manifest,
    write_manifest,
)
from hrsurvey.text.redact import Redactor
from hrsurvey.text.settings import TextConfig
from hrsurvey.text_prep import build_text_answers


@pytest.fixture(scope="module")
def inputs(ingested: IngestResult, config: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    return build_text_answers(ingested, config), build_answers_long(ingested, config)[0]


@pytest.fixture(scope="module")
def manifest(inputs, text_config: TextConfig, redactor: Redactor) -> pd.DataFrame:
    text, long = inputs
    return build_manifest(text, long, text_config, redactor)


def test_only_sendable_statuses_are_listed(manifest: pd.DataFrame, inputs) -> None:
    text, _ = inputs
    expected = text["status"].isin(["SUBSTANTIVE", "NO_ISSUE"]).sum()
    assert len(manifest) == expected
    assert set(manifest["status"]) == {"SUBSTANTIVE", "NO_ISSUE"}
    assert list(manifest.columns) == list(MANIFEST_COLUMNS)


def test_nothing_is_approved_by_default(manifest: pd.DataFrame) -> None:
    assert approved_rows(manifest).empty


def test_rows_are_grouped_by_question_not_person(manifest: pd.DataFrame) -> None:
    assert manifest["var_id"].is_monotonic_increasing


def test_engagement_bands(manifest: pd.DataFrame, profile_ids: dict[str, str]) -> None:
    band = manifest.drop_duplicates("response_id").set_index("response_id")["engagement_band"]
    assert band[profile_ids["tech_positive"]] == "favorable"  # q18j 5, q22 8
    assert band[profile_ids["sales_negative"]] == "unfavorable"  # q18j 1, q22 0


def test_inconsistent_respondents_get_unknown_band(
    inputs, text_config, redactor, profile_ids
) -> None:
    text, long = inputs
    inconsistent = profile_ids["none_inconsistent"]
    built = build_manifest(text, long, text_config, redactor, unreliable=frozenset({inconsistent}))
    bands = set(built.loc[built["response_id"] == inconsistent, "engagement_band"])
    assert bands == {"unknown"}


def test_rerun_keeps_approval_and_edits_for_unchanged_answers(
    manifest, inputs, text_config, redactor, tmp_path
) -> None:
    edited = manifest.assign(approved="yes")
    edited.loc[0, "text_redacted"] = "manually redacted"
    path = write_manifest(edited, tmp_path / "m.csv")
    text, long = inputs
    rebuilt = build_manifest(text, long, text_config, redactor, read_manifest(path))
    assert len(approved_rows(rebuilt)) == len(manifest)
    assert "manually redacted" in set(rebuilt["text_redacted"])


def test_changed_answer_resets_approval(manifest, inputs, text_config, redactor) -> None:
    text, long = inputs
    first = manifest.iloc[0]
    changed = text.copy()
    target = (changed["response_id"] == first["response_id"]) & (
        changed["var_id"] == first["var_id"]
    )
    changed.loc[target, "text_norm"] = "A completely different answer."
    rebuilt = build_manifest(changed, long, text_config, redactor, manifest.assign(approved="yes"))
    row = rebuilt.set_index("row_id").loc[first["row_id"]]
    assert row["approved"] == ""
    assert row["text_original"] == "A completely different answer."


def test_approval_is_explicit(manifest: pd.DataFrame) -> None:
    marked = manifest.assign(approved=["YES ", "no", "", "y", *["yes"] * (len(manifest) - 4)])
    assert len(approved_rows(marked)) == len(manifest) - 3


def test_tightened_rules_reach_unedited_rows_and_reset_their_approval(
    manifest, inputs, text_config, redactor
) -> None:
    text, long = inputs
    stale = manifest.assign(approved="yes")
    # row 0: never edited, but produced by older rules -> new text, approval reset
    stale.loc[0, ["text_auto", "text_redacted"]] = ["old rules output", "old rules output"]
    # row 1: edited by the analyst -> their text and approval survive
    stale.loc[1, "text_redacted"] = "analyst version"
    rebuilt = build_manifest(text, long, text_config, redactor, stale).set_index("row_id")
    first, second = rebuilt.loc[stale.loc[0, "row_id"]], rebuilt.loc[stale.loc[1, "row_id"]]
    assert (first["text_redacted"], first["approved"]) == (first["text_auto"], "")
    assert (second["text_redacted"], second["approved"]) == ("analyst version", "yes")


def test_duplicate_manifest_rows_are_rejected(manifest, tmp_path) -> None:
    path = write_manifest(pd.concat([manifest, manifest.iloc[[0]]]), tmp_path / "m.csv")
    with pytest.raises(ManifestError, match="duplicate"):
        read_manifest(path)
