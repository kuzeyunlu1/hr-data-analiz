from __future__ import annotations

import pytest

from hrsurvey.text.redact import Redactor

# Synthetic sentences only — never real survey answers.


@pytest.mark.parametrize(
    ("text", "placeholder", "gone"),
    [
        ("Please write to t.becker@example.com about it", "[EMAIL]", "t.becker@example.com"),
        ("The docs are at https://intranet.example.com/wiki", "[URL]", "intranet.example.com"),
        ("Call me on +49 30 1234 5678 tomorrow", "[PHONE]", "1234 5678"),
        ("Ruf an: 0171 2345678", "[PHONE]", "2345678"),
        ("Refund to DE89 3704 0044 0532 0130 00 please", "[IBAN]", "3704"),
        ("Herr Schmidt hat mir nie geantwortet.", "[PERSON]", "Schmidt"),
        ("Thomas Becker from sales never answers my emails.", "[PERSON]", "Becker"),
        ("Anna Schneider aus dem Vertrieb ist sehr hilfsbereit.", "[PERSON]", "Schneider"),
        ("Ruf mich an unter 0151 2345678.", "[PHONE]", "2345678"),  # sentence-final
        ("Frau Dr. Müller hat nie geantwortet.", "[PERSON]", "Müller"),  # stacked titles
        ("herr becker antwortet nie", "[PERSON]", "becker"),  # lower case
        ("Herr Šimić antwortet nie", "[PERSON]", "Šimić"),  # non-ASCII initial
    ],
)
def test_personal_data_is_redacted(redactor: Redactor, text: str, placeholder: str, gone: str):
    result = redactor.redact(text)
    assert placeholder in result.text
    assert gone not in result.text
    assert result.counts[placeholder] >= 1


@pytest.mark.parametrize(
    "text",
    [
        "Since 2026/10/15 and 15.10.2026 nothing has changed.",  # dates are not phone numbers
        "We closed 120 deals worth 45000 euros.",
        "Customers keep asking about Microsoft 365 migrations.",  # allowlisted vendor
        "Kein Hindernis, aber das Ticketsystem ist langsam.",
    ],
)
def test_ordinary_content_is_kept(redactor: Redactor, text: str) -> None:
    result = redactor.redact(text)
    assert result.text == text
    assert result.summary == ""


def test_existing_placeholders_are_not_retagged(redactor: Redactor) -> None:
    once = redactor.redact("Thomas Becker from sales never answers my emails.")
    assert redactor.redact(once.text).text == once.text


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Die Zusammenarbeit mit dem Vertrieb funktioniert nicht gut.", "de"),
        ("Cooperation with the sales team does not work well.", "en"),
    ],
)
def test_language_detection(redactor: Redactor, text: str, language: str) -> None:
    assert redactor.redact(text).language == language
