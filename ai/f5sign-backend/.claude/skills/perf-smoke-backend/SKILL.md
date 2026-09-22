---
name: perf-smoke-backend
description: 'Performance smoke test on the backend (PHP/Symfony). Its STATIC half runs today and is the useful one: N+1 by reading the code, an effective index for the new queries, heavy work (or network calls) inside a transaction or a lock, and synchronous work on the HTTP path that should go through Messenger. The DYNAMIC half (p95, throughput, memory) is not runnable: it depends on composer perf:seed, which doesn''t exist in this repo, and is reported as skipped with its reason, never as green. Emits warnings, doesn''t block. Only for repositories with a PHP/Symfony stack. Use it with /perf-smoke-backend TASK-NNN. Trigger with "smoke perf backend", "benchmark API PHP", "check N+1".'
---

# Perf Smoke (backend)

⛔ **The dynamic half is not runnable today.** It depends on `composer perf:seed`, which **doesn't
exist**: this repo's scripts are `test`, `coverage`, `coverage:text`, `coverage:clover`, `phpstan`,
`arch`, `lint`, `format`, `infection`, `qa` (check with `composer run-script --list`, don't trust
this list). Without fixtures there's no p95, no throughput, no comparable consumption, and
**`task-runner` skips it, declaring it in `run.log` as `skipped` with its reason — never as green**.

✅ **The static half does hold up, and it's the one that has paid off most in this repo.** It can be
done without fixtures:

- [ ] **N+1 by reading the code**: a loop that queries per element instead of one batched query.
- [ ] **Effective index for the queries the diff adds**: one whose prefix matches the actual `WHERE`
      (on tenant tables, starting with `tenant_id`), not just any index on the column.
- [ ] **Heavy work inside a transaction**: especially a network call inside a lock. ⚑ `BL-17` is open
      for exactly this — nothing bounds the lock window during DSS: `lock_timeout` and
      `statement_timeout` don't appear in `src/`, `config/` or infra, while the signing transaction
      spans N documents across DSS latency. If the diff widens that span, say so.
- [ ] **Synchronous work on the HTTP path** that should go through Messenger (repo rule 3).

The static half emits `warn`, it doesn't block. The dynamic half is reported as not run.

Performance smoke test. Invoked when the diff touches a hot path (query in a loop, long
transaction, worker, list endpoint). It is NOT a hard gate — it emits warnings.

## Invocation

```
/perf-smoke-backend TASK-NNN
```

## Precondition

⚠ **There's no `composer perf:seed` in this repo**, so fixtures are never loaded: the dynamic part
is reported `skipped` with that literal reason and only the static checks above run. It doesn't
block. Creating the seed is a decision (and a BACKLOG row), not something this skill improvises.

## Inputs

- `var/task-runner/TASK-NNN/changes.diff`
- `var/task-runner/TASK-NNN/context-digest.md`
- `var/task-runner/TASK-NNN/doctrine-guard.report.md` (if it exists; to correlate indexes)
- the task's `.md` (tags + overridden thresholds if declared)

Default thresholds (overridable in the `.md`):
- HTTP endpoint: p95 < 300ms → pass; 300-800ms → warn; > 800ms → warn high
- Worker: throughput ⚠ **no target: no file in `config/` defines a minimum throughput**, so this
  comparison has no right-hand side. Report the raw measurement, not a verdict
- Memory: endpoint < 50MB per request
(Frontend perf is measured with the `perf-smoke-frontend` skill in its own repo.)

## Outputs

- `var/task-runner/TASK-NNN/perf-smoke.report.md`
- `var/task-runner/TASK-NNN/perf-metrics.json`
- JSON:
  ```json
  {"status":"pass|warn|fail","summary":"...","issues":[...],"metrics":{"endpoints":{...},"workers":{...}}}
  ```

`status: fail` ONLY if the skill couldn't run (broken environment). Perf issues are always `warn`.

## Execution

### Step 1 — Detect what to measure

By tags and diff:
- If tag `api`: identify new/modified endpoints (search Controllers in the diff, extract paths)
- If tag `worker`: identify new/modified handlers
- No tags to validate: the entry condition is whatever the diff touches, and it's evaluated by
  whoever delegates.

If nothing is measurable → `status: pass`, `summary: "nothing measurable in the diff"`. No
`tagMismatches`: this format has no tags.

### Step 2 — Static query analysis (if there's persistence code in the diff)

- ⛔ **There's no Doctrine SQL logger to enable**: DBAL 4 retired the `SQLLogger` API in favor of
  middleware, the ORM was retired entirely (ADR-0018), and there's no WebProfiler. To count queries:
  instrument a DBAL middleware or read the Postgres log
- For each new endpoint: call it once against seed data
- Count executed queries; if > 5 when it should be 1 per collection → `warn` "suspected N+1"
- `EXPLAIN ANALYZE` on each new query:
  - Seq Scan on a table > 1000 rows → `warn`
  - Sort without an index → `warn`
  - Join without an index on the FK → `warn` (doctrine-guard should have caught it, but double check)

### Step 3 — Endpoint benchmark (if tag `api`)

For each new endpoint:
- **Warm-up:** 10 requests ignored
- **Measurement:** 100 sequential requests (not concurrent — this isn't a load test)
- Capture times in ms; compute p50, p95, p99, max
- Compare against thresholds (defaults or those declared in the `.md`)
- Result → metrics JSON

### Step 4 — Worker benchmark (if tag `worker`)

- Enqueue 50 test messages against the new handler
- Measure throughput (msg/s) and average time per message
- Compare against the project minimum

### Step 5 — Memory

- During endpoint execution, measure memory usage (`memory_get_peak_usage`)
- If > 50MB → `warn`
- If the code has `findAll`/`fetchAll` on large tables without pagination → `warn` "fetch without
  pagination"

### Step 6 — Fallback

⚠ **The dynamic tooling isn't there**: PHPBench isn't a dependency of this repo, and Lighthouse is
frontend (lives in `perf-smoke-frontend`, not here). Report `skipped` with the reason and stay on
the static half.

## Report

```markdown
# perf-smoke — TASK-NNN

**Status:** {PASS|WARN}
**Issues:** {N} warnings ({high}/{medium})

## Key metrics
- POST /api/v1/envelopes/{id}/close
  - p50: 145ms | p95: 312ms | p99: 480ms | max: 620ms
  - Queries per request: 8 (expected: ≤5)
- Worker SignEnvelopeHandler
  - Throughput: 12 msg/s (threshold: 10 msg/s) ✓

## Warnings
- [suspected N+1] GET /api/v1/envelopes/{id} runs 1+N queries when loading signers; consider a fetch join (high severity)
- [p95 near limit] POST /api/v1/envelopes/{id}/close p95=312ms, close to the 300ms threshold (medium severity)
```

## Return JSON

```json
{"status":"warn","summary":"2 warnings (1 high)","issues":[{"severity":"warn","category":"n+1","endpoint":"GET /api/v1/envelopes/{id}","message":"1+N queries"}],"metrics":{"endpoints":{"POST /api/v1/envelopes/{id}/close":{"p50":145,"p95":312,"p99":480}}}}
```

## Interaction with the loop

Never triggers an automatic retry. In supervised mode, if there's a high WARN, task-runner asks the
user whether to iterate or leave the technical debt documented in `notes.md` (picked up by
task-close).

## What it does NOT do

- It's not load testing (no concurrency, no spikes)
- Doesn't do line-by-line profiling (XHProf, Blackfire are done manually if the debt justifies it)
- Doesn't audit performance of untouched base code
- Doesn't optimize code — only detects

## References

- <!-- OFFREPO --> Original design (prototype, superseded): `Implementación/Skills de Ejecución de
  Tareas/backend/07 - Perf Smoke Backend.md`
- ⚠ **There's no task that provides `composer perf:seed`**: the earlier pointer (`T26.2.3`, legacy id
  format) resolves to nothing. Creating the seed is a decision and needs its BACKLOG row, which
  **doesn't exist today either**
