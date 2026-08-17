---
name: perf-smoke-backend
description: 'Smoke de performance en backend (PHP/Symfony). Su mitad ESTÁTICA sí corre hoy y es la útil: N+1 por lectura de código, índice efectivo para las consultas nuevas, trabajo pesado (o llamadas de red) dentro de una transacción o un lock, y trabajo síncrono en el camino HTTP que debería ir por Messenger. La mitad DINÁMICA (p95, throughput, memoria) no es ejecutable: depende de composer perf:seed, que no existe en este repo, y se reporta como skipped con su razón, nunca como verde. Emite warnings, no bloquea. Solo para repositorios con stack PHP/Symfony. Úsalo con /perf-smoke-backend T{id}. Activar con "smoke perf backend", "benchmark API PHP", "check N+1".'
---

# Perf Smoke (backend)

⛔ **La mitad dinámica no es ejecutable hoy.** Depende de `composer perf:seed`, que **no existe**: los
scripts de este repo son `test`, `coverage`, `coverage:text`, `coverage:clover`, `phpstan`, `arch`, `lint`,
`format`, `infection`, `qa` (comprobar con `composer run-script --list`, no fiarse de esta lista). Sin
fixtures no hay p95, ni throughput, ni consumo comparable, y **`task-runner` la salta declarándolo en
`run.log` como `skipped` con su razón — nunca como verde**.

✅ **La mitad estática sí vale, y es la que más ha pagado en este repo.** Se puede hacer sin fixtures:

- [ ] **N+1 por lectura del código**: un bucle que consulta por elemento en vez de una consulta por lote.
- [ ] **Índice efectivo para las consultas que el diff añade**: que exista uno cuyo prefijo sea el `WHERE`
      real (en tablas de tenant, empezando por `tenant_id`), no un índice cualquiera sobre la columna.
- [ ] **Trabajo pesado dentro de una transacción**: sobre todo una llamada de red dentro de un lock. ⚑
      `BL-17` está abierto justo por eso — nada acota la ventana de lock durante DSS: `lock_timeout` y
      `statement_timeout` no aparecen en `src/`, `config/` ni en infra, mientras la transacción de firma
      abarca N documentos a través de la latencia de DSS. Si el diff amplía ese tramo, decirlo.
- [ ] **Trabajo síncrono en el camino HTTP** que debería ir por Messenger (regla 3 del repo).

Lo estático emite `warn`, no bloquea. Lo dinámico se reporta como no ejecutado.

Smoke test de performance. Solo si tags incluye `critical-path`. NO es gate duro — emite warnings.

## Invocación

```
/perf-smoke T{id}
```

## Precondición

⚠ **No hay `composer perf:seed` en este repo**, así que los fixtures nunca están cargados: la parte dinámica se reporta `skipped` con esa razón literal y se ejecuta solo la estática de arriba. No bloquea. Crear el seed es una decisión (y una fila de BACKLOG), no algo que esta skill improvise.

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
- No hay tags que validar: la condición de entrada es lo que toca el diff, y la evalúa quien delega.

Si no hay nada medible → `status: pass`, `summary: "nada medible en el diff"`. Sin `tagMismatches`: no hay tags en este formato.

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

- <!-- OFFREPO --> Diseño original (prototipo, superado): `Implementación/Skills de Ejecución de Tareas/backend/07 - Perf Smoke Backend.md`
- Fixtures perf: T26.2.3 (provee `composer perf:seed`)
