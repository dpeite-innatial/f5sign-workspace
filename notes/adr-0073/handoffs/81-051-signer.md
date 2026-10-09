# Traspaso al signer (PROVISIONAL), addendum al 80: tras unir TASK-051 con el paquete ADR-0073

| | |
|---|---|
| **Origen** | TASK-051 (ADR-0074 §2.5: *un plazo vencido y aún no barrido responde como lo dejará el barrido*), arreglos posteriores a unirlo con el paquete ADR-0073 |
| **Medido en** | `f5sign-backend` rama `feat/envelope-answers-first` @ `a50fb502` (worktree `f5sign-backend-answer-order`), 2026-09-29. Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | signer (`f5sign-signer`). Integradores: las rutas máquina gemelas cambian igual (`…/recipients/{recipientId}/auth/otp/send` y `…/auth`) |
| **Status** | **PROVISIONAL, accionable contra mocks.** Completa el 80; no lo sustituye. El traspaso oficial irá en `f5sign-backend/docs/frontend-handoff/` |

## Qué cambió (commiteado)

**Ningún código nuevo en el catálogo.** Cambia qué responde cada ruta en dos situaciones nuevas.

### 1. Un destinatario liberado que nunca abrió su enlace

Nunca abrió el enlace, así que no tiene sesión. Pide el código en `POST /api/v1/signing/session/auth/otp/send` (o en
su gemelo máquina).

| Antes (tras el paquete) | Ahora |
|---|---|
| 404 `NOT_FOUND` (no hay sesión) | **409 `LEG_CLOSED`**: se pregunta por la participación antes de buscar la sesión |

No se envía ni se cobra nada, y el gemelo máquina no abre sesión.

### 2. El intervalo entre el plazo de un paso y el barrido (hasta ~1 minuto)

Un firmante **bloqueante** no ha actuado y el plazo de su paso ya venció, pero el barrido programado aún no lo ha
aplicado. Todas las rutas del enlace responden **ya** lo que responderán tras el barrido: el mismo valor antes y
después.

| Ruta | El plazo termina el sobre | El sobre sigue sin este destinatario |
|---|---|---|
| `POST /api/v1/signing/session` (abrir) | 409 `ENVELOPE_NO_LONGER_LIVE`, sin credencial | 409 `LEG_CLOSED`, sin credencial |
| `POST …/auth/otp/send`, `POST /api/v1/signing/session/auth` (+ gemelos máquina) | 409 `ENVELOPE_NO_LONGER_LIVE` | 409 `LEG_CLOSED` |
| `GET /api/v1/signing/session/auth` (descriptor) | `outcome: RELEASED`, `envelope_outcome: NOT_AGREED` (el valor con el que cerrará) | `outcome: RELEASED`, `envelope_outcome: null` |

- Antes de este cambio, en ese minuto:
  - abrir **emitía credencial**;
  - las rutas de código respondían `LEG_CLOSED` también cuando el plazo termina el sobre;
  - el descriptor publicaba `outcome: REVOKED`.

  Las tres cosas quedan corregidas.
- **Quien ya firmó y los miembros informativos** (visor, etc.) siguen entrando con normalidad en ese intervalo.
- Ninguna de estas respuestas se levanta sola: **no reintentéis**.

## Qué tiene que hacer el signer

1. **`LEG_CLOSED` en la petición de código** (situación 1): tratadlo igual que ya tratáis `LEG_CLOSED` en la apertura,
   con la pantalla de participación cerrada del traspaso 51 (`legReleasedSubtitle` por `envelope_outcome`). Antes
   llegaba un 404, que quizá mandabais a "enlace no válido".
2. **Descriptor con `outcome: RELEASED` y `envelope_outcome` no nulo mientras el sobre aún no figura cerrado**: es
   válido y es definitivo. Mostrad el texto de "tu parte terminó" según `envelope_outcome`, igual que tras el
   barrido. Ya no aparece `REVOKED` en ese intervalo.
3. **`envelope_outcome: null` con `outcome: RELEASED`**: el sobre sigue en curso sin este destinatario. Es el tercer
   texto que ya os señalé en el 51 ("tu parte terminó; el documento sigue su curso").
4. Nada que cambiar para firmantes que ya firmaron ni para informativos.

## Qué no cambia

Todo lo del 80 sigue vigente. Fuera del intervalo de ~1 minuto, las respuestas son las de siempre.
