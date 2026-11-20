# Handoff to the signer app: the copy screen, a recipient reads their copy through a read-only link

| | |
|---|---|
| **Origin** | branch `feat/copy-link`, **not merged** · [TASK-070](../tasks/TASK-070-a-recipient-reads-their-copy-through-a-link.md) · [ADR-0088](../adr/ADR-0088-a-recipients-copy-is-read-through-its-own-link.md) |
| **Date** | 2026-10-23 |
| **Repos affected** | **signer** (the copy screen); **dashboard** and integrators (the mint route, informational) |
| **Nature** | six new routes under `/api/v1/copy`, one new machine route; no existing route changes |
| **Required action** | signer: build the copy screen |
| **Deployed** | not yet |
| **Status** | Pending |

Read from the controllers' `#[OA\*]` attributes and the dumped spec, not from the plan. The routes below are the
six that the signer calls: five in `config/routes/api/copy.php` and the receipt, which Evidence & Audit serves. Where this file and the spec differ, the spec wins.

## Purpose

A recipient whose part has ended gets their copy back from a link that lives as long as the documents are kept. Until
now the only link they held was the signing token, which expires and, behind a declared access gate, cannot open a
finished session ([BL-188](../BACKLOG.md), closed by this task).

## The link

- It looks like `f5s_cl_` followed by 36 letters and digits. It is sent as `Authorization: Bearer <link>` to the three
  routes that take it (open, send, auth), and to nothing else.
- It is **read-only**. It admits those three routes and no route that signs, declines or reads the signing ceremony.
- It stays valid until the conservation period of the documents ends. There is no expiry date to show.
- **Every refusal is one 401 with no `code`**: unknown or malformed link, conservation period over, or a link replaced
  after the sender corrected the recipient's contact. The screen says "this link no longer works" and nothing more:
  nothing tells the cases apart, and nothing should be guessed.

## Flow

1. **Open.** `POST /api/v1/copy/open` with the link and no body. 200 carries `envelope_id`, `recipient_id`,
   `document_title`, `locale` (nullable) and `access_gate`.
   - `access_gate` is `null`: the body also carries `read_credential` and `expires_at`. Store the credential and go to
     step 4.
   - `access_gate` is not `null`: no credential yet. Render the gate **exactly as the signing access gate**: the same
     fields (`method`, `methods` with `masked_destination` and `code_length` each, `selection`, `masked_destination`,
     `code_length`), the same meaning of `ESCALATION` and `FREE_CHOICE`.
2. **Send a code.** `POST /api/v1/copy/auth/otp/send` with the link. The body is optional: `method` (a declared one;
   absent means the one in force) and `resend` (`true` mints a new code). 202 answers `minted`, `code_expires_at`,
   `next_resend_at`. One code a minute; per-channel ceilings apply (429 `OTP_SEND_COOLING_DOWN`, with `Retry-After`,
   `retry_after_seconds` and `retry_at`; prefer `retry_at`). Other answers: 409 `AUTH_METHOD_NOT_DECLARED`,
   `AUTH_METHOD_NOT_CHOSEN`, `AUTH_METHOD_NOT_DELIVERED`, `AUTH_NO_DESTINATION`; 401 `AUTH_NO_OPEN_CHALLENGE` when the
   gate asks for no code.
3. **Submit it.** `POST /api/v1/copy/auth` with the link and `{"code": "...", "method": null}` (`method` optional).
   200 answers `read_credential` and `expires_at`. 401 codes: `AUTH_CODE_INCORRECT`, `AUTH_CHALLENGE_EXPIRED`,
   `AUTH_NO_OPEN_CHALLENGE`, `AUTH_GATE_MISCONFIGURED`; 409 `AUTH_METHOD_NOT_DECLARED`; 422 on a malformed body.
4. **Read.** With the read credential as `Authorization: Bearer`, see Reading below.

The copy's code, attempts and lock are its own: passing or failing here never touches a signing session, and the other
way round.

## Lock

Five wrong codes lock the gate. The answer is **429 `AUTH_COOLING_DOWN`** with `Retry-After` (seconds left). The first
wait is five minutes, each further lock doubles it up to a day, and it **always lifts by itself**; a right code resets
it. This route **never answers 423**, so there is no "contact the sender" state on this screen: show the wait and let
the recipient try again.

## Reading

- `GET /api/v1/copy` lists what the credential may download: `envelope_id`, `recipient_id`, `document_title`,
  `documents[]` of `{document_id, name}`, `signed_copy` and `has_receipt`. **An empty list is a real state**: a recipient who declined
  reads no document, whether the envelope is open or closed, and one whose step has not been reached reads none yet.
  It is also empty from the moment a recipient's signature or approval is accepted until their copy carries it — their
  signature in the documents under incremental signing, otherwise the sealed envelope. Before the envelope closes the
  list holds the current version; after it, only sealed documents.
- `signed_copy` is always present and says which empty list the screen is looking at. It is the same field, with the
  same values and the same `null`, as `signed_copy` on `GET /api/v1/signing/session`:
  - `APPLYING` — their signature is being put into the PDF, which normally takes seconds. `documents` is empty
    meanwhile: show that the copy is being prepared and list again quickly, then backing off.
  - `AWAITING_ENVELOPE` — their act is accepted, and nothing of theirs will be in a PDF before the envelope ends (a
    single-seal envelope, a role that approves rather than signs, or an envelope already closed and not yet sealed).
    `documents` is empty, and on an envelope still open this can last **days**, until the envelope ends and is
    sealed. Say so, and do not poll fast for it: list again when the recipient comes back. The
    read credential lasts 15 minutes, so a later look means opening the link again, and behind a gate that costs the
    recipient another code.
  - In neither case show the empty list as final.
  - `CONTAINS_YOUR_SIGNATURE` (their signature is in the documents, which are not finished) or `FINAL` (every document they may
    read carries its seal — the envelope completed, or (`SEQUENTIAL_PADES`) their own act has landed and each of those
    documents was sealed early, while others may still be acting) — `documents` lists what they may download.
  - `null` — no act of theirs is accepted and waiting: they declined or were passed over without acting (before or
    after the envelope ends; they read no document), have not acted yet, or only receive the documents and the
    envelope has not yet completed with every document they may read sealed (from then on they read `FINAL`). `documents` is what they may
    download now, under the rules above; an empty list here is not a wait for their own act.
> ⚑ 2026-10-27, TASK-072: `has_receipt` is now `receipt != null`; read `receipt` (see
> [TASK-072's handoff](TASK-072-signer-copy-card-reads.md)). The text below is the TASK-070 wording.

- `has_receipt` is always present. It is `true` when this recipient acted (signed, approved or declined), so a receipt is owed
  them and `GET /api/v1/copy/receipt` serves it; it can be `true` a short while before the receipt is issued (see
  Receipt below). It is `false` for a recipient with no receipt, such as an informational member. A decliner's screen
  shows the receipt beside an empty document list.
- `GET /api/v1/copy/documents/{documentId}` returns the PDF bytes (`application/pdf`). 404 for a document the list
  would not show, one answer for every reason; 409 when the document is recorded but its bytes are no longer kept;
  400 for a malformed id.

## Expiry

The read credential lasts 15 minutes and is **not renewable**: there is no renew route and no refresh credential. On a
401 from `GET /api/v1/copy` or a document, open the link again. Behind a gate that costs another code, so do not reopen
silently in the background: ask the recipient.

## Receipt

`GET /api/v1/copy/receipt`, with the read credential as `Authorization: Bearer`, returns the recipient's sealed receipt
of their own act as a PDF (`application/pdf`, an attachment named `justificante-<envelope id>-<recipient id>.pdf`). It
is the same PDF the integrator reads for them. A decliner reads it whether the envelope is open or closed, though they
read no document.

> ⚑ **2026-10-28:** the name changed; see [TASK-076](TASK-076-integrator-signer-download-names.md).

> ⚑ 2026-10-27, TASK-072: the button follows `receipt` (`ISSUED` enables it, `PENDING` shows it disabled, `null` hides it),
> not `has_receipt`; see [TASK-072's handoff](TASK-072-signer-copy-card-reads.md).

- **When to show the button:** when `has_receipt` is `true`. Hide it when it is `false`.
- **409 `RECEIPT_NOT_READY`:** the recipient acted and the receipt is not issued yet, which normally takes seconds.
  Show that it is being prepared and ask again shortly, backing off. Do not treat it as a failure.
- **409 `RECEIPT_UNAVAILABLE`:** the receipt is recorded and its PDF cannot be read now. Offer a retry later; it is not
  a wait that resolves in seconds.
- **404:** this recipient has no receipt because they did not act. Not reached when the button follows `has_receipt`.
- **401:** as for the list: open the link again.
- A receipt is never rewritten, so it carries a strong `ETag`; `If-None-Match` answers 304.

## Not yet

- **The notices that carry the link** to the recipient are a later record, so for now the link reaches a recipient only
  through the integrator below.

## For integrators and the dashboard (informational)

`POST /api/v1/envelopes/{id}/recipients/{recipientId}/copy-links`, authenticated by API key, takes no body and answers
201 `{link, open_path}`; `link` matches `^f5s_cl_[A-Za-z0-9]{36}$` and `open_path` is `/api/v1/copy/open`. A link minted
here does not retire one minted earlier. A recipient who signs through the integrator's API holds a link with no gate.

> **2026-10-27, TASK-072:** the 201 now carries `Cache-Control: private, no-store`. The link is a bearer credential,
> returned once: store it where you keep it, and do not route this call through a cache that would keep the response.

Its other answers:

- 400 — `id` or `recipientId` is not a well-formed id.
- 401 — no API key, or one that is not valid.
- 404 — no such envelope, it belongs to another organisation, or that recipient is not on it; one answer for all three.
- 409, with `code`:
  - `ENVELOPE_NOT_SENT` — the envelope has not been sent.
  - `RECIPIENT_SLOT_NOT_CLAIMED` — the recipient is a claimable slot nobody has claimed.
  - `RECIPIENT_STEP_NOT_ACTIVE` — an informational member (viewer, reviewer, editor) whose step was never reached,
    unless the envelope ended agreed.
  - `RECIPIENT_HOLDS_NO_COPY` — a signer or approver who has not signed or declined yet, or who was released; a
    role the API does not run. Only the first can change: mint again once that signer or approver has signed or declined.

## What the signer app has to do

Build the copy screen on the flow above. Nothing else changes: the signing routes, the signing token and the session
credential are untouched.

## Note, 2026-10-26, TASK-071

2026-10-26, TASK-071: under `SEQUENTIAL_PADES`, `signed_copy` reads `FINAL` before the envelope completes, once the
recipient's own act has landed and every document they may read is sealed; under `SINGLE_SEAL`, and for a recipient who
only receives the documents, it still reads `FINAL` only at completion. See
TASK-071-signer-integrator-signed-copy-final.md.
