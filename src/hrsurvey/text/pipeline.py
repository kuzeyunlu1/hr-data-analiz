"""Phase 2 orchestration: redact -> (analyst approves manifest) -> code-text -> (analyst reviews) ->
review-import. All files live in the restricted zones under data/ (docs/08 › Data zones)."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import anthropic
import pandas as pd

from hrsurvey.config import Config
from hrsurvey.errors import ConfigError, ManifestError, MissingCredentialsError
from hrsurvey.ids import read_env_file
from hrsurvey.ingest import ingest, read_export
from hrsurvey.pipeline import interim_dir, processed_dir, standardize, write_table
from hrsurvey.text.coder import (
    CodeCache,
    Coder,
    CodingRequest,
    code_requests,
    prompt_fingerprint,
    request_key,
)
from hrsurvey.text.manifest import (
    approved_rows,
    build_manifest,
    question_texts,
    read_manifest,
    write_manifest,
)
from hrsurvey.text.redact import Redactor
from hrsurvey.text.review import (
    import_review,
    llm_segments,
    merge_review,
    read_review,
    rule_segments,
    write_review,
)
from hrsurvey.text.settings import TextConfig
from hrsurvey.text_prep import build_text_answers

API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
AUTH_TOKEN_ENV_VAR = "ANTHROPIC_AUTH_TOKEN"
WORKSPACE_ENV_VAR = "ANTHROPIC_WORKSPACE_ID"
STALE_REVIEW_FILE = "review_stale.csv"
MANIFEST_FILE = "llm_manifest.csv"
CACHE_FILE = "llm_codes.jsonl"
REVIEW_FILE = "review_segments.csv"
SEGMENTS_FILE = "text_segments.parquet"


@dataclass(frozen=True)
class RedactResult:
    path: Path
    rows: int
    approved: int
    redactions: int


@dataclass(frozen=True)
class CodeTextResult:
    approved: int
    not_approved: int
    cached: int
    to_send: int
    errors: tuple[str, ...]
    review_path: Path | None
    input_tokens: int
    output_tokens: int


def make_client(env_file: Path = Path(".env")) -> anthropic.Anthropic:
    """API key (or auth token) from the environment or .env. Checked here because the SDK only
    fails at request time, which would surface as a raw TypeError mid-run."""
    file_values = read_env_file(env_file)
    key = os.environ.get(API_KEY_ENV_VAR) or file_values.get(API_KEY_ENV_VAR)
    workspace = os.environ.get(WORKSPACE_ENV_VAR) or file_values.get(WORKSPACE_ENV_VAR)
    # keys not scoped to a workspace must name one on every request
    headers = {"anthropic-workspace-id": workspace} if workspace else None
    if key:
        return anthropic.Anthropic(api_key=key, default_headers=headers)
    if os.environ.get(AUTH_TOKEN_ENV_VAR):
        return anthropic.Anthropic(default_headers=headers)
    raise MissingCredentialsError(
        f"no Anthropic credentials: add {API_KEY_ENV_VAR}=... to .env (gitignored, never commit)"
    )


def run_redact(
    export_path: Path,
    config: Config,
    text_cfg: TextConfig,
    salt: bytes,
    wave: str | None,
    data_dir: Path,
) -> RedactResult:
    ingested = ingest(read_export(export_path), config, salt, wave)
    standardized = standardize(ingested, config)
    respondents = standardized.respondents
    unreliable = frozenset(respondents.loc[respondents["qflag_inconsistent"], "response_id"])
    path = interim_dir(data_dir, ingested.wave_id) / MANIFEST_FILE
    existing = read_manifest(path) if path.is_file() else None
    manifest = build_manifest(
        build_text_answers(ingested, config),
        standardized.answers_long,
        text_cfg,
        Redactor(text_cfg.redaction),
        existing,
        unreliable,
    )
    write_manifest(manifest, path)
    redactions = sum(
        int(part.rsplit("x", 1)[1])
        for summary in manifest["redactions"]
        if summary
        for part in summary.split(", ")
    )
    return RedactResult(path, len(manifest), len(approved_rows(manifest)), redactions)


def run_code_text(
    export_path: Path,
    config: Config,
    text_cfg: TextConfig,
    salt: bytes,
    wave: str | None,
    data_dir: Path,
    coder_factory: Callable[[], Coder],
    dry_run: bool = False,
) -> CodeTextResult:
    export = read_export(export_path)
    ingested = ingest(export, config, salt, wave)
    zone = interim_dir(data_dir, ingested.wave_id)
    if not (zone / MANIFEST_FILE).is_file():
        raise ManifestError("no send manifest yet — run `hrsurvey redact` first")
    manifest = read_manifest(zone / MANIFEST_FILE)
    approved = approved_rows(manifest)
    questions = question_texts(export.header, config)
    codebook, llm = text_cfg.codebook, text_cfg.llm
    unknown = sorted(set(approved["var_id"]) - set(questions))
    if unknown:
        raise ManifestError(f"manifest rows reference non-text or unknown questions: {unknown}")

    fingerprint = prompt_fingerprint(codebook)
    keys = {
        row.row_id: request_key(
            fingerprint,
            llm,
            questions[row.var_id],
            row.status,
            row.engagement_band,
            row.text_redacted,
        )
        for row in approved.itertuples(index=False)
    }
    requests = [
        CodingRequest(
            keys[r.row_id],
            r.var_id,
            questions[r.var_id],
            r.status,
            r.engagement_band,
            r.text_redacted,
        )
        for r in approved.itertuples(index=False)
    ]
    cache = CodeCache(zone / CACHE_FILE)
    cached = cache.load()
    todo = [r for r in requests if r.key not in cached]
    unique_todo = len({r.key for r in todo})
    if dry_run:
        return CodeTextResult(
            len(approved),
            len(manifest) - len(approved),
            len(requests) - len(todo),
            unique_todo,
            (),
            None,
            0,
            0,
        )

    try:
        outcomes = (
            code_requests(todo, coder_factory(), llm.max_workers, lambda o: cache.append([o]))
            if todo
            else []
        )
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as err:
        raise MissingCredentialsError(
            f"the Anthropic API rejected the credentials ({err.status_code}); "
            "results received before the error are cached"
        ) from None
    except anthropic.NotFoundError:
        raise ConfigError(f"model {llm.model!r} not found — check config/llm.yaml") from None
    by_key = {**cached, **{o.key: o for o in outcomes}}

    fresh = pd.concat(
        [
            llm_segments(approved, keys, by_key, codebook),
            rule_segments(build_text_answers(ingested, config), llm, codebook),
        ],
        ignore_index=True,
    )
    review_path = zone / REVIEW_FILE
    existing = read_review(review_path) if review_path.is_file() else None
    merged, stale = merge_review(fresh, existing)
    write_review(merged, review_path)
    if (
        not stale.empty
    ):  # decisions on answers that changed since — kept for reference, not imported
        write_review(stale, zone / STALE_REVIEW_FILE)
    return CodeTextResult(
        approved=len(approved),
        not_approved=len(manifest) - len(approved),
        cached=len(requests) - len(todo),
        to_send=unique_todo,
        errors=tuple(o.error for o in outcomes if not o.ok),
        review_path=review_path,
        input_tokens=sum(o.input_tokens for o in outcomes),
        output_tokens=sum(o.output_tokens for o in outcomes),
    )


def run_review_import(
    text_cfg: TextConfig, wave: str, data_dir: Path, allow_pending: bool
) -> tuple[Path, pd.DataFrame]:
    review_path = interim_dir(data_dir, wave) / REVIEW_FILE
    if not review_path.is_file():
        raise ManifestError("no review file yet — run `hrsurvey code-text` first")
    segments = import_review(review_path, text_cfg.codebook, wave, allow_pending)
    return write_table(segments, processed_dir(data_dir, wave) / SEGMENTS_FILE), segments
