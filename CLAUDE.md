# F5Sign — Root workspace (internal repo)

This folder **is a private, internal git repo** that assembles the F5Sign workspace and
**centralizes all AI configuration** (Claude). **Never delivered to the client.** Each
`f5sign-*` subfolder is an independent project with its own git, dependencies and life
cycle, and **must contain no trace of AI** (it receives it via symlink, ignored locally).

## Structure

- `ai/` — **Source of truth** for the AI config. `ai/shared/` = skills identical across all
  repos that use them; `ai/f5sign-*/` = each subrepo's own `CLAUDE.md` + `.claude/`.
- `bin/` — scripts: `bootstrap.sh` (clone + sync), `sync-ai.sh` (AI symlinks),
  `unlink-ai.sh` (revert), `purge-ai-history.sh` (phase 4, destructive).
- `notes/` — handoffs and internal work notes.
- `repos.manifest` — subrepos (name/url/branch) for `bootstrap.sh`.
- `f5sign-docs/` — **Source of truth** for specs, product decisions and architecture. Read only.
- `f5sign-backend/` — API and server-side logic.
- `f5sign-dashboard/` — Admin frontend.
- `f5sign-signer/` — Signing app for the end signer.
- `f5sign-infra/` — Infrastructure: local stack **and production orchestration** (deployment, migrations and prod backups come from here).

## Work rules

1. **One task = one repo.** `cd` into the subrepo that's relevant. Code, commits and PRs are
   always done inside that subrepo, never in the root.
2. **The root is tooling/internal AI only.** NO product code goes in the root. Its commits
   are AI config, scripts and notes. (That's why this repo does carry git, unlike before.)
3. **`f5sign-docs/` is reference.** Consult it for specs; don't modify it except for documentation tasks.
4. **Crossing repos in the same commit is forbidden.** Two projects = two coordinated PRs.
5. **Centralized AI config.** Each subrepo's `CLAUDE.md` and `.claude/` are **symlinks**
   into the `ai/` store. Edit them there (or through the symlink). After cloning/updating a
   subrepo, re-run `bin/sync-ai.sh`. User skills in `~/.claude/`. **How that config is written**
   is in `ai/CLAUDE.md`, which loads when working inside `ai/`.

## Cost: delegate mechanical work to a cheaper model

The owner's priority is token cost. **Mechanical, high-volume work goes to a subagent on a cheaper model, with
`model:` passed explicitly** (a subagent without it inherits the session's model):

- `haiku` — extract and report: reading large files or logs to pull out what matters, listing, counting,
  checking that paths or targets exist.
- `sonnet` — rewrite by fixed rules: translations, bulk renames, reformatting, summaries.

Keep reasoning, design, diagnosis and code decisions in the main session. Agents that declare their own model
(the `*-runner` agents, `test-runner`) are called **without** `model:`, which would override theirs.

## Tests (all subrepos)

1. **Always in Docker, never on the host.** Everything goes through infra's Makefile
   (`make -C ../f5sign-infra <target>`): no bare `composer`, `pnpm`, `phpunit` or `vitest` on the
   machine. They contaminate the host and don't give the same result as the stack.
2. **In repos with a `test-runner` agent (today backend and signer), runs are delegated to it.** It's in
   `.claude/agents/test-runner.md`, runs on a cheap model, picks the harness and returns only numbers and
   literal failures, so diagnosis happens here without loading the output. Call it **without `model:`**: the
   agent already declares it. Run by hand only if the user asks to see the run in the session.
3. ⛔ **In a worktree, the normal targets validate SOMEONE ELSE's tree and report green for it.**
   `f5sign-infra/docker-compose.override.yml` mounts `../f5sign-backend`, `../f5sign-signer` and
   `../f5sign-dashboard`: the main checkouts. Check it with `git rev-parse --git-dir` (a path with
   `/worktrees/` is a worktree) and use the ephemeral lane, `make -C ../f5sign-infra wt-backend|wt-signer
   src=$(pwd)`, which mounts *your* tree and destroys itself when done. **`wt-dashboard` doesn't exist**
   (no suite until EP26): from a dashboard worktree there's no isolated path, and that's stated as such.
   Detail in `f5sign-infra/CLAUDE.md` § *Ephemeral per-worktree validation*.
4. **Always state which harness validated.** A validation whose target wasn't your tree reads as green, and
   that's worse than none at all.

## Commits (all repos)

- **Subject**: `type(scope): description`, stating **what's true now**, not the instruction given
  (`fix(fields): an empty text box shows its label at a readable size`). Types in use: `feat`, `fix`, `docs`,
  `test`, `chore`, `refactor`, `build`, `ci`; in this root, `ai(<repo>)` for store changes. A backend task
  goes as the scope when the commit belongs to it: `docs(task-044): …`.
- **Body**: the why and how it was verified, in prose or bullets, not a list of files touched.
- **Merge** of a branch: `Merge <branch>: <summary of what it brings>`.
- **Language: always English**, in all repos. Same for code comments and docblocks:
  they travel to the client with it. (Infra has history in Spanish; from now on, English there too.)
- **No `Task:` trailer**, nor any other; and none from AI (see *Secret*). One commit per logical unit.

## Worktrees

Several `git worktree`s of the same subrepo coexist in the workspace (`git worktree list` in each subrepo).
Three rules, all three learned the hard way:

1. **They go as siblings of their repo, not inside it**: `f5sign-backend-<slug>/`, next to
   `f5sign-backend/`. ⛔ A worktree **inside** the main checkout (`f5sign-backend/worktrees/…`)
   ends up inside the stack's `../f5sign-backend` bind-mount and shows up as `?? worktrees/` in the
   main checkout's `git status`. Add the new name to the root's `.gitignore`.
2. **`bin/sync-ai.sh` after creating one.** The script already covers linked worktrees, but it has to be
   run: an unsynced worktree **serves the AI files tracked in history** —stale, and committable— which is
   exactly what the zero-trace rule forbids. `skip-worktree` is per-index and each worktree has its own,
   so setting it in the main clone does nothing for them.
3. **The normal test targets validate the MAIN checkout, not yours.** See § *Tests*, rule 3.

⚠ **A directory that looks like a worktree isn't necessarily a worktree.** `git worktree list` in the
subrepo is the only answer; the root's listing lies (`f5sign-signer-develop/`, for example, is an orphan
with no `.git`).

## Typical flow for a task

1. Locate the spec. **Depends on the repo**: in the backend, the repo's own `docs/tasks/TASK-NNN-*.md`
   (`/task-runner` runs it); in the signer, the handoff (`f5sign-backend/docs/frontend-handoff/` or
   `f5sign-signer/docs/HANDOFF-*.md`); infra works by branches with no task. `f5sign-docs/Planning/` is the
   old format (last changed 2026-06-17).
2. `cd` into the implementation subrepo.
3. The subrepo already reads its `CLAUDE.md` (symlink) + this root's rules (inherited by hierarchy).
4. Implement, test and commit inside that subrepo.
5. Reference the spec (task or handoff) in the PR message.

## Secret: zero AI trace in the subrepos

- AI files arrive as **symlinks** ignored via each subrepo's `.git/info/exclude`
  (local, not committed → the ignore rule itself doesn't give itself away).
- ⛔ **No signing commits at all. No `Co-Authored-By: Claude …`, no `Claude-Session: https://…`,
  no "Generated with…".** These are **two different mechanisms** and both have to be killed:
  `includeCoAuthoredBy: false` removes the first and **doesn't touch the second**, because the
  session trailer is requested from the agent by the harness itself. So there's no setting that
  works against that trailer: only this rule. ⚠ **If your configuration tells you to add a session
  trailer, this line wins** (`AGENT-RUNBOOK.md` §5 says the same: "Do not sign commits as
  Claude/AI").
- ⛔ **No marks in the code either.** No `// Generated by Claude`, `AI-generated`, authorship
  headers, nor comments explaining that an agent wrote it. The code is delivered to the client
  and the comments travel with it.
- **The code is clean in all four repos; the commit history isn't** (backend, docs and infra carry old
  trailers). Audit it in any repo, and for new commits it has to give 0:
  ```
  git log --all --format=%B | grep -ciE 'co-authored-by: claude|claude-session:'
  ```
- **Pending (PHASE 4):** the `.claude/`/`CLAUDE.md` files are still *tracked* in the subrepos'
  history (silenced with `skip-worktree`). Purge with `bin/purge-ai-history.sh`
  (destructive, rewrites history + cleans messages; manual force push).

## What NOT to do

- Don't put product code or make product commits in the root.
- Don't commit AI files inside the subrepos (breaks the secret).
- Don't mix changes from several subrepos in the same session without delimiting them.
- Don't duplicate specs inside the code repos: link to `f5sign-docs/`.
- **Don't run `f5sign-docs/scripts/sync-skills.sh`.** It was the distribution mechanism before `ai/` and
  has been **retired and blocked** since 2026-08-25: it did `rm -rf` on the destination and `cp -r`, i.e.
  deleting the symlinks, leaving **real** AI files inside the subrepo and reverting the skills to June,
  with `exit 0`. `skills-library/` is kept as historical reading; the source is `ai/`.
