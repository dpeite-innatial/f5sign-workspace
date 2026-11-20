# TASK-070 — A recipient reads their copy through a read-only link, for as long as it is kept

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/copy-link`** (`812fa7d2`), 2026-10-26. Gates under the `wt-backend` lane mounting this tree (`f5sign-backend-copy-link`), full gate on a fresh test database at `812fa7d2`: lint, deptrac, PHPStan and the whole suite green (8836 tests, 101261 assertions). Infection on this task's changed lines at `889a9e43` (the commits after it are a merge of the relay fix and prose): MSI 98 %, covered-MSI 99 %; the 10 mutants left are equivalent or unreachable, listed in §7. The full suite had failed `EventRelayEpochResetTest` until then: a relay defect this branch's extra tests exposed, fixed on `fix/relay-orders-by-transaction-id` ([BL-406](../BACKLOG.md)) and merged in. [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) is still `Proposed`: the owner accepts it. Not done here: the notices that carry the link, the production secret in `f5sign-infra`, the deferrals in §7. |
| **Type** | **Forward build** in Session, with enabling changes in Foundation (a credential kind, two `Authn` cases and their listeners, a second JWT codec) and one route in Evidence & Audit. It closes [BL-188](../BACKLOG.md). |
| **Why** | A recipient whose part has ended cannot get their copy back. The only link they can hold is the signing token, which expires after 7 days, and behind a declared access gate it is useless once their session is `COMPLETED`: ADR-0053 §2.3 refuses recovery there, so the gate cannot be passed again ([BL-188](../BACKLOG.md), parked 2026-08-24). The owner wants every notice that ends a recipient's part (the next record) to carry a link that opens their documents and their sealed receipt, by email and by SMS, for as long as the documents are kept. |
| **Builds on** | [ADR-0045](../adr/ADR-0045-issued-credential-format.md) (credential format), [ADR-0050](../adr/ADR-0050-session-credential-jwt-and-refresh.md) (the session JWT, whose shape the read credential mirrors under its own key), [ADR-0060](../adr/ADR-0060-retiring-a-credential-whose-holder-changed.md) and [ADR-0084](../adr/ADR-0084-a-correction-reaches-only-the-contact-it-changed.md) (retirement anchors), [ADR-0081](../adr/ADR-0081-each-gate-has-its-own-code-send-budget.md) (code-send budgets per gate), [ADR-0073](../adr/ADR-0073-step-policy-expiry-and-what-an-unagreed-envelope-keeps.md) §2.15–§2.16 (who reads what once an envelope closes; the ceiling). |
| **Scope** | The link, the gate passed again behind it, the reads it opens and the integrator's route to mint one. ⛔ **Not** the notices that carry it (the next record), and not the receipt itself ([TASK-047](TASK-047-per-signer-evidence-document.md)). |
| **Decision record** | **[ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md), `Accepted`** (2026-10-26, by the owner), drafted with this record (id swept over every ref and worktree on 2026-10-22; ADR-0087 is the highest, on `feat/early-document-seal`). It **lands in this task's changeset** (index, graph and crosswalk rows in `docs/adr/README.md`) and was accepted by the owner on 2026-10-26. It amends ADR-0045, ADR-0050, ADR-0053 §2.3, ADR-0073 §2.15 and ADR-0086 §2.6, and narrows ADR-0055 §2.15. Their amendment notes are written in this changeset, written while ADR-0088 was Proposed and updated at its acceptance, because the code that makes the old text false is on this branch (the repo's authoring rule 7); ADR-0086 §2.6 (*"only the machine route reaches a decliner's receipt"*) carries its note. |
| **Sibling** | ⚑ **[TASK-047](TASK-047-per-signer-evidence-document.md)** (**prerequisite**, merged into `develop`; ADR-0086 Accepted): the receipt and its registry. ⚑ [TASK-069](TASK-069-a-document-is-sealed-once-nobody-can-sign-it.md) (merged into `develop`; ADR-0087 Accepted): a document sealed before the close is served sealed here. ⚑ The per-recipient notices (not yet written): they mint this link; until they land, only the integrator's route mints one, and `SEALED_COPY_READY` keeps its 7-day signing token. ⚑ `f5sign-infra`: production must inject `COPY_READ_CREDENTIAL_SECRET` as it injects `SESSION_CREDENTIAL_SECRET` (a coordinated infra change, one repo per commit). |

<!-- OFFREPO: two outside surfaces are named here. (1) `f5sign-infra`, the workspace's infrastructure repository:
it injects the production secrets (as it injects `SESSION_CREDENTIAL_SECRET`) and provides the per-worktree test
lane; the fact this record needs is restated where it is used, and nothing here depends on reading it. (2) The
signer app (`f5sign-signer`), which builds the copy screen from the handoff this task writes in
`docs/frontend-handoff/`; the handoff is in this repository. TASK-047 and TASK-069, and their ADR-0086 and ADR-0087,
were on other branches when this record was written; both are now merged into `develop` and Accepted, so they are
read in this repository. -->

---

## 1. Why this task exists

Owner decisions, 2026-10-22:

- **A new credential, read-only.** It opens a recipient's documents and receipt and never admits an act.
- **If the sender declared an access gate, it is passed again** before anything is read. That is what BL-188
  lacked: the signing session is `COMPLETED` and refuses every gate.
- **It lasts as long as the documents are kept**: until the envelope's conservation ceiling.
- **A decliner's link opens only their receipt** (ADR-0073 §2.15: a decliner reads no document once the
  envelope closes).
- **The gate's codes live in a record of their own** per recipient; the completed signing session is not
  reopened.
- **Too many wrong codes lock the copy for a while, and it unlocks by itself**; the signing gate and the sender
  are not involved.
- **The integrator can mint a copy link** for its own delivery, as it can mint a signing token.

Owner decisions, 2026-10-23, after the claims check:

- **The lock's wait grows**: each window that ends locked doubles it, up to 24 hours, so the number of guesses stays
  bounded; it still unlocks by itself and never answers 423.
- **A delegated recipient is treated like every other**: signing elsewhere does not refuse a link.

Owner decision, 2026-10-26, after TASK-068 (ADR-0090) reached this branch: **the copy list publishes `signed_copy`**,
in the session read's vocabulary. Since ADR-0090 the copy serves nothing while a recipient's admitted act is being
applied, and without the field that empty list could not be told from a decliner's.

## 2. What already exists (reuse, do not rebuild)

**Credentials.** `Foundation/Credential/CredentialKind`: `API_KEY` (`ak`), `SESSION_REFRESH` (`sr`),
`SIGNING_TOKEN` (`st`); `bodyLength()` is a `match` with no default arm, and its docblock counts the `Authn` cases
that have a member. `IssuedCredential::mint()` builds `f5s_<kind>_<body><crc6>` and keeps only the SHA-256;
`parse()` checks length, trailer, marker, kind and body. A kind needs its OpenAPI pattern (as
`MintSigningTokenController`'s `^f5s_st_[A-Za-z0-9]{36}$`): `IssuedCredentialTest` iterates `CredentialKind::cases()`
and fails a kind with none; `CredentialKindTest` holds the entropy floor. `SensitiveDataRedactor` masks
`f5s_<x>_<16+>`.

**The signing-token store, the model for the link's.** `session.signing_token` (`token_digest` unique, RLS forced
with a digest-only policy, `REVOKE ALL` from the app role), written by the `SECURITY DEFINER`
`session.issue_signing_token(...)` and read by `session.resolve_signing_token(text)` (which returns `issued_at`,
for retirement) through `DbalSigningTokenDirectory`; `expires_at` is judged at the edge and purged by
`app:signing-token:purge`. `StoreBackedSigningTokenIssuer::LIFETIME` is `+7 days`. The raw
`Session/Contract/Service/SigningTokenIssuer` port carries no guard; TASK-036 put the guard in
`SigningTokenIssuance` (refuses an unclaimed slot, a recipient who signs elsewhere, a step not yet active), and
`NotifyCompletedEnvelopeRecipientsUseCase` calls the raw port with guards of its own.

**Authentication.** `Foundation/Actor/Authn`: `NONE`, `MACHINE_KEY`, `SIGNING_TOKEN`, `SESSION_CREDENTIAL`,
`SESSION_RENEWAL`. A route declares `_authn`; each listener acts only on its own case and returns early otherwise
(`SigningTokenListener`, `SessionCredentialListener`, `SessionRenewalListener`, `TenantRequestListener`), so a
case is accepted only where a route declares it. Session listeners set `_signing_envelope_id` and
`_signing_recipient_id`. `deptrac.yaml` lets Foundation depend on Kernel and Vendor only. Census: `AuthnTest`
iterates `Authn::cases()`; `tests/F5Sign/Foundation/Integration/RouteAuthnDeclarationTest.php` pins each route's case.

<!-- OFFREPO: `f5sign-infra` is the workspace's infrastructure repository; the fact needed (production injects
`SESSION_CREDENTIAL_SECRET` from its environment template and compose file) is restated here. -->
**The session JWT.** `SessionCredentialCodec`: HS256, `typ` `f5s-sc+jwt`, `aud` `f5sign:signing-session`, closed
claims `agp aud eid exp iat nbf rid tid` (pinned by `SessionCredentialCodecTest`), secret
`SESSION_CREDENTIAL_SECRET` (32-byte floor; absent from `.env`, a dev value in `.env.dev` and `.env.test`, injected
in production by `f5sign-infra`); callers set a 15-minute life.

**The access gate.** Challenges in `session.auth_challenge` and attempts in `session.auth_attempt`, held by
`SigningSession`. `IssueAuthChallengeUseCase`, `SubmitAuthResponseUseCase`, `OpenGateResolver` and
`EffectiveAuthMethodResolver` are keyed on `SigningSessionId` and refuse through `gatePasses` / `legIsOpen()`, which
refuse a decliner. `OpenGateResolver::openGateFor()` returns `null` for a terminal session (ADR-0053 §2.3,
ADR-0074). **Session-agnostic and reusable:** `OtpSendKeys::of(string $sessionId, AuthGate, …)`,
`FailOpenOtpSendLimiter` (per medium) and `OneTimeCodeRequest`; Notification picks `AUTH_OTP_ACCESS` for gate
`ACCESS` with no act. A hard lock is a Session fact, `AuthHardLockReached`, which Envelope turns into a recipient
lock that only the sender lifts (ADR-0049). An open access gate is the `DIRECT_LINK` declaration
(`RecipientAuthContext::accessGateIsOpen()`, ADR-0082).

**Reads after a part ends.** `SigningDocumentReader::read()` applies, in order: `withholdsDocumentFromRecipient()`
(unsent: withheld; open: not; closed: withheld unless signed or informational), `!recipientCouldPassTheGate()`,
retirement (`RecipientAuthContext::retires(credentialsRetiredAt, agp)`), `stepHoldsTheRecipientBack()`, and after
the close an unsealed document → `null`. A custody that was deleted or destroyed raises
`CustodyBytesUnavailableException`, answered 409. `RecipientView::hasSigned()` is `COMPLETED` **or** an admitted
`COMMIT` not yet landed. `SigningReadersRefuseUnsentEnvelopeTest` greps `src/` for callers of the recipient read
port and requires each to be classified on its unsent, terminal and step axes.

**Retention.** `Envelope/Contract/Query/ConservationCeilings::of(EnvelopeId)`:
`Result<DateTimeImmutable, EnvelopeNotFoundException|EnvelopeNotSentException>`, read under the tenant scope;
provisional until `COMPLETED`, re-resolved there (ADR-0073 §2.16). A custody's bytes can go **before** the
ceiling: `Custody::obligationEndsAt()` is the earlier of the ceiling and a customer deletion plus the bin grace
for a `PLATFORM_REVOCABLE` custody, which promotion uses.

**Retirement.** No retire action exists: three writers on the recipient move two anchors
(`Recipient::revokeInvitationsAt()`, `retireCredentialsAt()`), and each credential is judged against them at use
(`revokesInvitationIssuedAt`, `retires`). A contact correction and a dropped notification channel
(`changeNotificationChannels`, ADR-0084 §2.11) move both; they are refused on a closed leg and after the close
(ADR-0084 §2.3), and move the anchors only for a declared channel's destination (ADR-0084 §2.4, §2.11).
`Recipient::resetAccessCode()` moves `credentialsRetiredAt` only, and is legal after `COMPLETED` (ADR-0073: recovery
is never stricter than reading), so after the close it is the one writer that can retire a copy credential.

**The signer's recipient readers are keyed on the signing session.** `RecipientAuthContextReader::read()` takes a
`SigningSessionId` (used for its not-found refusal) and `EffectiveAuthMethodResolver` is keyed on the session; the
gate facts they read (declared methods, access-code hash, destinations, `authGeneration`) are not.

## 3. Scope

1. **The link.** A new `CredentialKind` `COPY_LINK` (`cl`), opaque, stored as a digest with its `issued_at` in
   `session.copy_link`, with RLS and `SECURITY DEFINER` issue and resolve functions, as the signing token is. No
   stored expiry.
2. **The mint, guarded at the port.** A service in `Session/Contract/Service` mints a link and refuses, inside
   itself (not one layer up, unlike `SigningTokenIssuer`), every recipient AC-14 refuses. The integrator's route and
   the next record's notices both call it.
3. **The edge.** `Authn::COPY_LINK` and its Foundation listener resolve the digest and set the envelope,
   recipient and issued-at attributes; `Authn::COPY_READ` and its listener verify the **copy read credential**: a
   JWT with its own codec, secret (`COPY_READ_CREDENTIAL_SECRET`), `typ`, `aud` and closed claims
   (`aud eid exp gpa iat nbf rid tid`, `gpa` the instant the gate was passed or the link opened), 15 minutes.
4. **Validity, in Session.** Every copy use case first reads `ConservationCeilings::of()` under the tenant scope
   and refuses when `now` is past the ceiling or the read errs; and refuses a link issued before the recipient's
   `invitationsRevokedAt`, or a read credential whose `gpa` is before `credentialsRetiredAt`. All of these answer
   the generic 401. The checks live in one Session service, exposed through a port in `Session/Contract/` so the
   receipt route (#6), which lives in Evidence & Audit, reaches them through its own Application layer rather than
   re-implementing them (`deptrac.yaml` lets `EvidenceAuditUI` depend on no other context's contract).
5. **The copy access record.** A new aggregate per (envelope, recipient) with its own challenges, attempts and a
   **temporary lock that grows**: `FAILURES_BEFORE_SOFT_LOCK` wrong codes lock it for
   `SOFT_LOCK_COOLDOWN_SECONDS`; each further window that ends locked doubles the wait, up to 24 hours; a passed gate
   resets it. It always unlocks by itself (owner, 2026-10-23). It reuses the signing gate's soft-tier constants
   (`Foundation/Auth/SignerAuthPolicy`) and `AuthGateCoolingDownException`, answered 429 `AUTH_COOLING_DOWN` with
   `Retry-After`, and **never reaches a hard lock**: the signing gate's escalation (423 `AUTH_HARD_LOCKED`, sender
   reset) lives in `SigningSession`'s private budget logic and is not copied. The growth is what bounds the guesses:
   `SignerAuthPolicy` names the cap on failures, not the code's entropy, as the defence (an access code may be a
   national id), and a fixed cooldown would allow about 1440 guesses a day until the ceiling; the doubling holds it
   to a few dozen on the first day and five a day after. New use cases issue and check its challenges, reusing
   `OtpSendKeys` (keyed on the record's own id), `FailOpenOtpSendLimiter` and `OneTimeCodeRequest`, and **not** the
   signing gate's `gatePasses` / `legIsOpen()`, which would refuse a decliner, nor the readers keyed on the signing
   session (§2): the copy gate reads the recipient's gate facts through a reader keyed on (envelope, recipient). No
   `AuthHardLockReached` is recorded, so the signing gate and the sender are not involved.
6. **Routes** (`config/routes/api/copy.php`, and one in `config/routes/api/evidence_audit.php`):
   - `POST /api/v1/copy/open` (`COPY_LINK`): an open access gate (`DIRECT_LINK`) → the read credential; a declared
     one → the gate descriptor.
   - `POST /api/v1/copy/auth/otp/send` and `POST /api/v1/copy/auth` (`COPY_LINK`): pass the gate; success → the
     read credential.
   - `GET /api/v1/copy` (`COPY_READ`): what this recipient may read (documents, where their own copy stands as
     `signed_copy`, and whether a receipt exists).
   - `GET /api/v1/copy/documents/{documentId}` (`COPY_READ`): the reader's rules below.
   - `GET /api/v1/copy/receipt` (`COPY_READ`), in `EvidenceAudit/UI/Http`, as TASK-047's session receipt route
     (ADR-0086 §2.6), so Session gains no dependency on Evidence & Audit; its ceiling and retirement checks go through
     #4's Session port. An informational member has no receipt.
   - `POST /api/v1/envelopes/{id}/recipients/{recipientId}/copy-links` (`MACHINE_KEY`): mint a link.
7. **The copy document reader** applies `withholdsDocumentFromRecipient()`; refuses a decliner every document,
   open or closed; applies the step and retirement guards; before the close serves the current tip, after it only a
   sealed document, at the tip of its sealed chain as the signing reader serves it; and lets a deleted or destroyed
   custody answer 409 as the signing reader does. Once the recipient's own commit is admitted, it serves nothing until
   their copy carries it, all or nothing (ADR-0090 §2.3, which closed [BL-462](../BACKLOG.md)): the copy shows what the
   signing reader would. New readers are classified
   in `SigningReadersRefuseUnsentEnvelopeTest`.
8. **Handoff.** `docs/frontend-handoff/` gains the signer app's copy screen (open, gate, list, download).
   <!-- OFFREPO: the signer app (`f5sign-signer`) builds the screen from this in-repo handoff; nothing here depends on it. -->
9. **Records.** ADR-0088; BL-188 closed by name; the `.env` header lists `COPY_READ_CREDENTIAL_SECRET` among the
   absent variables; the docblocks of `CredentialKind` and `Authn` that count their members.

<!-- OFFREPO: `f5sign-infra` is the workspace's infrastructure repository; what its change must do is restated in
§6 #4. -->
**Out:** the notices and `SEALED_COPY_READY`'s move to this link (the next record); a renewal route for the read
credential (a recipient opens the link again); the `f5sign-infra` change that injects the secret in production
(its own coordinated commit, §6 #4).

Concepts re-cut: *"a completed recipient cannot pass the access gate again"* (ADR-0053 §2.3, now: not for an
act); *"a decliner reads nothing once the envelope closes"* (ADR-0073 §2.15, now: their receipt);
`CredentialKind` (gains `COPY_LINK`); `Authn` (gains `COPY_LINK`, `COPY_READ`).

## 4. Key decisions

1. **Read-only by construction** (owner): the copy `Authn` cases are declared on copy routes only, and a listener
   acts only where its case is declared.
2. **Valid until the ceiling, checked at use, in Session** (owner): the ceiling is provisional until `COMPLETED`,
   so a stored expiry would be wrong; Foundation cannot read Envelope's contract, so the check runs in the use
   cases. A customer deletion can remove the bytes earlier; the link stays valid and the read answers 409.
3. **The gate is passed again where one was declared** (owner); the codes live in the copy access record (owner),
   so ADR-0074's rule that a terminal session answers no challenge stands.
4. **A temporary lock of its own** (owner): the copy record locks itself, for a period that doubles with each
   window that ends locked (owner, 2026-10-23), and unlocks by itself; no recipient lock, no sender unlock.
5. **A second JWT, not the session's**: neither is accepted where the other is.
6. **Retirement by anchors, as today**: the link's `issued_at` and the credential's `gpa` are compared with the
   recipient's anchors at use. A correction only reaches a recipient whose leg is open or who is informational; an
   access-code reset reaches a signer or an informational member, after the close included, and retires read
   credentials but not links.
7. **The receipt route lives in Evidence & Audit**, verifying the copy read credential through the Foundation seam.
8. **The integrator may mint** (owner), for its own tenant's recipients only, through the guarded service.

## 5. Verification

| Id | Criterion (an observable behaviour) | Origin | Tier / harness | Sabotage |
|---|---|---|---|---|
| AC-1 | A copy link or a copy read credential is refused by the signing, commit, decline and act-gate routes (members AC-1a, AC-1b) | owner | Acceptance | see *Notes on AC-1* |
| AC-2 | A link is accepted while `now` is before its envelope's conservation ceiling and refused after it, or when the ceiling read errs, with the generic 401 (members AC-2a…c) | owner | Application + Acceptance | skip the ceiling check |
| AC-3 | With a declared access gate the read credential is issued only after the gate is passed again; with `DIRECT_LINK` it is issued at `open` (members AC-3a…c) | owner | Acceptance | see *Notes on AC-3* |
| AC-4 | A decliner's credential reads the receipt and answers 404 for each document, the envelope open and closed (members AC-4a, AC-4b) | owner | Acceptance | serve documents to a decliner |
| AC-5 | Before the close a document read serves the current tip; after it only a sealed document, at the tip of its sealed chain, an unsealed one answering 404; a deleted custody answers 409 (members AC-5a…c) | owner | Application + Acceptance | serve the tip after the close |
| AC-6 | Each new route answers each documented code, each an `#[OA\Response]` (members AC-6a…g) | owner | Unit + Acceptance | see *Notes on AC-6* |
| AC-7 | The integrator mints a link for a recipient of its tenant; another tenant's envelope answers 404 | owner | Acceptance | drop the tenant scope |
| AC-8 | Passing the copy gate leaves the signing session, its challenges and its attempts unchanged | owner | Integration | write the challenge on the signing session |
| AC-9 | Too many wrong codes lock the copy record; each window that ends locked doubles the wait up to 24 hours, a passed gate resets it, and it always unlocks by itself; no `AuthHardLockReached` is recorded and the recipient is not locked (members AC-9a…c) | owner | Application | see *Notes on AC-9* |
| AC-10 | `COPY_LINK` credentials have their pattern, length and entropy, and the credential censuses cover the kind | derived — ADR-0045 | Unit | drop the pattern |
| AC-11 | The copy read credential has its own key, `typ`, `aud` and closed claim set; a session credential is refused on copy routes and a copy credential on session routes (members AC-11a…c) | derived — ADR-0050 | Unit + Acceptance | share the session key |
| AC-12 | A correction that moves the recipient's anchors refuses links issued and read credentials granted before it; an access-code reset refuses read credentials granted before it and leaves links valid (members AC-12a…c) | derived — ADR-0084 | Application | skip the anchor comparison |
| AC-13 | The link store resolves only by digest under RLS, and a link of one tenant opens nothing of another | derived — ADR-0071 | Integration | add a tenant-wide read policy |
| AC-14 | Who may be minted a link, over `RoleStanding` and the facts the reads use, failing on an unclassified member; the guard holds for every caller of the mint service (members AC-14a…k) | derived — authoring rule 5 | Unit (census) + Application | see *Notes on AC-14* |
| AC-15 | Copy gate sends are charged per medium and to the copy record's own session key per gate, never to the signing session's | derived — ADR-0081 | Application | key the send on the signing session id |
| AC-16 | `COPY_READ_CREDENTIAL_SECRET` is absent from `.env` and present in `.env.dev` and `.env.test`; the redactor masks `f5s_cl_` (members AC-16a, AC-16b) | derived — .env | Unit | commit a placeholder in `.env` |
| AC-17 | The new routes declare their `Authn` case, the new cases are in the `Authn` census, and the new recipient readers are classified (members AC-17a…c) | derived — tests/F5Sign/Foundation/Integration/RouteAuthnDeclarationTest.php | Unit + Integration | see *Notes on AC-17* |
| S-1 | A gated signer: link → code → list → sealed document → receipt | owner | Acceptance | — |
| S-2 | A decliner: link → receipt; a document answers 404 | owner | Acceptance | — |

<!-- OFFREPO: the `wt-backend` lane is a make target of `f5sign-infra`. It brings up this tree's own PHP container,
Postgres, MinIO and RabbitMQ, so storage and broker tests run against this checkout and not the main one. Nothing
in this record depends on reading that repository. -->
- **Gates:** suite, PHPStan, deptrac and lint, under the per-worktree lane (`wt-backend`) that mounts this tree.

**Notes on AC-1**
- AC-1a — a copy link on `POST /api/v1/signing/session`, `POST /api/v1/signing/commit`,
  `POST /api/v1/signing/decline` and `POST /api/v1/signing/session/auth` → 401.
- AC-1b — a copy read credential on the same routes and on `GET /api/v1/signing/session` → 401. Sabotage: declare
  `COPY_READ` on the commit route.

**Notes on AC-2**
- AC-2a — before the ceiling: accepted. AC-2b — past it: 401. AC-2c — the ceiling read errs: 401. Sabotage: admit
  on an error.

**Notes on AC-3**
- AC-3a — `DIRECT_LINK`: `open` answers the read credential.
- AC-3b — a declared OTP gate: `open` answers the descriptor; a code sent and submitted answers the read
  credential; a wrong code answers 401 and counts an attempt. Sabotage: issue the credential at `open`.
- AC-3c — a declared access code: submitted with method `ACCESS_CODE`, the same.

**Notes on AC-4**
- AC-4a — envelope open (a quorum step, the decline did not close it): documents 404, receipt 200. AC-4b — envelope
  closed: the same.

**Notes on AC-5**
- AC-5a — open: the current tip. AC-5b — closed, unsealed: 404; sealed: the tip of the sealed chain. AC-5c — a
  deleted custody: 409.

**Notes on AC-6**
- AC-6a `open`: 200, 401. AC-6b `auth/otp/send`: 202, 401, 429. AC-6c `auth`: 200, 401, 429 (`AUTH_COOLING_DOWN` with `Retry-After` while locked); never 423.
  AC-6d list: 200, 401. AC-6e document: 200, 401, 404, 409. AC-6f receipt: 200, 401, 404, 409
  `RECEIPT_NOT_READY`. AC-6g mint: 201, 400, 401, 404, 409 for a recipient AC-14 refuses. Sabotage: answer 500 for
  an unknown document.

**Notes on AC-9**
- AC-9a — the limit reached: the next submission answers 429 `AUTH_COOLING_DOWN` with `Retry-After` until the period
  ends, then is accepted; however many windows pass, it never answers 423.
- AC-9b — each further window that ends locked doubles `Retry-After` (300 s, 600 s, 1200 s, …) up to 24 hours,
  and a passed gate resets it to the first period. Sabotage: keep the period fixed.
- AC-9c — no `AuthHardLockReached` in the log, and the recipient's signing gate is not locked. Sabotage: record the
  hard-lock fact.

**Notes on AC-11**
- AC-11a closed claim set (an extra claim is refused). AC-11b a session credential on `GET /api/v1/copy` → 401.
  AC-11c a copy read credential on `GET /api/v1/signing/session` → 401.

**Notes on AC-12**
- AC-12a — an informational member's email corrected: a link issued before is refused at `open`. AC-12b — a read
  credential granted before is refused at the next read. AC-12c — a signer's access code reset after the close: a
  read credential granted before is refused at the next read; the link still opens, and the gate checks the new
  code.

**Notes on AC-14**
- Minted: AC-14a blocking, `COMPLETED`; AC-14b blocking, admitted `COMMIT` not yet landed (`hasSigned()`);
  AC-14c blocking, `DECLINED` (receipt only); AC-14d informational, any outcome, `RELEASED` included, whose step
  activated, or on an envelope that ended agreed whatever their step (on the step axis, ADR-0073 §2.15's
  `SEALED_COPY_READY` audience, which the next record moves to this link; unlike that notice today, delegated
  members included, AC-14e); AC-14e a recipient who signs elsewhere (`signs_via: MACHINE_KEY`), on the same terms as
  AC-14a…d: a blocking one who signed (no route lets a delegated recipient decline today), an informational one (owner, 2026-10-23: delegated recipients are
  treated like every other). They declare no access method, so their link opens with no gate.
- Refused: AC-14f blocking, `PENDING` with no admitted act; AC-14g blocking, `RELEASED`; AC-14h an unclaimed slot;
  AC-14i `NOT_BUILT` standing, and the `DELEGATED` / `SKIPPED` outcomes (never written; an outcome, not the
  `signs_via` of AC-14e); AC-14j an unsent envelope (as `SigningTokenIssuance` refuses one); AC-14k an informational
  member whose step never activated, while the envelope is open or once it ended not agreed (as
  `SigningTokenIssuance` refuses a step not yet active, and `NotifyCompletedEnvelopeRecipientsUseCase` skips one
  without agreement); on an envelope that ended agreed they are minted (AC-14d).
- Sabotage: move the guard to the integrator's controller, so the notices' call bypasses it.

**Notes on AC-16**
- AC-16a the variable's presence per file, as the repo's rule 4 on `.env` files requires (pattern (A): absent from
  `.env`, a dev value in `.env.dev` and `.env.test`). AC-16b the redactor on a `f5s_cl_` value.

**Notes on AC-17**
- AC-17a every route of `copy.php`, the receipt route and the mint route declare their case. AC-17b `AuthnTest`
  covers `COPY_LINK` and `COPY_READ`. AC-17c `SigningReadersRefuseUnsentEnvelopeTest` classifies each new reader on
  its unsent, terminal and step axes. Sabotage: leave one route undeclared.

## 6. Open follow-ups (track, don't solve here)

1. **The notices** (next record) mint this link through the guarded service, and `SEALED_COPY_READY` moves to it
   from the 7-day signing token.
2. **A renewal route for the read credential.** None: a recipient whose 15 minutes lapse opens the link again,
   which, behind a gate, costs another code.
3. **Copy links are never purged.** They lose validity at the ceiling; a sweep that deletes them after it is a
   storage tidy-up, not a security one.
4. **Production secret.** <!-- OFFREPO: `f5sign-infra` is the workspace's infrastructure repository; the fact needed
   (production injects `SESSION_CREDENTIAL_SECRET` from its environment template and compose file) is restated here. -->
   `f5sign-infra` must inject `COPY_READ_CREDENTIAL_SECRET` in its production environment
   template and compose file, as for `SESSION_CREDENTIAL_SECRET`, before this deploys: one PR in that repository,
   coordinated with this one.
5. **Credential-bearing responses carry no `no-store`.** The copy `open` and `auth` answers (a `read_credential`),
   the copy list and the receipt set none; the copy document route does. Tracked as [BL-472](../BACKLOG.md).
6. **A link holder can lock the real recipient out for up to 24 hours**, because the copy gate never hard-locks and
   `open` and `auth` have no per-source limiter. Declared in ADR-0088 §3.3; tracked as [BL-473](../BACKLOG.md).
7. **A copy link has no revocation of its own** and a second mint retires nothing. Declared in ADR-0088 §3.3;
   tracked as [BL-474](../BACKLOG.md).
8. **`GET /api/v1/copy/documents/{documentId}` serves the declared `Content-Type` inline with no `nosniff`.**
   Added to [BL-104](../BACKLOG.md) as an affected route; whatever closes that row covers it.
9. **The two copy reads disagree on a missing attribute** (400 on the document route, 401 on the list); both
   unreachable. Tracked as [BL-475](../BACKLOG.md).
10. **The production secret and the workspace store's absent-secret list** ([BL-476](../BACKLOG.md); item 4 above is
    its home).
11. **Closed by this task:** [BL-188](../BACKLOG.md), 2026-10-23, by the link, its gate and the reads.

## 7. Deviations & honest notes

### Scope
- None beyond the record's §3, with these additions it did not anticipate: `Authn::COPY_LINK` and `COPY_READ` came
  with two Foundation listeners and `CopyReadCredentialCodec`; the change reached 134 files (14 276 insertions),
  of which the amendment notes on ADR-0045, 0050, 0053, 0055, 0057, 0073, 0086 and 0090, `docs/LIVE_SCHEMA.md` and
  the README index are the records the code made false (authoring rules 1 and 7). `GET /api/v1/copy` publishes
  `signed_copy`, which §3 #6 now says; it was added on 2026-10-26 by the owner after ADR-0090 reached the branch.

### Decisions made during implementation
- One crossing class, `CopyRecipientContextReader`, carries the terminal and step axes and refuses an unsent
  envelope, so the reader census and its merge conflict are one slice; readers that do not cross it are pinned by
  behaviour.
- `RecipientAuthContextReader::fromView()` was extracted (a pure move) so the copy gate reads the gate facts by
  (envelope, recipient) instead of by signing session.
- Copy challenges exist only for delivered methods. An `ACCESS_CODE` answer is compared with the hash read at that
  submission and has no challenge. The submit body takes an optional `method`, resolved as `method`, else the live
  challenge's method, else the head.
- The lock is `300 × 2^(n−1)` seconds, `n` the windows that ended locked since the last pass, capped at 86 400 s.
  The sender's access-code reset does not clear it (only a passed gate does, as §3 #5 says); there is no
  `lockoutGeneration`.
- The copy access aggregate records no domain event and the copy use cases take no envelope command: a copy read
  leaves no fact on the log beyond the meter's billing record for a sent code.
- A decliner is `DECLINED` or an admitted `DECLINE`; they are minted a link (receipt only) and served no document.
- `CopyLinkRefusal` is a Contract enum whose values are the problem codes; one new code, `RECIPIENT_HOLDS_NO_COPY`,
  covers a blocking member who has not acted or was released, a `NOT_BUILT` role and the outcomes nothing writes.
  The 409 text is kept as is: when something starts writing `DELEGATED` or `SKIPPED`, that change owns the string.
- The mint guard lives in `CopyLinkIssuance`, the implementation of the Contract port `CopyLinkIssuer`; the raw
  `CopyLinkStore` is an Application port, unreachable from other contexts by deptrac.
- `copy_link` reuses the `f5sign_signing_token_custodian` role (roles are created outside migrations) and has its
  own GUC, `app.presented_copy_link_digest`; request attributes are `_copy_*`, distinct from `_signing_*`.
- `has_receipt` means a receipt is owed, read from Session's own status and never from Evidence & Audit.
- After TASK-068 (ADR-0090) the copy readers adopt `SignedCopy::of()`/`isReady()` all or nothing (slice 16a), and
  `CopyLinkEligibility::declined()` reads `RecipientView::outcomeAsAdmitted()`. Agreement with the signing download
  is pinned by `CopyReaderShowsWhatTheSigningReaderWouldTest`.
- The copy list publishes `signed_copy` (owner, 2026-10-26; slice 16b), so a decliner's empty list can be told from
  one waiting for the act to land.
- `DownloadCopyDocumentController` answers 400 for a missing listener attribute, as its signing sibling does;
  `GetCopyController` answers 401, since it publishes only 200 and 401. Each answers what it publishes; neither is
  reachable ([BL-475](../BACKLOG.md)).
- Security audit: no code change; each of its six warnings mirrors a sibling and is tracked in §6.

### Decisions that needed an ADR
- [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md), drafted `Proposed` with this record
  (2026-10-22); the owner's two additions of 2026-10-23 are in it. The owner moved it to Accepted on
  2026-10-26; the artifacts that exercise it are listed in ADR-0088 §5 and §6.

### Declared and unproven properties
- **Infection** (diff-scoped, `889a9e43`, `EventRelayEpochResetTest` excluded from the initial suite until the
  relay fix landed): 733 mutants, 723 killed, 7 escaped, 3 not covered; MSI 98 %, covered-MSI 99 %. A first run
  (82d97acd) had MSI 64.67 %: the copy controllers were reached only through Acceptance tests, which the
  diff-scoped selection does not pick; fix slices 20a and 20b added unit tests per controller and per mutant, and
  moved `@infection-ignore-all` before `security`/`parameters`/`responses` where a test pins them, as the receipt
  routes do. The 10 left, each equivalent or unreachable, each checked by a manual sabotage that stayed green or by
  the type system:
  - `CopyReadCredentialCodec:129` ReturnRemoval — an empty string reaches the parser, which throws and is caught to `null` anyway.
  - `IssueCopyChallengeUseCase:131` Throw_ — a gate that is not open always has a head method.
  - `CopyAccess:198` GreaterThan (`>=`) — two equal instants are the same value.
  - `DbalCopyAccessRepository:262` LogicalAnd — `AuthChallenge` already forces a SIGNING gate to carry an act.
  - `DbalCopyAccessRepository:113`, `:148`, `:161` (not covered) — unreachable: PHPStan level 9 rejects another id or aggregate type, and the insert of the same id ran in the same transaction.
  - `DownloadCopyDocumentController:114` MethodCallRemoval (`setPrivate()`) — after `no-store` Symfony adds `private` itself; the headers are identical.
  - `OpenCopyController:187`, `:210` null-safe calls — the access-gate descriptor is built only when the gate declares methods, so its head is never null.
  - Three catch-then-throw mutants in the copy use cases are killed only by PHP's undefined-variable warning under `failOnWarning`; the null guard below them refuses identically.
- **`EventRelayEpochResetTest`** failed at volume in every full run of this branch (142, 164, 166, 206 deliveries
  against 120) and in no filtered one. Diagnosis: the relay ordered each slice by the text of the transaction id,
  so a slice straddling 10000 repeated facts; this branch's added tests moved the counter across 10000 during
  that test. Fixed on `fix/relay-orders-by-transaction-id` (owner, 2026-10-26), merged here; the full suite is
  green with it.
- **Not reached by any harness here:** the production secret (outside the repository, [BL-476](../BACKLOG.md)).
- AC-6b's 401 and 429 are pinned by unit tests and not driven over HTTP.

### Debt left behind, and where it lives now
- Notices that mint the link, and `SEALED_COPY_READY` moving to it: §6 #1 (the next record).
- No renewal route for the read credential: §6 #2. Links never purged: §6 #3.
- Production secret and the workspace store list: §6 #4, [BL-476](../BACKLOG.md).
- `no-store` on credential-bearing responses: [BL-472](../BACKLOG.md). Lock-out by a link holder:
  [BL-473](../BACKLOG.md). No per-link revocation: [BL-474](../BACKLOG.md). Both are risk lines in ADR-0088 §3.3.
- The copy document route's `Content-Type` and `nosniff`: [BL-104](../BACKLOG.md), extended.
- `source_ip` and `user_agent` of a copy attempt stored in clear: [BL-171](../BACKLOG.md), noted.
- The 400 against 401 disagreement: [BL-475](../BACKLOG.md).
- `EventRelayEpochResetTest`: [BL-406](../BACKLOG.md), diagnosed and fixed on its own branch.
- Three copies of the context-and-admission step (`CopyDocumentReader`, `CopyContentsReader`,
  `CopyAdmission::admits`) are identical today; a single home on `CopyAdmission` removes a drift risk and is
  optional. `READ_CREDENTIAL_LIFE` is duplicated in two controllers. Neither is a defect, and neither has a row.

### Delegated work
- 20 implementer runs over slices 01 to 18 (with 16a and 16b): 17 critical on `opus`, 3 standard on `sonnet`
  (14, 16 and 18); 36 rounds in all. Every slice report's `## Delegated` says none: no replication target reached
  three, so the `replicator` was not used.
- Slice 15 returned NEEDS_CONTEXT once (the `ProblemCoded` census shape). The amend cap was reached after 16a, so
  the orchestrator wrote 16b. The closing sweep ran as 19a and 19b with two review rounds.

### Cost of the run
- Implementers (tokens as logged): `opus` 3 081 593 over 17 runs and 32 rounds; `sonnet` 460 319 over 3 runs and 4
  rounds; total 3 541 912.
- Reviews, the closing review, the gates and the sweep are not in the run log's token counts.
- Escalations: one NEEDS_CONTEXT (slice 15); one amend (16a, after TASK-068) and one owner-driven slice (16b).
- Full-suite runs: `4a40b8b9` green (8444 tests); `596208bd`, `82d97acd` (twice) red on the relay defect;
  `812fa7d2` green (8836 tests).
- Infection: two runs; the first below the MSI bar (64.67 %), fixed by slices 20a/20b; the second 98 % / 99 %.
