#!/usr/bin/env bash
# =============================================================================
# FASE 4 — PURGA DE HISTORIAL  (DESTRUCTIVA · reescribe historial · NO auto-push)
# -----------------------------------------------------------------------------
# Borra de TODO el historial de cada subrepo las rutas `.claude/` y `CLAUDE.md`,
# y limpia de los mensajes de commit los rastros de IA (Co-Authored-By: Claude,
# "Generated with Claude", 🤖). Reescribe TODOS los SHAs.
#
# NO se ejecuta sin pasar explícitamente:  --yes-rewrite-history
# Y aun así NO hace push: el `git push --force` se deja MANUAL tras revisar.
#
# Antes de lanzarlo, OBLIGATORIO:
#   1) Confirmar que nadie externo ha clonado y que no hay PRs abiertos
#      (reescribir rompe todo clon/PR existente).
#   2) Backups espejo:
#        mkdir -p backups
#        for r in f5sign-backend f5sign-dashboard f5sign-docs f5sign-infra f5sign-signer; do
#          git clone --mirror "$(git -C "$r" remote get-url origin)" "backups/$r.git"
#        done
#   3) git-filter-repo instalado:   pip install git-filter-repo
#
# Recordatorio: tras esto, pon includeCoAuthoredBy:false (fase 2) para no
# reintroducir el rastro en commits futuros.
# =============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS=(f5sign-backend f5sign-dashboard f5sign-docs f5sign-infra f5sign-signer)

if [ "${1:-}" != "--yes-rewrite-history" ]; then
  sed -n '2,30p' "${BASH_SOURCE[0]}"
  echo
  echo ">>> NO ejecutado. Lanza con:  bin/purge-ai-history.sh --yes-rewrite-history"
  exit 1
fi

command -v git-filter-repo >/dev/null 2>&1 || { echo "ERROR: falta git-filter-repo (pip install git-filter-repo)"; exit 1; }

MSG_CB='
lines = message.decode("utf-8", "replace").splitlines()
drop = ("Co-Authored-By: Claude", "Co-authored-by: Claude", "Generated with Claude", "Generated with [Claude", "\U0001F916")
lines = [l for l in lines if not any(d in l for d in drop)]
return ("\n".join(lines).rstrip() + "\n").encode()
'

for repo in "${REPOS[@]}"; do
  dst="$ROOT/$repo"
  [ -d "$dst/.git" ] || { echo "· $repo: no clonado, salto"; continue; }
  echo "== purgando $repo =="
  # Reactivar seguimiento por si quedó skip-worktree de la fase 3
  mapfile -t tracked < <(git -C "$dst" ls-files .claude CLAUDE.md 2>/dev/null || true)
  [ "${#tracked[@]}" -gt 0 ] && printf '%s\0' "${tracked[@]}" | xargs -0 -r git -C "$dst" update-index --no-skip-worktree || true
  origin="$(git -C "$dst" remote get-url origin)"
  ( cd "$dst" && git filter-repo --force \
      --path CLAUDE.md --path .claude --invert-paths \
      --message-callback "$MSG_CB" )
  git -C "$dst" remote add origin "$origin" 2>/dev/null || git -C "$dst" remote set-url origin "$origin"
  echo "   ✓ historial reescrito. Push MANUAL tras revisar:"
  echo "       git -C $dst push --force --all && git -C $dst push --force --tags"
done
echo
echo "Rewrite local completado. Re-sincroniza la IA después:  bin/sync-ai.sh"
