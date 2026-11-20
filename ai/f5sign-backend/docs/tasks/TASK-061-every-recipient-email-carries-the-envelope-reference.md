# TASK-061 — Every email a recipient receives carries the envelope reference

<!-- OFFREPO: the signer app and the dashboard are separate repositories. The only facts taken from them (the signer footer shows `envelope.id`; the dashboard cannot yet search by envelope id) are restated in §1. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/envelope-reference-in-emails`** (`f76722ae`), 2026-10-20 — full suite green under the `wt-backend` lane mounting this worktree (OK, 7602 tests, 84103 assertions; lint, arch and phpstan clean). Infection, filtered to the 10 `src/` files of the diff (`wt-backend-infection`, same lane): 0 escaped and 0 uncovered mutants on the 35 changed lines; whole-file MSI 94.3 %, covered-MSI 94.9 % (bars 70 / 85). Not built here, by decision: SMS, the dashboard's search by envelope id and the signer footer (§6, [BL-433](../BACKLOG.md)). |
| **Type** | **Forward build** in Notification only: one new slot in the shared EMAIL footer and the value supplied by every occasion that sends an email. No route, event or schema changes. |
| **Why** | A signer whose link fails has nothing to quote to support. The most common support case is *"my link doesn't work"*: a 401 on the signer's invalid-link page (expired, revoked or unknown token, deliberately without data), a 5xx, or a 409 `RECIPIENT_SIGNS_ELSEWHERE` (deliberately without ids). In all of them the signing read-model never answered, so the signer app has no envelope id to show, and the `f5s_st_…` token is opaque. The email is the one place the signer still holds a reference when the link fails. |
| **Decision record** | **No ADR yet.** The change adds a slot inside the rules that [ADR-0038](../adr/ADR-0038-template-archive.md) (Decision 2 and 6: a changed template mints a new archived version, kept insert-only) and [ADR-0052](../adr/ADR-0052-twig-layout-composition.md) (Twig composes, never interpolates; no recipient value reaches the view) already set. An ADR would be forced by showing the reference on SMS, or by making it anything other than an opaque identifier (a link, a lookup credential). |
| **Builds on** | [TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md) (the authored EMAIL catalog and its chrome), ADR-0052 (the shared layout). |
| **Scope** | EMAIL only. SMS copy is untouched (owner, 2026-10-20: segment cost). The dashboard's search by envelope id and the signer app's footer are other repositories (§6). |

---

## 1. Why this task exists

<!-- OFFREPO: the request comes from the signer team's session and the dashboard team's session on 2026-10-20. Nothing here depends on reading either: every fact taken from them is restated in this section. -->

The owner asked, through the signer team, that the envelope reference reach the signer in the email, so the
signer can quote it to support. The signer app will show the same value in its own footer: the full
`envelope.id` from `GET /api/v1/signing/session` (the same value as `envelope_id` returned when the session
opens), in monospace, labelled *"Referencia del sobre"* / *"Envelope reference"*. It can only show it once the
read-model has answered for that link, which is exactly what does not happen in the failure cases of the
header's **Why**.

The dashboard team confirmed on 2026-10-20 that the dashboard cannot yet find an envelope by its id (its only
id filter matches its own record's id); the owner decided the dashboard adds that search, in its own
repository.

Owner decisions, 2026-10-20: every EMAIL to a recipient carries it; no SMS does; the id is printed in full,
never abbreviated, in the same form as the signer app.

## 2. What already exists (reuse, do not rebuild)

- **The EMAIL catalog** is `Notification\Infrastructure\Channel\EmailNotificationChannel::TEMPLATES`, keyed
  locale → `NotificationPurpose` → `subject`, `body`, `html`. Locales `es` (the default) and `en`. All twelve
  purposes are authored in both: `RECIPIENT_INVITATION`, `RECIPIENT_INVITATION_RESENT`, `ENVELOPE_COMPLETED`,
  `SEALED_COPY_READY`, `ENVELOPE_ENDED_SENDER_CANCELLED`, `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON`,
  `ENVELOPE_ENDED_DECLINED`, `ENVELOPE_ENDED_TIME_RAN_OUT`, `ENVELOPE_ENDED_OUT_OF_REACH`, `AUTH_OTP_SIGNING`,
  `AUTH_OTP_ACCESS`, `AUTH_OTP_DECLINE`. Enumerate them from `NotificationPurpose` rather than from this list.
- **The shared footer** exists twice, once per part, both fed by `EmailNotificationChannel::CHROME` (per-locale
  words: `fallback_link_label`, `tagline`, `automated`, `never_asks`): the HTML footer in
  `templates/notification/layout.html.twig` (through `EmailLayoutView`; `auth-otp.html.twig` for the three
  `AUTH_OTP_*` purposes, per `htmlTemplate()`), and the text footer appended by `textFooter()` after `-- `.
  A line placed there reaches every purpose without editing twelve templates.
- **Slots.** `EmailNotificationChannel::slots()` passes through an allowlist (`envelope_title`, `link`,
  `code`, `reason`), deriving each `x_html` twin with `escapeHtml()`, plus `recipient_salutation`. A variable
  outside the list is dropped silently, so a new slot needs its name added there. `NativeTemplateEngine`
  leaves an unresolved `{{token}}` standing, and `TransmitDeliveryUseCase` refuses to send a message with one
  (`IncompleteRenderedMessageException`), on both channels.
- **The value is in scope at every source.** Eight places build a notification's variables, and each has the
  envelope id: `NotifyActivatedStepRecipientsUseCase`, `NotifyClaimedRecipientUseCase`,
  `NotifyRechanneledRecipientUseCase`, `NotifyCorrectedRecipientUseCase`,
  `NotifyResentInvitationRecipientUseCase`, `NotifyCompletedEnvelopeRecipientsUseCase` (two purposes),
  `NotifyEndedEnvelopeRecipientsUseCase` (as `$envelope->id`, already used for the subject `Reference`), and
  `OneTimeCodeDeliveryService` (as `OneTimeCodeRequest::$subjectId`, set by Session's
  `IssueAuthChallengeUseCase` from the envelope ref).
- **Templates are pinned at creation.** `NotificationTemplates` registers the template when the notification
  is saved; `Template::fingerprint()` derives the version from the parts, so an edited footer mints a new
  version and a new `platform.template` row (insert-only, `DbalTemplateArchive::put`). A notification saved
  before the change keeps its old template and its old variables (persisted as JSON by
  `DbalNotificationRepository`).
- **SMS** (`SmsNotificationChannel::slots()`) reads only the tokens its template uses and ignores extra
  variables, so supplying the new variable to an SMS-bound notification changes nothing there.
- **The recipient's notification history** (`GET …/recipients/{recipientId}/notifications`, TASK-058) does
  not expose variables, so no read contract changes.
- **Tests that pin today's set exactly** and will need the new member: `NotifyRechanneledRecipientUseCaseTest`
  and `NotifyClaimedRecipientUseCaseTest` (closed `variables()->toArray()`), `EndingNoticeCopyTest` (closed
  slot allowlist of the ending notices), `EmailLayoutViewTest` (its own chrome array),
  `EmailChannelTwigWiringTest` (byte-identical markup between container and hermetic environments). This list is not exhaustive: before implementing, `rg -n 'toArray\(\)|allowed' tests/F5Sign/Notification` for every exact-set assertion on variables or slots.

## 3. Scope

1. A new slot, `{{envelope_ref}}` / `{{envelope_ref_html}}`, in the shared footer of both EMAIL parts and of
   both layouts, after a per-locale label added to `CHROME`: *"Referencia del sobre"* (`es`),
   *"Envelope reference"* (`en`). The HTML shows the value in monospace and as plain text, not a link.
2. `envelope_ref` added to `slots()`'s pass-through list.
3. Each of the eight sources of §2 supplies `envelope_ref` = the envelope id's string form.
4. Tests of §5, and the exact-set tests of §2 extended with the new member.

Out: SMS copy; the dashboard search; the signer footer; tenant-authored copy.

Concepts re-cut: none (an addition; no term retired, no symbol's behaviour changed beyond the variable map).

## 4. Key decisions

- **The footer, not the twelve bodies.** One line in the chrome covers every purpose and every future one;
  editing each body would leave the next purpose without it.
- **A slot, not a view field.** The id is a per-envelope value, so under ADR-0052 §2.1 it reaches the markup
  only as a `{{token}}` that `NativeTemplateEngine` fills at transmit.
- **The full uuid**, identical to the signer app's `envelope.id`, so support sees one identifier wherever the
  signer looks.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | Every EMAIL purpose, in both parts and both authored locales, renders the full envelope id after the label "Referencia del sobre" / "Envelope reference" (members AC-1a…l) | owner | Unit | drop the footer line |
| AC-2 | The value in the invitation email equals the `envelope.id` that `GET /api/v1/signing/session` returns for the link in that same email | owner | Acceptance | supply another id |
| AC-3 | No SMS template carries the slot, and an SMS render is unchanged by the new variable | owner | Unit | add the slot to one SMS template |
| AC-4 | Each source supplies `envelope_ref` equal to the envelope id (members AC-4a…h) | derived — src/F5Sign/Notification/Application/UseCase/TransmitDeliveryUseCase.php (refuses an unresolved slot) | Application | drop the key at one source |
| AC-5 | A notification saved before the change, with its old pinned template and variables lacking `envelope_ref`, still transmits | derived — ADR-0038 Decision 2 and 6 | Integration | make the old template carry the slot |
| AC-6 | The composed (pre-interpolation) markup carries the literal `{{envelope_ref_html}}` slot; `EmailLayoutView` holds no envelope value | derived — ADR-0052 §2.1 | Unit | pass the id through the view |
| AC-7 | The chrome still links nothing but the vendor site: the reference is text, not a link | derived — tests/F5Sign/Notification/Unit/Infrastructure/Channel/EmailNotificationChannelTest.php | Unit | wrap the value in a link |
| AC-8 | Knowing an envelope id admits nothing: a machine route on it without the tenant's API client, and a signing route without a token, are refused | derived — ADR-0017 and ADR-0048 | Acceptance | — (regression) |

- **Gates:** suite, PHPStan, deptrac and lint, under the `wt-backend` lane that mounts this worktree.

**Notes on AC-1** — one member per `NotificationPurpose` case: AC-1a `RECIPIENT_INVITATION`, AC-1b
`RECIPIENT_INVITATION_RESENT`, AC-1c `ENVELOPE_COMPLETED`, AC-1d `SEALED_COPY_READY`, AC-1e
`ENVELOPE_ENDED_SENDER_CANCELLED`, AC-1f `ENVELOPE_ENDED_SENDER_CANCELLED_WITH_REASON`, AC-1g
`ENVELOPE_ENDED_DECLINED`, AC-1h `ENVELOPE_ENDED_TIME_RAN_OUT`, AC-1i `ENVELOPE_ENDED_OUT_OF_REACH`, AC-1j
`AUTH_OTP_SIGNING`, AC-1k `AUTH_OTP_ACCESS`, AC-1l `AUTH_OTP_DECLINE`. The test iterates the enum's cases, so
a thirteenth purpose is covered or fails. Owner said: "Todos los emails"; "Completo, como en el signer".

**Notes on AC-4** — AC-4a `NotifyActivatedStepRecipientsUseCase`, AC-4b `NotifyClaimedRecipientUseCase`,
AC-4c `NotifyRechanneledRecipientUseCase`, AC-4d `NotifyCorrectedRecipientUseCase`, AC-4e
`NotifyResentInvitationRecipientUseCase`, AC-4f `NotifyCompletedEnvelopeRecipientsUseCase` (both purposes),
AC-4g `NotifyEndedEnvelopeRecipientsUseCase`, AC-4h `OneTimeCodeDeliveryService`.

**Notes on AC-5** — this is the deploy-time risk: a delivery retried after the release must not meet a slot
its saved variables cannot fill. It holds by construction because the template is pinned with the
notification; the test pins it.

## 6. Open follow-ups (track, don't solve here)

<!-- OFFREPO: the first two items live in the dashboard and signer repositories. Their facts are restated in §1; nothing here depends on reading them. -->

- **Dashboard search by envelope id** — owner decided 2026-10-20 that the dashboard adds it, in its own
  repository. ⚠ **On hold by its owner since 2026-10-20: still decided, not started.** Until it lands, support
  cannot act on the reference. An out-of-repo dependency, indexed in [BL-433](../BACKLOG.md).
- **Signer footer** — the signer app shows the same value; built in its own repository ([BL-433](../BACKLOG.md)).
- **SMS** — not carried, by decision (segment cost). Revisit only with a measured segment budget.

## 7. Deviations & honest notes

### Scope
- None. The diff stays in Notification (`src/F5Sign/Notification`, `templates/notification/layout.html.twig`), its tests and this record. Slice 03 added `EmailChannelTwigWiringTest` and `PropagateDelivery{Failure,Success}UseCaseTest` to its files after the orchestrator's answer in round 1: their fixtures' variable maps needed the new member.

### Decisions made during implementation
- Slice 01: code and tests were written together, so red was not watched first; red was shown by sabotage of the `Corrected` and `Claimed` sources, and the reviewer confirmed the other three asserts fail without the entry.
- Slice 02: the production lines of the two use cases were added before the first run; their red was shown by sabotaging all three guards.
- Slice 04: the round-2 fix (`97b6dbe8`) is exactly the one finding, a three-line `@criterion` docblock on the single-recipient scenario. The orchestrator checked the diff instead of calling a second review.
- Slice 05: the pinned-delivery test uses a non-envelope subject to skip `stillNeeded()`'s envelope read. The reviewer confirmed that read is independent of AC-5's path (template find, render, unresolved check).

### Decisions that needed an ADR
- None. The slot sits inside ADR-0038 (Decisions 2 and 6) and ADR-0052 (§2.1) as they stand.

### Declared and unproven properties
- None. AC-5 has an Integration test (`PinnedBeforeTheEnvelopeReferenceTest`), AC-2 and AC-8 an Acceptance test (`Scenario01SingleRecipientHttpTest`). Infection leaves no escaped or uncovered mutant on the changed lines (Status).

### Debt left behind, and where it lives now
- The dashboard's search by envelope id (on hold) and the signer footer, both in other repositories: §6 and [BL-433](../BACKLOG.md).
- SMS does not carry the reference, by decision: §6.

### Delegated work
- Five slices, no `replicator` use (every slice's `## Delegated` is "none"; slice 03 notes the fixture ripple was seven one-line map edits across five files, cheaper by hand than by brief).
- 01 standard, sonnet, 1 round, DONE_WITH_CONCERNS (red-first not followed). 02 standard, sonnet, 1 round, DONE. 03 critical, opus, 2 rounds, DONE (an orphaned phpunit from a timed-out run overlapped one run, giving five false reds; it was killed and every cited green is after it). 04 standard, sonnet, 2 rounds, DONE. 05 standard, sonnet, 1 round, DONE.

### Cost of the run
- Five slices over six commits (31 files, +708 −15 against the record's commit); 7 review rounds in all, no escalation beyond slice 03's opus tier. The closing review approved with nothing above the cut; security audit passed with 0 blocking and 0 warnings. Per-model token totals are not in the workspace; the orchestrator's Phase 7 table holds them.
