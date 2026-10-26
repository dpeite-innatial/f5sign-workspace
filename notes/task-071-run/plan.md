# Plan — TASK-071

Record: `docs/tasks/TASK-071-a-recipient-is-told-when-their-part-ends.md` (tree `6b91230a`). Decision record: ADR-0089
(`Proposed`, not redrafted). No further ADR is needed: every cross-BC read used here is already granted in
`deptrac.yaml` (NotificationApplication/Infrastructure → Envelope, Session, SignatureExecution, EvidenceAudit contracts),
no Kernel/Foundation contract changes (only two Foundation docblocks gain the third `OwnsUnitOfWork` shape that ADR-0089
§2.3 decides), and no ruleset file is edited.

## Criteria → slices
| Criterion | Slices | Harness |
|---|---|---|
| AC-1 | 07, 10, 13, 14 (link), 18, 19 | Application (fakes) + Acceptance |
| AC-2 (a, b, c) | 07, 10 (a), 11 (c), 13 (b), 14 (link), 18, 19, 22 (c, race) | Application + Acceptance |
| AC-3 | 07, 13, 18 | Unit + Application + Acceptance |
| AC-4 | 07, 12, 13, 14 (link), 19 | Application + Acceptance |
| AC-5 (a, b, c) | 07, 12 (b close), 13, 14 (link), 18, 19, 22 (decision 2 on the post-lock view), 23 (S-3 citation) | Application + Acceptance |
| AC-6 | 15, 18 | Application + Acceptance |
| AC-7 (a, b, c) | 03, 05 (b, c), 10 (a), 14 (c with link), 23 (b citation) | Unit + Application |
| AC-8 | 07, 10, 13 | Unit census + Application |
| AC-9 | 01, 07, 10 | Unit + Application |
| AC-10 (a, b, c) | 02 (a), 01 (b), 06 (c) | Unit + Integration (+ Application assemblers) |
| AC-11 (a…f) | 01 | Unit |
| AC-12 (a…g) | 04 (f, g repo), 07 (a–e), 10 (a, b, d, f, g), 11 (a, c), 12 (g), 13 (e), 18 (d), 22 (a, c, d "whatever the order": post-lock view + seal waits) | Unit + Application + Integration lock probe |
| AC-13 | 13 | Application |
| AC-14 (a…n) | 07 (census), 12 (close half), 13 (end half), 15 (k, h, i after the delegated skip goes) | Unit census + Application |
| AC-15 | 03, 05 (enum), 09 (history + outcome fact) | Acceptance + Application |
| AC-16 (a, b, c) | 03, 05 (a), 14 (a link drop, c), 16 (b) | Unit + Application + Integration (real UoW) |
| AC-17 (a, b, c) | 03, 05 (a, b, c), 14 (a, c with link) | Unit |
| AC-18 | 20 | Integration, live broker — expected red until infra lands |
| AC-19 (a…e) | 08, 17 (copy list), 19 (a with the notice) | Unit + Application + Acceptance |
| S-1 | 18 | Acceptance (lane, live DSS, relay pumped) |
| S-2 | 18 | Acceptance |
| S-3 | 12 (close half), 19, 23 (assertions) | Acceptance |
| S-4 | 19, 23 (assertions) | Acceptance |

## Harness per property
| Property | Tier | Does the harness reach it? |
|---|---|---|
| `final` evaluated under the root lock with the call's requests | Unit (aggregate) | Yes: one method call, the pending events order is observable |
| A lost/rolled-back receipt claim records no fact | Integration (real connection, `writeAlongside`) | Yes; Application fakes cannot see a rollback |
| Two handlers cannot both send (row lock) | Integration `ProbesRowLocks` NOWAIT on the repository + Application spy that every handler reads through `findLockedForUpdate` | The probe sees the lock (DAMA alone cannot); the spy sees which read each handler used. Together they reach it |
| Recipients locked in id order (no deadlock) | Application (fake records read order) | Order yes; an actual deadlock no — accepted, order is the mechanism |
| One boundary per recipient at the end | Application (`ScriptedUnitOfWork`) + Integration real UoW (slice 16) | Application sees calls only; slice 16 reads committed rows from a second connection |
| A redelivered fact sends once | Application (two executions) | Yes for sequential redelivery; concurrent redelivery is the lock property above. `async_events` is `in-memory://`, nothing redelivers by itself |
| A refused copy link is never a silent skip | Application (scripted fake issuer) + Integration (16) | Yes |
| The broker routes `App.EvidenceAudit.Event.*` | Integration live AMQP (slice 20) | Only with infra's binding in the lane; otherwise red by construction |
| Copy says continue vs ended; SMS one segment | Unit over the catalogs | Yes |
| `FINAL` before completion and the bytes served | Unit `SignedCopy` + Acceptance download | Yes |
| The decision reads the view after the row lock (seal / close landing while waiting) | Application: `FakeRecipientPartNoticeRepository::$onLockedRead` swaps the fake query's view at the locked read; log `['lock','read']` | Yes for placement and for the decision's input; a real commit landing mid-wait is READ COMMITTED semantics, not re-proven |
| The seal handler waits on an uncommitted part/receipt insert of a recipient it sees | Integration, two OS processes (`part_notice_race_child.php`, `EnvelopeRootLockRaceTest` shape) | Yes: the child holds the insert; DAMA or one connection could not (a plain read cannot see it, and a lock never conflicts with itself) |
| Infection | `src/F5Sign` only | Sees the new code once it has callers; slices 10–13 give the policy and services callers in the same wave they land |

## Slices
⛔ **Gate before wave 6: the orchestrator merges `develop` (carrying TASK-070, `feat/copy-link`) into
`feat/recipient-notices`, re-runs the fast tier, and only then launches slices 14–19.** Slice 20 runs last and is
expected red until `f5sign-infra`'s `feat/evidenceaudit-events-and-copy-links` is in infra's main checkout.

| # | Title | Tier | Covers | Depends on | Wave |
|---|---|---|---|---|---|
| 01 | Envelope records RECIPIENT_PART_ENDED; a decline requests the seal of what it made final | critical | AC-10b, AC-11a–f, AC-9 | — | 1 |
| 02 | Issuing a receipt records RECEIPT_ISSUED inside its claim | critical | AC-10a | — | 1 |
| 03 | Three recipient notices exist as purposes, with copy (no link yet) | critical | AC-7b,c, AC-16a, AC-17a,b, AC-15 | — | 1 |
| 04 | One locked part-notice record per recipient | critical | AC-12f,g | — | 1 |
| 05 | Five `_YOUR_COPY` ending notices (no link yet) | critical | AC-17c, AC-7b, AC-16a, AC-17a,b, AC-15 | 03 | 2 |
| 06 | Trail and receipt over a stream holding both new facts | standard | AC-10c | 01, 02 | 2 |
| 07 | `PartNoticePolicy` + census | critical | AC-14, AC-3, AC-9, AC-8, AC-12a–e | 04, 05 | 3 |
| 08 | `signed_copy` FINAL once everything visible is sealed | critical | AC-19a–e | — (nelmio overlap with 03, 05) | 3 |
| 09 | New purposes in the history, with outcome facts | standard | AC-15 | 03, 05 | 3 |
| 10 | Part and receipt reach Notification; `RecipientNotices`, `RecipientPartNotices` | critical | AC-1, AC-2a, AC-7a, AC-8, AC-9, AC-12a,b,d,f,g | 01, 02, 07 | 4 |
| 11 | An early seal re-decides for its viewers | critical | AC-2c, AC-12a,c | 10 | 5 |
| 12 | The close spares who signed or declined | critical | AC-4, AC-5b, AC-14d–g, S-3 | 10 | 5 |
| 13 | The end: one command, a boundary per recipient | critical | AC-1, AC-2b, AC-3, AC-5a–c, AC-12e, AC-13, AC-14, AC-8 | 10 | 5 |
| 14 | ⛔ after develop integration (TASK-070) — the copy link on the new notices and ENVELOPE_COMPLETED | critical | AC-1/2/4/5 link, AC-16a,c, AC-17a,c, AC-7c | 12, 13, gate | 6 |
| 15 | ⛔ after develop integration (TASK-070) — SEALED_COPY_READY on the copy link, delegated included | critical | AC-6, AC-14h,i,k | 14 | 7 |
| 16 | ⛔ after develop integration (TASK-070) — a refused mint fails one boundary (real UoW) | critical | AC-16b | 14 | 7 |
| 17 | ⛔ after develop integration (TASK-070) — the copy list's prose on FINAL | standard (OA: opus review) | AC-19 | 08, gate | 6 |
| 18 | ⛔ after develop integration (TASK-070) — waybill and SINGLE_SEAL end to end | critical | S-1, S-2, AC-1, AC-2, AC-3, AC-5a, AC-6 | 15 | 8 |
| 19 | ⛔ after develop integration (TASK-070) — decline and secured-early end to end; decliner's link | critical | S-3, S-4, AC-4, AC-2c, AC-5b, AC-19a | 15 | 8 |
| 20 | RECEIPT_ISSUED through the broker (expected red until infra) | critical | AC-18 | 02 (last on purpose) | 9 |
| 21 | Trail labels for the two new facts (fix from the 2c full run) | standard | AC-10c | 01, 02, 06 | 9 |
| 22 | Closing: every part-notice decision reads the envelope after its row lock; the seal handler waits on a part still being written; decision-2 e2e if reachable | critical | AC-12a,c,d, AC-2c, AC-5 (decision 2), key decisions 7, 9 | 11, 12, 13 | 10 |
| 23 | Closing: AC-7b cited, F2 published copy-link list, F3/F4 prose, slice-19 e2e assertion items (a)–(c) | standard (OA: opus review) | AC-7b, S-3, S-4 | 22 (shared `RecipientNoticesSecuredEarlyHttpTest`) | 11 |

Shared-file notes for the orchestrator: `config/packages/nelmio_api_doc.yaml` (03 → 05 → 08), `NotificationPurpose.php`
(03 → 05 → 12 → 14 → 15), `ReactorConvergenceTest` (10 → 11), `RecipientNotices.php` (10 → 13 → 14 → 15),
`config/services.yaml` (04 → 13 → 14 → 15), `SigningReadersRefuseUnsentEnvelopeTest` (13 → 14 → 15).

## Sweep terms
Seeded from the record's `Concepts re-cut` line:
- "recipient self-serve download is NOT IMPLEMENTED" (`RecipientAuthContext`, `EmailNotificationChannel`, `NotifyCompletedEnvelopeRecipients*`) — false from slice 14
- "the signed notice carries no link and mints no token" — false from slice 14
- "no ending notice carries a link" → "no linkless ending notice does" (`NotificationPurpose`, `EmailNotificationChannel`, `EndingNoticeCopyTest`) — slices 05, 14
- "issuing records no fact" (ADR-0086; code docblocks in `EvidenceAudit`) — slice 02
- "a decline finds nothing to request" (`Envelope::admitDecline()`, `requestSealsOfFinalDocuments`, ADR-0087) — slice 01
- `SEALED_COPY_READY`'s signing-token link; `NOTIFICATION_SIGNING_BASE_URL` / `SigningTokenIssuer` for it; "A delegated party is sent no credential" on the copy-ready rule — slices 13, 15
- `NotificationPurpose` gains eight cases: every exhaustive `match`, `InvitationPurposes::of()`, `EmailLayoutView::palette()`, `EmailNotificationChannel::htmlTemplate()`, the nelmio `purpose` enum, hand lists (`TransmitDeliverySendTimeCheckTest::notices()`) — slices 03, 05
- `SigningReadersRefuseUnsentEnvelopeTest` census: the minting site moves to `RecipientNotices`, then mints copy links — slices 13, 14, 15
- "`FINAL` only at completion" (`SignedCopy`, ADR-0090 §2.2 and its §3 TASK-069 line, nelmio `signed_copy`, `DownloadSigningDocumentController`, TASK-068 and TASK-069 handoffs, BL-466; after TASK-070: `CopyContentsReader`, `CopyDocumentReader`, `GetCopyController`) — slices 08, 17
- "the decliner, who is in the audience" / "the decliner included" (`ENVELOPE_ENDED_DECLINED` docblock, record §2 wording) — slice 12
- Symbols whose behaviour changes: `NotifyCompletedEnvelopeRecipients` (now `OwnsUnitOfWork`), `NotifyEndedEnvelopeRecipientsUseCase` (audience narrowed), `IssuedReceipt::issue()` / `issueIfAbsent()` (now record a fact), `OwnsUnitOfWork` / `UnitOfWork` docblocks ("two shapes" → three)
- Losing alternatives to grep for in prose: "notify on the commit", "decide final in Notification from a state query", a template conditional, a Notification-owned copy-link port (rejected in favour of using `CopyLinkIssuer` directly, as `SigningTokenIssuer` is used)
- ADR texts (0086, 0087, 0090, 0073, 0055) are amended at acceptance (task-close), not in slices.
- Slice 22: `recipientsWithRecordsOn` (removed); "a recipient without a record is skipped", "every recipient with a record / with a row who can see" (the seal handler now opens a record for every viewer); `advance(EnvelopeContextView $e, RecipientView $p, …)` / `end($e, $p, …)` (now identity + issuer; the view is read after the lock); any "decides on the view it is handed" prose; `PartNoticeRecipientMissingException` thrown by the seal use case (now by `RecipientPartNotices`). Docs-sync: ADR-0089 §2.3 and record §3.5 say "every recipient with a row who can see" — still literally true, but the handler now opens the row; reword there, not in a slice.
- Slice 23: "the three RECIPIENT_* members", "no CTA yet", "the notices that will carry the link".

## Decisions made
1. **Early notices carry no link; slice 14 adds it.** The engine refuses an unset `{{link}}` at transmit, and `CopyLinkIssuer` does not exist before the develop merge. Slices 03/05 author the final wording minus the link line/CTA; slice 14 adds the link line, CTA and SMS link (copy additions only) and the mint inside `RecipientNotices::send()`. No early slice is rewritten beyond those additions.
2. **`RECIPIENT_PART_COMPLETE` requires `closed_at` unset** (slice 07). Owner approved 2026-10-26. The decision cannot tell an early seal from the envelope seal, which runs only after the close; without the condition a `RECEIPT_ISSUED` processed after the envelope seal of a NOT_AGREED envelope would send "the process has ended for you" instead of the `_YOUR_COPY` notice, and §3.5 wants `ENVELOPE_COMPLETED`, not `PART_COMPLETE`, for a part whose last document the envelope seal sealed. From the close, the end speaks.
3. **The last signer of a `SINGLE_SEAL` envelope gets no act notice.** Their commit closes the envelope at admission, so their receipt arrives after the close, and §3.5 / key decision 7 / AC-12d say a closed envelope sends no act notice. AC-3's "always" is read as "never the final notice under SINGLE_SEAL; the act notice whenever the envelope is open at the receipt". S-2's fixture has two signers; the first is asserted act + completed, the second completed only. Owner confirmed 2026-10-26.
4. **An empty visible set counts as everything sealed / final** in all three places (Envelope `final`, `PartNoticePolicy::seesEverythingSealed`, `SignedCopy`), and `SignedCopy`'s new branch is explicit about `SEQUENTIAL_PADES`, so `SINGLE_SEAL` never reads FINAL before completion.
5. **A slot is filled when the notice is decided**, even if `notification_channels: []` creates no occasion: "at most one" counts decisions, and `[]` silences the end too.
6. **The end no longer returns early without a sealed document**; that guard applies to the sealed-copy purposes only, so a decliner whose receipt was parked still gets `RECIPIENT_DECLINE_RECORDED`. An unsent envelope still returns early.
7. **A not-agreed end with no `endCause` throws** (`EndCauseMissingException`) inside that recipient's boundary: a signer must not be left without word silently.
8. **The close decides the spared recipients under their lock** (slice 12), creating their rows, the literal reading of §3.3/§3.5's handler list.
9. **Copy links are minted through Session's `CopyLinkIssuer` directly**, as `SigningTokenIssuer` is today; no Notification-owned port. Dev/test value `NOTIFICATION_COPY_BASE_URL=http://localhost:3001/c`.
10. **The minting site for `SEALED_COPY_READY` moves into `RecipientNotices` in slice 13** (still a signing token, after `find()` and the channel resolution), and switches to the copy link in slice 15.
11. **`queue.evidenceaudit.events` enters `messenger.yaml` in slice 20, last**: with `auto_setup: false` a consumer of `async_events` fails on a queue the broker does not declare, so earlier slices stay independent of the infra change. The branch must not land on `develop` before infra's change does.
12. Names: `RecipientPartAct` (Envelope contract), `RecipientPartEnded`, `ReceiptIssued` (subject `IssuedReceiptId`, stream = envelope; a `DomainEvent`, not `AuditableEvent`), `PartAct`/`PartNoticeSlot`/`PartNotice` (Notification domain), `RecipientPartNotice` + `notification.recipient_part_notice`, `PartNoticePolicy`, `RecipientNotices`, `RecipientPartNotices`, `EndNoticesIncompleteException`.
13. The `DOCUMENT_SEALED` handler runs in one transaction (default boundary), locking in recipient-id order; only the end draws per-recipient boundaries (the record requires them only there).
14. The new handoff (`docs/frontend-handoff/TASK-071-signer-integrator-signed-copy-final.md`) is written in Spanish, like its siblings.
15. **The race repair realizes ADR-0089 §2.3 as written; no new ADR** (closing review Low-confidence item 1, promoted by the orchestrator). (b) `RecipientPartNotices::advance()`/`end()` take `(TenantId, EnvelopeId, RecipientId, …, SystemActorId $issuedBy, $at)`, lock, then read the envelope once through `EnvelopeQueryInterface` and decide on that read; the stale view is not passed at all, so no caller can decide on it. Callers keep one pre-lock read only to choose whom to lock (viewers, spared, all) and for the tenant id. One envelope read per recipient lock; lock order unchanged (`strcmp` on the id everywhere). (a) The seal handler walks the view's viewers, not `recipientsWithRecordsOn()` (removed), so `openIfAbsent` waits on a concurrent uncommitted insert.
16. **The empty records slice 22 creates are harmless.** Every reader of `notification.recipient_part_notice` is `RecipientPartNotices::lock()` (`grep` over src/config/migrations: no other reader after `recipientsWithRecordsOn` goes), and every handler — part, receipt, seal, close, end — calls `openIfAbsent` before reading, so an empty row is exactly the state each would create: `decide()` returns null without part + receipt; `atTheEnd()` reads the view and the two slots, which an empty row leaves unset as a fresh one does; the close's spared loop opens anyway. The history route reads `notification.notification`, not this table; no sweep, report or conservation job reads it. Cost: one row per viewer of an early-sealed document, which the end would open anyway.
17. **Decision 2 on the post-lock view** is pinned by `RecipientPartNoticesTest::a_close_that_landed_while_waiting_withholds_part_complete` (Application, view swapped at the locked read). The e2e (`RecipientNoticesSecuredEarlyHttpTest`) is added in slice 22 only if a `DocumentReadyToSeal` released after the void, ahead of `EnvelopeReadyToSeal`, still yields `DOCUMENT_SEALED`; otherwise slice 22 records why and the Application test is the only pin.

## Deviations
- 03: `RECIPIENT_PART_COMPLETE` es subject reworded to `Ha terminado su participación en «…»` (agreement tripwire in EmailNotificationChannelTest); `EmailLayoutViewTest` tone list extended (`ok`). Positive "continues/ended for you" phrasing asserted on email only; SMS checked for the wrong word's absence. The `Notifications` nelmio tag description moved to slice 05.
- 03: the lane can serve a stale test container to `OpenApiSpecTest` after a yaml-only edit until `nelmio:apidoc:dump` (env=test) rebuilds it.
- 04: no DB DEFAULT on `receipt_issued`/`ended` (SchemaConformanceTest, ADR-0019 §4); factory `PartNotice::fromParts()` (factoryNaming rule). Tests written after the code; red shown by sabotage, accepted by the reviewer.
- 01 (for docs-sync/task-close): docs/ddd/envelope-domain-model.md:306 and ADR-0087 §2.1 still say a decline requests no seal.
- 02: no unit test on IssuedReceipt::issue() (covered by DbalIssuedReceiptRepositoryTest at Integration); if Infection's diff run escapes a mutant there, add tests/F5Sign/EvidenceAudit/Unit/Domain/Aggregate/IssuedReceiptTest.php. ConcurrentReceiptIssuanceTest now leaves two committed RECEIPT_ISSUED rows per run under its own tenant (reviewer: harmless to the relay, BL-138 is about open transactions).
- 01: the SINGLE_SEAL arm of recordPartEnded repeats isFinal()'s mode check and has no sabotage of its own (AC-11d pins the behaviour).
- 05 (for slices 12/13 and the closing review): until slice 12/13 decide it, the NotificationPurpose ⛔ wording and the published purpose description say signers get the _YOUR_COPY member, which nothing sends yet; re-check both once the end handler lands.
- 06: edited Factor5TrailSources (outside Touch, accepted); added a registry census. Implementer reported sha 4d1c9c1d for round 1, real commit 4849cc08.
- 09: the history test does not validate against the published spec (the slice assumed it did); OpenApiSpecTest pins the enum instead.
- 08 (for docs-sync/task-close): ADR-0090 §2.2 and its line on FINAL keyed to completion contradict the code from cdbdfffa; amended at ADR-0089 acceptance. BACKLOG: BL-465/BL-467 are Open rows under ## Closed (pre-existing).
- 07 (for slice 13): the policy throws on a null envelope outcome at the end where the old use case stayed silent (reviewer: probably unreachable); slice 13 must decide what the end does with it and test it.
- 07: orchestrator ruling on spared (BLOCKING standing + hasSigned||DECLINED; unreachable cells labelled); census looks its table up by value (PHPStan rejects default arms on exhaustive enum matches).
- 10: two exception classes created outside Files (accepted); RecipientPartNoticeMissingException's throw is unreachable in production (insert-if-absent + FOR UPDATE in one tx) and untested by choice; one guard test cites no criterion (accepted).
- 11 (for the closing review / BACKLOG): narrow race — the seal handler lists part-notice records without a lock; a receipt/part handler deciding on a view read before the seal commits and inserting its record after can be skipped, so that recipient gets the end notice instead of RECIPIENT_PART_COMPLETE. Comes from advance() reading the view before the row lock; repair = re-read the view under the lock. Reviewer confidence 40.
- 12: edited EndingNoticeCrossingTest (decliner no longer told the linkless notice; renamed), OneResolutionTest and EnablingSmsChangesNothingForAnEmailRecipientTest (constructor). Stale EmailNotificationChannel comments + NotificationPurpose/nelmio twin wording handed to slice 14.
- 12 (for docs-sync): docs/ddd/notification-domain-model.md, EnvelopeVoided consumer row and NotifyEndedEnvelopeRecipients command row still say every invited recipient; add 'A blocking recipient who signed (an admitted commit included) or declined is not sent this notice (ADR-0089 §2.3); their part-notice record is decided here, in recipient-id order.' and change 'must be true for a signer of an earlier step' to 'must be true for an addressee who never acted'.
- 17: round-1 OA wording not yet checked by OpenApiSpecTest (container broken by slice 14's in-flight wiring); slice 14's verify run covers it, and 2c's full run in any case.
- 14: the `_YOUR_COPY` twins' / ENVELOPE_COMPLETED copy says the signer's documents are sealed; slice 13 dropped the seal condition for signers. Reviewer proved it unreachable: EnvelopeCompleted with a signer is recorded only by Envelope::complete() on EnvelopeSealed, after SealEnvelopeUseCase sealed every document with a tip (a failed seal appends nothing); every sent document has a tip. The copy stays.
- 14 (for the security audit): LogNotificationChannel logs `variables` via http_build_query, now including a copy link (older path, LOG channel only).
- 14 (for docs-sync): docs/ddd/notification-domain-model.md (around lines 202, 869–870) still says ENVELOPE_COMPLETED carries no link.
- 16: refusal comes from the real CopyLinkIssuance (orchestrator), not FakeCopyLinkIssuer; the envelope is seeded and outcomes set by UPDATE envelope.recipient.
- 15: removed V-9 delegated-refusal test (property retired by ADR-0089 §2.5, Proposed); policy docblocks say 'lies within' the mint's eligibility, not 'equals' (the policy also needs a sealed document; the mint admits a blocking PENDING with an admitted decline the policy owes nothing). Docs-sync: TASK-050 / TASK-058 handoffs and docs/ddd still describe the copy-ready link as the signing link.
- 19 (for the closing slice): (a) `RecipientNoticesDeclineHttpTest::the_signer_is_told_after_the_seal_with_their_copy` cites AC-5b; cite S-3 / AC-5 instead. (b) assert exactly one RECIPIENT_INVITATION per recipient before filtering invitations out. (c) S-4: assert D_A's DOCUMENT_SEALED exists before "A's seal tells the carrier nothing". (d) Z's notice timing ("at the close") is not asserted. (e) Owner decision 2 (closed_at on PART_COMPLETE) is pinned only at unit tier; the reviewer's e2e recipe (hold D_B's DocumentReadyToSeal, void, release) may be unreachable if the envelope seal pre-empts the early seal — check first; if unreachable, record that the unit tests are the only possible pin.
- 18 (for task-close): the record's AC-3, AC-14j and §2 still say a SINGLE_SEAL signer "always" gets the act notice; owner decision 3 (the last signer, closed at admission, gets only ENVELOPE_COMPLETED) is the deviation to record there.
- 18 (BACKLOG candidate): notification.requested_at has second precision; the history route (TASK-058) can show two notices of one second in either order (P's ACT and COMPLETED pass occurredAt).
- 20 (infra, for the owner): f5sign-infra help strings of rabbit-check-dlx, rabbit-recreate-event-queues and rabbit-check-dlx-prod still say '4 event queues'; prod must import the new queue BEFORE this backend rolls out (auto_setup:false: a missing queue stops the worker reading all five).
- 20: config test is containment, not equality (prod async_events also reads queue.session.events, which async_events_amqp does not list — BACKLOG candidate: session events have no broker round trip in the test transport). Sabotage rebound the lane broker's test vhost binding and restored it.
- 20: `src/F5Sign/Foundation/Serialization/SelfSerializingMessageSerializer.php` docblock edited, outside the plan's two named Foundation docblocks (`OwnsUnitOfWork`, `UnitOfWork`). Docblock-only and true (closing review sweep: `rabbit-check-dlx` lists the queue in `EVENT_QUEUES` since infra `cf46fd0`/`1feaded`); no contract change, so no ADR. Accepted as a deviation.
- Closing review F5 (ADR-0089 §2.6 and record §3.6: owed-link set "equals" → "lies within" the mint census): left to docs-sync, not to slices 22/23 (orchestrator).
- Closing (for docs-sync): ADR-0089 §2.3 / record §3.5 "the `DOCUMENT_SEALED` handler runs the decision for every recipient with a row who can see the document" → "for every recipient who can see the document, opening the record of one who has none, so it waits on a part still being written" (slice 22).
- 22: owner decision 2 has no e2e case: on S-4's waybill the agreement is secured once A signs, so POST /void is refused (EnvelopeEndingEvaluator::decide, AGREEMENT_SECURED); its pins are RecipientPartNoticesTest::a_close_that_landed_while_waiting_withholds_part_complete and the unit tests. The race child script builds DbalRecipientPartNoticeRepository over doctrine.dbal.default_connection (a container lookup would need a phpstan.dist.neon ignore). Docs-sync: ADR-0089:72 'recipient with a row who can see the document'.
- 23 (for docs-sync): docs/ddd/signing-session-domain-model.md:749 'the notices that will carry the link'.
- 22 (BACKLOG/perf-smoke): the end does 1 + N full envelope-context reads (the seal 1 + one per viewer, the close 1 + one per spared): ~N² rows per end; a per-recipient scoped read would remove the quadratic part.
- 22 (BACKLOG candidate): owner decision 2 has no e2e pin; reachable on an unsecured void (step-1 signer sees only their document and signs, step 2 pending, sender voids, held DocumentReadyToSeal released) or on the S-3 decline with the signer's seal held across the decline. Pinned today by RecipientPartNoticesTest::a_close_that_landed_while_waiting_withholds_part_complete + PartNoticePolicyTest.
- 22: window 2 is closed up to the post-lock read; a close committing between a part handler's read and its commit can still be followed by that act notice (the close then re-decides under the same lock) — the most a handler can guarantee without sharing the close's transaction.
- 2c: BL-471 (ChannelChangeReinvitesCrossingTest invitation order) failed once more in the full run at d54ed1f2 and passed 3/3 alone; task-close adds this second sighting to BL-471.
- validate (for docs-sync/task-close): ADR-0086:97 and ADR-0072:494 still say 'Issuing records no fact'.
- contract-check (for docs-sync): docs/frontend-handoff/TASK-071-signer-integrator-signed-copy-final.md — (W1) its Naturaleza row says "ningún campo, ruta ni valor de enum nuevo" while the history `purpose` enum gains 8 values (its integrator section lists only 4): reword the row and list all 8; (W2) it does not mention the `notification_channels: []` change (with `[]` the integrator also delivers the copy link, POST /api/v1/envelopes/{id}/recipients/{recipientId}/copy-links, and the platform sends no part notices).
- security (for task-close / BACKLOG): (W1) the plaintext copy link sits in notification variables for ten purposes until the deliveries settle (same pattern as the invitation's signing link; ADR-0033 Proposed); (W2) LogNotificationChannel dumps variables including copy links — confirm LOG is never selected in prod; (W3) NOTIFICATION_COPY_BASE_URL is not scheme-validated (https). W4 fixed in c10c588b (comment only).
