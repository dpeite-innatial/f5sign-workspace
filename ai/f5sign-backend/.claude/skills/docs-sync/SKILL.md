---
name: docs-sync
description: 'Actualiza la documentación que vive fuera del código tras una task: los modelos de dominio de docs/ddd/ (docs vivos), docs/LIVE_SCHEMA.md, docs/ARCHITECTURE.md, CLAUDE.md cuando cambia el stack, las variables de .env/.env.dev/.env.test bajo la regla 4 del repo, y ADRs — que redacta SIEMPRE como Proposed y nunca da por aceptados sin el usuario. NO toca OpenAPI (Nelmio lo cubre inline). Condiciona por lo que toca el diff, no por tags. Úsalo con /docs-sync TASK-NNN. Activar con "sincronizar docs", "actualizar el modelo de dominio", "redactar ADR", "docs externas de task".'
---

# Docs Sync

Documentación fuera del código. No es gate duro; los fallos son warnings.

⚑ **La mitad de las dianas que esta skill tenía no existen en este repo.** Medido 2026-08-17: no hay
`CHANGELOG.md`, no hay `.env.example`, no hay `docs/asyncapi/`, no hay `docs/runbooks/`, y no hay
`src/*/README.md`. **Crear una superficie de documentación es una decisión, no una sincronización** — si
falta y hace falta, se reporta y se ficha en el BACKLOG; no se inventa a mitad de una task.

## Invocación

```
/docs-sync TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` y `context-digest.md`
- El `.md` de la task
- Del repo: [`docs/adr/`](../../../docs/adr/), [`docs/ddd/`](../../../docs/ddd/),
  [`docs/LIVE_SCHEMA.md`](../../../docs/LIVE_SCHEMA.md),
  [`docs/ARCHITECTURE.md`](../../../docs/ARCHITECTURE.md),
  [`docs/BACKLOG.md`](../../../docs/BACKLOG.md), [`CLAUDE.md`](../../../CLAUDE.md), `.env*`

## Outputs

- Ficheros del repo modificados, en **su propio commit** (no `--amend`: este repo integra PRs de varios
  commits)
- `var/task-runner/TASK-NNN/docs-sync.report.md`
- JSON: `{"status":"pass|warn","summary":"...","filesUpdated":[...],"surfacesAbsent":[...]}`

## Qué se ejecuta, según lo que toca el diff

**No hay tags en este formato de task.** La condición es el diff.

### El diff toca `src/F5Sign/<BC>/Domain/` o cambia un flujo → el modelo de dominio de ese BC

⚠ **El nombre del fichero no se deriva del directorio**: `Session/` → `signing-session-domain-model.md`,
`IdentityAccess/` → `identity-access-domain-model.md`, `SignatureExecution/` → `signature-execution-domain-model.md`.
Haz `ls docs/ddd/` en vez de construir el nombre en minúsculas.

Los modelos de dominio son **documentos vivos**: se actualizan en el sitio y su rastro es git
([`docs/adr/AUTHORING.md`](../../../docs/adr/AUTHORING.md) § ADRs vs domain models). Los ADRs son lo
contrario, puntuales.

- Actualizar el modelo del BC afectado con el estado actual.
- ⚑ **Si un ADR de este changeset supersede parte de un modelo**, no reescribas el modelo en la rama del
  ADR: pon un **banner con fecha** en la parte obsoleta apuntando al ADR, y deja que la siguiente feature
  del modelo lo reconcilie. El contrato está en
  [`docs/ddd/README.md`](../../../docs/ddd/README.md) § Document lifecycle.

### El diff toca `migrations/` → `docs/LIVE_SCHEMA.md`

- Actualizarlo, y **decir de dónde se re-derivó** (la migración, o una consulta al esquema).
- ⚠ Es **hecho de base de datos transcrito a mano**, o sea la única clase de afirmación que un documento no
  puede mantener cierta: ya está fichado como tal (`BL-99`). Si lo que toca es grande, el report debe decir
  que se transcribió a mano y qué no se verificó.

### El diff añade o cambia una variable de entorno → `.env`, `.env.dev`, `.env.test`

⛔ **No existe `.env.example` y no se crea.** La superficie de descubribilidad es la cabecera de orden de
carga de `.env`, que **nombra las variables en prosa**.

⛔ **Y para una variable sensible, un placeholder es la respuesta equivocada.** `.env` viaja **dentro de la
imagen de producción**, así que una clave nombrada ahí **siempre resuelve** y producción arrancaría con el
valor commiteado. La cabecera de `.env` lo dice literalmente: *no arregles esa ausencia commiteando un
placeholder*. Los dos patrones de la regla 4 del repo, y el primero es el estándar:

| Patrón | Cuándo | Ejemplos |
|---|---|---|
| **(A) Ausente** — el estándar | Siempre, salvo (B) | Son **seis**, y la cabecera de `.env` las nombra: `DATABASE_URL`, `APP_SECRET`, `MESSENGER_TRANSPORT_DSN`, `SIGNING_TOKEN_SECRET`, `IDENTITY_DATABASE_URL` y `PROVISIONING_DATABASE_URL` (las dos últimas llegaron con Identity & Access; `CLAUDE.md` sigue listando solo cuatro). `%env()%` falla al construir el contenedor en vez de caer a una contraseña de desarrollo |
| **(B) Presente y vacía** — excepción estrecha | Solo si un valor vacío **jamás** puede funcionar *y* su consumidor lo rechaza | `FIELD_ENCRYPTION_SECRET=` únicamente. **No es transferible**: `SIGNING_TOKEN_SECRET` tiene valor de dev en `.env.dev`, así que vacío no fallaría cerrado |

Añadir la variable al fichero del entorno que corresponda (valores de stack local sí van: coinciden con el
compose de infra y no son secretos), y **nombrarla en la cabecera de `.env`** si es de las ausentes.

### El diff cambia el stack, un bundle, un script de composer o un target de make → `CLAUDE.md`

⚑ **Es la superficie de mayor valor del repo y la que más daño hace al podrirse**, porque no se queda
obsoleta: empieza a **instruir mal**, y el siguiente agente reconstruye lo que quitaste. Declaró
*"Doctrine ORM 3"* durante semanas después de que saliera de `composer.json`. Entra en el barrido de la
regla de autoría 1 siempre.

### El diff añade un BC, una capa o cambia una ruta de decisión → `docs/ARCHITECTURE.md`

Su tabla de enrutado pregunta→documento es lo que lee alguien que llega nuevo. Si el mapa cambió, cambia.

### Hay una decisión transversal → un ADR, y **solo como `Proposed`**

⛔ **Esta skill no acepta decisiones.** Redacta; el usuario acepta. Hereda entero el gate de
`implement-backend` Paso 2b:

- **El vocabulario de estado es `Proposed` · `Accepted` · `Superseded`.** No existe `draft`. Y **`Accepted`
  significa ejercitado, no acordado**: escribirlo aquí falsifica el estado del repo.
- **Nada de `Origin: T{id}` ni cabeceras inventadas.** La cabecera es la tabla
  `| Field | Value |` con `Status` · `Date` · `Relates to` · `Crosswalk`, y las secciones son las de
  `AUTHORING.md` § Section template: `Context`, `Decision`, `Consequences` (con **Positive / Negative /
  Risks** — Risks no es opcional), `Related ADRs`, `Enforced by (in-repo)`, `Realized in (in-repo)`, y
  `Counterpoint` cuando hay alternativa creíble.
- **El número se acuña con el sweep de `AUTHORING.md`, corrido en ese momento y desde la raíz del repo**
  (`cd "$(git rev-parse --show-toplevel)"`, pathspec `':(top)docs/adr'`), sobre **todas** las ramas. "El
  mayor que hay + 1" mirando solo el working tree es cómo se acuñan colisiones: `AUTHORING.md` registra dos
  de ADR-0040, y `ADR-0049` apareció en otra rama en medio de una sesión.
- **Aterrizar es aterrizar completo: CINCO sitios.** Los tres de `docs/adr/README.md` (índice, grafo,
  crosswalk) más el campo `Crosswalk` de la cabecera; **más** los dos que `AUTHORING.md` llama *"each
  conditional but each easy to forget"*: la referencia `(ADR-NNNN)` en los docblocks del código que gobierna,
  y **la reconciliación del modelo de dominio** en `docs/ddd/` con su fila de estado en `docs/ddd/README.md`.
  Ese último es tuyo por definición: esta skill es la que mantiene los modelos.
- **Presentarlo al usuario** con qué decide, qué descarta y qué prohíbe, y **parar** hasta que responda.

### El diff cambia algo que el frontal consume → `docs/frontend-handoff/`

**Por qué existe.** La regla 4 del workspace prohíbe cruzar repos en un mismo commit: *dos proyectos = dos
PRs coordinados*. Así que un cambio de contrato del backend y su adopción en `f5sign-dashboard` /
`f5sign-signer` son changesets distintos, y sin un artefacto de traspaso el segundo se reconstruye
adivinando —o no llega nunca, que es lo que pasó con `signed_copy_url`: el frontal del firmante esconde su
botón de descarga desde entonces porque espera un campo que el backend nunca envía, y eso vivía
solo en un docblock del canal de email cuando se escribió esto — hoy está también en
`docs/ddd/notification-domain-model.md` y en el README del traspaso. (Dejo la corrección a la vista porque es
la regla 2 en acción: el *porqué* seguía siendo cierto y la mitad factual se había podrido.)

**Cuándo se escribe** — predicado, no tags. El diff toca `src/**/UI/Http/`, `config/routes/`, cualquier
`#[OA\`, un `Contract/` que la API emite, un enum cuyos valores salen por la API, una cabecera o regla CORS,
o una variable de entorno que el frontal necesita.

**Dónde:** `docs/frontend-handoff/TASK-NNN-<slug>.md` (o `YYYY-MM-DD-<slug>.md` si el cambio no viene de una
task). Convención completa en [`docs/frontend-handoff/README.md`](../../../docs/frontend-handoff/README.md).

⚠ **Y aquí hay una excepción explícita a la regla de arriba**, para que no parezca contradicción: el
directorio y su README nacieron en la rama `docs/task-conventions` y **puede que no existan en la rama donde
trabajas**. Escribir el primer traspaso ahí **sí** crea la superficie — y está autorizado, porque la decisión
ya está tomada y su convención escrita. Lo que la regla prohíbe es inventarse una superficie **sin decisión
previa**; esta la tiene. Si el README no está en tu rama, dilo en el report y enlaza a la rama que lo lleva.

**Qué lleva, y la forma importa porque el lector es un agente en otro repo sin acceso a este:**

```markdown
# Traspaso al frontal — {qué cambió, en una frase}

| | |
|---|---|
| **Origen** | rama `feat/...` · commit `<sha>` · {PR si existe} |
| **Fecha** | YYYY-MM-DD |
| **Repos afectados** | dashboard / signer / ambos |
| **Naturaleza** | aditivo · **rompe contrato** · corrige el spec |
| **Acción requerida** | ninguna · actualizar tipos · manejar estado nuevo · **migrar antes de {fecha}** |

## Lo que cambió en el contrato
- `{MÉTODO} {ruta}` — {qué campo/estado/código aparece o desaparece}, y **si es obligatorio**

## Lo que el frontal tiene que hacer
1. {paso concreto, en imperativo}

## Lo que NO está listo todavía
- {para que nadie construya contra un seam a medias}

## Cómo verificarlo desde el frontal
- {llamada concreta, o "regenerar el spec y diffear": el OpenAPI generado es la verdad máquina}
```

**Tres reglas anti-podredumbre**, porque este documento es la clase que más rápido se queda mintiendo:

1. **No copies el spec.** El OpenAPI que emite Nelmio es la verdad legible por máquina; aquí se dice **qué
   cambió y qué hacer**, y se apunta a él. Un esquema duplicado a mano divergirá y el frontal creerá al
   equivocado.
2. **Nombra el commit de origen.** Es lo único que le permite al agente del frontal saber si el traspaso ya
   está aplicado o si va por detrás.
3. **Di lo que no está listo.** La mitad del valor está en frenar trabajo contra un seam incompleto —el caso
   `signed_copy_url` es exactamente eso: los bytes ya son alcanzables, falta un campo y **la decisión de
   qué extremo lo pone**, que no se puede tomar desde dentro de este BC.

⚑ **Este fichero no autoriza a tocar el otro repo.** Se escribe aquí, viaja con este PR, y el cambio del
frontal es su propio PR en su propio repo.

### Superficies que no existen → warn, y ficha si hace falta

`CHANGELOG.md`, `.env.example`, `docs/asyncapi/`, `docs/runbooks/`, `src/*/README.md`.

No crear ninguna. Reportar en `surfacesAbsent` qué quedó sin documentar y dónde vive esa información
mientras tanto (p. ej. los eventos viven en sus clases `Contract/Event/` y en el ADR que los gobierna). Si
la ausencia es una carencia real y repetida, **una fila en `docs/BACKLOG.md`** con el id re-derivado por
grep en el momento — no un fichero fantasma a medio rellenar, que es peor que nada porque parece cobertura.

## Report

```markdown
# docs-sync — TASK-NNN

**Status:** {PASS|WARN} · **Ficheros actualizados:** {N}

## Cambios aplicados
- {fichero}: {qué}

## ADRs redactados
- ADR-NNNN — **Proposed**, pendiente de aceptación del usuario. Checklist de aterrizaje: {3 ediciones de
  README + campo Crosswalk} {hecho|pendiente}

## Superficies ausentes (no creadas a propósito)
- {p. ej. docs/asyncapi/: el evento X queda sin documentar; vive en su clase Contract/Event/ y en ADR-NNNN}

## Transcrito a mano y no verificado
- {p. ej. LIVE_SCHEMA.md: columnas de la tabla Y}
```

## Qué NO hace

- **No toca OpenAPI** — Nelmio lo cubre inline, en las anotaciones del código (`implement-backend` Paso 4).
- No edita el `.md` de la task (eso es `task-close`).
- No escribe el body del PR (`pr-ready`).
- **No marca ningún ADR como `Accepted`**, ni sigue adelante sin la respuesta del usuario.
- No crea superficies de documentación que el repo no tiene.
- No "mejora" documentación fuera del alcance de la task — salvo la prosa que la regla de autoría 1 obliga
  a corregir en el mismo changeset.
