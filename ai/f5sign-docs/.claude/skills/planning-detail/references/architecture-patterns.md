# Patrones de Arquitectura — Reglas Estrictas

Estas reglas gobiernan COMO se estructura el codigo en InnaSign. Cuando rellenes el detalle tecnico de una task, todo lo que escribas debe cumplir estas reglas. Si una task viola alguna regla, esta mal definida.

Fuente de verdad: `Arquitectura/Patrones de Código y Convenciones.md`

---

## 1. Arquitectura Hexagonal (Ports & Adapters)

### Regla fundamental: las dependencias solo apuntan hacia el dominio

```
Infrastructure --> Application --> Domain
     |                 |             |
     | puede           | puede       | NO puede
     | importar        | importar    | importar
     | todo            | Domain      | NADA externo
     v                 v             v
  Symfony           Domain        Solo PHP puro
  Doctrine          Shared        y Shared/Domain
  HTTP              Domain
  RabbitMQ
```

### Reglas estrictas por capa

**Domain (src/{Module}/Domain/):**
- NUNCA importa Symfony, Doctrine, HTTP, ni ningun framework
- NUNCA importa Application ni Infrastructure de ningun modulo
- Solo puede importar: PHP nativo, su propio Domain, y `Shared/Domain/`
- Contiene: Entity, ValueObject, Event, Exception, Repository (interface), Service, PublicApi

**Application (src/{Module}/Application/):**
- NUNCA importa Infrastructure de ningun modulo
- Solo puede importar: su propio Domain, `Shared/Domain/`, `Shared/Application/`
- Contiene: Command/{UseCase}/, Query/DTO/, EventSubscriber/

**Infrastructure (src/{Module}/Infrastructure/):**
- Puede importar todo: Domain, Application, Symfony, Doctrine, HTTP
- Es la unica capa que conoce los frameworks y librerias externas
- Contiene: Persistence/ (repos Doctrine + Mapping/), Http/Controller/, integraciones externas

### Aplicacion a tasks

Cuando definas una task de tipo "Entity + Value Objects":
- Todos los archivos van en `src/{Module}/Domain/`
- Ningun import de Symfony, Doctrine, ni Infrastructure
- Las interfaces de repositorio van en Domain, las implementaciones en Infrastructure

Cuando definas una task de tipo "Controller + API":
- El controller esta en Infrastructure, NUNCA en Domain ni Application
- El controller solo inyecta CommandBusInterface y QueryService — nada mas
- La logica de negocio NUNCA va en el controller

---

## 2. DDD (Domain-Driven Design)

### Aggregate Roots

Un Aggregate Root es la unica puerta de entrada a un cluster de entidades. En InnaSign:

| Aggregate Root | Entidades subordinadas | Bounded Context |
|---------------|----------------------|-----------------|
| Envelope | Document, Recipient, Field | Envelope |
| SigningSession | — | Signature |
| SignatureExecution | — | Signature |
| SigningGroup | SigningGroupMember | SigningGroup |
| Template | TemplateRecipient, TemplateField | Template |
| User | — | User |
| Tenant | — | TenantManagement |
| Workspace | — | Workspace |
| AuditEvent | — | Audit |
| WebhookSubscription | WebhookDelivery | API |
| ApiKey | — | API |
| Contact | — | Contact |
| LegalDocument | — | Legal |
| ShareLink | — | Document |
| Notification | — | Notification |

**Reglas estrictas:**
- Solo se modifica una entidad subordinada A TRAVES del aggregate root
- Ejemplo: para anadir un Recipient, se llama `Envelope::addRecipient()`, NUNCA se crea un Recipient suelto
- Los repositorios solo existen para Aggregate Roots, NUNCA para entidades subordinadas
- Ejemplo: existe `EnvelopeRepositoryInterface`, NO existe `RecipientRepositoryInterface`
- Al persistir el Aggregate Root, Doctrine persiste en cascada las entidades subordinadas

### Value Objects

**Reglas estrictas:**
- `final readonly` — inmutables
- Constructor privado — solo se crean via factory methods estaticos
- Ejemplo: `Email::fromString('user@example.com')` — nunca `new Email('user@example.com')`
- Validan en el constructor — si el valor es invalido, lanza excepcion de dominio
- Dos VOs con el mismo valor son iguales (`equals()` method)
- Los Enums de PHP son VOs especiales para conjuntos finitos (EnvelopeStatus, RecipientRole, etc.)

### Domain Events

**Reglas estrictas:**
- `final readonly` — inmutables
- Nombre en pasado: `EnvelopeCreated`, `DocumentSigned`, `RecipientDeclined`
- Se registran en la entidad con `$this->record(new EnvelopeCreated(...))` durante la operacion
- Se despachan DESPUES de persistir, NUNCA antes
- El handler los expone via `$aggregate->pullEvents()` y los envia al EventBus
- Un domain event NUNCA contiene entidades enteras — solo IDs y datos primitivos
- Payload: solo strings, ints, floats, bools, DateTimeImmutable

### Comunicacion entre modulos

**Reglas estrictas:**
- Un modulo NUNCA importa internals de otro modulo
- Solo puede usar la `PublicApi/` del otro modulo (interfaces en Domain/PublicApi/)
- O escuchar sus Domain Events (via EventSubscriber en Application/)
- Ejemplo: Notification no importa Envelope internals. Escucha `EnvelopeSent` event y actua.
- Ejemplo: Workflow necesita saber si un envelope existe → usa `EnvelopeQueryInterface` (PublicApi)

---

## 3. TDD (Test-Driven Development)

### Regla fundamental: el test se escribe ANTES que el codigo

Esto afecta al orden de trabajo DENTRO de cada task:

1. Escribir el test que define el comportamiento esperado
2. Ejecutar el test — debe FALLAR (red)
3. Escribir el codigo minimo para que el test pase (green)
4. Refactorizar si necesario (refactor)

### Aplicacion a tasks

Cuando definas una task, los tests NO son un "paso final". Son el PRIMER paso. La descripcion de la task debe reflejar esto:

```
## Orden de implementacion
1. Crear archivo de test `tests/Unit/.../EnvelopeTest.php`
2. Escribir tests: testCreateDraft, testNameTooLong, testInvalidTransition
3. Ejecutar tests — deben fallar (clases no existen aun)
4. Crear `src/.../Entity/Envelope.php` con el codigo minimo
5. Ejecutar tests — deben pasar
6. Refactorizar si necesario
```

### Tipos de test por capa (recordatorio)

| Capa | Tipo test | Base class | BD? | Framework? |
|------|-----------|-----------|-----|-----------|
| Domain | Unit | `TestCase` | No | No |
| Application | Integration | `IntegrationTestCase` | Si (PostgreSQL Docker) | Si (Symfony kernel) |
| Infrastructure/Http | E2E | `ApiTestCase` | Si | Si (HTTP client) |

**Regla de entornos:** Los tests de Integration se ejecutan en AMBOS entornos (`APP_ENV=saas` y `APP_ENV=dedicated`) para verificar que `PlanEnforcerInterface` y bundles condicionales funcionan en los dos modos.

### Que se testea en cada tipo

**Unit (Domain):**
- Creacion de entidades con datos validos
- Validaciones de Value Objects (casos validos e invalidos)
- Transiciones de estado (validas e invalidas)
- Emision de domain events (que se registran correctamente)
- Invariantes del aggregate (reglas de negocio)

**Integration (Application):**
- Handler completo: command → handler → persistencia → evento
- PlanEnforcement: que el handler rechaza cuando la cuota esta agotada
- Transaccionalidad: que un fallo en medio hace rollback
- Que los datos persisten correctamente en PostgreSQL

**E2E (Infrastructure/Http):**
- Request HTTP completa con JWT valido → response correcta
- Request sin auth → 401
- Request con rol insuficiente → 403
- Request con datos invalidos → 422
- Request con cuota agotada → 402

---

## 4. CQRS (Command Query Responsibility Segregation)

### Commands (escritura)

**Reglas estrictas:**
- Pasan por el Command Bus (Symfony Messenger sync)
- `final readonly class {Verb}{Noun}Command` — DTO inmutable
- SIEMPRE incluyen `tenantId` como propiedad
- Validaciones con `#[Assert\*]` de Symfony — el middleware `validation` las ejecuta
- Un command = un handler = un caso de uso
- El handler tiene un unico metodo: `__invoke({Verb}{Noun}Command $cmd)`

**Middleware del Command Bus (en orden):**
1. `SetTenantIdMiddleware` — establece `app.current_tenant_id` en PostgreSQL
2. `validation` — ejecuta constraints Symfony
3. `doctrine_transaction` — envuelve todo en una transaccion
4. `LogCommandMiddleware` — logging

**Orden de ejecucion dentro del handler:**
1. Verificar limites del plan (`planEnforcer->canXxx()`)
2. Cargar aggregate del repositorio (si aplica)
3. Ejecutar logica de dominio en el aggregate
4. Persistir (`repo->save($aggregate)`)
5. Despachar domain events (`foreach $aggregate->pullEvents() as $event`)

### Queries (lectura)

**Reglas estrictas:**
- NO pasan por el Command Bus — se llaman directamente desde el controller
- Viven en `{Module}/Application/Query/{Module}QueryService.php`
- Retornan DTOs (`{Noun}Response`), NUNCA entidades del dominio
- Pueden usar SQL optimizado (JOINs, indices) sin cargar aggregates completos
- Son de solo lectura — NUNCA modifican estado

### Sync vs Async

**Regla:** si la operacion tarda mas de 200ms o depende de un servicio externo → async.

| Tipo | Transport | Ejemplo |
|------|-----------|---------|
| Sync | `sync://` | CreateEnvelope, VoidEnvelope, Login |
| Async (alta prioridad) | RabbitMQ `async_priority_high` | SealDocument, EnvelopeCompleted |
| Async (normal) | RabbitMQ `async` | SendEmail, DeliverWebhook, GenerateAuditTrail |

---

## 5. Reglas adicionales criticas

### Doctrine Mapping: XML, no atributos

Los mappings de Doctrine son ficheros XML, NO atributos PHP:
- Archivo: `src/{Module}/Infrastructure/Persistence/Mapping/{Entity}.orm.xml`
- Razon: mantener el Domain libre de dependencias de framework

### Bundles condicionales (SaaS vs Dedicated)

Los modulos solo-SaaS se registran como bundles condicionales:
- `src/Module/Billing/BillingBundle.php` — solo se carga si `DEPLOYMENT_MODE=saas`
- Config en `config/packages/saas/billing.yaml` — solo se lee en entorno saas
- Rutas en `config/routes/saas/billing.yaml` — en Dedicated, 404 natural

### PlanEnforcerInterface

```
interface PlanEnforcerInterface {
    canCreateEnvelope(string $tenantId): bool;
    canCreateTemplate(string $tenantId): bool;
    canCreateApiKey(string $tenantId): bool;
    // etc.
}

// SaaS: verifica contra plan_limit en BD
class SaaSPlanEnforcer implements PlanEnforcerInterface { ... }

// Dedicated: siempre true
class UnlimitedPlanEnforcer implements PlanEnforcerInterface {
    public function canCreateEnvelope(string $tenantId): bool { return true; }
}
```

Inyectado por entorno Symfony: `services_saas.yaml` registra `SaaSPlanEnforcer`, `services_dedicated.yaml` registra `UnlimitedPlanEnforcer`.

### Error Handling

- Las excepciones de dominio se lanzan en el Domain layer
- Un `ExceptionListener` global (Infrastructure) las traduce a HTTP responses RFC 7807
- Los controllers NUNCA hacen try/catch de excepciones de dominio
- Mapeo estandar: `EntityNotFoundException` → 404, `InvalidTransitionException` → 409, `PlanLimitExceededException` → 402, `ValidationException` → 422
