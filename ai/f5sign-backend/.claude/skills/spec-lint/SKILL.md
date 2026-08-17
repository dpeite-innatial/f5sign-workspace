---
name: spec-lint
description: 'Validación mecánica de completitud del .md de una task de docs/tasks/ antes de implementarla. Comprueba la tabla de cabecera (Status, Type, Why, Decision record), que Status y Decision record sean falsificables, que una task que toca superficies transversales (deptrac, phpstan.dist.neon, el baseline, Kernel/Foundation, dependencias cross-BC) cite un ADR, que Builds on resuelva, secciones numeradas, autocontención (OFFREPO, enlaces relativos, cero citas por número de línea), unicidad del id entre ramas y ausencia de marcadores de incertidumbre. Úsalo con /spec-lint TASK-NNN o /spec-lint {ruta-al-.md}. Activar con "lint de tarea", "validar definición", "verificar task X", "revisar .md de task".'
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

- `var/task-runner/TASK-NNN/spec-lint.report.md`. ⚠ **`var/` puede ser de root y no dejarte crear el
  directorio** (comprobado 2026-08-17: `mkdir` desde el host da *Permission denied*, porque las herramientas
  corren en contenedores como root). Esta skill es la primera del flujo, así que es la que se lo encuentra:
  si pasa, crea el directorio dentro del contenedor o escribe el report en el scratchpad de la sesión, y
  **di en el summary dónde quedó**.
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
- [ ] `Decision record` — presente y **falsificable como `Status`** (Paso 3b), con la misma condición de
      antigüedad que `Why`. Un campo ausente es una task que no ha respondido *"¿qué decisión gobierna
      esto?"*, la pregunta de la que depende la regla 7 del repo.

⚑ **`Why` y `Decision record` solo bloquean en tasks todavía no implementadas.** La condición es una
propiedad, no una lista: si el `Status` **no** afirma código existente, el registro sigue siendo un plan
editable y los dos campos son obligatorios (`fail`). Si ya afirma código, son `warn` — porque rellenar el
*por qué* de un trabajo ya cerrado es inventarlo a posteriori, y un `Why` inventado es peor que ausente.
**Medido 2026-08-17: `Why` está en 6 de 21 registros y `Decision record` en 12**, así que exigirlos en
bloque haría fallar a 15 de 21 y el linter sería más estricto que el corpus del que dice derivarse.

Opcionales, y no se penaliza su ausencia: `Builds on`, `Scope`, `Delivery bar`, `Sibling`.

### Paso 3 — `Status` falsificable

El campo que más se podre, así que se valida por contenido, no por presencia:

- [ ] Si afirma que existe código (`merged`, `landed`, `in progress`, `shipped`, `✅`) → **nombra una rama o
      un commit**. Si no → `fail`, categoría `status-unverifiable`.
- [ ] Si dice `Not started` y el diff de la rama ya toca los ficheros de §Scope → `warn`, categoría
      `status-stale`.
- [ ] Si contiene una fecha, que sea absoluta (`2026-08-17`), nunca relativa (*"la semana pasada"*) →
      `fail`, categoría `date-relative`.

### Paso 3b — `Decision record` falsificable

Dos formas válidas, y ninguna más:

1. **Cita un ADR** (`[ADR-NNNN](../adr/ADR-NNNN-*.md)`) → el enlace debe resolver (Paso 6). Si además dice
   que esta task *contradice* o *revierte* algo de ese ADR, comprobar que declara **dónde aterriza el ADR
   nuevo** (esta task o cuál) → si no lo dice: `fail`, categoría `decision-unlanded`. Un ADR aceptado no
   se contradice en silencio.
2. **`No ADR yet` + qué lo forzaría.** La segunda mitad no es opcional: *"no hay ADR"* sin condición de
   disparo es indistinguible de *"no me lo he preguntado"*. → sin ella: `fail`, categoría
   `decision-record-unfalsifiable`.

⚑ **Y si el alcance de la task toca cualquiera de estas superficies, la forma 2 no vale.** ⚠ *Alcance*
aquí es **la sección**, no el campo `Scope` de la cabecera: ese campo existe en 2 de 21 registros y el Paso 2
lo declara opcional, así que gatear sobre él dejaría el check vacío en casi todos. Si no hay ni campo ni
sección de alcance, dilo como `warn` (`scope-unstated`) en vez de dar por bueno que no toca nada. Superficies: el ruleset o las
capas de [`deptrac.yaml`](../../../deptrac.yaml), `phpstan.dist.neon`, `phpstan-baseline.neon`, un contrato
de `src/F5Sign/Kernel/` o `src/F5Sign/Foundation/`, o una dependencia cross-BC nueva. Todas son decisiones
transversales por definición y piden ADR → `fail`, categoría `decision-required`, nombrando la superficie.

### Paso 4 — `Builds on` y `Sibling`

⚑ **Los dos campos no se validan igual, y confundirlos produce un falso bloqueante.** `Builds on` es una
dependencia real ("reuso su salida sin cambiarla"); `Sibling` es un aviso a un humano ("no planifiques
estas dos por separado"). Una task que declara honestamente que su sibling vive en otra rama está
haciendo justo lo que el formato pide, y penalizarlo castiga la conducta correcta.

**`Builds on` — bloquea:**

- [ ] Cada task citada existe como `docs/tasks/TASK-NNN-*.md` en **esta** rama. Si no existe aquí pero sí
      en otra (`git ls-tree -r --name-only <rama> -- ':(top)docs/tasks/'`) → `fail`, categoría
      `dependency-offbranch`, nombrando la rama: no se puede construir sobre algo que no está en el árbol.
- [ ] Si su `Status` es `Not started` → `fail`, categoría `dependency`.
- [ ] Puede citar ADRs además de tasks; para esos basta que el enlace resuelva (Paso 6).

**`Sibling` — nunca bloquea:**

- [ ] Si está marcado con ⚑ → `warn`, categoría `sibling-flagged`, recordando que no se planifican de
      forma independiente.
- [ ] Si vive en otra rama → **el mismo `warn`, con la rama nombrada**, y decir qué pasa si se ejecuta
      esta task antes de que aquella se integre. Nunca `fail`.

### Paso 5 — Secciones

Las secciones van numeradas (`## 1. …`) y se citan como `§N` desde otros documentos.

- [ ] Al menos una sección cuyo encabezado hable de **scope/alcance** y otra de
      **verification/acceptance/definition of done**. ⚑ Comprobar por *intención*, no contra una lista
      cerrada de encabezados: los 21 registros de esta rama usan variantes legítimas —el alcance aparece en §3, §4 y §6; la verificación en §4, §5, §6 y §9— y una enumeración
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
  git ls-tree -r --name-only "$b" -- ':(top)docs/tasks/' 2>/dev/null | grep -oE 'TASK-[0-9]{3}'
done | sort -u
```

⚠ **`':(top)'` no es decorativo, y sin él este check falla en abierto.** Un pathspec de git es relativo al
**cwd**, así que `-- docs/tasks/` ejecutado desde `docs/tasks/` — el directorio donde estás precisamente
cuando escribes una task — resuelve `docs/tasks/docs/tasks/` y devuelve **cero ids**. Cero ids se lee como
"el id está libre", en el único check cuyo trabajo es impedir una colisión. Medido 2026-08-17: **0 ids** sin
`:(top)` desde `docs/tasks/`, y **24** con él (o desde la raíz). ⚑ Y no copies ese 24 a ninguna parte: es el
recuento de ese día, no una constante. Una versión anterior de esta línea decía 21 —el número de ficheros de
*una* rama— y ese error se propagó a dos documentos antes de que un audit lo cazara.

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
