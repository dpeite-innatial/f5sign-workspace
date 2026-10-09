#!/usr/bin/env bash
# PreToolUse hook on Agent: refuses a subagent that would silently inherit the session's model.
#
# Why: the session runs on the top model, and a subagent launched without `model:` inherits it. Measured
# on the backend transcripts of 2026-09-21..10-08: 105 of 147 general-purpose launches carried no model,
# and those agents were ~21 % of all tokens read. The rule already lived in the root CLAUDE.md
# ("Cost: delegate mechanical work"), and a rule nothing enforces is not followed.
#
# Passes when:
#   - the call names a model (any: an explicit `opus` is a decision, not an accident);
#   - the agent's own definition declares one (`.claude/agents/<type>.md`, searched upwards from the cwd,
#     then ~/.claude/agents) — the *-runner agents and test-runner are called WITHOUT `model:` on purpose;
#   - it is a fork (a fork ignores `model:`; whether to fork is a separate judgement);
#   - it is a plugin agent (`plugin:name`) or one this script cannot resolve: unknown is let through,
#     because blocking a call the hook does not understand would break work it was not written for.
# Refuses (exit 2, the reason goes back to the model) the built-ins that inherit by default and any
# local agent whose definition declares no model.
set -euo pipefail

input=$(cat)
model=$(jq -r '.tool_input.model // empty' <<<"$input")
type=$(jq -r '.tool_input.subagent_type // "general-purpose"' <<<"$input")
cwd=$(jq -r '.cwd // empty' <<<"$input")

[ -n "$model" ] && exit 0
[ "$type" = fork ] && exit 0
case "$type" in *:*) exit 0 ;; esac

find_def() {
  local d=${cwd:-$PWD}
  while [ -n "$d" ] && [ "$d" != / ]; do
    [ -f "$d/.claude/agents/$type.md" ] && { echo "$d/.claude/agents/$type.md"; return; }
    d=$(dirname "$d")
  done
  [ -f "$HOME/.claude/agents/$type.md" ] && echo "$HOME/.claude/agents/$type.md"
  return 0
}

def=$(find_def)
if [ -n "$def" ]; then
  m=$(sed -n '2,/^---$/p' "$def" | sed -n 's/^model:[[:space:]]*//p' | head -1 | tr -d '[:space:]')
  [ -n "$m" ] && [ "$m" != inherit ] && exit 0
  reason="the agent '$type' ($def) declares no model, so it would inherit the session's"
else
  case "$type" in
    general-purpose|Explore|Plan|claude) reason="'$type' inherits the session's model when the call names none" ;;
    *) exit 0 ;;
  esac
fi

cat >&2 <<EOF
Agent launch refused: $reason.
Pass \`model:\` explicitly (workspace CLAUDE.md, "Cost: delegate mechanical work to a cheaper model"):
  haiku  — extract and report: reading large files or logs, listing, counting, checking paths exist
  sonnet — rewrite by fixed rules (translations, renames, prose sweeps) and closed-brief implementation
  opus   — design, diagnosis and judgement, when the brief genuinely needs it (say so: model: "opus")
Agents that declare their own model (*-runner, test-runner, plan-runner, slice-*) are called WITHOUT it.
EOF
exit 2
