# TASK-044 — A recipient's field values are recorded at the commit

<!-- OFFREPO: the consuming half lives in the sibling repository `f5sign-signer`, read at `develop` `ac2e955`
on 2026-09-21. The files cited are unchanged from `e476079`, where the first audit in §7 read them, through
`824b7ad`, where the second re-checked them.
- `app/composables/useSignFlow.ts`: `buildCommitRequest()` sends `{ consent: true, reservations: null }` and
  nothing else. `mapError` handles a 422 only for `AUTH_REQUIRED`; anything else falls through to a generic
  failure with a retry that resends the same body.
- `app/composables/api/types.ts`: the live `CommitRequest` has no field values. The
  `filled_fields: Array<{ field_id, value }>` shape belongs to `CompleteRequest`, the `/complete` contract.
  `types.ts` calls that contract docs-future, and `SigningApi.real.ts` makes `complete()` a dead alias of
  `commit`. It declares its value inline as `string | boolean | number`, the same union as `PatchValue` in
  `app/stores/useFieldsDraftStore.ts`.
- `app/composables/useFieldValidation.ts`, whose rules §3 #4 mirrors:
  - `null`, `undefined`, `''` and `false` are empty;
  - a required CHECKBOX must be `true`;
  - DATE is ISO `YYYY-MM-DD`;
  - no trimming;
  - a `pattern` is **skipped, and the value passes**, when it exceeds 200 characters, when the value exceeds
    4096 characters, when the `NESTED_QUANTIFIER` heuristic matches the pattern, or when `new RegExp` throws.
    Both ceilings are JS `.length`, so they count UTF-16 code units;
  - the pattern runs with no flags and unanchored;
  - one message per field, in the order required, max length, pattern.
- `app/stores/useFieldsDraftStore.ts`: values are keyed by field id. A CHECKBOX is `undefined` until ticked,
  and SIGNATURE / INITIALS are excluded by type.
- `app/pages/s/[token]/view.vue`: an EDITOR can edit fields, but its `submit-fill` action is a placeholder
  toast and never commits.

Every fact this record depends on is restated where it is used; nothing here needs that repository open. -->
<!-- OFFREPO: §5.1 relies on the sibling repository `f5sign-infra`: the per-worktree lane
(`make -C ../f5sign-infra wt-backend src=$(pwd)`, its default gates `lint arch phpstan test` and the opt-in
`WT_GATES="infection"`), and its committed `docker-compose.override.yml`, which binds the main checkout
`../f5sign-backend` into the shared stack. The command is spelled out where it is used; nothing here needs
that repository open. -->
<!-- OFFREPO: §2, §4 D14 and §8 rely on the sibling repository `factor5_dashboard_sf` (the Factor5 integrator),
read at its local branch `feat/waybill-pdf-pagination` `dac9a63f9` and at `origin/master` `20c6a1289` on
2026-09-21:
- `src/Service/TransportRequest/Signature/WaybillSignatureFormFields.php`: `forDestinatario()` authors one
  `TEXT` field labelled "Reservas", not `required`, with `max_length` 120 and two occurrences — the
  destinatario's own carta de porte, and its page of the conjunta. `forCargador()` and `forTransportista()`
  author none.
- `WaybillEnvelopeService.php`: all three roles are `SIGNER` on the platform. The cargador signs through the
  delegated route.
- `F5Sign/F5SignApiGateway.php`: `addField()` expects the value to be written at the commit. `getStatus()`
  reads no field member.

§8 also relies on two requests drafted by another backend session for the envelope Audit Trail
(`REQUESTS-SIGNER.md` and `REQUESTS-DASHBOARD-SF.md`), which are not committed anywhere, and on the workspace
note `notes/HANDOFF-signing-evidence-capture-2026-09-21.md` (the signer session's evidence proposal); their
relevant content is restated in §8. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/field-values-at-commit`, 2026-09-21** — one commit per tramo: `061e293` (ADR-0068 seam), `6f106d8` (domain rules), `0bae290` (port, narrow write, both commits), `50c44ac` (read side), `ce284c4` (`send()` guards), `4f7231e` (`RESERVATIONS`), `19d4e3b` (spec, records, handoffs, sweep); `origin/develop` merged at `b51b1bd`. Each code tramo went green under the `wt-backend` lane (`lint arch phpstan test`) on an isolated checkout of its commit — tramos 4+5 and 5+6 jointly at the later commit; the full run with Infection is the landing gate. [ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md) and [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md) are exercised, and the maintainer promoted both to `Accepted` on 2026-09-22. **Not deployed**: backend, signer and integrator deploy together (§4 D13). Until this line was written the Status read *"Not started — design only"*; the design history it summarized is §7 and §8. What departed from the design is §9. |
| **Type** | **Forward build**, with one enabling change: widening the problem-extension seam in Kernel and Foundation ([ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md)), and one new field type, `RESERVATIONS`, which places a recipient's reservations ([ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md)). It realizes the write half that [ADR-0040](../adr/ADR-0040-field-entity-unified-placement.md) Decision 6 deferred: `envelope.field.value` and `signed_at` have existed since `Version20260803000001`, and nothing writes them. |
| **Why** | Editable fields reach the signer and round-trip nothing ([BL-57](../BACKLOG.md)). A `TEXT`, `DATE`, `CHECKBOX`, `DROPDOWN` or `RADIO` is painted, validated in the browser and then dropped. `POST /api/v1/signing/commit` carries only `consent` and `reservations`, and the server enforces no `required` flag. So an envelope authored with required fields completes with them empty. |
| **Builds on** | Reused unchanged: [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md) (the crossing goes through `Contract/`) · [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md) (invariant violation → 422) · [ADR-0041](../adr/ADR-0041-field-definition-and-occurrences.md) §5–§6 (one value per field; visibility resolved per occurrence) · [ADR-0066](../adr/ADR-0066-no-recipient-acts-before-their-step.md) §2.6 and [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md) (the refusal order on both commits, which §4 D5 preserves). |
| **Scope** | **Recording only**, plus the `RESERVATIONS` placement type (§3 #11). Out of scope:<br>• drawing the values, or the reservations, onto the PDF ([BL-269](../BACKLOG.md));<br>• the three-state reservations marker ("declared none"), which belongs to the Audit Trail work and is not committed (§8);<br>• `SIGNATURE` and `INITIALS`, whose value is an appearance and gets its own slice;<br>• the draft auto-save ([BL-40](../BACKLOG.md));<br>• enciphering the column ([BL-49](../BACKLOG.md), decided *not now*, §4 D9);<br>• a tamper-evident digest ([BL-268](../BACKLOG.md), decided *not now*, §4 D10);<br>• EDITOR filling ([BL-271](../BACKLOG.md), §4 D7).<br>**The `f5sign-signer` and dashboard changes are not in this repository**: this task writes their handoffs (§3 #9). |
| **Decision record** | Three records (corrected 2026-09-21; it read *"Two records"* over this list of three):<br>• **[ADR-0040](../adr/ADR-0040-field-entity-unified-placement.md) Decision 6, realized here with no new ADR.** Its *"inside the commit transaction"* can only be met by a synchronous call, and its *"completion fact"* is realized as a port call, never as an event (§4 D11). No dependency direction opens: `deptrac.yaml` already grants `SessionApplication → EnvelopeContract`, and `SessionUI` is kept off Envelope types (§3 #1).<br>• **[ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md), `Accepted` since 2026-09-22**, for the one Kernel + Foundation contract change: a problem extension may carry a list of flat records (§4 D12).<br>• **[ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md), `Accepted` since 2026-09-22**, for the `FieldType` member shared with the signer: a `RESERVATIONS` field places the recipient's reservations and holds no value of its own (§4 D14).<br>▶ **What would force another ADR**: any edit to `deptrac.yaml`, or moving the validation into Session. |
| **Delivery bar** | One acceptance case (§5.3):<br>• a commit carrying `filled_fields` answers 200, and `GET /api/v1/envelopes/{id}` then shows each value and its `filled_at`;<br>• a commit **without** `filled_fields` writes nothing, not even a blank;<br>• a commit with invalid values answers **422 `FIELD_VALUES_INVALID`**, whose `field_errors` names **every** bad field — after which **the same signing code commits successfully**;<br>• a replay answers `SESSION_ALREADY_COMPLETED`. |
| **Sibling** | ⚑ The two unified handoffs, one for the signer and one for the Factor5 integrator (§3 #9). They also carry the Audit Trail requests (§8). **Backend, signer and integrator deploy together** (maintainer, 2026-09-21; §4 D13). |

---

## 1. Why this task exists

The signer projection landed on 2026-08-03 and made data fields visible to recipients. Nothing downstream
followed:
- `current_value` and `fields_draft` are hardcoded `null`;
- the commit body has no place for a value;
- neither commit use case looks at the envelope's fields.

So the product shows a form, lets a person fill it in, and keeps none of it. That is the worst of the
available states, because it looks finished.

The column has been waiting on purpose:
- [ADR-0040](../adr/ADR-0040-field-entity-unified-placement.md) Decision 6 fixed the write discipline: once,
  at commit, never a scratchpad.
- [ADR-0041](../adr/ADR-0041-field-definition-and-occurrences.md) §5 fixed the shape: one value per field,
  however many rectangles.

What is left:
- the write itself;
- the validation that has to guard it;
- the guards that stop an envelope from demanding a value nobody can give.

## 2. What already exists (reuse, do not rebuild)

- **The columns.** `envelope.field.value JSONB` and `signed_at TIMESTAMPTZ`, NULL on every row. **No
  migration is needed** while the column stays plaintext (§4 D9).
- **What reads and writes them today:**
  - **Nothing writes either column.** `DbalEnvelopeRepository::upsertField()` leaves both out on purpose, so
    that a re-save of the aggregate cannot blank a recorded value. That property must survive this task.
  - **`value` is read nowhere.** The aggregate hydration hardcodes `value: null`, and
    `DoctrineEnvelopeReadRepository` does not select the column.
  - **`signed_at` is already read, and already published.** Both hydrations select it, `FieldView::$signedAt`
    carries it, and `EnvelopeJsonPresenter` emits it per field on `GET /api/v1/envelopes/{id}`. The
    `config/packages/nelmio_api_doc.yaml` `Field` schema declares it `date-time, nullable`. It is `null` on
    every row today, and `EnvelopeJsonPresenterTest` pins the key on a fixture built with a null `signedAt`.
  - `Field::value()` is already typed `string|bool|int|float|null`.
- **"What this recipient was shown" exists only on the read side.**
  [`EnvelopeContextView::fieldsFor()`](../../src/F5Sign/Envelope/Contract/View/EnvelopeContextView.php)
  computes it:
  - from the recipient's accessible documents, narrowing each field's occurrences with
    `FieldOccurrences::restrictedTo()`;
  - dropping a field that resolves to no rectangle, through two limbs: a null occurrence list (text-tag), or a
    list narrowed to nothing ([LOAD-BEARING](../LOAD-BEARING.md) §1.8).

  The `Envelope` aggregate has no equivalent. It has the ingredients (`Recipient::visibleAssignments()`, the
  fields, `restrictedTo()`), which §3 #4 turns into one domain predicate.
- **The port.** [`EnvelopeCommandInterface`](../../src/F5Sign/Envelope/Contract/Command/EnvelopeCommandInterface.php)
  is synchronous and runs inside the caller's transaction, so a refusal rolls the caller back. Its class
  docblock names its callers: SignatureExecution and Notification. Its adapter has two shapes, for two
  different reasons:
  - **`markRecipientDeliverySent()` / `…Failed()`**: `findLockedForUpdate()` on the root, then `save()`.
    Under the root lock, `save()` cannot deadlock (see the adapter's docblock).
  - **`appendDocumentArtifact()`**: locks one **document** row (`findEnvelopeOfDocument()`, root left
    unlocked), then does a narrow `saveAppendedArtifact()`. It must stay narrow *because* it does not hold the
    root: two signers on different documents would otherwise deadlock inside `save()` (the
    `EnvelopeRepository::saveAppendedArtifact()` docblock). `EnvelopeRepository::find()`'s docblock says every
    write path takes `findLockedForUpdate()`; this is the documented exception, and
    [LOAD-BEARING](../LOAD-BEARING.md) §1.5 argues it is safe because its write is equally narrow.
- **The two commits.**
  - `CommitSignatureUseCase` locks the session, reads the auth context, checks that the credential is still
    this party's, checks the step, calls `SigningSession::commitSignature()`, then saves.
  - `CommitDelegatedSignatureUseCase` runs the same spine. It adds the assertion checks, **ahead of** its step
    guard, which answers last on that route (ADR-0066 §2.6, amended 2026-09-16).
  - The aggregate's named refusals — `SESSION_ALREADY_COMPLETED`, `ENVELOPE_NO_LONGER_LIVE` and the rest —
    are what the signer routes on (ADR-0067). The consent refusal carries no named code (`UNPROCESSABLE_ENTITY`).
  - Both controllers live in `Session\UI\Http`, and `SessionUI` **may not import `EnvelopeContract`**. The
    delegated controller already hands raw parts to its use case rather than an assembled `AssertedEvidence`,
    for the same kind of reason: `AssertedEvidence` lives in `SessionDomain`, which `SessionUI` may not
    import either.
  - The delegated route answers **204 with no body**.
- **The problem shape.**
  - `InvariantViolationException` maps to 422, and `ProblemCoded` names the code.
  - `ProblemExtensions` adds members, but is typed `array<string, scalar|null>`. `ApiExceptionListener` takes
    extensions under the same type, and drops one named `errors`. Hence ADR-0068.
- **Where the published spec lives.** These surfaces are documented in `config/packages/nelmio_api_doc.yaml`
  components, not only in `#[OA\*]` attributes:
  - `Field`;
  - `FieldOptions`, whose pattern text says *"the backend stores it and does not execute it"*;
  - `SigningField.current_value`, typed `string`;
  - `SigningSession.fields_draft`;
  - the `ProblemCode` catalog, in which `OpenApiSpecTest` requires every coded refusal.
- **The pattern is not executed server-side.** The
  [`FieldValidation`](../../src/F5Sign/Envelope/Contract/Type/FieldValidation.php) docblock says the
  commit-time validator is where this backend becomes an executor. That is [BL-50](../BACKLOG.md) limb 2.
- **Personal-data classification.** A type implementing `Kernel\Capability\Pii` is redacted by
  `SensitiveDataRedactor`, under any key, from what reaches the error tracker; `SentryBeforeSend` is its only
  caller. That is how `AssertedEvidence` is classified without being enciphered. ⚠ The redactor does not
  touch Monolog lines, the column, HTTP bodies or event payloads.
- **The lock probe.** [`ProbesRowLocks`](../../tests/F5Sign/Support/ProbesRowLocks.php) can tell a locked read
  from an unlocked one; the DAMA suite cannot.
- **Exhaustive role predicates.** `Role::signs()` and `Role::isBlocking()` are `match`es with no default. §3 #8
  adds a third in the same shape.
- **`Option` and `Result` are Kernel categories** since `8df1cb1`, with two PHPStan rules since `6460c09`: a
  method returning a `Result` must declare `#[NoDiscard]`, and no statement may discard one. Both are on
  `origin/develop`, after this record's base `e845e03`, and **no caller uses them yet**. §4 D16 decides whether
  this task is the first.
- **Reservations already have their own channel** ([TASK-016](TASK-016-sign-with-reservations.md)).
  - Both commits carry `reservations`, a string of at most 2000 characters on both DTOs.
  - It is stored in `signing_session.reservations` and `recipient.reservations`, and carried by the
    `SignatureCommitted` fact into the permanent log.
  - It is published as `recipients[].reservations` and `has_reservations` on `GET /api/v1/envelopes/{id}`.
  - Drawing it into the PDF was deferred (TASK-016 §4), for lack of a place to draw it.
- **The integrator's reservations box is a `TEXT` field** (see the OFFREPO note).
  - The Factor5 integrator authors one per destinatario, labelled "Reservas", with occurrences on the
    destinatario's carta de porte and on its page of the conjunta.
  - Recorded as designed before §8, it would have become a second, weaker reservations channel. ADR-0069 and
    §3 #11 replace it with a placement type.

## 3. What gets built

1. **Wire.**
   - **Signer route**, `POST /api/v1/signing/commit`, gains `filled_fields: [{ field_id, value }]`.
     - The DTO checks shape only, **before any lock**:
       - a list, bounded by a named ceiling;
       - each `field_id` a UUID;
       - each `value` a string, a boolean or `null` — a number is refused, deliberately narrower than the
         signer's `PatchValue`, since no field type stores one;
       - each string at most a DoS ceiling set **above** the domain's default text ceiling (#4), so that an
         over-long answer is refused as `TOO_LONG` on its own field, not as a generic `VALIDATION_ERROR`;
       - no `field_id` twice.
     - **Absent is not `[]`** (§4 D15).
       - *Absent* means this client collected no field values: nothing is written, not even a blank. A
         `required` field is still enforced, so it is refused as `REQUIRED`.
       - *Present*, even as `[]`, means the form was shown: blanks and an unticked CHECKBOX are recorded as
         such.
     - The controller puts the entries on `CommitSignature` as raw
       `?list<array{field_id: string, value: string|bool|null}>`, with `null` for absent, and **the use case**
       assembles the Contract type (§2: `SessionUI` may not import it).
     - Success answers as it does today, with no echo. A `fields_recorded` count was designed to let a new
       signer detect an old backend; the joint deploy (§4 D13) removed that need. It would also have been an
       echo that survives deleting the dispatch, which is the shape [BL-10](../BACKLOG.md) records.
   - **Delegated route**, `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature`, gains the same
     member, with the same absent/present meaning (§4 D8), and **stays 204**.
   - **Published spec.**
     - Both routes: the new member and its absent/present meaning, `field_errors`, and `FIELD_VALUES_INVALID`
       in the `nelmio_api_doc.yaml` `ProblemCode` catalog.
     - The delegated route: a note that integrators whose envelopes carry required data fields must now send
       values (§4 D8).
2. **A Contract type for the crossing.** `FilledFieldValues` in `Envelope\Contract\Type`: a list of
   `(FieldId, string|bool|null)` that refuses a duplicate id. **It implements `Pii`**, which classifies it
   without enciphering it (the classification half of BL-49, answered; §4 D9).
3. **One port method.**
   - `EnvelopeCommandInterface::recordFieldValues(EnvelopeId, RecipientId, ?FilledFieldValues, ?string $reservations, DateTimeImmutable $now)`
     validates and writes.
     - `null` values mean "not collected" (§3 #1).
     - `$reservations` is only checked, against the recipient's `RESERVATIONS` field (§3 #11), and never
       written here: TASK-016's path records it.
   - There is no read-only twin. A validating method on `EnvelopeQueryInterface` would
     break [ADR-0008](../adr/ADR-0008-read-side-realization.md), which realizes a cross-BC read as a `Query` DTO
     plus a handler returning a result shape. It would also have to reach the write model or re-implement the
     rules. The delegated route calls this same method earlier instead (§3 #6).
   - It refuses with `FieldValuesRejectedException`, a new Contract exception:
     - `InvariantViolationException` → 422;
     - `ProblemCoded` → `FIELD_VALUES_INVALID`;
     - `ProblemExtensions` → `field_errors: [{ field_id, code }]`, a list member ([ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md)).
   - **Every** bad field is reported, with **one code per field**, chosen by the precedence `UNKNOWN_FIELD` >
     `READONLY` > `WRONG_TYPE` > `REQUIRED` > `TOO_LONG` > `CONTROL_CHARACTERS` > `PATTERN_MISMATCH` /
     `INVALID_DATE` / `NOT_A_CHOICE`. That matches the signer's one message per field.
   - **A record never carries the submitted value** (ADR-0068 §2.3).
   - **The per-field codes are a Contract enum**, not string literals in the exception. `OpenApiSpecTest` reads
     every quoted UPPER_SNAKE literal in a file that implements `ProblemCoded` as a top-level code, and would
     demand each one in the `ProblemCode` catalog. The spec publishes them as a `FieldError.code` enum (shipped as
     `FieldValueError.code`, §9), pinned by
     a census test, since nothing else checks `field_errors`.
   - Under the root lock, an envelope that is no longer live is refused with a Contract refusal. That refusal
     does **not** implement `ProblemCoded`: the use case translates it to the existing
     `ENVELOPE_NO_LONGER_LIVE`, and it never reaches the wire itself. So a void landing between the
     auth-context read and the lock never writes into a VOIDED envelope.
   - `EnvelopeCommandInterface`'s class docblock, which enumerates its callers, gains Session.
4. **The rules, in the domain.**
   - **The key set is one domain predicate** on the aggregate (for example `Envelope::fieldsShownTo(RecipientId)`).
     It is built from the recipient's visible documents and `FieldOccurrences::restrictedTo()`, and keeps both
     occurrence-less limbs of LOAD-BEARING §1.8. It is intersected with the five data types (so `RESERVATIONS` is outside it), and it is **empty
     unless `Role::fillsFields()`**, read from `Recipient::role()`. `recordFieldValues()` and the send guard
     (#8) both use it, and a parity test holds it equal to `fieldsFor()` (§5.2). That is buildable:
     `fieldsFor()` has no signing-mode branch, and `documentsAccessibleTo()` is the visible assignments
     intersected with the documents, all of which the aggregate holds.
   - **Membership is decided first, before any type lookup.** A refusal must not tell another recipient's field
     apart from a random id, so that nothing can be learned about an envelope's other fields.
   - The rules mirror the signer's (§4 D3):

   | Type | Stored as | Accepted | Codes |
   |---|---|---|---|
   | `TEXT` | JSON string | See "Rules for `TEXT`" below | `TOO_LONG`, `CONTROL_CHARACTERS`, `PATTERN_MISMATCH` |
   | `DATE` | JSON string `YYYY-MM-DD` | A real calendar date. `date_format` is presentation only, and `max_length` / `pattern` are not applied, as in the signer ([BL-270](../BACKLOG.md)). The server accepts years 0000–0099, which the signer rejects; the harmless direction | `INVALID_DATE` |
   | `CHECKBOX` | JSON boolean | A boolean. **Missing from a present `filled_fields`, it is recorded as `false`**: the recipient saw an unticked box. With `filled_fields` absent, nothing is recorded (§4 D15) | `WRONG_TYPE` |
   | `DROPDOWN` / `RADIO` | JSON string | A member of `choices`, by `value` | `NOT_A_CHOICE` |

   - **Rules for `TEXT`:**
     - Length is counted in characters (`mb_strlen`). The signer counts UTF-16 units, so the server is never
       stricter.
     - The limit is `validation.max_length`, or a named default when none is authored.
       - The default is a constant of its own, set equal to `FieldValidation::MAX_LENGTH_CEILING` (32767) so
         that no authored rule is ever looser than it.
       - It is not that constant reused: that docblock says it is the column type's ceiling, *not* a statement
         about how long an answer may be.
       - The handoff publishes it, so the signer can bound its input.
     - `\n`, `\r` and `\t` are allowed; the signer offers a textarea. Every other C0 character and DEL is
       refused. That includes NUL, which `json_encode` writes as `\u0000` and `jsonb` rejects, surfacing as a
       500.
     - Values are not trimmed: a whitespace-only value satisfies `required`, as in the signer.
     - **`validation.pattern` is skipped, and the value passes, exactly where the signer skips it:**
       - the pattern exceeds 200 UTF-16 code units;
       - the value exceeds 4096 UTF-16 code units. Both are counted as JS `.length` counts; a `mb_strlen`
         count would enforce where the signer skipped.
       - the signer's `NESTED_QUANTIFIER` heuristic matches the pattern. It is ported with the same constants
         and expression, and run with `/u`, because JS `\s` is Unicode.
     - It is also skipped when the pattern fails to compile or the engine reports any error, including the
       backtrack limit and the JIT stack.
     - **Running the pattern:**
       - compiled as `"\x01(*UTF)" . $pattern . "\x01D"`, unanchored like JS `test()`;
       - `(*UTF)` is UTF mode **without** UCP, so `\d`, `\w` and `\b` stay ASCII as in JS. PHP's `/u` would
         turn UCP on and make the server stricter.
       - `D` makes `$` match only at the very end, as JS `$` does without `m`. Without it, `12345678Z\n` would
         pass here against `^\d{8}[A-Z]$` and fail in the signer.
       - Measured on 2026-09-21 (PHP 8.4, PCRE2 10.42, Node 24), `/u` against this form: it agrees with JS on
         `^\D+$`, `\bfoo`, `^\d{8}[A-Z]$` and `^\w+$`, where `/u` disagreed.
       - It still disagrees, in the harmful direction, on `^.{3,}$` against `"😀a"` (JS counts UTF-16 units)
         and on `^\s$` against a non-breaking space. Both are in [BL-272](../BACKLOG.md).
       - Delimited by `chr(1)`, which `FieldValidation::guardText()` refuses on every load (`fromParts()` in
         both repositories). That guard landed in the commit that created the column, so no stored pattern
         predates it. A `/` delimiter would silently break `^\d{2}/\d{2}$`.
       - inside a scoped error handler, because a compile failure raises `E_WARNING`, which is an
         `ErrorException` under debug and a test failure under `failOnWarning`;
       - under a low `pcre.backtrack_limit`, set in `try`/`finally`. It is honoured under JIT;
         `pcre.recursion_limit` is not.
     - The rest of the dialect gap is recorded as [BL-272](../BACKLOG.md). Syntax only PCRE accepts is enforced
       here and skipped by the signer. Syntax only JS accepts fails to compile here, so the server silently
       skips it: the harmless direction.
   - **For every type:**
     - `''` and `null` normalize to absent, and a blank is written as **SQL `NULL`**, never JSON `null`.
     - With `filled_fields` **absent**, only `REQUIRED` is checked, and nothing is written.
     - A `required` field is satisfied by a non-absent value; a required `CHECKBOX` only by `true` → `REQUIRED`.
     - A `readonly` field is not held to `required`, and an entry for it → `READONLY`. It is always `false`
       today; the rule is written now so that prefill cannot forget it.
     - A wrong JSON type → `WRONG_TYPE`.
     - Any key outside the set → `UNKNOWN_FIELD`. That covers another recipient's field, a field not shown,
       `SIGNATURE`, `INITIALS`, `RESERVATIONS`, the four inert types, and any field of a role that does not
       fill.
   - **The domain cannot log** (deptrac). The port returns the number of skipped pattern rules (built: the aggregate
     method returns it and the port's adapter logs it; the port itself returns nothing, §9), and the adapter
     logs the envelope id and that count — **never a value, and never a field id**. Monolog lines do not pass
     through `SensitiveDataRedactor` or `EgressAllowList`, which guard only what reaches the error tracker, so
     nothing would catch either.
5. **Persistence: a narrow write under the root lock.**
   - The adapter takes `findLockedForUpdate()` on the envelope, then writes through a new
     `EnvelopeRepository::saveFieldValues(Envelope, RecipientId)`.
   - The narrowness has its **own** reason, not `saveAppendedArtifact()`'s. That one is narrow because it runs
     without the root lock. This one runs under it, and is narrow because `save()` would re-upsert every child
     row of the envelope ([BL-53](../BACKLOG.md)) to record one recipient's answers.
   - The write is one `UPDATE` per field, scoped by `id`, `envelope_id` and `recipient_id`, and guarded by
     `signed_at IS NULL`. If the affected count differs from the fields it meant to write, it throws.
   - When `filled_fields` is present, `signed_at` is set to the commit instant on **every shown data field**,
     including one left blank (§4 D4). When it is absent, nothing is written.
   - Both hydrations read `value`.
   - **The cost, accepted.** Every commit — for every role, since only Envelope decides the key set — now loads
     the aggregate and takes the root lock. So it queues behind a concurrent `RecordRecipientCompletion`
     `save()` on the same envelope. The lock is held only for one recipient's `UPDATE`s.
6. **The order inside the two commits** (§4 D5):
   - **Normal:** existing guards → `session->commitSignature()` (in memory) → `recordFieldValues()` →
     `sessions->save()`.
   - **Delegated:** assertion checks → `recordFieldValues()` → step guard → `recordAssertedEvidence()` →
     `commitSignature()` → `save()`.
     - The field write runs **only when** `$auth->envelopeIsAlive && $session->status()->admitsSigning()`, the
       same shape as the step guard's own skip on a dead envelope. A delegated session opens with its access
       gate passed, so it is `AUTH_PASSED` until it completes.
     - When the gate is false, `commitSignature()` answers the standing refusal (`SESSION_ALREADY_COMPLETED`,
       `SESSION_CLOSED`, not authenticated, `ENVELOPE_NO_LONGER_LIVE`), exactly as on the normal route.
     - A refusal after the write — the step guard, or `commitSignature()` — rolls the write back with the rest of
       the transaction, which `startIfAbsent()` in the same use case already relies on.
7. **The read side.**
   - `FieldView` gains `value`, **with no default**. `fieldsFor()` rebuilds `FieldView` with named arguments, and
     a defaulted `value` would be dropped there silently, leaving `current_value` null.
   - `GET /api/v1/envelopes/{id}` publishes three things per field, and no column appears twice on the wire:
     - `value`, new;
     - `filled_at`, new, the stored `signed_at` for a **data** field;
     - `signed_at`, now emitted only for a `SIGNATURE` field (`null` otherwise). That keeps its meaning on the
       wire as ADR-0041 §4 and the `Field` docblock give it.
   - A `RESERVATIONS` field is published with `value: null`; its text is `recipients[].reservations`
     (ADR-0069 §2.7). In the signer's projection, its `current_value` is the recipient's committed reservations.
   - `EnvelopeJsonPresenterTest` and the nelmio `Field` schema change accordingly.
   - The signer's `current_value` becomes the recorded value. The nelmio `SigningField.current_value` is retyped
     to a nullable `string | boolean`, and its *"nothing writes it yet"* description replaced.
   - The inline comment in `GetSigningSessionController` goes, and so does the `fields_draft` description's
     *"(no form fields)"*.
8. **Three send-time guards** in `Envelope::ensurePreSendInvariants()`, all using #4's predicate:
   - a data field assigned to a recipient whose role does not fill: a new exhaustive `Role::fillsFields()`,
     `true` for `SIGNER` and `APPROVER` only (§4 D7);
   - a `required` field of one of the five inert types named by the `FieldType` docblock (`INITIALS`,
     `ATTACHMENT`, `PAYMENT`, `KYC`, `EUDI_WALLET`);
   - a `required` data field that is **totally unreachable** — no recipient, or no occurrence on a document its
     recipient may read ([BL-60](../BACKLOG.md)). A partially reachable field stays legal: it is published
     narrowed.

   These fire at send only. An envelope sent before this task lands is protected by #4 at the commit: a
   non-filling role's key set is empty, and an unreachable field is not in anyone's set.
9. **Two unified handoffs**, one per consumer, under `docs/frontend-handoff/`. Each carries this task's changes
   **and** the Audit Trail requests of §8, so that no consumer receives two instructions about one box:
   [`TASK-044-signer-field-values-and-reservations.md`](../frontend-handoff/TASK-044-signer-field-values-and-reservations.md)
   and
   [`TASK-044-dashboard-sf-field-values-and-reservations.md`](../frontend-handoff/TASK-044-dashboard-sf-field-values-and-reservations.md),
   and, written at landing as planned below,
   [`TASK-044-dashboard-field-values-and-send-refusals.md`](../frontend-handoff/TASK-044-dashboard-field-values-and-send-refusals.md).
   What this task contributes to them:
   - **Signer.**
     - **Sending:** send `filled_fields` on every commit that showed a form, restricted to the five types,
       non-readonly fields, ids in the field index, and `string | boolean | null`. Omit the member only when no
       form was shown.
     - **Reservations:** render the reservations input at a `RESERVATIONS` field's occurrence when the recipient
       has one, and the generic box otherwise. Send the text in `reservations`, never in `filled_fields`.
     - **Send it only when the recipient's role is `SIGNER` or `APPROVER`.** Every entry, blank ones included,
       is checked for membership. A data field shown to a REVIEWER (or to a VIEWER, which reaches the signer as
       REVIEWER) on an envelope sent before this lands is outside their key set, so any entry would draw
       `UNKNOWN_FIELD`.
     - **Refusals:** handle `FIELD_VALUES_INVALID` before the generic branch.
       - Map codes to the existing keys: `REQUIRED` → `validation.required` / `checkboxRequired`; `TOO_LONG` →
         `maxLength`; `PATTERN_MISMATCH` → the field's `pattern_message` or `validation.pattern`;
         `INVALID_DATE` → `dateInvalid`; `NOT_A_CHOICE` → `invalidChoice`.
       - Add keys for `CONTROL_CHARACTERS` and a page-level notice, and a client-side control-character rule,
         since pasted text carries them.
       - Treat `UNKNOWN_FIELD`, `READONLY` and `WRONG_TYPE` as client defects: report and fail.
     - **Text ceiling:** apply the published default, and a `RESERVATIONS` field's `max_length` to the
       reservations input.
     - **The draft:** keep it local against the real backend. `PATCH /signing/session/fields` does not exist
       ([BL-40](../BACKLOG.md)), and the final values travel on the commit. On signer `develop` `8ce01de` the
       store already does this: `hasDraftEndpoint()` keeps the values local and the indicator idle, since
       `476fe5c`. The Audit Trail request's *"falla, pasa a `offline` y reintenta"* does not hold there.
     - **Deploy order:** one deploy with the backend and the integrator (§4 D13).
     - **Stale comments to retire:** the skip rationale in `useFieldValidation.ts`, `FieldView.current_value` in
       `types.ts`, `hasDraftEndpoint`, the header and `buildCommitRequest` of `useSignFlow.ts`, and
       `hasFieldDraftEndpoint`.
     - **Known coverage gaps:** the MVP `click-sign.vue` path commits with no fields; end-to-end tests run the
       mock's `complete` path, so the real commit-with-fields path is uncovered.
   - **The Factor5 integrator (`dashboard-sf`).**
     - **Retype the "Reservas" field:** from `TEXT` to `RESERVATIONS`, keeping its occurrences and its
       `max_length`, in the same deploy.
     - **Read-back:** field values come back on `GET /api/v1/envelopes/{id}` (`value`, `filled_at`). Reservations
       come back on `recipients[].reservations`, not on the field.
     - **`signed_at`'s narrowed meaning.**
     - **The new authoring and `send()` refusals** of #8 and #11.
   - **`f5sign-dashboard`** reads the same envelope response and needs its own handoff for #7 and for the new
     `send()` refusals, per `docs/frontend-handoff/README.md`. No Audit Trail request is addressed to it, so
     there is nothing to unify: it is written at landing, as usual.
10. **The records**, in the landing changeset:
    - ADR-0040: `Status`, `Enforced by` and `Realized in` for Decision 6, worded *"by a port call"*. Its
      `Status` line *"no column … is unwritten except `value` / `signed_at`"* changes, and so does the
      `docs/adr/README.md` index row.
    - ADR-0068 and ADR-0069: `Status` per exercise, and their index rows.
    - `FieldType`'s published enumerations (nelmio `Field.type`, `SigningField.type`) gain `RESERVATIONS`.
      `docs/ddd/envelope-domain-model.md`'s field-type list and [BL-43](../BACKLOG.md) are dated against the
      twelve members.
    - ADR-0041: dated banners at §5 (*"Nothing writes them yet"*), and at the **Risks** bullet under
      *Consequences* on BL-64 (*"the harm only becomes real when BL-57 makes values flow"*). BL-64 was closed by
      decision on 2026-09-21 — accepted — and its harm, if any, arrives with drawing (BL-269), not with
      recording.
    - ADR-0040's `Related ADRs` table (this read *"ADR-0040 §4"*, a section that ADR does not have): a dated banner on the ADR-0008 row, *"`current_value` reflects the session's draft until
      completion"*, which §3 #7 contradicts.
    - ADR-0061 §2.12: a dated line `envelope.field` | `value` under its 2026-08-27 census.
    - `docs/LOAD-BEARING.md`: a new entry. `upsertField()` excluding `value` / `signed_at`, and
      `saveFieldValues()` beside `save()`, look like duplication and are not.
    - `docs/LIVE_SCHEMA.md` `envelope.field`: `signed_at` per type (§4 D4); `value` plaintext; a CHECKBOX
      missing from a present `filled_fields` stored as `false`; a `RESERVATIONS` row never carrying either.
    - Dated banners in two domain models:
      - `docs/ddd/signing-session-domain-model.md`: *"we hand back `fields_draft` on demand"*, the query port's
        `getFieldValues(sessionId)`, the `CommitSignature` atomic flow (which gains the Envelope write), and the
        context-map row.
      - `docs/ddd/envelope-domain-model.md`: the `fields_draft` *"final values read back on demand"* row, and the
        `EnvelopeCommandInterface` row (*"Sole consumer is Signature Execution"*).
    - Code and spec surfaces that the landing makes false:
      - the `nelmio_api_doc.yaml` strings:
        - *"the backend stores it and does not execute it"*, twice, in `FieldOptions.validation` and in
          `pattern`;
        - the `current_value` and `fields_draft` texts of §3 #7;
        - `Field.recipient_id`'s *"nothing refuses a null recipient at send (BL-60)"*;
      - the `SigningFieldValidationView` docblock, which says the backend does not execute the pattern;
      - the `Field::recipientId()` docblock and LIVE_SCHEMA's `recipient_id` row: *"`send()` has no reachability
        guard"*. That becomes partly false, for required fields;
      - the `Version20260804000001` docblock, *"nothing writes `value` yet (BL-57)"*;
      - `SigningReadEndpointsHttpTest`'s assertion message, *"nothing writes envelope.field.value yet"*.
    - Backlog:
      - BL-57 and BL-60 close;
      - BL-50 **narrows to limb 1 and stays open**. Limb 2 is built here, but the signer's `isPatternSafe` misses
        `((a+))+`, which still hangs the device.
      - BL-49 stays open.
11. **The `RESERVATIONS` field type** ([ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md)).
    - `FieldType::RESERVATIONS`, a twelfth member: not a signature, not fillable, no choices.
    - `FieldType::acceptsValidation()` is **not** widened for it. A narrower predicate admits `max_length` alone
      on this type, so a `pattern` or `date_format` on it is refused.
    - `Envelope::addField()` refuses a `RESERVATIONS` field that:
      - has no recipient;
      - is assigned to a role that does not fill;
      - is `required`;
      - carries `choices`;
      - is the recipient's second.
    - `recordFieldValues()` checks the commit's `reservations` against that field's `max_length`, when there is
      one → `TOO_LONG` on the field's id. It writes neither `value` nor `signed_at` on it.
    - Both projections publish it (§3 #7). The signer's `current_value` is the recipient's reservations.
    - Drawing it is [BL-269](../BACKLOG.md)'s: each occurrence gets the recipient's reservations, including
      occurrences on documents the recipient was not shown ([BL-64](../BACKLOG.md), accepted).

## 4. Key decisions

- **D1 — Validation lives in Envelope, behind the port.** Envelope owns the field definitions and the visibility
  that decides what a recipient sees. Both commit routes pass through one rule set; Session only carries the
  values. Putting the check in Session would duplicate the visibility rule across a boundary.
- **D2 — A recipient answers exactly what they were shown, if their role fills.** The key set is §3 #4's
  predicate: shown fields, data types only, empty for a non-filling role. It is decided before any type lookup.
  `required` is enforced only inside the set, so the server never demands a box the recipient was not given.
- **D3 — The server's rules are the signer's rules, including where the signer declines to apply one.**
  Divergence only ever strands a signer, who sees a green form and gets a 422. So the server is never stricter
  than the signer on something the signer accepts without warning, and a stricter rule lands in the signer
  first.
  - The pattern-skip conditions are ported, not approximated.
  - Two gaps remain, both recorded:
    - the regex dialect gap (BL-272);
    - control characters, the one protective asymmetry. A keyboard does not produce them, and the database
      cannot store NUL.
- **D4 — On a data field the `signed_at` column means "committed", and the wire keeps the two meanings apart.**
  - When `filled_fields` is present, `signed_at` is set on every shown data field. That makes "left blank"
    (`value` NULL, `signed_at` set) distinguishable from "not collected" (both NULL, D15), and gives the
    write-once guard a column to stand on.
  - On a `SIGNATURE` field the column keeps the meaning the `Field` docblock and ADR-0041 §4 give it: the instant
    of that mark's own PAdES revision. That is why this task does not write it there.
  - The wire publishes `filled_at` for a data field and `signed_at` for a signature field, so a dashboard never
    reads "signed" on a text box.
- **D5 — Refusal order, per route.**
  - **Normal route.** `commitSignature()` runs before `recordFieldValues()`, so a replay against a completed
    session still answers `SESSION_ALREADY_COMPLETED`, the code the signer routes to its done page. Running the
    write first would re-open what TASK-043 closed.
  - **Delegated route.** ADR-0066 §2.6 (amended) makes the step refusal answer **last**, by the test *"does
    waiting reach the remedy?"*. It does not for a bad value, so `recordFieldValues()` runs before the step
    guard. Otherwise a dormant recipient with a bad value would be told to wait, retry, and then be refused,
    which is the shape [BL-263](../BACKLOG.md) closed.
  - **But never before a standing refusal.** On the delegated route `commitSignature()` comes after the write, so
    the write is gated on a live envelope and a session that admits signing (§3 #6). Otherwise a replay, a
    closed session or a voided envelope would answer `FIELD_VALUES_INVALID` here while the normal route answers
    the standing code. That would break ADR-0067 §2.5: the code travels with the condition, never with the
    route.
  - **On both routes nothing is saved until the end.** A 422 therefore rolls back the challenge consumption with
    everything else, and **a mistyped NIF spends neither the signing code nor the attempt budget**, as long as
    the retry comes before the challenge expires. The audit confirmed this: `commitSignature()` consumes the
    challenge and records its events in memory only, and the commit touches no attempt counter or rate limiter.
- **D6 — Narrow write, root lock first; lock order session → envelope.**
  - `RecordRecipientCompletionUseCase` locks the root and `save()`s. That re-upserts every field row in the
    order `loadFields()` hydrated them (`ORDER BY id`). An unlocked narrow `UPDATE` in another order could
    deadlock with it; taking the root first serializes the two.
  - The audit read every `FOR UPDATE` site and found no synchronous path that takes envelope → session:
    - Envelope calls no Session write port;
    - `OnEnvelopeVoided` → `RevokeEnvelopeSessions` runs in its own relay-driven transaction;
    - no command is dispatched inside another;
    - there is no foreign key across the two schemas, and no advisory lock.
  - SignatureExecution's signing path locks only `envelope.document`, and the field `UPDATE` changes no key
    column, so there is no cycle there either.
- **D7 — Who fills: `SIGNER` and `APPROVER`.** *Maintainer, 2026-09-21.*
  - The maintainer first chose SIGNER, APPROVER and EDITOR. **EDITOR is deferred**: the signer lets it edit
    fields but cannot submit them, so its fields would stay empty on an envelope that completes without it (it
    is not blocking). Re-admitting it only relaxes a guard, so it is additive ([BL-271](../BACKLOG.md)).
  - `REVIEWER` and `VIEWER` are the signer's read-only roles. `IN_PERSON_HOST` and `CERTIFIED_DELIVERY` have no
    ceremony.
  - Enforced at send (§3 #8) **and** at the commit (§3 #4), because envelopes sent before this lands are never
    re-checked by a send guard, and ADR-0055 §2.13 records that nothing on the commit path otherwise reads the
    role.
- **D8 — The delegated route accepts `filled_fields`.** *Maintainer, 2026-09-21.*
  - The integrator asserts the values alongside the rest of the act, and the same rules validate them.
  - ADR-0055's forcing case is the consignor's employee signing the waybill. That is a `SIGNER`, so it fills
    under D7.
  - ⚠ **This is a contract change for existing integrators.** One whose envelopes carry required data fields and
    who sends none will now receive `REQUIRED`. The published description says so (§3 #1).
- **D9 — Plaintext, classified.** *Maintainer, 2026-09-21.*
  - [BL-49](../BACKLOG.md) asked for the classification before the first write, because enciphering a populated
    column is an expand/backfill/contract migration.
  - The classification is answered: `FilledFieldValues` is `Pii`, so it is redacted from what reaches the error
    tracker. ⚠ That is narrower than it sounds. The values also cross Session as raw arrays on the command, and
    `FieldView`'s new `value` is a raw scalar. Neither is covered, and nothing redacts the column or the HTTP
    body. That is why the adapter's log line carries no value by construction (§3 #4).
  - Encipherment is declined for now, knowingly, and BL-49 declares the gap the way [BL-214](../BACKLOG.md)
    declares the delegated evidence's.
- **D10 — No digest in the event log for now.** *Maintainer, 2026-09-21.* Until the values are drawn into a
  sealed PDF, the column is their only copy and can be altered without trace. The closing design is recorded in
  §6 and [BL-268](../BACKLOG.md).
- **D11 — Values never enter the event log, and the "completion fact" is a port call.**
  - ADR-0040 Decision 6 says values cross *"as a completion fact"*. Here that is realized as the synchronous
    port call inside the commit transaction, never as an event: the log is permanent ([BL-130](../BACKLOG.md)),
    and [LOAD-BEARING](../LOAD-BEARING.md) §2 forbids plaintext personal data in it.
  - A closed-key-set assertion on the two commit facts pins that (§5.2).
- **D12 — Per-field refusals travel as a list.** *Maintainer, 2026-09-21*, over "the first bad field only, as
  scalars". It widens a Kernel and a Foundation contract, which is why it has its own record:
  [ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md), `Accepted` since 2026-09-22.
- **D13 — Backend, signer and integrator deploy together.** *Maintainer, 2026-09-21*, revising "the signer
  first", decided earlier the same day.
  - The deployed signer sends no values and does not know `FIELD_VALUES_INVALID`. The integrator's "Reservas"
    field has to change type (D14) before a recipient can fill it into the wrong channel. A joint deploy removes
    both windows, and it is the shape ADR-0067 §2.6 settled for TASK-043.
  - It also removed the need for a `fields_recorded` echo, which existed only to let a new signer detect an old
    backend.
  - ⚠ **One residue.** A signer tab opened before the deploy commits without `filled_fields`. Under D15 that is
    "not collected", so it is refused only on an envelope with a **required** data field. The integrator's
    "Reservas" is not required.
- **D14 — Reservations: one channel for the text, a field for the place.** *Maintainer, 2026-09-21*
  ([ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md)).
  - The text travels only in the commit's `reservations` (TASK-016), which is in the permanent log and is what the
    Audit Trail reads.
  - A `RESERVATIONS` field only says where it is drawn, and on which documents.
  - **Without the field, the reservations are still collected, logged and published; they are just not drawn.**
  - The rejected alternatives are ADR-0069 §7 (this read *"the two"*; §7 has three):
    - recording a `TEXT` "Reservas" field would have built a second channel that the Audit Trail does not read;
    - dropping the field would have lost the conjunta's box;
    - a placement on the recipient or the assignment would have duplicated the occurrence model.
- **D15 — An absent `filled_fields` is "not collected", never "left blank".** *Maintainer, 2026-09-21*, adopting
  the Audit Trail design's rule for reservations: never infer a declaration from an absence, because only the
  commit knows what was asked.
  - Absent: nothing is written, not even `signed_at`, and `REQUIRED` still applies.
  - Present (even `[]`): the form was shown, so blanks and an unticked CHECKBOX are recorded.

- **D16 — The port refuses by throwing, not by returning a `Result`.** *Maintainer, 2026-09-21.* The new Kernel
  `Result` was considered.
  - The refusal is meant to reach the HTTP edge unchanged. Every refusal there — `ProblemCoded`,
    `ProblemExtensions`, and ADR-0029's and ADR-0067's mapping — is an exception.
  - A `Result` from `recordFieldValues()` would be unwrapped with `orThrow()` at its only call site. That adds a
    step and no guarantee: an exception cannot be forgotten either.
  - Being the first caller of a new Kernel category also sets the pattern for every port after it, and that is a
    decision for whoever introduced the category, not a side effect of this task.
  - ▶ **What would reverse it:** a convention, agreed with the category's author, that validation ports return
    `Result`. Adopting it then is local to §3 #3 and the two use cases.

## 5. Verification

### 5.1 Gates

The four default gates (`lint arch phpstan test`) plus `infection`. ⛔ From a worktree they run through the lane
(`make -C ../f5sign-infra wt-backend src=$(pwd)`, with `WT_GATES="infection"` for the fifth), never through the
main-checkout targets, which validate whatever branch that checkout is on.

### 5.2 Tests and sabotages

- **One unit case per row and rule of §3 #4.** Each is sabotaged by deleting its rule and checking that **that**
  case goes red. With several guards in series, a sabotage can report green about a guard it never reached, so
  check which refusal fired, not only that one did.
- **The pattern-skip mirror.** For each signer skip condition, a case that the server also skips:
  - a 201-character pattern;
  - a 4097-character value;
  - `(a+)+$` against `"b"`, which PCRE would enforce at once, but the heuristic skips as the signer does;
  - an uncompilable pattern.

  Plus:
  - a pattern and a value whose `mb_strlen` is under the ceiling but whose UTF-16 length is over it, which is
    skipped;
  - one case per engine failure: the backtrack limit, calibrated with JIT on, and the scoped handler swallowing
    the compile warning;
  - `^\d{2}/\d{2}$`, to pin the delimiter;
  - the four measured agreement rows of §3 #4 (`^\D+$`, `\bfoo`, `^\d{8}[A-Z]$` with a trailing newline,
    `^\w+$`). Sabotage by switching to `/u`: at least one must go red.
- **Key-set parity.** On a fixture where `signs` and `visible` **disagree**, including both occurrence-less limbs,
  the domain predicate equals `EnvelopeContextView::fieldsFor()`. A fixture in which they always agree cannot
  fail.
- **No oracle.** Another recipient's field id and a random uuid produce the same refusal.
- **Roles.** A census over `Role::cases()` for `fillsFields()` that fails on an unclassified member; drop one
  member and check it fails *naming* it. And a commit by a non-filling role on an already-sent envelope: empty key
  set, no `REQUIRED`, nothing stamped.
- **Write-once.** A second `saveFieldValues()` for the same recipient affects zero rows and throws. Sabotage by
  deleting `signed_at IS NULL`.
- **Blanks are SQL NULL**, not JSON `null`.
- **The root lock.** A `ProbesRowLocks` case proves `recordFieldValues()` holds the envelope row. Under DAMA alone
  an unlocked read would stay green.
- **A re-save does not blank a value.** Record, then run any `save()` path, then re-read. This pins `upsertField()`'s
  exclusion, which is now load-bearing.
- **A void mid-commit.** The envelope is voided between the auth-context read and the root lock →
  `ENVELOPE_NO_LONGER_LIVE`, nothing written. The DAMA suite runs one connection, so a concurrent void cannot be
  staged. Use a stubbed auth context that reports the envelope alive over a VOIDED row.
- **The per-field code census.** The `FieldError.code` enum (shipped as `FieldValueError.code`, §9) in the spec equals the Contract enum's cases, and
  none of them appears in the top-level `ProblemCode` catalog.
- **Absent is not empty (D15).** A commit with `filled_fields` absent, on an envelope with only optional data
  fields, writes nothing — no `value`, no `signed_at`, no `false` on a CHECKBOX. The same commit with `[]`
  stamps every shown field and records the CHECKBOX as `false`. With `filled_fields` absent and a required field
  → `REQUIRED`. Sabotage by collapsing absent into `[]`: the first case must go red.
- **`RESERVATIONS`** (§3 #11):
  - one authoring refusal per constraint, plus the second-field refusal;
  - an entry for it in `filled_fields` → `UNKNOWN_FIELD`;
  - a `reservations` longer than its `max_length` → `TOO_LONG` on the field's id;
  - after a commit, its `value` and `signed_at` are still `NULL`, and `recipients[].reservations` carries the
    text;
  - a recipient without the field commits reservations exactly as today.
- **Closed key sets:**
  - on `SignatureCommitted` and `SessionCompleted` (no value in the log);
  - on each `field_errors` record: exactly `field_id` and `code` (ADR-0068 §3.3).

### 5.3 The acceptance case

Over HTTP:
1. Author an envelope and send it: one `TEXT` with a pattern, one required `CHECKBOX`, one `DROPDOWN`, a
   `RESERVATIONS` field with `max_length` 120 on two documents, and a signing gate.
2. Commit **without** `filled_fields` → 422 `FIELD_VALUES_INVALID`, `REQUIRED` on the CHECKBOX alone.
3. Commit with a value that breaks the pattern, without the CHECKBOX, and with 121 characters of reservations →
   422, and `field_errors` names **all three** fields.
4. Commit again, correctly, **with the same signing code** → 200.
5. `GET /api/v1/envelopes/{id}` shows:
   - the three values and their `filled_at`, with `signed_at` null on all three;
   - the `RESERVATIONS` field with `value: null`;
   - the text in `recipients[].reservations`.
6. Replay the successful commit → `SESSION_ALREADY_COMPLETED`.

**Through the delegated route:**
- a dormant-step recipient with a bad value → `FIELD_VALUES_INVALID` before `STEP_NOT_ACTIVE`;
- a clean act → 204;
- a replay of it, even with changed values → `SESSION_ALREADY_COMPLETED`;
- a voided envelope with a bad value → `ENVELOPE_NO_LONGER_LIVE`.

### 5.4 The sweep, immediately before each commit

Case-insensitive, because *"Nothing writes them yet"* begins with a capital:

```
rg -n -i 'current_value|fields_draft|fields_recorded|eleven|nothing writes|does not execute|persists a field value|remain unwritten|is unwritten except|read back on demand|hand back|getFieldValues|sole consumer|completion fact|commit-time (write|validator)|no field validation|reachability guard|null recipient|reflects the session.s draft|BL-(49|50|57|60|64)\b|signed_at' \
   src tests migrations config docs CLAUDE.md
```

Read every hit for **tense**. Beyond §3 #10's list, the hits known on 2026-09-21 are:
- `Field`'s class docblock, whose *"completion fact"* wording stays true once read as §4 D11 reads it;
- `DbalEnvelopeRepository`'s hydration comment and `upsertField()`'s docblock;
- the `FieldValidation` docblock;
- `Version20260803000001` (its bullet **and** its 2026-08-03 banner, *"remain unwritten"*);
- `SigningSession`'s *"today nothing persists a field value"*;
- `SigningSessionAuthGateTest`'s *"nothing in this repo persists a field value"*;
- the three `nelmio_api_doc.yaml` strings of §3 #7.

⚑ **Leave the dated handoff `docs/frontend-handoff/2026-08-18-signer-contract-reconciliation.md` alone**: it is a
historical snapshot, and its hits are records of that day.

## 6. Open follow-ups (track, don't solve here)

- **[BL-268](../BACKLOG.md): a tamper-evident digest of the submitted values.**
  - `SignatureCommitted` would carry an HMAC-SHA256 over the canonical set, sorted by field id, under 32 random
    bytes kept in the session row.
  - It is not a plain hash, because a NIF's value space is small enough to reverse one by enumeration, and the
    log cannot be erased. Destroying the key at purge leaves the digest unlinkable.
  - Until then, the column is the values' only copy until BL-269 draws them. For `SEQUENTIAL_PADES` that lasts
    until its AcroForm half exists, which is longer than for the default mode.
- **[BL-269](../BACKLOG.md): recorded values reach no document.**
  - ⚑ 2026-09-21: the signer now lays a `TEXT` value out by written rules the drawing must follow; the five
    findings of that handoff's review live in the BL-269 row, not here.
  - DSS draws only inside a signature widget and has no form-fill API, and the stack has no PDF engine.
  - [TASK-018](TASK-018-visible-signature-mark.md) F4 records that once a signature exists, modifying a page's
    content corrupts every prior signature. So the two modes need different mechanisms:
    - `SINGLE_SEAL`, the default, can flatten every value before the seal;
    - `SEQUENTIAL_PADES` needs AcroForm fields created before the first signature and filled in incremental
      revisions.
  - A `RESERVATIONS` field is drawn from the recipient's reservations at each of its occurrences
    ([ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md) §2.6).
  - [BL-64](../BACKLOG.md) is answered: closed by decision on 2026-09-21 — accepted — so drawing includes
    occurrences on documents the recipient was not shown.
- **[BL-270](../BACKLOG.md): `FieldType::acceptsValidation()` admits `max_length` / `pattern` on `DATE`**, on
  the rationale that *"a date arrives as typed characters"*. The signer sends ISO from a native date input, and
  neither side applies them. Narrowing authoring is a contract change for the dashboard.
- **[BL-271](../BACKLOG.md): EDITOR does not fill** until the signer can submit a fill-only act. Re-admitting it
  means flipping `Role::fillsFields()` and nothing else.
- **[BL-272](../BACKLOG.md): the regex dialect gap.** The stored pattern is JS source. The signer runs it with no
  flags; the server runs it as PCRE in `(*UTF)` mode with `D` (§3 #4), which closes the `\d` / `\w` / `\b` / `$`
  differences that `/u` would open. What remains in the harmful direction (server stricter):
  - syntax only PCRE accepts, which is enforced here and skipped by the signer: `(?i)`, `(?>…)`, possessive
    quantifiers;
  - counts over characters outside the BMP: `^.{3,}$` against `"😀a"`, because JS counts UTF-16 units;
  - `\s` against Unicode whitespace such as a non-breaking space.

  `\p{L}` is a literal in JS without `u`. The repair is to refuse PCRE-only syntax at authoring, or to detect and
  skip it at the commit.
- **[BL-275](../BACKLOG.md): reservations are written in plaintext into the event log** (since TASK-016), and
  ADR-0069 makes that channel their only home. The maintainer kept it on 2026-09-21, to be revisited soon, with
  the Audit Trail's three-state ADR. Unlike field values, what is written there cannot be enciphered or erased
  later.
- **[BL-49](../BACKLOG.md)** stays open with §4 D9 recorded.
- **[BL-64](../BACKLOG.md)** — a value reaching an occurrence on a document its recipient was not shown — is
  **closed by decision**. The maintainer accepted it on 2026-09-21, on the Factor5 use case: the conjunta is the
  inspection copy and has to carry what the destinatario attested on its own leg.
- **The three-state reservations marker** ("declared none") belongs to the Audit Trail work, not committed on
  2026-09-21 (§8). Its shape is fixed by that work's own ADR. Neither design needs the other's shape.
- **[BL-40](../BACKLOG.md)**, the draft auto-save, does not change this task's contract: the commit carries the
  final values whether or not a draft exists.
- **[BL-276](../BACKLOG.md): a `RESERVATIONS` field's `max_length` bounds the text even when the recipient was not
  shown the field.** Found by the handoff review at landing: ADR-0069 §2.4 has no visibility condition, so a box
  placed only on unseen documents refuses a `TOO_LONG` the signer had no bound to prevent. The maintainer's call:
  bound only when shown, refuse such a box at `send()`, or publish the bound anyway.
- **[BL-277](../BACKLOG.md): the delegated commit stores a blank `reservations` as given** where the recipient's
  route stores `null` — older than this task, and what the Audit Trail's three-state marker would trip on.
- **[BL-278](../BACKLOG.md): on a 5xx, raw values reach the error tracker as stack-frame arguments** — the §4 D9
  classification covers `Pii` objects, not frame variables. The fix is in `f5sign-infra` or `SentryBeforeSend`.
- **[BL-279](../BACKLOG.md): the commit routes are not rate-limited**, and a refused commit is free to repeat.
- Whether the outbound `recipient.signed` notification carries values is
  [ADR-0064](../adr/ADR-0064-outbound-integrator-webhooks.md)'s decision, not this task's.

## 7. The 2026-09-21 audit

Four read-only reviews ran against the first draft of this record: code facts, design against the code,
documentation and conventions, and the signer. What each found that changed the design:

- **Deploy order was backwards.** The first draft had the backend first → §4 D13.
- **The extension seam is scalar-only.** `field_errors` could not be emitted without a Kernel + Foundation change
  → ADR-0068 and §4 D12.
- **`SessionUI` may not import Envelope types.** The draft had the controller building `FilledFieldValues` → raw
  parts, assembled in the use case (§3 #1).
- **The signer's pattern-skip rule was misdescribed** as a runtime limit. It is static → §3 #4 ports it, and §5.2
  pins it.
- **`signed_at` is already published** → the per-type split of §4 D4.
- **The delegated route answers 204.** It gets no echo (§3 #1). Its refusal order was first met with a read-only
  `checkFieldValues()`, which the second pass replaced (below).
- **The key set had no domain home** → one predicate with a parity test.
- **Roles were checked only at send** → also at the commit (§4 D7).
- **EDITOR cannot submit** → deferred (BL-271).
- **Smaller fixes:** the lock rationale borrowed from `saveAppendedArtifact()` was wrong; the sweep missed the
  nelmio YAML, the domain models, the aggregate and a test; and the record list lacked the ADR index, LIVE_SCHEMA,
  LOAD-BEARING and a dashboard handoff.

**The second pass**, two reviews of the rewrite (design, facts), found no blocker. What changed:

- **The read-only `checkFieldValues()` is gone.** It did not fit ADR-0008's query port. The delegated route now
  calls `recordFieldValues()` before its step guard instead, gated so that no standing refusal is masked
  (§3 #6, §4 D5).
- **`/u` made PCRE stricter than JS.** It became `(*UTF)` with `D`, measured by this session on 2026-09-21. The
  review's claim that this form agrees on all four of its rows was itself wrong on one row (the emoji count), so
  that row went to BL-272 with the NBSP case.
- **The skip ceilings** count UTF-16 units.
- **Per-field codes** are a Contract enum, kept out of the top-level catalog `OpenApiSpecTest` builds.
- **The signer sends values only for filling roles.**
- **`fields_recorded`** was defined exactly. §8 later removed it.
- **The default text ceiling** is a constant of its own.
- **The DTO bound** sits above it.
- **The redaction and logging claims** were narrowed to what `SentryBeforeSend` actually covers.
- **BL-50** stays open for limb 1.
- **Six more stale surfaces** joined §3 #10.
- **ADR-0068** names the listener's private return type as well.

What the reviews confirmed, and this record now states as measured rather than assumed:
- the port call inside the commit transaction is the only reading of ADR-0040 Decision 6 that holds;
- a 422 spends nothing;
- no synchronous path takes envelope → session;
- a NUL in `jsonb` is a 500;
- the server's length count is never stricter than the signer's.

## 8. Coordination with the Audit Trail requests (2026-09-21)

On 2026-09-21 another backend session drafted two requests for the envelope Audit Trail, due 2026-10-01: one to
the signer, one to the Factor5 integrator (see the OFFREPO note). They do not build field values, but they talk
about them and about reservations. Read against this record and against the integrator's code, they collided in
four places. The maintainer settled each one the same day.

- **Reservations: a field or the commit channel.**
  - The requests told the integrator to drop its "Reservas" `TEXT` field and rely on the signer's reservations
    box, and told the signer not to let a recipient type into that field.
  - This record, as drafted, would have recorded that field's value.
  - Both halves had a point: the commit channel has the legal semantics, and the field has the place to draw.
  - Recorded as a field, the reservation would have been invisible to the Audit Trail, which would then have
    stated that none was collected.
  - → The hybrid: §4 D14 and ADR-0069.
- **Absence.** The requests' rule is that a `null` is "no consta", never "firmó sin reservas", because only the
  commit knows what was asked. The first drafts of this record treated an absent `filled_fields` as `[]`, and so
  would have recorded blanks and `false` for fields nobody saw. → §4 D15.
- **How values are stored.** The signer request named `PATCH /signing/session/fields` as the not-yet-built way
  to store field values. Here values travel on the commit, and that route is only the draft (BL-40). → The
  unified signer handoff says so (§3 #9).
- **Deploy order.** The requests were additive, and could ship in any order. This record had "the signer first".
  → One deploy of all three (§4 D13).

**Two decisions taken on the same review:**
- BL-64 is accepted, on the integrator's own reasoning for the conjunta.
- The HMAC digest stays deferred (§4 D10). It would share `SignatureCommitted` with the requests' new field, and
  that is recorded in BL-268 for whoever revives it.

**A third design on the same request, found the same day.** The signer session left a proposal in the workspace
notes (`notes/HANDOFF-signing-evidence-capture-2026-09-21.md`, not committed, restated here). It adds an
optional `evidence` block to `POST /api/v1/signing/commit`, following a choice the maintainer made on
2026-09-21:
- geolocation, with its status when denied;
- device context;
- document reading.

The canvas/WebGL fingerprint and stroke biometrics are excluded.

It is **not** in this task's scope: it is evidence custody, and ADR-0032 governs that with its own legal gate. The maintainer split it into [TASK-045](TASK-045-browser-reported-evidence-at-the-commit.md) the same day, plaintext for now like the field values.
But it touches the same DTO, the same use case and the same deploy, and it follows the same two rules as
§4 D15 and the Audit Trail's three states:
- absent is valid and means "not collected";
- nothing collected goes to the permanent log, beyond a commitment if one is needed.

One consequence was fixed here. The Audit Trail request told the signer *"no construyáis nada"* for geolocation,
and the unified signer handoff had copied it. It now says the contract is still to be designed, and that nothing
is to be sent until the deployed spec publishes it.

**The unified handoffs are written by this task.** They carry the requests' other sections unchanged in substance:
the consent text, the conjunta page map, the operator's IP and user agent, contact corrections, the
authentication of a claimed recipient, the smaller notes, and what the Audit Trail will and will not say. So each
consumer receives one document.

## 9. Deviations & honest notes (written at landing, 2026-09-21)

### Scope
- **Two components beyond the design:** `components.schemas.FilledField` (the request item) and the published
  `filled_fields` on both routes' `#[OA]`, which §3 #1 implied without naming.
- **A third handoff**, `docs/frontend-handoff/TASK-044-dashboard-field-values-and-send-refusals.md`, planned by §3 #9
  and written at landing.
- **An existing acceptance fixture changed:** `SigningReadEndpointsHttpTest` authored a required `TEXT` for a
  `CERTIFIED_DELIVERY` recipient and a required `TEXT` reachable nowhere, both of which `send()` now refuses. They
  became an optional `INITIALS` and an optional `TEXT`; what the case proves — neither reaches the signer — is
  unchanged.
- **Test doubles of the port and the repository** gained the new methods in SignatureExecution, Notification and
  Envelope application tests (a doubled interface cannot compile otherwise).

### Decisions taken during the implementation
- **The per-field codes' schema is `FieldValueError`, not `FieldError`** (§3 #3, §5.2): `FieldError` already names
  the request-validation `errors[]` item, and one name for two shapes would have been the ambiguity ADR-0068 §2.4
  refuses for `errors` itself.
- **The port returns nothing; the aggregate returns the skipped-pattern count** and the adapter logs it (§3 #4):
  the count is a fact about one call, and a port method returning it would publish a number no caller needs.
- **`Role::fillsFields()` landed with the domain rules** (tramo 2) rather than with the send guards (tramo 5):
  `fieldsShownTo()` needs it.
- **A readonly field is not stamped by a present form.** §3 #5 says every shown data field is stamped; a
  backend-forced field is not the commit's to write, and none exists today.
- **A `field_id` is lower-cased as it crosses into Envelope**: ids compare exactly in memory and every stored id is
  lower case, so an upper-case id of a real field would otherwise be refused as unknown. The DTO's duplicate check
  is case-insensitive for the same reason.
- **The DTO ceilings are named constants on `FilledFieldsShape`**: 512 entries (equal to
  `FilledFieldValues::MAX_ENTRIES`, held by a test) and 40 000 characters per string.
- **Year 0000 is judged by the proleptic Gregorian rule** (a leap year), since `checkdate()` does not reach it;
  the harmless direction §3 #4 already accepted.
- **Session crosses once, through `Application/Service/CommitFieldValues`**, so both routes translate Envelope's
  refusals identically (ADR-0067 §2.5).
- **The send guard for inert types is stated as a property** — a required field no commit answers and no signature
  produces — rather than as §3 #8's list of five, so a later type joins it without an edit.

### Decisions that needed an ADR
- [ADR-0068](../adr/ADR-0068-a-problem-extension-may-carry-a-list.md) and
  [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md), both approved as text by
  the maintainer on 2026-09-21 before implementation; both exercised here and left `Proposed`. Their promotion to
  `Accepted` was proposed to the maintainer at landing, and the maintainer took it on 2026-09-22.

### Properties declared and not proved
- **ADR-0068's "a record holding a list must fail analysis"** was proved once by a probe implementor that PHPStan
  rejected with `return.type` (2026-09-21); no permanent test holds it.
- **`recipients[].reservations` after a commit** is TASK-016's projection, written by `OnSessionCompleted` once the
  relay carries the fact. The acceptance case asserts the commit's own write (`session.signing_session`) and leaves
  the projection to `SigningLoopTest`, which drives the relay.
- **On the delegated route, a relayed act's signing-challenge refusals and `ASSERTED_DOCUMENT_MISMATCH` now answer
  after `FIELD_VALUES_INVALID`**, where the recipient's route answers its signing-gate refusals first. Nothing is
  spent or leaked; the ordering is untested (security audit W6).
- **No case records field values on another tenant's envelope**; RLS on `envelope.field` and the root load under
  the credential's tenant are what hold it (security audit W7).
- **The acceptance case's delegated half asserts codes, not whole `field_errors` records**; the records' shape is
  held on the recipient's route and by `FieldValuesRejectedExceptionTest`.

### Process
- **Not strict test-first in tramos 1–6.** Code came first and every guard was then sabotaged to see its own case
  go red for its own reason; two sabotages first stayed green, and each changed a fixture or removed an
  equivalent mutant (a third green was a stale bind-mount view, and went red on re-run). The remaining pieces of tramo 6 and tramo 7 were written test-first. Recorded because the
  maintainer asked, and because sabotage proves a test can fail but not that the property was stated before the
  code shaped it.
- **Two of the four validation audits were cut by the maintainer on 2026-09-21, for token cost:** the contract
  check (covered by `OpenApiSpecTest` — presenter key sets against the schemas, the `FieldValueError.code` census,
  the pinned type enums — and by the handoff review, which checked every shape against the code) and the
  persistence guard (no migration; the two touched migrations changed prose only; the write, the lock and the
  re-save each have a sabotaged integration test; a `RESERVATIONS` row inserted against the real schema). The
  security audit, a gate of the runner, ran.
- **The lane ran on isolated checkouts of each commit.** A synced worktree serves `CLAUDE.md` as a symlink the lane
  cannot resolve, so `DocumentationLinkTest` is red there by construction (BL-251); a detached checkout of the
  commit carries the tracked file and runs every gate honestly.

### Debt left, and where it lives now
- BL-276, BL-277, BL-278 and BL-279 (§6), BL-268, BL-269, BL-270, BL-271, BL-272, BL-275, BL-49 and BL-50's first limb — all in
  §6 with their rows.

