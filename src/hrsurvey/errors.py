"""Domain errors. Every one of them means "stop and look" — the pipeline never coerces silently."""


class HrSurveyError(Exception):
    """Base class for all pipeline errors."""


class ConfigError(HrSurveyError):
    """A config file is missing, malformed or internally inconsistent."""


class SchemaMismatchError(HrSurveyError):
    """The export does not match config/survey_schema.yaml (column count or header text changed)."""


class UnknownLabelError(HrSurveyError):
    """A scale cell holds a label that is not in config/scales.yaml — the form probably changed."""


class TimestampParseError(HrSurveyError):
    """A timestamp does not match the locale pattern configured in survey_schema.yaml."""


class WaveError(HrSurveyError):
    """The wave id is invalid, or cannot be derived unambiguously from the submissions."""


class MissingSaltError(HrSurveyError):
    """No secret salt is available for pseudonymous response IDs."""


class ManifestError(HrSurveyError):
    """The send manifest is missing, malformed or does not match the export."""


class MissingCredentialsError(HrSurveyError):
    """No usable Anthropic credentials for LLM coding."""
