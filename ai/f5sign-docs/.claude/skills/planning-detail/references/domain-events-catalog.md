# Catalogo de Domain Events — MVP

Este catalogo lista TODOS los domain events del MVP con sus productores y consumidores. Cuando rellenes una task que emite o escucha un evento, consulta este catalogo para saber exactamente quien mas lo necesita.

Fuente completa: `Arquitectura/Catalogo de Domain Events.md`

Solo se listan aqui los eventos MVP. Para eventos v1/v2, consultar el documento fuente.

---

## Envelope

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `EnvelopeCreated` | POST /v1/envelopes | Audit (ENVELOPE_CREATED), Webhook (envelope.created) |
| `EnvelopeSent` | POST /v1/envelopes/{id}/send | Notification (SIGN-001 invitacion), Workflow (activa step 1), Audit, Webhook (envelope.sent) |
| `EnvelopeCompleted` | Sellado exitoso (worker) | Notification (SIGN-005 completado + PDF adjunto), Audit (genera Audit Trail), Webhook (envelope.completed) |
| `EnvelopeVoided` | POST /v1/envelopes/{id}/void | Notification (SIGN-006), Audit, Webhook (envelope.voided) |
| `EnvelopeExpired` | Cron C-13 (cada 5 min) | Notification (SIGN-007), Audit, Webhook (envelope.expired) |
| `EnvelopePaused` | Correccion en vuelo | Notification (SIGN-020), Audit |
| `EnvelopeResumed` | Correccion aplicada | Notification (SIGN-021), Audit |
| `EnvelopeExtended` | Ampliar plazo | Notification (SIGN-012), Audit, Webhook (envelope.deadline_extended) |
| `RecipientCorrected` | Corregir email/phone | Notification (SIGN-011 nueva invitacion), Audit |

## Signature

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `DocumentSigned` | Firmante completa firma | Workflow (evalua si step completo), SigningGroup (cuenta quorum), Audit (RECIPIENT_SIGNED), Webhook (recipient.signed) |
| `SignatureDeclined` | Firmante rechaza | Envelope (-> DECLINED), Notification (SIGN-008), Audit, Webhook (recipient.declined) |
| `SignatureDelegated` | Firmante delega | Envelope (nuevo recipient), Notification (SIGN-009), Audit, Webhook (recipient.delegated) |
| `EnvelopeReadyToSeal` | Ultimo firmante completa | Worker W-02 (inicia sellado) |

## Workflow

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `StepCompleted` | Todos los recipients del step terminan | AdvanceWorkflowHandler -> WorkflowAdvanced |
| `WorkflowAdvanced` | Step completado, avanza al siguiente | Notification (SIGN-010 invitacion siguiente step), Audit |

## Authentication

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `AuthVerified` | OTP/AccessCode correcto | Signature (desbloquea firma), Audit (RECIPIENT_AUTH_PASSED), Webhook (recipient.auth_passed) |
| `AuthFailed` | OTP incorrecto | Audit (intento fallido) |
| `AuthBlocked` | 3+ intentos fallidos | Notification (SIGN-017 alerta), Audit |
| `OtpSent` | Envio OTP SMS/Email | Notification (AUTH-001/002), Billing (SMS_SENT si SMS), Audit |

## Evidence

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `EvidenceCollected` | Evidencias capturadas (geo, fingerprint, biometria) | Audit |

## Cryptography

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `DocumentSealed` | Worker W-02 completa sellado PAdES | Envelope (-> COMPLETED), Audit (DOCUMENT_SEALED), W-03 (genera Audit Trail), Webhook (document.sealed) |

## Notification

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `NotificationSent` | Email/SMS entregado | Audit (RECIPIENT_NOTIFIED) |
| `NotificationFailed` | Fallo de envio (tras retries) | Audit, alerta Ops |
| `ReminderSent` | Recordatorio auto o manual | Audit (REMINDER_SENT), Webhook (reminder.sent) |

## SigningGroup

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `QuorumReached` | Firmas >= min_signatures | Workflow (avanza step), Notification (SIGN-014), Audit, Webhook (signing_group.quorum_reached) |
| `QuorumImpossible` | Demasiadas declinaciones | Notification (SIGN-015 alerta), Audit, Webhook (signing_group.quorum_impossible) |

## API (Webhooks)

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `WebhookDelivered` | W-04 entrega exitosa (HTTP 2xx) | Audit (WEBHOOK_SENT) |
| `WebhookFailed` | 8 reintentos agotados | Notification (API-003 alerta), Audit |

## User

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `UserCreated` | Crear usuario | Audit, Notification (ACCT-002 bienvenida) |
| `UserLoggedIn` | Login exitoso | Audit (USER_LOGIN) |
| `PasswordReset` | Reset de contrasena | Notification (ACCT-004) |

## Document

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `DocumentUploaded` | Upload PDF exitoso | Audit |

## Legal

| Evento | Trigger | Consumidores |
|--------|---------|-------------|
| `LegalDocumentPublished` | Nueva version publicada | Si major: Notification (re-aceptacion), Cron C-09 (recordatorios) |
| `LegalDocumentAccepted` | Admin acepta documento | Audit |

---

## Como usar este catalogo en las tasks

Cuando una task EMITE un evento:
- Lista el evento en "Domain Events" del detalle tecnico
- Incluye el payload completo (propiedades con tipos)
- Referencia los consumidores de este catalogo

Cuando una task CONSUME un evento (EventSubscriber):
- Indica que evento escucha
- Describe la accion que ejecuta
- Referencia el productor de este catalogo

Cuando una task implementa un WEBHOOK:
- Mapea el domain event al webhook event type (ej: `EnvelopeSent` -> `envelope.sent`)
- Incluye el payload del webhook (subset del domain event)
