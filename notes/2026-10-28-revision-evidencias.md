# Revisión de los ficheros de evidencia (registro de auditoría y justificante) — 2026-10-28

Estado: diagnóstico, nada implementado. Siguiente paso: decidir qué hallazgos van a una tarea (`/task-author`).
Diseño visual: tarea posterior (ver § Formato visual).

## Paso 0 — muestras

En `f5sign-backend/var/evidence-samples/` (ignorado por git; se regenera, no es durable):

- 6 registros: `app:evidence-audit:render-trail <tenant> <sobre> var/evidence-samples` con la plantilla actual.
  | sobre | escenario | págs |
  |---|---|---|
  | 01a15883 | secuencial, delegación, corrección, reenvío, OTP SMS | 10 |
  | 01a15444 | cerrado por el emisor tras acuerdo | 8 |
  | 01a15dbe | cambio de verificación y de canales, anulado | 7 |
  | 01a0f2e8 | anulado con rechazo | 6 |
  | 01a0f2c5 | anulado sin participación | 6 |
  | 01a1340a | otro tenant, sin OTP | 4 |
- 5 justificantes reales sacados del almacenamiento (`fetch.php`, vía `ByteStore`), JSON adjunto extraíble con `pdfdetach`.
- **Huecos de muestra:** los 5 justificantes son de firmantes con identidad declarada por el integrador (todos
  `RECIPIENT_SIGNED`); no hay justificante de OTP, rechazo ni aprobador, ni sobre terminado en `SINGLE_SEAL`.
  Hay que crear esos sobres en dev para cubrirlos.

## C.A — censo interno (eventos del log → PDF)

55 tipos de evento (`EVENT_TYPE` en `*/Contract/Event/`). El registro lee **solo el stream del sobre** hasta
`ENVELOPE_COMPLETED` (`AuditTrailSources`, `readSettled`); todos sus hechos salen en "Hechos registrados" y
los 55 tienen etiqueta en `trail.typ`.

- 28 interpretados (leídos a un campo del modelo), 18 solo en el listado genérico, 9 fuera del stream
  (`NOTIFICATION_*`, `IDENTITY_*`).
- Solo genéricos, que dicen algo de una parte y no aparecen en su sección (comprobado con `rg`, sin
  referencias en `EvidenceAudit`):
  - `AUTH_HARD_LOCK_REACHED` — un bloqueo por intentos no consta en la parte.
  - `RECIPIENT_AUTH_UNLOCKED` — el desbloqueo tampoco.
  - `RECIPIENT_NOTIFICATION_CHANNELS_CHANGED` — sí salen los cambios de verificación y contactos añadidos, no éste.
  - `RECIPIENT_DELIVERY_FAILED`, `RECIPIENT_INVITATION_RESENT` — revisar si `invitations` ya los cubre vía
    `RECIPIENT_INVITATION_OUTCOME_RECORDED`.
- **No existe evento de intento OTP fallido**: solo el bloqueo final. Los intentos fallidos no son evidenciables.
- Justificante: 10 tipos interpretados; solo imprime hecho de cierre, hecho del acto y frontera.

## C.B — contraste externo

Fuentes: eIDAS art. 26, LEC 326.3 (tras Ley 6/2020), DocuSign, Adobe Sign, Dropbox Sign, Signaturit,
Docuten, Lleida.net. Cobertura parcial (varias páginas 403; sin listas públicas de Validated ID, Logalty).

| dato | nosotros |
|---|---|
| id del sobre, hora de emisión UTC, emisor | ✅ |
| nombre del documento | ✅ · nº de páginas y tamaño ❌ |
| hash original, hash final, algoritmo | ✅ (y antes/después de cada revisión) |
| identidad del emisor | ⚠ solo cliente del integrador + nombre del tenant; la persona no (`DECLARED_SUBJECT_NOT_RECORDED`) |
| nombre, rol del destinatario | ✅ |
| email/teléfono | ⚠ ofuscados en el registro (`t***@***.com`); **ausentes** en el justificante |
| método y resultado de verificación con hora | ✅ (gates, nivel de garantía) |
| declarado por el integrador vs verificado | ✅ (`source` por dato) — por encima del mercado |
| cronología de eventos | ✅ |
| IP / navegador | ✅ en el acto · ❌ en la apertura |
| geolocalización | ✅ (navegador) |
| entregado / abierto | ⚠ primera apertura y lectura sí; acuse de entrega no; reaperturas no |
| motivo de rechazo | ✅ |
| imagen de la firma | ⚠ solo su hash |
| texto del consentimiento | ❌ solo que se dio (`CONSENT_TEXT_NOT_RECORDED`) |
| detalle del sello (nivel, validación, certificado) | ✅ |
| declaración de que no hay TSA/LTV | ✅ (`PLATFORM_CLOCK_TIMES`, `SHARED_PLATFORM_CERTIFICATE`) |
| sello/hash del propio registro | ✅ (sellado + cadena `sha256-chain/1` + JSON adjunto) |
| referencia externa del integrador | ❌ |

Justificante por destinatario: ningún competidor público emite uno separado (es diferencial nuestro).

## Hallazgos, por prioridad

1. **Defecto — el registro se contradice.** `GEOLOCATION_NOT_CAPTURED` ("no se captura la ubicación de ninguna
   parte") se emite siempre que alguien abrió o actuó (`TrailAssembler` `$opened || $acted`), aunque desde
   736e4efb el registro sí lleva la geolocalización del navegador. Sale en los 6 registros, también en los que
   muestran coordenadas `GRANTED`.
2. **Decisión — contactos ofuscados.** El registro va al tenant, que ya conoce los contactos; ofuscarlos le resta
   valor identificativo ante un tercero. Minimización RGPD vs prueba. El justificante no lleva contacto alguno.
3. **Huecos de datos reales**: texto/versión del consentimiento; persona detrás de un acto del integrador;
   IP en la apertura; reaperturas; acuse de entrega; intentos OTP fallidos y bloqueos en la sección de la parte;
   nº de páginas por documento; referencia externa.
4. **Menores**: `generation.app_version` sale de `SENTRY_RELEASE` (en dev `dev-smoke-20260902`, desfasado; verificar
   prod). poppler avisa `Suspects object is wrong type (boolean)` en todos los PDFs → revisar `/MarkInfo` (PDF/A-3a).

Añadir campos al JSON cambia formas publicadas (`f5sign.audit-trail/1`, `f5sign.receipt/1`). **Decisión del owner
(2026-10-28): no se sube la versión** — las evidencias no están en producción, así que se edita la `/1` en sitio.

## Hueco que el censo no vio: los campos rellenados

Los valores que el firmante rellena (`filled_fields` del commit, TASK-044) se guardan **una vez** en
`envelope.field.value` y, desde ADR-0085, se dibujan en el PDF como revisión de relleno antes de la firma, así que
están dentro de los bytes firmados (cubiertos por la huella del documento). Pero **ni el registro ni el justificante
los enumeran**: ninguna clase de `EvidenceAudit` los lee. El censo no lo detectó porque no son un evento del log
sino una fila. Propuesta: bloque "Campos rellenados" en la ficha del destinatario (etiqueta, tipo, valor, documento
y página, hora) y en su justificante; fuente `ROW` (valor inmutable una vez escrito). **Aparcado por el owner
(2026-10-28).** Valores fuera del log por TASK-044 D11; el HMAC de BL-268 sigue aplazado.

## Probar que el código recibido es el que se validó en este sobre

La cadena ya existe en los datos, pero el registro no la enseña:
- `session.auth_challenge`: el reto pertenece a la sesión (sobre + destinatario), a una puerta y, si es de firma, a un
  acto y al conjunto de documentos (`bound_document_set`); guarda solo la huella del código (`verifier_hash`).
- `AUTH_OTP_SENT`: `challenge_id` + `delivery_reference` (id de la notificación) + sobre + destinatario + método.
- Notification guarda por envío el id de mensaje del proveedor (`DbalNotificationHistory`), no en el evento.
- `AUTH_VERIFICATION_PASSED`: el mismo `challenge_id` + sobre + destinatario.
El código en claro no hace falta (ni debe salir): basta con que el reto verificado sea el enviado a ese contacto.
**Tarea de datos:** que cada envío del registro lleve `challenge_id`, hora y referencia del proveedor, y cada
verificación su `challenge_id`; así la tabla se fusiona con fiabilidad en "enviado (hora, contacto, ref. proveedor) →
verificado (hora)", y un código de firma muestra a qué documentos estaba ligado.

## Decisiones del owner (2026-10-28) para la tarea de datos

- **Contactos completos** en el registro (lo recibe el tenant, que ya los conoce); el justificante muestra el
  contacto completo del propio destinatario.
- **Entra:** IP y navegador en la apertura + cada reapertura; un evento por intento OTP fallido, y bloqueos /
  desbloqueos en la sección de la parte; nº de páginas y tamaño por documento + referencia externa del integrador.
- **No entra (por ahora):** texto/versión del consentimiento; ubicación obligatoria por sobre (`geolocation_required`,
  hoy `false` fijo en `GetSigningSessionController`) — más adelante.
- Pedir la ubicación al entrar (pantalla OTP): descartado por defecto — fricción, bloqueo permanente del permiso
  antes del acto, proporcionalidad RGPD; el acto es el momento probatorio.

## Diseño — prototipo v2 del registro (en curso)

Prototipo versionado en **`notes/evidence-design/`** (`trail-v2.typ`, `render.sh`, `logo.svg` =
`f5sign-signer/app/assets/brand/f5sign-bicolor-oscuro.svg`). Para iterar, se copia a `f5sign-backend/var/evidence-design/`
(ignorado por git) junto a `data/` con los JSON de muestra, y dentro de php-fpm `sh var/evidence-design/render.sh
trail-v2.typ trail` renderiza todas las muestras con el Typst fijado; salida en `out/`. Las muestras (`data/`, `out/`) **no
se versionan**: llevan datos personales reales; se regeneran con `app:evidence-audit:render-trail` (registros) y
`fetch.php` (justificantes, vía `ByteStore`). `trail-FICTICIO-niveles.json` es una muestra real con campos inventados
(lectura por firma, datos del fichero) para ver filas que los datos reales aún no traen. Textos solo de prototipo
en la plantilla: "No consta: el registro aún no guarda la lectura de cada firma" y la limitación de reservas.

Decidido con el owner (2026-10-28):
- Portada-resumen de una página: banda oscura con título, tenant, id y logo de la **plataforma** (no del tenant:
  el documento lo emite y sella la plataforma; un logo por URL rompe la reproducibilidad desde el JSON); estado,
  fechas clave, esquema del flujo, documentos con huella final, comprobaciones y raíz de la cadena.
- Cada sección empieza en página nueva y va numerada (las cortas siguen a la anterior); el pie dice la sección.
- **"Destinatarios", no "Partes"** (`Party` del modelo se coló en el texto; API, dashboard y justificante dicen
  destinatario). Barrido hecho en `trail-v2.typ` (0 "parte" en plantilla y PDFs); "destinatario en la entrega"
  (mercancía) pasó a "consignatario" para no mezclar sentidos. "Participación" se queda (es el término del tramo).
- **Opción C para pasos/destinatarios:** referencias `paso.posición` (1.1, 3.2; solo 1, 2, 3 si hay un paso), detalle
  agrupado por paso, y en portada un esquema del flujo por columnas (vertical si hay más de 4 pasos).
- Documentos siguen como D1, D2.
- **Cada paso y cada documento empiezan en página nueva**; los destinatarios de un mismo paso van seguidos (fichas
  cortas no desperdician página). El pie dice "3. Destinatarios · Paso 2 de 3" / "4. Documentos · D2 de 4"
  (marcadores `<step>` y `<document>`). Coste: la muestra más rica pasa de 11 a 15 páginas.
- Propuesto y aparcado por el owner: ficha del destinatario en bloques (Identificación · Cómo firmó · Actividad ·
  El acto · Datos técnicos), con "Actividad" como cronología única de invitaciones, códigos, verificaciones y acto.

- **Reservas (revisado):** nuestra app SIEMPRE ofrece reservas (campo RESERVATIONS del emisor o la casilla
  "Reservas (opcional)" en /sign y /click-sign; `sign.vue` `showReservationsBox`), y el backend guarda el vacío como
  `null` ("a clean signature", `CommitSignatureController`). Así que en la vía de la plataforma vacío = **"Sin
  reservas. Se le ofreció indicarlas y no indicó ninguna."** Solo la firma **delegada** queda en "no constan" (no
  sabemos si la pantalla del integrador las ofreció; BL-277: allí el vacío no se normaliza). La limitación general
  solo aparece si hay una delegada. Hoy el modelo mete ambos casos en `NOT_CAPTURED` (el diseño de tres estados
  quedó a medias): **va a la tarea de datos** — el ensamblador debe derivar el "sin reservas" de la vía de firma.
- **Invitaciones, verificaciones y códigos enviados como tablas** en la ficha (fuente de los contactos en una nota
  bajo cada tabla). Códigos ≠ verificaciones: un código puede no usarse, y hay verificaciones sin código. Los códigos
  van con su fecha, una fila por envío: `contacts[]` no lleva hora, pero cada uno es un `AUTH_OTP_SENT` del
  destinatario en orden (`TrailAssembler::contacts()`), y en el prototipo la plantilla toma la hora del hecho
  (cuadra 1:1 en las 6 muestras). **Tarea de datos:** añadir `at`/`position` a `ContactUse` en vez de que lo
  empareje la plantilla.
- **Fichas etiqueta/valor sin líneas, con la etiqueta centrada en vertical** respecto a su valor (todas las
  secciones; el owner descartó las líneas entre filas), para que un valor de varias líneas o una tabla quede con su
  etiqueta; un grupo de filas puede llevar subtítulo ("Declarado por el navegador
  del firmante"). Una ficha más alta que una página ya no salta: se queda y se parte (saltar dejaba el título del
  paso solo en una página).
- **Subtítulo "Declarado por el integrador · la plataforma no lo verificó"** en la ficha de una firma delegada: método,
  consentimiento, huellas, persona, IP y navegador declarados, sin repetir la coletilla de fuente en cada fila. Fuera
  quedan "Registrada por" y la IP/navegador del servidor del integrador, que sí observó la plataforma.
- **"Método al abrir" → "Acceso", y el texto era falso**: decía que la sesión se abrió *tras* una verificación de
  acceso, pero con puerta de acceso declarada se abre **antes**, sin método (`SigningSessionStarted`: "the null is a
  fact, not a gap"; 2.1 abre 09:50:13, verifica 09:50:24). "Pendiente de verificación" confundía al owner, así que la
  fila dice qué hizo falta para entrar y cuándo: "Con código por SMS: tuvo que verificarse antes de ver los
  documentos; lo hizo a las …" (de la primera verificación ACCESS) / "…no llegó a hacerlo" / "Solo con el enlace: no
  se le pidió verificarse" / "Clave de máquina del integrador." **Corregir también en producción**: el texto falso
  está en `trail.typ` y `receipt.typ`.
- **Ficha reordenada (opción A):** identidad (con el nombre arriba) → vía → subtítulo **"Invitación y verificación"**
  (Invitaciones → Primera apertura → Acceso → Códigos enviados → Verificaciones → Nivel de garantía) → subtítulo
  **"Resultado"** (firma/rechazo, consentimiento, reservas, IP y navegador del acto) → declarado por el integrador /
  por el navegador.
- **IPs de esas acciones: no existen.** `AUTH_OTP_SENT`, `AUTH_VERIFICATION_PASSED`, `AUTH_GATE_PASSED`,
  `SIGNING_SESSION_STARTED` no llevan IP ni navegador, ni `session.auth_attempt`; solo el acto (commit/rechazo) guarda
  `signer_ip`/`signer_user_agent`. Una invitación es saliente, no tiene IP del destinatario. **Tarea de datos:**
  ampliar "IP en la apertura" a IP + navegador en cada verificación (y en cada intento). Nota: `session.auth_attempt`
  ya guarda cada intento con `succeeded` (también los fallidos), fuera del log: fuente para "intentos OTP fallidos".
- **Mayúscula inicial en las etiquetas que van solas** (celdas, valores de ficha, tarjetas de portada): ayudantes
  `cap()` / `clbl()` en la plantilla; dentro de una frase la etiqueta sigue en minúscula ("firmada dibujando la
  firma", "acceso código por SMS → …"). Los **datos** (nombres, contactos, idiomas, versiones, huellas) nunca se tocan.
- **Invitaciones sin columna "Resultado"** (owner): "enviada al proveedor" es lo normal y no se dice; cualquier otro
  resultado (fallida, rechazada por el proveedor, sin canal alcanzable, la entregaba el integrador) se escribe en la
  celda de contacto, en rojo si no salió.
- **Documento rehecho:** "Asignado a" (quién lo ve / lo firma, agrupado; antes solo se veía desde cada destinatario),
  certificado una sola vez si es el mismo para todas las firmas y el sello (**retirado después**, ver abajo), y **una tabla "Historia del documento"**
  (Subido → Firma N → Sello → final) en dos líneas por fila para que no se ensanche: quién · fecha (de su hecho) ·
  cómo (modo + marca + huella corta de la imagen) y debajo la huella completa tras ese paso, con la etiqueta FINAL.
  Coletillas una vez bajo la tabla. Subtítulo "Sello de la plataforma" con la validación en palabras ("No se pudo
  confirmar: el certificado del sello no enlaza con una autoridad de confianza") y los códigos del validador al lado.
  D1 pasa de 2 páginas a 1; la muestra rica de 15 a 14.
- Ajustes del owner al documento: id del firmante bajo su nombre en cada firma; cada huella rotulada "SHA-256 del
  documento:"; el bloque "Sello de la plataforma" sube encima de la historia. El owner aún no está convencido del
  todo con la tabla de historia: revisar cuando vea los PDFs.
- Historia del documento, ajustes: rótulo "SHA-256:" a secas; sin etiqueta FINAL; el nivel PAdES ya no sale en la fila
  del sello (está en el bloque del sello; las firmas de los destinatarios no tienen nivel leído por firma en el
  modelo); paso y fecha en columnas propias centradas en vertical, fecha algo más pequeña.
- Línea "cómo firmó" (opción A): "Firma dibujada · Se ve: nombre e imagen · Imagen SHA-256 438cac57… · Puesta por el
  integrador". Modo: con un clic / dibujada / escrita; sin repetir la imagen en el modo (dibujada o escrita la implica).
- Historia: id del firmante en la línea del nombre si cabe (si no, baja entero); **SHA-256 de la imagen de firma
  completo** (recortado no sirve para comprobar nada), alineado con el del documento ("SHA-256 imagen" / "SHA-256
  documento"); fecha y hora en dos líneas para ganar ancho.
- **Regla de identificación (opción B):** el id del destinatario va siempre donde se le identifica formalmente
  (portada, ficha, "Asignado a", historia del documento); el número (1.1, 3.2) es solo apoyo visual (los UUIDv7 de un
  sobre comparten prefijo). Tablas densas (hechos) y textos sueltos llevan solo el número, y una **leyenda
  "Destinatarios de este registro"** (número · nombre · id · papel) abre la sección de hechos. "Asignado a" es una tabla:
  número · destinatario · id · Lo ve ✓/— · Lo firma ✓/—.
- **Certificado siempre en su sitio, sin colapsar "todos iguales"** (owner: con certificados personales eso dejará
  de cumplirse): el del sello en su bloque; el de cada firma en su fila de la historia (Certificado · SHA-256
  certificado, alineado con las huellas de imagen y documento). Hoy se repite; el formato no cambia el día que cada
  firmante use el suyo.
- **Tipo de firma por firma** (owner: puede haber firmas intermedias sin sello de tiempo y un sello que sí, o
  mezcla). El dato existe: `SignatureReadBack` relee del PDF final todas las firmas (`ObservedSignature`: nivel PAdES,
  sellos de tiempo, validación) pero `TrailAssembler` solo guarda el **certificado** de cada firma (la observación
  completa solo para el sello). **Tarea de datos:** que cada `Revision` guarde la misma observación que `SealStep`.
  Plantilla lista: fila "Tipo" (nivel · sello de tiempo de <TSA>, hora / sin sello de tiempo) y "Validación" corta en
  cada firma, y el bloque del sello unificado a "Tipo". Vista con una muestra **ficticia**
  (`data/trail-FICTICIO-niveles.json`, campos añadidos a mano, título "MUESTRA FICTICIA"); con datos reales no sale.
- **Bloque "Sello de la plataforma" retirado** (owner: repetía la historia): su tipo, validación y certificado van en la
  fila "Sello" de la historia, con el mismo formato que las firmas, y **cada fila lleva su "Registro: Hecho nº …"**.
  Fecha y hora vuelven a una sola línea.
- **Datos del fichero** (owner): fila "Archivo" (nombre original · tipo · tamaño · páginas), "Subido" (cuándo, por
  quién) y "Tamaño final" en la cabecera del documento; solo con la muestra ficticia. Disponibilidad: tamaño y fecha de
  cada versión en `envelope.document_artifact` (`size_bytes`, `created_at`), tipo y nombres en `envelope.document`
  (`mime_type`, `name`, `display_name`), quién lo subió en el hecho `DOCUMENT_ADDED_TO_ENVELOPE`; **las páginas no se
  guardan en ningún sitio** (habría que contarlas del PDF). Todo a la tarea de datos.
- "Documentos asignados" en la ficha del destinatario es ahora una tabla (D1 · documento · id · Lo ve · Lo firma), el
  espejo de "Asignado a" del documento. En las firmas reales sale "Tipo y validación: no consta" hasta que la tarea de
  datos guarde la lectura por firma.
- **Columnas de las tablas con anchos fijos** (owner: se ajustaban al largo de su título): invitaciones, códigos y
  verificaciones comparten fecha 31mm · verificación/tipo 20mm · método/canal 40mm · resto, así que las columnas
  quedan alineadas entre las tres tablas; asignados y leyenda: nº 8mm · nombre · id 52mm · ✓ 14mm (centrados).
- Columna de etiquetas de 44mm → **36mm**: medía casi lo mismo que el subtítulo "INVITACIÓN Y VERIFICACIÓN" y parecía
  ajustarse a él (ningún subtítulo influye: el ancho es fijo); además dejaba un hueco grande. Las etiquetas largas
  ("Versión de la plataforma") pasan a dos líneas.
- **Sin el nombre del tenant, de momento** (owner): fuera de la banda de portada, de la fila "Titular" de los datos del
  sobre y del autor del PDF. El JSON adjunto lo sigue llevando (`envelope.tenant_label`).

## Formato visual (para la tarea de diseño)

No se encontró ningún PDF de muestra público de DocuSign, Adobe, Dropbox Sign, Signaturit, Docuten, Validated ID ni
Logalty. Lo verificado:

- Lleida.net: certificado de una página aprox., logo del proveedor, id del certificado como único localizador,
  sin QR ni URL de verificación (muestra de email certificado, no de firma: https://www.lleida.net/en/documentary-evidence).
- Dropbox Sign: el registro va adjunto al documento firmado o por separado, con un identificador de consulta.
- Adobe: los informes intermedios se marcan como tales; horas en GMT.
- Signaturit: se descarga como PDF junto al documento.

Para la tarea de diseño: firmar un sobre de prueba en cada servicio (cuentas de prueba) y guardar sus PDFs.
