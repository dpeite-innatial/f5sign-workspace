# ADR-0073 package: amendment texts for the join (ADR-0073, ADR-0066 §2.3, ADR-0064 §2.4)

Drafts only. Nothing here has been applied to `docs/`. Each item is the exact text to paste, in the ADR's own voice, with the
verification against the tree beside it. Refs read: `feat/deadline-bars` @ `3a837cbe` (the worktree),
`feat/step-policy` @ `b3390036` (session 1's tip when read), `feat/envelope-expiry` @ `06e35abf` (TASK-049).

Two facts found while reading that change what the join sweep owes, and are worth knowing before the items:

- **ADR-0074 does not exist on any ref** (`git grep -l 'ADR-0074' feat/step-policy feat/deadline-bars -- docs src` returns
  nothing; no local ref is named for it). Item 2 cites "ADR-0074 §2.5 (TASK-051)" as the maintainer asked; that citation is
  marked TO CONFIRM and must not go in until the record lands.
- **ADR-0064 §2.4 already carries the census exclusion of `EnvelopeClosedBySender`** (the "Amended by ADR-0073 §2.11" paragraph,
  line 215 on `feat/deadline-bars` and on `feat/envelope-expiry`). CONTRACT-CHANGES.md's bullet "exists only in the event
  docblock" is stale. Item 7 is therefore a tightening of an existing sentence, not an insertion.

---

### 1. A released member's sessions are revoked per recipient, except one whose gate still passes

- **Target:** ADR-0073 §2.8, the last-but-two bullet, verbatim:

  > - A released member's sessions are revoked, asynchronously, per recipient (and every session by
  >   `EnvelopeVoided`, as today); an informational member passes the gate again to read. A released
  >   slot can no longer be claimed. Reads follow the role, never `release_reason` or `released_by`.

  And §2.11, the clause: "Revocation hangs on `EnvelopeVoided` (as today, `LOAD-BEARING.md` §1.16
  unchanged) and on each release;". (§2.15's "their sessions are revoked (§2.11)" stays true as written: it names a recipient
  who neither signed nor is informational, whose gate does not pass.) §5 gets one new bullet (below).

- **Replacement / addition (exact text):**

  §2.8, replacing the bullet:

  > - A released member's sessions are revoked, asynchronously, per recipient (Session's `OnRecipientReleased` →
  >   `RevokeRecipientSessionUseCase`), and every session by `EnvelopeVoided`, as today — **except a member whose gate still
  >   passes, who keeps theirs on both paths** (maintainer, 2026-09-29: first for the release, then for the void). Revocation
  >   exists to stop a member *acting*; a member who still passes the gate after the close — an informational member, or one who
  >   signed — can only read, and revoking them bought nothing but harm: the re-open then published their session as `REVOKED`,
  >   telling a reader the document was withdrawn, and the renewal refused it, so they read for one access credential's life
  >   per open. ⚑ **The exemption is the gate rule itself** (§2.3), asked of Envelope when the message is consumed —
  >   never a list of roles, and never `release_reason` or `released_by` — so a release and a void cannot disagree about who
  >   keeps a session; a context that no longer resolves, or an envelope never sent, revokes (the direction that fails closed).
  >   An informational member passes the gate again to read. A released slot can no longer be claimed. Reads follow the role,
  >   never `release_reason` or `released_by`.

  §2.11, replacing the clause:

  > Revocation hangs on `EnvelopeVoided` (as today, `LOAD-BEARING.md` §1.16 unchanged) and on each release, sparing a member
  > whose gate still passes on both (§2.8);

  §5, new bullet in TASK-050's slice:

  > - **Revocation spares whoever still passes the gate, on both paths** — [`RevocationSparesReadersTest`](../../tests/F5Sign/Session/Application/Service/RevocationSparesReadersTest.php)
  >   (the one predicate), and the two use-case tests that ask it, [`RevokeRecipientSessionUseCaseTest`](../../tests/F5Sign/Session/Application/UseCase/RevokeRecipientSessionUseCaseTest.php)
  >   (a release) and [`RevokeEnvelopeSessionsUseCaseTest`](../../tests/F5Sign/Session/Application/UseCase/RevokeEnvelopeSessionsUseCaseTest.php)
  >   (a void).

- **Verified against code:** VERIFIED on `feat/deadline-bars` @ `3a837cbe`. `OnRecipientReleased` (Session/Application/Subscriber)
  dispatches `RevokeRecipientSession`; `RevokeRecipientSessionUseCase::execute()` asks
  `RevocationSparesReaders::spares($envelopeId, $recipientId, $releasedAt)` at `RevokeRecipientSessionUseCase.php:71` and returns
  without revoking on `true`. The void path, `RevokeEnvelopeSessionsUseCase.php:77`, asks the same service per live session.
  `RevocationSparesReaders::spares()` answers `RecipientEnvelopeContextView::recipientCouldPassTheGate()`
  (`(!legIsClosed && acceptsActs) || hasSigned || isInformational`), returns `false` on `EnvelopeNotFoundException` and on
  `sentAt === null`. The "REVOKED on re-open / renewal refused" rationale is the service's own docblock. The test file paths
  exist in the tree (`RevocationSparesReadersTest.php`, `RevokeEnvelopeSessionsUseCaseTest.php`; `RevokeRecipientSessionUseCaseTest.php`
  is listed by the same `rg`). The CONTRACT-CHANGES commit for this is `480faab9` (release) and `21dc9a4a` (void).

---

### 2. §2.12 extended to step deadlines: past an open step's deadline, void and close-now are refused until the sweep closes the step

- **Target:** ADR-0073 §2.12, the third bullet, verbatim:

  > - **From `expires_at`, only the sweep moves the envelope** (maintainer, 2026-09-28): a void, a
  >   close-now or a step activating after the date is refused as expired, like an act, until the sweep
  >   closes it at most a minute later. Otherwise who came first in that minute would decide the
  >   published ending — `SENDER_VOIDED` or `EXPIRED`, `SENDER_CLOSED` or `EXPIRY` — for the same facts
  >   (§2.4); measured by `ExpiryGapTest`, where allowing them changed five of ten cases.

  Insertion point: a new bullet immediately after it. §2.7's sentence "or its deadline releases the rest" needs no edit.

- **Replacement / addition (exact text):**

  > - **From an open step's deadline, the same** (maintainer, 2026-09-29): past the deadline of the step that is open, a void
  >   and a close-now are refused with a named 409, `STEP_DEADLINE_PASSED` (retry after the sweep, at most a minute), until the
  >   sweep closes the step. The reason is §2.4's, one clock over: a sender's void or close-now in the gap between the deadline and
  >   the sweep would otherwise decide the published ending — `SENDER_VOIDED` or `STEP_DEADLINE_MISSED`, `SENDER_CLOSED` or the
  >   deadline's own outcome — for the same facts. A recipient's act in that gap is refused too, as it always was: the admission
  >   compares the instant of the act with the deadline, not with whether the sweep has run, and the route publishes it as the
  >   existing `LEG_CLOSED`. **TO CONFIRM:** "and follows ADR-0074 §2.5 (TASK-051)" — the maintainer named that record, but no ref
  >   carries an ADR-0074; cite it only once it exists. ⚑ `expires_at` is checked first, so past both dates the answer is
  >   `ENVELOPE_EXPIRED`.

  (Wording note: the "`ENVELOPE_EXPIRED` first" order is what the evaluator does today for the expiry gap — it refuses on
  `expires_at` before any per-trigger rule — and the deadline refusal is to sit beneath it; confirm against session 1's commit
  when it lands.)

- **Verified against code:** **CODE PENDING (Q2).** `STEP_DEADLINE_PASSED` exists only as an `ActRefusal` case for a *recipient's*
  act: `EnvelopeEndingEvaluator::admit()` (`feat/step-policy` @ `b3390036`, line 147: `$deadline !== null && $at >= $deadline =>
  ActRefusal::STEP_DEADLINE_PASSED`) and `Step::deadlineHasPassed()`. `EnvelopeEndingEvaluator::decide()` refuses a
  non-CLOCK trigger only at `expires_at` (`ENVELOPE_EXPIRED`); nothing refuses `VOID` or `CLOSE_NOW` past a step deadline, on
  `feat/step-policy` or `feat/deadline-bars`, and no `STEP_DEADLINE_PASSED` `ProblemCode` exists on either. What is in the tree for
  the recipient half: `feat/step-policy` maps `ActRefusal::STEP_DEADLINE_PASSED` to `LEG_CLOSED` in
  `AdmitRecipientAct::translated()` (`b138a5a1`, line 67); `feat/deadline-bars` @ `3a837cbe` still passes it through as
  `$refused` (line 64), so the mapping arrives with the join. Session 1's RESUME-session1.md lists Q2 (void and close-now
  refusal, the `void()`/`closeNow()` mappings and the `#[OA]` 409s) as not yet done.

---

### 3. §2.13: a step's deadline is stored on the step at activation

- **Target:** ADR-0073 §2.13, first sentence, verbatim: "Deadline instants and `expires_at` are the source of truth." (The
  paragraph's second sentence begins "A periodic sweep — its own Symfony Scheduler schedule…".)

- **Replacement / addition (exact text):** replace the first sentence with:

  > Deadline instants and `expires_at` are the source of truth. A step's deadline is **stored on the step when it activates**
  > (`envelope.step.deadline_at`, written once by `Step::activate()` from `deadline_hours` and never moved again — maintainer,
  > 2026-09-29), not derived on every read: the funnel below can index a stored instant, whereas `activated_at + interval` is only
  > `STABLE`. ⚑ A `CHECK` holds it equal to `activated_at` plus `deadline_hours` hours — null before activation and on a step
  > without a deadline — so the instant the evaluator computes from those two columns and the one the funnel reads cannot differ.

  and extend the funnel sentence: after "asks a funnel which tenants hold due work" add "— a sent, unclosed envelope past its
  `expires_at`, or one whose open step's deadline has been reached (the envelope's `closed_at IS NULL` is part of the step branch:
  an ending leaves the step that was open open for ever) —".

  §6, TASK-050's slice, one line (paste into a new "Built by TASK-050" block; shas TO CONFIRM at the close):

  > - **The step's deadline as a stored instant, and the sweep that reaches it** — `Step::deadlineAt()`, written by
  >   `Step::activate()`; the column and its `step_deadline_at_chk` in `Version20260929102747`; the funnel widened by
  >   `Version20260929124418` (a step branch `UNION`ed with the expiry branch, its partial index, the sweep role's column grants
  >   and a `TO`-role policy), with `DbalDueClockEnvelopes::inScope()` asking the same predicate per tenant.

- **Verified against code:** VERIFIED on `feat/step-policy` @ `b3390036` (commit `b3390036`, not on `feat/deadline-bars` @ `3a837cbe`,
  which lacks it). `Step.php`: `private ?DateTimeImmutable $deadlineAt`, `deadlineAt()`, `deadlineHasPassed()`, and
  `activate()` sets `$this->deadlineAt = $this->policy()->deadlineFrom($now)` behind an `activatedAt !== null` early return.
  `Version20260929102747`: `ADD COLUMN deadline_at TIMESTAMPTZ` and `step_deadline_at_chk CHECK (deadline_at IS NOT DISTINCT FROM
  activated_at + deadline_hours * interval '1 hour')`. `Version20260929124418`: the funnel's step branch, `step_due_deadline_idx`,
  the `f5sign_envelope_clock_sweep` grants and the `step_clock_sweep_visible` policy; its docblock carries the `closed_at IS NULL`
  rationale.

---

### 4. Release reasons are judged at the deadline instant, not the sweep's

- **Target:** ADR-0073 §2.8, the bullet, verbatim:

  > - **The reason is decided at the release**, on the facts recorded then — what the platform can prove
  >   at that instant. A delivery fact observed later, even one that occurred earlier (the relay can
  >   lag, §2.17), never rewrites it.

- **Replacement / addition (exact text):**

  > - **The reason is decided at the release**, on the facts recorded then — what the platform can prove
  >   at that instant. A delivery fact observed later, even one that occurred earlier (the relay can
  >   lag, §2.17), never rewrites it. ⚑ **For a release by a deadline the instant is the deadline's, not the sweep's**
  >   (maintainer, 2026-09-29): a sweep that runs late must not change what the platform could prove when the deadline fell — a
  >   link that expired between the deadline and the sweep is `SENT_NO_RESPONSE`, not `LINK_EXPIRED`. The same holds for expiry
  >   (`released_by: EXPIRY`), whose instant is `expires_at`. **TO CONFIRM:** whether expiry is meant to follow the same rule; the
  >   maintainer's Q1 names the step deadline only.

- **Verified against code:** **CODE PENDING (Q1).** On `feat/step-policy` @ `b3390036`, `EnvelopeEndingEvaluator::clock()` passes the
  sweep's own instant `$at` to `releasePendingBlocking($current, $open, $at, ReleasedBy::STEP_DEADLINE, …)`, which calls
  `$this->reasons->reasonFor($member, true, $at)`; the deadline (`$step->deadlineAt()`) is used only to decide *whether* the step is
  due. Nothing passes the deadline as the judging instant. RESUME-session1.md lists Q1 (with a test where the sweep runs late and a
  link expires in between) as not done. Same on `feat/deadline-bars`. The `LINK_EXPIRED` / `SENT_NO_RESPONSE` example above is
  derived from §2.8's own definitions of the two reasons, not from a test.

---

### 5. `envelope_outcome` on `GET /api/v1/signing/session/auth` and on the recipient read model; visible before the gate

- **Target:** ADR-0073 §2.9 (its last sentence: "The pre-credential routes publish `RELEASED` in their `status`/`outcome`
  unions.") and §2.15's first bullet; insertion as a new paragraph at the end of §2.15 (after "This decides who is notified, not
  who may read.").

- **Replacement / addition (exact text):** new bullet at the end of §2.15:

  > - **Both recipient surfaces publish how the envelope ended** (maintainer, 2026-09-29): `envelope_outcome`, `AGREED` or
  >   `NOT_AGREED`, and `null` until the close — on `GET /api/v1/signing/session/auth` and on the recipient read model,
  >   `GET /api/v1/signing/session`, from one rule (`RecipientEnvelopeContextView::publishedOutcome()`: the outcome from
  >   `closed_at`, `null` before it, so an agreement secured while the envelope is still open is not published). It splits what
  >   `outcome` had to say twice: `outcome` names only this participation (`RELEASED`, `DECLINED`, `COMPLETED`, or `null`), and
  >   `envelope_outcome` names the envelope's result, so a released signer of an `AGREED` envelope no longer reads `REVOKED` — the
  >   document was cancelled — for want of another word. ⛔ **Published, never a read rule**: who reads is the role's and the
  >   admission's question above; nothing branches on it. ⚠ **Visible before the gate, and accepted**: `/auth` answers to the
  >   link holder alone, so a party holding a leaked link learns from the close whether the envelope was agreed. That is less than
  >   the descriptor's `document_title` already concedes (what the document is about outweighs that it finished), the link holder
  >   is the email holder, TASK-040's notices already tell the recipient `NOT_AGREED`, and `outcome` was already published on the
  >   same route.

- **Verified against code:** VERIFIED. Descriptor: `GetAuthDescriptorController` (`feat/deadline-bars` @ `3a837cbe`, line 169 `required:
  [... 'envelope_outcome' ...]`, line 173 `#[OA\Property(property: 'envelope_outcome', enum: ['AGREED', 'NOT_AGREED'], nullable:
  true)]`, line 338 `'envelope_outcome' => $auth->envelopeOutcome`); its docblock (line 115) records the 2026-09-29 decision and the
  leaked-link cost. Read model: **not on `feat/deadline-bars`** — `feat/step-policy` @ `b3390036` (`901fd813`):
  `GetSigningSessionController.php:240 'envelope_outcome' => $view->envelopeOutcome`, the schema in `config/packages/nelmio_api_doc.yaml`
  (`SigningSession` required list and `envelope_outcome` property, line ~626) and `OpenApiSpecTest` pinning both
  (`'GET /api/v1/signing/session/auth 200.envelope_outcome'`, `'SigningSession.envelope_outcome'`). Both surfaces feed from
  `publishedOutcome()` on `feat/step-policy` (`RecipientAuthContextReader.php:235`, `SigningSessionView`); on `feat/deadline-bars`
  the descriptor still spells the rule inline (`$context->closedAt === null ? null : $context->outcome?->value`, line 236) — same
  value, single home after the join. "The pre-gate route" is `/auth`; the read model sits behind the session credential, so
  "before the gate" applies to `/auth` only. The claim "TASK-040 already emails NOT_AGREED" is from the maintainer's audit note in
  CONTRACT-CHANGES.md, not re-checked here.

---

### 6. Header: "Amends ADR-0066 §2.3" — and the carve-out in ADR-0066 §2.3 itself

- **Target:** ADR-0073's header **Relates to** row. Insertion point: after "**Preserves** [ADR-0066](ADR-0066-no-recipient-acts-before-their-step.md) §2.4/§2.6 and ADR-0056 §2.2." The current text reads "**Preserves** ADR-0066 §2.4/§2.6" and no
  ADR-0066 §2.3 amendment. Also §4's ADR-0066 row, verbatim: "| [ADR-0066](ADR-0066-no-recipient-acts-before-their-step.md) | **Preserves** §2.4 and §2.6. |". ADR-0066 §2.3 gets one paragraph, after the
  paragraph "Every ceremony refusal is `SigningSessionUnavailableException::stepNotActive()`…" and before "**The census grows an axis, not a sibling.**". Its `Status`/`Relates to` follows AUTHORING.md's
  rule that an amendment is expressed in the amended ADR's Status; see the last bullet below.

- **Replacement / addition (exact text):**

  ADR-0073 header, after the Preserves clause, add: "**Amends** [ADR-0066](ADR-0066-no-recipient-acts-before-their-step.md) §2.3: from `closed_at` the ceremony routes do not ask the step." and change "**Preserves** ADR-0066 §2.4/§2.6 and ADR-0056 §2.2." to "**Preserves** ADR-0066 §2.4/§2.6, its §2.3 before the close, and ADR-0056 §2.2."

  ADR-0073 §4 ADR-0066 row:

  > | [ADR-0066](ADR-0066-no-recipient-acts-before-their-step.md) | **Amends** §2.3: from `closed_at` the ceremony routes do not ask the step (§2.15). **Preserves** §2.4 and §2.6. |

  ADR-0066 §2.3, new paragraph:

  > ⚑ **Amended by [ADR-0073](ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.15 (2026-09-29): from
  > `closed_at` the ceremony routes do not ask the step.** The step orders *acts*, and a closed envelope admits none, so once the
  > envelope is closed the question this section asks — *has the workflow reached this recipient* — is no longer the one that
  > decides who reads: the role and whether the recipient signed do (§2.15), and the seal says when. So the rows above that
  > refuse a dormant recipient — the descriptor, the read model, the bytes, the one-time-code and auth-response routes and the open
  > — refuse only while `closed_at` is null; an informational member whose step never activated (a `VIEWER` after a close-now)
  > reads the sealed copy the copy-ready notice links them to, and a blocking member of the same never-activated step is still
  > refused, by the withholding and the gate rule rather than by the step. The condition is one method,
  > `RecipientEnvelopeContextView::stepHoldsTheRecipientBack()` (`closed_at` null and the step not active), shared by the routes.
  > It is `closed_at`, not `acceptsActs()`: from `expires_at` an expired envelope that is not yet closed still holds its dormant
  > members back until the close decides who reads. Two rows are untouched: the mint (`POST /api/v1/signing-tokens`) still asks the
  > step, which is the sender-side `RECIPIENT_STEP_NOT_ACTIVE` (§2.4), and the commit routes are decided by the envelope's admission
  > (ADR-0073 §2.1–§2.2), which refuses a closed envelope before it looks at a step.

  ADR-0066 `Status`: per AUTHORING.md an amendment is recorded in the amended ADR's Status "clause saying what was amended and what
  survives"; the same 2026-09-29 sentence goes there. **TO CONFIRM** the exact Status clause with the maintainer, since ADR-0066 is
  Accepted (exercised) and its Status cell is one long paragraph.

- **Verified against code:** VERIFIED on `feat/deadline-bars` @ `3a837cbe`. `RecipientEnvelopeContextView::stepHoldsTheRecipientBack()`
  = `$this->closedAt === null && !$this->recipientStepIsActive` (line 174; the docblock at 160 states the same `closed_at` versus
  `acceptsActs()` reasoning). Its callers: `RecipientAuthContextReader.php:215` (`stepIsActive: !stepHoldsTheRecipientBack()`, feeding
  the descriptor's check `GetAuthDescriptorController.php:263`, `StartSessionUseCase.php:143`, and the `envelopeIsAlive &&
  !stepIsActive` guards of `IssueAuthChallengeUseCase.php:201`, `SubmitAuthResponseUseCase.php:131` and `DeclineSignatureUseCase.php:85`),
  `SigningSessionReader.php:233` and `SigningDocumentReader.php:160`. The mint is unchanged: `SigningTokenIssuance.php:252` asks
  `$context->recipientStepIsActive` directly. The commit route: `AdmitRecipientAct::translated()` has `ENVELOPE_CLOSED` first, and
  the evaluator's `admit()` checks `isClosed()` before any step condition. One nuance for wording: the routes with a decline
  or one-time-code use case were already skipping the step on a dead envelope (`envelopeIsAlive`); the carve-out is new for the
  descriptor, the open, the read model and the bytes. The "unconditionally" phrasing in CONTRACT-CHANGES.md is not in ADR-0066 §2.3's
  text; the table only says each route answers 409/404 "after" its neighbouring refusals.

---

### 7. ADR-0064 §2.4 census: `EnvelopeClosedBySender` is excluded

- **Target:** ADR-0064 §2.4, the "Amended by ADR-0073 §2.11" paragraph (already present, line 215), the sentence, verbatim:

  > `EnvelopeClosedBySender` and `EnvelopeExpiryExtended` (TASK-050/TASK-049) are excluded from the census on the same logic as this table's authoring-time exclusions: they are the sender's own reversible acts, and their effect already arrives as `envelope.completed`/other published facts.

  Same wording exists in ADR-0073 §2.11 ("`EnvelopeClosedBySender` and `EnvelopeExpiryExtended` are excluded, being the sender's own
  acts whose end already arrives as `envelope.completed` — the reversible direction").

- **Replacement / addition (exact text):** replace that sentence with a version that names the outcome and separates the two events
  (their effects differ: an extension has no end of its own):

  > `EnvelopeClosedBySender` (TASK-050) and `EnvelopeExpiryExtended` (TASK-049) are **excluded** from the census, being the sender's own acts: the close-now's end arrives as `envelope.completed` with `outcome: AGREED` (its `ended_by` is set, no `end_cause`), the members it released as `envelope.recipient_released` with `released_by: SENDER_CLOSED`, and an extension moves a date and ends nothing. That is the reversible direction (§2.4 above): an exclusion can be widened additively later, a premature publication cannot be taken back.

  ⚠ **Census count** (TO CONFIRM): §2.4 says "The census closes at 36" and tells the reader to derive the count from
  `rg -l 'EVENT_TYPE = ' src/F5Sign/*/Contract/Event/ | wc -l`. TASK-048/049/050 added event types (`EnvelopeAgreed`,
  `RecipientReleased`, `EnvelopeClosedBySender`, `EnvelopeExpiryExtended`, and any others), so the "Envelope, internal" row and the
  36 are stale independent of this sentence. Re-derive at the join; do not copy a number from here. Also, the row for
  `envelope.expired` ("reserved, never emitted") is already amended in the same paragraph.

- **Verified against code:** VERIFIED. `EnvelopeClosedBySender::EVENT_TYPE = 'ENVELOPE_CLOSED_BY_SENDER'`, payload {envelope_id,
  tenant_id, closed_by, occurred_at}; its docblock says "Not published to integrators (ADR-0073 §2.11, excluding it from ADR-0064 §2.4's
  catalog)". `Envelope::closeNow()` → `EnvelopeEndingEvaluator::closeNow()` builds `new Ending(EnvelopeOutcome::AGREED, null, $at, true)`
  with `ReleasedBy::SENDER_CLOSED`, so the end is `EnvelopeCompleted` with `outcome: AGREED` and no `end_cause`.
  `EnvelopeExpiryExtended::EVENT_TYPE = 'ENVELOPE_EXPIRY_EXTENDED'` (`Envelope::extendExpiry()`). `feat/deadline-bars` @ `3a837cbe`.
  ADR-0064 has no `src/F5Sign/Webhook/` tree, so this is classification only, as its own paragraph already says.

---

### 8. The ADR-0073 Status line once TASK-050 closes

- **Target:** ADR-0073's **Status** cell, currently (verbatim):

  > **Accepted (enforcement partial)** — accepted by the maintainer 2026-09-29, after [TASK-048](../tasks/TASK-048-what-an-unagreed-envelope-keeps.md) exercised §2.1 (all but the informational-commit refusal), §2.2 (all but securing-per-policy and close-now), §2.3 (all but the expiry date), §2.5, §2.8, §2.9, §2.11, §2.14, §2.15 (all but the copy-ready notice) and §2.17 on `feat/task-048-how-an-envelope-ends` (`1f4af49d`; §5/§6 below name what holds it). [TASK-049](../tasks/TASK-049-an-envelope-expires.md) then exercised §2.3's date, §2.12, §2.13 (the sweep, its schedule and role; the step-deadline slot in its funnel is TASK-050's) and §2.16 on `feat/envelope-expiry` (`ddf1ed46`, not yet merged; it joins `feat/task-048-how-an-envelope-ends` with the rest of this package). Drafted 2026-09-24 from the maintainer's decisions of that day; audited and re-cut in place nine times, on 2026-09-24/25 and 2026-09-28 (§9). §2.4 (property-tested against one clock only, not yet discriminating), §2.6/§2.7 (the step-completion policy) and §2.10 (claims bounded in time) remain Proposed, to be realized by [TASK-050](../tasks/TASK-050-a-step-says-how-much-agreement-it-needs.md), built after TASK-048 on the same branch and deployed together with it. §2.17's freezing-clocks/operator half (§2.18) stays deferred, not rejected.

- **Replacement / addition (exact text):** (shas in angle brackets are TO CONFIRM at the close; no later sha exists yet.)

  > **Accepted (exercised)** — accepted by the maintainer 2026-09-29, after [TASK-048](../tasks/TASK-048-what-an-unagreed-envelope-keeps.md) exercised §2.1 (all but the informational-commit refusal), §2.2 (all but securing-per-policy and close-now), §2.3 (all but the expiry date), §2.5, §2.8, §2.9, §2.11, §2.14, §2.15 (all but the copy-ready notice) and §2.17 on `feat/task-048-how-an-envelope-ends` (`1f4af49d`; §5/§6 below name what holds it). [TASK-049](../tasks/TASK-049-an-envelope-expires.md) then exercised §2.3's date, §2.12, §2.13 (the sweep, its schedule and role) and §2.16 on `feat/envelope-expiry` (`06e35abf`), and [TASK-050](../tasks/TASK-050-a-step-says-how-much-agreement-it-needs.md) exercised the rest — §2.1's informational-commit refusal, §2.2's securing-per-policy and close-now, §2.4 (the same facts across every clock, discriminating), §2.6/§2.7 (the step-completion policy), §2.10 (claims bounded in time), §2.13's step-deadline slot (the deadline stored on the step, reached by the sweep), §2.12 extended to step deadlines, §2.8's release reasons judged at the deadline, and §2.15's copy-ready notice and its published `envelope_outcome` — on `feat/step-policy` (`<sha>`, session 1) and `feat/deadline-bars` (`<sha>`, session 2), joined into `feat/task-048-how-an-envelope-ends` (`<sha>`) with the rest of this package and deployed together with it. Drafted 2026-09-24 from the maintainer's decisions of that day; audited and re-cut in place nine times, on 2026-09-24/25 and 2026-09-28 (§9), and amended at the join on 2026-09-29 (§2.8's sessions, §2.12's step deadline, §2.13's stored deadline, §2.15's `envelope_outcome`). §2.17's freezing-clocks/operator half (§2.18) stays deferred, not rejected.

  Two choices inside that text are TO CONFIRM, because AUTHORING.md says "Accepted means exercised, not merely agreed" and qualifies
  a partial one:
  1. **Whether the qualifier drops.** It stays `(enforcement partial)` while anything above is pending. As of these refs, Q1 (§2.8's
     reason at the deadline) and Q2 (§2.12's step-deadline refusal on void and close-now) are **not built** (items 2 and 4), and the
     stack-only items in §5 ("Unproven": a running worker consuming the `envelope_clocks` schedule) are not proven. If TASK-050 closes
     with either open, keep `Accepted (enforcement partial)` and move the sentence about them to a "remain Proposed" clause, in the
     current line's form: "§2.8's deadline instant and §2.12's step-deadline refusal remain Proposed".
  2. **The words "the same facts across every clock, discriminating".** They rest on `EnvelopeExpirySameOutcomeTest` (`8642592d`,
     600 combinations on `feat/deadline-bars`) plus `ExpiryGapTest`. §5's current "Not yet enforced" paragraph says the comparison
     "is not yet discriminating" until the step deadline exists, which `b3390036` now provides for the evaluator; whether the
     deadline-versus-expiry comparison test exists on the joined branch is not established here.

- **Verified against code / refs:** The current Status text is from `feat/deadline-bars` @ `3a837cbe` and matches `feat/envelope-expiry` for
  the TASK-049 sentence (`feat/envelope-expiry` carries `06e35abf`, later than the `ddf1ed46` the current line names — the TASK-049
  close moved it). Exercised-by claims checked in the tree: informational-commit refusal `COMMIT_NOT_OFFERED_TO_ROLE`
  (`SigningSessionStateException.php:161`, `1cc5ef0e`); close-now `Envelope::closeNow()` (`da3d3071`, on `feat/deadline-bars`);
  copy-ready notice `SEALED_COPY_READY` (`NotifyCompletedEnvelopeRecipientsUseCase`, `c8e404c4`); step policy and `send()` judging it
  (`Envelope.php:2430` `refusalsAtSend()` is now called from the aggregate on both refs, so §5's "not yet called by
  `SendEnvelopeUseCase` (BL-313)" is false); claims past a deadline (`Envelope.php:2280 stepDeadlinePassed` on `feat/step-policy`);
  stored step deadline and funnel (item 3). Not verified: any sha in angle brackets; and that session 1's tip is `b3390036` at the
  time you read this ("its tip may be ahead").

---

## Other "join sweep" bullets that touch ADR-0073, ADR-0066 or ADR-0064 text (not covered by items 1-8)

### 9. ADR-0073 §2.4: "a `LOAD-BEARING.md` entry" names the section

- **Target:** §2.4, last sentence, verbatim: "Held by a property test (every policy × veto × member-outcome combination, closed by deadline and by expiry, same outcome), by the predicate's docblock and by a `LOAD-BEARING.md` entry forbidding a special evaluation for any clock."
- **Replacement (exact text):** "... by the predicate's docblock and by [`LOAD-BEARING.md`](../LOAD-BEARING.md) §1.21, which forbids a special evaluation for any clock."
- **Verified against code:** VERIFIED that the entry exists: `docs/LOAD-BEARING.md` `### 1.21 Every clock only closes a step and evaluates it through the one predicate` on both `feat/deadline-bars` and `feat/step-policy`. The property test's name as it stands in the tree is `EnvelopeExpirySameOutcomeTest` (deadline-bars) and `StepCompletionEvaluatorTest`'s same-facts census (named in CONTRACT-CHANGES.md; not opened here).

### 10. ADR-0073 §5 and §6: stale lists once TASK-050 lands

- **Target (verbatim, §5):** "**Not yet enforced**: §2.4's same-facts property (the expiry clock now exists beside admission, but the step deadline it must agree with is TASK-050's, so the comparison across clocks is not yet discriminating); §2.6/§2.7's step-completion policy; §2.10's time-bounded claims, TASK-050's. `EnvelopeEndingEvaluator::refusalsAtSend()` is unit-tested ([`EndingSendRefusalsTest`](../../tests/F5Sign/Envelope/Unit/Domain/Service/EndingSendRefusalsTest.php)) but not yet called by `SendEnvelopeUseCase` ([BL-313](../BACKLOG.md))."
  (Verbatim, §6): "**Still pure code, not yet exercised (TASK-050's)**: `EnvelopeEndingEvaluator::refusalsAtSend()` (built, unit-tested, not called by `SendEnvelopeUseCase` — [BL-313](../BACKLOG.md)); the step-completion policy beyond D-T1's transitional informational-member mode; the step deadline."
  Also §5's heading sentence "TASK-048's slice (§2.1 minus the informational-commit refusal, §2.2 minus securing-per-policy/close-now, ... §2.15 minus the copy-ready notice, §2.17):" stays, as a record of TASK-048's slice.
- **Replacement / addition (exact text):** delete both paragraphs and add, in their place, in the shape of the TASK-048/049 slices:

  > TASK-050's slice (§2.1's informational-commit refusal, §2.2's securing-per-policy and close-now, §2.4, §2.6/§2.7, §2.10, §2.13's step-deadline slot, §2.15's copy-ready notice and `envelope_outcome`; §2.12 and §2.8 extended to step deadlines), on `feat/step-policy` and `feat/deadline-bars`:
  >
  > - **The same facts produce the same outcome across clocks** — [`LOAD-BEARING.md`](../LOAD-BEARING.md) §1.21 and the same-facts census over `StepCompletionEvaluator`, and [`EnvelopeExpirySameOutcomeTest`](../../tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeExpirySameOutcomeTest.php) (every step combination reachable without a deadline, closed by expiry as by its other closings; the census names what it drops).
  > - **The step policy is judged at send** — `Envelope::send()` asks `EnvelopeEndingEvaluator::refusalsAtSend()` and refuses with the named `STEP_*`/`ENVELOPE_HAS_NO_BLOCKING_MEMBER`/`RECIPIENT_ROLE_NOT_BUILT` conditions (closing [BL-313](../BACKLOG.md)).
  > - **The gate rule and the opening agree** — [`GateRuleParityTest`](../../tests/F5Sign/Envelope/Integration/GateRuleParityTest.php) and the row-locked opening refusal (`63981fce`), so an opening on a leg the gate no longer admits mints nothing.
  > - **What each recipient reads after the close** — `WhatEachRecipientReadsAfterTheCloseHttpTest` (role × outcome × activation), `ClosedLegAtTheGateHttpTest`, `ClosedLegReadsOnAnOpenEnvelopeHttpTest` (a released or declined member's held credential is cut synchronously on reads, `897703a6`).
  > - **Revocation spares whoever still passes the gate** — see item 1's bullet.

  §6 gets the mirror block ("Built by TASK-050 on ...", naming the aggregate and evaluator symbols, `Step::deadlineAt()`, `EnvelopeClosedBySender`, `POST /api/v1/envelopes/{id}/close`, `SEALED_COPY_READY`, `envelope_outcome`), and its "**Still pure code, not yet exercised (TASK-050's)**" paragraph is deleted, since every member of it is now exercised. Both blocks are TO CONFIRM until the branch is joined: shas, the exact test list, and whether the same-facts census file is `StepCompletionEvaluatorTest`.
- **Verified against code:** PARTLY. `refusalsAtSend()` is called by `Envelope.php` on both refs (`feat/deadline-bars` line 2439, `feat/step-policy` line 2430) and BL-313's closing commit is `a3a524b2` per CONTRACT-CHANGES.md. `EnvelopeExpirySameOutcomeTest`, `GateRuleParityTest`, `ClosedLegAtTheGateHttpTest`, `ClosedLegReadsOnAnOpenEnvelopeHttpTest`, `WhatEachRecipientReadsAfterTheCloseHttpTest` exist in the `feat/deadline-bars` tree. The claim that §1.21's named census is `StepCompletionEvaluatorTest` is from CONTRACT-CHANGES.md, unopened. §2.13's/§2.10's step-deadline enforcement tests on `feat/step-policy` (`EnvelopeStepDeadlineTest`) are in that ref, not in `feat/deadline-bars`.

### 11. ADR-0073 Status/§5/§6 wording "minus the informational-commit refusal / D-T1 transitional mode" goes stale (050 B)

Covered by items 8 and 10 (the Status sentence and both §5/§6 paragraphs). One residual: §9, the revision arc's line ~660, "the informational-commit refusal to TASK-050 beside informational members no longer..." is a history record; leave it (AUTHORING.md: keep the record of what changed). Sweep with `rg -n 'informational-commit|D-T1' docs/adr/ADR-0073*` after the edits, read for tense.

### 12. ADR-0073 §2.10 "claims bounded in time" and §5's BL-313 line (050 C)

- **Target:** §2.10 has no "Proposed" marker in its own text; the status is carried by the Status cell and §5. Nothing in §2.10 to replace.
- **Replacement:** none. §2.10's enforcement is the claim guard: `Envelope::claim…` throws `RecipientNotClaimableException::stepDeadlinePassed()` when `$step->deadlineHasPassed($now)`, comparing the instant of the claim with the deadline rather than with whether the sweep has closed the step, and `ClaimRecipientController`'s 409 says the same (`Envelope.php:2280`). That belongs in item 10's block as one more bullet: "**Claims are bounded by the step's deadline** — the claim guard compares the claim's own instant with `Step::deadlineHasPassed()`" with its test (TO CONFIRM: the test name; `EnvelopeStepDeadlineTest` on `feat/step-policy` is a candidate).
- **Verified against code:** VERIFIED on `feat/step-policy` @ `b3390036` (`Envelope.php:2246-2281`, `RecipientNotClaimableException::stepDeadlinePassed()`, `ClaimRecipientController.php:162`). Not on `feat/deadline-bars` @ `3a837cbe`, which lacks that commit.

### 13. Bullets not requiring ADR text (listed so they are not re-derived)

- 050 A (`DECLINE_NOT_OFFERED_IN_QUORUM_STEP` retired): `rg DECLINE_NOT_OFFERED_IN_QUORUM_STEP docs`; ADR-0070 is named in the sweep list. Not an ADR-0073/0066/0064 text change (ADR-0073's own text does not carry the code, checked with `rg` on the file: no hit).
- 050 D `POST /envelopes/{id}/close`, `ENVELOPE_AGREEMENT_NOT_SECURED`, `ENVELOPE_NO_LONGER_LIVE`: contract, not ADR; ADR-0073 §2.2 already describes close-now.
- S6 / LOAD-BEARING §1.5 sentence and the "commit asks the envelope before the session's terminal state" rule (LOAD-BEARING §1.16): LOAD-BEARING edits, not the three ADRs.
- "Signer Q2: `signer.role` #[OA]" and the dashboard/signer handoff rewrites: not ADR text.
- 049 leftovers on ADR-0073 §5/§6 (listing 049's enforcers): already present in the current ADR-0073 (the TASK-049 slice blocks exist).

---

## One-line status per item

1. Sessions revoked per recipient except a member whose gate passes (release and void): **verified**.
2. §2.12 extended to step deadlines (void/close-now `STEP_DEADLINE_PASSED`): **code pending (Q2)**; ADR-0074 §2.5 **NOT FOUND** on any ref (TO CONFIRM).
3. §2.13 `deadline_at` stored at activation: **verified** on `feat/step-policy` @ `b3390036` (not yet on `feat/deadline-bars`).
4. Release reasons judged at the deadline instant: **code pending (Q1)**.
5. `envelope_outcome` on `/auth` and the read model, pre-gate accepted: **verified** (read model on `feat/step-policy` @ `901fd813` only).
6. Header "Amends ADR-0066 §2.3" and the §2.3 carve-out: **verified**.
7. ADR-0064 §2.4 census excludes `EnvelopeClosedBySender`: **verified**; the exclusion already exists in ADR-0064 line 215 (tighten, not insert); the "36" count is stale, re-derive.
8. Status line after TASK-050: **drafted**; shas and the `(enforcement partial)` qualifier TO CONFIRM (Q1, Q2 unbuilt).
9-12. Other sweep bullets (§2.4 to §1.21, §5/§6 lists, BL-313, §2.10): **verified in part**, test names TO CONFIRM.

```json
{
  "file": "/var/www/html/factor5_others/f5sign/notes/adr-0073/ADR-0073-join-amendments.md",
  "refs": {"feat/deadline-bars": "3a837cbe", "feat/step-policy": "b3390036", "feat/envelope-expiry": "06e35abf"},
  "items": {
    "1": "verified",
    "2": "code pending (Q2); ADR-0074 NOT FOUND",
    "3": "verified (feat/step-policy only)",
    "4": "code pending (Q1)",
    "5": "verified (read model on feat/step-policy only)",
    "6": "verified",
    "7": "verified (exclusion already in ADR-0064 line 215)",
    "8": "drafted; shas and qualifier TO CONFIRM",
    "9": "verified",
    "10": "partly verified",
    "11": "covered by 8 and 10",
    "12": "verified (feat/step-policy only)"
  },
  "not_found": ["ADR-0074 on any ref", "STEP_DEADLINE_PASSED as a sender-side refusal on void/close-now on any ref", "release reason judged at deadline instant on any ref"]
}
```

---

## Coordinator confirmations (2026-09-29, after drafting). These override the TO CONFIRM markers above.

- **ADR-0074 exists and is Accepted**, on the local branch `feat/envelope-answers-first` (`c51b50d1`, text corrected
  in `60eb68dd`/`1f32af7f`). The item 2 citation "follows ADR-0074 §2.5 (TASK-051)" **stands**. It was NOT FOUND
  only because the draft searched deadline-bars / step-policy / envelope-expiry.
- **Q1 applies to both clocks**: the release reason is judged at `deadline_at` for a step and at `expires_at` for
  the expiry. Item 4's expiry question is resolved in that direction; item 4 stays "code pending (Q1)" until session 1
  commits it.
- **ADR-0066 Status clause** (item 6): "Amended by ADR-0073 §2.3 (from closed_at the ceremony routes do not ask the
  step) and by ADR-0074 (§2.6)".
- Still open: the shas and the `(enforcement partial)` qualifier in item 8, the ADR-0064 census count (item 7), and
  the test names in items 9–12. They are set at the join.
