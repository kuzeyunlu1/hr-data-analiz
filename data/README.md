# data/

Restricted zone — everything in here except this file is gitignored.

| Folder | Contents |
|---|---|
| `raw/` | Original Google Forms exports, named `survey_export_<YYYY-MM-DD>.csv`. Never edited. |
| `interim/` | Normalized tables that still contain raw text. |
| `processed/` | Redacted, standardized, coded Parquet tables (`respondents`, `answers_long`, `text_segments`). |

Rules: no copies outside this machine, no e-mail/chat sharing, delete at project end.
See [docs/08-privacy-and-ethics.md](../docs/08-privacy-and-ethics.md#data-zones).
