# Traspaso al frontal — el sobre devuelve los valores de campo, y enviarlo rechaza campos que nadie puede responder

| | |
|---|---|
| **Origen** | Rama `feat/field-values-at-commit`: `50c44ac` (la lectura: `value`, `filled_at`, `signed_at` solo en firmas) · `ce284c4` (las guardas de `send()`) · `4f7231e` (el tipo `RESERVATIONS`, [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md)), sobre `061e293`, `6f106d8` y `0bae290`, más el merge de `origin/develop` en `b51b1bd`. El spec OpenAPI y estos registros van en **el commit de aterrizaje en `develop`: `<landing sha>`** ⚠ *pendiente de rellenar*. Sin PR. Diseño en [TASK-044](../tasks/TASK-044-field-values-recorded-at-the-commit.md) §3 #7, #8 y #11. |
| **Fecha** | 2026-09-21 |
| **Repos afectados** | dashboard (`f5sign-dashboard`). El signer y el integrador de Factor5 tienen sus propios traspasos: [signer](TASK-044-signer-field-values-and-reservations.md) y [dashboard-sf](TASK-044-dashboard-sf-field-values-and-reservations.md). |
| **Naturaleza** | Aditivo en el esquema de `GET /api/v1/envelopes/{id}`, con un cambio de significado: `fields[].signed_at` pasa a publicarse solo en firmas. Y **cambia comportamiento** al enviar: `POST /api/v1/envelopes/{id}/send` rechaza tres formas de sobre que hasta ahora aceptaba. |
| **Acción requerida** | Ninguna hoy, porque el dashboard no llama al backend. Al construir la vista del sobre y el editor de campos, codificad contra esto. |
| **Desplegado** | No. Ni siquiera mergeado en `develop` al escribir esto: el `<landing sha>` de arriba es el que lo dirá. |
| **Status** | Pending |

**Impacto medido hoy: ninguno.** En `f5sign-dashboard`, `master` `dafcc2d` (igual a `origin/master`) y la rama
`feat/ssr-false-spa-static` `f9c7abe`, el 2026-09-21: cero apariciones de `useFetch`, `$fetch` o `/api/v1` en el
código versionado, y ningún tipo de sobre ni de campo. Por eso este traspaso no os pide nada ahora; os dice cómo leer
el sobre cuando lo construyáis.

**Lo que no os toca.** El despliegue conjunto de TASK-044 es de backend, signer e integrador (TASK-044 §4 D13); el
dashboard no entra en él porque no consume nada todavía. Y ninguna petición del registro de auditoría (Audit Trail)
va dirigida a vosotros: esas van al signer y al integrador, en sus traspasos.

## Lo que cambió en el contrato

La forma normativa está en el `doc.json` del despliegue que os sirve, una vez desplegado: los esquemas `Field` y
`FieldOptions`. Aquí va qué cambia y cómo leerlo.

### 1. `GET /api/v1/envelopes/{id}`: cada campo trae su valor

- **`fields[].value`**, nuevo: lo que respondió el destinatario, registrado una vez, en su commit.
  - Texto en `TEXT` (tal cual lo escribió, sin recortar), `DATE` (`YYYY-MM-DD`), `DROPDOWN` y `RADIO` (el `value` de
    la opción elegida).
  - Booleano en `CHECKBOX`.
  - Siempre `null` en los demás tipos: `SIGNATURE`, `INITIALS`, `ATTACHMENT`, `PAYMENT`, `KYC`, `EUDI_WALLET` y
    `RESERVATIONS`.
- **`fields[].filled_at`**, nuevo: el instante del commit que registró el campo, solo en esos cinco tipos de datos.
  Siempre `null` en los demás.
- **Leed los dos juntos**, porque `value: null` solo no distingue tres casos:

| `filled_at` | `value` | Qué significa |
|---|---|---|
| `null` | `null` | Nada registrado: el destinatario no ha firmado, o firmó con un cliente que no le mostró el formulario |
| fecha | `null` | Lo vio y lo dejó en blanco |
| fecha | valor | Respondido. Una casilla que vio y no marcó es `false` |

- **Solo rellenan `SIGNER` y `APPROVER`.** Un campo de datos de otro rol se queda sin registrar; un sobre nuevo ni
  siquiera se puede enviar así (apartado 4).
- **No cambia después del commit.** Un valor registrado no se reescribe.

### 2. `fields[].signed_at` se estrecha a las firmas

- **Antes:** se publicaba en todos los campos, y era `null` en todos.
- **Ahora:** solo significa algo en un campo `SIGNATURE`, donde es el instante de la firma de esa marca. En los demás
  tipos es siempre `null`.
- **Hoy es `null` también en las firmas**, porque nada lo escribe todavía.
- **No leáis "firmado" en un campo de datos**: su instante es `filled_at`. Por eso el backend no publica la misma
  columna dos veces.

### 3. Un tipo de campo nuevo: `RESERVATIONS`

- **`fields[].type`** gana `RESERVATIONS`. El tipo dice **dónde** se dibujan las reservas de un destinatario
  (ADR-0069); no guarda nada.
- **`value` y `filled_at` son siempre `null`.** El texto de las reservas está en `recipients[].reservations` de su
  destinatario, y `has_reservations` dice si alguien escribió reservas en el sobre.
- **`required`** es siempre `false` y **`options.choices`** siempre `null`.
- **`options.validation`** es `null`, o trae solo `max_length`: el límite, en caracteres, de las reservas de ese
  destinatario.

### 4. `POST /api/v1/envelopes/{id}/send` rechaza tres casos nuevos

Cada uno es un 422 con `code: UNPROCESSABLE_ENTITY`, el mismo que los demás requisitos previos al envío (sin
documentos, sin pasos…), y un `detail` que empieza por *"Pre-send invariant violated: field `<id>` …"* y nombra el
campo. Uno por envío: el primero que encuentra.

1. **Un campo de datos asignado a un rol que no rellena.** Cualquier `TEXT`, `DATE`, `CHECKBOX`, `DROPDOWN` o
   `RADIO`, obligatorio o no, cuyo destinatario no sea `SIGNER` ni `APPROVER`. Su commit lo rechazaría, así que el
   campo solo podría quedarse vacío.
2. **Un campo obligatorio que nada puede responder todavía:** `INITIALS`, `ATTACHMENT`, `PAYMENT`, `KYC` o
   `EUDI_WALLET` con `required: true`.
3. **Un campo de datos obligatorio que nadie alcanza:** sin destinatario, o sin ningún rectángulo en un documento que
   su destinatario pueda leer. Uno alcanzable solo en parte es válido: se publica recortado.

⛔ **Prevenidlos en el editor, no esperéis al envío.** Hoy no hay ninguna ruta para quitar ni editar un campo: en
`config/routes/api/envelope.php` no hay `DELETE`, `PUT` ni `PATCH`, y `POST …/void` rechaza un borrador. Así que un
borrador con el caso 1 o el 2 **no se puede enviar ni arreglar**: hay que rehacer el sobre. El caso 3 tampoco, si al
campo le falta el destinatario, porque no se le puede asignar después. Si lo tiene, solo hay arreglo cuando todavía se
puede declarar su acceso a un documento donde el campo tiene un rectángulo: esas declaraciones son *append-only*, y
volver a declarar un par con otros permisos da 409.

### 5. `POST /api/v1/envelopes/{id}/fields` admite `RESERVATIONS`, con seis rechazos

Cada uno es un 422 que no crea nada, con `code: UNPROCESSABLE_ENTITY` y el motivo en `detail`. Lo que dice cada
`detail`, en sustancia:

- **sin destinatario:** un campo `RESERVATIONS` coloca las reservas de un destinatario; asignadlo a él. Así que el
  destinatario tiene que existir antes que el campo;
- **destinatario con un rol que no rellena:** ese rol no firma formulario, así que no tiene reservas que colocar;
- **`required: true`:** las reservas nunca son obligatorias;
- **con `choices`:** solo `DROPDOWN` y `RADIO` llevan opciones;
- **con un `pattern`, un `pattern_message` o un `date_format`:** este tipo solo admite `max_length`;
- **un segundo campo para el mismo destinatario:** ya tiene uno; para otra posición, añadid una ocurrencia a ese
  mismo campo.

## Lo que el dashboard tiene que hacer

Nada hoy. Cuando construyáis la vista del sobre y el editor de campos:

1. **Mostrad las respuestas con `value` y `filled_at` juntos** (apartado 1). No uséis `signed_at` en un campo de
   datos.
2. **Las reservas se leen del destinatario**, en `recipients[].reservations`, nunca del campo `RESERVATIONS`.
3. **Añadid `RESERVATIONS` al tipo de campo**, y en el editor, sus reglas: un destinatario `SIGNER` o `APPROVER` ya
   creado, nunca obligatorio, sin opciones, solo `max_length`, uno por destinatario (apartado 5).
4. **Impedid en el editor los tres casos del apartado 4.** Un campo de datos solo para `SIGNER` o `APPROVER`; los
   tipos `INITIALS`, `ATTACHMENT`, `PAYMENT`, `KYC` y `EUDI_WALLET` nunca obligatorios; y un campo de datos
   obligatorio, siempre con destinatario y con algún rectángulo en un documento que ese destinatario pueda leer.
5. **Mostrad el `detail` de un 422 del envío.** No hay un `code` propio para cada caso (apartado siguiente), y el
   `detail` es lo único que nombra el campo.

## Lo que NO está listo todavía

- **Un `code` por cada rechazo del envío.** Los tres nuevos comparten `UNPROCESSABLE_ENTITY` con los demás requisitos
  previos al envío, y solo el `detail`, que no es contractual, los distingue. No es una decisión: hoy simplemente no
  existe.
- *(Hecho por TASK-067, ver su traspaso.)* **Dibujar los valores y las reservas en el PDF** (BL-269). Se registran y se publican, pero la copia firmada no los
  lleva todavía.
- **Que `EDITOR` rellene campos** (BL-271). Hoy no rellena, y por eso un sobre con un campo de datos suyo no se
  puede enviar.
- **Lo que significa `recipients[].reservations: null`.** Hoy se publica como "firmó sin reservas" (TASK-016), y el
  trabajo del registro de auditoría lo va a convertir en "no consta", con un valor nuevo para "declaró no tener
  reservas". No es una petición para vosotros, pero no construyáis sobre el significado antiguo. Llegará en su
  propio traspaso.

## Lo que NO existirá, y por qué

- **Un valor propio en un campo `RESERVATIONS`.** Las reservas tienen un solo canal, el `reservations` del commit,
  que es el que guarda el registro permanente y el que lee el registro de auditoría. Si el texto viviera también en
  el campo, un sobre podría tener una reserva escrita y un registro que dice "no consta". El campo solo dice dónde se
  dibuja (ADR-0069).
- **`signed_at` en un campo de datos.** En un cuadro de texto nadie firma: responde. Publicar el instante del commit
  como `signed_at` pondría "firmado" en un cuadro de texto, así que va en `filled_at`, y `signed_at` queda para las
  firmas.

## Cómo verificarlo desde el frontal

- **En el `doc.json` del despliegue que os sirve:** el esquema `Field` tiene `value` y `filled_at`, la descripción de
  `signed_at` dice que es solo de `SIGNATURE`, y `Field.type` incluye `RESERVATIONS`. Si no, ese despliegue no lleva
  TASK-044.
- **Lectura:** en un sobre con un `TEXT` y una casilla, después de que el destinatario firme con un signer que ya
  envíe `filled_fields`, `GET /api/v1/envelopes/{id}` trae en cada campo su `value` y un `filled_at`, y
  `signed_at: null`.
- **Envío:** un borrador con un `TEXT` asignado a un `REVIEWER` responde 422 a `POST …/send`, con un `detail` que
  nombra el campo. No lo hagáis con un sobre que queráis conservar: ese borrador ya no se puede arreglar.
- **Autoría:** `POST …/fields` con `type: "RESERVATIONS"` y `required: true` responde 422 y no crea el campo.

> ⛔ **Seguridad:** `value` y `recipients[].reservations` son texto que escribió un destinatario. Renderizadlo siempre como texto, nunca como HTML.
