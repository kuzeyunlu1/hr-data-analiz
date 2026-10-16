"""Human review loop: coded segments -> review CSV -> validated text_segments table.

The review CSV is grouped by question and theme (not by person). The analyst edits codes in place
and sets `review_status` to accepted / edited / rejected. Re-running `code-text` never overwrites a
row a human has already decided on.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from hrsurvey.errors import HrSurveyError
from hrsurvey.status import Status
from hrsurvey.text.coder import CodingOutcome
from hrsurvey.text.settings import NEW_THEME, Codebook, LlmConfig

SEGMENT_COLUMNS = (
    "segment_id",
    "var_id",
    "q_no",
    "seq",
    "language",
    "text_en",
    "theme",
    "secondary_theme",
    "new_theme_label",
    "locus",
    "valence",
    "intensity",
    "sarcasm",
    "actionable",
    "suggestion",
    "confidence",
    "coder",
    "codebook_version",
    "review_status",
    "reviewer_note",
    "response_id",
)
PENDING, ACCEPTED, EDITED, REJECTED = "pending", "accepted", "edited", "rejected"
REVIEW_STATUSES = (PENDING, ACCEPTED, EDITED, REJECTED)
_BOOL = {"true": True, "false": False}
_LOWERCASE_COLUMNS = ("review_status", "sarcasm", "actionable")


class ReviewError(HrSurveyError):
    """The review CSV contains invalid codes or undecided rows."""


def segment_id(response_id: str, var_id: str, source: str, seq: int) -> str:
    """Stable while the SENT TEXT is unchanged. Deliberately independent of codebook, model and
    prompt: extending the codebook must not throw away human review decisions (DECISIONS D-019)."""
    return hashlib.sha256(f"{response_id}|{var_id}|{source}|{seq}".encode()).hexdigest()[:16]


def text_source(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def llm_segments(
    approved: pd.DataFrame,
    keys: Mapping[str, str],
    outcomes: Mapping[str, CodingOutcome],
    codebook: Codebook,
) -> pd.DataFrame:
    """One row per coded idea unit. `keys` maps manifest row_id -> request key."""
    rows = []
    for row in approved.itertuples(index=False):
        outcome = outcomes.get(keys[row.row_id])
        if outcome is None or not outcome.ok:
            continue
        for seq, seg in enumerate(outcome.answer.segments, start=1):
            rows.append(
                {
                    "segment_id": segment_id(
                        row.response_id, row.var_id, text_source(row.text_redacted), seq
                    ),
                    "var_id": row.var_id,
                    "q_no": row.q_no,
                    "seq": seq,
                    "language": outcome.answer.language,
                    **seg.model_dump(),
                    "coder": f"llm:{outcome.model}",
                    "codebook_version": codebook.version,
                    "review_status": PENDING,
                    "reviewer_note": "",
                    "response_id": row.response_id,
                }
            )
    return pd.DataFrame(rows, columns=list(SEGMENT_COLUMNS))


def rule_segments(text_answers: pd.DataFrame, llm: LlmConfig, codebook: Codebook) -> pd.DataFrame:
    """Answers coded locally by config (e.g. 'nothing' on the pride question) — never sent."""
    rows = []
    for answer in text_answers.itertuples(index=False):
        theme = llm.deterministic_codes.get(answer.var_id, {}).get(Status(answer.status))
        if theme is None:
            continue
        rows.append(
            {
                "segment_id": segment_id(answer.response_id, answer.var_id, "rule", 1),
                "var_id": answer.var_id,
                "q_no": answer.q_no,
                "seq": 1,
                "language": "",
                "text_en": f"[{answer.status}]",
                "theme": theme,
                "secondary_theme": None,
                "new_theme_label": None,
                "locus": "unspecified",
                "valence": -1,
                "intensity": 1,
                "sarcasm": False,
                "actionable": False,
                "suggestion": None,
                "confidence": "high",
                "coder": "rule",
                "codebook_version": codebook.version,
                "review_status": ACCEPTED,
                "reviewer_note": "",
                "response_id": answer.response_id,
            }
        )
    return pd.DataFrame(rows, columns=list(SEGMENT_COLUMNS))


def merge_review(
    fresh: pd.DataFrame, existing: pd.DataFrame | None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (review, stale).

    Human decisions are kept verbatim — but only for segments that are still current. A segment
    id embeds the sent text, so a re-redacted answer, a re-split answer or a revoked approval
    makes the old decision stale: it moves to `stale` instead of being imported twice.
    """
    if existing is None or existing.empty:
        return _sorted(fresh), fresh.iloc[0:0]
    decided = existing[existing["review_status"] != PENDING]
    current = decided["segment_id"].isin(fresh["segment_id"])
    merged = pd.concat(
        [decided[current], fresh[~fresh["segment_id"].isin(decided["segment_id"])]],
        ignore_index=True,
    )
    return _sorted(merged), decided[~current].reset_index(drop=True)


def _sorted(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(["var_id", "theme", "segment_id"], ignore_index=True)


def write_review(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def read_review(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(SEGMENT_COLUMNS) - set(frame.columns)
    if missing:
        raise ReviewError(f"review file is missing columns: {sorted(missing)}")
    # normalise once (spreadsheet edits add spaces and capitals); validation and filtering
    # then see exactly the same values
    frame = frame[list(SEGMENT_COLUMNS)].apply(lambda col: col.str.strip())
    return frame.assign(**{c: frame[c].str.lower() for c in _LOWERCASE_COLUMNS})


def _problems(frame: pd.DataFrame, codebook: Codebook, allow_pending: bool) -> list[str]:
    themes = {*codebook.themes, NEW_THEME}
    checks = {
        "review_status": set(REVIEW_STATUSES),
        "theme": themes,
        "secondary_theme": themes | {""},
        "locus": set(codebook.locus),
        "valence": {"-1", "0", "1"},
        "intensity": {"1", "2", "3"},
        "sarcasm": set(_BOOL),
        "actionable": set(_BOOL),
    }
    problems = []
    for column, allowed in checks.items():
        bad = frame.loc[~frame[column].isin(allowed), "segment_id"].tolist()
        if bad:
            problems.append(f"invalid {column} in segments {bad[:5]}")
    duplicated = frame.loc[frame["segment_id"].duplicated(), "segment_id"].tolist()
    if duplicated:
        problems.append(f"duplicate segment_id {duplicated[:5]}")
    new_without_label = frame[(frame["theme"] == NEW_THEME) & (frame["new_theme_label"] == "")]
    if not new_without_label.empty:
        problems.append("theme NEW without new_theme_label")
    if not allow_pending and (frame["review_status"] == PENDING).any():
        problems.append(
            f"{(frame['review_status'] == PENDING).sum()} segments still pending review"
        )
    return problems


def import_review(
    path: Path, codebook: Codebook, wave_id: str, allow_pending: bool = False
) -> pd.DataFrame:
    """Validate the reviewed CSV and return the text_segments table (rejected rows dropped)."""
    frame = read_review(path)
    problems = _problems(frame, codebook, allow_pending)
    if problems:
        raise ReviewError("review file not importable: " + "; ".join(problems))
    kept = frame[frame["review_status"] != REJECTED]
    return kept.assign(
        wave_id=wave_id,
        seq=kept["seq"].astype(int),
        valence=kept["valence"].astype(int),
        intensity=kept["intensity"].astype(int),
        sarcasm=kept["sarcasm"].map(_BOOL),
        actionable=kept["actionable"].map(_BOOL),
        secondary_theme=kept["secondary_theme"].replace("", None),
        new_theme_label=kept["new_theme_label"].replace("", None),
        suggestion=kept["suggestion"].replace("", None),
    ).sort_values(["response_id", "var_id", "seq"], ignore_index=True)
