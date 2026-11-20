# TASK-072 — The copy card reads what the recipient did, whether their receipt is ready, and where they will be told

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/copy-card-reads`** (implementation tip `abbaa0a7`; the full run below was at the earlier tip `0b0fd90a`), 2026-10-27 — full run at `0b0fd90a` under the `wt-backend` lane (this worktree's own tree, all tiers plus lint, arch and PHPStan): 9621 tests, 106356 assertions, green. Doctrine-guard clean; contract-check and security audit pass with warnings (recorded in §7 and [BL-484](../BACKLOG.md)). Infection (diff-filtered, bars 85/70) at `abbaa0a7`: 258 mutants, covered-MSI 96 %, MSI 93 %; the changed-line verdict exits 1 on 17 survivors, each recorded in §7 as equivalent, unreachable or harness-bound (accepted, as in TASK-060 and TASK-071). [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) is `Accepted` (2026-10-27, by the owner). Pending review; not integrated. |
| **Type** | **Forward build** in Session (two reads, two bundle routes), with one query port added in Evidence & Audit. No migration. |
| **Why** | The signer app is redesigning the screen after the commit (`/done`) and the copy screen (`/c/:link`) as one card: the envelope title, what the recipient did and when, one row per file and the receipt, and a footer. The reads lack what that card shows: when the recipient acted, what the act was (on the copy read), whether the receipt is issued (the app shows the button blind and handles a 409 on the tap), the copy read's `envelope_outcome` and the recipient's name, and where the part-end notice of TASK-071 will reach them. Several documents are downloaded one by one, and chained downloads are unreliable on iOS Safari. |
| **Builds on** | [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (the receipt and its routes), [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) (the copy link and `GET /api/v1/copy`), [ADR-0089](../adr/ADR-0089-a-recipient-is-told-when-their-part-ends.md) (the part-end notices and `RecipientPartAct`), [ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md) (`signed_copy`, all-or-nothing after the commit), [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) (declared notification channels), [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.7 (Session's mask is not Foundation's), [ADR-0039](../adr/ADR-0039-per-recipient-document-access.md) (which documents a recipient reaches). |
| **Scope** | New members on `GET /api/v1/signing/session` and `GET /api/v1/copy`; two new routes that bundle the recipient's documents as a ZIP; `Cache-Control: no-store` on the copy routes ([BL-472](../BACKLOG.md)); the signer handoff. ⛔ **Not** the sender's name (owner, 2026-10-27: a separate task in which the integrator names the sender per envelope), not `branding.company_name`, not any change to who receives a notice or a receipt. |
| **Decision record** | **[ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md), `Accepted` 2026-10-27 (owner)**, drafted with this record (id swept over every ref and worktree on 2026-10-27; ADR-0090 is the highest). It landed in this task's changeset (with its three `docs/adr/README.md` edits) and was accepted there once §5's bars were green. It records that Session reads Evidence & Audit's contract for the receipt's standing, amending ADR-0086 §2.6 and ADR-0088 §2.5 (*"Session gains no dependency on Evidence & Audit"*), on the Session ↔ Signature Execution precedent (`Session/Contract/Query/SignatureImageReader`, TASK-053), and answers ADR-0083 §7.2, which refused a different cycle (Envelope ↔ Session). |
| **Sibling** | None open. The sender's name is a later task (owner, 2026-10-27). |

<!-- OFFREPO: the six asks came from the signer app's session on 2026-10-27 (`f5sign-signer`, branch `develop`, local),
which already reads every new member as optional (absent = not shown) and offers the bundle only when the read
carries `receipt`. Restated here: the card shows "Firmado/Aprobado/Rechazado <date>" from `acted_at` plus the role
(session read) or `act` (copy read); a receipt button enabled from `receipt`; a line "te enviaremos el enlace a tu
copia a <masked destination>" from `notified_on`, shown only once TASK-071 is deployed; a "download all" button for
two or more documents. Two reviews of the receipt design (an architecture evaluation and an adversarial one) ran in
the owner's session on 2026-10-27; their conclusions are restated in §4 #2. -->

---

## 1. Why this task exists

Owner decisions, 2026-10-27:

- **The card's data comes from the backend, every member optional for the app.** Owner said: "Me parece bien si"
  to the reads, and "Si, inclúyelo" to `act` on the copy read.
- **No sender in this task.** `branding.company_name` on the session read is the envelope title (a known defect,
  ADR-0049 §2.3 amendment of 2026-08-18), and the tenant's name is the integrator's account, not the party that
  sends a waybill. A later task lets the integrator name the sender per envelope.
- **The ZIP is in this task.** Owner said: "zip en esta tarea".
- **The receipt's standing is read from Evidence & Audit through a contract port whose implementation the receipt
  routes also call** (`ReceiptStandingRule::receiptOrPending()`) (option A′ of §4 #2). Owner said: "Venga task 72 con A'".

## 2. What already exists (reuse, do not rebuild)

**The session read.** `Session/UI/Http/GetSigningSessionController` presents `SigningSessionReader::read()`'s
`SigningSessionView` as 13 top-level keys: `session_id`, `status`, `envelope_outcome`, `signed_copy`, `envelope`,
`documents`, `fields`, `auth_requirements`, `auth_status`, `signer` (`name`, `email`, `role`), `config`,
`branding`, `fields_draft`. `envelope_outcome` is `RecipientEnvelopeContextView::publishedOutcome()` (`AGREED`,
`NOT_AGREED`, null while open; ADR-0073 §2.15). `signed_copy` is `SignedCopy::of()`. `documents[]` items carry
`display_name`. The read refuses before presenting: a retired credential (401), a closed envelope (409
`ENVELOPE_NO_LONGER_LIVE`), a turn not reached (409 `STEP_NOT_ACTIVE`), a sealed record pending (409 `SEAL_PENDING`),
a part released without acting (409 `LEG_CLOSED`).

**The copy read.** `Session/UI/Http/GetCopyController` presents `CopyContentsReader::list()`'s `CopyContents` as
`envelope_id`, `recipient_id`, `document_title` (the envelope title), `documents[]` (`document_id`, `name`) ,
`signed_copy`, `has_receipt`. `documents[].name` is already the document's display name
(`DocumentView::$displayName`, trimmed), not its file name. `has_receipt` is "this recipient acted", read from
Session's own `Contract/Query/SessionStatusReader` (`closedByTheRecipientsOwnAct()`), documented as never read from
Evidence & Audit.

**When and how a recipient acted.** Envelope's `envelope.recipient.admitted_at` / `admitted_act` (`COMMIT` |
`DECLINE`), on `Contract/View/RecipientView::$admittedAt` / `$admittedAct`, added by `Version20260928131928`.
⚠ That migration backfilled admissions only on envelopes that were `SENT`, or `VOIDED` with the act before the
close; an act on an envelope that was already `READY_TO_SEAL` or `COMPLETED` when it ran has `admitted_at` null. Session's `signing_session.completed_at` is
set to the admission instant by `SigningSession::commitSignature()`; `SigningSession::decline()` stamps no time on the session row
(there is no `declined_at`); the decline's instant lives only on its `SESSION_DECLINED` fact.
`Envelope\Contract\Type\RecipientPartAct` (`SIGNED`, `APPROVED`, `DECLINED`) is the vocabulary of
`RECIPIENT_PART_ENDED`; `Envelope::recordPartEnded()` derives it as `DECLINED` for a decline and
`role()->signs() ? SIGNED : APPROVED` for a commit.

**The receipt.** Owned by Evidence & Audit: `IssuedReceipt` rows in `evidence_audit.issued_receipt` (RLS enabled
and forced, `Version20261023100913`), `IssuedReceiptRepository`, the fact `RECEIPT_ISSUED` (since 2026-10-26; no
fact exists for receipts issued before). The two routes, `GetSessionReceiptHandler` and `GetCopyReceiptHandler`,
decide in one order: a row → its bytes (200) or 409 `RECEIPT_UNAVAILABLE` (`ReceiptBytes::read`); no row and the
session closed by the recipient's own act (`SessionStatus::closedByTheRecipientsOwnAct()`) → 409
`RECEIPT_NOT_READY`; otherwise 404. Evidence & Audit already reads `Session/Contract/Query/SessionStatusReader`.
`EvidenceAudit/Contract/` holds only `Event/` and `Type/`.

**Dependencies.** `deptrac.yaml` already lists `EvidenceAuditContract` for `SessionApplication` and
`SessionInfrastructure`; `SessionUI` may not import it. No file under `src/F5Sign/Session` imports Evidence & Audit
today. Session and Signature Execution already read each other's contracts (`SignatureImageReader`, TASK-053).

**Notification channels.** `Envelope\Contract\Type\NotificationChannels` (`channels(): list<NotificationChannel>`
over `EMAIL` | `SMS`, `mode(): ?NotificationMode` over `IN_ORDER` | `ALL_AT_ONCE`) on
`RecipientView::$notificationChannels`, beside `$email` and `$phone` (unmasked). Session already reads email and
phone through `EnvelopeQueryInterface::getContextForRecipient()`. Session's mask is
`Session/Application/Service/MaskedDestination::of()`, used by the auth descriptor and `OpenCopyController`;
ADR-0078 §2.7 keeps it apart from `Foundation\ValueObject\MaskedContact` on purpose.

**Document downloads.** `DownloadSigningDocumentController` (`SigningDocumentReader`) and
`DownloadCopyDocumentController` (`CopyDocumentReader`) serve one document: 200 with `inline` disposition, a UTF-8
filename plus ASCII fallback, `private` and `no-store` on both; a bare 404 for every refusal (published as
one enumerated answer); the copy route a 409 when the bytes are no longer kept. `ext-zip` is built into the image
(`Dockerfile`, `docker-php-ext-install zip`) but not declared in `composer.json`.

**Tests beside them.** `tests/F5Sign/Session/Unit/UI/Http/GetSigningSessionControllerTest.php`,
`GetCopyControllerTest.php`, `CopyReadControllersDocumentTheirCodesTest.php`;
`tests/F5Sign/Session/Application/Query/SigningSessionReaderTest.php`, `CopyContentsReaderTest.php`,
`SigningReadersCannotDisagreeTest.php`, `CopyReaderShowsWhatTheSigningReaderWouldTest.php`;
`tests/F5Sign/Session/Acceptance/SigningReadEndpointsHttpTest.php`, `CopyReadHttpTest.php`,
`SignedCopyAfterTheCommitHttpTest.php`; `tests/F5Sign/Acceptance/OpenApiSpecTest.php`.

## 3. Scope

1. **`GET /api/v1/signing/session` gains** `acted_at` (ISO-8601 or null), `receipt` (`null` | `PENDING` |
   `ISSUED`) and `notified_on` (a list of `{channel, masked_destination}`).
2. **`GET /api/v1/copy` gains** `acted_at`, `act` (`SIGNED` | `APPROVED` | `DECLINED` | null), `receipt`,
   `envelope_outcome` and `recipient_name`. `documents[].name` stays as it is: it is already the display name.
3. **A receipt-standing port** in `EvidenceAudit/Contract/Query` (working name `ReceiptStandingReader`, returning a
   `Contract/Type` enum `PENDING` | `ISSUED`, or null), implemented in Evidence & Audit's Application layer with the
   receipt routes' own rule (row first, then the session's status); `GetSessionReceiptHandler` and
   `GetCopyReceiptHandler` take that part of their decision from it and keep their own refusals before it. Session's
   Application layer maps the enum to a Session-side value: `SessionUI` has no edge to Evidence & Audit's contract.
4. **Two bundle routes:** `GET /api/v1/signing/session/documents.zip` (session credential) and
   `GET /api/v1/copy/documents.zip` (copy read credential), `application/zip`, `attachment`, holding every document
   the matching read lists, each read through the single-document reader.
5. **`Cache-Control: no-store`** on `POST /api/v1/copy/open`, `POST /api/v1/copy/auth`, `GET /api/v1/copy`,
   `GET /api/v1/copy/receipt` and the copy bundle; it closes [BL-472](../BACKLOG.md).
6. **ADR-0091** as `Proposed`, and the frontend handoff to the signer
   (`docs/frontend-handoff/TASK-072-signer-copy-card-reads.md`).
7. **Hardening of the bundle and the copy link mint** (owner-approved addition, 2026-10-27, from this task's security
   audit): bundle entry names also lose format characters and line/paragraph separators, are composed to NFC before
   the duplicate check, have `:` replaced, a Windows reserved stem prefixed with `_`, and are cut to 240 UTF-8 bytes;
   the bundle is built on disk with at most two documents' bytes in memory and streamed with `Content-Length`, every guard and
   every custody read still before the first byte; `POST /api/v1/envelopes/{id}/recipients/{recipientId}/copy-links`
   answers `Cache-Control: no-store`. No criterion changes.

Concepts re-cut: `has_receipt` (now equal to `receipt != null`), `MaskedDestination`'s "one route" docblock (a third
route publishes its output), "Session gains no dependency on Evidence & Audit"
(ADR-0086 §2.6, ADR-0088 §2.5, the `CopyContentsReader::hasActed` docblock, TASK-070's handoff), the receipt
handlers' inline rule.

## 4. Key decisions

1. **`acted_at` is the admission of the recipient's act**, commit or decline, the instant the act's notices and
   receipt are about. The source must cover acts admitted before `admitted_at` existed (§2): the plan picks it
   (`admitted_at`), and AC-1e pins the legacy case: an act on an envelope that
   was already `READY_TO_SEAL` or `COMPLETED` when admissions were backfilled has no admission instant on the
   recipient row (the read does not go to the event log for it), so its `acted_at` is the
   landing's instant (`RecipientView::$outcomeRecordedAt`), documented as such on the published member.
2. **The receipt's standing comes from one predicate in Evidence & Audit (option A′).** Options weighed by two
   independent reviews on 2026-10-27: (A′) a contract port whose implementation the receipt routes also call (`ReceiptStandingRule::receiptOrPending()`); (A) the same port with
   the rule copied into Session; (B) Session subscribing to `RECEIPT_ISSUED` and keeping a mark; (C) inferring it in
   Session from `signed_copy` and status; (D) no field. B was refused: receipts issued before 2026-10-26 have no fact
   and would read `PENDING` beside a 200, and the relay's lag or a parked delivery leaves the mark behind the row
   with nothing to reconcile them. C is wrong under `SINGLE_SEAL` (receipt at the commit, copy at completion) and in
   the seconds between a landed signature and its receipt. A′ over A because one rule cannot drift between the field
   and the routes.
3. **No fourth value for `RECEIPT_UNAVAILABLE`.** `ISSUED` means "recorded"; detecting an unreadable custody would
   read the object store on every poll, and it is an operator incident, not a client state.
4. **A failing standing read fails the whole read.** It runs on the same connection and tenant scope as the rest of
   the read; degrading to null would tell a waiting signer "you have not acted" and stop their polling.
5. **`notified_on` says where the notices are addressed, not that they arrive.** Declared order, Session's mask,
   a channel whose contact is absent left out; delivery outcomes stay on the sender's history route (ADR-0078 §2.7),
   which Session may not read (ADR-0037). The mask is the one the auth descriptor already shows a link holder before
   the gate (ADR-0049 §2.3, route 3), but `notified_on` can show a destination the descriptor never did (an SMS
   channel beside an email gate, any channel beside an access-code gate). It is shown only behind the session
   credential, to the recipient whose contacts they are. `MaskedDestination`'s docblock, which still says one route
   serves it, is corrected.
6. **The bundle is all or nothing**, as the single route is after the commit (ADR-0090 §2.3): if any listed document
   would be refused, the bundle is refused with the single route's answer. It holds the same bytes the single route
   serves.
7. **`ext-zip` is declared in `composer.json`.** Only the lock's `content-hash` changes (`composer update --lock`),
   no package moves; repo rule 1 forbids regenerating the lock otherwise.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | The session read carries `acted_at`: the admission instant of this recipient's act, null before it (members AC-1a…e) | owner | Application + Acceptance | return null |
| AC-2 | The copy read carries `acted_at`, the same instant as AC-1 for the same recipient | owner | Application + Acceptance | read another field |
| AC-3 | The copy read carries `act`: `SIGNED`, `APPROVED`, `DECLINED`, or null with no act (members AC-3a…d) | owner | Application | map an approval to `SIGNED` |
| AC-4 | The copy read carries `recipient_name`, this recipient's own name | owner | Application + Acceptance | serve another recipient's name |
| AC-5 | The copy read carries `envelope_outcome`, equal to the session read's for the same recipient and instant | owner | Application | publish the raw outcome while open |
| AC-6 | Both reads carry `receipt`: `ISSUED`, `PENDING` or null (members AC-6a…c) | owner | Application + Acceptance | drop the row check |
| AC-7 | The session read carries `notified_on` (members AC-7a…e) | owner | Application + Unit | unmask the destination |
| AC-8 | `GET /api/v1/signing/session/documents.zip` serves every document the session read lists, or the single route's refusal (members AC-8a…e) | owner | Acceptance | serve a partial bundle |
| AC-9 | `GET /api/v1/copy/documents.zip` serves every document the copy read lists, or the single route's refusal (members AC-9a…e) | owner | Acceptance | serve a partial bundle |
| AC-10 | `receipt` and the receipt routes answer from one rule: `ISSUED` ⇔ 200 or 409 `RECEIPT_UNAVAILABLE`, `PENDING` ⇔ 409 `RECEIPT_NOT_READY`, null ⇔ 404, over every `SessionStatus` × row present/absent (members AC-10a…c) | derived — [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) §2.6 | Application + Acceptance | check status before the row |
| AC-11 | A failure of the standing read fails the session read and the copy read; neither answers null | derived — [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) §2.3 | Application | catch and return null |
| AC-12 | On the copy read, `has_receipt` is true exactly when `receipt` is not null | derived — [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) §2.5 | Application | keep the old predicate beside a changed one |
| AC-13 | The session read and the copy read agree on `acted_at`, `receipt` and `envelope_outcome` for one recipient context | derived — `tests/F5Sign/Session/Application/Query/CopyReaderShowsWhatTheSigningReaderWouldTest.php` | Application | read one member from a second source |
| AC-14 | The standing read is tenant-scoped: a tenant-B receipt row never reads `ISSUED` under a tenant-A credential | derived — `migrations/Version20261023100913.php` | Integration (RLS) | read without the tenant scope |
| AC-15 | The copy routes answer with `Cache-Control: no-store` (members AC-15a…e) | derived — [BL-472](../BACKLOG.md) | Acceptance | drop the directive |
| AC-16 | A bundle's entries are the documents' display names, made unique, stripped of path separators and control characters, with the single route's bytes (members AC-16a…d) | derived — `src/F5Sign/Session/UI/Http/DownloadCopyDocumentController.php` | Unit + Acceptance | keep a `/` in an entry name |
| AC-17 | The new members appear only after the reads' existing refusals: a turn not reached still answers 409 `STEP_NOT_ACTIVE`, a retired credential 401 | derived — [ADR-0039](../adr/ADR-0039-per-recipient-document-access.md) | Acceptance | present before the refusals |
| AC-18 | Both reads' published `required` key sets and both bundle routes' responses are documented in `#[OA\*]` and match what is emitted | derived — `tests/F5Sign/Acceptance/OpenApiSpecTest.php` | Unit + `OpenApiSpecTest` | leave a member out of `required` |
| AC-19 | `deptrac.yaml` is unchanged, and Session reaches Evidence & Audit only through its `Contract/` | derived — [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) §2.4 | arch (deptrac) | import the Application service |
| S-1 | A `SEQUENTIAL_PADES` envelope with two documents: after the commit the session read polls `receipt` `PENDING` then `ISSUED`, the bundle answers 404 while `signed_copy` is `APPLYING` and then 200 with two entries; the copy link reads the same | derived — [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) §2.2 | Acceptance, live DSS | — |
| S-2 | A decline: the copy read shows `act: DECLINED`, `acted_at`, `receipt`, no documents, and the copy bundle answers 404 | derived — [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) §2.5 | Acceptance | — |

- **Gates:** suite, PHPStan, deptrac and lint under the `wt-backend` lane on this task's worktree.

**Notes on AC-1**
- AC-1a — a signer's commit under `SEQUENTIAL_PADES`: the admission instant, already while `signed_copy` is `APPLYING`.
- AC-1b — an approver's commit: its admission instant.
- AC-1c — a decline: its admission instant (the session read answers 200 with `status: DECLINED`).
- AC-1d — before any act: null.
- AC-1e — an act on an envelope that completed before `admitted_at` existed (no admission row): the landing's
  instant, never null while `act` or `status` says the recipient acted; a commit and a decline each.

**Notes on AC-3**
- AC-3a — a commit by a role that signs: `SIGNED`. AC-3b — a commit by a role that approves: `APPROVED`. AC-3c — a
  decline: `DECLINED`. AC-3d — no act (an informational member reading their copy): null. The classification is
  `RecipientPartAct`'s, by `Role::signs()`; a census over `Role` fails on an unclassified member.

**Notes on AC-6**
- AC-6a — a receipt row exists: `ISSUED`. AC-6b — the recipient acted and no row exists yet: `PENDING`. AC-6c — no
  act: null.

**Notes on AC-7**
- AC-7a — `notification_channels: []`: `[]`.
- AC-7b — two declared channels: both, in declared order, each `{channel, masked_destination}` and no other key.
- AC-7c — a declared channel whose contact is absent (an unclaimed slot's `SMS` with no phone): left out.
- AC-7d — the destination is Session's `MaskedDestination`, never the contact in full. Sabotage: serve `$email`.
- AC-7e — the member's key set is closed: an added key fails the test.

**Notes on AC-8 and AC-9** (same members on each route)
- AC-8a / AC-9a — two documents ready: 200, `application/zip`, `attachment`, `private` and `no-store`, two entries.
- AC-8b / AC-9b — after the commit, `signed_copy` `APPLYING` or `AWAITING_ENVELOPE`: the single route's 404, no partial bundle.
- AC-8c / AC-9c — no document listed (a decliner): 404.
- AC-8d / AC-9d — no credential, or the other kind of credential: 401.
- AC-8e / AC-9e — a document whose bytes are no longer kept (its custody destroyed): the single route's 409, on each route.
  The member is the single route's answer, whatever it is; on the session route that is also a 409 (`CustodyBytesUnavailableException`
  from the store), not a 404 — a sent envelope cannot list a document with no bytes at all (the send refuses one).

**Notes on AC-10**
- The census runs every `SessionStatus` case with a receipt row and without one; a new case fails it unclassified.
- AC-10a — a row, whatever the status: `ISSUED`, and the route answers 200 (or 409 `RECEIPT_UNAVAILABLE`).
- AC-10b — no row, `COMPLETED` or `DECLINED`: `PENDING`, and the route answers 409 `RECEIPT_NOT_READY`.
- AC-10c — no row, any other status: null, and the route answers 404.
- Each route keeps its own refusals before the rule (the session route's context refusals, the copy route's
  admission); their existing tests stay.

**Notes on AC-15**
- AC-15a `POST /api/v1/copy/open`, AC-15b `POST /api/v1/copy/auth`, AC-15c `GET /api/v1/copy`, AC-15d
  `GET /api/v1/copy/receipt`, AC-15e `GET /api/v1/copy/documents.zip`.

**Notes on AC-16**
- AC-16a — two documents with the same display name: two entries, the second suffixed.
- AC-16b — a display name with `/`, `\` or `..`: no entry escapes the archive's root.
- AC-16c — a display name with control characters or nothing left after stripping: a fallback name.
- AC-16d — each entry's bytes equal what the single route serves for that document.

## 6. Open follow-ups (track, don't solve here)

1. **The sender's name per envelope.** A separate task (owner, 2026-10-27): the integrator names the party that
   sends; the card, the invitations and the notices show it.
2. **`branding.company_name` is the envelope title** (ADR-0049 §2.3 amendment). Unchanged here; the signer no longer
   presents it as a sender.
3. **A `PENDING` that never ends.** A parked issuance, a DSS outage, or an act from before TASK-047 keeps `PENDING`
   with no bound, as the receipt route's 409 already does. The handoff tells the app to cap its polling; a backend
   answer to "no receipt will come" is not built.
4. **A bound on the bundle.** Nothing caps a bundle's document count or total size; with the archive on disk, memory
   holds at most two documents and the disk up to about twice the total. The total is known before
   any byte is read (`CustodyStore::describe()`'s `sizeBytes` per document). ⚑ The owner chose no cap in this task
   (2026-10-27); what a later one would be: a cap
   (count and/or total bytes) and its answer, proposed 409 `BUNDLE_TOO_LARGE`, telling the app to fall back to
   single downloads. Tracked as [BL-484](../BACKLOG.md).
5. **BL-472, narrowed.** This task added `no-store` to the copy routes (open, auth, list, documents, `documents.zip`,
   the copy receipt) and to the copy-link mint. Still open in [BL-472](../BACKLOG.md): the signing session's open, the
   session receipt route, `MintSigningTokenController` and the copy OTP send.
6. **`composer update` with plugins cannot resolve on `develop`** (Flex's `7.4.*` restriction against the locked
   `psr-http-message-bridge` 8.1.0 and `sentry-symfony` 5.12.0). Tracked as [BL-485](../BACKLOG.md).
7. **The lane's PHPStan load** (`php-fpm-wt` capped at 2g and 4 CPUs; concurrent full runs exit 137). Tracked as
   [BL-486](../BACKLOG.md).
8. **The single signing document route's OpenAPI omits its 409.** Pre-existing, found by slice 09's review. Tracked as
   [BL-487](../BACKLOG.md).

## 7. Deviations & honest notes

### Scope
- Slice 01 declared `ext-zip` and refreshed the lock with `composer update --lock --no-plugins`: only `content-hash` and the platform list changed (see Decisions, 01).
- Two things the plan did not have: slice 16 edited the `SessionStatusReader` row of `docs/ddd/signing-session-domain-model.md` (the orchestrator asked for it in the slice addendum; docs-sync did the rest of `docs/ddd`), and an amend (slices 17 to 23, below) added entry-name hardening, `servableDocuments()` on both readers, the archive built on disk, `no-store` on the copy-link mint and a lazy, streamed bundle. `readAll()` and `archive()` were removed again in slice 22.
- The ZIP bundles, `no-store` on the copy routes and the signer handoff are in scope (§3); the sender's name is not, and TASK-073 (record only, `develop` at `655562e7`) was checked before wave 3: nothing to integrate.

### Decisions made during implementation
- **Lock refresh (01).** A plugin-enabled `composer update` cannot resolve on `develop`; the lock was refreshed with `--no-plugins`. Pre-existing → [BL-485](../BACKLOG.md).
- **Receipt handlers (07).** They depend on the concrete `ReceiptStandingRule` and call `receiptOrPending()`, because the port's `standingOf()` returns only the enum and a route needs the row for its bytes. ADR-0091 §2.2 was amended in slice 16 to "from the port's implementation, `ReceiptStandingRule::receiptOrPending()`, from which `standingOf()` is derived". Owner told.
- **Production `assert()` (05).** `CopyDocumentReader::contentOf()` narrows `?CustodyId` with an `assert()`, on the precedent of `IssueCopyChallengeUseCase`.
- **Entry names (08, 17).** Slice 08 stripped only `\p{Cc}` as specified; the first audit found that bidi overrides, U+2028/2029 and zero-width characters survived and NFC/NFD counted as distinct (display spoofing only, no path escape). The owner-approved slice 17 strips format characters, treats NFC and NFD as one name, prefixes reserved Windows names, rejects drive letters and cuts a name to 240 bytes on a code point, and the OpenAPI strings say so.
- **Bundle cap (owner, 2026-10-27).** Option 1: no cap now; the proposed 409 `BUNDLE_TOO_LARGE` and the SIGKILL/OOM temp-file residue are filed as [BL-484](../BACKLOG.md).
- **Read then refuse (05, fixed in 18).** Slice 05's `readAll()` read document 1's bytes before refusing document 2: the answer was right, but bytes were fetched before a refusal (timing, logs, egress). Slice 18 replaced it with `servableDocuments()` on both readers, decided before any byte is read, and pins it (`fetchedIds` is empty on a refusal). The pattern was removed outright with `readAll()` in slice 22.
- **Contract-check amend.** W1 rejected: both readers' `filename()` append `.pdf` to any name not ending in it, so `report.docx` becomes `report.docx.pdf` end to end and the handoff §7 is right. W2 (the response headers are unpublished in OpenAPI) is consistent with the other routes, not a regression. W3 done (a note in the TASK-070 handoff; the dashboard told).
- **Owner-approved hardening (§3 #7).** After the first audit the owner approved fixing warnings 1 to 5 and streaming the bundle (slices 17 to 21); the archive is built on disk with at most two documents in memory, and the response is streamed from a lazy bundler.
- **Signer (`f5sign-signer`).** It confirmed its side matches the handoff at `3459472f` and pins the operationIds `get_signing.documents_zip` and `downloadCopyDocumentsBundle`: they must not change. Notify it when this merges to `develop`.
- **Process change: red first.** Slices 04 and 05 ran a proof round (owner): every sabotage red by an assertion, no new test needed; AC-7a cannot go red under a `[]` stub by design. From then on reviewers asked for the red run of each guard before the green, and sabotage was reported by which assertion failed.
- **Lane load (owner, 2026-10-27).** From wave 8 on, implementers ran PHPStan and lint on their own files only; the full PHPStan and Deptrac ran once at the end → [BL-486](../BACKLOG.md).

### Decisions that needed an ADR
- [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md), drafted with this record and decided by the owner on 2026-10-27, landed in this changeset (slice 16, with its three `docs/adr/README.md` edits). The owner accepted it on 2026-10-27, once the tests of its §5 and the arch gate were green.

### Declared and unproven properties
- **Infection on the changed lines (slice 24).** The first run left 30 escaped and 25 not covered; slice 24's tests killed 28 of them (26 by a test that pins them, 2 only by accident, see the last item), and 11 on `#[OA\Get]` arguments of `DownloadSigningDocumentsBundleController` are now `@infection-ignore-all`, as on the copy twin (attribute arguments are never executed; `DownloadSigningDocumentsBundleControllerTest::the_route_documents_its_statuses_and_its_credential` pins them). The 16 left (17 when `:111` below is counted escaped) are equivalent or out of the harness's reach, and the line verdict still fails on them (exit 1):
  - `BundleEntryNames.php:61` TrueValue: equivalent; `isset()` is true for a `false` value as for `true`.
  - `BundleEntryNames.php:88` IncrementInteger: equivalent; element 0 of `explode('.', $stem, n)` is the text before the first dot for any `n` of 2 or more.
  - `BundleEntryNames.php:112` PregMatchRemoveCaret: equivalent; `(.*)` under `/s` matches from offset 0 whether anchored or not.
  - `BundleEntryNames.php:112` PregMatchRemoveFlags (drops `s`): equivalent; without `s`, `.` refuses only line breaks, and every one is gone by then (`\p{Cc}`, `\p{Zl}`, `\p{Zp}` are stripped first).
  - `BundleEntryNames.php:105` ArrayItemRemoval, ReturnRemoval: unreachable; `Normalizer::normalize()` fails only on invalid UTF-8, and the `/u` strip just before already answers `null` for it.
  - `ZipDocumentArchive.php:53` FunctionCallRemoval, `:54` Foreach_: out of reach; the shutdown function runs only in a process that dies of a fatal error, and `a_fatal_error_mid_build_leaves_no_file` proves it in a child process that loads `src/` through `vendor/autoload.php`, where Infection never substitutes its mutant.
  - `ZipDocumentArchive.php:42`, `:65`, `:73`, `:97`, `:102` Throw_: out of reach; `tempnam()`, `ZipArchive::open()` on the file just created, a short `file_put_contents()`, and `fopen()`/`filesize()` of the archive just closed cannot be made to fail in-process (`sys_get_temp_dir()` is cached per process).
  - `DocumentsBundleResponse.php:44` FunctionCallRemoval (`flush()`): out of reach; `flush()` only pushes the SAPI's buffer, which an in-process test cannot see.
  - `DocumentsBundleResponse.php:51` CastString: equivalent; `HeaderBag` (no `strict_types`) coerces an int to a string, so `Content-Length` reads `"<n>"` either way.
  - `DocumentsBundleResponse.php:59` MethodCallRemoval (`setPrivate()`): equivalent today; `ResponseHeaderBag` adds `private` when no `public`, `private` or `s-maxage` is set, and this response sets none.
  - Not pinned, though a run may count them killed: `ZipDocumentArchive.php:111` (`unchangeAll()`) and `:117` (`exchangeArray([])`). Of two runs at slice 24, one counted both killed and the next counted `:111` escaped. The "kill" comes from another mutant's temporary files: four threads share one `/tmp`, and `ZipDocumentArchiveTest` globs `f5s-bundle-*` there. With `unchangeAll()` removed by hand the suite stays green: `close()` then writes an archive that the cleanup deletes. `exchangeArray([])` only stops the shutdown function from unlinking those paths when the process ends, and no in-process test reaches that.
- A SIGKILL or OOM mid-build leaves `f5s-bundle-*` in php-fpm's temp directory and nothing reaps it (the custodian runs in another container); a slow or stalled reader holds an FPM worker. No harness here reaches either → [BL-484](../BACKLOG.md).
- Idle-poll behaviour for a `PENDING` receipt that never ends is not built (§6 #3).
- Slice 12 (low): `acted_at` is null for a recipient who acted with neither instant on the row, which the published "null before it" does not cover; and `receipt` null published as "not acted" depends on the rule and the `acted_at` fallback agreeing for legacy acts.
- Slice 13 (low): the copy `envelope_outcome` OA says "same value, at the same moment" as the session read, but between close and seal the session read answers 409 `SEAL_PENDING` with no body.
- Harness: every run above names the `wt-backend` lane on this worktree's tree, never the main checkout's stack.

### Record corrections already committed
- `0e05918e`: §2 and §4 #1 claimed the admission backfill covered only in-flight envelopes and that a decline has no instant; corrected to state which envelopes the backfill skipped (found by slice 03's review). No criterion changed.
- `98b6c655`: the AC-8e note said the session member "pins the single route's 404"; a destroyed custody makes the single route answer 409, and the bundle answers the same 409 on both routes. Criterion unchanged; owner told.

### Debt left behind, and where it lives now
- Bundle bound, temp-file residue, no rate or concurrency limit on the bundle routes → §6 #4, [BL-484](../BACKLOG.md).
- `no-store` still missing on the signing open, the session receipt, `MintSigningTokenController` and the copy OTP send → §6 #5, [BL-472](../BACKLOG.md) (narrowed, still Open).
- Plugin-enabled `composer update` blocked → §6 #6, [BL-485](../BACKLOG.md).
- Lane PHPStan load → §6 #7, [BL-486](../BACKLOG.md).
- The single signing document route's missing 409 in OpenAPI → §6 #8, [BL-487](../BACKLOG.md).
- The sender's name, `branding.company_name`, and a `PENDING` that never ends → §6 #1 to #3.

### Delegated work
- 23 slices in 11 waves: 8 critical (`opus`), 13 standard and 2 mechanical (`sonnet`). Fix rounds: 10 slices needed one (03, 06, 08, 11, 13, 15, 16, 17, 19, 21) and slice 09 needed two; the rest closed in round 1. Slice 01 returned NEEDS_CONTEXT and the orchestrator finished it with `--no-plugins`. Several round-2 fixes (docblock-only, test-only, comment) were checked by the orchestrator instead of a new review.
- Replication delegated to the `replicator`: none. Every slice report's `## Delegated` says none, or that the repetitions were below the threshold of three or each a first instance.
- Full-run history: green at `9a36971e` (9588 tests) and at `8b952c18` and `0b0fd90a` (9621 tests); no red full run.

### Cost of the run
- Slices: 23 in 11 waves (8 critical on opus, 13 standard and 2 mechanical on sonnet); the plan had 16, and slices 17 to 23 came from the closing review and the security audit's amend.
- Fix rounds: 12 in all (10 slices with one, slice 09 with two); no slice past round 3; one escalation of a kind (slice 01 finished by the orchestrator).
- Full runs: three, 786 s, 792 s and 794 s, all green; the baseline was 7807 tests (fast tier) and the final count 9621.
- Wall-clock from preparation (10:57) to the last gate (15:26 UTC): about 4.5 h, including the owner's plan approval and the amend.
- Tokens per model: not recorded in `run.log`, so no figure is given; Infection: Infection (diff-filtered, bars 85/70) at `abbaa0a7`: 258 mutants, covered-MSI 96 %, MSI 93 %; the changed-line verdict exits 1 on 17 survivors, each recorded in §7 as equivalent, unreachable or harness-bound (accepted, as in TASK-060 and TASK-071).
