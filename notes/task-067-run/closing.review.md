# Closing review — TASK-067

Range: `f0199eb8..65005c60` (merge-base with develop; the task's 45 non-merge commits). Slice 15 (28bbfa00,
740593e5, 99755780, 65005c60) reviewed here. No tests run (full suite on the lane at review time).

## Verdict: changes

Code, protocol and chain behaviour are consistent across slices. The open items are records and prose
(rule 1), one mis-cited criterion, and one security hardening.

## Findings

1. **(90, check 5 rule 1) `docs/BACKLOG.md:301` BL-269 and `:383` BL-366 are stale in present tense.**
   - BL-269 still says "Recorded field values will reach no document" and is still `Open`.
   - BL-366 still says "DSS then refuses the box when it seals". On a drawn document the widget's `/Rect` is now ours (`PageBox`), so DSS never sees coordinates and does not refuse an off-page box.
   - BL-366 (4), the CropBox shift, is fixed for envelope documents.
   - BL-366 still says "BL-269 depends on (1) and (4)", which is no longer true.
   - Fix (task-close's commit, since the record's §6 gives BACKLOG rows to task-close):
     - close BL-269, naming TASK-067 and ADR-0085;
     - in BL-366, mark (4) done for envelope documents and remaining only for a document signed without drawing (ADR-0085 §2.6);
     - say that an off-page placement on a drawn document is now signed where `PageBox` puts it (it may fall outside the CropBox) instead of refused by DSS;
     - drop the "BL-269 depends on" clause.
2. **(85, rule 1) Record header is stale.**
   - `docs/tasks/TASK-067-…md:7` says Status "Not started".
   - `:12` says Decision record "No ADR yet".
   - Fix: task-close sets Status. The Decision record cell should name ADR-0085, Accepted 2026-10-21.
3. **(85, rule 1) `CLAUDE.md` § Stack (symlink to `ai/f5sign-backend/CLAUDE.md`) does not mention pyHanko.**
   - It names Typst and its Dockerfile stage, but not pyHanko 0.29.0, `/opt/pyhanko`, python3 in dev and runtime, or `assets/signature-execution/form_engine.py`.
   - The SignatureExecution bullet under Current state does not mention the form engine either.
   - Fix (docs-sync, in the root repo, not on this branch):
     - add a Stack bullet: pyHanko 0.29.0, in a hash-pinned venv at `/opt/pyhanko` built by the Dockerfile's `pyhanko` stage, run as a process by `PyHankoFormEngine` over `form_engine.py`, draws recorded values as form fields before each signature (ADR-0085);
     - add "the form engine and fill revision (ADR-0085)" to the SignatureExecution bullet.
4. **(75, rule 1) `src/F5Sign/SignatureExecution/Application/Service/DocumentSigner.php:92`, `sign()` docblock.**
   - It opens with "one incremental PAdES revision layered over the signatures of everyone before them".
   - Four lines down, the same block (edited on this branch) says an act is a fill revision plus one signature revision per mark.
   - Fix: "A recipient's signing act: a fill revision, then one incremental PAdES signature per mark (one invisible when none), layered over the signatures of everyone before them".
5. **(80, check 1) `tests/F5Sign/SignatureExecution/Integration/FieldValuesDrawnSequentialTest.php:338` cites the wrong criterion.**
   - `a_viewer_fills_nothing` cites `AC-7c`.
   - The record's Notes on AC-7 order the members as REVIEWER = AC-7c, VIEWER = AC-7d.
   - Fix: change the line to `@criterion TASK-067 AC-7d`.
6. **(70, security, always reported) Recorded values and PDF bytes sit in new stack-frame arguments (the BL-278 class).**
   - `FormEngineFailedException` is thrown from `PyHankoFormEngine::run(array $request)`, with every value and the PDF in that array.
   - It is also thrown from `DrawnRevisionCheck::verify(string $input, FormRevision $revision, DrawnRevision $drawn)`.
   - `DocumentSigner` rethrows it, so the transport or Sentry records the trace with its arguments. Production does not set `zend.exception_ignore_args`, per BL-278.
   - AC-18 covers the message and the log line, not the frames.
   - Fix: mark with `#[\SensitiveParameter]`, as `SignatureImage` already does:
     - `PyHankoFormEngine::run` `$request`;
     - `PyHankoFormEngine::inspect` and `::apply` `$pdf`, and `apply`'s `$revision`;
     - `DrawnRevisionCheck::verify` `$input`, `$revision` and `$drawn`;
     - `FieldTextLayout::layOut` `$text`.
   - Alternatively, add these frames to BL-278's row in task-close.

## Checked and consistent

- **§5 coverage.** Every live id and sub-id is cited by at least one test, including AC-16a…c and AC-20. Each cited test asserts its row (spot-read: AC-2a/b/c, 5, 7a…g, 9a/b, 10, 11, 12, 13, 14a/b, 16a…c, 17a…d, 19, 20).
  - AC-13: `SequentialPadesLoopTest` now counts revisions exactly (+2, then +2+2).
  - AC-7: the role case iterates `Role::cases()` against a hard-coded SIGNER/APPROVER expectation that does not read `fillsFields()`.
- **Constraints § Landed so far matches the code.**
  - Signatures: `FormRevisionPlanner::plan(...)`, `PlannedRevision`, `DrawnRevisionCheck::verify`, `PdfFormEngineInterface::inspect/apply`, `SignRequest::$fieldId` as the last parameter, `Recipient::recordAdmittedReservations`, and the four `FieldDrawingLog` methods.
  - `NotPreparableReason` has FOREIGN_SIGNATURE, XFA and UNREADABLE, and is used consistently in DocumentSigner, the log, its Psr adapter and the tests.
  - Visible payload: `{fieldId, width, height, rotation: AUTOMATIC}`. Invisible payload: `imageParameters {fieldParameters {fieldId}}` only.
- **Protocol.** The keys between `PyHankoFormEngine` and `form_engine.py` match the constraints:
  - `inspect`: pages/mediaBox/cropBox/rotate, xfa, signatures, fields, signatureFields;
  - `apply`: create/fill/signatureFields, then the summary's fields and signatureFields.lock (null when absent);
  - exit codes 0–5 map through `FormEngineFailure::ofExitCode`;
  - the version is checked against the configured `0.29.0` after the exit-code check.
- **Security.**
  - argv carries only the interpreter, script, operation and the memory limit.
  - The environment is emptied by naming every inherited variable `false`.
  - The request goes on stdin. Stderr is never read, and the script redirects Python's stderr to devnull.
  - No temp file is written.
  - Exception messages carry the kind, exit code or check name only. Log lines carry ids, reason, kind and exit code only.
  - Drawn text is cp1252-encoded, and `\`, `(` and `)` are escaped in the literal (`literal()`). Field names and `/V` go through `TextStringObject`.
  - Our own `/F5SHelv` WinAnsi font is used, never a foreign `/Helv`.
- **ADR-0034 chain.**
  - One artifact per act per document. Custody is opened transient before the CAS append and written after it, in the order kept from before.
  - Inspect's PDF_UNREADABLE is the only failure that degrades to signing without drawing. Every other engine failure, including `outputMismatch`, is logged and rethrown before custody or append.
  - On a chain-conflict retry, the planner sees the other signer's drawn fields: it creates nothing, refills nothing (the script also refuses a field that has a `/V`), and adds a new signature field.
- **Records.**
  - ADR-0085 is Accepted. Every test method and file it names in §5 and §6 exists.
  - `docs/adr/README.md` has the index row, five graph edges and the crosswalk row. ADR-0023 and ADR-0034 carry the amendment.
  - Living docs updated: SE domain model banner and crosswalk, envelope model, ddd README and LIVE_SCHEMA.
- **Sweep.** `rg` over src, tests, migrations, docs, config and CLAUDE.md for each `plan.md § Sweep terms` entry and each losing alternative found no other stale present-tense claim:
  - "byte-for-byte", "one new revision", `%%EOF + 1`, "Maps 1:1", "measures from the MediaBox", "only checked", "recorded at completion";
  - `bool $xfa`, `/Helv`, `Signature1`, "fieldId alone", "AUTOMATIC", `isFillable` in SE, strict.
  - Every remaining hit is historical, annotated, or correct.
- **Scope and leftovers.**
  - Nothing touched `deptrac.yaml`, `phpstan*`, `Kernel/`, `Foundation/` or `migrations/`.
  - Every changed file belongs to a slice's Files, to slice 15's reported sweep additions, or to a recorded deviation (`echoes-request`, `pdf-form-reader.py`, `FieldValuesAtTheCommitHttpTest`).
  - `grep -niE 'claude|generated by|ai-generated'` over the diff: empty. Commit messages: no trailers.
  - No TODO or var_dump. The two `print(` hits are protocol output of test helper scripts.

## Low confidence

- (65) `FieldValuesDeliveryBarTest::the_envelope_signs_and_seals_with_every_signature_intact` writes sealed PDFs to `var/delivery-bar/` and writes to STDERR on every suite run. The owner's Adobe check is done. Consider gating it behind an env variable, or dropping it.
- (60) `form_engine.py:357`, the helper `def name(value)` inside `apply()`, is never called. It is dead code.
- (55) Published OA strings `nelmio_api_doc.yaml:796` (`recipients[].reservations`, "captured at signing") and `:320` (`has_reservations`, "any recipient signed with…"):
  - The text is now on the envelope JSON from the admission. That includes a recipient whose signature or completion never lands, where it used to appear only at completion.
  - It is not false, but it is a visible behaviour change with no frontend handoff. That belongs to contract-check.
- (50) An off-page placement on a drawn document no longer fails at DSS. It is signed with its widget outside the CropBox, so the mark is invisible. This is a behaviour change worth stating in BL-366 (see finding 1).
- (45) AC-16a/b (foreign signature, XFA) have no real-script end-to-end case. The pieces are covered:
  - the script's `inspect_sees_a_foreign_signature_and_an_xfa_form`, which cites only the grouped `AC-16`;
  - `FormStateTest`;
  - `DocumentSignerTest` with fakes.
  - Citing `AC-16a AC-16b` on the script test would make the trace exact.
- (40) A page whose CropBox does not intersect its MediaBox, or a `/Rotate` that is not a multiple of 90, makes `PageBox::of` throw. The adapter maps that to MALFORMED_OUTPUT, which blocks the act on every retry, where DSS used to sign such a document.
- (40) `FormEngineFailedException::LOCK`'s docblock is narrower than the check, which also refuses an absent lock and a present-but-unrequested one. `FormEngineFailure::REQUEST_INVALID`'s docblock says "the engine exited 2", but PHP also uses it for a `json_encode` failure, with no exit code.
- (40) A redelivery over the act's own tip runs the engine again and appends a new unlocked signature field before the append converges. This is a deviation recorded in slice 11.
- (35) `sys.stderr = open(os.devnull)` does not redirect fd 2 for native code. The adapter never reads stderr, so this is harmless.
- (30) `docs/ddd/signature-execution-domain-model.md:97, :224, :445` still name the external `pdf-tools` for AcroForm fill. These lines sit under the banner "tactical sections reconciled only in the crosswalk", and the crosswalk says "Realized otherwise".
- (30) ADR-0034:45 keeps the bold "`SINGLE_SEAL` is byte-for-byte unchanged", followed by the ADR-0085 amendment. README graph line 521 quotes it as ADR-0034's decision, which is correct as a quote.
- (25) The `DocumentRecord` docblock says "each signature is an incremental revision". The trail's "revisions" are the signing acts' artifacts, so the sentence still holds loosely.
- (25) `DrawnRevisionCheck` does not refuse extra fields or signature fields in the summary (open from slice 10).

## Not checked

- No suite, gate or Infection run. The lane was busy, as instructed.
- pyHanko 0.29.0 internals beyond what the script's code shows. arm64 hashes.
- That Adobe enforces the lock on S-1's PDFs. The owner's manual check covered placement only. The lock-tamper check was observed in the spike, not on these files.
- Whether Sentry is configured to send frame arguments in production. Finding 6 takes BL-278's statement as true.
