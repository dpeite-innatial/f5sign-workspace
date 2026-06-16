---
name: perf-smoke-frontend
description: 'Smoke test de performance en frontend (Nuxt/Vue): bundle size delta, Lighthouse CI (Performance, Accessibility, Best Practices, SEO), Core Web Vitals (LCP, FID, CLS), detección de imports pesados nuevos. Requiere tag critical-path. Emite warnings, no bloquea. Úsalo con /perf-smoke-frontend T{id}. Activar con "perf frontend", "bundle size", "lighthouse", "web vitals".'
---

# Perf Smoke Frontend

Smoke test de performance en frontend. Solo si tag `critical-path`. No gate duro — WARN.

## Invocación

```
/perf-smoke-frontend T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `.md` de la tarea
- Snapshot de bundle de `main` (pre-generado por task-runner)

Umbrales por defecto (overridables por `.md` en "Detalle tecnico" subsección):
- Bundle delta: `<+10%` pass, `+10-25%` warn, `>+25%` warn alto
- Lighthouse Performance: `≥80` pass, `60-80` warn, `<60` warn alto
- LCP: `<2.5s` pass, `2.5-4s` warn, `>4s` warn alto
- CLS: `<0.1` pass, `0.1-0.25` warn, `>0.25` warn alto

## Outputs

- `var/task-runner/T{id}/perf-smoke-frontend.report.md`
- `var/task-runner/T{id}/perf-metrics-frontend.json`
- `var/task-runner/T{id}/bundle-analysis.html` (si vite analyze se ejecuta)
- `var/task-runner/T{id}/lighthouse-report.json` (si lighthouse se ejecuta)
- JSON: `{"status":"pass|warn|fail","summary":"...","issues":[...],"metrics":{"bundleDelta":0.12,"lighthouse":{...}}}`

`fail` SOLO si la skill no pudo ejecutarse (entorno roto).

## Ejecución

### Paso 1 — Determinar qué medir

Según context-digest y diff:
- Rutas/páginas modificadas → candidatas para Lighthouse
- Componentes pesados nuevos → candidatos para análisis de bundle
- Si no hay nada medible → `status: warn, summary: "tag critical-path pero nada medible"`, añadir `tagMismatches: ["critical-path"]`

### Paso 2 — Bundle size

```bash
npm run build
```

Si el proyecto tiene `rollup-plugin-visualizer` o `vite-bundle-analyzer`:
```bash
# Genera HTML de análisis
npm run build -- --analyze
# O, dependiendo del setup
npx vite-bundle-visualizer
```

- Calcular tamaño del bundle actual (dist/ o equivalente)
- Comparar con snapshot de `main` (provisto por task-runner)
- Delta:
  - `<+10%` → pass
  - `+10-25%` → WARN
  - `>+25%` → WARN alto

Detectar imports pesados nuevos (librerías >50KB añadidas):
- Parsear `package.json` diff
- Si hay dependencia nueva: estimar su tamaño (via `bundlephobia` si disponible online, o del análisis de bundle)
- Si > 50KB gzipped → WARN "dependencia pesada {nombre} ({KB})"

### Paso 3 — Lighthouse CI

Requiere:
- Servidor de preview levantado (`npm run preview` o `npm run dev`)
- Backend accesible (puede ser mock o real)

```bash
npx lighthouse {URL-de-la-ruta} --output=json --output-path=var/task-runner/T{id}/lighthouse-report.json --chrome-flags="--headless"
```

Para cada ruta afectada, ejecutar Lighthouse y extraer:
- Performance score (0-100)
- Accessibility score
- Best Practices score
- SEO score
- Métricas de Core Web Vitals: LCP, FID (o TBT), CLS

Comparar con umbrales:
- Performance:
  - `≥80` → pass
  - `60-80` → WARN
  - `<60` → WARN alto
- Accessibility: `<90` → WARN (si tarea es crítica, considerar FAIL — lo gestiona a11y-check primariamente)
- LCP / CLS: según tabla de umbrales

### Paso 4 — Core Web Vitals

Incluidas en Lighthouse. Reportar explícitamente:
- **LCP** (Largest Contentful Paint): objetivo <2.5s
- **FID / TBT** (First Input Delay / Total Blocking Time): objetivo <100ms / <200ms
- **CLS** (Cumulative Layout Shift): objetivo <0.1

### Paso 5 — Análisis de renders (opcional)

Si disponible: ejecutar Playwright con Vue DevTools output capturado. Detectar componentes con >5 re-renders durante una interacción simple. Reportar como WARN "componente {X} re-renderiza excesivamente".

### Paso 6 — Fallback

Si Lighthouse CLI no está instalado, o vite build no está disponible, o el servidor de preview no arranca:
- `status: warn`, summary claro de qué falta
- Saltarse la medición correspondiente pero intentar las demás

Nunca bloquear por infra faltante en dev.

## Gravedad

Todo WARN (o FAIL solo si la skill no pudo correr). La deuda queda en `notes.md` para `task-close`.

## Report

```markdown
# perf-smoke-frontend — T{id}

**Status:** {PASS|WARN}
**Issues:** {N} warnings ({alta}/{media})

## Métricas

### Bundle
- Tamaño main: 342 KB gzipped → 358 KB gzipped
- Delta: +4.7% ✓
- Nuevas dependencias: ninguna

### Lighthouse (ruta /dashboard)
- Performance: 87 ✓
- Accessibility: 96 ✓
- Best Practices: 92 ✓
- SEO: 88 ✓

### Core Web Vitals
- LCP: 1.8s ✓
- FID (TBT): 50ms ✓
- CLS: 0.05 ✓

## Warnings
- [bundle-heavy-dep] Se añade `@tiptap/core` (~80KB gzipped); revisar si se puede lazy-load
- [lighthouse-seo] Falta meta description en nueva página /signer/uuid
```

## JSON de retorno

```json
{"status":"warn","summary":"1 dependencia pesada nueva + SEO perfectible","issues":[{"severity":"warn","category":"bundle-heavy-dep","message":"@tiptap/core ~80KB gzipped"}],"metrics":{"bundleDelta":0.047,"lighthouse":{"performance":87,"accessibility":96,"lcp":1800,"cls":0.05}}}
```

## Interacción con el loop

Nunca dispara reintento automático. Si supervised y hay WARN alta, task-runner pregunta si iterar o dejar deuda.

## Qué NO hace

- No es load testing (concurrencia, picos)
- No analiza performance de código de terceros (módulos node_modules)
- No hace profiling de runtime JS con flamegraphs
- No optimiza — solo detecta

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/frontend/07 - Perf Smoke Frontend.md`
