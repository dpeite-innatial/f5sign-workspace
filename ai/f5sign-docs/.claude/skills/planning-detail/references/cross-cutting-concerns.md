# Cross-cutting concerns

Estos patrones aparecen en MUCHAS stories. Cuando una story los involucra, incluye esta informacion en su "Contexto funcional". No repitas la explicacion completa — incluye un resumen de 2-3 lineas y los datos especificos de la story.

---

## PlanEnforcement

Todas las stories que crean recursos limitados (envelopes, templates, signing groups, API keys) deben verificar el plan del tenant antes de ejecutar.

**Como incluirlo en una story:**
```
### PlanEnforcement
Esta operacion verifica la cuota `{METRIC_NAME}` del plan del tenant via `PlanEnforcerInterface::can{Action}(tenantId)`.
- SaaS: verifica contra plan_limit. Si excede, lanza PlanLimitExceededException (HTTP 402 con upgrade_url).
- Dedicated: UnlimitedPlanEnforcer siempre retorna true.
Limites: Free={n}, Starter={n}, Business={n}, Enterprise=ilimitado.
```

**Limites por plan (de Modelo de Monetizacion):**

| Recurso | Free | Starter | Business | Enterprise |
|---------|------|---------|----------|------------|
| Envelopes/mes | 5 | 50/usuario | 200/usuario | Ilimitado |
| Templates | 3 | 10 | Ilimitados | Ilimitados |
| Signing Groups | 0 | 0 | 10 (max 10 miembros) | 20 (max 20 miembros) |
| API Keys | 1 (test only) | 2 | 5 | Ilimitados |
| Webhook subscriptions | 1 | 3 | 10 | Ilimitados |
| SMS OTP | 0 | Incluidos | Incluidos | Incluidos |
| Workspaces | 1 | 1 | 5 | Ilimitados |

---

## Multi-tenancy y RLS

Todas las queries y commands pasan por RLS automaticamente. No hay que filtrar manualmente por tenant_id en el codigo — PostgreSQL lo hace via la policy.

**Como incluirlo en una story:**
```
### Multi-tenancy
- RLS activo: todas las queries se filtran automaticamente por tenant_id.
- SetTenantIdMiddleware establece `app.current_tenant_id` en la conexion DB antes de cada command.
- En Dedicated: tenant_id es un UUID fijo configurado por variable de entorno.
```

---

## SaaS vs Dedicated

Algunas features se comportan distinto segun el modo. El codigo usa `DEPLOYMENT_MODE` env var y entornos Symfony separados.

**Como incluirlo en una story (solo si hay diferencia real):**
```
### SaaS vs Dedicated
- SaaS: {descripcion del comportamiento SaaS}
- Dedicated: {descripcion del comportamiento Dedicated}
- Implementacion: {como se diferencia — bundle condicional, PlanEnforcerInterface, etc.}
```

**Cosas que NO existen en Dedicated:**
- Billing, Stripe, Dunning
- Self-service signup
- Planes y limites (todo ilimitado)
- Multi-tenant admin

**Cosas que se configuran distinto en Dedicated:**
- SMTP: variable `SMTP_DSN` del cliente (no SendGrid)
- SMS: variable `SMS_PROVIDER_DSN` del cliente (no Twilio)
- e-Seal certificate: variable `SEAL_CERTIFICATE_PATH`
- TSA: variable `TSA_URL`
- S3: MinIO local en vez de AWS S3

---

## i18n

El MVP soporta ES y EN. Dashboard solo en ES. Signer Workspace y emails en ES + EN.

**Como incluirlo en una story (solo si involucra texto visible):**
```
### i18n
- Backend: usar Symfony Translation con claves en ingles (`envelope.created_successfully`).
- Frontend: usar `$t('key')` de vue-i18n. Toda cadena visible debe pasar por i18n.
- Audit Trail: bilingue (locale del sobre + ingles). Si el locale es ingles, solo ingles.
- Emails: templates por idioma ({locale}/sign_invitation.html.twig).
- API: errores siempre en ingles machine-readable (VALIDATION_ERROR, PLAN_LIMIT_EXCEEDED).
```

---

## Testing patterns

Cada task debe incluir tests. Estos son los patrones de testing de la arquitectura:

**Unit tests (Domain):**
- Solo logica de negocio, sin framework, sin BD
- Archivo: `tests/Unit/{Module}/Domain/{Entity|ValueObject}/{Name}Test.php`
- Extiende `PHPUnit\Framework\TestCase`
- Mock de interfaces del dominio si necesario

**Integration tests (Application):**
- Handler completo contra BD real (PostgreSQL en Docker)
- Archivo: `tests/Integration/{Module}/Application/Command/{UseCase}/{Handler}Test.php`
- Extiende `IntegrationTestCase` (custom base que levanta BD)
- Se ejecuta en AMBOS entornos: `APP_ENV=saas` y `APP_ENV=dedicated`

**E2E tests (Infrastructure/HTTP):**
- Request HTTP completa
- Archivo: `tests/E2E/{Module}/Infrastructure/Http/Controller/{Controller}Test.php`
- Extiende `ApiTestCase` (custom base con HTTP client + JWT)
- Verifica status code, response body, headers

---

## Error responses (RFC 7807)

Todos los errores siguen el formato Problem Details:

```json
{
  "type": "https://api.innasign.com/errors/PLAN_LIMIT_EXCEEDED",
  "title": "Plan limit exceeded",
  "status": 402,
  "detail": "You have reached your monthly envelope limit (5/5). Upgrade your plan to create more.",
  "instance": "/v1/envelopes",
  "upgrade_url": "https://app.innasign.com/billing/upgrade"
}
```

Mapeo estandar de excepciones de dominio a HTTP:
- `EntityNotFoundException` → 404
- `InvalidTransitionException` → 409
- `PlanLimitExceededException` → 402
- `InsufficientPermissionsException` → 403
- `DomainValidationException` → 422
- Symfony Validator violations → 422

Esto se gestiona en `ExceptionListener`, no en los controllers.
