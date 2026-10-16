"""Stages 1–3: validate the export, assign pseudonymous IDs, derive wave, branch and duplicates.

The timestamp is used only to validate the format, derive the wave and order duplicate detection;
it never leaves this module. Outputs are sorted by response_id so that row order does not reveal
submission order (DECISIONS D-014).
"""

from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from hrsurvey.config import ColumnSpec, Config, SurveySchema
from hrsurvey.errors import SchemaMismatchError, TimestampParseError, WaveError
from hrsurvey.ids import response_ids
from hrsurvey.timestamps import parse_timestamp

_WHITESPACE = re.compile(r"\s+")
WAVE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
NO_BRANCH = "none"
MULTIPLE_BRANCHES = "multiple"


def normalize_header(text: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", text)).strip()


def header_hash(text: str) -> str:
    """Short fingerprint of one header cell, robust to whitespace/line-break differences."""
    return hashlib.sha256(normalize_header(text).encode()).hexdigest()[:12]


@dataclass(frozen=True)
class RawExport:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class IngestResult:
    wave_id: str
    respondents: pd.DataFrame  # response_id, wave_id, branch, qflag_duplicate — sorted by id
    answers: pd.DataFrame  # index response_id (sorted), one column per var_id, no timestamp


def read_export(path: Path) -> RawExport:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        records = list(csv.reader(handle))
    if not records:
        raise SchemaMismatchError(f"{path} is empty")
    header, *rows = records
    return RawExport(tuple(header), tuple(tuple(row) for row in rows))


def validate_export(export: RawExport, survey: SurveySchema) -> None:
    """Fail loudly if the column count, any row width or any header text differs from the schema."""
    if len(export.header) != survey.expected_columns:
        raise SchemaMismatchError(
            f"export has {len(export.header)} columns, schema expects {survey.expected_columns}"
        )
    bad_rows = [n for n, row in enumerate(export.rows, start=1) if len(row) != len(export.header)]
    if bad_rows:
        raise SchemaMismatchError(f"data rows with wrong number of cells: {bad_rows}")
    changed = [
        f"{col.idx} {col.var_id}"
        for col, text in zip(survey.columns, export.header, strict=True)
        if header_hash(text) != col.header_hash
    ]
    if changed:
        raise SchemaMismatchError(
            "header text changed for: "
            + ", ".join(changed)
            + ". Update docs/03-data-dictionary.md "
            "and config/survey_schema.yaml before re-running."
        )


def derive_branch(row: tuple[str, ...], survey: SurveySchema) -> str:
    answered = {
        survey.branch_of(col)
        for col in survey.columns
        if survey.branch_of(col) is not None and row[col.idx].strip()
    }
    if not answered:
        return NO_BRANCH
    if len(answered) > 1:
        return MULTIPLE_BRANCHES
    return answered.pop()


def is_routed(column: ColumnSpec, branch: str, survey: SurveySchema) -> bool:
    """Core columns are routed to everyone; branch columns only to that branch's respondents."""
    column_branch = survey.branch_of(column)
    return column_branch is None or column_branch == branch or branch == MULTIPLE_BRANCHES


def _parse_submissions(export: RawExport, survey: SurveySchema) -> list[datetime]:
    parsed = []
    for number, row in enumerate(export.rows, start=1):
        try:
            parsed.append(parse_timestamp(row[survey.timestamp.column_idx], survey.timestamp))
        except TimestampParseError as err:
            raise TimestampParseError(f"data row {number}: {err}") from err
    return parsed


def resolve_wave(wave: str | None, submitted: Sequence[datetime]) -> str:
    """Explicit wave if valid; else the owner-local month, which must be unique."""
    if wave is not None:
        if not WAVE_PATTERN.match(wave):
            raise WaveError("wave may only contain letters, digits, '-' and '_'")
        return wave
    months = sorted({ts.strftime("%Y-%m") for ts in submitted})
    if len(months) > 1:
        raise WaveError(f"submissions span {months[0]} to {months[-1]}; pass --wave explicitly")
    return months[0]


def later_duplicates(
    export: RawExport, survey: SurveySchema, submitted: Sequence[datetime], min_answered: int
) -> list[bool]:
    """Flag a row whose answers (timestamp excluded) repeat an EARLIER submission.

    Sparse rows (< min_answered non-empty cells) are never flagged: two people can legitimately
    give the same handful of answers.
    """
    ts_idx = survey.timestamp.column_idx
    contents = [tuple(c for i, c in enumerate(row) if i != ts_idx) for row in export.rows]
    flags = [False] * len(contents)
    seen: set[tuple[str, ...]] = set()
    for position in sorted(range(len(contents)), key=lambda i: submitted[i]):
        content = contents[position]
        if sum(1 for cell in content if cell.strip()) < min_answered:
            continue
        flags[position] = content in seen
        seen.add(content)
    return flags


def ingest(export: RawExport, config: Config, salt: bytes, wave: str | None) -> IngestResult:
    survey = config.survey
    validate_export(export, survey)
    if not export.rows:
        raise SchemaMismatchError("export contains a header but no responses")
    submitted = _parse_submissions(export, survey)
    wave_id = resolve_wave(wave, submitted)
    ids = response_ids(export.rows, salt)
    min_answered = config.quality.duplicate_min_answered_cells

    respondents = pd.DataFrame(
        {
            "response_id": ids,
            "wave_id": wave_id,
            "branch": [derive_branch(row, survey) for row in export.rows],
            "qflag_duplicate": later_duplicates(export, survey, submitted, min_answered),
        }
    )
    kept = [col for col in survey.columns if col.idx != survey.timestamp.column_idx]
    answers = pd.DataFrame(
        [[row[col.idx] for col in kept] for row in export.rows],
        columns=[col.var_id for col in kept],
        index=pd.Index(ids, name="response_id"),
        dtype="object",
    )
    return IngestResult(
        wave_id=wave_id,
        respondents=respondents.sort_values("response_id", ignore_index=True),
        answers=answers.sort_index(),
    )
