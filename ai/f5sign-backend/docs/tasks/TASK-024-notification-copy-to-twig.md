# TASK-024 — Email layout to Twig, without changing the email

<!-- OFFREPO: the decision this task executes was argued in `notes/HANDOFF-notification-templating.md`, in the private workspace repo that assembles these subrepos; it is not reachable from a backend-only checkout. Every fact this task depends on is restated below, including the measurements (the ~2.3 min behavioural footprint of the pin, which `config/packages/messenger.yaml` states in its own comment) and the user's 2026-08-11 confirmation that no evidentiary reproduction is required. Nothing here needs that file read. -->

| Field | Value |
|-------|-------|
| **Status** | **Done** — implemented on `feat/notification-email-twig-layout` and merged to `develop` 2026-08-18. `make qa` green on the merged tree: 1573 tests, PHPStan level 9 clean, deptrac 0 violations, covered-MSI 86% (gate 79). The bar held with the three pinning tests' **bodies** unedited; what did change in that file is the private `channel()` helper, which gained the Twig environment the constructor now takes — see §7.1. ⛔ **One scope item was not delivered and cannot be** — §3's fifth, *removing the `x` / `x_html` twins* (§7.2). ⚑ **The design decision it executes was taken 2026-08-11** and lived only in a workspace handoff until this record; that handoff is committed in the workspace repo (`notes/HANDOFF-notification-templating.md`), and every fact it carried that this task depends on is restated here. |
| **Type** | Enabling, mechanism-only. Swaps the rendering engine for the `EMAIL` channel's HTML part and changes **nothing a recipient can see** — the acceptance bar is **rendering-identical** output (§5; it was byte-identical until 2026-08-17, and the reason it could be relaxed is dated there). ⚠ **Re-based 2026-08-17 — this field previously read *"it exists to make the next slice (words to ICU catalogs) possible at all"*, and that justification no longer holds:** the ICU chain was parked ([BL-111](../BACKLOG.md)) once it was measured that it buys no product today and cannot be sequenced where it was placed. **Two reasons survive, and they are enough.** (1) The markup is ~400 lines of heredocs inside an infrastructure class, which is a maintenance cost independent of what the words are made of. (2) `Sibling` below: TASK-022 adds the first new purpose since the BC shipped, and authoring it against the mechanism this task retires writes it twice. |
| **Why** | [`TemplateSyntax::TOKEN_PATTERN`](../../src/F5Sign/Foundation/Templating/TemplateSyntax.php) is `/\{\{(\w+)\}\}/` and admits **variable names only**. No plural form, no gender, no ordinal, no conditional — so 20 locales are unreachable, and it is already wrong in the one non-English locale the product needs: *«Contrato Q3» ha sido firmado* is correct and *«Acta de reunión» ha sido firmado* is not (it wants *firmada*). ⛔ **Corrected 2026-08-17 — that example was cited here as evidence for the syntax being the constraint, and it is not evidence for it.** The title's gender is user-supplied and unknowable at **every** point in the pipeline, so no engine can select the form: ICU could not have fixed it either, and the repair is copy that does not agree with the title ([TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md) §4 D3). The frozen-syntax fact above stands on its own — plural, ordinal and locale-correct number and date formatting are genuinely unreachable — but this task is no longer justified by it (see `Type`), and Spanish did not wait for it. |
| **Builds on** | [ADR-0037](../adr/ADR-0037-notification-supporting-bc.md) (the occasion + per-channel fan-out, untouched here), [ADR-0038](../adr/ADR-0038-template-archive.md) — **its pin only**, reused unchanged and kept green; the part of 0038 this task *contradicts* is its §Counterpoint, which is why it also appears under `Decision record` below — and [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md) (the placeholder/real channel duality) |
| **Scope** | The **HTML part of the `EMAIL` channel only.** Words stay exactly where they are, in `TEMPLATES`. The archive stays. The occasion aggregate, its states, the fan-out policy, the channel failure contract and every event payload stay **untouched** — `DeliveryRequested` is a thin pointer and carries no content, so none of this reaches the wire. |
| **Decision record** | [ADR-0052](../adr/ADR-0052-twig-layout-composition.md) — **`Accepted — realized` as of this task**, which is the exercise that promoted it (that promotion, its `Enforced by` and its `Realized in` are part of this changeset, per [`CLAUDE.md`](../../CLAUDE.md) authoring rule 7). It was `Proposed` while this plan was written, which is why the sections below argue as if it were. ⚠ **This field previously read *"owes a new ADR, and it lands in this changeset"*, with instructions to mint the number; that is done, so do not mint a second one.** ⚑ **Read §2.1–§2.4 of it before writing a template**, because it moves the ground under §4 D1–D3 below: the retraction of ADR-0038's Twig strike is scoped to *layout composition*, on the ground that the strike was ruling on the substitution seam and this adoption declines to put Twig there. Two consequences for the work — `strict_variables: true` is not in tension with *survives verbatim* (different layer, opposite right answer), and no Twig source may ever reach an archived row. ADR-0038 stays `Accepted — realized` here and is superseded only when the archive actually goes (§6). |
| **Delivery bar** | `make qa` green **with §5's three pinning tests unedited** (widening the cartesian smoke is a scope item, not a relaxation — §5 states why the two are not in tension), and `templates/notification/` is where the markup lives. |
| **Sibling** | ⚑ **TASK-022 introduces the first new purpose since the BC shipped.** ⚠ **Its branch has since merged**, so it is [TASK-022](TASK-022-delivered-codes-over-email.md) here, not the unreachable record this row described; the sentence that said otherwise is corrected rather than deleted because the sequencing it argued still holds. It plans — an `OTP_EMAIL` code delivered through Notification. Do not scope these independently: if the OTP variant is authored against the heredoc mechanism this task retires, it is written twice. Its body block is the wireframe's large monospaced code, which is exactly the slot §2 describes. |

---

## 1. Why this task exists

Three forces, none of which the current mechanism can absorb:

1. **Plurals and gender, above.** The frozen token syntax is the binding constraint, not the renderer.
2. **No translation flow.** The catalog is a PHP `const` in an infrastructure class. No TMS (Crowdin,
   Lokalise, Phrase) reads it and no translator will ever open it. Whatever the eventual localisation
   process is, it does not begin with a pull request against `EmailNotificationChannel.php`.
3. **Per-tenant copy is a confirmed product destination, and the archive cannot serve it.** The archive is
   *content-addressed*: the id is derived from the bytes. There is no lookup by coordinates, so it cannot
   answer *"what did tenant X's invitation say on 3 March?"* — to build the id you need the content you
   are looking for. That question is a `SELECT` against a revision table, which is a different shape.

**What this task deliberately does not do** is act on any of that. It moves the markup out of heredocs and
into Twig with identical output, so that the slice which *does* move words has one variable, not two. The
handoff's own sequencing rule: *"Sin tocar copy ni archive. Salida byte-idéntica."* ⚑ Quoted as the record
of what was decided in 2026-08, not as the live bar: **the first two clauses still hold, the third was
relaxed to rendering-identical on 2026-08-17** (§5). The words and the archive are still untouched here —
what changed is only how exactly the output has to match.

---

## 2. What already exists (reuse, do not rebuild)

[`EmailNotificationChannel`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailNotificationChannel.php)
is **already decomposed into Twig's shape**, which is what makes this slice cheap:

| Today, in PHP | Becomes |
|---|---|
| `htmlLayout()` — the base chrome shared by every purpose and locale | `templates/notification/_layout.html.twig` |
| `htmlBody()` — exhaustive `match` returning one purpose's central block | one `{% block %}` per purpose |
| `fieldsBlock()` — the labelled fact box both purposes fill the slot with | the default block body |
| `palette()` — accent colour + badge glyph, keyed by purpose alone | a typed view-object property |
| `FONT` — one inline font stack, repeated per text-bearing cell | unchanged; email has no cascade |
| `htmlDocument()` — pours the copy's `html` fields into the layout | the render call |

Also already in place, and all of it stays:

- **`requiredParts()` names `subject`, `body` and `html`**, and `send()` reads them in the same file. The
  parts contract is closed here on purpose.
- **The send path already throws on an unresolved slot** —
  [`IncompleteRenderedMessageException`](../../src/F5Sign/Notification/Application/Exception/IncompleteRenderedMessageException.php),
  raised from `TransmitDeliveryUseCase`. This is why `strict_variables: true` is **not** a behaviour
  change: Twig would throw where the code already throws by hand. ADR-0038's objection to Twig was that
  throwing "destroys post-deletion reconstruction" — but the send path throws already, and the
  reconstruction consumer never existed (§6).
- **`ext-intl` is in `composer.json` and unused.** The next slice needs it; nothing to add.
- **The cartesian smoke already has its shape.** `EmailNotificationChannelTest::catalogedTemplates()` is a
  provider over `(locale × purpose)`, so it widens by itself when either lands. **Measured
  2026-08-18, after [TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md) landed in full:**
  two purposes, `RECIPIENT_INVITATION` and `ENVELOPE_COMPLETED`, and **two** authored locales (`en`, `es`)
  — that task both widened the provider and renamed it from `catalogedPurposes()`. Re-count rather than
  trust this line — the sibling task adding `OTP_EMAIL` is in flight.
- ⚑ **`DEFAULT_LOCALE` is now `es`, not `en`, and a purpose authored in only one locale is a crash rather
  than a degradation.** TASK-027 §4 D8 flipped it and added a completeness guard asserting every
  `NotificationPurpose::cases()` is present under the fallback locale. So a new purpose — `OTP_EMAIL`, say
  — must be authored in **both** locales in the same changeset, or that guard reddens. It is doing its job
  when it does; do not widen it to let the purpose through.
- **Three tests are the acceptance bar and none of them may be edited** (§5, which names them). The
  cartesian smoke is **not** one of the three — widening it is a scope item (§3).

**Not present, must be added (measured 2026-08-17):** `twig/twig`, `symfony/twig-bundle`, and the bundle
entry — neither package is in `composer.json`. `CLAUDE.md` currently lists TwigBundle under *"Not enabled
(out of scope)"* — that line is part of this changeset.

---

## 3. Scope

**In:**

1. `twig` + `symfony/twig-bundle`, enabled **scoped to email**: `default_path` pointed at
   `templates/notification/`, and **no HTTP route renders Twig**. (The one thing the legacy
   `Planning/` record on this subject got right; see [`README.md`](README.md) §1.)
   ⚑ **Half of this is already done and must not be redone.** The two packages are declared in
   `composer.json` as of `feat/twig-scoped-to-email` — they were `packages-dev` and are now
   `packages`, with a patch bump of `symfony/twig-bundle` and nothing else moved (suite green, 1505
   tests). **Still owed here:** the `TwigBundle` entry in `config/bundles.php`, `config/packages/twig.yaml`
   with the scoping above, `strict_variables: true`, and the `templates/notification/` directory.
   🔑 **Both standing permissions this item needs were granted by the user on 2026-08-18** and do not
   need re-asking: editing `composer.json` / `composer.lock` ([repo rule 1](../../CLAUDE.md)), and
   correcting the `CLAUDE.md` line — which is a commit in the **workspace** repo, not this one
   ([ADR-0052](../adr/ADR-0052-twig-layout-composition.md) §2.6).
2. The six pieces in §2's table moved to `templates/notification/`, output unchanged.
3. **A typed view object per purpose** — `final readonly class`, typed properties, so the template writes
   `{{ view.envelopeTitle }}` and both ends are typed.
4. `strict_variables: true`.
5. **Removing the `x` / `x_html` twins** (§4).
6. The cartesian smoke widened to `(template × purpose × locale)`.

**Out, and each has its own slice in §6:** the words (ICU catalogs), the archive, `release_sha` on the
delivery, the `platform.template` migration, tenant-supplied copy, the ADR supersession, any new purpose.

---

## 4. Key decisions

**D1 — Twig autoescapes, so the twins must go, and this is the most likely way to break the slice.**
Today `slots()` mints an HTML-safe twin beside every passthrough (`envelope_title` → `envelope_title_html`,
via `escapeHtml()`) because
[`NativeTemplateEngine`](../../src/F5Sign/Foundation/Templating/NativeTemplateEngine.php) substitutes
inertly and escapes nothing. Under Twig the escaping happens in the engine, so keeping the twins yields
`&amp;lt;script&amp;gt;` — escaped twice. Remove the twins **in the same commit** as the conversion.

**D2 — ⚑ Twig's delimiters collide with the archive's, and the collision is silent.** The markup
`htmlDocument()` produces is **not** finished text: it still contains `{{token}}` slots, because the
composed markup is what gets archived and fingerprinted, and substitution happens later, at transmit, from
the pinned template. So a Twig template that must *emit* `{{envelope_title}}` has to protect it —
`{% verbatim %}`, or emit the braces as data. Get this wrong and Twig either throws on an undefined
variable or silently swallows the slot, and the archived bytes lose their placeholders. **This is the
sabotage target in §5.**

**D3 — Twig renders the layout at `authored()` time, not at transmit time.** That keeps the pin exactly as
it is: composed markup in, fingerprint over the same bytes, `NativeTemplateEngine` still doing the
substitution at transmit. Rendering with real values at transmit is a *different* pin and belongs to the
archive-removal slice, not here.

**D4 — the typed view object is a structural fix, not a lint.** ADR-0037 already books the hazard that
*"the template's text is versioned; the code supplying its slots is not."* A typed view object removes the
class of bug rather than detecting it — and it matters more the moment a tenant can edit text (§6), when
that goes from a rare hazard to a routine user action.

**D5 — no Rector, and TwigStan only after checking it.** Rector does not understand Twig templates.
TwigStan is worth evaluating as an extra, but verify Twig 3 / PHP 8.5 support before committing to it.

---

## 5. Verification

The properties here all live in the **hermetic tier** — no DB, no broker, no object store — so the
per-worktree lane's gaps (no MinIO, no RabbitMQ) do not weaken this slice's evidence. The end-to-end
acceptance scenario does need a reachable SMTP sink; see [`README.md`](README.md) §6.

**The bar is `make qa` green with the three pinning tests below unedited.** Each fails for a
different reason if the conversion is not neutral:

⚠ **"Unedited" scopes to these three, not to the suite.** An earlier cut of this task said *zero test
edits* in three places — and §3's sixth scope item asks for the cartesian smoke to be **widened**,
which is a test edit. Both are wanted: the three below are the neutrality proof and editing one
dissolves the evidence, while the smoke is a separate test whose additive widening is in scope.
Widening it is not a relaxation of this bar.

| Test | What it pins |
|---|---|
| `EmailNotificationChannelTest::a_value_reaching_the_markup_is_escaped_while_the_text_part_keeps_it_verbatim` | D1 — catches the double-escape directly |
| `TransmitDeliveryUseCaseTest::it_renders_and_delivers_an_email_invitation_to_the_outbox` | the exact rendered subject, `You have been invited to sign "Q3 Contract"` |
| `TransmitDeliveryUseCaseTest::it_renders_the_archived_template_rather_than_currently_deployed_copy` | D3 — that the archived version, not deployed code, is what renders |

**Sabotage before trusting the green run** ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 4):

1. Remove the `{% verbatim %}` protection from one slot (D2) → the subject test must go red, and it must
   fail *because the slot is gone*, not because of a whitespace diff.
2. Re-add one `_html` twin (D1) → the escaping test must go red with the doubly-escaped entity.
3. Restore both, re-run.

**The bar is rendering-identical, not byte-identical — relaxed 2026-08-17, and the relaxation is
conditional, so the condition is stated rather than the conclusion.**

This paragraph used to read *"a whitespace-only diff still fails this task"*, justified like this:
[`Template::of()`](../../src/F5Sign/Foundation/Templating/Template.php) derives `version` from a
fingerprint **over the composed parts**, and `TemplateId` is `v5(NAMESPACE, tenant|namespace|name|locale|version)`
— both frozen, both documented as orphaning every pinned template if changed. So the id *is* the content:
one byte of difference mints a **new archive row** per `(purpose, locale)`, and the archive would then
record a copy change on deploy day that never happened. The history would lie.

⚑ **That argument is empty while no environment carries a `platform.template` history anyone will read.**
His call, 2026-08-17: this repo is not in production, dev rows are disposable, so a one-time re-mint costs
nothing — and since the conversion happens once, it is long past by the time an environment is long-lived.

**What the bar still buys, and why it is not dropped:** it is the mechanical proof that the *email* did not
change. Double-escaping (`&amp;lt;`), a dropped `<td>`, a CTA whose `href` lost its token — those are
recipient-visible with or without production. So:

- **Whitespace-only differences are acceptable** — trailing newlines, indentation around Twig tags.
- **Any difference a mail client can render differently is not**, and remains a finding to report rather
  than a bar to lower.
- ⛔ **Do not contort the templates to chase a newline.** Twig's whitespace control (`{{-`, `-%}`) can force
  a byte match, and using it to satisfy a bar that no longer needs satisfying would trade away exactly the
  legibility this task exists to buy. That is the failure mode this relaxation exists to prevent.

⚠ **The condition, so a later reader does not generalise this into "whitespace never matters":** the day
there is a production archive, `platform.template` is real history again and a gratuitous re-mint is a real
(if minor) event. The relaxation is about *this conversion happening first*, not about fingerprints being
unimportant.

**What enforces it now:** the three tests above, plus a comparison of the rendered HTML with whitespace
normalised. No fingerprint-equality guard — it would defend the property that was just retired.

---

## 6. Open follow-ups (track, don't solve here)

1. **Words to ICU catalogs — parked 2026-08-17, and no longer "the next slice".** ⚠ This entry previously
   read *"the next slice, and the point of this one. Spanish enters there, with real plurals."* Neither half
   survived measurement: Spanish shipped without it ([TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md)),
   and the chain cannot be sequenced as planned — ICU needs formatting at transmit, which is §4 D3's
   archive-removal pin, so words and archive are **one** task rather than two. Both findings and the forcing
   condition are in [BL-111](../BACKLOG.md). When it is un-parked, plurals still enter there. ⚑ **It must
   re-home [BL-23](../BACKLOG.md) on the way in.** That row records the apostrophe
   hazard (under ICU an apostrophe immediately before a token turns it into literal text with **no error at
   all** — ordinary English and French copy meets this) and proposes the mitigation as a probe-render in
   `TemplateRegistry::register()`. **The archive-removal slice deletes that registry.** So the guard's home
   is the compositor or the cartesian smoke, and that has to be decided when ICU lands, not discovered
   afterwards.
2. **Retire the archive; put `release_sha` on the delivery.** Reproduction becomes `git checkout <sha>` +
   render: engineering traceability, explicitly **not** legal proof. ✅ Confirmed with the user
   (2026-08-11) that no judicial value is required and no post-deletion reconstruction is needed — which is
   what dissolves ADR-0038's D9. The reconstruction consumer would have been the Evidence & Audit
   projector ([TASK-014](TASK-014-evidence-audit-projector.md), not started), and even built it would not
   help: the events are thin pointers and the text was never in the log.
3. **Drop `platform.template` and `template_id`** — a **separate release** from (2). Code first, schema
   second ([repo rule 2](../../CLAUDE.md)); the reverse order breaks a running deploy.
4. **The two ADRs**: the new one lands with *this* task (header field above); ADR-0038 → `Superseded` lands
   with (3), and that is three edits in [`../adr/README.md`](../adr/README.md) — index row, relationship
   graph, crosswalk row — plus the header `Crosswalk` field and the `## ` sections from
   [`AUTHORING.md`](../adr/AUTHORING.md).
5. **Tenant-supplied copy is not in this chain.** Its hard prerequisite has since appeared — `identity.tenant`
   exists as of the identity-access merge — but it needs its own record: a revision table, and a
   **mandatory token allow-list per `(channel, purpose)` validated on save**, without which a tenant editing
   text can reference a slot the code does not supply. Until then the words stay a *parameter* of the
   compositor, never a constant it looks up.
6. **ICU output drifts with the container's ICU data version.** Accepted for engineering traceability;
   **unacceptable** if evidentiary value is ever wanted. If that changes, this whole chain is re-opened.

---

## 7. Deviations from the plan above (added on delivery, 2026-08-18)

The sections above are the plan as written on 2026-08-17 and are **not** rewritten to match what
shipped — §N are anchors other documents cite. What follows is the difference, and two of the four
items are cases where the plan and its own governing ADR disagreed.

### 7.1 The three pinning tests kept their bodies; their shared helper did not

§5 requires the three named tests unedited, and their assertions are byte-identical to what they were.
`EmailNotificationChannelTest`'s private `channel()` helper is not: `EmailNotificationChannel`'s
constructor gained a `Twig\Environment` as its second argument, so every construction of the real
channel took one line. Three places, none of them an assertion —
`EmailNotificationChannelTest::channel()` and two inline constructions in that file, plus
`OutboxEmailChannel`. Recorded rather than glossed because *"unedited"* is a bar and the file's
`git diff` is not empty.

The environment comes from the container in production and from
[`NotificationLayoutTwig`](../../tests/F5Sign/Notification/Testing/NotificationLayoutTwig.php) in the
hermetic tier — which is two definitions of one setting, and therefore a divergence risk rather than a
convenience. What closes it is
[`EmailChannelTwigWiringTest`](../../tests/F5Sign/Notification/Integration/EmailChannelTwigWiringTest.php):
it renders through both and asserts the bytes match. ⚑ **The authored pairs alone cannot see the
setting whose divergence matters most** — no authored locale contains a character `htmlspecialchars`
touches, so `autoescape: false` on one side would render byte-identical output and pass. That test
therefore also renders one probe view whose `lang` is observably escaped or not. It is the same
empty-set-reads-as-all-clear shape [`BL-125`](../BACKLOG.md) records, one level up.

### 7.2 ⛔ §3's fifth scope item — removing the `x` / `x_html` twins — was not done, because ADR-0052 forbids it

§4 D1 reads *"under Twig the escaping happens in the engine, so keeping the twins yields
`&amp;lt;script&amp;gt;` — escaped twice"*. That is true **only if Twig is the substitution engine**,
and [ADR-0052](../adr/ADR-0052-twig-layout-composition.md) §2.1 declines exactly that: Twig composes
the layout at `authored()` time and never receives a recipient's value. The `Decision record` field
above already warns that the ADR *"moves the ground under §4 D1–D3"*; this is the item it moves
furthest.

So nothing escapes a recipient's value for the markup unless
[`slots()`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailNotificationChannel.php) does —
`NativeTemplateEngine` is inert by contract, and Twig has finished running a whole phase before those
values exist. **Measured rather than argued:** deleting the twins reddens
`a_value_reaching_the_markup_is_escaped_while_the_text_part_keeps_it_verbatim` — one of §5's three
untouchable tests — with a raw `<script>` in the `html` part. The twins stay, the class docblock says
why on sight, and ADR-0052 §6 carries it as a *not realized, deliberately* entry.

### 7.3 D2's `{% verbatim %}` never became necessary, and §5's first sabotage step is inapplicable as written

§4 D2 and ADR-0052 §2.3 name the delimiter collision as the highest-risk mechanic, and §2.3 offers two
protections: `{% verbatim %}`, **or** emitting the braces as data. Because §3 keeps the words in
`TEMPLATES`, every `{{token}}` reaches Twig as a *value on the view*, never as literal braces in a
template — so the second protection is in force everywhere and there is no `{% verbatim %}` in the
tree. The hazard is real and unchanged; what is absent is any site that needs the first form.

§5's sabotage step 1 — *remove the `{% verbatim %}` protection from one slot → the subject test must go
red* — therefore could not be run as written, on two counts: there is no such protection to remove, and
the subject part is not composed by Twig at all, so no template edit could redden it. What was run
instead, and what each proved:

| Sabotage | Result |
|---|---|
| Layout emits one token no copy declares | `composition_introduces_no_slot_the_copy_did_not_declare` reddens on **all four** pairs, naming the token |
| Layout writes an unprotected literal `{{envelope_title_html}}` | Twig throws `Variable "envelope_title_html" does not exist` — §2.3's predicted *throws* branch, not its silent one |
| A copy property loses its `Twig\Markup` type | 6 failures + 1 error, showing `&amp;laquo;` — including all four pairs of the new cartesian check, where the pre-existing Spanish test could only see `es` |
| The `_html` twins removed (§7.2) | `a_value_reaching_the_markup_is_escaped_while_the_text_part_keeps_it_verbatim` reddens with raw `<script>` |

⚠ A fifth attempt is worth recording because it proved nothing and looked like it had: piping a copy
field through `|trim` to force autoescaping **left the suite green**, since Twig declares `trim`
`is_safe => ['html']`. A sabotage that is not a sabotage reads exactly like a test that does not work.

### 7.4 One view type, not one per purpose — and two corrections made to ADR-0052 in this changeset

§3's third item and ADR-0052 §2.5 both said *a typed view object per purpose*. What shipped is one
[`EmailLayoutView`](../../src/F5Sign/Notification/Infrastructure/Channel/EmailLayoutView.php): both
purposes' central block is the same fact box consuming the same `fields`, so the right granularity is
*per block shape*. ADR-0052 §2.5 now says so, and also withdraws its illustration
`{{ view.envelopeTitle }}` — an envelope title is a recipient value and never reaches Twig, which makes
that example the very conflation §1 of that ADR exists to prevent. Both corrections are marked in
place there rather than silently reworded.

Two smaller naming differences from §2's table, recorded here so the table is not read as a spec: the base
template shipped as `layout.html.twig`, not `_layout.html.twig` — the leading underscore marks a partial,
and this one is rendered directly — and *"one `{% block %}` per purpose"* shipped as **one `central` block
with a default body**, which both purposes take today. A purpose overrides it when its block differs; that
is the same trigger, expressed once instead of twice.

### 7.5 Landed alongside, because the change made them false

- [`BL-125`](../BACKLOG.md) and [TASK-027](TASK-027-spanish-email-and-the-locale-nobody-chooses.md)
  §6.11 both described the `lang=` escape as a hand-written `escapeHtml()` inside `htmlLayout()`. The
  method is gone; the property survived and is now held by Twig's autoescaping, which is stronger
  (it applies whether or not anyone remembers it) and differently fragile (the way to lose it is to
  declare `EmailLayoutView::$lang` as `Markup` for consistency with its neighbours).
- [`docs/ddd/notification-domain-model.md`](../ddd/notification-domain-model.md) described the code as
  *"one `htmlLayout()`, one `htmlBody()` match"*.
- [TASK-022](TASK-022-delivered-codes-over-email.md)'s `Sibling` row named an unscoped prerequisite —
  *Twig is not a production dependency* — that this task discharges, and warned against authoring
  against a mechanism that no longer exists.

### 7.6 Open follow-ups this delivery adds

Both are recorded in [`docs/BACKLOG.md`](../BACKLOG.md); neither is owed by this slice.

1. **`no HTTP route renders Twig` is still unenforced** ([BL-136](../BACKLOG.md)). `default_path` keeps
   an application view tree off the loader and that half is asserted, but nothing stops a controller
   rendering `layout.html.twig`. It holds today because no controller does, which is the shape rule 5
   warns about, not a gate.
2. **The `Markup`-versus-`string` contract on `EmailLayoutView` is a convention with a test, not a
   rule** ([BL-136](../BACKLOG.md), same row — they are one guard). Declaring a copy field `string`
   double-escapes it silently; declaring a value `Markup` un-escapes it silently. Today the cartesian
   composition check catches the first for any copy carrying an entity, and nothing catches the second.

### 7.7 The measurement, and the four fingerprints it moved

Re-measured independently on delivery rather than trusted from the conversion script: the two sides were
compared by **significant-token stream** — every tag and every non-whitespace text node, in order — not by
normalising whitespace away, which would have assumed the answer. Result: `subject` and `body` byte-identical
on all four pairs; `html` differing by 5 newlines (invitation) or 4 (completion) between `</tr>` and `<tr>`,
minus 1 inside the fact box, plus 1 after `</html>`. The `{{token}}` multiset and the HTML-entity multiset are
identical on both sides, so nothing was swallowed and nothing was double-escaped. The check was
sabotage-verified against a mutated copy of the templates: it reddens on a changed attribute value, changed
text, a dropped `<tr>`, a doubled entity and a CTA that lost its `{{link_html}}`, and stays green only for a
gratuitous inter-tag newline — so the green is discriminating rather than vacuous. Unauthored locales (`fr`,
`de-DE`) fall through the same path and match too, so the property is not confined to the four authored pairs.

⚑ **All four `Template::version` fingerprints changed**, and that is the accepted cost rather than a
surprise: `Template::of()` derives the version from the composed parts, so 5 newlines mint a new archive row
per `(purpose, locale)`. §5 relaxed the bar to rendering-identical on exactly this basis — no environment
carries a `platform.template` history anyone will read, and the conversion happens once. Recorded with the
fact stated rather than the conclusion, because the condition is what expires: the day there is a production
archive, a gratuitous re-mint is a real event again.

