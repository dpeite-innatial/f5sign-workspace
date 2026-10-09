# Traspaso al signer (PROVISIONAL): el enum de estado del sobre pierde `EXPIRED`

| | |
|---|---|
| **Origen** | TASK-049 (caducidad del sobre, dentro del paquete ADR-0073) |
| **Medido en** | `f5sign-backend` rama `feat/envelope-expiry` @ `01e77681` (2026-09-29). Sin mergear en `develop`, sin desplegar. Los nombres pueden cambiar hasta que el paquete aterrice |
| **Repos afectados** | signer (`f5sign-signer`, worktree `f5sign-signer-adr0073`, rama `feat/prep-adr-0073-envelope-ending`). El resto del contrato de caducidad (`expires_in_days`, `expiry-extensions`) es del integrador: ver `10-049-dashboard.md` |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` |

## Qué cambió (commiteado)

- **El `status` del sobre ya no tiene `EXPIRED`.** Un sobre caducado se lee `status: COMPLETED`, con
  `outcome: NOT_AGREED` y `end_cause: EXPIRED` (sin actor), o `outcome: AGREED` si su acuerdo ya estaba asegurado.
  Los miembros sin firmar quedan `RELEASED` con `released_by: EXPIRY`.
- **Pasada la fecha, un acto del destinatario (abrir, commit, rechazo) se rechaza con el `ENVELOPE_NO_LONGER_LIVE`
  que ya existe.** No hay código nuevo para el destinatario: `ENVELOPE_EXPIRED` es solo de rutas del emisor.
  El sobre se cierra en torno a un minuto después de la fecha; hasta entonces la puerta ya no admite actos.

## Qué tiene que hacer el signer

1. **Snapshot OpenAPI de los fixtures**: quitar `EXPIRED` del enum de `status` del sobre. Ojo: el `EXPIRED` del
   **estado de sesión** propio del signer es **otro enum y se queda**.
2. **Nada que añadir en el clasificador de errores**: `ENVELOPE_NO_LONGER_LIVE` ya está cubierto para abrir,
   commit y rechazo. Comprobad que un sobre caducado cae en la misma pantalla de "este sobre ya no está vigente"
   y no en un error genérico, y que no se muestra como firmado (`SESSION_CLOSED` / `ENVELOPE_NO_LONGER_LIVE` no
   son un éxito tardío).
3. Si el signer ramifica alguna vez por `status === 'EXPIRED'` del sobre, sustituirlo por `outcome` / `end_cause`.
   `COMPLETED` solo no significa acordado.

Un enlace de firma dura siete días desde su invitación aunque el sobre viva más: un enlace caducado sigue
necesitando un reenvío del emisor, y eso no ha cambiado.
