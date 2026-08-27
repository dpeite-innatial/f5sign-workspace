# INCIDENTE — el relay se tragó 29 hechos en silencio tras migrar PostgreSQL 16 → 18

**Fecha del incidente:** 2026-08-27, preprod (`api-sign-dev.factorcinco.com`).
**Estado:** **causa raíz confirmada con datos, arreglada en backend y prevenida en infra.**
**Repos implicados:** `f5sign-backend` (el arreglo) y `f5sign-infra` (la prevención). Ninguno basta solo.
**Datos perdidos:** 29 hechos, posiciones 173-201 de `platform.event_log`, **irrecuperables en la práctica**
(ver §7). El log en sí está **íntegro**: lo que se perdió fue la *entrega*, no los hechos.

⚑ **Si solo vas a leer un párrafo, que sea §6**: el primer culpable que identificamos era falso, y
seguía siéndolo después de que los datos ya apuntaran a otra cosa.

---

## 1. Qué se vio

Un sobre `SIGN_ORDERED` de tres pasos (`01a0427d-1b4d-7643-bec3-06eb5e748d72`) llegó a `COMPLETED` y se
selló **con una firma de tres**. El paso 3 se completó sin haberse activado nunca; los pasos 1 y 2
quedaron en `PENDING`. El firmante del paso 1 había firmado a las 09:12:14 y su firma no propagó a
ninguna parte, sin error en ningún sitio.

Eran tres defectos distintos, no uno. Este documento cubre el tercero, que es el único cuya causa no
era evidente; los otros dos tienen su propia fila (§8).

## 2. El mecanismo

El relay del event log (ADR-0031) avanza con un cursor `(sys_transaction_id, sys_global_position)` que
**compara primero por transaction id**. Eso descansa sobre una premisa que no estaba escrita en ningún
sitio: que `pg_current_xact_id()` nunca retrocede durante la vida del dato.

**Una migración mayor hecha como dump/restore a un clúster nuevo rompe exactamente esa premisa.** Los
valores `xid8` de la *columna* se restauran literales; el contador vivo del clúster arranca de cero. A
partir de ahí, todo hecho nuevo lleva un id **por debajo** del checkpoint restaurado, incumple la
comparación, y **no se lee jamás**.

Y no deja rastro *porque la fila nunca se lee*: no hay dead-letter, no hay línea de log, no hay tráfico
en las colas. `EventRelay::relayBatch()` devuelve 0 y reporta un log drenado.

## 3. La frontera, en dos líneas

```
pos 172 | txid 1087 | 2026-08-26 14:47:33   <- restaurada, época vieja
pos 173 | txid 1036 | 2026-08-27 09:11:30   <- nueva, el contador RETROCEDE 51
```

Checkpoint restaurado: `(1087, 172)`. Todo lo escrito con txid < 1087 quedó fuera del cursor. Se
reanudó **solo** a las 09:32:42 (pos 206, txid 1095), cuando el contador cruzó 1088 **por aritmética,
sin que nadie interviniera**. Esa es la peor forma de autosanarse: la entrega vuelve y el agujero se
queda.

⚠ **La brecha fueron 51 transacciones.** En un clúster de producción con historia real serían millones,
y la ventana de pérdida silenciosa no serían 21 minutos sino semanas.

## 4. Cómo se migró (la causa)

Dump/restore, no `pg_upgrade`: `pg_dump -Fc` con el 16 vivo → `pgdata` movido → `deploy-prod` con
`initdb` de un clúster 18 **vacío** → `pg_restore`. El procedimiento exacto está en el runbook de
`f5sign-infra` (corregido, §5).

Las vías que **preservan** el contador y por tanto no disparan esto —`pg_upgrade`, restore físico con
pgBackRest incluido PITR, `pg_basebackup`, réplica promovida, copia del directorio— están enumeradas en
ese runbook; **enuméralas allí, no desde aquí.**

## 5. Qué cambió, en cada repo

**`f5sign-backend`** — el arreglo (rama `fix/relay-txid-epoch-floor`): `platform.event_checkpoint` gana
`epoch_floor_position` y el relay detecta que el contador retrocedió, rescata lo que la época anterior
no llegó a entregar, y registra la frontera **como una posición** — la única clave de orden que un
restore conserva. Los porqués viven en los docblocks de `EventRelay`, de la migración y del test; no se
replican aquí.

**`f5sign-infra`** — la prevención: `7897df9`, `e5b90b0` y `8005d2a` en `master`. `pg_upgrade` pasa a ser
la recomendación para producción (elimina el fallo por construcción) y queda un gate obligatorio antes
de reabrir tráfico: `pg_current_xact_id() > max(sys_transaction_id)`.

⛔ **Las dos mitades no se sustituyen, y esto se decidió explícitamente.** La detección del backend solo
vive **mientras la brecha está abierta**; si el contador la cierra antes del primer poll del relay, el
arreglo no ve nada. O sea que es *más* fiable cuanto *mayor* es la brecha, y en preprod fueron 51 ids —
que un `pg_restore` grande se come sin despeinarse. El gate manual cubre justo el caso que el código no
puede ver. **No retires el gate argumentando que ya lo repara el backend.**

## 6. ⚑ El culpable falso, que es la lección

Durante horas el silencio de correos se atribuyó a un `MAILER_DSN` mal formado. Era **falso**: el DSN
estaba correcto desde las 09:08:55, cuando se recrearon los contenedores. Lo que confundió fue que un
`messenger:failed:retry` manual (09:32:10) y el cruce aritmético del contador (09:32:42) cayeran con 30
segundos de diferencia, y se atribuyó al primero lo que hizo el segundo.

**El dato que lo destapó fue el hueco de 23 minutos**: si el DSN fuera toda la historia, la cadena habría
revivido a las 09:08:55 y no a las 09:32. Una hipótesis que no explica un intervalo medido no es la
hipótesis.

⚠ Y una segunda trampa: al comprobar los txid se miraron los **rangos** por día, que se solapaban, y se
concluyó que no había desfase de época. Lo que había que comprobar era la **monotonía respecto a la
posición**. Rangos compatibles no implican orden compatible.

## 7. Las 29: por qué NO se replayan

Están en el log, se identifican por consulta y la maquinaria de despacho existe. Aun así no se
replayaron, por dos razones:

- `EventRelay::replayQuarantined()` solo actúa sobre filas **en cuarentena**, y estas nunca se leyeron,
  así que nunca se dead-letearon: las rechazaría una a una.
- Replayarlas hoy mandaría invitaciones a firmar y códigos OTP **reales** con semanas de desfase, a un
  sobre ya sellado que se va a anular igual.

**El valor está en el siguiente incidente**, detectado a los minutos: ahí replayar sí repara.

## 8. Qué queda abierto

- **`BL-198`** (backend) — la reparación se auto-corrige y sigue, y lo único que lo reporta es **una
  línea de log**. Nada cuenta las reparaciones ni expone la frontera.
- **`BL-33`** (backend) — el defecto 1 de este incidente (firmar fuera de orden de paso). Ya existía
  antes; lo que este incidente aporta es que su evaluación de exposición era optimista.
- El defecto 2 (sellado prematuro con pasos abiertos) tiene fila propia; búscala por
  `nextActivatableStepValue` en `docs/BACKLOG.md`.

## 9. Si vuelve a pasar: las tres sondas

```sql
-- 1) ¿retrocede el txid respecto a la posición? El escalón es el bug.
SELECT sys_global_position, sys_transaction_id, occurred_at FROM platform.event_log ORDER BY 1;

-- 2) ¿está el cursor en una época que este clúster no ha emitido?
SELECT consumer, last_transaction_id, last_global_position, epoch_floor_position,
       pg_snapshot_xmax(pg_current_snapshot()) AS next_xid FROM platform.event_checkpoint;

-- 3) EL INVARIANTE. Filas por delante del cursor en POSICIÓN y por detrás en su propio ORDEN.
--    Siempre 0 en salud, así que > 0 es evidencia, no un umbral — y nombra lo que se tragó.
SELECT count(*) FROM platform.event_log l, platform.event_checkpoint c
 WHERE c.consumer = 'event_relay'
   AND l.sys_global_position > GREATEST(c.last_global_position, c.epoch_floor_position)
   AND (l.sys_transaction_id, l.sys_global_position) <= (c.last_transaction_id, c.last_global_position);
```

## 10. Cómo se validó el arreglo

Tres brazos sobre un stack desechable, con `pg_dump`/`pg_restore` **de verdad** y sin falsificar ningún
txid — la brecha fijada en ~199.784 quemando ids en el clúster viejo antes de volcar, para que el
experimento no dependiera de la suerte:

| | A (`develop`) | B (arreglo) | C (arreglo, relay retrasado) |
|---|---|---|---|
| Entregados | **500 / 1000** ❌ | **1000 / 1000** ✅ | **1100 / 1100** ✅ |
| Invariante | 500 ❌ | 0 ✅ | 0 ✅ |
| Log del relay | **nada** | ERROR | ERROR |

El brazo A reprodujo el incidente a voluntad. El C es el que más importa: con el relay parado 100 hechos
antes del final, su log dio `previous_position: 500, epoch_floor_position: 600` — prueba de que los
rezagados salen **antes** de que el suelo caiga sobre ellos. Ese camino es el único que los tests
in-process no alcanzan sin fabricar un `sys_transaction_id`.
