# f5sign-backend — Operational guide for Claude Code

Symfony skeleton evolved into the **F5Sign backend** that exercises the locked tech-design commitments (platform-foundations, the domain-kernel, and the per-BC tech-docs). <!-- OFFREPO: the *why*-history lives in the design repo `../f5sign-doc/Arquitectura/DDD/tech/`; not reachable under agent-only backend access. The in-repo *what* is the kernel source docblocks + `docs/`. --> Per the lock-via-exercise paradigm, this codebase + its property-tests + scenario tests are the substrate that converts designed commitments into locked ones.

⚑ **Before writing code, read [Authoring rules](#authoring-rules--written-from-defects-this-repo-shipped) below.** Every rule there exists because the failure under it happened here, on a branch whose `make qa` was green. The gates cannot see any of them.

## Current state

- `src/F5Sign/` holds the populated kernel + foundation + 4 populated BC trees (Envelope, Session, SignatureExecution, Notification); Evidence & Audit + Legal exist only as deptrac layers (no `src/` yet). Enumerate rather than trust this list: `ls src/F5Sign/`.
  - `F5Sign/Kernel/` — categories (`Command`, `Query`, `Event`, `DomainEvent`, `AuditableEvent`, `ValueObject`, `Entity`, `AggregateRoot`, `EntityId`, `Reactor`), capabilities (`Subject`, `Equatable`, `Issued`, `Issuer`), `Repository`, `Time` (the `Clock` port; its test doubles live in `tests/F5Sign/Kernel/Testing/Time/`), `Context`.
  - `F5Sign/Foundation/` — `Bus` (Messenger adapters: `MessengerCommandHandler`, `MessengerEventSubscriber`), `EventLog` (the `platform.event_log` store + watermark relay, ADR-0031), `Actor` (issuer / actor-kind carrier), `Serialization` (event-type registry + wire codec), `Persistence`, `Identity` (UUID/string IDs), `Http` (retryable client), `Storage` (object store), `Tenancy` (tenant context), `Time` (system clock), `ValueObject` (`GenericValidationException`, `Uri`), `Billing` (metering port), `Crypto` (field-cipher primitive, ADR-0033), `Logging` (Monolog request-context processor, ADR-0009), `Templating` (content-addressed, insert-only template archive + engine, ADR-0038). Enumerate rather than trust this list: `ls src/F5Sign/Foundation/`.
  - `F5Sign/Envelope/` — populated BC (Domain + Application + Contract + Infrastructure + UI) per the vertical slice.
  - `F5Sign/SignatureExecution/` — populated BC (Domain + Application + Contract + Infrastructure): DSS sealing, sequential/incremental PAdES, visible marks.
  - `F5Sign/Session/` — populated BC (Domain + Application + Contract + Infrastructure + UI): the recipient signing ceremony (ADR-0028, amended by [ADR-0049](docs/adr/ADR-0049-two-gate-signer-authentication.md)/[ADR-0050](docs/adr/ADR-0050-session-credential-jwt-and-refresh.md)). ⚑ **The emailed signing token no longer admits a recipient to anything but the door.** It buys `POST /api/v1/signing/session` (open); the read-model, the document bytes and the commit all require the **session credential** (`Authn::SESSION_CREDENTIAL` — a 15-min JWT), and `POST /api/v1/signing/session/renew` is its own kind (`Authn::SESSION_RENEWAL`). Prose written before this — in docs, docblocks or `#[OA\*]` strings — that says the signing token authenticates the ceremony is describing the *previous* partition. Re-derive from the route file rather than from memory: `config/routes/api/signing.php` carries each route's `_authn`.
  - `F5Sign/Notification/` — populated BC (Domain + Application + Contract + Infrastructure): the notification occasion + per-channel `Delivery` fan-out. A **category-(c) supporting BC** ([ADR-0037](docs/adr/ADR-0037-notification-supporting-bc.md)) — no layer may depend on it, which is why its templating substrate lives in `Foundation/Templating` ([ADR-0038](docs/adr/ADR-0038-template-archive.md)), not in the BC.
  - Evidence & Audit and Legal — not yet populated (deptrac layers pre-scaffolded, deliberately: empty layers match no files, so the visibility rules are already in force when the first class lands). Evidence & Audit's PII-classification + cipher substrate *did* land ([ADR-0032](docs/adr/ADR-0032-evidence-pii-custody.md)/[ADR-0033](docs/adr/ADR-0033-pii-field-encryption-at-rest.md)); the projector itself ([TASK-014](docs/tasks/TASK-014-evidence-audit-projector.md)) is **not started**.
- `App\` namespace remains for `App\Kernel` (Symfony app kernel) + `App\PHPStan\Rules\` (custom architecture rules at `phpstan/src/Rules/`; sibling `phpstan/tests/Rules/` for rule tests — reference test landed at `EntityFinalConcreteRuleTest.php`).
- PHP version: 8.5; strict types throughout.

## Architecture — kernel categories (read before domain work)

The architectural contracts are the **kernel categories** in `src/F5Sign/Kernel/`. Each category's **canonical definition is its own source docblock** — a short description, the invariants it must uphold, and the rationale. They're self-contained: you do **not** need the design repo to understand or honor them.

- **Enumerate the ontology**, one command: `grep -rnE "Kernel (sub-)?category" src/F5Sign/Kernel/`. Each hit is a category (or sub-category) interface/abstract — open it and read the docblock.
- **Before implementing or modifying** a type in a kernel category, read that category's source docblock — it states the invariants your code must satisfy.
- **Follow `@see`** to walk the concept graph; related contracts link via `@see \Fully\Qualified\Name`.
- **When a PHPStan rule fires**, its message names the in-repo home that explains *why* — a class to open, `docs/adr/ADR-NNNN`, or `phpstan/README.md`.

**`@see` convention:** every `@see` that references a class is written **fully-qualified** (`@see \F5Sign\Kernel\…`), even when the symbol is imported — so the concept graph is greppable by canonical name regardless of local imports/aliases. `php-cs-fixer` is configured to preserve this (it shortens other phpdoc type tags but leaves `@see` alone; see `.php-cs-fixer.dist.php`).

## Stack

- Symfony 7.4
- PHP 8.5 (strict types)
- Doctrine DBAL 4 + DoctrineMigrationsBundle — **the ORM was retired for DBAL-only writes (ADR-0018).** `doctrine/orm` is not a dependency and there are no `*.orm.xml` files anywhere; see rule 2 under Authoring rules before writing any rationale that names ORM behaviour.
- Symfony Messenger + RabbitMQ for async (§2.5–§2.8)
- Symfony Lock (`LOCK_DSN`; `flock` in dev/test, Redis in the prod compose).
- ⚠ **Installed ≠ configured, and this line has now been wrong in *both* directions — check `composer.json` and `config/packages/` separately before restating it.** Measured 2026-08-18:
  - **RateLimiter — installed, zero limiters configured.** `symfony/rate-limiter` is a direct `require`. Nothing in `config/packages/` defines a limiter; `rg -n 'rate_limiter' config/` hits **only `config/reference.php`**, which is a *generated dump of Symfony's own config reference*, not configuration. So no endpoint is rate-limited today — but the package being absent is no longer the reason, and "add the package" is no longer the work.
  - **Redis — the client is installed, the cache does not use it.** `ext-redis` is a hard `require` and `symfony/cache` a direct one; what is untouched is the *wiring* — `config/packages/cache.yaml`'s pools are commented out, so cache is still the **filesystem default**. Redis's live use is `LOCK_DSN` in the prod compose, above.
  - The text here previously read "no Redis client is installed" and "RateLimiter is not installed at all". Both were false when read, and the correction is the narrower claim: nothing is *wired*.
- `lcobucci/jwt` ^5 — direct `require` since ADR-0050, used **only** for the recipient session credential (`Foundation/Http/SessionCredentialCodec`). ⛔ Not a general JWT layer: `symfony/security-bundle` and `lexik/jwt-authentication-bundle` sit in `composer.json` but are registered in **neither** `config/bundles.php` nor anything else (see the Bundles table below), and admission runs on the route-declared `Authn` seam (ADR-0048), not on a firewall.
- PostgreSQL 16 (§2.3)
- PHPUnit 11.5 (with `dama/doctrine-test-bundle` for transactional isolation)
- PHPStan ≥ 2.1 level 9 + custom architecture rules
- Deptrac ≥ 4.6 (visibility contract; the core-five BC layer-sets plus Notification are declared in [`deptrac.yaml`](deptrac.yaml) — count them there rather than here)
- Twig 3 (`twig/twig` + `symfony/twig-bundle`, direct `require` since ADR-0052) — **layout composition for one channel's email markup only**; see the bundle note below before reaching for it anywhere else
- PHP-CS-Fixer
- Xdebug (mode=off by default; coverage / step-debug via env override)

## Bundles enabled

| Bundle | Envs |
|--------|------|
| FrameworkBundle | all |
| MonologBundle | all |
| DoctrineBundle | all |
| DoctrineMigrationsBundle | all |
| MakerBundle | dev |
| DAMADoctrineTestBundle | test |
| NelmioApiDocBundle | all |
| TwigBundle | all |

⛔ **TwigBundle is NOT a view layer here, and the scoping is the decision** ([ADR-0052](docs/adr/ADR-0052-twig-layout-composition.md)). It exists to compose the `EMAIL` channel's HTML chrome at authoring time: `config/packages/twig.yaml` points `default_path` at `templates/notification/` rather than the conventional `templates/`, sets `strict_variables: true`, and the line the ADR draws is **no HTTP route renders Twig** — unenforced today ([BL-136](docs/BACKLOG.md)), so it holds by nobody having done it rather than by a gate. ⚑ Twig **composes**; it never **interpolates**. The markup it emits still carries the `{{token}}` slots, and `NativeTemplateEngine` stays the sole implementation of `TemplateEngine::interpolate()` — the only thing that ever meets a recipient's value. Unifying the two engines is the plausible cleanup that would break ADR-0038 decision 9; ADR-0052 is the record that the split is deliberate.

Not enabled (out of scope): SecurityBundle, LexikJWTAuthenticationBundle, WebProfilerBundle, DebugBundle.

## Running tests + tooling — always via the infra Makefile

⛔ **FIRST: are you in a git worktree? Then every target in the table below validates SOMEONE ELSE'S CODE, and reports green for it.** `f5sign-infra`'s `docker-compose.override.yml` bind-mounts **`../f5sign-backend`** — the *main* checkout, hardcoded — into the container. A worktree is never mounted, so `make test`, `make phpstan`, `make lint` and `make composer cmd=…` all run against whatever branch the main checkout happens to be sitting on. Your edits are not in the container, and **nothing warns you**: the run succeeds, the counts look plausible, and the answer is about another branch.

- **Check before trusting any run:** `git rev-parse --git-dir` — a path containing `/worktrees/` means you are in one. `git worktree list` names the main checkout, which is the tree those targets actually validate.
- **From a worktree use `make wt-backend src=<path-to-your-worktree>`**, which mounts *your* tree. ⚠ **Rebuilt 2026-08-18 by the `f5sign-infra` session — this bullet used to read *"the lane is postgres-test + an ephemeral php only (no RabbitMQ, no MinIO — storage tests fail there, broker tests skip)"*, and every clause of that is now false.** The lane brings up **its own set of every stateful service the suite mutates** — today `postgres-test`, `minio` + `minio-init` (the five buckets, with Object Lock), `rabbitmq` and `mailpit`, plus its own `php-fpm-wt`. The property is *per-lane if a test can write to it*, so enumerate today's members from `f5sign-infra/docker-compose.wt.backend.yml` rather than from this sentence. **Storage and broker tests pass there now.** The lane also bind-mounts `docker/php/php.ini`, so it runs at **512M** — the [BL-135](docs/BACKLOG.md) 128M trap is the *ad-hoc container's*, not the lane's — and sets `COMPOSER_PROCESS_TIMEOUT=1800`, which retires the old *"dies at Composer's 300s process timeout"* observation. Every step is its own `docker compose run` — `composer install`, migrate as the superuser `f5sign`, then **one run per gate** as the app role `f5sign_app` — so a failure names the step that died. Two costs that are real: teardown is `down -v`, which takes the per-lane vendor volume with it, so **every run redoes `composer install`**; and `flock` caps the backend at **one lane at a time**. Measured 2026-08-18: the whole run (install + migrate + suite) is a few minutes, of which the suite itself is **1:46**.
- **`eu-dss` is the one shared service, and deliberately — by what it is, not by what it costs.** It is request/response with a read-only Trusted-Lists cache, so there is nothing for two lanes to corrupt. It is reached through a `socat` proxy that is the **only** container on both networks: if the PHP container joined both, `minio`/`rabbitmq`/`mailpit` would resolve **ambiguously** (Docker DNS unions the entries of every attached network) and a lane could write into the shared stack's MinIO. `f5sign-infra/scripts/wt-validate.sh` **preflights** that the shared `eu-dss` is up and aborts with the reason written out if it is not — because `rg -n 'markTestSkipped' tests/` returns **nothing**, so a host that does not resolve goes **red**, not skipped. Escape hatch `WT_REQUIRE_DSS=0` runs anyway, with those tests red on purpose.
- ⛔ **A separate *database* on the shared cluster is NOT isolation — and it is the workaround everyone reaches for.** `src/F5Sign/Foundation/EventLog/EventRelay.php` filters on `sys_transaction_id < pg_snapshot_xmin(pg_current_snapshot())`, and **`pg_snapshot_xmin` is cluster-wide**: one open transaction in *any* database of the cluster — including `postgres`, which holds none of our tables — stalls the relay, **and the relay reports success while draining nothing** ([BL-138](docs/BACKLOG.md), which proved the mechanism by controlled A/B/C). **The rule is one cluster per session, not one database per session**; anything sharing a cluster is exposed no matter how many databases it is split across. The lane is isolated because it brings up its **own** `postgres-test` container — a separate cluster. A hand-rolled `docker run` against the shared `postgres-test` is not, and creating a second database inside it does not help. ⚑ **Confirmed 2026-08-18**, same tree, same commit, zero edits, **n=1 per arm** — a confirmation consistent with BL-138's A/B/C, not an independent proof of the mechanism: the ad-hoc container against an isolated database `f5sign_test_wt` on the **shared** cluster gave `1681 tests, 7177 assertions, 5 failures`; `make -C ../f5sign-infra wt-backend src=$(pwd)` on its **own** cluster gave `1681 tests, 7210 assertions, OK`. Identical test count in both arms, so nothing was skipped or filtered — the delta is purely pass/fail. All five reds were relay / event-log (`EventLogBrokerRoundTripTest`, `EventRelayTest`, `ReplayEventLogEventCommandTest`), two of them carrying BL-138's documented signatures verbatim (`0 is identical to 2`, `-1 is identical to 1`).
- ⚑ **The lane runs the gates, not just the suite — corrected 2026-08-19.** Until then this bullet read *"the cost that did not change: the lane runs `composer test` only … `lint`, `arch`, `phpstan` and `infection` still have **no worktree-aware route** through it"*, and a session asserted that twice — in a task record and in a status row — from the prose, without opening the script. `f5sign-infra/scripts/wt-validate.sh` takes **`WT_GATES`**: the default is `lint arch phpstan test`, `infection` is a fifth (opt-in, because it costs minutes), and an unknown name **exits 2** printing the valid set — so the set is closed and greppable *there*, which is where to enumerate it rather than from this sentence. Measured 2026-08-19 from a worktree: the default four gave `lint 0 of 905` · `Deptrac Violations 0` · PHPStan `[OK] No errors` · `OK (1901 tests, 9447 assertions)`; `WT_GATES="infection"` gave `Covered Code MSI: 87%` / `MSI: 58%` in 4m39s. ⚠ Infection runs there because the lane's compose mounts `docker/php/wt-infection.ini` (1536M, layered over the 512M above) — **the mounted ini is precisely the mechanism the next bullet names**, so the retired text described the fix and still concluded it did not exist.
- **An ad-hoc container remains the quick way to re-check one file, because `lint`, `arch` and `phpstan` are *static* and need no network:** `docker run --rm -v $(pwd):/var/www/html -w /var/www/html f5sign/backend:dev sh -c 'php -d memory_limit=-1 "$(command -v composer)" arch'`. Anything touching the DB belongs in the lane — and these are why it is a re-check, not a substitute:
  - ⚠ **The image bakes no `php.ini`, so it starts at `memory_limit=128M`, and `-d` does not reach child processes** — Infection respawns its own `phpunit`, and **so do PHPStan's parallel workers**. Measured 2026-08-19: an ad-hoc `composer phpstan` reports *"Found 2 errors"*, both of them `Child process error: PHPStan process crashed because it reached configured PHP memory limit: 128M`, followed by *"Result is incomplete because of severe errors"* — **that output looks like a code failure and is not**. The flag that works is PHPStan's own: `php -d memory_limit=-1 vendor/bin/phpstan analyse --no-progress --memory-limit=1G`. A mounted ini is the general fix ([BL-135](docs/BACKLOG.md)); the 128M problem is gone **in the lane**, not everywhere.
  - ⚠ **Point one at a database and two things weaken it silently — on top of the cluster rule above.** `.env.test` declares **five** DSNs across five roles (`DATABASE_URL`, `RELAY_DATABASE_URL`, `IDENTITY_DATABASE_URL`, `PROVISIONING_DATABASE_URL`, `IDENTITY_ADMIN_DATABASE_URL`), so overriding only `DATABASE_URL` leaves identity / provisioning / relay traffic on the shared one — internally consistent, so it *passes*, while split across two databases. And `f5sign` is the **bootstrap superuser, which bypasses `FORCE ROW LEVEL SECURITY`** (`f5sign-infra/docker/postgres/init-app-role.sh`; [`docs/LOAD-BEARING.md`](docs/LOAD-BEARING.md) §1.7): migrating as it is right, running the suite as it makes every RLS test weaker than production *and* weaker than the lane, which connects as `f5sign_app` on purpose. Run phpunit as `f5sign_app`.
- ⚑ **Measured 2026-08-17 — this is what it looks like when it bites, and the failure is confident rather than silent.** A session working in the `f5sign-backend-develop` worktree ran `make composer cmd=test`, got `OK (16 tests)`, and concluded from the count that 8 test methods in the file it had just edited were never collected — reporting it as a defect that undermined a planned task's acceptance bar. Both claims were false: the container was running `f5sign-backend` on an unrelated branch, whose copy of that file genuinely has 6 test methods. That same session had already reported "PHPStan green" for edits PHPStan never saw.

**Tests, PHPStan, Deptrac, lint, and Symfony console all run inside the `php-fpm` container** brought up by [`f5sign-infra`](../f5sign-infra/). That container sits on the stack network, so it resolves **every service the stack declares** by name — `postgresql`, `postgres-test`, `rabbitmq`, `minio`, `mailpit` and `eu-dss` as of 2026-08-18; the host resolves none of them. Enumerate the current set from `f5sign-infra`'s `docker-compose.yml` + `docker-compose.override.yml`, not from this line. Running `vendor/bin/phpunit` or `vendor/bin/phpstan` directly from the host shell will:

- pass for purely-static checks (phpstan analyse) but bypass the canonical run path,
- **fail for any test that touches Postgres / RabbitMQ** (`could not translate host name "postgres-test"`),
- skip the `ensure-stack` precondition that catches "stack not up" cleanly.

Always invoke through the infra repo's Makefile:

| Action | Make target (run from `../f5sign-infra/`) |
|--------|---------------------------------------------|
| Full setup (build + up + install + migrate) | `make install` |
| Stack up / down | `make up` / `make down` |
| Tests (auto-ensures stack + test-db) | `make test` |
| Tests with HTML coverage | `make test-coverage` |
| Tests with text coverage | `make test-coverage-text` |
| Static analysis | `make phpstan` |
| Architecture (deptrac) | `make composer cmd=arch` (no dedicated target yet) |
| Lint | `make lint` |
| Format (apply) | `make format` |
| Full QA (lint + arch + phpstan + tests + infection) | `make qa` |
| Migrations | `make migrate` |
| New migration | `make migration` |
| Symfony console | `make sf cmd="<command>"` |
| Composer | `make composer cmd="<command>"` |
| Container shell (⚠ **interactive only** — see below) | `make shell` |
| Any composer script with no target of its own | `make composer cmd="<script>"` |
| Test DB lifecycle | `make test-db-up` / `test-db-setup` / `test-db-down` / `test-db-reset` |
| Worker (Messenger consumer) | `make worker-up` / `worker-down` / `worker-status` |

⚠ **`make shell` is an INTERACTIVE shell (`docker compose exec php-fpm sh`) and an agent cannot use it.** It needs a TTY, so in a non-interactive harness it is not a route to anything — and it was previously the only route this file offered for `composer arch`, which meant an agent following these instructions literally could not run deptrac. **Reach for `make composer cmd="<script>"` instead**: it is the same container, takes any composer script, and returns its exit code. `make sf cmd="<command>"` is the twin for Symfony console. Both verified non-interactive.

**Inside the container** the equivalents are `php bin/console …`, `vendor/bin/phpunit`, `vendor/bin/phpstan analyse`, `vendor/bin/deptrac analyse`, `vendor/bin/php-cs-fixer fix`, `composer <script>` — reachable through the two `cmd=` targets above without opening a shell. **Enumerate the composer scripts with `composer run-script --list`** rather than guessing or trusting a list written here — an enumeration in this file is a hand-maintained locator and rots on the next `composer.json` edit. There is no `test:unit` / `test:integration` / `test:e2e`; a single tier is selected with `vendor/bin/phpunit --testsuite <name>` or `--filter`. **The two sets are not one-to-one and neither contains the other** — several composer scripts have no make target (the table above already names one: `arch`) and the Makefile carries a great deal that composer does not. Check both — `composer run-script --list` and `make help` — rather than assuming a twin exists.

**Async worker** sits behind the `workers` profile and is off by default — dispatching to `async` enqueues but doesn't consume until `make worker-up` runs. `make worker-status` shows queue depth.

## Conventions (in force)

- PSR-12 + `declare(strict_types=1);` everywhere.
- Domain layer cannot import Doctrine, Symfony, or any framework — enforced by Deptrac (`deptrac.yaml`) plus the kernel-placement PHPStan rules.
- Tests are size-tiered as directories (ADR-0035): `Unit/` + `Application/` (both hermetic — no container/DB, arch-rule enforced) · `Integration/` (real DB, DAMA rollback) · `Acceptance/` (HTTP), mirroring `src/F5Sign/<BC>/` under `tests/F5Sign/<BC>/<tier>/`; per-BC doubles live in `<BC>/Testing/Fake/`, cross-BC flows beside the BC directories in `tests/F5Sign/Integration/` + `tests/F5Sign/Acceptance/`. The eIDAS assurance tier (A/B) is a `#[Group]`, orthogonal to the directory. See [`tests/README.md`](tests/README.md) — the conventions spec. Structural test strength is gated by Infection covered-MSI (`composer infection`, ADR-0035) — **mutation strength, not coverage %**; there is no line-coverage threshold in this repo.
- New tests must declare `#[CoversClass]` (or `#[CoversNothing]`) — `phpunit.dist.xml` has `requireCoverageMetadata="true"`. Use `#[UsesClass]` for collaborators, including every exception type the test asserts directly.
- Property-driven TDD: see [`tests/README.md`](tests/README.md) for the in-repo convention (layout, `P-§` docblock citation, how to find properties already locked). The full property catalogs are design-repo (`Arquitectura/DDD/tech/{kernel,envelope}-testing-assumptions.md`) and may be unavailable under agent-only access — `tests/README.md` is self-sufficient.
- The PHPStan baseline at [`phpstan-baseline.neon`](phpstan-baseline.neon) is the catalog of design-blocked findings — each entry maps to a tracked DI / F item. Do not extend without recording *why* in the entry comment; where reachable, categorize it against the design-repo `FINDINGS.md` / `DESIGN_INCONSISTENCIES.md` trackers. <!-- OFFREPO: those trackers live in `../f5sign-doc/`; not reachable under agent-only backend access. -->
- Deptrac currently has no equivalent baseline mechanism; violations should be enumerated as findings directly, not silently allowed.

## Authoring rules — written from defects this repo shipped

Each rule below exists because the failure under it happened here, on a branch that passed `make qa`
green. **No gate in this repo can see any of them** — not PHPStan, not Deptrac, not Infection. They are
ordered by how often they have actually fired. Triggers are stated first, so the rule is findable from
the situation you are in rather than from its name.

### 1. You are changing what a concept means, mid-branch

Renaming a concept, re-cutting its shape, replacing a mechanism, re-gating a rule, changing a default.
**This is the single largest defect class in this repo's review history** — one re-cut left stale prose
in eleven files, and the same generator has now fired on five separate branches.

- **The diff is not the search surface.** A file that still needs the edit shows an **empty diff**
  across your re-cut. An empty diff means *never revisited*, not *needed no revision*.
- **One sweep, every surface:** `rg -n '<retired term>' src tests migrations docs config CLAUDE.md`.
  ⚑ **This file is in the sweep** — it is the only surface that does not merely go stale but starts
  *instructing wrongly*, making the next agent rebuild what you removed. It declared "Doctrine ORM 3"
  for weeks after that left `composer.json`; the review of the retiring branch called it the
  highest-value finding on it. Then the surfaces
  that get forgotten, worst first: **migration docblocks** (nobody re-reads an applied migration except
  to reconstruct why the schema looks as it does — which is exactly when a confident wrong rationale
  does maximum damage); **`#[OA\*]` attribute strings** (emitted verbatim into the generated OpenAPI
  spec that the frontend team ratifies — they are not internal comments, and one of them told clients
  to send a value the endpoint does not accept); **`docs/adr/README.md` index rows**; **test class
  docblocks**.
- **Convert one file at a time, completely.** Working from a per-line worklist leaves files
  half-converted, and a single survivor reads as a deliberate distinction rather than as residue.
- **Keep historical uses.** "An earlier cut held them as one level" is *correct* as a record of what
  changed. Sweep claims about the present, not descriptions of the past.
- Check the file against **itself**: a docblock that contradicts its own `@phpstan-type` nineteen lines
  down has shipped here.
- **Grep the symbol whose behaviour changed, not only a term you retired.** A re-gate, a backed-out
  carrier or a changed default retires *no name*, so there is nothing to sweep for unless you sweep for
  the thing itself: `SubscriberConventionsRule` re-gated path→interface with `phpstan.dist.neon` still
  describing the path gate; `DefaultChannelSelector` LOG→EMAIL with `services.yaml` still calling it
  "the degenerate LOG-only selector".
- **Scope the sweep by grep, never by directory.** `b3ae6f7`, a commit whose whole purpose was
  repointing orphaned links, swept `docs/adr/*` and missed `docs/tasks/*`. Also forgotten: ADR *bodies*
  and *footers* (not just index rows), `config/*.yaml` comments, and `§N` refs inside `src/`.

### 2. You are writing — or copying — a docblock that says *X because Y*

- **Y rots independently of X, and Y is the half that reads as timeless.** Verify Y against the tree
  before you write it. Half of this repo's recorded prose defects are a true guarantee attached to a
  mechanism that no longer exists.
- **Copying a neighbour's docblock copies its claim.** The claim was true *there*. `AssignDocuments`
  inherited "the write already took an envelope-scoped lock" from a sibling; that path takes no lock.
- Mechanisms **already retired here** — never reintroduce one as a rationale: **Doctrine ORM
  reflection/hydration writes** (ADR-0018; `doctrine/orm` is not a dependency, no `*.orm.xml` exists),
  the **outbox** (ADR-0031), `AuditCommandInterface`.
- **Do not delete the clause.** The mechanism rotted; the *reason* attached to it usually did not.
  Replace only the named mechanism — the corrected in-tree wording to mirror is
  `\F5Sign\Envelope\Domain\ValueObject\Settings`. Deleting the reason leaves the shape unexplained and
  invites exactly the "tidy-up" [`docs/LOAD-BEARING.md`](docs/LOAD-BEARING.md) §2 forbids.

### 3. You are writing a new class modelled on an existing one

- `ls` the directory and read **every** sibling, not the first one that matches. **Where two siblings
  differ, the difference is either a bug in one or a decision — find out which before copying either.**
- Shipped here: a new download controller copied the sibling *without* the filename strip and
  reintroduced a 500 that the other sibling had already found, fixed, documented and locked with a test
  naming the exact failing input.

### 4. You added an Application handler, use case, controller, or a public method on a `Contract/` type

- **It gets a test at the tier its siblings use** ([`tests/README.md`](tests/README.md) §Layers). `ls`
  the sibling test directory: being the only `*UseCase.php` with no `*UseCaseTest.php` beside it is the
  signal, and it has been accurate every time.
- **A gate says nothing about a property its harness cannot reach — and sabotage will not save you
  there.** Flip `lockForUpdate` to `false` and the suite stays green: `Integration/` runs **one
  connection** under DAMA rollback, so locked and unlocked reads are indistinguishable to it.
  `DbalNotificationRepository`'s `FOR UPDATE` shipped with three escaped mutants at 98.9% coverage while
  the probe that *can* separate them — [`ProbesRowLocks`](tests/F5Sign/Support/ProbesRowLocks.php) —
  already sat in the repo.
- **Before citing a green run, name where the property lives and check the harness goes there.** A second
  connection; a second process; a transport that can redeliver (`async_events` is `in-memory://` in
  test); a path inside Infection's `source` (`src/F5Sign` only — so a custom PHPStan rule's own test is
  its *sole* guard); an identity surviving serialization (a fake returning the instance it stored proves
  nothing about `save()`). And Infection cannot see code with no callers: four new surfaces shipped here
  untested at 88% covered-MSI, one a security-shaped predicate with no callers of any kind.
- **A fixture whose variables always agree cannot fail.** If every fixture row grants `signs` and
  `visible` together, a projection filtering on the wrong one still passes. Build the case where they
  **disagree**; that is what makes the test discriminating rather than decorative.
- **Sabotage before you trust it.** Revert the guard, watch the test fail *for the right reason*, then
  restore. Three guards were sabotage-checked on the last review; one of them accidentally upgraded an
  open question to evidence.
- **A test double that reimplements production logic is safe only if the real artifact has its own unit
  test.** That is the precondition, and it is the whole rule — port stubs and recording spies are not
  covered by it, logic-duplicating doubles are.

### 5. You are writing a predicate that decides what is in scope — a runtime guard, a PHPStan rule, or the set a test iterates

- **Enumerate the whole set the predicate exempts** and check your rationale covers every member. Two
  illustrative examples is not the set.
- Shipped here: a send-time guard keyed on `Role::signs()` — SIGNER only — justified by one sentence
  about VIEWER and CC. It exempts five roles; three of them get a live, consent-recording ceremony, and
  one of those is a *blocking* APPROVER.
- **An enumeration is a predicate, and the set it exempts is "everything not yet listed."**
  `SchemaConformanceTest`'s hardcoded `BC_SCHEMAS = ['envelope','session']` let a whole new BC's tables
  pass all seven conformance properties in silence. **Prefer a predicate stating the property over one
  enumerating today's members**; where you must name a set, **census the universe, classify, and fail on
  the unclassified** — then drop a known member and check the test fails *naming* it.
- ⚑ **An exempted set that is empty today returns nothing and reads as an all-clear.** It is the
  opposite: nothing *can* go red, so green is the expected signal, not evidence — and the set is
  populated later by someone with no reason to know your predicate exists. Re-gating
  `SubscriberConventionsRule` to a marker interface exempts adapters missing the marker; all five live
  ones carry it, so nothing reddens until the sixth. Same for an **absence**: PHPStan L9 rejects a
  *missing* key but accepts an *extra* one, so a "PII-free" spot-check waves through a new PII field.
  Assert the **closed key set**.

### 6. Your migration writes rows the domain layer will later read

- **A backfilled row is indistinguishable from an authored one.** Enumerate the aggregate states it
  lands on — draft, in-flight, terminal, superseded — and state what the row means in **each**, on the
  **write** side as well as the read side. Reasoning only about what a recipient can now *see* is how
  the last review's one blocking finding got shipped.
- **On an append-only model with no revoke path, a wrong row is permanent and unrepairable through the
  API.** That backfill had no status predicate; every undeclared pair on a pre-existing draft became a
  permanent 409, leaving those envelopes unsendable *and* unrepairable.
- **Prefer a predicate that states the property over one enumerating today's statuses.**
  `sent_at IS NOT NULL` asks the real question ("could a recipient already have read this?");
  `status <> 'DRAFT'` silently re-opens the hole the day a new pre-send status is added.
- **Migrations connect as the bootstrap superuser, which bypasses RLS outright** — `FORCE ROW LEVEL
  SECURITY` does not apply to them, in any environment including production
  (`f5sign-infra/docker/postgres/init-app-role.sh`; [`docs/LOAD-BEARING.md`](docs/LOAD-BEARING.md) §1.7).
  So **never wrap a migration's data write in a `NO FORCE` window.** It is a no-op that reads as a
  guard — see the Never entry in §2, which also records why the obvious repair is wrong if that role is
  ever narrowed.
- See also repo-specific rule 2, which bounds *when* a migration may still be edited: published SQL
  never, docblocks always, and a local unpushed migration set is still yours to rewrite or condense.

### 7. You are adding a row to a hand-maintained index, landing an ADR — or you just made one of its pending claims true

- **Re-derive the next free id by grep, at the moment you write the row** — never from memory, never
  from a view you read earlier in the session. Five ids collided on one branch because the author was
  working from a `docs/BACKLOG.md` that predated additions made two days earlier.
- **Never renumber an existing id.** They are stable cross-document anchors cited from
  `docs/LOAD-BEARING.md`, six ADRs, a test file, and this document.
- ⚑ **When an index collides, look for what else the same stale view produced.** The stale read that
  duplicated five ids had also duplicated an entire row on an unrelated subject. The collision is
  rarely the only artefact, and the second one is not visible from the diff.
- **Landing an ADR is three `docs/adr/README.md` edits** — index row, relationship graph, crosswalk row
  — **plus** the header `Crosswalk` field and the `## ` sections in
  [`docs/adr/AUTHORING.md`](docs/adr/AUTHORING.md) §Section template. This is restated here
  rather than left in `AUTHORING.md` because that file was read carefully and the checklist was still
  missed in four places: **a checklist in a file you must remember to open is not a forcing function.**
- **Realizing a record is the mirror of landing one, and only landing has a checklist.** When the last
  `(done)` goes into a realization plan — or you ship what a *"Pending until green"* / *"(target)"* list
  names — that record's **`Status`**, **`Enforced by`** and **`Realized in`** belong in **that**
  changeset. `feat/dbal-only-persistence` shipped three PHPStan rules enforcing ADR-0018 while ADR-0018
  still read `Status: realization pending` and "Enforced by: no new architecture rule is proposed yet";
  `feat/test-standards` did the same to ADR-0035. The error is always in the *under*-claiming direction,
  which is why nobody chases it — and an ADR left `Proposed` stops binding under repo-specific rule 7.
  ⚑ `AUTHORING.md` has maintenance sections for *adding* and *superseding* and **none for realizing**,
  so this bullet is the only home.
- **The cheap detector is the sibling record.** Both ADR-0018 misses were visible from ADR-0019, which
  already listed the three rules. When two records cover one decision, the one still saying *not yet* is
  the stale one.
- **Cite by symbol or grep pattern, never by line number.** Replacing a rotted pointer with a fresh
  hand-maintained one is not a fix.

> **These rules are interim where they are mechanical.** `docs/BACKLOG.md` id-uniqueness and ADR
> template conformance are both lintable, and both are recorded as owed (TASK-020). Prose rules degrade
> with volume — every rule added to this section makes the others marginally less likely to be read, so
> the bar for adding an eighth is that it has actually fired more than once.
>
> ⚑ **That bar was tested and it held — a dated measurement, not a live count.** A systematic pass over
> our accumulated pre-merge reviews (2026-07 → 2026-08) produced **no new rule**: every survivor was one
> of the seven above aimed a notch off, or a deterministic check that belongs in tooling. The largest
> bucket by a wide margin was *"the instruction already existed and was missed"*, spread across
> separately-located cases — so **prose is demonstrably not the binding constraint, and before proposing
> an eighth rule, check whether it can be a check instead.**
> ⚠ **Read that as a stamp, not a statistic, and do not refresh it with a fresh number.** The review
> corpus it was measured over is deliberately **not in this repository**, so nothing here can verify a
> figure or recompute one — a precise count would look authoritative with nothing to click. That is the
> same trap as the stale-locator rule above, one level up. If you re-run the exercise, add a new dated
> line; do not edit this one.
>
> ⚠ **And do not overestimate what this section buys.** On the day it was drafted, the same session that
> wrote it went on to commit two of the errors it names — a fresh *X because Y* whose Y was false,
> written into the very docblock being corrected, and two tests that could not fail. Knowing a rule is
> not the same as applying it under momentum. What caught both was **mechanical**: sabotaging a guard and
> watching it fail for the right reason, and probing for execution rather than trusting a coverage
> number. Treat rule 4's *Sabotage before you trust it* step and rule 1's one-command `rg` sweep as the
> load-bearing parts; the rest is a prompt, not a guarantee.

## Repo-specific rules

1. **Don't regenerate `composer.lock`** without an explicit request.
2. **Schema changes go through Doctrine migrations.** Never edit the **SQL** of a migration that has been **published** (pushed, so someone else may have run it) — supersede it with a new migration instead. Two carve-outs, both deliberate:
   - **Comment and docblock corrections are always in scope**, published or not. Authoring rule 1 names migration docblocks as the *highest-value* rotting surface precisely because nobody re-reads an applied migration except to reconstruct why the schema looks as it does — so a stale rationale there does maximum damage. Nothing re-runs when you fix a comment.
   - **On a local, unpushed branch the migration set is still yours.** It may legitimately be edited, reordered or condensed into a single migration before the merge; "applied on your dev volume" is not "published".

   If the migration writes rows the domain reads, authoring rule 6 applies.
3. **Async work goes through Symfony Messenger** — never block on slow services from a sync handler.
4. **`.env` / `.env.<env>` are committed; real secrets are not.** They carry non-secret, dev-stack defaults and serve as the discoverability surface for which variables exist (see the load-order header in `.env`). Never commit a real credential — production/staging DB passwords, real API tokens, a real `APP_SECRET`, the real DSS keystore password — those live only in gitignored `.env.local` / `.env.*.local` (or the [Symfony secrets vault](https://symfony.com/doc/current/configuration/secrets.html)). ⛔ **For a sensitive var with no safe default there are TWO patterns, and the default one is *absence*.** `.env` ships **inside the production image**, so a key named there always resolves and production would boot on the committed value — which is why a placeholder is the wrong instinct, and why `.env`'s own header says *"do not 'fix' that absence by committing a placeholder"*.
   - **(A) Absent — the standard.** `DATABASE_URL`, `APP_SECRET`, `MESSENGER_TRANSPORT_DSN`, `SESSION_CREDENTIAL_SECRET`, `ACCESS_CODE_PEPPER`, `IDENTITY_DATABASE_URL`, `PROVISIONING_DATABASE_URL`, `RATE_LIMITER_DSN`, `SMS_DSN`. `%env()%` then fails at container build rather than falling back to a development password, and `f5sign-infra` injects the real value from `.env.prod`. Discoverability is served by the load-order header in `.env`, which *names* them in prose — **read that header rather than this list**, which is a hand-maintained copy and has lagged it before: three names were once listed in that header while missing here, and it had lagged **again** by two (`ACCESS_CODE_PEPPER` and `SMS_DSN`) when TASK-030 landed — the second of which this list is the reason to check, since a committed `SMS_DSN` would make production spend money through whichever account the default named. ⚑ `SESSION_CREDENTIAL_SECRET` was deliberately **separate from the retired `SIGNING_TOKEN_SECRET`** (ADR-0050 §7.3), so the two credential types could not be confused for one another. That sibling went with `BL-148` when the signing token became store-backed and stopped needing a key at all; the rule it illustrates binds the next credential that does.
   - **(B) Present-but-empty — the narrow exception.** `FIELD_ENCRYPTION_SECRET=` only. Safe because an empty value can **never** be a working key *and* its consumer refuses anything under 32 bytes. ⚠ **Not transferable**: `SESSION_CREDENTIAL_SECRET` has a working dev value in `.env.dev`, so committing it empty would not fail closed.

   The committed local Postgres/RabbitMQ creds are stack-local defaults (they match the infra compose), not secrets.
5. **Never run `docker compose` from this repo.** All infra (Postgres, RabbitMQ, MinIO) is brought up from `../f5sign-infra` via `make up`. Symfony Flex's `compose.yaml` recipes are disabled (`extra.symfony.docker=false`) and gitignored — if a recipe regenerates them, delete; don't commit.
6. **Don't run tooling directly from the host.** Use the infra Makefile — a dedicated target where one exists, otherwise `make composer cmd="<script>"` / `make sf cmd="<command>"`. Direct `vendor/bin/phpunit` from the host will fail on any DB-touching test; direct PHPStan/Deptrac runs work but skip the canonical path. ⚠ **`make shell` is not an alternative to these** — it is an interactive shell and returns nothing to a non-interactive caller.
7. **Check `docs/adr/` before cross-cutting structural changes.** Before changing a kernel/foundation contract, a cross-BC dependency, or a realization pattern (use-case / adapter / reactor shape), check [`docs/adr/`](docs/adr/) for a governing decision. Contradicting an accepted ADR is an ADR change (a new ADR, or marking the old one `Superseded`), not a silent edit.
8. **Read [`docs/LOAD-BEARING.md`](docs/LOAD-BEARING.md) before removing or generalizing anything structural.** Rule 7 tells you to find the governing decision; this tells you which guards *look* like duplication or dead weight and are not. Several load-bearing decisions here are deliberately un-DRY — an `EntityReference` that must not extend `EntityId`, a row lock that must not be narrowed below `save()`'s write set, a paired handler/ID ceremony that must not be abstracted — so the plausible cleanup is the failure mode. It also carries the **Never** list: changes already proposed, argued, and rejected, with the reason, so the argument is not re-run from scratch.

## Where the specs live

**In-repo (this repo — self-contained, authored where the code is):**

- **Architecture overview (start here)**: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the one-page entry doc: the system, substrate + bounded contexts, the load-bearing contracts, and a question→doc routing table.
- **Architecture decisions**: [`docs/adr/`](docs/adr/) — cross-cutting decisions as ADRs (ADR-0001…), with [`README.md`](docs/adr/README.md) (index + relationship graph + crosswalk to legacy `DEC-*`) and [`AUTHORING.md`](docs/adr/AUTHORING.md) (how to write one). ADRs reference in-repo code + each other, never the design repo. **New architecture decisions are authored here**; legacy `DEC-*` in the design repo drain forward into this set as they discharge. Each ADR's "Enforced by" points at the real rules/tests that hold it.
- **PHPStan rules**: [`phpstan/README.md`](phpstan/README.md) — the truth-surface for what each rule enforces; [`phpstan/AUTHORING.md`](phpstan/AUTHORING.md) — how to write a new rule.
- **Kernel categories (domain contracts)**: their canonical definitions are the source docblocks in [`src/F5Sign/Kernel/`](src/F5Sign/Kernel/) — see "Architecture — kernel categories" above for the enumeration grep + walk-convention.
- **Test conventions**: [`tests/README.md`](tests/README.md) — property-driven-TDD layout, conventions, and how to find the properties already locked.

**Design repo (`../f5sign-doc/Arquitectura/` — the *why*-history; NOT available under agent-only-backend access. Do not rely on these for the *what* — each has an in-repo home below):**

<!-- OFFREPO: the design-repo refs in this file (this section + inline `§N`/`DEC-*`/`DI`/`F` markers) live in the sibling design repo `../f5sign-doc/Arquitectura/` (dir `f5sign-doc/`, git remote name `innasign-doc`); not reachable under agent-only backend access. Any residual `../../Arquitectura/` path sweep tracked in docs/BACKLOG.md BL-3. -->

- **Platform foundations** (`tech/00 - platform-foundations.md`) — *why* behind the infrastructure substrate. In-repo *what*: the `F5Sign/Foundation/` source + ADRs.
- **Domain kernel** (`tech/01 - domain-kernel.md`) — *why* behind the categories. **In-repo *what*: the kernel source docblocks** (see "Architecture — kernel categories" above).
- **Per-BC tech-docs** (`tech/<bc>.md`) — *why* per BC. In-repo *what*: the BC's `src/F5Sign/<BC>/` source.
- **Cross-cutting DDD rules** (`conventions.md §6`, legacy `DEC-*`) — In-repo *what*: [`docs/adr/`](docs/adr/) (the `DEC-*` drain here).
- **Testing-assumptions catalogs** (`tech/{kernel,envelope}-testing-assumptions.md`) — In-repo *what*: [`tests/README.md`](tests/README.md) + the `P-§` statements in test docblocks.
- **BC drafts / substrate-state trackers** (`COMMITMENTS.md`, `DESIGN_INCONSISTENCIES.md`, `FINDINGS.md`, `DECISIONS.md`) — design-repo *why*-history; not needed to write conformant code.
