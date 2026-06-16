---
name: implement-backend
description: Implementa una tarea backend (PHP/Symfony) del Planning/ siguiendo TDD estricto, respetando arquitectura hexagonal/DDD/CQRS. Lee el .md de la tarea y su Contexto requerido, escribe código + tests, anota endpoints con Nelmio OpenAPI, y produce artefactos context-digest.md, plan.md y un único commit final. Solo para repositorios con stack PHP/Symfony. Úsalo con /implement-backend T{id}. Activar con "implementa backend T{id}", "codifica tarea PHP...", "ejecuta implementación backend de...".
---

# Implement

Implementación TDD de una tarea. El modelo se elige según `Complejidad` del frontmatter (Sonnet para baja/media, Opus para alta) — el invocador (`task-runner` o el usuario vía Agent tool) selecciona el modelo al llamar a esta skill.

## Invocación

```
/implement T{id}                                   # resuelve por Glob
/implement {ruta al .md}
/implement T{id} --model=opus                      # override explícito (para escalada o testing)
/implement T{id} --amplified-context               # carga contexto ampliado (para escalada)
```

Si invocado por task-runner vía Agent tool, el modelo ya viene impuesto por el `model:` del Agent y `--amplified-context` se pasa como flag.

## Inputs

- `.md` de la tarea
- Ficheros listados en `## Contexto requerido` del `.md`
- Si `--amplified-context`: además, README de story padre + README de epic padre + `.md` de cada dependencia + `Implementación/` docs de cross-cutting + catálogo de eventos
- Referencias fijas siempre: `Arquitectura/Patrones de Código y Convenciones.md`

## Outputs

- Código + tests commiteados (1 único commit) en la rama actual `feat/T{id}-*`
- `var/task-runner/T{id}/plan.md`
- `var/task-runner/T{id}/context-digest.md`
- JSON de retorno (última línea):
  ```json
  {"status":"pass|fail","summary":"...","filesChanged":N,"testsAdded":N,"attempts":N,"diagnosis":"..."}
  ```

## Ejecución

### Paso 1 — Carga de contexto

1. Leer el `.md` de la tarea completo
2. Leer cada ruta listada en `## Contexto requerido` → subsecciones `### Specs del proyecto`, `### Código existente a consultar`, etc.
3. Leer referencias fijas
4. Si `--amplified-context`: cargar también los ficheros ampliados

### Paso 2 — Plan

Redactar `var/task-runner/T{id}/plan.md`:

```markdown
# Plan — T{id}

## Orden de ejecución (TDD)
1. [TEST] tests/Unit/.../FooTest::testCaso1
2. [CODE] src/.../Foo.php — añadir X
3. [TEST] tests/Integration/.../BarTest::testCaso1
4. [CODE] src/.../Bar.php
...

## Decisiones arquitectónicas
- {decisiones que se van a tomar durante la implementación}

## Desviaciones del .md original
- (vacío por ahora; se actualiza al final si hay)

## Status final
(se rellena al terminar)
```

**Gate de plan:** si al redactar el plan detectas ambigüedad no resoluble con el contexto disponible:
- Si diagnóstico = "spec contradictorio" o "contexto insuficiente" → devolver `status: fail` con `diagnosis` explícito y **no implementar nada**
- Ejemplo: el `.md` dice "el endpoint devuelve 200" pero AC exige "409 en este caso" sin resolver contradicción

### Paso 3 — TDD Loop

Por cada entrada de la tabla `## Tests` del `.md`, en orden:

1. **Escribir el test** en el fichero declarado. El test debe:
   - Incluir `AC-xx` en el nombre del método o como `@covers` si cubre un AC
   - Tener aserción concreta que fallará si el código de producción no existe o está mal
2. **Ejecutar el test** → confirmar que falla por la razón correcta (no por sintaxis, no por fichero inexistente):
   - `composer test:unit -- --filter={TestClass}::{method}` (o equivalente para integration/e2e)
3. **Escribir/modificar código de producción** mínimo necesario
4. **Ejecutar el test** → debe pasar (verde)
5. **Ejecutar la suite del módulo** (no toda la suite, solo módulo relacionado) para detectar regresiones
6. Siguiente test

**Política de reintentos:**
- Si un test no pasa tras 3 intentos de ajustar el código (3 iteraciones de editar-probar):
  - Generar diagnóstico: ¿test mal escrito?, ¿spec contradictorio?, ¿contexto insuficiente?, ¿complejidad excede el modelo?
  - Si diagnóstico = "spec contradictorio" o "contexto insuficiente" → `status: fail` sin escalar
  - Si diagnóstico = "complejidad excede el modelo" y el modelo actual no es Opus → devolver `status: fail` con `diagnosis: "escalate-to-opus"` para que task-runner pueda reintentar
  - Si diagnóstico = "test mal escrito por mí" → ya has usado los 3 intentos, devolver `status: fail`

### Paso 4 — Anotaciones OpenAPI (si tags incluye `api`)

Para cada endpoint nuevo/modificado:
- `#[OA\Response]` para cada código HTTP declarado en AC
- `#[OA\RequestBody]` si acepta body
- DTOs request/response con `#[OA\Property]` tipadas
- Security scheme si el endpoint es protegido

Tras anotar: ejecutar `bin/console nelmio:apidoc:dump --format=json` — debe completar sin error.

### Paso 5 — Reglas no negociables

Durante toda la implementación:

- **Domain no importa Symfony/Doctrine**. Si tests/código en `src/**/Domain/` incluye `use Symfony\` o `use Doctrine\`, rehacer.
- **Solo aggregate roots tienen repositorio**. Subordinate entities se modifican a través de su root.
- **Commands via bus, queries directas**. Controllers inyectan `CommandBusInterface` (para comandos) y `QueryService` (para queries), nunca handlers directamente.
- **VOs `final readonly`** con constructor privado + named constructors
- **Domain events en pasado** (`EnvelopeClosed`, no `CloseEnvelope`)

Si se detecta violación al escribir código: corregir antes de avanzar al siguiente test.

### Paso 6 — Consolidación del commit

Al terminar todos los tests (todos en verde):

1. Verificar `git status`: deben aparecer todos los ficheros declarados en `## Archivos a crear/modificar` del `.md`
2. Si hay ficheros adicionales no declarados → reportar en `plan.md § Desviaciones`
3. Si faltan ficheros declarados → FAIL
4. `git add <ficheros-tocados>` (específicos, no `git add .`)
5. Commit único:
   ```
   feat(T{id}): {título de la tarea extraído del .md}
   
   {resumen de 2-3 líneas del contexto de la tarea}
   ```
6. Generar diff acumulado: `git diff {base}..HEAD > var/task-runner/T{id}/changes.diff` donde `{base}` = merge-base con master

### Paso 7 — context-digest.md

Escribir `var/task-runner/T{id}/context-digest.md` con esta estructura EXACTA (≤ 150 líneas):

```markdown
# Context Digest — T{id}

## Task summary
{2-3 líneas: qué se implementó}

## Reglas de negocio aplicadas
- {bullet por regla, con referencia al spec § cuando aplique}

## Modelo de datos tocado
| Tabla | Columnas afectadas | Acción |
|---|---|---|

## Contratos afectados

### API
- {método path — descripción breve}
  - Request: {DTO}
  - Response: {HTTP status → DTO/error}

### Eventos de dominio
- Emite: {EventName} — ver src/.../Event/
- Escucha: {EventName} (o "ninguno")

## Invariantes preservadas
- {bullet por invariante}

## Decisiones tomadas durante implementación
- {decisión + why}

## ADRs vinculantes
- {referencias a ADRs aplicables, o "ninguno"}

## Alcance fuera de esta tarea
- {qué se dejó para otra tarea, con ID si existe}
```

### Paso 8 — Completar plan.md § Status final

Actualizar la sección final de `plan.md`:
```
## Status final
- Tests nuevos: N (todos en verde)
- Suite del módulo: PASS
- Ficheros modificados: N
- Desviaciones documentadas: {sí|no}
```

### Paso 9 — Devolver JSON

Última línea de la respuesta:
```json
{"status":"pass","summary":"T{id} implementada, N tests en verde, 1 commit","filesChanged":N,"testsAdded":N,"attempts":N}
```

## Qué NO hace

- No valida seguridad (security-audit), compliance (eidas-compliance), performance (perf-smoke) — solo garantiza que los tests declarados pasan
- No actualiza documentación fuera del código (docs-sync), excepto OpenAPI inline vía Nelmio
- No abre PR (pr-ready)
- No actualiza el `.md` de la tarea con el estado (task-close)
- No explora specs fuera de `Contexto requerido` — si falta algo, `status: fail` con diagnóstico

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/backend/01 - Implement Backend.md`
- Patrones de código: `Arquitectura/Patrones de Código y Convenciones.md`
