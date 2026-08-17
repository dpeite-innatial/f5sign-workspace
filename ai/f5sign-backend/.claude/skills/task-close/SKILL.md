---
name: task-close
description: 'Cierra documentalmente una task tras la implementación y las validaciones, y es la dueña del paso que nadie tenía: proponer el salto de un ADR de Proposed a Accepted cuando la task lo ejercita, nombrando el artefacto y esperando tu OK. También actualiza su Status en la tabla de cabecera nombrando rama y commit, añade la sección de desviaciones al final (sin renumerar), y —lo que más importa— lleva cada deferral y cada aprendizaje a un home durable en el repo (§Open follow-ups + fila de docs/BACKLOG.md), nunca a un memo suelto. Úsalo con /task-close TASK-NNN. Activar con "cerrar task", "actualizar el .md", "consolidar aprendizajes", "marcar task como review".'
---

# Task Close

Cierre documental de la task. No es gate duro, pero **es el único paso que impide que lo aprendido se
pierda**.

> Convención del formato: [`docs/tasks/README.md`](../../../docs/tasks/README.md). Si discrepa de esta
> skill, gana el README.

## Invocación

```
/task-close TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/` — todos los `*.report.md`, `context-digest.md`, `plan.md`
  (⚠ si `var/` es de root y los reports acabaron en el scratchpad, léelos de allí; `task-runner` Fase 0
  dice dónde quedaron)
- El `.md` de la task, para editarlo

## Outputs

- El `.md` editado: `Status` + sección de desviaciones + `Open follow-ups` completados
- Fila(s) nuevas en [`docs/BACKLOG.md`](../../../docs/BACKLOG.md) si aparecieron deferrals
- `var/task-runner/TASK-NNN/task-close.report.md`
- JSON: `{"status":"pass|warn","summary":"...","mdSectionsUpdated":[...],"deferralsHomed":N}`

## Ejecución

### Paso 1 — Leer los reports

De cada `*.report.md`: status, WARNs no resueltos, issues abiertos, y **el `harness` que declaró
`task-validate-backend`** (hace falta para el Status; un verde sin harness no es un verde).

### Paso 2 — `Status`, falsificable y nombrando el código

**No hay tabla *Seguimiento*, ni campos `Estado` / `Fin` / `Commit SHA`** — eso era el formato `Planning/`.
Lo que hay es el campo **`Status`** de la tabla de cabecera, y la regla del README §3: **si afirma que
existe código, nombra rama o commit.**

Forma a escribir:

```
| **Status** | **Implemented on `feat/<slug>`** (<sha corto>), 2026-08-17 — suite verde bajo
{harness}. Pendiente de review. {qué quedó fuera, si algo}. |
```

- Fecha **absoluta** siempre.
- ⛔ **Nunca escribir `merged` / `✅` desde aquí.** Esta skill corre antes del PR: afirmar integración es
  falsificar el estado, que es el error que el README §3 previene.
- Si el trabajo quedó a medias, decirlo en el `Status` en vez de dejarlo optimista: el campo se lee dentro
  de seis semanas, que es exactamente cuando el optimismo cuesta.

### Paso 3 — La sección de desviaciones va **al final**, y no se renumera nada

Las secciones se citan como `§N` desde ADRs, desde otras tasks y desde `CLAUDE.md`, así que **añadir en
medio rompe anclas**. Añadir `## N. Deviations & honest notes` como **última** sección (el número que
toque), nunca insertarla tras otra ni recolocar las existentes.

Contenido, y las subsecciones vacías se escriben como "Ninguna" en vez de omitirse:

```markdown
### Scope
- {ficheros del diff que el alcance no anticipaba, o "Ninguna"}

### Decisiones tomadas durante la implementación
- {de context-digest.md; cada una con su por qué}

### Decisiones que necesitaron ADR
- {ADR-NNNN, propuesto y aceptado por el usuario el YYYY-MM-DD — o "Ninguna"}

### Propiedades declaradas y no probadas
- {de validate.report.md: la afirmación + por qué el harness no la alcanza}

### Deuda dejada, y dónde vive ahora
- {cada una con su home: §Open follow-ups de esta task, fila BL-NNN, o el ADR que la registra}
```

### Paso 4 — Cada deferral y cada aprendizaje, a un home durable

⚑ **Este es el paso que justifica la skill, y el que la versión anterior hacía mal.** Escribía los
aprendizajes en un `notes.md` bajo `var/`, que está gitignorado: un memo que nadie volverá a leer. Este
repo ya pagó ese error dos veces — hubo que reconstruir a mano *"eight deferrals that lived only in an
untracked memo"*. **Un aprendizaje que solo existe en `var/` es un aprendizaje perdido.**

Los homes reales, por tipo:

| Lo que apareció | Dónde vive |
|---|---|
| Algo decidido y **no hecho** | `§Open follow-ups` de esta task (el home de verdad) **+ una fila en `docs/BACKLOG.md`** que lo indexa apuntando aquí |
| Una decisión transversal tomada | Su ADR. Si aún no existe → es `implement-backend` Paso 2b, no una nota |
| Un ADR que esta task hizo cierto | El `Status` / `Enforced by` / `Realized in` **de ese ADR**, en este changeset (regla de autoría 7) — ver Paso 4b, que es quien lo ejecuta |
| Una guarda que ningún harness alcanza | Fila de BACKLOG, citando qué harness haría falta |
| Prosa que quedó obsoleta en otro fichero | Se corrige ahora, no se apunta: es el barrido de la regla 1 |
| Fricción del proceso (entorno, tooling) | `var/…/task-close.report.md` está bien **solo** si es efímero de esta corrida; si se va a repetir, va al BACKLOG |

Para la fila de BACKLOG: **re-derivar el id por grep en el momento**, sobre todas las ramas, con el
pathspec absoluto (`':(top)docs/BACKLOG.md'`) — el mismo fallo en abierto que tenían los sweeps de ids.

### Paso 4b — Mover un ADR de `Proposed` a `Accepted` (esta skill es la dueña, con tu OK)

⚑ **Nadie era dueño de esta transición y por eso ADR-0018 y ADR-0035 se quedaron diciendo *not yet* mientras
su trabajo ya estaba en `master`.** `implement-backend` redacta el ADR como `Proposed` y para; `docs-sync` no
puede marcarlo `Accepted`; y aquí es donde por fin se sabe qué quedó verde. Así que el cambio de estado se
propone **aquí**, y solo aquí.

En este set **`Accepted` significa ejercitado**, no acordado. Por tanto:

- [ ] ¿La decisión del ADR está **ejercitada por algo que se puede señalar** — un test que la prueba, un
      camino de código que la aplica, una regla que la enforza? Si no, se queda `Proposed`. *"Ya está
      implementado"* no basta: hay que nombrar el artefacto.
- [ ] Rellenar **`Enforced by (in-repo)`** y **`Realized in (in-repo)`** con esos artefactos, por símbolo o
      patrón de grep, **nunca por número de línea**.
- [ ] **Proponerlo al usuario y esperar su OK**, igual que `implement-backend` hace al acuñarlo: *"ADR-NNNN
      pasa de Proposed a Accepted porque {artefacto} lo ejercita"*. ⛔ Sin respuesta no se toca el campo.
- [ ] Si la task ejercita **parte** de la decisión, existe el matiz: `Accepted (enforcement partial)` es una
      forma en uso en este repo (ADR-0045). Mejor eso que un `Accepted` que promete más de lo que hay.

### Paso 5 — Los `Open follow-ups` que la task ya resolvió

Si la implementación cerró alguno de los puntos de `§Open follow-ups`, **marcarlo cerrado ahí y en su fila
de BACKLOG**, con fecha. Un follow-up que sigue abierto en el papel y cerrado en el código es la misma
clase de mentira que un `Status` obsoleto, en la dirección contraria.

### Paso 6 — Commit

Esta skill **sí commitea sus propias ediciones** (`docs/` y el `.md`), como un commit de documentación
normal. No hay `--amend` que esperar: `pr-ready` ya no reescribe historia.

## Report

```markdown
# task-close — TASK-NNN

**Status:** {PASS|WARN} · **Secciones editadas:** {N} · **Deferrals con home:** {N}

## Cambios en el .md
- Status → {texto literal escrito}
- Sección {N} "Deviations & honest notes" añadida al final

## Deferrals y aprendizajes, con su home
- {qué} → {§Open follow-ups | BL-NNN | ADR-NNNN}

## Fricción del proceso en esta corrida
- {entorno, tooling; y si se repetirá, la fila de BACKLOG que lo recoge}
```

## Manejo de fallos

- Un report ilegible → WARN, no FAIL.
- Sin commit en la rama → FAIL: `implement-backend` no llegó a correr.
- `.md` no parseable → FAIL.

## Qué NO hace

- No abre PR (`pr-ready`).
- No **redacta** ADRs (los propone `implement-backend`, los escribe `docs-sync`) — pero **sí es quien mueve
  su estado** cuando la task los ejercita, con tu confirmación (Paso 4b).
- No decide si se publica.
- No corrige código ni tests.
