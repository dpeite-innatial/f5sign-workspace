---
name: eidas-compliance
description: 'Validates eIDAS compliance for what this backend does TODAY: server-side PAdES B-B sealing via EU DSS 6.4, digests from a closed enum (SHA-256/384/512), and the properties measured against the live DSS (coordinate origin, one widget = one incremental signature). Does NOT validate TSA, LTV, trust lists or per-user certificates: none of that exists in the repo, and pretending to check it is worse than not checking it. Binding decisions: ADR-0023, ADR-0034, ADR-0016 and docs/tasks/TASK-005|006|017|018. Use it with /eidas-compliance TASK-NNN. Trigger with "eIDAS compliance", "review signature", "validate PAdES", "check EU DSS".'
---

# eIDAS Compliance (what exists)

Invoked by `security-audit-core` when **the diff touches signing or crypto** —
`src/F5Sign/SignatureExecution/`, `Foundation/Crypto/`, DSS, PAdES. This task format has no tags: the
condition is the diff, and it's evaluated by whoever delegates.

> ⚑ **This skill was trimmed down on 2026-08-17 after an audit.** It used to cover TSA, LTV, LOTL/TSL
> trust lists, per-user certificates and the XAdES/CAdES/JAdES formats. **None of them has a target in
> this repo**: zero references to LOTL/TSL, zero OCSP/CRL, `requiresTsa()` with not a single caller in
> `src/`, no per-user certificate or policy OID, and a single level enum whose four cases are all
> `PAdES_BASELINE_*`. Those steps used to return **green by vacuity on every diff**, which is the most
> expensive way to fake coverage. What was removed isn't lost: it lives in ADR-0023's *Consequences*
> (B-B breadth, the rest deferred) and in `BL-4`.

## Invocation

```
/eidas-compliance TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` and the task's `.md`
- The binding decisions, **in the repo**:
  [`ADR-0023`](../../../docs/adr/ADR-0023-dss-server-signing-seal-flow.md) (server-side sealing with
  DSS), [`ADR-0034`](../../../docs/adr/ADR-0034-sequential-incremental-pades.md) (sequential
  incremental PAdES and visible marks), [`ADR-0016`](../../../docs/adr/ADR-0016-storage-model.md)
  (WORM + object-lock), and `docs/tasks/TASK-005`, `TASK-006`,
  [`TASK-017`](../../../docs/tasks/TASK-017-sequential-incremental-pades.md), `TASK-018`
  <!-- OFFREPO: the original "12 decisions" list (`project_cloud_signing_decisions.md`) and the EU DSS
  integration guide live in the design repo and are NOT reachable from a backend checkout. Everything
  still in force is restated in the ADRs above. If a check needs a decision that isn't in any of them,
  **the finding is that absence** (`decision-homeless`), not a divergence. -->

## Execution

### Step 1 — Signature level: **B-B is the decision, not a gap**

- [ ] The code produces `SignatureLevel::PADES_B_B`. ⛔ **Don't ask for B-T/B-LT/B-LTA.** ADR-0023
      §Consequences: *"the seal-level breadth is **B-B only**; B-T/B-LT/B-LTA … are deferred"*, filed
      as `BL-4`. A diff that **raises** the level is a decision (ADR), not a silent improvement; one
      that stays at B-B is conformant. ⚠ The only text that says "B-LT by default" is
      `docs/ddd/signature-execution-domain-model.md`, and there it describes the **target model**: it's
      not today's bar.

### Step 2 — Digests: the enum already closes the door

- [ ] Digests come from a **closed** enum `{SHA256, SHA384, SHA512}` (`DigestAlgorithm`), whose
      docblock says SHA-1 and MD5 are omitted per eIDAS policy. In other words: they're
      **unrepresentable**, and looking for them is looking for what the type already forbids. The
      real check is that **nothing introduces a digest via a raw string**, sidestepping the enum.
- [ ] Keys and curves are **not** chosen here: DSS resolves them from its keystore **by alias**. No
      key size or curve appears in `src/`, so don't report it as an omission.

### Step 3 — Format: PAdES only, and say so

- [ ] The only format with a code path is **PAdES**. There's no XAdES, CAdES or JAdES, nor any XML or
      JSON signing surface. If the diff introduces one, **it's an ADR** (a new format is a product and
      compliance decision), not an extension.

### Step 4 — The properties measured against the live DSS

Restated in [`TASK-018`](../../../docs/tasks/TASK-018-visible-signature-mark.md) §1; use them from
there and, if re-measured, **add a dated line** instead of editing the old one.

- [ ] **The coordinate origin is top-left**, with `originY` growing downward — opposite to the PDF
      user space. Getting it wrong **mirrors every mark vertically and throws no error at all**.
- [ ] **One `imageParameters` block = one visible widget = one incremental signature.** N boxes for
      one signer in one document are **N incremental PAdES signatures**, not one signature with N
      appearances. This is the fact that shapes the data model: placement is a **list**, and a list
      costs signatures.
- [ ] The resulting PDF is an **incremental update**: the previous bytes are kept as a prefix. A diff
      that rewrites the PDF instead of appending breaks the earlier signatures.

### Step 5 — Custody of the signed bytes (ADR-0016)

- [ ] The sealed bytes go to the WORM zone with object-lock. ⚑ And there's an open bug worth not
      making worse: `BL-14` — a `put()` to the COMPLIANCE zone happens **before** the compare-and-swap
      that can reject them, and with COMPLIANCE object-lock **not even root can delete**. If the diff
      touches the order of that sequence, it's a finding.

### Step 6 — What is NOT checked here, and why

Report it under `notApplicable` with its reason, instead of giving a green that reads as coverage.

| Not covered | Why |
|---|---|
| TSA / timestamping | `requiresTsa()` has no callers; no level ≥ B-T is ever produced. Deferred in ADR-0023, `BL-4` |
| LTV, CRL/OCSP | Zero signing-certificate revocation code in `src/` |
| LOTL/TSL trust lists | Live inside the DSS container, which this skill does **not** audit |
| Per-user certificate, policy OID, tenant plan | They don't exist: the seal is resolved **by alias** from the DSS keystore, and `SignRequest` says so in its docblock |
| Dev keystore's chain of trust | It's self-signed, so every signature validates as `INDETERMINATE / NO_CERTIFICATE_CHAIN_FOUND` — recorded in TASK-018 §4. It's environment, not a defect in the diff |

## Report

```markdown
# eidas-compliance — TASK-NNN

**Status:** {PASS|FAIL|WARN}

## Conformant
- Level: PADES_B_B (ADR-0023) · Digest: {enum case} · Format: PAdES

## Findings
- [{category}] {file} {what}

## Not applicable in this repo (not a green)
- {the Step 6 row that applies}

## Decisions with no in-repo home
- {what would be needed and isn't in any ADR or task} → `decision-homeless`
```

## What it does NOT do

- Doesn't audit the EU DSS container or its keystore (that's infra).
- Doesn't validate formats the backend doesn't produce.
- Doesn't raise the signature level or propose raising it: that's an ADR.
