# Retención y purga — cómo funcionaría todo, paso a paso

**2026-08-27.** Nota de trabajo, no decisión. El diseño viene de la sesión `f5sign-infra`
(pruebas contra MinIO); las comprobaciones sobre el código del backend son de esta sesión y
van marcadas ⊙. **Las duraciones son provisionales** y se moverán con las pruebas de Linode.

⚠ Nada de esto está construido todavía. La sección §8 dice exactamente qué hay y qué no.

---

## 1. El problema, en una frase

Hoy hay **un solo reloj** y hace dos trabajos que se contradicen: decide cuándo un documento
puede destruirse *y* cuándo el cliente deja de verlo. Como está puesto en COMPLIANCE 5 años,
el cliente **no puede borrar nada durante cinco años, y nosotros tampoco**.

Eso choca de frente con el **RGPD Art. 28.3.g**: al terminar la prestación, el encargado borra
o devuelve los datos a elección del responsable. Bajo COMPLIANCE no es caro ni incómodo —
es **imposible**. Y la excepción legal del artículo habla de *nuestra* obligación de conservar,
no la del cliente.

## 2. La idea central: una palabra hacía dos trabajos, y luego otra

Empezó como *"separar los dos relojes"*. Al aterrizarlo salieron **tres cosas distintas**, y el
error siempre fue el mismo: una sola palabra respondiendo preguntas opuestas.

| | **Techo de conservación** | **Suelo de obligación** | **Candado físico** |
|---|---|---|---|
| ¿Qué fija? | cuándo purgamos **solos** si nadie dice nada | antes de esta fecha **no podemos** borrar aunque lo pidan | qué puede destruirse y por quién |
| Default | **6 años** *(provisional — ver abajo)* | ninguno | GOVERNANCE |
| ¿Quién lo mueve? | el cliente; se pide **por documento**, resuelve a `max()` sobre el **envelope** (§9.5) | su regulación o el contrato | nosotros, al escribir |
| ¿Bloquea el borrado del usuario? | **no** | **sí** | solo COMPLIANCE |
| ¿Dónde vive? | Postgres | Postgres | grabado en el objeto |

⛔ **"Ampliar" significaba las dos primeras y son opuestas.** Ampliar el *techo* ("guárdalo hasta el
año 15") no le quita al usuario el derecho a borrarlo en el año 5: solo decía que nosotros no lo
íbamos a tirar. Ampliar por *obligación* sí se lo quita. Si se llaman igual, la misma petición se
acepta o se rechaza según quién lea el campo.

**La fecha de purga real es `max(gracia, suelo)`**, con el techo como disparador si nadie pide nada.

**Por qué 6 años y no 5.** El Código de Comercio manda conservar libros y correspondencia 6 años, que
es la obligación real de la mayoría de clientes españoles — un default vale más cuando responde a
algo que existe. ⚠ **Confirmar con legal antes de que entre en un contrato**: una vez escrito ahí no
se mueve.

⚑ **El default NO es "indefinido", y la razón es legal.** Se consideró (es lo que hacen DocuSign y
Adobe) y se descartó: retención indefinida por defecto choca con el **Art. 5.1.e (minimización)** y
solo se sostiene si el cliente la configura activamente. Un techo definido y justificable no
necesita esa muleta.

⚑ **Y el techo no lo pone el candado.** Los 6 años los aplica el worker desde Postgres. El candado es
otra cosa y sirve para otra cosa (§5.bis b).

## 3. Los tres niveles de candado (medidos contra MinIO por `f5sign-infra`)

| Nivel | ¿Se puede borrar? | ¿Reversible? | Para qué |
|---|---|---|---|
| **GOVERNANCE** | sí, con bypass auditado | sí | el default. Red de seguridad |
| **LEGAL HOLD** | **no**, ni con bypass | **sí** — lo levantamos nosotros | litigio. Sin fecha, sin comprometernos |
| **COMPLIANCE** | no, **ni aunque queramos** | **no** | custodia de pago |

Cuatro hechos medidos que sostienen todo lo demás:

1. **El candado protege la VERSIÓN, no la clave.** Con retención activa se puede escribir una v2
   de la misma clave; la v1 queda intacta. La inmutabilidad sale del *versioning*; el candado solo
   gobierna la **destrucción**.
2. **El borrado blando funciona en cualquier modo.** Un `rm` normal devuelve 0 y pone un *delete
   marker*: desaparece del listado, los bytes siguen enteros. **El cliente siempre puede borrar a
   nivel de producto**, incluso bajo COMPLIANCE.
3. **La retención solo se alarga.** 1d → 2d funciona; 2d → 1d se rechaza. (De aquí sale el truco del §5.)
4. **GOVERNANCE y COMPLIANCE conviven en el mismo bucket, por objeto.** La custodia de pago **no
   necesita buckets aparte**.

⚠ **El default del bucket no es una garantía duradera**: se puede cambiar de COMPLIANCE a
GOVERNANCE (afecta solo a objetos nuevos). Cualquiera con acceso de administración lo debilita.
**Solo el modo por objeto es garantía.** Esto tiene que estar escrito donde se prometa la garantía.

## 4. Los cuatro estados de un artefacto

```
activo ──► retirado ──► (bloqueado) ──► purgado
             │
             └──► activo     ← REVERSIBLE: se quita el delete marker y vuelve
```

- **activo** — visible y descargable.
- **retirado** — delete marker puesto. Invisible para el producto, **bytes intactos**. Reversible.
- **bloqueado** — retirado, pero el reloj legal sigue vivo. No se puede purgar todavía.
- **purgado** — versiones destruidas. Irreversible.

⚠ **`retirado` solo existe en tres de las cinco zonas.** ⊙ `originals` y `temp` tienen versioning
**apagado a propósito**, y `docker/minio/init-buckets.sh` *falla el aprovisionamiento* si lo
encuentra encendido: con versioning una regla `Expiration.Days` no borra, convierte la versión
actual en no-actual y pone un delete marker — el bucket se lee como "expira" y no expira nada, y
choca con la purga de tenant del Pilar 7, que exige borrado real. En esas dos zonas un borrado es
un borrado. Probablemente da igual (`originals` muere a 30 días), pero **el modelo de cuatro
estados no es uniforme y hay que escribirlo así**.

---

## 5. El recorrido, momento a momento

### T0 — El remitente sube el documento
Va a `originals`. **Sin candado**: expira por lifecycle a 30 días. No hace falta más: es la fuente
sin firmar, y su valor probatorio es cero una vez sellada.

### T1 — Se firma y se sella
Los bytes sellados se escriben en `signed` con **el suelo aplicable** de retención — no la fecha
final, el **mínimo**. Aquí es donde muerde el hecho 3: como la retención solo se alarga, poner el
suelo ahora no cierra ninguna puerta.

⊙ *Hoy el PUT no lleva ningún parámetro de retención: el objeto hereda el default del bucket
(COMPLIANCE 5 años). El puerto `ObjectStore` solo tiene `put()` y `get()`.*

### T2 — El envelope se cierra  ◄── **el truco del reloj**
Al cerrar ya se conoce la fecha exacta, así que la retención se **EXTIENDE** del suelo a la fecha
real. Así desaparece el desajuste entre el instante del PUT y el del cierre.

⊙ **Esto tiene sitio y es más seguro de lo que parece.** `Envelope::complete()` emite
`EnvelopeCompleted`, y el patrón de reactor ya existe (`OnEnvelopeSealed` +
`OnEnvelopeSealedHandler`). La llamada a S3 **no puede** ir en el agregado (el dominio no importa
infra) ni dentro del lock (regla 3: nada lento en un handler síncrono) → **reactor asíncrono sobre
el evento**.

⚑ **Y aquí está la propiedad que salva el diseño**: como la retención *solo se alarga*, extender
es **idempotente**. Reintentarlo es seguro, ejecutarlo dos veces es seguro, y un extend perdido
—por un fallo de red justo después de cerrar— **se repara volviéndolo a ejecutar**. El punto más
frágil del diseño resulta no serlo.

### T3 — Vida normal
El documento se descarga, se consulta, se enseña. El reloj legal corre por debajo sin que nadie lo
note.

### T4 — El cliente borra el documento
`rm` normal → delete marker. **Devuelve 0 y funciona en cualquier modo de candado.** Para el
cliente el documento ha dejado de existir: no sale en listados, no se descarga. Los bytes siguen
ahí, retenidos.

**Esto es lo que hace que el modelo cumpla el 28.3.g sin renunciar a la evidencia**: el derecho de
borrado del cliente se satisface *al instante*, en la capa de producto, y la obligación legal se
satisface por debajo.

### T5 — El cliente se arrepiente  ◄── **la papelera**
Se quita el delete marker y el documento vuelve. **Medido.** Es la razón de que `retirado` sea un
estado y no un borrado.

Y aquí es donde arranca **el reloj de gracia** — p. ej. **90 días** *(provisional; DocuSign usa 14)*.
⚑ **Lo que lo hace mejor que esperar al candado: la fecha de purga cuelga de CUÁNDO LO PIDIÓ EL
USUARIO, no de cuándo se escribió el documento.** Borra en el mes 1 → purga en el 4. Borra en el 10
→ purga en el 13. Deja de depender de un accidente. Sin esto, un documento borrado en el mes 1
sobrevive **once meses** — no porque no se pueda destruir, sino porque nada lo iba a destruir.

### T6 — Vence la gracia
Purgable **si además se cumplió el suelo de obligación** (`max(...)` del §2). Si no, espera: el
documento está retirado —invisible para el cliente— pero no se destruye hasta que el suelo lo permita.

*(Y si el usuario nunca borra: no pasa nada hasta el **techo**, año 6 por defecto, con los avisos del
§5.bis c. Ampliable por documento antes de que llegue.)*

### T7 — El worker purga
Corre a diario. Destruye las versiones con **la credencial de purga** y **emite un evento de purga
con el hash de lo borrado**.

⚑ **Unidad: el ENVELOPE** (§9.5) — y dentro, **la PUNTA de cada documento, no los N+1 artefactos** — todos los demás son prefijos byte a
byte de ella (§9.1). Y el audit trail nunca antes que su documento (§9.2).

⛔ **El worker purga lo que POSTGRES dice que un usuario retiró — NUNCA lo que tiene delete marker.**
Es fácil implementarlo al revés y el fallo es grave: credencial del backend robada → lo borra todo en
blando (los delete markers se ponen en cualquier modo, hecho 2) → 90 días después el worker lo
destruye **haciendo su trabajo correctamente**. La red de seguridad tendría **mecha de 90 días**. Con
la fila de Postgres como fuente la mecha no existe: la credencial de S3 no puede escribirla.

⛔ **Worker, NO lifecycle.** Tres razones, y las tres son independientes:
1. Un lifecycle **no sabe qué está retirado** — ese estado vive en Postgres, y los filtros de
   lifecycle son prefijos literales.
2. Borra **en silencio**, sin dejar registro. Justo lo contrario de lo que necesita una purga.
3. Podría poner delete markers **sobre documentos vivos**.

### T8 — Lo que queda
El evento de purga **sobrevive al documento**: `audit_events` pseudonimizados + hash SHA-256, que
demuestran que *"existió una firma válida"* sin revelar quién firmó. Son bytes, no gigas.

### 5.bis — Lo que la papelera cambia en el resto del diseño

**(a) El bypass pasa a ser la operación DIARIA, no la excepción.** Como la gracia (90d) es más corta
que el candado (1 año), la purga cae casi siempre *dentro* de la ventana → necesita bypass casi
siempre. Suena a debilitamiento y es lo contrario: **un camino que se usa a diario funciona el día
que lo necesitas; uno de emergencia está roto justo cuando vas a usarlo.** No toca la garantía — el
backend sigue sin saber construir la cabecera; la construye el purgador, que es otro servicio con
otra credencial y su propio registro.

**(b) Se aclara para qué sirve GOVERNANCE.** Con la papelera puesta se ve que el candado y la
papelera cubren **dos amenazas distintas**: el candado impide que una credencial robada del backend
**destruya** (puede ocultar todo, no puede destruir nada); la papelera protege del **borrado
individual por error**. Antes las dos colgaban del mismo número — por eso el número no podía estar
bien.

**(c) Hace falta papelera en producto**: lista de retirados con su fecha de purga. El Pilar 7 §G.1.6
ya trae el modelo de avisos (30 días antes, recordatorio a 7), así que encaja sin inventar nada.

**(d) La baja de cliente NO hereda la gracia.** El contrato terminó y pidieron destrucción; la
papelera es para arrepentirse de borrar *un documento*, no de *irse*. (DocuSign purga a los 90 días
del cierre de cuenta — decidir si se copia.)

---

## 6. Los tres casos especiales

**Litigio → LEGAL HOLD.** Object Lock sin fecha. No se borra ni con bypass, y lo levantamos
nosotros cuando el litigio acaba. No nos compromete a ninguna duración.

**Custodia de pago → COMPLIANCE por objeto.** Convierte el WORM fuerte de restricción en producto
— es lo que Signaturit/Yousign venden como archivado de larga duración, producto aparte.

⛔ **Y hay una consecuencia contractual que hay que escribir**: **quien elige COMPLIANCE elige que
NI ÉL pueda pedir el borrado.** Se le dice al contratar; no se descubre en la baja.

**Baja de cliente.** Pieza de primera clase, dos opciones: *exportar+destruir* (default, cumple
28.3.g, coste a cero) o *exportar+conservar* (de pago).

## 7. Las tres credenciales

| Camino | Permisos | ¿Bypass? |
|---|---|---|
| **backend** | RW limitada | **nunca** |
| **purga** | separada, fuera de `.env.prod` | **la única** |
| **operador** | unlimited | provisión |

En Linode la separación es **por camino, no por permiso** — no hay IAM. La mitigación verificable
es que **el código del backend no sepa construir la cabecera de bypass**, y eso sí se comprueba
estáticamente.

⚑ **Bypass solo destruye, no altera.** Los bytes de una versión son inmutables en los tres modos,
así que ni con bypass se falsifica nada: solo se hace desaparecer, y la desaparición queda
registrada. Por eso la garantía comercial se parte en dos: **estándar = "no lo haremos"**
(procedimiento auditado) · **custodia = "no podemos"** (COMPLIANCE).

⊙ **Este patrón ya existe en este repo, en Postgres, y conviene copiarlo en vez de inventarlo.**
El purgador de credenciales de firma no borra: llama a `SELECT session.purge_expired_signing_tokens(?)`
porque **`f5sign_app` no tiene DELETE sobre la tabla, solo EXECUTE sobre la función**. Hay además un
rol `NOBYPASSRLS` dedicado (`f5sign_signing_token_custodian`) y políticas RLS propias del camino de
purga (`signing_token_purge_visible`, `signing_token_purge_expired`). Es exactamente la misma idea
—capacidad de purga como chokepoint estrecho y auditable, no como permiso ancho— ya resuelta una vez.

---

## 8. Qué existe hoy y qué no  ⊙ *(medido en el árbol, 2026-08-27)*

| Pieza | Estado |
|---|---|
| Zonas `originals` / `signed` | ✅ se escriben (1 y 2 llamantes) |
| Zonas `audit-trails` / `biometrics` / `temp` | ⚠ **0 llamantes en `src/`** — aprovisionadas y verificadas, nadie escribe un byte |
| Retención por objeto en el PUT | ❌ el puerto no la tiene |
| Extender retención / legal hold / borrar | ❌ el puerto solo tiene `put()` y `get()` |
| Columna de retención configurable | ✅ **existe y se persiste** (ver abajo) |
| Estado `retirado` en el dominio | ❌ sin sitio (ver §9) |
| `data-retention-worker` | ❌ **no existe** |
| Papelera / reloj de gracia | ❌ no existe (§5.bis) |
| Techo / suelo como campos separados | ❌ hoy hay dos ints nulos que modelan otra cosa |
| Poda del `platform.event_log` | ⚠ **no existe** — y eso es lo que hace que el evento de purga sobreviva (§9.3) |
| Inventario de objetos de plataforma | ❌ no existe — es lo que hace enumerable el fan-out (§9.1+9.2) |
| Evento de purga | ❌ no existe, pero es barato (`EventTypeRegistry`, 47 `EVENT_TYPE`) |
| Verificación del hash al leer | ❌ **nunca se hace** (ver abajo) |

**La retención configurable NO es aspiracional — está medio construida y siempre vale null.**
`Settings::$effectiveRetentionActiveYears` / `$effectiveRetentionArchiveYears` existen, tienen
columnas desde `Version20260713000002`, y hacen el viaje completo save → hydrate → `equals()` →
SELECT. Pero **el único sitio de todo el repo que les pone un valor no-nulo es un fixture de test**
(valor 7). Ningún comando, ningún endpoint, ningún caso de uso, y no llegan a ninguna `Contract/View`.
➜ **El diseño no necesita columna nueva. Necesita escritor, lector y worker.**

**El sha256 no se verifica nunca.** Se calcula al escribir, se guarda en
`envelope.document_artifact.hash`, y al leer se saca de Postgres y se emite como **ETag**. Los bytes
vienen de S3 y el hash de Postgres, y **no se encuentran en ningún punto**. En el camino del
firmante es peor: `SigningDocumentContent` **no tiene campo de hash**. O sea que el "two-layer" de
ADR-0016 es tamper-**evidente** (el hash que haría posible detectarlo sí se graba) pero no
tamper-**detectante**.

⚑ Mitigación real, y es más fuerte de lo que parece: **el llamante no puede aportar clave.**
`S3ObjectStore::put()` la acuña él con 16 bytes aleatorios al final, y `get()` es el único otro
método. Ningún camino del backend puede escribir una v2 sobre una clave existente: la sustitución
tendría que venir **de fuera** — credencial robada u operador. Que es justo el modelo de amenaza que
abre GOVERNANCE + bypass. **Por eso el cambio aprieta aquí más de lo que apretaba antes.**

## 9. Huecos abiertos

### Los que muerden

**9.1 — RESUELTO: solo hay UNA cosa que purgar por documento.** ⊙ `DocumentSigner` firma sobre la
**punta**, no sobre el original, y *"DSS **appends** a new revision rather than rewriting, so every
earlier signature survives"*. Con la punta = el original cuando no hay firmas, la cadena entera es:

```
original ⊂ firmado-por-1 ⊂ firmado-por-2 ⊂ … ⊂ sellado (la punta)
```

Cada artefacto es **byte a byte un prefijo de la punta** — los primeros M bytes del fichero final.

- **Los intermedios son redundancia pura.** N+1 objetos por un contenido que ya está entero en uno.
- **Y tirarlos no pierde nada probatorio**: `document_artifact` guarda el `hash` de cada uno, así que
  *"así estaba cuando firmó el segundo"* se demuestra cogiendo los primeros M bytes de la punta y
  comprobando que dan ese hash. **Es para lo que existe la cadena de hashes, y no se usaba para nada.**
- **Ya está pasando y es correcto**: el UPLOAD va a `originals`, lifecycle 30 días, así que el
  original ya se borra solo hoy dejando su fila apuntando a una clave muerta. Correcto *precisamente*
  por la propiedad del prefijo.

➜ **Dentro de un documento solo se conserva la PUNTA** — ver §9.1.bis para dónde viven los
intermedios mientras tanto. *(Y la unidad completa es el **envelope** — §9.5.)*

### 9.1.bis — Stage-then-promote: dónde viven los intermedios

Sin esto, un documento con N firmantes deja **N+1 objetos en zona retenida**, y ≈ (N+1)× de coste
multiplicado por los años de retención. ⚠ **El versionado de S3 NO lo arregla**: las versiones son
copias completas, no deltas — 6 versiones ocupan lo mismo que 6 claves. El derroche viene de
*conservarlos*, no de cómo se direccionan.

**Las cinco reglas:**

1. **Los intermedios se escriben en zona de staging NO retenida.** ⚠ `temp` a 24 h **no sirve**: el
   intermedio no es scratch, es el documento vivo entre el firmante *k* y el *k+1*, y el siguiente lo
   lee días después. Hace falta ventana del orden de la vida del sobre.
2. **Se promueve la punta a `signed` cuando la cadena ya no va a crecer.**
3. ⛔ **El predicado es *"¿se aplicó alguna firma?"*, NO *"¿en qué estado terminó?"*** —
   `EXISTS(artifact WHERE produced_by_kind <> 'UPLOAD')`. Es la lección de la regla 6 tal cual
   (`sent_at IS NOT NULL` frente a `status <> 'DRAFT'`), y **aquí ya está rota de fábrica**: seis de
   los once `EnvelopeStatus` no los escribe nadie ([BL-202](BACKLOG.md)).
4. **Sin firmas no hay nada que promover**: muere con `originals`.
5. **El objeto promovido lleva el reloj normal del tenant, sin importar cómo acabó el sobre.** No por
   simplicidad: **cualquier regla que dé menos retención a los abandonados crea un incentivo a
   abandonar** — que el remitente anule para acortarle la vida a una firma que le perjudica.

**Por qué se conserva la firma de un sobre que nunca se completó.** El audit trail dice *"el firmante
1 firmó en T con hash H"*: eso es una afirmación **nuestra**. Los bytes firmados son prueba
**verificable por un tercero** — certificado, byte-range, sello de tiempo— **sin confiar en
nosotros**. Destruirlos deja la capacidad de *afirmar* y quita la de *verificar*, que es justo lo que
PAdES existe para dar. ⛔ **Y el botón de anular lo tiene el remitente**: si anular destruyera los
bytes, una parte podría destruir unilateralmente la prueba del acto de la otra. Cuesta **un objeto**,
no N, porque la punta lleva todas las firmas aplicadas.

⛔ **La promoción es un BARRIDO, no una reacción a evento.** Dos razones independientes: (a) solo
existen `EnvelopeCompleted` y `EnvelopeVoided` — nada para caducado ni rechazado, así que un sobre
abandonado en `SENT` **no dispararía nunca** y sus firmas morirían en staging en silencio; (b) un
evento que falla pierde la evidencia sin ruido, y un barrido reintenta cada día. ⚠ Y el predicado
mira **`expiresAt < now()`**, no `status = 'EXPIRED'`, que es el estado que nadie escribe (BL-202).

⚑ **Tres cosas más que arregla de paso:**
- **BL-14, el huérfano WORM.** Si el `put()` va a zona no retenida, el perdedor del compare-and-swap
  deja basura **borrable** en vez de un objeto bloqueado. BL-14 ya nombra `StorageZone::TEMP` como la
  zona de staging que lo arreglaría, *"que existe, está aprovisionada y no la referencia **nada**"*.
- **El extend-at-close (T2) desaparece**: el objeto **nace** en `signed` con la fecha correcta, así
  que no hay desajuste PUT↔cierre que tapar ni llamada de red que pueda fallar tras cerrar.
- **El inventario (§9.5) gana un segundo motivo independiente**: el huérfano es *invisible* — ninguna
  fila apunta a él—, así que sin inventario no hay nada que barrer. Es por lo que BL-14 lleva abierto
  desde julio con *"el arreglo registrado no puede funcionar"*.

⚠ **Salvedad**: vale para el camino **PAdES**. El Pilar 7 §B.2 contempla no-PDF con **CAdES
detached** (`.p7s` junto al original); ahí no hay prefijo y el original **sí** es irreemplazable. Si
se construye, esta regla necesita excepción explícita.

⚠ **Bug latente que cae de este análisis, ajeno a la retención.** `expiresAt` lo fija quien crea el
envelope, **sin tope**. Envelope a 60 días + primera firma el día 45 → `DocumentSigner` lee
`tipStorageKey`, que en un documento sin firmar **es el original en `originals`**, y el lifecycle ya
lo borró: `StorageException`, envelope inservible, nadie hizo nada mal. **Comprobar aparte.**

**9.2 — RESUELTO: la regla del audit trail es UNIDIRECCIONAL.** No es *"misma retención"* (Pilar 7
§B.2) sino **`retención(audit_trail) ≥ retención(documento)`**:

| | ¿Correcto? |
|---|---|
| purgar documento, conservar trail | sí — inofensivo, y es el estado final que el diseño ya quiere |
| **purgar trail, conservar documento** | ⛔ **nunca** — destruye la prueba de cómo se firmó algo vivo |
| los dos juntos | sí, el caso normal |

Se cumple **solo** al escribir (el trail se genera tras la última firma → su PUT es posterior → misma
duración da fecha más tardía)… **hasta la primera ampliación**. Si se amplía el documento y el trail
no se entera, el invariante se rompe justo en el caso que lo necesitaba.

**9.1+9.2 — LO QUE UNE A LOS DOS: el fan-out sobre un conjunto que no se puede enumerar.** Ampliar y
purgar son la misma operación sobre *los objetos de un envelope*, y **hoy no hay consulta que los
devuelva**: los artefactos están en `document_artifact` (BC Envelope), el audit trail es de Evidence
& Audit (sin construir). ➜ **Inventario de objetos a nivel de plataforma**, una fila por objeto en el
PUT: purgar y ampliar pasan a ser consultas sobre una tabla, y de paso se cierra BL-14 (un objeto
cuyo commit falló está en el inventario y es recogible).

⛔ **La alternativa —que el worker sepa qué BCs escriben bytes— es el fallo que prohíbe la regla 5 de
autoría de `CLAUDE.md`**: *"una enumeración es un predicado, y el conjunto que exime es todo lo que
aún no está en la lista"*. BC nuevo escribe bytes → el worker no los purga → **reporta éxito**. En
RGPD, un incumplimiento que se ve verde. Mismo fallo que el `BC_SCHEMAS` hardcodeado del
`SchemaConformanceTest`, que ya pasó aquí.

**9.3 — RESUELTO: la poda es la respuesta EQUIVOCADA.** ⊙ `platform.event_log` lleva
`sys_commitment BYTEA`, un *self-hash leaf* sobre la fila: **borrar o redactar una fila rompe la
evidencia de manipulación que hace que el log sea evidencia**. La tarea no es construir un podador,
es **decidir que el log no se poda nunca y hacer que eso sea seguro**. Dos caminos, los dos conservan
el commitment:

- **(a) Que la PII no entre en el payload.** ⊙ Ya hay aserción de **conjunto cerrado**… para **tres
  eventos de Session**. El propio test dice por qué tiene que serlo: *"PHPStan L9 rechaza una clave
  que falta y acepta encantado una de más, así que un spot-check de «no hay email» deja pasar un
  `destination` recién añadido"*. Son **47 `EVENT_TYPE`**, y el conjunto exento es *"todos aquellos
  para los que nadie escribió el test"*. ➜ **test censo**: enumerar los tipos, clasificar, fallar con
  los no clasificados.
- **(b) Que entre cifrada bajo clave destruible.** El DEK por envelope de
  [ADR-0032](adr/ADR-0032-evidence-pii-custody.md)/[ADR-0033](adr/ADR-0033-pii-field-encryption-at-rest.md):
  los bytes del ciphertext no cambian → **el commitment sigue válido**; se destruye la clave → el
  plano es irrecuperable. Crypto-shred ya es el mecanismo de la plataforma para evidencia; **nunca se
  aplicó al log**.

✅ Parte ya limpia por construcción: `actor` es `ActorId::toString()` = `prefix:uuid`, opaco.

**9.4 — RESUELTO: la plantilla existe entera, hay que copiarla.** El worker barre todos los tenants
y `f5sign_app` es FORCE RLS con `current_tenant_id()` fail-closed → **cero filas, y reporta éxito**.
⊙ `Version20260818000005` ya lo resolvió para los tokens: `SECURITY DEFINER` + `SET search_path`,
función **propiedad del rol custodio** (`NOBYPASSRLS`), `REVOKE EXECUTE FROM PUBLIC` + `GRANT` solo a
`f5sign_app`, y políticas RLS que leen un ajuste **transaction-local** que pone la propia función —
con el `DELETE` repitiendo el límite en su `WHERE` y el comentario que es la idea entera: *"la
política es lo que aguanta cuando la sentencia está mal, no cuando está bien"*.

⚑ **Por qué no es un agujero**: `SECURITY DEFINER` corre como el dueño y escapa del RLS de
`f5sign_app`, pero el dueño es **`NOBYPASSRLS`**, así que sigue atado a *sus propias* políticas
estrechas. **La capacidad es la función, no el rol.**

➜ Misma forma para almacenamiento. ⛔ **Y la prueba tiene que purgar de DOS tenants distintos**: el
modo de fallo es *cero filas y éxito*, que ninguna aserción de "termina sin error" caza.

**9.5 — RESUELTO: la unidad de purga es el ENVELOPE.** Medio envelope purgado no es un estado
válido, y hay tres razones que apuntan al mismo sitio:

- ⛔ **El audit trail es por envelope**, no por documento (`audit-trails/{tenant}/{envelope}/audit_trail.xml`).
  Con el documento como unidad, el invariante del §9.2 **no compone**: no existe *"el audit trail del
  documento 2"* que purgar. Esto solo ya decide.
- **El envelope es el agregado.** `Document` es una entidad dentro de él, sin ciclo de vida propio. Y
  `findSealedArtifact` devolvería `null` para los purgados **sin nada que los distinga de un documento
  nunca sellado**.
- **Lo legal es el envelope.** *"Existió una firma válida"* es sobre la transacción, no sobre el
  fichero 3 de 5; y la base de retención es el contrato.

➜ **La unidad completa: por envelope — la punta de cada documento + su audit trail.** Una consulta al
inventario.

➜ **Y la ampliación por documento sobrevive como gesto de interfaz, resolviendo a `max()` sobre el
envelope**: amplías el documento 3 y se quedan los cinco. Cuesta algo más y a cambio el estado
incoherente no existe — y con el §9.1 el sobrecoste es pequeño, porque de cada documento solo se
guarda la punta.

**9.6 — ACOTADO: censo hecho, y el hueco real es uno solo.** ⊙ Datos personales fuera de S3:

| Dónde | Qué | Estado |
|---|---|---|
| `envelope.recipient` | `email`, `full_name`, `phone` | cubierto por el §G.1.5 (pseudonimizar) |
| `notification.*` | `addressee_ref`, `destination` | ⛔ **no lo cubre nadie** |
| `session.auth_attempt` | `source_ip`, `user_agent` | **BL-116**, ya abierta |
| `platform.event_log` | payload | → §9.3 |

➜ **Queda Notification.** Y `destination` es el email o teléfono **realmente usado en el envío**: tras
purgar el envelope seguiría habiendo una fila diciendo *"enviado a juan@x.com"*.

⛔ **Restricción de arquitectura**: Notification es un **BC de soporte categoría (c)**
([ADR-0037](adr/ADR-0037-notification-supporting-bc.md)) del que **ninguna capa puede depender**. El
worker no puede alcanzarla desde Envelope — **necesita su propio camino de purga.**

### Los conocidos

- **Dónde vive `retirado`.** `document_artifact` es append-only e inmutable, así que un `retired_at`
  ahí choca de frente. Mejor tabla aparte, append-only, con fila de retirada y de restauración — da
  gratis la fecha desde la que cuenta la gracia.
- **Techo y suelo, ¿campos nuevos?** ⊙ `Settings` ya tiene dos ints (`effectiveRetentionActiveYears`
  / `ArchiveYears`) que hoy modelan otra cosa (las tres opciones del §G.1.6, con un "Archivar en
  frío" que este diseño no tiene) y que **siempre están vacíos**. Reasignar dos campos nulos es más
  barato que migrar: mirarlo antes de añadir columnas.
- **¿Se construye la verificación del hash al leer?** Hoy es discipline-until-built (§8).
- **Los números** (decisión, no construcción): 6 años (pendiente legal) · 90 días de gracia · la
  cifra del candado (ya decidido *largo*, §5.bis b) · y la **ventana de la zona de staging**
  (§9.1.bis regla 1: del orden de la vida del sobre, y `temp` a 24 h no vale).
- **Biometría Art. 9** — no encaja en el techo por defecto. Aplazable: es v2 y no existe.
- **¿Purga inmediata a petición?** Tercer disparador del worker. Barato, pero es el que hace el
  bypass alcanzable desde un flujo de cliente.
- **¿La baja de cliente hereda la gracia?** (§5.bis d.)
- **¿Un cambio de política es retroactivo** sobre lo ya guardado?

## 10. Qué falsaría el diseño

- **(b, pendiente)** Que el lifecycle ponga delete markers sobre objetos bloqueados.
- **(Linode, pendiente)** Que una *limited key* RW pueda hacer bypass de GOVERNANCE. ⚑ Si **no**
  puede, la garantía estándar deja de depender de *"el código no sabe construir la cabecera"* y pasa
  a ser una propiedad **de la credencial** — que es mucho mejor sitio para ponerla.

## 11. Lo que este cambio arregla de paso

- **BL-14 (el huérfano WORM) se disuelve.** Abierto desde 2026-07-28: los bytes firmados se hacen
  `put()` a la zona COMPLIANCE **antes** del compare-and-swap que puede rechazarlos, el modelo
  prescribe un reaper, y bajo COMPLIANCE el reaper es **imposible**. Con GOVERNANCE + bypass vuelve
  a ser construible. Es el mejor argumento *interno* a favor del cambio.
- **BL-200 pierde urgencia.** Argumenta que la jerarquía de claves debe decidirse **antes del primer
  PUT en producción** porque el layout queda congelado 5 años. Con GOVERNANCE 1 año esa ventana pasa
  de 5 años a 1, y con bypass deja de ser inmutable.

## 12. Lo que hay que tocar cuando se decida

- **`f5sign-infra`** — `docker/minio/init-buckets.sh` no solo *fija* COMPLIANCE 5y: lo **verifica**
  (busca `"mode":"compliance"` y `"validity":"5years"`, `exit 1` si no). Y es **el mismo script para
  dev, lane y `make s3-provision-prod`**, a propósito.
- **`f5sign-docs`** — Pilar 7 §B.1 dice *"ni siquiera un administrador con acceso root debe poder
  borrar"*. GOVERNANCE lo contradice **literalmente**; pasa de política de plataforma a descripción
  del **opt-in COMPLIANCE**. También §B.2 y §G.1.5.
- **`f5sign-backend`** — ADR nuevo (los **tres** niveles), ADR-0016 §5 pasa de *deferred* a
  requisito, y filas de `docs/BACKLOG.md`.

⚠ La analogía con SSE-KMS no tiene precedente aquí: esa desviación está escrita en
`f5sign-infra/README.md`, y en el backend hay **cero** menciones en `docs/`, `src/` y `config/`. No
hay formato de "nota de desviación" que copiar — contradecir el Pilar 7 desde el backend tiene que
ser **un ADR**.
