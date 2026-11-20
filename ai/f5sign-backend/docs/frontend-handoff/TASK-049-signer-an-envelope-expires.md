# Traspaso al signer — el `status` del sobre pierde `EXPIRED`; el signer no necesita cambiar código

| | |
|---|---|
| **Origen** | rama `feat/task-048-how-an-envelope-ends` (paquete [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)) · TASK-049 cerrada en `67626bce` · sin mergear en `develop` |
| **Fecha** | 2026-09-29 |
| **Repos afectados** | signer (`f5sign-signer`). El resto del contrato de caducidad (`expires_in_days`, `expiry-extensions`) es del integrador: [TASK-049-integrator-an-envelope-expires.md](TASK-049-integrator-an-envelope-expires.md) |
| **Naturaleza** | corrige el spec publicado: `EnvelopeStatus` pierde `EXPIRED` |
| **Acción requerida** | regenerar el snapshot OpenAPI desde `develop` cuando el paquete aterrice; ningún cambio de código |
| **Desplegado** | no — sin mergear en `develop` |
| **Status** | Pending. El signer informó (2026-09-29, sin que yo vea su árbol) de que no necesita cambio de código; lo único pendiente es el snapshot |

## Lo que cambió en el contrato

- **`EnvelopeStatus` ya no tiene `EXPIRED`.** Un sobre caducado se lee `status: COMPLETED`, `outcome: NOT_AGREED`,
  `end_cause: EXPIRED` (sin actor), o `outcome: AGREED` si su acuerdo ya estaba asegurado. Los miembros sin firmar
  quedan `RELEASED` con `released_by: EXPIRY`.
- **Pasada la fecha, un acto del destinatario (abrir, commit, rechazo) se rechaza con el `ENVELOPE_NO_LONGER_LIVE`
  que ya existe.** No hay código nuevo para el destinatario: `ENVELOPE_EXPIRED` es solo de rutas del emisor. El
  sobre se cierra en torno a un minuto después de la fecha; hasta entonces la puerta ya no admite actos.

## Lo que el frontal tiene que hacer

1. **Regenerar el snapshot OpenAPI de los fixtures desde `develop`** cuando el paquete aterrice: el enum de
   `status` del sobre pierde `EXPIRED`. Ojo: el `EXPIRED` del **estado de sesión** propio del signer es otro enum
   y se queda.
2. **Nada más.** El signer informa de que nunca lee el `status` del sobre y de que `ENVELOPE_NO_LONGER_LIVE` ya
   aterriza en su pantalla «ya está cerrado» (abrir, commit y rechazo). No hay que tocar el clasificador de
   errores ni ramas por `status === 'EXPIRED'`.

Un enlace de firma dura siete días desde su invitación aunque el sobre viva más: un enlace caducado sigue
necesitando un reenvío del emisor, y eso no ha cambiado.

## Lo que NO está listo todavía

- Nada del paquete está desplegado. Comprobad el `doc.json` de vuestro entorno antes de regenerar (regla 4).

## Cómo verificarlo desde el frontal

- Tras regenerar el snapshot, el enum de `status` del sobre no contiene `EXPIRED` y la suite del signer sigue verde.
- Un destinatario que abre su enlace con el sobre ya caducado ve la pantalla de sobre cerrado, no un error genérico
  ni un éxito tardío.
