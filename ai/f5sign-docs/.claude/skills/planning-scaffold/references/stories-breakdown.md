# Breakdown exhaustivo de Stories y Tasks por Epic

Este documento lista TODAS las stories y tasks que debe crear `/planning-scaffold`. El agente NO debe inventar stories ni tasks adicionales, ni omitir ninguna de las listadas aqui.

Cada story lista sus tasks con el patron de descomposicion estandar (ver templates.md). Los story points son estimaciones iniciales.

---

## F0 — Infraestructura y Esqueleto

### EP01 — Docker y Entorno de Desarrollo

**S01.1 — Docker Compose para Desarrollo** (5 pts)
- T01.1.1 — Fichero docker-compose.yml (2 pts, Infraestructura)
  - Servicios: php-fpm, nginx, postgresql, rabbitmq, redis, minio, eu-dss
- T01.1.2 — Ficheros de entorno y Makefile (2 pts, Infraestructura)
  - .env.example, .env.local, Makefile con comandos dev
- T01.1.3 — Healthchecks y networking (1 pt, Infraestructura)

**S01.2 — Proyecto Symfony Backend** (5 pts)
- T01.2.1 — Symfony skeleton y dependencias (2 pts, Backend)
  - symfony/skeleton, doctrine, messenger, validator, security
- T01.2.2 — Estructura de carpetas por modulo (2 pts, Backend)
  - src/Shared/, src/Envelope/, etc. con carpetas Domain/Application/Infrastructure vacias
- T01.2.3 — Configuracion de entornos saas/dedicated (1 pt, Backend)
  - .env.saas, .env.dedicated, config/packages/{saas,dedicated}/

**S01.3 — Monorepo Frontend Nuxt** (5 pts)
- T01.3.1 — pnpm workspace con dos apps (2 pts, Frontend)
  - apps/dashboard/, apps/signer/, packages/shared/
- T01.3.2 — Configuracion base Nuxt (2 pts, Frontend)
  - nuxt.config.ts, tailwind, typescript, vue-i18n, pinia
- T01.3.3 — Ficheros i18n base (1 pt, Frontend)
  - locales/es.json, locales/en.json con estructura base

### EP02 — PostgreSQL: Schema Base y Enums

**S02.1 — Tipos ENUM de PostgreSQL** (3 pts)
- T02.1.1 — Migracion con todos los ENUMs MVP (2 pts, Backend)
  - envelope_status, recipient_role, recipient_status, delivery_method, auth_method, signature_level, pades_profile, field_type, event_type, usage_metric, plan_type, tenant_status
- T02.1.2 — PHP Backed Enums correspondientes (1 pt, Backend)
  - Un enum PHP por cada ENUM de PostgreSQL en src/Shared/Domain/ValueObject/

**S02.2 — Tablas Base de Tenancy** (5 pts)
- T02.2.1 — Migracion: tablas tenant y workspace (2 pts, Backend)
  - CREATE TABLE tenant, workspace con todos los campos del ERD
- T02.2.2 — Entidades Doctrine: Tenant y Workspace (2 pts, Backend)
  - Entities + VOs + mappings XML
- T02.2.3 — Funcion helper RLS y politica base (1 pt, Backend)
  - current_tenant_id(), CREATE POLICY en tenant y workspace

### EP03 — Mensajeria y Cache

**S03.1 — RabbitMQ y Symfony Messenger** (5 pts)
- T03.1.1 — Configuracion RabbitMQ (2 pts, Infraestructura)
  - Exchanges, queues (pdf.sign, pdf.audit-trail, webhook.deliver, notification.send), delayed_message_exchange
- T03.1.2 — Transports de Symfony Messenger (2 pts, Backend)
  - messenger.yaml: sync, async, async_priority_high, routing
- T03.1.3 — Middleware del Command Bus (1 pt, Backend)
  - SetTenantIdMiddleware, LogCommandMiddleware, validation, doctrine_transaction

**S03.2 — Redis: Cache, Locks e Idempotencia** (3 pts)
- T03.2.1 — Configuracion Redis (1 pt, Infraestructura)
  - framework.yaml: cache, lock, rate_limiter
- T03.2.2 — Servicio de idempotencia (2 pts, Backend)
  - IdempotencyMiddleware, store en Redis con TTL 24h

### EP04 — EU DSS y Almacenamiento

**S04.1 — Contenedor EU DSS v6.4** (3 pts)
- T04.1.1 — Docker config EU DSS (2 pts, Infraestructura)
  - Dockerfile o imagen oficial, configuracion de modulos (pades, tsl, timestamp)
- T04.1.2 — Trusted Lists y TSA mock (1 pt, Infraestructura)
  - Config TL v6, TSA mock para desarrollo

**S04.2 — Cliente HTTP para EU DSS** (5 pts)
- T04.2.1 — DssClientInterface y adaptador HTTP (3 pts, Backend)
  - Interface en Cryptography/Domain/, impl en Infrastructure/, endpoints: getDataToSign, signDocument
- T04.2.2 — Tests con mock de EU DSS (2 pts, Backend)

**S04.3 — Almacenamiento S3/MinIO** (5 pts)
- T04.3.1 — Configuracion MinIO y buckets (1 pt, Infraestructura)
  - Buckets: innasign-originals, innasign-signed, innasign-audit-trails, innasign-biometrics, innasign-temp
- T04.3.2 — StorageInterface y adaptador S3 (3 pts, Backend)
  - Interface en Storage/Domain/, impl en Infrastructure/ con Flysystem o AWS SDK
- T04.3.3 — Tests de almacenamiento (1 pt, Backend)

### EP26 — Testing Infrastructure

**S26.1 — PHPUnit y Test Database** (5 pts)
- T26.1.1 — Configuracion PHPUnit y bootstrap (2 pts, Backend)
  - phpunit.xml.dist, autoload-dev, kernel de test, variables de entorno
- T26.1.2 — Base de datos de test PostgreSQL en Docker (2 pts, Infraestructura)
  - Servicio postgresql-test en docker-compose, migraciones automaticas en test
- T26.1.3 — AbstractIntegrationTestCase con tenant fixture y RLS (1 pt, Backend)
  - Base class con setUp que crea tenant/workspace de test y configura current_tenant_id()

**S26.2 — Fixtures y Factories** (3 pts)
- T26.2.1 — Factory pattern para entidades core (Tenant, User, Envelope, Recipient, Document) (2 pts, Backend)
  - Clases Factory con metodos create/build y estados predefinidos
- T26.2.2 — Data fixtures para desarrollo local (1 pt, Backend)
  - Comando bin/console app:fixtures:load con datos realistas de demo

**S26.3 — Frontend Testing (Vitest + Playwright)** (3 pts)
- T26.3.1 — Configuracion Vitest + Vue Test Utils para unit/component tests (2 pts, Frontend)
  - vitest.config.ts, @vue/test-utils, mocks de Pinia y vue-router
- T26.3.2 — Configuracion Playwright para E2E basico (1 pt, Frontend)
  - playwright.config.ts, proyecto dashboard + signer, scripts npm

### EP27 — Monitoring y Observabilidad

**S27.1 — Error Tracking (Sentry)** (3 pts)
- T27.1.1 — Integracion Sentry PHP (backend) + JS (frontend) (2 pts, Infraestructura)
  - sentry/sentry-symfony, @sentry/vue, DSN por entorno, source maps
- T27.1.2 — Contexto de tenant y user en Sentry scopes (1 pt, Backend)
  - EventSubscriber que anade tenant_id, user_id, workspace_id a cada evento

**S27.2 — Health Checks y Logging** (3 pts)
- T27.2.1 — Endpoint GET /healthz con checks de dependencias (2 pts, Backend)
  - Checks: PostgreSQL, Redis, RabbitMQ, MinIO, EU DSS. Response JSON con status por servicio
- T27.2.2 — Logging estructurado JSON con Monolog (1 pt, Backend)
  - Configuracion monolog.yaml: JSON formatter, canales por bounded context, correlation_id

---

## F1 — Auth, Tenancy y API Base

### EP05 — Modelo de Datos Core

**S05.1 — Tablas de Usuario y Autenticacion** (5 pts)
- T05.1.1 — Migracion: tablas user, refresh_token, user_invitation (2 pts, Backend)
- T05.1.2 — Entidades User, RefreshToken (2 pts, Backend)
- T05.1.3 — RLS policies para user y refresh_token (1 pt, Backend)

**S05.2 — Tablas de Envelope y Documentos** (5 pts)
- T05.2.1 — Migracion: tablas envelope, document, document_upload (2 pts, Backend)
- T05.2.2 — Entidades Envelope, Document (2 pts, Backend)
- T05.2.3 — RLS policies e indices (1 pt, Backend)

**S05.3 — Tablas de Recipient, Field y Firma** (5 pts)
- T05.3.1 — Migracion: tablas recipient, field, signing_session, signature_execution (2 pts, Backend)
- T05.3.2 — Entidades Recipient, Field, SigningSession, SignatureExecution (2 pts, Backend)
- T05.3.3 — RLS policies e indices (1 pt, Backend)

**S05.4 — Tablas Auxiliares MVP** (5 pts)
- T05.4.1 — Migracion: tablas template, contact, signing_group, signing_group_member (2 pts, Backend)
- T05.4.2 — Migracion: tablas audit_event, evidence_packet, notification, api_key, webhook_subscription (2 pts, Backend)
- T05.4.3 — Migracion: tablas share_link, legal_document, legal_acceptance, seal_config (1 pt, Backend)

### EP06 — Autenticacion y Usuarios Dashboard

**S06.1 — Login y JWT** (5 pts)
- T06.1.1 — Entity User con password hash (2 pts, Backend)
- T06.1.2 — LoginCommand + Handler + JWT generation (2 pts, Backend)
- T06.1.3 — Controller POST /v1/auth/login (1 pt, Backend)

**S06.2 — Refresh Token** (5 pts)
- T06.2.1 — Entity RefreshToken con rotacion (2 pts, Backend)
- T06.2.2 — RefreshTokenCommand + Handler (2 pts, Backend)
- T06.2.3 — Controller POST /v1/auth/refresh (1 pt, Backend)

**S06.3 — Verificacion de Email** (3 pts)
- T06.3.1 — VerifyEmailCommand + Handler + token 24h (2 pts, Backend)
- T06.3.2 — Controller POST /v1/auth/verify-email (1 pt, Backend)

**S06.4 — Recuperacion de Contrasena** (3 pts)
- T06.4.1 — ForgotPassword + ResetPassword commands (2 pts, Backend)
- T06.4.2 — Controllers POST /v1/auth/forgot-password y /reset-password (1 pt, Backend)

**S06.5 — Frontend: Login y Auth** (5 pts)
- T06.5.1 — useAuthStore (Pinia) con JWT y refresh (2 pts, Frontend)
- T06.5.2 — Paginas login, forgot-password, reset-password (2 pts, Frontend)
- T06.5.3 — Middleware auth.global.ts (1 pt, Frontend)

**S06.6 — Invitacion de Usuarios** (5 pts)
- T06.6.1 — InviteUserCommand + Handler (generar token 7 dias, asignar rol al workspace) (2 pts, Backend)
  - Validar: email no duplicado en tenant, max usuarios segun plan, enviar email de invitacion
- T06.6.2 — AcceptInvitationCommand + Handler (crear user, asociar a tenant/workspace) (2 pts, Backend)
  - Validar token, crear password, transicion invitation PENDING -> ACCEPTED
- T06.6.3 — Controllers POST /v1/users/invite, POST /v1/auth/accept-invitation (1 pt, Backend)

**S06.7 — Frontend: Gestion de Invitaciones** (3 pts)
- T06.7.1 — Pagina de gestion de usuarios con listado + invitaciones pendientes (2 pts, Frontend)
  - Tabla de usuarios, boton invitar, estado pending/accepted, reenviar invitacion
- T06.7.2 — Pagina publica de aceptacion de invitacion /auth/accept-invitation/:token (1 pt, Frontend)

### EP07 — Multi-tenancy y RLS

**S07.1 — Middleware de Tenant** (5 pts)
- T07.1.1 — TenantProviderInterface y JwtTenantProvider (2 pts, Backend)
- T07.1.2 — RlsTenantMiddleware HTTP (2 pts, Backend)
- T07.1.3 — SetTenantIdMiddleware para Command Bus (1 pt, Backend)

**S07.2 — Scoping por Workspace** (3 pts)
- T07.2.1 — WorkspaceScoper y filtros Doctrine (2 pts, Backend)
- T07.2.2 — Tests de aislamiento tenant y workspace (1 pt, Backend)

**S07.3 — Workspace CRUD** (5 pts)
- T07.3.1 — CreateWorkspaceCommand + UpdateWorkspaceCommand + Handlers (2 pts, Backend)
  - Validar limites por plan (Business: 5, Enterprise: ilimitados)
- T07.3.2 — DeleteWorkspaceCommand + Handler (solo si no tiene recursos asociados) (1 pt, Backend)
- T07.3.3 — Controllers CRUD /v1/workspaces (1 pt, Backend)
- T07.3.4 — AssignUserToWorkspaceCommand + Handler (asignar usuario con rol) (1 pt, Backend)

**S07.4 — Frontend: Workspace Switcher** (3 pts)
- T07.4.1 — Componente WorkspaceSwitcher en sidebar del Dashboard (2 pts, Frontend)
  - Dropdown con workspaces del usuario, persistir seleccion en localStorage
- T07.4.2 — Pagina de gestion de workspaces en Settings (1 pt, Frontend)

### EP08 — API Base y Convenciones

**S08.1 — Error Handling y Responses** (3 pts)
- T08.1.1 — ExceptionListener con RFC 7807 (2 pts, Backend)
- T08.1.2 — Response DTOs base y serializer config (1 pt, Backend)

**S08.2 — Paginacion, Filtros y Ordenacion** (3 pts)
- T08.2.1 — PaginationRequest, FilterRequest, SortRequest (2 pts, Backend)
- T08.2.2 — QueryBuilder helpers para pagination (1 pt, Backend)

**S08.3 — Rate Limiting** (2 pts)
- T08.3.1 — Configuracion Symfony RateLimiter por plan (1 pt, Backend)
- T08.3.2 — Headers X-RateLimit-* en responses (1 pt, Backend)

**S08.4 — Idempotencia y CORS** (2 pts)
- T08.4.1 — IdempotencyMiddleware con Redis (1 pt, Backend)
- T08.4.2 — CORS config para dashboard y signer (1 pt, Backend)

**S08.5 — Documentacion OpenAPI** (3 pts)
- T08.5.1 — Configuracion NelmioApiDocBundle + anotaciones OpenAPI en controllers (2 pts, Backend)
  - Schemas, ejemplos, codigos de error, autenticacion Bearer/API Key
- T08.5.2 — Swagger UI accesible en /api/doc (1 pt, Backend)

### EP28 — Localizacion i18n

**S28.1 — Backend i18n** (3 pts)
- T28.1.1 — Symfony Translation Component: catalogos YAML ES/EN (2 pts, Backend)
  - translations/messages.es.yaml, translations/messages.en.yaml, validators, emails
- T28.1.2 — Locale middleware: detectar de JWT user.locale o Accept-Language header (1 pt, Backend)

**S28.2 — Frontend i18n Avanzado** (5 pts)
- T28.2.1 — vue-i18n con lazy-loading de locales, pluralizacion e interpolacion (2 pts, Frontend)
  - Carga asincrona por ruta, fallback a ES, keys jerarquicas por modulo
- T28.2.2 — Formateo regional con Intl API (fechas, numeros, moneda) (1 pt, Frontend)
- T28.2.3 — Language selector en Dashboard (Perfil > Preferencias) y Signer Workspace (header) (2 pts, Frontend)

---

## F2 — Core de Firma: Envelope Lifecycle

### EP09 — Envelope CRUD

**S09.1 — Crear Sobre en DRAFT** (8 pts)
- T09.1.1 — Entity Envelope + Value Objects (EnvelopeStatus, WorkflowType, EnvelopeName) (2 pts, Backend)
- T09.1.2 — EnvelopeRepositoryInterface + DoctrineEnvelopeRepository (2 pts, Backend)
- T09.1.3 — CreateEnvelopeCommand + Handler con PlanEnforcement (2 pts, Backend)
- T09.1.4 — Controller POST /v1/envelopes + tests (1 pt, Backend)
- T09.1.5 — Frontend: integracion API crear sobre (1 pt, Frontend)

**S09.2 — Editar y Eliminar Borrador** (5 pts)
- T09.2.1 — UpdateEnvelopeCommand + Handler (solo DRAFT) (2 pts, Backend)
- T09.2.2 — DeleteEnvelopeCommand + Handler (solo DRAFT) (1 pt, Backend)
- T09.2.3 — Controllers PATCH y DELETE /v1/envelopes/{id} (1 pt, Backend)
- T09.2.4 — Frontend: edicion y borrado de borradores (1 pt, Frontend)

**S09.3 — Enviar Sobre** (8 pts)
- T09.3.1 — SendEnvelopeCommand + Handler con validaciones pre-envio (3 pts, Backend)
  - Validar: al menos 1 documento, al menos 1 recipient SIGNER, campos obligatorios posicionados
- T09.3.2 — Maquina de estados: transicion DRAFT -> SENT (2 pts, Backend)
- T09.3.3 — Domain Events: EnvelopeSent (trigger notificaciones, webhooks) (1 pt, Backend)
- T09.3.4 — Controller POST /v1/envelopes/{id}/send (1 pt, Backend)
- T09.3.5 — Frontend: boton enviar con confirmacion (1 pt, Frontend)

**S09.4 — Acciones en Vuelo** (8 pts)
- T09.4.1 — VoidEnvelopeCommand + Handler (anular) (2 pts, Backend)
- T09.4.2 — PauseEnvelopeCommand + Handler (pausar/reanudar) (2 pts, Backend)
- T09.4.3 — ExtendDeadlineCommand + Handler (ampliar plazo, max 90 dias) (1 pt, Backend)
- T09.4.4 — CorrectRecipientCommand + Handler (correccion en vuelo) (2 pts, Backend)
- T09.4.5 — Controllers para void, pause, extend, correct (1 pt, Backend)

### EP10 — Document Upload y Processing

**S10.1 — Subir Documentos PDF** (8 pts)
- T10.1.1 — Entity Document + DocumentUpload (2 pts, Backend)
- T10.1.2 — UploadDocumentCommand + Handler (validar PDF, max 25MB, max 5 docs) (3 pts, Backend)
- T10.1.3 — Controller PUT /v1/envelopes/{id}/documents/{docId}/upload (1 pt, Backend)
- T10.1.4 — Frontend: drag & drop upload con progress (2 pts, Frontend)

**S10.2 — Almacenamiento y Descarga** (5 pts)
- T10.2.1 — Subir a S3 bucket innasign-originals (2 pts, Backend)
- T10.2.2 — Endpoint de descarga GET /v1/envelopes/{id}/documents/{docId}/download (2 pts, Backend)
- T10.2.3 — Frontend: preview y descarga de documentos (1 pt, Frontend)

**S10.3 — Text Tags** (5 pts)
- T10.3.1 — Servicio de deteccion de Text Tags en PDF (3 pts, Backend)
  - Buscar patron {{Nombre_Rol}} en el texto del PDF, crear campos automaticamente
- T10.3.2 — Controller POST /v1/envelopes/{id}/documents/{docId}/detect-tags (1 pt, Backend)
- T10.3.3 — Frontend: indicador de tags detectados (1 pt, Frontend)

### EP11 — Recipients y Motor de Workflow

**S11.1 — CRUD de Recipients** (5 pts)
- T11.1.1 — Entity Recipient + Value Objects (RecipientRole, RecipientStatus, DeliveryMethod, AuthMethod) (2 pts, Backend)
- T11.1.2 — AddRecipientCommand + Handler (2 pts, Backend)
- T11.1.3 — Controllers para recipients (CRUD) (1 pt, Backend)

**S11.2 — Motor de Routing** (13 pts)
- T11.2.1 — WorkflowEngine: routing secuencial (3 pts, Backend)
  - Determinar siguiente step, activar recipients del step actual
- T11.2.2 — WorkflowEngine: routing paralelo (2 pts, Backend)
  - Activar todos los recipients del step simultaneamente
- T11.2.3 — WorkflowEngine: routing mixto (3 pts, Backend)
  - Combinar steps secuenciales con groups paralelos
- T11.2.4 — AdvanceWorkflowOnSignature EventSubscriber (3 pts, Backend)
  - Al completar un firmante, evaluar si el step esta completo, avanzar al siguiente
- T11.2.5 — Delayed Routing incondicional (2 pts, Backend)
  - Espera fija entre steps via delayed message en RabbitMQ

**S11.3 — Delegacion de Firma** (5 pts)
- T11.3.1 — DelegateSignatureCommand + Handler (3 pts, Backend)
  - Crear nuevo recipient, invalidar token anterior, notificar
- T11.3.2 — Controller POST /v1/envelopes/{id}/recipients/{recipientId}/delegate (1 pt, Backend)
- T11.3.3 — Frontend: flujo de delegacion en detalle de sobre (1 pt, Frontend)

**S11.4 — Signing Groups** (8 pts)
- T11.4.1 — Entities SigningGroup + SigningGroupMember (2 pts, Backend)
- T11.4.2 — CRUD Commands + Handlers (crear, editar, archivar, restaurar, eliminar) (3 pts, Backend)
- T11.4.3 — Logica de quorum (ANY/QUORUM/ALL, deteccion quorum imposible) (2 pts, Backend)
- T11.4.4 — Controllers CRUD /v1/signing-groups (1 pt, Backend)

**S11.5 — Expiracion y Recordatorios** (5 pts)
- T11.5.1 — Cron: envelope expiration check (cada 5 min) (2 pts, Backend)
- T11.5.2 — Cron: reminder automatico (segun reminder_frequency_days) (2 pts, Backend)
- T11.5.3 — Controller POST /v1/envelopes/{id}/remind (recordatorio manual) (1 pt, Backend)

### EP12 — Posicionamiento de Campos

**S12.1 — CRUD de Campos** (5 pts)
- T12.1.1 — Entity Field + Value Objects (FieldType, coordenadas, validaciones) (2 pts, Backend)
- T12.1.2 — AddFieldCommand + UpdateFieldCommand + Handlers (2 pts, Backend)
- T12.1.3 — Controllers CRUD /v1/envelopes/{id}/fields (1 pt, Backend)

**S12.2 — Editor Visual de Campos** (8 pts)
- T12.2.1 — Componente PdfViewer con pdfjs-dist (3 pts, Frontend)
- T12.2.2 — Componente FieldPositioner con drag & drop (3 pts, Frontend)
- T12.2.3 — Toolbar de tipos de campo y panel de propiedades (2 pts, Frontend)

**S12.3 — Wizard de Creacion de Sobre (5 pasos)** (8 pts)
- T12.3.1 — Componente EnvelopeWizard con navegacion de pasos (2 pts, Frontend)
- T12.3.2 — Paso 1: Documentos (upload) + Paso 2: Destinatarios (form) (2 pts, Frontend)
- T12.3.3 — Paso 3: Campos (editor visual) + Paso 4: Configuracion (2 pts, Frontend)
- T12.3.4 — Paso 5: Revisar y Confirmar + accion enviar (2 pts, Frontend)

---

## F3 — Signer Workspace y Evidencias

### EP13 — Sesion del Firmante

**S13.1 — Acceso por Token y Sesion** (8 pts)
- T13.1.1 — Entity SigningSession con estados (INITIATED -> AUTH_PENDING -> AUTH_PASSED -> SIGNING -> COMPLETED) (2 pts, Backend)
- T13.1.2 — InitiateSessionCommand + Handler (validar token, crear sesion) (2 pts, Backend)
- T13.1.3 — Controller GET /v1/signing/session (devuelve toda la info para renderizar) (2 pts, Backend)
- T13.1.4 — Frontend Signer: entry page /s/:token y middleware session (2 pts, Frontend)

**S13.2 — Visor de PDF y Navegacion Guiada** (8 pts)
- T13.2.1 — Componente PdfDocumentViewer para Signer (3 pts, Frontend)
- T13.2.2 — Componente InteractiveField (campos rellenables) (3 pts, Frontend)
- T13.2.3 — Navegacion guiada: boton "Siguiente Accion" que salta al siguiente campo obligatorio (2 pts, Frontend)

**S13.3 — Pantallas de Estado** (3 pts)
- T13.3.1 — Paginas: completado (/s/:token/done), rechazo (/s/:token/decline), expirado, error (2 pts, Frontend)
- T13.3.2 — DeclineEnvelopeCommand + Handler (motivo obligatorio) (1 pt, Backend)

**S13.4 — Re-autenticacion y TTL** (3 pts)
- T13.4.1 — Logica de re-auth: si TTL expirado, modal overlay sin perder contexto (2 pts, Backend)
- T13.4.2 — Frontend: modal de re-auth transparente (1 pt, Frontend)

### EP14 — Autenticacion del Firmante

**S14.1 — Direct Link (token only)** (2 pts)
- T14.1.1 — Validacion de token UUID v4 y transicion a AUTH_PASSED (2 pts, Backend)

**S14.2 — OTP por SMS** (5 pts)
- T14.2.1 — GenerateOtpCommand + Handler (6 digitos, TTL 10 min, max 3 intentos) (2 pts, Backend)
- T14.2.2 — VerifyOtpCommand + Handler (1 pt, Backend)
- T14.2.3 — SmsProviderInterface + TwilioAdapter (mock en dev) (1 pt, Backend)
- T14.2.4 — Frontend Signer: pantalla OTP con input y countdown (1 pt, Frontend)

**S14.3 — OTP por Email** (3 pts)
- T14.3.1 — Reutilizar GenerateOtp/VerifyOtp con canal EMAIL (1 pt, Backend)
- T14.3.2 — Template email OTP (1 pt, Backend)
- T14.3.3 — Frontend: misma pantalla OTP adaptada (1 pt, Frontend)

**S14.4 — Access Code** (3 pts)
- T14.4.1 — VerifyAccessCodeCommand + Handler (comparar con PIN/NIF almacenado) (2 pts, Backend)
- T14.4.2 — Frontend: pantalla de input de codigo secreto (1 pt, Frontend)

### EP15 — Captura de Firma y Biometria

**S15.1 — Canvas Biometrico** (8 pts)
- T15.1.1 — Componente SignatureCanvas con captura X/Y/T/P (3 pts, Frontend)
  - HTML5 Canvas, eventos touch y mouse, presion via PointerEvent.pressure
- T15.1.2 — Formato de datos biometricos segun ISO 39794-7 (2 pts, Frontend)
- T15.1.3 — Consentimiento biometrico RGPD Art 9.2.a (checkbox desmarcado por defecto) (1 pt, Frontend)
- T15.1.4 — Feedback visual: trazo en tiempo real, boton limpiar, boton rehacer (2 pts, Frontend)

**S15.2 — Firma Mecanografiada e Imagen** (5 pts)
- T15.2.1 — Componente TypedSignature: nombre en fuente cursiva, preview (2 pts, Frontend)
- T15.2.2 — Componente ImageSignature: upload de imagen de firma (2 pts, Frontend)
- T15.2.3 — Selector de modo de firma (tabs: Dibujar / Escribir / Imagen) (1 pt, Frontend)

**S15.3 — Vista de Reviewer** (3 pts)
- T15.3.1 — Pagina /s/:token/review: solo lectura + boton "He revisado" (2 pts, Frontend)
- T15.3.2 — MarkAsReviewedCommand + Handler (1 pt, Backend)

### EP16 — Evidencias y Completar Firma

**S16.1 — Captura de Evidencias** (5 pts)
- T16.1.1 — Composable useGeolocation: GPS activo + fallback Geo-IP (2 pts, Frontend)
- T16.1.2 — Composable useDeviceFingerprint: IP, User-Agent, screen resolution (2 pts, Frontend)
- T16.1.3 — Entity EvidencePacket con todos los campos (1 pt, Backend)

**S16.2 — Completar Sesion de Firma** (8 pts)
- T16.2.1 — CompleteSigningSessionCommand + Handler (3 pts, Backend)
  - Recibir firma + evidencias + campos, persistir, transicion sesion a COMPLETED
- T16.2.2 — Controller POST /v1/signing/session/complete (2 pts, Backend)
- T16.2.3 — EventSubscriber: al completar, evaluar workflow y disparar sellado si corresponde (2 pts, Backend)
- T16.2.4 — Frontend: flujo completo de firma -> envio -> pantalla completado (1 pt, Frontend)

---

## F4 — Sellado, Audit Trail y Notificaciones

### EP17 — Sellado PAdES con EU DSS

**S17.1 — Sellado de Sobre Completado** (13 pts)
- T17.1.1 — SealDocumentCommand + Handler: llamar EU DSS via HTTP (3 pts, Backend)
  - Flujo: getDataToSign -> signDocument con cert empresa -> verificar respuesta
- T17.1.2 — PAdES B-LT: embeber OCSP/CRL + timestamp TSA (3 pts, Backend)
- T17.1.3 — Almacenar PDF sellado en S3 bucket innasign-signed (1 pt, Backend)
- T17.1.4 — Transiciones de estado: READY_TO_SEAL -> SEALING -> COMPLETED o SEALING_FAILED (2 pts, Backend)
- T17.1.5 — Apariencia visual del sello en el PDF (2 pts, Backend)
- T17.1.6 — Retry: POST /v1/envelopes/{id}/retry-seal para SEALING_FAILED (2 pts, Backend)

**S17.2 — Sellado Directo (Seal-Only)** (8 pts)
- T17.2.1 — Endpoint POST /v1/seal (shortcut, multipart/form-data) (2 pts, Backend)
- T17.2.2 — Flujo Seal-Only via Envelope: DRAFT -> READY_TO_SEAL -> SEALING -> COMPLETED (3 pts, Backend)
- T17.2.3 — SealConfig por tenant: posicion, texto, fuente (2 pts, Backend)
- T17.2.4 — Frontend: pagina de sellado directo en Dashboard (1 pt, Frontend)

**S17.3 — Mock de Certificado y TSA** (3 pts)
- T17.3.1 — Certificado e-Seal de test (autofirmado) para desarrollo (1 pt, Infraestructura)
- T17.3.2 — TSA mock o TSA de test para desarrollo (1 pt, Infraestructura)
- T17.3.3 — Configuracion para intercambiar cert real (FNMT) cuando este disponible (1 pt, Backend)

### EP18 — Audit Trail

**S18.1 — Eventos de Auditoria** (8 pts)
- T18.1.1 — Entity AuditEvent con hash chain (SHA-256 del evento anterior) (3 pts, Backend)
- T18.1.2 — AuditEventSubscriber: escucha TODOS los domain events, crea AuditEvent (3 pts, Backend)
- T18.1.3 — Controller GET /v1/envelopes/{id}/audit-events (paginado) (1 pt, Backend)
- T18.1.4 — ~30 event types MVP (lista completa del Catalogo de Notificaciones) (1 pt, Backend)

**S18.2 — Generacion de Audit Trail PDF** (8 pts)
- T18.2.1 — Servicio de generacion PDF bilingue (ES + EN) con Twig + DOMPDF (5 pts, Backend)
  - Datos del sobre, firmantes, timeline de eventos, evidencias
- T18.2.2 — Worker: GenerateAuditTrailCommand en queue pdf.audit-trail (2 pts, Backend)
- T18.2.3 — Sellar Audit Trail PDF con certificado de empresa (1 pt, Backend)

### EP19 — Notificaciones Core

**S19.1 — Infraestructura de Notificaciones** (5 pts)
- T19.1.1 — Entity Notification + cola queue.notification.send (2 pts, Backend)
- T19.1.2 — EmailProviderInterface + SendGridAdapter (mock en dev) (2 pts, Backend)
- T19.1.3 — Plantillas email Twig con variables y soporte ES/EN (1 pt, Backend)

**S19.2 — Notificaciones del Flujo de Firma** (8 pts)
- T19.2.1 — SIGN-001: Invitacion a firmar (trigger: EnvelopeSent) (1 pt, Backend)
- T19.2.2 — SIGN-002/003: Recordatorio auto y manual (1 pt, Backend)
- T19.2.3 — SIGN-004: Aviso expiracion proxima (1 pt, Backend)
- T19.2.4 — SIGN-005: Sobre completado (adjuntar PDF + Audit Trail) (2 pts, Backend)
- T19.2.5 — SIGN-006/007/008: Cancelado, expirado, rechazado (1 pt, Backend)
- T19.2.6 — SIGN-009/010/011: Delegacion, siguiente step, correccion (2 pts, Backend)

**S19.3 — Notificaciones OTP** (3 pts)
- T19.3.1 — Envio OTP por SMS via Twilio (o mock) (2 pts, Backend)
- T19.3.2 — Envio OTP por Email via SendGrid (1 pt, Backend)

**S19.4 — Preferencias de Notificacion** (5 pts)
- T19.4.1 — Entity NotificationPreference (user_id, notification_type, channel, enabled) (1 pt, Backend)
  - Defaults: todo habilitado. 4 grupos no silenciables (account_security, billing_dunning, legal_compliance, certificate_critical)
- T19.4.2 — GetPreferencesQuery + UpdatePreferencesCommand + Handlers (2 pts, Backend)
  - Validar que grupos no silenciables no se desactivan, 16 grupos, canales EMAIL + IN_APP
- T19.4.3 — Controllers GET/PATCH /v1/notification-preferences (1 pt, Backend)
- T19.4.4 — Frontend: pagina Preferencias de Notificacion con toggles por grupo y canal (1 pt, Frontend)

**S19.5 — Centro de Notificaciones In-App** (5 pts)
- T19.5.1 — PersistInAppNotificationHandler: crear notificacion in-app si canal habilitado (2 pts, Backend)
  - Check preferencias antes de persistir, marcar como read/unread
- T19.5.2 — Controllers GET /v1/notifications, PATCH /v1/notifications/{id}/read, POST /v1/notifications/mark-all-read (1 pt, Backend)
- T19.5.3 — Frontend: icono campana con badge en header, dropdown recientes, pagina /notifications con historial completo (2 pts, Frontend)

### EP20 — Workers y Colas

**S20.1 — Procesos Worker** (5 pts)
- T20.1.1 — worker-sealing: consume pdf.sign + pdf.audit-trail (2 pts, Infraestructura)
- T20.1.2 — worker-general: consume webhook + notification (2 pts, Infraestructura)
- T20.1.3 — Supervisor/Docker config para workers (1 pt, Infraestructura)

**S20.2 — Crons MVP** (5 pts)
- T20.2.1 — C-13: Envelope expiration check (cada 5 min) (2 pts, Backend)
- T20.2.2 — C-12: Trusted Lists refresh (cada 6h) (1 pt, Backend)
- T20.2.3 — C-02: Cron de recordatorios programados (1 pt, Backend)
- T20.2.4 — Symfony Scheduler config (1 pt, Backend)

---

## F5 — Dashboard Completo, API y Polish

### EP21 — Dashboard: Home, Listados y Detalle

**S21.1 — Home con Metricas** (5 pts)
- T21.1.1 — EnvelopeQueryService: metricas (total, por estado, tasa completado) (2 pts, Backend)
- T21.1.2 — Controller GET /v1/dashboard/metrics (1 pt, Backend)
- T21.1.3 — Frontend: pagina Home con cards de metricas (2 pts, Frontend)

**S21.2 — Listado de Sobres** (8 pts)
- T21.2.1 — EnvelopeQueryService: listado con filtros, busqueda, paginacion (3 pts, Backend)
- T21.2.2 — Controller GET /v1/envelopes con query params (1 pt, Backend)
- T21.2.3 — Frontend: tabla con tabs por estado, barra busqueda, paginacion (3 pts, Frontend)
- T21.2.4 — Frontend: acciones masivas (exportar CSV, recordar, eliminar borradores) (1 pt, Frontend)

**S21.3 — Detalle de Sobre** (8 pts)
- T21.3.1 — Controller GET /v1/envelopes/{id} con include=recipients,documents,audit_events (2 pts, Backend)
- T21.3.2 — Frontend: pagina detalle con tabs (Resumen, Firmantes, Audit Trail, Documentos) (3 pts, Frontend)
- T21.3.3 — Frontend: acciones contextuales segun estado (pausar, recordar, anular, etc.) (2 pts, Frontend)
- T21.3.4 — Frontend: timeline de audit trail visual (1 pt, Frontend)

### EP22 — Templates, Contacts y Signing Groups

**S22.1 — Templates** (8 pts)
- T22.1.1 — Entity Template (reutilizar workflow completo) (2 pts, Backend)
- T22.1.2 — CRUD Commands + Handlers (2 pts, Backend)
- T22.1.3 — SendFromTemplateCommand: crear envelope desde template con overrides (2 pts, Backend)
- T22.1.4 — Controllers CRUD /v1/templates + POST /v1/templates/{id}/envelopes (1 pt, Backend)
- T22.1.5 — Frontend: listado y gestion de templates (1 pt, Frontend)

**S22.2 — Contacts** (5 pts)
- T22.2.1 — Entity Contact (nombre, email, telefono, empresa) (1 pt, Backend)
- T22.2.2 — CRUD Commands + Handlers + autocompletado (2 pts, Backend)
- T22.2.3 — Controllers CRUD /v1/contacts (1 pt, Backend)
- T22.2.4 — Frontend: libreta de contactos con autocompletado en wizard (1 pt, Frontend)

**S22.3 — Signing Groups Frontend** (5 pts)
- T22.3.1 — Frontend: pagina CRUD de signing groups (3 pts, Frontend)
- T22.3.2 — Frontend: selector de signing group en wizard de creacion de sobre (2 pts, Frontend)

### EP23 — Webhooks y Developer Hub

**S23.1 — Webhook Subscriptions** (5 pts)
- T23.1.1 — Entity WebhookSubscription (URL, event types, secret) (1 pt, Backend)
- T23.1.2 — CRUD Commands + Handlers (2 pts, Backend)
- T23.1.3 — Controllers CRUD /v1/webhooks + POST /v1/webhooks/{id}/test (1 pt, Backend)
- T23.1.4 — Frontend: pagina de gestion de webhooks (1 pt, Frontend)

**S23.2 — Webhook Delivery** (8 pts)
- T23.2.1 — DeliverWebhookCommand + Handler con HMAC-SHA256 (3 pts, Backend)
- T23.2.2 — Retry exponencial: 8 intentos, backoff ~72h (2 pts, Backend)
- T23.2.3 — Entity WebhookDelivery (historial de entregas) (1 pt, Backend)
- T23.2.4 — Controller GET /v1/webhooks/{id}/deliveries (1 pt, Backend)
- T23.2.5 — EventSubscriber: despachar webhook en domain events clave (1 pt, Backend)

**S23.3 — API Keys** (5 pts)
- T23.3.1 — Entity ApiKey (sk_live_/sk_test_, SHA-256 hash, scopes, expiry) (2 pts, Backend)
- T23.3.2 — CRUD Commands + ApiKeyAuthenticator (2 pts, Backend)
- T23.3.3 — Controllers CRUD /v1/developer/api-keys (1 pt, Backend)

**S23.4 — Developer Hub Frontend** (3 pts)
- T23.4.1 — Frontend: pagina Developer Hub con tabs (API Keys, Webhooks) (2 pts, Frontend)
- T23.4.2 — Frontend: formulario creacion de API key con scopes (1 pt, Frontend)

### EP24 — SDK Embebido

**S24.1 — iFrame y PostMessage** (8 pts)
- T24.1.1 — Signer: modo embedded (query param ?mode=embedded) (2 pts, Frontend)
- T24.1.2 — PostMessage bridge: eventos iFrame -> parent (3 pts, Frontend)
- T24.1.3 — CSP frame-ancestors dinamico desde tenant_allowed_origins (1 pt, Backend)
- T24.1.4 — Controller POST /v1/envelopes/{id}/recipients/{rid}/signing-url (2 pts, Backend)

**S24.2 — Paquete @innasign/sdk** (8 pts)
- T24.2.1 — SDK JS: InnaSign.embed(config) con inline y modal modes (3 pts, Frontend)
- T24.2.2 — Event catalog: session, auth, signature, navigation, fields (3 pts, Frontend)
- T24.2.3 — Empaquetado npm + CDN build (1 pt, Frontend)
- T24.2.4 — Ejemplos de integracion (React, Vue, vanilla JS) (1 pt, Frontend)

**S24.3 — Origin Allowlist** (3 pts)
- T24.3.1 — Entity TenantAllowedOrigin + CRUD (2 pts, Backend)
- T24.3.2 — Frontend: configuracion de origenes permitidos en Settings (1 pt, Frontend)

### EP25 — White-Label, Settings, Legal y Share Links

**S25.1 — Settings del Tenant** (5 pts)
- T25.1.1 — Controller PATCH /v1/account (nombre, timezone, locale, branding) (2 pts, Backend)
- T25.1.2 — Frontend: pagina Settings con tabs (General, Branding, Seguridad, Datos) (2 pts, Frontend)
- T25.1.3 — Frontend: upload de logo y selector de colores (1 pt, Frontend)

**S25.2 — White-Label** (5 pts)
- T25.2.1 — CSS variables dinamicas desde branding del tenant (2 pts, Frontend)
- T25.2.2 — Logo del tenant en emails y Signer Workspace (2 pts, Backend)
- T25.2.3 — Dominio de email configurable (noreply@innasign.com default) (1 pt, Backend)

**S25.3 — Paginas Legales** (5 pts)
- T25.3.1 — Entity LegalDocument con versionado (2 pts, Backend)
- T25.3.2 — Entity LegalAcceptance + flujo de aceptacion (2 pts, Backend)
- T25.3.3 — Controllers GET /v1/legal, POST /v1/legal/{type}/accept (1 pt, Backend)

**S25.4 — Share Links** (5 pts)
- T25.4.1 — Entity ShareLink (token, TTL, max_downloads, PIN opcional) (2 pts, Backend)
- T25.4.2 — CRUD Commands + Controller /v1/envelopes/{id}/documents/{docId}/share-links (2 pts, Backend)
- T25.4.3 — Endpoint publico GET /v1/share/{token} (descarga sin auth) (1 pt, Backend)

**S25.5 — Paginas Legales Frontend** (3 pts)
- T25.5.1 — Frontend: pagina /legal con documentos vigentes (1 pt, Frontend)
- T25.5.2 — Frontend: banner de re-aceptacion cuando hay version nueva (1 pt, Frontend)
- T25.5.3 — Frontend: divulgacion legal al firmante en Signer Workspace (1 pt, Frontend)

### EP29 — GDPR: Export y Purge

**S29.1 — Export de Datos (GDPR Art. 15)** (5 pts)
- T29.1.1 — ExportUserDataCommand + Handler: generar ZIP con datos del usuario/firmante (3 pts, Backend)
  - Incluir: datos personales, sobres, documentos firmados, audit events, evidencias
- T29.1.2 — Controller POST /v1/account/data-export + notificacion cuando listo (1 pt, Backend)
- T29.1.3 — Frontend: boton de exportacion en Settings > Datos personales (1 pt, Frontend)

**S29.2 — Purge RGPD (Art. 17)** (5 pts)
- T29.2.1 — PurgeEnvelopeCommand + Handler (eliminar documentos, biometria, evidencias, audit trail) (3 pts, Backend)
  - Generar certificado de purga (PDF sellado con certificado de empresa)
- T29.2.2 — PurgeByRecipientCommand + Handler (purga selectiva por firmante) (1 pt, Backend)
- T29.2.3 — Controllers POST /v1/envelopes/{id}/purge, POST /v1/recipients/{id}/purge (1 pt, Backend)

### EP30 — Feature Flags

**S30.1 — Sistema de Feature Flags** (3 pts)
- T30.1.1 — Entity FeatureFlag + FeatureFlagService (check por tenant_id o global) (2 pts, Backend)
  - Tabla feature_flag (key, scope, enabled, tenant_id nullable), cache en Redis
- T30.1.2 — Fichero de configuracion de flags MVP con defaults (1 pt, Backend)
  - config/feature_flags.yaml con lista de flags y valores por defecto

---

## Resumen de volumenes

| Fase | Epics | Stories | Tasks | Story Points |
|------|-------|---------|-------|-------------|
| F0 | 6 | 15 | 37 | ~61 |
| F1 | 5 | 22 | 56 | ~86 |
| F2 | 4 | 15 | 57 | ~104 |
| F3 | 4 | 13 | 37 | ~64 |
| F4 | 4 | 12 | 45 | ~76 |
| F5 | 7 | 21 | 69 | ~115 |
| **Total** | **30** | **98** | **301** | **~506** |
