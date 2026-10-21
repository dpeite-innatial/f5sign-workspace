# security-audit — TASK-067

**Status:** WARN
**Total issues:** 0 blocking, 11 warnings
**Delegations:** security-audit-backend (warn), eidas-compliance (warn)
Last green run cited, not re-run: 4a1a27fa, 8001 tests, wt-backend lane, image f5sign/backend:dev-task067. `composer audit` / `pip-audit` NOT run (no network/instructions): dependency state is undeclared, not clean.

## Core issues
- [dependencies] assets/signature-execution/pyhanko-requirements.txt: 16 new Python packages (asn1crypto, cryptography 50.0.2, lxml, oscrypto 1.3.0, requests, urllib3, certifi, pyyaml...) hash-pinned but no CVE scan exists for them; composer audit does not cover pip. oscrypto is unmaintained. WARN.
- [pii] Recorded field values (PII): logs carry ids/kind/exit code only (PsrFieldDrawingLog); no route, migration or column added; composer.json/lock, .env* untouched; no secrets found in the diff. Values in stack frames: closing.review.md finding 6 (BL-278 class, #[\SensitiveParameter] on PyHankoFormEngine::run/inspect/apply, DrawnRevisionCheck::verify, FieldTextLayout::layOut) - the backend audit found the 22 listed parameters covered; confirm the closing-review list is applied. WARN.
- [pii-at-rest] Recipient::recordAdmittedReservations writes the text in clear, earlier than before; FieldCipher unused, ADR-0033 Proposed. WARN.
- Auth/Authz, multi-tenant: no new route or table; custody opened with context tenantId. OK.
- Secrets: OK. Errors/logging: OK (generic 500, no stderr read).

## security-audit-backend (warn) - see security-audit-backend.report.md
Argv array, empty env, stdin only, cp1252+escaped content stream, DrawnRevisionCheck, hash-pinned wheels: held. Warnings: hand-listed SensitiveParameter census; only RLIMIT_AS (no CPU/NPROC), PHP holds PDF 3x; page_tree per-path seen set (shared /Kids DAG can blow memory, act fails every retry; tenant self-DoS); interpreter without -I; no sandbox; base image/apk/pip unpinned; reservations in clear.

## eidas-compliance (warn) - see eidas-compliance.report.md
PAdES_B_B/SHA256 unchanged, DSS sole signer, fill revision before signature, earlier signatures kept, /Lock, placement, SINGLE_SEAL and annulment seal conformant. Warnings: FormRevisionPlanner::fillOf (216-224) can draw and lock a co-step signer's admitted-but-unsigned values under another signer's signature (decision-homeless, owner's call; no test with a parallel step); off-page placement no longer refused (BL-366); odd page geometry blocks act on every retry; DrawnRevisionCheck does not verify earlier drawn values unchanged.

## Categories reviewed
- Secrets: OK; PII: WARN; Auth/Authz: OK; Multi-tenant: OK; Dependencies: not scanned (undeclared)
