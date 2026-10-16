from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from hrsurvey.config import Config, load_config
from hrsurvey.errors import ConfigError

from conftest import CONFIG_DIR, ROOT

DICTIONARY_ROW = re.compile(
    r"^\| (?P<col>[A-Z]+) \| (?P<idx>\d+) \| `(?P<var_id>[a-z0-9_]+)` \| (?P<q_no>[^|]+) \| "
    r"(?P<block>[^|]+) \| (?P<type>[^|]+) \| (?P<scale>[^|]+) \| (?P<pol>[^|]*) \|"
)


def test_config_loads_expected_shape(config: Config) -> None:
    assert len(config.survey.columns) == 86
    assert len(config.survey.closed_columns()) == 57
    assert len(config.survey.text_columns()) == 28


def test_schema_matches_data_dictionary_doc(config: Config) -> None:
    """docs/03-data-dictionary.md and config/survey_schema.yaml must never drift apart."""
    doc = (ROOT / "docs" / "03-data-dictionary.md").read_text(encoding="utf-8")
    documented = {}
    for line in doc.splitlines():
        match = DICTIONARY_ROW.match(line)
        if match:
            scale = match["scale"].strip()
            documented[int(match["idx"])] = (
                match["var_id"],
                match["q_no"].strip(),
                match["block"].strip(),
                match["type"].strip(),
                None if scale == "-" or match["type"].strip() in ("text", "timestamp") else scale,
                match["pol"].strip() or None,
            )
    configured = {
        c.idx: (c.var_id, c.q_no, c.block, c.type, c.scale_id, c.polarity)
        for c in config.survey.columns
    }
    assert documented == configured


def test_q16_and_q17_cover_the_same_factors_in_order(config: Config) -> None:
    importance = [
        c.var_id.removeprefix("q16_imp_")
        for c in config.survey.columns
        if c.var_id.startswith("q16_imp_")
    ]
    satisfaction = [
        c.var_id.removeprefix("q17_sat_")
        for c in config.survey.columns
        if c.var_id.startswith("q17_sat_")
    ]
    assert len(importance) == 14
    assert importance == satisfaction


def test_label_codes_are_unique_within_each_scale(config: Config) -> None:
    for scale_id, spec in config.scales.items():
        codes = list(spec.labels.values()) + list(spec.expected_labels.values())
        assert len(codes) == len(set(codes)), scale_id


def _copy_config(tmp_path: Path) -> Path:
    target = tmp_path / "config"
    shutil.copytree(CONFIG_DIR, target)
    return target


def test_missing_scale_definition_raises(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    scales = yaml.safe_load((config_dir / "scales.yaml").read_text(encoding="utf-8"))
    del scales["SAT5"]
    (config_dir / "scales.yaml").write_text(yaml.safe_dump(scales, allow_unicode=True))
    with pytest.raises(ConfigError, match="SAT5"):
        load_config(config_dir)


def test_missing_config_file_raises(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    (config_dir / "quality.yaml").unlink()
    with pytest.raises(ConfigError, match="quality.yaml"):
        load_config(config_dir)


def test_label_code_outside_range_raises(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    scales = yaml.safe_load((config_dir / "scales.yaml").read_text(encoding="utf-8"))
    scales["SAT5"]["labels"]["Satisfied / Zufrieden"] = 9
    (config_dir / "scales.yaml").write_text(yaml.safe_dump(scales, allow_unicode=True))
    with pytest.raises(ConfigError, match="outside"):
        load_config(config_dir)


def _mutate_yaml(config_dir: Path, name: str, mutate) -> None:
    path = config_dir / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "mutate", "message"),
    [
        (
            "scoring.yaml",
            lambda d: d["favorability_overrides"].update({"NUM0-10": d["favorability_default"]}),
            "unknown scales",
        ),
        ("scales.yaml", lambda d: d["PROB5"]["values"].pop(5), "every code"),
        (
            "quality.yaml",
            lambda d: d["inconsistency"].update(comparison_pattern="^q18[a-j]_"),
            "matches the target",
        ),
        (
            "quality.yaml",
            lambda d: d["inconsistency"].update(comparison_pattern="^q99_"),
            "too few",
        ),
        ("quality.yaml", lambda d: d["straightline"]["grids"].update(q16="^q16_typo_"), "q16"),
        (
            "quality.yaml",
            lambda d: d["inconsistency"].update(target_item="q24_top_suggestion_txt"),
            "not a closed item",
        ),
    ],
)
def test_config_typos_fail_loudly(tmp_path: Path, name: str, mutate, message: str) -> None:
    config_dir = _copy_config(tmp_path)
    _mutate_yaml(config_dir, name, mutate)
    with pytest.raises(ConfigError, match=message):
        load_config(config_dir)
