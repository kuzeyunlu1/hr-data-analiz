from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hrsurvey.config import Config
from hrsurvey.errors import TimestampParseError
from hrsurvey.timestamps import parse_timestamp


@pytest.mark.parametrize(
    ("raw", "expected_utc"),
    [
        ("2026/10/15 6:43:35 ÖS GMT+3", datetime(2026, 10, 15, 15, 43, 35, tzinfo=UTC)),
        ("2026/10/15 12:58:40 ÖS GMT+3", datetime(2026, 10, 15, 9, 58, 40, tzinfo=UTC)),
        # 12 AM is midnight -> previous UTC day
        ("2026/10/14 12:05:00 ÖÖ GMT+3", datetime(2026, 10, 13, 21, 5, 0, tzinfo=UTC)),
        ("2026/10/15 1:00:00 ÖÖ GMT+3", datetime(2026, 10, 14, 22, 0, 0, tzinfo=UTC)),
        ("2026/10/15 11:59:59 ÖS GMT+3", datetime(2026, 10, 15, 20, 59, 59, tzinfo=UTC)),
        ("2026/10/15 9:00:00 AM GMT+02:00", datetime(2026, 10, 15, 7, 0, 0, tzinfo=UTC)),
        ("2026/10/15 9:00:00 PM GMT-5", datetime(2026, 10, 16, 2, 0, 0, tzinfo=UTC)),
    ],
)
def test_parses_owner_locale_to_utc(raw: str, expected_utc: datetime, config: Config) -> None:
    assert parse_timestamp(raw, config.survey.timestamp) == expected_utc


@pytest.mark.parametrize(
    "raw",
    [
        "2026/10/15 6:43:35 XX GMT+3",  # unknown AM/PM token
        "2026/10/15 13:00:00 ÖS GMT+3",  # not a 12-hour clock
        "15.10.2026 18:43:35",  # different locale entirely
        "2026/02/30 1:00:00 ÖÖ GMT+3",  # impossible date
        "2026/10/15 6:60:00 ÖS GMT+3",  # minute out of range
        "2026/10/15 6:00:00 ÖS GMT+24",  # offset out of range
        "2026/10/15 6:00:00 ÖS GMT+3:75",  # offset minutes out of range
        "",
    ],
)
def test_rejects_unexpected_formats(raw: str, config: Config) -> None:
    with pytest.raises(TimestampParseError) as err:
        parse_timestamp(raw, config.survey.timestamp)
    if raw:
        assert raw not in str(err.value)  # timestamps are a re-identification vector
