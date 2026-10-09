# Traspaso al signer (PROVISIONAL): los roles informativos ya no hacen commit

| | |
|---|---|
| **Origen** | TASK-050 §3.2 (ADR-0073 §2.1), etapa B |
| **Medido en** | `f5sign-backend` rama `feat/step-policy` @ `1cc5ef0e` (2026-09-29). Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | signer. El dashboard-sf no crea destinatarios `VIEWER`/`REVIEWER`/`EDITOR` hoy, así que no le afecta, aunque la ruta de commit delegado también lo emite |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` |

## Qué cambió (commiteado)

- **Nuevo `ProblemCode` `COMMIT_NOT_OFFERED_TO_ROLE`** (409). El nombre ya es definitivo: lo confirmó el coordinador.
  Lo devuelve `POST /api/v1/signing/commit` (y el commit delegado
  `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature`) cuando quien hace commit es `VIEWER`,
  `REVIEWER` o `EDITOR`. No se admite nada y no se registra ningún acto.
- **Un miembro informativo ya no retiene su paso.** Antes, un `VIEWER` cerraba su participación haciendo commit
  (era la única forma), y el paso le esperaba. Ahora el paso avanza sin él. Un paso con solo miembros informativos
  se cierra en cuanto se activa. Al cerrar el sobre, el informativo queda `RELEASED` con `released_by: ENVELOPE_CLOSED`.
- Mientras el sobre sigue abierto, el miembro informativo sigue pasando la puerta y leyendo el documento igual que
  antes: solo cambia que no puede hacer commit.

## Qué tiene que hacer el signer

1. **No ofrecer la acción de firmar/confirmar a `VIEWER`, `REVIEWER` ni `EDITOR`.** Si la vista de lectura tenía un
   botón de "confirmar lectura" o similar que llamaba a `/signing/commit`, retirarlo: ya no se admite.
2. **Manejar `COMMIT_NOT_OFFERED_TO_ROLE`** en el clasificador de errores del commit (`useSignerNavigation.ts`),
   del mismo modo que `DECLINE_NOT_OFFERED_TO_ROLE` en el rechazo: esta persona no puede hacer esto aquí, así que se
   oculta la acción y se queda en la vista de lectura. No es reintentable.
3. Un código desconocido ya cae en el `default` seguro, pero conviene la rama explícita para no mandar al usuario a
   una pantalla de error genérica.

## Pendiente, no commiteado todavía (no actuar)

- Aviso de "copia sellada lista" con un enlace nuevo para los informativos al completarse el sobre: el aviso ya está
  commiteado (`c8e404c4`), pero el enlace aún no abre para un informativo cuyo paso nunca se activó. Llegará en otro
  traspaso cuando esté cerrado.
