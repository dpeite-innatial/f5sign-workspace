---
name: security-audit-frontend
description: 'Frontend-stack-specific security checks (Vue/Nuxt/TypeScript). Complements security-audit-core with: XSS (v-html + sanitization), CSP, secrets in client code, localStorage with sensitive data, open redirects, postMessage with origin validation, npm dependencies with CVEs. Invoked by security-audit-core. Use with /security-audit-frontend T{id}. Trigger with "security frontend", "audit Vue/JS", "check XSS/CSP".'
---

# Security Audit Frontend

Frontend-stack-specific checks. Normally invoked by `security-audit-core`; directly invocable for debugging.

## Invocation

```
/security-audit-frontend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- Task `.md`
- Output of `npm audit --json` provided by task-runner

## Outputs

- `var/task-runner/T{id}/security-audit-frontend.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...]}`

## Execution

### XSS

- [ ] `v-html` with sanitized content. Grep for `v-html` in templates:
  - If the value comes from an unsanitized variable → FAIL category `xss-v-html`
  - Acceptable sanitization: DOMPurify, sanitize-html, or the input comes from a documented trusted source
- [ ] `innerHTML` in JS/TS code with external input → FAIL
- [ ] `dangerouslySetInnerHTML` (if the project uses any React-like lib) → FAIL
- [ ] Rendering user markdown: always via a sanitizing library (marked + DOMPurify, or similar)

### CSP (Content Security Policy)

If the project defines a strict CSP:
- [ ] No inline `<script>` introduced in `*.vue` (only `<script setup>` processed by the compiler)
- [ ] No inline `<style>`; use `<style scoped>` or classes
- [ ] No `eval`, `new Function`, `setTimeout('string')` — none with strings as code
- [ ] External script imports via the CSP whitelist

### Secrets in client code

- [ ] Exhaustive search in frontend files for:
  - API keys (`API_KEY`, `sk_live_`, `pk_live_`, `AIza...`, etc.)
  - Embedded JWT tokens
  - Hardcoded passwords / credentials
  - Non-public internal URLs
- Any match → FAIL category `secret-hardcoded`
- Public frontend variables must come from `runtimeConfig.public` (Nuxt) or env vars exposed to the client, never hardcoded

### localStorage / sessionStorage / cookies

- [ ] Do not store JWT or session tokens in localStorage/sessionStorage (must go in httpOnly cookies)
  - Grep for `localStorage.setItem` / `sessionStorage.setItem` with keys such as `token`, `jwt`, `bearer`, `auth`, `refresh`
- [ ] Sensitive data (PII, card numbers, national IDs) is not persisted in client storage
- [ ] If localStorage is used for non-critical state: document what is stored and why

### Session validity on screens that don't revalidate it

Applies to apps with a route middleware that only runs on a root route (the signer:
`session.global.ts` short-circuits with `if (!isIndexRoute) return` to avoid re-entering on SSR). SUB-ROUTES
are rendered entirely from the persisted store, which may belong to an already-dead
session, and **nothing revalidates anything**.

- [ ] Every screen rendering from the session validates that it's still alive **against the
      backend**, not just checking that the store has data
  - The case that bites is not the empty store: it's the POPULATED and stale store, where
    `session` exists and says nothing
- [ ] A **401 from a session call** is ROUTED (discard session + return to the
      starting route), never rendered as a local error inside a component
  - Grep: error handlers that only do `errorMessage.value = ...` on a 401
  - An error confined inside a viewer/panel leaves the rest of the screen **alive**:
    the user keeps operating on a session the backend no longer recognizes
- [ ] Before bouncing, the invalid state is DISCARDED
  - If the middleware has a reuse branch (`session !== null && !error`), bouncing
    without clearing returns to the same screen → loop
- [ ] The bounce is limited to once per load

⛔ **Why this is FAIL and not WARN, with a real case:** in the signer it was possible to enter `/view`
and `/sign` with an expired session and walk through the entire ceremony —rails, fields and the sign
button— with the failure hidden in a card inside the PDF box. A signer could reach the end and
**believe they signed**. It was found by a user, not a review: unit tests don't see it because it lives
in the interaction between page, middleware and persisted store, so **this check is verified in the
BROWSER** with the session invalidated by hand, not by reading code.

### External URLs and redirects

- [ ] New domains in `fetch`/`axios`/`$fetch` are documented (allows CSP connect-src)
- [ ] Client redirects (`router.push`, `window.location`) do not accept external URLs from the query string without a whitelist (open redirect)
  - Grep: `router.push(route.query.redirect)` without validation → FAIL
- [ ] Links with `target="_blank"` include `rel="noopener noreferrer"` (tabnabbing)

### postMessage and iframes

- If the new code uses `postMessage` or embeds iframes:
- [ ] `addEventListener('message', ...)` validates `event.origin` against a whitelist
- [ ] `postMessage(data, targetOrigin)` uses a specific targetOrigin, not `'*'`
- [ ] iframes with a restrictive `sandbox` attribute

### npm dependencies

Input: output of `npm audit --json`.
- [ ] No CRITICAL CVEs → FAIL if any exist
- [ ] No HIGH CVEs → FAIL if any exist
- [ ] MEDIUM → WARN
- [ ] LOW → WARN

If the diff introduces new dependencies:
- [ ] Every new dependency with CVEs is rejected
- [ ] Dependencies with abandoned maintenance (e.g. last commit >2 years, <20 stars) → WARN

### Forms

- [ ] Traditional forms with `action="..."`: have a CSRF token in a header or hidden field (per the project's convention)
- [ ] If it's an SPA with fetch and SameSite=Strict/Lax cookies: CSRF auto-covered, OK
- [ ] Sensitive fields (passwords, tokens) use `autocomplete="new-password"` / `autocomplete="off"` where appropriate

### DOM manipulation dependencies

- [ ] `document.write` is not used (legacy, vulnerable)
- [ ] DOM refs (`ref()`) with `innerHTML = ...` with external input → FAIL

### Security tests (if the task is sensitive)

- [ ] If the task involves auth (login, logout, refresh): E2E tests verify that after logout the token no longer works, that refresh fails when the token is expired, that cookies are cleared
- [ ] If the task handles PII: a test verifies that data does not remain in localStorage after logout

## Severity

- **FAIL:**
  - XSS via unsanitized v-html
  - Hardcoded secret in client code
  - Token stored in localStorage
  - HIGH/CRITICAL CVEs in dependencies
  - Open redirect
  - postMessage without origin validation
  - `innerHTML` / `document.write` with external input
  - Invalidated session that leaves an action screen (signing, payment, submission) operable:
    the user can complete an act the backend no longer recognizes
- **WARN:**
  - New heavy dependency
  - Dependency with abandoned maintenance
  - `target="_blank"` without rel
  - LOW/MEDIUM CVE

## Report

```markdown
# security-audit-frontend — T{id}

**Status:** {PASS|FAIL|WARN}
**Issues:** {B} blocking, {W} warnings

## Blocking
- [{category}] {file:line} {message}

## Warnings
- [{category}] {message}

## Categories reviewed
- XSS: OK
- CSP: OK
- Secrets in code: OK
- localStorage: OK
- Redirects: OK
- postMessage: n/a
- npm dependencies: 2 LOW, 0 MEDIUM, 0 HIGH, 0 CRITICAL
- Forms: OK
```

## Return JSON

```json
{"status":"fail","summary":"1 XSS via v-html + 1 token in localStorage","issues":[{"severity":"fail","category":"xss-v-html","file":"components/EnvelopeDescription.vue:28","message":"v-html with unsanitized envelope.description"}]}
```

## What it does NOT do

- Does not do the generic checks (secrets in backend, PII in server logs, conceptual authz) — that's `security-audit-core`
- Does not audit the API it consumes — that's `contract-check-frontend` (types) + `security-audit-backend` (backend)
- Does not validate accessibility (`a11y-check`)
- Does not run client pentesting (real XSS not detectable without runtime)

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/frontend/06 - Security Audit Frontend.md`
- security-audit-core: `.claude/skills/security-audit-core/SKILL.md`
- OWASP Top 10 Web: https://owasp.org/www-project-top-ten/
