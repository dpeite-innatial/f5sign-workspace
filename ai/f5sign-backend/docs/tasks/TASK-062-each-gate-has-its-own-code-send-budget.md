# TASK-062 — Each gate has its own code-send budget

<!-- OFFREPO: the failure in §1 was reported by the dashboard team's session from local testing on 2026-10-20, and the signer's 429 copy fix lives in the signer repository. Every fact taken from them is restated in §1; nothing here depends on reading either. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/otp-budget-per-gate`** (tip `80cb951d`), 2026-10-20 — full suite green at `abf8b7ac` (7533 tests, 83665 assertions; lint, arch and PHPStan green) under the `wt-backend` lane of this worktree (the main checkout was not the harness); the commits after it change docblocks, one test's citation and the handoff index only. ADR-0081 is `Accepted (exercised)`: the owner accepted it on 2026-10-20, after this task exercised §2.1–§2.5 (§7). Infection verdict on the changed lines: one real escaped mutant (the session id dropped from the session key), killed by a test added in `50d9c93d`; the three left on that line are equivalent (§7). The tip `50d9c93d` adds that test to the commits above; its class is green. Pending review; not merged. |
| **Type** | **Corrective** in Session's delivered-code limiter: the per-session counter is split by gate, and five numbers in `config/packages/rate_limiter.yaml` change. No route, payload or event changes; the 429 is unchanged. |
| **Why** | The access gate and the signing gate draw on one per-session send budget. A recipient who needed three SMS codes to get in (one slow SMS is enough) cannot receive the code they need to sign for most of an hour: the signing gate's send is refused by `otp_sms_session` (3 per hour). The recipient who is already inside and about to sign is the one the limiter should block least. |
| **Decision record** | **ADR-0081, drafted as Proposed in this task's first slice; the owner accepts it.** It amends [ADR-0075](../adr/ADR-0075-the-signing-gate-is-answered-on-the-act.md), which says the ceiling stays the per-medium limiter "unchanged" and records that a joint cap per gate was weighed and not taken (§7.11 — that rejected a *tighter* joint cap, not a budget of the signing gate's own); [ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.9 (the per-session ceiling, now per session, per gate, per method); [ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.12 (session and destination counters identical on both surfaces — still true, now per gate; and its arithmetic that `otp_sms_source` is 10 per hour, now 30); and [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.10 (the narrow destination's SMS number). |
| **Builds on** | [TASK-022](TASK-022-delivered-codes-over-email.md) and [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) (the limiter and its per-medium sets), [TASK-057](TASK-057-sms-spend-guards.md) (the four counters and the operator rescue), ADR-0075 (the signing gate answered on the act). |
| **Scope** | Only the session counter gains the gate. The destination and source counters stay shared across gates. The machine source numbers (`otp_machine_*_source`) are unchanged. The signer's 429 copy is the signer team's (§6). |

---

## 1. Why this task exists

Reported from local testing on 2026-10-20: a recipient declared with `OTP_SMS` on both gates asked for three
access codes (the second and third because the first was slow), got in, pressed "Firmar", and the signing
code was never sent: the send was refused with 429 by `otp_sms_session` (3 per hour, sliding window), and the
signer could not ask again for about 17 minutes. The access gate's sends and the signing gate's sends shared
one counter, because `OtpSendKeys::of()` keys the session counter on the session id alone.

Owner decisions, 2026-10-20: each gate gets its own per-session budget, for SMS and for email, and the
numbers are those of §4.

## 2. What already exists (reuse, do not rebuild)

- **The keys.** `Session\Application\Port\OtpSendKeys` holds four keys plus `machineDriven`: `session`
  (sha256 of the session id), `narrowDestination` (envelope + normalized destination), `wideDestination`
  (normalized destination), `source` (the request's source address, or the API client on the machine
  surface). `of()` serves the browser route, `ofMachine()` the machine twin. No key carries the gate or the
  act today.
- **The limiter.** `Session\Infrastructure\RateLimit\FailOpenOtpSendLimiter` (port `OtpSendLimiter`):
  `consume()` spends session, narrow, wide, source in that order and stops at the first refusal;
  `policiesFor()` picks the `otp_email_*` or `otp_sms_*` set by `DeliveryMedium`, and the machine
  `otp_machine_*_source` for the source counter on the machine surface. A store failure fails open and logs
  at `error`. `clear()` resets session, narrow and wide (and the machine source only when `machineDriven`).
  Wiring: explicit arguments in `config/services.yaml`, one `limiter.<policy>` per policy.
- **The call site.** `IssueAuthChallengeUseCase::issue()` resolves `$gate` server-side and `$boundAct`
  (`null` on ACCESS, the act on SIGNING) before it calls `consume()`; both are in scope there and neither is
  passed today. Both routes, `POST /api/v1/signing/session/auth/otp/send` and its machine twin
  `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth/otp/send`, go through it. A recovering caller
  (`recover: true`, ADR-0053) gets a code for the ACCESS gate.
- **Acts.** `SigningAct` has `SIGN` and `DECLINE`, both on the SIGNING gate (ADR-0075 §2.3).
- **The operator rescue.** `ClearOtpSendLimitsUseCase` (`app:session:clear-otp-limits`) already loops over
  `AuthGate::ACCESS` and `AuthGate::SIGNING`, but dedupes its targets by medium + destination, because the
  keys carry no gate.
- **Today's numbers** (`config/packages/rate_limiter.yaml`, all `sliding_window`, one hour): email session 5,
  narrow 10, wide 30, source 30; SMS session 3, narrow 5, wide 30, source 10; machine source email 300,
  SMS 100. The file's comments carry the arithmetic (BL-178: 5 + 3 = 8 per session for a recipient declaring
  both media) and say the SMS numbers are estimates never measured (BL-169).
- **Tests that pin it.** `OtpSendKeysTest` (key shapes, no address in any key), `FailOpenOtpSendLimiterTest`
  and `ClearOtpSendLimitsUseCaseTest` (both through `Testing\YamlOtpSendLimiter`, which parses the real yaml
  and hard-codes the policy names), `IssueAuthChallengeUseCaseTest` (through `CountingOtpSendLimiter`),
  `OtpSendRefusalParityTest` (the 429 names no counter), `ClearOtpLimitsCommandTest`. No HTTP test can assert
  a limiter 429 (`DeliveredCodeCeremonyHttpTest`'s docblock: the pool resets between requests), so the
  numbers are pinned at the Unit/Application tier only.

## 3. Scope

1. ADR-0081 drafted as Proposed (first slice), with the four amendments of the header, the index row,
   relationship graph and crosswalk in `docs/adr/README.md`.
2. The session key carries the gate: `OtpSendKeys::of()` and `ofMachine()` take the gate and hash it into
   `session` only. `IssueAuthChallengeUseCase` passes `$gate`. The other three keys are unchanged.
3. `ClearOtpSendLimitsUseCase` clears the session counter of both gates (its dedupe gains the gate for the
   session key).
4. `rate_limiter.yaml`: the numbers of §4, and every comment whose arithmetic they change.
5. Tests of §5, and the existing tests that pin the old numbers updated.
6. A short handoff note to the signer and the dashboard: the 429 is unchanged; the budgets are now per gate.

Out: the signer's 429 copy (§6); any change to the machine source numbers; per-act budgets inside the
signing gate.

Concepts re-cut: `otp_sms_session` and `otp_email_session` keep their names but now count per session **per
gate**; "per-session ceiling" (BL-178, ADR-0054 §2.9, the yaml comments) changes meaning. Sweep both names and
"per session" claims about the limiter.

## 4. Key decisions

- **The gate goes into the key, not into the policy set.** One `*_session` policy per medium, counted under a
  per-gate key, gives each gate its own N without new policies or new wiring.
- **Only the session counter is split.** The destination and source counters protect a phone, a mailbox or
  an address from abuse whatever the gate; splitting them would double what one number can receive.
- **The numbers** (owner, 2026-10-20), per hour:

  | Counter | Email | SMS |
  |---|---|---|
  | Session, per gate | 5 (unchanged) | 5 (was 3) |
  | Destination on this envelope | 10 (unchanged) | 10 (was 5) |
  | Destination across envelopes | 30 (unchanged) | 30 (unchanged) |
  | Source address | 30 (unchanged) | 30 (was 10) |

  The narrow destination rises to 10 so that 5 + 5 per session never meets it first; the source rises to 30
  so an office behind one address does not meet it. Knowing a link is required to send at all, and the wide
  destination still bounds each number.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A session whose access-gate budget is spent still gets a signing-gate code (members AC-1a SMS, AC-1b email) | owner | Unit (`YamlOtpSendLimiter`) + Application | drop the gate from the session key |
| AC-2 | Each number of §4 holds: the send after the limit is refused, by the named policy (members AC-2a…f) | owner | Unit (`YamlOtpSendLimiter`) | revert the number |
| AC-3 | SIGN and DECLINE codes draw on the signing gate's one budget | derived — ADR-0075 | Application | key the session on the act |
| AC-4 | The destination and source counters stay shared across gates: with 5 + 5 SMS to one phone on one envelope in one hour, the narrow counter still counts all ten | derived — ADR-0077 | Unit | add the gate to the narrow key |
| AC-5 | The machine route spends the same per-gate session key as the browser route; its source policies are unchanged | derived — ADR-0055 | Unit | omit the gate in `ofMachine()` |
| AC-6 | The operator rescue clears the session counter of both gates | derived — src/F5Sign/Session/Application/UseCase/ClearOtpSendLimitsUseCase.php | Application | clear one gate only |
| AC-7 | No key carries an address, and the session key differs between gates of one session and is identical for one gate across both surfaces | derived — tests/F5Sign/Session/Unit/Application/Port/OtpSendKeysTest.php | Unit | — |
| AC-8 | The 429 is unchanged and names no counter | derived — ADR-0049 | Unit | — (regression) |
| AC-9 | A recovering caller's code (`recover: true`) is charged to the access gate's budget | derived — ADR-0053 | Application | charge it to the signing gate |

<!-- OFFREPO: the `wt-backend` lane is a target of the f5sign-infra Makefile; its one relevant fact is restated in the line below. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane: an ephemeral stack (its own
  PHP container, Postgres cluster and broker) that mounts this worktree's tree rather than the main checkout's.

**Notes on AC-2** — AC-2a SMS session per gate: the 6th refused by `otp_sms_session`; AC-2b email session per
gate: the 6th refused by `otp_email_session`; AC-2c SMS narrow destination: the 11th refused by
`otp_sms_envelope_destination`; AC-2d SMS source: the 31st refused by `otp_sms_source`; AC-2e the unchanged
email narrow (10), both wide (30) and the email source (30) still refuse at their numbers; AC-2f the machine
source numbers (`otp_machine_email_source` 300, `otp_machine_sms_source` 100) are read back unchanged from the
yaml. Owner said: "por sesión de firmante lo pondría a 5 ambos"; "Por teléfono/email en este sobre 10 / 10";
"Por IP de origen 30 / 30".

**Test design for AC-2 and AC-4** (from the claims check, 2026-10-20). `consume()` spends session, narrow, wide,
source in that order, so a refusal is always the first counter that is full:
- AC-2c and AC-4: one session on two gates stops at 5 + 5 on its own session counters, so the 11th send to the
  phone on the envelope comes from a **third session id**; that is the send `otp_sms_envelope_destination` refuses.
- AC-2d and the email source of AC-2e: the wide destination and the source are both 30 and wide is spent first,
  so the 30 sends and the 31st use **distinct destinations** (and fresh sessions); a same-phone loop is refused by
  the wide counter instead.

**Notes on AC-1** — Owner said: "cupo propio para firmar pero también para los emails, en resumen que cada
puerta y tipo de noti tengan sus límites".

**Deploy note** — counters live in Redis under the old session key; after the release every session starts a
fresh per-gate count. The window is one hour, so the effect is at most one extra hour of budget for sessions
open at deploy time. Not a criterion.

## 6. Open follow-ups (track, don't solve here)

- **The signer's 429 copy** — closed 2026-10-20, fixed by the signer team on 2026-10-20 (says no code was sent, counts down to
  `retry_at`), in its own repository.
- **The numbers are still estimates** (BL-169): revisit with real SMS traffic.
- **BL-189 reads stale** (three counters, machine capped at ten SMS per hour). Undecided: whether the row
  closes or is restated against today's four counters and the machine source key. It is forced the moment the
  sweep of §3 touches the BACKLOG; this task restates it only if its own numbers make the row more wrong.

## 7. Deviations & honest notes

### Scope
- Beyond the plan's file list: `docs/frontend-handoff/README.md` (index entry and count 47 to 48, added by the orchestrator after the slice-05 review) and `docs/ddd/signing-session-domain-model.md` plus the `OtpSendLimitsCleared` docblock (the plan said no `docs/ddd` edit; slice 02's review found the row stale, so slice 05 fixed it). Two docblocks (`SendAuthOtpController`, `OtpSendRateLimitedException`) were corrected by the orchestrator after the closing review (`8683f754`); `OtpSendRefusalParityTest` gained a citation fix (`80cb951d`).
- No migration, route, payload, event, `services.yaml`, deptrac or PHPStan change.

### Decisions made during implementation
- A per-gate census test, `every_shipped_otp_policy_has_its_number_pinned`, was added (`441cbdc5`) after slice 04's review: `YamlOtpSendLimiter` hard-codes policy names, so a policy added to the yaml would have passed unpinned.
- The rescue (`ClearOtpSendLimitsUseCase`) clears the session counter of every gate and dedupes only destination keys, because the declaration is read fresh and resetting an unspent counter costs nothing.
- A recovering caller is charged to the access gate (the gate the resolver returns for a recovery), pinned in `IssueAuthChallengeUseCaseTest`.
- The closing review's low-confidence note (BL-189's headline still reads "ten SMS an hour") was left: BL-189 carries a dated 2026-10-20 note saying the number is 30, and whether the row closes is undecided (§6).

### Decisions that needed an ADR
- ADR-0081, drafted as Proposed in slice 01. The owner accepted its substance on 2026-10-20. The owner accepted the move to `Accepted (exercised)` on 2026-10-20, applied in its own commit. Exercised by `OtpSendKeysTest`, `IssueAuthChallengeUseCaseTest`, `FailOpenOtpSendLimiterTest`, `ClearOtpSendLimitsUseCaseTest`, `OtpSendRefusalParityTest`; realized in `OtpSendKeys::of()`/`ofMachine()`, `IssueAuthChallengeUseCase::issue()`, `config/packages/rate_limiter.yaml` and `ClearOtpSendLimitsUseCase`.

### Declared and unproven properties
- The 429 cannot be asserted over HTTP (the pool resets between requests), so every number is pinned at the Unit/Application tier through `YamlOtpSendLimiter`, which parses the real yaml but is a test double of the limiter wiring.
- Redis-backed sliding-window behaviour under concurrency is not reached by any harness here; the in-memory pool stands in.
- The numbers are estimates (BL-169): no SMS has left this system.
- Security audit warning, accepted by the owner: the SMS cost surface rises (session 3 to 5 per gate, narrow destination 5 to 10, source 10 to 30; the wide SMS destination was and stays 30). `composer audit` was not run (no dependency change).
- Infection (filtered to the branch's 8 `src/` files, which it mutates whole; bars 85 covered-MSI / 70 MSI), `wt-backend-infection` on this worktree's lane, tip `80cb951d`: 228 mutants, 156 killed, 27 escaped, 45 not covered — covered-MSI **85.25 %** (pass), MSI **68.42 %** (below 70). Of the 72 undetected, **4 are on lines this branch changed**, all in `OtpSendKeys::sessionKey()`; the other 68 are on untouched lines of the touched files (mostly `SendAuthOtpController`'s `#[OA\*]` strings and older lines of the use cases and the limiter), so the MSI shortfall is not this task's code. Judged on changed lines: dropping the session id from the key was a **missing test** — `two_sessions_at_one_gate_spend_two_session_keys` (`50d9c93d`) kills it, sabotage-checked (only that test reddens). The other three are **equivalent**: two reorderings of the concatenation and dropping the `\n` separator, all still distinct per session and gate because the gate is a closed enum. Re-run on `OtpSendKeys.php` alone at `50d9c93d`: 22 mutants, 18 killed; the 4 escaped are those three plus a coalesce on line 69 (`$sourceAddress ?? 'unattributed'`), unchanged since 2026-08-19 and outside this task.

### Debt left behind, and where it lives now
- The numbers remain estimates: BL-169 (open).
- The sum of a sender's declared methods across both gates, now 20 sends an hour with ten chargeable for `[OTP_EMAIL, OTP_SMS]`: BL-178 (restated with today's arithmetic in this task).
- Whether BL-189 closes or is restated: BL-189 (dated note added; decision open), and §6 above.
- No new BACKLOG row was needed.

### Delegated work
- Slice 01 (ADR landing, mechanical): sonnet, 1 round, DONE.
- Slice 02 (session key carries the gate, rescue; critical): opus, 1 round, DONE_WITH_CONCERNS. One `replicator` job: `AuthGate::ACCESS` added to 16 `FailOpenOtpSendLimiterTest` call sites (the slice counted 17); the diff was reviewed, only the gate argument changed, accepted without rework.
- Slice 03 (use-case gate pins; critical): opus, 1 round, DONE_WITH_CONCERNS. No delegation.
- Slice 04 (owner numbers and table test; critical): opus, 2 rounds, DONE. No delegation.
- Slice 05 (prose, backlog, handoff sweep; standard): sonnet, 1 round, DONE. No delegation.

### Cost of the run
- Slice tokens: 712813 in total (sonnet 335397 over slices 01 and 05; opus 377416 over slices 02 to 04).
- Review rounds: 6 across 5 slices (slice 04 took two); no escalation after a failed round.
- Full suite: one run at `abf8b7ac`; baseline 6233 tests before, 7533 after.
