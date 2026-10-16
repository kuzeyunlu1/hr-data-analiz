from __future__ import annotations

from pathlib import Path

import pytest

from hrsurvey.config import Config, load_config
from hrsurvey.ids import response_ids
from hrsurvey.ingest import IngestResult, ingest, read_export
from hrsurvey.text import pipeline
from hrsurvey.text.manifest import read_manifest, write_manifest
from hrsurvey.text.redact import Redactor
from hrsurvey.text.settings import TextConfig, load_text_config

from fixtures.make_synthetic import PROFILES, write_synthetic

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
TEST_SALT = b"test-salt-0123456789abcdef0123456789abcdef"
N_PROFILES = len(PROFILES)


@pytest.fixture(scope="session")
def config() -> Config:
    return load_config(CONFIG_DIR)


@pytest.fixture(scope="session")
def synthetic_csv(config: Config, tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("synthetic") / "survey_export_synthetic.csv"
    return write_synthetic([c.var_id for c in config.survey.columns], out)


@pytest.fixture(scope="session")
def ingested(synthetic_csv: Path, config: Config) -> IngestResult:
    return ingest(read_export(synthetic_csv), config, TEST_SALT, wave=None)


@pytest.fixture(scope="session")
def text_config(config: Config) -> TextConfig:
    return load_text_config(CONFIG_DIR, config)


@pytest.fixture(scope="session")
def redactor(text_config: TextConfig) -> Redactor:
    return Redactor(text_config.redaction)  # spaCy models load once per test session


@pytest.fixture(scope="session")
def profile_ids(synthetic_csv: Path) -> dict[str, str]:
    """Synthetic profile name -> response_id, computed independently of output row order."""
    ids = response_ids(read_export(synthetic_csv).rows, TEST_SALT)
    return dict(zip(PROFILES, ids, strict=True))


@pytest.fixture
def run(synthetic_csv: Path, config: Config, text_config: TextConfig, tmp_path: Path):
    def redact():
        return pipeline.run_redact(synthetic_csv, config, text_config, TEST_SALT, None, tmp_path)

    def code(factory, dry_run=False):
        return pipeline.run_code_text(
            synthetic_csv, config, text_config, TEST_SALT, None, tmp_path, factory, dry_run
        )

    return redact, code, tmp_path / "interim" / "2026-10"


def approve_all(zone: Path) -> int:
    manifest = read_manifest(zone / pipeline.MANIFEST_FILE)
    write_manifest(manifest.assign(approved="yes"), zone / pipeline.MANIFEST_FILE)
    return len(manifest)
