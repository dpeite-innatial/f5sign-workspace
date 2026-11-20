# Traspaso al dashboard y al integrador — cómo firma cada destinatario, y si su nombre va en la marca

| | |
|---|---|
| **Origen** | rama `feat/signature-modes` (desde `develop` `ee2889a8`), **sin mergear, sin desplegar** · commit: ver `git log feat/signature-modes`, el último que toca `src/` es el que manda · [TASK-054](../tasks/TASK-054-the-sender-chooses-how-each-recipient-signs.md) |
| **Fecha** | 2026-10-08 |
| **Repos afectados** | **dashboard** (formulario del destinatario) e **integradores** que crean sobres por la API (`factor5-dashboard`) |
| **Naturaleza** | aditivo en el alta (tres miembros opcionales), con **un cambio de comportamiento por defecto**: un destinatario nuevo sin nada declarado firma `[SIMPLE]` (solo marcar), donde antes se le ofrecía un dibujo opcional. Un envío que antes salía puede rechazarse ahora (nuevo 422 al enviar) solo si se declaró un destinatario sin `SIMPLE`. Un 409 nuevo en la ruta de máquina |
| **Acción requerida** | exponer los tres miembros en el alta · tratar cuatro 422 nuevos en el alta, uno al enviar y un 409 en el commit por máquina |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

### Alta: `POST /api/v1/envelopes/{id}/recipients`

Tres miembros nuevos, todos opcionales. Se fijan aquí y **no cambian después**: la corrección
(`POST .../recipients/{recipientId}/corrections`) sigue cambiando solo email y teléfono.

- **`signature_modes`**: lista no vacía de `SIMPLE`, `DRAW`, `TYPE`. Por defecto `[SIMPLE]`.
  - `SIMPLE`: firmar marcando (consentimiento, más el código si hay puerta de firma). Sin imagen.
  - `DRAW`: firma dibujada. `TYPE`: nombre con tipografía manuscrita. Ambas dejan una imagen en la marca.
  - `[SIMPLE]` solo marcar · `[DRAW]` dibujo obligatorio · `[SIMPLE, DRAW]` dibujo opcional. El orden y las
    repeticiones no importan; se devuelve en el orden SIMPLE, DRAW, TYPE.
- **`biometrics_offered`**: booleano, por defecto `true`. Si el signer ofrece la casilla biométrica opcional junto
  al dibujo. Solo tiene sentido con `DRAW`.
- **`show_name`**: booleano, por defecto `true`. Si el nombre del destinatario se dibuja en su marca. Con `false`
  la marca lleva solo la imagen de firma, centrada (útil donde la casilla del documento ya imprime el nombre).

Rechazos, todos 422 con su `code`:

| `code` | Cuándo |
|---|---|
| `SIGNATURE_MODES_EMPTY` | `signature_modes: []`. Omitidlo para `[SIMPLE]` |
| `VALIDATION_ERROR` | un modo desconocido (`errors[]` nombra `signature_modes[i]`) |
| `BIOMETRICS_OFFERED_WITHOUT_DRAW` | `biometrics_offered: true` sin `DRAW` en los modos |
| `SIGNATURE_NAME_REQUIRED` | `show_name: false` con `SIMPLE` en los modos: una firma de solo marcar no tiene imagen y la marca quedaría vacía. Quien no deba dejar marca, sin colocación |
| `DELEGATED_RECIPIENT_SIGNS_SIMPLE` | `signs_via: MACHINE_KEY` con algo distinto de `[SIMPLE]` y `show_name: true` |

### Lectura: `GET /api/v1/envelopes/{id}`

Cada destinatario lleva `signature_modes`, `biometrics_offered` y `show_name` tal como se guardaron. Los
destinatarios creados antes de este cambio leen `[SIMPLE, DRAW, TYPE]` (o `[SIMPLE]` si firman por
`MACHINE_KEY`), `true`, `true`: lo que tenían.

### Envío: `POST /api/v1/envelopes/{id}/send`

Nuevo 422 **`SIGNATURE_MODES_NEED_A_MARK`**: un destinatario que puede comprometerse (no `VIEWER`, `REVIEWER`
ni `EDITOR`) y no tiene `SIMPLE` debe dejar una imagen, y no tiene dónde: el sobre es `SINGLE_SEAL`, o ninguna
de sus filas de firma tiene colocación visible (un `APPROVER` no tiene filas de firma, así que nunca). Remedio:
ofrecerle `SIMPLE`, o darle una colocación en un sobre `SEQUENTIAL_PADES`.

### Commit por máquina: `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature`

Esta ruta no lleva imagen, así que el acto que registra es un `SIMPLE`. Nuevo **409
`SIGNATURE_MODE_NOT_OFFERED`** para un destinatario retransmitido cuyo ajuste no incluye `SIMPLE`: tiene que
firmar en el signer. Se contesta después de `STEP_NOT_ACTIVE` y antes de leer el código, así que no cobra
intento. ⚑ El mismo `code` es un 422 en el commit del navegador: allí el cuerpo es incorrecto, aquí el estado del
destinatario es uno que esta ruta no puede satisfacer. Ramificad por `code`. Un destinatario `MACHINE_KEY` siempre
tiene `[SIMPLE]`, así que nunca recibe este 409.

## Lo que el dashboard y el integrador tienen que hacer

1. **Formulario / cuerpo del alta**: los tres miembros, con sus valores por defecto. Avisad de que el valor por
   defecto es ahora solo marcar.
2. **Validad antes de mandar** las combinaciones de la tabla (o mostrad el `code`).
3. **Un destinatario sin `SIMPLE` necesita una marca visible en un sobre `SEQUENTIAL_PADES`**; si no, el envío
   se rechaza con `SIGNATURE_MODES_NEED_A_MARK`.
4. **Integrador que retransmite por máquina**: ofreced `SIMPLE` a esos destinatarios, o tratad el 409.

## Lo que el backend no puede comprobar

Entre `DRAW` y `TYPE` el backend solo ve lo que el cliente declara: no distingue una imagen dibujada de una
escrita. La pista de auditoría dice el modo declarado.
