---
name: security-audit-backend
description: 'Security checks specific to the backend stack (PHP/Symfony). Complements security-audit-core with: SQL injection via DBAL (no ORM), Symfony asserts, the real authentication seam of this repo (Identity & Access with a route that declares its credential, NOT SecurityBundle: it is not registered), real idempotency (ADR-0042: the id is NOT a retry key), CORS via a custom CorsListener, and the cryptography that does exist (issued credential with partial enforcement, signing token). ⚠ And it says out loud that PII at rest is NOT encrypted today — FieldCipher has no callers and ADR-0033 is Proposed — instead of claiming a protection that does not exist. Includes the two holes an audit found here: the client-supplied Content-Type without nosniff, and the credential that outlives its resource. Names what is NOT installed —rate limiter— instead of reporting it endpoint by endpoint. Invoked by security-audit-core. Use it with /security-audit-backend TASK-NNN. Trigger with "security backend", "audit PHP", "check Symfony security".'
---

# Security Audit Backend

Checks specific to the PHP/Symfony stack. Normally invoked by `security-audit-core`; directly invocable
for debugging.

## Invocation

```
/security-audit-backend TASK-NNN
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/doctrine-guard.report.md` (if it exists)
- Task's `.md`

## Outputs

- `var/task-runner/T{id}/security-audit-backend.report.md`
- JSON:
  ```json
  {"status":"pass|fail|warn","summary":"...","issues":[...]}
  ```

## Execution

Apply the checks to the diff's files. Skip categories whose scope doesn't appear.

### Injection (PHP)
- [ ] No string concatenation in SQL queries: use DQL, QueryBuilder, or prepared statements
  - Grep: `"SELECT .* $" . $var`, `->getResult()` with built strings, incorrect PDO prepare
- [ ] No `shell_exec`/`exec`/`system`/`passthru`/backtick operator with user input
- [ ] No `eval()` or dynamic `include`/`require` with user input
- [ ] Parameterized LDAP/XPath queries if applicable
- [ ] Serialization: no `unserialize()` on external input (RCE)

### Symfony Request/Response
- [ ] Controllers use Request type-hints for parsing (not direct `$_GET`, `$_POST`, `$_REQUEST`)
- [ ] Response headers: explicit `Content-Type`, no autodetect
- [ ] Request DTOs with Symfony `#[Assert\*]` constraints on every property
  - `#[Assert\NotBlank]`, `#[Assert\Length(max=...)]`, `#[Assert\Email]`, `#[Assert\Choice]`, etc.
- [ ] Free-form strings with `#[Assert\Length(max=...)]` (avoid DoS via giant payload)
- [ ] Whitelists with `#[Assert\Choice]` on enums/choices
- [ ] File uploads: `#[Assert\File]` with `mimeTypes`, `maxSize`, `extensions`

### Authentication — **there is no SecurityBundle**, the seam is Identity & Access

⛔ `symfony/security-bundle` and `lexik/jwt-authentication-bundle` **are in `composer.json` but NOT
registered** in `config/bundles.php`. There's no `config/packages/security.yaml`, no firewalls, no
Voters, no `#[IsGranted]`. Looking for any of those is looking for something this repo doesn't have, and
"I didn't find it" would read as a finding when it's the architecture.

What does exist (ADR-0044…ADR-0048), and is what gets checked:

- [ ] **The route declares its credential type**, resolved in `kernel.controller`, **with no fallback**
      (ADR-0048: one credential per route). A new route with no declaration isn't "open by default": it's
      broken → `fail`, category `undeclared-auth`.
- [ ] **The use case receives an already-verified principal**; it does not derive identity from headers
      (ADR-0044). ⚠ The precedent is literal: before identity-access, the tenant came from an unverified
      `X-Tenant-Id` and the actor from an `X-Acting-User-Id` the same way — *"not a weakly attested actor:
      a fiction"*. Any new identity-header read → `fail`.
- [ ] **`F5Sign-Declared-Subject`** on machine routes: mandatory (ADR-0047), published in the spec and
      allowed in the CORS preflight — served here by
      [`CorsListener`](../../../src/F5Sign/Foundation/Http/CorsListener.php), **not**
      `nelmio_cors.yaml`, which doesn't exist.
- [ ] **The signer token** (`SigningTokenCodec` / `SigningTokenListener`) is not scope-widened: it's per
      recipient and per envelope. ⚠ The bug that closed out identity-access (BL-38): a recipient with a
      valid token **replayed their real tenant claim over a channel that verified nothing** and read
      documents that had been denied to them. Any route that accepts a tenant claim from the client →
      `fail`, category `unverified-tenant-claim`.
- [ ] Tests that verify 401/403 on the unauthorized attempt, and **a cross-tenant one that expects
      404/403**.

### Rate limiting — **not installed**, so it isn't a per-endpoint check

⚠ `symfony/rate-limiter` **is not a dependency of this repo** and `config/packages/rate_limiter.yaml`
doesn't exist. Don't flag endpoint by endpoint that "it's missing the limiter": **the whole capability is
missing**, and repeating it per route buries the fact in noise.

- [ ] If the diff adds a surface that needs it (login, OTP, resend, signing, bulk send): **a single
      `warn`** naming the component's absence and what's waiting on it — TASK-022 (in
      `docs/two-gate-signer-auth`) declares it as one of its two nonexistent prerequisites.
- [ ] Don't propose `#[RateLimit]` or create a `rate_limiter.yaml`: installing a component is a decision,
      and it goes through `implement-backend`'s Step 2b gate.

### Idempotency — derived identity, not a header

There are no forms or Twig, so **CSRF does not apply**: the API is consumed with a credential, not a
session cookie.

⛔ **And watch out with idempotency, because it's easy here to ask for what an ADR forbids.** ADR-0014's
Layer 1 is *id-at-the-boundary* (a preassigned UUID), **not** a deterministic mint; and **ADR-0042**
—`Accepted`, and its title is literally *"the id is **not** a retry key"*— removed `field_id` from the
authoring request and retired the 409, leaving it written that *"retry safety is Layer 3's, and its
absence is an accepted exposure"*. Layer 3 (`Idempotency-Key`) **is not built**.

- [ ] **Do not** ask for a derived id or a client-sent id as a retry key: that's exactly what ADR-0042
      removed. What does get checked is that the exposure is **declared** where it belongs, and that
      nothing new silently widens it.
- [ ] Convergence is actually checked: the second attempt **does not** duplicate. The live pattern is
      `if (!$delivery->isPending()) return;`.

### Cryptography — the generic kind and what this repo already has

Generic:

- [ ] Random: `random_bytes()` / `random_int()`. Never `mt_rand()`/`rand()` in a security context.
- [ ] Timing-safe comparison: `hash_equals()` for signatures and secrets. ⚠ **With one argued exception
      that should not be reported:** `IssuedCredential` compares the *trailer* with `!==` on purpose, and
      its docblock explains why — *"No `hash_equals` on the trailer, and its absence is deliberate… a
      constant-time compare there would be cargo-cult, and would suggest to a later reader that the
      trailer carries authority"*. A blanket rule there produces a guaranteed false positive against a
      documented decision.
- [ ] No embedded keys in code: they come from configuration.
- [ ] If passwords ever exist: `password_hash` with ARGON2ID/BCRYPT and `password_verify`. **There is no
      password login today**, so don't report its absence as a finding.

And what does exist here, which is where you actually need to look:

- [ ] **Issued credential**
      ([`IssuedCredential`](../../../src/F5Sign/Foundation/Credential/IssuedCredential.php), ADR-0045) —
      with two nuances that avoid a false `fail`. ADR-0045 is `Accepted (enforcement partial)` and its
      **Gate 1 is still open**: *"nothing publishes the pattern yet"* (BL-80), so "published grammar" is
      the destination, not the current state. And **the signing token is deliberately outside the
      grammar**, recorded as a *known non-conformance* in its §2.3. `CredentialKind` has only one case
      today (`API_KEY`). A new secret with its own format is `warn` citing ADR-0045, not `fail`.
- [ ] **Signing token** (`SigningTokenCodec`): verification with `hash_equals` ✓. ⚠ **The TTL is
      duplicated in two places and neither is "the use case that mints it"**: `MintSigningTokenController`
      does `->modify('+7 days')` and `NotifyActivatedStepRecipientsUseCase` declares
      `private const string TOKEN_TTL = '+7 days'`. Nothing keeps them in sync, so if the diff touches
      one, check the other. ⚑ And a retention promise in the copy about a 7-day token was a real,
      already-fixed bug; don't reintroduce it.
- [ ] ⚠ **PII at rest: today NOTHING is encrypted, and claiming otherwise is the worst possible mistake
      here.** `FieldCipher` exists and is tested, but has **zero callers in `src/`**, and ADR-0033 is
      `Proposed`, saying it in its own words: *"nothing calls them. No column is enciphered."* There is
      live plaintext — `envelope.recipient.email`, `full_name`, `notification.delivery.destination`. So
      the check **is not** "is it encrypted?" (the answer is no, always), it's: **does this diff add a
      column with PII?** → then ADR-0033 is the decision governing it, nothing enforces it, and that's
      reported as a finding with its BACKLOG row. ⚑ And the check is over a **closed set of keys**:
      PHPStan level 9 rejects a missing key and **accepts an extra one**, so an "I don't see PII here"
      skips the new field.
- [ ] **The event log is Path B**: PII in the clear stays **out** of the log; the payload is pseudonymous
      (ADR-0031). A new payload with PII in the clear → `fail`, category `pii-in-log`.
- [ ] `FIELD_ENCRYPTION_SECRET` is never committed with a value, and its consumer rejects fewer than 32
      bytes. It's the only **sensitive** case of the "present and empty" pattern —
      `CORS_ALLOWED_ORIGINS=` is also empty in `.env` and isn't a secret, so don't count it as an
      exception or fill it in.

### The two holes an audit found here, that no generic check catches

- [ ] ⛔ **Never return a `Content-Type` that comes from the client, and always send `nosniff`.**
      `UploadDocumentContentController` stores `$file->getClientMimeType()` —the **declared** one, not
      the sniffed one— with no `Assert\File`, no type list, no max size, and no magic bytes; and three
      download controllers return it verbatim. **`X-Content-Type-Options: nosniff` doesn't exist in
      `src/`, `config/`, or infra's Caddyfile.** If the diff touches upload or download: require a
      content-derived type, a closed list, and `nosniff` (+ `Content-Disposition: attachment` where
      applicable). ⚠ The generic bullet *"explicit Content-Type, no autodetect"* **is satisfied by this
      very broken code**: that's why this check is needed and that one isn't enough.
- [ ] ⛔ **A credential has to die with its resource.** The signing token is stateless, with `exp` and no
      revocation, 7-day TTL; **no file under `src/F5Sign/Session/` looks at `EnvelopeStatus`**, and
      `DownloadSigningDocumentController` only guards against `$content === null`. Result: after an
      envelope is voided, whoever holds the token keeps reading documents for the rest of the week
      (BL-61, open in the same seam). If the diff adds a route with a token or a new terminal state: ask
      **what invalidates the credential**, not just what validates it.

### Persistence — DBAL, not ORM

The ORM was retired (ADR-0018): there's no DQL, no ORM QueryBuilder, no `$em`. Looking for them is
looking for what doesn't exist.

- [ ] SQL with **bound parameters** in `executeQuery`/`executeStatement`; zero input interpolation.
- [ ] Identifiers coming from input (table/column names, `ORDER BY`) **are not** interpolated: they're
      mapped against a closed list in code.
- [ ] Reads go through Foundation's `Row` instead of indexing raw arrays, so an unexpected type fails
      where it's read and not three layers further down.

### Headers and CORS — a custom listener, not `nelmio_cors.yaml`

- [ ] CORS is served by [`CorsListener`](../../../src/F5Sign/Foundation/Http/CorsListener.php);
      **`nelmio_cors.yaml` does not exist**. Review the listener: no `*` origin for private routes, and
      **every mandatory API header allowed in the preflight** — the real bug was rejecting
      `F5Sign-Declared-Subject`, which is mandatory on every machine route, leaving browser clients
      unable to send it.
- [ ] User-facing errors with no stack traces or internal paths: that's centralized by
      [`ApiExceptionListener`](../../../src/F5Sign/Foundation/Http/ApiExceptionListener.php) with
      ADR-0029's mapping; a new exception that escapes the mapping leaks detail → `fail`.

### Security tests, based on what the diff touches (not on tags)

- [ ] If it touches RLS, `tenant_id`, or a tenant-scoped route: **a cross-tenant test** that tries
      another tenant's resource and expects 404/403. ⚑ And check the harness can actually see it:
      `Integration/` runs **one connection** under DAMA rollback, so an isolation test that doesn't open
      a second connection may be passing without exercising anything.
- [ ] If it touches a credential or a token: test of the rejection path (bad, expired, or another
      recipient's credential), not just the happy path.
- [ ] No rate-limit tests: the component isn't installed (see above).

## Severity

- **FAIL:**
  - SQL injection / command injection / path traversal / RCE via unserialize
  - Endpoint with no auth when the AC requires it
  - Weak crypto in security contexts (MD5/SHA1 for passwords, hardcoded key)
  - Object-level authz missing when the AC requires it
- **WARN:**
  - Rate limit missing on an endpoint that probably needs it
  - Verbose error message
  - Security header not explicit

## Report

```markdown
# security-audit-backend — T{id}

**Status:** {PASS|FAIL|WARN}
**Issues:** {B} blocking, {W} warnings

## Blocking
- [{category}] {file:line} {message}

## Warnings
- [{category}] {message}
```

## Return JSON

```json
{"status":"fail","summary":"1 SQL injection + 1 endpoint without auth","issues":[{"severity":"fail","category":"sqli","file":"src/...","message":"string concatenation in DQL, line 45"}]}
```

## What it does NOT do

- Does not do the generic checks (secrets, PII, generic dependencies, conceptual authz) — that's
  `security-audit-core`
- Does not validate eIDAS compliance — that's `eidas-compliance`
- Does not validate structural persistence (RLS policies, indexes) — that's `doctrine-guard`
- Does not validate API contracts — that's `contract-check-backend`
- Does not run pentesting

## References

- <!-- OFFREPO --> Original design (prototype, superseded): `Implementación/Skills de Ejecución de Tareas/backend/05 - Security Audit Backend.md`
- security-audit-core: `.claude/skills/security-audit-core/SKILL.md`
