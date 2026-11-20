# TASK-005 — DSS PAdES-B-B signing slice (first real cryptography)

| Field | Value |
|-------|-------|
| **Status** | **Implemented 2026-06-15** — `make qa` green (PHPStan L9 · Deptrac 0 · lint · 157 tests) incl. a live seal vs `eu-dss`. [ADR-0012](../adr/ADR-0012-dss-integration-boundary.md) → **Accepted**; [ADR-0023](../adr/ADR-0023-dss-server-signing-seal-flow.md) born **Accepted**. Deviations + corrections in §11. |
| **Type** | Agent-delegable implementation task (births SE's real signing path + realizes ADR-0012) |
| **Builds on** | [TASK-004](TASK-004-envelope-http-exposure.md) (HTTP edge, header-stub auth, error boundary); the found `feat/T04.2.1` DSS port+adapter (sibling worktree `f5sign-backend-dss/`); the `eu-dss` service already in the infra stack |
| **Delivery bar** | Green `make qa` via the infra Makefile **+** an integration test that produces a real PAdES-B-B signature over a fixture PDF against the live `eu-dss` server-signing keystore, asserting **cryptographic-structural** success (a signature is embedded; the byte-range digest matches) — **not** trust-chain validity (the dev seal is self-signed; see §7). |
| **Auth decision** | **Header-stub** (inherited from TASK-004). No real principal; the seal is a *platform* identity, not a user cert. |
| **Naming** | Code predates the brand rename; the f5sign rename — namespace → `F5Sign\`, brand prose, internal identifiers, and the infra-coupled DB roles / rabbitmq / keystore alias (`f5sign-dev-seal`) — was **applied 2026-06-18**. |

---

## 1. Why this task exists

The backend can author and expose an Envelope over HTTP (TASK-004) but **performs no cryptography** — Signature Execution holds only [`MockSignUseCase`](../../src/F5Sign/SignatureExecution/Application/UseCase/MockSignUseCase.php), which emits `DocumentSigned` with a random hash and a `mock://` storage key. Nothing real is signed.

This task builds the first slice that **performs real PAdES cryptography over a PDF**: Signature Execution seals a fixture PDF at level **PAdES-BASELINE-B** via the EU DSS **server-signing keystore**, producing a genuinely signed PDF. It is the *realizability test* for the single-signature-factory design — it converts [ADR-0012](../adr/ADR-0012-dss-integration-boundary.md) from an asserted boundary into an exercised one, and it stands up the first real piece of SE's Domain (today empty but for cross-BC `Contract/` types and the mock).

It is deliberately a **sub-MVP smoke path**, not the full sealing feature. Staging (see §3) keeps it thin: backend-only, fixture-driven, B-B (no TSA), sync, no audit trail, no persistence of a signing aggregate.

## 2. What already exists (reuse / lift — do not rebuild)

### 2a. The found DSS work — `feat/T04.2.1`, in the sibling worktree `f5sign-backend-dss/`

A real, well-tested DSS port + HTTP adapter, authored under `App\Shared\Pdf\…`. It is **lifted and re-namespaced** into this repo (§6), but the adapter's signing flow is **reworked** (§5 — it does not match the server-signing flow). Inventory:

| Found at (`f5sign-backend-dss/src/Shared/…`) | What | Disposition |
|---|---|---|
| `Domain/Pdf/DssClientInterface.php` | The wire port: `signDocument` / `extendDocument` / `getMessageDigest` / `signDocumentWithExternalCms` | **Rework** — the one-call `signDocument` is assembly-only (no `signatureValue`); replace with the server-signing flow (§5) |
| `Infrastructure/Pdf/DssHttpAdapter.php` | HTTP adapter (retry, 4xx/5xx→domain-exception mapping) | **Rework** the signing path; keep the error-mapping + transport scaffolding |
| `Infrastructure/Pdf/DssPayloadMapper.php` | DTO↔DSS-JSON mapper (`buildBaseParameters`, `pemToBase64Der`, image params) | **Lift + fix** — reuse `buildBaseParameters`/`pemToBase64Der`/image mapping; **fix the `signingDate` bug** (§5.3) |
| `Domain/Pdf/Request/{SignRequest,DigestRequest,ExtendRequest,SignWithCmsRequest}.php` | Request DTOs | **Lift + adjust** `SignRequest` (cert sourcing flips — §5.4); the others lift as-is (used by deferred levels) |
| `Domain/Pdf/Response/{SignResponse,DigestResponse,ExtendResponse}.php` | Response DTOs | **Lift as-is** (re-namespace only) |
| `Domain/Pdf/ValueObject/{SignatureLevel,DigestAlgorithm,SignatureImage}.php` | VOs (enum values match DSS exactly) | **Lift as-is** (re-namespace only) |
| `Domain/Pdf/Exception/{DssSigningFailed,DssUnavailable,DssInvalidRequest,DssTsaUnavailable}Exception.php` | Domain exceptions | **Lift as-is** (re-namespace only) |
| `Infrastructure/Http/RetryableHttpClientTrait.php` | Generic HTTP retry/backoff | **Lift → Foundation** (`Foundation/Http/` — cross-cutting, not DSS-specific) |

The found tests under `f5sign-backend-dss/tests/` (against `MockHttpClient`) are a **reference**, not a lift — they test the old one-call flow. Re-author against the reworked flow (§9).

### 2b. The `eu-dss` service (already in the infra stack)

In [`f5sign-infra/docker-compose.yml`](../../../f5sign-infra/docker-compose.yml) — built from `dss-demonstrations` v6.4, served at **`http://eu-dss:8080/services/rest`** (the backend reads `DSS_BASE_URL`, default `http://eu-dss:8080/services/rest`). The **server-signing module is enabled** — the healthcheck hits `GET /services/rest/server-signing/keys`.

- **Keystore:** self-signed PKCS#12 at `/keystore/self-signed.p12`, alias **`f5sign-dev-seal`** (DN `CN=F5Sign Dev Seal,O=F5Sign,C=ES`, RSA-2048), generated on first run by `f5sign-infra/docker/eu-dss/scripts/`. Password from `DSS_SIGNING_KEYSTORE_PASSWORD` (dev default `changeit`).
- **Real cert injection is deferred to EP10 and is NOT a blocker** — the server-signing module has its own working keystore. The self-signed seal is exactly why validation returns `INDETERMINATE`/`NO_CERTIFICATE_CHAIN_FOUND` (crypto intact, identity untrusted) — expected for this slice.

### 2c. SE scaffold + Foundation edge (in this repo — the backend, historically called `proto`)

| Thing | Where | Use |
|---|---|---|
| SE Contract types | `src/F5Sign/SignatureExecution/Contract/Type/` (`SignatureExecutionId`, `Target*Ref`) | id + cross-BC refs (untouched here) |
| `MockSignUseCase` / `MockSign` / `MockSignHandler` | `…/Application/UseCase/`, `…/Application/Command/`, `…/Infrastructure/Messenger/Command/` | **left in place** — the real path is added alongside; mock retirement is a later slice |
| Foundation HTTP edge | `src/F5Sign/Foundation/Http/` (`TenantRequestListener`, `ApiExceptionListener`) | the slice runs behind the existing edge; `RetryableHttpClientTrait` lands here too |
| Deptrac layers (SE Domain/Application/Infrastructure) | [`deptrac.yaml`](../../deptrac.yaml) | pre-scaffolded; SE Domain gets its first real classes |

**SE Domain is empty today.** This slice creates its first members.

## 3. Scope

**In scope — Stage 1 (backend-thin, fixture-driven):**
1. **Re-home** the found DSS port + DTOs + exceptions + VOs into SE (Domain), the adapter + mapper into SE (Infrastructure), and the retry trait into Foundation, re-namespaced `App\Shared\Pdf` → `F5Sign\SignatureExecution\…` / `F5Sign\Foundation\Http\…` (§6).
2. **Rework the adapter** to the EU DSS **server-signing** flow (§5): `getDataToSign` → `server-signing/sign/{alias}/SHA256` → `signDocument(signatureValue)`. Drop caller-supplied cert PEMs; resolve the seal cert from the DSS keystore by alias.
3. **SE Domain seal port + the use-case that drives it** (§4.2): a `SealDocument` command + use-case that takes fixture PDF bytes and a target level (B-B), calls the port, returns the signed bytes.
4. **Wiring + config:** `DSS_BASE_URL` + the seal alias as configuration; a scoped `HttpClientInterface` for the adapter; service registration honouring deptrac (Domain port ← Infrastructure adapter).
5. **A driver:** a thin Symfony console command (`app:se:seal-fixture`) **and** an integration test, both producing a real signed PDF against the live `eu-dss`.
6. **ADR:** flip [ADR-0012](../adr/ADR-0012-dss-integration-boundary.md) Proposed→Accepted (record the realized seam + whether the transport/domain split held — §8 D1); add a born-here ADR **only if** the build *changes* a decision (e.g. the cert-by-alias model, or the SE seal-port shape, warrant ADR-0023 — decide at §8).

**Out of scope (deferred — named so they're not silently dropped):**
- **Stage 2** — sealing a *real Envelope document*: pull source bytes from storage, write the signed bytes back. This forces the [ADR-0016](../adr/ADR-0016-storage-model.md) byte-path (MinIO `originals`→`signed`), which is an open question (no `StorageInterface` yet). **Separate task → done in [TASK-006](TASK-006-dss-stage2-real-document-seal.md) (2026-06-18).**
- **Stage 3** — end-to-end through the team **signer frontend** (Signing-Session BC enters; per-recipient signing flow). **Separate task, different BCs.**
- **Higher levels** — B-T / B-LT / B-LTA and the **TSA** (`extendDocument`). `requiresTsa()` is `false` only for B-B; the lifted `ExtendRequest`/`extendDocument` stay dormant.
- **The QES two-step** (`getMessageDigest` + `signDocumentWithExternalCms`) — user-cert / DNIe / EUDI-Wallet signing. Lifted but dormant.
- **Per-user cloud certificates** (`Especificaciones/Cloud Signing — Certificados por Usuario`). The seal here is the *platform* seal (AES company seal), not a per-user cert.
- **Audit trail** (the in-tx `AuditableEvent` chain), **a persisted `SignatureExecution` aggregate**, **async** sealing (Messenger), **real auth**, **real/trusted cert** (EP10), **visual signature** (the lifted `SignatureImage` stays optional/off).
- **Validation** of arbitrary signed documents (ADR-0012 point 4 — explicitly unhomed).

The full sealing feature (B-T + TSA + async + storage) is `Especificaciones/Sellado Directo`. This slice is the **DSS smoke path** under it.

## 4. Design leans (recommended; mine to lock unless you object)

Implementation-internal and reversible — stated so the build is unambiguous. The genuinely-debatable structural calls are in §8.

### 4.1 Re-homing & namespaces
- Found `App\Shared\Pdf\…` → **`F5Sign\SignatureExecution\Domain\Pdf\…`** (port, DTOs, exceptions, VOs) and **`F5Sign\SignatureExecution\Infrastructure\Pdf\…`** (adapter, mapper). `App\Shared\Infrastructure\Http\RetryableHttpClientTrait` → **`F5Sign\Foundation\Http\RetryableHttpClientTrait`**.
- Per [ADR-0012](../adr/ADR-0012-dss-integration-boundary.md) point 3, the wire client is "thin shared infrastructure," not a Foundation port (it carries domain DTOs like `SignatureLevel`). With SE the sole consumer in this slice, the ROADMAP's call stands: it lives **in SE**, not a shared module. The "shared" concern bites only when a second non-SE consumer appears — note the reconciliation on ADR-0012, don't pre-build a shared home (§8 D1).
- Strip Spanish docblocks to English on touched files per the source-of-truth-shift; keep the eIDAS notes (they're load-bearing). Re-point design-repo `@see`/refs (the found docblocks cite `Arquitectura/EU DSS - Guía de Integración.md §N`) per touched-file hygiene — tag with `OFFREPO:` where a pointer is irreducibly external.

### 4.2 The SE seal port + use-case
- Keep the reworked wire port named for what it is — a DSS client. The **use-case** carries SE's intent: `SealDocument` (command) → `SealDocumentUseCase`, which calls the port's `sealDocument(...)` (the reworked single seal operation) and returns/yields the signed bytes.
- **No persisted aggregate, no event** in this slice (unlike `MockSignUseCase`, which emits `DocumentSigned`). The smoke path proves cryptography, not the lifecycle. Returning signed bytes (or writing them to a temp path for the CLI) is enough. The `DocumentSigned`/artifact-append path stays the mock's job until Stage 2.
- **Do not reuse the cross-BC `EnvelopeCommandInterface` path** the mock uses — there's no Envelope here. Fixture in, signed bytes out.

### 4.3 Cert / keystore model (forced by server-signing)
- The seal cert is **not** supplied by the caller. The adapter resolves it from the DSS keystore by **alias** (`f5sign-dev-seal`, from config), via `GET /server-signing/key/{alias}`. So the lifted `SignRequest`'s `signingCertificatePem`/`certificateChainPem` fields **go away** for the seal path (§5.4). The alias is the platform-seal identity.

### 4.4 Config & wiring
- `DSS_BASE_URL` (env, default `http://eu-dss:8080/services/rest`) and `F5SIGN_SEAL_ALIAS` (default `f5sign-dev-seal`) as bound parameters. A scoped Symfony `HttpClientInterface` (`base_uri` = `DSS_BASE_URL`) injected into the adapter.
- Adapter registered as the `DssClientInterface` implementation; deptrac must stay green (Domain declares the port, Infrastructure implements it).

### 4.5 The driver
- A console command in `…/Infrastructure/Console/` (Infrastructure — framework-aware) that loads a fixture PDF (`tests/Fixtures/pdf/sample.pdf` or generated), seals it B-B, writes the result to a path, and prints a one-line summary. Demo affordance + manual smoke check.
- The integration test is the lock (§9).

## 5. The DSS server-signing flow (load-bearing — self-sufficient spec)

> The executing agent will **not** have the design repo (`Arquitectura/EU DSS - Guía de Integración.md`) under agent-only access. This section is the authoritative, in-repo description of the flow. Confirm endpoint shapes empirically against the running `eu-dss` as build step 1 (the integration test is the source of truth).

### 5.1 Why the found `signDocument` is wrong

EU DSS `POST /signature/one-document/signDocument` is the **assembly** step — it embeds an **already-computed `signatureValue`** into the PAdES container. The found adapter calls it with `parameters` + `toSignDocument` but **no `signatureValue`** (see `DssHttpAdapter::signDocument` in the salvage bundle). That is incomplete: DSS has nothing to embed. Server-side sealing needs the keystore to actually produce the signature first.

### 5.2 The correct flow (server-signing, B-B, no TSA)

Four HTTP calls against `eu-dss` (base `DSS_BASE_URL`):

```
0. GET  /server-signing/key/{alias}
        → RemoteKeyEntry: the seal's certificate (+ chain), base64 DER.
          (Or GET /server-signing/keys and pick {alias}.)

1. POST /signature/one-document/getDataToSign
        body: { parameters: P, toSignDocument: { bytes, name } }
        → ToBeSigned { bytes }   // the DTBS digest to sign
        where P.signingCertificate = the cert from step 0,
              P.signatureLevel = "PAdES_BASELINE_B",
              P.signaturePackaging = "ENVELOPED",
              P.digestAlgorithm = "SHA256",
              P.blevelParams.signingDate = <T>   // fixed; see 5.3

2. POST /server-signing/sign/{alias}/SHA256
        body: ToBeSigned { bytes }   // the DTBS from step 1
        → SignatureValue { algorithm, value }   // e.g. RSA_SHA256

3. POST /signature/one-document/signDocument
        body: { parameters: P, toSignDocument: { bytes, name },
                signatureValue: { algorithm, value } }   // from step 2
        → RemoteDocument { bytes, name, mimeType }   // the signed PDF
```

The `parameters` object `P` in steps 1 and 3 **must be byte-for-byte identical** (DSS recomputes the byte range; a mismatch invalidates the signature).

### 5.3 The `signingDate` bug (must fix on lift)

The found `DssPayloadMapper::buildBaseParameters` (in the since-deleted `feat/T04.2.1` code; quoted here because this doc is now its only record) sets `blevelParams.signingDate = (int)(microtime(true) * 1000)` **freshly on every call**. In the old one-call flow that was harmless; in the two-call flow it is a **correctness bug** — `getDataToSign` (step 1) and `signDocument` (step 3) would receive *different* signing dates, so the byte range hashed in step 1 ≠ the byte range assembled in step 3, and the signature is invalid. **Fix:** compute `signingDate` (and the whole `parameters` object) **once** per seal operation and reuse the identical object for steps 1 and 3.

### 5.4 `SignRequest` adjustment

For the seal path, replace the caller-supplied PEM fields with an alias-resolved cert. Either (a) the adapter fetches the cert (step 0) and `SignRequest` carries only `{ pdfBase64, fileName, signatureLevel, digestAlgorithm, signatureImage? }`, or (b) keep `SignRequest` cert-shaped internally and have the adapter populate it from step 0 before calling the mapper. Lean (a) — the port's request should not pretend the caller owns the cert. `pemToBase64Der` is reused to encode the step-0 cert into `encodedCertificate`.

### 5.5 Error mapping (keep from the found adapter)
- Transport failure after retries → `DssUnavailableException`.
- DSS 4xx → `DssInvalidRequestException` (extract `message`).
- DSS 5xx after retries → `DssUnavailableException`.
- Retry only the idempotent reads / 5xx; `server-signing/sign` is effectively idempotent for a fixed DTBS. Keep `RetryableHttpClientTrait`'s `[500,502,503,504]` set.

## 6. Re-homing map (source → target)

| Source (`f5sign-backend-dss/src/Shared/…`) | Target (`f5sign-backend/src/F5Sign/…`) | Change |
|---|---|---|
| `Domain/Pdf/DssClientInterface.php` | `SignatureExecution/Domain/Pdf/DssClientInterface.php` | rework signing op (§5) |
| `Domain/Pdf/Request/SignRequest.php` | `SignatureExecution/Domain/Pdf/Request/SignRequest.php` | drop PEM fields (§5.4) |
| `Domain/Pdf/Request/{Digest,Extend,SignWithCms}Request.php` | `SignatureExecution/Domain/Pdf/Request/…` | re-namespace only (dormant) |
| `Domain/Pdf/Response/*.php` | `SignatureExecution/Domain/Pdf/Response/…` | re-namespace only |
| `Domain/Pdf/ValueObject/*.php` | `SignatureExecution/Domain/Pdf/ValueObject/…` | re-namespace only |
| `Domain/Pdf/Exception/*.php` | `SignatureExecution/Domain/Pdf/Exception/…` | re-namespace only |
| `Infrastructure/Pdf/DssHttpAdapter.php` | `SignatureExecution/Infrastructure/Pdf/DssHttpAdapter.php` | rework flow (§5), fix signingDate |
| `Infrastructure/Pdf/DssPayloadMapper.php` | `SignatureExecution/Infrastructure/Pdf/DssPayloadMapper.php` | fix signingDate; add server-signing payloads |
| `Infrastructure/Http/RetryableHttpClientTrait.php` | `Foundation/Http/RetryableHttpClientTrait.php` | re-namespace only |
| *(new)* | `SignatureExecution/Application/Command/SealDocument.php` | new |
| *(new)* | `SignatureExecution/Application/UseCase/SealDocumentUseCase.php` | new |
| *(new)* | `SignatureExecution/Infrastructure/Console/SealFixtureCommand.php` | new |

## 7. The validation expectation (read before writing the test)

The spike produced a real B-B signature; DSS *validation* of it returned `INDETERMINATE` / `NO_CERTIFICATE_CHAIN_FOUND` — **the cryptography is intact; the self-signed dev seal is simply untrusted.** This is the correct, expected state for the slice ("real crypto / demo identity").

**Therefore the test asserts cryptographic-structural success, not trust:**
- the output is a non-empty, valid PDF (`%PDF` header; larger than the input);
- it contains an embedded PAdES signature (a `/Sig` / `/ByteRange` dictionary, or DSS's own structure check);
- (optionally) DSS's `/validation/validateSignature` returns a signature present with `INDETERMINATE` due to chain-not-found — i.e. assert the *signature exists*, and **do not** require `TOTAL_PASSED`.

Asserting `TOTAL_PASSED` would couple the test to a trusted cert we don't have (EP10) and is out of scope.

## 8. Decisions to resolve before building (your call — recommendation given)

**D1 — Honour ADR-0012's transport/domain split now, or defer?** ADR-0012 point 3 predicts a thin wire `DssClient` *wrapped* by domain-meaningful SE services (`SealService`/`PAdESSigningService`). The found code is only the thin client.
- *Option A (recommended):* **Defer the domain-service layer.** `SealDocumentUseCase` calls the reworked `DssClientInterface` directly. ADR-0012 itself flags the split as a *prediction* that "building the real client may reveal the seam wants reshaping" — so don't pre-build it; let a second consumer (E&A's XAdES audit-trail signing) force it. Flip ADR-0012 to Accepted, recording that the wire port landed in SE and the wrapping-service layer is deferred-not-rejected.
- *Option B:* Build `SealService` (Domain) wrapping the client now, to match ADR-0012's shape literally. More faithful, but speculative — one consumer, no forcing case.

**D2 — A born-here ADR for the cert-by-alias / server-signing model?** The slice introduces two things ADR-0012 didn't specify: (i) seal cert resolved by keystore **alias** (not caller-supplied), (ii) the **three-call server-signing orchestration**. These are decisions, not mere instantiation.
- *Recommendation:* fold (i)+(ii) into ADR-0012's "Realized in" + a short **ADR-0023 (server-signing seal flow)** only if you want them as a first-class, separately-citable decision. Lean: **ADR-0023**, because the cert-by-alias model is a real architectural choice a future reader (and the EP10 real-cert work) needs to find.

**D3 — Console command + integration test, or test-only?** Recommendation: **both** (ROADMAP says "test/CLI-driven"; the CLI is a cheap demo affordance and a manual smoke check). Cheap to drop if you'd rather keep surface minimal.

**D4 — Fixture PDF source.** A checked-in `tests/Fixtures/pdf/sample.pdf`, or generate a trivial PDF in-test? Recommendation: **checked-in fixture** (deterministic; a generated PDF adds a PDF-writer dependency for no benefit).

## 9. Test plan & acceptance

**Integration test** (`tests/F5Sign/SignatureExecution/Integration/DssSealSliceTest.php`) — runs via `make test` (auto-ensures the stack, so `eu-dss` is up):

| # | Given / When / Then |
|---|---|
| T1 | **Given** a fixture PDF + the dev seal alias, **when** `SealDocumentUseCase` seals it at B-B, **then** it returns a non-empty PDF, larger than the input, with `%PDF` header and an embedded signature dictionary. |
| T2 | **Given** the signed output, **when** inspected (or sent to DSS `/validation`), **then** a PAdES signature is present (validation may be `INDETERMINATE`/chain-not-found — assert *present*, not `TOTAL_PASSED`). |
| T3 | **Given** `eu-dss` unreachable (point the client at a dead base_uri, or `MockHttpClient` transport error), **when** sealing, **then** `DssUnavailableException`. |
| T4 | **Given** DSS returns 4xx (malformed parameters via `MockHttpClient`), **when** sealing, **then** `DssInvalidRequestException`. |

**Mapper unit tests** (`…/Unit/Pdf/DssPayloadMapperTest.php`) — re-authored from the found tests for the reworked flow. The load-bearing one: **the `parameters` object passed to `getDataToSign` and to `signDocument` is identical** (locks the §5.3 signingDate fix).

**Acceptance:**
- `make qa` green end-to-end (PHPStan L9 · Deptrac **0** · lint · full suite).
- T1–T4 green against the live `eu-dss`.
- ADR-0012 → Accepted (+ ADR-0023 if D2 chosen).
- Touched-file hygiene pass over every lifted/new file (Spanish→English, design-repo refs re-pointed or `OFFREPO:`-tagged).

## 10. Open follow-ups this task surfaces (track, don't solve here)
- **Stage 2 (real Envelope doc)** forces the [ADR-0016](../adr/ADR-0016-storage-model.md) byte-path (no `StorageInterface` yet) — its own task; consolidation tracked as [BACKLOG](../BACKLOG.md) BL-2. → **LANDED in [TASK-006](TASK-006-dss-stage2-real-document-seal.md) 2026-06-18; BL-2 discharged.**
- **EP10 — real/trusted seal cert** (FNMT or equivalent) replaces the self-signed dev seal; flips the validation expectation (§7) to `TOTAL_PASSED`.
- **B-T + TSA** (`extendDocument`) — needs a TSA URL + the augmentation step; the `eu-dss` `DSS_TSA_URL` is wired but untested.
- **Async sealing** via Messenger (CLAUDE.md rule 3 / 8 — never block a sync handler on DSS); the smoke path is sync by design.
- **`MockSignUseCase` retirement** — once the real lifecycle path (aggregate + `DocumentSigned` + artifact append from real bytes) lands, the mock goes.
- **The "no `DssClient` outside SignatureExecution" enforcement rule** (ADR-0012 "Enforced by" candidate) — addable now that the client is real (deptrac forbidden-dependency or PHPStan).
- **`/eidas-compliance` validation** — the team's `eidas-compliance` skill checks algorithms/levels/EU DSS integration against the cloud-signing decisions; run it (or its successor) against this slice.

## 11. Implementation outcome (2026-06-15)

Built green — `make qa`: PHPStan L9 · Deptrac **0** · lint · **157 tests** (was 133 after the value-layer salvage; +24 here). Decisions §8 landed as agreed: D1 defer the wrapper service, D2 born-here [ADR-0023](../adr/ADR-0023-dss-server-signing-seal-flow.md), D3 CLI built, D4 checked-in `tests/Fixtures/pdf/sample.pdf`. The slice was lifted from the dead `feat/T04.2.1` branch (its last copy deleted 2026-07-28; this doc is the record) and reworked. [ADR-0012](../adr/ADR-0012-dss-integration-boundary.md) → Accepted.

**Corrections to this spec's plan (the spec body above is the as-planned record):**
- **Seal alias is `certificate`, not `f5sign-dev-seal`** (§2b / §5 are wrong). The running `eu-dss` serves the **upstream demo keystore** (alias `certificate`); the infra `generate-self-signed-keystore.sh` alias `f5sign-dev-seal` is **not wired into the server-signing module** — EP10 keystore-injection debt, live. `F5SIGN_SEAL_ALIAS` defaults to `certificate`; validation stays `INDETERMINATE` by design (§7 holds).
- **No Application `SealDocument` use-case** (drops §4.2 / §9's `SealDocumentUseCase`). The kernel `UseCase` contract returns `void` → cannot hand back signed bytes for a fixture/CLI/test smoke. The port `DssClientInterface::seal()` is the unit; the CLI and tests call it directly. The command-bus path fits **Stage 2** (seal real doc → store bytes → emit `DocumentSigned`). Recorded in ADR-0023 Decision 5.
- **`DSS_BASE_URL` is the host only** (`http://eu-dss:8080`); the adapter owns the `/services/rest/…` paths. A leading-slash request path *overwrites* a base-URI path under RFC-3986/Symfony resolution — so the team's original `.env` (`…/services/rest`) + leading-slash paths had a **latent base-URL bug** the mock-only tests never caught. (ADR-0023 Decision 4.)
- **Only the seal-path types were lifted into proto** — not the full §6 map. The dormant Request/Response DTOs for the deferred flows (`Extend*`, `Digest*`, `SignWithCms*`) and `pemToBase64Der` stay in the **bundle**, to be lifted when B-T/QES features land. The salvaged JSON/PEM fixtures weren't needed (the new flow uses the keystore cert).

**Bugs fixed on lift:** the `signingDate`-per-call drift (§5.3 — now built once, locked by the mapper's parameter-identity test); generic exceptions → `GenericValidationException` (Domain) / typed DSS exceptions; `@see` FQCN.

**Tests realized:** §9's T1/T2 as the live integration test (`DssSealSliceTest`); T3/T4 as adapter unit tests (`DssHttpAdapterTest`, `MockHttpClient`); the signingDate-identity lock + response parsing as `DssPayloadMapperTest`; the retry trait test under Foundation. Realized files: see ADR-0023 "Realized in".

<!-- OFFREPO: external refs named here but not followable from this repo — `Arquitectura/EU DSS - Guía de Integración.md` (design-repo integration guide; §5 reproduces what's needed to build), `Especificaciones/{Sellado Directo, Cloud Signing — Certificados por Usuario}` (design-repo feature specs, used only to name the full feature this slice sits under), `EP10` (real-cert injection backlog), `f5sign-backend-dss/` (sibling worktree — removed) and the `feat/T04.2.1` branch it held, whose last copy (a workspace-root git bundle) was **deleted 2026-07-28 by decision**. Enough is described inline to act without them: this doc's §2a inventory, §5 rework and §7 record are the surviving account of that code, and §5's whole point is that the found adapter's flow was wrong. Nothing recoverable is owed — **none** of the deferred-flow shapes was lifted (`Extend*` for B-T/B-LT/B-LTA, `Digest*` and `SignWithCms*` for the QES two-step), and ADR-0023 now records that each must be re-authored against the live API when its flow is built. -->
