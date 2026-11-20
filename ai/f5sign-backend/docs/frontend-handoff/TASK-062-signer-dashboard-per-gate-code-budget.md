# Traspaso al firmante y al dashboard — cada puerta tiene su propio cupo de envíos de código

| | |
|---|---|
| **Origen** | rama `feat/otp-budget-per-gate`, **sin mergear** · [TASK-062](../tasks/TASK-062-each-gate-has-its-own-code-send-budget.md) |
| **Fecha** | 2026-10-20 |
| **Repos afectados** | **signer** y **dashboard** (integradores informados) |
| **Naturaleza** | ninguna ruta, clave ni código cambia |
| **Acción requerida** | ninguna |
| **Desplegado** | not yet |
| **Status** | Pending |

## Lo que cambió en el contrato

Nada. El 429 de `POST /api/v1/signing/session/auth/otp/send` y el de su gemelo de máquina es el mismo: mismo
`code`, mismas extensiones, y no nombra contador ni puerta.

## Lo que cambió en el comportamiento

Los envíos de la puerta de acceso y los de la puerta de firma ya no comparten cupo. Por hora:

- **Por sesión y por puerta:** 5 por email y 5 por SMS (antes, 3 por SMS, compartidos entre las dos puertas).
  Firmar y rechazar comparten el cupo de la puerta de firma. Un `recover: true` gasta el de acceso.
- **Por destino en este sobre:** 10 (el SMS era 5).
- **Por destino en todos los sobres:** 30.
- **Por IP de origen:** 30 (el SMS era 10).
- Los envíos de máquina por cliente de API no cambian (300 por email, 100 por SMS).

## Lo que el frontal tiene que hacer

Nada. La copia del 429 del firmante ya la corrigió su equipo el 2026-10-20.

## Cómo verificarlo desde el frontal

Pedir tres códigos SMS de acceso, entrar y pedir el de firma: llega (antes, 429).
