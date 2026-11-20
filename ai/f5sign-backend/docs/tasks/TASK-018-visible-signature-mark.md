# TASK-018 — The visible signature mark (per-recipient field placement)

<!-- OFFREPO: the Factor5 dashboard prototype patch (`factor5_dashboard_sf-ef12c8c-WIP Sign waybills with certificates.patch`, at the workspace root beside the repos) is another team's WIP and is not vendored here. Its `PdfSignerService::SIGNATURE_POSITIONS` and its `signature_calibrator` page are the prior art this task mines; every fact taken from it is restated below, so nothing here depends on reading it. The two Factor5 sample waybills its coordinates were calibrated against are likewise out of tree. -->

| Field | Value |
|-------|-------|
| **Status** | **✅ Merged to master** (`feat/sequential-pades`, backend-only — the visible half of [TASK-017](TASK-017-sequential-incremental-pades.md)). Both slices landed and green. The mark renders the recipient's name, sized to fit its box (§2, F7); the biometric scribble is deferred (§5), and is built by [TASK-053](TASK-053-the-recipients-drawn-signature-on-their-mark.md) (2026-10-07). |
| **Type** | Forward build — a recipient's signature becomes **visible** on the page: an authored list of field placements per `(recipient, document)`, rendered by the existing DSS byte-path as PAdES visible signatures. |
| **Why** | [TASK-017](TASK-017-sequential-incremental-pades.md) makes the signature real but **invisible**: `renderMark` is stored and never honoured, because no placement is stored and a visible widget needs `page` + a rectangle. A paper CMR accumulates signatures in the CONFORME boxes; an eCMR that proves custody cryptographically but shows nothing is not the document the parties expect. |
| **Scope** | The **signature widget is ours** (user, 2026-07-09). Other marks on the waybill — names, reservations text, the CONFORME checkbox — render from the dashboard's Twig template placeholders (`{{Firma_*}}`, `{{Reservas_*}}`, `{{Check_Conforme_*}}`) and are not this task's concern. |
| **Decision record** | Extends [ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md) (its "visible marks" deferral discharges here). Relies on ADR-0004 / ADR-0008 for the cross-BC read the signer loops. |

---

## 1. Facts, measured against the live EU DSS

Everything here was verified against the running `eu-dss` before any code was written. Each corrects or pins something that would otherwise cost an hour — or ship wrong.

**F1 — the coordinate origin is TOP-LEFT, `originY` increasing downward.** This is DSS's convention, the *opposite* of PDF user space. Signing a 792pt-tall page with `originY: 50, height: 40` yields the widget annotation `/Rect [40 702 140 742]`; `/Rect` is PDF user space (bottom-left), so the box's **top** edge lands at `792 - 50`. Read `originY` as "distance down from the top edge to the top of the box". *Our own docs said bottom-left until the coordinate-origin correction; the error is silent — it mirrors every mark vertically.* Corroborated by the prototype, whose comment reads "origin top-left, Y increases downward (same as PDF.js at scale 1.0)" — which is also **why** a browser-based calibrator works: pdf.js canvas coordinates and DSS field coordinates agree one-to-one, no flip.

**F2 — one `imageParameters` block is one visible widget, and one widget belongs to one signature.** N boxes for one signer on one document therefore means **N incremental PAdES signatures**, not one signature with N appearances. Measured: two marks produced two `/SubFilter /ETSI.CAdES.detached` signatures, both `/Rect`s at the requested coordinates, the second PDF byte-prefixed by the first (a true incremental update). This is the fact that shapes the data model — placement is a **list**, and a list costs signatures.

**F3 — a text-only mark renders.** No PNG is needed: `imageParameters` with only `textParameters` produces an appearance stream `BT /F1 12 Tf … Tj ET`. **The text is drawn as subset-encoded glyphs**, so it does *not* appear as a literal string anywhere in the PDF bytes. A test must therefore assert on the widget's `/Rect` and the presence of its `/AP` appearance stream — **never** by grepping for the text.

**F4 — after a signature exists, stamping is illegal.** PAdES permits only specific modifications to a signed document: adding signature fields, validation data, and timestamps. Modifying a page's `/Contents` or `/Resources` — which drawing an image stamp requires — corrupts every prior signature. The prototype carries a `stamp` strategy that is *only* safe for the first signer and silently falls back to DSS visible signatures for everyone after. **We never stamp.** Every mark is a DSS visible signature, which is a permitted Widget-annotation addition.

**F5 — never set `textWrapping`** on `imageParameters.textParameters`: DSS then scales the font to the box width and throws *"signature field box is too small"*.

**F7 — DSS defaults text to 12pt and does *not* shrink it to fit.** A mark wider than its box is drawn anyway and clipped by the widget's `/Rect`; with `signerTextPosition: RIGHT` the overflow falls off the **left**, so a 36-character UUID in a 153pt box renders as `…-4d80-ac04-e600e92d4775` and reads like a placement bug. Set `textParameters.size` explicitly — 8pt fits a ~30-character company name in the narrowest box the eCMR waybill authors. Not `textWrapping` (F5). *Found by a live drive on 2026-07-10, after the suite had been green for a day: no test can see this, because F3 forbids asserting on the drawn text.* UTF-8 is safe — `ñ`, `á`, `ç` and `&` all render correctly through the subset encoding.

> **Amended 2026-10-07 (branch `fix/mark-text-fits`).** 8pt alone did not hold: measured against DSS 6.4 in the
> waybill's 167×66 and 153×50pt boxes, a delegated company name with its route clipped its identifying start
> exactly as F7 describes, and DSS never shrinks or ellipsizes at FONT_BASED. F5 still stands, and more widely
> than it says: `FILL_BOX` / `FILL_BOX_AND_LINEBREAK` change the size (5–22pt), and the latter refuses the box
> beside an image. What DSS does honour is a `\n` in the text, at the same size (leading 10.2pt). So the backend
> now lays the text out itself, with the advance widths of the font DSS draws in (PT Serif Regular, table in
> `assets/signature-execution/`): left-aligned and centred vertically, wrapped at words to the box less 3pt of
> padding a side, as many lines as the box holds, the last one ellipsized; beneath an image, one ellipsized line
> (`\F5Sign\SignatureExecution\Infrastructure\Pdf\MarkTextLayout`). F3 still holds for grepping: the live test
> that checks the drawn lines (`MarkTextFitTest`) decodes the appearance stream through the font's `/ToUnicode`.

## 2. The model

**Placement is a list, per `(recipient, document)`.** The prototype keys positions by *role* (`SHIPPER`/`CARRIER`/`RECEIVER`) and hardcodes them as a class constant, because it is one app serving one document layout. Our backend has a single generic `SIGNER` role and the dashboard encodes eCMR policy — so placements are authored data hanging off the existing `SigningAssignment`, whose identity is already the `(recipient, document)` pair.

- `Contract\Type\FieldPlacement { page, originX, originY, width, height }` — a `CompositeValueObject`, private ctor + `fromRect()` factory (`ValueObjectShapeRule`).
- `domain.signing_assignment_placement`, keyed `(recipient_id, document_id, ordinal)`, FK-cascading from the assignment. Ordinal is load-bearing: the first placement's signature is the one a future TSA/B-T level would timestamp, and order must be stable across a replay.
- **`renderMark` retires.** It was a placeholder for "does this signature show", which is now exactly `placements !== []`. Keeping both admits the contradictory state we ship today — `renderMark: true`, no placement, signs invisibly, says nothing. One shape per concept.
- Coordinates are **template-coupled**: measured off the rendered Twig template, so they must be recomputed whenever the template moves. That is the dashboard's business (the prototype's `signature_calibrator` page is the right tool for it, rendered with pdf.js at scale 1.0); the backend only stores what it is given.

**The mark's content is the recipient's name** — what a paper CMR's CONFORME box carries — falling back to their email and finally to their id, since the aggregate guarantees neither. It is never empty: DSS draws no appearance stream for empty text, which would turn a *placed* signature silently invisible. *(It rendered the recipient's UUID until a live drive on 2026-07-10 showed the id overflowing the narrow per-order box; see §5.)* The prototype's mark is instead a hand-drawn biometric scribble captured with `signature_pad.js` and rasterised server-side. Our ceremony (ADR-0028) captures consent, IP and user-agent — no scribble — and the signer app is another team's; a scribble slots into the same `SignatureImage.imagePngBase64` field when it arrives. *(It arrived with [TASK-053](TASK-053-the-recipients-drawn-signature-on-their-mark.md): the signer rasterizes the drawn or typed signature to a PNG, the commit carries it, and the mark draws it above the name.)*

## 3. Build plan (slices on `feat/sequential-pades`)

**✅ Slice 1 — the placement model (DONE).** `FieldPlacement` + the child table + migration (`tenant_id` + FORCE RLS from birth via the shared `public.set_tenant_id_from_scope()` trigger, as `signing_assignment` does) + both persistence adapters (ORM alias *and* the DBAL twin, ADR-0018) + `Envelope::assignSigning()` + the `AssignSigning` command + the HTTP edge (`placements: [{page, origin_x, origin_y, width, height}]`) + `renderMark`'s retirement. `EnvelopeContextView::signingAssignmentsFor()` carries the placements through unchanged. **Zero behaviour change:** nothing reads a placement yet.

**✅ Slice 2 — render (DONE).** `DocumentSigner::sign()` takes the recipient's marks for one document and issues **one DSS signature per mark** (F2), chaining the bytes in memory, storing once, and appending **one** SIGN artifact — one signing act, one execution id, one chain entry, however many revisions the marks required. A recipient with no placements signs once, invisibly. `SignForRecipientUseCase` builds each `SignatureImage` from the placement plus the recipient's name (§2), resolved **once** before the document loop so a chain-conflict re-read cannot change what the mark says mid-act.

- **F6, learned here — an invisible signature still gets a signature *field*, with a degenerate `/Rect [0 0 0 0]`.** "Signed but not drawn" is a zero-area widget, not the absence of one. Asserting on that rect is strictly stronger than asserting no rect exists, which an *unsigned* document would also satisfy.

## 4. Verification

- `make qa` green at each slice; stop the workers first (`make worker-down`).
- **Slice 1:** aggregate guards (placement on an unassigned pair, a page below 1, a non-positive width); round-trip through the live ORM adapter *and* the DBAL read adapter, proving the ordinal survives and the trigger stamps `tenant_id` that no adapter writes; migration up/down on a scratch DB; live curl on `:8000`.
- **Slice 2 (done):** `VisibleSignatureMarkTest`, against the live DSS. A `SEQUENTIAL_PADES` envelope whose recipient has **two** placements on one document produces **two** signatures on it, each `/Rect` exactly where it was authored (F1's arithmetic, checked as `y_top = pageHeight - originY` — the fixture is US Letter, 792pt, not A4), bytes prefix-preserved, and **one** SIGN artifact. The same recipient's *unplaced* document gets one signature and a zero-area field (F6). Asserted on `/Rect` + `/AP`, never on the mark's text (F3).
- **Integrity, never validity** — the dev keystore is self-signed, so every signature validates as `INDETERMINATE / NO_CERTIFICATE_CHAIN_FOUND`. Unchanged from TASK-017 §5.

## 5. Deferred

- **The biometric scribble.** Needs the signer app (`:3001`, another team) to capture strokes and our edge to accept a PNG. Slots into `SignatureImage.imagePngBase64` with no model change. **Closed by [TASK-053](TASK-053-the-recipients-drawn-signature-on-their-mark.md) (2026-10-07).** The model needed none, but the mapper did: it sent the image as `{bytes, mimeType}`, which DSS 6.4 refuses, so it now sends `{bytes, name}` with the name at `BOTTOM`. The strokes reach the commit and are discarded (TASK-053 §4 D7).
- **Appearance tuning, partly discharged.** Font size is now set (F7) and the mark names its signer (§2). Still hardcoded and still cosmetic: `signerTextPosition: RIGHT` (so a mark is right-aligned in its box), `imageScaling`, and padding — the prototype's calibrated appearance uses `BOTTOM` and padding 5. Best settled against a real waybill.
- **A placement calibrator** — a dashboard concern (pdf.js at scale 1.0, drag the boxes, copy the coordinates out).
- **`padesTargetProfile` / TSA** — unchanged from [ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md). If B-T ever lands, only the *first* mark's signature should carry the timestamp, as the prototype does.
