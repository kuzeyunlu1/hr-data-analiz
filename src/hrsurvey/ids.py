"""Stable pseudonymous response IDs (DECISIONS D-011).

ID = HMAC-SHA256(secret salt, full raw row). Properties:
- stable across re-runs and across growing exports (needed to re-join human review files);
- not derivable without the salt, and not ordered by time or row position;
- the salt lives only in the analyst's environment (.env, gitignored).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from hrsurvey.errors import MissingSaltError

SALT_ENV_VAR = "HRSURVEY_ID_SALT"
MIN_SALT_LENGTH = 32
_FIELD_SEP = "\x1f"
_OCCURRENCE_SEP = "\x1e"


def response_ids(rows: Sequence[Sequence[str]], salt: bytes) -> list[str]:
    """One ID per row. Byte-identical rows get distinct IDs via an occurrence counter."""
    seen: Counter[str] = Counter()
    ids = []
    for row in rows:
        payload = _FIELD_SEP.join(row)
        occurrence = seen[payload]
        seen[payload] += 1
        message = f"{payload}{_OCCURRENCE_SEP}{occurrence}".encode()
        digest = hmac.new(salt, message, hashlib.sha256).hexdigest()
        ids.append(f"r_{digest[:16]}")
    return ids


def read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    pairs = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        pairs[key.strip()] = value.strip().strip("'\"")
    return pairs


def load_salt(env: Mapping[str, str] | None = None, env_file: Path | None = None) -> bytes:
    """Salt from the environment variable, else from a .env file. Raises if absent or too short."""
    environment = os.environ if env is None else env
    value = environment.get(SALT_ENV_VAR) or read_env_file(env_file or Path(".env")).get(
        SALT_ENV_VAR
    )
    if not value:
        raise MissingSaltError(
            f"{SALT_ENV_VAR} is not set. Run `uv run hrsurvey init-salt` once to create it in .env."
        )
    if len(value) < MIN_SALT_LENGTH:
        raise MissingSaltError(f"{SALT_ENV_VAR} must be at least {MIN_SALT_LENGTH} characters")
    return value.encode()


def init_salt(env_file: Path) -> bool:
    """Append a random salt to env_file unless one exists; True if one was written."""
    if read_env_file(env_file).get(SALT_ENV_VAR):
        return False
    prefix = "" if not env_file.exists() or env_file.read_text().endswith("\n") else "\n"
    with env_file.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{SALT_ENV_VAR}={secrets.token_hex(32)}\n")
    env_file.chmod(0o600)  # owner read/write only
    return True
