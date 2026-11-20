# TASK-038 — A voided envelope closes the ceremony, not only its writes

| Field | Value |
|-------|-------|
| **Status** | ✅ **Done — landed 2026-08-26, closed 2026-08-28.** Branch `feat/terminal-envelope-and-credential-retirement`, commits `bb6c43c` (the three crossings that read the envelope) and `a7b350f` (the reactor and the revoked session row). Green on the ephemeral worktree lane 2026-08-28: `lint 0 of 1036` · `Deptrac Violations 0` · PHPStan `[OK] No errors` · `OK (2460 tests)` — ⚑ the test count is pinned and the **assertion count deliberately is not**: it is non-deterministic across runs, as `3cff138` recorded when the same trap fired on ADR-0058. Falsifiable as written: `grep -c isTerminal src/F5Sign/Session/Application/Query/SigningSessionReader.php src/F5Sign/Session/Application/Query/SigningDocumentReader.php` returns a non-zero count for each, and [ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) reads `Accepted`. ⚑ The row previously read *"⏳ Not started. No branch, no code, no tests"* with a `git branch` probe that is no longer empty. |
| **Type** | **Gap closure.** No new capability: it adds a precondition four crossings never had, plus the cross-BC reactor [TASK-015](TASK-015-envelope-void.md) deferred. |
| **Why** | A cancelled envelope stays **readable**. [TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md) closed the write half — issuance, auth submit and commit all refuse a terminal envelope — and [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) guarded the *pre-send* half of the read path. Nothing guards the **terminal** half of the read path, so after `POST /api/v1/envelopes/{id}/void` the recipient's read model and the document bytes keep serving. ⛔ **And under a neutral access gate the session open itself keeps minting**, so the exposure is not a pending credential expiring but a working front door for the remaining life of the signing token — `+7 days` per `StoreBackedSigningTokenIssuer::LIFETIME`. |
| **Builds on** | **[TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md)** for the `envelopeIsAlive` seam and its cross-boundary rule (read behind the token seam where tenant scope exists, never at the public edge). **[ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md)** for the guard placement and the census test this extends rather than duplicates. **[TASK-015](TASK-015-envelope-void.md)** §4 for the reactor design, whose stated justification this task replaces. Reused unchanged: [ADR-0008](../adr/ADR-0008-read-side-realization.md)'s cross-BC read port, [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md)'s exception mapping, [ADR-0031](../adr/ADR-0031-event-log-store.md)'s relay. |
| **Sibling** | ⚑ **[TASK-039](TASK-039-retiring-a-credential-whose-holder-changed.md) — co-lands on one branch** (decided 2026-08-25): shared Session-subscribes-to-Envelope seam, built once. ⛔ The same green promotes **both** ADRs, so the changeset owes `Status`, `Enforced by` and `Realized in` for ADR-0059 **and** ADR-0060 (`CLAUDE.md` authoring rule 7), and a review blocking on either half blocks both. ⚠ Order **within** the branch still matters: §5's residual-window argument depends on the synchronous guards landing before or with the reactor, never after. |
| **Decision record** | **[ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md)**, **`Accepted`** — promoted 2026-08-28 with this slice's green, per `CLAUDE.md` authoring rule 7. ⚠ **This row read `Proposed` until 2026-09-01, five lines below a `Status` row citing *"ADR-0059 reads `Accepted`"* as its own falsifier** — a file contradicting itself, which is the check rule 1 asks for and which the promotion changeset skipped. ⛔ **Amended the same day**: §2.1's `isTerminal()` spelling is superseded for the three *read* crossings by `EnvelopeStatus::withholdsDocumentFromRecipient()`, because it also refused `COMPLETED` and closed a signer's own signed copy — the distinction that record's own §7.4 argues and its §2.1 erased. Promotion was the user's call, never taken here unilaterally. |
| **Delivery bar** | For an envelope whose `status->isTerminal()` is true: `POST /api/v1/signing/session` **mints nothing** and says the leg is closed; the recipient read model and the document bytes **refuse**; `POST /api/v1/signing/session/renew` **refuses**; and a live session carries `SessionStatus::REVOKED` once `EnvelopeVoided` is consumed. For a live envelope every path behaves exactly as before. |
| **Blocks** | Nothing declares this a hard dependency. It unblocks the honest closure of [`BL-87`](../BACKLOG.md) and retires [`BL-61`](../BACKLOG.md)'s terminal-direction extension. |

---

## 1. Why this task exists

**The write half is closed, the read half is not, and the records that describe the gap understate
it.** Three separate documents point at this work and none of them names all of it:

- [TASK-015](TASK-015-envelope-void.md) §4 deferred its Session revocation reactor because
  *"`commitSignature` does not check envelope status"*. It does now. The deferral's premise is gone;
  its subject is not.
- [`BL-87`](../BACKLOG.md) describes the harm as *"a voided envelope's documents stay readable to an
  **outstanding** signing token"* and asks for the posture to be decided before the reactor is built.
- [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.6 hands the terminal
  direction forward by name and bounds a related window at *"the 12-hour absolute cap"*.

**All three miss the session open.** Under a neutral access gate, arriving with the link *is* passing
the door ([ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) §2.2), so
`StartSessionUseCase` mints a fresh access credential and refresh credential on **every** open with no
envelope precondition. The twelve-hour cap does not bound that: it is measured from
`credentialFirstMintedAt`, which `SigningSession` writes once and never moves, and it is consulted
only inside `renewWith()`. A re-open does not renew — it mints. So the bound is the signing token's own
seven-day life, and issuance is additive with nothing to revoke it
([ADR-0045](../adr/ADR-0045-issued-credential-format.md) §2.6).

⚠ **Behind a *declared* gate the exposure is the smaller one `BL-87` describes** — both gates refuse a
dead envelope, so only a credential minted before the void survives, for at most twelve hours. The
weaker case is the neutral one, which is the default.

⚠ **[`BL-158`](../BACKLOG.md) says the opposite in passing and it is a sentence to correct.** It reads
*"a void refuses both gates and the credential buys nothing"*. The credential buys no **act**. It buys
every read, and under a neutral gate it can be re-minted at will.

## 2. What already exists (reuse, do not rebuild)

- **The seam and the predicate.** `RecipientAuthContextReader::read()` already computes
  `envelopeIsAlive: !$context->status->isTerminal()` behind the token seam, and already carries the
  `sentAt` guard [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) installed.
  Nothing new is read; the answer is one field away at every crossing.
- **The guard shape at two of the four crossings.** `SigningSessionReader::read()` and
  `SigningDocumentReader::read()` each refuse on `$context->sentAt === null`. The terminal check sits
  beside it, not instead of it — the two predicates answer different questions.
- **The census.**
  [`SigningReadersRefuseUnsentEnvelopeTest`](../../tests/F5Sign/Session/Application/Query/SigningReadersRefuseUnsentEnvelopeTest.php)
  scans `src/F5Sign/` for callers of `getContextForRecipient()` and fails on any not classified. It
  gains a second axis; it is not duplicated.
- **The reactor's design.** [TASK-015](TASK-015-envelope-void.md) §4 already specifies the shape:
  a new terminal `SessionStatus` member, `SigningSession::revoke()`, a `findByEnvelope(tenant, envelopeId)`
  finder over the existing `(tenant_id, envelope_id)` index, and the subscriber/handler pair on
  `event.bus`. Reuse it; only its justification changes.
- **The event.** `Envelope::void()` already records
  [`EnvelopeVoided`](../../src/F5Sign/Envelope/Contract/Event/EnvelopeVoided.php) with tenant, envelope,
  actor, reason and instant. It has zero consumers today; this task writes the first.
- **The convergence shape to mirror.** `Envelope::recordRecipientCompletion()`'s terminal branch is a
  silent no-op precisely so an at-least-once redelivery does not dead-letter. The reactor's revoke
  needs the same disposition.

## 3. What gets built

**Commit 1 — the four synchronous guards.**

- `StartSessionUseCase` refuses a terminal envelope and therefore mints nothing.
- `SigningSessionReader::read()` refuses.
- `SigningDocumentReader::read()` refuses, as a bare `null` before any object is fetched — the shape
  its `sentAt` guard already uses.
- The wire spelling of the recipient-facing refusal, per §5.
- The census extended to demand a terminal classification per crossing.

**Commit 2 — the reactor and the renewal.**

- `SessionStatus::REVOKED`, a new terminal member.
- `SigningSession::revoke()` — guard, mutate, `record()` — converging silently on an already-revoked
  session.
- `SigningSessionRepository::findByEnvelope(tenant, envelopeId)` and its DBAL implementation.
- `Session/Application/Subscriber/OnEnvelopeVoided.php` (a pure `Reactor`) plus its Messenger handler
  on `event.bus`, dispatching a `RevokeEnvelopeSessions` command to a use case that loads the live
  sessions and revokes each.
- `RenewSessionCredentialUseCase` refuses a revoked session — **by session state, with no envelope
  read** ([ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.3).

## 4. Scope

**In scope:** everything in §3, the tests of §6, and the `docs/` reconciliation of §7's first two rows
— which are corrections of claims this task falsifies, not follow-ups.

**Out of scope:**

- **Credential invalidation.** Nothing here makes an issued credential stop being one.
  [`BL-152`](../BACKLOG.md) (a corrected address whose old link keeps working) and
  [`BL-158`](../BACKLOG.md) (an access-code reset that does not evict) need a mechanism this task does
  not build, and must not be reported as closed by it. Their home is a decision about
  [ADR-0045](../adr/ADR-0045-issued-credential-format.md)'s credential format.
- **Revoking the signing token.** After this, the emailed link over a voided envelope opens nothing,
  but its row in `session.signing_token` lives out its seven days. Hygiene, and it belongs to the
  credential-invalidation record above.
- **Telling the recipient the envelope was cancelled.** `NotificationPurpose` has no member for it and
  nothing consumes `EnvelopeVoided` on the Notification side. §5 makes the cancellation legible to
  someone who returns to the link; it does not reach out. ⚑ Adding a purpose is **not** free: the SMS
  catalog authors every purpose in every locale and `SmsCopyTest` iterates
  `NotificationPurpose::cases()`, so a new member reddens that suite until copy exists in both
  locales, inside a one-segment budget.
- **Voidability from `ROUTING_FAILED` / `SEALING_FAILED`** — [TASK-015](TASK-015-envelope-void.md) §5's
  D1 widening, a change to `Envelope::void()`'s own guard and not to anything here.
- **Any change to the write half.** The three act-guards and the terminal no-op stay exactly as
  TASK-021 and ADR-0058 left them.

## 5. Key decisions

- **The predicate is `isTerminal()` and it sits beside `sentAt`, never merged with it.** They answer
  different questions — *could a recipient ever have read this* versus *may this still be acted on*.
  [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §7.1 argues why the first must
  not be a status list; the second is *already* the property-shaped spelling, because `isTerminal()`
  answers for every member including ones not yet added.
- **The open is the load-bearing crossing.** Guarding the read model and the bytes while leaving the
  open unguarded would leave a cancelled envelope with a working ceremony door minting credentials
  that buy nothing — defensible, but it burns a mint on every knock and publishes a live door.
- ⛔ **The guards are the guarantee; the reactor is the record and the renewal's mechanism.** They look
  like duplication and they are not ([ADR-0059](../adr/ADR-0059-terminal-envelope-closes-the-ceremony.md) §2.4,
  [`docs/LOAD-BEARING.md`](../LOAD-BEARING.md) §2). The guards are synchronous and depend on nothing;
  the reactor rides the relay and is therefore always slower than the void. Anyone who reads the two
  and removes the "redundant" synchronous check has the direction backwards.
- **A closed leg is published, not hidden.** [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md)
  §2.4 states the axis — *did this party ever legitimately have a ceremony* — and answers **no** for an
  unsent envelope, collapsing it into 404. Here the answer is **yes**, which is
  [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) §2.1's case: the recipient must
  be able to learn there is nothing left to prove.
- ⚠ **The wire spelling is decided in this task, not inherited.**
  [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md) §2.2 made the published
  `status` union a breaking change once, on the argument that an un-updated client's failure mode was
  *the same dead end it already had*. Re-answer that against the union as it stands when this is
  built — third member versus a field beside it, and whether `/v1` bumps ([`BL-59`](../BACKLOG.md)) —
  and write the answer here. The bytes path stays a bare refusal; the read model carries the
  explanation.
- **The renewal reads session state, never the envelope.** A cross-BC read on the renewal would run
  every fifteen minutes for every live session, forever, to answer a question that changes at most once
  per envelope — and for the overwhelming majority of envelopes, never.
  [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) §2.6 declined the same read on
  the same route for a weaker version of this reason.
- **The residual window is accepted and named.** Between the void and the revocation a renewal can
  still succeed. It mints a credential that buys only reads, and every read is refused synchronously by
  commit 1 — so the residual is harmless rather than merely small. ⛔ That argument depends on commit 1
  landing first or with it; commit 2 alone re-opens it.

## 6. Verification

Run through the **worktree lane** — `make -C ../f5sign-infra wt-backend src=$(pwd)` — which is the only
harness that mounts this tree. ⛔ The bare `make test` / `make phpstan` targets bind the main checkout
and report green for whatever branch it is sitting on.

**Properties to lock, one per crossing, each sabotage-checked individually** (`CLAUDE.md` authoring
rule 4 — revert the guard, watch its own case fail for the right reason, restore):

1. A terminal envelope's session open mints nothing — asserted as *nothing was minted*, not merely
   that the call refused.
2. A terminal envelope's read model refuses.
3. A terminal envelope serves no document bytes. ⚠ The fixture must model a recipient whose bytes
   **really would** be served otherwise; ADR-0058 §5.4 records this exact tripwire passing with the
   guard reverted because its fixture could serve nothing either way.
4. A renewal against a revoked session refuses.
5. A redelivered `EnvelopeVoided` over an already-revoked session is a silent no-op, not a throw.
6. Every live envelope path is unchanged — the discriminating case, since all five above pass trivially
   on a system that refuses everything.

**The census is the load-bearing test.** Extend
[`SigningReadersRefuseUnsentEnvelopeTest`](../../tests/F5Sign/Session/Application/Query/SigningReadersRefuseUnsentEnvelopeTest.php)
to demand a terminal classification per crossing, then check it the way its author did: drop a known
member and confirm it fails **naming** that member.

**One acceptance case that cannot be a unit test.** Void an envelope with a **neutral** access gate,
then re-open the link and assert nothing is minted. This is the chain §1 describes, and it is currently
traced from source and never executed — so no bar in this repo may quote the *seven days* figure until
this case runs.

**Gates:** `WT_GATES="lint arch phpstan test"` is the default four; `infection` is the opt-in fifth.
Quote what the lane actually printed, not a remembered figure.

## 7. Open follow-ups (track, don't solve here)

- **Correct [TASK-015](TASK-015-envelope-void.md) §4 and §5.** §4's deferral reason is falsified (the
  commit *does* check status, and the terminal no-op is verified rather than *"unverified, confirm when
  building this"*). §5's *"explicit token revocation — stateless HMAC has none today"* is falsified by
  [ADR-0045](../adr/ADR-0045-issued-credential-format.md): the token is store-backed, so a row exists
  and revocation is mechanically possible; what is absent is a `revoked_at` column and a chokepoint.
  ⚑ Keep the historical framing where it is a record of what changed; sweep only claims about the
  present (`CLAUDE.md` authoring rule 1).
- **Correct the `Envelope::void()` docblock.** It says *"In-flight signing is not terminated yet"* and
  names only `appendDocumentArtifact()` as the write-side guard, which under-claims what TASK-021 and
  ADR-0058 hold. Its last sentence — *"an already-minted signing token keeps its **read** access"* — is
  the part this task falsifies.
- **Correct [`BL-158`](../BACKLOG.md)'s parenthetical** (§1's last warning) and close
  [`BL-87`](../BACKLOG.md) naming what closed it. [`BL-61`](../BACKLOG.md)'s terminal-direction
  extension retires with it; its pre-send half was already retired by ADR-0058.
- ~~**The cancellation notice**~~ — **done by [TASK-040](TASK-040-cancellation-notice.md)** (2026-09-29, `feat/ending-notice`), for every ending without agreement and not only the sender's void, with the `SmsCopyTest` consequence §4 names. ⚑ Its audience is **not** the completion notice's: it goes only to recipients the platform actually wrote to, or it tells a dormant-step recipient about a document they were never shown.
- **Credential invalidation**, serving [`BL-152`](../BACKLOG.md) and [`BL-158`](../BACKLOG.md) — its own
  ADR amending [ADR-0045](../adr/ADR-0045-issued-credential-format.md), and where the token's
  `revoked_at` belongs.
- **D1 widening** — voidability from `ROUTING_FAILED` / `SEALING_FAILED`.
- ⛔ **Nothing enforces the publish-versus-hide axis of §5.** `deptrac.yaml` grants `SessionApplication`
  the whole `EnvelopeContract` layer, so nothing mechanical stops the terminal check drifting into a
  controller or the aggregate either. ADR-0058 §5.3 records the same absence for its own guards; this
  task adds four more crossings under it and closes neither.

## 8. Deviations & honest notes

Written at close, 2026-08-28, alongside §7's disposition.

**§7 disposition — three of its bullets discharged inside this changeset, and they were the three that
were *corrections* rather than future work:** [TASK-015](TASK-015-envelope-void.md) §4/§5 (in
`a7b350f`), the `Envelope::void()` docblock whose last sentence this task falsified (its replacement
quotes the falsified claim rather than deleting it, per `CLAUDE.md` authoring rule 2), and
[`BL-87`](../BACKLOG.md) + [`BL-61`](../BACKLOG.md), now moved to the Closed table naming this branch.
Everything else in §7 stayed open, unchanged: [TASK-040](TASK-040-cancellation-notice.md) (since done, 2026-09-29), D1 widening,
and the deptrac absence — which this task *widened* by four crossings and did not close.

**Credential invalidation did not stay a follow-up.** §7 lists it as one, serving
[`BL-152`](../BACKLOG.md) and [`BL-158`](../BACKLOG.md); it co-landed on this branch as
[TASK-039](TASK-039-retiring-a-credential-whose-holder-changed.md) /
[ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md). ⚑ **It is still not this
task's mechanism**, which is the distinction the `Sibling` row exists to keep: the guards here are a
predicate over envelope state, and nothing in them would have answered a holder who stopped being
legitimate.

**No deviation from §4's scope.** The three act paths still publish the status-derived `CONFLICT`
rather than a finer code — §4 put that out of scope as a breaking wire change, and
[`EnvelopeNoLongerLiveException`](../../src/F5Sign/Session/Application/Exception/EnvelopeNoLongerLiveException.php)'s
docblock records why the plausible cleanup (folding it into the domain exception) would ship that
break by accident.

⚑ **That paragraph stopped describing the tree on 2026-09-16 and is kept as the record of this task's
scope.** [ADR-0067](../adr/ADR-0067-a-refused-commit-names-its-condition.md), realized by
[TASK-043](TASK-043-a-refused-commit-names-its-condition.md), made `SigningSessionStateException`
`ProblemCoded`: the act paths each name their condition now, and the wire change **was made rather than
avoided, to be shipped as a coordinated release** — handed off before the merge, merged into `develop`
at `acb20d0` and pushed on 2026-09-16, and not deployed. ⛑ This clause read *"and on 2026-09-16 neither
merged nor deployed"* until the merge, later that same day. ⛑ This read *"was **shipped** as a coordinated release"* until the same day,
when ADR-0067's promotion was read against *exercised is not deployed*. ⛔ The docblock cited above no
longer carries the claim cited from it — it was corrected in the same changeset — so read this paragraph
as *what §4 put out of scope*, not as a live description. The split between the two exceptions survives;
it was never what made this task's change non-breaking.

⚠ **One honest limit on the acceptance evidence.** `TerminalEnvelopeClosesTheCeremonyHttpTest` proves
the re-open mints nothing by asserting the response body carries no credential members. That is the
right assertion for the wire, but it is not a proof that nothing was *written*: the use-case-tier case
`a_terminal_envelope_opens_no_session_and_mints_nothing()` is what holds the transaction property, and
the two are needed together rather than either alone.
