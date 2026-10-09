# Traspaso al signer (PROVISIONAL): `envelope_outcome` en el read model `GET /signing/session`

| | |
|---|---|
| **Origen** | TASK-050, etapa E. Decisión del mantenedor sobre la pregunta Q-E1 del signer |
| **Medido en** | `f5sign-backend` rama `feat/step-policy` @ `901fd813` (2026-09-29). Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | signer. Nadie más se ve afectado |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` |

## Qué cambió (commiteado)

1. **`GET /api/v1/signing/session` (200, el read model) gana `envelope_outcome`** al nivel superior, justo después de
   `status`: string enum `AGREED | NOT_AGREED`, nullable, la clave siempre está presente (va en `required`). Es `null`
   hasta que el sobre se cierra (también cuando el acuerdo ya está asegurado pero el sobre sigue abierto).
2. Es **exactamente el mismo valor** que el `envelope_outcome` de `/auth`: una única regla compartida en el backend,
   sin un segundo cálculo.
3. Orden de claves del 200: `session_id`, `status`, `envelope_outcome`, `envelope`, `documents`, `fields`,
   `auth_requirements`, `auth_status`, `signer`, `config`, `branding`, `fields_draft`.

### Tabla fijada por el test de Acceptance del backend

Es la tabla del traspaso 33 con una columna nueva: `GET /signing/session` `envelope_outcome`.

- Toda fila de miembro informativo (VIEWER/REVIEWER/EDITOR, con el paso activado o no, `AGREED` o `NOT_AGREED`) lee
  `{status: AUTH_PASSED, envelope_outcome: AGREED | NOT_AGREED}`.
- Un SIGNER que firmó lee `{status: COMPLETED, envelope_outcome: AGREED | NOT_AGREED}`.
- El SIGNER liberado en silencio sigue recibiendo 409 `ENVELOPE_NO_LONGER_LIVE`.
- Mientras el sobre está abierto, el read model muestra `{status: AUTH_PASSED, envelope_outcome: null}`.

## Qué tiene que hacer el signer

1. En el middleware que va de `AUTH_PASSED` a `getSession` a `/view`:
   - `status` `AUTH_PASSED` con `envelope_outcome != null`: enrutar a la vista de la copia sellada (`/copy`).
   - `envelope_outcome == null`: la ceremonia, como hasta ahora.
2. **Añadir `envelope_outcome` (nullable) al tipo de la respuesta de `GET /signing/session`.**
3. `/auth` ya no hace falta para esta decisión.
