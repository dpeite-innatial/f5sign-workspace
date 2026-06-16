# Convenciones de Desarrollo

Reglas y patrones que aplican transversalmente a todas las tasks. El agente debe incluir la informacion relevante de este fichero cuando rellene una task.

---

## 1. Test Factories

Las test factories crean entidades preconfiguradas para tests. Viven en `tests/Factory/` y se reutilizan en todos los niveles de test (unit, integration, E2E).

### Ubicacion y naming
```
tests/Factory/{Module}/{Name}Factory.php
```

Ejemplo: `tests/Factory/Envelope/EnvelopeFactory.php`

### Patron
- Clase `final` con metodos estaticos
- Cada metodo crea una entidad en un estado especifico
- Los metodos aceptan overrides opcionales para personalizar
- NUNCA persisten — eso lo hace el test si necesita BD

### Factories base del proyecto

Estas factories se crean en F1 (EP05) y se reutilizan en todo el proyecto:

| Factory | Metodos principales | Creada en |
|---------|-------------------|-----------|
| `TenantFactory` | `::create(overrides)`, `::createActive()`, `::createSuspended()` | S05.1 |
| `WorkspaceFactory` | `::create(tenant, overrides)`, `::createDefault(tenant)` | S05.1 |
| `UserFactory` | `::create(tenant, workspace, overrides)`, `::createAdmin()`, `::createSender()`, `::createViewer()` | S05.1 |

Estas se crean en F2:

| Factory | Metodos principales | Creada en |
|---------|-------------------|-----------|
| `EnvelopeFactory` | `::createDraft(overrides)`, `::createSent()`, `::createInProgress()`, `::createCompleted()`, `::createVoided()`, `::createSealOnly()` | S09.1 |
| `RecipientFactory` | `::createSigner(envelope, overrides)`, `::createApprover()`, `::createReviewer()`, `::createCc()` | S11.1 |
| `DocumentFactory` | `::create(envelope, overrides)`, `::createUploaded()` | S10.1 |
| `FieldFactory` | `::createSignature(document, recipient, overrides)`, `::createText()`, `::createCheckbox()` | S12.1 |
| `SigningGroupFactory` | `::create(tenant, overrides)`, `::createWithMembers(count)` | S11.4 |

Estas se crean en F3:

| Factory | Metodos principales | Creada en |
|---------|-------------------|-----------|
| `SigningSessionFactory` | `::create(recipient, overrides)`, `::createAuthPassed()`, `::createCompleted()` | S13.1 |
| `EvidencePacketFactory` | `::create(session, overrides)` | S16.1 |

### Como incluirlo en una task

Cuando una task de tests necesita factories, incluir en la seccion "Tests":

```
### Factories necesarias
- `TenantFactory::createActive()` — tenant de test
- `UserFactory::createSender(tenant, workspace)` — usuario con rol SENDER
- `EnvelopeFactory::createDraft(overrides)` — sobre en estado DRAFT

Si la factory no existe aun (pertenece a una story posterior), marcar:
[NEEDS CLARIFICATION: EnvelopeFactory se crea en S09.1 — esta task la necesita pero depende de ella]
```

---

## 2. Definition of Done

### DoD de Task

Una task esta COMPLETADA cuando:
- [ ] Todos los archivos listados en "Archivos a crear/modificar" estan creados
- [ ] Todos los tests listados en "Tests" estan escritos y pasan en verde
- [ ] El codigo sigue las reglas de `architecture-patterns.md` (hexagonal, DDD, CQRS)
- [ ] No hay warnings de PHPStan nivel 6+ (backend) ni errores de ESLint (frontend)
- [ ] Los tests se han ejecutado en AMBOS entornos si son de integracion (APP_ENV=saas y dedicated)

### DoD de Story

Una story esta COMPLETADA cuando:
- [ ] Todas sus tasks cumplen el DoD de Task
- [ ] Todos los criterios de aceptacion (AC-xx) estan verificados manualmente o por test
- [ ] No quedan `[NEEDS CLARIFICATION]` sin resolver en ninguno de sus ficheros
- [ ] Si la story tiene backend + frontend, ambos conectan end-to-end
- [ ] Si la story tiene endpoint API, se puede probar con curl/Postman contra el entorno de desarrollo
- [ ] Si la story emite domain events, los EventSubscribers relevantes estan implementados (o hay una task posterior que los cubre — documentado)

### DoD de Epic

Un epic esta COMPLETADO cuando:
- [ ] Todas sus stories cumplen el DoD de Story
- [ ] Las funcionalidades MVP listadas en el README del epic estan todas marcadas como completadas
- [ ] Smoke test del epic pasa (ver seccion 6)

---

## 3. Git Workflow

### Branch naming

```
{tipo}/{EPxx}-{Sxx.y}-{descripcion-kebab}
```

Tipos:
- `feature/` — nueva funcionalidad
- `fix/` — correccion de bug
- `infra/` — configuracion, Docker, CI
- `refactor/` — refactorizacion sin cambio funcional

Ejemplos:
```
feature/EP09-S09.1-crear-sobre-draft
feature/EP11-S11.2-motor-routing
fix/EP09-S09.1-validacion-nombre-vacio
infra/EP01-S01.1-docker-compose
```

Una branch por story. Si una story tiene muchas tasks, todas van en la misma branch con commits separados.

### Commit messages (Conventional Commits)

```
{tipo}({scope}): {descripcion imperativa en minusculas}

{cuerpo opcional — explica el por que, no el que}

Refs: {IDs de tasks}
```

Tipos:
- `feat` — nueva funcionalidad
- `fix` — correccion de bug
- `test` — solo tests (sin cambio funcional)
- `refactor` — refactorizacion
- `chore` — configuracion, dependencias
- `docs` — documentacion

Scope = nombre del modulo en minusculas: `envelope`, `signature`, `workflow`, `auth`, `notification`, etc.

Ejemplos:
```
feat(envelope): add Envelope entity with status state machine

Refs: T09.1.1

test(envelope): add unit tests for EnvelopeStatus transitions

Refs: T09.1.1

feat(envelope): add CreateEnvelopeCommand with PlanEnforcement

Handler verifies plan quota before creating the envelope.
Dispatches EnvelopeCreated domain event after persistence.

Refs: T09.1.3
```

### Workflow paso a paso

1. Crear branch desde `main`: `git checkout -b feature/EP09-S09.1-crear-sobre-draft`
2. Implementar tasks en orden (T09.1.1, T09.1.2, ...) con un commit por task
3. Ejecutar tests: `docker compose exec php bin/phpunit`
4. Push y crear PR con titulo: `feat(envelope): S09.1 — Crear sobre en DRAFT`
5. PR description: link a la story en el planning, lista de tasks completadas
6. Review + merge a main
7. Actualizar seguimiento: estado, fechas, PR/branch, commits

### PR template

```markdown
## Story
[S09.1 — Crear Sobre en DRAFT](link-relativo-al-planning)

## Tasks completadas
- [x] T09.1.1 — Entity Envelope + Value Objects
- [x] T09.1.2 — Repository + Doctrine Mapping
- [x] T09.1.3 — CreateEnvelopeCommand + Handler
- [x] T09.1.4 — Controller POST /v1/envelopes
- [x] T09.1.5 — Frontend: store + API call

## Tests
- X unit tests passing
- X integration tests passing
- X E2E tests passing

## Notas
{Decisiones tomadas, deuda tecnica, [NEEDS CLARIFICATION] encontrados}
```

---

## 4. Estrategia de Migraciones

### Naming
Doctrine genera nombres con timestamp automatico: `Version20260410143000.php`

### Protocolo para 2 devs en paralelo
1. Antes de crear una migracion, hacer `git pull` del branch principal
2. Generar la migracion: `php bin/console doctrine:migrations:diff`
3. Si hay conflicto de version (dos migraciones con el mismo timestamp):
   - El segundo dev borra su migracion
   - Hace `git pull` para obtener la del otro dev
   - Regenera su migracion (nuevo timestamp)
4. NUNCA editar una migracion ya mergeada al branch principal

### Migraciones manuales vs generadas
- Doctrine genera el DDL automaticamente desde los mappings XML
- Para RLS policies, ENUMs, funciones y triggers: migracion manual
- Las migraciones manuales llevan sufijo descriptivo: `Version20260410143000_add_rls_envelope.php`

### En el planning
Cada task que modifica el modelo de datos debe indicar:
- Si la migracion es auto-generada (Doctrine diff) o manual
- Si es manual, incluir el SQL exacto

---

## 4. Variables de Entorno por Modulo

### Variables compartidas (todos los modos)
```env
APP_ENV=saas|dedicated
APP_SECRET=<symfony-secret>
DATABASE_URL=postgresql://user:pass@host:5432/innasign
RABBITMQ_DSN=amqp://user:pass@host:5672
REDIS_URL=redis://host:6379
DSS_BASE_URL=http://eu-dss:8080/services/rest
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=<key>
S3_SECRET_KEY=<secret>
S3_REGION=eu-west-1
S3_BUCKET_ORIGINALS=innasign-originals
S3_BUCKET_SIGNED=innasign-signed
S3_BUCKET_AUDIT=innasign-audit-trails
S3_BUCKET_BIOMETRICS=innasign-biometrics
S3_BUCKET_TEMP=innasign-temp
JWT_SECRET_KEY=%kernel.project_dir%/config/jwt/private.pem
JWT_PUBLIC_KEY=%kernel.project_dir%/config/jwt/public.pem
JWT_PASSPHRASE=<passphrase>
JWT_TTL=900
REFRESH_TOKEN_TTL=604800
SEAL_CERTIFICATE_PATH=/etc/innasign/seal.p12
SEAL_CERTIFICATE_PASSWORD=<password>
TSA_URL=http://tsa.fnmt.es/tsa/tss
TRUSTED_LISTS_CACHE_DIR=/var/cache/dss/tl
```

### Variables solo SaaS
```env
SENDGRID_API_KEY=<key>
SENDGRID_FROM_EMAIL=noreply@innasign.com
SENDGRID_FROM_NAME=InnaSign
TWILIO_ACCOUNT_SID=<sid>
TWILIO_AUTH_TOKEN=<token>
TWILIO_FROM_NUMBER=+34600000000
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Variables solo Dedicated
```env
SMTP_DSN=smtp://user:pass@smtp.cliente.com:587
SMS_PROVIDER_DSN=twilio://sid:token@default?from=+34...
TENANT_ID=<uuid-fijo-del-tenant>
```

### En el planning
Cada task de infraestructura (Docker, config) debe listar las variables de entorno que necesita. Las tasks de codigo no necesitan listarlas (ya estan inyectadas por Symfony DI).

---

## 5. Contrato Frontend-Backend (TypeScript Types)

El frontend debe tener tipos TypeScript que coincidan con los Response DTOs del backend. Esto se gestiona manualmente (no hay generacion automatica en MVP).

### Ubicacion
```
apps/dashboard/types/api/{module}.ts
apps/signer/types/api/{module}.ts
```

### Patron
```typescript
// apps/dashboard/types/api/envelope.ts
export interface EnvelopeResponse {
  id: string
  name: string
  status: EnvelopeStatus
  workflow_type: WorkflowType
  locale: string
  expires_in_days: number
  reminder_frequency_days: number
  message: string | null
  documents_count: number
  recipients_count: number
  created_by: string
  created_at: string  // ISO 8601
  updated_at: string  // ISO 8601
}

export type EnvelopeStatus = 'DRAFT' | 'SENT' | 'IN_PROGRESS' | 'READY_TO_SEAL' | 'SEALING' | 'SEALING_FAILED' | 'COMPLETED' | 'VOIDED' | 'DECLINED' | 'EXPIRED' | 'CORRECTING'

export type WorkflowType = 'STANDARD' | 'SEAL_ONLY'

export interface CreateEnvelopeRequest {
  name: string
  locale?: string
  expires_in_days?: number
  reminder_frequency_days?: number
  message?: string
  workflow_type?: WorkflowType
}
```

### En el planning
Cada task de tipo Frontend que hace API calls debe incluir en su detalle tecnico:
- El tipo TypeScript del request
- El tipo TypeScript del response
- El archivo donde van: `apps/{app}/types/api/{module}.ts`

Cada task de tipo Backend que crea un endpoint debe incluir en su detalle tecnico:
- El Response DTO de PHP con todos sus campos y tipos
- Una nota recordando que el frontend necesita el tipo TS equivalente

---

## 6. Smoke Tests por Fase

Tras completar una fase entera, verificar que todo funciona junto con estos tests manuales o scripts:

### F0 — Infraestructura
- [ ] `docker compose up` levanta todos los servicios sin errores
- [ ] `php bin/console` funciona dentro del contenedor PHP
- [ ] PostgreSQL acepta conexiones y las tablas base existen
- [ ] RabbitMQ Management UI accesible en http://localhost:15672
- [ ] MinIO accesible y buckets creados
- [ ] EU DSS responde en su endpoint health
- [ ] Redis acepta conexiones

### F1 — Auth y Tenancy
- [ ] POST /v1/auth/login con credenciales validas devuelve JWT
- [ ] POST /v1/auth/refresh con refresh token valido devuelve nuevo JWT
- [ ] Request sin JWT a endpoint protegido devuelve 401
- [ ] Request con JWT de tenant A no ve datos de tenant B (RLS)
- [ ] Rate limiter responde con 429 tras exceder el limite

### F2 — Core Envelope
- [ ] Crear sobre DRAFT via API
- [ ] Subir PDF al sobre
- [ ] Anadir recipients (SIGNER, REVIEWER)
- [ ] Posicionar campos en el PDF
- [ ] Enviar sobre (DRAFT -> SENT)
- [ ] Verificar que EnvelopeSent event se emitio

### F3 — Signer Workspace
- [ ] Acceder al Signer Workspace con token valido
- [ ] Completar autenticacion OTP
- [ ] Ver PDF con campos interactivos
- [ ] Firmar (canvas biometrico)
- [ ] Completar sesion de firma
- [ ] Verificar que DocumentSigned event se emitio

### F4 — Sellado y Cierre
- [ ] Verificar que el worker de sellado procesa el sobre
- [ ] PDF sellado con PAdES B-LT almacenado en S3
- [ ] Audit Trail PDF generado
- [ ] Email de completado enviado (o en cola)
- [ ] Webhook de envelope.completed disparado (o en cola)

### F5 — Dashboard y Polish
- [ ] Home del Dashboard muestra metricas
- [ ] Listado de sobres con filtros funciona
- [ ] Detalle de sobre con tabs funciona
- [ ] Crear template y enviar desde template
- [ ] Crear webhook subscription y recibir eventos
- [ ] SDK embebido carga en iFrame
- [ ] White-label aplica logo y colores custom

### En el planning
El README de cada fase debe incluir la seccion de smoke tests correspondiente.
