# 11 — Making the review screen available beyond the analyst's laptop

Status: **investigation only** (2026-10-15). Nothing here is implemented or deployed. Read with
[08](08-privacy-and-ethics.md), [D-001](../DECISIONS.md), [D-007](../DECISIONS.md) and
[D-016](../DECISIONS.md).

> Not legal advice. Every option that moves review data off the analyst's machine is a new
> processing activity and must be cleared with the data protection officer and, very likely, the
> works council before it is built.

## What exists today

`uv run hrsurvey review-ui --wave W` (`src/hrsurvey/text/review_ui.py`):

- stdlib `ThreadingHTTPServer` bound to **127.0.0.1**, plain HTTP, default port 8765;
- one random per-run token (`secrets.token_urlsafe(16)`) in the page URL and in an `X-Token`
  header on `POST /save` — guards against other tabs, it is **not** a user login;
- `GET /<token>` embeds **all rows** of `data/interim/<wave>/review_segments.csv` as JSON in one
  self-contained page (`Cache-Control: no-store`, CSP `default-src 'self' 'unsafe-inline'`, no
  outside requests, request lines not logged);
- every decision POSTs the **whole row set** back; `save_rows` checks the segment list is
  unchanged and the statuses are valid, then replaces the CSV atomically (`os.replace`).

Properties that matter for deployment:

| Property | Consequence once more than one person or machine is involved |
|---|---|
| Whole-file save, no version check | Two reviewers → **last write wins**, silently undoing the other's decisions |
| No user identity | `reviewer_note` / `review_status` cannot say *who* decided; no second-coder κ possible |
| No audit trail | Changes overwrite in place; no history of who changed what, when |
| Payload carries every `SEGMENT_COLUMNS` field incl. `response_id` | Anyone with the page can group segments by respondent (content + branch linkage, see 08) |
| Token in URL, plain HTTP | Fine on loopback; on any network it leaks via history, proxies, screenshots, and travels unencrypted |
| Reads/writes `data/interim/` directly | The tool *is* the restricted zone; hosting it elsewhere means copying that zone |

## 1. Who would use a deployed version

| Scenario | What changes |
|---|---|
| **A. One analyst, other device** (e.g. reviewing on a second screen or tablet) | No concurrency or identity problem; only transport security. Rarely worth a deployment. |
| **B. Analyst + one second coder** (inter-rater check, D-007 "κ-based sampling later") | Needs identity per decision and *blind* double coding: each coder writes their own column set, the tool never shows coder 1's decision to coder 2. Disagreements are resolved by the analyst. |
| **C. Several reviewers, e.g. HR** | Everything in B, plus row-level locking/assignment, role-based access, audit log, access revocation at project end — and a governance question first (below). |

**Governance before engineering for C.** The survey promised anonymity; HR business partners
and managers are exactly the people respondents may fear being read by. Even redacted and
translated, a small company's colleagues recognize content (08, "re-identification vectors").
Before HR reviews free text:

- reviewers sign a confidentiality commitment specific to the survey;
- nobody reviews answers from the area they manage or support (needs a branch filter, which is
  itself a linkage risk — prefer reviewers outside the line);
- the works council agrees, likely including who the reviewers are. An access log of reviewers is
  itself data about employees' work (§ 87 (1) Nr. 6 BetrVG), so the audit trail needs the same
  agreement;
- respondents' privacy notice covers "a small named group reviews redacted answers" — if it only
  promised "the analyst", widening the circle needs a new notice for future waves and a careful
  look at whether it may apply to the current one at all.

## 2. Options

Effort is engineering time for this codebase; cost is indicative monthly running cost.

### (a) Keep local; share by screen or LAN

- **a1 — co-review at the analyst's machine / screen share.** Second person watches or dictates;
  the analyst clicks. Zero code. A video-call screen share transmits the pixels through the
  meeting vendor (a processor); use the company's approved tool, no recording, close the call
  when done. Identity: the analyst records the second coder's verdict in `reviewer_note`.
- **a2 — bind to the LAN.** Changing `127.0.0.1` to a LAN address exposes plain-HTTP JSON of all
  segments to the office network, with the token in the URL. Not acceptable without TLS and a
  real login; at that point it is option (b) on a laptop. **Not recommended.**
- Privacy: best — data stays in the restricted zone (08 data zones). Effort: none. Cost: none.
  Limits: one decision-maker at a time; does not scale to C.

### (b) Internal company hosting (VM/container behind SSO/VPN)

A small service on company infrastructure (on-prem VM, or the company's existing EU cloud
tenant), reachable only via VPN/zero-trust proxy, login through the company IdP (Entra ID /
Google Workspace / Keycloak) via an auth proxy (e.g. oauth2-proxy) that passes a verified
identity header.

- Privacy/GDPR: data stays within the controller's own systems and existing processor contracts;
  EU location is under company control. It is still a **new copy of interim data outside the
  analyst's machine** — needs a records-of-processing entry, DPO sign-off, works-council
  agreement, and a deletion date. Company admins of that VM can read the data: use a dedicated,
  encrypted volume and restrict admin access, or accept and document it.
- Effort: medium, ~3–5 days (code changes below + container + IdP config + tests).
- Cost: low, ~€0–30/month on existing infrastructure; the real cost is IT/DPO/works-council time.
- Code changes:
  1. Replace whole-file save with **per-row PATCH** carrying a row version
     (`segment_id`, `version`); reject stale writes (HTTP 409) instead of last-write-wins.
  2. Storage: SQLite (or the company Postgres) with tables `segments`, `decisions`
     (`segment_id`, `reviewer`, `status`, codes, `decided_at`) and append-only `audit_log`.
     `review-import` reads from an export of that DB back into the local pipeline.
  3. Identity from the trusted proxy header only; drop the URL token; CSRF protection on writes;
     server binds to the proxy-facing interface only.
  4. **Strip `response_id` from the browser payload**; use an opaque per-deployment segment key
     and map back only at import, locally. Never show `var_id` / `q_no` combinations that reveal
     the branch unless the item has n ≥ k.
  5. Roles: `analyst` (all segments, resolves conflicts), `coder` (assigned sample, blind to
     others' decisions). Assignment server-side.
  6. Keep: no request logging of bodies, `no-store`, strict CSP; add HSTS, session timeout.
  7. Upload/download is a manual analyst step (`hrsurvey review-export` / `review-pull`), so
     the local pipeline stays the source of truth.

### (c) Managed platforms (Vercel, Railway, Fly.io, Render …) with auth

- Privacy/GDPR: a new **processor** (Art. 28 DPA needed) plus usually US-headquartered parent
  companies (third-country transfer analysis, Schrems II/EU-US DPF check). EU regions exist
  (Fly `fra`, Railway EU-West, Render Frankfurt, Vercel functions in `fra1`), but logs,
  build systems and support access may sit elsewhere — must be verified per vendor, in writing.
  Platform-level request logs and edge caches must be disabled or scrubbed for this app.
- Fit: Vercel is serverless — no persistent local file, so the CSV-on-disk model does not work;
  it needs an external DB (another processor). Railway / Fly / Render can run the Python server
  as a container with a persistent volume, closer to today's code.
- Auth: platform password protection is shared-secret, not per-person; per-person needs an
  IdP (company SSO via OIDC, or Auth0/Clerk — yet another processor).
- Effort: medium, ~3–5 days (same code changes as (b)) plus vendor/contract review.
- Cost: ~$5–25/month for container + volume; auth provider free tier or ~$25+/month.
- Additional constraint: these platforms normally deploy from a Git repository; this project
  must **not** go to GitHub for now, so only CLI/image-based deploys would be possible.
- Verdict: technically easy, legally the heaviest of the hostable options for employee survey
  text. Only if the company has no internal hosting and the DPO approves the vendor.

### (d) claude.ai Artifact with a database

- What it would hold: the redacted, translated `text_en` segments and codes, stored in the
  artifact's shared database on Anthropic infrastructure, readable by everyone the artifact is
  shared with.
- Conflict with project rules: D-016 makes the send manifest the **only** path for respondent
  text to leave the machine, and the D-007 approval covers sending redacted answers to the LLM
  API **for coding**, one answer per request, under the API's data-processing terms. Storing the
  whole wave in a consumer/workspace web artifact is a different purpose, a different product
  and data-retention regime, and puts all segments of a respondent side by side in one place.
  It would need its own approval — and would contradict 08 "no copies in … chat tools or shared
  drives".
- Identity/audit: viewer identity is available, but access control, retention, deletion and
  EU-location guarantees are not something this project can configure or prove to a works
  council.
- Effort: low technically (the page is already self-contained HTML). Cost: within the existing
  subscription.
- Verdict: **not acceptable for real survey data.** Acceptable only for a demo with synthetic
  fixtures (as the tests use).

### Comparison

| | Data leaves analyst machine | New processor | Multi-reviewer | Effort | Running cost | Approval burden |
|---|---|---|---|---|---|---|
| (a1) co-review / screen | No (pixels only via meeting tool) | Meeting tool (already approved) | Sequential | none | €0 | Low |
| (a2) LAN bind | Yes, unencrypted | No | Unsafe | tiny | €0 | — not recommended |
| (b) internal + SSO | Yes, inside company | No (own infra) | Yes | ~3–5 d | €0–30 | Medium (DPO + works council) |
| (c) managed platform | Yes, to vendor | Yes (+ auth vendor) | Yes | ~3–5 d + vendor review | $5–50 | High |
| (d) claude.ai Artifact | Yes, to Anthropic web product | Yes, different terms than API | Yes | ~1 d | subscription | Not approvable under current rules |

## 3. What a deployed screen would hold, and minimum safeguards

**Data held** (per segment): `text_en` (translated, redacted answer segment), `theme`,
`secondary_theme`, `new_theme_label`, `locus`, `valence`, `intensity`, `sarcasm`, `actionable`,
`suggestion`, `confidence`, `coder`, `codebook_version`, `review_status`, `reviewer_note`, plus
keys. Never: original-language text, `text_auto`, raw exports, timestamps, scale profiles,
`engagement_band`, segments flagged `sensitive`.

Even redacted, this is **personal data** under GDPR Recital 26 in a small company (08), and may
contain special-category traces the redactor missed. Minimum safeguards:

| Safeguard | Minimum |
|---|---|
| Authentication | Per-person login via company SSO with MFA; no shared passwords, no link-only access |
| Authorization | Named allow-list of reviewers agreed with the works council; analyst role vs. coder role |
| Encryption | TLS everywhere (HSTS); encrypted volume / DB at rest; encrypted backups or no backups |
| Location | EU/EEA hosting, verified for app, DB, logs, backups and support access |
| Minimization | Strip `response_id`; opaque segment keys mapped back only locally; no branch fields; exclude `sensitive` segments; only the wave under review |
| No respondent grouping | UI never lists segments by respondent; shuffle order (consistent with D-014) |
| Concurrency | Per-row writes with version check; no silent overwrites |
| Audit log | Append-only: who, which segment, which field, old → new, when. Retained only until project end, scope agreed with the works council (it monitors reviewers too) |
| Access logging | Login/logout and export events; no request-body or segment-text logging anywhere (app, proxy, platform) |
| Retention & deletion | Instance and data deleted when the wave's review is imported; documented deletion date ≤ project end (08 retention); deletion confirmed in writing for any vendor |
| Exports | Only the analyst can export; export goes back into `data/interim/` locally |
| Incident path | Who to call if the URL or a reviewer account leaks; ability to revoke all sessions at once |

## 4. Recommendation

1. **Now: stay local (a1).** The current screen is safe precisely because it is local. For a
   second opinion, review together at the analyst's machine or via the company's approved
   meeting tool, and note the second coder's verdict in `reviewer_note`.
2. **If a real second coder or HR reviewers become necessary: internal hosting behind company
   SSO (b)**, after DPO and works-council agreement. Do not use managed platforms (c) unless the
   company has no internal hosting and the DPO approves the vendor; never a claude.ai Artifact
   (d) for real data.

### Steps to implement (b) later

1. Write the purpose, reviewer list, data fields, retention date and audit-log scope on one
   page; get DPO and works-council sign-off; add a `DECISIONS.md` entry (D-0xx) superseding
   nothing but extending D-016's "what leaves the machine" to "what leaves it for review".
2. Ask company IT for: an EU VM/container slot, VPN or zero-trust access, an IdP app
   registration, an encrypted volume, and a group containing only the approved reviewers.
3. Code (TDD, synthetic fixtures only): per-row PATCH with version check; SQLite store with
   `decisions` + append-only `audit_log`; identity from proxy header; roles and blind
   assignment; strip `response_id`; config for host/port/allowed group in `config/review.yaml`.
4. Add `hrsurvey review-export --wave W` (local → upload bundle, analyst-approved, like the send
   manifest) and `review-pull` (decisions → local `review_segments.csv`, then `review-import`
   as today).
5. Security review + a test run on synthetic data in the target environment; verify no segment
   text appears in any log.
6. Run the wave; when done, pull, import, and delete the instance data; record the deletion date.
