# Despliegue en prod: v1.0.0 con limpieza de datos (se conservan los tenants)

Fecha de preparación: 2026-11-06. Versiones: **infra `v1.0.0`** (`5a25db1`), **backend `v1.0.0`**
(`bf9518a9`, mismo commit que `v0.0.3`), **signer `v1.0.0`**. En prod corre hoy el backend `v0.0.2`,
que es el mismo commit que `v0.0.1` (`085ffef8`).

Base: `f5sign-infra/docs/operations/deploy.md` §5, adaptado a una limpieza. Donde este manual y el runbook
discrepen en algo que no sea la limpieza, manda el runbook.

## Qué hace este despliegue

1. Despliega el signer con la pantalla de copia (`/c/:link`).
2. Para todo lo que escribe y hace una copia completa del estado viejo (`corte`).
3. **Recrea la base de datos desde cero** y reinserta solo:
   - `identity.tenant`, `identity.api_client`, `identity.api_key` → los tenants y sus API keys
     siguen valiendo (la key solo se guarda como hash: no se puede regenerar).
   - `notification.tenant_default` → el locale por defecto de cada tenant.
4. Todo lo demás se pierde: sobres, sesiones, notificaciones, evidencias, custodias, plantillas
   archivadas y **el event log**. El runbook exige vaciar el event log antes de que entren datos reales
   con la primera release de Key Management, porque lo escrito en claro antes quedaría en claro para siempre.
5. Vacía RabbitMQ y Redis, que referencian datos que ya no existen.
6. Despliega el backend `v1.0.0` con Key Management.

## Qué se ensayó (2026-11-06) y qué no

Ensayado en una lane aislada (`wt-backend`, Postgres 18 propio):

- Con el código `v0.0.2` se provisionó un tenant y una API key, más una fila de `tenant_default`,
  y se hizo el volcado de L3.
- Después: `DROP` + `CREATE` + **solo** `init-app-role.sh`, como en prod. Las 81 migraciones de `v1.0.0`
  pasaron desde cero.
- Restauración:
  - **Sin** el truco del default falla (`null value in column "sms_notifications_enabled"`), y gracias
    a `-1` no deja nada a medias.
  - **Con** el truco, las huellas antes y después son idénticas y el event log queda a 0.
- `register-wrapping-key` registra la clave y una segunda ejecución también sale bien.
- La API key restaurada pasa la autenticación del código `v1.0.0`; una inventada da 401.

**No ensayado:** contra un volcado real de prod, el purgado de RabbitMQ/Redis y el rollback con `--create`.
Los pasos de despliegue (`deploy-signer`, `deploy-prod`…) son los del runbook.

## Cuándo

- Fuera de las 03:15 (backup del cron) y sin solapar con las 04:50 (chequeo del bucket).
- Calcula unos 20-30 min de ventana con el servicio caído. El tiempo depende sobre todo de `backup-prod`
  y `migrate-prod`.

---

## Antes de empezar en prod: lo que falló en dev (2026-11-06/07)

Todo esto se comprueba **con tráfico**, antes de la fase 1. Cada punto le pasó al host de dev.

1. **El checkout de infra en `master`.** Un `master` local con el historial anterior a la reescritura da
   *"unrelated histories"*: `git status -sb` debe decir `## master...origin/master`. Si no:
   `git branch old-master-pre-rewrite master && git checkout -B master origin/master`.
2. **Acceso al GHCR del backend.** La imagen sigue en el paquete personal (`ghcr.io/dpeite-innatial/…`):
   `docker manifest inspect ghcr.io/dpeite-innatial/f5sign-backend:v1.0.0 >/dev/null && echo OK`.
   Un `denied` aquí corta el `pull-prod` entero.
3. **`.env.prod` rehecho con `make env-prod-merge`** (P2), y después:
   - `BACKEND_TAG=v1.0.0` (en dev el merge dejó `develop`);
   - **sin** `COMPOSE_PROFILES` (el sink `messagepit` es solo para hosts de prueba);
   - `MAILER_DSN` y `SMS_DSN` de verdad, no los del MessagePit.
4. **El sello.** `make seal-check-prod`: en prod tiene que salir TU certificado. Si sale
   `O=European Commission, OU=PKI-TEST`, prod firma con la clave de demo y `deploy-prod` se parará en
   su preflight: decide antes qué hacer, no dentro de la ventana. Comprueba también que existen los dos
   ficheros, porque sin el segundo el `up` se corta a mitad (pasó en dev):
   `sudo ls -l /etc/f5sign/keystore/seal.p12 /etc/f5sign/secrets/seal-password`.
5. **Dónde viven los datos de Postgres.**
   `docker inspect f5sign-postgresql --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}  {{end}}'`
   - `/srv/f5sign/pgdata -> /var/lib/postgresql/data`: bien, ya está en el bind mount.
   - `f5sign_pg-data`: prod sigue en el volumen viejo. **Para y avisa**; dev se resolvió con otro camino
     (clúster nuevo) que en prod no se ha planteado.
   - ⚠ El preflight de pgdata da un **falso positivo** si tu usuario no puede leer la carpeta (es de
     Postgres, `700`). Compruébalo con `sudo cat /srv/f5sign/pgdata/PG_VERSION` (tiene que dar `18`).
     Solo si da `18` y el mount es el bind, en V12 usa `make deploy-prod PGDATA_PREFLIGHT=0`.
6. **pgBackRest en verde** (`make pgbackrest-status-prod`). Y **nada del bucket `f5sign-prod-backups`
   se toca a mano** (Cyberduck lo vació el 2026-11-06; se recuperó, ver memoria de la sesión).

## Fase 0 — Variables de shell (en el host, en el checkout de infra)

```bash
{
cd ~/f5sign-infra
DC="docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml"
PGU=$(sed -nE 's/^POSTGRES_USER=(.*)$/\1/p' .env.prod | tr -d '\r')
PGD=$(sed -nE 's/^POSTGRES_DB=(.*)$/\1/p' .env.prod | tr -d '\r')
PSQL="$DC exec -T postgresql psql -v ON_ERROR_STOP=1 -U $PGU"
B=$HOME/f5sign-backups; mkdir -p $B
echo "PGU=$PGU PGD=$PGD"          # que no salgan vacías
} </dev/null
```

**Apunta los tags actuales**, porque son la vuelta atrás:
```bash
{
grep -E '^(BACKEND|SIGNER)_TAG=' .env.prod | tee $B/tags-antes-v1.0.0.txt
} </dev/null
```

---

## Fase 1 — Preparación (con tráfico, nada de esto corta el servicio)

### P1. Actualizar el checkout de infra
```bash
{
git pull               # master; NO checkout de v1.0.0: la tag no lleva env-prod-merge (P2)
git log -1 --oneline   # 54e8569 o posterior
} </dev/null
```
- **Qué:** trae los targets nuevos (`wrapping-key-prod`, `register-wrapping-key-prod`,
  `rabbit-topology-prod`), el compose de prod y `definitions.json` con la cola `queue.evidenceaudit.events`.
- **Por qué:** todo sale de este checkout. Uno viejo arrancaría el worker contra la topología antigua, y
  sin la cola nueva el worker deja de leer **todas** las colas, no solo esa.
- ⚠ Si `git pull` aborta por `CLAUDE.md`, es el symlink con skip-worktree.

### P2. `.env.prod`

Primero, rehazlo sobre la plantilla limpia (el layout actual ya no coincide con `.env.prod.example`):
```bash
{
cp -p .env.prod .env.prod.bak-$(date +%Y%m%d)
make env-prod-merge          # escribe .env.prod.new; informa solo de NOMBRES de claves
} </dev/null
```
Del informe:
- **NEW**: deberían ser las tres de la tabla de abajo.
- **Only in the old file**: claves retiradas, que el script deja al final. Bórralas o pregunta.
- **Still CHANGE_ME**: más allá de `ALERT_EMAIL_TO`, JWT, SendGrid, Twilio y Stripe, cualquier otra
  (contraseñas de Postgres, S3, `SESSION_CREDENTIAL_SECRET`…) significa que el fichero viejo no la tenía o
  la tenía con otro nombre. **No sigas hasta aclararlo.**

Edita `.env.prod.new` con la tabla de abajo y luego:
```bash
{
make config-prod PROD_ENV=.env.prod.new     # verde
mv .env.prod.new .env.prod
} </dev/null
```

| Variable | Valor | Por qué |
|---|---|---|
| `BACKEND_TAG` | `v1.0.0` | La release |
| `COPY_READ_CREDENTIAL_SECRET` | `openssl rand -hex 32`, **distinto** de los demás | Firma los enlaces de copia de solo lectura del destinatario |
| `NOTIFICATION_COPY_BASE_URL` | `https://<SERVER_NAME_SIGN>/c` | Base del enlace que va en cada aviso |
| `ALERT_EMAIL_TO` | tu correo | Alertas del cron (no bloquea el arranque) |
| `WRAPPING_KEY_DIR` | solo si no quieres `/etc/f5sign/wrapping-key` | Dónde vive la clave de Key Management |

`SIGNER_TAG` **todavía no**: se cambia en P8.

- **Por qué van primero:** `COPY_READ_CREDENTIAL_SECRET` y `NOTIFICATION_COPY_BASE_URL` son `:?` en el
  compose. Si faltan, falla **cualquier** comando de compose, incluido `deploy-signer`.

### P3. Validar el render
```bash
{
make config-prod PROD_ENV=.env.prod
} </dev/null
```
- **Qué:** renderiza el compose de prod sin arrancar nada.
- **Por qué:** una variable que falte la nombra aquí, no dentro de la ventana. **Tiene que salir verde.**

### P4. Ensayo de backup
```bash
{
make backup-prod LABEL=ensayo
} </dev/null
```
- **Qué:** `pg_dump` verificado (tamaño mínimo + `pg_restore -l`). Si no pasa, borra el fichero.
- **Por qué:** comprueba credenciales, disco y mecanismo con tráfico, para no descubrirlo en la ventana.
  **No es la copia de rollback**: esa es `corte` (V2).

### P5. Descargar imágenes
```bash
{
make pull-prod
} </dev/null
```
- **Qué:** baja las imágenes de la release sin tocar lo que corre.
- **Por qué:** saca la descarga de la ventana.
- Si falla porque aún no existen los ficheros de la wrapping key: `docker pull` de la imagen del backend
  `v1.0.0`, haz P6 y repite este paso.

### P6. Generar la wrapping key
```bash
{
sudo make wrapping-key-prod
sudo ls -l /etc/f5sign/wrapping-key     # wrapping_key_public, wrapping_key_pair (600), wrapping_key_id
} </dev/null
```
- **Qué:** genera el par de claves de Key Management y su id, con la imagen de la release. Nunca
  sobrescribe un fichero.
- **Por qué:** compose no arranca un servicio al que le falta el fichero de un secret, así que sin esto
  no arranca ni `migrate-prod`.

### P7. ⛔ Backup de secretos, y sacarlo del host
```bash
{
sudo make backup-secrets BACKUP_DIR=$HOME/f5sign-backups && sudo chown -R $(id -un): $HOME/f5sign-backups
# copia el bundle fuera del host (scp a tu máquina) y guarda su PASS
} </dev/null
```
- **Qué:** un bundle cifrado con `.env.prod`, el sello, los certificados, `caddy.d` y la wrapping key.
- **Por qué:** **es lo único irreversible del despliegue.** Si se pierde `wrapping_key_pair`, todo lo que el
  backend cifre queda ilegible para siempre, en la base de datos y en cada backup. No sigas sin tener el
  bundle fuera del host.

### P8. Signer primero
```bash
{
# .env.prod: SIGNER_TAG=v1.0.0
make deploy-signer
} </dev/null
```
Abre **en el navegador** `https://<SERVER_NAME_SIGN>/c/cualquiercosa`: tiene que salir la pantalla de copia,
no el not-found del signer. Un código 200 no prueba nada, porque una SPA responde 200 a cualquier ruta.
- **Qué:** despliega solo el signer, sin tocar el backend.
- **Por qué antes:** cada aviso del backend nuevo lleva un enlace a `/c/:link`. Con el backend primero,
  se manda por correo un enlace a una página que no existe.

---

## Fase 2 — Ventana de corte (servicio caído)

### V1. Cortar todo lo que habla con Postgres
```bash
{
$DC stop caddy
make worker-down-prod
$DC stop php-fpm worker relay custodian
$PSQL -d postgres -Atc "SELECT datname, usename, application_name FROM pg_stat_activity WHERE datname = '$PGD'"
# sin filas = nadie conectado
} </dev/null
```
- **Qué:** sin tráfico y sin procesos de la app.
- **Por qué:** `DROP DATABASE` (V5) se niega mientras haya conexiones. Aquí no hace falta drenar colas:
  lo que llevan se va a tirar.

### V2. ⛔ Copia `corte`
```bash
{
make backup-prod LABEL=corte
ls -l $B/*-corte.dump
} </dev/null
```
- **Qué:** la copia completa del estado viejo, ya sin escrituras.
- **Por qué:** **es la única vuelta atrás** si algo falla de aquí a V10. Tiene que ser de hoy y de ahora.

### V3. Volcar lo que se conserva
```bash
{
$DC exec -T postgresql pg_dump -U $PGU -d $PGD --data-only --column-inserts --disable-triggers \
  -t identity.tenant -t identity.api_client -t identity.api_key -t notification.tenant_default \
  > $B/keep-tenants.sql
grep -c '^INSERT' $B/keep-tenants.sql
grep '^INSERT INTO identity.tenant' $B/keep-tenants.sql
} </dev/null
```
**Para aquí** si está vacío o falta algún tenant.
- **Qué:** solo los datos (sin esquema) de las cuatro tablas, como `INSERT` con nombres de columna.
- **Por qué con nombres de columna:** el esquema de `v1.0.0` no es el de `v0.0.2` (V7).

### V4. Huella de lo volcado
```bash
{
cat > $B/fingerprint.sql <<'EOF'
SELECT 'tenant', count(*), md5(string_agg(id::text, '|' ORDER BY id)) FROM identity.tenant
UNION ALL SELECT 'api_client', count(*), md5(string_agg(t::text, '|' ORDER BY t::text)) FROM identity.api_client t
UNION ALL SELECT 'api_key', count(*), md5(string_agg(t::text, '|' ORDER BY t::text)) FROM identity.api_key t
UNION ALL SELECT 'tenant_default', count(*), md5(string_agg(t::text, '|' ORDER BY t::text)) FROM notification.tenant_default t;
EOF
$PSQL -d $PGD -At < $B/fingerprint.sql | tee $B/keep-tenants.before
} </dev/null
```
- **Por qué:** en V7 se compara con lo restaurado. Si `api_key` coincide, la key que tienen los clientes
  sigue valiendo. En `tenant` solo se compara el id, porque la fila gana una columna.

### V5. Recrear la base de datos
```bash
{
$PSQL -d postgres -c "DROP DATABASE $PGD"
$PSQL -d postgres -c "CREATE DATABASE $PGD OWNER $PGU"
} </dev/null
```
- **Qué:** una base de datos vacía con el mismo nombre. Los roles son del clúster y sobreviven.
- **Por qué no borrar tabla a tabla:** es más simple y no deja restos de esquemas viejos.
- **Qué se pierde y repone V6:** los `GRANT CONNECT` y `ALTER DATABASE … SET app.current_tenant_id`,
  que son de la base de datos.

### V6. Roles y permisos de la base de datos
```bash
{
make init-roles-prod
$PSQL -d $PGD -Atc "SELECT array_to_string(datacl,' ') FROM pg_database WHERE datname='$PGD'"
# deben aparecer f5sign_app, f5sign_relay, f5sign_identity, f5sign_provisioning con =c
} </dev/null
```
- **Qué:** ejecuta `init-app-role.sh`. Crea los roles que falten, entre ellos el nuevo
  `f5sign_notification_custodian`, y vuelve a aplicar los permisos de V5. Es idempotente.
- **Por qué antes de migrar:** una migración que necesita un rol que no existe falla, y debe fallar,
  porque crearla sin él dejaría objetos del superusuario saltándose el RLS.

### V7. Migrar desde cero
```bash
{
make migrate-prod
make migrate-status-prod      # "Already at latest version"; la última, Version20261029084859
} </dev/null
```
- **Qué:** las 81 migraciones, desde un contenedor efímero de la imagen `v1.0.0`, sin desplegarla.
- **Por qué `migrate-status-prod` y no otra cosa:** consulta con el rol owner. Preguntando con `make sf`
  responde "0 ejecutadas" sobre una base de datos que está al día.

### V8. Reinsertar los tenants y comparar
```bash
{
{ echo "ALTER TABLE identity.tenant ALTER COLUMN sms_notifications_enabled SET DEFAULT false;"
  cat $B/keep-tenants.sql
  echo "ALTER TABLE identity.tenant ALTER COLUMN sms_notifications_enabled DROP DEFAULT;"
} | $PSQL -1 -d $PGD

$PSQL -d $PGD -At < $B/fingerprint.sql > $B/keep-tenants.after
diff $B/keep-tenants.before $B/keep-tenants.after && echo "HUELLAS IDENTICAS"
} </dev/null
```
- **Qué:** los `INSERT` de V3, en una sola transacción (`-1`): o entra todo o no entra nada.
- **Por qué el `SET DEFAULT` / `DROP DEFAULT`:**
  - `v1.0.0` añadió `identity.tenant.sms_notifications_enabled` como `NOT NULL` sin default
    (`Version20261013075329`).
  - El volcado de `v0.0.2` no la trae, así que sin el truco la restauración falla (medido).
  - Dar `false` es lo mismo que hizo la migración con las filas que ya existían.
  - Al terminar se quita el default y el esquema queda igual que tras migrar.
- **Consecuencia:** los tenants quedan con SMS desactivado. Si alguno debe tenerlo, se activa después.
- **Si `diff` muestra diferencias: no sigas.** Revisa antes de V9.

### V9. Registrar la wrapping key
⚠ **Este va SOLO, sin llaves `{ }`.** Usa `docker compose run` sin `-T` y necesita terminal:
dentro de un bloque falla con *the input device is not a TTY* sin hacer nada (pasó en dev).
```bash
make register-wrapping-key-prod
```
- **Qué:** registra la clave pública de P6 en Key Management, dentro de la base de datos nueva.
- **Por qué:** sin el registro, el backend rechaza sobres nuevos, documentos, anulaciones con motivo y
  rechazos, porque cada uno cifra su texto. Se puede volver a ejecutar sin problema.

### V10. Vaciar RabbitMQ y Redis
```bash
{
for q in $($DC exec -T rabbitmq rabbitmqctl -q list_queues name | grep -v '^name$'); do
  echo "purge $q"; $DC exec -T rabbitmq rabbitmqctl -q purge_queue "$q"; done
$DC exec -T rabbitmq rabbitmqctl -q list_queues name messages    # todo a 0
$DC exec -T redis redis-cli FLUSHALL
} </dev/null
```
- **Por qué RabbitMQ:** los mensajes encolados, incluido `queue.failed`, apuntan a filas que ya no existen
  y están serializados con las clases viejas.
- **Por qué Redis:** las claves de idempotencia devolverían respuestas cacheadas de sobres borrados ante el
  reintento de un cliente. Lo demás es caché, locks y rate limits, todo prescindible.

### V11. Punto de decisión: la API sola, sin tráfico
```bash
{
$DC up -d --wait php-fpm
$DC exec -T php-fpm ls /run/secrets      # NO debe aparecer wrapping_key_pair
} </dev/null
```
- **Qué:** arranca solo el proceso de la API, con caddy parado y sin workers.
- **Por qué:** demuestra que la release arranca y que su configuración se sostiene, y que solo `worker`
  podrá descifrar.
- **Mal → rollback (abajo).** Bien → V12.

### V12. Desplegar todo y reabrir
```bash
{
make deploy-prod
} </dev/null
```
- **Qué:** preflight de pgdata, pull, importa y verifica la topología de RabbitMQ (con la cola nueva) y
  hace `up -d` de todo. Caddy vuelve.
- **Por qué `deploy-prod` y no `deploy-backend`:** `deploy-backend` no actualiza el relay.

**Aquí se cierra la ventana. A partir de ahora no hay rollback: se arregla hacia delante.**

---

## Fase 3 — Comprobaciones

```bash
{
make migrate-status-prod        # latest
make worker-status-prod         # worker, relay y custodian Up; la columna consumers sale SIEMPRE a 0 (polling)
$DC ps                          # todo up / healthy
SN=$(sed -nE 's/^SERVER_NAME_API=(.*)$/\1/p' .env.prod | tr -d '\r')
curl -sS -o /dev/null -w '%{http_code}\n' "https://$SN/api/doc.json"   # 200
$DC exec -T eu-dss /usr/local/bin/wait-for-tl.sh 300    # Trusted Lists cargadas
make seal-check-prod            # firma con TU sello, no con el demo
for s in php-fpm relay custodian worker; do echo "== $s"; $DC exec -T "$s" ls /run/secrets; done
# wrapping_key_pair solo bajo worker
make pgbackrest-status-prod     # ESTADO: verde
} </dev/null
```

- **Comprobación de cliente:** una llamada real del dashboard de factor5 con su API key de siempre. Tiene
  que autenticar sin tocar nada.
- **Opcional, porque es una acción real en prod:** crea un sobre desechable, recházalo y lee el motivo en
  el audit trail. Demuestra que se cifra y que `worker` descifra.

### Después

```bash
{
make backup-full-prod
} </dev/null
```
- **Opcional.** Hace que el estado limpio sea el punto de partida de pgBackRest. Sin ella, una restauración
  partiría de la full del domingo anterior y reaplicaría todo el WAL desde entonces, limpieza incluida.
  Funciona, pero es más lento y depende de más WAL.
- El PITR hacia antes de la limpieza sigue disponible durante `PGBACKREST_RETENTION_DAYS` (30 días por
  defecto). ⚠ Sustituye la base de datos **entera**. Para recuperar algo suelto, carga `-corte.dump` en un
  contenedor aparte.

**Sobre el object storage:** los ficheros de los sobres viejos se quedan en los buckets sin nada que los
referencie. Los que tienen Object Lock en COMPLIANCE no se pueden borrar hasta que venza su retención. No
molestan al backend.

---

## Rollback (solo entre V1 y V11)

```bash
{
$DC stop php-fpm worker relay custodian
PGPW=$(sed -nE 's/^POSTGRES_PASSWORD=(.*)$/\1/p' .env.prod | tr -d '\r')
$DC exec -T -e PGPASSWORD=$PGPW postgresql \
  pg_restore -U $PGU -d postgres --clean --if-exists --create < "$(ls -t $B/*-corte.dump | head -1)"
# .env.prod: BACKEND_TAG y SIGNER_TAG a los valores de $B/tags-antes-v1.0.0.txt
make deploy-prod
} </dev/null
```
- **`--create` desde la base `postgres` es obligatorio.** Ni `make restore-prod` (reaplica el WAL hasta el
  final, es decir, hasta el estado limpio) ni un `pg_restore` sin `--create` te devuelven al estado viejo.
- **No borres la wrapping key** (`/etc/f5sign/wrapping-key`) aunque vuelvas atrás. Nunca generes otra
  para una base de datos que pueda tener valores cifrados.
- ⚠ No ensayado: el backend `v0.0.2` con el checkout de infra `v1.0.0`. El compose nuevo le monta secretos
  y variables que el código viejo ignora, así que debería arrancar, pero no se ha medido. Si no arranca,
  `git checkout v0.0.1` del repo de infra y `make deploy-prod`.
