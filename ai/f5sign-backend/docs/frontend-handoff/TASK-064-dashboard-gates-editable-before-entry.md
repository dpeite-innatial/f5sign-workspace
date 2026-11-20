# Traspaso al dashboard y al firmante — las puertas de un destinatario se pueden cambiar hasta que abre su enlace

| | |
|---|---|
| **Origen** | rama `feat/gates-editable-before-entry`, **sin mergear** · [TASK-064](../tasks/TASK-064-the-gates-are-editable-until-the-recipient-enters.md) · [ADR-0083](../adr/ADR-0083-a-recipients-gates-are-editable-until-they-enter.md) |
| **Fecha** | 2026-10-20 |
| **Repos afectados** | **dashboard** (ruta nueva) · **signer** (un 409 y un 503 nuevos al abrir la sesión) · integradores de los gemelos de máquina |
| **Naturaleza** | **aditivo**: una ruta nueva; tres rutas existentes responden un `code` y un estado nuevos |
| **Acción requerida** | dashboard: ninguna obligatoria, la ruta es opcional · signer: **sí**, tratar el 409 `AUTH_REQUIREMENT_CHANGED` y el 503 al abrir la sesión |
| **Desplegado** | not yet |
| **Status** | Pending |

La forma exacta de cada cuerpo está en el `doc.json` de la ruta; aquí va lo que cambió y qué hacer.

## Lo que cambió en el contrato (dashboard)

`PUT /api/v1/envelopes/{id}/recipients/{recipientId}/auth`, con clave de máquina. Sustituye **las dos puertas** de un
destinatario, enteras, con las mismas comprobaciones que al añadirlo. Se puede **hasta que el destinatario abre su enlace
por primera vez**, sea cual sea su rol; desde ese momento sus puertas quedan fijas. Vale en borrador y con el sobre ya
enviado.

- **Cuerpo**: `{"auth": {...}, "access_code": "..."}`. `auth` es el mismo objeto que en añadir destinatario y es
  obligatorio, con la puerta de acceso siempre declarada (`DIRECT_LINK` para que baste el enlace). `access_code` es
  opcional.
- **`selection`** queda fijada al añadir el destinatario: se envía solo con su valor actual, o se omite (omitirlo la
  deja como está).
- **Código de acceso**: si esta llamada *introduce* `ACCESS_CODE` en alguna puerta, se guarda el `access_code` enviado
  o el servidor genera uno y lo devuelve **una sola vez** en la respuesta. Si el destinatario ya declaraba
  `ACCESS_CODE`, no se toca y no se devuelve nada; para cambiarlo sigue estando
  `POST /api/v1/envelopes/{id}/recipients/{recipientId}/access-code`. Si lo quita de las dos puertas, el código se
  descarta.
- **Respuesta 200**: `warnings` (como en añadir destinatario) y `access_code` solo cuando esta llamada lo generó.
  Un cuerpo igual a lo guardado también responde 200 y no registra nada.
- El enlace ya enviado sigue valiendo y **no se avisa a nadie**. El cambio queda en el registro de auditoría.
- En un slot reclamable aún sin reclamar, las comprobaciones de contacto esperan a la reclamación, que las ejecuta con
  las puertas vigentes entonces. Esto es lo que saca de su atasco a un slot que declaró `[OTP_EMAIL, OTP_SMS]` y cuyo
  reclamante solo tiene email: se cambia a `[OTP_EMAIL]` y después se reclama.

### Respuestas de error y qué hacer

**409** (no se escribe nada):

| `code` | Significa | Qué hacer |
|---|---|---|
| `CONFLICT` | el sobre está cerrado | nada |
| `ENVELOPE_EXPIRED` | enviado y pasado su `expires_at` | no reintentar |
| `RECIPIENT_ALREADY_ENTERED` | el destinatario ya abrió su enlace; sus puertas son fijas | nada; deshabilitar la edición |
| `RECIPIENT_LEG_CLOSED` | su participación terminó, o venció el plazo de su paso | nada |
| `RECIPIENT_HAS_NO_GATES` | firma a través de un integrador (`signs_via: MACHINE_KEY`) y no tiene puertas | no ofrecer la edición |
| `AUTH_REQUIREMENT_CHANGED` | sus puertas cambiaron mientras la llamada estaba en curso | volver a leer el sobre y repetir si sigue haciendo falta |

**422**:

| `code` | Significa | Qué hacer |
|---|---|---|
| `VALIDATION_ERROR` | las reglas de campo de `auth` y `access_code` de añadir destinatario, con `errors[]` (entre ellas: falta `auth`, o la puerta de acceso sin declarar, en `auth.access_methods`) | marcar el campo |
| `AUTH_SELECTION_FROZEN` | `selection` distinta del modo con que se añadió | enviar el modo actual u omitirlo |
| `ACCESS_CODE_ALREADY_DECLARED` | `access_code` enviado cuando ya declaraba `ACCESS_CODE` | usar la ruta `access-code` |
| `AUTH_METHOD_UNAVAILABLE` | un método no está disponible en este despliegue | quitarlo |
| `RECIPIENT_CANNOT_RECEIVE_METHOD` | un método, en cualquier puerta y posición, no tiene adónde ir con el contacto del destinatario | quitarlo, o corregir antes el contacto |
| `PHONE_COUNTRY_NOT_SUPPORTED` | el móvil que pide `OTP_SMS` es de un país al que no se envían SMS | quitar `OTP_SMS` |

Además: **400** (cuerpo que no es JSON válido), **401** (clave de máquina ausente o inválida), **404** (sobre o destinatario que no existe para este cliente) y **503** `ENVELOPE_BUSY` (otra escritura tenía
el sobre bloqueado: repetir tras `Retry-After`).

## Lo que cambió para integradores (gemelos de máquina)

`POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth/otp/send` y
`POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth` registran ahora la apertura del destinatario **antes** de
abrir su sesión. Dos respuestas nuevas:

- **409 `AUTH_REQUIREMENT_CHANGED`**: el remitente cambió las puertas mientras la llamada estaba en curso; no se abrió
  ni se envió nada. Repetir la misma llamada.
- **503 `ENVELOPE_BUSY`**: la fila del destinatario estaba bloqueada (por ejemplo, por un cambio de sus puertas).
  Repetir tras `Retry-After`.

Y un efecto: la primera llamada de máquina cierra la ventana de edición de ese destinatario, aunque luego acabe en 429
o en "sin destino".

## Para el firmante

`POST /api/v1/signing/session` (abrir la sesión) responde dos cosas que antes no:

- **409 `AUTH_REQUIREMENT_CHANGED`** (el 409 distingue ahora **cinco** condiciones): el remitente cambió las puertas
  del destinatario mientras la llamada estaba en curso. No se abrió ni se emitió nada: **repetir la misma llamada**,
  que se responde con las puertas nuevas. No es un error que mostrar al firmante.
- **503 `ENVELOPE_BUSY`**: la fila del destinatario estaba bloqueada. Repetir tras `Retry-After`.

## Lo que NO existirá, y por qué

- **Editar las puertas después de que el destinatario abra su enlace.** Exigiría retirar retos vivos, credenciales y
  admisiones emitidos con las puertas anteriores, y ninguno de esos mecanismos existe; hacerlo mal deja firmar con la
  puerta vieja ([ADR-0083](../adr/ADR-0083-a-recipients-gates-are-editable-until-they-enter.md) §2.10, §7.1).
- **Cambiar `selection`**: el modo se fija al añadir el destinatario (ADR-0054 §2.4).
- **Avisar al remitente o al destinatario de un cambio**, o reinvitar por un cambio: no está decidido; hoy el registro
  de auditoría es lo único que deja constancia de él.

## Cómo verificarlo desde el frontal

Añadir un destinatario con `"auth": {"access_method": "DIRECT_LINK"}`, enviar `PUT …/auth` con
`{"auth": {"access_methods": ["OTP_EMAIL"]}}` → 200, y `GET /api/v1/envelopes/{id}` muestra la nueva puerta. Abrir su
enlace y repetir el `PUT` → 409 `RECIPIENT_ALREADY_ENTERED`.
