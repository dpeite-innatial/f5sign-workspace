---
name: v1-touched-file-hygiene
description: Before committing, audit every file a task touched for rot-prone prose and out-of-repo references, fixing or tagging them so the repo stays self-contained. Use when preparing to stage/commit changes, or when asked to "run the hygiene pass" / "clean touched files" / review changed files for rot and dangling pointers.
---

# Touched-file hygiene

Audit **every file a task touched** — before committing — for two things that quietly rot a repo: **rot-prone prose** and **out-of-repo references**. Fix or tag what's found, even when it's outside the task's scope.

**Why this exists:** keep the repo self-contained for an agent that has only *this* repo, without ever paying for a costly full-repo sweep — the cost amortizes into work already happening. A review step (PR) catches legitimate misses downstream, so aim for **high coverage, not perfection** — 99% beats the 0% you get from skipping the pass.

## The one rule that makes this work

This is an **AUDIT, not a SEARCH.** The failure mode is reaching for `grep` + batch-staging to "be efficient" — but a grep only finds what you predict, and the entire point is to catch what you *didn't* (a dead `§` anchor, a stale version pin, a forgotten `../../` link). So the **reading is delegated to a dedicated read-only subagent, one file at a time**, that cannot grep-shortcut or edit. You keep the judgment and the edits.

**Never substitute a grep for reading a file in this pass.** If you catch yourself writing a grep to *review*, stop — that's the search reflex; this is an audit.

## Procedure

1. **Enumerate** the touched files: `git status --porcelain` (include untracked). This is listing, not reviewing.
   - Unstage everything first (`git reset`) so that **staging a file becomes its per-file "reviewed & done" signal.**

2. **Flag — delegated, per file.** For each touched file, dispatch the `v1-hygiene-flagger` subagent (Agent tool, `subagent_type: v1-hygiene-flagger`) with just the file path. It reads the whole file and returns flagged candidates (category **A** rot / **B** out-of-repo, with line + context).
   - You may fan these out in parallel — each agent still does a full dedicated read, so thoroughness is preserved; only the reads parallelize. The efficient path and the thorough path are the same path here.
   - **Fallback:** if `v1-hygiene-flagger` isn't available in this session's registry, dispatch a general-purpose agent with the same instructions (read the *entire* file; flag A/B candidates; over-flag; report line + text + category + why + context; no fixes, no judgment).

3. **Judge + act — you, file by file, visible.** For each file's flags, decide and edit:
   - **In-repo reference** (path/symbol that resolves inside this repo) → fine, leave it. *Verify before assuming out-of-repo.*
   - **Rot-prone prose** → fix: drop the count, make the version pin agnostic, replace currency words with stable phrasing, etc.
   - **Out-of-repo reference** → pick one:
     - **Re-home** to the in-repo equivalent if one exists (source docblock, in-repo doc, ADR).
     - **Drop** if it carries no value for an agent with only this repo.
     - **`OFFREPO:` tag** if the reference is genuinely unavoidable *right now* (forward/roadmap tracking; design-repo why-history not yet migrated): `<!-- OFFREPO: <ref> — <why / when to clean> -->` in markdown, or `// OFFREPO: ...` in code. `grep -rn OFFREPO` then enumerates the **tagged** debt — an inventory *seeded from this task's touched files and grown one task at a time*, not a repo-complete census; don't mistake the grep for complete. **Tag only genuine debt** — a ref an agent would try to follow but can't. A deliberately-documented cross-repo *bridge* (an ADR crosswalk row, a self-labeled "(doc repo)" pointer that *is* the designed why-history link) is not debt; tagging it pollutes the inventory with false positives. Leave it.
     - **Defer the *re-home* of a pre-existing *haystack*** (a file dense with provenance refs) — re-homing dozens of refs inline mid-commit is the expensive grind to skip. But **tagging is not grinding**: drop one consolidated `OFFREPO:` line per touched file listing its deferred refs, so the deferral is greppable, not silent. The re-home stays a tracked scoped item.
   - Then `git add <file>`. Move to the next file. **Do not batch-stage.**

4. **Validate + summarize.** If code changed, re-run the repo's checks (lint / static analysis / tests). Summarize what was cleaned, what was `OFFREPO`-tagged, and what was deferred to a tracked task.

## Judgment heuristics

- **In-repo vs out-of-repo topology.** "Out-of-repo" means *dead for an agent that has only this repo.* A path or symbol that resolves inside this repo is fine — verify before re-homing.
- **Design-repo / planning docs use markers by design.** If the file *is* a design-repo or planning doc (a ROADMAP, a conventions doc), its own markers (`DEC-*`, `§N`, phase IDs) are its native vocabulary — do **not** force code-repo self-containment there. This skill's target is the **code** repo.
- **Clean your own first.** References *this task introduced* get cleaned or tagged immediately, no exceptions.
- **Pre-existing haystacks → tag now, re-home later.** A file saturated with provenance refs is a scoped *re-home* task, not an inline fix mid-commit — but still drop a per-file `OFFREPO:` marker so the deferred refs are greppable. Tagging is cheap; re-homing is the grind. Coverage accrues one task at a time.

## Notes

- `v1-hygiene-flagger` is read-only (`tools: Read`) — it physically cannot edit or grep-shortcut; it *must* read. That tool restriction is the structural guarantee. All editing and judgment stay here, in the main context.
- Run this skill in the **main context** (do not fork it) — a forked skill runs as a subagent, and subagents can't spawn the flagger subagents this procedure needs.
