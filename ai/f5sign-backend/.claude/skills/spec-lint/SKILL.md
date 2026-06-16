---
name: spec-lint
description: Validación mecánica de completitud del .md de una tarea del Planning/ antes de implementarla. Comprueba frontmatter (Complejidad, Tags, Depende de), secciones obligatorias, formato de Contexto requerido, existencia de rutas citadas, estado de dependencias y ausencia de PENDIENTE/NEEDS CLARIFICATION. Úsalo con /spec-lint T{id} o /spec-lint {ruta-al-.md}. Activar con "lint de tarea", "validar definición", "verificar tarea X", "revisar .md de tarea".
---

# Spec Lint

Gate de entrada. Ejecuta checklist determinista sobre el `.md` de la tarea.

## Invocación

```
/spec-lint T{id}                    # resuelve por Glob
/spec-lint {ruta al .md}
```

## Inputs

- Ruta al `.md` de la tarea (resuelta del argumento)
- Planning root: `Planning/`

## Outputs

- `var/task-runner/T{id}/spec-lint.report.md` (crear el directorio si no existe)
- Como último mensaje: JSON de una línea
  ```json
  {"status": "pass|fail", "summary": "...", "issues": [{"severity": "fail|warn", "category": "...", "message": "..."}]}
  ```

## Ejecución

### Paso 1 — Leer el .md

Si no existe o no es parseable → devolver `status: fail` con issue `{"category": "file", "message": "ruta no encontrada"}`.

### Paso 2 — Frontmatter

Extraer campos entre el título y la primera sección `##`. Verificar:

- [ ] `Story Points`: presente, entero > 0
- [ ] `Tipo`: ∈ {Backend, Frontend, Integracion, Infraestructura, Diseno}
- [ ] `Complejidad`: ∈ {baja, media, alta}
- [ ] `Tags`: presente, no vacío (parsear CSV)
- [ ] `Depende de`: presente (valor literal "ninguna" es válido)

Cada ausencia/invalidación → issue `fail` categoría `frontmatter`.

### Paso 3 — Dependencias

Si `Depende de` ≠ "ninguna":
- Parsear lista de IDs (formato `T{xx}.{y}.{z}`)
- Para cada ID: buscar `.md` con Glob `Planning/F*-*/EP*-*/S*-*/T{id}-*.md`
- Si no existe → issue `fail` categoría `dependency`: "T{id} referenciada no existe"
- Si existe → leer su tabla "Seguimiento", comprobar `Estado = completed`
  - Si no está completed → issue `fail` categoría `dependency`: "T{id} está en estado {X}, debe ser completed"

### Paso 4 — Secciones obligatorias

Verificar que estas secciones existen y ninguna contiene literalmente `PENDIENTE`:
- `## Descripcion`
- `## Contexto requerido`
- `## Archivos a crear/modificar`
- `## Detalle tecnico`
- `## Tests`

Cada fallo → issue `fail` categoría `section`.

### Paso 5 — Contexto requerido

Parsear subsecciones (`### Specs del proyecto`, `### ADRs y decisiones`, etc.). Verificar:

- [ ] Al menos una subsección con contenido no vacío
- [ ] Cada bullet tiene formato `- <ruta> — <razón>` (dash seguido de razón no vacía)
- [ ] Cada ruta citada existe en disco (resolver relativo a raíz del proyecto)
- [ ] Ningún bullet > 200 chars
- [ ] Total de bullets ≤ 15

Rutas que NO hay que validar en disco (son conceptuales): paths con wildcards `*`, o paths bajo `Planning/` con wildcards.

Issues: `fail` para rutas inexistentes y formato; `warn` para >15 bullets y bullets >200 chars.

### Paso 6 — Archivos a crear/modificar

- [ ] Tabla presente con cabecera `| Archivo | Accion |` o similar
- [ ] Al menos una fila
- [ ] Al menos una ruta bajo `tests/` (excepción: si `Tipo: Diseno` o `Tipo: Infraestructura`)

### Paso 7 — Tests

- [ ] Tabla presente
- [ ] Al menos una fila (excepción: `Tipo: Diseno`)

### Paso 8 — Referencias cruzadas AC

Buscar menciones de `AC-\d+` en el `.md`. Para cada una:
- Buscar `README.md` de la story padre (directorio inmediato superior)
- Verificar que el AC mencionado existe con ese número en la story
- Si no existe → issue `fail` categoría `ac-reference`

### Paso 9 — Marcadores de incertidumbre

Grep del texto `[NEEDS CLARIFICATION` en todo el `.md`. Cualquier ocurrencia → issue `fail` categoría `clarification`.

## Generación del report

`var/task-runner/T{id}/spec-lint.report.md`:

```markdown
# spec-lint — T{id}

**Status:** {PASS|FAIL}
**Issues:** {N} ({B} bloqueantes, {W} warnings)

## Bloqueantes
- [{categoría}] {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Chequeos superados
- Frontmatter completo
- {otros que pasaron}
```

## JSON de retorno

Última línea de tu respuesta debe ser un JSON válido de una sola línea:

```json
{"status":"fail","summary":"3 issues (2 fail, 1 warn)","issues":[{"severity":"fail","category":"dependency","message":"T02.1.0 en estado pendiente"},{"severity":"fail","category":"section","message":"Contexto requerido contiene PENDIENTE"},{"severity":"warn","category":"contexto-size","message":"17 bullets (>15)"}]}
```

## Qué NO hace

- No valida calidad semántica del contenido (solo formato y existencia)
- No modifica el `.md`
- No ejecuta tests ni código
- No resuelve las issues — solo las reporta

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/common/02 - Spec Lint.md`
