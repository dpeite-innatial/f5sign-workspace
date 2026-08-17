---
name: implement-backend
description: 'Implementa una task backend (PHP/Symfony) de docs/tasks/ con TDD dirigido por propiedades, respetando el kernel de dominio, la separación entre BCs (solo Contract/ ajeno) y las reglas de autoría de CLAUDE.md. Para y consulta al usuario antes de tomar cualquier decisión transversal — contradecir un ADR aceptado, abrir una dependencia cross-BC, tocar Kernel/Foundation o editar deptrac/phpstan: redacta el ADR como Proposed y espera aceptación explícita, nunca lo marca Accepted por su cuenta. Lee el .md de la task (lo que ya existe, el alcance y la verificación, localizados por intención y no por número de sección), escribe código + tests al tier que usan sus hermanos, anota endpoints con Nelmio, y produce context-digest.md y plan.md. Solo para repositorios con stack PHP/Symfony. Úsalo con /implement-backend TASK-NNN. Activar con "implementa backend TASK-NNN", "codifica task PHP...", "ejecuta implementación backend de...".'
---

# Implement (backend)

Implementación de una task por TDD dirigido por propiedades.

> **Antes de escribir código, leer las [reglas de autoría de `CLAUDE.md`](../../../CLAUDE.md).** Existen
> porque el fallo que describe cada una **pasó en este repo, en una rama con `make qa` verde**, y ningún
> gate las ve. Esta skill las referencia; no las duplica, porque una copia se desincroniza.

## Invocación

```
/implement-backend TASK-NNN
/implement-backend {ruta al .md}
/implement-backend TASK-NNN --amplified-context
```

**Sin selección de modelo por `Complejidad`**: ese campo no existe en este formato de task. Hereda el
modelo de la sesión; escalar solo tras fallo repetido con diagnóstico que lo justifique.

## Inputs

- El `.md` de la task, completo. Tres secciones gobiernan el trabajo: **lo que ya existe** (reusar, no
  reconstruir), **el alcance** (qué se toca y qué no) y **la verificación** (el listón).
  ⚠ **Localízalas por intención, no por número.** Medido 2026-08-17 sobre los 21 registros: el alcance está
  en §3 en 13 de 21 (también en §4 y §6), la verificación en §5 en solo 7 (también §4, §6, §9), y "lo que ya
  existe" aparece como *What was built*, *What will be built*, *Design grounding*, *Locked decisions* o
  *The model*. `docs/tasks/README.md` §2 dice explícitamente que los encabezados varían con el trabajo, así
  que direccionar por `§N` es la lista cerrada que la propia convención prohíbe.
- Lo que citen sus campos `Builds on` y `Decision record`.
- Referencias fijas, siempre:
  - [`CLAUDE.md`](../../../CLAUDE.md) — convenciones + reglas de autoría
  - [`docs/LOAD-BEARING.md`](../../../docs/LOAD-BEARING.md) — qué parece duplicación y no lo es, más la
    lista **Never** de cambios ya propuestos y rechazados con su razón
  - [`docs/adr/`](../../../docs/adr/) — la decisión que gobierna la zona que tocas (regla 7 del repo)
  - Los docblocks de `src/F5Sign/Kernel/` de las categorías que uses: son la definición canónica
    (`grep -rnE "Kernel (sub-)?category" src/F5Sign/Kernel/` para enumerarlas)
  - [`tests/README.md`](../../../tests/README.md) — tiers, layout y convención `P-§`

## Outputs

- Código + tests commiteados en la rama de la task.
- `var/task-runner/TASK-NNN/plan.md` y `context-digest.md`.
- JSON final: `{"status":"pass|fail","summary":"...","filesChanged":N,"testsAdded":N,"attempts":N,"diagnosis":"..."}`

## Ejecución

### Paso 1 — Contexto

1. Leer el `.md` completo.
2. Leer lo que citan §2, `Builds on` y `Decision record`.
3. Leer las referencias fijas de arriba.
4. ⚑ **Si vas a escribir una clase modelada sobre otra existente: `ls` el directorio y lee TODOS los
   hermanos**, no el primero que encaje. Donde dos hermanos difieren, la diferencia es un bug en uno o una
   decisión — averigua cuál antes de copiar (regla de autoría 3; aquí un controlador nuevo copió al hermano
   equivocado y reintrodujo un 500 ya arreglado y documentado).

### Paso 2 — Plan

`var/task-runner/TASK-NNN/plan.md`:

```markdown
# Plan — TASK-NNN

## Orden de ejecución (TDD)
1. [TEST] tests/F5Sign/<BC>/<tier>/...Test::<nombre>  — propiedad: {P-§ o la afirmación de §5}
2. [CODE] src/F5Sign/<BC>/...
...

## Harness por propiedad
| Propiedad | Tier | ¿El harness la alcanza? |
|---|---|---|

## Decisiones tomadas
## Desviaciones del .md
## Status final
```

**La tabla "Harness por propiedad" no es opcional.** Es donde se decide, *antes* de escribir el test, si el
tier elegido puede ver la propiedad: `Integration/` corre una conexión bajo rollback DAMA (no distingue
lock de no-lock), `async_events` es `in-memory://` (nada se reentrega), Infection solo mira `src/F5Sign` y
no ve código sin llamantes. Una propiedad cuyo harness no la alcanza necesita otro tier o una probe
([`ProbesRowLocks`](../../../tests/F5Sign/Support/ProbesRowLocks.php) ya existe).

**Gate de plan:** si al planificar aparece ambigüedad no resoluble con el contexto disponible → devolver
`status: fail` con `diagnosis` explícito (`"spec contradictorio"` / `"contexto insuficiente"`) y **no
implementar nada**.

### Paso 2b — Gate de decisión: un ADR no se salta, y tampoco se acuña solo

⛔ **Para y consulta al usuario si el trabajo hace cualquiera de estas cosas.** No es una lista de casos
sospechosos: es la definición operativa de "decisión transversal" en este repo (regla 7).

| Disparador | Por qué es decisión |
|---|---|
| Contradice un ADR **aceptado** | Contradecirlo es un cambio de ADR, nunca una edición silenciosa |
| Abre una dependencia **cross-BC** nueva | El acceso entre BCs es solo por `Contract/`; ampliarlo cambia el mapa |
| Cambia un contrato de `src/F5Sign/Kernel/` o `src/F5Sign/Foundation/` | Es substrato: lo hereda todo |
| Edita el ruleset o las capas de [`deptrac.yaml`](../../../deptrac.yaml), `phpstan.dist.neon`, o añade al `phpstan-baseline.neon` | **Estás editando la regla que te juzga** |
| Introduce un patrón de realización nuevo (forma de use case, adapter, reactor) | Lo copiará el siguiente |

**Qué hacer, en este orden:**

1. **Parar antes de escribir el código que la decisión gobierna.** No "implemento y luego documento": el
   ADR es la entrada del código, no su acta.
2. **Redactar el ADR como `Proposed`**, con la plantilla de secciones de
   [`docs/adr/AUTHORING.md`](../../../docs/adr/AUTHORING.md) — incluidas `Consequences` con sus tres
   sublistas (**Risks no es opcional**) y `Counterpoint` si hay alternativa creíble. El id se acuña con el
   sweep de `AUTHORING.md`, **corrido en ese momento y desde la raíz del repo**.
3. **Presentárselo al usuario y esperar aceptación explícita.** Qué se decide, qué alternativa se descarta
   y **qué prohíbe a partir de ahora**. Silencio no es aceptación; `status: fail` con
   `diagnosis: "awaiting-adr-acceptance"` y para ahí.
4. ⛔ **Nunca escribas `Accepted` por tu cuenta.** En este set *Accepted* significa **ejercitado**, no
   acordado ([`AUTHORING.md`](../../../docs/adr/AUTHORING.md) § status): un ADR que nadie ha ejercitado
   todavía se queda `Proposed`, y ponerlo `Accepted` falsifica el estado del repo.
5. **Si el usuario lo rechaza**, la decisión no es tuya: recorta el scope o cambia de enfoque y vuelve al
   gate de plan. No lo implementes "de forma más pequeña" para que no haga falta el ADR.
6. **Cuando el ADR aterrice, aterriza completo — son CINCO sitios**, y `AUTHORING.md` § *Maintenance when
   adding an ADR* los enumera: (1) fila de índice, (2) grafo de relaciones y (3) fila de crosswalk en
   [`docs/adr/README.md`](../../../docs/adr/README.md), más el campo `Crosswalk` de la cabecera y las
   secciones que pide la plantilla; (4) **hacer el ADR alcanzable desde el código que gobierna** con
   referencias `(ADR-NNNN)` en los docblocks —*"only the pair makes the decision discoverable in both
   directions"*—; y (5) **reconciliar el modelo de dominio afectado** en `docs/ddd/` y su fila de estado en
   `docs/ddd/README.md`. Los dos últimos son los que AUTHORING llama *"each conditional but each easy to
   forget"*, y son justo los que esta lista omitía.

⚑ **El caso que más veces se cuela: ampliar la allowlist para poner el gate verde.** Si `composer arch`
falla, la respuesta **no** es añadir la capa a la lista de dependencias permitidas — esa edición *es* la
decisión, y silencia la única cosa que la vigilaba. Igual con una entrada nueva en
`phpstan-baseline.neon`: cada entrada de ese fichero es un hallazgo de diseño con su *por qué* escrito, no
un supresor.

### Paso 3 — Bucle TDD

Por cada propiedad de la sección de verificación, en orden:

1. **Escribir el test** en el tier que usan sus hermanos (`ls` el directorio de tests del BC; ser el único
   `*UseCase.php` sin `*UseCaseTest.php` al lado es la señal, y ha acertado siempre). Debe llevar:
   - `#[CoversClass]` o `#[CoversNothing]` — `phpunit.dist.xml` tiene `requireCoverageMetadata="true"`
   - `#[UsesClass]` para colaboradores, **incluidas las excepciones que el test asserta**
   - La cita `P-§` en el docblock si la propiedad está catalogada (`tests/README.md`)
2. **Ejecutarlo y verlo fallar por la razón correcta** (no por sintaxis ni por clase inexistente):
   ```
   docker run --rm --network f5sign-net -v $(pwd):/var/www/html -w /var/www/html \
     f5sign/backend:dev sh -c 'vendor/bin/phpunit --filter=<Clase>::<metodo>'
   ```
   (o `make -C ../f5sign-infra test` si trabajas en el checkout que monta el stack — ver
   `task-validate-backend`, precondición.)
3. **Escribir el código de producción mínimo.**
4. **Verde.**
5. ⚑ **Sabotear la guarda y ver el test caer por el motivo correcto; restaurar.** Es el paso que atrapa
   los tests que no pueden fallar, y sin él la propiedad no está probada — está afirmada.
6. Suite del módulo, para regresiones.

**Política de reintentos:** 3 iteraciones de editar-probar por test. Después, diagnóstico:
`"test mal escrito"` → fail; `"spec contradictorio"` / `"contexto insuficiente"` → fail **sin escalar**;
`"excede el modelo"` → fail con `diagnosis: "escalate"`.

### Paso 4 — OpenAPI (si tocas `UI/Http/` o `config/routes/`)

- `#[OA\Response]` por cada código HTTP **alcanzable**, `#[OA\RequestBody]`, DTOs con `#[OA\Property]`
  tipadas, security scheme si la ruta está protegida.
- ⚠ **Los strings de `#[OA\*]` se emiten literalmente al spec que ratifica el equipo de frontend.** No son
  comentarios internos: uno de ellos llegó a decir a los clientes que enviaran un valor que el endpoint no
  acepta. Entran en el barrido de la regla 1.
- Verificar: `make -C ../f5sign-infra sf cmd="nelmio:apidoc:dump --format=json"` completa sin error.

### Paso 5 — Reglas no negociables

- **El dominio no importa Symfony ni Doctrine.** Lo vigila Deptrac (`composer arch`) y las reglas PHPStan
  de colocación; si lo ves antes que ellas, rehacer.
- **Entre BCs solo se ve el `Contract/` ajeno.** `deptrac.yaml` declara **38** capas (37 con entrada en `ruleset` más `Vendor`) y lo dice explícitamente:
  `EnvelopeApplication` puede ver `SessionContract`, `SignatureExecutionContract`,
  `IdentityAccessContract`… y **ningún `Domain` ni `Infrastructure` de otro BC**. `Kernel` depende de nada
  (`Kernel: []`). Si necesitas un dato que solo vive en el `Domain` de otro BC, la respuesta es un puerto
  de lectura en su `Contract/` (ADR-0008), no un import — y **eso es Paso 2b**, no una decisión de mientras
  implementas.
- ⚑ **Notification es un BC de soporte: nada puede depender de él** (ADR-0037, categoría (c)). El gate **sí**
  lo caza: el `ruleset` de deptrac es una **allowlist positiva** y el repo corre con `Uncovered 0`, así que
  una clase que dependa de una capa no permitida da `DependsOnDisallowedLayer`. Lo que **no** puede ponerse
  rojo es **añadir la entrada a la allowlist**: eso no viola nada, simplemente deja de vigilar. Así que la
  pregunta al revisar no es *"¿pasa deptrac?"* sino *"¿toca este diff `deptrac.yaml`?"* — y si lo toca, es
  el Paso 2b, no una decisión de mientras implementas. Corregido 2026-08-17: esta viñeta decía que el gate
  era ciego a la dependencia, que es la dirección peligrosa de equivocarse.
- **Solo los aggregate roots tienen repositorio.** Las entidades subordinadas se modifican por su root.
- **Comandos por el bus; queries por llamada directa.** ADR-0008: **no hay QueryBus**, y un `QueryHandler`
  se realiza con un `handle(Query): R` directo — su §Counterpoint rechaza expresamente meter un adaptador en
  medio. Así que un controlador **sí** inyecta un query handler (tres lo hacen hoy) y eso es conforme; lo que
  no debe hacer es inyectar un *command* handler saltándose el bus, porque el bus es donde viven la
  transacción, el tenant y el issuer (ADR-0010).
- **VOs: la forma depende del tipo, y en bloque es incorrecta** (ADR-0005). Un **wrapper** (un solo campo)
  es `final readonly`; un **composite** (varios campos) es `final` y **no** readonly — 11 de los 22 del árbol
  lo son, con constructor público. El modelo a imitar es
  [`Settings`](../../../src/F5Sign/Envelope/Domain/ValueObject/Settings.php), que lo dice en su propio
  docblock: *"final (not readonly) per ADR-0005"*. Exigir `final readonly` a todos reintroduce el defecto
  que ADR-0005 existe para registrar. Named constructors sí, en los dos casos.
- **Eventos de dominio en pasado** — ADR-0011, ilustrado con eventos que este repo tiene de verdad:
  `EnvelopeCreated`, `EnvelopeSent`, `EnvelopeCompleted`, `StepCompleted`. ⚠ Y la forma superficial es la
  mitad **cosmética**: ADR-0011 dice que lo load-bearing es la **partición de propiedad** (el prefijo
  pertenece a un BC) y el **espejo**, y que el lint de prefijo↔BC es *candidate rule, not yet written*. Ojo
  con leerlo al pie de la letra: `EnvelopeReadyToSeal` no es un verbo en pasado y **es conforme** (nombre de
  transición a estado objetivo, §4), y ADR-0011 está en `Proposed`, así que por la regla 7 del repo aún no
  vincula.
- **Persistencia solo DBAL.** El ORM se retiró (ADR-0018): `doctrine/orm` no es dependencia y no hay
  ningún `*.orm.xml`. ⛔ **No escribas un docblock que justifique nada con hidratación/reflexión del ORM,
  ni con el outbox, ni con `AuditCommandInterface`**: son mecanismos ya retirados, y la regla de autoría 2
  existe porque volvieron como *razón* en prosa después de desaparecer del árbol.
- **Un cambio de esquema es una migración**, y si la migración escribe filas que el dominio luego lee,
  aplica la regla de autoría 6 (enumerar los estados del agregado sobre los que cae la fila; preferir un
  predicado que enuncie la propiedad — `sent_at IS NOT NULL` — a uno que enumere los estados de hoy).

### Paso 6 — Commits

**Sin política de commit único.** Este repo integra PRs de varios commits y merges de `develop`; un
`--amend` sobre algo ya pusheado obliga a `--force-with-lease` sin ganar nada. Commits pequeños y
coherentes, cada uno con mensaje que diga *por qué*, y `git add` de ficheros concretos (nunca `git add .`).

Antes del último commit:

1. `git status` no debe traer nada que el alcance de la task declare **Out**.
2. Si el cambio re-cortó, renombró o re-gateó un concepto: barrido de la regla 1, en un comando —
   `rg -n '<término retirado>' src tests migrations docs config CLAUDE.md`. **El diff no es la superficie
   de búsqueda**: un fichero que aún necesita la edición aparece con diff vacío. Y `CLAUDE.md` está en el
   barrido: es la única superficie que no se queda obsoleta sino que empieza a **instruir mal**.
3. Si la task descarga un deferral de un ADR, o hace cierto algo que un ADR daba por pendiente, el
   `Status` / `Enforced by` / `Realized in` de ese ADR van **en este changeset** (regla de autoría 7).

### Paso 7 — `context-digest.md`

≤150 líneas: qué se implementó · reglas de negocio aplicadas · modelo de datos tocado · contratos
afectados (API y eventos) · invariantes preservadas · decisiones tomadas y por qué · ADRs vinculantes ·
qué queda fuera (con id de task si existe).

### Paso 8 — `plan.md § Status final` y JSON

Tests nuevos y en verde, sabotajes hechos, suite del módulo, ficheros modificados, desviaciones. Última
línea de la respuesta: el JSON.

## Qué NO hace

- No audita seguridad, compliance ni performance.
- No toca documentación fuera del código (eso es `docs-sync`), salvo el OpenAPI inline de Nelmio y las
  correcciones de prosa que la regla 1 obliga a hacer en el mismo changeset.
- No abre PR (`pr-ready`) ni actualiza el `Status` de la task (`task-close`).
- No explora más allá de lo que la task cita: si falta contexto, `status: fail` con diagnóstico.
