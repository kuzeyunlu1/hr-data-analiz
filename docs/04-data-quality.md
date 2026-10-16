# 04 — Data Quality Assessment

Findings from profiling `data/raw/survey_export_2026-10-15.csv` (86 columns × 3 responses).
Every issue below has a concrete handling rule that the standardization layer
([05-standardization](05-standardization.md)) must implement.

> Examples are paraphrased or reduced to non-identifying fragments on purpose — see
> [08-privacy-and-ethics](08-privacy-and-ethics.md#quoting-rules).

## A. Export-format issues

| # | Issue | Evidence | Impact if ignored | Handling |
|---|---|---|---|---|
| A1 | **Multi-line bilingual headers.** EN question, newline, DE question. | 85 of 86 headers contain `\n`; some have extra blank lines. | Header-text matching is brittle; any wording edit breaks loading. | Map by **position** (`idx`) using the [data dictionary](03-data-dictionary.md). Store a header fingerprint (hash of normalized header row) per wave and fail if it changes unexpectedly. |
| A2 | **Grid items encoded in brackets** with inconsistent separators. | Q13 and Q18 use `[EN / DE]`; Q16 and Q17 use `[EN \| DE]`. Q16 and Q17 brackets differ in leading spaces (`[Pay …` vs `[ Pay …`). | Naive pairing of Q16↔Q17 by text fails. | Pair by factor key (see [03 › factor keys](03-data-dictionary.md#motivation-factor-keys-q16--q17)). |
| A3 | **Duplicate header text.** | idx 69 (technical) and idx 81 (back office) are both "Please identify the information most frequently missing." | pandas silently renames to `….1`; branch attribution can be swapped. | Positional mapping; unit test asserting both columns land in the correct branch. |
| A4 | Leading whitespace / missing spaces in headers. | idx 65, 73 start with a space; `5.1.What…` lacks a space. | Cosmetic for positional mapping, breaks text matching. | Normalize only for display. |
| A5 | **Branch questions are unnumbered.** | idx 65–85 have no question numbers. | Hard to reference in reports. | Assigned IDs `T1–T7`, `S1–S7`, `O1–O7`. |
| A6 | **Locale-dependent timestamp.** | Header `Zaman damgası` (TR). Values like `2026/10/15 6:43:35 ÖS GMT+3`. `ÖÖ` = AM, `ÖS` = PM, 12-hour clock, no zero padding. | Wrong hour parsing; the timezone is the **form owner's** (GMT+3), not the respondent's (Germany: CEST/GMT+2 until 25 Oct 2026, CET/GMT+1 after). | Parser driven by a locale config (`TS_GFORMS_TR`); fail loudly on unparseable values. Convert to UTC, derive `wave_id`, then **drop** the timestamp (re-identification risk). |
| A7 | **Bilingual answer labels** `EN / DE`. | `Agree / Stimme zu`; DE part can contain commas (`Nicht genügend Erfahrung, um dies zu beurteilen`); probability labels contain an em dash (`75% — Likely / Wahrscheinlich`). | Split heuristics on `/`, `,` or `—` break on edge cases. | **Exact-match lookup** on the full normalized label. Unknown label → hard error (it means the form changed). |
| A8 | **Q18 exported as bare digits** `1`–`5`, while the similar Q13 grid is exported as labels. | idx 48–57. | Scale anchors (which end is "agree") are not in the data. | Assume 1 = strongly disagree, 5 = strongly agree **only after confirming in the form**. Tracked as open question. |
| A9 | Q22 (`0`–`10`) and Q23 (`1`–`5`) are bare numbers. | idx 62, 63. | Anchors unknown. | Same as A8. |
| A10 | **Branch columns are empty strings** for respondents not routed there. | idx 65–85. | "Not routed" and "skipped" look identical. | Derive `branch` first; empty cells outside the respondent's branch → `NOT_ROUTED`, inside it → `EMPTY`. |
| A11 | Quoted multi-line cells. | Some free-text answers contain line breaks. | Line-based reading corrupts rows. | Use a real CSV parser (`csv` / pandas with default quoting). UTF-8, no BOM, LF line endings. |
| A12 | Apostrophe variants. | `´` (U+00B4), `’` (U+2019), `'` (U+0027) all appear. | String matching for non-answers fails. | Unicode NFC + map all variants to `'` in the normalized text field. |

## B. Response-content issues

| # | Issue | Evidence (paraphrased) | Handling |
|---|---|---|---|
| B1 | **Non-substantive free text.** | "no customer contact", "-", "I don't know?", "I'm not in a position to answer that", "I couldn't think of one". | Classify into the [response status taxonomy](05-standardization.md#response-status-taxonomy) (`NO_BASIS`, `PLACEHOLDER`, `NOTHING_TO_ADD`). Rule-based patterns first, LLM fallback. |
| B2 | **Positive nulls are data, not missing.** | "There is no obstacle.", "No change is necessary.", "The responsibilities are clear." | Status `NO_ISSUE`. Counted in denominators and reported ("x of n see no obstacle"). |
| B3 | **Structural N/A hidden in a scale answer.** | In Q4 "Not enough experience to judge" was chosen by respondents whose Q4.1 explains they work alone in their department. | Scale status `NO_BASIS`; the text reveals a *single-person role*. Report only as an aggregate share — never as a respondent attribute (it is highly identifying). |
| B4 | **Relative references.** | Q18.1 "the first one" — but "above" can mean the Q16/17 factor list *or* the Q18 statements; the justification points to Q18a (disagreements). Another respondent answered with a Q16/17 factor. | Resolve to a canonical item with the coder, store `resolved_target`, `resolution_method=inferred`, `confidence`. Instrument fix for wave 2 in [02](02-survey-instrument.md#known-instrument-weaknesses). |
| B5 | **Irony / sarcasm.** | Answer to "What do you enjoy most?" names a trivial incidental event (cake on someone's birthday) — literal sentiment positive, intended meaning negative; the same response's scale answers are strongly negative. | Coder outputs an explicit `sarcasm` field. Cross-check text valence against the respondent's scale profile; disagreements go to human review. Never use an off-the-shelf sentiment score alone. |
| B6 | **Internal inconsistency.** | Near-top scores on most climate items but the lowest possible "would recommend" (Q18j); top-box pay satisfaction while the single top suggestion is "more money". | `qflag_inconsistent`. Possible causes: genuine nuance, reversed reading of the unlabeled Q18 scale (A8), careless responding. **Never auto-correct.** Run sensitivity analysis with/without flagged responses. |
| B7 | Straight-lining risk. | Grids of 10–14 items (Q16, Q17, Q18). | `qflag_straightline_<grid>` when within-grid SD = 0 across ≥ 10 items. Flag, don't drop. |
| B8 | **Code-switching carries meaning.** | An English answer contains a quoted German phrase ("bekanntes Thema" ≈ "known issue") used as organizational jargon for problems everybody knows about but nobody owns. | Translation keeps the original phrase and adds a gloss. Candidate codebook signal for responsibility diffusion. |
| B9 | Spelling errors, mostly in technical vocabulary. | e.g. "Secuirty". | Normalize in `text_en`, keep raw. **Do not** use spelling/style as a feature (stylometry = re-identification). |
| B10 | **Multi-idea answers.** | One Q12 answer contains: unrealistic timelines, repeated direction changes, need for continuity, call for long-term strategy. | Segment into idea units before coding; each unit gets its own code. |
| B11 | **Premise rejection.** | Q3 asks for a 30-day first step; an answer states nothing is achievable in 30 days. | Code the stance (`premise_rejected`) — it signals capacity limits or cynicism and is informative. |
| B12 | Item non-response in core block. | Q2, Q18.1 and T3 left empty by individual respondents. | Status `EMPTY`; never impute text. For indices see the minimum-items rule in [06](06-pattern-detection.md#scoring-rules). |
| B13 | Speeding cannot be detected. | Google Forms exports only the submit time — no start time. | Not addressable with this export. Document as limitation. |

## C. Instrument-design issues

Design-level problems (double-barreled items, mixed scale formats, missing "I work alone" option,
ambiguous Q18.1, no routing variable) are listed in
[02-survey-instrument › Known instrument weaknesses](02-survey-instrument.md#known-instrument-weaknesses),
because they must be fixed in the form, not in the pipeline.

## Quality flags (summary)

| Flag | Level | Trigger | Effect |
|---|---|---|---|
| `qflag_inconsistent` | response | \|`q18j_pomp` − mean(other Q18 items' pomp)\| ≥ `quality.inconsistency_gap` (default 50) | Reported; sensitivity analysis |
| `qflag_straightline_<grid>` | response | within-grid SD = 0 over ≥ 10 items | Reported; sensitivity analysis |
| `qflag_low_completion` | response | `core_completion` (closed core items answered) < `min_core_completion` (default 0.5) | Excluded from indices, kept for text |
| `qflag_duplicate` | response | All answers identical to an earlier submission (timestamp ignored) and ≥ `duplicate_min_answered_cells` (default 10) non-empty cells — the later copy is flagged | Reported; exclude the copy from counts |
| `qflag_multiple_branches` | response | Answers in more than one branch block (routing should prevent this) | Reported + CLI warning; all branches treated as routed |
| `qflag_sarcasm` | text segment | coder `sarcasm = true` | Valence inverted only after human confirmation |
| `qflag_unresolved_reference` | text segment | relative reference with confidence < 0.7 | Human review queue |

All thresholds live in [`config/quality.yaml`](../config/quality.yaml), not in code.
Response-level flags are implemented in `src/hrsurvey/quality.py`; the text-segment flags arrive with Phase 2.
