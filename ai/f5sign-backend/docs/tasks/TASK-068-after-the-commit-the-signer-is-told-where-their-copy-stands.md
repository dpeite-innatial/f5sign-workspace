# TASK-068 — After the commit, the signer is told where their copy stands

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `fix/signed-copy-after-commit`** (code tip `73f42ab6`; docs `88366009`), 2026-10-23 — full suite green under the `wt-backend` lane (an ephemeral stack mounting this worktree's tree, not the main checkout's): `OK (8239 tests, 92886 assertions)` at `73f42ab6` with lint, deptrac (0 violations, 0 uncovered) and PHPStan clean. Pending review. ADR-0090 was accepted by the owner on 2026-10-23, after this task exercised it. The Infection verdict on the changed lines is in §7. The copy after the signer leaves the ceremony is not here (BL-188, TASK-070). |
| **Type** | **Corrective + forward build** in Session's reads. Corrective: between an admitted commit and the landing of its signature, the signer's own reads say they have not signed. Forward: the signer's read says where their copy stands, and, after the commit, the download serves only once the recipient's copy is ready. No migration, no new route, no new event. |
| **Why** | `POST /api/v1/signing/commit` answers `COMPLETED`, while the signature is applied later by a worker (`SEQUENTIAL_PADES`: fill revision + DSS, then `RecipientSigned`). Until it lands, `GET /api/v1/signing/session` answers `status: AUTH_PASSED` — a signer who reloads is told to sign again — `GET /api/v1/signing/session/auth` answers `outcome: "PENDING"`, a value outside its published enum, and the document download serves the previous tip, without the signature the signer was just told was done. Seconds normally; hours while DSS is down and the fact sits on the `failed` transport ([BL-462](../BACKLOG.md), reported 2026-10-21: the ceremony showed the signature complete before it was stamped). |
| **Builds on** | [ADR-0034](../adr/ADR-0034-sequential-incremental-pades.md) (the signing mode elects the completion driver), [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.1 (an act is admitted at the commit, its outcome lands later) and §2.15 (what a closed envelope serves, `SEAL_PENDING`), [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.1 as amended (a signer's sealed copy stays readable after `COMPLETED`), all reused unchanged. |
| **Scope** | The signer's two reads and the download, while their envelope is open or sealing. ⛔ **Not** a way to get the copy after leaving the ceremony: that is the sibling below. |
| **Decision record** | **[ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md), drafted `Proposed` in this task** (owner, 2026-10-22; committed `Proposed` by the owner's decision; accepted by the owner on 2026-10-23). The rule it records — *after their commit is admitted, a recipient's download serves only a copy that carries their act* — is a new read rule on an **open** envelope, a case none of ADR-0059 §2.1, ADR-0070 §2.6 or ADR-0073 §2.15 covers (they govern reads once the envelope closes). The owner accepts it; this task does not. |
| **Sibling** | ⚑ The signer's copy after they leave the ceremony ([BL-188](../BACKLOG.md)): an email carrying a link to it. Not yet a task when this record was written; since 2026-10-23 it is TASK-070 on `feat/copy-link` (a read-only copy link, ADR-0088 `Proposed`), and the notices that would carry the link are a later task. This task's waiting screen must not promise that email. |

---

## 1. Why this task exists

A commit is two facts separated by a worker. At the commit, under the envelope's root lock, Envelope
**admits** the act (`Envelope::admitCommit()` sets `admittedAct = COMMIT` and `admittedAt`) and Session
completes the session; the route answers `200 {"status": "COMPLETED"}`. The recipient's **outcome** stays
`PENDING` until the signature lands: under `SEQUENTIAL_PADES`, Signature Execution's
`SignForRecipientUseCase` signs every document assigned to the recipient, appends `RecipientSigned`, and
Envelope's `OnRecipientSigned` calls `Envelope::recordRecipientCompletion()`, which sets `COMPLETED`. The
aggregate's own docblock says so: *"A commit's outcome stays `PENDING` until its signature lands."*

The signer's reads key on the outcome alone:

- `SigningSessionReader::status()` maps `RecipientOutcome::PENDING` to `SessionStatus::AUTH_PASSED`. The
  view it reads already carries `admittedAct`; it does not ask it.
- `RecipientAuthContextReader` publishes `closedLegOutcome` as `outcome->value` whenever
  `RecipientView::legIsClosed()` holds — which an admitted act makes true — so the auth descriptor's
  `outcome` reads `"PENDING"`. Its published enum is `COMPLETED | DECLINED | REVOKED | RELEASED`.
- `SigningDocumentReader` serves the tip (highest `artifact_seq`), which does not yet carry the signature.

Nothing in the signer's read says when the signature lands. The sender has one (`signed_at` per field in
`EnvelopeJsonPresenter`); the signer does not.

## 2. What already exists (reuse, do not rebuild)

- **Admission vs landing.** `Envelope::admitCommit()` (synchronous, at the commit) and
  `Envelope::recordRecipientCompletion()` (on the relayed landing). `Envelope::completesOn()`:
  `SINGLE_SEAL` elects `CompletionDriver::CONSENT` (the landing is the relayed `SessionCompleted`, seconds
  later; there are no per-recipient bytes), `SEQUENTIAL_PADES` elects `SIGNATURE` (the landing is
  `RecipientSigned`).
- **`RecipientView`** (`Envelope/Contract/View`) carries `outcome`, `admittedAct`, `admittedAt`, `role`,
  and `hasSigned()` (`outcome === COMPLETED || admittedAct === COMMIT`) and `legIsClosed()`.
- **`RecipientEnvelopeContextView`** carries `signingMode`, `closedAt`, `completedAt`, the documents
  (`DocumentView::$isSealed`, `tipCustodyId`), `readsWaitForTheSeal()` (`closedAt !== null && completedAt
  === null`) and `withholdsDocumentFromRecipient()`. Both readers are driven off this one context.
- **`SEAL_PENDING`** — `SigningSessionUnavailableException::sealPending()`, raised by
  `SigningSessionReader` once the envelope is closed and unsealed for a recipient entitled to its sealed
  record; published as *"It lifts by itself"*. `SigningDocumentReader` answers a bare 404 for the same
  case (`closedAt !== null && !isSealed`). ⚑ The envelope **closes at the admission**, not at the landing
  (`admitCommit()` → `apply($decision)`), so the last signer's commit puts them in `SEAL_PENDING` at once.
- **The non-signing committer.** `Role::signs()` is `SIGNER` only. Under `SEQUENTIAL_PADES` an `APPROVER`
  resolves to no assignments, and `SignForRecipientUseCase` appends `RecipientSigned` for them with no DSS
  call: their outcome lands, their act is never in a PDF.
- **`SigningReadersCannotDisagreeTest`** (`tests/F5Sign/Session/Application/Query/`) drives both readers
  off one context and holds the guarantee published on the download's 404: if the session read answers
  200, the 404 was not about the envelope, the credential or the step.
- **The signer's download** (`f5sign-signer`, `useDocumentDownload`) fetches `documents[].download_url`
  from the hydrated session on the done screen. <!-- OFFREPO: f5sign-signer's composable; the one fact used here is restated in this bullet. -->
- **Session's `OnRecipientSigned`** clears the signature image (TASK-053). Unchanged by this task: nothing
  here needs a column or a reactor, because Envelope already records the landing.
- **What the signer gets after leaving:** nothing. `NotifyCompletedEnvelopeRecipientsUseCase` sends a
  signer `ENVELOPE_COMPLETED` with no link (*"a signer's self-serve download is NOT IMPLEMENTED"*); BL-188.

## 3. Scope

In:

- `SigningSessionReader::status()` and the auth descriptor's `outcome` read an admitted commit as
  `COMPLETED`.
- A new member `signed_copy` on `GET /api/v1/signing/session`, computed from the read context, and on the
  commit's `200` (§4 #10).
- `SigningDocumentReader`, after an admitted commit, serves all or nothing: every document is refused while
  `signed_copy` is `APPLYING` or `AWAITING_ENVELOPE`, every readable one served once it is
  `CONTAINS_YOUR_SIGNATURE` or `FINAL`. Before the commit it serves as today.
- The `#[OA\*]` prose of the commit's 200, the session read and the download's 404; the ADR drafted
  `Proposed`; a frontend handoff for the signer.

Out:

- The copy after the signer leaves the ceremony (the sibling, BL-188).
- Anything in Signature Execution or DSS: when the signature lands does not change, only what the signer is
  told while it has not.
- `SINGLE_SEAL`'s seal timing.

Concepts re-cut: `AUTH_PASSED` (no longer covers an admitted act), `RecipientOutcome::PENDING` as read by the
signer, "Signature committed; session completed." (the commit's 200), "tip of the artifact chain" (the
download no longer serves any tip to a recipient who committed), `closedLegOutcome`.

## 4. Key decisions

1. **The reads answer from the admission, not the landing** (owner, 2026-10-22). The signer committed;
   `status` is `COMPLETED` from that moment, in both signing modes.
2. **After the commit, the signer downloads only once their copy is ready** (owner, 2026-10-22, who put it as *"only a copy that carries their act"*). Under
   `SEQUENTIAL_PADES`, once their signature is in the PDF; under `SINGLE_SEAL`, only the sealed document
   at the end. Before the commit the download serves as today: it is the route the ceremony renders the
   document from. ⚑ **All or nothing** (owner, 2026-10-22): while the copy is not ready (`APPLYING`,
   `AWAITING_ENVELOPE`) **every** document is withheld; once it is (`CONTAINS_YOUR_SIGNATURE`, `FINAL`)
   **every** document the recipient may read is served — the signer never sees one file available and
   another not. That includes a document they may read but are not assigned to sign (`readableDocumentIds`
   and the signing assignments are separate sets): it will never carry their signature, so once their copy
   is ready it is served like the rest, and during the wait it is withheld with the rest. The assigned
   documents already change together: `SignForRecipientUseCase` signs all of them in one transaction and
   appends `RecipientSigned` once, after the last.

   ⚑ **An earlier cut of this decision** (2026-10-22, same session) served an unassigned document during
   the wait too, and for a non-signing role had to special-case the empty assignment set. The all-or-nothing
   rule replaced it at the owner's request; it keys on `signed_copy` alone, so neither split survives.
3. **`signed_copy`, five values** (owner, 2026-10-22):

   | Value | When | Download |
   |---|---|---|
   | `null` | no commit admitted (and every non-committing reader while the envelope is open) | as today |
   | `APPLYING` | `SEQUENTIAL_PADES`, a `SIGNER`'s commit admitted, outcome still `PENDING`, envelope open | 404 |
   | `AWAITING_ENVELOPE` | committed, envelope open, nothing of theirs will be in a PDF before the end: `SINGLE_SEAL`, or a non-signing role | 404 |
   | `CONTAINS_YOUR_SIGNATURE` | `SEQUENTIAL_PADES`, a `SIGNER` whose outcome is `COMPLETED`, envelope open | 200, the tip, for every readable document |
   | `FINAL` | the envelope is `COMPLETED` and sealed | 200, the sealed document |

4. **The download keeps its bare 404** (owner, 2026-10-22). The session read explains it, as for
   `SEAL_PENDING`; the two readers still cannot disagree.
5. **Once the envelope closes, `SEAL_PENDING` pre-empts every value but `FINAL`, while a document they may
   see is unsealed (otherwise 200 with `AWAITING_ENVELOPE`, §4 #9's edge).** Between the close and the
   seal, while a document they may see is unsealed, the session read answers 409 `SEAL_PENDING` (it carries no
   `signed_copy`) and the download 404, as today; the rows above are for an **open** envelope. **The last signer needs nothing new** (owner, 2026-10-22): their commit closes the envelope, so the read
   answers `SEAL_PENDING` and then `FINAL`. The signer shows both waits on one screen.
6. **Computed from Envelope's read context, no column** (author, precedent-backed): the outcome, the
   admitted act, the role and the signing mode already say every value above.
7. **The envelopes in use today are `SEQUENTIAL_PADES`** (owner, 2026-10-22). The code's default is still
   `SINGLE_SEAL` (`Settings`, `CreateEnvelope`, `CreateEnvelopeRequest`), so `SINGLE_SEAL` is answered
   correctly, not left undefined, and every test of `APPLYING` or `CONTAINS_YOUR_SIGNATURE` (S-1 included)
   creates its envelope with `signing_mode: SEQUENTIAL_PADES` explicitly.
8. **`admittedAct = COMMIT` with outcome `PENDING` is the only not-yet-landed state** (census of
   `Envelope::admitCommit()`, `admitDecline()` and `recordRecipientCompletion()`, 2026-10-22): a decline
   closes `DECLINED` at its admission, and a release comes only from an unadmitted leg. So `APPLYING` and
   the `status` fix of #1 key on that pair; a new act that admits without landing would have to classify
   itself here.
<!-- OFFREPO: the signer frontend (f5sign-signer) asked for this table and treats a 409 SEAL_PENDING on the waiting screen as "keep waiting" without navigating, as its session reported on 2026-10-22; both facts are restated in this item, and nothing here depends on reading that repo. -->
9. **What a recipient whose commit was admitted reads, by envelope state** (2026-10-22, asked by the signer
   frontend; derived from `SigningSessionReader`'s guards):

   | Envelope | `GET /api/v1/signing/session` |
   |---|---|
   | open | 200, `status: COMPLETED`, `signed_copy` `APPLYING`, `AWAITING_ENVELOPE` or `CONTAINS_YOUR_SIGNATURE` |
   | closed, not yet sealed — agreed or not (the seal waits for every admitted signature to land, theirs included) | 409 `SEAL_PENDING` |
   | completed and sealed — agreed or not | 200, `status: COMPLETED`, `signed_copy: FINAL`; `envelope_outcome` says how it ended |

   ⚑ **The edge of row 2:** `SEAL_PENDING` fires only while a document the recipient may **see** is unsealed
   (`holdsAnUnsealedDocument()` over their visible documents). A recipient assigned to sign a document
   without sight of it (a real row: `signs` and `visible` are independent) and with no visible document
   at all falls through to a 200 in that window. There `signed_copy` is `AWAITING_ENVELOPE` (author,
   derived from #3: the copy is not ready and nothing is downloadable); AC-2f.

   ⛔ **`SEAL_PENDING` is the only 409 such a recipient can meet** (owner, 2026-10-22): the signer treats it
   as "keep waiting" without navigating, so any other 409 there would strand them on the waiting screen.
   Every other refusal of the reader is unreachable after an admitted commit — `STEP_NOT_ACTIVE`,
   `LEG_CLOSED`, `RECIPIENT_DELEGATED`, `ROLE_NOT_INTERACTIVE` by #8 and by the step having been active at
   the admission; `ENVELOPE_NO_LONGER_LIVE` because they signed (`withholdsDocumentFromRecipient()`) and an
   envelope someone signed is sealed before it completes. A 401 `CREDENTIAL_RETIRED` (a sender gesture) is
   not a 409 and stays reachable. AC-11 pins the census.
<!-- OFFREPO: the signer frontend (f5sign-signer) saves the session read right after the commit, as its session reported on 2026-10-22; the fact is restated in this item. -->
10. **The commit's `200` carries `signed_copy` too** (owner, 2026-10-22, asked by the signer frontend: it
   saves the read right after the commit). At the commit the copy is never ready, so it is `APPLYING` (a
   `SIGNER` under `SEQUENTIAL_PADES`) or `AWAITING_ENVELOPE` (everyone else) — and `AWAITING_ENVELOPE` when
   the commit closed the envelope, whose next read answers `SEAL_PENDING`.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| S-1 | The report replayed over HTTP: a `SEQUENTIAL_PADES` signer commits, and before `RecipientSigned` is consumed `GET /api/v1/signing/session` answers `status: COMPLETED`, `signed_copy: APPLYING`, and the document download answers 404 | owner | Acceptance | the code before this task |
| AC-1 | After an admitted commit and before its landing, the session read answers `status: COMPLETED` (members AC-1a…b) | owner | Unit + Acceptance | `status()` keyed on the outcome alone |
| AC-2 | `signed_copy` takes each value of §4 #3 in its state (members AC-2a…f) | owner | Unit + Acceptance | see *Notes on AC-2* |
| AC-3 | After an admitted commit, the download serves all or nothing: every readable document 404 while the copy is not ready, every one 200 once it is (members AC-3a…f) | owner | Unit + Acceptance | see *Notes on AC-3* |
| AC-4 | The last signer's commit reads `SEAL_PENDING`, then `FINAL` once sealed | owner | Acceptance | — (regression) |
| AC-5 | The `#[OA\*]` prose: the commit's 200 says the signature is recorded and not yet in the PDF; `signed_copy` is documented with its enum and that it lifts by itself; the download's 404 names the new reason under its guarantee | owner | review + `OpenApiSpecTest` | — |
| AC-6 | A frontend handoff for the signer in `docs/frontend-handoff/` | owner | review | — |
| AC-7 | `signed_copy` by role, over `Role::cases()`, failing on an unclassified member (members AC-7a…e) | derived — src/F5Sign/Envelope/Contract/Type/Role.php | Unit (census) | classify `APPROVER` as signing |
| AC-8 | After an admitted commit and before its landing, `GET /api/v1/signing/session/auth` answers `outcome: COMPLETED`, never `PENDING` | derived — src/F5Sign/Session/Application/Query/RecipientAuthContextReader.php | Unit + Acceptance | publish `outcome->value` |
| AC-9 | The two readers cannot disagree on the new axis: admitted commit × signing mode × role | derived — tests/F5Sign/Session/Application/Query/SigningReadersCannotDisagreeTest.php | Application | drop the new guard from one reader |
| AC-10 | The ADR recording §4 #2 is drafted `Proposed`, landed per the repo's authoring rule 7 (index row, graph, crosswalk) | derived — rule 7 | review | — |
| AC-11 | After an admitted commit, `GET /api/v1/signing/session` answers no 409 but `SEAL_PENDING`: a census over every refusal the reader raises, failing on an unclassified one (members AC-11a…h) | owner | Application (census) | add a refusal reachable after the commit |
| AC-12 | The commit's `200` carries `signed_copy` per §4 #10 (members AC-12a…c) | owner | Unit + Acceptance | answer the read's value computed after the landing |

<!-- OFFREPO: the `wt-backend` lane is a target of the f5sign-infra Makefile; its one relevant fact is restated in the line below. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane: an ephemeral stack (its own PHP
  container, Postgres cluster and broker) that mounts this worktree's tree rather than the main checkout's.
- **Reproduction first.** S-1 is written and run red against the unchanged `src/` before the fix
  (`AUTH_PASSED`, and a 200 on the download); the literal failure goes in the slice report. `async_events`
  is `in-memory://` in test, so the window between commit and landing exists in Acceptance without help:
  nothing consumes `RecipientSigned` until the test does.

**Notes on AC-1**
- AC-1a — `SEQUENTIAL_PADES`, admitted, outcome `PENDING` → `COMPLETED`.
- AC-1b — `SINGLE_SEAL`, admitted, `SessionCompleted` not yet relayed → `COMPLETED`.

**Notes on AC-2** — a `SIGNER` unless stated.
- AC-2a — no commit admitted → `null`. Sabotage: answer `AWAITING_ENVELOPE` for an open leg.
- AC-2b — `SEQUENTIAL_PADES`, admitted, outcome `PENDING`, envelope open → `APPLYING`. Sabotage: key on the outcome alone.
- AC-2c — `SINGLE_SEAL`, admitted (before and after the landing), envelope open →
  `AWAITING_ENVELOPE`. Sabotage: answer `CONTAINS_YOUR_SIGNATURE` on outcome `COMPLETED` in every mode.
- AC-2d — `SEQUENTIAL_PADES`, outcome `COMPLETED`, envelope open → `CONTAINS_YOUR_SIGNATURE`.
- AC-2e — envelope `COMPLETED` and sealed, either mode → `FINAL`.
- AC-2f — envelope closed and unsealed, a committed recipient with no visible document (signs without
  sight) → 200 with `AWAITING_ENVELOPE`, never `CONTAINS_YOUR_SIGNATURE`. Sabotage: derive the value from
  the outcome alone after the close.

**Notes on AC-3**
- AC-3a — `APPLYING` → 404. Sabotage: drop the new guard.
- AC-3b — `AWAITING_ENVELOPE` → 404, in `SINGLE_SEAL` and for an `APPROVER` under `SEQUENTIAL_PADES`.
- AC-3c — `CONTAINS_YOUR_SIGNATURE` → 200, and the bytes are the tip that carries the recipient's signature.
- AC-3d — `FINAL` → 200, the sealed document.
- AC-3e — no commit admitted → 200, the tip, as today. Sabotage: refuse every recipient whose session is
  `COMPLETED` from the session row rather than from the admission.
- AC-3f — all or nothing, on an envelope holding a document assigned to the signer **and** one they may read
  but are not assigned (authoring rule 4: the variables must disagree): under `APPLYING` both → 404; once
  `CONTAINS_YOUR_SIGNATURE`, both → 200, the assigned one carrying their signature. Sabotage: key the guard
  on the signing assignments (serves the unassigned one during the wait).

**Notes on AC-5 and AC-6** — a published guarantee changes. The download's 404 says today that, if the
session read answers 200, what is left is a document reason and only "nothing uploaded yet" is worth a
retry; the signer's retry control is built on it. Under `APPLYING` and `AWAITING_ENVELOPE` the session read
answers 200 and the download 404 for a new reason. The 404's prose, the `signed_copy` description and the
handoff all say it: **a 200 with a non-null `signed_copy` other than `CONTAINS_YOUR_SIGNATURE` or `FINAL` is
not a retry case for the download — poll the session read until it lifts.**

The handoff also carries, as recommendations the signer owns (owner, 2026-10-22):
- **Cadence:** poll fast, then back off — 2 s, 3 s, 5 s, 10 s, then every 30 s at most. The normal landing
  is seconds, so a fixed 30 s would hold a signer on the waiting screen for nothing.
<!-- OFFREPO: the signer frontend's renewal and absent-field behaviour, as its session reported them on 2026-10-22; restated in the two bullets below, and nothing here depends on reading that repo. -->
- **The credential** lasts 15 minutes; the signer's adapter already renews on a credential 401
  (`POST /api/v1/signing/session/renew`), per the signer frontend. A `COMPLETED` session keeps renewing
  (`SigningSession::renewWith()` asks `isAuthenticated()`, not `isTerminal()`), within the
  session's 12-hour absolute cap and its one-hour refresh window. Re-opening from the emailed link mints
  again only behind a neutral access gate; behind a declared one a completed session is not recovered
  (ADR-0053 §2.3), which is BL-188.
- **Deploy order:** the signer frontend treats an absent `signed_copy` as today's behaviour (its own report), so it ships first and
  the backend after it.
- **Past about 5 minutes** the screen says the signer may close the window, in neutral words. It does
  **not** promise an email: none exists until the sibling (BL-188) lands, and that task decides what the
  screen may say then.

**Notes on AC-12**
- AC-12a — a `SIGNER` under `SEQUENTIAL_PADES` whose commit leaves the envelope open → `APPLYING`.
- AC-12b — `SINGLE_SEAL`, or an `APPROVER` → `AWAITING_ENVELOPE`.
- AC-12c — a commit that closes the envelope → `AWAITING_ENVELOPE`, and the next session read → 409
  `SEAL_PENDING`.

**Notes on AC-11** — the refusals `SigningSessionReader` raises, as of 2026-10-23 (§4 #9 gives the
reasons). The census enumerates them from the reader, not from this list, and fails on one it cannot
classify.
- AC-11a — `SEAL_PENDING`: reachable (closed, not yet sealed), the one 409 allowed.
- AC-11b — `STEP_NOT_ACTIVE`: unreachable, the step was active at the admission and never un-activates.
- AC-11c — `LEG_CLOSED`: unreachable by §4 #8.
- AC-11d — `RECIPIENT_DELEGATED`: unreachable by §4 #8.
- AC-11e — `ROLE_NOT_INTERACTIVE`: unreachable, the two roles it names (`IN_PERSON_HOST`,
  `CERTIFIED_DELIVERY`) are `RoleStanding::NOT_BUILT` and refused at send.
- AC-11f — `ENVELOPE_NO_LONGER_LIVE`: unreachable for one who signed (`withholdsDocumentFromRecipient()`),
  and an envelope someone signed is sealed before it completes.
- AC-11g — 404 `SigningSessionNotFoundException` (no envelope, not a recipient, or unsent): unreachable,
  the commit was admitted on a sent envelope to this recipient.
- AC-11h — 401 `CREDENTIAL_RETIRED`: reachable (a sender gesture), and not a 409, so it is allowed.

**Notes on AC-7** — the seven roles of `Role`:
- AC-7a — `SIGNER`: the full cycle of AC-2.
- AC-7b — `APPROVER`: `AWAITING_ENVELOPE` after their commit, in both modes, then `FINAL`; never `APPLYING`
  nor `CONTAINS_YOUR_SIGNATURE` (their approval is never in a PDF; their `RecipientSigned` lands with no
  DSS call).
- AC-7c — `VIEWER`, `REVIEWER`, `EDITOR` (informational): `null` while the envelope is open, `FINAL` once
  completed **and sealed**; their reads are otherwise unchanged. A completed envelope that was never sealed
  (nobody engaged) still refuses the read with `ENVELOPE_NO_LONGER_LIVE`, as today.
- AC-7d — a recipient who declined: `null`, `status: DECLINED`, the download as today.
- AC-7e — `IN_PERSON_HOST`, `CERTIFIED_DELIVERY`: no ceremony; `ROLE_NOT_INTERACTIVE` as today.

## 6. Open follow-ups (track, don't solve here)

- **The signer's copy after they leave the ceremony** ([BL-188](../BACKLOG.md)), the sibling. While DSS is
  down a signer waits on `APPLYING` until they close the tab, and then has no way back to their copy; the
  envelope's completion email to a signer carries no link. To be written as its own task with an ADR. It decides between the two ways
  back BL-188 already names — an email carrying the copy or a link to it (at the landing, at completion, or
  both), or letting a finished signer re-pass the access gate for a read-only grant — and, with that, what
  this task's waiting screen says past about 5 minutes (owner, 2026-10-22: *"your files will reach
  you by email once they are ready"* is the intended wording if the email is chosen).
- **BL-462** is closed by this task (2026-10-23, pending merge); its row is in the backlog's *Closed* table.
- **BL-267** (the published responses that declare no `required`) is narrowed by this task: the commit's 200
  declares `required` since 2026-10-23; the rest of the row stays open.
- **BL-464** (the AC-11 census reads a ternary throw by either branch) is opened by this task; see §7.

## 7. Deviations & honest notes

### Scope
- Files the scope did not anticipate: `RecipientView::outcomeAsAdmitted()` (Envelope's Contract; the one place
  §4 #8 asks a new act to classify itself, decided in the plan), `config/packages/nelmio_api_doc.yaml` (the
  `signed_copy` schema), `docs/ddd/` (the signing-session model), `docs/adr/README.md` (ADR-0090's three rows)
  and `docs/BACKLOG.md` (this close). Each is a consequence of the rule, not an extra.

### Decisions made during implementation
- **`signed_copy` lives in Session** (`\F5Sign\Session\Application\Query\SignedCopy`), not on Envelope's
  view: it is the signer's wire vocabulary, and it keeps the Envelope Contract diff to one method.
- **S-1 was committed red** by the owner's decision (the reproduction first, against the unchanged `src/`).
- **ADR-0090 was committed `Proposed`** by the owner's decision, in slice 01, ahead of the code that realizes it.
- **The plan's AC-8 diagnosis was corrected.** The plan took the auth descriptor's published `outcome` to be
  `PENDING` at the source; the published outcome was already `COMPLETED`, and the defect was the carried
  `closedLegOutcome`, which read the landed outcome. The fix is where the value is carried
  (`RecipientAuthContextReader`, through `outcomeAsAdmitted()`), not where it is published.
- **The pre-existing unbounded `SEAL_PENDING` strings** (the session read's 409 clause (c), and the download
  404's *"409 `SEAL_PENDING` for a sealed record still being prepared"*) were bounded in slice 12 rather than
  indexed as a backlog row: this branch had not made them falser, but they were the last texts without the bound.
- **The closing review's F1 to F4** (published prose that said *"only a copy that carries their act"* where an
  unassigned readable document is served without it; ADR §7.4's false reason; two docblocks) were fixed in
  slice 12. F5 and F6 are this close's edits: BL-267, and §4 #2 / #5 above.
- **Harness: the `wt-backend` lane**, all tiers, kept up for the task; the last green run is `73f42ab6`,
  `OK (8239 tests, 92886 assertions)`. The earlier run at `9a303faa` counted 92895 assertions over the same
  8239 tests; slice 12 changed `#[OA\*]` strings and test docblocks, and the nine fewer assertions were not
  traced to a test (not a failure).

### Decisions that needed an ADR
- [ADR-0090](../adr/ADR-0090-after-the-commit-a-recipient-is-served-only-a-copy-that-carries-their-act.md),
  drafted and committed `Proposed` (owner, 2026-10-22 and 2026-10-23). It is not accepted: it stays `Proposed`
  until the owner accepts it. Its *Enforced by* and *Realized in* are filled, and the artifacts that exercise
  it are `SignedCopyTest`, `SignedCopyByRoleTest`, `SigningReadersCannotDisagreeTest`,
  `CommittedRecipientMeetsOnlySealPendingTest`, `SignedCopyAfterTheCommitHttpTest` and
  `RecipientViewOutcomeAsAdmittedTest`.

### Declared and unproven properties
- **The AC-11 census limit.** A `throw` whose expression is a ternary passes if either branch uses a spelling
  the census knows; none exists in the reader today. Home: [BL-464](../BACKLOG.md).
- AC-5 (published prose), AC-6 (the handoff) and AC-10 (the ADR's landing) are review criteria, not
  test-cited; `OpenApiSpecTest` pins `signed_copy` to `SignedCopy`.

### Debt left behind, and where it lives now
- The signer's copy after they leave the ceremony: §6 and [BL-188](../BACKLOG.md); TASK-070.
- The census limit above: [BL-464](../BACKLOG.md).
- BL-267, narrowed (the commit's 200 now declares `required`): [BL-267](../BACKLOG.md).
- BL-462: closed.
- The handoff for the signer is in Spanish, like every signer handoff, and cites `6bca4d06`, the last commit that
  changed `src/` or published text (`73f42ab6` changed prose only).

### Delegated work
- Twelve slices, 18 rounds: three `standard` slices on `sonnet` (02, 10, 11; one round each) and nine `critical`
  slices on `opus` (01, 03 to 09 and 12). Six slices needed a second round (01, 05, 06, 07, 08, 09), each to
  answer the slice review's findings. No `replicator` was used on any slice (every `## Delegated` reads "None":
  the edits were all different), so there is no replicator output to measure.

### Cost of the run
- Tokens per model are not recorded in `run.log`; the orchestrator's Phase 7 table carries them. What the log
  does hold: 12 slices, 18 rounds, no escalation of a slice's model, one closing review (verdict *changes*, 1
  finding above the cut, answered in slice 12), one fresh full-suite run at the tip.

### Infection verdict on the changed lines

Run with `make -C ../f5sign-infra wt-backend-infection src=<worktree> args="--min-covered-msi=85 --min-msi=70"`
on the `wt-backend` lane, mutating only the lines changed against `develop` (11 `src/` files, 294 lines).

- **First run (tip `88366009`):** 88 mutants, 83 killed, 0 escaped, 5 not covered (4 on changed lines, all in
  `CommitSignatureController`); covered-MSI 100 %, MSI 94 %. Verdict FAIL on the not-covered ones. The cause
  was coverage credit, not test selection: `SignedCopyAfterTheCommitHttpTest` and `OpenApiSpecTest` are
  `#[CoversNothing]` and credit no line, and three of the four mutants sat in arguments of a method-level
  `#[OA\Response]`, which is never an executed line (BL-252).
- **Fix (slice 13, `f275c608`):** a narrow `CommitSignatureControllerTest` (`#[CoversClass]`) pins the 200's
  body (closed key set; `signed_copy` read through the reader, `APPLYING` vs `AWAITING_ENVELOPE`); an exact
  `OpenApiSpecTest` pin holds the 200's `required` set and `signed_copy` enum, unpinned until then; and
  `// @infection-ignore-all` on that 200's `content:` argument removes the three mutants no test can be
  credited with. The spec dump is byte-identical before and after. Four sabotages, each red on its own
  assertion.
- **Final run (tip `f275c608`):** 85 mutants, all killed; 0 escaped, 0 not covered, 0 timed out on the
  changed lines. The tier at `f275c608`: `fast=1` OK (6787 tests, 72424 assertions); the four touched test
  classes OK (30 tests); lint, deptrac and PHPStan clean. The last full run of every tier is `73f42ab6`
  (OK, 8239 tests, 92886 assertions); `f275c608` adds two comment lines to `src/` and new tests only.
