"""Parse Google Forms timestamps whose format depends on the form owner's locale.

Example (Turkish locale): ``2026/10/15 6:43:35 ÖS GMT+3`` — ``ÖÖ`` = AM, ``ÖS`` = PM,
12-hour clock without zero padding, offset of the *owner's* timezone.

Error messages never contain the raw value: timestamps are a re-identification vector.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from hrsurvey.config import TimestampSpec
from hrsurvey.errors import TimestampParseError

_OFFSET = re.compile(r"^(?P<sign>[+-])(?P<hours>\d{1,2})(?::?(?P<minutes>\d{2}))?$")
_MAX_OFFSET_HOURS = 14


def _parse_offset(raw: str) -> timezone:
    match = _OFFSET.match(raw)
    if not match:
        raise TimestampParseError("unparseable UTC offset")
    hours, minutes = int(match["hours"]), int(match["minutes"] or 0)
    if hours > _MAX_OFFSET_HOURS or minutes >= 60:
        raise TimestampParseError("UTC offset out of range")
    sign = -1 if match["sign"] == "-" else 1
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def _to_24h(hour: int, ampm: str, spec: TimestampSpec) -> int:
    if not 1 <= hour <= 12:
        raise TimestampParseError("hour is not on a 12-hour clock")
    if ampm in spec.am_tokens:
        return hour % 12
    if ampm in spec.pm_tokens:
        return hour % 12 + 12
    raise TimestampParseError("unknown AM/PM token — check timestamp.am_tokens / pm_tokens")


def parse_timestamp(raw: str, spec: TimestampSpec) -> datetime:
    """Return a timezone-aware datetime in the form owner's offset.

    Raises TimestampParseError on any deviation from the configured pattern.
    """
    match = re.match(spec.regex, raw.strip())
    if not match:
        raise TimestampParseError("timestamp does not match the configured locale pattern")
    tz = _parse_offset(match["offset"])
    hour, minute, second = (int(part) for part in match["time"].split(":"))
    try:
        day = datetime.strptime(match["date"], spec.date_format)
        return day.replace(
            hour=_to_24h(hour, match["ampm"], spec), minute=minute, second=second, tzinfo=tz
        )
    except ValueError as err:
        raise TimestampParseError("invalid date or time value") from err
