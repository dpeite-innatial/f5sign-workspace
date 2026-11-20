# Handoff to the signer app: the copy card reads (acted date, receipt standing, notified destinations, document bundle)

| | |
|---|---|
| **Origin** | branch `feat/copy-card-reads`, **not merged** · TASK-072 · [ADR-0091](../adr/ADR-0091-a-recipients-reads-say-whether-their-receipt-is-issued.md) (`Accepted` 2026-10-27) |
| **Date** | 2026-10-27 |
| **Repos affected** | **signer** |
| **Nature** | additive: five members on `GET /api/v1/copy`, three on `GET /api/v1/signing/session`, two new routes; `has_receipt` redefined; `Cache-Control: no-store` on the copy routes that answer a body (not on the code send) |
| **Required action** | signer: read the new members as optional (absent = not shown); offer the receipt button from `receipt`; offer the documents bundle |
| **Deployed** | not yet |
| **Status** | Pending |

Read from the controllers' `#[OA\*]` attributes, `config/packages/nelmio_api_doc.yaml` and `config/routes/api/`, not
from the plan. Where this file and the spec differ, the spec wins. Every member below is **always present** on a 200
(`null` and `[]` included); a client that treats an absent member as "not shown" is also correct against an older
backend.

## 1. `acted_at` (both reads)

`GET /api/v1/copy` and `GET /api/v1/signing/session` carry `acted_at`: an ISO-8601 date-time, or `null`.

- It is when this recipient's act (a signature, an approval or a decline) was accepted. `null` before any act: show no date.
- For an act accepted before the platform recorded that instant, it is the instant the act was recorded on the
  envelope (a fallback, so an old act still shows a date).
- The verb: on the copy read, `act` (section 2) picks it (`SIGNED` Firmado, `APPROVED` Aprobado, `DECLINED`
  Rechazado). On the session read there is no `act`: `status` `DECLINED` is Rechazado; otherwise the role
  (`signer.role`) says Firmado (`SIGNER`) or Aprobado (`APPROVER`).

## 2. `act` (copy read only)

`SIGNED` | `APPROVED` | `DECLINED` | `null`. `APPROVED` is an approval in a role that does not sign. `null`: the
recipient has not acted, or only receives the documents.

## 3. `receipt` (both reads)

`ISSUED` | `PENDING` | `null`. It drives the receipt button (`GET /api/v1/copy/receipt` on the copy screen,
`GET /api/v1/signing/session/receipt` on the session):

- `ISSUED`: enable the button. The route can still answer **409 `RECEIPT_UNAVAILABLE`** (the receipt is recorded and
  its PDF cannot be read now, an operator incident): offer a retry later.
- `PENDING`: the recipient acted and the receipt is not issued. Show the button disabled ("preparando"). The route
  would answer 409 `RECEIPT_NOT_READY`. **Poll the read** (not the receipt route), backing off, **and cap the polling**:
  a `PENDING` can last with no bound. After the cap stop polling and keep the button disabled.
- `null`: they have not acted, no receipt is owed (the receipt route answers 404). Hide the button.

## 4. `has_receipt` (copy read)

Redefined: it is now exactly `receipt != null`, so it is `true` for `PENDING` as well as `ISSUED`. It is kept for
clients that read it before `receipt` existed. **Read `receipt` instead.**
[TASK-070's handoff](TASK-070-signer-copy-screen.md) said "when this recipient acted"; that wording is superseded.

## 5. `envelope_outcome` and `recipient_name` (copy read)

- `envelope_outcome`: `AGREED` | `NOT_AGREED` | `null` while the envelope has not closed. The same value as
  `envelope_outcome` on `GET /api/v1/signing/session`, from the same source, but not always at the same moment: this read
  carries it from the close, while after the close the session read answers it only to a recipient it still serves, and
  not while a document they may see awaits its seal (409 `SEAL_PENDING`, a problem document, not a session body).
- `recipient_name`: the recipient's own name as the sender wrote it; an empty string when they are addressed only by
  id (not `null`). Show no name in that case.

## 6. `notified_on` (session read only)

An array of `{channel, masked_destination}`, `channel` being `EMAIL` or `SMS`, in the declared order of the
recipient's notification channels. The destination is masked as the access gate masks one. A channel with no contact
on file is left out; `[]` when the recipient is notified on no channel: show no line.

- Line: "te enviaremos el enlace a tu copia a ..." followed by the destinations.
- It says where the notices are **addressed**, not that they arrived.
- Show it only once TASK-071 (the notices that carry the copy link) is deployed; before that the line would promise a
  link nobody sends.

## 7. The documents bundle

- `GET /api/v1/signing/session/documents.zip`, with the session credential (`Authorization: Bearer`).
- `GET /api/v1/copy/documents.zip`, with the copy read credential.

200: `application/zip`, `Content-Disposition: attachment` named `documentos-<envelope id>.zip`. One entry per
document the read lists, in its order, holding the bytes the single-document route serves. Entry names are the
display names with control and format characters and line/paragraph separators removed, composed to NFC, `/`, `\` and
`:` replaced by `_`, `.pdf` added when the name does not end in `.pdf`, a Windows reserved name (`CON`, `NUL`, `COM1`…) prefixed
with `_`, and cut to 240 UTF-8 bytes including the suffix of a repeated name (compared without case), which gets
` (2)`, ` (3)`. The archive is streamed with a `Content-Length`, so a download can show its progress; nothing else
about the response changed.

> ⚑ **2026-10-28:** the name changed; see [TASK-076](TASK-076-integrator-signer-download-names.md).

**All or nothing**, with the single-document rules:

- **404** (one answer for every refusal): the read lists no document, or any listed document would be refused. In
  particular, while `signed_copy` is `APPLYING` or `AWAITING_ENVELOPE` it is 404; poll the read, not this route.
- **409**: a listed document is recorded but its bytes are no longer kept; no archive at all. Both bundle routes answer
  it (`code` `CONFLICT`), as their single-document routes do: show that a document is no longer available, and offer no
  retry.
- 400 malformed request; 401 as for the read. On the copy route a copy that is no longer valid (past its documents'
  conservation period, or retired by a change to the recipient's contact or access code) is a 401, not a 404: open the
  link again.

Offer "download all" when the read lists **two or more** documents; with one, the single download is enough. The
archive has no `ETag`: it is not revalidated. ⚑ Since TASK-075 the threshold for the bundle *with* the receipt is one document: see [TASK-075's handoff](TASK-075-signer-bundle-with-receipt.md) §3.

## 8. `Cache-Control: no-store` on the copy routes

Open, auth (the code submit), the list, the documents (single and bundle) and the receipt carry `no-store` (the receipt keeps its
`private` and strong `ETag`/304). The code send (`POST`, 202) carries none. Nothing for the app to do, except **not
caching them in a service worker**.

## 9. Not in this task

The sender's name is not exposed; `branding.company_name` is still the envelope title.
