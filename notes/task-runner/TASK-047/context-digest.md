# Context digest — TASK-047

## Task summary
Each recipient who signs, approves or declines gets a sealed **receipt** ("justificante") of their own act: a
PDF/A-3a with its JSON attached, sealed through `PdfSealer`, stating that one recipient's act, the sending
organisation's name, and nothing about the other participants (the sender person included). It is issued by the fact that makes it true (`RECIPIENT_SIGNED` under `SEQUENTIAL_PADES`,
`SESSION_COMPLETED` under `SINGLE_SEAL`, `SESSION_DECLINED` in either mode), registered once per (envelope,
recipient), conserved only once the envelope has ended, and served by two routes: the integrator's machine route and
the recipient's session route. Decision record: ADR-0086 (`Proposed`; accepted by the owner at close).

## What will be implemented
- Foundation: `EventStreamReader::readSettledToSubject()` + overload `platform.read_settled_stream(uuid, text[],
  uuid, integer)` (new migration): stop at the lowest row of a type **and** a subject.
- Session: `Contract/Query/SessionStatusReader::forRecipient(EnvelopeRef, RecipientRef): Option<SessionStatus>` +
  `DbalSessionStatusReader`.
- Evidence & Audit Domain: `Domain/Receipt/*` model and `ReceiptJson` (`f5sign.receipt/1`, closed key set);
  `Domain/ValueObject/ReceiptBoundaryFact`; `IssuedReceipt` aggregate, `IssuedReceiptId` (v5 of envelope:recipient),
  `AuditedRecipientRef`, `IssuedReceiptRepository`; `TenantsWithUnconservedReceipts`.
- Evidence & Audit Application: `ReceiptTrigger`, `ActStream`, `ReceiptSources(+Document/Revision)`,
  `ReceiptSourcesGatherer`, `ReceiptAssembler`, `ReceiptEligibility`, `ReceiptRenderer` port, `IssueReceipt` +
  `IssueReceiptUseCase`, reactors `OnRecipientSigned`/`OnSessionCompleted`/`OnSessionDeclined`, queries
  `GetRecipientReceipt`, `GetSessionReceipt`, `ReceiptBytes`, exceptions (`ReceiptSourcesRefusal` family,
  `ReceiptNotIssued`, `ReceiptClaimedElsewhere`, `ReceiptUnavailableException`, `ReceiptNotReadyException`).
- Infrastructure: `TypstReceiptRenderer` + `assets/evidence-audit/receipt.typ`, `DbalIssuedReceiptRepository`,
  `DbalTenantsWithUnconservedReceipts`, Messenger handlers, `ConserveTrailsCommand` extended to receipts.
- UI: `DownloadRecipientReceiptController`, `DownloadSessionReceiptController`; routes in `evidence_audit.php`.
- Visibility only: shared readings of `TrailAssembler` and encoders of `TrailJson` become `public static`.

## Business rules applied
- Who: `SIGNER` and `APPROVER` only (exhaustive `ReceiptEligibility::receives(Role)`); decliners are signers or
  approvers (`mayDecline` also names `CERTIFIED_DELIVERY`, refused at send).
- When: `RECIPIENT_SIGNED` ⇔ SEQUENTIAL_PADES; `SESSION_COMPLETED` ⇔ SINGLE_SEAL; `SESSION_DECLINED` ⇔ either. A fact
  that does not issue returns quietly.
- Content: envelope id, title (from `ENVELOPE_CREATED`), mode, `closed_before` (first close fact in the prefix);
  recipient id/step/role/name, authentication, observed IP/UA/Accept-Language (only for an act made by the recipient),
  delegated assertion or browser report; act kind/fact/reason/reservation; per assigned document the original digest
  and, for a SEQUENTIAL_PADES signature on a signing assignment, the revision their execution appended (bytes check,
  certificate read back); boundary (type, position, subject, instant); `sha256-chain/1` over the prefix; limitation
  codes (`NO_PER_RECIPIENT_SIGNATURE`, `APPROVAL_SIGNS_NO_DOCUMENT`, `DECLINE_SIGNS_NO_DOCUMENT`,
  `SHARED_PLATFORM_CERTIFICATE`, `STATES_THE_ACT_ONLY`, `PLATFORM_CLOCK_TIMES`); generation.
- Retention: transient custody; conserved to the envelope's ceiling only after `ENVELOPE_COMPLETED` is on the stream.
- Session route: 404 for no act, a retired credential, or a recipient a closed envelope withholds; 409
  `RECEIPT_NOT_READY` when the session is `COMPLETED`/`DECLINED` and no receipt yet.

## Data model touched
- New table `evidence_audit.issued_receipt` (id PK derived; tenant_id; envelope_id; recipient_id; custody_id;
  boundary_type; boundary_position; issued_at; conserved_until/at with pair check; unique (envelope_id,
  recipient_id) and (custody_id); RLS enabled+forced, `issued_receipt_tenant_isolation`, tenant-stamp trigger;
  `f5sign_app`: SELECT, INSERT, UPDATE(conserve columns)).
- Custodian: column grant (tenant_id, conserved_at), policy `issued_receipt_conserve_sweep_visible`, function
  `evidence_audit.tenants_with_unconserved_receipts()`.
- New overload `platform.read_settled_stream(uuid, text[], uuid, integer)` (owner `f5sign_log_reader`).
- No change to `issued_trail`, the event log table, or any event payload.

## Contracts affected
- HTTP (new): `GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt` (`MACHINE_KEY`; 200/304/400/401/404/409
  `RECEIPT_UNAVAILABLE`/500) and `GET /api/v1/signing/session/receipt` (`SESSION_CREDENTIAL`; 200/304/400/401/404/409
  `RECEIPT_NOT_READY` | `RECEIPT_UNAVAILABLE`/500). Frontend handoff needed for the signer (contract-check decides).
- Events: none added or changed; three new consumers of `RECIPIENT_SIGNED`, `SESSION_COMPLETED`, `SESSION_DECLINED`.
- Published format: `f5sign.receipt/1` (new).
- Contract ports: `EventStreamReader` (Foundation, new method), `SessionStatusReader` (Session, new).

## Invariants preserved
- The audit trail is byte-identical: model, JSON goldens (`tests/Fixtures/audit-trail/`), template, renderer.
- ADR-0071: tenant-scoped definer read, wait on the stream lock, refusals as rows, READ COMMITTED.
- ADR-0076: no transaction open at any outbound call; the claim commits with the bytes; a lost claim withdraws.
- ADR-0002: reactors dispatch only. Deptrac unchanged: E&A Application → Session/SE/Envelope/Storage contracts.
- LOAD-BEARING §1.19/§1.20: `VOLATILE`, `pg_temp` last, no PUBLIC execute on every new definer function.

## Decisions made and why
See `plan.md § Decisions made`: `closed_before` instead of "open" (an agreed close has no fact); "its seal read back"
read as ADR-0072 §2.7; the sending organisation's provisioned label stated (through `TenantNames`, as the trail), the sender person never (owner, 2026-10-23); `closed_before` owner-confirmed; shared readings made public; renderer reuses `TypstCommand`;
`Option<SessionStatus>`; session-route guards from ADR-0060/ADR-0073; AC-10b split by harness; a separate receipts
funnel; waiting is not a failure.

## Binding ADRs
ADR-0086 (governing, Proposed), ADR-0071, ADR-0072 (§2.6, §2.7, §2.10), ADR-0073 (§2.2, §2.15, §2.16), ADR-0076,
ADR-0061 §2.7, ADR-0060 §2.3, ADR-0050, ADR-0002, ADR-0018 (DBAL only).

## Left out
- Delivery by email/SMS and the link/credential behind it (TASK-047 §6 #1; BL-280, BL-188).
- The trail citing receipts (§6 #2). A backstop sweep for parked issuances.
- TASK-068's session-read 409s (`SEAL_PENDING`, `signed_copy`), not on this branch.
- The second `RECIPIENT_SIGNED` an approver's redelivery can append (BL-463): not fixed, only shown harmless.
