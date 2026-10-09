# Traspaso al signer (PROVISIONAL): `envelope_outcome` en `/auth` y nuevo significado de `outcome`

| | |
|---|---|
| **Origen** | TASK-050, etapa E |
| **Medido en** | `f5sign-backend` rama `feat/step-policy` @ `480faab9` + `21dc9a4a` (2026-09-29). Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | signer. Nadie más se ve afectado |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` |

## Qué cambió (commiteado)

1. **`GET /api/v1/signing/session/auth` (200) gana `envelope_outcome`**: string enum `AGREED | NOT_AGREED`,
   nullable, la clave siempre está presente. Es `null` mientras el sobre no se ha cerrado (también cuando el acuerdo
   ya está asegurado pero el sobre sigue abierto); desde el cierre lleva valor.
2. **`outcome`** (mismo enum `COMPLETED | DECLINED | REVOKED | RELEASED`, nullable) ahora nombra lo que le pasó a
   **esta participación**. Una sesión revocada porque el sobre se cerró responde con el nombre que el sobre da a la
   participación cerrada (`RELEASED` o `DECLINED`), no `REVOKED`. `REVOKED` ya no significa "el sobre terminó sin
   acuerdo": hoy nada alcanzable lo emite en `/auth` (solo casos teóricos). En `POST /signing/session`, `status`
   muestra `REVOKED` solo para filas de sesión revocadas antes de este cambio; `GET /signing/session` nunca.
3. **Sesiones**: al liberar a un miembro se revoca su sesión de forma asíncrona, **salvo** que su puerta siga
   pasando (informativos `VIEWER`/`REVIEWER`/`EDITOR`), que la conserva. Con una anulación del remitente, los
   informativos también conservan la sesión.

### Cómo distinguir las tres situaciones solo con `/auth`

| `outcome` | `envelope_outcome` | Situación |
|---|---|---|
| `null` | fijado | miembro informativo: mostrar la copia sellada |
| `RELEASED` | fijado | participación terminada, nada que leer |
| `COMPLETED` | fijado | ya firmaste |

La ruta de apertura coincide: `AUTH_PASSED` / 409 `ENVELOPE_NO_LONGER_LIVE` / `COMPLETED`.

### Tabla fijada por el test de Acceptance del backend

Enlace nuevo tras `COMPLETED`, con copia sellada. Columnas: `/auth` `outcome`, `/auth` `envelope_outcome`,
`POST /signing/session` `status`, `GET /signing/session` `status`, `GET /signing/session/documents/{id}`.

**AGREED** (un paso `ALL`):

| Miembro | `outcome` | `envelope_outcome` | POST `status` | GET `status` | documento |
|---|---|---|---|---|---|
| SIGNER que firmó | `COMPLETED` | `AGREED` | `COMPLETED` | `COMPLETED` | sellado |
| VIEWER, REVIEWER, EDITOR (paso activado) | `null` | `AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |

**NOT_AGREED** (el remitente anula tras la primera firma; el paso 2 nunca se activó):

| Miembro | `outcome` | `envelope_outcome` | POST `status` | GET `status` | documento |
|---|---|---|---|---|---|
| SIGNER que firmó | `COMPLETED` | `NOT_AGREED` | `COMPLETED` | `COMPLETED` | sellado |
| SIGNER liberado en silencio (había abierto) | `RELEASED` | `NOT_AGREED` | 409 `ENVELOPE_NO_LONGER_LIVE` | 409 `ENVELOPE_NO_LONGER_LIVE` | 404 `NOT_FOUND` |
| VIEWER/REVIEWER/EDITOR, paso activado | `null` | `NOT_AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |
| VIEWER/REVIEWER/EDITOR, paso nunca activado | `null` | `NOT_AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |
| VIEWER que abrió antes de la anulación | `null` | `NOT_AGREED` | `AUTH_PASSED` | `AUTH_PASSED` | sellado |

Nota: tras un cierre `NOT_AGREED` los informativos no reciben aviso, así que ningún enlace real les llega (la fila
de "paso nunca activado" existe en el backend pero no es alcanzable por correo).

Mientras el sobre está abierto, `/auth` responde `outcome: null` y `envelope_outcome: null` a un miembro pendiente.

Filas no fijadas porque aún no pueden ocurrir (necesitan cierre inmediato o relojes): `AGREED` con un firmante
liberado en silencio, y `AGREED` con un paso nunca activado. A nivel de controlador el backend sí fija que una sesión
revocada en un sobre `AGREED` responde `RELEASED` + `AGREED`.

## Qué tiene que hacer el signer

1. **Enrutar por `outcome` y `envelope_outcome` a la vez**:
   - `outcome` `null` con `envelope_outcome` fijado: vista de lectura de la copia sellada (ni "tu participación ha
     terminado" ni la pantalla `/done` de "ya habías firmado").
   - `RELEASED`: participación terminada; el texto ya puede decir si el documento siguió adelante
     (`envelope_outcome` `AGREED`: "el documento se completó"; `NOT_AGREED`: "no siguió adelante").
   - `COMPLETED`: como hasta ahora.
2. **Dejar de tratar `REVOKED` como "el remitente canceló"**; mantener una rama `default` segura para él.
3. **Añadir `envelope_outcome` (nullable) a los tipos de la respuesta de `/auth`.**

## Pendiente (no actuar todavía)

- El texto del 409 `ENVELOPE_NO_LONGER_LIVE` de `POST /signing/session` sigue diciendo que se muestre "este
  documento fue cancelado". Cuando existan el cierre inmediato y los relojes, un miembro liberado de un sobre `AGREED`
  podrá recibirlo: para redactar esa pantalla, apoyarse en `/auth` y no solo en el 409.
