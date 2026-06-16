---
name: task-validate-frontend
description: Gate duro de calidad funcional en frontend (Nuxt 3 + Vue 3 + TypeScript): ejecuta npm run lint, type-check (vue-tsc), tests unit/component (Vitest) y e2e (Playwright si aplica), build (vite), valida cobertura mínima del 80%, y verifica que los AC de la story están cubiertos por tests. Solo para repositorios frontend. Úsalo con /task-validate-frontend T{id}. Activar con "validar tarea frontend", "run vitest", "check tests Vue/TS".
---

# Task Validate Frontend

Gate duro de calidad funcional en frontend. Se invoca siempre en repo frontend.

## Invocación

```
/task-validate-frontend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `.md` de la tarea
- README de la story padre (para AC)

## Outputs

- `var/task-runner/T{id}/validate.report.md`
- `var/task-runner/T{id}/test-results.json` (salida estructurada de Vitest)
- JSON: `{"status":"pass|fail","summary":"...","issues":[...],"acCovered":[...],"acFailed":[],"coverage":0.87}`

## Precondición

Servicios dependientes levantados: backend API mock o real accesible si los tests E2E requieren. Si no, emitir `fail, summary: "backend no accesible para E2E"`.

## Ejecución

### Paso 1 — Lint

```bash
npm run lint -- --format=json
```

- [ ] Exit code 0
- [ ] Sin errors (warnings permitidos con umbral bajo, ej. ≤3)

Si el lint está configurado con `--fix` automático: NO ejecutarlo aquí (solo validar, no modificar). El lint debería haberlo hecho `implement-frontend`.

### Paso 2 — Type check

```bash
npm run type-check
```

Equivale a `vue-tsc --noEmit` o similar según proyecto.

- [ ] Exit code 0
- [ ] Sin errores nuevos en ficheros del diff

### Paso 3 — Tests unit + component

```bash
npm run test:unit -- --reporter=json --coverage --coverage-reporter=clover
```

- [ ] Exit code 0
- [ ] Número de tests ejecutados = tests declarados en la tabla `## Tests` del `.md`
  - Diff negativo → FAIL
  - Diff positivo → WARN

Parsear output JSON, extraer:
- Total tests, passed, failed, skipped
- Tests que cubren cada `AC-xx` (grep en nombres/DocBlocks)

### Paso 4 — Coverage

- Coverage de líneas nuevas/modificadas (del diff)
  - Parsear clover.xml + cruzar con líneas del diff
- Umbral: **80%** (sin excepciones)
  - < 78% → FAIL
  - 78-80% → WARN
  - ≥ 80% → pass

### Paso 5 — Tests E2E (si aplica)

Condiciones para ejecutar E2E:
- Tarea tiene tag `critical-path`, O
- Tabla `## Tests` del `.md` declara tests E2E, O
- AC de la story involucran flujo completo (login + acción + resultado)

```bash
npm run test:e2e -- --reporter=json
```

- [ ] Exit 0
- [ ] Tests declarados ejecutados
- [ ] AC críticos cubiertos por E2E

### Paso 6 — Build

```bash
npm run build
```

- [ ] Exit 0 (el código compila limpio en modo producción)
- [ ] Sin warnings de build críticos

### Paso 7 — Cobertura de AC

Para cada `AC-\d+` aplicable a la tarea:
- [ ] Existe al menos un test cuyo nombre o DocBlock incluye `AC-{xx}`
- [ ] El test ha sido ejecutado y pasa

Lista `acCovered` / `acFailed` / `acUncovered`.

### Paso 8 — Ficheros declarados vs reales

- Parsear tabla `## Archivos a crear/modificar`
- `git diff --name-only {base}..HEAD`
- Ficheros declarados ausentes → FAIL
- Ficheros extra → WARN

## Report

```markdown
# task-validate-frontend — T{id}

**Status:** {PASS|FAIL}
**Lint:** PASS (0 errors, 2 warnings)
**Type check:** PASS
**Tests unit/component:** {total} total, {passed} passed, {failed} failed
**Tests E2E:** {total} total, {passed} passed (si se ejecutaron)
**Coverage:** {%} (umbral 80%)
**Build:** PASS
**AC cubiertos:** {N}/{total}

## Failed tests
- {fichero}::{método}
  - Expected: {x}
  - Actual: {y}

## AC no cubiertos
- AC-{xx}: ningún test lo verifica

## Ficheros fuera de scope
- {lista o "ninguno"}
```

## JSON de retorno

```json
{"status":"fail","summary":"2 tests fallan + coverage 76% < 80%","issues":[{"severity":"fail","category":"test-failure","test":"SignerForm.spec.ts::testValidation","message":"..."}],"acCovered":["AC-01","AC-02"],"acFailed":[],"acUncovered":["AC-03"],"coverage":0.76}
```

## Qué NO hace

- No audita seguridad (`security-audit-core` + `security-audit-frontend`)
- No valida a11y (`a11y-check`)
- No valida design system (`design-system-check`)
- No mide performance (`perf-smoke-frontend`)
- No corrige código ni tests
- No ejecuta lint `--fix` ni formateo

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/frontend/05 - Task Validate Frontend.md`
