---
name: task-validate-backend
description: 'Gate duro de calidad funcional en backend (PHP/Symfony): corre la suite (composer test), PHPStan nivel 9, Deptrac, lint, y mide fuerza estructural con covered-MSI de Infection en vez de porcentaje de líneas. Recomputa la separación entre BCs sobre el propio deptrac.yaml (solo Contract/ ajeno, nada depende de Notification, Kernel sin dependencias) porque una allowlist ampliada no produce violación alguna, reporta el delta de cualquier regla relajada y exige el ADR que la declare, y comprueba que un ADR que aterriza lo hace completo. Comprueba que las propiedades declaradas en §Verification de la task se ejecutan de verdad, y que el diff no se sale de su §Scope. Solo para repositorios con stack PHP/Symfony. Úsalo con /task-validate-backend TASK-NNN. Activar con "validar tarea backend", "run phpunit", "check PHPStan y deptrac".'
---

# Task Validate (backend)

Gate duro de calidad funcional. Se invoca siempre.

## Invocación

```
/task-validate-backend TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff`
- El `.md` de la task — en particular **§3 Scope** y **§5 Verification** (formato en
  [`docs/tasks/README.md`](../../../docs/tasks/README.md))

## Outputs

- `var/task-runner/TASK-NNN/validate.report.md`
- `var/task-runner/TASK-NNN/test-results.xml` (JUnit)
- JSON: `{"status":"pass|fail","summary":"...","issues":[...],"harness":"...","msi":0.91,"propertiesUnproven":[]}`

## Precondición crítica — declarar el harness, y comprobar que apunta a TU árbol

Los servicios que la suite necesita (Postgres, RabbitMQ, MinIO, Mailpit) los levanta
`../f5sign-infra`. **Nunca `docker compose` desde este repo** (regla 5). Y antes de correr nada:

⚑ **`f5sign-infra/docker-compose.override.yml` monta `../f5sign-backend`.** Si trabajas en un worktree
enlazado, `make test` valida el otro árbol y su verde no dice nada de tu código. Elegir vía y **escribirla
en el campo `harness` del JSON**:

| Vía | Sirve para | Limitación conocida |
|---|---|---|
| `make -C ../f5sign-infra test` | El checkout principal | Valida `../f5sign-backend`, no un worktree |
| `make -C ../f5sign-infra wt-backend src=$(pwd)` | Un worktree | Solo postgres: storage **falla** (`host: minio`), broker se salta, y `composer test` muere en el timeout de 300 s de Composer |
| `docker run --rm --network f5sign-net -v $(pwd):/var/www/html -w /var/www/html f5sign/backend:dev sh -c 'php -d memory_limit=-1 bin/phpunit --no-progress'` | Un worktree, suite completa | Requiere el stack arriba; migra antes contra `postgres-test` |

Si un servicio está caído durante la ejecución → `status: fail`, `summary: "infrastructure unavailable: X"`.
**No reintentar automáticamente, y no confundirlo con un fallo de código:** el síntoma clásico es
`Connection could not be established with host` (Mailpit desconectado de la red) o
`Could not resolve host: minio`. Ambos son entorno, no regresión.

## Ejecución

### Paso 1 — Suite

```bash
composer test        # un solo tier; NO existen test:unit / test:integration / test:e2e
```

Los tiers de este repo son **directorios**, no scripts (ADR-0035): `Unit/`, `Application/` (herméticos),
`Integration/` (DB real, rollback DAMA), `Acceptance/` (HTTP). Para acotar:
`vendor/bin/phpunit --testsuite <name>` o `--filter`.

- [ ] Exit code 0.
- [ ] Los tests que §5 Verification nombra **existen y se han ejecutado** (buscarlos por nombre en el
      JUnit). Un test nombrado en la task y ausente del run es `fail` categoría `property-unproven`.

### Paso 2 — Fuerza estructural: covered-MSI, no porcentaje de líneas

```bash
composer infection
```

**Este repo no tiene umbral de cobertura de líneas y no se debe inventar uno.** El gate es el covered-MSI
de Infection (ADR-0035). `composer coverage:text` / `coverage:clover` existen para inspección, no como bar.

- Covered-MSI por debajo del umbral → `fail`. El número lo declara `infection.json5.dist`
  (`minCoveredMsi`); leerlo de ahí, no de aquí ni de memoria.
- ⚠ **Infection no ve código sin llamantes**, y su `source` es `src/F5Sign` solamente. Un artefacto nuevo
  sin ningún llamante puntúa como si no existiera, y el test de una regla PHPStan propia (que vive en
  `phpstan/`) es su **única** guarda. Si el diff añade superficie en esas zonas, decirlo en el report en vez
  de dejar que el MSI hable por ella.

### Paso 3 — Estático y arquitectura

```bash
composer phpstan     # nivel 9
composer arch        # Deptrac: contrato de visibilidad entre capas y BCs
composer lint        # PHP-CS-Fixer en modo check
```

- [ ] PHPStan sin errores nuevos. **No ampliar `phpstan-baseline.neon` para pasar el gate**: cada entrada
      del baseline es un hallazgo de diseño con su *por qué* escrito. Añadir una es una decisión, no un fix.
- [ ] Deptrac sin violaciones. **No tiene baseline**: una violación se reporta como hallazgo, no se silencia.
- [ ] Lint limpio.
- [ ] Si el diff añade tests: llevan `#[CoversClass]` o `#[CoversNothing]` (`phpunit.dist.xml` tiene
      `requireCoverageMetadata="true"`), y `#[UsesClass]` para colaboradores, incluidas las excepciones que
      el test asserta.

### Paso 3b — La separación entre dominios, afirmada en vez de contada

`composer arch` responde *"¿hay violaciones?"*, y hay dos formas de que responda **no** sin que la
propiedad se cumpla. Este paso cubre las dos.

**a) El delta de la allowlist.** Si el diff toca [`deptrac.yaml`](../../../deptrac.yaml) (capas o ruleset),
`phpstan.dist.neon`, o añade entradas a `phpstan-baseline.neon`:

- [ ] **Reportar el delta en prosa**, no solo "fichero tocado": qué capa gana qué dependencia, qué regla se
      relaja, qué hallazgo se silencia. Es la única forma de que un reviewer lo vea.
- [ ] **Exigir ADR citado en el changeset** → si no hay: `fail`, categoría `undeclared-decision`. Ampliar
      la allowlist para que el gate pase **es la decisión**, no el arreglo (`implement-backend` Paso 2b).

**b) Las reglas con forma de ausencia, recomputadas.** Un ruleset ampliado no produce violación alguna:
la regla desaparece en silencio. Recomputar directamente sobre `deptrac.yaml`:

- [ ] **Ninguna capa fuera de Notification depende de una capa `Notification*`** — ADR-0037, BC de soporte
      de categoría (c). Medido 2026-08-17: cero. Si aparece una, `fail` aunque `composer arch` esté verde.
- [ ] **Ningún BC ve de otro BC nada que no sea su `Contract`** — ninguna lista de dependencias nombra un
      `…Domain`, `…Application`, `…Infrastructure` o `…UI` de otro BC.
- [ ] **`Kernel: []`** sigue sin depender de nada.

Estos tres se comprueban leyendo el ruleset, no ejecutando Deptrac: son afirmaciones sobre el **fichero de
reglas**, y por eso sobreviven a que alguien lo edite.

### Paso 3c — Un ADR que aterriza, aterriza completo

Si el diff añade o cambia el estado de un `docs/adr/ADR-*.md`:

- [ ] `Status` no es `Accepted` a menos que la decisión esté **ejercitada** en este mismo diff — en este set
      *Accepted* significa ejercitado, no acordado.
- [ ] Están las **tres** ediciones de [`docs/adr/README.md`](../../../docs/adr/README.md): fila de índice,
      grafo de relaciones, fila de crosswalk. Falta alguna → `fail`, categoría `adr-index-incomplete`.
- [ ] Está el campo `Crosswalk` de la cabecera y las secciones que exige `AUTHORING.md`
      (`Consequences` con **Risks**, `Enforced by`, `Realized in`).
- [ ] Si el diff hace cierto algo que otro ADR daba por pendiente, **ese** ADR mueve su
      `Status` / `Enforced by` / `Realized in` aquí y no después.

### Paso 4 — Las propiedades declaradas se prueban de verdad

Por cada afirmación de §5 Verification, comprobar que **el harness elegido puede verla**. Es el paso que
distingue esta skill de "correr la suite", y existe porque el repo ha shippeado guardas verdes que nada
ejecutaba (`CLAUDE.md` regla de autoría 4):

- **Locks de fila**: `Integration/` corre **una conexión** bajo rollback DAMA, así que con y sin
  `FOR UPDATE` es indistinguible. Se necesita una segunda conexión
  ([`ProbesRowLocks`](../../../tests/F5Sign/Support/ProbesRowLocks.php)).
- **Redelivery / reintentos**: `async_events` es `in-memory://` en test; nada se reentrega.
- **Identidad tras serializar**: un fake que devuelve la instancia que guardó no prueba nada de `save()`.
- **Fixtures que no discriminan**: si dos variables siempre concuerdan en los datos de prueba, una
  proyección que filtra por la equivocada pasa igual. Exigir el caso donde **discrepan**.

Lo que no pueda probarse con este harness va a `propertiesUnproven` y es `fail` si §5 lo declaraba probado.

### Paso 5 — El diff no se sale del §Scope

Este formato de task **no lleva tabla de "Archivos a crear/modificar"** (eso era el `Planning/` legado).
La diana es la prosa de §3 Scope, con su lista **In** y su lista **Out**:

- `git diff --name-only $(git merge-base HEAD develop)..HEAD`.
- [ ] Nada del diff cae en algo que §3 declara **Out** → si cae: `fail` categoría `out-of-scope`.
- [ ] Ficheros fuera de lo que §3 anticipaba pero no prohibidos: `warn` categoría `undeclared-file`.
- ⚑ Si el cambio re-corta o renombra un concepto, comprobar el barrido de la regla 1:
      `rg -n '<término retirado>' src tests migrations docs config CLAUDE.md`. Un fichero que aún necesita
      la edición aparece con **diff vacío**, así que el diff no es la superficie de búsqueda.

### Paso 6 — Migraciones (si el diff toca `migrations/`)

```bash
make -C ../f5sign-infra sf cmd="doctrine:migrations:migrate --dry-run --no-interaction"
```

- [ ] Sin errores, y reversible.
- [ ] Si la migración **escribe filas que el dominio luego lee**, es `doctrine-guard` quien lo audita
      (regla de autoría 6); aquí basta con marcarlo en el report para que no se pierda.

## Report

```markdown
# task-validate-backend — TASK-NNN

**Status:** {PASS|FAIL}
**Harness:** {la vía elegida, literal}
**Tests:** {passed} passed, {failed} failed, {skipped} skipped
**Covered-MSI:** {%} (umbral ADR-0035)
**PHPStan:** {N} errores nuevos · **Deptrac:** {N} violaciones · **Lint:** {N}

## Separación de dominios
- Contract-only entre BCs: {ok | la capa X gana Y}
- Nada depende de Notification: {ok | X → NotificationZ}
- `Kernel: []`: {ok | depende de X}
- Reglas relajadas en este diff: {ninguna | el delta en prosa + el ADR que lo declara}

## Propiedades declaradas y no probadas
- {afirmación de §5} → el harness no la alcanza porque {razón}

## Fuera de §Scope
- {lista o "ninguno"}

## Servicios no disponibles
- {lista o "ninguno"} (entorno, no regresión)
```

## Qué NO hace

- No audita seguridad, compliance ni performance.
- No escribe tests que falten — solo detecta que faltan.
- No corrige código ni tests.
- No amplía baselines para pasar.

## Protocolo de corrección

Si `task-runner` reintenta con este report como input, la instrucción es *"corregir los issues sin cambiar
el scope"*. Máximo 2 iteraciones automáticas; al tercer intento, intervención humana.
