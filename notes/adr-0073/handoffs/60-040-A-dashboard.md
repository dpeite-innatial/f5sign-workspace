# Traspaso al integrador (PROVISIONAL): el motivo de anulación llega a los destinatarios

| | |
|---|---|
| **Origen** | TASK-040 (aviso de fin sin acuerdo, dentro del paquete ADR-0073), etapa A |
| **Medido en** | `f5sign-backend` rama `feat/ending-notice` @ `5715b3c7` (2026-09-29; re-sellado, antes `0273fc33`); `dashboard-sf` rama `feat/waybill-pdf-pagination` @ `a4d8637ac` (2026-09-23). Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | `dashboard-sf` (integración de Factor5). El signer no se ve afectado: no cambia ninguna ruta de firma, ningún `ProblemCode` ni ningún campo que lea |
| **Status** | **PROVISIONAL, accionable ya.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` cuando el paquete ADR-0073 aterrice. Los nombres de propósito (`ENVELOPE_ENDED_*`) son internos y no fijados; a vosotros no os llegan |

## Qué cambió (commiteado, no planeado)

- **Cada vez que un sobre termina sin acuerdo, el backend avisa por email a cada destinatario al que ya había
  invitado.** Da igual la causa: anulación del emisor, rechazo, y más adelante expiración y política de paso.
  Los destinatarios de pasos que nunca se activaron no reciben nada. El aviso no lleva enlace ni nombra a nadie.
  Va en el idioma del destinatario.
- **El `reason` de `POST /api/v1/envelopes/{id}/void` deja de ser una nota interna.** Cuando el emisor anula
  con motivo, el aviso **cita el texto literal** al destinatario. Sin motivo, se envía un cuerpo que no lo menciona.
  El `#[OA\Property]` de `VoidEnvelopeRequest::$reason` ya lo dice en el spec:
  > *"Why you are cancelling the envelope. This text is NOT an internal note: it is quoted verbatim to the
  > recipients […] Omit it, send null, or send an empty or whitespace-only string to cancel without a reason
  > […] Notices go by email today and carry the reason in full; should they ever go by SMS, the reason may be
  > shortened there to fit a single message."*
- La forma del contrato no cambia: el campo, el límite de 1000, las respuestas y los códigos siguen igual.
  Cambia **para qué sirve el campo**, y eso ningún test vuestro lo va a detectar.

## ⚠ El hallazgo: hoy todos vuestros envíos llevan motivo, y es uno fijo

Medido en vuestro árbol:

- `WaybillController::anularAction()` (`src/Controller/TransportRequest/WaybillController.php:433`):
  `$request->request->getString('reason') ?: 'Carta de porte anulada por el usuario'`
- `WaybillSignatureController::signatureVoidAction()` (`…/WaybillSignatureController.php:648`):
  `$request->request->getString('reason') ?: 'Cancelado por el usuario'`
- Ningún JS envía `reason`: ni el botón "Anular" (`waybill/init.js`) ni "Cancelar la firma"
  (`waybill/signature.js`). Siempre sale el literal por defecto.

Con este backend desplegado, **cada anulación desde Factor5 manda a cada destinatario invitado** algo así:

> El remitente ha cancelado la firma de «…», que no seguirá adelante.
>
> Motivo indicado por el remitente:
> **Cancelado por el usuario**

Hay tres problemas con eso. Para el destinatario, "el usuario" es él mismo, así que parece que canceló él.
El literal va en español aunque el destinatario reciba el aviso en inglés. Y el mensaje no aporta nada:
decir "cancelado" ya es lo que dice el aviso sin motivo.

## Qué tiene que hacer el dashboard-sf

1. **Dejar de mandar el motivo por defecto.** Si el operador no escribió nada, no enviéis `reason`: omitidlo,
   mandad `null` o `""`. El backend lo trata como sin motivo y manda el cuerpo que no lo menciona. En la práctica:
   - quitar el `?: '…'` de las dos líneas de arriba;
   - hacer que `F5SignApiGateway::void()` acepte `?string $reason`;
   - que no incluya la clave cuando sea `null` o vacía.
2. **El comentario de `F5SignApiGateway::void()`** ("The reason lands in the backend's append-only event log…")
   ya no es cierto del todo: también llega a los destinatarios. Corregidlo en el mismo cambio.
3. **Opcional, decisión de producto vuestra:** ofrecer al operador un campo de motivo al anular. Si lo hacéis, el
   texto de ayuda tiene que decir que **lo leerán los firmantes**, porque el campo del spec es el único control
   sobre esa divulgación. Máximo 1000 caracteres. Hoy el aviso va solo por email, con el motivo entero; si algún día va por SMS, allí podrá recortarse.
4. **No enviéis vosotros un aviso propio de cancelación a los firmantes**: ya lo manda el backend. En el árbol
   medido no encontré ninguno junto a las dos acciones de anular; si existe en otro sitio, sobra.

Nada de esto rompe si no lo hacéis: el endpoint acepta lo mismo que hoy. Lo que sale mal es el mensaje que
reciben vuestros firmantes.
