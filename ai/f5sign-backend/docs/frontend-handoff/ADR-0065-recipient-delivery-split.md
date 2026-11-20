# Handoff — `outcome` se parte en dos: `outcome` + `delivery`

| Campo | Valor |
|---|---|
| **Naturaleza** | ⛔ **Breaking**, y es el único breaking de este lote: `DELIVERY_FAILED` **desaparece** del enum `outcome`. Todo lo demás es aditivo |
| **Origen** | [ADR-0065](../adr/ADR-0065-recipient-delivery-is-its-own-dimension.md), pasos 2 y 4 |
| **Estado** | En rama, **sin desplegar**. Verificable contra `doc.json` cuando aterrice |
| **Impacto medido hoy** | **Ninguno.** Comprobado el 2026-09-01: el dashboard no hace ninguna llamada al backend (`useFetch`, `$fetch`, `/api/v1`: cero apariciones) y no lee `outcome` ni `recipients`. Por eso el corte es limpio y sin ventana de deprecación |

## Qué cambia

El objeto `Recipient` respondía a dos preguntas distintas en un solo campo. Ahora son dos:

| Miembro | Pregunta | Valores |
|---|---|---|
| `outcome` | **qué hizo el destinatario** | `PENDING` · `COMPLETED` · `DECLINED` · `DELEGATED` · `SKIPPED` |
| `delivery` | **qué consiguió nuestro canal, POR DESTINO** | `null`, o un objeto `{ "EMAIL_ADDRESS": { "state": …, "observed_at": … }, "MOBILE_PHONE": {…} }` con `state` en `NOT_ATTEMPTED` · `SENT` · `DELIVERED` · `FAILED` |

⛔ **`delivery` es un MAPA, no un valor.** Un destinatario puede tener dirección y teléfono, y lo que
pasó con uno no dice nada del otro: un SMS aceptado no significa que el email llegara. Cada destino trae
su propio `state` y su propio `observed_at`.

⚠ **Una clave AUSENTE es *desconocido* para ese destino**, no "no se ha intentado". Un destinatario cuyo
email rebotó y cuyo teléfono nadie ha usado publica **una** clave, no dos — inventar la segunda sería
afirmar algo que no sabemos.

**El que se va:** `outcome: "DELIVERY_FAILED"`. Un destinatario al que no pudimos llegar ahora es
`outcome: "PENDING"` **y** `delivery: "FAILED"`.

## Por qué, en una frase que importa para vuestra UI

`DELIVERY_FAILED` nunca fue un desenlace de la pata del destinatario — el paso nunca se cerraba sobre él,
porque no era terminal. Era una anotación sobre una pata que **seguía pendiente**, y al ocupar el único
campo disponible borraba justamente el `PENDING` que anotaba. Consecuencia práctica que quizá hayáis
notado: un reenvío que fallaba **ponía** la bandera y uno que funcionaba **no podía quitarla**.

## Qué hacer

1. **Si ramificabais sobre `outcome === 'DELIVERY_FAILED'`, mirad `delivery === 'FAILED'`.** La pata de
   esa persona es `PENDING`, que es lo que siempre fue.
2. **No pintéis "no se pudo entregar" como un estado terminal.** No lo es y nunca lo fue: esa persona
   puede firmar perfectamente. El enlace se acuña **antes** de intentar la entrega, así que alguien a
   quien se lo leyeron por teléfono completa con normalidad.
3. ⛔ **`delivery: null` significa *desconocido*, NO *no se ha intentado nada*.** Son filas anteriores a
   este campo: nunca se registró en este lado que un envío hubiera salido bien, así que no hay verdad que
   rellenar. Pintadlo como "sin información", no como "pendiente de enviar".
4. ⚠ **`DELIVERED` no llega nunca hoy, y está publicado a propósito.** Todos los canales que existen
   topan en `SENT` — que significa "el proveedor lo aceptó", no "llegó" — porque el receipt seam está
   diferido. Está en el enum para que el vocabulario no cambie de forma cuando llegue. **No construyáis
   un badge de "entregado"**: no puede encenderse.
5. La recuperación no cambia: `POST /envelopes/{id}/recipients/{recipientId}/corrections`, que devuelve
   `delivery` a `NOT_ATTEMPTED` y reinvita. Sigue gastando una de tres.

## Cómo verificarlo cuando aterrice

1. `components.schemas.Recipient.properties.outcome.enum` **no** contiene `DELIVERY_FAILED` y tiene cinco
   miembros.
2. `…properties.delivery.enum` existe y tiene los cuatro, `nullable: true`.
3. `…properties.delivery_observed_at` existe.
4. Un `GET /envelopes/{id}` de un sobre con un destinatario rebotado trae `outcome: "PENDING"` y
   `delivery: "FAILED"`.

⚑ Los dos primeros los sostiene un censo bidireccional en `OpenApiSpecTest`, así que el enum publicado y
el enum PHP no pueden separarse sin que la suite se ponga roja — incluido `DELIVERED`, que es el miembro
que ningún camino de producción escribe y que por eso mismo un spot-check no vería.
