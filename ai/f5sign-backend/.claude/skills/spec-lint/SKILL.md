---
name: spec-lint
description: 'Validación mecánica de completitud del .md de una task de docs/tasks/ antes de implementarla. Comprueba la tabla de cabecera (Status, Type, Why), que Status sea falsificable, que Builds on resuelva, secciones numeradas, autocontención (OFFREPO, enlaces relativos, cero citas por número de línea), unicidad del id entre ramas y ausencia de marcadores de incertidumbre. Úsalo con /spec-lint TASK-NNN o /spec-lint {ruta-al-.md}. Activar con "lint de tarea", "validar definición", "verificar task X", "revisar .md de task".'
---

# Spec Lint

Gate de entrada. Checklist determinista sobre el `.md` de una task.

> **La convención que valida es [`docs/tasks/README.md`](../../../docs/tasks/README.md).** Si esta skill y
> ese README discrepan, gana el README y esta skill es el bug.

## Invocación

```
/spec-lint TASK-NNN                 # resuelve por Glob en docs/tasks/
/spec-lint {ruta al .md}
```

## Inputs

- Ruta al `.md` (resuelta del argumento). Raíz de tasks: **`docs/tasks/`** — no `Planning/`, que es
  legado del repo de docs (README §1).

## Outputs

- `var/task-runner/TASK-NNN/spec-lint.report.md` (crear el directorio si no existe)
- Última línea: JSON `{"status":"pass|fail","summary":"...","issues":[{"severity":"fail|warn","category":"...","message":"..."}]}`

## Ejecución

### Paso 1 — Leer el .md

Si no existe o no parsea → `fail`, categoría `file`.

### Paso 2 — Tabla de cabecera

Es una tabla de dos columnas entre el título y el primer `---`/`## `. **No hay frontmatter YAML, ni
`Story Points`, `Tipo`, `Complejidad`, `Tags` o `Depende de`** — esos campos eran del formato `Planning/`.

Obligatorios:

- [ ] `Status` — presente y no vacío
- [ ] `Type` — presente; texto libre, pero debe decir *qué clase de trabajo es* (forward build, corrective,
      enabling, groundwork) y no solo repetir el título
- [ ] `Why` — presente; debe enunciar el fallo o la carencia, de forma que se pueda **discrepar** de ella

Opcionales, y no se penaliza su ausencia: `Builds on`, `Scope`, `Decision record`, `Delivery bar`, `Sibling`.

### Paso 3 — `Status` falsificable

El campo que más se podre, así que se valida por contenido, no por presencia:

- [ ] Si afirma que existe código (`merged`, `landed`, `in progress`, `shipped`, `✅`) → **nombra una rama o
      un commit**. Si no → `fail`, categoría `status-unverifiable`.
- [ ] Si dice `Not started` y el diff de la rama ya toca los ficheros de §Scope → `warn`, categoría
      `status-stale`.
- [ ] Si contiene una fecha, que sea absoluta (`2026-08-17`), nunca relativa (*"la semana pasada"*) →
      `fail`, categoría `date-relative`.

### Paso 4 — `Builds on` y `Sibling`

Para cada task citada:

- [ ] Existe `docs/tasks/TASK-NNN-*.md` en **esta** rama. Si no existe pero sí en otra
      (`git ls-tree -r --name-only <rama> -- docs/tasks/`) → `fail`, categoría `dependency-offbranch`,
      nombrando la rama: una task que vive en otra rama no está disponible para construir sobre ella.
- [ ] Si es `Builds on` y su `Status` es `Not started` → `fail`, categoría `dependency`.
- [ ] Si es `Sibling` marcado con ⚑ → `warn` informativo recordando que **no se planifica de forma
      independiente**; es un aviso al humano, no un bloqueo.

### Paso 5 — Secciones

Las secciones van numeradas (`## 1. …`) y se citan como `§N` desde otros documentos.

- [ ] Al menos una sección cuyo encabezado hable de **scope/alcance** y otra de
      **verification/acceptance/definition of done**. ⚑ Comprobar por *intención*, no contra una lista
      cerrada de encabezados: los 20 registros existentes usan variantes legítimas, y una enumeración
      exime "todo lo que aún no está en la lista" (regla de autoría 5).
- [ ] Numeración sin huecos ni repetidos, y **empezando en 1**.
- [ ] Ninguna sección vacía (encabezado seguido de otro encabezado).

### Paso 6 — Autocontención

- [ ] Todo enlace relativo resuelve en disco → si no: `fail`, categoría `link-broken`.
- [ ] Toda referencia a algo fuera del repo lleva `<!-- OFFREPO: ... -->` cerca, y el hecho que se toma
      de ahí está **restatado** en el `.md` → si falta el tag: `fail`, categoría `offrepo-untagged`.
- [ ] **Cero citas por número de línea**: enlaces con `#L\d+` o rutas con `:\d+` → `fail`, categoría
      `line-number-citation`. Se cita por símbolo o por patrón de grep.
- [ ] Rutas con wildcard (`src/**/UI/`) no se validan en disco; son conceptuales.

### Paso 7 — Unicidad del id

Correr el sweep del README §4 **en el momento**:

```bash
for b in $(git branch -a --format='%(refname:short)' | grep -v HEAD); do
  git ls-tree -r --name-only "$b" -- docs/tasks/ 2>/dev/null | grep -oE 'TASK-[0-9]{3}'
done | sort -u
```

- [ ] El id del `.md` no aparece en ninguna otra rama con **otro** slug → si aparece: `fail`, categoría
      `id-collision`, nombrando la rama. Esto ha pasado de verdad: `TASK-021…023` viven en
      `docs/two-gate-signer-auth` y son invisibles desde cualquier otra rama.

### Paso 8 — Marcadores de incertidumbre

Grep de `PENDIENTE`, `[NEEDS CLARIFICATION`, `TBD`, `???`. Cualquier ocurrencia → `fail`, categoría
`clarification`.

⚠ **Excepción deliberada:** una sección de *Open follow-ups* **debe** contener cosas sin resolver — eso es
su función (README §7). No penalizar ahí; solo exigir que cada punto diga *qué* está sin decidir y *qué*
lo forzaría.

## Report

```markdown
# spec-lint — TASK-NNN

**Status:** {PASS|FAIL}
**Issues:** {N} ({B} bloqueantes, {W} warnings)

## Bloqueantes
- [{categoría}] {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Chequeos superados
- {lista}
```

## Qué NO hace

- No valida calidad semántica (solo formato, resolución y existencia).
- No modifica el `.md`.
- No ejecuta tests ni código.
- No resuelve las issues — solo las reporta.
