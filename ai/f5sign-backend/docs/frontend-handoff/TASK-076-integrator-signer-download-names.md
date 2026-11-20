# Handoff to the integrator and the signer: downloaded files are named by their envelope

| | |
|---|---|
| **Origin** | branch `fix/download-names` · TASK-076 |
| **Date** | 2026-10-28 |
| **Repos affected** | **integrator (machine key)**, **signer** |
| **Nature** | breaking for anything that parses the file name; no route, status, body or header other than `Content-Disposition` changes |
| **Required action** | integrator: file downloads by the new names. signer: none (it names its own downloads); the receipt's entry inside a bundle changes name |
| **Deployed** | not yet |
| **Status** | Pending |

Read from the routes' `#[OA\*]` attributes and `config/routes/api/`, not from the plan. Where this file and the spec
differ, the spec wins.

## 1. The names, before and now

| Route | Before | Now |
|---|---|---|
| `GET /api/v1/envelopes/{id}/audit-trail` | `registro-<envelope>.pdf` | `<envelope>.pdf` |
| `GET /api/v1/envelopes/{id}/recipients/{recipientId}/receipt`, `GET /api/v1/signing/session/receipt`, `GET /api/v1/copy/receipt` | `justificante-<envelope>-<recipient>.pdf` | `<envelope>.<recipient>.pdf` |
| `GET /api/v1/signing/session/documents.zip`, `GET /api/v1/copy/documents.zip` | `documentos-<envelope>.zip` | `<envelope>.zip` |
| the receipt's entry in a bundle with `with_receipt=1` | `justificante-<envelope>-<recipient>.pdf` | `<envelope>.<recipient>.pdf` (suffixed ` (2)` if a document has that name) |

- Ids are lower case in every name.
- The header stays `attachment; filename=<name>`.
- The documents' names (the single-document route and each document's entry in a bundle) are unchanged.
- A trail or receipt issued before this change is served under the new name, but the JSON embedded in the PDF keeps the
  old name (`registro-<envelope>.json`, `justificante-<envelope>-<recipient>.json`). One issued after this change embeds
  `<envelope>.json` / `<envelope>.<recipient>.json`. The sealed bytes and their `ETag` are unchanged.

## 2. Integrator

Anything that stores or matches the downloaded trail or receipt by its old name must use the new one. Nothing else
about the routes changes.

## 3. Signer

Nothing to release: the app names its own downloads. Only the receipt's entry inside a `with_receipt=1` bundle
changes name (table above). Whether the signer's own `copia.zip` follows `<envelope>.zip` is the signer's decision.
Nothing needs to wait for the backend merge on the signer's side.
