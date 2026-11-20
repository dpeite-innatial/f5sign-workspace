# Traspaso al integrador — valores de campo, reservas y registro de auditoría: lo que pedimos a dashboard-sf

| | |
|---|---|
| **Origen** | Rama `feat/field-values-at-commit`: `061e293` (una extensión del problema puede ser una lista, [ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md)) · `6f106d8` (las reglas de los valores) · `0bae290` (el commit lleva los valores a Envelope) · `50c44ac` (la lectura en las dos superficies) · `ce284c4` (las guardas de `send()`) · `4f7231e` (el tipo `RESERVATIONS`, [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md)) · merge de `origin/develop` en `b51b1bd`. El spec OpenAPI y estos registros van en **el commit de aterrizaje en `develop`: `<landing sha>`** ⚠ *pendiente de rellenar*. Sin PR. Diseño en [TASK-044](../tasks/TASK-044-field-values-recorded-at-the-commit.md). Las peticiones del registro de auditoría (Audit Trail), redactadas por otra sesión del backend, siguen sin commitear en ningún sitio. |
| **Fecha** | 2026-09-21 |
| **Repos afectados** | `dashboard-sf` (integración de Factor5) |
| **Naturaleza** | Aditivo en el esquema, con dos cambios de significado: `recipients[].reservations: null` y `fields[].signed_at`. Además, un cambio que tenéis que hacer vosotros: el tipo del campo "Reservas". |
| **Acción requerida** | Cambiar el tipo del campo "Reservas" **en el mismo despliegue** que el backend y el signer. El resto, a vuestro ritmo. |
| **Desplegado** | No. Ni siquiera mergeado en `develop` al escribir esto: el `<landing sha>` de arriba es el que lo dirá. |
| **Status** | Pending |

⛑ **2026-09-21**: la fila `Origen` decía *«Nada construido… A 2026-09-21 ni lo uno ni lo otro está commiteado»*. La
parte de TASK-044 está ya construida en la rama, y los apartados 1, 8 y 9 describen ahora lo construido; lo del Audit
Trail sigue igual.

**Medido en:**
- `dashboard-sf`: `origin/master` `20c6a1289` y `origin/feat/waybill-pdf` `cf8072e64`, que son los commits de las
  peticiones del Audit Trail. Los apartados 1 y 8 los hemos vuelto a medir en vuestra rama local
  `feat/waybill-pdf-pagination` `dac9a63f9`.
- `f5sign-backend`: `feat/field-values-at-commit` `b51b1bd`, con los `#[OA]` del tramo final aún sin commitear. La
  versión anterior de este documento midió `develop` `e845e03` con los cambios de TASK-044 sin commitear.

Este documento sustituye a la petición del Audit Trail a `dashboard-sf` (`REQUESTS-DASHBOARD-SF.md`) y añade lo
que os afecta de TASK-044. Se juntan porque los dos hablaban de vuestro campo "Reservas" y os pedían cosas
distintas.

## Resumen

Para el 2026-10-01 estamos construyendo el registro de auditoría (Audit Trail) de cada sobre: un PDF sellado,
aparte de los documentos firmados, que se genera cuando el sobre se completa o se anula. Dice qué pasó, y cuando
no lo sabe, dice que no lo sabe. Varias de sus afirmaciones sobre una carta de porte dependen de lo que envía
`dashboard-sf`.

**No esperamos nada del registro de auditoría para el 2026-10-01.** Mientras no llegue, el registro dirá "no
consta" o dirá de dónde sale cada dato. Cuando llegue, lo recogerá sin cambiar su diseño.

Aparte, con TASK-044 el backend empieza a guardar y devolver los valores de los campos, y las reservas pasan a
tener un solo canal. Eso sí exige un cambio vuestro en el despliegue conjunto.

| # | Qué | Prioridad |
|---|---|---|
| 1 | Reservas: el campo cambia de tipo, y leerlas | **alta; el cambio de tipo, en el despliegue conjunto** |
| 2 | Consentimiento del cargador: el texto del botón | alta |
| 3 | Mapa de páginas de la conjunta: fusionar el arreglo | alta |
| 4 | IP y user agent del operador en el commit delegado | media |
| 5 | Correcciones de contacto: enviarlas al backend | media |
| 6 | Destinatario reclamado: autenticarlo (decisión de producto) | media |
| 7 | Detalles menores | baja |
| 8 | Valores de campo: qué devuelve el backend | informativo |

Los cambios de contrato están en el apartado 9, y lo que dirá el registro de una carta de porte, en el 10.

## 1. Reservas (prioridad alta)

**Qué pasa hoy:**

- **Vuestro campo.** Cada destinatario lleva un campo de texto "Reservas" (`WaybillSignatureFormFields::forDestinatario`):
  no obligatorio, `max_length` 120, con una posición en su carta de porte y otra en su página de la conjunta.
- **El backend desplegado no guarda valores de campo** (el `current_value` de la sesión es siempre `null`) y no pinta
  reservas en el PDF sellado (TASK-016 §4 del backend). Con TASK-044 los guarda (apartado 8), pero sigue sin
  pintarlos (apartado 11).
- **Las reservas van por otro sitio:** el campo `reservations` del commit de firma, que envía la app del signer.
  La imagen desplegada del signer envía siempre `reservations: null`; se lo pedimos a su equipo por separado.
- **Resultado:** hoy ninguna reserva de un destinatario llega a la plataforma.
- **No las leéis:** `F5SignApiGateway::getStatus` no lee `recipients[].reservations` ni `has_reservations` de
  `GET /envelopes/{id}`, aunque el backend los publica.
- **Toda firma cuenta como entrega limpia:** `WaybillSignatureDeliveryLinker` convierte la firma de un
  destinatario en ENTREGA TOTAL, haya reservas o no.

**Por qué importa.** La Ley 15/2009 (art. 60.1) presume que la mercancía llegó como se describe si el
destinatario no hace reservas por escrito en la entrega. Por eso el registro no dirá nunca "firmó sin reservas" a
partir de un `null`: sería fabricar una prueba contra el destinatario. Hoy dirá "este canal no recoge reservas".

**Por qué el campo cambia de tipo en vez de desaparecer.** Vuestro docblock lo explica bien: el recuadro
OBSERVACIONES DESTINATARIO tiene que llevar la reserva en las dos copias, y la conjunta es la que el conductor
enseña en una inspección. Eso necesita una posición, y solo un campo la tiene. Pero si la reserva se guardara
como valor de un campo `TEXT`, viviría fuera del canal `reservations`: fuera del registro permanente y fuera de
lo que lee el registro de auditoría, que entonces diría "no consta" con una reserva escrita. Por eso:
- el texto viaja solo por `reservations`;
- un campo de tipo nuevo, `RESERVATIONS`, dice dónde se dibuja ([ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md)).

**Qué os pedimos:**

1. **Cambiar el tipo de "Reservas" de `TEXT` a `RESERVATIONS`** en `forDestinatario()`, en el mismo despliegue
   que el backend y el signer.
   - Mantened las dos posiciones y el `max_length` 120. Ahora ese límite es real: si el destinatario firma con unas
     reservas de más de 120 caracteres, su commit se rechaza con 422 `FIELD_VALUES_INVALID` y un registro
     `TOO_LONG` sobre el id de este campo. Al signer se le pide que aplique el límite al escribir. Hoy el backend no
     tiene ningún límite de 120; `reservations` admite 2000, y ese techo del canal no cambia.
   - **Las restricciones del tipo**, que `POST /api/v1/envelopes/{id}/fields` comprueba al crear el campo. Cada una
     es un 422 que no crea nada, con `code: UNPROCESSABLE_ENTITY` y el motivo en `detail`:
     - tiene que nombrar a un destinatario, así que ese destinatario tiene que existir antes que el campo;
     - ese destinatario tiene rol `SIGNER` o `APPROVER`, que es vuestro caso: vuestros tres roles son `SIGNER` en la
       plataforma;
     - no puede ser `required`;
     - no lleva `choices`;
     - de `validation`, solo `max_length`: un `pattern`, un `pattern_message` o un `date_format` se rechazan;
     - como mucho uno por destinatario. Para otra posición, se añade una ocurrencia al mismo campo, no un campo
       nuevo.
   - **Sin el cambio**, tras el despliegue el backend guardaría lo escrito como valor de un campo de texto, y
     el registro de auditoría no lo vería como reserva.
2. **Leer las reservas.** Guardad localmente `recipients[].reservations` en `getStatus`. El texto viene ahí, no en
   el campo, cuyo `value` es siempre `null`.
3. **Decidir qué significa localmente una firma con reservas.** Hoy acaba en ENTREGA TOTAL. Registrar como entrega
   limpia una firma con reservas repite en vuestros datos el mismo problema que el registro evita. Es decisión de
   producto; solo lo señalamos.
4. **En el commit delegado del cargador,** `reservations` es opcional. Si no le preguntáis al operador por
   reservas, no enviéis nada. Y no enviéis `""`: la ruta del firmante convierte un texto en blanco en `null`, pero
   la delegada lo guarda tal cual.

**Dibujar la reserva en el PDF** lo hizo después [TASK-067](TASK-067-signed-pdf-carries-the-recorded-values.md) (antes: apartado 11). Cuando exista, se dibujará en cada posición del
campo, **también en la conjunta que el destinatario no ve**. Esa es la respuesta que vuestro docblock pedía al
backlog del backend (BL-64): aceptada el 2026-09-21.

## 2. Consentimiento del cargador: el texto del botón (prioridad alta)

**Qué pasa hoy:**

- **El consentimiento es un clic.** El consentimiento del cargador es el clic del operador en "Sí, enviar". El
  diálogo dice "¿Enviar a firma? Se bloqueará la carta de porte y se enviará a firmar."
  (`assets/app/admin/js/modules/transport_request/waybill/signature.js`). No dice que al enviar el operador firma
  como cargador.
- **Vuestro propio código dice que el botón tiene que decirlo** (`WaybillEnvelopeService.php`).
- **La hora puede no ser la del consentimiento.** `autoSignCargador` usa la hora actual si no hay instante de
  consentimiento guardado, y el comentario de encima dice que eso no debe pasar.

**Por qué importa.** El registro dirá del cargador: "firmó por delegación; el integrador afirma que el operador
`<asserted_subject>` consintió el `<asserted_consented_at>`, autenticado por `DASHBOARD_SESSION`". Todo el peso de
esa línea está en el texto que vio el operador.

**Qué os pedimos:**

1. Un texto que lo diga. Por ejemplo: "Al enviar, firmas esta carta de porte como cargador, en nombre de
   {empresa}."
2. Guardar la historia de ese texto con fechas, para poder enseñar qué vio un operador un día concreto.
3. Si no hay instante de consentimiento guardado, no firmar, en vez de fecharlo con la hora de la llamada.

## 3. Mapa de páginas de la conjunta (prioridad alta)

**Qué pasa hoy** (medido en `20c6a1289` y `cf8072e64`):

- `origin/master` ya genera páginas de continuación, pero `WaybillSignatureCells::conjuntaPageFor` sigue
  devolviendo `i + 2`.
- Con una página de continuación, las marcas de firma y el recuadro de reservas de los destinos siguientes caen en
  la página equivocada, y el último destino se queda sin ellos.
- El arreglo (`WaybillConjuntaPageMap`) estaba en `origin/feat/waybill-pdf` (`cf8072e64`), un commit por delante de
  `origin/master`, sin fusionar.

**Por qué importa.** El PDF firmado es la prueba. Si la firma de un destinatario cae en la página de otro destino,
el registro señalará ese PDF como lo que se firmó. Con el apartado 1 importa también para las reservas: el
recuadro que dibujará el backend es la posición de vuestro campo `RESERVATIONS`.

**Qué os pedimos:** fusionar el arreglo antes de enviar a firma cartas de porte con páginas de continuación. En la
versión que revisamos el 2026-09-17, un bloque demasiado largo en la página de continuación se solapaba con la fila
CONFORME o se cortaba, y la comprobación del número de páginas no lo detectaba.

⚠ **Puede estar desfasado.** Vuestra rama local `feat/waybill-pdf-pagination` (`dac9a63f9`, *"Let the carta de
porte PDF flow, and pin the signatures to the foot of every page"*) va cuatro commits por delante de
`origin/master`, y en ella `forDestinatario()` ya recibe el `WaybillConjuntaPageMap`. No hemos vuelto a medir el
solapamiento en ella.

## 4. IP y user agent del operador en el commit delegado (prioridad media)

**Qué pasa hoy:** vuestro DTO ya los admite (`Dto/DelegatedSignatureAssertion.php`), pero `autoSignCargador` no los
pasa. El backend los acepta en `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature`:
`asserted_signer_ip` (máximo 45 caracteres) y `asserted_signer_user_agent` (máximo 512).

**Qué os pedimos:** tomarlos de la petición del envío a firma, la misma en la que guardáis el consentimiento, y
pasarlos al commit delegado. No los toméis de la segunda petición: el dato tiene que ser el del acto.

**Qué dirá el registro:** que el integrador los afirma. Sin ellos, "no consta".

## 5. Correcciones de contacto (prioridad media)

**Qué pasa hoy:** "Editar datos" en el hub solo cambia vuestra copia local (`WaybillPublicController.php`). La
plataforma sigue con la dirección vieja, así que un reenvío va a esa dirección, y el registro muestra la
dirección que tenía la plataforma.

**Qué os pedimos:** llamar a `POST /api/v1/envelopes/{id}/recipients/{recipientId}/corrections`. Vuestra nota dice
que no tenéis la especificación del cuerpo; está en el `doc.json` del despliegue (`CorrectRecipientRequest`). Lo
principal:

- Lleva `email`, `phone` o los dos. Al menos uno es obligatorio; el que falta no se toca.
- Devuelve al destinatario a `PENDING` y le manda una invitación nueva.
- Cada destinatario admite 3 correcciones. La cuarta devuelve 409 `RECIPIENT_CORRECTION_BUDGET_EXHAUSTED`, y una
  corrección rechazada no gasta ninguna.
- Un hueco sin reclamar no se corrige, se reclama (`…/claim`).

## 6. Destinatario reclamado: autenticarlo (prioridad media, decisión de producto)

**Qué pasa hoy:** un destinatario sin contacto sale como hueco reclamable y sin ningún control de acceso
(`WaybillEnvelopeService::isClaimableDestinatario`). Después del claim firma solo con el enlace. El registro dirá:
"identidad tecleada en el muelle por quien tenía el hub; sin autenticar; solo posesión del enlace".

**Lo que ya permite el backend** (ADR-0057 §2.13): declarar el control de acceso en el hueco al crearlo, y comprobar
el destino en el claim.

- Con `OTP_EMAIL`, el claim tiene que traer un email, y el destinatario lo demuestra con un código.
- Con `OTP_SMS`, tiene que traer un móvil. Además, el despliegue necesita un proveedor de SMS configurado
  (`SMS_DSN`); con el valor por defecto, los SMS se descartan.
- Un claim que no puede cumplir el control declarado se rechaza con 422.

**Qué os pedimos:** que lo consideréis. El coste es que, en el muelle, el destinatario tiene que poder recibir un
código. Lo decidís vosotros con Factor5.

## 7. Detalles menores (prioridad baja)

- **`deliveryFailed` no se enciende nunca.** Se calcula a partir de `outcome == "DELIVERY_FAILED"`
  (`F5SignApiGateway.php`), un valor que el backend retiró en ADR-0065. Usad el mapa `delivery`:
  `delivery[<destino>].state === "FAILED"`. El traspaso [ADR-0065-recipient-delivery-split.md](ADR-0065-recipient-delivery-split.md)
  lo explica.
- **El texto de respaldo del reenvío dice 15 minutos** (`WaybillPublicController.php`). El intervalo del backend es
  de 60 segundos. El camino normal usa `next_resend_at` y es correcto.
- **Motivo de anulación.** El modal no envía motivo, así que queda "Cancelado por el usuario"
  (`WaybillSignatureController.php`). El registro pone el motivo tal cual llega. Si el motivo real del operador
  puede importar en una reclamación, pedidlo en el modal.
- **`asserted_subject` es el id del operador.** El registro lo muestra como referencia opaca. En una reclamación,
  relacionarlo con una persona depende de vuestros registros: conservad la correspondencia entre id y persona, y el
  log de peticiones, durante el plazo de conservación de la carta de porte. Ese plazo está pendiente de confirmar
  con asesoría legal.

## 8. Valores de campo: qué devuelve el backend (informativo)

- **Vuestro comentario queda desfasado.** El de `F5SignApiGateway::addField()` dice que lo que teclea el firmante
  es de solo escritura, porque la parte del commit que lo guardaría no existe. Con TASK-044 existe: el valor se
  guarda en el commit y vuelve en `GET /api/v1/envelopes/{id}`.
- **Qué publica cada campo** en `fields[]`:
  - `value`, el valor registrado: texto en `TEXT`, `DATE` (`YYYY-MM-DD`), `DROPDOWN` y `RADIO` (el `value` de la
    opción), booleano en `CHECKBOX`. Es siempre `null` en los demás tipos, y en particular en `RESERVATIONS`, cuyo
    texto está en `recipients[].reservations`.
  - `filled_at`, el instante del commit, solo en esos cinco tipos de datos. Distingue los tres casos que `value: null`
    no distingue: sin `filled_at`, nada registrado (antes del commit, o un commit que no recogió formulario); con
    `filled_at` y `value: null`, se dejó en blanco; con los dos, respondido. Una casilla que se mostró y no se marcó
    queda `false`.
  - `signed_at`, **solo en un campo `SIGNATURE`**; en los demás, `null`. Hoy es `null` en todos, también en las
    firmas, porque nada lo escribe todavía; y vuestro `getStatus` no lo lee, así que no os afecta.
- **Rechazos nuevos al enviar el sobre**, en `POST /api/v1/envelopes/{id}/send`. Cada uno es un 422 con
  `code: UNPROCESSABLE_ENTITY` y un `detail` que empieza por *"Pre-send invariant violated: field `<id>` …"*:
  - un campo de datos (`TEXT`, `DATE`, `CHECKBOX`, `DROPDOWN` o `RADIO`), **obligatorio o no**, asignado a un rol que
    no rellena: solo rellenan `SIGNER` y `APPROVER`;
  - un campo obligatorio que nada puede responder todavía: `INITIALS`, `ATTACHMENT`, `PAYMENT`, `KYC` o `EUDI_WALLET`;
  - un campo de datos obligatorio que nadie alcanza: sin destinatario, o sin ningún rectángulo en un documento que su
    destinatario pueda leer. Uno alcanzable solo en parte sigue siendo válido.
- **Rechazos nuevos al crear un campo:** los de `RESERVATIONS` del apartado 1.
- **Ninguno afecta a vuestro sobre de hoy**: vuestros tres roles son `SIGNER`, y "Reservas" no es obligatorio.
- **El commit delegado del cargador** acepta también `filled_fields`, con la misma forma y las mismas reglas que la
  ruta del firmante. Si no lo enviáis, no se registra nada, pero un campo obligatorio de ese destinatario hace que
  el acto se rechace con 422 `FIELD_VALUES_INVALID`. El cargador no tiene campos (`forCargador()` devuelve `[]`),
  así que no tenéis que enviar nada.

## 9. Lo que va a cambiar en el contrato

**`GET /api/v1/envelopes/{id}`:**
- **Reservas en tres estados.** Es aditivo, pero cambia un significado:
  - **hoy**, `recipients[].reservations: null` se publica como "firmó sin reservas", y `has_reservations: false`
    como "nadie hizo reservas" (TASK-016);
  - **con el cambio**, `null` pasa a significar "no consta", y un valor nuevo por destinatario dirá "declaró no tener
    reservas". `has_reservations` sigue significando "alguien escribió reservas", pero `false` ya no implica "nadie
    tuvo reservas";
  - **impacto hoy:** ninguno, porque no leéis estos campos. No construyáis sobre el significado antiguo.
- **Por campo:** `value`, `filled_at`, y `signed_at` solo en firmas (apartado 8). Es TASK-044, construido en rama.
- **`type`:** gana el valor `RESERVATIONS`. También TASK-044.

**`POST /api/v1/envelopes/{id}/fields`:** admite `type: "RESERVATIONS"`, con las restricciones del apartado 1
(TASK-044).

**`POST /api/v1/envelopes/{id}/send`:** los tres rechazos nuevos del apartado 8 (TASK-044).

**Commit delegado (`…/recipients/{recipientId}/signature`):**
- tendrá el mismo campo de tres estados para las reservas, opcional;
- acepta `filled_fields` (TASK-044): una lista de `{ field_id, value }`, con exactamente esas dos claves, como mucho
  512 entradas, `value` texto, booleano o `null` (nunca un número). La forma exacta es
  `components.schemas.FilledField` del `doc.json`;
- puede responder 422 `FIELD_VALUES_INVALID`, con `field_errors: [{ field_id, code }]`: un registro por campo mal
  respondido, ordenados por `field_id` (`components.schemas.FieldValueError`). Responde antes que `STEP_NOT_ACTIVE`,
  porque esperar no arregla un valor, pero nunca antes de un rechazo del propio acto (ya completado, sesión cerrada,
  sobre que ya no está vivo);
- sigue respondiendo 204.

**Ruta nueva: descarga del registro de auditoría (PDF), con vuestra API key.**

- Existe cuando el sobre llega a `COMPLETED` o `VOIDED`. Se genera de forma asíncrona, normalmente poco después del
  estado terminal; si ese intento falla, una barrida cada hora lo repite. No contéis con él en el mismo instante en
  que veis `COMPLETED`.
- Quizá haya también un indicador en `GET /envelopes/{id}` de que el registro está disponible. No está decidido.
- El nombre, la forma y los códigos de error os llegarán en su traspaso.

**Lo que no cambia:** no hay webhooks salientes, así que vuestro `SignatureWebhookReceiver` sigue sin emisor. El
evento interno de firma gana un campo, pero no se publica.

Cada cambio os llegará como traspaso en `docs/frontend-handoff/` del backend, con el commit, y podréis comprobarlo
en el `doc.json` del despliegue que os sirve. Os avisaremos cuando se fusione y otra vez cuando se despliegue.

## 10. Qué dirá el registro de una carta de porte

La forma exacta del PDF está por cerrar. Esto es lo decidido:

- **El documento:** un PDF sellado, en español, aparte de los documentos firmados. Lleva un anexo legible por
  máquina con los compromisos y la raíz de la cadena, sin datos personales.
- **Qué cubre:** el sobre hasta su hecho terminal, `COMPLETED` o `VOIDED`. En una anulación dice qué sesiones
  cerró.
- **Cargador:** el nombre de la empresa; "firmó por delegación"; el operador, el instante y el método que afirma el
  integrador; IP y user agent si los enviáis.
- **Transportista y destinatario con contacto:** el nombre que figura en la marca del PDF firmado; el destino del
  código (enmascarado); autenticación por código.
- **Destinatario reclamado:** "identidad tecleada en el muelle; sin autenticar; solo posesión del enlace".
- **Reservas:** las que lleguen por `reservations`, incluidas las escritas en la caja de vuestro campo
  `RESERVATIONS`. Mientras no lleguen, "este canal no recoge reservas".
- **Datos personales:** email y teléfono enmascarados; IP y user agent completos; ningún número de documento de
  identidad.
- **Firmas:** las marcas de cada firmante se firman con el certificado de la plataforma. El registro dirá que no son
  firmas avanzadas de los firmantes.
- **Sello del propio registro:** el nivel que se obtenga de verdad. Mientras no haya una TSA cualificada y un
  certificado de sello, lo dirá.
- **No dirá:** las reaperturas del enlace, quién hizo el claim en el hub, ni el texto de consentimiento que vio
  cada firmante.
- **La geolocalización y el contexto del dispositivo** no los dirá hasta que el signer los envíe. El usuario
  decidió el 2026-09-21 que viajen siempre que sea posible; el contrato está por diseñar en el backend.

## 11. Lo que NO está listo todavía

- *(Hecho por TASK-067, ver su traspaso.)* **Pintar en el PDF sellado** los valores de campo y las reservas (backlog del backend BL-269). Se dibujarán en las
  posiciones de cada campo, `RESERVATIONS` incluido.
- **Webhooks salientes.**
- **El valor explícito de "sin reservas"** del apartado 9, cuyo nombre y forma fija un ADR del backend que aún no
  existe.

## 12. Lo que NO existirá, y por qué

- **Un ajuste por tenant o por canal del tipo "este canal recoge reservas".** Mentiría en cuanto convivieran dos
  builds del signer distintos. Solo el commit sabe si al firmante se le preguntó, así que la información viaja en
  cada commit.
- **Reservas guardadas como valor de un campo `TEXT`.** Tendrían posición, pero quedarían fuera del registro
  permanente y del registro de auditoría. El registro diría "no consta" con una reserva escrita. Por eso el texto
  tiene un solo canal, y el campo `RESERVATIONS` solo dice dónde va.

## Cómo verificarlo desde el integrador

- **Antes de cambiar el tipo:** el `doc.json` del despliegue que os sirve lista `RESERVATIONS` en `Field.type` y
  publica `components.schemas.FilledField` y `FieldValueError`. Si no, ese despliegue no lleva TASK-044, y crear el
  campo con ese tipo daría 422.
- **Tipo del campo:** tras el despliegue conjunto, `GET /api/v1/envelopes/{id}` de una carta de porte nueva
  devuelve el campo "Reservas" con `type: "RESERVATIONS"`, `value: null` y `filled_at: null`.
- **Reservas:** si un destinatario escribe una reserva, esa misma respuesta la devuelve en
  `recipients[].reservations` con `has_reservations: true`, al poco de firmar.
- **Límite:** unas reservas de más de 120 caracteres se rechazan en el commit con 422 `FIELD_VALUES_INVALID`, y
  `field_errors` trae `{ field_id: <id del campo "Reservas">, code: "TOO_LONG" }`.

> ⛔ **Seguridad:** `value` y `recipients[].reservations` son texto que escribió un destinatario. Tratadlo como no confiable al mostrarlo o al llevarlo a un PDF.
