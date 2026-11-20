# TASK-042 — No recipient acts before their step is active

<!-- OFFREPO: the preprod incident of 2026-08-27 is written up in the workspace root at
`notes/INCIDENT-relay-txid-epoch-2026-08-27.md`, outside this repository. Every fact this record takes
from it is restated in §1; nothing here depends on reading it. -->
<!-- OFFREPO: the signer frontend (`f5sign-signer`, `app/composables/useSignFlow.ts`) is a separate
repository. The one behaviour this record depends on is restated in §7. -->
<!-- OFFREPO: §5 D1 relies on two facts about the sibling repository `f5sign-infra`: its committed
`docker-compose.override.yml` binds `../f5sign-backend`, the main checkout, into the stack, and a clean
working tree there shows only that the file on disk is the committed one. The running `php-fpm` keeps
the mount it was created with until `make up` recreates it, so D1 also reads that mount from the
container. Both facts are restated in D1, beside the commands that re-check them. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `fix/step-order-at-every-door`** (cut from `develop` at `f036e4c`), 2026-09-16 — **merged into `develop` at `f490218` and pushed to `origin/develop` the same day, with no PR. Not deployed**: `develop` is not a deployment ([`docs/frontend-handoff/README.md`](../frontend-handoff/README.md) rule 4), and the same `develop` carries [TASK-043](TASK-043-a-refused-commit-names-its-condition.md), whose release order is **one deploy with the `f5sign-signer` change** ([ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) §2.6, amended 2026-09-16). ⛑ **Corrected 2026-09-16, at the merge**: this read *"not merged, not pushed, no PR"*. ⛔ **Enumerate the branch's commits with `git log --oneline --no-merges f490218^1..f490218^2` rather than reading a range here** — the merge's second parent is the branch tip, so the range no longer moves; ⛑ this command read `f036e4c..HEAD`, which on `develop` also lists [TASK-043](TASK-043-a-refused-commit-names-its-condition.md)'s commits and whatever lands after them. A written range on a live branch is stale by construction, and [TASK-041](TASK-041-resending-a-signing-invitation.md)'s row records what that costs. ⚑ **The gates ran at `37ffe1b`**, at the time the last commit that touches `src/`; everything after it was documentation, and that was checked rather than assumed — `git diff --name-only 37ffe1b..HEAD -- src tests config migrations composer.json composer.lock deptrac.yaml phpstan.dist.neon phpstan-baseline.neon infection.json5.dist` was **empty** then, so the run below carried to what was then the tip. ⛑ **Corrected 2026-09-16, at the merge**: this read *"is **empty**, so the run below carries to the tip"*; `5143466` below had already made it untrue, and on `develop` `HEAD` is no longer that tip. Harness per §5 D1, verified all four ways on the day. `make -C ../f5sign-infra qa` printed: lint `Found 0 of 1304 files that can be fixed` · Deptrac `Violations 0 · Uncovered 0 · Allowed 7055` · PHPStan `[OK] No errors` · `Tests: 2993, Assertions: 16149, Errors: 1, Failures: 1`, **0 skipped**, with `rg markTestSkipped tests/` returning nothing, so collected means executed. ⛔ **That is not a green bar and is not claimed as one.** The two reds are §5 D1's baseline names, matched by name **and by reason** — `StorageLifecycleScenarioTest` (its frozen clock, a year ahead of the wall clock, puts its signing step past the dev DSS signing certificate's `notAfter` — §5 D1's mechanism) and `DocumentationLinkTest` (20 docblock links to `CLAUDE.md`, the same 20 as the baseline; this branch added none of them). ⛑ **Corrected 2026-09-16**: the first parenthesis read *"the dev DSS signing certificate expired against the test's frozen clock"*, which reads as a certificate that had aged out. It had not: it was valid 2026-09-01 → 2027-09-01, and with a 365-day validity a signing step some two days more than a year past the wall clock could never fall inside it. That red has since gone; [`BL-251`](../BACKLOG.md) carries how. ⛔ **The mutation gate could NOT run through its sanctioned path**: `composer qa` aborts at `@test` before reaching Infection, and a plain `composer infection` then refuses to start over a red suite. Re-run with exactly those two classes filtered — both `#[CoversNothing]`, so removing them cannot move a mutant between the covered and not-covered populations — it printed **covered-MSI 82.7%** against the `minCoveredMsi: 79` floor, and MSI 50.37% against `minMsi: 50`. Indexed as [`BL-251`](../BACKLOG.md) and [`BL-252`](../BACKLOG.md). ⚑ **Superseded on 2026-09-16 by a later `src/` commit, and the re-run is below** — that sentence stood until `5143466` closed [`BL-263`](../BACKLOG.md) by moving the delegated commit's step guard below its assertion refusals (§8). Re-run at `5143466`: lint `Found 0 of 1304 files that can be fixed` · Deptrac `Violations 0 · Uncovered 0 · Allowed 7055` · PHPStan `[OK] No errors` · `Tests: 2994, Assertions: 16151, Errors: 1, Failures: 1` — the same two baseline reds by name and by reason, one test more because the order pin became a case of its own. ⚠ **That re-run is one commit short of the merged tip, stated rather than glossed** (added 2026-09-16, at the merge): `git diff --name-only 5143466 f490218^2 -- src tests config migrations` names one test file, whose only change is a docblock (`aedf403`). Infection was **not** re-run; the covered-MSI figure above is `37ffe1b`'s and is left labelled as such. **[ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md) is now `Accepted (exercised)`** — promoted by the maintainer on 2026-09-16 after that reconciliation; this row read *"stays `Proposed`… promotion is the maintainer's call and is proposed, not taken, in §8"* until then. Merged into `develop` on 2026-09-16 (above); ⛑ this sentence read *"Pending review."* until that merge, and a `Status` naming a commit that is an ancestor of `origin/develop` may not say so ([`BL-137`](../BACKLOG.md), [TASK-020](TASK-020-derive-the-deferral-index.md)). |
| **Type** | **Corrective.** It adds no capability. Every route a recipient's link or credential reaches gets a precondition it never had, and the seal predicate is rewritten to ask about completeness rather than about later steps. |
| **Why** | ⚑ **Past tense since 2026-09-16 — this row and §1 are the record of the defect this task removed, not of how things are.** A recipient whose step was never activated could open a session, authenticate, read the documents and commit. The commit emitted `SessionCompleted`, which two reactors consume: Envelope books the completion and SignatureExecution signs it into the PDF. This has already happened. In preprod on 2026-08-27 a three-step envelope sealed carrying **one signature of three** (§1). |
| **Builds on** | **[ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) + [TASK-035](TASK-035-signature-requires-readable-envelope.md)**: the crossings, the census and the mint guard, reused and extended by one question. **[ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) + [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md)**: a predicate on envelope state at those same crossings, with its precedence already worked out. **[ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.16**: the precedent for widening `RecipientAuthContext` with a fact about the recipient's own leg (`signsElsewhere`). **[ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.6** (the token is stored as a digest) and **[TASK-028](TASK-028-opaque-signing-token.md) §4.3** (issuance is additive and nothing revokes). Together they are why the mint must refuse before a credential exists. |
| **Scope** | The boundaries that surprise: **the signer frontend change is not here.** This task writes its handoff; the change is another repository's PR. **Preprod data is neither diagnosed nor repaired.** **[BL-183](../BACKLOG.md)'s outcome half** (a DELEGATED or SKIPPED leg) is not closed here. §4 carries the rest. |
| **Decision record** | **[ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md)**, **`Accepted (exercised)`** since 2026-09-16 — drafted alongside this record and carried as `Proposed` until the maintainer promoted it. It governs the predicate (§2.1), the members that carry it (§2.2), where it refuses (§2.3), the codes (§2.4), placement before the fact (§2.5), precedence (§2.6), the seal frontier (§2.7) and what stays open (§2.8). Promotion to `Accepted` was a maintainer's call once §6 was green, and belongs in the changeset that makes it so (`CLAUDE.md` authoring rule 7); it was given on 2026-09-16, in the changeset that reconciled §2.6 with the code. |
| **Delivery bar** | `DormantStepRefusedHttpTest` reproduces the incident and refutes it. With the commit guard sabotaged it answers **200** and a `SESSION_COMPLETED` row appears in `platform.event_log`. With the guard in place it answers **409 `STEP_NOT_ACTIVE`**, no such row exists, and step 3's `activated_at` and `completed_at` are still null. ⚑ **Corrected 2026-09-16, and only the account changed — the bar was met and the measurements above are the ones that were taken.** This row let its two clauses read as equals and §5 D3 named the *row* as the discriminator; an adversarial review measured that false. **The `200`-versus-`409` is the discriminator** — an aggregate-only guard leaves the HTTP commit answering 200, because the reactor it would refuse never runs in this harness — and the log query is a **redundant** end-to-end check that the fact is not written: it can only fail when the commit is allowed, which the 409 catches first. The absence of effect is pinned hermetically in `CommitSignatureUseCaseTest`. D3 carries both measurements. |

---

## 1. Why this task exists

**The gap.** `Envelope::recordRecipientCompletion()` guards three conditions: a terminal envelope, an unsent envelope (ADR-0058) and a terminal recipient outcome. It never asks whether the recipient's step is active, although `Step::isActivated()` exists. A recipient on a dormant step is still `PENDING`, so none of those guards stops them. No Session crossing asks either. A dormant-step recipient holding a link can open, pass both gates, read the read model and the bytes, and commit.

**Guarding only the aggregate would be worse than the hole.** `SessionCompleted` fans out to two sibling reactors that run independently: `Envelope\Application\Subscriber\OnSessionCompleted` dispatches `RecordRecipientCompletion`, and `SignatureExecution\Application\Subscriber\OnSessionCompleted` dispatches `SignForRecipient`. If the refusal lived only in the aggregate, the bookkeeping would be refused and the PDF signed anyway. That leaves signed bytes out of turn with no record to explain them. [BL-33](../BACKLOG.md) recorded this correction on 2026-09-02. So the refusal has to come **before the fact is emitted** (ADR-0066 §2.5).

**The seal predicate asks the wrong question.** Once an out-of-turn completion lands, `Envelope::advanceToNextStepOrSeal()` asks `nextActivatableStepValue()`. That helper only considers ordinals **greater than** the step just completed. When the highest step closes out of turn it finds no candidate and calls `markReadyToSeal()`, and the open steps beneath it are invisible. When a middle step closes out of turn, the next step activates and the earlier one stays open forever. That is [BL-199](../BACKLOG.md). It cannot fire without BL-33, but the predicate is independently wrong.

**It fired.** Restated from the workspace incident note and the BL-33 and BL-199 rows:

- Preprod, 2026-08-27. Envelope `01a0427d-1b4d-7643-bec3-06eb5e748d72` was `SIGN_ORDERED` with three steps.
- The step-3 recipient signed while step 1 was still the active step. Step 3 closed without ever being activated.
- The envelope reached `COMPLETED` and sealed carrying **one signature of three**. Steps 1 and 2 were left `PENDING`.
- Step 1 was still active because its signer's signature had been swallowed by a separate defect. After a PostgreSQL 16 → 18 dump/restore the cluster's transaction-id counter restarted below the relay's restored checkpoint, so new facts were never read. That defect has its own fix and is not this task's.
- Two further facts are not in the note or in either row; they are the operator's account, given on 2026-09-15. The envelope's signing mode was `SEQUENTIAL_PADES`, which is why SignatureExecution signed the PDF per recipient. The step-3 recipient's link came from the sender-side mint (`POST /api/v1/signing-tokens`).

**BL-33 says two doors ignore step order. Today there is one.** A dormant-step recipient needs a link, and the tokens minted on `RecipientStepActivated` only reach active steps. The census classifies five callers of the issuer: four take the `SigningTokenIssuer` port directly (three Notification use cases and `SigningTokenIssuance`), and `MintSigningTokenController` reaches it through `SigningTokenIssuance`. The three in Notification all refuse a dormant step today. `NotifyActivatedStepRecipientsUseCase` only ever sees the step that activated. `NotifyCorrectedRecipientUseCase` returns early on `stepHasActivated()`. `NotifyResentInvitationRecipientUseCase` sits behind `Envelope::resendInvitation()`, which throws `RecipientNotResendableException::stepNotActivated`. `SigningTokenIssuance::issueFor()`, behind the sender-side mint, is the one door left. BL-33's *"one of the two doors … the sender-side mint, or a contact correction"* is one door out of date.

**The mint is not the whole exposure.** Tokens minted before this ships still exist: issuance is additive (TASK-028 §4.3), and the only thing that retires a link is a contact correction (ADR-0060 §2.6). So the refusal must also sit at every route a token or credential reaches, not only at issuance.

## 2. What already exists (reuse, do not rebuild)

⚑ **Past tense since 2026-09-16: this section describes the tree at `f036e4c`, before §3 landed.** Two symbols it names are gone — `NotifyCorrectedRecipientUseCase::stepHasActivated()` (deleted by §3 #4, which is the point of the bullet) and, in §3 #16's account, `Envelope::nextActivatableStepValue()`. Nothing here is a claim about the tree today.

- **The domain predicate.** `Step::isActivated()` is `activatedAt !== null`. `Envelope::resendInvitation()` already refuses a dormant step with `RecipientNotResendableException::stepNotActivated()`, code `RECIPIENT_STEP_NOT_ACTIVE`, published on `ResendInvitationController`. ADR-0066 §2.1 keeps that exact meaning: activated, not "activated and not completed".
- **A view-side copy, by ordinal.** `NotifyCorrectedRecipientUseCase::stepHasActivated()` matches `StepView::$ordinal` against `RecipientView::$stepOrdinal`. It is fail-closed on a step it cannot resolve. It is replaced by the shared method, not copied.
- **The data, already loaded, so no new SQL.** `EnvelopeContextView::$steps` holds `StepView`s carrying `$id` (a `StepId`) and `$activatedAt`. `DoctrineEnvelopeReadRepository::findContextForSE()` already selects `activated_at`. `GetEnvelopeContextForRecipientHandler` projects down from that same read, and `RecipientView` already carries `$stepId` beside `$stepOrdinal`.
- **A precedent for a derived predicate on a Contract view.** `RecipientView::isUnclaimedSlot()`.
- **The crossing and its shape.** `RecipientAuthContextReader::read()` is where Session learns about the envelope, behind the token seam. It already carries three facts computed there: `envelopeIsAlive`, `documentIsWithheld` (required, no default) and `signsElsewhere` (ADR-0055 §2.16). The same file documents what a permissive default costs. `invitationsRevokedAt` was optional with a `null` default, so every crossing compiled and the guard never fired. That is why ADR-0066 §2.2 makes the new members required.
- **The recipient-facing code, already published and never written.** `SigningSessionUnavailableException::stepNotActive()` produces `STEP_NOT_ACTIVE`. Today only `SigningSessionReader`'s `RecipientOutcome::SKIPPED` arm throws it, and the `RecipientOutcome` docblock records that nothing in `src/` or any migration has ever written `SKIPPED`. `config/packages/nelmio_api_doc.yaml` already publishes both `STEP_NOT_ACTIVE` and `RECIPIENT_STEP_NOT_ACTIVE`, so no code is new.
- **The census.** [`SigningReadersRefuseUnsentEnvelopeTest`](../../tests/F5Sign/Session/Application/Query/SigningReadersRefuseUnsentEnvelopeTest.php) derives every `->getContextForRecipient(` crossing and every `SigningTokenIssuer` caller from the source tree. It classifies them on several axes: the unsent axis, the terminal axis with `REFUSES` / `CARRIES` / `EXEMPT` dispositions, the issuer-caller axis and the claimable-slot axis. It fails naming anything unclassified. This task adds one more axis to it.
- **Acceptance support.** `SeedsSentEnvelopes::seedSentEnvelope()` seeds through real commands but authors a **single** step (`StepOrdinal::of(1)`). `OpensSigningSessions::mintSessionCredential()` mints a session credential directly. `LeakedLinkRefusedHttpTest` and `UnsentEnvelopeRefusedHttpTest` already take a `SigningTokenIssuer` directly, bypassing the mint's guards. `DrivesEventLogRelay::pumpEventLogRelay()` drives the relay. The sibling tests to model on are [`UnsentEnvelopeRefusedHttpTest`](../../tests/F5Sign/Session/Acceptance/UnsentEnvelopeRefusedHttpTest.php) and [`TerminalEnvelopeClosesTheCeremonyHttpTest`](../../tests/F5Sign/Session/Acceptance/TerminalEnvelopeClosesTheCeremonyHttpTest.php). ⚠ No acceptance test reads `platform.event_log` today: `rg -ln 'event_log' tests` lists Integration, Application and Unit files and nothing under any `Acceptance/` directory. The delivery bar's row assertion is therefore new at that tier, and the Integration tests that already read the log (for example `tests/F5Sign/Integration/AuthMilestoneFactsReachTheLogTest.php`) are where to copy the query shape from.
- **Multi-step aggregate fixtures.** `EnvelopeBuilder::withStep(int $ordinal)`, `withRecipient(..., int $step)` and `buildSent()`. The closest aggregate sibling for the seal frontier is `EnvelopeCompleteTest`.
- **Test doubles.** `FakeEnvelopeQuery` already offers `neverSent()`, `withStatus()` and `withCredentialsRetiredAt()`. `RecipientContextProjection::of()` builds a `RecipientEnvelopeContextView` from an `EnvelopeContextView` for Notification, SignatureExecution and Session tests.

## 3. What gets built

| # | Where | What |
|---|-------|------|
| 1 | `Envelope/Contract/View/EnvelopeContextView` | `recipientStepIsActive(RecipientView $recipient): bool`. It matches `steps[*]->id` against `$recipient->stepId`, returns `activatedAt !== null` and returns `false` when no step matches (ADR-0066 §2.1). |
| 2 | `Envelope/Contract/View/RecipientEnvelopeContextView` + `GetEnvelopeContextForRecipientHandler` | New required `bool $recipientStepIsActive` with no default. The handler fills it by calling #1. |
| 3 | `tests/F5Sign/Envelope/Testing/Fake/RecipientContextProjection` | Calls #1 rather than re-deriving it, so the double reimplements no logic (`CLAUDE.md` authoring rule 4, last bullet). |
| 4 | `Notification/Application/UseCase/NotifyCorrectedRecipientUseCase` | `stepHasActivated()` is deleted and the guard calls #1. Behaviour is identical for every envelope whose step ids and ordinals agree, which is every real one. |
| 5 | `Session/Application/Query/RecipientAuthContext` + `RecipientAuthContextReader::read()` + `Session/Application/Command/StartSession` | New required `bool $stepIsActive` on the context, beside `documentIsWithheld`, filled from `$context->recipientStepIsActive`. `StartSession` gains the same required field, as it did for `documentIsWithheld` and `signsElsewhere` (ADR-0066 §2.2). |
| 6 | `Session/Application/Service/SigningTokenIssuance::issueFor()` + `SigningTokenNotIssuableException` | New factory producing 409 `RECIPIENT_STEP_NOT_ACTIVE`. It is thrown behind the existing `sentAt`, unclaimed-slot and signs-elsewhere refusals (ADR-0066 §2.4, §2.6), so nothing is minted. |
| 7 | `StartSessionUseCase` | 409 `STEP_NOT_ACTIVE`, behind the withheld-document and signs-elsewhere refusals and **before `startIfAbsent()`**, so no session row or credential is written. |
| 8 | `GetAuthDescriptorController` | 409 `STEP_NOT_ACTIVE`, beside the revoked-link refusal. |
| 9 | `IssueAuthChallengeUseCase::issue()` | 409 `STEP_NOT_ACTIVE` after the revoked-link refusal, for the browser route and its machine twin (`/envelopes/{id}/recipients/{recipientId}/auth/otp/send`). Skipped while `envelopeIsAlive` is false, so the aggregate's existing dead-envelope refusal still wins (ADR-0066 §2.6). |
| 10 | `SubmitAuthResponseUseCase::submit()` | Same as #9, for `/signing/session/auth` and `/envelopes/{id}/recipients/{recipientId}/auth`. |
| 11 | `SigningSessionReader::read()` | 409 `STEP_NOT_ACTIVE` after the retired-credential refusal. |
| 12 | `SigningDocumentReader::read()` | Returns bare `null` (404), the shape of its sibling refusals. |
| 13 | `CommitSignatureUseCase` | 409 `STEP_NOT_ACTIVE` after the retired-credential refusal and before `commitSignature()`, skipped while `envelopeIsAlive` is false. **This is the guard the delivery bar sabotages.** |
| 14 | `CommitDelegatedSignatureUseCase` | 409 `STEP_NOT_ACTIVE` after `$auth` is read and **after** the assertion checks, skipped while `envelopeIsAlive` is false. ⚑ **Amended 2026-09-16**: this cell read *"before the assertion checks"* and shipped that way; `5143466` moved the guard below them, closing [`BL-263`](../BACKLOG.md) — ADR-0066 §2.6's amendment carries why, and §8 records what it cost the pin. |
| 15 | `SigningSessionUnavailableException::stepNotActive()` | Docblock and message widened to cover **not yet active** as well as skipped. The code does not change. |
| 16 | `Envelope::advanceToNextStepOrSeal()` | `nextActivatableStepValue()` is replaced by the **frontier**, the lowest-ordinal step not completed. No frontier means `markReadyToSeal()`. A frontier that is not activated gets `activateStep()`. A frontier already activated means nothing happens, and in particular `RecipientStepActivated` is not re-recorded, although `activateStep()` records it unconditionally today. INV 20's order (`StepCompleted` before `RecipientStepActivated`) is kept (ADR-0066 §2.7). |
| 17 | `#[OA\*]` on every controller behind #6–#14 | Re-read each whole prose block, not the changed line. `CommitSignatureController`'s 409 stops saying *"Three distinct conditions"*. `MintSigningTokenController` and `CommitDelegatedSignatureController` gain their code. `GetAuthDescriptorController`, `SendRecipientAuthOtpController` and `SubmitRecipientAuthResponseController` publish no 409 today and gain one (ADR-0066 §3.2). `GetSigningSessionController`'s 409 lists `STEP_NOT_ACTIVE` among "no interactive ceremony to open", and its wording must cover a step not yet reached. `CommitDelegatedSignatureController`'s 409 also names `ENVELOPE_NOT_SENT` and `RECIPIENT_SLOT_NOT_CLAIMED`, which `CommitDelegatedSignatureUseCase` never raises (§7). **Those two clauses are left untouched on purpose.** Narrowing or realizing them is TASK-033's surface, not this task's, so the whole-block re-read must neither fix them in passing nor drop them without saying so. |
| 18 | `tests/F5Sign/Support/SeedsSentEnvelopes` | Multi-step seeding **by a parameter or a sibling method on this trait, never a second seeding trait.** |
| 19 | `SigningReadersRefuseUnsentEnvelopeTest` | A step-activeness axis classifying every crossing and every issuer caller. It follows the terminal axis's shape: every row names an existing case, and a guarded crossing is counted per callsite. |
| 20 | `tests/F5Sign/Session/Acceptance/DormantStepRefusedHttpTest.php` (new) | The delivery bar; see §6.3. |
| 21 | Fixtures | 17 test files build an `EnvelopeContextView` with `steps: []` (18 contain the literal), and 12 go through `RecipientContextProjection::of` (count with `rg -l 'steps: \[\]' tests` and `rg -l 'RecipientContextProjection::of' tests` at the time of the change). The Session reader and controller tests among them need an **activated step whose id matches the recipient's `stepId`**. `FakeEnvelopeQuery` gains `onDormantStep()`, spelled as the predicate like `neverSent()`, **not** as a status or ordinal change. Every direct `new RecipientEnvelopeContextView(` and `new RecipientAuthContext(` takes the new required member. |
| 22 | `docs/frontend-handoff/TASK-042-*.md` (new) | The signer must route `STEP_NOT_ACTIVE` on the commit response (§7). `STEP_NOT_ACTIVE` can now arrive on open, descriptor, OTP and auth submit. An integrator receives `RECIPIENT_STEP_NOT_ACTIVE` from the mint and `STEP_NOT_ACTIVE` from the delegated commit and the machine auth twins. |
| 23 | `docs/BACKLOG.md` | BL-33 and BL-199 move to Closed, naming this branch. BL-183 is annotated that its step half is closed and its outcome half is not. |
| 24 | `docs/ddd/` | [`signing-session-domain-model.md`](../ddd/signing-session-domain-model.md) and [`envelope-domain-model.md`](../ddd/envelope-domain-model.md). |
| 25 | `docs/adr/` | ADR-0066 and its three `docs/adr/README.md` entries, landed alongside this record, plus `(ADR-0066)` in the docblocks of #1, #5, #6 and #16. |

**No `deptrac.yaml` change and no new cross-BC dependency.** Session already reads `EnvelopeContract`, and every new fact crosses on a view that already crosses.

## 4. Scope

**In:** everything in §3, the tests and sabotages of §6, ADR-0066, this record, and the backlog and `docs/ddd/` reconciliation.

**Out, by decision:**

- **The signer frontend change.** It lives in another repository and ships as its own PR. This task owns only the handoff (#22) that states what it must do.
- **Preprod envelopes that may already be corrupted.** Not diagnosed and not repaired. A guard does not repair a row, and no backfill is written here.
- **BL-183's outcome half.** A DELEGATED or SKIPPED leg is still invisible to the pre-credential routes. This task crosses step activeness, not `RecipientOutcome`.
- **`POST /api/v1/signing/session/renew`.** It reads no envelope context (`RenewSessionCredentialUseCase` names neither `authContext` nor the envelope query port), and every route a renewed credential buys is guarded by §3. Adding the envelope read there would run a cross-BC read on every renewal to answer a question the next request answers anyway. ADR-0059 declined the same read for a related reason.
- **`Envelope::recordRecipientCompletion()` and `SignForRecipientUseCase`.** Neither gets the guard (ADR-0066 §2.5). With §3 in place both are unreachable out of turn. The second runs after the fact and would dead-letter a message rather than refuse a request.
- **Retiring already-minted tokens.** Issuance stays additive (TASK-028 §4.3), and the only retirement that exists is ADR-0060 §2.6's contact-correction anchor. Tokens minted before deploy are refused at use rather than retired (§7).

## 5. Key decisions

These are task-level decisions. The architectural ones are ADR-0066's and are not restated here.

### D1. The harness is the main checkout, with a baseline taken before the first edit.

This branch lives in the main checkout, so `make -C ../f5sign-infra {lint,phpstan,test,qa}` and `make -C ../f5sign-infra composer cmd=arch` validate *this* tree. Verify that rather than assume it: `git rev-parse --git-dir` is `.git`, `git -C ../f5sign-infra status --porcelain` is empty, the committed `docker-compose.override.yml` binds `../f5sign-backend`, and the running container mounts this checkout (`docker inspect f5sign-php-fpm` lists the `f5sign-backend` directory at `/var/www/html`). The last check is not redundant: `make test` and `make qa` exec into the `php-fpm` already running, which keeps the mount it was created with, so a clean infra tree says nothing about what that container was created from. Tell the other sessions before taking the shared stack. Record the pre-work baseline as a **test count only**. TASK-041's Status row records that the assertion count is non-deterministic on an unchanged tree: `ConcurrentAuthSubmissionTest`'s two-process row-lock probe interleaves differently from run to run. An assertion delta would therefore look measured and be noise. Measured 2026-09-15 on `f036e4c` through `make -C ../f5sign-infra test`: `2959 tests`, **1 error and 1 failure, both pre-existing and outside this task** — `StorageLifecycleScenarioTest` (its frozen clock now leads the wall clock by a year, so its signing step falls after the development DSS signing certificate's `notAfter` and DSS answers 500 *Expired certificate found*) and `DocumentationLinkTest` (the docblock links to `CLAUDE.md` do not resolve inside the container on this workspace). Every later run is compared against those two names, not against a green bar.

### D2. One commit per green piece, in dependency order.

The order is: predicate (#1–#4), then crossing (#5), then refusals by layer (#6–#15 with their fixtures), then the seal frontier (#16), then acceptance (#18–#20), then docs (#17, #22–#25). Each commit passes the gates on its own. The published contract (#17) may ride with the refusal it describes when that keeps a commit truthful.

### D3. The 409 at the edge is what separates this fix from the wrong fix; the event-log query is a redundant end-to-end check.

⚑ **Rewritten 2026-09-16 after an adversarial test review measured this decision false, and the measurement is the point of the entry.** It read: *"A 409 on the commit and an untouched step 3 would both hold for a fix that only guarded the aggregate, because the aggregate would refuse the bookkeeping. **Only the absence of a `SESSION_COMPLETED` row in `platform.event_log` for that session shows the fact was never emitted.**"* Both halves are wrong **in this harness**:

- **An aggregate-only guard would not produce a 409 here at all.** The bookkeeping it would refuse runs in the Envelope completion reactor ([`OnSessionCompleted`](../../src/F5Sign/Envelope/Application/Subscriber/OnSessionCompleted.php)), and that reactor never runs in an acceptance test: `save()` appends to `platform.event_log` and nothing else (ADR-0031 retired the outbox), `config/packages/messenger.yaml`'s `when@test` makes `async_events` `in-memory://`, the relay is a separate process, and **this file never drives it**: it takes `SeedsRelayCheckpoint` for the BYPASSRLS reader connection and **not** [`DrivesEventLogRelay`](../../tests/F5Sign/Support/DrivesEventLogRelay.php), which is the trait whose `pumpEventLogRelay()` is the only thing in the suite that drains the log into the reactors (`rg -l DrivesEventLogRelay tests/` names its users; this file is not among them). **Measured**: a throw inside that reactor leaves `DormantStepRefusedHttpTest` fully green, `OK (2 tests, 79 assertions)`. So the wrong fix answers the HTTP commit **200**, which the 409 assertion three lines above the log query catches on its own.
- **The log absence does not pin the guard's placement either.** Every command runs inside `DbalTransactionMiddleware`'s transaction and the log append is a row in it, so **any** throw in the handler takes the append back. **Measured**: moving the commit's step guard to *after* `$this->sessions->save($session)` leaves the whole acceptance file green; the only red is hermetic, `CommitSignatureUseCaseTest::a_recipient_whose_step_has_not_been_reached_signs_nothing` at `assertNull($sessions->saved)`.

**What actually discriminates**, and what the bar is therefore stated as: the **409 `STEP_NOT_ACTIVE`** at each edge — status *and* `code` — plus the hermetic absence-of-effect assertions one tier down, which are the pair that separates *the guard exists* from *the guard sits before the write*: `assertNull($sessions->saved)`, `saveCount === 0` and *no `SessionCompleted` pending*, each beside a liveness control.

**The log query stays, as a redundant end-to-end check that the fact is not written.** Redundant is not decorative: it is a real query over real SQL, and its trailing positive control proves it looks where the rows are — the same query returns `[SIGNATURE_COMMITTED, SESSION_COMPLETED]` for the step-1 recipient. What it cannot do is fail while the 409 holds, because it can only fail when the commit is *allowed*.

⛑ **The fix and its placement are unchanged, and none of the above weakens them.** The refusal still has to come before the fact is emitted (ADR-0066 §2.5) — in production both reactors *do* run off the drained log, which is the whole reason an aggregate-only guard is the wrong fix (§1). What was wrong was the account of which assertion proves it.

### D4. The id-versus-ordinal sabotage is catchable at the view tier, and only there.

Inside the aggregate, steps are keyed by ordinal and a recipient resolves its step through that key, so a step's id and ordinal cannot disagree. A `StepView` fixture and a `RecipientView` fixture **can** disagree: a step whose `id` matches the recipient's `stepId` while its `ordinal` does not match `stepOrdinal`, and the reverse. That fixture is what makes #1's `StepId` match discriminating. Without it, matching by ordinal — what `stepHasActivated()` did until §3 #4 deleted it — passes every test. ⚑ Both directions of the disagreement were built, not only the convenient one.

### D5. A fixture helper that names the predicate, not a state.

`FakeEnvelopeQuery::onDormantStep()` sets up "this recipient's step is not active" directly. It does not pick a status or shuffle ordinals. A fixture that produced dormancy through some other state would let a guard that reads the wrong field still pass (`CLAUDE.md` authoring rule 4, *a fixture whose variables always agree cannot fail*).

## 6. Verification

### 6.1 Gates

From the main checkout (D1): `make -C ../f5sign-infra lint`, `make -C ../f5sign-infra phpstan`, `make -C ../f5sign-infra composer cmd=arch`, `make -C ../f5sign-infra test`, and finally `make -C ../f5sign-infra qa`, which adds Infection. Infection is judged on **covered-MSI** against the `minCoveredMsi` floor in `infection.json5.dist`; read the floor there rather than from a number here. Quote what the run printed. Before citing a green run, check its sha is the branch tip, since later commits touching `src/` invalidate it.

### 6.2 Tests and sabotages

Each sabotage is applied, run, observed red **for the stated reason** and restored.

⛔ **Several guards sit in series on every route, so check WHICH guard fired, not merely that the test went red or stayed green** (`CLAUDE.md` authoring rule 4). A dormant-step case over an envelope that is also unsent or dead is refused upstream, and would stay green with the step guard deleted. Every dormant-step fixture is otherwise a sent, live, platform-signing, claimed recipient.

| # | Tier / file | Case | Sabotage → expected red |
|---|---|---|---|
| 1 | Unit, `tests/F5Sign/Envelope/Unit/Contract/View/` | `recipientStepIsActive` answers active, dormant and absent-step. It also answers correctly on a fixture where `StepView::$id` matches `stepId` but `ordinal` ≠ `stepOrdinal`, and on the reverse (D4). | Match by ordinal → red on the disagreeing fixture. Return `true` for an absent step → red on the absent case. |
| 2 | Application, `GetEnvelopeContextForRecipientHandlerTest` | Projects `true` for an activated step and `false` for a dormant one. | Hard-code `recipientStepIsActive: true` → red on the dormant case. |
| 3 | Application, `NotifyCorrectedRecipientUseCaseTest` | The existing dormant-step case still sends nothing. | Remove the guard → red. |
| 4 | Application, `SigningTokenIssuanceTest` | Dormant step → `RECIPIENT_STEP_NOT_ACTIVE` **and nothing minted**. | Delete the guard → red naming this case. |
| 5 | Application, `StartSessionUseCaseTest` | Dormant step → `STEP_NOT_ACTIVE`, no session saved and no credential minted. | Delete the guard → red. |
| 6 | Application, `IssueAuthChallengeUseCaseTest` | Dormant step → `STEP_NOT_ACTIVE`, no challenge issued and no event pending. | Delete the guard → red. |
| 7 | Application, `SubmitAuthResponseUseCaseTest` | Dormant step → `STEP_NOT_ACTIVE`, no attempt spent and no event pending. | Delete the guard → red. |
| 8 | Application, `SigningSessionReaderTest` | Dormant step → `STEP_NOT_ACTIVE`. | Delete the guard → red. |
| 9 | Application, `SigningDocumentReaderTest` | Dormant step → `null` on a fixture whose bytes **would** otherwise be served. | Delete the guard → red, printing bytes. |
| 10 | Application, `CommitSignatureUseCaseTest` | Dormant step → `STEP_NOT_ACTIVE`, nothing saved and no `SessionCompleted` pending. | Delete the guard → red. |
| 11 | Application, `CommitDelegatedSignatureUseCaseTest` | Dormant step → `STEP_NOT_ACTIVE` for an act the route accepts (`MACHINE_KEY`, asserting correctly), **and `ASSERTION_NOT_ACCEPTED` — not the step — for a `SIGNING_PLATFORM` recipient carrying one**. ⚑ **Inverted 2026-09-16**: this bar read *"`STEP_NOT_ACTIVE` before any assertion check"* and was met as written; [`BL-263`](../BACKLOG.md) moved the guard below them (ADR-0066 §2.6), so the second clause is now the opposite of what it was. | Delete the guard → red on the first. Move it back above the assertion checks → red on the second, naming `STEP_NOT_ACTIVE`; the first stays green, which is why it cannot carry this bar alone. |
| 12 | Application, the test files of rows 6, 7, 10 and 11 | **Precedence**: a dead envelope on a dormant step still yields the existing dead-envelope refusal, not `STEP_NOT_ACTIVE` (ADR-0066 §2.6). | Drop the `envelopeIsAlive` skip → red on this case. |
| 13 | Descriptor route | Dormant step → 409 `STEP_NOT_ACTIVE`. There is no controller unit test for `GetAuthDescriptorController` today, so this is proved by row 16's acceptance case unless a sibling-tier test is added. | Delete the guard → red. |
| 14 | Census, `SigningReadersRefuseUnsentEnvelopeTest` | Every crossing and every issuer caller is classified on the step axis, and every row names an existing case. | Drop a known member → red **naming it**. Add a second, unguarded crossing to a classified class → red on the per-callsite count. |
| 15 | Unit, Envelope aggregate (`EnvelopeBuilder`, beside `EnvelopeCompleteTest`) | Step 3 of 3 closes while step 1 is active → no `READY_TO_SEAL` and no `RecipientStepActivated`. Step 2 of 3 closes while step 1 is active → step 3 is not activated. A flow that runs in order still seals. | Restore `nextActivatableStepValue()` → red on the first case. |
| 16 | Acceptance, `DormantStepRefusedHttpTest` | See §6.3. | Remove the commit guard (§3 #13) → 200 and a `SESSION_COMPLETED` row appears. |

Fixture updates (§3 #21) are not tests of their own. They are what keeps every pre-existing Session reader and controller case describing a recipient who **may** act, which is what those cases always meant.

### 6.3 The acceptance case

Modelled on `UnsentEnvelopeRefusedHttpTest` and `TerminalEnvelopeClosesTheCeremonyHttpTest`:

1. Seed a sent **three-step** envelope through the extended `SeedsSentEnvelopes` (§3 #18). Only step 1 is active.
2. **Mint**: the sender-side mint for the step-3 recipient → 409 `RECIPIENT_STEP_NOT_ACTIVE`.
3. **Open**: a step-3 token issued directly through `SigningTokenIssuer`, standing in for a link minted before deploy → `POST /api/v1/signing/session` and `GET /api/v1/signing/session/auth` both answer 409 `STEP_NOT_ACTIVE`.
4. **Read, bytes, commit**: a credential from `mintSessionCredential()` → read model 409, document bytes 404, commit 409 `STEP_NOT_ACTIVE`.
5. **Delegated commit** for a dormant-step recipient → 409 `STEP_NOT_ACTIVE`.
6. **Over real SQL**: the envelope is still `SENT`. Step 3's `activated_at` and `completed_at` are null and its recipient is `PENDING`. `platform.event_log` holds **no `SESSION_COMPLETED` and no `SIGNATURE_COMMITTED` row** for that session. ⚑ **Corrected 2026-09-16**: this step cited D3 as *the* discriminating observation. It is not — it is a **redundant** end-to-end check that the fact is not written, kept deliberately, and what discriminates is step 4's and step 5's 409 with its `code`, plus the hermetic no-effect assertions of §6.2 rows 5–11. D3 states what was measured and why the query stays.
7. **Positive control**: the step-1 recipient commits and gets 200. Without this the case would pass on a system that refuses everyone.

### 6.4 The sweep, immediately before each commit

```bash
rg -n 'BL-33|BL-199|stepHasActivated|STEP_NOT_ACTIVE' src tests migrations config docs CLAUDE.md
```

Read the hits for **tense**. Run the sweep last, before each commit, not once as a phase: a change made after a sweep invalidates it (`CLAUDE.md` authoring rule 1). Also `rg` the rejected spelling, `stepOrdinal` compared against `StepView::$ordinal`, because stale prose points at the shape that lost.

## 7. Open follow-ups (track, don't solve here)

- **The signer must route `STEP_NOT_ACTIVE` on the commit response.** In `f5sign-signer` at `develop` `c894f88`, `useSignFlow`'s `mapError` sends a 409 `CONFLICT` or `ALREADY_SIGNED` to the done page. A 409 `STEP_NOT_ACTIVE` has no branch, so it falls into the generic `failed` error, which is also reported to Sentry as an unplanned failure. That happens even though a comment there says those codes are "handled below". The code-to-path table in `useSignerNavigation` already maps `STEP_NOT_ACTIVE` to `/unavailable`, but `mapError` never consults it for a 409. Owed by the handoff (§3 #22). ⚑ **The handoff landed on 2026-09-16** as [`TASK-042-no-recipient-acts-before-their-step.md`](../frontend-handoff/TASK-042-no-recipient-acts-before-their-step.md) (`d22bab6`), and it covers the four other routes that can now answer `STEP_NOT_ACTIVE` as well as the commit. **The signer change is committed on their side and not pushed**: `f5sign-signer` `639a788`, on `develop`, routes a 409 `STEP_NOT_ACTIVE` on the commit to `/unavailable` with a breadcrumb rather than a Sentry event — read in their clone on 2026-09-16, where it sits in `origin/develop..develop`. Nothing in this repository can gate it. Until it is deployed, a dormant-step signer who reaches the commit on the deployed signer still sees a generic failure instead of "not your turn yet". ⛑ **Corrected 2026-09-16**: this read *"The signer change itself is still owed … Until it ships"*. ⛑ **Superseded later on 2026-09-16: pushed.** In the same clone `origin/develop` = `develop` = `7ce2958`, and `git log c894f88..origin/develop` lists six commits, `639a788` first. Still not deployed, and it ships in one deploy with this backend ([ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) §2.6, amended that day).
- **Preprod envelopes may already be corrupted.** Envelope `01a0427d-…` is known. Others are not looked for, by decision. What would force the work: any envelope found `COMPLETED` or `READY_TO_SEAL` with a step whose `activated_at` is null.
- **`renew` still reads no envelope context.** It is harmless because every route a renewed credential buys refuses (§4). What would force it: a renewal-bought route added without a step guard. The census axis in §3 #19 is what catches that.
- **Tokens minted before deploy still exist.** They are refused at every use rather than retired. The only retirement that exists is ADR-0060 §2.6's anchor, which moves on a contact correction and on nothing else, and TASK-028 §4.3 declined revocation as a feature. Retiring links on the step axis would be a new decision, not this task's. What would force it: a route such a link reaches that does not refuse a dormant step, which the census axis of §3 #19 exists to catch, or revocation becoming a feature in its own right, which reopens TASK-028 §4.3.
- **[BL-183](../BACKLOG.md)'s outcome half.** A DELEGATED or SKIPPED leg is still invisible to the descriptor and the OTP send. It stays open with an annotation (§3 #23). ⚑ **The annotation was written on 2026-09-16**: the row now records that the step half crossed as a required member and that both pre-credential routes refuse on it, and that the outcome half is what keeps it `Open`. What would force it: the first writer of `DELEGATED` or `SKIPPED`. `RecipientOutcome`'s docblock records that nothing in `src/` or any migration writes either today, so the half is latent until one does.
- **Found while scoping this task, not ours:**
  - `Envelope::activateFirstStep()` calls `ksort()` on the list returned by `array_keys($this->steps)`. A list is already keyed `0..n-1`, so the call is a no-op. The order it relies on is insertion order, which `DbalEnvelopeRepository::loadSteps()` fixes with `ORDER BY ordinal ASC`. Harmless today, and misleading to a reader who trusts it. What would force it: any path that puts a step into `$this->steps` out of ordinal order before `activateFirstStep()` runs, since insertion order would then be the only thing deciding which step activates first.
  - `CommitDelegatedSignatureController`'s published 409 lists `ENVELOPE_NOT_SENT` and `RECIPIENT_SLOT_NOT_CLAIMED`. `CommitDelegatedSignatureUseCase` raises neither: its only collaborators are the session repository and `RecipientAuthContextReader`, which answers an unsent envelope with a 404 and asks no slot question. The published contract over-claims. Whether it should be narrowed or the codes realized belongs to TASK-033's surface. What would force it: a per-route code gate of the kind [BL-209](../BACKLOG.md) asks for, which would have to classify these two clauses before it could go green, or an integrator branching on either code for this route. ⛔ **There is a THIRD over-claim on that same block and this bullet missed it** — found by the contract check on 2026-09-16, indexed as [BL-249](../BACKLOG.md): the block also publishes `ALREADY_SIGNED`, which **nothing emits** (its condition is `SigningSessionStateException::sessionIsTerminal()`, which carries no `ProblemCoded`, so the boundary answers the default `CONFLICT`) and which is **not in the published `ProblemCode`** at all. Two of three were seen here and the third was not, on a block this task deliberately left alone — which is the argument for reading a whole prose block rather than the clauses one is already thinking about. ⚑ **`ALREADY_SIGNED` was retired on 2026-09-16** by [TASK-043](TASK-043-a-refused-commit-names-its-condition.md) / [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) (`8e99f33`), which makes the block's opening *branch on `code`* true for every code it names; the **other two clauses are still published** and are now [`BL-266`](../BACKLOG.md). Read the rest of this bullet as the record of what the contract check found, not as a description of the block.
  - `docs/adr/README.md`'s index lists ADR-0055 and ADR-0057 twice each (`rg -c '^\| \[ADR-0055\]' docs/adr/README.md` returns 2, and likewise for 0057). What would force it: the next edit to either row, which has to pick one of the two versions first, because the rows in each pair differ. ⚠ **One of the two ADR-0055 rows is additionally broken as Markdown**: it carries an unescaped `|` inside `SIGNING_PLATFORM | MACHINE_KEY`, which splits the cell, so that row renders wrong as well as twice.

- **Found while implementing and validating, and deferred by decision.** Each is indexed in
  [`docs/BACKLOG.md`](../BACKLOG.md) on 2026-09-16, because a deferral that lives only in a task section has no
  cross-cutting view and one that lives only in `var/` is lost. None is a blocker; none was fixed here.
  - **[BL-248](../BACKLOG.md)** — `AUTH_METHOD_NOT_CHOSEN` is reachable on both OTP-send routes and published on
    neither, and the spec states it on the descriptor, which cannot emit it. **This task gave the gap a second
    consumer**: the machine twin's new 409 points at the browser route's list *"whose 409 lists the other codes"*.
    What would force it: an integrator branching on `code` for a free-choice recipient, or [BL-209](../BACKLOG.md)'s
    per-route gate.
  - **[BL-249](../BACKLOG.md)** — the third over-claim on the delegated commit's 409, above. ⚑ **Closed
    2026-09-16** by [TASK-043](TASK-043-a-refused-commit-names-its-condition.md) /
    [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) (`8e99f33`): `ALREADY_SIGNED` is retired
    and the block publishes four codes a factory actually emits. **The other two over-claims above are not
    closed** and are now [`BL-266`](../BACKLOG.md), split out at that close so they keep an open row of their
    own.
  - **[BL-250](../BACKLOG.md)** — `machine_auth_otp_send`, `machine_auth_submit` and `commit_delegated_signature`
    declare no 404 although all three take both ids in the path and answer 404 for an unknown one; their browser
    twins declare it. Surfaced because this task added a 409 to each and re-read the blocks. What would force it:
    the first generated client, or [BL-209](../BACKLOG.md).
  - **[BL-251](../BACKLOG.md)** — the mutation gate cannot run through its sanctioned path on **any** branch while
    the two environmental reds stand: `composer qa` aborts at `@test`, and `composer infection` refuses to start
    over a red suite. The number in the Status row above came from a hand-rolled re-run that nothing records or
    repeats. What would force it: the first branch whose covered-MSI is genuinely in question. ⚑ **2026-09-16,
    later the same day: one of the two reds is gone.** `StorageLifecycleScenarioTest` was a frozen clock past a
    valid certificate rather than an expired one, and the development seal has been regenerated, so the row now
    names `DocumentationLinkTest` alone and records a run with that one test excluded. Read
    [BL-251](../BACKLOG.md) for the present state rather than this bullet.
  - **[BL-252](../BACKLOG.md)** — `minMsi` measured 50.37% against a floor of 50: ~45 mutants of headroom, down from
    the ~66 `infection.json5.dist` was calibrated against. Not this branch's doing (its own covered-MSI is 82.7%),
    but the branch that trips it will wear the red. The sanctioned response is a sabotage triage of the **new**
    not-covered entries — never attributing the broad flows, never moving the floor. ⚑ **Re-measured 2026-09-16
    on `fix/conflict-taxonomy`, which carries this branch**: MSI 50.095%, about 11 mutants of headroom. The
    figures, and what is and is not known about the drop, are in [BL-252](../BACKLOG.md) rather than here.
    ⚑ **Resolved 2026-09-16, so *"the branch that trips it will wear the red"* no longer holds**: the drop was
    uncoverable mutants in the concatenated prose of method-level `#[OA\*]` attributes, and the merge `2e00b0d`
    (`fix/msi-headroom`) removed them with `@infection-ignore-all` on each argument. Measured after it: MSI 55.91%,
    643 mutants of headroom. [BL-252](../BACKLOG.md) is Closed and carries the risks the fix leaves.
  - **[BL-253](../BACKLOG.md)** — `GetAuthDescriptorController`'s new 409 promises *"the same link is described
    normally once their step is active"*, which a dormant recipient on a **voided** envelope can never reach: that
    guard is the only one of the six with no `envelopeIsAlive` skip, correctly (§3 #8 — the descriptor reports
    terminal state in the 200 body rather than refusing), so the step simply never activates for them. Not a
    regression; the sentence claims more than the route can keep. What would force it: the first such recipient, or
    a copy pass over that block.
  - **[BL-254](../BACKLOG.md)** — `docs/frontend-handoff/README.md`'s *Handoffs vigentes* list named one of the
    nineteen files beside it. This task's own entry and TASK-041's were added on 2026-09-16 and sixteen are still
    missing; the list already warns that nothing watches it. What would force it: a reader trusting the list instead
    of `ls`.
  - **[BL-255](../BACKLOG.md)** — [TASK-037](TASK-037-claimable-invitation-and-visibility.md) names `stepHasActivated()`
    three times and this task deleted it. It is a **dated record**, so [`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §2
    says annotate and never rewrite — but one of the three is a **sabotage instruction**, which cannot be followed as
    written. What would force it: anyone re-running that sabotage.
  - **[BL-256](../BACKLOG.md)** — **closed 2026-09-16 by the maintainer, both rows corrected in place.** This
    bullet read that the two self-contradictions in
    [`signing-session-domain-model.md`](../ddd/signing-session-domain-model.md) were *"filed rather than fixed
    because each is a choice between two live sentences — the second is stated as a **decision** — and that is the
    maintainer's to make"*. The choices were made the same way in both: the **Access Token** row's *nothing revokes
    an earlier credential* is narrowed to keep its true half (a re-invitation retires nothing) and name the one
    retirement that exists, ADR-0060 §2.6's contact-correction anchor; and the **Gate HTTP edge** row records that
    its *deliberately not built* decision about route 4 was **overturned** by
    [TASK-022](TASK-022-delivered-codes-over-email.md), with the route named, rather than having the sentence
    deleted. Neither predated nor was caused by this task.
  - **[BL-257](../BACKLOG.md)** — the step refusal sits **above** the OTP limiter, by decision (ADR-0066 §2.6):
    nothing is sent and nothing is charged, which is what the route publishes. The side effect is that a link holder
    on a dormant step reaches the most abusable route in the system without spending limiter budget, at one cross-BC
    read per attempt. Recorded so the next audit finds a decision instead of rediscovering a defect.
  - **[BL-258](../BACKLOG.md)** — `worktrees/f5sign-backend/Senry` is a real worktree nested **inside** the main
    checkout, which the workspace `CLAUDE.md` forbids by name, and it is not in `.gitignore`. Verified per tool to
    contaminate **no** gate (php-cs-fixer, PHPStan, Infection and PHPUnit all have narrower path lists). Left
    untouched: it is another session's tree. What would force it: a `git add -A` in the main checkout.
  - **Not indexed, because it is one sentence and has no owner**: `NotifyActivatedStepRecipientsUseCase` still selects
    recipients by comparing `$recipient->stepOrdinal` against the activated step's ordinal — the shape ADR-0066 §2.1
    rejects for the predicate. It is pre-existing and **structural**: `RecipientStepActivated` carries an ordinal, not
    a `StepId`, so fixing it is an event-payload question. Harmless today because steps are not reordered after send,
    and the census classifies the use case `UPSTREAM` for exactly that reason. What would force it: any path that
    reorders steps on a sent envelope.

- **Found by three audits of this branch after it landed, and deferred by decision.** Each is indexed in
  [`docs/BACKLOG.md`](../BACKLOG.md) on 2026-09-16 as `BL-259`…`BL-265`, ids re-derived by grep at the moment the
  rows were written — over the working tree, every local and remote-tracking ref after `git fetch --all`, and every
  sibling worktree's working tree, the highest anywhere being `BL-258`. None is a blocker; none was fixed here.
  - **[BL-259](../BACKLOG.md)** — ⛔ **the highest-value row of the set.** `POST /api/v1/signing/commit` answers a bare
    `CONFLICT` for **three** conditions, and the signer sends all three to its done page — *your document is signed* —
    although for two of them (an envelope voided after authentication; a signing challenge that does not authorise
    that document set) nothing was signed. Reported by the signer session, which cannot fix it client-side: the
    three are indistinguishable on the wire and branching on `status` is what this route's own published prose
    forbids. Partitioning it means new published codes and a release coordinated with `f5sign-signer`, so it is a
    maintainer's decision. Its `ALREADY_SIGNED` half is [BL-249](../BACKLOG.md) and is cross-referenced, not
    duplicated. What would force it: the first signer shown *signed* on a cancelled envelope. ⚑ **Closed
    2026-09-16** by [TASK-043](TASK-043-a-refused-commit-names-its-condition.md) /
    [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) on `fix/conflict-taxonomy`: the three
    conditions became four named ones, and the fourth — a **drained** revocation — is a distinction the row
    could not see. ⚠ **The maintainer's decision this bullet reserved was taken and the release order is
    one-way**: the handoff landed before the merge (`6e8d443`), and the signer change is committed on their
    `develop` and not pushed (`639a788`, `2f4e721`, `eb5ac02`, `1638c6b`). If this backend is deployed before
    that signer is, the already-completed arm falls to their generic failure screen instead of their done page —
    the safe direction of the same defect. ⛑ **Corrected 2026-09-16**: this read *"the signer change is still
    owed, and until it ships the already-completed arm falls …"*. ⛔ **Qualified 2026-09-16, at the merge: the order
    is no longer one-way, it is one deploy**, confirmed by the maintainer. The signer removed its `CONFLICT`
    compatibility branch before either side deployed (`01ffece`), so a new signer breaks against the old backend
    just as the old signer breaks against this one — and there the already-completed arm is a **regression**, not
    the safe direction: a retry that cannot succeed, and a Sentry event on every retry. Both sides are pushed —
    both tasks on this `develop` (`f490218`, `acb20d0`), and the signer's `develop` at `7ce2958`, whose
    `c894f88..7ce2958` is the four commits above plus `01ffece` and `7ce2958` — so *"not pushed"* above stopped
    holding the same day. Nothing is deployed. ADR-0067 §2.6 carries the amendment and TASK-043 §7 the check.
  - **[BL-260](../BACKLOG.md)** — facts already in `platform.event_log` bypass all nine guards, which sit on the
    request path. A `SESSION_COMPLETED` row written before deploy is past them, and when the relay drains it
    `SignForRecipientUseCase` still applies an out-of-turn incremental PAdES under `SEQUENTIAL_PADES` — it carries no
    step predicate, deliberately (ADR-0066 §2.5). The incident's own co-cause was a stalled relay, so this is not
    hypothetical. What would force it: deploying while the relay is behind; the check is to confirm it has drained
    first.
  - **[BL-261](../BACKLOG.md)** — a recipient who signed out of turn **before** this fix is now permanently refused
    their own signed copy: a completed step that was never activated can never become the frontier, so `activated_at`
    stays null for ever, and the two readers now answer 409 and 404 where they used to serve. The repair is
    operational (the sender fetches over the `MACHINE_KEY` routes). The row carries the census query. It is the front
    half of bullet 2 above, which is why both stay.
  - **[BL-262](../BACKLOG.md)** — the census sees three of the nine guards; the other six live in
    `RecipientAuthContext` consumers, which is neither of its universes (ADR-0066 §5.5 calls them held by review
    alone). The mechanical repair is a fourth `callers()` needle on `$this->authContext->read(` — 8 call sites across
    7 classes today. What would force it: a new consumer that forgets to ask.
  - **[BL-263](../BACKLOG.md)** — **closed 2026-09-16 by `5143466`, and the code is what moved.** This bullet read
    that the step guard *"answers ahead of the platform/assertion refusal, so a `SIGNING_PLATFORM` recipient on a
    dormant step is told to wait and is then refused again for carrying an assertion … filed as a prose-versus-code
    tension … rather than as a bug"*. The maintainer resolved the tension the other way: `refusedForPlatformRecipient()`
    is a refusal **of standing** by §2.6's own list, so the old order masked one, and *wait for your step* was a remedy
    that could never work on a route that is never theirs. The guard now sits below both assertion refusals; §2.6 carries
    the amendment and §8 what it cost the pin.
  - **[BL-264](../BACKLOG.md)** — the mint has no terminal-envelope refusal, by a standing decision its own docblock
    defends, so a dormant recipient of a voided envelope now gets `RECIPIENT_STEP_NOT_ACTIVE` and its *until their
    step is active* promise. Same misleading remedy [BL-253](../BACKLOG.md) records for the descriptor, at a site
    that row does not name.
  - **[BL-265](../BACKLOG.md)** — latent: `frontierStep()` parks for ever on a step that can never complete, where
    the retired predicate stepped over it (that stepping-over was BL-199, so this is the cost of its fix). Unreachable
    today: `ensurePreSendInvariants()` refuses a recipient-less step and the roster is frozen at send. What would
    force it: any feature that removes a recipient after send, or a step whose completion predicate can fail.

## 8. Deviations & honest notes

Written at close on 2026-09-16, alongside §7's disposition. It is the **last** section and nothing above
it was renumbered, because `§N` are anchors cited from ADR-0066, from `docs/BACKLOG.md` and from this
record's own text.

### ADR-0066 was proposed for `Accepted` here, and the promotion was given on 2026-09-16

The decision is exercised, and the artifacts can be pointed at rather than asserted: the predicate
(`EnvelopeContextViewRecipientStepTest`, including both directions of the id-versus-ordinal
disagreement), the crossing (`RecipientAuthContext::$stepIsActive`, required, with
`GetEnvelopeContextForRecipientHandlerTest`), nine per-route Application cases, four
which-guard-fired precedence cases, the census axis with its five cases in
`SigningReadersRefuseUnsentEnvelopeTest`, the seal frontier's four cases in `EnvelopeSealFrontierTest`,
and the acceptance case `DormantStepRefusedHttpTest`, whose sabotage reproduced the preprod incident and
whose restored guard refuted it.

⛔ **At close the `Status` value was NOT changed, and this paragraph said why.** It read that `Accepted`
means *exercised* in this set and that it is, *"but the promotion is the maintainer's, it was reserved to
them on 2026-09-15, and taking it here would be this skill deciding something it is only allowed to
propose"*. What changed then was only the evidence: §5 and §6 said *"Nothing below exists"* while every bar
and every row had landed **in the same changeset**, and the header Status cell made four falsifiable claims
that this branch falsified. Those were repaired and the label left alone.

⚑ **The promotion was given on 2026-09-16**, after [`BL-263`](../BACKLOG.md) was settled by moving the
delegated commit's step guard below its assertion refusals (`5143466`) so that §2.6 and the code state one
order — the ADR's header, §2.3, §2.6, §5 and §6 and the `docs/adr/README.md` index row carry it. The form is
`Accepted (exercised)`, as this section said it should be. `Accepted (enforcement partial)` is **not** the
form, because nothing in §5 is held by argument alone — the three items under *Held by review alone* were
already declared as review at authoring time. ⚠ **Exercised is not deployed**: the branch is merged into
`develop` at `f490218` and pushed, nothing serves it, and the ADR's own header says so rather than letting
the label imply it. ⛑ **Corrected 2026-09-16, at the merge**: this read *"**Exercised is not merged**: the
branch is still neither merged nor pushed"*.

### D2 was relaxed by the maintainer, and "green" on this branch means the piece, not the commit

§5 D2 says *"Each commit passes the gates on its own."* On 2026-09-15 the maintainer relaxed it: the
per-commit gates became **lint + `composer cmd=arch` + `composer cmd=phpstan` + the filtered tests of the
touched classes**, with the **full suite** at the close of piece 3 (`1e12a88`, `2986 tests`) and piece 6,
and `make -C ../f5sign-infra qa` once at the end. The reason was cost: the shared stack is exclusive,
another session was waiting for it, and a full suite is minutes rather than seconds.

⚠ **The consequence, stated rather than glossed**: between `322ba10` and `1e12a88` no individual commit
was ever run against the whole suite, so **`git bisect` over that range cannot be trusted to the
commit** — the granularity of *green* on this branch is the piece. Nothing was found that would have
needed it, which is evidence of nothing either way.

### The seal frontier was built in a sibling worktree and cherry-picked

§3 #16 (BL-199) was built in parallel on branch `fix/seal-frontier`, in the sibling worktree
`../f5sign-backend-seal-frontier` cut from `dc88c1c`, and landed here as `7a54347` (cherry-pick of
`7a54347`). It was re-validated on the main checkout **after** the pick — lint `0 of 1303`, Deptrac
`0 violations / 0 uncovered`, `make phpstan` `[OK]`, `tests/F5Sign/Envelope/Unit` `OK (587 tests, 1497
assertions)` — rather than trusted from the worktree's own run.

⚠ **The worktree did not use the `wt-backend` lane, and that was deliberate**: the lane holds a `flock`
that the main checkout's own runs needed, and these were hermetic unit tests. It ran in an ad-hoc
container with the main checkout's `vendor/` mounted read-only and tmpfs caches, which is the shape
`CLAUDE.md` sanctions for a static or hermetic re-check and **not** for anything touching the database.
The cost was real and paid: the container left a root-owned `var/` inside the worktree, which had to be
deleted from a container before the worktree could be removed.

**Cleanup done 2026-09-16**: the worktree is removed (metadata and directory), `fix/seal-frontier` is
deleted after verifying its content identical to the cherry-pick, and the `/f5sign-backend-seal-frontier/`
line added to the **workspace root** `.gitignore` was reverted. `git worktree list` no longer names it.

### Scope

- **Nothing in the diff falls outside §4 In.** Measured at `d22bab6` — 76 files, all mapping onto §3
  #1–#22, #24 and #25; the documentation commits after it are §3 #23 and #25 plus this section, so
  re-measure with `git diff --stat f490218^1 f490218` — the merge's own diff against `develop` — rather
  than reading that number as current. ⛑ **Corrected 2026-09-16, at the merge**: the command read
  `git diff --stat $(git merge-base HEAD develop)..HEAD`, which on `develop` is empty. The §4 **Out** list is respected actively rather than by omission:
  `Envelope::recordRecipientCompletion()` gains no guard and carries a docblock saying the omission is
  the decision (`rg 'deliberately carries no step guard' src/`), and `SignForRecipientUseCase`,
  `RenewSessionCredentialUseCase`, the migrations directory and the token-retirement path are untouched.
- **One published block was corrected beyond what §3 #17 asked**, and it is recorded here because it is a
  scope deviation in the safe direction: `StartSessionController`'s 409 did not name
  `RECIPIENT_SIGNS_ELSEWHERE` although the route emits it. Fixed in `9f554ba` while the block was open.
- **`deptrac.yaml`, `phpstan.dist.neon` and `phpstan-baseline.neon` are untouched** — the diff against
  `develop` for all three is empty. No allowlist widened, no rule relaxed, no baseline entry added, so no
  ADR is owed on that axis.

### Decisions taken during implementation

- **§3 #14's ordering is pinned by the `SIGNING_PLATFORM` case, not by the no-assertion one — and on
  2026-09-16 the order it pins was inverted.** An act carrying **no** assertion never calls
  `startIfAbsent()`, so `findLockedForUpdate()` answers `null` and the route refuses from the no-session
  branch **above** the step guard — a case written that way would go green about a guard it never
  reached. That half is unchanged and is why the discriminating case has to carry an assertion.
  ⚑ **What changed**: this bullet read that the ordering was *"before the assertion checks"* and that
  *"the surplus-assertion refusal sits below the step guard, so `STEP_NOT_ACTIVE` is the discriminating
  answer"*. [`BL-263`](../BACKLOG.md) put that to the maintainer as a prose-versus-code tension and the
  answer was to move the code: `5143466` puts the step guard **below** both assertion refusals, so the
  discriminating answer for a `SIGNING_PLATFORM` recipient carrying an assertion on a dormant step is now
  `ASSERTION_NOT_ACCEPTED`. The arm left
  `a_recipient_whose_step_has_not_been_reached_commits_no_delegated_signature` and became
  `a_platform_recipient_on_a_dormant_step_is_refused_for_the_assertion_not_the_step`, with the opposite
  expectation; the case it left now says in its docblock that it cannot see the order, which is true of
  it in both worlds and was not said before. **Sabotage, measured 2026-09-16**: with the guard moved back
  above the assertion checks, exactly one case reddens — the new one — raising `STEP_NOT_ACTIVE` from the
  relocated guard, and the other seven stay green. Restored and byte-compared before the commit.
- **The acceptance case opens its session through the bus with `stepIsActive: true`** — the only site in
  the suite that passes that value for a recipient who may not act, and the case says so out loud. It is
  necessary because once the open refuses, **no route left in the system can produce that row**, and
  without the row the commit answers 404 and the guard under test is never reached. The alternative —
  inserting the row by hand — would have modelled a state the old system did not produce either.
- **`SigningSessionUnavailableException::stepNotActive()` lost its parameter entirely** (`37ffe1b`), after
  the security audit found the recipient's UUID interpolated into a `problem+json` `detail` on four
  **pre-gate** routes whose three sibling refusals deliberately carry no identifier. ADR-0066 §2.4 argued
  the disclosure cost of the *code* was nil, which is true of the code and was not true of an identifier.
  ⚑ **That retired the `RecipientId|RecipientRef` widening** added in `9f554ba` (`SessionUI` may not
  import `EnvelopeContract`, so the factory had been widened to accept either): with no parameter at all,
  the layer problem it solved no longer exists. Any handoff note mentioning that widening is describing a
  shape that survived seven commits.
- **Two `#[OA\*]` blocks gained a fresh closed count and then lost counts altogether.** §3 #17 asked
  `CommitSignatureController` to stop saying *"Three distinct conditions"*; `1e12a88` made it *"Four
  distinct conditions"*, and `MintSigningTokenController` went from *"distinguishes three conditions"* to
  *"distinguishes four"*. The contract check named that for what it was — a stale closed count replaced by
  a fresh one, in strings emitted verbatim into the spec the frontend ratifies — and `ac3152c` removed the
  counts from both, stating the property instead. ⚠ The first fix was *accurate on the day*, which is
  exactly why it passed review at the time.
- **The bytes reader's pre-existing refusal cases were not made dormant.** Every refusal there is the same
  bare `null`, so a dormant fixture would hide which guard fired.
- **Multi-step acceptance seeding is a `$steps` parameter on `SeedsSentEnvelopes`, never a second trait**
  (§3 #18), and the acceptance fixture's ids are generated per run because `platform.event_log` cannot be
  cleaned up and fixed ids would let a previous run's rows answer the positive control.

### Decisions that needed an ADR

None beyond ADR-0066, which was drafted with this record and is dealt with above. No ADR was minted
mid-branch, none was superseded, and no accepted ADR was contradicted.

### Properties declared and not proved

**None.** All sixteen §6.2 rows resolve to a collected, executed case; `0 skipped` plus the absence of any
`markTestSkipped(` call in `tests/` means collected implies executed. Row #16's event-log absence is a real
observation and not an artefact: real SQL on `platform.event_log` over a dedicated relay connection (the app
role holds no `SELECT` there), ids generated per run so an append-only table cannot make an absence look
true, and a positive control that runs **last** and finds the rows with the same query.

⚑ **Corrected 2026-09-16.** That paragraph called #16 *"the row that needed a discriminating harness"* and
said it *"has one"*. The harness is real and the query looks in the right place; what it is not is the
**discriminator** — D3 carries the two sabotages that measured this, and the property it names is held by
the 409 at the edge plus the hermetic no-effect assertions. The log query is kept as a redundant
end-to-end check. No §6.2 row lost its case, and none moved from proved to unproved.

### What validation caught that no gate could see

- **ADR-0066's own realization prose**, falsified by the changeset that wrote it (task-validate W1). Four
  clauses in the Status cell, §5, §6 and the ADR index row, all saying *nothing exists* about code that
  does. Repaired at close; the `Status` value left to the maintainer.
- **`docs/BACKLOG.md` untouched** although §3 #23 declared it In (W2) — including BL-199's *Where* column,
  which pointed at a symbol this branch deleted.
- **`docs/ddd/README.md`'s status rows** carrying no landing note (W3), although the model documents
  themselves were reconciled. ⚠ **A previous agent was told to leave that file alone** on the reasoning
  that the corrective siblings ADR-0058/0059/0060 did not touch it. That reasoning was wrong by half: those
  three left no note, and every *feature* landing since ADR-0049 did. The instruction was not re-derived
  from the file, and the validator caught it.
- **A third over-claim on the delegated commit's 409** (contract-check W2), on a block §3 #17 deliberately
  left alone after recording two — see §7.
- **The recipient UUID on the wire** (security audit W1), closed in-branch by `37ffe1b`.

### Honest notes

- **The one process slip recorded by the implementing agent**: a first filtered test run wrapped `timeout`
  around a `make` client, which the workspace forbids because it kills the client and leaves the container
  running. Caught and re-run; nothing downstream depended on it.
- **The workers, the relay and the custodian were down for the whole branch** and must be restored at
  close: `cache:clear` + `cache:warmup` with `APP_DEBUG=0`, then `make -C ../f5sign-infra worker-up`, then
  tell the other sessions. They were taken down because this branch changes constructors and the consumers
  run `APP_DEBUG=0` against a stale DI container.
- **`CLAUDE.md`'s sentence that the working tree and the running container *"agree with each other by
  construction"* has the same hole the OFFREPO tag had** — a clean `f5sign-infra` tree proves the file on
  disk is the committed one and proves nothing about the mount the running `php-fpm` was created with.
  §5 D1 and this task's precondition check both read the mount from `docker inspect` for that reason.
  ⛔ Not editable from this task: `CLAUDE.md` is a symlink into the workspace root repo, so a branch edit
  would hit every live session at once. Proposed to the maintainer instead.
- **`composer audit` was not run**, so the dependency delta is zero by construction (no `composer.json` or
  `composer.lock` change) while the absolute state is unmeasured. `eidas-compliance` was skipped with its
  reason: the diff touches no `SignatureExecution/` or `Foundation/Crypto/` source.
- **`perf-smoke-backend`'s dynamic half is not executable in this repo** (`composer perf:seed` does not
  exist) and is declared skipped rather than reported green.

### Debt left, and where it lives now

Everything this task found and did not fix has a durable home, and none of it lives only in
`var/task-runner/TASK-042/`:

| What | Where it lives now |
|---|---|
| The signer's `STEP_NOT_ACTIVE` routing | §7 bullet 1 + the landed handoff; another repository's PR |
| Preprod envelopes possibly corrupted | §7 bullet 2 |
| `renew` reads no envelope context | §7 bullet 3 + ADR-0066 §2.8; the census axis is the tripwire |
| Links minted before deploy | §7 bullet 4 |
| BL-183's outcome half | §7 bullet 5 + the annotated [BL-183](../BACKLOG.md) row |
| `activateFirstStep()`'s no-op `ksort()` | §7, *found while scoping* |
| The delegated 409's three over-claims | §7, *found while scoping* + [BL-249](../BACKLOG.md) for the third |
| Duplicate ADR-0055 / ADR-0057 index rows, one with a broken cell | §7, *found while scoping* |
| The eleven found while implementing and validating | §7, *found while implementing* + [BL-248](../BACKLOG.md)…[BL-258](../BACKLOG.md) |
| The seven found by the three post-landing audits | §7, *found by three audits* + [BL-259](../BACKLOG.md)…[BL-265](../BACKLOG.md) |
| `NotifyActivatedStepRecipientsUseCase`'s ordinal filter | §7, the *Not indexed* sub-bullet closing *found while implementing* — no row, one sentence, no owner. ⚑ It said *"last bullet"* until 2026-09-16, when the post-landing audits added a group after it |
| BL-33 and BL-199 | Closed in [`docs/BACKLOG.md`](../BACKLOG.md), naming this branch and the commits |
