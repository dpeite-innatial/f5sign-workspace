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
- `.md` de la tarea (para tags, decide delegaciones)
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
- [ ] No hay `.env` con valores reales commiteado
- [ ] No hay URLs internas commiteadas (endpoints privados, hostnames de prod)
- [ ] Logs no imprimen variables sensibles (grep log statements con variables que contengan "token", "password", "secret", "key", "credential")

#### PII
- [ ] PII en logs: emails, teléfonos, DNI/NIE, IBAN, direcciones físicas, nombres reales. Si aparecen en log statements, deben estar redactados (ej. `***@domain.tld`) o no loggearse
- [ ] PII en URLs: no está en path ni query string (va en body o headers)
- [ ] Responses no exponen más PII de la necesaria para el endpoint

#### Autenticación / Autorización (conceptual)
- [ ] Endpoints/rutas nuevas que deberían requerir auth, la requieren (cualquier stack)
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

Si el `.md` tiene tags `signing`, `crypto` o `eidas`:
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
- **WARN:** dependencia con CVE LOW/MEDIUM, mensaje de error ligeramente verbose, falta rate limit aparente

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

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/common/06 - Security Audit Core.md`
- security-audit-backend: `.claude/skills/security-audit-backend/SKILL.md` (en repo backend)
- security-audit-frontend: `.claude/skills/security-audit-frontend/SKILL.md` (en repo frontend)
