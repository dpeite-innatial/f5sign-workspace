---
name: a11y-check
description: Validates accessibility (WCAG 2.1 AA) of Vue components and pages that are new or modified after a frontend task. Runs axe-core/pa11y, checks color contrast, input labels, image alt text, keyboard navigation, correct ARIA roles and visible focus. Hard gate when there are visual changes. Use with /a11y-check T{id}. Trigger with "accessibility", "a11y", "WCAG", "check aria/alt/labels".
---

# A11y Check

Accessibility validation. Only if tags include `ui`. Hard gate.

## Invocation

```
/a11y-check T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- Task `.md`
- Vue files from the diff

## Outputs

- `var/task-runner/T{id}/a11y-check.report.md`
- `var/task-runner/T{id}/a11y-axe.json` (raw axe output if run)
- JSON: `{"status":"pass|fail|warn","summary":"...","issues":[...],"wcagLevel":"AA"}`

## Precondition

If the project doesn't have `axe-core`/`@axe-core/playwright` or `pa11y` installed → WARN "a11y tooling not available" and continue with the static checks (eslint-plugin-vuejs-accessibility linter if present). Do not block.

## Execution

### Step 1 — Static checks on Vue files from the diff

For each modified `*.vue`:

#### Labels and forms
- [ ] Every `<input>`, `<select>`, `<textarea>` has an associated `<label for="...">` or `aria-label`/`aria-labelledby`
- [ ] `checkbox`/`radio` inputs have clickable labels
- [ ] Forms have `<fieldset>`/`<legend>` when grouping related controls
- [ ] Error messages have `aria-live="polite"` or `role="alert"` and are linked to the input with `aria-describedby`

#### Images and media
- [ ] `<img>` has `alt` (empty if decorative, descriptive if informative)
- [ ] Decorative icons have `aria-hidden="true"` and `alt=""`
- [ ] Informative icons have `aria-label` or associated visible text

#### Buttons and interactivity
- [ ] Interactive elements are real buttons (`<button>`, `<a>`), not `<div>` with `@click`
- [ ] If `<div role="button">` is used exceptionally: it has `tabindex="0"`, handling of `keydown.enter` and `keydown.space`
- [ ] Icon-only buttons have `aria-label`
- [ ] Links (`<a>`) have a real `href` or are `<button>`

#### Semantic structure
- [ ] Use of `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>` where appropriate
- [ ] Hierarchical heading order (`<h1>` → `<h2>` → `<h3>`) without skips
- [ ] `<ul>`/`<ol>` for lists, not consecutive `<div>`s

#### ARIA
- [ ] No redundant `role`s (no `role="button"` on `<button>`)
- [ ] `aria-*` attributes valid and correct
- [ ] Composite widgets (combobox, tabs, modal, dialog) have all the ARIA attributes required by the WAI-ARIA pattern

#### Focus
- [ ] No `outline: none` in CSS without a visible alternative (`:focus-visible` with box-shadow or ring)
- [ ] Coherent tabindex (`0` for natural order; `-1` for programmatically focusable elements; never positive)
- [ ] Modals/dialogs trap focus (focus trap) and return it to the trigger on close

### Step 2 — Color contrast (if there are CSS/style changes)

- If the project uses Tailwind tokens and the tokens are verified as accessible, skip
- If there are new inline colors or new CSS variables: calculate contrast
  - Normal text vs background: ≥ 4.5:1
  - Large text (≥18pt or 14pt bold): ≥ 3:1
  - UI components (borders, icons): ≥ 3:1
- Use a library such as `color-contrast` or implement the WCAG contrast ratio formula

### Step 3 — eslint-plugin-vuejs-accessibility linter

If the project has the plugin installed:
- Run `npm run lint -- {diff-files}` specifically focused on a11y rules
- Parse JSON output
- Each plugin error → issue with severity `fail`, category `a11y-lint`

### Step 4 — axe-core / pa11y (if tooling available)

If the project has `@axe-core/playwright` or `pa11y`:
- Run against the affected routes (extracted from context-digest)
- Requires Playwright/the environment to be ready; if not, skip with warn
- Parse output, each violation → issue

```bash
# Example with @axe-core/playwright in a test:
npx playwright test a11y.spec.ts --grep "{route}"
```

axe issues by impact:
- `critical` → `fail`
- `serious` → `fail`
- `moderate` → `warn`
- `minor` → `warn`

### Step 5 — Keyboard navigation (if there are complex widgets)

If the task introduces a composite widget (dropdown, modal, tabs, combobox):
- Verify that the AC includes a Playwright test that navigates the widget using only the keyboard (Tab, Shift+Tab, Enter, Space, Escape, arrows)
- If it doesn't exist → `fail` category `a11y-keyboard-test-missing`

## Severity

- **FAIL:**
  - Input without a label
  - Informative image without alt
  - Interactive element not keyboard-accessible
  - Contrast < 4.5:1 (normal text) or < 3:1 (large text)
  - `outline: none` without a visible focus alternative
  - axe-core severity `critical` or `serious`
- **WARN:**
  - Semantic structure could be improved (`<div>` where `<section>` would be better)
  - Tab order could be improved
  - axe-core severity `moderate` or `minor`

## Report

```markdown
# a11y-check — T{id}

**Status:** {PASS|FAIL|WARN}
**WCAG level:** AA
**Issues:** {B} blocking, {W} warnings

## Blocking
- [{category}] {file:line} {message}

## Warnings
- [{category}] {message}

## Routes tested with axe
- /signer/{uuid} — 0 critical, 1 moderate
- /dashboard — 0 issues

## Tools run
- eslint-plugin-vuejs-accessibility: {N} errors
- axe-core: {N} critical/serious
- Contrast (WCAG AA): {N} violations
```

## Return JSON

```json
{"status":"fail","summary":"1 input without label + 1 insufficient contrast","issues":[{"severity":"fail","category":"label-missing","file":"components/SignerForm.vue:42","message":"input type=email without associated label"}],"wcagLevel":"AA"}
```

## What it does NOT do

- Does not fix issues — only reports
- Does not audit content semantic accessibility (e.g. plain language, understandable instructions) — that requires human review
- Does not validate performance (`perf-smoke-frontend`)
- Does not run real screen readers (only simulation via axe)

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/` (new section to be added)
- WCAG 2.1 AA: https://www.w3.org/WAI/WCAG21/quickref/
- Vuejs accessibility: https://vuejs.org/guide/best-practices/accessibility.html
