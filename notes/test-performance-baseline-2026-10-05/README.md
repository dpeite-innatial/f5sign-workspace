# Backend test-suite performance baseline — 2026-10-05

Starting point for any future attempt to speed up the f5sign-backend suite. Nothing was changed;
this is a measurement only.

## The run

- **Tree:** f5sign-backend `679e1a77` (develop, after merging `refactor/persistence-incremental`).
- **Harness:** `make -C ../f5sign-infra wt-backend-test src=<main checkout> args="--log-junit var/junit.xml"`
  (ephemeral lane, its own Postgres/MinIO/RabbitMQ; eu-dss real).
- **Result:** OK — 5911 tests, 70124 assertions, 0 failures/errors/skipped.
- **Time:** 9m28s PHPUnit runtime · 11m14s wall-clock (≈1m45s is lane start-up/teardown).
  A second run the same day (full gates) gave 8m28s PHPUnit, so expect ±1 min of noise.
- **Machine:** WSL2 + Docker Desktop, 16 CPUs, ~14 GB for Docker. opcache CLI off, Xdebug loaded with
  `mode=off` (`f5sign-infra/docker/php/php.ini`, `xdebug.ini`).

Files here: `junit.xml.gz` (the raw JUnit log) and `per-class.csv` (seconds, tests, avg ms per class).

## Where the time goes (sum of testcase times = 564 s)

| Tier | Time | % | Tests | Avg |
|---|---|---|---|---|
| Acceptance | 331.0 s | 58.7 % | 271 | 1221 ms |
| Integration | 204.0 s | 36.2 % | 732 | 279 ms |
| Unit | 17.6 s | 3.1 % | 4144 | 4 ms |
| phpstan rules | 5.7 s | 1.0 % | 26 | 220 ms |
| Application | 5.5 s | 1.0 % | 698 | 8 ms |

- 139 tests take >1 s and add up to 356 s (63 % of the total); 439 take >0.2 s and add up to 521 s.
- Top classes: `StepPolicyDeliveryBarHttpTest` 41.9 s (7 tests), `EnvelopeRootLockRaceTest` 34.7 s (13),
  `EnvelopeHttpTest` 24.8 s (40), `RecipientAuthHttpTest` 21.2 s, `AddFieldHttpTest` 20.4 s,
  `StepDeadlineBarsGhHttpTest` 20.0 s (3). Slowest single test: `ClosedNowEnvelopeTrailHttpTest` 11.1 s.
- The slow tests do real work, not sleeps: real PAdES signing through eu-dss (48 test files use it),
  real commits (`#[SkipDatabaseRollback]`, 79 files), relay pumping (`DrivesEventLogRelay`, 28 files),
  concurrent child `php` processes for the race tests. Only ~15 `usleep` calls exist, all short.

## Options assessed (none applied)

Same results:
1. **Shard Integration/Acceptance across 3–4 parallel lanes**, each with its own stack. Estimated
   ~3–4 min (not measured). Plain paratest on one cluster is NOT an option: `EventRelay` filters on the
   cluster-wide `pg_snapshot_xmin`, so one worker's open DAMA transaction stalls another's relay
   (BL-138). Infra change.
2. **Keep the lane up** (`wt-backend-up` … `wt-backend-down`): saves the ~1m45s start-up per run.
3. **`opcache.enable_cli` + `opcache.file_cache`** in the test container: helps the child `php`
   processes of the race tests. Expected small (5–10 %), unmeasured.

Change what is validated (rejected): mocking eu-dss, `APP_DEBUG=0` in test, rollback instead of real
commits in relay tests, excluding slow tests.

Unit + Application are already fast (23 s for 4842 tests) and run alone in the TDD loop (`fast=1`).

## Re-measuring

Run the same harness command, then compare per class against `per-class.csv`. Note the test count:
growth in tests alone moves the total.
