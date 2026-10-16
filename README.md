# HR Survey Pattern Analysis

Standardization and pattern detection for the anonymous **Employee Experience, Motivation &
Business Improvement** survey (EN/DE, Google Forms) run as part of a two-month internship project.

The system turns a raw survey export — 86 columns of scale and free-text answers in two
languages — into a clean dataset, then detects recurring patterns:

- **Leadership & management friction** — responsibility diffusion, slow or avoided decisions,
  recognition gaps, unstable priorities, trust deficits, low psychological safety
- **Operational inefficiency** — information chasing, handover gaps, avoidable rework,
  capacity bottlenecks, single-person roles
- **Business opportunities** — unmet customer needs, cross-sell potential, portfolio gaps

> **Patterns, not people.** Respondents were promised anonymity and that individuals would not be
> evaluated. All outputs are group-level (n ≥ k), triangulated, and treated as hypotheses for
> follow-up — never as verdicts on a person. See [docs/08-privacy-and-ethics.md](docs/08-privacy-and-ethics.md).

## Status

| | |
|---|---|
| Phase | 0 docs ✅ · 1 standardization ✅ · 2 text pipeline ✅ (pilot coding pending API key + approval) · 3 analysis next |
| Data | Pilot export 2026-10-15, **N = 3**, survey still open |
| Next | Phase 3: indices, gaps, VIE, rule engine ([roadmap](docs/09-architecture.md#roadmap)) |

## Quickstart

```bash
uv sync
```

```bash
uv run hrsurvey init-salt
```

```bash
uv run hrsurvey standardize data/raw/survey_export_2026-10-15.csv
```

```bash
uv run pytest
```

Free-text coding (Phase 2) — the analyst approves everything that leaves the machine:

```bash
uv run hrsurvey redact data/raw/survey_export_2026-10-15.csv
```

Open `data/interim/2026-10/llm_manifest.csv`, compare `text_original` with `text_redacted`, fix
`text_redacted` where needed and set `approved` to `yes`. Put `ANTHROPIC_API_KEY=…` in `.env`. Then:

```bash
uv run hrsurvey code-text data/raw/survey_export_2026-10-15.csv
```

Review `data/interim/2026-10/review_segments.csv` (`review_status`: accepted / edited / rejected), then:

```bash
uv run hrsurvey review-import --wave 2026-10
```

`init-salt` runs once and writes a secret to `.env` (gitignored) — it keeps response IDs stable.
`standardize` writes `data/processed/<wave>/respondents.parquet` and `answers_long.parquet`;
`text-prep` writes `data/interim/<wave>/text_answers.parquet`. Commands: [docs/09 › Pipeline](docs/09-architecture.md#pipeline).

## How it works

```
Google Forms CSV
  → validate (positional schema, header fingerprint)
  → standardize (scale labels → codes → 0–100 scores, 7 response statuses, branch derivation)
  → text pipeline (redact → translate → segment → LLM-assisted coding → human review)
  → analysis (construct indices, importance–satisfaction gaps, expectancy/VIE, theme analytics)
  → rule engine (triangulated patterns, k-anonymity suppression)
  → reports (findings, improvement backlog, customer insights, interview probes)
```

## Documentation

| # | Document | What's inside |
|---|---|---|
| 01 | [Project context](docs/01-project-context.md) | Purpose, promises to respondents, organization, scope |
| 02 | [Survey instrument](docs/02-survey-instrument.md) | Blocks, branching, scales, embedded theories, leadership signal map, instrument weaknesses |
| 03 | [Data dictionary](docs/03-data-dictionary.md) | All 86 columns → canonical `var_id`, scale, construct |
| 04 | [Data quality](docs/04-data-quality.md) | Export-format and response-content issues with handling rules |
| 05 | [Standardization spec](docs/05-standardization.md) | Pipeline stages, scale catalogue, response statuses, output schemas |
| 06 | [Pattern detection](docs/06-pattern-detection.md) | Indices, LFI/OFI, gap analysis, VIE, rule catalogue, confidence |
| 07 | [Text codebook](docs/07-text-codebook.md) | Themes, locus, valence, sarcasm, LLM coding protocol |
| 08 | [Privacy & ethics](docs/08-privacy-and-ethics.md) | k-anonymity, suppression, quoting rules, data zones, legal checkpoints |
| 09 | [Architecture](docs/09-architecture.md) | Stack, repo layout, pipeline, testing, roadmap |
| 10 | [Pilot learnings](docs/10-pilot-learnings.md) | What N = 3 taught us, emerging themes, interview probes, open questions |
| – | [DECISIONS.md](DECISIONS.md) | Decision log |

## Repository layout

```
.
├── README.md · CLAUDE.md · DECISIONS.md
├── docs/            # documentation
├── data/            # gitignored — raw / interim / processed (see data/README.md)
├── config/          # YAML: schema, scales, non-answer patterns, quality, scoring
├── src/hrsurvey/    # pipeline code (Phase 1: ingest → standardize → quality → text status)
├── tests/           # pytest, synthetic fixtures only
└── reports/         # planned, gitignored — aggregated outputs after review
```

## Data handling in one minute

- Raw exports go in `data/raw/` and **never** leave the analyst's machine or enter git.
- Nothing is reported for a group with fewer than **k = 5** respondents.
- Text is redacted before any external processing.
- Timestamps are dropped after ingestion.
- Every report passes the [pre-release checklist](docs/08-privacy-and-ethics.md#pre-release-checklist-every-report).

## Open questions

Tracked in [docs/10-pilot-learnings.md › Open questions](docs/10-pilot-learnings.md#open-questions-for-the-form-owner):
routing logic, full scale labels, Q18/Q22/Q23 anchors, headcount per area, survey timeline,
works council / LLM approval.
