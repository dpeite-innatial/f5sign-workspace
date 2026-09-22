---
name: security-audit-core
description: Generic security audit of the code introduced by a task, independent of the stack. Covers common checks (hardcoded secrets, PII in logs, dependencies with CVEs, authentication/authorization at a conceptual level, auth middleware present, cross-tenant leaks) and delegates the stack-specific checks to security-audit-backend or security-audit-frontend depending on the repo. If the diff touches signing or crypto, it also delegates to eidas-compliance. Use it with /security-audit-core TASK-NNN. Trigger with "security audit", "review security", "OWASP check", "auth/PII check".
---

# Security Audit Core

Hard security gate. Always invoked. Runs generic checks and delegates to the stack-specific variants.

## Invocation

```
/security-audit-core TASK-NNN
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- Previous reports that exist in the workspace (`doctrine-guard.report.md`, `contract-check*.report.md`,
  etc.) to avoid redundancy
- The task's `.md`. **Delegations are decided by what the diff touches, not by tags** (this format
  doesn't have them)
- Output of `composer audit` / `npm audit` provided by task-runner
- The repo's `.claude/skills-config.yaml` (to know the stack: `backend` | `frontend`) — it exists and
  declares `stack: backend`

## Outputs

- `var/task-runner/T{id}/security-audit.report.md` (consolidated report of core + backend/frontend +
  eidas if applicable)
- JSON:
  ```json
  {"status":"pass|fail|warn","summary":"...","issues":[...],"delegatedTo":["security-audit-backend|frontend","eidas-compliance"?]}
  ```

## Execution

### Step 1 — Generic checks (any stack)

Run over the diff's files. Skip categories whose scope doesn't appear in the diff.

#### Secrets
- [ ] No hardcoded API keys, passwords, tokens (grep patterns: `AWS_`, `API_KEY`, `SECRET`, `Bearer `,
      long base64, `sk_live_`, `pk_live_` strings, JWT-like)
- [ ] ⚑ **`.env`, `.env.dev` and `.env.test` ARE committed on purpose** (repo rule 4): they carry
      local-stack defaults, which match infra's compose and aren't secrets. What's being searched for
      isn't "there's an `.env` in git", it's **a real credential**: a prod/staging password, a real API
      token, a real `APP_SECRET`, the DSS keystore password. Those live only in `.env.local` /
      `.env.*.local` (gitignored) or in the secrets vault.
- [ ] ⛔ **And a placeholder for a sensitive variable is a finding, not a solution.** `.env` ships
      **inside the production image**, so a key named there always resolves and production would boot
      with the committed value. The correct pattern is **absence** (`%env()%` failing to build the
      container); the only exception is an empty `FIELD_ENCRYPTION_SECRET=`, because empty can't work
      and its consumer rejects fewer than 32 bytes
- [ ] No committed internal URLs (private endpoints, prod hostnames)
- [ ] Logs don't print sensitive variables (grep log statements with variables containing "token",
      "password", "secret", "key", "credential")

#### PII
- [ ] PII in logs: emails, phone numbers, DNI/NIE, IBAN, addresses, real names — redacted or excluded.
- [ ] ⚑ **Assert the closed set of keys, don't do a spot-check.** An "I don't see PII here" misses the
      new field: enumerate the fields the surface emits/persists and decide on **all** of them. ⚠ On the
      backend, PII kept out of the event log is correct and checkable (ADR-0031, Path B), but **PII at
      rest is NOT encrypted today**: `FieldCipher` has no callers and ADR-0033 is `Proposed`. Don't
      assume that protection; if the diff adds a column with PII, it's a finding
- [ ] PII in URLs: not in the path or query string (goes in body or headers)
- [ ] Responses don't expose more PII than the endpoint needs

#### Authentication / Authorization (conceptual)
- [ ] New routes that should require auth, do. ⚠ On the backend **there's no SecurityBundle
      registered**: the seam is the route declaring its credential type and an already-verified principal
      (ADR-0044/ADR-0048). The detail is checked by `security-audit-backend`; here it's enough that no
      new route is left undeclared
- [ ] Operations that require authz (not just being logged in, but having permission on the specific
      resource) have an explicit check
- [ ] JWT tokens / session tokens are not logged or returned in responses

- [ ] ⚑ **Declaring a credential type is not the same as being protected.** Check that a `NONE` is
      **defensible and scoped by environment**: today `GET /api/doc.json` declares `_authn: 'NONE'` —so
      it passes any "it's declared" check— and has **no** `when@dev` gate, so it publishes the API's
      entire surface, including the field vocabulary and every validation bound, in production (BL-63).
      A new `NONE` route with no justification and no environment gate → `fail`.

#### Multi-tenant isolation (conceptual)
- [ ] New endpoints/operations that access a tenant's data respect the context (formal stack-level
      verification happens in backend/frontend; here it's conceptual only)
- [ ] Resource IDs are not trusted from the client without verification
- [ ] If the task is critical for multi-tenancy: there's a cross-tenant test that tries to access
      another tenant's resource and expects 404/403

#### Dependencies
Input: output of `composer audit` (backend) or `npm audit` (frontend) provided by task-runner.
- [ ] ⚠ **`composer audit` needs network access**: without it, it fails with `Could not resolve host:
      repo.packagist.org` and there's no local advisory cache, so an offline run **can't be told apart**
      from a clean one. Declare it.
- [ ] No HIGH or CRITICAL CVEs **introduced by this task** — and also **report the absolute state**:
      today there's 1 live HIGH (`symfony/http-kernel`) that the delta filter never triggers on, and
      repo rule 1 forbids regenerating `composer.lock` without permission, so the fix isn't in this
      skill's hands.
- [ ] MEDIUM / LOW → `warn`. ⚑ And there are advisories with `severity: null` (today one,
      `symfony/runtime`): the ladder needs an arm for that case or they slip through silently.

#### Errors and logging
- [ ] User-facing error messages don't leak stack traces, internal paths, infrastructure details
- [ ] 404 vs 403: 403 only if the user already knows about the resource (avoid user enumeration)

### Step 2 — Delegate to security-audit-{stack}

Read `.claude/skills-config.yaml` to determine the stack. If the file doesn't exist, infer it from the
presence of `composer.json` (backend) or a `package.json` with Vue/Nuxt (frontend).

Invoke via the Agent tool:
```
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "security-audit-{stack} on T{id}",
  prompt: "Execute the security-audit-{stack} skill at .claude/skills/security-audit-{stack}/SKILL.md on T{id}. Workspace: var/task-runner/T{id}/. Return the JSON summary."
})
```

Consolidate its report under the "## security-audit-{stack}" section of the report. Its issues get added
to the total list.

### Step 3 — Delegate to eidas-compliance (if applicable)

If the diff touches signing or crypto — `src/F5Sign/SignatureExecution/`, `Foundation/Crypto/`, DSS,
PAdES, TSA:
```
Agent({
  subagent_type: "general-purpose",
  model: "opus",
  description: "eidas-compliance on T{id}",
  prompt: "Execute eidas-compliance skill at .claude/skills/eidas-compliance/SKILL.md on T{id}..."
})
```

Consolidate under "## eidas-compliance". If it returns `fail` → this skill also fails.

### Step 4 — Consolidate and return

If any delegation returned `fail` → `status: fail`.
If all `pass` but there are WARNs → `status: warn`.
If everything's clean → `status: pass`.

## Severity

- **FAIL:** SQL/command injection detected conceptually, endpoint with no auth when it should have one,
  cross-tenant leak, hardcoded secret, unredacted PII in logs, `security-audit-{stack}` or
  `eidas-compliance` returning fail
- **WARN:** dependency with a LOW/MEDIUM CVE, somewhat verbose error message, and —once only, not per
  endpoint— that a new surface would call for rate limiting: **the component isn't installed in the
  backend**, so it's a capability gap, not a defect in the route

## Report

```markdown
# security-audit — T{id}

**Status:** {PASS|FAIL|WARN}
**Total issues:** {B} blocking, {W} warnings
**Delegations:** security-audit-{stack} ({status}), eidas-compliance ({status})

## Core issues
- [{category}] {file:line} {message}

## security-audit-{stack}
{consolidated summary from the specific skill's report}

## eidas-compliance (if applicable)
{consolidated summary}

## Categories reviewed
- Secrets: OK
- PII: OK
- Auth/Authz: OK
- Multi-tenant: OK
- Dependencies: {N} CVEs (LOW:X, MEDIUM:Y, HIGH:0, CRITICAL:0)
```

## Return JSON

Last line:
```json
{"status":"fail","summary":"1 hardcoded secret + 1 fail in security-audit-backend","issues":[{"severity":"fail","category":"secret-hardcoded","file":"...","message":"..."}],"delegatedTo":["security-audit-backend"]}
```

## What it does NOT do

- Does not validate API contracts (contract-check-*)
- Does not validate persistence (doctrine-guard)
- Does not run pentesting or exploits
- Does not audit infrastructure (Docker, k8s, CI)
- Does not rewrite code — only reports

## Correction protocol

If task-runner retries by passing this report to `implement-*`: instruction "fix blocking issues without
changing scope". Max 2 automatic iterations.

## References

- <!-- OFFREPO --> Original design (prototype, superseded): `Implementación/Skills de Ejecución de Tareas/common/06 - Security Audit Core.md`
- security-audit-backend: `.claude/skills/security-audit-backend/SKILL.md` (in backend repo)
- security-audit-frontend: `.claude/skills/security-audit-frontend/SKILL.md` (in frontend repo)
