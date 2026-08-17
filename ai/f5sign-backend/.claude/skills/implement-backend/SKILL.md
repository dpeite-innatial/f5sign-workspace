---
name: implement-backend
description: 'Implementa una task backend (PHP/Symfony) de docs/tasks/ con TDD dirigido por propiedades, respetando el kernel de dominio, Deptrac y las reglas de autoría de CLAUDE.md. Lee el .md de la task (§2 lo que ya existe, §3 scope, §5 verification), escribe código + tests al tier que usan sus hermanos, anota endpoints con Nelmio, y produce context-digest.md y plan.md. Solo para repositorios con stack PHP/Symfony. Úsalo con /implement-backend TASK-NNN. Activar con "implementa backend TASK-NNN", "codifica task PHP...", "ejecuta implementación backend de...".'
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

- El `.md` de la task, completo. Las secciones que gobiernan el trabajo son **§2 What already exists**
  (lo que hay que reusar y no reconstruir), **§3 Scope** (lo que se puede tocar y lo que no) y
  **§5 Verification** (el listón).
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

### Paso 3 — Bucle TDD

Por cada propiedad de §5 Verification, en orden:

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
- **Solo los aggregate roots tienen repositorio.** Las entidades subordinadas se modifican por su root.
- **Comandos por el bus; queries directas.** Los controladores inyectan el bus o el servicio de lectura,
  nunca un handler.
- **VOs `final readonly`** con constructor privado y named constructors.
- **Eventos de dominio en pasado** (`EnvelopeClosed`, no `CloseEnvelope`) — ADR-0011.
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

1. `git status` no debe traer nada que §3 Scope declare **Out**.
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
