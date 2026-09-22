---
name: design-system-check
description: Validates coherence with the design system in new or modified Vue components and pages. Checks that Tailwind classes use canonical tokens from tailwind.config.ts (colors, spacing, typography, radii, shadows), that there are no unjustified arbitrary values, that the system's base components (Button, Input, Modal, etc.) are reused instead of reimplemented, and that there are no inline styles. Use with /design-system-check T{id}. Trigger with "design system", "tailwind tokens", "check visual coherence", "validate styles".
---

# Design System Check

Design system coherence validation. Only if tags include `ui`. **Not a hard gate** — emits WARN.

## Invocation

```
/design-system-check T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- Task `.md`
- `tailwind.config.ts` (technical source of truth for tokens)
- `.claude/skills/planning-detail/references/wireframe-conventions.md` (semantic reference)
- Optional: `design-system/allowed-arbitrary.json` (whitelist of accepted arbitrary values)
- Declared base components (e.g. `components/base/` or `components/ui/`)

## Outputs

- `var/task-runner/T{id}/design-system-check.report.md`
- JSON: `{"status":"pass|warn","summary":"...","issues":[...],"tokensViolations":N,"inlineStyles":N,"arbitraryValues":N}`

## Precondition

If `tailwind.config.ts` doesn't exist: emit WARN "tokens not defined, design without a system" and return `pass` (nothing to validate against).

## Execution

### Step 1 — Extract canonical tokens

Parse `tailwind.config.ts` (or `tailwind.config.js`):
- List of allowed colors (tokens + their shades)
- Allowed spacing scale (`xs`, `sm`, `md`, ... or numeric values `0, 1, 2, 4, 8, 16, ...`)
- Font sizes (`text-xs`, `text-sm`, ...)
- Border radius (`rounded-sm`, `rounded-md`, ...)
- Shadows (`shadow-sm`, `shadow-md`, ...)
- Breakpoints

Store as sets in memory for comparison.

### Step 2 — Parse Vue files from the diff

For each modified `.vue`, extract:
- `class` attributes from templates
- Classes inside dynamic `:class` (best effort)
- CSS from `<style>` blocks
- Inline styles `style="..."`

### Step 3 — Validate Tailwind classes

For each detected Tailwind class:

#### Arbitrary values `[...]`
- If the class has the format `bg-[#...]`, `p-[13px]`, `text-[14px]`, etc.:
  - Check if it's in `allowed-arbitrary.json` (if it exists)
  - If not → issue `warn` category `arbitrary-value`: "arbitrary value {class}, use a DS token or add to allowed-arbitrary.json with justification"

#### Colors
- `bg-{color}`, `text-{color}`, `border-{color}`, `ring-{color}`, `fill-{color}`, `stroke-{color}`:
  - If `{color}` is not in the tokens (or is not `current`, `transparent`, `black`, `white`) → issue `warn` category `color-off-palette`

#### Spacing
- `p-{n}`, `m-{n}`, `gap-{n}`, `space-{n}`, `inset-{n}`, `top-{n}`, etc.:
  - If `{n}` is not in the allowed spacing scale → issue `warn` category `spacing-off-scale`

#### Typography
- `text-{size}`: must be in the fontSize scale
- `font-{weight}`: must be in the defined weights

#### Radii and shadows
- `rounded-{size}`, `shadow-{level}`: same

### Step 4 — Inline styles

- Grep `style="..."` in templates
- Any occurrence → issue `warn` category `inline-style`: "move to Tailwind classes or `<style>` with variables"
- Documented exception: `style` using design system CSS variables (`style="--width: var(--space-md)"`) is acceptable with justification

### Step 5 — `<style>` blocks in SFCs

- [ ] Use `<style scoped>` (isolated)
- [ ] Design system CSS variables, not raw values
- [ ] Do not override global tokens (`:root { --color-primary: ... }`) — that's the design system's responsibility, not a component's
- [ ] No universal selectors `*`

### Step 6 — Use of base components

Detect whether the new or modified component is reimplementing something that already exists in the design system:

- If there's a `<button class="...">` with 5+ styling classes → probably should use the `<BaseButton />` component (or whatever it's called in the project)
  - Issue `warn` category `component-duplication`
- Same for Input, Modal, Dropdown, Card, etc.

The list of base components is read from `components/base/` or `components/ui/` (directory heuristic).

### Step 7 — Dark mode (if applicable)

If the project supports dark mode (detectable by the presence of `darkMode` in tailwind.config or `dark:*` variants used in existing components):
- [ ] Any class with a light color has its `dark:*` pair when it makes sense
  - Issue `warn` category `dark-mode-missing`

### Step 8 — Breakpoints

- [ ] Consistent use of defined breakpoints (`sm:`, `md:`, `lg:`, `xl:`, `2xl:`)
- Do not use arbitrary values in responsive classes

## Severity

Everything is **WARN by default**. It does not block. The user decides whether to fix or leave it as documented debt in `notes.md`.

Exception: if the task affects the system's base components (e.g. creates a new `<BaseButton>`), the checks become FAIL because the design system must be coherent.

## Report

```markdown
# design-system-check — T{id}

**Status:** {PASS|WARN}
**Violations:** {tokens}: N, {arbitrary}: N, {inline}: N, {duplications}: N

## Warnings
- [{category}] {file:line} {message}

## Tokens extracted from tailwind.config.ts
- Colors: primary-{500,600,700}, neutral-{100..900}, danger-500, ...
- Spacing: xs, sm, md, lg, xl (+ numeric 0,1,2,4,8...)
- FontSize: body, heading-{sm,md,lg}
- Radii: sm, md, lg
- Shadows: card, modal, dropdown

## Refactor suggestions
- components/SignerCard.vue:34 — reimplements Button inline; use <BaseButton />
- pages/dashboard.vue:87 — bg-[#1e3a8a], use bg-primary-500
```

## Return JSON

```json
{"status":"warn","summary":"3 colors off-palette + 1 button reimplementation","issues":[{"severity":"warn","category":"color-off-palette","file":"components/Card.vue:12","message":"bg-[#1e3a8a] → use bg-primary-500"}],"tokensViolations":3,"inlineStyles":0,"arbitraryValues":5}
```

## What it does NOT do

- Does not validate design accessibility (`a11y-check`)
- Does not validate visual performance (`perf-smoke-frontend`)
- Does not apply automatic fixes — only reports
- Does not generate the tokens — assumes they exist in `tailwind.config.ts`

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/` (new section)
- Wireframe conventions: `.claude/skills/planning-detail/references/wireframe-conventions.md`
