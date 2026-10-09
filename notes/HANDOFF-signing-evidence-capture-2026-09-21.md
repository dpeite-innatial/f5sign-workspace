# Handoff — Evidencias del navegador en la firma: GPS, dispositivo y lectura

| | |
|---|---|
| **Fecha** | 2026-09-21 |
| **De** | sesión `f5sign-signer` (`develop`) |
| **Para** | sesión `f5sign-backend` |
| **Repos afectados** | `f5sign-backend` (contrato + persistencia, primero), `f5sign-signer` (captura + envío, después) |
| **Estado** | **Propuesta. Nada implementado en el backend.** En el signer hay cambios SIN commitear en `develop` que preparan el terreno (ver §6). |
| **Origen** | Petición del usuario: *"el gps se tiene que enviar siempre que sea posible. Y tenemos que recoger todo lo posible en plan ip, user agent, y demás cosas que puedan ayudar"*. |

---

## 1. Por qué existe esta nota

El signer lleva meses capturando GPS y huella del dispositivo al firmar, y **contra el backend real
todo eso se tiraba a la basura**: `POST /api/v1/signing/commit` solo acepta `consent` y
`reservations` ([`CommitSignatureRequest.php`](../f5sign-backend/src/F5Sign/Session/UI/Http/Request/CommitSignatureRequest.php)),
y el endpoint rico de evidencias (`POST /signing/session/evidence`) no existe — el adaptador real lo
marca `notInBackend('sendEvidence', 'TASK-014')`, y
[TASK-014](../f5sign-backend/docs/tasks/TASK-014-evidence-audit-projector.md) está en *"Scoping /
design — NOT started"*.

La captura era además la parte lenta del cierre (fix GPS de alta precisión, hasta 10 s) y pedía
permiso de ubicación para nada. El 2026-09-21 el signer la **apagó donde no hay a quién enviarla**
(`hasRichSignFlow()`), a la espera de este contrato. El usuario quiere lo contrario de apagarla:
quiere que **viaje**. Eso empieza aquí.

## 2. Lo que el backend YA registra solo (verificado en código, no en prosa)

Observado por el servidor, sin que el cliente haga nada. Es la evidencia fuerte: nadie la declara.

| Dato | Dónde | Nota |
|---|---|---|
| IP | `CommitSignatureController` → `$request->getClientIp()` → columna `signer_ip` | ⚠ ver §5.2 (proxies) |
| User agent | cabecera `User-Agent` → `signer_user_agent` | |
| Consentimiento + instante | `ConsentRecorded` en el log, `completed_at` en la fila | |
| Método que se PROBÓ en cada puerta | `access_method_executed`, `access_gate_passed_at`; `AuthGatePassed` / `AuthVerificationPassed` en el log | |
| Método que se ELIGIÓ | `chosen_auth_method` | distinto del probado, a propósito (ADR-0054 §2.6) |

⚠ `signer_ip` y `signer_user_agent` se guardan **en claro**. [ADR-0032](../f5sign-backend/docs/adr/ADR-0032-evidence-pii-custody.md)
(Proposed) los clasifica como *"mutable evidential attributes → eager-custody snapshot at capture;
ciphered (PII)"*, y el sustrato de cifrado ya existe ([ADR-0033](../f5sign-backend/docs/adr/ADR-0033-pii-field-encryption-at-rest.md)).
Lo que se añada aquí hereda la misma pregunta: **decidir si va cifrado desde el primer día** (lo
recomendable: añadir columnas en claro para cifrarlas después es una migración de datos personales).

## 3. Lo que el usuario ha elegido que viaje (y lo que no)

Elegido por el usuario el 2026-09-21 de una lista de cuatro:

1. **GPS, si hay permiso** — y si no lo hay, **la negativa**, que también es evidencia.
2. **Contexto del dispositivo** — zona horaria, idiomas, pantalla, SO, modelo (Client Hints) y el
   reloj del cliente al firmar.
3. **Lectura del documento** — qué documentos se leyeron hasta la última página, y cuánto tiempo.

**Descartado:** la huella canvas/WebGL (`webgl_hash`, `canvas_hash` en
[`useDeviceFingerprint.ts`](../f5sign-signer/app/composables/useDeviceFingerprint.ts)). Identificar
un dispositivo por huella exige consentimiento según la ePrivacy (art. 5.3) y como prueba vale poco.
Tampoco entra aquí la biometría del trazo: tiene su propio consentimiento y el backend fija hoy
`biometric_capture_enabled: false` en `GetSigningSessionController`.

## 4. Propuesta de contrato

### 4.1 Dónde: dentro del propio commit, no en un endpoint aparte

Un bloque `evidence` **opcional** en el body de `POST /signing/commit`:

- **Atómico con el acto.** Se escribe en la misma transacción que `SignatureCommitted`: no puede
  haber evidencia sin firma ni firma que se quedó sin su evidencia por un fallo de red entre dos
  llamadas. El endpoint aparte del diseño antiguo (evidence → complete) tiene exactamente ese hueco.
- **Sin orden que coordinar**, sin estado intermedio "evidencia recibida, firma pendiente".
- **Ausente sigue siendo válido.** Un cliente viejo, un navegador sin geolocalización o un firmante
  que deniega todo firman igual. La evidencia nunca puede ser la razón de que alguien no pueda firmar.

### 4.2 La procedencia va en el nombre — el precedente ya existe

[`AssertedEvidence`](../f5sign-backend/src/F5Sign/Session/Domain/ValueObject/AssertedEvidence.php)
(ADR-0055, firma delegada) ya resolvió esto: `signer_ip` es *lo que vimos*, `asserted_signer_ip` es
*lo que nos dijeron*, y **no se mezclan nunca**, porque después no se pueden separar. Todo lo de esta
nota lo DECLARA el navegador — un cliente manipulado puede mandar cualquier coordenada — así que va
en campos propios, con procedencia en el nombre (p. ej. prefijo `reported_`), al lado de los
observados y nunca dentro de ellos. Mismas dos reglas que allí:

- ⛔ **Nada de esto al `platform.event_log`** (append-only, sin borrado → GDPR). Si hace falta
  anclarlo en el log, un hash de compromiso.
- ⛔ **Conjunto CERRADO**, censado por test. Que añadir un campo sea una decisión y no una acreción.

### 4.3 Forma propuesta

```jsonc
{
  "consent": true,
  "reservations": null,
  "evidence": {                        // opcional entero
    "geolocation": {                   // opcional
      "status": "GRANTED",             // GRANTED | DENIED | UNAVAILABLE | TIMEOUT
      "latitude": 42.8782,             // solo con GRANTED
      "longitude": -8.5448,
      "accuracy_m": 18.0,
      "captured_at": "2026-09-21T10:15:02Z"
    },
    "device": {                        // opcional, todos sus miembros opcionales
      "timezone": "Europe/Madrid",     // IANA
      "languages": ["es-ES", "en"],
      "screen": { "width": 390, "height": 844, "pixel_ratio": 3 },
      "platform": "iOS",
      "platform_version": "17.5",
      "model": "iPhone",               // UA Client Hints; ausente fuera de Chromium
      "touch": true,
      "client_clock_at_sign": "2026-09-21T10:15:04.120Z"
    },
    "reading": [                       // opcional; acotado por los documentos del firmante
      { "document_id": "…", "pages_total": 6, "max_page_seen": 6, "read_to_end": true, "visible_ms": 94500 }
    ]
  }
}
```

**Persistencia:** según ADR-0019 §5, como ya hizo `AssertedEvidence` — geolocalización y dispositivo
son de forma fija → **columnas tipadas**; `reading` está acotado por las asignaciones del firmante →
`jsonb` (el mismo argumento que `asserted_document_hashes`).

**Validación:** forma estricta (422 si llega mal: sería un bug de nuestro propio cliente), con
cotas — lat/lon en rango, precisión ≥ 0, `languages` ≤ N, cadenas con longitud máxima, fechas ISO.
`status` distinto de `GRANTED` con coordenadas → 422.

### 4.4 ⛔ El signer tiene hoy una trampa que el contrato debe impedir

`useGeolocation` rellena un *fallback* cuando no hay fix: `{latitude: 0, longitude: 0,
accuracy_meters: 50000, source: 'GEO_IP'}`
([`useGeolocation.ts`](../f5sign-signer/app/composables/useGeolocation.ts) → `applyFallback`). **No
hay ninguna consulta Geo-IP detrás**: es un marcador con nombre de dato. Enviado tal cual, registraría
como evidencia a un firmante situado en el golfo de Guinea. El flujo rico del mock ya lo manda así
(`buildEvidenceRequest`). Por eso la propuesta usa `status` y no admite coordenadas sin `GRANTED`, y
el signer quitará ese fallback cuando cablee esto. Si se quiere una ubicación aproximada por IP, se
calcula **en el servidor**, que es quien tiene la IP — y se marca como derivada, no como GPS.

## 5. Del lado del servidor, aparte del contrato

### 5.1 `Accept-Language`
Gratis y observado por el servidor. Guardarlo junto a `signer_user_agent`.

### 5.2 ⚠ `trusted_proxies` no está configurado
Ni en `config/packages/`, ni en `.env*`, ni en `f5sign-infra`. Hoy da igual: Caddy habla FastCGI
directo con PHP ([`docker/caddy/Caddyfile`](../f5sign-infra/docker/caddy/Caddyfile)), así que
`REMOTE_ADDR` es el cliente. **El día que se ponga un CDN o balanceador delante, `signer_ip` pasa a ser
la IP del proxy en todas las firmas, sin error ni aviso.** Decidirlo ahora (qué rango y qué
cabecera), y tener un test que lo fije.

## 6. Qué hará el signer cuando exista el contrato (y qué dejó hecho)

**Ya hecho (sin commitear en `develop`, 2026-09-21):**
- El código de la puerta de FIRMA se pide **antes** del commit, no tras un 401.
- La captura de GPS y dispositivo corre **después** de validar el código, y solo donde el backend la
  recibe (`hasRichSignFlow()` en `app/pages/s/[token]/sign.vue` → `onSign`).
- Botón «Cancelar» en el modal del código.

**Pendiente, cuando el backend publique el bloque `evidence`:**
1. `types.ts` + `pnpm contract:check` contra el OpenAPI vivo.
2. Una capacidad nueva en `useBackendCapabilities` (p. ej. `hasCommitEvidence()`) que vuelva a encender
   la captura en modo real — sin tocar `hasRichSignFlow`, que significa otra cosa.
3. Quitar el fallback `GEO_IP` falso (§4.4); mapear el fallo a `status`.
4. Contexto del dispositivo sin canvas/WebGL; modelo vía `userAgentData.getHighEntropyValues`.
5. `useDocumentReadThrough` hoy solo guarda la página más profunda por documento. **El tiempo
   visible no se mide todavía**: hay que añadirlo.
6. Latencia del GPS: el fix empieza tras el código. Valorar `maximumAge` de ~60 s y un timeout menor,
   o arrancarlo en paralelo al modal (a costa de que el aviso de permiso del navegador se superponga
   al código). Es decisión del signer.

## 7. Preguntas abiertas para el backend / el usuario

1. ¿Cifrado desde el primer día (ADR-0032/0033), y de paso `signer_ip`/`signer_user_agent`?
2. ¿Dentro del commit (recomendado) o endpoint aparte?
3. ¿ADR nuevo o enmienda de ADR-0032? Toca custodia de datos personales y tiene la puerta legal de su
   decisión 10.
4. ¿Geo-IP en servidor? Necesitaría una base de datos (MaxMind o similar), con su licencia.
5. `trusted_proxies`: ¿rango y cabecera, ahora que no hay nada delante?
