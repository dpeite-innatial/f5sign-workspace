# TASK-019 — Requirement traceability and the per-tier assurance gates

| | |
|---|---|
| **Status** | **Not started — groundwork only.** Diagnosis complete and the key feasibility claims are *measured* (§5), not estimated. Nothing here is built. |
| **Type** | Corrective + enabling. Closes the last substantive gap between [ADR-0035](../adr/ADR-0035-testing-standard.md) as written and as realized, and unblocks the per-tier covered-MSI gate that keeps that ADR at `Proposed`. |
| **Why** | ADR-0035 mandates requirement traceability for Tier A and a Tier A ≥ 90 / Tier B ≥ 70 covered-MSI split. Today traceability is **unenforceable as specified** (§1.1), the tags that express it have **no consumer at all** (§1.4), and the per-tier gate is recorded as blocked on "a design problem". It is not — §5 runs it. |
| **Decision record** | **Amends [ADR-0035](../adr/ADR-0035-testing-standard.md)**, which is still `Proposed`, so this is an in-place amendment rather than a superseding ADR. Closes the first of its two named `Pending` items; §4.5 optionally closes the second (`beStrictAboutCoverageMetadata`). Touches [`tests/README.md`](../../tests/README.md) (the realizer detail) and [`infection.json5.dist`](../../infection.json5.dist). |

---

## 1. The diagnosis — one root cause, four symptoms

**ADR-0035 specifies two markers. Only one was built, and it was made to carry both meanings.**

- ADR-0035 §Layering: *"Assurance-tier (A/B) is a `#[Group]`, orthogonal to the size-tier directory."*
- ADR-0035 §TDD & traceability: *"formalize `#[Group('eIDAS-…')]` **requirement traceability** on Tier-A tests."*

There is **no A/B tier group in the codebase**. `--list-groups` returns exactly four: `eIDAS-signing`,
`eIDAS-auth`, `eIDAS-rls`, `eIDAS-event-integrity`. The requirement tag became the tier marker by
default. Each symptom below follows from that.

### 1.1 Tier-A code with a non-eIDAS obligation is unmarkable

With one tag carrying both meanings, marking code Tier A requires inventing an eIDAS requirement for it.
`Foundation/Crypto` discharges **GDPR Art. 32** (confidentiality at rest, [ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md)),
not an eIDAS requirement — so there is no honest tag, while ADR-0035 makes traceability *mandatory* for
Tier A, and names **crypto** in the Tier-A set by hand. `FieldCipherTest` and `ConfigKeyProviderTest` are
consequently untagged. **The standard cannot be obeyed as written.** That is a specification defect.

### 1.2 A requirement discharged outside its owning context has no carrier

The matrix indexes *capability → carrier tests* and assumes carriers live in the context that owns the
capability. Evidence & Audit breaks it: the requirement is E&A's, the carriers are Envelope's and
Session's producer tests ([TASK-014](TASK-014-evidence-audit-projector.md) Stage 0), and the
`eIDAS-evidence` row therefore reads "none" while partly discharged.

⚑ **Cheap to fix and easy to over-think:** `#[Group]` is `IS_REPEATABLE` (§2). A test may carry several
requirement tags. `EnvelopeStreamKeyTest` genuinely discharges two — the *mechanism* is stream/log
integrity, the *purpose* is evidence completeness. One-tag-per-test is a habit, not a constraint.

### 1.3 The hand-maintained carrier column drifts — demonstrably

`ChildTableRlsIsolationTest` carried `#[Group('eIDAS-rls')]` and was **absent from the matrix** —
from `f822af8` (2026-07-22) until it was added **by hand** on 2026-07-28, during the doc-reconciliation
pass that also authored this task. It reads as closed in the tree you are holding; the drift is the
point, not the row. Nothing structural prevents the next one, which is what §4 is for.

The instructive part is how it happened. The commit that introduced that test — **`f822af8`** — also edited
`tests/README.md` in the same change, and its diff shows it **carefully adding three other carriers**
(`EnvelopeRowLockTest`, `EnvelopeConcurrentAppendTest`, `SigningSessionRowLockTest`) to two adjacent rows. The
author was actively maintaining the matrix, in the file, in that commit — and still missed the row for a
test that same commit created. If the most attentive possible moment produces drift, the mechanism is
wrong rather than the person.

### 1.4 ⚑ The tags have **no consumer**

Verified across `composer.json`, `phpunit.dist.xml`, `infection.json5.dist`, the infra `Makefile` and
`.github/`: **nothing selects, reports on, or gates by these groups.** The single non-test occurrence is
a *comment*. So the tags are prose stored in attributes, and the matrix is a hand transcription of that
prose. That is the whole of §1.3's cause: **a label nothing consumes is documentation, and documentation
drifts.**

### 1.5 The per-tier gate is not blocked by a design problem

`infection.json5.dist` and ADR-0035 both record the blocker as *"a mutant's assurance-tier is ill-defined
because tiers are `#[Group]` on tests while mutants live on source."*

**The framing is the blocker.** Cost-of-defect is a property of *what the code does* — true of
`FieldCipher.php` whether or not a test exists. ADR-0035 already knows this: its consequence section says
*"the Tier-A set is **enumerated** (signing/crypto/RLS/event-integrity)"* — an enumeration of **code
areas**. Tier was always a property of source; recording it only on tests is what made it unreadable to a
tool that mutates source.

---

## 2. What `#[Group]` actually is in PHPUnit (bounds everything below)

Read before designing on top of it; it is less than it looks.

```php
#[Attribute(Attribute::TARGET_CLASS | Attribute::TARGET_METHOD | Attribute::IS_REPEATABLE)]
final readonly class Group { public function __construct(string $name); }
```

- **An arbitrary non-empty string. No validation, no registry, no namespace, no meaning.** A typo is a
  new group, silently.
- **Repeatable, on class or method.** Multiple requirement tags per test are native (§1.2).
- **Every consumer in PHPUnit is *selection*** — `GroupFilterIterator`, the XML `<testsuite>`
  include/exclude, `--list-groups`. A group decides **whether a test runs**. It does nothing else: there
  is no reporting-by-group, no coverage integration, no enforcement.
- **Reserved names to avoid:** `small` / `medium` / `large` are mapped to PHPUnit *test sizes*, and
  `default` is the implicit group of every untagged test.
- **⚑ PHPUnit synthesizes hidden groups from coverage metadata:** `__phpunit_covers_<lowercased-fqcn>`,
  `__phpunit_uses_<…>`, `__phpunit_requires_php_extension<…>`. So a **source → test index already
  exists**, usable as a selector today:

  ```bash
  vendor/bin/phpunit --group='__phpunit_covers_f5sign\foundation\crypto\fieldcipher'   # → 13 tests
  ```

**The consequence that matters:** a `#[Group]` is a *selector*, so **any meaning we attach is ours to
enforce**. Tagging is not a standard; a tag plus a consumer is.

---

## 3. The design — three instruments, three questions

The current standard asks one artifact (the `eIDAS-*` tag) to answer three questions at once. Separate
them and each becomes mechanical.

| Question | Instrument | Lives on |
|---|---|---|
| **Is this Tier-A code guarded by a test that *claims* the requirement?** | `phpunit --group=<requirement tags> --coverage-clover`, read over the Tier-A source paths | tests (tag) × source (paths) |
| **Are those guards strong?** | `infection --filter=<Tier-A source paths> --min-covered-msi=90` | source |
| **Did unguarded code land anywhere?** | the existing global `minMsi` breadth tripwire — **unchanged** | source |

### 3.1 Traceability coverage — the new instrument, and what it means

Running coverage with **only the requirement-tagged tests selected** yields a number that neither plain
coverage nor covered-MSI can express: *what fraction of Tier-A source is exercised by tests that claim
responsibility for a Tier-A requirement?*

⚑ **A 0% here does not mean untested.** `FieldCipher` reads 0% on this instrument while the
`Foundation/Crypto` area it belongs to measures **91% covered-MSI** (§5 — an area figure over
`--filter=src/F5Sign/Foundation/Crypto`, which also covers `ConfigKeyProvider`, `KeyProvider` and
`CipherException`; no per-file figure for `FieldCipher.php` is reported anywhere in this doc) — it is well tested and *untraceable*. The usual remediation is
therefore **to add a tag, not to write a test**, which is what makes this instrument drive the behaviour
the standard actually wants. State this loudly wherever the number is reported, or someone will "fix" a
0% by writing redundant tests.

⚑ **It inherits the `#[CoversNothing]` blind spot.** With `requireCoverageMetadata="true"`, broad
scenario tests contribute no coverage, so a Tier-A class exercised only through flows reads 0% for a
third, legitimate reason. This is the same (a)/(b) triage `infection.json5.dist` documents at length, and
only sabotage distinguishes them. **This instrument must therefore be reported, never blindly gated**,
until §4.4 decides otherwise.

### 3.2 Tier is a property of source

Add a reviewed, versioned list of Tier-A source paths. It is still hand-maintained — but it is one short
list of capability areas (four today) consumed by a gate that **fails loudly when wrong**, rather than a
thirty-row table nothing checks. That asymmetry is the point.

### 3.3 Requirement tags become multi-regime and multi-valued

- Rename the concept: *"eIDAS traceability matrix"* → **"requirement traceability matrix"**. ADR-0035's
  own words are already "requirement-ID traceability".
- Add regime siblings rather than forcing everything under eIDAS: `gdpr-art32-at-rest` for the field
  cipher. **Existing four tags stay untouched** — minimum churn.
- Use several tags where a test discharges several requirements (§1.2).

---

## 4. Build plan (slices, cheapest first; each independently landable)

### 4.1 Vocabulary + tagging *(closes §1.1 and §1.2; no behaviour change)*

Reword `tests/README.md` and the ADR-0035 line to "requirement traceability"; add the `gdpr-*` family;
tag the currently-untagged Tier-A tests; multi-tag where a test discharges more than one requirement.
Known untagged Tier-A candidates, from §5: `FieldCipherTest`, `ConfigKeyProviderTest`,
`CanonicalJsonPayloadCodecTest`, `EventLogAccessControlTest`, `EventRelayTest`,
`EventRelayErrorSanitizationTest`, `EnvelopeSendRosterTest`, the consent assertions in
`SigningSessionTest`. **Decide each on merit — this list is a starting point, not a verdict.**

### 4.2 The enforcement rule *(closes §1.4 — the highest-value slice)*

A PHPStan rule, sibling of [`HermeticTierRule`](../../phpstan/src/Rules/HermeticTierRule.php) and
[`AuditableEventDeclaresStreamKeyRule`](../../phpstan/src/Rules/AuditableEventDeclaresStreamKeyRule.php):

> **A test that `#[CoversClass]` a class under a declared Tier-A source path must carry at least one
> requirement `#[Group]`.**

Statically checkable — attribute and path are both in the AST. This turns "traceability mandatory for
Tier A" from aspiration into a structural guarantee: it fires on `FieldCipherTest`, forcing the
vocabulary question in §1.1 instead of letting it be skipped.

⚠ **It does not close §1.3, and the difference matters.** §1.3's drift is a **missing row in a
hand-maintained column** of `tests/README.md`. This rule reads *test attributes only* — and
`ChildTableRlsIsolationTest` already carried `#[Group('eIDAS-rls')]` when it drifted out of the matrix,
so the rule would have fired on nothing. Guarding the tag cannot guard the transcription of the tag.
The fix for §1.3 is to **remove the drift surface**, not to add a check over it: generate the carrier
column from the attributes rather than maintaining a second copy by hand — which is exactly
[TASK-020](TASK-020-derive-the-deferral-index.md) §5's diagnosis, and is filed here as §4.6.

*Design note:* the rule needs the Tier-A path list from §4.3, so land that list first (as data) even if
the Infection gate that also consumes it comes later.

### 4.3 Tier-A source list + the scoped mutation gate *(closes §1.5, ADR-0035's `Pending` item)*

Add the path list and a composer script beside the existing one:

```
composer infection          # global ratchet, minCoveredMsi 79 — unchanged
composer infection:tier-a   # the Tier-A paths, --min-covered-msi=90
```

**Land report-only first.** It fails today (§5), and a gate introduced red is a gate people learn to
ignore.

### 4.4 Pay the Tier-A mutation debt, then make 4.3 blocking

12 escaped mutants over three files (§5). Order by what they protect: `EventLogCommitment` and
`CanonicalJsonPayloadCodec` first — they are the tamper-evidence core that
[ADR-0031](../adr/ADR-0031-event-log-store.md) and the whole Evidence & Audit line rest on. When green,
flip 4.3 to blocking and move **ADR-0035 to `Accepted`**.

### 4.5 *(Optional, adjacent)* `beStrictAboutCoverageMetadata`

ADR-0035's other named `Pending` item; absent from `phpunit.dist.xml` today. Independent of the above but
the only other thing between the ADR and `Accepted`, so worth scoping here.

### 4.6 Generate the carrier column *(closes §1.3 — the symptom §4.2 structurally cannot reach)*

§1.3's drift lives in the **transcription**, not the tag: the carrier column in `tests/README.md` is a
hand-maintained second copy of data that already exists as `#[Group]` attributes in `tests/`. A rule
over the attributes cannot see a row missing from a markdown table, so §4.2 leaves this open by
construction.

Derive the column instead — enumerate `#[Group('eIDAS-…')]` across `tests/` and emit the rows, so the
matrix becomes a projection rather than a promise. Same shape and same argument as
[TASK-020](TASK-020-derive-the-deferral-index.md) §5, which reaches it from the backlog side; **scope
the two together**, since one generator design serves both and TASK-020 already carries the
measurements. ⚠ Read TASK-020's standing constraint first — it applies here unchanged.

---

## 5. Measured baseline (2026-07-28)

Everything below was run, not estimated. Re-runnable in the container.

**Scoped mutation gate — works today, no new code:**

```bash
vendor/bin/infection --filter=src/F5Sign/Foundation/Crypto \
  --map-source-class-to-test --only-covering-test-cases --threads=4 --min-covered-msi=90
```

| Tier-A source area | killed / escaped | covered-MSI | vs ≥ 90 |
|---|---|---|---|
| `Foundation/Crypto` | 53 / 5 | **91%** | ✅ passes |
| `Foundation/EventLog` | 92 / 12 | **88%** | ❌ fails by 2pp |

**The 12 escaped mutants:** `EventRelay.php` 7 · `EventLogCommitment.php` 3 ·
`CanonicalJsonPayloadCodec.php` 2. **Nine sit in files whose tests carry no tag** — the traceability
blind spot and the strength gap are the same region.

**Traceability coverage — Tier-A source, requirement-tagged tests only** (165 of 804 tests selected):

| file | coverage from tagged tests | reading |
|---|---|---|
| `Foundation/Crypto/FieldCipher.php` | **0%** (0/33) | untraceable, **not** untested — 91% covered-MSI |
| `Foundation/Crypto/ConfigKeyProvider.php` | **0%** (0/10) | same |
| `Foundation/EventLog/CanonicalJsonPayloadCodec.php` | **0%** (0/13) | same |
| `Foundation/EventLog/Console/RelayEventLogCommand.php` | **0%** (0/39) | check whether Tier A at all |
| `Foundation/EventLog/EventRelay.php` | 77.4% (48/62) | |
| `SignatureExecution/…/Pdf/DssPayloadMapper.php` | 93.7% (59/63) | |
| `Foundation/EventLog/EventLogCommitment.php` | 95.5% (21/22) | |
| `Foundation/EventLog/DbalEventLog.php` | 100% (34/34) | |
| `SignatureExecution/…/Pdf/DssHttpAdapter.php` | 100% (67/67) | |

**Tag population:** `eIDAS-signing` 92 tests · `eIDAS-auth` 32 · `eIDAS-event-integrity` 23 ·
`eIDAS-rls` 18 · `default` (untagged) 639.

---

## 6. Open questions — decide before building, do not assume

1. **What is actually in the Tier-A source list?** §5 probed `Foundation/Crypto` and
   `Foundation/EventLog` because ADR-0035 names them. Signing (`SignatureExecution/…/Pdf`) is plausible;
   **RLS is partly SQL in migrations and Postgres policies, not PHP**, so it may not be
   mutation-testable in this shape at all. Establish that before promising a Tier-A number that silently
   omits the capability the standard names first — that is precisely the failure
   `infection.json5.dist` records as the S7 finding.
2. **Is `RelayEventLogCommand` Tier A?** It reads 0% on both instruments. Console entry points may
   legitimately be Tier B.
3. **Do the speed flags change the number?** §5 used `--only-covering-test-cases` and
   `--map-source-class-to-test`. Confirm on one area, with and without, that the scoped covered-MSI
   matches a full-suite run before either number gates anything.
4. **88% is n=1, and the 2pp gap is about two mutants.** ⚠ An earlier draft borrowed the config's
   per-mutant and variance figures (~0.037pp, ~±0.2pp) to argue the gap is real debt. Those are computed
   against the **global** 2673-mutant denominator and do not transfer: this is a *scoped* run of
   `Foundation/EventLog` — 92 killed + 12 escaped = **104** mutants — so one mutant moves the number by
   **~0.96pp**, roughly 26× the borrowed figure. Carried through, 2pp ≈ **2 mutants**, which is inside
   the run-to-run variance the same config records for itself. So the shortfall is *not* established as
   real debt by this measurement. Re-measure at n>1 before §4.3/§4.4 sequence work off it — and note
   the debt may well be real on its merits (the 12 escapes are in the tamper-evidence core, §5), just
   not because of this number.
5. **Should traceability coverage ever *gate*, or only report?** The `#[CoversNothing]` blind spot
   (§3.1) argues for report-only indefinitely. A gate would need an explicit exemption mechanism, which
   is a new list to maintain — weigh that against the drift lesson in §1.3.
6. **Tag naming.** Keeping `eIDAS-*` and adding `gdpr-*` is the minimum-churn option and is assumed
   above. A uniform `req-*` prefix would read better and cost a rename of ~27 files. Cosmetic; decide
   once.

---

## 7. Picking this up cold

- Read [ADR-0035](../adr/ADR-0035-testing-standard.md) first, then `tests/README.md` §*Assurance tiers*
  — that pair is the standard and its realizer detail, and the gap between them **is** this task.
- §1 above **is** the diagnosis; there is no fuller version to go and read. It was compressed from a
  workspace scratchpad that has since been retired, and the compression was audited before retirement:
  every measurement, reproduction command and headline figure survives here or in §5. Three things the
  scratchpad carried that this doc had dropped were folded back in at that point — the `f822af8` drift
  evidence (§1.3), the "generate, don't maintain" proposal (now [TASK-020](TASK-020-derive-the-deferral-index.md) §5),
  and the reason "just call it Tier B" is the wrong answer (now [ADR-0035](../adr/ADR-0035-testing-standard.md) Counterpoint).
- **The cheapest correct first move is §4.2, not §4.1.** The rule is what makes the tagging durable;
  tagging without it re-creates the drift this task exists to remove. §4.1 only has to come first
  because the rule would otherwise fail the build on tests it is about to fix.
- ⚠ **§4.2 does not close §1.3** — it guards the tag, and §1.3's drift is in the *transcription* of the
  tag into a hand-maintained table. That symptom needs §4.6 (generate the column). Do not read a green
  §4.2 as evidence the matrix cannot drift again.
