# Brief — TASK-050, first half (session 1)

- **Where**: worktree `f5sign-backend-step-policy`, branch `feat/step-policy`, cut from
  `feat/task-048-how-an-envelope-ends` @ `01955a9e`. Lane: `wt-backend … src=$(pwd)`.
- **Spec**: `docs/tasks/TASK-050-a-step-says-how-much-agreement-it-needs.md` (claims already corrected in `01955a9e`).
- **Rules**: read `../notes/adr-0073/COORDINATION.md` first; it binds.
- **Run**: `/task-runner TASK-050`. Skip Phase 1's spec-claims (done:
  `../notes/adr-0073/TASK-050-spec-claims.report.md`); fast gates only, no Infection, no full suite.

## Scope now: everything NOT waiting on TASK-049
The claims report §5 has the file-level split. In short:
- §3.1 step authoring (`completion`/`veto`/`deadline` columns + `CHECK`, `AddStepRequest`, `RosterStepShape`) and the
  `send()` refusals (`EnvelopeEndingEvaluator::refusalsAtSend()` already exists, so wire it).
- §3.2 flip the aggregate to `NEVER_HOLD`, delete `InformationalMembers`, refuse an informational commit by name;
  **add the `docs/LOAD-BEARING.md` entry** (§2.4, ask the coordinator for the § number).
- §3.3 apply `../notes/adr-0073/task-050-quorum-decline-retirement.patch`. It applies cleanly **except
  `DeclineSignatureController.php`** (TASK-048 moved it): `git apply --exclude=src/F5Sign/Session/UI/Http/DeclineSignatureController.php`,
  then port that hunk by hand. Contract change (`ProblemCode` retired) → tell the coordinator.
- §3.4 non-deadline half: `RecipientReleased` → Session per-recipient revocation (mirror `OnEnvelopeVoided`).
- §3.5 close-now (`EnvelopeClosedBySender`, sender route).
- §3.7 except anything clock-driven.
- Delivery bar cases (a)(b)(c)(f)(i).

## NOT now (second half, after the coordinator says 049 is done)
§3.4 deadline half, §3.6 (049's funnel/command slot), bars (d)(e)(g)(h)(j), same-facts bar at aggregate/HTTP tier.
You will then `git merge feat/task-049-…` (coordinator gives the branch name) into `feat/step-policy`.

## Shared-file hotspots with the coordinator's TASK-049
`Envelope.php` (`evaluator()`, `snapshot()`, `advance()`, `acceptsActs()`), the step entity/migration. Touch
`evaluator()`/`snapshot()` only for the `NEVER_HOLD` flip, and tell the coordinator the sha when you commit it.

When the first half is committed and fast-gate green: report "050 first half done @ <sha>" and stop. Don't do task-close yet.

## Coordinator answers already given (2026-09-29)
- Plan A–F (A decline patch · B NEVER_HOLD flip · C step authoring · D close-now · E OnRecipientReleased · F §3.7
  non-clock) approved.
- LOAD-BEARING id for B: **§1.21** (§1.19 is reserved by `feat/evidence-audit`). Add its provenance line at the top.
- Contract changes: send each one's exact name/shape to the coordinator when committed. The coordinator logs them in
  `CONTRACT-CHANGES.md` and relays them to the frontends in one batch at the package merge. Send the new
  informational-commit refusal code's name BEFORE committing B. Do not edit `docs/frontend-handoff/*`.
- `Envelope.php`: addStep()/send()/new closeNow() are yours; the coordinator's 049 stays in acceptsActs(), snapshot()'s
  expires_at and a clock entry point. Send B's sha when it lands.
