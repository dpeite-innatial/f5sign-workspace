# Traspaso al frontal — el registro de auditoría de un sobre terminado se descarga por API

| | |
|---|---|
| **Origen** | rama `feat/evidence-audit`, **mergeada en `develop` el 2026-09-29, sin desplegar** · la ruta: `5752fdf1` · su 409 ante un PDF alterado: `99de3290` · [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.10 · el contenido del registro se rehízo el 2026-10-01 en la rama `feat/trail-recut`, para seguir a ADR-0073 (ADR-0072 §9) · la forma de los textos cifrados: rama `feat/encrypt-the-other-members` ([ADR-0096](../adr/ADR-0096-key-management-encrypts-the-logs-free-text-under-erasable-keyrings.md) §2.9) |
| **Fecha** | 2026-09-29 · actualizado 2026-10-01, 2026-10-14 y 2026-11-03 |
| **Repos afectados** | **integradores con clave de máquina** (`dashboard-sf`). El **dashboard** no: la ruta no acepta la sesión de usuario |
| **Naturaleza** | aditivo: una ruta nueva, y ninguna ruta existente cambia |
| **Acción requerida** | ninguna. Opcional: ofrecer la descarga del registro de los sobres terminados |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`GET /api/v1/envelopes/{id}/audit-trail`** devuelve el registro de auditoría del sobre: un PDF/A-3a en
  español, sellado por la plataforma, aparte de los documentos firmados. Se descarga como
  `registro-<id del sobre>.pdf`. Las formas exactas están en el `doc.json` de la API, etiqueta `Audit trail`.

> ⚑ **2026-10-28:** el nombre cambió; ver [TASK-076](TASK-076-integrator-signer-download-names.md).

- **Autenticación:** la clave de máquina y la cabecera `F5Sign-Declared-Subject`, como en las demás rutas de
  integrador. Cualquier clave del tenant descarga el registro de cualquier sobre del tenant.
- **Cuándo existe:** la plataforma emite el registro poco después de que el sobre termina, en `COMPLETED`, con
  acuerdo o sin él (`outcome`: `AGREED` o `NOT_AGREED`). Un sobre que se cierra sin acuerdo (por ejemplo,
  anulado, rechazado o caducado) no termina al cerrarse: termina cuando han llegado las firmas admitidas
  antes del cierre y, si alguien intervino, cuando se ha sellado. Lo emite una vez, y después no cambia.
- **Respuestas:**
  - `200`: el PDF, con un `ETag` fuerte (el SHA-256 de los bytes) y `Cache-Control: private`.
  - `304`: con `If-None-Match` y ese mismo `ETag`.
  - `404`: una sola respuesta para un sobre que no existe, que es de otro tenant, que no ha terminado, o cuyo
    registro no se ha emitido todavía. Para un sobre terminado, la misma petición un poco después puede dar 200.
  - `409 AUDIT_TRAIL_UNAVAILABLE`: el registro consta, pero su PDF no se puede leer. Repetir da la misma
    respuesta, salvo que la plataforma restaure el PDF.
  - `400`: falta la cabecera `F5Sign-Declared-Subject`, o no es válida.
- **El anexo del PDF.** El PDF lleva adjunto, como fichero asociado PDF/A-3, el JSON con el que se genera la
  página (`"schema": "f5sign.audit-trail/1"`). Son los mismos datos que la página, **datos personales
  incluidos**, minimizados igual que en la página: email y teléfono enmascarados, IP y user agent completos,
  ningún número de documento de identidad (ADR-0072 §2.6). Tratad el anexo con el mismo cuidado que el PDF.
  **Esto corrige el apartado 10 de [TASK-044 — dashboard-sf](TASK-044-dashboard-sf-field-values-and-reservations.md)**,
  que dice que el anexo lleva «los compromisos y la raíz de la cadena, sin datos personales». Ese era el primer
  planteamiento, y el mantenedor lo cambió el 2026-09-21.
- **La forma del anexo cambió el 2026-10-01**, antes del primer despliegue, y sigue siendo
  `f5sign.audit-trail/1`, porque nadie la leía aún. Si ya la leéis en pruebas, estos son todos los cambios:
  - **Quitado:** `terminal.kind` (`COMPLETED` o `VOIDED`). El registro termina siempre en el final del sobre
    (`ENVELOPE_COMPLETED`). Leed `terminal.outcome.kind`: `AGREED` o `NOT_AGREED`.
  - **Mismo nombre, otro sentido:** `terminal.at` y `terminal.position`. Donde antes `kind` era `VOIDED`, ya no son
    los del cierre, sino los del final del sobre. El cierre está en `terminal.closed_at` y el acuerdo en
    `terminal.agreed_at`, los dos nuevos.
  - **Movidos a `terminal.outcome` y renombrados:** `by` pasa a `ended_by`, `declined_by` a
    `ended_by_recipient_id`, `cause` a `end_cause`, `reason` a `end_reason` y `signed_before` a
    `signed_before_close`. `ended_by` está en los dos resultados y vale lo mismo que el `ended_by` del sobre en
    la API: el remitente que anuló el sobre, o que lo cerró con `POST /envelopes/{id}/close`. En cualquier
    otro final es `null`.
  - **Sustituido:** `terminal.sessions_closed`, una lista de ids deducida del estado, por
    `terminal.revocations`: las sesiones que la plataforma revocó antes del final, leídas del log, cada una
    con `recipient_id` y `at`.
  - **Renombrado:** en cada parte, `act` pasa a `outcome`, con `kind` `SIGNED`, `DECLINED` o `RELEASED`. El
    último es nuevo y lleva `at`, `release_reason` y `released_by`.
  - **Quitado:** `documents[].seal.purpose`.
  - **Nuevo:** `envelope.expiry`, la caducidad y sus prórrogas.
- **El anexo gana las invitaciones de cada parte (2026-10-14, TASK-059).** Sigue siendo `f5sign.audit-trail/1`: se
  añade un campo, un código de limitación y un motivo de «no consta», y ninguno cambia de sentido. Si leéis el anexo,
  ignorad lo desconocido y no falléis por ello:
  - **Nuevo:** `personal.invitations` en cada parte, una declaración (`stated`, o no consta con su motivo). Si consta,
    es una lista, vacía si no hubo nada que enviar, con una entrada por resultado registrado y por destino
    rechazado: `purpose` (`INVITATION` o `RESEND`), `outcome` (`SENT`, `FAILED`, `REFUSED`,
    `NOT_SENT_NO_REACHABLE_CHANNEL` o `DELIVERED_BY_INTEGRATOR`), `channel` (`null` si el resultado no nombra
    destino), `at` y `contact` (enmascarado; `null` si no hay destino).
  - **Nuevo motivo de «no consta»:** `OUTCOME_NOT_RECORDED`, cuando el paso de la parte se activó y el flujo no
    guarda ningún hecho de invitación, como en todo flujo escrito antes de TASK-056.
  - **Nueva limitación:** `DELIVERY_RECEIPT_NOT_RECORDED`, presente si alguna invitación consta como `SENT`:
    `SENT` significa entregada a un proveedor, no recibida, porque no se registra ningún acuse.
  - El PDF imprime lo mismo. Las formas exactas están en ADR-0072 y ADR-0078 §2.5.
- **Cambia la forma de cuatro campos del anexo (2026-11-03, ADR-0096 §2.9).** El log guarda cifrado el texto que
  escribe una persona, y el anexo lleva ese texto en dos formas: `{"recorded": ..., "reading": ...}`. Sigue siendo
  `f5sign.audit-trail/1`, porque nada está desplegado. Si ya lo leéis en pruebas, estos son todos los cambios:
  - **`recorded`** es el valor tal como lo guarda el log. **`reading`** es una declaración de lo que imprime la página:
    `{"stated": true, "value": ..., "source": ...}` o `{"stated": false, "reason": ...}`. Leed el texto en `reading`,
    nunca en `recorded`.
  - **Pasan a las dos formas:** `envelope.title`, `terminal.outcome.end_reason`, `parties[].outcome.reason` en un
    rechazo, y `parties[].outcome.reservation.text` con `kind` `WRITTEN`.
  - **`envelope.title`** sale ahora del log, no de la fila del sobre. El texto es el mismo, porque nada cambia un título.
    Es `null` si el flujo no registra la creación del sobre, y la página imprime «No consta».
  - **`terminal.outcome.end_reason`:** en una anulación sin motivo, o con un motivo en blanco, `recorded` es `null` y
    `reading` dice que no se dio ninguno. En un final que no decidió un remitente, `end_reason` sigue siendo `null`.
  - **Nuevos motivos de «no consta»:** `ERASED`, cuando la clave del texto se destruyó, y `UNREADABLE`, cuando el valor
    está dañado. Hoy nada destruye una clave.

## Lo que el frontal tiene que hacer

Nada es obligatorio. Para ofrecer el registro:

1. Pedirlo solo para sobres en `COMPLETED`, con la clave de máquina y `F5Sign-Declared-Subject`.
2. Tratar un 404 justo después del final del sobre como «todavía no»: reintentar unos segundos después, con un
   límite de intentos.
3. Tratar `409 AUDIT_TRAIL_UNAVAILABLE` como definitivo: mostrar «no disponible, contacte con soporte», sin
   reintentar en bucle.
4. Si lo cacheáis, guardar el `ETag` y revalidar con `If-None-Match`.

## Lo que NO está listo todavía

- **Nada está desplegado.** Mientras el `doc.json` que os sirven no publique la ruta, la ruta no
  existe para vosotros (regla 4 del [README](README.md)).
- **Un sobre cerrado que no llega a terminar no tiene registro** hasta que termina: por ejemplo, si una firma
  queda aparcada o el sello falla una y otra vez. La ruta responde 404 mientras tanto (ADR-0072 §3.2).
- **Si la emisión falla**, por ejemplo porque el servicio de firma no responde, la plataforma la reintenta.
  Agotados los reintentos, la emisión queda aparcada para un operador, y la ruta responde 404 mientras tanto. El
  barrido que la recuperaría sin operador no está construido (ADR-0072 §2.10).
- **Ningún aviso de que el registro está listo:** ni webhook ni campo en el sobre. Hoy solo se sabe pidiéndolo.
- **El nombre del tenant** que muestra el registro es su identificador de alta, no su razón social
  ([`BL-299`](../BACKLOG.md)).
- **El sello del propio registro:** el registro dice el sello que lleva de verdad, leído de sus propios bytes.
  Mientras no haya una TSA y un certificado de sello reales, ese sello valida `INDETERMINATE`, y el registro lo
  dice (ADR-0072 §2.7).
- **El dashboard no puede descargarlo:** la ruta solo acepta la clave de máquina. No hay nada decidido sobre una
  ruta para la sesión de usuario.
- **Los firmantes no reciben el registro** ([`BL-280`](../BACKLOG.md)).

## Lo que NO existirá, y por qué

- **Un registro regenerado a petición.** La plataforma emite un registro por sobre y no lo reescribe: es una
  prueba sellada de lo que constaba cuando el sobre terminó, así que lo que pase después no lo cambia
  (ADR-0072 §2.1, §2.10).

## Cómo verificarlo desde el frontal

Con un `doc.json` que publique la ruta: completar o anular un sobre, esperar a que el sobre esté en
`COMPLETED`, y pedir `GET /api/v1/envelopes/{id}/audit-trail` con la clave y la cabecera. Primero responde 404, y en nuestras pruebas
del 2026-09-28 respondió 200 a los pocos segundos: `Content-Type: application/pdf`, un `Content-Disposition` con
`registro-<id>.pdf` y un `ETag`. El PDF lleva un solo adjunto, un JSON con `"schema": "f5sign.audit-trail/1"`.
La misma petición con `If-None-Match: <ETag>` responde 304. El mismo id con la clave de otro tenant responde 404,
y sin la cabecera responde 400.

> ⚑ **2026-10-28:** el nombre cambió; ver [TASK-076](TASK-076-integrator-signer-download-names.md).
