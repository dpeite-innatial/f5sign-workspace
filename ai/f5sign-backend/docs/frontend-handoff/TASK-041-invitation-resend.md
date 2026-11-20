# Traspaso al frontal — el botón «Reenviar notificación» por fin tiene ruta, y no es la que se dedujo

| | |
|---|---|
| **Origen** | rama `feat/recipient-invitation-reminder` · sin PR todavía. ⚑ **Citaba el commit `27c65e4`; ese árbol llamaba a la ruta `/reminders`.** El 2026-08-31 se renombró el concepto entero a **resend** antes de mergear —`reminder` ya era de otra función (los recordatorios programados de `RemindersSchedule`)— así que ese sha describe una ruta que no va a existir. La rama es lo que hay que mirar; la ruta buena es la de abajo |
| **Fecha** | 2026-08-31 |
| **Repos afectados** | **dashboard** (y cualquier consumidor de la API de remitente). `f5sign-signer` no cambia en código, pero sí le llega una consecuencia — última sección de *Lo que el frontal tiene que hacer* |
| **Naturaleza** | **additive** — una ruta nueva y **tres** miembros nuevos en `ProblemCode`; enumeradlos del enum publicado, no de esta fila, que dijo *«dos»* hasta el 2026-09-01. Ninguna respuesta existente cambia, ningún código cambia de significado, `corrections` sigue exactamente igual |
| **Acción requerida** | **repuntar `notifyRecipient()`** al path real y ramificar el 409 sobre `code` |
| **Desplegado** | ⛔ **NO todavía** — la rama no está mergeada. Y `develop` tampoco es un despliegue: comprobadlo vosotros en el `doc.json` que os sirven (regla 4 del README) |
| **Status** | Pending |

---

## Lo que cambió en el contrato

**Ruta nueva:** `POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends`

Vuelve a invitar a un destinatario de un sobre **ya enviado**, a la dirección que ya está en ficha.
`machineApiKey`, **sin cuerpo**, **204**. El esquema exacto está en el `doc.json`; aquí va lo que hay
que saber para usarla.

**No es una corrección, y ésa es toda su razón de ser.** Una corrección dice *la dirección estaba
mal*; un reenvío dice *estaba bien y el correo no llegó*. Este endpoint **no gasta ninguna de
las 3 correcciones** del destinatario, **no toca el contacto**, **no toca el `outcome`** y **no
escribe** el `RecipientCorrected` que afirma que el remitente se equivocó al direccionar.

⚠ **Tampoco es un recordatorio, y el nombre importa para vuestro copy.** Un recordatorio da por hecho
que el destinatario recibió la invitación y no ha actuado; aquí no sabemos eso, y el caso normal es
justo el contrario —la primera invitación se filtró, se borró sin abrir o nunca llegó—. Por eso el
correo que sale dice *«le reenviamos su invitación»* y **no** *«sigue pendiente su firma»*. Los
recordatorios programados son otra función, todavía sin construir (`RemindersSchedule`, ficha
[`BL-210`](../BACKLOG.md)).

⚠ **El 204 significa *registrado*, no *entregado*.** El envío es asíncrono.

⚠ **Lleva `F5Sign-Declared-Subject` como cualquier otra ruta de integrador**, y es **obligatoria**: si
la construís como una llamada nueva en vez de reutilizar vuestro cliente, olvidarla da **400**. No es
nada específico de este endpoint; se dice porque es el error típico al añadir la primera llamada.

**Tres miembros nuevos en `components.schemas.ProblemCode`:** `RECIPIENT_RESENT_TOO_RECENTLY`,
`RECIPIENT_STEP_NOT_ACTIVE` y `RECIPIENT_HAS_NO_ADDRESS`.

**El 409 lleva `application/problem+json` y cinco `code` posibles**, y hay que ramificar porque el
siguiente movimiento es distinto en cada uno. ⛔ Sacad la lista del `enum` publicado en `doc.json`, no
de esta tabla: decía cuatro hasta el 2026-09-01 y la quinta llegó con la propia rama.

| `code` | Qué pasó | Qué hacer |
|---|---|---|
| `RECIPIENT_RESENT_TOO_RECENTLY` | ya salió uno dentro del intervalo mínimo | **el único que se resuelve reintentando más tarde** |
| `RECIPIENT_STEP_NOT_ACTIVE` | su paso no se ha abierto: nunca se le invitó, así que no hay nada que reenviar | parar. Su primera invitación sale sola cuando le llegue el turno |
| `RECIPIENT_LEG_CLOSED` | ya firmó, rechazó, delegó o fue saltado | parar, no hay nada que entregarle |
| `RECIPIENT_HAS_NO_ADDRESS` | el destinatario no tiene dirección: no hay a dónde enviar | parar y **corregir su contacto**; esperar no lo cura |
| `CONFLICT` | el sobre es terminal, o **no se ha enviado** | parar |

⛑ **2026-10-13: superseded in part by [TASK-031](TASK-031-notification-channels.md).** `RECIPIENT_HAS_NO_ADDRESS` is retired. The resend now answers `409 RECIPIENT_NOTIFIED_BY_INTEGRATOR` (the recipient declared `notification_channels: []`), `409 RECIPIENT_HAS_NO_REACHABLE_CHANNEL` (no declared channel can reach them now) or `409 RECIPIENT_SIGNS_BY_DELEGATION`. The table above is the contract as this handoff shipped it.

⚑ **`RECIPIENT_LEG_CLOSED` es el mismo string que ya devuelve `…/corrections`, y es a propósito**: es
el mismo hecho sobre el mismo destinatario, y quien ya ramifica sobre él allí no debería tener que
aprenderse un segundo nombre aquí.

⚑ **Sobre `RECIPIENT_HAS_NO_ADDRESS`, el remedio exacto.** `POST /envelopes/{id}/recipients/{recipientId}/corrections`
con una dirección real. Si el paso del destinatario está abierto, la corrección reinvita en el acto; si
su paso todavía no se ha abierto, la corrección se aplica y la invitación sigue esperando su turno —
así que no dibujéis «reenviado» a partir del 2xx de la corrección en ese caso.

⚠ **No es un cambio de comportamiento para vosotros.** Durante el desarrollo de esta rama ese caso
respondía 204 sin enviar nada, pero la rama no se ha desplegado nunca, así que ningún cliente ha visto
ese 204. Para el dashboard este `code` nace ya con este significado.

⚑ **`RECIPIENT_RESENT_TOO_RECENTLY` —y solo ese— trae `next_resend_at` en el cuerpo**, un instante
absoluto RFC 3339 a partir del cual se admite el siguiente reenvío a ese destinatario:

```json
{ "code": "RECIPIENT_RESENT_TOO_RECENTLY", "next_resend_at": "2026-08-31T09:01:00+00:00" }
```

⛔ **No deduzcáis el intervalo de ese ejemplo.** El instante sale de `última marca + el intervalo que
el agregado impone`, y ese intervalo es un constante del dominio que ya se ha movido una vez antes del
merge (el ejemplo mostraba `09:15`, de cuando eran 15 minutos, hasta el 2026-09-01). Renderizad el
instante que os llegue; no dibujéis una cuenta atrás calculada por vuestra cuenta.

⚑ **Añadido el 2026-08-31 a petición del dashboard**, antes del merge. Este párrafo decía *«no hay
`Retry-After` ni campo numérico … si necesitáis el número como dato, pedidlo»*: se pidió y está.

Tres cosas sobre él:

- **Es absoluto y no una cuenta atrás**, para que no dependa de que los dos relojes coincidan ni de lo
  que tarde la respuesta en llegar. **Mostrad la hora**; no calculéis los segundos que faltan a partir
  de ella, porque eso reintroduce justo la dependencia que el instante evita.
- **No se mueve al reintentar.** Sale del sello del último envío, no de «ahora», así que pedirlo dos
  veces da lo mismo — y quien espere hasta esa hora exacta entra en vez de volver a ser rechazado.
- **Ningún otro `code` lo lleva**, y es deliberado: esperar no cura ninguno de los demás, y un plazo
  ahí sería una instrucción para hacer lo único que no puede funcionar.

⚠ El `detail` sigue nombrando el intervalo en prosa y **no es contrato**: no lo parseéis. El dato es
`next_resend_at`.

**404** para un sobre o un destinatario desconocidos, o de otro tenant. Igual que en el resto de la
superficie de remitente.

## Lo que el frontal tiene que hacer

1. **Repuntar `notifyRecipient()`.** Hoy apunta a `POST …/recipients/{id}/resend` — **en singular**,
   y nunca existió ([registro del 2026-08-21](2026-08-21-no-sender-side-otp-resend.md)). El destino
   real es `POST …/recipients/{recipientId}/resends`, **en plural** (es una colección de hechos
   registrados, no un verbo), **sin cuerpo**, y responde 204. El botón *«Reenviar notificación»*, que
   fallaba el 100% de las veces, pasa a funcionar en cuanto esto esté desplegado — no antes.
2. **Dejar de usar `corrections` como reenvío**, si lo estáis haciendo. Funciona, y cuesta una de las
   tres correcciones del destinatario **para siempre**, además de dejar escrito en un log
   append-only que la dirección estaba mal. Usad `corrections` cuando de verdad esté mal.
3. **Ramificad sobre `code`, no sobre el 409 a secas** (tabla de arriba). Un reintento ciego solo
   puede acertar en uno de los casos posibles, y falla en todos los demás.
4. **Decid en la UI que el enlace anterior sigue vivo.** El reenvío **no lo anula**: caduca por
   su cuenta, y quien encuentre el correo viejo puede seguir usándolo. Los dos llevan a la misma
   sesión de firma. Un texto tipo *«se ha enviado un enlace nuevo; el anterior sigue siendo válido»*
   evita el ticket de soporte.
5. **Avisad de que puede interrumpir a quien esté firmando ahora mismo.** Si el destinatario está a
   media ceremonia y pincha el enlace nuevo, se le emiten credenciales nuevas y —si su sobre declara
   puerta de autenticación— vuelve a pasar por ella. **No pierde progreso y es la misma sesión**,
   pero lo nota. ⛔ **No hay forma de preguntar antes si alguien está firmando**, así que esto se
   avisa en el copy del botón; no es algo que podáis comprobar.

## Lo que NO está listo todavía

- **Los recordatorios programados.** `RemindersSchedule` existe en los `Settings` del sobre —se
  valida y se persiste— y **no lo lee nadie**: ningún endpoint lo acepta y ningún worker lo consume.
  ⛔ **Y no es «la otra mitad» de esta ruta**, aunque este registro lo dijera hasta el 2026-08-31: eso
  cuenta los días que faltan para que un sobre caduque, esto repara una invitación que no llegó. Si
  vuestra UI ofrece configurar una cadencia de recordatorios, hoy no ocurre nada. Ficha
  [`BL-210`](../BACKLOG.md).
- **El número de reenvíos no sale por ninguna respuesta.** El backend lo cuenta por destinatario a
  partir de este cambio, pero `GET /envelopes/{id}` no lo publica. Si os hace falta para pintar
  *«reenviado 2 veces»*, pedidlo: es aditivo y no rompe a nadie.
- **El valor exacto del intervalo mínimo puede cambiar.** Es un número de negocio elegido donde
  equivocarse sale barato, no una medición, y vive en el servidor. No lo codifiquéis en el frontal
  ni lo deduzcáis de un `detail`.

## Lo que NO existirá, y por qué

⛔ **El reenvío NO mata el enlace anterior, y no es un «todavía».** Emitir es aditivo: dos
llamadas producen dos credenciales vivas, cada una hasta su propia caducidad. La revocación se
descartó en su momento sobre el registro ([ADR-0045](../adr/ADR-0045-issued-credential-format.md)
§2.6, [TASK-028](../tasks/TASK-028-opaque-signing-token.md) §4.3), y cambiarlo sería una decisión de
arquitectura, no una mejora de este endpoint. Diseñad la pantalla contando con **N enlaces vivos**.

⛔ **No habrá guarda contra reenviar a alguien que está firmando.** Para saberlo, el sobre tendría
que leer el estado de la sesión de firma, que es justo la dependencia entre contextos que este
diseño no tiene. Se acepta y se documenta; no se arregla aquí.

⛔ **Y esto NO reabre el reenvío de OTP desde el remitente.** Lo que se reenvía aquí es **la
invitación**, nunca el código de un solo uso: ése lo sigue pidiendo el firmante desde su pantalla, y
las tres razones siguen vigentes tal cual —
[2026-08-21-no-sender-side-otp-resend.md](2026-08-21-no-sender-side-otp-resend.md). La asimetría que
aquel registro señalaba (*«un reenvío de remitente SÍ existe — para la invitación, no para el
código»*) sigue siendo exactamente la misma, solo que ahora la invitación tiene su propia ruta en vez
de viajar de gorra en `corrections`.

## Cómo verificarlo desde el frontal

1. `GET /api/doc.json` → existe la operación
   `POST /api/v1/envelopes/{id}/recipients/{recipientId}/resends`. Si no está, ese despliegue es
   anterior a este cambio y el botón sigue sin destino.
2. `components.schemas.ProblemCode.enum` contiene `RECIPIENT_RESENT_TOO_RECENTLY`,
   `RECIPIENT_STEP_NOT_ACTIVE` y `RECIPIENT_HAS_NO_ADDRESS`. ⚠ Buscad los miembros del enum, no las palabras sueltas en el
   documento.
3. Sobre enviado, destinatario con su paso abierto → **204**, y le llega un correo cuyo asunto abre
   con *«Le reenviamos su invitación de firma»* —no con el de la primera invitación— y cuyo enlace
   funciona.
4. Repetir de inmediato → **409** con `code: "RECIPIENT_RESENT_TOO_RECENTLY"`.
5. Con un sobre en borrador → **409** con el `code` genérico (`CONFLICT`), no con uno de los dos
   nuevos.
6. Con un destinatario de un paso posterior que aún no se ha abierto → **409** con
   `code: "RECIPIENT_STEP_NOT_ACTIVE"`.
