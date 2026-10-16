from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from hrsurvey.cli import main
from hrsurvey.config import Config
from hrsurvey.ids import SALT_ENV_VAR

from conftest import CONFIG_DIR, N_PROFILES, TEST_SALT


@pytest.fixture(autouse=True)
def _salt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SALT_ENV_VAR, TEST_SALT.decode())


def test_schema_check_passes(synthetic_csv: Path) -> None:
    assert main(["schema-check", str(synthetic_csv), "--config", str(CONFIG_DIR)]) == 0


def test_standardize_writes_processed_tables(
    synthetic_csv: Path, tmp_path: Path, config: Config
) -> None:
    code = main(
        [
            "standardize",
            str(synthetic_csv),
            "--config",
            str(CONFIG_DIR),
            "--data-dir",
            str(tmp_path),
        ]
    )
    assert code == 0
    out = tmp_path / "processed" / "2026-10"
    long = pd.read_parquet(out / "answers_long.parquet")
    respondents = pd.read_parquet(out / "respondents.parquet")
    assert len(long) == N_PROFILES * 57
    assert len(respondents) == N_PROFILES
    assert respondents["response_id"].is_monotonic_increasing
    for frame in (long, respondents):
        assert not any("submitted" in column for column in frame.columns)
        assert not any(pd.api.types.is_datetime64_any_dtype(dtype) for dtype in frame.dtypes)
        text_cells = frame.select_dtypes(include=["object", "string"]).astype(str)
        timestamp_like = text_cells.apply(lambda col: col.str.match(config.survey.timestamp.regex))
        assert not timestamp_like.to_numpy().any()


def test_wave_cannot_escape_the_data_dir(synthetic_csv: Path, tmp_path: Path, capsys) -> None:
    args = ["standardize", str(synthetic_csv), "--config", str(CONFIG_DIR)]
    assert main([*args, "--data-dir", str(tmp_path), "--wave", "../../docs"]) == 2
    assert "wave" in capsys.readouterr().err
    assert not (tmp_path.parent / "docs").exists()


def test_errors_exit_nonzero_with_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text('"only","two"\n"a","b"\n', encoding="utf-8")
    assert main(["schema-check", str(bad), "--config", str(CONFIG_DIR)]) == 2
    assert "2 columns" in capsys.readouterr().err


def test_missing_salt_is_reported(
    synthetic_csv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.delenv(SALT_ENV_VAR)
    monkeypatch.chdir(tmp_path)  # no .env here
    args = ["standardize", str(synthetic_csv), "--config", str(CONFIG_DIR), "--data-dir", "."]
    assert main(args) == 2
    assert "init-salt" in capsys.readouterr().err


def test_init_salt_creates_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    assert main(["init-salt", "--env-file", str(env_file)]) == 0
    assert SALT_ENV_VAR in env_file.read_text()


def test_phase2_commands_end_to_end(
    synthetic_csv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from hrsurvey.text import pipeline
    from hrsurvey.text.manifest import read_manifest, write_manifest

    from fixtures.fake_anthropic import FakeClient

    base = ["--config", str(CONFIG_DIR), "--data-dir", str(tmp_path)]
    assert main(["redact", str(synthetic_csv), *base]) == 0
    assert "set approved=yes" in capsys.readouterr().out

    manifest_path = tmp_path / "interim" / "2026-10" / pipeline.MANIFEST_FILE
    write_manifest(read_manifest(manifest_path).assign(approved="yes"), manifest_path)

    assert main(["code-text", str(synthetic_csv), *base, "--dry-run"]) == 0
    assert "would send" in capsys.readouterr().out

    client = FakeClient()
    monkeypatch.setattr(pipeline, "make_client", lambda: client)
    assert main(["code-text", str(synthetic_csv), *base]) == 0
    assert client.beta.messages.calls, "approved rows must have been sent to the (fake) API"
    assert "review file" in capsys.readouterr().out

    args = ["review-import", "--wave", "2026-10", *base]
    assert main(args) == 2  # nothing reviewed yet
    assert "pending" in capsys.readouterr().err
    assert main([*args, "--allow-pending"]) == 0
    assert (tmp_path / "processed" / "2026-10" / "text_segments.parquet").is_file()


def test_missing_api_credentials_are_reported(
    synthetic_csv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    from hrsurvey.text import pipeline
    from hrsurvey.text.manifest import read_manifest, write_manifest

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.chdir(tmp_path)  # no .env with a key here
    base = ["--config", str(CONFIG_DIR), "--data-dir", str(tmp_path)]
    assert main(["redact", str(synthetic_csv), *base]) == 0
    manifest_path = tmp_path / "interim" / "2026-10" / pipeline.MANIFEST_FILE
    write_manifest(read_manifest(manifest_path).assign(approved="yes"), manifest_path)

    def no_credentials():
        raise pipeline.MissingCredentialsError("no Anthropic credentials: add ANTHROPIC_API_KEY")

    monkeypatch.setattr(pipeline, "make_client", no_credentials)
    assert main(["code-text", str(synthetic_csv), *base]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err
