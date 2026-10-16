"""Stages 4 + 6: closed items -> answers_long (docs/05-standardization.md#output-tables)."""

from __future__ import annotations

import pandas as pd

from hrsurvey.config import ColumnSpec, Config
from hrsurvey.ingest import IngestResult, is_routed
from hrsurvey.scales import MappedValue, ScaleMapper
from hrsurvey.scoring import favorability, pomp
from hrsurvey.status import Status

ANSWERS_LONG_COLUMNS = (
    "response_id",
    "wave_id",
    "var_id",
    "q_no",
    "block",
    "scale_id",
    "polarity",
    "status",
    "code",
    "value",
    "pomp",
    "favorability",
    "label_unverified",
)


def _row(
    response_id: str, wave_id: str, column: ColumnSpec, mapped: MappedValue, config: Config
) -> dict:
    scored = mapped.code is not None
    spec = config.scales[column.scale_id]
    score = pomp(mapped.code, spec, column.polarity) if scored else None
    return {
        "response_id": response_id,
        "wave_id": wave_id,
        "var_id": column.var_id,
        "q_no": column.q_no,
        "block": column.block,
        "scale_id": column.scale_id,
        "polarity": column.polarity,
        "status": mapped.status.value,
        "code": mapped.code,
        "value": mapped.value,
        "pomp": score,
        "favorability": (
            favorability(score, config.scoring.cutoffs_for(column.scale_id)) if scored else None
        ),
        "label_unverified": mapped.unverified,
    }


def build_answers_long(
    ingested: IngestResult, config: Config
) -> tuple[pd.DataFrame, tuple[str, ...]]:
    """Return (answers_long, warnings). Warnings list every use of an unverified label."""
    mapper = ScaleMapper(config.scales)
    survey = config.survey
    branches = ingested.respondents.set_index("response_id")["branch"]
    rows, warnings = [], []
    for response_id, answers in ingested.answers.iterrows():
        branch = branches[response_id]
        for column in survey.closed_columns():
            if is_routed(column, branch, survey):
                mapped = mapper.map(column.scale_id, answers[column.var_id])
            else:
                mapped = MappedValue(Status.NOT_ROUTED)
            if mapped.unverified:
                warnings.append(
                    f"{column.var_id}: unverified label {answers[column.var_id].strip()!r} "
                    "— confirm in the form editor, then move it to `labels` in scales.yaml"
                )
            rows.append(_row(response_id, ingested.wave_id, column, mapped, config))
    frame = pd.DataFrame(rows, columns=list(ANSWERS_LONG_COLUMNS)).astype(
        {"code": "Int64", "value": "Float64", "pomp": "Float64", "label_unverified": "bool"}
    )
    return frame, tuple(dict.fromkeys(warnings))
