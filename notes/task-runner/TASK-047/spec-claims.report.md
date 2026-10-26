# Claims check TASK-047 — run 1 (HEAD c90c8135) — status: fail
B1 (block): under SEQUENTIAL_PADES Envelope records the act only on RECIPIENT_SIGNED (Envelope::completesOn elects SIGNATURE; OnSessionCompleted dispatches CONSENT, declined). Route keyed on "Envelope records the act" answers 404, not 409 RECEIPT_NOT_READY, in the commit→signature window (BL-462). §4#5, ADR-0086 §2.6/§3.1, AC-8b.
B2 (block): ADR-0086 §3.3 / AC-9d "at most one RECIPIENT_SIGNED per subject on production paths" false: SignForRecipientUseCase repeat guards are isCleared() (needs an image) and ArtifactAlreadyAppended (needs assignments). APPROVER without image: redelivered SESSION_COMPLETED appends a second RecipientSigned with the same deterministic execution id. Verified by orchestrator at SignForRecipientUseCase.php:132,170,179.
W1: no port says "envelope ended"; ConservationCeilings::of answers provisional/final for any sent envelope. AC-12a/b need a named signal.
W2: ActEvidenceReader::forEnvelope returns all recipients' evidence; receipt must filter to its recipient (AC-5).
Minor: RecordingCustodyStore lives in tests/F5Sign/Storage/Testing/Fake/.
