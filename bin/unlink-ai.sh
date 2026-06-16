#!/usr/bin/env bash
# Revierte bin/sync-ai.sh: quita los symlinks, reactiva el seguimiento git y
# restaura los ficheros IA reales desde HEAD. Deja cada subrepo como estaba.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS=(f5sign-backend f5sign-dashboard f5sign-docs f5sign-infra f5sign-signer)

for repo in "${REPOS[@]}"; do
  dst="$ROOT/$repo"
  [ -d "$dst/.git" ] || { echo "· $repo: no clonado, salto"; continue; }
  mapfile -t tracked < <(git -C "$dst" ls-files .claude CLAUDE.md 2>/dev/null || true)
  if [ "${#tracked[@]}" -gt 0 ]; then
    printf '%s\0' "${tracked[@]}" | xargs -0 -r git -C "$dst" update-index --no-skip-worktree
  fi
  rm -rf "$dst/.claude" "$dst/CLAUDE.md"
  if [ "${#tracked[@]}" -gt 0 ]; then
    git -C "$dst" checkout -- "${tracked[@]}" 2>/dev/null || true
  fi
  echo "✓ $repo: symlinks retirados, ficheros reales restaurados desde HEAD"
done
