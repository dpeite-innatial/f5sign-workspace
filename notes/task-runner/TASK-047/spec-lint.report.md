# spec-lint — TASK-047

**Status:** PASS
**Issues:** 2 (0 blocking, 2 warnings)

**Record:** `docs/tasks/TASK-047-per-signer-evidence-document.md` (branch `feat/per-recipient-receipt`, worktree `f5sign-backend-per-recipient-receipt`, HEAD `c90c8135`)

## Blockers
(none)

## Warnings
- [sibling-flagged] Sibling TASK-068 (`docs/tasks/TASK-068-after-the-commit-the-signer-is-told-where-their-copy-stands.md`) lives only on `fix/signed-copy-after-commit`, not on `develop` or this branch. The Sibling field says so, and it is flagged ⚑. If TASK-047 runs before TASK-068 is integrated, the two must still not be planned independently: TASK-047's session route answers `409 RECEIPT_NOT_READY` and TASK-068 owns the session read's 409s (§4 #5, §Sibling). Never a blocker by spec.
- [sibling-flagged] Sibling BL-188 (`docs/BACKLOG.md`, row exists on develop) is flagged ⚑ as the delivery vehicle for the signer's copy. BL-188 is a backlog row, not a task record, so it is on-tree. Flagged for coordination only; it does not block.

## Checks passed
- Step 1: file exists and parses; 263 lines, six numbered sections plus header.
- Step 2 header: `Status`, `Type` (Forward build with one enabling Foundation change, states the kind of work), `Why` (states a gap that can be disagreed with), `Decision record` (ADR-0086, Proposed) all present and non-empty. `Builds on` (ADRs only), `Scope`, `Sibling` present. No Planning-era fields.
- Step 3 Status: claims no existing code (`Not started`); no `merged`/`landed`/`shipped`/`in progress`/✅ wording, so no `status-unverifiable`. Dates are absolute (2026-10-22, 2026-09-22). Branch diff vs `develop` touches only docs (BACKLOG, ADRs 0070/0072/0073/0086, README, TASK-045, TASK-047); no §Scope code file is touched, so no `status-stale`.
- Step 3b Decision record: form 1 (cites ADR-0086, link resolves to `docs/adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md`). The record does not say it contradicts or reverts an ADR; it extends ADR-0071/ADR-0072 §2.9 and points others at ADR-0086. It also declares where ADR-0086 lands (§3 #6: its Status, Enforced by and Realized in move with this task). Scope touches `Foundation/EventLog` (a contract), and an ADR is cited, so no `decision-required`. Scope section present (`scope-unstated` not triggered).
- Step 4 Builds on: all cited ADRs resolve (0050, 0061, 0071, 0072, 0073, 0076); no task is cited.
- Step 5 sections: §1–§6 numbered from 1 with no gaps or repeats; Scope (§3) and Verification (§5) present; no empty section.
- Step 5b criteria table (record is TASK-055+ style, so applies): columns match README §8 (`Id | Criterion | Origin | Tier / harness | Sabotage`). Ids AC-1…AC-15 and S-1…S-3, unique, well-formed. No `proposed` origin (owner and derived only). Every `derived` row names a source: ADR-0072 §2.9, §2.10, §2.7, §2.1; ADR-0061 §2.7; ADR-0073 §2.16; ADR-0071; and `rule 5` (CLAUDE.md § Authoring rules, rule 5 exists). Every row has a tier or harness. "each/every" rows (AC-7, AC-8) list their members (AC-7a…f, AC-8a…d) in Notes. No struck-through ids. Type is not Corrective, so `corrective-unreproduced` does not apply.
- Step 6 self-containment: all 8 relative links resolve on disk (BACKLOG.md; ADR-0050, 0061, 0071, 0072, 0073, 0076, 0086). No `#L\d+` or `:\d+` line-number citations. No external URLs, so no OFFREPO tag is needed.
- Step 7 id uniqueness: `TASK-047` carries the same slug (`per-signer-evidence-document`) on every branch where it appears. No collision. (TASK-068 and TASK-069 are distinct ids, not collisions.) ADR-0086 is claimed only by `feat/per-recipient-receipt` and its origin remote, with the same slug.
- Step 8 uncertainty markers: no `PENDIENTE`, `[NEEDS CLARIFICATION`, `TBD` or `???` in the file.

## Notes for the orchestrator (not spec-lint issues)
- ADR-0086 is `Proposed` and says it becomes Accepted when TASK-047's §5 bars are green. The task-close step owns that move; nothing here needs it now.
- The `var/task-runner/TASK-047/` directory was writable (owned by the running user); the report was written there directly, not to the scratchpad.
