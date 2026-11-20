# TASK-006 — DSS Stage-2: seal a real Envelope document (bytes through backend)

| Field | Value |
|-------|-------|
| **Status** | **Implemented 2026-06-18** — `make qa` green (PHPStan L9 · Deptrac **0**, 0 uncovered · lint · **163 tests**) incl. a live upload→seal round-trip vs MinIO + `eu-dss`. [ADR-0016](../adr/ADR-0016-storage-model.md) §5 flipped **open question → provisional v1**; the Foundation `ObjectStore` port + S3 adapter were born + exercised. Decisions + deviations in §7. |
| **Type** | **As-built record** — the Stage-2 unit [BL-2](../BACKLOG.md) anticipated ("future Stage-2 TASK … task not yet authored"). Documented after the build, not an as-planned spec; the body records what landed. |
| **Builds on** | [TASK-005](TASK-005-dss-pades-signing-slice.md) (Stage-1 — `DssClientInterface::seal()`, the live `eu-dss` server-signing path); [ADR-0016](../adr/ADR-0016-storage-model.md) (byte-path) + [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) (the storage port row); the `minio` + `eu-dss` services in the infra stack |
| **Delivery bar** | Green `make qa` **+** an integration test that uploads a real PDF's bytes *through* the backend (hashed inline → `originals`), seals the document via DSS, stores the signed output to the WORM `signed` zone, and asserts the **byte path** (artifact chain `originals`→`signed`, an embedded PAdES `ByteRange`, signed > source) — **not** trust-chain validity (the dev seal is self-signed; TASK-005 §7 holds). |
| **Auth** | **Header-stub** (inherited from TASK-004 / TASK-005). The seal is the *platform* identity, not a user cert. |
| **Naming** | Authored post-rename — `F5Sign\` throughout. |

---

## 1. Why this task exists

TASK-005 produced real PAdES-B-B cryptography but over a **fixture file → file**, with no persistence and no Envelope (`SealFixtureCommand` reads a path, writes a path). Stage-2 is the next slice TASK-005 deferred (its §3 / §10, tracked as [BL-2](../BACKLOG.md)): seal a **real Envelope document** — the original's bytes flow *through* the backend into object storage, the signed output is stored to a WORM zone, the signed artifact is recorded on the Envelope, and `DocumentSigned` is emitted.

It is the **realizability test for the storage model**: it converts [ADR-0016](../adr/ADR-0016-storage-model.md)'s byte-path from an open question into an exercised one and stands up the platform's first object-storage integration (`Foundation/Storage/`). It deliberately stays a sub-MVP path — synchronous, no presigned upload, no persisted `SignatureExecution` aggregate, no async.

## 2. What was built

**Storage foundation** (`Foundation/Storage/`):
- [`ObjectStore`](../../src/F5Sign/Foundation/Storage/ObjectStore.php) — the port (`put(zone, tenant, envelope, document, bytes, contentType): string` → opaque key; `get(key): string`); [`S3ObjectStore`](../../src/F5Sign/Foundation/Storage/S3ObjectStore.php) — the async-aws S3 adapter (zone→bucket + structured opaque key); [`StorageZone`](../../src/F5Sign/Foundation/Storage/StorageZone.php) (compliance zones) + [`StorageException`](../../src/F5Sign/Foundation/Storage/Exception/StorageException.php).
- Dependency `async-aws/s3` (+ `async-aws/core`); config [`storage.yaml`](../../config/packages/storage.yaml) + `S3_*` in `.env`/`.env.test` + DI in `services.yaml`; Deptrac `Vendor` layer gained `AsyncAws` so the Foundation→async-aws edge is covered.

**Upload — bytes-through-backend** (Envelope):
- [`UploadDocumentBytes`](../../src/F5Sign/Envelope/Application/Command/Authoring/UploadDocumentBytes.php) reshaped to carry **raw bytes** (was: pre-computed `hash`/`storageKey`/`sizeBytes`); the [use-case](../../src/F5Sign/Envelope/Application/UseCase/Authoring/UploadDocumentBytesUseCase.php) hashes inline → stores to `originals` → records the artifact.
- Multipart endpoint [`UploadDocumentContentController`](../../src/F5Sign/Envelope/UI/Http/UploadDocumentContentController.php) (`POST /api/v1/envelopes/{id}/documents/{documentId}/content`, field `file`, `204`) + a JSON [`AddDocumentController`](../../src/F5Sign/Envelope/UI/Http/AddDocumentController.php) (`POST …/documents`) + routes.

**Seal — real document** (SignatureExecution):
- [`SealDocument`](../../src/F5Sign/SignatureExecution/Application/Command/SealDocument.php) command + [`SealDocumentUseCase`](../../src/F5Sign/SignatureExecution/Application/UseCase/SealDocumentUseCase.php) + [`SealDocumentHandler`](../../src/F5Sign/SignatureExecution/Infrastructure/Messenger/Command/SealDocumentHandler.php): read the original from `originals` (via the cross-BC read below) → `DssClientInterface::seal()` → store signed bytes to `signed` → `appendDocumentArtifact(ProducedBy::seal)` → emit `DocumentSigned`. The real-bytes successor to `MockSignUseCase` (which stays — §7).

**Cross-BC read** (the seam TASK-005 didn't need):
- [`DocumentView`](../../src/F5Sign/Envelope/Contract/View/DocumentView.php) gained `originalStorageKey` (the first/lowest-`artifact_seq` artifact's opaque key), projected by a correlated subquery in [`DoctrineEnvelopeReadRepository`](../../src/F5Sign/Envelope/Infrastructure/Persistence/Doctrine/Read/DoctrineEnvelopeReadRepository.php). SE reads it through Envelope's exposed `getContextForSE` port — it never reaches into Envelope's data.

## 3. Scope

**In scope (built):** the bytes-through-backend synchronous byte-path; the Foundation `ObjectStore` port + S3 adapter (both deployment modes); the upload + seal verticals; the multipart upload HTTP endpoint; physical WORM via bucket-default Object-Lock; ADR-0016 §5 / §1 / Realized-in updates + ADR-0013/0022/0023 reconciliation.

**Out of scope (deferred — named so they're not silently dropped):**
- **Presigned-direct upload** + client-committed hash (the capacity / chain-of-custody dimensions of ADR-0016 §5).
- **Per-object retention / legal-hold** overrides (need the structured S3 client surface; WORM rides bucket-default retention for now).
- **The zone *class→profile* domain model** — an artifact carries no compliance-class attribute yet; the adapter maps zone→bucket (ADR-0016 #2).
- **A persisted `SignatureExecution` aggregate** + **`MockSignUseCase` retirement** (§7) — the seal is still a stateless use-case.
- **A console/HTTP seal *trigger*** — Stage-3 ([ADR-0023](../adr/ADR-0023-dss-server-signing-seal-flow.md) D5); the seal is dispatchable but driven by the integration test for now.
- **Async sealing** (Messenger) — the sync cut keeps [ADR-0015](../adr/ADR-0015-async-resilience.md) fully deferred.
- **Seal-vs-recipient-signature event semantics** (§7).

## 4. Key decisions

- **D1 — async-aws/s3 over Flysystem.** Both deployment modes are S3 (AWS / MinIO), so Flysystem's portability buys nothing while hiding the S3-native Object-Lock-retention + presigned surfaces the eventual targets need; the `ObjectStore` port is already our abstraction (ADR-0016 Counterpoint).
- **D2 — `ObjectStore` is a Foundation port.** Cross-BC capability (Envelope upload → `originals`; SE seal → `signed`), one async-aws adapter both modes, endpoint/creds/path-style differ by config only ([ADR-0013](../adr/ADR-0013-deployment-mode-duality.md)).
- **D3 — byte-path = bytes-through-backend, sync, inline hash (provisional v1).** Dissolves both gates the old open question raised: inline hash → no validation worker; sync seal → no async (ADR-0016 §5). Honest cost: the operator is in the original's pre-signature trust path (recorded in ADR-0016).
- **D4 — original location via the cross-BC read, not a smuggled command field.** SE asks Envelope `getContextForSE` for `DocumentView.originalStorageKey` (an opaque string — ACL-clean), rather than the seal command carrying a storage key nothing upstream actually holds.
- **D5 — WORM via bucket-default retention.** Infra provisions the WORM zones with a bucket-default COMPLIANCE retention, so a plain `put` inherits write-once immutability — the adapter sets no per-object retention header in v1.

## 5. Test plan & acceptance

- **[`S3ObjectStoreTest`](../../tests/F5Sign/Foundation/Integration/S3ObjectStoreTest.php)** (live MinIO): byte round-trip through `originals` (non-WORM) and `signed` (WORM, inherits bucket-default retention); opaque key encodes its zone for routing.
- **[`SealDocumentSliceTest`](../../tests/F5Sign/SignatureExecution/Integration/SealDocumentSliceTest.php)** (live MinIO + eu-dss): author a one-step/one-recipient envelope → upload a real PDF → send → `SealDocument`; assert the artifact chain (`originals` original + `signed` seal) and that the signed object is a real PAdES PDF (`%PDF`, `ByteRange`, larger than source).
- **Updated** for the reshaped `UploadDocumentBytes`: `EnvelopeVerticalSliceTest`, `DoctrineEnvelopeReadRepositoryTest`, `EnvelopeQueryAdapterTest`.
- **Acceptance met:** `make qa` green end-to-end (PHPStan L9 · Deptrac **0**, 0 uncovered · lint · **163 tests**); touched-file hygiene pass; ADR records updated (§ below).

## 6. ADR / doc reconciliation done here

- [ADR-0016](../adr/ADR-0016-storage-model.md): #5 open→**provisional v1** (bytes-through-backend + the chain-of-custody honesty + the two-dimensional deferral + the async-aws/port decision); physical WORM #1 now realized; Status → Partially Accepted; Realized-in / Enforced-by / Risks updated.
- [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md): storage matrix row → realized (one `S3ObjectStore` both modes); "Not realized" line corrected (storage + DSS ports done).
- [ADR-0022](../adr/ADR-0022-http-controller-conventions.md): the deferred multipart-upload request convention **landed** (binary body read off the `Request`, not `#[MapRequestPayload]`).
- [ADR-0023](../adr/ADR-0023-dss-server-signing-seal-flow.md): Decision 5's predicted Stage-2 `SealDocument` command **realized**; the ADR-0016 relationship row updated.
- [BL-2](../BACKLOG.md) discharged → this task; TASK-005 §3/§10 Stage-2 pointers reconciled.

## 7. Deviations & honest notes

- **`DocumentSigned` runs the completion chain synchronously.** `EventBus::dispatch` invokes subscribers inline, so the seal's `DocumentSigned` → Envelope's `OnDocumentSigned` → `RecordRecipientCompletion` all run inside the `SealDocument` command's call. The integration test therefore sets up a **real recipient + sent envelope** (not a no-recipient shortcut, which fails). This surfaced the broader **events + transactional-outbox** thread (see §8) — fine at this scale, a concern as cross-BC events multiply.
- **Operator in the original's pre-signature trust path** (v1; ADR-0016 #4 / chain-of-custody). WYSIWYS rests on operator honesty until the presigned-direct + client-hash path lands.
- **WORM accumulation in dev.** Tests write to the real `signed` bucket (5y COMPLIANCE) in the dev MinIO; objects accumulate until `make destroy` / `make minio-reset`. Acceptable (disposable dev volume); candidate refinement: a short-retention test bucket.
- **Seal vs recipient signature.** The platform seal records `ProducedBy::seal()` yet rides the existing `DocumentSigned` completion chain for the demo; refining that into a distinct sealing event is a later-stage concern (noted in `SealDocumentUseCase`).

## 8. Open follow-ups (track, don't solve here)

- **Events + transactional outbox + async relay** as cross-BC interactions grow — the synchronous in-process dispatch + the inspection-only `OutboxRecorder` won't scale (ordering, at-least-once, inter-BC failure isolation). Own design pass + likely an ADR; [ADR-0010](../adr/ADR-0010-command-bus-middleware-spine.md) (real outbox unwired) + [ADR-0015](../adr/ADR-0015-async-resilience.md) (async). **User-flagged 2026-06-18 for a dedicated discussion.** → **RESOLVED**: became the event-log substrate — the system-of-record `platform.event_log` + watermark relay ([ADR-0030](../adr/ADR-0030-record-first-event-floor.md)/[ADR-0031](../adr/ADR-0031-event-log-store.md)); the outbox, `OutboxRecorder`, and the inline `OnDocumentSigned` completion chain are gone.
- **`MockSignUseCase` retirement** — once the persisted `SignatureExecution` aggregate lands (the lifecycle path TASK-005 §10 named), the mock goes.
- **Presigned-direct + client-committed hash** (ADR-0016 §5 triggers: capacity, chain-of-custody).
- **Per-object retention / legal-hold** + the **zone class→profile** domain model + its class→profile mapping test (ADR-0016 #2 / Enforced-by candidates).
- **A console/HTTP seal trigger** (Stage-3; ADR-0023 D5) and **Stage-3** end-to-end through the team signer frontend.
- **[BL-4](../BACKLOG.md)** — the non-B-B guard in `seal()` still applies.
