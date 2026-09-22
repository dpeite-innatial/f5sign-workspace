# ai/ — how the AI config is written

These three habits are already present in the best-written parts of the store. They stay here as a
rule because what rots isn't the judgment, it's remembering.

1. **Cite, don't replicate.** If the fact lives in another file —a Makefile target, a compose
   service, a script's default— **link it and say where to enumerate it**; don't copy the list. A
   text that says *"enumerate the gates in `scripts/wt-validate.sh`"* can't fall behind. The one
   that listed them can: on 2026-08-18 at 16:11 a skill wrote that the lane ran a single gate, at
   18:18 `f5sign-infra` put four into it, and the skill didn't find out until 08-25 — its own
   `CLAUDE.md` had already corrected it on 08-19.
2. **Correct it in place and without leaving history in the text.** What it said before is already in
   the root's `git log`: the commit message says what the text claimed, since when it was false, and
   why it changed. A "⚑ corrected on day X, it used to say Y" inside the file loads in every session
   and doesn't help do anything better. **The only exception** is when the old claim is still
   circulating somewhere else (a runbook, a memory, another repo): there a visible line does go in,
   "if you read X somewhere else, it's from before <date> and no longer holds," because it stops
   someone from believing it.
3. **Every `make` target, path, variable or `BL-`/`ADR-` you name has to exist, and keep meaning the
   same thing.** It's checked in a second and fails in both directions: the generic `task-runner`
   pointed to `f5sign-docs/skills-library/` and to `sync-skills.sh` as the live source of the skills
   —both files exist, but had been retired since June, and running the second would have broken the
   secret—; and `make migrate-status` existed for four days without `f5sign-infra`'s table naming it,
   offering instead the two forms that lie about the DB's state.
