# TASK-075 — A recipient's documents bundle can carry their receipt

| Field | Value |
|-------|-------|
| **Status** | **Done — integrated in `develop` on 2026-10-28** from `feat/bundle-with-receipt` (develop `bdba6313` merged in at `fa00ad6d`; ADR-0093 accepted by the owner the same day). Last full run at `4a9ad377` under the `wt-backend` lane (this worktree's own tree, all tiers, plus lint, arch and PHPStan): 9765 tests, 107610 assertions; its one failure, `ChannelChangeReinvitesCrossingTest`, is the known flake [BL-471](../BACKLOG.md) (invitation order, untouched by this branch, green 5/5 alone), seen a third time; after it only `docs/BACKLOG.md` and this record changed. Gates: task-validate, contract-check and doctrine-guard pass; security-audit warn (`composer audit` not provided, no manifest change); perf-smoke skipped (no `perf:seed`). Infection on the changed `src/` files: covered-MSI 98.44 %, MSI 98.44 % (bars 85 / 70), two accepted survivors (§7). The `DocumentsBundleResponse` docblock lists 404/409 only ([BL-490](../BACKLOG.md)). |
| **Type** | **Forward build** in Session (a variant of the two bundle routes), with one query port added in Evidence & Audit's `Contract/`. No migration. |
| **Why** | The recipient's card offers the signed files and the receipt as separate downloads. TASK-072 bundled the files because chained downloads are unreliable on iOS Safari; the receipt is the download left over. The card also unlocks the files and the receipt at different moments under `SEQUENTIAL_PADES` (the copy is ready when the signature lands; the receipt is rendered and sealed seconds later), which reads as two separate events for one act. |
| **Builds on** | [TASK-072](TASK-072-the-copy-card-reads-what-the-recipient-did.md) (the two bundle routes, `DocumentBundler`, `BundleEntryNames`, the reads' `receipt` member), [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (the receipt and its routes), [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) (the copy read credential and the copy receipt route), [ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md) (documents all-or-nothing after the commit), [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) (Session reads the receipt's standing from Evidence & Audit's contract). |
| **Scope** | A `with_receipt` query parameter on `GET /api/v1/signing/session/documents.zip` and `GET /api/v1/copy/documents.zip`; a contract port through which Session obtains the receipt's bytes; the signer handoff (when the card unlocks the files and the receipt, and when it offers each bundle). ⛔ **Not** a cap on the bundle's size ([BL-484](../BACKLOG.md)), not `no-store` on the session receipt route ([BL-472](../BACKLOG.md)), not any change to the bundle without the parameter or to the receipt routes' own answers. |
| **Decision record** | **[ADR-0093](../adr/ADR-0093-a-recipients-bundle-takes-their-receipt-from-the-receipt-routes-rule.md), `Accepted` 2026-10-28 (owner)**, drafted with this record (id swept over every ref and worktree on 2026-10-28; ADR-0092 is the highest), accepted by the owner on 2026-10-28 once §5's bars were green. ADR-0091 §3.3 says its port answers a standing, *"never the receipt's content; a later member that reveals the receipt's data is a new decision"*. This task is that decision: Session obtains the receipt's bytes through an `EvidenceAudit/Contract/Query` port whose implementation holds the receipt routes' whole decision (the refusals now inside `GetSessionReceiptHandler` and `GetCopyReceiptHandler`, then `ReceiptStandingRule::receiptOrPending()` and `ReceiptBytes::read()`), with the two handlers delegating to it, on the A′ precedent of ADR-0091. It amends ADR-0091 §3.3, [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) §7.5 (*"What is rejected here is Session finding the receipt's bytes"*) and [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) §2.5 (*"The receipt's bytes are still served by the Evidence & Audit route"*): Session still does not find the bytes, Evidence & Audit hands them over under its own rule. |
| **Sibling** | None open. |

<!-- OFFREPO: the request came from the owner's session on 2026-10-28, after TASK-072 merged. The signer app
(`f5sign-signer`, local) pins the bundle routes' operationIds `get_signing.documents_zip` and
`downloadCopyDocumentsBundle`; they must not change. Nothing here depends on reading the app. -->

---

## 1. Why this task exists

Owner decisions, 2026-10-27/28:

- **Two bundles.** Owner said: "Yo lo haria de dos formas, una zip con todos los ficheros firmados, o zip con todos
  los ficheros firmados + el justificante de firma."
- **One unlock.** Owner said: "a nivel de frontend tambien se ve raro porque primero desbloquea los ficheros firmados
  y luego desbloquea el justificante de firma. Tambien deberia de hacerlo todo del tiron cuando esté el de firma."
- **The shape** (proposed in the session and confirmed: "Dale si"): one parameter on the existing routes rather than
  two new routes, so the pinned operationIds stay; a receipt not yet issued refuses the bundle rather than leaving
  the receipt out; under `AWAITING_ENVELOPE` the receipt is not held back for the files, which may take days.

## 2. What already exists (reuse, do not rebuild)

<!-- OFFREPO: the signer app (`f5sign-signer`) named in this record and its handoff is another team's repo; every
fact taken from it (the pinned operationIds, the card's rows) is restated here. -->

**The bundle routes.** `GET /api/v1/signing/session/documents.zip` (`config/routes/api/signing.php`, route
`signing.documents_zip`, `Authn::SESSION_CREDENTIAL`, controller `Session/UI/Http/DownloadSigningDocumentsBundleController`)
and `GET /api/v1/copy/documents.zip` (`config/routes/api/copy.php`, route `copy.documents_zip`, `Authn::COPY_READ`,
controller `Session/UI/Http/DownloadCopyDocumentsBundleController`). Neither reads a query parameter today. Each asks
its reader for `servableDocuments()` (`Session/Application/Query/SigningDocumentReader`, `CopyDocumentReader`;
null → 404, a missing claim or gate attribute → 400), then `DocumentBundler::bundle()`, then
`DocumentsBundleResponse::of()`: a `StreamedResponse`, `application/zip`, `Content-Length`, `attachment;
filename=documentos-<envelope id>.zip`, `private` and `no-store`, built only once the archive is complete, so every
refusal comes before any byte. A custody that cannot be read propagates from Storage's `CustodyStore` (a 409 on
both routes, TASK-072 AC-8e / AC-9e). The copy route's `#[OA\Get]` carries `operationId: downloadCopyDocumentsBundle`;
the signing route's carries none and Nelmio derives `get_signing.documents_zip` from the route name.

**The bundler.** `Session/Application/Service/DocumentBundler::bundle(non-empty-list<ServableDocument>)` names the
entries through `BundleEntryNames::of()` (strips `\p{Cc}`, `\p{Cf}`, `\p{Zl}`, `\p{Zp}`, composes to NFC, maps
`/ \ :` to `_`, prefixes reserved Windows stems, adds `.pdf`, caps at 240 bytes, dedupes case-insensitively with
` (2)`, ` (3)`) and hands a lazy generator of `ArchiveEntry(name, bytes)` to the `Session/Application/Port/DocumentArchive`
port (adapter `Session/Infrastructure/Archive/ZipDocumentArchive`, one temp file per entry, all or nothing), so at
most two entries' bytes are in memory. Its result is `BuiltArchive(stream, size)`.

**The receipt.** Owned by Evidence & Audit. `EvidenceAudit/Application/Query/GetSessionReceiptHandler` refuses with
null (→ 404) on an unknown context, an unsent envelope, a retired credential (`accessGatePassedAt` before
`credentialsRetiredAt`), a document withheld from the recipient, or a step that holds the recipient back; then
`ReceiptStandingRule::receiptOrPending()`: a recorded `IssuedReceipt` → `ReceiptBytes::read()`, `PENDING` →
`ReceiptNotReadyException` (409 `RECEIPT_NOT_READY`), otherwise null. `GetCopyReceiptHandler` first asks Session's
`Contract` `CopyReadAdmission::admits()` (false → `CopyReceiptRefusedException`, 401), then the same rule.
`ReceiptBytes::read()` reads the custody through `CustodyStore` and turns a missing or unreadable custody into
`ReceiptUnavailableException::forRecipient` and a digest mismatch into `ReceiptUnavailableException::substituted`
(both 409 `RECEIPT_UNAVAILABLE`); it returns `ReceiptContent` (filename `justificante-<envelope>-<recipient>.pdf`,
lowercased, `application/pdf`, sha256). The controllers (`EvidenceAudit/UI/Http/DownloadSessionReceiptController`,
`DownloadCopyReceiptController`) log a detected substitution at `error`. `ReceiptContent` lives in
`Application/Query`, outside `Contract/`.

**The contract today.** `EvidenceAudit/Contract/Query/ReceiptStandingReader::standingOf(AuditedEnvelopeRef,
AuditedRecipientRef): ?ReceiptStanding` (`ISSUED`, `PENDING`), implemented by `ReceiptStandingRule`; no
`Contract/` type carries a receipt's bytes. `deptrac.yaml` grants `EvidenceAuditContract` to `SessionApplication`
and not to `SessionUI`.

**The reads and the handoff.** Both reads carry `signed_copy` (null, `APPLYING`, `AWAITING_ENVELOPE`,
`CONTAINS_YOUR_SIGNATURE`, `FINAL`; the documents answer 404 in `APPLYING` and `AWAITING_ENVELOPE`, ADR-0090 §2.3)
and `receipt` (`ISSUED`, `PENDING`, null). Under `SINGLE_SEAL` the receipt is issued at the commit and the copy at
the envelope's completion; under `SEQUENTIAL_PADES` both follow `RECIPIENT_SIGNED`, the receipt seconds later.
[`docs/frontend-handoff/TASK-072-signer-copy-card-reads.md`](../frontend-handoff/TASK-072-signer-copy-card-reads.md)
§7 tells the app to offer "download all" for two or more documents, and §3 to enable the receipt button on `ISSUED`.

## 3. Scope

1. **`with_receipt`** on both bundle routes. Absent: the bundle as TASK-072 shipped it. `1`: the same documents plus
   the recipient's receipt as one more entry. Any other value: 400.
2. **The receipt's part of the answer is the receipt route's own.** With the parameter, after the bundle's
   readers' refusals (`servableDocuments()`, which reads no bytes), the route answers what the matching receipt route would (404, 401 on the copy route, 409
   `RECEIPT_NOT_READY`, 409 `RECEIPT_UNAVAILABLE`), and builds no archive when it refuses.
3. **A port in `EvidenceAudit/Contract/Query`** (working name `RecipientReceiptReader`) with one method per credential
   kind, taking what each receipt handler takes today (the session method the access-gate instant and the actor, the
   copy method the gate instant), returning a closed `Contract/Type` result (the receipt's filename and bytes, not
   ready, unavailable with missing or substituted, refused, none) rather than throwing Evidence & Audit's
   `Application/Exception` types, which Session cannot import. Its implementation holds the handlers' refusals and the
   standing rule; the two receipt handlers delegate to it and map the result back to the exceptions they throw today,
   so the routes and the bundle answer from one implementation. Session maps the result to its own refusals and logs
   a substitution (AC-11). The result carries the storage cause, so the handlers rebuild
   `ReceiptUnavailableException` with the same `getPrevious()` as today; Session answers with coded exceptions of its
   own carrying the same problem codes (`RECEIPT_NOT_READY`, `RECEIPT_UNAVAILABLE`), since it cannot import Evidence &
   Audit's. `DocumentBundler` takes the receipt entry as bytes beside its `ServableDocument` list. The bundle's call sits in Session's Application layer, not in
   `UI/Http`. `deptrac.yaml` does not change.
4. **ADR-0093** (`Proposed`), with its three `docs/adr/README.md` edits, amending ADR-0091 §3.3, ADR-0086 §7.5 and ADR-0088 §2.5.
5. **The signer handoff**, a new `docs/frontend-handoff/TASK-075-*.md`: when the card unlocks the files and the
   receipt, and when it offers each bundle.

Concepts re-cut: `ReceiptStandingReader` (no longer the only thing Session reads from Evidence & Audit; ADR-0091
§3.3, the `ReceiptStandingReader` docblock "never the receipt's content", ADR-0086 §2.6 and §7.5 and ADR-0088 §2.5 where they
say the receipt's bytes come only from Evidence & Audit's routes), "download all" (TASK-072 handoff §7's threshold).

## 4. Key decisions

1. **A parameter, not new routes.** Two more routes would duplicate the credential, the admission and the response
   of two routes the app already calls, and the app pins their operationIds.
2. **A receipt not yet issued refuses the bundle.** Leaving it out would make the archive's contents depend on the
   instant of the request, the partial bundle TASK-072 AC-8 / AC-9 refuse. The wait is seconds under
   `SEQUENTIAL_PADES`, and the reads' `receipt` already tells the app when to ask.
3. **`RECEIPT_UNAVAILABLE` refuses too**, with its own code, so the app can fall back to the bundle without the
   receipt; serving the documents without it under the parameter would hide a lost receipt.
4. **One rule for the receipt** (ADR-0091's A′ precedent): the bundle obtains the receipt through the same
   implementation the receipt routes call, so the two cannot drift.
5. **The unlock rule is the app's.** The reads already carry `signed_copy` and `receipt`; no new member.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | With `with_receipt=1`, each bundle route serves its documents plus the recipient's receipt as one more entry (members AC-1a…b) | owner | Acceptance | omit the receipt entry |
| AC-2 | Without the parameter, each bundle route's answer is unchanged: same entries, same bytes, same refusals (members AC-2a…b) | owner | Acceptance | add the receipt by default |
| AC-3 | With the parameter and the receipt `PENDING`: 409 `RECEIPT_NOT_READY` on each route, never a bundle without it (members AC-3a…b) | owner | Acceptance | skip the entry when pending |
| AC-4 | With the parameter and the receipt recorded but its bytes missing or substituted: 409 `RECEIPT_UNAVAILABLE` on each route (members AC-4a…d) | owner | Application + Acceptance | catch and leave it out |
| AC-5 | The handoff tells the card to unlock the files and the receipt together, once `signed_copy` is `CONTAINS_YOUR_SIGNATURE` or `FINAL` and `receipt` is `ISSUED` | owner | Handoff review | — |
| AC-6 | The handoff's exception: under `AWAITING_ENVELOPE` the receipt is shown as soon as it is `ISSUED`, and the files read as pending the other parties | owner | Handoff review | — |
| AC-7 | The handoff offers the bundle with the receipt from one document up, and keeps "two or more" for the bundle without it | owner | Handoff review | — |
| AC-8 | The receipt's part of the bundle answers as its receipt route does, over every refusal of the receipt route the bundle's own refusals do not answer first (members AC-8a…d) | derived — [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) §2 | Application + Acceptance | copy the rule into Session |
| AC-9 | The bundle readers' refusals come first; a refusal of the receipt builds no archive and leaves no temp file. A document custody that cannot be read is detected during the build, so it answers after the receipt's refusal | derived — `tests/F5Sign/Session/Integration/ZipDocumentArchiveTest.php` | Application + Integration | read the documents before the receipt |
| AC-10 | `with_receipt` is a closed set: absent, or `1`; any other value answers 400 on each route (members AC-10a…c) | derived — rule 5 | Unit | treat any value as true |
| AC-11 | A substituted receipt refused by a bundle route is logged at `error`, as the receipt routes log it | derived — `src/F5Sign/EvidenceAudit/UI/Http/DownloadSessionReceiptController.php` | Unit | drop the log line |
| AC-12 | The receipt's entry is named `justificante-<envelope>-<recipient>.pdf`, made unique against the documents' names, and holds the receipt route's bytes (members AC-12a…b) | derived — `src/F5Sign/Session/Application/Service/BundleEntryNames.php` | Unit + Acceptance | name it outside `BundleEntryNames` |
| AC-13 | A bundle never carries another recipient's receipt, of the same envelope or of another tenant's (members AC-13a…b) | derived — [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) §2.3 | Acceptance | read by envelope only |
| AC-14 | A decliner's bundle answers 404 with and without the parameter on both routes, and the copy receipt route still serves their receipt | derived — [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) §2.5 | Acceptance | serve a receipt-only bundle |
| AC-15 | While a bundle with the receipt is built, at most two documents' bytes are in memory besides the receipt's, which is read before the build (AC-9) | derived — `src/F5Sign/Session/Application/Service/DocumentBundler.php` | Application | read every entry up front |
| AC-16 | Both bundle routes document `with_receipt` and every code they emit in `#[OA\*]`, matching what is emitted; the operationIds do not change (members AC-16a…e) | derived — `tests/F5Sign/Acceptance/OpenApiSpecTest.php` | Unit + `OpenApiSpecTest` | leave `RECEIPT_NOT_READY` out |
| AC-17 | ADR-0093 lands as `Proposed` with its three `docs/adr/README.md` edits; `deptrac.yaml` is unchanged and Session reaches the receipt only through Evidence & Audit's `Contract/` | derived — rule 7 | arch (deptrac) + review | import `ReceiptBytes` from Session |
| S-1 | A `SEQUENTIAL_PADES` envelope with two documents: with the parameter, the bundle answers 409 `RECEIPT_NOT_READY` while `receipt` is `PENDING`, then 200 with three entries; the copy link's bundle reads the same. The fixture holds the receipt's issuance back (the `RECIPIENT_SIGNED` fact delivered to Envelope's reactor first, the receipt's reactor afterwards), since the two react to one fact independently. If the Acceptance harness cannot deliver the fact one reactor at a time under live DSS, the `PENDING` window stays pinned by AC-3 and AC-8d and S-1 asserts the end state (200, three entries) | derived — [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) §2.2 | Acceptance, live DSS | — |
| S-2 | A `SINGLE_SEAL` envelope with another party still to act: `signed_copy` is `AWAITING_ENVELOPE`, the bundle answers 404 with and without the parameter, and the receipt route answers 200 | derived — [ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md) §2.3 | Acceptance | — |

- **Gates:** suite, PHPStan, deptrac and lint under the `wt-backend` lane on this task's worktree.
  <!-- OFFREPO: the `wt-backend` lane is a target of `f5sign-infra`'s Makefile that mounts this worktree's own tree with its own Postgres, MinIO and RabbitMQ; restated here, nothing in this record depends on reading it. -->

**Notes on AC-1, AC-2 and AC-3**
- AC-1a / AC-1b — the signing route / the copy route: two documents ready and the receipt `ISSUED`: 200,
  `application/zip`, three entries.
- AC-2a / AC-2b — the signing route / the copy route: the same fixture without the parameter gives the two entries
  and bytes TASK-072 AC-8a / AC-9a pin; TASK-072's existing bundle tests stay green unchanged.
- AC-3a / AC-3b — the signing route / the copy route: the recipient acted, the documents are servable and no receipt
  is recorded.

**Notes on AC-4**
- AC-4a / AC-4b — the receipt's custody destroyed: the signing route, the copy route.
- AC-4c / AC-4d — the receipt's bytes replaced (digest mismatch): the signing route, the copy route.

**Notes on AC-8**
- Only the receipt can refuse in these members: the bundle's documents are servable in each. AC-8a no act yet,
  standing null (signing route: 404, though the documents alone would be served); AC-8b standing null on the copy
  route (404); AC-8c `ISSUED` (200, both routes); AC-8d `PENDING` (409, both routes, the Application half of AC-3).
- The receipt routes' refusals before the rule are answered first by the bundle's own readers, so they belong to
  AC-9: on the session route a retired credential, a document withheld and a step holding the recipient back
  (`SigningDocumentReader`); on the copy route the copy read admission, which `CopyDocumentReader` asks through the
  same `CopyAdmission` the copy receipt handler asks, so the two cannot disagree. Each test asserts the bundle's
  refusal and ⛔ checks **which** guard fired, not only the status (the repo's authoring rule 4, two guards in series).

**Notes on AC-10**
- AC-10a absent → the plain bundle. AC-10b `1` → with the receipt. AC-10c `0`, `true`, empty, an array → 400.

**Notes on AC-12**
- AC-12a — a document whose display name is `justificante-<envelope>-<recipient>`: two entries, the later one
  suffixed. AC-12b — the receipt entry's sha256 equals the receipt route's body.

**Notes on AC-16** (each member on both routes)
- AC-16a — the `with_receipt` query parameter, its one accepted value and that it is optional.
- AC-16b — 409 `RECEIPT_NOT_READY`. AC-16c — 409 `RECEIPT_UNAVAILABLE`. AC-16d — the 400 for an unaccepted value.
- AC-16e — the operationIds stay `get_signing.documents_zip` and `downloadCopyDocumentsBundle`.

**Notes on AC-13**
- AC-13a — two recipients of one envelope, both receipts issued: each bundle holds only its own. AC-13b — a
  tenant-B receipt row for the same ids never reaches a tenant-A credential.

## 6. Open follow-ups (track, don't solve here)

1. **A bound on the bundle** stays [BL-484](../BACKLOG.md); the receipt adds one bounded entry (a few pages) and
   does not change the answer. Forced by an envelope whose bundle a recipient cannot download, or by a memory or
   disk incident on the bundle routes.
2. **`no-store` on the session receipt route** stays [BL-472](../BACKLOG.md). Forced by a security review that
   finds a cached receipt, or by the next task that touches that route.
3. **`DocumentsBundleResponse` docblock lists the refusals as "404 or 409"** and the routes also answer 401 (the copy
   route, a refused access, a receipt `REFUSED`) and 400 (a bad `with_receipt`). Tracked as [BL-490](../BACKLOG.md).
   Forced by the next edit to that class or to a bundle route's refusals.

## 7. Deviations & honest notes

### Scope
- None beyond §3. Files touched are Evidence & Audit's contract port and its rule, the two receipt handlers, Session's
  bundle use and both bundle controllers, the tests, the signer handoff, the amended ADRs and the domain models.
- One file outside §3: `phpunit.dist.xml`, whose coverage exclusion of `*Bundle.php` hid `RecipientBundle` from Infection
  (see *Declared and unproven properties*). No class in `src/` is a Symfony bundle, so nothing else was excluded by it.

### Decisions made during implementation
- The rule sits in `EvidenceAudit/Application/Service/RecipientReceiptRule` and the port is `RecipientReceiptReader`
  (the record's working name), with the closed result types in `Contract/Type`. The two receipt handlers delegate to it
  and rebuild their exceptions, `ReceiptUnavailableException` keeping the same `getPrevious()` through the result's `cause()`.
- Session's `RecipientBundle` asks the receipt before any archive is built, so a receipt code comes before a lost
  document's. Only the copy route can hear `REFUSED` (401); the session route maps it, like `NONE`, to the 404.
- `WithReceipt` sits in `Session/UI/Http/`, not in `UI/Http/Request/` beside `AcceptLanguageHeader` (the plan's choice;
  closing review, confidence 40).
- Slice 01: the `sentAt === null` guard alone is held only by the census count, since the withholding check after it also
  refuses an unsent envelope, as in the existing handler test; the slice table expected a red in
  `an_unsent_envelope_answers_none`. The `config/services.yaml` comment and the rule docblock describe slices 02/03 as
  landed, which the closing review confirmed at the tip.
- Slice 05 added a test-side change (`562bb8df`) so the OpenAPI enum census names a parameter's enum without a mixed cast.
- Closing review: ADR-0091 §2.2 and §6 still described the handlers calling `receiptOrPending()` after their own
  refusals; fixed in `8cae0947`. Its low-confidence finding on the `DocumentsBundleResponse` docblock was left (see below).

### Decisions that needed an ADR
- [ADR-0093](../adr/ADR-0093-a-recipients-bundle-takes-their-receipt-from-the-receipt-routes-rule.md), drafted `Proposed`
  with this record, amending ADR-0091 §3.3, ADR-0086 §7.5 and ADR-0088 §2.5; accepted by the owner on 2026-10-28 once
  the §5 bars were green.

### Declared and unproven properties
- A `RECIPIENT_SIGNED` fact delivered to Envelope's reactor before the receipt's (the `PENDING` window under live DSS) is
  not reachable by the scenario harness: S-1 asserts the end state, and the window is pinned by AC-3 and AC-8d.
- Row locks and a second connection are not exercised; this task adds neither.
- **Infection** (diff-filtered on the 21 `src/` files the branch changes, bars covered-MSI 85 / MSI 70,
  `StorageLifecycleScenarioTest` excluded as in TASK-066, worktree lane). First run at `fa00ad6d`: covered-MSI 82.5 %,
  MSI 62.5 % (128 mutants, 17 escaped, 31 not covered). 22 of the not-covered were not a missing test:
  `phpunit.dist.xml` excluded every `src` file ending in `Bundle.php` from coverage, a Symfony skeleton leftover that
  matched only `RecipientBundle.php`; the exclusion is removed (slice 09, `eb17cd1d`), and tests now pin both Session
  receipt exceptions, `RecipientReceipt`'s refusal messages, `ReceiptUnavailableException::cause()` and the copy
  bundle's 404 (`8e350934`). Second run, same `src/` as `fa00ad6d`: **covered-MSI 98.44 %, MSI 98.44 %** (128 mutants,
  126 killed, 0 not covered). The changed-line verdict still exits 1 on two survivors, both accepted:
  - `GetSessionReceiptHandler.php:52` MatchArmRemoval of `REFUSED`: unreachable; `RecipientReceiptRule::forSession()`
    never answers `REFUSED`, and the handler depends on the concrete rule (plan decision).
  - `RecipientReceiptRule.php:63` ReturnRemoval of the `sentAt === null` answer: equivalent; the withholding check after
    it also answers `none()` for an unsent envelope (the slice 01 deviation above).

### Debt left behind, and where it lives now
- `DocumentsBundleResponse` docblock lists only 404 and 409 -> §6 item 3 and [BL-490](../BACKLOG.md). It predates this branch.
- The bundle's bound -> §6 item 1, [BL-484](../BACKLOG.md). `no-store` on the session receipt route -> §6 item 2, [BL-472](../BACKLOG.md).
- [BL-468](../BACKLOG.md) (the session receipt route's inline retirement comparison) was updated to name the rule's new home.

### Delegated work
- Eight slices in five waves: 01, 02, 03, 04, 07 critical on opus; 05, 06, 08 standard on sonnet (05 and 08 reviewed
  on opus, 06 on sonnet). Every slice report's `## Delegated` reads none: no shape reached three targets.
- Review rounds: 01, 03, 04, 06, 07 approved in round 0. Slices 02, 05 and 08 each had one fix round (a two-line
  docblock fix, the finding's sentence plus a pinning assertion, and text fixes), each checked by the orchestrator
  against the diff instead of a second review.
- Slice 04 was stalled mid-run by a Docker Desktop outage (the owner restarted it, roughly 09:29 to 09:57 UTC); the copy
  controller's tests had not been run when it stopped and were run on resume.
- Slice 07 reported two edits of about 20 s overlapping slices 05 and 06's runs.
- Slice 09 (Infection fix, critical on opus) was added after the first Infection run; one round, to cover the copy
  bundle's 404 that the exclusion had hidden.

### Cost of the run
- Not copied here: the orchestrator's Phase 7 table is not available to this closure; see `var/task-runner/TASK-075/run.log`
  for the per-slice models and rounds above.
