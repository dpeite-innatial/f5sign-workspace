# Traspaso al dashboard-sf (PROVISIONAL): política de paso en `POST /steps` y cuatro códigos nuevos en `send`

| | |
|---|---|
| **Origen** | TASK-050 (ADR-0073), etapa C |
| **Medido en** | `f5sign-backend` rama `feat/step-policy` @ `a3a524b2`, y `b4fce49f` para que el veto y el deadline cuenten en las reglas de fin (2026-09-29). Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | dashboard-sf (`F5SignApiGateway.php`, `F5SignErrorMessages.php`, `WaybillEnvelopeService.php`). Nada obligatorio para los flujos de hoy |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` cuando el paquete ADR-0073 aterrice |

## Qué cambió (commiteado, no planeado)

- **`POST /api/v1/envelopes/{id}/steps`** acepta la política del paso. Todo es aditivo:
  - `ordinal`: entero ≥ 1, obligatorio, como hoy.
  - `completion`: `"ALL"` \| `"AT_LEAST"`, por defecto `"ALL"`.
  - `min_signatures`: entero ≥ 1 o `null`. Obligatorio con `AT_LEAST`, rechazado con `ALL`.
  - `veto`: booleano, por defecto `false`. Solo con `AT_LEAST`.
  - `deadline_hours`: entero ≥ 24 o `null`, contado desde la activación del paso.
  - Una política mal formada devuelve 422 `VALIDATION_ERROR` que nombra el campo.
  - Reenviar el mismo `ordinal` con la misma política devuelve 201; con otra política, 409 `CONFLICT`.
  - Vuestra llamada de hoy, `{"ordinal": N}`, significa exactamente lo que significaba: `ALL`, sin veto, sin deadline.
- **Avisos documentados en esa ruta** (ambas configuraciones se aceptan):
  - Un paso `AT_LEAST` sin deadline espera a todos sus miembros, así que un paso que no es el último debería llevar deadline.
  - Un paso con veto y sin deadline solo se resuelve al vencer el sobre (hasta entonces, cerrar ahora se rechaza).
- **La unanimidad tiene una sola codificación:** `AT_LEAST n` con `n` igual o mayor que los miembros bloqueantes del paso (SIGNER/APPROVER) se rechaza en el envío. Usad `ALL`.
- **`GET /api/v1/envelopes/{id}`**: cada elemento de `steps[]` gana `completion`, `veto`, `deadline_hours` y `deadline_at` (`activated_at` + horas; `null` antes de la activación o sin deadline). `min_signatures` pasa a publicarse como nullable (siempre fue `null` con `ALL`; el esquema anterior decía entero, y era incorrecto).
- **`POST /api/v1/envelopes/{id}/send`** gana cuatro 422 `ProblemCode`:
  - `STEP_MINIMUM_NOT_BELOW_MEMBERS`: el `detail` indica enviar `completion` `ALL`.
  - `STEP_MIXES_BLOCKING_ROLES`: un paso `AT_LEAST` con SIGNER y APPROVER a la vez.
  - `ENVELOPE_HAS_NO_BLOCKING_MEMBER`: no hay ningún SIGNER/APPROVER en todo el sobre.
  - `RECIPIENT_ROLE_NOT_BUILT`: hay un destinatario `IN_PERSON_HOST` o `CERTIFIED_DELIVERY`.
  - Si aplican varios, `code` es el primero y `detail` los nombra todos.
- **Reclamar una plaza sin reclamar** (`POST /api/v1/envelopes/{id}/recipients/{recipientId}/claim`) una vez pasado el deadline de su paso devuelve 409 `RECIPIENT_CAN_NO_LONGER_ACT` (código que ya existía).
- El evento `EnvelopeRosterDeclared` gana `veto` y `deadline_hours` en sus pasos. Solo os afecta si consumís eventos; los webhooks no están activos.

## Qué tiene que hacer el dashboard-sf

Nada obligatorio para los flujos de hoy.

Recomendado:

1. `F5SignErrorMessages.php`: mapear los cuatro códigos nuevos de `send`, al menos `RECIPIENT_ROLE_NOT_BUILT` y `ENVELOPE_HAS_NO_BLOCKING_MEMBER`, que vuestra autoría podría alcanzar si algún día añade destinatarios que no firman.
2. Si algún día agrupáis consignatarios en un mismo paso con "al menos N firman": crear el paso con `completion: "AT_LEAST"` y `min_signatures`, y dar `deadline_hours` a los pasos así que no sean el último. Entonces el comentario de `WaybillEnvelopeService.php` sobre quórum/CC pasa a ser relevante y hay que revisitarlo.
