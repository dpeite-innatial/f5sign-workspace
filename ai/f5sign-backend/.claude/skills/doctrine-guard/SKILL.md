---
name: doctrine-guard
description: Validación mecánica de la capa de persistencia tras una tarea: entidades Doctrine (pureza hexagonal), mapeos orm.xml, migrations (reversibilidad, índices, multi-tenancy), políticas RLS y coherencia SQL↔PHP de ENUMs. Úsalo con /doctrine-guard T{id}. Activar con "validar migration", "revisar persistencia de tarea", "check doctrine", "auditar RLS".
---

# Doctrine Guard

Validación mecánica de persistencia. Solo se invoca si tags incluye `db`, `migration`, `rls` o `tenancy`.

## Invocación

```
/doctrine-guard T{id}
```

Si la tarea no tiene ninguno de los tags relevantes pero igual se invoca: emitir warn y terminar con `status: pass, summary: "nothing to check for these tags"`.

## Inputs

- `var/task-runner/T{id}/changes.diff` (obligatorio; si no existe → `status: fail, summary: "missing changes.diff"`)
- `var/task-runner/T{id}/context-digest.md` (opcional; usar para saber qué tablas se tocaron)
- `.md` de la tarea (para leer tags)

Ficheros del repo a consultar (solo los que aparecen en el diff):
- `src/**/Domain/Entity/*.php`
- `src/**/Infrastructure/Persistence/Mapping/*.orm.xml`
- `migrations/Version*.php`

## Outputs

- `var/task-runner/T{id}/doctrine-guard.report.md`
- JSON:
  ```json
  {"status":"pass|fail|warn","summary":"...","issues":[...],"tagMismatches":["db"?]}
  ```

## Ejecución

### Paso 1 — Detectar tag mismatch

Si tags incluye `db`/`migration`/`rls`/`tenancy` pero el diff NO toca:
- `migrations/*.php`, ni
- `src/**/Domain/Entity/*.php`, ni
- `*.orm.xml`

→ añadir `"db"` (o el tag correspondiente) a `tagMismatches` del JSON final. No es bloqueante.

### Paso 2 — Entidades Doctrine (si diff toca `Domain/Entity/`)

Por cada fichero `src/**/Domain/Entity/*.php` modificado:

- [ ] No tiene `use Symfony\` ni `use Doctrine\` (grep) → `fail`, categoría `hexagonal-violation`
- [ ] Todas las propiedades tienen tipo (no hay `private $x` sin tipo) → `fail`, categoría `typing`
- [ ] IDs usan VO (no `string $id`, sino `TenantId $id` o similar)
- [ ] Valores monetarios, fechas, emails: VO en lugar de primitivos

Determinar Aggregate Root vs subordinate:
- Aggregate Root: existe `src/{Module}/Domain/Repository/{Name}RepositoryInterface.php`
- Subordinate: no existe esa interfaz y la entidad es referenciada desde otra entidad

- [ ] Si es Aggregate Root → verificar repo interface existe
- [ ] Si no es Aggregate Root → NO debe existir repo propia para ella → `fail` categoría `ddd-violation`

### Paso 3 — Mapping ORM (`*.orm.xml`)

Por cada `.orm.xml` en el diff:

- [ ] El nombre del fichero coincide con una entidad en `Domain/Entity/`
- [ ] Parsear XML con DOMDocument
- [ ] Propiedades mapeadas = propiedades de la entidad (reflexión)
- [ ] Tipos XML coherentes con tipos PHP (`uuid` ↔ `UuidInterface`, `datetime_immutable` ↔ `DateTimeImmutable`, `string` ↔ `string`, `integer` ↔ `int`)
- [ ] Nullable del XML concuerda con nullable de la propiedad
- [ ] VOs embebidos usan `<embedded>` correctamente
- [ ] Si la tabla es multi-tenant (heurística: nombre no empieza por `tenant_` ni `workspace_`; está en el Bounded Context de datos del cliente): columnas `tenant_id` y `workspace_id` presentes

### Paso 4 — Migrations (`migrations/Version*.php`)

Por cada migration en el diff:

- [ ] Método `up()` presente
- [ ] Método `down()` presente (reversibilidad)
- [ ] `down()` no está vacío ni lanza excepción genérica; debe tener operaciones reales
- [ ] Si `up()` crea tabla multi-tenant → `CREATE TABLE` incluye `tenant_id` + `workspace_id`
- [ ] Toda FK tiene su `CREATE INDEX` correspondiente (o `INDEX` en la definición de la tabla)
- [ ] Para queries típicas multi-tenant, existe índice compuesto `(tenant_id, workspace_id, <columna-filtro>)` — si falta pero la tabla es multi-tenant: `warn`

### Paso 5 — RLS (si migration toca tabla multi-tenant)

Grep en la migration por `CREATE POLICY`, `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`:

- [ ] `CREATE POLICY` presente
- [ ] `ENABLE ROW LEVEL SECURITY` presente
- [ ] `FORCE ROW LEVEL SECURITY` presente (superuser también respeta)
- [ ] Policy usa `app.current_tenant_id` (o la variable de sesión del proyecto)
- [ ] Policy cubre SELECT/INSERT/UPDATE/DELETE (o comenta explícitamente por qué no)

Ausencia de cualquiera → `fail` categoría `rls`.

### Paso 6 — ENUMs

Si migration crea `CREATE TYPE ... AS ENUM`:

- [ ] Extraer valores del ENUM SQL
- [ ] Buscar backed enum PHP correspondiente en `src/**/Domain/Enum/*.php` o similar
- [ ] Comparar valores: deben ser idénticos (strings, orden puede variar)

Divergencia → `fail` categoría `enum-mismatch`.

### Paso 7 — Coherencia cruzada

Triangular:
- [ ] Tabla definida en migration = tabla en `<orm.xml>` correspondiente
- [ ] Columnas del orm.xml ⊆ columnas de la migration
- [ ] Propiedad en entidad → mapeada en orm.xml → columna en migration

## Generación del report

```markdown
# doctrine-guard — T{id}

**Status:** {PASS|FAIL|WARN}
**Issues:** {B} bloqueantes, {W} warnings
**Tag mismatches:** {lista o "ninguno"}

## Bloqueantes
- [{categoría}] {fichero:línea si aplica} {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Checks superados
- {resumen de lo que pasó OK}
```

## JSON de retorno

Última línea:
```json
{"status":"fail","summary":"2 bloqueantes en RLS","issues":[{"severity":"fail","category":"rls","file":"migrations/Version20260413120000.php","message":"CREATE POLICY ausente"}],"tagMismatches":[]}
```

## Qué NO hace

- No ejecuta migrations contra la DB
- No valida lógica de negocio de la entidad (eso es task-validate vía unit tests)
- No audita SQL injection ni authz (eso es security-audit)
- No mide performance real (eso es perf-smoke)

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/backend/02 - Doctrine Guard.md`
