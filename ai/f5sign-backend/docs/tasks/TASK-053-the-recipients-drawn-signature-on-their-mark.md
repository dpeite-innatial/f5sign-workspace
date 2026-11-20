# TASK-053 — The recipient's drawn signature appears on their mark

<!-- OFFREPO: the signer facts this record relies on were read from the sibling repository `f5sign-signer` on
2026-10-05, and are restated where they are used:
- the ceremony shows a signature step to a SIGNER or APPROVER, in the modes the session's
  `config.allowed_signature_modes` admits: DRAW (`SignatureCanvas.vue`, `useSignatureCapture.ts`) and TYPE
  (`SignatureTyped.vue`); an UPLOAD mode exists in the app and is not offered against this backend;
- one capture per session, held in `useSignatureStore` in memory only, and sent nowhere against the real backend
  (`useSignFlow.ts`: "the backend has no endpoint for it yet");
- DRAW records strokes as points `{x, y, t, p}` (time in epoch ms, pressure 0..1) and produces no bitmap; TYPE
  holds a text and a CSS font id and produces no bitmap;
- `pages/s/[token]/sign.vue` shows the biometric consent gate only when `config.biometric_capture_enabled` and
  `config.consent_biometric_required` are both `true`, and only for DRAW;
- the signer's docs-future flow names the biometric block `biometric_data: {type: 'GRAPHOMETRIC', strokes,
  canvas_width, canvas_height, device_dpi}`. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/drawn-signature-on-mark`** (code tip `06b3855d`; `9140cdeb` after it changes documents only), 2026-10-07 — suite green under the worktree lane (`wt-f5sign-backend-drawn-signature`, this tree mounted): 6131 tests, 71782 assertions, with lint, deptrac and PHPStan. Infection (run on `1fd39c40`, before the fix round): covered-MSI 84 % (gate 79 %), MSI 61 %. Pending review; not pushed, not merged. Left out as designed: keeping the strokes, UPLOAD, the consent text (§6). The sealed image is not byte-identical to the committed one (§4 D6 measurement, §7): the trail states the digest recorded at the act and says it cannot be checked against the PDF. |
| **Type** | **Forward build.** The commit gains the image of the recipient's signature, drawn on each of their visible marks, and the biometric strokes it was drawn with, which are received and not yet kept. |
| **Why** | The signer asks every recipient to draw or type a signature and then throws it away: against the real backend nothing receives it, so the sealed PDF shows only the recipient's name. A recipient who drew a signature finds no trace of it on the document they signed. |
| **Builds on** | Reused unchanged: [TASK-018](TASK-018-visible-signature-mark.md) (one DSS visible signature per placement, never a stamp on the page's content: F4), [TASK-044](TASK-044-field-values-recorded-at-the-commit.md) (the commit's shape and its narrow write), [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.7 (a step closes on the admission, before the bytes land), [ADR-0040](../adr/ADR-0040-field-entity-unified-placement.md) (biometric strokes never reach `field.value`), [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) (the act's evidence on the session row; the image is kept apart, §4 D5), and the `fieldParameters.rotation: AUTOMATIC` mapping that places a mark on a rotated page. |
| **Scope** | **`SEQUENTIAL_PADES` only, the normal commit route only, DRAW and TYPE only.** Out of scope:<br>• `SINGLE_SEAL`, which never carries a drawn signature (§4 D1);<br>• UPLOAD (§4 D2);<br>• keeping the biometric strokes (§4 D7), which waits for the `biometrics` zone;<br>• the delegated route, whose act is a machine's ([ADR-0055](../adr/ADR-0055-delegated-signature.md)). |
| **Decision record** | **[ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) is amended**: it states that a mark drawn from an image captured at the act reopens its rule for the mark, because *"its digest must be recorded at the act"*. This task records that digest and the trail states it (§3 #6). **[ADR-0032](../adr/ADR-0032-evidence-pii-custody.md) governs the image as personal evidence, and is `Proposed`**: the image is kept by its producer, Session, and only until it is sealed (§4 D5). **[ADR-0009](../adr/ADR-0009-observability-at-the-boundary.md)'s never-serialize rule governs the strokes.** **[ADR-0016](../adr/ADR-0016-storage-model.md), [ADR-0063](../adr/ADR-0063-where-storage-concerns-belong.md) and [ADR-0061](../adr/ADR-0061-retention-deletion-and-purge.md) name where the strokes will be kept**, the `biometrics` zone; this task does not keep them. |
| **Delivery bar** | A `SEQUENTIAL_PADES` recipient who commits with a signature image gets, on every visible mark of every document they sign, their image above their name, and the audit trail states the image's digest. A commit whose image is refused answers 422 and admits nothing. A commit carrying strokes answers as it would without them, and nothing of the strokes is kept or logged. Once the recipient's marks are sealed, nothing outside the PDF holds the image's bytes. |
| **Siblings** | [TASK-045](TASK-045-browser-reported-evidence-at-the-commit.md) changes the same commit request and route; whichever lands later rebases on the other's `CommitSignatureRequest`. [TASK-052](TASK-052-the-signing-gate-is-answered-on-the-act.md), which realized ADR-0075 on the same route, is already on `develop`, and this task builds on its commit. |
| **Coordinated change** | None. The `php-fpm` image (and the worker and relay, which are the same image) is built from this repository's `Dockerfile`, so the `gd` extension of §4 D3 is a change to this repository. An earlier draft placed it in `f5sign-infra`. |

---

## 1. Why this task exists

The visible mark ([TASK-018](TASK-018-visible-signature-mark.md)) renders the recipient's name. TASK-018 §5
deferred the drawn signature in one line: *"Needs the signer app to capture strokes and our edge to accept a PNG.
Slots into `SignatureImage.imagePngBase64` with no model change."*

Two of those three halves are now false or missing:

- **The signer already captures it** and discards it (see the note at the head of this file).
- **Our edge does not accept it**: `POST /api/v1/signing/commit` carries `consent`, `reservations` and
  `filled_fields`.
- **The slot does not work.** `DssPayloadMapper::mapImage()` sends `image: {bytes, mimeType}`, and DSS 6.4
  refuses the request: *"Unrecognized field "mimeType" (class eu.europa.esig.dss.ws.dto.RemoteDocument) … 3 known
  properties: "bytes", "digestAlgorithm", "name""*. Measured against the local DSS on 2026-10-05. Nothing passes
  an image today, so the defect is latent; the first caller would turn every seal into a failure.

## 2. What already exists (reuse, do not rebuild)

- `SignatureImage` carries `imagePngBase64` beside the box and the text, and `SignForRecipientUseCase::marksFor()`
  builds one per placement with the recipient's name as its text.
- DSS draws an image and a text in one widget. Measured on 2026-10-05 against DSS 6.4: image alone, image with
  the name to its RIGHT, image with the name at the BOTTOM, and on a `/Rotate 90` page. With the name to the right
  the image is squeezed into half the box; at the bottom both read well.
- `GetSigningSessionController` publishes the session's `config` with `biometric_capture_enabled: false`,
  `consent_biometric_required: false` and `allowed_signature_modes: ['DRAW', 'TYPE']`, all hard-coded.
- [`EgressAllowList`](../../src/F5Sign/Foundation/Observability/Redaction/EgressAllowList.php) already lists
  `biometric_data`, `strokes` and `signature_image` among the fields that never reach a log. It does **not** list
  `canvas_width`, `canvas_height` or `device_dpi`, although BL-187 says it does; §3 #5 adds them.
- [BL-187](../BACKLOG.md) records the units the signer emits the strokes in: `x`, `y`, `canvas_width` and
  `canvas_height` in logical CSS px, `device_dpi` as `96 × devicePixelRatio` (ISO/IEC 39794-7's header).
- The `biometrics` storage zone: ADR-0016 §2 gives it a 5-year WORM retention, encryption and zero-knowledge
  custody; [TASK-009](TASK-009-evidence-audit-persistence.md) designs its key pair and custodian (v2) and records
  the tension between a platform key and tenant-uniform RLS (§4.5). None of it is built.
- The PHP image has no image library: neither `gd` nor `imagick` is loaded in `php-fpm`.
- Another context already reads Session's commit evidence through a `Contract/Query` port:
  `CommitEvidenceReader` (since renamed [`ActEvidenceReader`](../../src/F5Sign/Session/Contract/Query/ActEvidenceReader.php) by TASK-045, which also serves a decline), implemented by
  `DbalActEvidenceReader` and read by Evidence & Audit's `AuditTrailSources`. The image port of §3 #4 is its
  sibling, with the same shape.

## 3. What gets built

1. **The commit accepts `signature_image`**: a base64 PNG, optional. Refused with 422
   `SIGNATURE_IMAGE_INVALID` when it breaks a bound of §4 D3 or does not decode, and with 422 when the envelope is
   `SINGLE_SEAL` or the recipient has no visible mark: an image that would reach no document is not accepted
   silently. A refusal admits nothing, so the same signing code can commit again.
2. **Storage, temporary** (§4 D5): the image's bytes, as received, in a table of Session's own whose primary key is
   the session id, so it can hold one image per session at most; **not** on `session.signing_session` and not in the
   `SigningSession` aggregate. Each row holds the bytes and their SHA-256. Written once, in the commit's unit of
   work and only after the signing code has passed. Once the recipient's marks are sealed the bytes are
   **cleared**: the column goes to `NULL` and the row stays, keeping the digest (§4 D9). ⛔ Not a column on the session row: `save()`
   upserts every column of that row, so a 100 KB value there would be written again on every later save of the
   session (measured on PostgreSQL 18 on 2026-10-05: +105 KB of TOAST per full upsert re-sending the same bytes, +0
   for an upsert that leaves the column out).
3. **The digest at the act**: the SHA-256 of those bytes in `SignatureCommitted`. The bytes never enter the event
   log.
4. **The mark**: `SignForRecipientUseCase` reads the session's image through Session's contract and passes it into
   each `SignatureImage`. `DssPayloadMapper` sends `image: {bytes, name}` and the text at the `BOTTOM`; the
   `mimeType` defect of §1 is fixed and pinned against the live DSS. The contract answers one of three states:
   no image was committed; the image; or **an image was committed and its bytes have been cleared** (the row keeps
   the digest, so it can tell the last two apart). On the third, the use case returns before any DSS call and
   writes nothing (§4 D9).
5. **The biometric block**: `biometric_data`, optional, accepted only from a DRAW capture beside a
   `signature_image` and with `biometric_consent: true`. Its shape and bounds are validated, and it is then
   discarded: kept nowhere, logged nowhere (§4 D7). `EgressAllowList` gains `canvas_width`, `canvas_height` and
   `device_dpi`.
6. **The trail** (ADR-0072's amendment): the revision of a mark drawn from an image states that it carries one,
   and the image's digest from `SignatureCommitted`. The name stays stated by rule. The wording states the digest
   as recorded at the act, and claims it can be checked against the PDF only if D6's measurement shows it can.
7. **The session's `config`**: `biometric_capture_enabled` and `consent_biometric_required` are `true` exactly
   where the commit takes an image: a `SEQUENTIAL_PADES` envelope and a recipient with at least one visible mark.
   For `SINGLE_SEAL`, and for a recipient whose signatures have no placement, they stay `false`. One predicate
   decides both (`RecipientEnvelopeContextView::marksTakeAnImage()`), so the signer keys on the flag alone and is
   never asked for an image the commit refuses. The published description of the `config` block says so.
   ⚠ The first build set the flag by signing mode alone, so a `SEQUENTIAL_PADES` recipient with no placement was
   asked for an image the commit then refused; the fix round of 2026-10-07 made both read the one predicate.
   ⚑ **Superseded in part by [TASK-054](TASK-054-the-sender-chooses-how-each-recipient-signs.md)**: the two
   flags also follow the recipient's `signature_modes` (`RecipientEnvelopeContextView::commitTakesAnImage()` and
   `offersBiometricConsent()`), and `allowed_signature_modes` is the recipient's setting rather than the
   constant `['DRAW', 'TYPE']`.
8. **The signer handoff** in `docs/frontend-handoff/`: rasterize DRAW and TYPE to a PNG as the recipient saw them,
   within §4 D3's bounds; send `signature_image` only where `config.biometric_capture_enabled` is `true` (§3 #7); send `biometric_data` under BL-187's
   units with the recipient's consent; the error codes of #1.
9. **The records sweep**: ADR-0072's mark rule; TASK-018 §5, TASK-017 §6 and TASK-020's deferral index, whose
   "biometric scribble" deferral this task closes; TASK-045's scope line, which says `biometric_capture_enabled`
   stays `false`; the `SignForRecipientUseCase` docblock that says the ceremony captures *"no scribble"*; and
   BL-187's claim that `EgressAllowList` already lists the canvas dimensions and DPI.

## 4. Key decisions

- **D1 — `SEQUENTIAL_PADES` only** (maintainer, 2026-10-05). `SINGLE_SEAL` produces one company seal and never
  carries a drawn signature. The signer must not ask for one there.
- **D2 — DRAW and TYPE; UPLOAD out** (maintainer, 2026-10-05). It matches what the session already publishes in
  `allowed_signature_modes`. Every image this task accepts is therefore drawn by our own signer's canvas.
- **D3 — the image is stamped as it was sent, and checked before it is admitted** (maintainer, 2026-10-05).
  - What the recipient saw is what lands on the document: the bytes reach DSS untouched, never re-encoded.
  - The signer keeps the image small, because it is repeated in every mark and every mark is its own incremental
    signature. Bounds: a PNG of at most 600 × 240 px and 100 KB; the exact numbers are fixed in the handoff after
    measuring them against a 180 × 70 pt box.
  - The backend checks, in this order: the decoded size, the PNG signature, the `IHDR` dimensions and the `IHDR`
    form in plain PHP, then a full decode with `gd`. `gd` only checks: its result is discarded. A refused image
    never reaches sealing, where it would become an admitted act that cannot be sealed ([BL-366](../BACKLOG.md)).
  - **The `IHDR` form is the one our canvas exports** (maintainer, 2026-10-07, fix round): bit depth 8, colour
    type 2 (RGB) or 6 (RGBA), no interlacing. By D2 every accepted image comes from our signer's canvas, so a
    palette, greyscale, 16-bit or interlaced PNG is refused with `SIGNATURE_IMAGE_INVALID` rather than passed on
    to the decoder and to DSS in a form neither was measured with.
  - **The checks run before the act's unit of work.** Since TASK-052, the commit draws its own unit with
    `UnitOfWork::own()` and a wrong signing code is a refusal that commits (ADR-0075 §2.4). Checking the image
    first means a refused image never costs a code attempt and the `gd` decode never holds the session lock.
  - `gd` needs the extension in this repository's `Dockerfile` and `ext-gd` in `composer.json`. That edit changes
    `composer.lock`'s content hash, so it needs the maintainer's explicit go-ahead (repo rule 1), given on
    2026-10-07.
- **D4 — image above, name below.** The name stays: a scribble identifies nobody, and the name is the mark today.
- **D5 — kept only until it is sealed** (maintainer, 2026-10-05). The copy exists so that sealing, which runs
  after the commit on the worker, can draw the mark. Once the recipient's marks are sealed the PDF holds the image
  and `SignatureCommitted` holds its digest, so the copy's bytes are cleared (D9). It is written only after the signing code has
  passed: under ADR-0075 a wrong code commits its unit, and an image recorded before the check would be kept for
  an act that did not happen.
- **D6 — a plain SHA-256.** TASK-044 rejected a plain hash for field values because a small value space can be
  reversed by enumeration. An image's cannot. The digest is required at the act by ADR-0072, so it is not routed to
  [BL-268](../BACKLOG.md).
  - ⚠ **What the digest can prove once the bytes are cleared was not measured when this record was written.** (Measured since: below.) ADR-0072 already says the
    bytes would come back from the PDF only if DSS keeps the image as it was sent, and a PDF does not embed a PNG
    with an alpha channel unchanged. If DSS re-encodes it, the digest is a commitment made at the act that
    nothing can check against the PDF after D9 clears the copy. The first step of the build measures it: seal a
    mark with a known PNG on the live DSS, extract the image from the PDF, compare. The result is written here and
    in the trail's wording, which must not claim a check that cannot be made.
  - **Measured on 2026-10-07** against the lane's DSS 6.4, with a 300 × 120 RGBA PNG whose alpha is real
    (`SignatureImageMarkTest`). DSS accepts `image: {bytes, name}` with the name at `BOTTOM` and seals it on an
    unrotated and on a `/Rotate 90` page, the widget's `/Rect` on the placement. **The PNG is not kept as sent**:
    DSS re-encodes it as an `/Image` XObject (`/DeviceRGB`, `/FlateDecode` with `/Predictor 15`) whose alpha is a
    separate `/DeviceGray` `/SMask`, so no stream of the PDF has the committed SHA-256. The pixels survive
    exactly: decoded, the RGB and the soft mask equal the PNG's RGB and alpha byte for byte. **So the digest is a
    commitment made at the act**: once D9 clears the copy, nothing can check it against the PDF, and the trail
    says so. A check of the pixels would need the PNG, which is what D9 clears.
- **D7 — the strokes travel now and are discarded** (maintainer, 2026-10-05: option (b), over keeping the capture
  switched off until they can be kept).
  - The contract with the signer is fixed now, so capture and keeping can be switched on independently.
  - They are not kept in the clear, because they are biometric data under GDPR art. 9 and ADR-0016 assigns them
    the encrypted, zero-knowledge `biometrics` zone; in the event log they could never be erased.
  - ⚠ **The recipient is asked for biometric consent for data that is then discarded.** The maintainer chose
    this knowingly. Whether the consent text must say so is legal's question, and is recorded as an open
    follow-up rather than decided here.
  - Without `biometric_consent: true` the block is dropped rather than refused, so a missing consent never blocks a
    signature. A validation failure never echoes a value: no stroke reaches an exception message, a stack frame or
    a log ([BL-278](../BACKLOG.md) is the path that would carry one).
- **D8 — the units are BL-187's.** The handoff restates them, so the follow-up never has to re-scale data already
  written.
- **D9 — the image's bytes are cleared on `RecipientSigned`** (maintainer, 2026-10-05; the row that survives the
  clearing was decided on 2026-10-07).
  - **The trigger.** SignatureExecution emits `RecipientSigned` once per recipient, when **every** document
    assigned to them has its signature, in the same transaction as those artifacts. It is the first moment the
    image is no longer needed, and Session receives it through the relay, after that commit, so the clearing can
    never precede the signatures. `MockSignUseCase` emits it too.
  - **A permitted edge, used for the first time** (checked 2026-10-07). `deptrac.yaml` lets `SessionApplication`
    depend on `SignatureExecutionContract`, so no rule changes. But no Session code imports SignatureExecution
    today, and SignatureExecution already reacts to Session (`OnSessionCompleted`) and will read Session's image
    port (§3 #4). After this task the two contexts depend on each other at runtime, each only through the other's
    `Contract/`. That is the decision, made here, not an accident of the build.
  - **The shape.** A Session reactor on `RecipientSigned` dispatches one command that clears the image of the
    session for that envelope and recipient (the refs the fact carries; the session is found by
    `findByRecipient`). The clearing is idempotent: no row (a recipient who sent no image) or a row already cleared
    (a redelivered fact) changes nothing and succeeds.
  - **Why the row survives** (maintainer, 2026-10-07). The sealing has to tell "no image was committed" from "the
    image was committed and is gone", and the session row is not where the digest lives (§3 #2). Clearing the
    bytes and keeping the row holds the digest without touching `session.signing_session`.
  - **A redelivered sealing after the clearing.** Messenger delivers at least once, so `SignForRecipient` can run
    again after it committed. Today such a rerun signs the first document through DSS again and learns that the
    act committed only when the append is refused ([BL-311](../BACKLOG.md)). After the clearing it would also find
    no bytes. An image that was committed and whose bytes are gone can only mean the act already landed, since the
    clearing follows `RecipientSigned`, so the use case returns before any DSS call (§3 #4). This closes BL-311 for a
    recipient who sent an image, and only for that case.
  - **A seal that never lands** (DSS failing past its retries, or a mark that cannot be sealed,
    [BL-366](../BACKLOG.md)) keeps the image, and that is intended: replaying the failed message needs it. The
    envelope cannot end meanwhile: `EnvelopeCompleted` is recorded only once every admitted signature has landed
    (`EnvelopeVoided` and `EnvelopeClosedBySender` close it, they do not end it). So the image stays exactly as
    long as the envelope stays stuck, which is BL-366's problem, not a new one.
  - **No other backstop** (maintainer, 2026-10-07). The clearing is a reactor like any other: the relay delivers
    at least once, and a handler that fails past its retries lands on the `failed` transport, from which it is
    replayed. A second clearing on the envelope's end was considered and dropped. ⚠ An earlier draft named "the
    session's own purge" as the backstop; no purge of session rows exists (`app:signing-token:purge` deletes
    credentials only).

## 5. Verification

- **Gates:** suite, PHPStan, deptrac and lint, under the lane that mounts this tree; the `php-fpm` image of the lane
  must carry `gd`.
- **Tests and sabotages:**
  - The mapper's full DSS payload with an image, pinned; sabotage by re-adding `mimeType`.
  - Against the live DSS: a mark with an image and a name seals, on an unrotated page and on a `/Rotate 90` page,
    and the widget's `/Rect` is the placement's.
  - Against the live DSS: whether the image extracted from the sealed PDF has the committed SHA-256 (D6). This
    is a measurement whose result is recorded either way, not a bar that must be green.
  - The image checks: one case per bound and per stage, each answering 422 and admitting nothing — oversized,
    not a PNG, `IHDR` beyond the dimensions, an `IHDR` form other than the canvas's (one case per field), valid
    header with a truncated body (the case only `gd` catches).
    Sabotage the `gd` stage and watch the truncated body get admitted.
  - `SINGLE_SEAL`, or a recipient with no visible mark, with an image → 422.
  - The session `config`: `true` for a `SEQUENTIAL_PADES` recipient with a visible mark, `false` for one with no
    placement and for `SINGLE_SEAL`.
  - `biometric_data` without `signature_image`, without consent, or ill-formed: the commit's answer is the one it
    gives without the block, and **no column, event or log line** carries a stroke. Assert the closed key set of
    `SignatureCommitted`.
  - The trail: a revision drawn from an image states it and its digest; one drawn without states neither.
  - The image is in its own table, never in the session aggregate: a later save of the session leaves its row
    untouched.
  - A commit with an image and a wrong signing code stores nothing; with a refused image and a wrong code, the
    image refusal answers and no attempt is charged.
  - A refusal after the code has passed (the admission refuses), then a retry that succeeds: exactly one image is
    stored, the retry's. A second insert for the same session fails on the primary key rather than duplicating or
    overwriting.
  - After `RecipientSigned`, the session's row holds no bytes and keeps the digest; the same fact delivered twice
    changes nothing and succeeds; a recipient with no image is a no-op.
  - A redelivered `SignForRecipient` after the clearing makes no DSS call and writes nothing. Sabotage: drop the
    cleared-state check, and watch the rerun reach DSS.
  - A sealing that fails leaves the image in place.
  - `EgressAllowList` refuses `canvas_width`, `canvas_height` and `device_dpi`.
- **Acceptance:** over HTTP, a `SEQUENTIAL_PADES` recipient with two placements commits with an image and a
  biometric block; until sealing, Session holds the bytes whose SHA-256 is the one in `SignatureCommitted`; the
  sealed PDF carries two marks with the image, and after that nothing outside it holds the image's bytes (the
  digest stays); nothing holds a stroke.

## 6. Open follow-ups (track, don't solve here)

- **Keeping the strokes** (D7): the maintainer intends to keep them long-term, enciphered, soon. Where and how is
  not decided: enciphered in the database, or ADR-0016's `biometrics` zone with the key pair and custodian TASK-009
  designs for v2 (and its §4.5 RLS tension); nor are legal's retention and DPIA. TASK-009 §4.4 records that
  biometric evidence is on the durability path, so it is written with the act, not after it.
- **The consent text** while the strokes are discarded (D7): legal's question.
- **UPLOAD** (D2), if it is ever offered: an image the recipient did not draw in our canvas.
- **[BL-366](../BACKLOG.md)**: a mark whose box cannot be sealed still reads as done; the image adds no new way to
  fail at sealing, because D3 refuses it at the commit.
  While a seal never lands, the envelope stays `SENT` and the image stays with it (D9).
- **[BL-171](../BACKLOG.md)** (appended): the image waits for sealing as plaintext `BYTEA` in
  `session.signature_image`, so it joins the personal data no carrier enciphers yet. Its lifetime is the shortest of the set.
- **[BL-278](../BACKLOG.md)** (extended): the image travels as scalars on the commit path; `#[SensitiveParameter]`
  keeps it out of a rendered frame, and the infrastructure half of that row's fix closes the rest.
- **[BL-382](../BACKLOG.md)**: the request body is capped only at 50 MB and `biometric_data` is fully decoded before
  its bounds apply; a session-credential holder can force a 500 against `memory_limit`. Low severity.
- **[BL-383](../BACKLOG.md)**: two Envelope acceptance tests that assert recipient order flake in Infection's initial
  run; cost two restarts here.
- **[BL-384](../BACKLOG.md)**: `develop`'s lock cannot be re-resolved (see §7).
- **Residue, fixed before the merge**: the first round inserted `withSigningMode` and `withSigningAssignments` in
  `tests/F5Sign/Session/Testing/Fake/FakeEnvelopeQuery.php` between `withCredentialsRetiredAt` and its docblock, so
  the docblock's warning about the auth-generation near-miss sat on the wrong method. It is back on its method.

## 7. Deviations & honest notes

### Scope
- None beyond the plan, except what the decisions below imply: `ext-gd` in the Dockerfile and `composer.json`
  (with the lock's `content-hash`), `Session`'s new reactor and table, and the `docs/ddd/` and `docs/LIVE_SCHEMA.md`
  updates, all of which §3 anticipated.

### Decisions made during implementation
- **The clearing joins in the store's UPDATE, not `findByRecipient`** (D9 said the session is found by
  `findByRecipient`). The clearing touches only the image row, so it needs no aggregate load and takes no session lock.
- **A separate code, `SIGNATURE_IMAGE_NOT_ACCEPTED`**, beside `SIGNATURE_IMAGE_INVALID` (the record said only "422"): one
  says the image is bad, the other that this recipient's marks take none.
- **The base64 length is measured before decoding**, with the same refusal as the byte bound, so an oversized string
  is never allocated twice.
- **Text-only marks stay at `RIGHT`**; text goes to `BOTTOM` only beside an image, so no existing mark moves.
- **The trail's digest is its own `Revision` member, sourced `LOG`**, not a field of `Mark`, whose statement is
  `ROW_CURRENT`; putting it there would have made the source label false.
- **`composer.lock`**: only its `content-hash` and the platform entry changed, with the hash computed by Composer's own
  rule (it reproduces the previous hash on the unchanged file), because `composer update --lock` cannot resolve
  `develop`'s lock (`symfony/psr-http-message-bridge` 8.1 against `extra.symfony.require` 7.4.\*). Filed as BL-384.
- **The config flags follow the signing mode and the recipient's marks.** The first build keyed them on the mode alone;
  the fix round made them read the one predicate the commit's refusal uses (`marksTakeAnImage()`), so the signer is never
  asked for an image the commit would refuse.
- **W5, the `IHDR` form**: bit depth 8, colour type 2 or 6, no interlacing, one message per field, checked after the
  dimensions and before `gd`.
- **W6, the live read-back asserts "nothing broken"** (count, last signature ends at EOF, not `TOTAL_FAILED`, no
  `HASH_FAILURE` / `SIG_CRYPTO_FAILURE` / `FORMAT_FAILURE`), not `TOTAL_PASSED`: in the lane every sound signature reads
  `INDETERMINATE` / `NO_CERTIFICATE_CHAIN_FOUND`, so its certificate verdict is not trusted evidence.
- **The shared image tag `f5sign/backend:dev` carries `gd` from this branch's build until it merges**; other checkouts
  running on that tag see the extension without having asked for it.
- **The handoff is in Spanish**, like its siblings in the signer's handoff folder.

### Decisions that needed an ADR
- **[ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) amended in place** by this build (the mark's
  rule, *Enforced by*, the revision arc), already `Accepted (realization partial)`. [ADR-0032](../adr/ADR-0032-evidence-pii-custody.md)
  stays `Proposed`; see the close report for why.

### Declared and unproven properties
- **The sealed image is not the committed bytes.** Against the live DSS 6.4 (2026-10-07) the PNG is re-encoded
  (`/DeviceRGB` Flate with `/Predictor 15` and a `/DeviceGray` `/SMask`): no stream in the PDF has the committed SHA-256,
  while pixels and alpha survive byte for byte. The trail therefore states the digest as recorded at the act.
- **Concurrency of the clearing**, as with every row-lock property here: `Integration/` runs one connection.
- **The certificate verdict of the sealed signatures** (W6 above).

### Dismissed finding, not filed
- **Security audit W2** ("a voided, closed or expired envelope keeps the image forever") is wrong. `EnvelopeVoided` and
  `EnvelopeClosedBySender` close the envelope without ending it; an admitted act still seals and emits `RecipientSigned`,
  which clears the image. The second `spec-claims` run verified it against the code. D9's backstop discussion stands.

### Debt left behind, and where it lives now
- Image at rest in plaintext: BL-171. Frame arguments in the error tracker: BL-278. Request-body cap and `biometric_data`
  decode: BL-382. Recipient-order flake in Infection's initial run: BL-383. The unresolvable lock: BL-384.
- Strokes, consent text, UPLOAD, BL-366: §6 above.
