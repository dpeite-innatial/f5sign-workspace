# Plan — TASK-067

Record: `docs/tasks/TASK-067-recorded-field-values-are-drawn-into-the-signed-pdf.md` (857d896f).
Decision record: ADR-0085, drafted `Proposed`, **uncommitted** in the worktree
(`docs/adr/ADR-0085-recorded-values-are-form-fields-each-signature-locks.md`). No slice runs until the
owner accepts it; the orchestrator then commits it.

## External precondition (not a slice: f5sign-infra, its own branch and PR)
The `wt-backend` lane must build `php-fpm-wt` from THIS worktree's `Dockerfile` under an image tag
named by variable (defaults unchanged). Slices that need `/opt/pyhanko` in the lane: **07, 08, 12, 13,
14**, and from slice **11** on the full Integration suite (everything signing through
`DocumentSigner` runs the real script). Slices **01, 02, 03, 04, 06, 09, 10** need no pyHanko; **05**
builds and measures images with plain `docker build`, outside the lane.

## Criteria → slices
| Criterion | Slices | Harness |
|---|---|---|
| AC-1 | 07 (09 create rules) | Integration, real script |
| AC-2a / b / c | 01, 11, 12 / 11, 12 / 11, 13 | Unit + Application + Integration live DSS |
| AC-3a, b | 03, 08 | Unit (golden) + Integration real script |
| AC-3c, d, e | 08 (09 for d's value) | Integration real script, Application |
| AC-4a, b | 01, 02, 07, 08, 14 | Unit (PageBox) + Integration live DSS |
| AC-5 | 05, 06, 15 | image build + Integration (fakes) |
| AC-6a / b / c | 12 / 12 / 13 (14 again) | Integration live DSS (DiagnosticData via `ReadsFieldLocks`) |
| AC-7a…g | 09 (all seven), 12 (a, b, c) | Application + Integration |
| AC-8 | 09 | Application |
| AC-9a / b | 11, 12 / 01, 11 | Application + Integration live DSS |
| AC-10 | 06, 11 | Integration (fakes) + Application |
| AC-11 | 08, 09 | Integration real script + Application |
| AC-12 | 06 | Unit + Integration (fakes) |
| AC-13 | 12 (count), 14 (trail) | Integration |
| AC-14a, b | 11, 13 | Application + Integration live DSS |
| AC-15 | 03, 08, 09 | Unit + Integration + Application |
| AC-16 | 06, 07, 09, 11 | Unit + Integration + Application |
| AC-17a…d | 10 (all four), 07/08 (summary) | Application + Integration |
| AC-18 | 06, 09, 10, 11 | Integration (fakes) + Unit + Application |
| AC-19 | 06 (timeout), 07 (memory), 11 | Integration |
| AC-20 | 04, 09, 12 | Unit + Integration + Application + live |
| S-1 | 14 (+ owner's Adobe check on `var/task-runner/TASK-067/s1-sealed.pdf`) | Integration live DSS |

## Harness per property
| Property | Tier | Does the harness reach it? |
|---|---|---|
| DSS signs into our field, keeps our `/Rect`, writes FieldMDP | Integration, live `eu-dss` | Yes (01, 12–14). Orientation (upright mark) is NOT asserted: no renderer in the image; it rests on the probe (RESULTS.md) + the unit pin that `rotation: AUTOMATIC` is sent |
| Adobe enforces the lock | Manual (owner) | No automated validator does (DSS 6.4/6.5.1 do not) — stated, not claimed |
| No value on argv / env empty / stderr never surfaced | Integration with fake executables | Yes: the fake echoes argv+env; a fake leaks a secret on stderr |
| Memory cap | Integration, real script | Yes: tiny `RLIMIT_AS` must fail (07) |
| Prefix preserved, summary matches | Application (10) + Integration (07/08) | Yes; the check is in `src/F5Sign` so Infection sees it |
| Planner decisions (roles, occurrences, reservations, already drawn) | Application, fixtures that DISAGREE (value on a VIEWER's field; value ≠ reservations; hidden occurrence) | Yes |
| Reservations written at admission, persisted | Unit + Integration (DAMA, one connection) | Yes for the write; the lock order is unchanged (same `saveAdmission` path), so no second-connection probe is needed |
| Python script logic | Integration, real script only | Infection cannot see it (not PHP); its guards are pinned by the integration tests' sabotage |
| Redelivery/chain-conflict not refilling | Application (09) + script refusal (08) | `async_events` is in-memory, so redelivery is simulated by re-running on a drawn tip, not by the transport |

## Slices
| # | Title | Tier | Covers | Depends on | Wave |
|---|---|---|---|---|---|
| 01 | DSS signs into a field of ours (SignRequest.fieldId, mapper, live pin) | critical | AC-2, AC-9b, AC-4 (DSS) | — | 1 |
| 02 | PageBox: displayed placement → user-space rect | standard | AC-4a, AC-4b | — | 1 |
| 03 | FieldTextLayout: signer's rules v1 + the 7 pt cut | standard | AC-3a, AC-3b, AC-15 | — | 1 |
| 04 | Reservations recorded at the admission (Envelope) | critical | AC-20 | — | 1 |
| 05 | Dockerfile: pyHanko 0.29.0 venv, hash-pinned; W1 measured | critical | AC-5 | — | 1 |
| 06 | Form engine port, DTOs, adapter with fakes, wiring | critical | AC-5, AC-12, AC-16, AC-18, AC-19 | 02 | 2 |
| 07 | Script: inspect, preparation, locked signature fields, rlimit | critical | AC-1, AC-16, AC-17, AC-19 | 05, 06 (+infra) | 3 |
| 09 | FormRevisionPlanner + FieldDrawingLog | critical | AC-7, AC-8, AC-11, AC-15, AC-20, AC-3d | 02, 03, 06 | 3 |
| 10 | DrawnRevisionCheck | critical | AC-17a…d | 06 | 3 |
| 08 | Script: fill per type, never twice | critical | AC-3, AC-4, AC-11, AC-15 | 03, 07 (+infra) | 4 |
| 11 | DocumentSigner draws, then signs into our field | critical | AC-2, AC-9, AC-10, AC-14, AC-16, AC-18 | 01, 06, 09, 10 | 4 |
| 12 | Live SEQUENTIAL_PADES: locks per signature, exact revisions | critical | AC-2a/b, AC-6a/b, AC-7a/b/c, AC-9a, AC-13, AC-20 | 04, 08, 11 (+infra) | 5 |
| 13 | Live SINGLE_SEAL agreed and voided | critical | AC-2c, AC-6c, AC-14a/b | 08, 11 (+infra) | 5 |
| 14 | Delivery bar S-1 + trail | critical | S-1, AC-4, AC-13 | 08, 11 (+infra) | 5 |
| 15 | Records and sweep | critical | AC-5 (records), §3 #5 | 01–14, ADR accepted | 6 |

File overlaps resolved by waves: `services.yaml` (06 w2, 09 w3); `form_engine.py` (07 w3, 08 w4);
`PyHankoFormScriptTest` (07, 08); `FormEngineFailedException` (06 w2, 10 w3). Within a wave, Files are disjoint.

## Sweep terms
- "one new revision" / "%%EOF + 1" per act or per seal in any test or docblock — now fill + signature(s) per act (slice 16 fixed AnnulmentSealTest; census the rest).
- src/F5Sign/Envelope/Contract/View/DocumentView.php constructor docblock: "leaves SINGLE_SEAL byte-for-byte unchanged" — retired by slice 11.
- ADR-0034 (Decision 5 line) and ADR-0023 still say SINGLE_SEAL is unchanged byte-for-byte — retired by slice 11; amend with ADR-0085's Relates-to (slice 15 / docs-sync).
- `recordAdmittedReservations` docblock says the signature "locks" the RESERVATIONS field — true only once slices 11–14 land; closing review checks it at the tip.
- `SignatureImage` class docblock "Maps 1:1 to EU DSS `SignatureImageParameters.fieldParameters`" — false when `fieldId` is sent (slice 01).
- `rotation: AUTOMATIC` — ⚑ **NOT retired** (the record's "Concepts re-cut" is wrong; the probe measured
  it is needed beside `fieldId`). What is retired: DSS mapping our coordinates for envelope documents.
- "one incremental revision per recipient per document" (ADR-0034) → fill revision + signatures, one artifact.
- "the mark's placement being DSS's to map", "DSS measures from the MediaBox … nothing corrects it" (`SignatureImage`, `FieldPlacement`).
- "`SINGLE_SEAL` is unchanged byte-for-byte" (`DocumentSigner`, ADR-0034 Decision 5).
- "a recipient's reservations are recorded at their completion" / "`$reservations` is only checked" (TASK-016 → admission).
- Losing alternatives: DSS creating its own signature field; `fieldId` alone on a rotated page; `FieldType::isFillable()` as the drawn set; laying out text in the script.
- `BL-269`, `BL-366` (tense).

## Decisions made
- **The script executes, PHP decides** (ADR-0085 §2.5): two commands (`inspect`, `apply`), the protocol in `constraints.md`; layout, conversion, preparability, already-drawn and locks are PHP (hermetic tiers, Infection-visible).
- **`rotation: AUTOMATIC` stays beside `fieldId`** for a visible mark; the invisible signature sends `imageParameters {fieldParameters {fieldId}}` only (probe 2026-10-21, coordinator's report; RESULTS.md).
- **An unpreparable document** (foreign signature or XFA) takes today's path unchanged (no `fieldId`, DSS coordinates + AUTOMATIC), with an `error` line: §4 #2 says "signed without drawing" and that path is the one measured for it.
- **All signature fields of one act carry the same `/Lock`**; none when nothing was filled (ADR-0085 §2.8).
- **Signature field names are random** (`f5s_sig_<16 hex>`): a redelivered seal or act re-runs over its own earlier tip, and a deterministic name would collide before the append's convergence refuses it.
- **"Drawn" = `/V` present**; a checkbox is created with `/AS /Off` and no `/V`. No borders on any appearance (the document's artwork carries its boxes).
- **DROPDOWN** (owner, 2026-10-21, after the plan): an `/Ch` combo whose `/Opt` are `[value label]` pairs; `/V` = the chosen value, the appearance draws its label (a value matching no choice draws as itself). Slices 07, 08, 09, constraints.md and the record were updated.
- **Engine failure is an exception, not a `Result`** (unlike `TypstTrailRenderer`): the caller is `DocumentSigner`, whose DSS failures already throw into the transport's retry.
- **Logging** through an `Application/Port` (`FieldDrawingLog`, the Session `ReportedEvidenceDropLog` pattern): Application cannot depend on Psr.
- **pyHanko without extras**, every transitive dependency hash-pinned, wheels only (same rationale as Typst's checksum).
- **No probe slice of its own**: the coordinator's throwaway probe (2026-10-21) already measured AC-9b, PNG via `fieldId`, `/Rotate` and CropBox; slice 01 is first and pins it as a permanent live test, with the record's stop clause (DSS refuses ⇒ BLOCKED).

## Deviations
- 03: invalid UTF-8 normalises to an empty string and draws nothing (reviewer, low confidence); values reach drawing from the DB, which holds validated UTF-8. Cut maximality is not pinned by a test.
- 02: test and class written together (no separate red run; both guards sabotaged red afterwards). Unpinned: `<=` boundary of the zero-area guard, rotate 180 with offset CropBox, NaN/INF inputs (reviewer, low confidence).
- 04: RecipientCompleted keeps the completion's reservations on its payload while the row keeps the admitted text; both come from SessionCompleted today, so they agree (orchestrator ruling, not changed: a Contract/Event payload change is out of scope).
- 04: FieldValueRecordingTest was red on today's clock (pre-existing date bomb); resolved by merging develop (715f6ea0), which brought PinsTheDatabaseClock — green after the merge.
- 01: upright drawing on a rotated page is pinned only by the unit payload assertion (`rotation: AUTOMATIC` beside `fieldId`) and the probe's rendered images, not by the live test.
- 05: round-1 fix was comment-only (two lines, no instruction changed); closed by the orchestrator reading the diff instead of a second review round. Low confidence left: apk python3 unpinned across three stages.
- 01: round-1 fixes were prose-only (two docblock/comment sentences); closed by the orchestrator reading the diff. Low confidence left: lastRect() assumes DSS writes our widget last.
- 02: PHPStan follow-up 1fc8ab73 (a phpstan-ignore/annotation on the deliberately malformed-box test), checked by orchestrator.
- 04: 843a9507 corrected a stale comment in tests/F5Sign/Session/Acceptance/FieldValuesAtTheCommitHttpTest.php (outside the slice's files; acknowledged, rule-1 fix).
- 04: a MockSign completion used to blank recipient.reservations; it now keeps the admitted text (docs-sync to note).
- 06: added fixture tests/Fixtures/pyhanko-fakes/echoes-request beyond the slice's Files (kept: only test of the apply request's encoding). FormEngineFailure is the only plain enum in a ValueObject/ dir (slice's placement).
- 10: extra entries in the engine's summary (fields or signature fields not asked for) are not refused; the slice did not ask for it (reviewer, 30). LOCK constant docblock narrower than the check (40).
- 09: a mark on a page the PDF lacks also throws fieldOffThePage (message says "a field"); not pinned by a test. `a_checkbox_is_filled_only_from_a_bool` cites AC-1 instead of AC-3c — fix in slice 15's sweep.
- 07 (orchestrator ruling): `/Lock` becomes an INDIRECT object (ISO 32000 Table 232 "shall be an indirect reference"); done in slice 08 (same file); slice 12's live test confirms DSS still writes FieldMDP.
- 07 (orchestrator ruling, for the owner to see): the script reads PDFs leniently (pyHanko strict=False), still writing one incremental update. With strict=True a slightly malformed PDF that DSS signs today would fail every act as PDF_UNREADABLE (§4 #6 blocks the act) and never be signed; §4 #2's sign-without-drawing exception only names a foreign signature or XFA. Done in slice 08 (same file).
- 07: TZ cannot be set (no zoneinfo; tzlocal raises) — warnings ignored, stderr to /dev/null. Script writes /AcroForm /DA when absent; pyHanko adds /Info and /ID. Memory: at <=48 MiB cryptography fails to import (exit 1, not 4); default cap 768 MiB unaffected; 10-page prepare VmPeak 67,964 kB.
- 11: DocumentSigner's `$fieldIds[$k] ?? null` would sign without our field if the planner returned fewer names than marks (unreachable today) — harden to a thrown invariant in the closing slice. A redelivery now converges only if the engine also succeeds on the act's own tip. An envelope signed before deploy logs documentNotPreparable worded as foreign-signed (signing as before is correct).
- 08: implementer's choices accepted — kind mismatch exits 5; duplicate fill name, checkbox with appearances, non-positive size exit 2. Lenient write copies the input's wrong startxref into /Prev (pyHanko's incremental writer), so such an output stays unreadable to a strict reader; slice 14 runs it through DSS end to end.
- 08 (orchestrator ruling): appearances use our own /F5SHelv (Type1 Helvetica, WinAnsiEncoding) in /DR, never a foreign /Helv, which Acrobat forms often give a /Differences map.
- 16 (fix slice): tests/Fixtures/pdf/sample.pdf was hand-written with wrong offsets (startxref 277 vs 320, wrong xref entries, /Length 44 vs 52); DSS reconstructed it, pyHanko cannot even leniently, so after slice 11 every act on it failed PDF_UNREADABLE. Rewritten well-formed; the original kept as tests/Fixtures/pdf/broken-xref.pdf for the owner's pending decision on unreadable PDFs in production. AnnulmentSealTest's helper now counts two revisions per seal (fill + seal).
- 13: recipients declared visible:true (send refuses a recipient shown no document); values read in the fill revision under the seal's ByteRange (AC-6). Sabotage windows on shared src: 15:11:20–15:11:51 and 15:12:05–15:12:44 UTC+? (local) — slice 12/14 runs inside them are suspect.
- 17 (owner decision 2026-10-21): inspect's PDF_UNREADABLE takes the not-preparable branch (sign without drawing, error log with reason); record §4 #2/AC-16 (AC-16a…c) and ADR-0085 §2.6 amended by the orchestrator.
- 12: tests/Fixtures/pdf-form-reader.py (outside the slice's Files, authorised by the orchestrator, own commit 9c8b71d5) no longer descends into a /Sig field's /V. AC-7c's VIEWER fixture is a direct SQL write (no API path produces it); the seven roles are discriminated at the Application tier. Third sabotage (separate fill artifact) not run: covered by the chain asserts (reviewer).
- 14: values asserted at A's and C's byteRangeEnd and in the full sealed bytes on both documents (round 1); the lenient-PDF live case pins the engine's lenient read end to end, no criterion id. Sealed PDFs written to var/delivery-bar/ in the lane and copied to var/task-runner/TASK-067/s1-sealed*.pdf.
- 17 (orchestrator ruling): the "Also" invariant (throw when the planner returns fewer signature-field names than marks) is dropped: FormRevisionPlanner is concrete and always returns one name per mark (pinned by FormRevisionPlannerTest), so the throw would be unreachable code and an escaped mutant; an interface + fake only for it is not worth it. DocumentSigner's `$fieldIds[$k] ?? null` stays.
- 18: mark tests compare /Rect and /BBox numerically; its BBox check surfaced a real defect (slice 19). SignatureModesHttpTest's box comparison was sabotaged only through slice 19's payload sabotage (reviewer, low).
- 17: inspect reports PDF_UNREADABLE also for a page-tree cycle or a page with no /MediaBox, so those documents are signed without drawing too (consistent with the owner's ruling; the record names the broken-xref case). NotPreparableReason lives in Application/Port beside FieldDrawingLog.
- Manual (owner, 2026-10-21): S-1's sealed PDFs (rotated page, offset CropBox) opened in Adobe Reader and look right. The record's second manual check — a copy with one locked value changed after its signature shows that signature invalid — was not repeated on these files; it was observed by the owner in the 2026-10-21 spike.
- Integrator (factor5 dashboard, 2026-10-21): stored recipients[].reservations the first time it appeared to open an incident; after §3 #6 that could capture a PENDING recipient's text. Adjusted on their side to read it only once the recipient is SIGNED. No backend change.
