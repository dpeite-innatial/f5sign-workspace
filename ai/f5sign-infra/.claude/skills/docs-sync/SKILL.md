---
name: docs-sync
description: 'Actualiza documentación que vive fuera del código tras una tarea: AsyncAPI, ADRs (como borrador), CHANGELOG, .env.example, runbooks de workers, READMEs de módulo. NO toca OpenAPI (Nelmio lo cubre inline). Condicional por tags adr/config/breaking/event/worker/new-module. Úsalo con /docs-sync T{id}. Activar con "sincronizar docs", "actualizar changelog", "crear ADR", "actualizar AsyncAPI", "docs externas de tarea".'
---

# Docs Sync

Actualización de documentación externa. No es gate duro; fallos emiten warnings.

## Invocación

```
/docs-sync T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/contract-check.report.md` (si tag `event`, para saber qué eventos sincronizar en AsyncAPI)
- `.md` de la tarea

Del repo (leer si existen):
- `docs/asyncapi/*.yaml`
- `docs/adr/*.md`
- `CHANGELOG.md`
- `.env.example`
- `docs/runbooks/*.md`
- `src/*/README.md`

## Outputs

- Ficheros modificados en el repo (amend al commit existente)
- `var/task-runner/T{id}/docs-sync.report.md`
- JSON:
  ```json
  {"status":"pass|warn","summary":"...","filesUpdated":[...],"tagMismatches":[...]}
  ```

## Selección de modelo

Esta skill puede ejecutarse con **Haiku** (default, para trabajo mecánico) o **Sonnet** (cuando redacta ADR).

Si la tarea tiene tag `adr`: task-runner debe invocar con model=sonnet. Para otros tags: Haiku es suficiente.

## Ejecución

Según tags del `.md`, ejecutar las subsecciones correspondientes. Al final, detectar tag mismatches.

### Tag `adr` (requiere Sonnet)

- Localizar `docs/adr/` (crearlo si no existe)
- Determinar próximo número: mayor NNNN existente + 1
- Título kebab-case derivado del título de la tarea o de la decisión principal en `context-digest.md § Decisiones tomadas`
- Crear `docs/adr/NNNN-titulo-kebab-case.md`:

```markdown
# ADR NNNN — {Título}

Status: draft
Date: {fecha actual}
Origin: T{id}

## Context
{extraído de context-digest.md § Reglas de negocio y §/Decisiones}

## Decision
{extraído literalmente o parafraseado con precisión}

## Consequences
{positivas y negativas, inferidas del contexto}

## Alternatives considered
{si se mencionan; si no, sección vacía o "No documentadas"}
```

**Status inicial `draft`.** El humano lo promueve a `accepted` en un commit manual posterior.

- Añadir entrada al índice `docs/adr/README.md` si existe.

### Tag `config`

- Detectar env vars nuevas/modificadas en el diff:
  - Grep en ficheros PHP por `$_ENV`, `$_SERVER`, `getenv(`, `env(`
  - Grep en `config/packages/*.yaml` y `config/services.yaml` por `%env(...)%`
- Para cada var nueva no presente en `.env.example`:
  - Añadir: `VAR_NAME=placeholder-or-default`
  - Añadir comentario encima explicando qué es (de una línea)
  - Si es secreta: placeholder tipo `CHANGE_ME` o `your-secret-here`
- Si existe `docs/configuracion.md` o equivalente: actualizar si hay sección correspondiente

### Tag `breaking`

- Añadir entrada en `CHANGELOG.md` bajo `## [Unreleased]` → `### Breaking`:
  - Formato: `- **{área}**: {qué cambia} ({cómo migrar})`
  - Si afecta API pública: incluir ejemplo antes/después en bloque de código

Si `CHANGELOG.md` no existe: crear con estructura keepachangelog.com y añadir la entrada.

### Tag `event`

- Revisar `docs/asyncapi/*.yaml` (puede haber varios ficheros por bounded context)
- Para cada evento nuevo/modificado (extraído de `context-digest.md § Eventos de dominio / Emite`):
  - Añadir/actualizar `components.schemas.{EventName}` con payload schema 1:1 con propiedades del evento PHP (tipos Jakarta-style: `type: string, format: uuid`, etc.)
  - Añadir/actualizar `channels.{module}.{event-slug}` con `subscribe` u `operation`
  - Si el evento hace referencia a queue/topic específico (Messenger config), reflejarlo en el channel binding

Si `docs/asyncapi/` no existe: emitir `warn` "AsyncAPI no presente en el proyecto, evento {X} sin documentar" y seguir. No crear AsyncAPI fantasma.

- Si hay catálogo (`docs/events-catalog.md`), añadir entrada.

### Tag `worker`

- Crear/actualizar `docs/runbooks/{worker-name}.md`:
  - Nombre del runbook = nombre del handler en kebab-case
  - Secciones:
    - Qué procesa (qué cola/mensaje)
    - Arranque/parada (comando supervisor/systemd)
    - Métricas a monitorizar (cola length, rate de fallo, p95)
    - Procedimiento ante atasco (DLQ, reproceso)
    - Cómo reprocesar mensajes fallidos

### Tag `new-module`

- Detectar directorio `src/{Module}/` nuevo en el diff
- Si no existe `src/{Module}/README.md`, crearlo:
  ```markdown
  # {Module}
  
  ## Propósito
  {2-3 líneas extraídas de context-digest.md}
  
  ## Aggregate roots
  {listar}
  
  ## Dependencias con otros módulos
  {listar, con referencia al Mapa de Módulos si procede}
  
  ## Eventos de dominio
  - Emite: {lista}
  - Consume: {lista}
  
  ## Entry points
  - Endpoints HTTP: {lista}
  - Handlers async: {lista}
  ```
- Actualizar `Arquitectura/Mapa de Módulos - Bounded Contexts.md` si existe: añadir el nuevo módulo a la lista/diagrama si procede.

## Paso final — Tag mismatches

Para cada tag procesado: si no se pudo generar cambios relevantes porque el diff no contiene evidencia del cambio declarado por el tag, añadir a `tagMismatches`.

Ejemplos:
- Tag `adr` pero no se puede extraer una decisión arquitectónica discernible del context-digest → `adr`
- Tag `config` pero no se detectaron env vars nuevas → `config`
- Tag `new-module` pero no hay directorio nuevo en `src/` → `new-module`

## Paso final — Amend al commit

Hacer `git add` de los ficheros tocados por docs-sync (solo los modificados en este paso) y `git commit --amend --no-edit`. Preserva la regla "1 commit por tarea".

## Report

```markdown
# docs-sync — T{id}

**Status:** {PASS|WARN}
**Ficheros actualizados:** {N}
**Tags procesados:** {lista}

## Cambios aplicados
- docs/asyncapi/envelope.yaml: añadido channel `envelope.closed` + schema
- .env.example: añadida DSS_TIMESTAMP_AUTHORITY_URL
- docs/adr/0012-tsa-fallback-strategy.md: creado (status: draft)

## Omitidos (con razón)
- AsyncAPI: docs/asyncapi/ no presente en el proyecto; evento EnvelopeClosed sin documentar

## Tag mismatches
- {lista o "ninguno"}
```

## JSON de retorno

```json
{"status":"pass","summary":"3 ficheros actualizados, 1 ADR creado como draft","filesUpdated":["docs/asyncapi/envelope.yaml",".env.example","docs/adr/0012-tsa-fallback-strategy.md"],"tagMismatches":[]}
```

## Qué NO hace

- **No toca OpenAPI** (Nelmio lo regenera inline)
- No edita el `.md` de la tarea (eso es task-close)
- No escribe descripción del PR (pr-ready)
- No crea docs no solicitadas por tags
- No "mejora" documentación existente fuera del scope de la tarea

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/common/05 - Docs Sync.md`
- Estrategia API docs: `memory/project_api_docs_strategy.md`
