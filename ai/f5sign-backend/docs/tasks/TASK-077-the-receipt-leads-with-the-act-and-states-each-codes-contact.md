# TASK-077 — The receipt leads with how the act ended, prints Spanish time, and states each code's contact and the signature image's digest

<!-- OFFREPO: the request came from the owner's session on 2026-10-28/29, comparing the receipt with a third-party
trust provider's contract certificate (a PDF the owner holds). Every fact taken from it is restated in §1; nothing
here depends on reading it.
OFFREPO: the `wt-backend` lane named in §5 and §7 is a target of the sibling `f5sign-infra` repo's Makefile
(`make -C ../f5sign-infra wt-backend… src=<worktree>`): it runs this worktree's own tree in containers of its own
(database, storage, broker), so a run there validates this branch and not the main checkout. -->

| Field | Value |
|-------|-------|
| **Status** | **Done — integrated in `develop` on 2026-10-29** from `feat/receipt-redesign` (merge `81e1a0c7`; tip `1579ffb0` at the last full run, later commits docs only). Full suite green under the `wt-backend` lane (this worktree): 9817 tests, one failure attributed to the already-recorded flake [BL-471](../BACKLOG.md) (green 5/5 filtered; the branch touches neither Notification nor Envelope); lint, deptrac and PHPStan green. Infection on the changed lines: see §7. Pending review. |
| **Type** | **Forward build** in Evidence & Audit: the receipt's template, and two members added to its model and its published JSON. No migration, no route, no event. |
| **Why** | The receipt reads as a technical dump: the outcome of the act sits in a table row halfway down, every time is in UTC for a Spanish reader, and log positions, revision sequences and template hashes share the body with what a recipient needs. It also leaves out two things the trail already knows about the same act: which contact each one-time code went to, and the digest of the signature image the recipient committed. |
| **Builds on** | [TASK-047](TASK-047-per-signer-evidence-document.md) (the receipt, its model, assembler, renderer and tests), [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (what a receipt states), [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.1, §2.5, §2.6 (wording in the template; the contact and image readings; masking), [ADR-0084](../adr/ADR-0084-a-correction-reaches-only-the-contact-it-changed.md) §2.9 (a correction unstates only the kind it changed). |
| **Scope** | Evidence & Audit only. ⛔ **Not** the per-document certificate (ADR-0094, `Proposed`, drafted on `feat/document-certificate` and not yet on `develop`; its own task), not the receipt's delivery by email or SMS ([BL-280](../BACKLOG.md)), not a route or a status code, not the trail's template. |
| **Decision record** | [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) (`Accepted`). The change adds two members to what §2.3 enumerates, both minimised as ADR-0072 §2.6 minimises them and both already stated by the trail, so it extends the receipt within that decision: §2.3's enumeration is updated (AC-14), no new ADR. |
| **Sibling** | None. |

---

## 1. Why this task exists

Owner decisions, 2026-10-28/29, after comparing the receipt with a third-party trust provider's contract certificate.
That certificate opens with a coloured band stating the transaction's state and its date, prints its times in
Spanish local time with the zone named, repeats the transaction's identifier and state at the top of every page,
keeps document digests as plain lines under each document's name, and puts its technical verification references
in a separate block. The owner asked to take ideas from it, not to clone it.

- **Lead with the outcome.** Owner agreed to "banda grande de estado (Firmado / Aprobado / Rechazado) con la hora".
- **Local time.** Owner agreed to "horas en hora de Madrid con su zona; el JSON se queda en UTC".
- **Less in the body.** Owner agreed to drop the step and the `Accept-Language` from the page, collapse the device
  report into one line, and move identifiers, log positions, revisions, the chain and the generation to a technical
  annex.
- **What the trail knows and the receipt does not.** Owner agreed to state the masked contact each code went to and
  the digest of the signature image.
- **No version bump.** Neither JSON form is in production, so `f5sign.receipt/1` is edited in place (owner's standing
  decision for the evidence schemas).
- **Dropped: the conservation date.** Agreed at first ("se conserva hasta …"), then dropped on 2026-10-29: when a
  receipt is issued its envelope's ceiling is still provisional, and it is final only at `COMPLETED` (ADR-0073
  §2.16), so the receipt cannot state it truthfully. §6 #1.

## 2. What already exists (reuse, do not rebuild)

- **The model**, `src/F5Sign/EvidenceAudit/Domain/Receipt/`: `Receipt` (`SCHEMA = 'f5sign.receipt/1'`), `ReceiptEnvelope`,
  `ReceiptRecipient` (`step`, `role`, `authentication`, `personal`), `ReceiptPersonal` (implements `Pii`: name, IP,
  user agent, `Accept-Language`, asserted identity, browser report), `ReceiptAct` (kind, fact, reason, reservation),
  `ReceiptDocument`, `ReceiptRevision`, `ReceiptBoundary`, `ReceiptFact`, `ActKind`, `ReceiptLimitationCode`.
- **The published form**, `ReceiptJson::encode`, top-level keys `schema`, `envelope`, `recipient`, `act`,
  `documents`, `boundary`, `chain`, `limitations`, `generation`; times through `TrailJson::time` (UTC). Encodings
  shared with the trail are public on `TrailJson` and say so in their docblocks (`reservation`, and others).
- **The assembler**, `ReceiptAssembler::assemble`, reads the stream up to the act and calls `TrailAssembler`'s public
  static readings (`authentication`, `observed`, `assertion`, `reservation`, `certificate`, `fact`, `present`,
  `browserReport`), so both documents state a value the same way. **`TrailAssembler::contacts`** (the contact each
  `OtpSent` went to, masked by `Foundation\ValueObject\MaskedContact`, `CORRECTED_AFTERWARDS` when a later
  `RecipientCorrected` changed that kind of contact) and **`TrailAssembler::markImage`** (the
  `signature_image_sha256` of the party's first `SignatureCommitted`, source `LOG`) are **private** on `develop` as of 2026-10-29.
- **The template**, `assets/evidence-audit/receipt.typ`: all wording lives there (ADR-0072 §2.1); its label groups are
  exposed as `<labels>` metadata; it prints times as `YYYY-MM-DD HH:MM:SS` and says "Todas las horas están en UTC";
  it prints the step ("Paso") and the `Accept-Language` ("Idiomas del navegador").
- **The renderer**, `TypstReceiptRenderer`: its identity is the Typst version plus the SHA-256 of `receipt.typ`, which
  every receipt records as `generation.template_hash`; it refuses a receipt naming another identity.
- **Tests**: `ReceiptJsonTest` (`the_published_form_has_exactly_these_keys`, path by path;
  `absent_values_are_null_and_times_are_utc`), `ReceiptCodesTest`, `ReceiptAssemblerTest` (24 cases cited
  `@criterion TASK-047`), `TypstReceiptRendererTest` (`the_template_labels_every_code_the_receipt_owns` reads the
  label groups with `typst eval 'query(<labels>)…'`), `ReceiptRendererWiringTest`, the acceptance tests under
  `tests/F5Sign/EvidenceAudit/Acceptance/`. The source builder `tests/F5Sign/EvidenceAudit/Testing/Builder/ReceiptSourcesBuilder.php`
  scripts each recipient's ceremony; it sends no codes and commits no image.
- **No test reads the printed text** of a receipt or trail PDF; there is no PDF text extractor in the image or in
  `composer.json` (`PdfProbe` reads embedded files and XMP only). [BL-416](../BACKLOG.md) records the same gap for
  the trail.
- **Consumers of the JSON**: none in code outside Evidence & Audit. The integrator handoff
  `docs/frontend-handoff/TASK-047-integrator-recipient-receipt.md` describes the attachment.
- **Corrections stop at the act**: `Recipient::legIsClosed()` is true from `admittedAt`, and `correctContact()`
  refuses a closed leg, so no correction can land after the act the receipt's stream ends at.

## 3. Scope

1. **The template** (`receipt.typ`):
   - a band at the top: the act as the state it left (a new label group `act-status`), its time, the recipient's
     name and role;
   - every time printed in peninsular Spanish time with its zone (`CET`/`CEST`, switched at 01:00 UTC on the last
     Sundays of March and October), and the intro saying the attachment keeps UTC;
   - from the second page, a header naming the receipt and the act's state;
   - the browser's device report as one line; the step and the `Accept-Language` not printed;
   - an annex on its own page holding the recipient and document identifiers, the log positions, the revisions, the
     discarded browser members, the closing fact, the chain and the generation;
   - the codes' contacts (with the verifications) and the signature image's digest (in the act), the digest with
     ADR-0072 §2.5's caveat that it cannot be checked against the PDF;
   - BL-469's sentence reworded so "destinatario" names one person.
2. **The model and its form**: `ReceiptPersonal` gains the contacts (a list of the trail's `ContactUse`), `ReceiptAct`
   gains the signature image's digest; `ReceiptJson` writes `recipient.personal.contacts[]` and
   `act.signature_image_sha256`; `TrailJson` and `TrailAssembler` make the shared encoding and the two readings
   public. `f5sign.receipt/1` keeps its name.
3. **Docs**: ADR-0086 §2.3's enumeration, `docs/ddd/evidence-audit-domain-model.md`, the integrator handoff, BL-469.

Concepts re-cut: receipt times printed in UTC (now local), "Paso" and "Idiomas del navegador" on the receipt page,
`TrailAssembler::contacts` and `TrailAssembler::markImage` as private, the `DECLARED_NONE` sentence of BL-469.

## 4. Key decisions

- **Peninsular time, named.** The page prints Europe/Madrid time and names the zone on each instant; the Canary
  Islands are not handled. The JSON keeps UTC with microseconds, so nothing machine-readable changes.
- **Contacts come from the trail's reading, unchanged.** The receipt's stream ends at the act, and no correction can
  land after it (§2), so the trail's rule (current row, unless a later correction changed that kind) is exact here
  too.
- **The image digest sits on the act**, not per document: one commit records one image.
- **BL-469**: the first sentence becomes "La parte declaró no formular reservas.", as the trail's sibling sentence
  reads; the second keeps "destinatario en la entrega", which then names only the consignee.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | The first page opens with a band stating the act's state, its time, and the recipient's name and role (members AC-1a…c) | owner | Integration (Typst query) | drop the band |
| AC-2 | Every printed time is peninsular Spanish time with its zone; the attached JSON keeps UTC (members AC-2a…b) | owner | Integration (Typst query) + Unit | print the UTC value |
| AC-3 | From the second page on, a header names the receipt and the act's state; the first page has none | owner | Integration (Typst query) | show the header on no page |
| AC-4 | The device report is one line; the step and the `Accept-Language` are not printed and stay in the JSON (members AC-4a…c) | owner | Integration (Typst query) + Unit | print the step |
| AC-5 | A technical annex starts on its own page and holds the identifiers, log positions, revisions, discarded members, closing fact, chain and generation, none of which the body prints (members AC-5a…b) | owner | Integration (Typst query) | drop the page break |
| AC-6 | The receipt states, for each code sent to its recipient, the gate, act, method and the masked contact | owner | Application | state no contacts |
| AC-7 | The receipt's act states the SHA-256 of the signature image its commit recorded | owner | Application | state none |
| AC-8 | The published form keeps `schema: f5sign.receipt/1` | owner | Unit | bump the schema |
| AC-9 | Only the receipt's own recipient's codes and image are stated, never another recipient's (members AC-9a…b) | derived — [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) §2.3 | Application | read the other recipient's facts |
| AC-10 | A contact corrected between the code and the act is unstated `CORRECTED_AFTERWARDS`; a code of the other kind of contact stays stated | derived — [ADR-0084](../adr/ADR-0084-a-correction-reaches-only-the-contact-it-changed.md) §2.9 | Application | ignore the correction |
| AC-11 | The page prints the image digest with the caveat that it cannot be checked against the PDF | derived — [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.5 | Integration (Typst query) | drop the caveat |
| AC-12 | No full email address or phone number of the recipient appears in the JSON or on the page (members AC-12a…b) | derived — [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.6 | Unit + Integration (Typst query) | encode the destination unmasked |
| AC-13 | The closed key set of the published form is pinned path by path with the new members | derived — [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) §5 | Unit | add a key unpinned |
| AC-14 | ADR-0086 (§2.3 and its `Relates to` row), `docs/ddd/evidence-audit-domain-model.md` and the integrator handoff name the two new members (members AC-14a…c) | derived — rule 1 | Review | — |
| AC-15 | The contacts stated for each way of acting (members AC-15a…d) | derived — `src/F5Sign/EvidenceAudit/Domain/Receipt/ActKind.php` | Application | see *Notes on AC-15* |
| AC-16 | The image digest stated for each way of acting (members AC-16a…e) | derived — `src/F5Sign/Session/Contract/Event/SignatureCommitted.php` | Application | see *Notes on AC-16* |
| AC-17 | The local-time conversion at each boundary (members AC-17a…e) | derived — `assets/evidence-audit/receipt.typ` | Integration (Typst eval) | switch at midnight |
| AC-18 | The `act-status` label group holds exactly `ActKind`'s cases | derived — rule 5 | Integration (Typst query) | remove one label |
| AC-19 | The trail's published form is unchanged by sharing the contact encoding | derived — `tests/F5Sign/EvidenceAudit/Unit/Domain/Trail/TrailJsonTest.php` | Unit | rename a contact key in the shared encoder |
| AC-20 | The `DECLARED_NONE` sentence names the party "La parte", and "destinatario" only the consignee | derived — `docs/BACKLOG.md` | Integration (Typst query) | restore the old sentence |

- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane mounting this tree; Infection filtered to
  the diff's `src` files.
- **How a printed line is tested.** No PDF text extractor exists (§2). The template exposes what it prints for these
  criteria as values Typst can query (as `<labels>` already is), and the tests read them with `typst eval`, as
  `the_template_labels_every_code_the_receipt_owns` does. A criterion on layout (a page break, a header's page)
  queries the element's location.

**Notes on AC-1**
- AC-1a — the band names the act's state (`act-status`). AC-1b — the act's time, local. AC-1c — the recipient's name and role.

**Notes on AC-2**
- AC-2a — the act's time, the verifications, the browser's times and the annex's times are printed local with the zone.
- AC-2b — the JSON's times are `+00:00` (`absent_values_are_null_and_times_are_utc`).

**Notes on AC-4**
- AC-4a — one device line, members joined, unsent members left out. AC-4b — the step: not printed, in the JSON.
  AC-4c — the `Accept-Language`: not printed, in the JSON.

**Notes on AC-5**
- AC-5a — the annex begins on a page after the body's last. AC-5b — each listed group appears in the annex and not in the body.

**Notes on AC-6**
- AC-6a — one entry per `OtpSent` of the recipient, in log order. AC-6b — each entry's gate, act and method as the
  fact recorded them. AC-6c — the contact masked by `MaskedContact`, source `LOG_DERIVED`.

**Notes on AC-9**
- AC-9a — contacts: with both recipients sent codes, each receipt states its own. AC-9b — image: with both committing
  images, each receipt states its own digest.

**Notes on AC-12**
- AC-12a — the JSON. AC-12b — the page.

**Notes on AC-14**
- AC-14a — ADR-0086 §2.3, and a line in its `Relates to` row naming this task. AC-14b — the domain model. AC-14c — `docs/frontend-handoff/TASK-047-integrator-recipient-receipt.md`.

**Notes on AC-15** (census of `ActKind` and the delegated path)
- AC-15a — a signer: the access gate's code and the signing gate's (act `SIGN`). Sabotage: keep only the first.
- AC-15b — an approver: the same as a signer. Sabotage: filter on `Role::signs()`.
- AC-15c — a decliner: the access gate's code, and the signing gate's code for the act `DECLINE` when one was sent.
  Sabotage: drop codes for a decline.
- AC-15d — a delegated act (the recipient signs via the integrator's system, `CommitDelegatedSignature`): no
  ceremony, so no codes and an empty list. Sabotage: state the asserted contact. ⚠ An ordinary recipient whose
  ceremony an integrator drives with its machine key (ADR-0055 §2.11) does receive codes and falls under AC-15a/b/c.

**Notes on AC-16** (census of commits)
- AC-16a — a signer whose commit recorded an image: its digest, source `LOG`.
- AC-16b — a commit that recorded none: empty.
- AC-16c — an approver: empty unless the commit recorded one.
- AC-16d — a decliner: empty.
- AC-16e — a delegated commit (`CommitDelegatedSignature` records none): empty.
- Sabotage for each: state the digest of any commit in the stream.

**Notes on AC-17**
- AC-17a — a winter instant prints `CET` (+1). AC-17b — a summer instant prints `CEST` (+2).
- AC-17c — the March change: 00:59:59 UTC is `CET`, 01:00:00 UTC is `CEST`.
- AC-17d — the October change: 00:59:59 UTC is `CEST`, 01:00:00 UTC is `CET`.
- AC-17e — 31 December 23:30 UTC prints 1 January of the next year.

## 6. Open follow-ups (track, don't solve here)

1. **The conservation date on the receipt.** Not stated: the ceiling is provisional until the envelope is
   `COMPLETED` (ADR-0073 §2.16). It could be stated on the per-document certificate, which is issued once its
   document is final (ADR-0094), or on a receipt re-issued at the end; neither is decided.
2. **The legal identity of the sender organisation.** The receipt still names the tenant by its provisioned label and
   says it is not the legal name; no context holds a legal name or tax id. Forced by the per-document certificate
   (ADR-0094), which names the parties as the owner wants them identified, or by a tenant asking for its legal name.
3. **Times outside peninsular Spain.** A tenant in the Canary Islands, or outside Spain, reads peninsular time. A
   per-tenant zone would be a field the receipt's model carries. Forced by the first tenant outside the peninsula.
4. **The trail's template** keeps UTC and its current layout; [BL-416](../BACKLOG.md) still records that its printed
   text has no test. Forced by any change to `trail.typ`'s printed lines, which would then ship untested; this task's
   query approach (§5) is the way to close it.

## 7. Deviations & honest notes

### Scope
- Evidence & Audit only, as §3 says. The diff also moved `TrailAssembler::contacts()` and `markImage()` (a pure move, for php-cs-fixer, added to slice 02: the lint failure came from the draft commit) and added `TypstTemplateProbe` beside `PdfProbe` under `tests/F5Sign/EvidenceAudit/Testing/Pdf/`. The trail's template and published form are untouched (AC-19).

### What the task flow did to the draft
- **A starting implementation predates this record.** It was written in the owner's session on 2026-10-29, before the owner pointed out that it skipped the task flow, on `feat/receipt-redesign`: the template (§3 #1, without AC-11's caveat and AC-20's sentence) and the model changes (§3 #2) with tests for a few criteria. The flow took it as a draft to verify, not as done.
- **Eight slices** landed on top of it: 01 the recipient's own codes, masked, for every way of acting; 04 the template regions, the probe, the band, local times and the running header; 02 the image digest of the act's own commit only; 05 the short body, the annex and the AC-20 sentence; 06 the printed contacts and image digest, the time boundaries and the label cite; 03 the schema, UTC, the closed key set and the unchanged trail; 07 ADR-0086, the domain model, the handoff and BL-469; 08 the closing slice (below). Critical slices ran on opus, standard ones on sonnet.
- **Findings fixed.** Slice 01: the AC-9a fixture did not discriminate (its row-2 sabotage stayed green) and got a fixture where the other recipient's access code went by SMS. Slice 04: the band-before-first-section check was tightened and a role-within-name finding closed. Slice 06: the page-level AC-12b assertion was proven red on its own after a hardening round. Closing review (one finding, confidence 80): the property `ReceiptAct::$signatureImage` encoded as `signature_image_sha256` broke `ReceiptJson`'s "keys are the model's field names" claim; slice 08 renamed it `$signatureImageSha256`, pinned a decliner's masked phone on the page, and corrected ADR-0086 §5, the handoff and docblock prose.
- The draft's printed-text criteria had no test; they now do (`ReceiptTemplateTest`, `TypstReceiptRendererTest`, via `TypstTemplateProbe`), each citing its AC.

### Decisions made during implementation
- Waves re-cut by the orchestrator and approved by the owner on 2026-10-29: slice 03 and 07 moved to wave 4, because sabotaging `ReceiptJson`/`TrailJson` (03) and `MaskedContact` (01) would have polluted the other slices' runs.
- Slice 04: the band-before-first-section check compares (page, y), not y alone; the footer's metadata binding is named `f`, not `h`, so it does not shadow Typst's `h(1fr)`.
- Slice 01: the builder's email correction moved after both codes (still before the act), so a check that ignores the correction's kind is caught.
- Slice 02: BL-463's claim that an approver commits no image was verified false (`CommitSignatureUseCase::checkModeAndImage` has no role branch); BL-463 and ADR-0086 §3.3 were corrected, keeping the reason. A commit through the integrator's system records no image.

### Decisions that needed an ADR
- None. The change extends ADR-0086 §2.3 within that decision (AC-14); no ADR moves state from this task.

### Declared and unproven properties
- The DST rule (AC-17c/d) is covered by Integration-tier Typst tests; the security audit warned (low) that they run only in a full suite, and they were in the full run at `1579ffb0`. `composer audit` was not run; `composer.json` and the lock are unchanged.
- Slice 06's template comment that the platform deletes its copy of the image once sealed was not re-verified in the slice; the closing review verified it (`Session\OnRecipientSigned` dispatches `ClearSignatureImage`).
- Contract-check, doctrine-guard and perf-smoke were skipped: the diff touches no route, OA string, event, migration or SQL, and no `perf:seed` script exists.

### Debt left behind, and where it lives now
- The four follow-ups of §6 keep their homes there.
- [BL-469](../BACKLOG.md) (the `DECLARED_NONE` sentence) is closed by slice 05/07; [BL-463](../BACKLOG.md) is corrected.
- [BL-471](../BACKLOG.md) (flaky `ChannelChangeReinvitesCrossingTest`): seen again on this branch's full run at `1579ffb0`; sighting added to its row.

### Delegated work
- No slice delegated to the `replicator` (every `## Delegated` reads none or below threshold). Slices: 01 critical/opus, 3 rounds; 04 critical/opus, 2 rounds; 02 critical/opus, 1 round; 05 standard/sonnet, 1; 06 standard/sonnet, 2; 07 standard/sonnet, 1; 03 standard/sonnet, 1; 08 critical/opus, 1.

### Cost of the run
- Eight slices, 12 review/implementation rounds in all; no escalation beyond the per-tier model choice, plus one plan amendment (slice 08) after the closing review.
- Infection on the diff's changed `src/` lines (6 files, 110 lines, merge-base `004d101b`), at `1579ffb0` on the
  `wt-backend` lane: 37 mutants, 33 killed, 4 escaped, 0 not covered; covered-MSI 89 %, MSI 89 % (bars 85/70). The
  four escapes, each justified:
  - `PublicVisibility` on `TrailAssembler::contacts`, `TrailAssembler::markImage` and `TrailJson::contactUse`: killed
    by the existing tests, which Infection's filtered test set did not include. Made `protected` one at a time,
    `ReceiptAssemblerTest` (the first two) and `ReceiptJsonTest` (the third) error on every case with "Call to
    protected method … from scope `ReceiptAssembler`" / "… from scope `ReceiptJson`"; each file restored.
  - `NullSafeMethodCall` on `AuthMethod::tryFrom($found[1]->method->value)?->requiredDestination()` in
    `TrailAssembler::contacts`: equivalent. Every `ExecutedAuthMethod` case is an `AuthMethod` case (census of both
    enums, 2026-10-29), and an `OtpSent` decodes its method as an `ExecutedAuthMethod`, so `tryFrom` never returns
    null for a decoded fact. The line predates this task; it is in the diff only because the method moved.
