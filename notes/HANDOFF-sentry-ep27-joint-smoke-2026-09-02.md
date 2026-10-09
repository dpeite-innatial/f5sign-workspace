# Handoff — Sentry EP27: el smoke conjunto se hizo, y salieron cinco cosas

| | |
|---|---|
| **Fecha** | 2026-09-02 |
| **Sesiones** | `f5sign-backend` (worktree `feat/claimable-recipient-slot`) + `f5sign-signer` (`develop`) |
| **Repos afectados** | `f5sign-backend`, `f5sign-signer`, `f5sign-infra` |
| **Qué cerró** | La mitad `request_id` de [`BL-174`](../f5sign-backend/docs/BACKLOG.md), abierta desde 2026-08-20 |
| **Estado** | Filas 2 y 3 **cerradas** en `develop` (`93e1ae1`, `13149c1`, `c1ba3d0`). Fila 1 **a medias**: la mitad del backend cerrada (`69298eb`), la de infra en rama sin mergear. Fila 4 abierta (es de consola, no de código). |

⚠ **Salvo la fila 3, nada de esto está commiteado en ningún subrepo.** Esta nota es el único
sitio donde viven las otras cuatro, y quieren home durable (`docs/BACKLOG.md` del repo que toque):
no se escribieron ahí porque la rama viva del backend era `feat/claimable-recipient-slot`, que no
es su sitio.

---

## Lo que sí quedó demostrado

**Correlación `request_id` backend ↔ signer, medida por tres puntos independientes.**
Hasta hoy los dos proyectos llevaban **90 días a cero eventos**: no es que se hubiera roto, es que
nunca se había encendido.

```
scope del proceso (leído en el controlador) : 01a06178-e007-731d-b2c7-0537fd45c167
cabecera HTTP  X-Request-Id                 : 01a06178-e007-731d-b2c7-0537fd45c167
tag indexado en Sentry (F5SIGN-BACKEND-2)   : 01a06178-e007-731d-b2c7-0537fd45c167
```

Medido por dos sesiones distintas, en los dos extremos. El evento salió de un 500 lanzado **dentro
de un controlador** por una ruta temporal con `Authn::NONE`, ya borrada.

De camino quedaron medidas dos cosas que hasta ahora eran comentarios en el YAML:

- **`kernel.exception`**: Sentry `ErrorListener` a prio **128**, `ApiExceptionListener` a **10**. O
  sea que Sentry ve la excepción antes de que el nuestro llame a `setResponse()` y corte la
  propagación. La ordenación que `config/packages/sentry.yaml` argumenta como load-bearing es real.
- **`sentry.capture_enabled`** = `true` en dev, `false` solo en `when@test`.

⚑ **Trampa del redactor, encontrada probando y no razonando.** `SensitiveDataRedactor::scrubText()`
lleva un patrón de DNI `\b\d{8}[A-Za-z]\b`. Un marcador tipo `SENTRY-SMOKE-BACKEND-20260902Z` sale
como `SENTRY-SMOKE-BACKEND-[redacted:dni]` — o sea que **el evento llega y parece que no ha
llegado**. La forma con guiones (`2026-09-02T09:35:05Z`) sobrevive. Quien vuelva a montar un smoke:
pasa el marcador por el redactor antes de lanzar.

---

## Las cinco filas

### 1. Producción arranca con Sentry apagado — y la guarda que lo detectaría está muerta
**Repos: `f5sign-infra` (arreglo) + `f5sign-backend` + `f5sign-signer` · la más grave**

`grep -rni sentry` sobre todo `f5sign-infra` (sin `.git`) da **0**. Ni en `docker-compose.prod.yml`,
ni en el ancla `x-backend-env` que alimenta php-fpm / worker / relay, ni en `.env.prod.example`.
Infra **no inyecta ninguna variable `SENTRY_*`**.

**Consecuencia A** — `SENTRY_DSN` se queda con el vacío de `.env` → producción no reporta nada. Es
especialmente invisible porque el DSN vacío *es* el modo desactivado de diseño (forma Dedicated de
ADR-0013): no hay nada roto que mirar, el sistema hace lo que se le pidió, y lo que se le pidió por
accidente es "no reportes".

**Consecuencia B, la que nadie había visto** — el backend no tiene `.env.prod` (sus ficheros son
`.env`, `.env.dev`, `.env.test`), y `.env` trae `SENTRY_ENVIRONMENT=development` fijo. Ese fichero
**viaja dentro de la imagen de producción**: `.dockerignore` excluye `.env.local`, `.env.*.local`,
`.env.dev`, `.env.test` — pero **no** `.env`, y lo dice explícitamente en su propio comentario; el
`COPY . .` del `Dockerfile` lo mete y el `COPY --from=builder /var/www/html` lo lleva a la etapa
final. Así que el día que alguien arregle A inyectando el DSN, **los eventos de producción llegarán
etiquetados `environment: development`**, mezclados con el ruido de dev e invisibles para cualquier
alerta apuntada a `production`. El arreglo obvio de un problema crea el otro, callado.

⛔ **Y la guarda existe, está bien argumentada, y no puede dispararse nunca.**
`config/packages/sentry.yaml` deja `environment` **sin `default::`** a propósito — `dsn` y `release`
sí lo llevan — y el comentario razona que un `SENTRY_ENVIRONMENT` ausente con DSN presente tiene que
ser fallo de arranque, *"porque un error de configuración que se disfraza del estado bueno es peor
que uno ruidoso"*. Esa protección está neutralizada: la variable **nunca llega a estar ausente**,
porque `.env` le da valor.

**Lo que hay que entender antes de arreglarlo: las tres piezas son individualmente correctas.** Que
`.env` se commitee es convención de Symfony y el `.dockerignore` lo razona. Que `environment` no
lleve `default::` es una protección deliberada. Que infra no inyecte lo que nadie le pidió es lo
normal. Nadie se equivocó — juntas neutralizan la única comprobación que existía.

Es [`BL-175`](../f5sign-backend/docs/BACKLOG.md) girado 180°: allí el miedo era que una variable
ausente cayera *dentro* de production (el default `"production"` de `@sentry/core`); aquí el default
commiteado hace que producción se disfrace de development. Misma frase: la mala configuración se lee
como la buena.

**Contraste útil** — el signer tiene A pero **no** B: su `environment` no se hornea desde un fichero
commiteado sino desde `vars.SENTRY_ENVIRONMENT`, y su workflow rompe el build si hay DSN sin
entorno. La diferencia no es el cuidado de cada lado: **un valor por defecto commiteado desarma
cualquier comprobación de "sin poner"**, y el signer no tiene ninguno.

▶ **Estado 2026-09-02, partido en dos:**
- **Backend: cerrado** (`69298eb`). `SENTRY_RELEASE` se hornea en la imagen (`ARG` en el stage
  runtime + build-arg del workflow), que es lo que `.env` afirmaba desde siempre sin que nadie lo
  hiciera. ⛔ Y **no** debe listarse además en el compose: la sintaxis de mapa define la clave aunque
  el valor esté vacío, así que una variable sin poner ahí pisa el valor horneado con cadena vacía
  (medido con un compose de dos servicios: el que llevaba la línea vio `[]`, el otro el valor bueno).
- **Infra: rama `feat/sentry-prod-env` empujada, SIN mergear.** Añade `SENTRY_DSN` (opcional) y
  `SENTRY_ENVIRONMENT` (`:?`, obligatoria) al ancla `x-backend-env`, que heredan php-fpm, worker y
  relay. ⚠ **Mergearla rompe el próximo despliegue de cualquier producción existente** hasta que su
  `.env.prod` declare `SENTRY_ENVIRONMENT` — es el fallo ruidoso que sustituye al silencioso, pero es
  una decisión con consecuencia y por eso no se ha mergeado sola. Verificado en las dos direcciones
  con `docker compose config`.

---

### 2. `before_send_transaction` sin cablear — ✅ CERRADA
**Repo: `f5sign-backend` · en `develop`, commit `13149c1` (2026-09-02)**

`config/packages/sentry.yaml` cablea **solo** `before_send`. En sentry-php,
`before_send_transaction` es una **opción separada cuyo default es un passthrough**
(`vendor/sentry/sentry/src/Options.php`, en el array de defaults), y `sentry-symfony` la expone como
su propio nodo de config.

O sea que subir `traces_sample_rate` por encima de 0 **abre un camino de egress que no toca el
redactor nunca**, y los spans llevan URLs, SQL y contexto de llamadas salientes — bastante más
superficie que un error. Es exactamente lo que ADR-0009 §4.1 prohíbe: su texto fue reescrito para
decir *"wired"* y no *"exists"* precisamente por este fallo.

⚑ El signer ya cablea las **cuatro** puertas por separado (`beforeSend`, `beforeSendTransaction`,
`beforeSendSpan`, `beforeBreadcrumb`), o sea que este lado es el que va corto.

▶ **Cableado.** `SentryBeforeSend` sirve a los dos hooks —una salida, un filtro— y redacta
descripción, `data` y `tags` de cada span; la descripción es la que lleva SQL y URLs, así que pasa
por el mismo scrub de texto que el mensaje de una excepción. Test de wiring en `SentryWiringTest`,
porque quitar cualquiera de los dos hooks es un cambio de una línea que ningún test unitario vería.

⚠ **`traces_sample_rate` SIGUE A 0, y eso es deliberado.** Lo que se ha discharged es la *mitad de
cableado* del gate de ADR-0009 §4.1; subir el número es ahora una decisión operativa ordinaria en
vez de una bloqueada. No se expone desde el compose de producción a propósito, para que encenderlo
sea un acto explícito. La mitad CORS ya estaba lista (ver fila 5), así que encender tracing es hoy
un cambio de una variable en los dos lados.

⚠ **Y «todos los sumideros» son SEIS hooks, no dos.** `before_send_check_in`, `before_send_log`,
`before_send_metric` y `before_send_metrics` siguen en pass-through. Es sano *hoy* solo porque nada
llama a las APIs que los alimentan — el SDK está confinado a `Foundation/Observability/Sentry/`. Se
deja escrito porque un conjunto eximido que hoy está vacío no devuelve nada y se lee como un
todo-en-orden: el primer llamante de cualquiera de ellos reabre esta fila y no tendrá motivo para
saber que existe.

---

### 3. Los rechazos de negocio se reportaban como errores — ✅ CERRADA
**Repo: `f5sign-backend` · en `develop`, commit `93e1ae1` (2026-09-02)**

⚑ **Esta fila creció el 2026-09-02.** Empezó como *"los 401 salen huérfanos"* (sin `request_id` ni
`deployment_mode`, porque el enricher corre a prio -10 después de los cuatro listeners de authn).
Daniel señaló lo que faltaba: **esos eventos no deberían salir siquiera**. Al mirarlo, el problema
era mucho mayor que el 401.

Sentry corre a prio **128** y `ApiExceptionListener` a **10**, así que Sentry ve la excepción
**original**, antes del mapeo a 4xx. Y la familia kernel entera mapea a 4xx: `NotFoundException`
(404), `ConflictException` (409), `AuthenticationRequiredException` (401), `AuthorizationDenied`
(423), `TemporallyRefused` (429), `InvariantViolation` (422). **Ninguna estaba en
`ignore_exceptions`**, que solo tenía formas de framework. O sea que *todo rechazo de negocio del
producto* —enlace caducado, sobre ya firmado, OTP rate-limitado— era un evento de error. Con cuota
gratuita, un pico de enlaces caducados se la come.

⛔ **No es un juicio nuevo sobre los 4xx: el repo ya lo tomó dos veces y Sentry era el que iba por
libre.** `ApiExceptionListener::log()` loguea un 4xx a `info` sin stack y un 5xx a `error` con
stack, y ADR-0009 registra ese reparto. El cambio alinea el tercer canal con los otros dos.

▶ **Hecho**: `ignore_exceptions` pasa a nombrar la familia kernel **por el padre
abstracto** (`is_a(..., true)` casa jerarquía, así que cubre toda excepción de cualquier BC que
herede, hoy y futuras) más `UnauthorizedHttpException`, que lanza el seam de authn en 8 sitios y es
hermana de `BadRequestHttpException`, no hija. Con test de censo que recorre
`src/F5Sign/Kernel/Exception/` y **falla ante un subtipo sin clasificar**, más un hermano que fija
que `DomainException` (el padre) NO se silencie nunca — silenciarlo eximiría el arma `default` del
`match`, que es donde cae lo aún no clasificado.

⚑ **Las dos guardas se comprobaron por sabotaje, no por confiar en el verde.** Quitar
`ConflictException` de la lista hace fallar el censo **nombrando ese tipo exacto**; meter el padre
hace fallar la guarda hermana **y deja el censo pasando en verde**, porque con el padre listado todo
casa. Eso último es el dato que justifica la guarda hermana: sin ella, la simplificación plausible
—"pon el padre y quita los seis hijos"— pasaría los gates silenciando de más.

⚠ **LO QUE ESTE CAMBIO CUESTA, Y HAY QUE SABERLO.** En una primera respuesta dije que un fallo
sistémico de auth *"sigue en los logs"*. **Es falso en producción** y se corrigió el mismo día: el
handler de prod está a `level: notice` (`config/packages/monolog.yaml`) y un 4xx se loguea a `info`,
que está por debajo. Así que tras este cambio, **una tormenta de 401 no se ve ni en Sentry ni en los
logs de producción por defecto**. Lo que queda: el log a `error` del rate limiter cuando falla
abierto, y métricas de volumen/tráfico. ▶ Si se quiere cerrar, la palanca es subir el nivel de los
rechazos de auth a `notice` en `ApiExceptionListener::log()` — **no se hizo**, porque afectaría a
todos los 4xx y es decisión aparte.

⚑ **El split del enricher sigue teniendo sentido, pero por otro motivo.** Ya no por el 401 (que deja
de emitirse), sino por el caso raro y grave: `TenantRequestListener` lanza un `LogicException`
cuando una ruta no declara `_authn` — un 500 de misconfiguración que hoy llegaría **huérfano**, y es
justo el que más querrías correlacionar. La asimetría que lo permite: de los cuatro tags del
enricher, `deployment_mode` (escalar) y `request_id` (acuñado en `kernel.request` prio 240) **no
dependen de authn**; solo `tenant_id` y `client_id` lo necesitan. ⛔ **No subas la prioridad del
enricher** — haría desaparecer esos dos de todos los eventos.

---

### 4. `user.geo`: Sentry deriva la ciudad de la IP en el ingest
**Repo: ninguno — configuración de org · ⚠ asimétrico, no lo trates como simétrico**

- **Signer: dato personal real.** El SDK de navegador conecta desde la máquina del firmante, así que
  la IP que Sentry geolocaliza es la suya. En un producto eIDAS eso es dato regulado.
- **Backend: ruido.** La conexión al ingest sale del servidor. Hoy es la salida a internet de la
  máquina de desarrollo; en producción sería el datacenter. **Ningún firmante toca el ingest por el
  lado del backend.**

⛑ **No lo busquéis en el `before_send`, que es donde lo buscaría cualquiera.** Prueba de que es
derivación en el ingest: el evento del backend viajó **sin bag de user** (ruta `Authn::NONE`, sin
`client_id`, y `SentryBeforeSend::reduceUser()` deja el user a null cuando no hay id) y Sentry le
puso geo igualmente. Ocurre **después** de nuestro `before_send`; no hay hook nuestro por detrás.

▶ **Arreglo**: *Prevent Storing of IP Addresses* en Security & Privacy de la org (y/o del proyecto).
Si va como "aparece en los dos" se va a leer como problema simétrico y se va a arreglar a medias.

---

### 5. Lo que ya está bien, para que nadie lo vuelva a tocar
**Repo: `f5sign-backend` · verificado en vivo contra el stack, no leído del código**

- `Access-Control-Allow-Headers: Authorization, Content-Type, F5Sign-Declared-Subject, sentry-trace,
  baggage` — **el signer puede encender la propagación sin que el navegador bloquee la petición.**
  Esta era la mitad que, de faltar, no degrada el tracing: **rompe la firma**, y no reproduce en
  desarrollo porque el devProxy del signer hace same-origin.
- `Access-Control-Expose-Headers: Retry-After, X-Request-Id` — el script cross-origin puede leerla.
- `X-Request-Id` se emite **también en respuestas de error** (verificado sobre un 401 y un 500).
- Un `X-Request-Id` entrante **se ignora**: se acuña siempre uno nuevo (v7). Verificado mandando uno
  falso y viendo que la respuesta trae otro.

---

## Estado operativo, ahora mismo

⚠ **El DSN sigue puesto en `f5sign-backend/.env.local` (gitignored), y el del signer en
`f5sign-signer/.env`.** Mientras estén, **la stack compartida reporta a Sentry cualquier error de
dev de cualquiera**, contra el tier gratuito. Van a `environment: development`, que es separable de
un vistazo, así que el coste es cuota y ruido — no contaminación de producción. **Decisión
pendiente**: si se quitan, se quitan los dos.

DSN del backend (client key `Default`, org `factor-5`, **región DE**):
`https://…@o4511415658348544.ingest.de.sentry.io/4511943526514768` — el valor completo está en
`.env.local`, no se copia aquí.

El checkout principal del backend quedó **limpio**: ruta temporal borrada, `git status` como estaba,
cero commits.
