# Catálogo de flujos de firma — ADR-0073 contra código

- **Rama:** `feat/ending-without-agreement`, commits `acbbddb3` (código y tests) y `200eb2c5` (docs). Sin push.
- **Qué es:** las reglas de decisión del ADR (admisión, aseguramiento, cierre, relojes, liberaciones, rechazos de
  `send()`) como código puro que el agregado llamará: `EnvelopeEndingEvaluator`, `StepCompletionEvaluator` y
  `ReleaseReasons`, en `src/F5Sign/Envelope/Domain/Service/`. Contra ese código se ejecuta un catálogo de
  historias: `tests/F5Sign/Envelope/Testing/Scenario/EndingScenarioCatalog.php`.
- **Verificado en el lane `wt-backend` sobre este árbol:**
  - 680 tests nuevos en verde, y los tiers Unit + Application completos (3310) también;
  - PHPStan nivel 9, deptrac y el lint, limpios;
  - tres sabotajes deliberados, y cada uno pone en rojo el escenario que lo nombra.
  - Integration y Acceptance no se ejecutaron: no hay persistencia ni HTTP todavía.

## Lo que encontró el catálogo

- **(a) de TASK-048.** En un sobre de dos firmantes, al firmar el segundo el sobre queda asegurado **y cerrado** a la
  vez. Una anulación en ese momento se habría rechazado como "sobre cerrado", pero la barra pide que se rechace
  nombrando el acuerdo asegurado. Corregido: la anulación de un acuerdo asegurado nombra siempre el acuerdo.

## Los escenarios

El waybill base: el cargador (paso 1, `ALL`), el transportista (paso 2, `ALL`) y los consignatarios A, B y C (paso 3).
"Con firma final" añade un paso 4 con el cargador cerrando. Las liberaciones se leen *motivo · qué liberó*.

| # | Historia | Resultado esperado (y verificado) |
|---|---|---|
| 1 | (g) A firma el día 0; anular se rechaza; B firma el día 1; C nunca abre; vence el plazo de 2 días | `AGREED`, asegurado el día 0; C `SENT_NO_RESPONSE · STEP_DEADLINE` |
| 2 | (j) Igual, sin plazo; A firma; nadie más; expira a los 30 días | `AGREED`; B y C `NOT_REACHED · EXPIRY` (su enlace de 7 días ya caducó) |
| 3 | Cierre anticipado: A firma, B abre y no firma, el remitente cierra | `AGREED` por el remitente; B `OPENED_NO_ACT · SENDER_CLOSED`; C `SENT_NO_RESPONSE · SENDER_CLOSED` |
| 4 | Cierre anticipado antes de asegurar | Rechazado: acuerdo no asegurado |
| 5 | (a) Con firma final: C declina, A y B firman, paso 4 firma | `AGREED`, C queda como declinado |
| 6 | (b) Los tres consignatarios declinan | `NOT_AGREED · MINIMUM_UNREACHABLE` en el tercero; el paso 4 `NOT_REACHED · ENVELOPE_CLOSED` |
| 7 | (c) El transportista declina | `NOT_AGREED · RECIPIENT_DECLINED`, parte: el transportista |
| 8 | (d) A firma, C declina, B nunca abre; vence el plazo; B intenta firmar; paso 4 firma | B `SENT_NO_RESPONSE · STEP_DEADLINE`, su firma posterior se rechaza; `AGREED` |
| 9 | (e) Un slot sin reclamar y dos declinan; vence el plazo | Espera hasta el plazo; `NOT_AGREED · STEP_DEADLINE_MISSED`; slot `UNCLAIMED · STEP_DEADLINE` |
| 10 | D13: paso 3 `AT_LEAST 1` sin plazo, con firma final; A firma; expira | `NOT_AGREED · EXPIRED` aunque se cumplió el mínimo (lo aceptaste y se documenta) |
| 11 | Expira en el hueco: el paso 3 cerró por plazo y el 4 espera aterrizajes | `NOT_AGREED · EXPIRED` |
| 12 | Un solo barrido con plazo y expiración vencidos | Primero cierra el plazo, luego la expiración encuentra el paso 4 pendiente: `NOT_AGREED · EXPIRED` |
| 13 | (f) Consejo `AT_LEAST 3` de 5 con veto: tres firman, el cuarto declina | `NOT_AGREED · RECIPIENT_VETOED`, parte: ese consejero |
| 14 | (f) en otro orden: el veto llega antes de ninguna firma | Igual |
| 15 | (h) Tres firman, uno calla, a otro le rebotó la invitación; vence el plazo | `NOT_AGREED · MEMBER_NOT_REACHED` |
| 16 | Consejo, todos alcanzados: tres firman, dos callan; cierre anticipado antes del plazo | Rechazado (con veto no hay aseguramiento hasta el cierre); al plazo, `AGREED` |
| 17 | Precedencia de causas: veto con un no alcanzado y el mínimo imposible, por plazo | `MEMBER_NOT_REACHED` |
| 18 | Lo mismo cerrado por expiración | `MEMBER_NOT_REACHED` (mismos hechos, mismo resultado) |
| 19 | (i) Dos firmantes y un VIEWER en el paso siguiente | Asegurado al segundo; el paso del viewer se activa y cierra a la vez: `AGREED`; viewer `NOT_REQUIRED · ENVELOPE_CLOSED` |
| 20 | Copia de cortesía en el mismo paso: intenta firmar y declinar; abre | Ambos rechazados; no retiene el paso; `OPENED_NO_ACT · ENVELOPE_CLOSED` |
| 21 | Paso solo informativo en medio | Cierra al activarse y se abre el siguiente |
| 22 | (b de TASK-048) Anulación a mitad de firma | La firma admitida se queda; `NOT_AGREED · SENDER_VOIDED`, por el remitente; el resto `ENVELOPE_CLOSED` |
| 23 | (a de TASK-048) Anular tras la segunda firma | Rechazado: acuerdo asegurado (el hallazgo de arriba) |
| 24 | TASK-049: dos firmantes `ALL`, firma uno, se amplía, expira | `NOT_AGREED · EXPIRED`, sin parte; el otro `SENT_NO_RESPONSE · EXPIRY` |
| 25 | Firmado un minuto antes de la fecha | `AGREED`: decide el instante de admisión |
| 26 | Firmar pasada la fecha, antes del barrido | Rechazado: expirado |
| 27 | Firmar pasado el plazo del paso, antes del barrido | Rechazado; luego `STEP_DEADLINE_MISSED` |
| 28 | Firmar en un paso aún no activo | Rechazado |
| 29 | B2B: aprobación y luego firma | `AGREED`, asegurado en la firma |
| 30 | Miembro firmado por el integrador que nunca actúa | `INTEGRATOR_NO_ACT · STEP_DEADLINE` (cuenta como alcanzado) |
| 31 | Invitación rebotada y reenviada con éxito | `SENT_NO_RESPONSE`, no `DELIVERY_FAILED` |
| 32 | Enlace enviado hace más de 7 días | `NOT_REACHED` |

Además:
- **Mismos hechos, mismo resultado:** 625 combinaciones (5 políticas × 5 estados posibles de cada uno de 3
  miembros), cerradas por plazo y por expiración. Salen iguales, salvo el nombre del reloj en la causa.
- **Tests focalizados:** el orden de los siete motivos de liberación y cada rechazo de `send()`, incluida la
  unanimidad como `AT_LEAST`.

## Qué no cubre todavía

Concurrencia, locks, relojes de la base de datos (`app_now()`), la migración y las rutas HTTP: necesitan el
agregado y la persistencia, y son de TASK-048/049/050. Cuando el agregado llame a estas reglas, el mismo catálogo
será su oráculo, y más tarde el de las barras HTTP.
