---
name: contract-check-frontend
description: Valida contratos API consumidos desde el frontend: los composables y stores que llaman a endpoints usan los tipos TypeScript generados desde OpenAPI (no tipos ad-hoc), manejan los error codes declarados, cancelan requests pendientes. Si la tarea escucha eventos async (websockets/SSE) verifica coherencia con AsyncAPI. Úsalo con /contract-check-frontend T{id}. Activar con "validar contratos frontend", "check tipos API", "revisar composables de fetch".
---

# Contract Check Frontend

Validación de contratos API desde el lado consumidor. Solo si tags incluye `api` o `event`. Gate duro.

## Invocación

```
/contract-check-frontend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `.md` de la tarea
- README de la story padre (para AC con error codes)
- Tipos generados desde OpenAPI (ruta típica: `types/api.ts`, `src/types/openapi.d.ts`, o donde configure el proyecto)
- `docs/asyncapi/*.yaml` (si la tarea consume eventos async)

## Outputs

- `var/task-runner/T{id}/contract-check-frontend.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...],"tagMismatches":[...]}`

## Precondición

Si el proyecto NO tiene tooling OpenAPI→TS configurado (no existe fichero de tipos generados ni script `openapi:generate`): emitir WARN "OpenAPI→TS no configurado, tipos ad-hoc permitidos" y saltar los checks de tipos. Seguir con el resto.

## Ejecución

### Paso 1 — Detectar tag mismatch

- Si tag `api` y el diff no contiene composables con `fetch`/`$fetch`/`useFetch`/`axios` ni stores con llamadas HTTP → `tagMismatches: ["api"]`
- Si tag `event` y el diff no contiene código de websocket/SSE/EventSource → `tagMismatches: ["event"]`

### Paso 2 — Checks tag `api`

#### Tipos generados
Localizar composables/stores del diff que hagan llamadas HTTP. Para cada llamada:

- [ ] El tipo de request (body) viene de los tipos generados (importado de `@/types/api` o equivalente)
  - Grep patterns: `import type { X } from '@/types/api'`, `paths['...']['post']['requestBody']`, etc.
- [ ] El tipo de response idem
- [ ] No hay `any` en request/response
- [ ] No hay interfaces/types ad-hoc duplicando lo que ya está en los tipos generados

#### Error codes
Para cada endpoint consumido, cruzar con AC de la story:

- [ ] Si AC declara error HTTP X con codigo Y (ej. 409 ENVELOPE_ALREADY_CLOSED), el código frontend lo maneja explícitamente:
  - Captura del error (try/catch o `.catch()`)
  - Discriminación por código (switch/if sobre `error.code` o `error.response.status`)
  - Traducción a UX (toast, mensaje en formulario, redirección)
- [ ] Errores no listados en AC tienen un handler genérico (no se silencian)
- [ ] Errores 401 desencadenan logout/refresh según convención del proyecto
- [ ] Errores 5xx muestran mensaje genérico al usuario y loggean al sistema de monitoring (si existe)

#### Cancelación de requests
- [ ] Si el composable ejecuta fetch en un watcher o effect: proporciona un mecanismo de cancelación (AbortController)
- [ ] Al desmontar el componente que usa el composable: pending requests se cancelan
- [ ] `onUnmounted` / `onScopeDispose` con cleanup

#### Actualización de tipos
- [ ] Si el backend cambió su OpenAPI (y los tipos se regeneraron) y esta tarea consume esos cambios: el import está actualizado
- [ ] Si se detecta que el composable usa un shape obsoleto → `warn` "tipos pueden estar desactualizados, verificar versión del OpenAPI"

### Paso 3 — Checks tag `event` (websockets, SSE, realtime)

#### AsyncAPI
Si `docs/asyncapi/` existe:
- [ ] Los eventos escuchados por el frontend están documentados en AsyncAPI
- [ ] El schema del payload coincide con el tipo TS que el código asume
- [ ] El channel/topic usado coincide con la config

Si AsyncAPI no existe: WARN "AsyncAPI no presente, eventos sin contrato formal" (no FAIL, consistente con backend).

#### Typing
- [ ] Los eventos recibidos se tipan; no se accede con `any` a sus propiedades
- [ ] Si el proyecto tiene tipos generados para eventos (ej. desde AsyncAPI), se usan

#### Cleanup
- [ ] Las subscripciones a eventos se limpian al desmontar (`onUnmounted(() => socket.off(...))`)
- [ ] No hay memory leaks de listeners huérfanos

### Paso 4 — Intersección (tags `api` + `event`)

Si la tarea tiene ambos:
- [ ] Si el flujo es "POST al backend → esperar evento de confirmación via websocket": timeout y fallback definidos si el evento no llega

### Paso 5 — Tests

- [ ] Los composables que consumen endpoints tienen test unitario que mockea la API y verifica:
  - Happy path
  - Al menos un error case del AC
  - Cancelación si aplica

## Gravedad

- **FAIL:**
  - Uso de `any` en request/response cuando existen tipos generados
  - Error code de AC no manejado
  - Evento escuchado sin cleanup al desmontar (memory leak potencial)
  - Schema AsyncAPI del evento diverge del tipo asumido en TS
- **WARN:**
  - Tipos ad-hoc duplicando los generados
  - AsyncAPI no presente
  - Tipos potencialmente desactualizados

## Report

```markdown
# contract-check-frontend — T{id}

**Status:** {PASS|FAIL|WARN}
**Tags evaluados:** {api, event}
**Issues:** {B} bloqueantes, {W} warnings

## Bloqueantes
- [{categoría}] {fichero:línea} {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Endpoints consumidos (desde el diff)
- POST /api/v1/envelopes/{id}/close — composables/useEnvelopes.ts:45
  - Tipos: paths['/api/v1/envelopes/{id}/close']['post'] ✓
  - Errores manejados: 409 ENVELOPE_ALREADY_CLOSED ✓, 403 ✓, 5xx ✓

## Eventos escuchados
- (ninguno)

## Tag mismatches
- {lista o "ninguno"}
```

## JSON de retorno

```json
{"status":"fail","summary":"1 error code de AC no manejado","issues":[{"severity":"fail","category":"error-unhandled","file":"composables/useEnvelopes.ts:52","message":"AC-04 exige manejar 409 ENVELOPE_ALREADY_CLOSED, no hay rama de error"}],"tagMismatches":[]}
```

## Qué NO hace

- No valida implementación del endpoint en backend (eso es `contract-check-backend`)
- No genera los tipos desde OpenAPI — asume que el proyecto tiene ese tooling
- No valida UX de manejo de errores (solo que se manejen)
- No audita seguridad del client (`security-audit-frontend`)

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/` (nueva sección)
- Estrategia API docs: `memory/project_api_docs_strategy.md`
