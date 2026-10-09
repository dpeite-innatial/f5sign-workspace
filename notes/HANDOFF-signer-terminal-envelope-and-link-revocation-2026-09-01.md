# Traspaso al frontal — un sobre terminal cierra la ceremonia, y una corrección de contacto mata el enlace viejo

| | |
|---|---|
| **Origen** | `feat/terminal-envelope-and-credential-retirement` (`bb6c43c` · `a7b350f` · `44b0551`, ya en `develop`) + `fix/signing-link-revocation-on-correction` (`2f8e97b` · `858d1a0`) + `fix/completed-envelope-keeps-recipient-reads` (`e41a489`) |
| **Fecha** | 2026-09-01 |
| **Repos afectados** | **signer** (todo lo de aquí) · dashboard (solo el punto 4) |
| **Naturaleza** | **rompe el contrato** en dos sitios (rechazos nuevos en rutas que antes servían) · **corrige la spec publicada** en tres |
| **Acción requerida** | **manejar dos estados nuevos** — un 409 y un 401 que antes no existían en estas rutas |
| **Desplegado** | ⚠ **`develop` solo.** TASK-038/039 están mergeados; los dos `fix/` no. Nada en producción a fecha de hoy. |
| **Status** | Pending |

⚠ **Este traspaso llega tarde y a destiempo, y conviene que lo sepáis al leerlo.** TASK-038/039 se
mergearon el 2026-08-28 sin traspaso, pese a que tocaban tres rutas de destinatario y añadían dos
`ProblemCode`. Una auditoría del 09-01 lo detectó junto con dos defectos en esas mismas ramas, y este
documento cubre las tres entregas a la vez porque separarlas os obligaría a aplicar un contrato que ya
sabemos que estaba mal.

## Lo que cambió en el contrato

**1. Un sobre cerrado por el emisor ya no sirve nada al destinatario.** Antes, un sobre anulado dejaba
funcionando el read-model, los bytes del documento y la apertura de sesión hasta que la credencial
caducaba. Ahora las cuatro travesías rechazan. La forma exacta está en el spec; lo que importa es que
`GET /api/v1/signing/session` responde **409** con `code: ENVELOPE_NO_LONGER_LIVE` y la ruta de bytes
responde **404**.

**2. Un sobre `COMPLETED` SIGUE sirviendo, y esto es una corrección de lo anterior.** El primer intento
usó un predicado que también cubría `COMPLETED`, así que el firmante perdía el acceso a su propia copia
**segundos después de firmar**, sin ninguna otra ruta para recuperarla. Corregido en `e41a489`. ⛔ Si ya
habíais empezado a tratar `409 ENVELOPE_NO_LONGER_LIVE` como *"la ceremonia acabó, incluida la vuestra"*,
**no lo hagáis**: un sobre completado responde 200 y el firmante debe poder volver a por su copia.

**3. Una corrección de contacto invalida el enlace anterior.** Cuando el emisor corrige la dirección de
un destinatario, **todos los enlaces emitidos antes de esa corrección dejan de abrir**. El rechazo es un
**401 indistinguible de un enlace desconocido o caducado** — mismo status, mismo `code: UNAUTHORIZED`,
mismo texto. ⚠ **Eso es deliberado y no vamos a cambiarlo**: quien sostiene el enlace superseded es, en
el caso para el que existe el mecanismo, el buzón equivocado, y un código distinguible le diría que la
dirección fue corregida.

**4. Un reset de código de acceso NO invalida el enlace** — el firmante legítimo vuelve por el mismo
enlace con el código nuevo. La asimetría con el punto 3 es intencionada. **Para el dashboard**: el texto
publicado del endpoint de reset decía que un reset es contención suficiente ante una filtración, y
**eso era falso en la configuración por defecto**; ahora enuncia la condición. Si mostráis copia basada
en ese texto, releedla.

## Lo que el frontal tiene que hacer

- **Distinguir tres rechazos que antes eran uno.** En las rutas de ceremonia: `409` +
  `ENVELOPE_NO_LONGER_LIVE` → *el documento se cerró*, pantalla terminal, **no reintentar**. `401` +
  `CREDENTIAL_RETIRED` → **recuperable**: mandad al firmante de vuelta por su enlace a pasar la puerta
  otra vez. `401` + `UNAUTHORIZED` → enlace inválido, caducado **o superseded**; pantalla de enlace roto,
  y el mensaje debería sugerir buscar un correo más reciente.
- **No enviar al firmante a la pantalla de auth ante un `COMPLETED`.** Sigue siendo lo que dice
  ADR-0056, y el punto 2 lo restaura.
- **Tratar `outcome: "REVOKED"`** en `GET /api/v1/signing/session/auth` (miembro nuevo del enum) como
  *el emisor canceló*. ⚠ Hoy solo lo produce una anulación, y llega por un reactor asíncrono, así que
  puede tardar: no lo useis como única señal de cancelación — el 409 del punto 1 es síncrono y llega
  antes.

## Lo que NO está listo todavía

- **La revocación del enlace no queda marcada en la fila del token.** Funciona, pero soporte no puede
  responder *"¿cuándo dejó de valer este enlace?"* leyendo la tabla de tokens. Se rastrea en `BL-229`.
  No os afecta salvo que estéis construyendo herramientas de soporte.
- **Un reset con puerta de acceso neutra no contiene del todo una filtración** (`BL-230`): retira las
  credenciales vivas, pero el intruso reabre el enlace y recupera lectura y bytes; solo la firma queda
  bloqueada. Si el dashboard ofrece *"resetear el código"* como respuesta a una sospecha de acceso
  indebido, **la respuesta completa hoy es anular el sobre**, no resetear.

## Lo que NO existirá, y por qué

- **No habrá descarga self-service de la copia sellada para el destinatario en esta entrega.**
  `DownloadSealedDocumentController` es ruta de **emisor** (`MACHINE_KEY`) y el correo de finalización no
  lleva enlace. Lo que el punto 2 restaura es que el firmante conserve acceso **por su enlace de firma
  mientras este siga vivo** — no una ruta nueva. ⚠ Decidlo así en la UI: *"descarga tu copia"* sobre un
  enlace con caducidad es una promesa que expira sin avisar.
- **El rechazo del enlace superseded no llevará nunca un `code` propio.** No es una omisión pendiente:
  darle uno le diría al buzón equivocado que la dirección fue corregida. No lo pidáis como mejora.

## Cómo verificarlo desde el frontal

⛔ **Antes de medir nada: el `doc.json` del stack local NO es `develop`, y esto invalidó la primera
versión de esta sección.** El compose de `f5sign-infra` bind-montea `../f5sign-backend` — el checkout
**principal** del backend — así que el spec que sirve es el de **la rama en la que ese checkout esté
sentado**, no el de `develop` ni el de ningún despliegue. Medido por la sesión del signer el
2026-09-01: el principal estaba en `feat/recipient-invitation-reminder` y `ProblemCode` daba **25**
miembros en vez de los 22 de `develop`. Un check contra el stack local puede pasar por código que no
existe en ninguna rama que os vayan a desplegar.

▶ **Medid por ref, no por stack**, o comprobad primero en qué rama está el principal:

```
git -C <backend> show origin/develop:config/packages/nelmio_api_doc.yaml   # la fuente
git -C <backend> rev-parse --abbrev-ref HEAD                              # en qué está el principal
```

1. `ProblemCode` contiene `ENVELOPE_NO_LONGER_LIVE` y `CREDENTIAL_RETIRED`. ⚑ Comprobad
   **pertenencia**, nunca el número de miembros: el catálogo del 2026-08-21 fijó una cifra y quedó
   mintiendo en cuatro días — y el stack local os dará una tercera cifra distinta por lo de arriba.
2. La descripción del `409` en `GET /api/v1/signing/session` **no** menciona `completed`. Si lo
   menciona, estáis contra un despliegue anterior a `e41a489` (que hoy, 2026-09-01, es todo lo
   desplegado).

   ⛔ **Y ese es el único estado que la descripción nombra ya.** La primera versión de este paso os
   mandaba comprobar la enumeración entera (*voided, declined or expired*), lo cual convertía en
   load-bearing exactamente la lista que os hizo daño: vuestro `990accf` la copió al mensaje de
   commit y de ahí bajó a tres comentarios y dos tests. Hemos quitado la enumeración de las tres
   cadenas publicadas — dicen la propiedad y mandan a ramificar por el `code`. ⚠ **No copiéis la
   lista de estados a vuestro lado en ningún sitio**: cuáles la producen es nuestro y va a cambiar,
   y `COMPLETED` **no** es uno, que es la única parte que sí es promesa.
3. El `enum` de `outcome` en `GET /api/v1/signing/session/auth` incluye `REVOKED`.
