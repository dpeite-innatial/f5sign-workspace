# f5sign-dashboard — Guia operativa para Claude Code

Frontend de administracion del producto F5Sign. Panel que usan los remitentes para gestionar envelopes, usuarios, billing, webhooks, API keys. Dominio en produccion: `app.f5sign.com`.

## Stack

- **Nuxt** 3.x con **Vue** 3.x (Composition API + `<script setup>`)
- **TypeScript** 5.x en modo estricto (`strict: true`, `noUncheckedIndexedAccess: true`)
- **Pinia** (via `@pinia/nuxt`) para state management
- **Tailwind CSS** 3.x (via `@nuxtjs/tailwindcss`)
- **vue-i18n** (via `@nuxtjs/i18n`) — locales `es` y `en` en MVP
- **@vueuse/core** para composables utility
- **@headlessui/vue** para componentes accesibles (modales, dropdowns)
- **zod** para validacion de schemas
- **chart.js** + **vue-chartjs** para graficas de analytics
- **ofetch** (built-in via `$fetch`) como cliente HTTP contra el backend
- **pnpm** 9.x como gestor de paquetes, **Node** 20 LTS

## Comandos

| Accion | Comando |
|--------|---------|
| Install deps | `pnpm install` |
| Dev server (puerto 3000) | `pnpm dev` |
| Build produccion | `pnpm build` |
| Preview del build | `pnpm preview` |
| Lint | `pnpm lint` |
| Lint + fix | `pnpm lint:fix` |
| Typecheck | `pnpm typecheck` |
| Format check | `pnpm format:check` |
| Format (aplicar) | `pnpm format` |
| Tests unitarios | `pnpm test` (Vitest; se introduce en EP26) |
| E2E | `pnpm test:e2e` (Playwright; se introduce en EP26) |
| Clean | `pnpm clean` |

> **CRITICO — los tests SIEMPRE corren en Docker, NUNCA en local.** No ejecutes
> `pnpm install` ni tests/lint/typecheck/build directamente en tu maquina: contaminan
> el host con dependencias y divergen del entorno reproducible. Los comandos `pnpm *`
> de arriba son los que se ejecutan **dentro** del contenedor `dashboard`. El dashboard
> aun no tiene suite de tests; cuando se anada (EP26), se ejecutara via targets `make
> test-dashboard*` desde `../f5sign-infra/` (con el stack arriba, `make up`), igual que
> el signer (ver `../f5sign-infra/CLAUDE.md` § "Tests frontend en Docker"). Los E2E
> correran en un contenedor dedicado con la imagen oficial de Playwright (el contenedor
> `dashboard` es Alpine y Playwright no lo soporta).

## Estructura del codigo

Convenciones Nuxt estandar en la raiz del repo (sin monorepo):

```
f5sign-dashboard/
├── app.vue                      ← <NuxtLayout><NuxtPage/>
├── nuxt.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── assets/css/tailwind.css
├── components/                  ← componentes reutilizables
├── composables/                 ← composables (useXxx)
├── layouts/                     ← layouts (default, auth, etc.)
├── middleware/                  ← global / per-route
├── pages/                       ← routing por fichero
├── plugins/
├── public/
├── stores/                      ← Pinia stores
├── types/                       ← declaraciones de tipos (incl. runtime-config.d.ts)
└── locales/
    ├── es.json
    └── en.json
```

## Convenciones de codigo

- **`<script setup lang="ts">`** por defecto en todos los componentes.
- **Componentes** en PascalCase multi-palabra (`UserTable.vue`, no `Table.vue`).
- **Composables** con prefijo `use*` (`useEnvelopes`, `useAuth`).
- **Stores Pinia** en `stores/<dominio>.ts` usando setup-style (`defineStore('envelopes', () => { ... })`).
- **Sin `any`** salvo justificacion explicita con comentario (prefiere `unknown` + narrowing).
- **Llamadas a API** via composables tipados (`useEnvelopes().list()`), no `$fetch` directo en componentes.
- **i18n**: todas las cadenas visibles al usuario van por `t('key')`, nunca hardcoded. Paridad de claves entre `es.json` y `en.json`.
- **Formularios**: validacion con `zod` schema + feedback visible.
- **Accesibilidad**: WCAG AA minimo (contraste, focus visible, navegacion por teclado, ARIA cuando aplique).
- **Commits**: convenciones en `../f5sign-docs/Planning/AGENT-RUNBOOK.md` § 5.

## Ubicacion de specs relevantes

- **Arquitectura Frontend**: `../f5sign-docs/Arquitectura/Arquitectura Frontend.md` § 2 (estructura), § 4 (Dashboard: paginas, componentes, stores), § 8 (i18n), § 9 (entornos).
- **API contracts**: en la spec de cada task (`Detalle tecnico > Contratos externos`). Tipos TS propios derivados manualmente de los Response DTOs del backend (ver `../f5sign-docs/.claude/skills/planning-detail/references/dev-conventions.md` § tipos TS).
- **Casos de uso**: `../f5sign-docs/Casos de Uso/` (flujos de Dashboard).
- **Modos de despliegue**: `../f5sign-docs/Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md`.
- **Planning por task**: `../f5sign-docs/Planning/F*/EP*/S*/T*.md`.

`f5sign-docs` es solo lectura desde aqui. Solo se escribe en `Planning/` para cerrar `Seguimiento` (ver AGENT-RUNBOOK).

## Reglas especificas del repo

1. **No regenerar `pnpm-lock.yaml`** sin peticion explicita.
2. **No anadir dependencias UI pesadas** sin justificacion (headless-ui ya cubre la mayoria de patrones).
3. **Runtime config**: toda variable configurable en runtime vive en `runtimeConfig.public` y se sobrescribe con `NUXT_PUBLIC_*`. **Ningun secreto en `public`** (es visible en el bundle cliente).
4. **i18n planificado desde el principio**: nuevas cadenas entran en los dos locales a la vez. Nunca shipear una clave solo en `es`.
5. **SaaS vs Dedicated**: usar `useRuntimeConfig().public.deploymentMode` para condicionales. No crear capas de abstraccion anticipadas; check directo en el punto de uso.
6. **No commitees `.env`.** Solo `.env.example`.
7. **SPA sin SSR** (`ssr: false` global). En prod el dashboard se sirve como estatico (`nuxt generate` → `.output/public`) horneado en la imagen nginx `f5sign-web` de `../f5sign-infra`; es panel admin tras login (sin SEO), por lo que SSR no aporta. No introducir codigo SSR-only (`useRequestEvent`, `import.meta.server`, etc.); todo es client-side.
