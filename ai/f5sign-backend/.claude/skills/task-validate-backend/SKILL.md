---
name: task-validate-backend
description: 'Gate duro de calidad funcional en backend (PHP/Symfony): corre la suite (composer test), PHPStan nivel 9, Deptrac, lint, y mide fuerza estructural con covered-MSI de Infection en vez de porcentaje de líneas. Vigila el diff de deptrac.yaml/phpstan y comprueba que las cuatro formas load-bearing del ruleset siguen intactas — el gate sí caza una dependencia prohibida, pero no puede cazar que alguien amplíe la allowlist para permitirla — reportando el delta y exigiendo el ADR que lo declare, y comprueba que un ADR que aterriza lo hace completo. Comprueba que las propiedades declaradas en §Verification de la task se ejecutan de verdad, y que el diff no se sale de su §Scope. Solo para repositorios con stack PHP/Symfony. Úsalo con /task-validate-backend TASK-NNN. Activar con "validar tarea backend", "run phpunit", "check PHPStan y deptrac".'
---

# Task Validate (backend)

Gate duro de calidad funcional. Se invoca siempre.

## Invocación

```
/task-validate-backend TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff`
- El `.md` de la task — sus secciones de **alcance** y **verificación**, localizadas por intención: no están
  en `§3` y `§5` de forma fiable (medido: alcance en §3 en 13 de 21; verificación en §5 en 7 de 21)

## Outputs

- `var/task-runner/TASK-NNN/validate.report.md`
- `var/task-runner/TASK-NNN/test-results.xml` (JUnit) — ⚠ **solo si lo pides explícitamente**:
  `phpunit.dist.xml` no tiene bloque `<logging>` y `composer test` no pasa `--log-junit`, así que la orden
  del Paso 1 tal cual **no produce ningún fichero**. Para el cruce con la sección de verificación, añade
  `--log-junit var/task-runner/TASK-NNN/test-results.xml` a la invocación de phpunit, o lee los nombres del
  stdout
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
| `make -C ../f5sign-infra wt-backend src=$(pwd)` | Un worktree | Solo postgres: storage **falla** (`host: minio`) y broker se salta. Muere además en el timeout de 300 s de Composer, pero **no por la duración de la suite** (~74 s medidos aparte): mete install + migraciones + suite en un proceso |
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
`Integration/` (DB real, rollback DAMA), `Acceptance/` (HTTP). ⚠ **Para acotar, `--filter`, no
`--testsuite`**: `phpunit.dist.xml` declara exactamente dos suites, `default` (todo `tests/`) y
`phpstan-rules` (`phpstan/tests`), y **ninguna es un tier**. `tests/README.md` registra las suites por tier
como *"(target)"*, o sea no construidas: `--testsuite Unit` da error.

- [ ] Exit code 0.
- [ ] Los tests que la sección de verificación nombra **existen y se han ejecutado** (buscarlos por nombre en el
      JUnit). Un test nombrado en la task y ausente del run es `fail` categoría `property-unproven`.

### Paso 2 — Fuerza estructural: covered-MSI, no porcentaje de líneas

```bash
composer infection
```

**Este repo no tiene umbral de cobertura de líneas y no se debe inventar uno.** El gate es el covered-MSI
de Infection (ADR-0035). `composer coverage:text` / `coverage:clover` existen para inspección, no como bar.

- **Son DOS puertas y `composer infection` falla con cualquiera de las dos.** `infection.json5.dist`
  declara `minCoveredMsi` (profundidad: de lo cubierto, cuánto resiste) **y `minMsi`** (amplitud: incluye lo
  no cubierto). Leer los dos números de ahí, no de aquí ni de memoria.
- ⛔ **Si cae `minMsi`, no lo repares atribuyendo los flujos anchos.** El propio fichero lo advierte: *"the
  cheapest way to raise MSI is to attribute the broad flows"* — y eso deshace la regla de dos tiers de
  ADR-0035. El arreglo es test, no atribución.
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

**b) Las cuatro formas load-bearing de `deptrac.yaml`, leídas como datos.**

⚠ **Corregido 2026-08-17, y la corrección importa:** una versión anterior de este paso decía que estas
reglas *"no pueden ponerse rojas"*. Falso. El `ruleset` es una **allowlist positiva** y el repo corre con
`Uncovered 0 / Allowed 3755`, así que una clase que dependa de una capa no permitida **sí** produce
`DependsOnDisallowedLayer`. Lo que no puede ponerse rojo es **ampliar la allowlist**: eso no viola nada,
simplemente deja de vigilar. Por eso el check real es el (a) de arriba —mirar el diff del fichero— más
comprobar que estas cuatro formas siguen intactas:

- [ ] **`Kernel: []`** — no depende de nada.
- [ ] **`Foundation: [Kernel, Vendor]` y nada más.** `LOAD-BEARING.md` §1.13 la marca como *"la más probable
      de todas de deshacerse, y por razón mecánica: un ruleset relajado no falla nada"*. Añadirle un
      `…Contract` disuelve la inversión de dependencia que ADR-0044 existe para forzar.
- [ ] **Entre BCs, solo `…Contract`** — ninguna lista nombra un `Domain`/`Application`/`Infrastructure`/`UI`
      ajeno. Y ninguna capa fuera de Notification nombra una `Notification*` (ADR-0037).
- [ ] **`IdentityAccessApplication` e `IdentityAccessInfrastructure` tienen lista de hermanos VACÍA**
      (ADR-0044, `LOAD-BEARING.md` §1.11). *"Completarla por simetría"* —porque parece un olvido al lado de
      once listas pobladas— es el modo de destrucción documentado.

⚑ **Y el collector `Vendor` es una allowlist de namespaces**, así que un vendor que no esté en su regex no
pertenece a ninguna capa y un `Domain/` puede importarlo sin violar nada. Hoy `Lexik\` está en
`composer.json` y **no** en la regex. Si el diff añade una dependencia de vendor, comprobar que su namespace
entra en el collector.

### Paso 3c — Un ADR que aterriza, aterriza completo

Si el diff añade o cambia el estado de un `docs/adr/ADR-*.md`:

- [ ] `Status` no es `Accepted` a menos que la decisión esté **ejercitada** en este mismo diff — en este set
      *Accepted* significa ejercitado, no acordado.
- [ ] Están las **tres** ediciones de [`docs/adr/README.md`](../../../docs/adr/README.md): fila de índice,
      grafo de relaciones, fila de crosswalk. Falta alguna → `fail`, categoría `adr-index-incomplete`.
- [ ] Y las **dos que `AUTHORING.md` llama fáciles de olvidar**, porque son cinco sitios en total: la
      referencia `(ADR-NNNN)` en los docblocks del código que gobierna (*"only the pair makes the decision
      discoverable in both directions"*), y la reconciliación del modelo de dominio en `docs/ddd/` **más su
      fila de estado** en `docs/ddd/README.md`.
- [ ] Está el campo `Crosswalk` de la cabecera y las secciones que exige `AUTHORING.md`
      (`Consequences` con **Risks**, `Enforced by`, `Realized in`).
- [ ] Si el diff hace cierto algo que otro ADR daba por pendiente, **ese** ADR mueve su
      `Status` / `Enforced by` / `Realized in` aquí y no después.

### Paso 4 — Las propiedades declaradas se prueban de verdad

Por cada afirmación de la sección de verificación, comprobar que **el harness elegido puede verla**. Es el paso que
distingue esta skill de "correr la suite", y existe porque el repo ha shippeado guardas verdes que nada
ejecutaba (`CLAUDE.md` regla de autoría 4):

- **Locks de fila**: `Integration/` corre **una conexión** bajo rollback DAMA, así que con y sin
  `FOR UPDATE` es indistinguible. Se necesita una segunda conexión
  ([`ProbesRowLocks`](../../../tests/F5Sign/Support/ProbesRowLocks.php)).
- **Redelivery / reintentos**: `async_events` es `in-memory://` en test; nada se reentrega.
- **Identidad tras serializar**: un fake que devuelve la instancia que guardó no prueba nada de `save()`.
- **Fixtures que no discriminan**: si dos variables siempre concuerdan en los datos de prueba, una
  proyección que filtra por la equivocada pasa igual. Exigir el caso donde **discrepan**.

- **Redelivery / reintentos**: `async_events` es `in-memory://` en test… **pero no es toda la verdad**:
  `when@test` declara además dos transportes AMQP reales (`async_events_amqp`,
  `async_events_unroutable_amqp`) para que los tests de broker alcancen propiedades de redelivery. Antes de
  declarar una propiedad inalcanzable, comprobar si le sirve uno de esos.
- ⚑ **La probe de locks necesita `#[SkipDatabaseRollback]`.** Su propio docblock lo dice: sin ese atributo la
  conexión estática de DAMA da a cada "sesión" la misma conexión física, **y un lock nunca choca consigo
  mismo**. Añadirla sin él reproduce el verde-que-no-prueba-nada que este paso existe para cazar.

**Dos formas de contaminar el run que hacen que un VERDE no valga nada** (`tests/README.md` § *Two ways to
get an untrustworthy run*):

- [ ] **`worker` o `relay` arriba durante la suite**: consumidores compitiendo en el mismo broker, se comen
      los mensajes que el test espera. `make worker-down`, confirmar con `make worker-status`. `ensure-stack`
      **no** lo comprueba.
- [ ] **Dos `phpunit` a la vez contra la misma DB de test**: el aislamiento de DAMA es por *conexión*, no por
      proceso — *"falla cerca del 100 % de las veces y se parece exactamente a una tormenta de flakes"*.
- [ ] Entorno: `ensure-stack` exige `redis` (que los tests no usan, `LOCK_DSN=flock`) y **no** exige `minio`
      (que sí usan), así que `make test` puede arrancar en verde con el storage caído.

⚑ **Antes de rehacer a mano una comprobación estructural, mira si ya hay un test que la cierra.** Dos existen
y ninguno de estos pasos los sustituye:
[`OpenApiSpecTest`](../../../tests/F5Sign/Acceptance/OpenApiSpecTest.php) cierra el conjunto de claves del
spec **en las dos direcciones**, con control positivo, y censa cada enum publicado; y
[`SchemaConformanceTest`](../../../tests/F5Sign/Integration/SchemaConformanceTest.php) afirma el scoping por
tenant y la RLS canónica contra la DB viva, con su taxonomía de exenciones. **Ejecútalos y lee su salida en
vez de reproducirlos**; si falta un caso, se añade allí.

Lo que no pueda probarse con este harness va a `propertiesUnproven` y es `fail` si la task lo declaraba probado.

### Paso 5 — El diff no se sale del alcance declarado

Este formato de task **no lleva tabla de "Archivos a crear/modificar"** (eso era el `Planning/` legado).
La diana es la prosa de la sección de alcance, con sus listas **In** y **Out**:

- `git diff --name-only $(git merge-base HEAD develop)..HEAD`.
- [ ] Nada del diff cae en algo declarado **Out** → si cae: `fail` categoría `out-of-scope`.
- [ ] Ficheros fuera de lo anticipado pero no prohibidos: `warn` categoría `undeclared-file`.
- ⚑ Si el cambio re-corta o renombra un concepto, comprobar el barrido de la regla 1:
      `rg -n '<término retirado>' src tests migrations docs config CLAUDE.md`. Un fichero que aún necesita
      la edición aparece con **diff vacío**, así que el diff no es la superficie de búsqueda.

### Paso 6 — Migraciones (si el diff toca `migrations/`)

⛔ **No con `make sf`.** Tres razones: monta `../f5sign-backend`, así que en un worktree valida **otro
árbol**; usa el rol `f5sign_app`, que no es superusuario (el target `migrate` del Makefile usa
`$(PHP_ADMIN)`); y `--dry-run` **solo imprime SQL**, así que no dice nada de `down()`. Usa el contenedor
puntual con la URL de admin, como en la precondición.

- [ ] `up()` aplica sin errores contra un `postgres-test` recién migrado.
- [ ] **`down()` se ejercita de verdad** — `--dry-run` no lo prueba; o se aplica y se revierte, o el report
      dice explícitamente que la reversibilidad quedó sin comprobar.
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
- {afirmación de la sección de verificación} → el harness no la alcanza porque {razón}

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
