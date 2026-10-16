from __future__ import annotations

import pytest

from hrsurvey.config import Config
from hrsurvey.errors import UnknownLabelError
from hrsurvey.scales import ScaleMapper
from hrsurvey.status import Status


@pytest.fixture(scope="module")
def mapper(config: Config) -> ScaleMapper:
    return ScaleMapper(config.scales)


def test_observed_label_maps_to_code(mapper: ScaleMapper) -> None:
    mapped = mapper.map("SAT5", "Satisfied / Zufrieden")
    assert (mapped.status, mapped.code, mapped.value, mapped.unverified) == (
        Status.SUBSTANTIVE,
        4,
        4.0,
        False,
    )


def test_expected_label_maps_but_is_marked_unverified(mapper: ScaleMapper) -> None:
    mapped = mapper.map("COMPLETE5", "Complete / Vollständig")
    assert mapped.code == 4
    assert mapped.unverified is True


def test_na_option_becomes_no_basis(mapper: ScaleMapper) -> None:
    mapped = mapper.map("AGREE5_LABELED", "Unable to judge / Kann ich nicht beurteilen")
    assert mapped.status == Status.NO_BASIS
    assert mapped.code is None


@pytest.mark.parametrize("raw", ["", "   ", "\n"])
def test_blank_cells_are_empty(mapper: ScaleMapper, raw: str) -> None:
    assert mapper.map("SAT5", raw).status == Status.EMPTY


def test_internal_whitespace_is_normalized(mapper: ScaleMapper) -> None:
    assert mapper.map("SAT5", "  Very   satisfied /\nSehr zufrieden ").code == 5


def test_unknown_label_stops_the_pipeline(mapper: ScaleMapper) -> None:
    with pytest.raises(UnknownLabelError, match="SAT5"):
        mapper.map("SAT5", "Kind of okay / Geht so")


def test_probability_and_valence_values(mapper: ScaleMapper) -> None:
    assert mapper.map("PROB5", "25% — Unlikely / Unwahrscheinlich").value == 0.25
    neutral = "Neither desirable nor undesirable / Weder erwünscht noch unerwünscht"
    assert mapper.map("DESIRABILITY5", neutral).value == 0.0
    assert mapper.map("DESIRABILITY5", "Very desirable / Sehr erwünscht").value == 1.0


@pytest.mark.parametrize(
    ("scale_id", "raw", "code"),
    [("NUM0_10", "0", 0), ("NUM1_5", " 4 ", 4), ("AGREE5_NUMERIC", "5", 5)],
)
def test_numeric_scales_parse_integers(mapper: ScaleMapper, scale_id: str, raw: str, code: int):
    assert mapper.map(scale_id, raw).code == code


@pytest.mark.parametrize(
    ("scale_id", "raw"),
    [("NUM0_10", "11"), ("NUM1_5", "0"), ("NUM0_10", "7.5"), ("AGREE5_NUMERIC", "Agree")],
)
def test_numeric_scales_reject_out_of_range(mapper: ScaleMapper, scale_id: str, raw: str) -> None:
    with pytest.raises(UnknownLabelError):
        mapper.map(scale_id, raw)


def test_every_configured_label_round_trips(config: Config, mapper: ScaleMapper) -> None:
    for scale_id, spec in config.scales.items():
        for label, code in {**spec.labels, **spec.expected_labels}.items():
            assert mapper.map(scale_id, label).code == code, (scale_id, label)
        for label in spec.na_labels:
            assert mapper.map(scale_id, label).status == Status.NO_BASIS
