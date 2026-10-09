# Traspaso al signer (PROVISIONAL): se retira `DECLINE_NOT_OFFERED_IN_QUORUM_STEP`

| | |
|---|---|
| **Origen** | TASK-050 §3.3 (ADR-0073), etapa A |
| **Medido en** | `f5sign-backend` rama `feat/step-policy` @ `8f42995d` (2026-09-29). Sin mergear en `develop`, sin desplegar |
| **Repos afectados** | signer (`f5sign-signer`, worktree `f5sign-signer-adr0073`). El dashboard-sf no se ve afectado: no llama a `POST /api/v1/signing/decline` |
| **Status** | **PROVISIONAL, accionable contra mocks.** El traspaso oficial llegará en `f5sign-backend/docs/frontend-handoff/` cuando el paquete ADR-0073 aterrice |

## Qué cambió (commiteado, no planeado)

- El `ProblemCode` **`DECLINE_NOT_OFFERED_IN_QUORUM_STEP` ya no existe**. Se ha quitado del enum publicado
  (`config/packages/nelmio_api_doc.yaml`) y de la descripción del 409 de `POST /api/v1/signing/decline`.
  Nadie lo emite.
- **Un rechazo dentro de un paso `AT_LEAST n` (quórum) se acepta** igual que cualquier otro rechazo, con la misma
  respuesta de éxito que un rechazo en un paso `ALL`. Es el sobre quien lo evalúa en la admisión con la política del
  paso: el paso sigue si el mínimo aún se alcanza, y el sobre termina `NOT_AGREED` / `MINIMUM_UNREACHABLE` si ya no.
- `DECLINE_NOT_OFFERED_TO_ROLE` **no cambia**.
- ⚠ Hoy todavía no se pueden crear pasos `AT_LEAST` por la API: eso llega con la etapa C, que tendrá su propio
  traspaso. Por eso el cambio no es observable end-to-end hasta entonces. Sí lo es la ausencia del código.

## Qué tiene que hacer el signer

1. `useSignerNavigation.ts`: quitar `DECLINE_NOT_OFFERED_IN_QUORUM_STEP` del `case` que comparte con
   `DECLINE_NOT_OFFERED_TO_ROLE` y de la constante `CODES_DECLINE_NOT_OFFERED`.
2. Tests: `useSignerNavigation.spec.ts` y `useDecline.spec.ts` pierden ese miembro de sus `it.each`.
3. Docblock del `decline()` del cliente API: quitar el código de la lista de 409.
4. El flag `declineNotOffered` no cambia: lo sigue activando `DECLINE_NOT_OFFERED_TO_ROLE`.
5. Ya no hay que ocultar Rechazar por estar en un paso de quórum. El signer tampoco lo deducía por su cuenta, porque
   no lee `min_signatures`, así que no hay más lógica que tocar.

Lo que sigue vigente es el apartado 6 de `../../adr-0073-provisional-handoffs/handoff-signer-adr0073.md`, salvo su
aviso "no lo hagáis todavía": ya se puede hacer.
