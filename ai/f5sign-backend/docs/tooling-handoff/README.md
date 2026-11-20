# `docs/tooling-handoff/` — what a run of the skill stack learned, and what changed in the store

A tooling handoff record says **what running the execution stack over a real task in this repo taught,
what was changed in a skill because of it, and what was deliberately left for the user to decide.** It is
written for a reader working in the **workspace-root repo**, which owns the skills — quite possibly
without this one open.

## Why this directory exists

The skills are **not in this repo**. `CLAUDE.md` and `.claude/skills/<name>/` here are **symlinks into the
workspace-root store** — `ai/f5sign-backend/…` for what belongs to this repo, `ai/shared/` for what several
repos share — ignored locally so no trace of them lands in this repo's history.

That has two consequences, and they pull in opposite directions:

1. **Editing through the symlink edits the store, immediately.** `.claude/skills/task-runner/SKILL.md` and
   `ai/f5sign-backend/.claude/skills/task-runner/SKILL.md` are the same file. So a record that merely *asks*
   somebody to make a change the author could have made is the gap this directory exists to close: the
   default is **make the edit, then write the record**. What survives as a proposal is only what is not the
   agent's call — anything that changes gate policy (what blocks a run, what a validation demands of the
   person running it) belongs to the user.
2. **But the edit lands in another repo.** Cross-repo changes are **two coordinated PRs, never one commit**
   (workspace rules 1 and 4). The skill edit does not appear in this repo's `git status`, does not travel on
   this repo's branch, and cannot be committed from here. Whoever commits it does so in the root repo — and
   this record is the only thing that tells them what it was for.

Before this directory existed, a lesson from a run had exactly three homes and none of them worked: the
session summary (dies with the session), `var/task-runner/TASK-NNN/` (gitignored, and root-owned besides),
or the task's `§Open follow-ups` plus a `docs/BACKLOG.md` row — which are for **this repo's** work, and a
skill edit is not this repo's work.

## When one gets written

After a run of `/task-runner` or any skill in its stack, whenever:

- something the skill **says** produced a wrong outcome, or something it **does not say** cost real work;
- a precondition cannot be satisfied in a legitimate environment;
- something the skill anticipated **worked** — worth recording so nobody "fixes" it away;
- **a skill was actually edited** — always, because the store carries the *what* and only this carries the
  *why*.

Not for the outcome of the task itself: that belongs in the task's `.md` and in
[`docs/BACKLOG.md`](../BACKLOG.md).

**One file per run, not per skill:** `TASK-NNN-<slug>.md`, or `YYYY-MM-DD-<slug>.md` when it does not come
from a task.

## Shape

```markdown
# Traspaso a tooling — <qué se aprendió, en una línea>

| | |
|---|---|
| **Origen** | rama · commit `<sha>` · la corrida que lo produjo |
| **Fecha** | YYYY-MM-DD |
| **Store afectado** | ruta(s) en el repo raíz: `ai/f5sign-backend/.claude/skills/<skill>/SKILL.md` |
| **Naturaleza** | cambios ya aplicados · propuestas pendientes de decisión · confirmaciones |
| **Acción requerida** | commitear el store en el repo raíz · decidir las propuestas abiertas |
| **Status** | Pending · Applied (`<repo>` `<pr|sha>`, YYYY-MM-DD) |

## Lo que se cambió en la skill      — una entrada por cambio: qué decía, qué pasó, qué dice ahora
## Lo que NO se cambió, y por qué    — lo que es decisión del usuario, con su evidencia
## Confirmaciones                    — lo que ya funcionaba y no hay que "arreglar"
## Cómo verificarlo
```

## The four rules that keep it from lying

1. **Quote the skill as it read *before*, verbatim, and say what it reads now.** A paraphrase rots against
   the store, and without the old wording a reader cannot tell whether the file in front of them is pre- or
   post-change.
2. **Give the store path of every file touched**, as seen **from the root repo**. `.claude/skills/…` is this
   repo's view of it; the reader is standing in the other one.
3. **Keep *applied* and *proposed* visibly apart.** A proposal that reads as done is worse than no record:
   it invites everyone to assume somebody else decided. State the evidence for a proposal and stop there.
4. **Cite by section title or by the quoted clause, never by line number.** Skills get edited and every
   number moves ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 7).

## ⚠ The weak spot, stated rather than hidden

**`Status` is hand-maintained and nobody owns flipping it** — the same hole
[`docs/frontend-handoff/README.md`](../frontend-handoff/README.md) names, one repo over: the commit that
lands the change happens in the root repo, which cannot edit this file.

There is a second one, specific to this directory: **a record ages against a store it cannot see.** A skill
can be edited, renamed or retired in the root repo and nothing here reddens — no gate in this repo reads
`ai/`, and it should not.

So: **the store is the fact, this record is the reason.** To know whether a change is still in force, read
the `SKILL.md` — through the symlink it is one `cat` away, and it always wins over what is written here.
