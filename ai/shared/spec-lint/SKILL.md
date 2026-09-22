---
name: spec-lint
description: Mechanical completeness validation of a Planning/ task's .md before implementing it. Checks the frontmatter (Complejidad, Tags, Depende de), required sections, the format of Contexto requerido, existence of cited paths, dependency status, and the absence of PENDIENTE/NEEDS CLARIFICATION. Use it with /spec-lint T{id} or /spec-lint {path-to-the-.md}. Trigger with "lint task", "validate definition", "verify task X", "review task .md".
---

# Spec Lint

Entry gate. Runs a deterministic checklist over the task's `.md`.

## Invocation

```
/spec-lint T{id}                    # resolved via Glob
/spec-lint {path to the .md}
```

## Inputs

- Path to the task's `.md` (resolved from the argument)
- Planning root: `Planning/`

## Outputs

- `var/task-runner/T{id}/spec-lint.report.md` (create the directory if it doesn't exist)
- As the last message: single-line JSON
  ```json
  {"status": "pass|fail", "summary": "...", "issues": [{"severity": "fail|warn", "category": "...", "message": "..."}]}
  ```

## Execution

### Step 1 — Read the .md

If it doesn't exist or isn't parseable → return `status: fail` with issue `{"category": "file", "message": "ruta no encontrada"}`.

### Step 2 — Frontmatter

Extract the fields between the title and the first `##` section. Verify:

- [ ] `Story Points`: present, integer > 0
- [ ] `Tipo`: ∈ {Backend, Frontend, Integracion, Infraestructura, Diseno}
- [ ] `Complejidad`: ∈ {baja, media, alta}
- [ ] `Tags`: present, not empty (parse as CSV)
- [ ] `Depende de`: present (the literal value "ninguna" is valid)

Each missing/invalid field → `fail` issue, category `frontmatter`.

### Step 3 — Dependencies

If `Depende de` ≠ "ninguna":
- Parse the list of IDs (format `T{xx}.{y}.{z}`)
- For each ID: look for the `.md` with Glob `Planning/F*-*/EP*-*/S*-*/T{id}-*.md`
- If it doesn't exist → `fail` issue, category `dependency`: "T{id} referenced does not exist"
- If it exists → read its "Seguimiento" table, check `Estado = completed`
  - If it isn't completed → `fail` issue, category `dependency`: "T{id} is in state {X}, must be completed"

### Step 4 — Required sections

Verify that these sections exist and that none of them literally contains `PENDIENTE`:
- `## Descripcion`
- `## Contexto requerido`
- `## Archivos a crear/modificar`
- `## Detalle tecnico`
- `## Tests`

Each failure → `fail` issue, category `section`.

### Step 5 — Contexto requerido

Parse subsections (`### Specs del proyecto`, `### ADRs y decisiones`, etc.). Verify:

- [ ] At least one subsection with non-empty content
- [ ] Each bullet has the format `- <ruta> — <razón>` (dash followed by a non-empty reason)
- [ ] Each cited path exists on disk (resolved relative to the project root)
- [ ] No bullet > 200 chars
- [ ] Total bullets ≤ 15

Paths that do NOT need to be validated on disk (they're conceptual): paths with wildcards `*`, or paths
under `Planning/` with wildcards.

Issues: `fail` for nonexistent paths and formatting; `warn` for >15 bullets and bullets >200 chars.

### Step 6 — Archivos a crear/modificar

- [ ] Table present with header `| Archivo | Accion |` or similar
- [ ] At least one row
- [ ] At least one path under `tests/` (exception: if `Tipo: Diseno` or `Tipo: Infraestructura`)

### Step 7 — Tests

- [ ] Table present
- [ ] At least one row (exception: `Tipo: Diseno`)

### Step 8 — AC cross-references

Search for mentions of `AC-\d+` in the `.md`. For each one:
- Look for the parent story's `README.md` (the immediate parent directory)
- Verify that the mentioned AC exists with that number in the story
- If it doesn't exist → `fail` issue, category `ac-reference`

### Step 9 — Uncertainty markers

Grep for the text `[NEEDS CLARIFICATION` across the whole `.md`. Any occurrence → `fail` issue, category
`clarification`.

## Report generation

`var/task-runner/T{id}/spec-lint.report.md`:

```markdown
# spec-lint — T{id}

**Status:** {PASS|FAIL}
**Issues:** {N} ({B} blocking, {W} warnings)

## Blocking
- [{category}] {message}

## Warnings
- [{category}] {message}

## Passed checks
- Complete frontmatter
- {other checks that passed}
```

## Return JSON

The last line of your response must be a valid single-line JSON:

```json
{"status":"fail","summary":"3 issues (2 fail, 1 warn)","issues":[{"severity":"fail","category":"dependency","message":"T02.1.0 en estado pendiente"},{"severity":"fail","category":"section","message":"Contexto requerido contiene PENDIENTE"},{"severity":"warn","category":"contexto-size","message":"17 bullets (>15)"}]}
```

## What it does NOT do

- Does not validate semantic quality of the content (only format and existence)
- Does not modify the `.md`
- Does not run tests or code
- Does not resolve the issues — only reports them

## References

- Full design: `Implementación/Skills de Ejecución de Tareas/common/02 - Spec Lint.md`
