# 07 — Text Codebook (v0.2)

How free-text answers are turned into structured, countable codes. The codebook is
**hybrid**: a deductive starter set derived from the instrument and the pilot answers, extended
inductively as new answers arrive. Every change bumps `codebook_version` and is logged at the
bottom of this file.

The machine-readable version is [`config/codebook.yaml`](../config/codebook.yaml) (its examples are synthetic); this file is the human reference. Keep both in sync and bump `version` in both.

## Unit of coding

One **idea unit** = one claim, complaint, observation or suggestion. Multi-idea answers are
segmented first ([05 › Text processing](05-standardization.md#text-processing)). Each segment
gets one primary theme (optional secondary) plus the dimensions below.

## Dimensions

### Dimension 1 — Theme

Hierarchical `FAMILY.CODE`. `+` = typically positive, `−` = typically negative, `±` = either.

| Family | Code | Definition | |
|---|---|---|---|
| **LEAD** leadership practice | `RESPONSIBILITY_DIFFUSION` | Ownership of tasks/decisions is passed back and forth; nobody takes it | − |
| | `DECISION_AVOIDANCE` | Decisions with negative consequences are postponed or deflected | − |
| | `DECISION_LATENCY` | Decisions take too long; topics stall | − |
| | `SUPPORT_LACK` / `SUPPORT_POSITIVE` | (Lack of) backing from supervisor/management | ± |
| | `HONEST_RESPONSE_NEEDED` | Asks for open, honest communication and clear answers | − |
| **STRAT** direction | `DIRECTION_CHANGES` | Strategy or approach changes repeatedly | − |
| | `SHORT_TERMISM` | Unrealistic timelines, short-term actions over long-term plans | − |
| **ROLE** clarity | `SHIFTING_RESPONSIBILITIES` | Own responsibilities change frequently | − |
| | `UNCLEAR_OWN` / `UNCLEAR_OTHERS` | Unclear who does what | − |
| | `CLEAR` | Responsibilities explicitly described as clear | + |
| **CULT** culture & climate | `TRUST_DEFICIT` | Trust is claimed but not lived; lack of sustained trust | − |
| | `RECOGNITION_LACK` | Effort not seen or appreciated | − |
| | `FEAR_OF_SPEAKING` | Hesitation to raise concerns | − |
| | `CONFLICT_DRAG` | Disagreements are discussed excessively without resolution | − |
| | `FAMILY_ATMOSPHERE` | Welcoming, family-like atmosphere | + |
| | `HELPFUL_COLLEAGUES` | Colleagues help; nobody is left alone | + |
| | `IDEAS_WELCOME` | New ideas are supported | + |
| **OWN** commitment & ownership | `COMMITMENT_LACK` | Tasks are not done with real commitment and ownership; wish that work is done properly | − |
| | `COMMITMENT_POSITIVE` | People take ownership and do their job properly | + |
| **INFO** information | `FOLLOW_UP_BURDEN` | Having to chase people for answers/information | − |
| | `MISSING_ANSWERS` | Questions go unanswered | − |
| | `HANDOVER_MISSING` | Information missing at handover | − |
| | `SHARING_LIMITS` | Not everything can be shared; wish for accessible general info | ± |
| | `ACCESS_SUFFICIENT` | Access to information is sufficient; no change needed | + |
| **XFUNC** cross-functional | `VARIES_BY_DEPT` | Cooperation quality depends heavily on the department | − |
| | `GOOD_COOPERATION` | Departments cooperate well | + |
| | `NEEDS_TO_SALES` | Customer needs/opportunities (do not) reach sales | ± |
| **PROC** process | `MEETING_OVERLOAD` | Too many / unproductive meetings | − |
| | `REWORK_INHERITED` | Avoidable work caused by poor upstream or previous-provider quality | − |
| | `PROCESS_MISSING` | No defined process for a recurring task | − |
| **CAP** capacity | `NO_CAPACITY` | No capacity to improve or develop processes/products | − |
| | `WORKLOAD_HIGH` | Too much work for available time | − |
| **ORG** structure | `SOLO_ROLE` | Respondent works alone in their department/function — **aggregate only** | ± |
| | `PERSONNEL_CHANGE` | Suggests changes in staffing/people as the fix — **sensitive, never quoted** | − |
| **REW** reward | `PAY` | Pay / financial reward | ± |
| | `CRITERIA_OPAQUE` | Unclear how rewards are decided | − |
| **WLB** | `WORK_LIFE_BALANCE` | Work-life balance | ± |
| **TOOL** | `TOOLS_LACK` | Missing or inadequate tools/resources | − |
| **GROW** growth | `LEARNING` | Learning, discovering new products/technologies | + |
| | `DEVELOPMENT_LACK` | No development opportunities | − |
| **MEAN** meaning & enjoyment | `CONTRIBUTION` | Driving things forward, contributing ideas | + |
| | `NOTHING_ENJOYABLE` | Nothing (or only trivia) named as enjoyable / source of pride | − |
| | `QUALITY_PRIDE` | Pride in colleagues' expertise or solution quality | + |
| **CUST** customer | `TRANSPARENCY_VALUED` | Customers value honesty, transparency, fairness | + |
| | `TAILORED_OFFERS` | Offers tailored to actual customer needs | + |
| | `BUDGET` | Customer budget limits business | − |
| **BIZ** business | `PORTFOLIO_GAP` | Deals lost to providers offering a broader portfolio | − |
| | `OFFER_AWARENESS` | Customers don't know what we offer → cross-sell potential | ± |
| | `ENTRY_SERVICE` | A service that opens doors to further business | + |
| | `TARGETED_ENGAGEMENT` | Proactive, tailored engagement with existing/new customers | + |
| | `DEMAND_TOPIC` | Topics customers ask for (e.g. security, infrastructure) | + |
| | `VALUE_SELLING_EASY` | Customers easily convinced; high close rate | + |
| **META** stance | `PREMISE_REJECTED` | Answer rejects the question's premise | ± |

### Dimension 2 — Locus

**Who or what the respondent holds responsible or is describing** (not who is affected).

| Locus | Use when |
|---|---|
| `self` | Own behaviour or situation |
| `peers` | Colleagues in the same department |
| `direct_supervisor` | **Explicit** mention of own supervisor / boss / Führungskraft / Chef |
| `management` | Senior leadership, Geschäftsleitung, "the company decides", strategy owners |
| `other_department` | Another department or function |
| `company` | Culture or organization as a whole, no actor implied |
| `process_tool` | Processes, systems, tools |
| `customer_market` | Customers, competitors, previous providers |
| `unspecified` | No actor identifiable — **default; do not guess** |

`direct_supervisor` vs `management` is the distinction that makes leadership findings
actionable. Never infer `direct_supervisor` from context alone.

### Dimension 3–7

| Dimension | Values | Notes |
|---|---|---|
| `valence` | −1 / 0 / +1 | As intended by the respondent (after sarcasm review) |
| `intensity` | 1 mild · 2 clear · 3 strong | Strong = absolute language, emotional emphasis, or explicit consequence |
| `sarcasm` | true / false | Literal meaning ≠ intended meaning. Valence is inverted **only after human confirmation** |
| `actionable` | true / false | Contains a concrete, implementable suggestion |
| `suggestion` | short normalized text or null | E.g. "decision owner for recurring decisions" — feeds the improvement backlog |

## Coding rules

1. Code what is said. The only interpretive dimension is `sarcasm`, and it requires review.
2. One primary theme per segment; add a secondary theme only if the segment genuinely carries two.
3. Positive themes are coded with the same care as negative ones — they show what to preserve.
4. Code from **redacted** text only. Codes never contain names.
5. `ORG.SOLO_ROLE` and `ORG.PERSONNEL_CHANGE` are reported as aggregate shares only and never quoted.
6. Answers with status `NO_BASIS`, `PLACEHOLDER`, `EMPTY` are not coded. `NO_ISSUE` is coded with the matching positive theme (e.g. "responsibilities are clear" → `ROLE.CLEAR`).
7. Unknown concept → propose `NEW:<short_label>`; reviewed and either mapped or added (version bump).

## Anchor examples

Paraphrased from the pilot; deliberately **not linked** to each other or to respondents.

| Paraphrased segment | Theme | Locus | Val | Int | Notes |
|---|---|---|---|---|---|
| Responsibility and decisions bounce back and forth, especially when consequences are unpleasant | `LEAD.RESPONSIBILITY_DIFFUSION` (+ `DECISION_AVOIDANCE`) | unspecified | −1 | 2 | Core leadership signal |
| Having to follow up constantly | `INFO.FOLLOW_UP_BURDEN` | unspecified | −1 | 2 | |
| Cut unnecessary meetings; make decisions faster | `PROC.MEETING_OVERLOAD` (+ `LEAD.DECISION_LATENCY`) | management | −1 | 2 | actionable |
| A multi-year project is squeezed into two months, then the approach changes again | `STRAT.SHORT_TERMISM` (+ `DIRECTION_CHANGES`) | management | −1 | 3 | |
| My responsibilities change every few months | `ROLE.SHIFTING_RESPONSIBILITIES` | management | −1 | 2 | |
| Problems labeled "known issues" that nobody really owns | `LEAD.RESPONSIBILITY_DIFFUSION` | company | −1 | 2 | German jargon kept + glossed |
| Trust must be shown consistently over time, not just stated | `CULT.TRUST_DEFICIT` | management | −1 | 3 | actionable |
| What I enjoy most: occasionally someone brings birthday cake | `MEAN.NOTHING_ENJOYABLE` | company | −1 | 2 | `sarcasm = true` → confirm |
| There is always someone to help; nobody is left alone | `CULT.HELPFUL_COLLEAGUES` | peers | +1 | 2 | |
| A customer chose another integrator who offered more services in one package | `BIZ.PORTFOLIO_GAP` | customer_market | −1 | 2 | |
| Customers probably don't know we offer this; nothing achievable in 30 days | `BIZ.OFFER_AWARENESS` + `META.PREMISE_REJECTED` | customer_market | 0 | 1 | |
| Disagreements are discussed at excessive length | `CULT.CONFLICT_DRAG` | unspecified | −1 | 2 | Resolves Q18.1 "the first one" → Q18a |
| Personnel changes (as the fix for cooperation) | `ORG.PERSONNEL_CHANGE` | unspecified | −1 | 2 | sensitive |
| New clients' infrastructure was left in poor shape by the previous provider | `PROC.REWORK_INHERITED` | customer_market | −1 | 2 | |
| No capacity to develop new processes and products | `CAP.NO_CAPACITY` | company | −1 | 2 | |
| We are honest and transparent with customers, and they value it | `CUST.TRANSPARENCY_VALUED` | self | +1 | 2 | |

## LLM-assisted coding protocol

1. **Input per call** (one answer per call, only rows approved in the send manifest): the
   bilingual question text, the answer status, the redacted answer, and a coarse
   `engagement_band` (favorable / neutral / unfavorable / unknown) to support sarcasm detection.
   The codebook sits in the cached system prompt. No IDs, branch, timestamps or other answers.
2. **Output:** JSON constrained by a schema built from the codebook — `language`,
   `translation_en` and per segment `text_en`, `theme` (or `NEW` + `new_theme_label`),
   `secondary_theme`, `locus`, `valence`, `intensity`, `sarcasm`, `actionable`, `suggestion`,
   `confidence` (low / medium / high). Model and settings: [DECISIONS D-017](../DECISIONS.md).
   "Nothing" answers to Q14/Q15 are coded locally as `MEAN.NOTHING_ENJOYABLE` and never sent.
3. **Validation:** while N is small, a human reviews **every** coded segment. Later: double-code
   ≥ 20 %, compute Cohen's κ per dimension (targets: theme ≥ 0.70, locus ≥ 0.60), and review all
   segments with `confidence < 0.7`, `sarcasm = true`, or `locus = direct_supervisor`.
4. **Provenance:** `coder` (`llm:<model>` / `rule`), `codebook_version`, `review_status`
   (pending → accepted / edited / rejected) and `reviewer_note` in
   `data/interim/<wave>/review_segments.csv`. Re-runs never overwrite a decided row;
   `hrsurvey review-import` refuses pending or invalid rows.

## Change log

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-10-15 | Initial deductive codebook from instrument design + pilot export (N = 3) |
| 0.2 | 2026-10-15 | From pilot review: new family **OWN** (commitment & ownership — kept separate from culture at the analyst's request) with `OWN.COMMITMENT_LACK` / `OWN.COMMITMENT_POSITIVE`, + `INFO.ACCESS_SUFFICIENT` ("no change needed" answers to Q8). Clarified: `PROC.REWORK_INHERITED` covers re-discovering new clients' infrastructure. |
