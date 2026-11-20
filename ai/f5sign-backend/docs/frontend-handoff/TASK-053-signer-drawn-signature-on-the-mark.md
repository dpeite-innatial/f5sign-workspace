# Traspaso al frontal — la firma dibujada o escrita se envía con el commit y se estampa en cada marca

| | |
|---|---|
| **Origen** | rama `feat/drawn-signature-on-mark` (desde `develop` `36ccbd3f`), **sin mergear, sin desplegar** · commit `a6827706`, la punta de la rama al escribir esto y el último commit que cambia código o texto publicado · [TASK-053](../tasks/TASK-053-the-recipients-drawn-signature-on-their-mark.md) |
| **Fecha** | 2026-10-07 |
| **Repos afectados** | **signer** |
| **Naturaleza** | aditivo: dos miembros nuevos y opcionales en el commit, y dos valores de `config` que dejan de ser fijos. Un cliente que no los manda firma como hoy, con el nombre solo |
| **Acción requerida** | rasterizar la firma (DRAW y TYPE) a PNG y mandarla como `signature_image` cuando `config.biometric_capture_enabled` es `true` · mandar los trazos como `biometric_data` con el consentimiento · tratar dos 422 nuevos |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`GET /api/v1/signing/session`: `config.biometric_capture_enabled` y `config.consent_biometric_required` ya
  no son siempre `false`.** Valen `true` exactamente donde el commit acepta la imagen: el sobre firma en
  `SEQUENTIAL_PADES` (cada destinatario firma el PDF con su propia firma incremental) **y** este destinatario
  tiene al menos una marca visible. Valen `false` en `SINGLE_SEAL` (un único sello de la empresa, sin marca de
  ningún destinatario) y para un destinatario cuyas firmas no tienen colocación (firma sin marca visible). El
  backend decide las dos cosas con la misma regla, así que **el flag basta: no hace falta mirar ni el rol ni el
  modo de firma**. `allowed_signature_modes` sigue siendo `['DRAW', 'TYPE']`. ⚑ Desde TASK-054 es el ajuste de
  cada destinatario y el commit exige `signature_mode`: ver
  [TASK-054-signer-signature-modes.md](TASK-054-signer-signature-modes.md).
- **`POST /api/v1/signing/commit` acepta `signature_image`**: la firma del destinatario como PNG en base64
  **sin** el prefijo `data:image/png;base64,`. Se estampa **tal cual llega, sin recodificar**, en **cada marca
  visible de cada documento** que firma el destinatario: la imagen arriba y su nombre debajo. Sin
  `signature_image` la marca lleva el nombre solo, como hasta ahora.
- **`POST /api/v1/signing/commit` acepta `biometric_data` y `biometric_consent`**: los trazos de una firma
  DRAW. ⚠ **Hoy se validan y se descartan**: no se guardan ni se registran en ningún sitio (TASK-053 §4 D7).
  Nunca rechazan un commit: un bloque mal formado, sin consentimiento o sin `signature_image` se ignora y el
  commit contesta lo mismo que sin él.
- **Dos códigos 422 nuevos en el commit**, ambos sin coste (no se cobra intento de código, no se gasta nada):
  - **`SIGNATURE_IMAGE_INVALID`**: `signature_image` no es base64, pasa de 100 KB decodificada, no es un PNG,
    su cabecera dice más de **600 × 240 px**, no es un PNG de 8 bits RGB o RGBA sin entrelazar, o no decodifica
    entero (por ejemplo, cortado). Se comprueba **antes que nada**, también antes del código: con un código incorrecto y una imagen mala la respuesta es
    esta, y el intento no se cobra. Corregid la imagen y repetid con el mismo código.
  - **`SIGNATURE_IMAGE_NOT_ACCEPTED`**: se mandó `signature_image` donde no se dibujaría en ningún sitio — el
    sobre es `SINGLE_SEAL`, o este destinatario no tiene marca visible. No se firma nada; repetid el commit
    **sin** la imagen y firma.
- **Lo que queda de la imagen**: con el acto se registra solo su huella SHA-256; los bytes se guardan hasta que
  las marcas del destinatario están selladas y entonces se borran. La pista de auditoría dice que la marca se
  dibujó con una imagen y da esa huella.

Las formas exactas están en la especificación OpenAPI (`signature_image`, `biometric_data`,
`biometric_consent` en el cuerpo del commit; los dos miembros de `config`).

## Lo que el frontal tiene que hacer

1. **Leed `config.biometric_capture_enabled`** de `GET /api/v1/signing/session`. Con `true`, el paso de firma
   captura como hoy (DRAW o TYPE) y el commit lleva la imagen. Con `false` (`SINGLE_SEAL`, o un destinatario sin
   marca visible), **no mandéis `signature_image`**: el backend la rechaza con `SIGNATURE_IMAGE_NOT_ACCEPTED`.
2. **Rasterizad la firma a un PNG tal como la vio el destinatario**, en DRAW y en TYPE:
   - **Límites del backend, fijos: como mucho 600 × 240 px y 100 KB** decodificada.
   - **Formato, fijo: PNG de 8 bits por canal, RGB o RGBA, sin entrelazado** (tipo de color 2 o 6, sin Adam7).
     Es la forma que exporta el lienzo del signer (`toBlob`/`toDataURL` en `image/png`); no lo paséis por un
     optimizador que lo convierta a paleta o a escala de grises, porque el backend rechaza cualquier otra forma
     con `SIGNATURE_IMAGE_INVALID`.
   - **Tamaño recomendado: 540 × 210 px**, el triple de la caja de 180 × 70 pt con la que se midió en DSS (la
     proporción de la caja, para que no se deforme). En la marca, la imagen ocupa la caja salvo la línea del
     nombre, debajo.
   - **Fondo transparente** (RGBA) y trazo oscuro. Medido en DSS 6.4: el canal alfa se conserva exacto en el
     PDF.
   - La imagen se repite en cada marca, y cada marca es una firma incremental: cuanto más pequeña, menos pesa
     cada documento. Medid el tamaño de vuestras firmas reales contra los 100 KB; el backend no lo ha medido con
     firmas reales, solo con un PNG de prueba de 300 × 120 px y un trazo, que ocupa 441 bytes.
   - TYPE: rasterizad el texto con la fuente que vio el destinatario; el backend no dibuja nada.
   - ⚑ **Instrucción nueva, 2026-10-07 (rama `fix/mark-text-fits`): dejad un margen transparente de ~6 % en
     cada lado del PNG y no lo recortéis a la tinta.** Desde esa rama el backend pide a DSS que escale la
     imagen **conservando su proporción** y centrada (`ZOOM_AND_CENTER`; antes la estiraba a toda la caja). Así
     la imagen llega hasta el borde superior de la marca, y el aire que haya por encima del trazo es el que
     traiga el propio PNG: el backend no añade ni recorta márgenes. En un lienzo de 540 × 210 px son unos 32 px
     a izquierda y derecha y unos 13 px arriba y abajo. Un PNG recortado a la tinta deja la firma pegada al
     borde de la caja.
   - Con imagen, el nombre va debajo **en una sola línea**: si no cabe en el ancho de la caja, el backend lo
     corta con «…» (cada línea más le quitaría a la imagen unos 10 pt de alto).
3. **Mandad `signature_image` solo cuando `config.biometric_capture_enabled` es `true`, y decidid solo con ese
   flag.** No lo derivéis del rol ni del modo de firma: el flag ya es `false` para un rol que no firma, en
   `SINGLE_SEAL` y para un destinatario sin marca visible, que son justo los casos en que el backend rechazaría
   la imagen. Si aun así llega un `SIGNATURE_IMAGE_NOT_ACCEPTED`, el destinatario firma repitiendo sin la
   imagen.
4. **Mandad `biometric_data` solo para DRAW**, junto a `signature_image`, y con **`biometric_consent: true`**
   cuando el destinatario dio el consentimiento (la casilla opcional que el signer ofrece junto al dibujo
   cuando `config.consent_biometric_required` es `true`; sin ella firma igual y los trazos no se mandan). La forma es la que ya emite `useSignatureStore`:
   `{type: 'GRAPHOMETRIC', strokes: [[{x, y, t, p}, …], …], canvas_width, canvas_height, device_dpi}`.
   **Unidades (BL-187), sin cambiar nada**: `x`, `y`, `canvas_width` y `canvas_height` en px CSS lógicos; `t` en
   milisegundos epoch; `p` la presión de 0 a 1; `device_dpi` = `96 × devicePixelRatio`. Límites: hasta 500
   trazos y 50 000 puntos en total; lienzo hasta 10 000 px por lado; `device_dpi` hasta 2000. Fuera de ellos el
   bloque se descarta en silencio, sin error.
5. **Tratad los dos 422 nuevos** como arriba: `SIGNATURE_IMAGE_INVALID` es un defecto del cliente (imagen mal
   generada); `SIGNATURE_IMAGE_NOT_ACCEPTED` se resuelve repitiendo el commit sin la imagen. Ninguno cobra
   intento ni gasta el código.

## Lo que NO está listo todavía

- **Guardar los trazos.** Se reciben y se descartan. Guardarlos cifrados es la intención del mantenedor, sin
  fecha ni diseño decidido (TASK-053 §6). El contrato de `biometric_data` queda fijado ahora para que capturar y
  guardar se puedan activar por separado.
- **El texto del consentimiento biométrico** mientras los trazos se descartan es una pregunta de legal, abierta
  (TASK-053 §6). No cambiéis el texto por vuestra cuenta.

## Lo que NO existirá, y por qué

- **UPLOAD** (subir una imagen de firma) no se ofrece contra este backend (TASK-053 §4 D2): toda imagen que
  acepta la dibujó o escribió el destinatario en vuestro lienzo. No lo añadáis a `allowed_signature_modes`.
- **Imagen en `SINGLE_SEAL`**: nunca. Ese modo produce un único sello de la empresa y ninguna marca de
  destinatario (TASK-053 §4 D1).
- **La ruta delegada** (`/api/v1/signing/delegated/...`) no lleva imagen: su acto es de una máquina y su marca
  nombra la ruta con palabras.

## Cómo verificarlo desde el frontal

- Contra un sobre `SEQUENTIAL_PADES` con un destinatario que tiene una marca: `GET /api/v1/signing/session` trae
  `config.biometric_capture_enabled: true`. Un commit con `signature_image` y `biometric_data` contesta 200 como
  hoy; cuando se sella, la copia sellada enseña la firma encima del nombre en cada marca.
- Con un PNG cortado por la mitad: 422 `SIGNATURE_IMAGE_INVALID`, y el mismo commit con un PNG bueno firma.
- Contra un sobre `SINGLE_SEAL`: `config.biometric_capture_enabled: false`, y un commit con imagen da 422
  `SIGNATURE_IMAGE_NOT_ACCEPTED`.
- En el backend, `DrawnSignatureOnTheMarkHttpTest` recorre todo esto contra el DSS real.
