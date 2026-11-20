# TASK-078 — The machine auth and signature routes refuse a slot nobody has claimed

<!-- OFFREPO: the `wt-backend` lane named in §5 is a target of the sibling `f5sign-infra` repo's Makefile
(`make -C ../f5sign-infra wt-backend… src=<worktree>`): it runs this worktree's own tree in containers of its own, so
a run there validates this branch and not the main checkout.
OFFREPO: the measurements in §1 came from a throwaway acceptance test on that lane, on 2026-11-04 at `8bf35051`. It
is not committed, and every result it gave is restated in §1; AC-1 replays the same requests.
OFFREPO: the callers' answers in §4 D7 come from the integrator's dashboard repo and the `f5sign-signer` repo, read on
2026-11-04. They are restated there; nothing here depends on reading those repos. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `fix/unclaimed-slot-on-machine-routes`** (`ce98f2cd`), 2026-11-04 — suite green under the `wt-backend` lane (10693 tests, 179329 assertions, lint, arch and PHPStan clean; the worktree's own tree). AC-15 is met by recording why the query was not run (§7, owner, 2026-11-19). **Merged to `develop` on 2026-11-19**, after `develop` was merged into the branch; the full suite ran again on the merged tree. Infection on the changed lines: 19 mutants, 19 killed, on `8aff64b2`. Left out, with homes: `ENVELOPE_NOT_SENT` (`BL-266`, open), credentials minted before the deploy (`BL-529`), the delegated route's undeclared 404 (`BL-250`). AC-6d was met in a corrected form (§8). |
| **Type** | **Corrective**: three use cases that accept what ADR-0055 §2.3 and ADR-0057 say they must refuse. No migration, no new route, no new event. |
| **Why** | One machine call on a slot nobody has claimed records an opening and a session, even when the call fails, which can strand the slot. The delegated route goes further and signs for it. |
| **Builds on** | [ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.3, [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.4 and §2.5, [ADR-0083](../adr/ADR-0083-a-recipients-gates-are-editable-until-they-enter.md) §2.1 and §2.8, [ADR-0074](../adr/ADR-0074-a-closed-envelope-or-leg-answers-before-the-session.md) §2.2 and §2.3, [ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md) §2.6 |
| **Scope** | Session only, plus the published contract and a handoff. ⛔ Not the sender-side recoveries on a slot (`BL-206`), not re-assigning a slot (`BL-193`), not `ENVELOPE_NOT_SENT` (§6). |
| **Decision record** | [ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.3 already decides the refusal on the signature route, and this realizes it. Extending it to the two gate twins applies [ADR-0057](../adr/ADR-0057-claimable-recipient-slot.md) §2.4's premise and contradicts neither. No new ADR; one would be forced if a legitimate caller turned out to need a gate on an unclaimed slot. |

---

## 1. Why this task exists

`IssueAuthChallengeUseCase`, `SubmitAuthResponseUseCase` and `CommitDelegatedSignatureUseCase` never ask whether the
recipient is an unclaimed slot. `SigningTokenIssuance` and `CopyLinkEligibility` do, so an integrator is refused the
link and the copy, and walks past both on these three routes with its machine key.

Measured over HTTP, against a control slot with the same declaration and no machine call, whose gate change answered
200 and whose email-only claim answered 204.

A slot declaring `OTP_EMAIL` and `OTP_SMS` with no contact, on a sent envelope:

| Call | Answer | Left behind |
|---|---|---|
| `POST …/recipients/{id}/auth/otp/send` | 409 `AUTH_NO_DESTINATION` | `first_opened_at` stamped, a `session.signing_session` row |
| `POST …/recipients/{id}/auth` | 401 `AUTH_NO_OPEN_CHALLENGE` | the same |
| `PUT …/recipients/{id}/auth`, afterwards | 409 `RECIPIENT_ALREADY_ENTERED` | |
| `POST …/claim` with an email only, afterwards | 422 `RECIPIENT_CANNOT_RECEIVE_METHOD` | |
| `POST …/claim` with an email and a phone, afterwards | 204 | |

So a claimant with only an email is stranded, which is the deadlock `BL-205` records as resolved. The way out is a
phone the claimant may not own, written into the evidence, or a void.

A slot authored with an email and `OTP_EMAIL`: the send answers 200 `minted: true` and creates an `AUTH_OTP_ACCESS`
notification holding a code, with `full_name` and `claimed_at` still null. The transmission was not observed, because
no worker ran.

The delegated route was measured on 2026-09-25 (`BL-266`): a sent envelope whose one recipient is `claimable` with
`signs_via: MACHINE_KEY` took a delegated commit with 204 and reached `COMPLETED` unclaimed. Its audit trail states
`NO_SESSION_BEFORE_CLAIM` as failing.

Only a holder of a machine key can do any of this.

## 2. What already exists (reuse, do not rebuild)

- **The predicate.** `RecipientView::isUnclaimedSlot()` is the conjunction *declared claimable and `claimed_at` null*,
  the read-side twin of `Recipient::isUnclaimedSlot()`. Reuse it; never read one of the two terms.
- **The code.** `RECIPIENT_SLOT_NOT_CLAIMED` is already in the published catalog (`config/packages/nelmio_api_doc.yaml`),
  is raised by `SigningTokenNotIssuableException::slotNotYetClaimed()`, and is named in
  `CommitDelegatedSignatureController`'s 409 block, whose use case never raises it.
- **The crossing.** `RecipientAuthContext`, built by `RecipientAuthContextReader`, is what all three use cases already
  read before they write. `stepIsActive` is the model for a required member.
- **The order.** The gate twins ask the recipient's own act, then the shut gate (`$auth->gatePasses`), then the step.
  `CommitDelegatedSignatureUseCase` asks the assertion shape, then the step, then the session's own refusals.
- **The rollback.** The delegated use case opens its session inside `UnitOfWork::own()`, so a refusal later in that unit
  removes the row.
- **The census.** `GateAndActRoutesAskTheirRuleTest` classifies every route of `config/routes/api/signing.php` and names
  the token each file must carry. It fails, named, on a route it has not classified.
- **Fixtures.** `tests/F5Sign/Envelope/Acceptance/RecipientClaimHttpTest.php` authors and sends a real slot over HTTP;
  `tests/F5Sign/Session/Acceptance/UnclaimedSlotRefusedHttpTest.php` is the mint's refusal, and
  `MachineDrivenCeremonyHttpTest`, `DelegatedSignatureHttpTest` and `MachineTwinsRecordTheOpeningHttpTest` are the
  routes under change. None of those three uses a slot.
- **The audit check.** `TrailAssembler::noSessionBeforeClaim()` fails a trail in which a session fact precedes the claim.

## 3. Scope

1. `RecipientAuthContext` carries a required member saying the recipient is an unclaimed slot, filled from
   `RecipientView::isUnclaimedSlot()`.
2. `IssueAuthChallengeUseCase` and `SubmitAuthResponseUseCase` refuse on it, on both their machine and their token
   paths, in the place D2 gives.
3. `CommitDelegatedSignatureUseCase` refuses on it, in the two places D3 gives.
4. The published 409 of `SendRecipientAuthOtpController` and `SubmitRecipientAuthResponseController` names the code. The
   delegated route's block already does, and becomes true. A new assertion scoped to these operations pins it:
   `OpenApiSpecTest` only proves that a code is named by *some* operation, and this one already is.
5. `GateAndActRoutesAskTheirRuleTest` gains the slot question for these three routes.
6. A frontend handoff under `docs/frontend-handoff/` for the integrator and the signer.
7. The read-only query of D6, its result recorded in §7.
8. The sweep of rule 1: `BL-528` closes; `BL-266`, `BL-176`, `BL-205` and `BL-387` are corrected or narrowed; ADR-0055's
   §2.3 bar and TASK-033's bar 20 say they hold; any docblock saying these routes ignore a slot.

**Out:** see §6.

Concepts re-cut: *"an unclaimed slot reaches no gate"* (false until this lands), `AUTH_NO_DESTINATION` on a slot,
`RECIPIENT_SLOT_NOT_CLAIMED` "cannot be raised" on the delegated route, `BL-205` "resolved" as unconditional.

## 4. Key decisions

- **D1 — The fact crosses in `RecipientAuthContext`, and is asked in each use case.** `Envelope::recordOpening()` with a
  new `ActRefusal` was considered and refused, for three reasons. The delegated commit never calls it. It runs after the
  step question, so a slot on a dormant step would be told to wait rather than to claim, unlike the mint. And three of
  the four `match` expressions over `ActRefusal` have a `default` arm that would report a new case as `LEG_CLOSED`.
- **D2 — On the gate routes: after the shut gate, before the step and before anything is written.** The recipient's own
  act and a shut gate keep their answers (ADR-0074 §2.3). The slot question then runs with no further condition, because
  whoever reaches it has passed the gate rule, and an informational slot on a closed envelope passes that rule. It runs
  before `recordRecipientOpening()`, `startIfAbsent()`, the limiter and any code.
- **D3 — On the delegated route: after the assertion checks, before the step, while the envelope is alive and the leg
  open.** The assertion refusals answer whether this route is theirs at all (ADR-0066 §2.6), and a dead envelope or a
  closed leg keeps the aggregate's answer (ADR-0074 §2.2). The session the call opened rolls back with the refusal. The
  no-session branch asks it too, so a relayed act on a slot answers 409 rather than 404.
- **D4 — Slot before step, as the mint answers.** The remedy for an unclaimed slot is to claim it; waiting for a step
  never fixes it.
- **D5 — No lock is needed for this read.** `declared_claimable` is written once, and a claim is once-only (ADR-0057
  §2.4), so a slot goes from unclaimed to claimed and never back. A read that sees it unclaimed during a racing claim
  answers a refusal the caller can retry, and writes nothing.
- **D6 — Existing rows are counted, not repaired.** `first_opened_at` is evidence, so no migration clears it. The query
  is in §7. ⛔ `envelope.recipient` has `FORCE ROW LEVEL SECURITY`, so as the application role with no tenant set it can
  return 0 rows, which reads as *no damage*. It runs as a role that bypasses RLS, beside a total count that separates an
  empty table from an undamaged one. If it finds rows, each is decided by the owner.
- **D7 — No known caller changes.** The integrator's dashboard never calls the send or the submit. It calls the signature
  route only for its `CARGADOR`, a named `MACHINE_KEY` recipient authored with `claimable=false`, so no path reaches a
  slot; read at its `feat/ecmr-signature` `1b2ddca88`. It does call `PUT …/auth` on an unclaimed slot before the claim, so
  that route must stay open, which AC-6 pins. The signer app calls none of the three machine routes. It does call the
  token twins, which share two of these use cases, but an unclaimed slot gets no signing token, so it never meets the
  refusal. Its `openapi-snapshot.json` lists no machine route, so these edits leave it as it is. No test here covers those
  repos.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | The measured defect: a machine send on a contactless slot answers 409 `RECIPIENT_SLOT_NOT_CLAIMED`, with `first_opened_at` null and no session row | owner | Acceptance | the code before the fix |
| AC-2 | A machine send on a slot authored with an email answers the same, with no `AUTH_OTP%` notification and no limiter charged | owner | Acceptance + Application | drop the guard in `IssueAuthChallengeUseCase` |
| AC-3 | A machine submit on a slot answers the same, with no opening, no session and no attempt spent | owner | Acceptance | drop the guard in `SubmitAuthResponseUseCase` |
| AC-4 | A delegated commit on a `MACHINE_KEY` slot answers the same, with no session row, and the envelope stays open | derived — ADR-0055 §2.3 | Acceptance | drop the guard after the assertion checks |
| AC-5 | A relayed commit on a slot with no session answers the same, not 404 | derived — rule 5 | Acceptance | drop the guard in the no-session branch |
| AC-6 | After each refusal of AC-1…AC-5 the slot is intact: the gate change answers as it did before the call, and an email-only claim 204 (members AC-6a…e) | owner | Acceptance | see *Notes on AC-6* |
| AC-7 | Once claimed, the machine ceremony and the delegated commit succeed, and the trail's `NO_SESSION_BEFORE_CLAIM` holds (members AC-7a…b) | derived — ADR-0057-claimable-recipient-slot.md | Acceptance | make the guard ignore `claimed_at` |
| AC-8 | Each state of a slot answers its own code on each route (members AC-8a…e) | derived — rule 5 | Acceptance | see *Notes on AC-8* |
| AC-9 | The context's member is the conjunction: declared and claimed is false, undeclared with no name is false, declared and unclaimed is true | derived — rule 5 | Application (`RecipientAuthContextReaderTest`) | read one term |
| AC-10 | A machine key of another tenant gets the answer it gets today, which does not reveal a slot | derived — rule 4 | Acceptance | ask the slot before the tenant-scoped read |
| AC-11 | Each machine route that can reach a slot's gate or act carries its slot question in `GateAndActRoutesAskTheirRuleTest`, and removing a guard reddens it naming the route (members AC-11a…c) | derived — rule 5 | Unit (architecture) | remove a token from a use case |
| AC-12 | The published 409 of each machine route names `RECIPIENT_SLOT_NOT_CLAIMED` (members AC-12a…c) | owner | Acceptance, a new route-scoped assertion on the spec | drop the name from that route's `#[OA\Response]` |
| AC-13 | The handoff states the three old and new answers, and the sweep of §3 #8 leaves no present-tense claim that these routes admit a slot | owner | Review, `rg` over the `Concepts re-cut` terms of §3 | — |
| AC-14 | A named recipient and an ordinary claimed one see no change: the three machine test classes of §2 pass with no edit to their assertions | derived — rule 4 | Acceptance | — |
| AC-15 | §7 records the query of D6 for each environment that holds real data, or why it was not run, and no row was changed | owner | Operational, recorded in §7 | Met: not run, and why (§7) |

<!-- OFFREPO: `f5sign-infra`'s lane, as tagged at the top of this record. -->
- **Gates:** suite, PHPStan, deptrac and lint under the lane that mounts this tree (`make -C ../f5sign-infra wt-backend
  src=<this worktree>`), and Infection on the changed lines.

**Notes on AC-6**
- AC-6a — after the contactless send. AC-6b — after the send on a slot with an email. AC-6c — after the submit.
  AC-6d — after the delegated commit. AC-6e — after the relayed commit. Sabotage: move the guard below
  `recordRecipientOpening()`, which still answers 409 and leaves the opening, so this and not AC-1's status reddens.
- The gate change answers 200 in AC-6a, AC-6b, AC-6c and AC-6e. In AC-6d the slot is `MACHINE_KEY`, whose gates cannot be
  changed whether or not a call preceded (ADR-0055 §2.2), so it answers 409 `RECIPIENT_HAS_NO_GATES` both before and after
  the refused commit, with `first_opened_at` null and no session row.
- ⚠ Assert the rows and the follow-up call, not only the 409. With two guards in series a sabotage can report green
  about a guard it never reached (the repo's authoring rule 4).

**Notes on AC-7**
- AC-7a — a slot claimed and then driven through the machine send and submit. AC-7b — a `MACHINE_KEY` slot claimed and
  then signed, whose rendered trail source holds the check.

**Notes on AC-11**
- AC-11a — `machine_auth_otp_send`. AC-11b — `machine_auth_submit`. AC-11c — `commit_delegated_signature`. The census
  holds one triple per route today, so the slot question needs a shape change. `auth_otp_send` and `auth_submit` share
  their files with the first two, so removing that token reddens both of a pair, and they get no member of their own.

**Notes on AC-12**
- AC-12a — the send. AC-12b — the submit. AC-12c — the delegated commit.

**Notes on AC-8**
- AC-8a — closed envelope, gate shut: `ENVELOPE_NO_LONGER_LIVE`, on the send, the submit and the delegated commit.
- AC-8b — a released slot on a live envelope: `LEG_CLOSED`, on the same three.
- AC-8c — a slot on a dormant step: `RECIPIENT_SLOT_NOT_CLAIMED`, not `STEP_NOT_ACTIVE`, on the same three.
- AC-8d — an informational slot after the close, which passes the gate rule: `RECIPIENT_SLOT_NOT_CLAIMED`, nothing
  written, on the send and the submit.
- AC-8e — a `SIGNING_PLATFORM` slot asserting on the delegated route: `ASSERTION_NOT_ACCEPTED` still answers first.
- Sabotage of AC-8a…c: move the slot question above the checks it follows, or below the step.

## 6. Open follow-ups (track, don't solve here)

- **`ENVELOPE_NOT_SENT` on the delegated route.** `BL-266`'s other half: published and never raised, since the route
  answers 404 for an unsent envelope. A contract question of its own; `BL-266` stays open for it. **What would force it:** building `BL-209`'s per-route gate, or an integrator branching on that code.
- **Reset and unlock on a slot** (`BL-206`). They write a recorded fact about a party who does not exist, and open no
  session. **What would force it:** a sender recovery called on a slot in real traffic.
- **Credentials already minted on a slot.** A session credential pair the machine submit returned on a slot, on a correct
  code, before this branch deploys is not withdrawn: `RenewSessionCredentialUseCase`, `CommitSignatureUseCase` and
  `DeclineSignatureUseCase` do not ask the slot question. It lasts at most until the session's twelve-hour cap and its last
  access credential's fifteen minutes, and the submit now refuses a slot, so no new pair starts there. **What would force
  it:** a deployment where a machine ceremony ran on a slot in the twelve hours before it. Home: `BL-529`, which also records that §7's query is only an upper bound for this (it counts `first_opened_at`, not minted credentials).
<!-- OFFREPO: the integrator's dashboard repo, read on 2026-11-04; the fact is restated here. -->
- **The dashboard's message for this code.** Its `F5SignErrorMessages` maps `slot_not_claimed` to text about assigning the
  recipient before generating their link. None of its calls can now receive it from these routes, so nothing changes;
  the handoff mentions it. **What would force it:** that repo starting to call these routes on a slot.

## 7. The query of D6

<!-- OFFREPO: the command is run by the owner on the production host, from the `f5sign-infra` directory. Its compose
files live there; the query itself is restated below. As of 2026-11-04 nothing here says whether production holds real
envelopes. -->

**Not run, by the owner's decision of 2026-11-19.** No known caller reaches the three routes on a slot: the
integrator's dashboard, read again on 2026-11-19 at `e10a0a8b2`, calls the signature route only for its named
`CARGADOR`, authored with `claimable=false`, calls neither the send nor the submit, and calls `PUT …/auth` on a slot,
which stays open (AC-6). The signer app calls none of the three. Production was emptied at the `v1.0.0` deployment
of 2026-11-07, keeping only the tenants and their keys, so only envelopes since then could hold a stamped row, and
only through a direct call with a machine key. No row was changed. The query stays here for whoever needs to count:

```
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml exec -T postgresql sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT rolsuper FROM pg_roles WHERE rolname = current_user" -c "SELECT count(*) AS recipients_total FROM envelope.recipient" -c "SELECT r.envelope_id, r.id FROM envelope.recipient r WHERE r.declared_claimable AND r.claimed_at IS NULL AND r.first_opened_at IS NOT NULL"'
```

A result of 0 counts only with `rolsuper` = `t` and `recipients_total` read. If the columns do not exist, the deployed
tag predates `Version20260828000001`, and that tag is what to record.

## 8. Deviations & honest notes

### Scope
- None. The diff is Session `src/` and its tests, the route-scoped `OpenApiSpecTest` assertion, the census test, the handoff `docs/frontend-handoff/TASK-078-integrator-signer-unclaimed-slot-on-machine-routes.md`, dated notes on five ADRs (0055, 0057, 0067, 0074, 0083), `BACKLOG.md` and TASK-033's record. Nothing under §6 Out. No migration, `deptrac.yaml`, PHPStan config or baseline change.
- Beyond the slices as dictated: AC-14 gained a citing test of its own (a named `MACHINE_KEY` signer is signed with no claim); the past-expiry state got an Acceptance and an Application test; the new AC-14 test class leaves rows in the event log and neighbouring tables, accepted against the reference class.

### Decisions made during implementation
- **AC-6d was corrected, at `3a0c9e67`.** The record said the gate change answers 200 after the delegated commit. AC-4's slot is `MACHINE_KEY`, and `Envelope::guardRecipientAuthChangeable()` refuses every `MACHINE_KEY` recipient with 409 `RECIPIENT_HAS_NO_GATES` (ADR-0055 §2.2), called or not, so 200 is unreachable. The test asserts the same `RECIPIENT_HAS_NO_GATES` before and after the refused commit, `first_opened_at` null, no session row, and the email-only claim 204. The property (the refusal left the slot intact) is kept; the criterion's wording in §5 stays as written, for the owner to see.
- **AC-10's sabotage was not the one the record names.** *"Ask the slot before the tenant-scoped read"* cannot be written, because the fact arrives only through that read. The sabotage used instead: `RecipientAuthContextReader::read()`'s not-found branch throws the slot refusal, which reddens the comparison against an unknown id (409 where 404 expected) on all three routes.
- **AC-2's limiter half is proven at the Application tier only** (`CountingOtpSendLimiter`), which the record's *Acceptance + Application* allows: `when@test` swaps the limiter pool for an array adapter and no Acceptance test can read the counter back. The Acceptance half asserts no `AUTH_OTP%` notification.
- The 409 prose of the send, submit and delegated operations states the rule by cause, not the lists slice 07 first dictated, after review rounds found the lists false in some states (a released slot, an informational slot). *"The recipient stays unopened"* became *"no opening is recorded"*, which also holds for a slot an earlier call stamped.
- Slot before step on the gate routes (D4), and the no-session branch of the delegated route asks too (D3): as the record decided. A relayed commit with no session keeps its 404 for an ended envelope or a closed leg, as the plan states.
- The closing review's F1 (credentials minted earlier) and F2 to F6 (handoff and docblock prose) were fixed or declared on the branch in slice 09 (`bad43e96`..`ce98f2cd`).

### Decisions that needed an ADR
- None. ADR-0055 §2.3 already decided the delegated refusal, and the gate twins apply ADR-0057 §2.4's premise. Five ADRs carry dated notes only. No ADR was moved to Accepted from this step.

### Declared and unproven properties
- **The `code` comparison of AC-10 has no recorded red.** Slice 03 saw the status comparison go red on all three routes under the sabotage above; the comparison of `code` after it was never seen red on its own, because the status assertion fails first. Accepted by the round 2 review.
- **AC-2's limiter** is not reachable at Acceptance (above).
- **D5 (no lock for the read)** has nothing to test, by decision: no lock is taken.
- **Mutation strength**: Infection on the changed lines of `src/F5Sign`, on `8aff64b2`, killed 19 of 19, with 0 escaped and 0 not covered, on the `wt-backend` lane with `StorageLifecycleScenarioTest` excluded (`BL-356`). The first run left `slotNotClaimed()` not covered, because every test reaching it only declared the exception as used; `SigningSessionUnavailableExceptionTest` closed that with no change to `src/`. Infection cannot see `#[OA\*]`, so the route-scoped `OpenApiSpecTest` assertion is the sole guard of AC-12.
- **The census** (`GateAndActRoutesAskTheirRuleTest`) reads `signing.php` only; the copy mint asks in `CopyLinkEligibility`, and the sender-side machine routes of `envelope.php` are not classified and must not ask (AC-6, `BL-206`).
- **AC-15 is met without the query.** The owner decided on 2026-11-19 not to run it, for the reasons §7 gives.
- **A sabotage of shared `src/` reached another slice's run.** Slice 04's run straight after its own sabotages were restored failed `another_tenants_key_learns_nothing_about_a_slot` with 409 vs 404, once, and did not recur in six later runs. It fits slice 03's sabotage of `RecipientAuthContextReader`'s catch, running on the shared tree at the same time; that is inferred from the lane timings, not observed. The later full runs (`90364ca6`, `ce98f2cd`) were quiet and green. Learning: with parallel slices on one tree, a sabotage of shared `src/` can show up as a red in a sibling slice's run, so judge a sibling's red from its assertions and cite a quiet full-suite run.

### Debt left behind, and where it lives now
- Credentials minted on a slot before this branch deploys, and that §7's query is only an upper bound for them: `BL-529` (new), and §6.
- The delegated route's undeclared 404, and two statements false for a `SIGNING_PLATFORM` recipient with no session (*"Every act on an ended envelope gets this answer"*; the handoff's first bullet of §2): a note on `BL-250`, for its fold. No new row.
- `ENVELOPE_NOT_SENT` on the delegated route: `BL-266` stays open for it. Sender-side recoveries on a slot (`BL-206`) and re-assigning a slot (`BL-193`) are untouched and out of scope.
- `BL-528` is closed in `BACKLOG.md`; its row says why AC-15's query was not run. Its id and `BL-529`'s were
  first written as `BL-507` and `BL-508`, which `develop` gave to other rows in the meantime.
- The dashboard's message for `slot_not_claimed`: §6, nothing changes today.
- The production query of §7: the owner's.

### Delegated work
- Nine slices. Critical, on opus: 01 (0 review rounds; one replicator call that edited nothing), 02 (1), 03 (1, DONE_WITH_CONCERNS: the `code` comparison has no recorded red), 04 (1, DONE_WITH_CONCERNS: watch `another_tenants_key_…` in the final run), 05 (1), 09 (1, DONE_WITH_CONCERNS: the route declares no 404, `BL-250`). Standard: 06 on sonnet (0), 08 on sonnet (1), 07 on sonnet then opus (2). The closing review returned 6 findings, which slice 09 resolved. No slice report other than 01's lists delegated work.

### Cost of the run
- `run.log` carries no token or cost lines; those are in the orchestrator's Phase 7 table, which this step does not have. What `run.log` holds: 9 slices (6 opus, 2 sonnet, 1 sonnet then opus), 8 slice review rounds in total, 1 closing review (6 findings, one fix slice), 2 full green runs of 10693 tests (the baseline was 8772), and one escalation, slice 07 from sonnet to opus. Totals per model: see Phase 7.
