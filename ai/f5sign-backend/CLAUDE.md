# innasign-backend — Operational guide for Claude Code

Symfony skeleton evolved into the **InnaSign prototype** that exercises the locked tech-design commitments at [`Arquitectura/DDD/tech/00 - platform-foundations.md`](../../Arquitectura/DDD/tech/00%20-%20platform-foundations.md), [`01 - domain-kernel.md`](../../Arquitectura/DDD/tech/01%20-%20domain-kernel.md), and the per-BC tech-docs. Per the lock-via-exercise paradigm, this prototype + its property-tests + scenario tests are the substrate that converts designed commitments into locked ones.

## Current state

- `src/Innasign/` holds the populated kernel + foundation + 5 BC scaffold:
  - `Innasign/Kernel/` — categories (`Command`, `Query`, `Event`, `DomainEvent`, `AuditableEvent`, `ValueObject`, `Entity`, `AggregateRoot`, `EntityId`, `Reactor`), capabilities (`Subject`, `Equatable`, `Issued`, `Issuer`), `Repository`, `Time` (incl. test doubles), `Context`.
  - `Innasign/Foundation/` — `Bus` (Messenger adapters: `MessengerCommandHandler`, `MessengerEventSubscriber`), `Outbox`, `Persistence`, `Identity` (UUID/string IDs), `Time` (system clock), `ValueObject` (`GenericValidationException`, `Uri`), `Billing` (metering port).
  - `Innasign/Envelope/` — populated BC (Domain + Application + Contract + Infrastructure) per the vertical slice.
  - `Innasign/SignatureExecution/` and `Innasign/EvidenceAudit/` — partial scaffolds (Contract + Application or Infrastructure).
  - Session and Legal — not yet populated (deptrac layers pre-scaffolded; classes pending).
- `App\` namespace remains for `App\Kernel` (Symfony app kernel) + `App\PHPStan\Rules\` (custom architecture rules at `phpstan/src/Rules/`; sibling `phpstan/tests/Rules/` for rule tests — reference test landed at `EntityFinalConcreteRuleTest.php`).
- PHP version: 8.5; strict types throughout.

## Architecture — kernel categories (read before domain work)

The architectural contracts are the **kernel categories** in `src/Innasign/Kernel/`. Each category's **canonical definition is its own source docblock** — a short description, the invariants it must uphold, and the rationale. They're self-contained: you do **not** need the design repo to understand or honor them.

- **Enumerate the ontology**, one command: `grep -rnE "Kernel (sub-)?category" src/Innasign/Kernel/`. Each hit is a category (or sub-category) interface/abstract — open it and read the docblock.
- **Before implementing or modifying** a type in a kernel category, read that category's source docblock — it states the invariants your code must satisfy.
- **Follow `@see`** to walk the concept graph; related contracts link via `@see \Fully\Qualified\Name`.
- **When a PHPStan rule fires**, its message names the in-repo home that explains *why* — a class to open, `docs/adr/ADR-NNNN`, or `phpstan/README.md`.

**`@see` convention:** every `@see` that references a class is written **fully-qualified** (`@see \Innasign\Kernel\…`), even when the symbol is imported — so the concept graph is greppable by canonical name regardless of local imports/aliases. `php-cs-fixer` is configured to preserve this (it shortens other phpdoc type tags but leaves `@see` alone; see `.php-cs-fixer.dist.php`).

## Stack

- Symfony 7.4
- PHP 8.5 (strict types)
- Doctrine ORM 3 + DoctrineMigrationsBundle (foundations §2.4)
- Symfony Messenger + RabbitMQ for async (§2.5–§2.8)
- Symfony Lock + Cache (Redis backend) + RateLimiter
- PostgreSQL 16 (§2.3)
- PHPUnit 11.5 (with `dama/doctrine-test-bundle` for transactional isolation)
- PHPStan ≥ 2.1 level 9 + custom architecture rules
- Deptrac ≥ 4.6 (visibility contract; 5 BC layers pre-scaffolded in [`deptrac.yaml`](deptrac.yaml))
- PHP-CS-Fixer
- Xdebug (mode=off by default; coverage / step-debug via env override)

## Bundles enabled

| Bundle | Envs |
|--------|------|
| FrameworkBundle | all |
| DoctrineBundle | all |
| DoctrineMigrationsBundle | all |
| MakerBundle | dev |
| DAMADoctrineTestBundle | test |
| DoctrineFixturesBundle | dev, test |

Not enabled (out of scope): SecurityBundle, LexikJWTAuthenticationBundle, TwigBundle, WebProfilerBundle, DebugBundle.

## Running tests + tooling — always via the infra Makefile

**Tests, PHPStan, Deptrac, lint, and Symfony console all run inside the `php-fpm` container** brought up by [`prototype/innasign-infra`](../innasign-infra/). The container has the network routes to `postgresql`, `postgres-test`, `rabbitmq`, and `minio`; the host does not. Running `vendor/bin/phpunit` or `vendor/bin/phpstan` directly from the host shell will:

- pass for purely-static checks (phpstan analyse) but bypass the canonical run path,
- **fail for any test that touches Postgres / RabbitMQ** (`could not translate host name "postgres-test"`),
- skip the `ensure-stack` precondition that catches "stack not up" cleanly.

Always invoke through the infra repo's Makefile:

| Action | Make target (run from `../innasign-infra/`) |
|--------|---------------------------------------------|
| Full setup (build + up + install + migrate) | `make install` |
| Stack up / down | `make up` / `make down` |
| Tests (auto-ensures stack + test-db) | `make test` |
| Tests with HTML coverage | `make test-coverage` |
| Static analysis | `make phpstan` |
| Architecture (deptrac) | `make shell` then `composer arch` (no direct target yet) |
| Lint | `make lint` |
| Format (apply) | `make format` |
| Full QA (phpstan + arch + lint + tests) | `make qa` |
| Migrations | `make migrate` |
| New migration | `make migration` |
| Symfony console | `make sf cmd="<command>"` |
| Composer | `make composer cmd="<command>"` |
| Container shell | `make shell` |
| Test DB lifecycle | `make test-db-up` / `test-db-setup` / `test-db-down` / `test-db-reset` |
| Worker (Messenger consumer) | `make worker-up` / `worker-down` / `worker-status` |

**Inside the container shell** (after `make shell`) the equivalents are `php bin/console …`, `vendor/bin/phpunit`, `vendor/bin/phpstan analyse`, `vendor/bin/deptrac analyse`, `vendor/bin/php-cs-fixer fix`, `composer <script>`. The composer scripts (`test`, `phpstan`, `arch`, `lint`, `format`, `qa`) are wired and equivalent to the make targets.

**Async worker** sits behind the `workers` profile and is off by default — dispatching to `async` enqueues but doesn't consume until `make worker-up` runs. `make worker-status` shows queue depth.

## Conventions (in force)

- PSR-12 + `declare(strict_types=1);` everywhere.
- Domain layer cannot import Doctrine, Symfony, or any framework — enforced by Deptrac (`deptrac.yaml`) plus the kernel-placement PHPStan rules.
- Tests in four layers per kernel §3.5: `Unit/`, `Handler/`, `Integration/`, `Scenario/`. Tree mirrors `src/Innasign/<BC>/` under `tests/Innasign/<BC>/<layer>/`.
- New tests must declare `#[CoversClass]` (or `#[CoversNothing]`) — `phpunit.dist.xml` has `requireCoverageMetadata="true"`. Use `#[UsesClass]` for collaborators.
- Property-driven TDD: see [`tests/README.md`](tests/README.md) for the in-repo convention (layout, `P-§` docblock citation, how to find properties already locked). The full property catalogs are design-repo (`Arquitectura/DDD/tech/{kernel,envelope}-testing-assumptions.md`) and may be unavailable under agent-only access — `tests/README.md` is self-sufficient.
- The PHPStan baseline at [`phpstan-baseline.neon`](phpstan-baseline.neon) is the catalogue of design-blocked findings — each entry maps to a tracked DI / F item. Do not extend without categorising the new finding in `/FINDINGS.md` and `/DESIGN_INCONSISTENCIES.md`.
- Deptrac currently has no equivalent baseline mechanism; violations should be enumerated as findings directly, not silently allowed.

## Repo-specific rules

1. **Don't regenerate `composer.lock`** without an explicit request.
2. **Schema changes go through Doctrine migrations.** No editing applied migrations.
3. **Async work goes through Symfony Messenger** — never block on slow services from a sync handler.
4. **`.env` is never committed** — only `.env.example`, `.env.dev`, `.env.test`, `.env.test.local.dist`.
5. **Never run `docker compose` from this repo.** All infra (Postgres, RabbitMQ, MinIO) is brought up from `../innasign-infra` via `make up`. Symfony Flex's `compose.yaml` recipes are disabled (`extra.symfony.docker=false`) and gitignored — if a recipe regenerates them, delete; don't commit.
6. **Don't run tooling directly from the host.** Use the infra Makefile (or `make shell` then composer scripts). Direct `vendor/bin/phpunit` from the host will fail on any DB-touching test; direct PHPStan/Deptrac runs work but skip the canonical path.
7. **Check `docs/adr/` before cross-cutting structural changes.** Before changing a kernel/foundation contract, a cross-BC dependency, or a realization pattern (use-case / adapter / reactor shape), check [`docs/adr/`](docs/adr/) for a governing decision. Contradicting an accepted ADR is an ADR change (a new ADR, or marking the old one `Superseded`), not a silent edit.

## Where the specs live

**In-repo (this repo — self-contained, authored where the code is):**

- **Architecture overview (start here)**: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the one-page entry doc: the system, substrate + bounded contexts, the load-bearing contracts, and a question→doc routing table.
- **Architecture decisions**: [`docs/adr/`](docs/adr/) — cross-cutting decisions as ADRs (ADR-0001…), with [`README.md`](docs/adr/README.md) (index + relationship graph + crosswalk to legacy `DEC-*`) and [`AUTHORING.md`](docs/adr/AUTHORING.md) (how to write one). ADRs reference in-repo code + each other, never the design repo. **New architecture decisions are authored here**; legacy `DEC-*` in the design repo drain forward into this set as they discharge. Each ADR's "Enforced by" points at the real rules/tests that hold it.
- **PHPStan rules**: [`phpstan/README.md`](phpstan/README.md) — the truth-surface for what each rule enforces; [`phpstan/AUTHORING.md`](phpstan/AUTHORING.md) — how to write a new rule.
- **Kernel categories (domain contracts)**: their canonical definitions are the source docblocks in [`src/Innasign/Kernel/`](src/Innasign/Kernel/) — see "Architecture — kernel categories" above for the enumeration grep + walk-convention.
- **Test conventions**: [`tests/README.md`](tests/README.md) — property-driven-TDD layout, conventions, and how to find the properties already locked.

**Design repo (`../../Arquitectura/` — the *why*-history; NOT available under agent-only-backend access. Do not rely on these for the *what* — each has an in-repo home below):**

- **Platform foundations** (`tech/00 - platform-foundations.md`) — *why* behind the infrastructure substrate. In-repo *what*: the `Innasign/Foundation/` source + ADRs.
- **Domain kernel** (`tech/01 - domain-kernel.md`) — *why* behind the categories. **In-repo *what*: the kernel source docblocks** (see "Architecture — kernel categories" above).
- **Per-BC tech-docs** (`tech/<bc>.md`) — *why* per BC. In-repo *what*: the BC's `src/Innasign/<BC>/` source.
- **Cross-cutting DDD rules** (`conventions.md §6`, legacy `DEC-*`) — In-repo *what*: [`docs/adr/`](docs/adr/) (the `DEC-*` drain here).
- **Testing-assumptions catalogs** (`tech/{kernel,envelope}-testing-assumptions.md`) — In-repo *what*: [`tests/README.md`](tests/README.md) + the `P-§` statements in test docblocks.
- **BC drafts / substrate-state trackers** (`COMMITMENTS.md`, `DESIGN_INCONSISTENCIES.md`, `FINDINGS.md`, `DECISIONS.md`) — design-repo *why*-history; not needed to write conformant code.
