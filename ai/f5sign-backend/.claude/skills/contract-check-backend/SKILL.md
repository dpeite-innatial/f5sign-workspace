---
name: contract-check-backend
description: 'Validates the backend published contracts (PHP/Symfony): Nelmio #[OA\\*] annotations against what the endpoint actually emits (a closed set of keys, not just "nothing is missing"), Contract/Event events (the value of EVENT_TYPE, which nothing pins and whose change re-types history already written; additive payload rules; and why registration and routing do NOT need checking, since they are automatic), and whether a frontend handoff exists when the contract changes. AsyncAPI has no target in this repo and is reported as absent instead of faked. Use it with /contract-check-backend TASK-NNN. Trigger with "validate backend contracts", "check task API", "review Nelmio and events".'
---

# Contract Check (backend)

Published contracts: HTTP and events. Invoked if the diff touches `src/**/UI/Http/`, `config/routes/`,
any `#[OA\`, or a `Contract/Event/`.

## Invocation

```
/contract-check-backend TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` and `context-digest.md`
- `var/task-runner/TASK-NNN/openapi-snapshot.json`. ⚠ **Two traps when generating it.** The `make sf`
  recipe doesn't carry `@`, so the **first line of its stdout is the command itself** and the redirected
  file isn't valid JSON: discard that line or use the container directly. And `make sf` runs on the
  stack's php-fpm, which mounts `../f5sign-backend` — in a worktree the snapshot is **another branch's
  spec**.
- The task's `.md`: its **verification** section serves as acceptance criteria (there's no `AC-NN`)

## Outputs

- `var/task-runner/TASK-NNN/contract-check.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...],"surfacesAbsent":[...]}`

## Execution

### Step 1 — HTTP: the strings in `#[OA\*]` are contract, not comments

⚠ **They get emitted literally into the spec the frontend team ratifies.** One of them actually went so
far as to tell clients to send a value the endpoint doesn't accept. They fall under the sweep of authoring
rule 1.

For every controller in the diff (`src/**/UI/Http/`):

- [ ] `#[OA\Response]` for every **reachable** HTTP code — not the ones it "should" return, the ones the
      code can actually produce, including the 404/409s that come from a mapped domain exception
      (ADR-0029).
- [ ] `#[OA\RequestBody]` if it accepts a body; DTOs with typed `#[OA\Property]` consistent with the PHP
      signature.
- [ ] Security scheme declared if the route is authenticated, and the route's required header declared
      too (a machine route that requires `F5Sign-Declared-Subject` and doesn't publish it leaves the
      browser client unable to send it, which is a real failure that has already happened in CORS
      preflight).

### Step 2 — The closed set of keys: **there's already a test that does this, run it**

⚑ **Before enumerating anything by hand:**
[`OpenApiSpecTest`](../../../tests/F5Sign/Acceptance/OpenApiSpecTest.php) already closes this mechanically
against the **generated** spec: `published_response_schemas_declare_every_key_the_presenter_emits`
compares in both directions over a fully populated view **and carries a positive control** (it fails if
the test could pass on an empty one), and `every_published_enum_is_pinned_to_its_php_enum_or_classified`
audits the enums and fails both for an unclassified one and for a stale classification — including the
four historical defects cited below. **Run that test and read its output.** Redoing it by hand and taking
the manual pass as your safety net is exactly the risk. If you think a case is missing, add it **there**,
not here.

What follows is the why, so you know what you're reading when that test fails:

This is the check that actually pays off, and the one the previous version didn't have. The natural
check —*"is everything the AC asks for declared?"*— **only looks in one direction**. This repo's real
failure was the opposite: the endpoints had always returned `signing_mode` and
`recipients[].document_assignments` and **the spec omitted them**; `Envelope.status` didn't publish
`READY_TO_SEAL`/`ROUTING_FAILED`/`SEALING_FAILED`, and `Recipient.role` left out
`IN_PERSON_HOST`/`CERTIFIED_DELIVERY`.

It's the same asymmetry as in PHPStan level 9: **it rejects a missing key and accepts an extra one**. So:

- [ ] Enumerate what the controller/DTO **actually emits** and compare it against what the spec declares,
      **in both directions**. A field emitted and not declared → `fail`, category `undeclared-emission`.
- [ ] For every enum that goes out through the API: **all** of its `case`s published, or the unsupported
      ones explicitly marked as such. Count the PHP enum's `case`s and compare; don't trust the spec's
      list.
- [ ] Reachable HTTP codes that aren't declared → `fail`.

### Step 3 — Events: `Contract/Event/`, and what bites is the VALUE of `EVENT_TYPE`

Published events live in `src/F5Sign/<BC>/Contract/Event/`, **not** in `Domain/Event/`.

- [ ] `final readonly` class, typed constructor.
- [ ] **Past-tense name** — ADR-0011, with two caveats. First: the surface form is the half the ADR
      itself calls **convention**; what's load-bearing is the **prefix ownership partition** (that
      `Signature*` belongs to SignatureExecution, `Envelope*` to Envelope) and the **mirror**, and its
      lint is *candidate rule, not yet written* — so there are legitimate exceptions from the act-owner
      corollary (`Session/Contract/Event/SignatureCommitted.php`,
      `SignatureExecution/Contract/Event/EnvelopeSealed.php`). Second: `EnvelopeReadyToSeal` is **not** a
      past-tense verb and **is compliant** (name of a transition to a target state). And ADR-0011 is
      `Proposed`, so by rule 7 it doesn't bind yet: report as `warn`, never `fail`.
- [ ] ⚠ **Don't check that the event is "registered": registration is automatic.**
      `RegisterDomainEventsPass` globs `*/Contract/Event/*.php`, filters by `Event` subclass, reads
      `EVENT_TYPE`, and re-runs whenever files are added or removed (`GlobResource`). A well-placed event
      **can't** end up unregistered, and a malformed one throws `LogicException` **at container compile
      time**, meaning the whole suite goes red before you even get here. `LOAD-BEARING.md` §2 already
      says so. What you **do** need to check is below: the **value** of `EVENT_TYPE`.
- [ ] ⛔ **Nothing pins the value of `EVENT_TYPE`, and changing it re-types history already written.**
      There are 26 declared and **no test asserts a value**: the one that pinned them was retired in
      stage 2 of the event log and its replacement is *queued* in ADR-0031. If the diff **changes** an
      existing value → `fail`, category `event-type-rewrite`: the log is permanent and append-only, so
      the bytes already written stop decoding and there's no fixing it. If it **adds** a new one, `pass`
      with a note.
- [ ] Actually emitted: if the event is new, the diff contains whoever publishes it.
- [ ] ⚠ **Don't look for a `routing:` entry for an event: it's deliberately empty.** `messenger.yaml`
      itself explains it — *"No class is bus-routed to `async_events` directly: cross-BC events reach
      the broker only through the event log + relay (ADR-0031), which forces the transport with a
      `TransportNamesStamp`"*. Reporting it as missing is a false positive; **adding it contradicts
      ADR-0031**. The handler also registers itself, via `_instanceof` on `MessengerEventSubscriber`.

### Step 4 — Payload rules (log evolution, ADR-0031)

The log is permanent and **evolution happens only by upcast**: rewriting a stored payload breaks its
`sys_commitment`, so it's forbidden. Hence three hard rules:

- [ ] ⛔ **Never a new required field in an existing payload.** It's read with `Row::optionalString()`
      — its own docblock says so, and there's precedent across four events in **three** BCs (Session ×2,
      SignatureExecution, Envelope). Required field added → `fail`, category `payload-required-field`.
- [ ] ⛔ **Never rename an `event_type` in place.** Add the new one, write both, retire the old one.
      Renamed in place → `fail`: the bytes already written stop decoding.
- [ ] ⚠ **And warn that none of this has a safety net today.** The canonical bytes fixture per
      `event_type` is recorded in ADR-0031 as *"Not enforced — queued, not built"*, and the round-trip
      that exists serializes and deserializes **with the same code**, so it can never detect an
      incompatible `fromPayload()`: both sides move together and drift away together from the bytes
      already in the log. A payload change without that fixture is `warn` with this note, not a silent
      pass.

### Step 5 — If the contract changed, there has to be a frontend handoff

- [ ] There's a new file **in this diff** under `docs/frontend-handoff/` **that isn't `README.md`** → if
      not: `fail`, category `handoff-missing`. ⚠ Don't use the glob `docs/frontend-handoff/*.md` as the
      condition: the README lives there, so the glob **always matches** and the check never fails.
      Convention in [`docs/frontend-handoff/README.md`](../../../docs/frontend-handoff/README.md);
      written by `docs-sync`. A contract change with no handoff is the pattern that left the signer
      waiting on a `signed_copy_url` nobody sends.

### Step 6 — Absent surfaces

**`docs/asyncapi/` doesn't exist on any branch of this repo** (checked 2026-08-17). Don't fail over it
and **don't create it**: report in `surfacesAbsent` which event is left without machine-readable
documentation and say where it lives in the meantime (its `Contract/Event/` class, its entry in
`EventTypeRegistry`, and the ADR that governs it). If the gap is real and recurring, it's a row in
`docs/BACKLOG.md`, not a ghost file.

## Report

```markdown
# contract-check-backend — TASK-NNN

**Status:** {PASS|FAIL|WARN} · **Issues:** {B} blocking, {W} warnings

## HTTP contract
- Declared and not emitted: {list}
- **Emitted and not declared: {list}**  ← the direction that gets forgotten
- Enums: {enum} {n} cases in PHP / {m} published

## Events
- {Event}: past tense ✓ · registered in EventTypeRegistry ✓ · additive payload ✓

## No safety net
- {payload change without a canonical bytes fixture, if applicable}

## Frontend handoff
- {file, or "ABSENT"}

## Absent surfaces (not created on purpose)
- docs/asyncapi/: {event} with no machine-readable contract; lives in {class} + ADR-NNNN
```

## What it does NOT do

- Doesn't validate business logic (`task-validate-backend`).
- Doesn't audit endpoint security (`security-audit-*`).
- Doesn't write the handoff or the OpenAPI (`docs-sync` writes the former; Nelmio generates the latter
  inline).
- Doesn't detect breaking changes by comparing against `develop` (that's CI, and it doesn't exist today).
