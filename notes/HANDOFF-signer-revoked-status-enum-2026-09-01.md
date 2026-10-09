# Traspaso al frontal — `REVOKED` en el enum de `status` de `POST /api/v1/signing/session`

| | |
|---|---|
| **Origen** | `f5sign-backend` · commit `852b054`, en `origin/develop` desde `f0767d4` |
| **Fecha** | 2026-09-01 |
| **Repos afectados** | **signer** |
| **Naturaleza** | **aditivo al enum publicado** — un valor nuevo en un campo que ya consumíais |
| **Acción requerida** | **manejar un valor nuevo de `status`** |
| **Desplegado** | no |
| **Status** | Aplicado por el signer en `c15c6dd` (su develop local, sin pushear) antes de existir esta nota |

⚠ **Esta nota llega tarde y por eso existe.** El cambio entró el 2026-09-01 sin traspaso, pese a que
el `README.md` de `f5sign-backend/docs/frontend-handoff/` lo exige *"whenever a change touches … an
enum whose values cross the wire"*. Lo encontró la sesión del signer **midiendo**, no leyendo. Queda
aquí, en `notes/` de la raíz, porque los traspasos de esta sesión no se commitean al repo de backend.

## Lo que cambió en el contrato

`status` en `POST /api/v1/signing/session` pasó de `['AUTH_PASSED','AUTH_PENDING','COMPLETED']` a
incluir **`REVOKED`**: el emisor cerró el sobre por debajo de una sesión viva. Es **terminal**, como
`COMPLETED`, y ahí acaba el parecido.

## Lo que el frontal tiene que hacer

- **`REVOKED` va a la pantalla de cancelado.** Nunca a `/done`, nunca a la puerta de auth.
- ⛔ **No lo aniden bajo el test de credencial como `COMPLETED`.** El signer llegó a esta distinción
  por su cuenta y es la correcta: con par de credenciales, un `COMPLETED` tiene un `/done` mejor al
  final del camino; **un sobre anulado no tiene nada mejor en ninguna parte**, así que merece rama
  propia antes. El enum dice *"terminal"* y no expresa cuál de los dos terminales merece qué pantalla
  — eso es del cliente.
- **Un valor no declarado no debe caer en la rama de auth.** Es lo que pasó aquí: `REVOKED` sin
  declarar caía al `return` de abajo y pintaba campo de código a alguien cuyo sobre acababan de
  anular — y sobre sesión terminal no llega ningún código nunca.

## Lo que NO está listo todavía

- **Hoy `REVOKED` no es alcanzable en esa respuesta.** Lo único que lo produce es una anulación, y un
  sobre anulado se rechaza con **409 `ENVELOPE_NO_LONGER_LIVE`** antes de construir ese cuerpo. Se
  publicó igual: ese acoplamiento vive en otra decisión y no es de esa ruta prometerlo, y un enum al
  que le falta un valor que su propia fuente puede devolver es como un cliente acaba en su rama de
  *estado desconocido* el día que el acoplamiento se mueva. ⚑ Que se encontrara midiendo y no en
  producción es consecuencia de haberlo publicado antes de que pudiera dispararse.

## Cómo verificarlo desde el frontal

⛔ **Medid por ref, no contra el stack local**: el compose de `f5sign-infra` bind-montea el checkout
**principal** del backend, así que su `doc.json` es el de la rama en la que ese checkout esté sentado.

```
git -C <backend> show origin/develop:src/F5Sign/Session/UI/Http/StartSessionController.php | grep "enum: \['AUTH"
```

Debe listar `REVOKED`. ⚠ Comprobad **pertenencia, nunca cuántos miembros**: `ProblemCode` da cifras
distintas en cada árbol y rama, que es exactamente por lo que el traspaso de códigos ya no lleva
número.
