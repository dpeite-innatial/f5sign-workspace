# Frontend handoff — how an envelope ends: `outcome` apart from `status`, `RELEASED`, and a stricter void

| | |
|---|---|
| **Origin** | branch `feat/task-048-how-an-envelope-ends` (commits after `8cd3424a` on the same branch) — the landed commit brought the retired `VOIDED` status, `outcome`/`end_cause`, the renamed void fields, `RELEASED`/`release_reason`/`released_by`, `ENVELOPE_BUSY`, `RECIPIENT_ACCESS_NOT_RECOVERABLE`; work after it on the same branch brings `expires_at` and `seal_pending_since` on the envelope read, the reset/unlock gate-rule refusal, and the storage funnels re-keyed · [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) (`Proposed`) · [TASK-048](../tasks/TASK-048-what-an-unagreed-envelope-keeps.md) |
| **Date** | 2026-09-28 |
| **Repos affected** | **dashboard** |
| **Nature** | **Breaks the contract.** `EnvelopeStatus.VOIDED` is removed from the enum the dashboard already reads. `voided_at`/`voided_by`/`voided_by_recipient_id`/`void_reason` are renamed. A "Voided" badge built on `status` alone stops matching anything. `POST /envelopes/{id}/void` now seals and is refused earlier (from `agreed_at`, not only from `READY_TO_SEAL`). |
| **Action required** | **Update types before this deploys — this will break silently otherwise.** Read `outcome`/`end_cause` instead of `status === 'VOIDED'`. Rename the four void fields. Add `RELEASED` handling for recipients. Handle `ENVELOPE_BUSY` (503, retryable) on writes. Handle `RECIPIENT_ACCESS_NOT_RECOVERABLE` (409) on reset/unlock. |
| **Deployed** | not yet — not merged into `develop` |
| **Status** | Pending |

**This branch is still being built.** The commit named above landed the status/outcome/end_cause mechanics and the field renames; the gate-rule work on reset/unlock and the envelope's `expires_at`/`seal_pending_since` fields are further work on the same branch, verified directly against the working tree on 2026-09-28. Re-check against the deployment's `doc.json` before building against anything below (workspace `frontend-handoff/README.md` rule 4).

## Changed since the provisional handoff

The provisional draft (`notes/adr-0073-provisional-handoffs/handoff-dashboard-sf-adr0073.md` — written for the `dashboard-sf` integrator, not the dashboard proper, but covering the same envelope/recipient read) described ADR-0073's *text*, before any of it was code. Verified against the tree:

- **`expires_at` and `seal_pending_since` ARE delivered, not pending.** The draft listed `expires_at` (and did not mention `seal_pending_since` at all) as "not published yet." Both are on the envelope read today, confirmed in `EnvelopeJsonPresenter::present()` and in the published `Envelope` schema in `config/packages/nelmio_api_doc.yaml`. `expires_at` is set at send time — when this was written unconditionally 30 days after creation. ⛑ **2026-09-29**: TASK-049 changed that — it is `null` while `DRAFT`, set at send as `sent_at + expires_in_days` (default 30), and extendable; see [TASK-049](TASK-049-integrator-an-envelope-expires.md). `seal_pending_since` is `closed_at` while the envelope is closed and not yet `COMPLETED`, else `null` — new, not in any draft.
- **`RECIPIENT_ACCESS_NOT_RECOVERABLE` is real and already wired**, on both `POST /envelopes/{id}/recipients/{recipientId}/access-code` (reset) and the unlock route — confirmed in both controllers' `#[OA\*]` text. The provisional draft did not name this code by its final spelling.
- **`ENVELOPE_BUSY` (503) is real, with `Retry-After: 2` seconds** — a root-lock writer that waits past its timeout answers this rather than hanging. Confirmed in `EnvelopeLockTimeoutException`. Not mentioned in the provisional draft at all.
- **The reset/unlock refusal rule is NOT `acceptsActs()`, and this was corrected mid-design (ADR-0073's own revision log, 2026-09-28) after the provisional draft was written.** Reset and unlock are refused by the **gate rule** (same rule as reading), not by whether the envelope still accepts acts — so a signer who lost their code **after `COMPLETED`** can still be reset and can still read; only a decliner or a non-informational released member is refused. The draft's text ("this recipient must still be able to pass the access gate") already said this correctly in prose (it quotes the right ADR clause), so there is no correction needed there — flagged only because the underlying ADR clause it cites went through a late revision the draft could not have known about, and the behavior is now confirmed live in code (`ResetRecipientAccessCodeController`, `UnlockRecipientAuthController`).
- **`DECLINE_NOT_OFFERED_IN_QUORUM_STEP` still exists** (relevant to the dashboard only if it renders integrator-facing error catalogs) — unchanged, not retired by this task. ⛑ **2026-09-29**: retired by TASK-050 (`8f42995d`).
- **`envelope.agreed` and `envelope.recipient_released` are event *names* the domain events declare they will be published as, but there is no outbound webhook sender anywhere in this backend.** `src/F5Sign/Webhook/` does not exist; ADR-0064 §6 ("Realized in") reads "Nothing." If the dashboard has any code path that expects webhook delivery, nothing changes for it — it was already receiving none, and still receives none.

## What changed in the contract

**`GET /api/v1/envelopes/{id}` — the envelope:**

| Field | Before | Now |
|---|---|---|
| `status` | included `VOIDED`, `EXPIRED` | `VOIDED` **retired** — no writer produces it, and reading it is now a value you will simply never see. `EXPIRED` is **also removed** (⛑ 2026-09-29, TASK-049): an expiry is `COMPLETED` with `end_cause: EXPIRED` |
| `outcome` | did not exist | new: `AGREED` \| `NOT_AGREED`, null until the envelope ends |
| `end_cause` | `void_cause`: `SENDER_VOIDED`, `RECIPIENT_DECLINED` | **renamed** to `end_cause`; gains `RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED` (none reachable yet — TASK-050's step policy is not built; ⛑ 2026-09-29: TASK-050 has since built it, same branch, not deployed), `EXPIRED` (written by the expiry sweep since TASK-049, 2026-09-29) |
| `voided_at` / `voided_by` / `voided_by_recipient_id` / `void_reason` | as named | **renamed**: `closed_at` / `ended_by` / `ended_by_recipient_id` / `end_reason` |
| `agreed_at`, `completed_at` | did not exist | new, published |
| `expires_at` | did not exist | new, published — **delivered now**, not pending |
| `seal_pending_since` | did not exist | new, published — `closed_at` while closed-and-not-`COMPLETED`, else null |

**`GET /api/v1/envelopes/{id}` — each recipient:**

| Field | Before | Now |
|---|---|---|
| `outcome` | `PENDING, COMPLETED, DECLINED, DELEGATED, SKIPPED` | + `RELEASED`: their leg was open when something closed it without their act |
| `release_reason` | did not exist | new, right after `outcome`: `NOT_REQUIRED`, `INTEGRATOR_NO_ACT`, `OPENED_NO_ACT`, `DELIVERY_FAILED`, `UNCLAIMED`, `NOT_REACHED`, `LINK_EXPIRED`, `SENT_NO_RESPONSE` — both null unless `outcome` is `RELEASED` (⛑ 2026-10-09: two members were added and `NOT_REACHED` now means no recorded fact that the platform reached them; see the TASK-056 handoff) |
| `released_by` | did not exist | new: `STEP_DEADLINE` (not reachable yet), `EXPIRY` (not reachable yet), `SENDER_CLOSED` (not reachable yet — no close-now route exists), `ENVELOPE_CLOSED` (**the only one reachable today** — the envelope closed some other way, with agreement or without it). ⛑ 2026-09-29: all four have writers now — `EXPIRY` (TASK-049), `STEP_DEADLINE` and `SENDER_CLOSED` (TASK-050) |

**`POST /api/v1/envelopes/{id}/void`:**

- Now **seals** every document with bytes on it, asynchronously (as it already did after TASK-046) — unchanged behavior from the last handoff.
- **Refused earlier than before.** Previously refused only from `READY_TO_SEAL` on (`ENVELOPE_REACHED_AGREEMENT`). Now refused from the instant **agreement is secured** (`agreed_at` set), which under `AT_LEAST n` policies can be earlier than `READY_TO_SEAL` — though `AT_LEAST n` steps do not exist yet in this deployment (TASK-050), so in practice, for an `ALL`-only envelope, "every blocking recipient has signed" is still the trigger and the observable timing is effectively unchanged today. ⛑ 2026-09-29: TASK-050 made `AT_LEAST n` authorable (`POST …/steps`), so the earlier refusal is now observable; `StepDeadlineBarsGhHttpTest` pins a void refused `ENVELOPE_REACHED_AGREEMENT` after the first of three consignees signs.

**Reset / unlock** (`POST .../access-code`, the unlock route):

- New 409 `RECIPIENT_ACCESS_NOT_RECOVERABLE` — refused for a decliner or a released member who neither signed nor reads as informational. Works on a `DRAFT` and on a never-opened recipient, as before. A signer, even after `COMPLETED`, and an informational member are never refused.

**Any root-lock write** (act-admission routes, reset, unlock, correction, resend, and the void route itself):

- New 503 `ENVELOPE_BUSY`, `Retry-After: 2` — the write waited too long for the envelope's lock. Retryable.

## What the frontend has to do

1. **Replace any `status === 'VOIDED'` check with `outcome === 'NOT_AGREED'`.** A "Voided"/cancelled badge is now `status: COMPLETED` + `outcome: NOT_AGREED` — it will look like every other `COMPLETED` envelope unless you read `outcome`.
2. **Rename the four fields** wherever they are read: `voided_at`→`closed_at`, `voided_by`→`ended_by`, `voided_by_recipient_id`→`ended_by_recipient_id`, `void_reason`→`end_reason`.
3. **Add a `RELEASED` branch for recipient status.** Today it is reachable only with `released_by: ENVELOPE_CLOSED` — a member whose leg was still open when the envelope closed some other way (an agreement completing, or a void/decline ending it without one). Read `release_reason` to say what is known about them (never opened, opened and did nothing, their invitation never landed, etc.).
4. **Distinguish the two unagreed causes with `end_cause`, not derived state**: `SENDER_VOIDED` vs `RECIPIENT_DECLINED` — same two values as the last (TASK-046) handoff, now living under the renamed field.
5. **Handle `ENVELOPE_BUSY` (503) as a retry-after-2-seconds condition** on every write against an envelope except its creation (`POST /envelopes` takes no lock) — new for every write route, not only void.
6. **Handle `RECIPIENT_ACCESS_NOT_RECOVERABLE` (409)** on reset/unlock — distinct from the write-conflict codes you already branch on.
7. **`expires_at` is real now** — if the dashboard wants to show a countdown or a "expires on" date, it can be read directly; ⛑ 2026-09-29: TASK-049 added `expires_in_days` at creation and `POST /envelopes/{id}/expiry-extensions`; `expires_at` is `null` on a draft. `dashboard-sf` decided to expose neither for now.

## What is NOT ready yet

- ~~**`AT_LEAST n` step policies, veto, and step deadlines** — `end_cause` values `RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED` and `released_by: STEP_DEADLINE` are published in the enum but nothing in the deployed code can produce them yet (TASK-050).~~ ⛑ **2026-09-29**: built by TASK-050 on the same branch (`f48b14e2`), not deployed; see [TASK-050 integrator](TASK-050-integrator-step-policy-and-close-now.md).
- ~~**Expiry as a real deadline**~~ — ⛑ **2026-09-29**: no longer pending. TASK-049 removed `EnvelopeStatus.EXPIRED`, made `expires_at` configurable and extendable, and `released_by: EXPIRY` now happens. See [TASK-049](TASK-049-integrator-an-envelope-expires.md).
- ~~**Close-now (early close by the sender)** — no route exists; `released_by: SENDER_CLOSED` cannot happen yet.~~ ⛑ **2026-09-29**: `POST /envelopes/{id}/close` exists (TASK-050), not deployed.
- **Outbound webhooks of any kind** — confirmed absent from this backend entirely (`src/F5Sign/Webhook/` does not exist). `envelope.agreed`/`envelope.recipient_released`/the widened `envelope.completed` are names the domain events declare for a future sender that does not exist yet.

## How to verify it from the dashboard

Void a `SENT` envelope where nobody has engaged → `204`; `GET /envelopes/{id}` → `status: COMPLETED`, `outcome: NOT_AGREED`, `end_cause: SENDER_VOIDED`, `closed_at` and `completed_at` set together (no seal, since nobody engaged). Void one where a recipient opened their link but did not sign → same status/outcome/cause, but `completed_at` lands later, once the seal of the engaged document arrives; that recipient's `outcome` reads `RELEASED`, `release_reason: OPENED_NO_ACT`, `released_by: ENVELOPE_CLOSED`. Void a `READY_TO_SEAL` envelope → `409 ENVELOPE_REACHED_AGREEMENT`, unchanged from the last handoff. Reset the access code of a recipient who already declined → `409 RECIPIENT_ACCESS_NOT_RECOVERABLE`.
