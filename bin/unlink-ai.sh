#!/usr/bin/env bash
# Revierte bin/sync-ai.sh: quita los symlinks, reactiva el seguimiento git y
# restaura los ficheros IA reales desde HEAD. Deja cada subrepo como estaba.
#
# Mirrors sync-ai.sh across linked worktrees: a worktree carries its own index, so a
# skip-worktree bit set there survives un-skipping the main clone. Reverting only the
# main clone would leave the worktree looking reverted while its bits stayed set.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS=(f5sign-backend f5sign-dashboard f5sign-docs f5sign-infra f5sign-signer)

unlink_from() {  # <checkout-dir> <label>
  local dst="$1" label="$2"
  local tracked=()
  mapfile -t tracked < <(git -C "$dst" ls-files .claude CLAUDE.md 2>/dev/null || true)
  if [ "${#tracked[@]}" -gt 0 ]; then
    printf '%s\0' "${tracked[@]}" | xargs -0 -r git -C "$dst" update-index --no-skip-worktree
  fi
  rm -rf "$dst/.claude" "$dst/CLAUDE.md"
  if [ "${#tracked[@]}" -gt 0 ]; then
    git -C "$dst" checkout -- "${tracked[@]}" 2>/dev/null || true
  fi
  echo "✓ $label: symlinks retirados, ficheros reales restaurados desde HEAD"
}

for repo in "${REPOS[@]}"; do
  dst="$ROOT/$repo"
  # -e, not -d: a linked worktree's `.git` is a file.
  [ -e "$dst/.git" ] || { echo "· $repo: no clonado, salto"; continue; }

  main="$(realpath "$dst")"
  while IFS= read -r wt; do
    [ -n "$wt" ] || continue
    [ -d "$wt" ] || continue
    [ "$(realpath "$wt")" = "$main" ] && continue
    unlink_from "$wt" "$repo → $(basename "$wt") (worktree)"
  done < <(git -C "$dst" worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p')

  unlink_from "$dst" "$repo"
done
