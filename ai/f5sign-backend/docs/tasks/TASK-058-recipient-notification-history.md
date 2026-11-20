# TASK-058 — The sender can read every message the platform sent to a recipient

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/notification-history`** (code tip `726877d7`), 2026-10-15, merged to `develop` 2026-10-19 — full suite green under the `wt-backend` lane (7329 tests, 82845 assertions at `aeb47170`; lint, arch and PHPStan OK; `a8778655` and `726877d7` add only tests after that run), task-validate PASS. Infection, filtered to the diff's `src/` files: covered MSI 96 %, MSI 92 % on `a8778655` (bar 85/70); the nine escaped on changed lines are five killed by `726877d7` and four justified in §8, confirmed by a re-run on `726877d7` (covered MSI 96 %, MSI 95 %, only those four escaped). ADR-0078 is `Accepted` (owner, 2026-10-19). Left out: carrier receipts ([BL-390](../BACKLOG.md)) and the follow-ups in §7, each with a row. |
| **Type** | **Forward build** in Notification (its first HTTP route and its first read side), with one additive migration on `notification.notification_delivery`, one relocated value object and a frontend handoff. |
| **Why** | The trace in Envelope keeps one state per contact and is written only for purposes that carry a means to act, so a sender cannot see that an ending notice bounced, that a sealed copy never left, or which of two channels an invitation took. [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.7 separates **showing everything** (this history) from **deciding automatically** (the trace, deliberately prudent). The data exists in Notification's tables but no route reads it, and the rows carry no per-delivery time. |
| **Decision record** | [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.7 — this task realizes it; **Accepted** by the owner on 2026-10-19 (Proposed when this record was written). It also exercises ADR-0078 §3.2's "Notification gains its first HTTP route". |
| **Builds on** | [TASK-055](TASK-055-delivery-reliability.md) (the transient failure kind and the `NOT_NEEDED` status the history lists; without it the history can show only the failures that exist today), [TASK-031](TASK-031-channel-selection-beyond-email.md) (which makes a recipient receive on more than one channel, and so makes a history worth having), [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) (category-(c): no layer may depend on Notification — this route is inbound HTTP, and adds no such dependency), [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) (`MaskedContact`, which the history must use). |

---

## 1. Why this task exists

Four messages can leave the platform for one recipient and the sender can read none of them: the invitation and its
resends (partly, through `invitation_sent_at` / `invitation_failed_at`, which TASK-056 landed), the ending notice, the
sealed copy, and the one-time codes. Support's first question — "did the carrier get anything, and where was it
sent?" — has no answer short of a database query. This task gives it one, read-only, from Notification's own tables.

## 2. What already exists (reuse, do not rebuild)

Checked against the tree on 2026-10-09.

- **Notification has no HTTP surface.** `ls src/F5Sign/Notification/` shows `Application`, `Contract`, `Domain`,
  `Infrastructure` and no `UI`; `config/routes/api/` holds `envelope.php`, `evidence_audit.php` and `signing.php`
  and no notification file; `config/services.yaml` registers controllers only for `Envelope\UI\Http\`,
  `Session\UI\Http\` and `EvidenceAudit\UI\Http\`.
- **The deptrac layer for it already exists.** `deptrac.yaml` declares `NotificationUI` (collector
  `src/F5Sign/Notification/UI/.*`) and its ruleset allows `Kernel`, `Foundation`, `NotificationContract`,
  `NotificationApplication` and `Vendor`. So adding a `UI` directory needs **no deptrac edit**; the "full five-layer
  set declared up front" comment was written for this day. ⚠ That ruleset does **not** include `NotificationDomain`, and
  every enum the response names (`DeliveryStatus`, `DeliveryChannel`, `NotificationPurpose`, `DeliveryFailureKind`) is a
  Domain type, so the handler's view carries their values as strings (§3.2). What *is* cross-cutting: a new controller registration in
  `services.yaml`, a new route file, and the Nelmio path pattern (`^/api/v1`) already covers it.
- **The precedent for a route outside the owning context's path list** is `EvidenceAudit`:
  `config/routes/api/evidence_audit.php` serves `GET /api/v1/envelopes/{id}/audit-trail` with
  `Authn::ROUTE_KEY => Authn::MACHINE_KEY->value`, `RouteCollisionTest` refuses a second route with the same method and
  path, and `RouteAuthnDeclarationTest` refuses a route without a declared credential.
- **The data.** `notification.notification`: `id`, `tenant_id`, `subject_type`/`subject_ref` (an `envelope` and its id),
  `addressee_type`/`addressee_ref` (a `recipient` and its id), `purpose`, `policy`, `variables`, `requested_at`;
  indexes `notification_subject_idx` and `notification_addressee_idx` (both lead with `tenant_id`).
  `notification.notification_delivery`: `id`, `notification_id`, `tenant_id`, `channel`, `destination`, `template_id`,
  `status`, `failure_reason`, `provider_reference`, `failure_kind` (`PERMANENT` / `TRANSIENT`, set exactly when the
  status is `FAILED`: `notification_delivery_failure_kind_chk`), `send_before` (a deadline, not a lifecycle instant) and
  `position` (the delivery's place in its occasion's order, `UNIQUE (notification_id, position)`) — **and no instant at
  which a delivery was requested or settled** (checked across `Version20260721000001`, `Version20260820000001`,
  `Version20261009144204` and `Version20261013075218`, the four migrations that touch it). FORCE row-level security
  with a tenant isolation policy covers both tables. No purge of notification data exists.
- ⚠ **`failure_reason` is personal data and must not be served.** `Delivery::failureReason()` and
  `TransmissionOutcome` document it as PII-bearing ("a provider's refusal routinely quotes the destination back"), and
  `DeliveryFailed` deliberately omits it. ADR-0078 §2.7 lists "failure kind and reason" among the fields; the tree
  says the raw reason cannot be one of them (decision D-1).
- **Ownership through Envelope's Contract.** `EnvelopeQueryInterface::getEnvelopeContext(EnvelopeId, SystemActorId,
  DateTimeImmutable)` throws `EnvelopeNotFoundException` for an unknown envelope **and** for one invisible to the
  caller's tenant, and returns the recipients (`EnvelopeContextView::$recipients`); eight Notification use cases already
  call it. It stamps its own issuer, so a caller supplies a `SystemActorId` and the `Clock`'s instant; its tenant
  invisibility comes from row-level security on the request's tenant scope, not from a predicate of its own. `NotificationApplication` may depend on `EnvelopeContract` per `deptrac.yaml`.
- **The precedent for a read handler.** `EvidenceAudit/Application/Query/GetAuditTrail` + `GetAuditTrailHandler`
  (kernel `Query` / `QueryHandler`), read on the connection's tenant scope, returning `null` for "not yours".
- **Masking.** `MaskedContact::of()` (`EvidenceAudit/Domain/Trail`) masks an email (first character and final suffix) or
  an E.164 phone (the `+` and the last two digits) and returns `None` for anything else; its private constructor keeps an
  unmasked contact out of the trail. It sits in **EvidenceAudit's Domain**, which Notification may not import.
- `ConstantSqlStatementRule` (PHPStan) requires constant SQL strings in persistence code.

## 3. What gets built

**3.1 The route.** `GET /api/v1/envelopes/{id}/recipients/{recipientId}/notifications`, declared in a new
`config/routes/api/notification.php` (collection `notification.`, `/v1` prefix) with `Authn::MACHINE_KEY`, served by
`Notification\UI\Http\ListRecipientNotificationsController`, registered in `config/services.yaml` with the
`controller.service_arguments` tag like its siblings. The route file's header lists its path and says why the path sits
under the envelope but is not Envelope's (the `evidence_audit.php` wording). `#[OA\Get]` with `machineApiKey` and
`DeclaredSubjectHeader` parameters; responses 200, 400, 401, 404 (one answer for an unknown envelope, another tenant's,
a recipient not on it, and a recipient with no messages is **200 with an empty list**, not 404).

**3.2 The ownership check, then the read.** `ListRecipientNotificationsHandler` (Application) first calls
`EnvelopeQueryInterface::getEnvelopeContext` and requires the recipient to be on the returned recipients; either failure
is the same 404. Only then does it read Notification's tables through a new `Domain/ReadRepository` port with a DBAL
adapter in `Infrastructure/Persistence`: one query over `notification_subject_idx`'s prefix
(`tenant_id`, `subject_type = 'envelope'`, `subject_ref`) filtered by `addressee_ref`, ordered by `requested_at`, then
`id`, joined to its deliveries. The tenant is named explicitly as `addresseesFor` does, not left to RLS alone. The read is
bounded (a page size and a cursor on `(requested_at, id)`; options and default in §5, D-2). The handler returns a view
in `Application/Query` beside its query, carrying the enum values as strings, as EvidenceAudit's `AuditTrailContent`
does: `NotificationUI` may import Application but not Domain (§2), so no `deptrac.yaml` edit is needed.

**3.3 The per-delivery timestamps.** A migration adds to `notification.notification_delivery` two nullable columns:
`requested_at TIMESTAMPTZ` (when this delivery was requested — which under TASK-031's `IN_ORDER` is later than its
occasion's, and is what makes the sequence of attempts legible) and `settled_at TIMESTAMPTZ` (when it reached a terminal
status). `Delivery` carries them and the transitions stamp them from the `Clock` in the same gesture as the status, as
`markSent` does with the provider reference. Before this task no `Delivery` transition took an instant (`pending()`, `markSent()`,
`markFailed()`, `markFailedTransiently()`, `markNotNeeded()`), nor did `Notification::recordNotNeeded()` and the
aggregate's ending of held `IN_ORDER` deliveries; `Notification::recordSent()`'s instant was optional and its callers could
omit it; and requesting a held successor recorded its fact without touching the `Delivery`. Those signatures gained a
required instant, and their callers pass it. **What `NULL` means, for every state a row can be in** (authoring rule 6),
because a backfilled row is indistinguishable from an authored one:

| Row | `requested_at` | `settled_at` |
|---|---|---|
| Written before the migration, `PENDING` | backfilled from `notification.requested_at` (true: under `SINGLE`, `ANY` and `ALL` every delivery is requested with its occasion) | `NULL`, correct |
| Written before the migration, `SENT` / `FAILED` | backfilled likewise | **`NULL` for ever**: the instant it settled was never recorded and is unfillable. The history shows no settled time rather than the occasion's |
| Written after, `PENDING` | set at creation or, for an ordered target not yet needed, `NULL` until it is requested | `NULL`, correct |
| Written after, terminal | set | set |
| `NOT_NEEDED` (TASK-055), found unnecessary after it was requested (the send-time check, or a cancellation of a pending invitation) | set | set (the instant it was found unnecessary) |
| `NOT_NEEDED`, an ordered target that was never requested (TASK-031) | `NULL` | set (the instant it was found unnecessary) |

The backfill states its property rather than a list of statuses: `requested_at` is copied from the occasion **only where
the delivery was requested with it** — its occasion's policy is not `IN_ORDER`, or it holds its occasion's lowest
`position`. Every other pre-migration row keeps `requested_at` `NULL`, and every pre-migration row keeps `settled_at`
`NULL`. The rows that predicate leaves out — a non-head `IN_ORDER` delivery, and any `NOT_NEEDED` written before the
migration — can exist only on a development database: the only release, v0.0.1 (`master`), predates both `IN_ORDER`
(TASK-031) and `NOT_NEEDED` (TASK-055), and a database built from scratch holds none. (On such a database
`Version20261013075218` backfilled `position` by channel name, so even "lowest position" is not guaranteed to be the
true head there.) On those rows a `NULL` means *not
recorded*, not *never requested*; the migration's docblock says so beside this table, which it reproduces.

No reader may treat `NULL settled_at` on a terminal row as "pending"; the status says that. The migration is generated,
never numbered by hand; `down()` drops the columns.

**3.4 The response.** Per occasion: `notification_id`, `purpose`, `requested_at`, and its `deliveries`. Per delivery:
`channel`, `destination` (masked, or `null` for a channel with none), `status` (the closed `DeliveryStatus` values),
`failure_kind` (closed: permanent refusal / transient, from TASK-055; `null` unless failed), `requested_at`,
`settled_at`, and `provider_reference` **not** included (it names a transmission for reconciliation, not for a sender).
The recipient-facing codes are included as occasions too (`AUTH_OTP_*`), because "the code never arrived" is the
question this answers; their `variables` (which hold the code and the link) are never selected — the query names its
columns and `variables` is not among them.

**3.5 `MaskedContact` moves out of EvidenceAudit.** Notification cannot import EvidenceAudit's Domain, and a second
copy of the masking rules would let the history and the trail disagree about what a masked number looks like. The class
moves to `Foundation` (a value object with the same private constructor and `of()`), `EvidenceAudit` uses it from there,
and its existing tests move with it (the trail's published form must not change: `TrailAssemblerTest`, `TrailJsonTest`, `TrailJsonCompletenessTest` and the
rest of `tests/F5Sign/EvidenceAudit/` keep every assertion and change only their imports; `TrailJsonCompletenessTest`'s
census walks `EvidenceAudit/Domain/Trail`, which the class leaves, and its `instanceof` branch follows the import). This is cross-cutting (`Foundation` gains a type and `EvidenceAudit` loses one; no
`deptrac.yaml` edit is needed), so the implementer drafts the note for the owner (repo rule 7)
before moving it.

**3.6 Docs.** A frontend handoff in `docs/frontend-handoff/` for the dashboard is a deliverable of this task (not
written with this record): the route, the response shape, masking, the empty-list-is-200 rule, the meaning of `SENT`
(*handed to the provider, not received*) and that a message accepted and lost downstream reads as sent
([BL-390](../BACKLOG.md)). Plus the `docs/ddd/notification-domain-model.md` read-side section, `docs/LIVE_SCHEMA.md`
for the two columns, and ADR-0078's Status / Enforced by / Realized in when the bars are green.

## 4. Scope

**In scope:** §3.1–§3.6.

**Out of scope:** any write; showing the reason text (D-1); pushing events to the sender (webhooks, ADR-0064, unbuilt);
filtering by purpose or channel (a follow-up if the dashboard needs it); a tenant-wide history; the rendering of
invitations in the audit trail ([TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md)); retention or
purge of notification rows (none exists, and none is added).

Concepts re-cut: `MaskedContact` (moves from EvidenceAudit's Domain to Foundation)

## 5. Key decisions (made here)

**D-1 — the failure reason.** Options: (A) serve the raw `failure_reason` — rejected, it quotes destinations and
provider text and the repo has kept it off every outbound surface on purpose; (B) serve nothing but the status; (C)
**serve a closed `failure_kind`** derived from TASK-055's transient/permanent distinction, and no free text. **Decided by the owner on 2026-10-09:
C.** It answers "is this number dead or was it an outage" without leaking. A provider *code* (for example Twilio
`21614`, a landline) <!-- OFFREPO: Twilio's error catalogue, outside this repository; code 21614 is its "not a mobile number" refusal, quoted only as an example of a provider code that would explain a refusal. --> would answer "why" better, but it needs a new nullable column the channel adapters fill; recorded as
a follow-up rather than widening this task.

**D-2 — paging.** Options: (A) unbounded; (B) a fixed cap with no cursor; (C) **cursor on `(requested_at, id)` with a
page size (default 50, maximum 200).** A recipient with resends and codes can accumulate dozens of rows, and codes are the
growth (one per request). **Decided: C** (2026-10-09, under the owner's standing grant for technical decisions with a clear precedent), which is what the index order supports.

**D-3 — where masking lives.** Options: (A) duplicate it in Notification; (B) **move `MaskedContact` to `Foundation`**;
(C) have the history return the raw destination because the caller is the tenant's own integrator. **Decided by the owner on
2026-10-09: B**, recorded in ADR-0078 §2.7 (repo rule 7). Session's `MaskedDestination` stays and stays different; the two are not merged.
(C) would put a phone number into an integrator's logs; (A) lets two masks drift.

**D-4 — one route or two.** One route returning every purpose (ADR-0078 §2.7 says every occasion of every purpose).
Splitting codes from notices would make the answer to "did they get anything" two calls.

## 6. Acceptance bars

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | The history of a recipient lists their occasion of each purpose (members AC-1a…l) | derived — ADR-0078 §2.7, rule 5 (census of `NotificationPurpose`) | Integration | drop that purpose from the read (inferred) |
| AC-12 | The history of recipient A lists none of recipient B's occasions | derived — ADR-0078 §2.7 | Integration | drop the `addressee_ref` filter |
| AC-2 | Each case of an envelope or recipient the caller may not see answers the one 404, with the same body (members AC-2a…c) | derived — ADR-0078 §2.7 | Acceptance | see *Notes on AC-2* |
| AC-3 | A recipient with no messages answers 200 with an empty list, not 404 | derived — ADR-0078 §2.7 | Acceptance (inferred) | answer 404 on an empty result (inferred) |
| AC-4 | Each kind of destination is served masked or `null`, and no raw value appears in the body (members AC-4a…c) | derived — ADR-0078 §2.7 | Acceptance (inferred) | serve `destination` raw |
| AC-5 | The response key set is closed: `failure_reason`, `variables`, `provider_reference`, the link and the code are absent | derived — rule 5 (closed key set) | Acceptance (inferred) | select `failure_reason` or `variables` in the query (inferred) |
| AC-6 | Each terminal outcome reads with its own status, kind and timestamps (members AC-6a…d) | derived — ADR-0078 §2.7 | Integration (inferred) | map every failure to one kind (inferred) |
| AC-7 | Each page boundary is stable across calls (members AC-7a…b) | derived — ADR-0078 §2.7 | Integration (inferred) | break the cursor predicate on `(requested_at, id)` (inferred) |
| AC-13 | Each malformed paging request answers 400 (members AC-13a…b) | derived — rule 5 (the other side of the page bounds) | Acceptance | clamp the page size silently instead of refusing |
| AC-8 | Each way a delivery gets its timestamps is served truthfully (members AC-8a…d) | derived — rule 6 | Integration (inferred) | see *Notes on AC-8* |
| AC-9 | Each part of the route's declaration holds (members AC-9a…c) | derived — ADR-0048 | Acceptance and the existing route tests (inferred) | see *Notes on AC-9* |
| AC-10 | Each guard of the `MaskedContact` move holds (members AC-10a…c) | derived — ADR-0078 §2.7 | existing EvidenceAudit tests, a Foundation unit test, the deptrac gate | change a mask rule in the moved class (inferred) |
| AC-11 | The OpenAPI test shows the route, its `machineApiKey`, its responses and the closed response schema | derived — ADR-0078 §2.7 | OpenAPI test (inferred) | remove the `#[OA\Get]` security or a response (inferred) |

**Notes on AC-1 and AC-12**
- Fixture: one envelope, two recipients, each with one occasion of every purpose, on mixed channels. Real SQL, because the two-recipient disagreement is in the data.
- Members, one per `NotificationPurpose` case on 2026-10-09: AC-1a `RECIPIENT_INVITATION`, AC-1b `RECIPIENT_INVITATION_RESENT`, AC-1c `ENVELOPE_COMPLETED`, AC-1d `ENVELOPE_ENDED_SENDER_CANCELLED`, AC-1e `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON`, AC-1f `ENVELOPE_ENDED_DECLINED`, AC-1g `ENVELOPE_ENDED_TIME_RAN_OUT`, AC-1h `ENVELOPE_ENDED_OUT_OF_REACH`, AC-1i `SEALED_COPY_READY`, AC-1j `AUTH_OTP_SIGNING`, AC-1k `AUTH_OTP_ACCESS`, AC-1l `AUTH_OTP_DECLINE`. The test iterates `NotificationPurpose::cases()`, so a purpose added later is listed without editing it.
- AC-12 — the history of recipient A lists none of recipient B's occasions. Sabotage: drop the `addressee_ref` filter; B's rows appear and the test names them.

**Notes on AC-2**
- AC-2a — an unknown envelope. Sabotage: let the envelope-not-found exception escape as another status.
- AC-2b — tenant T2's envelope id presented by T1's key. Sabotage: drop the explicit tenant on the read.
- AC-2c — T1's envelope with a recipient not on it, including a recipient of another envelope of the same tenant. Sabotage: skip the Envelope check and rely on RLS alone; the same-tenant case reddens, because RLS does not separate two envelopes of one tenant.

**Notes on AC-4**
- AC-4a — an email, AC-4b — a phone: the exact masked strings, and the body contains neither raw value. AC-4c — a destination for which `MaskedContact::of()` returns `None` is served as `null`. Sabotage of AC-4c: fall back to the raw string.

**Notes on AC-5**
- Fixture: a `failure_reason` of `550 5.1.1 <ada@example.com>: rejected` and `variables` holding a token. Assert the closed key set, not the absence of a few strings, so a new field must be added on purpose.

**Notes on AC-6**
- AC-6a — a permanently refused delivery reads as the permanent kind. AC-6b — an exhausted-retry delivery reads as the transient kind, different from AC-6a's. AC-6c — a `NOT_NEEDED` ordered target that was never requested has a null `requested_at` and a set `settled_at`. AC-6d — a `NOT_NEEDED` pending invitation cancelled after it was requested keeps its `requested_at`. Sabotage of AC-6c/AC-6d: stamp, or clear, `requested_at` on every not-needed delivery.

**Notes on AC-7 and AC-13**
- AC-7a — with more occasions than a page, no row is repeated or lost across the cursor. AC-7b — two occasions sharing a `requested_at` are ordered by id; sabotage: order by time alone.
- AC-13a — a page size over 200 answers 400. AC-13b — a cursor that does not decode answers 400.

**Notes on AC-8**
- AC-8a — a delivery sent through the real transmit use case has `requested_at` and `settled_at` from the test `Clock`. Sabotage: stamp `settled_at` on a non-terminal transition.
- AC-8b — an ordered successor requested later has a later `requested_at` than its predecessor. Sabotage: stamp `requested_at` from the occasion.
- AC-8c — a row in the migration's backfill shape (a `SENT` row, `settled_at` NULL) is served with `settled_at: null` and `requested_at` equal to its occasion's. Sabotage: revert the backfill.
- AC-8d — the backfill copies the occasion's `requested_at` only onto a delivery requested with it: on one `IN_ORDER` occasion with two pre-migration rows, the head gets it and the successor keeps `NULL`, while a `SINGLE` occasion's row gets it. Sabotage: drop the backfill's policy-and-position predicate; the successor reddens.

**Notes on AC-9**
- AC-9a — a `POST` answers 405. AC-9b — the route declares `MACHINE_KEY`, and `RouteAuthnDeclarationTest` and `RouteCollisionTest` stay green. AC-9c — a request with no key answers 401. Sabotage: drop the declared credential.

**Notes on AC-10**
- AC-10a — the trail's chained JSON for a fixture envelope is byte-identical before and after the move. AC-10b — the Foundation unit test pins the masks. AC-10c — deptrac passes with no edit to `deptrac.yaml`.

- Each bar names the fixture whose variables disagree and the sabotage that must redden it.
- AC-11 also requires that `/contract-check-backend TASK-058` is run and that the handoff exists.
- **Gates:** full suite, Infection covered-MSI, PHPStan (including `ConstantSqlStatementRule` on the new adapter), deptrac and lint green in the worktree lane.

## 7. Open follow-ups (track, don't solve here)

- [BL-423](../BACKLOG.md): a nullable provider **failure code** column filled by the channel adapters, so the history can say why without a free
  text field. Forced by the first support case that cannot tell a dead number from a landline with the failure kind alone.
- [BL-424](../BACKLOG.md): filtering by purpose or channel, and a tenant-wide view, if the dashboard asks.
- [BL-426](../BACKLOG.md): pushing these facts to the sender ([ADR-0064](../adr/ADR-0064-outbound-integrator-webhooks.md), unbuilt). Forced when ADR-0064's webhooks are built.
- Receipts and bounces ([BL-390](../BACKLOG.md)): until they exist, `SENT` is the best the history can say.
- [BL-425](../BACKLOG.md): whether notification rows should ever be purged (none is today); the history assumes they are kept. Forced by the first retention rule written for Notification's tables, or a privacy review that asks for one.
- [BL-422](../BACKLOG.md): a composite index for the history read, if volume grows (doctrine-guard, 2026-10-15). The page rides `notification_subject_idx` today.
- Closed by this task: [BL-128](../BACKLOG.md) (2026-10-15).

## 8. Deviations & honest notes

Infection (filtered to the diff's 24 `src/` files, worktree lane, bar 85/70): on `a8778655` covered MSI 96 %, MSI 92 %
(1160 mutants, 1072 killed, 36 escaped, 52 not covered), nine escaped on changed lines. Five, in `HistoryPaging`'s two
regexes and its base64 alphabet check, are killed by the test rows of `726877d7`. Four are equivalent, and the re-run on
`726877d7` (filtered to the three files) left exactly these four escaped, covered MSI 96 %, MSI 95 %:
- `HistoryPaging.php` `UnwrapRtrim` on the encode's padding strip: the plaintext is always 69 bytes (a 32-character
  instant, `|`, a 36-character id), a multiple of 3, so base64 never emits `=` and the `rtrim` removes nothing.
- `HistoryPaging.php` `ConcatOperandRemoval` on `'!' . INSTANT_FORMAT`: the format sets every field, so none defaults to
  now; a shorter instant fails to parse with or without the `!`.
- `ListRecipientNotificationsHandler.php` `Break_`: the loop only sets a flag to true, so continuing it cannot change
  the result.
- `DbalNotificationHistory.php` `ArrayItemRemoval` on the `limit` parameter's `INTEGER` type: pdo_pgsql sends it as
  untyped text and Postgres infers an integer for `LIMIT`; the mutant's own run, with the type removed, passed every
  history test.

The contract check's one warning (no test pinned `INVALID_DECLARED_SUBJECT` on this route) is closed by `a8778655`.

### Scope
- None outside §3.1–3.6. The diff also touches ADR-0072/0078 and TASK-059 documentation, owned by the docs phases, not by a slice.

### Decisions made during implementation
- Slice 01: the migration's docblock states §3.3's table literally (orchestrator, `1f869e4e`, docblock only); the lane's test database first recorded an empty generated stub, which the implementer repaired by deleting the version and migrating again.
- Slice 02: the failure folds take an `$observedAt` from the `Clock`, separate from the facts' instant; `recordSent` now always records `DeliverySent` (tests had only ever omitted it); `markSent`'s stale "deferred" sentence was fixed in the closing slice.
- Slice 05: the query carried a Domain cursor the UI could not name; the query takes the raw cursor string and the handler decodes it first (`HistoryPaging::rawCursor`). Slice 07 was amended.
- Slice 07: the query took Envelope Contract id types the UI may not import; resolved with `ListRecipientNotifications::fromPath` (path ids as strings).
- Slice 08: a malformed declared subject answers `INVALID_DECLARED_SUBJECT`, not `BAD_REQUEST`; the handoff and the route's 400 description say so (`c4fb05b4`), and `a8778655` pins it with an acceptance case. The handoff no longer says every invitation asks to sign.
- Closing slice: citations added for AC-9b, AC-10a and AC-10b, and a test asserting the route's `MACHINE_KEY` declaration.
- Notification's line in the repo's authoring guide (the new `UI` and its route) is edited outside this repository after the merge.

### Decisions that needed an ADR
- None new. [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.7 is realized here; moving it to `Accepted` is proposed to the owner, not applied.

### Declared and unproven properties
- The route file's `_authn` sabotage was refused by the permission classifier; a test-side flip was accepted by the reviewer together with slice 07's sabotage.
- AC-7b's `ORDER BY id` half is discriminating only through scan order (no fixture can do better); the cursor-predicate half is deterministic.
- AC-10c is gate-only (the `deptrac.yaml` diff is empty).
- Not reached: `composer audit` (not run; the diff touches no composer files); no performance run (`perf:seed` does not exist).

### Debt left behind, and where it lives now
- Composite index for the history read: BL-422. Failure code column: BL-423. Filters and tenant-wide view: BL-424. Retention of notification rows: BL-425. Push to the sender: BL-426 (ADR-0064).
- Carrier receipts, so `SENT` can become "delivered": BL-390 (open). TASK-025's workflow half (correcting an unreachable recipient's contact): stays in TASK-025 and BL-118.
- `notification_delivery.destination` stays unencrypted at rest (pre-existing; ADR-0033 Proposed).

### Delegated work
- Slices (tier, model, rounds, status): 01 critical opus 1 DONE; 02 critical opus 1 DONE (delegated to the replicator: 19 test files, accepted); 03 critical opus 1 DONE_WITH_CONCERNS; 04 critical opus 1 DONE; 05 critical opus 2 DONE; 06 critical opus 1 DONE; 07 critical opus 2 DONE; 08 standard sonnet 1 DONE (400-code fix applied by the orchestrator); 09 critical opus 1 DONE_WITH_CONCERNS; 10 standard, one fix round, DONE.

### Cost of the run
- Slice agents logged: 1,319,041 tokens in 9 logged slices; opus 1,224,402 (8 slices), sonnet 94,639 (slice 08). Slice 10 logged no tokens.
- Rounds: 11 across slices 01–09 (two slices needed a second round: 05 and 07).
- Escalations: none; critical slices ran on opus from the plan.
- Full suite runs: two (`236799d7`, `aeb47170`), both green.
- Gates: task-validate pass; doctrine-guard, contract-check and security-audit warn (no blockers); perf-smoke skipped.
