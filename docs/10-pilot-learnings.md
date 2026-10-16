# 10 — Pilot Learnings (export of 2026-10-15, N = 3)

What the first three responses teach us about the **instrument and the pipeline**.
No quantitative results are reported: N = 3 is below k = 5 ([08](08-privacy-and-ethics.md#minimum-group-size-k)),
and nothing here is linked to a respondent or a branch.

## Coverage

- 3 complete core sections (blocks A–I); 2 responses with a branch block, 1 without.
- Back-office branch: no responses yet.
- Survey is still open — expect the picture to change.

## What the pipeline must handle (confirmed by real data)

| Learning | Where it's handled |
|---|---|
| Positional mapping is mandatory (duplicate header, differing whitespace in grid labels) | [04 › A1–A4](04-data-quality.md#a-export-format-issues) |
| Turkish-locale timestamps (`ÖS`), owner's timezone | [04 › A6](04-data-quality.md#a-export-format-issues) |
| Three kinds of "empty": can't judge, no issue, nothing to add — plus not-routed | [05 › Response status](05-standardization.md#response-status-taxonomy) |
| A scale N/A option used to mean "I work alone", explained only in the follow-up text | [04 › B3](04-data-quality.md#b-response-content-issues) |
| Irony in an "enjoy most" answer — a sentiment model would score it positive | [07 › sarcasm](07-text-codebook.md#dimension-37) |
| A response whose scale answers contradict each other | [04 › B6](04-data-quality.md#b-response-content-issues) |
| Q18.1 answered against two different lists | [02 › W3](02-survey-instrument.md#known-instrument-weaknesses) |
| German jargon inside English answers carrying organizational meaning | [05 › glossary](05-standardization.md#text-processing) |
| Multi-idea answers needing segmentation | [07 › Unit of coding](07-text-codebook.md#unit-of-coding) |

## Emerging themes (to test once n ≥ k)

Themes appear here because they occurred at least once — **not** because they are prevalent.

| Area | Themes |
|---|---|
| Leadership & direction | Responsibility passed around on unpleasant decisions · slow decisions and long discussions · repeated strategy/approach changes and compressed timelines · shifting personal responsibilities · trust that is stated but not sustained · problems everyone knows about but nobody owns |
| Operations | Having to chase for information · department-dependent cooperation quality · single-person roles · no capacity to build new processes/products · rework caused by poor prior infrastructure at new clients · limits on what information can be shared |
| Motivation | Supervisor recognition rated neutral in desirability — recognition may not be the lever, or its source has lost weight · work-life balance and pay named as top levers |
| Strengths | Helpful colleagues · family-like atmosphere · honesty and transparency toward customers · tailored offers · strong technical expertise · learning new products · room to contribute ideas |
| Business | Losing deals to providers with a broader one-stop portfolio · customers unaware of the full offering · customer budget limits · infrastructure analysis as a door-opener · demand for security and infrastructure topics · value is easy to sell once presented |

## Hypotheses → interview probes

For the optional face-to-face interviews. Probes explore themes, never people
(and interview sign-ups are never linked to survey responses).

1. When a decision has unpleasant consequences, how is it made, and who ends up owning it?
2. What happens to issues that "everyone knows about"? Who tracks and owns them?
3. How often have priorities or the overall approach changed in the past year, and how was that communicated?
4. What kind of recognition actually matters to you, and from whom?
5. Which collaborations across departments work well — and what is different about them?
6. When the only person who knows a topic is unavailable, what happens?
7. What would "trust" look like in day-to-day work here?
8. Where do customer needs get lost between delivery and sales?
9. Which of our services would customers buy if they knew we offered them?

## Open questions for the form owner

| # | Question | Blocks |
|---|---|---|
| 1 | How is branch routing done? Is there a routing question missing from the export? | `branch` derivation |
| 2 | Full option lists for every scale (several labels not yet observed) | `config/scales.yaml` |
| 3 | Anchors of Q18 (1–5), Q22 (0–10), Q23 (1–5) | Polarity, reverse-reading check |
| 4 | Approximate headcount per area | Choosing k, feasibility of breakdowns |
| 5 | Survey close date; is a second wave planned? | Timeline, trend design |
| 6 | Is there a works council / data protection officer? Is LLM processing of redacted text approved? | Phase 2 |
