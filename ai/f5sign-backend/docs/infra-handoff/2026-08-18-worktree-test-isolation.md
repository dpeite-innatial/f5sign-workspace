# Traspaso a infra — dos sesiones contra el mismo clúster de Postgres producen rojos que se leen como defectos de código

| | |
|---|---|
| **Origen** | worktree `f5sign-backend-develop` · rama `feat/session-credential-and-refresh` · commit `f318c9e` · construyendo [TASK-029](../tasks/TASK-029-session-credential-and-refresh.md) |
| **Fecha** | 2026-08-18 |
| **Repo destino** | `f5sign-infra` (§1, §2 y §3) · la mitad de composer del §4 es nuestra y queda anotada para que las dos no se pisen |
| **Naturaleza** | cuatro hallazgos **medidos**, ninguno teorizado · **recomendaciones, no decisiones** |
| **Acción requerida** | ninguna es urgente salvo §1, que es la que cuesta horas por sesión paralela |
| **Status** | Pending |

Todo lo que sigue se midió el 2026-08-18 en el worktree `f5sign-backend-develop`. Los conteos de muestras
van pegados a cada afirmación a propósito: los cuatro hallazgos son intermitentes o ambientales, y un
snapshot no mide eso ([BL-140](../BACKLOG.md)).

⛔ **Antes de actuar sobre nada de esto, leer [§Lo que NO se ha verificado](#lo-que-no-se-ha-verificado).**
Esta sesión **no tenía `f5sign-infra` abierto**.

---

## 1. El caro: dos corridas de phpunit sobre el mismo clúster producen rojos falsos, y parecen defectos

### Lo que se observó

Con cinco subagentes trabajando en paralelo, la suite completa dio **9 fallos**, todos de la misma familia
—relay del event log y broker—:

`EventRelayTest` · `EventLogBrokerRoundTripTest` · `ReplayEventLogEventCommandTest` ·
`Scenario01SingleRecipientHttpTest` · `EnvelopeVerticalSliceTest`

Parecían defectos reales: concretos, con nombre, y verosímiles para una rama que toca autenticación de
sesión. **No lo eran. Era contención.**

### Cómo se estableció (A/B, no deducción)

| Prueba | Resultado |
|---|---|
| ¿Toca la rama el relay? `git diff origin/develop..HEAD -- src/F5Sign/Foundation/EventLog/` | **vacío**. En `tests/F5Sign/Foundation/Integration/` el único fichero tocado es `RouteAuthnDeclarationTest.php`, que no es del relay |
| `EventRelayTest` sola, desde un clúster verificado en reposo | **2/2 en verde** |
| la misma prueba **detrás** de un test nuevo que sí mantiene transacciones abiertas | 2/2 en verde |
| muestreo ×3 mientras corrían los agentes | 1 fallo · 2 fallos · verde — intermitente, **y con el número de fallos variando** |
| suite completa con todos los agentes parados, ×2 | **verde 2/2** (1675 tests, 7192 assertions) |

La variación del **conteo** entre muestras es la firma que descarta un defecto de código: un defecto no
cambia de cardinalidad entre corridas del mismo árbol.

### El mecanismo ya está escrito — no re-derivarlo

Es [**BL-138**](../BACKLOG.md), probado allí por A/B/C controlado. En una línea: `pg_snapshot_xmin` es de
**clúster**, así que una transacción abierta en **cualquier** base del clúster —incluida `postgres`, que no
contiene ninguna tabla nuestra— para el relay de otra base, y el relay reporta éxito sin drenar nada. La
regla que fija esa fila es la que importa aquí:

> **un clúster por sesión, no una base por sesión**

⚑ Y en producción esto es el relay **funcionando** ([ADR-0031](../adr/ADR-0031-event-log-store.md)): la
marca de agua existe para no relayar una fila cuya transacción no ha comitado. **No hay defecto de producto
que arreglar**, y BL-138 lo dice expresamente. Lo que falla es una suite que asume que es dueña del clúster.

### Qué significa para infra

Los lanes `wt-*` levantan **su propio contenedor `postgres-test`** — un clúster aparte —, así que **la forma
es la correcta**: hoy es el único mecanismo que aísla de verdad. El problema es que están cojos, y eso lo
dice la documentación del propio backend, en la **precondición 5** de
[`task-runner`](../../.claude/skills/task-runner/SKILL.md):

> Hoy levanta **solo postgres** (`docker-compose.wt.backend.yml` declara `postgres-test` + `php-fpm-wt` y
> nada más): los tests de storage **fallan** (`Could not resolve host: minio`) y los de broker se saltan.

y, sobre por qué muere:

> El lane mete `composer install` + migraciones + suite en el mismo proceso, que es la explicación probable.
> Si lo usas y muere, no lo leas como "los tests son lentos".

Tres carencias concretas, en el orden en que muerden:

- **(a) Falta el conjunto de dependencias.** Solo `postgres-test` + `php-fpm-wt`: sin MinIO los tests de
  storage fallan con `Could not resolve host: minio`, y los de broker se saltan. Un lane que falla y otro
  que salta son dos maneras distintas de no validar.
- **(b) Corre `composer test` y nada más.** Sin `lint`, `arch`, `phpstan` ni `infection`: los otros cuatro
  gates no tienen ruta consciente del worktree, y pasarlos por los targets del stack principal es
  exactamente la trampa que la precondición 5 existe para evitar (validan otro árbol y su verde no dice
  nada del tuyo).
- **(c) Muere en el *process timeout* de 300 s de Composer** — y el diagnóstico registrado **descarta** la
  duración de la suite: medida aparte tarda **~74 s** y los fallos de storage caen a los **~28 s**. Es el
  empaquetado en un solo proceso, no la lentitud.

### Recomendación

1. **Paridad de dependencias**: añadir al lane los servicios que la suite alcanza de verdad (MinIO seguro;
   RabbitMQ para que los tests de broker corran en vez de saltarse), o —si el coste por lane no lo permite—
   **decirlo explícitamente en el propio lane**, de forma que una corrida cojeando no se lea como verde.
2. **Partir `composer install` / migraciones / suite en procesos distintos**, para que un timeout no pueda
   matar la corrida entera y para que, cuando algo tarde, se sepa **qué** tardó.
3. **Ruta para los cuatro gates restantes**, aunque sea un target más; y si se decide no darla, que quede
   escrito, porque hoy la ausencia se descubre a mitad de una task.

### Qué compra

Una sesión en worktree pasa de *"acuérdate de que el lane está cojo y valida a mano contra el clúster
compartido"* a **aislamiento real**. Hoy el precio de no tenerlo son horas: los 9 fallos de arriba se
investigaron como defectos antes de establecerse que no lo eran, y esa investigación se repite entera en
cada sesión paralela mientras el lane no sirva. Es también lo único que cierra §2 de verdad.

---

## 2. Barato: una precondición de espera convirtió 3/3 en rojo en 3/3 en verde

### Lo que se observó y cómo se midió

Escribí a mano un bucle de espera antes de cada corrida: sondear `pg_stat_activity` hasta que no quede
ninguna transacción abierta, y solo entonces arrancar.

- **Antes**: la suite de Session fallaba **1-2 tests por corrida**, variando entre corridas.
- **Después**: **3/3 en verde**, con 118 tests y 626 assertions en cada una.

### La consulta, para levantarla tal cual

```sql
-- Deliberadamente SIN filtrar por datname: el horizonte de xmin es de CLÚSTER (BL-138),
-- así que una transacción abierta en cualquier base cuenta, incluidas las que no son nuestras.
SELECT count(*) FROM pg_stat_activity WHERE xact_start IS NOT NULL AND pid <> pg_backend_pid();
```

La forma del bucle (los datos de conexión son los del clúster de test del lane; en el stack principal el
contenedor observado es `f5sign-postgres-test`):

```sh
until [ "$(psql -Atq -c "SELECT count(*) FROM pg_stat_activity \
    WHERE xact_start IS NOT NULL AND pid <> pg_backend_pid();")" = "0" ]; do
  sleep 2
done
```

### Recomendación

Que viva en el **target del Makefile**, no en la cabeza de cada sesión: es la diferencia entre una
propiedad del entorno y una costumbre que se olvida. Añadirle un tope de espera, para que el target no se
cuelgue indefinidamente cuando el clúster nunca queda en reposo — y que al agotarse **diga por qué** en vez
de arrancar en silencio.

### ⚠ El límite, dicho en voz alta

**Es una precondición, no aislamiento.** Solo comprueba el instante del arranque: no hace nada cuando una
segunda corrida **empieza** durante la tuya, que es el caso frecuente con varias sesiones vivas. Para eso
solo sirve un clúster aparte. Es el 80 % barato; **el arreglo real es el §1**, y esto no debe cerrarlo.

---

## 3. BL-135 sigue mordiendo, con un matiz que no estaba

[**BL-135**](../BACKLOG.md) ya está medido: el contenedor ad-hoc que un worktree tiene que usar arranca con
`memory_limit=128M`, mientras que el `php-fpm` que usan los targets del Makefile arranca con **512M** — un
cuarto de la memoria, sin aviso.

### El matiz que añade esta sesión

**`php -d memory_limit=-1` no se hereda a los procesos hijo.** Infection lanza su propio `phpunit`, que
vuelve a 128M: la bandera que la receta documenta **no cubre el caso que la motivó**. Lo que sí funcionó fue
montar un `php.ini`:

```sh
printf 'memory_limit=-1\n' > infection.ini
docker run ... -v "$PWD/infection.ini":/usr/local/etc/php/conf.d/zz-infection.ini ...
```

### Recomendación

**Subir el límite en la imagen dev, o en el lane.** BL-135 ya separa las dos mitades y esta es la de infra:
la imagen cierra **la clase entera** —cualquier herramienta que cruce 128M desde un worktree, no solo
Infection—, mientras que parchear la receta solo cubre los comandos que alguien se acuerde de parchear. Y
mientras no exista, cada sesión que necesite más memoria vuelve a descubrir por su cuenta que la bandera no
basta y que hace falta un fichero montado.

---

## 4. Un artefacto de build rancio produjo un error FALSO y muy convincente, dos veces, a dos agentes independientes

### Lo que se observó

PHPStan reportó:

```
Service "F5Sign\Foundation\Http\SessionCredentialCodec" is not registered in the container
```

para un servicio que **sí** está registrado: `config/services.yaml` lo declara, y además con `public: true`.

**Causa**: un `var/cache/dev/App_KernelDevDebugContainer.xml` rancio, anterior a la aparición del servicio —
el fichero que `phpstan.dist.neon` declara en `symfony.containerXmlPath`. `bin/console cache:warmup
--env=dev` lo arregló.

**Dos agentes distintos cayeron en él el mismo día, por separado, y cada uno perdió tiempo.** El mensaje es
específico, verosímil y apunta al sitio equivocado: se lee como "falta registrar el servicio" y manda a
tocar `services.yaml`, que está bien.

### Recomendación

Ya está avisado en las notas de arranque de sesión, **y aun así costó tiempo dos veces en un día**: ese es
el argumento para hacerlo **mecánico** en vez de documentarlo mejor. Calentar la caché dev dentro del propio
camino de PHPStan —el target de infra— para que el análisis no pueda leer un contenedor anterior al árbol
que analiza. La mitad equivalente del lado composer es nuestra y no está hecha; queda anotada aquí solo para
que las dos no se dupliquen.

---

## Lo que NO se ha verificado

⛔ **Nada de esto se ha contrastado con los ficheros de compose reales de `f5sign-infra`.** Esta sesión no
tenía ese repo abierto. Todo lo que este documento afirma sobre el lane `wt-*` —qué servicios declara, dónde
está el timeout de 300 s, qué imagen fija los 128M— proviene de lo que **la documentación del propio
backend** dice de ese lane: la precondición 5 de
[`task-runner`](../../.claude/skills/task-runner/SKILL.md) y [BL-135](../BACKLOG.md). **No** de haber leído
`docker-compose.wt.backend.yml`. Si al abrirlo la realidad no coincide, manda la realidad — y esa
discrepancia merece una corrección en las filas del backlog, que es donde vive la verdad durable, no solo un
arreglo silencioso en infra.

Además, y por el mismo criterio:

- **No se ha medido el coste** de añadir MinIO y RabbitMQ a cada lane con varios lanes vivos a la vez. El
  cap de concurrencia y el presupuesto de recursos son de infra; la recomendación es de **forma**, no una
  configuración probada.
- **No se ha probado ninguna variante del lane.** Ninguna de las tres recomendaciones del §1 se ha
  ejecutado; están razonadas contra medidas, no validadas.
- **Lo establecido en el §1 es que *esos* 9 fallos eran contención**, no que todo rojo de esa familia lo sea
  siempre. [BL-139](../BACKLOG.md) registra un segundo mecanismo —`eu-dss` y MinIO compartidos, sin
  equivalente per-sesión— con **causa no confirmada** y firma distinta. **No fundir los dos**: se atribuyó
  una vez y la atribución fue errónea, y fundirlos haría que se "arreglase" el que no era.
- **Los conteos son de este árbol y de este día.** 1675 tests / 7192 assertions es la suite del commit
  `f318c9e`; no sirve como línea base de otra rama.

## Cómo reproducirlo desde infra

Sin el backend clonado hace falta el árbol para correr la suite, pero **el mecanismo del §1 se demuestra sin
ella**, y ese es el que decide si el trabajo merece la pena:

1. Levantar el stack de test y abrir, desde cualquier cliente, una transacción contra **cualquier** base del
   clúster de test — incluida una que no contenga tablas nuestras:
   `BEGIN; SELECT txid_current(); SELECT pg_sleep(90);`
2. Comprobar con la consulta del §2 que el clúster **no** está en reposo, y que la transacción de una base
   aparece igual mirando desde otra. Esa sola observación ya es la regla *un clúster por sesión*.
3. Con el backend disponible: correr `EventRelayTest` bajo esa transacción → rojo, con firmas del tipo
   `0 is identical to 2` o `actual size 0 matches expected size 1` (las que BL-138 registra). Matar ese
   backend y repetir → verde. **Repetir ×3 como mínimo**: un rojo suelto no mide un intermitente.
4. Para ver el límite del §2: intercalar la espera antes del paso 3 y abrir la transacción **después** de
   que la espera pase. Sigue rojo — que es exactamente lo que la espera no puede cubrir, y por qué no
   sustituye al §1.

---

## Correcciones 2026-08-18, de la sesión de `f5sign-infra` al aplicar el §1

Este documento avisaba en su sección *"Lo que NO se ha verificado"* de que ningún fichero de `f5sign-infra` había sido abierto. Al abrirlos, salieron tres correcciones. Van aquí en vez de reescribir el texto original, porque *"creíamos X y era Y"* es el registro útil.

**1. «Los tests de broker se saltan» es FALSO — fallan.** Verificado en este repo, no en el suyo: `rg -c markTestSkipped tests/` da **cero**, y `phpunit.dist.xml` no filtra ningún grupo — su único `<exclude>` es de *cobertura* (`src/**Bundle.php`). No existe mecanismo en la suite que salte nada.

⚑ **Y el origen del error importa más que el error**: la frase estaba citada textualmente de la precondición 5 de la skill `task-runner`, que es donde nació. Corregida allí también, porque un handoff arreglado deja la skill instruyendo mal a la siguiente sesión. *"Se salta"* y *"falla"* llevan a diagnósticos distintos, y aquí refuerza el caso en vez de debilitarlo: un fallo es más fácil de justificar arreglar que un skip.

**2. El inventario de hosts era corto, no largo.** `.env.test` resuelve **cinco**: `postgres-test`, `minio`, `rabbitmq`, **`mailpit`** y `eu-dss`. Este documento nombraba tres.

**3. El §3 (BL-135) estaba mal atribuido, y la corrección lo reordena.** `docker-compose.wt.backend.yml` **ya** bind-monteaba `./docker/php/php.ini` con `memory_limit=512M` dentro de `php-fpm-wt`, con un comentario describiendo esa muerte exacta. Los 128 MB que medimos eran de **nuestro `docker run` a mano**.

⛔ O sea que no era un defecto independiente sino **un síntoma del §1**: el lane cojo empuja a una sesión a fabricarse un contenedor propio, y ése sí arranca pelado. Tal y como estaba escrito mandaba a arreglar la imagen dev cuando el lane ya cubría el caso. `BL-135` lleva la corrección. ⚑ Lo que **sí** sobrevive intacto: `-d memory_limit=-1` no se hereda a los hijos, así que Infection relanzando `phpunit` vuelve al límite — y 512M tampoco es `-1`.

## Un cabo que es nuestro, no suyo

`composer install` dispara `post-install-cmd` → `@ide:phpstan-stubs` → `bin/extract-phpstan-stubs`, que escribe en `.phpstan-ide/` **dentro del árbol bind-monteado**. Está gitignorado, que es justo por lo que no aparece en `git status` y por lo que nadie lo ha visto. La sesión de infra lo ha tapado con un volumen por lane, pero **que un `post-install` escriba en el worktree es decisión de este repo**. Queda anotado aquí; si alguien lo mueve, que sea a sabiendas.

## Lo que quedó explícitamente pendiente en infra

Dicho por ellos y anotado aquí para que no se lea como hecho: los **cuatro gates restantes** (`lint`, `arch`, `phpstan`, `infection`) **no** tienen ruta de lane, y no por pereza — `phpstan` lee `var/cache/dev/App_KernelDevDebugContainer.xml` y el `var/` del lane es un volumen **vacío**, así que fallaría por *ausencia* en vez de por rancio (nuestro §4 al revés); e `infection` es justo lo que no cabe en 512M. El §2 (el bucle de espera de `pg_stat_activity`) tampoco se implementó, y con clúster por lane sobra en el lane — su sitio es `test-db-setup` del árbol principal.
