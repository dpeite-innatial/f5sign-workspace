# Ejemplo completo: Story S09.1 detallada

Este es un ejemplo REAL y COMPLETO de como debe quedar una story tras ejecutar `/planning-detail`. Usa este ejemplo como referencia de formato, profundidad y tono. Todas las stories deben tener este mismo nivel de detalle.

---

# S09.1 — Crear Sobre en DRAFT

> **Epic:** EP09 | **Fase:** F2 | **Story Points:** 8
> **Depende de:** S05.2 (tabla envelope), S07.1 (middleware tenant), S08.1 (error handling)
> **Bloquea:** S09.2, S09.3, S10.1, S11.1, S12.1

## User Story
**Como** remitente autenticado en el Dashboard
**Quiero** crear un nuevo sobre vacio en estado borrador
**Para** iniciar un proceso de firma electronica al que luego aniadire documentos, destinatarios y campos

## Contexto funcional

### Que es un Envelope
El Envelope es el aggregate root del bounded context Envelope. Representa un proceso de firma completo: contiene documentos, destinatarios, campos y configuracion. Todo envelope comienza como DRAFT y progresa a traves de una maquina de estados hasta COMPLETED, DECLINED, EXPIRED o VOIDED.

### Maquina de estados (MVP)
```
DRAFT --> SENT --> IN_PROGRESS --> READY_TO_SEAL --> SEALING --> COMPLETED
  |                    |                                 |
  |                    +--> DECLINED                     +--> SEALING_FAILED
  |                    +--> EXPIRED
  |                    +--> VOIDED
  |                    +--> CORRECTING --> (vuelve a IN_PROGRESS)
  +--> READY_TO_SEAL (seal-only, sin firmantes)
```

Solo la transicion DRAFT -> SENT (o DRAFT -> READY_TO_SEAL para seal-only) es relevante en esta story. Las demas se implementan en stories posteriores.

### Tipo de workflow
- `STANDARD`: tiene firmantes humanos. Flujo normal.
- `SEAL_ONLY`: sin firmantes. Solo sellado corporativo. Se marca al crear si se sabe, o se infiere al enviar.

### Campos del Envelope al crear
Al crear un sobre solo se requiere `name`. El resto son opcionales o se asignan automaticamente:

| Campo | Obligatorio | Default | Notas |
|-------|------------|---------|-------|
| name | Si | — | Min 1 char, max 255 |
| locale | No | tenant.default_locale | Idioma del Audit Trail |
| expires_in_days | No | 30 | Rango: 1-365. Se calcula expires_at al enviar, NO al crear |
| reminder_frequency_days | No | 2 | Frecuencia de recordatorios automaticos. 0 = desactivados |
| message | No | null | Mensaje general para todos los firmantes |
| workflow_type | No | STANDARD | STANDARD o SEAL_ONLY |

### PlanEnforcement
Antes de crear el sobre, verificar la cuota del plan del tenant:
- Free: 5 envelopes/mes
- Starter: 50/usuario/mes
- Business: 200/usuario/mes
- Enterprise: ilimitado (negociado)

La verificacion se hace con `PlanEnforcerInterface::canCreateEnvelope(tenantId)`. En modo Dedicated, `UnlimitedPlanEnforcer` siempre retorna true.

Si la cuota esta agotada, lanzar `PlanLimitExceededException` (HTTP 402).

### API: POST /v1/envelopes

**Request:**
```json
{
  "name": "Contrato de alquiler 2026",
  "locale": "es",
  "expires_in_days": 30,
  "reminder_frequency_days": 2,
  "message": "Por favor firme este contrato",
  "workflow_type": "STANDARD"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Contrato de alquiler 2026",
  "status": "DRAFT",
  "workflow_type": "STANDARD",
  "locale": "es",
  "expires_in_days": 30,
  "reminder_frequency_days": 2,
  "message": "Por favor firme este contrato",
  "documents_count": 0,
  "recipients_count": 0,
  "created_by": "user-uuid",
  "created_at": "2026-04-10T14:30:00Z",
  "updated_at": "2026-04-10T14:30:00Z"
}
```

**Errores:**
| HTTP | Codigo | Cuando |
|------|--------|--------|
| 401 | UNAUTHORIZED | Sin JWT o JWT expirado |
| 402 | PLAN_LIMIT_EXCEEDED | Cuota de envelopes agotada. Incluir `upgrade_url` en body |
| 403 | INSUFFICIENT_PERMISSIONS | Usuario sin rol SENDER o ADMIN en el workspace |
| 422 | VALIDATION_ERROR | Campo name vacio, locale invalido, expires_in_days fuera de rango |

**Headers requeridos:**
- `Authorization: Bearer {jwt}`
- `Content-Type: application/json`

**Headers opcionales:**
- `Idempotency-Key: {uuid}` — si se envia, la segunda request con el mismo key devuelve el mismo response sin crear otro sobre

### SaaS vs Dedicated
- SaaS: PlanEnforcement activo, verifica cuota del plan
- Dedicated: `UnlimitedPlanEnforcer` siempre retorna true, sin limites

### Edge cases
- Nombre con solo espacios: debe rechazarse (trim + validar min length 1)
- Locale no soportado: rechazar 422 (solo "es" y "en" en MVP)
- expires_in_days = 0: rechazar 422 (minimo 1)
- Request duplicada con Idempotency-Key: retornar el mismo response (201, no 200)
- Tenant sin workspace: imposible en MVP (se crea workspace default al crear tenant)

### Seguridad
- Requiere JWT valido con tenant_id y user_id
- RLS filtra automaticamente por tenant_id
- El workspace_id se toma del JWT (workspace activo del usuario)
- Input sanitizado: name se escapa contra XSS antes de almacenar

## Criterios de aceptacion

### AC-01 — Crear sobre con datos validos
- **Given** usuario autenticado con rol SENDER en workspace "ws-123" y 3 envelopes usados de 50 del plan Starter
  **When** POST /v1/envelopes con body `{ "name": "Contrato 2026" }`
  **Then** responde 201 con envelope en estado DRAFT, UUID v4, locale "es" (default del tenant), created_at en UTC
  **And** se emite domain event `EnvelopeCreated` con envelope_id y tenant_id

### AC-02 — Crear sobre con todos los campos opcionales
- **Given** usuario autenticado
  **When** POST /v1/envelopes con `{ "name": "Test", "locale": "en", "expires_in_days": 90, "reminder_frequency_days": 5, "message": "Please sign", "workflow_type": "SEAL_ONLY" }`
  **Then** responde 201 con todos los campos reflejados en el response

### AC-03 — Validacion: nombre vacio
- **Given** usuario autenticado
  **When** POST /v1/envelopes con `{ "name": "" }`
  **Then** responde 422 con error `VALIDATION_ERROR` y detalle "name: This value should not be blank"

### AC-04 — Validacion: nombre demasiado largo
- **Given** usuario autenticado
  **When** POST /v1/envelopes con name de 256 caracteres
  **Then** responde 422 con error `VALIDATION_ERROR` y detalle "name: This value is too long"

### AC-05 — Plan limit exceeded
- **Given** usuario en plan Free con 5/5 envelopes usados este mes
  **When** POST /v1/envelopes con `{ "name": "Sexto sobre" }`
  **Then** responde 402 con error `PLAN_LIMIT_EXCEEDED` y body que incluye `upgrade_url`

### AC-06 — Sin autenticacion
- **Given** request sin header Authorization
  **When** POST /v1/envelopes
  **Then** responde 401 con error `UNAUTHORIZED`

### AC-07 — Rol insuficiente
- **Given** usuario con rol VIEWER en el workspace
  **When** POST /v1/envelopes
  **Then** responde 403 con error `INSUFFICIENT_PERMISSIONS`

### AC-08 — Idempotencia
- **Given** usuario autenticado envia POST /v1/envelopes con `Idempotency-Key: abc-123` y recibe 201
  **When** reenvia la misma request con el mismo `Idempotency-Key: abc-123`
  **Then** responde 201 con el MISMO envelope (mismo id, mismos datos)
  **And** no se crea un segundo envelope en BD

### AC-09 — Aislamiento de tenant
- **Given** usuario del tenant A crea un sobre
  **When** usuario del tenant B hace GET /v1/envelopes
  **Then** el sobre del tenant A NO aparece en los resultados

## Tasks

| ID | Nombre | Pts | Tipo | Archivos principales | Estado |
|----|--------|-----|------|---------------------|--------|
| T09.1.1 | Entity Envelope + Value Objects | 2 | Backend | `src/Envelope/Domain/Entity/Envelope.php` | pendiente |
| T09.1.2 | Repository + Doctrine Mapping | 2 | Backend | `src/Envelope/Infrastructure/Persistence/DoctrineEnvelopeRepository.php` | pendiente |
| T09.1.3 | CreateEnvelopeCommand + Handler | 2 | Backend | `src/Envelope/Application/Command/CreateEnvelope/` | pendiente |
| T09.1.4 | Controller POST /v1/envelopes | 1 | Backend | `src/Envelope/Infrastructure/Http/Controller/EnvelopeController.php` | pendiente |
| T09.1.5 | Frontend: store + API call | 1 | Frontend | `apps/dashboard/stores/useEnvelopeStore.ts` | pendiente |

## Referencias
- [Pilar 1 — Workflows y Ciclo de Vida](../../../../Arquitectura/Pilares/1.%20Workflows%20y%20Ciclo%20de%20Vida.md) — secciones A y D
- [ERD PostgreSQL](../../../../Arquitectura/Modelo%20de%20Datos%20-%20ERD%20PostgreSQL.md) — tabla envelope
- [API RESTful](../../../../Arquitectura/Pilares/6.%20API%20RESTful%20y%20Webhooks.md) — POST /v1/envelopes
- [Pricing](../../../../Negocio/Modelo%20de%20Monetización%20y%20Pricing.md) — PlanEnforcement

---

# Ejemplo de Task detallada: T09.1.1

---

# T09.1.1 — Entity Envelope + Value Objects

> **Story:** S09.1 | **Epic:** EP09 | **Fase:** F2 | **Story Points:** 2
> **Depende de:** ninguna (primera task de la story)
> **Tipo:** Backend

## Descripcion
Crear la entidad Envelope como Aggregate Root del bounded context Envelope, junto con sus Value Objects (EnvelopeStatus, WorkflowType, EnvelopeName) y el Domain Event EnvelopeCreated. Incluir el mapping XML de Doctrine y los tests unitarios.

## Archivos a crear/modificar

| Archivo | Accion | Descripcion |
|---------|--------|-------------|
| `src/Envelope/Domain/Entity/Envelope.php` | Crear | Aggregate Root |
| `src/Envelope/Domain/ValueObject/EnvelopeStatus.php` | Crear | Enum backed con transiciones validas |
| `src/Envelope/Domain/ValueObject/EnvelopeName.php` | Crear | VO con validacion min/max length |
| `src/Envelope/Domain/ValueObject/WorkflowType.php` | Crear | Enum: STANDARD, SEAL_ONLY |
| `src/Envelope/Domain/Event/EnvelopeCreated.php` | Crear | Domain Event final readonly |
| `src/Envelope/Infrastructure/Persistence/Mapping/Envelope.orm.xml` | Crear | Doctrine XML mapping |
| `tests/Unit/Envelope/Domain/Entity/EnvelopeTest.php` | Crear | Tests unitarios |
| `tests/Unit/Envelope/Domain/ValueObject/EnvelopeStatusTest.php` | Crear | Tests de transiciones |
| `tests/Unit/Envelope/Domain/ValueObject/EnvelopeNameTest.php` | Crear | Tests de validacion |

## Detalle tecnico

### Entity Envelope — Propiedades

| Propiedad | Tipo PHP | Tipo BD | Nullable | Default | Constraint |
|-----------|----------|---------|----------|---------|------------|
| id | Uuid (VO de Shared) | UUID | No | gen_random_uuid() | PK |
| tenantId | Uuid | UUID | No | — | FK tenant(id), RLS |
| workspaceId | Uuid | UUID | No | — | FK workspace(id) |
| createdBy | Uuid | UUID | No | — | FK user(id) |
| name | EnvelopeName (VO) | VARCHAR(255) | No | — | min:1, max:255 |
| status | EnvelopeStatus (Enum) | envelope_status ENUM | No | DRAFT | — |
| workflowType | WorkflowType (Enum) | workflow_type ENUM | No | STANDARD | — |
| locale | string | VARCHAR(5) | No | — | Heredado de tenant.default_locale si no se especifica |
| expiresInDays | int | SMALLINT | No | 30 | Rango 1-365 |
| reminderFrequencyDays | int | SMALLINT | No | 2 | 0 = desactivados |
| message | ?string | TEXT | Si | null | Mensaje general para firmantes |
| expiresAt | ?DateTimeImmutable | TIMESTAMPTZ | Si | null | Se calcula al enviar (created_at + expires_in_days) |
| sentAt | ?DateTimeImmutable | TIMESTAMPTZ | Si | null | Momento del envio |
| completedAt | ?DateTimeImmutable | TIMESTAMPTZ | Si | null | Momento de completarse |
| createdAt | DateTimeImmutable | TIMESTAMPTZ | No | now() | — |
| updatedAt | DateTimeImmutable | TIMESTAMPTZ | No | now() | — |

### Value Object EnvelopeStatus

PHP backed enum con string values:

```
DRAFT, SENT, IN_PROGRESS, READY_TO_SEAL, SEALING, SEALING_FAILED, 
COMPLETED, VOIDED, DECLINED, EXPIRED, CORRECTING
```

Transiciones validas (metodo `canTransitionTo(EnvelopeStatus $target): bool`):

| Desde | Hacia | Trigger |
|-------|-------|---------|
| DRAFT | SENT | SendEnvelopeCommand |
| DRAFT | READY_TO_SEAL | SendEnvelopeCommand (workflow_type = SEAL_ONLY) |
| SENT | IN_PROGRESS | Primer firmante accede |
| IN_PROGRESS | READY_TO_SEAL | Ultimo firmante completa |
| IN_PROGRESS | DECLINED | Firmante rechaza |
| IN_PROGRESS | EXPIRED | Cron de expiracion |
| IN_PROGRESS | VOIDED | Remitente anula |
| IN_PROGRESS | CORRECTING | Remitente corrige datos de recipient |
| CORRECTING | IN_PROGRESS | Correccion aplicada |
| READY_TO_SEAL | SEALING | Worker inicia sellado |
| SEALING | COMPLETED | Sellado exitoso |
| SEALING | SEALING_FAILED | Error en EU DSS o TSA |
| SEALING_FAILED | SEALING | Retry manual |

Metodo `transitionTo(EnvelopeStatus $target): void` que lanza `InvalidEnvelopeTransitionException` si la transicion no es valida.

### Value Object EnvelopeName

- Constructor privado
- Factory: `EnvelopeName::fromString(string $name): self`
- Validacion: trim, length >= 1 y <= 255
- Lanza `InvalidEnvelopeNameException` si invalido

### Value Object WorkflowType

PHP backed enum: `STANDARD`, `SEAL_ONLY`

### Domain Event EnvelopeCreated

```
final readonly class EnvelopeCreated extends DomainEvent
  - envelopeId: string (UUID)
  - tenantId: string (UUID)
  - workspaceId: string (UUID)
  - createdBy: string (UUID)
  - workflowType: string ('STANDARD' | 'SEAL_ONLY')
  - occurredAt: DateTimeImmutable
```

### Doctrine XML Mapping

Archivo: `src/Envelope/Infrastructure/Persistence/Mapping/Envelope.orm.xml`

- Entity class: `App\Envelope\Domain\Entity\Envelope`
- Table: `envelope`
- id: type="uuid", generator strategy="NONE"
- tenant_id: type="uuid", column="tenant_id"
- status: type="string", column="status" (mapeado a PHP enum via custom type o string)
- Embedded: EnvelopeName como string (no es un embedded real, es un VO que se mapea a una columna)
- Timestamps: type="datetime_immutable"

### Invariantes de la entidad

1. Un envelope en DRAFT no puede tener expiresAt (se calcula al enviar)
2. Solo se puede modificar un envelope en estado DRAFT
3. El status solo cambia via transitionTo() (nunca setStatus())
4. La entidad acumula domain events via record() y los expone via pullEvents()

## Tests

| Test | Tipo | Archivo | Que verifica |
|------|------|---------|-------------|
| `testCreateDraft` | Unit | `tests/Unit/Envelope/Domain/Entity/EnvelopeTest.php` | Crea envelope DRAFT con campos validos, status=DRAFT, emite EnvelopeCreated |
| `testCreateWithAllOptionalFields` | Unit | Same | Crea con locale, expires_in_days, message, workflow_type |
| `testDefaultValues` | Unit | Same | Sin opcionales: locale del tenant, expires_in_days=30, reminder=2, workflow_type=STANDARD |
| `testTransitionDraftToSent` | Unit | Same | status DRAFT -> SENT ok |
| `testTransitionDraftToCompleted` | Unit | Same | status DRAFT -> COMPLETED lanza InvalidEnvelopeTransitionException |
| `testAllValidTransitions` | Unit | `tests/Unit/Envelope/Domain/ValueObject/EnvelopeStatusTest.php` | Cada transicion valida retorna true en canTransitionTo |
| `testAllInvalidTransitions` | Unit | Same | Cada transicion invalida retorna false |
| `testNameTooLong` | Unit | `tests/Unit/Envelope/Domain/ValueObject/EnvelopeNameTest.php` | 256 chars lanza InvalidEnvelopeNameException |
| `testNameEmpty` | Unit | Same | String vacio lanza InvalidEnvelopeNameException |
| `testNameOnlySpaces` | Unit | Same | "   " lanza InvalidEnvelopeNameException (tras trim) |
| `testNameValid` | Unit | Same | "Contrato 2026" crea VO correctamente |
| `testDomainEventPayload` | Unit | `tests/Unit/Envelope/Domain/Entity/EnvelopeTest.php` | EnvelopeCreated tiene todos los campos correctos |
| `testPullEventsClears` | Unit | Same | Despues de pullEvents(), la lista esta vacia |
