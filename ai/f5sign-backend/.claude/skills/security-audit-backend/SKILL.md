---
name: security-audit-backend
description: 'Checks de seguridad específicos del stack backend (PHP/Symfony). Complementa a security-audit-core con: inyección SQL en PHP (Doctrine/PDO), uso correcto de Symfony asserts, auth middleware Symfony, rate limiting, idempotency, headers de seguridad, criptografía genérica (bcrypt/argon2, hash_equals, random_bytes). Invocada por security-audit-core. Úsalo con /security-audit-backend T{id}. Activar con "security backend", "audit PHP", "check Symfony security".'
---

# Security Audit Backend

Checks específicos del stack PHP/Symfony. Normalmente invocada por `security-audit-core`; directamente invocable para debugging.

## Invocación

```
/security-audit-backend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/doctrine-guard.report.md` (si existe)
- `.md` de la tarea

## Outputs

- `var/task-runner/T{id}/security-audit-backend.report.md`
- JSON:
  ```json
  {"status":"pass|fail|warn","summary":"...","issues":[...]}
  ```

## Ejecución

Aplicar los checks sobre ficheros del diff. Saltar categorías cuyo scope no aparece.

### Inyección (PHP)
- [ ] No concatenación de strings en queries SQL: usar DQL, QueryBuilder o prepared statements
  - Grep: `"SELECT .* $" . $var`, `->getResult()` con strings construidos, PDO prepare incorrecto
- [ ] No `shell_exec`/`exec`/`system`/`passthru`/backtick operator con input de usuario
- [ ] No `eval()` ni `include`/`require` dinámicos con input de usuario
- [ ] LDAP/XPath queries parametrizadas si aplica
- [ ] Serialización: no `unserialize()` sobre input externo (RCE)

### Symfony Request/Response
- [ ] Controllers usan type-hints de Request para parse (no `$_GET`, `$_POST`, `$_REQUEST` directos)
- [ ] Response headers: `Content-Type` explícito, no autodetect
- [ ] DTOs request con constraints Symfony `#[Assert\*]` en cada propiedad
  - `#[Assert\NotBlank]`, `#[Assert\Length(max=...)]`, `#[Assert\Email]`, `#[Assert\Choice]`, etc.
- [ ] Strings libres con `#[Assert\Length(max=...)]` (evitar DoS por payload gigante)
- [ ] Whitelists con `#[Assert\Choice]` en enums/choices
- [ ] File uploads: `#[Assert\File]` con `mimeTypes`, `maxSize`, `extensions`

### Auth middleware (Symfony Security)
- [ ] Endpoints protegidos tienen `#[IsGranted(...)]` o equivalente
- [ ] Firewalls en `config/packages/security.yaml` cubren los paths nuevos
- [ ] Object-level authorization con Voters de Symfony (no solo roles globales)
- [ ] Tests E2E verifican 401/403 en intentos no autorizados

### Rate limiting
- [ ] Endpoints sensibles (login, reset password, firma, envío masivo) tienen limiter configurado en `config/packages/rate_limiter.yaml` y aplicado al controller

### Idempotencia y CSRF
- [ ] Endpoints POST/PUT/PATCH/DELETE con efectos irreversibles: idempotency key (header `Idempotency-Key`) o CSRF token si es form tradicional
- [ ] Operaciones críticas: doble check o confirmación explícita en flow

### Criptografía genérica PHP
- [ ] Password hashing: `password_hash(..., PASSWORD_BCRYPT)` o `PASSWORD_ARGON2ID`. NO MD5, NO SHA1 para passwords
- [ ] Verificación: `password_verify()`, no comparación directa
- [ ] No cifrado con claves hardcoded; usar `sodium_*` o `openssl_*` con claves de configuración
- [ ] Random: `random_bytes()` / `random_int()`. NO `mt_rand()`, NO `rand()` en contextos de seguridad
- [ ] Comparación timing-safe: `hash_equals()`, no `===` ni `==` para hashes/tokens

### Doctrine / Repositorios
- [ ] Queries con parámetros via `setParameter()`, no interpolación
- [ ] Si hay Native SQL (`$em->getConnection()->executeQuery`), parámetros vinculados (prepared)
- [ ] No concatenación de input en DQL

### Headers de seguridad
Si se añaden endpoints públicos o cambia CORS:
- [ ] CORS en `nelmio_cors.yaml`: no `allow_origin: ['*']` si el endpoint es privado
- [ ] Si el proyecto usa CSP: no introduce inline scripts en responses

### Tests de seguridad (si la tarea es sensible)
- [ ] Si la tarea tiene tag `tenancy`: test E2E de cross-tenant presente y pasa (ya verificado por task-validate, aquí se confirma que el AC lo exige)
- [ ] Si tag `critical-path` o es login/firma: test de rate limit presente (llamar N veces y esperar 429)

## Gravedad

- **FAIL:**
  - SQL injection / command injection / path traversal / RCE vía unserialize
  - Endpoint sin auth cuando AC lo exige
  - Crypto débil en contextos de seguridad (MD5/SHA1 para password, clave hardcoded)
  - Object-level authz ausente cuando AC lo requiere
- **WARN:**
  - Rate limit ausente en endpoint que probablemente lo necesita
  - Mensaje de error verbose
  - Header de seguridad no explícito

## Report

```markdown
# security-audit-backend — T{id}

**Status:** {PASS|FAIL|WARN}
**Issues:** {B} bloqueantes, {W} warnings

## Bloqueantes
- [{categoría}] {fichero:línea} {mensaje}

## Warnings
- [{categoría}] {mensaje}
```

## JSON de retorno

```json
{"status":"fail","summary":"1 SQL injection + 1 endpoint sin auth","issues":[{"severity":"fail","category":"sqli","file":"src/...","message":"concatenación de strings en DQL línea 45"}]}
```

## Qué NO hace

- No hace los checks genéricos (secretos, PII, dependencias genéricas, authz conceptual) — eso es `security-audit-core`
- No valida compliance eIDAS — eso es `eidas-compliance`
- No valida persistencia estructural (RLS policies, índices) — eso es `doctrine-guard`
- No valida contratos API — eso es `contract-check-backend`
- No ejecuta pentesting

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/backend/05 - Security Audit Backend.md`
- security-audit-core: `.claude/skills/security-audit-core/SKILL.md`
