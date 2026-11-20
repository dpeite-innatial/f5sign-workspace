# Traspaso al frontal — el firmante varado puede volver a pasar la puerta: `recover`

<!-- OFFREPO: los hechos del lado cliente (el `sessionStorage` por pestaña, la pantalla del firmante
varado, el `useCountdown`) los midió la sesión que trabajaba en `f5sign-signer` el 2026-08-19 contra
este backend. Están reescritos en línea donde se usan. -->

| | |
|---|---|
| **Origen** | rama `feat/access-grant-recovery` · commit `0a61092` · sin PR |
| **Fecha** | 2026-08-19 |
| **Repos afectados** | **signer** únicamente |
| **Naturaleza** | **aditivo** — un campo opcional en dos cuerpos de petición, y un miembro nuevo en la respuesta del descriptor. Nada cambia si no lo enviáis ni lo leéis |
| **Acción requerida** | cablear el control *«he perdido mi sesión»* en la pantalla del firmante varado |
| **Status** | Pending |

> **La forma que esperabais era otra, y es mejor así.** Se os anticipó una ruta de reapertura
> (`POST …/session/reopen`). **No existe y no va a existir.** Esa ruta retiraba la concesión *a
> petición*, y eso significaba que cualquiera con el enlace filtrado podía echar a un firmante que
> estaba trabajando en otra pestaña — en bucle, y sin gastar nada suyo, porque el limitador acota
> **envíos**, no expulsiones. El coste caía entero sobre el firmante legítimo, que necesita un código
> para volver a entrar cada vez. Lo que va en su lugar no retira nada: **pide volver a que te
> pregunten**, y nadie pierde su sesión hasta que alguien pasa la puerta de verdad. El razonamiento
> completo está en [`ADR-0053`](../adr/ADR-0053-access-grant-recovery.md) §7.1.

## Lo que cambió en el contrato

Un booleano opcional, `recover`, en el cuerpo de **dos rutas que ya usáis**. Por defecto `false`; si
no lo enviáis, todo responde exactamente igual que hoy.

| Ruta | Con `recover: true` |
|---|---|
| `POST /api/v1/signing/session/auth/otp/send` | manda un código **para la puerta de acceso** aunque la sesión ya la haya pasado |
| `POST /api/v1/signing/session/auth` | la respuesta que enviáis se contrasta **contra la puerta de acceso**, y si acierta os devuelve un par nuevo |

La respuesta de la segunda es **exactamente la de un primer paso de puerta**: `gate_passed: "ACCESS"`,
`status`, y los tres miembros de credencial. Mismo shape, mismas claves. No hay nada nuevo que parsear.

**Para una puerta de tipo `ACCESS_CODE` (código pre-compartido) no hay que llamar a la primera ruta.**
Ese código no se envía nunca — no hay nada que mandar — así que la recuperación entera es un solo
`POST …/session/auth` con `{code, recover: true}`. Si la llamáis, os responde `409
AUTH_METHOD_NOT_DELIVERED`, que es lo que ya hacía.

## Lo que el frontal tiene que hacer

1. **Detectar al varado.** Es el caso que os describí en el traspaso anterior y ya distinguís:
   `POST /signing/session` responde `status: "AUTH_PASSED"` **sin** `access_credential`. Ése, y sólo
   ése, es el firmante que ha pasado la puerta y ha perdido el par.

   > ⚠ **DESMENTIDO el 2026-08-24 por [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md).**
   > El *"y sólo ése"* era falso: ese cuerpo lo producían **dos** poblaciones, porque una sesión
   > `COMPLETED` también está autenticada —la puerta sí se pasó— y también llega sin credencial tras una
   > puerta declarada. Siguiendo este punto al pie de la letra, a quien ya había firmado se le ofrecía
   > recuperación y todo envío moría en `AUTH_NO_OPEN_CHALLENGE` sin salir ni un mensaje.
   > **Ahora sí es sólo ése, pero hay que comprobarlo:** `status` tiene un tercer miembro, `COMPLETED`,
   > con precedencia. El varado es `AUTH_PASSED` sin credencial **y** `status !== 'COMPLETED'`.
   > En la ruta 3 el mismo corte se lee en `outcome`, que debe ser `null`.

   **Y para saber QUÉ pedirle, `GET …/session/auth` trae ahora `access_gate`**, añadido el 2026-08-19
   a petición vuestra:

   ```json
   { "gate": null, "method": null,
     "access_gate": { "method": "ACCESS_CODE", "masked_destination": null } }
   ```

   `gate`/`method` siguen respondiendo *qué se te pide ahora* y van a `null` una vez pasada la puerta;
   `access_gate` responde *cuál es tu puerta* y sobrevive. `null` cuando la puerta de acceso es neutra
   — que es exactamente la población que no puede quedarse varada.

   ⛔ **No ramifiquéis la pantalla de auth por `access_gate`**: dice cuál es la puerta, no que os la
   estén pidiendo. Para eso, `gate`.

   ⚠ **Y no useis el `409 AUTH_METHOD_NOT_DELIVERED` como discriminante**, que era la salida que
   deducíais: ese rechazo cubre **diez de los catorce** métodos del catálogo, no `ACCESS_CODE`, así que
   se rompe en silencio el día que se cablee FIDO2, DNIe o cualquier otro que no entregue código.

   **Y con `access_gate.method` en la mano, la rama que hay que escribir son tres, no catorce:**

   | `method` | control |
   |---|---|
   | `ACCESS_CODE` | campo de contraseña — código pre-compartido que el remitente dictó aparte |
   | `OTP_SMS` · `OTP_EMAIL` · `OTP_WHATSAPP` · `OTP_VOICE` | campo de código, con `masked_destination` |
   | cualquier otro | **no soportado todavía** — decidle que contacte con el remitente |

   Los diez restantes no son "campo de contraseña": son WebAuthn, NFC del DNIe, wallet EUDI, vídeo-KYC.
   Cada uno necesita una interfaz propia que no existe en ninguno de los dos lados.

   **Y para dimensionar el control, `code_length`** — añadido el 2026-08-19 porque lo pedisteis, y en
   **los dos sitios**, que es la parte que vuestra propuesta no cubría:

   | dónde | dimensiona |
   |---|---|
   | `code_length` (raíz) | el control de la puerta que se pide **ahora** — vuestra pantalla de auth |
   | `access_gate.code_length` | el control de **recuperación**, que pregunta por la puerta sea cual sea la viva |

   Sólo en `access_gate` no habría bastado: vuestra pantalla de auth renderiza desde `gate`/`method`, y
   una puerta de **firma** también puede ser un método con entrega. Eran dos superficies, no una.

   ⛔ **`null` significa NO SE PUEDE SABER, nunca «no hay código».** Con `null`, campo único de texto
   libre — no una caja segmentada.
   - **Métodos con entrega** (`OTP_*`): viene el número. El código lo generamos nosotros por un único
     generador, así que la anchura es uniforme por construcción y podéis segmentar con confianza.
     Vuestras seis casillas se quedan, ahora dimensionadas por el contrato en vez de por una suposición.
   - **`ACCESS_CODE`**: viene `null`, y es la verdad literal — del código del remitente **sólo
     guardamos un hash**, así que no hay longitud que reportar. `MIN_SENDER_SUPPLIED_CODE_LENGTH` es un
     **suelo**, no una anchura, y el patrón para el que existe (*«el código de acceso es tu DNI»*) lo
     supera con nueve alfanuméricos. Vuestro `<input type="password">` único ya era lo correcto ahí.

   ⚠ **No dedujimos el `null` de una política: es que el dato no existe.** Y no leáis el número como
   permiso para cachearlo — leedlo del descriptor, que es donde se mantiene.

   ⛔ **Escribid la tercera rama aunque hoy esté vacía.** Este despliegue sólo habilita `ACCESS_CODE` y
   `OTP_EMAIL` (`signer.available_auth_methods`), así que hoy no puede aparecer nada más — pero eso es
   un hecho del **despliegue**, no del contrato: una instalación Dedicated que cablee SMS abre el
   miembro sin que cambie nada aquí ([ADR-0013](../adr/) lo hace una elección de composición). Una rama
   que hoy no se puede alcanzar no avisa de nada el día que se alcanza; si en su lugar dejáis que caiga
   en el `else` del campo de contraseña, el primer firmante con FIDO2 verá una caja pidiéndole un
   código que nadie le ha mandado.

2. **Ofrecer un control explícito**, no un reintento automático. Algo del tipo *«Vuelve a entrar»* /
   *«He perdido la sesión»*. Al pulsarlo:
   - si el método entrega código (`OTP_EMAIL`): `POST …/auth/otp/send` con `recover: true`, y a la
     pantalla del código;
   - si es `ACCESS_CODE`: directo a la pantalla del código, sin llamada previa.
   - `GET …/session/auth` os dice el método, como siempre.

3. **Enviad el código con `recover: true`** en `POST …/session/auth`. Respuesta 200 → par nuevo →
   guardadlo como guardáis el de un primer paso y seguid con la ceremonia.

4. **La cuenta atrás de `access_grant_expires_at` sigue teniendo sentido y no la quitéis.** Es la vía
   pasiva: el firmante que no quiere volver a pedir un código espera a ese instante y la siguiente
   apertura le devuelve `AUTH_PENDING`. Ahora hay dos salidas de la misma pantalla, una activa y una
   pasiva.

> **No lo enviéis al montar la pantalla.** Es la misma trampa que `resend`: mandado en cada carga, le
> pide a un firmante ya autenticado que reteclee un código que acaba de probar. Que salga de un gesto
> del usuario, o de haber leído `AUTH_PASSED` sin credencial.

## Lo que NO está listo todavía

- **No hay ruta nueva.** Si teníais algo cableado contra `POST …/session/reopen`, quitadlo: nunca
  existió.
- **No hay estado nuevo ni columna nueva.** `status` sigue siendo la misma unión de dos miembros en la
  apertura.
- **`recover` no concede nada por sí solo.** El código tiene que ser correcto; uno equivocado gasta
  presupuesto de intentos igual que en un primer intento, y los dos niveles de bloqueo (423 / 429) se
  aplican idénticos. No hay presupuesto propio para la recuperación, a propósito.
- **La pestaña vieja no se corta en seco.** Una recuperación con éxito mata el *refresh* anterior
  inmediatamente, pero la credencial de acceso anterior es un JWT sin revocación y sigue leyendo hasta
  que se le acaban sus quince minutos. O sea: la otra pestaña pierde la capacidad de *continuar*, no la
  petición que tenga en vuelo.
- **En un sobre con puerta NEUTRA el campo se ignora.** No es un error: esos destinatarios nunca se
  quedan varados, porque reabrir el enlace les acuña un par nuevo.

## Cómo verificarlo desde el frontal

Con un sobre de puerta `ACCESS_CODE` declarada:

1. Abrid, pasad la puerta con el código → llega el par.
2. Vaciad el `sessionStorage` y reabrid → `AUTH_PASSED` sin credencial (el varado).
3. `POST /api/v1/signing/session/auth` con `{"code": "<el correcto>", "recover": true}` → **200**,
   `gate_passed: "ACCESS"`, par nuevo. La ceremonia sigue con él.
4. Y la comprobación que de verdad importa, si queréis verla: con el código **equivocado** y
   `recover: true` → **401**, y la sesión sigue en `AUTH_PASSED` con su concesión viva. Un intento
   fallido no echa a nadie.
