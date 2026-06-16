---
name: task-close
description: Cierra documentalmente una tarea tras la implementación y validaciones: actualiza el .md (Estado=review, Fin, Commit SHA), consolida tagMismatches de todas las skills previas, añade sección "Desviaciones de lo planificado" al .md, y extrae aprendizajes no obvios a notes.md si los hay. Úsalo con /task-close T{id}. Activar con "cerrar tarea", "actualizar .md", "consolidar aprendizajes", "marcar tarea como review".
---

# Task Close

Cierre documental de la tarea. No es gate duro.

## Invocación

```
/task-close T{id}
```

## Inputs

- `var/task-runner/T{id}/` (todos los reports `*.report.md` generados)
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/plan.md`
- `.md` de la tarea (para editarlo)

## Outputs

- `.md` de la tarea EDITADO:
  - Frontmatter: Estado, Fin, Commit, PR/Branch (rama, no URL aún), Tags (limpios)
  - Nueva sección `## Desviaciones de lo planificado` añadida después de `## Tests`
  - Sección `## Tests` actualizada si `task-validate` ejecutó tests distintos/adicionales a los declarados
- `var/task-runner/T{id}/task-close.report.md`
- `var/task-runner/T{id}/notes.md` (SOLO si hay aprendizajes reales; si está vacío, NO crearlo)
- JSON:
  ```json
  {"status":"pass|warn","summary":"...","mdSectionsUpdated":[...],"lessonsCount":N}
  ```

## Ejecución

### Paso 1 — Leer reports

Parsear todos los `*.report.md` del workspace. Extraer:
- Status de cada skill
- `tagMismatches` de cada una (consolidar en un solo array)
- WARN activos (para deuda técnica)
- Issues relevantes no resueltos

### Paso 2 — Determinar SHA del commit

- `git log -1 --format=%H` (la rama actual debería tener el commit de implement + amends)
- Guardar SHA para actualizar el frontmatter

### Paso 3 — Editar frontmatter del `.md`

Usar Edit tool. Buscar la tabla "Seguimiento" en el `.md`:

- `Estado` → `review`
- `Fin` → fecha actual (formato `YYYY-MM-DD`)
- `Commit` → SHA completo (40 chars)
- `PR/Branch` → nombre de la rama actual (ej. `feat/T02.1.1-slug`); la URL completa la añadirá `pr-ready` más tarde

Además, en el bloque de header (arriba, con `> **Tags:** ...`):
- Quitar tags presentes en `tagMismatches` consolidado. Si quedan solo 1-2 tags, dejarlos (no vaciar).

### Paso 4 — Añadir sección "Desviaciones"

Buscar la sección `## Tests` y después de ella añadir (si no existe ya):

```markdown
## Desviaciones de lo planificado

### Archivos
- {si hay diferencia entre declarados y reales: listar. Si no: "Ninguna"}

### Tags corregidos
- Eliminado `{tag}`: {razón extraída del report que lo detectó}

### Decisiones tomadas en implementación
- {extraídas de context-digest.md § "Decisiones tomadas durante implementación"}

### Escaladas
- {si implement reportó escalada Sonnet→Opus en su JSON, documentar razón. Si no: "Ninguna"}

### Deuda técnica dejada
- {WARNs activos que el usuario decidió no corregir; extraer de perf-smoke, security-audit, etc.}
```

Si alguna subsección no tiene contenido → escribir "Ninguna" (no omitirla).

### Paso 5 — Actualizar tabla "Tests" (si aplica)

Leer `test-results.json` del workspace. Si el número/nombres de tests ejecutados difiere de la tabla `## Tests` del `.md`:
- Actualizar la tabla para reflejar los tests realmente añadidos
- Mantener el formato original (`| Test name | Type | File path | What it verifies |`)

### Paso 6 — Extraer aprendizajes → notes.md

Mirar reports y detectar patrones aplicables a futuras tareas:

- **Contexto insuficiente**: ¿implement escaló a Opus por falta de regla/spec? Documentar qué faltaba en `Contexto requerido`.
- **Tags mal asignados**: tag mismatches ≥ 1 → sugerir revisar criterio de planning-detail.
- **Decisiones implícitas**: decisiones tomadas durante implementación sin ADR → sugerir crear ADR si el patrón se repite.
- **Gates fallados reintentados**: si hubo corrección automática (implement re-invocada con report de validation/security), documentar qué cambió.
- **Deuda técnica no cerrada**: WARNs de perf-smoke/security-audit no resueltos.

Si hay al menos un aprendizaje → crear `var/task-runner/T{id}/notes.md`:

```markdown
# Notes — T{id}

## Aprendizajes potenciales
- [Contexto insuficiente] Escaló a Opus por falta de regla X; futuras tareas similares deberían listar [regla/fichero]
- [Tag mal usado] Tag `db` aplicado pero no tocó persistencia; revisar criterio en planning-detail

## Métricas
- Tiempo total: {min}
- Tokens estimados: {breakdown por skill}
- Escalada a Opus: {sí/no, razón}
- Gates fallados y reintentados: {N}

## Decisiones implícitas (candidatos a ADR si se repiten)
- {lista extraída de context-digest.md}
```

Si no hay aprendizajes (todo fue ideal) → **NO crear** el fichero.

### Paso 7 — NO commitear aún

`task-close` modifica el `.md` pero NO hace commit. `pr-ready` hará el `--amend` final que incluye estas modificaciones + la URL del PR una vez creado.

Dejar los cambios en staging es opcional; si se hace, `git add {rutaMd}` y listo. Si no, `pr-ready` lo añadirá.

## Report

`var/task-runner/T{id}/task-close.report.md`:

```markdown
# task-close — T{id}

**Status:** PASS  |  **Secciones actualizadas:** {N}  |  **Aprendizajes:** {N}

## Cambios aplicados al .md
- Frontmatter: Estado → review, Fin → 2026-04-13, Commit → abc123f
- Tags: eliminado `db` (mismatch detectado por doctrine-guard)
- Sección "Desviaciones" creada con 3 entradas
- Sección "Tests" actualizada (2 tests adicionales añadidos vs. plan original)

## Aprendizajes escritos en notes.md (2)
- Contexto insuficiente sobre regla de estado X
- Decisión implícita sobre estrategia Y (candidato a ADR si se repite)
```

## JSON de retorno

```json
{"status":"pass","summary":".md actualizado, 2 aprendizajes extraídos","mdSectionsUpdated":["frontmatter","tags","desviaciones","tests"],"lessonsCount":2}
```

## Manejo de fallos

- Si no puede parsear un report previo → WARN "skipped section X", no FAIL
- Si el `.md` está corrupto o no parseable → FAIL (caso improbable)
- Si falta el commit SHA (git no devuelve nada) → FAIL "no commit found, implement did not run?"

## Qué NO hace

- No abre PR (pr-ready)
- No commitea (pr-ready hace el amend final)
- No decide si se publica (confirmación del usuario)
- No escribe ADRs (docs-sync, como draft)
- No corrige tests ni código

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/common/03 - Task Close.md`
