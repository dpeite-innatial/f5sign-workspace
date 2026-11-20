# TASK-067 — Recorded field values are drawn into the signed PDF

<!-- OFFREPO: §2's "Measured" facts come from a spike the owner ran with this session on 2026-10-21 against the local stack's EU DSS 6.4 and pyHanko 0.29.0 in a throwaway container; its notes, scripts and the PDFs checked in Adobe Reader live in the workspace root (`notes/spike-pdf-field-values-2026-10-21/`). The signer's text layout rules live in the signer repository (`app/utils/fieldTextLayout.ts`, golden cases `tests/fixtures/field-text-layout/golden-v1.json`). Every fact taken from either is restated here; nothing in this record depends on reading them, except the golden-case file, which §3 #3 copies into this repository. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/field-values-drawn-into-the-pdf`** (code tip `ec5dbc12`, 2026-10-21), suite green under the `wt-backend` lane with the task's runtime image (`f5sign/backend:dev-task067`, pyHanko 0.29.0): 8190 tests, 92551 assertions, 0 failures, lint, deptrac and PHPStan clean at `ec5dbc12` (develop's TASK-065 merged in). Infection: see §7, *Infection verdict*. Pending review; merge to `develop` follows. Left out, each with a BACKLOG row (§6): refusing an unpreparable PDF at upload, `RADIO`, our own lock check, the signing service, DSS 6.5.1, and the security audit's residuals. Not repeated on the shipped files: the tamper check (a locked value changed after its signature). |
| **Type** | **Forward build** in Signature Execution: before every signature applied to a document, in both signing modes, the values the parties recorded are drawn into that document as read-only AcroForm fields, and the signature that follows locks them; plus one Envelope change, reservations recorded at the admission (§3 #6). |
| **Why** | Since [TASK-044](TASK-044-field-values-recorded-at-the-commit.md) a value a party types or ticks is recorded in `envelope.field.value` and reaches **no document** ([BL-269](../BACKLOG.md)). The signed PDF a recipient downloads, and the one an integrator files, does not carry what was attested. The Factor5 eCMR flow runs `SEQUENTIAL_PADES` and needs the values on the document, each one locked by the next signature its document receives: the filler's own when the filler signs it, otherwise the next party's or the seal (§4 #3). Deadline set by the owner: end of October 2026. |
| **Builds on** | [TASK-044](TASK-044-field-values-recorded-at-the-commit.md) (the recorded values), [TASK-018](TASK-018-visible-signature-mark.md) (the visible mark, F4: after a signature, editing page content corrupts it), [TASK-053](TASK-053-the-recipients-drawn-signature-on-their-mark.md) (the drawn image on the mark), [ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md) (one byte path for sign and seal), [ADR-0041](../adr/ADR-0041-field-definition-and-occurrences.md) (one value, every occurrence), [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md) (reservations). |
| **Scope** | Envelope documents, in both signing modes (owner, 2026-10-21), plus one change in Envelope: a recipient's reservations are recorded when their commit is admitted, beside the field values (§3 #6). The audit trail's own seal (`DssPdfSealer`, the `PdfSealer` port) and `SealFixtureCommand` keep today's path: their PDFs carry no fields. Refusing an unpreparable PDF at upload, `RADIO`, our own lock check and a signing service of our own are out (§6). |
| **Decision record** | [ADR-0085](../adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md), **Accepted 2026-10-21** by the owner, exercised by this task. It amends [ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md) (a signing act's artifact carries a fill revision before its signatures) and [ADR-0023](../adr/ADR-0023-dss-server-signing-seal-flow.md) (the signature parameters name a field we created, `fieldId`; the four calls are unchanged). It also replaces the placement mapping of [TASK-018](TASK-018-visible-signature-mark.md) (coordinates in `DssPayloadMapper` become our field, named by `fieldId`; `rotation: AUTOMATIC` stays, to orient the mark), and records the engine choice against [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §7.11, which rejected WeasyPrint for its ~99 MB of GPL system libraries and the Python shim it needed. |
| **Delivery bar** | A `SEQUENTIAL_PADES` envelope with two signers and an approver, each filling fields, signs end to end against the live DSS; every signature stays cryptographically intact, the DSS report shows each signature's FieldMDP, and the revision each signature covers holds the values recorded up to it (S-1). |

---

## 1. Why this task exists

TASK-044 made the values round-trip: the commit carries them, the server validates them, and they land in
`envelope.field.value`. It deferred drawing them, because the two signing modes need different mechanisms
and the stack had no PDF engine (TASK-044 §6, BL-269).

The constraint is TASK-018 F4: once a document carries a signature, PAdES allows only filling **existing**
form fields, adding signature fields, and adding validation data or timestamps. Writing on a page
(`/Contents`, `/Resources`) after a signature makes validators reject that signature. So in
`SEQUENTIAL_PADES`, where every signer's act is a real incremental signature, values cannot be stamped; they
have to be form fields that exist before the document's first signature and are filled in later revisions.

On 2026-10-21 the owner and this session measured that this works (§2, *Measured*), and the owner chose the
shape in §4.

## 2. What already exists (reuse, do not rebuild)

**The signing path (Signature Execution).**
- `OnSessionCompleted` dispatches `SignForRecipient`; `SignForRecipientHandler` delegates to
  `SignForRecipientUseCase`, which returns early unless the envelope's mode is `SEQUENTIAL_PADES`, reads the
  recipient's signature image (`SignatureImageReader::forRecipient`), builds one `SignatureImage` per
  `FieldPlacement` of each signing `DocumentAssignment` (`marksFor`), and calls `DocumentSigner` per
  document. A chain conflict re-reads the context (bounded attempts); `ArtifactAlreadyAppendedException`
  returns silently (redelivery converges).
- `SealEnvelopeUseCase` seals every document with a tip once the envelope is `READY_TO_SEAL`, through the
  same `DocumentSigner` (`seal`), in both modes; voided envelopes are sealed too
  ([ADR-0070](../adr/ADR-0070-an-envelope-ends-in-agreement-or-is-voided-and-sealed.md),
  [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)).
- `DocumentSigner::apply` reads the tip bytes from custody, calls `dss->seal(SignRequest)` **once per mark**,
  chaining the bytes (no marks = one invisible signature), then stores the result as a compare-and-swap:
  `appendDocumentArtifact(expectedTip)`, custody written after the append. One artifact per signing act
  per document ([ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md) Decisions 4–5,
  [ADR-0016](../adr/ADR-0016-storage-model.md)).
- `DssHttpAdapter::seal` runs the server-signing calls (keys, `getDataToSign`, `server-signing/sign`,
  `signDocument`) with one `parameters` object reused verbatim ([ADR-0023](../adr/ADR-0023-dss-server-signing-seal-flow.md)).
  `DssPayloadMapper::mapImage` sends `fieldParameters {page, originX, originY, width, height, rotation:
  AUTOMATIC}`; `validate()` calls `validateSignature`, and `DssValidationReport` parses it.
- `ChainConflictRetryStrategy` retries a lost chain race and otherwise delegates to the transport's backoff.

**The values.**
- `EnvelopeQueryInterface::getContextForSE` is Signature Execution's only read of Envelope. Its
  `EnvelopeContextView::$fields` holds every `FieldView` of the envelope (`id`, `recipientId`, `type`,
  `occurrences`, `choices`, `value`, `signedAt`); `fieldsFor()` narrows to what a recipient can read, which
  drawing must **not** use ([ADR-0041](../adr/ADR-0041-field-definition-and-occurrences.md) §6,
  [ADR-0069](../adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md) §2.6).
  `RecipientView::$reservations` holds a recipient's reservations; a `RESERVATIONS` field's value stays
  `NULL` (ADR-0069 §2.2). ⚑ **Today they are written later than the field values.** `Envelope::admitCommit`
  records `field.value` but only checks the reservations against the field's `max_length`; the column
  `recipient.reservations` is written by `Recipient::markCompleted`, reached through
  `recordRecipientCompletion`. In `SEQUENTIAL_PADES` that completion is driven by `RecipientSigned`
  (`Envelope\Application\Subscriber\OnRecipientSigned`, driver `SIGNATURE`), i.e. **after** the recipient's
  own signature, so the read their act is built from carries `null` reservations. The text does travel on
  `SignForRecipient::$reservations` and on `RecipientCompleted`; the audit trail reads them from neither,
  but from Session's `SignatureCommitted` (`TrailAssembler`), so it does not depend on the column. The placement
  is historical: TASK-016 added reservations before admission existed (TASK-044, ADR-0073), and no record
  requires the write to wait for the completion; ADR-0069 §2.2 only requires the column TASK-016 uses.
- `FieldOccurrence` = document id + `FieldPlacement` (`page`, `originX`, `originY`, `width`, `height`, PDF
  points, origin top-left, y downward — [ADR-0040](../adr/ADR-0040-field-entity-unified-placement.md)
  Decision 1). `FieldType` has twelve members; fillable today: `TEXT`, `DATE`, `CHECKBOX`, `DROPDOWN`,
  `RADIO` (+ `RESERVATIONS`, filled from the reservations).
- Roles (`Role::fillsFields()`): `SIGNER` and `APPROVER` fill; `REVIEWER`, `VIEWER`, `IN_PERSON_HOST`,
  `EDITOR` (BL-271) and `CERTIFIED_DELIVERY` do not. `Role::signs()` is `SIGNER` only, so an approver's
  values have no signature of their own.

**The external-binary pattern.** `TypstTrailRenderer` runs a pinned binary through
`Symfony\Component\Process\Process` with an empty environment and a timeout, and checks its version against
a pinned identity; the binary path is a parameter (`evidence_audit.typst_binary`), and the `Dockerfile`
copies it into the `dev` and final stages. No Python exists in the image today.

**Geometry.** No code reads a page's MediaBox, CropBox or `/Rotate` ([BL-366](../BACKLOG.md)). The visible
mark relies on DSS's `rotation: AUTOMATIC`; DSS measures from the MediaBox, so on a page whose CropBox is
offset the mark shifts by the offset (BL-366 (4)).

**Tests to keep green or extend.** `SignForRecipientUseCaseTest`, `DocumentSignerTest`, `DssHttpAdapterTest`,
`DssPayloadMapperTest`, `ChainConflictRetryStrategyTest`, `SequentialPadesLoopTest` (counts one `%%EOF` per
PDF revision), `AnnulmentSealTest`, and the live-DSS tests in `#[Group('eIDAS-signing')]`:
`RotatedPageMarkTest`, `SignatureImageMarkTest`, `MarkTextFitTest`, `VisibleSignatureMarkTest`.

<!-- OFFREPO: the spike notes in the workspace root, `notes/spike-pdf-field-values-2026-10-21/`; every fact below is restated and nothing here depends on reading them. -->

**Measured on 2026-10-21** (restated from the spike):
- Fields created before the first signature and filled in later revisions leave every DSS signature intact:
  every change is classified `SignatureOrFormFill`, `Undefined: 0`. DSS adds one warning to the earlier
  signature, *"Visual difference is detected on page(s) [N]"*, which a chain without fields does not show;
  the indication does not change.
- Signing **into** a signature field we created, carrying a `/Lock` (`SigFieldLock`, `Include`, field
  names), via `fieldParameters.fieldId`, makes DSS write a `FieldMDP` reference with those fields. Creating
  that signature field in the same revision as the fill, right before the signature, works the same as
  creating it up front.
- **Adobe Reader enforces the lock** (checked by the owner): a locked field changed after the signature makes
  that signature invalid; the same change without a lock leaves it valid.
- **DSS 6.4 does not enforce it**, and 6.5.1 does not either: its lock check compares the locked names with
  the names of modified fields, and a changed `/V` is recorded on the value, which has no `/T`, so the list of
  modified names is empty (`ObjectModification::getFieldName`, `AbstractPdfLockDictionaryCheck`). The change
  itself is listed in the report.
- When DSS creates its own signature field it rewrites the page's widgets with identical content; harmless,
  but avoided by signing into our own field.
- A partial field name must not contain `.` (it is the hierarchy separator); a checkbox's `/AP /N` state
  dictionary must be direct, or poppler does not paint it.
- pyHanko 0.29.0 in a venv on `php:8.5-fpm-alpine` runs on musl. Measured on this branch's images (W1): the
  runtime image grows by 90.1 MB and the dev image by 90.0 MB; preparing and filling a small PDF peaks at
  53,636 KiB (`ru_maxrss`). The spike notes' "93 MB" and "55 MB" were rounded recollections, not measurements
  taken here (§7, *Decisions made*).
- **Not measured by the spike:** every signature it put into a field of ours carried a visible, text-only
  mark (no PNG), on page 0, unrotated, with no CropBox offset. The `/Rotate` 90, offset-CropBox page was used
  only to look at drawn data fields. §5 (*Notes on AC-9*) measures the rest first.

**Measured on 2026-10-21, second probe** (live DSS 6.4; each case a second signature after one into
another field of ours, which stayed `Undefined: 0`):
- **AC-9b holds.** An invisible signature goes into our field (`/Rect [0 0 0 0]`) when `imageParameters`
  carries only `fieldParameters.fieldId`, and DSS writes the `FieldMDP` from our `/Lock`. With no
  `imageParameters` at all, DSS ignores our field and creates its own `Signature1`, with no lock.
- A mark with the PNG (`ZOOM_AND_CENTER`, text `BOTTOM`) signs into our field the same way.
- On `/Rotate` 90, 180 and 270, `fieldId` alone keeps our rectangle but draws the mark sideways or upside
  down; adding `fieldParameters.rotation: AUTOMATIC` beside `fieldId` draws it upright on the displayed
  rectangle, within 1–3 pt. `ROTATE_90` turns it the wrong way, `NONE` equals sending nothing, and a widget
  `/MK /R` is ignored.
- On a page whose CropBox is offset, a field whose user-space rectangle is the displayed one plus the
  CropBox's origin receives the mark on the displayed rectangle.

## 3. Scope

1. **The engine.** pyHanko 0.29.0, pinned, in a venv at `/opt/pyhanko` in the `dev` and final `Dockerfile`
   stages, driven by a script under `assets/signature-execution/` (non-PHP runtime files go in `assets/`),
   behind a Signature Execution port with one adapter that runs it as a process, like `TypstTrailRenderer`.
2. **Preparation.** The first time a document is about to receive a signature from this system, the data
   fields are created: one AcroForm field per `Field` of type `TEXT`, `DATE`, `CHECKBOX`, `DROPDOWN` or
   `RESERVATIONS` placed on that document (not `FieldType::isFillable()`, which includes `RADIO` and excludes
   `RESERVATIONS`), read-only, named
   `f5s_<fieldId>`, one widget per occurrence on that document (a field with N occurrences is one field with N
   `/Kids` sharing one `/V`), no `NeedAppearances`.
3. **Drawing.** Before every signature applied to an envelope document — a recipient's or the seal, in either
   mode; the drawing lives in `DocumentSigner`, so `SealDocumentUseCase` (documented as test-only) draws too —
   one incremental revision fills every value recorded in the envelope read that document's signature is built
   from, and not yet drawn, with an appearance we generate, and
   creates the signature field that signature will occupy, with a `/Lock` over the fields filled in that
   revision. Per type:
   <!-- OFFREPO: the rules are the header of the signer's `app/utils/fieldTextLayout.ts` and its golden cases `tests/fixtures/field-text-layout/golden-v1.json`; the rules are restated here and the golden file is copied into this repository. -->
   - `TEXT` and `RESERVATIONS`: the signer's layout rules — Helvetica (WinAnsi, not embedded), 10 pt down to
     7 pt, 3 pt padding, multi-line from a box height of 60 pt; lay out the original text and substitute
     characters WinAnsi lacks only when drawing (`?`, width 556, the fallback width); the signer's golden
     cases are copied into `tests/` pinned by their `version` and reproduced;
   - `CHECKBOX`: `/V` and `/AS` `/Yes` or `/Off`, a ZapfDingbats check;
   - `DROPDOWN`: `/V` holds the chosen value and the appearance draws that choice's label, the text the
     signer chose from (`FieldChoice`'s value is an identifier, not prose; owner, 2026-10-21); `/Opt` holds
     `[value label]` pairs. A value matching no current choice is drawn as itself;
   - `DATE`: the recorded ISO string as text ([BL-270](../BACKLOG.md) leaves the display format open).
4. **Signing into our field.** Every signature applied to an envelope document goes into the field step 3
   created, through
   `fieldParameters.fieldId`; the four DSS calls are otherwise unchanged. The placement's rectangle is
   converted by us from the displayed page (top-left, y down) to PDF user space, accounting for `/Rotate` and
   the CropBox. `fieldParameters.width`/`height` (the placement's) are still sent beside `fieldId`, or DSS
   sizes an image-above-name appearance to its content and viewers squash it (measured, second probe,
   2026-10-21). `fieldParameters.rotation: AUTOMATIC` is still sent beside `fieldId`: it no longer places
   the rectangle (our field does), it turns the drawn mark upright on a rotated page (measured, §2). An
   invisible signature sends `imageParameters` carrying only `fieldParameters.fieldId`; without
   `imageParameters` DSS ignores our field and creates its own, unlocked (measured, §2).
5. Records: ADR-0085 (Proposed), the `docs/adr/README.md` rows, the living docs, and a §6 row per deferral.
6. **Reservations recorded at the admission** (owner, 2026-10-21; Envelope). `Envelope::admitCommit` writes
   the commit's reservations to `recipient.reservations` in the same unit of work as `field.value`, so the
   read a recipient's own act is built from already carries them, and their signature locks them (AC-20).
   The completion no longer decides the text: `markCompleted` writes it only while the column is still
   `null` (a commit admitted before this ships), and otherwise leaves the admitted text as it is.
   `RecipientCompleted` keeps carrying the reservations; the audit trail, which reads them from
   `SignatureCommitted`, is unaffected. **Accepted consequence** (owner, 2026-10-21): the column's readers —
   `recipients[].reservations` and `has_reservations` on the envelope's JSON, and the signing-session read's
   `current_value` of a `RESERVATIONS` field — show the text from the admission on, as `field.value` already
   is, including for a recipient a failed act leaves `PENDING`. The `admitCommit` docblock ("only checked")
   and `markCompleted` are swept with the change.

Concepts re-cut: `rotation: AUTOMATIC` (still sent for envelope documents, but it now only orients the drawn mark; the rectangle is our field's), "one incremental revision per recipient per
document" (ADR-0034: now a fill revision plus the signatures), the mark's placement being DSS's to map, and
"a recipient's reservations are recorded at their completion" (TASK-016: now at the admission).

## 4. Key decisions

1. **One path for every signature** (owner, 2026-10-21): every signature, with or without values to lock,
   goes into a field we create. Two paths would double what must be measured, and ours also corrects the
   CropBox offset.
2. **A document that cannot be prepared is signed without drawing** (owner): if it already carries a
   signature this system did not apply, or an XFA form, or the engine cannot read it at all (owner,
   2026-10-21, after a malformed test fixture showed it: a PDF whose cross-reference table is broken signs
   in DSS but cannot be opened by pyHanko, even leniently), its values are not drawn, the act proceeds, and
   an `error` log line names the envelope, the document and which of the three it was. Refusing such a PDF at upload needs a PDF reader in
   Envelope and is out (§6). An envelope already in flight when this ships falls in the same branch for any
   document that was signed before.
3. **A signature locks every field filled in its revision** (owner), including an approver's, whose values
   have no signature of their own and are drawn in the next signature the document receives. Each document's signature is
   built from one read of the envelope (a recipient's act reads at its start and again after a chain conflict;
   the seal reads once per delivery), so a value another party commits after that read is drawn by the next
   signature too.
4. **Text that does not fit at 7 pt** (owner): `/V` holds the full text; the appearance is cut at 7 pt and its
   last visible line ends in `…`; a `warning` log line names the field. Pages cannot be added after a
   signature, so there is no annex.
5. **`SINGLE_SEAL` draws too** (owner): at the seal, preparation, the fill and the seal happen in one act, one
   artifact. A voided envelope is sealed with what was recorded before the void.
6. **An unexpected drawing failure blocks the signature** (owner, 2026-10-21). A crash, a timeout, or output
   that fails AC-17 fails the act with nothing appended, and the transport retries it as it retries a DSS
   failure today (four retries, then the failure transport, replayable; `app:envelope:report-pending-seals`
   names an envelope left closed and unsealed). Signing without drawing is reserved for the document that can
   never be prepared (§4 #2): an unsealed envelope can be replayed once the cause is fixed, while a document
   signed without its fields can never receive them.
7. **No lock check of our own yet**: Adobe enforces the lock and DSS does not (§2). Proving which value a
   signature covered stays possible by cutting the file at that signature's `/ByteRange` (§6).

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | Before a document's first signature, its data fields exist: read-only, named `f5s_<fieldId>`, one widget per occurrence with a shared `/V`, no `NeedAppearances` | owner | Integration (real script) | name a field with a `.`; drop the read-only flag |
| AC-2 | Each kind of signature on an envelope document goes into a field created in the same revision as the fill, with a `/Lock` over the fields filled there; DSS signs it through `fieldId`; earlier signatures stay intact (`Undefined: 0`) (members AC-2a…c) | owner | Integration, live DSS | send coordinates instead of `fieldId` |
| AC-3 | Each type is drawn as §3 #3 says (members AC-3a…e) | owner | Integration (real script) | see *Notes on AC-3* |
| AC-4 | A placement lands on the displayed page whatever its `/Rotate` and CropBox (members AC-4a…b) | owner | Integration, live DSS | see *Notes on AC-4* |
| AC-5 | The engine is pinned and checked: pyHanko 0.29.0 in `/opt/pyhanko` in the `dev` and final stages; the adapter refuses a different version | owner | Integration + image build | change the pinned version |
| AC-6 | The DSS report shows, for each kind of signature, a `FieldMDP` listing exactly the fields filled in its revision, and the bytes up to its `/ByteRange` hold the values the act read (members AC-6a…c) | owner | Integration, live DSS | drop the `/Lock` |
| AC-7 | Before any signature of a document, the values the act read and not yet drawn are drawn, per role: drawn for the two filling roles, nothing for the five others (members AC-7a…g) | derived — rule 5 | Application + Integration | see *Notes on AC-7* |
| AC-8 | Values reach occurrences on documents the filler was not shown; a `RESERVATIONS` field shows the recipient's reservations, not `field.value` | derived — docs/adr/ADR-0069-a-reservations-field-places-the-recipients-reservations.md | Application | draw from `fieldsFor()`; draw from `value` |
| AC-9 | A recipient with several marks on one document: the fill precedes the first, each mark lands on its placement; a signature with no mark (a recipient without placement, the seal) goes invisibly into a field of ours (members AC-9a…b) | derived — docs/adr/ADR-0034-sequential-incremental-pades.md | Integration, live DSS | see *Notes on AC-9* |
| AC-10 | A failing or timed-out drawing appends no artifact and fails the act the way a DSS failure does today | derived — docs/adr/ADR-0034-sequential-incremental-pades.md | Application | swallow the drawing error |
| AC-11 | A retry after a chain conflict, or a redelivery, never fills a field already drawn; a drawn value that differs from the record is logged at `error` and left untouched | derived — docs/adr/ADR-0034-sequential-incremental-pades.md | Integration (real script) | drop the already-drawn check |
| AC-12 | No value travels on the command line or lands in a file: input on stdin, output on stdout, empty process environment | derived — docs/BACKLOG.md | Unit | pass the values as an argument |
| AC-13 | `SequentialPadesLoopTest` counts the revisions exactly (today it asserts at least three); the audit trail of such an envelope renders with no failing check (`CheckRule`) and no unmatched signature, still one artifact per signing act | derived — docs/adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md | Integration | append the fill as its own artifact |
| AC-14 | `SINGLE_SEAL`: the seal prepares, fills the recorded values and seals in one act and one artifact, whichever way the envelope ended (members AC-14a…b) | owner | Integration, live DSS | gate drawing on `SEQUENTIAL_PADES` |
| AC-15 | Text that does not fit at 7 pt: `/V` holds the full text, the appearance ends in `…`, one `warning` log line names the field | owner | Integration (real script) | drop the ellipsis; truncate `/V` |
| AC-16 | A document carrying a signature this system did not apply, an XFA form, or bytes the engine cannot read (`PDF_UNREADABLE` from `inspect`), or a page geometry the conversion cannot place on (a `/Rotate` not a multiple of 90, a CropBox outside the MediaBox), is signed without drawing, with one `error` log line naming envelope, document and reason (members AC-16a…d) | owner | Integration (real script) for a…c; AC-16d Application + adapter (a shell fake reports the page) | prepare it anyway |
| AC-17 | Before DSS is called, the drawing's output is checked in PHP: it begins with the input bytes exactly, and the summary the script returns after re-opening its own output (each field's `/V`, the signature field and its `/Lock`) matches what was asked; a mismatch fails the act with nothing appended (members AC-17a…e) | derived — docs/tasks/TASK-018-visible-signature-mark.md | Application + Integration (real script) | see *Notes on AC-17* |
| AC-18 | A drawing failure logs the envelope, the document, the exit code and the error kind, and never the script's output or error text, which can carry values | derived — docs/BACKLOG.md (BL-278) | Unit | log the script's error output |
| AC-19 | The drawing process runs under a timeout (set on the `Process`) and a memory cap (the script sets `RLIMIT_AS` on itself first, from a value the adapter passes); exceeding either fails the act like AC-10 | derived — src/F5Sign/EvidenceAudit/Infrastructure/Render/TypstTrailRenderer.php | Integration (real script) | drop the memory cap |
| AC-20 | In `SEQUENTIAL_PADES`, a signer's own `RESERVATIONS` field is drawn in their own signature's revision and locked by it: the admitted commit has written `recipient.reservations` before their act reads the envelope; a completion leaves an admitted text unchanged and fills a `null` one | owner | Application + Integration | write the reservations only in `markCompleted` |
| S-1 | A `SEQUENTIAL_PADES` envelope with two signers and an approver, each filling fields across two documents (one rotated, one with an offset CropBox), signs and seals end to end against the live DSS; the trail renders | owner | Integration, live DSS | — |

<!-- OFFREPO: the lane's compose file lives in the sibling repository `f5sign-infra` (`docker-compose.wt.backend.yml`, service `php-fpm-wt`); the bullet below restates what it does, and nothing here depends on reading it. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane of this worktree, after the lane's
  image is rebuilt from **this worktree's** `Dockerfile`. Today the lane cannot do that: `php-fpm-wt` in
  `f5sign-infra/docker-compose.wt.backend.yml` builds from the main checkout (`context: ../f5sign-backend`)
  under the fixed tag every lane shares, and only the code is bind-mounted from the worktree. A coordinated
  `f5sign-infra` change (its own branch and PR, owner, 2026-10-21) lets a lane name its build context and its
  image tag by variable, defaulting to today's values; the gates run on a lane built that way, and the
  harness line names the tag.
- **Manual (owner):** the PDF S-1 produces is opened in Adobe Reader; a copy with one locked value changed
  after its signature shows that signature invalid.

**Notes on AC-2** (and AC-6, same members: AC-6a…c)
- AC-2a — a recipient's signature (`SignForRecipient`, `SEQUENTIAL_PADES`). Sabotage: coordinates instead of `fieldId`.
- AC-2b — the seal of a `SEQUENTIAL_PADES` envelope. Sabotage: the same.
- AC-2c — the seal of a `SINGLE_SEAL` envelope. Sabotage: the same.
- AC-6 reads `FieldMDP` from the DSS report's diagnostic data, which `DssValidationReport` does not parse and
  `DssClientInterface` does not expose: the test calls `validateSignature` itself through a test-side helper,
  so no Contract type (`ObservedSignature`) changes. Sabotage for each member: drop the `/Lock`.

**Notes on AC-3**
- AC-3a — `TEXT` reproduces every golden case of the signer's layout rules. Sabotage: change the 3 pt padding.
- AC-3b — `RESERVATIONS` is laid out by the same rules. Sabotage: draw it at a fixed 10 pt.
- AC-3c — `CHECKBOX` sets `/V` and `/AS` and paints the check with a direct `/AP /N`. Sabotage: make `/N` indirect.
- AC-3d — `DROPDOWN` keeps the chosen value in `/V` and draws its label. Sabotage: draw the first choice; draw the value.
- AC-3e — `DATE` draws the ISO string. Sabotage: reformat it.

**Notes on AC-14**
- AC-14a — an agreed envelope. Sabotage: gate drawing on `SEQUENTIAL_PADES`.
- AC-14b — a voided envelope: what was recorded before the void is drawn. Sabotage: skip drawing when voided.

**Notes on AC-16**
- AC-16a — a signature this system did not apply. Sabotage: prepare it anyway.
- AC-16b — an XFA form. Sabotage: prepare it anyway.
- AC-16c — bytes the engine cannot read (owner, 2026-10-21): only `inspect`'s `PDF_UNREADABLE` takes this
  branch; every other engine failure, and any failure after `inspect` succeeded, still blocks the act (§4 #6).
  Sabotage: rethrow it.
- AC-16d — a page geometry `PageBox` refuses (orchestrator, 2026-10-21, by analogy with AC-16c after the security
  audit: a property of the document that would fail every retry). A placement off a valid page is not in
  this branch. Sabotage: rethrow the geometry refusal.

**Notes on AC-17, AC-18, AC-19** (provenance)
- AC-17's prefix half comes from TASK-018 (every signature preserves the bytes before it); its summary half
  is this record's own design (§4 #6), confirmed by the owner on 2026-10-21.
- AC-18 follows [BL-278](../BACKLOG.md), where raw values reached the error tracker as stack-frame
  arguments: a Python traceback carries the same risk.
- AC-19 follows `TypstTrailRenderer`, which runs its binary under a `Process` timeout and handles a process
  the kernel kills for memory. Symfony `Process` has no memory cap of its own, hence the script's own limit.

**Notes on AC-17**
- AC-17a — the output does not begin with the input bytes (an earlier revision rewritten). Sabotage: drop the
  prefix comparison.
- AC-17b — a field's `/V` in the summary differs from the requested value. Sabotage: skip the value comparison.
- AC-17c — the summary lacks the requested signature field. Sabotage: skip the signature-field check.
- AC-17d — the signature field lacks its `/Lock`, or locks other fields. Sabotage: skip the lock check.
- AC-17e — the summary reports a change nobody asked for: a field outside this revision's fill whose value
  differs from what `inspect` read, or a signature or data field not requested (orchestrator, 2026-10-21,
  after the security audit). Sabotage: skip the untouched check.

**Notes on AC-4**
- AC-4a — `/Rotate` 0, 90, 180 and 270: the mark and the values land where `RotatedPageMarkTest` expects.
  Sabotage: ignore `/Rotate`.
- AC-4b — an offset CropBox: the mark and the values land on the displayed rectangle (BL-366 (4)).
  Sabotage: measure from the MediaBox.

**Notes on AC-7** (census of `Role`, `fillsFields()`)
- AC-7a — `SIGNER`: values drawn in their own signature's revision, locked by it.
- AC-7b — `APPROVER`: values drawn in the document's next signature (another signer's or the seal), locked by it.
- AC-7c…g — `REVIEWER`, `VIEWER`, `IN_PERSON_HOST`, `EDITOR`, `CERTIFIED_DELIVERY`: nothing drawn.
  Sabotage for each: flip `fillsFields()` for that member and watch the case name it.

**Notes on AC-9**
- AC-9a — two marks of one recipient on one document: one fill revision, two signatures, both marks on their
  placements. Sabotage: fill before each mark.
- AC-9b — an invisible signature into a field of ours. **Measured first**, before the slice that depends on
  it; if DSS refuses `fieldId` without a visible mark, the slice stops and the decision returns to the owner.
  Sabotage: give the field a visible rectangle.
<!-- OFFREPO: "the spike" is the one in the header's OFFREPO note (workspace root, `notes/spike-pdf-field-values-2026-10-21/`); the fact used below is restated in §2's *Measured* list, and nothing here depends on reading the notes. -->
- **Measured together, first** (owner, 2026-10-21): §2's last *Measured* bullet records that the spike
  signed into our field only with a text-only mark on an unrotated page 0. So three things are measured against the live DSS in one probe, before any
  slice that depends on them: AC-9b; a mark carrying the PNG (`ZOOM_AND_CENTER`, text below) signed through
  `fieldId`; and `fieldId` into a field placed by our conversion on a `/Rotate` 90 page and on a page with an
  offset CropBox (AC-4). If DSS refuses any of them, the work stops and the decision returns to the owner.

## 6. Open follow-ups (track, don't solve here)

Each has its BACKLOG row, written when this task closed (2026-10-21); the ids are beside each item. The audit's residuals have their own list at the end.

<!-- OFFREPO: the two bullets below restate measurements taken on the local stack on 2026-10-21 (`docker stats` of the `eu-dss` container) and the EU DSS release notes for 6.5 and 6.5.1 (published by the European Commission, `esig/dss` on GitHub), plus the image in the sibling repository `f5sign-infra`; every fact is restated and nothing here depends on reading them. -->
- **A signing service of our own, replacing the DSS demo webapp.** **[BL-449](../BACKLOG.md).** Measured 2026-10-21: the `eu-dss` container
  holds 1.48 GiB with `-Xmx1g` and 247 jars, for four signing calls and one validation call; each signature
  sends the PDF to it twice and back once. A service on the DSS libraries and PDFBox would do fill, lock and
  sign in one call, pick its DSS version, and own the keystore. It is a new codebase and supersedes
  ADR-0012 and ADR-0023; deferred for the deadline.
- **DSS 6.4 → 6.5.1.** **[BL-450](../BACKLOG.md).** Brings DSS-3946 (a signature field's appearance could change without invalidating
  the signature), a DPI change for visible signatures (DSS-3789/3799) and an image placement fix
  (DSS-3779) that need the mark re-measured, and Spring Boot 4 in the demo, which needs Tomcat 11 in
  `f5sign-infra`'s image.
- **Our own lock check.** **[BL-451](../BACKLOG.md).** For each signature, compare the values of its locked fields at its `/ByteRange`
  with the final document. It is the test DSS cannot give and the tool for a dispute.
- **`RADIO`** is not drawn: one box holds all its choices, and drawing a real radio group needs a widget per
  choice. **[BL-452](../BACKLOG.md).**
- **Refusing at upload** a PDF that already carries a signature or an XFA form (§4 #2). **[BL-453](../BACKLOG.md).**
- **The display format of a `DATE`** stays [BL-270](../BACKLOG.md).
- **[BL-268](../BACKLOG.md)**, a tamper-evident digest of the submitted values, is still open: drawing narrows
  the window (a value is signed at the next signature) but does not close it.
- **Security audit residuals (2026-10-21)**, none blocking; each is a BACKLOG row, and the audit's three
  "fix now" items were fixed in slice 21 before the close:
  - the `#[\SensitiveParameter]` census is a hand-listed set that cannot see a new value-carrying parameter
    ([BL-454](../BACKLOG.md));
  - the engine child has `RLIMIT_AS` and a 20 s timeout but no CPU, process-count or open-file limit, and PHP
    holds the PDF three times ([BL-455](../BACKLOG.md));
  - a shared `/Kids` DAG expands without bound in `page_tree`, and a deterministic `MEMORY_LIMIT` on a hostile
    PDF fails the act on every retry ([BL-456](../BACKLOG.md));
  - the child runs without a sandbox, with the php-fpm user's privileges and network
    ([BL-457](../BACKLOG.md));
  - the base image, `apk add python3` and the venv's own `pip` and `setuptools` are not digest-pinned
    ([BL-458](../BACKLOG.md));
  - the sixteen Python wheels are hash-pinned but never CVE-scanned (no `pip-audit`), `oscrypto` is
    unmaintained, and unused transitive packages widen the surface ([BL-459](../BACKLOG.md));
  - a recipient's reservations are written in the clear at the admission instead of at completion
    ([BL-460](../BACKLOG.md), beside [BL-171](../BACKLOG.md) and [ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md));
  - engine edge cases the closing review left at low confidence ([BL-461](../BACKLOG.md)).
- **[BL-366](../BACKLOG.md)** is amended, not closed: its (4), the CropBox shift, is done for envelope documents;
  an off-page placement on a drawn document is no longer refused (§7). **[BL-269](../BACKLOG.md)** is closed by this task.

## 7. Deviations & honest notes

### Scope
- Files beyond the slices' lists, all kept: `tests/Fixtures/pyhanko-fakes/echoes-request` (the only test of the
  apply request's encoding), `tests/Fixtures/pdf-form-reader.py` (no longer descends into a `/Sig` field's
  `/V`; own commit `9c8b71d5`), a stale comment in `tests/F5Sign/Session/Acceptance/FieldValuesAtTheCommitHttpTest.php`
  (rule-1 fix), and the `FieldValuesDeliveryBarTest` output written to `var/delivery-bar/`.
- `tests/Fixtures/pdf/sample.pdf` was hand-written with wrong offsets (DSS rebuilt it, pyHanko could not read
  it even leniently), so after the engine landed every act on it failed. It is rewritten well-formed and the
  original kept as `tests/Fixtures/pdf/broken-xref.pdf` (slice 16).
- Nothing touched `deptrac.yaml`, `phpstan*`, `Kernel/`, `Foundation/` or `migrations/`.

### Decisions made during implementation
- **Owner, 2026-10-21, taken during the run (already in §4/§5):** `DROPDOWN` draws the chosen value's label (a
  value matching no choice draws as itself); an unreadable PDF (`PDF_UNREADABLE` at inspect) is signed without
  drawing, with an `error` log (AC-16c, §4 #2); reservations are recorded at the admission (AC-20, §3 #6).
- **Co-step lock (§4 #3, owner-decided, stated plainly):** a signature locks every field filled in its
  revision, so in a parallel step one signer's signature can draw and lock a co-step signer's admitted but
  not yet signed values. `FormRevisionPlanner::fillOf` does not ask whether that owner's own signature has
  landed. It is the decided behaviour, not a deferral, and no test builds a parallel step.
- **Orchestrator rulings, by analogy or technique:** AC-16d geometry; AC-17e left untouched; `/Lock` is an
  indirect object (ISO 32000 Table 232); the script reads leniently (`strict=False`), still writing one
  incremental update, because a strict read would fail every act on a PDF DSS signs today; appearances use our
  own `/F5SHelv` (Type1 Helvetica, WinAnsi) in `/DR`, never a foreign `/Helv`; `width` and `height` travel
  beside `fieldId` in the visible payload (measured); the "Also" invariant (throw if the planner returns fewer
  signature-field names than marks) is dropped, because `FormRevisionPlanner` always returns one name per mark
  and the throw would be unreachable code; `rotation: AUTOMATIC` stays beside `fieldId`, the invisible
  signature sends `imageParameters {fieldParameters {fieldId}}` only; signature field names are random
  (`f5s_sig_<16 hex>`) so a redelivery cannot collide.
- **Measured W1 against the record's §2:** the runtime image grows 90.1 MB and the dev image 90.0 MB; prepare
  plus fill peaks at 53,636 KiB `ru_maxrss`. The record's "93 MB" and "55 MB" came from no measurement in the
  spike notes; §2 is corrected.
- The engine's failure is an exception, not a `Result` (the caller's DSS failures already throw into the
  transport's retry); logging goes through `Application/Port/FieldDrawingLog`.
- Slice-level notes: a MockSign completion used to blank `recipient.reservations` and now keeps the admitted
  text; `RecipientCompleted` still carries the completion's reservations on its payload (a `Contract/Event`
  payload change is out of scope); `FormEngineFailure` is the only plain enum in a `ValueObject/` directory;
  `NotPreparableReason` lives in `Application/Port`; inspect reports `PDF_UNREADABLE` also for a page-tree
  cycle or a page without `/MediaBox`, so those are signed without drawing; kind mismatch exits 5, a
  duplicate fill name, a checkbox with appearances and a non-positive size exit 2; `TZ` cannot be set in the
  image (no zoneinfo), so warnings are ignored and stderr goes to the null device.
- `FieldValueRecordingTest` was red on the day's clock (a pre-existing date bomb); resolved by merging
  `develop` (`715f6ea0`), which brought the clock pin.
- A redelivery over the act's own tip runs the engine again and appends a new unlocked signature field before
  the append converges, and an envelope signed before deploy logs `documentNotPreparable` worded as
  foreign-signed (signing as before is correct); both recorded in slice 11.

### Decisions that needed an ADR
- [ADR-0085](../adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md), proposed in planning and
  accepted by the owner on 2026-10-21, before implementation. Its §2.6 was amended during the run for the
  unreadable-PDF decision. It also amends ADR-0023 and ADR-0034 (both carry the amendment). No further ADR was
  needed and no acceptance proposal comes from the close.

### Declared and unproven properties
- **The tamper check on the shipped files.** A copy with one locked value changed after its signature should
  show that signature invalid. The owner observed it in the 2026-10-21 spike, not on the sealed PDFs of S-1.
  Those PDFs (rotated page, offset CropBox) were opened in Adobe Reader and the owner reported placement and
  signatures right. DSS does not enforce the lock and our own lock check is out ([BL-451](../BACKLOG.md)).
- **Upright drawing on a rotated page** is pinned by the unit payload assertion and the probe's rendered images,
  not by the live test.
- **AC-16a/b (foreign signature, XFA)** have no end-to-end case through the real script; the pieces are covered
  separately (the script's inspect case, `FormStateTest`, `DocumentSignerTest` with fakes).
- **Locked versus unlocked row reads and a second connection** are not reachable by the suite (one connection
  under DAMA); this task adds no row lock.
- arm64 hashes of the pinned wheels were not checked; the wheels were not CVE-scanned.

### Debt left behind, and where it lives now
- §6 lists each item with its row: BL-449 (signing service of our own), BL-450 (DSS 6.5.1), BL-451 (own lock
  check), BL-452 (`RADIO`), BL-453 (refusing at upload), BL-454 to BL-460 (the security audit's residuals),
  BL-461 (the closing review's engine edge cases); [BL-270](../BACKLOG.md) and [BL-268](../BACKLOG.md) already existed.
- **BL-269 is closed** (this task, ADR-0085). **BL-366** is amended: its (4), the CropBox shift, is done for
  envelope documents (the widget's `/Rect` is ours, from `PageBox`); a document signed without drawing still
  goes through DSS's coordinates and keeps the old shift. **An off-page placement on a drawn document is no
  longer refused** (DSS never sees coordinates): it is signed where `PageBox` puts it, which may fall outside
  the CropBox, so the mark is invisible. The "BL-269 depends on (1) and (4)" clause is gone.
- The published OpenAPI strings for `recipients[].reservations` and `has_reservations` stay true, but the text
  now appears from the admission, including for a recipient whose signature never lands. The integrator
  (factor5 dashboard) adjusted on its side to read it only once the recipient is SIGNED. No backend change; the
  contract is for the contract check to judge.

### Delegated work
- No slice delegated to the `replicator` (every slice report's `## Delegated` reads none, or "no shape with
  three or more targets").
- 21 slices (15 planned, 6 fix slices), 59 commits on the branch: 17 critical on `opus`, 4 standard on `sonnet` (02, 03 planned; 16, 18 fix slices). Wave 1 (01 to 05) ran in parallel. Review rounds by slice: 0 for 02, 03, 07, 09, 10, 11, 15,
  16, 17; 1 for 01, 04, 05, 06, 08, 12, 13, 14, 18, 19, 20; 2 for 21. Five of the one-round fixes were
  prose-only and closed by the orchestrator reading the diff instead of a second review.
- Fix slices added after the plan (15 planned slices): 16 (fixture), 17 (unreadable PDF, owner decision), 18
  (mark tests compare numbers), 19 (mark appearance sized to our field, a defect slice 18 surfaced), 20
  (closing fixes), 21 (security hardening).

### Cost of the run
- Slices: 21 (planned 15 plus 6 fix slices); tiers: 17 critical, 4 standard; models: `opus` for critical,
  `sonnet` for standard; review rounds: 13 in total; no escalation recorded in `run.log`. Token totals per
  model are not in `run.log` (the orchestrator's Phase 7 table has them if it was kept).
- Gates: baseline 6458 tests; final full suite 8015 tests, 90,792 assertions, 0 failures at `337c4afd`, on
  the `wt-backend` lane with the task image; lint 0 of 2191 files, deptrac 0 violations, PHPStan clean.
- Closing review: verdict *changes* (6 findings: records, a mis-cited criterion, a security hardening), all
  fixed in slice 20 or by this close; security audit: 0 blocking, 11 warnings; eIDAS: warnings only.

### Infection verdict
- **Gate:** `wt-backend-infection` in changed-lines scope (f5sign-infra `4df531b`, `--git-diff-lines`,
  `--fail-on-survivors`), bars 85 covered-MSI / 70 MSI, on `ec5dbc12` (the branch with develop's TASK-065 merged
  in), `wt-backend` lane, image `f5sign/backend:dev-task067`, 2026-10-21. **MSI 96 %, covered MSI 97 %.**
- **First run** (`91b0e8db`, the same gate): MSI 83 %, covered 88 %, with 87 escaped, 43 not covered and 4 timed
  out on changed lines. An earlier gate never counted not-covered mutants (fixed in infra the same day), so the
  slices' own reports did not see them. Fix slices 22a–d killed about a hundred with tests (each checked by
  re-applying the mutant by hand) and removed two pieces of dead code (`array_values` in `PageBox`, a
  `max(1, …)` floor in `FieldTextLayout`).
- **Survivors left, each justified** (the gate fails on any survivor on a changed line, so its exit stays red;
  this list is the verdict):
  - 18 escaped, equivalent or unreachable: `DrawnRevisionCheck` 86/97/108 `TrueValue` (the arrays are read only
    through `isset()`); `FieldTextLayout` 91 `IncrementInteger` and 148 `LessThan` (boundary steps that give the
    same layout), 189 `Concat` (a width is a sum of per-character widths); `HelveticaWidths` 86 `ReturnRemoval`
    (losing the early return loses only the cache); `PageBox` 75 `CastFloat` (an int widens to float in every
    use); `PyHankoFormEngine` 121 `Throw_` (the rotation guard next to it refuses the same input), 218/235/239/
    300/301/302 `UnwrapArrayMap` and 285 `UnwrapArrayValues` (the request objects already carry the protocol's
    key names; the bytes are pinned by the request test), 352 `?? -1` ×2 (the exit code is null only for a
    signalled process, which `run()` has already refused).
  - 4 timed out, `FieldTextLayout` 73/152/189: each mutant loops forever by construction; Infection counts a
    timeout as detected.
  - 10 not covered, `HelveticaWidths` 89–94 (the loops that build the width table once): an attribution
    artifact of the static cache. Re-applying 90 (`0x20`→`0x21`) and 94 (`0xA0`→`0xA1`) by hand turns
    `HelveticaWidthsTest` red (4 of 12) each time; the gate attributes the table's construction to whichever
    test calls it first.
