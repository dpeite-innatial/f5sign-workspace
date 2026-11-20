# Traspaso al dashboard y al integrador — un hueco reclamable se distingue de quien no ha actuado, y quien se nombra en él recibe su invitación

| | |
|---|---|
| **Origen** | rama `feat/claimed-recipient-invitation` (desde `develop` `7e87ce31`), **sin mergear, sin desplegar** · último commit que toca `src/` al escribir esto: `7b934db9`; el que manda es el último de `git log feat/claimed-recipient-invitation -- src/` · [TASK-037](../tasks/TASK-037-claimable-invitation-and-visibility.md) |
| **Fecha** | 2026-10-14 |
| **Repos afectados** | **dashboard** del remitente (estado de cada destinatario) e **integradores** que leen el sobre por la API (`factor5-dashboard`) |
| **Naturaleza** | aditivo: dos claves nuevas por destinatario en la lectura del sobre. Ninguna ruta nueva, ningún código de error nuevo, ningún enum nuevo. Cambia un comportamiento: quien se nombra en un hueco cuyo paso ya está activo recibe ahora su invitación |
| **Acción requerida** | distinguir el hueco que espera a que alguien lo nombre · retirar cualquier rodeo para invitar a quien se nombra (reclamar y luego corregir) |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

### Lectura: `GET /api/v1/envelopes/{id}`

Cada destinatario lleva dos claves nuevas, planas:

| Clave | Qué es |
|---|---|
| `declared_claimable` | `true` si el remitente lo creó como hueco reclamable (una posición sin persona, que se nombra con `POST /api/v1/envelopes/{id}/recipients/{recipientId}/claim`, antes o después de enviar el sobre). Se fija al crearlo y no cambia nunca, tampoco al reclamarlo. `false` en todo destinatario normal |
| `claimed_at` | Cuándo se nombró a la persona del hueco, o `null` si todavía no. Siempre `null` en un destinatario normal |

La forma exacta está en la especificación OpenAPI (`/api/doc.json`, esquema `Recipient`).

### Comportamiento: la invitación de quien se nombra

Hasta ahora, un hueco reclamado **cuando su paso ya estaba activo** no recibía invitación: la de la activación ya había
pasado y había saltado el hueco vacío. Ahora se invita a la persona nombrada **una sola vez**, sea cual sea el orden en
que la plataforma procese la activación del paso y la reclamación. Si se reclama en un paso que todavía no está activo,
o antes de enviar el sobre, la invitación sale cuando el paso se active, como la de cualquier otro destinatario. Sale
por los canales que se declararon para el hueco; si ninguno puede alcanzarla, `invitation_state` lo dice
(`NOT_SENT_NO_REACHABLE_CHANNEL`), igual que para cualquier destinatario.

## Lo que el dashboard y el integrador tienen que hacer

1. **La espera de un hueco es `declared_claimable === true && claimed_at === null`.** Mostradla como «pendiente de
   nombrar a alguien»: el remedio es reclamar el hueco, no recordarle nada a nadie.
2. **No uséis `declared_claimable` solo**: un hueco ya reclamado sigue en `true` y es un destinatario como otro
   cualquiera.
3. **No deduzcáis el hueco** de que falten `email`/`phone` ni de `invitation_state: null`: `null` también significa
   «su paso aún no se activó» o «firma por `MACHINE_KEY`».
4. **`outcome` sigue en `PENDING`** mientras el hueco espera, como el de quien está invitado y no ha actuado; es
   correcto, y no hay ni habrá un `outcome` propio para esto. El par de claves es lo que separa los dos casos.
5. **Quitad el rodeo** de reclamar y luego corregir para forzar una invitación: ya no hace falta, y cada corrección
   gasta una de las tres que tiene el destinatario.

## Lo que NO está listo todavía

- **Ningún recordatorio** para un hueco sin reclamar. La espera ya está acotada: cuando el sobre caduca o vence el
  plazo del paso, el hueco se libera como `RELEASED`: con `release_reason: UNCLAIMED` si su paso ya se había
  activado, y con `NOT_REACHED` si el sobre terminó antes de llegar a su paso.

## Lo que NO existirá, y por qué

- **Reasignar un hueco ya reclamado.** Un hueco se reclama una vez; nombrar a otra persona después se rechaza
  (`RECIPIENT_ALREADY_CLAIMED`). Cambiarlo exigiría otra decisión de arquitectura (ADR-0057 §2.4), y no está prevista.

## Cómo verificarlo desde el frontal

1. Cread un sobre con un destinatario `claimable: true` sin contacto y otro normal, y enviadlo. La lectura devuelve
   `declared_claimable: true, claimed_at: null` para el hueco y `false, null` para el normal; los dos en
   `outcome: PENDING`.
2. Reclamad el hueco con su paso activo. La lectura devuelve `declared_claimable: true` y un `claimed_at` con fecha, y
   la persona nombrada recibe una sola invitación por los canales declarados.
