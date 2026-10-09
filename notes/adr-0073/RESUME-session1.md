# Session 1 resume note: TASK-050 (paused 2026-09-29)

## Where
- Worktree `f5sign-backend-step-policy`, branch `feat/step-policy`, tip **`c250aad7`**.
- ⚠ The session was launched in `f5sign-backend-claimable` and then switched with EnterWorktree. Relaunch **from
  `f5sign-backend-step-policy`** so relative paths and git calls resolve there.
- Workspace: `var/task-runner/TASK-050/`. It holds `run.log` (every decision and coordination note, read it
  first), `deadline-core.plan.md` (the core design), and the gate reports (`validate`, `contract-check`,
  `security-audit`, `doctrine-guard`).

## Merged
- `feat/deadline-bars` @ `ce18d7c8`, merged in `c250aad7`. It contains TASK-049's envelope expiry (`06e35abf`) and
  session 2's close-now (D). The lane was rebuilt afterwards (`wt-backend-down` + `wt-backend-up`) for the
  clock-sweep role, and fast=1 is green on the merge: 3598 tests.

## Committed (first half, all green)
| Commit | Change |
|---|---|
| `8f42995d` | A: retires the quorum decline refusal |
| `1cc5ef0e` | B: never-hold, `COMMIT_NOT_OFFERED_TO_ROLE`, LOAD-BEARING §1.21 |
| `c8e404c4` | F: the `SEALED_COPY_READY` notice |
| `70593ec2` | Informational members read after the close |
| `480faab9` / `21dc9a4a` | E: per-release revocation, sparing readers; `envelope_outcome` on /auth, void spares readers |
| `a3a524b2` | C: step authoring, `send()` refusals, migration `Version20260929102747` |
| `b4fce49f` | `snapshot()` uses `Step::policy()` |
| `901fd813` | `envelope_outcome` on the read model |
| `0e499567` | Delivery bar (a)(b)(c)(f)(i) |
| `48cf24ce` | Dead quorum readers removed, docs/ddd |
| `aca35852` | SESSION_CLOSED prose |
| `b22dd37e` | `min_signatures` upper bound |

First-half fast gates were green @ `0e499567`: fast 3538, filtered Integration/Acceptance 288, lint/phpstan/deptrac
0. The read-only gates all passed: task-validate, contract-check, doctrine-guard, and security-audit with 4
warnings (see below).

## Uncommitted, on disk (NOT red, just unverified)
The recipient-side mapping `ActRefusal::STEP_DEADLINE_PASSED → LEG_CLOSED`, a maintainer decision. It touches
`AdmitRecipientAct.php`, `CommitSignatureController`, `CommitDelegatedSignatureController`,
`DeclineSignatureController` (one clause in the `LEG_CLOSED` #[OA]), and `AdmitRecipientActTest` (a census over
`ActRefusal::cases()`).
- The hermetic run on the merged tree already included it and was green: 3598 tests.
- Still to do before committing:
  1. `only='AdmitRecipientActTest|CommitSignatureUseCaseTest|DeclineSignatureUseCaseTest|CommitDelegatedSignatureUseCaseTest'`
  2. `WT_GATES=lint` and `WT_GATES=phpstan`.
  3. Sabotage: move `STEP_DEADLINE_PASSED` back into the `=> $refused` arm; the census must fail naming it.
  4. Add a one-line docblock fix in `SigningSessionUnavailableException::legClosed()`: it also covers a step past
     its deadline that hasn't been closed yet.
- The agent dropped the trailing "nothing was recorded; do not retry" from the coordinator's text, because each
  block already says it. Mention that when committing.

## Next 3 steps (the deadline core, per `deadline-core.plan.md` and the maintainer's decisions)
1. **Seam commit, first, because session 2 is waiting on it.**
   - `EnvelopeBuilder::withStep(ordinal, StepPolicy)`.
   - Rename `EndingScenario::isWithoutStepPolicyFlags` to `isWithoutCloseNowOrDelegation`, and sweep its callers.
   - `EnvelopeEndingStoriesTest` plays the deadline and veto stories through `applyClocks()`.
   - LEG_CLOSED #1.21 "until an aggregate-tier clock exists" becomes the stories test (the coordinator OK'd this
     one-line LOAD-BEARING edit).
   - Send the sha to session 2 (`f5sign-backend-delegated-ef`) and the coordinator.
2. **Q5, then the funnel.**
   - Q5: store `deadline_at` on the step at activation, by rewriting the unpushed migration
     `Version20260929102747`, plus `Step`, the repositories and the read.
   - Funnel, in a new generated migration (`wt-backend-sf … doctrine:migrations:generate`, never hand-named):
     widen `envelope.tenants_with_due_clocks`, grant `SELECT(id)` on `envelope` and the step columns, add a policy
     TO `f5sign_envelope_clock_sweep` and a partial index.
   - Widen `DbalDueClockEnvelopes::inScope()` the same way (the silent-zero half).
   - Update the docblocks, and add the Integration tests for the grant boundary (including a voided envelope),
     the sweep command with a silent-zero sabotage, and the schema census.
3. **Q1, then Q2.**
   - Q1: the release reason is judged AT THE DEADLINE instant, not the sweep's. Pin it with a test where the
     sweep runs late and a link expires in between.
   - Q2: void and close-now are refused past an open step's deadline with `STEP_DEADLINE_PASSED` 409 (the OA text
     is approved; the proposal is in the coordinator thread). This covers the evaluator, the `void()` mapping, the
     `closeNow()` mapping (mine, not session 2's), and the #[OA] on the void and `CloseEnvelopeNowController`
     409s.

## Pending decisions and messages
- **Security audit warnings (not yet sent to the coordinator):**
  - (2) `envelope_outcome` is visible on the pre-gate `/auth` to any link holder.
  - (3) While the envelope is open, a released or declined member keeps reading on a held 15-minute access JWT
    until the async revocation lands (`withholdsDocumentFromRecipient` ignores `legIsClosed`). It needs a
    decision plus a test.
  - (4) Informational sessions are kept on a void. That was the maintainer's decision; confirmation only.
  - Also pre-existing: `AddStepRequest::ordinal` has no upper bound either (a 500 on overflow).
- **Owned by others:**
  - Session 2 owns the S6 late-opening fix (the `EnvelopeCommandInterface` bool). It will send the port shape to
    the coordinator.
  - The coordinator's join list: BL-231, BL-283, BL-313, the ADR-0073 §2.4/§2.10/§2.11/§5 wording, the ADR-0066
    §2.3 amendment, the ADR-0067 §2.3 stale premise, and the official frontend handoffs.
  - The superseding ADR-0067 (envelope-first answers) is a separate task for the coordinator, after the package.
- **Handoffs sent:** 30 (A), 31 (B), 32 (F), 33 (E), 34 (C, dashboard), 35 (the read-model `envelope_outcome`).
  Next free number in my block: **36**.

## Lane
- `wt-f5sign-backend-step-policy` is UP (KEPT) and was rebuilt after the merge.
- No run is in flight.
- Tear it down at the end with `make -C ../f5sign-infra wt-backend-down src=<abs>`.
