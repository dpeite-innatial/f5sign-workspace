#!/usr/bin/env bash
# Distribuye la config IA del store central `ai/` a cada subrepo mediante symlinks
# y silencia los ficheros (aún trackeados) con --skip-worktree para que `git status`
# del subrepo quede limpio. Idempotente. Revertir con bin/unlink-ai.sh.
#
# Covers a repo's linked git worktrees as well as its main checkout. A linked
# worktree has `.git` as a FILE, not a directory, so the `-d "$dst/.git"` test this
# script used to gate on silently skipped every one of them -- and an unsynced
# worktree is worse than an absent one: it serves the AI files TRACKED IN HISTORY
# (stale, and stale by however long the purge has been pending) and leaves them
# committable, which is exactly what the workspace's "cero rastro de IA en los
# subrepos" rule forbids. Found when f5sign-backend-develop, the worktree the infra
# validation lane runs against, turned out to be serving July's skills.
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

# Point one checkout at the store. Takes the checkout dir so it can serve a main
# clone and a linked worktree identically -- they differ only in what `.git` is.
sync_into() {  # <checkout-dir> <store-dir> <label>
  local dst="$1" src="$2" label="$3"

  # CLAUDE.md
  if [ -f "$src/CLAUDE.md" ]; then
    rm -rf "$dst/CLAUDE.md"
    rel_link "$src/CLAUDE.md" "$dst/CLAUDE.md"
  fi

  # .claude/ : dir real; symlinks a nivel de hoja (descubrimiento robusto)
  if [ -d "$src/.claude" ]; then
    rm -rf "$dst/.claude"
    mkdir -p "$dst/.claude"
    local entry name child
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

  # Silenciar en git los paths IA aún trackeados (no commitea; reversible).
  # skip-worktree is per-index and a worktree has its own index, so this has to run
  # once per checkout -- setting it on the main clone does nothing for a worktree.
  local tracked=()
  mapfile -t tracked < <(git -C "$dst" ls-files .claude CLAUDE.md 2>/dev/null || true)
  if [ "${#tracked[@]}" -gt 0 ]; then
    printf '%s\0' "${tracked[@]}" | xargs -0 -r git -C "$dst" update-index --skip-worktree
  fi
  echo "✓ $label: symlinks creados, ${#tracked[@]} paths trackeados silenciados"
}

for repo in "${REPOS[@]}"; do
  src="$AI/$repo"; dst="$ROOT/$repo"
  [ -d "$src" ] || { echo "· $repo: sin store, salto"; continue; }
  # -e, not -d: a linked worktree's `.git` is a file.
  [ -e "$dst/.git" ] || { echo "· $repo: no clonado, salto"; continue; }

  sync_into "$dst" "$src" "$repo"

  # Linked worktrees of this repo. `worktree list` prints the main checkout too, so
  # compare canonical paths and skip it rather than syncing it twice.
  main="$(realpath "$dst")"
  while IFS= read -r wt; do
    [ -n "$wt" ] || continue
    [ -d "$wt" ] || continue
    [ "$(realpath "$wt")" = "$main" ] && continue
    sync_into "$wt" "$src" "$repo → $(basename "$wt") (worktree)"
  done < <(git -C "$dst" worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p')
done

cat <<'NOTE'

⚑ Un merge que toque `.claude/` o `CLAUDE.md` puede abortar en un checkout
   sincronizado: skip-worktree oculta esos paths y git se niega a sobrescribirlos.
   Si pasa: bin/unlink-ai.sh → merge → bin/sync-ai.sh.
NOTE
