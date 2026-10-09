# Step completion policy — a decline that does not void the envelope

Status: **design under discussion** (maintainer + backend session, 2026-09-23/24). Not an ADR yet; this is
the input for one. Nothing here is implemented.

## 1. The case that started it

Waybill ("carta de porte"), dev envelope `01a0c962-bcf8-72f1-9439-3416c8637928`:

| Step | Recipient | Signs + sees | Signs without seeing |
|---|---|---|---|
| 1 | Shipper (cargador) | ind-0, ind-1, ind-2, conjunta | — |
| 2 | Carrier (transportista) | ind-0, ind-1, ind-2, conjunta | — |
| 3 | Consignee A | ind-0 | conjunta |
| 3 | Consignee B | ind-1 | conjunta |
| 3 | Consignee C | ind-2 | conjunta |

`conjunta` is an acknowledgement; consignees sign it without seeing it (`signs=true, visible=false`), on
purpose. One consignee declined → under ADR-0070 §2.3 (every SIGNER is blocking) the **whole envelope was
voided**. The maintainer's requirement: consignees act independently; one consignee's refusal must not end
the envelope. Shipper or carrier refusing must still void everything. All three consignees refusing must
void.

## 2. Options considered and why they were set aside

| Option | Why not (now) |
|---|---|
| Keep ADR-0070 as is | Fails the waybill. |
| Invisible platform seal at decline time stating "X declined" | DSS 6.4 REST cannot write `/Reason` (measured, ADR-0070 §2.5); seal would be anonymous. Depends on BL-281 (custom DSS image). Explored in a separate session. |
| Per-document outcome, `required` per (recipient × document) + envelope mode `ENVELOPE / PER_DOCUMENT` | Most faithful, but two new knobs and a per-document sealing model. |
| **Agreements** as a unit (groups of documents with required parties + optional minimum) | Best long-term model; covers board minutes (3 of 5 + chair), HR packs, medical consents. Too big for now. Kept as the future direction; step policy below must stay a special case of it. |
| `on_decline: VOID/CONTINUE` per recipient | Conflates routing (what happens next) with agreement (what counts). Breaks when conditional routing (D) arrives: `on_decline: SUBSTITUTE` would lose whether the party is essential. Two sources of truth once agreements exist. |
| `required: bool` per recipient only | Needs an extra implicit rule ("a step with no signature voids") that depends on how recipients are arranged into steps — the bank-in-its-own-step case breaks. Kept as a later addition for mixed steps. |
| Implicit rule "each step needs ≥1 signature" | Changes today's behaviour for non-blocking-only steps (a CERTIFIED_DELIVERY decline would void); couples agreement to step arrangement. |
| Quorum per step as "N of M, the rest do not matter" | Maintainer rejected the framing: consignees are not interchangeable. Reframed below as a completion policy that waits for everyone. |
| Workflow/decision engine (D): transitions on outcomes | Wanted for the future (smart routing, conditional flows). Must sit *on top* of the agreement model and only read it; never decide what counts as agreed. |

Guiding separation: **agreement** (what counts as agreed) vs **routing** (who is asked next) vs **termination**
(when/how the envelope ends). Today `Role::isBlocking()` answers all three; that conflation is what makes
future conditional routing dangerous.

## 3. The design: a completion policy per step

### 3.1 Configuration (authoring, frozen at send)

| Field | Values | Default |
|---|---|---|
| `completion` | `ALL` \| `AT_LEAST n` (`n ≥ 0`) | `ALL` (= today) |
| `after_minimum` (only with `AT_LEAST`) | `WAIT_ALL` \| `GRACE(duration)` \| `CLOSE_NOW` | `WAIT_ALL` |
| `deadline` (optional) | duration from step activation | none |

- What counts: `COMPLETED` outcomes of **blocking roles** (SIGNER, APPROVER, IN_PERSON_HOST). Non-blocking
  roles (CERTIFIED_DELIVERY, VIEWER, REVIEWER, EDITOR) do not count toward the minimum. ⚠ **Corrected by
  review (§7):** they still *hold* the step as today — the live predicate
  `Envelope::advanceAfterRecipientTerminal()` waits on every member, blocking or not — so CLOSE_NOW/GRACE
  must not skip a pending CERTIFIED_DELIVERY (its opening is the legally material event).
- Explicit enum + number, never "`null` = all, `0` = optional" in one column (CLAUDE.md authoring rule 5).
- Per-recipient `required` is **deferred** until a mixed step appears (mandatory + optional in parallel).
  When added: a step succeeds when all required members completed AND at least `n` optional ones did.

### 3.2 Validation at `send()`

- `n ≤` number of counting members of the step.
- In an `AT_LEAST` step all counting members have the **same role** (otherwise an approval could satisfy a
  step with no signature).
- `after_minimum` only with `AT_LEAST`.
- The policy travels in `EnvelopeRosterDeclared` (it already carries `min_signatures`), so evidence can
  explain why an envelope with declines is `COMPLETED`.

### 3.3 Step lifecycle

```
OPEN ──(minimum reached)──► CLOSE_NOW: closed to new acts
  │                          GRACE:     timer → on expiry or when all answered: closed to new acts
  │                          WAIT_ALL:  when all answered: closed to new acts
  ├──(minimum becomes unreachable)──► envelope VOIDED (cause RECIPIENT_DECLINED, voided_by = the decliner that made it unreachable)
  └──(deadline elapses)──► minimum met → closed to new acts; else → envelope VOIDED

CLOSED TO NEW ACTS ──(every in-flight signature of the step has landed)──► COMPLETED → next step activates
```

- Members who never acted → `SKIPPED` (with a reason: grace expired / close-now / deadline), sessions
  revoked, later attempts refused with a new code (e.g. `STEP_CLOSED`).
- A member whose signature was **in flight** at closure counts as `COMPLETED` ("if a signature exists, it
  counts").
- The next step activates only after all in-flight signatures of the previous step reached the PDF — this
  preserves today's guarantee (`CompletionDriver` docblock: *"the next step cannot activate until the
  current signer's signature is the document's chain tip"*), including when a DSS call is retried or parked.

### 3.4 Decline

- `ALL` step: a blocking decline voids (today).
- `AT_LEAST` step: recorded; voids only when `signed + reachable pending < n`. Unclaimed claimable slots do
  not count as reachable.

### 3.5 Envelope ending

- `COMPLETED`: every step succeeded under its policy. Read side publishes declined and skipped recipients.
- `VOIDED`: decline in an `ALL` step, unreachable minimum, or deadline without minimum. ADR-0070 annulment
  sealing.
- `EXPIRED`: envelope expiry (BL-202).
- A document left with **no signature at all** never gets the completion seal.

### 3.6 Waybill under the design

Steps 1–2 `ALL`; step 3 `AT_LEAST 1` + `GRACE(e.g. PT72H)`. C declines → continues. All three decline →
void on the third. Carrier declines → void at once. A non-responding consignee is skipped 72 h after the
first consignee signature.

## 4. Holes found and how they are resolved

### 4.1 Concurrency: commit vs step closure (verified in code)

Today `CommitSignatureUseCase` locks the **session** row, then reads envelope/step state through
`RecipientAuthContextReader` → `EnvelopeQueryInterface` **without a lock**, checks `stepIsActive` /
`envelopeIsAlive`, commits, saves. A closure committing between that read and the save would let the
signature through; `SessionCompleted` → SignatureExecution signs the PDF, while the envelope ignores the
completion (recipient `SKIPPED`). ⚠ **Corrected by review (§7):** the sender-void window does **not** exist
today — `CommitFieldValues::record()` is called on every commit (both routes) and reaches
`EnvelopeCommandAdapter::recordFieldValues()`, which takes the root lock and refuses a terminal envelope
(`ENVELOPE_NO_LONGER_LIVE`). The step-closure race is **created** by this design (a step never goes from
active back to inactive today), not inherited.

In `SEQUENTIAL_PADES` the envelope completes a recipient on `RecipientSigned` (bytes), not on
`SessionCompleted` (`Envelope::completesOn()` declines the CONSENT driver), so at closure time the envelope
does not know who has committed.

**Proposed fix** — precedent exists: `CommitFieldValues` already calls
`EnvelopeCommandInterface::recordFieldValues()` (TASK-044), which takes the **envelope root lock** on the same
connection/transaction as the session commit (`EnvelopeCommandAdapter`). Add a method the commit always calls
(e.g. `admitSignature(recipient)`) that, under the root lock:
1. checks envelope alive, step active, step not closed to new acts — else throws and the whole commit rolls back;
2. marks the recipient "committed, bytes pending".

Closure also takes the root lock (aggregate operation) → the two serialize. Commit first → closure sees the
member as in flight and does not skip them. Closure first → commit refused before `SessionCompleted` exists.
Decline goes through the same door. The existing unlocked synchronous guards stay (LOAD-BEARING §1.16): they
refuse early with a good message; the locked check is the guarantee.

Lock order: session row → envelope root. Closure locks the envelope root and does not touch sessions
(revocation is async via relay). No cycle expected. ⚠ **Corrected by review (§7):** there is **no** lock-cycle
PHPStan rule; deadlock freedom needs a two-process test in the style of `EnvelopeConcurrentAppendTest`.
The door should **extend** `recordFieldValues`'s existing locked call, not add a second hop.

### 4.2 Late signatures after the next step

Normally impossible in practice (DSS seconds vs human minutes for the next step), but possible when a DSS
signing is retried or parked. Resolved by 4.1 + "next step activates only when in-flight bytes landed".
`SINGLE_SEAL` mode has no per-recipient revisions, so no ordering issue there.

### 4.3 Timers

`GRACE`, `deadline` and BL-202 envelope expiry are one piece of infrastructure (custodian schedule or
RabbitMQ delayed messages — the plugin is installed). Idempotent by construction if the fire is "close the
step if its deadline passed and it is still open", evaluated under the envelope lock. Open: whether business
sweeps belong in the custodian (today the closed list of *storage* sweeps under a credential nobody else
holds, ADR-0061 §2.8); precedence between step deadline and envelope expiry.

## 5. Open items

1. `StepCompletionEvaluator` exists with tests and is unused; its non-quorum branch contradicts the
   aggregate's live predicate (`docs/ddd/envelope-divergences.md` records it). Rewrite as the new policy or delete.
2. `min_signatures` column is published (migration `Version20260713000002`); replace via a new migration.
3. `SKIPPED` semantics and reason on `StepCompleted` (evidence will ask why).
4. Per-document sealing within one envelope (completion vs annulment seal per document) — change to ADR-0070 §2.5.
5. ADRs touched: ADR-0070 §2.3/§2.8 (quorum becomes the step policy), ADR-0066 (acting *after* a step
   closed), ADR-0056 (terminal page `STEP_CLOSED`), ADR-0059 (SKIPPED does not read).
6. Notifications: skipped ("no longer needed"), decliners (different completion copy), pending under GRACE
   ("X hours left").
7. Handoffs: signer (STEP_CLOSED page, decline consequence, visible deadlines); dashboard (policy authoring;
   show the 409 `code` instead of a generic error — observed 2026-09-24 with `RECIPIENT_STEP_NOT_ACTIVE`).
8. BL-202 (envelope expiry, enforced by nothing today) is a **prerequisite**: without it `WAIT_ALL` steps with
   a non-responder, a failed delivery or an unclaimed slot are zombies.

## 6. Known limits (accepted for the first cut)

- ind-2 without its consignee's agreement inside a `COMPLETED` envelope — the PDF cannot say it (BL-281);
  API/evidence only. Agreements would model it.
- Per-document decline (sign one document, refuse another: HR pack, medical consents) — not covered.
- Mandatory + optional in the same parallel step (bank beside buyer, customs inspector beside consignees,
  board with chair) — needs per-recipient `required`.
- One-way dependency between documents (financing depends on sale, not the reverse) — needs D.

## 7. Adversarial review (2026-09-24, three clean-context reviewers: concurrency, domain, evolution)

Verdict of all three: **the direction (agreement / routing / termination separated; step policy as the first
cut) is sound; the design as written is not ready for an ADR.** Deduplicated findings, verified in code unless
marked *(judgement)*.

### 7.1 Redesign needed

1. **The step policy terminates inside the agreement layer.** Unreachable minimum / deadline → `VOIDED`
   directly, which is irreversible (seal + revocation), so a later D transition (`SUBSTITUTE`, `ASK_SENDER`)
   could never act. Fix: the step emits a *"step not agreed"* fact; voiding is the **default reaction** to it.
2. **Admitted vs landed is undefined.** "Minimum reached", GRACE start, the unreachability test and the
   deadline branch all need to say whether an admitted-but-not-yet-signed signature counts. Admitted counts →
   CLOSE_NOW can skip everyone on a signature that later parks. Landed counts → commits keep being admitted
   during the DSS seconds.
3. **A parked signature wedges the step.** `SignForRecipientUseCase` rethrows `ArtifactChainConflictException`
   after `MAX_ATTEMPTS`, throws `signerAssignedNoDocument`, propagates DSS failures → retry → dead-letter. The
   member stays "bytes pending" forever; GRACE/deadline can close the step but never complete it. Needs a
   terminal verdict for a parked signature (operator replay, or failed → recount).
4. **Claimable slots break the waybill.** ADR-0057 exists for the unknown eCMR consignee and expects claims
   after the step activated (`Envelope::claimRecipient` accepts that). "Unclaimed = unreachable" voids step 3
   on C's decline while A/B are unclaimed (or at activation); "unclaimed = reachable" hangs until BL-202. Same
   dilemma for **delivery-failed** members (ADR-0065): reachable → hang; unreachable → void an envelope the
   sender could still repair via `correctRecipientContact`; skipped → evidence cannot tell "chose not to act"
   from "never received it".
5. **`AT_LEAST 0`** collides with published meaning (`Step::isQuorumStep()` treats 0/null as ALL; the key is in
   the immutable `EnvelopeRosterDeclared` payload) and is hazardous (CLOSE_NOW skips everyone at activation; a
   COMPLETED envelope with no act at all — BL-192 point 4). Recommendation: `n ≥ 1` until per-recipient
   `required` exists; the policy gets **new** payload members with a read-tolerant default (old rows = ALL).

### 7.2 Concurrency, beyond §4.1

- **Decline must also cross the locked door.** `DeclineSignatureUseCase` makes no Envelope command call; its
  effect arrives via relay (`OnSessionDeclined`). A closure in between → Session DECLINED, Envelope SKIPPED.
- **The delegated route** (`CommitDelegatedSignatureUseCase`) calls `CommitFieldValues` only under a
  condition and before the step guard; the admission check needs its own call after the step guard on both
  routes (ADR-0066 §2.6 refusal order).
- **Void vs in-flight bytes dead-letters them.** `Envelope::appendDocumentArtifact()` throws the Domain
  `EnvelopeStateException` on a terminal envelope, untranslated by the adapter (ADR-0004 leak); the append
  loads the envelope unlocked. Decide whether an admitted in-flight signature blocks the void, is refused,
  or lands under the annulment seal. `SealVoidedEnvelopeUseCase` has no chain-conflict retry.
- **The "bytes pending" marker is its own field**, written narrowly — never a `RecipientOutcome` member (rule
  5, `DELIVERY_FAILED` precedent) and never through `save()` (re-upserts document rows a DSS-bound
  `SignForRecipient` may hold → the HTTP commit would wait on DSS).
- *Suspected:* root→documents (save order) vs documents (assignment order) deadlock between a completion
  and a signing; exists today, closure adds a writer. Lock order stays clean only while revocation is async.
- SINGLE_SEAL: "landed" = relayed CONSENT completion; with workers off, steps wait on the relay.

### 7.3 Contradictions with accepted records (need a new ADR superseding parts of ADR-0070, not edits)

- **ADR-0070 §3.3's premise is gone**: an annulled document "holds fewer signatures than the blocking
  recipients" was the only offline discriminator; a COMPLETED ind-2 now has the same shape, and under
  SINGLE_SEAL (default) a refusal is invisible in the PDF. Needs explicit maintainer sign-off.
- ADR-0070 §2.2's reason for refusing `void()` at READY_TO_SEAL and §2.3's rejection of SKIPPED stop being
  true as written (keep the rules, replace the reasons). Also: while GRACE/WAIT_ALL runs after the minimum,
  the envelope is SENT, so the sender can void an agreement already reached — decide *(judgement)*.
- **`STEP_CLOSED` re-maps a pinned mapping**: ADR-0066 §2.4 sends SKIPPED to `STEP_NOT_ACTIVE` ("no new
  codes"), pinned by `SigningSessionReaderTest::closedOutcomes()` and the signer; BL-183 binds it. SKIPPED is
  invisible to the pre-credential routes, tokens cannot be revoked → a skipped member still gets billable OTPs.
  ADR-0066 §2.1 forbids widening "step active" to "step open": key the refusal on the outcome.
- `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` (published `ProblemCode`) loses its trigger — record the retirement.
- `VoidCause` has no member for a deadline void (closed published enum). `voided_by` = "last decliner" is
  arbitrary when several declined.
- `StepCompleted.is_skipped` already means *step* skipped — name the recipient-skip reason differently.
- Integrators read `envelope.completed` as "everyone agreed"; the policy is only in an internal event.
  `EnvelopeCompleted`/webhook need declined/skipped markers. `NotifyCompletedEnvelopeRecipients` mails every
  recipient, decliners and skipped included.
- Read rules: `withholdsDocumentFromRecipient` is `false` for COMPLETED/SENT for every outcome; "SKIPPED does
  not read" makes it recipient-aware for two more statuses.
- The `min_signatures` OpenAPI schema is already wrong (non-nullable, presenter emits null).
- **Timers must not live in the custodian** (unlimited retained-bucket key, no tenant scope, no transaction
  middleware — ADR-0061 §2.8). Use delayed messages on the normal bus.
- BL-192 already owns "release a party from a step's required set" and lists questions this design must answer.

### 7.4 Waybill configuration (judgement)

GRACE counts from the first signature, but consignees of a multi-drop receive goods days apart → a later drop
is skipped before its goods arrive. And "A, B decline, C silent" never voids under GRACE (it starts only once
the minimum is reached). The waybill needs `WAIT_ALL` + a step `deadline`, which depends on BL-202.

### 7.5 Future-fit caveats

- Per-recipient `required` does not merely extend §3.3: it rewrites it, and ALL / "all required + AT_LEAST 0"
  / "AT_LEAST m of m" become three encodings of one policy (rule 5).
- "Step policy is a special case of agreements" holds only if agreements can overlap on documents, carry
  several minimum pools, and void the whole envelope when one fails — which contradicts the planned
  per-document outcome.
- APPROVER-only `AT_LEAST` cannot express a veto *(judgement)*.

## 8. Maintainer decisions (2026-09-24)

1. **Unclaimed slots and delivery-failed members count as reachable** ("can still sign"). A decline does not
   void while they could still complete; the clock bounds the wait. (Resolves 7.1 #4; ADR-0057 §2.11 already
   accepted the stall, pending an expiry mechanism.)
2. **Clock = one deadline per step, counted from step activation**, for now. Per-recipient windows (from
   invitation, better for multi-drop) deferred. BL-202 envelope expiry remains the backstop.
3. **At the deadline, non-actors are released with a reason** (`NO_RESPONSE` / `UNCLAIMED` /
   `DELIVERY_FAILED`) and the step is evaluated on what it has. Released = terminal, not completed, not
   acted. This answers BL-192's four questions (see the discussion: the timer fire re-evaluates under the root
   lock; single-member steps end "not agreed"; no zero-signature COMPLETED because `n ≥ 1`).
4. **First cut — confirmed:** `ALL | AT_LEAST n` with `n ≥ 1`, wait for everyone (`WAIT_ALL`), step
   deadline. `CLOSE_NOW` and `GRACE` **deferred to a second phase** (§9). The waybill needs `WAIT_ALL`:
   `AT_LEAST 1` decides whether the step counts as agreed, not when it advances — the next step opens only
   when every consignee has answered or been released at the deadline.
5. **A step that fails emits a "step not agreed" fact; voiding is the default reaction** (room for a future
   decision engine).
6. **An admitted signature that DSS never applies (parked) keeps the step waiting until an operator replays
   it** — same as any failed signature today.
7. **Accepted:** a `COMPLETED` envelope may hold a document missing a decliner's signature; the PDF does not
   mark it in any way, only the database/API/evidence do. This knowingly gives up ADR-0070 §3.3's offline
   discriminator; the new ADR must record it as superseding that premise.
8. **Void without a single culprit** (several decliners, deadline): no `voided_by`; a new cause "the step did
   not reach agreement"; the list of decliners lives in the evidence.
9. **Read rule:** a decliner may read the sealed document of a `COMPLETED` envelope; a released (non-acting)
   member may not — same rule as voided envelopes (whoever acted reads).

Prerequisites confirmed by the review: BL-202 (clock infrastructure; delayed messages on the normal bus, not
the custodian), BL-183 (pre-credential routes must see a released outcome, or released members keep getting
billable OTPs), BL-192 (release — absorbed by decision 3, still needs its ADR text).

## 9. Second phase — deferred, not rejected: `CLOSE_NOW` and `GRACE`

Deferred by the maintainer on 2026-09-24 because no use case needs them yet (the waybill is `WAIT_ALL`), not
because they are unsound. The first cut already builds the shared machinery (locked admission door incl.
declines, "bytes pending" marker, release with reason, timers, advance only after in-flight bytes land), so
adding them is an extension, not a redesign. What they still owe:

1. **One open design decision: what counts toward "minimum reached"** at the moment of closing. Recommended:
   **landed signatures only** (bytes in the PDF); an admitted-but-parked signature must never close a step.
   Cost: commits keep being admitted during the seconds DSS takes — they count as in-flight, not released.
2. **The closure race becomes the hot path.** It fires on the landing of a signature, exactly while parallel
   members are signing. Needs two-process tests: minimum-reached vs commit, vs decline, vs admitted-then-parked.
3. **Release becomes a main path, not an edge case:** members are released mid-ceremony (open session, OTP
   just sent) → polished signer "no longer needed" page, a notification to released members, and BL-183 is
   mandatory (no billable OTP to a released member).
4. **`GRACE` needs a timer armed mid-flow:** a new fact ("step minimum reached") and a reaction scheduling
   the delayed message; plus the "X hours left" notice, which has no sender today (reminders have no consumer).
5. **Validation matrix at `send()`:** `after_minimum` only with `AT_LEAST`; `GRACE` vs step deadline ordering;
   `CLOSE_NOW` with a deadline.
6. **Evidence:** the release reason must distinguish `CLOSED_AT_MINIMUM` / `GRACE_EXPIRED` from the first
   cut's deadline reasons.

Home when the ADR lands: its "deferred" section plus a `docs/BACKLOG.md` row in the backend repo (this note is
internal and not delivered, so the repo must not point here).

## 10. Envelope expiry and clocks (BL-202) — maintainer decisions 2026-09-24

**Mechanism (design):** deadlines live in the database, never only in the broker — `envelope.expires_at`
(exists) and a step `deadline_at` computed and frozen at activation. A **periodic sweep** (its own Symfony
Scheduler schedule consumed by the normal worker — **not** the custodian, which holds the privileged storage
credential) lists due work across tenants through a funnel function on the `Version20260908000004` pattern,
then dispatches per-envelope commands (`ExpireEnvelope`, `CloseStepAtDeadline`) in tenant scope. Each command
re-checks "still due and still open" under the envelope root lock → idempotent, self-healing after a missed
run; precision = sweep interval. RabbitMQ delayed messages rejected for day/week timers: Symfony's AMQP delay
creates one queue per distinct delay, the delayed-message plugin keeps pending messages unreplicated on one
node and is not meant for long delays, and a lost broker-only timer means an envelope that silently never
expires.

**Semantics:** only a `SENT` envelope expires (`READY_TO_SEAL` already holds agreement, ADR-0070 §2.2).
Expiry is two-phase like step closure: closed to new acts (the locked admission door already refuses a
terminal envelope), then ends once in-flight bytes landed — otherwise they dead-letter (review §7.2). Step
deadlines act first; envelope expiry is the backstop. `send()` may check that the sum of step deadlines fits
in the envelope's life.

Decisions:

1. **An expired envelope ends `VOIDED` with cause `EXPIRED`** and goes through exactly the decline/void flow
   (annulment seal of what is signed, ADR-0070 §2.6 read rule, session revocation). Consistent with ADR-0070
   §2.1 (one ending without agreement, the cause says why). **`EnvelopeStatus::EXPIRED` is retired** from the
   enum. `VoidCause` gains `EXPIRED` and the step-not-agreed cause (published enum → dashboard handoff).
2. **Existing `SENT` envelopes past their hard-coded +30-day date simply expire** on the first sweep. No
   backfill. (No void notification exists yet — TASK-040 is not built — so this causes no mail burst; re-check
   if TASK-040 lands first.)
3. **The sender chooses the expiry at authoring (default 30 days, with a maximum) and may extend it after
   send.** Extension: only while `SENT`, only forward, bounded by the maximum, recorded as its own fact.
   ⚠ This amends the model's rule that settings freeze at send (`Settings::$expiresAt`) and must be checked
   against ADR-0062's promotion predicate and ADR-0061's retention clocks, which read `expires_at`.
4. **The other status members without a writer** (`SEALING`, `CORRECTING`, `ROUTING_FAILED`,
   `SEALING_FAILED`) are **out of scope**; BL-202's row is updated to say they remain open.

### 10.1 Extension and document promotion (reviewed 2026-09-24)

Four readers of `settings_expires_at`, all in the storage lifecycle (ADR-0062): `DbalPromotableDocuments`,
`DbalAbandonedUploads` (deletes the originals of unsigned abandoned envelopes), `DbalUnpromotedDocuments`, and
the custodian funnel in `Version20260908000004`. All treat `voided_at IS NOT NULL OR settings_expires_at <
now()` as "the chain will not grow", which silently relies on **expiry being monotonic**: once passed, passed
forever. An extension landing between the instant passing and the expiry sweep voiding the envelope could
revive an envelope whose original the discard sweep already deleted.

Maintainer decisions:

1. **Extension is refused once `now ≥ expires_at`**, checked under the envelope root lock, even if the sweep
   has not voided it yet ("if it is expired by date, it is expired"). This keeps expiry monotonic, so the four
   readers stay correct untouched. The rule is on the date, not on `SENT`, because the envelope is still
   `SENT` during that window.
2. **Expiry is a duration counted from the envelope's first send** (resolved to a date at `send()`), not from
   draft creation — today `CreateEnvelopeController` sets `+30 days` at creation, so a draft that waits 25
   days goes out with 5. A later re-send never resets it.
3. **Default 30 days; the total reachable is capped at 180 days from first send** (the cap applies to the
   initial choice and to the sum of extensions); several extensions are allowed until the cap is reached.
4. **Signing links (fixed 7-day `StoreBackedSigningTokenIssuer::LIFETIME`) are left as they are for now**,
   even though a 15-day step deadline or an extended envelope outlives them (a resend mints a new link).
   Record it in the ADR as a known limit.

Accepted side effects, to be written into the ADR so nobody reads them as defects: a document may be
promoted twice around expiry (the daily promotion runs between the date passing and the annulment seal; the
`conserved_artifact_seq` leg re-promotes the new tip — one extra retained object); the conservation ceiling
is anchored at send (`ConservationCeiling`, ADR-0061) and is not moved by an extension; the
`settings_expires_at` leg stays as ADR-0062's catch-all (still needed for `READY_TO_SEAL` envelopes past
their date, which do not expire).

## 11. What is kept after an envelope ends without agreement (TASK-048 input) — 2026-09-24

Found while reviewing expiry vs promotion: `SealVoidedEnvelopeUseCase` annulment-seals **every** document with
bytes, including ones nobody acted on; the seal then counts as "not an upload", so promotion retains for years
a document no person touched (contradicting ADR-0062 §2.5), and the daily `discard-abandoned-uploads` (01:05)
can delete an original **before** its pending annulment seal lands (DSS slow / workers off) → the seal parks
unrepairable. Promotion runs **hourly** (`CustodianSchedule`), discard daily. Separately, double promotion
(pre-seal tip then sealed tip) already happens today for any void whose seal is slower than the next hourly
promotion, because `voided_at` is written before the asynchronous seal.

Maintainer rule (2026-09-24): **envelope-level, not document-level.** An envelope that ended without agreement
in which **nobody acted** → no annulment seal, originals discarded. If **anyone acted** → every document of
the envelope, signed or not, is sealed, promoted and kept for the legal period ("people can still claim").

Refinements agreed:
- **"Acted" = signed (`COMPLETED`) or declined (`DECLINED`)** — `RecipientOutcome::hasActed()` — **or admitted
  by the locked admission door** (§4.1). A decline is legally material (the refused document proves what was
  refused).
- **Asked of the recipients, never of the PDF.** Under `SINGLE_SEAL` (the default) consents add no revision, so
  an artifact-based test reads "nobody signed" and would discard what people consented to; today only the
  indiscriminate annulment seal saves it, by accident.
- **Race closed by the admission marker:** today a commit/decline accepted by Session just before a void is
  relayed after it and ignored by the terminal envelope (convergence no-op), so `envelope.recipient` can say
  "nobody acted" while someone did. The admission door records the act on the envelope in the same
  transaction as the act. ⛔ **Ordering constraint: "do not seal when nobody acted" must not ship before the
  admission door covers commit, delegated commit and decline** — otherwise today's accidental protection goes
  and the hole opens.
- **Existing data:** envelopes voided before the deploy may hold raced acts their recipient rows do not show.
  Apply the new discard rule only to envelopes voided after the deploy (or reconcile first); keep "a SEAL
  exists → promote" so documents already annulment-sealed are promoted rather than stranded in staging.

Mechanics (accepted by the maintainer): a new migration supersedes the two published funnel functions of
`Version20260908000004` (`CREATE OR REPLACE`, down() restores); the custodian role gets a column-scoped grant
on `envelope.recipient (envelope_id, tenant_id, outcome)` only — never name/email/phone — plus a custodian
visibility policy narrowed to acted rows, with a measured "permission denied" test for the PII columns; the
per-tenant PHP reads (`DbalPromotableDocuments`, `DbalAbandonedUploads`) change in lockstep (a parity test);
`SealVoidedEnvelopeUseCase` learns "anyone acted" through `getContextForSE`. Promotion's "chain will not grow"
becomes seal-first: a `SEAL` on the document, or voided/expired **and** older than a margin (proposed 7 days,
pending confirmation); `report-unpromoted`'s 2-hour alarm must follow that margin.

Amends: ADR-0070 §2.5 (seal only when someone acted), ADR-0062 §2.4/§2.5 (acted, not artifact; seal-first).

## 12. Audit of ADR-0073 + TASK-048/049/050 (2026-09-24) — maintainer decisions, one by one

- **D1 Veto — option B.** `AT_LEAST n` gains a veto switch, **off by default**: when on, any decline in the
  step makes it not agreed (void, `STEP_NOT_AGREED`); silence still does not block. Waybill keeps it off.
  Board written resolutions and two-parent consents turn it on. Per-recipient veto is deferred with mixed
  mandatory/optional members (same piece).
- **D2 Precedence and the envelope lifecycle (decided 2026-09-25, after several re-cuts in discussion):**
  - **The admission instant decides, for every cause.** The ending is decided once, under the root lock, at the
    request (sender void, blocking decline, veto, step not agreed, expiry, step deadline), from the acts already
    admitted: if they complete the agreement the outcome is AGREED (a sender void is then refused with a named
    code, as READY_TO_SEAL refuses it today); otherwise NOT_AGREED with its cause. From that instant the
    admission door refuses every new act.
  - **Lifecycle vs result are separate.** Status = phase only: `DRAFT → SENT → READY_TO_SEAL → COMPLETED`.
    `READY_TO_SEAL` now means "decided, waiting for the seal" whatever the result; admitted in-flight signatures
    land normally there (the envelope is not terminal), then **one** seal (identical for both results, no
    /Reason), then `COMPLETED` = "lifecycle ended". **`VOIDED` is retired as a status** (as `EXPIRED`).
  - **`outcome: AGREED | NOT_AGREED`**, written at the decision and never changed; documented as an open enum
    (`PARTIALLY_AGREED` arrives with agreements, plus a per-agreement outcome; no `CLOSED` status needed then).
  - **`end_cause`** (renamed from `void_cause`): `SENDER_VOIDED | RECIPIENT_DECLINED | STEP_NOT_AGREED | EXPIRED`,
    with the voiding party where there is one. Who ended it is never folded into `outcome` (rule 5).
  - Consequences: `readsWaitForTheSeal()` becomes unnecessary (COMPLETED ⇒ sealed); storage sweeps key on
    COMPLETED so nothing is promoted before its seal (double promotion gone); no exception for signatures
    landing on a terminal envelope. Facts `EnvelopeCompleted` (agreement) / `EnvelopeVoided` (no agreement)
    keep their historical meaning in the log.
  - **Mandatory rule-1 sweep:** every read of `COMPLETED`/`VOIDED`/`void_cause` across src, tests, migrations,
    docs, config, the dashboard and the signer is reclassified as phase or result, plus a test that nothing says
    "signed" from `COMPLETED` alone. API docs state `COMPLETED` = lifecycle ended, result in `outcome`.
  - **Adjusted (2026-09-25): `READY_TO_SEAL` keeps today's technical meaning** — "every admitted signature is on
    the PDF, the seal can start". The decision writes `outcome`, `end_cause` and `decided_at` and closes the
    admission door while the status stays `SENT`; `READY_TO_SEAL` is written when the last admitted signature
    lands (or at the decision if none was in flight); the sealer and `EnvelopeReadyToSeal` are unchanged.
    Because the status reads `SENT` in that window, **one predicate `acceptsActs()` (= `SENT` and no decision)**
    replaces every "is it SENT?" check on routes that admit or prepare an act (session open, OTP issuance, link
    minting, claim, correction, resend), with a test that every such route uses it.
- **D3 A signature that never lands — option 4, corrected:** every DSS call (signatures and seals) retries on
  its own with backoff and is not parked for a transient failure; only non-retryable errors park. **Alarm when an
  envelope has been decided for more than 2 h without being sealed** (measured from `decided_at`), visible on the
  read side as "seal pending since…". A **DSS outage closes nothing** (a seal needs DSS; `COMPLETED` ⇒ sealed).
  A **permanently failing single signature with DSS up**: `NOT_AGREED` → after **72 h** seal without it and
  record in evidence "act admitted at T, signature not applied"; `AGREED` → never closed without it, the alarm
  escalates. Note: acts need no DSS (`CommitSignatureUseCase` makes no DSS call), so signers keep signing and
  envelopes keep being decided during an outage; only stamping and sealing wait.
- **D4 Non-blocking roles at the deadline — option C:** informational roles (`VIEWER`, `REVIEWER`, `EDITOR`) never
  decide agreement (they hold the step until they answer or the deadline releases them; a release is recorded
  and the step proceeds); `send()` requires at least one blocking member per envelope (an information-only
  envelope asks nobody to agree); `CERTIFIED_DELIVERY` counts as required in its step (released unopened →
  step not agreed, `STEP_NOT_AGREED` — honest "not delivered"; it cannot complete today, being non-interactive).
  `IN_PERSON_HOST` (blocking, not built, can never complete) is refused at `send()` until built — recommended
  alongside C and not contradicted by the maintainer.
- **D5 Release reasons — option B:** a **24 h minimum** step deadline; `NO_RESPONSE` only when the invitation is
  recorded as delivered and the link was still valid at the deadline, or the recipient opened a session; else
  a neutral **`NOT_REACHED`**; `UNCLAIMED` and `DELIVERY_FAILED` unchanged. API docs advise a resend when a
  step deadline outlives the 7-day link. **BL-306** added: automatically re-invite (new link or reminder) when a
  link expires unopened while its envelope and step are open.
- **D6 Opening counts for retention — option B:** a recipient who passed the access gate and opened their session
  counts as "someone acted" **for keeping and conserving only** (not for agreement, reads or outcome). Covers
  pre-contractual information the consumer opened; an envelope nobody opened is still discarded. **BL-307** added:
  a per-envelope "conserve always" opt-in for envelopes meant to prove what was sent (notices, offers).
- **D7 Internal rejections — option A:** any act, internal or external, keeps and conserves the envelope. The
  platform cannot tell internal members apart (a role does not say it), erring toward keeping is the safe
  direction (an internal rejection can be the audit evidence a company needs), and minimization is governed by
  the tenant's retention clock. A shorter clock for these is forbidden by ADR-0062 §2.6. An `internal` flag is
  recorded as a possible future request, not a backlog row.

## 13. Miguel's `feat/evidence-audit` (2026-09-25)

Maintainer: our branch goes **on top of** it and governs; work stays **disjoint** for now — nothing edits that
branch. When it reaches `develop`, `feat/ending-without-agreement` integrates `develop` and adapts its
assumptions (recorded in TASK-048 §6): terminal facts as "over" (`EndedStream::TERMINAL_TYPES`), `void_cause`
read verbatim from `EnvelopeVoided`, acts `Signed`/`Declined` only, `TrailJson` `kind: VOIDED`. Open question
for the maintainer: record `EnvelopeCompleted`/`EnvelopeVoided` at the lifecycle end (recommended — keeps that
branch's "terminal = final" assumption true and no in-flight signature is missed) or at the decision. The
event keeps the key `void_cause`; `end_cause` is the column/API name only. That branch has not integrated
`develop` since TASK-046 (its `EnvelopeStatus` still has `DECLINED`).

## 14. Second review round (2026-09-25) and the second re-cut

spec-lint passed on all three tasks; spec-claims passed on TASK-048/049 (all ~40+ present-tense claims true) and
failed on TASK-050 (`NO_RESPONSE` rested on `DELIVERED`, which nothing writes). Two auditors on the re-cut found
the core mechanism wrong in two places and several gaps. Maintainer decisions:

- **A2 — agreement secured apart from closing.** `agreed_at` (outcome AGREED, void refused) vs `closed_at` (no
  more acts). Pending members of the last step keep acting after agreement is secured — the waybill's consignees
  sign on their own schedule, a courtesy copy is opened, a veto can still be cast (with veto, agreement is secured
  only at the step's close). Endings without agreement settle and close at once.
- **B4 — release reasons name recorded facts:** `OPENED_NO_ACT`, `SENT_NO_RESPONSE`, `NOT_REACHED`,
  `DELIVERY_FAILED`, `UNCLAIMED`; "delivered" never asserted (no writer until ADR-0065's receipt seam).
- **C2 — `CERTIFIED_DELIVERY` refused at `send()` until built**, like `IN_PERSON_HOST`; its "required in its step"
  rule stays written for then.

Technical corrections applied: the step predicate counts admitted signatures; admission re-checks every
precondition under the lock (step active and deadline, leg open and not admitted, credential not retired); one
clock (`clock_timestamp()` under the lock); narrow writes and `lock_timeout` for everything under the root lock;
`acceptsActs()` = SENT ∧ not closed ∧ before expiry, unlocked on token routes, census includes `envelopeIsAlive`;
non-actors lose reads and sessions at closing (internal fact), actors wait for the seal, read after COMPLETED;
"acted" (reads) vs "engaged" (keeping) as two named predicates; seal-or-not and discard wait for the relay past
`closed_at`; signing on its own transport and worker with bounded retries (DoS/poison findings); full per-status
row migration with a zero-row assertion and drained queues; `READY_TO_SEAL` writer defined; unpromoted alarm
re-keyed; expiry releases never-activated steps' members; per-recipient revocation async; census includes
migrations and the stale docblocks; text fixes (sibling wording, `recipientStepIsQuorum`, `terminalOutcome()` as
new plumbing, the LOAD-BEARING pointer, BL-290 scope, no re-send, harness needs, infra-dependent bar).

## 15. Third review round (2026-09-25)

spec-lint passed on all three tasks with no warning; spec-claims failed on each (relay checkpoint not comparable
to an instant; link minting guarded contrary to `SigningTokenIssuance`'s documented reservation; the database
clock not pinnable in tests; link validity not readable — the token table is deliberately non-enumerable); the
auditor found the access gate closed to recipients who acted, `save()` left in ~11 existing root-lock writers,
three wordings of the securing rule, and a parked earlier-step signature voiding in-time acts.

Maintainer decisions: **1c** a parked admitted signature freezes the envelope's clocks (deadlines and expiry) with
an operator alarm; **2b** a sender may close now an envelope whose agreement is secured (`SENDER_CLOSED`);
**3a** a scanner that runs the page's scripts counts as engaged — checked: the signer is a client-side app
(`ssr: false`), the opening is its own POST `/signing/session`, so a plain fetch of the link records nothing;
**4a** link validity = last invitation `SENT` + fixed lifetime, with **BL-309** for a recorded "link issued" fact.

Technical corrections: access-gate routes follow the read rule; link minting left unguarded (its own reserved
decision); every post-send root writer enumerated and narrow; the opening recorded synchronously on the recipient
row (replaces the impossible relay wait) and bounded by `closed_at`; one securing rule evaluated at admission,
activation and close (a courtesy-copy-only last step no longer blocks securing); `app_now()` pinnable only in
tests; the new definer role created by infra; migration fixes (`completed_at` from the log, `ready_to_seal_at`,
seal instants, no second `EnvelopeVoided`, post-deploy re-drive, `DECLINED` dropped from the zero-row list).

## 16. Fourth review round (2026-09-25)

spec-claims: TASK-049 passed (app_now() feasible on the ConnectionTenantScope precedent; infra role claims true);
TASK-048 failed on an incomplete root-writer list (decline, delivery-sent, auth unlock, access-code reset);
TASK-050 failed on `UNCLAIMED` being unreachable (a slot is never invited, so `NOT_REACHED` matched first — a
regression of round three). The auditor found the gate rule stated two contradictory ways, an unbounded freeze,
link validity skewed by access-code sends and integrator mints, and `app_now()` steerable if shipped as one body.

Correction to the record: the auditor's premise that "today an ended envelope refuses every read" is false —
`withholdsDocumentFromRecipient()` withholds nothing on `COMPLETED` and only from non-actors on `VOIDED`, so
re-opening an ended envelope to read (with a link-only gate, as a bearer) already exists; the design narrows it.

Maintainer decisions: the operator resolves a parked signature (retry, or declare not applicable →
`TECHNICAL_FAILURE` when not secured; a secured agreement completes with the signature recorded as not
applied); frozen time is given back (deadlines, expiry and the 180-day cap shift); **only signers read the
sealed document after the end** — decliners and released members do not (narrows ADR-0070 §2.6; no backlog row
for a pre-decline copy, by the maintainer's choice); **close-now is the sender's decision whatever is pending**
(it cannot pre-empt a veto nor undo an agreement; `SENDER_CLOSED` records who ended the leg) — the per-step
`early_close` setting was proposed and dropped.

Technical: one gate predicate — (leg open ∧ acceptsActs) ∨ (signed ∧ closed); `UNCLAIMED` before `NOT_REACHED`
in activated steps; link validity from invitation-purpose `SENT` only, integrator-minted links read
`NOT_REACHED`; `app_now()` two bodies (production reads no setting; test body installed by `init-test.sql`),
pins restored in `finally`; a recorded parked state; the root-writer set held by a census; the recipient-row
lock and `SubmitAuthResponse`'s own transaction named as new shapes; the close takes recipient locks before
reading `closed_at`.

## 17. Full audit (2026-09-25) and the scope decision

A full audit of the whole proposal at 725e8964 (four clean-context auditors: state machine, security and
concurrency, real use cases, compatibility and contracts) found: expiry and step deadline giving opposite
outcomes; unreached members counting as "no objection" in veto steps; courtesy copies delaying the end or
voiding via later steps; the freeze/operator machinery freezing the waybill on ordinary contention, weaponisable
with a void, operator without authentication; `EnvelopeVoided` changing meaning when recorded at the end; the
access-gate rule locking out a finished signer while the envelope is open (ADR-0056 §2.2); undeclared
contradictions with LOAD-BEARING and the Never list (429 retryable); many published-contract gaps; bookkeeping
gaps; a pre-existing relay stall from DSS calls inside a transaction.

Maintainer decisions:
- **Miguel's `feat/evidence-audit` adapts to this branch** (it was designed before); ADR-0073 declares what it
  amends in ADR-0072 and TASK-048 §6 lists everything that branch must adapt; new ADRs on that side as needed.
- **Scope = option C**: blocks 1–5 now — step policy, admission, expiry, what is kept, **and the new lifecycle**
  (`COMPLETED` = ended, `outcome`, `end_cause`; it must happen before production). **Block 6 (freeze + operator
  powers + 72 h auto-seal) is deferred** to its own ADR. Minimal parked handling instead: the act counts from
  admission; the seal waits for admitted signatures; a parked one retries and alarms and is replayed as today; no
  automatic seal without it, no "not applicable", no freeze.
- **D2 Ending facts (2026-09-25):** three facts, one meaning each (pre-production, so meanings may be adjusted):
  `EnvelopeAgreed` (new, at `agreed_at`: agreement exists, a void is refused from here); `EnvelopeVoided` (at the
  decision of an ending without agreement — its meaning and timing unchanged from today, carrying the cause and
  the party); `EnvelopeCompleted` (at `COMPLETED`, both outcomes, carrying `outcome`, `end_cause`, `agreed_at`,
  `closed_at`, declined and released recipients — now means "lifecycle ended", matching `status: COMPLETED`; old
  events were all agreed and sealed, read with `outcome` absent as `AGREED`). Revocation hangs on `EnvelopeVoided`
  and per-recipient release; sealing on `EnvelopeReadyToSeal` for both outcomes; evidence and promotion on
  `EnvelopeCompleted`. The earlier "record both facts at the end" decision is superseded. Name `EnvelopeAgreed`
  proposed (pending the maintainer's confirmation of the name).
  Name `EnvelopeAgreed` confirmed by the maintainer (2026-09-25).
- **D3 Expiry vs step deadline — option A:** expiry is the last deadline — it releases every pending member
  (never-activated steps' members `NOT_REACHED`), evaluates the open step with exactly the deadline's rule, and
  ends `AGREED` if that yields agreement with no later step outstanding, else `NOT_AGREED` / `EXPIRED`.
  **Principle to write into the repo (maintainer): the same facts produce the same outcome — no clock decides
  agreement; every clock only closes a step and evaluates it with the one rule.** Homes: an ADR-0073 section
  naming it; a property test in TASK-050 (closing by deadline and by expiry give the same outcome for every
  policy × veto × member-outcome combination); the single step predicate's docblock; a LOAD-BEARING.md entry
  ("never add a special evaluation for expiry or a new clock").
- **D4 Unreached members in a veto step — option B:** in a step with veto, a member released as `NOT_REACHED`,
  `DELIVERY_FAILED` or `UNCLAIMED` makes the step not agreed (they never had the chance to object — the legal
  premise of a written board resolution or a two-parent consent), with its own cause detail ("not reached") so
  the sender knows to correct the contact and repeat; `OPENED_NO_ACT` and `SENT_NO_RESPONSE` count as having had
  the chance. Inside the veto semantics, not a separate setting.
- **D5 Informational members — option B:** informational members (`VIEWER`, `REVIEWER`, `EDITOR` — read-only or
  unable to submit today, BL-271) **never hold a step**: the step closes when its blocking members are done under
  its policy; an informational-only step activates, notifies and closes at once. They may open while the envelope
  is open; at the end they receive the sealed copy; one who never opened is released with a reason of its own
  (e.g. `NOT_REQUIRED`, "not awaited"), not "no response", and **keeps the right to read the sealed copy** — the
  read rule widens to signers + informational recipients. A sender who wants to wait for a review uses a blocking
  role (`APPROVER`); the API documentation says so. (Technical fix alongside: an informational-only last step no
  longer leaves a void window — the agreement is evaluated when the previous step is complete by admission.)
- **D6 End causes — option B:** `end_cause` = `SENDER_VOIDED` (party) | `RECIPIENT_DECLINED` (party; a blocking
  decline in an `ALL` step) | `RECIPIENT_VETOED` (party; a veto in an `AT_LEAST` step) | `MINIMUM_UNREACHABLE` |
  `STEP_DEADLINE_MISSED` | `MEMBER_NOT_REACHED` (D4) | `EXPIRED`. `STEP_NOT_AGREED` is retired before it ever
  existed in code. Each cause leads to a distinct remedy; a veto is attributed like a decline.
- **D7 No remedy after agreement is secured — option A:** once `EnvelopeAgreed` exists the agreement is undone only
  outside the platform (a rescission signed by the parties, or legal means); the platform supplies the proof. The
  ADR says so explicitly (noting that `AT_LEAST n` secures at the n-th signature, earlier than today's
  `READY_TO_SEAL`), and the API advises an access code — not the link alone — for recipients who matter. A dispute
  annotation (no outcome change) could come later; no backlog row.
- **D8 Delegated decline — option A:** still deferred (ADR-0070 §2.8), now declared in ADR-0073 too. A delegated
  (`MACHINE_KEY`) member who never acts is released with a reason of its own, `DELEGATED_NO_ACT`, never
  `NOT_REACHED`, and counts as reached for D4 (the integrator is their channel), so their silence never fails a
  veto step with a false cause. Checked on the dev waybill: the consignees are claimable but sign on the platform
  (`SIGNING_PLATFORM`); only the shipper (step 1, `ALL`) signs through the integrator.
- **D9 API versioning:** change `/v1` directly (not in production). Obligation: document every change well for the
  frontends (signer and dashboard handoffs in `docs/frontend-handoff/`) and for integrators (an integrator
  handoff/notice listing every changed status, field, enum member, ProblemCode and event).
- **D10 DSS calls inside a transaction stall the relay (pre-existing):** a separate task, later — already under
  study by the team, to be tackled soon; not part of this branch. ADR-0073 drops its false claim that signing
  never starves the relay and states the dependency instead.

All decisions of the full-audit round are taken. Next: rewrite ADR-0073 and the three tasks for scope C (blocks
1–5, block 6 deferred), D1–D10, the technical corrections of the full audit, and the evidence-audit adaptation list.

## 18. Rewrite after the full audit (2026-09-25)

ADR-0073 and TASK-048/049/050 rewritten for scope C and D1–D10: freeze, operator override, 72 h auto-seal and
`TECHNICAL_FAILURE` removed; `EnvelopeAgreed` / `EnvelopeVoided` at decision / `EnvelopeCompleted` both outcomes;
same-facts principle (§2.4) with its four homes; veto fails on unreached members; informational members never
hold a step and read the sealed copy (`NOT_REQUIRED`); specific causes; `DELEGATED_NO_ACT`; `ENVELOPE_ENDED` so
nothing stays `PENDING`; per-recipient invitation-sent column; admission instant handed to the session; gate rule
lets a signer pass at any time (ADR-0056 §2.2); acceptsActs() as properties; `app_now()` test body installed after
migrations; dedicated NOBYPASSRLS sweep role; retry policy unchanged (429 stays retryable), chain conflicts
transient; migration requires relay caught up and backfills from session state; party fields renamed; EnvelopeCompleted
carries ids and enum reasons only; ADR-0072/0064/0057 §2.17/LOAD-BEARING amendments declared; §9 revision arc;
acceptance bookkeeping owned by TASK-048 §3.12; evidence-audit adaptation list expanded (TASK-048 §6).
