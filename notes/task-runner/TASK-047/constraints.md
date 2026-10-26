# Constraints — TASK-047 (each recipient who acts receives a sealed receipt of their own act)

Every slice of this task reads this file. Short on purpose.

## Where you work

- Branch: `feat/per-recipient-receipt`. Worktree (absolute):
  `/var/www/html/factor5_others/f5sign/f5sign-backend-per-recipient-receipt` (call it `<wt>` below).
- It is a **worktree**: the normal infra targets validate the main checkout, not yours. Use the lane only.
  The lane is already up (kept by the orchestrator); never bring it up or down.
  - One test or class: `make -C /var/www/html/factor5_others/f5sign/f5sign-infra wt-backend-test src=<wt> only='<regex>'`
    — add `fast=1` for Unit/ and Application/ runs (hermetic, no queue).
  - Before each commit: `WT_GATES="lint arch phpstan test" WT_TIERS=fast make -C /var/www/html/factor5_others/f5sign/f5sign-infra wt-backend src=<wt> | tail -40`.
  - Console in the worktree: `make -C /var/www/html/factor5_others/f5sign/f5sign-infra wt-backend-sf src=<wt> cmd="<command>"`.
  - New migration: `… wt-backend-sf src=<wt> cmd="doctrine:migrations:generate"`. ⛔ Never name a migration by hand.
- ⛔ Do not stage `docs/tasks/TASK-047-per-signer-evidence-document.md`, `docs/adr/ADR-0086-*.md` or
  `docs/BACKLOG.md`: they carry uncommitted edits owned by the orchestrator. `git add` named files only.
- TASK-068 (`fix/signed-copy-after-commit`) is on develop and merged into this branch at `b8514b5f` (ADR-0090: `signed_copy`, `SEAL_PENDING`). The receipt routes do not refuse in its name.

## Binding decisions

- ADR-0086 §2.1 — the settled read may stop at a list of types **and** a subject: the lowest position whose
  type is in the list and whose `subject_id` is the subject; same wait, tenant policy, refusals and definer
  family; a new migration, never an edit of `Version20260922000002`. **This is the governing decision for the
  one Foundation change of this task (slice 01): it is not a new decision, do not stop for it.**
- ADR-0086 §2.2 — triggers: `RECIPIENT_SIGNED` (SEQUENTIAL_PADES sign/approve), `SESSION_COMPLETED`
  (SINGLE_SEAL only; the mode check sits in the use case), `SESSION_DECLINED` (decline, either mode). The
  boundary is the triggering fact: its type and its subject.
- ADR-0086 §2.3 — the receipt is its own model (`f5sign.receipt/1`), closed key set, **no other participant's
  data**; envelope state derived from the stream prefix; revision picked by the recipient's execution id, never
  the chain's tip; rendered by the pinned Typst behind a port of its own; sealed through `PdfSealer`.
  `TrailRenderer` and `TypstTrailRenderer` stay unchanged.
- Owner, 2026-10-23 — the receipt **states the sending organisation** (the tenant's provisioned label, read through
  `IdentityAccess\Contract\Query\TenantNames`, the port the trail already uses) and **never the sender person**
  (their actor reference, name, email or a sender's void reason). Its envelope state is `closed_before` (the first
  close fact in the prefix, or none, worded "the log records no close up to this act").
- ADR-0086 §2.4 — `evidence_audit.issued_receipt`, one row per (envelope, recipient), id derived from both,
  RLS enabled + forced; claim `INSERT … ON CONFLICT (id) DO NOTHING` inside `CustodyStore::writeAlongside()`.
- ADR-0086 §2.5 — a receipt's custody opens transient and is conserved only once `ENVELOPE_COMPLETED` is on
  its envelope's stream, read through `EndedStream`.
- ADR-0086 §2.6 — two routes: machine `GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt`
  (`MACHINE_KEY`) and `GET /api/v1/signing/session/receipt` (`SESSION_CREDENTIAL`, controller in
  `EvidenceAudit/UI/Http`); 409 `RECEIPT_NOT_READY` keyed on the session's own status (`COMPLETED`/`DECLINED`).
- ADR-0071 §2.2–§2.4 — the read runs through a `SECURITY DEFINER` function owned by `f5sign_log_reader`;
  refusals are rows, not errors; `READ COMMITTED` only.
- ADR-0072 §2.6/§2.7/§2.10 — minimisation of personal values, read-back from bytes, registry + custody shape.
- ADR-0076 §2.2/§2.6 — no transaction open at any outbound call; the claim commits with the bytes.
- ADR-0060 §2.3 — every route admitting a session credential refuses one whose `agp` is earlier than the
  recipient's `credentialsRetiredAt`. ADR-0073 §2.15 — a closed envelope withholds every read from a
  recipient who neither signed nor is informational.
- ADR-0002 — reactors dispatch only; they read nothing.
- LOAD-BEARING §1.19 (the settled read waits on the stream lock; `VOLATILE`), §1.20 (`pg_temp` last in every
  definer `search_path`; `REVOKE EXECUTE … FROM PUBLIC`).

## Non-negotiable rules (implement-backend Step 4, as they apply here)

- Between BCs only `Contract/` is visible. Evidence & Audit Application may use Envelope, Session,
  SignatureExecution, Storage, IdentityAccess contracts; its UI only its own Application. **Never edit
  `deptrac.yaml`, `phpstan.dist.neon` or `phpstan-baseline.neon`** — if a gate asks for it, `BLOCKED`.
- Domain imports no Symfony/Doctrine; DBAL only (no ORM rationale in prose); queries are called directly
  (no query bus); commands go through the command bus.
- A schema change is a generated migration; never edit a published migration's SQL.
- Every new test: `#[CoversClass]`/`#[CoversNothing]`, `#[UsesClass]` for collaborators and asserted
  exceptions, `@criterion TASK-047 <id>` in the method docblock.
- Prose: write only the slice's *Prose to write* or what you verified this session. No AI marks, English only.
- `#[OA\*]` strings come only from the slice.

## Out (TASK-047 §3)

- Delivery of the receipt by email or SMS; any link or credential minted for it (§6 #1, BL-188, BL-280).
- A decliner's in-session download beyond what the session route serves (§4 #4).
- The envelope trail: its model, JSON, template, renderer and goldens do not change (AC-15). Visibility
  changes on `TrailAssembler`/`TrailJson` helpers are allowed only where a slice names them, bodies unchanged.
- The trail citing receipts (§6 #2). The backstop sweep. TASK-068's session-read 409s.

## Landed so far
- `Receipt` (`SCHEMA = 'f5sign.receipt/1'`, `of()`) — src/F5Sign/EvidenceAudit/Domain/Receipt/Receipt.php — the receipt's one value; folds `Chain::over` over the facts at or before the boundary position only.
- `ReceiptJson` — src/F5Sign/EvidenceAudit/Domain/Receipt/ReceiptJson.php — the published closed key set (171 paths pinned in `ReceiptJsonTest`), includes `envelope.tenant_label`, no sender key.
- `ReceiptBoundaryFact` — src/F5Sign/EvidenceAudit/Domain/ValueObject/ReceiptBoundaryFact.php — the three trigger types.
- `TrailJson` shared encoders now public static, bodies unchanged — src/F5Sign/EvidenceAudit/Domain/Trail/TrailJson.php.
- `EventStreamReader::readSettledToSubject()` — src/F5Sign/Foundation/EventLog/EventStreamReader.php — settled read up to the lowest position whose type is in the list AND whose subject_id is the one named; same refusals as `readSettled` (`StreamNotSettled`, `NoBoundaryInStream`).
- `platform.read_settled_stream(uuid, text[], uuid, integer)` — migrations/Version20261023095048.php — the 4-arg overload behind it.
- `ReceiptSourcesGatherer::gather()` — src/F5Sign/EvidenceAudit/Application/Service/ReceiptSourcesGatherer.php — gathers one receipt's sources: the stream up to the trigger's type+subject, the recipient's revision by execution id (never the tip) read back from that artifact's bytes, only this recipient's evidence, the tenant label for the envelope view's tenant; refusals as `ReceiptSourcesRefusal` (`ActNotSettledYet`, `ReceiptEnvelopeUnreadable`, …).
- `ReceiptSources`, `ActStream`, `ReceiptTrigger` — src/F5Sign/EvidenceAudit/Application/Service/ — the gathered inputs; the stream still holds others' facts, the Receipt model keeps them out.
- `IssuedReceiptId::fromEnvelopeAndRecipient(AuditedEnvelopeRef, AuditedRecipientRef)` — src/F5Sign/EvidenceAudit/Contract/Type/IssuedReceiptId.php — v5 of envelope:recipient; the only id an `IssuedReceipt` accepts.
- `IssuedReceipt` — src/F5Sign/EvidenceAudit/Domain/Aggregate/IssuedReceipt.php — one row per (envelope, recipient); `issue()` refuses a non-derived id; `recordConserved()` once.
- `IssuedReceiptRepository` (`find`, `exists`, `issueIfAbsent` ON CONFLICT DO NOTHING, `save`, `unconserved`) — src/F5Sign/EvidenceAudit/Domain/Repository/ + Infrastructure/Persistence/DbalIssuedReceiptRepository.php.
- `evidence_audit.issued_receipt` — migrations/Version20261023100913.php — RLS enabled+forced, tenant policy, tenant-stamp trigger, f5sign_app SELECT/INSERT + UPDATE(conserved_until, conserved_at).
- `ReceiptAssembler::assemble()` — src/F5Sign/EvidenceAudit/Application/Service/ReceiptAssembler.php — one recipient's `Receipt` from `ReceiptSources`: envelope id from the stream, tenant label (never the sender), their own act/evidence/revision, `closed_before`, exhaustive limitation match; reuses `TrailAssembler`'s public static readings.
- `SessionStatusReader::forRecipient(EnvelopeRef, RecipientRef): Option<SessionStatus>` — src/F5Sign/Session/Contract/Query/SessionStatusReader.php — one recipient's session status on an envelope under the caller's tenant; `None` for no session / unknown envelope / other tenant alike. Adapter `DbalSessionStatusReader` (public alias).
- `ReceiptRenderer` (port) / `TypstReceiptRenderer` — src/F5Sign/EvidenceAudit/Application/Port/ReceiptRenderer.php, Infrastructure/Render/TypstReceiptRenderer.php — renders a `Receipt` as PDF/A-3a with its JSON attached byte for byte, author = tenant label, through `assets/evidence-audit/receipt.typ`; refusals are the trail's `TrailRenderFailure` family (messages name 'receipt').
- `IssueReceipt` (command: envelopeId, recipientId, fact, subjectId) / `IssueReceiptUseCase` / `IssueReceiptHandler` (command.bus) — src/F5Sign/EvidenceAudit/Application/… — issues one recipient's receipt once: registry check, envelope context, `ReceiptEligibility::issuesOn(fact, mode)` + `receives(role)` return early, gather, assemble, render, seal (`justificante-<env>-<recipient>.pdf`), transient custody, claim inside `writeAlongside`; a lost claim ends quietly; refusals are `ReceiptNotIssued` with a retry outlook.
- `ReceiptEligibility` — src/F5Sign/EvidenceAudit/Application/Service/ReceiptEligibility.php — static, exhaustive over `Role` and fact × `SigningMode`.
- EvidenceAudit `OnRecipientSigned` / `OnSessionCompleted` / `OnSessionDeclined` reactors + `…Handler` (event.bus) — src/F5Sign/EvidenceAudit/Application/Subscriber/, Infrastructure/Messenger/Subscriber/ — each dispatches one `IssueReceipt` from the fact's envelope, recipient, type and `subject()`; read nothing.
- `GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt` (`MACHINE_KEY`) — `DownloadRecipientReceiptController`, `GetRecipientReceipt(Handler)`, `ReceiptBytes`, `ReceiptContent`, `ReceiptUnavailableException` (409 `RECEIPT_UNAVAILABLE`) — src/F5Sign/EvidenceAudit/… — 200 PDF + strong ETag, 304, one 404 for no row / other recipient / other tenant; substitution logged at error. `ReceiptBytes` is the reusable read for slice 13.
- `app:evidence-audit:conserve-trails` receipts loop — src/F5Sign/EvidenceAudit/Infrastructure/Console/ConserveTrailsCommand.php — conserves a receipt to the envelope's ceiling only once `ENVELOPE_COMPLETED` is on its stream (`EndedStream::TERMINAL_TYPES`); not ended / still written = waiting, never a failure. Funnel `evidence_audit.tenants_with_unconserved_receipts()` + custodian column grant + `issued_receipt_conserve_sweep_visible` policy (Version20261023120139).
- `GET /api/v1/signing/session/receipt` (`SESSION_CREDENTIAL`) — `DownloadSessionReceiptController`, `GetSessionReceipt(Handler)`, `ReceiptNotReadyException` (409 `RECEIPT_NOT_READY`) — src/F5Sign/EvidenceAudit/… — the credential's own recipient only (no recipient id taken); 409 while the session is COMPLETED/DECLINED and no receipt is recorded; one 404 for no act, unsent, retired credential, withheld recipient, unreached step.
