# TASK-035 — A signature requires an envelope a recipient could already have read

| Field | Value |
|-------|-------|
| **Status** | ✅ **Built on `fix/signature-requires-readable-envelope` off `develop` at `d68ce50`.** Green on the **worktree lane** (`make -C ../f5sign-infra wt-backend src=$(pwd)`), the only harness that validates this tree: `lint 0 of 1018` · Deptrac `Violations 0` · PHPStan L9 `[OK] No errors` · **2402 tests** (assertions drift by one between runs — §6.1 quotes the range). ⛔ **No `develop` baseline is quoted, and the omission is
deliberate.** This row carried `2321 / 11041` until an audit traced that pair to
[ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md)'s header — another branch, another
day. `develop` was never measured here, and the implied delta was impossible anyway: `#[Test]` count is
**1783 at `d68ce50` and 1790 at HEAD**, seven new methods, not sixty-five. A number that looks
authoritative with nothing behind it is worse than no number. ⚑ **Every one of the five guards was sabotage-checked individually** (§6.2) and each failed naming its own case; the census was checked by dropping a known member. ⚠ **That pass found a real weakness rather than confirming the work** — one case was passing with its guard reverted; §9 carries it. ✅ **Merged to `develop` by fast-forward on 2026-08-25, and [ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md) promoted to `Accepted` in the same set.** ⚠ Verify the tip against `git log` rather than trusting this row — a fast-forward leaves no merge commit to cite, so `develop` simply carries this branch's five commits. |
| **Type** | **Gap closure.** No new capability: it adds a precondition the ceremony never had. The decision it realizes was already taken; what is left is placement, refusal shape and tests. |
| **Why** | Nothing in the Signing Session BC ever asked what state the envelope was in — no file under `src/F5Sign/Session/` imported `EnvelopeStatus` — and none does now (`rg -n 'use F5Sign\\Envelope\\Contract\\Type\\EnvelopeStatus' src/F5Sign/Session/` returns nothing). ⚠ Read that as the import claim it is: the looser *"appears nowhere"* is false by raw grep, and TASK-021 had already made the ceremony ask the *terminal* half via `status->isTerminal()`. So a recipient could be walked through signing an envelope the sender never sent, and the consequence is not a ceremony anomaly but **state-machine corruption**: a `DRAFT` envelope reaching `READY_TO_SEAL` without passing `send()`, skipping `ensurePreSendInvariants()`, `pinSendArtifact()`, `EnvelopeSent` and `EnvelopeRosterDeclared` — the legally-material required-set roster (INV-B). |
| **Builds on** | **[TASK-021](TASK-021-two-gate-auth-model-and-access-gate.md), reused rather than extended** — it introduced the `envelopeIsAlive` seam for the *terminal* direction of this same control, and its cross-boundary shape (read behind the seam where tenant scope exists, never at the public edge) is the constraint this obeys. [TASK-028](TASK-028-opaque-signing-token.md) owns the credential this refuses to mint. Reused unchanged: [ADR-0008](../adr/ADR-0008-read-side-realization.md)'s cross-BC read port, [ADR-0029](../adr/ADR-0029-domain-exception-http-mapping.md)'s exception mapping. |
| **Decision record** | **[ADR-0058](../adr/ADR-0058-signature-requires-a-readable-envelope.md)**, **`Accepted`** *(exercised)* — promoted 2026-08-25 by the user on this slice's own bars, after the audit in §9. It **amends [ADR-0028](../adr/ADR-0028-recipient-signing-token-auth.md)**. ⚑ Its §5 bars are green and it is promoted; this slice is what exercised it, so the Status, `Enforced by` and `Realized in` rows all landed here rather than in a later changeset (`CLAUDE.md` authoring rule 7). |
| **Delivery bar** | For an envelope with `sent_at IS NULL`: the sender-side mint answers **409 `ENVELOPE_NOT_SENT`** and **no credential is created**; every recipient-facing route answers **404**, indistinguishable from a wrong id; and `Envelope::recordRecipientCompletion()` **refuses** rather than advancing. For a sent envelope every recipient-facing path behaves exactly as before. ⚠ **Not the mint**: it also stops issuing for an envelope that does not exist, belongs to another tenant, or does not carry that recipient — a deliberate gain recorded in §3, and a contract change beyond *unsent*. |
| **Blocks** | `TASK-033` (delegated signature) declares this a **hard dependency** that must land first: it adds a machine route that signs with no link in existence, which removes by construction the accident that makes this gap harmless today. |

---

## 1. Why this task exists

`BL-61` was filed on 2026-08-03 and traced on 2026-08-10; `BL-66` is its write half. Neither was ever
executed — both were reasoned from source. The mechanism:

`CommitSignatureUseCase` never loaded the envelope, so `SessionCompleted` reached
`Envelope::recordRecipientCompletion()`, whose only envelope-level guard was
`$this->status->isTerminal()` — and `isTerminal()` is `COMPLETED|DECLINED|VOIDED|EXPIRED`. **DRAFT is
not in that set.** The guard's own comment showed it had been written against the VOIDED walk-back, so
DRAFT was unconsidered rather than rejected.

**What made it urgent is that the accident keeping it harmless is being removed.** Today nobody holds
a signing link before the send, because the only way to get one is a sender-side mint a sender
performs as part of sending. `ADR-0055` §2.8 records a forge chain (`BL-184`) that composes three
shipped routes into a signature, and states that its blast radius depends on precisely this question:
*"If it does, forging one means sending it, which notifies real recipients and is loud; if it does
not, the whole sequence is silent."*

## 2. What already exists (reuse, do not rebuild)

- **The predicate, and its exact spelling.** `Envelope::correctRecipientContact()` already refuses an
  unsent envelope as `sentAt === null` — explicitly *not* `status === DRAFT` — and
  `EnvelopeStateException::notYetSent()` already existed to say so. Nothing new was invented here.
- **The cross-boundary shape.** TASK-021's `envelopeIsAlive` established that the answer is read
  **behind the seam** where tenant scope exists, never at the public edge, which would need an
  unscoped read on a public route (`BL-87`).
- **`RecipientEnvelopeContextView` already carries `sentAt`.** No Envelope-side change, no new port,
  no new query: the fact was already crossing the boundary and nobody was reading it.
- **The refusal types.** `SigningSessionNotFoundException` (404) and `ConflictException` +
  `ProblemCoded` (409) both exist; only one new `code` was added.

## 3. What gets built

| # | Where | What |
|---|-------|------|
| 1 | `RecipientAuthContextReader::read()` | Refuses when `sentAt === null`. **The one crossing six routes share** — the open, the descriptor, the OTP send, the auth submit, the read model and the commit. |
| 2 | `SigningSessionReader::read()` | Same refusal for the read model. |
| 3 | `SigningDocumentReader::read()` | Bare `null`, before any object is fetched. Defence in depth — see §4. |
| 4 | `SigningTokenIssuance` (new, `Application/Service/`) + `SigningTokenNotIssuableException` (new) | The sender-side mint guard and its 409 `ENVELOPE_NOT_SENT`. `MintSigningTokenController` is rewired to it. |
| 5 | `Envelope::recordRecipientCompletion()` | Refuses — a **throw among no-ops**, argued in ADR-0058 §2.5. |
| 6 | `config/packages/nelmio_api_doc.yaml` | Publishes `ENVELOPE_NOT_SENT`, forced by a pre-existing gate in the same commit. |

**No `deptrac.yaml` change and no new cross-BC dependency.** `EnvelopeStatus` still appears nowhere
under `src/F5Sign/Session/`; the guards read `sentAt` off a view that already crossed.

## 4. Scope

**In:** the five guards above, their tests, the census that keeps them honest, the ADR, this record,
and the `BL-61`/`BL-66`/`BL-51` backlog rows they close.

**Out, by decision rather than by omission:**

- **The terminal direction** — a signing token outliving a voided envelope, stateless, seven days,
  no revocation (`BL-61`'s extension; `BL-87` holds the read half). TASK-021 closed the write half.
  It is out because the mechanism it needs is **a credential that can be invalidated**, which is a
  decision about ADR-0045's credential format (`BL-152`, `BL-158`), not about envelope readability.
  Answering it here would answer it in the wrong record. ⚑ **Decided explicitly**, because the
  handoff that opened this task asked for it either way.
- **`POST /signing/session/renew`** carries no guard: it performs no envelope read at all. ⚠ The
  reason first given here — *"the renewal credential only ever comes from an open that now refuses"* —
  is false: `SessionCredentialCodec::mint()` is called from **three** places, and the auth submit is
  the second mint site the route file itself labels as such. The conclusion survives because the open
  **and** the auth submit both cross the guarded reader. ⛔ **But only for sessions opened after this
  ships.** A row created before it, over an unsent envelope, keeps a live refresh digest for up to the
  12-hour absolute cap; the exposure is a renewal oracle and nothing more, since every route that
  credential buys is guarded — and no backfill closes it. Recorded rather than fixed.
- **A PHPStan rule** enforcing that new crossings carry the check. The census test in §6 does the job
  at a fraction of the cost; a rule is worth revisiting only if the crossings multiply.

## 5. Key decisions

1. **`sentAt IS NOT NULL`, never a status list** (ADR-0058 §2.1). A status enumeration re-opens the
   hole silently for whoever adds the next pre-send status.
2. **At the crossing, not on the aggregate** (§2.2). `envelopeIsAlive` is a boolean into
   `SigningSession` because the *domain* must answer it as part of a transition. This question is
   answered before there is a transition: an unsent envelope has no ceremony to refuse.
3. **404 to a link holder, 409 to the sender** (§2.4). Two audiences, two honest answers — and the
   deliberate opposite of [ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md),
   which requires a pre-credential route to *publish* a closed leg. The axis is *did this party ever
   legitimately have a ceremony*.
4. **The write half throws where both its neighbours converge** (§2.5). *Moot* versus *impossible*.
5. **The mint is guarded because issuance is additive and nothing revokes** (ADR-0058 §2.3). ⚠ The
   no-revocation half is [TASK-028](TASK-028-opaque-signing-token.md) §4.3's decision, **not** ADR-0045
   §2.6's, which only says the plaintext is stored as a digest.
   A credential minted in error cannot be recalled, so the only moment to prevent it is before it
   exists — which is why every mint test asserts *nothing was minted*, not merely that the call raised.

## 6. Verification

### 6.1 The gates

Worktree lane, 2026-08-25, after the audit repairs and the `develop` merge: `lint 0 of 1018` · Deptrac
`Violations 0` · PHPStan `[OK] No errors` · **2402 tests**, assertions `11460`–`11463`.

⚠ **The assertion count is quoted as a range because it is not stable, and the instinct to pin it to one
number is what §9.4 is about.** Five lane runs over this tree gave 11460, 11461, 11462, 11463 and then
**11461 again**, with the test count fixed at 2402 and, across the last three, no code change at all. It
is **non-deterministic within a narrow band, not a drift** — a fourth reading of *"+1 per run, so
something asserts once per something that grows"* was written here after four samples and falsified by
the fifth, which is the same mistake as pinning a figure, one level up. **Not diagnosed.** Named rather
than smoothed into a single number that would look measured and be wrong on the next run. `lint 0 of N` and the test *count* are exactly reproducible; treat those as the gate evidence.

**Infection** (the opt-in fifth gate, `WT_GATES="infection"`): **MSI 56%** and **Covered Code MSI
84%**, both over their floors (`minMsi: 50`, `minCoveredMsi: 79`), exit 0.

⚠ **Per-file attribution for the five guards was NOT captured, and is reported as absent rather than
assumed clean.** The escaped-mutant detail lives in `var/infection/infection.log`, and the lane mounts
`var/` as a named volume that its `down -v` teardown destroys — so the file does not survive the run
that produced the number above. A first attempt to grep it locally returned zero hits **for every
file**, which is what grepping a missing file returns; that is the shape of a false all-clear and is
recorded here rather than quietly dropped.

⚑ **The sabotage pass below is the stronger evidence for these five guards anyway**, and is the one
`CLAUDE.md` authoring rule 4 calls load-bearing: mutation score asks whether *some* test would notice
*some* change, while reverting the guard and watching a named case go red answers the actual question
directly.

### 6.2 The sabotage pass — what actually separates a real guard from a decorative one

Each guard reverted in turn, suite re-run, guard restored:

| Guard reverted | Result |
|----------------|--------|
| `RecipientAuthContextReader` | 1 failure — `the_auth_context_reader_refuses_an_unsent_envelope` |
| `SigningSessionReader` | 1 failure — `the_session_read_model_refuses_an_unsent_envelope` |
| `SigningDocumentReader` | 1 failure — the bytes case, **printing the bytes it would have served** |
| `SigningTokenIssuance` | 1 failure — `it_refuses_to_mint_for_an_envelope_that_was_never_sent` |
| `Envelope::recordRecipientCompletion()` | 2 failures — both write-half cases |
| A member dropped from the census map | 1 failure, **naming the dropped class** |
| `sentAt` hydration → `null` (availability direction) | 1 failure — `it_carries_sent_at_through_verbatim_in_both_directions` |
| `sentAt` hydration → coalesced non-null (**security** direction) | 1 failure — the same case, second assertion |
| A second, unguarded crossing in an already-classified class | 1 failure — `every_crossing_is_guarded_as_many_times_as_it_crosses` |
| A `CLASSIFIED` pointer aimed at a nonexistent case | 1 failure — `every_classified_row_names_a_case_that_exists` |
| A crossing added in another BC entirely | 2 failures — the class census and the callsite count |
| A second `issueFor()` inside an already-classified minting class | 1 failure — `every_caller_of_the_signing_token_issuer_is_classified` |
| A `{@see ...getContextForRecipient()}` docblock mention, no real crossing | **green — correctly**, no false positive |

⛔ **The last seven rows exist because a pre-merge audit defeated the first version of this work, and
they are the repair.** §8 records what each evasion was.

### 6.3 The census is the load-bearing test

`SigningReadersRefuseUnsentEnvelopeTest::every_crossing_of_the_recipient_read_port_is_classified_here`
derives the universe from the source tree and fails on any unclassified crossing. ⚑ **It caught its
own author**: `SigningTokenIssuance` was written in the same changeset, crosses the same port, and was
left out of the first draft because it is not a *reader*.

## 7. Open follow-ups (track, don't solve here)

- **`BL-87`** — the read half of the terminal direction, still open, posture still unanswered.
- **Pre-existing sessions over unsent envelopes keep a renewal window.** `/signing/session/renew` reads
  no envelope, so its exemption holds by construction only for sessions opened after this ships; a row
  created before it can keep exchanging a live refresh digest up to the 12-hour absolute cap. Bounded to
  a renewal oracle — every route that credential buys is guarded — and no backfill closes it. Deployment
  is pre-alpha, so the population is expected to be empty; **verify before assuming it is**.
- **The sender-side cross-BC read is attributed to the platform, not to the caller.**
  `SigningTokenIssuance` stamps `SystemActorId::boundedContext('Session')` while the controller already
  holds the authenticated principal, and that read returns the recipient's email, phone, name and access
  code hash. Latent: `issuedBy` is for audit-of-reads and the projector ([TASK-014](TASK-014-evidence-audit-projector.md))
  is not started. **It stops being latent the day it is**, and sender-initiated reads of recipient PII
  would be attributed to the platform rather than to the client that caused them.
- **§3.2's "one extra query" understates the mint's cost.** `getContextForRecipient()` projects down from
  the full-envelope read, so a send to N recipients now costs N full-envelope hydrations, on a route that
  carries no rate limiter. Tenant-authenticated, so the blast radius is bounded; the characterisation was
  simply wrong.
- **`BL-152` / `BL-158`** — the credential-invalidation mechanism the terminal direction needs.
- **`BL-184`** — the forge chain is broken at all three links by this task, but the row's underlying
  question (should a machine key need an entitlement) belongs to ADR-0044's authorization model.
- ⛔ **`CLAUDE.md` is owed one bullet, and it must land AT MERGE, not before.** Authoring rule 1 puts
  that file in the sweep and calls it the one surface that starts *instructing wrongly* — but in this
  workspace `f5sign-backend/CLAUDE.md` is a **symlink into the root repo's `ai/` store**, shared live
  by every worktree. Editing it from this branch would (a) cross a repo boundary the workspace rules
  forbid in one commit, and (b) tell the two other live sessions that a precondition is in force when
  it exists only here. It was written, seen to do exactly that, and reverted. **The text to apply once
  this merges**, appended to the `F5Sign/Session/` bullet. ⚠ Its link is written **root-relative**
  (`docs/adr/...`) on purpose — it resolves from `CLAUDE.md`, which lives at the repo root, and
  therefore does *not* resolve from this file. A link checker run over `docs/tasks/` will flag it;
  that is the checker being right about the wrong location, not a broken pointer to fix:

  > ⚑ **The whole ceremony also requires an envelope a recipient could already have read**
  > ([ADR-0058](docs/adr/ADR-0058-signature-requires-a-readable-envelope.md), amending ADR-0028):
  > asked as **`sentAt IS NOT NULL`** — never `status <> 'DRAFT'`, which re-opens the hole the day a
  > second pre-send status exists — at the sender-side mint (409 `ENVELOPE_NOT_SENT`), at the cross-BC
  > crossing the recipient routes share (404, indistinguishable from a wrong id), and in
  > `Envelope::recordRecipientCompletion()` (a throw among no-ops). ⛔ **The guard repeated at each
  > crossing is NOT duplication to tidy away**: the set is derived from the source tree by
  > `SigningReadersRefuseUnsentEnvelopeTest`, which fails naming any new crossing that does not
  > classify itself — enumerate from that test, not from this sentence.

  ⚑ **This is a general trap, not a quirk of this task**: any branch whose change alters what
  `CLAUDE.md` should say cannot land that edit with the branch, because the file is not in the branch.

## 8. Deviations & honest notes

- **The order of work was wrong, and it is recorded rather than smoothed over.** Implementation came
  first, tests second, the ADR and this record third. The repo's flow is spec → `spec-lint` →
  implement, and there was no task record when the first line was written. The decision itself was
  **not** invented afterwards — `ADR-0055` §2.8 took it on 2026-08-24 and said it owed a record and a
  task of its own — but the record owed should have come first anyway, because §2.4's audience split
  and §2.2's placement are exactly the kind of argument that belongs in a record before it belongs in
  a comment.
- **TDD was not followed; the sabotage pass was the compensation, and it was not merely ceremonial.**
  The bytes-path case was first written against a fixture whose recipient could reach no documents,
  asserting `null` — which is also what an empty document set returns. It passed with the guard
  reverted. It was moved beside the fixtures that can build an envelope whose bytes really would be
  served. **A test written after the code is a test that can be shaped by the code**, and this one was.
- **Two ADR-id collisions were avoided by re-deriving rather than trusting.** `ADR-0057` was handed
  over as the next free id and was already claimed on a sibling worktree branch; `ADR-0055` had been
  the same trap a day earlier. Both scans that produced the wrong number had covered refs but not
  sibling working trees.
- **Two characterisation tests were retired rather than repaired**, which is the disposition `BL-66`
  named for them in advance. ⚠ One of them **did not turn red** when the guard landed: the
  `SigningSessionReaderTest` option-less-`DROPDOWN` case described a *sent* envelope carrying a field a
  real `send()` would have refused, so it modelled a state that was never reachable and would have gone
  on passing forever.

## 9. What a five-lens audit found, after the gates were green

The user commissioned an adversarial audit of `687886d` — five parallel reviewers, each told to falsify
this record and the ADR rather than cite them. **None found an exploitable security defect or a domain
error.** The predicate, the monotonicity of `sentAt`, the guard ordering, the absence of a dead-lettering
interleaving, tenant isolation and the nine-route bypass sweep all came back verified. What did not
survive was **the apparatus built to watch the guards, and the prose written about them.**

Recorded here rather than smoothed away, because the pattern is more useful than the list.

### 9.1 The guards were sound; their input was not locked at all

Three of the five reviewers independently found the same thing, and it is the most serious finding in the
set. `GetEnvelopeContextForRecipientHandler` is the **sole** place `RecipientEnvelopeContextView::$sentAt`
is produced, every guard branches on it, and **no test in any tier asserted it**. Every guard test doubles
at the port, so all of them bypass that line.

The asymmetry is what makes it dangerous. Forcing `sentAt` to `null` breaks availability and a DB-backed
ceremony test would eventually catch it. Forcing it **non-null turns all five guards into no-ops**,
re-opening `BL-61` and `BL-66` in full — and **nothing at any tier noticed**: measured green at
`OK (882 tests, 2491 assertions)`, census included.

⚑ **The §6.2 sabotage pass is exactly what missed it**: it reverted each guard and never its input. That
is `CLAUDE.md` authoring rule 4 — *name where the property lives and check the harness goes there* —
applied to the guards and not to what feeds them. Closed, with both directions sabotage-verified.

### 9.1.1 …and the first attempt to size that gap was itself wrong, in the same way

Chasing it, this session claimed *"no integration test asserts `sentAt` anywhere"*, on the strength of
`rg -ln 'sentAt\(\)' tests/F5Sign/Envelope/Integration/`. **That grep searched for a method call and the
assertions are property reads** (`$view->sentAt`), so it could not have found them. It returned nothing
and the nothing was read as an answer.

The true picture, measured with a grep that can see both forms:

- **Read side: already covered**, in three places, including the draft/null direction
  (`DoctrineEnvelopeReadRepositoryTest`, `EnvelopeQueryAdapterTest`). The SQL hydration feeding the four
  Session guards was never the hole.
- **Write side: genuinely uncovered.** Nothing asserted that `Envelope::sentAt()` survives a round trip
  through `DbalEnvelopeRepository` — and that is the input to the write-half guard, reached from a
  reactor, which by construction always works on a cold-hydrated aggregate. Closed by
  `EnvelopeSendGuardHydrationTest::sent_at_survives_a_cold_reload_in_both_directions()`, beside the two
  cases already in that file for exactly this shape.
- **What `UnsentEnvelopeRefusedHttpTest` actually adds**, therefore, is narrower than first claimed and
  still real: it connects the hydration to the **guards' behaviour** over real HTTP, pins the wire
  contract (409 + `code`, and the 404), and is the only test of any tier over
  `MintSigningTokenController` since it swapped collaborators. Sabotage-verified: coalescing `sent_at`
  to non-null in the read repository turns it red with `Failed asserting that 201 is identical to 409` —
  the mint issuing a credential for a draft.

⚠ **Recorded because it is the audit's own lesson recurring inside the repair**: a tool that cannot see
the thing it is looking for returns silence, and silence reads as an all-clear. Two sessions made the
same mistake on the infra bind mount the same afternoon.

### 9.2 The census was defeated four ways in minutes

It asserted **one** property: that the set of classes calling `getContextForRecipient()` equalled a
hand-written list. The reviewers broke it by (a) adding a second, unguarded crossing to a class already on
the list; (b) pointing a map row at a test method that does not exist — so adding a row *was* the way to
pass, the exact opposite of what its docblock claimed; (c) a docblock `{@see}` mention, which reddened the
build while crossing nothing; and (d) a crossing in another BC, which its `Session/`-only universe could
not see. A fifth hole — a second `issueFor()` inside an already-classified minting class — was found by
re-sabotaging the *repair*. Now five properties, comments stripped with `token_get_all()`, counted per
callsite, every pointer resolved.

### 9.3 Three rotted reasons, repeated across thirteen sites

Authoring rule 2, three times over, and in each case the **conclusion survived while the stated reason did
not** — which is the shape that is hardest to catch by reading:

- *"a credential only the session open mints"* — false; there are **three** mint sites, and the route file
  itself labels the auth submit as the second one.
- *ADR-0045 §2.6* cited for *"nothing revokes"* — that section is about storing digests; the
  no-revocation decision is TASK-028 §4.3's, and the port's own docblock had it right.
- *"the three checks the port names as unenforced"* — named a different three, and one of the real three
  is still unenforced deliberately.

### 9.4 A measurement that was never measured

This record published `2321 / 11041` as a `develop` baseline. That pair is verbatim from
[ADR-0056](../adr/ADR-0056-terminal-state-on-pre-credential-routes.md)'s header — another branch, another
day — and the implied delta was arithmetically impossible. **Nothing was measured and the number looked
authoritative.** Removed rather than replaced; §1's own numbers are reproducible and are enough.

### 9.5 The register that would have sent the next engineer the wrong way

`docs/LOAD-BEARING.md` §1.8 argues from the premise *"a session only exists for a sent envelope — that is
false"*. **This task made it true**, and left the register saying the argument for deleting a live guard
was unsound when it had just become sound on its stated terms. That is precisely what §1.8 exists to
prevent, one level up. The same inverted premise sat in two more places in `src/`, one of them 520 lines
below a guard this changeset added to the same file — an **empty diff on a file that needed the edit**,
which is authoring rule 1's headline failure mode.

### 9.6 What this says about the order of work

§8 records that implementation came before the record. The audit is the bill for it. Every finding above
is something a reviewer reading a *specification* would have asked — where does the input come from, what
does the census actually assert, which mint sites exist, what is the baseline — and that reader did not
exist until the code was already written and the prose already committed to defending it. ⚠ The
mechanical steps still did the heavy lifting: sabotage found the decorative test, the census caught its own
author, and the audit's own perturbations found §9.1. **Prose review found the rotted reasons; nothing
mechanical could have.**
