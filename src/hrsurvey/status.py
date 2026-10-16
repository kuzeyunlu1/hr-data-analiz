"""Response status taxonomy (docs/05-standardization.md#response-status-taxonomy)."""

from enum import StrEnum


class Status(StrEnum):
    SUBSTANTIVE = "SUBSTANTIVE"
    NO_ISSUE = "NO_ISSUE"
    NO_BASIS = "NO_BASIS"
    NOTHING_TO_ADD = "NOTHING_TO_ADD"
    PLACEHOLDER = "PLACEHOLDER"
    EMPTY = "EMPTY"
    NOT_ROUTED = "NOT_ROUTED"


# Statuses produced by free-text pattern matching, in the order they are checked.
PATTERN_STATUSES = (Status.NO_BASIS, Status.NOTHING_TO_ADD, Status.NO_ISSUE)
