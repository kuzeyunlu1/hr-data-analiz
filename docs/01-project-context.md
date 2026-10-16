# 01 — Project Context

## What this is

An analysis system for an **anonymous employee experience survey** run as part of a
two-month internship project. The survey covers employee experience, customer needs,
internal processes, cross-department cooperation, motivation and improvement ideas.
It mixes closed (scale) questions and open-ended questions, in English and German.

The system's job: **standardize the answers into a clean, comparable dataset and detect
recurring patterns** — in particular

1. **Leadership- and management-related friction** — e.g. responsibility being passed back
   and forth, slow or avoided decisions, recognition gaps, low psychological safety, unstable
   priorities, trust deficits; and
2. **Efficiency / business-improvement opportunities** — e.g. information gaps at handovers,
   avoidable rework, cross-department friction, unmet customer needs, cross-selling gaps.

## Guiding principle: patterns, not people

The survey introduction makes three explicit promises to respondents:

| Promise in the survey introduction | Consequence for this system |
|---|---|
| The purpose is *not* to evaluate individual employees. | Outputs are group-level patterns. No per-person scores, rankings or profiles. |
| The questionnaire is anonymous. | No re-identification attempts of any kind (timestamps, writing style, rare-answer combinations). Minimum group size for every breakdown. |
| Interview sign-up details are not linked to questionnaire responses. | The pipeline never joins sign-up data to responses. |

Detecting manager-related problems is still possible — and the instrument is built for it
(see [02 › Leadership signal map](02-survey-instrument.md#leadership-signal-map)) — but as
**patterns in a group of sufficient size**, triangulated across scale items and free text.
The output is a hypothesis to explore (e.g. in the follow-up interviews), never a verdict on
a person. Full rules: [08-privacy-and-ethics](08-privacy-and-ethics.md).

## Organizational context (inferred from responses — verify)

| Aspect | Inference | Evidence |
|---|---|---|
| Industry | IT services provider / system integrator with consulting and managed services | Mentions of IT security, infrastructure, managed services, "integrator", consultants |
| Language / region | German-speaking (DACH), English as preferred survey language | Bilingual EN/DE instrument, German phrases in English answers |
| Size | Small to mid-sized; several respondents describe being the only person in their department | Q4/Q4.1 answers |
| Functional areas | At least: technical/consulting, sales, back office (Sachbearbeitung), plus roles routed to none of these | Three branch blocks in the form |
| Customer relationship | B2B, project-based, trust and transparency as differentiators | Q1 answers |

## Timeline

| Date | Event |
|---|---|
| 2026-10-14 | First response recorded |
| 2026-10-15 | Export analysed for this documentation (N = 3) |
| tbd | Survey close |
| tbd | Optional face-to-face interviews (sign-up via separate link) |
| tbd | Results presentation to management |

The survey is **still collecting**. All design decisions assume N will grow and that the
pipeline will be re-run on new exports (and possibly on future waves).

## Stakeholders

| Stakeholder | Interest | What they receive |
|---|---|---|
| Respondents (employees) | Being heard without exposure | Aggregated results, visible follow-up actions |
| Management | Actionable improvement areas | Group-level findings, improvement backlog |
| Intern / analyst | Deliverable for the internship | This pipeline, reports, interview guide |
| HR / data protection (if present) | Compliance | Privacy design ([08](08-privacy-and-ethics.md)) |
| Works council (if present) | Co-determination on employee surveys and analysis tools | Same as above — verify whether consent is required |

## Scope

**In scope**

- Ingestion and validation of Google Forms CSV exports
- Standardization of all 86 columns (scales, non-answers, bilingual text)
- Construct indices, importance–satisfaction gaps, expectancy (VIE) analysis
- Thematic coding of free text (LLM-assisted, human-validated)
- Rule-based pattern detection with confidence levels and k-anonymity suppression
- Reports: findings, improvement backlog, customer/business insight register, interview probes

**Out of scope**

- Identifying, scoring or ranking individual employees or managers
- Linking survey data to HR records, interview sign-ups or any other dataset
- Statistical inference at current N (see [06 › Small-N policy](06-pattern-detection.md#small-n-policy))
- Real-time dashboards (possible later, see [09](09-architecture.md#roadmap))
