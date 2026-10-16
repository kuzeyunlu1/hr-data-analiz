from __future__ import annotations

import pytest

from hrsurvey.config import Config
from hrsurvey.status import Status
from hrsurvey.text_status import TextClassifier, normalize_text, resolve_residual


@pytest.fixture(scope="module")
def classifier(config: Config) -> TextClassifier:
    return TextClassifier(config.nonanswer)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("I don´t have  any\ncustomer contact ", "I don't have any customer contact"),
        ("It’s fine", "It's fine"),
        ("Weiss  ich\tnicht", "Weiss ich nicht"),
        ("", ""),
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


# --- cases decided without the residual rule --------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", Status.EMPTY),
        ("   ", Status.EMPTY),
        ("-", Status.PLACEHOLDER),
        (".", Status.PLACEHOLDER),
        ("n/a", Status.PLACEHOLDER),
        ("Having to follow up constantly", Status.SUBSTANTIVE),
        ("I'm pretty much on my own.", Status.SUBSTANTIVE),
        # "don't know" is only a non-answer at the start of the text
        ("We don't know what the strategy is", Status.SUBSTANTIVE),
        # non-answer phrases inside a real answer must not match at all
        ("I don't know who is responsible for approvals", Status.SUBSTANTIVE),
        ("No idea who owns the CRM", Status.SUBSTANTIVE),
        ("Ich weiß nicht, wer zuständig ist", Status.SUBSTANTIVE),
        ("Responsibilities are clearly not defined", Status.SUBSTANTIVE),
        ("I can't think of anyone who helps me", Status.SUBSTANTIVE),
    ],
)
def test_classification_without_pattern_match(
    classifier: TextClassifier, raw: str, expected: Status
) -> None:
    assert classifier.classify(raw) == expected


# --- cases that depend on resolve_residual() --------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("There is no obstacle.", Status.NO_ISSUE),
        ("The responsibilities are clear.", Status.NO_ISSUE),
        ("Keine Änderung nötig.", Status.NO_ISSUE),
        ("I don´t have any customer contact", Status.NO_BASIS),
        ("I'm not in a position to answer that", Status.NO_BASIS),
        ("In my position, I am not in a position to assess this properly.", Status.NO_BASIS),
        ("Kann ich nicht beurteilen", Status.NO_BASIS),
        ("I dont know?", Status.NOTHING_TO_ADD),
        ("I couldn't think of one", Status.NOTHING_TO_ADD),
        ("Weiß ich nicht", Status.NOTHING_TO_ADD),
        # "nothing" gets the same status in both languages
        ("Nothing.", Status.NOTHING_TO_ADD),
        ("Nichts.", Status.NOTHING_TO_ADD),
        ("None", Status.NOTHING_TO_ADD),
        # short elaboration of a non-answer stays a non-answer
        (
            "No change is necessary. If I need access to information, I'll find a way to get it",
            Status.NO_ISSUE,
        ),
        # a contrast turns it into real content, however short
        ("No obstacle, but the VPN drops daily.", Status.SUBSTANTIVE),
        ("Kein Hindernis, aber das Ticketsystem ist langsam.", Status.SUBSTANTIVE),
        # a long residual is real content
        (
            "No obstacle in my team, but other departments never answer my emails "
            "and I lose hours every week.",
            Status.SUBSTANTIVE,
        ),
    ],
)
def test_classification_with_residual_rule(
    classifier: TextClassifier, raw: str, expected: Status
) -> None:
    assert classifier.classify(raw) == expected


@pytest.mark.parametrize(
    ("matched", "residual", "expected"),
    [
        (Status.NO_ISSUE, "", Status.NO_ISSUE),
        (Status.NO_ISSUE, ".", Status.NO_ISSUE),
        (Status.NO_BASIS, "in my position, i am this properly.", Status.NO_BASIS),
        (Status.NO_ISSUE, ", but the vpn drops daily.", Status.SUBSTANTIVE),
        (Status.NO_ISSUE, ", jedoch fehlt ein ticketsystem", Status.SUBSTANTIVE),
        (Status.NOTHING_TO_ADD, " " + " ".join(["word"] * 16), Status.SUBSTANTIVE),
        # marker must be a whole word: "butter" is not "but"
        (Status.NO_ISSUE, " butter and bread", Status.NO_ISSUE),
    ],
)
def test_resolve_residual(config: Config, matched: Status, residual: str, expected: Status) -> None:
    assert resolve_residual(matched, residual, config.nonanswer.residual) == expected
