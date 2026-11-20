# Traspaso al dashboard — la puerta de acceso se declara siempre: cambio incompatible al añadir un destinatario

| | |
|---|---|
| **Origen** | rama `feat/explicit-access-gate`, **sin mergear** · [TASK-063](../tasks/TASK-063-the-access-gate-is-always-declared.md) · [ADR-0082](../adr/ADR-0082-the-access-gate-is-always-declared.md) |
| **Fecha** | 2026-10-20 |
| **Repos afectados** | **dashboard** (el firmante no cambia) |
| **Naturaleza** | **cambio incompatible** del cuerpo de `POST /api/v1/envelopes/{id}/recipients` |
| **Acción requerida** | **sí, antes del despliegue**: sin ella, añadir un destinatario devuelve 422 |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

La puerta de acceso se declara siempre: el cuerpo lleva `auth.access_method` o un `auth.access_methods` no vacío.
Sin ella, la ruta responde **422** `VALIDATION_ERROR` con `errors[].field = "auth.access_methods"`:

> The access gate must be declared: send auth.access_method or auth.access_methods. To let the link alone admit this recipient, declare DIRECT_LINK.

- **Puerta abierta** (el enlace basta): se escribe `DIRECT_LINK`, como escalar (`access_method`) o como lista de uno
  (`access_methods: ["DIRECT_LINK"]`). En una lista de dos o más, `DIRECT_LINK` es 422.
- **La puerta de firma sigue opcional**, y `DIRECT_LINK` ahí sigue rechazado.
- **Exentos** (siguen sin `auth`): `signs_via: MACHINE_KEY` (con `DIRECT_LINK` al lado es 422, en
  `auth.access_method` o `auth.access_methods[0]`) y los roles `IN_PERSON_HOST` y `CERTIFIED_DELIVERY`.
- **Un slot reclamable (`claimable: true`) NO está exento**: también declara la puerta.

Detalle y motivo: [ADR-0082](../adr/ADR-0082-the-access-gate-is-always-declared.md).

## Lo que no cambia

La lectura es asimétrica a propósito: `GET /api/v1/envelopes/{id}` sigue devolviendo `access_methods: []` para una
puerta abierta, y el descriptor del firmante sigue con `access_gate: null`. Al reenviar lo leído, hay que traducir
`[]` a `["DIRECT_LINK"]`.

## Antes / después

Un destinatario SIGNER con la puerta abierta. Antes:

```json
{
  "step_ordinal": 1,
  "role": "SIGNER",
  "email": "ana@example.com",
  "notification_channels": ["EMAIL"]
}
```

Ahora (422 si falta `auth`):

```json
{
  "step_ordinal": 1,
  "role": "SIGNER",
  "email": "ana@example.com",
  "notification_channels": ["EMAIL"],
  "auth": { "access_method": "DIRECT_LINK" }
}
```

Un slot reclamable, que también declara su puerta:

```json
{
  "step_ordinal": 1,
  "role": "SIGNER",
  "claimable": true,
  "auth": { "access_methods": ["OTP_EMAIL"] }
}
```

## Lo que el frontal tiene que hacer

- Enviar siempre la puerta de acceso.
- **Dejar de recortar los métodos declarados a los contactos disponibles.** En un slot no hay contactos, y ese
  recorte es lo que dejó la puerta abierta el 2026-10-20.
- Mostrar el 422 en el campo de la puerta de acceso.

## Cómo verificarlo

Crear un destinatario sin `auth` → 422 en `auth.access_methods`. Con `"auth": {"access_method": "DIRECT_LINK"}` → 201.
