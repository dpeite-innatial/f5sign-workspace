# TASK-073 — The integrator names the sender of an envelope, and recipients see it "vía F5Sign"

| Field | Value |
|-------|-------|
| **Status** | **Not started — parked by the owner on 2026-10-27**, written the same day so the decisions are kept; not to be launched until the owner says so. |
| **Type** | **Forward build** across Envelope (the field, its guard, the integrator read), Identity & Access (a per-tenant permission), Notification (the copy) and Session (the two recipient reads). One migration in `envelope`, one in `identity`. |
| **Why** | Nothing tells a recipient who sends them a document. The signer's card has no sender, the emails and SMS name only the platform, and an SMS from `F5Sign` reading "Tiene un documento pendiente de firma" looks like phishing ([BL-398](../BACKLOG.md)). The platform cannot name the sender itself: the tenant is the integrator's account (for the dashboard, Factor5), not the company that sends a waybill, and the sending user is an opaque actor id. Only the integrator knows. |
| **Builds on** | [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3 (what the recipient reads may carry; its 2026-08-18 amendment kept `sender_name` out for want of a source), [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) §2.4 (the per-tenant SMS permission, the pattern this follows), [ADR-0038](../adr/ADR-0038-template-archive.md) (copy is archived; variables are pinned on the occasion), [ADR-0052](../adr/ADR-0052-twig-layout-composition.md) (Twig composes, never interpolates), [ADR-0089](../adr/ADR-0089-a-recipient-is-told-when-their-part-ends.md) §7.4 (the engine has no conditional). |
| **Scope** | An optional `sender` on envelope creation (`display_name`, optional `tax_id`), refused for a tenant without the permission; the permission and its operator command; `sender` on the integrator's envelope read and on the two recipient reads; the sender in the recipient-facing emails and in the two invitation SMS. ⛔ **Not** the receipt, the audit trail or the PDF (owner, 2026-10-27), not the email's `From` (always F5Sign), not `branding.company_name`, not a list of verified senders per tenant, not an abuse-report link. |
| **Decision record** | **[ADR-0092](../adr/ADR-0092-the-integrator-names-the-sender-and-the-platform-stays-the-voice.md), `Proposed` 2026-10-27**, drafted with this record (id swept over every ref and worktree on 2026-10-27; ADR-0091 is the highest). It landed on `develop` as `Proposed` with this parked record (with its three `docs/adr/README.md` edits), and becomes Accepted in this task's changeset once §5's bars are green. It amends ADR-0049 §2.3's 2026-08-18 amendment: the sender has a source now, declared by the integrator. |
| **Sibling** | TASK-072 on `feat/copy-card-reads` (OFFREPO until it merges) adds members to the same two recipient reads (`GetSigningSessionController`, `GetCopyController`). Whichever lands second integrates `develop` before its read slice. |

<!-- OFFREPO: TASK-072 lives on `feat/copy-card-reads`; it adds `acted_at`, `act`, `receipt`, `envelope_outcome`,
`recipient_name` and `notified_on` to the two recipient reads. The request came from the signer app's session (`f5sign-signer`) on 2026-10-27, for the card on its
`/done` and `/c/:link` screens, and the integrator is the `factor5-dashboard` project, which sends waybills on
behalf of many shipping companies under one tenant. The SaaS concern in §1 is the owner's, 2026-10-27. -->

---

## 1. Why this task exists

Owner decisions, 2026-10-27:

- **Where it shows:** the signer's screens (the session read and the copy read) and the emails and SMS. Not the
  receipt nor the trail: a sealed receipt cannot be reworded, and that wants its own decision. Owner said: "1 a y b".
- **Optional, immutable.** Owner said: "Opcional si", "No se puede cambiar". It is set at creation only; no route
  edits an envelope's title or settings today, and this adds none.
- **A name and a tax id, both in one object.** Owner said: "mete el cif tambien como campo opcional y ya".
- **No sender → "F5Sign".** The copy cannot branch (ADR-0089 §7.4), so an absent sender reads as the platform.
- **SMS cost.** The name goes into the two invitation SMS only when the body stays one GSM-7 segment, transliterated
  to GSM-7; the tax id never goes by SMS.
- **SaaS safety, three layers.** Owner said: "mete la 1 y la 2 y la 3 en la 73, pero de todas formas el from de los
  correos siempre siempre va a ser f5sign".
  1. A per-tenant permission, off by default, enabled by an operator (today, only for the dashboard's tenant): a
     tenant without it that sends `sender` is refused.
  2. The platform stays the voice: recipients read "Transportes García, vía F5Sign"; the email's `From` and the SMS
     sender id stay F5Sign, always.
  3. The name is sanitised and refused when it carries a URL, an address or a domain; `ENVELOPE_CREATED` records it
     beside the actor that created the envelope.
- **`branding.company_name` is not touched**; the reads gain a separate `sender`. **The integrator's envelope read
  echoes it.**

## 2. What already exists (reuse, do not rebuild)

**Creation.** `POST /api/v1/envelopes` (`MACHINE_KEY`) is the only create route:
`Envelope/UI/Http/CreateEnvelopeController` maps `CreateEnvelopeRequest` (`title` NotBlank, `workflow_type`,
`signing_mode`, `expires_in_days` 1..180; Symfony Assert attributes, `#[MapRequestPayload]`) to
`Application/Command/Authoring/CreateEnvelope::draft()`, run by `CreateEnvelopeUseCase` into `Envelope::create()`,
which records `Contract/Event/EnvelopeCreated` (`ENVELOPE_CREATED`; payload `envelope_id`, `tenant_id`, `sender_id`
— the creating actor — `title`, `workflow_type`, `occurred_at`; `toPayload()` is the wire form, `payload()` the audit
snapshot, and `Row::optionalString` decodes an additive member an older row lacks as null). No route edits an
envelope's title (`POST /api/v1/envelopes/{id}/expiry-extensions` changes only its expiry).
Many tests dispatch `CreateEnvelope` directly (e.g. `tests/F5Sign/Integration/EnvelopeVerticalSliceTest.php`).

**Persistence.** `envelope.envelope` (RLS enabled and forced) has no sender, metadata or branding column; `title` is
`TEXT` with no bound (the repo-wide missing length bound is [BL-121](../BACKLOG.md)). `DbalEnvelopeRepository` and
`Persistence/Doctrine/Read/DoctrineEnvelopeReadRepository` read and write it.

**The per-tenant permission precedent.** SMS is enabled per tenant (ADR-0077 §2.4): a column on `identity.tenant`
(`Version20261013075329`), `IdentityAccess/Domain/Aggregate/Tenant`, the column's `GRANT UPDATE` to `f5sign_provisioning` in the same migration, the operator command
`IdentityAccess/UI/Cli/SetTenantSmsNotificationsCommand` (`app:identity:sms-notifications <tenant> --enable|--disable`)
through `SetTenantSmsNotificationsUseCase`, the fact `TenantSmsNotificationsChanged`, the contract port
`IdentityAccess/Contract/Query/TenantSmsNotifications::isEnabledFor()` (false for a tenant nobody enabled and for an
unknown id) with `DbalTenantSmsNotifications`, read in Envelope by `Application/Service/SmsAvailability`, refusing with
`SMS_NOT_ENABLED_FOR_TENANT` (published in `config/packages/nelmio_api_doc.yaml`'s code enum).

**Reads.** The integrator's `GET /api/v1/envelopes/{id}` is `GetEnvelopeController` with `EnvelopeJsonPresenter`
(`title` beside `id`, `status`…). Session reads Envelope through `EnvelopeQueryInterface::getContextForRecipient()`
(`RecipientEnvelopeContextView`, projected by `GetEnvelopeContextForRecipientHandler`; no sender); Notification
through `getContextForSE()` (`EnvelopeContextView`, positional, extended by appending). `GetSigningSessionController`
emits `branding.company_name` = the envelope title, a known defect (ADR-0049 §2.3); `GetAuthDescriptorController`'s
docblock says `sender_organization` and `sender_name` are unavailable. `GetCopyController` has no sender.

**Copy.** A notice's variables are built where it is created, in nine places, each with its own
`TemplateVariables::fromMap()`: `Notification/Application/Service/RecipientNotices::send()` (the part notices and the
sealed copy), `NotifyActivatedStepRecipientsUseCase` (the invitation), `NotifyResentInvitationRecipientUseCase`,
`NotifyAddedContactUseCase`, `NotifyClaimedRecipientUseCase`, `NotifyCorrectedRecipientUseCase`,
`NotifyRechanneledRecipientUseCase`, `NotifyEndedEnvelopeRecipientsUseCase` (the ending notices) and
`OneTimeCodeDeliveryService` (the codes). They are pinned on the occasion (ADR-0038). An unset token survives
verbatim (`NativeTemplateEngine`) and `TransmitDeliveryUseCase` then refuses the delivery in the worker
(`IncompleteRenderedMessageException`), so a variable the copy names must be set on every occasion of that purpose.
`EmailNotificationChannel::slots()` passes through only a fixed list of variables (`envelope_title`, `link`, `code`,
`reason`, `envelope_ref`) and mints each one's escaped `_html` twin; a variable outside it reaches no slot.
`SmsNotificationChannel::slots()` treats every token but `link` and `code` as customer data, transliterates it to
GSM-7 and truncates it to the remaining budget with an ellipsis. Email copy is authored inline per locale and purpose in
`Notification/Infrastructure/Channel/EmailNotificationChannel` (its docblock says the wireframe's "sender
organization" was omitted because it is not carried); the `From` is `notification.from_email` /
`notification.from_name` (`config/services.yaml`). SMS copy is authored in `SmsNotificationChannel`: the Spanish
invitation `Tiene un documento pendiente de firma: {{link}}` is 39 characters plus a 69-character link, accent-free on
purpose; a body over 160 GSM-7 units, or 70 once one character falls outside GSM-7, splits into paid segments
(`Infrastructure/Sms/SmsSegments`, `Gsm7Alphabet`). Copy and length tests: `tests/F5Sign/Notification/Unit/Infrastructure/Channel/SmsCopyTest.php`,
`EndingNoticeCopyTest.php`, `RecipientInvitationResentCopyTest.php`; variables:
`tests/F5Sign/Notification/Application/Service/RecipientNoticesTest.php`. The purposes are the 20 cases of
`Notification/Domain/ValueObject/NotificationPurpose`, three of them delivered one-time codes (`AUTH_OTP_*`).

## 3. Scope

1. **Input.** `CreateEnvelopeRequest` gains an optional `sender` object: `display_name` (required inside it) and
   `tax_id` (optional). Rules in §4 #3. Stored on two nullable columns of `envelope.envelope`, never changed.
2. **The permission.** `identity.tenant` gains a boolean, off by default; `app:identity:sender-naming <tenant>
   --enable|--disable`; a fact on change; a contract port `TenantSenderNaming::isEnabledFor()`. Envelope refuses a
   `sender` from a tenant without it with a new code `SENDER_NAMING_NOT_ENABLED`.
3. **The fact.** `ENVELOPE_CREATED` gains `sender_display_name` and `sender_tax_id` (null when absent); an older
   payload decodes with both null.
4. **Reads.** `sender: {display_name, tax_id} | null` on `GET /api/v1/envelopes/{id}`, `GET /api/v1/signing/session`
   and `GET /api/v1/copy`, through the two context views.
5. **Copy.** Every recipient-facing email except the three delivered codes names the sender as
   "<name>, vía F5Sign" (localised), or "F5Sign" with none, and shows the tax id when present; the two invitation SMS
   name it when the body stays one segment. The `From` is untouched.
6. **ADR-0092** as `Proposed`; the handoffs to the signer and the integrator.

Concepts re-cut: `sender_name` / `sender_organization` "have no source" (ADR-0049 §2.3, `GetAuthDescriptorController`
and `SmsNotificationChannel` docblocks, the TASK-021 handoff), the email channel's "sender organization omitted"
docblock, `sender_id` (still the creating actor, never a display name).

## 4. Key decisions

1. **Creation only.** No route edits an envelope's title or its sender, so "immutable after send" is met by never
   offering a write; a later edit route is a new decision.
2. **The permission is Identity & Access's, read through its contract.** As SMS is (ADR-0077 §2.4): the tenant is
   Identity & Access's aggregate, and an operator command, not the API, enables it.
3. **Input rules.** `display_name`: trimmed, control characters removed, 1..70 characters, refused if it contains a
   URL scheme, an `@`, or a dotted host (`label.tld`, the label alphanumeric or hyphen and the TLD two or more
   letters); `S.L.`, `S.A.` and `Ind.` pass. `tax_id`: trimmed and upper-cased, 1..20 of `A-Z`, `0-9`, `-`; no checksum,
   since it may be foreign. `sender: {}` and `sender` with only a `tax_id` are refused.
4. **The voice stays the platform's.** The sender is a variable inside copy authored by the platform, never the
   `From` header nor the SMS sender id. With no sender the variable reads `F5Sign`, so no copy branches. Because
   every occasion of a purpose whose copy names the sender must carry the variables (§2), every builder takes them
   from one shared source that also applies the default, and a census over the builders fails on one that does not.
   The email channel's pass-through list gains the new variables.
5. **SMS spends no extra segment.** The name is transliterated to GSM-7 for SMS (`García` → `Garcia`); if the body
   would then exceed one segment, the SMS goes with today's body, never with a truncated name. The tax id never goes
   by SMS, and the SMS body says no "vía F5Sign": the sender id already says it, and `í` would push the whole body to
   UCS-2 beside the 69-character link. With the body `<name> le envia un documento para firmar: {{link}}` (36
   characters plus the link), a name of up to 55 GSM-7 units fits. No path chooses today between two bodies, and the
   SMS slot mechanism truncates instead: the plan chooses between a second archived body per invitation and a
   platform-authored slot, and proposes the exact Spanish and English bodies to the owner before the copy slice.
6. **Delivered codes stay as they are.** `AUTH_OTP_*` carry a code and nothing else; adding a name to them widens
   what a forged one could claim.
7. **`branding.company_name` is untouched**; a client that reads it keeps reading the title.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A permitted tenant creates an envelope with `sender`, and it is stored and read back unchanged (members AC-1a…c) | owner | Acceptance | drop the column write |
| AC-2 | A tenant without the permission that sends `sender` is refused 422 `SENDER_NAMING_NOT_ENABLED`, and no envelope is created; without `sender` it creates as today | owner | Acceptance | skip the permission check |
| AC-3 | The permission is off for every tenant until an operator enables it, and the command enables and disables it (members AC-3a…c) | owner | Integration + Unit | default the column to true |
| AC-4 | `sender` is refused 422 with a field violation for each rule of §4 #3 (members AC-4a…h) | owner | Acceptance | drop the URL rule |
| AC-5 | No route changes `sender` after creation | owner | Acceptance (route census) | add a PATCH |
| AC-6 | `GET /api/v1/envelopes/{id}` carries `sender`, null when none | owner | Acceptance | omit the key when null |
| AC-7 | `GET /api/v1/signing/session` and `GET /api/v1/copy` carry the same `sender`, null when none | owner | Application + Acceptance | read it from the tenant |
| AC-8 | Every recipient-facing email but the delivered codes names "<name>, vía F5Sign", or "F5Sign" with none, in each authored locale (members AC-8a…c) | owner | Unit (copy census) | leave one purpose without it |
| AC-9 | The email's `From` is F5Sign's address and name whatever the sender, and no header carries the sender's name | owner | Unit | set the display name from `sender` |
| AC-10 | The two invitation SMS name the sender transliterated to GSM-7 when the body stays one segment, and keep today's body otherwise; no SMS carries the tax id (members AC-10a…d) | owner | Unit | keep the accent |
| AC-11 | `ENVELOPE_CREATED`'s wire form (`toPayload`) carries `sender_display_name` and `sender_tax_id` beside `sender_id`, an older payload decodes with both null, and its audit snapshot (`payload`) is unchanged | owner | Unit | drop a key from `toPayload` |
| AC-12 | The tax id appears in the emails' sender line when present and nowhere when absent | owner | Unit | print an empty label |
| AC-13 | An envelope created before the migration reads `sender: null` everywhere and its notices say "F5Sign" | derived — rule 6 | Integration | backfill a value |
| AC-14 | The sender reaches every email's slots and is escaped as text there (members AC-14a…c) | derived — [ADR-0052](../adr/ADR-0052-twig-layout-composition.md) §2.3 | Unit | use the raw variable in the HTML twin |
| AC-15 | The delivered-code messages (`AUTH_OTP_*`) are unchanged, by email and by SMS | derived — [ADR-0092](../adr/ADR-0092-the-integrator-names-the-sender-and-the-platform-stays-the-voice.md) §2.4 | Unit | add the sender line |
| AC-16 | A notice created before a sender exists keeps its pinned variables (no sender is added to an existing occasion) | derived — [ADR-0038](../adr/ADR-0038-template-archive.md) | Application | read the sender at delivery |
| AC-17 | The permission read is per tenant: enabling tenant A does not let tenant B name a sender | derived — `src/F5Sign/IdentityAccess/Contract/Query/TenantSmsNotifications.php` | Integration | ignore the tenant id |
| AC-18 | The published `#[OA\*]` of the create route (the `sender` input, its 422 codes) and of the three reads (`sender` in `required`, nullable) match what is emitted, and `SENDER_NAMING_NOT_ENABLED` is in the code enum | derived — `tests/F5Sign/Acceptance/OpenApiSpecTest.php` | Unit + `OpenApiSpecTest` | leave the code out of the enum |
| AC-19 | The receipt, the audit trail and `branding.company_name` are unchanged | derived — [ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md) §2.3 | Unit | print the sender on the receipt |
| AC-20 | Every place that creates a notice whose copy names the sender sets the sender variables, with the default when the envelope has none: a census over the builders of §2 fails on one that does not (members AC-20a…b) | derived — `src/F5Sign/Notification/Application/UseCase/TransmitDeliveryUseCase.php` | Application | drop the variables from one builder |
| S-1 | A permitted tenant sends an envelope with `sender` to an email recipient and an SMS recipient: the invitation email reads "Transportes García, vía F5Sign" with the tax id, `From` F5Sign; the SMS names "Transportes Garcia" in one segment; the signer's session read and copy read carry `sender` | derived — [ADR-0092](../adr/ADR-0092-the-integrator-names-the-sender-and-the-platform-stays-the-voice.md) §2.1 | Acceptance | — |

- **Gates:** suite, PHPStan, deptrac and lint, under the lane that mounts this tree.

**Notes on AC-1**
- AC-1a — `display_name` and `tax_id`: both stored, the tax id upper-cased.
- AC-1b — `display_name` alone: `tax_id` null.
- AC-1c — no `sender`: both null, and the envelope behaves as today.

**Notes on AC-3**
- AC-3a — every existing tenant reads false after the migration. AC-3b — `--enable` makes it true and records the
  fact. AC-3c — `--disable` makes it false; an envelope already created keeps its sender.

**Notes on AC-4**
- AC-4a — empty `display_name` after trimming. AC-4b — over 70 characters. AC-4c — `https://…` or `http://…`.
  AC-4d — an `@`. AC-4e — a dotted host (`banco.com`, `pay.example.es`). AC-4f — `tax_id` with a character outside
  `A-Z0-9-` or over 20. AC-4g — `sender: {}`. AC-4h — `sender` with only a `tax_id`.
- Accepted beside them: `Transportes García S.L.`, `Ind. Pérez S.A.`, control characters stripped.

**Notes on AC-14**
- AC-14a — the email channel's pass-through list carries the sender variables and their escaped `_html` twins.
- AC-14b — a name with `<`, `&` or `"` renders literally in the HTML part.
- AC-14c — the plain-text part carries the name unescaped and unaltered.

**Notes on AC-20**
- AC-20a — every builder of a purpose that names the sender (the invitation, the resend, the added contact, the
  claim, the correction, the re-channel, the endings, the part notices, the sealed copy) sets them.
- AC-20b — the codes' builder (`OneTimeCodeDeliveryService`) does not, and its copy does not name them (AC-15).

**Notes on AC-8**
- AC-8a — the census runs every `NotificationPurpose` case and classifies it as naming the sender or as a delivered
  code; a new case fails it unclassified. AC-8b — with a sender. AC-8c — without one: "F5Sign".

**Notes on AC-10**
- AC-10a — `RECIPIENT_INVITATION`, short name: one segment, the name transliterated. AC-10b —
  `RECIPIENT_INVITATION_RESENT`, the same. AC-10c — a name that would take a second segment: today's body. AC-10d —
  a tax id is never in any SMS body.

## 6. Open follow-ups (track, don't solve here)

1. **The sender on the receipt and the trail.** A sealed receipt cannot be reworded; printing the sender there wants
   its own decision (owner, 2026-10-27).
2. **Verified senders per tenant and an abuse-report link**, for a self-service SaaS: the integrator would pick among
   names an operator approved instead of writing free text. The permission of this task is the gate meanwhile.
3. **A sole trader's tax id is personal data**, stored in plain text like every column today (ADR-0033 is
   `Proposed`).
4. **`branding.company_name`** still carries the envelope title (ADR-0049 §2.3).
