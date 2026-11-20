# TASK-003 — Cross-BC ACL realization (mirror drain, both directions)

| Field | Value |
|-------|-------|
| **Status** | **Landed 2026-06-11** — substrate green: PHPStan L9, Deptrac **0**, full suite on **both** write adapters (96 tests). `EntityReference` kernel category + `ExecutionRef`/`Target*Ref` mirrors + ORM-mismatch fix; ADR-0004 → Accepted, ADR-0020 minted, ADR-0007 corrected; `DEC-XBC-1` marked substrate-discharged (`DECISIONS.md` retained, design-repo cascade deferred). All §4 decisions resolved. |
| **Type** | Agent-delegable implementation task **+ discharge sweep** (closes a legacy line) |
| **Exercises** | [ADR-0004](../adr/ADR-0004-cross-bc-anti-corruption-layer.md) (strict Anti-Corruption Layer) — flips it **Proposed → Accepted** |
| **Introduces** | a new kernel category `EntityReference` (§4.3 / §5.0) — reference-to-foreign identity, sibling of `EntityId` — documented by new **ADR-0020**; cross-links + corrects [ADR-0007](../adr/ADR-0007-kernel-identity-discipline.md) |
| **Closes** | legacy `DEC-XBC-1` **substrate** — the `DECISIONS.md` entry is **retained, marked substrate-discharged** (deletion deferred to the design-repo doc cascade, per that file's delete-after-cascade protocol). `DI-6`/`F8`/`F19` resolved in substrate; their design-repo close-notes deferred. |
| **Delivery bar** | Green `make qa` via the infra Makefile with **Deptrac at 0 cross-BC violations**, against **both** Envelope write adapters (ORM + DBAL) |

---

## 1. Why this task exists

ADR-0004 locked the strict ACL rule (Domain/Contract speak own-BC vocabulary only; cross-BC translation lives in the adapter layers) but it is **Proposed — unexercised**: Deptrac stands red and no enforcement bar is green. `DEC-XBC-1` is the last live `DECISIONS.md` entry; discharging its substrate is what flips ADR-0004 to Accepted. (The file itself is *kept* — its delete-after-cascade protocol means the entry persists, marked discharged, until the deferred design-repo doc cascade lands.)

**A Deptrac misconfig was masking half the problem.** `deptrac.yaml` line 214 lets `SignatureExecutionContract` import `EnvelopeContract` — the lone non-strict Contract ruleset (every other BC's Contract = Kernel + Foundation only). It **hides 3 real SE→Envelope violations** in `SignatureExecution/Contract/Event/DocumentSigned` (imports `EnvelopeId`/`DocumentId`/`RecipientId`). So ADR-0004's recorded "**0 SE→Envelope violations**" is a tooling artifact, not reality: **the true count is 14** — **11** Envelope→SE (surfaced; ADR-0004 said 10, but `Recipient` carries 4 edges not 3) + **3** SE→Envelope (masked). Closing the line honestly = the **full bidirectional** refactor + the misconfig fix. ADR-0004's "Realized in" gets corrected as part of the sweep (the rule was *half-unenforced*).

## 2. What already exists (reuse, do not rebuild)

- **The rule is fully specified** — ADR-0004 + `DECISIONS.md DEC-XBC-1` (9 sub-questions, pressure-test cases, mirror-minting convention, the bidirectional refactor plan).
- **Read side + error channel are already ACL-correct** — `Contract/View/RecipientView` projects `signedExecutionId` as raw `?string`; `EnvelopeQueryAdapter` throws the published `Contract\Exception\EnvelopeNotFoundException` (ADR-0008). Don't touch.
- **Persistence already stores plain strings.** Both write adapters — `DoctrineEnvelopeRepository` (ORM) and `DbalEnvelopeRepository` (DBAL) — round-trip `signed_execution_id` as a 36-char string (no `SignatureExecutionId` import). So this is an **in-memory type + reconstitution** change, **not a column/migration change**.
- **Import sites (the 14 edges):**
  - Envelope→SE (11, surfaced): `Contract/Event/RecipientCompleted` (field, 1) · `Contract/Type/ProducedBy` (field + `sign`/`seal`/`extension` + `fromString`, 5) · `Domain/Aggregate/Envelope` (param, 1) · `Domain/Entity/Recipient` (field + getter + `markCompleted` + rehydrate, 4).
  - SE→Envelope (3, masked): `SignatureExecution/Contract/Event/DocumentSigned` (`EnvelopeId`/`DocumentId`/`RecipientId`).
  - Translation seams (adapter layers — already allowed to import cross-BC Contract): `Application/Command/Lifecycle/RecordRecipientCompletion` handler (Envelope) · `SignatureExecution/Application` `MockSign*` (SE) · Envelope's `OnDocumentSigned` reactor.

## 3. Scope

**In:** the **`EntityReference` kernel category** (§5.0 — interface + base + `KernelFqcn` + one `KernelGenericBoundRule` ladder rung) · Envelope mirror (1) + its Doctrine Type (fixes the latent ORM mismatch) · SE mirrors (3, **transient** — only in the `DocumentSigned` payload) · the Deptrac misconfig fix (line 214) · the translation seams · drive Deptrac **14 → 0** · flip ADR-0004 → Accepted + mint **ADR-0020** (the new category) + cross-link/correct ADR-0007 · mark `DEC-XBC-1` substrate-discharged (entry **retained**) + re-home stale in-repo `DECISIONS.md` links to their ADRs (code-repo cascade; design-repo cascade deferred).

**Out (deferred — not required to close the line):**
- The **design-repo prose cascade** (`foundations-grounding §6`/§8, `platform-foundations §2.18`, `code-conventions`, `COMMITMENTS CMT-XBC-*`) — *docs remain pending* per the directional commitment (ADRs are canonical; design docs are why-history).
- **`ContractSurfaceKernelGroundedRule`** (DI-31) — a *separate* §6-grounding PHPStan rule; lands under its own line.
- **SE Doctrine Types** for the 3 SE mirrors — SE has no real persistence yet; the mirrors are transient.
- **DI-38** (`BoundedContextId` placement) — separable.

## 4. Design decisions to resolve first (pressure-test before cutting)

1. **Mirror name — RESOLVED 2026-06-11: `ExecutionRef`.** Grounded in Envelope's UL, not a default lean. The referenced SE aggregate identifies *all three* crypto acts SE executes — signing, sealing, preservation-extension — and Envelope's own spec already names each reference `…ExecutionId` (`Recipient.signedExecutionId`, `Envelope.recordSealingCompleted($sealingExecutionId)`, `ProducedBy.executionId` across SIGN/SEAL/EXTENSION; see [envelope.md §3.4 / §11](../../../../Arquitectura/DDD/tech/envelope.md)). So "execution" *is* Envelope's established term for the foreign act, and it's the only candidate covering all three reference roles. Rejected: **`SignatureRef`** (seal + extension aren't "signing" in Envelope's UL — sealing is its own `READY_TO_SEAL→SEALING→COMPLETED` lifecycle); **`CompletionSourceRef` / `ExternalProductionRef`** (role-specific, can't span sign-completion + artifact-production + seal-completion); **`SignatureExecutionRef`** (re-imports SE's type name). ACL autonomy is satisfied *structurally* — own type, no import; SE may rename `SignatureExecutionId` freely without rebinding `ExecutionRef`. SE-side mirrors: `TargetEnvelopeRef`/`TargetDocumentRef`/`TargetRecipientRef`. (Distinct from the kernel category name `EntityReference`, §4.3 — the type these mirrors extend.)
2. **Scope of the Envelope change — RESOLVED 2026-06-11: include the ORM-mismatch fix.** The mirror needs a `Doctrine<Mirror>Type` anyway (confirmed: `Recipient.orm.xml` (ORM mapping, removed with the DBAL-only adoption — ADR-0018) mapped `signedExecutionId` `type="string"` against a `?SignatureExecutionId` *object* property — latent because no test reconstitutes a completed recipient through the ORM adapter; the DBAL path sidesteps it by calling `->toString()` manually). The custom Type fixes the mismatch for free.
3. **`generate()` semantics — RESOLVED 2026-06-11: new `EntityReference` kernel category (§5.0).** A mirror needs *typed identity* but explicitly *not* mintability: a reference-to-foreign is received via `fromString()`, never minted. The root tension is that [`EntityId`](../../src/F5Sign/Kernel/Identity/EntityId.php) fuses two commitments — typed-identity-with-equality **and** client-mintability (`generate()`, grounded in the mint-Subject-before-the-aggregate semantics) — and a mirror wants the first while rejecting the second. (`EntityIdHasGenerateMethodRule` only checks `generate()` *exists + is static* — the "real mint, not a throws-stub" wording was ADR-0007 *prose*, never enforced; a throws-stub would have passed but encodes the tension as a runtime landmine.) **Decision: split the contract along its seam.** Mint a sibling category `EntityReference extends ValueObject, Stringable` — **not `Subject`** (a reference is never what a fact is *about*: every `subject()` in the codebase returns an own-BC `EntityId`; Command/DomainEvent narrow `subject()` to `EntityId`, Event/Query require `Subject`, so a reference is structurally barred from *any* subject position). Mirrors `extends StringEntityReference implements EntityReference`: **no `generate()`** (the rule keys on `EntityId`, which a reference is not — fires zero), every other VO shape-rule auto-covers via the `ValueObject` chain. Formalizes ADR-0007's "separate category, reference-to-foreign" line as a real type; its "real mint" claim then holds honestly for *every* `EntityId`. Applies to all 4 mirrors.

**Step zero — base / sequencing.** Settle the DBAL disposition so this lands on a stable base: **park the `config/services.yaml` alias on the ORM adapter**, commit the ADR-0019 work and the DBAL experiment as **separate clean units**, then do this task on top. Both adapters stay green throughout this task.

## 5. Deliverables

### 5.0 Kernel category — `EntityReference` (gates §5.1–§5.2; land first)
- Mint `Kernel/Identity/EntityReference` — `interface EntityReference extends ValueObject, Stringable` with `@template T` (mirrors `EntityId`'s shape minus `Subject`); docblock states *reference-to-foreign, received-not-minted, never a fact's subject*, and disambiguates from Doctrine's `EntityManager::getReference()`.
- Mint `Kernel/Identity/StringEntityReference` — `abstract readonly`, body mirrors [`StringEntityId`](../../src/F5Sign/Kernel/Identity/StringEntityId.php) (`protected string $value`, `toString()`/`__toString()`, `equals()` via `instanceof static`) but binds `EntityReference`, not `EntityId`. **Detached** — no shared `StringValue` base yet (rule-of-three defers extraction).
- `KernelFqcn`: add `ENTITY_REFERENCE` + `STRING_ENTITY_REFERENCE`. [`KernelGenericBoundRule`](../../phpstan/src/Rules/KernelGenericBoundRule.php): add one `EntityReference` rung to the ladder (clean self-binding error label). **`EntityIdHasGenerateMethodRule`: no change** — a reference is not an `EntityId`, so it never fires; the `final readonly` / factory-naming / generic-bound / composite-shape rules auto-cover via the `ValueObject` chain.
- Add a rule test + `phpstan/README.md` entry if a ladder rung is added (per the sibling-test convention).

### 5.1 Envelope mirror + persistence
- Mint the mirror in `Envelope/Contract/Type/` (it appears in the published `RecipientCompleted` payload): `final readonly class <Mirror> extends StringEntityReference implements EntityReference` (§5.0), `fromString()` public, **no `generate()`**.
- `Infrastructure/Persistence/Doctrine/Type/Doctrine<Mirror>Type` + registration; update `Recipient`'s ORM mapping (string → custom type). Schema column unchanged (stays `uuid`/string).

### 5.2 SE mirrors (transient)
- Mint `TargetEnvelopeRef` / `TargetDocumentRef` / `TargetRecipientRef` in `SignatureExecution/Contract/Type/` (published in `DocumentSigned`). `StringEntityReference`-shaped (§5.0); **no `generate()`**. **No Doctrine Types** (not persisted).

### 5.3 Refactors
- Envelope: the 4 import-site files → mirror; drop `SignatureExecutionId` imports.
- SE: `DocumentSigned` payload → SE mirrors; drop Envelope imports. `MockSign*` (Application) translates inbound Envelope IDs → SE mirrors at construction.
- Translation seams: `RecordRecipientCompletion` handler adapts inbound `SignatureExecutionId` → Envelope mirror before invoking Domain; Envelope's `OnDocumentSigned` reactor translates SE mirrors → Envelope's typed IDs before dispatching `RecordRecipientCompletion`.

### 5.4 Deptrac
- **Remove line 214** (`EnvelopeContract` from `SignatureExecutionContract`); confirm no other cross-BC entry sits in any `*Contract` or `*Domain` ruleset (all others verified strict). Run → **0 violations**. (Expect it to surface 11→14 the moment the misconfig is removed, *before* the refactor lands them at 0.)

### 5.5 Discharge sweep
- **Mint [ADR-0020](../adr/ADR-0020-entity-reference-kernel-category.md)** — the `EntityReference` kernel category (reference-to-foreign identity; `extends ValueObject, Stringable`, **not `Subject`**; no `generate()`; sibling of `EntityId`). Relate to **ADR-0004** (its consumer — mirrors realize this category) and **ADR-0007** (formalizes ADR-0007's "separate category, reference-to-foreign" line into a real type). Add to [`docs/adr/README.md`](../adr/README.md) index + relationship graph + crosswalk.
- **Correct ADR-0007** — cross-link ADR-0020; its "Enforced by" claim that `EntityIdHasGenerateMethodRule` enforces "a real mint, not a throws-stub" becomes honest *because* mirrors are now `EntityReference`, not `EntityId` (no throws-stub lives on any `EntityId`). Note the rule-vs-prose gap is resolved by category split, not by hardening the rule.
- ADR-0004 **Proposed → Accepted**; correct its "Realized in" (the masked-violation finding; true count was **14** = 11 Envelope→SE + 3 SE→Envelope; both directions mirrored).
- **Keep `DECISIONS.md`; mark `DEC-XBC-1` substrate-discharged** (authoritative home → ADR-0004 + ADR-0020; only the design-repo doc cascade remains, deferred). The file is retained per its delete-after-cascade protocol — deletion now would dangle ~14 design-repo + in-repo links that point to it for *other* drained `DEC-*`.
- **Code-repo cascade (in-scope):** re-home the stale `../../../DECISIONS.md` links in `phpstan/README.md` + `phpstan/AUTHORING.md` to their ADR homes (DEC-CH-1→0001, DEC-SUB-1→0002, DEC-VO-1→0005, DEC-STEP-1→0006, DEC-KID-1→0007, DEC-XBC-1→0004); update ADR-0004 Crosswalk + `docs/adr/README` crosswalk. This also restores the ADR-set detachment principle (no in-repo `→ ../../../DECISIONS.md` links).
- **Design-repo cascade (deferred, §9):** `conventions.md §6` XBC-1 entry, `DI-6`/`F8`/`F19` close-notes, `foundations-grounding §6`, `platform-foundations §2.18`, `COMMITMENTS CMT-XBC-*`, and the eventual `DECISIONS.md` deletion — left for the doc-cascade pass.

## 6. Acceptance criteria (properties)

- **P-ACL.1** — `make qa` green: PHPStan L9 + lint + full suite, **with the alias flipped to each adapter in turn** (ORM and DBAL both green).
- **P-ACL.2** — Deptrac reports **0** violations; no `*Domain` or `*Contract` ruleset imports another BC.
- **P-ACL.3** — no `F5Sign\<OtherBC>` import survives in any BC's `Domain/` or `Contract/` (grep-clean, both directions).
- **P-ACL.4** — the cross-BC seams round-trip by **string equality**: an SE execution id entering at `RecordRecipientCompletion` reconstitutes as the Envelope mirror with the same `toString()`; the `OnDocumentSigned` reactor maps SE mirrors → Envelope IDs preserving string value (a focused adapter-translation test).
- **P-ACL.5** — `Recipient` persists + reconstitutes the mirror identically through **both** adapters (the ORM mismatch is gone).

## 7. Constraints

- **No schema/migration change** — `signed_execution_id` stays a string column; the change is PHP-side type + Doctrine Type.
- **Both adapters stay green** at every step (don't fix one path by breaking the other).
- **No design-repo edits** — the prose cascade is deferred (docs pending); this task touches only `prototype/f5sign-backend/` + the legacy trackers it retires.
- §4 fully resolved — land **§5.0 (the `EntityReference` category) first**; it gates all four mirrors.

## 8. Definition of done

Green `make qa` (Deptrac **0**, both adapters) · `EntityReference` kernel category landed (§5.0) · **ADR-0020 minted** + ADR-0007 cross-linked/corrected · ADR-0004 **Accepted** + corrected · `DEC-XBC-1` marked substrate-discharged (`DECISIONS.md` **retained**; design-repo cascade + deletion deferred) · stale in-repo `DECISIONS.md` links re-homed to ADRs · touched-file hygiene pass before commit.

## 9. Follow-ups (still out of scope)

- Design-repo prose cascade (`foundations-grounding`/`platform-foundations §2.18`/`code-conventions`/`COMMITMENTS CMT-XBC-*`) — docs-pending.
- `ContractSurfaceKernelGroundedRule` (DI-31) — separate grounding-rule line.
- SE mirror Doctrine Types — when SE gains real persistence.
- DI-38 (`BoundedContextId` placement).
- The ADR-0019 implementation to-dos (separate from this task).
