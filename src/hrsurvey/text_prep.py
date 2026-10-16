"""Stage 5 output: text_answers (restricted zone — contains normalized original text).

Redaction, translation and segmentation (stage 7) are Phase 2.
"""

from __future__ import annotations

import pandas as pd

from hrsurvey.config import Config
from hrsurvey.ingest import IngestResult, is_routed
from hrsurvey.status import Status
from hrsurvey.text_status import TextClassifier, normalize_text

TEXT_ANSWER_COLUMNS = (
    "response_id",
    "wave_id",
    "var_id",
    "q_no",
    "block",
    "status",
    "counts_as_signal",
    "text_norm",
)

_SIGNAL_STATUSES = frozenset({Status.SUBSTANTIVE, Status.NO_ISSUE})


def counts_as_signal(status: Status, var_id: str, config: Config) -> bool:
    """SUBSTANTIVE / NO_ISSUE always count; NOTHING_TO_ADD only where "nothing" is meaningful."""
    if status in _SIGNAL_STATUSES:
        return True
    return status == Status.NOTHING_TO_ADD and var_id in config.nonanswer.meaningful_nothing_vars


def build_text_answers(ingested: IngestResult, config: Config) -> pd.DataFrame:
    classifier = TextClassifier(config.nonanswer)
    survey = config.survey
    branches = ingested.respondents.set_index("response_id")["branch"]
    rows = []
    for response_id, answers in ingested.answers.iterrows():
        for column in survey.text_columns():
            raw = answers[column.var_id]
            routed = is_routed(column, branches[response_id], survey)
            status = classifier.classify(raw) if routed else Status.NOT_ROUTED
            rows.append(
                {
                    "response_id": response_id,
                    "wave_id": ingested.wave_id,
                    "var_id": column.var_id,
                    "q_no": column.q_no,
                    "block": column.block,
                    "status": status.value,
                    "counts_as_signal": counts_as_signal(status, column.var_id, config),
                    "text_norm": normalize_text(raw) if routed else "",
                }
            )
    return pd.DataFrame(rows, columns=list(TEXT_ANSWER_COLUMNS))
