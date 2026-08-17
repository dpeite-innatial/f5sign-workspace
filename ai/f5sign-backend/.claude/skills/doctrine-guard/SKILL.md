---
name: doctrine-guard
description: 'Validación mecánica de la capa de persistencia tras una task: migraciones (reversibilidad, índices, SQL publicado que no se edita), RLS (ENABLE + FORCE + policy sobre current_tenant_id(), con la excepción documentada del event log), coherencia entre enums PHP y lo que la columna acepta, y —lo más caro de equivocarse— las filas que una migración escribe y el dominio luego lee. Sin ORM: doctrine/orm se retiró (ADR-0018) y no hay ningún *.orm.xml. Úsalo con /doctrine-guard TASK-NNN. Activar con "validar migration", "revisar persistencia de task", "auditar RLS".'
---

# Doctrine Guard

Validación mecánica de persistencia. Se invoca si el diff toca `migrations/`,
`src/**/Infrastructure/Persistence/`, o SQL/RLS en cualquier fichero.

⛔ **Este repo no tiene ORM.** `doctrine/orm` no es dependencia y **no existe ni un `*.orm.xml`**
(ADR-0018, DBAL puro). Todo lo que esta skill comprobaba sobre mapeos y triangulación entidad↔XML↔tabla no
tiene diana. Si el diff **añade** `doctrine/orm` o un `.orm.xml`, eso revierte un ADR aceptado → `fail`,
categoría `retired-mechanism`, y es el gate de decisión de `implement-backend` Paso 2b.

## Invocación

```
/doctrine-guard TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` (sin él: `fail`, `missing changes.diff`)
- `migrations/Version*.php` y `src/**/Infrastructure/Persistence/*` del diff
- [`docs/LOAD-BEARING.md`](../../../docs/LOAD-BEARING.md) §1.7 y su lista **Never**

## Outputs

- `var/task-runner/TASK-NNN/doctrine-guard.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...]}`

## Ejecución

### Paso 1 — Qué se puede editar de una migración

- [ ] **SQL de una migración ya publicada (pusheada): no se toca.** Se supersede con otra. Editarla es
      `fail`, categoría `published-migration`.
- [ ] **Comentarios y docblocks: siempre en alcance**, publicada o no. La regla de autoría 1 los llama la
      superficie que más daño hace al podrirse, porque nadie re-lee una migración aplicada salvo para
      reconstruir *por qué* el esquema es así — y ahí una razón falsa cuesta lo máximo. Corregirlos no
      re-ejecuta nada.
- [ ] **En una rama local sin pushear el set es tuyo:** se puede reordenar o condensar. "Aplicada en tu
      volumen de dev" no es "publicada".

### Paso 2 — Reversibilidad e índices

- [ ] `up()` y `down()` presentes; `down()` con operaciones reales, no vacío ni un throw genérico.
- [ ] Toda FK con su índice (en la definición o un `CREATE INDEX`).
- [ ] Tabla con datos de cliente → columna **`tenant_id`**. ⚠ **No exigir `workspace_id`: no existe.**
      Aparece una sola vez en todo el repo, en un docblock que describe un modelo futuro de claves
      dual-scoped. Pedirlo sería inventar el esquema.
- [ ] Índice compuesto que empiece por `tenant_id` para las consultas filtradas por tenant → si falta:
      `warn`.

### Paso 3 — RLS

Grep de `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, `CREATE POLICY`:

- [ ] `ENABLE` **y** `FORCE` presentes. `FORCE` es lo que hace que el dueño de la tabla también obedezca.
- [ ] La policy se apoya en **`current_tenant_id()`** (la función fail-closed que envuelve
      `current_setting('app.current_tenant_id')`), no en el setting a pelo.
- [ ] Cubre lectura y escritura, **o dice explícitamente por qué no**. ⚑ Hay una excepción documentada y
      legítima: `platform.event_log` es **write-check-only** (`WITH CHECK`, sin `USING`) porque sus
      lectores son proyectores cross-tenant de confianza (ADR-0031, con el carve-out recíproco en
      ADR-0017 §7). Antes de marcar `fail` por falta de `USING`, comprobar si la tabla es de ese caso.

### Paso 4 — ⚠ Una migración corre como superusuario, así que la RLS no la protege

Las migraciones conectan como el **superusuario de bootstrap** (`POSTGRES_USER`), nunca como el rol de la
app — **en todos los entornos, producción incluida** (`docs/LOAD-BEARING.md` §1.7). Un superusuario
**bypassea RLS por completo**, con `FORCE` o sin él. Dos consecuencias que hay que comprobar:

- [ ] ⛔ **Ningún `NO FORCE ROW LEVEL SECURITY` alrededor de una escritura de datos.** Es un **no-op que se
      lee como una guarda**: la RLS ya no aplicaba. Está en la lista **Never** de `LOAD-BEARING.md` §2,
      junto con por qué la reparación obvia también es incorrecta si algún día se estrecha ese rol.
      Presencia → `fail`, categoría `false-guard`.
- [ ] La corrección de una escritura de datos tiene que venir del **SQL mismo** (su `WHERE`), no de la RLS.

### Paso 5 — Filas que el dominio luego lee (regla de autoría 6)

El check más caro de saltarse: en la última revisión, el único hallazgo bloqueante salió de aquí.

- [ ] **Enumerar los estados del agregado sobre los que cae la fila** — draft, en vuelo, terminal,
      superseded — y decir qué significa la fila **en cada uno**, en el lado de **escritura** además del de
      lectura. Razonar solo sobre "qué puede ver ahora un destinatario" es exactamente cómo se colló ese
      bloqueante.
- [ ] **Predicado que enuncie la propiedad, no enumeración de los estados de hoy.** `sent_at IS NOT NULL`
      pregunta lo real (*"¿pudo alguien leer esto ya?"*); `status <> 'DRAFT'` reabre el agujero el día que
      se añada un estado pre-envío. Enumeración → `warn` con el predicado propuesto.
- [ ] **Modelo append-only sin vía de revocación ⇒ una fila mal escrita es permanente e irreparable por
      API.** Si el backfill no lleva predicado de estado, `fail`: el precedente es un backfill que convirtió
      cada par no declarado de un borrador preexistente en un 409 permanente, dejando esos envelopes ni
      enviables ni reparables.

### Paso 6 — Enums PHP ↔ lo que la columna acepta

**No hay ENUMs SQL en este repo** (`CREATE TYPE ... AS ENUM`: cero). Los estados viajan como `TEXT` y el
tipo vive en un backed enum de PHP. Así que la comprobación no es "¿coinciden los dos enums?" sino:

- [ ] Si la columna lleva `CHECK (... IN (...))`, sus valores coinciden con los `case` del enum PHP.
- [ ] **Un `case` nuevo en PHP no rompe la columna** (es `TEXT`), y eso es precisamente el riesgo: lo que se
      comprueba es que **el lado de lectura sabe parsearlo** — el mapeo del repositorio, la proyección y
      cualquier `match` exhaustivo. Un valor escribible que el read-side no reconoce es `fail`, categoría
      `unparseable-value`.
- [ ] Si el enum es parte de un contrato publicado (sale por la API), el `#[OA\*]` correspondiente lo lista
      → si no: es cosa de `contract-check-backend`, se reporta y se pasa el dato.

### Paso 7 — Entidades y repositorios

Sin re-hacer lo que ya vigilan Deptrac y las reglas PHPStan propias (pureza de capa, colocación en kernel):

- [ ] Aggregate root ⇒ tiene repositorio; entidad subordinada ⇒ **no** tiene el suyo, se modifica por su
      root.
- [ ] ⚑ **`EntityReference` no extiende `EntityId`, y eso no es duplicación que limpiar** — está en
      `LOAD-BEARING.md`. Igual que el row lock que no se estrecha por debajo del write-set de `save()`.
      Antes de "simplificar" cualquier cosa de persistencia, ese documento primero.

## Report

```markdown
# doctrine-guard — TASK-NNN

**Status:** {PASS|FAIL|WARN} · **Issues:** {B} bloqueantes, {W} warnings

## Bloqueantes
- [{categoría}] {fichero} {mensaje}

## Filas escritas y su lectura futura
- {tabla}: estados del agregado enumerados {sí/no} · predicado {el usado} · reparable por API {sí/no}

## Warnings
## Checks superados
```

## Qué NO hace

- No ejecuta migraciones contra la DB (eso es `task-validate-backend`, con `--dry-run`).
- No valida lógica de negocio (tests unitarios).
- No audita inyección SQL ni authz (`security-audit-*`).
- No mide performance (`perf-smoke-backend`).
