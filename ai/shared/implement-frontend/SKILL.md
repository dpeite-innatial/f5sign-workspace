---
name: implement-frontend
description: Implementa una tarea frontend (Nuxt 3 + Vue 3 + TypeScript + Tailwind + Pinia) del Planning/ siguiendo TDD (Vitest para unit/component, Playwright para E2E), respetando la separación páginas/composables/componentes y las convenciones de i18n y design system. Lee el .md de la tarea y su Contexto requerido, escribe código + tests, y produce artefactos context-digest.md, plan.md y un único commit final. Solo para repositorios frontend. Úsalo con /implement-frontend T{id}. Activar con "implementa frontend T{id}", "codifica tarea Vue...", "implementa componente...".
---

# Implement Frontend

Implementación TDD de una tarea frontend. El modelo se elige según `Complejidad` (Sonnet para baja/media, Opus para alta).

## Invocación

```
/implement-frontend T{id}
/implement-frontend T{id} --model=opus
/implement-frontend T{id} --amplified-context
```

## Inputs

- `.md` de la tarea
- Ficheros listados en `## Contexto requerido`
- ⚑ **Los traspasos pendientes del backend: `../f5sign-backend/docs/frontend-handoff/*.md`.** Un cambio de
  contrato en el backend y su adopción aquí son **dos PRs** (regla 4 del workspace: dos proyectos, dos PRs
  coordinados), así que ese directorio es el único sitio donde está escrito *qué cambió y qué hay que hacer
  en este repo*. Cada fichero nombra su commit de origen — compáralo con lo que ya está aplicado para saber
  si vas por detrás — y lee su sección *"Lo que NO está listo todavía"* **antes** de construir contra un
  endpoint: media utilidad de ese documento es frenar trabajo contra un seam incompleto.
  Si el directorio no es alcanzable (acceso solo a este repo), **pide al usuario el fichero de traspaso** en
  vez de inferir el contrato; y los tipos se regeneran del OpenAPI, que es la verdad legible por máquina,
  nunca a mano desde la prosa del traspaso.
- Si `--amplified-context`: README de story padre + README de epic padre + `.md` de dependencias + catálogo de eventos si aplica
- Referencias fijas: `Arquitectura/Arquitectura Frontend.md`, `.claude/skills/planning-detail/references/wireframe-conventions.md`
- `tailwind.config.ts` (tokens canónicos)

## Outputs

- Código + tests commiteados (1 único commit) en la rama `feat/T{id}-*`
- `var/task-runner/T{id}/plan.md`
- `var/task-runner/T{id}/context-digest.md`
- JSON: `{"status":"pass|fail","summary":"...","filesChanged":N,"testsAdded":N,"attempts":N,"diagnosis":"..."}`

## Ejecución

### Paso 1 — Carga de contexto

1. Leer `.md` de la tarea completo
2. Leer ficheros de `## Contexto requerido`
3. Leer referencias fijas (arquitectura frontend + wireframe conventions)
4. Leer `tailwind.config.ts` para conocer tokens
5. Si el proyecto tiene tipos generados desde OpenAPI (ej. `types/api.ts` o similar): leerlos si la tarea consume endpoints

### Paso 2 — Plan

Redactar `var/task-runner/T{id}/plan.md` con orden TDD. Si detectas ambigüedad no resoluble:
- diagnóstico = "spec contradictorio" o "contexto insuficiente" → `status: fail` sin implementar

### Paso 3 — TDD loop

Por cada entrada de la tabla `## Tests`:

1. Escribir test (Vitest unit/component o Playwright E2E según corresponda)
   - Incluir `AC-xx` en nombre del test
   - Componentes: usar `@vue/test-utils` con `mount`/`shallowMount`
   - Composables: tests aislados pasando mocks de stores
   - Stores Pinia: tests con `createTestingPinia()`
2. Ejecutar el test → debe fallar por la razón correcta
   - `npm run test:unit -- {path}` o `npm run test:e2e -- {path}`
3. Escribir código de producción mínimo
4. Ejecutar el test → verde
5. Ejecutar tests del módulo/feature para no introducir regresiones

**Política de reintentos y escalada:** igual que implement-backend (3 intentos modelo asignado + diagnóstico + 3 intentos Opus con contexto ampliado si el diagnóstico justifica escalar).

### Paso 4 — Reglas no negociables

#### Arquitectura de capas
- **Páginas (`pages/`)**: orquestan. Llaman composables, renderizan componentes. NO contienen lógica de negocio.
- **Composables (`composables/`)**: capa de uso. Encapsulan estado + API + side effects. Retornan `{ state, actions, getters }` reactivos.
- **Componentes (`components/`)**: presentacionales. Reciben props, emiten eventos. NO importan stores ni hacen fetch directo (salvo componentes específicos "container" claramente documentados).
- **Stores (`stores/`)**: Pinia stores con state/actions/getters tipados.

Violación → rehacer antes de seguir.

#### TypeScript strict
- Sin `any` (si inevitable, comentar razón y usar `unknown` + narrowing)
- Sin `@ts-ignore` salvo justificación documentada
- `defineProps<T>()` con interfaz explícita
- `defineEmits<{(e: 'eventName', payload: T): void}>()`
- Respuestas de API con los tipos generados desde OpenAPI (si el proyecto tiene ese tooling)

#### i18n
- Sin strings hardcoded en templates. Todo pasa por `$t('key')` / `useI18n().t()`
- Las claves de traducción se añaden en los ficheros `locales/*.json` / `i18n/*.json` del proyecto
- Formatos de fecha/número con `$d()` / `$n()`, no `toLocaleString` directo

#### Tailwind / Design system
- Usa clases del design system (colores `primary-*`, spacing `xs/sm/md/...`, etc. definidos en `tailwind.config.ts`)
- Evita valores arbitrarios `[13px]`, `[#ff5733]`. Si imprescindible, comenta razón
- Reutiliza componentes base del sistema (Button, Input, Modal según wireframe-conventions) en lugar de reimplementar

#### Accesibilidad básica (el check exhaustivo lo hace `a11y-check`)
- `<label>` asociado a cada input
- `alt` en cada `<img>` (vacío si decorativa)
- Botones reales (`<button>`) en vez de `<div role="button">`
- Focus visible (no `outline: none` sin reemplazo)
- `tabindex` coherente

#### Tests
- Vitest para unit (utils, composables) y component (@vue/test-utils)
- Playwright para E2E (flujos críticos)
- Cada AC aplicable con al menos 1 test que lo cubra

### Paso 5 — Si consume API

- Si la tarea tiene tag `api`: verificar que el composable/store que llama al backend:
  - Usa tipos generados desde OpenAPI (si el proyecto tiene `openapi-typescript` configurado)
  - Maneja todos los error codes declarados en el AC (no ignorar 4xx silenciosamente)
  - Cancela requests pendientes al desmontar el componente (AbortController)

### Paso 6 — Consolidación del commit

1. Verificar `git status`: ficheros declarados en `## Archivos a crear/modificar` están presentes
2. Si hay extras: documentar en `plan.md § Desviaciones`
3. Si faltan declarados: FAIL
4. `git add <ficheros-tocados>`
5. Commit único:
   ```
   feat(T{id}): {título de la tarea}
   
   {resumen 2-3 líneas}
   ```
6. `git diff {base}..HEAD > var/task-runner/T{id}/changes.diff`

### Paso 7 — context-digest.md

Escribir `var/task-runner/T{id}/context-digest.md` (≤ 150 líneas), adaptado a frontend:

```markdown
# Context Digest — T{id}

## Task summary
{2-3 líneas: qué se implementó}

## Rutas / páginas afectadas
- /ruta/path — nueva / modificada

## Componentes tocados
- components/Button.vue — props nuevas, emits
- components/SignerCard.vue — nuevo componente

## Composables nuevos / modificados
- composables/useEnvelopes.ts

## Stores Pinia
- stores/envelope.ts — acción `closeEnvelope` añadida

## Endpoints consumidos
- POST /api/v1/envelopes/{id}/close
  - Tipos: request CloseEnvelopeRequest, response EnvelopeResponse (generados)

## Eventos emitidos / escuchados
- `envelope:closed` (emit interno via event bus), `push:envelope.closed` (websocket)

## Claves i18n añadidas
- envelope.actions.close
- envelope.errors.alreadyClosed

## Decisiones tomadas durante implementación
- {decisión + why}

## Alcance fuera de esta tarea
- ...
```

### Paso 8 — plan.md § Status final

Actualizar la sección final de `plan.md`:
```
## Status final
- Tests nuevos: N (todos en verde)
- Suite del módulo: PASS
- Build: PASS (vite build)
- Ficheros modificados: N
- Desviaciones documentadas: {sí|no}
```

### Paso 9 — Devolver JSON

```json
{"status":"pass","summary":"T{id} implementada, N tests verde, 1 commit","filesChanged":N,"testsAdded":N,"attempts":N}
```

## Qué NO hace

- No valida a11y exhaustiva (`a11y-check`)
- No valida coherencia design system (`design-system-check`)
- No valida contratos API (`contract-check-frontend`)
- No audita seguridad (`security-audit-core` + `security-audit-frontend`)
- No mide performance (`perf-smoke-frontend`)
- No actualiza docs externos (`docs-sync`)
- No abre PR ni actualiza el `.md`

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/frontend/01 - Implement Frontend.md`
- Arquitectura: `Arquitectura/Arquitectura Frontend.md`
- Wireframes y design: `.claude/skills/planning-detail/references/wireframe-conventions.md`
