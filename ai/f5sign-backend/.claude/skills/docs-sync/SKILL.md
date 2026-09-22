---
name: docs-sync
description: 'Updates the documentation that lives outside the code after a task: the domain models in docs/ddd/ (living docs), docs/LIVE_SCHEMA.md, docs/ARCHITECTURE.md, CLAUDE.md when the stack changes, the variables in .env/.env.dev/.env.test under repo rule 4, and ADRs — which it ALWAYS drafts as Proposed and never treats as accepted without the user. Does NOT touch OpenAPI (Nelmio covers it inline). Conditions on what the diff touches, not on tags. Use it with /docs-sync TASK-NNN. Trigger with "sync docs", "update the domain model", "draft ADR", "external docs for task".'
---

# Docs Sync

Documentation outside the code. Not a hard gate; failures are warnings.

⚑ **Half of the targets this skill used to have do not exist in this repo.** Measured 2026-08-17: there
is no `CHANGELOG.md`, no `.env.example`, no `docs/asyncapi/`, no `docs/runbooks/`, and no
`src/*/README.md`. **Creating a documentation surface is a decision, not a sync** — if it's missing and
needed, report it and file it in BACKLOG; don't invent it mid-task.

## Invocation

```
/docs-sync TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` and `context-digest.md`
- The task's `.md`
- From the repo: [`docs/adr/`](../../../docs/adr/), [`docs/ddd/`](../../../docs/ddd/),
  [`docs/LIVE_SCHEMA.md`](../../../docs/LIVE_SCHEMA.md),
  [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md),
  [`docs/BACKLOG.md`](../../../docs/BACKLOG.md), [`CLAUDE.md`](../../../CLAUDE.md), `.env*`

## Outputs

- Repo files modified, in **their own commit** (not `--amend`: this repo integrates multi-commit PRs)
- `var/task-runner/TASK-NNN/docs-sync.report.md`
- JSON: `{"status":"pass|warn","summary":"...","filesUpdated":[...],"surfacesAbsent":[...]}`

## What runs, based on what the diff touches

**There are no tags in this task format.** The condition is the diff.

### The diff touches `src/F5Sign/<BC>/Domain/` or changes a flow → that BC's domain model

⚠ **The filename is not derived from the directory**: `Session/` → `signing-session-domain-model.md`,
`IdentityAccess/` → `identity-access-domain-model.md`, `SignatureExecution/` →
`signature-execution-domain-model.md`. Run `ls docs/ddd/` instead of building the lowercase name.

Domain models are **living documents**: they get updated in place and their trail is git
([`docs/adr/AUTHORING.md`](../../../docs/adr/AUTHORING.md) § ADRs vs domain models). ADRs are the
opposite, point-in-time.

- Update the affected BC's model with the current state.
- ⚑ **If an ADR in this changeset supersedes part of a model**, don't rewrite the model on the ADR's
  branch: put a **dated banner** on the obsolete part pointing to the ADR, and let the model's next
  feature reconcile it. The contract is in [`docs/ddd/README.md`](../../../docs/ddd/README.md) §
  Document lifecycle.

### The diff touches `migrations/` → `docs/LIVE_SCHEMA.md`

- Update it, and **say where it was re-derived from** (the migration, or a query against the schema).
- ⚠ It's **database fact transcribed by hand**, i.e. the one kind of claim a document can't keep true on
  its own: already filed as such (`BL-99`). If what's touched is large, the report must say it was
  transcribed by hand and what wasn't verified.

### The diff adds or changes an environment variable → `.env`, `.env.dev`, `.env.test`

⛔ **`.env.example` does not exist and is not created.** The discoverability surface is the load-order
header of `.env`, which **names the variables in prose**.

⛔ **And for a sensitive variable, a placeholder is the wrong answer.** `.env` ships **inside the
production image**, so a key named there **always resolves** and production would boot with the
committed value. The `.env` header says it literally: *don't fix that absence by committing a
placeholder*. The two patterns from repo rule 4, and the first is the standard one:

| Pattern | When | Examples |
|---|---|---|
| **(A) Absent** — the standard | Always, except (B) | There are **six**, and the `.env` header names them: `DATABASE_URL`, `APP_SECRET`, `MESSENGER_TRANSPORT_DSN`, `SIGNING_TOKEN_SECRET`, `IDENTITY_DATABASE_URL` and `PROVISIONING_DATABASE_URL` (the last two arrived with Identity & Access; `CLAUDE.md` still lists only four). `%env()%` fails building the container instead of falling back to a dev password |
| **(B) Present and empty** — narrow exception | Only if an empty value can **never** work *and* its consumer rejects it | `FIELD_ENCRYPTION_SECRET=` only. **Not transferable**: `SIGNING_TOKEN_SECRET` has a dev value in `.env.dev`, so empty wouldn't fail closed |

Add the variable to the matching environment file (local-stack values do go in: they match infra's
compose and aren't secrets), and **name it in the `.env` header** if it's one of the absent ones.

### The diff changes the stack, a bundle, a composer script, or a make target → `CLAUDE.md`

⚑ **It's the repo's highest-value surface and the one that does the most damage when it rots**, because
it doesn't just go stale: it starts **giving bad instructions**, and the next agent rebuilds what you
removed. It declared *"Doctrine ORM 3"* for weeks after it left `composer.json`. It's always in scope
for authorship rule 1's sweep.

### The diff adds a BC, a layer, or changes a decision path → `docs/ARCHITECTURE.md`

Its question→document routing table is what someone new reads. If the map changed, it changes.

### There's a cross-cutting decision → an ADR, and **only as `Proposed`**

⛔ **This skill does not accept decisions.** It drafts; the user accepts. It fully inherits
`implement-backend`'s Step 2b gate:

- **The status vocabulary is `Proposed` · `Accepted` · `Superseded`.** There's no `draft`. And
  **`Accepted` means exercised, not agreed**: writing it here misrepresents the repo's state.
- **No `Origin: T{id}` and no invented headers.** The header is the `| Field | Value |` table with
  `Status` · `Date` · `Relates to` · `Crosswalk`, and the sections are `AUTHORING.md` § Section
  template's: `Context`, `Decision`, `Consequences` (with **Positive / Negative / Risks** — Risks isn't
  optional), `Related ADRs`, `Enforced by (in-repo)`, `Realized in (in-repo)`, and `Counterpoint` when
  there's a credible alternative.
- **The number is minted with `AUTHORING.md`'s sweep, run at that moment and from the repo root**
  (`cd "$(git rev-parse --show-toplevel)"`, pathspec `':(top)docs/adr'`), across **all** branches. "The
  highest one there is + 1" looking only at the working tree is how collisions get minted:
  `AUTHORING.md` records two ADR-0040s, and `ADR-0049` showed up on another branch mid-session.
- **Landing means landing completely: FIVE places.** The three in `docs/adr/README.md` (index, graph,
  crosswalk) plus the header's `Crosswalk` field; **plus** the two `AUTHORING.md` calls *"each
  conditional but each easy to forget"*: the `(ADR-NNNN)` reference in the docblocks of the code it
  governs, and **the domain model reconciliation** in `docs/ddd/` with its status row in
  `docs/ddd/README.md`. That last one is yours by definition: this skill is the one that maintains the
  models.
- **Present it to the user** with what it decides, what it discards, and what it forbids, and **stop**
  until they respond.

### The diff changes something the frontend consumes → `docs/frontend-handoff/`

**Why it exists.** Workspace rule 4 forbids crossing repos in the same commit: *two projects = two
coordinated PRs*. So a backend contract change and its adoption in `f5sign-dashboard` / `f5sign-signer`
are different changesets, and without a handoff artifact the second one gets rebuilt by guessing —or
never arrives, which is what happened with `signed_copy_url`: the signer frontend has been hiding its
download button ever since because it expects a field the backend never sends, and that lived only in an
email-channel docblock when this was written — today it's also in
`docs/ddd/notification-domain-model.md` and in the handoff README. (Leaving the correction visible
because it's authorship rule 2 in action: the *why* was still true and the factual half had rotted.)

**When it's written** — predicate, not tags. The diff touches `src/**/UI/Http/`, `config/routes/`, any
`#[OA\`, a `Contract/` the API emits, an enum whose values go out through the API, a CORS header or
rule, or an environment variable the frontend needs.

**Where:** `docs/frontend-handoff/TASK-NNN-<slug>.md` (or `YYYY-MM-DD-<slug>.md` if the change doesn't
come from a task). Full convention in
[`docs/frontend-handoff/README.md`](../../../docs/frontend-handoff/README.md).

⚠ **And here's an explicit exception to the rule above**, so it doesn't look like a contradiction: the
directory and its README were born on branch `docs/task-conventions` and **may not exist on the branch
you're working on**. Writing the first handoff there **does** create the surface — and it's authorized,
because the decision is already made and its convention written. What the rule forbids is inventing a
surface **without a prior decision**; this one has one. If the README isn't on your branch, say so in
the report and link to the branch that has it.

**What it carries, and the form matters because the reader is an agent in another repo with no access to
this one:**

```markdown
# Handoff to frontend — {what changed, in one sentence}

| | |
|---|---|
| **Origin** | branch `feat/...` · commit `<sha>` · {PR if it exists} |
| **Date** | YYYY-MM-DD |
| **Repos affected** | dashboard / signer / both |
| **Nature** | additive · **breaks contract** · fixes the spec |
| **Action required** | none · update types · handle new state · **migrate before {date}** |

## What changed in the contract
- `{METHOD} {route}` — {what field/state/code appears or disappears}, and **whether it's required**

## What the frontend needs to do
1. {concrete step, imperative}

## What is NOT ready yet
- {so nobody builds against a half-finished seam}

## How to verify it from the frontend
- {concrete call, or "regenerate the spec and diff it": the generated OpenAPI is the machine truth}
```

**Three anti-rot rules**, because this document is the kind that goes stale fastest:

1. **Don't copy the spec.** The OpenAPI Nelmio emits is the machine-readable truth; here you say **what
   changed and what to do**, and point to it. A hand-duplicated schema will diverge and the frontend
   will believe the wrong one.
2. **Name the origin commit.** It's the only thing that lets the frontend agent know whether the handoff
   is already applied or is behind.
3. **Say what isn't ready.** Half the value is in stopping work against an incomplete seam —the
   `signed_copy_url` case is exactly that: the bytes are already reachable, a field is missing, and so
   is **the decision of which end adds it**, which can't be made from inside this BC.

⚑ **This file does not authorize touching the other repo.** It's written here, it travels with this PR,
and the frontend's change is its own PR in its own repo.

### Surfaces that don't exist → warn, and file it if needed

`CHANGELOG.md`, `.env.example`, `docs/asyncapi/`, `docs/runbooks/`, `src/*/README.md`.

Don't create any of them. Report in `surfacesAbsent` what was left undocumented and where that
information lives in the meantime (e.g. events live in their `Contract/Event/` classes and in the ADR
that governs them). If the absence is a real, recurring gap, **a row in `docs/BACKLOG.md`** with the id
re-derived by grep at that moment — not a half-filled phantom file, which is worse than nothing because
it looks like coverage.

## Report

```markdown
# docs-sync — TASK-NNN

**Status:** {PASS|WARN} · **Files updated:** {N}

## Changes applied
- {file}: {what}

## ADRs drafted
- ADR-NNNN — **Proposed**, pending user acceptance. Landing checklist: {3 README edits
  + Crosswalk field} {done|pending}

## Absent surfaces (not created on purpose)
- {e.g. docs/asyncapi/: event X is left undocumented; it lives in its Contract/Event/ class and in ADR-NNNN}

## Transcribed by hand and unverified
- {e.g. LIVE_SCHEMA.md: columns of table Y}
```

## What it does NOT do

- **Does not touch OpenAPI** — Nelmio covers it inline, in the code's annotations (`implement-backend`
  Step 4).
- Does not edit the task's `.md` (that's `task-close`).
- Does not write the PR body (`pr-ready`).
- **Does not mark any ADR as `Accepted`**, and does not proceed without the user's response.
- Does not create documentation surfaces the repo doesn't have.
- Does not "improve" documentation outside the task's scope — except for prose that authorship rule 1
  requires fixing in the same changeset.
