# RUNBOOK — Despliegue a producción, noviembre 2026

**Estado: borrador. No está ejecutado ni ensayado, y la base es una suposición.**

- **Destino:** `f5sign-backend` `develop` @ `ce035a80` (Key Management). Infra `master` @ `8cae056`.
- **Base supuesta:** backend `v0.0.2` (`085ffef8`, 2026-10-05; `v0.0.1` es el mismo commit). Es lo más probable,
  pero nadie lo ha medido en el host. **Si la fase 0 da otro tag, este documento hay que recalcularlo.**
- **Tamaño desde esa base:** 1022 commits y 22 migraciones.
- **Redactado:** 2026-11-04, por la sesión de backend con datos de la sesión de infra.

Referencia general, que sigue vigente: `f5sign-infra/docs/operations/deploy.md` y `backups.md`. Este documento solo
concreta esta release. Si discrepan, **manda lo que diga el host**, y después se corrige lo que estuviera mal.

> **Veredicto: ventana de corte con downtime.** El código viejo no tolera el esquema nuevo (hay un `DROP COLUMN` y
> columnas obligatorias sin default) y el código nuevo necesita el esquema nuevo. No hay orden sin parada.

**Leyenda:** ⛔ irreversible o pérdida de datos · ⚠ falla en silencio o sin probar · ❓ falta un dato o una decisión

---

## 0. Antes de nada: leer el host (no cambia nada)

Se hace **antes** de cualquier `git pull`:

```bash
cd <checkout de f5sign-infra en el host>
grep -E '^(BACKEND|SIGNER)_TAG=' .env.prod
git rev-parse --abbrev-ref HEAD
git log -1 --oneline
git remote -v
make migrate-status-prod
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml images
make worker-status-prod
```

Qué hay que mirar:

| Dato | Por qué importa |
|---|---|
| `BACKEND_TAG` y `migrate-status-prod` | Fijan el rango real de migraciones. ⛔ El estado solo vale con este target: el rol de aplicación no ve la tabla y dice `Executed 0` sobre una base al día. Nunca reacciones a esa cifra con un reset. |
| `images` | La imagen que corre de verdad. `BACKEND_TAG` puede no coincidir con los contenedores: el checkout pudo cambiar sin redespliegue. **Si discrepan, manda la imagen y las migraciones aplicadas.** |
| Rama y `git remote -v` | Según la memoria de infra, el host pasó a `Factorcinco`/`master` el 2026-10-05 (`eaed865`), así que probablemente no haya problema. En agosto desplegaba desde otra rama, por lo que es una comprobación obligada. Si no es así, ❓ resolverlo con infra **antes** de abrir ventana. |
| `worker-status-prod` | Mensajes aparcados en `queue.failed` o colas con profundidad antes de empezar (§4). |
| `SIGNER_TAG` | `v0.0.2` del signer no tiene la pantalla `/c/:link`; `develop` sí. |

### Pasos que dependen de la base

| Si el host está en… | Consecuencia |
|---|---|
| `v0.0.2` (`085ffef8`) | Aplica todo lo de abajo. TASK-048 (`Version20260928131928`, `reconcile-endings`) y la caducidad de TASK-049 **ya venían** en este tag, y sus pasos debían haberse hecho entonces. ❓ No consta que `reconcile-endings` se ejecutara; se puede repetir sin riesgo (§5.5). |
| Anterior a `v0.0.1` | Hay más migraciones, TASK-048 y TASK-049 entran ahora, y la primera pasada de `sweep-clocks` cierra los sobres caducados y avisa a sus destinatarios. **Recalcular.** |
| Una imagen `:develop` u otra sin tag | Medir por `migrate-status-prod` qué falta. **Recalcular.** |

---

## 1. Decisiones previas

| ❓ | Decisión | Quién |
|---|---|---|
| 1 | Merge de `develop` a `master` del backend y tag nuevo. La CI publica `:vX.Y.Z`. Ni `ce035a80` está en `master` ni hay tag que lo contenga. | Owner |
| 2 | Tag de release del signer. La CI hornea la URL de la API según la referencia (`v*` → prod). | Owner |
| 3 | ¿Va el dashboard en esta release? El checklist del 19 de octubre lo tenía en una rama aparte, y este documento no lo cubre. | Owner |
| 4 | ¿Prod tiene tráfico real? Una migración dice *"accepted while nothing is in production"*. Con sobres en curso pesa mucho más §6. | Owner |
| 5 | Valores de `SYMFONY_TRUSTED_PROXIES`, `SMS_DSN` (Twilio real), `SMS_VOLUME_WARN_OVER` y `ALERT_EMAIL_TO`. | Owner + infra |
| 6 | ¿Se hace un rechazo de prueba en prod (§5.6)? Es la única prueba real del cifrado. | Owner |
| 7 | Ensayo con datos reales (§2). Recomendado. | Owner |

---

## 2. Ensayo recomendado

Las 22 migraciones nunca han corrido contra datos de prod, y varias reescriben filas o añaden `CHECK` y `UNIQUE`
(§7). Conviene restaurar un dump de prod en un entorno aislado, ejecutar `migrate` con el rol dueño y después el
registro de la clave. **Después, prueba el rollback:** restaura el mismo dump con la receta de §8 sobre la base ya
migrada y comprueba que el esquema y `doctrine_migration_versions` vuelven exactos. Esa receta solo se ha medido en una
reproducción pequeña; si `--create` falla con el dump real, avisa a infra, que corregiría `deploy.md` y el `Makefile`.

⚠ Un dump de prod contiene datos personales: no lo dejes en la máquina de desarrollo al terminar.

---

## 3. Preparación, con tráfico arriba

⚠ **Conflicto de orden en `deploy.md`:** la parte de TASK-070/071 pide `git pull` de infra **antes** de la release,
y la de Key Management lo pone **después** de `pull-prod`. Aquí va primero el `git pull`, porque los targets de
la clave y el compose nuevo salen de ese checkout. Por eso `pull-prod` corre sin los ficheros de la clave. Infra lo
ha probado en `--dry-run` y con una sola imagen, sin problema, pero no de forma real; el paso 3 da la salida.

**1. Infra y variables**

```bash
git pull                                    # solo tras resolver la rama y el remote de la fase 0
```

En `.env.prod`:

```bash
BACKEND_TAG=<release>
COPY_READ_CREDENTIAL_SECRET=<openssl rand -hex 32, distinto de los demás secretos>
NOTIFICATION_COPY_BASE_URL=https://<SERVER_NAME_SIGN>/c
# WRAPPING_KEY_DIR=/etc/f5sign/wrapping-key  es el valor por defecto
# revisar: SYMFONY_TRUSTED_PROXIES, SMS_DSN, SMS_VOLUME_WARN_OVER, ALERT_EMAIL_TO
```

Comprueba también que están las cuatro `POSTGRES_*_PASSWORD`: `init-roles-prod` se niega a correr sin ellas. Después:

```bash
make config-prod PROD_ENV=.env.prod         # tiene que salir verde
```

**2. Copia de ensayo** (prueba credenciales, disco y mecanismo; no es la copia buena)

```bash
make backup-prod LABEL=ensayo
```

**3. Imagen y clave**

```bash
make pull-prod
# si falla porque faltan los ficheros de la clave:
#   docker pull ghcr.io/dpeite-innatial/f5sign-backend:<release>
sudo make wrapping-key-prod                 # genera la clave una vez; nunca sustituye ficheros
make pull-prod                              # solo si falló antes
```

**4. Copia de los secretos**

```bash
sudo make backup-secrets BACKUP_DIR=$HOME/f5sign-backups && sudo chown -R $(id -un): $HOME/f5sign-backups
```

Saca el paquete del host y guarda la passphrase aparte. `deploy.md` lo escribe sin `sudo`, pero el par es de root con
permisos `600` y el target falla sin él.

⛔ **Sin el par de claves, todo valor cifrado queda ilegible para siempre, en la base y en cada backup.** Nunca generes
otro sobre una base que ya tenga valores cifrados: restaura los ficheros desde este paquete. La clave no tiene
rotación todavía.

**5. Signer, justo antes de la ventana**

```bash
# SIGNER_TAG=<release> en .env.prod
make deploy-signer                          # no arrastra al backend: el signer no tiene depends_on
```

Abre una URL `/c/…` y comprueba **a ojo** que es la pantalla de copia. Un 200 no prueba nada: la app responde 200
también en rutas que no tiene.

⚠ **Sin comprobar:** `deploy.md` pide el signer antes del backend para que ningún correo enlace a una página
inexistente, pero nadie ha comprobado cómo funciona el signer nuevo contra el backend viejo. Una migración avisa de
lo contrario: un signer viejo es rechazado por el backend nuevo al firmar. Por eso va el último de esta fase y sin
pausa hasta la ventana. ❓ Confirmarlo con la sesión del signer.

---

## 4. La ventana

**Dos pasos se apartan de `deploy.md`; el owner los aceptó el 2026-11-04.** Están marcados con «propuesto» hasta que
`deploy.md` los incorpore. La secuencia antigua era: `worker-down-prod`, `stop caddy`, y `deploy-prod` directamente
tras el registro de la clave.

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml stop caddy
# ── ventana abierta ──────────────────────────────────────────────
make worker-status-prod             # propuesto: esperar a 0 mensajes en toda cola con consumidor
make worker-down-prod
make backup-prod LABEL=corte        # LA copia buena: ya sin escrituras
make init-roles-prod                # antes de migrar; al terminar lista los roles
make migrate-status-prod
make migrate-prod                   # corre desde la imagen nueva, sin desplegarla
make register-wrapping-key-prod     # antes de servir tráfico; se puede repetir

# propuesto: punto de decisión, sin tráfico ni workers
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --wait php-fpm
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml exec -T php-fpm ls /run/secrets
# arranca y no aparece wrapping_key_pair → seguir. Si no → rollback dentro de ventana (§8).

make deploy-prod                    # NO deploy-backend: dejaría el relay en la imagen vieja
# ── ventana cerrada ──────────────────────────────────────────────
make migrate-status-prod
make worker-status-prod
```

- **Vaciar colas (propuesto):** parar caddy primero corta las escrituras nuevas y deja que el código viejo procese lo
  suyo. `queue.failed` y `queue.events.unroutable` no tienen consumidor y no bajan a 0, y `worker-status-prod` no
  muestra el avance del relay. Según la lectura de los `fromPayload` desde `v0.0.2`, los eventos en cola se decodifican también con el
  código nuevo: las claves añadidas son opcionales y no desaparece ningún tipo. Por eso no parece obligatorio, pero
  no se ha ejecutado, y un mensaje indecodificable bloquea su cola hasta purgarla a mano (BL-100). Si un reintento
  retrasado impide llegar a 0, decide en ese momento.
- **`queue.failed`:** usa el serializador PHP por defecto, no el de los eventos, así que un mensaje aparcado puede no
  deserializarse si su clase ha cambiado. Revísalo en la fase 0 y resuelve lo que haya **antes** de la ventana.
- **Punto de decisión (propuesto):** `deploy-prod` levanta a la vez caddy, workers y custodian, y desde ese momento
  pueden salir correos y sweeps. Solo prueba el arranque y la configuración, no el flujo completo.
- **`init-roles-prod`:** `Version20261015093359` falla sin `f5sign_notification_custodian`, que entró en el script de
  infra el 15 de octubre. No la hagas tolerante: un objeto creado sin su rol queda en manos de un superusuario que se
  salta RLS.
- **`register-wrapping-key-prod`:** hasta que corre, el backend rechaza **todos** los rechazos de firma, porque cifran
  el motivo.
- **`deploy-prod`:** importa y verifica la topología de RabbitMQ antes de arrancar el backend, incluida la cola nueva
  `queue.evidenceaudit.events`. Sin ella, el worker deja de leer **todas** las colas de eventos.
- **La copia `corte` tiene que ser del mismo día,** igual que la `ensayo`. Si hay que restaurar, es esta.

---

## 5. Verificación

1. **Contenedores:** `docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps`.
2. **Accesos:** `curl -k https://<api>/api/doc.json` y `curl -k https://<sign>/`.
3. **Sello:** `wait-for-tl.sh 300` en `eu-dss` y `make seal-check-prod`.
4. **Colas y custodio:** `make rabbit-check-dlx-prod` y `make custodian-report-prod`.
5. **`reconcile-endings`,** solo si no consta que corrió (§0). Con la ventana cerrada y los workers arriba, usando la
   lista de tenants de `deploy.md` §5.
6. **Sobre de prueba completo:** crear, enviar, abrir enlace y firmar; luego copia (`/c/…`), recibo y primera subida a
   S3. ❓ Añadir un **rechazo** con un sobre desechable: es lo único que prueba el cifrado, y su lectura en el audit
   trail o el recibo prueba el worker, que es el único que tiene el par.
7. **Logs:** el del rate limiter a nivel `error`. Falla abierto y ese log es el control.

---

## 6. Qué notarán los usuarios

Solo importa si hay sobres en curso (decisión 4):

- **Firmantes a mitad de ceremonia:** el código de firma pasa a responderse en el propio acto (TASK-052). El acto
  siguiente al despliegue vuelve a pedir el código.
- **Signer viejo:** un signer que no envía `signature_mode` es rechazado al firmar. Por eso va con el backend.
- **Reenvíos por SMS (TASK-057):** un destinatario SMS en curso con 5 reenvíos o más queda bloqueado al desplegar. Se
  repara con `app:envelope:unblock-resends`.
- **Canales:** todo destinatario existente queda con `notification_channels = ["EMAIL"]`, sea cual sea su estado.
- **Motivos de rechazo:** el motivo va cifrado en el log solo desde este despliegue. Los ya escritos siguen en claro,
  porque el log no se puede reescribir.
- **Lo que este despliegue no cifra:** `envelope.recipient.decline_reason` y `reservations` siguen en claro en sus
  columnas. Las reservas también siguen en claro en el log (ADR-0096, realización parcial).

---

## 7. Migraciones desde `v0.0.2`

Censo de los 22 ficheros hecho por un agente. **Solo he comprobado personalmente `20261021095351`, `20261013081004`,
`20261029084859` y el texto de `20261015093359`.** Ningún `up()` tiene una guarda que rechace filas existentes, pero
los `CHECK` y `UNIQUE` nuevos solo se han razonado, no ejecutado contra datos reales: eso cubre el ensayo de §2.

| Versión | Qué hace | No aditiva | Escribe filas |
|---|---|---|---|
| 20261006082020 | `auth_challenge.bound_act`, `CHECK`, cambia el índice único | sí | `SIGNING` → `SIGN` |
| 20261006113521 | `custody.withdrawn_at`, política y función | no | no |
| 20261007112819 | Tabla `session.signature_image` | no | no |
| 20261008083445 | `recipient.signature_modes`, `biometrics_offered`, `show_name` | sí, `NOT NULL` sin default | sí, todas; `MACHINE_KEY` → `["SIMPLE"]` |
| 20261009144204 | `notification_delivery.send_before`, `failure_kind`, `CHECK` | sí | `FAILED` → `PERMANENT` |
| 20261009145725 | `recipient.invitation_unsent_*` | no | no |
| 20261013075218 | `notification_delivery.position`, `NOT NULL`, `UNIQUE` | sí | sí, numera las entregas |
| 20261013075329 | `tenant.sms_notifications_enabled` | sí, `NOT NULL` sin default | sí, todas a `false` |
| 20261013081004 | `recipient.notification_channels`, `notification_mode` | sí, `NOT NULL` sin default | sí, todas a `["EMAIL"]` |
| 20261013110756 | 18 columnas `reported_*` y similares en `signing_session` | no | no |
| 20261015093359 | Función del volumen de SMS. ⛔ **Requiere `f5sign_notification_custodian`** | no | no |
| 20261015094057 | `notification_delivery.requested_at`, `settled_at` | no | sí, `requested_at` |
| 20261015100335 | `recipient.resend_allowance` | sí, `NOT NULL` sin default | sí, todas a `0` |
| 20261019142042 | `recipient.sms_resends_made` | sí, `NOT NULL` sin default | sí |
| 20261021095351 | Sustituye `last_resent_at` por uno por canal | ⛔ sí, `DROP COLUMN` | sí |
| 20261023095048 | Sobrecarga de `read_settled_stream` | no | no |
| 20261023100843 | Tablas `session.copy_access*` | no | no |
| 20261023100913 | Tabla `evidence_audit.issued_receipt` | no | no |
| 20261023102241 | Tabla `session.copy_link` y funciones | no | no |
| 20261023120139 | Función y política de conservación de recibos | no | no |
| 20261026114032 | Tabla `notification.recipient_part_notice` | no | no |
| 20261029084859 | Esquema `key_management` | no | no |

Roles que nombran: `f5sign_app`, `f5sign_provisioning`, `f5sign_storage_custodian`, `f5sign_notification_custodian`,
`f5sign_log_reader`, `f5sign_signing_token_custodian`, `f5sign_evidence_audit_custodian`. ⚠ Infra solo señala como
nuevo a `f5sign_notification_custodian`; compruébalo con la lista que imprime `init-roles-prod` **antes de migrar**.

Las 6 migraciones anteriores modificadas desde `v0.0.2` solo cambian comentarios. No hay que volver a aplicar nada.

---

## 8. Rollback

⛔ **`BACKEND_TAG` anterior + `deploy-prod` no es un rollback.** La imagen vieja espera el esquema viejo, y además
no puede leer un motivo cifrado: la imagen nueva escribe `{"encrypted": …}` y la vieja hace `Row::string('reason')`,
que lanza una excepción. No se ha medido qué hace después el relay o el worker con ella; hay que asumir que puede atascarse.

| Momento | Qué hacer |
|---|---|
| Falla algo **antes** de abrir la ventana | Sin efecto en datos. Revierte `BACKEND_TAG` en `.env.prod`, que ya está cambiado desde §3; si no, el siguiente `run` o `deploy` usa la imagen nueva. Si el signer nuevo ya está desplegado, vuelve también a su tag anterior. |
| Falla **dentro** de la ventana, antes de `deploy-prod` | `make backup-prod LABEL=antes-del-restore`, restaura `corte` con la receta de abajo, vuelve a `BACKEND_TAG` y `SIGNER_TAG` anteriores, `make deploy-prod` y reabre. |
| Falla **después** de `deploy-prod` | Desde ahí pueden haber salido correos y sweeps, aunque no se haya abierto al público, así que restaurar ya no sale gratis. Arreglar hacia delante. Restaurar `corte` pierde lo escrito desde entonces: en una plataforma de firma son firmas que el firmante vio confirmadas. Solo con decisión expresa del owner. |

**Receta para restaurar `corte`,** de la rama de infra `docs/deploy-cutover-sequence` (`374949e`), aún sin mergear a
`master`:

```bash
DC="docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml"
$DC stop php-fpm worker relay custodian
$DC exec -T -e PGPASSWORD=<password> postgresql \
  pg_restore -U <POSTGRES_USER> -d postgres --clean --if-exists --create < <fichero>-corte.dump
```

- ⛔ **No uses la receta que imprimía `backup-prod` hasta `8cae056`** (`-d <db> --clean --if-exists`). No deshace una
  migración: deja el esquema nuevo e indica la versión vieja en `doctrine_migration_versions`, así que el estado de
  migraciones también mentiría. Infra lo midió en una reproducción pequeña, igual que la receta nueva. ⚠ Ninguna se ha
  probado con un dump real: eso cubre el ensayo de §2.
- ⛔ **`make restore-prod` no restaura `corte`.** Restaura desde pgBackRest y, sin `TARGET`, reproduce el WAL hasta el
  final: te devolvería al estado ya migrado. Solo vale como recuperación a un instante, con un `TARGET` explícito
  anterior a la migración.
- `migrate-prev` y `migrate-to` son solo de desarrollo.
- ⛔ El `down()` de `20261021095351` no devuelve la columna con sus datos.
- ⛔ Si restauras una base con valores cifrados, conserva la **misma** clave. No generes otra.

---

## 9. Abierto

- ❓ El tag real de prod, la rama y el remote del host (§0).
- ❓ Si el signer nuevo funciona contra el backend viejo durante los minutos que van entre §3 y §4.
- ❓ Merge a `master` de `docs/deploy-cutover-sequence` (`374949e`). Hasta entonces, el host imprime la receta vieja de
  restauración, `deploy.md` no tiene estas correcciones y el runbook mantiene los «propuesto».
- ⚠ La receta de restauración con `--create`: medida solo en una reproducción pequeña.
- ⚠ `pull-prod` sin los ficheros de la clave: probado solo en `--dry-run` y con una imagen.
- ⚠ `migrate-prod` y `register-wrapping-key-prod`: el primer uso real en prod será el estreno de esta combinación.
- ⚠ **BL-492:** una excepción aparcada en el failure transport, o enviada a Sentry, puede conservar un motivo
  descifrado en los argumentos de su traza. Conviene decidir antes si se acepta con `SENTRY_DSN` activo.
- ⚠ **BL-495:** solo el fichero no montado impide que un proceso descifre. Tras desplegar, comprueba que el par solo
  está en `worker`:
  ```bash
  for s in php-fpm relay custodian; do
    docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml exec $s ls /run/secrets
  done
  ```
  No debe salir `wrapping_key_pair` en ninguno.
- El checklist de pruebas (`notes/CHECKLIST-pruebas-release-2026-10-19.md`) se quedó en `b70e70fd`: no cubre TASK-070 ni
  posteriores, el recibo ni Key Management.
