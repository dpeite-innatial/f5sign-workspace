# Traspaso al frontal — `status` en la apertura pasa a decir la verdad, y llega `access_grant_expires_at`

<!-- OFFREPO: los hechos del lado cliente (el bucle `/auth` ↔ índice, el `useCountdown`, la fila medida
del destinatario afectado) los midió la sesión que trabajaba en `f5sign-signer` el 2026-08-19 contra este
backend. Están reescritos en línea donde se usan, así que nada de este documento exige tener ese repo
delante. -->

| | |
|---|---|
| **Origen** | rama `fix/session-status-and-grant-expiry` · commit `be298d4` · sin PR |
| **Fecha** | 2026-08-19 |
| **Repos afectados** | **signer** únicamente. El dashboard no toca esta ruta |
| **Naturaleza** | **corrige la especificación publicada** (el valor de `status` era erróneo) · **aditivo** (`access_grant_expires_at`) |
| **Acción requerida** | **dejar de ramificar por `status`** en la respuesta de apertura y ramificar por la **presencia de `access_credential`** · pintar la cuenta atrás desde `access_grant_expires_at` en vez de desde una constante |
| **Status** | Pending |

> ⚠ **DESMENTIDO EN PARTE el 2026-08-24 por [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md).
> Lo de abajo se conserva entero: era cierto cuando se escribió y sigue describiendo bien al firmante varado.
> Lo que este documento no sabía es que `AUTH_PASSED` sin credencial son DOS poblaciones, no una.**
>
> La otra es el firmante que **ya firmó**. Su sesión es `COMPLETED`, que `isAuthenticated()` clasifica como
> autenticada —correctamente: la puerta sí se pasó—, así que producía exactamente el mismo cuerpo que el
> varado. Un cliente que siguiera al pie de la letra la tabla del punto 2 le ofrecía recuperación, y todo
> envío moría en `AUTH_NO_OPEN_CHALLENGE` sin tocar ningún canal.
>
> ⛔ **Y el punto 3 de abajo es falso para esa población, de forma permanente**: una sesión terminal nunca
> se retira por inactividad, así que su `access_grant_expires_at` viene **en el pasado** y la siguiente
> apertura no los devuelve a ninguna puerta, ni al pasar ese instante ni nunca.
>
> **Qué hacer ahora**: `status` tiene un tercer miembro, `COMPLETED`, que tiene precedencia. Leedlo
> **antes** que nada — antes de la tabla del punto 2 y antes de dibujar cualquier reloj.

> ⛔ **Lo que arregla esto es la pantalla en blanco.** `POST /api/v1/signing/session` calculaba `status`
> desde la **declaración del remitente** —si el destinatario tiene puerta declarada o no—, que es un hecho
> que no cambia nunca. Un destinatario que ya había pasado la puerta recibía `AUTH_PENDING` en **cada**
> apertura posterior, para siempre. Ramificando por ese campo, el signer iba a la pantalla de
> autenticación, `GET …/session/auth` respondía `gate: null` porque la puerta sí estaba pasada, y el
> cliente volvía al índice: **un bucle cerrado**.

## Lo que cambió en el contrato

Sólo `POST /api/v1/signing/session`. Los shapes están en el OpenAPI que genera Nelmio; aquí va **qué
cambió y qué hacer**.

1. **`status` pasa a ser un hecho sobre la SESIÓN, no sobre la declaración.**
   - `AUTH_PASSED` — la puerta de acceso está detrás de este destinatario. Puede ser porque era neutra (y
     llegar con el enlace *es* pasarla) **o porque la pasó en una petición anterior**.
   - `AUTH_PENDING` — hay una puerta declarada sin pasar. Aquí colapsa también `AWAITING_REAUTH`: una
     concesión retirada por inactividad hay que volver a ganarla por la misma puerta, así que para vosotros
     es el mismo camino y no hay un tercer valor que manejar.

2. **⛔ `AUTH_PASSED` deja de implicar que haya credencial en el cuerpo.** Es el punto que decide vuestro
   código. Reabrir el enlace **nunca** acuña detrás de una puerta declarada —pasarla es lo único que
   acuña—, así que un destinatario que pasó la puerta y **perdió el par** recibe `AUTH_PASSED` con los tres
   miembros de credencial **ausentes**. Es un estado real y frecuente: iOS descarta la pestaña en segundo
   plano mientras el firmante va a su correo a leer el código, y con ella se va el `sessionStorage`.

3. **Llega `access_grant_expires_at`**, siempre presente, `null` cuando no hay concesión viva. Es el
   instante en que la concesión **actual** deja de renovarse: la caducidad de la credencial de refresco,
   que es el reloj de inactividad real ([ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md)
   §2.5). Nombrado así, y no `retry_at`, porque es *cuándo caduca lo que hay*, no *cuándo podrá entrar el
   firmante*: si otra pestaña sigue viva y renovando, el instante **se empuja hacia adelante**.
   - ⚠ **No lo confundáis con `expires_at`**, que ya estaba y es la vida de quince minutos de la credencial
     de acceso que va en ese mismo cuerpo. Uno es la puerta, el otro es el pase.

## Lo que el frontal tiene que hacer

1. **Ramificar por la presencia de `access_credential`, nunca por `status`.** Es un cambio de una línea en
   el punto donde hoy leéis la credencial de la respuesta de apertura, y deroga el discriminante que os
   dimos en [`TASK-021-two-gate-signer-auth.md`](TASK-021-two-gate-signer-auth.md) §«La rotura» —ese
   documento lleva ya la corrección marcada en su sitio.

2. **Enrutad los tres casos, que ahora son distinguibles:**

   | `status` | `access_credential` | qué es | a dónde va |
   |---|---|---|---|
   | `AUTH_PENDING` | ausente | puerta declarada sin pasar (o concesión retirada por inactividad) | pantalla de autenticación |
   | `AUTH_PASSED` | **presente** | puerta neutra, o recién pasada | ceremonia, como hasta ahora |
   | `AUTH_PASSED` | **ausente** | ⛔ **el firmante varado**: pasó la puerta, perdió el par | ver punto 3 |
   | `COMPLETED` | presente **o** ausente | ⚑ **añadido 2026-08-24** (ADR-0056): ya firmó. Presente si su puerta era neutra —sigue teniendo su copia sellada—, ausente si estaba declarada | pantalla de finalizado; **nunca** la de autenticación |

3. **Para el varado, pintad la espera real.** ⚠ *Comprobad primero que `status` no es `COMPLETED`: para esa población este punto entero es falso y el instante viene en el pasado — ver el desmentido de arriba.* `access_grant_expires_at` viene no-nulo y en el futuro:
   es cuándo caduca la concesión que ya no pueden usar, y **al pasar ese instante la siguiente apertura los
   devuelve a `AUTH_PENDING`**, o sea, a la puerta, que es por donde vuelven a entrar. Vuestro `useCountdown`
   ya dibuja desde un ISO-8601 y ya cae a un techo si el instante no viene o no parsea, así que esto es
   cambiar la fuente del valor, no la pantalla.
   - ⚠ **Releedlo en cada apertura en vez de contar desde el primer valor cacheado.** Otra pestaña viva que
     renueve lo empuja hacia adelante.

## Lo que NO está listo todavía

- ⛔ **La recuperación explícita no está en este cambio.** Hoy el varado **espera**: hasta una hora, y el
  gesto que lo provoca no tiene nada de raro. Está decidido cómo se arregla —un reto de recuperación que
  deja volver a pasar la puerta de acceso sin echar a nadie de ninguna pestaña— y va en un cambio aparte,
  con su propio traspaso. **No cableéis nada contra él hasta que exista**: la forma de la ruta todavía
  puede moverse.
- **No se toca ninguna otra ruta.** `GET …/session/auth`, `POST …/session/auth`,
  `POST …/session/auth/otp/send`, el read-model y el commit responden exactamente igual que ayer.
- **`access_grant_expires_at` no aparece en ninguna otra respuesta.** Sólo en la apertura.

## Cómo verificarlo desde el frontal

Hace falta un sobre con **puerta de acceso declarada** (`ACCESS_CODE`); con uno neutro no se distingue
nada de esto y las pruebas manuales pasan igual con el código roto.

1. Abrid con el enlace → `200`, `AUTH_PENDING`, sin credenciales, `access_grant_expires_at: null`.
2. Pasad la puerta con el código → `200`, llega el par.
3. **Vaciad el `sessionStorage`** (es lo que hace iOS por vosotros) y volved a abrir con el mismo enlace →
   `200`, **`AUTH_PASSED`**, sin credenciales, y `access_grant_expires_at` con un instante en el futuro.
   Antes de este cambio el paso 3 devolvía `AUTH_PENDING`, que es lo que abría el bucle.
