# TASK-046 — A recipient may decline, and an envelope that ends without agreement is sealed

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/recipient-decline` (`c1427b8`), 2026-09-23 — suite green under the worktree lane `wt-backend`.** Last full green run `fc33045` (3367 tests / 19177 assertions, all tiers, plus lint/deptrac/phpstan) — `c1427b8` on top is docs-only, so it inherits that run's tree unchanged. Infection at `fc33045`: covered-MSI 83% (floor 79), MSI 57% (floor 50). Merged into `develop` at `26ed0d7` on 2026-09-23 after a full run of every tier on the merged tree (`0f0af1b`: 3367 tests / 19176 assertions, lint/deptrac/phpstan clean); not pushed, not deployed. **Two declared deviations** (§7): the delivery bar's `CERTIFIED_DELIVERY` non-blocking-continues case and the "other live sessions revoked" half are held one tier down, and the decline act and the annulment seal share one commit (`f29c673`). **ADR-0070 is `Accepted (exercised)`**, promoted by the maintainer on 2026-09-23; its §5/§6 name the artifacts that exercise it. ⛑ A first cut of this record, on 2026-09-22, ended a declined envelope in `EnvelopeStatus::DECLINED` and left it unsealed; the maintainer re-cut it (§4 D1, D5) before any code. |
| **Type** | **Forward build**, with one retirement. A recipient gains the act of declining (`RecipientOutcome::DECLINED`, published for weeks and written by nothing). An envelope that ends without agreement — voided by its sender, or ended by a blocking recipient's decline — ends in **`VOIDED`**, and `VOIDED` becomes a binding end: the document is sealed as it stands, invisibly and with no statement in the PDF (DSS 6.4's REST interface cannot write a `/Reason`), and its evidence is kept like a completed signature's. `EnvelopeStatus::DECLINED` is retired. |
| **Why** | A recipient cannot refuse. The signer hides its *Rechazar* button against the real backend because `…/decline` answers 404 — until 2026-08-18 the button was shown, failed after the tap, and left the signer believing they had declined ([BL-142](../BACKLOG.md)). And an envelope that ends without agreement leaves nothing sealed: if the third of five signers walks away, the first two signatures exist and would be needed in a dispute, but no act of the platform closes and attests that state. *"Rechazar una firma debería tener la misma validez legal y en el tiempo que haber firmado"* (maintainer). |
| **Builds on** | Reused unchanged: [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) (the two gates) and [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) (the session credential) · [ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md) (no recipient acts before their step — a decline is an act) · [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) (a refusal names its condition) · [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) (`terminalOutcome()` is where a new terminal declares itself) · [ADR-0061](../adr/ADR-0061-retention-deletion-and-purge.md) (conservation is resolved at SEND, whatever the ending) · [ADR-0062](../adr/ADR-0062-stage-then-promote.md) §2.4 (promotion asks whether a signature exists; `voided_at` and a `SEAL` artifact are already legs of it). Amended: [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) (§4 D5b). |
| **Scope** | The recipient's own decline on the session credential; its effect on leg, step and envelope; `VOIDED` gaining a cause and a seal, for both of its causes; the read side; the retirement of `EnvelopeStatus::DECLINED`. Out of scope, each with its reason in §4 or §6:<br>• a **delegated** decline by the integrator (§4 D2b);<br>• decline inside a **quorum** step (§4 D1c);<br>• the **evidence documents** — the envelope's rejection evidence belongs to the audit-trail work (§4 D9a); the per-signer evidence document is TASK-047;<br>• **notifications** (§4 D7 — TASK-040);<br>• undoing a decline, and replacing a recipient (§4 D6);<br>• how the Factor5 waybill *uses* decline against reservations (§4 D8).<br>**The `f5sign-signer` and integrator changes are not in this repository**: this task writes their handoffs. |
| **Decision record** | **[ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md), drafted `Proposed` on 2026-09-22 before implementation**; its text was approved by the maintainer on 2026-09-23 as the go-ahead. This task exercises it (§5/§6 of the ADR name the artifacts), and the maintainer promoted it to **`Accepted (exercised)`** on 2026-09-23. It carries: an envelope ends either in agreement (`COMPLETED`) or without it (`VOIDED`, with a cause), and both are sealed (§4 D1, D5); the retirement of `EnvelopeStatus::DECLINED`; the amendment to ADR-0059 (§4 D5b); and a **conscious exception to [`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §2** — the decline reason rides the event log in plaintext (§4 D3), as `reservations` does under [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md) §3.2 and [BL-275](../BACKLOG.md). Its number was derived by grep at the moment it was written. |
| **Delivery bar** | Over HTTP, five blocking signers under `SEQUENTIAL_PADES`: two sign, the third passes their gate and declines with a reason → 200. Then `GET /api/v1/envelopes/{id}` shows `status: VOIDED`, `void_cause: RECIPIENT_DECLINED`, `voided_at`, `voided_by_recipient_id`, and on the third recipient `outcome: DECLINED`, `declined_at`, `decline_reason` and the authentication method; the other live sessions are revoked; `…/documents/{id}/sealed` serves the PDF carrying both signatures plus the platform seal, one invisible platform seal added, and neither the decliner's name nor the reason anywhere in the PDF; recipients one to three can download it and four and five cannot. A sender's `void` of another envelope produces the same seal with the sender's wording and `void_cause: SENDER_VOIDED`; a `void` of an envelope at `READY_TO_SEAL` is refused by name. On a non-blocking recipient (`CERTIFIED_DELIVERY`) a decline closes only their leg and the envelope completes without them. |
| **Sibling** | **TASK-047** (per-signer evidence document), blocked on the audit trail. **TASK-040** (the notice that an envelope ended without agreement), which tells every invited recipient of a decline or a void, worded by cause. **TASK-045** (browser-reported evidence) — if it lands first, the decline records the same evidence as the commit. **The audit-trail work** on `feat/evidence-audit`, which produces the envelope's evidence document for a `VOIDED` end (§4 D9a). **Ordering: this task does not wait for it.** It emits the facts that work will read; until that branch lands, a `VOIDED` envelope has its annulment seal and no evidence document, and the decline reason is readable only on the read side. |

---

## 1. Why this task exists

The platform models refusal everywhere except where it happens, and it models an ending without agreement as
something that leaves no sealed trace. `RecipientOutcome::DECLINED` is terminal and written by nothing; the
signer session's read-model publishes `outcome: DECLINED` ahead of any writer; `Step::declinedCount` is
incremented by nothing. And `Envelope::void()` moves the envelope to `VOIDED` and revokes sessions, but seals
nothing: the partially signed document of a voided envelope is attested by no act of the platform.

## 2. What already exists (reuse, do not rebuild)

- **Void.** `Envelope::void()` moves `SENT`/`READY_TO_SEAL` to `VOIDED`, records
  `EnvelopeVoided{envelopeId, tenantId, voidedBy, reason, occurredAt}`; `OnEnvelopeVoided` revokes every live
  session through `SigningSession::revoke()`. The guarantee is the synchronous envelope-status guards on the
  Session routes, not that reactor (LOAD-BEARING §1.16). A recipient of a voided envelope stays `PENDING`.
- **Sealing.** Only on completion: `markReadyToSeal()` records `EnvelopeReadyToSeal`, SignatureExecution seals
  through EU DSS, `complete()` records `EnvelopeCompleted`. Our signatures carry no DocMDP certification, so an
  incremental revision after them leaves them valid.
- **Conservation** is resolved at SEND (`envelope_conservation_on_send_chk`, ADR-0061), so a `VOIDED` envelope
  is conserved on the tenant's ordinary clock already. **Promotion** (ADR-0062 §2.4) already has a `voided_at`
  leg and a `SEAL` leg.
- **Step closure.** `StepCompletionEvaluator`: a non-quorum step closes when every **blocking** member is
  completion-terminal (`Role::isBlocking()`: `SIGNER`, `APPROVER`, `IN_PERSON_HOST`). Quorum steps cannot be
  authored: `min_signatures` is presented and accepted by no write route.
- **Document withholding.** `EnvelopeStatus::withholdsDocumentFromRecipient()` withholds on `VOIDED` from every
  recipient (ADR-0059).
- **`EnvelopeStatus::DECLINED`** is declared, classified in `isTerminal()` and `withholdsDocumentFromRecipient()`,
  published, pinned by `EnvelopeStatusTest`, and written by nothing.
- **BL-142 already classified the route:** `…/decline` takes the **session credential**, like the commit.
- **The audit trail** on `feat/evidence-audit` models an envelope's end as `Completed|Voided`; `Voided` carries
  position, instant, actor, reason, sessions closed and who signed before. It renders PDF/A-3a and adds a
  contract port to seal a PDF from another context. Not on `develop` on 2026-09-22.

## 3. What gets built

1. **Route.** `POST /api/v1/signing/decline`, `Authn::SESSION_CREDENTIAL`, body `{ "reason": string }`. The
   signer's docs-future `DeclineRequest` also carries `session_id`; the credential already names the session, so
   the body does not, and the handoff says so.
2. **Session.** `SessionStatus::DECLINED`, a terminal case, classified in `admitsSigning()`, `isAuthenticated()`
   and `terminalOutcome()`. `SigningSession::decline()` with the commit's guard order: terminal session → named
   refusal; gate not passed → refusal (§4 D4); envelope not live → `ENVELOPE_NO_LONGER_LIVE`; step not active →
   `STEP_NOT_ACTIVE`. No consent is asked. Records a decline fact carrying the reason (§4 D3).
3. **Preconditions refused by name, never 404** (§4 D2): a role that may not decline; a quorum step (§4 D1c).
4. **Crossing into Envelope.** The decline fact → a use case recording the leg (outcome `DECLINED`,
   `declined_at`, `decline_reason`, `step.incrementDeclinedCount()`) and, for a blocking recipient, voiding the
   envelope with cause `RECIPIENT_DECLINED`.
5. **`VOIDED` gains a cause.** `void_cause`: `SENDER_VOIDED` | `RECIPIENT_DECLINED`, and the voiding party: the
   sender's actor, or the declining recipient. `EnvelopeVoided` carries both. The sender's route keeps its shape,
   and **`void()` stops accepting `READY_TO_SEAL`** (§4 D5e): a named refusal where it used to void.
6. **`VOIDED` is sealed.** `EnvelopeVoided` starts the sealing of each document as it stands: an incremental
   PAdES revision by the platform seal over whatever signatures it holds (under `SINGLE_SEAL`, over the
   original). The seal is invisible and writes **no `/Reason`**: the same seal parameters as the completion
   (§4 D5a). ⛑ This step first asked for a `/Reason`, measured before building; DSS 6.4's REST interface
   refused it (HTTP 500 *Unrecognized field "reason"*) and the maintainer chose no statement (ADR-0070 §2.5,
   BL-281). Recorded as
   a `SEAL` artifact, so promotion takes it through the existing leg. It does **not** record `EnvelopeCompleted`.
   A failed seal fails **as the completion seal does today**: retried, then parked on the `failed` transport for
   an operator to replay. No failure fact or status is added — `SEALING_FAILED` is written by nothing, and
   client-visible seal failure is BL-15's, for both seals. Until the seal lands, recipients are refused the
   sealed document by name.
7. **Who reads the sealed PDF** (§4 D5b): the sender; recipients whose outcome is `COMPLETED` or `DECLINED`. A
   recipient who never acted is refused.
8. **Retire `EnvelopeStatus::DECLINED`** (§4 D1e): the case, its classifications, `EnvelopeStatusTest`'s pins,
   the published enum, and every prose surface naming it (authoring rule 1 — `rg -n 'DECLINED'` read case by
   case, since `RecipientOutcome::DECLINED` stays).
9. **Read side** (§4 D9b). Envelope: `void_cause`, `voided_at`, `voided_by_recipient_id`. Recipient:
   `declined_at`, `decline_reason`, the authentication method executed at the decline. `#[OA\*]` strings saying
   *"decline is not built on the write side"* are rewritten.
10. **Handoffs:** signer (the button, the confirmation step, the refusal codes, the new terminal) and integrator
    (`void_cause`, the recipient fields, that **an existing `void` now seals**, and that it is **refused at
    `READY_TO_SEAL`** — two behaviour changes on a live route). A note to the audit-trail work (§4 D9a).

## 4. Key decisions (maintainer, 2026-09-22)

- **D1 — A decline closes the recipient's leg; the envelope ends only when it must, and then it ends `VOIDED`.**
  *"Hay que verlo con calma para hacerlo bien."*
  - **D1a — A blocking recipient declines → the envelope is voided**, cause `RECIPIENT_DECLINED`. Their step can
    never close, so continuing would leave the envelope waiting for ever. Skipping them (`SKIPPED`) was rejected:
    it would make *blocking* optional at one click.
  - **D1b — A non-blocking recipient declines → their leg is `DECLINED` and the envelope continues.**
  - **D1c — Quorum steps: the rule is written, the build is deferred.** For later: a decline that leaves the
    quorum unreachable voids the envelope at once; otherwise it is recorded and the step goes on. Until quorum
    steps can be authored, a decline inside one is refused by name.
  - **D1d — When the envelope is voided, every other live session is revoked**, through the existing path.
  - **D1e — `DECLINED` is a recipient's outcome, never an envelope's.** An envelope ends in agreement or
    without it; *who* ended it is the cause, not a second status. ⛑ The first cut ended a declined envelope in
    `EnvelopeStatus::DECLINED`; the maintainer re-cut it so that both endings without agreement share one
    binding path. `EnvelopeStatus::DECLINED`, which nothing ever wrote, is retired rather than left as a
    published member that never occurs.
- **D2 — Who may decline.** `SIGNER`, `APPROVER`, `CERTIFIED_DELIVERY`: **yes**. `REVIEWER`, `IN_PERSON_HOST`:
  **deferred** (each needs its own meaning). `VIEWER`, `EDITOR`: **no**. Deferred and no are the same on the
  wire — a named refusal.
  - **D2b — No delegated decline in this task.** For the waybill, a cargador who will not sign is a cancelled
    transport, and the integrator already has `void`. ⚑ **The delegated decline is the normal case for other
    flows** (maintainer): §6's first follow-up, not a rejected idea.
- **D3 — The reason is mandatory free text, and it rides the event log.** Its own member (`decline_reason`),
  treated exactly as `reservations`: plaintext in the decline fact's payload. *"Sería exactamente igual que las
  reservas… El día de mañana se cifrará todo."* ⚠ A **conscious exception to LOAD-BEARING §2**, beside ADR-0069
  §3.2: the log cannot be rewritten, so enciphering later reaches only rows written after it; BL-275 resolves
  the two together. Rules as the fields': no control characters, blank refused, at most 500 characters.
- **D4 — Only after the identity gate**, as for signing. A blocking decline ends an envelope irreversibly; before
  the gate, anyone holding a forwarded link could end someone else's envelope.
- **D5 — An envelope that ends without agreement is binding, and is kept and proved like a signature.**
  - **D5a — Seal what there is; the platform, not the PDF, says it was annulled.** Two of five signatures are evidence a dispute needs,
    so the document is sealed as it stands, **invisibly and with no statement in the PDF**. The annulment is
    stated by the platform — `VOIDED` with its cause on the read side — and, once the audit trail lands, by the
    evidence document; no name and no reason ever enter the PDF. ⛑ Re-cut twice on 2026-09-23. The first text
    named the recipient in `/Reason` and drew a visible mark; the maintainer dropped the mark (nowhere safe to
    go — over content on an existing page, or on an added page validators report as a post-signature
    modification) and the name (an opaque id instead) (ADR-0070 §7.7, §7.8). Then the measurement in §3 #6
    found DSS 6.4's REST interface cannot write a `/Reason` at all, and the maintainer chose no statement over
    customising DSS, a CMS attribute or the mark (ADR-0070 §7.10–§7.12). Writing it later is BL-281. ⚠ Until
    the evidence document exists, the PDF alone cannot tell an annulment from a completion.
  - **D5b — Who may read it: the sender, and the recipients who acted** — those who signed and the one who
    declined. A recipient who never acted may not. This amends ADR-0059, which withholds from every recipient
    of a `VOIDED` envelope.
  - **D5c — Conservation needs nothing new**: it is resolved at SEND for every ending, and the `SEAL` artifact
    promotes through the existing leg.
  - **D5d — This applies to the sender's `void` too**, which today seals nothing. The behaviour of a live route
    changes; the integrator's handoff says so.
  - **D5e — The sender cannot void an envelope at `READY_TO_SEAL`** (maintainer, 2026-09-23). Every blocking
    recipient has signed, so it has reached agreement (D1e). It also closes a race live today: the completion
    sealer runs at `READY_TO_SEAL` (`SEALING` is written by nothing), so a `void` between the completion seal's
    append and `complete()` leaves a `VOIDED` envelope carrying a completion seal — and, with D5, an annulment
    seal on top of it. `void()`'s docblock, which excludes `SEALING` *"to avoid racing the sealer"*, is
    rewritten with it (authoring rule 1). The integrator's handoff says so.
- **D6 — Irreversible.** Terminal like a signature; to retry, the sender creates a new envelope. The signer asks
  for an explicit confirmation before calling the route; replacing a recipient is a follow-up (§6).
- **D7 — This task sends no notification.** TASK-040's ending notice covers both causes, worded by cause — a decline
  gets its *a participant declined* family. The §7 exclusion this bullet anticipated was rewritten when TASK-040 was
  re-cut against ADR-0073 (2026-09-29). A non-blocking decline sends
  nothing.
- **D8 — Decline versus reservations is the integrator's to use.** The backend offers both.
- **D9 — Evidence and read side.**
  - **D9a — The envelope's evidence document for a `VOIDED` end is the audit trail's**, sealed through the port
    that work adds. This task emits facts complete enough for it: `Voided`'s members plus the cause, the
    declining recipient and the reason. The **per-signer** evidence document is TASK-047.
  - **D9b — Publish everything known**, so an integrator derives nothing: the fields of §3 #9.

## 5. Verification

- The gates, through the lane from a worktree (`make -C ../f5sign-infra wt-backend src=$(pwd)`), plus Infection;
  the seal against the live DSS (`make dss-wait-tl` first).
- **One case per refusal**, each sabotaged by deleting its guard and checking **which** refusal fired.
- **Role census** over `Role::cases()` for the decline predicate, failing on an unclassified member.
- **D1a/D1b** on a fixture where blocking and non-blocking recipients share a step, so the outcomes **disagree**.
- **Revocation** holds by the synchronous guard: sabotage the reactor and another recipient's commit is still
  refused.
- **A decline racing a commit** is ordered by the root lock (`ProbesRowLocks`).
- **The seal:** both earlier signatures still validate after it; one platform seal is added; no widget is drawn;
  neither the reason text nor the recipient's name is in the PDF; no `EnvelopeCompleted` is recorded.
- **`void()` at `READY_TO_SEAL`** refused by name (D5e), with a case whose envelope is at `READY_TO_SEAL`
  because every blocking recipient signed, not one set there by hand.
- **D5b** on a fixture with a signed, a declined and a pending recipient — three answers, two of them the same.
- **The retirement:** `EnvelopeStatus::DECLINED` is gone from the enum, from the published OpenAPI enum
  (`config/packages/nelmio_api_doc.yaml` lists it today) and from every prose surface. Not a census of writers:
  `SEALING`, `EXPIRED`, `CORRECTING`, `ROUTING_FAILED` and `SEALING_FAILED` are unwritten too, and which of them
  stay is BL-202's decision, not this task's.
- **Closed key sets** on the new facts and on the new read members.
- **The acceptance case** of the delivery bar, over HTTP.

## 6. Open follow-ups (track, don't solve here)

Each gets a `docs/BACKLOG.md` row at landing, id re-derived by grep then.

- **Delegated decline** (D2b) — the integrator declines on behalf of a recipient, as that recipient's word
  (ADR-0055's shape). The normal case outside the waybill. [BL-282](../BACKLOG.md).
- **Quorum decline** (D1c) — deferred here, since built with quorum authoring by TASK-050: a decline inside an `AT_LEAST` step is admitted like any other act. [BL-283](../BACKLOG.md), closed.
- **`REVIEWER` and `IN_PERSON_HOST` decline** (D2). [BL-284](../BACKLOG.md).
- **Replacing a recipient** (D6) — `EnvelopeStatus::CORRECTING` exists for it. [BL-285](../BACKLOG.md).
- **Evidence at the decline** — built by [TASK-045](TASK-045-browser-reported-evidence-at-the-commit.md) (§4 D13): the decline takes the commit's observed IP, user agent and `Accept-Language` and the browser's report. [BL-286](../BACKLOG.md), closed.
- **The annulment stated in the PDF** — BL-281: DSS 6.4's REST interface writes no `/Reason`.
- **Webhook** — ADR-0064 reserves `envelope.declined`; under D1e the envelope-level name is `envelope.voided`
  with a cause, and the reservation is revisited there. [BL-287](../BACKLOG.md).

Surfaced by implementation/validation, not by §4's design pass — same treatment, same home:

- **A declined recipient behind the access gate cannot re-enter a `VOIDED` envelope once their session
  credential lapses** — the same limitation `COMPLETED` already has; no route re-mints a terminal session.
  [BL-288](../BACKLOG.md).
- **`CERTIFIED_DELIVERY` may decline (D2), but the role has no interactive read model at all**
  (`ROLE_NOT_INTERACTIVE`) — the route is reachable with no signer-app screen behind it.
  [BL-289](../BACKLOG.md).
- **A sender's `void` racing a recipient's `decline` can leave the recipient `PENDING` on the envelope while
  their own session reads `DECLINED`** — the two routes have no shared lock ordering them across the
  Session→Envelope crossing. [BL-290](../BACKLOG.md). ⛑ Closed 2026-10-01: since ADR-0073 the decline is
  admitted under the envelope's root lock before the session writes, and `EnvelopeRootLockRaceTest` races
  it against a void from a second process.
- **`PromoteSignedDocumentsCommandTest`'s `#[SkipDatabaseRollback]` cases leave committed rows that broke a
  later full run on a kept lane** — not this task's defect, surfaced while validating it.
  [BL-291](../BACKLOG.md).
- **Migration `Version20260925000001`'s `down()` was never exercised dynamically** — the lane now offers
  `wt-backend-sf admin=1` for it. [BL-292](../BACKLOG.md).
- **`docs/ddd/signing-session-domain-model.md`'s top banner still calls TASK-022's route 4 unbuilt** —
  pre-existing, unrelated to this task. [BL-293](../BACKLOG.md).

## 7. Deviations & honest notes

### Scope
- None. `task-validate-backend`'s cross-check of the full file list against the header Scope's out-of-scope
  list (delegated decline, quorum-step decline, evidence documents, notifications, undoing/replacing a
  recipient, waybill usage) found nothing outside it.

### Decisions made during implementation
- **Decline needs the ACCESS gate only, never a signing code or consent** (ADR-0070 §2.4; ADR-0049 §2.4 binds
  the signing challenge to a signature over the signable set, which a decline never produces).
- **Guard order**: use case — credential retired → step not active (skipped when the envelope is already
  dead); aggregate — terminal → re-auth → not authenticated → envelope not live → role → quorum. Each guard
  was sabotage-checked to confirm which one fires when two apply.
- **A second decline names itself `SESSION_ALREADY_DECLINED`**, distinct from `_COMPLETED`/`_CLOSED`, so a
  repeat call is diagnosable.
- **The decline reason rides one fact only** (`SessionDeclined`); `RecipientDeclined` (the envelope-side fact)
  deliberately does not repeat it, to avoid a second plaintext copy of the same PII.
- **`voided_by` stays null on a decline; `voided_by_recipient_id` names the party** — the sender's `reason`
  member stays the sender's own wording, never overloaded to carry the decline reason.
- **`declined_at` is derived from `outcome_recorded_at`** rather than a new column, since the recipient's leg
  already carries one write-once timestamp for whichever terminal outcome landed.
- **DSS 6.4's REST interface cannot write `/Reason`** — measured against the live service before building the
  seal (plan.md Step 0); the maintainer chose no statement in the PDF over customising DSS, a CMS attribute,
  or restoring the visible mark (ADR-0070 §2.5, §7.10–§7.12; BL-281). ADR-0070 and this task's own §3 #6 and
  §4 D5a were amended in place at `989251b` to record the re-cut.

### Decisions that needed an ADR
- [ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md), drafted `Proposed` on
  2026-09-22, text approved by the maintainer on 2026-09-23 as the go-ahead for this task. It amends
  [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.1 (§2.6) and hands a reservation back
  to [ADR-0064](../adr/ADR-0064-outbound-integrator-webhooks.md) (§2.8). Its §5 (*Enforced by*) and §6
  (*Realized in*) were filled in with the actual tests and code this branch built. Promotion to `Accepted` was
  proposed by this closure and applied on the maintainer's OK the same day (2026-09-23).

### Declared and unproven properties
- **`AnnulmentSealTest` proves both earlier signatures still validate after the seal by byte-prefix, not by
  asking DSS to re-validate the second one** (eidas-compliance, medium). The claim likely holds — the platform
  writes no DocMDP certification, so nothing later invalidates an earlier signature — but the harness doesn't
  discriminate a case that would break it.
- **The same test's redaction check can't fail even if the reason or the decliner's name had been written**:
  it does a raw `str_contains` for non-ASCII UTF-8 against PDF bytes that encode strings as
  PDFDocEncoding/UTF-16BE (eidas-compliance, low). The guarantee holds structurally — verified independently
  via the `SignRequest` shape DSS is actually sent — but this particular assertion is decorative.
- **`Envelope::admitsAnnulmentSeal()`'s `status !== VOIDED` clause has no aggregate-tier test forcing it to
  fire** (eidas-compliance, low): deleting the clause leaves the suite green, because a wider terminal-envelope
  predicate elsewhere converges to the same observable outcome.
- **`SealDocumentUseCase` (test-only, but registered) has no status gate of its own**; it relies on the wider
  terminal-envelope predicate rather than refusing a `VOIDED` envelope by name (eidas-compliance, low).
  Reachable only via a pre-branch `EnvelopeVoided` redelivery, which the relay watermark makes unlikely.
- **Migration `Version20260925000001`'s `down()` was left unexercised** (`task-validate-backend`): the lane's
  admin/superuser DSN was not reachable through `wt-backend-sf` in either `env=dev` or `env=test` at the time
  of that pass. Structural review of the SQL (reverse-order drops, `IF EXISTS` throughout) found nothing
  wrong; execution is [BL-292](../BACKLOG.md).

### Debt left behind, and where it lives now
- Delegated decline, quorum decline, `REVIEWER`/`IN_PERSON_HOST` decline, replacing a recipient, evidence at
  the decline, the webhook name, and the annulment-in-the-PDF gap — §6 above, each now cross-indexed to
  [BL-282](../BACKLOG.md)–[BL-287](../BACKLOG.md) and [BL-281](../BACKLOG.md).
- The six items surfaced by implementation/validation rather than by §4's design pass — access-gate re-entry
  after credential lapse, `CERTIFIED_DELIVERY`'s missing read model, the sender-void/decline race, the
  `PromoteSignedDocumentsCommandTest` lane leftovers, the unexercised migration `down()`, and the pre-existing
  `docs/ddd` banner — §6 above, [BL-288](../BACKLOG.md)–[BL-293](../BACKLOG.md).
- The four `AnnulmentSealTest`/annulment-seal test-strength gaps eidas-compliance found (byte-prefix vs.
  live-DSS re-validation, the decorative redaction assertion, the untested aggregate-tier status clause, and
  `SealDocumentUseCase`'s own missing gate) — recorded above under *Declared and unproven properties*; not
  given a separate BACKLOG row, since none of them is a security hole (security-audit-backend passed clean)
  and Infection's covered-MSI/MSI both clear their floor with headroom.
- ADR-0070's promotion from `Proposed` to `Accepted` — proposed by this closure, applied on the maintainer's OK
  on 2026-09-23.
