# CLAUDE.md — HR Survey Pattern Analysis

Analysis pipeline for an anonymous bilingual (EN/DE) employee survey. Start with `README.md`;
the specs live in `docs/01`–`docs/10`, decisions in `DECISIONS.md`.

## Hard rules

- **Patterns, not people.** Never identify, score, rank or profile an individual respondent or
  manager. Never attempt re-identification (timestamps, writing style, branch + content linkage).
  See `docs/08-privacy-and-ethics.md`.
- **Raw data stays local.** `data/` and `reports/` are gitignored. Never commit, paste into docs,
  or send respondent text anywhere unredacted. Docs use paraphrased, unlinked examples only.
- **k-anonymity.** Nothing is reported for groups/items with fewer than `privacy.k` (default 5)
  respondents; apply complementary suppression.
- **Config over constants.** Labels, weights, thresholds, k, model IDs go in `config/*.yaml`.
- **Position is the contract.** Columns are mapped by index per `docs/03-data-dictionary.md`.
  Unknown labels or header changes must raise, never be coerced.
- **Tests use synthetic fixtures only.**

## Commands

- `uv run pytest` — tests (synthetic data only)
- `uv run ruff check src tests && uv run ruff format src tests`
- `uv run hrsurvey schema-check|standardize|text-prep|redact|code-text <csv>` / `review-import --wave W` / `init-salt`
- Never set `approved=yes` in the send manifest yourself and never run `code-text` without the user's go-ahead: approval of what leaves the machine is the analyst's.
- Never print respondent text in tool output; inspect real data via aggregates (counts per status/var).

## When the form changes

Update together: `docs/03-data-dictionary.md`, `config/survey_schema.yaml`, `config/scales.yaml`,
and add a `DECISIONS.md` entry if analysis logic changes.

## Conventions

- Variable IDs: `q<nn>_<topic>`, grid items `q16_imp_<factor>` / `q17_sat_<factor>` / `q18<letter>_<topic>`,
  branches `tec<n>_`, `sal<n>_`, `bo<n>_`; free text ends in `_txt`.
- Scores: `pomp` 0–100, higher = healthier; composites LFI/OFI higher = more friction.
- Text codes: `FAMILY.CODE` from `docs/07-text-codebook.md`; bump `codebook_version` on change.
- Documentation in English; conversation with the user in Turkish.
