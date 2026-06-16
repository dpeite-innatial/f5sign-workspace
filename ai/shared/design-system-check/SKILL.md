---
name: design-system-check
description: Valida coherencia con el design system en componentes y páginas Vue nuevos o modificados. Comprueba que las clases Tailwind usan tokens canónicos de tailwind.config.ts (colores, spacing, tipografía, radios, sombras), que no hay valores arbitrarios sin justificación, que los componentes base del sistema (Button, Input, Modal, etc.) se reutilizan en lugar de reimplementar, y que no hay estilos inline. Úsalo con /design-system-check T{id}. Activar con "design system", "tokens tailwind", "check coherencia visual", "validar estilos".
---

# Design System Check

Validación de coherencia con el design system. Solo si tags incluye `ui`. **No es gate duro** — emite WARN.

## Invocación

```
/design-system-check T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `.md` de la tarea
- `tailwind.config.ts` (fuente de verdad técnica de tokens)
- `.claude/skills/planning-detail/references/wireframe-conventions.md` (referencia semántica)
- Opcional: `design-system/allowed-arbitrary.json` (lista blanca de valores arbitrarios aceptados)
- Componentes base declarados (ej. `components/base/` o `components/ui/`)

## Outputs

- `var/task-runner/T{id}/design-system-check.report.md`
- JSON: `{"status":"pass|warn","summary":"...","issues":[...],"tokensViolations":N,"inlineStyles":N,"arbitraryValues":N}`

## Precondición

Si no existe `tailwind.config.ts`: emitir WARN "tokens no definidos, diseño sin sistema" y devolver `pass` (no hay contra qué validar).

## Ejecución

### Paso 1 — Extraer tokens canónicos

Parsear `tailwind.config.ts` (o `tailwind.config.js`):
- Lista de colores permitidos (tokens + sus shades)
- Escala de spacing permitida (`xs`, `sm`, `md`, ... o valores numéricos `0, 1, 2, 4, 8, 16, ...`)
- Tamaños de fuente (`text-xs`, `text-sm`, ...)
- Border radius (`rounded-sm`, `rounded-md`, ...)
- Sombras (`shadow-sm`, `shadow-md`, ...)
- Breakpoints

Guardar como sets en memoria para comparación.

### Paso 2 — Parsear ficheros Vue del diff

Para cada `.vue` modificado, extraer:
- Atributos `class` de los templates
- Clases dentro de `:class` dinámico (mejor esfuerzo)
- CSS de bloques `<style>`
- Estilos inline `style="..."`

### Paso 3 — Validar clases Tailwind

Para cada clase Tailwind detectada:

#### Valores arbitrarios `[...]`
- Si la clase tiene formato `bg-[#...]`, `p-[13px]`, `text-[14px]`, etc.:
  - Comprobar si está en `allowed-arbitrary.json` (si existe)
  - Si no → issue `warn` categoría `arbitrary-value`: "valor arbitrario {clase}, usar token del DS o añadir a allowed-arbitrary.json con justificación"

#### Colores
- `bg-{color}`, `text-{color}`, `border-{color}`, `ring-{color}`, `fill-{color}`, `stroke-{color}`:
  - Si `{color}` no está en tokens (o no es `current`, `transparent`, `black`, `white`) → issue `warn` categoría `color-off-palette`

#### Spacing
- `p-{n}`, `m-{n}`, `gap-{n}`, `space-{n}`, `inset-{n}`, `top-{n}`, etc.:
  - Si `{n}` no está en la escala de spacing permitida → issue `warn` categoría `spacing-off-scale`

#### Tipografía
- `text-{size}`: debe estar en la escala de fontSize
- `font-{weight}`: debe estar en los pesos definidos

#### Radios y sombras
- `rounded-{size}`, `shadow-{level}`: idem

### Paso 4 — Estilos inline

- Grep `style="..."` en templates
- Cualquier ocurrencia → issue `warn` categoría `inline-style`: "mover a clases Tailwind o `<style>` con variables"
- Excepción documentada: `style` que usa variables CSS del design system (`style="--width: var(--space-md)"`) es aceptable con justificación

### Paso 5 — Bloques `<style>` en SFCs

- [ ] Usan `<style scoped>` (aislados)
- [ ] Variables CSS del design system, no valores crudos
- [ ] No sobrescriben tokens globales (`:root { --color-primary: ... }`) — eso es responsabilidad del design system, no de un componente
- [ ] Selectores universales `*` fuera

### Paso 6 — Uso de componentes base

Detectar si el componente nuevo o modificado está reimplementando algo que ya existe en el design system:

- Si hay `<button class="...">` con 5+ clases de styling → probablemente debería usar el componente `<BaseButton />` (o como se llame en el proyecto)
  - Issue `warn` categoría `component-duplication`
- Lo mismo para Input, Modal, Dropdown, Card, etc.

La lista de componentes base se lee de `components/base/` o `components/ui/` (heurística por directorio).

### Paso 7 — Dark mode (si aplica)

Si el proyecto soporta dark mode (detectable por presencia de `darkMode` en tailwind.config o variantes `dark:*` usadas en componentes existentes):
- [ ] Cualquier clase con color ligh tiene su pareja `dark:*` cuando tiene sentido
  - Issue `warn` categoría `dark-mode-missing`

### Paso 8 — Breakpoints

- [ ] Uso consistente de breakpoints definidos (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`)
- No usar valores arbitrarios en clases responsive

## Gravedad

Todo es **WARN por defecto**. No bloquea. El usuario decide si arreglar o dejar como deuda documentada en `notes.md`.

Excepción: si la tarea afecta a componentes base del sistema (ej. crea un nuevo `<BaseButton>`), los checks pasan a FAIL porque el design system debe ser coherente.

## Report

```markdown
# design-system-check — T{id}

**Status:** {PASS|WARN}
**Violaciones:** {tokens}: N, {arbitrary}: N, {inline}: N, {duplications}: N

## Warnings
- [{categoría}] {fichero:línea} {mensaje}

## Tokens extraídos de tailwind.config.ts
- Colores: primary-{500,600,700}, neutral-{100..900}, danger-500, ...
- Spacing: xs, sm, md, lg, xl (+ numéricos 0,1,2,4,8...)
- FontSize: body, heading-{sm,md,lg}
- Radii: sm, md, lg
- Shadows: card, modal, dropdown

## Sugerencias de refactor
- components/SignerCard.vue:34 — reimplementa Button inline; usar <BaseButton />
- pages/dashboard.vue:87 — bg-[#1e3a8a], usar bg-primary-500
```

## JSON de retorno

```json
{"status":"warn","summary":"3 colores fuera de paleta + 1 reimplementación de botón","issues":[{"severity":"warn","category":"color-off-palette","file":"components/Card.vue:12","message":"bg-[#1e3a8a] → usar bg-primary-500"}],"tokensViolations":3,"inlineStyles":0,"arbitraryValues":5}
```

## Qué NO hace

- No valida accesibilidad del diseño (`a11y-check`)
- No valida performance visual (`perf-smoke-frontend`)
- No aplica fixes automáticos — solo reporta
- No genera los tokens — asume que existen en `tailwind.config.ts`

## Referencias

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/` (nueva sección)
- Wireframe conventions: `.claude/skills/planning-detail/references/wireframe-conventions.md`
