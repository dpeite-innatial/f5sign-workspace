# Handoff 2026-10-07 — signature marks and per-recipient signing modes (backend)

## Done today
- **TASK-053** (drawn signature on the mark) is merged on backend `develop` as `5d0957d1` and pushed. The dev DB is
  migrated, and the dev containers were recreated with `gd` (the 500 on signing was containers older than the image).
- The **signer** has the TASK-053 handoff. It asked for, and got, the backend's OK to replace the biometric modal with
  an optional checkbox: drawing is free, and the box decides whether the strokes are sent.
- **AI store:** `spec-claims` re-runs after a spec edit, adds a category for causal claims, and gains the new
  `replicator` agent with `implement-backend` Step 3b (delegate repetition to a cheaper model, never a fork).

## In progress
### A — mark text fitting (`fix/mark-text-fits`, worktree `f5sign-backend-mark-text`, lane kept up)
- **The defect:**
  - a long name in a text-only mark loses its start (DSS right-aligns it and clips the left);
  - the drawn signature is stretched over the whole box.
- **Measured against live DSS 6.4** (renders in `f5sign-backend-mark-text/var/task-runner/mark-text/dss-measure/`):
  - DSS honours `\n` at a fixed 8 pt;
  - its wrapping modes change the font size, and none ellipsizes;
  - `ZOOM_AND_CENTER` keeps the image's aspect ratio;
  - the font is PT Serif Regular, from `dss-pades-6.4.jar`.
- **The fix being built:**
  - Text-only marks go LEFT and MIDDLE with padding 3. The backend wraps at words to the box using PT Serif widths,
    caps the lines and ellipsizes the last one, so the size is never changed.
  - Image marks use `ZOOM_AND_CENTER`, with the name on one line, ellipsized.
  - Rewording `consent_biometric_required` for the checkbox.
- **The image's top margin is the signer's job** (maintainer chose option (a)): it leaves about 6 % transparent margin
  in the PNG. This is added to the TASK-053 handoff.
- **Still to do:** when the implementing agent reports, run the gates and merge.
  - Mind the trail: if a mark shows an ellipsized name, the trail must still be truthful (ADR-0072).

### B — TASK-054 (spec only, branch `docs/task-054-signature-modes`, pushed, worktree `f5sign-backend-task-054`)
- **Per recipient:**
  - `signature_modes` ⊆ {SIMPLE, DRAW, TYPE}, with `[SIMPLE]` by default;
  - `biometrics_offered`: offered, never required (the DPIA's free-consent rule);
  - `show_name`, with no empty mark allowed.
- The commit declares `signature_mode`, and the backend checks it.
- **⚠ Open D2:** may `SIMPLE` be combined with `DRAW`/`TYPE` (optional drawing)? The build waits for the answer.

## Waiting on people
- **Legal:** the checkbox reading (a PNG is not biometric, the strokes are) and the consent copy. Then update
  `f5sign-docs/Especificaciones/Páginas Legales.md`, which still says that without consent drawing is disabled.
- **The maintainer:** TASK-054 D2.

## Traps seen today
- The shared image tag `f5sign/backend:dev` is built from whichever tree last ran `docker build`. After a merge
  that touches the Dockerfile, recreate the dev containers: `make up`, then `worker-down` and `worker-up`.
