# RESUME — session 2

> **Superseded 2026-09-29 (evening): session 2's ADR-0073 work is DONE.** `feat/deadline-bars` @ `71bf88a7`, a clean
> tree (session 1's `f02fe3bf` + the (d)(e) bars). Committed since the pause:
> - `8e3e63a2` the close-now 204;
> - `0578ca7f`/`8642592d` (j) + the expiry same-facts census;
> - `63981fce` S6 + GateRuleParityTest + §1.5;
> - `b63648e1` the reword;
> - `897703a6` the bytes cut;
> - `71bf88a7` (d)(e).
> Handoffs 50 (dashboard) and 51 (signer) were sent. The ADR join texts are in `ADR-0073-join-amendments.md`. TASK-050's
> close is the coordinator's. Open findings (with the coordinator):
> - otp/send answers 404 instead of LEG_CLOSED for a released recipient who never opened;
> - an open in the deadline→sweep gap is admitted.
> Everything below is the paused state, kept as history.

Worktree: `f5sign-backend-ending-notice` (the session's working directory).

## Branches and tips

| Branch | Tip | State |
|---|---|---|
| `feat/ending-notice` | `0aad773b` | **TASK-040 done and closed** (task-close committed; BL-325/326/327). Merged with step-policy at `5e1a6aa9`. |
| `feat/close-now` | `da3d3071` | **TASK-050 stage D done.** Gates green there: lint 0/1475, deptrac 0, phpstan OK, fast 3504/16239. Handoff 50 sent. |
| `feat/deadline-bars` | **`ce18d7c8`** ← checked out | **Integration base**: step-policy `d6b56876` + close-now + envelope-expiry `06e35abf`. Green: lint 0/1511, deptrac 0, phpstan OK, fast 3596/16723. Sha sent to the coordinator and to session 1. |

## Uncommitted on disk (feat/deadline-bars)

Only `tests/F5Sign/Envelope/Acceptance/CloseEnvelopeNowHttpTest.php` (+177/−25). **Not green, never run. Do not commit as is.**

## The wave, item by item

1. **Close-now HTTP 204** (the file above):
   - Written: `the_sender_closes_an_envelope_secured_by_one_signature_and_releases_the_two_still_pending`. Real DSS commit, relay pumped, `#[SkipDatabaseRollback]`, per-run tenant + tearDown.
   - Two deliberate placeholders to fill after the first run: `STATUS_PLACEHOLDER` (SENT or COMPLETED, with a comment on why) and `REASON_PLACEHOLDER` (`NOT_REACHED` if the env records no invitation delivery, `SENT_NO_RESPONSE` if it does).
   - Then: run `only=CloseEnvelopeNowHttpTest` → fill the placeholders.
   - Sabotage: controller returns 204 without dispatching → expect red → `git checkout` the controller.
   - Commit `test(task-050): a sender's close-now over HTTP releases the pending members of a secured AT_LEAST step and is idempotent`.
2. **`POST /signing/session` #[OA] reword** (ENVELOPE_NO_LONGER_LIVE says "cancelled", which is false for a released member of an AGREED envelope):
   - **Not started.** Point the client to GET `/signing/session/auth`'s `outcome` + `envelope_outcome`.
   - Also rg the same claim in the other Session controllers.
   - Text to the coordinator before commit; commit on its own.
   - Assigned to the S6 agent (same controller).
3. **Case (j) + expiry side of same-facts:**
   - **Nothing written.** Findings:
     - (j) and D13 already run at the aggregate tier (`EndingScenarioCatalog`: "TASK-050 (j): …" and "D13: …", via `EnvelopeEndingStoriesTest`).
     - Missing: (j) over HTTP, D13 over HTTP (optional), and the same-facts census unit test.
   - HTTP template: `tests/F5Sign/Acceptance/EnvelopeExpiryHttpTest.php` (frozen_now pin, `SweepEnvelopeClocksCommand`, relay pump). AT_LEAST authoring: `tests/F5Sign/Envelope/Acceptance/StepPolicyHttpTest.php`.
   - Plan to make the reason discriminate:
     - `expires_in_days: 7`;
     - resend B once (`POST …/recipients/{rid}/resends`) so B's `invitation_sent_at` is later than C's;
     - pin `app_now()` at microsecond precision between C sent + 7d and B sent + 7d (`pinClock` needs `Y-m-d\TH:i:s.uP`);
     - expected: B `SENT_NO_RESPONSE`, C `LINK_EXPIRED`, both `EXPIRY`.
   - Same-facts without step deadlines: expiry vs natural closing, close-now and void, over the census policy × veto × outcome × role × reachability. It fails naming any dropped combination, and includes "ALL, one signed + one silent → NOT_AGREED".
   - Sabotages:
     - (a) expiry release uses ENVELOPE_CLOSED;
     - (b) the clock skips releases;
     - (c) drop one census combination.
4. **S6: a late opening on a released leg** (coordinator-approved, port `bool`). **Nothing written.** Two decisions are needed from the coordinator first:
   - **D-S6-1, return semantics on a closed envelope.** "false = envelope closed" contradicts the gate rule: a signer or an informational member still passes after the close (`WhatEachRecipientReadsAfterTheCloseHttpTest`). Proposal:
     - true = the gate rule, re-read under the member's row lock, passes;
     - the write happens only if the envelope is open AND the gate passes;
     - a closed envelope writes nothing but answers true for those members.
   - **D-S6-2, the aggregate twin.** `Envelope::recordOpening()` (`Envelope.php`, the in-memory twin used by `FakeEnvelopeRepository`) checks only `isClosed()`. Either it gains the leg check (an `Envelope.php` change, needs the coordinator's OK), or the fake applies the gate itself. Otherwise Application tests disagree with the real repository.
   - Other findings:
     - The check must sit inside `DbalEnvelopeRepository::recordOpeningInTransaction()`, not only in the adapter. The `AuthGatePassed` relay → `RecordRecipientAuthenticationUseCase` → `recordOpening()` path writes `authenticated_at` on a released leg even when Session refuses the credential, and that counts as engagement.
     - The predicate lives in `Contract/View/RecipientEnvelopeContextView::recipientCouldPassTheGate()` (built by `Application/Query/GetEnvelopeContextForRecipientHandler`). A private duplicate sits at `Envelope::recipientCouldPassTheGate()`.
     - Plan: the repository re-reads through the query handler on the same connection after its FOR UPDATE, with no root lock. Check that it's the same connection and tenant context.
     - The repository returns `{written, gatePasses}`; the adapter returns `gatePasses`.
     - Doubles to update for the `bool` return: `RecordingEnvelopeCommand`, the anonymous implementations in SealEnvelopeUseCaseTest (×2), MockSignUseCaseTest, SignForRecipientUseCaseTest, DocumentSignerTest, and `tests/bin/envelope_race_child.php`.
   - **Draft §1.5 sentence** (the coordinator edits LOAD-BEARING.md; not sent yet): *"The opening's row lock also decides the leg: under that lock `recordOpening()` re-reads the gate rule (`RecipientEnvelopeContextView::recipientCouldPassTheGate()`, ADR-0073 §2.3) and writes nothing on a leg the gate refuses — a released blocking member, a decliner — and the synchronous gate then mints no credential; a member who signed and an informational member still pass, without the root lock."*
   - **ProblemCode for `legClosed()`: not chosen.** Prefer reusing an existing "can no longer act" code (check `RECIPIENT_CAN_NO_LONGER_ACT` in `nelmio_api_doc.yaml`) before proposing a new one; tell the coordinator.
   - Tests to write:
     - Integration: an opening on a STEP_DEADLINE-released leg is refused;
     - a signed signer and a viewer re-opening still get a credential;
     - Application: legClosed thrown before minting;
     - keep `WhatEachRecipientReadsAfterTheCloseHttpTest` green.
   - Sabotages:
     - (a) the check always admits;
     - (b) it refuses informational members;
     - (c) the throw is removed.

## Coordinator decisions received after the pause (2026-09-29)

- **D-S6-1 accepted as proposed.**
  - `true` = the gate rule, re-read under the member's row lock, passes.
  - The write happens only when the envelope is open AND the gate passes.
  - A closed envelope writes nothing but answers `true` for a signer or a viewer.
- **D-S6-2:** the leg check goes in **`Envelope::recordOpening()`** (Envelope.php allowed for THAT method only, using the same gate predicate), **not in the fake** (authoring rule 4: a fake that reimplements production logic). The check also lives inside `DbalEnvelopeRepository::recordOpeningInTransaction()`, which covers the AuthGatePassed relay path.
- **Send the §1.5 sentence to the coordinator on resume.**

## Next steps, in order

1. `make -C ../f5sign-infra wt-backend-up src=$(pwd)` (the lane was up at pause; a reboot stops it).
2. D-S6-1 and D-S6-2 are decided (section above). Send the coordinator the §1.5 draft.
3. The wave again, on disjoint files: the 204 (finish), (j) + census, S6 + the OA reword. Tests serial on the lane.
4. Full gates via `test-runner` (fast + lint/arch/phpstan), plus filtered: CloseEnvelopeNow, EnvelopeExpiry, WhatEachRecipientReads, RecipientOpeningWrite, EnvelopeRootLockRace, StartSession, SubmitAuthResponse, OpenApiSpecTest.
5. Commit per unit (`test(task-050)`, `fix(task-050)`); contract texts to the coordinator first. Handoffs in 50–59 (the S6 refusal code and the OA reword → signer handoff).
6. Report "(j) done @ <sha>". Pre-writing (d)(e)(g)(h) waits for session 1's builder seam (`EnvelopeBuilder::withStep(ordinal, StepPolicy)`), after it merges feat/deadline-bars. Maintainer decisions to respect: reasons judged at the deadline instant; deadline_at stored at activation; void/close-now in the deadline gap refused (session 1 wires close-now's mapping).

## Lane

`wt-f5sign-backend-ending-notice` backend lane: up (KEPT) at pause, rebuilt after the 049 merge (049's clock-sweep role present). Nothing running. Session 1 shares the backend cap (1).
