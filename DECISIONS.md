# Decision Log

Every significant design decision, newest last. Decisions are never deleted: a retired decision
gets a 🔄 **superseded** marker with date and reason, and the replacement gets its own entry.

Status legend: ✅ active · 🔄 superseded · ⏳ pending confirmation

---

### D-001 · Pattern-level analysis only — no individual identification
- **Date:** 2026-10-15 · **Status:** ✅
- **Context:** The survey promised anonymity and stated it does not evaluate individuals. The project
  goal includes detecting problems caused by people, especially managers.
- **Decision:** The system detects leadership/management and process **patterns at group level**
  (n ≥ k), triangulated across scale items and coded text. It never identifies, scores or ranks
  individuals, and never attempts re-identification.
- **Consequences:** Leadership findings are organization- or branch-level until a team variable
  exists (and is announced to respondents). See [08](docs/08-privacy-and-ethics.md).

### D-002 · Positional column mapping with header fingerprint
- **Date:** 2026-10-15 · **Status:** ✅
- **Context:** Headers are multi-line, bilingual, contain a duplicate and inconsistent whitespace.
- **Decision:** Map columns by index via the data dictionary; store a header fingerprint per wave and fail on mismatch.
- **Consequences:** Any form edit requires updating `docs/03-data-dictionary.md` and `config/survey_schema.yaml`.

### D-003 · English as canonical analysis language
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** All text is translated to English for coding; originals are kept in the restricted zone;
  internal German jargon is preserved with a gloss. Documentation is written in English.

### D-004 · Configuration over constants
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** Scale labels, construct weights, rule thresholds, quality thresholds, k and model IDs live
  in YAML under `config/`. Changing them never requires a code change.

### D-005 · Minimum group size k = 5 with complementary suppression
- **Date:** 2026-10-15 · **Status:** ⏳ (confirm against headcount per area)
- **Decision:** Nothing is reported for groups (or items) with fewer than 5 respondents; suppressing one
  subgroup forces suppression of another so it can't be derived by subtraction.

### D-006 · Long-format Parquet storage, DuckDB for queries
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** `respondents`, `answers_long`, `text_segments` as Parquet; DuckDB for ad-hoc SQL. No database server.

### D-007 · Hybrid codebook, LLM-assisted coding, human-validated
- **Date:** 2026-10-15 · **Status:** ✅ company approval for sending redacted text reported by the analyst on 2026-10-15
- **Decision:** Deductive starter codebook + inductive extension; LLM proposes codes on **redacted** text,
  a human reviews every segment while N is small; κ-based sampling later.
- **Consequences:** Fallback to local model or manual coding if external processing is not approved.

### D-008 · Timestamps dropped after wave derivation
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** The submission timestamp is converted to `wave_id` and removed from all processed tables.

### D-009 · Triangulation required for findings
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** A finding needs ≥ 2 independent signals and n ≥ k. Single-respondent themes become
  interview probes, never findings.

### D-010 · Response-status taxonomy instead of a single "missing"
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** Seven statuses (`SUBSTANTIVE`, `NO_ISSUE`, `NO_BASIS`, `NOTHING_TO_ADD`, `PLACEHOLDER`,
  `EMPTY`, `NOT_ROUTED`). "No obstacle" counts as a positive answer, not as missing.

### D-011 · Stable pseudonymous response IDs via keyed hash
- **Date:** 2026-10-15 · **Status:** ✅
- **Context:** Phase 2 needs human-review CSVs that re-join to responses across re-runs and growing
  exports. Random UUIDs change on every run.
- **Decision:** `response_id = "r_" + HMAC-SHA256(salt, full raw row)[:16]`. The salt lives only in
  `.env` (`HRSURVEY_ID_SALT`, created by `hrsurvey init-salt`). Byte-identical rows get an occurrence
  counter so IDs stay unique.
- **Consequences:** 🔄 Supersedes the "random UUID v4" definition originally written in
  `docs/03-data-dictionary.md` (2026-10-15). Losing the salt only means IDs change on the next run;
  leaking it does not reveal identities (the attacker would already need the raw export).

### D-012 · Unverified scale labels map, but are reported
- **Date:** 2026-10-15 · **Status:** ✅
- **Context:** Several scale options have not appeared in any export yet, so their exact wording is unknown.
- **Decision:** `config/scales.yaml` separates `labels` (observed) from `expected_labels` (guessed).
  Expected labels map, set `label_unverified = true` and print a warning; any other unknown label stops
  the pipeline.
- **Consequences:** New exports rarely break; every guessed label is confirmed before it is trusted.

### D-013 · Completion measured on closed core items only
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** `core_completion` = share of closed core items (blocks B–H) with status ≠ `EMPTY`.
  "Can't judge" counts as answered. Open questions are excluded because skipping them is normal and
  indices are built from closed items only.

### D-014 · Output tables never reveal submission order
- **Date:** 2026-10-15 · **Status:** ✅
- **Context:** Code review: dropping the timestamp is not enough — Google Forms exports rows in
  submission order, so row order alone tells who answered first.
- **Decision:** `respondents`, `answers_long` and `text_answers` are sorted by `response_id` (a keyed
  hash, so the order is meaningless). Duplicate detection uses the timestamps inside ingest only.
  Error messages name the data row, never the timestamp value.

### D-015 · Wave = owner-local month; explicit `--wave` when ambiguous
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** Without `--wave`, the wave is the month of the submissions in the form owner's
  timezone. If submissions span more than one month, the run stops and asks for `--wave`. Wave ids
  may only contain letters, digits, `-` and `_`, and outputs must stay inside `data/`.

### D-016 · The send manifest is the only path to the LLM
- **Date:** 2026-10-15 · **Status:** ✅
- **Decision:** `hrsurvey redact` writes `data/interim/<wave>/llm_manifest.csv` (original + redacted
  text side by side). Only rows the analyst marks `approved=yes` are sent, exactly as shown in
  `text_redacted`. One request per answer — never several answers of one person in one request —
  carrying only: question text, answer status, a coarse engagement band and the redacted answer.
  Translation, segmentation and coding happen in that single call.
- **Consequences:** Nothing leaves the machine by accident; NER false positives (typos, German
  jargon) are fixed by hand before sending. Respondents with `qflag_inconsistent` get band `unknown`.
- **Re-runs (after code review, 2026-10-15):** the manifest keeps `text_auto` (rule output) next to
  `text_redacted`. An analyst edit and its approval survive re-runs; an unedited row whose rule
  output changes gets the new text and loses its approval. Review decisions on answers that changed
  move to `review_stale.csv` and are never imported. Results are cached as they arrive; a bad key,
  missing access or a wrong model name stops the run at once.

### D-017 · Coding model and request settings
- **Date:** 2026-10-15 · **Status:** 🔄 superseded by D-018 (2026-10-15) for the model choice; other settings still apply
- **Decision:** `claude-opus-5-5`, effort `medium`, JSON-schema structured output with the codebook
  as enums, server-side `fallbacks: "default"` on refusals, prompt caching of the codebook prompt.
  Results are cached per (codebook version, model, effort, question, answer text), so re-runs only
  send what changed and identical answers are coded once. All in `config/llm.yaml`.

### D-018 · Coding model: Claude Haiku 5.5
- **Date:** 2026-10-15 · **Status:** ✅
- **Context:** The analyst chose Haiku over Opus for the coding calls (cost/speed).
- **Decision:** `model: claude-haiku-5-5`, effort `medium`. Server-side refusal fallback is not
  available for Haiku 5.5, so `fallbacks` is off; a refusal is recorded as an error for that answer.
- **Consequences:** Supersedes the model part of D-017. The cache key includes the model, so any
  earlier codes from another model are not reused. Validate quality in human review; if theme or
  sarcasm accuracy is poor, switch back with one line in `config/llm.yaml`.

### D-019 · Review decisions survive codebook changes; codebook 0.2
- **Date:** 2026-10-15 · **Status:** ✅
- **Context:** Pilot review produced 6 "NEW" topics, four of which were comments typed into the
  new-topic box because the review screen had no second-topic or note field. Extending the codebook
  would also have invalidated every review decision (segment ids embedded the request key).
- **Decision:** Segment ids now depend only on respondent, question, sent text and position — not on
  codebook, model or prompt. Codebook 0.2 adds a separate family **OWN** (commitment & ownership:
  `OWN.COMMITMENT_LACK`, `OWN.COMMITMENT_POSITIVE`) at the analyst's request, plus
  `INFO.ACCESS_SUFFICIENT`. The review screen gained a second-topic picker and a note field.
- **Consequences:** A codebook change still re-codes answers on the next `code-text` run (the prompt
  changed), but human decisions on unchanged answers are kept. Pilot review file migrated in place.
