---
name: eidas-compliance
description: Valida cumplimiento eIDAS de código de firma electrónica: algoritmos permitidos (EC-P256, SHA-256+), formatos (PAdES/XAdES/CAdES/JAdES), niveles (B-B, B-T, B-LT, B-LTA), sellado de tiempo TSA, LTV, trust lists LOTL/TSL, certificados, integración con EU DSS v6.4, y alineación con las 12 decisiones de project_cloud_signing_decisions.md. Úsalo con /eidas-compliance T{id}. Activar con "compliance eIDAS", "revisar firma", "validar PAdES/XAdES", "check EU DSS".
---

# eIDAS Compliance

Validación de cumplimiento eIDAS. Normalmente invocada por `security-audit` cuando tags incluyen `signing`, `crypto` o `eidas`. Directamente invocable por el usuario para debugging.

## Invocación

```
/eidas-compliance T{id}
```

## Inputs

- `var/task-runner/T{id}/changes.diff`
- `var/task-runner/T{id}/context-digest.md`
- `.md` de la tarea

Memoria y specs cargadas al inicio (obligatorias):
- `memory/project_cloud_signing_decisions.md` (12 decisiones resueltas)
- `Arquitectura/EU DSS - Guía de Integración.md`
- `Arquitectura/Pilares/7. Infraestructura y Compliance.md` § D

## Outputs

- `var/task-runner/T{id}/eidas.report.md`
- JSON:
  ```json
  {"status":"pass|fail","summary":"...","issues":[...],"complianceLevel":"AdES-B-LT","signatureFormat":"PAdES","decisionsEvaluated":{"D1":"pass","D7":"fail"}}
  ```

## Detección inicial

Si tags incluye `signing`/`crypto`/`eidas` pero el diff NO toca código de firma (no hay imports de DSS, no hay clases con "Signature", "Signing", "Sign" en su nombre, no hay operaciones crypto) → `tagMismatches: ["signing"]` o el correspondiente, y devolver `status: pass` (nothing to check).

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

### Paso 11 — Alineación con decisiones del proyecto

Por cada decisión de `project_cloud_signing_decisions.md`:
- [ ] Si es aplicable a esta tarea (revisar tags/context-digest): verificar cumplimiento
- [ ] Si el código diverge: `fail` con referencia a la decisión concreta (ej. "D7 exige EC-P256; código usa SHA1")

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

- Diseño completo: `Implementación/Skills de Ejecución de Tareas/backend/06 - eIDAS Compliance.md`
- Decisiones vinculantes: `memory/project_cloud_signing_decisions.md`
