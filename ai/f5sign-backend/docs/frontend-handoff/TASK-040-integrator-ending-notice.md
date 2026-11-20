# Traspaso al integrador — el motivo de anulación llega, literal, a los destinatarios invitados

| | |
|---|---|
| **Origen** | rama `feat/task-048-how-an-envelope-ends` (paquete [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)) · TASK-040 cerrada en `0aad773b` · sin mergear en `develop` |
| **Fecha** | 2026-09-29 |
| **Repos afectados** | `dashboard-sf` (integración de Factor5) y cualquier integrador que llame a `POST /api/v1/envelopes/{id}/void`. El signer no se ve afectado: ninguna ruta de firma, `ProblemCode` ni campo que lea cambia |
| **Naturaleza** | **cambia el significado de un campo sin cambiar su forma**: `reason` de `void` deja de ser una nota interna |
| **Acción requerida** | no mandar un motivo por defecto; si se ofrece un campo de motivo, avisar de que lo leen los firmantes |
| **Desplegado** | no — sin mergear en `develop` |
| **Status** | Pending. `dashboard-sf` dejó de mandar motivos fijos (informado por el mantenedor; no visto en su árbol) |

## Lo que cambió en el contrato

- **Cada vez que un sobre termina sin acuerdo, el backend avisa por correo a cada destinatario al que ya había
  invitado.** Da igual la causa: anulación del emisor, rechazo, expiración ([TASK-049](TASK-049-integrator-an-envelope-expires.md)) o
  política de paso. Quien nunca fue invitado (un paso que no llegó a activarse) no recibe nada. El aviso no lleva
  enlace ni nombra a nadie, y va en el idioma del destinatario.
- **El `reason` de `POST /api/v1/envelopes/{id}/void` ya no es una nota interna.** Con motivo, el aviso lo **cita
  literalmente** al destinatario. Sin motivo, se manda un cuerpo que no lo menciona. **Vacío o solo espacios
  cuenta como sin motivo**, igual que omitirlo o mandar `null`.
- Los avisos van **por correo hoy**, con el motivo entero; si algún día van por SMS, allí podrá recortarse (el
  `#[OA\Property]` de `VoidEnvelopeRequest::$reason` lo dice).
- La forma no cambia: mismo campo, límite de 1000 caracteres, mismas respuestas y códigos. Cambia para qué sirve, y
  ningún test de contrato lo va a detectar. El texto se sigue guardando como `end_reason` en el sobre y en el
  registro de eventos.

## Lo que el frontal tiene que hacer

1. **No mandar un motivo por defecto.** Si el operador no escribió nada, omitid `reason`, mandad `null` o `""`.
   Un literal fijo («Cancelado por el usuario») llegaría a cada destinatario como si fuera el motivo, en español
   aunque el aviso vaya en otro idioma, y «el usuario» sería, para él, él mismo.
2. **`dashboard-sf`: ya hecho por su parte** (informado, no visto): dejó de enviar los motivos codificados, y por
   decisión del mantenedor **sus diálogos no tendrán campo de motivo**. Si algún día se añade, el texto de ayuda
   tiene que decir que lo leerán los firmantes.
3. **No mandéis un aviso propio de cancelación** a los firmantes: ya lo manda el backend.
4. Cualquier comentario o documentación vuestra que diga que el motivo es solo interno queda desfasado.

## Lo que NO está listo todavía

- **Avisos por SMS**: hoy solo correo. El SMS depende de la selección de canal (TASK-031).
- Nada está desplegado; comprobad el `doc.json` de vuestro entorno (regla 4).

## Cómo verificarlo desde el frontal

- Anular un sobre ya enviado sin `reason` y con `reason: "   "`: el destinatario invitado recibe el aviso sin motivo.
- Anular con un `reason` de texto: el aviso lo cita entero.
