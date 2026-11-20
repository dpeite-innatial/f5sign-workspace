# TASK-030 — The SMS delivery channel: the first paid transport behind the notification port

<!-- OFFREPO: §6 states facts about Twilio's REST API and its free test surface — the test-credential
endpoints, the magic phone numbers and the error codes they return, the segment arithmetic, and what Link
Shortening requires. They were read from Twilio's public documentation on 2026-08-19 and every one of them
is restated inline here, so this record stays actionable with only this repository open. §5 also states
that `f5sign-infra` runs no SMS sink container (the analogue of Mailpit); that repo is not reachable under
agent-only backend access, and nothing here depends on reading it. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/sms-delivery-channel`** (`79b00bb`), merged into local `develop` (`5d5f439`) 2026-08-20 — **not pushed at the time of writing**. Green under the **main-checkout infra Makefile against the live stack** (this branch was developed in the main checkout, not a worktree, so `make lint` / `make phpstan` / `make composer cmd=arch` / `make test` validated this tree): lint `0 of 959` · deptrac `Violations 0` / `Uncovered 15` (unmoved — the BL-167 `Lcobucci\JWT` set) / `Allowed 4898 → 4973` · PHPStan L9 `[OK] No errors` · `OK (2128 tests, 10346 assertions)` · Infection **Covered Code MSI 86.75%**, 7.75pp over the floor and level with the repo's 2026-08-19 reading. ⛔ **Two bars are NOT met and are not claimed.** §6's sandbox tier is built and **has never been executed** — no Twilio account exists — so the hermetic tier's canned bodies remain *derived from documentation, not captured*, which is the one thing §6 wired the sandbox to prevent; and the **Delivery bar's "reach a handset" is unmet** for the same reason plus the processor agreement. ⚠ The channel has **no production caller**: no phone column exists. `SMS_DSN` was unbound in production and **`f5sign-infra` wired it on 2026-08-20** (`f13aafd` on that repo's `master`, unpushed at the time of writing) — ⚑ that audit found **seven** required variables missing from the production render, not one, `MAILER_DSN` among them, so **production was already returning 500 on every request before this task existed**; the failure is a DI-container compile on the *first request*, since the image bakes no cache and runs no warmup. See §9. ⚑ **§5's open design decisions were answered on 2026-08-19** — sender identity, account scope, the link in the invitation, the over-budget send, the duplicate window, the sandbox tier, how much context each message carries, and the provider reference. **The copy was authored on 2026-08-19** and every string is measured (§3). What is still open is the administrative track in the row below, and one decision inside it: **the exact alphanumeric string to register**, which §5 promoted from cosmetic to load-bearing. |
| **Type** | **Enabling** — it builds a transport, not a feature. Extracted from [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) on 2026-08-19 for the reason [TASK-022](TASK-022-delivered-codes-over-email.md) states about itself in reverse: that slice was cheap *because* `EmailNotificationChannel` already existed, and the SMS slice was expensive because it had to build the channel and the ceremony's destination in one go. An SMS is a way of reaching a person, not a way of authenticating one — the OTP is one purpose riding it, and the invitation and the completion notice are two more. |
| **Why** | Every real channel beyond `EMAIL` is named as deferred in [`docs/ddd/notification-domain-model.md`](../ddd/notification-domain-model.md) § Deferred surface and nothing has built one, so the "adding WhatsApp is one tagged service" claim in § Channels and dispatch has never been paid for. It is also the platform's **first transport that costs money per message**, and that is a different class of adapter from a mailer: a bug that retries too eagerly is a bill rather than a log line. |
| **Builds on** | [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) (the Notification BC, the channel port, the failure contract), [ADR-0038](../adr/ADR-0038-template-archive.md) (the archive its copy is pinned into), [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) (vendor as a composition-root adapter), [TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md) (the `recipient → tenant → system` locale chain, reused unchanged). |
| **Decision record** | **No new ADR expected.** [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) already settles the shape — a channel is one self-describing tagged service — and [`DeliveryChannel`](../../src/F5Sign/Notification/Domain/ValueObject/DeliveryChannel.php)'s own docblock says `SMS` "lands as a new case here". What **would** force one: moving the transport out of the BC into `Foundation`; opening a second cross-BC dependency; or adopting delivery receipts, which changes `successThreshold()` from a constant into a provider-dependent answer and reopens § Delivery status. |
| **Provider** | **Twilio, Programmable Messaging** — decided 2026-08-17, for Spain-only traffic in the first year, and **moved to this record on 2026-08-19** because it is a property of the transport rather than of the OTP. It is the **SaaS-mode default, not a platform-wide commitment**: [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) makes the channel an adapter chosen at the composition root, so a Dedicated install brings its own vendor and being wrong costs an adapter rather than a migration. ⚠ **Two of the three things this decision drags with it have lead times measured in weeks and no engineering content, so they are the first things to start rather than the last**: the **processor agreement and data residency** (a Spanish phone number is personal data crossing to a US-headquartered vendor) and **alphanumeric sender-ID registration**, which Spain requires in advance. The third is §5's *delivers, does not verify*. |
| **Prerequisites that do not exist yet, and are calendar-bound rather than engineering-bound** | ⚠ **None of these three has been started, and two of them gate a real send rather than the build.** (1) **A Twilio account** — nobody owns one; the free tier is enough for everything in §6 (a) and (b), so this gates the build by days at most. (2) **Alphanumeric sender-ID registration in Spain** — required in advance, weeks of calendar, gates production and nothing else; start it first. (3) **The processor agreement and data-residency position** — a Spanish phone number is personal data crossing to a US-headquartered vendor; it gates sending to a real person, so it gates §6 (c) and the Delivery bar, **not** the sandbox. ⚑ The build and the paperwork run in parallel: test credentials need only (1). |
| **Delivery bar** | A `RECIPIENT_INVITATION` and an `AUTH_OTP` message, authored in `es` and `en`, reach a handset (or the Virtual Phone of §6) through Twilio; a provider refusal that is genuinely permanent commits `FAILED` while a timeout retries; and `composer test` proves both without sending anything or spending anything. |
| **Siblings — do not scope independently** | **Two records stand between this transport and a message a recipient reads, and they close different halves.** [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) gives it a **destination** — the phone column, without which no `ContactPoint` of SMS shape can be built by any live path — and with it the one-time code becomes routable, because [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 lets an auth method name its own channel and bypass the selector. [TASK-031](TASK-031-channel-selection-beyond-email.md) gives it **everything else**: until the selector has inputs, the invitation and the completion notice still go to a mailbox and nowhere else. ⛔ Shipping this alone buys a tested transport and zero delivered messages — see §5's first decision, where that cost is argued rather than hidden. Sequence this one first anyway; it is the cheap half and it is the half carrying the vendor lead times. |

---

## 1. Why this task exists

[TASK-022](TASK-022-delivered-codes-over-email.md) got the whole delivered-code ceremony for the price of the ceremony, and said why in one sentence: `EmailNotificationChannel` already existed. [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) inherited the opposite deal — it had to build a paid third-party transport, a new class of personal data on the Envelope aggregate, the first caller of a cipher nothing had ever called, and a billing persistence, in one slice, and its own §2 already flags that it is "quietly larger than it reads".

**The channel is the separable half, and it is separable because it is not about authentication at all.** An SMS is a way of reaching a person. The one-time code is one purpose riding it; the invitation and the completion notice are two more, both of which exist today and neither of which has any way to reach a phone. Splitting them lets the expensive, slow-moving, vendor-shaped work — a contract, a sender-ID registration, a processor agreement, an error taxonomy, a cost model measured in message segments — proceed without waiting on a PII migration, and leaves [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) holding only what is genuinely OTP-shaped.

**It is also the first transport that spends money on every call**, and that changes what the adapter owes. A mailer that retries a transient failure five times costs nothing; an SMS adapter that does the same bills five times. So the failure taxonomy of §3 is not documentation — it is the spend control.

## 2. What already exists (reuse, do not rebuild)

- **The port is a whole pipeline, and it is the only seam a channel needs.** [`NotificationChannel`](../../src/F5Sign/Notification/Domain/Port/NotificationChannel.php) declares `channel()` · `requiredParts()` · `authored()` · `render()` · `send()` in one interface, deliberately: whatever declares the parts is what reads them. Services are collected by [`NotificationChannelRegistry`](../../src/F5Sign/Notification/Application/Service/NotificationChannelRegistry.php) from the `notification.channel` tagged iterator, applied by `_instanceof` so the Domain port carries no framework attribute. It fails loud on an unregistered channel and on two services claiming the same one. **Adding a channel is one tagged service and no routing change.**
- **The failure contract already distinguishes the two cases this adapter must classify.** A channel *returns* a [`TransmissionOutcome`](../../src/F5Sign/Notification/Domain/ValueObject/TransmissionOutcome.php) when it knows where it stands — accepted, or permanently refused — and *throws* when it does not. A throw rolls the delivery back to `PENDING` and the retry ladder runs; a returned rejection commits terminal `FAILED` and stops the retries dead. The port's docblock states the tie-breaker as **when in doubt, throw**. [`EmailNotificationChannel::isPermanentReply()`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailNotificationChannel.php) is the worked example over SMTP 5xx, and it is the shape to mirror — including its comment about *why* an unparseable code counts as "not permanent".
- **[`DeliveryChannel`](../../src/F5Sign/Notification/Domain/ValueObject/DeliveryChannel.php) has three members' worth of behaviour to extend**, two of them exhaustive `match` expressions that will not compile-by-omission: `successThreshold()` and `requiresContact()`. `templateKey()` is already channel-generic and needs nothing.
- **[`ContactPoint`](../../src/F5Sign/Notification/Domain/ValueObject/ContactPoint.php) is medium-agnostic on purpose** — an opaque non-empty string the channel's own adapter interprets, carried per-`Delivery` rather than on the occasion root, precisely so one type serves an email address and a phone number.
- **The templating substrate is done and is not Twig.** [`Template`](../../src/F5Sign/Foundation/Templating/Template.php) is a map of named parts and [`RenderedTemplate`](../../src/F5Sign/Foundation/Templating/RenderedTemplate.php)'s docblock already names the SMS shape — "an SMS carries a lone `body`". Interpolation is `NativeTemplateEngine`, the sole implementation of `TemplateEngine::interpolate()`. ⛔ **Twig is not available to this channel and that is a decision, not an omission** ([ADR-0052](../adr/ADR-0052-twig-layout-composition.md)): it composes the `EMAIL` channel's HTML chrome only, `default_path` points at `templates/notification/`, and an SMS body is plain text with nothing to compose.
- **The locale chain is built and live** — `recipient → tenant → system`, resolved in one place ([`NotificationTemplates`](../../src/F5Sign/Notification/Application/Service/NotificationTemplates.php)), with the system floor committed as `es` ([TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md) §4 D8). A new channel authors copy in the two authored locales and inherits the resolution whole.
- **The three purposes that exist today** are `RECIPIENT_INVITATION`, `ENVELOPE_COMPLETED` and `AUTH_OTP` — enumerate from [`NotificationPurpose`](../../src/F5Sign/Notification/Domain/ValueObject/NotificationPurpose.php) rather than from this line, which is a hand-maintained copy.
- **Retryable HTTP is in Foundation and its docblock already names this caller.** [`RetryableHttpClientTrait`](../../src/F5Sign/Foundation/Http/RetryableHttpClientTrait.php) says it exists for "any future HTTP adapter (TSA, SMS, email, webhooks)".
- **`MAILER_DSN` is the precedent for how a channel is bound to its transport** — env, not code ([ADR-0013](../adr/ADR-0013-deployment-mode-duality.md)): `framework.mailer.dsn: '%env(MAILER_DSN)%'`, absent from `.env`, present in `.env.dev` and `.env.test`, injected in production. §5 follows it exactly rather than inventing a second pattern.

**What does not exist, and this task does not add:** a phone number anywhere in the schema ([`Recipient`](../../src/F5Sign/Envelope/Domain/Entity/Recipient.php) carries `email` and `fullName`), `symfony/notifier` in `composer.json`, any usage table behind [`UsageMeterInterface`](../../src/F5Sign/Foundation/Billing/UsageMeterInterface.php) — whose only implementation, [`NullUsageMeter`](../../src/F5Sign/Foundation/Billing/NullUsageMeter.php), records nothing.

## 3. What gets built

**The enum case.** `DeliveryChannel::SMS`, with `successThreshold()` returning `SENT` — Twilio's create-message response is an acceptance, never a delivery, and receipts are out of scope — and `requiresContact()` returning `true`.

**The channel.** `SmsNotificationChannel` in `Notification/Infrastructure/Channel/`, tagged like its siblings, `requiredParts()` returning `['body']` and nothing else. It authors copy for **every** purpose in the enum (§5), renders through `NativeTemplateEngine`, and transmits through the transport below.

**The transport.** A small vendor-facing seam the channel depends on, so the Twilio specifics — endpoint, auth, parameter names, error codes — sit in one class that [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) allows a Dedicated install to replace. The Twilio implementation posts to `https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json` with HTTP basic auth (`AccountSid`:`AuthToken`) and form parameters `From`, `To`, `Body`, over `symfony/http-client` plus [`RetryableHttpClientTrait`](../../src/F5Sign/Foundation/Http/RetryableHttpClientTrait.php).

**The failure taxonomy — the part that is a spend control rather than a docblock.** Twilio answers a refusal with an HTTP status and a JSON body carrying a numeric `code`. The permanent set is what may be *returned* as `rejected`; everything else, including every code not listed, throws:

| Twilio `code` | Means | Verdict |
|---|---|---|
| `21211` | `To` is not a valid phone number | **permanent** — `rejected` |
| `21610` | the recipient has opted out / is blocked for this account | **permanent** — `rejected` |
| `21614` | `To` cannot receive SMS (a landline) | **permanent** — `rejected` |
| `21408` | this account lacks permission to send to that region | throw — a **configuration** fault, not a fact about the recipient |
| `21606`, `21212` | the `From` number is invalid or not ours | throw — same reason |
| `21611` | this number's queue is full | throw — transient by definition |
| anything else, any 5xx, any timeout | unknown | throw |

⚑ **The split down the middle of that table is deliberate and is the one thing to get right.** `21408` and `21606` look permanent — retrying will indeed never help — but recording `FAILED` on them tells the *sender* that the *recipient* is unreachable, and routes a misconfigured account into [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md)'s recipient-correction path, where a human will patch a perfectly good phone number and watch it fail again. A configuration fault must be loud and ours, not quiet and theirs.

**Configuration.** `SMS_DSN`, **one per installation** following `MAILER_DSN` exactly — the sender identity travels **inside** it (`?from=`), which is what makes §5's per-environment sender a config difference and not a code branch: **absent from `.env`** (repo rule 4 pattern A — it carries a credential and `.env` ships inside the production image), `null://null` in `.env.test` and `.env.dev`, injected in production by `f5sign-infra`. The scheme selects the transport, so `null://` is an inert one and a Dedicated install with no SMS vendor sets it explicitly rather than inheriting a silent default. It is named in `.env`'s load-order header, in prose, with the rest of the absent set.

**Copy — authored 2026-08-19, and every string below is measured rather than estimated.** One body per purpose per authored locale, in the catalog shape the EMAIL channel uses, plus this channel's sibling of `every_purpose_is_authored_in_the_fallback_locale`. Register and vocabulary follow the EMAIL copy rather than inventing a second voice: **usted**, and *código* for the one-time code.

| Purpose | Locale | Body | Units | Segments |
|---|---|---|---|---|
| `RECIPIENT_INVITATION` | `es` | `Tiene un documento pendiente de firma: {{link}}` | 108 GSM-7 | 1 |
| `RECIPIENT_INVITATION` | `en` | `You have a document to sign: {{link}}` | 98 GSM-7 | 1 |
| `AUTH_OTP` | `es` | `Su código para firmar es {{code}}. Caduca en 5 minutos.` | 53 UCS-2 | 1 |
| `AUTH_OTP` | `en` | `Your code to sign is {{code}}. It expires in 5 minutes.` | 55 GSM-7 | 1 |
| `ENVELOPE_COMPLETED` | `es` | `"{{envelope_title}}" ya tiene todas las firmas y queda sellado. No tiene que hacer nada.` | 93 GSM-7 | 1 |
| `ENVELOPE_COMPLETED` | `en` | `"{{envelope_title}}" has been signed by everyone and sealed. Nothing more is needed.` | 89 GSM-7 | 1 |

Three properties of these strings are load-bearing rather than stylistic, and each is argued in §5: **the invitation carries no customer-supplied slot at all**; the Spanish keeps its accents because it is authored text under our control, and is phrased to stay inside the UCS-2 budget rather than transliterated; and the completed notice is the one purpose that does interpolate customer data, which is what keeps the slot treatment below from being code with no caller.

⚠ **`ENVELOPE_COMPLETED`'s Spanish is deliberately `queda sellado` and not `está sellado`.** With a customer title in the body the whole message is one accent away from UCS-2, and `está` would spend that budget on a word that has a perfectly correct accent-free alternative. This is a real constraint on authoring here, not a typo to be helpfully corrected.

**The slot treatment — applied to customer-supplied values only, before composition.** A value that arrives from the customer (`envelope_title` today) is transliterated into GSM-7 (`préstamo` → `prestamo`) and truncated with `...` to whatever budget the surrounding authored string leaves — computed as *what is left*, never a fixed number, because Spanish runs longer than English. ⛔ **This is not the body truncation §5 forbids, and the distinction is the whole point:** the link and our own words are never touched, so nothing can silently lose the end of a URL. `…` is itself outside GSM-7, which is why the marker is three periods.

**The provider's own reference, persisted.** `notification.notification_delivery` gains a **nullable** `provider_reference` column and its migration. Before this task that table carried `id`, `notification_id`, `tenant_id`, `channel`, `destination`, `template_id`, `status` and `failure_reason` — nothing that pointed back at the provider — so *"did that message actually go out?"* can be answered only with *"our row says `SENT`"*, which by `successThreshold()`'s own definition means no more than *the provider accepted it*. The column is what lets a delivery be reconciled against an invoice or a support case, and it is the key a future status callback would arrive holding. Nullable because `LOG` and `EMAIL` have nothing to put in it, and because it is cheap now and unfillable later: every row written before it exists stays blank forever.

**The over-budget send.** A rendered body that exceeds one segment is **transmitted anyway and logged at `error`** (§5). The log line *is* the control, so it names the delivery, the channel, the segment count and the encoding — enough to find which tenant's data caused it without putting the body itself in a log.

**Docs.** The channel table in [`docs/ddd/notification-domain-model.md`](../ddd/notification-domain-model.md) § Channels and dispatch gains its third row, and § Deferred surface's *"Real channels beyond EMAIL"* bullet narrows to WhatsApp / voice / in-app / push.

## 4. Scope

**In scope:** everything in §3, plus the sandbox test tier of §6 and the segment guard of §5.

**Out of scope:**

- **The recipient phone column, and therefore any production route to this channel** — [TASK-023](TASK-023-sms-codes-and-recipient-phone.md). See §5.
- **`OTP_SMS` in the availability adapter.** A method is available when a deployment can *execute* it, and executing it needs a destination this task does not add. It stays closed here, which is also what stops this channel being reachable in production before its destination exists.
- **Usage metering and the billing persistence** — the **call site** is [TASK-023](TASK-023-sms-codes-and-recipient-phone.md), where the idempotency key (the challenge id) exists; the **persistence** is [`BL-166`](../BACKLOG.md). ⚑ **That split is not pedantry and this line elided it until 2026-08-20**: TASK-023 §7 D1 deferred the table deliberately, so TASK-023 landing proves the *caller* and not the *charge* — and the charge is the half that reaches an invoice. Anyone reading "metering → TASK-023" and seeing that record go green would conclude the spend is counted. It is not. ⚠ **This is the one out-of-scope line with a real consequence rather than a boundary**: this task can send a paid message and nothing counts it. The mitigations are that nothing routes here in production until TASK-023 lands, and that §6's sandbox spends nothing — but if this channel is ever pointed at live credentials before TASK-023, it bills silently.
- **Delivery receipts and status callbacks.** They would change `successThreshold()` from a constant into a provider-dependent answer, which is § Delivery status reopened and an ADR. Twilio's test credentials do not fire them anyway (§6).
- **Inbound SMS, STOP/opt-out handling and the Advanced Opt-Out product.** Twilio applies carrier-level opt-out itself and surfaces the result as `21610`, which this task classifies; building our own consent ledger is a separate decision with a legal owner.
- **Messaging Services, alphanumeric sender IDs in code, and Link Shortening** — see §5.
- **WhatsApp and voice.** Both are additional channels behind this same port and neither adds a decision once this one is built.
- **Spend alerting and budget caps.** Nobody is watching the bill. Worth an owner before this reaches a real tenant, and it is a follow-up rather than a boundary (§8).

## 5. Key decisions

- ⚠ **This ships a transport with no production caller, and that is the price of the split — stated here rather than discovered in review.** With no phone column, no `ContactPoint` of SMS shape can be built by any live path, so the channel is registered, tagged, tested and unreachable until [TASK-023](TASK-023-sms-codes-and-recipient-phone.md). `CLAUDE.md` authoring rules 4 and 5 both warn about exactly this: Infection cannot see code with no callers, and an empty exempted set reads as an all-clear. ⚑ **And a destination is not the same as a route**: even after [TASK-023](TASK-023-sms-codes-and-recipient-phone.md), only `AUTH_OTP` reaches this channel, because the auth method names its own channel while every other purpose still resolves through a selector that returns `[EMAIL]` unconditionally. The invitation and the completion notice wait on [TASK-031](TASK-031-channel-selection-beyond-email.md). Three things make the gap acceptable and none of them is "it will be fine": `OTP_SMS` stays **unavailable** in the availability adapter, so nothing can declare it; `SMS_DSN` is **inert by default**, so a deployment that has not been configured sends nothing rather than something; and §6's sandbox tier exercises the adapter end-to-end against the real API, which is a stronger guard than the mocked one a caller-less class would otherwise get. ⛔ **Do not treat the green suite as evidence that the channel works in production** — it is evidence that it works against Twilio's validator.
- **The REST API over `symfony/http-client`, not `symfony/twilio-notifier` and not `twilio/sdk`, and the reason is §3's table.** Measured 2026-08-19 against the published sources: the Symfony bridge's transport throws `TransportException('Unable to send the SMS: '.$error['message'])` for any status other than 201, so the numeric `code` the taxonomy is built on survives only as prose in a message string (it is recoverable from the attached response, but only by re-reading and re-parsing it). It also pulls in the whole `symfony/notifier` component, which is a second channel-and-transport seam sitting beside the one [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) already gives us. `twilio/sdk` does surface the code (`RestException::getCode()`) but brings its own HTTP transport, which routes around `RetryableHttpClientTrait` and the retry policy this repo already has. The REST call is a handful of lines against a client that is already a direct dependency.
- **The provider delivers; it does not verify.** Inherited from [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) §4 and restated here because the adapter is now *here*, which is where the temptation lives. Twilio sells **Verify** — generation, delivery, verification and anti-fraud in one call — and its documentation routes this exact use case towards it. It is rejected for the verification half because it relocates the `OtpVerified` fact, which is precisely the evidence the audit trail exists to sustain, into a third party's records. **Programmable Messaging is the product.** A pull request that reaches for Verify because it is fewer lines is reversing this decision, not shortening it.
- **Copy is authored for every purpose; routing is not changed.** The channel authors `RECIPIENT_INVITATION`, `ENVELOPE_COMPLETED` and `AUTH_OTP` even though only the third can ever reach it once [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) lands — [`DefaultChannelSelector`](../../src/F5Sign/Notification/Domain/Service/DefaultChannelSelector.php) still maps every purpose to `EMAIL`, and [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.7 makes the OTP's channel a property of the declared auth method rather than something the selector picks. Authoring the full set costs three short strings per locale and keeps the property **closed over the enum** rather than over today's members, which is `CLAUDE.md` authoring rule 5: the alternative is a channel that renders whatever it was given and explodes on the first purpose someone routes to it later — and [TASK-031](TASK-031-channel-selection-beyond-email.md) is the task that will route them, so this is a dated cheque rather than a hypothetical.
- ⛔ **Link Shortening is rejected, and the reasons are not about the fee.** Twilio does **not** shorten links automatically — it is an opt-in Messaging Services feature, part of Engagement Suite and priced separately, and it requires a domain we own. Three things disqualify it here, in order: it stores the long↔short association for **90 days** and then redirects expired links to a fallback URL, which would silently break a signing link whose token can outlive that window; it exists to provide **click tracking**, so the vendor would record that a signer opened their signing link — an evidence-adjacent event we do not want in a processor's logs; and it only works through a `MessagingServiceSid`, which **test credentials refuse** (§6), so it could never be exercised in the free sandbox. **We do not need a shortener of our own either**, and the arithmetic is the argument: the opaque signing token is `f5s_st_` + a 30-character base62 body + a 6-character control trailer = **43 characters**, so a link over a short production host lands near 68 — which fits a single GSM-7 segment with room for copy. The link is already short by construction; a shortener would buy segments we are not spending.
- ⚠ **The unit of cost is the segment, and it bites in exactly one message — measured 2026-08-19, not estimated.** Twilio bills **per segment**: a body over **160 GSM-7 characters** (or **70 UCS-2**) is split and charged as two. The GSM-7 alphabet carries `ñ`, `Ñ`, `¿`, `¡`, `é`, `à`, `ü` but **not `á`, `í`, `ó`, `ú`**, so one accented word drops the whole message to UCS-2 and the budget from 160 to 70. Over a signing link of **69 characters** (`https://firma.f5sign.es/s/` + the 43-character opaque token):

  | Candidate body | Encoding | Units | Segments |
  |---|---|---|---|
  | code, no accents | GSM-7 | 49 | 1 |
  | code, with `código` | UCS-2 | 49 | **1** |
  | code naming the organization | GSM-7 | 61 | 1 |
  | invitation + link | GSM-7 | 102 | 1 |
  | invitation + organization + link | GSM-7 | 117 | 1 |
  | **the same, with `Fírmalo aquí`** | UCS-2 | 117 | **2** |
  | invitation + organization + document + link | GSM-7 | 124 | 1 |

  ⚑ **So the rule is not "accents are expensive" — it is "accents are free in the code and fatal in the invitation"**, because the link alone already consumes 69 of UCS-2's 70. Writing the rule the general way is what would get the code's copy needlessly mangled into accent-free Spanish for no saving at all.

  ⛔ **And the danger is not in the copy we write, which is exactly why a copy review cannot catch it.** The organization's name is a **variable**, interpolated at render: a customer called *Peluquería Ñuño* injects an `í` that no authored string ever contained. That is the whole argument for the decision below.

- **The sender is alphanumeric in production and a Spanish long number in development — decided 2026-08-19, and it costs no structure because the identity rides inside `SMS_DSN`.** An alphanumeric ID (`F5Sign`) is what makes a message carrying a signing link readable as ours rather than as a stranger's; a long number would arrive looking like an unknown mobile, which is the shape of the thing we are asking people not to fall for. ⚠ **Two consequences follow and neither is optional to know.** An alphanumeric sender is **one-way**: nobody can reply, so no copy may ever invite a reply, and any future inbound feature is a different sender. And **Spain requires the ID to be registered in advance** — weeks of calendar, no engineering, so it starts before the code does. The development number is there to make manual testing possible without waiting on that registration; §6 records where the divergence goes untested.
- **One Twilio account per installation, not a subaccount per tenant.** That is what SaaS mode means under [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md), and per-customer billing separation comes from **our** meter ([TASK-023](TASK-023-sms-codes-and-recipient-phone.md)) rather than from the provider's. A subaccount per tenant would turn the DSN from configuration into **data** — a per-tenant credential store, with its RLS and its encryption — which is a feature, not a parameter. A Dedicated install brings its own vendor and its own DSN, unchanged.
- **The invitation carries the signing link.** The alternative — *"you have a document to sign, check your email"* — is coherent and fails the one case that justifies the channel: the recipient who has no email. ⚠ What it costs is a live credential resting in a phone's message store and in a carrier's logs, which is [`BL-113`](../BACKLOG.md)'s shape on a new surface; it is accepted here and named in §8 rather than discovered later.
- **A rendered body over one segment is sent, and shouted about.** Refusing would be a hard spend ceiling, and it would strand a signer at a gate because of the length of their own customer's name — the failure arriving at the worst possible moment, which is the exact trade [TASK-022](TASK-022-delivered-codes-over-email.md) §2 already made when it chose fail-open for the limiter. So the send proceeds and the `error` line is the control. ⛔ **Do not quieten that log**, and do not "fix" this later by truncating: a truncated SMS silently removes the end of a link.
- **The at-least-once window is accepted, not closed.** [`TransmitDeliveryUseCase`](../../src/F5Sign/Notification/Application/UseCase/TransmitDeliveryUseCase.php) already documents it: a hand-off the transport accepted and a commit then lost is re-sent on retry, and the ladder allows five attempts. On a paid channel that is a second billed message and a signer receiving the same code twice — and **Twilio's Messages API documents no idempotency key** (checked 2026-08-19), so there is nothing provider-side to deduplicate against. It is accepted because the window requires the database to fail *after* a successful HTTP call, in a path that read the aggregate before sending; the two alternatives are worse. A pre-send marker converts at-least-once into **at-most-once**, which loses the message outright on a crash — and a lost OTP leaves a signer waiting for something that is never coming. A shorter ladder for SMS alone needs a transport of its own, which is the deferred `queue.notification.send` and its unbuilt tenant propagation. ⚑ Revisit if the invoice ever says otherwise; that is the signal, and the `provider_reference` column of §3 is what makes reading it possible.
- ⚑ **The invitation carries no customer-supplied value at all — revised 2026-08-19, and the first version of this bullet was wrong in a way only measurement caught.** It said the invitation should name **the organization asking for the signature**. Two findings retired that. (1) **The organization is not available.** [`EnvelopeContextView`](../../src/F5Sign/Envelope/Contract/View/EnvelopeContextView.php) carries `tenantId` — a UUID — and `title`, and a tenant's *name* is an Identity & Access fact; Notification reads exactly one sibling Contract today and [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) makes opening a second an **ADR-level** question (`BL-76` records what the last attempt cost). Envelope cannot reach it either — `deptrac.yaml` grants `EnvelopeApplication` no `IdentityAccessContract`. (2) **Any customer value plus the link makes two or three segments the normal case, not the exception.** Measured over the same 69-character link: an ordinary Spanish title (`Contrato de préstamo Nº4`) costs **three** segments, and a merely long one costs two. With no customer slot the invitation is a **deterministic 108 units**, so one segment is a property of the string rather than a hope about the data.

  ⚠ **What that costs, stated rather than glossed: the invitation no longer says what is being signed, so the sender identity is the only signal the recipient has.** That promotes the alphanumeric sender-ID registration from cosmetic to load-bearing — it is now the anti-fraud control, and a deployment that falls back to a numeric sender is materially weaker. The sender organization remains the better signal and is in §8, where it belongs, as work that needs a cross-BC decision first.

- **Customer-supplied slots are transliterated and budget-truncated; our own words are neither.** Without it the *"send and shout"* decision above eats itself: the `error` line would fire on nearly every Spanish invitation, and a control that always fires is noise rather than a signal. With it, one segment is deterministic and the log means *a defect*. The asymmetry is deliberate — we control our copy and can phrase it inside the budget (see `queda sellado` in §3), and we do not control a customer's document title. ⛔ **Never extend this to the composed body**: truncating there removes the end of a link.

- **The copy speaks the EMAIL channel's register and vocabulary, and states its own TTL.** *usted* and *código*, because a platform that addresses the same person formally by email and informally by SMS reads as two systems. ⚠ **`5 minutos` is a duration the copy cannot read** — the value lives in [`SignerAuthPolicy::OTP_SMS_CHALLENGE_TTL_SECONDS`](../../src/F5Sign/Foundation/Auth/SignerAuthPolicy.php) (300) and the string is a `const`, so changing one silently falsifies the other. The EMAIL copy already made this trade for its own 15 minutes, and it is repeated here for consistency rather than re-argued — but it is a rot pairing, and §8 carries it. ⚑ The two numbers differ **legitimately**: [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.8 sets the TTL per method, so a reader finding 5 here and 15 there has found the design, not a bug.

- ⚠ **The Spanish code message drops the *do not share it* advice, and it is a margin decision rather than an editorial one.** The full email-consistent phrasing (`Su código de verificación para firmar es …. No lo comparta.`) measures **85 units in UCS-2 — two segments**. Shortened it fits with 17 units of margin, and margin matters here for a reason this channel cannot see: the code's length is a fact about Signing Session's generator, which [`EmailNotificationChannel::slots()`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailNotificationChannel.php) already warns must not be assumed from here. The English is dropped too, for parity — a security warning present in one language and absent in the other reads as a bug. §8 carries how to get it back.

## 6. The provider sandbox: exercising this without sending or spending

Twilio has three testing surfaces and they cover different halves of the bar. **Only the first is free and hermetic-ish; the split matters because the temptation is to claim the third is retired by the first.**

**(a) Test credentials — validates the request, sends nothing, charges nothing.** A separate Account SID and Auth Token from the Console's *API keys & tokens* page, used against the **real** endpoint (`POST …/Accounts/{TestAccountSid}/Messages`). Twilio validates the input exactly as it does for live credentials but does not charge, does not touch account state and does not connect to a real number. Constraints, all of which this task's design already respects or must:

- Only four resources are reachable — `IncomingPhoneNumbers`, `Messages`, `Calls` and Lookup. **Anything else returns 403.**
- **`MessagingServiceSid` is not supported**, so sends must carry `From`. This is also why §5's Link Shortening rejection is not merely preferred but untestable.
- **No status callbacks fire.** Costless here, because receipts are out of scope (§4).
- They cannot be used with the Twilio CLI, and magic numbers do not work with live credentials.
- ⚠ **The `From` that passes validation is a magic *number* (`+15005550006`), so the sandbox never exercises the alphanumeric sender at all.** Combined with §5's decision to use a long number in development, that means the production sender identity is covered by **no automated test anywhere** — it is verified once, by a human, through (b) or (c). Written here because the gap is invisible from a green run.

**Magic numbers — the reason this is worth wiring rather than mocking.** They make §3's taxonomy deterministic instead of aspirational, which is a property no mocked client can give us:

| `From` | Result | `code` |
|---|---|---|
| `+15005550006` | passes all validation | — |
| `+15005550001` | invalid number | `21212` |
| `+15005550007` | not owned by the account / not SMS-capable | `21606` |
| `+15005550008` | this number's queue is full | `21611` |

| `To` | Result | `code` |
|---|---|---|
| any other valid number | validated normally, **nothing sent** | — |
| `+15005550001` | invalid number | `21211` |
| `+15005550002` | cannot route to this number | `21612` |
| `+15005550003` | no international permission for this region | `21408` |
| `+15005550004` | blocked for this account | `21610` |
| `+15005550009` | cannot receive SMS | `21614` |

**(b) The Virtual Phone — a simulated handset in the Console** at `+1 877 780 4236`, filtered per account, requiring neither A2P 10DLC registration nor toll-free verification. This is a **real send** that consumes trial units, and it is the only cheap way to see what the copy actually looks like: segmentation, the sender as displayed, and whether the accents of §5 pushed the body into UCS-2.

**(c) A trial account — 100 free SMS units, expiring after 30 days**, deliverable only to verified numbers and prefixed with *"Sent from your Twilio trial account"* — which itself consumes segment budget and must not be mistaken for our copy overflowing.

**How this maps onto the tiers.** ⛔ **A test that reaches `api.twilio.com` cannot go in the default suite**: `rg -n 'markTestSkipped' tests/` returns **nothing**, so this repo does not skip — a host that does not resolve goes **red**, not skipped, and every offline `composer test` would fail. So:

- **`Unit/` + `Application/`** use a `MockHttpClient` whose canned responses are the **JSON bodies captured from the sandbox**, not invented ones. That is the point of running (a) at all: a fake that made up the error shape would lock in our guess.
- **A sandbox tier, opt-in and outside `make qa`**, drives the real endpoint under test credentials and walks every row of the magic-number tables. It follows the `WT_REQUIRE_DSS` precedent the worktree lane already sets — announce the missing precondition and abort with the reason written out, never silently pass.
- **(b) and (c) are manual and are run once**, by a human, before this is called done. They are what the Delivery bar means by "reach a handset"; the sandbox does not retire them and no bar below claims it does.

## 7. Acceptance bars

1. **Every magic-number row produces the verdict §3's table assigns it** — the three permanent codes commit terminal `FAILED`, and every other row, plus a timeout, leaves the delivery `PENDING` for the retry ladder. Driven through the real sandbox, not a mock; the mocked tier asserts the same table against the captured bodies so an offline run still covers it.
2. **A misconfigured account does not look like an unreachable recipient.** `21408` and `21606` retry and stay loud; they do not reach [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md)'s correction path. This is the bar most likely to be assumed rather than asserted, and getting it wrong sends a human to edit a phone number that was never the problem.
3. **Every purpose is authored in the fallback locale for this channel**, asserted over `NotificationPurpose::cases()` rather than a list — then drop one authored purpose and confirm the test fails **naming it**.
4. **No authored body exceeds one segment once rendered with a realistic organization name**, asserted by computing encoding and length per locale — GSM-7 ⇒ ≤160, otherwise ⇒ ≤70. ⚑ **Sabotage it on the invitation, not on the code**: pasting `código` into the code body changes nothing (49 units fits UCS-2's 70 either way, so the test would stay green and prove nothing), while one `í` in the invitation flips it to two segments. A sabotage aimed at the wrong message is how this bar would come to read as passing while measuring nothing.
5. **An over-budget rendered body is transmitted and logged at `error`.** Drive it with an organization name long enough — or accented enough — to cross the threshold, and assert **both halves**: the message went out, and the line was written. Then delete the log call and confirm the test reddens, because a control nobody can see is not a control.
6. **The provider's reference is persisted on the delivery row** for a successful SMS, and stays `NULL` for `LOG` and `EMAIL`. Assert it against the raw column rather than the entity getter.
7. **The invitation template names no customer-supplied slot.** Asserted as a **closed set** over the slots it uses — `{link}` and nothing else — rather than as "does not contain `envelope_title`", which would admit the next customer value somebody adds. This is the bar that holds §5's determinism claim, and it is the one a well-meaning edit would break first.
8. **A hostile customer value still costs one segment.** Render the completed notice with a title that is both accented and far too long, and assert the result is transliterated, truncated with `...`, and one segment — and that the **link and the authored words came through untouched** in the invitation's equivalent case.
9. **The transmitted body carries no un-interpolated slot.** A `{{` surviving into `send()` is a message a recipient will read; the EMAIL channel gets this from its template tests and the new channel needs its own.
10. **An unconfigured deployment sends nothing rather than something.** With `SMS_DSN` at `null://null` the channel resolves, records, and transmits nothing — the same property `LOG` has, asserted rather than assumed, because it is the guard standing between this task and the unmetered spend §4 names.
11. ⚠ **What no bar covers, and will not:** that the copy is *good* Spanish; that the alphanumeric sender a carrier actually displays matches what was registered (§6 — no test anywhere reaches it); and that the duplicate window of §5 stays as rare as it is argued to be. The first two are human checks against (b) or (c) and fail silently in the direction of a recipient distrusting the message; the third is only ever observable in an invoice.

`make qa` green: PHPStan L9, Deptrac 0, lint, full suite — from the worktree lane (`make wt-backend src=$(pwd)` in `f5sign-infra`), not from the main-checkout targets.

## 8. Open follow-ups (track, don't solve here)

- **Delivery receipts.** The `DELIVERED` status is modeled and unreached; a receipt-capable channel would make `successThreshold()` provider-dependent and reopens § Delivery status. Blocked on the status-callback surface and on the processor question, and it is the honest way to close [`BL-118`](../BACKLOG.md) for SMS.
- **Spend alerting and budget caps.** The OTP limiter bounds the *rate* of one purpose; nothing bounds the bill, and after this task the platform can spend money. Needs an owner before a real tenant.
- **Opt-out as a first-class fact.** `21610` is currently a delivery failure like any other. A recipient who replied STOP is a different thing from a wrong number, and the correction path will treat them identically.
- **An SMS dev sink.** `f5sign-infra` runs Mailpit for email and has no SMS analogue, so the dev loop is the Virtual Phone or nothing. A `log://` transport scheme would give offline developers the message body without an account. ⚑ **2026-10-08:** the backend half of a sink landed instead: `SmsTransportFactory` accepts `&tls=0` in dev and test, so the `twilio://` DSN can name a local Twilio mock that speaks plain HTTP (refused towards any `*.twilio.com` host and in every other environment). `.env.dev` points `SMS_DSN` at the MessagePit sink `f5sign-infra` runs in dev.
- **The sender organization as the invitation's context.** It is the better anti-fraud signal — *who* wants the signature beats *what* is being signed — and §5 could not use it: the name is an Identity & Access fact and Notification reads one sibling Contract. Needs that cross-BC decision ([ADR-0037](../adr/ADR-0037-notification-supporting-bc.md), `BL-76`) before it is a copy change. Until then the alphanumeric sender carries the whole load.
- **The *do not share it* advice, in both locales.** Dropped for segment margin (§5). Getting it back costs one of three things: transliterating our own Spanish, accepting a second segment on every code, or a shorter phrasing nobody has found yet.
- **Copy that states a TTL it cannot read.** `5 minutos` here and `15 minutos` in the EMAIL copy are both `const` strings mirroring constants in [`SignerAuthPolicy`](../../src/F5Sign/Foundation/Auth/SignerAuthPolicy.php). Nothing pairs them, so changing a TTL silently makes the copy lie. It predates this task and this task doubles it; a backlog row is owed whether or not it is fixed here.
- **A signing link resting on a handset.** §5 accepts it to serve the recipient with no email: the credential now lives in a phone's message store and in a carrier's logs, which is [`BL-113`](../BACKLOG.md)'s shape on a surface that row was not written about. Its bounded-lifetime half is the mitigation that transfers; its at-rest half does not.
- **WhatsApp and voice**, each one more tagged service, and `OTP_VOICE` in particular is the accessibility-substitution target [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.11 excludes.
- **Routing anything but the one-time code to this channel** — [TASK-031](TASK-031-channel-selection-beyond-email.md), which is where the selector acquires the inputs that would let it choose.
- ⛔ **The sandbox tier is built and has never been executed, so the hermetic tier's fixtures are a
  reading of the documentation rather than a record of the wire** ([`BL-169`](../BACKLOG.md)). §6 wired
  the sandbox for exactly one reason — *"a fake that made up the error shape would lock in our guess"* —
  and that reason is currently unpaid. `TwilioSandboxTest` fails loud with its precondition written out
  and is excluded from the default suite by group, so nothing claims it passed; what is owed is one run
  under test credentials, and then correcting `TwilioSmsTransportTest`'s canned bodies against what
  actually came back. **It needs a Twilio account and nothing else** — no paperwork, no registration.
- ⚠ **Two gates of this repository can report on something other than the code under test, and both bit
  during this task** ([`BL-170`](../BACKLOG.md)). `make test` run while `composer infection` was
  mid-flight returned a specific, plausible red about the slice under test that was pure cross-talk
  against the shared `f5sign_test` database. Recorded because the failure blames your code and looks
  exactly like a defect.

---

## 9. Deviations & honest notes

Added at close, as the last section — nothing above it was renumbered, because `§N` anchors are cited
from other records.

### Scope

- **`src/F5Sign/Notification/Application/`** was not anticipated by §3, and the reason is worth keeping:
  adding `DeliveryChannel::SMS` forced **four exhaustive `match`es over the channel that live in
  Application code**, and a `rg` for the enum does not find them because they match on a *variable*
  rather than on `$this`. PHPStan found them, which is the design working. Their arms are split
  deliberately — see the decisions below.
- **`src/F5Sign/Foundation/Http/RetryableHttpClientTrait.php`** — docblock only. It said *"any future
  HTTP adapter (TSA, SMS, …)"*; SMS is no longer future.
- **`phpunit.dist.xml`** gains its first-ever `<groups>` element, to exclude the `sandbox` tier. Named
  because it is the one edit to that file that makes the suite report on **less** than it did.
- The documentation sweep touched eleven files outside `src/`. All of it is authoring rule 1: claims the
  new case falsified, not new prose. The largest class was **count claims** (*"both standing channels"*,
  *"the two channel adapters"*) — the `BL-165` shape — including one docblock that contradicted itself
  nineteen lines apart.

### Decisiones tomadas durante la implementación

- **The transport seam is `Infrastructure/Sms/SmsTransport`, not a Domain port** — it is vendor-facing
  with one consumer, and deptrac lets `NotificationInfrastructure` see its own Infrastructure.
- **It returns `TransmissionOutcome`** rather than a parallel outcome type: that VO's docblock already
  said `handedOff()` is where a provider handle would ride, so the shape was forecast, not invented.
- **Customer-supplied is the DEFAULT and the exempt set is the closed one** (`link`, `code`). Written
  the other way — naming `envelope_title` as the thing to shorten — the set silently exempted would have
  been *every variable anybody adds later*, and a new customer value would reach the wire untreated
  (authoring rule 5).
- **Transliteration is total**: anything unmapped becomes `?`. A partial map would let one glyph flip the
  body to UCS-2, which destroys §5's determinism claim outright — a value that is *mostly*
  transliterated buys nothing.
- **The envelope-arc use cases refuse SMS; `OneTimeCodeDeliveryService` refuses it too.** The second was
  a **correction**: it first shared an arm with EMAIL, justified by *"an authentication method supplies
  its own destination"*. That is false — the only caller sets `destination` from
  `$recipient->email` unconditionally — so a selector choosing SMS would have posted a **mailbox** to
  Twilio. ⚑ Authoring rule 2, fired on prose written in the session that was quoting the rule.
- **One POST per attempt** (`maxRetries: 0`). The transport first shipped with `2`, which nobody had
  decided, under a five-attempt Messenger ladder — up to **fifteen** POSTs for one message on a channel
  billed per message. §5 reasons about the duplicate window over *five* attempts; the default would have
  made that arithmetic wrong by 3×.
- **A 2xx carrying no `sid` throws.** Twilio always returns one, so its absence is evidence that
  something else answered — reachable in practice because the DSN accepts a host override for egress
  proxies. The cost is stated: a real 201 without `sid` would be re-sent. Same trade §5 makes preferring
  at-least-once.

### Decisiones que necesitaron ADR

**Ninguna.** The `Decision record` field predicted none and none was needed: the transport stayed inside
the BC, no second cross-BC dependency was opened, and delivery receipts stayed out of scope — those are
the three things that field names as ADR-forcing. `deptrac.yaml`, `phpstan.dist.neon` and the baseline
were **not touched**.

### Propiedades declaradas y no probadas

- ⛔ **Bar 1's sandbox half, and the Delivery bar.** Not executed; no Twilio account. Owed as
  [`BL-169`](../BACKLOG.md).
- **The alphanumeric sender a carrier actually displays** (§6, §7.11) — no harness anywhere reaches it:
  the sandbox `From` is a magic *number* and development uses a long number. Human check, once.
- **Whether the copy is good Spanish** (§7.11) — human.
- **How often the duplicate-send window actually fires** (§7.11) — only ever visible in an invoice, which
  is what `provider_reference` now makes readable.

### An intentional divergence from §3's own illustration

⚑ **`é` is not transliterated.** §3 writes the rule as *transliterated into GSM-7* and illustrates it
with `préstamo → prestamo`. Measured against 3GPP TS 23.038, **`é` is a member of the default alphabet**
— `á í ó ú` are not — so folding it saves exactly zero units while mangling correct Spanish. The **rule**
is implemented; the illustration's input was simply not checked against the table, and §5's own principle
(*"accents are free in the code and fatal in the invitation"*) points the same way. Locked by
`Gsm7AlphabetTest::an_accent_the_alphabet_already_carries_is_not_folded_for_a_saving_of_zero`, whose
docblock is what to read before "fixing" the table to match the example.

### A deviation from §3's over-budget log line

§3 says the line *"names the delivery"*. It cannot: `NotificationChannel::send()` receives the rendered
message and the destination and **no identity at all**. The line carries `tenant_id` instead — read from
`TenantContext`, because ADR-0009's `RequestContextProcessor` is a documented no-op off the request cycle
and names *"a notification delivery"* as the case it cannot stamp. That serves §3's stated purpose
(*"enough to find which tenant's data caused it"*). Widening the Domain port would touch every channel
and every fake for an observability field; it was raised and declined rather than done silently.

### Deuda dejada, y dónde vive ahora

| Qué | Su home |
|---|---|
| The sandbox tier never executed; fixtures derived from documentation | §8 above + [`BL-169`](../BACKLOG.md) |
| `make test` / `composer infection` cross-talk, and a compiled container that can report on stale config | §8 above + [`BL-170`](../BACKLOG.md) |
| Nothing counts a paid message | [`BL-166`](../BACKLOG.md), updated at this landing — its *"can send the moment it lands"* is now *"is live"* |
| Eight copy strings asserting a TTL none can read | [`BL-164`](../BACKLOG.md), updated: both channels are now paired by test, the generic detector is not built |
| `SMS_DSN` unbound in production | §8's own note + the `f5sign-infra` session, told directly on 2026-08-20 |
| The alphanumeric sender string, still undecided | The header's `Prerequisites` row — it is calendar, not engineering |
