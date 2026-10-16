from __future__ import annotations

import re
from pathlib import Path

import pytest

from hrsurvey.errors import MissingSaltError
from hrsurvey.ids import SALT_ENV_VAR, init_salt, load_salt, response_ids

from conftest import TEST_SALT

ROWS = [("2026/10/15 1:00:00 ÖÖ GMT+3", "a", "b"), ("2026/10/15 2:00:00 ÖÖ GMT+3", "a", "b")]


def test_ids_are_stable_and_well_formed() -> None:
    first = response_ids(ROWS, TEST_SALT)
    assert first == response_ids(ROWS, TEST_SALT)
    assert all(re.fullmatch(r"r_[0-9a-f]{16}", rid) for rid in first)
    assert len(set(first)) == len(first)


def test_ids_do_not_depend_on_row_position() -> None:
    forward = response_ids(ROWS, TEST_SALT)
    backward = response_ids(list(reversed(ROWS)), TEST_SALT)
    assert forward == list(reversed(backward))


def test_ids_change_with_salt() -> None:
    other_salt = b"another-salt-0123456789abcdef0123456789"
    assert response_ids(ROWS, TEST_SALT) != response_ids(ROWS, other_salt)


def test_identical_rows_get_distinct_ids() -> None:
    ids = response_ids([ROWS[0], ROWS[0]], TEST_SALT)
    assert ids[0] != ids[1]


def test_load_salt_prefers_environment(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"{SALT_ENV_VAR}={'f' * 40}\n")
    assert load_salt({SALT_ENV_VAR: "e" * 40}, env_file) == b"e" * 40


def test_load_salt_falls_back_to_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"# comment\n{SALT_ENV_VAR}='{'f' * 40}'\n")
    assert load_salt({}, env_file) == b"f" * 40


@pytest.mark.parametrize("value", [None, "too-short"])
def test_load_salt_rejects_missing_or_short(value: str | None, tmp_path: Path) -> None:
    env = {} if value is None else {SALT_ENV_VAR: value}
    with pytest.raises(MissingSaltError):
        load_salt(env, tmp_path / "absent.env")


def test_init_salt_writes_once(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER=1")  # no trailing newline
    assert init_salt(env_file) is True
    content = env_file.read_text()
    assert init_salt(env_file) is False
    assert env_file.read_text() == content
    assert content.startswith("OTHER=1\n")
    assert len(load_salt({}, env_file)) == 64
    assert env_file.stat().st_mode & 0o777 == 0o600
