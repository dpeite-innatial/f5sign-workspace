#!/usr/bin/env bash
# ==============================================================
# ai-doctor.sh — verifica el INVARIANTE DEL SECRETO. Silencioso si todo esta bien.
# ==============================================================
# La arquitectura de este workspace existe para una sola promesa: que los subrepos
# no lleven rastro de IA. Todo lo demas (el store `ai/`, los symlinks, sync-ai.sh,
# skip-worktree) es maquinaria al servicio de eso. Esto comprueba que la promesa
# sigue en pie, que es lo unico que ningun gate ve y que se rompe en silencio.
#
# Tres formas conocidas de romperla, las tres cubiertas aqui:
#   1. Correr algo que sustituya un symlink por un fichero real (era el caso de
#      f5sign-docs/scripts/sync-skills.sh, bloqueado en 2026-08-25).
#   2. Crear un worktree y olvidar bin/sync-ai.sh: sirve los ficheros de IA
#      TRACKEADOS EN EL HISTORIAL, viejos y commiteables.
#   3. Un merge que deshaga el skip-worktree y devuelva los paths a `git status`.
#
# Uso:
#   bin/ai-doctor.sh            # informe; SIEMPRE exit 0 (pensado para el hook)
#   bin/ai-doctor.sh --strict   # exit 1 si hay problemas (para uso manual/CI)
#
# ⚠ Este script NO arregla nada a proposito. El arreglo casi siempre es
#   bin/sync-ai.sh, y decidirlo es de quien lee.
# ==============================================================
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 0
strict=0; [ "${1:-}" = "--strict" ] && strict=1

fail=0
say() { echo "  ⛔ $*"; fail=$((fail+1)); }

check_checkout() { # <dir> <label>
  local d="$1" label="$2" p tracked unskipped
  for p in "$d/CLAUDE.md" "$d"/.claude/* "$d"/.claude/skills/* "$d"/.claude/agents/*; do
    [ -e "$p" ] || [ -L "$p" ] || continue
    # `skills/` y `agents/` son directorios reales a proposito: sync-ai.sh enlaza
    # a nivel de HOJA para que anadir una skill no exija re-enlazar el arbol.
    case "$p" in */.claude/skills|*/.claude/agents) continue ;; esac
    if [ ! -L "$p" ]; then
      say "$label: FICHERO REAL de IA dentro del subrepo (rompe el secreto): ${p#$ROOT/}"
    elif [ ! -e "$p" ]; then
      say "$label: symlink roto: ${p#$ROOT/} -> $(readlink "$p")"
    fi
  done
  # skip-worktree es POR INDICE y cada worktree tiene el suyo: comprobarlo aqui,
  # no en el clon principal, o los worktrees pasan de largo.
  tracked=$(git -C "$d" ls-files .claude CLAUDE.md 2>/dev/null | wc -l)
  if [ "$tracked" -gt 0 ]; then
    unskipped=$(git -C "$d" ls-files -v .claude CLAUDE.md 2>/dev/null | grep -cv '^S')
    [ "$unskipped" -eq 0 ] || \
      say "$label: $unskipped de $tracked paths de IA trackeados SIN skip-worktree (git status los delata)"
  fi
}

# La lista sale del store, nunca hardcodeada. El primer prototipo de esto llevaba
# los cinco nombres a mano, y sobre un workspace de prueba respondio "ok" habiendo
# mirado CERO checkouts: el modo de fallo que este fichero entero existe para cazar.
checked=0
for storedir in ai/*/; do
  repo="$(basename "$storedir")"
  [ "$repo" = "shared" ] && continue
  [ -e "$repo/.git" ] || { echo "  · $repo: en el store pero sin clonar, salto"; continue; }
  check_checkout "$repo" "$repo"; checked=$((checked+1))
  main="$(realpath "$repo")"
  while IFS= read -r wt; do
    [ -d "$wt" ] || continue
    [ "$(realpath "$wt")" = "$main" ] && continue
    if [ ! -L "$wt/CLAUDE.md" ] && [ -e "ai/$repo/CLAUDE.md" ]; then
      say "$repo → $(basename "$wt"): worktree SIN SINCRONIZAR (sirve la IA del historial) — corre bin/sync-ai.sh"
    else
      check_checkout "$wt" "$repo → $(basename "$wt")"
    fi
    checked=$((checked+1))
  done < <(git -C "$repo" worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p')
done

if [ "$checked" -eq 0 ]; then
  echo "ai-doctor: ⛔ 0 checkouts revisados — esto NO es un ok, es que no habia nada que mirar"
  [ "$strict" = 1 ] && exit 1 || exit 0
fi
if [ "$fail" -eq 0 ]; then
  echo "ai-doctor: ok ($checked checkouts)"
else
  echo "ai-doctor: $fail problema(s) en $checked checkouts — el arreglo suele ser bin/sync-ai.sh"
fi
[ "$strict" = 1 ] && exit $(( fail > 0 ? 1 : 0 )) || exit 0
