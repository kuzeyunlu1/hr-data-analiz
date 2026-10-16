"""CLI handlers for Phase 2. Imported lazily so Phase 1 commands never load spaCy or the SDK."""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from hrsurvey.config import load_config
from hrsurvey.ids import load_salt
from hrsurvey.text import pipeline
from hrsurvey.text.coder import AnthropicCoder
from hrsurvey.text.settings import load_text_config


def _configs(args: argparse.Namespace):
    config = load_config(args.config)
    return config, load_text_config(args.config, config)


def redact(args: argparse.Namespace) -> None:
    config, text_cfg = _configs(args)
    result = pipeline.run_redact(
        args.export, config, text_cfg, load_salt(), args.wave, args.data_dir
    )
    print(f"send manifest: {result.path}")
    print(
        f"rows: {result.rows} · approved: {result.approved} · redactions made: {result.redactions}"
    )
    if result.approved < result.rows:
        print(
            "NEXT: review every row (compare text_original with text_redacted, edit "
            "text_redacted if needed) and set approved=yes. Only approved rows are ever sent."
        )


def code_text(args: argparse.Namespace) -> None:
    config, text_cfg = _configs(args)

    def coder_factory() -> AnthropicCoder:
        return AnthropicCoder(text_cfg.llm, text_cfg.codebook, pipeline.make_client())

    result = pipeline.run_code_text(
        args.export,
        config,
        text_cfg,
        load_salt(),
        args.wave,
        args.data_dir,
        coder_factory,
        dry_run=args.dry_run,
    )
    print(
        f"approved rows: {result.approved} · not approved (skipped): {result.not_approved} · "
        f"cached: {result.cached} · {'would send' if args.dry_run else 'sent'}: {result.to_send}"
        f" unique answers to {text_cfg.llm.model}"
    )
    if args.dry_run:
        return
    print(f"tokens: input {result.input_tokens} · output {result.output_tokens}")
    for error, count in Counter(result.errors).most_common():
        print(f"WARNING {count}x coding failed: {error} (re-run to retry)", file=sys.stderr)
    print(f"review file: {result.review_path}")
    print(
        "NEXT: review codes, set review_status (accepted/edited/rejected), then run review-import."
    )


def review_import(args: argparse.Namespace) -> None:
    config, text_cfg = _configs(args)
    path, segments = pipeline.run_review_import(
        text_cfg, args.wave, args.data_dir, args.allow_pending
    )
    print(f"{len(segments)} segments -> {path}")


def review_ui(args: argparse.Namespace) -> None:
    import webbrowser

    from hrsurvey.pipeline import interim_dir
    from hrsurvey.text.review_ui import serve

    config, text_cfg = _configs(args)
    path = interim_dir(args.data_dir, args.wave) / pipeline.REVIEW_FILE
    if not path.is_file():
        raise pipeline.ManifestError("no review file yet — run `hrsurvey code-text` first")
    server, url = serve(path, text_cfg.codebook, args.port)
    print(f"review screen (local only): {url}", flush=True)
    print("every decision is saved straight to the review file · Ctrl+C to stop", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
