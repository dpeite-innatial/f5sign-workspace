# Templates de formato para Planning

Estos templates definen el formato EXACTO de cada archivo en la estructura de Planning. Usa estos templates tal cual, reemplazando los placeholders en `{curly_braces}`.

## Convenciones de naming para archivos y carpetas

- Carpetas de fase: `F{n}-{Nombre-Kebab}/` — ej: `F0-Infraestructura/`, `F2-Core-Envelope/`
- Carpetas de epic: `EP{xx}-{Nombre-Kebab}/` — ej: `EP09-Envelope-CRUD/`
- Carpetas de story: `S{xx}.{y}-{Nombre-Kebab}/` — ej: `S09.1-Crear-Sobre-Draft/`
- Archivos de task: `T{xx}.{y}.{z}-{Nombre-Kebab}.md` — ej: `T09.1.1-Entity-Envelope.md`
- Los README.md van dentro de cada carpeta (fase, epic, story)
- Nombres en español sin acentos: "Autenticacion" no "Autenticación", "Creacion" no "Creación"
- Kebab-case para las palabras: "Docker-y-Entorno", no "Docker_y_Entorno"

---

## Template 1: `Planning/README.md` (Indice maestro)

```markdown
# InnaSign — Planning MVP

> Generado: {fecha} | Scope: MVP (~83 funcionalidades)
> Equipo: 2 devs fullstack | Stack: PHP 8.4/Symfony 7.4 + Vue 3/Nuxt 3 + PostgreSQL 16 + RabbitMQ + Redis + EU DSS v6.4

## Fases

| Fase | Nombre | Epics | Stories | Story Points | Estado |
|------|--------|-------|---------|-------------|--------|
| F0 | Infraestructura y Esqueleto | {n} | {n} | {n} | pendiente |
| F1 | Auth, Tenancy y API Base | {n} | {n} | {n} | pendiente |
| F2 | Core Envelope | {n} | {n} | {n} | pendiente |
| F3 | Signer Workspace | {n} | {n} | {n} | pendiente |
| F4 | Sellado y Cierre | {n} | {n} | {n} | pendiente |
| F5 | Dashboard y Polish | {n} | {n} | {n} | pendiente |
| **Total** | | **{n}** | **{n}** | **{n}** | |

## Dependencias entre fases

F0 --> F1 --> F2 --> F3 --> F4 --> F5

Notas:
- F2 (parcial: EP09 + EP10) es necesario antes de F3 (Signer necesita envelopes)
- F3 y F4 tienen dependencia bidireccional: el sellado (F4) cierra el ciclo de firma (F3)
- Dentro de cada fase, los epics pueden ejecutarse parcialmente en paralelo (ver README de cada fase)

## Indice de Epics

### F0 — Infraestructura y Esqueleto
- [EP01 — Docker y Entorno](F0-Infraestructura/EP01-Docker-y-Entorno/)
- [EP02 — PostgreSQL Schema](F0-Infraestructura/EP02-PostgreSQL-Schema/)
- [EP03 — Mensajeria y Cache](F0-Infraestructura/EP03-Mensajeria-Cache/)
- [EP04 — EU DSS y Almacenamiento](F0-Infraestructura/EP04-EU-DSS-Almacenamiento/)

### F1 — Auth, Tenancy y API Base
- [EP05 — Modelo de Datos Core](F1-Auth-Tenancy/EP05-Modelo-Datos-Core/)
- [EP06 — Autenticacion Dashboard](F1-Auth-Tenancy/EP06-Autenticacion-Dashboard/)
- [EP07 — Multi-tenancy y RLS](F1-Auth-Tenancy/EP07-Multi-tenancy-RLS/)
- [EP08 — API Base y Convenciones](F1-Auth-Tenancy/EP08-API-Base/)

### F2 — Core Envelope
- [EP09 — Envelope CRUD](F2-Core-Envelope/EP09-Envelope-CRUD/)
- [EP10 — Document Upload](F2-Core-Envelope/EP10-Document-Upload/)
- [EP11 — Recipients y Workflow](F2-Core-Envelope/EP11-Recipients-Workflow/)
- [EP12 — Posicionamiento de Campos](F2-Core-Envelope/EP12-Posicionamiento-Campos/)

### F3 — Signer Workspace
- [EP13 — Sesion del Firmante](F3-Signer-Workspace/EP13-Sesion-Firmante/)
- [EP14 — Autenticacion Firmante](F3-Signer-Workspace/EP14-Autenticacion-Firmante/)
- [EP15 — Captura de Firma](F3-Signer-Workspace/EP15-Captura-Firma/)
- [EP16 — Evidencias](F3-Signer-Workspace/EP16-Evidencias/)

### F4 — Sellado y Cierre
- [EP17 — Sellado PAdES](F4-Sellado-Cierre/EP17-Sellado-PAdES/)
- [EP18 — Audit Trail](F4-Sellado-Cierre/EP18-Audit-Trail/)
- [EP19 — Notificaciones Core](F4-Sellado-Cierre/EP19-Notificaciones-Core/)
- [EP20 — Workers y Colas](F4-Sellado-Cierre/EP20-Workers-Colas/)

### F5 — Dashboard y Polish
- [EP21 — Dashboard Home y Listados](F5-Dashboard-Polish/EP21-Dashboard-Home-Listados/)
- [EP22 — Templates Contacts Groups](F5-Dashboard-Polish/EP22-Templates-Contacts-Groups/)
- [EP23 — Webhooks y Developer Hub](F5-Dashboard-Polish/EP23-Webhooks-Developer-Hub/)
- [EP24 — SDK Embebido](F5-Dashboard-Polish/EP24-SDK-Embebido/)
- [EP25 — White-Label Settings Legal](F5-Dashboard-Polish/EP25-White-Label-Settings-Legal/)

## Convenciones

- **IDs:** F{n} (fase), EP{xx} (epic), S{xx}.{y} (story), T{xx}.{y}.{z} (task)
- **Story Points:** Fibonacci (1, 2, 3, 5, 8, 13)
- **Estado:** pendiente | en_progreso | completado | bloqueado
- **Dependencias:** cada item lista de que depende y a que bloquea
- **Paths de codigo:** siguen `Arquitectura/Patrones de Codigo y Convenciones.md`
  - Domain: `src/{Module}/Domain/{Entity,ValueObject,Event,Exception,Repository,Service,PublicApi}/`
  - Application: `src/{Module}/Application/{Command/{UseCase}/,Query/DTO/,EventSubscriber/}/`
  - Infrastructure: `src/{Module}/Infrastructure/{Persistence/Mapping/,Http/Controller/}/`
  - Frontend Dashboard: `apps/dashboard/`
  - Frontend Signer: `apps/signer/`
  - Tests Unit: `tests/Unit/{Module}/Domain/`
  - Tests Integration: `tests/Integration/{Module}/Application/`
  - Tests E2E: `tests/E2E/{Module}/Infrastructure/Http/`
```

---

## Template 2: `F{n}-Nombre/README.md` (Fase)

```markdown
# F{n} — {Nombre de la Fase}

> **Story Points totales:** {total} | **Stories:** {count} | **Epics:** {count}
> **Depende de:** F{n-1} (o "ninguna" para F0)
> **Desbloquea:** F{n+1}

## Seguimiento

| Campo | Valor |
|-------|-------|
| Estado | pendiente |
| Progreso | 0/{n} epics completados |
| Inicio | — |
| Fin | — |

## Objetivo
{2-3 frases explicando por que esta fase existe y que se consigue al completarla}

## Epics

| ID | Nombre | Stories | Pts | Depende de | Estado |
|----|--------|---------|-----|-----------|--------|
| EP{xx} | {nombre} | {n} | {pts} | {deps o "—"} | pendiente |

## Dependencias entre epics
{Descripcion textual: que epics pueden hacerse en paralelo, cuales son secuenciales}

## Riesgos y notas
- {Dependencias externas, decisiones pendientes, riesgos}
```

---

## Template 3: `EP{xx}-Nombre/README.md` (Epic)

```markdown
# EP{xx} — {Nombre del Epic}

> **Fase:** F{n} | **Story Points:** {total} | **Stories:** {count}
> **Depende de:** EP{yy}, EP{zz} (o "ninguno")
> **Bloquea:** EP{aa}, EP{bb}
> **Bounded Context:** {nombre del BC segun Mapa de Modulos}

## Seguimiento

| Campo | Valor |
|-------|-------|
| Estado | pendiente |
| Progreso | 0/{n} stories completadas |
| Inicio | — |
| Fin | — |
| Notas | — |

## Objetivo
{2-3 frases explicando que se consigue al completar este epic}

## Stories

| ID | Nombre | Pts | Tasks | Depende de | Asignado | Estado |
|----|--------|-----|-------|-----------|----------|--------|
| S{xx}.{y} | {nombre} | {pts} | {n} | {deps o "—"} | — | pendiente |

## Funcionalidades MVP cubiertas
{Lista de funcionalidades del Checklist Funcionalidades.md que este epic implementa.
Copiar el texto EXACTO del checklist.}
- [ ] {Funcionalidad 1}
- [ ] {Funcionalidad 2}

## Referencias
- [{Documento de spec}]({link relativo al .md desde la carpeta del epic})
- [{Otro documento}]({link relativo})
```

---

## Template 4: `S{xx}.{y}-Nombre/README.md` (Story)

```markdown
# S{xx}.{y} — {Nombre de la Story}

> **Epic:** EP{xx} | **Fase:** F{n} | **Story Points:** {total de la story}
> **Depende de:** S{xx}.{z}, S{yy}.{w} (o "ninguna")
> **Bloquea:** S{xx}.{z+1}, S{aa}.{b} (o "ninguna")

## Seguimiento

| Campo | Valor |
|-------|-------|
| Estado | pendiente |
| Prioridad | media |
| Asignado | — |
| Inicio | — |
| Fin | — |
| Progreso | 0/{n} tasks completadas |
| Bloqueantes | — |
| PR/Branch | — |
| Notas | — |

## User Story
**Como** {actor — ej: "remitente autenticado", "firmante", "sistema"}
**Quiero** {accion concreta}
**Para** {beneficio de negocio}

## Contexto funcional
{PENDIENTE — sera rellenado por /planning-detail}

## Criterios de aceptacion
{PENDIENTE — sera rellenado por /planning-detail}

## Tasks

| ID | Nombre | Pts | Tipo | Repo | Asignado | Estado |
|----|--------|-----|------|------|----------|--------|
| T{xx}.{y}.1 | {nombre} | {pts} | Backend | f5sign-backend | — | pendiente |
| T{xx}.{y}.2 | {nombre} | {pts} | Backend | f5sign-backend | — | pendiente |
| T{xx}.{y}.3 | {nombre} | {pts} | Frontend | f5sign-dashboard | — | pendiente |

## Referencias
- [{Spec principal}]({link relativo})
- [{ERD}]({link relativo}) — seccion {x}
```

---

## Template 5: `T{xx}.{y}.{z}-Nombre.md` (Task)

```markdown
# T{xx}.{y}.{z} — {Nombre de la Task}

> **Story:** S{xx}.{y} | **Epic:** EP{xx} | **Fase:** F{n} | **Story Points:** {pts}
> **Depende de:** T{xx}.{y}.{z-1} (o "ninguna")
> **Tipo:** Backend | Frontend | Integracion | Infraestructura | Diseno
> **Repo:** f5sign-backend | f5sign-dashboard | f5sign-signer | f5sign-infra | f5sign-docs
> **Complejidad:** baja | media | alta
> **Tags:** {csv: db, api, signing, crypto, rls, state-machine, worker, ui, migration, event, ...}

## Seguimiento

| Campo | Valor |
|-------|-------|
| Estado | pendiente |
| Prioridad | media |
| Asignado | — |
| Inicio | — |
| Fin | — |
| Bloqueantes | — |
| PR/Branch | — |
| Commit | — |
| Notas | — |

## Descripcion
{1-2 frases describiendo que hay que hacer en esta task}

## Contexto requerido
{PENDIENTE — sera rellenado por /planning-detail}

## Archivos a crear/modificar
{PENDIENTE — sera rellenado por /planning-detail}

## Detalle tecnico
{PENDIENTE — sera rellenado por /planning-detail}

## Tests
{PENDIENTE — sera rellenado por /planning-detail}
```

---

## Patron estandar de descomposicion de tasks por story

Cada story que involucre una feature end-to-end se descompone en estas tasks, en este orden:

### Para una story de Backend + Frontend:

| # | Nombre patron | Tipo | Que incluye | Pts tipicos |
|---|--------------|------|-------------|-------------|
| 1 | Entity + Value Objects | Backend | Entidad, VOs, Enums, Domain Events, mapping XML, tests unitarios | 2-3 |
| 2 | Repository + Migracion | Backend | Interface repo, impl Doctrine, migracion SQL, RLS policy, tests integracion | 2-3 |
| 3 | Command + Handler | Backend | Command DTO, Handler con logica, EventSubscribers, tests integracion | 2-5 |
| 4 | Controller + API | Backend | Controller, request validation, response DTO, error handling, tests E2E | 2-3 |
| 5 | Frontend: Store + Pagina | Frontend | Pinia store, API composable, pagina/componente, route | 2-5 |

### Para una story solo Backend (ej: workers, crons):

| # | Nombre patron | Tipo | Pts tipicos |
|---|--------------|------|-------------|
| 1 | Message DTO + Handler | Backend | 2-3 |
| 2 | Worker config + routing | Infraestructura | 1-2 |
| 3 | Tests integracion | Backend | 2-3 |

### Para una story solo Frontend (ej: UI components):

| # | Nombre patron | Tipo | Pts tipicos |
|---|--------------|------|-------------|
| 1 | Componentes | Frontend | 2-5 |
| 2 | Store + API | Frontend | 2-3 |
| 3 | Pagina + Routing | Frontend | 1-2 |

### Para una story de Infraestructura (ej: Docker, DB setup):

| # | Nombre patron | Tipo | Pts tipicos |
|---|--------------|------|-------------|
| 1 | Configuracion | Infraestructura | 2-3 |
| 2 | Verificacion + Tests | Infraestructura | 1-2 |

## Calibracion de story points

| Puntos | Ejemplo concreto | Complejidad |
|--------|-----------------|-------------|
| 1 | Crear un Value Object simple (Email, Uuid) con 2-3 tests | Trivial |
| 2 | Crear una Entity con 5-8 propiedades y mapping XML | Simple |
| 3 | Crear un Command + Handler con 1-2 reglas de negocio | Moderado |
| 5 | Implementar un controller con validacion, paginacion y 5+ tests | Complejo |
| 8 | Motor de workflow con routing secuencial/paralelo/mixto | Muy complejo |
| 13 | Integracion EU DSS completa (HTTP client, retry, error handling, mock) | Excepcional |

## Campos de seguimiento

Todos los niveles (fase, epic, story, task) tienen una seccion "Seguimiento" con campos editables manualmente. Los campos varian por nivel:

### Estados posibles

| Estado | Significado | Cuando se usa |
|--------|------------|---------------|
| `pendiente` | No se ha empezado | Estado inicial por defecto |
| `en_progreso` | Alguien esta trabajando en ello | Se cambia al empezar |
| `completado` | Cumple su Definition of Done | Se cambia al terminar |
| `bloqueado` | No puede avanzar por una dependencia externa | Se cambia cuando hay un bloqueante |

### Prioridades

| Prioridad | Cuando |
|-----------|--------|
| `alta` | Bloquea a otras stories/tasks o es critico para el MVP |
| `media` | Prioridad normal, se hace en orden |
| `baja` | Se puede postponer si hay carga |

### Campos por nivel

| Campo | Fase | Epic | Story | Task |
|-------|:----:|:----:|:-----:|:----:|
| Estado | Si | Si | Si | Si |
| Progreso (x/n completados) | Si | Si | Si | — |
| Prioridad | — | — | Si | Si |
| Asignado | — | — | Si | Si |
| Inicio (fecha) | Si | Si | Si | Si |
| Fin (fecha) | Si | Si | Si | Si |
| Bloqueantes | — | — | Si | Si |
| PR/Branch | — | — | Si | Si |
| Commit | — | — | — | Si |
| Notas | — | Si | Si | Si |

### Como actualizar el seguimiento

1. Al empezar una task: cambiar Estado a `en_progreso`, poner fecha de Inicio, poner Asignado
2. Al terminar una task: cambiar Estado a `completado`, poner fecha de Fin, poner Commit
3. Al completar una task, actualizar el Progreso de la story padre (ej: "3/5 tasks completadas")
4. Al completar todas las tasks de una story, verificar el DoD de Story y cambiar Estado a `completado`
5. Al completar todas las stories de un epic, cambiar Estado del epic a `completado`
6. Al completar todos los epics de una fase, ejecutar smoke tests y cambiar Estado de la fase a `completado`

## Asignacion de Repo a cada task

El workspace `f5sign/` agrupa cinco repos independientes. Cada task se ejecuta en **exactamente uno** y esto debe reflejarse en el campo `Repo:` del header y en la columna `Repo` de la tabla de tasks del story README.

### Valores permitidos

| Valor | Contenido |
|-------|-----------|
| `f5sign-backend` | API Symfony 7.4 + PHP 8.4, workers, migraciones, tests backend |
| `f5sign-dashboard` | Frontend Nuxt 3 del panel de administracion |
| `f5sign-signer` | Frontend Nuxt 3 de la experiencia de firma del firmante |
| `f5sign-infra` | docker-compose, Makefile, Dockerfiles, scripts de orquestacion local y de produccion, configuracion CI/CD |
| `f5sign-docs` | Specs, planning, ADRs, wireframes/diseños |

### Reglas de mapeo por Tipo y contexto

| Tipo | Regla de asignacion |
|------|---------------------|
| `Backend` | Siempre `f5sign-backend` |
| `Infraestructura` | Siempre `f5sign-infra` (Docker, nginx, PostgreSQL/RabbitMQ/Redis/MinIO/EU DSS, CI) |
| `Integracion` | `f5sign-backend` salvo que la task sea puramente frontend (consumo desde cliente) |
| `Frontend` | `f5sign-signer` si la story esta en **F3-Signer-Workspace** o su nombre contiene "Signer", "Firmante", "Captura" o "Firma-UI". En cualquier otro caso `f5sign-dashboard` |
| `Diseno` | `f5sign-docs` (los wireframes y diseños viven en docs) |

### Regla de exclusividad

Una task **no puede** tocar mas de un repo. Si una task necesita cambios en backend y frontend, partirla en dos tasks separadas durante el scaffold: una con `Repo: f5sign-backend` y otra con `Repo: f5sign-dashboard` (o signer), coordinadas via `Depende de:`.

### Campo obligatorio

El campo `Repo:` es **obligatorio** en todos los task headers y en la columna `Repo` de la tabla de tasks del story README. Un scaffold sin este campo se considera incompleto.

