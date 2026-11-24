# Checklist de pruebas en local — release posterior a backend v0.0.1 / signer v0.0.2

Fecha: 2026-10-19. Backend `develop` @ `b70e70fd` (17 merges desde `v0.0.1`, 13 migraciones).
Signer `develop` (5 merges desde `v0.0.2`). Dashboard: rama `feat/ssr-false-spa-static` (1 commit sobre `master`).

⚠ Los pasos se han sacado leyendo código, rutas, `#[OA\*]` y handoffs, **no ejecutándolos**. Si un código de error
o un campo no coincide con lo que ves, apúntalo: puede ser un fallo o un error de este documento.
⚠ En local el almacenamiento es MinIO, que acepta lo que Linode rechaza (el incidente del custodio de hoy).
Lo de `retained` solo se prueba de verdad en Linode (§10).

Marca cada casilla con ✅ / ❌ y, si falla, el código y el body recibidos.

---

## 0. Montaje

- [ ] `make -C f5sign-infra up` (o `install` si es la primera vez) → `make -C f5sign-infra migrate` → `make -C f5sign-infra worker-up`
- [ ] `make -C f5sign-infra dss-wait-tl` (sin la TL cacheada DSS no firma)
- [ ] `make -C f5sign-infra worker-status`: worker, relay y custodian `Up`
- [ ] `f5sign-infra/.env` tiene `SIGNER_API_MODE=real` (ya está así; con `mock` el signer usa fixtures)

| Qué | URL |
|---|---|
| API | http://localhost:8000/api/v1 |
| Signer | http://localhost:3001 (enlace: `/s/<token>`) |
| Dashboard | http://localhost:3000 |
| MessagePit (email + pestaña SMS) | http://127.0.0.1:8025 |
| MinIO console | http://localhost:9101 |
| RabbitMQ | http://localhost:15672 (f5sign/f5sign) |

**Emisor = el dashboard general de factor5** (`/var/www/html/factor5_dashboard_sf`, rama `feat/ecmr-signature`):
crea los sobres de albaranes contra `F5SIGN_API_URL=http://localhost:8000/api/v1`, con la clave de su `.env.local`
(comprobado el 2026-10-19: el backend local la acepta). No hace falta dar de alta un tenant ni otra clave.

- [ ] Si SMS da `SMS_NOT_ENABLED_FOR_TENANT`: `make -C f5sign-infra sf cmd="app:identity:sms-notifications <tenant> --enable"`
- Para los negativos por curl, usa esa misma clave (sin pegarla en ningún sitio):
  `export API=http://localhost:8000/api/v1 F5_API_KEY=$(grep -E '^F5SIGN_API_KEY=' /var/www/html/factor5_dashboard_sf/.env.local | cut -d= -f2-)`

**Qué se prueba desde factor5 y qué no.** Factor5 llama a: crear el sobre, documentos, pasos, recipients (con
`claimable`, `signs_via`, `signature_modes` y canales), asignaciones, campos, enviar, leer, `claim`, `resends`,
historial de notificaciones, firma delegada (`…/signature`), `void`, `close`, el documento sellado o actual y el audit trail.
Factor5 **no** envía `biometrics_offered` ni `show_name` (usa los valores por defecto). Esos dos casos de §1 y todos
los negativos se prueban por curl.

Todas las rutas del emisor llevan `Authorization: Bearer $F5_API_KEY`. Las rutas de recipient (`claim`, historial de
notificaciones, OTP de máquina) también llevan la cabecera `F5Sign-Declared-Subject`.

**Sobre base por curl**, solo si un caso no se puede montar desde factor5 (adaptado de `notes/smoke-terminal-envelope-and-credential-retirement.sh`, la única receta vigente;
`smoke-authoring.sh` y `smoke-signing-session.sh` usan cabeceras retiradas):
`POST /envelopes` `{"title":"…","workflow_type":"SIGN_ORDERED","signing_mode":"SEQUENTIAL_PADES"}` →
`POST /envelopes/{id}/documents` → `POST /envelopes/{id}/steps` `{"ordinal":1}` → `POST /envelopes/{id}/recipients` →
`POST …/documents/{doc}/content` (multipart, `file=@x.pdf`) → `POST /envelopes/{id}/document-assignments`
(con `placements`, para que haya marca visible) → `POST /envelopes/{id}/send` `{}`.
El enlace de firma llega por email/SMS a MessagePit.

⚑ **Cambio de contrato:** `notification_channels` es **obligatorio** al añadir un recipient (§3). La receta del smoke
no lo lleva: añade `"notification_channels":["EMAIL"]`.

---

## 1. Modos de firma (TASK-054, `215f2a86`)

Recipient con `signature_modes` (`SIMPLE|DRAW|TYPE`, por defecto `[SIMPLE]`), `biometrics_offered`, `show_name`.

- [ ] Recipient con `["SIMPLE","DRAW","TYPE"]` → el signer ofrece los tres, en ese orden
- [ ] Recipient con `["DRAW"]` → el signer solo ofrece dibujar
- [ ] Firmar en SIMPLE → `status: COMPLETED`; la marca del PDF sin imagen
- [ ] Firmar en DRAW y en TYPE (un sobre para cada uno) → la marca lleva la imagen (§2)
- [ ] `show_name:false` + DRAW → la marca lleva solo la imagen, centrada
- [ ] El checkbox de biometría aparece junto a DRAW, es opcional y no bloquea la firma
- Negativos al añadir el recipient (422):
  - [ ] `signature_modes: []` → `SIGNATURE_MODES_EMPTY`
  - [ ] `biometrics_offered:true` sin DRAW → `BIOMETRICS_OFFERED_WITHOUT_DRAW`
  - [ ] `show_name:false` con solo SIMPLE → `SIGNATURE_NAME_REQUIRED`
- Negativos en `POST /signing/commit` (por curl, con la credencial de sesión; 422):
  - [ ] sin `signature_mode` → `VALIDATION_ERROR`
  - [ ] SIMPLE con `signature_image` → `SIGNATURE_IMAGE_NOT_ACCEPTED`
  - [ ] DRAW sin `signature_image` → `SIGNATURE_IMAGE_REQUIRED`
  - [ ] un modo no ofrecido → `SIGNATURE_MODE_NOT_OFFERED`

## 2. Firma dibujada en la marca y texto que cabe (`5d0957d1`, `ee2889a8`)

- [ ] La imagen dibujada aparece en **todas** las marcas del recipient, encima del nombre
- [ ] La imagen conserva sus proporciones (no se estira)
- [ ] Recipient con un nombre muy largo y una marca pequeña → el texto queda dentro de la caja, cortado con "…"
- [ ] Negativo: una imagen PNG de más de 600×240, de más de 100 KB o entrelazada (por curl) → 422 `SIGNATURE_IMAGE_INVALID`, y no se firma nada

## 3. Canales de notificación (TASK-031, `2cc11f80`)

- [ ] `["EMAIL"]` → la invitación llega por email a MessagePit
- [ ] `["SMS"]` con `phone` móvil `+34…` → la invitación llega a la pestaña SMS de MessagePit
- [ ] `["EMAIL","SMS"]` + `notification_mode:"ALL_AT_ONCE"` → llegan las dos; con `IN_ORDER`, primero una y luego la otra (UNVERIFIED: cuándo se envía la segunda)
- [ ] `[]` → la plataforma no envía nada; en `GET /envelopes/{id}` sale `invitation_unsent_kind: DELIVERED_BY_INTEGRATOR`
- [ ] `PUT …/recipients/{rid}/notification-channels` con el sobre en curso → 200 `{warnings}`
- [ ] Invitación y OTP por el mismo canal → `warnings` contiene `LINK_AND_CODE_SHARE_A_CHANNEL`
- Negativos:
  - [ ] sin `notification_channels` → 422 `VALIDATION_ERROR`
  - [ ] `["EMAIL","EMAIL"]`, o dos canales sin `notification_mode` → 422 `NOTIFICATION_CHANNELS_REFUSED`
  - [ ] SMS con el tenant en `--disable` → 422 `SMS_NOT_ENABLED_FOR_TENANT`
  - [ ] EMAIL sin email, o SMS con un fijo → 422 `RECIPIENT_CANNOT_RECEIVE_METHOD`
  - [ ] teléfono sin `+` → 400 `INVALID_PHONE_NUMBER`
  - [ ] PUT con el sobre cerrado → 409 `CONFLICT`

## 4. Estado de la invitación visible para el emisor (TASK-056, `cde9642d`) y fiabilidad de la entrega (TASK-055, `5cc4da21`)

Necesita el worker levantado.

- [ ] Tras el envío, en `GET /envelopes/{id}` cada recipient tiene `invitation_state: SENT` e `invitation_sent_at`.
  `SENT` significa que se entregó al proveedor, no que el destinatario lo recibiera.
- [ ] Un recipient de un paso posterior queda en `NOT_YET` hasta que su paso se activa
- [ ] Anular (`/void`) o cerrar el sobre con invitaciones pendientes → las pendientes no salen
- [ ] Con el worker parado (`worker-down`), enviar y luego `worker-up` → la invitación sale tarde, pero sale (o termina en `NOT_NEEDED` si ya no hace falta)
- [ ] Los fallos transitorios no aparecen en la lectura del sobre (es así por diseño). Se ven en la tabla `notification.notification_delivery`, columnas `status`/`failure_kind`. Provocar un fallo real del proveedor en local no está documentado: si quieres probarlo, cambia `MESSAGEPIT_TWILIO_TOKEN` para que dé 403 (UNVERIFIED).

## 5. Slot reclamable (TASK-037, `cf8fc9b9`)

- [ ] Añadir un recipient con `claimable:true` y sin nombre → en la lectura sale `declared_claimable:true`, `claimed_at:null`, y no se invita a nadie
- [ ] `POST …/recipients/{rid}/claim` `{"full_name":"…","email":"…"}` + `F5Sign-Declared-Subject` → 204, y **una** invitación en MessagePit
- [ ] Repetir el mismo claim → 204, y sigue habiendo una sola invitación
- Negativos:
  - [ ] claim con otro nombre → 409 `RECIPIENT_ALREADY_CLAIMED`
  - [ ] claim sobre un recipient no reclamable → 409 `RECIPIENT_NOT_CLAIMABLE`
  - [ ] `F5Sign-Declared-Subject: f5s:none` → 400
  - [ ] reenviar (`/resends`) un slot sin reclamar → 409 `RECIPIENT_SLOT_NOT_CLAIMED`

## 6. Código de firma en el propio acto (ADR-0075, `60098a57`)

Recipient con puerta de firma: `auth.signing_methods: ["OTP_EMAIL"]` (u `OTP_SMS`).

- [ ] En el signer, al firmar se pide el código, que llega a MessagePit, y la firma pasa
- [ ] Rechazar desde el signer → pide su propio código (`act: DECLINE`) → `status: DECLINED`
- [ ] Un código pedido para firmar no sirve para rechazar, y al revés
- Negativos (por curl):
  - [ ] commit sin `code` → 401 `AUTH_CODE_REQUIRED` (no gasta intento)
  - [ ] código incorrecto → 401 `AUTH_CODE_INCORRECT`
  - [ ] `POST /signing/session/auth` con una puerta de firma abierta → 409 `SIGNING_GATE_ANSWERED_ON_THE_ACT`
  - [ ] segundo commit → `SESSION_ALREADY_COMPLETED`; segundo rechazo → `SESSION_ALREADY_DECLINED`

## 7. Límites de gasto en SMS y en OTP (TASK-057, `2ad96bbf`)

Límites por hora y ventana deslizante. Con SMS: 3 envíos por sesión, 5 por destino en el sobre, 30 por destino en total, 10 por IP de origen. Con email: 5, 10, 30 y 30. Hay además un mínimo de 60 s entre envíos.

- [ ] En el signer, recipient con OTP por SMS: pide el código 4 veces, con más de 60 s entre cada una → la 4ª da 429 `OTP_SEND_COOLING_DOWN`, con `retry_after_seconds`, `retry_at` y la cabecera `Retry-After`. El signer muestra la espera.
- [ ] Lo mismo con email: es la 6ª petición la que da 429
- [ ] `make -C f5sign-infra sf cmd="app:session:clear-otp-limits --tenant=<t> --envelope=<e> --recipient=<r> --operator=prueba"` → informa de lo que ha limpiado y avisa de que el contador por origen **no** se limpia. Después se puede volver a pedir.
- [ ] Reenviar la invitación 6 veces a un recipient con SMS (con más de 60 s entre cada una) → la 6ª da 409 `RECIPIENT_RESEND_CAP_REACHED`. Dentro de los 60 s da 409 `RECIPIENT_RESENT_TOO_RECENTLY`.
- [ ] `app:envelope:unblock-resends --tenant --envelope --recipient --operator=prueba --grant=2` → imprime "Granted 2 further resend(s)…"
- [ ] `app:notification:report-sms-volume --warn-over=0` → lista el tenant con su volumen e imprime "Nothing was blocked."
- [ ] Negativo: `clear-otp-limits` sin `--operator` → "Name --operator." y sale con error

## 8. Historial de notificaciones (TASK-058, `67253940`)

- [ ] `GET /envelopes/{id}/recipients/{rid}/notifications` + `F5Sign-Declared-Subject` → 200, `notifications[]` con `purpose`, `deliveries[]` (`channel`, `destination` enmascarado, `status`, `failure_kind`, `settled_at`)
- [ ] Están la invitación, los OTP y los reenvíos de los pasos anteriores; el email y el teléfono salen enmascarados (`a***@***.com`, `+*******12`)
- [ ] `?limit=1` → aparece `next_cursor`, y pasándolo se obtiene la página siguiente
- Negativos:
  - [ ] `limit=0` o `limit=201` → `INVALID_PAGE_SIZE`
  - [ ] `cursor=basura` → `INVALID_CURSOR`
  - [ ] un recipient de otro sobre → 404, sin nombrar ningún id
  - [ ] sin la cabecera → 400

## 9. Evidencia del navegador y audit trail (TASK-045 `7e87ce31`, TASK-059 `1262d9ec`, PR #7 `36ccbd3f`)

- [ ] Firmar desde el signer aceptando la geolocalización del navegador; firmar otro sobre denegándola
- [ ] Rechazar un sobre desde el signer
- [ ] Al terminar cada sobre, `GET /envelopes/{id}/audit-trail` descarga el PDF (el worker lo emite en cuanto termina el sobre)
- [ ] En el PDF:
  - [ ] la sección "Declarado por el navegador del firmante", con la ubicación (si se concedió) y "Navegador al firmar"
  - [ ] en el rechazo, "Navegador al rechazar" con la IP y el user agent
  - [ ] sin datos, "No consta: el navegador no envió ningún dato."
  - [ ] la sección "Invitaciones" de cada parte: canal, resultado (`SENT`…) y destino enmascarado; si a esa parte no tocaba invitarla, "Ninguna; no correspondía invitar a esta parte"
- [ ] Negativo (por curl): `evidence.geolocation` con `status:"GRANTED"` y `latitude: 91` → la firma pasa **igual**, la geolocalización se descarta y se registra el warning "Browser-reported evidence dropped at the act."

## 10. Custodio y almacenamiento (`b70e70fd`)

En local solo se prueba que el camino sigue funcionando. La prueba real es el primer barrido en Linode tras el despliegue.

- [ ] Tras completar un sobre: `make -C f5sign-infra sf cmd="app:envelope:promote-signed-documents"` → `Named N … : N conserved`
- [ ] `app:evidence-audit:conserve-trails` → `Named N trails …: N conserved`
- [ ] `make -C f5sign-infra custodian-report` → todo con exit 0 (justo después de arrancar puede salir algún rojo que desaparece en la siguiente ventana)
- [ ] En la consola de MinIO, el bucket `retained` contiene el documento y el trail, con retención COMPLIANCE
- [ ] **Después de desplegar en prod:** `make custodian-report-prod` en verde, y `s3-check-prod` sin el "retained vacio"

## 11. Proxies de confianza (`SYMFONY_TRUSTED_PROXIES`, nueva en `.env`)

- [ ] Vacía (por defecto): firmar por curl con `X-Forwarded-For: 203.0.113.9` → en el trail, la IP **no** es 203.0.113.9
- [ ] Antes de desplegar, decidir el valor en `.env.prod`: la IP o la red de Caddy. Si se queda vacía detrás de Caddy, el trail registra la IP de Caddy y no la del firmante (UNVERIFIED en la topología de prod: comprobarlo con una firma real).

## 12. Signer (`develop` desde `v0.0.2`)

Repaso visual de lo que cambia en el signer. Los contratos ya están cubiertos en §1, §2, §6 y §9.

- [ ] Los textos de la pantalla de firma se ajustan a cada combinación de modos ofrecidos
- [ ] Subir una imagen de firma (`SignatureUpload`), además de dibujar y teclear
- [ ] Consentimiento biométrico: casilla opcional junto a DRAW
- [ ] Rechazar → pantalla `declined`
- [ ] **Escalado (email principal, SMS secundario):** tras llegar el email, el SMS aparece bloqueado con una cuenta atrás
  hasta `next_resend_at` (unos 60 s) y luego se puede elegir y llega. Es el comportamiento de ADR-0054 §2.5 y §2.8: la espera es por
  puerta, no por método. Encontrado el 2026-10-19: el signer dejaba elegir SMS antes de tiempo y no pasaba nada. Se le ha pedido a la sesión del signer que lo corrija.
- [ ] En el móvil (o con el modo responsive del navegador): el canvas de firma y el aviso de permiso de ubicación

## 13. Dashboard

Solo hay un commit desde `master`: `f9c7abe`, que pone `ssr: false` (build SPA estático). No hay cambios funcionales ni llamadas al API.

- [ ] http://localhost:3000 carga, y el selector de idioma (es/en) cambia los textos
- [ ] Build de producción: genera los estáticos y se sirven bien sin SSR (navegar a `/` y recargar)
- [ ] ⚠ El commit está en la rama `feat/ssr-false-spa-static`, que aún no está en `master`. Hay que mergearla antes de la release.

## 14. Reenvío por un canal concreto (TASK-060, `fbee2488`)

Destinatario con `["EMAIL","SMS"]` declarado (y `notification_mode`), sobre enviado.

- [ ] Desde factor5 (cuando lo tenga) o por curl: `POST …/resends` con `{"channel":"SMS"}` → 204; llega **solo** un SMS a MessagePit, ningún email
- [ ] `{"channel":"EMAIL"}` → solo un email; `GET` del sobre: `notification_channels` y `notification_mode` sin cambiar
- [ ] Sin cuerpo o `{}` → igual que antes (según lo declarado)
- [ ] El historial (`…/notifications`) muestra esa única entrega en el canal elegido
- Negativos:
  - [ ] destinatario solo `["EMAIL"]` + `{"channel":"SMS"}` → 409 `RESEND_CHANNEL_NOT_DECLARED`
  - [ ] SMS declarado pero tenant con SMS desactivado (`--disable`) → 409 `RESEND_CHANNEL_UNREACHABLE`
  - [ ] destinatario con `[]` → 409 `RECIPIENT_NOTIFIED_BY_INTEGRATOR`, con o sin canal
  - [ ] `{"channel":"PIGEON"}` o `{"channel":1}` → 422 `VALIDATION_ERROR`
  - [ ] 6 reenvíos con `channel:SMS` (separados >60 s) → el 6º da 409 `RECIPIENT_RESEND_CAP_REACHED`; con `channel:EMAIL` no se agota el tope

---

## Antes de la release (no son pruebas)

- `.env.prod`: decidir `SYMFONY_TRUSTED_PROXIES`, revisar `SMS_DSN` (Twilio real) y `SMS_VOLUME_WARN_OVER`
- Backup → `deploy-backend` → migraciones (son 13) → `worker-status-prod` → `custodian-report-prod`
- El signer va **junto con** el backend: TASK-045, los modos de firma y el código en el acto cambian el contrato
- `make init-roles-prod` si alguna migración necesita un rol nuevo (p. ej. `f5sign_notification_custodian` para el informe de volumen SMS); el 2026-09-17 ya faltaron roles en prod
