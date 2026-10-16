# 02 — Survey Instrument

Title (from export file name): *Employee Experience, Motivation & Business Improvement —
Mitarbeitererfahrung, Motivation & Unternehmensverbesserung*. Platform: Google Forms.
All questions are bilingual (EN first, DE second); answers may be given in either language.

## Blocks

| Block | Questions | Theme | Item types |
|---|---|---|---|
| A | Q1–Q3 | Customer value, customer problems, business opportunities | 3 × text |
| B | Q4–Q6 | Cooperation within and across departments | 2 × scale, 3 × text |
| C | Q7–Q13 | Information access, role clarity, reachability, obstacles | 6 × scale, 3 × text |
| D | Q14–Q15 | Pride and enjoyment | 2 × text |
| E | Q16 | Importance of 14 motivation factors | 14 × scale |
| F | Q17 | Satisfaction with the same 14 factors | 14 × scale |
| G | Q18, Q18.1 | Climate: conflict, recognition, support, priorities, time, voice, recommendation | 10 × scale (numeric 1–5), 1 × text |
| H | Q19–Q23 | Expectancy chain (VIE), recent motivation, company support | 3 × scale, 2 × numeric |
| I | Q24 | The ONE suggestion management should implement | 1 × text |
| T | T1–T7 | **Branch: technical** — customer needs → sales, handover completeness, avoidable work | 2 × scale, 5 × text |
| S | S1–S7 | **Branch: sales** — growth segments, high-value services, internal hindrances, value selling | 2 × scale, 5 × text |
| O | O1–O7 | **Branch: back office** — delays, info completeness, handovers, recurring enquiries | 2 × scale, 5 × text |

Column-level detail: [03-data-dictionary](03-data-dictionary.md).

## Branching

Blocks A–I are answered by everyone. Blocks T, S, O are role-specific.
In the pilot export: one respondent answered T, one answered S, one answered no branch; nobody answered O.

**Open question:** the export contains **no routing variable** (no "Which area do you work in?"
column). Either the routing question was removed from the export, or the branch sections are
optional and self-selected. This matters because:

- `branch` is currently *derived* (= the branch block with ≥ 1 non-empty answer). A routed
  respondent who skipped every branch question is indistinguishable from `none`.
- Branch is the **only** grouping variable available — and with a small company, branch groups
  will often be below the anonymity threshold (see [08](08-privacy-and-ethics.md#minimum-group-size-k)).

→ Confirm the routing logic with the form owner before relying on `branch`.

## Scales used

| scale_id | Used by | Points | Labels observed in pilot | Not yet observed (expected — verify in form) |
|---|---|---|---|---|
| `QUALITY5` | Q4, Q5 | 5 + N/A | Very good, Good, Neither poor nor good, *Not enough experience to judge* | Poor, Very poor |
| `SAT5` | Q7, Q17 | 5 | all five | – |
| `CLARITY5` | Q9, Q10 | 5 | Very clear, Clear, Very unclear | middle label, Unclear |
| `EASE5` | Q11 | 5 | Very easy, Easy | middle, Difficult, Very difficult |
| `AGREE5_LABELED` | Q13a–b | 5 + N/A | Strongly agree, Agree, Neither, Strongly disagree, *Unable to judge* | Disagree |
| `AGREE5_NUMERIC` | Q18a–j | 1–5 digits | 1–5 | anchors not exported |
| `IMPORTANCE5` | Q16 | 5 | Extremely, Very, Moderately important | Slightly, Not at all important |
| `PROB5` | Q19, Q20 | 5 (0–100 %) | 25 %, 50 %, 75 % | 0 %, 100 % |
| `DESIRABILITY5` | Q21 | 5 | Very desirable, Neither desirable nor undesirable | the rest |
| `NUM0_10` | Q22 | 11 | 0, 8 | anchors not exported |
| `NUM1_5` | Q23 | 5 | 2, 4 | anchors not exported |
| `EFFECTIVE5` | T2, O4 | 5 | Very effectively | the rest |
| `COMPLETE5` | T4, O2 | 5 | Very complete | the rest |
| `EXTENT5` | S3 | 5 | Moderately | the rest (negative polarity) |
| `DIFFICULTY5` | S5 | 5 | Not difficult at all | the rest (negative polarity) |

Full label → code mappings: [05 › Scale catalogue](05-standardization.md#scale-catalogue).
**Action:** export the full option lists from the form editor once, and replace every
"expected" label in the config with the real one.

## Theoretical frameworks embedded in the instrument

Recognizing these lets us analyze the data the way the questions were designed.

| Framework | Items | How we use it |
|---|---|---|
| **Importance–Performance Analysis** (Martilla & James) | Q16 × Q17, 14 paired factors | Gap per factor, priority quadrant matrix → [06 › B](06-pattern-detection.md#b-importancesatisfaction-gap-analysis) |
| **Vroom's Expectancy Theory (VIE)** | Q19 = Expectancy (effort → performance), Q20 = Instrumentality (performance → supervisor recognition), Q21 = Valence (value of that recognition); Q22 = motivation outcome | Motivational force `E × I × V`, weakest-link diagnosis → [06 › C](06-pattern-detection.md#c-expectancy-model-vie) |
| **Herzberg's two-factor theory / Self-Determination Theory** | Q16/Q17 factor list mixes hygiene factors (pay, security, workload, tools, relationships) with motivators (recognition, development, interesting & meaningful work, autonomy) | Separate reporting of hygiene vs. motivator gaps |
| **Organizational justice** (procedural / distributive) | Q18c timely, Q18d fair, Q18e transparent criteria | Recognition-system diagnosis |
| **Psychological safety** (Edmondson) | Q18i voice, Q18a constructive conflict | Voice & conflict index |
| **Role ambiguity** (Rizzo et al.) | Q9, Q10, Q18g, Q10.1 | Role clarity index; responsibility-diffusion detection |
| **Perceived organizational support** (Eisenberger) | Q23, Q18f | Org-level leadership index |
| **eNPS-like advocacy** | Q18j | Engagement outcome. *Not* a real eNPS (needs a 0–10 scale). |

## Leadership signal map

Which items carry information about leadership — and at which level. This is the backbone of
manager-related pattern detection.

| Item | Leadership aspect | Level | Signal strength |
|---|---|---|---|
| Q17 `rel_supervisor` | Relationship quality | Direct supervisor | Strong, specific |
| Q20 instrumentality | Will my supervisor recognize good performance? | Direct supervisor | Strong, specific |
| Q21 valence | Is supervisor recognition worth anything to me? (low → trust/relationship erosion) | Direct supervisor | Medium, interpretive |
| Q18f | Feeling supported | **Supervisor OR management** (double-barreled) | Strong, but level ambiguous |
| Q18b, c, d, e | Appreciation, timeliness, fairness, transparency of recognition | Mixed | Medium |
| Q18a | Constructive handling of disagreements | Mixed | Medium |
| Q18i | Safe to raise concerns | Mixed | Strong |
| Q18g, Q9 | Priority and role clarity (management's job to provide) | Mixed | Medium |
| Q18h, Q17 `workload` | Workload allocation | Mixed | Medium |
| Q13b | Timely communication of changes | Organization | Medium |
| Q23, Q17 `job_security` | Organizational support, security | Organization | Medium |
| Text: Q10.1, Q12, Q6, Q24, Q18.1, Q4.1, Q5.1 | Free-text descriptions of decision-making, responsibility, trust, strategy | Coded per segment with a `locus` field | Strongest when triangulated |

The free-text coder assigns each segment a **locus** (`direct_supervisor`, `management`,
`other_department`, `peers`, `process_tool`, `customer`, `self`) — see
[07-text-codebook](07-text-codebook.md#dimension-2--locus). That is how "management" problems are
distinguished from "process" problems without naming anyone.

## Efficiency / business signal map

| Area | Items |
|---|---|
| Information flow | Q7, Q8, Q13a, Q17 `info_access`, T4, T5, O2, O3 |
| Cross-functional handovers | Q5, Q5.1, Q6, Q10, Q11, T2, T3, O4, O5, S3, S4 |
| Avoidable work / rework | Q12, T6, O1 |
| Capacity & tools | Q17 `workload`, Q17 `tools_resources`, Q18h, T7, S7, O7 |
| Customer needs & opportunities | Q1, Q2, Q3, T1, S1, S2, S5, S6, O6 |

## Known instrument weaknesses

Recommendations for a second wave (or for interpreting this one):

| # | Weakness | Consequence | Recommendation |
|---|---|---|---|
| W1 | **Q18f is double-barreled** ("supervisor *or* management"). | Cannot tell direct-supervisor from top-management issues. | Split into two items. |
| W2 | **Mixed scale formats**: Q13 labeled, Q18 numeric with no exported anchors, Q22 0–10, Q23 1–5. | Reversed-reading risk (see [04 › B6](04-data-quality.md#b-response-content-issues)); harder comparison. | One labeled 5-point agreement scale for all agreement items. |
| W3 | **Q18.1 "factors above" is ambiguous** (Q16/17 list or Q18 statements). | Pilot answers referred to both lists. | Make it a dropdown of the 14 factors + "other". |
| W4 | **No "I work alone in my department" option** in Q4. | Single-person roles end up as "Not enough experience to judge". | Add the option (and keep it out of breakdowns — it is identifying). |
| W5 | **No routing / grouping variable** in the export. | Branch must be inferred; no team-level analysis possible. | Add a coarse area question; guarantee in the intro that groups below k are never reported separately. |
| W6 | **Q1–Q3 lack a "no customer contact" checkbox.** | Non-answers arrive as free text. | Add the checkbox; make the text conditional. |
| W7 | Q18j is not a true eNPS. | No benchmark comparability. | If benchmarking matters, ask 0–10 "How likely are you to recommend…". |
| W8 | Timestamp exported in the form owner's locale/timezone. | Parsing fragility, re-identification risk. | Keep the owner locale stable; drop timestamps after ingest. |
