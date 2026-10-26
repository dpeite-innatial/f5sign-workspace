plan: approved 2026-10-23 | record sha1 1df06b2ae6b342f07454baeba3a70f36367e07a8
- [x] 01 The settled read can stop at the first row of a type and a subject (critical) | commits d667e8c8..9ea28e79 | round 1 | findings slices/01.findings.md
- [x] 02 The receipt is a model of its own, with a closed published JSON (critical) | commits 5cde8049 | round 0 | findings slices/02.findings.md
- [x] 03 Session answers one recipient's session status through its contract (critical) | commits a333af83 | round 0 | findings slices/03.findings.md
- [x] 04 A receipt's sources are gathered up to the recipient's act, and only theirs (critical) | commits 79c4c6b7..6d9847a2 | round 1 | findings slices/04.findings.md
- [x] 05 The receipt is assembled from its sources, for its recipient only (critical) | commits 15e3c0a9..4dcc92cb | round 1 | findings slices/05.findings.md
- [x] 06 The receipt renders as PDF/A-3a with its JSON attached (critical) | commits 1ac615e1..27970b43 | round 2 | findings slices/06.findings.md
- [x] 07 One receipt row per (envelope, recipient), tenant-isolated, claimed once (critical) | commits b48f56b6 | round 0 | findings slices/07.findings.md
- [x] 08 One recipient's receipt is issued once, when its fact makes it true (critical) | commits ae2f7e05..3d6880d2 | round 2 | findings slices/08.findings.md
- [x] 09 Three reactors issue a receipt on the fact that ends the act (critical) | commits 663828ef..70700729 | round 2 | findings slices/09.findings.md
- [x] 10 Two issuances of one receipt leave one row and one custody (critical) | commits 96899a62..66a6c4b1 | round 1 | findings slices/10.findings.md
- [x] 11 The integrator downloads a recipient's receipt (critical) | commits f001b3fd..c720daa9 | round 1 | findings slices/11.findings.md
- [x] 12 A receipt is kept as long as its envelope, once it has ended (critical) | commits d14cadf5..b8e8b5c8 | round 3 | findings slices/12.findings.md
- [x] 13 A recipient downloads their own receipt with their session credential (critical) | commits c87b9573..71a218cf | round 3 | findings slices/13.findings.md
- [x] 14 Real flows issue each acting recipient's receipt, both routes serve it (critical) | commits 7a260863..e79d0f11 | round 1 | findings slices/14.findings.md
- [x] 15 The records name what this task built (standard) | commits affed9ba..78dfde59 | round 1 | findings slices/15.findings.md
- [x] 16 Closing: the prose the branch made false says what is true now (critical) | commits d00ec09a..898a5c99 | round 1 | findings slices/16.findings.md

## Paused 2026-10-23 (owner asked to pause)
- All 16 slices ticked (15 planned + closing slice 16). Branch tip f3bc315a, 76 commits ahead of origin, not pushed.
- develop (TASK-068) merged at b8514b5f.
- Full suite at 1404641b: OK (8403 tests, 97584 assertions), arch + phpstan OK (log /tmp/tmp.oYP13m9v89.log). Lint flagged two imports, fixed in the next commit (lint-only, lint clean). That run is last_green_run for Phase 3 (the commit after it is an import line only).
- Next on resume (task-runner Phase 2c → 3): (1) last_green_run = 1404641b (above); (2) OpenAPI dump of this tree into the workspace; (3) Phase 3 gates in one message: task-validate (infection: deferred), doctrine-guard, contract-check, security-audit (diff touches no signing/crypto internals beyond PdfSealer use — say "does not" unless the gate decides); (4) Phase 3b Infection final + Phase 5 docs-sync + Phase 6 task-close in parallel; (5) propose ADR-0086 → Accepted to the owner; (6) merge to develop (owner: 068 → 047; 068 is in), migrate dev DB; ping TASK-070 (f5sign-backend-31), it waits for 047 on develop.
- docs-sync leads: plan.md § Deviations lines tagged "→ docs-sync" (LIVE_SCHEMA two tables, issued_receipt subsection, funnel, read_settled_stream overload, custodian role row; docs/ddd evidence-audit, signing-session SessionStatusReader, identity-access route list; ARCHITECTURE check).
- CLAUDE.md edits (root ai/ store, at landing): closing.review.md § CLAUDE.md list.
- task-close leads: BL-324 extends to the receipts' loop; BL-463 open.
- [x] 17 Infection fix: the receipt guards each have a killing test (critical) | commits 3904d011..7e2b661c | round 1 | findings slices/17.findings.md
