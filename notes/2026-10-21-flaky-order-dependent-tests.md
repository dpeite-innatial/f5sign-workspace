# Two backend tests that fail intermittently in random order (2026-10-21)

Found while optimising the infra infection gate. Not fixed: the gate now runs PHPUnit in default order
(`--order-by=default`, f5sign-infra `4df531b`), so it no longer trips on them, but the dependency is real.

## The two failures

| Test | Assertion that failed |
|---|---|
| `tests/F5Sign/Integration/ChannelChangeReinvitesCrossingTest.php::a_sent_recipient_is_not_reinvited_and_a_failed_one_is` | line 143: expected deliveries `[EMAIL, SMS]`, got `[SMS, EMAIL]` (`ORDER BY n.requested_at, d.position`) |
| `tests/F5Sign/Integration/StorageLifecycleScenarioTest.php::bytes_are_staged_promoted_and_destroyed_on_the_clock_the_platform_undertook` | line 842 (from 490): `versionExists($superseded)` is true — the staging copy's version is still in the bucket after promotion |

## What is known

- Conditions where they failed: Infection's initial run (Xdebug coverage, **random order**), full suite, on a
  TASK-067 tree (`4a1a27fa`). 2 failures in 3 random-order runs that day, a different test each time. Seed of
  the StorageLifecycle failure: `1792594625` (Infection's own generated config).
- Where they pass: each test alone; the full suite with `--order-by=random --random-order-seed=1792594625`
  without coverage (7918 tests); the full suite under coverage in default order; one more random-order run
  under coverage.
- So it is order-dependent and probably timing-sensitive too (coverage slows everything ~2x).
- Both read state another test can leave behind: notification rows by envelope, and object versions in the
  staging bucket. Both classes are `#[SkipDatabaseRollback]`-style scenarios; the known leak class is a
  committing test whose rows a later sweep picks up (f5sign-infra CLAUDE.md, *Persistent lanes*, the 59
  committed VOIDED envelopes).
- The `ChannelChange` ordering: the email invite takes `requested_at` from the seeded activation's
  `occurredAt` (`NOW` = 2026-10-13 09:00), the SMS from the channel change's `issuedAt` (+1 h). For SMS to sort
  first, one of those instants must have come from somewhere else — not traced.

## To reproduce

Infection in random order on a kept lane, until it fails with a visible seed, then bisect the tests that run
before the failing one:

```bash
make -C f5sign-infra wt-backend-infection src=<worktree> scope=files \
  args="--filter=<a covered src file> --test-framework-options=--order-by=random --min-msi=0 --min-covered-msi=0"
```

~8–10 min per run.
