# TASK-063 — The access gate is always declared

<!-- OFFREPO: the incident in §1 was reported by the dashboard team's session on 2026-10-20, and the options weighed in §4 were argued in the owner's working session that day. Every fact taken from them is restated here; nothing in this record depends on reading either. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/explicit-access-gate`** (tip `60a4bb78`), 2026-10-20 — full suite green under the `wt-backend` lane of this worktree (7657 tests, 84359 assertions, source identical to cf6c6c14; lint, deptrac and PHPStan clean); `60a4bb78` adds four Unit tests on top, fast tier green there (6376 tests; lint, deptrac and PHPStan clean). Infection verdict on the changed lines: eight real escaped mutants killed by tests in `60a4bb78`, the rest justified (§7). ADR-0082 is `Accepted (exercised)`: the owner accepted it on 2026-10-20. The dashboard's change (declare the gate, stop trimming methods) is its own work. |
| **Type** | **Corrective**, at the HTTP edge of `POST /api/v1/envelopes/{id}/recipients` only: omitting the access gate stops meaning "open". The domain types, the stored rows and every read surface are unchanged. A **breaking** change to the published add-recipient contract, coordinated with the dashboard, which is its only client today. |
| **Why** | An open access gate is said by omission, so a client that drops its gates by mistake authors a recipient who enters with the link alone, and nothing anywhere reports it. That is what happened on 2026-10-20 (§1). After this task the omission is a 422 and an open door has to be written down. |
| **Builds on** | [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) (the two-gate model and its request vocabulary), [TASK-033](TASK-033-delegated-signature.md) (`signs_via: MACHINE_KEY` and its neutral pair), [TASK-036](TASK-036-claimable-recipient-slot-and-claim.md) (the claimable slot). |
| **Scope** | The request DTO `AuthRequirementRequest`, `AddRecipientRequest` and `AddRecipientController`, their `#[OA\*]` strings, `OpenApiSpecTest`, the tests that author recipients over HTTP, and the documentation that says an open gate is said by omission. ⛔ Not the domain (`AuthMethod`, `AccessGate`, `SigningGate`, `Recipient`), not the bus command `AddRecipient`, not the read model. |
| **Decision record** | **[ADR-0082](../adr/ADR-0082-the-access-gate-is-always-declared.md)** (drafted as Proposed while planning this task; accepted by the owner on 2026-10-20). It amends [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.1 (the open gate's one spelling becomes `DIRECT_LINK` rather than the absence), [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) (the list spelling) and [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.13 (a slot's gates are declared like any recipient's). |
| **Sibling** | ⚑ TASK-064 (`TASK-064-the-gates-are-editable-until-the-recipient-enters.md`, on branch `feat/gates-editable-before-entry` until it merges) reuses this task's declaration rules for its `PUT`; its HTTP slice lands after this task is merged. |

---

## 1. Why this task exists

On 2026-10-20 the dashboard authored a claimable slot ("Empresa Fantasma S.L", `claimable: true`) with no `auth`
object. Its UI trimmed the declared methods to the contacts it had at creation, and a slot has none, so the
list came out empty and the client sent no `auth` at all. Today that is the neutral pair
(`AccessGate::open()`, `SigningGate::none()`): after the claim the party opened the link and signed, and the
evidence recorded `DIRECT_LINK`. Nobody noticed until after the signature.

The backend cannot tell an open door the sender chose from one a client produced by mistake: both arrive as an
absent `auth`. The owner decided on 2026-10-20 that the access gate is always declared, and that an open one is
written `DIRECT_LINK`. The signing gate stays optional. Four alternatives were weighed (§4).

## 2. What already exists (reuse, do not rebuild)

- `src/F5Sign/Envelope/UI/Http/Request/AuthRequirementRequest.php`:
  - `validateStructuralRules()` runs `validateAccessSlot()` and `validateSigningSlot()` over each scalar and
    each list member.
  - `validateAccessSlot()` refuses `DIRECT_LINK` today ("an open gate is said by omitting…") and refuses any
    method that cannot be established without a session.
  - `validateSigningSlot()` refuses `DIRECT_LINK` ("it issues no challenge") and refuses any method that issues
    no per-act challenge.
  - `validateOneSpellingPerSlot()` refuses the scalar and the list together.
  - A list of two or more may hold only methods that deliver a code. A list of one may hold anything the scalar
    could.
  - The list items' enum in `#[OA\Items]` is hand-typed, because Nelmio does not read `Assert\Choice` nested
    inside `Assert\All`. It already contains `DIRECT_LINK`.
- `src/F5Sign/Envelope/UI/Http/AddRecipientController.php`:
  - `requirementFrom()` returns `null` for an absent `auth`, and also when both slots are empty.
  - Otherwise it builds `AuthRequirement::fromGates()` with `AccessGate::open()` for an empty access slot and
    `SigningGate::none()` for an empty signing slot. `null` reaches the bus as "the aggregate writes the
    neutral pair".
- `src/F5Sign/Envelope/UI/Http/Request/AddRecipientRequest.php`:
  - `$auth` (`?AuthRequirementRequest`), `$claimable` (bool), `$signs_via`.
  - The `$signs_via` description says `MACHINE_KEY` requires the neutral pair: omit `auth`, or send it with
    neither gate declared.
- `src/F5Sign/Envelope/Domain/Entity/Recipient.php` (constructor): a delegated `signs_via` requires
  `access->isOpen() && signing->isNone()` and throws otherwise. Unchanged.
- `src/F5Sign/Envelope/Contract/Type/RoleStanding.php`: `of(Role)` classifies every role as `BLOCKING`,
  `INFORMATIONAL` or `NOT_BUILT`. `IN_PERSON_HOST` and `CERTIFIED_DELIVERY` are `NOT_BUILT`: they are refused
  at `send()` (`RECIPIENT_ROLE_NOT_BUILT`) and never face a gate. Census the members from the enum, not from
  this line.
- `tests/F5Sign/Acceptance/OpenApiSpecTest.php` pins the enums of `AuthRequirementRequest.access_methods[]`,
  `signing_methods[]` and the two scalars, and the read side's `Recipient.auth.*`.
- `tests/F5Sign/Support/SeedsSentEnvelopes.php` and every Application-tier test dispatch `AddRecipient` with
  `authRequirement: null`. That is why the rule lives at the edge only (AC-9).
- Read side: `EnvelopeJsonPresenter`'s `auth` block publishes `access_methods: []` for an open gate. The
  signer's route-3 descriptor (`GetAuthDescriptorController`) publishes `access_gate: null` for it. Both stay
  as they are (AC-10).
- About 25 test files POST add-recipient bodies, and most send no `auth`. There is no shared builder. The
  per-file helpers are the places to change, for example `RecipientCorrectionHttpTest::addRecipient()`, which
  already takes an optional `$auth`.

## 3. Scope

**In**

1. `auth` with an access declaration is required on add-recipient for every recipient whose role is not
   `NOT_BUILT` and whose `signs_via` is not `MACHINE_KEY`. "Access declaration" means either
   `auth.access_method` or a non-empty `auth.access_methods`. Its absence is a 422 whose violation points at
   `auth.access_methods`. ⚑ The rule needs `role`, `signs_via` and `auth` together, so it is an `Assert\Callback`
   on `AddRecipientRequest` (beside `validateAccessCodeHasAGate`), building the violation with `atPath`:
   `AuthRequirementRequest` sees one slot at a time and is not reached at all when `auth` is null. ⚠ Do not copy
   that neighbour's reading of the declaration: it reads the scalar spellings only (§6).
2. `DIRECT_LINK` becomes accepted on the access slot, as the scalar or as a list of one, and maps to
   `AccessGate::open()` in `requirementFrom()`. It stays refused in a list of two or more (the existing list rule
   already refuses any member that delivers no code), on the signing slot, and with `signs_via: MACHINE_KEY`
   (a cross-field rule, so it sits in the same `AddRecipientRequest` callback). ⚠ Two refusals stand in the way
   today, and both must be bypassed, not only the first:
   - `validateAccessSlot()` refuses `DIRECT_LINK` in its own branch, and then again in the following `elseif`
     (`establishableWithoutSession()` is false for it).
   - `AccessGate::requiring()` throws for `DIRECT_LINK` in the domain, which would surface as a 400. So
     `requirementFrom()` routes it to `AccessGate::open()` before ever calling `requiring()`.
3. The signing slot is unchanged: optional, and absent means `SigningGate::none()`.
4. `signs_via: MACHINE_KEY` keeps omitting `auth`, or sending it with neither gate declared.
5. The `#[OA\*]` strings, the `OpenApiSpecTest` pins and the documentation surfaces listed in AC-11.
6. Every HTTP test that authors a recipient sends an explicit access declaration.
7. ADR-0082 (Proposed), and a frontend handoff for the dashboard.

**Out**

- The read model, and the signer's descriptor: an open gate still reads `access_methods: []` and
  `access_gate: null` (AC-10). Echoing `DIRECT_LINK` there changes the meaning of `null` for the signer and for
  the audit trail's assurance test, so it would be a task of its own.
- A request-only `NONE` for the signing gate: weighed and dropped (§4).
- Editing gates after authoring: TASK-064.
- The bus command and the aggregate: `AddRecipient` with `authRequirement: null` still writes the neutral pair.

Concepts re-cut: "an open gate is said by omission", "one spelling per concept" (the spelling changes from
absence to `DIRECT_LINK`), "omit `auth` for the default", `validateAccessSlot` (its `DIRECT_LINK` refusal),
`requirementFrom` (null on empty slots).

## 4. Key decisions

1. **The access gate only.** The access gate decides who gets in. A forgotten signing gate asks nothing more
   of a party who already passed a declared door.
   - `DIRECT_LINK` is a true statement at the access gate: holding the link is what admits. It would be a false
     one at the signing gate ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §7.4), so the
     signing gate keeps its absence.
   - The owner first considered a request-only `NONE` for the signing gate. All four reviewers of the options
     recommended against it: it is a wire token outside the catalog and it does not reach the incident, so it
     was dropped.
2. **The edge, not the domain.** The domain already has one value for an open gate, `AccessGate::open()`.
   - What was missing is a way for the request to say that the sender meant it. Mapping `DIRECT_LINK` to that
     value in `requirementFrom()` keeps one meaning inside, and gives one spelling on the wire again, because
     the absence is now refused.
   - This keeps ADR-0049 §7.4's reasoning intact: no catalog member is added and no illegal pair becomes
     writable.
3. **Keyed on properties, not on a list of roles.** The rule exempts a recipient for two reasons only:
   - their `signs_via` is delegated, so a declared gate is impossible;
   - their role is `NOT_BUILT` (`RoleStanding`), so no gate exists yet.

   A hand-written list of roles is what the repo's authoring rule 5 warns against. The test iterates
   `Role::cases()` and fails on an unclassified member.
4. **Alternatives weighed on 2026-10-20 and not taken here:**
   - **A dashboard-side fix alone:** it relies on the client being right, which is the failure.
   - **A read-model warning:** it cannot tell a chosen open door from a mistaken one, so it fires on every
     deliberate open recipient for ever.
   - **Narrowing the gates at the claim:** it covers slots only. TASK-064 covers it.
   - **Dropping unreachable methods automatically at the claim:** it is the incident's own shape, a silent
     weakening.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | An add-recipient with no access declaration is refused with 422, violation at `auth.access_methods`, and writes nothing (members AC-1a…c) | owner | Acceptance | accept a null `auth` |
| AC-2 | `DIRECT_LINK` on the access slot is accepted and the recipient is stored with `AccessGate::open()`, exactly as an omitted `auth` was before this task (members AC-2a scalar, AC-2b list of one) | owner | Acceptance + Unit (`requirementFrom`) | map `DIRECT_LINK` to a declared gate |
| AC-3 | The signing slot stays optional: an access declaration with no signing declaration stores `SigningGate::none()` | owner | Acceptance | require the signing slot |
| AC-4 | `signs_via: MACHINE_KEY` with no `auth` is still accepted, and so is `auth` with neither gate declared | owner | Acceptance | drop the delegated exemption |
| AC-5 | `DIRECT_LINK` with `signs_via: MACHINE_KEY` is refused with 422: a delegated act has no link | derived — ADR-0055 | Acceptance | accept it as the neutral pair |
| AC-6 | `DIRECT_LINK` in a list of two or more on the access slot is refused with 422 | derived — ADR-0054 | Unit (`AuthRequirementRequest`) | let the list rule skip `DIRECT_LINK` |
| AC-7 | `DIRECT_LINK` on the signing slot is still refused with 422 (scalar and list) | derived — ADR-0049 | Unit | drop the signing-slot refusal |
| AC-8 | The rule is a predicate over `RoleStanding` and `signs_via`: every `Role::cases()` member is classified, a `NOT_BUILT` role may omit the access declaration, and every other role may not (members AC-8a…g, one per role) | derived — rule 5 | Unit (census) + Acceptance | exempt a role by name |
| AC-9 | The bus command and the aggregate are unchanged: `AddRecipient` dispatched with `authRequirement: null` still writes the neutral pair | derived — tests/F5Sign/Support/SeedsSentEnvelopes.php | Application | move the rule into `AddRecipientUseCase` |
| AC-10 | Recipients authored before this task, and the read model, are unchanged: an open gate reads `access_methods: []` in the envelope read and `access_gate: null` in the signer's descriptor | derived — rule 6 | Acceptance | echo `DIRECT_LINK` on the read side |
| AC-11 | The published contract and the prose say the new rule (members AC-11a…c) | derived — rule 1 | Acceptance (`OpenApiSpecTest`) + review | leave an "omit `auth`" sentence |
| AC-12 | A frontend handoff tells the dashboard the body change, the 422 and the `DIRECT_LINK` spelling, with before and after request examples | derived — docs/frontend-handoff/README.md | review | — |
| AC-13 | ADR-0082 is drafted as Proposed with the three `docs/adr/README.md` edits, and ADR-0049, ADR-0054 and ADR-0057 carry the amendment notes | derived — rule 7 | review | — |

<!-- OFFREPO: the `wt-backend` lane is a target of the f5sign-infra Makefile; its one relevant fact is restated in the line below. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane: an ephemeral stack (its own PHP
  container, Postgres cluster and broker) that mounts this worktree's tree rather than the main checkout's.

**Notes on AC-2** — AC-2a: `access_method: "DIRECT_LINK"`; AC-2b: `access_methods: ["DIRECT_LINK"]`. Both read back
exactly as a recipient authored with no `auth` before this task.

**Notes on AC-1**
- AC-1a: no `auth` key.
- AC-1b: `auth` with `access_method` null and `access_methods: []` (for example only a signing gate, or only
  `selection`).
- AC-1c: the incident's body: `claimable: true`, `role: SIGNER`, no `auth`.
- Each refusal leaves the envelope's recipient count unchanged.
- Owner said: "que siempre haya que enviar auth y que si la queremos abierta sea Direct_link".

**Notes on AC-8** — census from `RoleStanding::of()`, one sub-id per member:
- AC-8a `SIGNER`, AC-8b `APPROVER` (blocking): the access declaration is required.
- AC-8c `VIEWER`, AC-8d `REVIEWER`, AC-8e `EDITOR` (informational): required.
- AC-8f `IN_PERSON_HOST`, AC-8g `CERTIFIED_DELIVERY` (not built): may omit it. The sabotage is to replace the
`RoleStanding` test with a list of names and drop one member; the census test must then fail naming it.

**Notes on AC-11**
- AC-11a: the schema's `required` set stays `['step_ordinal', 'role', 'notification_channels']`, which
  `OpenApiSpecTest` pins: the rule is conditional on role and `signs_via`, so a static `required: auth` would
  publish a contract that refuses bodies the endpoint accepts. The `$auth` and `access_method(s)` descriptions
  state the conditional rule and its 422, and no longer say "refused" for `DIRECT_LINK` on the access slot.
- AC-11b: the prose surfaces are swept: `AuthRequirementRequest` (class docblock, schema description,
  `access_method` / `access_methods` OA text, the `validateStructuralRules` comment), `AddRecipientController`
  (the `requirementFrom` docblock and the comment above its call), `AddRecipientRequest` (`$auth` and
  `$signs_via` OA), the test docblocks that say "null for the neutral pair", `docs/ddd/`,
  `docs/frontend-handoff/`, and the ADR bodies named in AC-13.
- AC-11c: the closing sweep is `rg -n 'by omission|omit.*auth|Omit the object|neutral pair|one spelling' src tests docs config`,
  run after the last change of the branch and read for relevance and tense. It matches about 60 files on
  `develop`, many of them unrelated ("neutral pair" is common domain and test prose; `CredentialKind`,
  `EventReplayOutcome`, ADR-0044 and ADR-0048 are about other omissions). Besides the files named here, likely
  candidates are `AccessGate.php`, `Recipient.php`, `RecipientView.php`, `config/packages/nelmio_api_doc.yaml`,
  `docs/LIVE_SCHEMA.md`, ADR-0053, ADR-0055 and `docs/adr/README.md`.
  `AuthRequirementRequestTest` asserts the old message ("an open gate is said by omitting the field") for
  `['OTP_EMAIL','DIRECT_LINK']`. The violation path still holds through the list rule; the message and its
  rationale change.
  Among those it must change: `AuthRequirement.php`, `SeedsSentEnvelopes.php` (as a description of the bus, which
  stays true), `AddRecipientRequest.php`, `AuthRequirementRequest.php`, ADR-0049 §2.1.

## 6. Open follow-ups (track, don't solve here)

- **The signing gate stays silently optional.** A client that drops only the signing gate still authors a
  recipient who signs with no per-act challenge. The reviewers judged it lower risk: no stranger enters through
  it. What would force it: a second incident on that side. The shape kept in reserve is a request-only `NONE`
  mapped at the edge, never a catalog member. Its `docs/BACKLOG.md` row is BL-434.
- **`AddRecipientRequest::validateAccessCodeHasAGate` reads only the scalar spellings.** A body that declares
  `ACCESS_CODE` in `access_methods` (the plural) and sends `access_code` is refused today although the gate
  declares it. Found by the claims check of 2026-10-20; not this task's change, and the new callback must not
  inherit it. Its `docs/BACKLOG.md` row is BL-435.
- **The declaration is enforced at the HTTP edge only.** A future non-HTTP caller of `AddRecipient` (an importer, a
  template) would author an open gate by omission with nothing to catch it (ADR-0082 sections 2.5 and 7.6; the
  security audit's warning). Its `docs/BACKLOG.md` row is BL-436.
- **The dashboard should stop trimming declared methods to the contacts it has.** That trim was the incident's
  origin. It is the dashboard's to change, and the handoff (AC-12) says so.

## 7. Deviations & honest notes

### Scope
- None. The diff stays inside §3: the request DTOs, the controller, their `#[OA\*]` strings, `OpenApiSpecTest`, the Acceptance tests that author recipients, and the prose that said an open gate is said by omission. The domain, the bus command and the read model are untouched.

### Decisions made during implementation
- The rule sits on `AddRecipientRequest` (it needs role, `signs_via` and `auth` together); `AuthRequirementRequest` only learns to accept `DIRECT_LINK` alone on the access slot, and the controller maps `[]` / `[DIRECT_LINK]` to `AccessGate::open()` before `AccessGate::requiring()`, which still refuses it. Expand-then-contract: the acceptance landed before the refusal.
- Slice 06 moved one `RecipientAuthHttpTest` data row ("declared on the signing gate only") from a null access method to `DIRECT_LINK`: same stored gate, same read-back.
- Slice 07, round 1: the `signing_methods` description had inherited "required" and `DIRECT_LINK` through "Same rules as access_methods"; fixed. The read-model text in `nelmio_api_doc.yaml` moved to slice 09.
- Slice 09's sweep found ADR-0077 section 2.9 and the TASK-031 handoff stating the empty access list as present fact. ADR-0082 now also amends ADR-0077 section 2.9 on the wire.
- Slice 06 ran the Acceptance tier directly on the lane (342 tests OK) rather than through `test-runner`. A filtered run in slice 07 hung 1800 s on a parse error the implementer introduced and fixed; the orchestrator re-ran the four affected classes green (42 tests).

### Decisions that needed an ADR
- [ADR-0082](../adr/ADR-0082-the-access-gate-is-always-declared.md), drafted as Proposed while planning and **accepted by the owner on 2026-10-20**. It amends ADR-0049 section 2.1, ADR-0054, ADR-0057 section 2.13 and ADR-0077 section 2.9. Its Status / Enforced by / Realized in move to Accepted in the orchestrator's commit, naming `AddRecipientRequest::validateAccessIsDeclared()`, `AuthRequirementRequest::validateAccessSlot()`, `AddRecipientController::accessGateFrom()` and the tests below.

### Declared and unproven properties
- AC-11c, AC-12 and AC-13 are review-tier rows (a sweep, the dashboard handoff, the ADR landing) with no test by nature; they were verified by the slice 08/09 reviews and the closing review. `task-validate` reports them uncited: expected.
- AC-4: the "auth with neither gate declared" half is asserted at Unit (`AddRecipientRequestTest`) only, not at Acceptance as the criterion's tier says.
- AC-6 was green before its fix (the list rule already fired at the same index); it is pinned by sabotage (the list rule skipping `DIRECT_LINK`), not by a red-before-fix.
- AC-10: the descriptor half (`access_gate: null`) is held by `GatedSigningCeremonyHttpTest`, seeded over the bus and not citing the criterion: a `DIRECT_LINK` recipient stores exactly the neutral pair, so no new test could separate them.
- `OpenApiSpecTest`'s `assertStringContainsString('DIRECT_LINK', $auth)` pin is vacuous (the enum already contains it); the other pins discriminate.
- The incident regression's open-door case stops at `AUTH_PASSED`, as the slice asked, not at a signed act.
- Security audit (warn, by design): the declaration is enforced only at the HTTP edge (ADR-0082 sections 2.5 and 7.6). See BL-436.
- **Infection** (filtered to the branch's 7 `src/` files, which it mutates whole; bars 85 covered-MSI / 70 MSI), `wt-backend-infection` on this worktree's lane, tip `e9ae6f53`: 736 mutants, 191 killed, 430 escaped, 115 not covered — covered-MSI **30.8 %**, MSI **26.0 %**, both below the bars. The whole-file numbers measure the untouched parts of the touched files (362 of the 430 escapes are `Concat` mutants on `#[OA\*]` strings and validation messages nobody asserts), which is the pre-existing debt of BL-409, not this task's code. Judged on the changed lines (`infection-changed-lines.py --base develop`): 40 escaped, 0 not covered, 1 skipped. **Eight were missing tests**, killed in `60a4bb78`, each mutant applied by hand and its test seen red: an unknown `signs_via` with no `auth` must be a violation, not an `Error` (`AddRecipientRequest::validateAccessIsDeclared()`'s null-safe call); both refusal messages pinned verbatim, because the dashboard handoff quotes them; and `AddRecipientController::accessGateFrom()`'s empty-list and non-`DIRECT_LINK` arms. **Justified:** `validateAccessIsDeclared()`'s `PublicVisibility` is equivalent (Symfony's `CallbackValidator` invokes it through `ReflectionMethod::invoke`, as for the older `validateAccessCodeHasAGate`); the `ReturnRemoval` after the delegated `DIRECT_LINK` violation is equivalent (falling through reaches `$declared`, true for `DIRECT_LINK`, and adds no second violation); the 30 `Concat` mutants on `AuthRequirementRequest`'s `access_methods` `#[OA\Property]` description only reorder its text, and `OpenApiSpecTest` pins its substrings, not their order. Re-run on `AddRecipientRequest.php` and `AddRecipientController.php` at `60a4bb78`: on the changed lines only the two equivalent mutants survive.

### Debt left behind, and where it lives now
- The signing gate stays silently optional: section 6 and BL-434.
- `validateAccessCodeHasAGate` reads only the scalar spellings: section 6 and BL-435.
- A non-HTTP caller of `AddRecipient` would author an open gate by omission: BL-436.
- The dashboard still trims declared methods to the contacts it has: the dashboard's to change; the handoff says so.

### Delegated work
- No slice delegated to the `replicator` (every slice report says none; no shape had three or more targets).
- Slices: 02 critical (opus, 0 rounds, DONE_WITH_CONCERNS then approved); 03-05 mechanical (sonnet, 0 rounds); 06 critical (opus, 0 rounds, concerns then approved); 08 standard (sonnet, 0 rounds); 01 mechanical (sonnet, 0 rounds); 07 standard (sonnet implementer, opus review, 1 round); 09 standard (sonnet, 1 round, verified by the orchestrator); 10 follow-up fixes.

### Cost of the run
- Implementers: opus on the two critical code slices (02, 06); sonnet on the other nine (01, 03–05, 07–11).
- Reviewers: opus on 02, 06, 07 (two rounds), 10 and the closing review; sonnet on 01, 03–05 (one joint review), 08, 09.
- Fix rounds: 07 one (a published `signing_methods` string inheriting the access rules), 09 one (the ADR-0077 relation unrecorded); the closing review added slice 10, Infection added slice 11.
- Escalations: none. One filtered run hung 30 minutes on a parse error introduced and fixed inside slice 07.
- Elapsed: about 5 h 15 min, from preparation (18:20) to the Infection re-run.
