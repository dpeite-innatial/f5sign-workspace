# TASK-022 — Delivered one-time codes over email: issuance, expiry, and the re-send endpoint

<!-- OFFREPO: §6 states facts about the sibling repo `f5sign-signer` (the auth-method union it already carries, the re-send control it must draw, the 429 it must render as a countdown) and the `Prerequisites` row + §2 state facts about `f5sign-infra`'s stack (the shared Redis it runs, the broker). Neither repo is reachable under agent-only backend access; every fact is restated inline here so this record stays self-contained. -->

| Field | Value |
|-------|-------|
| **Status** | **In review** — implemented 2026-08-19 on branch `feat/otp-email-codes` (branched from `develop` at `e1370e1`). ⚑ **One thing was deliberately left undone here because it was the user's call, and it has since been given**: this slice left [ADR-0051](../adr/ADR-0051-notification-inbound-command-surface.md) at `Proposed` with every bar in its §5 already green, because promotion was explicitly reserved — so the slice recorded the evidence and stopped there. The call was given on 2026-08-19 and the ADR is now **`Accepted`** *(exercised; §2.3 narrowed)*, promoted in its own changeset rather than in this one. See §8 for what was deviated and why — §8.2 is the deviation that qualifier names. Originally a forward plan, written 2026-08-10. Decision record: [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.5 and §2.7 through §2.10 for the ceremony, and [ADR-0051](../adr/ADR-0051-notification-inbound-command-surface.md) (`Proposed` while this task ran, `Accepted` since 2026-08-19 on this task's exercise) for how the issuance reaches Notification at all — a seam that did not exist when the first cut was written, and whose absence is why §2.9 had to be retracted. |
| **Type** | **Forward build** — slice 2 of 3. Swaps a delivered verifier into the gates [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) built, over the one channel that already exists. |
| **Why** | The access code is a *pre-shared* secret: the sender must reach the signer out of band to hand it over, and every envelope that needs a gate needs a phone call first. A **delivered** code removes that, and it is the difference between a feature an integrator can enable and one a human has to operate. Email is the cheap way in — the channel exists, so this slice needs no provider, no new contract and no personal data the recipient row does not already hold. |
| **Decision record** | [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) (**`Accepted` since 2026-08-19** on [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md), *exercised; delivery half deferred* — this task is that deferred half: §2.5's *mint a new challenge* operation and route 4) + [ADR-0051](../adr/ADR-0051-notification-inbound-command-surface.md) (the inbound command port this calls through) + [ADR-0014](../adr/ADR-0014-idempotency-three-layer.md) (whose open costly-side-effect question §2 answers with fail-open). No new ADR is expected; if the limiter turns out to need a level of policy override, that is `BL-120` and an ADR, not an edit here. |
| **Sequencing** | **Next**, and unblocked: its hard dependency [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) landed, and [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) shipped the gates, the challenge entity, the budget and the act binding this reuses unchanged. [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) follows and cannot overlap — it reuses this entire mechanism and adds a destination, not a ceremony. ⚑ **Updated 2026-08-19**: the channel it was going to add left it for [TASK-030](TASK-030-sms-delivery-channel.md), for the same reason this row gives for its own cheapness — a transport is not a ceremony, and email was cheap here only because its transport already existed. ⚑ **It CAN run in parallel with [TASK-019](TASK-019-requirement-traceability-and-per-tier-gates.md)**, which touches test infrastructure and no BC: the only contention is the worktree lane's `flock`, which serialises *validation* and not authoring. |
| **Builds on** | [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) (the gates, the challenge entity, the cumulative budget, the act binding — all of which this reuses unchanged), [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) (the Notification BC and the cause-convergence rule that shapes re-sending). |
| **Delivery bar** | A recipient declared `OTP_EMAIL` on either gate receives a code through Notification, enters it, and proceeds. A **re-send actually sends** — a second code arrives — and the failed-attempt budget does **not** reset across it. |
| **Depends on** | **[TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) must land first**, and it is a hard dependency rather than a preference: [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 forbids falling back to another channel, so without the correction path an undeliverable code strands the envelope with **no** recovery, sender-side or otherwise. It was scoped inside this task in the first cut and moved out on 2026-08-17, once it turned out not to be an OTP prerequisite at all: `NotificationFailed` is already recorded today, nobody subscribes, and a hard-bounced **invitation** already strands its envelope in production. The fix is owed to every envelope, not to this feature. |
| **Sibling — do not scope independently** | **[TASK-024](TASK-024-notification-copy-to-twig.md) retires the mechanism this task's copy would otherwise be written against.** It moves the `EMAIL` channel's HTML out of the heredocs in [`EmailNotificationChannel`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailNotificationChannel.php) into `templates/notification/`, byte for byte, changing nothing a recipient sees. **Sequence it before this one**: the OTP body is a large monospaced code block in the layout that task establishes, and authoring it against the heredocs means writing it twice. An earlier cut of this row said the two could not be linked because TASK-024 lived on another branch, and warned that its premise — HTML in heredocs — sat on an unmerged branch and might never land. Both halves expired when `develop` merged `feat/notification-email-html` and TASK-024 with it. ⚑ **Update 2026-08-18 — TASK-024 has landed, so this row's prerequisites are discharged and its instruction inverts.** The heredocs are gone; `templates/notification/` exists with `layout.html.twig` and `fields.html.twig`; `twig/twig` and `symfony/twig-bundle` are direct `require`s and `TwigBundle` is registered and scoped ([ADR-0052](../adr/ADR-0052-twig-layout-composition.md) §2.6). The earlier text warned that **Twig is not a production dependency** and that whichever task arrived first owed that change; it arrived, and the debt is paid. So this task no longer *waits* on anything here — it **authors against** what is now in place: a template overriding the layout's `central` block for the monospaced code, its copy added to `TEMPLATES` in **both** authored locales (a purpose missing from the fallback locale reddens `every_purpose_is_authored_in_the_fallback_locale`), and the purpose named in `EmailNotificationChannel::htmlTemplate()`'s exhaustive `match`. ⛔ Do not add a view property for the code as a plain `string`: [`EmailLayoutView`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailLayoutView.php)'s property types are the escaping contract, and a `string` is autoescaped. |
| **Prerequisites that do not exist** | ⛔ **Half of this row was already false when it was written, and it made the task look more expensive than it is.** `symfony/rate-limiter` genuinely was missing — **installed 2026-08-18** (`bedd3c5`, v7.4.16). But the Redis half never held: **`ext-redis` is compiled into `f5sign/backend:dev`** (`php -m` lists it) and the broker has been running in the infra stack all along, so **no PHP Redis client was needed** — the extension is simply declared in `require`. ⚑ **A declared prerequisite goes stale exactly like a `Status` does**, and in the more expensive direction: nobody re-checks the prerequisites of a task in `Not started`, so it stays parked for a blocker that has partly dissolved. **What is still owed here and deliberately not done yet**: the cache pool and the limiter policies (three keys, limits, cooldown, fail-open) — those are this task's §4 design decisions, and a Redis-backed pool with no consumer would be configuration nothing exercises. `cache.yaml` is still the vanilla skeleton, and the DSN still owes its entry in `.env`'s load-order header under repo rule 4. |

---

## 1. Why this task exists

[TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) leaves a working two-gate ceremony whose only verifier is a code the sender told the signer by phone. That is legitimate but narrow: it cannot serve a recipient the sender has never spoken to, and it makes the access code — which never expires — the sole secret standing in front of the envelope.

A *delivered* code fixes both, and email is the cheap way in: [`EmailNotificationChannel`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailNotificationChannel.php) already exists, so this slice needs no provider, no contract, and no personal data the recipient row does not already hold. It buys the whole delivered-code mechanism — issuance, expiry, re-sending, rate limiting — while [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) is left holding only what is genuinely SMS-shaped.

Two hazards are the actual content of this slice, and both are already documented in the repo rather than discovered here.

**The re-send that never sends.** Notification converges by cause ([`NotificationId::fromCause`](../../src/F5Sign/Notification/Contract/Type/NotificationId.php)): a second delivery under the same cause token is a **silent no-op**. A re-send button that reuses the cause produces a spinner, a log line, and no email. [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) names an OTP re-issuance as the worked example of exactly this.

**The re-send that resets the lockout.** Three attempts, re-send, three more, without end — if the budget belongs to the challenge. [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) built it on the session for this reason; this slice is where that becomes load-bearing rather than theoretical.

## 2. What gets built

**Issuance.** `InitiateAuthChallenge` mints a challenge, generates a code with a CSPRNG, stores only its peppered hash, and requests delivery. The plaintext reaches no log, no event payload and no event-log entry — only the `OtpSent` / `OtpVerified` *facts* do.

⛔ **The first thing this slice will hit, written here because this is the file that will be open when it does — [`BL-157`](../BACKLOG.md).** Giving a challenge a TTL makes a latent `23505` live. `session.auth_challenge`'s partial unique index counts a gate as occupied by `consumed_at IS NULL` **only** — expiry is deliberately absent from the predicate, because a partial index may not reference `now()` — while `SigningSession::ensureLiveChallenge()` treats an *expired* challenge as **absent** and opens a second row beside it. The two disagree about what occupies a gate, and the database wins. It is unreachable in [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) for one narrow reason only: `SubmitAuthResponseUseCase` is the sole issuance site and passes `challengeExpiresAt: null` **literally**. ▶ The issuing path must retire the timed-out row first, through [`AuthChallenge::invalidate()`](../../src/F5Sign/Session/Domain/Entity/AuthChallenge.php) — which already exists for exactly this, is documented as *"consumption by another name"*, and has **zero production callers**, so Infection scores it as nonexistent and no gate will notice if it rots before you get here.

**But it does get written down, and this slice does not clean it up.** Notification's create-then-transmit split means the occasion persists its template slots in `notification.notification.variables` and re-reads them at transmission to render, so a delivered code lands at rest, unenciphered, in a sibling table of the one holding its peppered hash — and nothing removes it. That is deferred to `BL-113`, deliberately: the fix is Notification's retention posture, it is the same mechanism as the far more serious invitation-link case that row already holds, and solving half of it inside an OTP slice would leave the dangerous half open while reading as closed.

What the deferral costs here is small and worth stating so nobody re-derives it in alarm: these codes are dead within their TTL, so the rows accumulate spent secrets. The credential that is *not* dead — the invitation's composed link — is `BL-113`'s case and predates this task.

**The request is a call, and the seam it calls through does not exist yet.** [ADR-0051](../adr/ADR-0051-notification-inbound-command-surface.md) is the decision: Notification publishes a synchronous command port under `Notification/Contract/Command/`, and `SessionApplication` is granted **that layer only** — `Contract/Event/` stays ungranted, so no core context gains the ability to observe Notification's facts. That grant is `deptrac.yaml`'s **third** enumerated exception and must be added to the header comment that enumerates them, per its own instruction.

So this slice carries structural work it did not carry in the first cut: the port, its adapter, the Deptrac layer and grant, and the enumeration. It is the first requirement in the repo where one context needs another to perform a user-blocking side effect promptly, which is why it is the one that pays for the seam.

**And the transmission keeps its relay hop, which is a retraction rather than an omission.** ADR-0049 §2.9 said the send is *"a command on the plain queue"*; there is no such queue — `routing:` is empty and its comment says cross-context messages reach the broker only through the event log and its relay. The request escapes the poll because it is a direct call; the delivery behind it does not. Do not read the original sentence as unimplemented scope: it was retracted, and §2.9 now records on what grounds.

**Issuance is two operations, and collapsing them is a defect that ships by default.** [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.5 splits them and this is the slice that builds the split:

- **Ensure a live challenge** — what the auth screen calls when it opens. If a challenge is already open and unexpired it is returned; nothing is minted and nothing is invalidated.
- **Mint a new challenge** — what the re-send control calls. It mints, **invalidates the previous code**, and requests delivery.

Only modelling the second is how a page refresh kills the code the signer is holding. The signer app issues on component mount, and a session is keyed `(tenant, envelope, recipient)` with a deterministic id — so a reload, or opening the link on a second device, converges on the same session and would mint a second code, invalidating the one in the email the signer is looking at. Re-issuance-invalidates-the-previous is right (concurrent live codes multiply the brute-force surface against a shared budget); making *arriving at the screen* an issuance is not.

Minting is forced to produce a genuinely new challenge by cause convergence: each issuance carries its own challenge id and therefore its own cause token. At most one challenge is open per session, so neither operation needs an argument naming which gate it means.

**Where the limiter keeps its count, and what it does when it cannot.** A limiter that counts in the local filesystem cache counts *per container*: with three replicas an attacker gets three times the budget and each replica believes it is behaving. So the count goes in the shared Redis the infra stack already runs — which is why the client and the pool are prerequisites above rather than a detail.

And the second half, which [ADR-0014](../adr/ADR-0014-idempotency-three-layer.md) left open pending a costly-side-effect forcing case: **this is that case, and it fails open.** If Redis is unreachable the request proceeds unlimited rather than being refused. That is the more expensive failure — a Redis outage becomes an unmetered SMS window instead of a bounded one — and it is chosen deliberately over the alternative, which is that a broker nobody is watching takes signing offline for every tenant at once. The trade is availability of a legally-material act over a spend ceiling, and it is only defensible while somebody can see the outage: the fail-open path must be loud, which is the one observability requirement this slice cannot defer.

**The re-send endpoint.** `POST /api/v1/signing/session/auth/otp/send` — route 4 of [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3's partition, declaring `SIGNING_TOKEN` because it is reachable **before** the gate by construction. That makes it an anonymous endpoint that costs money and touches personal data. It carries: rate limiting on **three** keys (session, destination, source address — per session alone lets a set of leaked tokens multiply the spend linearly), a server-side minimum interval surfaced as `429` with `retryAfter` under the problem+json shape ([ADR-0025](../adr/ADR-0025-rfc9457-error-shape.md)) so the client can disable its own control rather than be trusted to, and a response that **never echoes the destination** — any "sent to ···456" affordance is masked server-side.

The *ensure* operation is not throttled into uselessness by that limiter, because it mints nothing when a challenge is already open. That is the second reason the two are separated.

**Per-method policy, and this is the slice where the values start being read.** They are platform defaults read through the single point [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) established; there are no tenant, workspace or envelope overrides, and `BL-120` holds why. Email is not SMS: a five-minute TTL calibrated for a text message is hostile to a mail that passes greylisting and spam filtering, which is why [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.8 sets **15 minutes for `OTP_EMAIL`** against 5 for SMS, with a **60-second minimum interval** between issuances.

Two of those three bind here and the third does not: `OTP_SMS` has no channel until [TASK-030](TASK-030-sms-delivery-channel.md) and no destination until [TASK-023](TASK-023-sms-codes-and-recipient-phone.md), so its row lands as configuration nothing exercises. And the interval must keep fitting several times inside the email TTL — at these values, fifteen times — because the failure it prevents is a signer whose mail never arrived being held behind their own cooldown until the code they are waiting for expires.

**Notification.** `NotificationPurpose` gains `AUTH_OTP` with a `SINGLE` must-succeed delivery policy — the first new purpose since the BC shipped. Adding a case forces its **channel selection** — `DefaultChannelSelector::select()` is an exhaustive `match`, so the compiler refuses a purpose it cannot route.

⚠ **The copy has no such net, and an earlier cut of this line claimed it did.** ⚑ **Corrected 2026-08-19 against the tree, because this sentence contradicted the `Sibling` row above it**: `EmailNotificationChannel` *does* carry an exhaustive `match` — `htmlTemplate()`, which TASK-024 added and which a new purpose must name — so the compiler does refuse an unrouted purpose. What has no net is the **copy itself**: a `private const array TEMPLATES` keyed `[locale][purpose]` and read by subscript, typed loosely enough that any string key satisfies PHPStan. A purpose added without copy is therefore an **undefined-array-key at send time**, on the path where a person is waiting for a code — not a build failure. Whatever else this slice does, the copy must be added deliberately and covered by a test, because nothing structural will notice its absence.

**The copy is authored as a Twig template, not as a heredoc**, per the sibling row above: the OTP body is a large monospaced code block that overrides the `central` block of `templates/notification/layout.html.twig`, which TASK-024 landed on 2026-08-18 — so the mechanism this warned against writing twice no longer exists to write against. **There is no override to remove**: [`DefaultChannelSelector`](../../src/F5Sign/Notification/Domain/Service/DefaultChannelSelector.php) maps the two existing purposes to `EMAIL` and forces nothing. The OTP-forced-to-SMS rule is a *designed* behaviour of the preference-aware selector that is meant to replace this one, specified in [`docs/ddd/notification-domain-model.md`](../ddd/notification-domain-model.md) § Channel selection and in the selector's docblock; [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 withdraws it before it is built, because a method that names its own channel leaves nothing to override. So this slice **maps `AUTH_OTP` straight to `EMAIL`** and reconciles the two prose homes; the served-legal-notice half of the override stands.

**The availability port opens by one.** [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) shipped the [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) availability adapter reporting **`ACCESS_CODE` and nothing else**, plus an application guard that refuses anything else **at authoring**. Adding `OTP_EMAIL` to the `signer.available_auth_methods` parameter in [`config/services.yaml`](../../config/services.yaml) — wherever a mail transport is configured — is what makes this slice declarable; until then none of it is reachable. Cheap, and easy to leave out of a slice that is thinking about codes rather than about capability.

⚠ **This paragraph said the adapter reports `DIRECT_LINK`, `NONE` and `ACCESS_CODE`, and it was wrong twice** (corrected 2026-08-19 against the shipped code). There is no `NONE` member at all — the neutral lives in the slot type, not in the catalog ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.1) — and `DIRECT_LINK` is declarable on neither slot, since both `requiring()` constructors refuse it before an availability question can be asked. The adapter classifies `DIRECT_LINK` as unavailable and says so explicitly, precisely because a member that cannot reach the predicate is the one an enumeration drops.

**No fallback — and the path it falls back to instead is [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md), not this task.** A failed delivery never retries on another channel: an automatic email fallback would let an infrastructure incident silently downgrade a declared auth strength — and, through the signature-level projection, the asserted strength of the resulting signature. A hard bounce routes instead into the `RecipientDeliveryFailed` → `DELIVERY_FAILED` → `CorrectRecipient` path.

What this task owes that path is **one purpose-specific behaviour, not the path itself**: a corrected contact must re-trigger a *new challenge*, not a re-delivery of the dead one, because §5's cause convergence makes the second send under the same cause a silent no-op. Everything else — the Notification-side reaction, the outcome, the command, its route and the sender's view of it — lands in TASK-025.

## 3. Scope

**In scope:** `InitiateAuthChallenge` + code generation/storage/verification; the issuance path through ADR-0051's Notification port, plus the Deptrac layer, grant and enumeration it needs; **the ensure/mint split of §2** and challenge replacement semantics; the re-send endpoint with its three-key limiter, cooldown and masked response; the rate-limiter component installation and configuration; `AUTH_OTP` purpose mapped to `EMAIL` + the two prose homes of the withdrawn OTP override reconciled; **`OTP_EMAIL` added to the availability adapter**; per-method TTL/limit resolution; **a corrected contact re-triggering a new challenge rather than a re-delivery**; `OtpSent` / `OtpVerified` facts on the event log; tests per §5.

**Out of scope:**
- **The recipient-correction path itself** — [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md), and a hard dependency rather than a deferral. It was in scope in the first cut; moving it out is not a reduction in what must exist before this ships, only in who builds it.
- **SMS, WhatsApp and voice** — the SMS *channel* is [TASK-030](TASK-030-sms-delivery-channel.md) and the phone it delivers to is [TASK-023](TASK-023-sms-codes-and-recipient-phone.md). With no phone on the recipient row, they are unbuildable here regardless.
- **Usage metering.** Email is not billable, so no `UsageMeter` call fires in this slice. The idempotency key it will use — the challenge id — is minted here, which is the point.
- **Sender-side visibility of delivery state.** [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) puts lock state on the sender-facing read model, so the carrier for "code sent, not yet entered" now exists — this is deferred by choice rather than for want of a consumer. Worth revisiting the moment support starts asking "did it go out?", which is the first question a delivered factor generates.
- **Anti-automation beyond rate limiting** (proof-of-work, CAPTCHA). The three-key limiter is the defence; if abuse data later says otherwise, that is a separate decision.
- **Both mitigations for the one-factor-twice case** named in §4, which this slice therefore ships without. (a) The **authoring-time warning** when the invitation channel equals the OTP channel is a dashboard surface, not a backend one. (b) The **signature-level projection rule** that must not score `OTP_EMAIL`-over-an-email-invitation as equal to `OTP_SMS` belongs to Signature Execution, which consumes the auth method as a level refiner but has no auth-method input yet — it acquires one only after [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) makes the distinction meaningful. Until both exist, an `OTP_EMAIL` envelope delivered by email asserts more ceremony than it performed. **This is a known, accepted, temporary overstatement and it is legally material** — it should not outlive slice 3.

## 4. Key decisions

- **Email first, deliberately — and it is often the weaker factor.** When the invitation link and the code arrive in the same mailbox, one compromised mailbox yields both: it is one factor twice, not two. It is built first anyway because it exercises the entire delivered-code mechanism with zero new infrastructure, leaving [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) holding only the genuinely SMS-shaped work. What that costs is recorded under *Out of scope* rather than papered over: neither mitigation lands here.
- **A re-send mints rather than re-delivers.** The alternative — keeping previous codes valid until their own expiry — is friendlier when a delayed message lands after the signer has already asked again, and is rejected: it multiplies the live-code surface against a shared attempt budget and makes the counter ambiguous about what it is counting.
- **The channel is named by the method, not chosen by the selector.** This keeps a special case out of Notification rather than adding one — the override was specified and never built, so what lands here is a retraction in prose, not a deletion in code.
- **The limiter is configuration, not structure.** Stated plainly because it means a mis-scoped limiter is a spend incident rather than a test failure — see §5's note on what no bar covers.
- **The limits, decided 2026-08-19, and they are PER METHOD rather than shared.** The three keys of §2 get `otp_email_session: 5/hour`, `otp_email_destination: 10/hour`, `otp_email_source: 30/hour`. ⚑ **The policy names carry the method on purpose**: [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) adds `otp_sms_*` with its **own** numbers rather than re-tuning these, because the two channels differ in the only variable that matters here — an email costs nothing and an SMS costs money on every send, so a ceiling that is generous for one is a spend incident for the other. A single shared limiter would force one number to be wrong.

  The session limit sits well above the 60-second `MIN_SECONDS_BETWEEN_ISSUANCES` floor that already exists, so a real signer whose mail is delayed by greylisting can ask again several times without meeting it; what the limit stops is the *burst*, and it bites long before the 15-minute email TTL makes a code useless.

- ⚠ **The source-address key is a spend ceiling and NOT an identity, and this is written down because the name invites the opposite reading.** An IP does not identify a user in either direction: carrier-grade NAT, corporate egress and mobile networks put **many unrelated signers behind one address** — an office where six people sign the same afternoon shares a counter — while a determined attacker rotates addresses freely and pays almost nothing for it. So this key **over-blocks legitimate users and under-blocks a motivated one**, which is the opposite of what a security control should do.

  It is kept anyway, and for one narrow reason worth stating rather than assuming: without it, per-session alone lets a set of leaked tokens multiply the spend **linearly** — the argument §2 already makes. It buys a bound on *cost*, not on *access*. ⛔ **Nothing may be built on top of it as though it were an actor**: no per-IP lockout, no per-IP trust, nothing in the evidence trail that reads as "who". And when it refuses, the refusal must be the same `429` with the same `Retry-After` as the other two keys, so a signer sharing an office NAT is told to wait rather than told they did something wrong.

## 5. Acceptance bars

1. **A re-send actually sends.** Two consecutive issuances produce two **distinct** notification causes, locking the silent no-op [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) documents. This is the bar most likely to be assumed rather than asserted.
2. **A re-send does not restore the budget.** Driven through the real re-send path, not the aggregate — [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) asserted the aggregate; this asserts the path.
3. **The previous code dies — but only when something minted.** After a *re-send* the earlier code is refused. After two *ensure* calls — the signer reloading the page, or opening the link on a second device — there is still exactly one challenge and the code already in their inbox still works. Both halves matter: the first is the security property, the second is the bug that would otherwise reach a real signer on their first reload.
4. **Expiry refuses, and says so.** A code past its per-method TTL is refused under its own machine `code`, **distinct** from a wrong one. [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3 settles that refusals here may be specific — the token already names the subject, so there is nothing to enumerate and blurring buys nothing. Telling a signer who typed correctly that their code expired is the difference between a retry and a support call they have no way to make.
5. **The endpoint refuses abuse.** Cooldown and each of the three limiter keys produce `429` with `retryAfter`; the response body carries no destination.
6. **The request does not sit behind the relay, and the grant stays narrow.** Issuance reaches Notification by a direct call rather than by a relayed fact — asserted structurally, since a latency regression here is invisible to a functional test. And `composer arch` refuses a Session import of `Notification\Contract\Event\*` while permitting `Notification\Contract\Command\*`: the whole of ADR-0051 is that distinction, and a grant widened by one line would pass every behavioural test.
7. **An undeliverable code has a way out, and the way out issues a *new* code.** A hard bounce reaches the [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) path, the corrected address returns the recipient to `PENDING`, and what then goes out is a **new challenge under a new cause** — not a re-delivery of the invalidated one, which cause convergence would swallow in silence. TASK-025 owns the first half of that sentence and asserts it for an invitation; this bar is the second half, and it is the one that only exists because the payload is an OTP.

**What no bar covers, and will not:** that a plaintext code never reaches a log or an event payload, and that the limiter stays scoped to three keys. Both are review-held, and both fail silently. Worth a second reader on the issuance path specifically.


---

## 6. Cross-repo coordination

**`f5sign-signer` is affected and this is additive for them**, unlike [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md), which withdrew a credential from three shipped routes. What arrives: a new declarable method (`OTP_EMAIL`) in a union they already widened to fourteen; **route 4**, the re-send control, which they have to draw because a delivered code that never arrives has no other recovery; and a `429` on that route carrying `Retry-After`, which they must surface as a countdown rather than as an error — the server-side minimum interval exists precisely so the client can stop being trusted to enforce its own.

⛔ **The response never echoes the destination.** Any *"sent to ···456"* affordance is masked **server-side** and handed over masked; the client must not reconstruct it from anything it holds. A handoff record under `docs/frontend-handoff/` is owed in the same changeset, per that directory's own rule.

The **sender** surface does not change: declaring `OTP_EMAIL` is the same add-recipient field TASK-021 shipped, and the availability adapter opening by one is a parameter, not an endpoint.

## 7. Open follow-ups

- **`BL-157` becomes live in this slice.** Giving a challenge a TTL makes the latent `23505` reachable: the partial unique index counts a gate as occupied by `consumed_at IS NULL` only, while `ensureLiveChallenge()` treats an expired challenge as absent and mints beside it. §2 carries the full warning at the site that will cause it. **This is a prerequisite of the first code with an expiry, not a follow-up.**
- **`BL-159` also becomes live.** A verified signing proof never expires, because consumption never checks liveness — harmless while no challenge carries a TTL, which is exactly what this slice ends.
- **The delivered code lands at rest, unenciphered**, in `notification.notification.variables` — Notification's create-then-transmit split re-reads its template slots at transmission. §2 records that this slice does not clean it up; it is the first real consumer of the cipher `ADR-0033` proposes and nothing calls.
- **The IP limiter key is a spend ceiling and not an actor** (§4). If anything later wants a per-actor control on this surface, it needs a different key, and that is a decision rather than a tuning.

---

## 8. Deviations, and what the slice found on the way

Appended at close, 2026-08-19. ⚑ Sections are stable `§N` anchors cited from other documents, so this is added at the end rather than renumbering anything above it.

### 8.1 One route serves both issuance operations

§2 and [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.5 describe *ensure* and *mint* as two operations, and §2 names one route. They are reconciled by a **body discriminator** rather than a second route: `POST /api/v1/signing/session/auth/otp/send` takes `{"resend": bool}`, **optional, absent meaning `false`**.

That is not a shortcut — ADR-0049 §2.3's route partition is an eight-row table whose row 4 reads *"issue **or** re-send the code"*, and ADR-0049 became `Accepted` on 2026-08-19. Adding a ninth row would have been contradicting an accepted decision, which is an ADR change rather than an implementation choice. §2.5's split is a split of **domain** operations, and it is honoured as two aggregate methods (`ensureLiveChallenge()` / `mintChallenge()`).

⛔ **The default direction is load-bearing.** A client that omits the field gets *ensure*, which can never kill a live code. Defaulting the other way would make *forgetting* the field equivalent to invalidating the signer's code on every page load — silent on the server, mystifying on the client. The consuming app confirmed this was not hypothetical: mount and re-send were literally the same call in three places on their side.

### 8.2 The port call sits just outside the issuing transaction

[ADR-0051](../adr/ADR-0051-notification-inbound-command-surface.md) §2.3 says the port call *"creates the occasion inside the caller's transaction"*. It is made **immediately after** it instead, and the ordering was chosen against the failure it produces rather than against the sentence.

Asking Notification first means a real email goes out carrying a code that the minimum-interval guard — which lives in the aggregate, under the row lock — may then refuse to mint. The signer receives a code the server does not know, and cannot recover. Written first, the failure is a challenge with no message: the signer waits out the interval and asks again, and the 500 is loud. What §2.3 was actually buying, *the request escapes the relay*, is unaffected; what is conceded is atomicity between the domain write and the occasion. Recorded in ADR-0051 §3.2.

⛔ Do not "fix" it by moving the call into the repository: `SessionInfrastructure` is not granted the layer, and widening the grant to give it one would undo ADR-0051 §2.2 — which is the entire decision.

### 8.3 `OtpVerified` is not a new fact; `OtpSent` is

§3 scopes *"`OtpSent` / `OtpVerified` facts on the event log"*. Only the first was added.

[ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.6 enumerates **six** milestones — *"a challenge issued, a delivery requested, a verification passed, a gate passed …, a lockout reached, a lockout lifted"* — and [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) shipped five. The one it could not ship is *a delivery requested*, because it had no delivery: that is `OtpSent` (`AUTH_OTP_SENT`). **Verification already has its fact** — `AuthVerificationPassed`, which carries the method — so minting a second event firing at the same instant for one method would have re-typed history rather than recorded anything new.

⚑ `OtpSent` is genuinely distinct from `AuthChallengeIssued` rather than a rename of it: a pre-shared `ACCESS_CODE` issues a challenge and requests **no** delivery, so the two do not co-occur in the common case, and only the second can testify that the platform tried to reach somebody.

### 8.4 The edge grew an extension-member seam

The 429 owes a body member (§5 bar 5), and `ApiExceptionListener` could only put the wait in a header. Two additive changes at the boundary: a `Kernel\Exception\ProblemExtensions` interface — the exact sibling of `ProblemCoded`, so the BC owns the terms and the edge enumerates none — and its merge in `problem()`, with the five RFC members guarded against being overwritten from inside a refusal's own body.

⚠ **A second, smaller gap was closed with it**: `ProblemCoded` was honoured only on the *domain* branch, so an edge-born refusal could carry a status and a `Retry-After` but never its own machine `code`. That is how a rate limiter's 429 ends up published as `TOO_MANY_REQUESTS` — a term the consuming app maps to its *invalid link* screen, which would have told a signer asking for a second code that their link was not valid.

⚑ **Not spelled `retryAfter`.** ADR-0049 §2.10 promises that name; it was written before any body member existed, was never built, and every member on this API is snake_case. The wire won: `retry_after_seconds`, plus an **absolute** `retry_at` the consuming app asked for and justified — the happy path of an emailed code is leaving the app to read mail and coming back, and a backgrounded tab has its timers suspended, so a relative countdown drifts on the *normal* path rather than on an edge.

### 8.5 What §5 said no bar would cover, and what happened to it

§5 closes: *"that a plaintext code never reaches a log or an event payload, and that the limiter stays scoped to three keys. Both are review-held, and both fail silently."*

The first is now **partly** mechanical: `OtpSent`'s payload key set is asserted **closed**, so a member added later reddens rather than shipping. What stays review-held is the negative across every *other* surface — and the review found one: [`BL-161`](../BACKLOG.md), a log channel that would fold every template variable into a log line. It is unreachable only because no purpose routes to `LOG`, which is the empty-exempted-set shape `CLAUDE.md` authoring rule 5 names.

The second stays review-held entirely. The three keys are configuration, so a fourth — or a widened third — is a spend incident rather than a test failure, exactly as §4 predicted.

### 8.6 A defect this slice introduced and then closed — the eternal challenge

Worth writing down because it was **found by review rather than by a gate**, it fails *closed*, and failing closed is exactly what made it look harmless.

`submitAuthResponse()` ensures-then-verifies: it opens a challenge before comparing. That is right for a pre-shared `ACCESS_CODE`, which has no issuance route — the challenge legitimately first exists there. Once `OTP_EMAIL` became declarable, the same path applied to a **delivered** method the moment a signer submitted a code that had just timed out: it minted a replacement carrying `verifierHash: null` and `expiresAt: null`.

The gate then refuses it — `AUTH_GATE_MISCONFIGURED`, not an open door — so nothing is bypassed and every security test stays green. ⛔ **What is lost is the signer.** That row is unconsumed and has no expiry, so it occupies the gate for ever; every later *ensure* hands it back with `minted: false`, no message is ever sent again, and the person sits in front of *"enter the code we sent you"* waiting for a code that cannot exist. It also makes `AUTH_CHALLENGE_EXPIRED` unreachable, so the one refusal that would have told them to ask for another is replaced by one that tells them nothing they can act on.

**Fixed** by not ensuring at all for a method that delivers: only route 4 may open one of those, because only route 4 knows the code and can send it.

⚑ **The part worth keeping is how nearly it shipped.** The guard was added with a mirror in the in-memory double, and sabotaging the **double** reddened the Application tier — which reads like coverage. Sabotaging the **real adapter** left **seventy** tests green, because no test reached that seam. That is `CLAUDE.md` authoring rule 4's *"a gate says nothing about a property its harness cannot reach"*, encountered rather than recited. `DeliveredCodeIssuanceTest::the_verify_path_does_not_conjure_an_eternal_challenge_for_a_delivered_method` is the case that reaches it, and it was sabotage-verified against the production guard rather than against the double.

⚠ And its first assertion was wrong in the instructive direction: *"no unconsumed row survives"* fails, because the timed-out row legitimately stays unconsumed until route 4 retires it. The property that actually discriminates is whether a **second** row appeared and what it carries — a null verifier and a null expiry.

### 8.7 What the gates measured

All five, in the isolated worktree lane (`WT_GATES`), which is the only harness whose green is about *this* branch — the infra make targets mount the main checkout and report on whatever it is sitting on.

| Gate | Result |
|---|---|
| `lint` | 0 of 935 |
| `arch` (Deptrac) | 0 violations |
| `phpstan` (L9) | `[OK] No errors` |
| `test` | **OK (1977 tests, 9823 assertions)** — baseline at `e1370e1` was 1901 / 9447 |
| `infection` | **Covered Code MSI 87%**, MSI 57%, 7125 mutants, 4m48s |

⚑ **Covered-MSI held at the 87% baseline**, which is the gated figure ([ADR-0035](../adr/ADR-0035-testing-standard.md) gates mutation strength, not line coverage). Overall MSI moved 58% → 57%, which is the expected direction when a slice adds source faster than it adds mutation-killing tests, and is not what the gate measures.

⚠ **The mutation gate was down for one run and the cause is worth recording**, because it looked like an Infection problem and was not: a `#[UsesClass]` naming an **interface** emits a PHPUnit 11 warning (an interface is not a valid coverage target), and Infection treats a warning-bearing initial run as a failed one — so it aborted before generating a single mutant, with an exit code that says nothing about mutation strength. Two attributes, five gates' worth of silence.

### 8.8 Where each acceptance bar is held, and the one that nearly could not fail

§5's bars name no harness, which `spec-lint` flagged — and for bar 5 it was not a formality. The limiter counts in a **shared store**, and the worktree validation lane brings up no Redis; a limiter whose store is unreachable **fails open by design**, so bar 5 would have passed there while asserting nothing. That is the empty-refusal-set shape `CLAUDE.md` authoring rule 5 names, and it would have looked green forever.

⛑ **Closed by defining the pool per environment**: `when@test` gives `cache.rate_limiter` an in-memory adapter, so the limiter genuinely counts and genuinely refuses under test, while dev and prod keep Redis. ⚠ Doing it as a one-key *override* of a shared definition does **not** work and fails in a way that looks unrelated — Symfony merges the surviving `provider:` into `ArrayAdapter::__construct(int $defaultLifetime)` and every limiter-touching test dies with a `TypeError`. Measured, and written into `config/packages/cache.yaml` so nobody re-derives it from a red run.

| Bar | Held by | Tier |
|---|---|---|
| 1 — a re-send actually sends | `IssueAuthChallengeUseCaseTest::two_issuances_carry_two_distinct_causes`, and ✅ confirmed end-to-end 2026-08-19: two *ensure* calls produced **one** code email in the recipient's mailbox — the mailbox, not the `minted` flag, which is the only thing that could tell them apart | Application + external E2E |
| 2 — a re-send does not restore the budget | `SigningSessionDeliveredCodeTest` (aggregate) + the acceptance walk (the path) | Unit + Acceptance |
| 3 — the previous code dies, but only when something minted | `SigningSessionDeliveredCodeTest` (both halves) + `DeliveredCodeCeremonyHttpTest` | Unit + Acceptance |
| 4 — expiry refuses under its own code | `SigningSessionDeliveredCodeTest::an_expired_code_is_refused_under_its_own_code_distinct_from_a_wrong_one`, paired with the inside-the-window case so it cannot pass by refusing everything | Unit |
| 5 — the endpoint refuses abuse (**cooldown**) | `DeliveredCodeCeremonyHttpTest`, over real HTTP: 429, closed body key set, `Retry-After` equal to `retry_after_seconds`, absolute `retry_at`, and no destination anywhere in the raw bytes | Acceptance |
| 5 — the endpoint refuses abuse (**limiter keys**) | ✅ **closed 2026-08-19 by an end-to-end run against the dev stack** — see below | Application + external E2E |
| 6 — the request does not sit behind the relay; the grant stays narrow | `NotificationInboundGrantTest` (walks the source tree, not the config it guards) | Architecture |
| 7 — an undeliverable code issues a *new* code | ⛔ **not held by a bar in this slice** — see below | — |

⚠ **Bar 5's limiter half is held at the Application tier and NOT over the wire, and the cause is the harness rather than the limiter.** A cache pool carries Symfony's `kernel.reset` tag, and `Kernel::handle()` sets `resetServices = true` — so the *next* request empties the in-memory pool. `disableReboot()` suppresses the kernel **reboot**, not the **resetter**. Measured by reflecting into the pool between requests: the same adapter instance survives (same object id) and every key reports a hit count of 1 on every request, so `otp_email_session` never approaches its ceiling of five. Driven in one process the limiter refuses on the sixth consume, so the component is fine.

What that leaves uncovered is narrow and worth naming precisely: the limiter refusal's **wire shape**. `IssueAuthChallengeUseCaseTest` covers *when* the limiter is consulted (and that *ensure* over a live challenge spends nothing); the 429 shape is asserted end-to-end for the **domain cooldown**, and the two refusals are held identical by `OtpSendRefusalParityTest` rather than by assertion-in-two-places. Closing it properly needs a test-environment pool without the `kernel.reset` tag.

⚑ **CLOSED 2026-08-19, and by the consuming app rather than by this repository.** The signer session drove the
limiter to its ceiling against the dev stack — where the pool is Redis and therefore counts for real — using the
**destination** key (10/hour) across twelve sessions rather than the session key, so each request cleared its own
60-second interval and the refusal that landed was unambiguously the limiter's. It cut at the eleventh:

```json
{"type":"about:blank","title":"Too Many Requests","status":429,
 "code":"OTP_SEND_COOLING_DOWN",
 "retry_after_seconds":359,
 "retry_at":"2026-08-19T13:47:42+00:00"}
Retry-After: 359
```

**Byte-identical in shape to the domain cooldown** — same machine code, both body carriers, the header — differing only
in `detail`, which no client renders. So `OtpSendRefusalParityTest`'s claim holds on the wire and not merely across two
constructors, and the observable below did **not** occur: the countdown started and the button stayed disabled for the
full 359 seconds.

⚠ **What that does and does not retire.** The gap in *this repository's* harness is unchanged — Symfony's service
resetter still empties the in-memory pool between requests, so a test here still cannot see it. What changed is that
the property is now evidenced, by a run this repo cannot reproduce. Anyone re-opening the question should know the
evidence is external and lives in `f5sign-signer`'s `smoke-otp-limiter.sh`, not in `tests/`.

⚑ **And the consuming app named the observable to look for, which is worth more than the description above.** Its countdown prefers `retry_at`, falls back to `retry_after_seconds`, and **invents nothing** when neither is present — so a limiter 429 that shipped without the body members would not render as wrong text. It would render as a **re-send button that stays enabled after a 429**, which the signer then presses and immediately eats another one. That is the signature an end-to-end run should watch for; it is not reachable from this repository, which is why it is written down here.

⛔ **Bar 7 is the one this slice does not close, and it is stated rather than quietly dropped.** The property is that a corrected contact re-triggers a **new challenge** rather than a re-delivery of the invalidated one. The mechanism that makes it true is in place — every issuance carries its own cause token, so a re-delivery under the old cause is impossible by construction rather than by discipline — but the end-to-end walk it deserves crosses into [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md)'s correction path and is not exercised here. What holds it today is the cause-token property (bar 1) plus review. Carried into §9.

## 9. Open follow-ups

- **[`BL-160`](../BACKLOG.md) — the code at rest.** §2 and §7 defer it to `BL-113`, which is **Resolved** and whose fix is link-specific; a deferral pointing at a closed row is one nobody will find. `BL-160` is its own home. Partly mitigated in this slice: `code` joined `SECRET_BEARING_VARIABLES`, so it is dropped once every delivery is terminal.
- **[`BL-161`](../BACKLOG.md) — the log channel would print a delivered secret.** New, found while adding `code` to that list.
- **[`BL-159`](../BACKLOG.md) is now live**, as §7 predicted, and is **not** fixed here. A verified signing proof still never checks liveness. Narrowing a consumption guard changes the act binding and wants its own bar rather than riding along in a slice about codes; the row was updated so it no longer claims to be unreachable.
- **[`BL-157`](../BACKLOG.md) is Resolved** — the fix is one line in `SigningSession::openChallenge()`, held at two tiers and sabotage-verified at both.
- **[ADR-0051](../adr/ADR-0051-notification-inbound-command-surface.md) is promoted — this follow-up is closed.** Every bar in its §5 was green and §6 enumerated the artifacts, and this slice deliberately left the `Status` row unchanged because that call was reserved. The user gave it on 2026-08-19: the ADR is now `Accepted` *(exercised; §2.3 narrowed)*, and the qualifier is §8.2's deviation, which is this slice's.
- ⛔ **Acceptance bar 7 has no end-to-end bar** (§8.6). The cause-token property that makes it true is asserted; the walk through the correction path is not. It is the one bar this slice leaves to review.
- **The two one-factor-twice mitigations still do not exist** (§3). Until slice 3, an `OTP_EMAIL` envelope delivered by email asserts more ceremony than it performed. Known, accepted, temporary — and legally material.
