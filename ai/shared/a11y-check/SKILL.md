---
name: a11y-check
description: Valida accesibilidad (WCAG 2.1 AA) de componentes y páginas Vue nuevos o modificados tras una tarea frontend. Ejecuta axe-core/pa11y, verifica contraste de colores, labels en inputs, alt en imágenes, navegación por teclado, roles ARIA correctos y focus visible. Gate duro cuando hay cambios visuales. Úsalo con /a11y-check T{id}. Activar con "accesibilidad", "a11y", "WCAG", "check aria/alt/labels".
---

# A11y Check

Validación de accesibilidad. Solo si tags incluye `ui`. Gate duro.

## Invocación

```
/a11y-check T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `.md` de la tarea
- Ficheros Vue del diff

## Outputs

- `var/task-runner/T{id}/a11y-check.report.md`
- `var/task-runner/T{id}/a11y-axe.json` (output crudo de axe si se ejecuta)
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...],"wcagLevel":"AA"}`

## Precondición

Si el proyecto no tiene `axe-core`/`@axe-core/playwright` o `pa11y` instalado → WARN "tooling a11y no disponible" y seguir con los checks estáticos (linter eslint-plugin-vuejs-accessibility si existe). No bloquear.

## Ejecución

### Paso 1 — Checks estáticos sobre ficheros Vue del diff

Para cada `*.vue` modificado:

#### Labels y formularios
- [ ] Cada `<input>`, `<select>`, `<textarea>` tiene `<label for="...">` asociado o `aria-label`/`aria-labelledby`
- [ ] Inputs de tipo `checkbox`/`radio` tienen labels clickeables
- [ ] Formularios tienen `<fieldset>`/`<legend>` cuando agrupan controles relacionados
- [ ] Mensajes de error tienen `aria-live="polite"` o `role="alert"` y vinculados al input con `aria-describedby`

#### Imágenes y media
- [ ] `<img>` tiene `alt` (vacío si decorativa, descriptivo si informativa)
- [ ] Iconos decorativos con `aria-hidden="true"` y `alt=""`
- [ ] Iconos informativos con `aria-label` o texto visible asociado

#### Botones e interactividad
- [ ] Elementos interactivos son botones reales (`<button>`, `<a>`), no `<div>` con `@click`
- [ ] Si se usa `<div role="button">` excepcionalmente: tiene `tabindex="0"`, manejo de `keydown.enter` y `keydown.space`
- [ ] Botones con solo iconos tienen `aria-label`
- [ ] Links (`<a>`) tienen `href` real o son `<button>`

#### Estructura semántica
- [ ] Uso de `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>` donde corresponda
- [ ] Orden jerárquico de headings (`<h1>` → `<h2>` → `<h3>`) sin saltos
- [ ] `<ul>`/`<ol>` para listas, no `<div>` consecutivos

#### ARIA
- [ ] No hay `role` redundantes (no `role="button"` en `<button>`)
- [ ] `aria-*` attributes válidos y correctos
- [ ] Widgets compuestos (combobox, tabs, modal, dialog) tienen todos los ARIA attributes que el patrón WAI-ARIA exige

#### Focus
- [ ] No hay `outline: none` en CSS sin una alternativa visible (`:focus-visible` con box-shadow o ring)
- [ ] Tabindex coherente (`0` para orden natural; `-1` para elementos programáticamente enfocables; nunca positivos)
- [ ] Modales/diálogos atrapan el focus (focus trap) y lo devuelven al trigger al cerrarse

### Paso 2 — Contraste de colores (si hay cambios en CSS/estilos)

- Si el proyecto usa tokens de Tailwind y los tokens están verificados como accesibles, saltar
- Si hay colores nuevos inline o variables CSS nuevas: calcular contraste
  - Texto normal vs fondo: ≥ 4.5:1
  - Texto grande (≥18pt o 14pt bold): ≥ 3:1
  - UI components (bordes, iconos): ≥ 3:1
- Usar librería como `color-contrast` o implementar WCAG contrast ratio formula

### Paso 3 — Linter eslint-plugin-vuejs-accessibility

Si el proyecto tiene el plugin instalado:
- Ejecutar `npm run lint -- {ficheros-del-diff}` específicamente enfocado en reglas a11y
- Parsear output JSON
- Cada error del plugin → issue con severidad `fail` categoría `a11y-lint`

### Paso 4 — axe-core / pa11y (si tooling disponible)

Si el proyecto tiene `@axe-core/playwright` o `pa11y`:
- Ejecutar contra las rutas afectadas (extraídas del context-digest)
- Requiere que Playwright/entorno esté listo; si no, saltar con warn
- Parsear output, cada violación → issue

```bash
# Ejemplo con @axe-core/playwright en un test:
npx playwright test a11y.spec.ts --grep "{ruta}"
```

Issues de axe con impact:
- `critical` → `fail`
- `serious` → `fail`
- `moderate` → `warn`
- `minor` → `warn`

### Paso 5 — Navegación por teclado (si hay widgets complejos)

Si la tarea introduce un widget compuesto (dropdown, modal, tabs, combobox):
- Verificar que el AC incluye test Playwright que navegue el widget solo con teclado (Tab, Shift+Tab, Enter, Space, Escape, flechas)
- Si no existe → `fail` categoría `a11y-keyboard-test-missing`

## Gravedad

- **FAIL:**
  - Input sin label
  - Imagen informativa sin alt
  - Elemento interactivo no accesible por teclado
  - Contraste < 4.5:1 (texto normal) o < 3:1 (texto grande)
  - `outline: none` sin alternativa de focus visible
  - axe-core severity `critical` o `serious`
- **WARN:**
  - Estructura semántica mejorable (`<div>` donde mejor sería `<section>`)
  - Tab order mejorable
  - axe-core severity `moderate` o `minor`

## Report

```markdown
# a11y-check — T{id}

**Status:** {PASS|FAIL|WARN}
**Nivel WCAG:** AA
**Issues:** {B} bloqueantes, {W} warnings

## Bloqueantes
- [{categoría}] {fichero:línea} {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Rutas probadas con axe
- /signer/{uuid} — 0 critical, 1 moderate
- /dashboard — 0 issues

## Herramientas ejecutadas
- eslint-plugin-vuejs-accessibility: {N} errors
- axe-core: {N} critical/serious
- Contraste (WCAG AA): {N} violaciones
```

## JSON de retorno

```json
{"status":"fail","summary":"1 input sin label + 1 contraste insuficiente","issues":[{"severity":"fail","category":"label-missing","file":"components/SignerForm.vue:42","message":"input type=email sin label asociado"}],"wcagLevel":"AA"}
```

## Qué NO hace

- No corrige los issues — solo reporta
- No audita accesibilidad semántica de contenidos (ej. lenguaje claro, instrucciones comprensibles) — eso requiere revisión humana
- No valida performance (`perf-smoke-frontend`)
- No ejecuta screen readers reales (solo simulación via axe)

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/` (sección nueva a añadir)
- WCAG 2.1 AA: https://www.w3.org/WAI/WCAG21/quickref/
- Vuejs accessibility: https://vuejs.org/guide/best-practices/accessibility.html
