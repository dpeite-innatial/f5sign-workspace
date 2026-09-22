# f5sign-dashboard — Operational guide for Claude Code

Admin frontend for the F5Sign product. Panel used by senders to manage envelopes, users, billing, webhooks, API keys. Production domain: `app.f5sign.com`.

## Stack

- **Nuxt** 3.x with **Vue** 3.x (Composition API + `<script setup>`)
- **TypeScript** 5.x in strict mode (`strict: true`, `noUncheckedIndexedAccess: true`)
- **Pinia** (via `@pinia/nuxt`) for state management
- **Tailwind CSS** 3.x (via `@nuxtjs/tailwindcss`)
- **vue-i18n** (via `@nuxtjs/i18n`) — locales `es` and `en` in MVP
- **@vueuse/core** for utility composables
- **@headlessui/vue** for accessible components (modals, dropdowns)
- **zod** for schema validation
- **chart.js** + **vue-chartjs** for analytics charts
- **ofetch** (built-in via `$fetch`) as the HTTP client against the backend
- **pnpm** 9.x as package manager, **Node** 20 LTS

## Commands

| Action | Command |
|--------|---------|
| Install deps | `pnpm install` |
| Dev server (port 3000) | `pnpm dev` |
| Production build | `pnpm build` |
| Build preview | `pnpm preview` |
| Lint | `pnpm lint` |
| Lint + fix | `pnpm lint:fix` |
| Typecheck | `pnpm typecheck` |
| Format check | `pnpm format:check` |
| Format (apply) | `pnpm format` |
| Unit tests | `pnpm test` (Vitest; introduced in EP26) |
| E2E | `pnpm test:e2e` (Playwright; introduced in EP26) |
| Clean | `pnpm clean` |

> **CRITICAL — tests ALWAYS run in Docker, NEVER locally.** Don't run
> `pnpm install` or tests/lint/typecheck/build directly on your machine: they contaminate
> the host with dependencies and diverge from the reproducible environment. The `pnpm *`
> commands above are the ones run **inside** the `dashboard` container. The dashboard
> doesn't have a test suite yet; when it's added (EP26), it will run via `make
> test-dashboard*` targets from `../f5sign-infra/` (with the stack up, `make up`), same as
> the signer (see `../f5sign-infra/CLAUDE.md` § "Frontend tests in Docker"). The E2E tests
> will run in a dedicated container with the official Playwright image (the `dashboard`
> container is Alpine and Playwright doesn't support it).

### Worktrees: today there's no isolated validation path

⛔ **The dashboard has no ephemeral lane.** The signer and the backend do
(`make -C ../f5sign-infra wt-signer` / `wt-backend`): they spin up their own stack that mounts *your*
tree and destroy it when done. **`wt-dashboard` doesn't exist**, and `docker-compose.override.yml`
bind-mounts `../f5sign-dashboard`, the **main** checkout, hardcoded — so a worktree never gets mounted.

- **Check where you are:** `git rev-parse --git-dir` — if the path contains `/worktrees/`, you're in one.
- **From a dashboard worktree**, anything that runs in the `dashboard` container validates the main
  checkout's tree. Today that matters little because there's no suite; **it will matter as soon as EP26
  brings it**, and then this becomes the same trap the backend documents in five places: the run passes,
  the numbers are plausible, and the answer is about a different branch.
- **In the meantime: state it.** If you work in a dashboard worktree, the report says *"not validated in
  container"*, not a green borrowed from the main checkout.

▶ **What it would take:** a `docker-compose.wt.dashboard.yml` + entry in `scripts/wt-validate.sh`,
copied from the signer, which already solves the whole frontend case. It comes with EP26, not before:
without a suite there's nothing to isolate. Noted here on 2026-08-25 so EP26 doesn't close without it.

## Code structure

Standard Nuxt conventions at the repo root (no monorepo):

```
f5sign-dashboard/
├── app.vue                      ← <NuxtLayout><NuxtPage/>
├── nuxt.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── assets/css/tailwind.css
├── components/                  ← reusable components
├── composables/                 ← composables (useXxx)
├── layouts/                     ← layouts (default, auth, etc.)
├── middleware/                  ← global / per-route
├── pages/                       ← file-based routing
├── plugins/
├── public/
├── stores/                      ← Pinia stores
├── types/                       ← type declarations (incl. runtime-config.d.ts)
└── locales/
    ├── es.json
    └── en.json
```

## Code conventions

- **`<script setup lang="ts">`** by default in all components.
- **Components** in multi-word PascalCase (`UserTable.vue`, not `Table.vue`).
- **Composables** with `use*` prefix (`useEnvelopes`, `useAuth`).
- **Pinia stores** in `stores/<domain>.ts` using setup-style (`defineStore('envelopes', () => { ... })`).
- **No `any`** except with explicit justification via comment (prefer `unknown` + narrowing).
- **API calls** via typed composables (`useEnvelopes().list()`), not direct `$fetch` in components.
- **i18n**: all user-visible strings go through `t('key')`, never hardcoded. Key parity between `es.json` and `en.json`.
- **Forms**: validation with `zod` schema + visible feedback.
- **Accessibility**: WCAG AA minimum (contrast, visible focus, keyboard navigation, ARIA where applicable).
- **Commits**: convention in the workspace root `CLAUDE.md` § *Commits*.

## Location of relevant specs

- **Frontend Architecture**: `../f5sign-docs/Arquitectura/Arquitectura Frontend.md` § 2 (structure), § 4 (Dashboard: pages, components, stores), § 8 (i18n), § 9 (environments).
- **API contracts**: in each task's spec (`Detalle tecnico > Contratos externos`). Own TS types manually derived from the backend's Response DTOs (see `../f5sign-docs/.claude/skills/planning-detail/references/dev-conventions.md` § tipos TS).
- **Use cases**: `../f5sign-docs/Casos de Uso/` (Dashboard flows).
- **Deployment modes**: `../f5sign-docs/Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md`.
- **Planning by task**: `../f5sign-docs/Planning/F*/EP*/S*/T*.md`.

`f5sign-docs` is read-only from here. The only writes to `Planning/` are to close `Seguimiento` (see AGENT-RUNBOOK).

## Repo-specific rules

1. **Don't regenerate `pnpm-lock.yaml`** without explicit request.
2. **Don't add heavy UI dependencies** without justification (headless-ui already covers most patterns).
3. **Runtime config**: every runtime-configurable variable lives in `runtimeConfig.public` and is overridden with `NUXT_PUBLIC_*`. **No secrets in `public`** (it's visible in the client bundle).
4. **i18n planned from the start**: new strings go into both locales at once. Never ship a key only in `es`.
5. **SaaS vs Dedicated**: use `useRuntimeConfig().public.deploymentMode` for conditionals. Don't create premature abstraction layers; check directly at the point of use.
6. **Don't commit `.env`.** Only `.env.example`.
7. **SPA with no SSR** (global `ssr: false`). In prod the dashboard is served as static (`nuxt generate` → `.output/public`) baked into the `f5sign-web` nginx image from `../f5sign-infra`; it's an admin panel behind login (no SEO), so SSR adds nothing. Don't introduce SSR-only code (`useRequestEvent`, `import.meta.server`, etc.); everything is client-side.
