"""Command line entry point: `uv run hrsurvey <command> ...`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from hrsurvey.config import load_config
from hrsurvey.errors import HrSurveyError
from hrsurvey.ids import init_salt, load_salt
from hrsurvey.ingest import read_export, validate_export
from hrsurvey.pipeline import (
    interim_dir,
    load,
    prepare_text,
    processed_dir,
    standardize,
    write_table,
)

EXIT_OK = 0
EXIT_ERROR = 2


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("export", type=Path, help="Google Forms CSV export")
    parser.add_argument("--config", type=Path, default=Path("config"), help="config directory")


def _pipeline_args(parser: argparse.ArgumentParser) -> None:
    _common(parser)
    parser.add_argument("--wave", help="wave id (default: YYYY-MM of the first submission)")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="data root")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hrsurvey", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    _common(commands.add_parser("schema-check", help="validate an export against the schema"))
    _pipeline_args(commands.add_parser("standardize", help="closed items -> processed tables"))
    _pipeline_args(commands.add_parser("text-prep", help="free text -> interim text_answers"))
    salt = commands.add_parser("init-salt", help="create the ID salt in .env if missing")
    salt.add_argument("--env-file", type=Path, default=Path(".env"))
    _pipeline_args(commands.add_parser("redact", help="redact free text -> send manifest"))
    code = commands.add_parser("code-text", help="send APPROVED manifest rows for LLM coding")
    _pipeline_args(code)
    code.add_argument(
        "--dry-run", action="store_true", help="count what would be sent, send nothing"
    )
    review = commands.add_parser("review-import", help="reviewed codes -> processed text_segments")
    review.add_argument("--wave", required=True)
    review.add_argument("--config", type=Path, default=Path("config"))
    review.add_argument("--data-dir", type=Path, default=Path("data"))
    review.add_argument("--allow-pending", action="store_true", help="import unreviewed segments")
    ui = commands.add_parser("review-ui", help="open the local review screen in the browser")
    ui.add_argument("--wave", required=True)
    ui.add_argument("--config", type=Path, default=Path("config"))
    ui.add_argument("--data-dir", type=Path, default=Path("data"))
    ui.add_argument("--port", type=int, default=8765)
    ui.add_argument("--no-browser", action="store_true")
    return parser


def _counts(counts: pd.Series) -> str:
    return ", ".join(f"{key}={int(value)}" for key, value in counts.items())


def _schema_check(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    export = read_export(args.export)
    validate_export(export, config.survey)
    print(f"OK: {len(export.rows)} responses, {len(export.header)} columns match the schema")


def _standardize(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ingested = load(args.export, config, load_salt(), args.wave)
    result = standardize(ingested, config)
    out = processed_dir(args.data_dir, result.wave_id)
    write_table(result.respondents, out / "respondents.parquet")
    write_table(result.answers_long, out / "answers_long.parquet")
    flags = result.respondents.filter(like="qflag_").sum()
    print(f"wave {result.wave_id}: {len(result.respondents)} responses -> {out}")
    print(f"branches: {_counts(result.respondents['branch'].value_counts())}")
    print(f"closed-item statuses: {_counts(result.answers_long['status'].value_counts())}")
    print(f"quality flags: {_counts(flags[flags > 0]) or 'none'}")
    for warning in result.warnings:
        print(f"WARNING {warning}", file=sys.stderr)
    if flags.get("qflag_multiple_branches", 0):
        print(
            "WARNING responses with answers in more than one branch block — check the form routing",
            file=sys.stderr,
        )


def _text_prep(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ingested = load(args.export, config, load_salt(), args.wave)
    text = prepare_text(ingested, config)
    path = write_table(text, interim_dir(args.data_dir, ingested.wave_id) / "text_answers.parquet")
    print(f"wave {ingested.wave_id}: {len(text)} text cells -> {path}")
    print(f"text statuses: {_counts(text['status'].value_counts())}")


def _init_salt(args: argparse.Namespace) -> None:
    created = init_salt(args.env_file)
    print(f"salt {'created in' if created else 'already present in'} {args.env_file}")


def _text_command(name: str):
    """Phase 2 handlers are imported on use, so Phase 1 commands stay light."""

    def run(args: argparse.Namespace) -> None:
        from hrsurvey.text import commands

        getattr(commands, name)(args)

    return run


_HANDLERS = {
    "schema-check": _schema_check,
    "standardize": _standardize,
    "text-prep": _text_prep,
    "init-salt": _init_salt,
    "redact": _text_command("redact"),
    "code-text": _text_command("code_text"),
    "review-import": _text_command("review_import"),
    "review-ui": _text_command("review_ui"),
}


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        _HANDLERS[args.command](args)
    except HrSurveyError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
