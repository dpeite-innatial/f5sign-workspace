---
name: eidas-compliance
description: 'Valida cumplimiento eIDAS del código de firma: algoritmos (EC-P256, SHA-256+), formatos (PAdES/XAdES/CAdES/JAdES), niveles (B-B, B-T, B-LT, B-LTA), sellado de tiempo TSA, LTV, trust lists LOTL/TSL, certificados e integración con EU DSS 6.4. Las decisiones vinculantes se leen de sus homes in-repo (ADR-0023 flujo de sellado servidor, ADR-0034 PAdES incremental secuencial, ADR-0016 modelo de almacenamiento WORM) y de las TASK-005/006/017/018, no del repo de diseño. Úsalo con /eidas-compliance T{id}. Activar con "compliance eIDAS", "revisar firma", "validar PAdES/XAdES", "check EU DSS".'
---

# eIDAS Compliance

Validación de cumplimiento eIDAS. La invoca `security-audit-core` cuando **el diff toca firma o cripto** —
`src/F5Sign/SignatureExecution/`, `Foundation/Crypto/`, DSS, PAdES, TSA— y es invocable a mano para depurar.
**Este formato de task no tiene tags**, así que la condición es el diff.

## Invocación

```
/eidas-compliance T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `.md` de la tarea

Memoria y specs cargadas al inicio (obligatorias):
- Las decisiones vinculantes, **en el repo**:
  [`ADR-0023`](../../../docs/adr/ADR-0023-dss-server-signing-seal-flow.md) (flujo de sellado en servidor con
  DSS), [`ADR-0034`](../../../docs/adr/ADR-0034-sequential-incremental-pades.md) (PAdES incremental
  secuencial y sus marcas visibles), [`ADR-0016`](../../../docs/adr/ADR-0016-storage-model.md) (zonas WORM y
  object-lock), y las tasks [`TASK-005`](../../../docs/tasks/TASK-005-dss-pades-signing-slice.md),
  `TASK-006`, [`TASK-017`](../../../docs/tasks/TASK-017-sequential-incremental-pades.md), `TASK-018`
  <!-- OFFREPO: la lista original de "12 decisiones" vivía en `project_cloud_signing_decisions.md`, del repo
  de diseño, y no es alcanzable desde un checkout del backend. Todo lo que de ahí siga vigente está
  restatado en los ADRs citados arriba; si una comprobación necesita una decisión que no está en ninguno de
  ellos, **eso es el hallazgo**: la decisión no tiene home in-repo. -->
- `Arquitectura/EU DSS - Guía de Integración.md`
- `Arquitectura/Pilares/7. Infraestructura y Compliance.md` § D

## Outputs

- `var/task-runner/T{id}/eidas.report.md`
- JSON:
  ```json
  {"status":"pass|fail","summary":"...","issues":[...],"complianceLevel":"AdES-B-LT","signatureFormat":"PAdES","decisionsEvaluated":{"D1":"pass","D7":"fail"}}
  ```

## Detección inicial

Si el diff **no** toca código de firma (sin imports de DSS, sin clases con `Signature`/`Signing`/`Seal` en el nombre, sin operaciones cripto) → `status: pass`, `summary: "nothing to check"`. **Sin `tagMismatches`**: no hay tags que desmentir, y la condición de entrada la evalúa quien delega, sobre el diff.

## Ejecución

### Paso 1 — Determinar formato y nivel declarados

Inspeccionar el código y el context-digest para identificar:
- **Formato**: PAdES, XAdES, CAdES, JAdES o "desconocido"
  - Heurística: PDF → PAdES; XML → XAdES; binario → CAdES; JSON/JWT → JAdES
- **Nivel**: B-B, B-T, B-LT, B-LTA
  - Heurística: buscar constantes/strings tipo `BASELINE_B`, `BASELINE_T`, etc. en las llamadas a DSS

Documentar los valores detectados en el report.

### Paso 2 — Algoritmos criptográficos

- [ ] Firma asimétrica usa EC-P256 (decisión del proyecto D7) o superior (P-384, P-521)
- [ ] Hash: SHA-256 o superior. NO MD5, NO SHA-1
- [ ] Si aparece RSA: ≥ 2048 bits
- [ ] Sin algoritmos deprecados (RIPEMD, DSA)
- [ ] Curvas EC de NIST/Brainpool estándar (no curvas custom)

### Paso 3 — Formatos de firma

- [ ] Formato detectado coincide con tipo de documento
- [ ] Si nivel declarado es B-T/B-LT/B-LTA: la implementación incluye los componentes requeridos del nivel (no solo el string, sino la lógica)
- [ ] Proyecto exige B-LT por defecto (verificar en decisiones): si el código usa nivel inferior, debe haber justificación documentada

### Paso 4 — Sellado de tiempo (TSA)

- [ ] Si nivel ≥ B-T: existe llamada a TSA
- [ ] URL de TSA = la del proyecto (producción: cualificada UE; dev: mock declarado)
- [ ] Fallback: reintento con backoff; no degradar silenciosamente a nivel inferior si TSA falla
- [ ] Timestamp token efectivamente incrustado en la firma (no guardado aparte)

### Paso 5 — LTV

- [ ] Si nivel ≥ B-LT: cadena de certificados, CRLs/OCSP, timestamps adicionales presentes
- [ ] Si nivel ≥ B-LTA: archive timestamps aplicados
- [ ] Revocation info obtenida ANTES de firmar, no después

### Paso 6 — Trust Lists (LOTL/TSL)

- [ ] Validación contra LOTL/TSL vigente
- [ ] Cache con TTL razonable (no permanente; < 24h típicamente)
- [ ] Mecanismo de actualización definido (cron, lazy refresh)

### Paso 7 — Certificados

- [ ] Algoritmo del cert coincide con D7 (EC-P256)
- [ ] Policy OID correcta (qualified / advanced según plan del tenant — comparar con decisión D3)
- [ ] TTL = decisión del proyecto (ver D2)
- [ ] Plan del tenant verificado antes de emitir cert cualificado (Business+, según D3)
- [ ] Certificate chain validation completa (no solo end-entity)
- [ ] Clave privada NUNCA sale del HSM / entorno seguro; solo hash viaja

### Paso 8 — EU DSS (integración)

- [ ] Versión DSS = v6.4 (verificar en llamadas)
- [ ] Parámetros pasados (format, level, digestAlgo, signaturePolicy) coinciden con nivel/formato declarado
- [ ] Respuesta de DSS validada (no confiar ciegamente)
- [ ] Errores mapeados a excepciones de dominio (no HTTP crudos)

### Paso 9 — Hash del documento

- [ ] Se firma el hash, no el documento completo (salvo formato que lo exija)
- [ ] Hash calculado sobre contenido canónico (XML canonicalization, PDF byte-range correcto)
- [ ] Hash NO se recalcula tras modificar el documento

### Paso 10 — Evidencia y auditoría

- [ ] Firma emite evento de dominio (ej. `DocumentSigned`) con metadata completa:
  - timestamp, algoritmo, formato, nivel, certificado (thumbprint), TSA usada
- [ ] Evento se persiste en audit log inmutable si proyecto lo exige

### Paso 11 — Alineación con las decisiones que sí tienen home in-repo

- [ ] Contrastar contra **ADR-0023 / ADR-0034 / ADR-0016** y las TASK-005/006/017/018. Divergencia →
      `fail`, citando el ADR y la sección.
- [ ] ⚑ **Si una comprobación necesita una decisión que no está en ningún ADR ni task, el hallazgo es esa
      ausencia**, no la divergencia: una decisión de firma sin home in-repo no puede vincular a nadie, y
      pedirla es el gate de decisión de `implement-backend` Paso 2b. Reportar como `warn`, categoría
      `decision-homeless`, nombrando qué falta.
- [ ] Los hechos medidos contra el DSS vivo (origen de coordenadas arriba-izquierda, un `imageParameters`
      = un widget = **una firma incremental**) están restatados en TASK-018 §1: usarlos de ahí, y si se
      re-miden, añadir línea fechada en vez de editar la vieja.

### Paso 12 — Adversarios conocidos

- [ ] No downgrade de algoritmo vía parámetro de request del cliente
- [ ] No se acepta una firma sin validarla antes de usarla
- [ ] Signature policy OID aplicada si corresponde

## Manejo de formatos no cubiertos

Si aparece formato no contemplado en las decisiones (ej. JAdES cuando las decisiones solo hablan de PAdES):
- Emitir **WARN** "formato no cubierto por decisiones del proyecto, aplicar defaults de eIDAS y pedir al usuario confirmar"
- NO bloquear (bloquear por decisión no tomada es demasiado rígido en exploración)

## Report

```markdown
# eidas-compliance — T{id}

**Status:** {PASS|FAIL}
**Formato detectado:** {PAdES|XAdES|CAdES|JAdES|n/a}
**Nivel declarado:** {B-B|B-T|B-LT|B-LTA}
**Nivel efectivo:** {idem — marcar si divergen}

## Bloqueantes
- [{categoría}] {fichero:línea} {mensaje}

## Warnings
- [{categoría}] {mensaje}

## Decisiones del proyecto evaluadas
- ✓ D1 (cert por usuario)
- ✓ D3 (plan Business+ para qualified)
- ✗ D7 (algoritmo EC-P256)
- n/a resto (no aplicables a esta tarea)
```

## JSON de retorno

```json
{"status":"fail","summary":"Nivel declarado B-LT pero falta recolección CRL antes de firmar","issues":[{"severity":"fail","category":"ltv","file":"src/Signing/...","message":"..."}],"complianceLevel":"AdES-B-T","signatureFormat":"PAdES","decisionsEvaluated":{"D7":"fail"}}
```

## Coste

Skill más cara del stack (Opus obligatorio). Se minimiza con:
- Solo se invoca si tags lo justifican (task-runner lo controla)
- Memoria y specs cargadas una vez al inicio
- Diff ya filtrado a lo tocado por la tarea
- Si tag mismatch detectado → pass inmediato sin análisis

## Qué NO hace

- No valida crypto genérica no relacionada con firma (security-audit)
- No ejecuta firmas de prueba (lo hacen tests E2E vía task-validate)
- No audita infra del contenedor EU DSS ni configuración runtime
- No valida UX de firma (Signer Workspace)

## Referencias

- <!-- OFFREPO --> Diseño original (prototipo, superado): `Implementación/Skills de Ejecución de Tareas/backend/06 - eIDAS Compliance.md`
- Decisiones vinculantes **in-repo**: [`docs/adr/ADR-0023`](../../../docs/adr/ADR-0023-dss-server-signing-seal-flow.md),
  [`ADR-0034`](../../../docs/adr/ADR-0034-sequential-incremental-pades.md),
  [`ADR-0016`](../../../docs/adr/ADR-0016-storage-model.md), y `docs/tasks/TASK-005|006|017|018`
