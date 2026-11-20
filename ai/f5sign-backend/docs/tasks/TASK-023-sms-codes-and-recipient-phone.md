# TASK-023 — SMS one-time codes: the recipient phone, a new class of personal data held in the clear

<!-- OFFREPO: §4, §6 and the Provider row state facts about Twilio's REST API and its free test surface
— the Verify-versus-Programmable-Messaging product split, the magic numbers `+15005550004` and
`+15005550001`, the error codes `21614` and `21211`, and the trial account's terms (100 units, 30 days,
the "Sent from your Twilio trial account" prefix) — plus Spain's advance alphanumeric-sender
registration and the processor-agreement/data-residency position. They were read from Twilio's public
documentation and from Spanish carrier rules on 2026-08-19 and each is restated inline by
[TASK-030](TASK-030-sms-delivery-channel.md) §5/§6, which is reachable from this repository. §3 also
cites `ETSI EN 319 142-1` for PAdES baseline levels; its in-repo home is
[`SignatureLevel`](../../src/F5Sign/SignatureExecution/Domain/Pdf/ValueObject/SignatureLevel.php). Nothing
here depends on reading any of those sources. -->

| Field | Value |
|-------|-------|
| **Status** | ✅ **Implemented on `feat/sms-codes-and-recipient-phone`**, branched from `develop` at `8245900`; landed as `d7874ff` and merged `--no-ff` into `develop` as `ed92eaf` on 2026-08-20, with the `BL-172` answer following as `f287454` / `59bb445`. ✅ **Pushed to `origin/develop` the same day**, on the user's instruction — it had been deliberately held back until then. Green on the **worktree lane** (`make -C ../f5sign-infra wt-backend src=$(pwd)` with `WT_GATES="lint arch phpstan test"`), which is the only harness that validates this tree — the main-checkout make targets bind-mount `../f5sign-backend` and report on another branch. ⛔ **One acceptance bar is NOT met and is not claimed: the Delivery bar's *on a real handset*.** No Twilio account exists — the same blocker as [`BL-169`](../BACKLOG.md), whose sandbox tier is built and has never run — so nothing here has ever put a message on a device, and `SMS_DSN` is `null://null` in dev and test. Everything below the handset is built and exercised. ⚑ **One decision was escalated rather than taken, and then answered**: whether the phone joins the sender-facing envelope response is a personal-data question (§3), so the slice shipped without it — the cheap direction to reverse — and the user answered on 2026-08-20 that it is published **whole, like `email` beside it**, on the ground that a partial measure now is worth less than a coherent carrier over both columns later ([`BL-171`](../BACKLOG.md)). Landed on `feat/recipient-phone-on-the-envelope-response`; [`BL-172`](../BACKLOG.md) is **Resolved**. See §10 for what deviated. Originally a forward plan, written 2026-08-10, re-scoped 2026-08-19 (§7 D1–D4) and 2026-08-20 (§7 D5 and the two §2 widenings). |
| **Why** | The only delivered second factor the platform has shares a channel with the invitation: link and code land in the same mailbox, so one compromised mailbox yields both. That is **one factor twice, not two**, and it is the gap SMS exists to close — a code on a handset is a genuinely separate channel. ⚑ Disagree with this by disagreeing with the premise: if invitations stop travelling by email, or if the product accepts single-channel delivery as sufficient, the case for a paid channel weakens accordingly. |
| **Decision record** | [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) (`Accepted`) for the ceremony this reuses, and [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) — ⚠ **`Proposed`, not `Accepted`** — for the capability port the availability row joins. **No new ADR is expected**, because §7 D3 moved the one thing that needed one out of scope. What would force one: reintroducing the signature-level projection (cross-BC), or landing the billing persistence here (a `Foundation/Billing` surface). ⛔ **This task exercises [ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md) in no way, as of 2026-08-20** (§7 D5) — it used to be its first caller, and the row said so. That ADR stays `Proposed` with zero callers; see §9 for why that is a cost rather than a neutral outcome. |
| **Type** | **Forward build** — slice 3 of 3, and the only paid one. ⚑ **Narrowed on 2026-08-19**: it used to add the channel too, and [TASK-030](TASK-030-sms-delivery-channel.md) now holds that half. What is left here is the personal data an SMS needs, the authoring guard around it, and the metering that makes it billable — the OTP-shaped work, over a transport that already exists by the time this starts. |
| **Builds on** | **[TASK-030](TASK-030-sms-delivery-channel.md) (the SMS channel itself — `DeliveryChannel::SMS`, the provider adapter, the failure taxonomy, the copy and the sandbox tier, all reused unchanged; it is a hard dependency, not a preference)**, [TASK-022](TASK-022-delivered-codes-over-email.md) (the entire delivered-code mechanism **and the recipient-correction path**, both reused unchanged — this slice adds a destination, not a ceremony and no longer a channel). ⚠ **[ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md) was in this row until 2026-08-20** as *"whose cipher this is the first caller of"*; §7 D5 removed the encryption, so this task now builds on it in no way at all. |
| **Delivery bar** | A recipient declared `OTP_SMS` receives a code **on a real handset** through a real provider, and the phone round-trips as canonical E.164. ⚠ **The *enciphered* half of this bar was removed on 2026-08-20** (§7 D5): the column is stored in the clear, deliberately. ⚠ *On a real handset* is meant literally and is the one clause the free sandbox cannot retire — see §6. ⚑ **The usage-row clause was removed on 2026-08-19** (§7 D1): with the meter still null, a bar asserting a charge would pass vacuously, and a bar that cannot fail is not a bar. |
| **Provider** | **Twilio, Programmable Messaging** — decided 2026-08-17, and **owned by [TASK-030](TASK-030-sms-delivery-channel.md) since 2026-08-19**, which is where the vendor seam, the failure taxonomy and the sandbox live. Restated here because two of its consequences are prerequisites of *this* slice rather than of that one, and both have lead times measured in weeks with no engineering content: **data residency and the processor agreement** (a Spanish phone number is personal data crossing to a US-headquartered vendor — this is the slice that creates that data), and **alphanumeric sender registration**, which Spain requires in advance. ⚑ The third consequence, **Programmable Messaging and not Verify**, is recorded in [TASK-030](TASK-030-sms-delivery-channel.md) §5 and repeated in §4 below, because the temptation is strongest in an OTP slice. ⚠ The earlier text called the channel *"a Foundation adapter"*; [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md)'s **pattern** is honoured exactly, but the adapter is a Notification Infrastructure service — `Foundation` may import only `Kernel` and `Vendor`, so it could not name a `DeliveryChannel` at all. |
| **Scheduling** | **Deferred — future work**, confirmed 2026-08-17, and now **sequenced behind [TASK-030](TASK-030-sms-delivery-channel.md)**, which is the half that can start immediately and carries the vendor lead times. Nothing in [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) or [TASK-022](TASK-022-delivered-codes-over-email.md) waits on it, and email carries the whole delivered-code mechanism until it lands. What the deferral costs is named under [TASK-022](TASK-022-delivered-codes-over-email.md)'s *Out of scope*: until a second, genuinely out-of-band channel exists, an `OTP_EMAIL` envelope delivered by email asserts more ceremony than it performed, and that overstatement is legally material. It survives the deferral; it should not survive indefinitely. |
| **Closes** | [`BL-162`](../BACKLOG.md) — a sender can declare a delivered method against a recipient who has nowhere to receive it, and nothing says so until a signer is already stuck (§7 D4 makes the guard per-method rather than SMS-only, which is what closes it rather than half-closing it). |
| **Does NOT close** | ⚠ [`BL-117`](../BACKLOG.md), **and this row is a correction**: until 2026-08-19 this record promised it. Closing it needs the signature-level projection, which §7 D3 moved out of scope because the strength ordering it depends on is undecided and [`BL-119`](../BACKLOG.md) argues this is the wrong place to decide it. What this task *does* buy is that the overstatement stops being structural — a second, genuinely out-of-band channel will exist — and becomes only *"we have not ranked them yet"*. |

---

## 1. Why this task exists

After [TASK-022](TASK-022-delivered-codes-over-email.md) the ceremony is complete and the only delivered factor shares a channel with the invitation. SMS is what makes the second factor an actually separate one, and it is the factor senders ask for by name.

It is last because everything genuinely new about it is expensive rather than structural: a personal-data column that does not exist, a paid third party, and a metering path that must not double-charge. None of that teaches us anything about the two-gate model, which is why it is not allowed to gate the model.

⚑ **And the paid third party left this record on 2026-08-19.** [TASK-030](TASK-030-sms-delivery-channel.md) builds the SMS channel on its own, because a transport is not an authentication concern: the invitation and the completion notice want a phone as much as the code does, and the vendor-shaped work — a contract, a sender-ID registration, an error taxonomy, a cost model in message segments — has lead times that should not sit behind a PII migration. What is left here is the OTP-shaped half, and it is the half that needs a schema change.

**The recipient row has no phone number at all.** [`Recipient`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php) carries `email` and `fullName` and nothing else — so this is not "add a column to send an SMS", it is introducing a new class of personal data to the Envelope aggregate.

⛔ **And the phone is stored in the CLEAR — decided 2026-08-20 by the user, reversing this record's founding premise.** Until that date this task was *"the recipient phone as the first enciphered column"*, and it was going to be [ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md)'s first caller. §7 D5 carries the whole argument; the short version is that enciphering **this** column while the `email` beside it stays plaintext protects the rare field and leaves the universal one exposed, and that the same number is written unenciphered to `notification.notification_delivery.destination` on **every send** anyway. ⚠ **This is a deliberate cost, not an oversight**: the task introduces a new class of personal data to the Envelope aggregate and does not protect it. [`BL-171`](../BACKLOG.md) holds what is owed.

## 2. What gets built

**The destination.** A phone number on `Recipient`, stored **in the clear** (§7 D5), with no database default on a domain-authored column ([ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §4). ⚑ **A plain additive column, and the expand / backfill / contract ceremony no longer applies**: that discipline was here to get a *cipher* onto an existing column safely, and a new nullable column with nothing to backfill is one `ADD COLUMN`. Nullable, because most recipients will never have one — and a `OTP_SMS` declaration against a recipient without one is an **authoring-time refusal**, not a runtime surprise discovered when the signer is already waiting.

**And it is a value object, not a string (§7 D2).** `PhoneNumber` normalizes to **E.164 at construction** and validates through `giggsey/libphonenumber-for-php-lite`, kept **behind the value object** so the library is an implementation detail the domain never names. Two reasons, and the second is the one that makes it urgent rather than tidy. ⚑ **In Spain mobile and fixed line are decidable from the number** (6xx/7xx against 8xx/9xx), which they are not everywhere — the library answers `FIXED_LINE_OR_MOBILE` in countries where the number does not say. So a Madrid landline like `+34911234567`, which a length-and-plus regex accepts happily, is caught **at authoring** instead of being accepted by Twilio, **charged**, and returned as `21614` *"cannot receive SMS"* at the moment the signer is waiting. ⛔ **Normalize before storing, and get it right the first time.** ⚠ This clause read *"normalization happens before encryption … not a later `UPDATE` but a decrypt-and-rewrite of every row"* until 2026-08-20; with the column in the clear (§7 D5) a repair **is** a plain `UPDATE`, which is genuinely cheaper. The reason to still get it right has not changed and is the half worth keeping: the canonical form is what every later comparison, correction and support lookup reads, so a row stored non-canonically is not wrong in one place, it is unmatchable everywhere.

✅ **Installed 2026-08-20 at `9.0.37`, and the claim above was verified against the library rather than its documentation** — a Spanish 6xx and 7xx answer `MOBILE`, a 9xx and an 8xx answer `FIXED_LINE`, and `+34123` is refused as invalid. The `FIXED_LINE_OR_MOBILE` ambiguity this paragraph warns about did **not** occur for `ES`, which is the whole argument for §5 bar 6. It pulled in **zero** transitive packages. ⚑ **One API detail for whoever writes `PhoneNumber`:** in v9 `PhoneNumberUtil::getNumberType()` returns a `PhoneNumberType` **enum**, not the integer constant every pre-9 example on the internet compares against — so a copied snippet fails at the comparison rather than at the call.

⚠ **Two things about that dependency, both checked 2026-08-19.** The `-lite` variant is the one to take: it drops `giggsey/locale` (geocoding, carrier and timezone metadata, none of which we need) and requires only `symfony/polyfill-mbstring`. And its **metadata goes stale** — numbering plans change, so validation living in a dependency is a standing commitment to keep it current; an outdated copy refuses a legitimately new range, and the library is occasionally stricter than reality. Refusing at authoring time is what makes that survivable: the sender is present and can fix it.

⚑ **It needs no `deptrac.yaml` change, and the reason is worth knowing rather than relying on.** The `Vendor` collector's regex names Symfony, Doctrine, Psr and a dozen more, and `libphonenumber\` is not among them — but neither is `Lcobucci\`, which `Foundation/Http/SessionCredentialCodec` imports today with `composer arch` reporting zero violations. A class matching no layer is *uncovered*, and uncovered dependencies pass silently. So the collector reads like an allowlist and is not one; see [`BL-167`](../BACKLOG.md).

**The channel — no longer built here.** `DeliveryChannel::SMS`, the provider adapter behind the existing `NotificationChannel` port, its failure taxonomy and its copy are [TASK-030](TASK-030-sms-delivery-channel.md), and this slice consumes them unchanged. What survives in this record is the constraint that shaped them: the provider is a **delivery vendor only** — code generation, expiry and verification stay ours (§4).

**The channel the declared method names, carried end to end — and the selector shut out of the OTP path.** [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 says Notification *"has nothing to select"* for a delivered code, and nothing realizes that sentence: [`OneTimeCodeDeliveryService`](../../src/F5Sign/Notification/Application/Service/OneTimeCodeDeliveryService.php) asks [`DefaultChannelSelector`](../../src/F5Sign/Notification/Domain/Service/DefaultChannelSelector.php), which answers `[EMAIL]` for every purpose it carries. ⛔ **This is the task that turns that from inert into a live defect**, because it is the task that makes `OTP_SMS` declarable: the moment a sender can declare it, [`RecipientAuthContextReader`](../../src/F5Sign/Session/Application/Query/RecipientAuthContextReader.php) resolves a phone as the destination, the selector still says `EMAIL`, and `EmailNotificationChannel::send()` does `->to('+34600…')` — a hard throw the retry ladder cannot resolve, arriving while the signer waits at a gate. ⚑ It was **nobody's** until now: [TASK-030](TASK-030-sms-delivery-channel.md) §5 and [TASK-031](TASK-031-channel-selection-beyond-email.md) §4 both assume it already works, and this record's own §3 did not name it.

Four parts, and the fourth is what stops it coming back:

- [`ExecutedAuthMethod`](../../src/F5Sign/Session/Contract/Type/ExecutedAuthMethod.php) gains a `deliveryMedium()` beside `deliversCode()` — the same `match` over all fourteen catalog members **with no `default` arm**, for the reason that docblock already gives, so `OTP_WHATSAPP` and `OTP_VOICE` are classified deliberately rather than exempted by silence (`CLAUDE.md` authoring rule 5). It is the sibling of the per-method destination guard above: one says *which contact this method needs*, the other *which channel it travels on*.
- [`OneTimeCodeRequest`](../../src/F5Sign/Notification/Contract/Command/OneTimeCodeRequest.php) carries that medium **as an opaque string**, beside the destination it already carries. ⚑ Not a `DeliveryChannel`: [`deptrac.yaml`](../../deptrac.yaml) grants `NotificationContractCommand` only `Kernel` and `Foundation`, so it cannot name one — and the shape is already settled inside that very class, where `$locale` is a `?string` although `Foundation\Templating\Locale` was importable. This follows a precedent rather than inventing a convention.
- `OneTimeCodeDeliveryService` builds its own `ChannelSelection::of([…], SINGLE)` from that medium and **drops `ChannelSelector` from its constructor**. ⛔ **Its `SMS` arm currently throws [`UnroutableChannelException::noDestinationFor()`](../../src/F5Sign/Notification/Application/Exception/UnroutableChannelException.php), and this task must REPLACE that guard rather than relax it.** The comment in place says exactly why it is there and why it is this task's to remove: the service cannot see the medium at all, and the only caller resolves `destination` from `$context->recipient->email` unconditionally, with no branch on the method — so a selector choosing SMS today would post a mailbox to Twilio as `To`, which is a silent `21211` **and a charge**, not a refusal. Making the destination method-dependent is precisely the first half of this bullet list; the arm becomes a real target only once it has. ⚠ A test pins the refusal (`OneTimeCodeDeliveryServiceTest::it_refuses_a_channel_whose_medium_the_caller_cannot_have_addressed`, sabotage-checked) — **convert it, do not delete it**: what it asserts afterwards is that the medium and the destination agree.
- ⛔ **And `DefaultChannelSelector`'s `AUTH_OTP` arm becomes a `throw`.** The `match` is exhaustive over [`NotificationPurpose`](../../src/F5Sign/Notification/Domain/ValueObject/NotificationPurpose.php), so the purpose still needs an arm, and leaving `[EMAIL]` there as dead code is the empty-exempted-set shape authoring rule 5 warns about — nothing can go red, so green means nothing. Throwing converts §2.7 from prose in four homes ([`ChannelSelector`](../../src/F5Sign/Notification/Domain/Port/ChannelSelector.php)'s docblock, the selector's own, `notification-domain-model.md` § Channel selection, and [`DefaultChannelSelectorTest`](../../tests/F5Sign/Notification/Unit/Domain/Service/DefaultChannelSelectorTest.php)) into something a wrong caller cannot get past. ⚠ [TASK-031](TASK-031-channel-selection-beyond-email.md) §4 warns that widening the selector is *precisely* the change that makes re-introducing an OTP override look natural; this is what makes that warning enforceable rather than hopeful.

**The masked destination learns a second shape — decided 2026-08-20, and without it every SMS recipient sees a blank.** [`MaskedDestination::of()`](../../src/F5Sign/Session/Application/Service/MaskedDestination.php) returns `null` for any value with no `@`, so the moment a destination is a phone number the descriptor route serves `masked_destination: null`. ⛔ **That blank is not a cosmetic loss, and the class's own docblock is the argument against it**: the masked value exists so a signer can recognise their own contact on *"the one screen where an anonymous code box is indistinguishable from a phishing page"*. Worse, `null` already means something else on that route — *"no address on file"* — so the client cannot tell a recipient with no phone from one whose phone we simply cannot render.

**The disclosure is the last two digits**, over an intact country code: `+34 ··· ··· ·56`. The country code is shared by every Spanish recipient and so discloses nothing about *this* one, while being what makes the string read as a phone at all; two digits is a 1-in-100 guess for a link-holder who does not already know the number, and it is the recognition cue for the person who does. ⚑ Both quantities are one constant each — say so where they are written, so the next person tuning them is tuning a decision rather than editing a regex.

⛔ **Recognise the phone POSITIVELY; do not widen the fallthrough.** The current `null` for an unparsed shape is deliberate and its comment says why — *"a partial mask over a value we did not parse could reveal more than the rule above promises"*. The new branch must match an E.164 number and mask that; anything still unrecognised keeps returning `null`. Turning the email branch into a general "mask everything after the first character" is the change that leaks.

⚠ **And it is two `#[OA\*]` strings, not one.** [`GetAuthDescriptorController`](../../src/F5Sign/Session/UI/Http/GetAuthDescriptorController.php) documents `masked_destination` twice — once for the gate's own method and once for the recovery method — and both say *"null when no address is on file"*, which stops being the whole truth here. Per `CLAUDE.md` authoring rule 1 those strings are emitted **verbatim** into the generated OpenAPI spec the frontend team ratifies, so they are contract text rather than comments. A [`docs/frontend-handoff/`](../frontend-handoff/) note is owed with them (§3).

**Correction.** `CorrectRecipient` — built for email in [TASK-022](TASK-022-delivered-codes-over-email.md), where the first undeliverable code made it a prerequisite rather than a nicety — extends to patch the phone under the same max-3-corrections rule, so a wrong number routes into the `RecipientDeliveryFailed` → `DELIVERY_FAILED` → correction path rather than into a support ticket. This is the *only* recovery for an undeliverable code, since [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 forbids falling back to another channel. Cheap here **only because slice 2 paid for it**; if TASK-022 ships without it, it lands here at full price and a failed SMS has no way back.

**The availability port opens by one again.** `OTP_SMS` joins the [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) availability adapter wherever a provider is wired — the row that also makes the Dedicated case honest: an install with no SMS vendor simply never offers the method. Distinct from, and additional to, the destination refusal above: one asks *can this deployment run the method*, the other *does this recipient have somewhere to send it*.

**The authoring guard, and it is per method rather than per channel (§7 D4).** Each delivered method declares **which destination it needs**, and the guard refuses a declaration the recipient cannot receive: `OTP_EMAIL` wants an address, `OTP_SMS` wants a number, and the next channel wants its own without the guard being rewritten. It sits beside `AddRecipientUseCase::guardDeclaredMethodsAreAvailable()`, which already asks the sibling question — *can this **deployment** run the method* — and answers a different one: *can this **recipient** receive it*. ⛔ Do not implement it as *"requires an email"*: [`BL-162`](../BACKLOG.md) names that shortcut and says it has to be rewritten the day a second destination exists, which is this task.

**Metering — the call site only; the persistence is deferred (§7 D1).** A billable issuance records usage through the Foundation billing port inside the same transaction as the state change that earned it, keyed on the challenge id minted back in [TASK-022](TASK-022-delivered-codes-over-email.md). Each re-send is a legitimately new challenge and therefore a legitimately new charge, which is why that slice's cooldown and three-key limiter had to land before a paid channel existed.

⚠ **What that does and does not buy, stated plainly because the earlier version of this record overclaimed it.** The port's only implementation is [`NullUsageMeter`](../../src/F5Sign/Foundation/Billing/NullUsageMeter.php), which records nothing, and there is **no usage table anywhere in the schema**. So *"a rolled-back issuance leaves no usage row"* and *"a duplicate is rejected rather than charged twice"* are asserted against a **recording double**, which proves the **caller** and not the **charge** — and the charge is the half that reaches an invoice. The real persistence, with its table, RLS contract, migration, append-only discipline and idempotency constraint, is [`BL-166`](../BACKLOG.md). ⛔ **The consequence is not theoretical and belongs in the open**: from [TASK-030](TASK-030-sms-delivery-channel.md) onward the platform can spend money and nothing counts it, which makes that record's §8 spend-alerting follow-up materially more urgent, not less.

## 3. Scope

**In scope:** the phone column — **plaintext** (§7 D5) — as a `PhoneNumber` value object over `libphonenumber-lite`, plus its additive migration; the **per-method** authoring-time destination guard; **`OTP_SMS` in the availability adapter**; **the declared method's channel carried end to end, and `DefaultChannelSelector` refusing `AUTH_OTP`** (§2, added 2026-08-20); **the phone shape in `MaskedDestination`, its two `#[OA\*]` strings and a `docs/frontend-handoff/` note** (§2, added 2026-08-20); **the `otp_sms_*` limiter policies** with their own numbers, which `config/packages/rate_limiter.yaml` already names this task as the owner of; phone correction; the same-transaction metering **call**, keyed on the challenge id, asserted against a recording double; tests per §5.

⚠ **And the wire surface, which no earlier version of this record named.** A phone has to *arrive*: [`AddRecipientRequest`](../../src/F5Sign/Envelope/UI/Http/Request/AddRecipientRequest.php) and its `#[OA\Property]`; [`CorrectRecipientRequest`](../../src/F5Sign/Envelope/UI/Http/Request/CorrectRecipientRequest.php), whose `email` is **required** today (`#[OA\Schema(required: ['email'])]`) and must become *at least one of the two*; and [`EnvelopeJsonPresenter`](../../src/F5Sign/Envelope/UI/Http/EnvelopeJsonPresenter.php), which already returns `'email' => $recipient->email` per recipient — so whether the phone joins it is a **PII decision**, not a field addition. All three are consumed by the dashboard, so the handoff note above covers them too.

**Out of scope:**
- ⛔ **The SMS channel itself** — [TASK-030](TASK-030-sms-delivery-channel.md), and a **hard dependency** rather than a deferral: `DeliveryChannel::SMS`, the Twilio adapter, the permanent-versus-transient error taxonomy, the SMS copy and the sandbox test tier all land there and are consumed here unchanged. Moving it out is not a reduction in what must exist before this ships, only in who builds it — the same manoeuvre [TASK-022](TASK-022-delivered-codes-over-email.md) made with the correction path.
- ⛔ **The signature-level projection, and with it `BL-117`** (§7 D3). Two things it needs do not exist: Signature Execution has **no auth-method input at all** — the seam is cross-BC and would be an ADR — and the **strength ordering** it would project through is undecided, because [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.1 declines to rank the catalog on the ground that strength is not one-dimensional (the same `OTP_EMAIL` is weak behind an emailed invitation and strong behind one handed over in person). [`BL-119`](../BACKLOG.md) says that ordering must be decided **tiered and eIDAS-anchored, with the case in front of it** — beside `SubstituteAuthMethod`'s accessibility swaps — rather than invented as a scalar here.

  ⚠ **And whoever picks this up later must not wire it into [`SignatureLevel`](../../src/F5Sign/SignatureExecution/Domain/Pdf/ValueObject/SignatureLevel.php).** That type already exists, it is about **PAdES baseline levels** (`B-B`, `B-T`, `B-LT`, `B-LTA` — ETSI EN 319 142-1, a question about timestamps and long-term validation data), and it has nothing to do with confidence in the signer's identity. The names collide and the wrong one is the one that is easy to find; the mistake would be plausible, silent, and would end up inside sealed documents.
- **The billing persistence** — [`BL-166`](../BACKLOG.md), deferred by §7 D1 rather than forgotten.
- **WhatsApp and voice.** Both are in the `AuthMethod` catalog and both are additional channels behind the same port; neither adds a decision. `OTP_VOICE` in particular is the accessibility substitution target and belongs with `SubstituteAuthMethod`, which [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.11 excludes.
- **Enciphering any column, this one included** (§7 D5, [`BL-171`](../BACKLOG.md)). Every personal-data column, new and old, stays exactly as it is.
- **Provider failover between vendors**, and **delivery-receipt tracking** beyond what the port already models.
- **Spend alerting and budget caps.** The limiter bounds the rate; nobody is watching the bill. Worth an owner before this ships to a real tenant.

## 4. Key decisions

- **The provider delivers; it does not verify.** ⚑ Recorded in [TASK-030](TASK-030-sms-delivery-channel.md) §5, which owns the vendor seam, and repeated here because this is the slice where the shortcut looks like a saving. Vendor "verify" APIs are genuinely attractive — generation, verification, delivery and anti-fraud in one call, and they would remove [TASK-022](TASK-022-delivered-codes-over-email.md)'s abuse surface entirely. Rejected for the verification half because it relocates the `OtpVerified` fact — precisely the evidence the audit trail exists to sustain — into a third party's records. Kept, and recommended, for delivery. ⚑ **Now that the vendor is named, the temptation is concrete rather than hypothetical**: Twilio sells Verify and its documentation routes this exact use case towards it. Programmable Messaging is the product; a pull request that reaches for Verify because it is fewer lines is reversing this decision, not shortening it.
- **A missing destination is an authoring error, not a runtime one.** The alternative fails at the worst possible moment: the signer is waiting, the sender is absent, and the only recovery is sender-side.
- **Metering rides the transaction, not the delivery callback.** A provider acknowledgement is not the billable event; the state change is. This is what makes a rolled-back issuance free.
- **The phone is stored in the clear, not enciphered** — the decision, its four grounds and the counter-argument that would reopen it are §7 D5.

## 5. Acceptance bars

1. **The column round-trips E.164, and the raw database value is asserted directly.** Read the raw column, not the entity getter — an accessor-level assertion proves nothing about what is at rest, and that is as true of a normalization bar as it was of the encryption bar this replaces. ⚑ **Assert the plaintext deliberately**, so the day the carrier of [`BL-171`](../BACKLOG.md) lands, this bar **fails** and forces someone to look at it. A bar that would pass either way would let the column be enciphered, or stop being, without anybody noticing.
2. **The metering *call* is correct, which is all this slice can assert.** A rolled-back issuance leaves the recording double with no entry, and a duplicate challenge id is refused rather than recorded twice. ⚠ Stated as a limit rather than a bar: with the meter null and no usage table, this proves the **caller** and not the **charge** ([`BL-166`](../BACKLOG.md)). Sabotage it by making the double record unconditionally and confirm the rollback case reddens — otherwise it is asserting nothing at all.
3. **A destination-less delivered method is refused at authoring**, not at issuance — **for every method, not just SMS**. Assert `OTP_EMAIL` against an address-less recipient too, which is the half that closes [`BL-162`](../BACKLOG.md); then drop one method from whatever declares its required destination and confirm the test fails **naming it**, so the guard is a predicate over the catalog rather than a list of today's members.
4. **A hard bounce reaches the correction path** and returns the recipient to a correctable state.
5. **No fallback occurs.** A failed SMS delivery does not produce an email — asserted, because the friendly behaviour is the wrong one here and someone will eventually add it as a fix.
6. **A landline is refused at authoring.** `+34911234567` is a valid Spanish number and cannot receive SMS; the value object rejects it before a sender can declare `OTP_SMS` against it. This is the bar that justifies the dependency — a length-and-plus regex passes this input, and the failure it buys is a charged message that never arrives, discovered while the signer waits.
7. **A declared `OTP_SMS` reaches SMS and a declared `OTP_EMAIL` reaches email, and neither consults the selector.** Assert the occasion's target channel by driving the **real issuance path** end to end, not by hand-building a request — a hand-built one proves the service and skips the two hops (`ExecutedAuthMethod` → the request field) where the medium can be dropped. Then ask `DefaultChannelSelector` for `AUTH_OTP` directly and confirm it **throws**: that assertion is what keeps [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 enforced once [TASK-031](TASK-031-channel-selection-beyond-email.md) widens the selector's signature, and it is the bar that reddens if a later reader "restores" the `EMAIL` arm. ⚑ Sabotage it the ordinary way (authoring rule 4): make `deliveryMedium()` return the email medium for `OTP_SMS` and confirm the first half fails **naming the channel it got**.
8. **A phone destination is masked to its last two digits, and an unrecognised one still returns `null`.** Assert the rendered value on the **descriptor route**, not on the masker alone — a unit test on `MaskedDestination` proves the string and skips whether the route actually reaches it. ⛔ Then assert the negative half in the same test class: a value that is neither an email nor an E.164 number returns `null`, so the branch that was added did not turn into a general masker. ⚑ That negative is the one worth sabotaging (authoring rule 4): widen the new branch to match anything, and confirm the unrecognised case reddens.

`make qa` green: PHPStan L9, Deptrac 0, lint, full suite — from the worktree lane (`make wt-backend src=$(pwd)` in `f5sign-infra`), not from the main-checkout targets. Delivery is exercised against a real provider sandbox — a mocked channel cannot retire the estimate risk this slice exists to hold — and §6 states exactly which half of that a free sandbox reaches.

## 6. What the free sandbox retires here, and what it does not

[TASK-030](TASK-030-sms-delivery-channel.md) §6 is the home of the provider's test surface: the **test credentials** (a second Account SID and Auth Token that validate a request against the real endpoint, send nothing and charge nothing), the **magic numbers** that force each error code deterministically, the **Virtual Phone** (a simulated handset in the Console, no regulatory onboarding), and the **trial account** (100 free SMS units, 30 days, verified numbers only). Read it there rather than restating it; what belongs *here* is which of this slice's bars each surface can and cannot close.

**It closes bar 4 outright, and better than a real send would.** *A hard bounce reaches the correction path* needs a hard bounce on demand, which is what a magic number is: `+15005550004` returns the opt-out/blocked code and `+15005550001` an invalid number, so the [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) route can be driven repeatedly, offline of any real handset, with no carrier in the loop. Asserting this against a live number means finding a number that is genuinely undeliverable and hoping it stays that way.

**It closes bar 5 the same way.** *No fallback occurs* — a refused SMS must not become an email — is asserted by forcing a permanent refusal and observing that no `EMAIL` delivery is born. Costless, deterministic, and it is the bar most likely to be broken later by someone being helpful.

⛔ **It cannot close bar 2, and the reason is the one worth writing down: the sandbox never charges, so it cannot tell a correct meter from a missing one.** *A rolled-back issuance leaves no usage row, and a duplicate challenge id is rejected rather than charged twice* is a property of **our** usage table and its idempotency constraint, not of Twilio's response — the provider's acceptance is not the billable event (§4). Assert it against the database, in the transaction, exactly as if no provider existed. A green sandbox run says nothing about it in either direction.

⚠ **And it does not close the Delivery bar's *real handset*.** Test credentials never connect to a phone; the Virtual Phone is a screen; only the trial account puts a message on a device, prefixed with *"Sent from your Twilio trial account"* — which itself eats into the segment budget and must not be read as our copy overflowing. That is **one manual run by a human before this is called done**, and no automated bar substitutes for it. What it is actually checking is the half a validator cannot see: that a Spanish signer receives a legible code from a sender they recognise, in one segment.

## 7. Decisions taken on 2026-08-19, and one on 2026-08-20

Four questions that made this record unexecutable, and what each one moved. Recorded here rather than folded silently into the sections above, because two of them **reverse a position this task had already written down**.

- **D1 — The billing persistence is deferred, not built here.** §2 previously said *"it is in scope"* and argued its own case: a metering bar asserted against a double proves the caller, not the charge. That reasoning still stands and is **accepted knowingly** — the slice ships with the null meter, the bars assert the call, and [`BL-166`](../BACKLOG.md) carries the table, its RLS contract, its migration, its append-only discipline and its idempotency constraint. ⚠ The cost is that from [TASK-030](TASK-030-sms-delivery-channel.md) onward money is spent and nothing counts it.
- **D2 — The phone is a value object over `libphonenumber-lite`, normalized to E.164 before encryption.** The deciding argument is Spain-specific rather than general: mobile and fixed line are decidable from a Spanish number, so a landline is refusable at authoring instead of being charged and rejected as `21614` while a signer waits. ⚑ Chosen over copying a sibling because **the siblings disagree**: `Foundation/ValueObject/Email` exists with **no production caller** while `Recipient::$email` is a plain `?string`, so "follow the neighbour" answers this two different ways (`CLAUDE.md` authoring rule 3).
- **D3 — The signature-level projection leaves scope, and this task no longer closes [`BL-117`](../BACKLOG.md).** It needed two things that do not exist — a cross-BC seam into Signature Execution, and the strength ordering [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.1 deliberately declined to invent. See §3 for the `SignatureLevel` name collision that makes the wrong implementation the easy one.
- **D4 — The authoring guard is per method, so it closes [`BL-162`](../BACKLOG.md) rather than half of it.** Building it as *"requires a phone"* would need rewriting the day a third destination appears, and would leave the email case — which can bite in production **today** — open.

- ⛔ **D5 — the phone is NOT enciphered, and this reverses what this record was built around (user, 2026-08-20).** The argument *for* enciphering it was real and is worth keeping, because it is the reason anyone would revisit this: a **brand-new nullable column has no legacy plaintext to backfill**, and backfill is precisely what killed the previous attempt — [ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md)'s Status records that a first cut was *"built and green, then held back"* because it enciphered on write with no backfill and its read path threw on legacy plaintext. So this column is the cheapest place the carrier could ever be landed. It is still not being landed here, for four measured reasons:
  1. **The row is protected in the wrong half.** `envelope.recipient.email` is `TEXT` in the clear today and every recipient has one; few will have a phone. Enciphering the rare column beside the plaintext universal one buys little against ADR-0033's own stated failure mode — *"signer/recipient PII sitting in plaintext in an operational table, readable by anyone with DB access or a leaked backup"*.
  2. **There is a plaintext shadow one schema over, on the live path.** `notification.notification_delivery.destination` is plain `TEXT` and takes the same number on every send; [`ContactPoint`](../../src/F5Sign/Notification/Domain/ValueObject/ContactPoint.php)'s docblock says at-rest encryption there is deferred. Using the protected value writes it in the clear.
  3. **Two of the three things people assume encryption gives you are absent.** [`ConfigKeyProvider::currentVersion()`](../../src/F5Sign/Foundation/Crypto/ConfigKeyProvider.php) returns a hardcoded `1`, so there is **no key-rotation path**; and its keys are HKDF-*derived* rather than stored, so **crypto-shred is not available** — its own `Never` block says destroying the master secret would strand every tenant at once. Erasure is row deletion. What the cipher does buy is real but narrow: a leaked backup.
  4. **The production key provider does not exist.** `ConfigKeyProvider` calls itself *"dev / slice-grade"*; ADR-0032 decision 6's managed-KMS provider is deferred.
  ⚑ **What this costs, stated plainly rather than argued away**: a phone number is a stronger identifier than an email in a breach, and this task creates that data. The reversal is a judgement that a *coherent* carrier over both columns is worth more than a partial one landed early — see [`BL-171`](../BACKLOG.md), which is where that work now lives.

## 8. What already exists (reuse, do not rebuild)

Enumerated because the ceremony this rides on is complete, and the failure mode here is rebuilding it. Verify each by opening it rather than trusting this list.

- **The entire delivered-code mechanism**, from [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) and [TASK-022](TASK-022-delivered-codes-over-email.md): challenge issuance and the ensure/mint split, the peppered-hash storage, per-method TTL resolution, the cumulative attempt budget that does **not** reset across a re-send, the two-tier lockout, the re-send route with its cooldown, and the three-key rate limiter. This slice adds a destination, not a ceremony.
- **`AuthMethod::OTP_SMS` is already in the catalog** — [`AuthMethod`](../../src/F5Sign/Envelope/Contract/Type/AuthMethod.php) carries all fourteen members as vocabulary and does not grow slice by slice.
- **Its TTL is already written and inert**: `SignerAuthPolicy::OTP_SMS_CHALLENGE_TTL_SECONDS` is 300 seconds, and the resolver that would read it is built and running for the email sibling.
- **The availability port and its adapter** — [`ConfiguredAuthMethodAvailability`](../../src/F5Sign/Envelope/Infrastructure/Auth/ConfiguredAuthMethodAvailability.php), whose shipped set is `ACCESS_CODE` and `OTP_EMAIL` today. Its test guards that set deliberately: **do not edit that constant to make a test pass.**
- **The correction path** — `CorrectRecipient`, `RecipientOutcome::DELIVERY_FAILED` and the max-3-corrections rule, landed by [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md). This slice extends it to a second field.
- **The cipher** — ADR-0033's `FieldCipher` / `KeyProvider`, realized and unit-locked, with **zero callers**. ⚠ **This slice no longer becomes the first** (§7 D5); the count stays zero and [`BL-171`](../BACKLOG.md) is what changes it.
- **The billing port** — `UsageMeterInterface` with `NullUsageMeter` behind it. The port is the seam; only the persistence is missing.
- **Everything SMS-shaped below the destination** — [TASK-030](TASK-030-sms-delivery-channel.md): the channel, the Twilio adapter, the permanent-versus-transient taxonomy, the authored copy, the slot treatment and the sandbox tier.
- ⚑ **The limiter policies are named `otp_email_*` on purpose.** `config/packages/rate_limiter.yaml` says it in a ⛔ comment: this task adds `otp_sms_*` with its **own** numbers rather than re-tuning those, because an email costs nothing and an SMS costs money on every send.

## 9. Open follow-ups (track, don't solve here)

- **The billing persistence** — [`BL-166`](../BACKLOG.md). Forced the moment anyone asks what a tenant owes, or the first time the Twilio invoice needs reconciling against our own records.
- **The signature-level projection and the strength ordering** — [`BL-117`](../BACKLOG.md) + [`BL-119`](../BACKLOG.md). Forced by whichever arrives first: a customer asserting an eIDAS tier we cannot substantiate, or `SubstituteAuthMethod`, which cannot decide an acceptable accessibility swap without the same ordering.
- **The `Vendor` collector is not an allowlist** — [`BL-167`](../BACKLOG.md). Surfaced here because this task adds a dependency and the check that looks like it would govern that does not.
- **Enciphering any personal-data column at all, this one included** (§7 D5) — [`BL-171`](../BACKLOG.md). What forces it is a retention or DPA commitment, or the first customer who asks; and when it comes it should cover `email` and `phone` together, because a carrier that protects one column of a row is the incoherence D5 declined.
- **Spend alerting and budget caps** — owned by [TASK-030](TASK-030-sms-delivery-channel.md) §8 and made more urgent by D1, since nothing counts what is spent.
- ⛔ **Promoting [ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md) from `Proposed` to `Accepted`.** ⚠ **This entry inverted on 2026-08-20 and the inversion is the point.** It read *"this task is its exercise, so the evidence lands here"*; after §7 D5 the task exercises nothing, so under lock-via-exercise the ADR **stays `Proposed`** and there is no promotion to hold or to take. ⚑ That is not free, and the earlier version of this bullet already said why: an ADR left `Proposed` stops binding (`CLAUDE.md` authoring rule 7), so the decision now sits unrealized *and* unbinding until [`BL-171`](../BACKLOG.md) is picked up. Whoever picks it up promotes it; nobody else should.

## 10. What deviated, and what is owed

Written at close, appended rather than folded into the sections above (the `§N` anchors are cited from
other documents).

### 10.1 The metering call rides the ORDERING, not the transaction

§2 asks for the usage record *"inside the same transaction as the state change that earned it"*. It is
made **immediately after the commit** instead, beside the delivery request and inside the same
`if ($minted)` branch.

⛔ **The reason is structural rather than a shortcut.**
[`IssueAuthChallengeUseCase`](../../src/F5Sign/Session/Application/UseCase/IssueAuthChallengeUseCase.php)
is deliberately **off the command bus** — a person is waiting on the answer and the write must commit
before the delivery is requested — so there is no `DbalTransactionMiddleware` transaction to enrol in.
The only in-transaction seam is `DbalSigningSessionRepository::issueAuthChallenge()`, and putting the
call there would move a Foundation billing port into Session Infrastructure and take the *which metric,
how much* decision out of the Application layer, against
[ADR-0010](../adr/ADR-0010-command-bus-middleware-spine.md) rule 3.

⛑ **What the ordering still guarantees** is the property bar 2 actually asserts: the repository throws
on rollback, so a rolled-back issuance never reaches the meter and leaves no record. What it does not
guarantee is atomicity — a commit followed by a crash before that line loses the charge, which
**under-bills**. Unobservable today in either direction, because `NullUsageMeter` records nothing.
[`BL-166`](../BACKLOG.md) now carries the question for whoever builds the table.

### 10.2 `PhoneNumber` is `Contract/Type/`, and the library is not behind it

§7 D2 said the library is *"kept behind the value object"*. It is kept behind a **port** —
[`PhoneNumberParser`](../../src/F5Sign/Envelope/Application/Port/PhoneNumberParser.php), adapted by
`Envelope/Infrastructure/Phone/LibPhoneNumberParser` — and the value object holds only the **E.164
shape**.

⚑ **Two independent reasons, and the second one is the honest one.** (a) The two questions rot on
different schedules: the shape is fixed by ITU-T and can be a construction invariant, while *is this
number assigned* and *can it receive an SMS* come from vendor metadata §2 itself records as going stale.
(b) `EnvelopeContract` is granted `Kernel` + `Foundation` and **not** `Vendor`, so the value object could
not name the library even if (a) did not hold. ⚠ It would have *passed* `composer arch` — `libphonenumber\`
matches no collector, and uncovered dependencies are permitted silently ([`BL-167`](../BACKLOG.md), which
now carries this as a third dated reading: `Uncovered 15 → 36`). Passing is not being allowed, and the
placement was argued from `deptrac.yaml` by hand because the gate could not have told the difference.

The record never stated the namespace, which `spec-lint` flagged as an open decision. It is
`Envelope/Contract/Type/`, by the rule
[`CompletionDriver`](../../src/F5Sign/Envelope/Domain/ValueObject/CompletionDriver.php) states for its own
placement: a phone is **edge-settable** and **read cross-BC**, so it belongs on the published surface.

### 10.3 The medium is a typed `DeliveryMedium`, not a bare string

§2 says `OneTimeCodeRequest` carries the medium **as an opaque string**, and it does. What §2 did not
specify is the type on the Session side, and
[`ExecutedAuthMethod::deliveryMedium()`](../../src/F5Sign/Session/Contract/Type/ExecutedAuthMethod.php)
returns a `?DeliveryMedium` — a second Session-side mirror — rather than `?string`.

⚑ **Forced by PHPStan, and better for it.** A `match` over strings cannot be proved exhaustive, so the
destination lookup needed a `default` arm — and both candidates for it were wrong in the expensive
direction (falling through to the mailbox addresses a phone method at an address; falling through to
`null` blames the recipient for a classification bug). The enum removes the arm entirely. The string
crossing to Notification is `$medium->value`, unchanged.

### 10.4 A correction cannot clear a contact

§2 says the correction *"extends to patch the phone under the same max-3-corrections rule"*. With two
fields and *at least one* required, an **absent** field had to mean something, and it means **leave it
alone** rather than **clear it**.

⛔ The erasing reading would silently remove the address of an `OTP_EMAIL` recipient whose sender only
meant to fix their phone, stranding them with no error anywhere. The cost is that no contact can be
cleared through this endpoint, which loses nothing that existed — `email` was previously required — and
is right on its own terms: making a recipient unreachable is the opposite of what a recovery is for.

⚑ **This forced a guard §2 did not name.** A correction cannot *remove* a destination, but it can
**replace a mobile with a landline** while `OTP_SMS` is declared — reopening [`BL-162`](../BACKLOG.md)
through the other door, with every other guard green. `CorrectRecipientUseCase` therefore runs the same
per-method guard over the **post-write** contact pair, before the mutation, so a refused correction
spends none of the three.

### 10.5 The masked phone discloses at most two leading digits, not "the country code"

§2 specifies *"the last two digits over an intact country code"*. The trailing half is exact. The leading
half is **at most two digits**, which is the whole country code for a 1- or 2-digit zone and a **prefix**
of it for a 3-digit one.

⛔ **Identifying the country code needs the numbering plan, and that library may not be on the display
path**: `SessionApplication` is granted no `Vendor`, and metadata that goes stale would render a signer's
own number unrecognisably rather than refuse a bad one at authoring. A greedy regex is not a substitute —
`+34600…` would split as `+346`, and that `6` is the first digit of the **national** number. The ceiling
is chosen so a disclosed digit can never be a subscriber's.

## 11. Open follow-ups (track, don't solve here)

- ⛔ **The Delivery bar's *real handset*, unmet** — and it is the bar the record insists cannot be
  retired by a sandbox (§6). Forced by the first Twilio account, which is the same blocker as
  [`BL-169`](../BACKLOG.md). ⚠ Until a human has watched a Spanish signer receive a legible code from a
  sender they recognise, in one segment, this slice is **not** done in the sense §6 means.
- ✅ **Whether the phone joins the sender-facing envelope response** — [`BL-172`](../BACKLOG.md),
  **Resolved 2026-08-20**: published whole, like `email`. ⚑ The reasoning is worth keeping because it is
  the same one §7 D5 used: this route already publishes the address in the clear, so masking the phone
  beside it protects nothing and buys an asymmetry. ⛔ **The signer's side did not change** — route 3
  still masks — and the two projections must not be harmonized.
- **The billing persistence, and now the atomicity question with it** — [`BL-166`](../BACKLOG.md), plus
  §10.1.
- **Enciphering any personal-data column, this one included** — [`BL-171`](../BACKLOG.md), unchanged by
  this slice except that the set is one column larger.
- **The `Vendor` collector is not an allowlist** — [`BL-167`](../BACKLOG.md), which this slice moved from
  a prediction to a measurement (`Uncovered 15 → 36`).
- ⚠ **The `otp_sms_*` ceilings are estimates and nothing has measured them.** No SMS has ever left this
  system, so nobody has seen what a real signer's re-send behaviour looks like on a handset. They are set
  where being wrong is cheap — too tight refuses a send, too loose spends money. Revisit against real
  traffic rather than against a complaint.
- ⚠ **The limiter is still not asserted at the acceptance tier**, and the SMS trio inherits that gap
  whole. `DeliveredCodeCeremonyHttpTest`'s docblock carries the measurement: the test-environment cache
  pool is tagged `kernel.reset`, so the counters are emptied between requests. Closing it is a
  configuration decision, not a test's to take.
- ⛔ **A phone-only recipient is authorable and then never invited** — [`BL-173`](../BACKLOG.md), found
  while closing this record. `NotifyActivatedStepRecipientsUseCase` skips a recipient with no email with
  a bare `continue`, which was unreachable before this slice and is reachable now: nothing stops a sender
  supplying a phone, declaring `OTP_SMS`, and omitting the address. ⚠ **This task's own guard does not
  catch it and should not** — it asks *can this recipient receive the method they declared*, and the
  answer is a truthful yes. The missing question is *can they be reached by the invitation at all*, which
  no guard asks. Forced by the first sender who tries it.
- **Spend alerting and budget caps** — owned by [TASK-030](TASK-030-sms-delivery-channel.md) §8, and more
  urgent now than when that record was written: this is the slice that gives the paid channel a caller.
