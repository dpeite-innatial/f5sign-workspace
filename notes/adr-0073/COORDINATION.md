# ADR-0073 package — coordination rules (both worktree sessions)

Coordinator = the session in the main checkout `f5sign-backend/` (it runs TASK-049 there). Find it with
`ListAgents`; its name changes when it restarts.

- **Shared files — ask the coordinator before editing**: `src/F5Sign/Envelope/Domain/Aggregate/Envelope.php`,
  `EnvelopeEndingEvaluator` / `StepCompletionEvaluator`, `docs/adr/ADR-0073-*.md`, `docs/adr/README.md`,
  `docs/frontend-handoff/*`, `docs/BACKLOG.md`, `docs/LOAD-BEARING.md`. **BACKLOG ids come from the coordinator**,
  never picked yourself.
- **Any `/v1` contract change** (route, field, `ProblemCode`, `#[OA\*]` string, event payload) → message the
  coordinator, who logs it in `CONTRACT-CHANGES.md`.
- **Provisional handoffs to the frontends, as each stage lands (maintainer, 2026-09-29, replacing "one batch at the
  merge")**: when a committed stage changes what the signer or the dashboard-sf (Factor5's integration backend, NOT
  the signing backend) sees, write a provisional handoff in Spanish, in the same format as
  `../notes/adr-0073-provisional-handoffs/` (PROVISIONAL, actionable against mocks, measured-at shas, names not fixed
  marked as such), to `../notes/adr-0073/handoffs/<NN>-<task>-<stage>-<signer|dashboard>.md` (`<NN>` from your task's own block, next free inside it, so parallel sessions never collide: 049 → 10–29, 050 → 30–49, 050 stage D (session 2) → 50–59, 040 → 60–79), and send its path plus a
  3-line summary directly to the frontend session (`ListAgents`: `f5sign-signer-*`, `factor5-dashboard-sf-*`). Tell
  the coordinator the same thing at the same time. Only what is committed, never what is planned. The dashboard-sf
  keeps working on its current branch (`feat/waybill-pdf-pagination`), and the signer on its ADR-0073 worktree
  `f5sign-signer-adr0073` (`feat/prep-adr-0073-envelope-ending`). The official handoffs in
  `docs/frontend-handoff/` are still the coordinator's, written at the package join.
- **Tests only on your own lane**: `make -C ../f5sign-infra wt-backend-up src=$(pwd)` once, then
  `wt-backend-test src=$(pwd) only=<regex>` (or `changed=1 fast=1`) while implementing; `wt-backend-down` at the end.
  Never `make test` / `make qa` from a worktree: they validate the main checkout. The backend lane cap is **1**
  (flock in `wt-validate.sh`): if the other worktree session is running, your run waits. That is expected, so don't
  kill it. Full suite and Infection run ONCE at the end over the joined package; per task only the fast gates.
- **Migrations**: `make -C ../f5sign-infra wt-backend-sf src=$(pwd) cmd=doctrine:migrations:generate`. Never name one
  by hand.
- **Commits**: subagents never commit; you commit with explicit paths; English; no trailers; no AI mention in
  messages or code. Keep each stage under ~60 uncommitted files and commit as pieces close.
- **Parallelise** inside the task with subagents on disjoint files (and the fast gates in parallel). Launch first,
  check after; short briefs that point to files.
- **Decisions for the maintainer go through the coordinator** (maintainer, 2026-09-29): never ask the maintainer directly; send the question, the options and your recommendation to the coordinator, who asks and sends back the answer. This applies to the frontend sessions too.
- **Report to the coordinator** (SendMessage) at: plan ready · each stage committed (sha) · blocked · done.
- Workers of the dev stack are down on purpose, so leave them down.
