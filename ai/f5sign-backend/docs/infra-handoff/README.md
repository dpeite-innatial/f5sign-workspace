# `docs/infra-handoff/` — what a backend measurement requires of `f5sign-infra`

A handoff record says **what a session in this repo measured about the environment it builds and validates
in, and what `f5sign-infra` could do about it**. It is written for a reader who is working in *that* repo,
quite possibly without this one checked out.

It is the sibling of [`../frontend-handoff/`](../frontend-handoff/README.md) and exists for the same
reason, aimed the other way.

## Why this directory exists

Cross-repo changes are **two coordinated PRs**, never one commit — the workspace rule that keeps each
project's history its own. So a finding made here and its fix over there are separated in time, by
different changesets, often by different sessions. Nothing carried the information across that gap.

The cost is already on the board. The most expensive environment defect this repo has measured — one open
transaction in *any* database of a Postgres cluster stalls another session's event-log relay, so a suite
goes red for something that is not the code under test — was proven by controlled experiment in a backend
session and written down as [`BL-138`](../BACKLOG.md). The sentence that matters to infra is one line of
that row (*one cluster per session, not one database per session*), and it sits in a backlog file inside a
repo an infra reader has no reason to open. Same for [`BL-135`](../BACKLOG.md): the dev image's `128M`
default is measured, recorded, and invisible from where the image is built.

**Nothing was missing on either side** — the measurement existed and the fix was cheap; they just had no
channel between them. This directory is that channel.

## The asymmetry with the frontend directory — read this before writing one

A frontend handoff is triggered by **a change we made** and states an obligation. An infra handoff is
triggered by **a measurement**, and it states **no obligation at all**. `f5sign-infra` owns its compose
files, its images and its Makefile; a backend session almost never has them open. So every record here is a
**recommendation, and must read as one**.

## When one gets written

Whenever a session measures something about the environment that infra owns and this repo cannot fix: the
shape or limits of a `wt-*` lane, a container default (memory, php.ini, image contents), which services the
suite actually reaches, cluster/database isolation, an env var the stack must inject, or a build artifact
whose staleness produces false failures.

**One file per finding set, not per release:** `TASK-NNN-<slug>.md`, or `YYYY-MM-DD-<slug>.md` when the
finding does not come from a task.

## Shape

Records are written in Spanish, as in the sibling directory; code and commit messages stay English.

```markdown
# Traspaso a infra — <what was measured, in one line>

| | |
|---|---|
| **Origen** | checkout / worktree · branch · commit `<sha>` |
| **Fecha** | YYYY-MM-DD |
| **Repo destino** | `f5sign-infra` (+ any other) |
| **Naturaleza** | measured finding · **recommendation, not a decision** |
| **Acción requerida** | none · lane parity · image change · Makefile target |
| **Status** | Pending · Applied (`f5sign-infra` `<pr|sha>`, YYYY-MM-DD) |

## Lo que se midió
## Qué significa para infra
## Lo que NO se ha verificado
## Cómo reproducirlo
```

## The four rules that keep it from lying

1. **Never make this the home of truth.** A finding's durable home is a [`docs/BACKLOG.md`](../BACKLOG.md)
   row or an ADR; this directory is a **carrier**. Cite the row, do not replace it — otherwise the finding
   dies with the handoff, and the next session re-derives it.
2. **The sample count travels with the claim.** Every measurement here is about something intermittent or
   environmental, and *"I checked"* does not measure that — [`BL-140`](../BACKLOG.md) records both
   sessions asserting a snapshot as fact on one night, in opposite directions. Write *"3 runs, all green"*,
   not *"green"*.
3. **Recommendations, never work orders — and say what you did not open.** If you did not read the compose
   file, the record must say so in its own section, because everything else in it will read as verified.
4. **Always name the origin commit.** It is the only thing that lets a reader tell whether the handoff is
   already applied or whether they are behind.

## ⚠ The weak spot, stated rather than hidden

**`Status` is hand-maintained, and nobody owns flipping it.** The infra PR that applies a handoff lands in
*another repo* and cannot edit this one, so `Applied` gets written here only if somebody comes back to do
it. That is precisely the shape of claim this repo keeps finding stale.

So: **treat `Status` as a hint, and the measurement plus its origin commit as the fact.** To know whether a
handoff is applied, re-run the reproduction the record ends with; do not trust the field. And when infra
does apply one, the durable update is the `BL-` row (rule 1), not this file.
