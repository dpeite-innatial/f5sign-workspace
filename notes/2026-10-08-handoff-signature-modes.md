# Handoff 2026-10-08 — mark text fitting (merged) and TASK-054 (ready, not merged)

## Merged today
- **fix/mark-text-fits** is on backend `develop` at `ee2889a8`, pushed. The backend lays out a mark's text with PT
  Serif widths: text-only marks are wrapped at 8 pt, capped, and the last line is ellipsized, with the delegated
  route always kept. Image marks use `ZOOM_AND_CENTER` with the name on one line. The full regression was 6160 tests.
  - The dev stack was down at merge time. On the next `make up`, the containers compile the new `services.yaml`.
    If the workers were already running, run `worker-down` and then `worker-up`.

## TASK-054 — ready except Infection and the merge
- **Branch** `feat/signature-modes`, pushed. The worktree is `f5sign-backend-signature-modes`, and its lane is
  KEPT up. The tip carries code from `7d82550d` (full regression: 6230 tests, lint, deptrac and PHPStan green) and
  from `53c61d7d` (published wording; lint, PHPStan, OpenApiSpecTest and the fast tier green). After that the
  commits are docs only.
- **Gates done:**
  - spec-lint ×2;
  - spec-claims ×3;
  - task-validate (it ran Infection at 84%, but at `7025b022`, before the fix round, so that figure is NOT valid);
  - doctrine-guard;
  - contract-check ×2 (the blocker was fixed);
  - security and eIDAS;
  - docs-sync;
  - task-close (Status reads "implemented, Infection pending, not merged").
- **To finish:**
  1. Phase 3b: Infection **once**, on the tip: `task-validate-runner` with `infection: final`. The maintainer said
     not today, and asked to be told before it is launched.
  2. If it is green, merge into develop and push. Run `make migrate`, because migration `Version20261008083445`
     adds three columns to `envelope.recipient`. Recreate the dev containers.
  3. Tell the signer and the integrator: `signature_mode` becomes required on the commit, so the signer must deploy
     with it. The handoffs are `docs/frontend-handoff/TASK-054-*.md`.
  4. Remove the worktree and the root `.gitignore` line, and bring the lane down.
- **Follow-ups filed:** BL-385 to BL-389, covering the image on the machine route, per-tenant defaults, the
  claimable MACHINE_KEY, the OpenApiSpecTest per-route limit, and legal's review of the checkbox.
- **Moved:** BL-382 to BL-384 had been filed under Closed by mistake. They now sit under Open.

## Learned today, and already in the AI store
- Infection runs once, after every gate and fix round (task-runner Phase 3b), never beside the gates.
- Briefs from a worktree give the workspace by absolute path.
- git pushes through Windows `ssh.exe`. Never override `GIT_SSH_COMMAND`.
- Delegation works: the replicator did 3 jobs (31, 28 and 48 sites), and all three were accepted.
