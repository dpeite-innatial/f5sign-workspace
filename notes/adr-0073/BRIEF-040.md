# Brief — TASK-040 (session 2)

- **Where**: worktree `f5sign-backend-ending-notice`, branch `feat/ending-notice`, cut from
  `feat/task-048-how-an-envelope-ends` @ `01955a9e`. Lane: `wt-backend … src=$(pwd)`.
- **Spec**: `docs/tasks/TASK-040-cancellation-notice.md`. It is the re-cut against ADR-0073, with the maintainer's
  decisions of 2026-09-29 already applied (`../notes/adr-0073/TASK-040-decisions.md`): every `EnvelopeVoided`
  notifies, one mechanism, 4 copy families / 5 purposes (sender split by reason), decliner/vetoer in the audience.
  Purpose names are provisional.
- **Rules**: read `../notes/adr-0073/COORDINATION.md` first; it binds.
- **Run**: `/task-runner TASK-040`. The old claims report (`../notes/adr-0073/TASK-040-spec-claims.report.pre-recut.md`)
  predates the re-cut, so run spec-claims again on the re-cut in Phase 1. Fast gates only, no Infection, no full suite.

## Watch
- The causes with no writer yet (time ran out, out of reach, veto) are held at the use-case tier (§9). Do not wait for
  049/050.
- `VoidEnvelopeRequest::$reason`'s `#[OA\*]` change is a published-contract change → tell the coordinator before
  committing it.
- New purposes hit six exhaustive `match`es and every authored locale (§5). Spanish copy goes in its catalog as usual.
- The §7 "landing sweep, for tense" list touches TASK-046/038/047/049, ADR-0059/0070 and a signer handoff. The handoff
  and ADR edits are shared files, so ask the coordinator first.

Full task-close when done and fast-gate green; report "040 done @ <sha>".
