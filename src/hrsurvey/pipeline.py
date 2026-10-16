"""Orchestration of the Phase 1 stages and output locations (docs/08 › Data zones)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from hrsurvey.config import Config
from hrsurvey.errors import WaveError
from hrsurvey.ingest import IngestResult, ingest, read_export
from hrsurvey.quality import build_respondents
from hrsurvey.standardize import build_answers_long
from hrsurvey.text_prep import build_text_answers


@dataclass(frozen=True)
class StandardizeResult:
    wave_id: str
    respondents: pd.DataFrame
    answers_long: pd.DataFrame
    warnings: tuple[str, ...]


def load(export_path: Path, config: Config, salt: bytes, wave: str | None) -> IngestResult:
    return ingest(read_export(export_path), config, salt, wave)


def standardize(ingested: IngestResult, config: Config) -> StandardizeResult:
    answers_long, warnings = build_answers_long(ingested, config)
    respondents = build_respondents(ingested, answers_long, config)
    return StandardizeResult(ingested.wave_id, respondents, answers_long, warnings)


def prepare_text(ingested: IngestResult, config: Config) -> pd.DataFrame:
    return build_text_answers(ingested, config)


def _zone_dir(data_dir: Path, zone: str, wave_id: str) -> Path:
    target = data_dir / zone / wave_id
    if not target.resolve().is_relative_to((data_dir / zone).resolve()):
        raise WaveError("wave id would write outside the data directory")
    return target


def processed_dir(data_dir: Path, wave_id: str) -> Path:
    """Closed-item tables. Respondent-level → restricted, gitignored."""
    return _zone_dir(data_dir, "processed", wave_id)


def interim_dir(data_dir: Path, wave_id: str) -> Path:
    """Tables that still contain respondents' own words. Restricted, gitignored."""
    return _zone_dir(data_dir, "interim", wave_id)


def write_table(frame: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    return path
