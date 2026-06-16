#!/usr/bin/env bash
# Monta el workspace de cero: clona los subrepos ausentes (según repos.manifest)
# y luego distribuye la config IA con sync-ai.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="$ROOT/repos.manifest"

while IFS=$'\t' read -r name url branch; do
  [[ -z "${name:-}" || "$name" == \#* ]] && continue
  if [ -d "$ROOT/$name/.git" ]; then
    echo "· $name ya presente"
  else
    echo "↓ clonando $name ($branch)…"
    git clone --branch "$branch" "$url" "$ROOT/$name"
  fi
done < "$MANIFEST"

echo "→ sincronizando IA…"
"$ROOT/bin/sync-ai.sh"
echo "Workspace listo."
