"""Stage 7a: local redaction of personal data — runs before any text can leave the machine.

regex patterns (e-mail, URL, IBAN, phone, titled names) -> spaCy NER (EN and/or DE) -> allowlist.
Over-redaction is accepted: every row is reviewed by the analyst in the send manifest.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType

import spacy
from lingua import Language, LanguageDetectorBuilder

from hrsurvey.text.settings import RedactionConfig

LANGUAGE_CODES = {Language.ENGLISH: "en", Language.GERMAN: "de"}
MIXED = "mixed"
_PLACEHOLDER = re.compile(r"\[[A-Z]+\]")


@dataclass(frozen=True)
class Redaction:
    text: str
    language: str  # en | de | mixed
    counts: Mapping[str, int] = field(default_factory=dict)  # placeholder -> occurrences

    @property
    def summary(self) -> str:
        return ", ".join(f"{tag}x{n}" for tag, n in sorted(self.counts.items()))


class Redactor:
    """Stateless after construction; spaCy models load lazily on first use."""

    def __init__(self, cfg: RedactionConfig) -> None:
        self._cfg = cfg
        self._patterns = tuple(
            (rule, re.compile(rule.regex), re.compile(rule.exclude_regex or r"(?!)"))
            for rule in cfg.patterns
        )
        self._allow = frozenset(term.casefold() for term in cfg.allowlist)
        self._detector = LanguageDetectorBuilder.from_languages(*LANGUAGE_CODES).build()

    @cached_property
    def _models(self) -> Mapping[str, spacy.language.Language]:
        models = {}
        for lang, name in self._cfg.spacy_models.items():
            nlp = spacy.load(name)
            nlp.select_pipes(enable=[p for p in ("tok2vec", "ner") if p in nlp.pipe_names])
            models[lang] = nlp
        return MappingProxyType(models)

    def detect_language(self, text: str) -> str:
        values = self._detector.compute_language_confidence_values(text)
        if not values or values[0].value < self._cfg.min_language_confidence:
            return MIXED
        return LANGUAGE_CODES[values[0].language]

    def _apply_patterns(self, text: str, counts: Counter[str]) -> str:
        for rule, pattern, exclude in self._patterns:

            def replace(match: re.Match[str], rule=rule, exclude=exclude) -> str:
                found = match.group()
                if sum(ch.isdigit() for ch in found) < rule.min_digits or exclude.fullmatch(found):
                    return found
                counts[rule.placeholder] += 1
                return rule.placeholder

            text = pattern.sub(replace, text)
        return text

    def _entity_spans(self, text: str, language: str) -> list[tuple[int, int, str]]:
        langs = (language,) if language in self._models else tuple(self._models)
        protected = [(m.start(), m.end()) for m in _PLACEHOLDER.finditer(text)]
        spans = []
        for lang in langs:
            for ent in self._models[lang](text).ents:
                placeholder = self._cfg.entities.get(ent.label_)
                surface = ent.text.strip(" .,;:!?\"'()")
                if placeholder is None or surface.casefold() in self._allow:
                    continue
                # never re-tag our own placeholders (spaCy splits "[IBAN]" into [, IBAN, ]),
                # but still redact the rest of an entity that overlaps one ("[PERSON]. Müller")
                spans += [
                    (start, end, placeholder)
                    for start, end in _subtract(ent.start_char, ent.end_char, protected)
                    if any(ch.isalpha() for ch in text[start:end])
                ]
        return _merge_overlaps(spans)

    def redact(self, text: str) -> Redaction:
        counts: Counter[str] = Counter()
        patterned = self._apply_patterns(text, counts)
        language = self.detect_language(patterned)
        result = patterned
        for start, end, placeholder in reversed(self._entity_spans(patterned, language)):
            result = result[:start] + placeholder + result[end:]
            counts[placeholder] += 1
        return Redaction(result, language, MappingProxyType(dict(counts)))


def _subtract(start: int, end: int, holes: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Pieces of [start, end) not covered by any hole, trimmed of surrounding punctuation."""
    pieces, cursor = [], start
    for hole_start, hole_end in sorted(holes):
        if hole_end <= cursor or hole_start >= end:
            continue
        if hole_start > cursor:
            pieces.append((cursor, hole_start))
        cursor = max(cursor, hole_end)
    if cursor < end:
        pieces.append((cursor, end))
    return pieces


def _merge_overlaps(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Union of entity spans from several models; overlapping spans collapse to the widest."""
    merged: list[tuple[int, int, str]] = []
    for start, end, tag in sorted(spans, key=lambda s: (s[0], -s[1])):
        if merged and start < merged[-1][1]:
            prev_start, prev_end, prev_tag = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end), prev_tag)
        else:
            merged.append((start, end, tag))
    return merged
