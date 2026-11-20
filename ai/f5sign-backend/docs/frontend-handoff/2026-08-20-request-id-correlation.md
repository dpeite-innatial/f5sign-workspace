# Traspaso al frontal — cada respuesta trae un `X-Request-Id`, y podéis leerlo

| | |
|---|---|
| **Origen** | rama `sentry` · commit `63595f3`. ✅ **Publicado en `origin/develop` el 2026-08-20.** La cabecera CORS que lo acompaña (`sentry-trace`, `baggage`) entró antes, en `47344ee`. |
| **Fecha** | 2026-08-20 |
| **Repos afectados** | **signer** (lo pidió y tiene el hueco escrito) y **dashboard** (le sirve igual, no lo ha pedido) |
| **Naturaleza** | **aditivo**. No rompe nada: una cabecera de respuesta nueva y un nombre más en `Access-Control-Expose-Headers`. Ignorarlo no cambia ningún comportamiento. |
| **Acción requerida** | signer: cablear la lectura en el `$fetch` centralizado y encender la propagación de trazas. Dashboard: opcional. |
| **Status** | Pending |

## Lo que hay

**1. Toda respuesta de la API trae `X-Request-Id`.** Un UUIDv7 acuñado por petición. **Incluidas las
respuestas de error** — el 500 es justo el caso que más lo necesita, y hay un test escrito sobre una
respuesta 500 precisamente para que a nadie se le ocurra meter un `isSuccessful()` por delante.

**2. Está en `Access-Control-Expose-Headers`, así que un script cross-origin puede leerlo de
verdad.** Esto no es un detalle: un navegador entrega al script solo las cabeceras CORS-safelisted, y
sin nombrarla ahí la cabecera **llega, es invisible, y `getResponseHeader()` devuelve null sin que
nada reporte un error en ninguna parte**. La lista completa hoy es `Retry-After, X-Request-Id`.

**3. ⛔ Si mandáis un `X-Request-Id`, se ignora.** El backend acuña siempre el suyo y os devuelve otro
distinto. No es un descuido, es la decisión:

- Un id suministrado por el llamante **se lee como autoritativo en una línea de log y no lo es** — la
  misma razón por la que se borraron `X-Tenant-Id` y `X-Acting-User-Id` en el credential cutover.
- Es **envenenable**: un cliente que mande siempre el mismo id colapsa todos los registros en un solo
  hilo, y uno que mande el de otro tenant empalma su tráfico con el ajeno. Ninguna de las dos cosas
  se detecta a posteriori.
- Es **entrada sin acotar en un campo de log y en un tag**, o sea inyección de saltos de línea y
  explosión de cardinalidad en los dos sitios peor preparados para defenderse.

Hay un test que asserta que el id publicado **no es** el que llegó, y no solo que exista alguno: un
listener que hiciera eco pasaría la aserción débil.

**4. `sentry-trace` y `baggage` están permitidos en el preflight.** Podéis adjuntarlos. ⚠ Esto era
**bloqueante y no cosmético**: una cabecera que el preflight no permite hace que el navegador
**rechace la petición entera** antes de enviarla. No degrada el tracing — rompe la firma. Y no
reproduce en desarrollo, donde el devProxy del signer hace same-origin y no se emite preflight.

## Cómo usarlo

Leedlo en **todas** las respuestas, no solo en el `catch`, y cachead el último. En el signer el sitio
es el `$fetch` centralizado de `SigningApi.real.ts` — un punto único.

Cuando no haya id, que el tag quede **ausente, no vacío ni inventado**. Hay dos casos reales donde no
lo habrá y son legítimos: un fallo de red, CORS o timeout (no hay respuesta que leer) y un error
puramente de SPA (render, arranque, un gesto en el canvas) que nunca tocó la API.

## Lo que esto NO es todavía

⚠ **Ningún evento ha salido nunca hacia Sentry desde el backend.** La integración está completa y con
gates verdes: el redactor está cableado como `before_send`, redacta lo que debe, y con DSN vacío no
se manda nada. Lo que **no** está demostrado es que un error llegue a un ingest y llegue censurado.

Esa comprobación es [`BL-174`](../BACKLOG.md) — el smoke conjunto de EP27, «provocar un 500 real y ver
los dos eventos, PHP y JS, con el mismo `request_id`».

⛔ **Y su bloqueo cambió el 2026-08-20, a uno peor.** El proyecto ya existe (org `factor-5`, región
`de.sentry.io`), pero la **cuota de errores de la organización está agotada**: la ingesta responde
`429` con `organization:error_usage_exceeded`, el SDK hace backoff y descarta el evento en local.
⚠ **Las transacciones y los spans sí entran** — es otra categoría de cuota — así que el tracing se
verifica bien mientras los errores se pierden, y lo único que delata la pérdida es un item
`client_report` dentro del envelope. Desde la aplicación es **indistinguible de una integración que
funciona y que nadie está mirando**.
⛔ **Es de nadie por defecto y por eso está escrito**: la suite del backend sale verde sin él, la del
signer sale verde sin él, y las dos partes pueden reportar "terminado" mientras la única cosa para la
que existe el epic no se ha observado ni una vez.
