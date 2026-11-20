# `docs/frontend-handoff/` — what a backend change requires of the front ends

A handoff record says **what changed in this repo's published contract, and what `f5sign-dashboard` or
`f5sign-signer` must now do about it**. It is written for a reader who is working in *that* repo, quite
possibly without this one checked out.

## Why this directory exists

Cross-repo changes are **two coordinated PRs**, never one commit — the workspace rule that keeps each
project's history its own. So a contract change here and its adoption over there are separated in time, by
different changesets, often by different sessions. Nothing carried the information across that gap.

The cost is already on the board. The signer's completed screen gates its download button on a
`signed_copy_url` that this backend **never sends**, so the button has been permanently hidden — while
`GET /api/v1/signing/session` has been emitting the working URL the whole time as `documents[].download_url`,
served by `DownloadSigningDocumentController`. **Nothing was missing on either side**: the key carries a
different name and lives per **document**, not per session. That fact lived only in a PHP docblock, where no
front-end agent would ever read it — which is worse than a missing field, because both repos were complete
and still could not meet.

This directory is where that kind of fact goes instead.

## When one gets written

Whenever a change touches something a front end consumes: `src/**/UI/Http/`, `config/routes/`, any
`#[OA\*]` attribute, a `Contract/` type the API emits, an enum whose values cross the wire, a CORS rule or
required header, or an env var the front end needs. `docs-sync` writes it as part of the same changeset.

**One file per change, not per release:** `TASK-NNN-<slug>.md`, or `YYYY-MM-DD-<slug>.md` when the change
does not come from a task.

## Shape

```markdown
# Traspaso al frontal — <what changed, in one line>

| | |
|---|---|
| **Origen** | branch · commit `<sha>` · PR if there is one |
| **Fecha** | YYYY-MM-DD |
| **Repos afectados** | dashboard / signer / both |
| **Naturaleza** | additive · **breaks the contract** · corrects the published spec |
| **Acción requerida** | none · update types · handle a new state · **migrate before <date>** |
| **Desplegado** | not yet · `<env>` since YYYY-MM-DD — see rule 4 |
| **Status** | Pending · Applied (`<repo>` `<pr|sha>`, YYYY-MM-DD) |

## Lo que cambió en el contrato
## Lo que el frontal tiene que hacer
## Lo que NO está listo todavía
## Lo que NO existirá, y por qué   <- only when something was decided against; see rule 3
## Cómo verificarlo desde el frontal
```

## The four rules that keep it from lying

1. **Never copy the spec.** The OpenAPI document Nelmio generates is the machine-readable truth. Restating
   a schema here guarantees the two diverge, and the front end will believe the wrong one. Say **what
   changed and what to do**; point at the spec for shapes.
2. **Always name the origin commit.** It is the only thing that lets a reader tell whether the handoff is
   already applied or whether they are behind.
3. **Always say what is not ready — and say SEPARATELY what will never exist.** Half the value is stopping
   work against a half-built seam. A handoff that only lists opportunities invites the front end to build
   against something that will move.

   ⛔ **The two are different claims and the section heading below conflates them.** *"Lo que NO está listo
   **todavía**"* has an implied *yet*, so an absence filed there reads as a promise with no date — and a
   consumer who needs the thing will write code against it and wait. **A decided absence is not a gap**, and
   it is the one a reader cannot infer, because a missing route looks identical whichever it is.

   ⚑ **Measured, 2026-08-21, and this rule exists because of it.** The `factor5_dashboard_sf` session — an
   external consumer — shipped a `notifyRecipient()` pointing at `POST …/recipients/{id}/resend`, a route
   **we never announced and never intended**, with a comment beside it reading *"it lights up unchanged once
   the backend ships the route."* Nobody made them that promise; they inferred it from the silence. They
   found out only by asking. ⚠ **And the inference was reasonable**, which is the part to keep: `corrections`
   is published as *"correct a recipient's contact details and **re-send their invitation**"*, so a
   sender-side re-send visibly exists — just not for the code. An asymmetry we never wrote down is one the
   reader will resolve for themselves, in whichever direction their feature needs.

   ⚑ **Postscript, 2026-08-31, and it sharpens the rule rather than softening it.** The *gesture* they
   inferred was built — `POST …/recipients/{rid}/resends`, a sender-side re-send of the **invitation**
   ([TASK-041](TASK-041-invitation-resend.md)) — while the absence that was actually decided, a
   sender-side re-send of the **code**, stands untouched. So the inference was right about the half they
   could see and wrong about the half they could not, at a path nobody would have guessed. ▶ Read that as
   the argument *for* writing both records, not against: the decided absence had to be written down to stay
   decided, and the built half had to be handed over to be reachable. Neither was inferable from silence,
   and silence would have got one of them wrong whichever way the reader leaned.

   ▶ So when a thing is decided *against*, give it its own record with the reason, and file it under
   **`## Lo que NO existirá, y por qué`**. The reason is what makes it stick: *"no habrá reenvío de
   remitente"* invites a re-ask next quarter, and *"…porque el reenvío es una ruta anónima que gasta dinero
   y el código va ligado a la sesión del firmante"* does not.

4. **Say whether it is DEPLOYED, not only whether it is merged.** `Origen` names a commit, which answers
   *does this exist in the repo* — a different question from *can I call it today*, and the front end can
   only act on the second.

   ⚑ **Measured: three times in one week** (2026-08-21) a consumer of this API was blocked by that
   distinction alone — TASK-023, TASK-032, and the `ProblemCode` catalog, each landed on `develop` and
   each absent from what their stack was being served. The third time they checked the served `doc.json`
   *before* building rather than after, which is the good outcome and is why it cost nothing.

   ⛑ **The consumer's own rule is the better control and it is theirs, not ours** — *do not adopt a field
   until the `doc.json` of the deployment that serves you publishes it.* It is verifiable by the party who
   needs the answer, which a promise from us is not. This field does not replace it; it saves them a round
   trip and stops us writing *"shipped"* when we mean *"merged"*.

   ⚠ **`develop` is not a deployment.** In this workspace the running stack bind-mounts the **main
   checkout**, which is frequently several commits behind — it was **8 behind** on the day this rule was
   written. Merging changes nothing about what is served.

## ⚠ The weak spot, stated rather than hidden

**`Status` is hand-maintained, and nobody owns flipping it.** The front-end PR that applies a handoff lands
in *another repo*, and it cannot edit this one — so `Applied` gets written here only if somebody comes back
to do it. That is precisely the shape of claim this repo keeps finding stale.

⛔ **And it fails in BOTH directions, which was measured on 2026-08-21 — once each, within hours.** The
TASK-032 handoff sat at `Pending` while the signer had already applied three of its four pieces. Then the
`no-sender-side-otp-resend` record was written straight to `Applied`, on the strength of a consumer saying
*"lo arreglamos por aquí"* in conversation — **an intention, minuted as a fact**. Their session came back to
correct it, unprompted: *"prefiero que vuestro registro esté bien a que nos deje bien."*

⚑ **The under-claim is the harmless one and the over-claim is not**, so the asymmetry is worth naming: a
stale `Pending` makes somebody re-check work that is done, while a premature `Applied` closes a loop nobody
closed and removes the reason anyone would look again. ▶ **The rule that falls out: `Applied` is written
from the other repo's tree, never from its session's sentence.** If you cannot see the tree, write what
they reported, attribute it, and date it — which is what that record's `Status` now does.

So: **treat `Status` as a hint and the origin commit as the fact.** To know whether a handoff is applied,
look in the front-end repo for the thing it asks for; do not trust the field. The front-end PR should cite
its handoff file, which makes the link discoverable from the side that actually knows.

A cheap improvement, deliberately not built yet: derive the state instead of storing it — a check that
greps the front-end repos for each handoff's named symbol. It needs both repos reachable from one place,
which is true in the workspace and not under repo-only access, so it is recorded here as an option rather
than assumed.

## Handoffs vigentes

⚠ **Esta lista se mantiene a mano y no la vigila nada.** Enumera los ficheros del directorio (`ls
docs/frontend-handoff/`) antes de fiarte de que está completa; se creó el 2026-09-01, cuando un handoff
nuevo se quedó pegado al final del fichero dentro de una sección que hablaba de otra cosa porque no había
dónde ponerlo.

- [ADR-0065 — `outcome` se parte en dos](ADR-0065-recipient-delivery-split.md) — ⛔ **breaking**:
  `DELIVERY_FAILED` sale del enum `outcome`; `delivery` es un mapa por destino. Sin consumidores vivos hoy.
- [TASK-041 — el botón «Reenviar notificación» por fin tiene ruta](TASK-041-invitation-resend.md) — **additive**,
  para el **dashboard**: `POST …/resends` en vez de gastar una de las tres correcciones; ramificad el 409 sobre `code`.
- [TASK-042 — nadie actúa antes de que el flujo llegue a su paso](TASK-042-no-recipient-acts-before-their-step.md) —
  **additive**, para el **signer** y para integradores: nueve rutas de la ceremonia pueden responder ya 409
  `STEP_NOT_ACTIVE` (incluido el commit, que en el signer desplegado cae en el error genérico y se reporta a Sentry), los
  bytes siguen en 404, la emisión responde `RECIPIENT_STEP_NOT_ACTIVE`. Ningún código nuevo en el catálogo. ⛑ **2026-09-16**:
  decía *«que hoy cae»*; el `develop` del signer ya lo enruta (`639a788`), y este traspaso y el de TASK-043 llevan
  `Applied` en su `Status`. ⛑ **Y pusheado, también el 2026-09-16**: esa frase decía *«(`639a788`, sin push)»* y
  *«llevan `Applied`, sin push»*; el `develop` del signer está en `origin` hasta `7ce2958`. ⚠ **Mergeado en
  `develop` (`f490218`) y pusheado el 2026-09-16, y sin desplegar**: *«pueden responder ya»* describe el contrato,
  no lo que os sirven hoy (regla 4).
- [TASK-043 — un commit rechazado dice por qué](TASK-043-a-refused-commit-names-its-condition.md) — **aditivo en el
  esquema y aun así rompe comportamiento para el signer**: el 409 de `POST /api/v1/signing/commit` deja de colapsar
  cuatro condiciones en un `CONFLICT` pelado y nombra cada una (`SESSION_ALREADY_COMPLETED`, `SESSION_CLOSED`,
  `SIGNING_CHALLENGE_MISBOUND` — nuevos — y `ENVELOPE_NO_LONGER_LIVE`); `ALREADY_SIGNED` se retira. ⛔ **El signer y el
  backend salen en el mismo despliegue**, porque el signer quitó su rama de compatibilidad con `CONFLICT` antes de
  desplegar (`01ffece`) y cada lado se rompe contra la versión vieja del otro. Los dos están pusheados el 2026-09-16
  — el backend mergeado en `develop` en `acb20d0`, el signer en su `develop` hasta `7ce2958` — y ninguno
  desplegado. ⛑ **Cambiado el 2026-09-16, confirmado por el mantenedor**: decía *«El signer sale primero, y la
  rama de compatibilidad con `CONFLICT` se quita cuando esté **desplegado**, no cuando esté mergeado»*.

- [TASK-046 — signer: un destinatario puede rechazar](TASK-046-signer-decline.md) — **aditivo**: `POST /api/v1/signing/decline`
  con la credencial de sesión, el estado terminal `DECLINED`, cuatro códigos nuevos (`SESSION_ALREADY_DECLINED`,
  `DECLINE_NOT_OFFERED_TO_ROLE`, `DECLINE_NOT_OFFERED_IN_QUORUM_STEP`, `SEAL_PENDING`), y un sobre `VOIDED` que vuelve a
  servir su documento sellado a quien firmó o rechazó. Mergeado en `develop` en `26ed0d7`, sin desplegar.
  ⛑ **2026-09-29**: `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` está retirado desde TASK-050 (`8f42995d`); ver
  [TASK-050 signer](TASK-050-signer-step-policy-and-what-a-recipient-reads.md).
- [TASK-046 — dashboard e integradores: la causa de una anulación, y el sello de anulación](TASK-046-integrator-void-cause-and-annulment-seal.md) —
  **rompe un enum** (`EnvelopeStatus.DECLINED`, que nunca se emitió) y **cambia el comportamiento de `void`**: ahora
  sella, y se rechaza en `READY_TO_SEAL` con `ENVELOPE_REACHED_AGREEMENT`. Campos nuevos: `void_cause`,
  `voided_by_recipient_id` y, por destinatario, `declined_at`, `decline_reason`, `decline_access_method`. Misma rama.
- [TASK-044 — signer: los valores de campo llegan en el commit, y las reservas tienen un solo canal](TASK-044-signer-field-values-and-reservations.md) —
  **aditivo en el esquema y cambia comportamiento**: `filled_fields` en el commit (ausente ≠ vacío), 422
  `FIELD_VALUES_INVALID` con `field_errors`, el tipo `RESERVATIONS` y `reservations` en tres estados. Junta en un solo
  documento la parte de TASK-044 y la petición del registro de auditoría al signer. ⛔ **Backend, signer e integrador
  salen en el mismo despliegue.** Construido en la rama `feat/field-values-at-commit`, sin mergear ni desplegar.
- [TASK-044 — dashboard-sf: valores de campo, reservas y registro de auditoría](TASK-044-dashboard-sf-field-values-and-reservations.md) —
  para el **integrador de Factor5**: el campo "Reservas" pasa de `TEXT` a `RESERVATIONS` en el despliegue conjunto, más
  las peticiones del registro de auditoría (consentimiento del cargador, mapa de páginas, IP/UA, correcciones, claim).
  La parte de TASK-044, construida en la rama `feat/field-values-at-commit`, sin mergear ni desplegar.
  ⛑ **2026-09-21**: esta entrada y la anterior decían *«Nada construido a 2026-09-21»*, que era cierto al escribirlas
  ese mismo día; lo del registro de auditoría sigue sin construir.
- [TASK-044 — dashboard: el sobre devuelve los valores de campo, y enviarlo rechaza campos que nadie puede responder](TASK-044-dashboard-field-values-and-send-refusals.md) —
  **aditivo en el esquema y cambia comportamiento**, para el **dashboard**: `fields[].value` y `filled_at` nuevos,
  `signed_at` solo en firmas, el tipo `RESERVATIONS`, y tres rechazos nuevos de `POST …/send` (422
  `UNPROCESSABLE_ENTITY`, sin código propio). Sin consumidores vivos hoy, y fuera del despliegue conjunto.
- [TASK-048 — signer: one lifecycle, `RELEASED`, and a widened gate rule](TASK-048-signer-how-an-envelope-ends.md) —
  **breaks the contract**: `GET /signing/session/auth`'s `outcome` gains `RELEASED` (published even without a
  session ever opened), `REVOKED` (on both that route and `POST /signing/session`) is now reachable by more than
  a sender's void, a new 409 `LEG_CLOSED` can appear on session open, `SEAL_PENDING` now covers both outcomes,
  and a decliner no longer reads the sealed document after `COMPLETED` (narrows the TASK-046 behavior).
  `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` stays live. Branch `feat/task-048-how-an-envelope-ends`, commits after
  `8cd3424a` on the same branch, not merged, not deployed. ⛑ **2026-09-29**: *«stays live»* was true when written;
  TASK-050 retired it (`8f42995d`), and a revoked session whose leg the envelope closed now reads `RELEASED` or
  `DECLINED` on `/auth`, not `REVOKED` — see the TASK-050 signer handoff.
- [TASK-048 — dashboard: `outcome` apart from `status`, `RELEASED`, and a stricter void](TASK-048-dashboard-how-an-envelope-ends.md) —
  **breaks the contract**: `EnvelopeStatus.VOIDED` is retired (read `outcome`/`end_cause` instead), `voided_at` /
  `voided_by` / `voided_by_recipient_id` / `void_reason` are renamed, recipients gain `RELEASED` with
  `release_reason`/`released_by`, and writes can answer new `ENVELOPE_BUSY` (503) / `RECIPIENT_ACCESS_NOT_RECOVERABLE`
  (409). `expires_at` and `seal_pending_since` are delivered. Same branch and commit as above, not merged, not
  deployed.
- [TASK-048 — integrator: how an envelope ends, on `/v1`](TASK-048-integrator-how-an-envelope-ends.md) —
  **breaks the contract**, for any `/api/v1/**` consumer: same status/outcome/end_cause/field-rename change as the
  dashboard entry above, plus confirmation that **no outbound webhook sender exists in this backend at all**
  (`envelope.agreed`, `envelope.recipient_released` and the widened `envelope.completed` are names nothing sends
  yet). Same branch and commit, not merged, not deployed.

- [TASK-049 — integrador: un sobre caduca en la fecha que eligió el emisor, y se puede prorrogar](TASK-049-integrator-an-envelope-expires.md) —
  **aditivo, y rompe un enum**: `expires_in_days` al crear, `expires_at` nulo en borrador y resuelto al enviar, ruta
  nueva `POST …/expiry-extensions`, tres `ProblemCode` nuevos, y `EnvelopeStatus` pierde `EXPIRED` (una caducidad es
  `COMPLETED` con `end_cause: EXPIRED`). ⚠ Al desplegar, el barrido caduca en un minuto los sobres abiertos de más de 30
  días. Decisiones del mantenedor para `dashboard-sf`: sin `expires_in_days`, sin «Prorrogar». Misma rama, no mergeado, no desplegado.
- [TASK-049 — signer: el `status` del sobre pierde `EXPIRED`](TASK-049-signer-an-envelope-expires.md) — corrige el spec;
  el signer informa de que no necesita cambio de código, solo regenerar su snapshot OpenAPI desde `develop`. Misma rama.
- [TASK-040 — integrador: el motivo de anulación llega, literal, a los destinatarios invitados](TASK-040-integrator-ending-notice.md) —
  **cambia el significado de `reason` en `void`** sin cambiar su forma: los destinatarios invitados reciben un correo
  (sin enlace) con el motivo citado; en blanco cuenta como sin motivo. Misma rama, no mergeado, no desplegado.
- [TASK-050 — integrador: política de paso, plazos de paso y cerrar ya](TASK-050-integrator-step-policy-and-close-now.md) —
  **aditivo, y cambia el significado de `ended_by`**: `completion`/`min_signatures`/`veto`/`deadline_hours` al crear el
  paso, `deadline_at` en su lectura, cuatro 422 nuevos en `send`, ruta nueva `POST …/close` (`ENVELOPE_AGREEMENT_NOT_SECURED`),
  `STEP_DEADLINE_PASSED` en `/void` y `/close` entre el plazo de un paso y el barrido, y el barrido por minuto que
  libera con `released_by: STEP_DEADLINE`. Decisión para `dashboard-sf`: solo pasos `ALL`, sin «Cerrar ya». Rama
  `feat/task-048-how-an-envelope-ends` en `f48b14e2`, no en `develop`, no desplegado.
- [TASK-050 — signer: política de paso, plazos, y qué lee cada destinatario cuando el sobre termina](TASK-050-signer-step-policy-and-what-a-recipient-reads.md) —
  **retira un código y cambia significados**: `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` sale, `COMMIT_NOT_OFFERED_TO_ROLE`
  entra, `envelope_outcome` en `/auth` y en `GET /signing/session`, `REVOKED` deja de significar «sin acuerdo»,
  `LEG_CLOSED` en más rutas, `ENVELOPE_NO_LONGER_LIVE` ya no dice «cancelado», vista `/copy`. Misma rama y commit, no
  desplegado; el signer informa de haberlo aplicado en su rama local, sin verificar desde aquí.
- [ADR-0072 — el registro de auditoría de un sobre terminado se descarga por API](ADR-0072-audit-trail-download.md) —
  **aditivo**, para **integradores con clave de máquina** (`dashboard-sf`): `GET /api/v1/envelopes/{id}/audit-trail` sirve el
  PDF sellado, con 404 hasta que se emite y 409 `AUDIT_TRAIL_UNAVAILABLE` si su PDF no se puede leer. El anexo JSON lleva
  datos personales minimizados, y eso corrige el apartado 10 del traspaso de TASK-044 a dashboard-sf. Rama
  `feat/evidence-audit`, mergeada en `develop` el 2026-09-29, sin desplegar.
- [TASK-056 — dashboard e integradores: qué fue de la invitación de cada destinatario](TASK-056-dashboard-integrator-invitation-state.md) —
  **aditivo**: cinco claves nuevas por destinatario (`invitation_state` y sus tres instantes más `invitation_unsent_kind`),
  dos `release_reason` nuevos, y `NOT_REACHED` pasa a significar «sin hecho registrado de que se les alcanzara». `SENT` no es
  «recibida»; los tres enums son abiertos. Rama `feat/delivery-facts`, sin mergear ni desplegar.
- [TASK-037 — dashboard e integradores: la espera de un hueco reclamable, y la invitación del reclamado](TASK-037-dashboard-integrator-claimable-wait.md) —
  **aditivo**: dos claves nuevas por destinatario (`declared_claimable`, `claimed_at`); la espera es
  `declared_claimable === true && claimed_at === null`. Un reclamado sobre un paso ya activo recibe ahora su invitación,
  una sola vez. Rama `feat/claimed-recipient-invitation`, sin mergear ni desplegar.
- [TASK-057 — dashboard e integradores: el reenvío de un destinatario por SMS tiene tope](TASK-057-dashboard-resend-cap.md) —
  **aditivo**: un `code` nuevo, `RECIPIENT_RESEND_CAP_REACHED`, en el 409 de la ruta de reenvío (5 reenvíos, más los que conceda un operador, si sus canales
  incluyen `SMS`; sin `next_resend_at`; solo lo levanta un operador). Rama `feat/sms-spend-guards`, sin mergear ni desplegar.
- [TASK-060 — integrador y dashboard: un reenvío puede nombrar uno de los canales que el destinatario declaró](TASK-060-integrator-resend-channel.md) —
  **aditivo**: cuerpo opcional `{"channel":"EMAIL"|"SMS"}` en la ruta de reenvío (una sola entrega, sin caer al otro canal), dos `code` nuevos en el 409
  (`RESEND_CHANNEL_NOT_DECLARED`, `RESEND_CHANNEL_UNREACHABLE`) y el tope de SMS pasa a contar los reenvíos que pueden salir por SMS. ADR-0080 aceptado. Rama `feat/resend-channel`, sin mergear ni desplegar.
- [TASK-062 — signer y dashboard: cada puerta tiene su propio cupo de envíos de código](TASK-062-signer-dashboard-per-gate-code-budget.md) —
  **sin cambio de contrato**: el 429 es el mismo; el cupo por sesión pasa a ser por puerta (entrar / firmar), 5 por hora por email y por SMS, y suben
  tres cifras de SMS (ADR-0081, aceptado). Rama `feat/otp-budget-per-gate`, sin mergear ni desplegar.
- [TASK-063 — dashboard: la puerta de acceso se declara siempre al añadir un destinatario](TASK-063-dashboard-access-gate-always-declared.md) —
  **cambio incompatible**: `POST /api/v1/envelopes/{id}/recipients` exige `auth.access_method` o `auth.access_methods` no vacío (422 en `auth.access_methods`); la puerta abierta se escribe `DIRECT_LINK`; exentos `MACHINE_KEY` y los roles sin construir, no los slots reclamables; la lectura sigue devolviendo `[]`. El dashboard deja de recortar los métodos a los contactos que tiene. ADR-0082. Rama `feat/explicit-access-gate`, sin mergear ni desplegar.
- [TASK-064 — dashboard y firmante: las puertas de un destinatario se pueden cambiar hasta que abre su enlace](TASK-064-dashboard-gates-editable-before-entry.md) —
  **aditivo**: `PUT /api/v1/envelopes/{id}/recipients/{recipientId}/auth` sustituye las dos puertas mientras el destinatario no haya abierto su enlace (409 `RECIPIENT_ALREADY_ENTERED` después), con cinco `code` nuevos; el firmante trata el 409 `AUTH_REQUIREMENT_CHANGED` y el 503 nuevos de abrir la sesión (repetir), y los gemelos de máquina responden lo mismo. ADR-0083. Rama `feat/gates-editable-before-entry`, sin mergear ni desplegar.
- [TASK-066 — dashboard: el intervalo entre reenvíos cuenta por canal](TASK-066-dashboard-resend-interval-per-channel.md) —
  **sin cambio de contrato**: `EMAIL` y luego `SMS` seguidos ya no dan 409 `RECIPIENT_RESENT_TOO_RECENTLY`; un reenvío sin canal cuenta para todos los canales que alcanzan al destinatario, y `next_resend_at` es el más tardío. Rama `feat/resend-interval-per-channel`, sin mergear ni desplegar.
- [TASK-067 — dashboard y firmante: el PDF firmado lleva los valores de campo y las reservas](TASK-067-signed-pdf-carries-the-recorded-values.md) —
  **sin cambio de contrato**: los valores registrados se dibujan como campos de solo lectura antes de cada firma, y las reservas se registran en la admisión. Rama `feat/field-values-drawn-into-the-pdf`, sin mergear ni desplegar.

⚠ **Y la lista sigue incompleta**: estas veintisiete entradas son veintisiete de los **cincuenta y tres** handoffs del directorio, contados con `ls` el 2026-10-21 al añadir el de TASK-067 (antes decía *«estas veintiséis entradas son veintiséis de los **cincuenta y dos**»*, al añadir el de TASK-066; antes decía *«estas veinticinco entradas son veinticinco de los **cincuenta y un**»*, contados con `ls` el 2026-10-20 al añadir el de TASK-064; antes decía *«estas veinticuatro entradas son veinticuatro de los **cincuenta**»*, contados ese día al añadir el de TASK-063; antes decía *«estas veintitrés entradas son veintitrés de los **cuarenta y nueve**»*, contados ese día al unir `develop`, que trajo el de TASK-061; antes decía *«de los **cuarenta y ocho**»*, contados ese día al añadir el de TASK-062; antes decía *«estas veintidós entradas son veintidós de los **cuarenta y siete**»*, contados con `ls` el 2026-10-19 al añadir el de TASK-060; antes decía *«estas veintiuna entradas son veintiuna de los **cuarenta y cinco**»*, contados con `ls` el 2026-10-15 al añadir el de TASK-057; antes decía *«estas veinte entradas son veinte de los **cuarenta y cuatro**»*, contados con `ls` el 2026-10-14 al añadir el de TASK-037; antes decía *«estas diecinueve entradas son diecinueve de los **cuarenta y uno**»*, contados con `ls` el 2026-10-09 al añadir el de TASK-056; antes decía *«estas dieciocho entradas son dieciocho de los **treinta y cuatro**»*, contados con `grep` el 2026-09-29 al unir `develop`, que trajo el de ADR-0072; antes decía *«estas diecisiete entradas son diecisiete de los **treinta y tres**»*, contado ese día al añadir las dos de TASK-050) — la cifra anterior a esa, *trece*, ya iba corta en dos: la lista tenía quince (antes decía *«estas trece entradas son trece de los **treinta y uno**»*, contado el 2026-09-29 al añadir las tres de TASK-049 y TASK-040, y antes decía *«estas diez entradas son diez de los **veintiocho**»*, contado el 2026-09-28 al añadir las tres de TASK-048, y antes *«estas siete entradas son siete de los **veintitrés**»*, contado el 2026-09-21 al añadir el del dashboard de TASK-044, y antes *«estas seis entradas son seis de los **veintidós**»*, contado ese mismo día al añadir los dos primeros de TASK-044, y antes *«estas cuatro entradas son cuatro de los **veinte**»*), así que la
advertencia de arriba no es retórica — `ls` primero. Indexado como [`BL-254`](../BACKLOG.md), con las dos reparaciones
posibles (generarla, o borrarla y quedarse con el `ls`). ⛑ **Contado de nuevo el 2026-09-16, al añadir TASK-043**: decía
*"estas tres entradas son tres de los diecinueve ficheros"*, que era cierto el 2026-09-01. Una cifra a mano dentro de un
aviso sobre listas a mano es precisamente lo que esa fila de backlog propone dejar de mantener.
