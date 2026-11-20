# TASK-076 — Downloaded files are named by their envelope

| Field | Value |
|-------|-------|
| **Status** | **Done — integrated in `develop` on 2026-10-28** from `fix/download-names` (no-ff merge; `develop` had not moved since the branch was cut at `b7aae135`, so the merged tree is the validated one). Last full run at `e270cf34` under the `wt-backend` lane of this task's worktree: 9771 tests, 107616 assertions, lint, arch and PHPStan green, the BL-471 flake absent; after it only two docblocks changed (`405f5a4d`). Gates: task-validate pass, contract-check pass, security-audit warn (no `composer audit` output, no manifest change); doctrine-guard not run (no migration or persistence touched); perf-smoke skipped (no `perf:seed`). Infection: Infection on the changed lines of the 12 changed `src/` files (`wt-backend-infection`, lane of this worktree, run at `414120b1`): 10 mutants, all killed; covered-MSI 100 %, MSI 100 % (bars 85 / 70), no escaped, uncovered or timed-out mutant. Pending review. |
| **Type** | **Forward build**: a change to the names in the `Content-Disposition` of the bundle, audit-trail and receipt routes (the receipt's entry inside a recipient's bundle follows its route's name, as it already does), and to the JSON attachment embedded in the audit trail and the receipt. No migration, no new route, no new code path. |
| **Why** | The names of the files a client downloads carry Spanish prefixes (`documentos-`, `registro-`, `justificante-`) that read as noise to the integrator, which files them by envelope. The owner wants one rule: the envelope's id names what is the envelope's, and the recipient's id is added only where one envelope yields several files; the receipt carries the same name wherever it is served, inside a bundle too. |
| **Builds on** | [TASK-072](TASK-072-the-copy-card-reads-what-the-recipient-did.md) (the two bundle routes, `BundleEntryNames`), [TASK-075](TASK-075-a-recipients-bundle-can-carry-their-receipt.md) (the receipt as the bundle's last entry), [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) (the audit trail and its route), [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (the receipt and its routes), [ADR-0093](../adr/ADR-0093-a-recipients-bundle-takes-their-receipt-from-the-receipt-routes-rule.md) (the bundle takes the receipt through Evidence & Audit's contract). |
| **Scope** | Names only. ⛔ **Not** the document download routes' names (the sender's display name, unchanged), not the signer app's own file names (it names its downloads itself; see the OFFREPO note under the header), not `app:evidence-audit:render-trail`'s output files (`trail-<id>.*`, an operator tool's local directory, not a download), not any receipt or trail already sealed (their embedded attachment keeps the old name; sealed bytes are immutable). |
| **Decision record** | [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.10 states the trail is served *"as `registro-<envelope id>.pdf`"*; it gets a dated amendment in place (owner, 2026-10-28), since the name is a detail of the built route and not the decision the ADR records. No other ADR states a download name: ADR-0093 §2.1 leaves the receipt's filename to Evidence & Audit, and no ADR names the bundle's. A new ADR would be forced only if a name became part of a cross-context contract. |
| **Sibling** | None. |

<!-- OFFREPO: the signer app (`f5sign-signer`, local) downloads every file through a blob, because its credential
travels in a header, and names the file itself from its locale: the receipt `justificante.pdf`
(`status.receipt.fileName`), the bundle `copia.zip` (`copyCard.bundleFileName`; `copy.zip` in English), a
document its display name with `.pdf` added. So the routes' `Content-Disposition` reaches no signer, and the one
backend-chosen name a signer sees is the entry names inside the bundle. Restated here; nothing in this record
depends on reading the app. The integrator is the `factor5-dashboard` backend, which reads the routes'
`Content-Disposition`. -->

---

## 1. Why this task exists

Owner decisions, 2026-10-28:

- **The bundle**: Owner said: "para el zip diria que bastaría con el id del sobre, para los ficheros dentro del zip tal
  cual."
- **No prefixes**: Owner said: "Sí, yo quitaría los prefijos. En logalty lo que le llega al firmante es lo que paece
  el id del sobre.par.pdf".
  <!-- OFFREPO: the owner cites another signature provider, whose signer receives a file named after the envelope's
  id with a `.par.pdf` suffix, as the model for naming by id without a prefix. Restated here; nothing in this record
  depends on it. -->
- **The receipt keeps the recipient's id** on its routes, because the integrator downloads one receipt per recipient of
  one envelope (`GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt`) and `<envelope>.pdf` would make them
  collide with each other and with the trail. Owner said: "Sí, adelante con <sobre>.<destinatario>.pdf".
- **The trail**: `<envelope>.pdf` (owner's choice among the options offered).
- **The signer app keeps "justificante"**: Owner asked: "Y a nivel de ui del frontal de firma, no sería mejor mantener
  el \"justificante\"?" The app already names its own downloads (`justificante.pdf`, `copia.zip`; see the OFFREPO note
  above), so nothing changes there. The criteria were confirmed: "Sí, confirmo todo, y los JSON opción (a)".
- **The receipt inside the bundle follows the same rule**: Owner said: "Dentro del zip el justificate deberia seguir las
  mismas normas que fuera". Its entry is `<envelope>.<recipient>.pdf`, the name its route serves.
- **The embedded JSON** follows the PDF's name (option (a)).

## 2. What already exists (reuse, do not rebuild)

**The bundle's name.** `Session/UI/Http/DocumentsBundleResponse::of()` sets `Content-Disposition: attachment;
filename=documentos-<envelope id>.zip` (id lowercased) for both `GET /api/v1/signing/session/documents.zip` and
`GET /api/v1/copy/documents.zip`.

**The bundle's entries.** `Session/Application/Service/DocumentBundler::bundle()` names the documents and, under
`with_receipt=1`, the receipt through `BundleEntryNames::of()` (dedupe compared without case, ` (2)`, ` (3)`). The
receipt's entry takes `ServableReceipt::$filename`, which `Session/Application/Service/RecipientBundle` copies from
Evidence & Audit's `Contract/Type/RecipientReceipt` (the receipt routes' filename). The `#[OA\*]` descriptions of
`DownloadSigningDocumentsBundleController` and `DownloadCopyDocumentsBundleController` state the entry's name as
`justificante-<envelope id>-<recipient id>.pdf`.

**The receipt's name.** `EvidenceAudit/Application/Query/ReceiptBytes::read()` builds
`justificante-<envelope>-<recipient>.pdf` (both ids lowercased) at serve time, for the three receipt routes
(`DownloadRecipientReceiptController`, `DownloadSessionReceiptController`, `DownloadCopyReceiptController`, which pass
`ReceiptContent::$filename` to `HeaderUtils::makeDisposition` with no strip). `IssueReceiptUseCase` passes
`justificante-%s-%s.pdf` to `PdfSealer::seal()` as the document's name in the DSS request.

**The trail's name.** `EvidenceAudit/Application/Query/GetAuditTrailHandler` builds `registro-<envelope>.pdf`
(lowercased) for `DownloadAuditTrailController`; `IssueAuditTrailUseCase` and `RenderTrailCommand` pass
`registro-%s.pdf` to `PdfSealer::seal()`.

**The embedded JSON.** `assets/evidence-audit/trail.typ` attaches `registro-<envelope_id>.json` and its page text names
it; `assets/evidence-audit/receipt.typ` attaches `justificante-<envelope_id>-<recipient_id>.json` (`attachment-name`)
and its page text names it. `TypstTrailRendererTest` and `TypstReceiptRendererTest` assert the embedded names.

**The prose that names them.** ADR-0072 §2.10; `docs/ddd/signing-session-domain-model.md`; the handoffs
`docs/frontend-handoff/ADR-0072-audit-trail-download.md`, `TASK-047-integrator-recipient-receipt.md`,
`TASK-047-signer-receipt-download.md`, `TASK-070-signer-copy-screen.md`, `TASK-072-signer-copy-card-reads.md`,
`TASK-075-signer-bundle-with-receipt.md`; the class docblocks of `IssueReceiptUseCase`,
`DownloadRecipientReceiptController` and `DownloadAuditTrailController`. TASK-072's and TASK-075's records describe the
names as they were then and stay as history.

## 3. Scope

1. The bundle: `<envelope>.zip` on both bundle routes.
2. The trail: `<envelope>.pdf` on its route and as the sealed document's name.
3. The receipt: `<envelope>.<recipient>.pdf` on its three routes and as the sealed document's name.
4. The receipt's entry in a recipient's bundle: the name its route serves, `<envelope>.<recipient>.pdf`, which Session
   already takes from the contract's filename and `BundleEntryNames` makes unique against the documents' names. Session's
   code does not change; its `#[OA\*]` strings and tests do.
5. The embedded JSON: `<envelope>.json` in the trail, `<envelope>.<recipient>.json` in the receipt, and the page text
   that names it.
6. Every `#[OA\*]` string, docblock and doc that states one of the old names, ADR-0072 §2.10's dated amendment, and a
   handoff for the integrator and the signer.

Ids are lowercased everywhere a name carries one, including the names passed to the sealer, which today take the
ids as stored (`IssueReceiptUseCase`, `IssueAuditTrailUseCase`, `RenderTrailCommand`). The tests that pin an old name
(the receipt and trail handlers', controllers' and renderers' tests, `DocumentBundlerTest`, `RecipientBundleTest`,
`RecipientReceiptRuleTest`, `RecipientReceiptTest`) change with it.

Concepts re-cut: `documentos-`, `registro-`, `justificante-` (as file-name prefixes), `ReceiptBytes::read`,
`GetAuditTrailHandler`, `DocumentsBundleResponse::of`.

## 4. Key decisions

1. **A name with ids wherever the backend names a file the envelope yields.** The integrator keeps many envelopes'
   files side by side; the signer app chooses its own names for what it saves, so the only backend name a recipient
   sees is the receipt's entry in the bundle.
2. **One name per receipt.** The entry in the bundle repeats the route's name, as TASK-075 made it; the owner kept that
   rule rather than a human name for the entry.
3. **Names are computed when served**, so receipts and trails issued before this change are served under the new names
   with no migration. Only their embedded JSON keeps the old name, inside bytes that are sealed.
4. **The name passed to the sealer follows the download's.** DSS uses it only as the request's document name; aligning
   it keeps one name per artifact in the code.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | Each bundle route names its archive `<envelope>.zip`, with and without `with_receipt` (members AC-1a…b) | owner | Unit + Acceptance | keep the prefix |
| AC-2 | The audit-trail route names its PDF `<envelope>.pdf` | owner | Unit + Acceptance | keep the prefix |
| AC-3 | Each receipt route names its PDF `<envelope>.<recipient>.pdf` (members AC-3a…c) | owner | Application + Acceptance | separate the ids with `-` |
| AC-4 | A document's name, downloaded alone or as a bundle entry, is unchanged: its display name with `.pdf` added | owner | Acceptance (existing tests) | — |
| AC-5 | Every id in a name is lowercase, whatever the case of the id the name is built from (members AC-5a…c) | owner | Unit | drop the `strtolower` |
| AC-6 | The receipt's entry in a bundle is `<envelope>.<recipient>.pdf` on both bundle routes, the name its receipt route serves, and a document already named that pushes it to `<envelope>.<recipient> (2).pdf` (members AC-6a…c) | owner | Application + Acceptance | name the entry in Session |
| AC-7 | The receipt's entry holds the bytes its receipt route serves | derived — [ADR-0093](../adr/ADR-0093-a-recipients-bundle-takes-their-receipt-from-the-receipt-routes-rule.md) §2.1 | Acceptance (TASK-075's test, kept) | — |
| AC-8 | A receipt and a trail issued before this change are served under the new names | derived — `src/F5Sign/EvidenceAudit/Application/Query/ReceiptBytes.php` | Acceptance | store the name at issuance |
| AC-9 | The routes' header is exactly `attachment; filename=<name>`, with no `filename*` member (members AC-9a…c: bundle, trail, receipt) | derived — `src/F5Sign/EvidenceAudit/UI/Http/DownloadRecipientReceiptController.php` | Unit | — |
| AC-10 | The name passed to `PdfSealer::seal()` is the download's name, ids lowercased, for the issued receipt, the issued trail and the render command (members AC-10a…c) | derived — `src/F5Sign/EvidenceAudit/Application/UseCase/IssueReceiptUseCase.php` | Application + Integration | keep the old name |
| AC-11 | The trail embeds `<envelope>.json` and the receipt `<envelope>.<recipient>.json`, and each page's text names that file (members AC-11a…b) | owner | Integration (Typst renderer) | keep the old attachment name |
| AC-12 | No `#[OA\*]` string, docblock, config comment or doc outside another task's historical record names a download with the old prefixes | derived — rule 1 | sweep (`rg`) | — |
| AC-13 | ADR-0072 §2.10 carries a dated amendment naming `<envelope>.pdf` | derived — rule 7 | review | — |
| AC-14 | A handoff tells the integrator and the signer the new names; the six earlier handoffs that state an old name point to it | derived — `docs/frontend-handoff/TASK-047-integrator-recipient-receipt.md` | review | — |

- **Gates:** suite, PHPStan, deptrac and lint under the `wt-backend` lane on this task's worktree.
  <!-- OFFREPO: the `wt-backend` lane is a target of `f5sign-infra`'s Makefile that mounts this worktree's own tree with its own Postgres, MinIO and RabbitMQ; restated here, nothing in this record depends on reading it. -->

**Notes on AC-1, AC-3, AC-5, AC-6, AC-9, AC-10 and AC-11**
- AC-1a / AC-1b — the signing route / the copy route; each asserted with and without `with_receipt=1`.
- AC-3a / AC-3b / AC-3c — the integrator's route, the session route, the copy route.
- AC-5a / AC-5b / AC-5c — the bundle's name, the trail's, the receipt's.
- AC-6a / AC-6b — the signing bundle / the copy bundle with `with_receipt=1`: the last entry's name equals the
  `Content-Disposition` name of `GET /api/v1/signing/session/receipt` / `GET /api/v1/copy/receipt` for the same
  recipient, compared to the header rather than to a literal. AC-6c — a document whose display name is
  `<envelope>.<recipient>`: entries `<envelope>.<recipient>.pdf` (the document) and `<envelope>.<recipient> (2).pdf`
  (the receipt, last).
- AC-9a / AC-9b / AC-9c — the bundle routes, the trail route, the receipt routes.
- AC-10a / AC-10b / AC-10c — `IssueReceiptUseCase`, `IssueAuditTrailUseCase`, `RenderTrailCommand`.
- AC-11a / AC-11b — the trail / the receipt.

## 6. Open follow-ups (track, don't solve here)

- The signer app names its bundle `copia.zip`; whether it should follow `<envelope>.zip` is the signer's decision, in
  its own repo.
  Tracked as [BL-491](../BACKLOG.md).

## 7. Deviations & honest notes

### Scope
- None. The helpers `ReceiptFileName` and `TrailFileName` (`EvidenceAudit/Application/Service/`) are new classes the plan amend introduced, inside the task's names-only scope.

### Decisions made during implementation
- **One helper per artifact** (plan amend, owner-approved 2026-10-28): each name is built in one place, `ReceiptFileName::of()` / `TrailFileName::of()`, so the route, the sealer and the bundle cannot drift. They sit in `Application/Service/`, not `Contract/` (no other context needs them; Session takes the name from `RecipientReceipt`) and not `Domain/` (no naming sits there). The helpers' docblocks cite §4 of this record for the one-name rule.
- **AC-6c fixture is `e.r.pdf`**: the document readers (`SigningDocumentReader`, `CopyDocumentReader`) append `.pdf` to a display name before `BundleEntryNames` sees it, so the unit fixture hands the bundler `<envelope>.<recipient>.pdf`. The AC-6c note holds end to end; nothing to correct.
- **§3's claim that the trail's sealer took ids "as stored" was inaccurate**: `EnvelopeSummary` already lowercases. Harmless; the helper lowercases regardless.
- Slice 01's `ReceiptRoutesAnswerTheStandingTest` gained one `#[UsesClass(ReceiptFileName::class)]` outside the slice's file list (coverage metadata requires it). Slice 03's over-broad `@criterion AC-11a` and missing `strtolower` imports were fixed by the orchestrator (`2c5bccd2`, `f5750450`).

### Decisions that needed an ADR
- None. ADR-0072 §2.10 was amended in place (dated, owner, 2026-10-28; already Accepted). No ADR moves to Accepted from this task.

### Declared and unproven properties
- Infection: Infection on the changed lines of the 12 changed `src/` files (`wt-backend-infection`, lane of this worktree, run at `414120b1`): 10 mutants, all killed; covered-MSI 100 %, MSI 100 % (bars 85 / 70), no escaped, uncovered or timed-out mutant.
- The signer app's own file names are outside this repo's harness; the signer session confirmed nothing breaks on its side.

### Debt left behind, and where it lives now
- The signer's bundle name `copia.zip` → §6 above and [BL-491](../BACKLOG.md) (signer's decision, in its repo; the signer regenerates its OpenAPI snapshot after this merges).
- security-audit warned only for lack of `composer audit` output; nothing in the diff changes a manifest.

### Delegated work
- Five slices, all tier standard, no Delegated replication (every slice report: `Delegated: none`). Wave 1: slices 01 (`e026a6c0`), 02 (`cefc1f92`), 03 (`1e640eba`), each approved in 1 review round; slice 02 ended DONE_WITH_CONCERNS (lint red on slice 03 files, fixed by orchestrator; phpstan in a slice 01 file, sent to slice 01). Wave 2: slice 04 (`6612ca60`), 2 review rounds (F1 closed by an orchestrator sabotage run, 4 red for the right reason; F2 deferred to slice 05 by plan). Wave 3: slice 05 (docs, `e270cf34`), 1 round. Closing review (opus): approve, two low-confidence docblock items fixed in `405f5a4d`.

### Cost of the run
- Not recorded in the run workspace at close time; the orchestrator's Phase 7 table holds it.
