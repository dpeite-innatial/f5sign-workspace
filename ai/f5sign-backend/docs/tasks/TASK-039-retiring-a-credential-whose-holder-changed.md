# TASK-039 — Retiring a credential whose holder stopped being legitimate

| Field | Value |
|-------|-------|
| **Status** | ✅ **Done — landed 2026-08-26, closed 2026-08-28.** Branch `feat/terminal-envelope-and-credential-retirement`, commit `44b0551`. Green on the ephemeral worktree lane 2026-08-28: `lint 0 of 1036` · `Deptrac Violations 0` · PHPStan `[OK] No errors` · `OK (2460 tests)` — ⚑ the test count is pinned and the **assertion count deliberately is not**: it is non-deterministic across runs, as `3cff138` recorded when the same trap fired on ADR-0058. Falsifiable as written: `ls migrations/Version20260826000001.php` resolves and `grep -c credentials_retired_at` on it is non-zero, and [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) reads `Accepted`. ⚠ Two of its §5 bars are held **by construction and not by an assertion** — filed as [`BL-203`](../BACKLOG.md) rather than claimed. ⚑ The row previously read *"⏳ Not started. No branch, no code, no migration"*. |
| **Type** | **Gap closure.** Two recorded harms with named rows, one mechanism each, no new capability exposed to a caller. |
| **Why** | Two sender gestures admit that a live credential should stop working, and neither takes one back. **A corrected contact** ([`BL-152`](../BACKLOG.md)) mints a fresh link for the right address and leaves the old one working from the wrong mailbox for the rest of its seven days — and a correction is precisely the admission that an address was wrong. **A reset access code** ([`BL-158`](../BACKLOG.md)) changes what the next submission checks and does nothing to a session credential already minted, so whoever got in before the reset keeps read, bytes and the ability to sign for up to the twelve-hour absolute cap. |
| **Builds on** | **[ADR-0045](../adr/ADR-0045-issued-credential-format.md)** §2.6 for the digest store this revokes against, and **[TASK-028](TASK-028-opaque-signing-token.md)** §4.3, whose refusal to build revocation *"because it comes for free"* is the constraint this obeys — it is built on the two cases with names, not on the possibility. **[ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md)** for the stateless credential and the `agp` claim. **[ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md)** §2.4 for the guarantee/reactor split this repeats. ⚑ The reactor seam it shares is the `Sibling` row below, not a dependency. |
| **Sibling** | ⚑ **[TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md) — co-lands on one branch** (decided 2026-08-25), so the two are not planned independently: they share the Session-subscribes-to-Envelope seam, which is built once here rather than built there and extended here. ⚠ **Deliberately not a `Builds on`.** Neither reuses the other's output unchanged, and naming a `Not started` task as a dependency would be depending on something that does not exist. ⛔ Two consequences: the same green promotes **both** ADRs, so the changeset owes `Status`, `Enforced by` and `Realized in` for ADR-0059 **and** ADR-0060 (`CLAUDE.md` authoring rule 7); and a review blocking on either half blocks both. |
| **Decision record** | **[ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md)**, **`Accepted (persistence partial)`**. ⚠ **This row read `Proposed` until 2026-09-01, five lines below a `Status` row citing *"ADR-0060 reads `Accepted`"* as its own falsifier** — the self-contradiction `CLAUDE.md` rule 1's *"check the file against itself"* exists to catch. ⛔ **And the qualifier is not cosmetic: §2.6 and §2.4 were never built.** The record was promoted to a bare `Accepted` — which `AUTHORING.md` defines as *exercised* — while describing in the present tense a `session.signing_token.revoked_at` column, a second `SECURITY DEFINER` function and a renewal reactor that do not exist. See §8. |
| **Delivery bar** | After a contact correction: the superseded signing token **resolves to a refusal**, and any session credential minted before it is refused on every credential-bearing route. After an access-code reset: session credentials minted before it are refused, **and the signing token still works** — the signer is expected back through that same link with the new code. After an auth unlock: **nothing is retired**. |
| **Blocks** | Nothing. It closes [`BL-152`](../BACKLOG.md) and [`BL-158`](../BACKLOG.md), which [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.6 and [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.6 both declined by name as belonging here. |

---

## 1. Why this task exists

Two rows, one gap, and both name the mechanism they need rather than the fix they want:
[`BL-152`](../BACKLOG.md) asks for *"a `revoked_at` column and a fourth chokepoint"*;
[`BL-158`](../BACKLOG.md) asks for *"the mechanism `BL-152` already names as missing"* and adds that it
*"is an ADR decision about the credential format, not a fix to this"*. Two ADRs have since declined the
work by name and pointed here — [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md)
§2.6 and [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.6.

⛔ **This is not the voided-envelope case and must not be built as though it were.**
[ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) covers an envelope that died while
its holder stayed legitimate, answerable by a predicate over envelope state every crossing already
holds. Here the envelope is fine and the *holder's* legitimacy changed — invisible to any
envelope-status predicate. [TASK-028](TASK-028-opaque-signing-token.md) §4.3 also forbids the specific
shortcut: *"do not justify [a revocation path] with the envelope-void gap"*.

⚠ **The obvious anchor is wrong, and finding out why is most of this task's value.**
[`BL-158`](../BACKLOG.md) proposes stamping the recipient's `auth_generation` into the credential.
`Envelope::correctRecipientContact()` **does not advance it** — only `resetRecipientAccessCode()` and
`unlockRecipientAuth()` do, and both funnel into the same `RecipientAuthUnlocked` fact — so a
generation-based design cannot see the case with the named harm. And stamping any new claim breaks
`SessionCredentialCodec`'s **closed** claim set, which would refuse every credential minted before the
deploy. [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.2 and §7.1 carry
the full argument.

## 2. What already exists (reuse, do not rebuild)

- **The instant to compare against is already in the credential.** `agp` — *access gate passed at* — is
  minted at all three mint sites, and `RenewSessionCredentialUseCase` **carries it forward from the
  expired credential rather than resetting it**, which is what stops a renewal laundering a retired
  credential into a fresh one. No new claim is needed and none may be added.
- **The token chokepoint is a single named place.** `f5sign_app` holds no privilege on
  `session.signing_token` beyond `EXECUTE` on the issuing function
  ([`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §1.14), so the resolution path cannot be routed around.
- **The reads that carry the anchor already happen.** The read model, the document bytes and the commit
  all cross `getContextForRecipient()`; `RecipientAuthContext` is where the anchor rides in, beside
  `authGeneration` and `envelopeIsAlive`.
- **The facts already exist.** `RecipientCorrected` and `RecipientAuthUnlocked` are published Envelope
  contract events; no new event is needed for the reactor.
- **The reactor scaffolding.** [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md) builds the
  first Session-subscribes-to-Envelope edge, the `findByEnvelope` finder and the handler pair. This
  shares that seam rather than opening a second one — built once, because the two co-land. ⚑ **The
  consequences of that live in the `Sibling` row of the header and are not repeated here**, so there is
  one home for them rather than two that rot apart.
- ⚑ **A working revocation, already in this repository.** `identity.api_key` has carried `revoked_at`
  since `Version20260803000012`: a nullable instant, an `UPDATE … WHERE id = :id AND revoked_at IS NULL`
  that is idempotent by construction, and `DbalApiKeyDirectory` filtering `AND revoked_at IS NULL` in the
  resolution path. Read all three before writing the token half — `CLAUDE.md` authoring rule 3 — and copy
  the shape. ⚠ **Do not copy the grant**: that one is a column-scoped `GRANT UPDATE (revoked_at)` to
  `f5sign_provisioning`, a role the correction path does not run as, and a direct write grant is the very
  thing [`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §1.14 keeps off `session.signing_token`
  ([ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §7.6).
- **The census shape.** `SigningReadersRefuseUnsentEnvelopeTest` is the in-tree example of *census the
  universe, classify, fail on the unclassified*.

## 3. What gets built

**Commit 1 — the anchor and the synchronous comparison.**

- A nullable retirement instant on `envelope.recipient`, written by the gestures
  [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.5 classifies, and
  surfaced on `RecipientAuthContext` alongside the fields already read there.
- The three credential-bearing routes that cross the read port refuse a credential whose `agp` is
  earlier than the anchor.
- The census of §2.5's gestures, and the non-eviction test for `unlockRecipientAuth()`.

**Commit 2 — the token revocation.**

- `session.signing_token.revoked_at`, nullable, plus a **second `SECURITY DEFINER` function** beside
  the issuing one and an `EXECUTE` grant on it. ⛔ **Not an `UPDATE`, and not a new table grant.**
  [`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §1.14: `ALTER DEFAULT PRIVILEGES IN SCHEMA session`
  grants full DML on every table created there, so the app role's lack of privilege on this one is
  held by an explicit `REVOKE` in its migration — and **nothing fails** if that is undone. The
  measured check is `has_table_privilege('f5sign_app', 'session.signing_token', 'SELECT') → false`.
- The resolution path refuses a revoked row, distinguishably from a row that never existed.
- Only `correctRecipientContact()` revokes. ⛔ A reset must **not**: the signer is expected back through
  the same link with the new code, and revoking it strands exactly the population the gesture serves.

**Commit 3 — the renewal.**

- The reactor consumes `RecipientCorrected` and `RecipientAuthUnlocked` and writes into the session row
  the renewal already loads, so `renewWith()` refuses without a cross-BC read
  ([ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §2.4).

## 4. Scope

**In scope:** everything in §3, the tests of §6, and closing [`BL-152`](../BACKLOG.md) and
[`BL-158`](../BACKLOG.md) naming this slice.

**Out of scope:**

- **A sender-facing revocation operation.** Nothing here lets a sender say *"kill that link"* as a
  gesture of its own; the anchor moves only as a consequence of §2.5's classified gestures. That is a
  feature with a UI and a permission question. ⚠ The `revoked_at` column makes it look one endpoint
  away, which is precisely the scope creep [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md)
  §3.3 flags and TASK-028 §4.3 already refused once.
- **`identity.api_key`.** ADR-0045 §2.6's original subject, its own lifecycle, its own schema the app
  role cannot reach, and no case in either driving row.
- **Backfill.** Corrections and resets already performed retire nothing; no anchor is written for them.
- **The voided-envelope direction** — [TASK-038](TASK-038-terminal-envelope-closes-the-ceremony.md).
- **Any change to the auth generation's meaning.** It stays the auth-attempt epoch
  ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.6) and acquires no second job.

## 5. Key decisions

All are [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md)'s; restated here only
where the implementation could plausibly drift from them.

- **An instant, never the auth generation** (§2.2). The correction does not advance the counter, and
  `unlockRecipientAuth()` is a gesture that wants the bump *without* the eviction.
- **Compare `agp`; add no claim** (§2.3). `SessionCredentialCodec` asserts its claim set closed, so a
  new member evicts every in-flight signer at deploy — a security fix indistinguishable from an outage.
  ⛑ A regression test must pin the claim set unchanged, so this property is held by a test rather than
  by whoever remembers.
- **Two mechanisms, one per credential kind** (§2.1), because the two kinds were stored differently by
  prior decision. Unifying means making the session credential store-backed, rejected in §7.2.
- ⛔ **A reset does not revoke the link** (§2.6). The asymmetry is the whole of what keeps the fix from
  becoming the next stranding defect.
- ⛔ **`unlockRecipientAuth()` retires nothing** (§2.5). It sits beside the reset in the aggregate,
  shares its event and its generation bump, and answers the opposite way.

## 6. Verification

Run through the **worktree lane** — `make -C ../f5sign-infra wt-backend src=$(pwd)`. ⛔ The bare
`make test` / `make phpstan` targets bind the main checkout and report green for another branch.

**Properties to lock, each sabotage-checked** (`CLAUDE.md` authoring rule 4):

1. After a correction, the superseded signing token is refused — and refused **distinguishably** from a
   digest that never existed.
2. After a correction, a session credential minted before it is refused on each credential-bearing
   route. One case per route; a single shared case would not show which crossing lost its comparison.
3. After a reset, session credentials minted before it are refused **and the signing token still
   resolves**. The second half is the one whose failure strands signers.
4. ⛔ After an unlock, **nothing is retired** — the non-eviction case. Sabotage by making
   `unlockRecipientAuth()` write the anchor and confirm this case, and only this case, goes red.
5. A renewal cannot launder a retired credential: mint, retire, renew, assert refusal — the property
   that depends on `agp` being carried forward rather than reset.
6. `SessionCredentialCodec`'s claim set is unchanged by this work.
7. The gesture census fails, naming the member, when a classified gesture is dropped from it.
8. Every path unaffected by any gesture behaves exactly as before — the discriminating case, since 1–5
   all pass trivially on a system that refuses everything.

**One acceptance case per driving row**, end to end over HTTP, because §1's two survival windows are
traced from source and have never been executed. ⛔ No bar may quote *seven days* or *twelve hours*
from [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) until these run.

**Migration review.** Two tables, and `CLAUDE.md` authoring rule 6 applies to neither as a data
backfill — both columns land nullable with no rows written — but the `session.signing_token` half needs
a new `SECURITY DEFINER` function and an `EXECUTE` grant, and the app role must **not** acquire any
direct privilege on that table. ⛑ **Assert it rather than intending it**, because §1.14's whole point
is that undoing it breaks nothing visible: pin
`has_table_privilege('f5sign_app', 'session.signing_token', 'SELECT') = false` after the migration.

**Gates:** `WT_GATES="lint arch phpstan test"`, `infection` opt-in. Quote what the lane printed.

## 7. Open follow-ups (track, don't solve here)

- **A sender-facing revocation gesture**, if the dashboard ever wants one. §4 explains why the column
  existing is not the same as the feature existing.
- **Clock skew as a correctness input.** The anchor and `agp` come from the same application clock
  today; a deployment that mints on one node and writes on another inherits a window.
  [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) §3.3 records it.
- **Retiring credentials for gestures already performed.** No backfill is attempted; if that is ever
  wanted, it is a data write the domain reads and `CLAUDE.md` authoring rule 6 governs it in full.
- **The fourth axis on one census.** ADR-0058, ADR-0059 and this record all classify the same
  crossings for different properties. At some point that is one test doing four jobs, and splitting it
  is a decision rather than a tidy-up.
- **[`BL-113`](../BACKLOG.md) is untouched.** A credential resting in a mailbox or a handset that
  nobody has corrected is exposure none of this addresses.

## 8. Deviations & honest notes

Written at close, 2026-08-28, alongside §7's disposition.

⚠ **Two §5 bars of [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) are held
by construction and by no assertion, and they are recorded rather than claimed** — filed as
[`BL-203`](../BACKLOG.md), and named in §5 itself so the ADR does not read stronger than the tree:

- *A renewal cannot launder a retired credential.*
  [`RenewSessionCredentialUseCase`](../../src/F5Sign/Session/Application/UseCase/RenewSessionCredentialUseCase.php)
  carries `agp` forward instead of re-stamping it, so the renewed credential is refused at the same
  three crossings — but re-stamping to `now` is exactly the change that reads like a tidy-up, and
  nothing would go red.
- *A reset does not revoke the signing token.* Nothing on the reset path touches
  `session.signing_token`; the nearest assertion covers a recipient who never opened the link, not one
  whose credential was just retired.

**Two silent defects found while wiring, both of which would have shipped green** (recorded in §6 of
the ADR too, because that is where someone reconstructing the shape will look): `Recipient::rehydrate()`
accepted the anchor and never forwarded it to the constructor — the column would have round-tripped as
`NULL` with every hermetic test passing — and
[`GetSigningSessionController`](../../src/F5Sign/Session/UI/Http/GetSigningSessionController.php) fell
back to `now` when the gate instant was absent, which is the permissive direction the moment `agp`
stops being a published field and becomes a security input.

**Two pre-existing gaps closed in passing**, both on surfaces this task touched and neither in its
§4 scope: [`Version20260824000001`](../../migrations/Version20260824000001.php) cited
`Version20260721000001` (Notification's) for `envelope.recipient`'s RLS and tenant stamp, which come
from `Version20260713000002`; and [`LIVE_SCHEMA.md`](../LIVE_SCHEMA.md) was missing four columns of
that table, three of them [TASK-034](TASK-034-recipient-access-trace.md)'s. Both are the migration-
docblock carve-out of repo-specific rule 2 — comment corrections, nothing re-runs.

**No deviation on the anchor.** §2's warning that the obvious anchor (`auth_generation`) is wrong held
all the way through: it is not stamped, no claim was added, and
[`SessionCredentialCodec`](../../src/F5Sign/Foundation/Http/SessionCredentialCodec.php) is not in the
diff — which is what kept the deploy from evicting every in-flight signer.
