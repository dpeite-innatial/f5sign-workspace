# Traspaso al frontal — los valores de campo llegan en el commit, y las reservas tienen un solo canal

| | |
|---|---|
| **Origen** | Rama `feat/field-values-at-commit`: `061e293` (una extensión del problema puede ser una lista, [ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md)) · `6f106d8` (las reglas de los valores) · `0bae290` (el commit lleva los valores a Envelope) · `50c44ac` (la lectura en las dos superficies) · `ce284c4` (las guardas de `send()`) · `4f7231e` (el tipo `RESERVATIONS`, [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md)) · merge de `origin/develop` en `b51b1bd`. El spec OpenAPI y estos registros van en **el commit de aterrizaje en `develop`: `<landing sha>`** ⚠ *pendiente de rellenar*. Sin PR. Diseño en [TASK-044](../tasks/TASK-044-field-values-recorded-at-the-commit.md). Las peticiones del registro de auditoría (Audit Trail), redactadas por otra sesión del backend, siguen sin commitear en ningún sitio. |
| **Fecha** | 2026-09-21 |
| **Repos afectados** | signer |
| **Naturaleza** | Aditivo en el esquema, y aun así **cambia comportamiento**: un commit con campos obligatorios sin rellenar pasa a ser rechazado. Y un tipo de campo nuevo, `RESERVATIONS`, que vuestro `FieldType` no conoce. |
| **Acción requerida** | Adoptar antes del despliegue conjunto (backend, signer e integrador salen juntos). |
| **Desplegado** | No. Ni siquiera mergeado en `develop` al escribir esto: el `<landing sha>` de arriba es el que lo dirá. |
| **Status** | Pending |

⛑ **2026-09-21**: la fila `Origen` decía *«Nada construido… A 2026-09-21 ni lo uno ni lo otro está commiteado»*. La
parte de TASK-044 está ya construida en la rama; lo del Audit Trail sigue igual. Este documento describe ahora lo
construido, no lo diseñado.

**Medido en:** `f5sign-signer` `develop` `18316cc` (2026-09-21; la versión anterior de este documento midió
`8ce01de`, que es antecesor, y lo citado abajo no ha cambiado entre los dos). El árbol de trabajo del signer tenía
cambios sin commitear en `sign.vue`, `click-sign.vue` y `SignAcceptance.vue` que **no hemos leído**. Y
`f5sign-backend` `feat/field-values-at-commit` `b51b1bd`, con los `#[OA]` del tramo final aún sin commitear. Las
peticiones del Audit Trail citaban el signer en `b36587f`, que este clon no contiene; donde este documento dice algo
distinto, es porque lo ha vuelto a medir.

Este documento sustituye a dos: la parte de valores de campo de TASK-044 y la petición del Audit Trail al signer
(`REQUESTS-SIGNER.md`). Se juntan porque hablaban de la misma caja y os pedían cosas contrarias.

## Resumen

1. **Los valores de los campos se envían en el commit**, en `filled_fields`. No hay ruta de borrador.
2. **Si un valor no vale, el commit responde 422 `FIELD_VALUES_INVALID`**, con `field_errors`: todos los campos a
   corregir, un código cada uno.
3. **Las reservas van solo por `reservations`.** Un campo nuevo de tipo `RESERVATIONS` os dice **dónde** pedirlas y
   cuánto pueden medir.
4. **`reservations` va a distinguir tres estados:** no se preguntó, se preguntó y no tiene, y hay texto.
5. **Todo sale en un único despliegue** de backend, signer e integrador.

## Lo que cambió en el contrato

La forma normativa está en el `doc.json` del despliegue que os sirve, una vez desplegado:
`components.schemas.FilledField`, `components.schemas.FieldValueError`, `SigningField` y el `ProblemCode`. Aquí va
qué cambia y cómo se comporta.

### 1. `filled_fields` en `POST /api/v1/signing/commit`

- **Forma:** `filled_fields: [{ "field_id": "<uuid>", "value": … }]`.
  - Cada entrada lleva **exactamente** `field_id` y `value`. Una clave de más o de menos se rechaza, no se ignora.
  - `field_id` es un UUID y aparece como mucho una vez (se comparan sin distinguir mayúsculas).
  - `value` es un texto, un booleano o `null`. **Un número se rechaza**, aunque vuestro `PatchValue` y el
    `CompleteRequest` de `types.ts` lo admitan: ningún tipo de campo guarda números.
  - Como mucho **512** entradas, y cada texto como mucho **40 000** caracteres.
  - Esto lo comprueba la petición antes de nada, y un fallo es un 422 **`VALIDATION_ERROR`** con `errors[]`, no con
    `field_errors`. Es un defecto del cliente.
- **Ausente no es lo mismo que vacío:**
  - **Si no enviáis el miembro, o lo enviáis `null`**, el backend entiende que este cliente no recogió campos. No
    escribe nada, ni siquiera un blanco. Pero sí rechaza el commit si hay campos obligatorios (`REQUIRED`).
  - **Si lo enviáis, aunque sea `[]`**, entiende que se mostró el formulario. Todo campo mostrado se registra: uno
    que no viene, o que viene `null` o `""`, queda en blanco; una casilla que no viene queda como no marcada
    (`false`).
- **Qué campos entran:** solo los cinco tipos rellenables (`TEXT`, `DATE`, `CHECKBOX`, `DROPDOWN`, `RADIO`), de
  campos que no sean de solo lectura, con ids de la lista `fields` de la sesión.
- **Quién lo envía:** solo un firmante con rol `SIGNER` o `APPROVER` (`signer.role` de la sesión). Para cualquier
  otro rol, cualquier entrada, aunque sea `null`, se rechaza con `UNKNOWN_FIELD`. `EDITOR` tampoco rellena todavía
  (BL-271).
- **Cómo se juzga cada valor**, con las reglas de vuestro `useFieldValidation.ts`:
  - **TEXT:** se cuenta en caracteres. El límite es `max_length`, o **32 767** si el campo no trae ninguno. No se
    recortan espacios, así que un valor de solo espacios cumple `required`. No admite caracteres de control, salvo
    tabulador, salto de línea y retorno de carro. El `pattern` se aplica como lo aplicáis vosotros, y se salta
    donde vosotros lo saltáis (patrón de más de 200 unidades UTF-16, valor de más de 4096, la heurística
    `NESTED_QUANTIFIER`, o un patrón que no compila). ⚠ Quedan diferencias de dialecto en las que el backend
    puede rechazar lo que vosotros aceptáis: sintaxis que solo PCRE entiende, conteos sobre caracteres fuera del
    BMP y `\s` frente a espacios Unicode (BL-272).
  - **DATE:** `YYYY-MM-DD`, y un día que exista.
  - **CHECKBOX:** un booleano. Si es obligatoria, solo vale `true`.
  - **DROPDOWN y RADIO:** el `value` de una de las opciones.
- **La respuesta de éxito no cambia:** 200 con `{ session_id, status }`. No hay eco de lo registrado.

### 2. El rechazo por campos: 422 `FIELD_VALUES_INVALID`

- **Qué trae:** un problema RFC 9457 (`application/problem+json`) con un miembro nuevo, `field_errors`:

  ```json
  {
    "type": "about:blank",
    "title": "Unprocessable Content",
    "status": 422,
    "code": "FIELD_VALUES_INVALID",
    "detail": "2 field values were refused; see field_errors.",
    "field_errors": [
      { "field_id": "0b6c2f4e-…", "code": "PATTERN_MISMATCH" },
      { "field_id": "7e21a9d0-…", "code": "REQUIRED" }
    ]
  }
  ```

  - **Todos** los campos con problema a la vez, **un código por campo**, ordenados por `field_id` (en minúsculas).
  - Cada registro trae **exactamente** `field_id` y `code`. Nunca el valor enviado.
  - `detail` no es contractual; no lo parseéis.
- **`field_errors` puede nombrar campos que no enviasteis:** un obligatorio que faltaba (`REQUIRED`), o el campo
  `RESERVATIONS` cuando las reservas son demasiado largas (`TOO_LONG`, apartado 3). Buscad cada `field_id` en la
  `fields` de la sesión, no en lo que enviasteis.
  - ⚠ **Un `field_id` que no está en vuestra `fields`, y que no enviasteis, solo puede ser un `TOO_LONG` de
    reservas.** Pasa cuando el firmante tiene un campo `RESERVATIONS` con `max_length` y ninguna de sus posiciones
    cae en un documento que puede leer: el campo no os llega, pero su límite se aplica igual. Ponedlo en la caja
    genérica de reservas.
- **Qué deja intacto:** un 422 no gasta el código de firma ni nada más. El firmante corrige y vuelve a firmar con el
  mismo código mientras no caduque.
- **Qué responde antes:** en esta ruta, cualquier otro rechazo del commit responde antes que los campos, con los
  códigos que ya manejáis: paso no activo (`STEP_NOT_ACTIVE`), sesión completada, sesión cerrada, sobre que ya no
  está vivo, y los de la puerta de firma. Un `FIELD_VALUES_INVALID` solo llega cuando todo lo demás estaba bien.
- **Los códigos** son los del enum `FieldValueError.code` del spec. Son términos por campo: nunca llegan como `code`
  de la respuesta. Si un campo falla por dos motivos, se informa el primero en este orden:

| Código | Qué significa | Clave de traducción que ya tenéis |
|---|---|---|
| `UNKNOWN_FIELD` | No es un campo que este firmante vea y responda. Otro firmante, un id inventado, una firma, un `RESERVATIONS`, un rol que no rellena: todos dan lo mismo | ninguna: defecto del cliente |
| `READONLY` | Campo de solo lectura (hoy ninguno lo es) | ninguna: defecto del cliente |
| `WRONG_TYPE` | Un booleano donde iba texto, o al revés | ninguna: defecto del cliente |
| `REQUIRED` | Obligatorio en blanco, o casilla obligatoria sin marcar | `validation.required`, o `validation.checkboxRequired` en una casilla |
| `TOO_LONG` | TEXT por encima de su `max_length` (32 767 si no trae); en un `RESERVATIONS`, las `reservations` por encima de su `max_length` | `validation.maxLength` |
| `CONTROL_CHARACTERS` | TEXT con un carácter de control que no es tabulador, salto de línea ni retorno de carro | **nueva** |
| `PATTERN_MISMATCH` | TEXT que no cumple su `pattern` | el `pattern_message` del campo, o `validation.pattern` |
| `INVALID_DATE` | DATE que no es un día real en `YYYY-MM-DD` | `validation.dateInvalid` |
| `NOT_A_CHOICE` | No es el `value` de ninguna opción | `validation.invalidChoice` |

### 3. El campo `RESERVATIONS` (nuevo tipo)

- **Qué es:** un tipo de campo nuevo que marca **dónde** van las reservas de ese firmante. No tiene valor propio y
  no se rellena por `filled_fields`: una entrada para él da `UNKNOWN_FIELD`.
- **Cómo os llega:** en `fields` de la sesión, con `type: "RESERVATIONS"` y sus posiciones en los documentos que el
  firmante puede leer.
  - `required` es siempre `false` y `options.choices` es siempre `null`.
  - `options.validation` es `null`, o trae solo `max_length`; los demás miembros vienen a `null`.
  - Como mucho hay uno por firmante, y solo lo tiene un `SIGNER` o un `APPROVER`: el backend rechaza cualquier otra
    cosa al crear el campo.
- **`max_length` es el límite de las reservas de ese firmante.** Unas `reservations` más largas se rechazan con 422
  `FIELD_VALUES_INVALID` y un `TOO_LONG` sobre el id de este campo, **también si el commit no trae
  `filled_fields`**. El backend cuenta caracteres. El techo propio del canal sigue siendo 2000: por encima de eso,
  el rechazo es `VALIDATION_ERROR`.
- **`current_value`:** las reservas que el firmante registró, sacadas de `recipients[].reservations`. Ese texto lo
  escribe el backend al procesar la firma, de forma asíncrona, así que justo después del 200 puede venir todavía
  `null`.
- **Qué sustituye:** en la carta de porte de Factor5, al campo `TEXT` "Reservas", que el integrador cambia de tipo
  en el mismo despliegue.

### 4. `reservations` con tres estados (trabajo del Audit Trail)

- **Qué pasa hoy:** `reservations` es texto o `null`, y el backend publica `null` como "firmó sin reservas"
  (TASK-016).
- **Qué va a cambiar:** `null` pasará a significar "no consta", y un valor nuevo dirá "se le preguntó y no tiene
  reservas". El nombre y la forma los fija el ADR de ese trabajo, que aún no existe. Os llegará en su propio
  traspaso.
- **Compatibilidad:** es aditivo, porque `{ consent: true, reservations: null }` sigue funcionando. Lo que cambia es
  el significado.

### 5. `GET /api/v1/signing/session`

- **`current_value`:** el valor que registró el commit. Texto en TEXT, DATE, DROPDOWN y RADIO; booleano en CHECKBOX.
  Es `null` antes del commit, `null` si se dejó en blanco, y siempre `null` en una marca de firma. En un
  `RESERVATIONS`, el texto de las reservas (apartado 3).
- **`fields[].type`:** gana `RESERVATIONS`.
- **`fields_draft`:** sigue en `null` (BL-40).

## Lo que el signer tiene que hacer

1. **Pedir las reservas en la pantalla que usa la imagen desplegada.**
   - **Por qué `/sign`:** la imagen se construye sin `NUXT_PUBLIC_SIGNING_MVP` (no aparece en
     `.github/workflows/build-image.yml`, y el `Dockerfile` lo deja en `false`). El middleware
     (`app/middleware/session.global.ts`) lleva entonces al firmante a `/sign`. `useSignFlow` cierra siempre con
     `{ consent: true, reservations: null }`. `click-sign` sí tiene la caja y la envía, pero la imagen desplegada
     nunca llega a esa pantalla.
   - **Dónde ponerla:** si el firmante tiene un campo `RESERVATIONS`, en sus posiciones; si no, en una caja genérica
     opcional, como la de `click-sign`.
   - **Quién puede hacer reservas:** el backend las acepta de cualquier firmante, porque el transportista las hace
     en la recogida y el destinatario en la entrega.
2. **Que "sin reservas" sea una respuesta explícita**, no una caja vacía. Modelad ya los tres estados, aunque hasta
   que exista el valor explícito solo podáis enviar dos: el texto si lo hay, y `null` en los demás casos.
3. **No enviéis `""` para decir "sin reservas".** En esta ruta el backend convierte un texto vacío o de solo espacios
   en `null` (`CommitSignatureController::normalizeReservations`).
4. **Añadid `RESERVATIONS` a vuestro `FieldType`** (`app/composables/api/types.ts`). Hoy no está, y
   `app/components/signer/InteractiveField.vue` no pinta nada para él: no tiene rama propia, y
   `UnsupportedFieldPlaceholder` solo cubre `ATTACHMENT`, `PAYMENT`, `KYC` y `EUDI_WALLET`. En sus posiciones va la
   caja de reservas, limitada por su `max_length`, y su texto va en `reservations`, nunca en `filled_fields`.
5. **Enviad `filled_fields`** en todo commit en el que el firmante haya visto un formulario, con las restricciones
   del apartado 1. Hoy `buildCommitRequest()` envía solo `consent` y `reservations`.
   - **Construid la lista con los cinco tipos, no quitando tipos.** `NON_DRAFT_TYPES` en
     `app/stores/useFieldsDraftStore.ts` excluye solo `SIGNATURE` e `INITIALS`: una lista hecha a partir de él
     metería un `RESERVATIONS`, y eso da `UNKNOWN_FIELD`.
   - **Solo si `signer.role` es `SIGNER` o `APPROVER`.** Con cualquier otro rol, omitid el miembro.
6. **Tratad el 422 `FIELD_VALUES_INVALID` antes de la rama genérica** de `mapError`. Hoy un 422 solo se enruta si es
   `AUTH_REQUIRED`, y lo demás cae en el fallo genérico, cuyo reintento reenvía el mismo cuerpo.
   - Localizad cada `field_id` en la `fields` de la sesión (apartado 2), incluido el campo `RESERVATIONS`, cuyo
     `TOO_LONG` va a la caja de reservas.
   - `REQUIRED`, `TOO_LONG`, `CONTROL_CHARACTERS`, `PATTERN_MISMATCH`, `INVALID_DATE` y `NOT_A_CHOICE`: poned cada
     código en su campo con su clave de traducción, mostrad los errores y volved al formulario, sin mandar el
     evento a Sentry. El firmante vuelve a firmar con el mismo código.
   - `UNKNOWN_FIELD`, `READONLY` y `WRONG_TYPE`: reportad y mostrad el fallo.
   - Un 422 `VALIDATION_ERROR` sobre `filled_fields` (con `errors[]`) también es un defecto vuestro.
7. **Dos reglas nuevas en el cliente:**
   - **caracteres de control:** el texto pegado puede traerlos, y el backend los rechaza. Hace falta una clave de
     traducción nueva para `CONTROL_CHARACTERS`, y otra para el aviso a nivel de página;
   - **límite de longitud por defecto:** cuando un TEXT no trae `max_length`, aplicad 32 767, que es lo que publica
     `FieldValueError` en su descripción de `TOO_LONG`. Vosotros contáis unidades UTF-16 y el backend cuenta
     caracteres, así que nunca seréis más permisivos que él;
   - **`isPatternSafe` no detecta `((a+))+`** (BL-50, primera vía, sigue abierta): su `[^()]*` no atraviesa el grupo
     interior, así que ese patrón pasa la heurística y cuelga el dispositivo en `.test()`. El backend lo corta con su
     límite de backtracking y se salta la regla, pero en vuestro lado no hay límite: hace falta que la heurística
     cubra grupos anidados, o un matcher acotado.
8. **El borrador se queda en local** (BL-40). En `18316cc` ya es así: `hasDraftEndpoint()` deja los valores en memoria
   y el indicador en reposo. No volváis a llamar a `PATCH /signing/session/fields` contra el backend real. Lo que
   cambia es el motivo: los valores definitivos ya viajan en el commit, así que esa ruta, si llega, será solo
   borrador.
9. **Retirad los comentarios que dejarán de ser verdad:**
   - en `app/composables/useFieldValidation.ts`, la justificación del salto del patrón en `isPatternSafe`: dice que el
     backend guarda el patrón y no lo ejecuta, y que no valida nada en el commit;
   - en `app/composables/api/types.ts`, `FieldView.current_value` ("Always `null` today (BL-57)… that slice is not
     built"), y el comentario de `fields_draft` que remite a él;
   - `hasDraftEndpoint` en `app/stores/useFieldsDraftStore.ts`, cuyo motivo es que la escritura del commit no existe;
   - la cabecera y `buildCommitRequest` de `app/composables/useSignFlow.ts`;
   - `hasFieldDraftEndpoint` en `app/composables/useBackendCapabilities.ts`, con el mismo motivo que `hasDraftEndpoint`;
   - también, en `types.ts`, la nota de `occurrences` que llama a BL-64 *"open as a product decision"*: el 2026-09-21
     se cerró por decisión, aceptado.
10. **Tened en cuenta tres huecos de cobertura:**
    - `click-sign.vue` (flag MVP) hace commit sin `filled_fields`;
    - los tests de extremo a extremo corren con `NUXT_PUBLIC_API_MODE: 'mock'` (`playwright.config.ts`) y van por el
      camino `complete` del mock, así que el commit real con campos queda sin cubrir;
    - los fixtures `tests/fixtures/signing-session/commit-ok.json` y `commit-consent-required.json` hay que
      regenerarlos contra el nuevo spec, y no hay ninguno de un 422 `FIELD_VALUES_INVALID`.

## Lo que NO está listo todavía

- **El estampado** *(hecho por TASK-067, ver su traspaso)*. Dibujar los valores y las reservas en el PDF (BL-269). Hasta entonces, la marca visible sigue
  siendo el nombre del firmante, o su email si no hay nombre.
- **El borrador y las evidencias.** El borrador (`PATCH /signing/session/fields`, BL-40) y la recepción de
  evidencias (`POST /signing/session/evidence`).
- **Que `EDITOR` rellene campos** (BL-271). Hasta que el signer pueda enviar un acto que solo rellena, un `EDITOR` no
  envía `filled_fields`.
- **El valor explícito de "sin reservas"** (apartado 4).
- **Descargar el registro de auditoría desde el signer.** El 2026-10-01 solo lo descarga el tenant con su API key.
  Si el firmante tiene que poder hacerlo es una pregunta abierta.
- **Geolocalización, contexto del dispositivo y lectura de documentos.** El usuario decidió el 2026-09-21 que
  viajen siempre que sea posible, y la huella canvas/WebGL no. Vuestra propia propuesta es un bloque `evidence`
  opcional dentro del commit (nota interna `notes/HANDOFF-signing-evidence-capture-2026-09-21.md` del workspace).
  **Ese contrato no forma parte de este traspaso.** Su diseño en el backend es
  [TASK-045](../tasks/TASK-045-browser-reported-evidence-at-the-commit.md) (nada construido), y llegará en su propio
  traspaso. Dos cosas que ya os afectan de él: el bloque nunca impedirá firmar (un miembro mal formado se descarta
  y se anota, no da 422), y el *fallback* falso `GEO_IP` (latitud 0, longitud 0) tiene que desaparecer. Hasta que el
  `doc.json` desplegado lo publique, no lo enviéis: hoy el backend ignoraría el miembro en silencio, sin error
  (BL-177).
⚑ 2026-10-14: construido en TASK-045, en el propio commit y rechazo (no hay ruta `/signing/session/evidence`); ver [TASK-045-signer-browser-evidence.md](TASK-045-signer-browser-evidence.md).

## Lo que NO existirá, y por qué

- **Guardar los valores definitivos por `PATCH`.** Los valores definitivos solo viajan en el commit. Así el
  firmante nunca deja escrito un valor que no ha llegado a firmar. Si algún día hay borrador, será solo eso.
- **Reservas dentro de `filled_fields`, o en un campo `TEXT`.** Si las reservas pudieran vivir en dos sitios,
  el registro de auditoría, que lee el canal `reservations`, diría "no se recogieron reservas" con una reserva
  escrita en otra parte. Por eso las reservas tienen un solo canal y un tipo de campo que solo dice dónde van.
- **Un ajuste por tenant o por canal del tipo "este signer recoge reservas".** Mentiría en cuanto convivieran dos
  builds distintos, por ejemplo uno con `click-sign` y otro sin él. Solo el commit sabe qué se le preguntó al
  firmante, así que la información viaja en cada commit: en `reservations`, y en si `filled_fields` viene o no.
- **Un eco en la respuesta del commit** (un `fields_recorded` con lo registrado). Se diseñó para que un signer nuevo
  detectara un backend viejo, y el despliegue conjunto quita esa necesidad. Además, un eco seguiría respondiendo
  aunque alguien borrara la escritura, que es el defecto que registra BL-10.

## Lo que dirá el registro de auditoría mientras tanto

- **Reservas:** "este canal no recoge reservas", hasta que llegue un texto o el valor explícito.
- **IP y user agent del firmante:** los que el backend ve en la petición del commit.
- **Lo que no dirá:** ni la posición, ni el contexto del dispositivo, ni la firma dibujada, ni el texto de
  consentimiento que vio el firmante, porque nada de eso llega hoy al backend. La posición y el dispositivo
  llegarán con el bloque `evidence`, cuando exista.

## Cómo verificarlo desde el frontal

- **Antes de adoptar nada:** el `doc.json` del despliegue que os sirve publica `components.schemas.FilledField`,
  `components.schemas.FieldValueError`, `FIELD_VALUES_INVALID` en `ProblemCode` y `RESERVATIONS` en
  `SigningField.type`. Si no, ese despliegue no lleva TASK-044.
- **Campos:** con un campo TEXT y una casilla obligatoria, un commit con `filled_fields` sin la casilla devuelve 422
  `FIELD_VALUES_INVALID` con `field_errors: [{ field_id: <casilla>, code: "REQUIRED" }]`. Tras corregirla, el mismo
  código firma, y `GET /api/v1/envelopes/{id}` (con la API key del tenant) devuelve cada valor en `fields[].value`,
  su instante en `fields[].filled_at`, y `signed_at: null` en los dos.
- **Reservas:** con un sobre de prueba, el firmante escribe una reserva desde la pantalla de la imagen desplegada.
  `GET /api/v1/envelopes/{id}` devuelve el texto en `recipients[].reservations` y `has_reservations: true`, al poco
  de firmar.
- **Límite de reservas:** con un campo `RESERVATIONS` de `max_length` 120, unas reservas de 121 caracteres devuelven
  422 con un `TOO_LONG` sobre el id de ese campo.
- **El cuerpo del commit:**
  - `reservations` lleva el texto o `null`, nunca `""`;
  - `filled_fields` va presente cuando hubo formulario, y solo con los cinco tipos.

> ⛔ **Seguridad:** `current_value` (y `recipients[].reservations`) es texto que escribió un destinatario. Renderizadlo siempre como texto, nunca como HTML.
