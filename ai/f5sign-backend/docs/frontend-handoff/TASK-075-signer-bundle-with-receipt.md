# Handoff to the signer app: the documents bundle can carry the receipt

| | |
|---|---|
| **Origin** | branch `feat/bundle-with-receipt`, **merged to `develop` 2026-10-28** · TASK-075 · [ADR-0093](../adr/ADR-0093-a-recipients-bundle-takes-their-receipt-from-the-receipt-routes-rule.md) (`Accepted`) |
| **Date** | 2026-10-28 |
| **Repos affected** | **signer** |
| **Nature** | additive: one optional query parameter, `with_receipt`, on the two bundle routes; no new route, operationIds unchanged |
| **Required action** | signer: unlock the files and the receipt together; offer the bundle with the receipt |
| **Deployed** | not yet |
| **Status** | Pending |

Read from the bundle controllers' `#[OA\*]` attributes and `config/routes/api/`, not from the plan. Where this file and
the spec differ, the spec wins. It builds on [TASK-072's handoff](TASK-072-signer-copy-card-reads.md) §7: a bundle
requested without the parameter is exactly the one described there.

## 1. The parameter

`with_receipt=1` on `GET /api/v1/signing/session/documents.zip` and on `GET /api/v1/copy/documents.zip`.

- Absent: TASK-072's bundle, unchanged. Any other value (`0`, `true`, empty): **400**.
- With it, the archive ends with one more entry, the recipient's own receipt, named
  `justificante-<envelope>-<recipient>.pdf`, always last.

> ⚑ **2026-10-28:** the name changed; see [TASK-076](TASK-076-integrator-signer-download-names.md).

- The receipt is the one `GET /api/v1/signing/session/receipt` / `GET /api/v1/copy/receipt` serves, and never another
  party's.

Answers (the bundle is all or nothing; no archive is sent on any refusal):

- **404** as before, and also when the recipient has not acted (they have no receipt to carry).
- **409 `RECEIPT_NOT_READY`**: the act is recorded and the receipt is not issued yet. Wait and re-read `receipt` on the
  read.
- **409 `RECEIPT_UNAVAILABLE`**: the receipt is recorded and cannot be served. Fall back to the bundle without the
  parameter.
- **409 `CONFLICT`**: a listed document is no longer kept (as without the parameter).
- When both a receipt problem and a document problem apply, the receipt's code comes first.
- **401** as before.

## 2. One unlock

Show the files and the receipt as ready together, once `signed_copy` is `CONTAINS_YOUR_SIGNATURE` or `FINAL` **and**
`receipt` is `ISSUED`. Under `SEQUENTIAL_PADES` the receipt follows the signature by seconds: keep both pending until
both are ready.

The exception: while `signed_copy` is `AWAITING_ENVELOPE` (under `SINGLE_SEAL`, until every party has acted, which may
take days) show the receipt as soon as `receipt` is `ISSUED`, and the files as pending the other parties.

The unlock rule is the app's: the reads already carry `signed_copy` and `receipt`; there is no new member.

## 3. Which bundle

Offer the bundle with the receipt from **one** document up, once both are ready. Keep "download all" without the
receipt for **two or more** documents, as TASK-072 §7 says (its "with one, the single download is enough" is about the
bundle without the receipt only). On `RECEIPT_UNAVAILABLE`, offer the bundle without the parameter.

## 4. Not in this task

No cap on the bundle's size or count (BL-484). The session receipt route's caching is unchanged (BL-472).
