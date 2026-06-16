# Mapeo Epic -> Documentos de Especificacion

Este documento indica EXACTAMENTE que ficheros de especificacion debe leer el agente para rellenar cada epic. No leas documentos que no estan listados para el epic objetivo — es una perdida de contexto.

Los paths son relativos a la raiz del proyecto.

---

## F0 — Infraestructura

### EP01 — Docker y Entorno
- `Implementación/Contexto de Desarrollo MVP.md` — equipo, repos, testing, CI/CD, dependencias
- `Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md` — servicios Docker, variables entorno
- `Arquitectura/Patrones de Código y Convenciones.md` — seccion estructura de carpetas
- `Arquitectura/Arquitectura Frontend.md` — seccion monorepo y configuracion Nuxt

### EP02 — PostgreSQL Schema
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — TODOS los ENUMs, tablas tenant y workspace
- `Arquitectura/Pilares/7. Infraestructura y Compliance.md` — seccion C (Base de datos, RLS, PgBouncer)

### EP03 — Mensajeria y Cache
- `Arquitectura/Arquitectura de Workers.md` — colas, exchanges, procesos worker
- `Arquitectura/Patrones de Código y Convenciones.md` — seccion CQRS, Messenger, middleware stack

### EP04 — EU DSS y Almacenamiento
- `Arquitectura/EU DSS - Guía de Integración.md` — completo
- `Arquitectura/Pilares/7. Infraestructura y Compliance.md` — seccion B (S3, buckets, WORM)
- `Arquitectura/Pilares/4-5. Evidencias, Autenticación y Criptografía.md` — seccion D (Motor de firma)

---

## F1 — Auth y Tenancy

### EP05 — Modelo de Datos Core
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — TODAS las tablas y campos. Leer COMPLETO.
- `Arquitectura/Mapa de Módulos - Bounded Contexts.md` — relaciones entre bounded contexts

### EP06 — Autenticacion Dashboard
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — seccion autenticacion (JWT, OAuth PKCE, API Keys)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tablas user, refresh_token, user_invitation
- `Arquitectura/Pilares/7. Infraestructura y Compliance.md` — seccion E (seguridad perimetral, TLS)

### EP07 — Multi-tenancy y RLS
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — seccion RLS, funcion current_tenant_id()
- `Arquitectura/Patrones de Código y Convenciones.md` — SetTenantIdMiddleware, entornos saas/dedicated
- `Arquitectura/Modos de Despliegue - SaaS vs Dedicated.md` — PlanEnforcerInterface, bundles condicionales

### EP08 — API Base
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — convenciones REST, paginacion, rate limiting, idempotencia, error handling
- `Arquitectura/Patrones de Código y Convenciones.md` — controllers, middleware, error responses

### EP28 — Localizacion i18n
- `Especificaciones/Localización i18n.md` — COMPLETO. Por story:
  - S28.1 (Backend): §1-3 (vision, tipos de texto, determinacion idioma), §7 (emails transaccionales), §8.2 (Symfony Translation), §8.3 (plantillas Twig), §8.4 (Audit Trail PDF), §9 (fallback), §10 (API locale, Accept-Language, campo locale, errores localizados)
  - S28.2 (Frontend): §1-3 (vision, tipos de texto, determinacion idioma), §4 (formatos regionales — fechas, numeros, moneda, timezone via Intl API), §8.1 (vue-i18n), §11 (Signer — auto-deteccion + selector), §12 (Dashboard — selector), §13 (lo que NO se traduce), §14 (SaaS vs Dedicated)
- `Arquitectura/Arquitectura Frontend.md` — seccion vue-i18n y configuracion Nuxt (solo para S28.2)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — campo `locale` y `timezone` en tablas user, tenant, recipient
- `Especificaciones/Notificaciones - Preferencias y Centro In-App.md` — solo si la story toca preferencias de idioma de usuario

---

## F2 — Core Envelope

### EP09 — Envelope CRUD
- `Arquitectura/Pilares/1. Workflows y Ciclo de Vida.md` — secciones A (tipos routing), D (excepciones), maquina de estados completa
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla envelope con TODOS los campos
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — endpoints /v1/envelopes
- `Negocio/Modelo de Monetización y Pricing.md` — PlanEnforcement, limites por plan

### EP10 — Document Upload
- `Arquitectura/Pilares/1. Workflows y Ciclo de Vida.md` — seccion G (Document Visibility)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tablas document, document_upload
- `Arquitectura/Pilares/7. Infraestructura y Compliance.md` — seccion B (S3 buckets, rutas de almacenamiento)
- `Arquitectura/Pilares/2. Dashboard del Remitente.md` — Paso 1 del Wizard, Text Tags (seccion D.3)

### EP11 — Recipients y Workflow
- `Arquitectura/Pilares/1. Workflows y Ciclo de Vida.md` — COMPLETO (routing, roles, signing groups, delegacion, expiracion, recordatorios, delayed routing)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tablas recipient, signing_group, signing_group_member
- `Arquitectura/Pilares/2. Dashboard del Remitente.md` — Paso 2 del Wizard, Workflow Builder
- `Arquitectura/Arquitectura de Workers.md` — W-07 (Delayed Routing), W-11 (Reminder), C-13 (Expiration)

### EP12 — Posicionamiento de Campos
- `Arquitectura/Pilares/2. Dashboard del Remitente.md` — Paso 3 del Wizard, Editor Visual (seccion B)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla field con todos los campos
- `Arquitectura/Pilares/1. Workflows y Ciclo de Vida.md` — seccion B (roles de participantes, campos por rol)
- `Arquitectura/Arquitectura Frontend.md` — componente FieldPositioner

---

## F3 — Signer Workspace

### EP13 — Sesion del Firmante
- `Arquitectura/Pilares/3. Signer Workspace.md` — secciones A (UX), D (modos despliegue), H (Signing Session)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla signing_session
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — endpoints /v1/signing/*
- `Arquitectura/Arquitectura Frontend.md` — stores y componentes del Signer
- `Especificaciones/Embedded Signing - Especificación SDK.md` — signing URL, zero cookies, iFrame

### EP14 — Autenticacion Firmante
- `Arquitectura/Pilares/4-5. Evidencias, Autenticación y Criptografía.md` — seccion A (Identity Proofing, 12 metodos, solo MVP: DIRECT_LINK, ACCESS_CODE, OTP_SMS, OTP_EMAIL)
- `Arquitectura/Pilares/3. Signer Workspace.md` — seccion H (auth TTL, re-auth)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — enum auth_method, tabla signing_session campos auth

### EP15 — Captura de Firma
- `Arquitectura/Pilares/3. Signer Workspace.md` — seccion B (Motor de Captura Biometrica), seccion I (Reviewer)
- `Arquitectura/Pilares/4-5. Evidencias, Autenticación y Criptografía.md` — seccion B (biometria grafometrica, ISO 39794-7)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla signature_execution
- `Arquitectura/Arquitectura Frontend.md` — componentes SignatureCanvas, TypedSignature, BiometricConsent

### EP16 — Evidencias
- `Arquitectura/Pilares/4-5. Evidencias, Autenticación y Criptografía.md` — seccion B (evidencias pasivas), seccion C (cifrado)
- `Arquitectura/Pilares/3. Signer Workspace.md` — seccion C (evidencias silenciosas)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla evidence_packet
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — endpoint POST /v1/signing/session/complete

---

## F4 — Sellado y Cierre

### EP17 — Sellado PAdES
- `Arquitectura/EU DSS - Guía de Integración.md` — flujo AES completo, endpoints REST, modulos
- `Arquitectura/Pilares/4-5. Evidencias, Autenticación y Criptografía.md` — seccion D (motor de firma, PAdES profiles)
- `Especificaciones/Sellado Directo - Especificación.md` — COMPLETO (seal-only, visual, errores)
- `Arquitectura/Arquitectura de Workers.md` — W-01 (firma PAdES), W-02 (sellado final)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla seal_config, enum pades_profile

### EP18 — Audit Trail
- `Arquitectura/Pilares/4-5. Evidencias, Autenticación y Criptografía.md` — seccion E (TSA, Audit Trail)
- `Arquitectura/Pilares/9. Catálogo de Notificaciones.md` — lista de event_types para audit
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla audit_event
- `Arquitectura/Arquitectura de Workers.md` — W-03 (Audit Trail PDF)
- `Especificaciones/Localización i18n.md` — Audit Trail bilingue

### EP19 — Notificaciones Core
- `Arquitectura/Pilares/9. Catálogo de Notificaciones.md` — COMPLETO (todas las notificaciones MVP)
- `Arquitectura/Arquitectura de Workers.md` — W-05 (Email/SMS), W-11 (Reminder)
- `Especificaciones/Localización i18n.md` — templates por idioma
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla notification

### EP20 — Workers y Colas
- `Arquitectura/Arquitectura de Workers.md` — COMPLETO (todos los workers y crons)
- `Arquitectura/Patrones de Código y Convenciones.md` — Symfony Messenger, transports
- `Implementación/Contexto de Desarrollo MVP.md` — dependencias externas (FNMT, EU DSS)

---

## F5 — Dashboard y Polish

### EP21 — Dashboard Home y Listados
- `Arquitectura/Pilares/2. Dashboard del Remitente.md` — secciones E (Listado), E.2 (Detalle)
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — endpoints GET /v1/envelopes, include, filtros
- `Arquitectura/Arquitectura Frontend.md` — paginas y stores del Dashboard

### EP22 — Templates, Contacts, Groups
- `Arquitectura/Pilares/2. Dashboard del Remitente.md` — seccion D (Plantillas, Bulk Send, Text Tags)
- `Arquitectura/Pilares/1. Workflows y Ciclo de Vida.md` — seccion C (Signing Groups)
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tablas template, contact, signing_group
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — endpoints /v1/templates, /v1/contacts, /v1/signing-groups

### EP23 — Webhooks y Developer Hub
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — seccion Webhooks completa, seccion API Keys
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tablas webhook_subscription, webhook_delivery, api_key
- `Arquitectura/Arquitectura de Workers.md` — W-04 (Webhook delivery)
- `Arquitectura/Arquitectura Frontend.md` — paginas Developer Hub

### EP24 — SDK Embebido
- `Especificaciones/Embedded Signing - Especificación SDK.md` — COMPLETO
- `Arquitectura/Pilares/3. Signer Workspace.md` — seccion D (modos: standalone, embedded)
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — endpoint signing-url
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tabla tenant_allowed_origins

### EP25 — White-Label, Settings, Legal, Share Links
- `Arquitectura/Pilares/2. Dashboard del Remitente.md` — Settings, Branding
- `Especificaciones/Páginas Legales.md` — COMPLETO (documentos legales, versionado, aceptacion)
- `Arquitectura/Pilares/6. API RESTful y Webhooks.md` — endpoints /v1/account, /v1/legal, /v1/share
- `Arquitectura/Modelo de Datos - ERD PostgreSQL.md` — tablas legal_document, legal_acceptance, share_link
- `Especificaciones/Localización i18n.md` — locale del tenant, timezone
