# Auditoría de prompts — configuración de IA de f5sign-backend (2026-09-28)

Diff propuesto, **sin aplicar**: [`2026-09-28-prompt-audit-backend.patch`](2026-09-28-prompt-audit-backend.patch)
(41 hunks, uno por hallazgo o sub-hallazgo; `git apply --check` limpio desde la raíz). Se aplica por hunks
con `git apply --include=…` o a mano.

## Supuestos (Step 0)

- **Alcance:** la superficie de prompts de `f5sign-backend`: `CLAUDE.md`, los 11 subagentes de
  `.claude/agents/`, los 14 `SKILL.md` de `.claude/skills/` y `.claude/skills/README.md`. Todo son symlinks a
  `ai/f5sign-backend/`, así que **cualquier edición cae en el repo raíz**; el patch está escrito con esas
  rutas.
- **Fuera de alcance:**
  - el `CLAUDE.md` de la raíz (ancestro): solo se usó para comparar;
  - la memoria de `~/.claude/`;
  - `ai/shared/`;
  - `.claude/settings*.json`, que no se leyeron por si contienen secretos.
- **Modelo objetivo:**
  - Claude Opus 5.5 para `CLAUDE.md` y las skills que heredan el modelo de la sesión;
  - Sonnet 5 / Haiku 4.5 para los subagentes que fijan `model: sonnet` / `model: haiku`;
  - `eidas-compliance` se lanza con `opus`.
- No hay marcadores de otros proveedores.
- **Cómo se verificó:** las comprobaciones de hechos se hicieron con `grep`/`ls` de solo lectura (el guion
  pide herramientas de lectura de ficheros). No se ejecutó ningún comando del repo.

## Resumen

Lo que más pesa es que **varias skills de gate afirman sobre el código cosas que el código contradice**, y
el agente que las sigue produce hallazgos falsos o se salta los reales:

1. **La auditoría de seguridad parte de hechos falsos.**
   - `security-audit-backend` y `security-audit-core` dicen que el rate limiter "no está instalado". Está
     instalado y configurado (`rate_limiter.yaml`, `FailOpenOtpSendLimiter`), y `CLAUDE.md` lo describe.
   - La misma skill sitúa el TTL del token de firma en clases que ya no existen (`SigningTokenCodec`,
     `TOKEN_TTL`).
   - Afirma que "nada en Session mira `EnvelopeStatus`", cuando tres ficheros lo hacen.
2. **`CLAUDE.md` se carga en cada sesión y omite dos BCs** (`IdentityAccess`, `Storage`) en su lista de BCs
   poblados.
3. **Contradicciones dentro de los gates:**
   - `task-validate-backend` dice que no hay redelivery y, dos líneas después, que sí la hay;
   - `contract-check-backend` dice que nada fija `EVENT_TYPE` y su propio Step 4 describe el test que lo
     fija;
   - `perf-smoke-backend` dice que no hay tags y luego condiciona sus pasos a tags, y manda la deuda a
     `notes.md`, que `task-close` prohíbe.

**Recuento por grupo:**

| Grupo | Resultado |
|---|---|
| Grupo 1 (texto anticuado) | 0 edits; 2 flags de registro enfático |
| Grupo 2 (ficheros de configuración frágiles) | 14 de confianza alta + 9 de media, con diff; 6 flags |
| Grupo 3 (descripciones de herramientas) | no aplica: no hay definiciones de tools |
| Grupo 4 (configuración de peticiones) | no aplica: el backend no llama a la API de Claude. Revisada la plantilla de subagentes: los `*-runner` difieren en la skill que precargan y en el modelo, así que no son duplicados |

## Hallazgos — confianza alta (el repo los contradice)

| # | Ubicación | Evidencia | Patrón | Por qué está mal | Acción |
|---|---|---|---|---|---|
| 1 | `skills/security-audit-backend/SKILL.md:81-91` (+ :3, :203, :213) | "`symfony/rate-limiter` **is not a dependency** … `rate_limiter.yaml` doesn't exist" | G2 Volatile specifics / conflicto con `CLAUDE.md` § Stack | Lo contradicen `composer.json` (dependencia presente), `config/packages/rate_limiter.yaml` y `Session/Infrastructure/RateLimit/FailOpenOtpSendLimiter.php` | rewrite |
| 2 | `skills/security-audit-core/SKILL.md:152-154` | "the component isn't installed in the backend" | G2 Volatile specifics | Ídem | rewrite |
| 3 | `skills/security-audit-backend/SKILL.md:73, 134-139` | "`SigningTokenCodec`" · "`MintSigningTokenController` does `->modify('+7 days')` and `NotifyActivatedStepRecipientsUseCase` declares `TOKEN_TTL`" | G2 Volatile specifics | No existe ninguna clase `SigningTokenCodec` ni `TOKEN_TTL`. La vida del token es `StoreBackedSigningTokenIssuer::LIFETIME` | rewrite |
| 4 | `skills/security-audit-backend/SKILL.md:166-171` | "**no file under `src/F5Sign/Session/` looks at `EnvelopeStatus`**" | G2 Volatile specifics | Sí lo miran `SigningTokenIssuance`, `RecipientAuthContextReader` y `EnvelopeNoLongerLiveException` (ADR-0056/0059). Se mantiene la regla ("la credencial muere con su recurso") y se corrige el mecanismo | rewrite |
| 5 | `CLAUDE.md:9` | "4 populated BC trees (Envelope, Session, SignatureExecution, Notification)" | G2 Volatile specifics | `ls src/F5Sign/` muestra además `IdentityAccess/` y `Storage/`, ambos poblados. Se carga en cada sesión | rewrite |
| 6 | `skills/docs-sync/SKILL.md:75-76` | "There are **six** … `SIGNING_TOKEN_SECRET` … `CLAUDE.md` still lists only four" | G2 Contradicción entre ficheros + Volatile | La regla 4 de `CLAUDE.md` enumera nueve. `SIGNING_TOKEN_SECRET` no aparece en `.env` ni en `.env.dev`. Se propone remitir a la lista de `CLAUDE.md` en vez de duplicarla | rewrite |
| 7 | `skills/implement-backend/SKILL.md:207-208` | "`deptrac.yaml` declares **38** layers (37 …)" | G2 Volatile / contradicción | `deptrac.yaml` tiene hoy 44 capas, y `CLAUDE.md` pide contarlas allí | rewrite |
| 8 | `skills/spec-lint/SKILL.md:157-158` | "`TASK-021…023` live on `docs/two-gate-signer-auth` and are invisible from any other branch" | G2 Volatile | Las tres están en `docs/tasks/` de esta rama | rewrite (en pasado) |
| 9 | `skills/task-validate-backend/SKILL.md:190` vs `:196-199` | "nothing gets redelivered" / "but that's not the whole truth: `when@test` also declares two real AMQP transports" | G2 Contradicción dentro del mismo fichero | `messenger.yaml` declara `async_events_amqp` y `async_events_unroutable_amqp`. Se funden las dos viñetas | rewrite |
| 10 | `skills/task-validate-backend/SKILL.md:244-245` | "Use the one-off container with the admin URL, as in the precondition." | G2 Referencia colgante | La precondición ya no describe ese contenedor: lo prohíbe ("Never a hand-rolled `docker run`") | remove la frase |
| 11 | `skills/perf-smoke-backend/SKILL.md:149-151` | "leave the technical debt documented in `notes.md` (picked up by task-close)" | G2 Contradicción entre skills | El Step 4 de `task-close` prohíbe expresamente los `notes.md` en `var/` | rewrite |
| 12 | `skills/perf-smoke-backend/SKILL.md:48, 72-76, 93, 102` | "By tags and diff: If tag `api` … If tag `worker`" | G2 Contradicción dentro del mismo fichero | El propio fichero (:75-79) dice que este formato no tiene tags | rewrite |
| 13 | `skills/contract-check-backend/SKILL.md:101-106` y `:164` | "Nothing pins the value of `EVENT_TYPE` … There are 26 declared and **no test asserts a value**" · plantilla "registered in EventTypeRegistry ✓" | G2 Contradicción dentro del mismo fichero + Volatile | Las fixtures de `GoldenPayloadBytesTest` van una por `EVENT_TYPE` y su censo detecta el renombrado (una fixture huérfana); hay 42 ficheros con `EVENT_TYPE`. La plantilla pide marcar el registro que el Step 3 (:95) dice no comprobar | rewrite |
| 14 | `skills/docs-sync/SKILL.md:136-141` | "the directory and its README … **may not exist on the branch you're working on**" | G2 Volatile | `docs/frontend-handoff/README.md` existe | remove |

## Hallazgos — confianza media (narrativa histórica, redacción relativa a migraciones, recuentos volátiles)

Mantienen la regla y su porqué, y quitan la arqueología: fechas de corrección, "the previous version…",
"until 2026-09-23…", y recuentos de un día concreto que ya no son ciertos (por ejemplo "6 of 21 records":
hoy hay 50).

| # | Ubicación | Evidencia | Patrón | Acción |
|---|---|---|---|---|
| 15 | `eidas-compliance/SKILL.md:12-18` | "This skill was trimmed down on 2026-08-17 … It used to cover…" | G2 History narratives; 1d migration-relative | rewrite en 2 líneas (el Step 6 ya da el porqué) |
| 16 | `doctrine-guard/SKILL.md:12-13, 85, 89-90` | "Everything this skill used to check…" · "in the last review, the one blocking finding came from here" | G2 History / 1d | rewrite |
| 17 | `contract-check-backend/SKILL.md:66, 130-132` | "the one the previous version didn't have" · "⛑ This item said … until 2026-09-23" | G2 History / 1d | rewrite / remove |
| 18 | `task-validate-backend/SKILL.md:20, 47-48, 142-146` | "measured: scope in §3 in 13 of 21" · "whatever an older version of this skill said" · "Corrected 2026-08-17 … `Uncovered 0 / Allowed 3755`" | G2 Volatile + History | rewrite |
| 19 | `implement-backend/SKILL.md:29-31, 218-220, 224, 228-229` | "Measured 2026-08-17 across the 21 records" · "Corrected 2026-08-17" · "(three do today)" · "11 of the 22" | G2 Volatile + History | rewrite |
| 20 | `spec-lint/SKILL.md:59-60, 88, 123, 151-154` | "6 of 21 records" · "2 of 21" · "the 21 records" · "An earlier version of this line said 21…" | G2 Volatile + History | rewrite / remove |
| 21 | `docs-sync/SKILL.md:10-13, 120-126` | "Half of the targets this skill used to have…" · "(Leaving the correction visible…)" | G2 History / 1d | rewrite |
| 22 | `task-close/SKILL.md:87-90, 135` | "the one the previous version got wrong … paid for that mistake twice" · "`pr-ready` no longer rewrites history" | G2 History / 1d | rewrite |
| 23 | `task-runner/SKILL.md:112-114, 193-194` | "Until 2026-09-23 this was the FULL suite…" · "(Until 2026-09-23 the security audit ran after…)" | G2 History | rewrite / remove |

## Flags (sin edición propuesta)

| # | Ubicación | Qué | Por qué es flag |
|---|---|---|---|
| 24 | `pr-ready/SKILL.md:73` y `:147`, frente a `CLAUDE.md` de la raíz § Commits | Título "in the imperative" y commit "point TASK-NNN at its PR", frente a "stating **what's true now**, not the instruction given" | Contradicción entre ficheros que el historial no puede ordenar: ambos entraron el 2026-09-22 con 6 s de diferencia, en la misma sesión (7316be2 / ddc4263). Además, la regla de la raíz está fuera del proyecto. **Tienes que decidir tú** cuál manda para los títulos de PR |
| 25 | `agents/v1-docblock-flagger.md:3` | "Dispatched by the phase-C docblock pass" | Nada dentro del proyecto lo lanza. Puede que se use desde `notes/`; si no, es un agente huérfano cuya descripción viaja en cada sesión |
| 26 | `agents/spec-claims-runner.md:6` | `maxTurns: 60` | Observado en la sesión del 2026-09-25: se quedó sin turnos en TASK-050 sin entregar informe. No corresponde a ningún patrón documentado; es una observación |
| 27 | `agents/v1-hygiene-flagger.md:10`, `agents/v1-docblock-flagger.md:13`, `skills/v1-touched-file-hygiene/SKILL.md:14-16` | "This is an **AUDIT, not a SEARCH**" en mayúsculas | G1 1a (registro enfático). Lleva su porqué, y `tools: Read` ya lo garantiza estructuralmente. Confianza baja |
| 28 | `CLAUDE.md` en general | Densidad de ⛔/⚑/⚠ | G1 1a. Casi todos llevan su porqué al lado. Confianza baja; no se propone una pasada general |
| 29 | `security-audit-core/SKILL.md:98-102` | "today there's 1 live HIGH (`symfony/http-kernel`)" · "today one, `symfony/runtime`" | Volátil y no verificable sin red (`composer audit` necesita red) |
| 30 | `skills/README.md:8-43` | Tabla de estado "measured on 2026-08-17", "The twelve" | Instantánea histórica. No se carga sola, así que su impacto es bajo |
| 31 | `security-audit-core` / `security-audit-backend` | Rutas `var/task-runner/T{id}/` frente a `TASK-NNN` en el resto | Inconsistencia de marcador. El orquestador pasa el workspace explícito; confianza baja |
| 32 | `task-runner/SKILL.md:60-61, 157, 223`, `implement-backend/SKILL.md:183-188` | Incidentes "on TASK-046 …" | Son el porqué de reglas vigentes (lista de conservación, punto 1). Solo sobraría el id del incidente |

## Comprobado y correcto (no se toca)

- `gh` no está instalado (`pr-ready`, `task-runner`).
- `.claude/skills-config.yaml` existe.
- `lock_timeout`/`statement_timeout` no aparecen en `src/` ni `config/` (`perf-smoke-backend`).
- `/api/doc.json` declara `_authn: 'NONE'` sin gate de entorno (`security-audit-core`).
- `Lexik\` no está en el colector `Vendor` (`task-validate-backend`).
- `.env` sigue sin nombrar `RATE_LIMITER_DSN`, como avisa `CLAUDE.md`.

## Siguiente paso

Revisar el patch por hunks. Recuerda que un hunk sobre `ai/` afecta a todas las sesiones y worktrees en
cuanto se aplica (son symlinks). Si se aplica, conviene volver a pasar `security-audit-core` sobre una task
real (la regla 1 de `skills/README.md`) antes de fiarse del gate corregido.
