# Traspaso al frontal — tras el commit, la lectura dice que firmaste y `signed_copy` dice dónde está tu copia

| | |
|---|---|
| **Origen** | rama `fix/signed-copy-after-commit`, **sin mergear, sin desplegar** · commit `6bca4d06`, la punta de la rama al escribir esto y el último commit que cambia código o texto publicado · TASK-068 · [ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md) (`Accepted`, 2026-10-23) |
| **Fecha** | 2026-10-23 |
| **Repos afectados** | **signer** |
| **Naturaleza** | aditivo: un miembro nuevo (`signed_copy`) en la lectura de sesión y en la respuesta del commit; una garantía publicada se estrecha (el 404 de la descarga) y `status` pasa a `COMPLETED` antes |
| **Acción requerida** | leer `signed_copy` y no ofrecer reintento de descarga mientras valga `APPLYING` o `AWAITING_ENVELOPE` · hacer polling de la lectura de sesión con la cadencia recomendada · tratar el 409 `SEAL_PENDING` como espera en la misma pantalla |
| **Desplegado** | not yet |
| **Status** | Pending |

> 2026-10-26, TASK-071: `FINAL` ya no espera a la compleción del sobre; ver [TASK-071](TASK-071-signer-integrator-signed-copy-final.md).

## Lo que cambió en el contrato

- **`GET /api/v1/signing/session`: `status` vale `COMPLETED` desde el momento en que se admite el commit**, en los
  dos modos de firma (`SEQUENTIAL_PADES` y `SINGLE_SEAL`). Hasta ahora seguía en `AUTH_PASSED` hasta que la firma
  llegaba al PDF. `COMPLETED` ya no significa «tu firma está en el documento»: eso lo dice `signed_copy`.
- **`GET /api/v1/signing/session`: miembro nuevo `signed_copy`**, siempre presente, `null` o uno de cinco valores:
  - `null`: no hay commit admitido de este destinatario y el sobre no ha completado; la descarga sirve como siempre.
  - `APPLYING`: firmó y su firma se está aplicando al PDF.
  - `AWAITING_ENVELOPE`: firmó, y nada suyo irá en un PDF antes de que acabe el sobre (`SINGLE_SEAL`, un rol que
    aprueba en vez de firmar, o un sobre que ya cerró).
  - `CONTAINS_YOUR_SIGNATURE`: su firma está en el documento, que los demás destinatarios aún no han terminado.
  - `FINAL`: el sobre completó y está sellado.
- **`POST /api/v1/signing/commit`: el 200 gana `signed_copy`**, siempre presente, y solo puede ser `APPLYING` o
  `AWAITING_ENVELOPE`, nunca una copia lista. Guardadlo como el de la lectura, igual que ya hacéis con `status`.
- **La descarga tras el commit es todo o nada** (`GET` de un documento de la sesión). Mientras `signed_copy` es
  `APPLYING` o `AWAITING_ENVELOPE`, **404 para todos los documentos**. En `CONTAINS_YOUR_SIGNATURE` y `FINAL`,
  **200 para cada documento que el destinatario puede leer**. Antes del commit, sin cambios.
- ⚠ **La garantía que cambió.** Antes: si la lectura de sesión contestaba 200, lo único que quedaba tras un 404 de
  la descarga era un motivo del documento, y solo «aún no hay nada subido» merecía reintento. Ahora: **un 200 de la
  lectura con `signed_copy` distinto de `null` y distinto de `CONTAINS_YOUR_SIGNATURE` y `FINAL` NO es un caso de
  reintento de la descarga**. El 404 de ese momento es la espera, no un documento que falte. Hacedle polling a la
  lectura de sesión hasta que se levante y no mostréis control de reintento sobre la descarga.
- **Entre el cierre del sobre y el sellado**, mientras haya un documento que el destinatario puede ver sin sellar,
  la lectura contesta **409 `SEAL_PENDING`**, sin `signed_copy`. Es el único 409 que puede recibir quien ya
  firmó: seguid esperando en la misma pantalla. Si en cambio no queda ningún documento visible sin sellar, la
  lectura contesta 200 con `AWAITING_ENVELOPE`. Sigue siendo posible un 401 `CREDENTIAL_RETIRED`.

Las formas exactas están en la especificación OpenAPI (`signed_copy` en `SigningSession` y en el 200 del commit; el
404 de la descarga).

## Lo que el frontal tiene que hacer

1. **Tras el commit, leed `signed_copy` de la respuesta** y pintad la pantalla de espera con él. No presentéis el
   documento como firmado por el mero hecho de que `status` sea `COMPLETED`.
2. **Haced polling de `GET /api/v1/signing/session` mientras `signed_copy` sea `APPLYING` o `AWAITING_ENVELOPE`**, o
   la lectura conteste 409 `SEAL_PENDING`. Cadencia recomendada (propietario, 2026-10-22): 2 s, 3 s, 5 s, 10 s, y
   después cada 30 s como mucho.
3. **Ofreced la descarga solo con `CONTAINS_YOUR_SIGNATURE` o `FINAL`.** Un 404 de la descarga junto a `APPLYING` o
   `AWAITING_ENVELOPE` no lleva control de reintento.
4. **La credencial dura 15 minutos y sigue renovándose con la sesión `COMPLETED`**
   (`POST /api/v1/signing/session/renew`), dentro del tope absoluto de 12 horas y de la ventana de refresco de una
   hora. Renovadla durante la espera.
5. **Pasados unos 5 minutos de espera**, la pantalla dice, en palabras neutras, que el firmante puede cerrar la
   ventana. **No prometáis un correo ni ningún otro medio de recibir la copia**: hoy no existe ninguno (ver abajo).
6. **Orden de despliegue: primero el signer, después el backend.** El signer debe tratar un `signed_copy` ausente
   como hoy (el backend actual no lo emite), de modo que desplegarlo antes no rompe nada.

## Lo que NO está listo todavía

- **La copia del firmante una vez que sale de la ceremonia** (BL-188, otra tarea): no hay enlace ni descarga fuera
  de la sesión.
- **El correo `envelope.completed` a un firmante no lleva ningún enlace hoy.** Por eso la pantalla de espera no puede
  prometer que la copia llegará por correo.

## Cómo verificarlo desde el frontal

Contra un sobre `SEQUENTIAL_PADES` con dos firmantes:

1. El primero hace el commit: el 200 trae `signed_copy: APPLYING`.
2. `GET /api/v1/signing/session` como ese firmante: `status: COMPLETED`, `signed_copy: APPLYING`.
3. Descargar un documento: 404.
4. Esperar al worker y volver a leer: `signed_copy: CONTAINS_YOUR_SIGNATURE`.
5. Descargar el documento: 200, con la firma del primer firmante dentro.

En el backend, `SignedCopyAfterTheCommitHttpTest` recorre los primeros pasos y `SigningReadersCannotDisagreeTest`
fija que las dos rutas no se contradicen.
