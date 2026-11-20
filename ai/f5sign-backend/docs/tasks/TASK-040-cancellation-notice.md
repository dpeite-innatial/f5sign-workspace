# TASK-040 — Telling a recipient their envelope ended without agreement

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/ending-notice`** (tip `41362564`), 2026-09-29 — it reached `develop` with the ADR-0073 package, merged into `develop` on 2026-09-30 at `e6a0af5e` (⛑ corrected 2026-10-01; this read "not merged"). Commits, oldest first: `5be70b77` spec fix, `bc02eaa2` purposes and copy, `15908cdd` reactor, use case and audience, `0273fc33` `#[OA]`, `aba1614f` closed-envelope guards, `5e1a6aa9` merge of `feat/step-policy`, `7e7945a8` ADR-0059/0070 sweep, `b6bee27d` TASK-038/046 sweep, `5715b3c7` `#[OA]` SMS sentence, `5d57c4a1` docblock, `c3548175` and `41362564` docs-sync. Harness: the `wt-backend` lane bound to this worktree. Last green at `5e1a6aa9`: lint 0/1466, deptrac 0/0, phpstan OK, fast tiers 3589 tests / 15898 assertions; the slow tiers ran **filtered only** (32 tests, green). **Not run, by the package rule:** Infection and the full Integration/ and Acceptance/ suites, which run once over the joined ADR-0073 package (§8). Falsifiable: `grep -n "case ENVELOPE_ENDED" src/F5Sign/Notification/Domain/ValueObject/NotificationPurpose.php` now matches on this branch. Review: the package was merged (see above). |
| **Type** | **Forward build, plus one published-contract change.** A new notification occasion on an existing seam — no new BC edge, no new transport, no new decision about who may notify whom. ⚠ **But it is not confined to Notification**: making the sender's reason recipient-facing (§5) changes the `#[OA\*]` on `VoidEnvelopeRequest::$reason` in `Envelope/UI/`, which is emitted into the spec the frontend team ratifies. Additive to the spec — no field, code or status moves — but it re-describes what an existing field is **for**, which no gate can detect. |
| **Why** | Every ending without agreement — the sender's void, a blocking decline, a veto, the minimum out of reach, a missed step deadline, an unreached member of a veto step, the expiry — **closes** the envelope and records [`EnvelopeVoided`](../../src/F5Sign/Envelope/Contract/Event/EnvelopeVoided.php) at the decision (ADR-0073 §2.2, §2.11), and **nobody tells the recipient**. The void does not end the lifecycle — the status stays `SENT` until every signature admitted before the close has landed and the one seal path reaches `COMPLETED` (ADR-0073 §2.5) — but from `closed_at` no act is admitted, and a recipient who neither signed nor is informational is refused every read and every pass of the gate (ADR-0073 §2.15). A signer invited yesterday still has the link in their inbox and no reason to think anything changed; when they follow it they meet a refusal with no explanation of *why*. |
| **Builds on** | **[TASK-048](TASK-048-what-an-unagreed-envelope-keeps.md) — a prerequisite, not a sibling: branch from `feat/task-048-how-an-envelope-ends`.** It is what makes `EnvelopeVoided` carry an [`EndCause`](../../src/F5Sign/Envelope/Contract/Type/EndCause.php) and the party that cause names, what added `NotificationPurpose::isInvitation()`, and what put the `outcome` guard in `NotifyCompletedEnvelopeRecipientsUseCase` that keeps a `NOT_AGREED` `EnvelopeCompleted` silent there. **[ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md)** §2.2/§2.11 (an ending without agreement is `EnvelopeVoided` at the decision), §2.5 (`end_cause` and its members), §2.12 (expiry is `EnvelopeVoided` with cause `EXPIRED`). **[TASK-046](TASK-046-a-recipient-may-decline.md)** for the decline that writes `RECIPIENT_DECLINED`. **[ADR-0037](../adr/ADR-0037-notification-supporting-bc.md)** — Notification is a category-(c) supporting BC and this changes nothing about that. The reactor shape is [`OnEnvelopeCompleted`](../../src/F5Sign/Notification/Application/Subscriber/OnEnvelopeCompleted.php) and its handler, copied rather than invented. **[ADR-0038](../adr/ADR-0038-template-archive.md)** for the pin-at-creation template archive, **[TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md)** for the locale resolution chain, **[TASK-030](TASK-030-sms-delivery-channel.md)** §5 for the SMS segment budget a new purpose inherits. |
| **Decision record** | **None, and that is the finding rather than an omission.** Every cross-cutting question this touches is already decided: ADR-0037 owns the BC's category, [ADR-0031](../adr/ADR-0031-event-log-store.md) the delivery path, ADR-0073 the fact, its causes and its timing, and the selector's purpose→channel mapping is [TASK-031](TASK-031-channel-selection-beyond-email.md)'s. ADR-0073 decides **one** notice — §2.15's copy-ready notice at `COMPLETED`, which is [TASK-050](TASK-050-a-step-says-how-much-agreement-it-needs.md)'s — and says nothing about telling recipients of the decision itself. What is left is copy, audience and idempotency — all task-level; the maintainer's decision of 2026-09-29 on which endings are told and how is recorded in §5. ⛔ If implementing this turns out to need a second sibling `Contract` read, **stop**: ADR-0037 makes that an ADR-level question (`BL-76` records what the last attempt cost). The cause and the sender's reason ride the event itself, so none should be needed. |
| **Delivery bar** | Every `EnvelopeVoided`, whatever its `end_cause`, produces exactly one notification per recipient **the platform actually wrote to**, in that recipient's resolved locale, in the copy of that cause's family (§9). Over HTTP on this branch: a sender's void notifies with the sender's reason when one was given and the no-reason body when it was not; a blocking decline in an `ALL` step notifies with the *a participant declined* copy, naming nobody. The causes with no writer yet (§9) are held at the use-case tier. A recipient whose step never activated gets nothing. A redelivered `EnvelopeVoided` produces no second notice. ⛔ **Not shippable without the `#[OA\*]` change of §5** that tells senders the text reaches the recipient. |
| **Sibling** | **[TASK-050](TASK-050-a-step-says-how-much-agreement-it-needs.md)**'s copy-ready notice (ADR-0073 §2.15) — **cross-referenced, not absorbed** (§5). **[TASK-049](TASK-049-an-envelope-expires.md)** and TASK-050, whose clock- and policy-driven endings reach this notice with no further wiring once they land (§9). |
| **Blocks** | Nothing. ⚑ **Its value rose on 2026-08-26**, when [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md) landed and the link started refusing: a recipient who follows a closed link now meets a 409 with no explanation of *why*, which is the gap this task fills. It rises again with TASK-049 and TASK-050: every ending they add is an `EnvelopeVoided` nobody is told about until this lands. |

---

## 1. Why this task exists

`EnvelopeVoided` is recorded at every decision that ends an envelope without agreement — the sender's
`Envelope::void()` and every admission or evaluation the aggregate's ending evaluator decides against the
agreement — with tenant, envelope, cause, the party that cause names (an actor for the sender's void, a
recipient for a decline or a veto, nobody for an ending no party decided), the sender's reason and the
instant. ⛔ **It is the instant the envelope CLOSED, not the instant it ended** (the event's own docblock;
ADR-0073 §7.8 is why it was not moved to the end). Two subscribers consumed it before this task:
[`Session\Application\Subscriber\OnEnvelopeVoided`](../../src/F5Sign/Session/Application/Subscriber/OnEnvelopeVoided.php),
since TASK-038, which revokes every live signing session on the envelope, and Evidence & Audit's
`OnEnvelopeVoided` (retired 2026-10-01: the trail is now issued at `EnvelopeCompleted`), which
issued the envelope's audit trail ([ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md)
§2.10). **Notification does not consume it**, and neither of the two tells the recipient. `NotificationPurpose` has five occasions — the invitation, its
resend, the completion notice and the two one-time-code purposes — and none of them is an ending without
agreement.

A recipient with a live link on a closed envelope meets the refusal TASK-038 and ADR-0073 §2.9/§2.15 give
it, correctly — and in closing the ceremony that converts *silence plus a working link* into *silence plus
a refusal*, which is the worse of the two for the person holding it. ⚑
[ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.5 already decided that a closed
leg is **published rather than hidden**, on
[ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md)'s reasoning; that makes the ending
legible to someone who **comes back** to the link. It does not reach out to someone who does not, which is
this task.

⚑ **The notice hangs on `EnvelopeVoided`, not on a `NOT_AGREED` `EnvelopeCompleted`.** The decision is what
the recipient needs to hear, and the end can be hours later while an admitted signature waits on DSS
(ADR-0073 §2.17). `EnvelopeCompleted` at `COMPLETED` is where a *different* notice lives — §2.15's
copy-ready notice, TASK-050's (§5).

## 2. What already exists (reuse, do not rebuild)

- **The reactor pair, verbatim in shape.** [`OnEnvelopeCompleted`](../../src/F5Sign/Notification/Application/Subscriber/OnEnvelopeCompleted.php)
  is a pure `Reactor` translating an Envelope fact into a Notification command, with its Messenger
  handler beside it on `event.bus`. Copy the shape; ⚠ the repo's authoring rule 3 applies — read
  **every** sibling subscriber in `src/F5Sign/Notification/Application/Subscriber/` before copying one,
  because where two differ the difference is either a bug or a decision.
- **The occasion + per-channel `Delivery` fan-out**, the deterministic `NotificationId::fromCause()`
  token, the resolve-at-creation contact and the pin-at-creation template. All of it is in
  [`NotifyCompletedEnvelopeRecipientsUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyCompletedEnvelopeRecipientsUseCase.php),
  which is the closest analogue **for the mechanism only**: one notice per recipient, fanned out from one
  Envelope fact. ⚠ Not for its trigger or its audience — since ADR-0073 §2.5 `EnvelopeCompleted` fires for
  both outcomes, and that use case now returns early unless `outcome` is `AGREED`. Leave that guard alone:
  it is what keeps a `NOT_AGREED` envelope from being told it was signed.
- **The locale chain** — recipient → tenant → system — already implemented as `localeFor()`.
- **The event, the cause and the reason.** `EnvelopeVoided` carries `cause` (an `EndCause`) and the
  sender's `reason`; its constructor refuses a reason on any cause but `SENDER_VOIDED`, and a decline's
  free text rides `SessionDeclined` alone (ADR-0070 §2.7's plaintext exception). No new Envelope fact is
  needed and none should be added.
- **The invitation occasions** — `envelope:<id>|recipient:<id>|purpose:RECIPIENT_INVITATION` from the
  activation fan-out, and `…|purpose:RECIPIENT_INVITATION|correction:<N>` from a contact correction — which
  §5's audience predicate reads, through Notification's own repository.

## 3. What gets built

- **Five `NotificationPurpose` cases, one per copy variant of §9** — four families, the sender's split in
  two by the presence of a reason. Provisional names: `ENVELOPE_ENDED_SENDER_CANCELLED`,
  `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON`, `ENVELOPE_ENDED_DECLINED`, `ENVELOPE_ENDED_TIME_RAN_OUT`,
  `ENVELOPE_ENDED_OUT_OF_REACH`. The names may change; the count follows from how copy is keyed (§5) and a
  different count is a deviation for §8. Each is classified in **every** exhaustive `match` of §5 —
  `namesItsOwnChannel()` **false** (an ordinary notification: the selector forms the transport opinion,
  which is `EMAIL` for everything until [TASK-031](TASK-031-channel-selection-beyond-email.md)),
  `carriesMeansToAct()` **false**, `isInvitation()` **false**.
- **The cause → family map**: an exhaustive `match` over `EndCause` with **no `default`**, in
  Notification's **Application** layer (the Domain may not read `EnvelopeContract`, `deptrac.yaml`
  `NotificationDomain`), naming each member's family as §9 decides; and the family (+ reason present) →
  purpose step.
- A palette entry per purpose in [`EmailLayoutView::palette()`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailLayoutView.php).
  ⚑ **The red family** for all five, which that method's own comment names as *"refusal"* and nothing
  uses yet (its families: blue *"please act on a document"*, green *"the arc closed"*, amber
  *"reminder"*, red *"refusal"*). Every ending without agreement is one event kind to the recipient;
  painting any of them green or blue would make an envelope dying look like an envelope succeeding.
- An arm per purpose in `EmailNotificationChannel::htmlTemplate()` (`layout.html.twig`, as the envelope-arc
  purposes).
- EMAIL copy in every authored locale, and SMS copy in every authored locale, for each of the five (§9).
- The `#[OA\*]` and docblock change on `VoidEnvelopeRequest::$reason` telling senders the text reaches
  the recipient (§5). ⛔ Same changeset, or the notice ships ahead of the contract that permits it.
- `OnEnvelopeVoided` (Notification) + its Messenger handler + a `NotifyEndedEnvelopeRecipients` command
  carrying the envelope id, the cause and the sender's reason taken from the event + the use case.
- The `NotificationPurpose` class docblock's account of what notices a missing copy is corrected while
  the file is open: it still says only the fallback-locale test notices, which §5 shows is no longer
  true.

## 4. Scope

**In scope:** everything in §3 and the tests of §6.

**Out of scope:**

- **Notifying the sender.** They performed the action, or — for a clock-driven ending — the dashboard
  shows the outcome; a confirmation is a dashboard concern.
- **The copy-ready notice at `COMPLETED`** (ADR-0073 §2.15) — [TASK-050](TASK-050-a-step-says-how-much-agreement-it-needs.md).
  §5 says how the two relate.
- **Routing this anywhere but email** — [TASK-031](TASK-031-channel-selection-beyond-email.md) owns the
  selector. The SMS copy is authored anyway (§5) and is unreachable until then.
- **Any change to `void()` itself**, its guard, its transitions or its response codes, and **any change
  to how an ending is decided or recorded** (TASK-048/049/050). ⚠ **One carve-out, and it is not
  optional**: the `#[OA\*]` string and docblock on `VoidEnvelopeRequest::$reason` change here, because §5
  makes that field recipient-facing and the published contract must say so before the notice ships. That
  is the **only** part of the void endpoint this task touches, and it touches a second BC
  (`Envelope/UI/`) to do it.
- **The read-side refusal a returning recipient meets** — TASK-038, and ADR-0073 §2.9/§2.15 (TASK-048).
- **Writers for the causes that have none yet** — `STEP_DEADLINE_MISSED`, `EXPIRED`, `MEMBER_NOT_REACHED`
  and, until `send()` accepts a completion policy, `RECIPIENT_VETOED` and `MINIMUM_UNREACHABLE` are
  TASK-049's and TASK-050's. This task authors their copy and maps them; it does not make them reachable.
- **Backfill.** Envelopes that ended before this ships notify nobody.

## 5. Key decisions

- ⛔ **Every ending without agreement is told, by one mechanism, with copy chosen by cause — decided by the
  maintainer 2026-09-29, replacing the deferral this task's §7 carried.** Every `EnvelopeVoided`, whatever
  its `end_cause`, produces the notice to the recipients the platform actually wrote to; there is one
  reactor, one command, one use case and one audience predicate, and the cause picks the copy. The
  members of `EndCause` are grouped into a **small closed set of copy families** (§9), and the grouping is
  an exhaustive `match` with no `default`: an `EndCause` member nobody classified is a static-analysis
  failure (PHPStan's unhandled-match check at level 9) and a red census (§6 case 9), **never** a fallback
  to some family's words. ⚑ Why this and not a filter: `EnvelopeVoided` already couples the causes —
  expiry, deadlines, vetoes and unreachable minimums are all recorded through it (ADR-0073 §2.12, §2.6) —
  so a reactor listening to it would have told every one of them *"cancelled"* by construction the day
  their writers landed. A `default` arm would reproduce exactly that for the next cause added.
- ⛔ **The notice goes only to recipients the platform actually wrote to, and the predicate is
  Notification's own record of having written**: *Notification holds a `RECIPIENT_INVITATION` occasion
  for this recipient on this envelope*, answered by a query on `NotificationRepository` over the
  subject/addressee it already indexes — no new field, no schema change, no cross-BC read and no guess.
  ⚠ **Not `find()` on the base token** `envelope:<id>|recipient:<id>|purpose:RECIPIENT_INVITATION`, which
  this bullet named until the claims check of 2026-09-29: the activation fan-out skips a recipient with no
  email, and when a contact correction later gives them one on an active step,
  `NotifyCorrectedRecipientUseCase` invites them under `…|correction:<N>` with no base record — a person
  holding a live link whom the base-token lookup never finds (§6 case 2b). Resends are not counted: one
  always follows a base or correction occasion. The Envelope view's `invitationSentAt` /
  `invitationFailedAt` were weighed and refused: delivery propagation writes them asynchronously, so an
  invitation still `PENDING` would drop out. ⛔ If the query turns out to need a migration or an index,
  stop: that is outside this task's scope as decided. ⚠ **Do not copy the completion
  notice's audience.** It notifies every recipient with an email, which is right there — everyone on an
  agreed envelope has a claim on the sealed copy — and wrong here: a recipient in a step that never
  activated was never told the envelope existed, and *"the document you were asked to sign will not go
  ahead"* would be the first they hear of it. That is a disclosure with nobody to serve, and it is the same
  axis [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.4 states for refusals.
  Under ADR-0073 §2.8 such a member is released `NOT_REACHED` and has no invitation on file, so the
  predicate yields nothing for them. ⚑ A recipient whose invitation **bounced** — released
  `DELIVERY_FAILED` — still gets one: the occasion exists, we did try to write, and a second failure costs
  nothing.
- ⚑ **The deciding recipient is inside the audience, and the copy is written to be true for them.** A
  decliner or a vetoer was invited, so the predicate includes them; the *declined* family's copy says a
  participant declined and **names nobody**, so it reads as a confirmation to the decliner and discloses
  no identity to anyone else. No family's copy names a party, carries a link, or says anything either
  way about signatures or a copy of the document (§6 case 8). Keeping the decider in is the maintainer's decision of 2026-09-29 (§7).
- **The sender's reason is carried by the sender family only — decided by the product owner 2026-08-25
  for the void, reversing this bullet's first draft.** A signer told only *"cancelled"* cannot tell whether
  to expect a replacement envelope or to stop waiting, and that is the question the notice exists to
  answer. `EnvelopeVoided` refuses a reason on every other cause, so the other families have no reason
  slot at all. ⛔ **But the field changes meaning, and three things follow that are not optional.**

  1. ⛔ **The published contract must say so, in the same changeset.** `VoidEnvelopeRequest::$reason`
     today carries only a length bound and a docblock calling it *"the optional reason"* the sender gives,
     landing *"in the append-only event log"* — which reads as internal, and senders have had every
     reason to treat it that way. Its `#[OA\*]` string is emitted verbatim into the spec the frontend
     team ratifies (the repo's authoring rule 1 names those strings as a top rotting surface), so it
     must state that the text **reaches the recipient**. Shipping the notice without that change turns
     every internal note already being written into a message to a third party.
  2. **It becomes a customer-supplied slot, with everything that implies on SMS.** 1000 characters is
     many paid segments, so it takes the transliterate-and-truncate treatment `SmsNotificationChannel`
     already applies to `envelope_title` — which is an exemption stated as *"our own words are exempt,
     everything else is customer-supplied"*, so a new slot inherits it by default rather than needing to
     be listed. ⛔ The truncation is on the **slot**, never on the composed body.
  3. ⚠ **The reason is optional, and the engine cannot branch.** `NativeTemplateEngine` interpolates
     `{{token}}` slots and nothing else — Twig composes chrome at authoring time and never interpolates
     ([ADR-0052](../adr/ADR-0052-twig-layout-composition.md)) — so there is no conditional to hang an
     absent reason on. **Author two bodies and let the use case choose**, rather than interpolating an
     empty string and shipping a dangling *"Motivo:"* with nothing after it. The copy catalog
     (`EmailNotificationChannel::TEMPLATES`, keyed locale → purpose) and the archive pin
     (`NotificationTemplates::pinFor()`, keyed by purpose) have no variant axis, and `NotificationPurpose`'s
     own docblock argues against adding one (*"in this enum the words are the purpose"*), so the two
     bodies are **two purposes**. That is why §3 has five purposes for four families.

  4. **"A reason is present" means non-empty after `trim()`** (coordinator, 2026-09-29). Neither
     `VoidEnvelopeRequest` nor `EnvelopeVoided` refuses `""` or `"   "`, so the use case decides: a reason
     blank after trimming is absent and selects the no-reason body. The rule reads the event alone, so it
     is redelivery-stable (the idempotency bullet below), and the request contract does not change — its
     `#[OA\*]` text states the rule.

  ⚑ **No backfill (§4) is what keeps this honest**: only envelopes voided *after* the contract says so
  produce a notice, so no reason written under the old understanding is ever published.
- **Idempotency is the same cause token as its siblings** — `envelope:<id>|recipient:<id>|purpose:<P>`,
  with `<P>` the purpose §9 chose — so a redelivered `EnvelopeVoided` under at-least-once delivery
  converges rather than sending twice. It holds because the purpose is derived **from the event alone**
  (cause, and whether a reason is present), which decodes the same on every redelivery, and because an
  envelope records at most one `EnvelopeVoided`: a second void records nothing, and a closed envelope is
  not ended again. Do not derive `<P>` from a live read of the envelope.
- ⚠ **Adding a purpose is not free — this is the part to get right.** **Six** exhaustive `match`es key on
  `NotificationPurpose` and refuse a purpose that skipped them: `namesItsOwnChannel()`,
  `carriesMeansToAct()`, `isInvitation()` (ADR-0073 §2.8) — all three on the enum itself —
  `DefaultChannelSelector::select()`, `EmailLayoutView::palette()` and
  `EmailNotificationChannel::htmlTemplate()`. Enumerate them again by grep before trusting this count.
  Each new purpose answers **false** to all three predicates: it is sent after the envelope closed, so it
  carries no means to act — and `false` is what keeps a bounced ending notice off the ADR-0037 return path
  that records a `FAILED` delivery against the recipient; it is not an invitation, so its delivery facts
  never reach the recipient's invitation columns that a `release_reason` rests on. **The EMAIL copy catalog
  is not a `match`**: `authored()` falls back per pair to `DEFAULT_LOCALE` when a locale lacks a purpose,
  and indexes the fallback with no net. What holds it now is test-side and covers every authored locale:
  `EmailNotificationChannelTest::every_authored_template_carries_the_parts_this_channel_requires`, over the
  `catalogedTemplates()` provider (every authored locale × `NotificationPurpose::cases()`), asserts the
  locale served is the one asked for, so a purpose missing from any authored locale goes red; and
  `every_purpose_is_authored_in_the_fallback_locale` holds the fallback. ⚠ **This bullet said an unauthored
  non-fallback locale ships green; that was true when written and is not now.** The SMS catalog is held the
  same way: `SmsCopyTest` iterates `NotificationPurpose::cases()` across authored locales.
- **The SMS body inherits TASK-030 §5's budget, and the reason changes what that guarantees for the sender
  family.** ⚠ **This bullet said *"no customer slot, so one segment is a property of the string rather
  than a hope about the data"* and that is false since the reason became recipient-facing.** The reason
  **is** a customer slot, so one segment is a property of the **truncation budget** — what the authored
  words leave, computed rather than fixed — exactly as `envelope_title` already works. ⛑ **Truncation is
  the chosen behaviour, decided by the product owner 2026-08-25, not a default inherited from the title
  slot** — the alternative weighed and refused was falling back to the no-reason body when the reason does
  not fit whole. ⚠ **The residual is accepted and is worse here than for a title**: a cut title is
  recognisably a cut title, whereas a cut reason can read as a *different* reason from the one the sender
  wrote — *"…porque el importe"* stops somewhere the sender did not choose. So a long reason arrives whole
  by email and cut by SMS, and the same envelope tells two recipients slightly different things. ⚑ Accents
  remain affordable in a link-free body — `código` costs nothing at 53 of UCS-2's 70 — so do not mangle
  the authored Spanish for a saving that does not exist.
- **Three subscribers now consume `EnvelopeVoided`** — this one, Session's
  [`OnEnvelopeVoided`](../../src/F5Sign/Session/Application/Subscriber/OnEnvelopeVoided.php), which has
  revoked sessions on it since TASK-038, and Evidence & Audit's trail issuance
  ([ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.10). They are independent,
  must not be merged, and none may assume another ran. A retry of any one runs all of them again, so this
  one must converge on a redelivery as the others do. (SignatureExecution's annulment seal, which also
  listened here, is retired by ADR-0073 §2.5.)
- ⚑ **This is not ADR-0073 §2.15's copy-ready notice, and neither reuses the other's audience.** That
  notice ([TASK-050](TASK-050-a-step-says-how-much-agreement-it-needs.md)) fires at `COMPLETED`, carries a
  newly minted link, goes only to **informational** members — with `NOT_AGREED`, only those whose step
  activated — and only when a sealed document exists. This one fires at the decision (`EnvelopeVoided`),
  carries no link and goes to **every invited recipient**, signers included. An informational member of an
  activated step on a `NOT_AGREED` envelope where someone engaged receives both, hours apart, each saying
  something the other does not; so this notice's copy must **not** promise a copy of the document — most
  of its addressees will never get one, and an envelope nobody engaged has none.

## 6. Verification

Run through the lane that binds **this** tree: from a worktree (`git rev-parse --git-dir` shows
`/worktrees/`), `make -C ../f5sign-infra wt-backend src=$(pwd)`. ⛔ The bare `make test` / `make phpstan`
targets bind the main checkout and report green for another branch. Filtered runs while implementing may
use `wt-backend-test only=<regex>`; `Integration/` and `Acceptance/` run once as regressions when the task
is complete.

**Properties to lock:**

1. An ending notifies every recipient who was invited, in their resolved locale.
2. ⛔ A recipient whose step never activated is **not** notified. Build the fixture where the two
   populations **disagree** — a multi-step envelope voided while a later step is still dormant. A
   fixture whose recipients were all invited cannot fail this.
2b. A recipient who had no email when their step activated, and was invited by a later contact
   correction (`…|correction:<N>`, no base occasion), **is** notified.
3. A recipient whose invitation is `DELIVERY_FAILED` **is** notified.
4. A redelivered `EnvelopeVoided` produces no second occasion.
5. The rendered sender-family body **contains** the reason, asserted against an envelope voided with one
   — and asserted on the *rendered* output, not on the command, so an interpolation that silently drops
   the slot fails.
5b. An envelope voided **without** a reason renders the no-reason body — no empty slot, no dangling
   label. This is the case that a single-body implementation passes by accident and a reader never
   checks.
5c. A 1000-character reason renders inside one SMS segment, via the slot treatment and not by
   truncating the composed body.
6. Every authored EMAIL locale authors every new purpose, not only the fallback. Held by the existing
   `catalogedTemplates()`-driven test (§5), which widens with `cases()`; confirm it by deleting one
   non-fallback locale's entry for one new purpose and watching that test go red naming the pair.
7. Each SMS body renders inside one segment (`SmsCopyTest`'s census over `cases()`).
8. **One bar per copy family**, each over **every** `EndCause` member of that family (a data provider
   keyed by member name), asserted on the rendered EMAIL body: the family's distinctive sentence is
   present, and no other family's is. For every family: the body names no recipient, contains no URL,
   and makes **no claim either way about signatures and no promise either way about a copy** — neither
   *"was signed"* nor *"nothing was signed"*, neither *"a copy will follow"* nor *"no copy is coming"*.
   The copy must be true for a step-1 signer of an envelope voided at step 2, who did sign and who,
   under ADR-0073 §2.15, reads the sealed copy after `COMPLETED`.
   - 8a. *The sender cancelled it* — `SENDER_VOIDED`, both bodies (with 5 and 5b).
   - 8b. *A participant declined* — `RECIPIENT_DECLINED`, `RECIPIENT_VETOED`; the fixture includes the
     decliner among the invited recipients, and the decliner's own notice is this copy.
   - 8c. *The time allowed ran out* — `STEP_DEADLINE_MISSED`, `EXPIRED`.
   - 8d. *The agreement can no longer be reached* — `MINIMUM_UNREACHABLE`, `MEMBER_NOT_REACHED`.

   Harness: the use case at the `Application/` tier with the command built per cause, for every member —
   the only tier that reaches the causes with no writer on this branch. The two causes with a writer
   (`SENDER_VOIDED`, `RECIPIENT_DECLINED`) are also driven from the real aggregate through the subscriber
   at `Integration/`, so the event-to-command translation is exercised on a fact the domain produced.
9. **The census: every `EndCause` maps to exactly one family.** The test iterates `EndCause::cases()`
   against an **expected table written in the test** (member → family), keyed by member name, and fails
   on a member the table does not classify. Remove one arm of the cause → family `match` and the test must
   go red **naming that member**; move a member to another family and it must go red naming it; add a
   member to `EndCause` and it must go red naming it until someone classifies it.
10. A `NOT_AGREED` ending produces, per invited recipient, this notice and **no** `ENVELOPE_COMPLETED`
    notice when the envelope later reaches `COMPLETED` — one ending, one notice (the existing outcome guard
    in `NotifyCompletedEnvelopeRecipientsUseCase`, held from this side). `Integration/`.
11. A failed delivery of an ending notice records no `FAILED` delivery against the recipient and writes no
    invitation column — the `carriesMeansToAct()` and `isInvitation()` answers of §5, asserted through the
    propagation use cases rather than by reading the enum.

**Sabotage before trusting any of it** (the repo's authoring rule 4): revert the audience predicate and
confirm case 2 — and only case 2 — goes red; replace the audience query with `find()` on the base
invitation token and confirm case 2b goes red; drop one arm of the cause → family `match` and confirm case 9
names the member (and check it was the census that fired, not an `UnhandledMatchError` in an 8x case
alone); swap two members' families and confirm case 9 names both; collapse the sender family to one body
and confirm 5b goes red.

**Gates:** `WT_GATES="lint arch phpstan test"`, `infection` opt-in. Quote what the lane printed.

## 7. Open follow-ups (track, don't solve here)

- **The truncated-reason fallback, if the residual ever bites ([BL-327](../BACKLOG.md)).** §5 accepts that an SMS reason is cut
  mid-sentence and can therefore read as a different reason. ▶ The trigger to revisit is a real
  complaint or a sender asking why their recipients got half a sentence; the fix already exists in
  shape — the no-reason body is authored anyway, so falling back to it is a branch in the use case and
  not new copy. Recorded now so the next person finds a decision rather than an oversight.
- ⚠ **The sender's reason is now dual-purpose and nothing enforces the split ([BL-326](../BACKLOG.md)).** It is simultaneously the
  internal record in the event log (`reason` on `EnvelopeVoided`, `end_reason` on the envelope since
  ADR-0073 §2.5) and a recipient-facing message. Nothing stops a sender writing something they intended as
  internal, and no gate can tell the two apart — the `#[OA\*]` string (§5) is the only control, which
  makes it prose holding a disclosure property. If that turns out to be too thin, the fix is two fields,
  and it is a contract change rather than a copy change. ⚠ **It is also a phishing vector:** the reason is
  quoted verbatim in a platform-branded email, and although it is HTML-escaped, a URL or an instruction in
  it still reads as coming from the platform.
- ~~**The EMAIL catalog's per-locale hole.**~~ **Closed before this task started**: the
  `catalogedTemplates()`-driven test now asserts the served locale for every authored locale × purpose
  (§5). Kept struck through so a reader of the old §6 case 6 finds where it went.
- ~~**Notifying on the other terminal states.**~~ **Decided 2026-09-29 (§5)**: every ending without
  agreement is told, by family. What survives of the old bullet: `EnvelopeStatus::EXPIRED` is still
  declared with no writer, and its retirement is TASK-049's (ADR-0073 §2.12), not this task's.
- ~~**Whether the deciding recipient should be left out.**~~ **Decided 2026-09-29 (maintainer): the
  decliner or vetoer stays in the audience** and gets the same notice, which reads to them as a
  confirmation (§5). Should that ever be reversed, the predicate gains one clause on
  `EnvelopeVoided::$voidedByRecipientId`, which the command can carry from the event — no second
  `Contract` read.
- ⚠ **A reaction racing the close is not caught ([BL-325](../BACKLOG.md)).** A reaction that read the envelope just
  before the close, and saves its invitation after the ending notice read its audience, is not caught by the
  closed-envelope guards; nothing serializes the two (§8, the bullet *nothing stopped an invitation after the close*, its **What remains**).
- **Landing sweep, for tense** (the repo's authoring rule 1). **Done on this branch:** ADR-0059 §2.5 and ADR-0070
  (`7e7945a8`), TASK-038 and TASK-046 (`b6bee27d`); TASK-047's sibling row is still true as written.
  **Left, by the coordinator's decision:** TASK-049 D2 and its deferrals list (*"no expiry notice exists yet"*,
  *"an expiry notice with TASK-040"*), applied at TASK-049's close, and the signer handoff
  `docs/frontend-handoff/TASK-046-signer-decline.md`, rewritten at the package join. `rg 'TASK-040' docs src tests
  config` re-derives the list; do not trust this one.
- **Routing this to SMS** — [TASK-031](TASK-031-channel-selection-beyond-email.md).

## 8. Deviations & honest notes

Written at close, alongside §7's disposition.

- **Before implementation — the claims check of 2026-09-29 found two defects in the re-cut, both
  resolved by the coordinator the same day.** (1) §6 case 8 required the body to *say* nothing was
  signed and no copy is coming. That is false for a step-1 signer of an envelope voided at step 2, and
  contradicts ADR-0073 §2.14/§2.15, which keep the signature and let the signer read the sealed copy.
  §5 already stated the intent as an absence, so case 8 is now an absence bar. (2) §5's audience predicate
  was `find()` on the base invitation token, which misses a recipient invited only by a contact
  correction. It is now a query for any `RECIPIENT_INVITATION` occasion on Notification's own repository,
  with case 2b holding it. The same pass fixed the blank-reason rule (§5 item 4).
- **Found and fixed during implementation: nothing stopped an invitation after the close.**
  `RecipientStepActivated`, `RecipientCorrected` and `RecipientInvitationResent` can only be *recorded*
  while the envelope is open, because the aggregate refuses them after `closed_at`. But their reactions are
  handled independently of `EnvelopeVoided`'s. One handled after the ending (a retry, or a second
  consumer) minted a fresh 7-day credential and mailed a link to a closed envelope. The ending notice's
  audience, already read, did not contain that recipient, so they were invited and never told. A
  recipient invited only by a correction had no other invitation at all. Decided with the coordinator
  2026-09-29 to fix inside this task, since it is the property the notice depends on (*nobody is newly
  invited once the envelope closed*) and it lives in Notification. `NotifyActivatedStepRecipientsUseCase`,
  `NotifyCorrectedRecipientUseCase` and `NotifyResentInvitationRecipientUseCase` now return before any
  token is issued when the envelope view carries `closedAt`. They read `closedAt`, not the status, because
  a closed envelope stays `SENT` while admitted signatures land. Each guard has an Application-tier case
  whose envelope closed before the reaction ran; sabotaging all three turned exactly those three cases
  red, on the "no credential is minted" assertion. ⚠ **What remains:** a reaction that read the envelope
  just before the close and saves its invitation after the ending notice read its audience is not
  caught; nothing serializes the two. That window is two relayed reactions wide, not a retry wide.

- **The dashboard sends a hardcoded Spanish reason.** The dashboard's void flow always sends
  `'Cancelado por el usuario'` (or `'Carta de porte anulada por el usuario'`), so every recipient of a
  dashboard-voided envelope is quoted that sentence in whatever locale they read. This task changes what the
  field is *for*; it does not change what the dashboard writes into it. Recorded in the package's provisional
  integrator handoff 60 (outside this repo), which owns the dashboard-side fix.
- **Contract-check fixed the `#[OA]` SMS sentence (`5715b3c7`).** The published description said an SMS
  notice may shorten the reason, which described an unreachable path as current (no ending notice routes to
  SMS until TASK-031). It now says notices go by email today and carry the reason in full, and that SMS, should
  it ever carry the notice, may shorten it (BL-327).
- **Accepted with no id, by the coordinator:** *a participant declined* implies the envelope has other parties.
  The recipient already knows that from their own invitation, so the copy is not reworded to hide it.
- **The name decision:** the provisional purpose names were kept; no rename was made in this task.
- **The lint fix inside the merge (`5e1a6aa9`):** it comes from `1cc5ef0e` on `feat/step-policy`, not from this
  task's own commits.
- **Honest notes.** §6 case 10 builds `EnvelopeCompleted(NOT_AGREED)` in the test, because this tier does not
  drive the seal. Case 11's success half cannot observe `isInvitation()` through the propagation path
  (`carriesMeansToAct()` guards first), so only the enum table holds it. The slow tiers ran **filtered only**
  (32 tests); Infection and the full Integration/ and Acceptance/ suites are declared skips under the package
  rule and run once over the joined ADR-0073 package.
- **Decision record:** none. No ADR moves to `Accepted` from this task; no proposal is made.

## 9. The copy families (maintainer decision 2026-09-29)

Derived from `EndCause`'s members and their docblocks, and from ADR-0073 §2.6's *"a fact explains the
failure before a clock does"*: a family names **what the recipient can understand happened**, not which
mechanism recorded it. Four families; the map is exhaustive with no `default` (§5).

| Family | `EndCause` members | What the copy says (meaning, not final wording) | Reachable on `feat/task-048-how-an-envelope-ends` |
|---|---|---|---|
| **The sender cancelled it** | `SENDER_VOIDED` | The sender cancelled the envelope — with the sender's reason when given (two bodies, §5). | Yes — `POST /api/v1/envelopes/{id}/void`. |
| **A participant declined** | `RECIPIENT_DECLINED`, `RECIPIENT_VETOED` | It will not go ahead because a participant declined. Names nobody; carries no decline text (the event has none). A veto is a decline in a veto step, and to the recipient it is the same event. | `RECIPIENT_DECLINED` yes (TASK-046's decline in an `ALL` step); `RECIPIENT_VETOED` when TASK-050 lets `send()` accept a veto step. |
| **The time allowed ran out** | `STEP_DEADLINE_MISSED`, `EXPIRED` | It ended because the time allowed for it passed before it was completed. | No — the sweep that closes a step or expires the envelope is TASK-049's and TASK-050's. |
| **The agreement can no longer be reached** | `MINIMUM_UNREACHABLE`, `MEMBER_NOT_REACHED` | It ended because the signatures it needed can no longer be gathered. `MEMBER_NOT_REACHED` sits here and not with the clocks because the cause names a fact (a veto-step member never reached), which ADR-0073 §2.6 ranks before the clock that closed the step. | No — both need a completion policy on a step (TASK-050). |

⚑ A cause added to `EndCause` later is classified here, in the `match` and in §6 case 9's expected table,
in one changeset — or it fails the build naming itself. Adding a family is a new purpose (or two) and
walks every site of §5.

## 10. Re-cut against ADR-0073 (2026-09-29)

What changed from the draft of 2026-08-25/2026-09-23, so a reader of an older copy can find it:

- **Scope widened from "the sender's void" to every ending without agreement**, by the maintainer's
  decision of 2026-09-29 (§5, §9); the title changed with it (the filename, an anchor, did not).
- **Why**: the void *closes* the envelope; it does not reach a terminal state (ADR-0073 §2.5).
- **§1**: Session has consumed `EnvelopeVoided` since TASK-038; the event now carries a cause and a party.
- **§2**: the completion use case is a mechanism analogue only — it now stays silent on `NOT_AGREED`.
- **§5**: the exhaustive-`match` checklist gained `carriesMeansToAct()` and `isInvitation()` (and
  `htmlTemplate()`), six sites in all; the EMAIL-catalog claim was corrected against the current tests;
  the copy-ready notice of ADR-0073 §2.15 is cross-referenced.
- **§6**: one bar per family (8), the cause → family census (9), and cases 10–11; case 6 now names the
  test that already holds it.
- **Builds on**: TASK-048 is a prerequisite; the branch is cut from `feat/task-048-how-an-envelope-ends`.
