# Traspaso al frontal — el destinatario tiene teléfono, y el código puede ir por SMS

| | |
|---|---|
| **Origen** | rama `feat/sms-codes-and-recipient-phone` · commit `d7874ff`, mergeado a `develop` en `ed92eaf` (2026-08-20). ✅ **Publicado en `origin/develop` el 2026-08-20**; el campo `phone` de la respuesta del sobre entra en `f287454` (merge `59bb445`). |
| **Fecha** | 2026-08-20 |
| **Repos afectados** | **dashboard** (autoría y corrección) y **signer** (pantalla de gate) |
| **Naturaleza** | additive en `POST /recipients` y en `GET /envelopes/{id}` · **rompe el contrato** en `POST …/corrections` · corrige la spec publicada de `masked_destination` |
| **Acción requerida** | dashboard: **migrar antes de desplegar** el campo `email` de la corrección; signer: **manejar un nuevo estado** (`masked_destination` con forma de teléfono) |
| **Status** | ✅ **Applied (`f5sign-signer`, 2026-08-21)** — el equipo del signer verificó los cuatro requisitos de este traspaso. ⚑ **Lo que lo hace creíble es que las comprobaciones que cargan el peso son NEGATIVAS y verificadas por barrido, no una lista de sitios que cumplen**: **cero** ramificación por la forma del contacto en todo `app/` (ningún `includes('@')` ni equivalente), y **no existe ninguna función de enmascarado** en el cliente. Una lista de sitios que se comportan bien no habría podido establecer *«el cliente nunca da por hecho el correo»*, porque lo que buscábamos era justo el sitio que nadie enumeró. ⚠ **Sin sha**: lo confirmó la sesión que trabajaba en ese repo, no un PR — y este campo es de mantenimiento manual, así que **el hecho es el código de `f5sign-signer`, no esta fila** (ver [README](README.md) §*The weak spot*). |

## Lo que cambió en el contrato

**0. `GET /api/v1/envelopes/{id}` devuelve `phone` por destinatario (aditivo), entero, como `email`.** Canonicalizado a E.164, no la forma que enviasteis.

**1. `POST /api/v1/envelopes/{id}/recipients` acepta `phone` (aditivo).** Formato internacional con
prefijo de país (`+34600123456`). Se guarda canonicalizado a E.164 — los espacios y la puntuación que
mandéis se normalizan. Es opcional, y **solo se puede fijar aquí**: no hay más endpoint que lo cambie
salvo la corrección.

**2. `POST /api/v1/envelopes/{id}/recipients/{recipientId}/corrections` cambia su lista `required`, y
esto es lo único que rompe.** Antes `email` era obligatorio; ahora la regla es **al menos uno de
`email` o `phone`**. ⛔ **Un campo que omitáis se deja como está — no se borra.** No hay forma de
vaciar un contacto por esta vía, deliberadamente: vaciarlo dejaría al destinatario inalcanzable, que
es justo lo contrario de lo que una corrección existe para arreglar. Enviar el cuerpo vacío (`{}`) se
rechaza con 422 en vez de gastar una de las tres correcciones sin cambiar nada.

**3. `GET /api/v1/signing/session/auth` → `masked_destination` puede ahora tener forma de teléfono.**
Antes era siempre `usuario@dominio` enmascarado, o `null`. Ahora, cuando el método declarado es
`OTP_SMS`, llega como `+34 ·······56`.

**4. `OTP_SMS` es declarable.** Hasta ahora la API lo rechazaba con 422 `AUTH_METHOD_UNAVAILABLE`
porque ningún despliegue lo tenía cableado. Ya no.

**5. Dos códigos de error nuevos**, ambos en los dos endpoints de destinatario:

- **400 `INVALID_PHONE_NUMBER`** — el número no se puede leer, o no pertenece a ningún rango
  asignado. El cuerpo **no** repite el número (es dato personal).
- **422 `RECIPIENT_CANNOT_RECEIVE_METHOD`** — el número es perfectamente válido pero no sirve para el
  método declarado. El caso real y no obvio: **un fijo español con `OTP_SMS`**. `+34911234567` es un
  número correcto que no puede recibir SMS, y se rechaza al declararlo en vez de descubrirlo cuando
  el firmante ya está esperando. El mensaje dice qué **clase** de contacto falta y en qué puerta,
  nunca el contacto en sí.

Las formas exactas están en la spec de Nelmio; aquí no se copian.

## Lo que el frontal tiene que hacer

**Dashboard — el orden importa:**

1. **Primero**, dejad de asumir que `email` es obligatorio en la corrección. Si vuestro formulario lo
   manda siempre, no os rompéis, pero perdéis la mitad de la funcionalidad nueva.
2. Añadid `phone` al alta de destinatario. Si vuestro usuario declara `OTP_SMS`, el número deja de
   ser opcional **en la práctica**: sin él la llamada se rechaza con 422.
3. **Enrutad los dos códigos a sitios distintos, porque piden cosas distintas.**
   `INVALID_PHONE_NUMBER` significa *«este número está mal escrito»* → error de campo, junto al
   input. `RECIPIENT_CANNOT_RECEIVE_METHOD` significa *«este número está bien pero no vale para el
   método que has elegido»* → el remedio es cambiar el método **o** el número, y presentarlo como
   error de formato hará que el usuario reescriba el mismo número.
4. Mandad el teléfono como lo tenga escrito el usuario. No lo normalicéis vosotros: lo hacemos aquí,
   y dos normalizaciones distintas es peor que ninguna.

**Signer — un estado nuevo en una pantalla que ya existe:**

`masked_destination` deja de ser siempre una dirección. Si lo estáis renderizando con una plantilla
que dice *«te hemos enviado un correo a …»*, esa frase es ahora falsa para los destinatarios de SMS.
El campo `method` del mismo descriptor os dice cuál es (`OTP_SMS` / `OTP_EMAIL`); **usadlo para
elegir la frase**, y `masked_destination` solo para el valor.

⚠ **No reconstruyáis el enmascarado en cliente.** Llega ya enmascarado desde el servidor, a propósito:
esa ruta contesta **antes** de que nadie haya demostrado nada, así que lo que revela se le revela a
quien tenga el enlace. Si necesitáis otra forma, pedidla — no la derivéis.

## Lo que NO está listo todavía

⛔ **Ningún SMS ha salido nunca de este sistema.** La cuenta de Twilio está en espera, así que:

- `SMS_DSN` vale `null://null` en dev y en test — el canal está cableado y **descarta** lo que se le
  manda. Una prueba end-to-end vuestra en dev **no** hará sonar ningún móvil, y eso no es un fallo.
- La barra de entrega *«el código llega a un móvil real»* **queda abierta**. Está dicho así en el
  registro de la task; no la deis por buena porque el 200 salga bien.

✅ **El teléfono SÍ sale en la respuesta del sobre — resuelto el 2026-08-20.** Este apartado decía que
estaba pendiente; ya no lo está. `GET /envelopes/{id}` devuelve `phone` por destinatario, **entero**,
igual que `email`. Podéis construir la pantalla de edición que muestra el número actual.

⚑ **Ojo a la forma**: lo que devolvemos es E.164 canónico, **no** lo que se envió. Si mandáis
`"+34 600 12 34 56"`, al leerlo os llega `"+34600123456"`. Es a propósito — hay una sola forma
almacenada — pero si vuestro formulario compara lo tecleado con lo devuelto para detectar cambios,
tenedlo en cuenta o veréis diferencias que no existen.

⛔ **Y NO es lo mismo que ve el firmante.** En `GET /signing/session/auth` el número va **enmascarado**
(`+34 ·······56`), porque esa ruta contesta antes de que nadie haya demostrado nada. Las dos
proyecciones son distintas a propósito; no useis una para rellenar la otra.

⚠ **El teléfono se guarda sin cifrar**, igual que el correo que ya estaba. Es una decisión tomada y
registrada, no un descuido, pero conviene que lo sepáis si estáis pensando en cachearlo en cliente.

⛔ **`OTP_WHATSAPP` y `OTP_VOICE` siguen sin existir.** Están en el catálogo de métodos y ningún
despliegue los puede ejecutar; declararlos se rechaza con `AUTH_METHOD_UNAVAILABLE`.

## Cómo verificarlo desde el frontal

1. **Alta con teléfono**: `POST /recipients` con `phone: "+34 600 12 34 56"` y `auth.access_method:
   "OTP_SMS"` → 201. Un `GET` del sobre después **sí** os devuelve el número, en E.164 canónico
   (`+34600123456`) — ver arriba. ⚑ **Esta línea decía lo contrario hasta el 2026-08-21** (*«no os
   devolverá el número»*): era cierta cuando se escribió y dejó de serlo el mismo 2026-08-20 en que
   `phone` entró en la respuesta del sobre, dos secciones más arriba, sin que nadie volviera a esta.
2. **El fijo**: el mismo alta con `phone: "+34911234567"` → 422 con `code:
   "RECIPIENT_CANNOT_RECEIVE_METHOD"`. Es el caso que más merece un test vuestro, porque es el único
   que parece que debería funcionar.
3. **Número ilegible**: `phone: "no-soy-un-numero"` → 400 con `code: "INVALID_PHONE_NUMBER"`.
4. **Corrección solo de teléfono**: `POST …/corrections` con `{"phone": "+34600123457"}` → 204, y el
   correo del destinatario sigue siendo el que era.
5. **Corrección vacía**: `{}` → 422. Si os devuelve 204, avisadnos.
6. **El descriptor**: abrid un enlace de firma de un destinatario con `OTP_SMS` y mirad
   `masked_destination` en `GET /signing/session/auth`. Debe empezar por `+34` y acabar en los dos
   últimos dígitos, y el cuerpo entero no debe contener ninguna `@`.

⛑ **2026-10-13** ([TASK-031](TASK-031-notification-channels.md)): an add-recipient now also requires `notification_channels`, so step 1's body needs it (`["EMAIL"]` keeps the old behaviour), and the correction in step 4 answers `200 {"warnings": [...]}`, not `204`. The steps above are the contract as this handoff shipped it.
