"""Offline stand-ins for the Anthropic client — tests never call the real API."""

from __future__ import annotations

import json
from collections.abc import Callable
from types import SimpleNamespace

from hrsurvey.text.coder import CodedAnswer, CodingOutcome, CodingRequest

VALID_ANSWER = {
    "language": "en",
    "translation_en": "The ticket system is slow.",
    "segments": [
        {
            "text_en": "The ticket system is slow.",
            "theme": "TOOL.TOOLS_LACK",
            "new_theme_label": None,
            "secondary_theme": None,
            "locus": "process_tool",
            "valence": -1,
            "intensity": 2,
            "sarcasm": False,
            "actionable": False,
            "suggestion": None,
            "confidence": "high",
        }
    ],
}


def fake_response(
    payload: dict | str, stop_reason: str = "end_turn", model: str = "claude-opus-5-5"
) -> SimpleNamespace:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category="cyber") if stop_reason == "refusal" else None,
        model=model,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50, cache_read_input_tokens=900),
    )


class FakeMessages:
    def __init__(self, responder: Callable[[dict], SimpleNamespace]) -> None:
        self.calls: list[dict] = []
        self._responder = responder

    def create(self, **kwargs) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._responder(kwargs)


class FakeClient:
    def __init__(self, responder: Callable[[dict], SimpleNamespace] | None = None) -> None:
        self.beta = SimpleNamespace(
            messages=FakeMessages(responder or (lambda _: fake_response(VALID_ANSWER)))
        )


class FakeCoder:
    """Coder protocol double: records requests, answers every one with VALID_ANSWER."""

    def __init__(self) -> None:
        self.requests: list[CodingRequest] = []

    def code(self, request: CodingRequest) -> CodingOutcome:
        self.requests.append(request)
        return CodingOutcome(
            request.key, CodedAnswer.model_validate(VALID_ANSWER), None, "claude-opus-5-5", 10, 5
        )
