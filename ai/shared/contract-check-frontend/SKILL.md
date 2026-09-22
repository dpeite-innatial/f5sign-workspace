---
name: contract-check-frontend
description: 'Validates API contracts consumed from the frontend: composables and stores calling endpoints use TypeScript types generated from OpenAPI (not ad-hoc types), handle the declared error codes, cancel pending requests. If the task listens to async events (websockets/SSE) it verifies coherence with AsyncAPI. Use with /contract-check-frontend T{id}. Trigger with "validate frontend contracts", "check API types", "review fetch composables".'
---

# Contract Check Frontend

API contract validation from the consumer side. Only if tags include `api` or `event`. Hard gate.

## Invocation

```
/contract-check-frontend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- Task `.md`
- Parent story README (for AC with error codes)
- Types generated from OpenAPI (typical path: `types/api.ts`, `src/types/openapi.d.ts`, or wherever the project configures it)
- `docs/asyncapi/*.yaml` (if the task consumes async events)

## Outputs

- `var/task-runner/T{id}/contract-check-frontend.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...],"tagMismatches":[...]}`

## Precondition

If the project does NOT have OpenAPI→TS tooling configured (no generated types file nor an `openapi:generate` script exists): emit WARN "OpenAPI→TS not configured, ad-hoc types allowed" and skip the type checks. Continue with the rest.

## Execution

### Step 1 — Detect tag mismatch

- If tag `api` and the diff does not contain composables with `fetch`/`$fetch`/`useFetch`/`axios` or stores with HTTP calls → `tagMismatches: ["api"]`
- If tag `event` and the diff does not contain websocket/SSE/EventSource code → `tagMismatches: ["event"]`

### Step 2 — Checks for tag `api`

#### Generated types
Locate composables/stores in the diff that make HTTP calls. For each call:

- [ ] The request (body) type comes from generated types (imported from `@/types/api` or equivalent)
  - Grep patterns: `import type { X } from '@/types/api'`, `paths['...']['post']['requestBody']`, etc.
- [ ] Same for the response type
- [ ] No `any` in request/response
- [ ] No ad-hoc interfaces/types duplicating what's already in the generated types

#### Error codes
For each consumed endpoint, cross-reference with the story's AC:

- [ ] If the AC declares HTTP error X with code Y (e.g. 409 ENVELOPE_ALREADY_CLOSED), the frontend code handles it explicitly:
  - Error capture (try/catch or `.catch()`)
  - Discrimination by code (switch/if on `error.code` or `error.response.status`)
  - Translation to UX (toast, form message, redirect)
- [ ] Errors not listed in the AC have a generic handler (not silenced)
- [ ] 401 errors trigger logout/refresh according to the project's convention
- [ ] 5xx errors show a generic message to the user and log to the monitoring system (if one exists)

#### Request cancellation
- [ ] If the composable runs a fetch in a watcher or effect: it provides a cancellation mechanism (AbortController)
- [ ] On unmount of the component using the composable: pending requests are cancelled
- [ ] `onUnmounted` / `onScopeDispose` with cleanup

#### Type updates
- [ ] If the backend changed its OpenAPI (and types were regenerated) and this task consumes those changes: the import is updated
- [ ] If a composable is detected using a stale shape → `warn` "types may be outdated, verify OpenAPI version"

### Step 3 — Checks for tag `event` (websockets, SSE, realtime)

#### AsyncAPI
If `docs/asyncapi/` exists:
- [ ] Events listened to by the frontend are documented in AsyncAPI
- [ ] The payload schema matches the TS type assumed by the code
- [ ] The channel/topic used matches the config

If AsyncAPI doesn't exist: WARN "AsyncAPI not present, events without a formal contract" (not FAIL, consistent with backend).

#### Typing
- [ ] Received events are typed; their properties are not accessed with `any`
- [ ] If the project has generated types for events (e.g. from AsyncAPI), they are used

#### Cleanup
- [ ] Event subscriptions are cleaned up on unmount (`onUnmounted(() => socket.off(...))`)
- [ ] No orphaned listener memory leaks

### Step 4 — Intersection (tags `api` + `event`)

If the task has both:
- [ ] If the flow is "POST to backend → wait for confirmation event via websocket": timeout and fallback are defined in case the event doesn't arrive

### Step 5 — Tests

- [ ] Composables consuming endpoints have a unit test that mocks the API and verifies:
  - Happy path
  - At least one AC error case
  - Cancellation if applicable

## Severity

- **FAIL:**
  - Use of `any` in request/response when generated types exist
  - AC error code not handled
  - Event listened to without cleanup on unmount (potential memory leak)
  - AsyncAPI event schema diverges from the TS type assumed
- **WARN:**
  - Ad-hoc types duplicating generated ones
  - AsyncAPI not present
  - Potentially outdated types

## Report

```markdown
# contract-check-frontend — T{id}

**Status:** {PASS|FAIL|WARN}
**Tags evaluated:** {api, event}
**Issues:** {B} blocking, {W} warnings

## Blocking
- [{category}] {file:line} {message}

## Warnings
- [{category}] {message}

## Endpoints consumed (from the diff)
- POST /api/v1/envelopes/{id}/close — composables/useEnvelopes.ts:45
  - Types: paths['/api/v1/envelopes/{id}/close']['post'] ✓
  - Errors handled: 409 ENVELOPE_ALREADY_CLOSED ✓, 403 ✓, 5xx ✓

## Events listened to
- (none)

## Tag mismatches
- {list or "none"}
```

## Return JSON

```json
{"status":"fail","summary":"1 AC error code not handled","issues":[{"severity":"fail","category":"error-unhandled","file":"composables/useEnvelopes.ts:52","message":"AC-04 requires handling 409 ENVELOPE_ALREADY_CLOSED, no error branch"}],"tagMismatches":[]}
```

## What it does NOT do

- Does not validate the endpoint's backend implementation (that's `contract-check-backend`)
- Does not generate types from OpenAPI — assumes the project has that tooling
- Does not validate error-handling UX (only that errors are handled)
- Does not audit client security (`security-audit-frontend`)

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/` (new section)
- API docs strategy: `memory/project_api_docs_strategy.md`
