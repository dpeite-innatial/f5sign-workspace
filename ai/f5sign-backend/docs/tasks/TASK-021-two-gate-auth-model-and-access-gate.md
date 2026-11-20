# TASK-021 — Two-gate signer authentication: the model, the access gate, the session credential, and the act binding

<!-- OFFREPO: §2, §6 and §7 state concrete facts about the sibling repo `f5sign-signer` — that its shipped app already
declares routes 4 and 5 as provisional paths in `SigningApi.real.ts`, that it branches an auth page on the method,
and that it keys routing on `auth_status.authenticated`. That repo is not reachable from a backend-only checkout.
Every one of those facts is restated inline where it is used, so nothing here needs it read.
[TASK-029](TASK-029-session-credential-and-refresh.md), split out of this record, carries the same tag for the same reason. -->

| Field | Value |
|-------|-------|
| **Status** | ✅ **Built and green on `feat/two-gate-signer-auth`, 2026-08-19.** All 15 acceptance bars execute, two with structural deviations recorded in §9. Gates on the isolated worktree lane: lint 0, Deptrac 0 violations, PHPStan L9 clean, full suite green. ⚠ **The counts are deliberately not quoted here** — a test count in this row went stale twice in one day; `git log` and the lane are the measurement. **Not merged, no PR.** ⚑ [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) was promoted to **`Accepted` *(exercised; delivery half deferred)*** on this exercise, 2026-08-19, by the user — the decision this record deliberately declined to take on its own behalf. ⚑ **Infection HAS a worktree-aware route and this record twice said it did not** — `WT_GATES="infection"` on `f5sign-infra`'s `wt-validate.sh`, which mounts a `php.ini` precisely because `-d memory_limit` does not reach the `phpunit` child Infection spawns. §8's *"no worktree-aware route"* and `CLAUDE.md`'s matching line both predate that gate. Corrected 2026-08-19 by reading the script rather than the instructions. |
| **Why** | Possession of the emailed link is the whole of authentication today ([ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md)), so a leaked link signs. [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) answers that with two declared gates — one guarding *reach*, one guarding *the act* — and this task builds the model itself. [TASK-029](TASK-029-session-credential-and-refresh.md) already shipped the clause that comes first, that passing a gate must **mint** something rather than set a flag; what is missing is a gate that can be **failed**. Until then every envelope carries the neutral pair, the link is the method, and re-opening is free. |
| **Type** | **Forward build** — slice 1 of 3. Builds the whole two-gate shape **using no infrastructure that does not already exist**, so the model and the ADR's load-bearing risks are retired before any delivery channel is chosen. |
| **Builds on** | [TASK-029](TASK-029-session-credential-and-refresh.md) (**landed** — the credential a passed gate mints, its two `Authn` cases, their listeners and the route partition; this slice **consumes** all of it and builds none of it), [TASK-008](TASK-008-signing-session-recipient-ceremony.md) (the Session BC + the token edge this amends), [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) (the token it demotes), [ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md) (the admission seam — ⚠ this row said *"grows a fourth credential kind into"* until 2026-08-18 and no longer holds: [TASK-029](TASK-029-session-credential-and-refresh.md) landed **two** cases, `SESSION_CREDENTIAL` and `SESSION_RENEWAL`, so `Authn` now has five and **this task adds none** — §3 lists them as out of scope), [ADR-0039](../adr/ADR-0039-per-recipient-document-access.md) (the `signs` grants the signing gate binds to). |
| **Decision record** | [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md). Its five formerly-open questions are all closed; the *Questions closed* table there names which section each moved. Two of its clauses are amended elsewhere and this task follows the amendment, not the original: [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.5 replaces **§2.3**'s last-activity clock, and ADR-0050 §2.3 replaces **§2.8**'s 30-minute idle figure. ⚠ Those two anchors read `§3` and `§8` until 2026-08-18 and were both wrong — ADR-0049 §3 is *Consequences* and ADR-0049 **has no §8 at all** (its headings run 7 → 9). The body of this record cited them correctly throughout, so the header contradicted the document it heads. Nothing here is blocked on a decision. |
| **Sequencing** | **Fourth**, in `TASK-025 → TASK-029 → TASK-028 → this → TASK-022 → TASK-023`. [TASK-025](TASK-025-recipient-delivery-failure-and-correction.md) shares no substrate with this work and repairs a hole open in production, so it can also run in parallel. [TASK-029](TASK-029-session-credential-and-refresh.md) **does** block this one: it builds the credential a passed gate mints, and it is where the `f5sign-signer` cascade happens. [TASK-022](TASK-022-delivered-codes-over-email.md) follows. ⚠ **[TASK-028](TASK-028-opaque-signing-token.md) does NOT block this task**, and the ordering string above reads as if it did. Nothing here needs an opaque token — §2 keeps the signing token's routing and tenant-scoping job untouched on the routes this slice uses, and TASK-028 appears in no other row, section or bar. Its own §5 already records that the reasoning which put it first (avoiding two `f5sign-signer` cascades in consecutive weeks) moved to TASK-029 when the route partition did. What couples them is the signer **release window**, not the code. |
| **Delivery bar** | An envelope authored with a non-neutral access gate **serves no document, no field and no bytes** to a recipient until the code is entered, because no session credential is minted until then; entering it mints one. A signing gate then consumes a challenge **bound to that recipient's signable document set** at commit. Both driven end-to-end over HTTP, `make qa` green. |
| **Breaking** | **No longer for `f5sign-signer`** — that cascade moved to [TASK-029](TASK-029-session-credential-and-refresh.md) with the route partition. Breaking for the **sender** surface: the add-recipient call gains a requirement field and two new `MACHINE_KEY` routes appear. Envelopes authored before this slice carry the neutral pair and are unaffected. |

---

## 1. Why this task exists

Today a bearer token *is* authentication ([ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md): possession of the token is authentication), so a leaked link signs. The product requirement is that the sender declares, per recipient, that the signer must prove something — before entering, before signing, or both.

Two risks make this slice 1 rather than a subset of a delivery feature, and both are retirable now because they are orthogonal to how the secret was delivered.

**The signing gate is worth nothing unless the challenge is bound to the act and consumed at commit.** A gate satisfied by "the session is authenticated" collapses into the access gate, and the collapse is invisible — every functional test still passes, the second prompt still appears, and the ceremony simply stops meaning anything.

**The access gate is worth almost nothing unless passing it mints something.** A session is keyed `(tenant, envelope, recipient)` with a deterministic id, so every holder of the link converges on the same session. If passing the gate is a flag on that row, a leaked-link holder polls until the legitimate signer authenticates and is then inside, having proved nothing — they need not even race him. The access code would protect only the interval before the signer arrives. [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3 answers this with a minted credential, and it is why the route partition below is in slice 1 rather than deferred.

Both are buildable with `ACCESS_CODE` on either gate — no channel, no provider, no rate limiter, no personal data. Delivery becomes a verifier swap in [TASK-022](TASK-022-delivered-codes-over-email.md).

## 2. What gets built

**The declaration (Envelope).** An `AuthRequirement` value object on `Recipient` with two **typed** slots — an access slot and a signing slot — each carrying its own neutral through a named constructor (`open()` / `none()`) per [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §1. The `AuthMethod` catalog lands whole, with the **fourteen** members [`signing-session-domain-model.md`](../ddd/signing-session-domain-model.md) fixes and no neutral among them, written as exhaustive `match`es with no `default` — the shape [`Role`](../../src/F5Sign/Envelope/Contract/Type/Role.php) already uses, because an `AuthMethod` falling through to "no gate" would be an authentication bypass.

The two structural rules live **in the slot constructors**, not in a validator: the signing slot refuses a method that cannot issue a per-act challenge, the access slot refuses one that cannot be established without a prior session, and both refuse `DIRECT_LINK` in `requiring()` so the open gate has exactly one spelling. An envelope with no door is therefore not rejected — it is unwritable.

Authoring commands to declare the requirement, plus `ResetRecipientAccessCode` (mint, surface once to the sender, invalidate the old) and `UnlockRecipientAuth`, which are the only two recoveries once the code is a hash.

**The sender's surface is the authoring API, and all of it lands here.** Envelope authoring is already an integrator-facing API under `MACHINE_KEY` — create, documents, steps, recipients, fields, assignments, send, void — so declaring an auth requirement is a field on the existing `POST /api/v1/envelopes/{id}/recipients`, and the feature is usable by an integrator the day this ships. It does **not** wait on the sender dashboard, which is a separate product surface in another repo. What that makes non-optional is the rest of the sender's half, because a command with no route is unreachable code:

| Sender action | Where it lives |
|---|---|
| Declare the requirement | A field on the existing add-recipient call |
| Receive a server-generated code, once | That call's **response body**, and only there |
| Regenerate the code | **New route**, `MACHINE_KEY` |
| Lift a hard lock | **New route**, `MACHINE_KEY` |
| See that a recipient is locked | A field on the existing `GET /api/v1/envelopes/{id}` |

The one-shot code goes in the minting call's response rather than behind a fetch, because a fetchable code is either re-readable — restoring the recoverable secret the hash exists to prevent — or single-use, which is this with an extra round trip ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.8). It appears only when the **server** generated it: a sender who supplied their own already knows it. And it must never reach a log, which no test can hold.

Without the two new routes, acceptance bar 9 below cannot be driven over HTTP at all — a forgotten code would have no recovery in practice, whatever the aggregate can do.

**Availability — an application guard over a capability port.** Whether a declared method can run in *this* deployment is a capability, so it is a port with an adapter per [ADR-0013](../adr/ADR-0013-deployment-mode-duality.md), not a flag on the enum; the domain never reads it. In this slice the adapter reports the access-gate neutral and `ACCESS_CODE` available and everything else not, which is what stops an author declaring `OTP_SMS` before [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) wires one. The port lands here and gains a row in ADR-0013's capability matrix. ⚠ **This paragraph said *"a Foundation port"* until 2026-08-19.** It is [`Envelope\Application\Port\AuthMethodAvailability`](../../src/F5Sign/Envelope/Application/Port/AuthMethodAvailability.php): ADR-0013's *pattern* is honoured exactly, but `Foundation` may import only `Kernel` and `Vendor`, so a Foundation port could not name `AuthMethod` in a signature. That port's docblock is the home of the argument.

**The verifier crossing (Envelope → Session).** The requirement travels on the cross-BC read port Session already uses — [`EnvelopeQueryInterface::getContextForRecipient()`](../../src/F5Sign/Envelope/Contract/Query/EnvelopeQueryInterface.php) returning a [`RecipientEnvelopeContextView`](../../src/F5Sign/Envelope/Contract/View/RecipientEnvelopeContextView.php) — so this is a field on an existing view, not a new seam. *(The design calls this crossing `EnvelopeReadSide`; no port of that name exists — `envelope-divergences.md` D4 has it deferred "until that consumer exists" and the consumer arrived under the other name. Worth closing D4 while here.)*

**Only `ACCESS_CODE` carries a verifier across.** A delivered code's hash is born on the challenge inside Session and dies with it; Envelope declares the method and already holds the destination. Getting this backwards puts an OTP hash in an authoring table.

**The catalog does not cross with it, and the obvious implementation is a Deptrac violation on day one.** `AuthMethod` is Envelope vocabulary and lives in `Envelope/Contract/Type/`. But `SessionDomain` may import only `Kernel`, `Foundation` and `SessionContract` — and `SessionContract` itself only `Kernel` and `Foundation` — so **neither the `SigningSession` aggregate nor anything in Session's Contract can name Envelope's enum.** Typing the executed method, or a challenge's method, as `Envelope\Contract\Type\AuthMethod` fails `composer arch` the first time it is written.

The answer is not a relaxed ruleset; it is the mirror this BC already builds for exactly this reason. [`EnvelopeRef`](../../src/F5Sign/Session/Contract/Type/EnvelopeRef.php) says it in its own docblock — *Session Contract may import only Kernel + Foundation, so it cannot speak Envelope's `EnvelopeId` directly* — and is the anti-corruption mirror [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md) prescribes. So Session gets its own method type in `Session/Contract/Type/`, translated at the Application boundary where the requirement is read, exactly where `EnvelopeRef` is translated today.

Two consequences of that home, both deliberate. It is **`Contract`, not `Domain`**, because Signature Execution consumes the executed method as a signature-level projection refiner and `SignatureExecutionApplication` is granted `SessionContract` — publishing it in `Domain` would put it somewhere no other context may look. And it means **the fourteen members are written twice**, which is duplication with a purpose rather than an oversight: the two enums are free to diverge, since Envelope's is what a sender may *declare* and Session's is what a ceremony can *execute*, and the day those sets differ the mirror is what lets them. A test enumerating both and asserting the translation is total in the direction Session needs is what stops the copy rotting — the same discipline `ActorKind` already applies to its own vocabulary.

**That re-read happens in `Session/Application/`, and the aggregate never performs it.** `SessionDomain` cannot import `EnvelopeContract`, so injecting `EnvelopeQueryInterface` into a domain service is the same violation one layer down. The use case reads the requirement, translates it into Session's own vocabulary, and hands the aggregate values it can already speak — which is also why the mirror above is a translation boundary and not merely a naming preference.

**Session re-reads the requirement at every verification and never caches it at session start.** A reset changes the hash, and a cached verifier makes the reset a no-op. This is also what lets the lockout generation ride across for free.

**The ceremony (Session).** `SessionStatus` gains `AUTH_PENDING`; a session opens there whenever the access gate is non-neutral. A challenge child entity and an append-only attempt child entity on the aggregate. Submitting a response verifies in constant time against the peppered hash and passes the gate.

**Both new writes take the row lock, because two devices are one row.** A session id is derived from `(tenant, envelope, recipient)`, so a signer with the link open on a phone and a laptop is not two sessions — they are two requests against the same row, and read-decide-write is three steps with room between them. Two simultaneous verifications each read the failure counter, each add one, and one of the two failures disappears; that is not a rounding error when N × M is the only security property the ceremony has. Two simultaneous *ensure a live challenge* calls each find none open and each mint one, which is §2.5's defect arriving through concurrency rather than through a reload.

The remedy already ships: [`SigningSessionRepository::findLockedForUpdate()`](../../src/F5Sign/Session/Domain/Repository/SigningSessionRepository.php) is what `CommitSignatureUseCase` uses today. Verification and issuance take the same path. Nothing new is invented here — what is new is remembering to.

**And the one-open-challenge invariant gets a database constraint as well, because a lock only protects the callers who take it.** A partial unique index — at most one unconsumed, unexpired challenge per session — makes a second live challenge unwritable rather than merely unwritten, so a future issuance path that forgets the lock fails loudly instead of silently reintroducing the defect. Same reasoning as the typed slots of §2.1: a rule that must be remembered is a rule that will be forgotten, and this one would pass every single-threaded test while broken.

The failed-attempt budget is **cumulative per session across challenge replacement** — inert in this slice, load-bearing the moment [TASK-022](TASK-022-delivered-codes-over-email.md) adds re-sending — and is held as a **scalar on the session, never derived by counting attempt rows**: a derived count would make any future row cleanup a silent lockout reset, so the scalar exists from the first commit rather than being retrofitted. **A successful pass clears the lockout state entirely**, both the failure count and the consumed-window count ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.6).

**The session credential is NOT built here.** [TASK-029](TASK-029-session-credential-and-refresh.md) builds it — the JWT, the opaque rotating refresh, the two `Authn` cases and the route partition — and lands **before** this task, against the neutral gate pair. What this task adds is the only part that needs a gate to exist: **passing a non-neutral access gate is what mints it.** Until this slice, every session mints one immediately because every gate is open.

⛔ **Do not reintroduce the credential into this task's scope, and do not mint it with [`SigningTokenCodec`](../../src/F5Sign/Foundation/Http/SigningTokenCodec.php).** An earlier cut of ADR-0049 §2.3 specified that codec; [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §7.3 records why it was withdrawn.

**The route partition** is [TASK-029](TASK-029-session-credential-and-refresh.md)'s, and **landed with it on 2026-08-18**. Reproduced here because routes 3 and 5 are *this* task's to build and they sit inside it. One question decides each route: *does it have a legitimate purpose before the code is typed?*

| # | What it is | Route | Method | `Authn` |
|---|---|---|---|---|
| 1 | The sender mints a recipient's link | `/api/v1/signing-tokens` | POST | `MACHINE_KEY` — unchanged |
| 2 | Open or resume the session | `/api/v1/signing/session` | POST | `SIGNING_TOKEN` — unchanged |
| 3 | **Which gate do I face?** *(new)* | `/api/v1/signing/session/auth` | GET | `SIGNING_TOKEN` |
| 4 | Issue or re-send the code | `/api/v1/signing/session/auth/otp/send` | POST | `SIGNING_TOKEN` — [TASK-022](TASK-022-delivered-codes-over-email.md) |
| 5 | Submit the code → returns the credential *(new)* | `/api/v1/signing/session/auth` | POST | `SIGNING_TOKEN` |
| 6 | The recipient read-model | `/api/v1/signing/session` | GET | ✅ `SESSION_CREDENTIAL` — **already live** (TASK-029) |
| 7 | The document bytes | `/api/v1/signing/session/documents/{documentId}` | GET | ✅ `SESSION_CREDENTIAL` — **already live** (TASK-029) |
| 8 | Commit the signature | `/api/v1/signing/commit` | POST | ✅ `SESSION_CREDENTIAL` — **already live** (TASK-029) |
| 9 | Renew the credential pair | `/api/v1/signing/session/renew` | POST | ✅ `SESSION_RENEWAL` — **already live** (TASK-029); not in ADR-0049 §2.3's table, added by [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.4 |

Route 5 is already declared by the shipped signer app under exactly this path (and route 4 likewise, for [TASK-022](TASK-022-delivered-codes-over-email.md)), against a backend that serves neither — so those two are being fixed, not invented. Route 3 is new: the signer reads the requirement off the session read-model today, which is the coupling this partition removes. Route 3 returns the open gate, its method and a masked destination — never the signer's identity, the documents or the branding — and serves both gates, so the client has one place to ask *what is being asked of me right now*.

**Expiry and re-authentication.** `SessionStatus` also gains `AWAITING_REAUTH`, reached when the access grant goes idle past its window ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.1: idle, not age). Recovering means repeating the **access** gate, never the signing gate; re-auth attempts spend the same budget.

⚑ **The mechanism is no longer a last-activity column, and an earlier cut of this section said it was.** [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.5 replaces it: the idle clock is the **refresh credential's own expiry**, built in [TASK-029](TASK-029-session-credential-and-refresh.md). That deletes the column and the obligation on every gated route to read the session — an obligation that was never met, since two of the three routes touch no session row today. What this task owns is the *state transition* into `AWAITING_REAUTH` and what it takes to leave it, not the clock that triggers it.

This is in the model rather than deferred because an access gate whose pass never expires is a gate that opens once and never closes.

**The policy constants, behind one read point and with no override levels.** The values are [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.8's platform defaults — and they are *only* that. An earlier cut of this paragraph said they resolve through a tenant → workspace → envelope chain; none of those three levels exists, there is no policy store at any of them, and `workspace` is described by its own migration as an untriaged fork. Nobody has asked to configure these values, so this slice does not build a resolver for them (`BL-120`). What it does build is the one thing that keeps the option open cheaply: a single place the ceremony reads them from, so the day an override is wanted it is that place that grows, not every call site: code length 6 digits, **N** = 5 failures, cooldown window 5 minutes, **M** = 3 windows. Server-generated codes by default; a sender-supplied one takes a six-character minimum.

The challenge TTLs and the re-send interval now have values in that same table — 5 minutes for `OTP_SMS`, 15 for `OTP_EMAIL`, 60 seconds between issuances — ⚠ and **not** §2.8's *idle TTL 30 minutes*, which [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.3 replaced with 60 minutes idle under a 12-hour cap, both **already built** by [TASK-029](TASK-029-session-credential-and-refresh.md) and therefore out of scope here — but **nothing here reads them**, because this slice delivers no code: the only verifier is a pre-shared one whose life is the envelope's. They are named so the precedence chain is built to hold a per-method value from the first commit rather than being retrofitted around a scalar, and they come into force in [TASK-022](TASK-022-delivered-codes-over-email.md).

**The lockout, and the generation that lifts it.** Two tiers per [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.6: a **soft** lock that releases itself after a cooldown window, and a **hard** lock, reached by exhausting soft windows, that does not.

Both sender-side exits work through a monotonic **auth generation** on the recipient rather than by writing into Session. `ResetRecipientAccessCode` and `UnlockRecipientAuth` bump it; a lockout records the generation it was set under; **a lockout whose generation is behind the recipient's current one is inert**. One write, one aggregate, one transaction — and the case with no good alternative answer, *the session does not exist because the recipient never opened the link*, stops being a case at all.

The lock reaches the **sender-facing read model** the other way, as a fact: Session emits the lockout milestone, Envelope reacts and records it on the recipient, exactly as [`OnSessionCompleted`](../../src/F5Sign/Envelope/Application/Subscriber/OnSessionCompleted.php) already translates `SessionCompleted`. Because Envelope knows the current generation locally, the read model renders "unlocked" the moment the sender resets, however late Session's fact arrives.

**What is recorded, and where.** Milestones reach the event log — challenge issued, verification passed, gate passed (naming *which* gate and *which* method), lockout reached, lockout lifted — and **individual attempts do not**: the access gate is public and anonymous, so per-attempt appends to a permanent commitment-bearing store are a write amplifier an attacker controls. Attempts land on the aggregate instead, bounded by the budget. No fact carries the destination in any form.

**The binding (Session).** A signing-gate challenge is issued bound to the recipient's signable document set (the `signs` grants, [ADR-0039](../adr/ADR-0039-per-recipient-document-access.md)) and `commitSignature` **consumes** it: single-use, valid only for that set. Since a recipient signs all of their assigned documents in one terminal act, the set is fixed at issuance.

**The envelope has to be alive, and today nobody asks.** `EnvelopeStatus` appears nowhere under `src/F5Sign/Session/`: the context reads the recipient's outcome and never the envelope's state. So a recipient whose envelope was voided after they opened the link can still commit — [TASK-015](TASK-015-envelope-void.md) records this as a deferred reactor and its own words are *"a recipient holding a live authenticated session can still commit a signature after the envelope is voided"*, and `BL-61` traces the consequence past the ceremony into state-machine corruption. This slice rewrites exactly that seam and would otherwise ship a gate that never asks the question.

So both new decision points read the envelope's state: **issuing a challenge** and **consuming one at commit**. Issuing matters for a reason the commit guard does not cover — with a delivered code, a dead envelope makes the platform send a message, and in [TASK-023](TASK-023-sms-codes-and-recipient-phone.md) pay for an SMS, to let someone into something that no longer exists.

**Behind the seam, never at the edge.** `BL-87` is explicit about this: a status lookup on the public recipient route would need an unscoped read on a public route, which is the shape this repo has already removed once. The guard belongs where the tenant scope is already established and the requirement is already being read, which is the same application-layer call this slice added for the verifier and the auth generation.

⚠ **This closes the harm, not the deferral.** A credential already minted stays valid until it expires; what changes is that it buys nothing, because both gates refuse. Making the void itself end live sessions is the reactor TASK-015 deferred, it is cross-context work with its own shape to decide, and it stays open under `BL-61` and `BL-87`.

**The demotion.** The token keeps its routing and tenant-scoping job — [`SigningTokenListener`](../../src/F5Sign/Foundation/Http/SigningTokenListener.php) and the RLS-from-token seam are untouched — and loses its authenticator job on routes 6–8.

Two shapes worth knowing before touching this: [`SigningSessionReader`](../../src/F5Sign/Session/Application/Query/SigningSessionReader.php) **never reads the session** — it derives `status` from the envelope's `RecipientOutcome` — so gating the read path is a new input, not a guard added to an existing check. And [`GetSigningSessionController`](../../src/F5Sign/Session/UI/Http/GetSigningSessionController.php) already emits an `auth_requirements` array and an `auth_status` block, both in the published Nelmio schema: this slice fills a stub rather than inventing a contract. ⚠ **But the stub is now half-filled, and this paragraph said "both hard-coded to constants" until 2026-08-18.** [TASK-029](TASK-029-session-credential-and-refresh.md) made three of `auth_status`'s five members real — `auth_completed_at`, `auth_expires_at` and `auth_ttl_minutes` now come from the verified session credential. What is still literal is `authenticated` (always `true`) and `method_used` (always `DIRECT_LINK`), and **those two are exactly what this task makes real**. ⛔ `method_used` additionally has a **published single-member enum** in [`nelmio_api_doc.yaml`](../../config/packages/nelmio_api_doc.yaml), registered as a deliberate non-mirroring exception in [`OpenApiSpecTest`](../../tests/F5Sign/Acceptance/OpenApiSpecTest.php) — widening it is this task's, and it is a wire-contract change the front ends ratify.

**The refusal kinds (Kernel/Foundation).** [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md) left the auth-refusal kinds unminted for want of an aggregate guard that exercised them. This is that exercise, and it needs **three** ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.3): authentication-required → 401 (wrong code, expired challenge, re-auth needed), authorization-denied → **423** (hard lock — the status the shipped signer already treats as *contact the sender*), and temporally-refused → 429 with `Retry-After` (soft lock). A replayed or mis-bound challenge reuses the existing conflict kind for its 409. Without them every one of these falls to the default 422.

**Indexes, named rather than left to whoever writes the migration.** `LIVE_SCHEMA.md` documents indexes per table as part of the contract, and this slice adds three read paths that run on every ceremony: the open, unexpired challenge for a session (read every time the auth screen loads), the attempt rows for a session (read to build the trail), and the lock state per recipient on the sender-facing model (read on every `GET /api/v1/envelopes/{id}`). The first is already covered by the partial unique index the one-open-challenge invariant needs — the same index serves the lookup, which is worth noticing before someone adds a second.

**Two secrets, and one of them cannot be rotated quietly.** The code pepper and — from [TASK-029](TASK-029-session-credential-and-refresh.md) — the credential signing key are both server-held and both absent from `.env` under repo rule 4, following the discipline [`SigningTokenCodec`](../../src/F5Sign/Foundation/Http/SigningTokenCodec.php) already states for `SIGNING_TOKEN_SECRET`. The pepper carries a consequence nobody has written down: **rotating it invalidates every access-code hash in the database at once**, stranding every envelope carrying one until each sender resets it. There is no rehash-on-verify path and this slice does not build one; what it does is say so, so that rotation is planned rather than discovered.

**And the `Retry-After` a client is told to obey is one it cannot currently read.** [`CorsListener`](../../src/F5Sign/Foundation/Http/CorsListener.php) sets `Allow-Methods`, `Allow-Headers` and `Max-Age` on the preflight and emits no `Access-Control-Expose-Headers`, so a browser hands a cross-origin caller only the CORS-safelisted headers — and `Retry-After` is not one of them. The soft lock would arrive as a 429 whose wait the signer app cannot see. Two ways out and this slice takes the first: expose the header, which is one constant on an existing listener. The alternative — making the problem+json `retryAfter` member the contract and the header advisory — is defensible but quietly demotes a standard header to decoration. Either way it must be decided here, because the bar that asserts `Retry-After` passes server-side while the client is blind.

**Schema.** Requirement columns, the access-code hash and the auth generation on `envelope.recipient`; challenge and attempt child tables, and the executed method on the session side. ⚠ **No last-activity column** — this line asked for one until 2026-08-18, contradicting this section's own expiry paragraph (the ⚑ beginning *"The mechanism is no longer a last-activity column"*): ADR-0050 §2.5 deleted that mechanism and [TASK-029](TASK-029-session-credential-and-refresh.md) built the idle clock as the refresh credential's own expiry (`session.signing_session.refresh_expires_at`) instead — the method is not cosmetic, Signature Execution consumes it as a signature-level projection refiner. Child tables per [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §5, FORCE-RLS per [ADR-0017](../adr/ADR-0017-tenant-isolation-rls-persistence-contract.md), no database defaults on domain-authored columns. The migration backfills the neutral pair rather than leaving a null for later code to interpret.

### What already exists — reuse it, do not rebuild it

⚑ **Added 2026-08-18, after [TASK-029](TASK-029-session-credential-and-refresh.md) landed.** This record was written when none of the following existed, and it names in §2 what *not* to mint with while never naming what to mint **with**. Everything below is on `develop` and green.

| What you need | What already ships it |
|---|---|
| Mint the credential a passed gate hands over | [`SessionCredentialCodec::mint()`](../../src/F5Sign/Foundation/Http/SessionCredentialCodec.php) — JWT, 15 minutes, algorithm pinned, closed claim set |
| The opaque half of the pair | [`IssuedCredential::mint(CredentialKind::SESSION_REFRESH)`](../../src/F5Sign/Foundation/Credential/IssuedCredential.php) — ADR-0045-conformant, digest at rest, plaintext once |
| Store the pair on the session, rotate it, expire it | [`SigningSession::mintCredential()`](../../src/F5Sign/Session/Domain/Aggregate/SigningSession.php) + `renewWith()`, and `SigningSessionRepository::mintCredentialFor()` for the atomic write |
| Admit the three partitioned routes | [`SessionCredentialListener`](../../src/F5Sign/Foundation/Http/SessionCredentialListener.php) — admission **plus** `TenantContext` **plus** the RLS GUC |
| Declare a route's credential | `Authn::SESSION_CREDENTIAL` / `Authn::SESSION_RENEWAL` in [`config/routes/api/signing.php`](../../config/routes/api/signing.php), pinned per kind by [`RouteAuthnDeclarationTest`](../../tests/F5Sign/Foundation/Integration/RouteAuthnDeclarationTest.php) |

⛔ **The one relocation this task owes, and it is not obvious from §3.** TASK-029 put the mint in [`StartSessionController`](../../src/F5Sign/Session/UI/Http/StartSessionController.php), **unconditional at session open** — correct under the neutral pair, where opening *is* passing the gate. This slice must make that conditional and add a **second** mint site on route 5 (submit the code), so that a recipient facing a real gate leaves the open with **no** credential and gets one only by passing. Neither the site nor that choice is named anywhere else in this record.

⚠ **And re-opening currently re-mints unconditionally**, which is what the signer app's idle-recovery path relies on ([`BL-146`](../BACKLOG.md) context). Once a gate can be failed, re-opening must stop being a free credential — otherwise the gate is bypassable by returning to the link, which is the whole defect this task exists to close.


## 3. Scope

**In scope:** the `AuthRequirement` VO with two typed slots + the full fourteen-member `AuthMethod` catalog; the two structural rules as constructor refusals; the availability port + its adapter and the application guard consuming it, plus the ADR-0013 matrix row; authoring, reset and unlock commands **with their two new `MACHINE_KEY` routes**, the requirement as a field on the add-recipient call, the one-shot generated code in that call's response, and the lock state on `GET /api/v1/envelopes/{id}`; the auth-generation counter and the inert-lockout rule; the read-port crossing with its two projections; `AUTH_PENDING` + `AWAITING_REAUTH` + challenge/attempt entities + the submit path; routes 3 and 5, and **the act of minting the session credential on a passed gate** (the credential itself is [TASK-029](TASK-029-session-credential-and-refresh.md)'s); the cumulative attempt budget as a session scalar and its reset on a successful pass; the two-tier lockout and both sender-side exits; the lock fact and its landing on the sender-facing read model; the envelope-status guard on issuance and commit; the milestone facts of §2 and the deliberate absence of per-attempt ones; the act binding and its consumption at commit; the three refusal kinds and their edge mapping; the Nelmio schema updates for every changed route — **including widening `method_used`'s single-member enum in `nelmio_api_doc.yaml` and its allowlist entry in `OpenApiSpecTest`**, both of which the shipped code assigns to this task by name; **making [TASK-029](TASK-029-session-credential-and-refresh.md)'s unconditional mint in `StartSessionController` conditional, and adding the second mint site on route 5** (see §2's *What already exists*); a `docs/frontend-handoff/TASK-021-*.md` record, since this slice changes wire enums, adds routes and touches `#[OA\*]`; migrations; tests per §5.

**Out of scope (named so they are not silently dropped):**
- **The session credential and everything under it** — the JWT, the opaque rotating refresh, the two `Authn` cases and their listeners, the renewal endpoint, the route partition and the digest columns. All [TASK-029](TASK-029-session-credential-and-refresh.md), landed before this task. This slice consumes that machinery; it does not build any of it.
- **The idle clock itself.** [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.5 makes it the refresh credential's expiry, so it **landed with** [TASK-029](TASK-029-session-credential-and-refresh.md). Only the `AWAITING_REAUTH` transition and its exit are here.
- **Every delivered method** — `OTP_EMAIL` is [TASK-022](TASK-022-delivered-codes-over-email.md), `OTP_SMS` is [TASK-023](TASK-023-sms-codes-and-recipient-phone.md). No channel, no route 4, no rate limiter here.
- **The two issuance operations.** [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.5 splits *ensure a live challenge* from *mint a new one*; with no delivery and no re-send control, only the first is reachable in this slice. The distinction is built in [TASK-022](TASK-022-delivered-codes-over-email.md), where a page reload would otherwise kill the code the signer is holding.
- **The six cases [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.11 excludes** — claimable recipients, delegation, batch sessions, in-person signing, `CHANGE_AUTH`, `SubstituteAuthMethod`.
- **Evidence-packet handoff of the auth trail** to Evidence & Audit. It stays where [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) left it.
- **Cleaning up attempt rows.** [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.6 settles the policy — terminality plus a completed evidence handoff — and the handoff is unbuilt, so **no cleanup job is written here**. The scalar counter is in scope precisely so that job is safe whenever it arrives.
- **The dashboard rendering of a locked session.** The lock state *is* projected onto the sender-facing read model here; drawing it, and the unlock control, is frontend work in another repo.

## 4. Key decisions

- **`ACCESS_CODE` on both gates in this slice.** Re-prompting a pre-shared code before the act is a real product configuration, and it is chosen here because it makes the act binding and the credential buildable and testable with zero infrastructure. The verifier type is orthogonal to both, so nothing about this choice is redone when a delivered code replaces it.
- **The neutral lives in the slot type, not in the catalog.** `(open(), none())` is a declaration, not an absence, so the migration backfills a value rather than leaving a null. And because no `NONE` exists as a method, the envelope-with-no-door is unrepresentable rather than validator-dependent — which matters given the permissive-`default` bypass this repo already shipped on the neighbouring role enum.
- **The credential is a replacement, not an accompaniment.** One credential per request keeps [ADR-0048](../adr/ADR-0048-route-declared-authentication-seam.md)'s one-kind-per-route literally true, and partitioning the routes is what lets *both* halves of the surface be edge-enforced instead of one half being held by a handler.
- **The verifier travels with the declaration only where the sender owns it.** Putting the access-code hash in Envelope and the check in Session keeps the boundary the domain models state; putting an OTP hash there would be a category error.
- **The lockout expires rather than being cleared.** A generation on the recipient means the sender's gesture is one local write, the reset takes effect on the signer's very next attempt, and a session that does not exist yet needs no special case.
- **The attempt budget belongs to the session, not the challenge.** Inert here, since nothing replaces a challenge yet. Built now because retrofitting it after re-sending exists means shipping the reset-the-lockout hole first.

**Assurance tier: A.** [ADR-0035](../adr/ADR-0035-testing-standard.md) puts *RLS and tenant isolation* in Tier A and this task sits on it, so its tests carry the Tier A bar rather than the default: risk-based exhaustive coverage including negatives, covered-MSI at the Tier A threshold, and the per-requirement traceability group that tier makes mandatory rather than optional. ADR-0035's Tier A set is enumerated rather than argued per pull request, so **the enumeration grows to name this work** — an enumeration that silently omits the newest member of its own category is the failure mode this repo has already met on `SchemaConformanceTest`.

## 5. Acceptance bars

Each turns one of [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md)'s stated bars green. The first two are the reasons the slice exists.

1. **The gate is what mints.** Behind a non-neutral access gate, a session mints **no** credential until the code is submitted, and mints one the moment it is. Driven over HTTP. *(That the credential — and not the link — is what admits a request is [TASK-029](TASK-029-session-credential-and-refresh.md) bar 1, and it is already green before this slice starts. What this bar adds is that an unopened gate withholds it.)*
2. **The binding holds.** A challenge issued for one document set is refused for another; a consumed challenge cannot be replayed. Aggregate-level, plus one end-to-end.
3. **The gate is real over HTTP.** Session content and document bytes are refused before the gate passes, driven through the actual routes rather than asserted on the aggregate — and the descriptor route answers with the method and a masked destination so the signer learns which gate they face.
4. **The budget survives challenge replacement, row deletion and concurrency.** Replacing a challenge does not restore failed attempts (asserted against the aggregate here; [TASK-022](TASK-022-delivered-codes-over-email.md) drives it through a real re-send), and neither does deleting attempt rows — the bar that stops a later cleanup job being written against a derived count. **And two simultaneous wrong codes spend two attempts, not one**, driven as two overlapping requests rather than two sequential ones. Written sequentially this bar passes with the row lock absent, which is the whole reason it is worth writing at all.
5. **A successful pass clears the lockout.** Four failures, one success, one failure weeks later: not locked, and the counter reads one rather than five. The regression this catches is a signer refused for mistakes nobody remembers — and it is worth writing knowing what it concedes, because the same reset is what makes the guessing budget per-episode rather than per-envelope ([ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.8). This bar asserts the decision, not the property it gives up.
6. **Refusals map by kind.** The three new kinds reach 401 / 423 / 429 at the edge under the problem+json shape, the soft lock carries `Retry-After`, and a replayed or mis-bound challenge is 409 — driven through the edge listener rather than asserted on the exception classes. The half worth writing carefully is **429 ≠ 423**: they instruct a client to do opposite things.
7. **Neutral is unchanged.** A recipient carrying `(open(), none())` walks the ceremony with no behavioural difference — the regression bar for every envelope authored before this slice. Its session still mints a credential immediately, exactly as it did after [TASK-029](TASK-029-session-credential-and-refresh.md), so nothing about routes 6–8 changes here.
8. **Idle expiry withdraws the act, not the work.** A session idle past its window reaches `AWAITING_REAUTH`, refuses to commit, and passing the access gate again restores it. ⚑ **The half of this bar about field drafts is currently unwritable and must not be quietly dropped.** [ADR-0049](../adr/ADR-0049-two-gate-signer-authentication.md) §2.1 says drafts survive ejection, and an earlier cut of this bar asserted it — but **no field value is persisted anywhere in this repo**, so there is nothing to survive and nothing to assert. Today an ejection discards whatever the signer typed. That is also why [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) §2.3 raised the idle window rather than inheriting ADR-0049 §2.8's 30 minutes, whose stated rationale was precisely that drafts survive. Restore this half of the bar when drafts land; do not delete the sentence.
9. **The lock has an exit, both ways — including with no session.** The soft tier releases itself after its window with no intervention; the hard tier does not, and is lifted by *either* sender-side path. And a sender who resets a recipient **who never opened the link** succeeds, with the reset in force when that recipient later opens it.
10. **The structural rules refuse the right thing, and only that.** `DIRECT_LINK` is refused in both `requiring()` constructors; an otherwise "weak-looking" pair such as `(DNIE_NFC, ACCESS_CODE)` is **accepted**. The second assertion is the one worth writing — it is what stops a later reader re-adding a strength comparison because the pair looks wrong at a glance.
11. **An unavailable method is refused at authoring, and nothing falls through.** Declaring `OTP_SMS` in this slice is rejected by the guard, not discovered by a signer; and no catalog member reaches the ceremony without an explicit branch — the bar against a `default` that quietly means "no gate".
12. **The two new routes declare.** `RouteAuthnDeclarationTest` extends to routes 3 and 5.
13. **One live challenge, under load.** Two simultaneous *ensure a live challenge* calls yield one challenge and one delivery, not two — and the database refuses the second even when the caller skips the lock, so the invariant survives a path that forgets it. The second half is asserted directly against the constraint, because it is what protects the invariant from code that does not exist yet.
14. **A dead envelope refuses both gates.** An envelope voided after its recipient authenticated refuses to issue a challenge and refuses to consume one at commit — driven over HTTP with a session that was legitimately open beforehand, because opening it afterwards is a different and easier case. The bar asserts the refusal, not the revocation: the credential is still valid and still buys nothing.
15. **The mirror holds, in both directions.** `composer arch` is green with the method vocabulary duplicated into `Session/Contract/Type/` — and a test enumerates both enums and asserts the translation is total for every member Session can execute, so a member added on one side and forgotten on the other fails at build time rather than at a signer's gate. Behaviour alone would not catch this: the ceremony works perfectly with the dependency inverted, right up until Deptrac runs. The partition itself, and that test's repair for it, are [TASK-029](TASK-029-session-credential-and-refresh.md) bar 10 — *RouteAuthnDeclarationTest is repaired, not widened* — and are green before this starts (bar 8 there is the tenant scope surviving the credential swap, a different property).

`make qa` green: PHPStan L9, Deptrac 0, lint, full suite.

## 6. Cross-repo coordination

The signer app (`f5sign-signer`) already implements the whole ceremony against the published contract — an auth page branching on `ACCESS_CODE` / `OTP_SMS` / `OTP_EMAIL`, a re-auth modal, a masked-channel subtitle, and routing that keys on `auth_status.authenticated` rather than on the status enum. It is not new work there so much as reconnection, but it is a separate repo and therefore a separate, coordinated PR ([ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md) §5: this surface is ratified at OpenAPI, not unilaterally).

**The credential half of that coordination moved to [TASK-029](TASK-029-session-credential-and-refresh.md) §6** — two credentials in one storage slot, the renewal cycle, single-flight, and the five routes the partition does not classify. It landed 2026-08-18, before this task, so by the time this one ships the signer already holds and routes the credential correctly.

What remains for this task's signer PR: the descriptor route in place of reading requirements off the session read-model; `AUTH_PENDING` and `AWAITING_REAUTH` in its status union; `gate` on the requirement entries; the `AuthMethod` union widened to the full catalog; and the 423/429 split where it currently treats 423 alone as blocked.

Neither side ships alone, but the break is smaller than it was: this PR adds routes and states rather than withdrawing a credential from three shipped ones. Sequence them in one window.

---

## 7. Open follow-ups

⚑ Added 2026-08-18. `docs/tasks/README.md` §7 makes this section a deliverable rather than a courtesy; this record deferred things in §3's *Out of scope* without a durable home, and these are the ones that outlive the slice.

- **Re-opening with the link must stop being a free credential.** [TASK-029](TASK-029-session-credential-and-refresh.md) mints unconditionally at session open, which is correct while every gate is neutral — the link *is* the method. The moment a gate can be **failed**, a recipient who returns to their link and gets a fresh credential has bypassed it. ⛔ This is not a follow-up to schedule but a **property this slice must not ship without**; it is recorded here because it lives in another task's code and is invisible from this record's diff.
- **The `f5sign-signer` idle-recovery path depends on that same unconditional re-mint.** They built *renewal refused → re-open with the link → carry on* against the neutral world. Closing the hole above **breaks that path** for gated envelopes, and they need telling in the same window rather than discovering it. Their contact point is `docs/frontend-handoff/`.
- **`method_used` is a published single-member enum**, registered as a deliberate non-mirroring exception in `OpenApiSpecTest`. Widening it is a wire-contract change the front ends ratify, and the exception entry has to move with it or the census stops meaning anything.
- **The policy-override chain is still a convention with no level behind it** — [`BL-120`](../BACKLOG.md), unchanged by this slice, which reads the constants through the single point that keeps it cheap later.

---

## 8. Where this stopped, 2026-08-18 — read this before resuming

⚑ **Written so the next session does not re-derive any of it.** The durable homes are this section,
the five commit messages on `feat/two-gate-signer-auth`, and the amended clause in ADR-0049 §2.3.

### What is built and green

The three refusal kinds and their edge mapping (401 / 423 / **429 with `Retry-After`, exposed
cross-origin** — it is not CORS-safelisted, so without that the soft lock arrives with its wait
invisible); the fourteen-member catalog and the two typed slots; `Recipient`'s five columns with both
DBAL mappers and the migration; the Envelope authoring surface (availability port, the one-shot code,
the two `MACHINE_KEY` recovery routes, the lock on the sender read model); Session's mirror of the
catalog, `AUTH_PENDING` / `AWAITING_REAUTH`, the challenge and attempt children, the cumulative budget
and the two-tier lockout; **the credential mint made conditional on a passed gate, with the second
mint site on route 5**; routes 3 and 5; the child tables with the partial unique index; and the
published contract widened (`method_used` to fourteen, `auth_requirements` real, `Recipient.auth`).

### ✅ The 11 reds — CLOSED by `f026fdb`, and they were two causes rather than one

⚠ **The heading here read *"11 reds, one cause"* and the count and the cause were both off by one.**
The section enumerated ten — nine across three fixtures plus the hydration one, which it called *"the
eleventh"* when it was the tenth — and never mentioned the actual eleventh, which had a different
cause entirely. That is authoring rule 7's *"when an index collides, look for what else the same
stale view produced"*, one level up: the miscount was the visible artefact, the unrecorded red was
not. The original diagnosis is kept below because it was right about the ten and about the repair.

**The eleventh** was `OpenApiSpecTest::every_published_enum_is_pinned_to_its_php_enum_or_classified`
on `SigningSession.auth_requirements[].gate` — a published enum this slice added and classified
nowhere. Pinned to Session's `AuthGate`, and the asymmetry with its sibling `method` is written into
`PINNED_ENUMS`: `method` is the *declared* method and pins to the side that owns the declaration,
`gate` has no mirror at all.

**The tenth** needed more than a fixture repair, and the reason is worth carrying: this slice added a
column no *completed* session can hold. A lockout is armed by failing a gate and **cleared outright**
by passing it, so anything that reached `COMPLETED` has necessarily wiped `soft_locked_until`. The
predicate now spans two fixtures and asks that every column be written by at least one — which is
that test's own instruction (*extend the fixture until the column has a value*) rather than the
whitelist of allowed nulls it forbids. The four lockout columns also got the cold-reload enumeration
they shipped without.

**The nine** were repaired through
[`SeedsSentEnvelopes`](../../tests/F5Sign/Support/SeedsSentEnvelopes.php) rather than three more
copies of the seed — four private copies already existed and three more would have made seven; two
of the four are foldable and are `BL-155`, two are deliberately different shapes. One thing did not
survive the repair and is not a loss to mourn quietly: `SessionRenewalCeremonyHttpTest` named **one**
envelope and **one** recipient in *both* tenants, and that is not representable — `envelope.envelope`
and `envelope.recipient` are keyed by `id` alone, so two tenants cannot hold the same row whatever
row-level security does with visibility. Its docblock now says what actually makes the cross-tenant
case discriminating.

**Sabotage-verified**, per authoring rule 4: dropping `soft_locked_until` from the write mapping reds
the predicate *naming that column and listing both fixtures*, and reds the enumeration with it.
Restored; green again.

### ⛔ The original diagnosis, kept — do not "fix" the guard

Opening a session and committing now read the recipient's declared requirement across the BC
boundary. The open cannot decide whether to mint without it; the commit cannot know whether the
envelope is alive or what a signing challenge binds to. A missing envelope, or a recipient not on it,
collapses to 404 — the same collapse `SigningSessionReader` already performs.

**Three Session fixtures never create an envelope**: they mint a token over invented uuids, which
worked only because the open never read one. That is a **latent defect being closed** — a token
naming a nonexistent envelope used to open a real session row. Repair the fixtures:
`SigningCeremonyHttpTest`, `SessionRenewalCeremonyHttpTest`, `DbalSigningSessionRepositoryAppendTest`.
⚑ There is a working precedent in the same directory — `SigningReadEndpointsHttpTest` with
`SeededEnvelope` — so follow it rather than inventing a second way. Seed the **neutral** requirement:
these tests are about the ceremony, and a gated fixture would change what they assert.

The eleventh is `SigningSessionHydrationTest::no_stored_column_is_left_unwritten` —
`soft_locked_until` comes back NULL because the fixture never fails an attempt. Its own failure
message states the two possibilities; it is the second.

### What is left, in order

1. ~~The fixtures above.~~ **Done, `f026fdb`.**
2. HTTP acceptance for bars 1, 3, 6, 14. Then the two hard ones: **bar 4's concurrent half** (two
   genuinely overlapping requests — written sequentially it passes with the row lock absent, which is
   the whole reason it is worth writing) and **bar 13's second half**, asserted directly against the
   partial unique index.
3. ~~The lockout fact returning to Envelope.~~ **Done** — `AuthHardLockReached` → `OnAuthHardLockReached`
   → `RecordRecipientAuthHardLock`, shaped like `OnSessionCompleted` as this item asked, with
   `AuthHardLockCrossingTest` driving the whole crossing. ⚑ The load-bearing find sat underneath it:
   `submitAuthResponse()` drained pending events on **neither** branch, so this fact would have been
   recorded, committed and silently lost. See §9.
4. ~~Docs owed under authoring rule 7.~~ **Done, `d055505`** — ADR-0013's capability-matrix row is
   realized with its port, adapter and consumer named, and *Realized in* has the entry (the half of
   landing a decision that has no checklist). All four *"Foundation port"* surfaces are corrected —
   `AuthMethod`'s docblock, ADR-0049 §2.1, §2 above, **and the matrix's own intro line**, which
   called every row *"a Foundation capability"* and had this row as its counterexample; that fourth
   one was not in the list below and was found by opening the matrix rather than by grepping the
   phrase. TASK-022's twice-wrong adapter claim is fixed too. ⚑ ADR-0013 stays `Proposed`: one row
   moved, the mode-blind contract is still unenforced and there is still no `DEPLOYMENT_MODE`
   selector.
5. Merge `origin/develop` (TASK-028 landed at `0b0ee28`). ⚠ Run `make -C ../f5sign-infra init-roles`
   **before** migrating or it fails with `role does not exist`, which reads as a broken migration and
   is not. `docs/BACKLOG.md` on this branch is behind develop and will conflict — and now carries one
   more row of its own (`BL-155`). ⚠ **Re-derive any new `BL-` id against BOTH trees**: `BL-148`…
   `BL-153` exist only on develop, so a number that looks free here is not. That check is what caught
   `BL-155`, which was first written as `BL-149` from this branch's view alone.
6. Full suite on the isolated lane, then Infection.

### Harness — three measured facts, one correction, and one thing that changed

⚑ **Read this first, because it retires most of what follows for the common case.** The lane now
takes `WT_GATES`, so `lint`, `arch`, `phpstan` and `test` all run through it in one command and none
of the ad-hoc-container notes below apply to them:

```
WT_GATES="lint arch phpstan test" ../f5sign-infra/scripts/wt-validate.sh backend "$(pwd)"
```

Measured 2026-08-19 from this worktree: install + migrate + all four gates, with the suite itself at
**2:22**. The lane warms the dev container dump before PHPStan, which is the `BL-147` trap handled
for you. The notes below still hold for anything the lane does not run — and for `lint`, `arch` and
`phpstan` specifically, an ad-hoc container is still the quick way to re-check a docblock edit
without paying for a full lane run.

- **`--tmpfs /var/www/html/var/cache:rw,exec,mode=1777` on every test container.** `var/cache` is a
  bind mount shared between concurrent runs and they deadlock on it — 40+ minutes with no output,
  which reads as a slow suite. ⚠ **Not for PHPStan**, which reads the container dump from there and
  fails without it.
- **`timeout` goes INSIDE the container** (`sh -c 'timeout 600 php …'`). From the host it kills only
  the docker client and leaves the container running and holding locks.
- ⛔ **Never `docker kill` filtered on the image.** `--filter ancestor=f5sign/backend:dev` also matches
  the shared stack's `f5sign-php-fpm`. It happened here and took the stack down for other sessions.
- ⚠ **A correction:** the timeouts were first attributed to two suites sharing one database. That was
  wrong — it is the shared `var/cache`. Separating databases does not fix it, because the database was
  never the constraint. (Separating **clusters** is a different and also-real requirement — `BL-138`.)

---

## 9. Deviations, and what was found while closing — 2026-08-19

⚑ **Appended, not renumbered.** §1–§8 are anchors cited from other documents; §8 in particular is the
*"where this stopped"* record of the previous session and is deliberately left as it was written, with
its own corrections in place.

### The two bars that could not be discharged as written

**Bar 6's mis-bound challenge is not drivable over HTTP, and this is structural rather than an
omission.** [`Envelope::assignDocument()`](../../src/F5Sign/Envelope/Domain/Aggregate/Envelope.php)
calls `guardDraft()`, and no post-send method on that aggregate mutates an assignment — so a
recipient's signable set **cannot move after send**, and a challenge bound at issuance can never find
a different set at commit. `SigningSessionStateException::signingChallengeMisbound` therefore has no
route path. It is held at the aggregate tier instead, and better than the bar asked: the test asserts
the **absence of the `AuthGatePassed` fact**, not the exception class. The kind→409 mapping itself
does run through the edge listener, via a sibling factory.

**Bar 2's *"a consumed challenge cannot be replayed"* is unobservable as a state.** `commitSignature()`
consumes the challenge and completes the session in one call, so the 409 an HTTP test sees comes from
the completion guard rather than from the consumption — the two are indistinguishable from the wire.
Pinned where it *is* observable: a rehydrated `AUTH_PASSED` session holding a verified-and-consumed
challenge, the one reachable state where the completion guard is silent and the refusal is the
binding's alone.

**Bar 8's field-drafts half stays unwritten**, exactly as §5 instructs — nothing persists a field
value, so there is nothing to survive an ejection. The sentence is preserved rather than deleted.

### What was found that no bar named

Five of these were **defects in shipped code**, not gaps in coverage:

1. **A recipient with both gates declared could never sign.** `accessGateIsOpen()` reports whether the
   access slot is *neutral*; two call sites read it as whether the gate had been *passed*. Passing
   does not change a declaration, so the access gate stayed "open" forever and the signing gate was
   never selectable — while the commit demanded a signing challenge nothing could issue. This is §4's
   headline configuration. Fixed by [`OpenGateResolver`](../../src/F5Sign/Session/Application/Query/OpenGateResolver.php)
   plus an in-lock ordering invariant.
2. **`DbalSigningSessionRepository::submitAuthResponse()` drained pending events on neither branch.**
   A fact recorded at the gate was written to the row and thrown away. Found while building the
   lockout crossing, which it would have silently swallowed.
3. **`Recipient::recordAuthHardLock()` had no caller**, so `hard_locked` on the sender read model —
   §2's *"the whole point of surfacing anything here"* — could only ever be `false`.
4. **`withdrawAccessGrantAsIdle()` had no caller**, so `AWAITING_REAUTH` was unreachable. Bar 8 was
   not untested but unbuilt.
5. **Four of §2's five milestone facts did not exist.** Only *lockout reached* was ever built.

And three that were contract or gate defects:

6. **`POST /api/v1/signing/session` reached 404 and declared 200/400/401.** This slice made it
   reachable, by reading the requirement across the context boundary.
7. **The commit route grew four refusals and described none**, including two 401s that are not
   credential faults and that a client routes to renewal by default — where renewal fixes neither.
8. ⛔ **`OpenApiSpecTest`'s enum census walked `components.schemas` and never `paths`.** Every
   published enum happened to live in a component, so the set it exempted was **empty**: nothing
   could go red, and its green was the expected signal rather than evidence. This slice published the
   first four inline operation enums and every one sailed past the test whose whole purpose is to
   catch that. Authoring rule 5, in the file that teaches it.

### Prose that was instructing wrongly

Corrected rather than deleted, with the retired claim kept and dated: ADR-0013's *"a Foundation
capability"* (four surfaces, of which §8 had found three — the fourth was the capability matrix's own
intro line); ADR-0029's *"the auth-refusal kind is not minted"* and its three-row table for a
six-member family; ADR-0049's header, §5 and §6 plus its `docs/adr/README.md` index row; ADR-0035's
Tier-A set, which never named this work while its tests carried the tag; `tests/README.md`'s
`eIDAS-auth` carrier list, which cited a class TASK-028 had deleted and named 7 of 39 files;
`Version20260818000007`'s claim that an index existed (measured: Seq Scan); `Version20260818000006`'s
state census, which named 7 of 11 statuses while reading exhaustive; and
`GetSigningSessionController`'s `method_used`, whose inline comment and OpenAPI description both named
a mechanism the line does not use.

⚠ **One of those was written by this session and rotted inside it**: the `eIDAS-auth` census cell was
annotated *"36 files as of 2026-08-19"* and was 39 three commits later the same day. A count beside a
census command is the hand-maintained thing the command exists to replace.

### ⛔ What the security audit found, and what this slice does NOT close

The two-gate core held under attack — six paths checked for obtaining a credential without passing a
gate, all three mint sites gate-conditioned; the budget is non-restorable across challenge
replacement, row deletion, a re-open and two genuinely concurrent submissions; the lockout guard runs
**before** any comparison and `hash_equals` takes the known-good value first. What did not hold is on
the far side of a passed gate, and both findings share one root: **a proof is bound to the session,
and the session is shared by every holder of the link.** That is the exact observation §1 uses to
justify minting a credential rather than setting a flag — applied to the two surfaces where it was
not.

- ⛔ [`BL-158`](../BACKLOG.md) — **a code reset does not evict a party who already passed.** It
  replaces what the gate checks; it does not revoke what passing it already minted. Read, bytes and
  the ability to sign survive up to the twelve-hour cap. ⚠ **And the published contract said the
  opposite** — *"The previous code stops working immediately"*, true of the code and false as an
  eviction. §2 wrote the honest version for the *voided* envelope (*"both gates refuse"*, which this
  slice does close) and nobody wrote down that the reset has no equivalent. The endpoint's `#[OA\*]`
  now says a reset is the wrong tool once you believe someone is already in, and points at voiding.
  ⛔ **The fix is not available inside this task**: revoking an issued credential is the mechanism
  [`BL-152`](../BACKLOG.md) already records as missing — issuance is additive under
  [ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.6 — and changing that is a decision about
  the credential format, which is an ADR, not an edit here.
- ⚠ [`BL-159`](../BACKLOG.md) — **a verified signing proof is transferable and never expires.**
  `consumeSigningChallengeFor()` never calls `isLive()`, and the proof is bound to the session rather
  than to whoever answered it. The counterargument is real and partial: under a neutral access gate
  ADR-0028 already makes link possession the whole of identity, so nothing is stolen — what is lost is
  narrower, and it is precisely what §4 claims the signing gate buys.

⚑ **Neither is a regression this slice introduced**, and neither is a reason to withhold it: before
this task there was no gate at all, and a leaked link signed outright. They are the two places where
the model's own argument was not carried all the way, recorded here rather than discovered later.

### Deferred, with homes

- [`BL-157`](../BACKLOG.md) — `ensureLiveChallenge()` mints over an expired-but-unconsumed challenge
  and the partial unique index refuses it. ⚑ **Resolved 2026-08-19 by
  [TASK-022](TASK-022-delivered-codes-over-email.md)**, which is the slice that made it reachable; the
  paragraph below is left as the record of why this task could defer it. Unreachable at the time only
  because the sole issuance site passed `challengeExpiresAt: null` literally; [TASK-022](TASK-022-delivered-codes-over-email.md) §2 carries
  the warning at the site that will cause it.
- [`BL-155`](../BACKLOG.md) — four private copies of the sent-envelope seed remain beside
  `SeedsSentEnvelopes`; two are foldable, two are deliberately different shapes.
- [`BL-156`](../BACKLOG.md) — the `f5sign-signer` idle-recovery break, and the frontend handoff that
  carries it.

### ⚠ Two things a reader must not take from the green

- ⚠ **"Infection has no worktree-aware route" is false, and I asserted it twice before checking.** It
  is in §8's remaining list, in `CLAUDE.md`'s harness section, and — until this line — in the Status
  row above. `f5sign-infra`'s `wt-validate.sh` takes `WT_GATES="infection"` and mounts
  `docker/php/wt-infection.ini` for exactly the reason the prose gives for why it *cannot* work: the
  `-d memory_limit` flag does not reach the `phpunit` process Infection spawns, so the limit comes
  from a mounted ini instead of from a flag. The instruction was written when that was true and was
  repeated after it stopped being. ⚑ **The lesson is the one this section is full of**: the harness
  note and the harness had drifted, and reading the script took less time than restating the claim
  did.

  **It ran. `Covered Code MSI: 87%`, `MSI: 58%`, 4m39s** — 3983 mutants killed, 547 covered-but-undetected,
  2249 not covered (repo-wide, not this slice). Both gates pass: `minCoveredMsi: 79` and `minMsi: 50`.

  ⛔ **And that does NOT establish Tier-A conformance, which is the thing worth being careful about.**
  [ADR-0035](../adr/ADR-0035-testing-standard.md) sets Tier A at covered-MSI **≥ 90** and this is a
  **global** 87 — but the two numbers are not comparable in either direction, because Infection gates
  one value over the whole of `src/F5Sign` while an assurance tier is a `#[Group]` on *tests*. There
  is no per-tag figure to compare, which is precisely the design problem ADR-0035 records as the
  reason its per-tier gate is still deferred ([TASK-019](TASK-019-requirement-traceability-and-per-tier-gates.md)).
  So the honest statement is: **the configured gate passes, and this slice's Tier-A number is not
  measurable today.** ⚠ Do not read 87 as "three points short of Tier A" — it is a different
  population. And per `infection.json`'s own instruction, `minMsi` is a tripwire and not a target:
  do not raise it because a run came in over it.
- **The migration set on this branch was rewritten twice on 2026-08-19** — renumbered from
  `…0003/0004` to `…0006/0007` when `develop` turned out to own those numbers, then edited again to
  add the missing index. Anyone who ran the branch before that has `doctrine_migration_versions` rows
  naming migrations that no longer exist, and will hit `ADD COLUMN` failures that read as broken SQL
  and are not. **Reset the local test database before running this branch.**
