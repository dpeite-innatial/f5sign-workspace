# f5sign-signer — Operational Guide for Claude Code

Signing frontend for the signer in F5Sign. Public experience (no account required) accessed via a signed link `/s/:token`. Mobile-first: modest devices with unstable connections are the main target. Production domain: `sign.f5sign.com` (or `firma.<tenant>.com` in white-label).

## Stack

- **Nuxt** 4.x with **Vue** 3.5+ (Composition API + `<script setup>`). New layout: app code in `app/`, configs and `tests/`/`public/`/`types/`/`i18n/` at the root.
- **TypeScript** 5.x in strict mode
- **Pinia** 3.x (via `@pinia/nuxt` 0.11.x) for state management
- **Tailwind CSS** 3.x with mobile-safe reset (iOS anti-zoom)
- **vue-i18n** (via `@nuxtjs/i18n` 10.x) — `es` and `en` locales in the MVP (in `i18n/locales/`, not in `app/`), detection via `navigator.language` and query `?lang=`. `language` property (replaces `iso` from v8).
- **@vueuse/core** 11.x for utility composables
- **zod** for validation
- **pdfjs-dist** for inline PDF rendering
- **ofetch** (via `$fetch`) as HTTP client
- **pnpm** 9.x, **Node**: `package.json` requires `>=20.19.0` (Nuxt 4 requirement). Dev runs on `node:24-alpine`; the production `Dockerfile` builds with `node:20-alpine`, out of support since 2026-04-30.
- **postcss** ^8.5.15 forced via `pnpm.overrides` (fix for CVE GHSA-qx2v-qp2m-jg93)

Note: **no `chart.js`** or **`@headlessui/vue`** in the signer — the flow is touch-based and minimal, it doesn't need heavy admin UI.

## Commands

The general rules (Docker only, delegate to `test-runner`, worktree → `wt-signer`, declare the harness) are
in the workspace root `CLAUDE.md` § *Tests*. Here, the signer specifics: the `package.json` scripts run in the
`signer` container (dev server on 3001, to avoid clashing with the dashboard on 3000); E2E run in `signer-e2e`,
because Playwright doesn't support Alpine and the browsers come bundled in its image. With the stack up (`make up`):

| Action | Command (from f5sign-infra) |
| ------ | ---------------------------- |
| Lint + typecheck + unit | `make test-signer` |
| Unit only (Vitest) | `make test-signer-unit` |
| Full E2E (Playwright, 4 profiles) | `make test-signer-e2e` |
| E2E smoke (mobile-iphone-se) | `make test-signer-e2e-mobile` |

- **`pnpm test` measures coverage with an 80% threshold**: a failure due to coverage alone is a failure, not a false positive.

## Code structure

Nuxt 4 default layout (`srcDir: 'app/'`):

```
f5sign-signer/
├── nuxt.config.ts               ← viewport-fit=cover, theme-color
├── tailwind.config.ts
├── tsconfig.json                ← extends .nuxt/tsconfig.json
├── tsconfig.test.json           ← standalone for Vitest
├── vitest.config.ts
├── app/                         ← srcDir (Nuxt 4)
│   ├── app.vue                  ← <NuxtLayout><NuxtPage/>
│   ├── assets/css/tailwind.css  ← mobile reset (iOS anti-zoom)
│   ├── components/              ← base/ · layout/ · signer/ (+ fields/, workspace/) · status/
│   ├── composables/
│   │   └── api/                 ← SigningApi mock/real + types + fixtures loader
│   ├── layouts/                 ← default.vue (mobile-first, no sidebar) + workspace.vue
│   ├── middleware/              ← session.global.ts
│   ├── pages/
│   ├── plugins/
│   ├── stores/
│   └── utils/                   ← Sentry scrub/redact, signingToken, errorReporter
├── i18n/locales/                ← ⚠ NOT in app/: restructureDir from @nuxtjs/i18n v10
│   ├── es.json
│   └── en.json
├── scripts/                     ← check-bundle · check-contract · inject-csp · copy-pdfjs-worker
├── docker/                      ← Caddyfile (serves the static SPA; CSP and cache live there)
├── public/                      ← static assets
├── types/                       ← global d.ts (runtime-config, etc.)
└── tests/
    ├── fixtures/signing-session/  ← JSONs + sample-contract.pdf
    ├── helpers/ · setup.ts
    ├── unit/
    └── e2e/                       ← Playwright (4 profiles)
```

## Code conventions

- **`<script setup lang="ts">`** by default.
- **Components** in multi-word PascalCase.
- **Composables** with `use*` prefix.
- **No `any`** without justification.
- **i18n**: all strings via `t('key')`. Parity between `es.json` and `en.json`.
- **Mobile-first**: base styles are for mobile, `md:`/`lg:` variants add refinements for tablet/desktop. Not the other way around.
- **Touch events** first; mouse events as fallback.
- **Performance**: lazy-load PDF pages, avoid loading heavy bundles on the initial route.
- **Accessibility**: WCAG AA. The signing experience must have a textual fallback (checkbox acceptance) for screen readers where the canvas isn't viable.
- **Commits**: convention in the workspace root `CLAUDE.md` § *Commits*.

## Location of relevant specs

- **Frontend Architecture**: `../f5sign-docs/Arquitectura/Arquitectura Frontend.md` § 5 (Signer: routes, components, flow), § 8 (i18n), § 9 (environments).
- **PAdES signing and cryptography**: `../f5sign-docs/Arquitectura/Pilares/5. Firma Digital y Criptografía.md`.
- **Signing use cases**: `../f5sign-docs/Casos de Uso/`.
- **Where the work comes from**: from the handoffs, not from `Planning/`. The backend's are in `../f5sign-backend/docs/frontend-handoff/`; the signer's own are in `docs/HANDOFF-*.md`. Docs' `Planning/` hasn't been touched since 2026-06-17 and no signer commit since August cites a `T*` id.

`f5sign-docs` is read-only from here.

## Repo-specific rules

1. **Privacy — CRITICAL**: don't log biometric data ([x,y,t,p] strokes from the canvas), document content, or the link's `access_token`. No `console.log` of sensitive data in production.
2. **Session verdict gets ROUTED, never painted in a corner — CRITICAL.** The
   global middleware cuts out on the very first line for any sub-route
   (`if (!isIndexRoute) return`, to avoid re-entering on SSR), so on `/view`, `/sign`,
   `/review`, `/decline`, `/click-sign` **and also the terminal routes** (`/done`,
   `/declined`, `/expired`, `/unavailable`) **nobody revalidates anything**: they're
   painted entirely from the persisted store, which could belong to a dead session —or
   to another link, or to none at all—. Every sub-route must use `useSessionVerdict`,
   and these rules apply:
   - **Check against the backend, not against the store.** The case that bites isn't
     the empty store, it's the POPULATED and stale store: there `session.session` exists
     and says nothing.
   - **On a 401, `clear()` before bouncing.** The middleware has a reuse branch
     (`session.session !== null && !error`) that skips the bootstrap and only recomputes
     the destination; with a stale store it sends you back to the same screen and you get
     stuck in a loop. Measured: five bounces without moving.
   - **Never confine the failure inside a component.** A 401 shown as a card inside
     the viewer leaves the ceremony alive around it — rails, fields and the sign
     button—, and a signer can go through the whole thing and **believe they signed**.
     Actually happened with a real user, on `/view` and on `/sign`.
   - **Absence of data is NOT proof of anything, and the proof has to be for THIS
     link.** No screen can assert an envelope state with an empty store: a verdict
     (`requireVerdictFor`) or read-model (`requireSessionFor`) is required for the URL's
     token, and without it nothing gets painted —back to the index, which asks and
     routes—. Two ways to get this wrong, both measured in the browser: (1) `/done` with
     an empty store fell into its `v-else` variant and said **"Firma completada"** to
     whoever opened a token that doesn't exist, with a 200 and zero network calls; (2) the
     store lives in `sessionStorage` under a single key, so a second link in the same tab
     painted the first one's data —document, sender, signing date— under the second
     link's URL. Corollaries: a status screen's `v-else` becomes `v-else-if="proven"`
     (otherwise the success branch swallows the gap), and `/invalid` NEVER has a gate: it's
     the honest destination that everything else bounces to.
   - **But routing isn't always the answer: a failure with an on-the-spot remedy gets
     resolved on the spot.** The 401 `AUTH_NO_OPEN_CHALLENGE` from `commit` (SIGNING gate
     declared and unanswered) is handled with the modal over `/sign`, not by navigating to
     `/auth`: the signature and the evidence live in RAM and don't survive a page jump.
     Measured: the signer went through the ceremony **twice** —code, landing on `/view`,
     tapping Sign again, collecting evidence again— for a single signature. Its sibling
     `AUTH_REAUTH_REQUIRED` does go to `/auth`, because it's the ACCESS gate expired by
     inactivity and the modal doesn't serve it. Telling them apart is the job.
3. **Don't regenerate `pnpm-lock.yaml`** without an explicit request.
4. **Mobile compatibility**: always test on **Safari iOS** and Chrome Android before closing a task with UI changes. Chrome DevTools mobile doesn't replace a real device.
5. **Performance as a requirement, not a later optimization**: lazy-load, code-splitting, no unnecessary dependencies. Target budget: initial bundle < 200KB gzipped.
6. **Accessibility with textual fallback**: every step requiring canvas or complex gestures must have a keyboard or button equivalent.
7. **Runtime config**: same rules as dashboard (`NUXT_PUBLIC_*`, no secrets). `apiMode` defaults to `'real'` so that a deploy without an override doesn't serve mock fixtures.
8. **White-label (Dedicated)**: branding is resolved via the `Host` header in middleware (F3). The skeleton leaves the structure ready but doesn't implement the logic.
9. **Don't commit `.env`.** Only `.env.example`.
10. **Two symbolically distinct domains** (`sign.f5sign.com` and `firma.<tenant>.com`) point to the same app with branding middleware; don't duplicate code.
