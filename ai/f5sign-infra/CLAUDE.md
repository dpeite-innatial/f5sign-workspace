# f5sign-infra — Operating guide for Claude Code

Infrastructure repo for the F5Sign product. Contains the Docker orchestration (local and production), custom Dockerfiles, Caddy configuration, init scripts and automation (`Makefile`, CI/CD pipelines where applicable). It's the repo that starts the full stack: backend + dashboard + signer + services (PostgreSQL, RabbitMQ, Redis, MinIO, EU DSS).

## Repo purpose

- **Orchestration**: `docker-compose.yml` that brings up all the MVP services in a single command.
- **Custom Dockerfiles**: for services that don't have a valid official image (PHP-FPM with Symfony extensions, EU DSS build, MinIO init scripts).
- **Service configuration**: `docker/caddy/Caddyfile{,.dev}`, `docker/php/php.ini`, `docker/minio/init-buckets.sh`, etc.
- **Makefile**: automation for the team (`make up`, `make test`, `make sf cmd=...`).
- **Env template**: `.env.example` with all the shared variables.
- **CI/CD** (added in later phases): build/deploy workflows for the three apps.

## Stack

- **Docker** / **Docker Compose** (v2)
- **Caddy** 2 alpine (`caddy:2-alpine`, reverse proxy for the API in dev and prod)
- **PostgreSQL** 18 alpine (own image: `docker/postgres/Dockerfile` = official base + pgBackRest)
- **RabbitMQ** 4.2 management (own image: `docker/rabbitmq/Dockerfile` + delayed-message plugin v4.2.0)
- **Redis** 8 alpine
- **MinIO** `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` (dev only) + **AWS CLI** `2.36.47` for init. ⚑ Corrected 2026-09-17: it said *"MinIO latest + `mc` for init"*; that day Docker Hub pulled `minio/minio` and `minio/mc`, init moved to the AWS CLI (reason in the header of `docker/minio/init-buckets.sh`) and `mc` became the dev `mc` service (profile `tools`) for the shortcuts
- **EU DSS** (`nowina-solutions/dss-webapp:6.4`, Java image)
- **PHP** 8.5 fpm alpine (the Dockerfile lives in `f5sign-backend`, see rule 7)
- **Node** 24 alpine (for the dashboard and signer dev containers)
- **GNU Make** for the Makefile

⚑ **Versions reviewed and bumped on 2026-08-26.** This list had **two false entries**: it said
*"RabbitMQ 3.13"* when the compose had been on 4.0 for months (a full major version behind) and
*"PHP 8.4"* when `f5sign-backend/Dockerfile` is `php:8.5-fpm-alpine`. In the same pass we
bumped **Node 20 -> 24** (20 has been OUT OF SUPPORT since 2026-04-30), **Redis 7 -> 8** and
**RabbitMQ 4.0 -> 4.2**. ⛔ **RabbitMQ can't go past 4.2** even if the broker ships 4.3: the
`delayed-message-exchange` plugin stays at v4.2.0 and its series has to track the broker's.
PostgreSQL 16 -> 18 was done the same day (see README § *Copias de seguridad*). EU DSS stays at
6.4: 6.5 only has an RC1.

## Repo structure

```
f5sign-infra/
├── docker-compose.yml             ← prod-safe base
├── docker-compose.override.yml    ← dev overrides (auto-loads on `up`)
├── docker-compose.prod.yml        ← production overrides (GHCR images)
├── docker-compose.test.yml        ← test services (profile `test`)
├── Makefile
├── .env.example                   ← dev environment
├── .env.prod.example              ← prod environment (template)
├── .gitignore
├── docker-compose.mock-signer.yml ← simulated signer
├── docker-compose.wt.{signer,backend}.yml  ← ephemeral per-worktree lanes
├── docker/
│   ├── caddy/
│   │   ├── Caddyfile              ← prod
│   │   ├── Caddyfile.dev          ← dev
│   │   └── conf.d/                ← local sites, not version-controlled
│   ├── php/
│   │   ├── php.ini                ← config ONLY; the Dockerfile lives in
│   │   └── xdebug.ini               f5sign-backend (see rule 7)
│   ├── postgres/
│   │   ├── init-app-role.sh       ← CLUSTER-level roles (`make init-roles`)
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
│   └── scripts/{agent-smoke,check-event-dlx,check-seal,wait-for-healthy}.sh
└── scripts/
    └── wt-validate.sh             ← driver for the `wt-*` lanes
```

> There's no `.github/workflows/` in this repo: each app's CI lives in its own repo.

## Workspace layout and bind mounts

`f5sign-infra` is a **sibling repo** to the other three code repos:

```
factor5_others/f5sign/
├── f5sign-backend/
├── f5sign-dashboard/
├── f5sign-signer/
├── f5sign-infra/           ← this repo
└── f5sign-docs/
```

So the bind mounts in `docker-compose.yml` reference the sibling repos with relative paths:

- `../f5sign-backend:/var/www/html` (php-fpm, caddy, worker)
- `../f5sign-dashboard:/app` (dashboard container)
- `../f5sign-signer:/app` (signer container)

The `./docker/` directory refers to subdirectories **inside this repo** (caddy, php config, etc.).

## Commands

All commands run from the root of **this** repo:

| Action | Command |
|--------|---------|
| Start the stack | `docker compose up -d` or `make up` |
| Stop the stack | `docker compose down` or `make down` |
| Destroy stack + volumes | `make destroy` |
| View logs | `make logs` / `make logs s=php-fpm` |
| Shell in PHP container | `make shell` |
| Symfony console | `make sf cmd="doctrine:migrations:migrate"` |
| Backend tests | `make test` |
| Signer tests (lint+typecheck+unit) | `make test-signer` |
| Signer tests (unit only, Vitest) | `make test-signer-unit` |
| Signer E2E tests (Playwright, 4 profiles) | `make test-signer-e2e` |
| Signer E2E tests (mobile smoke) | `make test-signer-e2e-mobile` |
| Reset DB (drop+create+migrate+fixtures) | `make reset-db` |
| **Migration status** | **`make migrate-status`** — ⛔ don't check it any other way, see below |
| Undo the last migration (does NOT destroy the DB) | `make migrate-prev` |
| Migrate to a specific version (up or down) | `make migrate-to v=Version...` |
| Build images | `docker compose build` or `make build` |
| Initial setup | `make install` (build + up + init-db) |
| Build+push prod's own images (GHCR) | `make release-prod TAG=v1.2.3` |
| Release backend ONLY | `make release-backend BACKEND_TAG=v1.2.4` |
| Validate prod merge | `make config-prod PROD_ENV=.env.prod.example` |
| Create cluster roles on an already-existing volume | `make init-roles` |
| Full deploy on the prod host | `make deploy-prod` (preflight + pull + up, requires `.env.prod`) |
| Deploy backend ONLY (php-fpm+worker) | `make deploy-backend` — ⚠ **does NOT include the relay**, see below |
| Deploy signer ONLY | `make deploy-signer` (bumps `SIGNER_TAG` in `.env.prod`) |
| **Deployment-window backup** | **`make backup-prod LABEL=...`** — the floor of the cutover, see below |
| **Restore prod** | **`make restore-prod CONFIRM=si-restaurar`** — destructive; `TARGET="fecha hora"` for PITR |
| Continuous backup (full/incremental) | `make backup-full-prod` / `make backup-incr-prod` (cron; see README) |
| WAL archiving status | `make pgbackrest-status-prod` — ⛔ the watchdog, see below |
| Secrets no DB backup covers | `make backup-secrets` (.env.prod + seal.p12 + certs, encrypted) |
| **Migrations in prod** | **`make migrate-prod`** — ⛔ does not go inside `deploy-prod`, see below |
| Migration status in prod | `make migrate-status-prod` (same reason as `migrate-status`) |
| Cluster roles on the prod host | `make init-roles-prod` — BEFORE migrating if the release brings roles |
| Only download the release images | `make pull-prod` (without touching what's running) |

> **I'm not listing the 21 `*-prod` targets here**, since that's the list that goes stale.
> `make help` lists all of them; **`README.md` § *Despliegue en preprod / produccion* §5 gives the SEQUENCE**,
> which is what actually matters and doesn't fit in a table: there are two, one for additive releases and
> one for releases that aren't.

⛔ **Migration status is ONLY checked with `make migrate-status`, and the reason is worse than the one
for `migrate-prev`.** Asking with `make sf` or a bare `docker compose exec php-fpm` runs as
`f5sign_app`, which **can't see `doctrine_migration_versions`**. It doesn't fail: it calmly answers `Executed 0` and
marks all 26 migrations as *not migrated* on a database that's fully up to date. Where `migrate-prev` blows up
loudly with *permission denied* and you notice, this one hands you a false number. ⚠ **And the natural
reaction to "the DB is empty" is `make reset-db`, which really does empty it and takes the provisioned
API key with it — the one that's only shown once.** Measured on 2026-08-21: the same command said `0 de 26`
as `f5sign_app` and *"Already at latest version"* as owner.
⚑ **Added 2026-08-25.** The target has existed since 2026-08-21 (`07b29b1`) and this table, written on 08-18,
didn't list it — meaning it documented the two noisy ways and not the only one that tells the truth.

⛔ **`migrate-prod` does NOT go inside `deploy-prod`, and the order between the two depends on the release.**
⚑ **Rewritten on 2026-08-27: until today this rule said "additive -> deploy first", and that leads to the
opposite mistake in a real case that just came up.** The axis is NOT additive/non-additive. There are TWO
independent compatibilities, and both need to be asked:

| | If the answer is NO |
|---|---|
| Does the **OLD code** tolerate the **NEW schema**? | migrate **after** deploying |
| Does the **NEW code** tolerate the **OLD schema**? | migrate **before** deploying |

- **Additive and the new code doesn't need it** (the common case through 2026-07): both answers are yes,
  `deploy-prod` -> `migrate-prod`, no window.
- **NOT additive** (`RENAME`, `DROP COLUMN`, `SET NOT NULL`, `ALTER COLUMN ... TYPE`): the old code does NOT
  tolerate the new schema -> migrate first, and the window between the two is a hard cutover.
- ⛔ **Additive but the new code REQUIRES the column**: the trap. It's additive, so the old rule said
  to deploy first — and the new code would start up against a table missing the column. You have to
  **migrate first**. Real case that exposed this: the `epoch_floor_position` the backend adds to
  `platform.event_checkpoint` so the relay survives a dump/restore (see README PostgreSQL section,
  the note on the transaction counter).

Whoever prepares the release is the one who has to answer both questions. The complete sequence, with the
cutover window, is in `README.md` §5; don't duplicate it here.

⚑ **Added on 2026-08-26, and this drops a line that until today was the recommended one.** `migrate-prod` runs
the console in an **ephemeral container of the NEW image** (`docker compose run --rm --no-deps -u www-data`),
without touching the one serving traffic — which is what makes it possible to migrate BEFORE deploying. Until
2026-08-26 it was an `exec` on the **running** container, and that not only blocked that order: it made it
**invisible**. Migrations travel inside the image, so `exec` before deploying only saw the OLD set and replied
*"Already at latest version"* with exit 0. A no-op that reads as green, and afterward the deploy would leave the
API returning 500 until someone migrated again. **If you read a runbook that says "migrate-prod always goes after
deploy-prod", it predates this date.**

⚑ **Corrected on 2026-08-26, and this drops the central claim of this block.** It said `backup-prod` was *"the ONLY rollback that exists"* and that *"there's no `restore-prod` or any rollback target"*. That was true: the `pg_restore` recipe was printed in an `echo` nobody had ever run. Now there's **continuous WAL archiving with pgBackRest** (PITR) and a real **`make restore-prod`**, with explicit confirmation. Setup, cron and the order — which isn't obvious: the stanza is created with archiving TURNED OFF — in `README.md` § *Copias de seguridad y recuperacion*.

⛔ **The watchdog isn't `failed_count`.** That `pg_stat_archiver` counter is cumulative and never resets: a healthy cluster carries the pre-stanza failures forever (measured: 7 with archiving working perfectly). What decides it is whether `last_failed_time` is LATER than `last_archived_time`. And if archiving breaks, Postgres RETAINS the WAL and `pg_wal` fills the disk until writes stop. `make pgbackrest-status-prod` checks both.

⛔ **And before migrating in prod, `make backup-prod` all the same.** It's still the floor of the window:
`migrate-prev` and `migrate-to` are still **dev-only** (they run against the development stack), and the `down()` of a
non-additive migration is destructive by definition — a `DROP COLUMN`'s doesn't give the data back. The target
verifies what it produces and **deletes the file if it fails**, so nothing that looks like a backup is left behind. In a
cutover window there are **two** backups with different `LABEL=` values and only the one taken after the cutover gets
restored; the reasoning is in `README.md` §5.

> **Tests ALWAYS run in Docker, never locally** (don't pollute the
> machine with dependencies). See "Frontend tests in Docker" below.

### 3-file Compose model (dev vs prod)

- **`docker-compose.yml`** — **prod-safe** base: backend + backing services, no
  code bind-mounts, no xdebug, no MinIO, no debug ports.
- **`docker-compose.override.yml`** — **dev**, auto-loads with `docker compose up`
  (`make up`). This is where the dev-only services live (dev caddy, dashboard, signer,
  minio/minio-init, **mailpit**), the code bind-mounts, xdebug and the published
  ports. List them in the file itself, which is where they won't go stale.

  ⚑ **Mailpit is the dev SMTP sink, and until 2026-08-26 this document only named it as a
  dependency of the worktree lane** — meaning an agent wanting to check a notification email had
  nowhere to look. `MAILER_DSN` points there in dev; in prod **there's no Mailpit** and that
  variable is a `:?` that has to carry a real transport.
- **`docker-compose.prod.yml`** — **prod**, explicit (`-f docker-compose.yml -f
  docker-compose.prod.yml`, does not load the override). Own images from GHCR
  (`image:` + `pull_policy: always`), `APP_ENV=prod`, object storage on AWS/Linode
  (S3_* from `.env.prod`), `restart: always`, worker active.

Services in prod (`docker-compose.prod.yml`): `caddy`, `php-fpm`, `worker`, `relay`,
`signer`, `postgresql`, `rabbitmq`, `redis`, `eu-dss`. **There's NO `dashboard`
container nor MinIO** (object storage is external S3). Release flow:
`make build-prod` (local build with buildx named contexts) -> `make push-prod` (GHCR)
-> on the host: `make deploy-prod`. Environment template: `.env.prod.example`.

**What gets built here and what doesn't.** `make build-prod` = `build-backend` +
`build-rabbitmq-prod` + `build-eu-dss-prod`: **three** own images. Everything else isn't
built in this repo — `caddy` is the official `caddy:2-alpine` image (it serves
`docker/caddy/Caddyfile`), and **the signer is consumed as an image already published by its
own repo's CI**, pinned with `SIGNER_TAG`, which is fail-closed (`:?`) so that
an incomplete `.env.prod` fails to render instead of starting up something unexpected.

**Independent tags**: `BACKEND_TAG` (php-fpm + worker + relay) and `SIGNER_TAG`,
both set in `.env.prod`. That way you can deploy backend only
(`deploy-backend`) or signer only (`deploy-signer`) without touching the other. `rabbitmq` and
`eu-dss` are pinned (`4.0` / `6.4`).

⚠ **`BACKEND_TAG` governs THREE images but `deploy-backend` redeploys TWO: the `relay` is left
on the old one.** The two sentences above are each true on their own and together are a trap — the target
runs `pull php-fpm worker` + `up -d php-fpm worker`, and its name says so ("backend ONLY (php-fpm +
worker)"), but whoever reads "BACKEND_TAG = php-fpm + worker + relay" will assume bumping the tag and
running `deploy-backend` moves all three. **If the release changes the schema, use `deploy-prod`**: a
relay running old code against a migrated schema doesn't fail loudly — it drains the event log and publishes
incorrectly. (Noted on 2026-08-26 while preparing the deployment of 28 migrations; the mismatch had been
there since the target existed.)

## Published ports (host → container)

| Service | Host | Container | Notes |
|----------|------|------------|-------|
| Caddy (backend API) | `http://localhost:8000` | `80` | Entry point to the Symfony API (`/api`) |
| Dashboard (Nuxt dev) | `http://localhost:3000` | `3000` | `pnpm install` takes a while on 1st startup — use `make frontends-wait` |
| Signer (Nuxt dev) | `http://localhost:3001` | `3001` | See above |
| PostgreSQL (dev) | `localhost:5432` | `5432` | `f5sign` / `f5sign` |
| PostgreSQL (test) | `127.0.0.1:5433` | `5432` | `f5sign` / `f5sign_test_pw`, tmpfs, profile `test` |
| RabbitMQ AMQP | `localhost:5672` | `5672` | `f5sign` / `f5sign` (declared in `definitions.json`) |
| RabbitMQ Management | `http://localhost:15672` | `15672` | Web UI, same credentials |
| RabbitMQ Prometheus | `localhost:15692` | `15692` | Metrics |
| Redis | _(internal)_ | `6379` | NOT published to host (clashed with other redis instances on the host); use `make redis-cli`. No password (DBs: cache=0, locks=1, idempotency=2, rate-limiter=3) |
| MinIO API (S3) | `127.0.0.1:9100` | `9000` | `minioadmin` / `minioadmin` |
| MinIO Console | `http://127.0.0.1:9101` | `9001` | Web UI |
| EU DSS | `127.0.0.1:8080` | `8080` | Exposed only in dev (override); healthy != TLs loaded |
| Mailpit (UI + SMTP sink) | `http://127.0.0.1:8025` | `8025` | **Where emails land in dev.** No credentials |

Shortcuts: `make psql`, `make redis-cli`, `make rabbit-console`, `make minio-console`, `make mc cmd="ls local/"`, `make agent-smoke`.

## Frontend tests in Docker

**Hard rule: tests (backend and frontend) ALWAYS run inside the Docker stack, NEVER locally.** The goal is to avoid polluting the dev/agent machine with dependencies (`node_modules`, Playwright browsers, pnpm stores). All of that lives in isolated Docker volumes.

Prerequisite: the stack up (`make up`) — the test targets use `--no-deps` and do NOT recreate services; they assume the stack is already running.

| Target | What it does | Where it runs |
|--------|----------|-------------|
| `make test-signer` | lint + typecheck + unit (Vitest) | `signer` container (Alpine) |
| `make test-signer-unit` | unit only (Vitest) | `signer` container |
| `make test-signer-e2e` | E2E Playwright (4 profiles) | dedicated `signer-e2e` container |
| `make test-signer-e2e-mobile` | E2E smoke (mobile-iphone-se) | dedicated `signer-e2e` container |

**Why a separate E2E container (`signer-e2e`)**: the `signer` container is Alpine (`node:24-alpine`) and **Playwright doesn't support Alpine**. E2E tests run on the official `mcr.microsoft.com/playwright` image (glibc + preloaded browsers), defined in `docker-compose.test.yml` (profile `test`). It points at the `signer` service's dev server over the internal network (`PLAYWRIGHT_BASE_URL=http://signer:3001`); that's why `signer` has to be up.

**Host isolation**: both the dev services (`signer`/`dashboard`) and `signer-e2e` keep `node_modules`, `.nuxt`, the pnpm store and the Playwright artifacts in **named volumes**. The repo's bind-mount is effectively read-only; the only things that show up in the host repo are empty mount-point directories (`.nuxt`, `tests/e2e/.playwright`), gitignored.

> The **dashboard** doesn't have a test suite yet; once it does, replicate these targets/services (`test-dashboard`, `dashboard-e2e`).

## Ephemeral per-worktree validation (for parallel agents)

**Audience: AUTOMATED use by agents.** Meant for running several `/task-runner` instances at once, one
per `git worktree`. The normal test targets (`make test`, `make test-signer*`) validate the **main
tree** (fixed host ports, shared `signer`/`postgres-test` services) → two worktrees would
collide and a secondary worktree isn't even bind-mounted. To validate a worktree, use the
`wt-*` targets, which spin up an **ephemeral, isolated lane on the fly** and clean it up when done.

| Target | What it does |
|--------|----------|
| `make wt-signer src=<path>` | Signer lane: 1 Playwright container that self-hosts its dev server; lint+typecheck+unit, **no E2E**. Reuses and keeps a lane whose state is already there; with none, ephemeral as before |
| `make wt-signer-up src=<path>` | Brings up a signer lane and KEEPS it: `pnpm install` + `nuxt prepare`, no gates |
| `make wt-signer-down src=<path>` | Tears down a worktree's signer lane and its volumes |
| `make wt-signer-e2e src=<path> [args=…]` | The same + Playwright E2E (~15 min). **Manual only**, at the user's explicit request — never from a task or a gate. |
| `make wt-backend src=<path>` | Backend lane: `postgres-test` (tmpfs) + ephemeral php; `composer install` + migrate (admin) + `composer test` (real RLS). Reuses and keeps a lane that's already up; with none up, ephemeral as before |
| `make wt-backend-up src=<path>` | Brings up a backend lane and KEEPS it: install + migrate, no gates |
| `make wt-backend-test src=<path> [only=<regex>] [changed=1] [fast=1] [args="..."]` | PHPUnit only, on the kept lane |
| `make wt-backend-sf src=<path> cmd="<console command>" [env=test]` | Symfony console over the **worktree's** code (default `env=dev`). `make sf` runs in the shared `php-fpm`, which mounts the main checkout, so from a worktree its `debug:*` output describes another branch's wiring. Reuses a kept lane; otherwise ephemeral. `admin=1` runs it as the lane's **superuser** (the DSN the lane migrates with), to exercise a migration's `down()`/`up()` from a worktree (`cmd="doctrine:migrations:execute --down '<Version>'"`, then `migrate`). ⛔ It bypasses RLS: migration operations only, never tests — it is reachable from `wt-backend-sf` alone, never from `wt-backend-test` or the test gate. A console run never migrates first, so a `--down` stays down until you `migrate` |
| `make wt-backend-down src=<path>` | Tears down a worktree's backend lane and its volumes |
| `make wt-ls` | Lists active lanes (`wt-*` compose projects) |
| `make wt-down name=<lane>` | Tears down a lane and its volumes, and fails if any container of it survives (until 2026-09-23 a backend lane was never actually removed: compose refused without `BACKEND_SRC`, silently) |
| `make wt-gc` | Removes every `wt-*` volume, network and `wt-*/backend` image Docker does not consider **in use** (preserves the `f5sign-*` CAS caches). ⚠ Not "of deleted worktrees", which is what its help said until 2026-09-23: a KEPT lane is safe only while its containers are alive — after a Docker or WSL restart they are stopped and this takes its `vendor/` and caches too |

`src` is the worktree's path; if omitted, the wrapper uses the git toplevel of the `cwd`.

⛔ **`scripts/wt-validate.sh` runs from a private copy of itself, and that is not cosmetic.** bash reads a
script **incrementally** from its file descriptor, so editing the file while a run is in flight — a commit,
a merge, a branch switch in the main checkout — makes the running shell pick up the new bytes at the offset
it had reached. Measured 2026-09-23: a commit to this script during a lane's Infection run made bash execute
comment text (`ls: cannot access 'WT_CONSOLE_ADMIN=1'`) and the run died with Error 2 **after** Infection had
printed passing results. The script now copies itself to `/tmp`, re-execs the copy and unlinks it at once
(the inode lives while bash holds it open), so nothing is left behind and an edit mid-run is harmless.
⚠ Anything that resolves paths from `BASH_SOURCE` inside that script is wrong for the same reason: the copy
lives in `/tmp`. `INFRA_DIR` comes from the original invocation path.

### Persistent lanes

Both lanes can now be kept alive across runs instead of torn down on exit — a TDD loop
pays the ~67s startup once instead of on every `wt-backend`. `make wt-backend-up` brings it up and keeps
it (`WT_KEEP=1 WT_GATES=none`: install + migrate, no gates). `make wt-backend-test` then runs PHPUnit
only against that kept lane (`WT_GATES=test`): `only=<regex>` → `WT_FILTER` → PHPUnit `--filter`;
`changed=1` → `WT_TESTS=changed`; `fast=1` → `WT_TIERS=fast`; `args="..."` → `WT_TEST_ARGS`, appended
raw. `make wt-backend-down` tears the lane down explicitly. Plain `make wt-backend` also reuses and
keeps a lane that's already up (a validation run never destroys someone's live lane, `WT_KEEP` or not);
with no lane up it behaves exactly as before — ephemeral, torn down on exit via the `trap`.

**The signer lane got the same treatment on 2026-09-23** (`make wt-signer-up` / `wt-signer-down`), and it
is the bigger win of the two: it was ephemeral *always*, so every validation threw `node_modules` and
`.nuxt` away and paid `pnpm install` + `nuxt prepare` before the first line of lint. What says a signer
lane exists is its state, not a container — it has no long-lived one — so the wrapper looks for its
`node_modules` volume. ⚠ Two consequences of it being volumes: `make wt-gc` will take a kept signer lane
whose containers are not running, and until 2026-09-23 `wt-down` never removed those volumes at all (the
signer overlay interpolates `SIGNER_SRC` with `:?`, compose refused, and the refusal went to `/dev/null`
— the same bug that hid the backend teardown; ~550 MB of orphan `node_modules` per lane).

What reusing a lane skips or changes, versus a cold `wt-backend`:

- **`composer install` is skipped** when `composer.json` + `composer.lock` are unchanged since the last
  install on that lane — a sha1 of both is stamped at `vendor/.wt-lock.sha1` inside the lane's `vendor/`
  volume and compared before reinstalling.
- ⛔ **A full run on a reused lane empties the database AND the object store**, together, before
  migrating; a selective run (`only=`, `changed=`, `fast=`) empties neither, because that is a TDD loop
  whose speed is the point. `WT_RESET=0` disables it. **Neither store is self-cleaning, and the database
  was the surprise**: `dama/doctrine-test-bundle` rolls back the tests that let it, but
  `#[SkipDatabaseRollback]` cases COMMIT — measured 2026-09-23, a kept lane holding 59 committed VOIDED
  envelopes, one of which every later promotion sweep picked up; deleting that one row turned two classes
  green with no code change. ⚠ Emptying only one of the two is **worse than emptying neither**: committed
  rows then point at objects that no longer exist. The real fix belongs in the backend (a test that opts
  out of the rollback cleaning up after itself); this is the lane refusing to hand anyone a red it caused.
  **How the object store is emptied matters.** Over S3 it cannot be done: deleting a *version* under a
  COMPLIANCE retention answers *"Object is WORM protected and cannot be overwritten"* (measured; deleting
  or overwriting the *key* does work — it writes another version, which is why "a second run rewrites the
  same key" was never the whole story). So the bytes go at the filesystem level from inside the container:
  `/data/*/` globs the bucket dirs and skips the hidden `.minio.sys`, where the buckets and their Object
  Lock config live — 0.23 s, after which the store still reports `ObjectLockEnabled` and accepts a PUT of
  the key that was protected a moment earlier. ⛔ Do NOT go back to dropping the volume and re-running
  `minio-init`: that target takes **43 s on an idle machine and 70-74 s on a busy one, even over an
  already-initialised store** (~40 aws-cli calls, each one a process start — `--debug`, which every call
  carries, is 0.43 s of the 1.38 s).
- **Migrations are compared, not re-run.** One `psql` reads `doctrine_migration_versions` and diffs it
  against the files in `migrations/`: versions missing there are migrated, and a version applied here that
  the branch no longer carries (a local set rewritten or condensed, repo-specific rule 2) recreates
  `postgres-test` (tmpfs: recreating it IS emptying it; `init-*.sql` reruns). It replaces two PHP
  containers — `doctrine:migrations:status` plus a `migrate` that on a reused lane was a no-op — with a
  0.2 s query. ⛔ It is deliberately NOT a stamp of `migrations/`: a stamp answers *"did the branch
  change?"*, which is not the question, and it outlives the tmpfs database it describes (a plain
  `docker restart` of `postgres-test` empties the schema and keeps any file inside the container), so it
  would report green over an empty database. A migration edited **keeping its version** is not detected —
  `migrate` did not re-run it either. If the query can't be trusted, it falls back to the old path.
- **Each step is a `docker compose exec`, not a container of its own.** On a kept lane the php service is
  left running and every gate, install check and console call execs into it. Measured 2026-09-23 on WSL:
  `run --rm` costs 1.21 s before the command starts, `exec` 0.13 s, and a run makes four to six of them.
  If the container can't be kept up the run says so and falls back to one container per step.
- **PHPStan keeps its result cache** in a per-lane volume at `/tmp/phpstan` (the backend sets no `tmpDir`,
  and a `run --rm` container's `/tmp` dies with it): a kept lane's phpstan gate re-analyses only what
  changed. Measured 2026-09-23: 140 s cold, 17 s warm, the lane's fixed ~14 s included.
- **Waits for the cluster to go idle before the `test` gate.** A reused lane can carry an open
  transaction from an earlier interrupted run (Ctrl+C, a timeout), and `pg_snapshot_xmin` is
  cluster-wide (BL-138, see below) — an open transaction would stall the relay and read as a defect in
  the branch under test rather than as leftover lane state.

**Test selection** (`wt-backend-test` only): `changed=1` selects a changed `*Test.php` file as-is, and
maps a changed class under `src/` or `phpstan/src/` to the tests that reference its fully-qualified
class name — measured against `WT_BASE` (default `develop`), including uncommitted and untracked files;
changes under `config/`, `migrations/` or `templates/` can't be mapped this way and print as a warning
instead of silently running nothing for them. `fast=1` keeps only `Unit/`, `Application/` and
`phpstan/tests` — no DB, no HTTP, no DSS. `WT_VERBOSE=1` lists the selected files instead of just the
count.

⚑ **Re-measured 2026-09-23 after the reuse work** (worktree `f5sign-backend-develop`, end to end): cold
`wt-backend-up` **77 s**, of which `minio-init` alone is **43 s** — more than half of a cold lane, and the
next thing worth attacking; a filtered `wt-backend-test` **4.4 s**, against ~22 s before; `fast=1` **11.9 s**
for 1 979 tests, of which 8.3 s is PHPUnit itself, so the fixed overhead per run went from ~14 s to ~3.5 s.
The figures below predate that work and are kept for the tier proportions, which still hold.

**Measured 2026-09-23** (backend main checkout, kept lane): first `wt-backend-up` ~67s; `only=` on one
class (`EnvelopeStatusTest`) ~8s; `fast=1` ~23s (2,594 tests); `changed=1 fast=1` over a 12-commit branch,
9-11s; the full suite on a kept lane, ~4-6 min, of which ~95% is `Integration/` + `Acceptance/`
(`Acceptance/` runs ≈0.5-1.7s per test — a fixed per-test HTTP setup cost, not individually slow tests).

The flock cap (`WT_CAP_BACKEND`, default 1) still limits concurrent **runs**, not lanes held open: an
idle kept lane holds no slot and costs the same ~280 MiB idle footprint measured for the ephemeral lane.
Intended use: `wt-backend-test` for the TDD loop (a direct `make` call, no subagent needed for it), a
`WT_GATES="lint arch phpstan test" WT_TIERS=fast make wt-backend src=…` before each commit (static gates
+ hermetic tiers), one full `wt-backend` (every tier) when the task is complete, `wt-backend-down` when it
closes. The backend skill `implement-backend` owns that cadence.

How it works (`scripts/wt-validate.sh` + `docker-compose.wt.{signer,backend}.yml`):

- **Isolation via `STACK_NS=wt-<lane>`** (`<lane>` = worktree basename). Re-namespaces network,
  volumes and names because they all interpolate `${STACK_NS}`. (Note: `-p`/`COMPOSE_PROJECT_NAME` alone
  is NOT enough — resources have a `name:` tied to `STACK_NS`.)
- **Lanes with NO host ports** → zero collision; everything goes over the lane's internal network. Agents
  don't do manual browsing, so nothing gets published.
- **Backend with dependency parity (6 containers)**: `backend/.env.test` resolves **five**
  hosts via DNS (`postgres-test`, `minio`, `rabbitmq`, `mailpit`, `eu-dss`) and the suite **doesn't have a
  single `markTestSkipped`** → whatever doesn't resolve **doesn't get skipped, it fails**. The lane brings up four of the five
  **per lane**, because those four hold state the tests mutate, and sharing them reproduces BL-138 on
  another substrate: postgres (xmin is **cluster**-scoped), minio (the 5 `S3_BUCKET_*` are fixed names → two
  lanes step on each other's keys), mailpit (single accumulating mailbox) and rabbitmq (shared queues). Redis
  stays out: cache=filesystem and lock=flock, the tests don't touch it. DB = `postgres-test` tmpfs per lane
  (reuses `docker/postgres/init-*.{sql,sh}`); migrates as `f5sign` (superuser), tests as `f5sign_app`
  (non-superuser, real RLS). `var/` and `vendor/` go to per-lane volumes (they don't pollute the worktree).
- **`eu-dss` is the only SHARED one**, and because of what it **is**, not what it costs: pure
  request/response, its only state is the Trusted Lists cache (read-only, identical for everyone). It's reached via
  `eu-dss-proxy` (socat), the **only** container in the lane on both networks: if the php container
  were on both, `minio`/`rabbitmq`/`mailpit` would resolve **ambiguously** and a lane would end up
  writing to the main stack's MinIO. `wt-validate.sh` **aborts with an explicit message** if the
  shared stack isn't up (`SHARED_NS`, default `f5sign`); `WT_REQUIRE_DSS=0` runs anyway, knowing
  full well the sealing tests will go red.
- **Explicit `mem_limit` and `cpus` on ALL services in the lane** (`WT_*_MEM` / `WT_*_CPUS`). Ceiling
  with the defaults: **~3.0 GiB and ~9.25 CPUs** per backend lane; actual measured idle usage, ~280 MiB. The
  cap matters most on minio: without it, it holds on to ~950 MiB of Go runtime slack (measured on the
  main stack) versus **84 MiB** under a 512m cap.
- **The five gates in the lane, selectable with `WT_GATES`** (default `lint arch phpstan test`;
  `infection` is **opt-in** because it takes orders of magnitude longer). Two things that weren't just wiring:
  **PHPStan** fails in the lane for the OPPOSITE reason it fails in the main tree — there, the container's
  dump is stale; here, it **doesn't exist**, because `var/` is a per-lane volume that starts empty and
  `composer install` clears cache under `env=test`, not dev. The gate generates it and **checks it's there**
  before analyzing. **Infection** needs the memory limit in a mounted `.ini`
  (`docker/php/wt-infection.ini`), not a `php -d`: it relaunches phpunit as a child process and the flag doesn't
  get inherited. Its value is a starting point, not a measurement.
- **Separate steps, not a chained `sh -lc`**: install / migrations / each gate are separate `run`
  calls, so a failure says **which one** died. It also sets
  `COMPOSER_PROCESS_TIMEOUT` (`WT_COMPOSER_TIMEOUT`, default 1800): `composer test` is a Composer
  *script*, and Composer kills its scripts at **300s** by default — the backend doesn't set
  `config.process-timeout`, so without this the suite dies on the clock without anything actually failing.
- **Shared CAS caches** across lanes (external volumes `f5sign-pnpm-store`, `f5sign-composer-cache`)
  → fast installs; `wt-down`/`wt-gc`/teardown NEVER delete them.
- **Concurrency cap** (flock): signer=2, backend=1 (`WT_CAP_SIGNER`/`WT_CAP_BACKEND`). **Don't push it
  on WSL** (OOM risk; it already froze the machine with 2 backend lanes). `mem_limit` is there as a backstop.
- **Automatic teardown** via `trap` (`down -v --remove-orphans`). `make wt-gc` is the safety net.

⛔ **Don't cobble together an ad-hoc `docker run` instead of the lane.** It's the alternative people
improvise when the lane feels like overkill, and it costs hours for three reasons already measured (backend
session, 2026-08-18), all three invisible while they're happening:

- **It locks up on `var/cache`.** A hand-rolled `docker run` mounts `var/` from the working tree, so
  **two concurrent runs end up waiting on the lock**: 40+ minutes with not a single line of
  output, and it reads as *"the tests are slow"*. The lane doesn't suffer from this because `var/` is the
  `wt-backend-var` volume, private to each lane. If you still need the `docker run`, add
  `--tmpfs /var/www/html/var/cache` to it.
- **A `timeout` on the HOST wrapping `docker run` doesn't kill the container**, only the client: the container
  stays alive holding locks, and zombies pile up (nine, in the measured case). The `timeout` has
  to go INSIDE: `sh -c "timeout 420 php ..."`. `wt-validate.sh` doesn't have this problem — its `trap`
  runs `down -v` on TERM too, verified by cutting a run short with `timeout`.
- **Cleaning them up afterward is worse than the problem.** `docker ps --filter ancestor=f5sign/backend:dev`
  also matches **the shared stack's `php-fpm`**, which runs that same image: an `xargs
  docker kill` over that filter takes down everyone's stack (happened, ~40s).

And the definitive argument, measured on the same tree and the same commit: ad-hoc container with an isolated
DB but a **shared cluster** -> 1681 tests, **5 failures** (all from the relay); `make wt-backend`
with its **own cluster** -> 1681 tests, **OK**. Isolating the database isn't enough; you have to isolate the cluster
(BL-138). It's the counterfactual that the lane's green runs, by themselves, don't demonstrate.

To integrate this with `/task-runner`: when an agent validates a worktree, instead of `make test-signer`
use `make wt-signer src=<worktree>` (same for backend). The shared stack for the PAdES tests **already
exists**: it's the dev stack itself (`make up` + `make dss-wait-tl`), from which the lane only consumes
`eu-dss` via proxy — see the two bullets above.

## Workers (Symfony Messenger)

The `worker` service consumes the `async_events` transport (cross-BC domain events, drained
by the `relay` — ADR-0031). It's **under the `workers` profile and does NOT start with `make up`** by default;
in prod, `docker-compose.prod.yml` enables it with `profiles: !reset []`.

**Reason (updated):** the default-off is **no longer** a workaround. The transport exists and the worker
starts up clean — it's a deliberate choice not to have the async pipeline running in dev unless it's
requested. *(This paragraph used to say the worker "crash-loops" because the backend hadn't
defined the `async` transport (task T03.1.2); the backend defined it as `async_events` and that reason
became obsolete.)*

⛔ **The operational trap is still alive, and it's the important one:** with the worker down, any
async `MessageBusInterface::dispatch()` gets **queued but not consumed**, and the dev or agent
might think the message was lost. Worse: an event whose routing key doesn't match any binding
falls through to the alternate exchange and lands in `queue.events.unroutable`, which **nobody reads
outside `when@test`** — it fails silently with the whole stack green. Check
`make worker-status` (pending messages per queue) **before** concluding something wasn't emitted.

Lifecycle:

| Action | Command |
|--------|---------|
| Start the async pipeline (worker + relay) | `make worker-up` |
| Stop worker | `make worker-down` |
| Restart after handler changes | `make worker-restart` |
| Real-time logs | `make worker-logs` |
| Status + pending queues | `make worker-status` |

## RabbitMQ — how the topology gets applied (and how it doesn't)

It's declared by `docker/rabbitmq/definitions.json`, which is the source of truth: the backend runs with
`auto_setup: false` and declares nothing. It reaches the container via **bind-mount**, and from that come the two
traps, both silent:

1. ⛔ **An `up -d` does NOT reload `definitions.json`.** Its content isn't part of the container's
   configuration hash, so `make deploy-prod` doesn't notice it changed. You need
   `make reload-rabbitmq`, which also passes it **over STDIN from the host**: a SINGLE-file bind-mount
   is tied to the inode, and git replaces files via rename, so after a `git pull` the running container
   keeps seeing the OLD file — forever. Without this, a new queue doesn't exist and the worker dies in
   a loop with `NOT_FOUND - no queue '...' in vhost '/'`.
2. ⛔ **A queue's arguments are IMMUTABLE, and the import doesn't fail: it keeps the old ones and
   reports success.** Redeclaring an existing queue with a different `x-dead-letter-exchange` changes nothing and doesn't
   warn you. That's why `reload-rabbitmq` doesn't stop at the import: it verifies with
   `docker/scripts/check-event-dlx.sh` and goes red if the redirect isn't there. Fixing it requires **deleting and
   recreating** the queues — `make rabbit-check-dlx-prod` to check, `make rabbit-recreate-event-queues-prod`
   to fix it (requires depth 0 and zero consumers; `FORCE=1` accepts the loss).

⚠ Why it matters: without a redirect, an undecipherable message gets rejected with nowhere to go, and rejecting
with no redirect is **discarding**. With the whole stack green.

## EU DSS (Trusted Lists)

`eu-dss` can be **"healthy" without being usable**. Compose's healthcheck validates that Tomcat responds (endpoint `/server-signing/keys`, ~20-30s after startup), but validating eIDAS signatures also requires having loaded:

- **LOTL** (List of Trusted Lists): master XML at `https://ec.europa.eu/tools/lotl/eu-lotl.xml`.
- **Trusted Lists** from the member states (~27 XMLs).

The first time (cold cache) it takes an extra 30-90s after "healthy". On later startups it comes from `dss-tl-cache` (persistent volume) in seconds.

Commands:

| Action | Command |
|--------|---------|
| Basic health (Tomcat) | `make dss-health` |
| Wait for TLs to load (default timeout 180s) | `make dss-wait-tl` |
| With a custom timeout | `make dss-wait-tl t=300` |
| **WHICH identity is signing** | **`make seal-check-prod`** — the third form of "healthy without serving", see below |

PAdES B-LT signing tests and eIDAS validation **must** depend on `dss-wait-tl`. `make smoke` shows both states separately.

### The seal: the trap the healthcheck doesn't show

⛔ **Healthy and with the TLs loaded, `eu-dss` can still be signing with an identity that isn't yours.** The `dss-demonstrations` webapp ships a DEMO keystore **inside the WAR**, and when it can't find the configured one it doesn't fail: it serves its own. The PDFs come out signed, the healthcheck green, and the structure tests green too — because the cryptography is real; what isn't yours is the certificate.

⚑ **Added on 2026-09-01, the day it was measured.** This document described two ways `eu-dss` could be "healthy without being usable" (Tomcat up, TLs not loaded) and not the third one, which is the only one with legal consequences. State that day: dev and preprod had been sealing since the beginning with `CN=self-signed, O=European Commission, OU=PKI-TEST`, serial 01 — whose **private key is published** in the `dss-demonstrations` repo along with its password. Anyone could produce an equivalent seal. It's already wired up, and **as of 2026-09-03 it's in `f5sign-infra`'s `master`** (merge `fc660f6`) — until today this line said *"branch `fix/dss-seal-keystore-wiring`"*, which was true on 09-01 and no longer is: that branch was **local only, never pushed**, and today it was merged and deleted. But the mechanism is still alive and needs to be understood:

- DSS loads the keystore with `ClassPathResource`, meaning **via classpath, not the filesystem**: a `.p12` in a volume is invisible unless its directory is in Tomcat's `common.loader`. That's why the Dockerfile puts `/keystore` there.
- The properties are `dss.server.signing.keystore.{type,filename,password}`, and `filename` is **relative to the classpath**, not an absolute path. The ones starting with `dss.keystore.` don't exist: they're silently ignored.
- ⛔ **Don't assume the seal is good because a sealing test is green.** A test that asserts structure (there's a `ByteRange`, the PDF grows) passes the same way with a demo identity. The only thing that tells them apart is checking subject/issuer: `make seal-check-prod`, or by hand `GET /services/rest/server-signing/key/{alias}`.
- In dev the seal is deliberately self-signed (`CN=F5Sign Dev Seal`) and validation returns `INDETERMINATE`: that's what's stated in the backend's ADR-0023 and isn't a failure. What got fixed wasn't that, but whose key it was.

**Moving a machine from the demo keystore to your own seal is NOT a normal `deploy-prod`** — the host material goes before the image (if the password file is missing NOTHING starts, not just `eu-dss`) and the first deployment blocks itself with its own gate. The procedure, with the escape hatch you need exactly once, is in `README.md` § *Despliegue en preprod / produccion* → *Migracion del sello*; don't duplicate it here.

## Conventions

- **Pinned versions** in `docker-compose.yml`. No `latest` on images, no exceptions since 2026-09-17 (until that day `minio/mc` was one, as an ephemeral init).
- **Healthchecks** mandatory on services other services depend on (PostgreSQL, RabbitMQ, EU DSS).
- **Single network** `f5sign-net` (bridge). Services communicate by internal DNS name.
- **Named volumes** for persistent data **in dev**. Declared by the `volumes:` block of each
  compose file (base, override and prod each declare their own): list them there, not here.
  ⛔ **In PROD, Postgres data is NOT a named volume: it's a host bind mount**
  (`PGDATA_HOST_DIR`, default `/srv/f5sign/pgdata`), and that's exactly the property it bought —
  Docker doesn't manage the path, so neither `docker compose down -v`, nor `docker volume prune`, nor
  `docker system prune --volumes` can take the DB out by accident; only an explicit `rm` can.
  ⚑ **Corrected 2026-08-26**: this line said "Named volumes for persistent data
  (`pg-data`, ...)" without distinguishing dev from prod, meaning it stated the opposite of the safety
  property `09ec6e2` introduced — and stated it right where someone would look to check whether it's safe to run
  a `prune`. ⚠ Migrating a prod predating that commit isn't automatic: `make deploy-prod` runs
  `preflight-prod` beforehand, which goes red if the bind mount is empty and the old volume still exists, and
  prints the copy recipe.
- **External ports documented** in the README or directly in compose comments (full map in `../f5sign-docs/Planning/F0-Infraestructura/EP01-Docker-y-Entorno/S01.1-Docker-Compose-para-Desarrollo/README.md`).
- **Environment variables**: `.env` is never committed; `.env.example` is, with values valid for local development.
- **Deployment modes**: `DEPLOYMENT_MODE=saas|dedicated` controls which bundles and extra services get activated. Details in `../f5sign-docs/Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md`.
- **Commits**: convention in the workspace root `CLAUDE.md` § *Commits*.

## Where the relevant specs live

- **Deployment modes**: `../f5sign-docs/Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md`.
- **Infrastructure and compliance**: `../f5sign-docs/Arquitectura/Pilares/7. Infraestructura y Compliance.md`.
- **EU DSS**: `../f5sign-docs/Arquitectura/EU DSS - Guía de Integración.md`.
- **Development context**: `../f5sign-docs/Implementación/Contexto de Desarrollo MVP.md`.
- **Planning per task**: `../f5sign-docs/Planning/F*/EP*/S*/T*.md`.

`f5sign-docs` is read-only from here. The only writes are to `Planning/` to close out `Seguimiento` (see AGENT-RUNBOOK).

## Repo-specific rules

1. **Pre-flight for the sibling repos**: before `docker compose up`, the three repos (`f5sign-backend`, `f5sign-dashboard`, `f5sign-signer`) must exist alongside this one. Otherwise, the bind mounts mount empty directories and the containers fail to start.
2. **Don't commit `.env`**. Only `.env.example`.
3. **Don't hardcode credentials** in `docker-compose.yml`; always via `${VAR}` from `.env`.
4. **Prod vs Dev**: the base `docker-compose.yml` is **prod-safe** (no bind-mounts or debug ports). The "dev shaping" lives in `docker-compose.override.yml` (auto-loads on `make up`); the production overrides in `docker-compose.prod.yml` (explicit: `-f docker-compose.yml -f docker-compose.prod.yml`, does NOT load the override). See "3-file Compose model" above.
5. **Don't modify DB migrations from here**. Schemas are `f5sign-backend`'s responsibility (`doctrine:migrations:*`).
6. **Logs and health**: all services must expose health endpoints or commands; the compose healthchecks depend on it.
7. **Custom images**: the `Dockerfile`s in `docker/` are the source for INFRA's own images (rabbitmq, eu-dss). No ad-hoc builds outside compose. **Exception — the PHP image isn't defined here**: dev and prod both come from the same `f5sign-backend/Dockerfile` (`target: dev` for the local container, the default target for the production one published by its CI). There used to be a second Dockerfile in `docker/php/`, with the same base and the same extensions, that had to be synced by hand; it was removed so the PHP version and extension set can't diverge between dev and prod. `docker/php/` now only holds configuration (`php.ini`, `xdebug.ini`), which gets bind-mounted.
8. **Tests ALWAYS in Docker, NEVER locally**: neither backend nor frontend gets tested/linted/built on the host machine. Use the `make test*` targets (see "Frontend tests in Docker"). Don't run `pnpm`/`npm`/`composer` install or tests directly on the host: it pollutes the machine and diverges from the stack's reproducible environment.
