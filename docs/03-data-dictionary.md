# 03 — Data Dictionary

Canonical mapping of every column in the Google Forms export to a stable variable ID.
**This file is the contract** between the raw export and everything downstream
(standardization, indices, rules, codebook). When the form changes, update this file
and [`config/survey_schema.yaml`](../config/survey_schema.yaml) together —
`tests/test_config.py` fails if the two drift apart.

Source file analysed: `data/raw/survey_export_2026-10-15.csv` — 86 columns, 3 responses.

## Conventions

| Element | Rule |
|---|---|
| `idx` | 0-based column position (pandas `iloc`). **Position is the source of truth**, not header text (see [04-data-quality](04-data-quality.md#a-export-format-issues)). |
| `col` | Spreadsheet column letter, for cross-checking in Google Sheets / Excel. |
| `var_id` | `snake_case`, prefixed with question number (`q16_…`) or branch code (`tec`, `sal`, `bo`). Free-text variables end in `_txt`. |
| `block` | Survey block, see [02-survey-instrument](02-survey-instrument.md#blocks). |
| `type` | `scale` (ordinal labelled), `numeric` (bare number), `text` (open-ended), `timestamp`. |
| `scale_id` | Key into the scale catalogue in [05-standardization](05-standardization.md#scale-catalogue). |
| `pol` | Polarity. `+` = higher is healthier, `-` = higher is worse (reversed before indexing). |
| `construct` | The analytical construct the item feeds, see [06-pattern-detection](06-pattern-detection.md#a-construct-indices). |

## Column map

| col | idx | var_id | Q | block | type | scale_id | pol | question (short, EN) | construct |
|---|---|---|---|---|---|---|---|---|---|
| A | 0 | `submitted_at_raw` | - | META | timestamp | TS_GFORMS_TR |  | Form submission timestamp (Google Forms, TR locale) | - |
| B | 1 | `q01_customer_value_txt` | 1 | A | text | - |  | ONE thing your department does that customers value (+ example) | CUSTOMER_INSIGHT |
| C | 2 | `q02_customer_problem_txt` | 2 | A | text | - |  | ONE recurring customer problem / unmet need | CUSTOMER_INSIGHT |
| D | 3 | `q03_business_opportunity_txt` | 3 | A | text | - |  | ONE retention / new-business opportunity + 30-day first step | BUSINESS_OPPORTUNITY |
| E | 4 | `q04_coop_within_dept` | 4 | B | scale | QUALITY5 | + | Rating of cooperation within own department | PEER |
| F | 5 | `q04_1_coop_within_reason_txt` | 4.1 | B | text | - |  | Main reason for the within-department rating | PEER |
| G | 6 | `q05_coop_cross_dept` | 5 | B | scale | QUALITY5 | + | Rating of cooperation with other departments | XFUNC |
| H | 7 | `q05_1_coop_cross_reason_txt` | 5.1 | B | text | - |  | Main reason for the cross-department rating + impact | XFUNC |
| I | 8 | `q06_coop_change_txt` | 6 | B | text | - |  | ONE practical change to improve cooperation (state which type) | XFUNC |
| J | 9 | `q07_info_access_sat` | 7 | C | scale | SAT5 | + | Satisfaction with access to information needed | INFO_FLOW |
| K | 10 | `q08_info_access_change_txt` | 8 | C | text | - |  | ONE change to improve access to information | INFO_FLOW |
| L | 11 | `q09_role_clarity_own` | 9 | C | scale | CLARITY5 | + | Clarity of own responsibilities | ROLE_CLARITY |
| M | 12 | `q10_role_clarity_others` | 10 | C | scale | CLARITY5 | + | Clarity of other departments' responsibilities | XFUNC |
| N | 13 | `q10_1_role_unclear_txt` | 10.1 | C | text | - |  | What is unclear (own / other / both) | ROLE_CLARITY |
| O | 14 | `q11_reachability` | 11 | C | scale | EASE5 | + | Ease of reaching colleagues in other departments | XFUNC |
| P | 15 | `q12_obstacles_txt` | 12 | C | text | - |  | What currently makes the job difficult + impact | OBSTACLES |
| Q | 16 | `q13a_info_clear` | 13a | C | scale | AGREE5_LABELED | + | The information I receive for my work is clear | INFO_FLOW |
| R | 17 | `q13b_change_informed_timely` | 13b | C | scale | AGREE5_LABELED | + | I am informed about changes in time to respond | LEAD_ORG |
| S | 18 | `q14_pride_txt` | 14 | D | text | - |  | What makes you proud to work here | PRIDE_ENJOY |
| T | 19 | `q15_enjoy_txt` | 15 | D | text | - |  | What you enjoy most about working here | PRIDE_ENJOY |
| U | 20 | `q16_imp_pay` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Pay and financial rewards | IMPORTANCE |
| V | 21 | `q16_imp_recognition` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Recognition of my work and contribution | IMPORTANCE |
| W | 22 | `q16_imp_job_security` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Job security | IMPORTANCE |
| X | 23 | `q16_imp_rel_colleagues` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Relationships with colleagues | IMPORTANCE |
| Y | 24 | `q16_imp_rel_supervisor` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Relationship with my direct supervisor | IMPORTANCE |
| Z | 25 | `q16_imp_workload` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: A manageable workload | IMPORTANCE |
| AA | 26 | `q16_imp_work_life_balance` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Work-life balance | IMPORTANCE |
| AB | 27 | `q16_imp_autonomy` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Autonomy in how I do my work | IMPORTANCE |
| AC | 28 | `q16_imp_development` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Opportunities for professional development | IMPORTANCE |
| AD | 29 | `q16_imp_interesting_tasks` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Interesting work tasks | IMPORTANCE |
| AE | 30 | `q16_imp_meaningful_work` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Meaningful work | IMPORTANCE |
| AF | 31 | `q16_imp_info_access` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Access to the information I need | IMPORTANCE |
| AG | 32 | `q16_imp_idea_contribution` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Opportunities to contribute ideas | IMPORTANCE |
| AH | 33 | `q16_imp_tools_resources` | 16 | E | scale | IMPORTANCE5 | + | Importance for motivation: Adequate tools and resources | IMPORTANCE |
| AI | 34 | `q17_sat_pay` | 17 | F | scale | SAT5 | + | Satisfaction: Pay and financial rewards | COMPENSATION |
| AJ | 35 | `q17_sat_recognition` | 17 | F | scale | SAT5 | + | Satisfaction: Recognition of my work and contribution | RECOGNITION |
| AK | 36 | `q17_sat_job_security` | 17 | F | scale | SAT5 | + | Satisfaction: Job security | LEAD_ORG |
| AL | 37 | `q17_sat_rel_colleagues` | 17 | F | scale | SAT5 | + | Satisfaction: Relationships with colleagues | PEER |
| AM | 38 | `q17_sat_rel_supervisor` | 17 | F | scale | SAT5 | + | Satisfaction: Relationship with my direct supervisor | LEAD_DIRECT |
| AN | 39 | `q17_sat_workload` | 17 | F | scale | SAT5 | + | Satisfaction: A manageable workload | WORKLOAD |
| AO | 40 | `q17_sat_work_life_balance` | 17 | F | scale | SAT5 | + | Satisfaction: Work-life balance | WORKLOAD |
| AP | 41 | `q17_sat_autonomy` | 17 | F | scale | SAT5 | + | Satisfaction: Autonomy in how I do my work | GROWTH_MEANING |
| AQ | 42 | `q17_sat_development` | 17 | F | scale | SAT5 | + | Satisfaction: Opportunities for professional development | GROWTH_MEANING |
| AR | 43 | `q17_sat_interesting_tasks` | 17 | F | scale | SAT5 | + | Satisfaction: Interesting work tasks | GROWTH_MEANING |
| AS | 44 | `q17_sat_meaningful_work` | 17 | F | scale | SAT5 | + | Satisfaction: Meaningful work | GROWTH_MEANING |
| AT | 45 | `q17_sat_info_access` | 17 | F | scale | SAT5 | + | Satisfaction: Access to the information I need | INFO_FLOW |
| AU | 46 | `q17_sat_idea_contribution` | 17 | F | scale | SAT5 | + | Satisfaction: Opportunities to contribute ideas | VOICE_CONFLICT |
| AV | 47 | `q17_sat_tools_resources` | 17 | F | scale | SAT5 | + | Satisfaction: Adequate tools and resources | RESOURCES |
| AW | 48 | `q18a_disagreement_constructive` | 18a | G | scale | AGREE5_NUMERIC | + | Disagreements are handled constructively | VOICE_CONFLICT |
| AX | 49 | `q18b_effort_appreciated` | 18b | G | scale | AGREE5_NUMERIC | + | My effort and contribution are appreciated | RECOGNITION |
| AY | 50 | `q18c_recognition_timely` | 18c | G | scale | AGREE5_NUMERIC | + | Good work is recognised in a timely manner | RECOGNITION |
| AZ | 51 | `q18d_recognition_fair` | 18d | G | scale | AGREE5_NUMERIC | + | Recognition is given fairly across employees | RECOGNITION |
| BA | 52 | `q18e_reward_criteria_clear` | 18e | G | scale | AGREE5_NUMERIC | + | I understand how recognition/rewards are determined | RECOGNITION |
| BB | 53 | `q18f_supported_by_leadership` | 18f | G | scale | AGREE5_NUMERIC | + | I feel supported by my supervisor OR management (double-barreled) | LEAD_ORG |
| BC | 54 | `q18g_priorities_clear` | 18g | G | scale | AGREE5_NUMERIC | + | I know which tasks to prioritise | ROLE_CLARITY |
| BD | 55 | `q18h_time_sufficient` | 18h | G | scale | AGREE5_NUMERIC | + | I have enough time to do main tasks to standard | WORKLOAD |
| BE | 56 | `q18i_voice_safety` | 18i | G | scale | AGREE5_NUMERIC | + | I feel comfortable sharing ideas or concerns | VOICE_CONFLICT |
| BF | 57 | `q18j_recommend_employer` | 18j | G | scale | AGREE5_NUMERIC | + | I would recommend this company as a place to work | ENGAGEMENT |
| BG | 58 | `q18_1_top_motivator_txt` | 18.1 | G | text | - |  | Which ONE factor above would most improve motivation + why | SUGGESTION |
| BH | 59 | `q19_expectancy` | 19 | H | scale | PROB5 | + | Effort -> meeting performance expectations (likelihood) | VIE_E |
| BI | 60 | `q20_instrumentality` | 20 | H | scale | PROB5 | + | Performance -> direct supervisor recognises it (likelihood) | VIE_I, LEAD_DIRECT |
| BJ | 61 | `q21_valence` | 21 | H | scale | DESIRABILITY5 | + | Desirability of recognition from direct supervisor | VIE_V |
| BK | 62 | `q22_motivation_2w` | 22 | H | numeric | NUM0_10 | + | Motivation over the past two weeks (0-10) | ENGAGEMENT |
| BL | 63 | `q23_company_support` | 23 | H | numeric | NUM1_5 | + | Feeling supported by the company (1-5) | LEAD_ORG |
| BM | 64 | `q24_top_suggestion_txt` | 24 | I | text | - |  | If management could implement only ONE suggestion | SUGGESTION |
| BN | 65 | `tec1_customer_requests_txt` | T1 | T | text | - |  | Most requested additional service / support / solution | CUSTOMER_INSIGHT |
| BO | 66 | `tec2_needs_to_sales_eff` | T2 | T | scale | EFFECTIVE5 | + | How effectively customer needs reach the sales team | XFUNC |
| BP | 67 | `tec3_needs_to_sales_improve_txt` | T3 | T | text | - |  | Most important improvement to that communication | XFUNC |
| BQ | 68 | `tec4_handover_completeness` | T4 | T | scale | COMPLETE5 | + | Completeness of info at technical task / order handover | INFO_FLOW |
| BR | 69 | `tec5_handover_missing_info_txt` | T5 | T | text | - |  | Information most frequently missing at handover | INFO_FLOW |
| BS | 70 | `tec6_avoidable_work_txt` | T6 | T | text | - |  | Recurring technical task creating most avoidable work | OBSTACLES |
| BT | 71 | `tec7_single_change_txt` | T7 | T | text | - |  | Single change that would make technical work easier | SUGGESTION |
| BU | 72 | `sal1_growth_segment_txt` | S1 | S | text | - |  | Customer group with greatest potential + why | BUSINESS_OPPORTUNITY |
| BV | 73 | `sal2_high_value_service_txt` | S2 | S | text | - |  | Service/solution with greatest added-value potential | BUSINESS_OPPORTUNITY |
| BW | 74 | `sal3_internal_hindrance` | S3 | S | scale | EXTENT5 | - | Extent internal processes/missing info hinder acquisition | XFUNC |
| BX | 75 | `sal4_main_obstacle_txt` | S4 | S | text | - |  | Main obstacle (internal) | OBSTACLES |
| BY | 76 | `sal5_value_convince_difficulty` | S5 | S | scale | DIFFICULTY5 | - | Difficulty convincing customers of our value | BUSINESS_OPPORTUNITY |
| BZ | 77 | `sal6_difficulty_reason_txt` | S6 | S | text | - |  | Main reason for the difficulty rating | BUSINESS_OPPORTUNITY |
| CA | 78 | `sal7_single_change_txt` | S7 | S | text | - |  | Single change that would most help acquisition | SUGGESTION |
| CB | 79 | `bo1_delay_step_txt` | O1 | O | text | - |  | Step in enquiry/order handling causing most delay + why | OBSTACLES |
| CC | 80 | `bo2_info_completeness` | O2 | O | scale | COMPLETE5 | + | Completeness of info when processing enquiry/order | INFO_FLOW |
| CD | 81 | `bo3_missing_info_txt` | O3 | O | text | - |  | Information most frequently missing | INFO_FLOW |
| CE | 82 | `bo4_handover_eff` | O4 | O | scale | EFFECTIVE5 | + | Effectiveness of back-office <-> department handovers | XFUNC |
| CF | 83 | `bo5_handover_improve_txt` | O5 | O | text | - |  | Most important improvement to these handovers | XFUNC |
| CG | 84 | `bo6_recurring_enquiries_txt` | O6 | O | text | - |  | Recurring enquiries hinting at support need / opportunity | CUSTOMER_INSIGHT |
| CH | 85 | `bo7_single_change_txt` | O7 | O | text | - |  | Single change that would make the work easier | SUGGESTION |

### Column counts

| Type | Count |
|---|---|
| timestamp | 1 |
| scale (ordinal) | 55 (Q4, Q5, Q7, Q9, Q10, Q11, 2 × Q13, 14 × Q16, 14 × Q17, 10 × Q18, Q19, Q20, Q21, T2, T4, S3, S5, O2, O4) |
| numeric (bare number) | 2 (Q22, Q23) |
| text (open-ended) | 28 (13 core + 5 technical + 5 sales + 5 back-office) |
| **total** | **86** |

## Motivation factor keys (Q16 ↔ Q17)

Q16 (importance) and Q17 (satisfaction) ask about the **same 14 factors in the same order**.
They are paired by factor key, never by header text (header whitespace differs between the two grids).

| factor key | Label (EN) | Label (DE) | Satisfaction feeds construct |
|---|---|---|---|
| `pay` | Pay and financial rewards | Gehalt und finanzielle Vergütung | COMPENSATION |
| `recognition` | Recognition of my work and contribution | Anerkennung meiner Arbeit und meines Beitrags | RECOGNITION |
| `job_security` | Job security | Arbeitsplatzsicherheit | LEAD_ORG |
| `rel_colleagues` | Relationships with colleagues | Beziehungen zu Kolleginnen und Kollegen | PEER |
| `rel_supervisor` | Relationship with my direct supervisor | Beziehung zu meiner direkten Führungskraft | LEAD_DIRECT |
| `workload` | A manageable workload | Eine gut zu bewältigende Arbeitsbelastung | WORKLOAD |
| `work_life_balance` | Work-life balance | Vereinbarkeit von Beruf und Privatleben | WORKLOAD |
| `autonomy` | Autonomy in how I do my work | Selbstständigkeit bei der Gestaltung meiner Arbeit | GROWTH_MEANING |
| `development` | Opportunities for professional development | Möglichkeiten zur beruflichen Weiterentwicklung | GROWTH_MEANING |
| `interesting_tasks` | Interesting work tasks | Interessante Arbeitsaufgaben | GROWTH_MEANING |
| `meaningful_work` | Meaningful work | Sinnvolle Arbeit | GROWTH_MEANING |
| `info_access` | Access to the information I need | Zugang zu den benötigten Informationen | INFO_FLOW |
| `idea_contribution` | Opportunities to contribute ideas | Möglichkeiten, eigene Ideen einzubringen | VOICE_CONFLICT |
| `tools_resources` | Adequate tools and resources | Ausreichende Arbeitsmittel und Ressourcen | RESOURCES |

## Derived variables

Created by the pipeline; never present in the raw export.

| var_id | Type | Definition |
|---|---|---|
| `response_id` | str | `r_` + first 16 hex chars of HMAC-SHA256(secret salt, full raw row). Stable across re-runs, independent of row order, not reproducible without the salt in `.env`. See [DECISIONS D-011](../DECISIONS.md). *(Originally specified as random UUID v4 — superseded 2026-10-15.)* |
| `wave_id` | string | Survey wave, e.g. `2026-10`. Replaces the timestamp for analysis. |
| `branch` | enum | `technical` / `sales` / `back_office` / `none` / `multiple` — which branch block (T/S/O) contains at least one non-empty answer. See [02 › Branching](02-survey-instrument.md#branching). |
| `core_completion` | float 0–1 | Share of the 51 closed core items (blocks B–H) answered, i.e. status ≠ `EMPTY` ("can't judge" counts as answered). See [DECISIONS D-013](../DECISIONS.md). |
| `<var>_code` | int | Ordinal code of a scale item (1–5, 0–10, …) after label mapping. |
| `<var>_pomp` | float 0–100 | Percent-of-maximum-possible score, polarity-corrected (higher = healthier). |
| `<var>_status` | enum | Response status, see [05 › Response status](05-standardization.md#response-status-taxonomy). |
| `label_unverified` | bool | The cell matched an `expected_labels` entry in `config/scales.yaml` (wording not yet confirmed). See [DECISIONS D-012](../DECISIONS.md). |
| `counts_as_signal` | bool | Text cell counts as information: `SUBSTANTIVE`, `NO_ISSUE`, or `NOTHING_TO_ADD` on Q14/Q15. |
| `gap_<factor>` | int −4…+4 | `q16_imp_<factor>_code − q17_sat_<factor>_code`. Positive = under-served need. |
| `vie_mf` | float | Vroom motivational force `E × I × V`, see [06 › VIE](06-pattern-detection.md#c-expectancy-model-vie). |
| `idx_<CONSTRUCT>` | float 0–100 | Construct index, see [06 › Construct indices](06-pattern-detection.md#a-construct-indices). |
| `qflag_*` | bool | Response-quality flags, see [04 › Response-content issues](04-data-quality.md#b-response-content-issues). |
