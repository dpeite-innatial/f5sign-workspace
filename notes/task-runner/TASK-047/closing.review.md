# Closing review: TASK-047, the per-recipient receipt

- **Range:** `af917e9d..HEAD`. That is `merge-base HEAD origin/develop`, which is develop's tip. Because the range starts there, the TASK-068 code that the `b8514b5f` merge brought in is outside it.
- **Size:** 136 files across 43 non-merge commits.
- **What I read:** plan.md (sweep terms, decisions, deviations), constraints.md (landed so far), every `slices/NN.review.md`, the record's §5, and the files of the critical slices wherever a claim depended on them.
- **No tests run**, as instructed.

## Verdict: changes

Four kinds of defect are open:
- one criterion that no test cites, which will block `task-validate-backend` (Step 4b);
- published `#[OA\*]` and nelmio strings that list which routes take the session credential, and are now incomplete;
- a route-file docblock that this branch edited, and whose adjacent claim is false;
- two header rows of the record that the develop merge made false.

None of these is a code defect. The code itself looks consistent across slices: the names, the refusal codes, the retry outlooks, the "has acted" key and the tenant scope all line up.

## Findings

### F1 (90, check 1): AC-15 is not cited by any test
- **Problem.** `rg '@criterion TASK-047[^\n]*\bAC-15\b' tests/` finds nothing. AC-15 has no sub-ids. task-validate-backend Step 4b fails a live id that no test cites.
- **What does hold it.** The property holds today through the unchanged goldens: no golden and no trail test changed in the range except the trail assertions of `ConserveTrailsCommandTest`. But nothing cites it.
- **Fix.** Add `@criterion TASK-047 AC-15` to the method docblock of these goldens tests. This is a docblock line only, so the test bodies and the goldens stay unchanged, as AC-15 requires.
  - `tests/F5Sign/EvidenceAudit/Unit/Domain/Trail/TrailJsonTest.php::the_trail_encodes_to_its_golden`, which pins the trail JSON byte for byte, at P-TRAIL-16.
  - The equivalent golden test in `tests/F5Sign/EvidenceAudit/Application/Service/TrailAssemblerTest.php`, if one exists.

### F2 (85, check 5, rule 1): published strings list the session-credential routes without the session receipt route
Each of these strings is emitted verbatim into the spec. The receipt route (`config/routes/api/evidence_audit.php`, `Authn::SESSION_CREDENTIAL`) is a route the credential admits, and since V-1 it also refuses a retired credential. None of these strings says so.

`rg SESSION_CREDENTIAL config/routes/` gives five routes: `session_read`, `document`, `commit`, `decline` and `download_session_receipt`.

| File | Current text | Gap |
|---|---|---|
| `src/F5Sign/Session/UI/Http/SubmitAuthResponseController.php:95` (`access_credential` property) | "on the read-model, document, commit and decline routes" | missing the receipt |
| `src/F5Sign/Session/UI/Http/StartSessionController.php:98` (`access_credential` property) | "on the read-model, document and commit routes" | missing the decline (already stale before this branch) and the receipt |
| `src/F5Sign/Envelope/UI/Http/ResetRecipientAccessCodeController.php:82` | "refused on the read-model, the document bytes and the commit" | the retirement now also refuses the receipt route (V-1), and the decline |
| `config/packages/nelmio_api_doc.yaml:33` (`info.description`) | "the read-model, the document bytes and the commit" | same |
| `config/packages/nelmio_api_doc.yaml`, `signingToken.description` (~l.1011) | same list | same |
| `config/packages/nelmio_api_doc.yaml`, `sessionCredential.description` (~l.1017) | same list | same |

**Fix.** In each string, name all five, for example "the read-model, the document bytes, the commit, the decline and your receipt (`GET /api/v1/signing/session/receipt`)". Alternatively, reword so the string stops enumerating, for example "every recipient route after the gate". Then run `nelmio:apidoc:dump` and `OpenApiSpecTest`.

### F3 (80, check 5, rule 1): the `src/F5Sign/Foundation/Actor/Authn.php` docblocks enumerate routes 6–8 only
- **Problem.**
  - `SIGNING_TOKEN` says "the read-model, the document bytes and the commit take SESSION_CREDENTIAL instead".
  - `SESSION_CREDENTIAL` says it admits "(ADR-0049 §2.3 routes 6-8, ADR-0050 §2.2)".
  - Both are closed lists. The decline and the session receipt are missing.
- **Fix.** Mirror `SessionCredentialListener`'s new wording: routes 6–8 first, then the decline and the session receipt (ADR-0086 §2.6), and "enumerate them with `rg SESSION_CREDENTIAL config/routes/`".

### F4 (80, check 5, rule 1): a prose block that this branch edited carries a false claim
- **Where.** `config/routes/api/signing.php`, file docblock, the "Recipient (token-scoped)" bullet.
- **Problem.**
  - This branch added the bullet "`GET /api/v1/signing/session/receipt` is declared in `evidence_audit.php`" to this block.
  - The bullet just above it still says these routes are "Public + bearer-token-authenticated — the SigningTokenListener derives tenant + envelope + recipient from the token".
  - That is false for four of the five routes it lists. Read, document, commit and decline are `Authn::SESSION_CREDENTIAL`, and `SessionCredentialListener` admits them.
  - Rule 1 asks for the whole edited block to be re-read.
- **Fix.** Reword the bullet:
  - The signing token admits only `POST /api/v1/signing/session` (open).
  - The read-model, the bytes, the commit and the decline take the session credential (`SessionCredentialListener` derives tenant, envelope and recipient from its claims).
  - `/renew` is `SESSION_RENEWAL`.
  - Keep the receipt bullet as it is.

### F5 (85, check 5, rule 1): the record's header rows say TASK-068 is not on develop
- **Where.** `docs/tasks/TASK-047-per-signer-evidence-document.md`.
- **Problem.**
  - The *Sibling* row says "TASK-068, on `fix/signed-copy-after-commit` and not yet on `develop`".
  - The *Decision record* row says "TASK-068 … also owes an ADR and has not minted it".
  - Both are false. `af917e9d` merged TASK-068 into develop, `b8514b5f` merged develop into this branch, and ADR-0090 is accepted (`75ad9863`).
  - The *Status* row still says **Not started**. That is task-close's to change, but it falls in the same edit.
- **Fix.**
  - *Sibling:* "TASK-068 (ADR-0090, accepted) is on develop and merged here at `b8514b5f`; …".
  - *Decision record:* drop the clause "whichever is drafted second re-runs the sweep", or put it in the past tense (ADR-0090 was minted after ADR-0086).
  - Status: leave it for task-close.

## Sweep (authoring rule 1): surfaces left for docs-sync and the root store

These are not in the fix loop. They are listed so that Phase 5 and the root `ai/` store commit take them.

### docs-sync (Phase 5)
- **`docs/LIVE_SCHEMA.md`:**
  - §evidence_audit, l.727: "One table: the registry of issued audit trails" should say two tables. Add an `issued_receipt` subsection: its columns, `issued_receipt_recipient_uniq`, `issued_receipt_custody_id_uniq`, `issued_receipt_conserved_pair_chk`, RLS FORCE plus `issued_receipt_tenant_isolation`, `issued_receipt_conserve_sweep_visible`, the trigger, and the grants to `f5sign_app`.
  - l.747: the function list needs `tenants_with_unconserved_receipts()`.
  - l.812: `read_settled_stream` is listed with one signature. Add `(uuid, text[], uuid, integer)` (`Version20261023095048`).
  - l.827: the `f5sign_evidence_audit_custodian` row says "column-scoped SELECT … on `issued_trail` … and nothing else anywhere". That is now false: the role also owns the receipts' funnel and holds `SELECT (tenant_id, conserved_at)` on `issued_receipt` (`Version20261023120139`).
- **`docs/ddd/evidence-audit-domain-model.md`:** there is no receipt anywhere. It needs the receipt model, the assembler and gatherer, the renderer, `IssueReceiptUseCase` with its three reactors, `IssuedReceipt` with its registry, the two routes, and the custodian job conserving receipts once `ENVELOPE_COMPLETED` is on the stream.
- **`docs/ddd/identity-access-domain-model.md:406`:** "the read-model, the document bytes and the commit are `Authn::SESSION_CREDENTIAL`" leaves out the decline and the session receipt.
- **`docs/ddd/signing-session-domain-model.md`:** the Session contract gains `SessionStatusReader`.
- **`docs/ARCHITECTURE.md`:** it says nothing of receipts. Check whether its Evidence & Audit row needs one.
- **BL-324 row (task-close):** extend it to the receipts' loop, which has the same untested per-tenant failure branch.
- **`.env*`:** no new variable. `evidence_audit.receipt_template` is a parameter.

### `CLAUDE.md` (a symlink into the root `ai/` store; it does not land with this branch)
1. **Session bullet:** "the read-model, the document bytes and the commit all require the session credential" should add "the decline and the session receipt (`GET /api/v1/signing/session/receipt`, declared in `config/routes/api/evidence_audit.php`)". Better still, point at `rg SESSION_CREDENTIAL config/routes/`, which the bullet already recommends.
2. **Current state, Evidence & Audit (first bullet and the Legal/E&A paragraph):**
   - Add:
     - the receipt model (`EvidenceAudit/Domain/Receipt`, `f5sign.receipt/1`);
     - `ReceiptSourcesGatherer` and `ReceiptAssembler` (`Application/Service`);
     - `TypstReceiptRenderer` behind `Application/Port/ReceiptRenderer` (`assets/evidence-audit/receipt.typ`);
     - `IssueReceiptUseCase` with the reactors on `RECIPIENT_SIGNED` (SEQUENTIAL_PADES), `SESSION_COMPLETED` (SINGLE_SEAL) and `SESSION_DECLINED`;
     - the two routes, `GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt` (MACHINE_KEY) and `GET /api/v1/signing/session/receipt` (SESSION_CREDENTIAL).
   - Replace "`evidence_audit.issued_trail`, the context's one table" with "one of its two tables, beside `evidence_audit.issued_receipt`".
   - Replace "The custodian keeps each issued trail as long as its envelope" with "… each issued trail, and each receipt once its envelope has ended, …".
3. **`Foundation/EventLog`:** "the tenant-scoped settled stream read, ADR-0071" could add "which may also stop at a type and a subject (ADR-0086 §2.1)".
4. **Session bullet, Evidence & Audit's dependency:** it now also reads `Session/Contract/Query/SessionStatusReader`.
5. **Stack, Typst line:** "renders the audit trail PDF" should read "renders the audit trail and receipt PDFs". The `templates/` paragraph ("The audit trail's Typst template and fonts") should also name `receipt.typ`.

## Criteria → tests (check 1)
Each live id has at least one citing method:

| Criterion | Citing tests |
|---|---|
| AC-1 | `IssueReceiptUseCaseTest` l.443, `OnRecipientSignedTest` l.41, `ReceiptAssemblerTest` l.374, `ReceiptLifecycleHttpTest` l.133 |
| AC-2a / AC-2b | `ReceiptAssemblerTest` l.430/431 |
| AC-2a | `IssueReceiptUseCaseTest` l.510 |
| AC-2c | `IssueReceiptUseCaseTest` l.494, `ReceiptEligibilityTest` l.71 |
| AC-3 | `ReceiptAssemblerTest` l.405, `ReceiptSourcesGathererTest` l.360, `ReceiptLifecycleHttpTest` l.134 |
| AC-4a | `ReceiptAssemblerTest` l.220/258, `ReceiptLifecycleHttpTest` l.230 |
| AC-4b | `ReceiptAssemblerTest` l.291, `OnSessionDeclinedTest` l.42 |
| AC-5 | `ReceiptJsonTest` l.151/335/360, `ReceiptAssemblerTest` l.168/193/219, `ReceiptSourcesGathererTest` l.308/334, `ReceiptCodesTest`, `TypstReceiptRendererTest` l.312 |
| AC-6a–e | `ReceiptAssemblerTest` (each member), `ReceiptSourcesGathererTest` l.252/274/309/447, `ReceiptTest` l.105, `ReceiptLifecycleHttpTest` l.263 |
| AC-7a–f | `RecipientReceiptHttpTest` (each member), `GetRecipientReceiptHandlerTest`, `DownloadRecipientReceiptControllerTest` |
| AC-8a–d | `SessionReceiptHttpTest` (each member), `GetSessionReceiptHandlerTest`, `DbalSessionStatusReaderTest` |
| AC-9a–d | `EventStreamSubjectBoundaryTest` (each member) |
| AC-9b/c | `ReceiptSourcesGathererTest` l.402/403 |
| AC-9d | `IssueReceiptUseCaseTest` l.536 |
| AC-10a | `IssueReceiptUseCaseTest` l.535, the three reactor tests |
| AC-10b | `ConcurrentReceiptClaimTest` l.101, `ConcurrentReceiptIssuanceTest` l.182 |
| AC-11 | `IssueReceiptUseCaseTest` l.558–716, `ReceiptSourcesGathererTest` l.384 |
| AC-12a/b | `ConserveTrailsCommandTest` l.212/236/264, plus the funnel and registry tests |
| AC-13 | `DbalIssuedReceiptRepositoryTest` l.97/119, `SessionCredentialTenantScopeTest` l.314 |
| AC-14a–e | `ReceiptEligibilityTest` |
| AC-14d | `IssueReceiptUseCaseTest` l.600 |
| AC-14f–h | `ReceiptTriggersCensusTest` |
| S-1a–c, S-2, S-3 | `ReceiptLifecycleHttpTest` |
| V-1 | `GetSessionReceiptHandlerTest` l.182/217/233 |
| V-2 | `TypstReceiptRendererTest` (13 methods), `ReceiptRendererWiringTest` |
| **AC-15** | **none (F1)** |

## Cross-slice consistency (check 3)
- **"Has acted":** `GetSessionReceiptHandler` keys the 409 on `SessionStatusReader::forRecipient()->isSomeAnd(closedByTheRecipientsOwnAct())`. Nothing on the receipt path reads `RecipientOutcome` for that. `ReceiptTriggersCensusTest` binds the census to the same predicate.
- **Refusal codes:** `RECEIPT_UNAVAILABLE` (both routes) and `RECEIPT_NOT_READY` (session route only) are in the `ProblemCode` enum of `nelmio_api_doc.yaml`. Each controller's 409 `#[OA]` names exactly the codes its handler can throw.
- **Retry outlooks:** the `IssueReceiptUseCase` maps are total over each failure family. `ReceiptNotIssued` exposes `emptyPdf`, `recipientNotOnEnvelope` and `because`. The tests pin each arm (slice 08, round 2).
- **Tenant scope:**
  - The machine route reads the registry under RLS only, and AC-13 is discriminating (200 first).
  - The session route is scoped by `SessionCredentialListener`'s GUC (`SessionCredentialTenantScopeTest`, receipt case).
  - The tenant label is asked for the tenant Envelope reads the envelope under.
  - The custodian funnel is pinned in the nil-UUID scope by `SentinelScopeRestoredTest`.
- **Names:** `IssuedReceiptId::fromEnvelopeAndRecipient` is used everywhere. The filename is `justificante-<env>-<recipient>.pdf` in the seal and in `ReceiptBytes`. The attachment is `justificante-….json`.
- **Wiring:** every `registers` entry is in `config/services.yaml`: the receipt-model exclude, `ReceiptContent` exclude, `TypstReceiptRenderer` with its port alias, the `ReceiptSourcesGatherer` `$appVersion`, `IssuedReceiptRepository`, `TenantsWithUnconservedReceipts` and `SessionStatusReader`. `IssueReceiptHandler` and the three reactor handlers are wired by attribute.

## Deferred to closing by the slices
- **02 (`Receipt` says its JSON is attached to the PDF):** resolved. `receipt.typ` runs `pdf.attach`, and V-2 pins byte equality.
- **03 (present tense about the session route):** now true. The missing `\ValueError` in the port's **Throws** is under Low confidence.
- **06 (`RendererUnavailable`, the `DECLARED_NONE` sentence):** under Low confidence.
- **08 (`ReceiptNotIssued` docblock: "a port returns as a value"):** under Low confidence.
- **12 / 07 (docs-sync surfaces):** listed above.
- **13 (`SessionCredentialListener` count):** resolved; it no longer counts. Its siblings did not follow (F2, F3).

## Low confidence
- **(60)** The `DECLARED_NONE` reservation in `receipt.typ` (l.281) reads "El destinatario declaró no formular reservas. Si firmó como destinatario en la entrega, …". In one sentence "destinatario" means both the envelope recipient and the goods' consignee. Suggest "como destinatario de la mercancía". The trail says "La parte" and has no such clash. Once issued, a sealed receipt cannot be reworded.
- **(50)** `ReceiptNotIssued`'s class docblock lists the cases it is thrown for and omits the thrown `EnvelopeNotFoundException`, which the use case wraps as SAME_RESULT. The trail sibling has the same gap.
- **(45)** `RendererUnavailable`'s docblock: "a fault of the deployment, not of the trail. The same trail renders once…". This now also serves the receipt; "document" would fix it.
- **(45)** The **Throws** of `Session\Contract\Query\SessionStatusReader` omits `\ValueError` from `SessionStatus::from()`. Its sibling `ActEvidenceReader` documents it.
- **(40)** The 409 `RECEIPT_NOT_READY` description says "It lifts by itself". If issuance refuses with SAME_RESULT or AFTER_A_FIX and the fact is parked, it stays 409 forever (for example `recipientNotOnEnvelope`, or `ActNotRecorded`). That is unreachable through today's reactors.
- **(40)** `CustodianSchedule`'s docblock: "the audit trails' conservation is hourly … bounds how long an issued trail stays transient". For receipts the hourly cadence bounds nothing; a receipt waits for the envelope's end. Incomplete rather than false.
- **(35)** Test docblocks that list the credential's routes as read/document/commit: `tests/F5Sign/Support/OpenedSigningSession.php`, `OpensSigningSessions.php`, `Session/Acceptance/LeakedLinkRefusedHttpTest.php:53`. `SessionCredentialTenantScopeTest` says "on every route the credential admits" and then excludes the decline (this predates the branch).
- **(30)** The Dockerfile's `typst` stage comments say "the Typst binary that renders the audit trail". That is outside the sweep set, and incomplete.
- **(30)** `config/packages/evidence_audit.yaml` header: "the build that a trail names" is trail-only. A receipt names the build too.

## Not checked
- No test or gate was run. I take the green on `2ae3ff08` from the orchestrator: a full-suite failure in the `DbalIssuedReceiptRepositoryTest` policy list, fixed there. That run is not re-confirmed for the tip.
- The frontend handoff for `GET /api/v1/signing/session/receipt`: none exists under `docs/frontend-handoff/`, and that is contract-check's call. The signer app is the consumer of this route.
- Infection on the diff, and `nelmio:apidoc:dump` output.
- `f5sign-infra` role scripts for `f5sign_evidence_audit_custodian`, which are outside this repo.
