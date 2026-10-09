# BACKLOG ids handed out by the coordinator (ADR-0073 package)

Highest id on any ref, worktree or note at 2026-09-29 ~12:50: BL-324. Re-audit before each new batch.

| Id | Task | Row |
|---|---|---|
| BL-325 | 040 | Residual race: a reaction reads the envelope just before the close and saves after the ending notice's audience read |
| BL-326 | 040 | The void reason is dual-purpose (internal record + recipient-facing) and a phishing vector in a branded email |
| BL-327 | 040 | Truncated-reason fallback, if a notice ever goes by SMS |

## Ids reserved by the coordinator (2026-09-29)
- ADR-0074 and TASK-051: envelope-first answer on commit/decline/challenge/auth (supersedes ADR-0067 §2.3/§7.3), worktree ../f5sign-backend-answer-order, branch feat/envelope-answers-first. After the ADR-0073 package.

## Batch 2 (audited 2026-09-29 ~17:35: highest in use BL-327)
- BL-328 .. BL-341: TASK-050's 14 follow-ups flagged "NEEDS BL-id" in var/task-runner/TASK-050/close-draft.md, assigned in the draft's order (first → BL-328).
- BL-342: TASK-051 — OpenApiSpecTest does not read ActRefusal cases.
- BL-343: TASK-050/Q1 residual — invitation failures and resends carry no stored instant, so one recorded in the deadline→sweep gap still counts (store those instants).

## Batch 3 (audited ~18:00: highest in use BL-343)
- BL-344..BL-348: TASK-050's five unproven properties (task §6/§7 order): two-process opening race vs a step deadline; two-process commit race vs a step deadline; migrated SENT rows on the new funnel predicate; the waiting AT_LEAST step end to end over HTTP; deadline-vs-expiry same-facts at HTTP tier. Close-now with a never-activated VIEWER over HTTP → BL-349.
- BL-350: TASK-050 'admitted counts' property (unrowed).
- BL-351: sub-second boundaries floored by datetime_immutable (ready_to_seal_at, settings_expires_at, refresh_grace_until, soft_locked_until, auth_attempt ordering); credential-retirement instants must NOT move.
- BL-352: TASK-051 residual — read-to-lock race names LEG_CLOSED in the ending arm of the deadline gap.

## Correction after the develop merge (158d0b1b, ~19:40)
- The merge renumbered the package's own BL-310..314 (TASK-048, collided with develop's published BL-310..324) to BL-352..356, and filed BL-357 (the audit trail does not follow ADR-0073's ending). So BL-352 is NOT TASK-051's any more: TASK-051's read-to-lock residual becomes **BL-358**.
