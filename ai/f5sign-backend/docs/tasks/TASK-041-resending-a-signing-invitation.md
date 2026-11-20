# TASK-041 — Resending a signing invitation, without pretending the address was wrong

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/recipient-invitation-reminder`** — enumerate the range with `git log --oneline --no-merges origin/develop..HEAD` rather than reading a pair of shas here. ⛔ **A written range on an active branch is stale by construction**: this row named `a2745d2` → `5a0dcbe`, was corrected to `682b03f` → `6003e85` on 2026-09-01, and was three commits behind again within the hour. The record that does not rot is the command. ⛔ **Not merged.** ⚠ **And it IS pushed** — this row said *"not merged and not pushed"*, corrected 2026-08-31 at the rename, which is exactly when the difference started to matter: the rename edits a migration's SQL in place, and repo rule 2's carve-out is **unpushed**, not unmerged — so it does **not** cover this branch. The edit was taken anyway because the branch is workspace-local and nobody outside it holds a copy, and the cost is a mandatory `make -C ../f5sign-infra test-db-reset` for anyone who already ran it. ⛔ Stating the rule as *"unmerged"* (as this row and `Version20260831000002`'s docblock both did until 2026-09-01) widens a carve-out that the next reader will cite while editing genuinely published SQL. `git rev-parse origin/feat/recipient-invitation-reminder` is the check. Falsifiable in the opposite direction to the sentence this replaced: `grep -n "RECIPIENT_INVITATION_RESENT" src/F5Sign/Notification/Domain/ValueObject/NotificationPurpose.php` and `grep -n "resends" config/routes/api/envelope.php` both return hits, `src/F5Sign/Notification/Application/Subscriber/OnRecipientInvitationResent.php` exists, and the two `envelope.recipient` columns are in `migrations/Version20260831000002.php`. Green under the **main-checkout infra Makefile against the live stack** — this branch was developed in the main checkout, not a worktree, and the harness was verified rather than assumed (`git rev-parse --git-dir` = `.git`, `git -C ../f5sign-infra status --porcelain` empty, the **committed** `docker-compose.override.yml` binding `../f5sign-backend`), so `make -C ../f5sign-infra {lint,phpstan,composer cmd=arch,test}` validated *this* tree: lint `0 of 1039` · deptrac `Violations 0` / `Errors 0` · PHPStan L9 `[OK] No errors` · `OK (2467 tests, 11939 assertions)` against a pre-work baseline of `OK (2415 tests, 11627 assertions)` = **+52 tests, +312 assertions** · Infection **Covered-MSI 85 %** against the `minCoveredMsi` floor of 79. Every property in §6 executes (count them there, not here); the sabotage §6 names by hand was run and reddened case 2 and only case 2. ⚠ **Two consequences ship open and are not claimed as solved**: correct-then-resend sends twice inside the `Recipient::MIN_RESEND_INTERVAL_SECONDS` window ([BL-212](../BACKLOG.md)), and `SMALLINT` is the only ceiling on `resends_made` ([BL-213](../BACKLOG.md)). §8 carries the rest, including a migration that had to be renumbered mid-branch. ⚑ **Re-measured 2026-08-31 after the rename** (§8, *the concept shipped under a noun another feature already owned*), on a tree merged with `develop` and through the same main-checkout targets: lint `0 of 1054` · deptrac `Violations 0` / `Errors 0` · PHPStan L9 `[OK] No errors` · `OK (2513 tests, 12168 assertions)`, which is **assertion-identical to the pre-rename `HEAD`** measured the same way on the same reset database — the rename moved names, not behaviour. ⚠ `make test-db-reset` is required across that commit, because the migration renames a column rather than adding one. ⚑ **Re-measured 2026-09-01 after the branch audit**, same main-checkout targets, on a tree carrying the audit's prose corrections and the uncommitted `900 → 60`: lint `0 of 1054` · deptrac `Violations 0` · PHPStan L9 `[OK] No errors` · `OK (2515 tests, …)`. ⛔ **The assertion count is NOT stable and should not be quoted as a baseline.** Runs of one unchanged tree gave 12173, 12174, 12175 and 12179 with the test count fixed at 2515. **Located 2026-09-01 by diffing two `--log-junit` runs per test**, which is the cheap way and the only one that names it: the sole disagreeing case is `Session\Integration\ConcurrentAuthSubmissionTest::two_overlapping_wrong_codes_each_spend_an_attempt`, at **25 or 26** assertions. It is the two-`proc_open()`-children row-lock probe — real concurrency on separate connections with an `awaitBothBlocked()` readiness wait — so its assertion count depends on how the children interleave, not on anything under test. ⚑ **Nothing is wrong with it and it should not be 'fixed' into determinism**: a probe that spends assertions proving both children actually blocked is the only shape that can separate a held row lock from an absent one, which `Integration/`'s single DAMA connection cannot. Unrelated to this branch, which merely reproduces it. The consequence for records like this one: **cite the test count, never the assertion count** — the *assertion-identical* comparison above is worth a few either way. Ruled out on the way: filesystem censuses (all eight root at `src/F5Sign` or narrower and filter by needle), the shared Mailpit (both readers isolate on a per-run tenant-derived address), and the shared broker (`EventLogBrokerRoundTrip|EventBrokerRetryDelivery` gave 23 assertions across five consecutive runs). Three sabotages were run on the parts that were rewritten by hand rather than mechanically — the resent invitation borrowing the invitation's eyebrow, the Spanish title made the subject of an agreeing verb, and an accent in the Spanish SMS body — and each reddened its own test and nothing else; all three restored, verified by checksum. |
| **Type** | **Forward build.** One new route on the integrator surface, one new Envelope fact, one new notification occasion — each on a seam that already exists and carries two or three members. No new BC edge: Envelope emits, Notification observes, exactly as the invitation and the correction already do. |
| **Why** | ⚑ **Past tense since 2026-08-31 — this is the record of what the task removed, not of how things are.** A recipient who lost, ignored or never received their invitation **could not be re-invited**. The only path was [`POST /envelopes/{id}/recipients/{recipientId}/corrections`](../../config/routes/api/envelope.php), which does produce a working link — but it spends one of the **three** corrections [`Recipient::MAX_CORRECTIONS`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php) reserves for real addressing errors, and records a [`RecipientCorrected`](../../src/F5Sign/Envelope/Contract/Event/RecipientCorrected.php) asserting the address was wrong when it was not. The audit trail is the thing this platform sells; spending it on a resend was the defect. |
| **Builds on** | **[ADR-0037](../adr/ADR-0037-notification-supporting-bc.md)** — Notification is a category-(c) supporting BC and this changes nothing about that; the reactor pair is [`OnRecipientCorrected`](../../src/F5Sign/Notification/Application/Subscriber/OnRecipientCorrected.php) + its handler, copied rather than invented. **[ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.6** and **[TASK-028](TASK-028-opaque-signing-token.md) §4.3** — the credential is stored as a digest and issuance is additive; together they fix the shape of this feature (§5 D1). **[ADR-0038](../adr/ADR-0038-template-archive.md)** for pin-at-creation, **[TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md)** for the locale chain, **[TASK-030](TASK-030-sms-delivery-channel.md)** §5 for the SMS segment budget a new purpose inherits. |
| **Decision record** | **No ADR, and none was owed — confirmed at close.** The branch minted none and moved none: no ADR changed `Status`, and neither `deptrac.yaml` nor `phpstan.dist.neon` nor the baseline was touched. (ADR-0037 *was* edited on this branch — four stale counts in its body, prose only; §8 says why that is not a decision change.) Every cross-cutting question here was already answered. ADR-0037 owns the one-way rule this stays inside; ADR-0045 §2.6 owns why a resend must be a reissue; [ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md) owns the route-declared `Authn` seam the new route uses unchanged; [TASK-031](TASK-031-channel-selection-beyond-email.md) owns the selector. ⛔ **What would force one:** killing the previous link (§7) is revocation, which TASK-028 §4.3 declined on the record — proposing it is an ADR, not a task decision. So is any guard that needs Envelope to read Session state (§7). |
| **Delivery bar** | An integrator calls the new route for a recipient who was already invited and gets one new notification whose copy reads as **the invitation, sent again** and whose link works. The signing session, if one exists, is untouched — same id, same state, same progress. A second call inside the minimum interval is refused with a distinct error. A recipient whose leg has closed, or whose step never activated, is refused. |
| **Blocks** | Nothing. ⚑ **Corrected 2026-08-31, at the rename**: this row read *"it is the manual half of the automatic reminders `RemindersSchedule` was shaped for"*, and that was false in a way that outlived a wording fix. `RemindersSchedule` is a **cadence before a deadline** — *nudge 14, 7 and 1 days before expiry* — and this task repairs **one invitation that did not arrive**. Different trigger, different population, different copy; neither is a half of the other. That confusion is exactly what the rename removed, and [BL-210](../BACKLOG.md) now stands on its own: a shaped, persisted, validated setting that nothing reads. |

---

## 1. Why this task exists

The invitation is sent once, by
[`OnRecipientStepActivated`](../../src/F5Sign/Notification/Application/Subscriber/OnRecipientStepActivated.php)
reacting to `RecipientStepActivated`, and **the occasion is idempotent by construction**:
`NotifyActivatedStepRecipientsUseCase` derives its id from
`envelope|recipient|purpose` and returns early when a notification with that id already exists. So
re-activating a step does not re-invite anybody — it converges and does nothing, silently and
successfully.

That is correct behaviour for an accidental redelivery and wrong for a deliberate resend. The
[`Notification`](../../src/F5Sign/Notification/Domain/Aggregate/Notification.php) aggregate already
names the distinction in its own docblock — *"an accidental redelivery of the same cause converges,
but **a forced resend** / new OTP issuance / re-activation is a new cause → a new occasion that
actually sends"* — so the aggregate is built for this and **only the trigger is missing**.

Meanwhile **no route on the sender-facing surface re-invited anybody** — enumerate that surface from
[`config/routes/api/envelope.php`](../../config/routes/api/envelope.php) rather than from a number
here. The workaround in the field was the contact-correction endpoint, which works because
[`Recipient::correctContact()`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php) does not
require the contact to have changed. Its cost is stated in the header table and is not recoverable
after the fact: the correction budget is spent and the event is written.

⚑ **Corrected 2026-08-31, at close.** This paragraph read *"the sender-facing surface **has fifteen
routes** and none of them re-invites"*, in the present tense, and this task falsified the second half
by adding the route that does. The count was wrong on its own terms too — that file declared sixteen
routes before this change and declares seventeen after — which is why the replacement states the
property and says where to count, instead of writing *sixteen* and waiting for the same failure.

## 2. What already exists (reuse, do not rebuild)

- **The reactor pair, in shape.**
  [`OnRecipientCorrected`](../../src/F5Sign/Notification/Application/Subscriber/OnRecipientCorrected.php)
  translates an Envelope fact into a Notification command, with its Messenger handler beside it.
  ⚠ `CLAUDE.md` authoring rule 3 applies: read **every** sibling subscriber before copying one —
  `ls src/F5Sign/Notification/Application/Subscriber/`, and where two differ the difference is either a
  bug or a decision. ⚑ This line said *"there are five"* until 2026-08-31, when this task's own
  `OnRecipientInvitationResent` made it six.
- **The whole notification path**, in
  [`NotifyCorrectedRecipientUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyCorrectedRecipientUseCase.php),
  which is the exact analogue: mint a credential, build the link, resolve the contact at creation,
  pin the template, create the occasion. It already carries an ordinal in its cause string. This task
  is that use case with a different purpose and a different ordinal.
- **The credential seam.** [`SigningTokenIssuer`](../../src/F5Sign/Session/Contract/Service/SigningTokenIssuer.php)
  owns the lifetime and mints on demand; Notification already calls it directly from its own
  minting sites — census them from `ISSUER_CALLERS` in
  [`SigningReadersRefuseUnsentEnvelopeTest`](../../tests/F5Sign/Session/Application/Query/SigningReadersRefuseUnsentEnvelopeTest.php),
  which is the set [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.3 makes
  load-bearing. Nothing new was needed there. ⚑ This line said *"its two triggers"* until 2026-08-31;
  this task's `NotifyResentInvitationRecipientUseCase` is the third, and it enrolled itself in that census.
- **The aggregate guard shape.** `correctRecipientContact()` already refuses a terminal envelope, an
  unsent one, and a closed recipient leg via
  [`RecipientNotCorrectableException`](../../src/F5Sign/Envelope/Domain/Exception/RecipientNotCorrectableException.php).
  The new method's guard is that guard, minus the correction budget.
- **The locale chain** (`localeFor()`, recipient → tenant → system) and the layout palette.
- ⛔ **The session.** Nothing in the Session BC changes, and nothing should.
  [`StartSessionUseCase`](../../src/F5Sign/Session/Application/UseCase/StartSessionUseCase.php)
  already converges via `startIfAbsent()` against `signing_session_recipient_uniq`
  `UNIQUE (tenant_id, envelope_id, recipient_id)`, so a second link opens the same session. §6 case 6
  turns that into a locked property instead of an assumption.

## 3. What gets built

- **Route** `POST /envelopes/{id}/recipients/{recipientId}/resends`, declaring
  `Authn::MACHINE_KEY` like every other integrator route, with its controller modelled on
  [`CorrectRecipientController`](../../src/F5Sign/Envelope/UI/Http/CorrectRecipientController.php).
  No request body.
- **`Envelope::resendInvitation()`**, with the §5 D6 guard, recording a new
  `RecipientInvitationResent` contract event carrying envelope, recipient, step ordinal, **resend
  ordinal** and instant — the shape of `RecipientCorrected`, one field renamed.
- **`Recipient` state**: a resend counter and a last-resent instant, both persisted, both feeding
  the guard.
- **`NotificationPurpose::RECIPIENT_INVITATION_RESENT`**, with `namesItsOwnChannel()` returning **false** — an
  ordinary notification, so the selector forms the transport opinion. ⛔ Check what adding a case
  forces by reading that enum's own docblock, which warns that a new case forces *some* of its wiring
  and not all of it.
- **A palette arm** in [`EmailLayoutView::palette()`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailLayoutView.php).
  ⚑ **Reversed at the 2026-08-31 rename, and the reversal is the same argument as the noun.** This
  bullet read *"the amber family, which that method's comment already reserves for reminder … painting
  it blue would make a resend indistinguishable from a first invitation"*, and it shipped that way.
  The resent invitation now **shares the invitation's own blue arm**, glyph included, because it is not
  a different kind of event — it is that invitation again — and amber goes back to the scheduled nudge
  the wireframe reserved it for, which is still unbuilt. What separates the two mails is the copy: the
  eyebrow, the heading and the lead are all rewritten, and unlike a hue that distinction survives a
  monochrome client, an images-off client and a screen reader.
- **EMAIL copy in every authored locale**, and SMS copy in every authored locale (unreachable until
  TASK-031, authored anyway per TASK-030 §5).
- **`OnRecipientInvitationResent`** + its Messenger handler + a `NotifyResentInvitationRecipient` command +
  the use case.

## 4. Scope

**In scope:** everything in §3 and the tests of §6.

**Out of scope:**

- **Revoking the previous link.** It keeps working until its own expiry (§5 D7). Changing that is an
  ADR, not this task.
- **Any guard against resending to a signer who is mid-ceremony.** §5 D8 records the consequence and §7
  carries the question; a guard would need Envelope to read Session state, which is an ADR-level
  cross-BC question and not a scope decision.
- **Scheduled expiry reminders.** [`RemindersSchedule`](../../src/F5Sign/Envelope/Domain/ValueObject/RemindersSchedule.php)
  stays exactly as it is — stored, validated, hydrated, and read by nothing (§7). ⛔ **It is a separate
  feature, not the other half of this one**, and the noun is its: this task ships as a *resend*
  precisely so that the word `reminder` is still free when somebody builds the cadence.
- **Routing to SMS** — TASK-031 owns the selector.
- **The dashboard surface.** This is the integrator API only.
- **Any change to the invitation path**, its idempotency, or `RecipientStepActivated`.

## 5. Key decisions

Eight, and the first three are the ones that decide whether this ships working: what the endpoint
actually does to a credential (D1), which direction the trigger travels (D2), and the one field
whose absence makes the whole feature fail silently (D3).

### D1. It reissues; it does not resend. The distinction is invisible to the recipient and total inside.

The plaintext credential is **gone**. [`IssuedSigningToken`](../../src/F5Sign/Session/Contract/Service/IssuedSigningToken.php)
states it as an absolute: *"This value is the one and only appearance of the secret, and the system
keeps no copy … a credential that is lost between here and the recipient's inbox cannot be recovered,
re-read or resent — it can only be reissued, which mints a different one."* ADR-0045 §2.6 stores a
`sha256` digest and nothing else.

The notification does not hold it either. `Notification::forgetSecretsOnceSettled()` strips `link`
and `code` from the stored variables once **every** delivery of the occasion reaches a terminal
status; `envelope_title` and `recipient_name` survive on purpose, so support can still answer *what
was sent to whom*.

⚑ **Do not "fix" either of those to make a literal resend possible.** Keeping the plaintext to
re-send it reinstates precisely the leak TASK-028 removed, on a surface that outlives the credential.
And it would not even work: the credential's lifetime is seven days, so the common resend case — a
recipient who ignored the mail for a fortnight — would re-send a dead link and a refusal that
explains nothing.

### D2. The trigger is an Envelope event, not a call into Notification.

Envelope records `RecipientInvitationResent`; Notification's own subscriber observes it. That is the
path the invitation, the correction and the completion notice all take, and it is what keeps
ADR-0037's one-way rule intact — Envelope does not learn that Notification exists.

⛔ **Do not reach for [ADR-0051](../adr/ADR-0051-notification-inbound-command-surface.md)'s inbound
command surface.** That narrowing exists for a **user-blocked** side effect — a signer waiting at the
auth screen for a code — and its two members are the OTP pair. A resend blocks nobody: the
integrator fires it and no human is waiting on a response for it. Using the command surface here
would widen an exception that was argued narrow.

### D3. A resend ordinal, and it is the whole feature.

`NotificationId::fromCause()` converges on an identical cause. Without an ordinal in the cause string
the **second** resend finds an existing occasion and returns early — sending nothing, and reporting
success. `NotifyCorrectedRecipientUseCase` already carries `correction:%d` for exactly this reason;
the resend carries `resend:%d`.

⚑ **This is the failure this task is most likely to ship, and it is silent in both directions**: the
integrator gets a 2xx, the recipient gets nothing, and no log line says a send was skipped. §6 case 2
is the only thing that can catch it, and it is the case a lazy fixture never reaches.

### D4. Its own purpose, not a reuse of `RECIPIENT_INVITATION`.

A resend that opens *"se te invita a firmar"* to somebody who has read that sentence once already
reads as a bug in our system rather than as a second try. The copy has to be its own, so the purpose
has to be its own — and the purpose is also what selects the archived pin and the SMS segment budget.

⚑ **Two clauses of this decision were rewritten at the 2026-08-31 rename.** The purpose was called
`RECIPIENT_REMINDER` and this paragraph closed *"the amber family is already reserved for it"*. Both
went: the name because `RemindersSchedule` already owns that noun for the scheduled expiry nudge, and
the colour because §3 now argues the opposite — a resent invitation should look like the invitation.
What survives untouched is the decision itself: **its own purpose, because the words are its own.**

### D5. The minimum interval lives in the aggregate, not in the rate limiter.

`Recipient` holds the last-resent instant and refuses a resend inside the window. It is **not** a
`RateLimiter` policy, for three reasons: this is a business rule about not harassing a signer rather
than infrastructure protection of a costly anonymous endpoint (which is what the existing limiter
guards); the aggregate is already row-locked on this path, so the check is exact where a per-replica
limiter is approximate; and it is hermetically testable without a store.

The window's value was the one open number. **It shipped at 60 seconds — one minute.** It was 900 until 2026-08-31, lowered before the merge on the asymmetry this decision already states: that argument always pointed at the short end, and 900 was further from it than anything required. ⚠ The cost is stated in the constant's own docblock — the practical ceiling per recipient goes from about four an hour to about sixty, against which [`BL-213`](../BACKLOG.md) records that `SMALLINT` is still the only bound. It was chosen as
`MIN_RESEND_INTERVAL_SECONDS`, a private constant on
[`Recipient`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php); read the figure there rather
than from this sentence, which is a copy. It was chosen on this section's own *start where being
wrong is cheap* test, and the two directions are **not** symmetric: too short is corrected by raising
a number and strands nobody, while too long leaves a sender on the phone with a signer, no override
inside the window and no remedy but waiting. So the error was taken on the short side deliberately.
⚠ It remains a judgement and not a measurement — §7 keeps the row open.

### D6. The guard is the aggregate's, and that is what licenses the direct port call.

`resendInvitation()` refuses a terminal envelope, an unsent one, a recipient whose step never
activated, and a leg already closed via `RecipientOutcome::isTerminal()`. That mirrors
`correctRecipientContact()` and it is the *reason* Notification may keep calling `SigningTokenIssuer`
directly: the port's docblock permits Notification's triggers precisely because **only a sent
envelope can fire them**, and this event inherits that property from the guard above. ⛔ Adding the
guard anywhere else — the controller, the use case — leaves the port's licence unearned, and
[ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) is the record of what that
costs.

### D7. The previous link keeps working, and that is stated rather than repaired.

Issuance is additive: two calls produce two live credentials, each until its own expiry. That follows
from ADR-0045 §2.6 and TASK-028 §4.3, which declined revocation on the record and warned against
justifying one with an adjacent gap. So a resend does **not** invalidate what is already in the
mailbox, and the `#[OA\*]` description must say so rather than leave an integrator to assume the
opposite.

### D8. Resending to a signer who is mid-ceremony will bump them, and there is no guard for it.

`StartSessionUseCase` re-issues on re-open and `mintCredential()` discards the previous pair, while
the twelve-hour cap stays anchored to the first mint. So a recipient who is part-way through and then
clicks the new link gets a fresh credential — and, behind a declared gate, a fresh trip to the door.
No progress is lost and the session is the same aggregate, but it is a real interruption.

We accept it and document it rather than guard it, because the guard would require Envelope to read
Session state, which is the cross-BC question §4 puts out of scope. The `#[OA\*]` description says
what a resend does to somebody currently signing.

## 6. Verification

Run through the **worktree lane** — `make -C ../f5sign-infra wt-backend src=$(pwd)`. ⛔ **From a
worktree**, the bare `make test` / `make phpstan` targets bind the main checkout and report green for
another branch.

⚑ **Qualified 2026-08-31, at close.** The ⛔ above was written unconditionally and is only true from a
worktree; this branch was developed **in the main checkout**, which is the tree those targets bind, so
the lane was neither used nor needed. The check that decides which sentence applies to you is
`git rev-parse --git-dir` — a path containing `/worktrees/` means the lane; a bare `.git` means the
bare targets already validate what you edited. The `Status` row records how the binding was verified
rather than assumed.

**Properties to lock:**

1. A resend to an invited recipient produces exactly one new occasion, and the rendered link
   resolves to a credential that opens a session.
2. ⛔ **Two resends produce TWO occasions.** Build the fixture where the second call is *after* the
   interval, so it must succeed. A test that ever sends only one resend passes an implementation
   with no ordinal at all — see D3. Assert on the rendered output of both, not on the commands.
3. A resend inside the minimum interval is refused, with an error distinguishable from every other
   refusal on the route.
4. A resend to a recipient whose leg has closed is refused.
5. A resend to a recipient whose step **never activated** is refused. ⚠ Build the fixture where the
   two populations disagree — a multi-step envelope with a later step still dormant. A fixture whose
   recipients were all invited cannot fail this.
6. ⚑ **The signing session is untouched.** Open a session, take its id and state, resend the
   invitation, open again with the new link, and assert the same session id and the same progress. This is the
   property a resend feature is most likely to break and the one nobody thinks to test.
7. The **previous** link still opens after a resend (D7). This locks an accepted consequence as a
   property, so a later "tidy-up" that revokes on reissue fails here instead of shipping.
8. The rendered body reads as **the invitation sent again** and not as the invitation's own words,
   in the resolved locale, and **every** authored locale authors the purpose — not only the fallback.
9. Each SMS body renders inside one segment.
10. ⛔ **A recipient carrying no address cannot be re-invited, and the refusal costs nothing.** Added
    2026-09-01 by the branch audit, which found the route answering 204, spending the ordinal and
    appending `RecipientInvitationResent` for a mail that never left. The property is the two
    *negatives* — the ordinal stays 0 and no fact is appended — plus `RECIPIENT_HAS_NO_ADDRESS`
    reaching the sender. Locked by
    `EnvelopeInvitationResendTest::a_recipient_with_no_address_cannot_be_re_invited()` and, for the
    guard's position ahead of the step gate, by
    `…_on_a_dormant_step_is_told_about_the_address()`; both sabotage-checked.

    ⛑ **Dated note, 2026-10-13.** [TASK-031](TASK-031-channel-selection-beyond-email.md) retired
    `RECIPIENT_HAS_NO_ADDRESS`: the resend now asks whether the recipient's declared channels would send
    anything ([ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.8). The
    refusal is `RECIPIENT_NOTIFIED_BY_INTEGRATOR` for a recipient who declared `[]` and
    `RECIPIENT_HAS_NO_REACHABLE_CHANNEL` for one whose channels resolve nothing, and it still costs nothing.
    The two tests named above were replaced in `EnvelopeInvitationResendTest` by
    `none_declared_is_refused_as_delivered_by_the_integrator()`,
    `a_list_that_resolves_nothing_is_refused_as_unreachable()` and
    `an_unreachable_recipient_on_a_dormant_step_is_told_they_are_unreachable()`. The text above is the record
    of this task as built.

**Sabotage before trusting any of it** (`CLAUDE.md` authoring rule 4): drop `resend:%d` from the
cause string and confirm case 2 — and only case 2 — goes red. Then restore. If case 2 stays green,
the fixture is not reaching a second resend and the test is decorative.

**Gates:** `WT_GATES="lint arch phpstan test"`, `infection` opt-in. Quote what the lane printed.

⚑ **What ran, 2026-08-31:** the same four gates through the main-checkout targets, plus `infection`
even though it is opt-in — 20 new or changed files under `src/F5Sign` is the *breadth* tripwire
`minMsi` exists for, and `Recipient::resendInvitation()`'s `< 60` is exactly the kind of boundary predicate
aggregate numbers hide. That was the right call twice over: its **per-file** output is what exposed
`ResendRecipientInvitationUseCase` as uncovered and the interval boundary as unguarded, both of which the
aggregate 85 % would have concealed. Numbers in the `Status` row; §8 records what the two findings
cost.

## 7. Open follow-ups (track, don't solve here)

- ⚑ **`RemindersSchedule` is shaped, persisted, validated — and read by nothing.** It is a value
  object with a `fromJson()` that rejects malformed input, a `settings_reminders` jsonb column and a
  hydrator; `Settings::defaultsFor()` always builds `none()`, no endpoint accepts the field, and no
  worker consumes it. ⚑ **Corrected 2026-08-31, at the rename**: this bullet read *"this task is the
  **manual** half of the feature it was shaped for"*, which the header `Blocks` row now records as
  false — a cadence counting down to an expiry and a repair for one lost mail share a verb and nothing
  else. What this task does leave behind is **reusable machinery**, which is a weaker and true claim:
  a purpose, a copy catalog, a reaction and a counter on `Recipient`. ▶ The trigger to build the
  cadence is the first customer asking why reminders are configurable and never arrive. ☑ **Indexed as
  [BL-210](../BACKLOG.md)** (written on the way in, 2026-08-31) — the row exists because a dead setting
  that looks alive is worse than an absent one. Still open; this task deliberately touched none of it.
- ✅ **A successful resend never cleared `DELIVERY_FAILED`, and a failed one could set it — resolved by
  [ADR-0065](../adr/ADR-0065-recipient-delivery-is-its-own-dimension.md), 2026-09-01.** The asymmetry was
  not a missing writer but a modelling error: the delivery fact lived in the leg field, so *clearing* it
  meant claiming the leg had moved. Delivery is now its own dimension, a failure leaves the leg `PENDING`,
  and `correctContact()` returns the dimension to `NOT_ATTEMPTED`. ⚑ **Fully cured as of ADR-0065 step 3**: `markRecipientDeliverySent` exists, Notification
  publishes a `DeliverySent` fact, and a successful resend moves the dimension back off `FAILED`. ⚠ This
  bullet said *"half-cured … still owed"* for exactly one commit, having been written before step 3 and
  not re-read after it.
- ⚠ **This task writes the fourth dead SMS arm, and the copy is written rather than merely stubbed.**
  `NotifyResentInvitationRecipientUseCase` throws `UnroutableChannelException::noDestinationFor()` on
  `DeliveryChannel::SMS`, and `SmsNotificationChannel` carries authored `en`+`es` copy for the purpose
  that nothing can reach — `DefaultChannelSelector` never returns SMS for it. That is **not new here**:
  census it with `rg -n 'noDestinationFor' src/` and re-derive the count rather than trusting one, but
  as of 2026-09-01 the same shape sits in `NotifyCorrectedRecipientUseCase`,
  `NotifyActivatedStepRecipientsUseCase` and `NotifyCompletedEnvelopeRecipientsUseCase`, all three on
  `develop`. ⛔ **The consequence is about the set, not this member**: copy already exists in four
  places behind a deferred receipt seam, so the branch that finally gives one of these purposes an SMS
  destination lights several arms at once, and nothing in *that* change points back at the seam. This
  task neither widens nor narrows it; recorded so the fourth member is not mistaken for the first.
  (Surfaced 2026-09-01 by the `docs/outbound-webhooks` session while auditing the receipt seam; its
  backlog row is not on `develop` yet, so it is deliberately not cited here.)
- **Whether a resend should kill the previous link** (D7). Revocation was declined on the record and
  the mechanism does not exist. ▶ The trigger is a security review objecting to N live credentials per
  recipient. It is an ADR, and TASK-028 §4.3's warning binds it: storage makes revocation possible
  and does not make it a feature.
- **Bumping a signer who is mid-ceremony** (D8). ▶ The trigger is a real complaint. The fix needs
  Envelope to read Session state, which is an ADR-level cross-BC question, so it arrives as a decision
  rather than a patch.
- **The interval's value** (D5), which shipped as a judgement rather than a measurement: **60 s / 1 min** since 2026-08-31, reasoned in D5 and recorded in §8. ▶ The trigger is either half of the asymmetry showing
  up in the field — a sender blocked by a window that is too long, or a recipient complaining about a
  second mail. Nothing measures it today and nothing will until one of those arrives.
- ⚠ **The interval counts resends and nothing else, so *correct-then-resend* sends twice inside the
  window.** A recipient re-invited through the corrections endpoint — the workaround §1 exists to
  retire — lands with `corrections_made > 0` but `resends_made = 0` and `last_resent_at IS NULL`,
  so the guard sees a recipient who has never been re-invited and lets the resend straight through.
  Defensible (they are different facts, and a correction is itself a repair) and **left as it is**:
  the alternative couples two counters whose meanings differ, which is the confusion this task exists
  to remove. ▶ The trigger is a signer receiving two mails minutes apart and saying so. Indexed as
  [BL-212](../BACKLOG.md).
- ⚠ **`SMALLINT` is the only ceiling on `resends_made`.** Unlike `corrections_made`, which
  `Recipient::MAX_CORRECTIONS` bounds in the domain, nothing bounds a resend by count — deliberately
  (D5 bounds it in time). So crossing 32767 surfaces as a DBAL *numeric value out of range* inside
  `save()`, i.e. a 5xx rather than a domain refusal carrying a `code`. Reachable only by a looping
  integrator against one recipient for 32767 resends at the `Recipient::MIN_RESEND_INTERVAL_SECONDS`
  floor — roughly **23 days** at today's 60 s, and re-derive it from the constant rather than quoting that
  number: it read *"341 days at the 15-minute floor"* until 2026-09-01, computed while the floor was 900 s.
  Loud rather than corrupting when it lands. ▶ The trigger is either the first sighting or a domain reason to cap
  resends at all; today there is none. Indexed as [BL-213](../BACKLOG.md). (⛑ 2026-10-15: TASK-057 found one for a
  recipient reached by SMS, spend, and caps it at five plus an operator's grant; the email-only case stands as written.)
- **A sender-facing count of resends sent.** The data exists on `Recipient` after this task; nothing
  exposes it. Dashboard concern.
- **The same gesture for the other notification occasions.** Nothing re-sends a completion notice
  either; whether that matters is the same question one step over.

## 8. Deviations & honest notes

Written at close on 2026-08-31, alongside §7's disposition. It is the **last** section and nothing
above it was renumbered, because `§N` are anchors cited from other records.

### The concept shipped under a noun another feature already owned

The whole feature landed as a **reminder** — `POST …/reminders`, `RemindRecipient`,
`NotificationPurpose::RECIPIENT_REMINDER`, `Recipient::remind()`, `last_reminded_at`,
`RECIPIENT_REMINDED_TOO_RECENTLY` — and that word was already taken, in this repo, by
[`RemindersSchedule`](../../src/F5Sign/Envelope/Domain/ValueObject/RemindersSchedule.php): the
`daysBeforeExpiry` cadence on `Settings` that models *"nudge 14, 7 and 1 days before this envelope
expires"*. Renamed on 2026-08-31 to **resend** throughout, before the branch merged.

⛔ **The cost was not ambiguity, it was that the record argued from it.** The header `Blocks` row and
[BL-210](../BACKLOG.md) both claimed this endpoint was *"the manual half of the automatic reminders
`RemindersSchedule` was shaped for"* — and once written, that sentence makes the cadence look
half-built rather than unstarted, and makes this task's counter, copy and reaction look like parts of
it. They are not: one counts down to a deadline for a recipient who is merely slow, the other repairs
a single invitation that never arrived. Different trigger, different population, different words. Both
records now say so, and BL-210 stands on its own.

⚑ **The palette went with the noun** (§3, §5 D4): the resent invitation now shares
`RECIPIENT_INVITATION`'s blue arm and amber returns to the wireframe family reserved for the cadence,
unclaimed. ⚑ **And so did the copy** — EMAIL and SMS, `en` and `es`. It read *"your signature is still
needed" / "sigue pendiente su firma"*, which asserts the recipient is late; nothing here knows that,
and the ordinary case is a first invitation that was filtered or never arrived. It now asserts only
what we did: *the invitation, sent again*.

⚠ **The branch name `feat/recipient-invitation-reminder` was NOT renamed**, deliberately — it is
pushed, and a branch name is not a surface anybody reads for meaning. The `Status` row above names it
as it is rather than as it should have been.

### The migration collided with another branch, and the loud failure is not the one that matters

`Version20260831000001` — the number this task first minted — already named a **different** migration,
of the same class name and the same path, on `feat/delegated-signature`: the six `asserted_*` columns
on `session.signing_session` (ADR-0055 / TASK-033). Both were unpushed, both targeted `develop`. Ours
renumbered to `Version20260831000002`, because ours was the later of the two by authored time (13:38
against 12:29), and the loser of that tie is the one that moves.

⚑ **The merge conflict is loud; the real cost is silent.** `doctrine_migration_versions` records the
version **string**, not the file's content — so on any volume that had already run *either* copy,
`make migrate` finds the string recorded, reports success, and creates **neither** column. A green
migrate and a schema missing what the code reads.

⚠ **This actually bit during the run, in its mirror form.** After the renumber, the dev volume still
carried the old string and had never seen the new one, so the migration ran a second time and
`make test-db-setup` died with `column "resends_made" of relation "recipient" already exists`. It was
cleared with `make -C ../f5sign-infra test-db-reset`, which is the remedy — there is no code change to
make. ▶ **Anyone who ran this branch before the renumber will hit exactly that**, and the fix is that
reset.

The mechanism is generic to this workspace — six sibling worktrees minting `VersionYYYYMMDDNNNNNN`
against the same `develop` — so it is indexed as [BL-211](../BACKLOG.md) rather than left here.

### Scope

- **Two additions beyond §3, both deliberate, both recorded as scope deviations.**
  - `5a0dcbe` — one paragraph on **`CorrectRecipientController`**'s `#[OA\*]` description pointing at
    the new route. The cross-reference was one-way: the resend explained how it differed from
    corrections, and corrections said nothing back — so the integrators using corrections as a resend
    today, which is the entire population this task exists for, had no path in the published spec to
    discover the cheaper route. Raised independently by two reviewers, which is why it is here rather
    than deferred.
  - `4839128` — the **`docs-sync` sweep**: the owed handoff
    ([`TASK-041-invitation-resend.md`](../frontend-handoff/TASK-041-invitation-resend.md)),
    `docs/LIVE_SCHEMA.md`, and both `docs/ddd/` domain models. ⚑ The half that was not merely owed
    but **falsified** is
    [`2026-08-21-no-sender-side-otp-resend.md`](../frontend-handoff/2026-08-21-no-sender-side-otp-resend.md),
    whose route list closed with *"las cinco rutas de remitente … son, y **seguirán siendo**"*. The
    clause this change broke is `seguirán siendo`, not the count: a decided absence covering the OTP
    code had been extended, by the shape of the sentence, over the whole list. Corrected and dated
    there; no `Status` was flipped, because the dashboard's tree was not read.
- **Files the diff touches that §3 never named**, none of them new behaviour and all of them
  authoring-rule surfaces — enumerate them with `git diff --name-only develop..HEAD`, not from this
  list: `config/packages/nelmio_api_doc.yaml` (the published `code` enum is a closed enumeration the
  two new refusals must join), `NotifyCorrectedRecipient.php` (docblock count only), and the two
  censuses plus the frozen payload fixture that force the new member to be classified —
  `ReactorConvergenceTest`, `SigningReadersRefuseUnsentEnvelopeTest::ISSUER_CALLERS` and
  `tests/Fixtures/event-payloads/RECIPIENT_INVITATION_RESENT.json`. ⚑ The validation report called
  this set *"four"* while naming five, which is the count-rot shape twice over; the number is dropped
  here rather than corrected.
- **ADR-0037 prose** (`7485b16`) — see below.
- ⚠ **The handoff documents are written in Spanish, against the general English rule.** Every document
  already in `docs/frontend-handoff/` is Spanish and the section template in that directory's own
  README is Spanish (`## Lo que cambió en el contrato`, …). The audience is a reader working in
  `f5sign-dashboard` / `f5sign-signer`; a lone English document in that set would read as a different
  kind of record. Stated rather than quietly done, because it is a deviation either way.

### Decisions taken during implementation

- **The interval is 60 seconds** — D5's one open number, now recorded there too. It shipped at 900 and was lowered before the merge; §5 D5 carries both the argument and the cost. Chosen
  on *start where being wrong is cheap*, and the two directions are not symmetric: too short is fixed
  by raising a number and strands nobody, too long leaves a sender with no override and no remedy
  inside the window. The error is taken on the short side on purpose.
- **Its own exception type, `RecipientNotResendableException`**, rather than reusing
  `RecipientNotCorrectableException` — whose docblock and both factories are about a *contact
  correction*, so reusing it would have made a refusal explain the wrong thing.
- **No step gate in the Notification use case**, unlike its correction sibling: a resend cannot
  arrive for a dormant step (the aggregate refuses first), so the copied gate would be a guard that
  can never fire and a second home for a rule ADR-0058 §2.3 places on the aggregate.
- **`carriesMeansToAct()` is `true`** — an undeliverable resend has to open the correction path.
- **`resendsMade` is unbounded, where `correctionsMade` is capped at three** (for a recipient reached only by email
  since TASK-057, which caps an SMS recipient at five plus an operator's grant). A correction rewrites who
  receives a document others consented to send; a resend rewrites nothing. Time bounds it (D5), not
  count. The cost of that choice is the `SMALLINT` ceiling — §7 and [BL-213](../BACKLOG.md).
- **`last_resent_at` is deliberately NOT backfilled.** `NULL` is what lets a pre-existing recipient's
  first resend through; any backfilled instant would lock untouched rows out of the feature with no
  API to clear it. `resends_made` backfills to `0` under the same reasoning (authoring rule 6: the row
  means *"never re-invited"* on the write side in every aggregate state, not merely on the read side).
- **`RECIPIENT_LEG_CLOSED` is reused verbatim** from the correction path — the same fact, and
  integrators already branch on that string — while the two genuinely new refusals get published
  `ProblemCode` members in the same changeset that introduces them.

### Decisions that needed an ADR

**None**, and the `Decision record` row predicted it: the reaction stayed inside the existing one-way
edge, the new minting site enrolled in the existing census, no cross-BC dependency opened, and
`deptrac.yaml` / `phpstan.dist.neon` / the baseline were untouched. **No ADR moved to `Proposed` or
`Accepted` on this branch.**

⚑ **ADR-0037 was edited, and that is not a decision change.** Four counts in its body had gone stale —
*"Two purposes already share it"* and three occurrences of *"three reactions / three use cases"*, all
of which were accurate on `develop` and false at `HEAD` (four boundary reactions, four `Notify*`
use cases, measured). They were replaced with a **property rather than a fresh number**, because these
lines have now rotted once and a count rots again on the next member. ⛔ The count inside the ADR's
`Status` field was left alone on purpose: it records what exercised the decision **at acceptance**,
which is a description of the past and correct as written.

### Properties declared and not proved

- ⛔ **The migration's backfill semantics are reasoned and reviewed, not exercised.** This repo has no
  harness that can run one migration over a fixture it wrote first (migrate to N, seed, migrate to
  N+1, assert), so nothing proves that a backfilled `resends_made = 0` / `last_resent_at IS NULL`
  row behaves like an authored one. The home for that gap already exists —
  [`BL-179`](../BACKLOG.md), filed from TASK-032 — and this task adds a second instance rather than a
  second row. Until such a harness exists the property rests on `doctrine-guard`'s state census plus
  the `up()`/`down()`/`up()` round trip, which is a review and a smoke test, not a test of meaning.
- **SMS copy is authored and measured but unroutable.** §6 case 9 proves each body fits one segment;
  nothing proves a resend ever *travels* over SMS, because `DefaultChannelSelector` gives
  `RECIPIENT_INVITATION_RESENT` → `[EMAIL]` and TASK-031 owns the selector. Declared in §3, restated here so
  the authored copy is not mistaken for a live channel.
- **Everything else in §6 executes.** Every property runs — count them from §6 rather than here, which said *"all nine"* until a tenth landed on 2026-09-01 — and the sabotage §6 names by hand
  reddened case 2 at both tiers and nothing else.

### What validation caught that no gate could see

Five findings, none of which lint, Deptrac, PHPStan or the suite could have produced:

- ⛔ **The published contract denied its own route.** The `#[OA\Post]` description said
  `POST …/corrections` *"is the only way to do this today"* **inside the description of the route that
  makes it false**, and contradicted itself two clauses later. It is emitted verbatim into the spec the
  frontend ratifies, so it was telling integrators to keep spending corrections on resends — the exact
  defect this task exists to remove. Fixed in `7485b16`; the clause went, the contrast it carried
  stayed.
- ⚑ **§6 case 6 was decorative.** `assertSame($before->sessionId, $after->sessionId)` **could not
  fail**: `SigningSessionId::fromScope()` is a UUIDv5 of `tenant|envelope|recipient`, none of which a
  resend touches, so the two ids were equal by construction before `startIfAbsent()` was even reached,
  and the failure the assertion's own message described was unreachable. The `status` half was no
  better — a recipient declaring no gate reports the same status from first open to last, so the
  fixture had no progress to compare. Reworked in `27c65e4`: the recipient now passes a declared
  `ACCESS_CODE` gate **before** the resend, which gives the ceremony durable progress a resend could
  roll back, and the *"a second session beside it"* claim is falsified separately by
  `count(*) FROM session.signing_session = 1` — which comparing two ids derived from an unchanged
  scope can never do.
- **`ResendRecipientInvitationUseCase` shipped as the only one of the nine in
  `Envelope/Application/UseCase/Lifecycle/` with no sibling-tier test** — authoring rule 4's named
  signal, verbatim, and Infection agreed by reporting its body Not Covered. What that left unpinned
  mattered more than the missing file: nothing asserted it reaches for `findLockedForUpdate` rather
  than `find`, and without the lock two concurrent resends read the same ordinal, write two facts
  carrying one cause token and produce **one** occasion — 204 to both senders, one mail to the
  recipient, which is D3's silence arriving by another door. Closed in `62353e9`.
- **The interval boundary was unguarded** (`9a04a8c`). `Recipient::resendInvitation()` compares with `<` and its
  docblock calls the strictness deliberate, but the test file probed `+1 minute` and `+1 day` only —
  instants where `<` and `<=` agree. Two cases one second apart now locate the line.
- **ADR-0037's stale counts**, above.

**Ten sabotages were run across the branch and every one was restored**, each verified by an empty
`git diff` afterwards. They are named in the commit messages that carry them, which is where the
argument for each test's discriminating power actually lives.

### Honest notes

- ⚠ **One flake, not reproduced.** `DeliveredCodeCeremonyHttpTest` failed once on an intermediate run
  and never again: **7 clean samples afterwards** (two full-suite runs plus five consecutive isolated
  ones), no semantic path from this diff to that test — every change it could touch is additive: a new
  enum case, a new arm in an exhaustive `match`, a new palette entry, new copy — and no shared-state
  path either. Stated as *not reproduced in 7 samples*, **not** as proved absent, per
  [`BL-140`](../BACKLOG.md)'s rule that the sample count belongs with the claim; the shape is
  [`BL-139`](../BACKLOG.md)'s.
- **The censuses behaved exactly as their two shapes predict, which is worth recording as evidence
  for the pattern.** `SmsCopyTest`'s data provider enumerates `NotificationPurpose::cases()`, so the
  new member **enrolled itself** with no diff to that file at all; `OpenApiSpecTest` and
  `SchemaConformanceTest` stayed green untouched. `ReactorConvergenceTest` and
  `SigningReadersRefuseUnsentEnvelopeTest::ISSUER_CALLERS` had to be **edited to classify** the new
  member — that is not the pattern failing, it is authoring rule 5's *census the universe, classify,
  and fail on the unclassified* working: neither would go green until somebody said, in writing, what
  the new reaction and the new minting site are.

### Debt left, and where it lives now

| What | Home |
|---|---|
| Scheduled expiry reminders — `RemindersSchedule` still read by nothing, and a separate feature | §7 + [BL-210](../BACKLOG.md) |
| The migration-version collision mechanism (silent no-op across branches) | §8 above + [BL-211](../BACKLOG.md) |
| Correct-then-resend sends twice inside the window | §7 + [BL-212](../BACKLOG.md) |
| `SMALLINT` as the only ceiling on `resends_made` | §7 + [BL-213](../BACKLOG.md) |
| No harness proves a migrated row means what an authored one means | [BL-179](../BACKLOG.md) (pre-existing; this task is a second instance, not a second row) |
| Whether a resend should kill the previous link (D7) | §7 — ADR-level, TASK-028 §4.3 binds it |
| Bumping a signer mid-ceremony (D8) | §7 — ADR-level cross-BC question |
| The interval's value as a judgement rather than a measurement | §7 + D5 |
| A sender-facing count of resends sent | §7 — the data exists on `Recipient`; nothing exposes it |
| The same gesture for the other notification occasions | §7 |
| The acceptance-suite flake shape | [BL-139](../BACKLOG.md) / [BL-140](../BACKLOG.md) |
