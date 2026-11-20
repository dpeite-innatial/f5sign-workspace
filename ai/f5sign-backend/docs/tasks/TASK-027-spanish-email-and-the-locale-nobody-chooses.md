# TASK-027 — Spanish email, and the recipient locale that nothing currently chooses

<!-- OFFREPO: the templating strategy this task deliberately steps around was argued in `notes/HANDOFF-notification-templating.md`, in the private workspace repo that assembles these subrepos; it is not reachable from a backend-only checkout. Its §Parte 1 sequenced Spanish behind an ICU migration. That sequencing was re-measured against this tree on 2026-08-17 and does not hold — the reasons are restated in full in §1 and §4 D7, and nothing here needs that file read. -->

| Field | Value |
|-------|-------|
| **Status** | ✅ **Done — all three slices of §3 are in `origin/develop`.** ⚑ This line read *"pending review, not merged"* for hours after the code had landed and other sessions were building on it — [`CLAUDE.md`](../../CLAUDE.md) authoring rule 7's realization mirror, in the under-claiming direction that nobody chases because nothing breaks. Corrected 2026-08-18 once `963ad60` was confirmed an ancestor of `origin/develop`. Slice 1 landed 2026-08-17 as `852db21` on `feat/spanish-email-locale`, merged to `develop` as `e24460d`. Slices 2 and 3 landed 2026-08-18 on **`feat/recipient-locale-chain`**: `477fbdc` (sweep of the three surfaces slice 1 left stale), `e46e4f8` (slice 2 — the recipient tier), `2c09c92` (slice 3 — the tenant tier, the chain, and both `es` flips), `e41b1b5` (the frontend handoff record + the docs it falsified), `f45d3a4` + `735e453` (fixes from validation and the security audit). ⚑ **Spanish is now reachable in production and is the platform default**: `envelope.recipient.locale` and `notification.tenant_default` both exist, and neither use case holds `Locale::of($this->defaultLocale)` any more — both resolve `recipient → tenant → system` through [`NotificationTemplates`](../../src/F5Sign/Notification/Application/Service/NotificationTemplates.php). ⚑ **Harness, because a green run here is only as good as the tree it ran against:** everything below was measured by the container route over **this worktree** (`docker run --network f5sign-net` against an isolated `f5sign_test_wt`), **never** through `../f5sign-infra`'s make targets, which bind-mount the main checkout and would have validated an unrelated branch ([BL-112](../BACKLOG.md)). **1524 tests / 6277 assertions green · PHPStan level 9: 0 · Deptrac: 0 violations, 0 uncovered · php-cs-fixer: 0 of 761 · Infection covered-MSI 86% (min 79), MSI 63% (min 50).** Both migrations were applied and reverted live. Every sabotage §5 names was performed and observed failing for the right reason. **What did NOT land, and is not owed by this task:** nothing can *set* a tenant default (§6.2 — hand-inserted rows only, so the middle tier is inert on delivery), and the domain-side length bound [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §5 asks for is still owed ([BL-121](../BACKLOG.md)). §7 records the deviations and the five new deferrals; §6.7–§6.11 are their home-of-truth. The eight decisions in §4 were taken with the user on 2026-08-17 and are not open. |
| **Type** | Forward build, **product-facing** — the first recipient-visible change in the Notification BC since it shipped. A Spanish recipient currently receives English. |
| **Why** | Every notification this platform sends is English, for everyone, always. Not because the mechanism is missing — `authored()` already selects and falls back per locale — but because two things are absent: [`EmailNotificationChannel`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailNotificationChannel.php)'s `TEMPLATES` has exactly one locale key (`'en'`), and **nothing anywhere passes a locale other than the system default** — both notification use cases hardcode `Locale::of($this->defaultLocale)`, and a recipient has no language attribute to read. |
| **Builds on** | [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) (the occasion + per-channel fan-out, untouched), [ADR-0038](../adr/ADR-0038-template-archive.md) (the pin — **reused unchanged and kept green**; the archived template already carries its locale), [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md) + [ADR-0008](../adr/ADR-0008-read-side-realization.md) (the cross-BC query port this extends **additively**, opening no new dependency) |
| **Scope** | The **locale a delivery is authored in**, and the Spanish copy itself. Explicitly *not* the rendering engine, the token syntax, the archive, or the translation tooling — see §4 D7, which records why the chain those belong to was parked rather than forgotten. |
| **Decision record** | **No new ADR.** The recipient locale is an additive field on an existing declared cross-BC read port ([ADR-0008](../adr/ADR-0008-read-side-realization.md)), not a new dependency; the tenant default lands in a **Notification-owned** table (§4 D2) precisely so that stays true. ⚑ **One decision would force an ADR and is deliberately avoided:** putting the tenant default on `identity.tenant` would open Notification's second cross-BC dependency, and [repo rule 7](../../CLAUDE.md) makes that an ADR rather than a drive-by. If a later reviewer prefers that placement, it is an ADR, not a refactor. |
| **Delivery bar** | A recipient marked English receives English; a recipient marked nothing, in a tenant defaulting to English, receives English; **everyone else receives Spanish** — including a recipient marked with a locale this catalog cannot serve (§4 D8). ⚑ The bar is stated in that direction on purpose: under D8 Spanish is the *default*, so an implementation that ignores the chain entirely still passes any test whose expectation is Spanish. **English is the discriminating case now**, and §5 is built around that inversion. |
| **Sibling** | ⚑ **[TASK-024](TASK-024-notification-copy-to-twig.md) touches the same `TEMPLATES` constant and the same cartesian smoke.** They do not conflict in intent — this task adds a locale key, that one moves the markup out of heredocs — but whichever lands second rebases onto the other's edit of the same two artifacts. **The copy added here must not be re-typed by hand during that conversion**, which is exactly the accident its output-comparison bar exists to catch. ⚑ That bar was relaxed from byte-identical to **rendering-identical** on 2026-08-17 (TASK-024 §5), so it no longer catches a stray newline — it still catches a re-typed word, a lost accent or a mangled `«»`, which is what matters here. |

---

## 1. Why this task exists, and why it is not the task the handoff planned

The workspace handoff sequenced Spanish as the payoff of an ICU migration: *"Palabras a catálogos ICU. **Español entra aquí**, con plurales de verdad."* Re-measured against this tree on 2026-08-17, that sequencing does not survive, for two independent reasons. Both are restated here because the handoff is not reachable from this repository.

**First, the ICU slice cannot be built where it was placed.** It was scheduled *before* archive removal, and it cannot be: [`TemplateSyntax::TOKEN_PATTERN`](../../src/F5Sign/Foundation/Templating/TemplateSyntax.php) is frozen, and its own docblock names the collision by name — *"Every archived row is stored in this syntax, and a richer pattern (**ICU's `{token}`, say**) would not parse them."* Worse, [`NotificationChannel::authored()`](../../src/F5Sign/Notification/Domain/Port/NotificationChannel.php) takes `(purpose, locale)` and **no variables at all**, so ICU has nothing to select a plural form *with* at the point where composition happens. ICU requires formatting at transmit, which is the pin change [TASK-024](TASK-024-notification-copy-to-twig.md) §4 D3 explicitly assigns to the archive-removal slice. The two are one piece of work, not two.

**Second, and decisive for shipping Spanish: ICU buys nothing here yet.** The catalog is two purposes across two locales since slice 1, and **not one slot is a count, a number or a date** — every one is a plain substitution (`{{envelope_title}}`, `{{recipient_salutation}}`, `{{link}}`). There is no plural to get right.

⚑ **And the sentence that motivated the whole chain is not an ICU problem.** *«Acta de reunión» ha sido firmado* wants *firmada*, and ICU cannot fix it either: selecting a form requires knowing the noun's gender, and the noun is a user-supplied document title whose gender is unknowable at any point in the pipeline — which the handoff itself concedes (*"género del título desconocible, no arreglable en render"*). The fix is to **write copy that does not agree with it** (§4 D3). That is available today, at zero architectural cost.

So Spanish needs neither Twig, nor ICU, nor the archive's removal. It needs copy, and a locale to choose it with.

---

## 2. What already exists (reuse, do not rebuild)

Measured against this tree on 2026-08-17.

**The locale mechanism is complete and unused.**

- `authored(NotificationPurpose $purpose, Locale $locale)` already resolves `isset(self::TEMPLATES[$locale->value][$purpose->value]) ? $locale : DEFAULT_LOCALE` and **pins the locale it actually used**, never the one requested. Its port docblock states the property: the pin must not *"imply a translation exists when it does not"*. Adding an `'es'` key is all that side needs.
- The archived `Template` carries its locale, so a delivery pinned in Spanish renders Spanish on retry regardless of what is deployed later. **No change to the pin, the fingerprint, or the archive.**
- `NOTIFICATION_DEFAULT_LOCALE` exists as an env var wired through `notification.default_locale` to both use cases; its committed default is `en`.

**The slot for the missing chain is already marked, in the exact place, in both use cases.** [`NotifyActivatedStepRecipientsUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyActivatedStepRecipientsUseCase.php) and [`NotifyCompletedEnvelopeRecipientsUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyCompletedEnvelopeRecipientsUseCase.php) both carry:

```php
// Locale is the system default for now — recipient preference then tenant default slot in here.
$locale = Locale::of($this->defaultLocale);
```

[`NotificationTemplates`](../../src/F5Sign/Notification/Application/Service/NotificationTemplates.php)'s class docblock states the same intended chain: *"locale is the configured system default today, and recipient preference → tenant default → system"*. **This task builds precisely what those two comments describe** — the design is not being invented here, only realized.

**The cross-BC read path already carries per-recipient data.** The use cases read the envelope through `EnvelopeQueryInterface::getEnvelopeContext(...)` and iterate `$envelope->recipients`, using `$recipient->email`, `$recipient->id` and `$recipient->stepOrdinal`. So a recipient locale is **an additive field on a port that already exists and already carries recipient attributes** — not a new dependency and not a new query.

**The cartesian smoke is already widened.** `EmailNotificationChannelTest::catalogedTemplates()` iterates `(locale × purpose)` — slice 1 widened it from the purpose-only provider it used to be, and renamed it accordingly. Slices 2 and 3 add no locale, so this provider needs no further change.

**Not present, must be added (measured 2026-08-17, re-measured after slice 1):**

- ~~No `'es'` key in `TEMPLATES`.~~ **Landed in slice 1** — `TEMPLATES` now carries `en` and `es`, both covering both purposes. Kept as a record of what changed, not as outstanding work.
- **No language attribute on a recipient.** `envelope.recipient` (created in `Version20260713000002`) has no locale column, and neither does `RecipientView`.
- **No per-tenant locale.** `identity.tenant` carries `id` and `name` only.
- `Locale` itself is a permissive string wrapper — it enumerates nothing, so it constrains nothing (§4 D6).

⚑ **`settings_audit_trail_locale` already exists on the envelope and is a different thing** — the language of the audit-trail PDF, not of the email. It is the in-tree precedent for "a locale stored per envelope", and §6.3 records why the two are being kept separate despite the user's expectation that they normally agree.

---

## 3. Scope

**In, as three slices that can land in one release:**

1. **The Spanish copy.** An `'es'` key covering both purposes — `subject`, `body`, and every `html` field — written under the D3 constraint.
2. **The recipient tier.** A nullable locale column on `envelope.recipient`, surfaced on `RecipientView` / `EnvelopeQueryInterface`, and accepted by `AddRecipient` — **set once, at add time, and immutable thereafter** (his call, 2026-08-17: *"de momento se fija al añadir y es inmutable, más adelante ya editaremos ese y otros campos"*). Carries a wire-contract change: `#[OA\*]` annotations + a **handoff record file** under [`docs/frontend-handoff/`](../frontend-handoff/README.md) — `TASK-027-<slug>.md`, with that README's six-field header table and its four mandatory sections. ⚑ It is a *file*, not a row in an index, and it would be the **first** record in that directory (only `README.md` exists today), so there is no sibling to copy the shape from — read the README's §Shape.
3. **The tenant tier + the resolution chain.** A Notification-owned per-tenant default (§4 D2); the two use cases replacing their hardcoded default with `recipient → tenant → system`; **both default constants moved to `es` and the fallback-completeness guard that D8 makes mandatory.**

**Out:** the rendering engine ([TASK-024](TASK-024-notification-copy-to-twig.md)); ICU, the token syntax and the archive (§4 D7, parked); tenant-*supplied* copy, which is [BL-103](../BACKLOG.md) and needs its own record plus a token allow-list; any new purpose; any endpoint for a tenant to set its own default (§6.2); **any path that edits a recipient after it is added** — none exists today for any recipient attribute, and inventing one for this field alone is how a task grows a second subject.

⚠ **A consequence of immutability worth stating rather than discovering:** a recipient's locale can be *replayed* into a different value, because [`Envelope::addRecipient()`](../../src/F5Sign/Envelope/Domain/Aggregate/Envelope.php) does not check for an existing id and **overwrites** ([BL-69](../BACKLOG.md)). So "immutable" is a property of the API surface, not of the aggregate. His call was to leave that as it stands (*"déjalo así de momento"*); it is BL-69's to fix, and this task must not paper over it with a private per-endpoint guard — that is the one-off shape BL-69 explicitly warns against.

---

## 4. Key decisions

**D1 — The chain is `recipient → tenant → system`, and each tier is optional.** This is the user's decision of 2026-08-17 (*"por destinatario si se indica, si no por defecto del tenant"*) and it is the same chain both in-tree comments already describe. A tier that is absent is skipped, never treated as an assertion.

**D2 — The tenant default is Notification's, not Identity & Access's.** It lands in a Notification-owned table keyed by tenant, **not** as a column on `identity.tenant`. Two reasons, and the second is the load-bearing one:

- A tenant's *name* is an identity fact; a tenant's *default email language* is a notification preference. The BC that consumes it owns it.
- ⛔ **Putting it on `identity.tenant` would open Notification's second cross-BC dependency, and that is not cheap here.** Notification today reads exactly one sibling Contract (Envelope's, via `EnvelopeQueryInterface`). [BL-76](../BACKLOG.md) is the standing evidence of what opening an Identity port costs: the port that would resolve a *sender* still does not exist, and the signature that was specified for it is already wrong. This task must not be the thing that drags that question into scope.

⚠ The new table needs RLS like every other tenant-scoped table (`ENABLE` + `FORCE` + a policy on `current_tenant_id()`), and the `notification` schema must be present in **both** the conformance census and the cross-schema rule's map — [BL-106](../BACKLOG.md) records that those two are half-paired and that the gap already fired on this exact schema.

**D3 — The Spanish copy must never grammatically agree with the document title.** The title is user-supplied and its gender is unknowable, so *«{{envelope_title}}» ha sido firmado* is wrong roughly half the time and unfixable by any engine. Copy is written to sidestep agreement — *Se ha completado la firma de «{{envelope_title}}»* rather than *«{{envelope_title}}» ha sido firmado*. ⚑ **This is a standing constraint on all future Spanish copy, not a one-off phrasing choice**, and it is the reason the ICU chain would not have solved the problem it was justified by.

⚑ **Extended while writing the copy: there is a second unknowable gender, the recipient's.** It rules out *Estimado/a* exactly as the first rules out *firmado/a*. `Hola` carries no gender and `Le invitamos` is courteous without asserting one, so the greeting and the second person are both safe — but any future copy that reaches for a gendered address to the reader hits the same wall. Both halves are one rule: **nothing in this catalog may agree with a value the platform does not know.**

**The constraint is enforced, not merely written down** — `EmailNotificationChannelTest::no_spanish_copy_makes_the_envelope_title_the_subject_of_an_agreeing_verb` walks every Spanish part of every purpose and reddens on a verb directly following the closing quote. ⚠ It is a tripwire on the known failure shape, not a proof of grammaticality; reviewing new Spanish copy stays a human act.

**Three register decisions, taken 2026-08-17 and not open:** `usted` throughout · Spanish quotation marks `«»` (`&laquo;`/`&raquo;` in markup), deliberately diverging from the English `&ldquo;`/`&rdquo;` because they are different languages, not an inconsistency · `FIRMA COMPLETADA` where the English says `DOCUMENT COMPLETED`, because an envelope can carry several documents and the English is imprecise there.

**D4 — An absent locale means "not indicated", identically on old rows and new ones.** The recipient column is nullable with no backfill and no default. A pre-existing recipient reads exactly as a newly-authored one that declined to state a language: fall through to the next tier. ⚑ [`CLAUDE.md`](../../CLAUDE.md) authoring rule 6 asks what a migration-written row *means* in every aggregate state — the answer here is that the migration writes **no rows at all**, which is what makes the semantics uniform across draft, in-flight and completed envelopes. **Do not add a backfill or a column default**; either one would convert "not stated" into a false assertion on every envelope that predates this task.

**D5 — The fallback's honesty property is preserved; only the locale it falls back *to* moves (D8).** `authored()` continues to pin the locale it *used*, never the one requested. So a recipient marked `fr` — which this catalog does not author — is pinned `es`, and the pin says `es`. ⚑ That property is what stops D8's "no validation" from becoming a lie: nothing anywhere claims a French delivery happened.

**D6 — `es`, not `es-ES`, and the authored set is `en` + `es`.** Region-neutral until a region actually diverges. ⚠ `Locale` enumerates nothing, so **nothing stops a caller storing `pt-BR` today** and nothing will report it. That is now a decision rather than a gap — see D8.

**D7 — The ICU / archive chain is parked, not abandoned.** Decided with the user 2026-08-17, on the §1 finding that it buys no product today. ▶ **What would force it:** the first copy carrying a real count, number or date; or the translation *process* becoming the bottleneck (today a `const` in an infrastructure class is a pull request, which is tolerable for two purposes in two locales and stops being tolerable well before twenty). ⚑ **When it is un-parked it is one task, not the handoff's two** — words and archive removal together, for the §1 reason. It is indexed as [BL-111](../BACKLOG.md).

**D8 — An unserveable locale is not rejected; it falls back, and the fallback is Spanish.** His call, 2026-08-17: *"si alguien mete un idioma que no tenemos, primero culpa nuestra por no validarlo antes, y segundo, como tiene que salir, fallback a español y ya."* Validation was considered and dropped — ⛔ **and the option this task originally proposed was not merely expensive, it was illegal.** §6.6 first suggested validating at Envelope's write edge against Notification's authored set; no Envelope layer lists `NotificationContract` in [`deptrac.yaml`](../../deptrac.yaml), and [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) makes Notification a category-(c) BC nothing may depend on. A shared `Foundation` locale registry would have been the legal shape and is what makes rejection cost an ADR; a message that always goes out costs nothing.

⚑ **"Spanish" means two different constants, and conflating them is the way to get this wrong.** Both move, deliberately:

| Constant | Today | Becomes | What it decides |
|---|---|---|---|
| `NOTIFICATION_DEFAULT_LOCALE` (`.env`) | `en` | `es` | The chain's **last tier** — what a recipient nobody described receives |
| `EmailNotificationChannel::DEFAULT_LOCALE` | `en` | `es` | The **catalog fallback** — what an unauthored `(purpose, locale)` pair renders as |

⚠ **This flips the product's default language, and that is a bigger change than the word "fallback" suggests**: today *every* recipient receives English, because nothing supplies a locale. It is stated here so the size of it is on the record rather than discovered from an inbox.

⛔ **It also creates an invariant nothing currently guards: the fallback locale must be complete.** `authored()` reads `TEMPLATES[$resolved][$purpose]` with no net, so a purpose authored only in English while the fallback is `es` is a crash, not a degradation. Both locales cover both purposes today, so the flip is safe **now** — the guard is what keeps it safe, and it is owed in the same changeset: assert every `NotificationPurpose::cases()` is present under `DEFAULT_LOCALE`. That is a different property from the cartesian smoke, which checks the pairs that *exist* rather than the ones that must.

⚑ **Two existing artifacts state the old behaviour and must move with it**, not be left to rot: `EmailNotificationChannelTest::an_uncatalogued_locale_falls_back_to_the_authored_one_and_says_so` asserts `'en'` and `'Hello'`, and its docblock explains *why* that branch matters. Change the assertions **and** the prose.

---

## 5. Verification

The properties here are hermetic except the column and the chain, so the per-worktree lane's missing MinIO and RabbitMQ do not weaken this slice ([`README.md`](README.md) §6).

| Property | Harness | Slice |
|---|---|---|
| Every `(purpose × locale)` pair renders with no unresolved slot | `Notification/Unit` — the cartesian smoke | 1 — **landed**, `catalogedTemplates()` |
| The English output is **byte-identical** to before | `Notification/Unit` — the existing subject and escaping assertions, unedited | 1 — **landed** |
| A Spanish `subject` survives `escapeHtml()` with its accents intact | `Notification/Unit` — `spanish_copy_survives_the_escaping_path_with_its_accents_and_guillemets` | ⚠ **marked landed in slice 1 with nothing behind it; landed for real in `f45d3a4`.** Slice 1 ticked this row without writing the assertion: the pre-existing escaping test renders `en` with an ASCII payload, and the Spanish acceptance assertions are accent-free prefixes, so a mangled `«»` or a dropped accent reddened nothing. Recorded rather than quietly re-ticked, because this is the *over*-claiming direction and it survived a whole merge. |
| A recipient locale wins over the tenant default, which wins over the system default | `Notification/Application` (hermetic, fakes for the query port) — 4 methods in `NotificationTemplatesTest` (tiers `fr` / `de` / `en`, mutually disagreeing) **+** `each_addressee_is_authored_in_the_locale_the_chain_resolved_for_them` in both use-case tests | 3 — **landed** (`2c09c92`) |
| Every `NotificationPurpose::cases()` is present under `DEFAULT_LOCALE` (D8's completeness invariant) | `Notification/Unit` — `every_purpose_is_authored_in_the_fallback_locale` | 3 — **landed** (`2c09c92`) |
| The column round-trips and a NULL means "not indicated" | `Envelope/Integration` — real DB — `RecipientLocalePersistenceTest::a_stated_locale_round_trips_and_an_unstated_one_stays_null` **+** `an_unrelated_later_write_does_not_erase_a_recipients_locale` | 2 — **landed** (`e46e4f8`) |
| The new tenant-default table carries RLS (`ENABLE` + `FORCE` + a `current_tenant_id()` policy) | `Integration` — the existing schema-conformance census (`notification` was already in `BC_SCHEMAS`, so the table entered it with **no edit to the test**) **+** `DbalTenantNotificationDefaultsTest::one_tenants_default_is_invisible_to_another` against the live DB under the non-superuser `f5sign_app` role | 3 — **landed** (`2c09c92`) |

⛔ **The discriminating case is the one a careless fixture destroys, and it is this task's whole risk.** [`CLAUDE.md`](../../CLAUDE.md) authoring rule 4: *a fixture whose variables always agree cannot fail.* If the recipient, the tenant and the system default all say `es`, then a chain that reads **only** the system default passes every assertion and ships. The chain test must be built on three tiers that **disagree**, and each tier dropped in turn.

⚑ **D8 makes that trap sharper in two ways, and both are easy to walk into.**

- **Spanish is now the default, so a Spanish expectation proves nothing.** An implementation that ignores the chain entirely still returns `es` for almost every fixture. **The load-bearing assertions are the ones expecting `en`** — the tier that has to be *read* to be honoured.
- ⛔ **Assert what the chain RESOLVED, not what the catalog PINNED — they are two different steps and the second masks the first.** A fixture like *system default `fr`* does not prove the system tier was read: `fr` is unauthored, so `authored()` falls back and pins `es`, which is what a chain that read nothing would also produce. Either assert the locale the chain handed to `pinFor(...)` before `authored()` touches it, or build every tier out of **authored** locales. With only `en` and `es` authored, three mutually-disagreeing authored tiers do not exist — so the resolution has to be observed at its own seam, not through the rendered output.

⚠ **Spanish accented copy meets the escaping path**, which is fine by construction and worth one assertion rather than an assumption: `escapeHtml()` is `htmlspecialchars(..., ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')`, and `TemplateSyntax::TOKEN_PATTERN` is deliberately non-`/u` because *token names* are ASCII — the copy around them need not be. Assert that a Spanish `subject` survives the round trip with its accents intact.

**Sabotage before trusting the green run:**

1. Point the chain at the system default only. The three-tier test must redden **naming the tier it skipped**, not merely mismatching a string. ✅ **Performed 2026-08-18, in both halves.** (1a) `localeFor()` made to return the tenant default — 6 failures, diff `-'fr' +'de'`, message *"the recipient who stated a language gets it…"*. (1b) `tenantDefault()` made to return the system default — 4 failures, diff `-'de' +'en'`. Both name the skipped tier rather than mismatching a string; tree restored.
2. ✅ **Performed in slice 1** — an `'es'` slot was misspelled and the cartesian smoke reddened naming the pair. Not re-owed by slices 2–3, which add no locale. The slice-3 equivalent is sabotage 4 below.
3. Request an unauthored locale (`fr`). The pin must say **`es`** — proving D5's honesty property survives the D8 flip: the pin names the copy that was actually sent, never the locale that was asked for. ⚠ Do **not** write this sabotage as "remove the `'es'` key": under D8 `es` *is* the fallback, so removing it is not a fallback test but the crash D8 names as its own invariant. Sabotage that separately — that is sabotage 4. ✅ **Performed 2026-08-18** — `authored()` made to stop falling back (`$resolved = $locale`); both fallback tests error out, so the guards do notice.
4. Remove one purpose from the fallback locale's block. The **completeness guard** (§5 table, slice 3) must redden naming the missing `(DEFAULT_LOCALE, purpose)` pair — not blow up with an undefined-key error from somewhere down in `authored()`, which is the crash the guard exists to pre-empt rather than reproduce. ✅ **Performed 2026-08-18, and a second limb was found worth sabotaging too.** (4) `ENVELOPE_COMPLETED` renamed inside the `es` block — the guard fails as an `assertContains` reading *"the fallback locale \"es\" does not author ENVELOPE_COMPLETED. authored() indexes TEMPLATES[fallback][purpose] with no net…"*, **not** an undefined-key crash. (4b) `DEFAULT_LOCALE` set to the unauthored `'fr'` — the guard's first limb fails with *"the fallback locale \"fr\" is not authored at all — it has nowhere to fall back to"*, closing the hole the cartesian smoke structurally cannot see.

---

## 6. Open follow-ups (track, don't solve here)

1. ⚑ **NOT a follow-up — this one is in scope and §3 slice 2 requires it in the same changeset.** It is listed here only because the *adoption* half lands in another repo. Authoring a recipient gains an optional language, which is a published-contract change, so it owes its `#[OA\*]` annotations (emitted verbatim into the spec the frontend team ratifies) **and** a handoff record file under [`docs/frontend-handoff/`](../frontend-handoff/README.md) — see §3 slice 2 for its required shape. What genuinely defers is only the dashboard/signer side, which is a separate PR in a separate repo by that directory's own rule. ✅ **The in-repo half is DONE (2026-08-18, `e46e4f8` + `e41b1b5`).** Both `#[OA\*]` surfaces carry the field and `OpenApiSpecTest`'s closed-key-set check gates it in both directions; [`docs/frontend-handoff/TASK-027-recipient-locale.md`](../frontend-handoff/TASK-027-recipient-locale.md) is the first record in that directory and conforms to the README's six-field header and four mandatory sections. **The dashboard/signer adoption is still open and is not this repo's to close.**
2. **Nothing can set a tenant's default, and that is confirmed rather than overlooked** (his call, 2026-08-17: *"si, de momento solo a mano"*). The table lands with no endpoint and no provisioning path. ⚠ **So the middle tier is inert on delivery and its test is the only thing exercising it** — which under D8 is doubly worth stating, because a tenant tier that silently never fires is indistinguishable from one working correctly when the answer is Spanish either way. ▶ What would force an endpoint: the first tenant that is not Spanish-speaking.
3. **Audit-trail locale and notification locale are independent, and neither defaults from the other — decided, not deferred.** His call, 2026-08-17: *"no hereda del campo `settings_audit_trail_locale`, son campos distintos que se editarán o se enlazarán de alguna forma en el futuro."* So `settings_audit_trail_locale` is **not** read by this task and is not a fallback tier: the chain is exactly `recipient → tenant → system` (D1) and nothing else. ⚠ **The consequence stays true and is nobody's bug**: an envelope can carry a Spanish audit trail and an English email, or the reverse, with nothing warning anyone. Under D8 that is now unlikely rather than impossible — both sides land on Spanish by default — which is precisely why it would go unnoticed if it ever stopped being unlikely. ▶ What would force the link: a tenant that sets one and expects the other to follow.
4. **The ICU / archive chain, parked under D7** — [BL-111](../BACKLOG.md) carries the forcing condition and the finding that it is one task rather than two.
5. **Tenant-supplied copy ([BL-103](../BACKLOG.md)) will land beside D2's table** and must not be folded into it opportunistically: it needs a revision model and a mandatory token allow-list per `(channel, purpose)` validated on save, without which a tenant edit can name a slot the code does not supply and silently arm a delivery failure.
6. **A locale the catalog cannot serve is accepted, not rejected — decided, not deferred** (D8). It degrades to Spanish and the pin says `es` (D5), so nothing claims a delivery that did not happen; what is *not* available is a signal that the caller asked for something we do not have. ⛔ **This entry previously proposed validating at Envelope's write edge, which deptrac forbids** — no Envelope layer lists `NotificationContract` — so anyone re-opening this should start from the `Foundation` locale-registry shape (and its ADR), not from that suggestion. ▶ What would force it: a tenant complaining that they configured French and got Spanish with no error.

⚑ **Items 7–11 were surfaced by this task's own validation and security passes (2026-08-18) and are its new deferrals.** Each is indexed from [`docs/BACKLOG.md`](../BACKLOG.md); this section is the home-of-truth and the BACKLOG row only points here.

7. **The domain-side length bound on `Locale` is owed, and the gap is repo-wide rather than this field's.** [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §5 permits `TEXT` **because** it relocates the length bound to the value object — *"a string unbounded everywhere is forbidden"* — and [`Locale::of()`](../../src/F5Sign/Foundation/Templating/Locale.php) enforces none, so that relocation has not happened. ⚠ **What landed here is a ceiling at one edge, not the bound the ADR wants**: `AddRecipientRequest::$locale` carries `#[Assert\Length(max: 35)]` (`735e453`), so a writer that does not go through the HTTP edge — the hand-written `notification.tenant_default` row is exactly one — is still unbounded. ⛔ **Do not close this by adding a bound to `Locale` alone.** The same hole is open on `AddRecipientRequest::$full_name` (the *same payload*, with no constraint at all), `CreateEnvelopeRequest::$title`, and `AddDocumentRequest`'s `$name` / `$display_name` / `$mime_type`; neither `Envelope::title` nor `Recipient::fullName` carries a domain bound either. The compliant precedent in the same tree is `AddFieldRequest::$label` / `$anchor_text` (`Length(max: 255)`) and `VoidEnvelopeRequest::$reason` (`Length(max: 1000)`). So this wants **one decision about `Foundation` value objects**, not six drive-bys. ⚠ **Impact today is bounded and was measured, not assumed**: the value is reachable only by an authenticated tenant principal under RLS, is never rendered into an email, logged, put in a `Contract/Event` payload, a URL or an error body, and never becomes the *pinned* locale. The residual is permanent storage bloat plus `GET` amplification — permanent because §3 gives the field no edit path. ▶ What would force it: any of these fields becoming reachable by an unauthenticated or lower-trust caller, or the ADR-0019 conformance census growing a bound check. → [BL-121](../BACKLOG.md).
8. **`DbalTenantNotificationDefaults` passes the stored tag through un-normalized, so a hand-typed `' en '` silently gives a tenant the opposite of what they configured.** The adapter guards blankness (`trim($locale) !== ''`, so a `' '` row is read as *absent* rather than throwing inside the fan-out) but deliberately does **not** normalize the value: `' en '` reaches `Locale::of()` verbatim, matches no authored catalog key, and degrades to the D8 fallback — Spanish. ⛔ **The severity comes from §6.2, not from the string handling**: hand insertion is the *only* writer this table has, so the person capable of typing a stray space is the only person who ever writes here, and the failure is silent in both directions (no error, and Spanish is also the correct answer for almost everyone). ⚠ **Left as-is on purpose rather than fixed in passing.** `Locale::of()` stores tags verbatim everywhere in the tree, so normalizing them *here* would make one adapter disagree with the type — and normalizing tag *values* is the edge of the validation D8 explicitly declined, whose legal shape is a shared `Foundation` locale registry costing an ADR (§6.6). A `CHECK (locale = btrim(locale))` on the column is the cheap containment if this bites before the registry exists; the migration is still local and unpushed, so its SQL remains editable under repo-specific rule 2. ▶ What would force it: the first tenant default that does not take effect. → [BL-122](../BACKLOG.md).
9. **The tenant tier is inert on delivery, and that is now a shipped state rather than a plan.** §6.2 recorded the decision; this records its consequence after the code landed. `notification.tenant_default` exists, carries RLS, is read once per occasion batch, and **nothing in the application writes it** — no endpoint, no provisioning path, no console command. So in production the chain is effectively `recipient → system`, and the middle tier is exercised only by its tests and by an operator with `psql`. ⚠ **Under D8 this is indistinguishable from a working tier**: with the system default also `es`, a tenant tier that never fires and a tenant tier that fires correctly produce the same email. ⚑ Both published `#[OA\*]` descriptions now say so in the spec itself (*"no API sets a tenant default yet"*), and the frontend handoff leads with *"No construir una pantalla de ajustes del tenant contra este campo"* — so the gap is disclosed on the surfaces that would otherwise imply a configurable setting. ▶ What would force an endpoint: the first tenant that is not Spanish-speaking. → [BL-123](../BACKLOG.md).
10. **`EmailNotificationChannel::fallbackLocale()` has no production caller, so the covered-MSI figure does not speak for it.** It exists so the completeness guard follows `DEFAULT_LOCALE` instead of restating today's value — which is the right design and is why it has no caller — but Infection can only mutate what a test *reaches through the code under test*, so the 86% is silent about this method. What actually holds it is sabotage 4b (§5), which set `DEFAULT_LOCALE` to an unauthored `'fr'` and watched the guard's first limb redden. ⚑ **Recorded because the number is the thing people quote**: "86% covered-MSI" will be read as covering everything this changeset added, and it does not cover this. `authoredPurposes()` is the near-miss worth contrasting — same file, same guard, but it *is* called from the guard's body, so its mutants are attempted. ▶ What would force a change: `fallbackLocale()` acquiring a second consumer, at which point it stops being a test-facing accessor and owes a normal test. → [BL-124](../BACKLOG.md).
11. **The `lang=` escape is deliberately unobservable through the public API, so Infection reports it as an escaped mutant by design — do not "fix" it.** `htmlLayout()` now emits `<html lang="{$lang}">` with `$lang = self::escapeHtml($locale->value)` (`735e453`). No authored locale contains a character `htmlspecialchars` touches, and `authored()` only ever hands the layout a catalog key or `DEFAULT_LOCALE`, so **no test reachable through the public API can separate the escaped call from the bare interpolation.** ⛔ **That is the expected signal for a defence-in-depth guard, not a missing test**, and the plausible cleanup — deleting the escape because a mutation report says nothing kills it — is the failure mode [`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) exists to pre-empt: a guard that looks like dead weight and is not. It is not on that file's `§2 Never` list because nobody has proposed removing it yet; if someone does and it is argued down, that is where the argument belongs. It earns its place because this task is what first made the locale **client-supplied**, and because the `html` part is archived and fingerprinted ([ADR-0038](../adr/ADR-0038-template-archive.md)): a regression in the upstream predicate would not spoil one email, it would write attacker-controlled markup into the template archive under a pin. ⚑ Containment was probed rather than reasoned — six hostile tags (XSS, attribute break, CRLF, 100k characters, numeric-string key coercion, and an unauthored `fr`) all pinned `es` and rendered `lang="es"`, with an authored `en` alongside as the control that still passes through as itself. ▶ What would force a test: the day the escape becomes observable is the day the upstream constraint has already failed. → [BL-125](../BACKLOG.md). ⚑ **Update 2026-08-18 ([TASK-024](TASK-024-notification-copy-to-twig.md)) — the mechanism above is retired, the property is not.** `htmlLayout()` no longer exists: the sink moved to `templates/notification/layout.html.twig` as `<html lang="{{ view.lang }}">`, and Twig's autoescaping is what escapes it — held by the engine rather than by a line, which is strictly better. The paragraph above is kept as the record of why the guard was placed, not as a description of where it now lives; BL-125 carries the current one.

---

## 7. Deviations & honest notes

*Written at close, 2026-08-18, from the run's own reports. Added as the last section on purpose: §1–§6 are
cited as `§N` anchors from ADRs, sibling tasks and source docblocks, so nothing above was renumbered.*

### Scope

- **Nothing landed in an `Out` bucket**, and both of §3's explicit prohibitions held in code as well as in
  prose: no recipient-**edit** path was invented (the Envelope diff touches only `AddRecipient` /
  `AddRecipientUseCase` / `AddRecipientController` / `AddRecipientRequest`; no new command, no `PATCH`), and
  no private per-endpoint guard was added against [BL-69](../BACKLOG.md)'s replayed-add overwrite —
  `Recipient::locale()`'s docblock names the row and says *"do not paper over that with a guard here"*.
- **Four files outside §3 were edited, all authoring-rule-1 sweep targets rather than scope creep:**
  [`docs/LIVE_SCHEMA.md`](../LIVE_SCHEMA.md) (both new surfaces),
  [`docs/ddd/notification-domain-model.md`](../ddd/notification-domain-model.md) (two claims this change
  falsified, including the *"Locale resolution"* deferral, now struck as resolved),
  [`docs/BACKLOG.md`](../BACKLOG.md) ([BL-111](../BACKLOG.md)'s wording) and
  [TASK-024](TASK-024-notification-copy-to-twig.md).
- **One file outside §3 that is genuinely new**: `docs/frontend-handoff/TASK-027-recipient-locale.md`, the
  first record in that directory — required by §3 slice 2, listed here because §3 described it as a
  deliverable rather than as a path.

### Decisions taken during implementation

- **The chain lives in [`NotificationTemplates`](../../src/F5Sign/Notification/Application/Service/NotificationTemplates.php), not in a new service.** Its own docblock already claimed resolution
  (*"it needs one home, and this is it"*), so this adds no realization pattern — and it **removes** a
  duplication, since the system default had been bound onto both use cases separately.
- **Two methods on that service, not one.** `tenantDefault(TenantId)` is read once per occasion batch and
  `localeFor(?Locale, Locale)` once per addressee, because the completion reaction fans out over every
  recipient and a per-recipient tenant read would have been N queries.
- **No memoization in the adapter.** §6.2/§6.9 make the row hand-written, so a worker-lifetime cache would
  hide an operator's edit until restart — the one failure mode worth avoiding on a table only a human writes.
- **All new parameters are trailing optionals** (`Recipient::create`, `Envelope::addRecipient`,
  `AddRecipient`), because those have positional call sites across roughly twenty test files.
- **`LogNotificationChannel::DEFAULT_LOCALE` stays `en`, and that is authoring rule 5 applied rather than an
  oversight.** The tree holds three `DEFAULT_LOCALE`-shaped constants; D8's table names the two that move,
  and the third authors a locale-independent diagnostic dump — its own docblock says *"a diagnostic dump
  reads the same in every language"*.
- ⚠ **`Scenario01SingleRecipientHttpTest`'s copy assertions moved from English to Spanish, and §5's
  "byte-identical English output" row is still true where it is scoped.** That row targets
  `Notification/Unit`'s catalog-rendering assertions, which are untouched and still request `Locale::of('en')`
  explicitly. The acceptance scenario adds a recipient with no language into a tenant with no row, so after
  the D8 flip it *must* land on Spanish — keeping its English assertions was not an option, and asserting
  Spanish there is the acceptance-level evidence that the platform default really moved. Nothing was dropped
  in the swap and one guarantee was added (the no-download promise is now asserted in Spanish too).
- ⚠ **`EmailNotificationChannelTest::an_uncatalogued_locale_falls_back_…` had its assertions changed from
  `en`/`Hello` to `es`/`Hola`.** This is not a weakened test: D8 ordered it explicitly (*"two existing
  artifacts state the old behaviour and must move with it"*), the prose moved with the assertions, and the
  case stays discriminating because `fr` is authored by nothing, so requested ≠ used whichever language the
  fallback is.

### Decisions that needed an ADR

- **None**, and that was verified rather than asserted. `deptrac.yaml`, `phpstan.dist.neon`,
  `phpstan-baseline.neon`, `infection.json5.dist`, `phpunit.dist.xml`, `composer.json` and `composer.lock`
  are all untouched; Deptrac's `Allowed` count rose 3755 → 3809 purely because the new classes are *covered*
  by existing rules, not because an allowlist widened. The `TenantNotificationDefaults` port imports only
  `Foundation` (`TenantId`, `Locale`), which `NotificationDomain` already allows, and Envelope's new `Locale`
  imports resolve to `Foundation`, already allowed on all four of its layers — **so no cross-BC edge was
  opened**, which is exactly what the `Decision record` field promised. The one placement that *would* have
  forced an ADR — putting the tenant default on `identity.tenant` — is the one D2 declined.
- ⚑ **No ADR moved from `Proposed` to `Accepted` either, because none was owed.** Both ADRs this task builds
  on are already `Accepted — realized`: [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) and
  [ADR-0038](../adr/ADR-0038-template-archive.md). ADR-0037's `Deferred` list names *"the full purpose
  catalog and real i18n"* — this task **advances** that (a second authored language and a real resolution
  chain) without **discharging** it (no ICU, no translation process; the catalog is still a `const` in an
  infrastructure class, parked under D7 / [BL-111](../BACKLOG.md)), so the deferral stays as written.

### Properties declared and not proved

- **Both remaining ones were closed before this section was written, and are recorded because the
  *over*-claim survived a merge.** §5's *"a Spanish `subject` survives `escapeHtml()` with its accents
  intact"* row was ticked `1 — landed` in slice 1 with **no assertion behind it**: the escaping test rendered
  `en` with an ASCII payload and the Spanish acceptance assertions were accent-free prefixes, so a mangled
  `«»` or a dropped accent reddened nothing. `f45d3a4` added
  `spanish_copy_survives_the_escaping_path_with_its_accents_and_guillemets`, which asserts the guillemets and
  the accent verbatim in the text part, `&laquo;` present and `&amp;laquo;` absent in the markup. The §5 row
  now says so rather than carrying a clean tick.
- **`down()` reversibility was declared unverified by the validation pass and has since been measured.** The
  migration commands were blocked by the permission classifier during validation; both migrations were
  afterwards applied and reverted live (`down()` removes both surfaces; `up()` restores `locale`
  text/nullable/no-default and `tenant_default` RLS enabled + forced).
- **Everything else in §5 executed.** Each row was matched by test name against the run's JUnit output, and
  the four properties this task added were sabotage-confirmed (§5, sabotages 1, 3, 4 and 4b).

### Debt left, and where it lives now

| What | Home-of-truth | Index |
|---|---|---|
| The domain-side length bound `ADR-0019` §5 wants, repo-wide across six fields | §6.7 | [BL-121](../BACKLOG.md) |
| The un-normalized tenant tag (`' en '` → silent Spanish) | §6.8 | [BL-122](../BACKLOG.md) |
| The tenant tier being inert on delivery | §6.9 | [BL-123](../BACKLOG.md) |
| `fallbackLocale()` having no production caller, so covered-MSI is silent about it | §6.10 | [BL-124](../BACKLOG.md) |
| The `lang=` escape being unobservable by design (Infection reports it escaped) | §6.11 | [BL-125](../BACKLOG.md) |

**Pre-existing and explicitly *not* this task's**, listed so the close is not read as an all-clear: ten open
composer advisories (1 HIGH `symfony/http-kernel`, 5 MEDIUM, 3 LOW, 1 `null`-severity `symfony/runtime` that
lets a request set `APP_ENV`/`APP_DEBUG`) — `composer.lock` is untouched and repo rule 1 forbids regenerating
it unasked; PII at rest is still unencrypted (`FieldCipher` has zero callers,
[ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md) is `Proposed`) and this diff adds no strongly
personal column; `GET /api/doc.json` is still public in production ([BL-63](../BACKLOG.md)), which now
publishes two more field descriptions; and no rate limiter is installed anywhere in this backend.

**Process friction worth naming once:** Infection's initial test suite was flaky in this harness across four
attempts — one memory exhaustion (Infection does not inherit the outer `-d memory_limit=-1`), one killed by a
*foreign concurrent `phpunit` run from another session* against the same `postgres-test` and the same broker,
one green, one failing in an untouched relay test under random order. The reported MSI is from the clean
attempt, and the session subsequently moved to an isolated `f5sign_test_wt` database. This is environmental
and is close kin to [BL-108](../BACKLOG.md) (no CI runs any of this) and [BL-112](../BACKLOG.md) (worktree
tooling), rather than a new row.
