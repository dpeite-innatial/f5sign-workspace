# TASK-033 — Delegated signature: the consignor who never opens the link

| Field | Value |
|-------|-------|
| **Status** | **Ready for review on `feat/delegated-signature`** — every section of §3 is built and the branch is green on the full four-gate lane: `OK (2542 tests, 12514 assertions)`, lint `0 of 1073`, Deptrac `0`, PHPStan `[OK]`. ⚠ **Two properties are declared rather than met**: the asserted evidence is stored in cleartext ([`BL-214`](../BACKLOG.md), §6 bar 17) and the delegated commit's row lock is asserted by reading rather than by running ([`BL-215`](../BACKLOG.md), §6 bars 13 and 18). ⛔ **ADR-0055 stays `Proposed`** and this slice does not promote it: §3.3's three legal questions are not this repository's to answer. Previously: **In progress on `feat/delegated-signature`** (worktree `f5sign-backend-delegated`, branched from `feat/claimable-recipient-slot` — TASK-036 — at `cd8947a`). **Two commits, both green on the full four-gate lane**: `a1e0453` (§3.1 — the two enum members, both by-name gate refusals, `SignsVia`; `OK (2502 tests, 12160 assertions)`) and `8d93135` (§3.2 — `signs_via`, its migration, the cross-slot invariant, both persistence mappings, the authoring chain; `OK (2508 tests, 12207 assertions)`), against a `2500/12146` baseline measured on this tree before the first edit. ⚑ **Updated 2026-08-31: four more commits, each lane-green on its own run** — the base-branch merge (`e4108bc`), §3.10's three guards with four bars and four sabotages (`dac5498`), the `ISSUER_CALLERS` delegated axis (`cbbcab1`) and §3.11 / ADR-0055 §2.16 guard 2 on the session open (`993d1e7`, `OK (2518 tests, 12260 assertions)`). §8.5 steps 1–3 are done and §8.1 carries the per-commit table. ⛔ **This row said the three guards were UNCOMMITTED and UNTESTED**, which was true when written and stopped being true at `dac5498`; they are committed, barred and sabotaged. Next is §8.5 step 4 (§3.3 + §3.3b), not started. ⚑ This row read *"Not started. No branch, no code"* until 2026-08-28. |
| **Type** | **Forward build.** The domain shape is decided ([ADR-0055](../adr/ADR-0055-delegated-signature.md)) and nothing gates the start. ⚑ This field read *"with one blocking precondition"* until 2026-08-24; §3.0 records the premise that was retracted. |
| **Why** | The eCMR consignor is the integrator's own customer, authenticated inside the integrator's transport-management system, working at a loading dock. They will never open our link. Today the platform has no way to say *this party was authenticated elsewhere by someone who stands behind it* — so an integrator with this requirement either mails a link to someone who should not receive one, or asks for a side-door endpoint that signs. [ADR-0055](../adr/ADR-0055-delegated-signature.md) §1 carries the full statement of the gap and this record does not restate it. |
| **Builds on** | ⚑ **Discharged 2026-08-25.** This read *"a hard dependency that does not exist yet"* until [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) / [TASK-035](TASK-035-signature-requires-readable-envelope.md) landed on `develop`: the slice closing [`BL-61`](../BACKLOG.md) — a ceremony may not run over an envelope no recipient could have read. The reason it had to land first: that hole was harmless only **by accident** (no link exists before send), and this task removes the accident by construction, since a delegated act needs no link at all. It is now guarded at all four ceremony points on the predicate `sentAt IS NOT NULL`, so the sequencing constraint is satisfied and nothing here waits on it. Then **[TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md)** (the two-gate model and the slot types this widens) and **[TASK-032](TASK-032-ordered-auth-method-list.md)** (which made both slots lists and wrote the mirror test this extends). Reused unchanged: [ADR-0047](../adr/ADR-0047-declared-subject-on-machine-requests.md) (the declared subject, whose first reader this is), [ADR-0033](../adr/ADR-0033-pii-field-encryption-at-rest.md) (the cipher — ⚠ *a* caller, not provably the *first*: ADR-0049 holds the same claim and neither has shipped one), [ADR-0014](../adr/ADR-0014-idempotency-three-layer.md) (layer 1, which the deterministic session id already supplies). ⛔ **And a hard one added 2026-08-25: `TASK-036`** (claimable recipients, on the unmerged `docs/claimable-recipient` branch, cited by id and deliberately not linked). ADR-0055 §2.3 refuses a claimable slot nobody has claimed, and §3.11 carries the two claim facts across the same seam as `signsVia` — neither is buildable until that task lands the columns. It is already the recommended first branch, so this constraint costs nothing; it is recorded so a reorder does not read as *the field was never wanted*. |
| **Decision record** | **[ADR-0055](../adr/ADR-0055-delegated-signature.md)**, `Proposed` — seventeen decisions with seven rejected alternatives. ⚑ **This slice does NOT promote it on a green build**, and that is stated in the ADR itself: ADR-0055 §3.3 names a contractual precondition that no test can reach, and its §5 closes by naming what no bar can see. Promotion needs ADR-0055 §5's bars **plus** the two non-code preconditions, which are **ADR-0055 §3.3's contractual half and its three legal questions** — the eCMR article 3.1 presumption, article 5.2's reference to the agreed procedure, and GDPR article 14. ⚑ **Corrected 2026-08-31**: this row sent the reader to *"this record's §3.0"*, which contains no preconditions at all — §3.0 records that the entitlement premise was retracted, which is a different thing. |
| **Delivery bar** | An envelope is authored with one recipient declared `signsVia: MACHINE_KEY`, carrying the neutral gate pair. The integrator calls the signature route with a declared subject naming a person and an assertion carrying their captured evidence. The recipient completes, the incremental PAdES lands with a mark that names the signing route as well as the person, the next step activates, and the session records ADR-0055 §2.1's recorded-only member — not `DIRECT_LINK`, since no link existed. The same call repeated is refused as a conflict naming the existing act. A second recipient on the same envelope, declared `OTP_EMAIL`, behaves exactly as they do today. |

---

## 1. Why this task exists

[ADR-0055](../adr/ADR-0055-delegated-signature.md) §1 states the gap; what belongs here is why it is
a task rather than a paragraph. **The domain change is small and lands in a type that four surfaces
read.** `AuthMethod` is a `Contract` enum with an anti-corruption mirror, so a member added on one
side fails the build on the other; the slot types validate it; the authoring request, the persistence,
the cross-BC read port, the signer-facing descriptor and the published OpenAPI all project it. None of
that is hard, and all of it is in one slice.

**The half that is genuinely new is the assertion record**, and it is new in a way the repository has
not done before: a structure whose every field is *someone else's claim*, which must never merge into
the fields holding our own observations and must never reach the event log.

## 2. What already exists (reuse, do not rebuild)

Every item below was read in the tree on 2026-08-24, not recalled.

- **The access-gate seam is already exactly the right shape.**
  [`SigningSession::start()`](../../src/F5Sign/Session/Domain/Aggregate/SigningSession.php) takes
  `accessGateIsOpen` and, when true, lands `AUTH_PASSED` with `authenticatedAt`, `accessGatePassedAt`
  and `accessMethodExecuted: ExecutedAuthMethod::DIRECT_LINK`. A delegated start is that constructor
  with a different executed method. **No new status, no new state machine.**
- **The signing gate already refuses the new member, for free.**
  [`SigningGate::requiring()`](../../src/F5Sign/Envelope/Contract/Type/SigningGate.php) rejects any
  method whose `issuesPerActChallenge()` is `false`. So ADR-0055 §2.1's rule that a delegated
  recipient faces no per-act challenge needs a **test**, not a guard.
- ⛔ **This bullet said the opposite until 2026-08-25 and would have shipped the retired design.** It
  read *"the access gate already admits it, for free … a member answering `true` to that predicate is
  admitted with no change to the constructor"* — residue of the catalog-member shape (ADR-0055 §7.1),
  in the section titled *do not rebuild what exists*, pointing the permissive way.
  [`AccessGate::requiring()`](../../src/F5Sign/Envelope/Contract/Type/AccessGate.php) refuses
  `DIRECT_LINK` **by name** and then anything failing `establishableWithoutSession()` — whose own
  docblock says *"exactly one member answers false"*. So a new member is **admitted** unless the
  constructor is changed. The recorded-only member needs an **explicit refusal in both constructors**
  (§3.1); it is not free, and building it as this bullet described yields an envelope with a door
  nobody can ever pass and a recipient stranded with no repair path.
- **The ordered-list rule already excludes it, for free.** Both slots require every member of a
  multi-member declaration to `deliversCode()`. That rule is untouched here: nothing delegated is
  declarable in a gate at all ([ADR-0054](../adr/ADR-0054-ordered-auth-method-list.md) §2.2).
- **The mirror is already enforced.**
  `ExecutedAuthMethodMirrorTest` asserts equal cardinality between the two enums, name-for-name
  executability in both directions, and `deliversCode()` agreement member by member. Adding to one
  side only reddens the build without a line being written here.
- **Idempotency is already solved twice over.** The session id is deterministic for
  `(tenant, envelope, recipient)` and `startIfAbsent()` creates-or-does-nothing in one statement; and
  [`SignForRecipientUseCase`](../../src/F5Sign/SignatureExecution/Application/UseCase/SignForRecipientUseCase.php)
  derives its execution identity from the session, so a redelivery finds its artifacts on the chain
  and writes nothing.
- **The declared subject already distinguishes the two cases.**
  [`DeclaredSubject`](../../src/F5Sign/Foundation/Actor/DeclaredSubject.php) has a reserved
  `f5s:none` meaning *no triggering human*, so ADR-0055 §2.6's refusal is a comparison against a
  constant, not a new grammar.
- **The whole downstream pipeline is untouched.** Consent, `SignatureCommitted`, `SessionCompleted`,
  the Signature Execution reactor, the PAdES artifacts, `RecipientSigned`, `RecordRecipientCompletion`,
  step activation and the seal all run because the delegated act is an ordinary commit.

## 3. What gets built

### 3.0 No entitlement gate in this increment

⚑ **This section said the opposite until 2026-08-24, on a premise that was checked and found false.**
It required an entitlement before the route could exist, arguing that a leaked API key cannot sign
today. It can: `POST /api/v1/signing-tokens` mints any recipient's token,
`POST /api/v1/signing/session` finds the neutral access gate every envelope carries by default and
mints the session credential, and `POST /api/v1/signing/commit` completes the act. Three shipped
routes, no delegation involved.

⚑ **Narrowed on 2026-08-25 and still standing, which is the part to read carefully**
([ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md)). All three links now refuse
an envelope no recipient could have read, so the clause that read *"mints any recipient's token with
**no status check**"* is retired — the mint answers `409 ENVELOPE_NOT_SENT` on a draft. What that
removes is the **silent** run: a forger must now send the envelope for real, which notifies its
actual recipients. On an envelope that **was** sent and carries the default neutral gate — every
envelope authored without a declared gate — the chain works exactly as described. So the premise
this section rests on is intact and `BL-184` stays open, narrowed.

So the route ships under `Authn::MACHINE_KEY` with the declaration of ADR-0055 §2.2 as its only
condition, and **nothing in this task is blocked on an authorization model**. The reasoning, the two
preserved candidate shapes, and the residual exposure are in
[ADR-0055](../adr/ADR-0055-delegated-signature.md) §2.8; the forge path itself is
[`BL-184`](../BACKLOG.md).

⛔ **Do not add a capability check here "while we are at it".** A gate on this route and not on the
three above is the appearance of a control, and it would read to the next agent as though the
surface were protected.

### 3.1 The declaration, and the recorded-only member

**Two separate things, and conflating them is what an earlier cut of ADR-0055 did** (§7.1):

1. `signsVia: SIGNING_PLATFORM | MACHINE_KEY` on the recipient — the sender's declaration, defaulting to
   `SIGNING_PLATFORM` so every existing envelope keeps its meaning.
2. One **recorded-only** member in [`ExecutedAuthMethod`](../../src/F5Sign/Session/Contract/Type/ExecutedAuthMethod.php)
   and its twin in [`AuthMethod`](../../src/F5Sign/Envelope/Contract/Type/AuthMethod.php), **refused by
   both gate constructors** exactly as `DIRECT_LINK` is. ⚠ **The declarable count does not move, and the number to quote is thirteen, not fourteen**: `DIRECT_LINK` is already declarable in neither gate, so the catalog's fourteen members are thirteen declarable ones plus one recorded-only. Afterwards: fifteen members, still thirteen declarable, two recorded-only.

⛔ **Both constructors need a NEW explicit refusal — it is not inherited.** `AccessGate::requiring()`
refuses `DIRECT_LINK` by name plus anything failing `establishableWithoutSession()`, and that predicate
answers `false` for `DIRECT_LINK` alone. Whatever the new member answers, it is admitted unless the
constructor names it. This is a code change in `Envelope/Contract/Type/`, not a test.

⛔ **And it is the thing a later reader will delete as dead weight** — a member no gate accepts looks
like a mistake until you know it is the point. Bar 2 of ADR-0055 §5 is what keeps it.

⚑ **The declaration's values are named after credential kinds and are NOT `Authn`.** A two-member
mirror in `Envelope\Contract\Type`; `Authn` has five cases of which three mean nothing as *who may
commit*. ADR-0055 §2.1 carries why.

Both twins answer all four predicates with their reasons in the docblock, not only their values.
`MAX_DECLARED_LIST_LENGTH` does not move — it derives from the delivered set, which this does not join.

⚠ **The catalog docblock cites a document that has to move with it.**
[`docs/ddd/signing-session-domain-model.md`](../ddd/signing-session-domain-model.md) § Ubiquitous
Language is named as what fixes the catalog's members, so it is part of this changeset. ⚑ And it needs
the **distinction**, not just a row: the count of *declarable* methods is unchanged at thirteen, and
what grows is the recorded-only set: **fourteen members and thirteen declarable today; fifteen and still thirteen afterwards**. A document reporting fourteen or fifteen *declarable* methods would be false in the direction that invites someone to declare one.

### 3.2 The invariant, and it is no longer inside `AuthRequirement`

`signsVia: MACHINE_KEY` requires the **neutral pair** — `AccessGate::open()` and
`SigningGate::none()`. Any other combination is refused at authoring (ADR-0055 §2.2).

⚑ **This moved.** An earlier cut put a narrower version inside
[`AuthRequirement::fromGates()`](../../src/F5Sign/Envelope/Contract/Type/AuthRequirement.php) — narrower
because it only refused a declared *signing* gate and left a declared access gate representable. The
rule now spans the requirement and the new declaration, which meet on the recipient, so that is where
it lives. `AuthRequirement` keeps knowing only about its own two slots.

### 3.3 The assertion record (ADR-0055 §2.5, §2.13, §2.17)

A `Pii`-classified structure with a **closed** set: three required — `subject`, `assertedConsentedAt`,
`assertedDocumentHashes` — and **three** optional — `assertedSignerIp`, `assertedSignerUserAgent` and
`assertedAuthMethod`. ADR-0055 §2.5 carries the table and why each is there.

⚑ **Corrected 2026-08-31, twice, and both corrections came from building it.** This sentence read
*"two optional … plus `assertedAuthMethod`"*, which left the sixth field unclassified: §2.5's table
says `no` and its prose calls it one of *"the three optional fields"*, with §2.14 and §5 bar 12 both
counting six. And the third required field was **`assertedDocumentHash`, singular**, which ADR-0055
§2.5 has since amended to a **map of `documentId → digest`**: an assertion belongs to a session, a
session is one per `(tenant, envelope, recipient)`, and that recipient signs *N* documents — *"one
PAdES signature each"* — so the singular was a cardinality error rather than a loose wording.

⛔ **`assertedDocumentHashes` is compared at commit, not merely stored.** A mismatch refuses. Storing
it without comparing gives a field that looks like a binding and is a decoration.

⛔ **Three ways to be wrong, and a one-arm test pins only the first**: a **content** mismatch on one
document; a map **missing** a document the recipient signs; and a map naming a document they do **not**
sign. Coverage must be exact, and the refusal must name the offending document rather than the set —
which is the half a single combined digest could never express, because it collapses *the content
changed* and *you did not sign all of it* into one opaque mismatch.

⛔ **Closed, and asserted as closed in a test.** PHPStan level 9 rejects a missing key and accepts an
extra one, so an absence check waves through the next field somebody adds (`CLAUDE.md` rule 5).

⛔ **It never reaches `platform.event_log`.** [ADR-0031](../adr/ADR-0031-event-log-store.md) gives the
log no application delete path.

⛔ **`Pii` classifies; it does not encipher.** The only rule attached to that marker forbids implicit
plaintext reads. **Nothing in this repository connects it to `FieldCipher`**, which still has no
callers — so *first caller of ADR-0033* becomes plaintext columns with a green build unless bar 12 is
written. ⚠ And it has a **deployment precondition nobody has named**: `FIELD_ENCRYPTION_SECRET` is
committed **empty** and `ConfigKeyProvider` refuses under 32 bytes, so this path fails closed in every
unprovisioned environment. Say so in `.env`'s header, or the first person to hit it will store in clear
to make the error go away.

⚠ **Deferred, and not by omission** (ADR-0055 §2.17): the signed assertion, its proof level, the
per-client key registry, and the mandate reference. Do not build them; do not leave hooks for them
either — the set is closed so that adding a field later is a decision.

### 3.3b The migration (ADR-0055 §2.14)

⛔ **Three tables, not two — an earlier cut listed only the session ones and omitted the field the whole
decision turns on.** `envelope.recipient` gains `signs_via`; `session.signing_session` gains the
`asserted_*` columns; `session.auth_attempt` gains the twin pair. `assertion_proof` and `assertion_jws`
are **deferred** with the signed assertion (ADR-0055 §2.17) and are not in this migration.

⚑ For `signs_via`, imitate `Version20260818000006.php`: `ADD COLUMN … DEFAULT` then `ALTER … DROP
DEFAULT`, so existing rows are backfilled without leaving a DB-side default that ADR-0019 §4 forbids. No new table, no `jsonb`, no new pattern — [ADR-0019](../adr/ADR-0019-database-schema-conventions.md)
§5 decides the shape and ADR-0055 §2.14 records the one naming variance and why.

⛔ **`signing_session` has grown by `ADD COLUMN` THREE times already**; this is the fourth and by far
the widest. ⚑ **Corrected 2026-08-31 — this read *"four times … this is the fifth"***, and the
near-miss that inflates it is `Version20260824000001`, which only *reads* the table in a backfill and
adds its columns to `envelope.recipient`. Anyone grepping `signing_session` hits it. Check the table against §5's other rules while in there — `TEXT` not `varchar(n)`, no
DB-side `DEFAULT` on domain columns, `timestamptz` for instants.

⚠ **`SchemaConformanceTest` enumerates `BC_SCHEMAS` by hand.** It is the trap `CLAUDE.md` authoring
rule 5 names by example: adding columns to a schema already in the list is fine, but confirm the list
covers what this migration touches rather than assuming it.

⚠ **RLS is not inherited by new columns but the policy is per table** — `signing_session` and
`auth_attempt` both already carry `ENABLE` + `FORCE` + a `current_tenant_id()` predicate, so nothing
new is owed here. Stated because it is the thing a reviewer will ask.

### 3.4 The delegated commit path

A use case that starts the session with the delegated executed method, then commits through
`SigningSession::commitSignature()` unchanged.

⛔ **It must re-read under `findLockedForUpdate()` before committing.** `startIfAbsent()` protects only
the creation of the row; the `FOR UPDATE` is what stops two concurrent calls both clearing
`alreadyCompleted` and appending two `ConsentRecorded` + two `SignatureCommitted` to a log with no
delete path. ⚠ **The `Integration/` tier cannot catch its absence** — one connection under DAMA
rollback — so bar 13 has to use [`ProbesRowLocks`](../../tests/F5Sign/Support/ProbesRowLocks.php).

⛔ **It passes `refreshDigest: null` and mints no credential** (ADR-0055 §2.4) — the act opens and
closes in one call, so there is nobody to hand one to. `StartSessionUseCase` already returns before
minting on a null digest, so nothing changes there. **Put the reason in the use case's docblock**: an
unexplained `null` at a call site is what the next reader repairs. Consent arrives asserted and is refused if absent —
the aggregate already throws `SigningConsentRequiredException`, so this is a mapping, not a guard.

### 3.5 The route

⛔ **The controller lives in `Session/UI/Http/`, not `Envelope/UI/Http/`.** `deptrac.yaml` grants
`EnvelopeUI` no access to `SessionContract` or `SessionApplication`, and these routes drive Session use
cases — placed under Envelope they do not build. Precedent:
[`MintSigningTokenController`](../../src/F5Sign/Session/UI/Http/MintSigningTokenController.php), a
`MACHINE_KEY` sender-side route on a non-`/signing/` path. Path params are Session's mirrors.

`POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature` under `Authn::MACHINE_KEY`, annotated with `#[OA\*]` per [ADR-0026](../adr/ADR-0026-openapi-documentation.md).
Refuses `f5s:none`. A repeat for an already-signed recipient is a conflict naming the existing act,
mapped through [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md) /
[ADR-0025](../adr/ADR-0025-rfc9457-error-shape.md).

**It also refuses a claimable slot nobody has claimed** (ADR-0055 §2.3), and the refusal is owed here
rather than on the mint: a delegated act mints nothing, so a guard on the issuance path never runs for
this route. Bar 20 asserts the absence of the session row, which is the thing that actually matters.

⛔ **Both refusal codes are choices this record has to make, and neither is inherited.**
[ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.4 splits the shape by
audience — 404 to a link holder who must not learn whether an id exists, 409 to the sender, who
already knows — and §3.3 of that ADR says in terms that *"the next surface has to make it again"*.
This route's caller is the sender's integrator, so **both the unsent-envelope and the unclaimed-slot
refusals are 409**, not the 404 the recipient-facing readers return. Reaching them through a reader
that answers 404 is the plausible mistake: it is one call away and it type-checks.

### 3.6 The machine-driven ceremony surface (ADR-0055 §2.11)

```
POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth/otp/send
POST /api/v1/envelopes/{id}/recipients/{recipientId}/auth
POST /api/v1/envelopes/{id}/recipients/{recipientId}/signature      (= §3.5)
```

Each declares `Authn::MACHINE_KEY` and drives the same use case its recipient-side twin drives. The
recipient's `signsVia` decides what the third demands: an assertion (`MACHINE_KEY`) or an
already-passed gate (`SIGNING_PLATFORM`).

⚠ **Flattened, not mirrored** — no `session` segment, because none is addressable here. Each route's
`#[OA\*]` summary should name its recipient-side twin, since the parallel has to be read rather than
seen (ADR-0055 §2.11).

⛔ **The machine ceremony DOES mint a session credential**, unlike the one-call delegated act
(ADR-0055 §2.4): the integrator holds several steps, exactly as a browser does. Two paths, opposite
answers, in one slice — the place to get it backwards.

⛔ **Do not build this by letting the integrator call the recipient's own routes.** They work when
called by a server, which is what makes the shortcut attractive, and ADR-0055 §7.7 records the two
defects it produces. The `#[OA\*]` annotations must not describe these as recipient routes.

### 3.7 The limiter's third key, as a valve (ADR-0055 §2.12)

On a machine-authenticated send the third counter is keyed on the **API client**, not on
`$request->getClientIp()`. A fourth policy pair joins
[`config/packages/rate_limiter.yaml`](../../config/packages/rate_limiter.yaml) and
`FailOpenOtpSendLimiter::policiesFor()` gains the machine arms.

⛔ **The machine numbers are a safety valve and the config comment must say so in those words.** They
are deliberately loose — of the order of ten times any expected peak — because their only job is that
a runaway loop cannot spend without bound. [`BL-189`](../BACKLOG.md) is the row that says this slice
builds them, and this sentence is the citation back it was owed. They are **not** a spend control: that is metering's, whose
call site already exists in `IssueAuthChallengeUseCase` and whose persistence is
[`BL-166`](../BACKLOG.md). A future reader who tightens these numbers "to control cost" will strand
real signers and still not control cost.

⛔ **The session and destination counters do not change, and that is half the decision.** They bound
what can happen to one person; only the third was ever about the caller. A refactor that unifies all
three "for symmetry" removes the person-facing protection this fix deliberately leaves alone.

⚠ **The existing `otp_sms_source` comment stops describing the whole ceiling** the moment the machine
pair lands — it describes the browser half. Update it in the same changeset (`CLAUDE.md` authoring
rule 1: config comments are a swept surface).

### 3.8 The three request-derived fields (ADR-0055 §2.5)

Three controllers read the request for an address — enumerate them with
`rg -n 'getClientIp|User-Agent' src/F5Sign/Session/UI/Http/` rather than from a list that rots. On
the machine surface each records a data centre.

**They keep their meaning and keep their value**: what was observed *is* the integrator's server, and
that is a true fact worth having in an incident. What changes is that it stops being the only answer
to *where did the signer come from*, because the asserted namespace of §3.3 now answers that
separately. Nothing is nulled and nothing is overwritten.

### 3.10 The fan-out does not invite a delegated recipient (ADR-0055 §2.15)

⛔ **The guard goes in [`SigningTokenIssuer`](../../src/F5Sign/Session/Contract/Service/SigningTokenIssuer.php), not in the fan-out.**
It has **three** callers — `NotifyActivatedStepRecipientsUseCase`, `NotifyCorrectedRecipientUseCase`
and [`SigningTokenIssuance`](../../src/F5Sign/Session/Application/Service/SigningTokenIssuance.php) —
and the second mints a token and sends the deep link after a contact correction. Guarding the first
alone leaves a corrected delegated recipient receiving a live signing link, which is exactly what this
decision exists to prevent (ADR-0055 §2.15). ⚠ **The membership changed on 2026-08-25 and the count
did not, which is why this list read as current when it was not.** `MintSigningTokenController` was
the third caller until [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) put
`SigningTokenIssuance` between it and the port; the controller now injects that service and no longer
names the port at all. Re-derive with `rg -n -- '->issueFor\(' src/` rather than trusting this
sentence.

`NotifyActivatedStepRecipientsUseCase` filters on step ordinal and on having an email, and on nothing
else — worth knowing, because the fan-out still needs `signsVia` to avoid composing a notification with
no link in it.

⛔ **And it needs it BEFORE the issuer call, not merely to compose the body — otherwise this guard
takes the whole step's fan-out down with it.** The issuer is called bare inside the per-recipient loop
and there is **no `try`/`catch` anywhere under `src/F5Sign/Notification/Application/`**. A delegated
recipient is a person the sender knows, so they have an email and the `email === null` skip does not
catch them: execution reaches the issuer, the guard throws, the exception escapes the loop, **every
remaining recipient of that step is never invited**, and the handler dead-letters. The refusal
belonging to the issuer and the fan-out needing a skip of its own are not alternatives — the first is
what makes the second load-bearing. Bar 21 is what stops a single-recipient fixture from certifying
the defect.

⛔ **The port DOES widen, and this bullet claimed otherwise until 2026-08-25.** `RecipientView` carries
`authRequirement` and **nothing called `signsVia`** — under the restructured shape the fan-out cannot
see the answer at all. ADR-0055 §2.15 and §3.2 say so and call it the one line item where the retired
shape was cheaper. An implementer following the old text finds no reason to filter.

⛔ **Without it the system emails a working signing link to somebody who signs elsewhere** — and the
expectation is one *we* created, which is worse than a link somebody found.

⚠ This is the fan-out's first filter keyed on what a recipient must **prove** rather than on whether
we can reach them. The comment beside the email check says role-differentiated inclusion is deferred;
this gives it a first member without discharging it.

⛔ **It is also the condition that crosses ADR-0055 §2.15's own threshold, and that is recorded rather
than acted on here.** That clause says *"the fourth should move the question rather than add to the
list"* — moving *which recipients are actionable* out of Notification, whose concept it is not, and
into Envelope. The threshold is crossed by this condition plus
[TASK-037](TASK-037-claimable-invitation-and-visibility.md) §4 D4's, so **neither slice's diff shows
the crossing**. ⚑ **Linkified 2026-09-02**: this read *"on the unmerged `docs/claimable-recipient`
branch"*, and that branch's work is in this tree (`ls docs/tasks/`). The same correction reached
[ADR-0055](../adr/ADR-0055-delegated-signature.md) on 2026-09-01 and did not reach its own task —
which is the shape the ADR's own note describes: two records each written while the other was
unmerged, and neither re-checked against the tree. Do not attempt the
move inside this task: it is a cross-BC concept move on the largest of the four slices, and it would
be reviewed by whoever is reviewing delegated signature. [`BL-196`](../BACKLOG.md) owns it and names
the trigger that should start it — a fifth condition, or
[TASK-031](TASK-031-channel-selection-beyond-email.md) deleting the `email === null` skip, whichever
lands first. What this task owes is the record, which is this paragraph.

⛔ **A present-tense sentence in a living doc goes false when this lands, and its diff will be empty**
— the rule-1 case. [`docs/ddd/notification-domain-model.md`](../ddd/notification-domain-model.md)
§ Open questions item 1 reads *"Today the reaction includes every recipient of the step with an
address."* That stops being true.

⚑ **Correct the sentence; do NOT close the question.** Item 1 asks which **roles** are invited; this
filters on the declared **method**. Two axes, and the second does not answer the first — a delegated
`SIGNER` is skipped while the role question is exactly as open as it was. Closing it here would
record a resolution nobody reached.

⚠ **Check before writing**: the Notification session may already have amended that item on its own
branch, marked as a pending change from ADR-0055 rather than as merged. Reconcile with what is there
instead of adding a second note saying the same thing.

### 3.11 A delegated recipient is refused before the credential (ADR-0055 §2.16)

⛔ **This is the guard the retired shape gave for free.** `RecipientAuthContext::accessGateIsOpen()`
is `$this->accessMethods === []`, so the neutral pair a delegated recipient carries reads as *open
door*: `StartSession` lands `AUTH_PASSED`, mints the credential pair, and the commit route admits the
act. Anyone holding a signing token for that recipient could sign through the ordinary recipient
surface, and the evidence would say `DIRECT_LINK`.

Two guards:

1. `POST /api/v1/signing-tokens` refuses an `MACHINE_KEY` recipient.
2. The pre-credential routes answer *this recipient signs elsewhere* **before** anything is minted.
   Needs `signsVia` on [`RecipientAuthContext`](../../src/F5Sign/Session/Application/Query/RecipientAuthContext.php),
   which is what routes 2 and 3 read across the Envelope boundary — a widening of an existing view,
   not a new seam.

⚑ **The same widening carries the claim facts, and it is one trip rather than two.** ADR-0055 §2.3's
unclaimed-slot refusal reads `declared_claimable` and `claimed_at`, which cross the same boundary on
the same view for the same reason. Carry all three fields in one change: two passes over one seam is
what [`BL-190`](../BACKLOG.md) already objects to for a neighbouring pair of fields, and the objection
applies here with nothing changed. ⛔ Note the ordering this creates —
[TASK-036](TASK-036-claimable-recipient-slot-and-claim.md) (claimable) lands the two columns, so
**it must land first**. ⚑ **Linkified 2026-09-02**, same correction as above: the *"cited by id and
deliberately not linked"* instruction outlived its condition. ⚠ The ordering constraint itself still
holds and is the reason this clause exists — it is now satisfied rather than pending, since
`integration/claimable-delegated` merges claimable **before** delegated. That is the order already recommended
for unrelated reasons, so the constraint costs nothing; it is recorded because a reader who reorders
the two branches would otherwise find the field missing and infer it was never wanted.

⚠ **Guard 1 alone is not enough and will look like it is.** A token minted before the declaration
changed is still live, and so is one minted by a caller who had reason to. Guard 2 is the one that
matters; guard 1 just removes the normal path.

⚑ **Reconcile with ADR-0056 at merge, do not build it twice.** *"A closed leg says so before the
credential"* lands on `develop` while this is in flight and does the same thing for a recipient whose
leg is terminal — same principle, different input. ⚑ It was not on this branch when this was written; `develop`
merged in on 2026-08-25, so it is [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md)
and the link resolves. Read it before writing anything, and prefer extending its seam to opening a
second one.

### 3.9 The visible mark — and it has a bar now

⚠ **ADR-0055 §3.3 calls this the clause most likely to be quietly dropped, and until 2026-08-25 it had
no verification bar anywhere.** Bar 11 is it. And per §3.3(b) it may be a **requirement rather than a
courtesy**: article 5.2 of the eCMR Additional Protocol wants the agreed procedure referenced in the
consignment note itself, and this is the only place this design writes into the document.


`SignForRecipientUseCase::markTextFor()` renders a delegated act as the person **and** the route by
which they signed (ADR-0055 §2.9). One method; the only place the record speaks to a reader who has
none of this context.

## 4. Scope

**In:** the two enums and their predicates; the cross-slot invariant; the assertion record and its
persistence; the delegated commit use case; the routes and their OpenAPI annotations; the machine
ceremony surface and the limiter's **machine-keyed source pair**; the three request-derived fields; the mark;
the signing-session domain model; the present-tense sentence in the notification domain model's open question 1; and ADR-0055's own `Status`, §5 and §6 at close.

⚑ **Owed at close, and easy to miss.** In [`docs/adr/README.md`](../adr/README.md), ADR-0055's own row moves off `Proposed`.

⚠ **And one incidental claim in an accepted ADR goes stale — check it, do not rewrite it.** [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) says *"the catalog stays at fourteen"* in the table row explaining why there is no `NONE` member. After this task the catalog has fifteen **members** while still having thirteen **declarable** ones. ⛔ **Its body stays as written** — an ADR is a historical record and `AUTHORING.md` says supersession is expressed in `Status` and nowhere else in the body. And its *argument* is untouched: it refuses a **neutral** in the catalog, and this task adds a recorded-only member for an event, not a neutral. The judgement call at close is whether ADR-0049's index row deserves a line saying the count moved while the reasoning held — this record's answer is **yes, one clause**, but it is a call and not a mechanical edit.

**Out, and each for a reason:**

- **The automatic variant** — a delegated recipient signed on step activation with no call. Deferred
  in ADR-0055 §2.7, not rejected.
- **The signed assertion, its proof level and the per-client key registry.** ⚑ This was listed in **both** In and Out until 2026-08-25. It is **Out** (ADR-0055 §2.17): it protects against the asserter lying, and here the asserter is the signatory's own employer.
- **The mandate reference** of ADR-0055 §2.13.
- **The counterparty-type field** that would refuse consumers — structurally absent in this case and required the moment an asserter can name somebody who is not its own.
- **The level-of-assurance field.** [`BL-74`](../BACKLOG.md) owns it and says the first move is a
  decision. This task must not invent one in passing.
- **The signing SDK.** ADR-0055 §2.10 refuses it as a catalog member in advance and names the mint
  route that already serves it. Nothing here is an increment towards it.
- **Restricting the method by counterparty type** (business versus consumer). Named as a risk in
  ADR-0055 §3.3; needs the contractual half first.
- **The Legal bounded context.** It has no `src/` tree, and the developer terms that would carry the
  integrator's obligations live there.
- **Closed recipient legs invisible to the pre-credential routes.** Proposed as scope for this task on
  2026-08-25 and **declined the same day**: that defect is about `RecipientOutcome::DELEGATED` and
  `SKIPPED` — legs that are *terminal, with nothing to sign* — where a recipient declared with the
  delegated **auth method** signs normally. The two share a word and nothing else, which is how the
  proposal arose. The originating session has since retracted the connection and measured that no code
  path or migration writes either outcome today, so the population is empty and the defect latent.
  It stays where it was raised.
- **Differentiated per-client budgets.** One configured ceiling per medium, keyed per client, is the
  increment; giving integrator A a different number from integrator B is a provisioning attribute
  and its own piece of work (ADR-0055 §2.12).
- **A cost alarm on the fail-open window.** Named as the natural companion in ADR-0055 §2.12 and
  deliberately not folded in — it is observability work with its own shape.

## 5. Key decisions

Taken in [ADR-0055](../adr/ADR-0055-delegated-signature.md) and not re-opened here. The ones most
likely to be argued back during implementation, with where the argument already lives. ⚑ **Corrected
2026-08-31: this said *"the three"* over a table of five**, which had been five since two more were
added and the count was not.

| Pressure | Answer | Where |
|---|---|---|
| "Just call `SignForRecipient` directly" | The artifacts are not the act — no session, no consent fact, no completion, and the envelope stalls | ADR-0055 §7.2 |
| "`DIRECT_LINK` already means *proved nothing to us*" | False in the overstating direction, and the two become indistinguishable exactly when someone needs to tell them apart | ADR-0055 §7.3 |
| "Put the asserted IP in `signerIp`, the column is right there" | It redefines a field that means *what we observed*, and the rows are indistinguishable afterwards | ADR-0055 §7.5 |
| "The integrator can just call the recipient's routes, it already works" | It works, and it is what produces the ten-SMS-per-hour cap and three fields naming a data centre | ADR-0055 §7.7 |
| "Unify the three limiter keys while we are in there" | Only the third was ever about the caller; the other two protect one person and must not move | ADR-0055 §2.12 |

## 6. Verification

Each property below names the tier that can actually reach it. Per `CLAUDE.md` authoring rule 4,
**sabotage each guard and watch it fail for the right reason** before citing any of these as green.

1. **The mirror holds.** Adding the member to one enum only reddens `ExecutedAuthMethodMirrorTest`.
   Verify by adding it to one side, running, then adding the other. (Unit.)
2. **Both gate constructors refuse the recorded-only member.** Not one of them — both. (Unit.)
3. **The neutral-pair invariant sweeps BOTH slots.** A recipient declared `MACHINE_KEY` with anything
   other than `AccessGate::open()` **and** `SigningGate::none()` is refused at authoring. Build it over
   the whole declarable set and drop one member to watch it fail **naming** it (`CLAUDE.md` rule 5).
   ⛔ An earlier cut aimed this at `AuthRequirement::fromGates()`, which **cannot see `signsVia`** — the
   bar was greenable by testing something else.
4. **`f5s:none` is refused.** (Acceptance.)
5. **The executed method is recorded as §2.1's member.** ⛔ Assert the recorded value, not
   that the ceremony completed — a delegated act that silently records `DIRECT_LINK` completes just
   as happily and the evidence is then wrong in the only field that carries this task's meaning.
   (Integration.)
6. **Asserted evidence never appears in an event-log payload.** Written as a **closed key-set**
   assertion. PHPStan level 9 rejects a missing key and accepts an extra one, so an absence check
   waves through the next field somebody adds. (Integration.)
7. **No bar** — ADR-0055 §2.8 takes no entitlement. Kept as a numbered placeholder rather than
   removed, so the later numbers keep their addresses and a shortened list is not read as a met one.
8. **The repeat converges visibly.** The same call twice yields one signature, one set of artifacts,
   one `SignatureCommitted`, and a conflict on the second. Assert the artifact count, not just the
   status code. (Integration.)
9. **A non-delegated recipient on the same envelope is byte-identical on the wire** to today.
   (Acceptance.)
10. **Two clients do not consume each other's send budget.** ⛔ The discriminating case is **two**
    clients: with one, the defective source key and the correct client key behave identically, so a
    single-client test is decorative. Drive two ceremonies from two clients and assert neither is
    refused. (Integration.)
11. **The session and destination counters are consumed identically on both surfaces.** This is the
    half of ADR-0055 §2.12 that must not change; sabotage it by keying one of them on the client and
    watch this test fail. (Integration.)
12. **The signature route fails closed on both arms**: an **assertion-carrying call** for a
    `SIGNING_PLATFORM` recipient is refused, and a **missing assertion** for a `MACHINE_KEY`
    recipient is refused. (Acceptance.) ⚠ This bar said *"a missing **challenge** for an
    `MACHINE_KEY` recipient"* until 2026-08-25, and there is no such state: ADR-0055 §2.2 forces that
    recipient onto `SigningGate::none()`, so a challenge whose absence could be refused cannot be
    authored. Written from the printed bar, this test would have pinned an unreachable state and
    passed for ever.
13. **A token-holder for a delegated recipient is refused before a credential exists.** ⛔ Assert that
    **no credential was minted**, not that the commit failed — refusing at the commit passes a naive
    test while leaving a credentialled session behind. And assert it for a token minted *before* the
    declaration changed, which is the case the mint-side guard cannot reach. (Integration.)
14. **No bar** — the proof level and the signed assertion are deferred (ADR-0055 §2.17). Kept numbered
    so the addresses below do not shift.
15. **No request-derived address reaches a field meaning an observation, on the machine surface.**
    ⚠ A green run here proves the mapping, not the honesty — assert the recorded value, not that the
    call succeeded. (Integration.)

16. **The visible mark of a delegated act names the route as well as the person.** ⚠ ADR-0055 §3.3 calls
    this the clause most likely to be quietly dropped, and it had no bar at all until 2026-08-25.
17. **The assertion block is enciphered at rest.** ⛔ `Pii` classifies and does not encipher — nothing
    connects the marker to `FieldCipher`. Without this, six plaintext PII columns ship green.
    ⚠ Provision `FIELD_ENCRYPTION_SECRET` first: it is committed empty and the provider refuses under
    32 bytes.
18. **Two concurrent delegated calls produce ONE signature**, one `ConsentRecorded`, one
    `SignatureCommitted`. ⛔ Second connection via [`ProbesRowLocks`](../../tests/F5Sign/Support/ProbesRowLocks.php).
    The `Integration/` tier runs one connection under DAMA rollback, where a missing `FOR UPDATE` is
    invisible — item 8 is sequential and proves nothing about this.
19. **`assertedDocumentHashes` is compared at commit and a mismatch refuses.** Assert the refusal, not
    that the field was stored. ⛔ **Three arms** (ADR-0055 §5 bar 14, amended 2026-08-31): a content
    mismatch, a missing document, and a document the recipient does not sign. Each refuses, and the
    refusal names the document rather than the set.
20. **The signature route refuses a claimable slot nobody has claimed**, as a 409 naming the
    unclaimed state (ADR-0055 §2.3). ⛔ Assert that **no `signing_session` row exists** afterwards,
    not merely that the call failed. The failure this bar exists for is a session opened over a party
    with no identity, and a refusal taken at commit time passes a naive test while leaving that row
    behind — the same shape item 13 guards on the credential side. (Acceptance.)
    ⚑ Holds since 2026-11-04 ([TASK-078](TASK-078-the-machine-routes-refuse-an-unclaimed-slot.md)): `DelegatedCommitOnAnUnclaimedSlotHttpTest::a_delegated_commit_on_a_slot_is_refused_and_keeps_no_session`.
21. **A delegated recipient does not break the fan-out for everybody else on their step.**
    ⛔ The discriminating fixture is an activated step carrying a delegated recipient **and** at least
    one ordinary one, with the delegated recipient **first** in the roster. Assert the ordinary
    recipient is invited. `NotifyActivatedStepRecipientsUseCase` calls the issuer bare inside the
    per-recipient loop and there is no `try`/`catch` anywhere under
    `src/F5Sign/Notification/Application/`, so a refusal that throws there takes the rest of the step
    with it and dead-letters the handler. A single-recipient fixture cannot fail and would certify
    the defect. (Integration.)

⚠ **Where a green run would not mean anything, and must be said rather than assumed**: the substance
of this feature is whether the integrator's assertion is true, and no harness in this repository can
reach that. ADR-0055 §5 closes on the same point. Do not let a full green board read as *this is
safe*. ⚑ The count is deliberately not quoted here — it was *"nineteen"* until items 20 and 21
landed, and a hand-maintained tally in a sentence about not over-reading the tally is the first thing
to rot.

## 7. Open follow-ups (track, don't solve here)

Each of these needs a [`docs/BACKLOG.md`](../BACKLOG.md) row at close, with its id derived by grep at
the moment the row is written — across every local and remote ref, not against `develop` alone. Ids
are deliberately not reserved here: a number claimed in a task record and written into the backlog
days later is exactly how five ids collided on one branch.

- **The authorization model** that §3.0's stand-in stands in for, if the narrow grant is what ships.
- **The signed assertion** — accepting a JWS from the integrator's own key, and what the platform
  does with it. The evidentiary upgrade ADR-0055 §2.5 wants and does not mandate.
- **The automatic variant** of ADR-0055 §2.7.
- **Differentiated per-client send budgets**, and the provisioning attribute that would carry them.
- **A cost alarm on the limiter's fail-open window** — at integration scale the `error` log line is
  the only thing between a store outage and a bill on a paid channel.
- **The per-integrator spend control itself** — [`BL-166`](../BACKLOG.md)'s metering persistence,
  plus a `PlanEnforcer` question for code issuance. Until it lands there is **no** spend control on
  this channel, only the valve; ADR-0055 §2.12 takes that deliberately and says why.
- **Consumer counterparties** — whether a delegated declaration may name one at all, blocked on the
  contractual half.
- **The developer terms** carrying the integrator's obligation to authenticate and to retain their
  own logs, owned by a Legal bounded context that does not exist.
- **[`BL-74`](../BACKLOG.md) is not a new row** — it already owns the level-of-assurance gap. What
  this task owes it is an updated statement: the gap stops being latent once two materially different
  kinds of act share one representation.


---

## 8. Where this was paused, 2026-08-28

⚑ **Appended at the end, and nothing above is renumbered** — the `§N` headings are anchors cited from
[`docs/BACKLOG.md`](../BACKLOG.md) (`BL-189` → §3.7, `BL-196` → §3.10) and from ADR-0055.

### 8.1 What is committed and green

`a1e0453` and `8d93135`, both validated by `make -C ../f5sign-infra wt-backend src=$(pwd)` on the
lane's own cluster. The counts are in the `Status` row. Everything committed is gated.

⚑ **Updated 2026-08-31 — four more commits, each with its own lane run on the lane's own cluster.**
The two above were measured before the base branch moved, so their counts do not describe this tree.

| Commit | What closed | Lane |
|---|---|---|
| `e4108bc` | merge of `origin/feat/claimable-recipient-slot` (§8.6b), taken first and gated on its own | `OK (2509 tests, 12210 assertions)` |
| `dac5498` | §3.10's three guards, their four bars and the published 409 enumeration (§8.5 step 1) | `OK (2513 tests, 12223 assertions)` |
| `cbbcab1` | the `ISSUER_CALLERS` delegated axis (§8.4, §8.5 step 2) | `OK (2515 tests, 12233 assertions)` |
| `993d1e7` | §3.11 / ADR-0055 §2.16 guard 2 on the session open (§8.5 step 3) | `OK (2518 tests, 12260 assertions)` |

⚑ **The merge produced no conflicts**, which §8.6c did not predict — it expected a mechanical one in
`Recipient.php` and `Envelope.php`. Both auto-merged. ⚠ It also touched a **third** file that §8.6c's
two-file conflict surface did not name, `SigningTokenIssuance.php`, which mattered only because the
uncommitted guards were sitting on it: the guards had to be set aside as a patch before the merge and
re-applied after its lane pass. Recorded because the next person merging a moved base with a dirty
tree hits the same thing.

⚑ **Updated again 2026-08-31 — steps 4 and most of 5 are done.** Later commits, each with its own lane
run on the lane's own cluster:

| Commit | What closed |
|---|---|
| `518bcc1` | `DeclaredSubject::toString()`, discharging that type's own `Never` with the user's assent |
| `fc6c71e` | `AssertedEvidence`, closed at six fields, `Pii`-classified |
| `3e172f8` | the migration + persistence; a census refused the `auth_attempt` half |
| `1c11800` | the singular→map re-cut of `assertedDocumentHashes` |
| `b6ed335` | `startDelegated()` + `recordAssertedEvidence()`'s three arms |
| `3cbc6e7` | the delegated commit use case, and the digest map that made two of three refusals real |
| `e9f17bf` | the route, its controller and four acceptance cases |
| `b077f81` | the delegated visible mark (§3.9) |

Final lane on this state: **`OK (2539 tests, 12427 assertions)`**, four gates.

⚑ **§3.6 and §3.7 landed too — the section below is kept as the record of why they were coupled and
what shape the coupling forced.** The machine ceremony's two routes exist
(`SendRecipientAuthOtpController`, `SubmitRecipientAuthResponseController`), the signature route is
dual-mode, and the limiter has its client-keyed arm. ⛔ **`RECIPIENT_SIGNS_HERE` is retired**: it was
correct only while no machine surface could pass a gate, and §3.6 is exactly what made that false. Its
replacement is `AssertionNotApplicableException`, whose two codes are bar 12's two arms.

⚠ **Still not done: §3.6's routes have no acceptance tests of their own.** They drive the same use
cases their recipient twins do, which are covered — but the machine routes' own wiring (path-derived
scope, the client-keyed limiter arm, the credential the relay returns) is exercised by nothing. That is
the honest gap in this branch and the first thing to write next.

⛔ **Why they were one coupled piece — kept because the reasoning outlives the work:**

- **§3.6** is NOT two more routes beside `/signature` — it is a **second mode of the route that already
  exists**, plus the two authentication routes that make it reachable. ADR-0055 §2.11's case is a
  `SIGNING_PLATFORM` recipient with a real method whose ceremony the integrator *relays*: we mint the
  code, the person reads it on their own handset, they type it into the integrator's screen. That is
  not delegation and must not be declared as it. For them the signature route must demand an
  **already-passed gate** instead of an assertion, so `RECIPIENT_SIGNS_HERE` becomes conditional.
  ⚠ **Change the guard and the routes together**: leaving it while adding the routes strands the
  ceremony at its last step, and removing it before they exist admits an act with no authentication
  behind it on either surface. Both the controller and the exception carry this note in their
  docblocks.
- ⛔ **The machine ceremony DOES mint a session credential**, opposite to the one-call delegated act
  (§2.4). Two paths, opposite answers — §3.6 names this as the place to get it backwards.
- **§3.7** has **no caller until §3.6 exists**, which is why it is not built: a limiter arm nothing
  invokes is the same dead surface `AuthChildTableHydrationTest` already refused for `auth_attempt` in
  this branch. ⚠ Its implementation has a shape trap worth knowing first: `policiesFor()` returns one
  `$prefix` from which all three policy names are derived, and §3.7 forbids the session and destination
  counters from changing — so the machine arm cannot be expressed by swapping one factory. Widen the
  tuple to carry three names, or split selection into medium × caller kind.
- **§3.8** needs no code. The three request-derived fields keep their meaning and their value; what
  changed is that they stopped being the only answer to *where did the signer come from*, and
  `CommitDelegatedSignatureController` records that where it reads them.

### 8.2 ⛔ ~~What is in the working tree, uncommitted, and must NOT be committed as it stands~~

⚑ **Discharged 2026-08-31 — everything below is COMMITTED and lane-green** (`dac5498`, four gates,
`OK (2513 tests, 12223 assertions)`). All four things it said were owed were written before the
commit: the discriminating bar-21 fixture, a bar for door 1, a bar for door 3 carrying **both** halves,
and a sabotage of each. The section is kept, struck rather than deleted, because the *reasoning* below
is why each guard has the shape it has — a `continue` and not a `throw`, a send-side refusal and not a
write-side one — and that argument outlives the working-tree state it was written about. Read the rest
as the record of a decision, not as an instruction.

Four files carrying **§3.10's three guards** plus the exception they throw:

- `SigningTokenNotIssuableException::recipientSignsElsewhere()` — code `RECIPIENT_SIGNS_ELSEWHERE`.
- `SigningTokenIssuance::issueFor()` — door 1, the mint (ADR-0055 §2.16 guard 1).
- `NotifyActivatedStepRecipientsUseCase` — door 2, a `continue` **before** the issuer call.
- `NotifyCorrectedRecipientUseCase` — door 3, a `return` **before** the issuer call.
- plus the mint route's published 409 enumeration, which listed two codes and now lists three.

**PHPStan and Deptrac are green on them. There are no tests and no lane run.** A patch of the exact
state is at `var/task-runner/TASK-033/uncommitted-guards.patch` (gitignored, so it survives on disk
and not in git — §8.5 is what makes it reproducible without it).

⛔ **What they still owe before any commit:**

1. **Bar 21's discriminating fixture** — an activated step with a delegated recipient **and** at least
   one ordinary one, the delegated **first**, asserting the ordinary one is still invited. A
   single-recipient fixture cannot fail and would certify the defect. The issuer is called bare inside
   the loop and `rg 'try\s*\{' src/F5Sign/Notification/Application/` returns **nothing**, so a guard
   that threw would take the whole step down and dead-letter the handler — which is why door 2 is a
   `continue` and not a `throw`.
2. A bar for door 1 (the mint answers 409 `RECIPIENT_SIGNS_ELSEWHERE`).
3. A bar for door 3 with **both halves**: the correction itself still **succeeds** for a delegated
   recipient, and **no link is sent**. Without the first half somebody "completes" this by moving the
   refusal to the write edge, mirroring ADR-0057, and breaks a correction that should have worked.
4. Sabotage each, and count the targets against what this record requires.

### 8.3 Decisions already taken — do not re-open

1. **`BL-195` / where the guard lives.** The **accepted** placement wins (ADR-0058 §2.3, ADR-0057
   §2.5): **nothing on the `SigningTokenIssuer` port**, three guards on the three callers. The reasons
   are measured rather than deferential — the port takes **three strings** and holds no view, so a
   guard there needs a fresh cross-BC read on every mint, while all three callers already hold the
   `RecipientView`; and the port's own docblock says *"This is a storage seam, not a domain guard"*.
   ⛔ **This means ADR-0055 §2.15's stated MECHANISM is superseded while its intent is realized**, and
   saying so is owed at close.
2. **One branch**, not staged.
3. **The assertion ships in the clear for now** — see §8.6.

### 8.4 ⛔ The hole this leaves open, and it is not optional

ADR-0058's census grants its exemption to a **trigger**: `StepActivated` only fires on a sent
envelope, so Notification's callers need not re-ask about `sentAt`. **No trigger settles `signsVia`** —
a step activating says nothing about whether a given recipient signs by machine key. So
`ISSUER_CALLERS` in
[`SigningReadersRefuseUnsentEnvelopeTest`](../../tests/F5Sign/Session/Application/Query/SigningReadersRefuseUnsentEnvelopeTest.php)
**cannot carry this question as written**: a fourth caller arrives, its author writes a row with a
perfectly true `sentAt` trigger argument, and the delegated hole reopens with a green build.

**Owed:** widen that census so a row must also name a case proving its caller refuses a delegated
recipient. Without it the three guards are correct today and defend nothing tomorrow.

⚑ **DISCHARGED 2026-08-31** in `feat/delegated-signature`. `ISSUER_CALLERS` rows are now five
elements — the count, the `sentAt` proof, and a **delegated-axis** proof — and
`every_issuer_caller_row_names_a_case_that_exists()` resolves both pointers, failing with the caller's
name when either rots. The asymmetry is written into the map's docblock: column one may be answered by
a trigger argument, columns four and five may **only** be answered by a case that drives a delegated
recipient, because no trigger settles `signsVia`. The fourth caller's proof
([`DelegatedRecipientRefusedHttpTest`](../../tests/F5Sign/Session/Acceptance/DelegatedRecipientRefusedHttpTest.php))
did not exist and was written for it; `SeedsSentEnvelopes` gained a `signsVia` parameter to seed one.
Sabotaged by rotting the fan-out pointer: the census fails naming
`NotifyActivatedStepRecipientsUseCase` and the missing case.

### 8.5 The order to resume in

⚑ **Steps 1 and 2 are done as of 2026-08-31**, both lane-green on their own runs; the base-branch
merge §8.6b required landed first, also with its own lane pass. Step 3 is where the next session
starts.

1. ~~Tests + sabotage for the three guards → lane → commit.~~ **Done** — `dac5498`, lane
   `OK (2513 tests, 12223 assertions)`, four gates green.
2. ~~Widen `ISSUER_CALLERS` (§8.4) → commit.~~ **Done** — lane `OK (2515 tests, 12233 assertions)`.
3. ~~§3.11 — `signsVia` on `RecipientAuthContext` and the pre-credential routes.~~ **Done
   2026-08-31** — lane `OK (2518 tests, 12260 assertions)`. ADR-0056's seam was extended rather than
   duplicated: the fact rides the crossing the edge already makes, as a **translated `bool`**
   (`signsElsewhere`) beside `envelopeIsAlive`, and `StartSessionUseCase` refuses above
   `startIfAbsent()` so nothing is minted. Bar 13 is held at two tiers — the hermetic one asserts the
   repository was never touched, the acceptance one drives a token minted **before** the declaration
   changed and asserts no `signing_session` row. Both sabotaged through the lane. ⚠ **The wire shape
   is still owed to `f5sign-signer`** — see §8.9. Original note follows. **Extend ADR-0056's
   seam, do not open a second.** ⚑ Two thirds of §3.11 as written is stale: TASK-036 put the claim
   conjunction on `RecipientView::isUnclaimedSlot()`, not on the context, so what is left is
   `signsVia` alone — and if the context ever needs the claim facts, mirror the **accessor**, never
   the two raw terms. ⚠ Bar 13 asserts **no credential was minted**, not that the commit failed, and
   for a token minted **before** the declaration changed. The wire shape is a contract question with
   `f5sign-signer`.
4. §3.3 + §3.3b (the assertion and its three-table migration) — the largest piece.
5. ~~§3.4, then §3.5~~ **done** (`b6ed335`, `3cbc6e7`, `e9f17bf`); ~~§3.9~~ **done** (`b077f81`);
   ~~§3.8~~ **needs no code** — see §8.1. ⛔ **§3.6 and §3.7 remain and are one coupled piece** — see
   §8.1 for why, and for the two traps that decide their shape.
6. `docs-sync`, `security-audit-core`, `task-close`.

### 8.6 Deferrals owed a `docs/BACKLOG.md` row at close

- ~~**The assertion persists in the CLEAR.**~~ **[`BL-214`](../BACKLOG.md) minted 2026-08-31**, with the
  provisioning blocker named as the reason it could not simply be done. ⚠ The id was taken from an audit
  across **every local and remote ref**, not from this tree: this worktree's `docs/BACKLOG.md` tops out
  at `BL-209` while another ref already reached `BL-213`, so the obvious next id would have collided —
  which is the failure `CLAUDE.md` authoring rule 7 records. Original note follows. Taken deliberately. `FieldCipher` still has no callers and
  `FIELD_ENCRYPTION_SECRET` is empty in `.env` and absent from `.env.dev` / `.env.test`. **§6 bar 17 /
  ADR-0055 §5 bar 12 is UNMET and declared**, not omitted — that bar exists precisely because six
  plaintext PII columns otherwise ship with a green build.
- **`BL-196` gets a better argument than it carries**: two of the three guards land in Notification,
  more weight than ADR-0055 §2.15 anticipated when it reasoned the port would absorb all of it.
- ~~**`BL-189`** already says *"TASK-033 §3.7 builds it"*; §3.7 does not cite it back.~~ **§3.7 now
  cites it**, in the paragraph separating the valve from the spend control.

### 8.6b The base branch moved after §8 was written — merge it FIRST, and gate it

⛔ **`origin/feat/claimable-recipient-slot` is five commits ahead of this branch's merge base as of
the pause**, and it is **not** docs-only: seventeen files, ~600 insertions, including two
`fix(task-036)` commits that change behaviour and edits to
[`RecipientTest`](../../tests/F5Sign/Envelope/Unit/Domain/Entity/RecipientTest.php), which is where
§8.2's bar 3 census lives. So expect a real merge there rather than a fast-forward.

**Do this before anything else, and give it its own lane run.** The two lane-green commits on this
branch were measured *before* those fixes existed, so their counts do not describe the merged tree.
Merge, do not rebase — this repo's history uses merges (`e83b061`).

⚑ **`BL-209` exists already; do not open a second row for it.** It is on that branch (cited by id
rather than linked, because the row is not in this tree until the merge) and it owns the per-route
`#[OA\*]` code-enumeration check — the gap §8.7's last bullets describe. It carries the implementation
trap this slice supplied: a route's reachable codes are **not** statically obvious from its
controller, because `RECIPIENT_SIGNS_ELSEWHERE` is thrown two layers down inside
`SigningTokenIssuance`, so a census reading only the controller's own `throw`s would pass this very
case with the stale enumeration in front of it. The row names the sabotage that proves otherwise.

### 8.6c The merge surface, measured — and one landmine that applies before it

Reported by the TASK-036 session and **verified here against this tree**, so it is a measurement
rather than a relay.

**Nine commits since the base at `013a758`, of which only TWO change behaviour.** The other seven are
docs, `BL-209` among them. So the merge is smaller than its 600-line diff suggests, and what needs
re-validating is bounded:

- `0802326` — `Recipient::claim()` was erasing `email` / `phone` when the claim omitted them. A
  correctness fix; the writes are now conditional.
- `c1c0516` — adds `Recipient::guardClaimable()` and `Envelope::guardRecipientCouldBeClaimed()`.

**Conflict surface: two files, `Recipient.php` and `Envelope.php`, and it should be mechanical.** Both
new methods sit adjacent to `claim()`. `signs_via` touched this branch's constructor, `create()`,
`rehydrate()` and the accessor block — none of which that branch moved, and no signature there
changed.

⛔ **The landmine, and it applies to THIS branch already rather than only after the merge.**
[`EnvelopeCredentialRetirementTest`](../../tests/F5Sign/Envelope/Unit/Domain/Aggregate/EnvelopeCredentialRetirementTest.php)
holds a `RETIRES` census that reflects over **every public `Envelope` method whose first parameter is
a `RecipientId`** — mechanically, every gesture the sender aims at one recipient — and compares that
derived universe against the map. Verified present in this tree at the pause.

So **if any remaining part of TASK-033 adds such a method, that census red-lines naming it**, and the
failure will look like an unrelated credential-retirement problem. It is not: the answer is a row in
the map recording whether that gesture retires this recipient's credentials, and why. ⚑ Worth knowing
before it fires rather than after — `§3.4`'s delegated commit path drives Session use cases rather
than Envelope gestures, so it may never fire, but `§3.6`'s machine ceremony surface is the part most
likely to reach for one.

⚑ `create()` and `rehydrate()` are outside that universe by construction — neither takes a
`RecipientId` first — which is why `signs_via` did not trip it.

### 8.7 Corrections this slice found and owes at close

- ~~**ADR-0055 §5 bar 2** says the property *"keeps the declarable catalog at fourteen"*; its own §2.1
  says thirteen.~~ **Corrected 2026-08-31** — bar 2 now says thirteen, which four other places in that
  ADR already said.
- ~~**This record's `Decision record` row** sends the reader to *"the two non-code preconditions in
  this record's §3.0"*.~~ **Corrected 2026-08-31** — it now names ADR-0055 §3.3's contract and its
  three legal questions directly.
- ~~**§5** says *"the three most likely to be argued back"* over a table of **five** rows.~~
  **Corrected 2026-08-31.**
- ~~**§3.3b** says `signing_session` has grown by `ADD COLUMN` four times; it is **three**.~~
  **Corrected 2026-08-31**, with the near-miss migration that inflates the count named.
- **§3.7's two counting axes.** *"The limiter's third key"* is exact; *"the limiter's fourth policy
  pair"* parses only on an axis the tree never uses (six policies in **two trios**). And
  `FailOpenOtpSendLimiter::policiesFor()` takes **only** `DeliveryMedium` and matches exhaustively over
  it, so it cannot "gain the machine arms" without its input changing — that is redesign, not a case.
- **[`docs/ddd/notification-domain-model.md`](../ddd/notification-domain-model.md) § Open questions
  item 1** carries a pending note naming `AuthMethod::INTEGRATOR_ASSERTED` and keying the guard on the
  **access gate** — the shape ADR-0055 §7.1 retired. It needs **correcting**, not extending, and §4
  Scope as written declares only *"the present-tense sentence"*.
- **`docs/BACKLOG.md` `BL-183`** asserts in the present tense that the member is
  `INTEGRATOR_ASSERTED` and a *"fifteenth catalog member"*. Both false after the re-cut. Its
  *historical* clause about the confusion is correct and stays.

### 8.8 Harness notes for whoever picks this up

`make -C ../f5sign-infra wt-backend src=$(pwd)` — the four gates on the lane's own cluster.

- ⚠ `flock` allows **one backend lane at a time** and the TASK-036 session uses it heavily.
- ⛔ **Do not edit the tree while a lane is running or queued** — it bind-mounts your tree, so it
  would validate a mixture.
- ⛔ **Do not read a green out of a chained `$?`.** `make …; echo EXIT=$?; grep …` reports the
  **grep's** status; that is how a run with one failure got reported here as exit 0. Run `make` alone.
- `vendor/` is installed in the worktree, so lint / PHPStan / Deptrac run fast ad hoc; anything
  touching the database goes to the lane, without exception.

### 8.9 ⛔ Owed to `f5sign-signer`: a published code it does not route

`POST /api/v1/signing/session` can now answer **409 `RECIPIENT_SIGNS_ELSEWHERE`** (ADR-0055 §2.16
guard 2, landed 2026-08-31). That is a **recipient-facing** route, so the code reaches the signer app,
and it is new to it.

⛔ **This is a cross-repo contract change and it is NOT this repo's to make.** Per the workspace rule
*one task = one repo*, the backend half is done and the frontend half is a coordinated PR in
`f5sign-signer`. Recorded here rather than fixed here.

**What the other side needs**, stated so nobody has to re-derive it:

- `useSignerNavigation.errorCodeToPath()` already routes `RECIPIENT_DELEGATED`, `STEP_NOT_ACTIVE` and
  `ROLE_NOT_INTERACTIVE` to `/unavailable` (measured by `f5sign-signer` and recorded on
  [`BL-183`](../BACKLOG.md)). `RECIPIENT_SIGNS_ELSEWHERE` wants the same destination and is not in
  that map. <!-- OFFREPO: that function is in `f5sign-signer`; nothing here can verify it, and the
  claim is a relay of BL-183's measurement rather than a fresh one. -->
- ⛔ **Do not route it to whatever `RECIPIENT_DELEGATED` means to a human reading the code name.**
  The two are opposites and were confused once already in one afternoon: that member is a **terminal
  leg reassigned to somebody else**; this is a **live** recipient who signs normally, elsewhere. The
  destination happens to coincide; the reason does not, and any copy written from the word will be
  wrong the moment the copy is read.
- ⚠ **Until it lands, the failure mode is a degradation rather than a hole.** The backend refuses and
  mints nothing either way — the guard is server-side and complete. What a recipient sees is whatever
  the app does with an unrecognised `code`, which is a worse message, not a signable document.

⛔ **AND A LIVE DEFECT THE HANDOFF UNCOVERED, which is not this task's and is not hypothetical.**
Reported by the `f5sign-signer` session on 2026-08-31 while wiring the above, and it concerns a
decision **this** repo owns. <!-- OFFREPO: the client-side half is `f5sign-signer`'s measurement;
nothing here can verify or re-run it. -->

`ENVELOPE_NO_LONGER_LIVE` — the 409 [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md)
introduced, thrown by `StartSessionController` and `GetSigningSessionController` — is **undeclared in
their `errorCodeToPath()`**, so it falls to their default, and a declared 4xx that is not a service
fault routes to the *invalid link* screen: *"Este enlace no existe o ha sido revocado."*

⚠ **That is the exact outcome `GetSigningSessionController`'s own published `#[OA\*]` prose tells
clients to avoid**, in as many words: *"show them that the document was cancelled, rather than the
broken-link screen a 404 would earn."* And ADR-0059 §2.5 chose a **conflict over a not-found** on the
reasoning that the recipient *"is told, rather than handed an answer indistinguishable from a wrong
id"*. End to end, today, they are handed exactly that. The backend half is right and the sentence is
still false where it counts — on the screen.

⚑ **Live on `develop` now, not created by this branch.** It has nothing to do with delegated
signature; it surfaced only because someone finally read that mapping against the backend's codes.
`CREDENTIAL_RETIRED` is undeclared there too, but is milder and should self-heal: it is a 401, and
their client treats any 401 as a credential rejection and reopens with the emailed link, which is the
remedy [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) prescribes anyway.

⚑ **The client half LANDED the same day** — `f5sign-signer` `990accf`, reported 2026-08-31 — so this
stopped being a live defect within hours of being found. It routes `ENVELOPE_NO_LONGER_LIVE` to their
*declined* screen with a subtitle of its own, and the subtitle is the part worth recording here:
their existing one said *"the envelope was rejected or voided"*, which is **false for the completed
and expired members** of the same predicate, so reusing it would have reproduced this exact class of
lie one level down. The replacement names no member. They also declared `CREDENTIAL_RETIRED`, and
deliberately did **not** hand-edit their OpenAPI snapshot, which stays behind until it can be measured
against a live backend.

▶ **What is left is verification, not repair.** ⚠ And the honest bound on it: the client half is
covered by **unit tests only**. The shape that produces the code is not reachable from their mock, and
the backend half is not something that side can drive — so *"ADR-0059 §2.5's outcome is true end to
end"* is **not** established by either suite alone and will not be until someone exercises the pair.
That is the claim to re-check on merge.

▶ **Ownership settled 2026-08-31**: this record keeps it and `f5sign-signer` mints nothing, so one
fact has one home. Whether it also earns a `BL-` row is left to whoever next opens
[`docs/BACKLOG.md`](../BACKLOG.md) with a current view of it — deliberately not minted mid-slice,
because an id taken from a stale view is how five collided here once (`CLAUDE.md` authoring rule 7).

⚑ **The same code on `POST /api/v1/signing-tokens` needs nothing from the signer app** — that route is
`MACHINE_KEY` and sender-facing. One code, two audiences, and only one of them is a browser.
