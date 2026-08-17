---
name: contract-check-backend
description: 'Valida los contratos publicados del backend (PHP/Symfony): anotaciones Nelmio #[OA\\*] frente a lo que el endpoint realmente emite (conjunto de claves cerrado, no solo "no falta ninguna"), eventos de Contract/Event (nombre en pasado, registro en EventTypeRegistry, reglas de payload aditivo) y la existencia del traspaso a frontal cuando el contrato cambia. AsyncAPI no tiene diana en este repo y se reporta como ausente en vez de fingirse. Úsalo con /contract-check-backend TASK-NNN. Activar con "validar contratos backend", "check API de la task", "revisar Nelmio y eventos".'
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
- `var/task-runner/TASK-NNN/openapi-snapshot.json` — lo pre-genera `task-runner` con
  `make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"`
- El `.md` de la task: **§5 Verification** es lo que hace de criterios de aceptación (no hay `AC-NN`)

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

### Paso 2 — ⚑ El conjunto de claves, **cerrado**: el spec omitiendo lo que el endpoint sí emite

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

### Paso 3 — Eventos: `Contract/Event/`, y el registro es el que muerde

Los eventos publicados viven en `src/F5Sign/<BC>/Contract/Event/`, **no** en `Domain/Event/`.

- [ ] Clase `final readonly`, constructor tipado.
- [ ] **Nombre en pasado** (`EnvelopeCompleted`, no `CompleteEnvelope`) — ADR-0011.
- [ ] ⚑ **Registrado en [`EventTypeRegistry`](../../../src/F5Sign/Foundation/Serialization/EventTypeRegistry.php).**
      No es burocracia: un `event_type` que el registro no conoce **no se puede reconstruir**, el relay lo
      cuenta como poison y a los cinco intentos lo **pone en cuarentena avanzando el cursor por encima** —
      el hecho no llega nunca al broker y, para Notification, es una notificación que no se envía jamás.
      Sin registrar → `fail`, categoría `unregistered-event-type`.
- [ ] Emitido de verdad: si el evento es nuevo, el diff contiene quien lo publica.
- [ ] Si es async: rutado en `config/packages/messenger.yaml` y handler registrado.

### Paso 4 — Reglas de payload (evolución del log, ADR-0031)

El log es permanente y **la evolución es solo por upcast**: reescribir un payload almacenado rompe su
`sys_commitment`, así que está prohibido. De ahí tres reglas duras:

- [ ] ⛔ **Nunca un campo obligatorio nuevo en un payload existente.** Se lee con
      `Row::optionalString()` — su propio docblock lo dice, y hay precedente en cuatro eventos de cuatro
      BCs. Campo obligatorio añadido → `fail`, categoría `payload-required-field`.
- [ ] ⛔ **Nunca renombrar un `event_type` en sitio.** Se añade el nuevo, se escriben ambos, se retira el
      viejo. Renombrado en sitio → `fail`: los bytes ya escritos dejan de decodificarse.
- [ ] ⚠ **Y avisa de que hoy nada de esto tiene red.** El fixture de bytes canónicos por `event_type` está
      registrado en ADR-0031 como *"Not enforced — queued, not built"*, y el round-trip que existe
      serializa y deserializa **con el mismo código**, así que nunca puede detectar un `fromPayload()`
      incompatible: los dos lados se mueven juntos y se alejan a la vez de los bytes que ya están en el log.
      Un cambio de payload sin ese fixture es `warn` con esta frase, no un pass silencioso.

### Paso 5 — Si el contrato cambió, tiene que haber traspaso al frontal

- [ ] Existe `docs/frontend-handoff/*.md` en este changeset describiendo el cambio → si no:
      `fail`, categoría `handoff-missing`. Convención en
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
