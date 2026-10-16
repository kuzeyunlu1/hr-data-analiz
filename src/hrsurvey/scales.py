"""Stage 4: strict label -> code mapping (docs/05-standardization.md#scale-catalogue)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from hrsurvey.config import ScaleSpec
from hrsurvey.errors import UnknownLabelError
from hrsurvey.status import Status

_WHITESPACE = re.compile(r"\s+")
_INTEGER = re.compile(r"^-?\d+$")


def normalize_label(raw: str) -> str:
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", raw)).strip()


@dataclass(frozen=True)
class MappedValue:
    status: Status
    code: int | None = None
    value: float | None = None
    unverified: bool = False


@dataclass(frozen=True)
class _Lookup:
    spec: ScaleSpec
    observed: Mapping[str, int]
    expected: Mapping[str, int]
    not_applicable: frozenset[str]


class ScaleMapper:
    """Maps raw cells of every configured scale. Unknown labels raise — never guessed."""

    def __init__(self, scales: Mapping[str, ScaleSpec]) -> None:
        self._lookups = MappingProxyType(
            {
                scale_id: _Lookup(
                    spec=spec,
                    observed=MappingProxyType(
                        {normalize_label(k): v for k, v in spec.labels.items()}
                    ),
                    expected=MappingProxyType(
                        {normalize_label(k): v for k, v in spec.expected_labels.items()}
                    ),
                    not_applicable=frozenset(normalize_label(k) for k in spec.na_labels),
                )
                for scale_id, spec in scales.items()
            }
        )

    def map(self, scale_id: str, raw: str) -> MappedValue:
        lookup = self._lookups[scale_id]
        text = normalize_label(raw)
        if not text:
            return MappedValue(Status.EMPTY)
        if text in lookup.not_applicable:
            return MappedValue(Status.NO_BASIS)
        if lookup.spec.kind == "numeric":
            return self._numeric(scale_id, lookup.spec, text)
        if text in lookup.observed:
            return self._mapped(lookup.spec, lookup.observed[text], unverified=False)
        if text in lookup.expected:
            return self._mapped(lookup.spec, lookup.expected[text], unverified=True)
        known = sorted([*lookup.observed, *lookup.expected, *lookup.not_applicable])
        raise UnknownLabelError(
            f"{scale_id}: unknown label {text!r}. Known labels: {known}. "
            "If the form changed, add the label to config/scales.yaml."
        )

    @staticmethod
    def _mapped(spec: ScaleSpec, code: int, *, unverified: bool) -> MappedValue:
        return MappedValue(
            status=Status.SUBSTANTIVE,
            code=code,
            value=spec.values.get(code, float(code)),
            unverified=unverified,
        )

    def _numeric(self, scale_id: str, spec: ScaleSpec, text: str) -> MappedValue:
        if not _INTEGER.match(text) or not spec.min <= int(text) <= spec.max:
            raise UnknownLabelError(
                f"{scale_id}: {text!r} is not an integer in [{spec.min}, {spec.max}]"
            )
        return self._mapped(spec, int(text), unverified=False)
