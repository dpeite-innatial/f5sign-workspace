# eidas-compliance — TASK-067

**Status:** WARN

Read-only review of `changes.diff`, which is identical to `git diff f0199eb8..4a1a27fa` (checked byte for byte). No tests or docker were run. The cited green run is the full suite at **4a1a27fa** = HEAD: 8001 tests, 0 failures, lint/deptrac/phpstan clean, on the wt-backend lane image `f5sign/backend:dev-task067` (`run.log`, last `full-suite` line). It covers the tip, so no further run is needed for anything below. The live-DSS cases (`eIDAS-signing` group) are part of that suite.

## Conformant
- **Level: PADES_B_B, digest SHA256, format PAdES.**
  - Both are hard-coded on the one signing path: `src/F5Sign/SignatureExecution/Application/Service/DocumentSigner.php:162-163`.
  - Nothing added by the diff raises the level, adds a digest as a raw string, or adds XAdES/CAdES/JAdES. Grepped every `+` line of the diff; the only `CAdES` hit is a `/SubFilter` in a test fixture's foreign-signature PDF.
- **DSS is still the only signer (ADR-0012).**
  - The script imports only `pyhanko.pdf_utils.{generic,incremental_writer,reader}` and `pyhanko.version` (`assets/signature-execution/form_engine.py:598-601`).
  - None of pyHanko's signing API is used.
  - pyHanko is pinned by version and by hash (`assets/signature-execution/pyhanko-requirements.txt`, `--require-hashes`).
- **A fill revision comes before the act's first signature, and it is one artifact per act per document (ADR-0085 §2.1, amending ADR-0034 D4–5).**
  - Order: inspect → plan → apply → check, then the DSS loop over the drawn bytes, then a single open/append/write (`DocumentSigner.php:139-209`).
  - `seal()` and `sign()` share `apply()` (`:90`, `:115`), so `SINGLE_SEAL` and the annulment/unagreed seal draw too. Live tests: `FieldValuesDrawnSingleSealTest`, and `AnnulmentSealTest::assertFillThenInvisibleSealAddedOver`, which checks exactly +2 `%%EOF`, exactly one new `/Type /Sig`, `/T (f5s_sig_`, and only zero-area `/Rect`s.
- **Incremental revisions keep earlier signatures.**
  - `DrawnRevisionCheck::verify` refuses output that does not begin with the input bytes, or that is not longer than them, before DSS is called (`Application/Service/DrawnRevisionCheck.php:305-307`). It then checks every filled value and every requested lock (`:309-344`).
  - The script writes through `IncrementalPdfFileWriter` (`form_engine.py:342`).
  - Live DSS validation checks that every earlier `/ByteRange` is found again intact after the seal (`AnnulmentSealTest::assertEarlierSignaturesStillValidate`; also `FieldValuesDrawnSequentialTest::every_signature_stays_intact` and `FieldValuesDrawnSingleSealTest::the_seal_stays_intact`).
- **No data field is ever created after a signature exists (TASK-018 F4).**
  - Fields are created only when `!isPrepared()` (`FormRevisionPlanner.php:164`).
  - A document that is not prepared is preparable only with 0 signatures (`Domain/Pdf/Response/FormState.php:47-50`).
  - So creation implies a signature count of 0. Later revisions only fill existing fields and add signature fields.
  - The fonts in `/DR` are added only when absent (`form_engine.py:384-392`), so in practice only at preparation.
  - The script refuses to overwrite a field that already has `/V` (`form_engine.py:544`).
- **Field locks (/Lock, ADR-0085 §2.8).**
  - Each signature field gets an indirect `/SigFieldLock` with `/Action /Include` over exactly the names filled in this revision. No lock is written when nothing was filled (`form_engine.py:565-569`; `FormRevisionPlanner.php:182-194`).
  - The check requires the reported lock to be absent when none was asked for, and the same sorted set otherwise (`DrawnRevisionCheck.php:321-344`).
  - Live: `FieldIdSigningTest` reads the `FieldMDP` DSS writes, and `FieldValuesDeliveryBarTest::each_signature_locks_the_values_filled_in_its_revision` checks it.
  - Not machine-enforced (ADR-0085 §3.2, stated): DSS 6.4/6.5.1 do not enforce `FieldMDP`. Adobe enforcement was seen in the spike, not on S-1's files (`run.log` manual-owner line).
- **Widget placement (Step 4: origin top-left, y down).**
  - `PageBox::place` converts from the displayed page (CropBox clipped to MediaBox, `/Rotate` clockwise) to PDF user space (`Domain/Pdf/Form/PageBox.php:87-97`).
  - I re-derived the 0° and 90° cases by hand: the display's top-left maps to `(cx0, cy1)` and `(cx0, cy0)` respectively, which matches the code.
  - Live: `FieldIdSigningTest::the_mark_keeps_our_rect_on_a_rotated_page` and `::the_mark_keeps_our_rect_on_an_offset_cropbox`, plus `PageBoxTest`.
  - The CropBox shift of BL-366 (4) is fixed for documents that get drawn.
- **One `imageParameters` = one widget = one incremental signature.**
  - The loop makes one DSS round trip per mark, or one invisible `[null]` when there are none (`DocumentSigner.php:158-175`).
  - The planner makes one signature field per mark, or one `/Rect [0 0 0 0]` field when there are none (`FormRevisionPlanner.php:184-194`).
  - Live: `FieldValuesDrawnSequentialTest::two_marks_follow_one_fill_and_land_on_their_placements` and `SequentialPadesLoopTest`, which counts revisions exactly.
- **The DSS payload maps fieldId correctly (ADR-0085 §2.2, amending ADR-0023).**
  - Visible: `fieldParameters {fieldId, width, height, rotation: AUTOMATIC}` (`Infrastructure/Pdf/DssPayloadMapper.php:173-188`).
  - Invisible: `imageParameters {fieldParameters {fieldId}}` only (`:83-87`). This avoids the measured "DSS ignores our field and creates its own, unlocked" failure.
  - The coordinate path is unchanged for `fieldId === null` (`:189-202`), which covers a document that cannot be prepared and the audit trail's `DssPdfSealer`, which is untouched by the diff.
  - `parameters` is still built once and reused for `getDataToSign` and `signDocument`.
  - Test: `DssPayloadMapperTest`.
- **The SINGLE_SEAL path.**
  - The tip is the original, so preparation, fill and an invisible seal locking every filled field happen in one artifact (chain `UPLOAD, SEAL`).
  - A voided envelope is sealed with the values recorded before the void (`FieldValuesDrawnSingleSealTest::a_voided_envelope_is_sealed_with_what_was_recorded_before_the_void`).
- **The annulment / unagreed seal.**
  - It is the same invisible seal through `seal()`, with a fill revision under it.
  - The decline reason and the decliner's name never enter the PDF (`AnnulmentSealTest`, `encodingsHeldBy`).
  - A signature admitted before a void and landing after it is sealed over, still intact (`AnnulmentSealTest::a_signature_admitted_before_the_void_and_landing_after_it_is_sealed_in`).
- **Failure split (ADR-0085 §2.6).**
  - Only inspect's `PDF_UNREADABLE`, XFA or a foreign signature leads to signing without drawing, through the old coordinate path, with an `error` log (`DocumentSigner.php:141-142`, `:218-235`).
  - Every other engine failure is logged and rethrown before custody or append (`:150-154`), so the act is not appended half-drawn.
- **Custody (Step 5, ADR-0016 / BL-14).**
  - The order is unchanged by the diff: transient `open()`, then the CAS `appendDocumentArtifact(expectedTipId)`, then `write()` (`DocumentSigner.php:183-209`). Those lines are context-only in the diff.
  - The fill happens before all of it, so a refused fill writes nothing.
- **Retry and redelivery.**
  - A chain-conflict retry re-reads, re-inspects and re-plans with fresh `f5s_sig_` names. Nothing from the lost attempt is persisted.
  - A redelivery converges on `ProducedBy` before the CAS, so its re-drawn bytes are discarded (`slices/11.review.md:33-38`).

## Findings
- **[cross-party-lock · WARN · confidence 60] A co-step signer's values can be drawn and locked under another signer's signature.**
  - `FormRevisionPlanner::fillOf` fills every owner whose role `fillsFields()` and whose value is recorded. It does not ask whether that owner's own signature has landed (`src/F5Sign/SignatureExecution/Application/Service/FormRevisionPlanner.php:216-224`).
  - Values are recorded at the admission (`Envelope::admitCommit`, `src/F5Sign/Envelope/Domain/Aggregate/Envelope.php:1344-1353`), and the signature follows asynchronously (`Application/Subscriber/OnSessionCompleted.php:55`).
  - So under `SEQUENTIAL_PADES` with two signers in one all-required step (the case ADR-0034 D4 names, `docs/adr/ADR-0034-sequential-incremental-pades.md:37`): if B is admitted before A's act reads the envelope, A's fill revision draws B's values, and A's `/Lock` and `FieldMDP` list B's fields. B's own signature then fills nothing and carries no lock.
  - A validator reading the PDF attributes B's values to A's signed revision.
  - Partly homed: ADR-0085 §2.1 ("every value recorded in the envelope read") and TASK-067 §4 #3 (`docs/tasks/TASK-067-…md:201-205`) imply it. But §2.8 (`docs/adr/ADR-0085-…md:111-115`) names only the approver as a party locked by someone else's signature.
  - No test builds a parallel step. The live sequential cases are all one recipient per step, and the single-seal case is `SINGLE_SEAL`.
  - Either state it in ADR-0085 §2.8, or restrict a signer's fill to the acting recipient plus owners who have no signature of their own (approvers). The choice is the owner's.
- **[placement · low · 50] A placement off the page is no longer refused.**
  - `PageBox::place` does not bounds-check (`Domain/Pdf/Form/PageBox.php:87-97`). On a drawn document DSS never sees coordinates, so a box outside the CropBox is signed with an invisible mark where DSS used to refuse it.
  - The signature is still valid. Only the visible mark is lost. This belongs in BL-366, as the closing review already notes.
- **[availability · low · 40] Odd page geometry blocks the act instead of signing without drawing.**
  - A `/Rotate` that is not a multiple of 90, or a CropBox disjoint from the MediaBox, throws `PageGeometryException` (`PageBox.php:49-56`). The adapter maps it to a form-engine failure, which blocks the act on every retry.
  - ADR-0085 §2.6's "never preparable" carve-out lists only foreign signature, XFA and unreadable. This is not an eIDAS defect: nothing is signed wrongly. But such a document would end in the failure transport.
- **[check-depth · low · 25] `DrawnRevisionCheck` does not confirm that values drawn earlier are unchanged in the summary.**
  - It checks the prefix, the fills and the locks only (`DrawnRevisionCheck.php:305-344`).
  - An incremental update could override an earlier field object without breaking the prefix. Earlier `/ByteRange`s would stay intact, but the value shown would change. The only guard is the script's `/V`-present refusal (`form_engine.py:544`).
  - Comparing `state->fields` (non-null) against `drawn->fields` would close it in PHP.
- **[log-wording · info · 30] An in-flight document already signed through DSS's own `Signature1` before this shipped is logged as `FOREIGN_SIGNATURE`.**
  - Only `f5s_` signature fields count as prepared (`form_engine.py:285`; `FormState.php:37-50`).
  - The behaviour is correct (ADR-0085 §3.3: signed without drawing), but the reason names "someone else" for our own signature.

## Not applicable in this repo (not a green)
- **TSA / timestamping:** `requiresTsa()` has no callers and no level at or above B-T is produced. Deferred in ADR-0023, BL-4.
- **LTV, CRL/OCSP:** there is no revocation code in `src/`.
- **LOTL/TSL trust lists:** they live in the DSS container, which this skill does not audit.
- **Per-user certificate, policy OID:** the seal is resolved by alias from the DSS keystore. `SignRequest` still says so (`Domain/Pdf/Request/SignRequest.php:15-19`).
- **Dev keystore chain:** it is self-signed, so the result is INDETERMINATE / NO_CERTIFICATE_CHAIN_FOUND. That is the environment, not this diff.
- **Enforcement of FieldMDP by a validator:** neither DSS 6.4 nor 6.5.1 enforces it (ADR-0085 §3.2). Only Adobe does, and that was seen in the spike only.

## Decisions with no in-repo home
- Whether a signer's signature may carry and lock a co-step signer's admitted-but-unsigned values (finding 1) → `decision-homeless` (partial: implied by ADR-0085 §2.1 and TASK-067 §4 #3, but not stated in §2.8).
