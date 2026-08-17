# f5sign-infra — Guia operativa para Claude Code

Repo de infraestructura del producto F5Sign. Contiene la orquestacion Docker (local y produccion), los Dockerfiles personalizados, configuracion de Caddy, scripts de init y automatismos (`Makefile`, pipelines CI/CD cuando apliquen). Es el repo que arranca el stack completo: backend + dashboard + signer + servicios (PostgreSQL, RabbitMQ, Redis, MinIO, EU DSS).

## Proposito del repo

- **Orquestacion**: `docker-compose.yml` que levanta todos los servicios del MVP en un solo comando.
- **Dockerfiles custom**: para servicios que no tienen imagen oficial valida (PHP-FPM con extensiones Symfony, build de EU DSS, scripts de init de MinIO).
- **Configuracion de servicios**: `docker/caddy/Caddyfile{,.dev}`, `docker/php/php.ini`, `docker/minio/init-buckets.sh`, etc.
- **Makefile**: automatismos para el equipo (`make up`, `make test`, `make sf cmd=...`).
- **Env template**: `.env.example` con todas las variables compartidas.
- **CI/CD** (se anade en fases posteriores): workflows de build/deploy de las tres apps.

## Stack

- **Docker** / **Docker Compose** (v2)
- **Caddy** 2 alpine (`caddy:2-alpine`, reverse proxy de la API en dev y en prod)
- **PostgreSQL** 16 alpine
- **RabbitMQ** 3.13 management alpine
- **Redis** 7 alpine
- **MinIO** latest + `mc` para init
- **EU DSS** (`nowina-solutions/dss-webapp:6.4`, imagen Java)
- **PHP** 8.4 fpm alpine (Dockerfile custom con extensiones Symfony)
- **Node** 20 alpine (para los contenedores de dev de dashboard y signer)
- **GNU Make** para el Makefile

## Estructura del repo

```
f5sign-infra/
├── docker-compose.yml             ← base prod-safe
├── docker-compose.override.yml    ← overrides de dev (auto-carga en `up`)
├── docker-compose.prod.yml        ← overrides de produccion (imagenes GHCR)
├── docker-compose.test.yml        ← servicios de test (profile `test`)
├── Makefile
├── .env.example                   ← entorno dev
├── .env.prod.example              ← entorno prod (plantilla)
├── .gitignore
├── docker-compose.mock-signer.yml ← signer simulado
├── docker-compose.wt.{signer,backend}.yml  ← lanes efimeros por worktree
├── docker/
│   ├── caddy/
│   │   ├── Caddyfile              ← prod
│   │   ├── Caddyfile.dev          ← dev
│   │   └── conf.d/                ← sitios locales, no versionados
│   ├── php/
│   │   ├── php.ini                ← SOLO config; el Dockerfile vive en
│   │   └── xdebug.ini               f5sign-backend (ver regla 7)
│   ├── postgres/
│   │   ├── init-app-role.sh       ← roles a nivel CLUSTER (`make init-roles`)
│   │   └── init-test.sql
│   ├── rabbitmq/
│   │   ├── Dockerfile
│   │   ├── definitions.json + render-definitions.sh
│   │   ├── enabled_plugins
│   │   └── rabbitmq.conf
│   ├── redis/redis.conf
│   ├── minio/
│   │   ├── init-buckets.sh
│   │   └── lifecycle-{originals,temp}.json
│   ├── eu-dss/
│   │   ├── Dockerfile
│   │   ├── conf/logback.xml
│   │   └── scripts/{entrypoint,generate-self-signed-keystore,wait-for-tl}.sh
│   └── scripts/{agent-smoke,wait-for-healthy}.sh
└── scripts/
    └── wt-validate.sh             ← driver de los lanes `wt-*`
```

> No hay `.github/workflows/` en este repo: el CI de cada app vive en su propio repo.

## Layout del workspace y bind mounts

`f5sign-infra` es un **repo hermano** de los otros tres de codigo:

```
factor5_others/f5sign/
├── f5sign-backend/
├── f5sign-dashboard/
├── f5sign-signer/
├── f5sign-infra/           ← este repo
└── f5sign-docs/
```

Por tanto, los bind mounts en `docker-compose.yml` referencian los repos hermanos con rutas relativas:

- `../f5sign-backend:/var/www/html` (php-fpm, caddy, worker)
- `../f5sign-dashboard:/app` (contenedor dashboard)
- `../f5sign-signer:/app` (contenedor signer)

El directorio `./docker/` se refiere a subdirectorios **dentro de este repo** (config de caddy, php, etc.).

## Comandos

Todos los comandos se ejecutan desde la raiz de **este** repo:

| Accion | Comando |
|--------|---------|
| Arrancar stack | `docker compose up -d` o `make up` |
| Parar stack | `docker compose down` o `make down` |
| Destruir stack + volumenes | `make destroy` |
| Ver logs | `make logs` / `make logs s=php-fpm` |
| Shell en contenedor PHP | `make shell` |
| Consola Symfony | `make sf cmd="doctrine:migrations:migrate"` |
| Tests backend | `make test` |
| Tests signer (lint+typecheck+unit) | `make test-signer` |
| Tests signer (solo unit, Vitest) | `make test-signer-unit` |
| Tests signer E2E (Playwright, 4 perfiles) | `make test-signer-e2e` |
| Tests signer E2E (smoke mobile) | `make test-signer-e2e-mobile` |
| Reset BD (drop+create+migrate+fixtures) | `make reset-db` |
| Build imagenes | `docker compose build` o `make build` |
| Setup inicial | `make install` (build + up + init-db) |
| Build+push las imagenes propias de prod (GHCR) | `make release-prod TAG=v1.2.3` |
| Release SOLO backend | `make release-backend BACKEND_TAG=v1.2.4` |
| Validar merge de prod | `make config-prod PROD_ENV=.env.prod.example` |
| Crear los roles de cluster en un volumen ya existente | `make init-roles` |
| Deploy completo en host de prod | `make deploy-prod` (pull + up, req. `.env.prod`) |
| Deploy SOLO backend (php-fpm+worker) | `make deploy-backend` (bumpea `BACKEND_TAG` en `.env.prod`) |
| Deploy SOLO signer | `make deploy-signer` (bumpea `SIGNER_TAG` en `.env.prod`) |

> **Los tests SIEMPRE corren en Docker, nunca en local** (no contaminar la
> maquina con dependencias). Ver "Tests frontend en Docker" abajo.

### Modelo de 3 ficheros Compose (dev vs prod)

- **`docker-compose.yml`** — base **prod-safe**: backend + backing services, sin
  bind-mounts de codigo, sin xdebug, sin MinIO, sin puertos de debug.
- **`docker-compose.override.yml`** — **dev**, se auto-carga con `docker compose up`
  (`make up`). Aqui viven los servicios dev-only (caddy dev, dashboard, signer,
  minio/minio-init), los bind-mounts del codigo, xdebug y los puertos publicados.
- **`docker-compose.prod.yml`** — **prod**, explicito (`-f docker-compose.yml -f
  docker-compose.prod.yml`, no carga el override). Imagenes propias desde GHCR
  (`image:` + `pull_policy: always`), `APP_ENV=prod`, object storage en AWS/Linode
  (S3_* de `.env.prod`), `restart: always`, worker activo.

Servicios en prod (`docker-compose.prod.yml`): `caddy`, `php-fpm`, `worker`, `relay`,
`signer`, `postgresql`, `rabbitmq`, `redis`, `eu-dss`. **NO hay contenedor
`dashboard` ni MinIO** (el object storage es S3 externo). Flujo de release:
`make build-prod` (build local con buildx named contexts) -> `make push-prod` (GHCR)
-> en el host: `make deploy-prod`. Plantilla de entorno: `.env.prod.example`.

**Que se construye aqui y que no.** `make build-prod` = `build-backend` +
`build-rabbitmq-prod` + `build-eu-dss-prod`: **tres** imagenes propias. El resto no
se construye en este repo — `caddy` es la imagen oficial `caddy:2-alpine` (sirve
`docker/caddy/Caddyfile`), y **el signer se consume como imagen ya publicada por el
CI de su propio repo**, fijada con `SIGNER_TAG`, que es fail-closed (`:?`) para que
un `.env.prod` incompleto falle al renderizar en vez de arrancar algo inesperado.

**Tags independientes**: `BACKEND_TAG` (php-fpm + worker + relay) y `SIGNER_TAG`,
ambos fijados en `.env.prod`. Asi se puede deployar solo backend
(`deploy-backend`) o solo signer (`deploy-signer`) sin tocar el otro. `rabbitmq` y
`eu-dss` van pineadas (`4.0` / `6.4`).

## Puertos publicados (host → contenedor)

| Servicio | Host | Contenedor | Notas |
|----------|------|------------|-------|
| Caddy (API backend) | `http://localhost:8000` | `80` | Entrada a la API Symfony (`/api`) |
| Dashboard (Nuxt dev) | `http://localhost:3000` | `3000` | `pnpm install` tarda en 1er arranque — usa `make frontends-wait` |
| Signer (Nuxt dev) | `http://localhost:3001` | `3001` | Ver arriba |
| PostgreSQL (dev) | `localhost:5432` | `5432` | `f5sign` / `f5sign` |
| PostgreSQL (test) | `127.0.0.1:5433` | `5432` | `f5sign` / `f5sign_test_pw`, tmpfs, profile `test` |
| RabbitMQ AMQP | `localhost:5672` | `5672` | `f5sign` / `f5sign` (declarado en `definitions.json`) |
| RabbitMQ Management | `http://localhost:15672` | `15672` | UI web, mismas credenciales |
| RabbitMQ Prometheus | `localhost:15692` | `15692` | Metricas |
| Redis | _(interno)_ | `6379` | NO publicado a host (chocaba con otros redis del host); usa `make redis-cli`. Sin password (DBs: cache=0, locks=1, idempotency=2, rate-limiter=3) |
| MinIO API (S3) | `127.0.0.1:9100` | `9000` | `minioadmin` / `minioadmin` |
| MinIO Console | `http://127.0.0.1:9101` | `9001` | UI web |
| EU DSS | `127.0.0.1:8080` | `8080` | Expuesto solo en dev (override); healthy != TL cargadas |

Atajos: `make psql`, `make redis-cli`, `make rabbit-console`, `make minio-console`, `make mc cmd="ls local/"`, `make agent-smoke`.

## Tests frontend en Docker

**Regla dura: los tests (backend y frontend) SIEMPRE se ejecutan dentro del stack Docker, NUNCA en local.** El objetivo es no contaminar la maquina del dev/agente con dependencias (`node_modules`, navegadores de Playwright, stores de pnpm). Todo eso vive en volumes de Docker aislados.

Prerrequisito: el stack arriba (`make up`) — los targets de tests usan `--no-deps` y NO recrean servicios; asumen el stack ya corriendo.

| Target | Que hace | Donde corre |
|--------|----------|-------------|
| `make test-signer` | lint + typecheck + unit (Vitest) | contenedor `signer` (Alpine) |
| `make test-signer-unit` | solo unit (Vitest) | contenedor `signer` |
| `make test-signer-e2e` | E2E Playwright (4 perfiles) | contenedor dedicado `signer-e2e` |
| `make test-signer-e2e-mobile` | E2E smoke (mobile-iphone-se) | contenedor dedicado `signer-e2e` |

**Por que un contenedor E2E aparte (`signer-e2e`)**: el contenedor `signer` es `node:20-alpine` y **Playwright no soporta Alpine**. Los E2E corren en la imagen oficial `mcr.microsoft.com/playwright` (glibc + navegadores precargados), definida en `docker-compose.test.yml` (profile `test`). Apunta al dev server del servicio `signer` por la red interna (`PLAYWRIGHT_BASE_URL=http://signer:3001`); por eso `signer` debe estar arriba.

**Aislamiento del host**: tanto los servicios de dev (`signer`/`dashboard`) como `signer-e2e` guardan `node_modules`, `.nuxt`, la store de pnpm y los artefactos de Playwright en **volumes nombrados**. El bind-mount del repo es de solo-lectura en la practica; lo unico que aparece en el repo del host son directorios-punto-de-montaje vacios (`.nuxt`, `tests/e2e/.playwright`), gitignored.

> El **dashboard** aun no tiene suite de tests; cuando la tenga, replicar estos targets/servicios (`test-dashboard`, `dashboard-e2e`).

## Validacion efimera por worktree (para agentes en paralelo)

**Audiencia: uso AUTOMATIZADO por agentes.** Pensado para correr varios `/task-runner` a la vez, uno
por `git worktree`. Los targets de test normales (`make test`, `make test-signer*`) validan el **arbol
principal** (puertos host fijos, servicios `signer`/`postgres-test` compartidos) → dos worktrees
colisionarian y un worktree secundario ni siquiera esta bind-mounteado. Para validar un worktree usa los
targets `wt-*`, que levantan un **lane efimero y aislado al vuelo** y lo limpian al terminar.

| Target | Que hace |
|--------|----------|
| `make wt-signer src=<path>` | Lane signer: 1 contenedor Playwright que auto-hostea su dev server; lint+typecheck+unit+e2e |
| `make wt-backend src=<path>` | Lane backend: `postgres-test` (tmpfs) + php efimero; `composer install` + migrate (admin) + `composer test` (RLS real) |
| `make wt-ls` | Lista lanes activos (proyectos compose `wt-*`) |
| `make wt-down name=<lane>` | Tira un lane y sus volumenes |
| `make wt-gc` | Limpia volumenes/redes de worktrees borrados (preserva las cachas CAS `f5sign-*`) |

`src` es el path del worktree; si se omite, el wrapper usa el toplevel git del `cwd`.

Como funciona (`scripts/wt-validate.sh` + `docker-compose.wt.{signer,backend}.yml`):

- **Aislamiento por `STACK_NS=wt-<lane>`** (`<lane>` = basename del worktree). Re-namespacea red,
  volumenes y nombres porque todos interpolan `${STACK_NS}`. (Ojo: `-p`/`COMPOSE_PROJECT_NAME` por si
  solo NO basta — los recursos llevan `name:` atado a `STACK_NS`.)
- **Lanes SIN puertos al host** → cero colision; todo va por la red interna del lane. Los agentes no
  hacen browsing manual, asi que no se publica nada.
- **Backend ligero (2 contenedores)**: en test, messenger es `in-memory`, cache=filesystem, lock=flock
  → **sin Redis, sin RabbitMQ, sin eu-dss**. BD = `postgres-test` tmpfs **por lane** (reusa
  `docker/postgres/init-*.{sql,sh}`); migra como `f5sign` (superuser), testea como `f5sign_app`
  (non-superuser, RLS real). `var/` y `vendor/` van a volumenes por-lane (no contaminan el worktree).
- **Cachas CAS compartidas** entre lanes (volumenes external `f5sign-pnpm-store`, `f5sign-composer-cache`)
  → installs rapidos; `wt-down`/`wt-gc`/teardown NUNCA las borran.
- **Cap de concurrencia** (flock): signer=2, backend=1 (`WT_CAP_SIGNER`/`WT_CAP_BACKEND`). **En WSL no
  abuses** (riesgo OOM; ya colgo la maquina con 2 backend). Hay `mem_limit` como backstop.
- **Teardown automatico** con `trap` (`down -v --remove-orphans`). `make wt-gc` es la red de seguridad.

Para integrarlo con `/task-runner`: cuando un agente valida un worktree, en vez de `make test-signer`
usa `make wt-signer src=<worktree>` (idem backend). El stack compartido (eu-dss para tests PAdES) es
**Fase 3** (aun no implementada; ver el handoff en la raiz del workspace).

## Workers (Symfony Messenger)

El servicio `worker` consume el transport `async_events` (eventos de dominio cross-BC, drenados
por el `relay` — ADR-0031). Esta **bajo profile `workers` y NO arranca con `make up`** por defecto;
en prod `docker-compose.prod.yml` lo activa con `profiles: !reset []`.

**Motivo (actualizado):** el default-off ya **no** es un workaround. El transport existe y el worker
arranca limpio — es una eleccion deliberada para no tener la pipeline async corriendo en dev salvo
que se pida. *(Este parrafo decia que el worker "crashea en bucle" porque el backend no habia
definido el transport `async` (task T03.1.2); el backend lo definio como `async_events` y esa razon
quedo obsoleta.)*

⛔ **La trampa operativa sigue viva, y es la importante:** con el worker abajo, cualquier
`MessageBusInterface::dispatch()` asincrono se **encola pero no se consume**, y el dev o agente
puede creer que el mensaje se perdio. Peor: un evento cuya routing key no case con ningun binding
cae al alternate exchange y aterriza en `queue.events.unroutable`, que **nadie lee fuera de
`when@test`** — falla en silencio y con la pila entera en verde. Inspeccionar con
`make worker-status` (mensajes pendientes por cola) **antes** de concluir que algo no se emitio.

Ciclo de vida:

| Accion | Comando |
|--------|---------|
| Arrancar la pipeline async (worker + relay) | `make worker-up` |
| Parar worker | `make worker-down` |
| Reiniciar tras cambios en handlers | `make worker-restart` |
| Logs en tiempo real | `make worker-logs` |
| Estado + colas pendientes | `make worker-status` |

## EU DSS (Trusted Lists)

`eu-dss` puede estar **"healthy" sin ser utilizable**. El healthcheck de Compose valida que Tomcat responde (endpoint `/server-signing/keys`, ~20-30s tras arrancar), pero validar firmas eIDAS requiere ademas tener cargadas:

- **LOTL** (List of Trusted Lists): XML maestro en `https://ec.europa.eu/tools/lotl/eu-lotl.xml`.
- **Trusted Lists** de los estados miembros (~27 XMLs).

Primera vez (cache frio) tarda 30-90s adicionales tras el "healthy". En arranques posteriores sale de `dss-tl-cache` (volumen persistente) en segundos.

Comandos:

| Accion | Comando |
|--------|---------|
| Health basico (Tomcat) | `make dss-health` |
| Esperar a TL cargadas (default timeout 180s) | `make dss-wait-tl` |
| Con timeout custom | `make dss-wait-tl t=300` |

Tests de firma PAdES B-LT y validacion eIDAS **deben** depender de `dss-wait-tl`. `make smoke` muestra ambos estados por separado.

## Convenciones

- **Versiones pineadas** en `docker-compose.yml`. Nada de `latest` en imagenes (excepcion: `minio/mc` como init efimero).
- **Healthchecks** obligatorios en servicios de los que otros dependen (PostgreSQL, RabbitMQ, EU DSS).
- **Red unica** `f5sign-net` (bridge). Servicios se comunican por nombre DNS interno.
- **Volumenes nombrados** para datos persistentes (`pg-data`, `rabbitmq-data`, `redis-data`, `minio-data`, `dss-tl-cache`).
- **Puertos externos documentados** en README o directamente en comentarios del compose (mapa completo en `../f5sign-docs/Planning/F0-Infraestructura/EP01-Docker-y-Entorno/S01.1-Docker-Compose-para-Desarrollo/README.md`).
- **Variables de entorno**: `.env` nunca se commitea; `.env.example` si, con valores validos para desarrollo local.
- **Modos de despliegue**: `DEPLOYMENT_MODE=saas|dedicated` controla que bundles y servicios extras se activan. Detalle en `../f5sign-docs/Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md`.
- **Commits**: convenciones en `../f5sign-docs/Planning/AGENT-RUNBOOK.md` § 5.

## Ubicacion de specs relevantes

- **Modos de despliegue**: `../f5sign-docs/Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md`.
- **Infraestructura y compliance**: `../f5sign-docs/Arquitectura/Pilares/7. Infraestructura y Compliance.md`.
- **EU DSS**: `../f5sign-docs/Arquitectura/EU DSS - Guía de Integración.md`.
- **Contexto de desarrollo**: `../f5sign-docs/Implementación/Contexto de Desarrollo MVP.md`.
- **Planning por task**: `../f5sign-docs/Planning/F*/EP*/S*/T*.md`.

`f5sign-docs` es solo lectura desde aqui. Solo se escribe en `Planning/` para cerrar `Seguimiento` (ver AGENT-RUNBOOK).

## Reglas especificas del repo

1. **Pre-flight de los repos hermanos**: antes de `docker compose up`, los tres repos (`f5sign-backend`, `f5sign-dashboard`, `f5sign-signer`) deben existir al lado. Si no, los bind mounts montan directorios vacios y los contenedores fallan al arrancar.
2. **No commitees `.env`**. Solo `.env.example`.
3. **No hardcodees credenciales** en `docker-compose.yml`; siempre via `${VAR}` desde `.env`.
4. **Prod vs Dev**: el base `docker-compose.yml` es **prod-safe** (sin bind-mounts ni puertos de debug). El "dev shaping" vive en `docker-compose.override.yml` (auto-carga en `make up`); los overrides de produccion en `docker-compose.prod.yml` (explicito: `-f docker-compose.yml -f docker-compose.prod.yml`, NO carga el override). Ver "Modelo de 3 ficheros Compose" arriba.
5. **No modifiques migraciones de BD desde aqui**. Esquemas son responsabilidad de `f5sign-backend` (`doctrine:migrations:*`).
6. **Logs y health**: todos los servicios deben exponer endpoints o comandos de health; los healthchecks del compose dependen de ello.
7. **Imagenes custom**: los `Dockerfile` en `docker/` son la fuente de las imagenes propias de INFRA (rabbitmq, eu-dss). No builds ad-hoc fuera de compose. **Excepcion — la imagen PHP no se define aqui**: dev y prod salen del mismo `f5sign-backend/Dockerfile` (`target: dev` para el contenedor local, el target por defecto para la de produccion que publica su CI). Antes habia un segundo Dockerfile en `docker/php/`, con la misma base y las mismas extensiones, que habia que sincronizar a mano; se retiro para que la version de PHP y el juego de extensiones no puedan divergir entre dev y prod. En `docker/php/` solo queda configuracion (`php.ini`, `xdebug.ini`), que se bind-montea.
8. **Tests SIEMPRE en Docker, NUNCA en local**: ni backend ni frontend se testean/lintean/buildean en la maquina host. Usa los targets `make test*` (ver "Tests frontend en Docker"). No ejecutes `pnpm`/`npm`/`composer` install ni tests directamente en el host: contamina la maquina y diverge del entorno reproducible del stack.
