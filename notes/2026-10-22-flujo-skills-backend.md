# Flujo de skills y agentes del backend (task-author → task-runner → PR)

Documento para revisar el stack de skills/agentes del backend de F5Sign y valorar llevarlo a otro proyecto.
Contrastado contra las 16 skills, los 15 agentes y `settings.json` del store a fecha 2026-10-22.

## Dónde está

| Qué | Ruta |
|---|---|
| Skills (el "qué hacer" de cada paso) | `ai/f5sign-backend/.claude/skills/` |
| Agentes (quién lo ejecuta: modelo, herramientas, skill precargada) | `ai/f5sign-backend/.claude/agents/` |
| Hooks compartidos | `ai/shared/settings.json` (+ scripts en `bin/` de la raíz) |
| Estado de adaptación de cada skill | `ai/f5sign-backend/.claude/skills/README.md` |

Hacen falta **skills y agentes**. Cada paso del flujo tiene un agente (`.claude/agents/*.md`) que declara su
modelo, precarga su skill (`skills:`) y limita herramientas: los validadores y revisores tienen prohibido
editar (`disallowedTools: Edit`). El orquestador lanza **agentes**, nunca carga las skills en su propio
contexto (las llenaría de código y correría con el modelo de la sesión).

## Visión general

```
/task-author ─► registro docs/tasks/TASK-NNN-*.md  +  rama  +  worktree   (commit tras OK del responsable)
      │  investiga con 3× Explore (haiku) · comprueba con spec-lint-runner + spec-claims-runner
      ▼
/task-runner TASK-NNN        orquestador: no escribe código; lanza agentes y lee solo su JSON final
   │
   ├─ Precondiciones   task commiteada · git limpio · base develop · stack levantado
   ├─ Fase 0   Preparación: worktree, workspace, entorno de tests, baseline
   ├─ Fase 1   spec-lint-runner + spec-claims-runner                              [GATE]
   ├─ Fase 2                                                                     [GATE]
   │    2a  plan-runner (opus, una vez) → plan.md, constraints.md, slices/NN.md
   │    2b  por oleadas, slices en paralelo:
   │          slice-implementer (+ replicator) ─► slice-reviewer ─► fix   (máx. 5 rondas)
   │    2c  test-runner (suite completa) ─► slice-reviewer de cierre (opus) ─► slice de cierre si hace falta
   ├─ Fase 3   en paralelo, según lo que toque el diff:                           [GATES]
   │           task-validate-runner · security-audit-runner (→ security-audit-backend, eidas-compliance)
   │           doctrine-guard-runner* · contract-check-runner*
   ├─ Fase 3b  Infection una vez sobre la punta final   ║ en paralelo: Fase 5 docs-sync + Fase 6 task-close
   ├─ Fase 4   perf-smoke (hoy se salta)
   ├─ Fase 7   Confirmación del usuario + tabla de coste (supervisado)
   └─ Fase 8   pr-ready
                                                          * solo si el diff toca lo suyo

Fuera del pipeline:  v1-touched-file-hygiene (antes de cada commit) → v1-hygiene-flagger por lotes
```

## Ideas que sostienen el diseño

1. **Planificar caro una vez, implementar barato muchas.** Un solo agente implementando una task entera relee
   un contexto que no para de crecer (medido: 895 turnos y 966k tokens de contexto en una task). Con un plan
   suficientemente preciso, cada slice lo hace un agente **nuevo** que solo lee su slice y `constraints.md`, y
   la mayoría pueden ir en sonnet.
2. **Quien implementa no se revisa a sí mismo.** Cada slice lo revisa otro agente con contexto limpio y sin
   permiso de escritura, antes de pasar al siguiente. Al final, una revisión global de la rama.
3. **Forma y fondo de la spec, por separado.** `spec-lint` comprueba que la task está bien escrita;
   `spec-claims` que lo que dice del código actual es verdad. Una task pasó la primera limpia con un mecanismo
   falso dentro.
4. **Gates que paran.** Fases 1, 2 y 3 bloquean; el resto avisa y sigue.
5. **El orquestador no lee código ni informes enteros.** Solo el JSON final de cada agente y, si algo falla,
   su informe. Los hallazgos viajan por fichero, no por su contexto.
6. **Los agentes no deciden lo transversal.** Si algo requiere una decisión de arquitectura, se redacta un
   ADR como `Proposed` y se para hasta que el usuario lo acepta, incluso en `--auto`. Un subagente no puede
   preguntar al usuario: devuelve `awaiting-adr-acceptance` y pregunta el orquestador.
7. **Una comprobación vale para el texto que comprobó.** Lo que se edita para contestar a un hallazgo se
   vuelve a comprobar.

## 1. Antes del pipeline: `task-author`

`/task-author` con lo que se quiere construir. Pasos:

1. **Intake**: qué debe conseguir y qué criterios trae ya el responsable (entran tal cual, origen `owner`).
   Una sola ronda de preguntas, y nada que pueda responder el código.
2. **Investigación delegada**: 3 agentes `Explore` (haiku) en paralelo, cada uno devolviendo hechos con
   `fichero:símbolo`: qué existe ya (clases, puertos, rutas, eventos, tests), qué ADR gobiernan el área, y qué
   pendientes la tocan (backlog, otras tasks, handoffs). Lo que no se puede señalar en un fichero no entra.
3. **Deriva los criterios que faltan** y los marca como propuestos, con su fuente.
4. **Confirmación del responsable**, por grupos o uno a uno según el origen. Si el trabajo es transversal, se
   dice aquí y la decisión es del responsable.
5. **Escribe el registro** en una rama y worktree nuevos desde `develop` (igual que la Fase 0 del runner).
6. **Lo comprueba** con `spec-lint-runner` + `spec-claims-runner` en paralelo, y re-lanza `spec-claims` sobre
   lo que corrija.
7. **Commit solo tras el OK final** del responsable. El worktree queda listo para `/task-runner`.

## 2. El orquestador: `task-runner`

```
/task-runner TASK-NNN               supervisado (por defecto)
/task-runner TASK-NNN --auto        sin supervisión
/task-runner TASK-NNN --resume      retoma un workspace existente
/task-runner TASK-NNN --plan-only   se para tras aprobar el plan
```

Todo lo que producen las fases vive en un **workspace** dentro del worktree,
`var/task-runner/TASK-NNN/` (ignorado por git): `plan.md`, `constraints.md`, `slices/NN.md` y sus
`NN.report.md` / `NN.review.md` / `NN.findings.md`, `progress.md` (el ledger), `context-digest.md`,
`changes.diff`, los informes de cada gate y `run.log`.

### Precondiciones (si falla alguna, se para con un mensaje claro)

1. Existe `docs/tasks/TASK-NNN-*.md`.
2. `git status` limpio; la task tiene que estar **commiteada** (un worktree sale de un commit).
3. La base es `develop`; se ramifica desde la ref, nunca haciendo checkout.
4. El stack de desarrollo está levantado.
5. **Todas las ejecuciones de tests y gates pasan por el agente `test-runner`** (salvo el bucle TDD dentro de
   cada slice), y el `run.log` dice **contra qué árbol** se validó: una validación que no apuntaba a tu árbol
   se lee como verde.

### Fase 0 — Preparación

1. Localiza la task y lee su cabecera; si tiene una task hermana marcada, la lee antes.
2. Comprueba que sus dependencias (`Builds on`) están hechas o mergeadas.
3. **Worktree hermano** (`../f5sign-backend-<slug>`), o reutiliza el que dejó `task-author`. No se trabaja en
   el checkout principal porque los workers de desarrollo lo montan con caché que no se recompila.
4. Crea el workspace (si ya existe sin `--resume`, pregunta si retomar o empezar).
5. Levanta y **mantiene** el entorno de tests aislado del worktree durante toda la task.
6. **Baseline** de los tests rápidos (Unit/Application) antes de tocar nada, anotando nº exacto de tests y
   asserts, para separar luego los rojos propios de los del entorno. Un baseline rojo no aborta: se declara.

### Fase 1 — Forma y fondo de la task [GATE]

Dos agentes de solo lectura en paralelo (junto con la baseline):

- **`spec-lint-runner`** (haiku, skill `spec-lint`): la **forma** — cabecera, secciones, rutas citadas que
  existen, dependencias resueltas, ningún "PENDIENTE", ADR citado si toca superficies transversales.
- **`spec-claims-runner`** (sonnet): el **fondo** — lo que la task afirma sobre el código actual es cierto y
  sus criterios de verificación pueden llegar a verde.

Un bloqueo lo resuelve el usuario (cambia la task o la decisión). Si para eso se edita la task,
`spec-claims-runner` se re-lanza sobre los pasajes editados antes de la Fase 2.

### Fase 2 — Plan y slices [GATE]

#### 2a · Plan — `plan-runner` (opus, skill `plan-backend`), una sola vez

- Lee la task, lo que cita y el código afectado; el censo de código (llamantes, hermanos) lo delega en
  `Explore` (haiku). Si va a modelar una clase sobre otra, lee **todas** las hermanas.
- Produce:
  - `plan.md`: matriz criterios → slices, cómo se prueba cada propiedad, la tabla de slices, *Sweep terms*
    (términos retirados que hay que barrer), decisiones tomadas y desviaciones.
  - `constraints.md`: lo que ata a todos los slices (ADR que aplican, reglas, lo que está fuera de alcance,
    rama, worktree) y una sección `Landed so far` que irá rellenando el orquestador.
  - `slices/NN.md`, con formato fijo: objetivo, por qué, **ficheros**, registros (handlers, rutas…),
    **instancia de referencia** a imitar, prosa a escribir, afirmaciones que NO se pueden copiar, **tests a
    escribir primero**, **sabotaje** que el test debe detectar, cómo verificar, y **cuándo parar y reportar**.
    Cada slice lleva un **tier** (`mechanical` / `standard` / `critical`) y una **oleada**.
  - `context-digest.md`: resumen ≤150 líneas para los gates de la Fase 3.
- Si detecta una decisión transversal, redacta el ADR como `Proposed` y devuelve `awaiting-adr-acceptance`:
  turno del usuario. Prohibido aceptarlo por él o recortar el cambio para esquivar la decisión.
- **Comprobación del plan** (script o `Explore` haiku) antes de enseñarlo: todo criterio cubierto por un
  slice y un test, todo handler/ruta nueva con su registro, las palabras de riesgo (migraciones, locks,
  autenticación, RLS…) implican `critical`, sin placeholders, oleadas coherentes y con ficheros disjuntos.
  Si falla, una enmienda de `plan-runner`.
- **Supervisado**: el usuario ve slices con tier y motivo, la matriz con lo no cubierto resaltado y las
  decisiones que el plan tomó por su cuenta; aprueba, corrige o re-corta. `--plan-only` se para aquí.
- `plan-runner` tiene además un **modo enmienda**: re-corta slices no aprobados, escribe slices de corrección
  (de un gate o de la revisión de cierre) y el slice de cierre. Nunca toca un slice ya aprobado.

#### 2b · Cada slice: implementar → revisar → corregir

**Por oleadas, en paralelo dentro de cada una.** Un slice está listo cuando lo están sus dependencias. Los
implementers en paralelo comparten worktree, así que reciben reglas estrictas: tocar solo sus ficheros,
`git commit --only -- <sus rutas>`, nunca `git add -A` / `stash` / `reset`, solo tests filtrados.

1. **`slice-implementer`** (sonnet; opus si el slice es `critical`; skill `implement-backend`):
   - **Primero contrasta el slice con el código.** Si no cuadra (un símbolo que no está, un test que ya
     pasa), se para con `NEEDS_CONTEXT`; si hace falta una decisión, tocar fuera de sus ficheros o algo
     transversal, `BLOCKED`. No adapta el plan por su cuenta ni redacta ADR.
   - **TDD**: tests primero, verlos fallar por el motivo correcto, implementar, **sabotear** la protección
     para comprobar que el test la detecta.
   - Delega lo repetitivo en **`replicator`** (sonnet): le pasa un ejemplo ya cubierto por un test y la
     lista exacta de destinos (casos restantes de una tabla, el mismo método en cada fake, una firma en todos
     sus llamantes). El replicator solo edita: ni tests, ni git, ni decisiones.
   - Commits pequeños con rutas explícitas; antes del último, barrido de términos retirados en todo el repo.
   - Devuelve `DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`.
2. **El orquestador actúa según el estado:**

   | Estado | Qué hace |
   |---|---|
   | `DONE` | Revisión |
   | `DONE_WITH_CONCERNS` | Lee las dudas: las de corrección o alcance se arreglan antes de revisar; las observaciones van a desviaciones |
   | `NEEDS_CONTEXT` | Completa el slice desde la task o el plan y lanza un implementer nuevo; si cambia el plan, es del usuario o una enmienda |
   | `BLOCKED` | Algo cambia antes de reintentar (más contexto, opus, slice más pequeño, plan corregido). **Nunca** se relanza igual. Una decisión o un slice mal cortado va a `plan-runner` en modo enmienda |

   **Límites**: 2 relanzamientos por `NEEDS_CONTEXT`/`BLOCKED` por slice; 1 enmienda del plan por task (+1
   por cada slice de corrección de la Fase 3). Superado un límite: supervisado → pregunta; `--auto` → se para
   con el estado guardado, nunca borra.
3. **`slice-reviewer`** (sonnet; opus si el slice es `critical` o escribe textos de OpenAPI): ve **solo** el
   slice, `constraints.md`, el informe del implementador y el diff. No puede editar; escribe hallazgos
   puntuados por confianza en `slices/NN.review.md`. Los slices `mechanical` consecutivos se revisan juntos.
4. **Bucle de corrección**, máximo **5 rondas** (una ronda = un fix + una revisión):
   - Los hallazgos van a `slices/NN.findings.md`. En las rondas 1–3 se le mandan **al mismo implementer**
     (`SendMessage`, ya tiene el slice en contexto); si no se puede retomar, a uno nuevo con el informe.
   - **Escalada a opus** a la primera repetición de un hallazgo de seguridad, tenant, consentimiento o de
     ciertas reglas de autoría; si no, tras la ronda 3.
   - **Antes de la ronda 4, diagnóstico**: si el slice está mal cortado, enmienda del plan en vez de
     relanzar.
   - Tras la 5.ª, el orquestador decide cada hallazgo restante: lo arregla él o lo registra como desviación.
     En `--auto` se para si alguno es de seguridad, tenant o consentimiento.
5. **Al aprobar**, el orquestador actualiza de una vez: marca el slice en `progress.md` (rango de commits,
   ronda), añade sus términos cambiados a *Sweep terms*, sus desviaciones a `plan.md` y una línea por símbolo
   nuevo o cambiado a `constraints.md § Landed so far` (así los slices siguientes saben qué existe ya).

#### 2c · Toda la rama, una vez

1. **`test-runner`** (haiku): suite completa y gates sobre el entorno del worktree. Su resultado es el
   `last_green_run` (sha, tests, asserts, log) que reutiliza la Fase 3. Un rojo aquí → slice de corrección.
2. Genera `changes.diff` (`merge-base..HEAD`) y refresca `context-digest.md`.
3. **Revisión de cierre**: `slice-reviewer` en modo cierre con opus sobre toda la rama, con *Sweep terms*,
   `Landed so far`, todas las revisiones de slice y la task. Siempre.
4. **Slice de cierre** (critical) si la revisión pide cambios, si hay términos retirados o un ADR que
   aterrizar, o si la task añade un registro (listener, handler, ruta, servicio etiquetado). Lo escribe
   `plan-runner` en modo enmienda y pasa por 2b; después se repiten los pasos 1–2.
5. Registra cada slice en `run.log`: tier, modelo, rondas, turnos, tokens, estado.

### Fase 3 — Validaciones [GATES]

Qué se lanza depende de **lo que toca el diff**, no de etiquetas. Todos en el mismo mensaje, en paralelo:

| Agente / skill | Cuándo | Qué valida |
|---|---|---|
| `task-validate-runner` / `task-validate-backend` | siempre | suite, PHPStan nivel 9, Deptrac, lint; separación de dominios; que un ADR aterriza completo; que cada propiedad declarada está probada y cada criterio tiene un test que lo cita; que el diff no se sale del alcance; migraciones |
| `security-audit-runner` / `security-audit-core` | siempre | secretos, PII en logs, CVE, autenticación, fugas entre tenants. Lanza a su vez `security-audit-backend` (agente `general-purpose`, sonnet) y, si el diff toca firma o cripto, `eidas-compliance` (`general-purpose`, opus) |
| `doctrine-guard-runner` / `doctrine-guard` | si toca persistencia o SQL | migraciones reversibles, índices, RLS, enums vs columnas |
| `contract-check-runner` / `contract-check-backend` | si toca endpoints o eventos | OpenAPI vs respuesta real (conjunto cerrado de claves), eventos solo con cambios aditivos |

Reglas de la fase:

- **Antes de lanzar**: el volcado de OpenAPI de este árbol (si hay endpoints) y todo lo que no son tests.
- **Solo `task-validate` ejecuta tests.** El entorno admite una ejecución a la vez, así que los demás
  **citan `last_green_run`** y, si necesitan otra ejecución, lo dicen en su informe y se lanza después.
- **Cada agente recibe su lista de rutas** y la orden de reportar, no editar, lo que vea fuera. Antes de
  repartir, el orquestador comprueba que toda superficie del alcance tiene dueño; lo que no, es suyo.
- Los gates no tienen `Edit`. Si un brief necesita sabotear un fichero para ver fallar una protección, se usa
  `general-purpose`, que debe restaurarlo y demostrarlo con un `git diff` vacío.
- **Si el diff añade un listener, middleware o servicio etiquetado, se comprueba que está registrado**
  (`debug:event-dispatcher`, `debug:container --tag`, `debug:messenger`): uno sin registrar es un no-op
  silencioso que ningún gate ve.
- Un gate que falla: supervisado → slice de corrección escrito por `plan-runner` y pasado por 2b (máx. 2
  iteraciones) o abortar; `--auto` → abortar.

### Fase 3b — Infection, una vez

La prueba de mutación (~35 min) se ejecuta **solo** cuando todos los gates han pasado y no queda ninguna
corrección pendiente, sobre la punta que se va a mergear (si `src/` cambia después, se repite). **En
paralelo** se lanzan las fases 5 y 6, que solo tocan documentación y no la invalidan (~20 min ahorrados por
task).

### Fase 4 — `perf-smoke-backend`

Revisión estática de rendimiento (N+1, índices, trabajo pesado en transacciones, trabajo síncrono que debería
ir por cola). La parte dinámica no existe (falta un seed de datos), así que se registra como "saltada", no
como verde.

### Fase 5 — `docs-sync` (agente `docs-sync-runner`)

Si el diff toca ADR, configuración, `.env*`, eventos o añade un módulo. Actualiza la documentación fuera del
código (DDD, esquema, arquitectura, variables de entorno); ADR siempre como `Proposed`. Commit propio. No es
gate: si falla, avisa y sigue.

### Fase 6 — `task-close` (agente `task-close-runner`)

Siempre. Actualiza el estado de la task nombrando rama o commit; añade al final la sección de desviaciones
(alcance, decisiones tomadas, propiedades sin probar, deuda, trabajo delegado, coste); y se asegura de que
**nada aprendido se queda en `var/`**: lo aplazado va a seguimientos y al backlog, las decisiones a su ADR.
Si la task hizo cierto un ADR, propone pasarlo a `Accepted` y devuelve `awaiting-adr-acceptance`: el
orquestador pregunta al usuario y, si acepta, lo aplica en su propio commit.

### Fase 7 — Confirmación (solo supervisado)

Resumen de fases, ficheros, tests añadidos, criterios cubiertos, avisos activos y **con qué entorno se
validó**, más una tabla de coste por slice (tier, modelo, rondas, estado, turnos/tokens) sacada de
`run.log`. Pregunta si abrir el PR.

### Fase 8 — `pr-ready`

Push, título *conventional commits*, cuerpo generado (task, resumen, cambios, propiedades verificadas, tabla
de validaciones con el entorno usado, notas para el revisor, plan de pruebas), draft si quedan avisos,
etiquetas solo si existen en el repo, y un commit final que apunta la task al PR. Multi-commit, sin
`--amend`.

⚠ **Hoy `gh` no está instalado**, así que el PR se abre a mano y el runner lo dice en el resumen (no es un
fallo). Con `gh` disponible lo hace la skill.

### Retomar (`--resume` o tras compactar)

Re-levanta el entorno del worktree (idempotente); un slice con commits pero sin aprobar va directo a
revisión; el contador de rondas sigue desde el ledger; si la task cambió desde que empezó, lista lo cambiado
y pregunta.

### Contrato y fallos

- Cada agente recibe la task y el workspace **por ruta absoluta**, escribe su `*.report.md` en una ruta
  predecible y devuelve como última línea `{ status, summary, issues?, metrics? }`.
- `run.log` (JSON lines): una línea por fase y otra por slice/agente con modelo, rondas, turnos y tokens.
- Gate que falla → parar o corregir; no gate → avisar y seguir; agente caído → un reintento; git que falla →
  nunca `--force` ni `reset --hard`, se para. Ctrl+C deja el workspace intacto.
- El resultado de un subagente se espera por su notificación, nunca sondeando su fichero de salida.
- El orquestador **no** edita código, no interpreta informes (solo su JSON), no crea tasks y no mergea.

## 3. Fuera del pipeline: `v1-touched-file-hygiene`

Antes de cada commit: revisa los ficheros tocados en busca de texto que se quedará obsoleto y referencias a
cosas fuera del repo, para que el repo siga siendo autocontenido. La lectura la delega por lotes (menos de
diez agentes por pasada) en **`v1-hygiene-flagger`** (sonnet, solo lectura: señala candidatos, ni corrige ni
decide); la skill juzga y corrige fichero a fichero.

Del mismo tipo existe **`v1-docblock-flagger`** (sonnet, solo lectura), que señala docblocks mal formados o
condensables. Se usó en una pasada puntual de limpieza y no forma parte del flujo de una task.

## 4. Hooks que sostienen el flujo (`ai/shared/settings.json`)

| Hook | Qué hace |
|---|---|
| `ai-doctor.sh` (inicio de sesión) | detecta ficheros de IA reales o desincronizados en los subrepos |
| `require-agent-model.sh` (antes de `Agent`) | rechaza lanzar un agente que heredaría el modelo caro de la sesión sin declararlo |
| `refuse-self-matching-wait.sh` (antes de `Bash`) | rechaza los bucles de espera que sondean el fichero de salida de un subagente (nunca terminan) |

## Mapa de agentes y modelos

| Agente | Modelo | Skill | Lo lanza |
|---|---|---|---|
| `spec-lint-runner` | haiku | `spec-lint` | task-author, runner F1 |
| `spec-claims-runner` | sonnet | — | task-author, runner F1 |
| `plan-runner` | opus | `plan-backend` | runner F2a y enmiendas |
| `slice-implementer` | sonnet (opus si crítico o escalado) | `implement-backend` | runner F2b |
| `replicator` | sonnet | — | slice-implementer |
| `slice-reviewer` | sonnet (opus si crítico y en el cierre) | — | runner F2b, F2c |
| `test-runner` | haiku | — | runner (toda ejecución de tests salvo el TDD del slice) |
| `task-validate-runner` | sonnet | `task-validate-backend` | runner F3, F3b |
| `security-audit-runner` | sonnet | `security-audit-core` | runner F3 |
| `doctrine-guard-runner` | sonnet | `doctrine-guard` | runner F3 |
| `contract-check-runner` | sonnet | `contract-check-backend` | runner F3 |
| `docs-sync-runner` | sonnet | `docs-sync` | runner F5 |
| `task-close-runner` | sonnet | `task-close` | runner F6 |
| `v1-hygiene-flagger` | sonnet | — | v1-touched-file-hygiene |
| `v1-docblock-flagger` | sonnet | — | pasada puntual |
| `general-purpose` (genérico) | sonnet / opus | `security-audit-backend` / `eidas-compliance` | security-audit-core |
| `Explore` (genérico) | haiku | — | task-author, plan-backend, comprobación del plan |

Skills sin agente propio: `task-author`, `task-runner`, `pr-ready` y `v1-touched-file-hygiene` corren en la
sesión principal; `perf-smoke-backend` no se ejecuta hoy.

Regla: el orquestador **no pasa `model:`** al lanzar un agente con modelo declarado (anularía el suyo),
salvo en 2b/2c para subir a opus un slice crítico, una ronda escalada o la revisión de cierre.

## Qué llevarse a otro proyecto

- **El método** (lo más valioso): orquestador + plan único con modelo caro + slices con agentes nuevos y
  baratos + revisor independiente sin escritura + revisión de cierre + gates. Empezar por `task-runner`,
  `plan-backend`, `implement-backend` y `agents/slice-reviewer.md`, y copiar también `agents/` y los hooks.
- **Fáciles de adaptar**: `task-author`, `spec-lint` + `spec-claims-runner`, `security-audit-core`,
  `pr-ready`, `v1-touched-file-hygiene`, `test-runner`, `replicator`.
- **Solo con stack parecido (PHP/Symfony/Postgres)**: `task-validate-backend`, `doctrine-guard`,
  `contract-check-backend`, `security-audit-backend`, `perf-smoke-backend`, `docs-sync`.
- **Específica de este producto**: `eidas-compliance` (firma PAdES con EU DSS).

Todas tienen referencias propias de F5Sign (formato `TASK-NNN`, entornos `wt-*` de infra, ADR concretos,
rama `develop`, ids de tasks pasadas en los ejemplos) que habrá que sustituir.
