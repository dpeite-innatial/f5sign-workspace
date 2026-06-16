# Handoff — Validación efímera por worktree (signer + backend)

> **Fecha:** 2026-06-10 · **Revisado/implementado:** 2026-06-15 · **Estado:** Fase 1 (signer) y Fase 2 (backend) **IMPLEMENTADAS** en `f5sign-infra`; Fase 3 (eu-dss compartido) diseñada, sin implementar.
> **Por qué existe:** documento cross-repo (signer + backend + infra). No vive dentro de un repo a propósito.
> **Promoción sugerida:** `f5sign-docs/Planning/BACKLOG.md` → **BT-08** si se formaliza.

> **Audiencia: uso AUTOMATIZADO por agentes de IA.** El harness existe sobre todo para que varios
> agentes (uno por `git worktree`, cada uno con su `/task-runner`) validen **en paralelo y desatendido**.
> Eso dicta las prioridades: sin puertos host, teardown por `trap`, cap de concurrencia, autodetección
> de lane e integración transparente con la skill. El uso manual es secundario (depurar).

---

## 0. Qué cambió respecto al diseño original (2026-06-10)

El diseño original quedó desactualizado tras el split de compose en 3 ficheros y el RLS con rol de app.
La exploración del 2026-06-15 corrigió **tres premisas**:

1. **El knob de aislamiento es `STACK_NS`, NO `-p`.** El original proponía `-p f5sign-wt-<name>`. No
   funciona: volúmenes (`name: ${STACK_NS}_…`), red (`name: ${STACK_NS}-net`) y
   `container_name: ${STACK_NS}-…` llevan `name:`/nombre explícito → Compose ignora el prefijo de
   proyecto para ellos. **Se usa `STACK_NS=wt-<lane>`** (+ `COMPOSE_PROJECT_NAME` espejo). Los servicios
   efímeros del overlay **no fijan `container_name`** (permite `run --rm` y reintentos).
2. **El lane de backend es LIGERO (2 contenedores), no ~4.** En test: `MESSENGER_TRANSPORT_DSN=in-memory://`,
   cache=filesystem, lock=flock → el backend **no usa Redis ni RabbitMQ ni eu-dss** en sus tests. Lane =
   `postgres-test` (tmpfs) + `php` efímero.
3. **El "TEMPLATE clone" se DESCARTA.** `CREATE DATABASE … TEMPLATE` no copia `GRANT CONNECT` ni el
   `ALTER DATABASE … SET app.current_tenant_id` (per-DB), y como `current_tenant_id()` es *fail-closed*
   da errores crípticos; además con cap=1 el ahorro de contenedores es nulo. **Se usa `postgres-test`
   tmpfs por lane** (aislamiento total, teardown atómico con `down -v`). Optimización futura si las
   migraciones crecen: sembrar el tmpfs del lane desde un dump pre-migrado (dentro del lane, no compartido).

## 1. El problema

Paralelizar `/task-runner` con `git worktree` (1 sesión por worktree). Los tests SIEMPRE corren en
Docker (regla dura). Pero `signer`/`postgres-test` usan **puertos host fijos** y recursos atados a
`STACK_NS`, y solo el árbol principal está bind-mounteado → dos worktrees colisionan y un worktree
secundario validaría el código equivocado. El worktree aísla la **edición**; faltaba aislar la
**validación**.

## 2. Concepto: tier compartido vs tier efímero

- **Compartido (siempre-arriba, uno solo):** eu-dss con Trusted Lists (frío 30-90s, jamás per-lane);
  cachés CAS (`f5sign-pnpm-store`, `f5sign-composer-cache`, volúmenes `external`); opcionalmente el
  stack dev de master para browsing manual.
- **Efímero per-worktree (`STACK_NS=wt-<lane>`, sin puertos host, `run --rm` + `down -v` con trap, cap):**
  solo lo que debe aislarse por estado.

## 3. Implementación (Fase 1 + 2)

Ficheros en `f5sign-infra/`:

- **`scripts/wt-validate.sh`** `<signer|backend> [src]` — deriva `lane = basename(src)`, exporta
  `STACK_NS=wt-<lane>`, cap por `flock` (signer=2, backend=1), crea cachés CAS idempotente, `trap`
  teardown (`down -v --remove-orphans`), y dispara el lane.
- **`docker-compose.wt.signer.yml`** — 1 contenedor `signer-wt` (`mcr…/playwright`): bind-mount del
  worktree, `node_modules`/`.nuxt`/output por-lane + `f5sign-pnpm-store` (external), `CI=1` y
  **`PLAYWRIGHT_BASE_URL` sin setear** → `playwright.config` auto-hostea `pnpm dev` (:3001, mock) dentro
  del contenedor. Corre lint+typecheck+unit+e2e.
- **`docker-compose.wt.backend.yml`** — `postgres-test` (tmpfs, **nombre exacto `postgres-test`** para
  casar `backend/.env.test`; reusa `docker/postgres/init-*.{sql,sh}`) + `php-fpm-wt` (build dev,
  `var/`+`vendor/` por-lane, composer cache external). El wrapper: `up -d --wait postgres-test` →
  `composer install` → migrate como admin (`innasign`) → `composer test` (como `innasign_app`, RLS real).
- **`Makefile`** — `wt-signer`, `wt-backend`, `wt-ls`, `wt-down name=<lane>`, `wt-gc` (whitelist: nunca
  borra `f5sign-*`).
- **`CLAUDE.md`** — sección "Validación efímera por worktree".

Uso:
```bash
git -C f5sign-signer worktree add --detach ../f5sign-signer-laneb
make -C f5sign-infra wt-signer  src=../f5sign-signer-laneb
make -C f5sign-infra wt-backend src=../f5sign-backend-laneb
```

## 4. Decisiones (resumen)

- Aislamiento BD: **tmpfs por lane** (no TEMPLATE, no compartido).
- eu-dss/cachés: **compartidos** (cachés ya como volúmenes external; eu-dss → Fase 3).
- Cap: **backend=1, signer=2** (WSL; configurable, `mem_limit` de backstop). No mezclar varios backend.
- Integración skill: los targets `wt-*` los dispara el orquestador; documentado en `CLAUDE.md`.

## 5. Riesgos / edge-cases

- **WSL OOM** (ya colgó con 2 backend): caps firmes + `mem_limit` + no abusar de lanes simultáneos.
- **`.env.test` hardcodea host `postgres-test`** → resuelto nombrando el servicio del overlay
  `postgres-test`.
- **`.git` del worktree es un fichero** que apunta fuera del bind-mount: irrelevante para signer; en
  backend, `composer install` no debería necesitar git (vigilar si algún script lo invoca).
- **Cold start:** primer lane backend **construye** la imagen php dev (compila extensiones) → pre-`make
  build`. Primer install puebla la caché CAS.
- **Teardown sucio** (timeout/Ctrl-C): `trap … EXIT INT TERM` + `make wt-gc`.

## 6. Fase 3 — tier compartido eu-dss (PENDIENTE, solo para tests PAdES B-LT)

Hoy **ningún test toca eu-dss**, así que no hace falta. Cuando lleguen los tests PAdES B-LT/eIDAS:
`docker-compose.wt.shared.yml` + red `external f5sign-shared` (nombre fijo, no interpolar STACK_NS) +
eu-dss compartido + `make wt-up-shared`. El lane de firma joinea `f5sign-shared` además de su red interna;
`dss-wait-tl` antes de los tests de firma; `wt-gc` debe respetar `f5sign-shared`.

## 7. Punteros

- `f5sign-infra/scripts/wt-validate.sh`, `docker-compose.wt.{signer,backend}.yml`, `Makefile` (targets
  `wt-*`), `CLAUDE.md` (sección worktree).
- `f5sign-infra/docker/postgres/init-test.sql` + `init-app-role.sh` — crean `innasign_test` + rol
  `innasign_app` (cluster-wide).
- `f5sign-backend/.env.test` — `DATABASE_URL` (app role) + `MESSENGER_TRANSPORT_DSN=in-memory://`.
- `f5sign-signer/playwright.config.ts` — `webServer` auto-arranca si `PLAYWRIGHT_BASE_URL` no está.
- `f5sign-docs/Planning/FRONTEND-ORDER.md`, `BACKLOG.md` (aquí iría BT-08).

## 8. Estado

- **Fase 1 (signer) y Fase 2 (backend): implementadas y verificadas** en `f5sign-infra` (2026-06-15).
- **Fase 3 (eu-dss compartido): pendiente** (hasta que haya tests PAdES B-LT).
- Integración fina con la skill (que `make test-*` autodetecte worktree y delegue) queda como mejora
  opcional; de momento el orquestador llama a `wt-signer`/`wt-backend` explícitamente.
