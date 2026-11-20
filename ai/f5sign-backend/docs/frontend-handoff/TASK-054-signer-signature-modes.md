# Traspaso al frontal — el remitente elige cómo firma cada destinatario, y el commit declara cómo firmó

| | |
|---|---|
| **Origen** | rama `feat/signature-modes` (desde `develop` `ee2889a8`), **sin mergear, sin desplegar** · commit: ver `git log feat/signature-modes`, el último que toca `src/` es el que manda · [TASK-054](../tasks/TASK-054-the-sender-chooses-how-each-recipient-signs.md) |
| **Fecha** | 2026-10-08 |
| **Repos afectados** | **signer** |
| **Naturaleza** | ⛔ **rompedor**: `signature_mode` pasa a ser **obligatorio** en `POST /api/v1/signing/commit`. Un signer que no lo manda recibe 422 `VALIDATION_ERROR` en cada commit. Nada está en producción |
| **Acción requerida** | ofrecer exactamente `config.allowed_signature_modes` · mandar `signature_mode` en cada commit · la casilla biométrica solo con `config.consent_biometric_required` · tratar tres 422 nuevos |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

- **`GET /api/v1/signing/session`: `config.allowed_signature_modes` son ahora los modos que este destinatario
  puede usar**, no la constante `['DRAW', 'TYPE']`: los que le ofreció el remitente, menos `DRAW` y `TYPE`
  cuando ninguna marca suya admite imagen (sobre `SINGLE_SEAL`, o sin colocación visible); entonces siempre
  queda `SIMPLE`. Valores posibles: `SIMPLE`, `DRAW`, `TYPE`, en ese orden. Vacío solo para un rol de solo
  lectura, cuyo commit se rechaza con `COMMIT_NOT_OFFERED_TO_ROLE`.
  - `SIMPLE` es la firma de solo marcar: consentimiento (y el código de firma si hay puerta de firma). **Sin
    imagen.**
  - `DRAW` es la firma dibujada; `TYPE`, el nombre escrito con tipografía manuscrita. Ambas se mandan como
    `signature_image`, como hasta ahora.
  - Combinaciones: `[SIMPLE]` = solo marcar · `[DRAW]` = dibujo obligatorio · `[SIMPLE, DRAW]` = dibujo
    opcional. Un destinatario dado de alta antes de este cambio lee `[SIMPLE, DRAW, TYPE]` (lo que ya tenía:
    el dibujo era opcional); uno nuevo sin nada declarado lee `[SIMPLE]`.
- **`config.biometric_capture_enabled`** = el commit acepta imagen: hay `DRAW` o `TYPE` entre los modos
  publicados, que ya solo los incluyen si el sobre es `SEQUENTIAL_PADES` **y** el destinatario tiene marca
  visible. Un `[SIMPLE, DRAW]` en un sobre `SINGLE_SEAL` se publica como `[SIMPLE]`.
- **`config.consent_biometric_required`** = ofrecer la casilla biométrica **opcional**: `DRAW` está en los modos,
  el remitente ofreció biometría y `biometric_capture_enabled` es `true`. Es una casilla, no una puerta: el
  destinatario puede dibujar sin marcarla. Sin marcar, no mandéis los trazos.
- **`POST /api/v1/signing/commit` exige `signature_mode`** (`SIMPLE` | `DRAW` | `TYPE`): el modo con el que el
  destinatario firmó. Mandad uno de `allowed_signature_modes`.
- **Tres 422 nuevos en el commit**, ninguno cobra intento ni gasta el código (se repite con el **mismo** código):
  - `SIGNATURE_MODE_NOT_OFFERED`: el `signature_mode` no es uno que el remitente ofreciera a este destinatario.
  - `SIGNATURE_IMAGE_REQUIRED`: `DRAW` o `TYPE` sin `signature_image`.
  - `SIGNATURE_IMAGE_NOT_ACCEPTED` (el código de TASK-053, con dos causas más): `SIMPLE` con `signature_image`,
    o `DRAW`/`TYPE` ofrecidos pero fuera de `allowed_signature_modes` porque ninguna marca admite imagen (con
    imagen o sin ella). Firmad `SIMPLE`, sin imagen.
  - Sin `signature_mode`, o con un valor desconocido: 422 `VALIDATION_ERROR` (`errors[]` nombra el miembro).
- **`biometric_data`** solo se lee con `signature_mode: DRAW` y `biometric_consent: true`. Con otro modo se
  descarta, nunca se rechaza. Sigue sin guardarse (TASK-053 §4 D7).
- **La marca**: si el remitente ocultó el nombre (`show_name: false`, solo posible sin `SIMPLE`), la marca lleva
  **solo la imagen, centrada y sin deformar** (medido en DSS 6.4 el 2026-10-08). Con el nombre visible, como en
  TASK-053: imagen arriba, nombre debajo; con `SIMPLE`, el nombre solo.

## Lo que el frontal tiene que hacer

⚠ **Despliegue**: como `signature_mode` es obligatorio, un signer sin este cambio no puede firmar contra un
backend con él. Desplegad los dos en la misma ventana.


1. **Ofreced exactamente los modos de `allowed_signature_modes`**: el backend ya ha quitado los que no se
   pueden usar. `SIMPLE` es un botón de firmar sin lienzo.
2. **Mandad `signature_mode` en cada commit**, con el modo usado. Con `DRAW`/`TYPE`, la imagen como en
   TASK-053; con `SIMPLE`, sin imagen.
3. **La casilla biométrica, solo con `consent_biometric_required: true`** y solo junto a `DRAW`. Desmarcada por
   defecto. Marcada → `biometric_consent: true` y `biometric_data`.
4. **Tratad los tres 422 nuevos** como errores del cliente: no deberían darse si se sigue `config`.

## Lo que el backend no puede comprobar

El backend comprueba el modo **declarado**, no cómo se hizo la imagen: un PNG dibujado y uno escrito son los
mismos bytes para él (TASK-054 §4 D5). Un cliente manipulado podría declarar `DRAW` y mandar un nombre
escrito, y nada aquí lo detecta. La pista de auditoría dice el modo **declarado** y nada más.

## Cómo probarlo

- Un sobre `SEQUENTIAL_PADES` con marcas y tres destinatarios: `[SIMPLE]`, `[DRAW]` sin nombre y
  `[SIMPLE, DRAW]`. El primero firma sin lienzo; el segundo no puede firmar sin dibujar y su marca es solo la
  imagen; el tercero puede hacer cualquiera de las dos cosas.
- Un commit sin `signature_mode` → 422 `VALIDATION_ERROR`.
