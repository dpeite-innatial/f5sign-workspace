#!/usr/bin/env bash
# PreToolUse hook on Bash: refuses a wait loop whose `pgrep -f` / `pkill -f` pattern matches the loop itself.
#
# Why: `until ! pgrep -f "wt-validate.*my-worktree" ...; do sleep 3; done` runs inside a shell whose own
# command line contains that pattern, so pgrep always finds the loop and the loop never ends. Subagents
# (test-runner, slice-implementer) left such loops behind for hours on TASK-067 (2026-10-21) — one ran 3h17m
# after its agent had reported — and on earlier tasks; a memory note about it did not stop it, because the
# agents that write the loop never read it.
#
# Refuses (exit 2, the reason goes back to the model) a command that has a `while`/`until` loop AND a
# `pgrep -f` / `pkill -f` whose pattern has no bracket class. The bracket trick (`pgrep -f '[w]t-validate'`)
# makes the regex unable to match its own text, so it passes; so does any command without a loop.
# Fails open on anything it cannot parse: blocking a call it does not understand would break unrelated work.
set -uo pipefail

input=$(cat)
cmd=$(jq -r '.tool_input.command // empty' <<<"$input" 2>/dev/null) || exit 0
[ -z "$cmd" ] && exit 0

# A loop at all? (word boundary: `while`/`until` as keywords)
grep -qE '(^|[;&|({[:space:]])(while|until)[[:space:]]' <<<"$cmd" || exit 0

# Every pgrep/pkill -f pattern in the command, quotes stripped.
patterns=$(grep -oE 'p(grep|kill)([[:space:]]+-[a-zA-Z]+)*[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*([[:space:]]+-[a-zA-Z]+)*[[:space:]]+("[^"]*"|'"'"'[^'"'"']*'"'"'|[^[:space:];|&)]+)' <<<"$cmd" \
  | sed -E 's/.*[[:space:]]("[^"]*"|'"'"'[^'"'"']*'"'"'|[^[:space:];|&)]+)$/\1/; s/^["'"'"']//; s/["'"'"']$//')
[ -z "$patterns" ] && exit 0

while IFS= read -r p; do
  [ -z "$p" ] && continue
  case "$p" in
    *\[*\]*) continue ;;   # bracket class: cannot match its own command line
  esac
  cat >&2 <<EOF
Refused: this wait loop uses \`pgrep/pkill -f '$p'\`, and that pattern also matches the loop's own command
line, so the loop never ends (it ran for hours after its agent reported, TASK-067).
Do one of:
  - wait for the work with the Bash tool itself: run the long command with run_in_background and act on
    its completion notification (no loop at all);
  - or make the pattern unable to match itself with a bracket class, e.g. pgrep -f '[${p:0:1}]${p:1}'.
EOF
  exit 2
done <<<"$patterns"

exit 0
