---
name: contract-check-backend
description: Valida contratos externos desde el lado backend (PHP/Symfony): anotaciones Nelmio #[OA\\*] en endpoints, OpenAPI generado coherente con los AC, definición correcta de domain events y sincronización con docs/asyncapi/. Solo para repositorios con stack PHP/Symfony. Úsalo con /contract-check-backend T{id}. Activar con "validar contratos backend", "check API PHP de tarea", "revisar Nelmio/AsyncAPI".
---

# Contract Check

Validación de contratos API y eventos. Solo si tags incluye `api` o `event`.

## Invocación

```
/contract-check T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/openapi-snapshot.json` (si tag `api` — lo pre-genera task-runner)
- `.md` de la tarea
- README de la story padre (para AC)

Del repo:
- Controladores, DTOs de HTTP, Domain events, Messages, `docs/asyncapi/*.yaml` si existe

## Outputs

- `var/task-runner/T{id}/contract-check.report.md`
- JSON:
  ```json
  {"status":"pass|fail|warn","summary":"...","issues":[...],"tagMismatches":[]}
  ```

## Ejecución

### Paso 1 — Detectar tag mismatch

- Si tag `api` y el diff no contiene ficheros bajo `src/**/Infrastructure/Http/` ni `src/**/Application/*/DTO/` → `tagMismatches: ["api"]`
- Si tag `event` y el diff no contiene `Domain/Event/`, `Application/Message/`, ni handlers → `tagMismatches: ["event"]`

### Paso 2 — Checks tag `api`

#### Anotaciones Nelmio
Para cada Controller modificado:
- [ ] Cada método público (endpoint) tiene `#[OA\Response(response=X, ...)]` para cada HTTP status listado en AC de la story
- [ ] Si el método acepta body: `#[OA\RequestBody(required=true, content=...)]`
- [ ] Si el endpoint es protegido: security scheme declarado (bearer/oauth2)

Para cada DTO request/response:
- [ ] Cada propiedad tiene `#[OA\Property(type="...", description="...")]`
- [ ] Tipos concordantes con la firma PHP

#### OpenAPI generado
- [ ] `openapi-snapshot.json` existe y es JSON válido
- [ ] Contiene el path del endpoint modificado
- [ ] Todos los `$ref` resuelven a schemas presentes en `components.schemas`
- [ ] Sin warnings ni errors en la generación (si task-runner capturó stderr)

#### Coherencia con AC
Para cada `AC-\d+` en la story que describa request/response/errores HTTP:
- [ ] HTTP status declarado en AC ∈ responses del OpenAPI
- [ ] Error code aplicación (ej. `ENVELOPE_ALREADY_CLOSED`) aparece en el schema del response del código HTTP correspondiente
- [ ] Path y método del AC = path y método en Nelmio
- [ ] Campos del request descritos en AC = `#[OA\Property]` del DTO request
- [ ] Campos del response descritos en AC = `#[OA\Property]` del DTO response

Divergencias → `fail` categoría `ac-mismatch`.

### Paso 3 — Checks tag `event`

#### Definición del evento
Para cada fichero modificado en `src/**/Domain/Event/`:
- [ ] Clase es `final readonly`
- [ ] Nombre en tiempo pasado (`EnvelopeClosed`, no `CloseEnvelope`, no `Closing`)
- [ ] Constructor tipado en todas las propiedades
- [ ] Implementa la interfaz de domain event del proyecto si existe (ej. `DomainEventInterface`)

#### Emisión
- [ ] Si el evento es nuevo → grep en el diff por uso (dispatch): debe haberse añadido llamada a `$this->eventBus->dispatch(new {Event}(...))` o `$entity->recordEvent(new ...)` en algún Handler o Entity
- [ ] Si el evento aparece en `context-digest.md § Eventos de dominio / Emite` → confirmar que está listado en `Implementación/Skills de Ejecución de Tareas/` o en el catálogo oficial (`/.claude/skills/planning-detail/references/domain-events-catalog.md` si existe)
  - Si no aparece → `warn` categoría `catalog`: "añadir al catálogo"

#### AsyncAPI
Si existe `docs/asyncapi/`:
- [ ] Parsear YAML relevante
- [ ] Para cada evento emitido/consumido por esta tarea: schema en `components.schemas` con propiedades idénticas al evento PHP
- [ ] Channel/queue name coincide con configuración Messenger
- [ ] Si el evento emitido es nuevo y no aparece en AsyncAPI → `fail` categoría `asyncapi-missing`

Si NO existe `docs/asyncapi/`: emitir warn "AsyncAPI no presente, contratos de eventos sin documentar" y seguir. No bloquear.

#### Messenger (si mensaje async)
- [ ] Rutado definido en `config/packages/messenger.yaml` (grep)
- [ ] Handler registrado (clase con `AsMessageHandler` u otra convención del proyecto)
- [ ] Si puede fallar: retry strategy definida

### Paso 4 — Intersección (tags `api` + `event`)

Si la tarea tiene ambos:
- [ ] Para cada AC que diga "endpoint emite evento X": verificar que el Handler del comando del endpoint efectivamente dispatcha X
- [ ] Verificar que existe test E2E que valida la emisión del evento tras llamar al endpoint

## Report

```markdown
# contract-check — T{id}

**Status:** {PASS|FAIL|WARN}
**Tags evaluados:** {api, event}
**Issues:** {B} bloqueantes, {W} warnings

## Bloqueantes
- [{categoría}] {fichero:línea} {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Tag mismatches
- {lista o "ninguno"}
```

## JSON de retorno

```json
{"status":"fail","summary":"1 bloqueante en AsyncAPI","issues":[{"severity":"fail","category":"asyncapi-missing","message":"Evento EnvelopeClosed sin schema en docs/asyncapi/envelope.yaml"}],"tagMismatches":[]}
```

## Qué NO hace

- No valida lógica de negocio (task-validate)
- No audita seguridad de endpoints (security-audit)
- No actualiza AsyncAPI (docs-sync lo hace)
- No genera OpenAPI (Nelmio lo hace inline)
- No detecta breaking changes (eso es CI comparando contra main)
- No analiza performance (perf-smoke)

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/backend/03 - Contract Check Backend.md`
- Estrategia docs: `memory/project_api_docs_strategy.md`
