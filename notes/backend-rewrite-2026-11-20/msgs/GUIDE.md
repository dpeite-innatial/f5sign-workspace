# Writing the commit messages of the rewritten history

You write one git commit message per input row. The repository is a PHP/Symfony e-signature backend
written by two developers, Daniel and Miguel. The history is being cleaned before it is handed over:
the messages must read as written by those two people, in plain English, with no trace of AI tooling.

## Input row fields
- `id`, `kind`, `author`, `date`, `lines` (size of the change).
- `sources`: the original message(s) this commit replaces (subject + body). Several sources means several
  original commits were squashed into this one: write ONE message covering them.
- `kind = part` / `split-final`: one oversized original commit is being split into a short series by layer;
  `part` says which slice ("2 of 5"), `layer` and `files_in_this_part` say what this slice contains. Write a
  message for THIS slice only, as a step of building the feature (e.g. "feat(storage): add the custody
  aggregate and its obligations" for the domain slice, "test(storage): cover custody destruction and
  erasure" for the tests slice). The `split-final` slice may carry the short "why" of the whole feature.
- `kind = fakemerge`: a run of commits (`branch_commits`) now lives on a feature branch merged with --no-ff.
  Write the merge message `Merge <branch>: <what the branch brings>` and choose a good branch name
  (`feat/<kebab-words>` or `fix/<kebab-words>`, 2-5 words, describing the work; replace a poor
  `suggested_branch` like `feat/wip` or `feat/tests`).
- A real merge (has `merged_branch`): keep the form `Merge <branch>: <summary>` (or `Merge develop into
  <branch>: …` when that is what it was), with a short summary; keep the branch name as given.

## Output
JSON lines: `{"id": <id>, "message": "<subject>\n\n<body>"}` (no body: just the subject, no trailing
newline). Same ids as the input, every id exactly once. Write the file with a Python script
(`json.dumps(..., ensure_ascii=False)`), never by hand.

## Style
- Subject: Conventional Commits, `type(scope): summary` — types feat, fix, docs, test, chore, refactor, build,
  ci, perf. Lowercase after the colon, imperative or "what is true now" ("a void after another ending is
  refused by name"); no final period; aim for <= 72 characters, never over 90. Keep the original scope and
  any task id in the scope when it was there (`docs(task-044): …`). Never just "wip": say what changed.
- Body: optional. About a fifth of the commits need none. Otherwise 1-5 short lines of plain prose (hard limit:
  6 lines, one paragraph, two at most): why the change exists and, when it matters, how it was checked. Wrap at ~72 columns. No headings, no bullet
  walls; at most 3 bullets when a list really helps.
- Shorten hard: the originals are often very long. Keep the one or two facts that matter, drop the rest.
- Vary naturally: two people wrote these over seven months; do not make every message the same shape.

## Must never appear
- Any mention of Claude, AI, agents, subagents, models (Opus, Sonnet, Haiku), sessions of a tool, skills,
  task-runner, "slice N", plans under var/, prompts, reviewers that were agents, "the orchestrator",
  CLAUDE.md, `.claude`, "authoring rule N", "repo rule N", co-author or session trailers.
- The glyphs ⚑ ⛔ ⚠ ⛑ or emoji.
- Spanish: translate any Spanish into English.
- Internal workspace details: the "workspace" root repo, scratchpads, notes/, symlinks to a store.
- Environment vocabulary of the old tooling: "main checkout", "lane", "wt-backend", "worktree", "harness",
  "hermetic tiers", "sabotage", "gates". Say it plainly: "the full suite passes", "tested against a real DB".
- Line numbers and counts of things that only matter to the tooling (e.g. "10693 tests, 179329 assertions"
  is fine only rarely; prefer "the full suite passes").

## Allowed
- Task ids (TASK-078) and backlog ids (BL-528) as ticket references.
- ADR references (ADR-0094).
- Short commit hashes from the sources may be kept verbatim if the sentence needs them (they are remapped
  later); otherwise drop them.
