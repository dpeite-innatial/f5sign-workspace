# TASK-028 — The signing token becomes opaque: closing ADR-0045's recorded non-conformance

| Field | Value |
|-------|-------|
| **Status** | **Done** — landed on `develop` from `feat/opaque-signing-token` (12 commits), `make qa` green (1711 tests, PHPStan L9, deptrac 0, lint 0, Infection covered-MSI 87% against a floor of 79). ⚑ **A commit range is deliberately not cited here**: the branch was rebased twice while `develop` moved under it, so any sha written during the work is a dead pointer. `git log --grep='TASK-028'` is the durable locator. Every credential this system issues is opaque; §2.3's non-conformance is discharged in [ADR-0045](../adr/ADR-0045-issued-credential-format.md). ⚠ **Three pieces are deliberately NOT in it and are tracked rather than assumed**: the legacy-encoding window at the edge and the codec's retirement ([`BL-148`](../BACKLOG.md)), `SIGNING_TOKEN_SECRET`'s six surfaces in `f5sign-infra` ([`BL-149`](../BACKLOG.md)), and the handoff to `f5sign-signer` ([`BL-150`](../BACKLOG.md)). See §7. Originally a forward plan written 2026-08-17, split out of [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) so the material *decision* could land without carrying a migration of a live credential behind it. |
| **Type** | **Conversion of a live credential.** Not a feature. Nothing a recipient can see changes; what changes is what a leaked link teaches its finder. |
| **Why** | The recipient signing token discloses `(tenant, envelope, recipient)` to anyone holding it, because its claims half is plain `base64url`. [ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.3 records this as the grammar's **one known non-conformance** — recorded rather than carved out — and names the measured defect behind the rule: a recipient read a true tenant id off their own credential and replayed it at the sender edge (`BL-38`, claim laundering rather than forgery). The token travels by email, so it is the credential most likely to end up somewhere its holder did not put it. |
| **Builds on** | [ADR-0045](../adr/ADR-0045-issued-credential-format.md) (the grammar the token joins), [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §1.1 (the observation that unblocks it), [ADR-0044](../adr/ADR-0044-principal-resolution-at-the-edge.md) (the narrowly-exempt-lookup limb this reuses), [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) (the ADR this amends). |
| **Decision record** | [ADR-0045](../adr/ADR-0045-issued-credential-format.md). **Nothing new is decided for this task** — that ADR already fixed the material (opaque, store-backed, digest-stored) and already recorded this token as its one non-conformance. What was missing was not a decision but a blocker, and [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §1.1 reports it dissolved. **The shape is still open** — §4 lists what this task must decide, and any of it that turns out to be cross-cutting is an ADR change, not a silent edit. On landing, ADR-0028's stated constraint is amended, per repo-specific rule 7. |
| **Delivery bar** | A recipient's link carries an opaque credential conforming to [ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.1–§2.5. Decoding it yields nothing about tenant, envelope or recipient. The full ceremony runs end to end against it — open session, read model, bytes, commit — and `make qa` is green. |
| **Sequencing** | **Immediately after [TASK-029](TASK-029-session-credential-and-refresh.md), in the same `f5sign-signer` window** — see §5. Not gated by [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md), [TASK-022](TASK-022-delivered-codes-over-email.md) or [TASK-023](TASK-023-sms-codes-and-recipient-phone.md). |
| **Breaking** | **Yes, for `f5sign-signer` and for any link already in a mailbox.** The cutover window is one token expiry rather than a coordinated rotation — [ADR-0045](../adr/ADR-0045-issued-credential-format.md) §3.2 already priced this as cheap as cascades go — but the schedule is not ours alone. |

---

## 1. Why this task exists

[ADR-0045](../adr/ADR-0045-issued-credential-format.md) decided that every credential F5Sign hands outside its trust boundary is **opaque**: its plaintext may say what kind of thing it is and nothing else. The finder of a leaked credential must learn only *"this is an F5Sign credential of kind K"*, because identifiers inside a credential turn a leak into an intelligence disclosure that **survives revocation** — the revoked credential stops working, the tenant id it taught does not stop being true.

The signing token violates that on two counts that [ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.3 shows are really one. Its `base64url(claims)` half is readable by anyone holding it, and because `base64url` uses `_`, its body cannot satisfy the grammar's alphabet rule either — so it cannot even carry the family marker while keeping its claims. The two counts close at the same moment: **one fix, one moment, one cascade.**

That ADR deferred the fix on a stated blocker: *"This ADR does not solve the pre-scope lookup that gates it."* An opaque credential must be looked up in the database; a tenant-scoped query cannot run before the tenant scope exists; the lookup is what would establish it.

**That blocker is gone, and [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §1.1 is where it is recorded.** [`DbalApiKeyDirectory`](../../src/F5Sign/IdentityAccess/Infrastructure/Persistence/DbalApiKeyDirectory.php) already resolves an opaque credential to a tenant with **no tenant scope set**, against `identity.api_key` and `identity.api_client` — tables deliberately left RLS-free as [ADR-0044](../adr/ADR-0044-principal-resolution-at-the-edge.md)'s explicitly-exempt-lookup limb. It authenticates every `MACHINE_KEY` route today. The pattern this task needs is built, shipped and exercised; what is missing is a second instance of it.

⚑ **The interesting part of this task is not the code — it is that nobody noticed.** The constraint dissolved when the machine half shipped, in a branch about a different credential, and no record was updated. Two ADRs went on citing it as live. Whatever else this task produces, the amendment to [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) §1 is the part that stops the next reader re-deriving a false constraint.

## 2. What gets built

**A token kind under [ADR-0045](../adr/ADR-0045-issued-credential-format.md)'s grammar.** A marker, a body length, and the family control trailer — the same shape `ak` has, registered as its own kind. §2.1–§2.5 of that ADR are the spec; this task does not reinterpret them.

**A lookup table and its resolver**, mirroring [`DbalApiKeyDirectory`](../../src/F5Sign/IdentityAccess/Infrastructure/Persistence/DbalApiKeyDirectory.php): RLS-free by construction, storing a **digest** of the presented credential and never its plaintext ([ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.6), returning the `(tenant, envelope, recipient)` triple plus expiry. Read the sibling before writing this one — where the two differ, the difference is either a bug in one or a decision, and it must be resolved rather than copied.

**Two minting paths that store instead of encoding, not one.** [`MintSigningTokenController`](../../src/F5Sign/Session/UI/Http/MintSigningTokenController.php) is the sender-facing one. ⚑ **[`NotifyActivatedStepRecipientsUseCase`](../../src/F5Sign/Notification/Application/UseCase/NotifyActivatedStepRecipientsUseCase.php) is the other, and it is the one that mints the token a recipient actually receives** — it composes the invitation link. Each hardcodes its own `+7 days`, independently, with nothing holding the two together; a stored credential expires by column, so the two reconcile into one.

**The signer's client-side validation, which fails closed before any network call.** `f5sign-signer`'s `signingToken.ts` validates with a regex requiring **exactly one dot**; an opaque credential has none. Its global middleware redirects to the invalid-token page **before the first fetch**, so every emailed link would land there with no request made and nothing to diagnose. ⚑ **And the signer's own suite would not catch it**: its fixtures use UUIDs almost everywhere, so only one unit spec pins the real token shape. This is the single highest-risk item in the cutover and it lives in another repo.

**The retirement of [`SigningTokenCodec`](../../src/F5Sign/Foundation/Http/SigningTokenCodec.php)** and of `SIGNING_TOKEN_SECRET`, once no caller remains. ⚑ **Check the whole surface, not the diff** ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 1): `rg -n 'SigningTokenCodec|SIGNING_TOKEN_SECRET' src tests migrations docs config .env* CLAUDE.md`. `.env.dev` carries a working dev value and the load-order header in `.env` names the variable in prose. ⚑ **Three surfaces argue *from* this variable and lose their subject when it goes**, so they need rewriting rather than deleting: [`CLAUDE.md`](../../CLAUDE.md) repo rule 4 uses it as the canonical pattern-(A) example *and* as the counterexample in its "not transferable" caveat; [`ConfigKeyProvider`](../../src/F5Sign/Foundation/Crypto/ConfigKeyProvider.php) names it as the by-convention counterparty of the 32-byte floor; and [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.2 and §6 cite the codec as a live comparison.

⚑ **And the sweep leaves this repository.** `../f5sign-infra` carries `${SIGNING_TOKEN_SECRET:?...}` in its production compose file — a **hard boot failure** that will keep demanding a dead variable after the backend stops reading it — plus `.env.prod.example` and a README runbook line stating that rotating it invalidates issued signing links, which stops being true.

**Expiry, and what replaces `exp`.** The claim currently expires the token by itself; a stored credential expires by column, and something must remove dead rows.

## 3. Scope

**In scope:** the kind registration; the table + migration + RLS exemption; the resolver and its wiring at the [ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md) seam; the minting path; expiry and cleanup; the codec's retirement and the secret's removal; the `#[OA\*]` updates on every route whose credential description changes; the amendment to [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) and the status update to [ADR-0045](../adr/ADR-0045-issued-credential-format.md)'s non-conformance clause; the handoff to `f5sign-signer`.

**Out of scope:** the session credential and everything in [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.2 — that is [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md)'s. The `Authn` enum gains no case here: the token keeps `SIGNING_TOKEN`, and only what verifies it changes.

## 4. What this task must still decide

Named here rather than left implicit, because [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) deliberately stopped at the material:

1. **The kind marker and body length** — [ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.4 requires each kind to pin its own length so its pattern stays a tight anchor.
2. **Expiry mechanics** — a column plus a sweep, or expiry evaluated at read. Whichever is chosen, a dead row must not be servable and must not accumulate forever.
3. **Whether the row is revocable, and by whom.** Storage makes revocation *possible*; it does not make it a feature. ⛔ **Do not build a revocation path on the reasoning that it comes for free**, and do not justify one with the envelope-void gap: [TASK-015](TASK-015-envelope-void.md) owns that, and clearing a credential checks nothing about whether an envelope is voided, completed or its step still active — the domain guard is broader than one condition and is needed regardless. ⚑ **Note that [`BL-87`](../BACKLOG.md)'s argument *against* an edge-level revocation lookup dissolves here**, since after this task an unscoped read happens on every recipient request by construction. That removes an objection; it does not supply a reason.
4. **Where the table lives.** `session.` and `identity.` are both defensible and the choice has RLS consequences; [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) governs.
5. **The cutover with `f5sign-signer`** — whether both formats are accepted for one expiry window, or the cut is hard. ⚠ A dual-accept window means two verifiers live at once, which is exactly what [ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md) §2.2 forbids for a *route*; if it is chosen, state precisely why this does not breach that rule.

## 5. Why this rides with TASK-029

⚠ **An earlier cut of this section sequenced this task after [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md), and its reasoning no longer applies.** That reasoning was to avoid two `f5sign-signer` cascades; the cascade has since moved out of TASK-021 into [TASK-029](TASK-029-session-credential-and-refresh.md), which is where the route partition and the new credentials now live.

So the pairing is with TASK-029, and it is tighter than "adjacent". That task changes **which credential** three routes accept; this one changes **what the token is**. Both are breaking changes to the same client, both need the same coordinated release, and shipping them a few weeks apart means asking another team to touch its credential handling twice. One window, two backend PRs, one signer PR.

⚠ **The carry-across, now aimed at TASK-029:** nothing in that slice may assume the token is parseable. It has no reason to — [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3 keeps `SIGNING_TOKEN` on routes 1 and 2 and changes nothing about what it is — but a helper that reads a claim out of the token string becomes this task's problem. One grep at the end of that slice rather than a surprise at the start of this one.

## 6. Acceptance bars

1. **Nothing is readable.** Decoding a minted token by any standard means yields no tenant, envelope or recipient. This is the bar the task exists for; write it as a test that fails against today's token, so it is discriminating rather than decorative.
2. **The pre-scope lookup works, and is exercised as such.** A request arrives with no tenant scope, the resolver establishes it from the credential, and the tenant is never read from request input. Sabotage-verify: point the resolver at an RLS-protected table and watch it RAISE, per the fail-closed `current_tenant_id()` predicate.
3. **A wrong or corrupted credential is refused at the edge**, by checksum, before the digest is computed and before any query runs ([ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.5).
4. **The plaintext is never stored — and the test must name BOTH places, or it passes while being false.** Assert on the column contents rather than the write path, since a digest column holding a plaintext is invisible to a test that only checks the writer. ⛔ **The second place is `notification.notification.variables`**, which stores the composed invitation link with the live token inside it, indefinitely, and which a test written against the new lookup table sails past in green ([`BL-113`](../BACKLOG.md)). Fixing that storage is Notification's problem and explicitly not this task's; **asserting honestly about it is this task's**, because this is the bar that would otherwise certify a property the system does not have. If the second assertion cannot be made true here, it must be written as a documented failing expectation rather than dropped.
5. **The full ceremony is green end to end** against the new credential, including the seal loop.
6. **The sweep of §2 leaves no survivor**, `CLAUDE.md`, `.env*` and `../f5sign-infra` included. Two in-tree docblocks argue *against* this change and will read as instructions not to do it unless rewritten: [`CredentialKind`](../../src/F5Sign/Foundation/Credential/CredentialKind.php) states that adding a signing-token kind "is not a gap to fill", and [`BearerCredential`](../../src/F5Sign/Foundation/Http/BearerCredential.php) asserts that both credentials are unpadded base64url. Neither has a test that reddens.
7. **The new lookup table is enrolled in `SchemaConformanceTest`.** It checks exemptions in both directions and will red on an unclassified table, which is correct — but the classification is an argument to make, not a slot to fill.
8. **[ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) and [ADR-0045](../adr/ADR-0045-issued-credential-format.md) are updated in the same changeset.** Realizing a record is the mirror of landing one ([`CLAUDE.md`](../../CLAUDE.md) authoring rule 7): ADR-0045's `Status` names the non-conformance as live, and it stops being live here. The cheap detector is the sibling record — if ADR-0045 still says the token stands outside the grammar after this lands, this bar is unmet.

---

## 7. What was decided, and what deviated

Written on landing. §4 named five open decisions; four were taken here and one turned out not to be
the choice it looked like.

**§4.1 — marker and body length.** `st`, 30 base62 characters, so the published pattern is
`f5s_st_[A-Za-z0-9]{36}`. Same width as `ak` and `sr` deliberately rather than by copying: all three
are bearer credentials with no second factor, and this one's shorter life is not a substitute for
entropy — the window an attacker gets is the credential's life, not ours.

**§4.2 — expiry.** Both, in different places, because they answer different questions. *Not
servable* is the edge comparing `expires_at` to the clock on every request, so correctness never
depends on a job having run. *Not accumulating* is `app:signing-token:purge`, with a 30-day grace so
a lapsed link still yields *"expired"* rather than a bare refusal.

**§4.3 — revocation.** Not built, as §4.3 instructs. Issuance is additive: a re-invitation does not
invalidate the link already in a mailbox, and `SigningTokenIssuer` says so where a caller will read
it rather than leaving it to be discovered.

**§4.4 — where the table lives.** `session.`, and the deciding fact was not the one §4.4 anticipated.
It is not about `identity.` being defensible: `f5sign_app` holds **no `USAGE` on the `identity`
schema**, deliberately (`docs/LOAD-BEARING.md` §1.10), and calling a function requires `USAGE` on its
schema. Putting the chokepoint in `identity.` would have meant either granting the app that `USAGE`
— breaking a documented invariant — or handing the public recipient edge a connection that can read
every tenant's API keys. `session.` needed no new grant at all.

**§4.5 — the cutover.** ⚠ **This is the deviation worth reading.** §4.5 framed it as *dual-accept vs
hard cut*, with dual-accept needing an argument against [ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md)
§2.2. The framing dissolved: `f5sign-signer` had **already** made its client accept both shapes, so
there was never a coordinated-release problem on their side ([`BL-150`](../BACKLOG.md)). What
remained was only *our* outstanding links, and the argument is stated in
[`SigningTokenListener`](../../src/F5Sign/Foundation/Http/SigningTokenListener.php): §2.2 forbids a
**route** having two verifiers because a caller presenting the wrong *kind* would fall through to a
weaker one. Nothing falls through here — one declared kind, one listener, and a parseable `st`
credential is answered by the store and **never** retried against the codec, since that retry would
be the downgrade. The branches discriminated the *encoding* of one kind, for one expiry window.
✅ **That window is closed** — `BL-148` deleted the legacy branch and the codec, so the listener now
has one branch and the argument above is history rather than a live justification.

### Deviations from the plan

- **§2 named TWO minting paths; there were THREE.** `NotifyCorrectedRecipientUseCase` — the
recipient-correction email — also minted, and was missed by the task and by the first cutover
commit, so for a short window this repo claimed every issued credential was opaque while one path
still emitted the old encoding. Found by enumerating the codec's callers during `BL-148` rather than
by re-reading the task. ⚑ The lesson is the enumeration: the plan's list of call sites was written
from memory of the domain, and the compiler's list was not consulted until the class was deleted.

- **§2 said "a lookup table and its resolver"; three chokepoints were built.** Read, write and purge
  all go through `SECURITY DEFINER` functions, so `f5sign_app` holds nothing on the table in any
  direction. The write one is not symmetry: with a plain `GRANT INSERT`, the digest policy would
  oblige the app only to insert rows whose digest it already names — which is what minting *is*, so
  no restriction at all — and it would delete the one place a minting invariant can live.
- **A role had to be created in `f5sign-infra` and then renamed.** `f5sign_signing_token_custodian`;
  it was `…_reader` for a few hours, until the write path showed the same owner must write.
  The rename was done immediately because that script is **additive only** — no `DROP ROLE`, no
  rename — so a later change would have orphaned the old role in every cluster.
- **`docs/LOAD-BEARING.md` §1.14 is new and was not planned.** `Version20260713000003` leaves
  `ALTER DEFAULT PRIVILEGES IN SCHEMA session … TO f5sign_app` in force, so the lookup table was
  granted full DML **at creation**; the explicit `REVOKE` is the grant model, not tidying, and
  without it the chokepoint is decorative with nothing failing.

### Open follow-ups

| What | Where |
|---|---|
| ✅ Delete the legacy encoding branch + retire `SigningTokenCodec` and `SIGNING_TOKEN_SECRET` | [`BL-148`](../BACKLOG.md), closed |
| ✅ Generalise the chokepoint-owner assertion over every `SECURITY DEFINER` function | [`BL-151`](../BACKLOG.md), closed |
| A correction issues a second live credential and retires nothing | [`BL-152`](../BACKLOG.md) |

| ✅ The invitation link stored a live credential indefinitely | [`BL-113`](../BACKLOG.md), closed |
| ✅ `SIGNING_TOKEN_SECRET`'s six surfaces in `f5sign-infra` | [`BL-149`](../BACKLOG.md), closed |
| ✅ Tell `f5sign-signer` the cutover shipped so they can drop their old branch | [`BL-150`](../BACKLOG.md), closed |
⚠ **This table drifted from `docs/BACKLOG.md` three times while the task was being closed** — rows
went to `Resolved` there while staying open here (BL-151, then BL-149 and BL-150 together). Each time
the two documents disagreed and neither could tell. ⚑ **The cheap detector is comparing the two
lists, and it takes one command** — which table a row sits in, against what this one claims:

```sh
CLOSED=$(grep -n '^## Closed' docs/BACKLOG.md | cut -d: -f1)
grep -n '^| BL-' docs/BACKLOG.md \
  | awk -F: -v c="$CLOSED" '{ print ($1 > c ? "closed" : "open"), substr($2, 1, 12) }'
```

⚠ **The parentheses are load-bearing and the first draft of this snippet was broken.** Without them
`awk` reads `>` inside `print` as **redirection**, not comparison, and the command dies with a syntax
error — which at least fails loudly. Verified by running it before publishing it, because a detector
nobody has executed is the thing this note is complaining about.

That is the same shape as [`BL-153`](../BACKLOG.md): a hand-maintained list is a census, and a census
is only as good as the last person who remembered it. This one exists because a *reader* wants the
follow-ups in one place — so it stays, and this note is what makes it checkable rather than trusted.

✅ **Bar 4 is met in both places, which it was not when this section was first written.** §6 bar 4
requires naming both places a plaintext could be stored. The lookup table is asserted — only a
digest is ever written. The second place, `notification.notification.variables`, stored the composed
invitation link with a live credential inside it and nothing deleted the row; it is now dropped once
every delivery is terminal ([`BL-113`](../BACKLOG.md), closed). ⚑ **This section previously said the
bar was unmet and that the fix was Notification's problem, not this task's.** That was the honest
reading at the time and it is kept here because it names the trap: a test written only against the
new lookup table goes green while ADR-0045 §2.6 is violated one table over.
