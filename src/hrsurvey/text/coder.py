"""LLM-assisted coding of one redacted answer per request (docs/07 › LLM-assisted coding protocol).

Each request carries: the question text, the answer's status, a coarse engagement band and the
redacted answer — never response IDs, branch, timestamps or other answers of the same person.
Translation to English and segmentation happen in the same call. Results are cached by a key over
(codebook version, model, question, answer text), so re-runs only send what changed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import anthropic
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from hrsurvey.errors import HrSurveyError
from hrsurvey.text.settings import NEW_THEME, Codebook, LlmConfig


class CacheError(HrSurveyError):
    """The local LLM-code cache is corrupt."""


Confidence = Literal["low", "medium", "high"]


class CodedSegment(BaseModel):
    # hide_input_in_errors: a validation error must never echo respondent text to the terminal
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    text_en: str
    theme: str
    new_theme_label: str | None
    secondary_theme: str | None
    locus: str
    valence: Literal[-1, 0, 1]
    intensity: Literal[1, 2, 3]
    sarcasm: bool
    actionable: bool
    suggestion: str | None
    confidence: Confidence

    @model_validator(mode="after")
    def _new_theme_needs_label(self) -> CodedSegment:
        if self.theme == NEW_THEME and not (self.new_theme_label or "").strip():
            raise ValueError("theme NEW requires new_theme_label")
        return self


class CodedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", hide_input_in_errors=True)

    language: Literal["en", "de", "mixed", "other"]
    translation_en: str
    segments: tuple[CodedSegment, ...]


@dataclass(frozen=True)
class CodingRequest:
    key: str
    var_id: str
    question: str
    status: str
    engagement_band: str
    text: str


@dataclass(frozen=True)
class CodingOutcome:
    key: str
    answer: CodedAnswer | None
    error: str | None
    model: str | None
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def ok(self) -> bool:
        return self.answer is not None


def prompt_fingerprint(codebook: Codebook) -> str:
    """Hash of everything the model is told — a codebook edit invalidates the cache even
    when nobody bumps `version`."""
    content = system_prompt(codebook) + json.dumps(output_schema(codebook), sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def request_key(
    fingerprint: str, llm: LlmConfig, question: str, status: str, band: str, text: str
) -> str:
    """Covers every input of the request: same key <=> identical request."""
    payload = "\x1f".join((fingerprint, llm.model, llm.effort, question, status, band, text))
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


# --- prompt & schema ---------------------------------------------------------------------------


def output_schema(codebook: Codebook) -> dict:
    themes = [*codebook.themes, NEW_THEME]
    nullable_str = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    segment = {
        "type": "object",
        "properties": {
            "text_en": {"type": "string"},
            "theme": {"type": "string", "enum": themes},
            "new_theme_label": nullable_str,
            "secondary_theme": {"anyOf": [{"type": "string", "enum": themes}, {"type": "null"}]},
            "locus": {"type": "string", "enum": list(codebook.locus)},
            "valence": {"type": "integer", "enum": [-1, 0, 1]},
            "intensity": {"type": "integer", "enum": [1, 2, 3]},
            "sarcasm": {"type": "boolean"},
            "actionable": {"type": "boolean"},
            "suggestion": nullable_str,
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": list(CodedSegment.model_fields),
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "language": {"type": "string", "enum": ["en", "de", "mixed", "other"]},
            "translation_en": {"type": "string"},
            "segments": {"type": "array", "items": segment},
        },
        "required": ["language", "translation_en", "segments"],
        "additionalProperties": False,
    }


def system_prompt(codebook: Codebook) -> str:
    themes = "\n".join(f"- {code}: {definition}" for code, definition in codebook.themes.items())
    loci = "\n".join(f"- {name}: {definition}" for name, definition in codebook.locus.items())
    rules = "\n".join(f"- {rule}" for rule in codebook.rules)
    examples = "\n\n".join(
        f"Question: {ex.question}\nAnswer: {ex.answer}\nSegments: "
        + json.dumps([s.model_dump(exclude_none=True) for s in ex.segments], ensure_ascii=False)
        for ex in codebook.examples
    )
    return f"""You code free-text answers from an anonymous employee survey of a German-speaking \
IT services company. Answers are in English or German. The results feed a group-level analysis of \
leadership, collaboration and process issues; no individual is ever evaluated.

For each answer: detect its language, translate it faithfully into English (keep the meaning, \
tone and any [PLACEHOLDER] tokens; gloss internal German jargon in parentheses), split it into \
idea units and code every unit with the codebook below.

Codebook version {codebook.version}.

Themes:
{themes}
- NEW: no theme fits; give a short new_theme_label.

Locus (who or what the respondent holds responsible or describes):
{loci}

Valence: -1 negative, 0 neutral or descriptive, 1 positive — as intended by the respondent.
Intensity: 1 mild, 2 clear, 3 strong (absolute language, emotional emphasis, explicit consequences).
Actionable: true if the segment contains a concrete, implementable suggestion; then put it, \
shortened and neutral, in `suggestion`.
Confidence: how sure you are about the theme and locus.

Rules:
{rules}

Synthetic examples:
{examples}"""


def user_message(request: CodingRequest) -> str:
    return (
        f"<question>{request.question}</question>\n"
        f"<answer_status>{request.status}</answer_status>\n"
        f"<respondent_engagement>{request.engagement_band}</respondent_engagement>\n"
        f"<answer>{request.text}</answer>\n\n"
        "Code the answer. Respondent engagement is a coarse band from their scale answers; "
        "use it only as a hint when judging irony."
    )


# --- client ------------------------------------------------------------------------------------


class Coder(Protocol):
    def code(self, request: CodingRequest) -> CodingOutcome: ...


class AnthropicCoder:
    def __init__(self, llm: LlmConfig, codebook: Codebook, client: anthropic.Anthropic) -> None:
        self._llm = llm
        self._codebook = codebook
        self._client = client
        self._system = system_prompt(codebook)
        self._schema = output_schema(codebook)

    def request_params(self, request: CodingRequest) -> dict:
        params = {
            "model": self._llm.model,
            "max_tokens": self._llm.max_tokens,
            "system": [
                {"type": "text", "text": self._system, "cache_control": {"type": "ephemeral"}}
            ],
            "output_config": {
                "effort": self._llm.effort,
                "format": {"type": "json_schema", "schema": self._schema},
            },
            "messages": [{"role": "user", "content": user_message(request)}],
        }
        if self._llm.fallbacks:
            params["betas"] = [self._llm.fallback_beta]
            params["fallbacks"] = self._llm.fallbacks
        return params

    def code(self, request: CodingRequest) -> CodingOutcome:
        try:
            response = self._client.beta.messages.create(**self.request_params(request))
        except anthropic.BadRequestError as err:
            return CodingOutcome(
                request.key, None, f"bad request ({err.status_code}): {_api_message(err)}", None
            )
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
            anthropic.NotFoundError,
        ):
            raise  # fatal for the whole run (bad key, no access, wrong model) — stop everything
        except anthropic.RateLimitError:
            return CodingOutcome(request.key, None, "rate limited after retries", None)
        except anthropic.APIStatusError as err:
            return CodingOutcome(request.key, None, f"API error ({err.status_code})", None)
        except anthropic.APIConnectionError:
            return CodingOutcome(request.key, None, "connection error after retries", None)
        return self._parse(request, response)

    def _parse(self, request: CodingRequest, response) -> CodingOutcome:
        usage = response.usage
        meta = {
            "model": response.model,
            "input_tokens": (usage.input_tokens or 0)
            + (getattr(usage, "cache_read_input_tokens", 0) or 0)
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0),
            "output_tokens": usage.output_tokens or 0,
        }
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None)
            return CodingOutcome(request.key, None, f"refusal ({category})", **meta)
        if response.stop_reason == "max_tokens":
            return CodingOutcome(request.key, None, "max_tokens reached", **meta)
        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            answer = CodedAnswer.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as err:
            return CodingOutcome(request.key, None, f"invalid output: {type(err).__name__}", **meta)
        return CodingOutcome(request.key, answer, None, **meta)


def _api_message(err: anthropic.APIStatusError) -> str:
    """The API's own explanation of a rejected request (parameter problems, not answer text)."""
    body = err.body if isinstance(err.body, dict) else {}
    message = (body.get("error") or {}).get("message") or str(err.message)
    return " ".join(message.split())[:300]


# --- cache & batch run -------------------------------------------------------------------------


class CodeCache:
    """Successful outcomes as JSON lines in the restricted interim zone. Errors are never cached."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, CodingOutcome]:
        if not self._path.is_file():
            return {}
        cached = {}
        for number, line in enumerate(self._path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                record = json.loads(line)
                answer = CodedAnswer.model_validate(record["answer"])
            except (json.JSONDecodeError, KeyError, ValidationError) as err:
                raise CacheError(
                    f"{self._path.name} line {number} is unreadable ({type(err).__name__}); "
                    "delete that line (or the file) to re-code those answers"
                ) from None  # no chained error: it would print respondent text
            cached[record["key"]] = CodingOutcome(record["key"], answer, None, record["model"])
        return cached

    def append(self, outcomes: Iterable[CodingOutcome]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            for outcome in outcomes:
                if outcome.ok:
                    record = {
                        "key": outcome.key,
                        "model": outcome.model,
                        "answer": outcome.answer.model_dump(),
                    }
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def code_requests(
    requests: Sequence[CodingRequest],
    coder: Coder,
    max_workers: int,
    on_result: Callable[[CodingOutcome], None] = lambda _: None,
) -> list[CodingOutcome]:
    """Run requests in parallel. `on_result` sees each outcome as soon as it arrives (on the main
    thread), so paid results persist even if the run is interrupted. Fatal errors cancel the queue.
    """
    unique = list({r.key: r for r in requests}.values())  # identical requests are sent once
    results = []
    pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        for future in as_completed([pool.submit(coder.code, r) for r in unique]):
            outcome = future.result()
            on_result(outcome)
            results.append(outcome)
    except BaseException:
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    pool.shutdown(wait=True)
    return results
