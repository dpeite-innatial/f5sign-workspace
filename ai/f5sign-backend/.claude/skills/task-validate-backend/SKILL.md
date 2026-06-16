---
name: task-validate-backend
description: 'Gate duro de calidad funcional en backend (PHP/Symfony): corre composer test:* (unit, integration, e2e), valida cobertura mínima del 80%, ejecuta PHPStan y PHP-CS-Fixer, comprueba cobertura de AC, y confirma que los ficheros declarados en el .md coinciden con los modificados. Solo para repositorios con stack PHP/Symfony. Úsalo con /task-validate-backend T{id}. Activar con "validar tarea backend", "run phpunit", "check PHPStan y AC".'
---

# Task Validate

Gate duro de calidad funcional. Se invoca siempre.

## Invocación

```
/task-validate T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `.md` de la tarea
- README de la story padre (para AC)

## Outputs

- `var/task-runner/T{id}/validate.report.md`
- `var/task-runner/T{id}/test-results.json`
- JSON:
  ```json
  {"status":"pass|fail","summary":"...","issues":[...],"acCovered":["AC-01","AC-02"],"acFailed":[],"coverage":0.87}
  ```

## Precondición crítica

El entorno de tests debe estar operativo (DB, RabbitMQ, Redis). Si algún servicio está down durante la ejecución → `status: fail, summary: "infrastructure unavailable: X"`. No reintentar automáticamente.

## Ejecución

### Paso 1 — Suite de tests

Ejecutar en orden (parar al primer fallo bloqueante si todos los siguientes dependen):

```bash
composer test:unit          # exit code 0 esperado
composer test:integration   # exit code 0 esperado
composer test:e2e           # solo si tags incluye "api"
```

Capturar output en `test-results.json` (usar `--log-junit` de PHPUnit o equivalente).

Para cada suite:
- [ ] Exit code 0
- [ ] Contar tests ejecutados vs tests declarados en la tabla `## Tests` del `.md`
  - Diff negativo → `fail` "tests declarados no ejecutados"
  - Diff positivo → `warn` "más tests ejecutados que declarados" (puede ser legítimo)

### Paso 2 — Coverage

- Generar coverage solo de líneas modificadas (parsear `changes.diff` + coverage clover):
  ```bash
  composer test:unit -- --coverage-clover=var/task-runner/T{id}/coverage.xml
  ```
- Calcular % de líneas nuevas/modificadas cubiertas
- Umbral: **80%** (duro, sin excepciones por tarea)
- < 78% → `fail`
- 78-80% → `warn` "rozando el umbral"
- ≥ 80% → pass

### Paso 3 — Análisis estático

```bash
composer phpstan -- --error-format=json {ficheros-del-diff}
```

- [ ] Sin errores nuevos en ficheros del diff (comparar contra baseline si existe)

```bash
composer psalm -- --output-format=json {ficheros-del-diff}    # solo si está configurado
composer cs-check                                               # PHP-CS-Fixer o Pint
```

- [ ] Sin errores nuevos
- [ ] Sin violaciones de estilo

### Paso 4 — Cobertura de AC

Para cada `AC-\d+` en la story que aplique a esta tarea (heurística: la tabla de Tasks de la story menciona la tarea):
- [ ] Existe al menos un test cuyo nombre o DocBlock contiene `AC-{xx}` (ej. `testAC01_HappyPath` o `@covers AC-01`)
- [ ] El test ha sido ejecutado y pasa

Lista `acCovered` y `acFailed` en el JSON.

Si algún AC aplicable no tiene test → `fail` categoría `ac-uncovered`.

### Paso 5 — Ficheros declarados vs reales

- Parsear tabla `## Archivos a crear/modificar` del `.md`
- Obtener `git diff --name-only {base}..HEAD`
- [ ] Todos los ficheros declarados están en el diff → si falta alguno: `fail` categoría `missing-file`
- [ ] Ficheros en el diff fuera de los declarados: `warn` categoría `extra-file` (puede ser legítimo pero alerta)

### Paso 6 — Migrations (si tags incluye `migration`)

```bash
bin/console doctrine:migrations:migrate --dry-run --no-interaction
```

- [ ] Sin errores

Si tag `rls`: ejecutar la suite específica de RLS si el proyecto la tiene (ej. `composer test:rls`).

## Report

```markdown
# task-validate — T{id}

**Status:** {PASS|FAIL}
**Tests:** {ejecutados} passed, {failed} failed, {skipped} skipped
**Coverage:** {%} (umbral 80%)
**AC cubiertos:** {N}/{total}

## Failed tests
- {fichero::método}
  - Expected: {x}
  - Actual: {y}

## AC no cubiertos
- AC-{xx} "{descripción}": ningún test lo verifica

## Análisis estático
- PHPStan: {N} errores nuevos
- PHP-CS: {N} violaciones

## Ficheros fuera de scope
- {lista o "ninguno"}
```

## JSON de retorno

```json
{"status":"fail","summary":"3 tests fallan, AC-05 no cubierto","issues":[{"severity":"fail","category":"test-failure","test":"CloseEnvelopeHandlerTest::testAC03","message":"..."}],"acCovered":["AC-01","AC-02","AC-03","AC-04"],"acFailed":[],"acUncovered":["AC-05"],"coverage":0.76}
```

## Qué NO hace

- No audita seguridad, compliance, performance
- No juzga diseño/arquitectura (cubierto implícitamente por PHPStan + convenciones)
- No escribe tests faltantes — solo detecta que faltan
- No corrige código ni tests

## Protocolo de corrección

Si `task-runner` lanza un reintento con este report como input a `implement`, la instrucción es "corregir los issues sin cambiar el scope". Máximo 2 iteraciones automáticas. Al 3er intento fallido → abort + intervención humana.

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/backend/04 - Task Validate Backend.md`
