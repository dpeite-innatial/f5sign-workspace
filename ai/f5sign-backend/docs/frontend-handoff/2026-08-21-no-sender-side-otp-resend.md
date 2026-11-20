# Traspaso al frontal — NO habrá reenvío de OTP desde el remitente, y este es el motivo

| | |
|---|---|
| **Origen** | ninguna rama: **nada cambia en el hilo**. Es una ausencia decidida que hasta hoy solo se podía inferir del silencio, escrita a raíz de un coste medido (abajo). ⚑ Enmendado el 2026-09-01 desde `feat/claimable-recipient-slot` · `3bef45f`, que añade una ruta a la familia de abajo sin tocar nada de lo que este registro decide |
| **Fecha** | 2026-08-21 |
| **Repos afectados** | **dashboard** (y cualquier consumidor de la API de remitente) |
| **Naturaleza** | **aclara el contrato publicado** — cero cambios de wire, cero campos, cero códigos nuevos |
| **Acción requerida** | **ninguna en código** por lo que este registro decide. ⚑ **Matizado el 2026-08-31**: decía *"salvo que tengáis escrito algo contra una ruta de reenvío de remitente: entonces bórralo, no esperéis"*, y ahora hay que mirar **qué** reenvía ese código antes de borrarlo. Si reenvía **el código de un solo uso**, sigue igual: bórralo. Si reenvía **la invitación** —que es lo que hacía `notifyRecipient()`— ya tiene destino real y lo que toca es repuntarlo, no borrarlo: [TASK-041](TASK-041-invitation-resend.md) |
| **Status** | ⚠ **Pendiente por parte de `factor5_dashboard_sf`** — según su propio reporte del 2026-08-21, no medido por nosotros. `notifyRecipient()` sigue apuntando a `/recipients/{id}/resend` (404), sus comentarios siguen diciendo *"the platform does not expose a resend route **yet**"* — el mismo *todavía* que la regla 3 acaba de separar — y la UI sigue pintando un botón *"Reenviar notificación"* que falla el 100% de las veces. ⛑ **No miente al usuario final**: los dos controladores que lo llaman capturan el fallo y reportan que no se envió nada. Pendiente de que decidan con su usuario si retiran el botón o lo repuntan. ⚑ **Esta fila decía *"Aplicado … (retiraron su `notifyRecipient()`)"* durante unas horas del 2026-08-21, y era falso**: se escribió a partir de un *"lo arreglamos por aquí"* dicho en conversación, que es una intención. Lo corrigieron ellos, con la frase que debería presidir este campo — *"prefiero que vuestro registro esté bien a que nos deje bien"*. ⚑ **2026-08-31 — la disyuntiva de esa fila tenía una tercera salida y ya está construida.** *"Retirar el botón o repuntarlo"* se escribió cuando repuntarlo no era posible; hoy `POST …/recipients/{rid}/resends` hace exactamente lo que ese botón prometía ([TASK-041](TASK-041-invitation-resend.md)), así que la decisión pendiente por su parte es más barata de lo que este campo dice. ⛔ **Nada de esto es un cambio de `Status`**: no hemos mirado su árbol, y `Applied` se escribe desde el árbol del otro repo y nunca desde una frase — la regla que este mismo registro estrenó |

---

## Lo que cambió en el contrato

**Nada.** Este registro existe porque una ausencia no dice si es *"todavía no"* o *"nunca"*, y un
consumidor externo pagó esa ambigüedad en código.

## Lo que NO existirá, y por qué

⛔ **No hay —ni habrá— una ruta de remitente que acuñe o reenvíe el código de un solo uso.** No es un
hueco pendiente de priorizar: es la forma que tiene el diseño
([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.10).

**Y eso es una propiedad de la familia entera, no de una lista concreta**: ninguna ruta de remitente
sobre un destinatario acuña ni entrega ese código, sea cual sea el tamaño de la familia. Y la familia
**sí crece**, así que enumeradla del spec y no de aquí: `GET /api/doc.json`, las operaciones bajo
`/envelopes/{id}/recipients`. Lo cerrado es la propiedad; la lista no lo fue nunca.

Instantánea a 2026-09-01, para orientar la lectura y nada más:

```
POST /envelopes/{id}/recipients                            añadir
POST /envelopes/{id}/recipients/{rid}/access-code          acuñar código pre-compartido
POST /envelopes/{id}/recipients/{rid}/auth-unlock          levantar bloqueo
POST /envelopes/{id}/recipients/{rid}/corrections          corregir contacto + reenviar INVITACIÓN
POST /envelopes/{id}/recipients/{rid}/resends              reenviar INVITACIÓN sin corregir nada
POST /envelopes/{id}/recipients/{rid}/claim                nombrar a la parte de un hueco declarado
POST /envelopes/{id}/recipients/{rid}/signing-assignments  asignar documento
```

⚑ **Corregido dos veces, por dos ramas que no se veían, con un día de diferencia — y esa coincidencia
es el argumento.** Este bloque venía introducido por *"Las **cinco** rutas de remitente sobre un
destinatario son, **y seguirán siendo**:"*. El 2026-08-31 lo corrigió [TASK-041](TASK-041-invitation-resend.md)
al añadir `resends`; el 2026-09-01 lo corrigió [TASK-036](TASK-036-claimable-recipient-slot.md) al
añadir `claim` (rama `feat/claimable-recipient-slot`, **sin mergear ni desplegar**). Ninguna de las dos
vio a la otra, y las dos escribieron su propio banner diciendo lo mismo. Seis, no cinco — y el número
volverá a moverse.

⛔ **Lo que hacía daño era el *"y seguirán siendo"*, no la cifra**, y las dos correcciones coincidieron
también en eso: una enumeración cerrada con una promesa de permanencia **extiende la decisión a todo lo
que la lista contiene**, cuando la decisión sólo cubría un miembro. En un documento escrito para leerse
desde **otro** repositorio —o sea, para copiarse— eso es peor que un número viejo: una lista copiada no
tiene forma de enterarse de que le falta un miembro; una propiedad, sí. Enumerad contra el `doc.json`;
esta caja es una foto fechada.

⛔ **La tesis de este registro no se mueve, y ninguna de las dos rutas nuevas la toca.** Lo que se
declaró que no existiría es una ruta de remitente **para el código de un solo uso**, y sigue sin
existir. `resends` es la invitación — el otro caso, el que este registro ya señalaba como la asimetría
razonable, y que ahora tiene ruta propia en vez de viajar de gorra en `corrections`. Y `claim` nombra a
la parte de un hueco declarado sin acuñar ni entregar ningún OTP. Las tres razones de aquí abajo les
aplican a las dos exactamente igual.

**Tres razones, y ninguna es de esfuerzo:**

1. **El reenvío tiene que ser alcanzable ANTES de autenticarse — ése es su propósito.** El firmante
   que no ha podido pasar la puerta es exactamente quien lo necesita. Por eso vive en
   `POST /api/v1/signing/session/auth/otp/send`, que va con el **token de firma del enlace**, no con
   una API key. Vuestra clave da `401` ahí, y ese `401` es la propiedad, no un permiso que falte.
2. **Es la superficie más abusable del sistema: anónima, con coste y con datos personales.** Lleva
   limitador de **tres** claves (sesión, destino e IP), un intervalo mínimo de servidor devuelto como
   `429` con `retryAfter`, y una respuesta que **nunca** hace eco del destino. Una ruta de remitente
   equivalente sería una cuarta vía de gasto sin ninguna de esas tres defensas.
3. **El código va ligado a la sesión del firmante**, que es lo que sostiene la evidencia: quien pide
   el código es quien va a firmar. Un reenvío de remitente rompería esa correspondencia justo en el
   artefacto que tiene que aguantar una impugnación.

### ⚠ La asimetría que hace razonable deducir lo contrario

`corrections` se publica como *"corregir los datos de contacto de un destinatario **y reenviar su
invitación**"*. **O sea: un reenvío de remitente SÍ existe** — para la invitación, no para el código.
Nunca escribimos esa distinción en ningún sitio, así que quien la necesitaba la resolvió solo, y en la
dirección que le convenía. Escrita aquí para que no haga falta deducirla.

### Lo que sí puede hacer el remitente cuando el firmante llama

| Situación | Ruta | Qué hace |
|---|---|---|
| El contacto está mal | `POST …/corrections` | Corrige el destino y reenvía **la invitación**. El código lo pide el firmante desde su pantalla |
| El contacto está bien y el correo se perdió | `POST …/resends` | Reenvía **la invitación** a la dirección que ya está en ficha, sin gastar corrección y sin afirmar que estaba mal. Añadida el 2026-08-31 ([TASK-041](TASK-041-invitation-resend.md)); antes este caso se resolvía usando `corrections`, que es la fila de arriba mintiendo |
| Está bloqueado por intentos | `POST …/auth-unlock` | Levanta el bloqueo. **No envía nada** |
| El canal no le llega | *nada del remitente* | Es lo que resuelve la lista ordenada de métodos: el firmante se cambia de canal él mismo |

⛔ **`access-code` NO es una de estas, aunque hoy responda `200`.** Sobre un destinatario cuya puerta
no declara `ACCESS_CODE` acuña un código que ningún verificador mirará jamás, y os lo devuelve para
que lo dictéis — [`BL-180`](../BACKLOG.md), pendiente de arreglo, pasará a `422`.

## Lo que NO está listo todavía

- ⚠ **La tercera fila de la tabla de arriba está declarable pero no entrega.** La lista ordenada de
  métodos ([TASK-032](../tasks/TASK-032-ordered-auth-method-list.md)) está construida y desplegada,
  pero **hoy no sale ningún SMS de este sistema**: `SMS_DSN` es `null://null` y el tier sandbox de
  Twilio está construido y nunca ejecutado ([`BL-169`](../BACKLOG.md)). Declarar
  `["OTP_EMAIL","OTP_SMS"]` hoy le ofrece al firmante una opción *"recibir por SMS"* que no le trae
  nada. **Esperad al aviso de que `SMS_DSN` entrega de verdad.** Esto sí es un *todavía*.
- ⚠ **Corregir el contacto NO mata el código ya enviado al destino viejo** ([`BL-168`](../BACKLOG.md)).
  Durante lo que le quede de TTL sigue siendo contestable en el buzón que el remitente acaba de
  repudiar. No se deduce del contrato y por eso está aquí.

## Cómo verificarlo desde el frontal

1. `POST /api/v1/signing/session/auth/otp/send` con vuestra API key → **`401`**. Es el estado
   correcto y permanente; no abráis un ticket por ello.
2. Buscad en vuestro código cualquier ruta de remitente con `resend`, `notify`, `reenviar` o
   `/otp` en el path. Si `GET /api/doc.json` no la publica como operación real, **no existe y no va
   a existir** — la regla de *no adoptéis un campo hasta que el `doc.json` lo publique* vale igual
   para rutas, y es vuestra.

---

## ⚑ Por qué existe este registro

El 2026-08-21 la sesión `factor5_dashboard_sf` nos contó que tenía un `notifyRecipient()` apuntando a
`POST …/recipients/{id}/resend` — una ruta **que nunca anunciamos y nunca quisimos** — con este
comentario al lado:

> *The route does not exist yet: today this fails loudly with the backend's 404 […] it lights up
> unchanged once the backend ships the route.*

Nadie les hizo esa promesa: la infirieron del silencio, y solo lo descubrieron preguntando. Su
diagnóstico es el que provocó esta regla, y va literal porque está mejor dicho que cualquier
paráfrasis nuestra:

> *La ausencia de una ruta no dice si es "todavía no" o "nunca".*

`README.md` § regla 3 recoge la lección; este fichero es su primer caso.
