# TASK-054 — The sender chooses how each recipient signs, and what their mark shows

<!-- OFFREPO: the product and legal facts this record relies on were read from the sibling repository
`f5sign-docs` on 2026-10-07, and are restated where they are used:
- `Legal/DPIA - Biometría Grafométrica.md` (v1.0, 2026-03-30, draft pending the DPO), §4.2: "Libre: El firmante
  debe tener una alternativa real para firmar sin proporcionar biometría"; risk R04 ("consentimiento no libre") is
  rated low because that alternative exists;
- `Especificaciones/Páginas Legales.md`: without biometric consent "se desactiva el modo 'Dibujar' y solo quedan
  'Escribir' (tipografía) o 'Subir' (imagen)";
- `Planning/F1-Auth-Tenancy/EP05-Modelo-Datos-Core/S05.3-Tablas-Recipient-Field-Firma/` (the old planning format,
  2026-07-01) gave each recipient a `signature_level` (`CLICK_TO_SIGN`, `ADVANCED_BIOMETRIC`, …); it was never
  built.
And the signer facts, read from `f5sign-signer` on 2026-10-07: the signer is replacing the blocking biometric
consent modal with an optional checkbox beside the Sign button (unticked by default). The recipient draws freely;
the box decides only whether the strokes are sent. The owner chose this, and it goes to legal with the consent copy. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/signature-modes`** (tip `8ccc8fc3`; behaviour at `7d82550d`, published wording at `53c61d7d`), 2026-10-08. Under the worktree lane (`wt-backend`, this tree), the full regression at `7d82550d` ran 6230 tests and 73575 assertions with lint, deptrac and PHPStan green; `53c61d7d` was then validated with lint, PHPStan, `OpenApiSpecTest` and the fast tier (5168 tests), and the commits after it are docs only. ⚠ **Infection is pending:** the 84% covered-MSI measured at `7025b022` predates the fix round, and by the maintainer's decision of 2026-10-08 it runs once at the end (task-runner Phase 3b). **Implemented, Infection pending, not merged, not pushed.** Design written 2026-10-07; D2 answered and D7–D12 added on 2026-10-08. |
| **Type** | **Forward build.** Each recipient gets, at authoring, the ways they may sign (`SIMPLE`, `DRAW`, `TYPE`), whether biometrics are offered to them, and whether their name appears in their mark; the commit declares the way used and the backend checks it. |
| **Why** | Today every recipient is offered the same thing: the session publishes `allowed_signature_modes: ['DRAW', 'TYPE']` for everyone, hard-coded, and a drawn image is optional. The sender cannot ask a carrier for a check-only signature, require a drawn one from a consignee, or leave the name out of a mark. |
| **Builds on** | [TASK-053](TASK-053-the-recipients-drawn-signature-on-their-mark.md) (the commit's `signature_image` and `biometric_data`, the image's table and clearing, `RecipientEnvelopeContextView::marksTakeAnImage()`, the config flags), [TASK-032](TASK-032-ordered-auth-method-list.md) (how a per-recipient authoring setting is declared, validated and read back), [TASK-018](TASK-018-visible-signature-mark.md) (the mark), and the mark-text fitting fix on `fix/mark-text-fits` (2026-10-07: the name wrapped and ellipsized inside the box). |
| **Scope** | Envelope authoring (add-recipient, the dashboard's and the integrator's route) and send, the recipient's stored setting, the session's published `config`, the commit's validation, the mark's composition, the trail's statement of the mark, and the signer and integrator handoffs. **Out:** keeping the strokes (TASK-053 §6, still open); `UPLOAD`; per-tenant defaults. |
| **Decision record** | **[ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md)**: the trail states a mark's text by rule; with the name optional, the rule gains the recipient's setting. **[ADR-0032](../adr/ADR-0032-evidence-pii-custody.md)** (`Proposed`) governs the image as before. If the build finds that storing the setting on the recipient needs a cross-BC change, it drafts an ADR as `Proposed` and stops. |
| **Delivery bar** | A sender declares, per recipient, `signature_modes` and `show_name` (and `biometrics_offered`); the recipient's session publishes exactly those modes; a commit whose declared mode or image does not match is refused with 422 and admits nothing; a mark shows the image and/or the name as configured; a recipient for whom nothing was declared signs with a check, as `SIMPLE`. |
| **Siblings** | `fix/mark-text-fits` (in progress, 2026-10-07) changes how the mark's text is drawn, introduces `ZOOM_AND_CENTER` and touches `MarkText`; this task changes whether the text is drawn. **That fix lands first and this task builds on it**: D9 and D11 lean on what it leaves in `MarkText` and `DssPayloadMapper`. [TASK-045](TASK-045-browser-reported-evidence-at-the-commit.md) changes the same commit request. |
| **Coordinated change** | `f5sign-signer` (reads the modes it already reads; sends `signature_mode`), `f5sign-dashboard` (the recipient form), and the integrator (`factor5-dashboard`), who authors envelopes through the API. Each gets a handoff. |

---

## 1. Why this task exists

After TASK-053 a recipient with a visible mark is offered a drawing, may skip it, and always gets their name in the
mark. Every one of those is a choice the sender should make per recipient, not a constant:

- A carrier confirming a delivery should sign with a check, quickly.
- A consignee accepting goods may have to leave a handwritten signature.
- Some waybill boxes have the name printed already, so the mark should carry only the signature.

## 2. What already exists (reuse, do not rebuild)

- **The modes the signer shows already arrive from the session.** `GetSigningSessionController` publishes
  `config.allowed_signature_modes`, today the constant `['DRAW', 'TYPE']`, and the signer renders whatever it lists.
  This task makes that value the recipient's setting.
- **The image path is TASK-053's.**
  - The commit accepts `signature_image`, checked before the act's unit of work.
  - Session keeps it in `session.signature_image` until `RecipientSigned`, then clears the bytes and keeps the
    digest.
  - The image is drawn on every mark above the name.
  - `biometric_data` is validated and discarded, and only with `biometric_consent: true`.
- **One predicate decides whether a recipient's marks take an image:**
  `RecipientEnvelopeContextView::marksTakeAnImage()` (SEQUENTIAL_PADES and at least one visible mark). It feeds the
  commit's 422 `SIGNATURE_IMAGE_NOT_ACCEPTED` and both config flags.
- **A per-recipient authoring setting already exists to copy:** the ordered auth-method list (TASK-032). It is
  declared on **add-recipient only**, which is draft-only (`Envelope::addRecipient()` starts with `guardDraft()`).
  Its structural rules live in its slot value types, not in the aggregate. It is read back on the envelope, and read by
  Session through Envelope's contract.
- **A correction is not a field edit, and it is not the route for this setting.** `CorrectRecipientRequest` carries
  only `email` and `phone`, and `CorrectRecipientController` says so in its docblock. A correction is limited to 3 per
  recipient, emits `RecipientCorrected`, re-invites the recipient, and is legal only on a sent envelope. Adding the
  signature setting to it would spend that budget and re-invite someone whose contact was never wrong.
- **A delegated recipient's mark always states the route in words** (`SignatureExecution\Contract\Type\MarkText`,
  ADR-0055 §3.3(b)), and the delegated commit never carries an image (`CommitDelegatedSignatureUseCase`).
- **The mark's text is composed by one rule** (ADR-0072; moved to a SignatureExecution contract type), which the
  signer and the trail both use.

## 3. What gets built

1. **Authoring.** Add-recipient accepts, per recipient:
   - `signature_modes`: a non-empty set of `SIMPLE`, `DRAW` and `TYPE`. If it is absent, it is `[SIMPLE]`.
   - `biometrics_offered`: a boolean, meaningful only with `DRAW`. The default is `true`, decided 2026-10-07 and
     revisable.
   - `show_name`: a boolean, default `true`.

   Refused with 422 and a named code (the structural rules in the setting's own value type, as TASK-032 does):
   - an empty or unknown mode;
   - `biometrics_offered: true` without `DRAW`;
   - **`show_name: false` with `SIMPLE` among the modes**, because a recipient who signs with a check would leave
     an empty mark. A recipient who should leave no mark gets no placement;
   - **for a machine recipient** (`signs_via` `MACHINE_KEY`, known at add-recipient), anything but `[SIMPLE]` with
     `show_name: true` (D9).

   The setting is fixed at add-recipient, in draft, and read back on the envelope's views. It is **not** part of a
   correction and does not change once the envelope is sent (D7).
1b. **Send.** `Envelope::send()` refuses (422 `SIGNATURE_MODES_NEED_A_MARK`; *amended 2026-10-08: first written as 409, built as 422 per ADR-0029, see §7*) a recipient whose modes lack `SIMPLE` when no mark of
   theirs can take an image: on a `SINGLE_SEAL` envelope, or on `SEQUENTIAL_PADES` with no visible placement (D8).
   ⛔ **Not gated on `Role::signs()`.** The neighbouring `ensureEverySignerIsAssigned()` is, but an APPROVER
   (BLOCKING, so it commits) authored `[DRAW]` has no signing rows, so no mark of theirs can take an image. Copying
   that gate would reopen the hole. The check keys on roles that can commit. VIEWER, REVIEWER and EDITOR are
   INFORMATIONAL and refused at the admission (`COMMIT_NOT_OFFERED_TO_ROLE`), so their modes never reach a commit.
   It is the same question `marksTakeAnImage()` asks on the read side, so the two must share one predicate or be
   pinned against each other by a test.
1c. **Existing rows.** The migration gives every recipient that already exists `biometrics_offered: true` and
   `show_name: true`, and these modes:
   - a `MACHINE_KEY` recipient gets `[SIMPLE]`, which satisfies D9;
   - every other recipient gets `[SIMPLE, DRAW, TYPE]`, which is today's behaviour (an optional drawing).

   A draft, a sent envelope and an ended one read the same as before in every check. The one visible difference is
   that the published `allowed_signature_modes` becomes `['SIMPLE', 'DRAW', 'TYPE']` instead of today's hard-coded
   `['DRAW', 'TYPE']`, which states the optional drawing explicitly. Only recipients added after the migration take
   the `[SIMPLE]` default (D10). The migration does not cover one thing: the commit's new required `signature_mode`
   (§3 #3). An in-flight session on a signer build that predates the field is refused at its next commit. That is
   the accepted cost of a breaking change while nothing is in production.
2. **The session's `config`.** For each recipient:
   - `allowed_signature_modes` = the modes they can use: their `signature_modes`, less `DRAW` and `TYPE` where
     `marksTakeAnImage()` is false (`SINGLE_SEAL`, or no visible placement). D8 leaves `SIMPLE` there. Amended in
     the fix round of 2026-10-08 (it first published `signature_modes` whole, offering modes the commit refused);
     the rule's one home is `RecipientEnvelopeContextView::usableSignatureModes()`.
   - `biometric_capture_enabled` = the commit accepts an image: `DRAW` or `TYPE` among those modes.
   - `consent_biometric_required` = `DRAW` among those modes and `biometrics_offered`. It means "offer the
     optional biometric checkbox"; see D4.

   The `#[OA\*]` description of the block says exactly that.
3. **The commit declares `signature_mode`** (`SIMPLE` | `DRAW` | `TYPE`, required once this lands). It is checked
   before the act's unit of work, beside TASK-053's image checks, and costs no code attempt. It answers 422:
   - **A mode the recipient was not offered:** `SIGNATURE_MODE_NOT_OFFERED`.
   - **`SIMPLE` with a `signature_image`,** or **`DRAW`/`TYPE` without one:** `SIGNATURE_IMAGE_REQUIRED` /
     `SIGNATURE_IMAGE_NOT_ACCEPTED`. The exact code set is fixed when built, reusing TASK-053's where the meaning
     is the same.
   - **`biometric_data` with any mode but `DRAW`, or when biometrics were not offered:** the block is dropped, as
     today without consent. It is never refused, so a biometric problem never blocks a signature.

   The mode used is recorded on `SignatureCommitted` (additive key), so the trail can state it. `signature_mode` is
   required on the browser commit, so a signer build that does not send it is refused; the handoff says so.
   **The machine route** (`CommitDelegatedSignatureController`) serves two kinds of recipient: a `MACHINE_KEY` one
   with an assertion, and a relayed `SIGNING_PLATFORM` one. It never carries an image, so it records `SIMPLE` and
   **refuses** (409, `SIGNATURE_MODE_NOT_OFFERED`) a recipient whose modes lack `SIMPLE`. That recipient can still sign
   in the signer, so the refusal never leaves them unable to sign (D12).
   - **Placement:** after the route's step guard, so `STEP_NOT_ACTIVE` still comes first, and **before**
     `signingGate->answer()`, so the refusal charges no relayed code attempt, like the browser commit's checks.
   - **The split status is deliberate.** The same code answers 422 on the browser commit, where the request's
     shape is wrong, and 409 on the machine route, where the recipient's state is one this route cannot satisfy;
     every other state refusal on that route is a 409. Clients branch on `code`.
   - **Its 409 `#[OA\*]` block is a closed list** ("`code` distinguishes the conditions"), and it gains this code.
4. **The mark.**
   - `show_name: false` drops the name from the mark: the image only, centred, keeping its aspect ratio. ⚠ Image-only
     placement is not measured yet: the first step of the build seals one against the live DSS with the
     `ZOOM_AND_CENTER` scaling that `fix/mark-text-fits` introduces, and records the result (D11).
   - `SIMPLE` draws the name only, as today's text-only mark (wrapped and ellipsized by the fitting fix).
5. **The trail** (ADR-0072's mark rule): it states the mode used and whether the name was drawn. It keeps stating the
   image's digest when there is one. The rule's text in ADR-0072 is amended in place.
6. **Handoffs.**
   - **Signer:** read `allowed_signature_modes`; send `signature_mode`; the optional biometric checkbox only when
     `consent_biometric_required`; the new 422s.
   - **Dashboard and integrator:** the three authoring members, their defaults and their refusals.
7. **Records sweep.** TASK-053's §3 #7 and the session controller's hard-coded modes; the `allowed_signature_modes`
   description; `docs/ddd` (envelope and signing-session models); `docs/LIVE_SCHEMA.md` if the setting adds columns.

## 4. Key decisions

- **D1 — the modes are `SIMPLE`, `DRAW` and `TYPE`** (maintainer, 2026-10-07).
  - `SIMPLE` is the check-only signature: consent, plus the signing code if the recipient has a signing gate.
  - The name was chosen over `CHECK` and `CLICK`.
  - `UPLOAD` stays out (TASK-053 D2).
- **D2 — `SIMPLE` may be combined with `DRAW` and `TYPE`** (maintainer, 2026-10-08).
  - `[SIMPLE]` is a check only, `[DRAW]` is a required drawing, and `[SIMPLE, DRAW]` is an optional drawing.
  - The recipient picks among what was offered, and the commit's `signature_mode` says which.
- **D3 — the default is `[SIMPLE]`** (maintainer, 2026-10-07). A recipient for whom the sender declared nothing
  signs with a check. This changes today's behaviour, where a drawing is offered to everyone with a visible mark.
  That is accepted because nothing is in production.
- **D4 — biometrics are offered, never required** (DPIA §4.2, restated in the head note).
  - The sender decides whether the optional checkbox appears; the recipient decides whether to tick it.
  - `DRAW` without ticking is the free, non-biometric alternative the DPIA demands, so a `[DRAW]`-only recipient is
    lawful.
  - ⚠ This departs from `Páginas Legales`, which disables drawing without consent. The owner chose the checkbox. The
    reading (a PNG carries no timing or pressure; the strokes are what is biometric) goes to legal with the consent
    copy, and `f5sign-docs` is updated after legal agrees.
- **D5 — the backend checks the declared mode, and cannot check the image's origin.** A PNG drawn and a PNG typed are
  the same to the server. A tampered client could declare `DRAW` and send a typed name, and nothing here can tell.
  The only signal is strokes beside a `DRAW` whose recipient consented, and their absence proves nothing. State this
  in the handoff and the trail wording; do not claim more.
- **D6 — no empty mark.** `show_name: false` is refused with `SIMPLE` among the modes (§3 #1). With only `DRAW`
  and/or `TYPE`, the image is required, so the mark is never empty.

D7 to D11 were settled on 2026-10-08, under the maintainer's instruction to proceed without asking unless a decision
was theirs. Each follows from the code or from an existing rule, and each is revisable.

- **D7 — the setting is authored, never corrected.** It is set at add-recipient like the auth-method list, and fixed
  once the envelope is sent. Making it correctable would need its own recorded fact and route, because the
  correction route is contact-only, bounded and re-invites. Nothing asks for that today.
- **D8 — a recipient who must leave an image needs somewhere to leave it, and send is where that is known.**
  Assignments and placements are added after the recipient, so add-recipient cannot check it. Without the send-time
  refusal, a `[DRAW]` recipient on `SINGLE_SEAL`, or one with no visible placement, could never sign: the commit
  would demand an image and refuse it at once. The refusal is loud; nothing narrows the modes silently.
- **D9 — a delegated recipient signs `SIMPLE`, with the name.** The machine route has no ceremony and carries no
  image, and its mark must state the route in words (ADR-0055 §3.3(b), `MarkText`'s invariants and their test).
- **D10 — existing recipients keep today's behaviour.** The migration writes the setting that reproduces it, so the
  rows it lands on mean the same in every state, on the write side as well as the read side (the repo's authoring
  rule 6). The `[SIMPLE]` default applies only to recipients added afterwards.
- **D12 — a relayed act is a check, so the machine route takes it only from a recipient offered `SIMPLE`**
  (2026-10-08, same footing as D7–D11). The route has no image member. A `[DRAW]` recipient relayed through it would
  either record a mode they were not offered or be unable to finish there. They finish in the signer instead.
  Whether the machine route should accept an image is a follow-up, opened only if an integrator asks.
- **D11 — image-only placement is measured before it is promised.** If DSS cannot centre an image alone while
  keeping its aspect ratio, the build stops and reports rather than pre-scaling the PNG. Pre-scaling would contradict
  TASK-053 D3, which keeps the image as sent.
  - **Measured 2026-10-08, against the live DSS 6.4 with `ZOOM_AND_CENTER`:** an image-only mark is centred and keeps its ratio. A 300×120 image in a 167×66 box was placed 165×66 at x=1; in 153×50, 125×50 at x=14; a 100×200 image in 167×66, 33×66 at x=67. Pinned by `MarkTextFitTest::an_image_alone_is_centred_in_the_box_and_keeps_its_proportions`. No pre-scaling was needed.

## 5. Verification

- **Gates:** suite, PHPStan, deptrac and lint, under the lane that mounts this tree.
- **Tests and sabotages:**
  - **Authoring:** every refusal of §3 #1, one case each, including a delegated recipient's. The default `[SIMPLE]`
    when the member is absent, read back. The correction route's request gains no member: a
    correction still changes the contact only.
  - **Send (D8):** a `[DRAW]` recipient on `SINGLE_SEAL`, one with no visible placement, and a non-SIGNER recipient
    (an APPROVER) authored `[DRAW]` each refuse the send. A `[SIMPLE, DRAW]` recipient in the same envelope does not. The send-time predicate and `marksTakeAnImage()` are
    pinned against each other. Sabotage: drop the send check, and watch the case reach a commit that can never
    succeed.
  - **Migration (D10):** an existing draft, sent and ended platform recipient each read `[SIMPLE, DRAW, TYPE]` after
    it; an existing `MACHINE_KEY` recipient reads `[SIMPLE]`; a recipient added afterwards reads `[SIMPLE]`.
  - **Machine route (D12):** a relayed recipient authored `[DRAW]` is refused with `SIGNATURE_MODE_NOT_OFFERED` and
    charged no attempt; one authored `[SIMPLE, DRAW]` commits and records `SIMPLE`; a `MACHINE_KEY` commit records
    `SIMPLE`. ⚠ The fixture's envelope must pass the new send check (SEQUENTIAL_PADES with a visible placement for
    that recipient), or the send refuses first and the case never reaches the route.
  - **Config, per combination:** modes, the two flags, and their agreement with the commit's checks through one shared
    predicate. The fixture must make mode, marks and signing mode disagree. Sabotage: compute a flag from the mode
    alone.
  - **Commit, one case per refusal of §3 #3:** each answers 422, admits nothing and charges no attempt. A biometric
    block with a non-`DRAW` mode is dropped, not refused. Sabotage each guard and check which one fired.
  - **Mark:** `show_name: false` draws the image only, and `SIMPLE` draws the name only, against the live DSS. The
    widget's `/Rect` is the placement's.
  - **Trail:** the mode and the name's presence are stated. The closed key set of `SignatureCommitted` is asserted.
- **Acceptance:** over HTTP, a SEQUENTIAL_PADES envelope with visible placements and three recipients (`[SIMPLE]`,
  `[DRAW]` with no name, and `[SIMPLE, DRAW]`) signs end to end. Each mark matches its setting, and a commit that
  breaks a recipient's setting is refused. A second envelope with a `[DRAW]` recipient and no placement for them is
  refused at send.

## 6. Open follow-ups (track, don't solve here)

- **Keeping the strokes** (TASK-053 §6); the consent record then has to be kept with them.
- **Legal:** the checkbox reading of D4 and the consent copy; then `f5sign-docs` `Páginas Legales`. Tracked as BL-389.
- **Per-tenant defaults** for the three members, if a tenant wants `[DRAW]` by default. Tracked as BL-386.
- **An image on the machine route** (D12), if an integrator needs to relay a drawn signature. Tracked as BL-385.
- **A claimable `MACHINE_KEY` recipient** takes the same D9 rule. Checked 2026-10-08: reachable, and the recipient constructor enforces D9 for it, but no test pins the pair. Tracked as BL-387.

## 7. Deviations & honest notes

### Scope
- None beyond the record. The main commit `72bd3f79` batches 136 files: a required member threaded through every layer (`SignatureSetting` on the recipient, its views, repositories, presenters and the commit) would not compile in parts. This is a process note, not a scope one; its subject names the scope (`feat(task-054)`) for that reason.

### Decisions made during implementation
- **The send refusal is 422 `SIGNATURE_MODES_NEED_A_MARK`, not §3 #1b's 409**, per accepted ADR-0029 (a request-shape-versus-state mapping); §3 #1b is amended in place and says so.
- **`allowed_signature_modes` publishes the usable subset** (`RecipientEnvelopeContextView::usableSignatureModes()`), not the raw offer (security audit W1, fix round); §3 #2 states it.
- **`signature_modes` is capped at 3** (the three modes; a longer list is refused).
- **An unknown mode answers `VALIDATION_ERROR`**, as TASK-032 does for an unknown auth method.
- **The biometrics-offered half of dropping strokes is not checked at the edge**: strokes are not kept yet (TASK-053 §6), so there is nothing to drop on that side.
- **`RecipientAuthContext::$marksTakeAnImage` was removed**; its job is the shared predicate `SigningMode::marksTakeAnImage()`, read by send and by the session view.
- **D11 was measured first**, see the dated line under D11.

### Decisions that needed an ADR
- None new. ADR-0029 (status mapping) and ADR-0072 (the mark rule, amended in place and already accepted) bind it; no ADR's `Status`, `Enforced by` or `Realized in` moves from this task, so none is proposed for acceptance.

### Declared and unproven properties
- **D5 stays unprovable**: the server cannot tell a drawn PNG from a typed one.
- **Infection**: the 84% covered-MSI was measured at `7025b022`, before the fix round; the figure for the tip is unmeasured.
- **`OpenApiSpecTest` proves a code is named by some operation, not that it sits in the right route's closed list** (BL-388).
- **BL-356's full-order flake** (`StorageLifecycleScenarioTest`) failed once at `b18f6cbe` and passed in the full runs at `7025b022` and `7d82550d`.
- No SMS, DSS-external or real-signer run exercises the signer side; the handoff is the contract.

### Debt left behind, and where it lives now
- An image on the machine route (D12) → BL-385.
- Per-tenant defaults → BL-386.
- A claimable `MACHINE_KEY` recipient: reachable today and covered by the constructor's D9 rule, but unpinned by a test → BL-387.
- The `OpenApiSpecTest` per-route limit (a PHPStan call graph with bus resolution, an ADR-level decision) → BL-388.
- Legal's review of the checkbox reading and the `f5sign-docs` `Páginas Legales` update (off-repo) → BL-389.
- Keeping the strokes → TASK-053 §6, not duplicated here.

### Delegated work
- Three `replicator` delegations, all accepted: `signatureSetting` at 31 `RecipientView` sites plus 6 SQL fixtures; `signatureMode` at 28 callers; `signature_mode` in 48 HTTP commit bodies. In the last, the replicator escaped a JSON literal correctly where the brief's own literal was wrong.
