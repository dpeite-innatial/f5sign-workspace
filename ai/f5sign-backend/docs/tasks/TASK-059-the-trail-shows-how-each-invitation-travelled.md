# TASK-059 — The audit trail shows how each invitation travelled

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/trail-invitations`** (d9d80e24), 2026-10-14 — the full suite is green at that commit under the `wt-backend` lane on this worktree's tree (lint, arch, PHPStan and all tiers: 7233 tests, 81948 assertions). Infection, filtered to the eight `src/` files the branch touches: covered MSI 97 %, MSI 97 % (bar 85/70), every mutant covered; of the four escaped on changed lines one is killed by P-TRAIL-219 (59b1ae78, a test-only commit) and three are justified in §8. AC-7c is an evidence run, not a test (§8). Pending review; ADR-0078 stays Proposed (it moves with TASK-058). |
| **Type** | **Forward build with a change to a published format**, inside Evidence & Audit: the trail model, its JSON form, the assembler, the Typst template and its labels. No other context changes. |
| **Why** | The trail cannot prove how the signer got the link. It renders contact uses only from Session's `OtpSent`; no invitation, resend or refusal reaches it, for email either, and Evidence & Audit may not read Notification's events ([ADR-0037](../adr/ADR-0037-notification-supporting-bc.md)). Once [TASK-056](TASK-056-delivery-facts-and-sender-visibility.md) records each outcome as an Envelope event, the trail can state channel, masked destination, outcome and purpose from the log, and a court reading it can see that a link went to `f***@***.com` by email at a given instant, or that it was never sent. |
| **Decision record** | [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.5, the trail half — **Proposed** on 2026-10-09 (it moves to Accepted with TASK-056 and TASK-058). It extends [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md): the trail gains a source. |
| **Builds on** | [TASK-056](TASK-056-delivery-facts-and-sender-visibility.md) (**required**: the events this renders) · [TASK-031](TASK-031-channel-selection-beyond-email.md) §3.13 (**required**: types the events' `channel` as Envelope's closed `InvitationChannel`, the vocabulary this states and labels) · [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.2, §2.3, §2.4, §2.6 · [`PartyPersonal`](../../src/F5Sign/EvidenceAudit/Domain/Trail/PartyPersonal.php) and [`ContactUse`](../../src/F5Sign/EvidenceAudit/Domain/Trail/ContactUse.php), the precedent this follows · [`MaskedContact`](../../src/F5Sign/Foundation/ValueObject/MaskedContact.php) · [`TrailJson`](../../src/F5Sign/EvidenceAudit/Domain/Trail/TrailJson.php) · [`Chain`](../../src/F5Sign/EvidenceAudit/Domain/Trail/Chain.php). |
| **Order** | Last of the four: needs TASK-056 and [TASK-031](TASK-031-channel-selection-beyond-email.md) merged; TASK-031 types `channel` (§3.13) and first produces `DELIVERED_BY_INTEGRATOR`. Independent of [TASK-055](TASK-055-delivery-reliability.md). |

---

## 1. Why this task exists (measured on the tree, 2026-10-09)

- **Contacts are rendered from codes only.** `TrailAssembler::contacts()` builds one `ContactUse` per
  `OtpSent` fact and nothing else; `rg -n 'RECIPIENT_INVITATION|RecipientInvitationResent' src/F5Sign/EvidenceAudit`
  finds no invitation rendering. A signer behind an open gate who arrived by an emailed link has no
  statement of how it reached them.
- **The facts will be in the log without this task.** The trail folds the **whole stream**
  (ADR-0072 §2.2, `AuditTrail::facts`), and `Chain` folds each fact's log position and commitment,
  nothing of the model. So the day TASK-056 records `RecipientInvitationOutcomeRecorded` and
  `RecipientDestinationRefused` in the Envelope stream, they are listed in `facts` and inside the chain,
  and the template already prints them as labelled lines. ADR-0078 §2.5 says rendering "changes its
  published, chained form"; on the tree the **chain** changes at TASK-056, and what this task changes is
  the **model and its JSON**, by adding a section.
- **The published form is guarded in four places**: `AuditTrail::SCHEMA` (`f5sign.audit-trail/1`),
  `TrailJson`'s docblock rule ("adding a field keeps the schema version; removing a field or changing
  its meaning moves it"), the goldens and `TrailJsonCompletenessTest`, and `PublishedCodesTest` for
  enumerated codes.

## 2. What already exists (reuse, do not rebuild)

- **The precedent for exactly this shape.** `PartyPersonal::contacts()` holds `ContactUse` records
  (gate, act, method, a `Statement<MaskedContact>`), and `TrailAssembler::contacts()` resolves the
  destination from the recipient row by what the method needs, states `CORRECTED_AFTERWARDS` when a
  `RecipientCorrected` fact sits after the sent fact in log order, and `SOURCE_UNAVAILABLE` when the row
  is gone. The invitation follows it, destination kind in place of method.
- **`MaskedContact::of()` is the only way to build one**, so an unmasked contact cannot reach the trail by
  construction (private constructor). ADR-0072 §2.6 keeps every personal value of a party inside
  `PartyPersonal`, so a later cipher wraps the group without reshaping the trail.
- **`DecodedStream::allFor()` / `firstFor()`** return a recipient's facts by event class in log order;
  the registry decodes any registered event class, so TASK-056's events decode without wiring.
- **`Statement` / `UnstatedReason`** (`NOT_PROVIDED_BY_INTEGRATOR`, `NOT_RECORDED_BY_PLATFORM`,
  `SOURCE_UNAVAILABLE`, `CORRECTED_AFTERWARDS`) are how this model says "the platform cannot tell".
  *Note, 2026-10-14:* that list is the pre-task tree's. TASK-045 added `NOT_REPORTED` and
  `DISCARDED_ILL_FORMED`; this task adds `OUTCOME_NOT_RECORDED` (§5 D3).
- **`RecipientStepActivated`** carries the step ordinal and no `recipient_id`, and a `Party` carries its
  `step`: an activation fact for the party's step is readable from the stream, but not through
  `allFor()` / `firstFor()`, which match on `recipient_id`. It is found by filtering the stream's facts of
  that class on `step_ordinal`, and one is enough (a step that activated more than once still activated).
- **`LimitationCode`**: "a code never changes meaning"; a limitation is listed only when it applies and
  in the order of the cases.
- **Issued trails are immutable.** `evidence_audit.issued_trail` holds one row per envelope and its sealed
  PDF sits in custody (ADR-0072 §2.10); a deployment of this task rewrites none of them.
  `app:evidence-audit:render-trail` can re-render an old stream and will use the new code on it.
- **Fixtures**: `Factor5TrailSources`, `Factor5TrailFixtures`, `tests/bin/render-trail-fixtures.php`.
  ADR-0072 §9 records why hand-built streams are not enough: the 2026-10-01 re-cut found defects that
  hand fixtures, written in the earlier order, had passed.

## 3. What gets built

**3.1 The model.** `InvitationUse`: the purpose (`INVITATION` | `RESEND`), the outcome (`SENT`, `FAILED`, `REFUSED`,
`NOT_SENT_NO_REACHABLE_CHANNEL`, `DELIVERED_BY_INTEGRATOR`), the channel (the event's own `channel`, an
Envelope `InvitationChannel`; never derived from `destination_kind`, which cannot tell one medium's
channels apart), the instant, and an `Option<Statement<MaskedContact>>` (empty for `FAILED`, `NOT_SENT_NO_REACHABLE_CHANNEL` and
`DELIVERED_BY_INTEGRATOR`, whose events carry neither channel nor destination, so their channel is
empty too). The destination is resolved from the event's `destination_kind`, which says which of the
recipient's contacts it was. The outcome is a trail-side enum of five members: Envelope's four
`InvitationOutcome` cases plus `REFUSED`, which is not one of them. `RecipientDestinationRefused` events (all of an invitation purpose: TASK-056 §3.4 has no `CODE` member) become `REFUSED` entries, so
a refused SMS beside a landed email is stated.

**3.2 The assembler.** Per party: the party's `RecipientInvitationOutcomeRecorded` and
`RecipientDestinationRefused` facts in log order, each resolved as `contacts()` resolves a code's
destination (§2). A re-invitation after a correction is the entry that follows `RECIPIENT_CORRECTED` in
the party's list; it carries no purpose of its own (TASK-056 §5 D3).

**3.3 The JSON.** `personal.invitations`, beside `contacts` and in the model's order, each entry
`{purpose, outcome, channel, at, contact}`; `schema` stays `f5sign.audit-trail/1` (§5 D1).

**3.4 The template and its labels.** A line per entry in the party's block; label groups
`invitation-purpose`, `invitation-outcome` and `channel` in `assets/evidence-audit/trail.typ`, Spanish
like the rest, and the same groups added to the label census in `TypstTrailRendererTest`, which compares
each group's keys to the enum's cases exactly: `invitation-purpose` against Envelope's
`InvitationPurpose`, `channel` against Envelope's `InvitationChannel` (TASK-031 §3.13, closed: a channel
added later fails the census naming it), and `invitation-outcome` against the trail's own five-member
outcome enum (§3.1), not Envelope's `InvitationOutcome`, which has no `REFUSED`. TASK-056's two event types and its release-reason members
are labelled by TASK-056; verify rather than assume.

**3.5 One limitation.** A new `LimitationCode` appended **last**, applying when the trail states any
`SENT` invitation: the platform records that a message was handed to a provider and ingests no receipt
([BL-390](../BACKLOG.md)). Appended last so no existing trail's limitation order moves.

**3.6 Docs: a rule-1 sweep.** `rg -n 'OtpSent|contacts\(\)|ContactUse|published, chained|invitation' src/F5Sign/EvidenceAudit docs/adr/ADR-0072* docs/ddd/evidence-audit-domain-model.md assets`
and convert one file at a time: ADR-0072 (§2.4, §2.6, §5, §6, a §9 entry for this arc, Status),
`docs/ddd/evidence-audit-domain-model.md`, the `TrailJson`, `PartyPersonal` and `ContactUse` docblocks
(each says contacts are for codes), ADR-0078's Status / Enforced by / Realized in.

## 4. Scope

**In scope:** §3.1–§3.6. **Out of scope:** Notification's history route
([ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) §2.7; it is not evidence);
rendering the refusal of a delivered **code** (it is a `RecipientDeliveryFailed` fact, not a `RecipientDestinationRefused` one, and stays in the facts list); the cipher of the personal
group; any change to `Chain` or to `AuditTrail::SCHEMA`; the Envelope events themselves
(TASK-056).

Concepts re-cut: contacts (no longer codes only), ContactUse, PartyPersonal, published chained form.

## 5. Key decisions

**D1 — How the section joins a published, chained format without breaking the trails that exist.**
Options:

- **(A) Additive, schema unchanged.** A new key under `personal`; `AuditTrail::SCHEMA` stays `/1`;
  `Chain` untouched. `TrailJson`'s own rule allows it, a reader of `/1` that ignores unknown keys is
  unaffected, and issued trails are immutable.
- **(B) Move the schema to `/2`.** A reader pinned to `/1` refuses the new trails. The docblock reserves
  the bump for removing or redefining a field, which this is not.
- **(C) A second attachment** (an invitations JSON). Leaves the trail's bytes alone, but ADR-0072 §2.1
  makes the trail's JSON the PDF's **one** attachment, and the evidence would split across two files.
- **(D) Print in the template from `facts`, with no model field.** Rejected by `AuditTrail`'s own rule:
  anything not in the model cannot appear on the page.

**Decided by the owner on 2026-10-09: (A)** — the owner confirmed that nothing outside this repository reads the trail's JSON, which discharges the precondition below. The chain is a function of the stream's facts, and those do not depend on this
task. `Chain::GENESIS_PREFIX` is a literal deliberately independent of the schema string. One
precondition, checked before merge: ADR-0072 §9 recorded on 2026-09-28 that *nothing outside the
repository reads the JSON yet*; if a consumer now exists that **rejects unknown keys**, take (B), and
every bar below holds for either (the schema string is asserted from one constant).

**D2 — Where the destination sits.** (a) The whole entry inside `PartyPersonal`, as `ContactUse` does
(it keeps method and gate there too). (b) Outcome and instant at party level, the masked destination
alone in `PartyPersonal`, joined by the fact's log position. **Decided: (a)** (2026-10-09, under the owner's standing grant for technical decisions with a clear precedent), the precedent and
the simpler join. Cost, stated: a later cipher of the group would hide the outcomes with the
destinations; revisit then, with the cipher.

**D3 — How "nothing recorded" differs from "nothing happened".** A plain list makes an empty one mean
both. Options: (a) a per-party `Statement<list<InvitationUse>>`; (b) an envelope-level cutover
timestamp (time-based, wrong after a restore); (c) a marker event. **Decided by the owner on 2026-10-09: (a)**:
`Stated(list)` when the party has at least one outcome or refusal fact; `Unstated(OUTCOME_NOT_RECORDED)`
when the stream has a `RecipientStepActivated` for the party's step and **no** outcome fact (every
stream written before TASK-056 is in this case, and so is an anomaly); `Stated([])` when the step never
activated, because nothing was due. `Unstated(OUTCOME_NOT_RECORDED)` states exactly what the stream
shows, that no outcome fact was recorded, and claims nothing about why. Besides pre-TASK-056 streams, the
cases that land there after TASK-056 are an activation the reactor handled after the envelope closed, a
step whose channels could reach no destination it records, and an outcome still in flight when the trail
was issued (delivery is asynchronous). For each, "not recorded" is literally true, so the branch stays.
The 2026-10-09 decision stated this case as `Unstated(NOT_RECORDED_BY_PLATFORM)`; the owner replaced it on
2026-10-14, after the closing review, with `OUTCOME_NOT_RECORDED`, a more specific reason than
`NOT_RECORDED_BY_PLATFORM`, because the platform does record invitations and the PDF would otherwise say it
does not. `NOT_RECORDED_BY_PLATFORM` keeps its meaning for the statements that use it.
The parties for whom it would be false, because the platform decided not to invite them, are D4's.

**D4 — Which routes show invitations.** Delegated and claimable parties follow the same rule: a
delegated party's step activates but it is never invited by design, so its activation without a fact
would read as unrecorded. A party whose route is `Delegated` takes `Stated([])` when it has no
invitation fact. **Decided** (2026-10-09, under the owner's standing grant): it is the trail's form of
TASK-056 §3.5, where the same recipients have invitation state `null`. A party whose route is `Claimable`,
that has **no** invitation fact and whose slot was still unclaimed when its step activated, also takes
`Stated([])`, whether its slot stayed unclaimed to its release or was claimed only after its step
activated. The activation reactor skips an unclaimed slot before recording anything, and nothing invites a
slot when it is claimed later, so in both cases the platform decided not to invite it. **Decided by the
owner on 2026-10-13**, widening the 2026-10-09 rule, which covered only the slot unclaimed at its release.
A claimable slot claimed before its step activated was due its invitation: with no invitation fact it is
D3's `Unstated(OUTCOME_NOT_RECORDED)`, and with one it is `Stated(list)` like any other.
⚑ **Changed 2026-10-14 by [TASK-037](TASK-037-claimable-invitation-and-visibility.md).** The reason above
(*"nothing invites a slot when it is claimed later"*) stopped being true: a claim on an already-active step
is now invited under the activation's own cause token. So only a slot the log **never** records as claimed
takes `Stated([])` without a fact; a slot claimed before **or after** its step activated is due its
invitation and, with no fact, is D3's `Unstated(OUTCOME_NOT_RECORDED)` — which is also true of a stream
written before TASK-037, where nothing recorded it. The decision above is kept as it was made.

## 6. Acceptance bars

Evidence-trail paths are Tier A (`tests/README.md`); worktree lane only
(`make -C ../f5sign-infra wt-backend src=$(pwd)`). <!-- OFFREPO: the ephemeral per-worktree lane is a target of the sibling repository f5sign-infra's Makefile; it mounts the given tree into its own containers and runs this repo's own test suites there, so it validates this tree rather than the main checkout. -->

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | One fixed stream fed to the assembler before and after this task yields the same `chain.root` and `leaves`; the root is pinned by a golden constant | derived — ADR-0072 §2.2 | Unit, `ChainTest` + assembler | filter the new event classes out of `AuditTrail::facts` |
| AC-2 | Each guard of the published form holds (members AC-2a…c) | derived — ADR-0072 §2.4 | Unit, goldens + `TrailJsonCompletenessTest` | see *Notes on AC-2* |
| AC-3 | Each kind of party gets the statement its stream supports (members AC-3a…f) | derived — ADR-0078 §2.5 | Application, assembler over `Factor5TrailSources` | see *Notes on AC-3* |
| AC-4 | Each stated destination is masked and resolved by log position (members AC-4a…e) | derived — ADR-0072 §2.6 | Application | see *Notes on AC-4* |
| AC-5 | `SENT` email plus `REFUSED` SMS gives two entries with their own channels, ordered by log position | derived — ADR-0078 §2.5 | Application | (inferred) sort by channel or by instant |
| AC-6 | Each outcome that is not a delivery to a destination is worded so, and carries no contact (members AC-6a…c) | derived — ADR-0078 §2.5, rule 5 (census of the outcomes) | Application + render | give it a destination or the sent wording (inferred) |
| AC-10 | Each invitation purpose is stated as itself (members AC-10a…b) | derived — ADR-0078 §2.5 | Application | state every entry as `INVITATION` |
| AC-7 | Each render guard holds with the new section (members AC-7a…c) | derived — ADR-0072 §2.1 | Integration, `TypstTrailRendererTest` | see *Notes on AC-7* |
| AC-8 | The new limitation appears exactly when a `SENT` is stated and moves no existing one (members AC-8a…c) | derived — ADR-0078 §2.5 | Unit, `PublishedCodesTest` + assembler | see *Notes on AC-8* |
| AC-9 | An envelope whose stream has activations and no outcome facts (a pre-TASK-056 stream) renders without error, its parties' invitations are `Unstated OUTCOME_NOT_RECORDED`, and its check results equal those of the same stream rendered before this task | derived — rule 6 | Integration, `RenderTrailCommandTest` shape | (inferred) fail on a missing outcome fact |
| S-1 | An envelope sent through the HTTP API and signed has its trail, downloaded from `GET /api/v1/envelopes/{id}/audit-trail`, contain the invitation entry with `EMAIL`, a masked address and the instant of the `SENT` fact | derived — ADR-0078 §2.5 | Acceptance, `AuditTrailHttpTest` shape | — |

**Notes on AC-1**
- The property that makes D1 (A) safe; it lives in `Chain::over()` and the assembler, which `ChainTest` and the assembler test both reach.
- Sabotage: the chain recompute check must redden, naming the missing leaves.

**Notes on AC-2**
- AC-2a — `schema` is asserted from the constant and stays `f5sign.audit-trail/1`. Sabotage: change the schema string.
- AC-2b — the key set of `personal` is the previous set plus `invitations`, no more; a closed set, because an extra key passes a type check. Sabotage: add a key.
- AC-2c — a party golden with no invitations still encodes `invitations` as a statement, not a missing key. Sabotage: omit the key when the list is empty.

**Notes on AC-3**
- One stream, six parties. AC-3a — outcome facts: `Stated` with its entries. AC-3b — step activated, no outcome fact: `Unstated OUTCOME_NOT_RECORDED`; sabotage: render it as an empty list. AC-3c — step never activated: `Stated([])`; AC-3b and AC-3c differ only by the activation fact. AC-3d — delegated, step activated: `Stated([])`. AC-3e — claimable and unclaimed at its release, step activated: `Stated([])`. AC-3f — claimable, claimed after its step activated, no invitation fact: `Stated([])` (D4, 2026-10-13); its fixture claims the slot by a `RecipientClaimed` fact placed after the `RecipientStepActivated`. ⚑ *Changed 2026-10-14 by [TASK-037](TASK-037-claimable-invitation-and-visibility.md): a claim on an already-active step is invited, so this case is now `Unstated(OUTCOME_NOT_RECORDED)` (§5 D4's note); the sabotage is restoring the claim-position exemption, which reddens AC-3f.* Sabotage of AC-3d/AC-3e/AC-3f: drop the route exemption, or narrow it back to the slot unclaimed at its release (AC-3f reddens).

**Notes on AC-4**
- AC-4a — an email `SENT` states `f***@***.com`-shaped output. AC-4b — a phone `SENT` states `+*********56`-shaped output. Sabotage: skip `MaskedContact::of()`.
- AC-4c — the raw address and phone appear nowhere in the encoded JSON (string search over the encoded form).
- AC-4d — a `RecipientCorrected` after the sent fact gives `CORRECTED_AFTERWARDS`. AC-4e — one before it states the current contact. Sabotage: ignore log position; AC-4d reddens.

**Notes on AC-5**
- The fixture's channel order disagrees with its time order, so a sort by channel or by instant fails.

**Notes on AC-6 and AC-10**
- AC-6a — `NOT_SENT_NO_REACHABLE_CHANNEL`. AC-6b — `DELIVERED_BY_INTEGRATOR`. AC-6c — `FAILED` (every channel failed; its event names no channel, so the entry states none). With `SENT` (AC-4) and `REFUSED` (AC-5) they are every outcome of §3.1. None of the three prints "enviada".
- AC-10a — a `RESEND` outcome is stated with purpose `RESEND`. AC-10b — the re-invitation after a correction is stated with purpose `INVITATION`, after `RECIPIENT_CORRECTED` in the party's list (TASK-056 §5 D3).

**Notes on AC-7**
- AC-7a — the new label groups are in the label census against the enums §3.4 names (`channel` against `InvitationChannel::cases()`, `invitation-outcome` against the trail's own outcome enum), and an unlabelled case fails naming it. AC-7b — a rendered trail passes the PDF/A-3a validation with its one attachment. AC-7c — `generation.template_hash` changes and the fixtures are regenerated with `tests/bin/render-trail-fixtures.php` in the same run.

**Notes on AC-8**
- AC-8a — present when a `SENT` is stated. AC-8b — absent when the only entries are `REFUSED` or unsent. AC-8c — last in the enum, so the order of every existing limitation list is unchanged.

**Notes on S-1**
- The tier is Acceptance because only the real path (delivery, relay, Envelope write port, event log, issuance) can show that the fact the trail reads is the fact production writes, which hand-built streams have already failed to show once (ADR-0072 §9).

- **Gates:** full suite, Infection covered-MSI, PHPStan, deptrac and lint green in the worktree lane.
- Nothing here signs, so `/eidas-compliance` is not needed; run `/contract-check-backend` for the published JSON.

## 7. Open follow-ups (track, don't solve here)

- **Refusals of delivered codes** are in the facts list and not in the party's section; an `OtpSent`
  with no landing is not stated as failed anywhere. Decide with the first request from a court.
  Home: [BL-418](../BACKLOG.md).
- **The cipher of the personal group** ([ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md)) will
  need D2 revisited. Home: [BL-171](../BACKLOG.md), which now names the invitations' destinations.
- **Carrier receipts** ([BL-390](../BACKLOG.md)) would let `SENT` become "delivered" in the evidence; the
  limitation of §3.5 (`DELIVERY_RECEIPT_NOT_RECORDED`) is retired then. Home: BL-390.
- **A verifier's guide** for the new key, if the JSON gains a reader outside the repository. Home:
  [BL-419](../BACKLOG.md).
- **The invitation line's printed text is unpinned** (the contact guard in `trail.typ`). Home:
  [BL-416](../BACKLOG.md), extended.

## 8. Deviations & honest notes

### Scope
- None beyond the record. The diff stays in Evidence & Audit (model, assembler, JSON, template, labels), its tests and goldens, and the records that state them. No change to `Chain`, `AuditTrail::SCHEMA`, Envelope, Notification, deptrac, PHPStan, `composer.lock` or migrations.

### Decisions made during implementation
- **Channel and purpose stay Envelope code strings in `Domain/Trail`** (owner, 2026-10-14, after considering a trail-side enum): deptrac keeps `Domain/Trail` off Envelope, so the model holds the event's own `channel` and purpose codes and the label census compares them to Envelope's `InvitationChannel` and `InvitationPurpose` in the test.
- **`OUTCOME_NOT_RECORDED` is a new `UnstatedReason`, not a reuse of `NOT_RECORDED_BY_PLATFORM`** (owner, 2026-10-14, closing review): the platform does record invitations since TASK-056, and the printed "la plataforma no lo registra" would have said it does not. §5 D3 states it; `PublishedCodesTest` pins the code.
- **D4, a step activated twice is judged by its first activation** (slice 02, round 2): a claim between two activations of the same step counts as late, so the party is exempt (`Stated([])`). The record says "when its step activated", which is ambiguous for a re-activated step, and §2 says one activation is enough. Not reachable today; accepted. ⚑ *Retired 2026-10-14 by TASK-037: the claim's position against the activation no longer matters (§5 D4's note), and P-TRAIL-219 now pins that a claim between two activations is unstated without a fact.*
- Slice 02, round 1: the claimable exemption was narrowed to "unclaimed when its step activated" to match D4 literally; slice 07 reworded the record's D4 sentence (a slot claimed before its activation with no fact is D3's unstated case).
- **AC-7c is an evidence run, not a test**: `generation.template_hash` is `ad2f0faa…` against develop's `4eb6180b…`, and `jq del(.generation)` of the regenerated fixtures diffs empty. The fixture PDFs were rendered inside the lane container, because its `var/` is not the worktree's (`docker exec` then `docker cp`).
- Slice 04: the template's `!= none` guard on an invitation's contact is load-bearing for the printed text (without it a destinationless line prints ", a —") and no test reads rendered PDF text. Kept; follow-up in BL-416.
- Slice 01's plan predicted P-TRAIL-26 red on a dropped `channel` key; it stays green until slice 03 puts an `InvitationUse` in a golden (P-TRAIL-206 guards it meanwhile). Plan error, not a defect.
- Slices 03 to 06 ran in parallel and share `TrailAssembler`; slice 06's first sabotage run was green and judged stale, the re-run was red. Slices 04, 05 and 06 were each reviewed and approved without findings, with the verdict returned rather than saved as a file; their reviewers judged each sabotage from the test's assertions, because another slice's sabotage of shared `src/` could reach a concurrent run. The full suite at d9d80e24, run with no slice editing the tree, is the run that stands for all four.

### Decisions that needed an ADR
- None. [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) gained the invitations section additively (§5 D1, A). [ADR-0078](../adr/ADR-0078-delivery-outcomes-come-back-as-facts.md) stays Proposed: it moves to Accepted with TASK-058, and this task's artifacts (P-TRAIL-209 to 223, the trail half of §2.5) are proposed there as evidence of its exercise.

### Declared and unproven properties
- AC-7c has no guard; it is the evidence run above.
- The trail PDF's printed text, including the invitation line and its contact guard, has no test: [BL-416](../BACKLOG.md).
- AC-8b is exercised with `REFUSED` and `FAILED` only; `NOT_SENT_NO_REACHABLE_CHANNEL` and `DELIVERED_BY_INTEGRATOR` alone are not asserted to omit the limitation (the predicate is `=== SENT`). Low confidence, left as is.
- Only S-1 (P-TRAIL-223) runs on a stream a real flow wrote through the HTTP API; the rest run on synthetic streams.
- Infection (filtered to the branch's `src/` files, 732 mutants, 97 % covered MSI and MSI). Four escaped on changed lines of `TrailAssembler.php`:
  - `break` in the activation loop (`Break_`): killed by P-TRAIL-219, which pins the first-activation reading of D4. ⚑ *2026-10-14, TASK-037: the loop and the claim-position check below are gone; the assembler asks only whether the step activated and whether the slot was ever claimed.*
  - `$later > $position` → `>=` in the correction check (`GreaterThan`): equivalent. A correction and an invitation fact are different log rows, and log positions are unique, so they are never equal.
  - `$found[0]->row->position < $activated` → `<=` in the claim check (`LessThan`): equivalent for the same reason; a claim and an activation never share a position.
  - `AuthMethod::tryFrom(...)?->` → `->` in `destination()` (`NullSafeMethodCall`): the expression is develop's, moved unchanged from an assignment into a `return`; every executed method the fixtures hold has an `AuthMethod`. Inherited, not introduced.
  Thirteen more escaped on lines this task did not change, and are outside its bar.

### Debt left behind, and where it lives now
- Refusals of delivered codes: [BL-418](../BACKLOG.md).
- Cipher of the personal group: [BL-171](../BACKLOG.md).
- Carrier receipts and the retirement of `DELIVERY_RECEIPT_NOT_RECORDED`: [BL-390](../BACKLOG.md).
- Verifier's guide: [BL-419](../BACKLOG.md).
- Printed-text test: [BL-416](../BACKLOG.md).
- Low-confidence residue from the closing review, left as is: P-TRAIL-218 cites AC-6a though it is a completeness pin; ADR-0072 §5's TASK-059 bullet omits P-TRAIL-36 and P-TRAIL-133.

### Delegated work
- 8 slices: 4 on opus (01, 02, 07, 08), 4 on sonnet (03, 04, 05, 06); implementation rounds 1, 3, 2, 1, 1, 1, 1, 1 for slices 01 to 08. Statuses: 01, 02, 06, 07 DONE_WITH_CONCERNS, the others DONE. Slice 08 was written by the orchestrator after the owner's ruling (plan amendment cap reached).
- No slice delegated to the replicator.

### Cost of the run
- Totals per model: only slice 01's tokens (214,690, opus) are in run.log; the other slices, reviewers, gates and close agents are not recorded.
- Rounds: 11 across 8 slices; one plan amendment.
- Escalations: none beyond the critical slices on opus; one owner-directed fix after the closing review (`OUTCOME_NOT_RECORDED`).
- Baseline 2cc11f80: 5394 tests, 60082 assertions (`wt-backend` lane, fast=1); full suite at d9d80e24: 7233 tests, 81948 assertions in 1006 s.
- Phase 7's table was not written when this was closed.
