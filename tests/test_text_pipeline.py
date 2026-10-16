"""End-to-end Phase 2 on the synthetic export with a fake coder: redact -> approve -> code ->
review -> import. Nothing leaves the machine."""

from __future__ import annotations

import pandas as pd
import pytest

from hrsurvey.errors import ManifestError
from hrsurvey.text import pipeline
from hrsurvey.text.manifest import read_manifest, write_manifest
from hrsurvey.text.review import (
    ACCEPTED,
    PENDING,
    REJECTED,
    ReviewError,
    read_review,
    write_review,
)
from hrsurvey.text.settings import TextConfig

from conftest import TEST_SALT
from conftest import approve_all as _approve_all
from fixtures.fake_anthropic import FakeCoder


def _never_called():
    raise AssertionError("the coder must not be created when nothing needs sending")


def test_code_text_requires_a_manifest(run) -> None:
    _, code, _ = run
    with pytest.raises(ManifestError, match="redact"):
        code(_never_called)


def test_nothing_is_sent_without_approval(run) -> None:
    redact, code, _ = run
    assert redact().approved == 0
    result = code(_never_called)
    assert (result.to_send, result.approved) == (0, 0)


def test_full_round_trip(run, text_config: TextConfig) -> None:
    redact, code, zone = run
    redact()
    rows = _approve_all(zone)

    preview = code(_never_called, dry_run=True)
    assert preview.to_send <= rows and preview.cached == 0

    coder = FakeCoder()
    result = code(lambda: coder)
    assert result.to_send == len(coder.requests) == preview.to_send
    assert result.errors == ()
    review = read_review(result.review_path)
    llm_rows = review[review["coder"].str.startswith("llm:")]
    assert len(llm_rows) == rows  # one segment per answer from the fake coder
    assert set(llm_rows["review_status"]) == {PENDING}
    # "I dont know?" on the pride question is coded locally, never sent
    rule_rows = review[review["coder"] == "rule"]
    assert set(rule_rows["theme"]) == {"MEAN.NOTHING_ENJOYABLE"}
    assert set(rule_rows["review_status"]) == {ACCEPTED}

    # second run: everything cached, the API client is never even created
    again = code(_never_called)
    assert (again.to_send, again.cached) == (0, rows)

    # unreviewed rows block the import
    with pytest.raises(ReviewError, match="pending"):
        pipeline.run_review_import(text_config, "2026-10", zone.parent.parent, False)

    decided = review.assign(review_status=ACCEPTED)
    decided.loc[0, "review_status"] = REJECTED
    write_review(decided, result.review_path)
    path, segments = pipeline.run_review_import(text_config, "2026-10", zone.parent.parent, False)
    assert len(segments) == len(review) - 1
    stored = pd.read_parquet(path)
    assert stored["valence"].dtype.kind == "i"
    assert set(stored["wave_id"]) == {"2026-10"}


def test_human_decisions_survive_recoding(run) -> None:
    redact, code, zone = run
    redact()
    _approve_all(zone)
    first = code(FakeCoder)
    review = read_review(first.review_path)
    review.loc[0, ["review_status", "theme"]] = ["edited", "CAP.NO_CAPACITY"]
    write_review(review, first.review_path)

    code(_never_called)  # cached re-run rebuilds the review file
    kept = read_review(first.review_path).set_index("segment_id").loc[review.loc[0, "segment_id"]]
    assert (kept["review_status"], kept["theme"]) == ("edited", "CAP.NO_CAPACITY")


def test_invalid_review_values_are_rejected(run, text_config: TextConfig) -> None:
    redact, code, zone = run
    redact()
    _approve_all(zone)
    result = code(FakeCoder)
    review = read_review(result.review_path).assign(review_status=ACCEPTED)
    review.loc[0, "theme"] = "MADE.UP"
    write_review(review, result.review_path)
    with pytest.raises(ReviewError, match="invalid theme"):
        pipeline.run_review_import(text_config, "2026-10", zone.parent.parent, False)


def test_spreadsheet_whitespace_cannot_smuggle_rows_past_the_checks(run, text_config) -> None:
    redact, code, zone = run
    redact()
    _approve_all(zone)
    result = code(FakeCoder)
    review = read_review(result.review_path).assign(review_status=" Accepted ")
    review.loc[0, "review_status"] = " rejected"
    review.loc[1, "review_status"] = "Pending "
    write_review(review, result.review_path)
    with pytest.raises(ReviewError, match="1 segments still pending"):
        pipeline.run_review_import(text_config, "2026-10", zone.parent.parent, False)
    review.loc[1, "review_status"] = "accepted"
    write_review(review, result.review_path)
    _, segments = pipeline.run_review_import(text_config, "2026-10", zone.parent.parent, False)
    assert len(segments) == len(review) - 1  # the " rejected" row is really dropped


def test_decisions_on_changed_answers_become_stale(run, text_config) -> None:
    redact, code, zone = run
    redact()
    _approve_all(zone)
    first = code(FakeCoder)
    review = read_review(first.review_path).assign(review_status=ACCEPTED)
    write_review(review, first.review_path)
    llm_row = review[review["coder"].str.startswith("llm:")].iloc[0]

    manifest = read_manifest(zone / pipeline.MANIFEST_FILE)
    target = manifest["row_id"] == f"{llm_row['response_id']}:{llm_row['var_id']}"
    manifest.loc[target, "text_redacted"] = "re-redacted by the analyst"
    write_manifest(manifest, zone / pipeline.MANIFEST_FILE)
    code(FakeCoder)

    current = read_review(first.review_path)
    assert llm_row["segment_id"] not in set(current["segment_id"])
    stale = read_review(zone / pipeline.STALE_REVIEW_FILE)
    assert set(stale["segment_id"]) == {llm_row["segment_id"]}
    with pytest.raises(ReviewError, match="pending"):  # the new codes still need a decision
        pipeline.run_review_import(text_config, "2026-10", zone.parent.parent, False)


def test_codebook_changes_keep_human_decisions(run, synthetic_csv, config, text_config, tmp_path):
    redact, code, zone = run
    redact()
    _approve_all(zone)
    first = code(FakeCoder)
    write_review(read_review(first.review_path).assign(review_status=ACCEPTED), first.review_path)

    themes = {**text_config.codebook.themes, "OWN.NEW_IDEA": "an added theme"}
    extended = text_config.model_copy(
        update={"codebook": text_config.codebook.model_copy(update={"themes": themes})}
    )
    coder = FakeCoder()
    again = pipeline.run_code_text(
        synthetic_csv, config, extended, TEST_SALT, None, tmp_path, lambda: coder
    )
    assert coder.requests, "a codebook change re-codes (the prompt changed) ..."
    review = read_review(again.review_path)
    assert set(review["review_status"]) == {ACCEPTED}  # ... but decisions survive
    assert not (zone / pipeline.STALE_REVIEW_FILE).exists()
