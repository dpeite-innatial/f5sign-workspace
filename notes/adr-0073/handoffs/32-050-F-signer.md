# Traspaso al signer (PROVISIONAL): aviso de "copia sellada lista" y lectura tras el cierre

| | |
|---|---|
| **Origen** | TASK-050 §3.7 (ADR-0073 §2.15), etapa F |
| **Medido en** | `f5sign-backend` rama `feat/step-policy`: el aviso @ `c8e404c4` y la regla de lectura @ `70593ec2` (2026-09-29). Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | signer. El dashboard-sf no se ve afectado |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` |

## Qué cambió (commiteado)

1. **Nuevo aviso `SEALED_COPY_READY`** (email; en/es) para los miembros informativos (`VIEWER`, `REVIEWER`,
   `EDITOR`) cuando el sobre se completa y hay un documento sellado:
   - si el sobre termina `AGREED`, lo reciben todos los informativos, se haya activado su paso o no;
   - si termina `NOT_AGREED`, solo aquellos cuyo paso se llegó a activar;
   - si no se selló nada, nadie recibe nada.

   Lleva un **enlace de firma nuevo, emitido al completarse el sobre**, no el de la invitación. Abre
   `/s/{token}` exactamente como cualquier otro enlace.
2. **Un informativo cuyo paso nunca se activó ya puede entrar y leer una vez cerrado el sobre.** Antes recibía
   `STEP_NOT_ACTIVE`. Ahora el paso solo se pregunta mientras el sobre está abierto. Desde el cierre deciden las
   reglas de siempre:
   - los informativos leen, sea cual sea el desenlace;
   - los bloqueantes de ese paso siguen rechazados (`ENVELOPE_NO_LONGER_LIVE` al abrir y en el modelo de lectura,
     404 en los bytes).
3. En consecuencia, **tras el cierre `GET /signing/session/auth` ya no responde 409 `STEP_NOT_ACTIVE`** a un
   miembro de un paso nunca activado. Responde con el descriptor normal (200): un informativo pasa, y un bloqueante
   ve su `outcome` de pata cerrada (p. ej. `RELEASED`).
4. Entre el cierre y `COMPLETED`, la lectura responde `SEAL_PENDING` como ya hacía. Los bytes dan 404 hasta el
   sellado.
5. `ENVELOPE_COMPLETED` ("firmado") solo lo reciben ya quienes firmaron un sobre `AGREED`, y su texto ya no dice
   "firmado por todos". Esto no afecta al código del signer, solo al correo.

## Qué tiene que hacer el signer

1. **Un `VIEWER`/`REVIEWER`/`EDITOR` puede llegar por primera vez a un sobre ya `COMPLETED`**, sin haber pasado
   nunca por la vista de "pendiente". La vista de lectura del documento sellado tiene que funcionar como primera
   pantalla en ese caso, sin suponer una sesión previa ni un paso activo.
2. **No mostrar `STEP_NOT_ACTIVE` ("todavía no es tu turno") tras el cierre**: el backend ya no lo emite ahí. Si el
   signer deducía "no es tu turno" por su cuenta, a partir de otro dato, revisarlo.
3. Mientras el sello no ha llegado (`SEAL_PENDING`), la misma pantalla de espera que ya existe.

## Pendiente (no actuar todavía)

- Viene otro traspaso con un campo nuevo `envelope_outcome` en `GET /signing/session/auth`, más un cambio en
  cuándo aparece `REVOKED`. Está en construcción.
