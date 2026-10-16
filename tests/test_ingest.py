from __future__ import annotations

import csv
from pathlib import Path

import pytest

from hrsurvey.config import Config
from hrsurvey.errors import SchemaMismatchError, TimestampParseError, WaveError
from hrsurvey.ingest import (
    IngestResult,
    RawExport,
    ingest,
    read_export,
    resolve_wave,
    validate_export,
)
from hrsurvey.timestamps import parse_timestamp

from conftest import N_PROFILES, TEST_SALT


def _rewrite(src: Path, dst: Path, mutate) -> Path:
    with src.open(newline="", encoding="utf-8") as handle:
        header, *rows = list(csv.reader(handle))
    header, rows = mutate(header, rows)
    with dst.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        writer.writerows(rows)
    return dst


def test_synthetic_export_validates(synthetic_csv: Path, config: Config) -> None:
    validate_export(read_export(synthetic_csv), config.survey)


def test_multiline_cells_survive_parsing(synthetic_csv: Path) -> None:
    export = read_export(synthetic_csv)
    assert len(export.rows) == N_PROFILES
    assert any("\n" in cell for row in export.rows for cell in row[1:])


def test_wrong_column_count_raises(synthetic_csv: Path, config: Config, tmp_path: Path) -> None:
    path = _rewrite(
        synthetic_csv, tmp_path / "x.csv", lambda h, r: (h[:-1], [row[:-1] for row in r])
    )
    with pytest.raises(SchemaMismatchError, match="85 columns"):
        validate_export(read_export(path), config.survey)


def test_changed_question_text_names_the_column(
    synthetic_csv: Path, config: Config, tmp_path: Path
) -> None:
    def mutate(header, rows):
        return [*header[:5], "4.1. A reworded question?", *header[6:]], rows

    path = _rewrite(synthetic_csv, tmp_path / "x.csv", mutate)
    with pytest.raises(SchemaMismatchError, match="q04_1_coop_within_reason_txt"):
        validate_export(read_export(path), config.survey)


def test_whitespace_only_header_changes_are_tolerated(
    synthetic_csv: Path, config: Config, tmp_path: Path
) -> None:
    def mutate(header, rows):
        return [f"  {cell.replace(chr(10), chr(10) + chr(10))} " for cell in header], rows

    path = _rewrite(synthetic_csv, tmp_path / "x.csv", mutate)
    validate_export(read_export(path), config.survey)


def test_ragged_row_raises(config: Config, synthetic_csv: Path) -> None:
    export = read_export(synthetic_csv)
    ragged = RawExport(export.header, (export.rows[0][:-2],))
    with pytest.raises(SchemaMismatchError, match="wrong number of cells"):
        validate_export(ragged, config.survey)


def test_header_only_export_raises(config: Config, synthetic_csv: Path) -> None:
    empty = RawExport(read_export(synthetic_csv).header, ())
    with pytest.raises(SchemaMismatchError, match="no responses"):
        ingest(empty, config, TEST_SALT, wave=None)


def test_branch_is_derived_from_answered_branch_blocks(
    ingested: IngestResult, profile_ids: dict[str, str]
) -> None:
    branch = ingested.respondents.set_index("response_id")["branch"]
    assert branch[profile_ids["tech_positive"]] == "technical"
    assert branch[profile_ids["sales_negative"]] == "sales"
    assert branch[profile_ids["backoffice_mixed"]] == "back_office"
    assert branch[profile_ids["multi_branch"]] == "multiple"
    assert (branch == "none").sum() == 4


def test_timestamp_never_leaves_ingest(ingested: IngestResult) -> None:
    assert "submitted_at_raw" not in ingested.answers.columns
    assert list(ingested.respondents.columns) == [
        "response_id",
        "wave_id",
        "branch",
        "qflag_duplicate",
    ]


def test_row_order_does_not_reveal_submission_order(ingested: IngestResult) -> None:
    assert ingested.respondents["response_id"].is_monotonic_increasing
    assert ingested.answers.index.is_monotonic_increasing


def test_wave_is_the_owner_local_month(ingested: IngestResult) -> None:
    # earliest synthetic submission is 2026-10-14 00:05 at GMT+3 (= 2026-10-13 in UTC)
    assert ingested.wave_id == "2026-10"
    assert set(ingested.respondents["wave_id"]) == {"2026-10"}


def test_explicit_wave_overrides_derivation(synthetic_csv: Path, config: Config) -> None:
    result = ingest(read_export(synthetic_csv), config, TEST_SALT, wave="pilot")
    assert result.wave_id == "pilot"


@pytest.mark.parametrize("wave", ["../../docs", "/tmp/x", "", "2026 10", ".hidden"])
def test_unsafe_wave_ids_are_rejected(wave: str) -> None:
    with pytest.raises(WaveError):
        resolve_wave(wave, [])


def test_submissions_spanning_months_require_explicit_wave(config: Config) -> None:
    spec = config.survey.timestamp
    submitted = [
        parse_timestamp("2026/10/31 11:00:00 ÖS GMT+3", spec),
        parse_timestamp("2026/11/01 9:00:00 ÖÖ GMT+3", spec),
    ]
    with pytest.raises(WaveError, match="2026-10 to 2026-11"):
        resolve_wave(None, submitted)
    assert resolve_wave("2026-autumn", submitted) == "2026-autumn"


def test_unparseable_timestamp_names_the_row_not_the_value(
    synthetic_csv: Path, config: Config, tmp_path: Path
) -> None:
    def mutate(header, rows):
        return header, [rows[0], ["15.10.2026 18:43", *rows[1][1:]], *rows[2:]]

    path = _rewrite(synthetic_csv, tmp_path / "x.csv", mutate)
    with pytest.raises(TimestampParseError, match="data row 2") as err:
        ingest(read_export(path), config, TEST_SALT, wave=None)
    assert "18:43" not in str(err.value)


def test_sparse_identical_answers_are_not_duplicates(config: Config, synthetic_csv: Path) -> None:
    header = read_export(synthetic_csv).header
    row = ["2026/10/15 1:00:00 ÖÖ GMT+3", *[""] * 85]
    row[4], row[6] = "Good / Gut", "Good / Gut"  # same two answers from two people
    later = ["2026/10/15 2:00:00 ÖÖ GMT+3", *row[1:]]
    result = ingest(RawExport(header, (tuple(row), tuple(later))), config, TEST_SALT, wave=None)
    assert not result.respondents["qflag_duplicate"].any()
