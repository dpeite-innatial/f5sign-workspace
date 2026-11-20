# TASK-071 — A recipient is told when their part ends, and the notice carries their copy

| Field | Value |
|-------|-------|
| **Status** | **Done — integrated in `develop` on 2026-10-26** from `feat/recipient-notices` (implementation tip `46b51ec7`; ADR-0089 accepted in `89deafe3`). Last full run at `d54ed1f2` under the `wt-backend` lane (the worktree's own tree, all tiers, plus lint, arch and PHPStan): 9367 tests, 105253 assertions; its one failure, `ChannelChangeReinvitesCrossingTest`, is the known flake [BL-471](../BACKLOG.md) (invitation order, untouched by this branch, green 3/3 alone), seen a second time. After it, `c10c588b` changes a comment and `663efd2d`/`46b51ec7` add tests only (hermetic tiers green, 7807 tests). Doctrine-guard clean; contract-check and security audit pass with warnings (recorded in §7). Infection on the branch's changed lines (diff against `2cb84eb0`, lane `wt-backend-infection`): covered-MSI 95 %, MSI 91 % (bars 85 / 70); 2 escaped mutants, both equivalent (`Envelope.php` `break`→`continue` after `$final` is false, and `array_values` over a list), and 6 not covered, the thin Messenger handlers, which the Acceptance tier exercises. The infra side (`queue.evidenceaudit.events`, `NOTIFICATION_COPY_BASE_URL`, the prod topology guard) is on `f5sign-infra` master; AC-18 is green on the lane. Two owner decisions differ from this record's text (§7). |
| **Type** | **Forward build** in Notification, with one fact added in Evidence & Audit and one in Envelope. It discharges the delivery half of [BL-280](../BACKLOG.md). |
| **Why** | A recipient whose part ends hears nothing until the whole envelope ends, and then a signer gets `ENVELOPE_COMPLETED` with no link and no document; nobody gets anything at their own act ([BL-280](../BACKLOG.md)). People cannot tell whether more steps remain. The owner's principle (2026-10-22): **a recipient whose part ends receives something complete and final at that moment, without depending on the others**, and is told plainly whether the process has ended for them. |
| **Builds on** | [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) (Notification as a supporting context), [ADR-0038](../adr/ADR-0038-template-archive.md) (pinned, archived copy; the engine only interpolates), [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) (declared channels; `[]` sends none), [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) (history and delivery facts), [ADR-0079](../adr/ADR-0079-a-delivery-retries-by-what-it-carries.md) (retry and send-time profiles), [ADR-0076](../adr/ADR-0076-a-first-write-commits-with-its-consumers-record.md) (a first write commits with its consumer's record), reused unchanged. |
| **Scope** | The notices at a recipient's act, at their documents being final, and at the envelope's end; the link each carries. ⛔ **Not** the receipt, the early seal or the copy link themselves. |
| **Decision record** | **[ADR-0089](../adr/ADR-0089-a-recipient-is-told-when-their-part-ends.md), Accepted 2026-10-26**, drafted with this record (id swept over every ref and worktree on 2026-10-23; ADR-0088 is the highest, on `feat/copy-link`). It **landed in this task's changeset** and was accepted by the owner on 2026-10-26, once §5 was green. It amends [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (the receipt records a fact), [ADR-0087](../adr/ADR-0087-a-document-is-sealed-once-it-is-final.md) (Envelope records whether a recipient's part is final), [ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md) §2.2 (`FINAL` once everything the recipient can see is sealed) and ADR-0073 §2.15 (the copy-ready notice's link), and narrows the reach of ADR-0055 §2.15 (signing links only); amendment notes are written at acceptance. |
| **Sibling** | ⚑ **Prerequisite** on its own branch: TASK-070 (`feat/copy-link`, ADR-0088). On `develop`: [TASK-047](TASK-047-per-signer-evidence-document.md) (ADR-0086), [TASK-069](TASK-069-a-document-is-sealed-once-nobody-can-sign-it.md) (ADR-0087), [TASK-068](TASK-068-after-the-commit-the-signer-is-told-where-their-copy-stands.md) (ADR-0090: what the signer's screen says after the commit; this task moves its `FINAL`, and the notices must not contradict it). |

<!-- OFFREPO: TASK-070 / ADR-0088 live on `feat/copy-link`; what this record relies on is restated here. A read-only
copy link minted through `Session/Contract/Service/CopyLinkIssuer::mintFor($tenantId, $envelopeId, $recipientId)`,
which returns an `IssuedCopyLink` or throws `CopyLinkNotIssuableException` / `CopyLinkTenantMismatchException`; valid
until the conservation ceiling; it opens a recipient's documents and receipt (a decliner's, the receipt only); after
the close only sealed documents are served. Its copy list publishes `signed_copy` from `SignedCopy::of()`, so the
`FINAL` amendment below reaches it. Its mint census (amended 2026-10-23): minted for a blocking member who signed or
declined, an informational member whose step activated or any informational member once the envelope ended agreed,
delegated recipients on the same terms; refused for an unsent envelope, a blocking member pending with no act or
released, an unclaimed slot, a `NOT_BUILT` role, and an informational member whose step never activated while the
envelope is open or after a not-agreed end. The signer app (`f5sign-signer`) renders the copy screen from TASK-070's
handoff. -->

---

## 1. Why this task exists

Owner decisions, 2026-10-22, 2026-10-23 and 2026-10-26:

- **One final notice** when a recipient's part ends and **every document they can see** is sealed (the early seal of
  TASK-069). It says the process has ended for them, carries the link, and nothing follows.
- **Otherwise an act notice** ("your signature is recorded; the process continues; you will receive everything when
  it is complete"), with the link, and **one** more notice: the final notice as soon as every document they can see
  is sealed before the end (2026-10-26), or the end notice. Under `SINGLE_SEAL` the act notice while the envelope is open, and the end
  notice (the last signer, whose commit closes the envelope, gets the end notice only: §7).
- **`FINAL` means the same as the final notice** (2026-10-23, option A): the session read's `signed_copy` reads
  `FINAL` once every document the recipient can see is sealed, early seal included, not only at completion. The
  screen and the notices never disagree about whether the recipient's copy is final.
- **A decliner gets one notice**, whose link opens only their receipt.
- **The end-of-envelope notice carries the link** for those who signed and had no final notice. When the envelope
  ends without agreement, a signer gets **one** ending notice, sent once the documents are sealed, with the link;
  recipients who never signed get the ending notice at the close, as today, with no link.
- **Delegated recipients are treated like everyone else.**
- **Informational members** keep `SEALED_COPY_READY` (who and when unchanged); its link becomes the copy link.
- **Delivered by link**, on the recipient's declared channels, email and SMS.

## 2. What already exists (reuse, do not rebuild)

**Purposes.** `Notification/Domain/ValueObject/NotificationPurpose` has 12 cases: `RECIPIENT_INVITATION`,
`RECIPIENT_INVITATION_RESENT`, `ENVELOPE_COMPLETED`, five `ENVELOPE_ENDED_*` (`SENDER_CANCELLED`,
`SENDER_CANCELLED_WITH_REASON`, `DECLINED`, `TIME_RAN_OUT`, `OUT_OF_REACH`), `SEALED_COPY_READY` and three
`AUTH_OTP_*`. Its predicates are `match`es with no default arm (`carriesMeansToAct()`, `isInvitation()`,
`namesItsOwnChannel()`, `retryProfile()`, `sendTimeCheck()`), and so are `InvitationPurposes::of()`,
`EmailLayoutView::palette()` and `EmailNotificationChannel::htmlTemplate()`. Its docblock states *"no ending notice
carries a link"* and, on `ENVELOPE_COMPLETED`, *"carries no link"*; `EndingNoticeCopyTest` pins the first.
`config/packages/nelmio_api_doc.yaml` publishes the closed `purpose` enum of the history route.

**The template engine only interpolates.** `NativeTemplateEngine` replaces `{{slot}}` and leaves an unset slot
literally; it has no conditional (ADR-0038). One purpose therefore cannot carry a link for some recipients and none
for others.

**The end.** `OnEnvelopeCompleted` dispatches `NotifyCompletedEnvelopeRecipients`.
`NotifyCompletedEnvelopeRecipientsUseCase` sends nothing for an unsent envelope or one with no sealed document; gives
`ENVELOPE_COMPLETED` to a blocking member who signed when the outcome is `AGREED` (no delegated guard), with no link;
gives `SEALED_COPY_READY` to an informational member (all when agreed, those whose step activated when not), skipping
unclaimed slots and delegated recipients, with a link minted from the raw `SigningTokenIssuer` (7 days) as
`{NOTIFICATION_SIGNING_BASE_URL}/<token>`. `OnEnvelopeVoided` (fired at the **close**, before the seal) dispatches
`NotifyEndedEnvelopeRecipients`; `EndingNoticeFamily::of()` maps the cause to a purpose; the audience is every
recipient with an invitation occasion plus delegated recipients whose step activated, the decliner included; no link.
`EnvelopeCompleted` is recorded at `COMPLETED` for both outcomes, after the seal.

**At a recipient's act: nothing.** No Notification subscriber reacts to an act fact.

**The early seal (TASK-069).** `Envelope::requestSealsOfFinalDocuments()` (private, returns `void`) runs at the end of
`recordRecipientCompletion`, `admitDecline`, `admitCommit`, `applyClocks` and `reconcileAfterDataMigration`, after
their releases, and records one `DocumentReadyToSeal` per document of its candidate set that `Envelope::isFinal()`
accepts. The candidates are the documents the completed recipient signs or owns a field on (completion only), plus
every document when the call secured the agreement, which happens in `admitCommit`, `applyClocks` or the reconcile;
nothing remembers a request. ⚠ **One path makes a document final and requests nothing**: `admitDecline` passes no
candidates, and its docblock reasons that no decline secures the agreement. But a last `AT_LEAST n` step without veto
stays open after its n-th commit secures the agreement (`StepCompletionEvaluator::judge`), and a pending member there
may still decline; `DECLINED` does not block an early seal (`RecipientOutcome::blocksAnEarlySeal()`), so a document
the decliner signed beside an already-landed signer becomes final and waits for the envelope seal at the close. `isFinal()` is false under `SINGLE_SEAL`, before the agreement, from `closed_at`, and for a document already
sealed. `DocumentView::$isSealed` says a seal exists, early or at the envelope seal.

**`signed_copy` (TASK-068).** `Session/Application/Query/SignedCopy::of()` is the one home of the value the session read
publishes and the download obeys (ADR-0090 §2.2, §2.3): `FINAL` only when `completedAt` is set, nothing is withheld
and `holdsAnUnsealedDocument()` is false; before that, a recipient whose signature landed reads
`CONTAINS_YOUR_SIGNATURE` even when every document they can see is already sealed early ([BL-466](../BACKLOG.md)).
`isReady()` is true for both values, so the download already serves those bytes. The published description lives in
`config/packages/nelmio_api_doc.yaml` (the session read's `signed_copy`) and
`DownloadSigningDocumentController`'s `#[OA\*]` strings; the signer handoffs
[TASK-068](../frontend-handoff/TASK-068-signer-signed-copy-after-commit.md) and
[TASK-069](../frontend-handoff/TASK-069-integrator-signer-early-document-seal.md) say `FINAL` only at completion.

**Delivery.** `RecipientNotificationChannels::resolve()` asks Envelope's resolver for the declared channels; an empty
resolution (`notification_channels: []`) creates nothing. Templates are pinned at creation (`NotificationTemplates`),
copy lives in `EmailNotificationChannel::TEMPLATES` and `SmsNotificationChannel::TEMPLATES` (en, es; SMS segment
budgets in `SmsCopyTest`). Idempotency per purpose: `NotificationId::fromCause('envelope:<id>|recipient:<id>|purpose:<p>')`
with a `find()` before minting; `DbalNotificationRepository` upserts, so two concurrent creators of one notification
can both pass the `find()`. `forgetSecretsOnceSettled()` drops `link` once every delivery is terminal. History:
`GET /api/v1/envelopes/{id}/recipients/{recipientId}/notifications`.

**Dependencies.** `deptrac.yaml` grants `NotificationApplication` the contracts of Envelope, Session,
SignatureExecution and EvidenceAudit, and no `Vendor` (Notification's application layer does not log).
`EvidenceAudit/Contract` holds only `Type/` today.

**Row locks.** `tests/F5Sign/Support/ProbesRowLocks.php` is the harness that separates a locked read from an unlocked
one; `Integration/` alone runs one connection and cannot.

**Tests to mirror.** `NotifyCompletedEnvelopeRecipientsUseCaseTest`, `NotifyEndedEnvelopeRecipientsUseCaseTest`,
`OnEnvelopeVoidedTest`, `EndingNoticeFamilyTest`, `EndingNoticeCrossingTest`, `EndingNoticeCopyTest`, `SmsCopyTest`,
`EmailNotificationChannelTest`, `NotificationPurposeTest`, `TransmitDeliverySendTimeCheckTest`.

## 3. Scope

1. **The receipt records a fact.** Evidence & Audit records `RECEIPT_ISSUED` (`envelope_id`, `recipient_id`,
   `occurred_at`) inside the receipt's claim (`writeAlongside`'s callable, same connection), on the envelope's stream.
   It is Evidence & Audit's **first event**, and the relay routes by `App.<BC>.Event.<Name>`
   (`EventTypeNaming::routingKeyForClass()`): `config/packages/messenger.yaml` gains `queue.evidenceaudit.events`
   beside the four existing event queues, in `async_events` and in the opt-in `async_events_amqp` test transport, and `f5sign-infra` binds `App.EvidenceAudit.Event.#` to it (a coordinated
   infra change, §6) <!-- OFFREPO: the RabbitMQ bindings live in f5sign-infra's definitions file, which binds event
   queues for Envelope, Session, Signature Execution and Notification only; nothing here depends on reading it -->. Without both, the fact lands in the unroutable queue while the suite stays green on
   `in-memory://` — the failure BL-32 and BL-133 record. The infra change declares the queue with the dead-letter
   argument the other four carry, binds it, and adds it to its DLX check.
2. **Envelope records when a part ends, and whether it is final.** At the end of `recordRecipientCompletion` (in
   both signing modes) and of `admitDecline`, after their releases, Envelope records `RECIPIENT_PART_ENDED`
   (`envelope_id`, `recipient_id`, `act` — `SIGNED`, `APPROVED`, `DECLINED` — `final`, `occurred_at`). `final` is true
   when every document the recipient can see (their `DocumentAssignment::visible`) is already sealed or is accepted by
   `isFinal()` once the call's requests are recorded: requested in this call or in an earlier one and not yet sealed.
   That holds only if every call that makes a document final requests it, so **`admitDecline` requests the seal of the
   documents the decliner signs or owns a field on**, as `recordRecipientCompletion` does for the completed recipient,
   and its docblock is corrected (ADR-0087 §2.1 already says a document is sealed once final; this closes the path
   TASK-069 missed). An envelope already agreed and open when TASK-069 was deployed may hold a final document never
   requested; its recipients' parts read final, they get no act notice, and the end notice reaches them (§3.5). Its seal is on its
   way, so the recipient gets no act notice that a final notice would follow seconds later. The evaluation runs in the
   same method, under the same root lock, as the requests. Under `SINGLE_SEAL`, and for a decline, `final` is false.
   A visible document that nobody signs is sealed only at the close, so it keeps its viewers' parts non-final until
   the end.
3. **A part-notice record per recipient.** Notification keeps one row per (envelope, recipient): the part (act,
   final), whether the receipt exists, whether the envelope has ended, the act-kind notice sent (if any) and the
   end-kind notice sent (if any). Every handler
   creates it if absent (`INSERT … ON CONFLICT DO NOTHING`), reads it `FOR UPDATE`, updates it, and then runs **one
   decision function**, which reads the documents' seal state and the envelope's `closed_at` from Envelope's
   contract at that moment (not every agreed close records a fact; a sender's close-now records `EnvelopeClosedBySender`) and sends at most one notice. Handlers that touch several recipients lock their rows in recipient-id order.
4. **Purposes.**
   - `RECIPIENT_ACT_RECORDED` (the process continues), `RECIPIENT_PART_COMPLETE` (it has ended for you),
     `RECIPIENT_DECLINE_RECORDED`.
   - A link-bearing ending notice per cause, sent to a signer once the documents are sealed:
     `ENVELOPE_ENDED_*_YOUR_COPY` (five, one per existing `ENVELOPE_ENDED_*`). The existing five stay linkless for
     everyone who did not sign.
   - `ENVELOPE_COMPLETED` carries the copy link (everyone it reaches can be minted one).
   Each with the `NOTICE` retry profile, the `DESTINATION_STILL_CURRENT` check, email and SMS copy in en and es.
5. **The decision function**, run by every handler (`RECIPIENT_PART_ENDED`, `RECEIPT_ISSUED`, `DOCUMENT_SEALED`,
   `EnvelopeVoided`, `EnvelopeCompleted`) once the record is updated and locked; nothing is sent until both the part
   and the receipt are known, except by the end:
   - a decline → `RECIPIENT_DECLINE_RECORDED`, once;
   - a signed or approved part under `SEQUENTIAL_PADES` and every visible document sealed → `RECIPIENT_PART_COMPLETE`,
     whether or not the act notice went before (owner, 2026-10-26): a part that was not final at the act becomes
     complete when the last document the recipient can see is sealed early, and the end then sends nothing;
   - not final and the envelope not closed (`closed_at` unset) → `RECIPIENT_ACT_RECORDED`;
   - otherwise → nothing yet.
   The `DOCUMENT_SEALED` handler therefore runs the decision for every recipient who can see that
   document, opening the record of one who has none so that it waits on a part still being written, in
   recipient-id order. `RECIPIENT_ACT_RECORDED` fills the record's act-kind slot;
   `RECIPIENT_PART_COMPLETE`, `RECIPIENT_DECLINE_RECORDED` and every end notice fill its end-kind slot, so a recipient
   gets at most one of each.
   **At the close** (`EnvelopeVoided`) the ending notice goes as today, except to a recipient who signed
   (`RecipientView::hasSigned()`, an admitted commit included) or declined (outcome `DECLINED`), read from Envelope's
   view, not from the record, which may not exist yet. **At the end** (`EnvelopeCompleted`) the reactor dispatches one
   command, which declares `OwnsUnitOfWork` and draws **one boundary per recipient**: it creates each recipient's row
   if absent and marks it ended, even when it sends nothing; a recipient who signed and was sent no
   `RECIPIENT_PART_COMPLETE` gets `ENVELOPE_COMPLETED` (agreed) or the cause's `_YOUR_COPY` ending notice (not agreed),
   with the link; a decliner not yet sent their notice gets `RECIPIENT_DECLINE_RECORDED` (its link shows the receipt
   once issued). On `EnvelopeCompleted` this end rule replaces the decision function: a final recipient whose last document
   the envelope seal sealed (no `DOCUMENT_SEALED` is recorded for it) gets `ENVELOPE_COMPLETED` or the `_YOUR_COPY`
   notice, not `RECIPIENT_PART_COMPLETE`. A failure for one recipient does not stop the others; the command rethrows at the end, and its
   retry finds the others already marked. A fact arriving after a row is ended sends nothing.
6. **Links** are minted through TASK-070's guarded service at the notice's creation, as
   `{NOTIFICATION_COPY_BASE_URL}/<link>`. The variable follows the repo's rule 4 pattern (A): absent from `.env`, a dev
   value in `.env.dev` and `.env.test` beside `NOTIFICATION_SIGNING_BASE_URL`, injected in production by
   `f5sign-infra` <!-- OFFREPO: the workspace's infrastructure repository, which injects production variables as it
   injects NOTIFICATION_SIGNING_BASE_URL; nothing here depends on reading it -->. The owed-link set lies within TASK-070's mint census (the policy also needs a sealed document, and the mint admits a blocking `PENDING` recipient with an admitted decline, to whom the policy owes nothing), so a refusal for a recipient owed a link is an
   invariant breach: that recipient's boundary fails, the others commit, and the command rethrows, is retried, then
   parked.
7. **Copy-ready.** `SEALED_COPY_READY` keeps its timing and its audience under ADR-0073 §2.15, **now including
   delegated informational members** (owner, 2026-10-23; the skip existed because the link was a signing token,
   which ADR-0055 §2.15 keeps from delegated recipients; a copy link is not one), and its link becomes the copy
   link.
8. **`FINAL` once everything the recipient can see is sealed** (owner, 2026-10-23, option A). `SignedCopy::of()`
   returns `FINAL` when the envelope completed, as today, **or** when the recipient's own act has landed (outcome
   `COMPLETED`), nothing is withheld from them and every document they can see carries its seal. It is the
   condition of `RECIPIENT_PART_COMPLETE`, so the screen says `FINAL` from the moment that notice can be sent. The
   rule stays in `SignedCopy::of()` and is still computed from the read context, with no column; the read context
   already carries each document's `isSealed`. Under `SINGLE_SEAL` nothing is sealed before the end, so nothing
   changes there. ADR-0090 §2.2 is amended with it (its `FINAL` row, and §2.5, which already lets `FINAL` through
   `SEAL_PENDING`); [BL-466](../BACKLOG.md) is closed in this changeset. The published `signed_copy` description, the
   download's `#[OA\*]` strings and a handoff to the signer and the integrator say it. TASK-070's copy list publishes
   the same value, so its `signed_copy` prose is swept when TASK-070 is on `develop`.

**Out:** the receipt, the early seal and the copy link; a resend of these notices.

Concepts re-cut: *"recipient self-serve download is NOT IMPLEMENTED"*, *"the signed notice carries no link and mints
no token"*, *"no ending notice carries a link"* (`NotificationPurpose`, `EmailNotificationChannel`,
`NotifyCompletedEnvelopeRecipients`, `NotifyCompletedEnvelopeRecipientsUseCase`, `NotifyEndedEnvelopeRecipientsUseCase`,
`RecipientAuthContext` docblocks; `EndingNoticeCopyTest`); *"issuing records no fact"* (ADR-0086); *"a decline finds nothing to request"* (`Envelope::admitDecline()`'s docblock, ADR-0087);
`SEALED_COPY_READY`'s signing-token link and `NOTIFICATION_SIGNING_BASE_URL` for it; `NotificationPurpose` (gains
eight cases) with every exhaustive `match` over it and the published `purpose` enum in `nelmio_api_doc.yaml`; the
`SigningReadersRefuseUnsentEnvelopeTest` census, which gains the new mint sites; *"`FINAL` only at completion"*
(the `SignedCopy` docblock, ADR-0090 §2.2 and its §3 line on TASK-069 keeping `FINAL` at completion, the `signed_copy` description in
`nelmio_api_doc.yaml`, `DownloadSigningDocumentController`, the TASK-068 and TASK-069 handoffs, BL-466; after TASK-070
lands, `CopyContentsReader`, `CopyDocumentReader` and the copy list's published prose).

## 4. Key decisions

1. **The part ends where Envelope decides it** (author): `final` is evaluated in the same call as the early-seal
   requests, under the root lock, so a part is final only when every visible document is sealed or being sealed at
   that moment. (Amended 2026-10-26: the first cut read only that call's request set, which left a part non-final
   while a document requested by an earlier call was still being sealed; with `FINAL` following the seals, that
   recipient would be told the process continues seconds before their screen said final.)
2. **One record per recipient, locked** (author): the receipt, the seals and the end arrive in any order on
   different workers; the row lock serialises them, and the record says which notice went.
3. **Final means everything the recipient can see is sealed** (owner): an approver, who signs nothing, is not told
   it is over while documents they read can still change.
4. **One ending notice for a signer, after the seal** (owner): it carries the link when the documents exist. A
   recipient who never signed is told at the close, as today.
5. **Delegated recipients like everyone else** (owner); `notification_channels: []` still silences any recipient.
6. **The end is the safety net** (author): whoever acted and was sent nothing gets their notice at the end, from one
   command with a boundary per recipient (a reactor dispatches one command; `OwnsUnitOfWork` lets it draw its own
   boundaries), so a refusal for one recipient does not stop the others.
7. **Closed counts as ended for the act notice** (author): a signature can land after the close, and its receipt must
   not say the process continues.
8. **`FINAL` and the final notice share one condition** (owner, 2026-10-23, option A): rather than keeping `FINAL` at
   completion and wording the notice around it.
9. **A part that becomes complete before the end is told then** (owner, 2026-10-26): a recipient who got the act
   notice gets `RECIPIENT_PART_COMPLETE` when the last document they can see is sealed early, not a notice at the end,
   so they never hold a `FINAL` screen beside a notice that says the process continues for days.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A recipient whose part is final gets one `RECIPIENT_PART_COMPLETE` with a copy link once their receipt exists and every document they can see is sealed, and nothing at the end | owner | Application | send `ENVELOPE_COMPLETED` regardless |
| AC-2 | A recipient whose part is not final gets `RECIPIENT_ACT_RECORDED` at their receipt and one more notice: `RECIPIENT_PART_COMPLETE` when every document they can see is sealed before the end, otherwise the end-of-envelope notice (members AC-2a…c) | owner | Application | see *Notes on AC-2* |
| AC-3 | Under `SINGLE_SEAL` a signer gets the act notice while the envelope is open at their receipt, and the end notice; ⚑ the signer whose commit closes the envelope gets only the end notice (owner decision 3, §7) | owner | Application | mark a `SINGLE_SEAL` part final |
| AC-4 | A decliner gets one `RECIPIENT_DECLINE_RECORDED` whose link opens only their receipt, and no ending notice | owner | Application + Acceptance | keep the decliner in the close's audience |
| AC-5 | At the end, a recipient who signed and had no final notice gets one notice with the copy link: `ENVELOPE_COMPLETED` when agreed, the cause's `_YOUR_COPY` ending notice when not, sent after the seal (members AC-5a…c) | owner | Application | see *Notes on AC-5* |
| AC-6 | `SEALED_COPY_READY` keeps its timing and ADR-0073 §2.15's audience, delegated informational members included, and carries a copy link, not a signing token | owner | Application | mint a signing token |
| AC-7 | Each notice goes on the declared channels, in the recipient's locale, and says whether the process has ended for them (members AC-7a…c) | owner | Unit + Application | see *Notes on AC-7* |
| AC-8 | Delegated recipients get the same notices as any other recipient in their position | owner | Application | skip delegated recipients |
| AC-9 | "Final" means every document the recipient can see is sealed or being sealed: an approver whose visible documents are not all final gets the act notice | owner | Unit + Application | test only the documents they sign |
| AC-10 | `RECEIPT_ISSUED` and `RECIPIENT_PART_ENDED` have closed key sets, are registered for the wire, commit with their writers, and leave the envelope's audit trail checks green (members AC-10a…c) | derived — ADR-0076 | Unit + Integration | see *Notes on AC-10* |
| AC-11 | `RECIPIENT_PART_ENDED.final` is true exactly when every visible document is sealed or accepted by `isFinal()` after the call's requests (members AC-11a…f) | derived — ADR-0034 | Unit | see *Notes on AC-11* |
| AC-12 | Each recipient gets at most one notice of the act kind and at most one of the end kind, whatever the order of the part, the receipt, the seals, the close and the end; every handler takes the record's lock (members AC-12a…g) | derived — tests/F5Sign/Support/ProbesRowLocks.php | Application + Integration (lock probe) | see *Notes on AC-12* |
| AC-13 | Whoever acted and was sent nothing (a receipt or a seal parked) gets the end-of-envelope notice | derived — ADR-0073 | Application | skip a recipient without a sent notice |
| AC-14 | Which notices each recipient gets, over `RoleStanding` × `RecipientOutcome` (and an admitted act), the signing mode, the envelope's outcome and delegation, failing on an unclassified member (members AC-14a…n) | derived — authoring rule 5 | Unit (census) | see *Notes on AC-14* |
| AC-15 | The new purposes appear in the recipient's history and the published `purpose` enum, and their delivery outcomes are recorded as facts | derived — ADR-0078 | Acceptance | leave the enum unchanged |
| AC-16 | The new purposes have the `NOTICE` profile and the `DESTINATION_STILL_CURRENT` check, carry no means to act, and drop their `link` once settled; a refused mint for one recipient at the end lets the others' notices commit and the command rethrow; `NOTIFICATION_COPY_BASE_URL` is absent from `.env` and present in `.env.dev` and `.env.test` (members AC-16a…c) | derived — ADR-0079 | Unit + Application | see *Notes on AC-16* |
| AC-17 | Each new SMS fits its segment budget, each new template is pinned and archived, and every linkless ending notice still carries no link (members AC-17a…c) | derived — ADR-0038 | Unit | interpolate a link into a linkless ending body |
| AC-18 | `RECEIPT_ISSUED` reaches Notification's worker through the broker: an AMQP round trip routes `App.EvidenceAudit.Event.*` to `queue.evidenceaudit.events`; green only with §6 #6's infra change in the lane | derived — config/packages/messenger.yaml | Integration, live broker (`EventLogBrokerRoundTripTest` shape) | drop the queue |
| AC-19 | `signed_copy` reads `FINAL` once the recipient's act has landed and every document they can see is sealed, before completion included, and as today at completion; the download serves the same bytes (members AC-19a…e) | owner | Unit + Acceptance | see *Notes on AC-19* |
| S-1 | The waybill: the carrier gets the act notice and `ENVELOPE_COMPLETED`; consignee A one `RECIPIENT_PART_COMPLETE`; B the same; C none; informational members the copy-ready notice | owner | Acceptance | — |
| S-2 | A `SINGLE_SEAL` signer: the act notice, then `ENVELOPE_COMPLETED` | owner | Acceptance | — |
| S-3 | A decline voids the envelope: the decliner gets their decline notice only; a recipient who had signed gets the `ENVELOPE_ENDED_DECLINED_YOUR_COPY` notice after the seal; a recipient who never signed gets the linkless ending notice at the close | owner | Acceptance | — |
| S-4 | The agreement is secured while members of the last `AT_LEAST` step are still pending: the carrier signs, then the consignees of the documents the carrier can see, while consignee C, on a document the carrier cannot see, keeps the envelope open: the carrier gets the act notice, then `RECIPIENT_PART_COMPLETE` when their last document is sealed, while their session read already says `FINAL`; at the end, nothing more | owner | Acceptance | — |

<!-- OFFREPO: the `wt-backend` lane is a make target of `f5sign-infra`; it runs this tree's own containers. Nothing
here depends on reading that repository. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the per-worktree lane (`wt-backend`) that mounts this tree.

**Notes on AC-2**
- AC-2a — a carrier whose documents still wait for the consignees: the act notice at their receipt. AC-2b — the same
  carrier when the last of their documents is sealed by the envelope seal: `ENVELOPE_COMPLETED` with the link, and no
  `RECIPIENT_PART_COMPLETE`. AC-2c — the same carrier when the last of their documents is sealed early and a later step
  keeps the envelope open: `RECIPIENT_PART_COMPLETE` at that `DOCUMENT_SEALED`, and nothing at the end. Sabotage:
  wait for the end.

**Notes on AC-5**
- AC-5a — agreed: `ENVELOPE_COMPLETED` with a link. AC-5b — voided by the sender after a signer signed: nothing to
  that signer at the close, `ENVELOPE_ENDED_SENDER_CANCELLED_YOUR_COPY` at `EnvelopeCompleted`. AC-5c — the receipt
  arrives after the end: no act notice is sent. Sabotage: send the act notice after the end.

**Notes on AC-7**
- AC-7a — channels as declared; `[]` creates nothing. AC-7b — `es` and `en` copy. AC-7c — the act notice states the
  process continues, the final notice that it has ended for them. Sabotage: one copy for both.

**Notes on AC-10**
- AC-10a — `RECEIPT_ISSUED` closed key set, committed inside the receipt's claim (a lost claim records no fact).
- AC-10b — `RECIPIENT_PART_ENDED` closed key set, recorded by `recordRecipientCompletion` and `admitDecline`.
- AC-10c — the envelope's audit trail, issued over a stream holding both facts, passes its checks. Sabotage: record
  the receipt fact after the claim's commit.

**Notes on AC-11**
- AC-11a — a part whose visible documents were all requested in the same call: `final`. AC-11b — one visible document
  with a signer still pending: not final. AC-11c — a visible document nobody signs: not final. AC-11d — `SINGLE_SEAL`:
  not final. AC-11e — a visible document requested in an earlier call and not yet sealed: final. AC-11f — a pending
  member of an open, secured `AT_LEAST` step declines, and a document they signed beside a landed signer becomes final:
  `admitDecline` requests its seal. Sabotage: evaluate `final` from this call's request set alone (AC-11e goes red);
  pass no candidates from `admitDecline` (AC-11f goes red).

**Notes on AC-12**
- AC-12a — part, receipt, then last seal: final at the seal. AC-12b — last seal, then part, then receipt: final at the
  receipt. AC-12c — receipt, then seal, then part: final at the part. AC-12d — receipt after the close (agreed or not,
  read from `closed_at`), part not final: no act notice. AC-12e — anything after `EnvelopeCompleted`'s notice: nothing more. AC-12f — the same fact
  delivered twice: one notice. AC-12g — every handler's read holds the row lock (`ProbesRowLocks`, NOWAIT from a second
  session). Sabotage: read the record without `FOR UPDATE`.

**Notes on AC-14**
- AC-14a blocking signer, part final: final notice only. AC-14b blocking signer, part not final: act, then the final
  notice if every visible document is sealed before the end, else the end notice.
  AC-14c blocking approver: as AC-14a/b by visible documents. AC-14d blocking, declined (voiding or not): decline
  notice only. AC-14e blocking, admitted commit not yet landed when the envelope closes: no linkless close notice and no act
  notice; at the end `ENVELOPE_COMPLETED` (agreed) or the `_YOUR_COPY` notice (not agreed).
  AC-14f blocking, released: the linkless ending notice at the close when not agreed; nothing when agreed.
  AC-14g blocking, pending and never acted, at a not-agreed close: the linkless ending notice; at an agreed end:
  nothing. AC-14h informational whose step activated: copy-ready. AC-14i informational whose step never activated:
  copy-ready when agreed, nothing when not. AC-14j `SINGLE_SEAL` signer: act + end; the signer whose commit closes the envelope: end only (owner decision 3, §7). AC-14k delegated: as the same
  position undelegated. AC-14l unclaimed slot: none. AC-14m `NOT_BUILT` role: none. AC-14n `DELEGATED` / `SKIPPED`
  outcomes (never written): none. Sabotage: notify a released blocking member at an agreed end.

**Notes on AC-16**
- AC-16a profiles and checks per new purpose. AC-16b (Integration, real unit of work) a refused mint for one recipient:
  the others' notices are committed and the command rethrows. AC-16c the variable's presence per `.env` file.
  Sabotage: one boundary around every recipient.

**Notes on AC-17**
- AC-17a SMS budgets per locale. AC-17b templates pinned and reproducible. AC-17c `EndingNoticeCopyTest` still holds
  for the five linkless ending purposes.

**Notes on AC-19**
- AC-19a — `SEQUENTIAL_PADES`, the signer's act landed, every visible document sealed early, envelope open: `FINAL`.
  AC-19b — one visible document still unsealed: `CONTAINS_YOUR_SIGNATURE`. AC-19c — an approver whose act landed and
  whose visible documents are all sealed: `FINAL`. AC-19d — admitted, not yet landed (`APPLYING`), even with every
  visible document sealed: not `FINAL`. AC-19e — closed, every visible document sealed early: `FINAL`, not
  `SEAL_PENDING`. Sabotage: keep `completedAt` as the only way to `FINAL` (AC-19a and AC-19c go red).

## 6. Open follow-ups (track, don't solve here)

1. **The copy screen in the signer app** is TASK-070's handoff; these notices link to it. <!-- OFFREPO: the signer
   app is `f5sign-signer`, another repository of the workspace; nothing here depends on reading it. -->
2. **A resend** of an act or final notice is not built; the integrator can mint a copy link (TASK-070).
3. **BL-280** is discharged by this task together with TASK-047; its row is closed in this changeset when it lands.
4. **TASK-070's census.** Amended on `feat/copy-link` on 2026-10-23 (delegated minted; informational dormant members
   minted once agreed); this task's owed-link set relies on it.
5. **Production variable.** <!-- OFFREPO: `f5sign-infra`, the workspace's infrastructure repository; restated fact:
   it injects production variables from its environment template. --> `f5sign-infra` injects `NOTIFICATION_COPY_BASE_URL` in production, as it injects
   `NOTIFICATION_SIGNING_BASE_URL`: a coordinated infra change.
6. **Broker binding.** <!-- OFFREPO: `f5sign-infra` declares the RabbitMQ bindings in its definitions file; today it
   binds event queues for Envelope, Session, Signature Execution and Notification only. --> `f5sign-infra` binds
   `App.EvidenceAudit.Event.#` to `queue.evidenceaudit.events`, in the same coordinated change as #5.
7. **Owner decision 2 has no end-to-end pin.** Only `RecipientPartNoticesTest::a_close_that_landed_while_waiting_withholds_part_complete` and `PartNoticePolicyTest` hold it. → [BL-478](../BACKLOG.md).
8. **The end reads the envelope context once per recipient** (about N² rows per end). → [BL-477](../BACKLOG.md).
9. **`notification.requested_at` has second precision**, so the history can order two notices of one second either way. → [BL-479](../BACKLOG.md).
10. **Session events have no broker round trip in the test transport.** → [BL-480](../BACKLOG.md).
11. **Security warnings W1–W3** of the audit. → [BL-481](../BACKLOG.md), [BL-482](../BACKLOG.md), [BL-483](../BACKLOG.md).
12. **A second sighting of [BL-471](../BACKLOG.md)** in this task's full run, added to its row.
13. **Infra help strings.** <!-- OFFREPO: `f5sign-infra`, the workspace's infrastructure repository; restated fact: three of its help strings name a number of event queues. --> `rabbit-check-dlx`, `rabbit-recreate-event-queues` and `rabbit-check-dlx-prod` still say "4 event queues"; production must import the new queue before this backend rolls out. Belongs to the same coordinated change as #5 and #6.
14. **[BL-467](../BACKLOG.md) is narrowed, not closed:** a decline now requests the seal of what it made final (slice 1); a release and the data migration still request none.
15. **[BL-280](../BACKLOG.md)** is Closed: this task delivered it, integrated in `develop` on 2026-10-26.

## 7. Deviations & honest notes

Written at close, 2026-10-26, on `feat/recipient-notices` at `c10c588b`. Slice reports, reviews and the plan are in the gitignored `var/task-runner/TASK-071/`; what matters from them is here.

### Scope
- Files outside the slices' stated Touch lists, all accepted by review: `Factor5TrailSources` (slice 06, with a registry census); two exception classes (slice 10); `EndingNoticeCrossingTest`, `OneResolutionTest` and `EnablingSmsChangesNothingForAnEmailRecipientTest` (slice 12); the docblock of `SelfSerializingMessageSerializer` (slice 20, docblock only, true to the infra queue list; no contract change, so no ADR). The `OwnsUnitOfWork` and `UnitOfWork` docblocks gain the third shape ADR-0089 §2.3 decides.
- Slice 21 was added after the first full run found a trail template that did not label the two new facts; slices 22 and 23 came from the closing review (see *Decisions*).

### Decisions made during implementation
- ⚑ **Owner decision 2 (2026-10-26), a deviation from this record's text:** `RECIPIENT_PART_COMPLETE` is sent only while the envelope is open (`closed_at` unset). The decision cannot tell an early seal from the envelope seal, which runs after the close; without the condition a `RECEIPT_ISSUED` handled after the envelope seal of a not-agreed envelope would say "the process has ended for you" instead of sending the `_YOUR_COPY` notice. From the close, the end notice speaks. §3.5 and key decision 9 describe the early notice without this condition.
- ⚑ **Owner decision 3 (2026-10-26), a deviation from AC-3, AC-14j and §1:** the last signer of a `SINGLE_SEAL` envelope gets only `ENVELOPE_COMPLETED`. Their commit closes the envelope at admission, so their receipt arrives after the close, and §3.5 and AC-12d say a closed envelope sends no act notice. AC-3's and AC-14j's "always" is read as "the act notice whenever the envelope is open at the receipt, never the final notice under `SINGLE_SEAL` before completion". S-2's fixture has two signers: the first gets act and completed, the second completed only. Those lines are annotated in place.
- An empty visible set counts as everything sealed in all three places (`Envelope`'s `final`, `PartNoticePolicy`, `SignedCopy`), and `SignedCopy`'s new branch names `SEQUENTIAL_PADES`, so `SINGLE_SEAL` never reads `FINAL` before completion.
- A slot is filled when the notice is decided, even when `notification_channels: []` creates no occasion: "at most one" counts decisions, and `[]` silences the end too.
- The end no longer returns early without a sealed document for the non-sealed-copy purposes, so a decliner whose receipt was parked still gets `RECIPIENT_DECLINE_RECORDED`. A not-agreed end with no cause throws `EndCauseMissingException` inside that recipient's boundary.
- The close decides the spared recipients under their lock and opens their records (the literal reading of §3.3 and §3.5).
- Copy links are minted through Session's `CopyLinkIssuer` directly, as `SigningTokenIssuer` is used; no Notification-owned port. The early notices were authored without the link and slice 14 added it, because the engine refuses an unset `{{link}}` and the issuer is not on `develop` before the TASK-070 merge.
- The `SEALED_COPY_READY` minting site moved into `RecipientNotices` (slice 13) and switched from a signing token to a copy link (slice 15). The delegated-refusal property was retired by ADR-0089 §2.5 and its test removed.
- `queue.evidenceaudit.events` entered `messenger.yaml` last (slice 20), so earlier slices stay independent of the infra change.
- Spared-recipient census (orchestrator ruling in slice 7): blocking standing and (signed or declined); unreachable cells are labelled as such. The census looks its table up by value.
- **Closing review, race repaired in slice 22 and realizing ADR-0089 §2.3 as written (no new ADR):** `RecipientPartNotices::advance()` and `end()` take identities, lock, then read the envelope once and decide on that read; the seal handler walks the view's viewers and opens a record for each, so it waits on a part still being written. A close that lands while a handler waits withholds `RECIPIENT_PART_COMPLETE`. The empty records this creates are harmless: every reader is `RecipientPartNotices::lock()` and every handler opens before reading.
- Window left open on purpose: a close committing between a part handler's post-lock read and its commit can still be followed by that act notice; the close then re-decides under the same lock. That is the most a handler can guarantee without sharing the close's transaction.
- A published-spec note: `RECIPIENT_PART_COMPLETE` has the subject `Ha terminado su participación en «…»`; the handoff is written in Spanish like its siblings.

### Decisions that needed an ADR
- None new. [ADR-0089](../adr/ADR-0089-a-recipient-is-told-when-their-part-ends.md) was drafted with this record and accepted by the owner on 2026-10-26, in its own commit after the close. Texts that other records still carry from before this task (ADR-0086 and ADR-0072 "issuing records no fact", ADR-0087 §2.1 "a decline requests no seal", ADR-0090 §2.2 keyed to completion, ADR-0089 §2.6 "equals" for the owed-link set) were amended by docs-sync (`374c41aa`) and at acceptance.

### Declared and unproven properties
- A real commit landing mid-wait on a row lock is READ COMMITTED semantics; the Application test swaps the view at the locked read, which proves placement and input, not the commit. The probe that can see the lock is the Integration two-process test (`SealWaitsOnAConcurrentPartTest`, with `PartNoticeRaceActs`).
- Redelivery is proven sequentially only: `async_events` is `in-memory://` in test, so nothing redelivers by itself. Concurrent redelivery is the row-lock property.
- A deadlock is not exercised; the mechanism is lock order (recipient id, `strcmp`), proven by the order the fake records.
- AC-18 (the broker routes `App.EvidenceAudit.Event.*`) is green only with the infra binding in the lane. The config test checks containment, not equality, because production's `async_events` also reads `queue.session.events`.
- Owner decision 2 has no end-to-end pin: on S-4's waybill the agreement is secured once A signs, so `POST /void` is refused. It is reachable on an unsecured void (a step-1 signer sees only their document and signs, step 2 pending, the sender voids, the held `DocumentReadyToSeal` is released) or on S-3 with the signer's seal held across the decline.
- `SingleSeal` arm of `recordPartEnded` repeats `isFinal()`'s mode check and has no sabotage of its own; AC-11d pins the behaviour.
- `IssuedReceipt::issue()` has no unit test of its own, only `DbalIssuedReceiptRepositoryTest` at Integration. If Infection's diff run escapes a mutant there, add `tests/F5Sign/EvidenceAudit/Unit/Domain/Aggregate/IssuedReceiptTest.php`.
- `RecipientPartNoticeMissingException`'s throw is unreachable in production (insert-if-absent and `FOR UPDATE` in one transaction) and untested by choice.
- Harness: every run above names the `wt-backend` lane on this worktree's tree, never the main checkout's stack.

### Debt left behind, and where it lives now
- Owner decision 2 without an e2e pin → §6 #7, [BL-478](../BACKLOG.md).
- About N² context reads at the end → §6 #8, [BL-477](../BACKLOG.md).
- `notification.requested_at` second precision (history order of two notices in one second) → §6 #9, [BL-479](../BACKLOG.md).
- Session events have no broker round trip in the test transport → §6 #10, [BL-480](../BACKLOG.md).
- Security audit W1 (the plaintext copy link sits in notification variables for ten purposes until the deliveries settle, the pattern of the invitation's signing link; ADR-0033 is `Proposed`) → [BL-481](../BACKLOG.md). W2 (`LogNotificationChannel` dumps variables including copy links; confirm LOG is never selected in production) → [BL-482](../BACKLOG.md). W3 (`NOTIFICATION_COPY_BASE_URL` is not scheme-validated) → [BL-483](../BACKLOG.md). W4 (a comment ambiguity) was fixed in `c10c588b`.
- Second sighting of the `ChannelChangeReinvitesCrossingTest` flake, at `d54ed1f2` → added to [BL-471](../BACKLOG.md).
- Infra: queue binding, `NOTIFICATION_COPY_BASE_URL` and three help strings → §6 #5, #6, #13.
- Contract-check warnings, both for the handoff (docs-sync owns it): W1 its "Naturaleza" row says no new enum value while the history `purpose` enum gains eight; W2 it does not mention the `notification_channels: []` consequences. Docs the sweep left to docs-sync: `docs/ddd/notification-domain-model.md`, `docs/ddd/envelope-domain-model.md`, `docs/ddd/signing-session-domain-model.md`, the TASK-050 and TASK-058 handoffs.
- Contract-check and perf notes carried by the rows above; BL-467 narrowed (§6 #14); BL-280 closed (§6 #15). BL-466 was already closed by `SignedCopy::of()`.

### Delegated work
- 23 slices: 18 critical on `opus`, 5 standard on `sonnet`. Review rounds: 15 slices needed one round and 8 none, 15 rounds in all. 17 slices ended `DONE_WITH_CONCERNS`, 5 `DONE`, and slice 21 was approved by the orchestrator's diff check (two label lines).
- Waves: 11. Slice 21 (a fix from the first full run) and slices 22 and 23 (the closing review) were added after the plan's 20.
- Replication delegated to the `replicator`: none. Every slice report's `## Delegated` says none or "below the threshold" (the one close call was a copy-entry script run locally, with every hunk read).
- Full-run history: the first full run at `1e262930` was red once (a trail template missing the two new labels, fixed in slice 21); the run at `d54ed1f2` was green except the BL-471 flake.

### Cost of the run
- 24 slices: 18 critical on opus (implementer and reviewer), 6 standard on sonnet (opus review for the three that wrote published strings); 16 fix rounds in all, none past round 1, no escalation. Wall-clock from preparation to the last gate: about 5.9 h, including about 30 min waiting for TASK-070 to reach `develop` and two closing slices (22: the post-lock read race; 24: Infection's escaped mutants) that the plan did not have.
- Infection, first run on `c10c588b`: covered-MSI 90 %, MSI 78 %, with 24 escaped and 46 uncovered mutants on changed lines; slice 24 (tests only) brought it to 95 % / 91 %, 2 escaped (equivalent) and 6 uncovered (thin handlers).
