# Spec-claims check — TASK-040 vs. current tree (feat/task-048-how-an-envelope-ends @ 786c39c2)

TASK-040 was drafted against ADR-0070's world (`VOIDED` a terminal status, `EnvelopeVoided` a
sender-only fact). ADR-0073 (Proposed) + TASK-048 (substantially landed on this branch) have since
rewritten the ending machinery. This checks every present-tense claim in TASK-040 and its reused
mechanisms against the code as it stands now.

## 1. Central finding (block): `EnvelopeVoided` is no longer a sender-void-only fact — TASK-040's own
   "open follow-up" question is pre-empted by the mechanism it specifies

TASK-040 hooks its whole design on one fact: build `OnEnvelopeVoided` (Notification) to react to
`EnvelopeVoided` and send a "your envelope was cancelled" notice. §7 explicitly treats *whether expiry
(and, by the same logic, other non-decline endings) should also produce this notice* as an **open,
undecided, deferred** question:

> "Notifying on the other terminal states. `EXPIRED` is declared and produces no notice either;
> whether it should is the same question one step over, and it has no writer today."

That framing is now false as a description of the mechanism, even though `EnvelopeStatus::EXPIRED`
itself is indeed still unwritten (`src/F5Sign/Envelope/Contract/Type/EnvelopeStatus.php:34` — "`EXPIRED`
has no writer either"). Under ADR-0073 §2.12, expiry is **not** a separate status/event that would need
its own separate notification wiring: it is recorded as `EnvelopeVoided` with `end_cause: EXPIRED`
("recorded as `EnvelopeVoided` with no party — its party members, always set today, become nullable on a
published event", ADR-0073 §2.12). The same is true for four more causes that ADR-0073 added to
`EndCause` (`src/F5Sign/Envelope/Contract/Type/EndCause.php`): `RECIPIENT_VETOED`, `MINIMUM_UNREACHABLE`,
`STEP_DEADLINE_MISSED`, `MEMBER_NOT_REACHED` — all recorded via the same `EnvelopeVoided` fact
(`EnvelopeVoided::__construct`'s `$namesItsParty` match, `src/F5Sign/Envelope/Contract/Event/EnvelopeVoided.php:70-77`,
enumerates all seven causes as valid parties of this one event).

**Verified this is not merely designed but already wired in this tree**, not just a TASK-049/050
future: `Envelope::decline()`'s admission path already calls the same evaluator with
`Trigger::decline($member, $at)` (`src/F5Sign/Envelope/Domain/Aggregate/Envelope.php:2583`), and every
non-refused decision — whatever its cause — is recorded through one call site,
`$this->record(new EnvelopeVoided(...))` (`Envelope.php:2676`). `Trigger` also already has `clock()`
and `closeNow()` factories (`src/F5Sign/Envelope/Domain/Service/Trigger.php`), i.e. the aggregate-level
machinery for deadline/expiry-driven endings is already in place; only the sweep that dispatches a
clock trigger is TASK-049's job. Once it lands, a `Trigger::clock()` decision that ends the envelope
without agreement is recorded exactly the same way — through `EnvelopeVoided` — with no new fact, no
new subscriber and no opt-in.

**Consequence for TASK-040 as written**: if `OnEnvelopeVoided` (Notification) is built to react to
`EnvelopeVoided` unconditionally (as §3 specifies, mirroring `OnEnvelopeCompleted`'s shape), it will
**automatically** start sending "the envelope was cancelled" notices for expiry, step-deadline releases,
vetoes and unreachable minimums the moment TASK-049/050 land — using copy authored only for "cancelled,
with/without a sender reason" (§5). None of those five causes is a decision by any party to *cancel*
anything, and the task's copy plan has no branch for them. This is exactly the deferred question in §7,
already answered "yes, and worded as a cancellation" by construction, without anyone deciding that.

**This is a decision for the maintainer**, not a wording fix: either (a) TASK-040's reactor must filter
on `EndCause` (e.g. only `SENDER_VOIDED`/`RECIPIENT_DECLINED`/`RECIPIENT_VETOED`, holding
`STEP_DEADLINE_MISSED`/`MINIMUM_UNREACHABLE`/`MEMBER_NOT_REACHED`/`EXPIRED` for whatever task is meant to
own "tell a recipient their envelope expired/timed out"), or (b) the copy is deliberately widened to
cover every cause, with per-cause wording — a materially bigger task than "cancellation notice". §7's
"same question one step over" line should be replaced with a statement that the mechanism already
couples these, not that the coupling is still open.

## 2. False claim (warn): header "Why" — void "reaches a terminal state"

> "`POST /api/v1/envelopes/{id}/void` reaches a terminal state, records `EnvelopeVoided`, and nobody
> tells the recipient."

False under ADR-0073/TASK-048. `Envelope::void()`'s own docblock is explicit: "**It does not end the
lifecycle.** ... the status stays `SENT` until [an in-flight signature] lands" (`Envelope.php:906-913`).
`EnvelopeVoided`'s docblock states it plainly: "**This is the instant the envelope CLOSED, not the
instant it ended.**" (`src/F5Sign/Envelope/Contract/Event/EnvelopeVoided.php:20`). The terminal status
(`COMPLETED`, for either outcome) is reached later, asynchronously, once every signature admitted before
the close has landed and the one seal path (`EnvelopeReadyToSeal` → seal → `EnvelopeCompleted`) runs.
`EnvelopeStatus::isTerminal()` only returns true for `COMPLETED`/`EXPIRED`
(`src/F5Sign/Envelope/Contract/Type/EnvelopeStatus.php:44-49`); `VOIDED` was retired as a status
entirely (§2.5).

This does not by itself break TASK-040's mechanism (hooking `EnvelopeVoided`, recorded "at the decision",
is still the right seam — ADR-0073 explicitly keeps that timing, §7.8 records that moving the fact to
the end was considered and rejected). It is a stale sentence to correct, not a design problem: "reaches
a terminal state" → "the envelope closes" (or similar), consistent with how §1 already (correctly) treats
the void as a *decision* rather than a completed lifecycle.

## 3. False claim (warn): §1 — "nothing consumes it — not Session, not Notification, not Evidence & Audit"

False against this tree, and not because of ADR-0073: `F5Sign\Session\Application\Subscriber\OnEnvelopeVoided`
(`src/F5Sign/Session/Application/Subscriber/OnEnvelopeVoided.php`) already consumes `EnvelopeVoided` and
has since TASK-038 landed (`a7b350fb`, 2026-08-26) — it dispatches `RevokeEnvelopeSessions`, closing every
live signing session. TASK-040's own header acknowledges TASK-038 landed ("Its value rose on 2026-08-26,
when TASK-038 landed") but §1's sentence was never updated to match. Mechanical fix: drop "not Session"
(or reword to "Session already revokes sessions on it; Notification and Evidence & Audit still don't").
Not an ADR-0073 effect, but a live contradiction against the current tree the prompt asked to check.

## 4. Mechanism check (info, mostly holds): the reused reactor pair and use case

- `OnEnvelopeCompleted` (`src/F5Sign/Notification/Application/Subscriber/OnEnvelopeCompleted.php`) is
  still a pure dispatch-only `Reactor`, shape unchanged — TASK-040's "copy the shape" instruction is
  still sound as a *shape* reference.
- **But `NotifyCompletedEnvelopeRecipientsUseCase`**, which TASK-040 calls "the closest analogue: one
  notice per recipient when an envelope reaches a terminal state," has already been edited for exactly
  the ADR-0073 change TASK-040 doesn't know about: it now opens with
  `if ($envelope->outcome !== EnvelopeOutcome::AGREED) { return; }`
  (`src/F5Sign/Notification/Application/UseCase/NotifyCompletedEnvelopeRecipientsUseCase.php:78-83`),
  with a comment explaining that `EnvelopeCompleted` now fires for both outcomes and that "who is told
  of its sealed copy, and with what link, is TASK-050's copy-ready notice." This confirms (a) TASK-040's
  own instinct to build a *separate* audience rule rather than copy the completion notice's is still
  correct, and (b) there is a second, ADR-0073-introduced notification concept — the §2.15 "copy-ready
  notice, with a fresh link" for `COMPLETED` — that did not exist when TASK-040 was written and that
  TASK-040 does not mention. Worth a cross-reference in §1/§7 so nobody reading both tasks assumes
  TASK-040's notice is that one, or reuses TASK-040's audience rule for it (they differ: §2.15 sends the
  `NOT_AGREED` courtesy copy only to informational members whose step activated, keyed off `COMPLETED`
  and a fresh link — not off `EnvelopeVoided` and not to signers).

## 5. Mechanical gap (info): the census of "exhaustive matches a new purpose must satisfy" is incomplete

TASK-040 §5 names two compiler-enforced exhaustive `match`es a new `NotificationPurpose` case must
satisfy (`namesItsOwnChannel()`, `EmailLayoutView::palette()`) plus, implicitly, the channel selector
(`DefaultChannelSelector::select()`, confirmed still an exhaustive `match` with no `default`,
`src/F5Sign/Notification/Domain/Service/DefaultChannelSelector.php:62-66`). Since TASK-040 was drafted,
ADR-0073 §2.8 added a fourth: `NotificationPurpose::isInvitation()`
(`src/F5Sign/Notification/Domain/ValueObject/NotificationPurpose.php`, "Exhaustive with no `default`, so
a purpose added later classifies itself here"), which `RecipientReleased`'s `release_reason` computation
now depends on. Adding `ENVELOPE_VOIDED` will not compile until this `match` also has an arm (correct
answer is `false` — it is not an invitation — but the task doesn't name the site). Mechanical, not a
decision; add one line to §5's enumeration. (`carriesMeansToAct()` is a fifth pre-existing exhaustive
match the task also doesn't name, independent of ADR-0073 — same fix.)

## 6. Checked and still holds (no finding)

- **Audience predicate** ("the notice goes only to recipients the platform actually wrote to" via a
  `find()` on the deterministic `RECIPIENT_INVITATION` cause token) is unaffected by ADR-0073 and is
  compatible with the new `RELEASED`/`release_reason` model: a member released `NOT_REACHED` (step never
  activated) has no invitation notification on file, so the predicate correctly yields nothing for them;
  a member released `DELIVERY_FAILED` does have one, so TASK-040's explicit carve-out ("a recipient whose
  invitation bounced still gets one") is still correct under ADR-0073 §2.8's `release_reason` taxonomy.
- **`VoidEnvelopeRequest::$reason`** and `Envelope::void(ActorId $voidedBy, ?string $reason, ...)` are
  unchanged in shape; §5's `#[OA\*]` plan still applies to the same field.
- **Idempotency via cause token** (`NotificationId::fromCause()`) is unaffected; `EnvelopeVoided` is
  still recorded once per envelope-ending decision (idempotent void: "a second void records nothing",
  `Envelope.php:920-923`), so redelivery-safety still holds the way §5 describes.
- Verification bars §6 (1–7) are all still meetable on this tree as specified, **once §1's audience
  scope is resolved per finding 1** — none of them name a harness or fixture that can't reach the
  property.

## 7. Not checked (out of budget / genuinely external)

- Whether `RECIPIENT_VETOED` is reachable at all today (it requires an `AT_LEAST ... veto` step, which
  is TASK-050's `completion`/veto columns — `min_signatures`/veto/deadline are described in ADR-0073
  §2.6 as "new columns," and `send()`'s validation of them is also TASK-050's). Not verified whether a
  veto-caused `EnvelopeVoided` can occur before TASK-050 lands; doesn't change finding 1's conclusion
  (the coupling exists in the fact's shape regardless of which causes are currently reachable).

## Decisions for the maintainer vs. mechanical

- **Maintainer decision**: finding 1 — whether TASK-040's `OnEnvelopeVoided` should filter by `EndCause`
  and, if so, which causes get "cancelled" copy vs. no notice vs. different copy; whether expiry/deadline/
  veto/unreachable-minimum endings get their own task and their own wording.
- **Mechanical**: findings 2, 3, 5 — rewording the "Why" and §1 sentences, and adding the `isInvitation()`
  (and `carriesMeansToAct()`) arm to §5's checklist.
- **Informational, no action required in TASK-040 itself**: finding 4 — worth a cross-reference so the
  two notices (TASK-040's cancellation notice vs. ADR-0073 §2.15's copy-ready notice) aren't conflated by
  a future reader.
