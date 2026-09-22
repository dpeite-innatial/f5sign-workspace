---
name: pr-ready
description: 'Closes the task by opening the Pull Request against develop. Pushes the branch, generates a title (conventional commits) and PR body (task + verified properties + validations table with the declared harness + test plan derived from the diff), and marks it draft if warnings are still active. Use it with /pr-ready TASK-NNN. Trigger with "create PR", "open pull request", "close task and publish", "pr ready".'
---

# PR Ready

Final closure. Only invoked if the previous gates passed (or the user forced it to continue in supervised
mode).

## Invocation

```
/pr-ready TASK-NNN
/pr-ready TASK-NNN --draft      # force draft
/pr-ready TASK-NNN --ready      # force ready (careful)
```

## Inputs

- `var/task-runner/TASK-NNN/` — artifacts and reports from the previous phases
- The task's `.md`, already edited by `task-close`

## Outputs

- Branch pushed to `origin`, PR opened against **`develop`**
- Follow-up commit with the PR URL in the `.md`
- `var/task-runner/TASK-NNN/pr-ready.report.md` — ⚠ `var/` may be owned by root and not let you write; in
  that case, use the session's scratchpad and **say where it ended up** (`task-runner` Phase 0 documents this)
- JSON: `{"status":"pass|fail","summary":"...","prUrl":"...","prNumber":N,"branchName":"...","draft":bool}`

## Execution

### Step 1 — Pre-check

- [ ] `git status --short` clean, except for what's expected (the `.md`, `docs/`, `.env*`).
- [ ] The branch follows the repo's actual convention, `<type>/<slug>` (`feat/notification-email-html`,
      `docs/task-conventions`). ⚠ **No branch in this repo has ever carried the task id in its name**,
      so don't require `feat/TASK-NNN-*`: that pattern fails on 100% of real branches. The id goes in the
      PR body.
- [ ] `gh` exists. ⛔ **Today it isn't installed** — neither on the host nor in the `f5sign/backend:dev`
      image, and infra's Makefile has no target for it — so this skill **can't complete its work on this
      machine** and the PR gets opened by hand. `status: fail`, `summary: "gh CLI absent: open the PR
      manually"`, and **don't** diagnose it as an authentication problem: there's no binary to authenticate.
- [ ] **The base is `develop`.** `master` is the release branch; product work isn't integrated there
      directly.

⛔ **No defensive squashing.** This repo integrates PRs with multiple commits and merges from `develop`;
counting commits and doing a `git reset --soft` to leave a single one destroys useful history and forces
`--force-with-lease` for no gain. If the commits are coherent and explain their *why*, they're fine as they
are.

### Step 2 — Push

```bash
git push -u origin <branch>
```

If the branch already exists on the remote and the push isn't fast-forward → **stop**: `status: fail` with
the reason. Never `--force`; `--force-with-lease` only if the user explicitly asks for it and knows what it
discards.

### Step 3 — Draft or ready

Read the workspace reports and count unresolved WARNs. With WARNs → `--draft`. Without WARNs → ready.
`--draft` / `--ready` from the argument takes precedence.

⚑ **A declared `skipped` isn't a WARN, but it isn't a PASS either.** `perf-smoke-backend` is skipped today
for lack of `composer perf:seed`; it goes into the body as *skipped, with its reason*, not as green.

### Step 4 — Title

`{type}({scope}): {what it does, in the imperative}`, ≤70 chars. The `type` comes from what the diff does
(`feat`, `fix`, `docs`, `chore`, `refactor`, `test`), not from a `Tipo` field — this task format doesn't
have one. The `scope` is the BC or subsystem touched (`envelope`, `notification`, `session`,
`foundation`…). If the change breaks a published contract, `!` before the colon.

### Step 5 — Body

```markdown
## Task
[TASK-NNN](docs/tasks/TASK-NNN-{slug}.md) — {title}

## Summary
{2-3 lines from context-digest.md § Task summary}

## Changes
- **Domain / Application / Infrastructure / Contract / UI:** {files by layer}
- **Tests:** {files}
- **Docs:** {ADRs, docs/, .env*}

## Verified properties
- [x] {claim from the verification section} → {test that proves it}
- [ ] {one that couldn't be proven} → {why the harness doesn't reach it}

## Validations run
| Skill | Status | Notes |
|---|---|---|
| spec-lint | PASS | — |
| task-validate-backend | PASS | N tests · covered-MSI X% · **harness: {route used}** |
| doctrine-guard | PASS/n-a | — |
| contract-check-backend | PASS/n-a | — |
| security-audit-core | PASS | — |
| eidas-compliance | PASS/n-a | — |
| perf-smoke-backend | skipped | `composer perf:seed` doesn't exist |
| docs-sync | PASS/n-a | — |

## Notes for the reviewer
{WARNs, declared debt, ADRs whose Status moved in this changeset, and new Open follow-ups}

## Test plan
{derived from what the diff touches, not from tags}
- [ ] {if it touches UI/Http or config/routes:} call the endpoint for each declared case, and check that
      the generated OpenAPI says the same thing as the code
- [ ] {if it touches migrations/:} `migrate`, verify the schema, `migrate --dry-run` downward and check
      reversibility. If it writes rows the domain reads: enumerate the aggregate states the row falls under
- [ ] {if it touches a Contract/Event/ or a payload:} check that no required field was added
      (`Row::optionalString()`) and that no `event_type` was renamed in place
- [ ] {if it touches a worker or a reactor:} drain (`worker-down` → depth 0) → deploy → `worker-up`
```

**The table's `harness` field is mandatory.** A PR that claims green without saying which tree and which
services ran is exactly the failure `task-validate-backend` documents in its precondition: the stack
mounts `../f5sign-backend`, so a green pulled from the wrong checkout says nothing about the PR's code.

### Step 6 — Create the PR

```bash
gh pr create --base develop --head <branch> \
  --title "{title}" --body-file {tmp} [--draft]
```

If there's already an open PR for the branch (`gh pr list --head ...`), push and **update the existing
one**; don't create another. Report it in the summary.

### Step 7 — Labels (only the ones that exist)

`gh label list` first; apply only the intersection. **Don't invent labels** for phase/epic/tag: those
fields don't exist in this task format, and creating ghost labels clutters the repo.

### Step 8 — PR URL in the `.md`

Update the `.md`'s `Status` so it names the branch and the PR (README §3: a `Status` that claims code
must name a branch or commit) and commit **on top**, without amending:

```bash
git add {mdPath} && git commit -m "docs(tasks): point TASK-NNN at its PR" && git push
```

## Failure handling

- **Push rejected (branch protection):** `status: fail`, say which rule was violated.
- **`gh pr create` fails:** `status: fail`. ⚠ Before suggesting `gh auth login`, check that the binary
  exists: today **it isn't installed**, and confusing absence with missing credentials sends the user to
  authenticate something that isn't there.
- **Someone merged into `develop` in the meantime:** `status: fail`, `summary: "develop merge required"`.
  Don't rebase automatically. ⚑ If the merge touches `.claude/` or `CLAUDE.md`, it may abort due to
  `skip-worktree`: `bin/unlink-ai.sh` → merge → `bin/sync-ai.sh` from the workspace root.

## What it does NOT do

- Doesn't merge the PR.
- Doesn't assign reviewers or milestones.
- Doesn't run CI by hand.
- Doesn't squash or rewrite history.
