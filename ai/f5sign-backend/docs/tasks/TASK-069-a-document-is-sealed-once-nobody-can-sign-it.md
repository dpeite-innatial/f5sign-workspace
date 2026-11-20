# TASK-069 — A document is sealed as soon as nobody can still sign it and the agreement is secured

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/early-document-seal`** (`839a4c5c`), 2026-10-23, with `develop` merged in at `a8115e00` (TASK-068 included) — suite green under the `wt-backend` kept lane on this worktree at `3f71dbf9` (8313 tests, 93547 assertions), plus lint, arch and phpstan; Infection on the changed lines 95 % covered-MSI (§ 7). Pending review. [ADR-0087](../adr/ADR-0087-a-document-is-sealed-once-it-is-final.md) accepted by the owner, 2026-10-23. Left out, each with its home in § 7: the window of AC-4c (BL-465), `signed_copy` reading `CONTAINS_YOUR_SIGNATURE` for an early-sealed signer until completion (BL-466), and the triggers a decline, a release and a data migration do not have (BL-467). The Infection verdict is in § 7. |
| **Type** | **Forward build** across Envelope (decides when a document is final), Signature Execution (seals it) and Evidence & Audit (the trail accepts the seal). |
| **Why** | A recipient whose part ends gets nothing final until every other party has acted, and they cannot know whether more steps remain. On the Factor5 waybill a consignee signs on delivery, and their own document waits for the other consignees or the step's two-day deadline before it carries the company seal. The owner's principle (2026-10-22): **a recipient whose part ends receives something complete and final at that moment, without depending on the others.** |
| **Builds on** | [ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md) (the artifact chain and its compare-and-swap; `DocumentSigner`), [ADR-0023](../adr/ADR-0023-dss-server-signing-seal-flow.md) (the seal flow), [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.2 (agreement secured apart from closing; a sender void refused after it), [ADR-0062](../adr/ADR-0062-stage-then-promote.md) (stage then promote), reused unchanged. |
| **Scope** | `SEQUENTIAL_PADES` only. ⛔ **Not** the notifications that tell the recipient (the next record), and not `SINGLE_SEAL`, which keeps one seal at the end. |
| **Decision record** | **[ADR-0087](../adr/ADR-0087-a-document-is-sealed-once-it-is-final.md), `Accepted`** (2026-10-23, by the owner; `Proposed` until then), drafted with this record (id swept over every ref and worktree on 2026-10-22; ADR-0086 is the highest, on `feat/per-recipient-receipt`). It amends ADR-0073 §2.5, ADR-0039 §10 and ADR-0072 §2.2. |
| **Sibling** | ⚑ TASK-068 (`fix/signed-copy-after-commit`, not on `develop`): its `signed_copy: FINAL` means *the envelope is `COMPLETED` and sealed*; after this task a document can be final earlier. Whichever lands second reconciles them. ⚑ TASK-047 (`feat/per-recipient-receipt`): the receipt states the revision the recipient's execution appended, which is unaffected by a seal over it. ⚑ The per-recipient notifications (not yet written): they send one final email when a recipient's documents are sealed at their act, and depend on this task. |

---

## 1. Why this task exists

Today the company seal is one act at the end. `SealEnvelopeUseCase` runs on `ENVELOPE_READY_TO_SEAL`, which
Envelope records only once the envelope is closed, somebody engaged and no signature is in flight, and it seals
every document under one execution id. Until then every document is an intermediate revision.

On the waybill (TASK-050: shipper and carrier in `ALL` steps, three consignees in a last `AT_LEAST 1` step with
a two-day deadline, each consignee signing their own document), consignee A's commit secures the agreement, and
A's document then has no signer left. Nothing more can happen to it but the seal, yet the seal waits for B, C
or the deadline.

Owner decisions, 2026-10-22:

- Seal a document as soon as **nobody pending can still sign it** and **the agreement is secured**. The
  second condition is what makes it safe: after `ENVELOPE_AGREED` a sender void is refused and the outcome
  cannot become `NOT_AGREED`, so an early seal can never be contradicted by an annulment that the PDF could not
  state ([BL-281](../BACKLOG.md): DSS writes no `/Reason`).
- Only after the last signer's signature is in the PDF, never at the commit.
- `SINGLE_SEAL` is unchanged.
- The bytes stay in staging until the envelope completes, and are promoted once.
- Informational members keep `SEALED_COPY_READY` at completion, as today.

## 2. What already exists (reuse, do not rebuild)

**The seal.**

- `SignatureExecution/Application/UseCase/SealEnvelopeUseCase`: reads the context, returns unless the status is
  `READY_TO_SEAL`, and for each document with a tip calls `DocumentSigner::seal()` under one execution id,
  `SignatureExecutionId::fromEnvelopeSeal()` (v5 over `seal|<envelope>`); a repeat is caught as
  `ArtifactAlreadyAppendedException` and returns; then it appends `ENVELOPE_SEALED` (`execution_id`,
  `envelope_id`, `occurred_at`). Triggered by `OnEnvelopeReadyToSeal`.
- `SignatureExecution/Application/UseCase/SealDocumentUseCase` and its command `SealDocument` (`executionId`,
  `envelopeId`, `documentId`, `recipientId`): seal one document and append `DOCUMENT_SIGNED`. **Test-only**:
  nothing in `src/` dispatches it; `SealDocumentSliceTest` exercises it against DSS. It returns on a terminal
  envelope, and it does **not** catch `ArtifactAlreadyAppendedException`.
- `SignatureExecution/Application/Service/DocumentSigner`: `seal()` and `sign()` share one byte path that differs
  only in `ProducedBy`; it lays the fill revision (ADR-0085), signs at PAdES-B-B, and appends one artifact with
  the compare-and-swap on `tipArtifactId`.
- `Envelope/Contract/Type/ProducedByKind`: `UPLOAD`, `SIGN`, `SEAL`, `EXTENSION` (no producer of `EXTENSION`).

**The chain.** `Document::appendArtifact()` refuses, in order: a production already present
(`ArtifactAlreadyAppendedException`), a superseded document, a moved tip (`ArtifactChainConflictException`).
`Envelope::appendDocumentArtifact()` adds: a terminal envelope refuses; under `READY_TO_SEAL` only a `SEAL`
appends. **In `SENT`, any kind is accepted, a `SEAL` included, and nothing refuses a `SIGN` over a sealed tip.**
`DoctrineEnvelopeReadRepository` projects each document's tip and `isSealed`.

**Agreement.** `Envelope::apply()` records `ENVELOPE_AGREED` (`envelope_id`, `tenant_id`, `occurred_at`) when
`EnvelopeEndingEvaluator` secures the agreement, at an admission or a step close, never waiting for bytes; it is
stored as `envelope.envelope.agreed_at` (`Envelope::agreedAt()`). Nothing reacts to it. `closed_at` is set later,
by `Envelope::close()`.

**Signers of a document.** `DocumentAssignment` (`recipientId`, `documentId`, `signs`, `visible`); assignments are
frozen at send (ADR-0039 §8). `Recipient::signsDocument()`, `Recipient::outcome()`,
`Recipient::hasSignatureInFlight()`. **No predicate answers "does this document still have a pending signer".**
`RecipientOutcome`: `PENDING`, `COMPLETED`, `DECLINED`, `DELEGATED`, `SKIPPED`, `RELEASED` (`DELEGATED` and
`SKIPPED` are never written). Under `SEQUENTIAL_PADES`, `OnRecipientSigned` dispatches `RecordRecipientCompletion`,
and `Envelope::recordRecipientCompletion()` marks the recipient `COMPLETED` and advances.

**Reads.** `SigningDocumentReader` serves the chain tip to the session's recipient. `SigningSessionReader` raises
`SEAL_PENDING` only while the recipient sees a document with bytes and no seal (`holdsAnUnsealedDocument()`).
The integrator's `GET …/documents/{id}/sealed` (`DownloadSealedDocumentController`, `GetSealedDocumentHandler`,
`findSealedArtifact()`: the latest `SEAL` artifact) answers 404 while no seal exists; ADR-0039 §10 states that
sealing covers every document, and its Consequences that the seal is applied at completion, so the route 404s
mid-flow.

**Storage.** `PromoteSignedDocumentsCommand` (hourly, custodian) raises each document's tip to the envelope's
ceiling once the envelope has `completed_at` and the chain will not grow (`DbalPromotableDocuments`); the ceiling
is final only at `COMPLETED` (ADR-0073 §2.16). Until then every revision sits in staging, and a transient custody
has no end of its own.

**Trail.** ADR-0072 §2.2's check `EVERY_ARTIFACT_HAS_ITS_FACT` fails a `SIGN` or `SEAL` artifact whose execution
id matches no held fact; today the only seal fact is `ENVELOPE_SEALED`.

**Tests to mirror.** `SealEnvelopeUseCaseTest`, `SealDocumentUseCaseTest`, `DocumentSignerTest`,
`OnEnvelopeReadyToSealTest`, `SequentialPadesLoopTest`, `EnvelopeSealLoopTest`, `RedeliveredSealTest`,
`SealDocumentSliceTest`, `DocumentArtifactChainTest`, `EnvelopeConcurrentAppendTest`,
`PromoteSignedDocumentsCommandTest`, `EnvelopeSealFrontierTest`.

## 3. Scope

1. **Envelope decides.** A predicate states when a document is final: the envelope is `SEQUENTIAL_PADES`, the
   agreement is secured, the envelope is not closed, the document has bytes and at least one signature, its tip is
   not sealed, and no recipient who signs it is still pending, nor any recipient who owns a field with an
   occurrence on it (owner, 2026-10-23, security audit). It is evaluated without stored state, **at the end
   of each call** that records a completion or secures the agreement, after that call's releases, over one set:
   the documents the completed recipient **signs** (`signs = true`) or owns a field on (a sight-only assignment
   alone adds none), plus every
   document when the call secured the agreement. A document is requested at most once across calls: a request
   needs the agreement and no pending signer or field owner, so it cannot recur at the securing (which happens once) nor at a
   later completion (whose recipient would have been pending). For each document requested, Envelope records
   `DOCUMENT_READY_TO_SEAL`. The hook sits at the end of the aggregate's
   public methods that reach it (`admitCommit`, `admitDecline`, `recordRecipientCompletion`, `applyClocks`,
   `reconcileAfterDataMigration`), not inside `apply()`, which is re-entrant through `advance()` and would
   evaluate before the outer call's releases.
2. **The view says who sealed.** `DocumentView` (a `Contract/View` type) gains `sealedBy`: the execution id of the
   `SEAL` artifact on the document's chain, or `null`. Today it carries only `isSealed`, a chain-level flag, and
   Signature Execution cannot tell its own seal from another's without it.
3. **The chain refuses after a seal.** A document whose chain holds a `SEAL` accepts no further `SIGN` or `SEAL`;
   the refusal is named. An `EXTENSION` (preservation over a seal, which the tree anticipates in the docblocks of
   `DocumentView::$isSealed`, `Document`, `Envelope::recordDocumentConserved()` and `PromotableDocuments`, and has
   no producer of today) stays allowed.
4. **Signature Execution seals one document.** A reactor on `DOCUMENT_READY_TO_SEAL` dispatches `SealDocument`
   with an execution id derived from the envelope and the document. The use case converges on a repeat and on a
   tip already sealed, and appends `DOCUMENT_SEALED` instead of `DOCUMENT_SIGNED`. The command loses its
   `recipientId`, which a seal does not have.
5. **The envelope seal skips what another execution sealed.** `SealEnvelopeUseCase` first asks, through
   `sealedBy`, whether any document holds a `SEAL` of **its own** execution: if so, it already committed, and it converges with no fact,
   as its `ArtifactAlreadyAppendedException` catch did before this task (`RedeliveredSealTest`); the catch stays for
   a concurrent duplicate that read the chain before the first delivery committed. Otherwise it skips the
   documents whose tip is a `SEAL` of another execution (an early seal), seals the rest, and records
   `ENVELOPE_SEALED` even when nothing was left. A tip conflict or the §3 #3 refusal met in a race rolls the
   attempt back and the delivery is retried; the retry re-reads, finds the sealed tip and skips it.
6. **Reads.** The integrator's sealed-document route serves an early seal; its `#[OA\*]` prose says so.
7. **Trail.** `DOCUMENT_SEALED` is a held fact for its `SEAL` artifact, in the check (`everyArtifactHasItsFact`)
   and where the trail builds each document's seal step (`documents()`, which today finds a seal's fact through
   `sealFact`, `ENVELOPE_SEALED` only).
8. **Records.** ADR-0087; ADR-0039 §10, ADR-0073 §2.5 and ADR-0072 §2.2 carry its amendment once it is accepted.
   The prose that says *one seal path* or *test-only* is swept with the code: the docblocks of
   `DbalPromotableDocuments`, `CheckRule`, `TrailAssembler` (and its `sealFact`), `DocumentSigner::seal()`,
   `SealDocument`, `SealDocumentUseCase`, `SealEnvelopeUseCase` (its catch comment),
   `SignatureExecutionId::fromEnvelopeSeal()` and `DownloadSealedDocumentController`, and ADR-0072's text on
   `EVERY_ARTIFACT_HAS_ITS_FACT` and the seal.

**Out:** the notifications (Sibling); `SINGLE_SEAL`; promotion before `completed_at`; a document nobody signs
(sealed at the close, as today).

Concepts re-cut: *"one seal at completion"*, *"after `READY_TO_SEAL` only the seal appends"*, *"the sealed route
404s mid-flow"*, `SealDocument` (test-only → production, loses `recipientId`), `SealEnvelopeUseCase` (seals every
document → seals the unsealed ones).

## 4. Key decisions

1. **Envelope owns the predicate** (author, from ADR-0034: the chain, the steps and the assignments are
   Envelope's). Signature Execution only executes, as it does for the envelope seal.
2. **Agreement is the safety condition** (owner). Without it a later decline or void could annul a sealed
   document, and the seal could not say so.
3. **After the signature lands** (owner): the evaluation runs on `RecordRecipientCompletion`, which under
   `SEQUENTIAL_PADES` follows `RECIPIENT_SIGNED`, and on the agreement being secured, when every signer of the
   document has already landed.
4. **Not once the envelope is closed**: from `closed_at` the envelope seal owns the remaining documents, so the
   two seal paths only meet in a race (AC-11).
5. **Staging until `completed_at`** (owner): promotion is unchanged, so each document is still promoted once, with
   the final ceiling.
6. **A document nobody signs is sealed at the close**: it has nobody whose part ends.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | Under `SEQUENTIAL_PADES` a document is sealed once the agreement is secured and none of its signers is pending, and only after its last signer's signature has landed (members AC-1a…c) | owner | Unit + Application | see *Notes on AC-1* |
| AC-2 | The waybill: A signs, and A's document is sealed while B and C are pending; A's session download serves the sealed revision | owner | Acceptance | evaluate only at the close |
| AC-3 | Under `SINGLE_SEAL` no document is sealed before the end | owner | Unit | drop the mode condition |
| AC-4 | At completion the envelope seal seals only the documents no other execution sealed; with every document already sealed early it records `ENVELOPE_SEALED` and the envelope completes; redelivered after it committed, it converges with no second fact (members AC-4a…c; **AC-4c holds only where the envelope seal appended at least one seal**, see § 7 *Decisions made during implementation*) | owner | Application + Integration | see *Notes on AC-4* |
| AC-5 | An early-sealed document stays in staging and is promoted once, after `completed_at`, to the final ceiling: one retained object per document | owner | Integration | promote on `DOCUMENT_SEALED` |
| AC-6 | Informational members get `SEALED_COPY_READY` at completion, unchanged | owner | Application (regression) | — |
| AC-7 | A document whose chain holds a `SEAL` refuses a further `SIGN` or `SEAL`, by name, and still accepts an `EXTENSION` | derived — ADR-0073 §2.5 | Unit | drop the guard |
| AC-8 | `DOCUMENT_READY_TO_SEAL` and `DOCUMENT_SEALED` have closed key sets and are registered for the wire (members AC-8a, AC-8b) | derived — ADR-0072 §2.2 | Unit | add a key |
| AC-9 | The trail holds an early seal with its own fact: `EVERY_ARTIFACT_HAS_ITS_FACT` passes and the seal shows under its document | derived — ADR-0072 §2.2 | Application | drop `DOCUMENT_SEALED` from the held facts |
| AC-10 | A document is requested once and sealed once: a redelivered fact, a later completion and the securing never request it twice, and a repeated request converges on the execution id derived from the envelope and the document (members AC-10a…d) | derived — ADR-0034 | Unit + Application | see *Notes on AC-10* |
| AC-11 | The early seal and the envelope seal racing on one document leave one `SEAL` artifact; the loser's attempt is refused (the tip moved, or `documentAlreadySealed` on a sealed tip, §3 item 3, pinned by `EarlySealRaceTest`) and its retry converges, with no second fact | derived — ADR-0034 | Integration, second connection | skip the re-read on retry |
| AC-12 | A DSS failure on the early seal records nothing and throws; the delivery is retried, then parked; the envelope still completes and its seal covers the document; the parked seal replayed afterwards converges (members AC-12a…c) | derived — ADR-0073 §2.17 | see *Notes on AC-12* | swallow the failure |
| AC-13 | A sender void is refused on an envelope holding an early seal | derived — ADR-0073 §2.2 | Acceptance (regression) | — |
| AC-14 | The integrator's sealed-document route serves an early seal before the close, and its `#[OA\*]` prose says when one exists | derived — ADR-0039 | Acceptance + Unit | 404 while the envelope is open |
| AC-15 | What blocks an early seal, over the whole set, failing on an unclassified member (members AC-15a…i) | derived — rule 5 | Unit (census) | classify `RELEASED` as blocking |
| S-1 | The waybill end to end on live DSS (members S-1a…c) | owner | Acceptance, live DSS | see *Notes on S-1* |

- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane that mounts this tree. <!-- OFFREPO: `wt-backend` is a make target of the sibling infra repository that runs this repo's suite in a container mounting this worktree; nothing here depends on reading it. -->

**Notes on AC-1**
- AC-1a — the agreement is secured at A's admission and A's signature lands later: no request at the admission, a
  request at A's completion. Sabotage: evaluate at the admission.
- AC-1b — a document with a pending signer in a later step is not requested. Sabotage: look at the current step only.
- AC-1c — every signer done and no agreement yet: not requested; once the agreement is secured, requested.
  Sabotage: drop the agreement condition.
- Narrowed by AC-15i (owner, 2026-10-23, security audit): a recipient who owns a field with an occurrence on the
  document also holds it while pending, and their landing requests it.

**Notes on AC-4**
- AC-4a — two documents, one early-sealed: the envelope seal appends one `SEAL`. Sabotage: seal every document.
- AC-4b — all early-sealed: no new artifact, `ENVELOPE_SEALED` recorded, `COMPLETED`. Sabotage: record nothing
  when nothing is left.
- AC-4c — the envelope seal redelivered after it committed: no second `ENVELOPE_SEALED` (`RedeliveredSealTest`
  keeps passing). Sabotage: skip every `SEAL` tip without asking whose execution it is. ⚠ Accepted by the owner on
  2026-10-23 with a window: when every document was sealed early, nothing on the chain belongs to the envelope
  seal's execution, and a redelivery before `COMPLETED` records a second `ENVELOPE_SEALED` (§ 7, BL-465).

**Notes on AC-8**
- AC-8a `DOCUMENT_READY_TO_SEAL`: `envelope_id`, `document_id`, `occurred_at`. AC-8b `DOCUMENT_SEALED`:
  `execution_id`, `envelope_id`, `document_id`, `occurred_at`.

**Notes on AC-10**
- AC-10a — `RECIPIENT_SIGNED` redelivered: no second `DOCUMENT_READY_TO_SEAL`.
- AC-10b — A's document requested at A's completion; B's later completion does not request it again, including
  when B holds a sight-only assignment on it; a call that secures the agreement and leaves the envelope open
  requests each document final at that moment exactly once, and a later completion does not request it again.
  A call that secures and also closes requests nothing: the envelope seal takes the documents. So the fixture
  secures without closing, as the waybill's last `AT_LEAST 1` step does while B and C are pending. Sabotage:
  evaluate every document B is assigned, sight-only included.
- AC-10d — the securing call releases a member who signs document D, and D's other signers have landed: D is
  requested in that call. Sabotage: evaluate before the call's releases.
- AC-10c — `DOCUMENT_READY_TO_SEAL` delivered twice: one `SEAL`, one `DOCUMENT_SEALED`. Sabotage: mint a fresh
  execution id.

**Notes on AC-12**
- AC-12a (Application) — the sealer refuses: nothing appended, no `DOCUMENT_SEALED`, the use case throws.
- AC-12b (Integration) — the failing delivery is retried (the broker-backed pattern of
  `EventBrokerRetryDeliveryTest`, which proves the retry round trip only) and, its retries exhausted, is found on
  the `failed` transport. No test asserts a parked message today (`messenger.yaml`, `when@test`); this one does.
- AC-12c (Application) — after the envelope seal sealed the document, the parked request replayed converges with
  no fact.

**Notes on AC-14**
- AC-14b (owner, 2026-10-23, security audit) — a second tenant's machine credential GETs an early-sealed document
  while its envelope is open: 404 `NOT_FOUND`, the route's own not-found. Sabotage: send it with the owning tenant's
  credential.

**Notes on AC-15**
- Blocks: AC-15a `SINGLE_SEAL`; AC-15b no agreement; AC-15c the envelope closed (the envelope seal owns it);
  AC-15d a signer `PENDING`, in any step; AC-15e a signer `DELEGATED` or `SKIPPED` (never written; fails closed);
  AC-15f a document nobody signs.
- Does not block: AC-15g a signer `COMPLETED` or `DECLINED`; AC-15h a signer `RELEASED`.
- Blocks (owner, 2026-10-23, security audit): AC-15i a recipient who owns a field with an occurrence on the
  document, signing it or not, still pending; their landing requests it. A field nobody owns, or placed on another
  document, holds nothing.

**Notes on S-1**
- S-1a — A signs: A's document is sealed with the envelope open, and A's download is the sealed revision.
- S-1b — B signs the next day: the same for B.
- S-1c — C never opens; at the deadline C is `RELEASED`, the envelope completes and its seal appends only to C's
  document.

## 6. Open follow-ups (track, don't solve here)

1. **The per-recipient notifications** (next record): one final email when a recipient's documents are sealed at
   their act, otherwise an act email saying the process continues and a close email; delivered by link (BL-188,
   BL-280); carrying the TASK-047 receipt.
2. **TASK-068's `FINAL`** is keyed on `COMPLETED`; once both land, a document sealed early should read final.
3. **A decline or a release does not trigger the evaluation.** A document whose last pending signer or field owner
   declines or is released is sealed early only if a later completion or the agreement evaluates it, and otherwise at the
   close: nobody's part ends with a copy of it.
4. **The custody of a lost race.** *(Resolved in the code, 2026-10-23; the part that remains is BL-244's.)* `DocumentSigner` opens a `PENDING` custody before the append and writes the
   bytes only after it, and the append refuses in memory once the document row lock shows the current tip, so no
   loser ever writes bytes. What happens to its custody row depends on the refusal. The loser of AC-11's race
   (the tip moved, or §3 item 3's refusal of a sealed tip) lets the exception through, so the command's
   transaction rolls back with the row and the redelivery converges; nothing is left. Only a concurrent duplicate
   of the same execution, which read the chain before the first delivery committed, is refused with
   `ArtifactAlreadyAppendedException`, caught, and commits its `PENDING` custody row (a sequential redelivery
   returns on `sealedBy` before opening any custody): BL-244's ordinary path, whose stated fix is ADR-0076's
   `writeAlongside`, not yet adopted by `DocumentSigner`.

---

## 7. Deviations & honest notes

### Scope
- `phpstan.dist.neon` gained one per-file `symfonyContainer.serviceNotFound` entry for `tests/bin/seal_race_child.php`, the same shape as the sibling child scripts' (authorised by the orchestrator, slice 12). No ruleset shape changed, `deptrac.yaml` is untouched, no migration.
- `assets/evidence-audit/trail.typ` gained the two event-type labels (`DOCUMENT_READY_TO_SEAL` and `DOCUMENT_SEALED`), because the renderer's Integration census requires one per loggable type (slices 03/10).
- `tests/F5Sign/Envelope/Integration/PromotableDocumentsTest.php` joined slice 05's files: the command-level sabotage cannot reach the read-port guard, because the published tenant funnel guards `completed_at` first.
- `TrailAssembler.php` took one docblock sentence in slice 16 (closing review F2), against the slice-10-only reservation.
- `config/routes/api/envelope.php` took a comment-only change (slice 06). `php-cs-fixer` moved two test files (`TrailAssemblerTest`, `NotifyCompletedEnvelopeRecipientsUseCaseTest`) with no other change.
- The integrator and signer handoff for this task, and `docs/ddd/`, are written by docs-sync, not by a slice.

### Decisions made during implementation
- **AC-4c is accepted as a deviation (owner, 2026-10-23).** When every document was sealed early, a redelivered `ENVELOPE_READY_TO_SEAL` arriving between the envelope seal's commit and `COMPLETED` records `ENVELOPE_SEALED` a second time. `Envelope::complete()` is idempotent and the trail reads the first fact by execution, so nothing breaks; it is most frequent in one-signer envelopes. Stated in `SealEnvelopeUseCase`'s docblock. AC-4c holds wherever the envelope seal appended at least one seal. Home: BL-465.
- **AC-10b was rewritten by the owner before implementation** (2026-10-23) to name the securing admission and the deadline sweep; no deviation remains. Its clause "a completion that secures the agreement in the same call" cannot be built through the public API (a landing never secures); slice 07 pins "each document once" at the securing admission and at AC-10d's securing clock instead.
- **AC-11's loser is refused, not rolled back on a tip conflict.** The row said the loser "rolls back on the tip conflict"; it is refused by `EnvelopeStateException::documentAlreadySealed()` when the tip it meets is a seal (§3 item 3), or by the compare-and-swap when the tip moved. It is not an `ArtifactChainConflictException`, so the loser gets the ordinary backoff, and its first retry converges. Pinned by `EarlySealRaceTest`.
- **`signed_copy` for an early-sealed signer (owner, 2026-10-23, after integrating TASK-068).** It reads `CONTAINS_YOUR_SIGNATURE`, not `FINAL`, until the envelope completes, because [ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md) §2.2 keys `FINAL` on `completedAt`. Left as is; TASK-071 (per-recipient notices) decides the "final copy" signal. Home: BL-466. This settles §6 item 2.
- **Fill-only contributors block the early seal (owner, 2026-10-23, from the security audit; slice 17).** A recipient whose outcome `blocksAnEarlySeal()` and who owns a field with an occurrence on the document keeps it from being final, signing it or not. Read as ownership plus occurrence, mirroring `FormRevisionPlanner::plan()`: no type filter, no grant or role filter (fail closed). A field with no occurrences counts as on every document; `send()` refuses one, so that branch is unreachable and untested by decision. A completion's candidates now add the documents the completed recipient owns a field on. ADR-0087 §2.1's body was amended for it. A cross-tenant GET of an early-sealed document is pinned as 404 (AC-14b).
- The refusal lives in `Envelope::appendDocumentArtifact()` after the repeat, terminal, `READY_TO_SEAL` and superseded checks and before the compare-and-swap; total `match` on `ProducedByKind`: `EXTENSION` allowed, `SIGN`, `SEAL` and `UPLOAD` refused.
- `SealDocumentUseCase` returns on `sealedBy !== null` (its own seal or another's) before `DocumentSigner` opens a custody, so a sequential redelivery commits no `PENDING` custody row. Only a concurrent duplicate reaches the `ArtifactAlreadyAppendedException` catch and commits one (BL-244, narrowed there).
- `SealEnvelopeUseCase`: own-execution check first (no fact), then skip other executions' seals, then seal, then `EnvelopeSealed` even when nothing was left.
- `DocumentView::$sealedBy` is `?ExecutionRef`, last with a default; `SignatureExecutionId::fromDocumentSeal()` is a v5 over `document-seal|<envelope>|<document>`; the trail matches `DocumentSealed` by execution AND document.
- `SealDocument::$issuedBy` is an `Issuer`, not an `ActorId`: the reactor's issuer is a `SystemActorId` (slice 08).
- An envelope whose agreement was set by the data migration gets no early request from the reconcile; such envelopes are sealed at the close (slice 07, review). Home: BL-467.
- Slice 14 proves AC-4a, not AC-4b, in its waybill case (D_C is left for the envelope seal); the label was corrected by the orchestrator and AC-4b stays at the Application tier (slice 09). Slice 10 has no plain red before the code; its evidence is the clean sabotage of `sealFact()`'s document match.
- Slice 13's Worker test freezes Symfony's clock and advances it 61 s per idle tick (the in-memory transport holds a delayed retry on the clock service); slice 17's APPROVER fixture is `AT_LEAST 1` of approvers only, because `send()` refuses mixed blocking roles in `AT_LEAST`.

### Decisions that needed an ADR
- [ADR-0087](../adr/ADR-0087-a-document-is-sealed-once-it-is-final.md), drafted `Proposed` with this record and accepted by the owner on 2026-10-23, after the full suite and gates were green at `839a4c5c`. The artifacts that exercise it are `EarlyDocumentSealHttpTest` (the chain over the relay on live DSS), `EarlySealRaceTest` (the two seal paths on two connections), `Envelope::requestSealsOfFinalDocuments` with `Envelope::isFinal()`, the append guard in `Envelope::appendDocumentArtifact()`, `SealDocumentUseCase`, the skip in `SealEnvelopeUseCase` and `TrailAssembler::sealFact`. The acceptance commit (`33b7a864`) filled its *Enforced by* and *Realized in* and added amendment banners to ADR-0039 §10, ADR-0072 §2.2 and ADR-0073 §2.5.

### Declared and unproven properties
- `Envelope::isFinal()`'s `isSuperseded()` clause is fail-closed and unreachable today: a superseded document with a signature cannot be built through the API. Documented, untested by decision.
- Infection on the changed lines (diff-scoped against `develop`, `--min-covered-msi=85 --min-msi=70`, `wt-backend` kept lane), at `3f71dbf9`: 193 mutants, 185 killed, 8 escaped, 0 not covered; covered-MSI 95 %, MSI 95 %. The first run, at `839a4c5c`, stood at 85.3 % / 81.3 % with 27 escaped and 9 not covered: nine of those were coverage credit lost to `#[UsesClass]` where `#[CoversClass]` belonged, and the rest were real gaps, closed by the tests of the Infection fix slice. The 8 that escape are equivalent, each argued against the code: in `Envelope`, `placesOn`'s key check (`isset` is true for `false` too); `admitDecline()`'s seal request, which finds nothing because no step policy lets a decline secure the agreement; an `array_values` over a list that is already one; `reconcileAfterDataMigration`'s request in its closed-envelope branch, where `isFinal()` refuses a closed envelope; the two `true` values of the candidate set, whose keys alone are read; the string cast of a UUID key, which PHP never turns into an integer; and `documentsWithFieldsOf`'s `break`, whose duplicates collapse in the keyed candidate set. The infra target exits 1 on any escaped mutant, so its exit code reads red on these eight; the thresholds hold. The no-occurrence field branch and `isSuperseded()` produced no surviving mutant.
- The AC-4c window is stated in code and unpinned by a test (it is accepted behaviour, not a guarantee).
- The first grouped run after merging `develop` showed two failures in `EarlyDocumentSealHttpTest` (`null is of type string`, `409 vs 200`) that were not reproduced (standalone green, grouped green twice, then the full suite at `a8115e00` and `839a4c5c`); the log was not kept and the cause is unexplained.
- `composer audit` could not run in the security audit (no vendor on the host); the diff touches neither `composer.json` nor `composer.lock`.
- AC-6 and AC-13 are regression assertions with no sabotage, as § 5 states.

### Debt left behind, and where it lives now
- AC-4c's second `ENVELOPE_SEALED` window: [BL-465](../BACKLOG.md).
- `signed_copy` before completion for an early-sealed signer: [BL-466](../BACKLOG.md) (TASK-071 decides).
- A decline, a release or a data migration requests no early seal; a document whose last pending signer or field owner leaves that way waits for the close: [BL-467](../BACKLOG.md) (§ 6 item 3).
- The `PENDING` custody a concurrent duplicate of the same seal commits: [BL-244](../BACKLOG.md), whose catch sites now include `SealDocumentUseCase` and whose ordinary path is narrowed.
- The per-recipient notifications that tell the recipient their copy is final: the next record (§ 6 item 1), BL-188 and BL-280.

### Delegated work
Slices 03 (implementer and reviewer, one pass, 115626 tokens), 01, 02, 04, 08, 07, 12, 13, 14, 15, 16, 17 ran at the critical tier on opus; 05 and 06 at standard (sonnet; 06 reviewed on opus), 11 at mechanical (sonnet); 09 and 10 are logged without tier or model. Review rounds: 1 for 01, 02, 03, 04, 08, 11, 13, 15, 16; 2 for 05, 06, 07, 12, 14, 17. Statuses: all DONE, slice 17 after one NEEDS_CONTEXT answered by the orchestrator, and slice 05 with a concern (two guards in series; the read-port case was added). Every slice report's `## Delegated` reads none or "below the threshold of three targets"; no work went to the `replicator`, so there is no outcome to measure.

### Cost of the run
- Slices: 17 (15 planned, 2 added: the Phase 2c fix 16 and the security-audit fix 17), 4 waves.
- Models by slice: opus 12 (critical), sonnet 3 (05, 06, 11), unlogged 2 (09, 10).
- Rounds: 21 in the 15 slices that log them (9 at one round, 6 at two; 09 and 10 unlogged); escalations: 1 NEEDS_CONTEXT (17) and 1 concern (05).
- Tokens: logged for slice 03 only (115626); the run.log carries no per-model totals, so a total is not known.
- Gates: baseline 6740 tests, full suite 8248 at `d94e6e4e` (1194 s), 8300 at `a8115e00`, 8304 at `839a4c5c`; all green on the `wt-backend` kept lane.
