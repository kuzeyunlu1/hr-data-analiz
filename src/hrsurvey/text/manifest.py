"""The send manifest: the ONLY gate through which text can reach the LLM.

`hrsurvey redact` writes one row per answer that would be coded. The analyst reviews it, may edit
`text_redacted` (e.g. redact more, or restore a wrongly masked word using `text_original`) and sets
`approved` to `yes`. `hrsurvey code-text` sends approved rows only — exactly the `text_redacted`
shown. Re-running `redact` keeps approvals and edits for answers whose source text is unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from hrsurvey.config import Config
from hrsurvey.errors import ManifestError
from hrsurvey.ingest import normalize_header
from hrsurvey.status import Status
from hrsurvey.text.redact import Redactor
from hrsurvey.text.settings import EngagementBandConfig, TextConfig

MANIFEST_COLUMNS = (
    "row_id",
    "response_id",
    "var_id",
    "q_no",
    "status",
    "engagement_band",
    "language",
    "redactions",
    "text_original",
    "text_auto",
    "text_redacted",
    "source_hash",
    "approved",
)
APPROVED = "yes"
# text_auto = what the rules produced; text_redacted = what will be sent (the analyst may edit it)
UNKNOWN_BAND = "unknown"


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def engagement_bands(answers_long: pd.DataFrame, cfg: EngagementBandConfig) -> dict[str, str]:
    """Coarse favorable / neutral / unfavorable band per respondent from the configured items."""
    items = answers_long[
        answers_long["var_id"].isin(cfg.items) & (answers_long["status"] == Status.SUBSTANTIVE)
    ]
    means = items.groupby("response_id")["pomp"].mean()
    bands = {}
    for response_id, score in means.items():
        if score >= cfg.favorable_min_pomp:
            bands[response_id] = "favorable"
        elif score <= cfg.unfavorable_max_pomp:
            bands[response_id] = "unfavorable"
        else:
            bands[response_id] = "neutral"
    return bands


def _candidates(text_answers: pd.DataFrame, text_cfg: TextConfig) -> pd.DataFrame:
    sendable = {s.value for s in text_cfg.llm.send_statuses}
    return text_answers[text_answers["status"].isin(sendable)]


def build_manifest(
    text_answers: pd.DataFrame,
    answers_long: pd.DataFrame,
    text_cfg: TextConfig,
    redactor: Redactor,
    existing: pd.DataFrame | None = None,
    unreliable: frozenset[str] = frozenset(),
) -> pd.DataFrame:
    """`unreliable` = respondents whose scale answers contradict each other (qflag_inconsistent):
    their band would mislead the coder's irony judgement, so it is sent as 'unknown'."""
    bands = {
        rid: (UNKNOWN_BAND if rid in unreliable else band)
        for rid, band in engagement_bands(answers_long, text_cfg.llm.engagement_band).items()
    }
    previous = {} if existing is None else existing.set_index("row_id").to_dict("index")
    rows = []
    for answer in _candidates(text_answers, text_cfg).itertuples(index=False):
        row_id = f"{answer.response_id}:{answer.var_id}"
        digest = source_hash(answer.text_norm)
        redaction = redactor.redact(answer.text_norm)
        row = {
            "row_id": row_id,
            "response_id": answer.response_id,
            "var_id": answer.var_id,
            "q_no": answer.q_no,
            "status": answer.status,
            "engagement_band": bands.get(answer.response_id, UNKNOWN_BAND),
            "language": redaction.language,
            "redactions": redaction.summary,
            "text_original": answer.text_norm,
            "text_auto": redaction.text,
            "text_redacted": redaction.text,
            "source_hash": digest,
            "approved": "",
        }
        rows.append(_carry_over(row, previous.get(row_id)))
    frame = pd.DataFrame(rows, columns=list(MANIFEST_COLUMNS))
    # grouped by question, not by person: reviewing reads one question across respondents
    return frame.sort_values(["var_id", "row_id"], ignore_index=True)


def _carry_over(fresh: dict, kept: dict | None) -> dict:
    """Decide what survives a re-run for one answer.

    - answer text changed            -> fresh row, approval reset
    - analyst edited text_redacted   -> keep their text and approval (it is what they approved)
    - unedited, rules give same text -> keep approval
    - unedited, rules changed output -> new auto text, approval reset (they never saw it)
    """
    if kept is None or kept["source_hash"] != fresh["source_hash"]:
        return fresh
    if kept["text_redacted"] != kept["text_auto"]:
        return fresh | {"text_redacted": kept["text_redacted"], "approved": kept["approved"]}
    if kept["text_auto"] == fresh["text_auto"]:
        return fresh | {"approved": kept["approved"]}
    return fresh


def write_manifest(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def read_manifest(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    missing = set(MANIFEST_COLUMNS) - set(frame.columns)
    if missing:
        raise ManifestError(
            f"manifest {path} is missing columns {sorted(missing)} — it was made by an older "
            "version; delete it and run `hrsurvey redact` again"
        )
    duplicated = frame.loc[frame["row_id"].duplicated(), "row_id"].tolist()
    if duplicated:
        raise ManifestError(f"manifest has duplicate rows: {duplicated[:5]}")
    return frame[list(MANIFEST_COLUMNS)]


def approved_rows(manifest: pd.DataFrame) -> pd.DataFrame:
    return manifest[manifest["approved"].str.strip().str.lower() == APPROVED]


def question_texts(header: tuple[str, ...], config: Config) -> dict[str, str]:
    """Full bilingual question text per text var_id (instrument text, no respondent data)."""
    return {c.var_id: normalize_header(header[c.idx]) for c in config.survey.text_columns()}
