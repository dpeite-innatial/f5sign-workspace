---
name: security-audit-core
description: Audit de seguridad genérico del código introducido por una tarea, independiente del stack. Cubre checks comunes (secretos hardcoded, PII en logs, dependencias con CVEs, autenticación/autorización a nivel conceptual, auth middleware presente, cross-tenant leaks) y delega los checks específicos del stack en security-audit-backend o security-audit-frontend según el repo. Si la tarea toca firma/crypto, delega también en eidas-compliance. Úsalo con /security-audit-core T{id}. Activar con "audit seguridad", "revisar security", "OWASP check", "auth/PII check".
---

# Security Audit Core

Gate duro de seguridad. Se invoca siempre. Ejecuta checks genéricos y delega en las variantes específicas del stack.

## Invocación

```
/security-audit-core T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- Reports previos que existan en el workspace (`doctrine-guard.report.md`, `contract-check*.report.md`, etc.) para evitar redundancia
- El `.md` de la task. **Las delegaciones se deciden por lo que toca el diff, no por tags** (este formato no los tiene)
- Output de `composer audit` / `npm audit` provisto por task-runner
- `.claude/skills-config.yaml` del repo (para saber el stack: `backend` | `frontend`)

## Outputs

- `var/task-runner/T{id}/security-audit.report.md` (reporte consolidado de core + backend/frontend + eidas si aplica)
- JSON:
  ```json
  {"status":"pass|fail|warn","summary":"...","issues":[...],"delegatedTo":["security-audit-backend|frontend","eidas-compliance"?]}
  ```

## Ejecución

### Paso 1 — Checks genéricos (cualquier stack)

Ejecutar sobre ficheros del diff. Saltar categorías cuyo scope no aparece en el diff.

#### Secretos
- [ ] No hay API keys, passwords, tokens hardcoded (grep patrones: `AWS_`, `API_KEY`, `SECRET`, `Bearer `, base64 largo, strings `sk_live_`, `pk_live_`, JWT-like)
- [ ] ⚑ **`.env`, `.env.dev` y `.env.test` SÍ están commiteados a propósito** (regla 4 del repo): llevan
      defaults del stack local, que coinciden con el compose de infra y no son secretos. Lo que se busca no
      es "hay un `.env` en git", es **una credencial real**: password de prod/staging, token de API real,
      `APP_SECRET` real, la contraseña del keystore de DSS. Esas viven solo en `.env.local` / `.env.*.local`
      (gitignorados) o en el vault de secretos.
- [ ] ⛔ **Y un placeholder para una variable sensible es un hallazgo, no una solución.** `.env` viaja
      **dentro de la imagen de producción**, así que una clave nombrada ahí siempre resuelve y producción
      arrancaría con el valor commiteado. El patrón correcto es la **ausencia** (que `%env()%` falle al
      construir el contenedor); la única excepción es `FIELD_ENCRYPTION_SECRET=` vacía, porque vacío no
      puede funcionar y su consumidor rechaza menos de 32 bytes
- [ ] No hay URLs internas commiteadas (endpoints privados, hostnames de prod)
- [ ] Logs no imprimen variables sensibles (grep log statements con variables que contengan "token", "password", "secret", "key", "credential")

#### PII
- [ ] PII en logs: emails, teléfonos, DNI/NIE, IBAN, direcciones, nombres reales — redactados o fuera.
- [ ] ⚑ **Afirmar el conjunto de claves cerrado, no hacer un spot-check.** Un "aquí no veo PII" pasa por alto
      el campo nuevo: enumerar los campos que la superficie emite/persiste y decidir sobre **todos**. En el
      backend, PII en reposo va cifrada por campo (ADR-0032/ADR-0033) y **fuera** del event log, cuyo payload
      es pseudónimo (ADR-0031, Path B)
- [ ] PII en URLs: no está en path ni query string (va en body o headers)
- [ ] Responses no exponen más PII de la necesaria para el endpoint

#### Autenticación / Autorización (conceptual)
- [ ] Rutas nuevas que deberían requerir auth, la requieren. ⚠ En el backend **no hay SecurityBundle
      registrado**: el seam es la ruta que declara su tipo de credencial y un principal ya verificado
      (ADR-0044/ADR-0048). El detalle lo comprueba `security-audit-backend`; aquí basta con que ninguna ruta
      nueva quede sin declaración
- [ ] Operaciones que requieren authz (no solo estar logueado, sino tener permiso sobre el recurso concreto) tienen check explícito
- [ ] Tokens JWT / session tokens no se loguean ni devuelven en responses

#### Aislamiento multi-tenant (conceptual)
- [ ] Endpoints/operaciones nuevas que acceden a datos de un tenant respetan el contexto (verificación formal a nivel stack se hace en backend/frontend; aquí solo conceptual)
- [ ] IDs de recursos no se confían del cliente sin verificación
- [ ] Si la tarea es crítica en multi-tenancy: existe test de cross-tenant que intenta acceder a recurso de otro tenant y espera 404/403

#### Dependencias
Input: output de `composer audit` (backend) o `npm audit` (frontend) provisto por task-runner.
- [ ] Sin CVEs HIGH ni CRITICAL introducidas por esta tarea
- MEDIUM → `warn`
- LOW → `warn`

#### Errores y logging
- [ ] Mensajes de error al usuario no filtran stack traces, paths internos, detalles de infraestructura
- [ ] 404 vs 403: 403 solo si el usuario sabe del recurso (evitar user enumeration)

### Paso 2 — Delegar en security-audit-{stack}

Leer `.claude/skills-config.yaml` para determinar stack. Si no existe el fichero, inferir por presencia de `composer.json` (backend) o `package.json` con Vue/Nuxt (frontend).

Invocar via Agent tool:
```
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "security-audit-{stack} on T{id}",
  prompt: "Execute the security-audit-{stack} skill at .claude/skills/security-audit-{stack}/SKILL.md on T{id}. Workspace: var/task-runner/T{id}/. Return the JSON summary."
})
```

Consolidar su report bajo sección "## security-audit-{stack}" del report propio. Sus issues se suman a la lista total.

### Paso 3 — Delegar en eidas-compliance (si aplica)

Si el diff toca firma o cripto — `src/F5Sign/SignatureExecution/`, `Foundation/Crypto/`, DSS, PAdES, TSA:
```
Agent({
  subagent_type: "general-purpose",
  model: "opus",
  description: "eidas-compliance on T{id}",
  prompt: "Execute eidas-compliance skill at .claude/skills/eidas-compliance/SKILL.md on T{id}..."
})
```

Consolidar bajo "## eidas-compliance". Si devuelve `fail` → esta skill también falla.

### Paso 4 — Consolidar y devolver

Si cualquier delegación devolvió `fail` → `status: fail`.
Si todas `pass` pero hay WARNs → `status: warn`.
Si todo limpio → `status: pass`.

## Gravedad

- **FAIL:** SQL/command injection detectada conceptualmente, endpoint sin auth cuando debería, cross-tenant leak, secreto hardcoded, PII en logs sin redactar, `security-audit-{stack}` o `eidas-compliance` devuelven fail
- **WARN:** dependencia con CVE LOW/MEDIUM, mensaje de error algo verboso, y —una sola vez, no por
  endpoint— que una superficie nueva pediría rate limiting: **el componente no está instalado en el
  backend**, así que es una carencia de capacidad, no un defecto de la ruta

## Report

```markdown
# security-audit — T{id}

**Status:** {PASS|FAIL|WARN}
**Issues totales:** {B} bloqueantes, {W} warnings
**Delegaciones:** security-audit-{stack} ({status}), eidas-compliance ({status})

## Issues core
- [{categoría}] {fichero:línea} {mensaje}

## security-audit-{stack}
{resumen consolidado del report de la skill específica}

## eidas-compliance (si aplica)
{resumen consolidado}

## Categorías revisadas
- Secretos: OK
- PII: OK
- Auth/Authz: OK
- Multi-tenant: OK
- Dependencias: {N} CVEs (LOW:X, MEDIUM:Y, HIGH:0, CRITICAL:0)
```

## JSON de retorno

Última línea:
```json
{"status":"fail","summary":"1 secreto hardcoded + 1 fail en security-audit-backend","issues":[{"severity":"fail","category":"secret-hardcoded","file":"...","message":"..."}],"delegatedTo":["security-audit-backend"]}
```

## Qué NO hace

- No valida contratos API (contract-check-*)
- No valida persistencia (doctrine-guard)
- No ejecuta pentesting ni exploits
- No audita infraestructura (Docker, k8s, CI)
- No reescribe código — solo reporta

## Protocolo de corrección

Si task-runner reintenta pasando este report a `implement-*`: instrucción "corregir issues bloqueantes sin cambiar el scope". Máx 2 iteraciones automáticas.

## Referencias

- <!-- OFFREPO --> Diseño original (prototipo, superado): `Implementación/Skills de Ejecución de Tareas/common/06 - Security Audit Core.md`
- security-audit-backend: `.claude/skills/security-audit-backend/SKILL.md` (en repo backend)
- security-audit-frontend: `.claude/skills/security-audit-frontend/SKILL.md` (en repo frontend)
