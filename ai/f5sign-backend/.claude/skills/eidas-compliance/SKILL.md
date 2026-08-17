---
name: eidas-compliance
description: 'Valida el cumplimiento eIDAS de lo que este backend hace HOY: sellado PAdES B-B en servidor vía EU DSS 6.4, digests de un enum cerrado (SHA-256/384/512), y las propiedades medidas contra el DSS vivo (origen de coordenadas, un widget = una firma incremental). NO valida TSA, LTV, trust lists ni certificados por usuario: nada de eso existe en el repo, y fingir que se comprueba es peor que no comprobarlo. Decisiones vinculantes: ADR-0023, ADR-0034, ADR-0016 y docs/tasks/TASK-005|006|017|018. Úsalo con /eidas-compliance TASK-NNN. Activar con "compliance eIDAS", "revisar firma", "validar PAdES", "check EU DSS".'
---

# eIDAS Compliance (lo que existe)

La invoca `security-audit-core` cuando **el diff toca firma o cripto** — `src/F5Sign/SignatureExecution/`,
`Foundation/Crypto/`, DSS, PAdES. Este formato de task no tiene tags: la condición es el diff, y la evalúa
quien delega.

> ⚑ **Esta skill se recortó el 2026-08-17 tras una auditoría.** Cubría TSA, LTV, trust lists LOTL/TSL,
> certificados por usuario y los formatos XAdES/CAdES/JAdES. **Ninguno tiene diana en este repo**: cero
> referencias a LOTL/TSL, cero OCSP/CRL, `requiresTsa()` sin un solo llamante en `src/`, ningún certificado
> por usuario ni policy OID, y un único enum de nivel cuyos cuatro casos son `PAdES_BASELINE_*`. Aquellos
> pasos devolvían **verde por vacío en todos los diffs**, que es la forma más cara de fingir cobertura. Lo
> retirado no se pierde: vive en las *Consequences* de ADR-0023 (breadth B-B, el resto diferido) y en `BL-4`.

## Invocación

```
/eidas-compliance TASK-NNN
```

## Inputs

- `var/task-runner/TASK-NNN/changes.diff` y el `.md` de la task
- Las decisiones vinculantes, **en el repo**:
  [`ADR-0023`](../../../docs/adr/ADR-0023-dss-server-signing-seal-flow.md) (sellado en servidor con DSS),
  [`ADR-0034`](../../../docs/adr/ADR-0034-sequential-incremental-pades.md) (PAdES incremental secuencial y
  marcas visibles), [`ADR-0016`](../../../docs/adr/ADR-0016-storage-model.md) (WORM + object-lock), y
  `docs/tasks/TASK-005`, `TASK-006`,
  [`TASK-017`](../../../docs/tasks/TASK-017-sequential-incremental-pades.md), `TASK-018`
  <!-- OFFREPO: la lista original de "12 decisiones" (`project_cloud_signing_decisions.md`) y la guía de
  integración de EU DSS viven en el repo de diseño y NO son alcanzables desde un checkout del backend. Todo
  lo vigente está restatado en los ADRs de arriba. Si una comprobación necesita una decisión que no está en
  ninguno de ellos, **el hallazgo es esa ausencia** (`decision-homeless`), no la divergencia. -->

## Ejecución

### Paso 1 — Nivel de firma: **B-B es la decisión, no una carencia**

- [ ] El código produce `SignatureLevel::PADES_B_B`. ⛔ **No pidas B-T/B-LT/B-LTA.** ADR-0023 §Consequences:
      *"the seal-level breadth is **B-B only**; B-T/B-LT/B-LTA … are deferred"*, fichado en `BL-4`. Un diff
      que **suba** el nivel es una decisión (ADR), no una mejora silenciosa; uno que se quede en B-B es
      conforme. ⚠ El único texto que dice "B-LT por defecto" es
      `docs/ddd/signature-execution-domain-model.md`, y ahí describe el **modelo objetivo**: no es el listón
      de hoy.

### Paso 2 — Digests: el enum ya cierra la puerta

- [ ] Los digests salen de un enum **cerrado** `{SHA256, SHA384, SHA512}` (`DigestAlgorithm`), cuyo docblock
      dice que SHA-1 y MD5 se omiten por política eIDAS. O sea: **son irrepresentables**, y buscarlos es
      buscar lo que el tipo ya prohíbe. El check real es que **nada introduzca un digest por string**
      esquivando el enum.
- [ ] Claves y curvas **no** se eligen aquí: las resuelve DSS desde su keystore **por alias**. Ningún tamaño
      de clave ni curva aparece en `src/`, así que no lo reportes como omisión.

### Paso 3 — Formato: solo PAdES, y decirlo

- [ ] El único formato con camino de código es **PAdES**. No hay XAdES, CAdES ni JAdES, ni superficie de firma
      XML o JSON. Si el diff introduce uno, **es un ADR** (formato nuevo = decisión de producto y de
      compliance), no una extensión.

### Paso 4 — Las propiedades medidas contra el DSS vivo

Restatadas en [`TASK-018`](../../../docs/tasks/TASK-018-visible-signature-mark.md) §1; usarlas de ahí y, si se
re-miden, **añadir línea fechada** en vez de editar la vieja.

- [ ] **El origen de coordenadas es arriba-izquierda**, con `originY` creciendo hacia abajo — al contrario que
      el espacio de usuario de PDF. Equivocarlo **espeja cada marca verticalmente y no da ningún error**.
- [ ] **Un bloque `imageParameters` = un widget visible = una firma incremental.** N cajas para un firmante en
      un documento son **N firmas PAdES incrementales**, no una firma con N apariencias. Es el hecho que da
      forma al modelo de datos: la colocación es una **lista**, y una lista cuesta firmas.
- [ ] El PDF resultante es un **incremental update**: los bytes previos se conservan como prefijo. Un diff que
      reescriba el PDF en vez de añadir rompe las firmas anteriores.

### Paso 5 — Custodia de los bytes firmados (ADR-0016)

- [ ] Los bytes sellados van a la zona WORM con object-lock. ⚑ Y hay un fallo abierto que conviene no
      empeorar: `BL-14` — se hace `put()` a la zona COMPLIANCE **antes** del compare-and-swap que puede
      rechazarlos, y con object-lock COMPLIANCE **ni root borra**. Si el diff toca el orden de esa secuencia,
      es hallazgo.

### Paso 6 — Lo que NO se comprueba aquí, y por qué

Reportarlo en `notApplicable` con su razón, en vez de dar un verde que se lea como cobertura:

| No cubierto | Por qué |
|---|---|
| TSA / sellado de tiempo | `requiresTsa()` no tiene llamantes; no se produce ningún nivel ≥ B-T. Diferido en ADR-0023, `BL-4` |
| LTV, CRL/OCSP | Cero código de revocación de certificado de firma en `src/` |
| Trust lists LOTL/TSL | Viven dentro del contenedor DSS, que esta skill **no** audita |
| Certificado por usuario, policy OID, plan de tenant | No existen: el sello se resuelve **por alias** del keystore de DSS, y `SignRequest` lo dice en su docblock |
| Cadena de confianza del keystore de dev | Es autofirmado, así que toda firma valida como `INDETERMINATE / NO_CERTIFICATE_CHAIN_FOUND` — registrado en TASK-018 §4. Es entorno, no defecto del diff |

## Report

```markdown
# eidas-compliance — TASK-NNN

**Status:** {PASS|FAIL|WARN}

## Conforme
- Nivel: PADES_B_B (ADR-0023) · Digest: {caso del enum} · Formato: PAdES

## Hallazgos
- [{categoría}] {fichero} {qué}

## No aplicable en este repo (no es un verde)
- {la fila del Paso 6 que venga al caso}

## Decisiones sin home in-repo
- {lo que haría falta y no está en ningún ADR ni task} → `decision-homeless`
```

## Qué NO hace

- No audita el contenedor EU DSS ni su keystore (es infra).
- No valida formatos que el backend no produce.
- No sube el nivel de firma ni propone subirlo: eso es un ADR.
