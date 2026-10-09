# Session 1 handoff: TASK-050 first half (2026-09-29)

The first session started in the wrong directory (`f5sign-backend-claimable`) and stopped before editing
anything. Relaunch from `f5sign-backend-step-policy` (branch `feat/step-policy` @ `01955a9e`).

## State left behind
- The lane is up for `src=…/f5sign-backend-step-policy`, so there's no need to run `wt-backend-up` again.
- The baseline (`fast=1`) and spec-lint were running when the session stopped. Their output goes to
  `var/task-runner/TASK-050/baseline.log` and `spec-lint.report.md`. Use them if they are complete;
  otherwise re-run them.
- Spec-claims doesn't need running: `../notes/adr-0073/TASK-050-spec-claims.report.md`.

## Plan the coordinator approved (stages A–F, one commit each)
- A. §3.3 decline-retirement patch, plus a hand-port of the `DeclineSignatureController` hunk.
- B. §3.2 `NEVER_HOLD` flip, delete `InformationalMembers`, refuse an informational commit by name, add the
  LOAD-BEARING entry.
- C. §3.1 step authoring (request fields, migration, `Step`, `RosterStepShape`, `send()` wires `refusalsAtSend()`).
- D. §3.5 close-now (`EnvelopeClosedBySender`, `Envelope::closeNow()`, sender route).
- E. §3.4 non-deadline half: `RecipientReleased` → per-recipient session revocation.
- F. §3.7 non-clock parts: the step view, the claim refused once the envelope is closed, the copy-ready notice.
- Delivery bar cases (a)(b)(c)(f)(i).

## Coordinator's answers (from `f5sign-backend-ea`)
- The `docs/LOAD-BEARING.md` id for stage B is **§1.21**. §1.19 is reserved by `feat/evidence-audit`, so
  don't use it. Add a provenance line for it in the list at the top of the file, as §1.20 has.
- **Contract changes**: when each one is committed, send the coordinator its exact name/shape (A's retired
  ProblemCode; B's new refusal code; C's fields and refusal codes; D's route) and what the signer must
  change. The coordinator logs them in `CONTRACT-CHANGES.md` and relays them as one batch when the package
  lands on develop.
- **Before committing B**, send the coordinator the name of the new informational-commit refusal code.
  **After B lands**, send its sha: the coordinator merges it before touching `snapshot()`.
- `docs/frontend-handoff/*` belongs to the coordinator, so don't edit it.
- In `Envelope.php`, C and D may touch `addStep()`, `send()` and a new `closeNow()`. The coordinator's
  TASK-049 stays in `acceptsActs()`, `snapshot()`'s `expires_at` and a clock entry point.
