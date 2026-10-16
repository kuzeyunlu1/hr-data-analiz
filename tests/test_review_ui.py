"""Local review screen: page embeds data safely, saves validate and stay on localhost."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from hrsurvey.config import load_config
from hrsurvey.text.review import ReviewError, read_review
from hrsurvey.text.review_ui import build_page, save_rows, serve
from hrsurvey.text.settings import TextConfig

from conftest import CONFIG_DIR
from conftest import approve_all as _approve_all
from fixtures.fake_anthropic import FakeCoder


@pytest.fixture
def review_path(run) -> Path:
    redact, code, zone = run
    redact()
    _approve_all(zone)
    return code(FakeCoder).review_path


def test_page_cannot_be_broken_by_answer_text(review_path, text_config: TextConfig) -> None:
    review = read_review(review_path)
    review.loc[0, "text_en"] = "</script><script>alert(1)</script>"
    page = build_page(review, text_config.codebook, "tok")
    assert "</script><script>alert(1)" not in page
    assert page.count("</script>") == 1


def test_save_round_trip_and_guards(review_path) -> None:
    rows = read_review(review_path).assign(review_status="accepted").to_dict("records")
    assert save_rows(review_path, rows) == len(rows)
    assert set(read_review(review_path)["review_status"]) == {"accepted"}
    with pytest.raises(ReviewError, match="segment list"):
        save_rows(review_path, rows[1:])
    with pytest.raises(ReviewError, match="review_status"):
        save_rows(review_path, [{**rows[0], "review_status": "maybe"}, *rows[1:]])


def test_server_binds_localhost_and_requires_token(review_path, text_config) -> None:
    server, url = serve(review_path, text_config.codebook, port=0)
    assert server.server_address[0] == "127.0.0.1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert urllib.request.urlopen(url).status == 200
        base = url.rsplit("/", 1)[0]
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(base + "/")
        assert err.value.code == 404
        body = json.dumps({"rows": read_review(review_path).to_dict("records")}).encode()
        forged = urllib.request.Request(
            base + "/save", data=body, method="POST", headers={"X-Token": "wrong"}
        )
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(forged)
        assert err.value.code == 403
        token = url.rsplit("/", 1)[1]
        ok = urllib.request.Request(
            base + "/save",
            data=body,
            method="POST",
            headers={"X-Token": token, "Content-Type": "application/json"},
        )
        assert json.loads(urllib.request.urlopen(ok).read())["ok"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_every_code_has_plain_language_labels(text_config: TextConfig) -> None:
    from hrsurvey.text.review_labels import CATEGORIES_TR, LOCUS_TR, QUESTIONS_TR, THEMES_TR

    assert set(THEMES_TR) == set(text_config.codebook.themes)
    assert set(LOCUS_TR) == set(text_config.codebook.locus)
    assert {code.split(".")[0] for code in THEMES_TR} <= set(CATEGORIES_TR)
    sendable = {c.var_id for c in load_config(CONFIG_DIR).survey.text_columns()}
    assert set(QUESTIONS_TR) == sendable
