# Traspaso al frontal — el sobre puede pedir una prueba en la puerta: abrir el enlace deja de garantizar credencial

<!-- OFFREPO: los hechos del lado cliente que se citan aquí —que `SigningApi.real.ts` ya declara provisionalmente
las dos rutas `…/session/auth`, y que la recuperación por inactividad del signer es *renovación rechazada →
reabrir con el enlace → seguir*— vienen de `f5sign-signer`, que no es alcanzable desde un checkout sólo-backend.
Los confirmó la sesión que trabajaba en ese repo el 2026-08-18 y están reescritos en línea donde se usan, así que
nada de este documento exige tener ese repo delante. -->

| | |
|---|---|
| **Origen** | rama `feat/two-gate-signer-auth` · **slice de backend terminada y en verde**, NO mergeada, sin PR y sin subir a `origin` · commit al escribir esto: `fcea368`. ⚠ La primera versión de este documento fijaba `2ef3eb5`, que era la foto de mitad de slice: veinticuatro commits después, nueve de sus afirmaciones habían dejado de ser ciertas. Está reescrito entero |
| **Fecha** | 2026-08-19 · reescritura completa del original del 2026-08-18 |
| **Repos afectados** | **signer** únicamente. La mitad del remitente (declarar la puerta, regenerar el código, levantar el bloqueo) es API de integrador bajo `MACHINE_KEY` y no toca ninguna ruta del signer |
| **Naturaleza** | **aditivo en la forma, y rompe el contrato en un punto concreto.** No desaparece ningún campo y no cambia el tipo de ninguno: lo que cambia es que **tres miembros de la respuesta de apertura pasan a ser condicionales**, y con ellos deja de funcionar vuestra recuperación por inactividad para los sobres con puerta declarada |
| **Acción requerida** | **manejar un estado nuevo** (`AUTH_PENDING`) en la apertura · **separar las dos uniones de `status`**, que no son la misma (§2) · **recablear el enrutado de errores contra la tabla de §5 con los nombres de hoy**: `AUTH_GATE_NOT_DECLARED` ya no existe *y su condición cambió de código* · manejar **dos 401 nuevos en el commit** que no se arreglan renovando (§7) · separar 423 de 429 · leer la sección ⛔ de abajo antes de tocar la recuperación por inactividad |
| **Status** | Pending en el frontal — nadie ha aplicado nada todavía. En el backend: **completo y en verde en la rama**, ni mergeado ni desplegado. La última medición registrada es sobre `0da4915` — 1867 tests, 0 fallos, 0 *skips* — y después han entrado tres commits, dos de ellos de pruebas: el número de hoy es mayor y no se ha vuelto a medir para escribir esta fila. Lo de §«Lo que cambió en el contrato» está commiteado, servido por rutas reales y cubierto por una prueba de aceptación que conduce la ceremonia entera sobre HTTP |

> ⛔ **El punto que va primero porque no lo vais a descubrir vosotros hasta que os muerda.**
>
> Vuestra recuperación por inactividad es *renovación rechazada → reabrir con el enlace del correo →
> seguir*. Funciona porque hasta hoy **abrir el enlace acuñaba un par de credenciales siempre, sin
> preguntar nada**. A partir de esta slice el acuñado es **condicional**: si el remitente declaró una
> puerta de acceso para ese destinatario, reabrir el enlace devuelve **200**, sin credencial, con
> `status: "AUTH_PENDING"`.
>
> Vuestra ruta de recuperación **no falla: se queda a medias**. La llamada sale bien, y el cuerpo no trae
> la credencial que el código de después da por hecha.
>
> ⚠ **Y los sobres neutros —que son todos los que existen hoy, y todos los de vuestras pruebas— siguen
> comportándose exactamente igual.** Por eso hay que contarlo en vez de dejar que se descubra: en manual
> testing no se ve.

## Lo que cambió en el contrato

Las formas exactas están en el spec (`GET /api/doc.json`) **cuando esto aterrice**, y ahí manda el
documento generado, no este traspaso.

⚑ **Corrección respecto a la versión anterior de este documento:** decía que el spec «todavía describe
el mundo anterior en el endpoint de apertura» y que en ese endpoint mandaba este traspaso. Eso fue cierto
hasta el 2026-08-19; las anotaciones `#[OA\*]` de la apertura, del descriptor y del envío describen ya
este mundo, así que **la excepción se retira: manda el spec en todas partes**.

Todo lo de esta sección está **commiteado y no se mueve**.

### 1. `POST /api/v1/signing/session` puede devolver un cuerpo sin credencial

Hasta hoy la apertura devolvía siempre siete miembros. A partir de ahora devuelve **cuatro o siete**:

| | Puerta de acceso **abierta** (todo lo existente) | Puerta de acceso **declarada** |
|---|---|---|
| `session_id`, `envelope_id`, `recipient_id` | ✅ | ✅ |
| `status` | `"AUTH_PASSED"` | `"AUTH_PENDING"` |
| `access_credential` · `refresh_credential` · `expires_at` | ✅ | ⛔ **no están** |

⛔ **No están: no vienen a `null`.** Los tres miembros **se omiten del objeto**, y eso es una decisión, no
un detalle de serialización. Un cliente que ramifica sobre *presencia* no puede confundir «retenida» con
«caducada», que son dos situaciones con dos remedios opuestos —pasar la puerta contra renovar—. Y un
cliente que ignorase el `status` falla ruidosamente al leer una clave que no existe, en vez de mandar
`Bearer null` y leer el 401 resultante como un fallo del servidor.

Traducido a vuestro tipado: los tres miembros pasan a ser **opcionales**, y el discriminante es `status`.

⚑ **Y esta ruta declara ahora un `404` que no declaraba** (desde el 2026-08-19). Es alcanzable, no
teórico: acuñar un token de firma **no valida ni el sobre ni el destinatario**, así que se puede tener un
token perfectamente válido que no nombra nada. Además la apertura lee ahora el requisito declarado del
destinatario para decidir si acuña, de modo que un sobre inexistente —o un destinatario que no está en
él— colapsa a 404 exactamente igual que en el read-model y en el commit. Tratadlo como «este enlace no
corresponde a nada», nunca como un fallo transitorio que reintentar.

### 2. Hay **dos** `status` en el cable, y no son la misma unión

⚠ **Esto es la corrección más silenciosa de la reescritura.** La versión anterior entregaba **una sola**
unión de cinco miembros —`INITIATED · AUTH_PENDING · AUTH_PASSED · AWAITING_REAUTH · COMPLETED`— y
omitía `DECLINED`. Esa es la unión del **enum interno del backend**, no la del cable: tal cual, os hace
escribir ramas del read-model que no pueden dispararse nunca y os deja sin la única que sí llega.

**Unión A — la de la ceremonia de autenticación:**

- `POST /api/v1/signing/session` (apertura): `"AUTH_PASSED"` | `"AUTH_PENDING"`.
- `POST /api/v1/signing/session/auth` (envío del código): `"AUTH_PASSED"` y nada más — un rechazo aquí es
  un `problem+json`, no un `status` distinto.

**Unión B — la del read-model y el acto:**

- `GET /api/v1/signing/session`: `"AUTH_PASSED"` | `"COMPLETED"` | `"DECLINED"`.
- `POST /api/v1/signing/commit` (200): `"COMPLETED"` y nada más.

Tres consecuencias que hay que tipar bien:

- **`DECLINED` es el miembro que faltaba.** Sale del *outcome* del destinatario, no del estado de sesión.
  ⚠ Hoy **no hay ruta que lo produzca** —el rechazo no está construido en el lado de escritura— pero está
  publicado en el esquema y el frontal ya lo tipa: dejadlo en la unión B, y no lo esperéis en la A.
- **`INITIATED` y `AWAITING_REAUTH` no cruzan el cable en ningún cuerpo.** Son estados del agregado. No
  los pongáis en un `Record<SessionStatus, …>` alimentado desde una respuesta HTTP: esa rama no se
  ejecutará jamás.
- **`AWAITING_REAUTH` se os manifiesta como un `401` con `code: "AUTH_REAUTH_REQUIRED"`**, no como un
  `status`. Es la señal, y es la que enruta a vuestra pantalla de re-autenticación.

⚑ **`AWAITING_REAUTH` sí es alcanzable desde el 2026-08-19**, aunque no lo veáis como estado: un
destinatario **con puerta declarada** que vuelve a su enlace después de que la credencial de renovación
haya caducado es expulsado a ese estado en la propia apertura. Es la única petición que puede llegar a
una sesión cuya concesión ha expirado —todo lo demás se rechaza antes, en el borde—, así que ahí vive la
transición. Lo que vosotros veis es la apertura respondiendo `AUTH_PENDING`: hay que volver a pasar la
puerta de **acceso**.

⚠ **`AWAITING_REAUTH` y la caducidad de la credencial son cosas distintas**, y confundirlas manda al
usuario a la pantalla equivocada. La credencial caducada se arregla renovando (TASK-029, ya desplegado);
`AWAITING_REAUTH` no se arregla renovando — hay que volver a pasar la puerta de acceso. Nunca la de firma.

### 3. `AuthMethod` llega entero: catorce miembros

No crece slice a slice: el catálogo aterriza completo para que vuestra unión no tenga que ampliarse otras
tres veces.

`DIRECT_LINK` · `ACCESS_CODE` · `OTP_SMS` · `OTP_EMAIL` · `OTP_WHATSAPP` · `OTP_VOICE` ·
`DEVICE_BIOMETRIC` · `FIDO2_WEBAUTHN` · `DNIE_NFC` · `EUDI_WALLET` · `USER_CERTIFICATE` · `BANK_ID_PSD3` ·
`VIDEO_KYC_ASYNC` · `CLAVE`

Ese mismo enum de catorce se publica hoy en los tres sitios donde un método cruza el cable: en
`auth_requirements[].method` del read-model, en `auth_status.method_used`, y en el `method` del
descriptor. ⚑ Este último **se publicaba como cadena suelta hasta el 2026-08-19** —lo que no os dejaba
`switch`ear sobre nada—; ya no.

Dos avisos para que no dibujéis catorce pantallas:

- ⚑ **Sólo `ACCESS_CODE` es ejecutable en este despliegue hoy.** Qué métodos puede correr una instalación
  es una capacidad con adaptador por despliegue, y el de hoy declara disponible únicamente `ACCESS_CODE`:
  un remitente que intente declarar `OTP_SMS` es rechazado al autorar con **422 `AUTH_METHOD_UNAVAILABLE`**,
  no descubierto por un firmante. Los otros doce están en la unión para que el tipo no se mueva, no
  porque vayan a llegaros mañana.
- ⚠ **`DIRECT_LINK` no es declarable**, ni en la puerta de acceso ni en la de firma: es el método que una
  ceremonia **registra haber ejecutado** cuando no había puerta. Lo vais a ver como valor de salida, nunca
  como algo que un remitente eligiera. ⚑ **2026-10-20, [ADR-0082](../adr/ADR-0082-the-access-gate-is-always-declared.md):** en la puerta de acceso sí se declara al añadir un destinatario — es como se escribe la puerta abierta, y omitirla es 422 (ver [TASK-063](TASK-063-dashboard-access-gate-always-declared.md)); en la de firma sigue rechazado, y en lectura una puerta abierta sigue saliendo como `[]` / `null`.
- ⛔ **No hay orden de fuerza definido entre los catorce**, y no lo infiráis vosotros. `(DNIE_NFC,
  ACCESS_CODE)` es una pareja **válida** por mucho que parezca rara: el backend no compara fuerzas.

### 4. Dos rutas nuevas, en el path que ya teníais escrito

| Ruta | Método | Para qué | Qué credencial pide |
|---|---|---|---|
| `/api/v1/signing/session/auth` | **GET** | ¿Qué puerta tengo delante? | **token del correo** |
| `/api/v1/signing/session/auth` | **POST** | Enviar el código → devuelve la credencial | **token del correo** |

Son exactamente los paths que vuestro `SigningApi.real.ts` ya declara de forma provisional: **se sirven, no
se inventan**. Y las dos toman el **token del correo**, no la credencial de sesión, porque la regla de la
partición es *«¿tiene esta ruta un propósito legítimo antes de que el firmante teclee el código?»* — y en
ese momento no puede existir ninguna credencial que presentar.

El GET existe para que dejéis de deducir el requisito del read-model: esa ruta pide credencial, que es
justo lo que todavía no tenéis. **Se puede llamar antes incluso de abrir la sesión**, nada más aterrizar
en el enlace.

**Qué publica el GET, exactamente — cinco miembros y ni uno más** (el conjunto está cerrado y hay una
prueba que redea si aparece un sexto):

| Miembro | Valor |
|---|---|
| `gate` | `"ACCESS"` mientras la puerta de acceso está sin pasar · `"SIGNING"` una vez pasada, si hay puerta de firma declarada · `null` cuando no se pide nada (destinatario neutro, o ceremonia ya terminada) |
| `method` | uno de los catorce de §3; `null` cuando `gate` es `null` |
| `masked_destination` | **siempre `null` en esta slice** — `ACCESS_CODE` no se entrega por ningún canal, así que no hay destino que enmascarar. Se publica ya para que vuestra forma no cambie cuando TASK-022 dé canal a un método |
| `document_title` | qué está desbloqueando el firmante |
| `locale` | el idioma declarado del destinatario, o `null` si nadie declaró ninguno — caed a vuestro propio idioma por defecto, **no** leáis una elección en la ausencia |

⚑ **`document_title` y `locale` no estaban en la versión anterior de este documento**, que enumeraba tres
miembros y decía «nada más». Se añadieron con la enmienda del 2026-08-18 a la cláusula de divulgación y
ya se sirven. La razón es la que os afecta directamente: bajo `AUTH_PENDING` el read-model está **detrás**
de la puerta, así que cuando pintáis la pantalla de autenticación **no tenéis nada**. Una caja de código
en una página en blanco, en el idioma equivocado y sin nombrar nada, es indistinguible de una página de
phishing — justo en la pantalla donde eso cuesta más caro.

⛔ **Y lo que el descriptor no lleva, dicho para que no lo pidáis dos veces.** `sender_name` y
`sender_organization` están deliberadamente ausentes y no se pueden «añadir sin más»: uno vive detrás de
un esquema al que el rol de la aplicación no tiene acceso, y el otro no tiene fuente ninguna hoy. Y
**nunca el verificador**: ni hash, ni código, ni cuenta de intentos.

### 5. Los códigos de error, el corte 423 / 429, y el `Retry-After` que por fin podéis leer

| Situación | Dónde llega | Status | `code` en el problem+json |
|---|---|---|---|
| Código incorrecto | `POST …/session/auth` | **401** | `AUTH_CODE_INCORRECT` |
| El desafío caducó | `POST …/session/auth` | **401** | `AUTH_CHALLENGE_EXPIRED` |
| No hay ningún desafío abierto | `POST …/session/auth` · `POST /signing/commit` | **401** | `AUTH_NO_OPEN_CHALLENGE` |
| La concesión de acceso se quedó inactiva: repetir la puerta de acceso | `POST …/session/auth` · `POST /signing/commit` | **401** | `AUTH_REAUTH_REQUIRED` |
| **Puerta declarada sin verificador** — el remitente se equivocó al autorar | `POST …/session/auth` | **401** | `AUTH_GATE_MISCONFIGURED` |
| **Bloqueo duro** — sólo el remitente lo levanta | `POST …/session/auth` | **423** | `AUTH_HARD_LOCKED` |
| **Enfriamiento** — se suelta solo | `POST …/session/auth` | **429** + `Retry-After` | `AUTH_COOLING_DOWN` |
| Sobre anulado · sesión ya completada | `POST …/session/auth` · `POST /signing/commit` | **409** | `CONFLICT` |
| Desafío de firma que no autoriza este conjunto de documentos | `POST /signing/commit` | **409** | `CONFLICT` |

El cuerpo es `application/problem+json` con `type` (`about:blank`), `title`, `status`, `code` y `detail`.
**Discriminad por `status` + `code`, nunca por el texto de `detail`.**

> ⛔ **`AUTH_GATE_NOT_DECLARED` ya no existe, y esto NO es un renombrado cosmético: cambió también de
> significado.** Si cableasteis vuestro enrutado contra la tabla de la versión anterior, hay que mover
> **dos** cosas, no una.
>
> - **La cadena.** `AUTH_GATE_NOT_DECLARED` estuvo vigente hasta el 2026-08-19 y hoy no se emite en
>   ninguna ruta; el código es `AUTH_GATE_MISCONFIGURED`.
> - **El significado, que es la parte cara.** La fila vieja describía *«enviáis a una puerta que ese sobre
>   no declara»*. Esa condición **ya no produce este código**: enviar contra una puerta que no está
>   abierta no encuentra desafío y se rechaza mucho antes con `AUTH_NO_OPEN_CHALLENGE`. Lo que
>   `AUTH_GATE_MISCONFIGURED` significa hoy es otra cosa: **una puerta declarada para la que no hay
>   verificador en ninguna parte** — por ejemplo un `ACCESS_CODE` cuyo destinatario no tiene hash de
>   código. Es una **misconfiguración del remitente**, y el firmante no la resuelve reintentando.
>
> ⚠ **Enrutar el nombre nuevo a la pantalla vieja es peor que no manejarlo.** La pantalla correcta para
> `AUTH_GATE_MISCONFIGURED` dice *«pide al remitente que restablezca tu código de acceso»*; la vieja
> decía algo parecido a *«espera tu turno»*, que aquí es sencillamente falso y deja al firmante sin
> salida. El backend falla cerrado a propósito: una puerta sin verificador podría leerse como «no hay
> nada que comprobar, que pase», y esa lectura convierte un desliz de teclado del remitente en una
> puerta abierta.

⚑ **Y lo que la versión anterior avisaba ya no aplica.** Decía *«no vais a ver ninguno de estos `code`
por el cable hasta que aterrice el `POST …/session/auth`»* y que *«un par de ellos no tiene quien los
lance ni siquiera en el dominio»*. Ambas cosas fueron ciertas hasta el 2026-08-19: hoy las dos rutas se
sirven y **todas las negativas de la tabla de arriba tienen sitio de lanzamiento**. Queda una sola reserva, y es de
alcanzabilidad y no de existencia: ⚠ **`AUTH_CHALLENGE_EXPIRED` no puede dispararse todavía**, porque en
esta slice ningún desafío lleva caducidad —un `ACCESS_CODE` vive lo que viva su sobre, y lo que acota el
adivinado es el presupuesto de intentos, no un reloj—. Tipadlo y enrutadlo igualmente; empieza a llegar
con los códigos entregados de TASK-022.

⛔ **423 y 429 os mandan hacer cosas opuestas, y tratarlos igual hace lo incorrecto en uno de los dos
casos.** 429 significa **esperad**: el bloqueo es blando, se libera solo pasado el enfriamiento y nadie
tiene que intervenir. 423 significa **dejad de esperar y llamad al remitente**: el bloqueo es duro y no se
suelta solo — sólo lo levanta el remitente regenerando el código o quitando el bloqueo. Un cliente que
enseñe 429 donde había 423 deja al firmante puliendo un botón contra una puerta que no se va a abrir; uno
que enseñe 423 donde había 429 le hace llamar por teléfono por una espera de cinco minutos, que es
exactamente la llamada que el nivel blando existe para evitar. ⚑ El 423 **no lleva `Retry-After`**, y esa
ausencia es deliberada: es lo que lo hace no-poleable en vez de meramente lento.

⚑ **Y el `Retry-After` del 429 ya es legible desde otro origen.** `Retry-After` no está en la lista segura
de CORS, así que hasta hoy un navegador os habría entregado el 429 con la espera invisible y vuestra única
salida habría sido hacer *polling* — convirtiendo una defensa contra fuerza bruta en un generador de carga
contra el endpoint que protege. El backend emite `Access-Control-Expose-Headers: Retry-After` en las
respuestas a un origen permitido. El valor son **segundos**, y nunca es `0`.

⚠ **Ningún 401 os dice cuántos intentos quedan, y no lo va a decir.** Publicar un contador es darle al
atacante una barra de progreso contra el presupuesto y decirle cuándo parar para no disparar el bloqueo. Si
vuestra UI quiere avisar, tiene que hacerlo con lo que sí llega: el 429 con su espera y el 423 con su
«llama al remitente».

### 6. Las dos puertas a la vez: la ceremonia entera, en orden

⚑ **Ésta es la configuración por la que existe la funcionalidad** —código en la puerta y el mismo código
otra vez en el acto— y **hasta el 2026-08-19 era imposible de firmar**: qué puerta estaba abierta se
deducía de la *declaración* y nunca del estado de la sesión, así que toda respuesta volvía a contestar
`ACCESS`, no se emitía jamás un desafío de firma, y el commit devolvía `AUTH_NO_OPEN_CHALLENGE` para
siempre. Ahora funciona, y ésta es la secuencia exacta, cada paso con lo que devuelve:

1. `POST /signing/session` → **200**, `status: "AUTH_PENDING"`, **sin** los tres miembros de credencial.
2. `GET …/session/auth` → `gate: "ACCESS"`.
3. `POST …/session/auth` con el código → **200** con **cinco** miembros: `gate_passed: "ACCESS"`,
   `status: "AUTH_PASSED"`, `access_credential`, `refresh_credential`, `expires_at`.
4. `GET …/session/auth` otra vez (con el token del correo) → ahora `gate: "SIGNING"`.
5. `GET /signing/session` y los bytes del documento → **200**, ya con la credencial de sesión.
6. `POST …/session/auth` con el código otra vez → **200** con **dos** miembros: `gate_passed: "SIGNING"`,
   `status: "AUTH_PASSED"`. **Ninguna credencial.**
7. `POST /signing/commit` → **200**, `status: "COMPLETED"`.
8. `GET …/session/auth` → `gate: null`. A un firmante que ha terminado no se le pide nada.

⛔ **La asimetría del paso 6 es el modelo, no un olvido.** Pasar la puerta de **firma** no acuña nada
porque no concede nada duradero: su prueba se guarda contra **un acto concreto** —ligada al conjunto de
documentos firmables— y la consume el commit. Un par de credenciales ahí significaría que la prueba del
acto se ha convertido en una concesión permanente, que es exactamente lo contrario de lo que la segunda
puerta existe para conseguir.

⚠ **Lo que esto os obliga a hacer: volver a preguntarle al descriptor después de pasar cada puerta.** Un
cliente que asuma «una puerta y ya» se queda en el paso 3 con una credencial que abre el read-model y un
commit que responde `401 AUTH_NO_OPEN_CHALLENGE` sin que nada se lo explique.

⚑ Hoy las dos puertas comparten el mismo secreto (un único verificador en el destinatario), así que lo
que añade el segundo prompt no es un segundo secreto sino un segundo **momento**. TASK-022 es lo que les
dará verificadores distintos; nada de vuestro lado tiene que cambiar por eso.

### 7. `POST /api/v1/signing/commit` gana cuatro negativas nuevas

**Dos 401 que NO son fallos de credencial**, y ésta es la trampa concreta: son 401, y lo que un cliente
hace por defecto ante un 401 es renovar. **Renovar no arregla ninguno de los dos.**

- `AUTH_REAUTH_REQUIRED` → la concesión de acceso se quedó inactiva. Hay que **volver a pasar la puerta de
  acceso**, no renovar.
- `AUTH_NO_OPEN_CHALLENGE` → hay una puerta de firma declarada y nadie la ha contestado. Hay que ir a
  `POST …/session/auth`, no a renovar.

⚠ La respuesta 401 compartida del spec dice *«deliberadamente no distingue los casos»*. Eso es cierto de
la credencial y **falso de estos dos**: llevan un `code` más fino justamente porque el remedio es otro.
**Mirad el `code` antes de decidir renovar.**

**Dos 409 más**, además del «ya firmada» que ya existía. Los tres comparten status porque comparten
remedio —ninguno es reintentable tal cual— y los tres llevan `code: "CONFLICT"`:

- el sobre fue **anulado** después de que este destinatario se autenticase. ⚑ Es un **rechazo, no una
  revocación**: la credencial sigue siendo válida y se sigue admitiendo en el borde; lo que pasa es que
  ya no compra nada en ninguna de las dos puertas. Un 401 aquí querría decir que la credencial dejó de
  aceptarse, que no es lo que ocurrió;
- un desafío de firma que **no autoriza este conjunto de documentos**;
- y el que ya conocíais: la sesión ya está completada — un segundo commit con la misma credencial válida
  cae aquí en vez de firmar dos veces.

Y el **404** que ya tenía: todavía no se ha abierto sesión para este token. Un token recién acuñado está
en ese estado hasta que corre `POST /signing/session`, así que commitear primero es un orden de llamadas
alcanzable desde el cliente, no una petición malformada.

## ⛔ La rotura: vuestra recuperación por inactividad deja de funcionar en los sobres con puerta

**Lo que funcionaba y por qué.** Cuando os dijimos *«renovación rechazada → reabrir con el enlace →
seguir»* era cierto, y era cierto por un motivo concreto: el backend acuñaba un par de credenciales
**incondicionalmente** en cada apertura. Reabrir era gratis, y `startIfAbsent()` no-opeaba sobre la sesión
existente mientras el acuñado corría igualmente detrás. Misma sesión, mismo estado, credencial nueva.

**Lo que cambia.** Ese acuñado gratis es exactamente el agujero que esta slice cierra: si reabrir el enlace
devolviera credencial, la puerta de acceso sería evitable **volviendo al enlace**, y entonces no sería una
puerta. Así que el acuñado pasa a ser condicional a que la puerta esté abierta.

**Cómo se os presenta.** No como un error. La reapertura devuelve **200** y sin los tres miembros de
credencial. Si vuestro código asume que ahí hay una credencial, lo que se rompe es lo de después.

> ⛔ **CORRECCIÓN 2026-08-19 — este párrafo y el discriminante de abajo eran erróneos, y su error os costó
> una pantalla en blanco.** Aquí decía que la reapertura devuelve `status: "AUTH_PENDING"`. **No es así, y
> nunca debió serlo**: el controlador calculaba ese campo desde la *declaración del remitente* —un hecho
> que no cambia nunca— en vez de desde el estado real de la sesión. Un destinatario que ya había pasado la
> puerta recibía `AUTH_PENDING` en cada apertura posterior; enrutado por eso a la pantalla de
> autenticación, `GET …/session/auth` respondía `gate: null` porque la puerta sí estaba pasada, y el
> cliente volvía al índice: **un bucle cerrado**. Corregido en el traspaso
> [`2026-08-19-session-status-and-grant-expiry.md`](2026-08-19-session-status-and-grant-expiry.md),
> que es el que hay que leer para el discriminante de hoy. Lo que sigue queda como registro de lo que se os
> dijo, no como instrucción vigente.

**Qué hacer en su lugar.** La recuperación pasa a tener dos ramas, y el discriminante es el `status` de la
respuesta de apertura:

- `status: "AUTH_PASSED"` → hay credencial, seguid exactamente como hasta ahora.
  ⛔ *Falso desde el 2026-08-19*: `AUTH_PASSED` **no** implica credencial. Ramificad por la **presencia de
  `access_credential`**, nunca por `status` a secas.
- `status: "AUTH_PENDING"` → **no** hay credencial: enrutad a la pantalla de autenticación (`GET
  …/session/auth` os dice qué puerta), y sólo después de que el `POST …/session/auth` os devuelva la
  credencial se sigue con la ceremonia.

Dicho de otra forma: **la ausencia de credencial deja de ser un fallo y pasa a ser un estado**. El único
sitio donde eso hay que decidirlo es el punto en el que hoy leéis la credencial de la respuesta de
apertura, y hay que decidirlo **por la presencia de la credencial, no por un `try`**.

⚑ **Y una tranquilidad que sí se puede afirmar: reabrir no revoca nada.** Lo que la reapertura se niega a
dar es una concesión **nueva**; la credencial que la puerta ya acuñó sigue intacta y sigue abriendo el
read-model. Está pinado con una prueba que reabre el enlace *después* de haber pasado la puerta y
comprueba las dos cosas a la vez.

⚠ **Y lo que hace que esto merezca un aviso en vez de un ticket: los sobres neutros no cambian nada.** Todo
sobre autorado antes de esta slice queda con el par neutro *(puerta de acceso abierta, sin puerta de
firma)* — la migración lo escribe explícitamente en cada destinatario existente, no lo deja a interpretar.
Para esos sobres la apertura sigue devolviendo los siete miembros y `AUTH_PASSED`, igual que hoy. **Vuestras
pruebas manuales van a seguir pasando con la rama rota**, y el fallo aparecerá el día que alguien autore el
primer sobre con código de acceso.

## Lo que el frontal tiene que hacer

1. **La rama `AUTH_PENDING` en la apertura**, que es la de arriba. Es el único punto obligatorio para que
   la ceremonia de un sobre con puerta arranque siquiera.
2. **Los tres miembros de credencial pasan a opcionales** en el tipo de la respuesta de apertura.
3. **Separar las dos uniones de `status`** (§2). ⚠ Si tenéis una sola: la de la apertura gana
   `AUTH_PENDING`, y la del read-model **no** debe incluir `AUTH_PENDING` ni `AWAITING_REAUTH` —esas ramas
   no pueden dispararse— pero sí `DECLINED`. Si tenéis un `switch` exhaustivo o un
   `Record<SessionStatus, …>`, deja de compilar; si no lo tenéis, los estados nuevos caen en vuestra rama
   por defecto, que probablemente diga algo parecido a «listo para firmar».
4. **Ampliar la unión de `AuthMethod`** a los catorce.
5. ⛔ **Buscar `AUTH_GATE_NOT_DECLARED` en vuestro código y reasignarlo.** No basta con cambiar la cadena
   por `AUTH_GATE_MISCONFIGURED`: la pantalla también cambia, porque cambió la condición (§5). Lo que
   describía el nombre viejo llega hoy como `AUTH_NO_OPEN_CHALLENGE`.
6. **Separar 423 de 429** donde hoy tratáis 423 como el único «bloqueado». Leed el `Retry-After` del 429 —
   ya llega, y ya es legible desde el navegador — y usadlo para el copy de la espera.
7. **Vuestra pantalla de re-auth deja de ser código muerto.** El traspaso de TASK-029 os dijo que la
   aparcarais y no la borrarais, y que no ramificarais contra cadenas adivinadas. Ésta es la llegada: las
   cadenas de la tabla de §5 son las reales, y `AUTH_REAUTH_REQUIRED` es la que enruta a esa pantalla —
   ⚑ y llega **también por el commit**, no sólo por la ruta de autenticación.
8. **Volver a preguntar al descriptor después de pasar cada puerta** (§6). Es lo único que separa un
   cliente que firma un sobre de dos puertas de uno que se queda con un `401` inexplicable en el commit.
9. **Rutar los dos 401 del commit por `code` antes de renovar** (§7). Renovar ante un
   `AUTH_REAUTH_REQUIRED` o un `AUTH_NO_OPEN_CHALLENGE` es un bucle: la renovación funciona, y el commit
   vuelve a fallar igual.
10. **Dejar de deducir el requisito del read-model.** El GET descriptor ya está publicado y contesta *qué
    se me pide **ahora***; `auth_requirements` del read-model contesta *qué se me declaró* (y ya trae su
    campo `gate` real). Son dos preguntas distintas: para pintar la pantalla de autenticación usad el
    descriptor, que además responde sin credencial.

⚑ **Y lo que NO cambia, dicho para que no lo repuntéis de más:** la partición de credenciales de TASK-029
sigue exactamente igual. `GET /signing/session`, los bytes del documento y el commit siguen pidiendo la
credencial de sesión; la apertura y la renovación siguen como estaban. Esta slice **añade** dos rutas de
enlace y **añade** estados y códigos; no mueve ninguna ruta de un lado al otro de la frontera.

## Lo que NO está listo todavía

⚑ **Cuatro puntos de la lista original quedaron superados el 2026-08-19.** Se dejan nombrados porque
alguien pudo haber planificado contra ellos:

- *«El cuerpo del GET descriptor y el del POST de envío NO son definitivos»* — **lo son**: §4 y §6 los
  publican miembro a miembro, y el conjunto de claves del descriptor está cerrado por una prueba.
- *«El spec generado va por detrás de este documento en el endpoint de apertura»* — **ya no**; la
  excepción que os pedía creer a este traspaso por encima del spec queda retirada.
- *«La mitad del remitente… hoy no hay ninguna forma de autorar un sobre con puerta»* — **la hay**, y por
  eso ahora podéis probar el camino entero (ver §«Cómo verificarlo»). Sigue siendo API de integrador bajo
  `MACHINE_KEY` y sigue sin ser vuestra.
- *«El campo `gate` en las entradas de requisito llega con el cuerpo del punto 2»* — **ya llega**, en
  `auth_requirements[].gate`, con valores `ACCESS` / `SIGNING`.

Lo que sigue realmente sin estar listo:

1. ⛔ **El despliegue.** La slice de backend está terminada y en verde, pero la rama **no está mergeada,
   no tiene PR y ni siquiera está subida**. Nada de este documento se puede llamar todavía contra un
   entorno desplegado. Lo de §«Lo que cambió» es contrato firme para codificar; lo que no es firme es la
   fecha.
2. ⚠ **`AUTH_CHALLENGE_EXPIRED` existe pero no puede dispararse.** Ningún desafío lleva caducidad en esta
   slice (§5). Enrutadlo igual; se hace alcanzable con TASK-022.
3. **Nada de esto trae un canal.** `ACCESS_CODE` es un código que el remitente comparte fuera de banda; no
   hay envío de OTP por correo ni por SMS en esta ventana, y por tanto **no hay ruta de reenvío**. El botón
   de «reenviar código» de vuestra pantalla no tiene contra qué hablar todavía. Es también la razón de que
   `masked_destination` sea siempre `null`.
4. ⚑ **`auth_status.authenticated` sigue siendo un `true` literal — y esto NO es una carencia**, que es
   justo lo que la versión anterior de este documento daba a entender al listarlo junto a los stubs. Es
   `true` siempre que esa ruta **conteste**, y por una propiedad de la partición: la ruta exige credencial
   de sesión, y detrás de una puerta declarada una credencial sólo existe si la puerta se pasó, así que
   quien no la ha pasado es rechazado en el borde y no llega nunca a esa línea. No esperéis que «se
   vuelva dinámico»: leerlo de una bandera de sesión sería una segunda respuesta, más débil, a una
   pregunta que el borde ya contestó. *(Los otros dos que la versión anterior daba por stub —
   `auth_requirements` y `method_used`— **sí** se hicieron reales: el primero lista una entrada por puerta
   declarada, el segundo publica el enum de catorce y vale `DIRECT_LINK` para el par neutro, que es el
   registro honesto de que lo único probado fue poseer el enlace. Y los tres de TASK-029 —
   `auth_completed_at`, `auth_expires_at`, `auth_ttl_minutes`— siguen siendo reales y no los toca nada de
   esto.)*

## Secuenciación

**Ninguno de los dos lados despliega solo.** Esta superficie se ratifica en el OpenAPI, no por decisión
unilateral de ninguno de los dos repos ([ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) §5), y
un repo no puede commitear en el otro: son **dos PRs coordinados en una misma ventana de release**.

La buena noticia comparada con el traspaso anterior: **esta vez la rotura es más pequeña**. TASK-029 os
retiraba una credencial de tres rutas ya desplegadas y no admitía convivencia. Ésta **añade** estados y
rutas, y sólo rompe un camino concreto —la recuperación por inactividad— y sólo para sobres que hoy no
existen. Así que:

- Podéis **empezar hoy** con todo lo de §«Lo que cambió»: es contrato commiteado, servido y probado
  extremo a extremo sobre HTTP.
- Podéis **desplegar antes** que el backend sin romper nada: manejar `AUTH_PENDING` en un mundo donde
  ningún sobre lo devuelve es código inerte, no una regresión.
- Lo que **no** podéis es desplegar después y dar por hecho que la recuperación por inactividad sigue en
  pie.

## Cómo verificarlo desde el frontal

⚑ **Esto ya se puede ejecutar** contra un stack local levantado sobre esta rama — no contra un entorno
desplegado, que todavía no existe. El orden importa porque cada paso descarta un fallo distinto.

1. **Las dos rutas existen.** `docker compose exec -T php-fpm php bin/console debug:router` desde
   `f5sign-infra`, buscando `signing/session/auth`. Deben salir las dos, GET y POST.
2. **El spec dice qué credencial pide cada una.** `GET http://localhost:8000/api/doc.json` → el `security`
   de cada operación. Las dos deben pedir el token del correo (`signingToken`), no la credencial de sesión.
   Si el documento y este traspaso no coinciden, **manda el documento**, sin excepciones.
3. **Autorad un sobre con puerta**, que ya se puede: `POST /api/v1/envelopes/{id}/recipients` bajo
   `MACHINE_KEY`, con `auth: { "access_method": "ACCESS_CODE" }`. Si omitís `access_code`, el servidor
   genera uno de seis dígitos y lo devuelve **una sola vez** en el 201 — no hay forma de volver a leerlo.
   `POST …/recipients/{recipientId}/access-code` lo regenera y `POST …/recipients/{recipientId}/auth-unlock`
   levanta un bloqueo duro; las dos son del remitente, no vuestras, pero son las que os desatascan una
   prueba.
4. **El sobre neutro no ha cambiado.** Abrid con un enlace de vuestros sobres de prueba de siempre: siete
   miembros y `AUTH_PASSED`. Ésta es la regresión que más importa.
5. **El sobre con puerta retiene la credencial.** Abrir devuelve **200**, `AUTH_PENDING`, y **sin** las
   tres claves. Comprobadlo con una aserción de **ausencia de clave**, no de valor nulo — un `!== null`
   pasa igual y no prueba lo que creéis.
6. ⚑ **La prueba de la reapertura, que es la que os avisa de haber dejado la recuperación vieja en pie.**
   Con ese mismo sobre con puerta: pasad la puerta, tirad la credencial de acceso como si hubiera caducado,
   y ejecutad vuestra ruta de recuperación entera. Debe acabar en la pantalla de autenticación, **no** en
   un error ni en una petición con `Bearer undefined`.
7. ⛔ **Las dos puertas, la secuencia entera de §6.** Autorad un destinatario con
   `auth: { "access_method": "ACCESS_CODE", "signing_method": "ACCESS_CODE" }` y recorred los ocho pasos.
   Los dos que separan un cliente correcto de uno roto son el **4** (el descriptor pasa a decir `SIGNING`)
   y el **6** (la respuesta trae dos miembros y **ninguna** credencial).
8. **El corte 423 / 429.** Fallad el código hasta el bloqueo blando: 429 con `Retry-After` **legible desde
   el navegador** (miradlo desde vuestro origen, no con `curl`: el fallo que esto caza es de CORS y `curl`
   no lo tiene). Seguid hasta el bloqueo duro: 423, **sin** `Retry-After`, y la pantalla debe decir
   «contacta con el remitente».
9. **El `code` y no el texto.** Provocad dos 401 distintos —código incorrecto y desafío sin abrir— y
   comprobad que vuestro enrutado los separa por `code`. Si los separáis por `detail`, funciona hoy y se
   rompe con la primera corrección de redacción. Y de paso: `grep -r AUTH_GATE_NOT_DECLARED` en vuestro
   repo debe devolver **cero** resultados.
