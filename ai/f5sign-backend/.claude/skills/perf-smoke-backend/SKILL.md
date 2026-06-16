---
name: perf-smoke-backend
description: 'Smoke test de performance en backend (PHP/Symfony) sobre código crítico: detecta N+1, falta de índices efectivos, endpoints lentos (p95), throughput de workers y consumo de memoria anómalo. Requiere fixtures perf cargadas previamente (composer perf:seed). Emite warnings, no bloquea. Solo para repositorios con stack PHP/Symfony. Úsalo con /perf-smoke-backend T{id}. Activar con "smoke perf backend", "benchmark API PHP", "check N+1".'
---

# Perf Smoke

Smoke test de performance. Solo si tags incluye `critical-path`. NO es gate duro — emite warnings.

## Invocación

```
/perf-smoke T{id}
```

## Precondición

`task-runner` ha ejecutado `composer perf:seed` antes de invocar esta skill. Si los fixtures no están cargados → `status: warn, summary: "perf seed not loaded, skipped"`. No bloquea.

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `var/task-runner/T{id}/doctrine-guard.report.md` (si existe; para correlacionar índices)
- `.md` de la tarea (tags + umbrales overrideados si los declara)

Umbrales por defecto (overridables en el `.md`):
- Endpoint HTTP: p95 < 300ms → pass; 300-800ms → warn; > 800ms → warn alta
- Worker: throughput por encima del mínimo definido en config del proyecto
- Memoria: endpoint < 50MB por request
(Frontend perf se mide con la skill `perf-smoke-frontend` en su propio repo.)

## Outputs

- `var/task-runner/T{id}/perf-smoke.report.md`
- `var/task-runner/T{id}/perf-metrics.json`
- JSON:
  ```json
  {"status":"pass|warn|fail","summary":"...","issues":[...],"metrics":{"endpoints":{...},"workers":{...}}}
  ```

`status: fail` SOLO si la skill no pudo ejecutarse (entorno roto). Issues de perf son siempre `warn`.

## Ejecución

### Paso 1 — Detectar qué medir

Según tags y diff:
- Si tag `api`: identificar endpoints nuevos/modificados (buscar Controllers en el diff, extraer paths)
- Si tag `worker`: identificar handlers nuevos/modificados
- El tag `ui` NO aplica en backend — si aparece aquí, es un error del `.md` (señalar como tagMismatch)

Si no hay nada medible → `status: warn, summary: "tag critical-path pero nada medible en el diff"`, añadir `tagMismatches: ["critical-path"]`.

### Paso 2 — Análisis estático de queries (si hay código de persistencia en diff)

- Habilitar Doctrine SQL logger en el entorno de medición
- Para cada endpoint nuevo: llamarlo una vez contra datos del seed
- Contar queries ejecutadas; si > 5 cuando debería ser 1 por colección → `warn` "N+1 sospechoso"
- `EXPLAIN ANALYZE` sobre cada query nueva:
  - Seq Scan en tabla > 1000 filas → `warn`
  - Sort sin índice → `warn`
  - Join sin índice en FK → `warn` (doctrine-guard debería haberlo pillado, pero doble check)

### Paso 3 — Benchmark de endpoints (si tag `api`)

Para cada endpoint nuevo:
- **Warm-up:** 10 requests ignorados
- **Medición:** 100 requests secuenciales (no concurrentes — esto no es load test)
- Capturar tiempos en ms; calcular p50, p95, p99, max
- Comparar con umbrales (defaults o los declarados en el `.md`)
- Resultado → metrics JSON

### Paso 4 — Benchmark de workers (si tag `worker`)

- Encolar 50 mensajes de prueba contra el handler nuevo
- Medir throughput (msg/s) y tiempo medio por mensaje
- Comparar con mínimo del proyecto

### Paso 5 — Memoria

- Durante la ejecución del endpoint, medir uso de memoria (`memory_get_peak_usage`)
- Si > 50MB → `warn`
- Si el código tiene `findAll`/`fetchAll` sobre tablas grandes sin paginación → `warn` "fetch sin paginación"

### Paso 6 — Fallback

Si tooling no disponible (PHPBench no instalado, Lighthouse no instalado, seed no cargado) → `status: warn`, summary claro indicando qué faltó, y saltarse la medición correspondiente. Nunca bloquear por infra faltante en dev.

## Report

```markdown
# perf-smoke — T{id}

**Status:** {PASS|WARN}
**Issues:** {N} warnings ({alta}/{media})

## Métricas clave
- POST /api/v1/envelopes/{id}/close
  - p50: 145ms | p95: 312ms | p99: 480ms | max: 620ms
  - Queries por request: 8 (esperado: ≤5)
- Worker SignEnvelopeHandler
  - Throughput: 12 msg/s (umbral: 10 msg/s) ✓

## Warnings
- [N+1 sospechoso] GET /api/v1/envelopes/{id} ejecuta 1+N queries al cargar signers; considerar fetch join (gravedad alta)
- [p95 límite] POST /api/v1/envelopes/{id}/close p95=312ms, rozando umbral 300ms (gravedad media)
```

## JSON de retorno

```json
{"status":"warn","summary":"2 warnings (1 alta)","issues":[{"severity":"warn","category":"n+1","endpoint":"GET /api/v1/envelopes/{id}","message":"1+N queries"}],"metrics":{"endpoints":{"POST /api/v1/envelopes/{id}/close":{"p50":145,"p95":312,"p99":480}}}}
```

## Interacción con el loop

Nunca dispara reintento automático. Si modo supervised y hay WARN alta, task-runner pregunta al usuario si iterar o dejar la deuda técnica documentada en `notes.md` (lo recoge task-close).

## Qué NO hace

- No es load testing (sin concurrencia, sin picos)
- No hace profiling línea a línea (XHProf, Blackfire se hacen manualmente si la deuda justifica)
- No audita performance de código base no tocado
- No optimiza código — solo detecta

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/backend/07 - Perf Smoke Backend.md`
- Fixtures perf: T26.2.3 (provee `composer perf:seed`)
