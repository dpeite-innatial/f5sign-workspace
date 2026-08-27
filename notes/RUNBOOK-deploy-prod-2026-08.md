# RUNBOOK — Despliegue a producción, agosto 2026

**Rango:** `f5sign-backend` `403813c` (2026-07-20, último commit de Miguel Melón) → `develop` `e3eec4e` (2026-08-26).
**Tamaño:** 366 commits · 28 migraciones nuevas · 5 semanas.
**Redactado:** 2026-08-26, por la sesión de backend con datos de la sesión de infra.

> **Veredicto: esto es una ventana de corte con downtime.** No hay ordenación rolling que
> funcione. El código viejo se rompe *después* de migrar (6 migraciones no aditivas) y el
> código nuevo se rompe *antes* de migrar (TASK-034 / BL-39). No hay solape válido.

**Leyenda de avisos**

| Marca | Significado |
|---|---|
| ⛔ | Irreversible o pérdida de datos. No se arregla repitiendo el paso. |
| ⚠ | **Falla en silencio**: sale verde y está mal. Lo más caro de este despliegue. |
| ✅ | Verificado leyendo los repos en esta sesión. |
| ◻ | Reportado por infra, **pendiente de verificar en el host de producción**. |

---

## 1. Bloqueadores a resolver ANTES de programar la ventana

Ninguno de estos se resuelve dentro de la ventana. Si alguno está mal, no hay despliegue.

### 1.0 ✅ RESUELTO — un reto de FIRMA verificado ya no sobrevive a su propio plazo

**Arreglado y en `develop` el 2026-08-26** (`9708009`, mergeado en `e3eec4e`). Ya no bloquea.

- Pasado `expires_at`, el acto se rechaza con `AUTH_CHALLENGE_EXPIRED`.
- Volver a pasar la puerta de ACCESO retira una prueba de FIRMA retenida (decisión de producto
  del 2026-08-26, sobre la alternativa más estrecha de dejar que solo el TTL la acotara).
- Ambas guardas verificadas por sabotaje: cada una cae, sola, por su propio motivo.
- Verde en el lane: `lint 0 de 1018` · `Deptrac 0` · PHPStan L9 `[OK]` ·
  `OK (2405 tests, 11470 assertions)`.
- ⛔ **El signer SÍ necesitó cambio, y yo dije que no.** Corregido el 2026-08-26: este bloque
  afirmaba *"el signer no necesita cambio alguno"* porque los dos códigos figuran en
  `useSignerNavigation.ts`. Esa tabla es el **último recurso**; la ruta del commit
  (`useSignFlow.ts`) lee códigos concretos **antes** de caer a ella.
  `AUTH_NO_OPEN_CHALLENGE` tenía rama propia → modal, correcto. `AUTH_CHALLENGE_EXPIRED` caía
  al genérico → **navegación de página**, y la firma y las evidencias viven en RAM: el
  firmante tenía que recapturarlo todo y hacer **dos ceremonias completas** para una firma. Un
  200 indebido convertido en ceremonia abandonada.
  ✅ Arreglado en `f5sign-signer` `cbbfaca` (ambos códigos al modal; verde con lint, typecheck
  y 2385 unit). ⚑ **Ese despliegue del signer va acoplado a éste**: el backend sin el signer
  nuevo degrada la ceremonia de firma.

⛔ **Lo que NO cierra, y sigue abierto: la mitad de TRANSFERENCIA de `BL-159`.** La prueba
sigue ligada a la *sesión* y no a quien contestó, así que bajo `(access: OPEN, signing:
ACCESS_CODE)` una segunda parte que no vuelva a pasar ACCESO puede gastar una prueba que ganó
la primera. La cascada estrecha la ventana; no la cierra. `BL-197` registra la forma que
acabaría con la clase entera —fundir la verificación en el commit— y por qué es un cambio de
contrato con el signer y no una guarda.

⚑ **Y una lección sobre este propio documento.** Lo registré aquí como hallazgo nuevo del
signer, y no lo era: `BL-159` lo llevaba desde el 2026-08-19, de una auditoría de seguridad,
con la reparación exacta escrita, y `ADR-0049` lo nombraba en su fila de estado como límite
abierto conocido. Hizo falta que la sesión del signer lo topara **empíricamente en un stack
vivo** para que se arreglara. Un hallazgo de auditoría aparcado una semana y un reporte de
campo del mismo defecto son el mismo hecho llegando dos veces; el segundo es el que mueve.

---

**Lo que decía este bloque antes del arreglo, conservado porque explica el defecto:**

Reportado por la sesión de `f5sign-signer` el 2026-08-26
(`notes/HANDOFF-signing-challenge-no-expiry.md`) y ✅ **confirmado en el código de este repo**:

[`SigningSession::consumeSigningChallengeFor()`](../f5sign-backend/src/F5Sign/Session/Domain/Aggregate/SigningSession.php)
filtra por `AuthChallenge::isVerifiedAndUnspent()`, que es `verifiedAt !== null &&
consumedAt === null` y **no mira `expiresAt`**. El helper que sí lo mira, `isLive()`, cubre el
camino de emisión/verificación (`liveChallengeFor()`) pero **no el de consumo**. El reto caduca
para poder abrirse otro, no para gastarse.

Medido en el stack local: `verified_at=07:40:37` · `expires_at=07:55:28` ·
`consumed_at=09:10:07`. Una firma autorizada con una prueba de hora y media antes, con seis
pasos de la puerta de ACCESO en medio que no la tocaron, y sin que al firmante se le pidiera
código.

⚑ **No está en producción**: `AuthChallenge.php` no existe en `master` y las tres migraciones
de `session.auth_challenge` (`Version20260818000007`, `20260820000004`, `20260824000002`) son
de las 28 nuevas. **El mecanismo entero entra con este despliegue.** No hay nada que remediar
en prod ni firmas comprometidas ya emitidas — pero si sale tal cual, sale con el defecto.

**Las tres decisiones de producto, resueltas el 2026-08-26:**
1. El límite es el `expires_at` del reto — no una ventana de retención propia, que habría
   añadido un segundo plazo que elegir sin datos.
2. Sí: volver a pasar ACCESO invalida una prueba de FIRMA retenida. ⚠ Coste aceptado a
   sabiendas — un firmante que reabra su enlace en otra pestaña pierde una prueba legítima y
   tiene que pedir otro código.
3. `AUTH_CHALLENGE_EXPIRED`, que ya existía y el signer ya enrutaba. Sin coordinación
   necesaria y sin riesgo de caer a `/invalid`.

### 1.1 ⛔◻ El volumen de Postgres cambió de forma

`09ec6e2` de infra movió pgdata de *named volume* a *bind mount* del host
(`PGDATA_HOST_DIR`, default `/srv/f5sign/pgdata`).

Si producción sigue corriendo con el named volume `f5sign_pg-data`, un `deploy-prod`
recrea postgres apuntando a un **directorio vacío** → `initdb` sobre disco nuevo. La base
de julio no se borra (sigue viva en el volumen) pero **el stack arranca con una BD vacía**,
y eso a las 3 de la mañana se parece exactamente a una pérdida total.

**Comprobar en el host, antes de nada:**

```bash
docker volume ls | grep pg-data
ls -la /srv/f5sign/pgdata 2>/dev/null | head
docker inspect <contenedor-postgres> --format '{{json .Mounts}}' | python3 -m json.tool
```

Si el bind mount está vacío y el volumen tiene datos: **migración manual de datos con el
stack parado**, antes de tocar nada más. `pg_dump` desde el contenedor viejo, o copia
directa del volumen al directorio del host.

### 1.2 ⛔◻ nginx ya no existe — es Caddy, y necesita certificados en el host

`881e5ae` sustituyó la capa web entera. Caddy **no arranca sin**:

- `/etc/f5sign/certs/fullchain.pem`
- `/etc/f5sign/certs/privkey.pem`
- `/etc/f5sign/caddy.d` (aunque esté vacío)

No hay autofirmado de respaldo, y es deliberado. Sin esto no hay API.

### 1.3 ⛔◻ El signer es dependencia dura de la API

Aunque el signer no sea prioridad de este despliegue:

- `SIGNER_TAG` es fail-closed (`:?`) → `deploy-prod` no arranca sin él.
- `caddy` tiene `depends_on: signer: service_healthy` → **si el signer no pone healthy,
  Caddy no arranca y la API tampoco.**

Hay que tener una imagen del signer publicada y sana. No es opcional.

### 1.4 ⚠ El `.env.prod` real del host puede venir de julio

`.env.prod.example` está actualizado (2026-08-20) y cubre todo. El riesgo no es el ejemplo,
es el fichero real del host.

**Diff obligado contra el ejemplo.** Variables nuevas desde el 2026-07-20:

`SESSION_CREDENTIAL_SECRET` · `ACCESS_CODE_PEPPER` · `SMS_DSN` · `RATE_LIMITER_DSN` ·
`MAILER_DSN` · `NOTIFICATION_FROM_EMAIL` · `NOTIFICATION_FROM_NAME` ·
`NOTIFICATION_SIGNING_BASE_URL` · `IDENTITY_DATABASE_URL` · `PROVISIONING_DATABASE_URL` ·
`CORS_ALLOWED_ORIGINS`

Cuatro avisos concretos:

- ⚠ **`S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` fallan *abiertas*.** No vienen del
  ancla de prod sino del compose **base**, con defaults de MinIO y `:-` en vez de `:?`. En
  prod no hay MinIO: el stack **arranca bien** y revienta en el primer upload con un 500
  tipo *"Could not contact remote server"*. Es la única del conjunto que no falla al
  arrancar — o sea, la única que puedes desplegar sin enterarte.
- 💰 **`SMS_DSN` cuesta dinero de verdad.** Es la única variable del fichero que gasta por
  envío. Lleva el credencial del proveedor **y** la identidad del remitente en `?from=`.
- ⛔ **`ACCESS_CODE_PEPPER` es la de peor historia de rotación.** Rotarla invalida todos los
  hashes de códigos de acceso a la vez, sin rehash-on-verify, y cada remitente afectado
  tiene que reiniciar. Ponla bien a la primera.
- **`CORS_ALLOWED_ORIGINS` va vacío por defecto = rechaza todo cross-origin.** Sin el
  dominio del signer, el frontal se cae aunque el backend esté perfecto.

**No se inyectan (y hoy es correcto):**

- `FIELD_ENCRYPTION_SECRET` — está en `.env.prod.example` pero no en `x-backend-env`. Hoy no
  hay call sites (`FieldCipher`/`KeyProvider` sin llamantes, BL-171), y `AccessCodeHasher`
  usa `ACCESS_CODE_PEPPER`, no ésta. **Genérala y guárdala igual**: perderla no es
  reversible, y cuando aterrice el primer carrier hará falta.
- `DEPLOYMENT_MODE`, `DSS_TIMEOUT_SECONDS`, `DSS_MAX_RETRIES` — están en el ejemplo pero
  **no llegan a ningún contenedor**; gana el `.env` horneado en la imagen. Ponerlas en
  `.env.prod` no hace nada.

**Retirada:** `SIGNING_TOKEN_SECRET` ya no se lee (el token pasó a credencial opaca en BD,
BL-148). Si está en tu `.env.prod`, sobra. ⛔ No la reintroduzcas: `BACKEND_TAG` tiene que
ser ≥ el corte de BL-148, porque una imagen anterior aún la lee y revienta al construir el
contenedor. `develop` lo cumple. Y los enlaces de firma pre-corte que sigan en circulación
**se rechazan**.

---

## 2. Las 6 migraciones no aditivas

Barrido sobre el cuerpo de `up()` únicamente (los `down()` son destructivos por diseño y no
cuentan). ✅ Verificadas en el árbol.

| Migración | Operación | Por qué rompe el código viejo |
|---|---|---|
| `Version20260729000001` | `RENAME TO` | `signing_assignment` → `document_assignment` |
| `Version20260729000002` | `SET NOT NULL` + backfill | |
| `Version20260804000001` | `DROP CONSTRAINT`, `DROP COLUMN` | reshape de `field_occurrence` (ADR-0041) |
| `Version20260805000001` | `DROP CONSTRAINT`, `DROP COLUMN` | retira `ordinal` (ADR-0043) |
| `Version20260810000001` | `ALTER COLUMN ... TYPE` + datos | `sender_id`/`voided_by` de `UUID` a `TEXT` cualificado (`user:<uuid>`, ADR-0046) |
| `Version20260820000005` | `SET NOT NULL` + backfill | |

Y en la dirección contraria, **TASK-034 exige migrar antes de desplegar**: el repositorio de
lectura nuevo nombra columnas nuevas en su `SELECT`, así que el código nuevo contra el
esquema viejo revienta `GET /api/v1/envelopes/{id}` en el acto. Registrado en **BL-39**.

---

## 3. ⚠ Las tres trampas que salen verdes

Éstas son las que hay que tener delante durante la ventana.

> ✅ **Las dos primeras están arregladas y pusheadas** (`f5sign-infra` `origin/master`,
> `f13aafd..2a228db`, 2026-08-26). ⚠ **Pero el arreglo sólo llega al host cuando alguien hace
> `git pull` allí.** Hasta ese `pull`, las trampas siguen vivas tal cual se describen abajo, y
> las descripciones se conservan por eso: no son historia, son el estado del host mientras no
> se actualice. Comprobación en §7.

### 3.1 ⚠ `migrate-prod` antes de desplegar **no falla: no hace nada** — CORREGIDO

La versión vieja hacía `exec` sobre el `php-fpm` **en marcha**. Ese contenedor sólo conoce las
4 migraciones de julio, ya aplicadas → *"Already at latest version"*, **exit 0**. Un no-op que
se lee como verde, y después el deploy te deja los 500.

✅ **Arreglado**: `migrate-prod` conserva el nombre y ahora hace
`run --rm --no-deps -u www-data` desde la imagen que apunta `BACKEND_TAG`, sin tocar el
contenedor que sirve tráfico. Verificado en el Makefile.

Dos cosas que infra verificó ejecutando, no razonando: `run --rm` **ignora el
`container_name`** del servicio (crea `<proyecto>-php-fpm-run-<hash>`, sin colisión con el que
sirve), y entra como **root** por defecto — por eso el `-u www-data` va dentro del target.

⚠ **Un runbook o README anterior que diga *"`migrate-prod` va siempre después de
`deploy-prod`"* es de antes de este cambio.**

### 3.2 ⚠⛔ `init-roles-prod` puede crear los roles nuevos con passwords de DESARROLLO — CORREGIDO

`init-app-role.sh` toma las passwords del entorno **del contenedor de postgres**, con
fallback al literal:

```sh
IDENTITY_PASSWORD="${POSTGRES_IDENTITY_PASSWORD:-f5sign_identity}"
PROVISIONING_PASSWORD="${POSTGRES_PROVISIONING_PASSWORD:-f5sign_provisioning}"
```

La versión vieja hacía `exec` sobre el contenedor en marcha, que se arrancó **antes** de que
el compose le pasara esas variables → no las tiene → cae al literal. (Infra lo confirmó:
`git show 16c290a^:docker-compose.yml` no las contiene. Un contenedor de julio no las tiene.)

⛔ Y como cada `CREATE ROLE` va tras `IF NOT EXISTS`, **repetir el comando no lo corrige**.
Una vez creado con la password floja hay que `ALTER ROLE ... PASSWORD` a mano.

✅ **Arreglado**: `init-roles-prod` ahora **se niega a correr** si alguna de las cuatro
`POSTGRES_{APP,RELAY,IDENTITY,PROVISIONING}_PASSWORD` falta en `.env.prod` o sigue en
`CHANGE_ME`, nombrándolas una a una; y cuando corre las inyecta **explícitas con `-e`** en vez
de confiar en el entorno del contenedor. Al terminar lista los roles `f5sign*` del cluster.
Verificado en el Makefile.

### 3.3 ⚠ Las 4 colas de eventos se quedan sin desvío, en silencio

`definitions.json` cambió el 2026-08-18 (`75595dc`) añadiendo `x-dead-letter-exchange` a las
cuatro colas de eventos. **Los argumentos de una cola son inmutables en RabbitMQ**, y
`import_definitions` **se queda con los viejos, no avisa y reporta éxito**.

Con el wrap de `MessageDecodingFailedException` que trae este despliegue, un mensaje
indescifrable se rechaza contra ningún desvío — y rechazar sin desvío es **descartar**.
Pérdida de eventos sin traza.

Y aparte: `definitions.json` llega **por bind-mount**, así que `up -d` no se entera de que
cambió. Sin `import_definitions`, la cola `queue.notification.events` (`f9f5ce7`) no existe y
el worker **muere en bucle** con `NOT_FOUND - no queue '...' in vhost '/'`.

---

## 4. Antes de la ventana (días, no horas)

- [ ] Resolver los cuatro bloqueadores de §1 en el host.
- [ ] `make -C ../f5sign-infra qa` sobre `develop` en el checkout principal. En verde.
- [ ] Diff de `.env.prod` real contra `.env.prod.example`. Rellenar lo que falte.
- [ ] Generar y guardar `SESSION_CREDENTIAL_SECRET`, `ACCESS_CODE_PEPPER`,
      `FIELD_ENCRYPTION_SECRET` en el gestor de secretos.
- [ ] ⚠ **El dump que uses aquí NO es el backup de la ventana.** Sirve para probar la cadena
      de migraciones; como suelo de rollback caduca en cuanto prod acepta una escritura más.
      Los dos `backup-prod` de §5 se hacen **el día que se abre la ventana**, sin excepción.
- [ ] **Ensayo completo**: dump de prod → cluster limpio → cadena entera de las 28
      migraciones. **No hay preprod** (TASK-034 lo declara; los entornos son `dev`/`test`/`prod`
      y "preprod" es este mismo stack con `BACKEND_TAG=develop`). Este ensayo *es* el preprod.
- [ ] `make release-backend` — build + push de la imagen. Fijar `BACKEND_TAG` y `SIGNER_TAG`.
- [x] ✅ Infra: targets `*-prod` pusheados (`f13aafd..2a228db`, 2026-08-26).

- [ ] ⛔ `git pull` en el `f5sign-infra` del host **desde la rama
      `feat/caddy-tls-modes-letsencrypt`, NO desde `master`** (§7). Verificar después:
      `grep -c preflight-prod Makefile` > 0 **y** `grep -c CHANGE_ME .env.prod.example` = 31.
- [ ] `make config-prod PROD_ENV=.env.prod` → en verde.

---

## 5. La ventana

Todo desde `f5sign-infra` en el host, con `.env.prod` presente. Los targets `*-prod` llegaron
el 2026-08-26 — si `make preflight-prod` no existe, el host no los tiene todavía (ver §3).

**0. Preflight de pgdata** (§1.1). Es prerequisito automático de `deploy-prod` y `up-prod`,
pero córrelo suelto primero para enterarte **antes** del corte, no en mitad de él.

```bash
make preflight-prod
```

Se pone rojo en una sola condición, las dos a la vez: `PGDATA_HOST_DIR` sin `PG_VERSION` **y**
el volumen `<STACK_NS>_pg-data` existiendo. Un cluster nuevo de verdad no tiene el volumen y
pasa; uno ya migrado tiene `PG_VERSION` y pasa. Si falla, imprime la receta de copia. Escape:
`PGDATA_PREFLIGHT=0` — no lo uses sin entender por qué saltó.

**1. ⛔ BACKUP nº1 — el ENSAYO. No es la copia de trabajo.**

Va aquí, con el tráfico arriba, y su único fin es **enterarte de que el mecanismo no funciona
antes de cortar**: credenciales mal, disco lleno, el contenedor sin `pg_dump`. Cuesta ~0,3 s
(medido por infra: 11 MB en dev, 0,30 / 0,27 / 0,27 s en tres corridas) y prueba la cadena
entera. De paso deja un suelo.

```bash
make backup-prod LABEL=ensayo     # → f5sign-<fecha>-<hora>-ensayo.dump
```

⛔ **No la borres por redundante y no restaures ésta.** La que vale es la del paso 4, que sale
con `-corte` en el nombre. **Pasa siempre el `LABEL`**: es lo que hace que el fichero diga por
sí solo cuál es, en vez de obligarte a comparar dos marcas de tiempo largas justo cuando peor
se compara.

⚑ En el `Makefile` **`LABEL` es opcional, y no es un desajuste con este "siempre"**: el target
lo comparte con el release aditivo, que hace una sola copia y no tiene nada que desambiguar.
La obligatoriedad vive aquí, en el procedimiento de la ventana de corte, que es el único que
sabe que hay dos.

Antes, si quieres saber a qué escala juegas en prod:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml \
  exec -T postgresql psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -Atc "SELECT pg_size_pretty(pg_database_size(current_database()))"
```

**2. Imagen nueva en disco, tráfico intacto**

```bash
make pull-prod
```

⛔ **No lo quites por redundante.** Estrictamente no hace falta —los servicios llevan
`pull_policy: always`, así que `deploy-prod` y `migrate-prod` se traen la imagen solos—, pero
**su valor es *cuándo* corre, no que corra**: descargar cuesta lo mismo antes que después, y
la diferencia es si se paga con la ventana abierta.

**3. CORTE.** Parar `caddy`, no escalar `php-fpm` a 0: Caddy es el único edge (termina TLS,
habla FastCGI con php-fpm y proxya el signer), así que un contenedor apaga las dos superficies
a la vez y el estado es inequívoco. Parar php-fpm dejaría a Caddy sirviendo 502 y la SPA del
firmante cargando para fallar en cada llamada.

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml \
  stop caddy
make worker-down-prod
```

`worker` y `relay` reanudan solos después: el relay está checkpointeado y las colas son
durables.

**4. ⛔ BACKUP nº2 — LA BUENA. Es el único rollback que vas a tener.**

No hay targets de rollback. `migrate-prev` y `migrate-to` son **dev-only**, y con 6
migraciones no aditivas sus `down()` son destructivos por definición.

**Por qué va aquí y no antes del corte** (acordado con infra 2026-08-26; ambos documentos
coinciden): un `pg_dump` con tráfico vivo da un snapshot consistente, pero **a un instante
anterior al corte**, y las escrituras de ese hueco no están en él. En una plataforma de firma
eso es una firma que ocurrió, que el firmante vio confirmada, y que un restore haría
desaparecer. Un rollback que no te devuelve al estado del que partiste no es un rollback.
El coste —ventana más larga— es ruido a esta escala: ~0,3 s.

```bash
make backup-prod LABEL=corte      # → $BACKUP_DIR/f5sign-<fecha>-<hora>-corte.dump
```

⛑ **La que se restaura es la que pone `-corte` en el nombre.** La `-ensayo` del paso 1 es el
ensayo y le faltan todas las escrituras posteriores.

⚑ Cuando la base crezca hasta que el dump no se pague con la ventana abierta, la salida **no**
es adelantar la copia buena: es `pg_basebackup`/snapshot antes **más** este dump corto después
del corte.

El target verifica en cascada y ⛔ **borra el fichero si cualquiera falla**, para que no quede
nada con pinta de copia: (1) exit del `pg_dump`; (2) tamaño ≥ 1024 bytes; (3) `pg_restore -l`
sobre el archivo con ≥ 1 entrada. Además avisa si la TOC **no** contiene
`doctrine_migration_versions` — eso sólo es esperable en un cluster al que nunca se migró; en
cualquier otro caso significa que has hecho el dump **contra la base equivocada**. Al final
imprime la línea de `pg_restore --clean --if-exists` para restaurar: **guárdala**.

Lee la salida. Un `OK: <bytes>, <n> entradas, doctrine_migration_versions: si` es lo que
buscas.

**5. Roles nuevos — ANTES de migrar.** Tres se añadieron después del 2026-07-20 y un cluster
inicializado antes **no los tiene**: `f5sign_identity` y `f5sign_provisioning` (`16c290a`,
2026-08-13) y `f5sign_signing_token_custodian` (`1c95e83`+`715abd7`, 2026-08-18).
`f5sign_app`, `f5sign_relay` y `f5sign_log_writer` sí están.

```bash
make init-roles-prod
```

Se niega si falta alguna password o sigue en `CHANGE_ME` (§3.2), y al terminar lista los roles
`f5sign*`. **Comprobar en esa lista**: los seis están, y no hay un
`f5sign_signing_token_reader` huérfano — el custodian se llamó así durante ~un día
(2026-08-18) y el script es puramente aditivo, sin `DROP`.

Probar una conexión real con **cada** DSN antes de seguir.

**6. Migrar desde la imagen NUEVA**

```bash
make migrate-prod
```

Hace `run --rm --no-deps -u www-data` desde la imagen que apunta `BACKEND_TAG`, sin tocar el
contenedor que sirve tráfico. El `-u www-data` va dentro del target y ⛔ **no es cosmético**
(`da97092`): entrar como root crea `var/cache/prod/` con propietario root, y a partir de ahí
**toda** petición a la API responde 500 con *"Cannot rename ... Permission denied"* — un
síntoma que aparece después de un despliegue aparentemente bueno y no apunta a las migraciones
por ningún lado.

**7. Topología de RabbitMQ**

Mirar primero, que es barato y no toca nada:

```bash
make rabbit-check-dlx-prod
```

Si sale **rojo** (lo esperable si las 4 colas ya existen desde julio):

```bash
make worker-status-prod                    # confirmar profundidad 0
make rabbit-recreate-event-queues-prod     # borra + reimporta + verifica
```

El target se niega si alguna cola no está a cero e imprime la salida que toca. `FORCE=1`
asume la pérdida. Reimporta `definitions.json` **por STDIN desde el host** (el bind-mount se
ata al inode: tras un `git pull` el contenedor sigue viendo el fichero viejo) y verifica con
5 reintentos, porque el import es asíncrono.

⚠ Aunque el check salga verde, el import hace falta igual si `definitions.json` cambió: sin él
la cola `queue.notification.events` no existe y el worker muere en bucle.

**8. Desplegar todo y reabrir**

⛔ **`deploy-prod`, no `deploy-backend`.** `deploy-backend` hace `pull php-fpm worker` +
`up -d php-fpm worker`: **el relay se queda con la imagen vieja**, aunque la doc prometa que
`BACKEND_TAG` cubre los tres. Con un `RENAME` de tabla de por medio, un relay viejo contra el
esquema nuevo falla sin ruido.

```bash
make deploy-prod
```

**9. Recargar lo que llega por bind-mount** (si cambió el Caddyfile):

```bash
make reload-caddy
```

---

## 6. Después

- [ ] `make rabbit-check-dlx-prod` en verde — las 4 colas desvían.
- [ ] `make migrate-status-prod` — usa la URL de OWNER y `run`, no `exec`.
      ⚠ Si lo consultas con el **rol de aplicación** dirá `Executed 0` y las 32 como
      *not migrated* sobre una base al día. **No te fíes de esa cifra y no reacciones con un
      `reset-db`.** Por eso existe el target.
- [ ] `make worker-status-prod` — `worker` y `relay` arriba y consumiendo, profundidad bajando.
- [ ] Un envelope de prueba end-to-end: crear → enviar → abrir enlace → firmar.
- [ ] **Primer upload a S3** — es lo único que falla abierto (§1.4).
- [ ] Vigilar el log del rate limiter: **falla abierto** y loguea a `error` cuando su store no
      responde. Ese log *es* el control; no lo silencies.
- [ ] `GET /api/v1/envelopes/{id}` devuelve `first_opened_at` (TASK-034).

---

## 7. Abierto

- ⛔⛔ **PROD NO DESPLIEGA DE `master`. Despliega de `feat/caddy-tls-modes-letsencrypt`.**
  Descubierto el 2026-08-26 y confirmado por el usuario de infra. **Es la trampa más cara de
  todo este documento**, porque no falla ruidosamente: un `git pull` sobre la rama equivocada
  sale en verde y deja el host exactamente como estaba.

  Esa rama iba **24 commits por detrás de `master`**, no 2. Hasta el merge de hoy, el host no
  tenía:
  - ⛔ **las siete variables que el backend exige para arrancar** (`f13aafd`) —
    `SESSION_CREDENTIAL_SECRET`, `ACCESS_CODE_PEPPER`, `MAILER_DSN`, `NOTIFICATION_*`,
    `SMS_DSN`. Desplegar el backend nuevo contra ese compose es **500 en todo**, no una función
    degradada;
  - ⛔ `f5sign_signing_token_custodian` en `init-app-role.sh` (cinco roles, no seis) →
    `Version20260818000003/4/5` habrían fallado con *role does not exist*;
  - `RATE_LIMITER_DSN`, los `mem_limit`, la rotación de logs, el bind mount de pgdata, el DLX
    de las colas ni `check-event-dlx.sh`;
  - y `.env.prod.example` seguía llevando `SIGNING_TOKEN_SECRET`, retirada en `657abda`.

  ✅ **Resuelto**: `master` mergeado en esa rama y pusheado (`7af6128..a1fc0c6`). Verificado
  contra `origin/feat/caddy-tls-modes-letsencrypt`: contiene `master`, 31 `CHANGE_ME`,
  `preflight-prod`, `run --rm --no-deps` y el rol custodian.

  **Comprobar en el host tras el `git pull`.** Las tres, porque miden cosas distintas:
  ```bash
  git rev-parse --abbrev-ref HEAD        # feat/caddy-tls-modes-letsencrypt
  grep -c preflight-prod Makefile        # > 0   → preflight de pgdata + migrate-prod nuevo
  grep -c 'run --rm --no-deps' Makefile  # > 0   → (son dos intenciones; un cherry-pick
                                         #          podría traer una sin la otra)
  grep -c CHANGE_ME .env.prod.example    # = 31  → la plantilla está al día
  ```
  ⚑ **Lección que vale más que el arreglo**: durante horas los dos repos dimos por hecho que
  prod seguía a `master`. Ninguna verificación sobre `master` podía detectarlo, porque todas
  salían en verde. **Lo que lo cazó fue un dato del host** — tu `grep -c CHANGE_ME` dando 27
  donde el repo decía 31. Ante una discrepancia entre lo que dice el repo y lo que dice el
  host, **gana el host**.
- ⚠ **El mecanismo `run` se verificó contra el merge de DEV**, con imagen local
  `f5sign/backend:dev`. No se pudo ejercitar contra el merge de prod porque tira de GHCR y en
  la máquina de desarrollo no hay login. Del merge de prod sí está verificado que **renderiza**
  (`make config-prod`, exit 0) y qué variables recibe cada contenedor. **El primer
  `migrate-prod` real contra prod es el estreno del mecanismo** — hazlo con el backup ya hecho
  y verificado.
- **Sentry es nuevo** y está registrado en todos los entornos, pero `.env.prod.example` no
  lista ningún `SENTRY_*`. Hoy prod arrancaría **sin** Sentry — inerte, no roto (el DSN vacío
  es lo que desactiva el egreso). Si lo queréis: `SENTRY_DSN` + `SENTRY_ENVIRONMENT` (el
  `.env` commiteado dice `development`, que en prod miente).
- **Ramas sin mergear en `develop`**, por si se daban por incluidas:
  `docs/delegated-signature` (24 commits) · `docs/claimable-recipient` (4) ·
  `fix/adr-0058-rationale` (1) · `chore/issuer-census-pointers` (1).
- **Reparto de entorno**: `relay` recibe un juego más corto que `worker` (sin `DSS_BASE_URL`,
  sin `S3_*`, sin `SEAL_CERTIFICATE_PATH`). Si el relay empieza a necesitar S3 o DSS, hay que
  añadírselo.
