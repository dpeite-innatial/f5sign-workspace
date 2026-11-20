# Traspaso al frontal — el código de un solo uso llega por correo, y hay una ruta para pedirlo

| | |
|---|---|
| **Origen** | rama `feat/otp-email-codes` · commit de la slice (ver `git log` de esa rama; no hay PR todavía) |
| **Fecha** | 2026-08-19 |
| **Repos afectados** | **signer** (método declarable nuevo, ruta nueva, 429 nuevo) · **dashboard** (ninguna acción: declarar `OTP_EMAIL` es el mismo campo de añadir-destinatario que ya existe) |
| **Naturaleza** | additive — ninguna ruta cambia de credencial, ningún campo cambia de tipo ni desaparece |
| **Acción requerida** | **handle a new route** — la ruta 4 hay que dibujarla, y su `429` hay que pintarlo como **cuenta atrás, no como error** |
| **Status** | Applied (`f5sign-signer` `1af8e89`, 2026-08-19) — implementado contra mock; los E2E contra el stack real quedan pendientes de que esta rama llegue a `develop` |

## Lo que cambió en el contrato

Las formas exactas están en el spec (`GET /api/doc.json`); aquí va **qué cambió y qué hacer**.

1. **`OTP_EMAIL` pasa a ser declarable.** Hasta hoy la única familia de métodos que un remitente podía declarar era `ACCESS_CODE`. La unión de catorce miembros que ya tipáis no cambia — lo que cambia es que un segundo miembro se vuelve *alcanzable*. Un destinatario con `OTP_EMAIL` en cualquiera de sus dos puertas recibe un código de 6 dígitos por correo en vez de que el remitente se lo tenga que dictar por teléfono.

2. **Ruta nueva: `POST /api/v1/signing/session/auth/otp/send`** (la ruta 4 de ADR-0049 §2.3). Declara `SIGNING_TOKEN` —el enlace del correo, no la credencial de sesión— porque por construcción se alcanza **antes** de pasar la puerta.

   ⛔ **Una ruta, DOS operaciones, y confundirlas es el defecto que se despliega solo.** El discriminante es `resend` en el cuerpo, **opcional, y su ausencia significa `false`**:
   - `{"resend": false}` — *asegurar*. Si ya hay un código vivo lo devuelve y **no envía nada**. Es lo que tiene que llamar la pantalla al montarse.
   - `{"resend": true}` — *acuñar*. Emite uno nuevo y **el que el firmante tiene en la bandeja deja de funcionar**. Es lo que tiene que llamar el botón de re-enviar, y solo él.

   El default es el no destructivo a propósito: un cliente que se olvide del campo obtiene la operación que no puede matar un código bueno. Cablear el montaje a `resend: true` es cómo una recarga de página mata el código que el firmante está leyendo.

   ⚑ **No lleva `gate` ni `method`.** El servidor resuelve qué puerta se está preguntando; un cliente que nombrara la suya podría pedir un código de firma con la puerta de acceso aún cerrada.

3. **El 200 lleva tres miembros y ninguno es el destino.** `minted` (bool), `code_expires_at` y `next_resend_at` (los dos ISO-8601 absolutos).

   - `minted: false` significa *ya había uno vivo y no ha salido ningún correo*. Sin ese flag la pantalla diría "te hemos enviado un código" y el firmante esperaría un correo que no llega.
   - `next_resend_at` **puede venir en el pasado**, y no lo recortamos: significa *ya puedes re-enviar*. No dibujéis cuenta atrás en ese caso.

4. **429 nuevo, con `code: OTP_SEND_COOLING_DOWN`.** Un único código para las **cuatro** formas en que esta ruta rechaza —el intervalo mínimo de 60 s y cada una de las tres claves del limitador (sesión, destino, dirección de origen)— y es deliberado: dos de esas tres claves rechazan a gente que no ha hecho nada malo (una oficina detrás de un NAT comparte contador), así que al firmante se le dice **espera**, nunca *te has pasado*.

   El tiempo de espera viaja por **tres** portadores: la cabecera `Retry-After` (expuesta cross-origin), `retry_after_seconds` en el cuerpo y `retry_at` como instante **absoluto**. Preferid el último: el camino feliz de un código por correo es que el firmante se vaya a la app de correo y vuelva, y una pestaña en segundo plano tiene los timers suspendidos.

5. **409 nuevo en esa misma ruta, con dos códigos.** `AUTH_METHOD_NOT_DELIVERED` — la puerta es de `ACCESS_CODE`, cuyo secreto compartió el remitente fuera de banda; **no hay re-envío**, la recuperación es que el remitente lo resetee. `AUTH_NO_DESTINATION` — no hay dirección en ficha; lo arregla el remitente por la vía de corrección de contacto.

6. **`masked_destination` en `GET /signing/session/auth` deja de ser siempre `null`.** El campo ya estaba publicado; ahora trae un valor cuando la puerta declara un método entregado. Enmascarado **en servidor** y entregado ya enmascarado.

## Lo que el frontal tiene que hacer

- **Partir montaje de re-envío.** Son llamadas distintas al mismo endpoint y hoy eran la misma. Montaje → `{"resend": false}`; botón → `{"resend": true}`.
- **Colgar la copy de `minted`**, no de que la llamada haya ido bien.
- **Dibujar el 429 como reloj**, desde `retry_at`.
- ⛔ **No mapeéis `OTP_SEND_COOLING_DOWN` a las rutas de error genéricas.** Es un código propio precisamente para que no caiga en el mapeo de `TOO_MANY_REQUESTS` (que lleva a la pantalla de *enlace no válido* — un firmante que pide un segundo código acabaría ahí) ni en el de `AUTH_COOLING_DOWN` (que lleva a `/s/:token/auth` — correcto para la puerta, pero el re-envío también se dispara desde el modal de re-auth sobre `/sign`, y ahí es echar al firmante de la pantalla de firma a mitad de firma). `AUTH_COOLING_DOWN` **sigue existiendo y sigue saliendo por la ruta 5**: ahora hay dos 429 distintos en la superficie de auth, uno por ruta.
- ⛔ **No reconstruyáis el destino.** El 200 no lo lleva en ninguna forma. El enmascarado sale una sola vez, del descriptor de la ruta 3.

## Lo que NO está listo todavía

- ⚠ **`OTP_SMS` no es declarable, y `sendOtp` queda medio construido.** Esta slice abre la disponibilidad **solo** para `OTP_EMAIL`; SMS llega con TASK-023 y WhatsApp/voz no tienen tarea. Los gates de capacidad por *endpoint* no bastan a partir de aquí: hacen falta por *método*.
- ⚠ **La fixture `tests/fixtures/signing-session/auth-otp-send-rate-limited.json` del repo del signer llevaba `"error": "TOO_MANY_REQUESTS"`**, que es exactamente el código que acordamos no emitir. Corregida en `f5sign-signer@6998cca` junto con dos fixtures nuevas para los dos caminos de `minted`. Se menciona aquí para que nadie lea la versión vieja como contrato vigente.
- **El remitente no ve el estado de entrega del código.** "Enviado, aún no introducido" no está expuesto en el read-model del remitente; es un aplazamiento deliberado, no un olvido.
- **No hay reintento automático ni fallback de canal.** Una entrega fallida **nunca** cae a otro canal: eso degradaría en silencio la fuerza de autenticación declarada. La recuperación es la corrección de contacto (TASK-025), y un contacto corregido dispara un **código nuevo**, no un re-envío del muerto.
- ⚠ **Un `OTP_EMAIL` cuya invitación llegó por correo es un factor dos veces, no dos factores.** Está aceptado a sabiendas y es temporal; la regla de proyección que debe puntuarlo por debajo de `OTP_SMS` no existe hasta que TASK-023 haga la distinción significativa.

## ⚠ Antes de verificar nada: sin worker no sale ningún correo, y el 200 dice `minted: true` igualmente

Medido 2026-08-19 durante los E2E: una pasada completa devolvió `{"minted": true}` con el buzón **a cero** porque el worker estaba parado. ⚑ **Corregido el mismo día**: una segunda pasada dio también el buzón a cero, y la primera versión de esta nota se la atribuyó al worker. No era eso — el worker ya estaba arriba y lo que falló fue la resolución de Mailpit desde el worker. Dos causas distintas con el mismo síntoma, que es precisamente lo que hace peligrosa a esta clase de fallo.

⛔ **El 200 de esta ruta NO prueba la entrega, y no puede.** La petición escapa del relay —por eso es una llamada
síncrona— pero **la transmisión no**: la ocasión se crea, se registra `DeliveryRequested`, y quien renderiza y envía es
`TransmitDelivery`, un hop de relay más allá. El consumidor de Messenger está tras el perfil `workers` y **está apagado
por defecto**, así que sin él la petición queda encolada para siempre y el cliente ve un éxito perfecto.

Arráncalo antes de probar: `make -C ../f5sign-infra worker-up` (y `worker-status` para ver la profundidad de cola).

⚑ Consecuencia para el diseño del frontal, que es la parte que os toca: **no colguéis de este 200 ningún mensaje que
afirme que el mensaje llegó.** `minted: true` significa *hemos pedido la entrega*, no *el correo está en su bandeja*.
La diferencia importa el día que un proveedor rechace: eso llega por el camino de `RecipientDeliveryFailed`, no por
esta respuesta.

## ⚠ Y antes de creerte lo que veas en Mailpit: comprueba a qué Mailpit estás preguntando

⛔ **`http://localhost:8025` puede no ser el Mailpit de este stack, y cuando no lo es responde con datos plausibles de
otro proyecto en vez de fallar.** Medido 2026-08-19: había **dos** contenedores Mailpit en la máquina — el del stack
(`f5sign-mailpit`, en `f5sign-net`) y uno suelto de otro proyecto — y el suelto se había quedado con el binding del
puerto 8025. Todo lo que se consultaba por `localhost` era el ajeno. Llevó a reportar como "correos destruidos" unos
mensajes que ni siquiera eran de este sistema.

⚑ **Es una trampa peor que la del worker**, y por una razón concreta: el worker parado te da un buzón **vacío**, que se
lee como *"algo falla"*. El Mailpit equivocado te da un buzón **lleno**, que se lee como *"funciona"* — solo que lo que
ves es de otro sitio, y lo que buscabas no está.

**Pregunta siempre desde dentro de la red de docker**, donde el nombre `mailpit` sólo puede resolver al del stack:

```
docker exec f5sign-php-fpm curl -s "http://mailpit:8025/api/v1/search?query=<destinatario>"
```

⚠ Y no des por hecho que `localhost:8025` funciona aunque el contenedor esté `healthy`: medido después de que el suelto
se detuviera, esa URL no respondía nada mientras el buzón real sí tenía el mensaje dentro.

## Cómo verificarlo desde el frontal

1. Crear un sobre con un destinatario cuya puerta de acceso declare `OTP_EMAIL` y enviarlo.
2. Abrir el enlace → `POST /api/v1/signing/session` (200) → `GET /api/v1/signing/session/auth` → `gate: "ACCESS"`, `method: "OTP_EMAIL"`, `masked_destination` con valor.
3. `POST …/auth/otp/send` con `{"resend": false}` → 200 con `minted: true`. Sale un correo.
4. Repetir la misma llamada → 200 con **`minted: false`** y los mismos `code_expires_at` / `next_resend_at`. **No sale un segundo correo.**
5. `POST …/auth/otp/send` con `{"resend": true}` antes de 60 s → **429**, `code: OTP_SEND_COOLING_DOWN`, con `Retry-After`, `retry_after_seconds` y `retry_at`.
6. Pasados los 60 s, repetir con `{"resend": true}` → 200 con `minted: true`, y **el código del correo anterior ya no pasa la puerta** (401 `AUTH_CODE_INCORRECT`).
7. Dejar caducar un código (15 min) y enviarlo → 401 con `AUTH_CHALLENGE_EXPIRED`, **distinto** de `AUTH_CODE_INCORRECT`. Esa diferencia es la que le dice al firmante que pida otro en vez de llamar a soporte.
8. Sobre con puerta `ACCESS_CODE`, misma ruta → **409** `AUTH_METHOD_NOT_DELIVERED`.
