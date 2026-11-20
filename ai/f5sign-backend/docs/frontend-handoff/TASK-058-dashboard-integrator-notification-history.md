# Traspaso al dashboard y al integrador — historial de mensajes de cada destinatario

| | |
|---|---|
| **Origen** | rama `feat/notification-history`, **sin mergear, sin desplegar** · commit: ver `git log feat/notification-history`, el último que toca `src/` es el que manda · [TASK-058](../tasks/TASK-058-recipient-notification-history.md) |
| **Fecha** | 2026-10-15 |
| **Repos afectados** | **dashboard** del remitente (historial de mensajes por destinatario) e **integradores** que leen el sobre por la API (`factor5-dashboard`) |
| **Naturaleza** | aditivo: una ruta nueva de solo lectura y dos códigos de error nuevos, `INVALID_PAGE_SIZE` e `INVALID_CURSOR`. Ninguna ruta existente cambia |
| **Acción requerida** | mostrar el historial por destinatario · tolerar valores desconocidos en `purpose` |
| **Desplegado** | not yet |
| **Status** | Pending |

## La ruta

**`GET /api/v1/envelopes/{id}/recipients/{recipientId}/notifications`** devuelve todo lo que la plataforma envió a
un destinatario de un sobre: invitaciones, reenvíos, códigos de un solo uso, avisos de cierre y copias selladas, con
lo que fue de cada mensaje en cada canal. Solo lectura: no escribe nada y no decide nada. Las formas exactas están en
el `doc.json` de la API, etiqueta `Notifications`.

- **Autenticación:** la clave de máquina y la cabecera `F5Sign-Declared-Subject`, como en las demás rutas de
  integrador. Cualquier clave del tenant lee el historial de cualquier destinatario de cualquier sobre del tenant.
- **`limit`** (opcional): cuántas ocasiones devolver, de 1 a 200; **50 por defecto**.
- **`cursor`** (opcional): el `next_cursor` de la página anterior, tal cual. Se omite en la primera página.
- Orden: del más antiguo al más reciente, por `requested_at` de la ocasión y luego por `notification_id`.

## La respuesta

Una **ocasión** es un mensaje que la plataforma decidió enviar (una invitación, un código…). Cada ocasión lleva una
**entrega** por canal, en el orden en que la ocasión listó sus canales. Ejemplo con dos ocasiones: una invitación
cuyo SMS falló de forma permanente y cayó a EMAIL, bajo una lista ordenada de canales, y un código de acceso.

```json
{
  "notifications": [
    {
      "notification_id": "0192f0a4-6b1e-7c3d-8e2f-4a5b6c7d8e9f",
      "purpose": "RECIPIENT_INVITATION",
      "requested_at": "2026-10-15T09:00:00+00:00",
      "deliveries": [
        {
          "channel": "SMS",
          "destination": "+*********56",
          "status": "FAILED",
          "failure_kind": "PERMANENT",
          "requested_at": "2026-10-15T09:00:00+00:00",
          "settled_at": "2026-10-15T09:00:02+00:00"
        },
        {
          "channel": "EMAIL",
          "destination": "f***@***.com",
          "status": "SENT",
          "failure_kind": null,
          "requested_at": "2026-10-15T09:00:02+00:00",
          "settled_at": "2026-10-15T09:00:03+00:00"
        }
      ]
    },
    {
      "notification_id": "0192f0a7-1c44-7a90-b3d1-0e5f6a7b8c9d",
      "purpose": "AUTH_OTP_ACCESS",
      "requested_at": "2026-10-15T09:12:30+00:00",
      "deliveries": [
        {
          "channel": "EMAIL",
          "destination": "f***@***.com",
          "status": "SENT",
          "failure_kind": null,
          "requested_at": "2026-10-15T09:12:30+00:00",
          "settled_at": "2026-10-15T09:12:31+00:00"
        }
      ]
    }
  ],
  "next_cursor": null
}
```

Todas las claves están siempre presentes; una ausente se escribe `null`. Los esquemas están cerrados: no habrá
claves que no estén aquí. Los instantes van en ISO 8601 con desfase.

**Raíz**

| Clave | Qué es |
|---|---|
| `notifications` | Las ocasiones de esta página; `[]` si no hay ninguna |
| `next_cursor` | Pásalo como `cursor` para la página siguiente; `null` en la última. **Opaco**: no lo interpretéis ni lo construyáis |

**Ocasión**

| Clave | Qué es |
|---|---|
| `notification_id` | Identificador de la ocasión (UUID) |
| `purpose` | Por qué se envió. Valores hoy: `RECIPIENT_INVITATION`, `RECIPIENT_INVITATION_RESENT`, `ENVELOPE_COMPLETED`, `ENVELOPE_ENDED_SENDER_CANCELLED`, `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON`, `ENVELOPE_ENDED_DECLINED`, `ENVELOPE_ENDED_TIME_RAN_OUT`, `ENVELOPE_ENDED_OUT_OF_REACH`, `SEALED_COPY_READY`, `AUTH_OTP_ACCESS`, `AUTH_OTP_SIGNING`, `AUTH_OTP_DECLINE` y, desde TASK-071 (2026-10-26, sin desplegar), `RECIPIENT_ACT_RECORDED`, `RECIPIENT_PART_COMPLETE`, `RECIPIENT_DECLINE_RECORDED` y cinco `ENVELOPE_ENDED_*_YOUR_COPY`. **Conjunto abierto**: mostrad un valor desconocido en lugar de rechazarlo |
| `requested_at` | Cuándo decidió la plataforma enviarlo |
| `deliveries` | Una entrega por canal |

Las dos invitaciones avisan al destinatario de que tiene un sobre que atender (firmar, aprobar o verlo, según su rol); `ENVELOPE_COMPLETED` y los `ENVELOPE_ENDED_*` le dicen
cómo terminó el sobre; `SEALED_COPY_READY`, que su copia sellada está lista; los tres `RECIPIENT_*` nuevos le dicen que su acto quedó registrado, que su parte está completa o que su rechazo quedó registrado, y los `*_YOUR_COPY`, cómo terminó el sobre para quien firmó; los tres `AUTH_OTP_*` llevan un código de
un solo uso, que **nunca** se devuelve.

**Entrega**

| Clave | Qué es |
|---|---|
| `channel` | `EMAIL`, `SMS` o `LOG`. `LOG` escribe en el registro propio de la plataforma y no llega a nadie |
| `destination` | A dónde se envió, enmascarado (ver abajo); `null` si no hay |
| `status` | Ver «Qué significa cada estado» |
| `failure_kind` | `PERMANENT` o `TRANSIENT`, solo cuando `status` es `FAILED`; `null` en los demás |
| `requested_at` | Cuándo se pidió a este canal que enviara |
| `settled_at` | Cuándo `status` pasó a ser definitivo |

## Enmascarado

El destino nunca sale en claro. Una dirección conserva su primer carácter y su sufijo final: `f***@***.com`. Un
teléfono conserva el `+` y las dos últimas cifras: `+*********56`. `destination` es `null` para un canal `LOG` y para
un destino que no es ni una dirección ni un teléfono. Es la misma máscara que usa el registro de auditoría.

## Reglas

- **Un destinatario sin mensajes es `200` con `{"notifications": [], "next_cursor": null}`**, no un `404`.
- **Un solo `404` (`NOT_FOUND`), con el mismo cuerpo**, para un sobre desconocido, un sobre de otro tenant y un
  destinatario que no está en el sobre. El cuerpo no nombra ningún id: no se puede distinguir entre los tres casos.
- **`400`**:
  - `INVALID_PAGE_SIZE`: `limit` no es un número entero de 1 a 200.
  - `INVALID_CURSOR`: `cursor` no tiene la forma en que esta ruta lo devuelve. Se rechaza por su forma, no por quién
    lo emitió: pasad `next_cursor` tal cual. Se rechaza igual aunque el sobre no sea vuestro.
  - `INVALID_ENVELOPE_ID` / `INVALID_RECIPIENT_ID`: un id de la ruta que no es un UUID.
  - `BAD_REQUEST`: falta la cabecera `F5Sign-Declared-Subject`.
  - `INVALID_DECLARED_SUBJECT`: la cabecera está pero no es válida (vacía, más de 128 octetos, con espacios, con `@` o con el prefijo reservado `f5s:` salvo el valor `f5s:none`).
- `401` sin clave de máquina válida.
- El cursor es **opaco**. Una página siguiente se pide con el `next_cursor` recibido y los mismos demás parámetros.

## Qué significa cada estado

| `status` | Significa |
|---|---|
| `PENDING` | Aún sin resolver |
| `SENT` | ⚠ **El proveedor lo aceptó. No significa «recibido»**: no se registran acuses de operador (BL-390). Un mensaje aceptado y perdido aguas abajo sigue leyéndose `SENT` |
| `DELIVERED` | Reservado: ningún canal informa de acuses todavía, así que hoy nada lo escribe. Tolerad el valor |
| `FAILED` | Falló; mirad `failure_kind` |
| `NOT_NEEDED` | No se envió porque ya no hacía falta (un canal anterior alcanzó al destinatario, o el sobre o el destinatario cambiaron antes). **Es un estado, no un fallo**: `failure_kind` es `null` |

| `failure_kind` | Significa |
|---|---|
| `PERMANENT` | El proveedor lo rechazó |
| `TRANSIENT` | Todos los reintentos fallaron, o se agotó la ventana de envío de un código de un solo uso antes de poder enviarlo |

## Los instantes

- `requested_at` de la **entrega** puede ser posterior al de la ocasión: en un canal de reserva es el momento en que
  se probó, después de que fallara el anterior.
- `requested_at` de la entrega es `null` para un canal de reserva **nunca probado**, y para algunos mensajes
  anteriores a esta versión.
- `settled_at` es `null` mientras la entrega está `PENDING` **y también** para mensajes resueltos antes de esta
  versión. **El estado, no `settled_at`, dice si sigue pendiente.**

## Qué no se devuelve nunca

El texto con que el proveedor rechazó el mensaje, la referencia del proveedor, el código de un solo uso y el enlace.
Tampoco hay filtros por propósito o canal, ni un historial de todo el tenant; si el dashboard los necesita, es un
seguimiento aparte.
