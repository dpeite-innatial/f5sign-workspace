# TASK-051 — A closed envelope or leg answers the same before and after the revocation

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/envelope-answers-first`**, 2026-09-29; the branch is merged into `develop` on 2026-09-30 at `e6a0af5e` (it joined the ADR-0073 package at `aaf15651` the same day, and reached `develop` through that package). The implementation is `d6d2ffcd`, `c27fbd96`, `91d95ef9`, `911fdc89`, `c98c933c` and `a80eed76` (with the record commits `328397b6` and `9cab62da`); the ADR-0073 package was then merged in at `873f0971` and three post-join fixes followed in `f3b83ad3`, with the records in `e54d7c77` and `44064fe1` (§7). Validated on this worktree's own lane (`wt-backend`, `src=` this tree): lint, deptrac and phpstan clean, the fast tier green, and the gap, gate, parity, opening and race HTTP and Integration classes green. **Left out:** Infection and the full Integration/Acceptance suite over the joined package, which are the coordinator's; ADR-0074 stays as its record reads until the maintainer moves it. |
| **Type** | **Corrective.** No new capability: five recipient routes stop letting a queue choose their refusal code, an act past a step deadline the sweep has not applied stops answering a fixed `LEG_CLOSED` whatever the sweep will do, and `SESSION_CLOSED` is narrowed to the case where it is informative. |
| **Why** | The same act against the same closed envelope or released leg is answered with one code before the Session revocation drains and another after it (§1). The maintainer decided on 2026-09-29 that the answer must not depend on it, reversing ADR-0067 §2.3. |
| **Builds on** | [TASK-050](TASK-050-a-step-says-how-much-agreement-it-needs.md) on `feat/step-policy` (the per-recipient release and `RevokeRecipientSessionUseCase`, `480faab9`; the step deadlines and their sweep) and the [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) package (TASK-048/049: the admission `AdmitRecipientAct`, `acceptsActs()`, the gate rule). Reused unchanged: `RecipientAuthContext` and its reader, the two revocation use cases and their reactors, `SigningSessionStateException`'s factories and codes. |
| **Scope** | Session only. The order of the refusals in `SigningSession`'s act guards (`guardCommit()`, `guardDecline()`) and gate transitions (`ensureLiveChallenge()`, `mintChallenge()`, `submitAuthResponse()`); the five use cases that call them, including where the two gate use cases call `OpenGateResolver`; `AdmitRecipientAct`'s translation of `STEP_DEADLINE_PASSED`; the seven `#[OA\*]` 409 blocks and the docblocks listed in §3.4; the tests of §5; one frontend handoff. **Not ours:** the open, descriptor, read-model, download and renewal routes (checked in §3.5, not changed unless the check fails); any catalog change; Envelope's evaluator rules. |
| **Decision record** | **[ADR-0074](../adr/ADR-0074-a-closed-envelope-or-leg-answers-before-the-session.md)**, `Accepted` 2026-09-29 by the maintainer, realization pending (this task). Supersedes ADR-0067 §2.3 and §7.3 and amends ADR-0066 §2.6; both records already carry the supersession and the amendment, so this task realizes ADR-0074 and leaves those notes as they are. |
| **Delivery bar** | Over HTTP, for the commit, the delegated commit, the decline, the challenge issue and the auth submit: the same act against a voided envelope answers `ENVELOPE_NO_LONGER_LIVE` both before and after `RevokeEnvelopeSessions` is dispatched, and against a released leg on an open envelope answers `LEG_CLOSED` both before and after `RevokeRecipientSession` is dispatched. On the two gate routes the after-revocation arm answers 401 `AUTH_NO_OPEN_CHALLENGE` today, from `OpenGateResolver` (§1), and the released leg's before-arm answers `ENVELOPE_NO_LONGER_LIVE`. |
| **Sibling** | **TASK-050**, on `feat/step-policy`, merged into this branch at `51ade171`. Its `eb686c5f` mapped the deadline→sweep gap to a fixed `LEG_CLOSED` (a coordinator call of 2026-09-29, earlier the same day as ADR-0074); ADR-0074 §2.5 supersedes that mapping and §3.3 changes it. |

---

## 1. Why this task exists (measured on `0e499567`; the gate routes' resolver and the deadline gap's mapping corrected at `cdf2be68`)

**The guard order.** `SigningSession::guardCommit()` and `::guardDecline()` ask, in this order:
`status->isTerminal()` (`SESSION_ALREADY_COMPLETED`, `SESSION_ALREADY_DECLINED` or `SESSION_CLOSED`),
then `AWAITING_REAUTH` (401 `AUTH_REAUTH_REQUIRED`), then `!admitsSigning()` (bare `CONFLICT`), then
`!$envelopeIsAlive` (`ENVELOPE_NO_LONGER_LIVE`). `ensureLiveChallenge()`, `mintChallenge()` and
`submitAuthResponse()` ask `isTerminal()` before `!$envelopeIsAlive` as well, and `commitSignature()`
and `decline()` call the guards first. `LEG_CLOSED` is asked only by the admission,
`AdmitRecipientAct`, under the envelope's root lock, which each act use case calls **after**
`guardCommit()` / `guardDecline()`.

**The revocations.** `SigningSession::revoke()` has two callers: `RevokeEnvelopeSessionsUseCase`
(reacting to `EnvelopeVoided`) and `RevokeRecipientSessionUseCase` (reacting to `RecipientReleased`,
added by TASK-050 in `480faab9`, and skipping a member whose gate still passes, via
`RevocationSparesReaders`). Both ride the event log and relay, so both lag the fact they record.

**The gate routes answer a terminal session before the aggregate.** `IssueAuthChallengeUseCase` and
`SubmitAuthResponseUseCase` call `OpenGateResolver::resolve()` before the aggregate, and its
`openGateFor()` returns `null` for **any** terminal session (*"Terminal is terminal"*); both use cases
then throw 401 `AUTH_NO_OPEN_CHALLENGE` (`AuthGateRefusedException::noOpenChallenge()`), so the
aggregate's `isTerminal()` arm is never reached through these routes.
`GatedSigningCeremonyHttpTest::recovery_is_refused_once_the_session_is_signed` pins that answer for a
completed session. The only refusals ahead of the resolver are the superseded link and the step
pre-check `$auth->envelopeIsAlive && !$auth->stepIsActive`.

**What that produces**, per route, with `async_events` drained or not:

| Route | Envelope voided, session live | Envelope voided, session revoked | Leg released on an open envelope, session live | …session revoked |
|---|---|---|---|---|
| Commit, delegated commit, decline | `ENVELOPE_NO_LONGER_LIVE` | `SESSION_CLOSED` | `LEG_CLOSED` (admission) | `SESSION_CLOSED` |
| Challenge issue, auth submit (while a gate is open for the recipient) | `ENVELOPE_NO_LONGER_LIVE` | 401 `AUTH_NO_OPEN_CHALLENGE` (`OpenGateResolver`, before the aggregate) | `ENVELOPE_NO_LONGER_LIVE` (false: the envelope is live) | 401 `AUTH_NO_OPEN_CHALLENGE` |
| Any act route, session idled to `AWAITING_REAUTH`, envelope voided | 401 `AUTH_REAUTH_REQUIRED` | `SESSION_CLOSED` | — | — |

The gate row's pre-revocation cells come from the two gate use cases passing
`envelopeIsAlive: $auth->gatePasses` into the aggregate: a released, non-signing, non-informational
member has a shut gate on a live envelope, and the aggregate names that `ENVELOPE_NO_LONGER_LIVE`. Its
post-revocation cells come from the resolver: `SESSION_CLOSED` is not reachable on the gate routes at
all. A completed or declined session answers `AUTH_NO_OPEN_CHALLENGE` on them too, on either side of
any revocation, since `revoke()` never overwrites a terminal session: that answer is not relay-timed.

**The deadline→sweep gap.** `EnvelopeEndingEvaluator::admit()` refuses an act at or after a step's
deadline with `ActRefusal::STEP_DEADLINE_PASSED`. On `0e499567` `AdmitRecipientAct::translated()`
passed it through untranslated. TASK-050's `eb686c5f` (merged here at `51ade171`) maps it to a fixed
`LEG_CLOSED`: the arm `ActRefusal::LEG_CLOSED, ActRefusal::STEP_DEADLINE_PASSED =>
SigningSessionUnavailableException::legClosed()` in `translated()`, argued in its docblock (*"A step
past its deadline answers `LEG_CLOSED`"*, maintainer 2026-09-29), pinned by `AdmitRecipientActTest`'s
`'step deadline passed' => … 'LEG_CLOSED'` case, and published in `LEG_CLOSED`'s `#[OA\*]` text on the
commit, delegated commit and decline (*"including when this recipient's step has reached its deadline
and is about to be closed without this act"*). The same commit added a census over
`ActRefusal::cases()` so no refusal an act can meet reaches the wire untranslated. After the sweep the
same act meets a released leg (`LEG_CLOSED`, or `SESSION_CLOSED` once revoked), or a closed envelope if
the deadline ended it (`ENVELOPE_NO_LONGER_LIVE`). So the fixed mapping is right in the first case and
sweep-timed in the second.
It was a coordinator call made earlier on the same day, and ADR-0074 §2.5 supersedes it.

**Why it is now a defect rather than a decision.** ADR-0067 §2.3 kept the split as a diagnostic on
the premise that `REVOKED` has one writer. The second writer makes `SESSION_CLOSED` ambiguous, the gate
routes' pre-drain answer is false and their post-drain answer is an authentication code, and the signer
renders the two codes identically. ADR-0074 §1 and
§2.1 carry the full argument.

## 2. What already exists (reuse, do not rebuild)

- **The synchronous facts the new order needs are already read.** `RecipientAuthContext` carries
  `$envelopeIsAlive` (`acceptsActs()`), `$gatePasses` (ADR-0073 §2.3's gate rule) and
  `$closedLegOutcome` (non-null iff `RecipientView::legIsClosed()`), read by
  `RecipientAuthContextReader` after the session row is locked. No new cross-BC read is needed.
- **The admission stays the authority.** `AdmitRecipientAct` re-checks envelope, leg and step under
  the root lock and already maps `ENVELOPE_CLOSED` / `ENVELOPE_EXPIRED` to `ENVELOPE_NO_LONGER_LIVE` and
  `LEG_CLOSED` to `SigningSessionUnavailableException::legClosed()`. The advisory read must answer with
  the same codes. (`STEP_DEADLINE_PASSED` also maps to `legClosed()` today, `eb686c5f`; that arm is what
  §3.3 changes.)
- **The census over `ActRefusal` exists**: `AdmitRecipientActTest::every_refusal_a_recipient_act_can_meet_answers_a_published_session_code`
  (`eb686c5f`) fails naming any member left untranslated. §3.3 keeps it green.
- **The evaluator already knows what a deadline does at an instant**: `EnvelopeEndingEvaluator`'s clock
  trigger releases pending blocking members of the open step and settles or ends the envelope. §3.3
  derives the gap's answer from it rather than restating the rules.
- **The factories and codes do not change.** `SigningSessionStateException::sessionIsTerminal()`,
  `::envelopeNoLongerLive()` and `SigningSessionUnavailableException::legClosed()` are reused as they
  are; `OpenApiSpecTest` needs no catalog change.
- **The test seams exist**: `SigningSessionCommitRefusalTest` already builds a revoked session beside a
  dead envelope (`closedByTheSender()`); `CommitRefusalsNameTheirConditionHttpTest` already dispatches
  `RevokeEnvelopeSessions` by hand; `RevokeRecipientSessionUseCaseTest` shows the release side.

## 3. What gets built

### 3.1 The act guards ask in ADR-0074 §2.2's order

`guardCommit()` and `guardDecline()` (and so `commitSignature()` and `decline()`) take the leg's
closure as an input beside `envelopeIsAlive`, and ask: the recipient's own act (`COMPLETED`,
`DECLINED`) → envelope → leg → `AWAITING_REAUTH` → `notAuthenticated()` → `SESSION_CLOSED` for any other
terminal status → consent, challenge, role. The three act use cases pass
`$auth->closedLegOutcome === null` (or a named accessor on the context, if one reads better).

**The leg is asked BEFORE the step pre-check `$auth->envelopeIsAlive && !$auth->stepIsActive`, in all
five use cases** (`CommitSignatureUseCase`, `CommitDelegatedSignatureUseCase`,
`DeclineSignatureUseCase`, `IssueAuthChallengeUseCase`, `SubmitAuthResponseUseCase`), so the step never
masks the leg. The pre-check never answers `STEP_NOT_ACTIVE` for a closed leg. On the three act use
cases it yields to a closed leg, and the aggregate names the leg after the own act (question 3).
Answering `LEG_CLOSED` in the use case would pre-empt `SESSION_ALREADY_COMPLETED` on a replay, because
a completed recipient's leg is closed too. On the two gate use cases the leg is asked in the use case,
after the own act and before both the pre-check and `OpenGateResolver` (§3.2).
⚠ **`stepIsActive` is `!stepHoldsTheRecipientBack()`**
(`RecipientAuthContextReader`), which is `closed_at === null && !recipientStepIsActive`, and
`recipientStepIsActive()` means *activated*, not *activated and still open*. So the pre-check fires on
a live envelope only for a member whose step was never activated. It masks a closed leg only when the
leg was closed in a step the workflow never reached. The enumeration below states whether any path
produces that case. The order holds either way, and it is ADR-0073 §2.1's order in the admission.

⚠ **Enumerate before relying on `legIsClosed()`.** It is true for every terminal `RecipientOutcome`
(`COMPLETED`, `DECLINED`, `DELEGATED`, `SKIPPED`, `RELEASED`) and for an admitted act. State, in the
guard's docblock and in a test, which code each reaches on each act route after the reorder; a
`DELEGATED` recipient in particular may already be refused earlier on some routes (the repo's
authoring rule 5).

### 3.2 The gate transitions name why the gate is shut

**The envelope and the leg are asked before `OpenGateResolver`.** Today the resolver's terminal
short-circuit in `openGateFor()` answers every terminal session `null`, and the two use cases turn that
into 401 `AUTH_NO_OPEN_CHALLENGE` before the aggregate (§1). A revocation makes a live session terminal,
so that refusal is relay-timed. In `IssueAuthChallengeUseCase` and `SubmitAuthResponseUseCase` the
order becomes:

1. the superseded link (unchanged, first);
2. the recipient's own act (`COMPLETED`, `DECLINED`): 401 `AUTH_NO_OPEN_CHALLENGE`, today's answer,
   unchanged and not relay-timed (`revoke()` never overwrites a terminal session);
3. the envelope not accepting acts: `ENVELOPE_NO_LONGER_LIVE`, from `$auth->envelopeIsAlive`;
4. the leg closed: `LEG_CLOSED`, from `$auth->closedLegOutcome`;
5. the step pre-check (§3.1);
6. `OpenGateResolver`: 401 `AUTH_NO_OPEN_CHALLENGE` for any other terminal session (the envelope and
   the leg are both live, so this is not relay-timed) and for a recipient with nothing left to prove;
7. the rest, then the aggregate.

Question 2 needs the session's status ahead of questions 3 and 4, and the resolver already reads the
session. Whether the resolver's terminal arm is split so the own-act half is answered first, or the use
case reads the status itself, is the implementer's call. The resolver stays the single home of *which
gate is open* (its class docblock), and its terminal short-circuit keeps running before its recovery
arm (`GatedSigningCeremonyHttpTest::recovery_is_refused_once_the_session_is_signed`).

**The aggregate re-asks inside the lock.** The two use cases stop passing `gatePasses` into a parameter
named `envelopeIsAlive`. The aggregate's three gate transitions ask: own act → gate shut with the
envelope not accepting acts (`ENVELOPE_NO_LONGER_LIVE`) → gate shut with it accepting acts
(`LEG_CLOSED`) → the rest, with `SESSION_CLOSED` after the gate. Whether that is two booleans or one
small value object is the implementer's call; the parameter's name must say what it carries. Through
the routes, the aggregate's terminal arms are reached only in the unlocked window between the
resolver's read and the locked load (the resolver's docblock, *"The read is not under the write
lock"*). They are pinned at Unit (§5), and **`SESSION_CLOSED` is not reachable on the gate routes**.

Then **check every other refusal the two gate use cases answer before the aggregate**: the
effective-method resolution, the deliverability checks and the OTP limiter. For each, check whether it
reads session state a revocation changes. Record the result per refusal in §7 of this record when it
is written. Any that does is relay-timed and is moved or answered from the synchronous facts. The
resolver is not on this list because the claims check already found it relay-timed, and the ordering
above answers it.

### 3.3 The deadline→sweep gap answers as the sweep's result

`STEP_DEADLINE_PASSED` already stays off the wire, but as a fixed `LEG_CLOSED` (`eb686c5f`, §1). That
is right only where the deadline does not end the envelope. This task changes it to follow the sweep's
result, in ADR-0074 §2.5's two arms. On that refusal the admission derives the answer from the
envelope's state once the due deadline is applied at the act's instant: `ENVELOPE_NO_LONGER_LIVE` if it
ends the envelope, otherwise `LEG_CLOSED`, because the actor is a member of the step that expired and
the sweep releases them. ⛑ Amended 2026-09-29 (maintainer), before any code: this read three arms, the
third *"`STEP_NOT_ACTIVE` if it closes the step without releasing them"*. It is removed:
`STEP_NOT_ACTIVE`'s published remedy (*lifts by itself*) would be false for a member of the step that
expired. ⛑ **Amended again 2026-09-29 (maintainer): an informational member answers its role refusal**
(`COMMIT_NOT_OFFERED_TO_ROLE`, `DECLINE_NOT_OFFERED_TO_ROLE`), not `LEG_CLOSED`: the sweep does not release
an informational leg, and the role answers before the gap arm whatever the timing (ADR-0074 §2.5); a
deadline that ends the envelope still answers `ENVELOPE_NO_LONGER_LIVE` first. Where that derivation lives (the evaluator returning the post-clock refusal, or
`AdmitRecipientAct` translating by it) is the implementer's call, within ADR-0073 §2.1's rule that the
admission decides under the lock.

What changes with it, all from `eb686c5f`: the `STEP_DEADLINE_PASSED` member of `translated()`'s
`LEG_CLOSED` arm; the paragraph of `translated()`'s docblock that argues the fixed mapping (*"A step
past its deadline answers `LEG_CLOSED`"*), per the repo's authoring rule 2 (its reason, *no new code*,
still holds and stays); `AdmitRecipientActTest`'s `'step deadline passed'` case and its comment, which
become one case per arm (two); and the `LEG_CLOSED` clause on the commit, delegated commit and decline
`#[OA\*]` 409 blocks (*"including when this recipient's step has reached its deadline and is about to
be closed without this act"*), which then covers only the member the deadline releases. The census
over `ActRefusal::cases()` stays green unchanged.

### 3.4 Every surface that states the old order

Enumerated with `rg -n 'SESSION_CLOSED|ENVELOPE_NO_LONGER_LIVE' src config docs` and
`rg -n 'ADR-0067 §2.3|ADR-0067 §7.3|ADR-0066 §2.6' src tests docs`, at `c12d4602` (the tip this
branch will be rebased onto; `aca35852` there rewrote the published strings without changing the
order). **Re-run both greps at the moment of the change; this list is a worklist, not the bar.**

**Published `#[OA\*]` 409 blocks (the spec the signer and integrators read):**

| Route | Controller | What it states today | Becomes |
|---|---|---|---|
| `POST /api/v1/signing/commit` | `CommitSignatureController` | `SESSION_CLOSED` is the released leg; `ENVELOPE_NO_LONGER_LIVE` is *"Same outcome as the previous one, reached before the session had been closed … depends only on whether that closing has happened yet. Treat them alike"*; `LEG_CLOSED` is *"already over, as the envelope judges it at the moment of the act: an act of theirs was already admitted, or their leg was released without one, including when this recipient's step has reached its deadline and is about to be closed without this act. (A closed envelope answers `ENVELOPE_NO_LONGER_LIVE` instead, ahead of this.) It can arrive before the session itself has been closed, which is why it is not `SESSION_CLOSED`"* (re-read at `cdf2be68`) | Closed envelope → `ENVELOPE_NO_LONGER_LIVE`; closed leg on a live envelope → `LEG_CLOSED`, with the deadline clause covering only the member the deadline releases (§3.3); `SESSION_CLOSED` only for ADR-0074 §2.4's case; no sentence about the revocation's timing, including `LEG_CLOSED`'s *"It can arrive before the session itself has been closed"* |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature` | `CommitDelegatedSignatureController` | `SESSION_CLOSED` and `ENVELOPE_NO_LONGER_LIVE` as on the commit, in the delegated wording; `LEG_CLOSED` carries the deadline clause but **not** the *"before the session itself has been closed"* sentence | Same as the commit |
| `POST /api/v1/signing/decline` | `DeclineSignatureController` | As the delegated commit, in the decline wording (deadline clause present, no *"before the session"* sentence on `LEG_CLOSED`) | Same as the commit |
| `POST /api/v1/signing/session/auth/otp/send` | `SendAuthOtpController` | *"an ended envelope answers this or `ENVELOPE_NO_LONGER_LIVE` depending only on whether the session has been closed yet"*; lists `SESSION_ALREADY_COMPLETED` and `SESSION_CLOSED`, which this route reaches only in the resolver's unlocked-read window (a terminal session is 401 `AUTH_NO_OPEN_CHALLENGE` from `OpenGateResolver`, §1, §3.2); no `LEG_CLOSED` | Adds `LEG_CLOSED`; drops the timing clause; states that a terminal session is answered by the 401 `AUTH_NO_OPEN_CHALLENGE`, not by `SESSION_ALREADY_COMPLETED` or `SESSION_CLOSED` |
| `POST /api/v1/signing/session/auth` | `SubmitAuthResponseController` | Same as the OTP send | Same |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth/otp/send` | `SendRecipientAuthOtpController` | Lists `ENVELOPE_NO_LONGER_LIVE`, `SESSION_ALREADY_COMPLETED`, `SESSION_CLOSED` as the lifecycle refusals | Adds `LEG_CLOSED`; the two session codes as on the OTP send |
| `POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth` | `SubmitRecipientAuthResponseController` | Same list | Same |

Read each route's path and `_authn` from `config/routes/api/signing.php` rather than from this table. The 422 block of `CommitDelegatedSignatureController` lists the act's
refusals it never answers ahead of (*"already completed, closed, no longer live, `STEP_NOT_ACTIVE`,
`LEG_CLOSED`"*); re-read it for the new order.

**Docblocks and comments in `src/`:** `AdmitRecipientAct::translated()`'s docblock paragraph on the
step deadline (§3.3); `OpenGateResolver::openGateFor()`'s terminal short-circuit comment, if the
own-act half moves (§3.2); `SigningSession::guardCommit()`'s and `::commitSignature()`'s
docblock (*"The order of the first two guards is load-bearing and is pinned … Swapping them makes every
dead envelope report the relay as behind"*); `::guardDecline()` / `::decline()`'s *"The session asks the
first three in the commit's order for the commit's reason (ADR-0067 §2.3)"*;
`SigningSessionStateException::sessionIsTerminal()` and `::envelopeNoLongerLive()`;
`IssueAuthChallengeUseCase` and `SubmitAuthResponseUseCase`'s comments on `envelopeIsAlive: $auth->gatePasses`
(*"it refuses as `ENVELOPE_NO_LONGER_LIVE` whichever of the two it is handed"*); the ADR-0066 §2.6
comments in `CommitSignatureUseCase`, `CommitDelegatedSignatureUseCase`, `IssueAuthChallengeUseCase`,
`SubmitAuthResponseUseCase` and `RecipientAuthContext::$stepIsActive`; `AdmitRecipientAct`'s class
docblock (*"after, so a replay against a completed session still answers `SESSION_ALREADY_COMPLETED`"*
stays true; re-read the rest). Per the repo's authoring rule 2, the relay-diagnostic reason is replaced
by the event log as its home, not deleted.

**Tests whose docblocks cite the old order:** `SigningSessionCommitRefusalTest`,
`SigningSessionDeclineTest`, `SigningSessionStateRefusalCensusTest`, `CommitSignatureUseCaseTest`,
`CommitDelegatedSignatureUseCaseTest`, `GatedSigningCeremonyHttpTest`,
`CommitRefusalsNameTheirConditionHttpTest`, `StepPolicyDeliveryBarHttpTest`,
`SigningSessionStateMessageTest` (the files `rg -l 'SESSION_CLOSED|sessionIsTerminal' tests` lists);
and `AdmitRecipientActTest`'s `'step deadline passed'` case (§3.3).

**Documents:** ADR-0074's `Status`, §5 and §6 (ADR-0067's and ADR-0066's `Status` notes and their
`docs/adr/README.md` rows were written at `cdf2be68`, on acceptance, and are not this task's); the domain model
under `docs/ddd/` that describes the session's refusals, if it states the order; the frontend handoffs
that describe `SESSION_CLOSED` (`docs/frontend-handoff/TASK-043-…`, `TASK-046-…`, `TASK-048-…` and the
README's code table) — historical handoffs are annotated, not rewritten; `docs/BACKLOG.md` rows that
cite `SESSION_CLOSED`, read for tense.

### 3.5 The routes not changed, checked

The open (`StartSessionUseCase` / `SigningTokenIssuance`), the descriptor, the read model, the document
download and the renewal each already answer a closed envelope or a shut gate from the synchronous
predicates. Confirm by reading each that none answers from `SessionStatus::REVOKED` in a way a
revocation's timing changes, and record the result in this record's deviations section. A route that
fails the check enters scope.

### 3.6 Frontend handoff

One handoff under `docs/frontend-handoff/`, before the merge: `LEG_CLOSED` is new on the OTP send and
the auth submit (both audiences); on those two routes a closed envelope or leg no longer turns into 401
`AUTH_NO_OPEN_CHALLENGE` once the session is revoked, and `SESSION_CLOSED` / `SESSION_ALREADY_COMPLETED`
are not answered there; `SESSION_CLOSED` is narrowed; `ENVELOPE_NO_LONGER_LIVE` is the only answer to a
closed envelope on every route; an act past an unswept step deadline answers what the sweep will make
of it rather than a fixed `LEG_CLOSED`. State the release order ADR-0074 §2.8 leaves to this task.

## 4. Key decisions

Decided in ADR-0074 and not reopened here: the order (§2.2), the gate split (§2.3), `SESSION_CLOSED`
kept and narrowed (§2.4), the deadline gap answered as the sweep's result (§2.5), no catalog change. Left
to the implementer, within those: the parameter shape for the leg and gate inputs (§3.1, §3.2), how the
own-act status reaches the gate use cases ahead of the envelope (§3.2), and where the deadline
derivation lives (§3.3).

## 5. Verification

Harness: the ephemeral lane from this worktree (`make -C ../f5sign-infra wt-backend src=$(pwd)`), full
suite through `test-runner`, and the name of the harness stated with every green run. `async_events` is
`in-memory://` in test, so **nothing drains unless a test dispatches the revocation by hand**; every
before/after case below dispatches it explicitly between the two acts.

1. **Same act, same code, before and after the revocation** — for the commit, the delegated commit,
   the decline, the challenge issue and the auth submit:
   - a voided envelope: act, dispatch `RevokeEnvelopeSessions`, act again → `ENVELOPE_NO_LONGER_LIVE`
     both times;
   - a released leg on an open envelope: act, dispatch `RevokeRecipientSession`, act again →
     `LEG_CLOSED` both times.
   On the challenge issue and the auth submit, before this task the second act answered 401
   `AUTH_NO_OPEN_CHALLENGE` from `OpenGateResolver` in both cases, and the released leg's first act
   answered `ENVELOPE_NO_LONGER_LIVE` (§1). So the gate routes' cases must drive the
   use case, not only the aggregate, since the resolver's refusal happens before the aggregate is called.
   At Unit (`SigningSessionCommitRefusalTest`, `SigningSessionDeclineTest`, `SigningSessionAuthGateTest`)
   with both-true fixtures, at Application (the five `*UseCaseTest`s), and over HTTP (one acceptance case
   per route family; the delivery bar).
2. **`LEG_CLOSED` for a released leg on an open envelope with the session already `REVOKED`**: the case
   that answered `SESSION_CLOSED` on the act routes and `AUTH_NO_OPEN_CHALLENGE` on the gate routes on
   `0e499567`.
3. **An idled session on a closed envelope is not sent to re-authenticate**: `AWAITING_REAUTH` on a
   voided envelope answers `ENVELOPE_NO_LONGER_LIVE`, not 401 `AUTH_REAUTH_REQUIRED`.
4. **`SESSION_CLOSED` still answers when the session ended while the envelope and the leg are live**: a
   `REVOKED` session with `envelopeIsAlive` true and the leg open answers `SESSION_CLOSED` on every act
   and on the aggregate's three gate transitions. This is a Unit fixture: no production path builds it,
   and the case's docblock says so. Over the gate routes the same state answers 401
   `AUTH_NO_OPEN_CHALLENGE` from the resolver, which is not relay-timed because the envelope and the leg
   are live. One Application case per gate use case pins it.
5. **Own act still first, on the act routes** (commit, delegated commit, decline): a completed session
   on a voided envelope answers `SESSION_ALREADY_COMPLETED`, and a declined one
   `SESSION_ALREADY_DECLINED`, before and after the revocation (TASK-043's replay). **On the gate
   routes** a completed or declined session answers 401 `AUTH_NO_OPEN_CHALLENGE`, on a live and on a
   voided envelope, before and after the revocation. That answer is unchanged, and it is not relay-timed.
   `GatedSigningCeremonyHttpTest::recovery_is_refused_once_the_session_is_signed` stays green as it is.
6. **The deadline gap**: in `AdmitRecipientActTest` (or the evaluator's test, wherever §3.3 puts the
   derivation), each of ADR-0074 §2.5's two arms (amended 2026-09-29 from three), with the deadline
   passed and unswept, answers the code the same act gets after the sweep; and an informational member
   answers its role refusal in the gap and after the sweep (amended 2026-09-29). Sabotage: the gap arm
   ahead of the role reddens naming `STEP_DEADLINE_PASSED` (Session's `LEG_CLOSED`). This replaces `eb686c5f`'s single `'step deadline passed' =>
   LEG_CLOSED` case. `every_refusal_a_recipient_act_can_meet_answers_a_published_session_code` stays
   green, so `STEP_DEADLINE_PASSED` reaches no route.
7. **The census updated**: `SigningSessionStateRefusalCensusTest` keeps its three factory properties and
   `every_terminal_status_is_classified_by_the_refusal_it_raises` unchanged, and gains
   `every_terminal_status_declares_whether_it_is_the_recipients_own_act`, derived from
   `SessionStatus::cases()`. Drop `DECLINED` from the own-act set and watch it fail naming `DECLINED`.
8. **Sabotage checks**, each applied, observed red for the stated reason, restored:
   - move `isTerminal()` back above the envelope check in `guardCommit()` → case 1's commit arm reddens
     naming `SESSION_CLOSED`, and case 5 stays green (it must: own act is still first);
   - move the leg check below `SESSION_CLOSED` → case 2 reddens naming `SESSION_CLOSED`;
   - pass `gatePasses` back as the single gate input → the gate half of case 1 reddens naming
     `ENVELOPE_NO_LONGER_LIVE` on the live-envelope arm;
   - move the envelope and leg checks back below `openGate->resolve()` in `IssueAuthChallengeUseCase`
     (then in `SubmitAuthResponseUseCase`) → the after-revocation arm of case 1 reddens naming
     `AUTH_NO_OPEN_CHALLENGE`, and case 5's gate half stays green;
   - move the envelope check below `AWAITING_REAUTH` → case 3 reddens naming `AUTH_REAUTH_REQUIRED`;
   - revert the deadline derivation to `eb686c5f`'s fixed `STEP_DEADLINE_PASSED → LEG_CLOSED` arm →
     case 6's envelope-ending arm reddens naming `LEG_CLOSED` where `ENVELOPE_NO_LONGER_LIVE` is
     expected; the release arm stays green.
   ⚠ **With two guards in series, check which one fired** (the repo's authoring rule 4): for each
   sabotage, assert the code, not only a red.
9. **`OpenApiSpecTest` green with no catalog change**, and the seven `#[OA\*]` blocks of §3.4 re-read
   whole, not by changed line, after the last code commit.

## 6. Open follow-ups (track, don't solve here)

- **A per-route completeness check for published codes** ([`BL-209`](../BACKLOG.md)) would have caught
  `STEP_DEADLINE_PASSED` on the wire before `eb686c5f`, and `LEG_CLOSED`'s absence from the gate routes.
  It would also catch `SESSION_ALREADY_COMPLETED` / `SESSION_CLOSED` published on routes that answer a
  terminal session with `AUTH_NO_OPEN_CHALLENGE`. Not built here.
- **A refusal code emitted by `ActNotAdmittedException` through `->name` is invisible to
  `OpenApiSpecTest`**, which reads single-quoted literals. For `AdmitRecipientAct` this is covered by
  `eb686c5f`'s census over `ActRefusal::cases()`. The census classifies `AGREEMENT_NOT_SECURED` and
  `AGREEMENT_SECURED` as unreachable from an act by a stated reason, not by a test that drives the
  evaluator. A refusal that reaches a route through `ActNotAdmittedException` other than by
  `AdmitRecipientAct` is outside that census. Whether `OpenApiSpecTest`
  should read `ActRefusal`'s cases is a follow-up: [`BL-342`](../BACKLOG.md).
- **Support's view of relay lag** moves to the event log (`SessionRevoked`). If support needs it without
  database access, a read surface for it is a separate decision.
- **The read-to-lock race in the ending arm** ([`BL-358`](../BACKLOG.md)): see §7, *Found at the join*, fix 3.
- **ADR-0074's `Enforced by` / `Realized in`** may now name the post-join commits; that is the maintainer's edit (ADR-0074 is `Accepted` already).

---

## 7. Deviations & honest notes

### Scope
- None beyond §3 for the first implementation. The join added `EnvelopeEndingEvaluator::deadlineGap()`, `Envelope::endingAtTheDeadline()` (with a private `clockDecision()` shared with `applyClocks()`), `StepView::$pastDeadline`, and made the port `recordRecipientOpening()` return `?ActRefusal`; all inside the Envelope and Session models this task's answer order already reads.

### Decisions made during implementation
- The join with the ADR-0073 package (`873f0971`) had eight conflicts, resolved keeping both intents. One conflict was hidden: `StepDeadlineBarsDeHttpTest` now asserts 409 `LEG_CLOSED` on the code send.

### Found at the join (post-join fixes, `f3b83ad3`)
1. **`LEG_CLOSED` on both code-send routes for a released recipient who never opened.** No code change was needed; a test and the `#[OA]` blocks were added.
2. **An opening in the step-deadline to sweep gap is refused as the sweep will leave it**, by one rule, `EnvelopeEndingEvaluator::deadlineGap()`, applied in both homes of the gate rule: the aggregate and the view (via `StepView::$pastDeadline`). `GateRuleParityTest` goes to 16 cases. The port's `recordRecipientOpening()` now returns `?ActRefusal`.
3. **The descriptor publishes `RELEASED` (not `REVOKED`) in the gap**, and the code-send and auth-submit routes answer `ENVELOPE_NO_LONGER_LIVE` where the deadline ends the envelope. The read side asks the new pure `Envelope::endingAtTheDeadline()`, pinned at every clock of the 41 ending stories.
   - **Design decision:** the coordinator rejected reading through `applyClocks()` on a copy of the envelope in favour of the pure query, which reuses `Domain\Service\Ending`, so the read cannot mutate and cannot drift from the write.
   - **Side effect:** the sender's access-code reset and auth unlock are refused in the gap too, because they share the gate rule; their `#[OA]` says so.
   - **Coverage:** `closedLegAtTheGate()` is covered only by the Acceptance test (sabotage-checked), not by a lower tier.
   - **Unchanged on purpose:** an informational member with a session in the gap sees their session state, as before.
   - **Race:** if the deadline passes between the unlocked read and the row lock, an open where the deadline ends the envelope still answers `LEG_CLOSED` instead of `ENVELOPE_NO_LONGER_LIVE`; filed as [`BL-358`](../BACKLOG.md).

### Decisions that needed an ADR
- ADR-0074, `Accepted` 2026-09-29 by the maintainer; no further ADR from the join.

### Declared and unproven properties
- Infection covered-MSI and the full Integration/Acceptance suite over the joined package were not run here.
- Sabotages that fired on this lane: code-send answers 404; one home of the gate rule alone makes the parity test name the gap cases; both homes give 200 with a credential; the descriptor reads `REVOKED`; the gate routes answer `LEG_CLOSED`; the pure query ignoring deadlines fails 14 of 41 stories.

### Debt left behind, and where it lives now
- `OpenApiSpecTest` does not read `ActRefusal` cases: [`BL-342`](../BACKLOG.md).
- The read-to-lock race in the ending arm: [`BL-358`](../BACKLOG.md).
