# f5sign-signer — Guia operativa para Claude Code

Frontend de firma del firmante en F5Sign. Experiencia publica (no requiere cuenta) que se accede via enlace firmado `/s/:token`. Mobile-first: dispositivos modestos con conexion inestable son el target principal. Dominio en produccion: `sign.f5sign.com` (o `firma.<tenant>.com` en white-label).

## Stack

- **Nuxt** 4.x con **Vue** 3.5+ (Composition API + `<script setup>`). Layout nuevo: codigo de app en `app/`, configs y `tests/`/`public/`/`server/`/`types/` en raiz.
- **TypeScript** 5.x en modo estricto
- **Pinia** 3.x (via `@pinia/nuxt` 0.11.x) para state management
- **Tailwind CSS** 3.x con reset mobile-safe (anti-zoom iOS)
- **vue-i18n** (via `@nuxtjs/i18n` 10.x) — locales `es` y `en` en MVP, deteccion por `navigator.language` y query `?lang=`. Propiedad `language` (sustituye `iso` de v8).
- **@vueuse/core** 11.x para composables utility
- **zod** para validacion
- **pdfjs-dist** para renderizado de PDF inline
- **ofetch** (via `$fetch`) como cliente HTTP
- **pnpm** 9.x, **Node** 20.19+ (requisito de Nuxt 4)
- **postcss** ^8.5.15 forzado via `pnpm.overrides` (fix CVE GHSA-qx2v-qp2m-jg93)

Nota: **sin `chart.js`** ni **`@headlessui/vue`** en el signer — el flujo es tactil y minimal, no necesita UI admin pesada.

## Comandos

| Accion                   | Comando                                            |
| ------------------------ | -------------------------------------------------- |
| Install deps             | `pnpm install`                                     |
| Dev server (puerto 3001) | `pnpm dev`                                         |
| Build produccion         | `pnpm build`                                       |
| Preview del build        | `pnpm preview`                                     |
| Lint                     | `pnpm lint`                                        |
| Typecheck                | `pnpm typecheck`                                   |
| Format check             | `pnpm format:check`                                |
| Tests unitarios          | `pnpm test` (Vitest)                               |
| E2E                      | `pnpm test:e2e` (Playwright)                       |
| E2E (modo UI)            | `pnpm test:e2e:ui`                                 |
| Instalar navegadores E2E | `pnpm test:e2e:install` (ejecutar una vez antes de E2E) |
| Clean                    | `pnpm clean`                                       |

> El puerto 3001 esta fijado para evitar colision con el dashboard (3000) cuando ambos corren simultaneamente via `docker compose`.

> **CRITICO — los tests SIEMPRE corren en Docker, NUNCA en local.** No ejecutes
> `pnpm install` ni los `pnpm test*`/`pnpm lint`/`pnpm typecheck`/`pnpm build`
> directamente en tu maquina: contaminan el host con dependencias y divergen del
> entorno reproducible. Los comandos `pnpm *` de la tabla de arriba son los que se
> ejecutan **dentro** de los contenedores. Desde `../f5sign-infra/` (stack arriba
> con `make up`):
>
> | Accion | Comando (desde f5sign-infra) |
> | ------ | ---------------------------- |
> | Lint + typecheck + unit | `make test-signer` |
> | Solo unit (Vitest) | `make test-signer-unit` |
> | E2E completo (Playwright, 4 perfiles) | `make test-signer-e2e` |
> | E2E smoke (mobile-iphone-se) | `make test-signer-e2e-mobile` |
>
> Unit/lint/typecheck/build corren en el contenedor `signer`. Los E2E corren en un
> contenedor dedicado con la imagen oficial de Playwright (el contenedor `signer`
> es Alpine y Playwright no lo soporta). No hace falta `pnpm test:e2e:install` en el
> host: los navegadores vienen en la imagen oficial. Detalle en `../f5sign-infra/CLAUDE.md` § "Tests frontend en Docker".

## Estructura del codigo

Nuxt 4 default layout (`srcDir: 'app/'`):

```
f5sign-signer/
├── nuxt.config.ts               ← viewport-fit=cover, theme-color
├── tailwind.config.ts
├── tsconfig.json                ← extiende .nuxt/tsconfig.json
├── tsconfig.test.json           ← standalone para Vitest
├── vitest.config.ts
├── app/                         ← srcDir (Nuxt 4)
│   ├── app.vue                  ← <NuxtLayout><NuxtPage/>
│   ├── assets/css/tailwind.css  ← reset mobile (anti-zoom iOS)
│   ├── components/
│   ├── composables/
│   │   └── api/                 ← SigningApi mock/real + types + fixtures loader
│   ├── layouts/
│   │   └── default.vue          ← layout mobile-first, sin sidebar
│   ├── middleware/              ← session.global.ts se anade en F3
│   ├── pages/
│   ├── plugins/
│   ├── stores/
│   └── locales/
│       ├── es.json
│       └── en.json
├── server/                      ← endpoints Nitro si los hay
├── public/                      ← assets estaticos
├── types/                       ← d.ts globales (runtime-config, etc.)
└── tests/
    ├── fixtures/signing-session/  ← JSONs + sample-contract.pdf
    └── unit/
```

## Convenciones de codigo

- **`<script setup lang="ts">`** por defecto.
- **Componentes** en PascalCase multi-palabra.
- **Composables** con prefijo `use*`.
- **Sin `any`** salvo justificacion.
- **i18n**: todas las cadenas via `t('key')`. Paridad entre `es.json` y `en.json`.
- **Mobile-first**: los estilos base son para movil, las variantes `md:`/`lg:` anaden refinamientos para tablet/desktop. No al reves.
- **Touch events** primero; mouse events como fallback.
- **Rendimiento**: lazy-load de paginas del PDF, evitar cargar bundles pesados en la ruta inicial.
- **Accesibilidad**: WCAG AA. La experiencia de firma debe tener fallback textual (aceptacion por checkbox) para lectores de pantalla donde el canvas no sea viable.
- **Commits**: convenciones en `../f5sign-docs/Planning/AGENT-RUNBOOK.md` § 5.

## Ubicacion de specs relevantes

- **Arquitectura Frontend**: `../f5sign-docs/Arquitectura/Arquitectura Frontend.md` § 5 (Signer: rutas, componentes, flujo), § 8 (i18n), § 9 (entornos).
- **Firma PAdES y criptografia**: `../f5sign-docs/Arquitectura/Pilares/5. Firma Digital y Criptografía.md`.
- **Casos de uso de firma**: `../f5sign-docs/Casos de Uso/`.
- **Planning por task**: `../f5sign-docs/Planning/F*/EP*/S*/T*.md`.

`f5sign-docs` es solo lectura desde aqui. Solo se escribe en `Planning/` para cerrar `Seguimiento` (ver AGENT-RUNBOOK).

## Reglas especificas del repo

1. **Privacidad — CRITICO**: no loggear datos biometricos (trazos [x,y,t,p] del canvas), ni contenido del documento, ni el `access_token` del enlace. Ningun `console.log` de datos sensibles en produccion.
2. **El veredicto de sesion se ENRUTA, nunca se pinta en un rincon — CRITICO.** El
   middleware global corta en la primera linea de cualquier sub-ruta
   (`if (!isIndexRoute) return`, para no reentrar en SSR), asi que en `/view`, `/sign`,
   `/review`, `/decline` y `/click-sign` **nadie revalida nada**: se pintan enteras desde
   el store persistido, que puede ser de una sesion muerta. Toda pantalla de ceremonia
   debe usar `useSessionVerdict`, y valen estas tres reglas:
   - **Comprobar contra el backend, no contra el store.** El caso que muerde no es el
     store vacio, es el store POBLADO y rancio: ahi `session.session` existe y no dice
     nada.
   - **Ante un 401, `clear()` antes de rebotar.** El middleware tiene una rama de
     reutilizacion (`session.session !== null && !error`) que se salta el arranque y solo
     recalcula el destino; con el store rancio devuelve a la misma pantalla y se entra en
     bucle. Medido: cinco rebotes sin moverse.
   - **Nunca confinar el fallo dentro de un componente.** Un 401 mostrado como tarjeta
     dentro del visor deja la ceremonia viva alrededor — rieles, campos y boton de
     firmar—, y un firmante puede recorrerla entera y **creer que firmo**. Paso de
     verdad con un usuario, en `/view` y en `/sign`.
3. **No regenerar `pnpm-lock.yaml`** sin peticion explicita.
4. **Compatibilidad movil**: testear siempre en **Safari iOS** y Chrome Android antes de cerrar una task con cambios de UI. Chrome DevTools mobile no sustituye al dispositivo real.
5. **Rendimiento como requisito, no optimizacion posterior**: lazy-load, code-splitting, sin dependencias innecesarias. Presupuesto objetivo: bundle inicial < 200KB gzipped.
6. **Accesibilidad con fallback textual**: todo paso que requiera canvas o gestos complejos debe tener un equivalente por teclado o boton.
7. **Runtime config**: mismas reglas que dashboard (`NUXT_PUBLIC_*`, nada de secretos). `apiMode` por defecto es `'real'` para que un deploy sin override no sirva fixtures de mock.
8. **White-label (Dedicated)**: el branding se resuelve por `Host` header en middleware (F3). El skeleton deja estructura lista pero no implementa logica.
9. **No commitees `.env`.** Solo `.env.example`.
10. **Dos dominios simbolicamente distintos** (`sign.f5sign.com` y `firma.<tenant>.com`) apuntan a la misma app con middleware de branding; no duplicar codigo.
