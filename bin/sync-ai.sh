#!/usr/bin/env bash
# Distribuye la config IA del store central `ai/` a cada subrepo mediante symlinks
# y silencia los ficheros (aún trackeados) con --skip-worktree para que `git status`
# del subrepo quede limpio. Idempotente. Revertir con bin/unlink-ai.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI="$ROOT/ai"
REPOS=(f5sign-backend f5sign-dashboard f5sign-docs f5sign-infra f5sign-signer)

rel_link() {  # <target-real> <link-path>
  local target="$1" link="$2" dir
  dir="$(dirname "$link")"
  mkdir -p "$dir"
  rm -rf "$link"
  ln -s "$(realpath --relative-to="$dir" "$target")" "$link"
}

for repo in "${REPOS[@]}"; do
  src="$AI/$repo"; dst="$ROOT/$repo"
  [ -d "$src" ] || { echo "· $repo: sin store, salto"; continue; }
  [ -d "$dst/.git" ] || { echo "· $repo: no clonado, salto"; continue; }

  # CLAUDE.md
  if [ -f "$src/CLAUDE.md" ]; then
    rm -rf "$dst/CLAUDE.md"
    rel_link "$src/CLAUDE.md" "$dst/CLAUDE.md"
  fi

  # .claude/ : dir real; symlinks a nivel de hoja (descubrimiento robusto)
  if [ -d "$src/.claude" ]; then
    rm -rf "$dst/.claude"
    mkdir -p "$dst/.claude"
    for entry in "$src/.claude"/*; do
      [ -e "$entry" ] || continue
      name="$(basename "$entry")"
      if [ -d "$entry" ] && { [ "$name" = "skills" ] || [ "$name" = "agents" ]; }; then
        mkdir -p "$dst/.claude/$name"
        for child in "$entry"/*; do
          [ -e "$child" ] || continue
          rel_link "$(realpath "$child")" "$dst/.claude/$name/$(basename "$child")"
        done
      else
        rel_link "$(realpath "$entry")" "$dst/.claude/$name"
      fi
    done
  fi

  # Silenciar en git los paths IA aún trackeados (no commitea; reversible)
  mapfile -t tracked < <(git -C "$dst" ls-files .claude CLAUDE.md 2>/dev/null || true)
  if [ "${#tracked[@]}" -gt 0 ]; then
    printf '%s\0' "${tracked[@]}" | xargs -0 -r git -C "$dst" update-index --skip-worktree
  fi
  echo "✓ $repo: symlinks creados, ${#tracked[@]} paths trackeados silenciados"
done
