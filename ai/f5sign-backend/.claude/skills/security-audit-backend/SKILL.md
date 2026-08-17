---
name: security-audit-backend
description: 'Checks de seguridad específicos del stack backend (PHP/Symfony). Complementa a security-audit-core con: inyección en SQL vía DBAL (no hay ORM), asserts de Symfony, el seam de autenticación real de este repo (Identity & Access con ruta que declara credencial, NO SecurityBundle: no está registrado), idempotencia por identidad derivada, CORS vía CorsListener propio, y la criptografía que sí existe aquí (credencial emitida, token de firma, cifrado de campo para PII). Nombra lo que NO está instalado —rate limiter— en vez de reportarlo endpoint por endpoint. Invocada por security-audit-core. Úsalo con /security-audit-backend T{id}. Activar con "security backend", "audit PHP", "check Symfony security".'
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

### Autenticación — **no hay SecurityBundle**, el seam es Identity & Access

⛔ `symfony/security-bundle` y `lexik/jwt-authentication-bundle` **están en `composer.json` pero NO
registrados** en `config/bundles.php`. No existe `config/packages/security.yaml`, ni firewalls, ni Voters,
ni `#[IsGranted]`. Buscar cualquiera de esas cosas es buscar algo que este repo no tiene, y "no lo encontré"
se leería como hallazgo cuando es la arquitectura.

Lo que sí hay (ADR-0044…ADR-0048), y es lo que se comprueba:

- [ ] **La ruta declara su tipo de credencial**, resuelto en `kernel.controller`, **sin fallback**
      (ADR-0048: una credencial por ruta). Una ruta nueva sin declaración no queda "abierta por defecto":
      queda mal → `fail`, categoría `undeclared-auth`.
- [ ] **El caso de uso recibe un principal ya verificado**; no deriva identidad de cabeceras (ADR-0044).
      ⚠ El precedente es literal: antes de identity-access el tenant salía de un `X-Tenant-Id` sin verificar
      y el actor de un `X-Acting-User-Id` igual — *"no un actor débilmente atestiguado: una ficción"*.
      Cualquier lectura nueva de cabecera de identidad → `fail`.
- [ ] **`F5Sign-Declared-Subject`** en rutas de máquina: obligatoria (ADR-0047), publicada en el spec y
      permitida en el preflight CORS — que aquí lo sirve
      [`CorsListener`](../../../src/F5Sign/Foundation/Http/CorsListener.php), **no** `nelmio_cors.yaml`,
      que no existe.
- [ ] **El token de firmante** (`SigningTokenCodec` / `SigningTokenListener`) no se amplía de alcance: es
      por destinatario y por sobre. ⚠ El fallo que cerró identity-access (BL-38): un destinatario con token
      válido **replicaba su claim de tenant verdadero en un canal que no verificaba nada** y leía documentos
      que le habían sido denegados. Cualquier ruta que acepte del cliente un claim de tenant → `fail`,
      categoría `unverified-tenant-claim`.
- [ ] Tests que verifiquen 401/403 en el intento no autorizado, y **un cross-tenant que espere 404/403**.

### Rate limiting — **no está instalado**, así que no es un check por endpoint

⚠ `symfony/rate-limiter` **no es dependencia de este repo** y `config/packages/rate_limiter.yaml` no
existe. No marcar endpoint por endpoint que "le falta el limitador": **falta la capacidad entera**, y
repetirlo por cada ruta entierra el hecho en ruido.

- [ ] Si el diff añade una superficie que lo necesita (login, OTP, reenvío, firma, envío masivo): **un solo
      `warn`** nombrando la ausencia del componente y qué lo espera — TASK-022 (en
      `docs/two-gate-signer-auth`) lo declara como uno de sus dos prerequisitos inexistentes.
- [ ] No proponer `#[RateLimit]` ni crear un `rate_limiter.yaml`: instalar un componente es una decisión, y
      va por el gate de `implement-backend` Paso 2b.

### Idempotencia — identidad derivada, no una cabecera

No hay formularios ni Twig, así que **CSRF no aplica**: la API se consume con credencial, no con cookie de
sesión. Y la idempotencia de este repo **no** es un header `Idempotency-Key`: son las tres capas de
ADR-0014, la primera de las cuales es **identidad derivada** (el id se mina de forma determinista, así que
el reintento colisiona en vez de duplicar).

- [ ] Una operación con efecto irreversible que se pueda reintentar tiene su id derivado, o dice por qué no.
- [ ] La convergencia se comprueba de verdad: el segundo intento **no** duplica. El patrón vivo es
      `if (!$delivery->isPending()) return;`.

### Criptografía — la genérica y la que este repo ya tiene

Genérico:

- [ ] Random: `random_bytes()` / `random_int()`. Nunca `mt_rand()`/`rand()` en contexto de seguridad.
- [ ] Comparación timing-safe: `hash_equals()`, jamás `===`/`==` sobre hashes o tokens.
- [ ] Sin claves embebidas en el código: salen de configuración.
- [ ] Si algún día hay contraseñas: `password_hash` con ARGON2ID/BCRYPT y `password_verify`. **Hoy no hay
      login por contraseña**, así que no reportar su ausencia como hallazgo.

Y lo que sí existe aquí, que es donde de verdad hay que mirar:

- [ ] **Credencial emitida** ([`IssuedCredential`](../../../src/F5Sign/Foundation/Credential/IssuedCredential.php),
      ADR-0045): una gramática publicada para todo secreto que F5Sign entrega. Un secreto nuevo con formato
      propio → `fail`, categoría `credential-format`.
- [ ] **Token de firma** (`SigningTokenCodec`): verificación con `hash_equals`, y **el TTL vive en el caso de
      uso que lo mina**, no en la copia. ⚑ Una promesa de retención en el copy sobre un token de 7 días fue
      un fallo real ya corregido; no reintroducirla.
- [ ] **PII cifrada en reposo** ([`FieldCipher`](../../../src/F5Sign/Foundation/Crypto/FieldCipher.php),
      ADR-0032/ADR-0033): un campo nuevo con PII se clasifica y se cifra. ⚠ **El check es el conjunto de
      claves cerrado**, no un spot-check: PHPStan nivel 9 rechaza una clave que falta y **acepta una de
      más**, así que un "aquí no hay PII" pasa por alto el campo nuevo. Enumerar y afirmar el conjunto.
- [ ] **El event log es Path B**: PII en claro **fuera** del log; el payload es pseudónimo (ADR-0031). Un
      payload nuevo con PII en claro → `fail`, categoría `pii-in-log`.
- [ ] `FIELD_ENCRYPTION_SECRET` no se commitea con valor, y su consumidor rechaza menos de 32 bytes: es la
      única variable del patrón "presente y vacía" (regla 4 del repo).

### Persistencia — DBAL, no ORM

El ORM se retiró (ADR-0018): no hay DQL, ni QueryBuilder de ORM, ni `$em`. Buscarlos es buscar lo que no
existe.

- [ ] SQL con **parámetros vinculados** en `executeQuery`/`executeStatement`; cero interpolación de input.
- [ ] Identificadores que vengan de input (nombres de tabla/columna, `ORDER BY`) **no** se interpolan: se
      mapean contra una lista cerrada en código.
- [ ] La lectura pasa por el `Row` de Foundation en vez de indexar arrays a pelo, para que un tipo
      inesperado falle donde se lee y no tres capas más allá.

### Headers y CORS — un listener propio, no `nelmio_cors.yaml`

- [ ] CORS lo sirve [`CorsListener`](../../../src/F5Sign/Foundation/Http/CorsListener.php); **no existe
      `nelmio_cors.yaml`**. Revisar el listener: sin `*` de origen para rutas privadas, y **cada cabecera
      obligatoria de la API permitida en el preflight** — el fallo real fue rechazar
      `F5Sign-Declared-Subject`, que es obligatoria en toda ruta de máquina, dejando a los clientes de
      navegador sin poder mandarla.
- [ ] Errores al usuario sin stack traces ni rutas internas: eso lo centraliza
      [`ApiExceptionListener`](../../../src/F5Sign/Foundation/Http/ApiExceptionListener.php) con el mapeo de
      ADR-0029; una excepción nueva que se escape del mapeo filtra detalle → `fail`.

### Tests de seguridad, según lo que toca el diff (no según tags)

- [ ] Si toca RLS, `tenant_id` o una ruta con tenant: **test cross-tenant** que intente el recurso de otro
      tenant y espere 404/403. ⚑ Y comprobar que el harness puede verlo: `Integration/` corre **una
      conexión** bajo rollback DAMA, así que una prueba de aislamiento que no abra una segunda conexión
      puede estar pasando sin ejercitar nada.
- [ ] Si toca una credencial o un token: test del camino de rechazo (credencial mala, expirada, de otro
      destinatario), no solo del feliz.
- [ ] Nada de tests de rate limit: el componente no está instalado (arriba).

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

- <!-- OFFREPO --> Diseño original (prototipo, superado): `Implementación/Skills de Ejecución de Tareas/backend/05 - Security Audit Backend.md`
- security-audit-core: `.claude/skills/security-audit-core/SKILL.md`
