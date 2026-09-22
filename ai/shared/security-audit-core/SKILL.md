---
name: security-audit-core
description: Generic security audit of the code introduced by a task, independent of the stack. Covers common checks (hardcoded secrets, PII in logs, dependencies with CVEs, authentication/authorization at a conceptual level, auth middleware present, cross-tenant leaks) and delegates stack-specific checks to security-audit-backend or security-audit-frontend depending on the repo. If the task touches signing/crypto, it also delegates to eidas-compliance. Use with /security-audit-core T{id}. Trigger with "security audit", "review security", "OWASP check", "auth/PII check".
---

# Security Audit Core

Hard security gate. Always invoked. Runs generic checks and delegates to the stack-specific variants.

## Invocation

```
/security-audit-core T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- Previous reports present in the workspace (`doctrine-guard.report.md`, `contract-check*.report.md`, etc.) to avoid redundancy
- Task `.md` (for tags, decides delegations)
- Output of `composer audit` / `npm audit` provided by task-runner
- Repo's `.claude/skills-config.yaml` (to know the stack: `backend` | `frontend`)

## Outputs

- `var/task-runner/T{id}/security-audit.report.md` (consolidated report of core + backend/frontend + eidas if applicable)
- JSON:
  ```json
  {"status":"pass|fail|warn","summary":"...","issues":[...],"delegatedTo":["security-audit-backend|frontend","eidas-compliance"?]}
  ```

## Execution

### Step 1 — Generic checks (any stack)

Run over the diff's files. Skip categories whose scope doesn't appear in the diff.

#### Secrets
- [ ] No hardcoded API keys, passwords, tokens (grep patterns: `AWS_`, `API_KEY`, `SECRET`, `Bearer `, long base64, strings `sk_live_`, `pk_live_`, JWT-like)
- [ ] No `.env` with real values committed
- [ ] No internal URLs committed (private endpoints, prod hostnames)
- [ ] Logs do not print sensitive variables (grep log statements with variables containing "token", "password", "secret", "key", "credential")

#### PII
- [ ] PII in logs: emails, phone numbers, national IDs, IBAN, physical addresses, real names. If they appear in log statements, they must be redacted (e.g. `***@domain.tld`) or not logged
- [ ] PII in URLs: not in path or query string (goes in body or headers)
- [ ] Responses do not expose more PII than necessary for the endpoint

#### Authentication / Authorization (conceptual)
- [ ] New endpoints/routes that should require auth, do require it (any stack)
- [ ] Operations that require authz (not just being logged in, but having permission over the specific resource) have an explicit check
- [ ] JWT / session tokens are not logged or returned in responses

#### Multi-tenant isolation (conceptual)
- [ ] New endpoints/operations accessing tenant data respect the context (formal stack-level verification is done in backend/frontend; only conceptual here)
- [ ] Resource IDs are not trusted from the client without verification
- [ ] If the task is critical to multi-tenancy: a cross-tenant test exists that attempts to access another tenant's resource and expects 404/403

#### Dependencies
Input: output of `composer audit` (backend) or `npm audit` (frontend) provided by task-runner.
- [ ] No HIGH or CRITICAL CVEs introduced by this task
- MEDIUM → `warn`
- LOW → `warn`

#### Errors and logging
- [ ] User-facing error messages do not leak stack traces, internal paths, infrastructure details
- [ ] 404 vs 403: 403 only if the user already knows about the resource (avoid user enumeration)

### Step 2 — Delegate to security-audit-{stack}

Read `.claude/skills-config.yaml` to determine the stack. If the file doesn't exist, infer from the presence of `composer.json` (backend) or `package.json` with Vue/Nuxt (frontend).

Invoke via the Agent tool:
```
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "security-audit-{stack} on T{id}",
  prompt: "Execute the security-audit-{stack} skill at .claude/skills/security-audit-{stack}/SKILL.md on T{id}. Workspace: var/task-runner/T{id}/. Return the JSON summary."
})
```

Consolidate its report under the "## security-audit-{stack}" section of the own report. Its issues are added to the total list.

### Step 3 — Delegate to eidas-compliance (if applicable)

If the `.md` has tags `signing`, `crypto` or `eidas`:
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
If everything is clean → `status: pass`.

## Severity

- **FAIL:** SQL/command injection detected conceptually, endpoint without auth when it should have one, cross-tenant leak, hardcoded secret, unredacted PII in logs, `security-audit-{stack}` or `eidas-compliance` return fail
- **WARN:** dependency with a LOW/MEDIUM CVE, slightly verbose error message, apparent missing rate limit

## Report

```markdown
# security-audit — T{id}

**Status:** {PASS|FAIL|WARN}
**Total issues:** {B} blocking, {W} warnings
**Delegations:** security-audit-{stack} ({status}), eidas-compliance ({status})

## Core issues
- [{category}] {file:line} {message}

## security-audit-{stack}
{consolidated summary of the specific skill's report}

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

If task-runner retries by passing this report to `implement-*`: instruction "fix blocking issues without changing scope". Max 2 automatic iterations.

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/common/06 - Security Audit Core.md`
- security-audit-backend: `.claude/skills/security-audit-backend/SKILL.md` (in the backend repo)
- security-audit-frontend: `.claude/skills/security-audit-frontend/SKILL.md` (in the frontend repo)
