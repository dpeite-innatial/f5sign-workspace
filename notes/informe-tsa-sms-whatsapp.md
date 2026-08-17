# Informe de proveedores — TSA cualificada + SMS/WhatsApp/OTP para F5Sign

> **Fecha de consulta:** julio 2026 · **Divisa:** los internacionales publican en USD (≈ 1,08–1,15 USD/€) · Precios sin IVA salvo indicación · Todos cambian sin previo aviso.
> **Método:** investigación multi-fuente con verificación adversarial 3-votos (23 claims confirmados, 2 refutados). Nivel de confianza indicado por proveedor.

---

## 0. Resumen ejecutivo (TL;DR)

Son **dos decisiones independientes** que conviene no mezclar:

1. **Sellado de tiempo (Bloque A):** las grandes (FNMT, Uanataca, Firmaprofesional) van por presupuesto, pero **dos QTSA españolas SÍ publican precio abierto**: **Mensatek** (sello cualificado 0,029–0,045€/sello, tarifa completa por tramos) y **Lleida.net** (desde 0,03€/sello). Si basta RFC 3161 no cualificado, DigiCert es gratis.
2. **Mensajería — SMS + WhatsApp + OTP (Bloques B y C):** **recomendación: Twilio.** Una sola integración cubre SMS, WhatsApp Business API y OTP con caída automática entre canales, con el precio más transparente del mercado. Esendex es más barato por SMS suelto, pero no unifica los tres canales.

---

## BLOQUE A — Sellado de tiempo cualificado (TSA, RFC 3161)

> Twilio **no** interviene aquí: no es autoridad de sellado de tiempo. Esta decisión es separada de la de mensajería.

### A.1 — QTSA cualificadas eIDAS (Trusted List UE)

| Proveedor | Cualificada eIDAS | Modelo de precio | ¿Precio abierto? | Fuente |
|---|---|---|---|---|
| **FNMT-RCM** (oficial, sincronizada con ROA) | ✅ QTSA | Contrato; tarifa a discreción de FNMT | ❌ Bajo petición | [cert.fnmt.es](https://www.cert.fnmt.es/catalogo-de-servicios/sellado-de-tiempo) · [TyC TSA (PDF)](https://sede.fnmt.gob.es/documents/10445900/10556270/TyC_TSA.pdf) |
| **Uanataca** | ✅ QTSA | Prepago (bono) o postpago mensual; "zero investment, pay per use" | ❌ Bajo petición | [Servicio](https://web.uanataca.com/en/services/time-stamping) · [FAQ facturación](https://web.uanataca.com/en/faqs/time-stamping/how-does-the-billing-service-work) |
| **Firmaprofesional** (grupo Logalty) | ✅ QTSP | Suscripción anual (Internet o TSU on-premise) | ❌ Bajo petición | [Sello de tiempo cualificado](https://firmaprofesional.com/servicios/sello-de-tiempo-cualificado/) |
| **ANF AC** | ✅ QTSP | Contacto/demo (su tarifario público omite el timestamping) | ❌ Bajo petición | [Time-stamps](https://anf.es/en/solutions/time-stamps/) |
| **GlobalSign** (variante *Qualified*) | ✅ QTSP UE+UK | Contact-sales | ❌ Bajo petición | [Timestamp service](https://www.globalsign.com/en/timestamp-service) |
| **Mensatek** ⭐ | ✅ qTSP eIDAS (verificar en TL) | Bono de créditos prepago; sello cualificado propio = 1 créd. | ✅ **Sí, en €** — **0,029–0,045€/sello** | [Precios](https://www.mensatek.com/precios.php?s=4) · [API sellado](https://www.mensatek.com/api-sellado-de-tiempo.html) |
| **Lleida.net** ⭐ | ✅ QTSA eIDAS | Bono de sellos (tramos exactos tras registro) | ◑ **Precio de partida publicado: desde 0,03€/sello** | [Sello de tiempo](https://www.lleida.net/en/esignature-and-econtracting/timestamp) · [Compra](https://www.lleida.net/en/esignature-and-econtracting/timestamp-purchase) |

**Corrección importante:** la mayoría de QTSA no publican precio, **pero Mensatek y Lleida.net sí** (total y parcialmente). Ya no es cierto que la comparativa en €/sello cualificado solo se cierre pidiendo oferta — hay dos referencias abiertas.

**Detalle de tarifa abierta — Mensatek** (sin coste de alta, créditos no caducan, pago por uso). Su **sello cualificado propio = 1 crédito**; el **sello FNMT vía Mensatek = 2 créditos**:

| Bono | Créditos | €/crédito | €/sello cualificado (1 créd.) | €/sello FNMT (2 créd.) |
|---|---|---|---|---|
| 5€ | 111 | 0,045€ | **0,045€** | 0,090€ |
| 50€ | 1.190 | 0,042€ | 0,042€ | 0,084€ |
| 100€ | 2.564 | 0,039€ | 0,039€ | 0,078€ |
| 500€ | 14.286 | 0,035€ | 0,035€ | 0,070€ |
| 1.000€ | 30.303 | 0,033€ | 0,033€ | 0,066€ |
| 5.000€ | 172.413 | 0,029€ | **0,029€** | 0,058€ |

**Lleida.net:** QTSA cualificada, precio de partida **"desde 0,03€/sello"** publicado; los tramos por volumen exactos se ven al seleccionar pack / registrarse en su tienda (existe pack inicial de 70 créditos por 9,99€). Precio de partida ≈ igual o mejor que Mensatek a alto volumen.

> ⚠️ **A verificar antes de contratar:** confirmar la razón social exacta de Mensatek y Lleida.net como QTSP de sellado en la [Trusted List UE](https://eidas.ec.europa.eu/efda/tl-browser/) / lista del Ministerio (Mensatek se declara qTSP propio desde 2021; conviene comprobar que el sello de 1 crédito es el cualificado y no el resold de FNMT). El resto: FNMT = oficial/hora legal ROA; Uanataca = pre/postpago flexible sin inversión inicial; Firmaprofesional = suscripción anual + opción on-premise (todos bajo presupuesto).

### A.2 — TSA RFC 3161 estándar (no cualificada)

| Proveedor | Cualificada eIDAS | Modelo | ¿Precio abierto? | Fuente |
|---|---|---|---|---|
| **DigiCert** | ❌ No (RFC 3161 + Adobe AATL) | Endpoint público `http://timestamp.digicert.com` | ✅ **Gratis / incluido** con sus certificados | [KB DigiCert](https://knowledge.digicert.com/general-information/rfc3161-compliant-time-stamp-authority-server) |
| **GlobalSign** (AATL/Code Signing) | ❌ No (RFC 3161 + AATL) | Incluido "sin coste adicional" con Document Signing Certificates | ❌ Sin rate card independiente | [Timestamp service](https://www.globalsign.com/en/timestamp-service) |
| **Sectigo / SSL.com** | ❌ No | La investigación no devolvió precio publicado; suelen ofrecer endpoint RFC 3161 gratuito ligado a sus certificados — **a verificar** | ⚠️ No confirmado | — |

> ⚠️ **Decisión de fondo:** ¿F5Sign necesita sello **cualificado eIDAS** (validez a largo plazo con presunción legal reforzada, que es lo que exige el punto 2.2) o basta un **RFC 3161 fiable**? Si basta el estándar → DigiCert gratis. Si necesitas cualificado (recomendable para firma con validez legal robusta en la UE) → no hay atajo: contratar QTSA con alta previa.

---

## BLOQUE B — SMS a España

| Proveedor | Origen | Precio SMS a España | Modelo | ¿Precio abierto? | Fuente |
|---|---|---|---|---|---|
| **Twilio** ⭐ | 🌍 US | **$0,0875/SMS** (≈0,076–0,081€) | Postpago pay-as-you-go | ✅ Sí (USD) | [twilio.com/sms/pricing/es](https://www.twilio.com/en-us/sms/pricing/es) |
| **Esendex** | 🇪🇸 ES | 0,096€ → 0,034€/SMS por tramos | Bono prepago | ✅ Sí, en € | [esendex.es/precios](https://www.esendex.es/precios/) |
| **LabsMobile** | 🇪🇸 ES | ~0,045€ → 0,04€ por volumen (vía calculadora) | Prepago, pack mín. 9€ | ◑ Semi | [labsmobile.com](https://www.labsmobile.com/en/purchase-sms-price) |
| **Plivo** | 🌍 US | $0,0716–0,0877 según operador | Postpago | ✅ Sí (USD) | [plivo.com/sms/pricing/es](https://www.plivo.com/sms/pricing/es/) |
| **Sinch** | 🌍 | ~0,06€ (fuente independiente) | Postpago | ◑ Media confianza | *(sent.dm)* |
| **Vonage (Nexmo)** | 🌍 | ~0,081€ (no verificable abiertamente) | Postpago | ❌ Bajo petición | [vonage.com](https://www.vonage.com/communications-apis/messages/pricing/) |
| **Infobip** | 🌍 | Solo rango €0,008–0,28; España negociada | Postpago/volumen | ❌ Bajo petición | *(no publica España)* |

**Tramos Esendex (referencia de precio abierto más bajo):** 500→0,096€ · 1.000→0,069€ · 2.500→0,051€ · 5.000→0,044€ · 10.000→0,039€ · 25.000→0,036€ · 50.000→0,034€/SMS.

**OTP con API dedicada — Twilio Verify:** **$0,05 por verificación exitosa + coste del canal** (para España, +~$0,0875 del SMS) → ≈$0,14/OTP-SMS exitoso. Gestiona reintentos, plantillas y multicanal. [Verify pricing](https://www.twilio.com/en-us/verify/pricing).

> ⚠️ Precios por **segmento de 160 caracteres** (Unicode/tildes → 70). Twilio/Plivo/Vonage cotizan en USD/postpago; Esendex/LabsMobile en €/prepago.

---

## BLOQUE C — WhatsApp Business API (cruce omnicanal)

**Sí es viable una sola integración para SMS + WhatsApp.** Contexto: desde el **1-jul-2025** Meta cobra **por mensaje/plantilla** (no por conversación); la tarifa la fija el **país destino (España)**. Cada proveedor factura **tarifa Meta (pass-through) + su fee**. Tarifas Meta España aprox. 2026: **authentication/OTP ≈ 0,0166€**, marketing ≈ 0,0509€, *service* (ventana 24h) **gratis**. ⚠️ Cifras Meta de fuentes de terceros datadas (may/jun-2026), no rate card oficial.

| Proveedor | WhatsApp API | OTP omnicanal (WA→SMS auto) | Precio WhatsApp España | Fuente |
|---|---|---|---|---|
| **Twilio** ⭐ | ✅ | ✅ Verify (auto, plantillas auto) | Fee $0,005/msg + Meta — **calculadora pública** | [pricing](https://www.twilio.com/en-us/whatsapp/pricing) · [Verify WA](https://www.twilio.com/docs/verify/whatsapp) |
| **Infobip** | ✅ | ✅ 2FA con fallback auto a SMS/email | Bajo petición | [WhatsApp OTP](https://www.infobip.com/whatsapp-business/otp) |
| **Vonage** | ✅ | ✅ Verify v2 (cascada declarativa SMS→Voz→WA→Email) | Fee ~desde 0,0001€ + Meta; bajo petición | [Verify](https://www.vonage.com/communications-apis/verify/) |
| **Bird** (MessageBird) | ✅ | ✅ failover auto WA→SMS | Fee ~$0,001–0,005 + Meta; bajo petición | [pricing](https://bird.com/en-us/pricing/whatsapp) |
| **Sinch** | ✅ | ✅ Verification con fallback auto | Bajo petición | [WhatsApp OTP](https://www.sinch.com/products/apis/verification/whatsapp-otp/) |
| **Plivo** | ✅ | ✅ Verify (SMS/Voz/WA, fee API $0) | Solo EE.UU. publicado; España no | [pricing](https://www.plivo.com/whatsapp-message/pricing/) |
| **AWS End User Messaging** | ✅ | ❌ OTP gestionado **solo SMS** | Fee $0,005/msg + Meta (publicado) | [pricing](https://aws.amazon.com/end-user-messaging/pricing/) |
| **Esendex** 🇪🇸 | ✅ (Meta BSP) | ◑ WhatsApp aún no combinable con SMS en misma petición | Bajo petición | [WhatsApp API](https://www.esendex.es/api/whatsapp-api/) |
| **Afilnet** 🇪🇸 | ✅ | ◑ OTP multicanal en 1 API (fallback auto a confirmar) | Bajo petición (OTP gratis) | [WhatsApp](https://www.afilnet.com/es/whatsapp-business/) |
| **360NRS / Altiria / Mensatek** 🇪🇸 | ✅ | ◑/❌ (Altiria: OTP solo SMS) | Bajo petición (Mensatek: 0,3 créd./msg) | [360NRS](https://www.360nrs.com/whatsapp-business-api) |
| **LabsMobile / Gateway360 / Instasent** 🇪🇸 | ❌ | ❌ (solo SMS) | — | — |

---

## RECOMENDACIÓN DE MENSAJERÍA → Twilio

Para el conjunto **SMS + WhatsApp + OTP**, la opción recomendada es **Twilio**, por cuatro razones que ningún otro proveedor reúne a la vez:

1. **Una sola integración para todo.** Programmable Messaging + Content API cubren SMS y WhatsApp con el mismo SDK, y **Twilio Verify** añade OTP con **caída automática WhatsApp → SMS** y creación automática de las plantillas de autenticación. Un solo contrato, un solo SDK, un solo panel → menos código y menos mantenimiento que integrar dos proveedores.
2. **El precio más transparente del mercado.** Único con **calculadora y CSV públicos** tanto de SMS ($0,0875 a España) como de WhatsApp (fee plano $0,005/msg + pass-through Meta). El resto de proveedores de WhatsApp dejan la cifra España **bajo petición**, lo que dificulta presupuestar.
3. **OTP maduro y probado.** Verify gestiona reintentos, rate-limiting, expiración y multicanal de fábrica; enviar el OTP primero por WhatsApp (≈0,0166€, más barato que el SMS) y caer a SMS si falla **abarata el OTP** frente a SMS puro, sin desarrollo extra.
4. **Documentación y madurez.** La mejor documentación y estabilidad de API del comparativo, decisivo para integrar rápido en F5Sign.

**Coste realista (para el informe):** Twilio es ~2× más caro por SMS suelto que Esendex por volumen (≈0,08€ vs 0,034€). La contrapartida es que **una sola integración** para SMS + WhatsApp + OTP ahorra desarrollo, mantenimiento y un segundo contrato; y enrutar OTP por WhatsApp primero recorta el coste por verificación. Para el volumen de OTP/notificaciones de una plataforma de firma, esa diferencia unitaria es marginal frente al ahorro de ingeniería.

**Cuándo reconsiderar:** si el volumen de SMS a España fuera muy alto y **solo** se necesitara SMS (sin WhatsApp ni OTP gestionado), **Esendex** (precio abierto en €, 0,034€/SMS por volumen) sería más barato. En cuanto entra WhatsApp + OTP unificados, Twilio compensa.

---

## Recomendación por escenario (visión conjunta)

| Escenario | TSA (Bloque A) | Mensajería (Bloques B+C) |
|---|---|---|
| **Validez legal máxima (cualificado eIDAS)** | Precio abierto ya publicado: **Mensatek** (0,029–0,045€/sello) o **Lleida.net** (desde 0,03€). Comparar contra presupuesto de **FNMT** (oficial/ROA) y **Uanataca** | **Twilio** (SMS + WhatsApp + OTP) |
| **Basta RFC 3161 estándar** | **DigiCert** gratis | **Twilio** |
| **Minimizar coste SMS puro, alto volumen** | según requisito legal | **Esendex** (si no hace falta WhatsApp/OTP unificado) |

---

## Pendiente de pedir (queda abierto)

1. **Verificar en la [Trusted List UE](https://eidas.ec.europa.eu/efda/tl-browser/)** que Mensatek y Lleida.net figuran como QTSP de sellado y que su sello barato es el cualificado (no un resold). Si confirma → ya tienes precio abierto de referencia (0,029–0,045€/sello) para negociar con FNMT/Uanataca.
2. **Precios en € por sello** (bonos/cuota de alta) de **FNMT, Uanataca, Firmaprofesional** — pedir presupuesto para comparar contra Mensatek/Lleida.net.
3. **Confirmar categoría de sello** que necesita F5Sign: cualificado eIDAS vs RFC 3161 estándar.
4. **Coste/requisitos del Sender ID alfanumérico** para España en Twilio (gratis como tipo de número; verificar registro).
5. **Cerrar precio WhatsApp España en Twilio** con la calculadora oficial según categorías (auth/utility/marketing) y volumen estimado.

---

### Nota de fiabilidad

Confianza **alta**: FNMT/Uanataca/Firmaprofesional/GlobalSign (bajo petición), DigiCert (gratis), **Mensatek** (tarifa TSA abierta, cifras verificadas en su web), **Lleida.net** (precio de partida 0,03€ verificado en su web), Twilio (SMS, Verify, WhatsApp), Esendex, Plivo. Confianza **media**: Sinch (~0,06€), Vonage (~0,081€), Infobip, y todas las tarifas Meta de WhatsApp (fuentes de terceros datadas). **A confirmar (no verificado en fuente oficial):** el estatus QTSP exacto de Mensatek/Lleida.net en la Trusted List UE y cuál de sus sellos es el cualificado. Refutados en verificación: un listado multi-proveedor de sent.dm y la afirmación de que Infobip no publica ningún rango.
