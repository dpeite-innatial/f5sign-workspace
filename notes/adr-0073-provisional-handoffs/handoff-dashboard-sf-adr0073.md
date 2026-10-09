# Traspaso al integrador (BORRADOR PROVISIONAL) — cómo termina un sobre: acuerdo, expiración y política de paso

| | |
|---|---|
| **Origen** | [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md), **Status: Proposed** (redactado 2026-09-24, re-cortado por última vez 2026-09-28 tras nueve rondas de auditoría con decisiones explícitas del mantenedor — no es un borrador sin dueño, pero tampoco está "Accepted"). Lo realizan [TASK-048](../tasks/TASK-048-what-an-unagreed-envelope-keeps.md) (§3.12 es el apartado que promete este traspaso), [TASK-049](../tasks/TASK-049-an-envelope-expires.md) y [TASK-050](../tasks/TASK-050-a-step-says-how-much-agreement-it-needs.md), **las tres en la misma rama** `feat/task-048-how-an-envelope-ends`, construidas en ese orden y **desplegadas juntas**. TASK-048 está en implementación desde el 2026-09-28 (primer commit `ec05e42`); TASK-049 y TASK-050 van después. Sin PR todavía. Sin diseño en TASK-044 (ese es otro traspaso, ya construido); el diseño de este es ADR-0073 completo. |
| **Fecha** | 2026-09-28 |
| **Repos afectados** | `dashboard-sf` (integración de Factor5) |
| **Naturaleza** | Aditivo en su mayor parte (dos enums nuevos, dos campos nuevos por destinatario, dos campos nuevos por sobre, dos eventos nuevos), con **un renombrado de campo** (`void_cause` → `end_cause`, entre otros) y **un cambio de significado que puede esconder un fallo silencioso**: `status: COMPLETED` deja de implicar "acordado". |
| **Acción requerida** | **Avanzar ya, contra mocks**, detrás del contrato descrito aquí. Decisión del mantenedor (2026-09-28): los tres frentes trabajan en paralelo y se prueba de extremo a extremo cuando el backend aterrice. Los nombres marcados como no fijados pueden cambiar: aisladlos en un solo sitio (constantes, tipos, mapeos) para que conciliar con el traspaso oficial sea un cambio pequeño. |
| **Desplegado** | No. En implementación, sin mergear en `develop`. |
| **Status** | **PROVISIONAL — accionable contra mocks** |

**Medido en:**
- `dashboard-sf`: `feat/waybill-pdf-pagination` `a4d8637` (2026-09-23), que es la rama local más avanzada a la fecha de este documento.
- `f5sign-backend`: `feat/task-048-how-an-envelope-ends` `ec05e42` (2026-09-28) — la rama de trabajo actual, que aún no contiene ninguna de las tres tasks; solo la regla de negocio como código puro sin conectar (ver banner de abajo).

---

## ⚑ Esto es un avance, no un traspaso

- **El backend está EMPEZANDO a construirlo ahora**, no lo ha construido. Lo único que existe hoy en el árbol es la regla de negocio como código puro y desconectado: `EnvelopeEndingEvaluator`, `StepCompletionEvaluator` y `ReleaseReasons` en `src/F5Sign/Envelope/Domain/Service/`, ejercitados contra un catálogo de casos (`tests/F5Sign/Envelope/Testing/Scenario/EndingScenarioCatalog.php`). **Nada de esto persiste, bloquea ni publica todavía en la API** — eso es exactamente lo que hacen TASK-048, 049 y 050, en ese orden, en la misma rama.
- **El contrato viene del diseño ya aceptado en ADR-0073**, pero un ADR en `Proposed` puede recortarse de nuevo hasta que aterrice. El propio documento lleva nueve rondas de auditoría registradas (§9 del ADR) en las que nombres, causas y hasta el orden de las columnas cambiaron. **Los nombres y detalles de aquí pueden cambiar.** Lo que es estable es la forma de las decisiones (un `outcome` separado del `status`, un `end_cause` con causas específicas, un `RELEASED` con dos columnas) porque ya sobrevivió a esas nueve rondas.
- **El traspaso oficial llega más tarde**, en `f5sign-backend/docs/frontend-handoff/`, cuando TASK-048 (la primera de las tres) tenga código real, tests y un commit de aterrizaje — con el sha exacto y el `doc.json` real para contrastar, como el resto de traspasos que ya conocéis.
- **Por qué merece la pena leerlo ya de todos modos:** el hallazgo del apartado 1 no es una etiqueta nueva que ignorar sin coste — es un mapeo que hoy funciona por casualidad (`'VOIDED'` y `'EXPIRED'` son literales explícitos) y que, el día que esos dos literales dejen de llegar, caerá en el `default` de un `match` que hoy significa "en progreso".

## Resumen

Con ADR-0073 el backend deja de tener dos formas de terminar un sobre (`COMPLETED` con acuerdo, `VOIDED`/`EXPIRED` sin él) y pasa a tener una sola: **todo sobre que termina llega a `status: COMPLETED`**, y quién ganó se lee aparte, en un campo nuevo `outcome` (`AGREED` \| `NOT_AGREED`) y, si no hubo acuerdo, en `end_cause` (el `void_cause` de hoy, renombrado y con más causas). Además el sobre gana una expiración de verdad (hoy es decorativa) y un paso puede pedir "al menos N de M" en vez de "todos", con una fecha límite propia.

| # | Qué | Prioridad |
|---|---|---|
| 1 | `envelopeStatus()` deja de distinguir agreed / not-agreed: hay que leer `outcome` | **alta — el hallazgo crítico** |
| 2 | `void_cause` se renombra a `end_cause`, con más causas | **alta** (va con el 1, mismo despliegue) |
| 3 | `recipientStatus()` no tiene rama para `RELEASED`: cae en `PENDING` para siempre | media |
| 4 | `void()` puede empezar a refusarse antes de lo que refusa hoy | media |
| 5 | Expiración: vuestro DTO ya lleva `expirationDays` sin usar | baja/media, oportunidad |
| 6 | `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` se retira | informativo — no os afecta |
| 7 | Política de paso (`AT_LEAST n`, veto, deadline) | informativo — no la usáis hoy |
| 8 | Webhooks salientes: catálogo real vs. el que espera vuestro handler dormido | informativo |
| 9 | Mensajes de error (`F5SignErrorMessages`) | baja |

Los cambios de contrato completos están en el apartado "Lo que va a cambiar en el contrato".

## 1. `envelopeStatus()` deja de distinguir un sobre acordado de uno que no lo está (prioridad alta)

**Qué pasa hoy** (medido en `src/Service/TransportRequest/Signature/F5Sign/F5SignApiGateway.php:678-690`):

```php
private function envelopeStatus(string $backendStatus, ?string $voidCause = null): SignatureStatus
{
    return match ($backendStatus) {
        'DRAFT' => SignatureStatus::NONE,
        'SENT' => SignatureStatus::SENT,
        'COMPLETED' => SignatureStatus::COMPLETED,
        'VOIDED' => 'RECIPIENT_DECLINED' === $voidCause ? SignatureStatus::DECLINED : SignatureStatus::VOIDED,
        'EXPIRED' => SignatureStatus::EXPIRED,
        'ROUTING_FAILED', 'SEALING_FAILED' => SignatureStatus::FAILED,
        // READY_TO_SEAL / SEALING / CORRECTING, and anything not yet known here.
        default => SignatureStatus::IN_PROGRESS,
    };
}
```

Este método traduce el `status` del backend a vuestro propio enum (`src/Enum/Signature/SignatureStatus.php`: `NONE/SENT/IN_PROGRESS/COMPLETED/DECLINED/VOIDED/EXPIRED/FAILED`), y distingue los tres desenlaces sin acuerdo (`VOIDED` por el emisor, `VOIDED` por un rechazo bloqueante, `EXPIRED`) mirando el literal `'VOIDED'`/`'EXPIRED'` del backend y, dentro de `VOIDED`, el `void_cause`.

**Qué cambia.** Con ADR-0073, `status` **nunca vuelve a valer `'VOIDED'` ni `'EXPIRED'`** — los dos se retiran del enum del backend (ADR-0073 §2.5, §2.12). Todo sobre que termina, con acuerdo o sin él, llega como `'COMPLETED'`; el desenlace se lee en dos campos nuevos:

- `outcome`: `AGREED` \| `NOT_AGREED`.
- `end_cause` (el `void_cause` de hoy, renombrado): `SENDER_VOIDED`, `RECIPIENT_DECLINED`, y tres causas nuevas de TASK-050 (`RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED`) más `EXPIRED` de TASK-049. Vacío (`null`) cuando `outcome: AGREED`.

**El riesgo, dicho sin rodeos.** Con el `match` de arriba sin tocar, el día que se despliegue TASK-048/049/050: el brazo `'VOIDED' => ...` y el brazo `'EXPIRED' => ...` se quedan **muertos** (esos literales ya no llegan nunca), y el `'COMPLETED' => SignatureStatus::COMPLETED` **captura todo** — un sobre anulado por el remitente, un rechazo bloqueante, o una expiración se leerían como `SignatureStatus::COMPLETED`, es decir, **como una carta de porte firmada correctamente**. No es un campo que deje de rellenarse: es un dato que pasa a significar lo contrario de lo que dice.

Y hay un segundo efecto, más silencioso todavía: `src/Command/TransportRequest/RefreshWaybillSignaturesCommand.php:61-65` limita el barrido periódico a `LIVE_STATUSES = [SENT, IN_PROGRESS, FAILED]` — un `SignatureStatus::COMPLETED` sale de esa ventana de sondeo, así que el estado incorrecto no se corrige solo; se queda fijado la primera vez que se lee tras el despliegue.

**Qué habrá que hacer** (cuando exista el traspaso oficial, no antes):

1. `envelopeStatus()` deja de recibir solo `status`/`void_cause`; necesita también `outcome` y `end_cause` (renombrado) para poder seguir devolviendo vuestro `DECLINED`/`VOIDED`/`EXPIRED`/`COMPLETED` de siempre. La forma exacta (parámetros nuevos, o un DTO pequeño) es vuestra: el backend solo fija los nombres de los campos.
2. `getStatus()` (línea 338) pasa a leer `$data['outcome']` y `$data['end_cause']` en vez de solo `$data['void_cause']`.
3. Mantener el `default => IN_PROGRESS` para `READY_TO_SEAL`/`SEALING`/`CORRECTING` sigue siendo correcto — esos no cambian.

## 2. Renombrados de campo en el sobre (prioridad alta, va con el punto 1)

| Campo hoy | Pasa a llamarse | ¿Lo leéis hoy? |
|---|---|---|
| `void_cause` | `end_cause` | **Sí** — `F5SignApiGateway.php:338` y `:684` |
| `voided_at` | `closed_at` | No — cero apariciones en el repo |
| `voided_by` | `ended_by` | No — cero apariciones |
| `voided_by_recipient_id` | `ended_by_recipient_id` | No — cero apariciones |
| `void_reason` | `end_reason` | No — cero apariciones |

Solo el primero os afecta de verdad; los otros cuatro los medimos con `grep` en todo `src/` y son cero. `end_cause` gana además valores nuevos frente a `void_cause` (ver apartado 1) — el `match`/`switch` que lo lea en el futuro debería tratar un valor no reconocido como "no agreed, causa desconocida" en vez de fallar, por la misma razón que ya seguís en `envelopeStatus()` con el `default`.

El campo que enviáis hacia el backend en `void(string $envelopeId, string $reason)` (`F5SignApiGateway.php:486-490`, cuerpo `{"reason": ...}`) **no cambia** — el renombrado es solo de lectura, en `GET /envelopes/{id}`.

## 3. `recipientStatus()` no tiene rama para `RELEASED` (prioridad media)

**Qué pasa hoy** (`F5SignApiGateway.php:738-748`):

```php
private function recipientStatus(string $outcome): RecipientSignatureStatus
{
    return match ($outcome) {
        'COMPLETED' => RecipientSignatureStatus::SIGNED,
        'DECLINED' => RecipientSignatureStatus::DECLINED,
        // PENDING / DELEGATED / SKIPPED — none of them is a finer step of this signer's
        // progress. ...
        default => RecipientSignatureStatus::PENDING,
    };
}
```

Con ADR-0073, `outcome` de un destinatario gana `RELEASED` — cerrado sin haber actuado, por deadline de su paso, por cierre anticipado del emisor, o por expiración del sobre (TASK-048 §3.4, §2.8 del ADR). Con el `match` de arriba sin tocar, un destinatario `RELEASED` **cae en el `default` y se lee como `PENDING`** — es decir, para siempre "esperando a que firme", cuando en realidad su turno ya pasó y nadie está esperando nada de él. Menos grave que el apartado 1 (no convierte un fallo en un éxito), pero sí deja la franja de trazabilidad de una carta de porte diciendo "pendiente" de un destinatario que el sistema ya dio por perdido.

Curiosamente, el propio repo ya tiene la advertencia general escrita: `src/Service/TransportRequest/Signature/F5Sign/F5SignErrorMessages.php:58-62` comenta, sobre otro enum del backend, que derivar un código de "ya no puede actuar" de una lista de outcomes "se rompe en silencio el día que añaden un outcome terminal" — es exactamente lo que le pasaría a `recipientStatus()` con `RELEASED`.

**Qué habrá que hacer:** añadir un brazo `'RELEASED' => RecipientSignatureStatus::???` — vuestro propio enum (`RecipientSignatureStatus`) no tiene hoy un valor equivalente a "cerrado sin actuar"; decidir si reutilizar `DECLINED` (que hoy dispara `WaybillSignatureDeliveryLinker` como entrega fallida, `WaybillSignatureDeliveryLinker.php:216`) es correcto para un `RELEASED`, o si hace falta un valor propio, es una decisión vuestra que conviene tomar cuando exista el traspaso real y se sepa el `release_reason` que lo acompaña (no todo `RELEASED` es lo mismo: un destinatario que nunca abrió el enlace no es lo mismo que uno cuya invitación falló).

## 4. `void()` puede empezar a refusarse antes de lo que refusa hoy (prioridad media)

`WaybillController.php:430-435` y `WaybillSignatureController.php:637-652` dejan cancelar (llaman a `gateway->void()`) mientras el estado local sea `SENT`, `IN_PROGRESS` o `FAILED`, y hoy el backend solo refusa el void con `ENVELOPE_REACHED_AGREEMENT` una vez el sobre llega a `READY_TO_SEAL` (todas las firmas bloqueantes ya están en el PDF). Vuestro `F5SignErrorMessages.php` ya tiene mensaje propio para ese código (línea ~87).

Con ADR-0073, un void se refusa desde el instante en que el **acuerdo queda asegurado** (`agreed_at`, ADR-0073 §2.2), que es un instante **anterior** a `READY_TO_SEAL`: ya no hace falta que las firmas hayan terminado de estamparse en el PDF, basta con que el último firmante bloqueante haya cometido su firma. Para vuestro flujo — un firmante por paso, todos `ALL` — la ventana entre "el último firmante cometió" y "el PDF terminó de estamparse" es normalmente de segundos, así que el efecto práctico es pequeño; pero es una ventana real donde hoy un cancel podría colarse y con ADR-0073 se refusará con el mismo `ENVELOPE_REACHED_AGREEMENT` de siempre, sin necesitar un código nuevo. No es una acción vuestra hoy — es una diferencia de comportamiento a tener en cuenta si alguna vez un operador reporta "no me deja cancelar y el estado seguía SENT".

## 5. Expiración: vuestro DTO ya tiene un campo sin usar (prioridad baja/media, oportunidad)

`src/Service/TransportRequest/Signature/Dto/EnvelopeRequest.php:22-23` ya lleva un campo `expirationDays`, construido en `WaybillEnvelopeService.php` (línea ~836-843, `buildEnvelopeRequest()`) a partir de `$this->signatureExpirationDays` — pero **nunca se envía**: `F5SignApiGateway::createEnvelope()` (línea 78-85) construye el `POST /envelopes` con solo `{title, workflow_type, signing_mode}`. Es un dato calculado y luego descartado.

Con TASK-049, `POST /envelopes` admite un duración opcional (1–180 días, 30 por defecto) que se resuelve a `expires_at` en el envío. Cuando ese campo exista de verdad en el backend, conectar `expirationDays` con el `POST` os deja elegir vuestra propia ventana en vez del valor por defecto — hoy es exactamente el dato que ya calculáis y tiráis.

Nota aparte, sin relación directa con ADR-0073 pero descubierta mirando el mismo sitio: `RefreshWaybillSignaturesCommand.php:42-44` asume en un comentario que "the platform expires an envelope after `SIGNATURE_EXPIRATION_DAYS` (7)" para dimensionar la ventana de 30 días del sondeo — 7 días es la vida del **enlace de firma** (`StoreBackedSigningTokenIssuer::LIFETIME`), no la expiración del **sobre**, que hoy son 30 días fijos desde la creación y con TASK-049 será configurable hasta 180. Vale la pena revisar esa ventana de sondeo cuando `expires_at` se publique de verdad, para que cubra sobres con una vida larga.

## 6. `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` se retira (informativo, no os afecta)

Es un código de `POST /api/v1/signing/decline`, una ruta que solo llama la app del firmante (el signer) con credencial de sesión. Vuestro commit delegado (`commitDelegatedSignature()`, `F5SignApiGateway.php:401`) firma, nunca rechaza — y confirmado por `grep`: cero apariciones de `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` ni de `SESSION_ALREADY_DECLINED` en todo `dashboard-sf`. Se incluye aquí solo por completitud del catálogo que pide este traspaso.

## 7. Política de paso — `AT_LEAST n`, veto, deadline (informativo, no la usáis hoy)

`F5SignApiGateway.php:109-117` crea un paso por cada ordinal distinto de destinatario, con el cuerpo `{"ordinal": N}` únicamente — nunca `min_signatures`, nunca nada de quórum. Confirmado por `grep`: cero apariciones de `min_signatures`/`quorum` como dato en todo el repo. TASK-050 añade `completion` (`ALL` por defecto o `AT_LEAST n`), un `veto` y un `deadline` opcionales al mismo `POST /envelopes/{id}/steps` — son **aditivos**: vuestra llamada de hoy, sin esos campos, sigue significando exactamente lo mismo (`ALL`, sin deadline).

Vale la pena citar un comentario que ya está en vuestro propio código, porque describe justo el escenario que TASK-050 hace posible: `WaybillEnvelopeService.php:426-429` dice, sobre por qué no hace falta cierta comprobación hoy, *"no step of ours closes on a quorum that could leave a member unacted. Add a CC/viewer recipient — or a quorum — and this comment becomes a bug report"*. Si алgún día Factor5 quiere agrupar varios destinatarios en un mismo paso con "al menos N firman" (el caso de varios consignatarios en un mismo reparto, que es justo el ejemplo que usa ADR-0073 para justificar la política), ese comentario es la señal de que hay que revisitarlo.

## 8. Webhooks salientes: el catálogo real, para cuando se activen (informativo)

Confirmado: `SignatureWebhookReceiver.php:15-25` sigue sin emisor — el backend no manda webhooks salientes a nadie hoy (solo se sondea, `F5SignApiGateway::getStatus()`). El handler (`WaybillSignatureWebhookHandler.php`) está escrito y probado, pero dormido.

Si alguna vez se activa de verdad, tres cosas a tener en cuenta contra el catálogo **real** del backend ([ADR-0064](ADR-0064-outbound-integrator-webhooks.md) §2.4, no el que vuestro handler da por hecho):

- **Los nombres de evento no coinciden.** Vuestro `match` (línea 65-75) escucha `recipient.notified`, `recipient.viewed`, `recipient.claimed`, `recipient.assigned`, `envelope.expiration_warning` — ninguno de esos existe en el catálogo publicado por el backend (que es: `envelope.created`, `envelope.sent`, `envelope.completed`, `envelope.voided`, `envelope.recipient_completed`, `envelope.recipient_corrected`, `envelope.recipient_delivery_failed`, `envelope.step_completed`, `signature.document_signed`, `signature.recipient_signed`, `signature.envelope_sealed`). Esto es anterior a ADR-0073 — no lo causa, pero lo hace más visible: no hay caso para `envelope.voided` en absoluto, así que hoy, si llegara, se ignoraría en silencio (cae en el `default => null` de la línea 74).
- **`'envelope.expired'` (línea 72) nunca se va a emitir, ni antes ni después de ADR-0073.** Ya estaba reservado sin escritor (ADR-0064 §2.4); con ADR-0073 §2.12 queda confirmado para siempre: la expiración se publica como `envelope.voided` con `data.end_cause: EXPIRED`. Ese brazo del `match` es código muerto por construcción.
- **`envelope.completed` (línea 71) pasa a cubrir los dos desenlaces.** Hoy `onEnvelopeCompleted()` fija incondicionalmente `SignatureStatus::COMPLETED` cuando llega. Con ADR-0073 este evento se dispara también cuando el sobre termina `NOT_AGREED` (voided, rechazado o expirado) — así que, si alguna vez se activa de verdad, tendría que leer `data.outcome` en vez de asumir "completado" siempre. Dos eventos nuevos se suman al catálogo: `envelope.agreed` (el instante en que el acuerdo queda asegurado, antes del cierre) y `envelope.recipient_released`.
- El comentario de `onRecipientDeclined()` (líneas 141-144) — *"the envelope status is left to the poll, which reads `void_cause`"* — sigue siendo cierto en espíritu (el evento de un rechazo no dice si terminó el sobre entero), pero la palabra exacta pasa a ser `end_cause`.

## 9. Mensajes de error (prioridad baja)

`F5SignErrorMessages.php` ya traduce buena parte del catálogo actual de `ProblemCode` a mensajes propios (`keyFor()`, líneas 38-118) — incluido `ENVELOPE_REACHED_AGREEMENT` (línea ~87). Cuando exista el traspaso real, revisar si el código nuevo del commit de un rol informativo (TASK-050 §3.2, nombre aún sin fijar) o los de la ruta de extensión de expiración (TASK-049 §3.2, también sin nombre fijado) merecen mensaje propio o basta con el genérico por `statusKey()` (líneas 149-160).

## Lo que va a cambiar en el contrato

**`GET /api/v1/envelopes/{id}` — el sobre:**

| Campo | Hoy | Con ADR-0073 |
|---|---|---|
| `status` | incluye `VOIDED`, `EXPIRED` | se retiran ambos; `COMPLETED` = terminó, con o sin acuerdo |
| `outcome` | no existe | nuevo: `AGREED` \| `NOT_AGREED` |
| `end_cause` (antes `void_cause`) | `SENDER_VOIDED`, `RECIPIENT_DECLINED` | + `RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`, `STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED`, `EXPIRED` |
| `voided_at`/`voided_by`/`voided_by_recipient_id`/`void_reason` | así | renombrados a `closed_at`/`ended_by`/`ended_by_recipient_id`/`end_reason` |
| `agreed_at`, `completed_at` | no existen | nuevos |
| `expires_at` | no se publica | nuevo, publicado |

**`GET /api/v1/envelopes/{id}` — cada destinatario:**

| Campo | Hoy | Con ADR-0073 |
|---|---|---|
| `outcome` | `PENDING, COMPLETED, DECLINED, DELEGATED, SKIPPED` | + `RELEASED` |
| `release_reason` | no existe | nuevo: `NOT_REQUIRED`, `INTEGRATOR_NO_ACT`, `OPENED_NO_ACT`, `DELIVERY_FAILED`, `UNCLAIMED`, `NOT_REACHED`, `LINK_EXPIRED`, `SENT_NO_RESPONSE` |
| `released_by` | no existe | nuevo: `STEP_DEADLINE`, `EXPIRY`, `SENDER_CLOSED`, `ENVELOPE_CLOSED` |

**`POST /api/v1/envelopes` (creación):** gana un campo opcional de duración de vida (1–180 días, 30 por defecto) — nombre exacto aún no fijado en las tasks.

**Ruta nueva de extensión de expiración**, sobre un sobre vivo: URL exacta no fijada; refusalas nombradas: cerrado, ya pasada la fecha, por encima del tope de 180 días, o hacia atrás.

**Ruta nueva de cierre anticipado ("close-now")**, del emisor: cierra un sobre con el acuerdo ya asegurado, liberando a quien quede pendiente con `released_by: SENDER_CLOSED`. URL exacta no fijada.

**`POST /api/v1/envelopes/{id}/steps`:** gana, de forma aditiva, `completion` (`ALL` por defecto o `AT_LEAST n`), `veto` (booleano, solo con `AT_LEAST`) y un `deadline` opcional (duración ≥ 24h). Vuestra llamada de hoy (`{ordinal}` solo) sigue significando lo mismo.

**`POST /api/v1/signing/decline`:** `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` se retira del catálogo de `ProblemCode` — no os afecta, no llamáis esta ruta.

**Eventos/webhooks (§2.4, §2.11 de ADR-0073, sobre el catálogo de ADR-0064):**
- `envelope.completed` pasa a dispararse para los dos desenlaces, con `outcome` en el `data`.
- `envelope.expired` sigue confirmado sin emitirse nunca — la expiración es `envelope.voided` con `end_cause: EXPIRED`.
- Dos eventos nuevos: `envelope.agreed` (al asegurarse el acuerdo, puede ser días antes del cierre) y `envelope.recipient_released` (con `release_reason` y `released_by`).
- `EnvelopeVoided` (el hecho interno detrás de `envelope.voided`) gana un matiz: cuando lo dispara una expiración, no tiene parte (`ended_by`/`ended_by_recipient_id` nulos) — los campos de parte se vuelven anulables en el evento publicado.

## Lo que NO está listo todavía

- **Los nombres exactos de dos `ProblemCode` nuevos** (el rechazo del commit de un rol informativo, y los de la ruta de extensión de expiración) — las tasks dicen que existirán, no cómo se llaman.
- **Las URLs exactas de las dos rutas nuevas** (extensión de expiración, cierre anticipado).
- **Todo lo que ADR-0073 deja fuera explícitamente** (§2.18): avanzar con el mínimo alcanzado sin esperar al resto, pasos con miembros obligatorios y opcionales mezclados, veto por destinatario, votos con peso, ventanas por destinatario, extender el deadline de un paso ya activo, agregar varios sobres como una unidad (`PARTIALLY_AGREED`), motor de decisión, dependencias en un sentido, decline por documento, decline delegado, anotación de disputa, una marca visible en el PDF de que fue anulado, reenvío automático de invitación, "conservar siempre", una puerta más débil para el rechazo.

## Lo que NO existirá, y por qué

- **Un `VOIDED` o `EXPIRED` como estado propio, nunca más.** ADR-0073 lo decide explícitamente (§2.5): "un lifecycle, el resultado es un campo" — separar la fase (`status`) del resultado (`outcome`/`end_cause`) es la razón de ser de todo el ADR, no un detalle de implementación que pueda revertirse en el camino.
- **Un ProblemCode por cada causa de `end_cause`.** El rechazo del void y del cierre anticipado siguen respondiendo con el mismo `ENVELOPE_REACHED_AGREEMENT`/`CONFLICT` de siempre; la causa fina vive en el campo `end_cause` del sobre, no en el código del error, exactamente como hoy `void_cause` no tiene un código de error propio.

## Cómo verificarlo desde el integrador (cuando exista el traspaso real, no antes)

- **Antes de tocar código:** el `doc.json` del despliegue que os sirva tiene que listar `outcome`, `end_cause` (no `void_cause`), `release_reason` y `released_by` en el esquema `Envelope`/`Recipient`, y el enum de `status` ya no debe tener `VOIDED` ni `EXPIRED`. Si no, ese despliegue no lleva TASK-048/049/050.
- **El caso crítico del apartado 1:** un sobre con un rechazo bloqueante (o anulado, o expirado) debe devolver `status: COMPLETED`, `outcome: NOT_AGREED`, `end_cause` con la causa concreta — nunca dejéis que un `envelopeStatus()` sin actualizar lo lea como `COMPLETED` a secas.
- **`RELEASED`:** un destinatario cuyo paso venció sin que actuara debe traer `outcome: RELEASED`, `release_reason` y `released_by` — no `PENDING`.

---

*Este documento vive solo en el scratchpad de esta sesión. No se ha escrito ni se va a escribir en ningún repo — cuando TASK-048 aterrice en `develop`, el traspaso real (en `f5sign-backend/docs/frontend-handoff/`) sustituye a este.*
