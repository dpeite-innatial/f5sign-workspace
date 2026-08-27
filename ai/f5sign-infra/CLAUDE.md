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
- **PostgreSQL** 18 alpine (imagen propia: `docker/postgres/Dockerfile` = base oficial + pgBackRest)
- **RabbitMQ** 4.2 management (imagen propia: `docker/rabbitmq/Dockerfile` + plugin delayed-message v4.2.0)
- **Redis** 8 alpine
- **MinIO** latest + `mc` para init
- **EU DSS** (`nowina-solutions/dss-webapp:6.4`, imagen Java)
- **PHP** 8.5 fpm alpine (el Dockerfile vive en `f5sign-backend`, ver regla 7)
- **Node** 24 alpine (para los contenedores de dev de dashboard y signer)
- **GNU Make** para el Makefile

⚑ **Versiones revisadas y subidas el 2026-08-26.** Esta lista tenia **dos entradas falsas**: decia
*"RabbitMQ 3.13"* cuando el compose llevaba 4.0 desde hacia meses (un major entero de desfase) y
*"PHP 8.4"* cuando `f5sign-backend/Dockerfile` es `php:8.5-fpm-alpine`. En el mismo repaso se
subio **Node 20 -> 24** (la 20 esta FUERA DE SOPORTE desde el 2026-04-30), **Redis 7 -> 8** y
**RabbitMQ 4.0 -> 4.2**. ⛔ **RabbitMQ no puede pasar de 4.2** aunque el broker publique 4.3: el
plugin `delayed-message-exchange` se queda en v4.2.0 y su serie debe seguir a la del broker.
PostgreSQL 16 -> 18 se hizo el mismo dia (ver README § *Copias de seguridad*). EU DSS 6.4 se
queda: la 6.5 solo tiene RC1.

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
│   └── scripts/{agent-smoke,check-event-dlx,wait-for-healthy}.sh
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
| **Estado de las migraciones** | **`make migrate-status`** — ⛔ no lo consultes de otra forma, ver abajo |
| Deshacer la ultima migracion (NO destruye la BD) | `make migrate-prev` |
| Migrar a una version concreta (arriba o abajo) | `make migrate-to v=Version...` |
| Build imagenes | `docker compose build` o `make build` |
| Setup inicial | `make install` (build + up + init-db) |
| Build+push las imagenes propias de prod (GHCR) | `make release-prod TAG=v1.2.3` |
| Release SOLO backend | `make release-backend BACKEND_TAG=v1.2.4` |
| Validar merge de prod | `make config-prod PROD_ENV=.env.prod.example` |
| Crear los roles de cluster en un volumen ya existente | `make init-roles` |
| Deploy completo en host de prod | `make deploy-prod` (preflight + pull + up, req. `.env.prod`) |
| Deploy SOLO backend (php-fpm+worker) | `make deploy-backend` — ⚠ **NO incluye el relay**, ver abajo |
| Deploy SOLO signer | `make deploy-signer` (bumpea `SIGNER_TAG` en `.env.prod`) |
| **Copia de la ventana de despliegue** | **`make backup-prod LABEL=...`** — el suelo del corte, ver abajo |
| **Restaurar prod** | **`make restore-prod CONFIRM=si-restaurar`** — destructivo; `TARGET="fecha hora"` para PITR |
| Backup continuo (full/incremental) | `make backup-full-prod` / `make backup-incr-prod` (cron; ver README) |
| Estado del archivado de WAL | `make pgbackrest-status-prod` — ⛔ el watchdog, ver abajo |
| Secretos que ningun backup de BD cubre | `make backup-secrets` (.env.prod + seal.p12 + certs, cifrado) |
| **Migraciones en prod** | **`make migrate-prod`** — ⛔ no va dentro de `deploy-prod`, ver abajo |
| Estado de las migraciones en prod | `make migrate-status-prod` (mismo motivo que `migrate-status`) |
| Roles de cluster en el host de prod | `make init-roles-prod` — ANTES de migrar si el release trae roles |
| Solo descargar las imagenes del release | `make pull-prod` (sin tocar lo que corre) |

> **No enumero aqui los 21 targets `*-prod`**, que es la lista que se queda atras.
> `make help` los lista todos; **`README.md` § *Despliegue en preprod / produccion* §5 da la SECUENCIA**,
> que es lo que de verdad hace falta y no cabe en una tabla: hay dos, una para releases aditivos y otra
> para los que no lo son.

⛔ **El estado de las migraciones SOLO se consulta con `make migrate-status`, y el motivo es peor que el
de `migrate-prev`.** Preguntarlo con `make sf` o un `docker compose exec php-fpm` pelado corre como
`f5sign_app`, que **no ve `doctrine_migration_versions`**. No falla: responde tan tranquilo `Executed 0` y
marca las 26 migraciones como *not migrated* sobre una base que esta al dia. Donde `migrate-prev` revienta
ruidosamente con *permission denied* y te enteras, esto te contesta una cifra falsa. ⚠ **Y la reaccion
natural a "la BD esta vacia" es `make reset-db`, que la vacia de verdad y se lleva la API key
aprovisionada, que solo se muestra una vez.** Medido el 2026-08-21: el mismo comando decia `0 de 26` como
`f5sign_app` y *"Already at latest version"* como owner.
⚑ **Anadido 2026-08-25.** El target existe desde el 2026-08-21 (`07b29b1`) y esta tabla, escrita el 08-18,
no lo listaba — o sea que documentaba las dos formas ruidosas y no la unica que dice la verdad.

⛔ **`migrate-prod` NO va dentro de `deploy-prod`, y el orden entre los dos depende del release.**
⚑ **Reescrito el 2026-08-27: hasta hoy esta regla decia "aditiva -> deploy primero", y eso induce al
error contrario en un caso real que acaba de aparecer.** El eje NO es aditiva/no aditiva. Son DOS
compatibilidades independientes, y hay que preguntarse las dos:

| | Si la respuesta es NO |
|---|---|
| ¿Aguanta el **codigo VIEJO** el **esquema NUEVO**? | migrar **despues** de desplegar |
| ¿Aguanta el **codigo NUEVO** el **esquema VIEJO**? | migrar **antes** de desplegar |

- **Aditiva y el codigo nuevo no la necesita** (el caso comun hasta 2026-07): las dos respuestas son si,
  `deploy-prod` -> `migrate-prod`, sin ventana.
- **NO aditiva** (`RENAME`, `DROP COLUMN`, `SET NOT NULL`, `ALTER COLUMN ... TYPE`): el codigo viejo NO
  aguanta el esquema nuevo -> migrar antes, y la ventana entre ambos es un corte duro.
- ⛔ **Aditiva pero el codigo nuevo EXIGE la columna**: la trampa. Es aditiva, asi que la regla vieja
  mandaba desplegar primero — y el codigo nuevo arrancaria contra una tabla sin la columna. Hay que
  **migrar antes**. Caso real que destapo esto: el `epoch_floor_position` que el backend anade a
  `platform.event_checkpoint` para que el relay sobreviva a un dump/restore (ver README seccion
  PostgreSQL, la nota del contador de transacciones).

Quien prepara el release es quien tiene que contestar las dos preguntas. La secuencia completa, con la
ventana de corte, esta en `README.md` §5; no la dupliques aqui.

⚑ **Anadido 2026-08-26, y con esto se cae una frase que hasta hoy era la recomendada.** `migrate-prod` corre
la consola en un contenedor **efimero de la imagen NUEVA** (`docker compose run --rm --no-deps -u www-data`),
sin tocar el que sirve trafico — que es lo que hace posible migrar ANTES de desplegar. Hasta el 2026-08-26 era
un `exec` sobre el contenedor **en marcha**, y eso no solo impedia ese orden: lo hacia **invisible**. Las
migraciones viajan dentro de la imagen, asi que `exec` antes de desplegar solo veia el juego VIEJO y respondia
*"Already at latest version"* con exit 0. Un no-op que se lee como verde, y despues el deploy dejaba la API en
500 hasta que alguien volvia a migrar. **Si lees un runbook que diga "migrate-prod va siempre despues de
deploy-prod", es anterior a esta fecha.**

⚑ **Corregido 2026-08-26, y con esto se cae la afirmacion central de este bloque.** Decia que `backup-prod` era *"el UNICO rollback que existe"* y que *"no hay `restore-prod` ni ningun target de rollback"*. Era cierto: la receta de `pg_restore` se imprimia en un `echo` que nadie habia ejecutado nunca. Ahora hay **archivado continuo de WAL con pgBackRest** (PITR) y un **`make restore-prod`** de verdad, con confirmacion explicita. Puesta en marcha, cron y el orden —que no se adivina: la stanza se crea con el archivado APAGADO— en `README.md` § *Copias de seguridad y recuperacion*.

⛔ **El watchdog no es `failed_count`.** Ese contador de `pg_stat_archiver` es acumulativo y no se resetea: un cluster sano arrastra para siempre los fallos previos a la stanza (medido: 7 con el archivado perfecto). Lo que decide es si `last_failed_time` es POSTERIOR a `last_archived_time`. Y si el archivado se rompe, Postgres RETIENE el WAL y `pg_wal` llena el disco hasta parar las escrituras. Las dos cosas las mira `make pgbackrest-status-prod`.

⛔ **Y antes de migrar en prod, `make backup-prod` igual.** Sigue siendo el suelo de la ventana:
`migrate-prev` y `migrate-to` siguen siendo **dev-only** (van contra el stack de desarrollo), y el `down()` de una
migracion no aditiva es destructivo por definicion — el de un `DROP COLUMN` no devuelve los datos. El target
verifica lo que produce y **borra el fichero si no pasa**, para que no quede nada con pinta de copia. En una
ventana de corte van **dos** copias con `LABEL=` distinto y solo la de despues del corte es la que se
restaura; el porque esta en `README.md` §5.

> **Los tests SIEMPRE corren en Docker, nunca en local** (no contaminar la
> maquina con dependencias). Ver "Tests frontend en Docker" abajo.

### Modelo de 3 ficheros Compose (dev vs prod)

- **`docker-compose.yml`** — base **prod-safe**: backend + backing services, sin
  bind-mounts de codigo, sin xdebug, sin MinIO, sin puertos de debug.
- **`docker-compose.override.yml`** — **dev**, se auto-carga con `docker compose up`
  (`make up`). Aqui viven los servicios dev-only (caddy dev, dashboard, signer,
  minio/minio-init, **mailpit**), los bind-mounts del codigo, xdebug y los puertos
  publicados. Enumeralos en el propio fichero, que es donde no se quedan atras.

  ⚑ **Mailpit es el sumidero SMTP de dev, y hasta 2026-08-26 este documento solo lo nombraba como
  dependencia del lane de worktree** — o sea que un agente que quisiera comprobar un email de
  notificacion no tenia donde mirar. `MAILER_DSN` apunta ahi en dev; en prod **no hay Mailpit** y esa
  variable es un `:?` que tiene que llevar un transporte real.
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

⚠ **`BACKEND_TAG` gobierna TRES imagenes pero `deploy-backend` redespliega DOS: el `relay` se queda
con la vieja.** Las dos frases de arriba son ciertas por separado y juntas son una trampa — el target
hace `pull php-fpm worker` + `up -d php-fpm worker`, y su nombre lo dice ("SOLO backend (php-fpm +
worker)"), pero quien lea "BACKEND_TAG = php-fpm + worker + relay" dara por hecho que bumpear el tag y
correr `deploy-backend` mueve los tres. **Si el release cambia el esquema, usa `deploy-prod`**: un
relay con codigo viejo contra un esquema migrado no falla ruidosamente — drena el event-log y publica
mal. (Anotado 2026-08-26 preparando el despliegue de 28 migraciones; el desajuste llevaba ahi desde
que existe el target.)

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
| Mailpit (UI + SMTP sink) | `http://127.0.0.1:8025` | `8025` | **Donde aterrizan los emails en dev.** Sin credenciales |

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
- **Backend con paridad de dependencias (6 contenedores)**: `backend/.env.test` resuelve **cinco**
  hosts por DNS (`postgres-test`, `minio`, `rabbitmq`, `mailpit`, `eu-dss`) y la suite **no tiene ni un
  `markTestSkipped`** → lo que no resuelve **no se salta, falla**. El lane levanta cuatro de los cinco
  **por lane**, porque los cuatro guardan estado que los tests mutan y compartirlos reproduce BL-138 en
  otro sustrato: postgres (xmin es de **cluster**), minio (los 5 `S3_BUCKET_*` son nombres fijos → dos
  lanes se pisan las claves), mailpit (buzon unico acumulativo) y rabbitmq (colas compartidas). Redis
  sigue fuera: cache=filesystem y lock=flock, los tests no lo tocan. BD = `postgres-test` tmpfs por lane
  (reusa `docker/postgres/init-*.{sql,sh}`); migra como `f5sign` (superuser), testea como `f5sign_app`
  (non-superuser, RLS real). `var/` y `vendor/` van a volumenes por-lane (no contaminan el worktree).
- **`eu-dss` es el unico COMPARTIDO**, y por lo que **es**, no por lo que cuesta: peticion/respuesta pura,
  su unico estado es la cache de Trusted Lists (solo lectura, identica para todos). Se alcanza con
  `eu-dss-proxy` (socat), el **unico** contenedor del lane en las dos redes: si el contenedor de php
  estuviera en ambas, `minio`/`rabbitmq`/`mailpit` resolverian **ambiguamente** y un lane acabaria
  escribiendo en el MinIO del stack principal. `wt-validate.sh` **aborta con mensaje explicito** si el
  stack compartido no esta arriba (`SHARED_NS`, por defecto `f5sign`); `WT_REQUIRE_DSS=0` corre igual, a
  sabiendas de que los tests de sellado iran en rojo.
- **`mem_limit` y `cpus` explicitos en TODOS los servicios del lane** (`WT_*_MEM` / `WT_*_CPUS`). Techo
  con los defaults: **~3.0 GiB y ~9.25 CPUs** por lane backend; uso real medido en reposo, ~280 MiB. El
  tope importa sobre todo en minio: sin el se queda ~950 MiB de holgura del runtime de Go (medido en el
  stack principal) frente a **84 MiB** bajo un cap de 512m.
- **Los cinco gates en el lane, seleccionables con `WT_GATES`** (default `lint arch phpstan test`;
  `infection` es **opt-in** porque tarda ordenes de magnitud mas). Dos cosas que no eran cableado:
  **PHPStan** falla en el lane por el motivo CONTRARIO al del arbol principal — alli el dump del
  contenedor esta rancio, aqui **no existe**, porque `var/` es un volumen por lane que nace vacio y el
  `composer install` limpia cache en `env=test`, no en dev. El gate lo genera y **comprueba que esta**
  antes de analizar. **Infection** necesita el limite de memoria en un `.ini` montado
  (`docker/php/wt-infection.ini`), no en un `php -d`: relanza phpunit como hijo y la bandera no se
  hereda. Su valor es un punto de partida, no una medicion.
- **Pasos separados, no un `sh -lc` encadenado**: install / migraciones / cada gate son `run`
  distintos, para que un fallo diga **cual** murio. Ademas se fija
  `COMPOSER_PROCESS_TIMEOUT` (`WT_COMPOSER_TIMEOUT`, default 1800): `composer test` es un *script* de
  Composer y Composer mata sus scripts a los **300 s** por defecto — el backend no fija
  `config.process-timeout`, asi que sin esto la suite muere por reloj sin que falle nada.
- **Cachas CAS compartidas** entre lanes (volumenes external `f5sign-pnpm-store`, `f5sign-composer-cache`)
  → installs rapidos; `wt-down`/`wt-gc`/teardown NUNCA las borran.
- **Cap de concurrencia** (flock): signer=2, backend=1 (`WT_CAP_SIGNER`/`WT_CAP_BACKEND`). **En WSL no
  abuses** (riesgo OOM; ya colgo la maquina con 2 backend). Hay `mem_limit` como backstop.
- **Teardown automatico** con `trap` (`down -v --remove-orphans`). `make wt-gc` es la red de seguridad.

⛔ **No te fabriques un `docker run` ad-hoc en lugar del lane.** Es la alternativa que la gente
improvisa cuando el lane le parece de mas, y cuesta horas por tres motivos ya medidos (sesion de
backend, 2026-08-18), los tres invisibles mientras pasan:

- **Se bloquea en `var/cache`.** Un `docker run` a mano monta `var/` desde el arbol de trabajo, asi
  que **dos corridas concurrentes se quedan esperando el lock**: 40+ minutos sin una sola linea de
  salida, y se lee como *"los tests son lentos"*. El lane no lo sufre porque `var/` es el volumen
  `wt-backend-var`, propio de cada lane. Si aun asi necesitas el `docker run`, anadele
  `--tmpfs /var/www/html/var/cache`.
- **Un `timeout` del HOST sobre `docker run` no mata el contenedor**, solo al cliente: el contenedor
  sigue vivo sosteniendo locks, y se acumulan zombis (nueve, en el caso medido). El `timeout` tiene
  que ir DENTRO: `sh -c "timeout 420 php ..."`. `wt-validate.sh` no tiene este problema — su `trap`
  hace el `down -v` tambien con TERM, verificado cortando una corrida con `timeout`.
- **Limpiarlos luego es peor que el problema.** `docker ps --filter ancestor=f5sign/backend:dev`
  empareja **tambien el `php-fpm` del stack compartido**, que corre esa misma imagen: un `xargs
  docker kill` sobre ese filtro tumba el stack de todo el mundo (paso, ~40 s).

Y el argumento definitivo, medido sobre el mismo arbol y el mismo commit: contenedor ad-hoc con BD
aislada pero **cluster compartido** -> 1681 tests, **5 fallos** (todos del relay); `make wt-backend`
con **cluster propio** -> 1681 tests, **OK**. Aislar la base no basta; hay que aislar el cluster
(BL-138). Es el contrafactual que las corridas verdes del lane, por si solas, no demuestran.

Para integrarlo con `/task-runner`: cuando un agente valida un worktree, en vez de `make test-signer`
usa `make wt-signer src=<worktree>` (idem backend). El stack compartido para los tests PAdES **ya
existe**: es el propio stack de dev (`make up` + `make dss-wait-tl`), del que el lane consume solo
`eu-dss` por proxy — ver los dos puntos de arriba.

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

## RabbitMQ — como llega (y como NO llega) la topologia

La declara `docker/rabbitmq/definitions.json`, que es la fuente de verdad: el backend corre con
`auto_setup: false` y no declara nada. Llega al contenedor por **bind-mount**, y de ahi salen las dos
trampas, las dos silenciosas:

1. ⛔ **Un `up -d` NO recarga `definitions.json`.** Su contenido no entra en el hash de configuracion
   del contenedor, asi que `make deploy-prod` no se entera de que cambio. Hace falta
   `make reload-rabbitmq`, que ademas lo pasa **por STDIN desde el host**: un bind-mount de fichero
   UNICO se ata al inode y git reemplaza por rename, asi que tras un `git pull` el contenedor en marcha
   sigue viendo el fichero VIEJO — para siempre. Sin esto una cola nueva no existe y el worker muere en
   bucle con `NOT_FOUND - no queue '...' in vhost '/'`.
2. ⛔ **Los argumentos de una cola son INMUTABLES, y el import no falla: se queda con los viejos y
   reporta exito.** Redeclarar una cola existente con otro `x-dead-letter-exchange` no cambia nada y no
   avisa. Por eso `reload-rabbitmq` no termina en el import: verifica con
   `docker/scripts/check-event-dlx.sh` y se pone rojo si el desvio no esta. Arreglarlo exige **borrar y
   recrear** las colas — `make rabbit-check-dlx-prod` para mirar, `make rabbit-recreate-event-queues-prod`
   para arreglar (exige profundidad 0 y cero consumidores; `FORCE=1` asume la perdida).

⚠ Por que importa: sin desvio, un mensaje indescifrable se rechaza contra ningun destino, y rechazar
sin desvio es **descartar**. Con la pila entera en verde.

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
- **Volumenes nombrados** para datos persistentes **en dev**. Los declara el bloque `volumes:` de cada
  fichero compose (base, override y prod declaran los suyos): enumeralos ahi, no aqui.
  ⛔ **En PROD los datos de Postgres NO son un volumen nombrado: son un bind mount del host**
  (`PGDATA_HOST_DIR`, por defecto `/srv/f5sign/pgdata`), y esa es justo la propiedad que se compro —
  Docker no gestiona la ruta, asi que ni `docker compose down -v`, ni `docker volume prune`, ni
  `docker system prune --volumes` pueden llevarse la BD por descuido; solo un `rm` explicito.
  ⚑ **Corregido 2026-08-26**: esta linea decia "Volumenes nombrados para datos persistentes
  (`pg-data`, ...)" sin distinguir dev de prod, o sea que afirmaba lo contrario de la propiedad de
  seguridad que introdujo `09ec6e2` — y lo afirmaba justo donde alguien va a mirar si es seguro correr
  un `prune`. ⚠ Migrar un prod anterior a ese commit no es automatico: `make deploy-prod` corre antes
  `preflight-prod`, que se pone rojo si el bind mount esta vacio y el volumen viejo sigue existiendo, e
  imprime la receta de copia.
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
