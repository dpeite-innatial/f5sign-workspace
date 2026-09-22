---
name: docs-sync
description: 'Updates documentation that lives outside the code after a task: AsyncAPI, ADRs (as draft), CHANGELOG, .env.example, worker runbooks, module READMEs. Does NOT touch OpenAPI (Nelmio covers it inline). Conditional on the adr/config/breaking/event/worker/new-module tags. Use it with /docs-sync T{id}. Trigger with "sync docs", "update changelog", "create ADR", "update AsyncAPI", "external docs for task".'
---

# Docs Sync

External documentation update. Not a hard gate; failures emit warnings.

## Invocation

```
/docs-sync T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/contract-check.report.md` (if tag `event`, to know which events to sync in
  AsyncAPI)
- The task's `.md`

From the repo (read if they exist):
- `docs/asyncapi/*.yaml`
- `docs/adr/*.md`
- `CHANGELOG.md`
- `.env.example`
- `docs/runbooks/*.md`
- `src/*/README.md`

## Outputs

- Files modified in the repo (amend to the existing commit)
- `var/task-runner/T{id}/docs-sync.report.md`
- JSON:
  ```json
  {"status":"pass|warn","summary":"...","filesUpdated":[...],"tagMismatches":[...]}
  ```

## Model selection

This skill can run with **Haiku** (default, for mechanical work) or **Sonnet** (when drafting an ADR).

If the task has tag `adr`: task-runner must invoke it with model=sonnet. For other tags: Haiku is
enough.

## Execution

Based on the `.md`'s tags, run the corresponding subsections. At the end, detect tag mismatches.

### Tag `adr` (requires Sonnet)

- Locate `docs/adr/` (create it if it doesn't exist)
- Determine the next number: highest existing NNNN + 1
- Kebab-case title derived from the task's title or from the main decision in
  `context-digest.md § Decisions made`
- Create `docs/adr/NNNN-title-kebab-case.md`:

```markdown
# ADR NNNN — {Title}

Status: draft
Date: {current date}
Origin: T{id}

## Context
{extracted from context-digest.md § Business rules and §/Decisions}

## Decision
{extracted literally or paraphrased precisely}

## Consequences
{positive and negative, inferred from the context}

## Alternatives considered
{if mentioned; if not, empty section or "Not documented"}
```

**Initial status `draft`.** A human promotes it to `accepted` in a later manual commit.

- Add an entry to the `docs/adr/README.md` index if it exists.

### Tag `config`

- Detect new/modified env vars in the diff:
  - Grep PHP files for `$_ENV`, `$_SERVER`, `getenv(`, `env(`
  - Grep `config/packages/*.yaml` and `config/services.yaml` for `%env(...)%`
- For each new var not present in `.env.example`:
  - Add: `VAR_NAME=placeholder-or-default`
  - Add a one-line comment above explaining what it is
  - If it's secret: placeholder like `CHANGE_ME` or `your-secret-here`
- If `docs/configuracion.md` or equivalent exists: update it if there's a corresponding section

### Tag `breaking`

- Add an entry to `CHANGELOG.md` under `## [Unreleased]` → `### Breaking`:
  - Format: `- **{area}**: {what changes} ({how to migrate})`
  - If it affects the public API: include a before/after example in a code block

If `CHANGELOG.md` doesn't exist: create it with the keepachangelog.com structure and add the entry.

### Tag `event`

- Review `docs/asyncapi/*.yaml` (there may be several files per bounded context)
- For each new/modified event (extracted from `context-digest.md § Domain events / Emits`):
  - Add/update `components.schemas.{EventName}` with a payload schema 1:1 with the PHP event's
    properties (Jakarta-style types: `type: string, format: uuid`, etc.)
  - Add/update `channels.{module}.{event-slug}` with `subscribe` or `operation`
  - If the event references a specific queue/topic (Messenger config), reflect it in the channel binding

If `docs/asyncapi/` doesn't exist: emit `warn` "AsyncAPI not present in the project, event {X}
undocumented" and continue. Don't create a phantom AsyncAPI.

- If a catalog exists (`docs/events-catalog.md`), add an entry.

### Tag `worker`

- Create/update `docs/runbooks/{worker-name}.md`:
  - Runbook name = handler name in kebab-case
  - Sections:
    - What it processes (which queue/message)
    - Start/stop (supervisor/systemd command)
    - Metrics to monitor (queue length, failure rate, p95)
    - Procedure for a stuck queue (DLQ, reprocessing)
    - How to reprocess failed messages

### Tag `new-module`

- Detect a new `src/{Module}/` directory in the diff
- If `src/{Module}/README.md` doesn't exist, create it:
  ```markdown
  # {Module}
  
  ## Purpose
  {2-3 lines extracted from context-digest.md}
  
  ## Aggregate roots
  {list}
  
  ## Dependencies on other modules
  {list, with a reference to Mapa de Módulos if applicable}
  
  ## Domain events
  - Emits: {list}
  - Consumes: {list}
  
  ## Entry points
  - HTTP endpoints: {list}
  - Async handlers: {list}
  ```
- Update `Arquitectura/Mapa de Módulos - Bounded Contexts.md` if it exists: add the new module to the
  list/diagram if applicable.

## Final step — Tag mismatches

For each processed tag: if relevant changes couldn't be generated because the diff doesn't contain
evidence of the change declared by the tag, add it to `tagMismatches`.

Examples:
- Tag `adr` but no discernible architectural decision can be extracted from the context-digest → `adr`
- Tag `config` but no new env vars were detected → `config`
- Tag `new-module` but there's no new directory under `src/` → `new-module`

## Final step — Amend to the commit

Run `git add` on the files touched by docs-sync (only the ones modified in this step) and
`git commit --amend --no-edit`. Preserves the "1 commit per task" rule.

## Report

```markdown
# docs-sync — T{id}

**Status:** {PASS|WARN}
**Files updated:** {N}
**Tags processed:** {list}

## Changes applied
- docs/asyncapi/envelope.yaml: added channel `envelope.closed` + schema
- .env.example: added DSS_TIMESTAMP_AUTHORITY_URL
- docs/adr/0012-tsa-fallback-strategy.md: created (status: draft)

## Skipped (with reason)
- AsyncAPI: docs/asyncapi/ not present in the project; event EnvelopeClosed undocumented

## Tag mismatches
- {list or "none"}
```

## Return JSON

```json
{"status":"pass","summary":"3 files updated, 1 ADR created as draft","filesUpdated":["docs/asyncapi/envelope.yaml",".env.example","docs/adr/0012-tsa-fallback-strategy.md"],"tagMismatches":[]}
```

## What it does NOT do

- **Does not touch OpenAPI** (Nelmio regenerates it inline)
- Does not edit the task's `.md` (that's task-close)
- Does not write the PR description (pr-ready)
- Does not create docs not requested by tags
- Does not "improve" existing documentation outside the task's scope

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/common/05 - Docs Sync.md`
- API docs strategy: `memory/project_api_docs_strategy.md`
