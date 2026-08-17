---
name: contract-check-backend
description: 'Valida los contratos publicados del backend (PHP/Symfony): anotaciones Nelmio #[OA\\*] frente a lo que el endpoint realmente emite (conjunto de claves cerrado, no solo "no falta ninguna"), eventos de Contract/Event (el valor de EVENT_TYPE, que nada fija y cuyo cambio re-tipa historia ya escrita; reglas de payload aditivo; y por qué NO hay que comprobar el registro ni el routing, que son automáticos) y la existencia del traspaso a frontal cuando el contrato cambia. AsyncAPI no tiene diana en este repo y se reporta como ausente en vez de fingirse. Úsalo con /contract-check-backend TASK-NNN. Activar con "validar contratos backend", "check API de la task", "revisar Nelmio y eventos".'
---

# Contract Check (backend)

Contratos publicados: HTTP y eventos. Se invoca si el diff toca `src/**/UI/Http/`, `config/routes/`,
cualquier `#[OA\`, o un `Contract/Event/`.

## Invocación

```
/contract-check-backend TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` y `context-digest.md`
- `var/task-runner/TASK-NNN/openapi-snapshot.json`. ⚠ **Dos trampas al generarlo.** El recipe `make sf` no
  lleva `@`, así que la **primera línea de su stdout es el propio comando** y el fichero redirigido no es JSON
  válido: descarta esa línea o usa el contenedor directamente. Y `make sf` corre en el php-fpm del stack, que
  monta `../f5sign-backend` — en un worktree el snapshot es **el spec de otra rama**.
- El `.md` de la task: su sección de **verificación** hace de criterios de aceptación (no hay `AC-NN`)

## Outputs

- `var/task-runner/TASK-NNN/contract-check.report.md`
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...],"surfacesAbsent":[...]}`

## Ejecución

### Paso 1 — HTTP: los strings de `#[OA\*]` son contrato, no comentarios

⚠ **Se emiten literalmente al spec que ratifica el equipo de frontal.** Uno de ellos llegó a decir a los
clientes que enviaran un valor que el endpoint no acepta. Entran en el barrido de la regla de autoría 1.

Por cada controlador del diff (`src/**/UI/Http/`):

- [ ] `#[OA\Response]` por cada código HTTP **alcanzable** — no los que "tocaría" devolver, los que el
      código puede producir de verdad, incluidos los 404/409 que salen de una excepción de dominio mapeada
      (ADR-0029).
- [ ] `#[OA\RequestBody]` si acepta body; DTOs con `#[OA\Property]` tipadas y coherentes con la firma PHP.
- [ ] Esquema de seguridad declarado si la ruta está autenticada, y la cabecera obligatoria de la ruta
      declarada también (una ruta de máquina que exige `F5Sign-Declared-Subject` y no lo publica deja al
      cliente de navegador sin poder mandarla, que es un fallo real ya ocurrido en CORS preflight).

### Paso 2 — El conjunto de claves cerrado: **ya hay un test que lo hace, ejecútalo**

⚑ **Antes de enumerar nada a mano:**
[`OpenApiSpecTest`](../../../tests/F5Sign/Acceptance/OpenApiSpecTest.php) ya cierra esto mecánicamente contra
el spec **generado**: `published_response_schemas_declare_every_key_the_presenter_emits` compara en las dos
direcciones sobre una vista completamente poblada **y lleva control positivo** (falla si el test podría pasar
en vacío), y `every_published_enum_is_pinned_to_its_php_enum_or_classified` censa los enums y falla tanto por
uno sin clasificar como por una clasificación obsoleta — incluidos los cuatro defectos históricos que se
citan abajo. **Corre ese test y lee su salida.** Rehacerlo a mano y tomar el pase manual como red es
exactamente el riesgo. Si crees que falta un caso, se añade **allí**, no aquí.

Lo que sigue es el porqué, para saber qué estás leyendo cuando ese test falle:

Este es el check que de verdad paga, y el que la versión anterior no tenía. La comprobación natural
—*"¿está declarado todo lo que el AC pide?"*— **solo mira en una dirección**. El fallo real de este repo fue
el contrario: los endpoints devolvían `signing_mode` y `recipients[].document_assignments` desde siempre y
**el spec los omitía**; `Envelope.status` no publicaba `READY_TO_SEAL`/`ROUTING_FAILED`/`SEALING_FAILED`, y
`Recipient.role` se dejaba fuera `IN_PERSON_HOST`/`CERTIFIED_DELIVERY`.

Es la misma asimetría que en PHPStan nivel 9: **rechaza una clave que falta y acepta una de más**. Así que:

- [ ] Enumerar lo que el controlador/DTO **emite de verdad** y compararlo con lo que el spec declara, **en
      las dos direcciones**. Campo emitido y no declarado → `fail`, categoría `undeclared-emission`.
- [ ] Para cada enum que sale por la API: **todos** sus `case` publicados, o los no soportados marcados
      explícitamente como tales. Contar los `case` del enum PHP y comparar; no fiarse de la lista del spec.
- [ ] Códigos HTTP alcanzables y no declarados → `fail`.

### Paso 3 — Eventos: `Contract/Event/`, y lo que muerde es el VALOR de `EVENT_TYPE`

Los eventos publicados viven en `src/F5Sign/<BC>/Contract/Event/`, **no** en `Domain/Event/`.

- [ ] Clase `final readonly`, constructor tipado.
- [ ] **Nombre en pasado** — ADR-0011, y con dos avisos. Primero: la forma superficial es la mitad que el
      propio ADR llama **convención**; lo load-bearing es la **partición de propiedad del prefijo** (que
      `Signature*` sea de SignatureExecution, `Envelope*` de Envelope) y el **espejo**, y su lint es
      *candidate rule, not yet written* — así que hay excepciones legítimas por la corolaria del dueño del
      acto (`Session/Contract/Event/SignatureCommitted.php`,
      `SignatureExecution/Contract/Event/EnvelopeSealed.php`). Segundo: `EnvelopeReadyToSeal` **no** es un
      verbo en pasado y **es conforme** (nombre de transición a estado objetivo). Y ADR-0011 está `Proposed`,
      luego por la regla 7 aún no vincula: reportar como `warn`, nunca `fail`.
- [ ] ⚠ **No compruebes que el evento está "registrado": el registro es automático.**
      `RegisterDomainEventsPass` globea `*/Contract/Event/*.php`, filtra por subclase de `Event`, lee
      `EVENT_TYPE` y se re-ejecuta al añadir o quitar ficheros (`GlobResource`). Un evento bien colocado **no
      puede** quedar sin registrar, y uno malformado lanza `LogicException` **al compilar el contenedor**, o
      sea que la suite entera se pone roja antes de llegar aquí. `LOAD-BEARING.md` §2 ya lo dice.
      Lo que **sí** hay que comprobar es lo de abajo: el **valor** de `EVENT_TYPE`.
- [ ] ⛔ **El valor de `EVENT_TYPE` no lo fija nada, y cambiarlo re-tipa historia ya escrita.** Hay 26
      declarados y **ningún test asserta un valor**: el que los fijaba se retiró en el stage 2 del event log
      y su reemplazo está *queued* en ADR-0031. Si el diff **cambia** un valor existente → `fail`, categoría
      `event-type-rewrite`: el log es permanente y append-only, así que los bytes ya escritos dejan de
      decodificarse y no hay reparación. Si **añade** uno nuevo, `pass` con nota.
- [ ] Emitido de verdad: si el evento es nuevo, el diff contiene quien lo publica.
- [ ] ⚠ **No busques una entrada de `routing:` para un evento: está deliberadamente vacía.** El propio
      `messenger.yaml` lo explica — *"No class is bus-routed to `async_events` directly: cross-BC events reach
      the broker only through the event log + relay (ADR-0031), which forces the transport with a
      `TransportNamesStamp`"*. Reportar que falta es un falso positivo; **añadirla contradice ADR-0031**. El
      handler también se registra solo, por `_instanceof` de `MessengerEventSubscriber`.

### Paso 4 — Reglas de payload (evolución del log, ADR-0031)

El log es permanente y **la evolución es solo por upcast**: reescribir un payload almacenado rompe su
`sys_commitment`, así que está prohibido. De ahí tres reglas duras:

- [ ] ⛔ **Nunca un campo obligatorio nuevo en un payload existente.** Se lee con
      `Row::optionalString()` — su propio docblock lo dice, y hay precedente en cuatro eventos de **tres**
      BCs (Session ×2, SignatureExecution, Envelope). Campo obligatorio añadido → `fail`, categoría `payload-required-field`.
- [ ] ⛔ **Nunca renombrar un `event_type` en sitio.** Se añade el nuevo, se escriben ambos, se retira el
      viejo. Renombrado en sitio → `fail`: los bytes ya escritos dejan de decodificarse.
- [ ] ⚠ **Y avisa de que hoy nada de esto tiene red.** El fixture de bytes canónicos por `event_type` está
      registrado en ADR-0031 como *"Not enforced — queued, not built"*, y el round-trip que existe
      serializa y deserializa **con el mismo código**, así que nunca puede detectar un `fromPayload()`
      incompatible: los dos lados se mueven juntos y se alejan a la vez de los bytes que ya están en el log.
      Un cambio de payload sin ese fixture es `warn` con esta frase, no un pass silencioso.

### Paso 5 — Si el contrato cambió, tiene que haber traspaso al frontal

- [ ] Existe en **este diff** un fichero nuevo bajo `docs/frontend-handoff/` **que no sea `README.md`** → si
      no: `fail`, categoría `handoff-missing`. ⚠ No uses el glob `docs/frontend-handoff/*.md` como condición:
      el README vive ahí, así que el glob **siempre casa** y el check nunca falla. Convención en
      [`docs/frontend-handoff/README.md`](../../../docs/frontend-handoff/README.md); lo escribe `docs-sync`.
      Un cambio de contrato sin traspaso es el patrón que dejó al firmante esperando un `signed_copy_url`
      que nadie envía.

### Paso 6 — Superficies ausentes

**`docs/asyncapi/` no existe en ninguna rama de este repo** (comprobado 2026-08-17). No fallar por ello y
**no crearlo**: reportar en `surfacesAbsent` qué evento queda sin documentación legible por máquina y decir
dónde vive mientras tanto (su clase `Contract/Event/`, su entrada en `EventTypeRegistry`, y el ADR que lo
gobierna). Si la carencia es real y repetida, es una fila de `docs/BACKLOG.md`, no un fichero fantasma.

## Report

```markdown
# contract-check-backend — TASK-NNN

**Status:** {PASS|FAIL|WARN} · **Issues:** {B} bloqueantes, {W} warnings

## Contrato HTTP
- Declarado y no emitido: {lista}
- **Emitido y no declarado: {lista}**  ← la dirección que se olvida
- Enums: {enum} {n} cases en PHP / {m} publicados

## Eventos
- {Evento}: pasado ✓ · registrado en EventTypeRegistry ✓ · payload aditivo ✓

## Sin red
- {cambio de payload sin fixture de bytes canónicos, si aplica}

## Traspaso a frontal
- {fichero, o "AUSENTE"}

## Superficies ausentes (no creadas a propósito)
- docs/asyncapi/: {evento} sin contrato legible por máquina; vive en {clase} + ADR-NNNN
```

## Qué NO hace

- No valida lógica de negocio (`task-validate-backend`).
- No audita seguridad de endpoints (`security-audit-*`).
- No escribe el traspaso ni el OpenAPI (`docs-sync` el primero; Nelmio genera el segundo inline).
- No detecta breaking changes comparando contra `develop` (eso es CI, y hoy no existe).
