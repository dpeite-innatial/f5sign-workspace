# Traspaso al frontal — un destinatario puede declarar VARIOS métodos de autenticación, en orden

| | |
|---|---|
| **Origen** | ✅ **merged en `develop`: `c79ce3d`, y pusheado** — la rama `feat/ordered-auth-method-list` traía `ab459a9` (declaración) + `1bab9ee` (ceremonia) + el modo de presentación (§5); `97d7e3c` y `5daef92` cayeron en `develop` **después** del merge, los dos barridos de prosa sobre el mismo re-corte. ⚑ Esta fila decía *"la rama sigue viva y aún no hay PR"* hasta el 2026-08-21 |
| **Fecha** | 2026-08-20, **ampliado el 2026-08-21 con la mitad de ceremonia y, ese mismo día, con el modo de presentación (§5)** |
| **Repos afectados** | **dashboard** (autoría) y **signer** (ceremonia) |
| **Naturaleza** | **additive** — ningún campo publicado cambia de tipo ni desaparece. ⚠ Dos campos nuevos del descriptor (`methods` y `selection`) son **incondicionales**: aparecen también para una puerta de un solo método, y `selection` está además en `access_gate` |
| **Acción requerida** | dashboard: *update types*, y recoger un teléfono antes de poder declarar SMS · signer: *update types*, **y ya se puede construir la pantalla de elección** — ⛔ y antes de nada, **declarar `AUTH_METHOD_NOT_CHOSEN` en `OtpAuth` y en `ReauthModal`**: §5.3 explica por qué eso va primero |
| **Desplegado** | ✅ **Sí** — `c79ce3d` es ancestro del checkout que sirve el stack (`97d7e3c`), y vosotros mismos lo verificasteis contra la API el 2026-08-21. ⚠ Lo que vino **después** de ese commit no lo está: el checkout servido va varios commits por detrás de `develop`, así que comprobad cada añadido en el `doc.json` que os sirven antes de adoptarlo (README regla 4) |
| **Status** | ⚠ **Parcialmente aplicado — y lo que falta es justo lo que mantiene `FREE_CHOICE` inalcanzable.** Medido el 2026-08-21 sobre los checkouts hermanos y **no** sobre el remoto, que es la diferencia que importa aquí: **`f5sign-signer`** tiene `4bc13cc` (declara `AUTH_METHOD_NOT_CHOSEN`, el paso que el orden de despliegue de abajo exige primero), `e1dd775` (modela la lista y el modo de presentación) y `ffaa0db` (la pantalla de elección, **deliberadamente sin montar**) — los tres **sin pushear** en su `develop`, así que un escaneo del remoto no los ve y concluiría que no hay nada. **`f5sign-dashboard`**: nada; no consume el objeto `auth` en absoluto. ⛔ Sin control de autoría en dashboard ningún remitente puede declarar la lista ni el modo, que es exactamente por qué el signer dejó su pantalla sin cablear en vez de olvidarla. Comprobadlo contra el `git log` de cada repo, no contra esta fila. |

---

## Lo que cambió en el contrato

**Un gate ya no nombra un método: nombra una lista ordenada.** La decisión es
[ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md); el problema que resuelve es que un firmante
cuyo código no llega **no tiene ninguna jugada** — la única recuperación es que el remitente le
corrija el contacto, y mientras tanto espera a alguien que no está delante.

⛔ **Lo que NO cambia, y conviene decirlo primero porque es lo que la gente asume al revés:** el
backend **nunca** cambia de canal por su cuenta. Si un envío falla, no reintenta por otro sitio. La
lista le da la elección **al firmante**, que es un acto de una persona identificada; un cambio
automático alteraría en silencio la fuerza que queda registrada en la evidencia de la firma
(ADR-0049 §2.7, que sigue vigente).

### Autoría — `POST /api/v1/envelopes/{id}/recipients`

El objeto `auth` gana dos campos, **y los dos antiguos siguen funcionando igual**:

| campo | estado |
|---|---|
| `access_method` (string, nullable) | **sin cambios**, y ahora significa *la lista de un elemento* |
| `signing_method` (string, nullable) | **sin cambios**, idem |
| `access_methods` (array de string) | **nuevo** — la lista, en orden |
| `signing_methods` (array de string) | **nuevo** — idem, e **independiente** del anterior |

⛔ **Mandar el singular y el plural del mismo slot es un 422.** Son dos grafías de una sola
declaración y no hay lectura de "ambos" que sea segura de adivinar, así que no hay regla de
precedencia que se pueda malinterpretar: o una, o la otra.

**Reglas de la lista** (todas devuelven 422, con el índice del miembro que falla en el `path`):

- Una lista de **dos o más** solo admite métodos que **entregan un código**: `OTP_EMAIL`, `OTP_SMS`,
  `OTP_WHATSAPP`, `OTP_VOICE`. `ACCESS_CODE` queda fuera — se comparte fuera de banda, así que no hay
  nada a lo que escalar, y mezclarlo con uno entregado pondría dos custodias distintas en un mismo
  slot.
- Una lista de **uno** admite lo mismo que admitía `access_method`. Por eso ningún sobre ya redactado
  cambia de significado.
- **No se puede repetir** un método. No es cosmético: cada miembro lleva su propio presupuesto de
  envíos, así que `["OTP_EMAIL","OTP_EMAIL"]` se leería como una declaración y gastaría dos.
- **El orden importa.** El primero es el que se ofrece y —en el modo por defecto— el que **se envía**.
  En SMS eso es dinero.
- Cada miembro tiene que ser un método que este despliegue tenga cableado (422
  `AUTH_METHOD_UNAVAILABLE`) **y** que ese destinatario pueda recibir de verdad (422
  `RECIPIENT_CANNOT_RECEIVE_METHOD`).

⚠ **Lo segundo se comprueba MIEMBRO A MIEMBRO, y es el cambio que más se va a notar en el
dashboard.** Declarar `["OTP_EMAIL","OTP_SMS"]` a alguien sin teléfono se rechaza aunque el email
esté perfecto. En la práctica: **hay que recoger un teléfono antes de poder ofrecer SMS como
alternativa**, y el formulario debería pedirlo en el mismo paso en que se añade el segundo método,
no después.

### Lectura — `GET /api/v1/envelopes/{id}`

El bloque `auth` de cada destinatario gana dos claves y **conserva las tres que ya tenía**:

```
auth: {
  access_method,    // sin cambios: ahora es la CABEZA de la lista, o null
  access_methods,   // NUEVO: la lista entera, en orden. [] si la puerta está abierta
  signing_method,   // sin cambios: la cabeza, o null
  signing_methods,  // NUEVO: la lista entera. [] si no se pide nada al firmar
  hard_locked       // sin cambios
}
```

⚑ **El escalar es DERIVADO de la lista, no un segundo campo almacenado**, así que los dos no pueden
contradecirse. Por eso es seguro mantenerlo: un cliente que no sepa nada de listas sigue leyendo lo
que leía. Su retirada está anotada como pendiente en
[TASK-032](../tasks/TASK-032-ordered-auth-method-list.md) §7 — no la hagáis vosotros, avisaremos.

⚑ **`[]` es la lista vacía y se publica siempre, nunca `null` ni ausente.** «No se pide nada» es una
de las respuestas, no una clave que haya que interpretar por su ausencia.

## Lo que el frontal tiene que hacer

**Dashboard**

1. Aceptar `access_methods` / `signing_methods` en los tipos de respuesta. Si solo pintáis un método,
   `access_method` os sigue sirviendo y no hay nada urgente.
2. Para *ofrecer* alternativas: mandar el plural en la autoría, y **no** mandar el singular a la vez.
3. Recoger el teléfono en el mismo formulario donde se declare `OTP_SMS`, o el 422 llegará al pulsar
   guardar con el número en otra pantalla.
4. El orden de la lista es el que teclea el remitente: si la UI lo deja reordenar, ese orden es la
   declaración, no una preferencia de visualización.

**Signer**

Nada obligatorio todavía — ver la sección siguiente.

## La ceremonia — aterrizada el 2026-08-21 en `1bab9ee`

⚠ **Esta sección REEMPLAZA a la que decía «lo que NO está listo todavía».** Aquella listaba tres
cosas pendientes y os pedía no construir la pantalla de elección contra el descriptor de entonces;
dos de las tres ya están, y la clave que las alimenta se llama **`methods`**.

### 1. `GET /api/v1/signing/session/auth` gana `methods`

Una entrada **por método declarado, la cabeza incluida**, en el orden del remitente:

```json
{ "gate": "ACCESS", "method": "OTP_EMAIL", "code_length": 6,
  "masked_destination": "a**@example.com",
  "methods": [
    { "method": "OTP_EMAIL", "masked_destination": "a**@example.com", "code_length": 6 },
    { "method": "OTP_SMS",   "masked_destination": "+34 ·······56",   "code_length": 6 }
  ],
  "access_gate": { "method": "OTP_EMAIL", "code_length": 6,
                   "masked_destination": "a**@example.com", "methods": [ … ] },
  "document_title": "…", "locale": null }
```

⚠ **`methods` es incondicional**: sale también para una puerta de un solo método, donde repite lo que
`method` ya dice. Un campo que aparece y desaparece es un campo que hay que proteger en cada lectura.
Y `methods: []` cuando `gate` es `null`.

⚑ **`method` (el plano) pasa a ser *el que está en vigor*, no *el primero declarado*.** Si el firmante
ha elegido SMS, `method` dice `OTP_SMS` y `masked_destination` / `code_length` van con **ese** método.
El orden de `methods` sigue siendo el del remitente y no cambia con la elección.

`access_gate.methods` es la misma lista para **la puerta**, que es de donde debe pintar el modal de
re-autenticación y la pantalla de recuperación.

### 2. `POST /api/v1/signing/session/auth/otp/send` gana `method` (opcional)

⛔ **Omitirlo es exactamente el comportamiento de hoy.** Mandarlo es *elegir*:

- **elegir MINTEA** — el código que ya está en la bandeja **deja de valer** y sale uno nuevo por el
  canal nombrado. No lo mandéis en el montaje del componente si el valor viene de estado del cliente
  y no de un click: es la misma trampa que `resend: true`;
- ⚑ **salvo que nombréis el método que YA está vivo**, que es un *ensure*: no se mintea nada y el
  código de la bandeja sigue valiendo. Un re-montaje que repite la elección es seguro;
- **el cooldown es de la PUERTA, no del método** — elegir dentro del intervalo devuelve el mismo
  **429 `OTP_SEND_COOLING_DOWN`** que un re-envío, con el mismo `retry_at`. ⚑ Ese instante es
  `next_resend_at`, el que ya recibís: *el momento en que se puede re-enviar y el momento en que se
  puede elegir son el mismo*. No pintéis un segundo reloj;
- **un método que la puerta no declara es un `409 AUTH_METHOD_NOT_DECLARED`**, nunca un envío
  silencioso por la cabeza. Leed la lista de `methods`, no la adivinéis.

### 3. La elección es PEGAJOSA y es de servidor

Elegir SMS y volver a pedir código lo manda por SMS, durante el resto de la ceremonia y **también
después de un `AWAITING_REAUTH`** (ADR-0054 §2.6). No transportéis nada en el cliente: el modal de
re-autenticación hereda el canal solo, que es justo lo que el aviso (b) de más abajo pedía.

⚑ **Se traslada a la puerta de firma solo si esa puerta declara el mismo método** (§2.7). Las dos
listas son declaraciones independientes: un firmante que eligió SMS en la puerta y cuya puerta de
firma solo declara `OTP_EMAIL` recibe el código del acto **por correo**, y pedir SMS ahí es un 409.

### 4. `auth_status.method_used` pasa a ser lo que se PROBÓ

En `GET /api/v1/signing/session`. Antes salía de la declaración; ahora sale de la sesión. Para un
destinatario declarado `[OTP_EMAIL, OTP_SMS]` que eligió SMS, `method_used` dice `OTP_SMS` mientras
`auth_requirements[].method` sigue diciendo `OTP_EMAIL`. **No es una contradicción**: uno dice *qué
pasó* y el otro *qué se pidió*. No derivéis uno del otro.

### 5. `selection` — el MODO DE PRESENTACIÓN, aterrizado el 2026-08-21

⚑ **Esta sección sustituye a lo que este documento decía antes**, que era: *«no hay elección libre y
no hay dónde pedirla, así que no pintéis un selector que no envíe nada hasta que el firmante elija —
esa pantalla todavía no tiene backend»*. Ya lo tiene. La forma es la que acordamos con vosotros el
2026-08-21 y es la que está implementada, no una propuesta.

#### 5.1 En el descriptor: `selection`, DENTRO DE CADA BLOQUE de puerta

`GET /api/v1/signing/session/auth` publica `selection` **junto a `methods` en el objeto raíz** (la
puerta viva) **y dentro de `access_gate`**. Es **`required`** en los dos, como los otros cinco
miembros: nunca falta, nunca es `null`.

- Valores: `"ESCALATION"` | `"FREE_CHOICE"`. **En mayúscula, como `gate`, `method` y todo lo demás de esa ruta** — una sola caja en las dos superficies, así que un cliente que lea ambas conmuta sobre un único vocabulario. ⚠ Este documento dijo lo contrario durante unas horas: propuse minúscula sin mirar a sus vecinos y se confirmó sin mirarlos tampoco. Lo tumbó una medición vuestra —en `types.ts` toda unión de wire es mayúscula y toda minúscula es estado de cliente—, así que un `FREE_CHOICE` habría mentido sobre su procedencia.
  asimetría es deliberada: la superficie del firmante usa esta grafía y la del remitente la otra.
- ⚑ **Hoy los dos bloques llevan el MISMO valor**, porque el modo es del **destinatario**, no de la
  puerta. Se publica por bloque de todas formas para que el control de recuperación no tenga que mirar
  a otro sitio para saber su propio modo, y para que un modo por puerta más adelante no obligue a
  cambiar la forma.

**Qué hace vuestra pantalla con cada valor:**

- `"ESCALATION"` — lo de siempre. Al montar, llamáis a la ruta de envío sin cuerpo y sale un código
  para `method`; las demás entradas de `methods` se ofrecen a partir de `next_resend_at`.
- `"FREE_CHOICE"` — **NO se ha enviado nada y no se enviará hasta que el firmante elija.** Pintad
  primero el selector con `methods`. Hasta que elija **no hay código, no hay `code_expires_at` y no
  hay `next_resend_at`**: no dibujéis reloj. Cuando elija, mandáis su `method` a la ruta de envío y a
  partir de ahí la pantalla se comporta como en escalado.
- ✅ **Cambiar de método durante el enfriamiento sigue permitido** (el enfriamiento es de la *puerta*,
  §2.8), así que el selector se queda visible mientras corre el reloj. No lo escondáis ni lo
  deshabilitéis.

#### 5.2 En autoría: `auth.selection`, opcional, por destinatario

`POST /api/v1/envelopes/{id}/recipients` acepta `auth.selection` con `"ESCALATION"` | `"FREE_CHOICE"`
(**mayúsculas aquí**). Omitirlo es `ESCALATION`, que es lo que hace todo el mundo hoy, así que un
cliente que no lo mande no cambia de comportamiento. `GET /api/v1/envelopes/{id}` lo devuelve en el
bloque `auth` de cada destinatario, siempre presente. **No hay endpoint que lo cambie después**: se
declara una vez, al añadir al destinatario, porque decide qué método puede acabar en la evidencia de
una firma ya en curso.

#### 5.3 ⛔ ORDEN DE DESPLIEGUE DEL 409 — leedlo antes de habilitar nada

**El código `AUTH_METHOD_NOT_CHOSEN` (409) ya está publicado, y hoy es INALCANZABLE a propósito.**
`POST …/auth/otp/send` **sin** `method`, sobre un destinatario en `FREE_CHOICE` que todavía no ha
elegido, responde `409 AUTH_METHOD_NOT_CHOSEN`.

> ⛔ **EL ORDEN ES: (1) se publica el código en el backend → (2) la app de firma lo declara y lo trata
> → (3) solo entonces alguien puede habilitar la elección libre.** Vuestra navegación manda cualquier
> 4xx **no declarado** a `/invalid`, así que un `AUTH_METHOD_NOT_CHOSEN` sin declarar le diría a un
> firmante con un enlace perfectamente bueno que su enlace no vale. Ya tenéis dos cicatrices de
> exactamente eso.

⚠ **Son DOS las superficies que llaman a la ruta 4 al montarse, y las dos tienen que declararlo:**
**`OtpAuth`** (la pantalla de autenticación) y **`ReauthModal`** (el modal de re-autenticación sobre
`/sign`). La segunda es la que se olvida: se monta en otra pantalla, a veces tras una recarga, y llama
a la misma ruta. Si solo lo declara la primera, el firmante en `FREE_CHOICE` que vuelve tras una
expiración por inactividad acaba en `/invalid`.

⚑ **Mientras tanto nadie puede llegar a ese 409**: ningún cliente de autoría manda todavía
`auth.selection`, así que no hay destinatarios en `FREE_CHOICE`. Ésa es exactamente la ventana en la
que os toca declararlo, sin prisa y sin riesgo.

### Lo que sigue SIN estar

- **El nivel de tenant para el modo** — [`BL-120`](../BACKLOG.md). El modo existe y se declara **por
  destinatario, en cada `POST …/recipients`**; lo que no existe es un sitio donde fijar el valor por
  defecto de un tenant. Si queréis que una organización entera vaya en elección libre, hoy hay que
  mandarlo destinatario a destinatario desde el cliente de autoría.

- ⛔ **El control de autoría en `f5sign-dashboard`** — no existe (medido el 2026-08-21: ese repo no
  menciona `access_method` ni `signing_method` en ningún sitio), y es el **primer eslabón de la
  cadena**: sin él ningún remitente puede declarar ni la lista ni el modo, así que `FREE_CHOICE` es
  hoy inalcanzable en producción aunque el backend ya lo sirva. ⚑ Es también la razón por la que el
  signer dejó su pantalla de elección **sin montar** (`ffaa0db`) — una decisión suya y correcta, no
  un olvido: cablearla ahora cambiaría lo que `auth.vue` y `ReauthModal` hacen al montar, sin ninguna
  forma de ejercitar el camino nuevo de punta a punta.

El estado real está en [TASK-032](../tasks/TASK-032-ordered-auth-method-list.md) — su tabla de
cabecera dice qué se construyó y qué queda, y es lo que hay que mirar, no este campo `Status`, que es
de mantenimiento manual (ver el README de este directorio).

## Lo acordado con `f5sign-signer` el 2026-08-20 — tres cosas fijadas antes de construirlas

Revisado con esa sesión **antes** de publicar el contrato, que es cuando cambiarlo es barato. Las tres
quedan fijadas aquí para que no se re-decidan por el camino:

1. ⛔ **La lista del descriptor incluirá LA CABEZA, no solo las alternativas.** Publicar «las otras»
   obligaría a la pantalla a recomponer la fila actual empalmando los campos planos (`method`,
   `masked_destination`, `code_length`) con la lista — **dos fuentes para una misma fila**, que
   divergen en cuanto una cambie. Con la lista completa, los campos planos siguen siendo lo que ya
   son: el atajo del caso común, no una pieza que haya que reensamblar.
2. **Forma: lista de objetos `{method, masked_destination, code_length}`**, no un mapa indexado por
   método. El orden es una declaración del remitente y un mapa lo pierde; además un mapa hace
   irrepresentable el duplicado (`OTP_EMAIL` al correo personal y al del trabajo), que hoy **está
   refusado** por otra razón —cada miembro lleva su propio presupuesto de envíos— pero que la forma
   de lista deja abierto sin obligar a decidirlo ahora.
3. **Mismos tipos que ya pintan**: `masked_destination` string enmascarado **en servidor**, y
   `code_length` entero **nullable** con la misma semántica de hoy — `null` significa *no se puede
   saber*, nunca *no hay código*.

### ⛔ Dos avisos que vienen del signer y que hay que dejar por escrito

**(a) El `method` opcional en la ruta de envío es una REAPERTURA DELIBERADA, no una regresión.**
Hoy el signer **borra** ese campo del body a propósito (`SigningApi.real.ts`), con el motivo escrito
al lado: comprobaron contra el backend real que mandar un `method` equivocado se procesaba igual, así
que enviarlo *sugería que el cliente elige el canal, siendo falso*. Esa decisión era **correcta
entonces** y deja de serlo cuando el campo exista de verdad y esté validado contra la lista declarada.
⚠ Sin esta nota, alguien —ellos incluidos— lo «arreglará» quitándolo otra vez.

**(b) Hay una TERCERA superficie de canje: el modal de re-autenticación** (`ReauthModal.vue`), que se
monta sobre `/sign`, en otra pantalla y a veces tras una recarga. ✅ **La pegajosidad de la elección es
de SERVIDOR** (ADR-0054 §2.6: vive en la fila de la sesión y sobrevive a `AWAITING_REAUTH`), así que
ese modal **hereda el canal solo** y el cliente no tiene que transportar nada. Si fuera cosa del
cliente, ése es justo el sitio donde se perdería.

### ⛔ (c) AVISO DE ORDEN DE DESPLIEGUE — leedlo antes de adoptar el plural

**Un despliegue del backend anterior a este cambio NO rechaza `access_methods`: lo TIRA en silencio y
responde `201`.** Medido contra el stack, no razonado — un `POST …/recipients` con
`auth.access_methods` devolvió **201** y la fila quedó con `{"access_method": null, "signing_method":
null}`. El `phone` desapareció igual.

⚠ **Para un cliente ése es el peor resultado posible**, y es peor que un 422: creéis que habéis
exigido SMS y el destinatario tiene **la puerta abierta**, sin error en ningún sitio. Es una
declaración de seguridad decorativa que nadie manda.

⚑ **La causa no es este campo**: ningún DTO de esta API rechaza campos desconocidos —
`#[MapRequestPayload]` los descarta por defecto y no hay estrictez configurada— así que le pasa a los
20 endpoints por igual. Lo que cambia aquí es que el campo tirado es **de autenticación**. Queda como
[`BL-177`](../BACKLOG.md), con cuatro opciones y sin elegir: cerrarlo globalmente rompe contrato
publicado y es una decisión de nivel ADR.

▶ **La regla barata, y es la que os sirve si NO hacéis relectura.** Propuesta por
`factor5_dashboard_sf`, que es quien encontró el fallo:

> **No adoptéis un campo hasta que el `doc.json` del despliegue que os sirve lo publique.**

⚑ **Se comprueba UNA VEZ, antes de escribir código**, en lugar de en cada llamada y para siempre — y
sobre todo **es verificable por el cliente**, al contrario que la precondición de orden de despliegue,
que nosotros mismos anotamos arriba como algo que nadie puede comprobar. Una precondición que nadie
puede comprobar no es un control; ésta sí. Es exactamente como ellos pillaron que `access_methods`
estaba ausente.

⚠ **Y una advertencia sobre cómo comprobarlo**, que también es suya y que casi les cuesta una falsa
alarma: **buscar el nombre como subcadena en el `doc.json` no vale.** `selection` casa dentro de la
descripción en prosa de otro esquema. Comprobad que es una **propiedad real de un esquema**, no que
la palabra aparezca. Una comprobación laxa devuelve un positivo tranquilizador, y los positivos
tranquilizadores no se investigan.

▶ **La otra regla, para quien SÍ relee:** no adoptéis `access_methods` hasta que la
**lectura os lo devuelva**. Es decir: mandadlo, leed el sobre con `GET …/envelopes/{id}` y comprobad
que `access_methods` vuelve con lo que mandasteis. Si vuelve `[]` con `access_method: null`, ese
backend no conoce el campo y acabáis de crear un destinatario sin puerta. ⛔ Los pasos 1 y 5 de la
verificación de abajo **pasan igual** contra un backend pre-despliegue; el 2 es el único que muerde,
y solo porque hace esa lectura de vuelta.

### ⛔ El STATUS no basta en esta API: el dato es el `code`

Aportado por `factor5_dashboard_sf` el 2026-08-21, midiendo el despliegue — y casi les cuesta una
falsa alarma **en la dirección contraria** a la del 201 silencioso:

```
ANTES : 422 AUTH_METHOD_UNAVAILABLE          ← el método no está cableado
AHORA : 422 RECIPIENT_CANNOT_RECEIVE_METHOD  ← el método SÍ está; ese destinatario no puede recibirlo
```

**Mismo status, otro código, significados opuestos.** Quedarse en el `422` habría concluido que el
despliegue no hizo nada, cuando lo que había pasado es que la primera comprobación ya se pasa y falla
la segunda — que es justo lo que esta task añadió.

⚑ Es la simétrica del otro fallo del día: por la mañana **un 201 tapaba un fallo**, por la tarde **un
422 tapaba un éxito**. En ninguno de los dos casos el status decía la verdad.

▶ **Ramificad siempre sobre `code`, nunca sobre el status a secas.** Y si comparáis un antes con un
después, comparad códigos: dos `422` idénticos pueden ser dos mundos distintos.

## Cómo verificarlo desde el frontal

1. `POST …/recipients` con `auth: { access_methods: ["OTP_EMAIL","OTP_SMS"] }` sobre un destinatario
   **sin** teléfono → **422 `RECIPIENT_CANNOT_RECEIVE_METHOD`**, y el mensaje nombra `OTP_SMS`, no el
   slot a secas.
2. El mismo cuerpo sobre un destinatario **con** móvil → **201**, y `GET …/envelopes/{id}` devuelve
   `access_methods: ["OTP_EMAIL","OTP_SMS"]` con `access_method: "OTP_EMAIL"`.
3. `auth: { access_method: "OTP_EMAIL", access_methods: ["OTP_EMAIL"] }` → **422**, las dos grafías a
   la vez.
4. `auth: { access_methods: ["OTP_EMAIL","ACCESS_CODE"] }` → **422**: `ACCESS_CODE` no puede estar en
   una lista de más de uno.
5. Un destinatario ya existente, declarado antes de este cambio, sigue devolviendo exactamente el
   mismo `access_method` que devolvía — y ahora además `access_methods` con ese único miembro, y
   `selection: "ESCALATION"`.
6. `auth: { access_methods: ["OTP_EMAIL","OTP_SMS"], selection: "FREE_CHOICE" }` → **201**, y
   `GET …/envelopes/{id}` devuelve `selection: "FREE_CHOICE"` en el bloque `auth`. ⚠ La misma regla de
   la lectura de vuelta del aviso (c) aplica aquí: si vuelve `"ESCALATION"`, ese backend no conoce el
   campo y acabáis de crear un destinatario en escalado creyendo lo contrario.
7. Sobre ese destinatario, `GET …/signing/session/auth` → `selection: "FREE_CHOICE"` **en la raíz y
   dentro de `access_gate`**, y `POST …/auth/otp/send` con cuerpo vacío → **409
   `AUTH_METHOD_NOT_CHOSEN`**, sin que se haya enviado nada. Con `{"method":"OTP_SMS"}` → **200** y el
   código sale por SMS.
8. El mismo par de llamadas sobre un destinatario en `ESCALATION` → `selection: "escalation"` y la
   segunda llamada devuelve **200** con `minted: true`. Es el caso que distingue los dos modos; sin él,
   el 7 podría estar pasando por cualquier otra razón.

La forma exacta de cada esquema está en el OpenAPI que genera Nelmio, que es la verdad legible por
máquina; aquí no se copia a propósito.
