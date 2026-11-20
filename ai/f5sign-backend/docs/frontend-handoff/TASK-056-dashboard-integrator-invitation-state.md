# Traspaso al dashboard y al integrador — qué fue de la invitación de cada destinatario

| | |
|---|---|
| **Origen** | rama `feat/delivery-facts` (desde `develop` `9a7f25b5`), **sin mergear, sin desplegar** · commit: ver `git log feat/delivery-facts`, el último que toca `src/` es el que manda · [TASK-056](../tasks/TASK-056-delivery-facts-and-sender-visibility.md) |
| **Fecha** | 2026-10-09 |
| **Repos afectados** | **dashboard** del remitente (estado del envío por destinatario) e **integradores** que leen el sobre por la API (`factor5-dashboard`) |
| **Naturaleza** | aditivo: cinco claves nuevas por destinatario en la lectura del sobre y dos miembros nuevos en `release_reason`. Cambia el **significado** de `NOT_REACHED` (ver abajo). Ninguna ruta nueva, ningún código de error nuevo |
| **Acción requerida** | mostrar `invitation_state` (y, si queréis, sus tres instantes) · tolerar valores desconocidos en tres enums abiertos · pintar los dos `release_reason` nuevos como «no alcanzado» |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

### Lectura: `GET /api/v1/envelopes/{id}`

Cada destinatario lleva cinco claves nuevas, planas, justo después de `outcome_recorded_at`:

| Clave | Qué es |
|---|---|
| `invitation_state` | Qué fue de su invitación. Ver abajo |
| `invitation_sent_at` | Último instante en que una invitación (o un reenvío) se entregó a un proveedor por algún canal; `null` si nunca. El enlace que llevaba se emitió justo antes y caduca siete días después de emitirse, así que como mucho siete días desde este instante; un reenvío o una corrección emiten uno nuevo sin revocar el anterior |
| `invitation_failed_at` | Último instante en que una invitación falló en todos los canales en que se probó; `null` si nunca |
| `invitation_unsent_at` | Último instante en que una invitación debida no se envió; `null` si nunca |
| `invitation_unsent_kind` | El porqué, junto a `invitation_unsent_at` (los dos `null` o los dos puestos): `NOT_SENT_NO_REACHABLE_CHANNEL` o `DELIVERED_BY_INTEGRATOR` |

**`invitation_state`** se calcula con lo que se registró cuando ocurrió y con la activación de su paso; **nunca** con
su contacto o su configuración de hoy. Cambiarle el email después no reescribe lo que pasó.

| Valor | Significa |
|---|---|
| `SENT` | Entregada a un proveedor por al menos un canal. ⚠ **`SENT` no es «recibida»**: no se registran acuses de operador (BL-390). Que un email o un SMS «salga» no prueba que llegue |
| `FAILED` | Todos los canales de la última invitación fallaron |
| `NOT_SENT_NO_REACHABLE_CHANNEL` | La plataforma no tenía ningún canal que pudiera alcanzarle |
| `DELIVERED_BY_INTEGRATOR` | El integrador iba a entregar el enlace; la plataforma no escribió |
| `NOT_YET` | Su paso está activo y **todavía no hay nada registrado**: una invitación en curso, **o una enviada antes de esta versión** (esas columnas no se rellenaron hacia atrás, así que no se distinguen). No lo leáis como «no enviada» |
| `null` | **No se le debe invitación ahora**: su paso aún no se activó (`steps[].activated_at`), firma por `MACHINE_KEY`, o es un hueco sin reclamar |

El último hecho registrado gana: una invitación fallida seguida de un reenvío que sale pasa a `SENT`.

⚑ **Las tres claves de instante no son un histórico**: cada una guarda solo el último. El historial por destinatario
no existe todavía.

### Los enums son abiertos

`invitation_state`, `invitation_unsent_kind` y `release_reason` son **conjuntos abiertos**: pueden ganar valores sin
aviso. Un consumidor tiene que tolerar uno desconocido (mostrarlo en crudo o como «desconocido»), no romper.

### `delivery` ahora puede discrepar de la invitación

El mapa `delivery` (por destino) puede mostrar un destino en `FAILED` junto a otro en `SENT` **mientras el
destinatario está bien**: es el rechazo de un canal, no una invitación fallida. El veredicto sobre la invitación
entera es `invitation_state`; `delivery` es el detalle por contacto. `FAILED` en `delivery` tampoco impide firmar.

### `release_reason`: dos miembros nuevos y un significado más estrecho

Un destinatario `RELEASED` puede leer:

- `NO_REACHABLE_CHANNEL`: su paso se activó y ningún canal podía alcanzarle.
- `INTEGRATOR_DELIVERED_NOT_OPENED`: el integrador iba a invitarle y el destinatario nunca abrió el enlace.

Ambos cuentan como «no alcanzado», igual que `DELIVERY_FAILED`, `UNCLAIMED` y `NOT_REACHED`: en un paso `AT_LEAST n` con veto, un liberado con cualquiera de los cinco termina el sobre `NOT_AGREED` con `end_cause: MEMBER_NOT_REACHED` (la lista de tres del traspaso de TASK-050 se queda corta). Y **`NOT_REACHED` pasa a significar «no
hay ningún hecho registrado de que la plataforma les alcanzara»**: un paso que nunca se activó, o un destinatario sin
ninguna invitación registrada. Los casos con causa conocida salen ahora con su propio miembro.

## Lo que el dashboard y el integrador tienen que hacer

1. **Mostrad `invitation_state`** junto a cada destinatario. `null` = nada que mostrar; `NOT_YET` = «pendiente de
   enviar», no «no enviada».
2. **No presentéis `SENT` como «entregada» ni «recibida»**; es «enviada» (entregada al proveedor).
3. **Tolerad valores desconocidos** en los tres enums abiertos.
4. **Pintad `NO_REACHABLE_CHANNEL` e `INTEGRATOR_DELIVERED_NOT_OPENED`** como «no alcanzado», y releed vuestra copia
   de `NOT_REACHED` a la luz del significado nuevo.
5. **No deriváis el estado de `email`/`phone` ni de `delivery`**: leed `invitation_state`.

## Lo que NO está listo todavía

- Acuses de recepción del operador: `SENT` es el techo (BL-390).
- Historial de invitaciones por destinatario: solo el último instante de cada clase.
- `DELIVERED_BY_INTEGRATOR` (estado) e `INTEGRATOR_DELIVERED_NOT_OPENED` (motivo): definidos y publicados, pero nada los produce hasta TASK-031 (la primera lista de canales vacía); tolerarlos ya, no esperarlos. ⛑ **2026-10-13**: TASK-031 los produce para un destinatario con `notification_channels: []` ([traspaso de TASK-031](TASK-031-notification-channels.md)).
- Reintentos del proveedor ante fallos transitorios: hasta que lleguen, todo `FAILED` es definitivo.

## Cómo verificarlo desde el frontal

No adoptéis las claves hasta que el `doc.json` del despliegue que os sirve publique `invitation_state` en el esquema
`Recipient`. Después, un sobre enviado debe traer `invitation_state` no nulo en todo destinatario cuyo paso esté
activo y que firme por la plataforma.
