# TASK-047 — Each recipient who acts receives a sealed receipt of their own act

| Field | Value |
|-------|-------|
| **Status** | **Done — merged into `develop` on 2026-10-26** from `feat/per-recipient-receipt` (with TASK-068 merged in at `b8514b5f`). Full suite under the `wt-backend` lane that mounts this tree at `7e2b661c`: 8433 tests, one failure outside this branch ([BL-470](../BACKLOG.md), green on re-run); lint, deptrac and PHPStan clean; Infection on the changed lines 95 % covered-MSI (§7). [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) accepted 2026-10-26. Left out: delivery by email or SMS (§6 #1, [BL-280](../BACKLOG.md)). |
| **Type** | **Forward build** in Evidence & Audit, with one enabling change in `Foundation/EventLog`: the settled read gains a boundary qualified by subject. |
| **Why** | A recipient who signs, approves or declines keeps nothing that proves what they did. The envelope's audit trail is issued only when the whole envelope ends, it is served only to the tenant's API keys, and it states every party's personal data, so it cannot be handed to one recipient. The owner wants each recipient who acts to get a **receipt** ("justificante") of their own act: the proof that their act was recorded and, when the mode signs per recipient, that their signature is in the PDF. |
| **Builds on** | [ADR-0071](../adr/ADR-0071-a-stream-is-read-settled-and-by-its-own-tenant.md) (the settled read, extended here), [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) (the trail model, its renderer, its seal and read-back, its custody), [ADR-0076](../adr/ADR-0076-a-first-write-commits-with-its-consumers-record.md) (`writeAlongside`), [ADR-0061](../adr/ADR-0061-retention-deletion-and-purge.md) §2.7 (retention), [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.15 (who reads what once an envelope closes), [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) (the session credential). |
| **Scope** | The receipt: its issuance, its content, its custody, and two ways to download it. ⛔ **Not** its delivery by email or SMS (§6). |
| **Decision record** | **[ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md), `Accepted`** (2026-10-26, by the owner), drafted with this record (id swept over every branch on 2026-10-22; ADR-0085 was the highest). It records that the settled read may stop at a type **and a subject** (ADR-0072 §2.9 names this task as the point where the read gains a boundary finer than a type), the receipt's triggers, its model, its registry, its conservation and the two routes. ⚑ TASK-068, written the same day on `fix/signed-copy-after-commit`, also owed an ADR; it minted ADR-0090, after this one. |
| **Sibling** | ⚑ TASK-068 (ADR-0090, accepted), on `develop` and merged into this branch at `b8514b5f`: what the signer's session read says between their commit and their signature landing (`signed_copy`, `SEAL_PENDING`). This task adds a route under the same credential; its `RECEIPT_NOT_READY` is not a refusal of TASK-068's reads. ⚑ [BL-188](../BACKLOG.md): a link that brings the signer's copy back after they leave the ceremony, the vehicle that the receipt's delivery would ride. |

---

## 1. Why this task exists

The envelope's audit trail (ADR-0072) attests the whole envelope, once it has ended. Nothing attests one
recipient's act at the moment it happens. A signer under `SEQUENTIAL_PADES` who finishes today is told
`COMPLETED`, and keeps nothing: no copy, no proof, and the trail, when it exists, is not theirs to read.

The owner's decisions, 2026-10-22:

- The document is the recipient's **receipt** of their own act, not a minutes of the envelope.
- It is issued when the recipient's act ends **and**, where the signing mode applies a per-recipient
  signature, only once that signature is in the PDF. A receipt issued at the commit would attest a
  signature that a worker has not applied yet ([BL-462](../BACKLOG.md)).
- Under `SINGLE_SEAL` no per-recipient signature exists; the receipt is issued at the act anyway, from the
  evidence recorded then, and says that this mode signs nothing per recipient.
- Signers, approvers and decliners get one. Nobody else.
- It states **nothing about the other participants**.
- Its delivery by email or SMS comes later (§6).

## 2. What already exists (reuse, do not rebuild)

**Evidence & Audit (the envelope trail).**

- `EvidenceAudit/Application/UseCase/IssueAuditTrailUseCase`: returns at once when the registry holds the
  envelope's row; otherwise gathers (`AuditTrailSources::gather()`), assembles (`TrailAssembler::assemble()`),
  renders (`TrailRenderer`), seals (`SignatureExecution/Contract/Service/PdfSealer`), opens a transient
  custody and writes the sealed PDF through `CustodyStore::writeAlongside()` with the registry claim
  (`IssuedTrailRepository::issueIfAbsent()`, `INSERT … ON CONFLICT (id) DO NOTHING`) committed beside it.
  Every refusal is `TrailNotIssued` carrying a `RetryOutlook`.
- `EvidenceAudit/Application/Subscriber/OnEnvelopeCompleted`: the only trigger, on `ENVELOPE_COMPLETED`.
  No per-recipient trigger exists.
- `EvidenceAudit/Domain/Aggregate/IssuedTrail`, table `evidence_audit.issued_trail` (RLS, policy
  `issued_trail_tenant_isolation`), one row per envelope, id derived from the envelope
  (`IssuedTrailId::fromEnvelope()`).
- `TrailAssembler::assemble(TrailSources)` takes no separate boundary: it reads the last row of
  `TrailSources::$stream` (`EndedStream`, which wraps a `SettledStream`). `EndedStream::TERMINAL_TYPES` is
  `[ENVELOPE_COMPLETED]`.
- `AuditTrailSources` reads through `Foundation/EventLog/EventStreamReader`, `Envelope/Contract/Query/DocumentArtifactChains`,
  `Envelope/Contract/Query/EnvelopeQueryInterface`, `Session/Contract/Query/ActEvidenceReader`,
  `IdentityAccess/Contract/Query/TenantNames`, `Storage/Contract/CustodyStore` and
  `SignatureExecution/Contract/Service/SignatureReadBack`.
- `PartyPersonal` (`EvidenceAudit/Domain/Trail`) is the one group holding personal values, minimised per
  ADR-0072 §2.6 (contacts masked; IP and user agent in full).
- `ConserveTrailsCommand` (`app:evidence-audit:conserve-trails`), hourly: raises each issued trail's custody
  to its envelope's conservation ceiling (`ConservationCeilings`), then records `conserved_until`/`conserved_at`.
- `DownloadAuditTrailController` + `GetAuditTrailHandler`: `MACHINE_KEY`; 200 PDF with a strong `ETag`
  (SHA-256), 304, 404 for no trail, 409 `AUDIT_TRAIL_UNAVAILABLE` for missing bytes or a detected
  substitution (logged at error).
- Tests to mirror: `IssueAuditTrailUseCaseTest`, `OnEnvelopeCompletedTest`, `TrailAssemblerTest`,
  `TrailJsonCompletenessTest`, `ConcurrentTrailClaimTest`, `ConserveTrailsCommandTest`,
  `DownloadAuditTrailControllerTest`, `AuditTrailHttpTest`, `DeclinedEnvelopeTrailHttpTest`; fakes in
  `tests/F5Sign/EvidenceAudit/Testing/Fake/` (`ScriptedPdfSealer`, `ScriptedTrailRenderer`,
  `InMemoryIssuedTrailRepository`, `RecordingCustodyStore`).

**The settled read (ADR-0071).** `EventStreamReader::readSettled(string $streamId, array $boundaryEventTypes)`
returns `Result<SettledStream, StreamReadRefusal>` (`StreamNotSettled`, `NoBoundaryInStream`): the rows up to
and including the **lowest position** whose type is in the list. It cannot stop at "this recipient's act",
because an envelope's stream holds one `RECIPIENT_SIGNED` per recipient. Adapter `DbalEventStreamReader`
calls the `SECURITY DEFINER` function `platform.read_settled_stream`. Tests:
`EventStreamSettledReadTest`, `SettledStreamTest`.

**The facts that end a recipient's act** (all on the envelope's stream: their `streamKey()` is the envelope id).

| Act | Fact | Notes |
|---|---|---|
| commit (sign or approve) | `SESSION_COMPLETED` (`Session/Contract/Event/SessionCompleted`) | recorded in `SigningSession::commitSignature()`, after `SIGNATURE_COMMITTED` |
| signature applied | `RECIPIENT_SIGNED` (`SignatureExecution/Contract/Event/RecipientSigned`) | `SignForRecipientUseCase` returns early unless the mode is `SEQUENTIAL_PADES`; there it signs each assignment that `signs` (`DOCUMENT_SIGNED` per document) and then **always** appends `RECIPIENT_SIGNED`, also for an `APPROVER`, who holds no signing rows and so changes nothing in the PDF. `MockSignUseCase` also appends it (a test and dev path, `SEQUENTIAL_PADES` only) |
| decline | Envelope's `RECIPIENT_DECLINED` (and, when it voids the envelope, the close), **then** `SESSION_DECLINED` (`Session/Contract/Event/SessionDeclined`) | `DeclineSignatureUseCase` crosses to Envelope first, synchronously (`AdmitRecipientAct::decline()` → `admitDecline()`), then `SigningSession::decline()`, guarded by `Role::mayDecline()`, records `SESSION_DECLINED`. Only `SESSION_DECLINED` carries the reason; `RECIPIENT_DECLINED` carries none (ADR-0072 §2.9) |

**Roles and outcomes.** `Role` (`Envelope/Contract/Type/Role`): `SIGNER`, `APPROVER`, `REVIEWER`, `VIEWER`,
`IN_PERSON_HOST`, `EDITOR`, `CERTIFIED_DELIVERY`. `VIEWER`, `REVIEWER` and `EDITOR` are refused at the commit
(`COMMIT_NOT_OFFERED_TO_ROLE`); `IN_PERSON_HOST` and `CERTIFIED_DELIVERY` are refused at send. `mayDecline()`
is `SIGNER`, `APPROVER`, `CERTIFIED_DELIVERY`. `RecipientOutcome`: `PENDING`, `COMPLETED`, `DECLINED`,
`DELEGATED`, `SKIPPED`, `RELEASED` (`DELEGATED` and `SKIPPED` are never written).

**The recipient's reads.** `GET /api/v1/signing/session` and `GET /api/v1/signing/session/documents/{documentId}`
take `Authn::SESSION_CREDENTIAL` (a 15-minute JWT carrying the tenant, envelope and recipient; renewable for
up to 12 hours, ADR-0050 §2.2–§2.3). Once the envelope closes, `RecipientEnvelopeContextView::withholdsDocumentFromRecipient()`
withholds every read from a recipient who neither signed nor is informational, and that recipient's sessions
are revoked (ADR-0073 §2.15). A decliner therefore holds no session once their decline closes the envelope.

## 3. Scope

1. **The subject-qualified boundary.** `EventStreamReader` gains a read that stops at the lowest position
   whose type is in a list **and** whose `subject_id` is a given subject, with the same settledness, tenant
   rules and refusals as the type boundary (ADR-0086 §2.1). A relayed fact carries no log position, but its
   `subject()` names the act: the session for `SESSION_COMPLETED` and `SESSION_DECLINED`, the execution for
   `RECIPIENT_SIGNED`.
2. **The triggers.** A reactor issues one recipient's receipt on:
   - `RECIPIENT_SIGNED` — a signer or an approver under `SEQUENTIAL_PADES`;
   - `SESSION_COMPLETED` — a signer or an approver under `SINGLE_SEAL`, and nothing under `SEQUENTIAL_PADES`.
     The event carries no mode and a reactor reads nothing (ADR-0002), so the mode check sits in the use case,
     which reads the envelope context, as `SignForRecipientUseCase` does;
   - `SESSION_DECLINED` — a decliner, in either mode. It is the decline's last fact and the only one with the
     reason, so the boundary already holds the close when the decline voided the envelope.
   The boundary is the triggering fact: its type and its subject.
3. **The receipt.** A model of its own in Evidence & Audit, assembled from the stream up to the boundary
   and from the same ports the trail reads, holding: the envelope's identity and whether it was still open at
   the boundary, **derived from the stream prefix**, because `EnvelopeQueryInterface` and
   `DocumentArtifactChains` answer the present, which for a receipt can already hold later signers' acts;
   the recipient's act; their identity evidence (`ActEvidenceReader`, delegated evidence included; it answers
   every recipient of the envelope, so the receipt keeps only its own recipient's entries before assembling); per
   assigned document, its original digest and, under `SEQUENTIAL_PADES`, the revision their own execution
   appended, picked from the artifact chain by their execution id (never the chain's tip) and read back from
   the bytes up to that revision (`PrefixDigests`, `SignatureReadBack`); the hash chain up to the boundary; the limitations that apply (under `SINGLE_SEAL`,
   that no per-recipient signature exists). **No other participant's data.** Rendered PDF/A-3a with its JSON
   attached by the same pinned Typst binary behind a receipt renderer port of its own (`TrailRenderer` takes an
   `AuditTrail` and its adapter binds `trail.typ` alone; both stay unchanged), sealed through `PdfSealer`, as
   the trail is.
4. **The registry and custody.** One row per (envelope, recipient), id derived from both, RLS like
   `issued_trail`; the sealed PDF written with `writeAlongside()`. **The custody stays transient while the
   envelope is open** and is conserved only once the envelope has ended, which is `ENVELOPE_COMPLETED` on its
   stream: the one fact that ends an envelope, whatever its outcome (ADR-0073 §2.5), and the instant its
   ceiling becomes final (§2.16). `ConservationCeilings::of()` answers for any sent envelope, provisional or final,
   so it cannot say this; the job reads the fact through what the trail's issuance already uses
   (`EvidenceAudit/Application/Service/EndedStream`, `TERMINAL_TYPES`), reused, not rebuilt. `ConserveTrailsCommand` raises a
   custody once and records it, and it relies on the ceiling being final (ADR-0073 §2.16: the send-time
   ceiling is provisional and is re-resolved at `COMPLETED`); a receipt issued mid-envelope would be raised to
   a ceiling that later moves. A transient custody that nobody deleted has no end of its own (`Custody`: nothing
   schedules its destruction), so waiting loses nothing; only a customer's deletion bounds it, by its grace window. The job, which reads `issued_trail` only today, is extended to the
   receipts' registry.
5. **Two routes.**
   - `GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt`, `MACHINE_KEY`, for the integrator.
   - `GET /api/v1/signing/session/receipt`, `SESSION_CREDENTIAL`, the session's own recipient only. Whether
     that session has acted (§4 #5) is Session's to answer, and its contract exposes no such read today
     (`Session/Contract/Query` holds `ActEvidenceReader`, whose map also keys sessions that have not acted,
     and `SignatureImageReader`). So Session gains one port in `Session/Contract/Query` that returns one
     session's `SessionStatus` (already in `Session/Contract/Type`), keyed by envelope and recipient (the
     credential carries those, not a session id; a recipient has at most one session), scoped to the caller's tenant, with its
     refusals as values. An EvidenceAudit Application service reads it: deptrac lets EvidenceAudit's
     Application depend on `SessionContract`, and its UI only on its own Application.
6. **Records.** Done when this record was written: BL-280 says what this task builds and what stays open,
   and ADR-0072 §2.9, ADR-0070 §2.8, ADR-0073 §3.2 and TASK-045 point at ADR-0086. Left as written: the
   records that state their own past (TASK-040, TASK-046). When the task lands, ADR-0086's `Status`,
   `Enforced by` and `Realized in` move with it.

**Out:** delivery by email or SMS (§6 #1); the decliner's in-session download (§4 #4); the envelope trail
itself, which does not change (AC-15).

Concepts re-cut: `per-signer evidence document` → `receipt`; `EventStreamReader::readSettled` (gains a
subject-qualified sibling; ADR-0072 §2.9 spoke of a *position* boundary); BL-280 (*"blocked on the audit trail"*, *"not on develop"*, *"emailed together
with the signed document"*).

## 4. Key decisions

1. **The trigger is the fact that makes the receipt true** (owner). Under `SEQUENTIAL_PADES` that is
   `RECIPIENT_SIGNED`, not the commit, for an approver too: one trigger per mode, and the approver's receipt
   claims no revision because none was applied.
2. **`SINGLE_SEAL` gets a receipt at the act** (owner): what was recorded at the moment of signing still
   matters, and the receipt states the limitation instead of omitting the receipt.
3. **Nothing about other participants** (owner). The receipt's JSON has a closed key set; other parties
   appear neither in it nor on the page. Earlier signers' visible marks are already in the PDF.
4. **A decliner downloads through the integrator now, and through the link of §6 #1 later.** When their
   decline closes the envelope their session is revoked (ADR-0073 §2.15), so the session route cannot reach
   them; when it leaves the envelope open, they may reach it until their credential is revoked, and it serves
   them their own receipt.
   Reopening a credential for them is the link's question, not this task's.
5. **The session route answers 409 `RECEIPT_NOT_READY` between the act and the issuance**, so the frontend
   can wait for it (owner, 2026-10-23). "Has acted" is the **session's own state**, `COMPLETED` or `DECLINED`,
   read through Session's contract, not Envelope's record of the act: under `SEQUENTIAL_PADES` Envelope
   records a signer's or approver's completion only on `RECIPIENT_SIGNED` (`Envelope::completesOn()` elects
   the signature driver), which is the receipt's own trigger, so keyed on Envelope the route would answer 404
   through the whole commit-to-signature window ([BL-462](../BACKLOG.md), whose signer-facing half TASK-068 closed) it exists to cover. It lifts once the receipt is issued; a parked issuance keeps it (ADR-0086 §3.3). It is a new route, so TASK-068's census of the session read's 409s
   does not cover it.
6. **A receipt is conserved when its envelope ends, not when it is issued** (author, from the job's own
   invariant; §3 #4). Raising it early would fix it to a provisional ceiling.
7. **One task, not two.** A subject-qualified boundary with no consumer cannot be tested usefully. The Foundation
   change is small and lands first in the plan.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A `SEQUENTIAL_PADES` signer's receipt is issued on their `RECIPIENT_SIGNED` and never before it, and states per assigned document the revision carrying their signature, read back from the bytes | owner | Application + Acceptance | trigger on `SESSION_COMPLETED` |
| AC-2 | Under `SINGLE_SEAL` a signer's or an approver's receipt is issued on `SESSION_COMPLETED` and states the no-per-recipient-signature limitation; under `SEQUENTIAL_PADES`, `SESSION_COMPLETED` issues nothing (members AC-2a…c) | owner | Application (the use case) | see *Notes on AC-2* |
| AC-3 | A `SEQUENTIAL_PADES` approver's receipt is issued on `RECIPIENT_SIGNED`, states the approval and claims no revision of theirs | owner | Application | state the document's latest revision as theirs |
| AC-4 | A decliner's receipt (signer or approver) is issued on `SESSION_DECLINED` and states the decline, its reason and the decline evidence (members AC-4a, AC-4b) | owner | Application + Acceptance | see *Notes on AC-4* |
| AC-5 | The receipt states nothing about another participant: its JSON has a closed key set, and with two recipients whose names, contacts, IPs and user agents all differ, none of the other's values appears in the JSON | owner | Unit | add the roster to the receipt model |
| AC-6 | The receipt holds the envelope's identity and whether it was open at the boundary, the recipient's act, their identity evidence, per document the digests up to their own revision, and the chain up to the boundary; nothing issued after the boundary appears (members AC-6a…e) | owner | Unit + Application | see *Notes on AC-6* |
| AC-7 | `GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt` answers each documented code, each one an `#[OA\Response]` (members AC-7a…f) | owner | Unit + Acceptance | see *Notes on AC-7* |
| AC-8 | `GET /api/v1/signing/session/receipt` serves only the credential's own recipient's receipt, and answers each documented code (members AC-8a…d) | owner | Acceptance | see *Notes on AC-8* |
| AC-9 | The settled read with a type-and-subject boundary returns the rows up to and including the first row of that type with that subject, refuses when no such row exists or the stream is not settled, and a repeated row of that type and subject moves nothing (members AC-9a…d) | derived — ADR-0072 §2.9 | Integration (real log) | see *Notes on AC-9* |
| AC-10 | One receipt per (envelope, recipient): a redelivered fact seals and writes nothing, and two concurrent issuances leave one row and one custody (members AC-10a, AC-10b) | derived — ADR-0072 §2.10 | Application (AC-10a); Integration, second connection (AC-10b) | see *Notes on AC-10* |
| AC-11 | The receipt is sealed through `PdfSealer` and its seal read back; a sealer or read-back that does not answer records nothing and throws a refusal whose outlook a retry can clear | derived — ADR-0072 §2.7 | Application | swallow the sealer's refusal |
| AC-12 | A receipt's custody opens transient and stays transient while its envelope is open; once the envelope has ended, the hourly conservation job raises it to the envelope's final ceiling (members AC-12a, AC-12b) | derived — ADR-0061 §2.7, ADR-0073 §2.16 | Integration | see *Notes on AC-12* |
| AC-13 | The registry table has RLS enabled and forced with a tenant policy, and the machine route answers 404 for another tenant's envelope | derived — ADR-0071 | Integration + Acceptance | drop the policy |
| AC-14 | Who gets a receipt, over `Role::cases()` and `RecipientOutcome::cases()`, failing on an unclassified member (members AC-14a…h) | derived — rule 5 | Unit (census) | classify `VIEWER` as receiving |
| AC-15 | The envelope trail does not change: its JSON for a fixed fixture is byte-equal before and after, and its existing tests stay green | derived — ADR-0072 §2.1 | Unit + the EvidenceAudit suite | — (regression) |
| S-1 | A `SEQUENTIAL_PADES` envelope with two signers and an approver, end to end, each receipt downloaded through the machine route (members S-1a…c) | owner | Acceptance, live DSS | see *Notes on S-1* |
| S-2 | A `SINGLE_SEAL` signer downloads their receipt through the session route right after their commit, once it is issued | owner | Acceptance | — |
| S-3 | A recipient declines; the integrator downloads the decliner's receipt | owner | Acceptance | — |

- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane that mounts this tree.

**Notes on AC-2**
- AC-2a — `SINGLE_SEAL` signer, receipt on `SESSION_COMPLETED` with the limitation. Sabotage: drop the limitation.
- AC-2b — `SINGLE_SEAL` approver, the same.
- AC-2c — `SEQUENTIAL_PADES`, `SESSION_COMPLETED` issues nothing. Sabotage: drop the mode check in the use case.

**Notes on AC-4**
- AC-4a — a `SIGNER` declines: the receipt states the decline, its reason (from `SESSION_DECLINED`) and the decline
  evidence, and, when the decline voided the envelope, that it was closed at the boundary. Sabotage: trigger on
  `RECIPIENT_DECLINED`, whose boundary holds no reason.
- AC-4b — an `APPROVER` declines: the same. Sabotage: drop the decline reactor.

**Notes on AC-6**
- AC-6a envelope id and title, and whether it was open at the boundary, from the stream prefix. Sabotage: read the
  status from `EnvelopeQueryInterface`.
- AC-6b the act and its instant. AC-6c the identity evidence, delegated evidence included. Sabotage: drop the field.
- AC-6d per document the original digest and the digest of the revision the recipient's execution appended, with a
  later signer's revision already in the chain. Sabotage: take the chain's tip.
- AC-6e the chain's head at the boundary, recomputed; no fact above the boundary is folded. Sabotage: read to the
  stream's end.

**Notes on AC-7**
- AC-7a 200 with the PDF and a strong `ETag`; AC-7b 304 on a matching `If-None-Match`; AC-7c 404 when no receipt
  exists (no act yet, a role that gets none, an unknown recipient); AC-7d 409 `RECEIPT_UNAVAILABLE` for missing
  bytes and for a substitution, the second logged at error; AC-7e 400 for a malformed id; AC-7f 401 without a key.
  Sabotage: answer 200 with an empty body for AC-7d.

**Notes on AC-8**
- AC-8a 200 with the session recipient's own receipt; AC-8b 409 `RECEIPT_NOT_READY` after the act and before the
  issuance, under `SEQUENTIAL_PADES` between the commit and `RECIPIENT_SIGNED` (sabotage: key "acted" on
  Envelope's recorded outcome); AC-8c 404 when the session is neither `COMPLETED` nor `DECLINED`; AC-8d another recipient's receipt is never reachable
  (the route takes no recipient id). Sabotage: read the recipient from a query parameter.

**Notes on AC-10**
- AC-10a — the triggering fact delivered twice: one seal, one custody, one row. Sabotage: skip the registry check.
- AC-10b — two issuances of one receipt on two connections, driven through the use case and not only the
  repository claim (`ConcurrentTrailClaimTest` covers the claim alone): one row, one custody standing, the
  loser's custody withdrawn. Sabotage: drop the `ON CONFLICT` claim.

**Notes on AC-12**
- AC-12a — a receipt of an open envelope is left transient by the job. Sabotage: conserve it against the
  provisional ceiling.
- AC-12b — once the envelope has ended, the job raises the receipt to the final ceiling and records it. Sabotage:
  leave the receipts' registry out of the job.

**Notes on S-1**
- S-1a — the first signer's receipt names the revision their execution appended, not the second signer's.
- S-1b — the second signer's receipt names their own revision.
- S-1c — the approver's receipt states the approval and claims no revision.

**Notes on AC-9**
- AC-9a with two rows of the same type and different subjects, the read stops at the named subject's row, not
  the first of the type. Sabotage: ignore the subject.
- AC-9b no row of that type and subject: `NoBoundaryInStream`. AC-9c an unsettled stream: `StreamNotSettled`.
- AC-9d a second row of the same type and subject above the first (a redelivered `SESSION_COMPLETED` makes
  `SignForRecipientUseCase` append one for an approver, [BL-463](../BACKLOG.md)) moves
  neither the boundary nor the receipt: the read stops at the first, and the issuance writes nothing new.
  Sabotage: take the highest position of the type and subject.

**Notes on AC-14**
- Receives: AC-14a `SIGNER` `COMPLETED`; AC-14b `APPROVER` `COMPLETED`; AC-14c `SIGNER`/`APPROVER` `DECLINED`.
- Receives nothing: AC-14d `VIEWER`, `REVIEWER`, `EDITOR` (refused at the commit); AC-14e `IN_PERSON_HOST`,
  `CERTIFIED_DELIVERY` (refused at send); AC-14f `RELEASED`; AC-14g `PENDING`; AC-14h a revoked session with no
  act. `DELEGATED` and `SKIPPED` are never written and classify as nothing.

## 6. Open follow-ups (track, don't solve here)

1. **Delivery by email or SMS.** The owner wants each receipt to reach its recipient. An SMS cannot carry an
   attachment and the email channel carries none today, so it is a link: a credential minted for it, as
   `SEALED_COPY_READY` mints one at `COMPLETED` (`NotifyCompletedEnvelopeRecipientsUseCase`). It is the same
   vehicle [BL-188](../BACKLOG.md) needs for the signer's copy, and the decliner's only way to get their
   receipt themselves (§4 #4). Indexed by BL-280.
2. **The trail does not cite the receipts.** A later version could list the receipts issued for the envelope
   with their digests. Nothing needs it today.
3. **The session route's liveness rule is copied inline, and its rejection tests sit below HTTP.** [BL-468](../BACKLOG.md).
4. **The `DECLARED_NONE` sentence of the receipt template says "destinatario" for two people.** [BL-469](../BACKLOG.md). A sealed receipt cannot be reworded, so it is cheapest before the first production issuance.
5. **Already tracked, and this task touches them:** [BL-463](../BACKLOG.md) (a redelivered `SESSION_COMPLETED` appends a second `RECIPIENT_SIGNED` for an approver; the receipt reads the first, so nothing reads it wrong); [BL-324](../BACKLOG.md) (the untested per-tenant failure branch, now also the receipts' loop); [BL-104](../BACKLOG.md) (no `nosniff`, now on the two receipt routes); [BL-171](../BACKLOG.md) (personal data in clear, now in the receipt's PDF and JSON).

## 7. Deviations & honest notes

### Scope
- Files outside the planned set, each forced by a census or gate: `EntityIdFormatGuardTest` (slice 07), `ReactorConvergenceTest` (09), `config/packages/nelmio_api_doc.yaml` for the new `ProblemCode`s (11), `StorageLifecycleScenarioTest` and `SentinelScopeRestoredTest` (12), `SigningReadersRefuseUnsentEnvelopeTest`, `RouteAuthnDeclarationTest`, `SessionCredentialTenantScopeTest` (13).
- Slice 16, added after the plan: a closing sweep of prose the branch made false (the session-credential route lists in docblocks and `#[OA\*]` strings, the renderer, custodian and build comments). Commit `92309746` also carries record-header edits its message does not name.
- A docblock-only edit to the published `Version20260922000002` (slice 01, repo rule 2) and ADR-0072 §2.9 reworded out of slice (15).

### Decisions made during implementation
- The session route keys "has acted" on the session's own state (`SessionStatus` `COMPLETED` or `DECLINED`, through the new `SessionStatusReader`), never on Envelope's recorded outcome (§4 #5; claims check B1, resolved by the owner 2026-10-23).
- An unsent envelope is classified in the route census (explicit check, beside `withholdsDocumentFromRecipient()`); a closed envelope and a step not yet reached refuse (slice 13, ruled by the orchestrator).
- `GetSessionReceipt::$issuedBy` is `SystemActorId::recipient()`, not an `ActorId` (which cannot name a recipient).
- The envelope context is read before the mode and role checks, so a fact that issues nothing costs one Envelope read; a redelivered `SESSION_COMPLETED` with no receipt due therefore redelivers (documented on `OnSessionCompleted`).
- Empty custody bytes count as no bytes, as in the trail's sources; a document missing from the view is named by its id.
- The retirement comparison in `GetSessionReceiptHandler` is inline because deptrac forbids the dependency on Session/Application (indexed as BL-468).

### Decisions that needed an ADR
- [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md): proposed with this record, accepted by the owner on 2026-10-26 once the bars above were green, in its own commit.

### Declared and unproven properties
- **Covered-MSI of the diff: 95 % (MSI 94 %)**, Infection on the branch's changed lines at `7e2b661c`: 687 mutants, 652 killed, 28 escaped, 7 not covered. The first run at `f3bc315a` (720 mutants: 600 killed, 44 escaped, 76 not covered) sent the branch back for a test-only fix slice. Every survivor left is judged equivalent, unreachable or an unpinned attribute argument, one line each in the run's slice report; the `#[OA\*]` arguments `OpenApiSpecTest` pins are marked `@infection-ignore-all`, as `DeclineSignatureController` does. Full suite at `7e2b661c` on the wt-backend lane: 8433 tests, 1 failure, `RecipientNotificationHistoryHttpTest::the_body_carries_exactly_the_published_keys`, which this branch does not touch: it asserts the body never contains `550` while the body carries a UUID that can contain it by chance ([BL-470](../BACKLOG.md)); green on re-run. Lint, deptrac and PHPStan clean.
- Two issuances on two connections (AC-10b) and the custodian's grants run only under the integration harness; no memory test exists for "one document's bytes held at a time" (slice 04).
- The `nosniff` header, personal data at rest and `composer audit` were not verified (security audit: 0 blocking, 5 warnings), see §6 #3 to #5.
- Not run: the dynamic half of perf-smoke (no seed script); eIDAS delegation (no signing internals changed; the seal is the platform's, as the trail's).
- A document name falls back to its id (`Stated(name, ROW)`); unreachable today because names never change and documents are never removed (slice 05).

### Debt left behind, and where it lives now
- Delivery by email or SMS: §6 #1, [BL-280](../BACKLOG.md), [BL-188](../BACKLOG.md).
- The trail does not cite the receipts: §6 #2.
- The session route's inline liveness rule and handler-level 404 tests: §6 #3, [BL-468](../BACKLOG.md).
- The `DECLARED_NONE` wording: §6 #4, [BL-469](../BACKLOG.md).
- A second `RECIPIENT_SIGNED` for a redelivered approver commit: [BL-463](../BACKLOG.md).
- The receipts' conservation loop untested on failure: [BL-324](../BACKLOG.md). No `nosniff`: [BL-104](../BACKLOG.md). Personal data in clear: [BL-171](../BACKLOG.md).
- No `tenant_id`-leading index on `issued_receipt`: accepted, as `issued_trail` (doctrine-guard warning).
- Frontend handoffs owed (signer: session receipt route, `RECEIPT_NOT_READY`, `RECEIPT_UNAVAILABLE`, the 404s, PDF with `ETag`; integrator: machine route and the two `ProblemCode`s): routed to docs-sync, not done by this skill.
- The Evidence & Audit bullet of the repo guide ("the context's one table") is stale; the guide is a symlink into the root `ai/` store, so it is edited there at landing.

### Delegated work
- No slice delegated to a `replicator` (every `delegated` list in the run log is empty). 16 slices: 15 critical on opus and one standard on sonnet (slice 15). Review rounds per slice 0 to 3, 20 in all (slices 12 and 13 took three each).

### Cost of the run
- Slices: 2,878,073 tokens in all: 2,778,041 on opus, 100,032 on sonnet.
- 20 review rounds over 16 slices; no escalation to a higher tier.
- Full suite: one failure at `affed9ba` (the policy list of `DbalIssuedReceiptRepositoryTest`), fixed in `2ae3ff08`; green at `1404641b`.
- Planning, spec gates, closing review and this close are not in the slice figures.
