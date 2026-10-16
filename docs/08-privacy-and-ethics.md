# 08 — Privacy, Anonymity & Ethics

This system processes candid feedback from employees who were promised anonymity, in what is
likely a small organization. A single slip — a quote that sounds like one person, a breakdown
with two respondents — can expose someone and destroy trust in every future survey.
These rules are **binding design constraints**, not guidelines.

> Not legal advice. The legal checkpoints below are prompts to verify with HR, the data
> protection officer and (if one exists) the works council.

## Commitments

**The system will**

- report only aggregated results for groups with n ≥ k;
- detect leadership and process patterns at group level, triangulated across sources;
- keep raw data on the analyst's machine only;
- redact personal data before any text leaves that machine;
- delete raw data at project end.

**The system will never**

- identify, score, rank or profile individual respondents — or individual managers;
- attempt re-identification by any means: timestamps, writing style, spelling, language choice,
  rare-answer combinations, branch + content linkage;
- link survey responses to interview sign-ups, HR records or any other dataset;
- produce a list of "at-risk" or "problematic" people;
- serve as the sole basis for a personnel decision about anyone.

## Re-identification vectors in this dataset

| Vector | Why it's risky here | Mitigation |
|---|---|---|
| Timestamp | Can be matched to who was at their desk / in a meeting | Parsed into `wave_id`, then dropped ([05](05-standardization.md#pipeline-stages)) |
| Branch (technical / sales / back office) | Small functions may have 1–3 people | Branch breakdowns only if n ≥ k, with complementary suppression |
| Self-descriptions in text | "I'm the only one in my department" identifies the person outright in a small company | Redacted to `[ROLE]`; `ORG.SOLO_ROLE` reported as aggregate share only |
| Content + branch linkage | A sales-specific complaint reveals that the author is in sales, linking their other answers | Never publish a respondent's answers side by side; quotes are unlinked |
| Writing style, typos, language choice | Colleagues recognize each other's writing | Paraphrase in reports; never use style as a feature |
| Rare answer combinations | An unusual scale profile can be recognizable | No respondent-level tables leave `data/processed/` |
| Customer / project mentions | Specific deals point to specific account owners | Redacted to `[CUSTOMER]` / `[PROJECT]` |

## Minimum group size (k)

- Default **k = 5** (`config/privacy.yaml → k`). No statistic, share, theme count or quote is
  reported for a group with fewer than k respondents.
- k applies to the **number of respondents who answered the item**, not the number in the group
  (an item answered by 3 of 8 people is suppressed).
- The whole-organization total is also subject to k: with N < k, nothing is reported at all.
- Raise k (never lower it) if the population is very small or a group is highly homogeneous.

## Complementary suppression

If a total and all-but-one subgroups are shown, the hidden subgroup can be computed by
subtraction. Rule: when any subgroup is suppressed, suppress at least one more subgroup (the
next smallest) or show only the total. The report generator enforces this automatically.

## Quoting rules

1. Only from groups with n ≥ k.
2. Default to **paraphrase**. A verbatim quote requires that it contains no names, roles, customers,
   projects, distinctive phrasing or typos — the analyst confirms this manually.
3. Never more than one quote per respondent in a report, and quotes are never placed next to
   each other in a way that links them to one author.
4. Never quote `ORG.SOLO_ROLE`, `ORG.PERSONNEL_CHANGE`, or anything mentioning health, family or
   other personal circumstances.
5. Translation of a German answer into English counts as paraphrase-level protection only if the
   wording is also neutralized.

## Sensitive content in free text

Free text can contain special-category data (e.g. health, burnout, family situations) or
accusations against identifiable people. Handling:

- Detected at redaction time → segment flagged `sensitive`, excluded from LLM coding and from
  reports; counted only in an aggregate "sensitive content present" metric for the analyst.
- Allegations of misconduct against a named or identifiable person are **out of scope** for this
  analysis. The analyst escalates through the appropriate channel (HR / compliance) per company
  policy, without the survey data leaving the restricted zone.

## Data zones

| Zone | Path | Contains | Who | Committed to git |
|---|---|---|---|---|
| Raw | `data/raw/` | Original exports | Analyst only | **Never** |
| Interim | `data/interim/` | Normalized, still raw text | Analyst only | **Never** |
| Processed | `data/processed/` | Redacted, coded, respondent-level | Analyst only | **Never** |
| Reports | `reports/` | Aggregated, k-checked, reviewed | Management after review | Never by default; publish manually |
| Docs & config | `docs/`, `config/` | No respondent data | Anyone | Yes |

Storage: encrypted disk; no copies in e-mail, chat tools or shared drives.
Retention: raw and interim data deleted at project end (date tbd); processed data deleted or
fully aggregated at the same time.

## External processing (LLM APIs)

Sending employee free text to an external model provider is a transfer to a processor.

- Only **redacted** segments are sent; never timestamps, branch or scale profiles (only a coarse
  `engagement_band`, see [07](07-text-codebook.md#llm-assisted-coding-protocol)).
- Company approval reported by the analyst on 2026-10-15 ([D-007](../DECISIONS.md)). Keep the
  data processing agreement, data-location and retention settings on file with that approval.
- **Send manifest gate** ([D-016](../DECISIONS.md)): local redaction first, then the analyst
  approves every row; only `approved=yes` rows are sent, exactly as shown. One answer per request.
- API credentials live in `.env` (gitignored); never in code, config or chat.

## Legal checkpoints (verify — DACH context)

| Topic | Why it may apply |
|---|---|
| GDPR applicability | Survey data counts as anonymous only if re-identification is not reasonably likely (Recital 26). With free text in a small organization, treat it as personal data. |
| GDPR principles (Art. 5) | Purpose limitation (improvement, not individual evaluation), data minimization, storage limitation. |
| Employee data (Art. 88 GDPR, § 26 BDSG) | Processing of employee data in the employment context. |
| Processor agreement (Art. 28 GDPR) | Any external tool that processes the text (LLM API, cloud storage). |
| Works council: § 94 BetrVG | Personnel questionnaires may require works council consent. |
| Works council: § 87 (1) Nr. 6 BetrVG | Technical systems objectively suitable for monitoring employee behaviour or performance are subject to co-determination — an automated analysis system may fall under this. |

If the organization is in Austria or Switzerland, the equivalent national rules apply instead.

## Use of results

- Findings are **hypotheses about the organization**, based on self-reports from a small sample.
  They are inputs to conversations (interviews, team discussions, leadership development),
  not evidence against anyone.
- Every report states n, confidence level and limitations.
- Respondents should see what happens with their feedback — visible follow-up is what makes
  the next survey honest.

## Pre-release checklist (every report)

- [ ] Every reported group and item has n ≥ k
- [ ] Complementary suppression applied
- [ ] No timestamps, branch-by-respondent tables, or respondent IDs in the report
- [ ] Every quote reviewed against the quoting rules
- [ ] No `ORG.SOLO_ROLE` / `ORG.PERSONNEL_CHANGE` / sensitive content quoted
- [ ] Confidence and limitations stated for every finding
- [ ] Second person reviewed the report before it leaves the analyst
