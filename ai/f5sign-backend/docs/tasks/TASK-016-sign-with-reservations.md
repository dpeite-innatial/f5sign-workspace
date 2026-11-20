# TASK-016 — Sign with reservations (eCMR attest-with-exception)

<!-- OFFREPO: design-trail cross-refs are native design vocabulary, not followable from the tree — the "Factor5 finding" + inv 26 (backend `docs/ddd/envelope-domain-model.md`, design repo `01 - Envelope and Workflow BC.md §7`), the CMR Convention (Art. 8 carrier reservations; consignee reservations-on-delivery), and TransFollow's observation-on-signature feature. -->

| Field | Value |
|-------|-------|
| **Status** | **✅ Merged to master** (`feat/ecmr-reservations`, backend-only). `make qa` green (PHPStan L9 · Deptrac 0 · lint · full suite). |
| **Type** | Forward build — an **optional free-text reservation** a signer attaches at commit time, riding along with their `COMPLETED` outcome as evidence. |
| **Why** | The eCMR *carta de porte* is an **attestation** document, not a consensus one. A destinatario receiving damaged/wrong cargo does **not** decline — under the CMR Convention they **sign to acknowledge delivery** and **note reservations** ("recibí con incidencias"); the signature completes the leg and the reservation is recorded as evidence (often the key dispute evidence). This is exactly how the transport-domain platforms (TransFollow) model it, and unlike generic e-sign (DocuSign/Adobe), where any decline voids the whole envelope. |
| **Decision record** | Rides the existing sign path (ADR-0024/0027 choreography, ADR-0031 event log, ADR-0008 read side). **No new ADR, no lifecycle change, no inv-26 reopening** — a reservation is an *annotation on a completion*, so the state machine and step-completion predicate are untouched. |

---

## 1. The model (locked in design discussion 2026-07-08)

A reservation is an **annotation on a `COMPLETED` recipient**, captured atomically at the signing act. Consequences of that framing:

- **Outcome is unchanged** — the recipient still ends `RecipientOutcome::COMPLETED`; "with exception" is *derived* from `reservations != null`. No new enum value, no `RecipientOutcome`/D5 change, no step-completion-predicate change. *(The Factor5 note floated a distinct `ATTESTED_EXCEPTION` outcome — rejected here: under the sign-with-reservations framing a nullable field is cleaner and touches nothing.)*
- **Multi-recipient steps are the easy case.** Each recipient (each destination in a multi-drop) completes independently; a reservation on one imposes nothing on the others; the step closes by the existing all-terminal predicate. The design effort is in the **evidence model** (capture + roll-up), not lifecycle. Steps are **all-required, non-quorum** (destinations are non-interchangeable — quorum does not model them), so no inv-16 evaluator wiring is needed.
- **Available to any signer** (not gated by role) — the carrier reserves at pickup (CMR Art. 8), the consignee at delivery; any recipient may attach a reservation at their own commit.

## 2. The chain (Session BC → Envelope BC) — thread an optional `?string $reservations`

The reservation is captured in the ceremony and flows the existing sign path unchanged; every hop below just gains one optional param / payload key:

`CommitSignatureRequest` → `CommitSignature` cmd → `SigningSession::commitSignature` (stored field, parallel to consent/ip/ua) → **`SignatureCommitted`** (the AuditableEvent — reservation belongs in `payload()`, the evidence subset, + `toPayload()`) + **`SessionCompleted`** (`toPayload()`) → `OnSessionCompleted` reactor → `RecordRecipientCompletion` cmd → `Envelope::recordRecipientCompletion` → `Recipient::markCompleted` (stored field) → **`RecipientCompleted`** (`toPayload()`) → read view/repo/presenter.

**Storage (three places, mirroring how consent/ip/ua + void-metadata are handled):**
- `signing_session.reservations` (TEXT, nullable) — the ceremony record (parallels `signer_user_agent`).
- `recipient.reservations` (TEXT, nullable) — the envelope read model.
- the **event log** — `SignatureCommitted`/`SessionCompleted`/`RecipientCompleted` payloads (system of record + the evidence itself).

One migration adds both columns, sorting after the migration that created the table it extends. (The
original anchor named here, `Version20260708000001`, no longer exists — it was consolidated into the
four `Version20260713*` baselines by ADR-0018's Phase-A clean-baseline rewrite, so the ordering
constraint is stated as a property rather than pinned to a version that cannot be looked up.)

**⚑ Forward-compat (found + fixed during build).** Adding `reservations` to an event payload means rows appended *before* this change lack the key. `Row::nullableString` throws on an absent key (by design, for required columns), so reconstructing a pre-existing `SessionCompleted`/`SignatureCommitted`/`RecipientCompleted` via `fromPayload()` would throw — a poison event on any floor-read / replay / projector rebuild (surfaced by `EventRelayTest`'s first-run-from-floor path against the append-only log). Fix: a new tolerant accessor **`Row::optionalString`** (absent key → null, like a present-null) used for `reservations` in all three `fromPayload()` methods. This is the reusable pattern for **any additive event-payload field** going forward; a breaking change would instead bump `schema_version`.

## 3. Surfacing

- Recipient read view (`RecipientView` + `loadRecipients` + presenter `recipient()`) gains `reservations`; OpenAPI `Recipient` schema gains the field.
- **Envelope-level `has_reservations` rollup** (derived in the presenter — true if any recipient has reservations) for the dashboard "this shipment has exceptions" signal. *Optional / cuttable at review; no storage.*
- Normalize empty/whitespace `reservations` → `null` at the edge (a clean signature is `null`, not `""`); bound the length (`Assert\Length`, ~2000).

## 4. Deferred

- **Rendering reservations into the sealed carta-de-porte PDF** (the visual reservations box per consignee) — pairs with the sequential-PAdES work (queue #2), which owns the per-signer incremental signature the reservation would render beside.
- **Attachments** (photo/file) + **per-good association** (TransFollow "Good Indicate") — richer evidence; text-only for MVP.
- A true **decline-to-participate** (refuse to sign, records-and-continues) — the separate decline-disposition that *would* reopen inv 26; only needed if a destinatario can refuse outright. Not this task.

## 5. Verification

- `make qa` green.
- Migration applies + reverses on a scratch DB.
- Unit: `commitSignature` captures the reservation; both session events carry it.
- Serialization round-trip (`SessionCompleted`/`SignatureCommitted`/`RecipientCompleted`) with and without a reservation.
- HTTP/scenario: a signer commits with a reservation → GET envelope shows it on that recipient + `has_reservations: true`; a clean signer → `reservations: null`.
- Multi-recipient step: two recipients, one with a reservation → both `COMPLETED`, step closes, each recipient's reservation independent.
