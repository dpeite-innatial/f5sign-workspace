# Plan — TASK-047

Record: `docs/tasks/TASK-047-per-signer-evidence-document.md` (working tree, with the claims-check fixes).
Decision record: ADR-0086 (`Proposed`), which covers every cross-cutting change below; no new ADR is needed.

## Criteria → slices
| Criterion | Slices | Harness |
|---|---|---|
| AC-1 | 05, 08, 09, 14 | Application (assembler, use case, reactor) + Acceptance live DSS |
| AC-2 (a, b, c) | 05 (a, b), 08 (a, c), 09 | Application |
| AC-3 | 04, 05, 14 | Application + Acceptance |
| AC-4 (a, b) | 05 (a, b), 09 (b: the reactor), 14 (a) | Application + Acceptance |
| AC-5 | 02 (closed key set: `tenant_label` in, no sender key), 04 (own evidence only; tenant name for the view's tenant), 05 (two recipients; the sender's reference and void reason absent), 06 (tenant printed, document author) | Unit + Application + Integration (Typst) |
| AC-6 (a–e) | 04 (d, e), 05 (a–e), 02 (e) | Unit + Application |
| AC-7 (a–f) | 11 | Unit + Application + Acceptance |
| AC-8 (a–d) | 03 (status read), 13, 14 (S-2) | Integration + Application + Acceptance |
| AC-9 (a–d) | 01 (a–d), 08 (d: issuance writes nothing new) | Integration (real log) + Application |
| AC-10 (a, b) | 08 (a), 09 (a: equal commands), 07 (b: claim on two connections), 10 (b: through the use case) | Application + Integration |
| AC-11 | 04 (read-back kept as `Err`), 08 (refusal outlooks) | Application |
| AC-12 (a, b) | 12 | Integration |
| AC-13 | 07 (RLS), 11 (machine 404 for another tenant) | Integration + Acceptance |
| AC-14 (a–h) | 08 (a–e: roles), 09 (f–h: outcomes, statuses, handlers) | Unit (census) |
| AC-15 | 02, 05, 06 (trail tests unchanged, goldens byte-equal) | Unit + EvidenceAudit suite |
| S-1 (a–c) | 14 | Acceptance, live DSS |
| S-2 | 14 | Acceptance |
| S-3 | 14 | Acceptance |
| V-1 (plan-local) — the session route answers 404 to a retired credential (ADR-0060 §2.3) and to a recipient a closed envelope withholds (ADR-0073 §2.15) | 13 | Application |
| V-2 (plan-local) — the receipt renders PDF/A-3a with its JSON attached byte for byte, deterministically, every code labelled | 06 | Integration (real Typst) |

## Harness per property
| Property | Tier | Does the harness reach it? |
|---|---|---|
| The subject boundary stops at the right row; a repeat does not move it | Integration, real log, `SkipDatabaseRollback` | Yes: real `platform.read_settled_stream` overload; DAMA bypassed |
| The read waits for an open writer below the subject boundary | Integration, two sessions | Yes: separate sessions as `EventStreamSettledReadTest` |
| No other participant's value reaches the receipt | Unit (closed key set) + Application (two recipients, all values differ) | Yes: a fixture whose two recipients disagree on every value |
| The sending organisation is stated; the sender person is not | Unit (key set) + Application (sender uuid and void reason unique in the fixture, searched in the encoded JSON) | Yes; name/email of the sender are in no source the gatherer reads (the log holds an actor reference only, and no user-reading port is injected), so the reference is what can leak and is what is searched |
| The revision is the recipient's own, not the tip | Application (fake chain with a later signer) + Acceptance (live chain) | Yes; the fake returns what it is given, the real chain is S-1 |
| Mode check before issuance | Application | Yes: counts seals/custodies |
| Idempotency on redelivery | Application (in-memory registry) | Yes for the existence check; the SQL claim is Integration |
| Concurrent claim waits and converges | Integration, two connections, `lock_timeout` | Yes (slice 07); DAMA's one connection could not |
| Loser's custody withdrawn through the use case | Integration, real registry + store, interleaved in the seal | Yes: the use case holds no transaction there (ADR-0076 §2.6) |
| RLS on `issued_receipt` | Integration, catalog + second tenant scope | Yes |
| Conservation waits for `ENVELOPE_COMPLETED` | Integration, `appendFact` on the test's own connection | Yes: the settled read does not wait on the caller's own append |
| Receipt route 409 between commit and signature | Acceptance, real commit, no relay pump | Yes: the window is real; Envelope's outcome is still `PENDING` |
| Reactors fire on the real delivery | Acceptance, `pumpEventLogRelay` (`async_events` is `in-memory://`) | Partly: no redelivery transport; redelivery is pinned at Application (equal commands, registry check) |
| Typst output | Integration, real binary | Yes |
| Census of roles / outcomes / handlers | Unit | Yes: fails naming an unclassified member |
| Infection | `src/F5Sign` only | Covers the new src; the PHPStan/SQL guards are reached only by their Integration tests |

## Slices
| # | Title | Tier | Covers | Depends on | Wave |
|---|---|---|---|---|---|
| 01 | The settled read can stop at the first row of a type and a subject | critical | AC-9 | — | 1 |
| 02 | The receipt is a model of its own, with a closed published JSON | critical | AC-5, AC-6e, AC-15 | — | 1 |
| 03 | Session answers one recipient's session status through its contract | critical | AC-8 (support) | — | 3 |
| 04 | A receipt's sources are gathered up to the recipient's act, and only theirs | critical | AC-6d, AC-6c, AC-5, AC-11 | 01, 02 | 2 |
| 05 | The receipt is assembled from its sources, for its recipient only | critical | AC-2a/b, AC-3, AC-4, AC-5, AC-6, AC-15 | 02, 04 | 3 |
| 06 | The receipt renders as PDF/A-3a with its JSON attached | critical | V-2, AC-15 | 02 | 4 |
| 07 | One receipt row per (envelope, recipient), tenant-isolated, claimed once | critical | AC-13, AC-10b | 02 | 2 |
| 08 | One recipient's receipt is issued once, when its fact makes it true | critical | AC-1, AC-2a/c, AC-9d, AC-10a, AC-11, AC-14a–e | 04, 05, 06, 07 | 5 |
| 09 | Three reactors issue a receipt on the fact that ends the act | critical | AC-1, AC-2, AC-4b, AC-14f–h | 08 | 6 |
| 10 | Two issuances of one receipt leave one row and one custody | critical | AC-10b | 08 | 6 |
| 11 | The integrator downloads a recipient's receipt | critical | AC-7, AC-13 | 07 | 6 |
| 12 | A receipt is kept as long as its envelope, once it has ended | critical | AC-12 | 07 | 7 |
| 13 | A recipient downloads their own receipt with their session credential | critical | AC-8, V-1 | 03, 07, 11 | 7 |
| 14 | Real flows issue each acting recipient's receipt, both routes serve it | critical | S-1, S-2, S-3, AC-1, AC-3, AC-4a | 09, 11, 13 | 8 |
| 15 | The records name what this task built | standard | AC-15 (records) | 01–14 | 9 |

Wave note: `config/services.yaml` is touched by 02, 03, 06, 07, 08, 11 and 12, so no two of them share a wave;
that, not the dependencies, is why 03 waits for wave 3 and 06 for wave 4. Files are otherwise disjoint per wave
(01 and 04 both touch `TrailPortsFake`, in different waves).

## Sweep terms
- `per-signer evidence document` / `per-recipient evidence document` → `receipt` (record's re-cut).
- `EventStreamReader::readSettled` — gains a subject-qualified sibling, `readSettledToSubject`; prose that says the
  read stops "at the first row of a type" as the only form (ADR-0071 §2.3, LOAD-BEARING §1.19, ADR-0072 §2.9's
  "position boundary").
- `platform.read_settled_stream` — now two signatures.
- BL-280 (*"blocked on the audit trail"*, *"not on develop"*, *"emailed together with the signed document"*).
- `ConserveTrailsCommand` / `app:evidence-audit:conserve-trails` — now also conserves receipts ("trails only" prose:
  the command's docblock, `CustodianSchedule`, `docs/ddd/`, `CLAUDE.md` "Current state").
- `RemovesIssuedTrails` — now also removes receipt rows.
- `TrailJson` / `TrailAssembler` helpers made public — "private" claims about them.
- `SessionCredentialListener` docblock enumerates the session-credential routes ("the read-model, the document bytes
  and the commit"): a closed enumeration this task extends again (the decline already escaped it).
- `signing.php` docblock lists the recipient routes: the receipt route lives in `evidence_audit.php`.
- The losing reading "the receipt states no tenant name" / "no organisation": any prose that says the receipt names
  no tenant is now wrong; prose that says it names no sender is right.
- Losing alternatives: "carry the log position on the relayed message" (ADR-0086 §7.1), "filter the trail"
  (§7.2), "issue at the commit" (§7.3), "conserve at issuance" (§7.4), "serve from Session" (§7.5).
- 02: `TrailJson::statement|optionalText|text|time|digest|certificate|authentication|browserReport` private→public; `TrailJson::reservation`, `TrailJson::assertedIdentity` extracted (new).
- 07: `IssuedReceiptId::forRecipient` → `IssuedReceiptId::fromEnvelopeAndRecipient` (PHPStan factoryNaming).
- 07: `evidence_audit.issued_trail` "the context's one table" / LIVE_SCHEMA "One table" — now two tables.
- 05: `TrailAssembler::authentication|browserReport|observed|assertion|reservation|certificate|present|fact` private → public static, bodies unchanged.
- 06: `GenerationMismatch::__construct`, `TrailNotEncodable::__construct` gain optional `$document = 'trail'`; failure-family, `RendererIdentity`, `TypstCommand` docblocks widened to trail + receipt.
- 06: `receipt.typ` says "destinatario", never the trail's "la parte".
- 12: `ConserveTrailsCommand` / `app:evidence-audit:conserve-trails` now also conserves receipts (description, --dry-run help, verdict strings, docblock).
- 13: `SessionCredentialListener` docblock no longer counts the credential's routes; points at `rg SESSION_CREDENTIAL config/routes/`. `SessionCredentialTenantScopeTest` docblock names the receipt route.

## Decisions made
- **Envelope state at the act is `closed_before`** (owner-confirmed 2026-10-23), the first `ENVELOPE_VOIDED`, `ENVELOPE_CLOSED_BY_SENDER` or
  `ENVELOPE_COMPLETED` in the prefix, or none. An agreement's own close records no fact (ADR-0073 §2.2:
  `Envelope::close()` records nothing for a non-sender agreed close, and `EnvelopeAgreed` is "securing, not
  closing"), so "open at the boundary" cannot be derived from the log for the act that closes an envelope in
  agreement; the receipt states what the log records and the template words "none" as "the log records no close up
  to this act". AC-6a/AC-4a are met in that form (a voiding decline names `ENVELOPE_VOIDED`).
- **"Its seal read back"** (AC-11, ADR-0086 §2.3) is read as ADR-0072 §2.7 reads seals: the signatures of the
  documents the receipt states (the recipient's revision), not the receipt's own seal, which the trail never reads
  back either. A read-back the signing engine did not answer is a `MAY_SUCCEED` refusal.
- **The receipt states the sending organisation, not the sender person** (owner, 2026-10-23, reversing the first
  plan's "no tenant name"): the organisation is not a participant and the recipient already sees it in the
  invitation and the ceremony. It is the trail's `tenant_label` — the provisioned label, read through
  `IdentityAccess\Contract\Query\TenantNames`, which `AuditTrailSources` already injects (no new cross-BC
  dependency, no deptrac change) — asked for the tenant Envelope reads the envelope under; `Unstated(SOURCE_UNAVAILABLE)`
  when none; also the PDF's author, as `trail.typ` sets it. The sender person (their actor reference, name, email,
  and a sender's void reason) is another party's personal data and stays out: no key, no port. Neither the record
  nor ADR-0086 says "no tenant name" (the strict reading was the planner's), so neither needs an edit. Amended slices
  02, 04, 05, 06, plus the 200 `#[OA\*]` strings of 11 and 13 (published: they now say the receipt names the
  organisation and not the sender); ids, tiers and waves unchanged.
- **Shared readings, not copies:** `TrailAssembler`'s and `TrailJson`'s readings/encoders of shared values become
  `public static` with unchanged bodies, so both documents minimise and spell a value alike; the trail's goldens pin
  that nothing moved (AC-15).
- **Receipt renderer reuses `TypstCommand` and `TrailRenderFailure`** unchanged (the job's file names and the run's
  failures are document-agnostic); `TypstReceiptRenderer` copies `TypstTrailRenderer`'s process handling rather than
  refactoring it, because the record keeps the trail renderer unchanged.
- **`SessionStatusReader` returns `Option<SessionStatus>`**: the absence is the one refusal (unknown envelope, other
  tenant, no session read alike), as its two siblings state.
- **Session route guards**, applying accepted ADRs to a new credential route: a retired credential (ADR-0060 §2.3,
  `agp` < `credentialsRetiredAt`) and a recipient the closed envelope withholds (ADR-0073 §2.15, "every read") get the
  route's 404. This is what makes ADR-0086 §2.6's "a decliner whose decline closes the envelope … only the machine
  route reaches their receipt" true for a still-valid JWT. Pinned as V-1.
- **AC-10b is split by where each property lives**: the claim's wait on two live connections (slice 07, as
  `ConcurrentTrailClaimTest`) and the loser's custody withdrawal through the use case, interleaved inside the seal
  where no transaction is open (slice 10).
- **Receipts in the job are their own loop and funnel** (`tenants_with_unconserved_receipts()`), not a widened
  trail funnel: the custodian's column grant and policy are per table, and widening one is a security change.
- **Conservation waiting is not a failure**: a receipt of an envelope not ended (or a stream still written) is left
  transient and counted as waiting, so an open envelope never colours the custodian's exit code.
- **Who gets a receipt is checked twice by design**: the mode × fact rule and the role rule in the use case
  (`ReceiptEligibility`, exhaustive), and the census of handlers/outcomes/statuses in tests.

## Risks carried into the run
- Wiring the reactors (slice 09) makes ~26 Integration/Acceptance files issue receipts during their relay pumps
  (Typst + a DSS seal per acting recipient): slower, and any of them that pumps a hand-built stream may now throw.
  Slice 09 runs them and stops on a red rather than adapting those tests.
- A receipt refusal on `SESSION_COMPLETED` re-runs every handler of that delivery, including Signature Execution's,
  which can append a second `RECIPIENT_SIGNED` for an approver (BL-463); AC-9d pins that the boundary does not move.

## Deviations
- 02: `ReceiptBoundary::$eventType` typed `string` (as `ReceiptFact::$eventType`); slice 08 may retype it to `ReceiptBoundaryFact`.
- 02: signer fixture's `closed_before` (pos 7) follows the act (pos 6): an encoder shape, not a log sequence (reviewer: harmless).
- 02: no reflection census over the receipt model (unlike `TrailJsonCompletenessTest`); a new property is caught only via the literal key list.
- 02: `Receipt` docblock says the JSON is attached to the PDF; true once slice 06 lands — closing review to confirm.
- 01: the slice's first sabotage (subject filter on the FIRST min()) turns AC-9b red, not AC-9a; a sabotage on the second min() was added and turns AC-9a red.
- 01: `EventStreamReadAccessTest`'s lock-key source check covers only the 3-arg overload; the 4-arg one is held by AC-9c's behaviour.
- 01: round 1 fixed `Version20260922000002`'s docblock ("the only read"), docblock only, repo rule 2.
- 04: empty custody bytes = no bytes (as `AuditTrailSources::bytes()`); a document missing from the view is named by its id; evidence looked up by exact key on the trigger's recipient id (reviewer approved all three).
- 04: "one document's bytes held at a time" holds by structure only; no memory test for the receipt.
- 04: round 1 fixed three docblocks: the no-other-participant guarantee is the Receipt model's, not the sources'; `ReceiptEnvelopeUnreadable` = no envelope with its id.
- 07: code written before tests; reds seen only via sabotage (reviewer: process deviation, guards proven).
- 07: edited `EntityIdFormatGuardTest` outside Files (census requires it); integration tests use `PinsTheDatabaseClock`.
- 07 → docs-sync (Phase 5): `docs/LIVE_SCHEMA.md` §evidence_audit "One table" + issued_receipt subsection + f5sign_app grants.
- 07 → at landing, in the root ai/ store (CLAUDE.md is a symlink): Evidence & Audit bullet "the context's one table" → one of two, beside issued_receipt.
- 07 → slice 12: `SchemaConformanceTest` will need an entry for the custodian's policy on issued_receipt.
- 05: a document's name is `Stated(name, ROW)` even on the id fallback; the fallback is unreachable today (names never change, documents are never removed). If it ever fires, fix is slice 04's `ReceiptDocumentSource::$name` → `Option<string>` stated `Unstated(SOURCE_UNAVAILABLE)`.
- 05: envelope id taken from the boundary row's stream id (reviewer: correct).
- 05: round 1 pinned four branches that `mapOr`'s eager default hid from coverage (no revision source, no bytes, differing bytes, no signature at the revision's length).
- 03: other-tenant guard is the session table's RLS policy (published migration), tested by `another_tenants_session_reads_as_none` under f5sign_app, not sabotaged.
- 03 → closing: `SessionStatusReader` Throws omits `\ValueError` from `SessionStatus::from()` (sibling `ActEvidenceReader` documents it); its docblock and the services.yaml comment speak of the session route in the present tense — true once slice 13 lands.
- 06: Files widened in round 1 for the failure family's message and docblocks (TypstCommand docblock only).
- 06 → closing: `RendererUnavailable` docblock still speaks only of the trail (incomplete, not false); `DECLARED_NONE` Ley 15/2009 sentence uses "destinatario" for both the envelope recipient and the consignee (ambiguity).
- 06: config/packages/evidence_audit.yaml header now names both renderers.
- 08: `ReceiptNotIssued::recipientNotOnEnvelope()` added (SAME_RESULT, no previous; reviewer: keep).
- 08: envelope context read before the mode/role checks, so a fact that issues nothing costs one Envelope read.
- 08: rounds 1–2 pinned every refusal's retry outlook and the no-seal assertion for every pre-seal refusal.
- 08 → closing: `ReceiptNotIssued` docblock says refusals "a port returns as a value" but `EnvelopeNotFoundException` is thrown (trail has the same gap).
- 10: the slice's sabotage (claim not written) reds before the custody assertions; a third sabotage (lost claim answered Ok) pins the loser's withdrawal; setUp/tearDown delete the fixed receipt id via the owner connection (cross-run residue under RLS).
- 09: Files amended for `ReactorConvergenceTest` (reflective census of every Reactor needs a fixture per reactor).
- 09: `StorageLifecycleScenarioTest` expectations predate receipts (5 custodies → 7; day-3/day-31 footprint needs receipt conservation) — routed to slice 12 with 09's uncommitted helper edit.
- 09: `OnSessionCompleted` docblock states BL-463 and that a receipt refusal redelivers `SESSION_COMPLETED` even when no receipt is due (registry check + envelope read precede `issuesOn`).
- 11: Files amended for `config/packages/nelmio_api_doc.yaml` (`RECEIPT_UNAVAILABLE` in ProblemCode; `OpenApiSpecTest` requires it); slice 13 pre-amended for `RECEIPT_NOT_READY`.
- 11: acceptance issuedAt uses the current time (no fixed literal, no ALLOWED row).
- 11: round 1 made the other-recipient and other-tenant 404s discriminating (200 first), each sabotaged red (id from envelope alone; find() pinned to tenant A).
- 11 → docs-sync: CLAUDE.md Current state does not mention receipts.
- 12 → docs-sync: `docs/LIVE_SCHEMA.md` custodian role row ("and nothing else anywhere") + funnel entry for `tenants_with_unconserved_receipts()`; `docs/ddd/evidence-audit-domain-model.md` and the repo guide's Evidence & Audit paragraph describe the custodian job as trails-only.
- 12: BL-324's untested per-tenant failure branch now also covers the receipts' loop (task-close: extend BL-324's row).
- 12: funnel's WHERE restates the policy predicate (defence in depth, as the trails'); the policy is pinned by `SchemaConformanceTest`.
- 12: Files amended for `StorageLifecycleScenarioTest` (with 09's edit) and `SentinelScopeRestoredTest` FUNNELS; three trail verdict assertions re-worded (reviewer: not weakened); round 3 pinned the StreamNotSettled → waiting branch.
- 13: census classification ruled by orchestrator: unsent CLASSIFIED (explicit check, defence in depth beside `withholdsDocumentFromRecipient()`), closed REFUSES, step REFUSES (`stepHoldsTheRecipientBack()`).
- 13: `GetSessionReceipt::$issuedBy` is `SystemActorId::recipient()` (slice said `ActorId`, which cannot name a recipient).
- 13: Files widened: `SigningReadersRefuseUnsentEnvelopeTest`, `ReceiptUnavailableException` docblock, `SessionCredentialListener` docblock, `RouteAuthnDeclarationTest`, `SessionCredentialTenantScopeTest`.
- 13: the handler does not ask `recipientCouldPassTheGate()` (sibling reader does) — consistent with ADR-0086's decliner whose decline leaves the envelope open.
- 14: S-1's roster cannot reach the gatherer's execution-id guard (B cannot sign before A's receipt is gathered); a fourth test (two signers on one step, one pump) pins it on real DSS bytes.
- 14: S-2 runs under SINGLE_SEAL, so its AC-8b citation cannot catch the SEQUENTIAL_PADES sabotage; `SessionReceiptHttpTest` covers the right mode.
- merge: develop (TASK-068 / ADR-0090) merged at b8514b5f before slice 14.
- 15: ADR-0072 §2.9 reworded "a projection of this trail" → "made from this log" (out of slice; reviewer: true). TASK-047 BL-462 hit notes TASK-068 closed its signer-facing half. Round 1 corrected eight §5 descriptions and the ADR index row.
- 16: closing sweep (F1–F5 + six leads + codec/claims lists + RECEIPT_NOT_READY detail). Kept: the machine route's 404 description "issued shortly after the act is recorded" mirrors the trail sibling's wording for normal timing (ADR-0086 §3.3 names the parked case). `92309746`'s message omits the record-header edits it carries.
- doctrine-guard: no tenant_id-leading index on issued_receipt — mirrors issued_trail, small table keyed by unique pairs; accepted, no change.
- security-audit (warn, 0 blocking): (1) composer audit not run (no composer change); (2) no nosniff on the two PDF routes — repo-wide gap, same as the trail route; (3) receipt PII in clear — ADR-0033 not enforced, same posture as the trail; (4) GetSessionReceiptHandler repeats `RecipientAuthContext::retires`'s comparison inline — forced: that type is Session/Application, which EvidenceAudit may not depend on (deptrac); the comment names the source, V-1 pins the boundary; (5) retired/closed 404s tested at handler level, not over HTTP. Task-close: record 2–5 as follow-ups where no BL row already covers them.
- contract-check (fail → docs-sync): frontend handoffs owed — signer (session receipt route, 409 RECEIPT_NOT_READY / RECEIPT_UNAVAILABLE, 404s, PDF + ETag/304) and integrator (machine route, the two new ProblemCodes).
- 17: Infection fix — 47 new test cases (each mutant hand-applied red); 600/44/76 → 651/29/40 on changed lines. Equivalents/unreachable recorded in slices/17.report.md. `IssuedReceiptId::generate()` kept (mirrors `IssuedTrailId::generate()`). OA attribute arguments pinned by `OpenApiSpecTest` marked `@infection-ignore-all` per the TASK-068 precedent (`DeclineSignatureController`).
- 17 → follow-up: StartSessionController:93 `session_id` schema property is pinned by no spec test (pre-existing; not this task's route).
