#!/bin/sh
# Usage (inside php-fpm, from /var/www/html): sh var/evidence-design/render.sh <template.typ> <trail|receipt> [json-glob]
set -e
D=var/evidence-design; T=$1; K=$2; G=${3:-}
for j in $D/data/${G:-}*.json; do
  case "$(basename $j)" in trail-*) [ "$K" = trail ] || continue;; justificante-*) [ "$K" = receipt ] || continue;; esac
  n=$(basename $j .json); cp $j $D/input.json
  /usr/local/bin/typst compile --root $D --input trail=/input.json --pdf-standard a-3a --ignore-system-fonts --ignore-embedded-fonts --font-path assets/evidence-audit/fonts --diagnostic-format short $D/$T $D/out/$n.$(basename $T .typ).pdf
  echo "ok $n"
done
chmod -R a+rw $D/out
