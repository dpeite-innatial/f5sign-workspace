# Traspaso al signer — el commit y el rechazo llevan lo que declara el navegador (`evidence`)

| | |
|---|---|
| **Origen** | rama `feat/browser-reported-evidence` (desde `develop` `f0e4b7fb`), **sin mergear, sin desplegar** · commit `f649bec6`, el último que cambia código o texto publicado · [TASK-045](../tasks/TASK-045-browser-reported-evidence-at-the-commit.md) |
| **Fecha** | 2026-10-14 |
| **Repos afectados** | **signer** |
| **Naturaleza** | aditivo: un miembro nuevo y opcional, `evidence`, en el commit y en el rechazo. Un cliente que no lo manda firma y rechaza como hoy |
| **Acción requerida** | quitar el `GEO_IP` falso · dejar de mandar `webgl_hash` y `canvas_hash` · medir el tiempo visible por documento · mandar `evidence` en `commit` y `decline` · encender la captura solo con el flag nuevo, con el backend desplegado y con el aviso de privacidad al día |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`POST /api/v1/signing/commit` y `POST /api/v1/signing/decline` aceptan el mismo miembro opcional `evidence`**
  (esquema `BrowserEvidence` de la especificación OpenAPI). Ausente o `null` = no recogido. Todos sus miembros son
  opcionales:
  - **`geolocation`**: `status` siempre (`GRANTED`, `DENIED`, `UNAVAILABLE`, `TIMEOUT`). `latitude` (−90 a 90),
    `longitude` (−180 a 180), `accuracy_m` (0 a 1 000 000, en metros) y `captured_at` (RFC 3339 con
    desfase) van **con `GRANTED` y solo con él**, los cuatro. Con otro estado, sin coordenadas.
  - **`device`**, cada campo opcional:
    - `timezone`: texto de 1 a 64 caracteres, solo `A-Z a-z 0-9 _ + / -` (nombre IANA; se comprueba la forma, no que exista).
    - `languages`: de 1 a 10 etiquetas BCP 47, cada una de 2 a 35 caracteres de `A-Z a-z 0-9 -`, en el orden del navegador.
    - `screen`: `width` y `height` enteros de 1 a 32 768, `pixel_ratio` mayor que 0 y como mucho 16. Se toma entero, como un solo campo; los tres son obligatorios dentro de él.
    - `platform` y `platform_version`: texto de 1 a 32 caracteres.
    - `model`: texto de 0 a 64 caracteres (puede ir vacío: los client hints de un escritorio dan un modelo vacío).
    - `touch`: booleano.
    - `client_clock_at_act`: RFC 3339 con desfase, el reloj del dispositivo en el acto.
    - Un texto con un carácter de control es inválido.
  - **`reading`**: lista de como mucho **100** entradas, una por documento, con `document_id` (uuid **en
    minúsculas**, tal como lo lista la sesión), `pages_total` (entero de 1 a 10 000), `max_page_seen` (entero de 1
    a `pages_total`), `read_to_end` (booleano) y `visible_ms` (entero de 0 a 86 400 000, 24 horas). Los cinco son
    obligatorios en cada entrada. Los números de página son los del navegador: el backend no los compara con el documento.
- **Los miembros desconocidos se ignoran** (el esquema no es estricto): ver más abajo por qué importa al encender la captura.
- Las formas exactas, con todos los límites, están en `BrowserEvidence` de la especificación OpenAPI; los límites
  de arriba son los de esa especificación.
- **`Accept-Language` no va en `evidence`.** El servidor lo lee de la cabecera de la petición, como la IP y el agente de usuario; el cliente no lo manda en el cuerpo. `device.languages` es la lista que declara el navegador, y se registra y se muestra aparte.
- Los trazos biométricos siguen igual: se validan y se descartan.

## Nunca rechaza

Un bloque mal formado **no cambia la respuesta**: el commit y el rechazo contestan lo mismo que sin `evidence`.
Lo mal formado se descarta por una unidad fija y el resto se guarda:

- `geolocation`: **entera**. Se descarta con coordenadas junto a un estado distinto de `GRANTED`, con `GRANTED` al que
  le falta alguna de las cuatro, con un valor fuera de rango, sin `status` o con un `status` que no es uno de los cuatro.
- `device`: **campo a campo**; un campo inválido se descarta y los demás se guardan. `screen` cuenta como un solo campo. `languages` con más de 10 etiquetas, o que no es una lista, se descarta entero.
- `reading`: **entrada a entrada**. Una entrada de un documento que este destinatario no puede leer, o una segunda
  entrada del mismo documento, se descarta. Pasadas 100 entradas solo se leen las 100 primeras. Un `reading` que no es una lista se descarta entero.
- `evidence` que no es un objeto se descarta entero.

Cada descarte se registra por miembro y motivo, **nunca por valor**. Los motivos son `WRONG_TYPE`, `OUT_OF_RANGE`,
`TOO_LONG`, `MISSING_FIELD`, `NOT_ALLOWED_FOR_STATUS`, `NOT_READABLE`, `DUPLICATE` y `TOO_MANY`.

⚠ **Consecuencia para el cliente**: un descarte es un defecto del cliente y **solo se ve en la pista de auditoría y en
los registros**, no en la respuesta. Probad el cuerpo contra el esquema publicado antes de enviarlo.

## Lo que el signer tiene que hacer

1. **Quitad el `GEO_IP` falso.** `useGeolocation.ts` construye `{lat: 0, lng: 0, acc: 50000, source: GEO_IP}` cuando no hay
   fijación, sin ninguna consulta Geo-IP detrás: tal cual, pondría al firmante en el golfo de Guinea. Mandad `status`
   (`DENIED`, `UNAVAILABLE` o `TIMEOUT`) **sin coordenadas**; coordenadas solo con `GRANTED`. `source` no existe en el contrato.
2. **Sin canvas ni WebGL.** `useDeviceFingerprint.ts` deja de mandar `webgl_hash` y `canvas_hash`: una huella así
   necesita consentimiento (Directiva ePrivacy, art. 5.3) y queda fuera del contrato (el backend los ignoraría como desconocidos).
3. **Medid el tiempo visible.** `useDocumentReadThrough.ts` guarda la página más profunda por documento y ningún tiempo visible;
   el contrato pide `visible_ms` por documento, y `document_id` en minúsculas para un documento que la sesión lista.
4. **Mandad `evidence` en `commit` y en `decline`**, con la misma forma en los dos.
5. **Cuándo encenderlo.** Un flag de capacidad nuevo vuelve a encender la captura en modo real. Ponedlo a `true` **solo
   cuando la especificación DESPLEGADA publique `BrowserEvidence`**: un backend anterior ignora los miembros
   desconocidos y el bloque se perdería sin avisar (BL-177). `hasRichSignFlow()` se queda como está para los demás flujos.
6. **Aviso de privacidad.** La captura sigue apagada mientras el aviso del firmante no nombre los datos de ubicación,
   de dispositivo y de lectura (TASK-045 §6). Si el aviso basta es una pregunta para legal.

## Lo que ve el remitente

La pista de auditoría dice cada valor como **declarado por el navegador** del firmante, en un bloque aparte de lo que
el servidor observa. En un rechazo, la IP y el navegador se rotulan como los del rechazo. Un miembro ausente consta
como no declarado; uno descartado, como descartado por mal formado.
