# Integrator notice — how an envelope ends, on `/v1`

| | |
|---|---|
| **Origin** | branch `feat/task-048-how-an-envelope-ends` (commits after `8cd3424a` on the same branch) — the landed commit brought status/outcome/end_cause, the field renames, `RELEASED`, `EnvelopeAgreed`, the widened `EnvelopeCompleted`, `ENVELOPE_BUSY`, `RECIPIENT_ACCESS_NOT_RECOVERABLE`, `LEG_CLOSED`; work after it on the same branch brings the gate rule on session open/renewal/OTP-send/auth-submit (including `outcome: RELEASED` on the signing-token auth descriptor) and `expires_at`/`seal_pending_since` on the envelope read · [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) (`Proposed`) · [TASK-048](../tasks/TASK-048-what-an-unagreed-envelope-keeps.md) §3.12 |
| **Date** | 2026-09-28 |
| **Repos affected** | any integrator consuming `/api/v1/**`, machine-key or signing-token clients alike |
| **Nature** | **Breaks the contract.** `EnvelopeStatus.VOIDED` is removed. Four envelope fields are renamed. A "voided" branch built on `status` alone will silently misclassify every unagreed ending as a plain `COMPLETED`. |
| **Action required** | Stop branching on `status === 'VOIDED'`; read `outcome`/`end_cause` instead. Rename the four fields. Add `RELEASED` to any recipient-outcome switch. Treat `ENVELOPE_BUSY` (503) as retryable after `Retry-After`, and handle `LEG_CLOSED` (409) on the delegated commit. Do not build against outbound webhooks — none exist. |
| **Deployed** | not yet — not merged into `develop` |
| **Status** | Pending |

**This branch is still being built.** TASK-049 (expiry) and TASK-050 (step policy, release at a step's close, close-now) build after this task, on the same branch, before any of the three deploy. ⛑ **2026-09-29**: TASK-049 (closed at `67626bce`) and TASK-040 (the ending notice, closed at `0aad773b`) have since landed on the branch; TASK-050 has not. Statements below about expiry were corrected in place where they described a state TASK-049 changed. Everything below is what the code on this branch does **today**; several published enum members have no writer yet and are called out explicitly. ⛑ **2026-09-29, later the same day**: TASK-050 has now landed too (merged at `f48b14e2`). Its rows are dated inline below; the current contract is in [TASK-050 integrator](TASK-050-integrator-step-policy-and-close-now.md). In short: `AT_LEAST`/veto/deadlines can be authored, so `RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED`, `released_by: STEP_DEADLINE` and `released_by: SENDER_CLOSED` all have writers; `POST /envelopes/{id}/close` exists; `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` is retired (`8f42995d`); on the signing-token auth descriptor a revoked session whose leg the envelope closed reads `RELEASED`/`DECLINED`, not `REVOKED`, beside a new `envelope_outcome`.

## Changed since the provisional handoff

The provisional draft (`notes/adr-0073-provisional-handoffs/handoff-dashboard-sf-adr0073.md`) was written against ADR-0073's design text before this task had any code — verified line by line against the tree, here is everything that changed or was confirmed:

- **The critical finding stands, unchanged, and is now confirmed in shipped code.** `envelopeStatus()`-shaped code in any integrator that switches on the literal `'VOIDED'`/`'EXPIRED'` will silently misread every unagreed ending as `COMPLETED` the moment this deploys, because `EnvelopeStatus::VOIDED` genuinely no longer exists (confirmed: the enum in `src/F5Sign/Envelope/Contract/Type/EnvelopeStatus.php` has no `VOIDED` case, and its own docblock says so explicitly: *"`VOIDED` was retired by ADR-0073 … do not restore it as a second ending"*). `EXPIRED` was declared in the enum with no writer when this was written; ⛑ **2026-09-29**: TASK-049 has since **removed** it (`EnvelopeStatus` no longer has an `EXPIRED` case; an expiry is `COMPLETED` with `end_cause: EXPIRED`), so a defensive `default` branch for unrecognized statuses remains correct. See [TASK-049](TASK-049-integrator-an-envelope-expires.md).
- **`expires_at` IS delivered, contrary to any reading of the draft that filed it as "not ready."** Confirmed in `EnvelopeJsonPresenter` and the published `Envelope` OpenAPI schema. When this was written it was set at send time as 30 days after creation, unconditionally. ⛑ **2026-09-29**: TASK-049 changed that — it is now `null` while `DRAFT` and set at send as `sent_at + expires_in_days` (1 to 180, default 30, chosen at creation), and `POST /envelopes/{id}/expiry-extensions` extends it. See [TASK-049](TASK-049-integrator-an-envelope-expires.md).
- **`seal_pending_since` is also delivered** — new, not named in the draft at all: `closed_at` while the envelope is closed and not `COMPLETED`, else null.
- **`ENVELOPE_BUSY` (503) and `LEG_CLOSED` (409) are both real, confirmed in the `ProblemCode` catalog and their throwing sites** — neither was named in the provisional draft, which predates them. Both reach machine-key routes, the delegated commit among them; the routes are listed under *ProblemCode catalog* below.
- **`RECIPIENT_ACCESS_NOT_RECOVERABLE` (409) is real**, on the reset and unlock routes — refused for a decliner or a non-informational released member.
- **`envelope.agreed` and `envelope.recipient_released` are NOT delivered as webhooks, and neither is anything else — confirmed decisively, not merely "still dormant."** The draft's §8 already flagged `SignatureWebhookReceiver.php` as unwired on the `dashboard-sf` side and got that right. What is new here: on the **backend** side, there is no outbound webhook sender of any kind. `ls src/F5Sign/` names seven bounded contexts and no `Webhook`; ADR-0064's own §5/§6 ("Enforced by" / "Realized in") read, verbatim, *"Nothing. There is no code, no rule and no test"* and *"No `src/F5Sign/Webhook/` tree exists."* Every event name below (`envelope.agreed`, `envelope.recipient_released`, the widened `envelope.completed`, `envelope.voided`) is a name a domain event's docblock declares it *would* be published as, once ADR-0064 is realized — not a name anything sends today, over any transport, to anyone. If your integration polls (as the reference `dashboard-sf` integration does, per the draft's own measurement), nothing here changes that story; if it is waiting on webhooks, it was already waiting on nothing, and still is.
- **The void refusal boundary moved earlier than `READY_TO_SEAL`, confirmed, but with no observable effect for an `ALL`-only workflow.** `POST /envelopes/{id}/void` is refused from the instant `agreed_at` is set (agreement secured), which under an `AT_LEAST n` step can be earlier than `READY_TO_SEAL`. No `AT_LEAST n` step can be authored yet (TASK-050), so for every envelope buildable today the observable trigger is unchanged: every blocking recipient has signed. ⛑ 2026-09-29: TASK-050 made `AT_LEAST n` authorable (`POST …/steps`), so the earlier refusal is now observable; `StepDeadlineBarsGhHttpTest` pins a void refused `ENVELOPE_REACHED_AGREEMENT` after the first of three consignees signs.
- **The reset/unlock refusal rule is the gate rule, not `acceptsActs()` — this was a late correction inside ADR-0073's own drafting (2026-09-28) and the draft's prose already matched the corrected version by citing the right clause**, so there is nothing to fix in the draft's wording; flagged only so nobody re-derives the older, stricter rule from the ADR's revision history.
- **`DECLINE_NOT_OFFERED_IN_QUORUM_STEP` is still live** — unaffected by this task; retirement is TASK-050's. ⛑ **2026-09-29**: retired by TASK-050 (`8f42995d`).

## What changed in the contract

### Envelope (`GET /api/v1/envelopes/{id}`)

| Field | Before | Now |
|---|---|---|
| `status` | included `VOIDED` | **retired, no writer** — every ended envelope, agreed or not, is `COMPLETED`. `EXPIRED` is **removed** too (TASK-049): an expiry is `COMPLETED` with `end_cause: EXPIRED`. |
| `outcome` | did not exist | new: `AGREED` \| `NOT_AGREED`. Open enum — an unrecognized future value should read as "not fully agreed." |
| `end_cause` | `void_cause`: `SENDER_VOIDED`, `RECIPIENT_DECLINED` | **renamed** `end_cause`. Adds `RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED` (all TASK-050, no writer yet — ⛑ 2026-09-29: TASK-050 has since given all four a writer) and `EXPIRED` (TASK-049, written by the expiry sweep). Null when `outcome` is `AGREED`. |
| `voided_at` / `voided_by` / `voided_by_recipient_id` / `void_reason` | as named | **renamed**: `closed_at` / `ended_by` / `ended_by_recipient_id` / `end_reason` |
| `agreed_at` | did not exist | new — when agreement was secured, which can be **before** the envelope closes (pending members may keep acting) |
| `completed_at` | did not exist | new — when the lifecycle actually ended |
| `expires_at` | did not exist | new, delivered — `null` while `DRAFT`; at send, `sent_at + expires_in_days` (TASK-049; was creation + 30 days) |
| `seal_pending_since` | did not exist | new, delivered — `closed_at` while closed-and-not-`COMPLETED` |

### Recipient (inside the same envelope read)

| Field | Before | Now |
|---|---|---|
| `outcome` | `PENDING, COMPLETED, DECLINED, DELEGATED, SKIPPED` | + `RELEASED` |
| `release_reason` | did not exist | new: `NOT_REQUIRED`, `INTEGRATOR_NO_ACT`, `OPENED_NO_ACT`, `DELIVERY_FAILED`, `UNCLAIMED`, `NOT_REACHED`, `LINK_EXPIRED`, `SENT_NO_RESPONSE` (⛑ 2026-10-09: two members were added and `NOT_REACHED` now means no recorded fact that the platform reached them; see the TASK-056 handoff) |
| `released_by` | did not exist | new: `STEP_DEADLINE` (no writer yet), `EXPIRY` (no writer yet), `SENDER_CLOSED` (no writer yet — no close-now route), `ENVELOPE_CLOSED` (**the only reachable one today**). ⛑ 2026-09-29: all four have writers now — `EXPIRY` (TASK-049), `STEP_DEADLINE` and `SENDER_CLOSED` (TASK-050) |

### ProblemCode catalog (`/v1`, cross-cutting)

- **`ENVELOPE_BUSY`** (503, `Retry-After: 2`) — a write waited too long for the envelope's root lock to admit an act. Retryable after the delay. Declared (as the shared `ServiceUnavailable` response) on every route whose request waits for that lock synchronously — 17 routes, not 20 (see below for the three that dropped off):
  - machine key: `POST /envelopes/{id}/documents`, `/documents/{documentId}/content`, `/steps`, `/recipients`, `/fields`, `/document-assignments`, `/send`, `/void`, and on `/recipients/{recipientId}/`: `corrections`, `access-code`, `auth-unlock`, `resends`, `claim`, `signing-assignments`, `signature` (the delegated commit) — the 14 Envelope write routes (every write except creation, which takes no lock) plus the delegated commit;
  - signing token / session credential: `POST /signing/commit`, `POST /signing/decline`.

  Envelope creation, reads, token minting, OTP sends and credential renewal wait for no envelope lock and never declared it. **Session open, auth submit and the machine-key relayed gate answer no longer declare it either** — `POST /signing/session`, `POST /signing/session/auth` and `POST /envelopes/{id}/recipients/{recipientId}/auth` dropped off this list: the gate's opening write (`recordOpening()`, in `EnvelopeCommandAdapter`) used to refuse with this 503 when it timed out on the recipient's row lock, but now it swallows `EnvelopeLockTimeoutException` and simply records nothing — the gate's opening write never refuses the gate. The relay-borne twin of the opening fact lands later if the envelope is still open. So none of those three routes can answer 503 any more; retry logic built against the earlier ("four signer routes" / 20-route) version of this handoff should drop them.
- **`LEG_CLOSED`** (409) — the envelope is still open, but this recipient's own part in it is already over: an act of theirs was already admitted, or their leg was released without one (a closed envelope answers `ENVELOPE_NO_LONGER_LIVE` instead, ahead of it). Reachable on the signing-token session open (`POST /signing/session`), on the recipient's own commit and decline (`POST /signing/commit`, `POST /signing/decline`), and **on the machine-key delegated commit, `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature`**: the act is admitted on the envelope under its lock, and the admission refuses a closed leg ahead of the step, the deadline and the answers themselves, so it also answers ahead of `FIELD_VALUES_INVALID` (422). Terminal for that recipient: do not retry, and do not wait for it to lift as you would for `STEP_NOT_ACTIVE`.
- **The signing-token auth descriptor (`GET /api/v1/signing/session/auth`) gains `outcome: RELEASED`**, alongside its existing `COMPLETED`/`DECLINED`/`REVOKED` — published even when the recipient never opened a session. Relevant only to a caller that reads the recipient's own auth descriptor on their behalf (e.g. relaying an OTP for a `SIGNING_PLATFORM` recipient); the sender-facing envelope read's recipient `outcome` (the table above) already had `RELEASED` since the landed commit and is unaffected by this.
- **`RECIPIENT_ACCESS_NOT_RECOVERABLE`** (409) — reset/unlock refused for a recipient who can no longer pass the access gate (a decliner, or a released non-informational member).
- **`DECLINE_NOT_OFFERED_IN_QUORUM_STEP`** — still in the catalog, still emitted by the recipient-facing decline route. Not retired by this task. ⛑ **2026-09-29**: retired by TASK-050 (`8f42995d`); no longer in the catalog.

### `POST /api/v1/envelopes/{id}/void`

- Still seals every document with bytes, asynchronously — unchanged since TASK-046.
- Refusal boundary (`ENVELOPE_REACHED_AGREEMENT`) moved from `READY_TO_SEAL` to `agreed_at` (agreement secured) — see above for why this has no observable effect yet on an `ALL`-only workflow, which is everything buildable today.

### Events / webhooks

- **Confirmed: nothing is delivered as a webhook, at all, by this backend, today.** No exceptions, no partial rollout. `envelope.agreed` (fact: `EnvelopeAgreed`) and `envelope.recipient_released` (fact: `RecipientReleased`) are the names their domain events' docblocks declare for a future publisher. `envelope.completed`'s meaning is declared to widen — carrying `outcome` for both endings rather than only agreements — but that widening, too, only matters the day a webhook sender exists.
- If and when outbound webhooks are built, plan for: `envelope.completed` firing for **both** outcomes (read `outcome`, never assume the name alone means "agreed" — an old-shaped payload with no `outcome` key would mean `AGREED` under the additive versioning rule the event declares); `envelope.voided`'s payload keeping its existing key names (`void_cause`, `voided_by`, `voided_by_recipient_id`) even though the envelope's own fields renamed, and its party fields becoming nullable for an ending nobody decided (not reachable yet, since expiry has no writer); two new names, `envelope.agreed` and `envelope.recipient_released`.

## What is NOT ready yet

- ~~**`AT_LEAST n` steps, veto, step deadlines** — the four related `end_cause` values and `released_by: STEP_DEADLINE` are declared, not reachable (TASK-050).~~ ⛑ **2026-09-29**: built by TASK-050; see [TASK-050 integrator](TASK-050-integrator-step-policy-and-close-now.md).
- ~~**Real expiry**~~ — ⛑ **2026-09-29**: no longer pending; TASK-049 made `expires_at` configurable (`expires_in_days`), extendable, and closing (`released_by: EXPIRY`, `end_cause: EXPIRED`). See [TASK-049](TASK-049-integrator-an-envelope-expires.md).
- ~~**Close-now** — no route exists; `released_by: SENDER_CLOSED` unreachable.~~ ⛑ **2026-09-29**: `POST /envelopes/{id}/close` exists (TASK-050).
- **Any outbound webhook delivery whatsoever** — confirmed absent, see above.
- **API versioning** — this is `/v1` changing in place, before production, per ADR-0073 §2.18 and BL-59; there will be no `/v2` for this change.

## What will NOT exist, and why

- **An `EnvelopeStatus.VOIDED` or `.EXPIRED` value that a writer ever produces again.** ADR-0073 §2.5's whole point is separating the phase (`status`) from the result (`outcome`/`end_cause`); reintroducing a second terminal status would undo the decision the rest of this record exists to make. ⛑ **2026-09-29**: `EXPIRED` has since been removed from the enum (TASK-049), which settles the point.
- **A `ProblemCode` per `end_cause`.** The void and (eventually) close-now refusals keep answering with the same `ENVELOPE_REACHED_AGREEMENT`/bare-`CONFLICT` shape as today; the fine-grained cause lives in the envelope's `end_cause` field, not in the error code — exactly as `void_cause` never had one either.

## How to verify it from an integrator

Before writing code against any of this: the deployment's `doc.json` has to list `outcome`, `end_cause` (not `void_cause`), `release_reason` and `released_by` on the `Envelope`/`Recipient` schemas, and the `status` enum must no longer carry `VOIDED`. If it still does, that deployment predates this task. Then: void a `SENT` envelope with a blocking recipient's decline instead (once reachable) or by the sender directly → `status: COMPLETED`, `outcome: NOT_AGREED`, `end_cause` naming the concrete cause — never let an unupdated `envelopeStatus()`-style mapper read that as a plain `COMPLETED`. A recipient whose step never got a chance to act before the envelope closed → `outcome: RELEASED`, `release_reason`, `released_by: ENVELOPE_CLOSED` — never `PENDING`.
