# HANDOFF — Capa de plantillas de Notification + fallo del relay de eventos

**Estado:** decisión tomada, sin implementar. Repo afectado: `f5sign-backend` (+ `f5sign-infra` para un bloque).
**Origen:** ¿las plantillas HTML de email están dentro o fuera de los PHP? Dentro —
`EmailNotificationChannel.php`, 609 líneas, copy en `const TEMPLATES` y markup en heredocs.

---

## Resumen ejecutivo

Sustituir el archive direccionado por contenido (`Foundation/Templating` + `platform.template`) por
**Twig** (maquetación) + **catálogos ICU** (palabras) + **SHA de release** (trazabilidad). Y antes de eso,
cerrar un fallo vivo del relay de eventos que provoca notificaciones que nunca se envían.

---

## Parte 0 — El fallo vivo (prioridad, independiente de todo lo demás)

`EventRelay::relayBatch():125-134` captura `Throwable` por fila:

- Falla → `recordDeadLetter()` incrementa contador
- Por debajo de `MAX_ATTEMPTS = 5` → `break`, el cursor no avanza, reintenta en el siguiente poll
- **Al llegar a 5 → el checkpoint avanza *por encima* de la fila.** Cuarentena permanente.

El hecho nunca sale del log → **la notificación nunca se envía**. Queda en `platform.event_dead_letter`
(`event_id`, `consumer`, `error`, `attempt_count`, `failed_at`; PK `(event_id, consumer)`; sin RLS).

```
grep -rn "dead_letter" src/ --include="*.php" | grep -v EventRelay
→ (vacío)
```

**Ningún código del repo lee esa tabla.** Ni comando, ni health check, ni métrica.

El docblock de `tests/F5Sign/Notification/Unit/Contract/Event/NotificationEventPayloadTest.php` confirma
que este modo de fallo *"has already reached dev/prod **twice** on this BC's event path"*, produciendo
*"a notification that silently never sends"*.

### El otro punto de decodificación: el consumidor

`SelfSerializingMessageSerializer::decode()` lanza `RuntimeException`; `Row` lanza
`UnexpectedValueException`. Pero `vendor/symfony/amqp-messenger/Transport/AmqpReceiver.php:81` **solo
captura `MessageDecodingFailedException`** — que aparece **cero veces** en `src/` y `tests/`.

Resultado: el mensaje no se rechaza ni se confirma, la excepción mata el worker, el mensaje sigue sin
confirmar → se redistribuye → **bucle de envenenado**. No llega al transporte `failed` ni a la escalera de
reintentos: ambos operan sobre `Envelope`s. Y las colas **no tienen dead-letter-exchange** en
`f5sign-infra/docker/rabbitmq/definitions.json` (solo un `alternate-exchange` para *no enrutables*).

### Orden de trabajo

| | Qué | Repo |
|---|---|---|
| **0a** | Comando de consola que lista la cuarentena (`event_dead_letter`) | backend |
| **0b** | Reproceso: rebobinar checkpoint / republicar fila. Mecanismo: `UPDATE` de una fila en `platform.event_checkpoint` (`consumer`, `last_transaction_id`, `last_global_position`). Hoy sin CLI | backend |
| **1** | Fixture de bytes canónicos por `event_type` — ADR-0031 ya lo tiene fichado como *"Not enforced — **queued, not built**"* | backend |
| **0c** | `MessageDecodingFailedException` + DLX en la topología. **DLX primero**: rechazar sin dead-letter *descarta* el mensaje | backend + infra (2 PRs, regla 4) |

**Por qué el fixture (1) importa:** ADR-0031 explica que el test round-trip actual *"serializes and
deserializes with the **same code** and therefore can never catch a backward-incompatible `fromPayload()`
edit — the two move together and agree with each other while both drift away from the bytes already in the
log."* Hoy puedes romper la decodificación de todo el log histórico y tener la suite en verde.

Modelo: `RelayEventLogCommand` (`#[AsCommand(name: 'app:event-log:relay')]`, inyecta `EventRelay`,
`SymfonyStyle`).

---

## Parte 1 — La decisión de plantillas

### Qué la fuerza

1. **Plurales y género para 20 idiomas.** `TemplateSyntax::TOKEN_PATTERN` (`/\{\{(\w+)\}\}/`) está
   **congelado** y solo admite nombres de variable. Polaco: 4 formas plurales. Árabe: 6. Ya se manifiesta
   en castellano — `«Contrato Q3» ha sido firmado` correcto, `«Acta de reunión» ha sido firmado`
   incorrecto (pediría *firmada*), género del título desconocible, **no arreglable en render**.
2. **Flujo de traducción real.** El catálogo es una `const` PHP; ninguna herramienta (Crowdin, Lokalise,
   Phrase) lo entiende y ningún traductor lo toca.
3. **Copy por tenant** (destino de producto confirmado). El archive **no puede** responder *"¿qué decía la
   plantilla del tenant X el 3 de marzo?"*: es direccionado por contenido y **sin búsqueda por
   coordenadas**, así que para construir el id necesitas el contenido que buscas.

### La medición que lo decidió

**La huella conductual completa del pin son ~2,3 minutos.** Solo cambia el comportamiento entre crear una
entrega y transmitirla, ventana acotada por la escalera de reintentos (`messenger.yaml`: `max_retries: 4`,
2s→6s→18s→54s; el comentario la cifra en ≈2,3 min).

No se estira porque:
- **Un reenvío es ocasión nueva** — domain model: *"a forced resend […] is a **new occasion with a new
  id**, and it actually sends."*
- **Replicar un evento viejo es no-op** — `TransmitDeliveryUseCase:73`: `if (!$delivery->isPending())
  return;`

Coste de esos dos minutos: ~14 clases, una tabla con RLS + política + trigger, un fingerprint congelado, un
namespace UUID congelado, y una sintaxis congelada que bloquea ICU.

### Rebatiendo ADR-0038

- **Twig — "descalificado por semántica".** El argumento: `strict_variables` lanza ante token sin resolver,
  *"destruyendo la reconstrucción post-borrado"*. **Pero el camino de envío ya lanza** —
  `IncompleteRenderedMessageException`, `TransmitDeliveryUseCase:92-95`. Para enviar, lanzar es lo correcto
  y Twig coincide con lo que el código ya hace a mano. Los otros reproches (compila a PHP, `packages-dev`,
  fuera de alcance) son coste de adopción, no objeciones de principio — y el tenant nunca escribe Twig.
- **ICU — "creíble, aplazado, no rechazado".** Motivo textual: *"formatted output **drifts with the
  container's ICU data version** (bad for an archive whose job is reproducing what was sent)"*. **Sin
  archive, desaparece.** El propio ADR reconoce que compra *"plural/select/ordinal and locale-correct
  number/date formatting"*. `ext-intl` ya está en `composer.json`, sin usar.
- **`symfony/translation` — "resuelve la mitad equivocada".** Reproche: *"no versioning, no pinning, no
  per-tenant record and no archive"*. Rechazo **condicionado a querer el archive**. Sin él es la
  herramienta correcta; el "per-tenant record" lo sirve la tabla de revisiones.
- **D9 (el token sin resolver sobrevive, para reconstrucción post-borrado)** — **sin consumidor**. Quien
  reproyectaría es el proyector de Evidence & Audit (TASK-014, sin empezar), y aunque existiera los eventos
  son **punteros finos**: `DeliveryRequested` lleva `notification_id`, `delivery_id`, `tenant_id`,
  `occurred_at` y **ningún contenido**. El texto nunca estuvo en el log.
  ✅ **Confirmado con el usuario: sin valor judicial, no hace falta reconstrucción.**

### La decisión

| Qué | Dónde | Versionado por | Quién edita |
|---|---|---|---|
| **Maquetación** | Twig, `templates/notification/` | SHA de release | Solo desarrollo |
| **Palabras** | Catálogos ICU por idioma, `translations/` | SHA de release | Traductores vía TMS |
| **Copy de tenant** | `notification.tenant_copy` + tabla de revisiones | `revision_id` | El tenant |
| **Marca** | Campos estructurados (logo, color) — **nunca HTML libre** | — | El tenant |

La entrega registra `plantilla + locale + release_sha + tenant_copy_revision_id` (nulo = plataforma).
Reproducir = `git checkout <sha>` y renderizar. **Trazabilidad de ingeniería, no prueba legal.**

### Seguridad de variables en Twig — estructural, no lint

1. **Objeto de vista tipado por purpose** — `final readonly class` con propiedades tipadas; la plantilla
   escribe `{{ view.envelopeTitle }}`. Los dos extremos tipados. **Elimina la clase de bug**, no la
   detecta. Ataca de paso el riesgo que ADR-0037 ya tiene fichado (*"the template's text is versioned; the
   code supplying its slots is not"*).
2. **`strict_variables: true`** — variable indefinida pasa de blanco silencioso a excepción.
3. **Smoke test cartesiano** `(plantilla × purpose × locale)` en CI. El repo ya tiene esa forma
   (`catalogedPurposes()` itera `NotificationPurpose::cases()`), así que se amplía sola.

**Rector no sirve** (no entiende plantillas Twig). **TwigStan** merece evaluarse como extra; verificar
soporte Twig 3 / PHP 8.5 antes de comprometerse.

### Marca de correlación en el email

Comentario HTML con `delivery_id` + `release_sha`. Un cliente reenvía el correo, se mira el fuente, queda
identificada la entrega y el código que la produjo.

**Rechazado: hash del propio email.** Los correos se modifican en tránsito de forma legítima y rutinaria —
Defender/Safe Links, Proofpoint y Mimecast reescriben URLs del cuerpo HTML; las pasarelas añaden banners;
el `Content-Transfer-Encoding` se re-codifica; los finales de línea se normalizan. Un hash del cuerpo daría
falsos positivos constantes, no evidencia. (SPF/DKIM/DMARC: **excluido explícitamente** del alcance.)

### Consecuencias

**Positivas:** plurales/género/ordinales · catálogos que las TMS entienden · *"¿qué decía la plantilla del
tenant X?"* → un `SELECT` · variación estructural con `{% block %}` · ~14 clases y una tabla menos.

**Negativas:** se pierde reproducción byte-exacta · se pierde deduplicación de copy entre tenants (sin
cliente) · `TwigBundle` entra en alcance (actualizar `CLAUDE.md`, hoy lo lista como fuera) · un mensaje
aparcado y reintentado días después sale con copy nuevo.

**Riesgos:** la salida de ICU **varía con la versión de datos ICU del contenedor** — aceptable para
trazabilidad de ingeniería, inaceptable si algún día se quiere valor probatorio · alcance real (4 clases de
Notification, ~14 de Foundation, 18 ficheros de test, 2 migraciones, 2 ADRs) · **el texto se versiona, el
código que rellena sus huecos no** → con edición por tenant pasa de peligro raro a acción rutinaria de
usuario. **Mitigación obligatoria: lista blanca de tokens por `(canal, purpose)` validada al guardar.**

### Lo que NO cambia

Los eventos (`DeliveryRequested` es puntero fino, **ningún payload se toca**) · el agregado `Notification`,
sus estados, la política de fan-out, el contrato de fallo del canal · un servicio por medio con iterador
etiquetado (ADR-0037 D9) · la convergencia (`if (!$delivery->isPending()) return;`).

---

## Parte 2 — Reglas de redespliegue

1. **Nunca añadir un campo obligatorio a un payload.** Usar `Row::optionalString()` — su docblock lo dice
   literalmente. Precedente: `optionalString('reservations')` en 4 eventos de 4 BCs.
2. **Nunca renombrar un `event_type` en sitio.** Añadir el nuevo, escribir ambos, retirar el viejo.
3. **Esquema: código primero, migración después** (dos releases). El orden inverso rompe.
4. **Drenar antes de desplegar:** `make worker-down` → profundidad 0 (`make worker-status`) → deploy →
   `make worker-up`. El log es la fuente de verdad, así que drenar no pierde nada.

---

## Orden de ejecución

| # | Bloque | Repo | Depende de |
|---|---|---|---|
| **0a/0b** | Visibilidad + reproceso de la cuarentena | backend | — |
| **1** | Fixture de bytes canónicos por `event_type` | backend | — |
| **0c** | `MessageDecodingFailedException` + DLX | backend + infra | — |
| **2** | Twig + `symfony/translation`; `TwigBundle`; `CLAUDE.md` | backend | — |
| **3** | Maquetación a Twig + objeto de vista tipado + `strict_variables` + smoke cartesiano. **Sin tocar copy ni archive.** Salida byte-idéntica | backend | 2 |
| **4** | Palabras a catálogos ICU. **Español entra aquí**, con plurales de verdad | backend | 3 |
| **5** | Quitar el archive; añadir `release_sha` a la entrega | backend | 4 |
| **6** | Migración: tirar `platform.template` y `template_id`. **Release aparte de la 5** (regla 3) | backend | 5 desplegado |
| **7** | Los dos ADRs; ADR-0038 → `Superseded`; 3 ediciones en `docs/adr/README.md`; `docs/ddd/notification-domain-model.md` | backend | 6 |

**Copy de tenant NO entra.** Prerequisito duro: **no existe tabla de tenants** — cero migraciones crean
una, el tenant sale de una cabecera `X-Tenant-Id` de pega, provisioning diferido a Identity & Access. El
bloque 5 solo deja el sitio hecho: las palabras siempre **parámetro** del compositor, nunca constante que
va a buscar.

### ⚑ Trampa del bloque 3

**Twig autoescapa por defecto.** El código actual acuña gemelas `x` / `x_html` a mano porque el motor es
inerte. **Con Twig hay que quitar las gemelas o se escapa dos veces** (`&amp;lt;script&amp;gt;`). Es el
error más probable del bloque, y el test de escapado que ya existe lo caza.

### Verificación de que el bloque 3 fue neutral

`make qa` verde **sin editar un solo test** — en particular `TransmitDeliveryUseCaseTest:342` (subject
inglés exacto) y el test de escapado.

---

## Numeración de ADRs

⚠ **Comprobar contra TODAS las ramas, no contra `develop`.** Un número lo reclama *un fichero en una rama*,
así que dos ramas largas pueden acuñar el mismo. `AUTHORING.md`: *"Take the next number past the highest
that exists **anywhere in flight**."*

```bash
for b in $(git branch -a --format='%(refname:short)' | grep -v HEAD | grep -v '^origin$'); do
  git ls-tree -r --name-only "$b" -- docs/adr/ | grep -oE 'ADR-[0-9]{4}'
done | sort -u | tail -3
```

Historial: se reservaron 0042/0043 para este trabajo y **quedaron consumidos** mientras esperaba. A
11-08-2026 el máximo en vuelo es **0044**, así que el siguiente libre es **0045** — **volver a comprobar**
antes de crear ficheros.

## Estado del repo (11-08-2026)

- Rama `feat/notification-email-html`: 1 commit sin mergear (`a1947de`, el HTML por heredocs).
  **Decisión pendiente:** mergear o aparcar — el bloque 3 sustituye su implementación (el diseño, copy y
  paleta se conservan).
- `develop` 15 commits por delante.
- `config/reference.php` modificado sin commitear: **churn generado** (40/40 líneas, reordenamiento de
  anotaciones psalm). No arrastrar a ninguna rama.
