// The audit trail's PDF, rendered from the trail's JSON form (schema f5sign.audit-trail/1).
//
// Input: `--input trail=<path>`, the path of the trail JSON. The path resolves against the
// Typst root (`--root`), so `/trail.json` means "<root>/trail.json".
// Output: a PDF/A-3a document when compiled with `--pdf-standard a-3a`. The JSON is attached to
// it as an associated file, byte for byte.
//
// All explanatory wording lives in this file. The JSON carries codes, and this file turns each
// code into Spanish. A code with no label is printed as it is and is never dropped. Rewording is
// a change to this file only; the trail names this file by its SHA-256.
//
// Data values are inserted as text and never evaluated as markup, so a value that looks like
// Typst syntax is printed literally. This file imports nothing.

#let trail-path = sys.inputs.at("trail", default: "/trail.json")
// The bytes are read once. The same bytes are parsed for the page and attached to the PDF, so the
// attachment is exactly the data the page shows.
#let trail-bytes = read(trail-path, encoding: none)
#let trail = json(trail-bytes)

// ---------------------------------------------------------------------------------------------
// Labels. Each group maps a code to its Spanish wording. The groups are also exposed as the
// metadata `<labels>`, so a test can check that every code the platform owns has a label.
// ---------------------------------------------------------------------------------------------

#let labels = (
  // Codes the trail model owns (E&A enums): every case must have a label.
  source: (
    LOG: "registro de eventos",
    LOG_DERIVED: "deducido del registro de eventos",
    BYTES: "contenido del documento firmado",
    ROW: "registro de la plataforma",
    ROW_CURRENT: "valor actual en la plataforma; puede haber cambiado después del acto",
    INTEGRATOR_ASSERTION: "declarado por el integrador; la plataforma no lo verificó",
    BROWSER_REPORT: "declarado por el navegador del firmante",
  ),
  unstated-reason: (
    NOT_PROVIDED_BY_INTEGRATOR: "el integrador no lo facilitó",
    NOT_RECORDED_BY_PLATFORM: "la plataforma no lo registra",
    SOURCE_UNAVAILABLE: "la fuente no respondió al generar este documento",
    CORRECTED_AFTERWARDS: "los datos del destinatario se corrigieron después; este registro no puede decir a qué contacto se envió",
    NOT_REPORTED: "el navegador no lo envió",
    DISCARDED_ILL_FORMED: "enviado mal formado, descartado",
    OUTCOME_NOT_RECORDED: "el paso se activó y el registro no guarda ningún resultado del envío",
  ),
  assurance-tier: (
    ONE_TIME_CODE: "código de un solo uso enviado a un contacto del destinatario",
    LINK_POSSESSION_ONLY: "solo la posesión del enlace; no se verificó nada más",
    INTEGRATOR_ASSERTION: "identidad declarada por el integrador; la plataforma no vio a la persona",
  ),
  signature-mode: (
    SIMPLE: "marcando (sin imagen)",
    DRAW: "dibujando la firma",
    TYPE: "escribiendo el nombre",
  ),
  geolocation-status: (
    GRANTED: "Ubicación concedida",
    DENIED: "Ubicación denegada por el firmante",
    UNAVAILABLE: "Ubicación no disponible en el dispositivo",
    TIMEOUT: "El dispositivo no obtuvo la ubicación a tiempo",
  ),
  discard-reason: (
    WRONG_TYPE: "tipo o formato no válido",
    OUT_OF_RANGE: "fuera de rango",
    TOO_LONG: "demasiado largo",
    MISSING_FIELD: "falta un dato obligatorio",
    NOT_ALLOWED_FOR_STATUS: "coordenadas sin ubicación concedida",
    NOT_READABLE: "documento que el destinatario no puede leer",
    DUPLICATE: "documento repetido",
    TOO_MANY: "demasiadas entradas",
  ),
  mark-form: (
    NAME: "nombre del destinatario",
    EMAIL: "correo electrónico del destinatario",
    RECIPIENT_ID: "identificador del destinatario",
  ),
  check-rule: (
    SIGNED_EXACTLY_ASSIGNED_SET: "Cada destinatario firmó exactamente los documentos que se le asignaron para firmar, y ningún otro.",
    REVISIONS_INCREMENTAL: "Cada firma se añadió a los bytes anteriores del documento, sin reescribir su contenido.",
    EVERY_ARTIFACT_HAS_ITS_FACT: "Cada firma y cada sello que consta en un documento tiene su hecho en este registro.",
    NO_SESSION_BEFORE_CLAIM: "Ninguna participación reclamable tiene hechos de su sesión de firma anteriores a su reclamación.",
    CLAIM_WHILE_SLOT_COULD_ACT: "Cada reclamación se hizo mientras la participación reclamada aún podía actuar.",
    ROW_DIGEST_MATCHES_CUSTODY: "La huella que la plataforma anotó para cada documento coincide con la de los bytes en custodia.",
    ASSERTED_DIGESTS_IN_CHAIN: "Cada huella que el integrador declaró en una firma delegada es la de un estado del documento anterior a la firma del destinatario, y declaró una por cada documento que el destinatario firma.",
    COMMITMENTS_RECOMPUTE: "El compromiso de cada hecho se recalcula a partir de su entrada en el registro de eventos.",
    EVERY_FACT_READABLE: "El contenido de cada hecho se lee como el tipo de hecho que indica.",
    CREATION_AND_SEND_RECORDED: "El registro de eventos del sobre recoge su creación y su envío.",
    ROSTER_RECONCILED: "Cada destinatario declarado al enviar el sobre tiene un resultado en este registro.",
  ),
  check-outcome: (
    HOLDS: "Se cumple",
    FAILS: "No se cumple",
    NOT_EVALUATED: "No evaluada",
  ),
  limitation: (
    REOPENS_NOT_RECORDED: "Solo consta la primera apertura de la sesión de cada destinatario. Las aperturas posteriores no se registran.",
    GEOLOCATION_NOT_CAPTURED: "No se registra la ubicación geográfica de ningún destinatario.",
    DECLARED_SUBJECT_NOT_RECORDED: "No se registra la persona que el integrador declaró detrás de una creación, una reclamación, una anulación, un cierre o una prórroga.",
    CONSENT_TEXT_NOT_RECORDED: "No se registra el texto de consentimiento que se mostró a cada destinatario; solo consta que lo dio.",
    ORDER_WITHIN_RESTORE_EPOCH: "El orden de los hechos es fiable desde la última restauración del registro de eventos a partir de una copia de seguridad, no antes.",
    PLATFORM_CLOCK_TIMES: "Las horas proceden del reloj de la plataforma y no las acredita una autoridad de sellado de tiempo.",
    SHARED_PLATFORM_CERTIFICATE: "Todas las firmas de los destinatarios usan un mismo certificado de la plataforma, por lo que ninguna es una firma avanzada de la persona que firmó.",
    DELIVERY_RECEIPT_NOT_RECORDED: "Que una invitación conste como enviada significa que se entregó al proveedor de envío. La plataforma no registra acuses de recibo del proveedor ni del operador, así que no consta que llegara al destinatario.",
  ),
  invitation-outcome: (
    SENT: "enviada al proveedor de envío",
    FAILED: "no salió: fallaron todos sus canales",
    REFUSED: "el proveedor rechazó este destino",
    NOT_SENT_NO_REACHABLE_CHANNEL: "no se envió: ningún canal podía hacerla llegar",
    DELIVERED_BY_INTEGRATOR: "no la envió la plataforma: el enlace lo entregaba el integrador",
  ),

  // Codes other contexts own: labelled where known, printed as they are otherwise. A test checks
  // that every event type in the code has a label, and that `outcome`, `end-cause`,
  // `release-reason`, `released-by`, `invitation-purpose` and `channel` label exactly their
  // enum's cases. A label for an event type no longer in the code stays, because the log keeps
  // that type's rows.
  event-type: (
    AUTH_CHALLENGE_ISSUED: "Reto de verificación emitido",
    AUTH_GATE_PASSED: "Verificación superada",
    AUTH_HARD_LOCK_REACHED: "Verificación bloqueada por intentos",
    AUTH_OTP_SENT: "Código de un solo uso enviado",
    AUTH_VERIFICATION_PASSED: "Código comprobado",
    CONSENT_RECORDED: "Consentimiento registrado",
    DOCUMENT_ADDED_TO_ENVELOPE: "Documento añadido al sobre",
    DOCUMENT_CONSERVED: "Documento conservado",
    DOCUMENT_READY_TO_SEAL: "Documento listo para sellar",
    DOCUMENT_SEALED: "Documento sellado",
    DOCUMENT_SIGNED: "Documento firmado",
    ENVELOPE_AGREED: "Acuerdo asegurado",
    ENVELOPE_CLOSED_BY_SENDER: "Sobre cerrado por el remitente",
    ENVELOPE_COMPLETED: "Sobre terminado",
    ENVELOPE_CREATED: "Sobre creado",
    ENVELOPE_EXPIRY_EXTENDED: "Caducidad del sobre prorrogada",
    ENVELOPE_READY_TO_SEAL: "Sobre listo para sellar",
    ENVELOPE_ROSTER_DECLARED: "Destinatarios declarados",
    ENVELOPE_SEALED: "Sobre sellado",
    ENVELOPE_SENT: "Sobre enviado",
    ENVELOPE_VOIDED: "Sobre cerrado sin acuerdo",
    IDENTITY_API_CLIENT_REGISTERED: "Cliente de la API registrado",
    IDENTITY_API_KEY_ISSUED: "Clave de la API emitida",
    IDENTITY_TENANT_PROVISIONED: "Titular dado de alta",
    IDENTITY_TENANT_SMS_NOTIFICATIONS_CHANGED: "Avisos por SMS del titular cambiados",
    NOTIFICATION_DELIVERY_FAILED: "Entrega de un aviso fallida",
    NOTIFICATION_DELIVERY_REQUESTED: "Entrega de un aviso solicitada",
    NOTIFICATION_DELIVERY_SENT: "Aviso enviado",
    NOTIFICATION_FAILED: "Aviso fallido",
    NOTIFICATION_REQUESTED: "Aviso solicitado",
    OTP_SEND_LIMITS_CLEARED: "Contadores de envío de códigos reiniciados",
    RECEIPT_ISSUED: "Justificante emitido",
    RECIPIENT_AUTH_REQUIREMENT_CHANGED: "Verificación del destinatario cambiada",
    RECIPIENT_AUTH_UNLOCKED: "Verificación desbloqueada",
    RECIPIENT_CLAIMED: "Participación reclamada",
    RECIPIENT_COMPLETED: "Destinatario completado",
    RECIPIENT_CONTACT_ADDED: "Contacto del destinatario añadido",
    RECIPIENT_CORRECTED: "Datos del destinatario corregidos",
    RECIPIENT_DECLINED: "Rechazo del destinatario",
    RECIPIENT_DELIVERY_FAILED: "Envío al destinatario fallido",
    RECIPIENT_DESTINATION_REFUSED: "Destino del destinatario rechazado",
    RECIPIENT_INVITATION_OUTCOME_RECORDED: "Resultado de la invitación registrado",
    RECIPIENT_INVITATION_RESENT: "Invitación reenviada",
    RECIPIENT_NOTIFICATION_CHANNELS_CHANGED: "Canales de aviso del destinatario cambiados",
    RECIPIENT_PART_ENDED: "Participación del destinatario terminada",
    RECIPIENT_RELEASED: "Destinatario liberado",
    RECIPIENT_RESENDS_UNBLOCKED: "Reenvíos de invitación adicionales permitidos",
    RECIPIENT_SIGNED: "Firma del destinatario",
    RECIPIENT_STEP_ACTIVATED: "Turno del destinatario activado",
    SESSION_COMPLETED: "Sesión de firma completada",
    SESSION_DECLINED: "Rechazo confirmado por el destinatario",
    SESSION_REVOKED: "Sesión de firma revocada",
    SIGNATURE_COMMITTED: "Firma confirmada por el destinatario",
    SIGNING_SESSION_STARTED: "Sesión de firma iniciada",
    STEP_COMPLETED: "Paso completado",
  ),
  auth-method: (
    DIRECT_LINK: "enlace directo",
    MACHINE_KEY_ASSERTED: "clave de máquina del integrador",
    ACCESS_CODE: "código de acceso",
    OTP_SMS: "código por SMS",
    OTP_EMAIL: "código por correo electrónico",
    OTP_WHATSAPP: "código por WhatsApp",
    OTP_VOICE: "código por llamada de voz",
    DEVICE_BIOMETRIC: "biometría del dispositivo",
    FIDO2_WEBAUTHN: "llave de seguridad FIDO2",
    DNIE_NFC: "DNIe por NFC",
    EUDI_WALLET: "cartera europea de identidad digital",
    USER_CERTIFICATE: "certificado de la persona",
    BANK_ID_PSD3: "identificación bancaria",
    VIDEO_KYC_ASYNC: "videoidentificación",
    CLAVE: "Cl@ve",
  ),
  gate: (
    ACCESS: "Acceso",
    SIGNING: "Firma",
  ),
  // The act a signing-gate verification or code served (ADR-0075 section 2.6). A signing-gate entry is
  // labelled by its act, never by the gate, so a decline's never reads as a signature's.
  signing-act: (
    SIGN: "Firma",
    DECLINE: "Rechazo",
  ),
  role: (
    SIGNER: "Firmante",
    APPROVER: "Aprobador",
    REVIEWER: "Revisor",
    VIEWER: "Observador",
    IN_PERSON_HOST: "Anfitrión presencial",
    EDITOR: "Editor",
    CERTIFIED_DELIVERY: "Entrega certificada",
  ),
  workflow: (
    SIGN_ORDERED: "Firma por turnos",
    SIGN_UNORDERED: "Firma sin orden",
    SIGN_MIXED: "Firma mixta",
    SEAL_ONLY: "Solo sello",
  ),
  signing-mode: (
    SINGLE_SEAL: "Un sello al final",
    SEQUENTIAL_PADES: "Firmas PAdES sucesivas",
  ),
  actor-kind: (
    USER: "Usuario",
    SYSTEM: "Sistema",
    RECIPIENT: "Destinatario",
    ANONYMOUS: "Anónimo",
    MACHINE: "Integrador",
  ),
  outcome: (
    AGREED: "Completado con acuerdo",
    NOT_AGREED: "Terminado sin acuerdo",
  ),
  end-cause: (
    SENDER_VOIDED: "el remitente anuló el sobre",
    RECIPIENT_DECLINED: "un destinatario rechazó firmar",
    RECIPIENT_VETOED: "un destinatario de un paso con veto rechazó firmar",
    MINIMUM_UNREACHABLE: "ya no era posible reunir las firmas mínimas de un paso",
    STEP_DEADLINE_MISSED: "venció el plazo de un paso sin el acuerdo que exigía",
    MEMBER_NOT_REACHED: "un paso con veto se cerró por plazo con un destinatario al que la plataforma no llegó",
    EXPIRED: "caducó el sobre",
  ),
  release-reason: (
    NOT_REQUIRED: "destinatario informativo que no abrió el sobre",
    INTEGRATOR_NO_ACT: "su firma estaba delegada en el integrador, que no actuó",
    OPENED_NO_ACT: "superó la verificación de acceso y no firmó ni rechazó",
    DELIVERY_FAILED: "falló el envío de su última invitación",
    UNCLAIMED: "nadie reclamó la participación",
    INTEGRATOR_DELIVERED_NOT_OPENED: "su invitación la entregaba el integrador y no consta que abriera el enlace",
    NO_REACHABLE_CHANNEL: "su paso se activó y ningún canal podía hacerle llegar la invitación",
    NOT_REACHED: "su paso no llegó a activarse, o no consta que la plataforma le hiciera llegar la invitación",
    LINK_EXPIRED: "se le envió una invitación y su enlace había caducado",
    SENT_NO_RESPONSE: "se le envió una invitación, con el enlace vigente, y no superó la verificación de acceso",
  ),
  released-by: (
    STEP_DEADLINE: "venció el plazo de su paso",
    EXPIRY: "caducó el sobre",
    SENDER_CLOSED: "el remitente cerró el sobre con el acuerdo ya asegurado",
    ENVELOPE_CLOSED: "el sobre se cerró",
  ),
  invitation-purpose: (
    INVITATION: "Invitación",
    RESEND: "Reenvío",
  ),
  channel: (
    EMAIL: "correo electrónico",
    SMS: "SMS",
  ),
  route-kind: (
    PLATFORM: "En la plataforma",
    DELEGATED: "Delegada en el integrador",
    CLAIMABLE: "Reclamable",
  ),
  validation-indication: (
    TOTAL_PASSED: "válida",
    PASSED: "válida",
    INDETERMINATE: "indeterminada",
    FAILED: "no válida",
    TOTAL_FAILED: "no válida",
  ),
)

// The label of `code` in `group`, or the code itself when it has none.
#let lbl(group, code) = if code == none { none } else { labels.at(group).at(code, default: code) }

// The label of a gate entry: the signing gate's by the act it served, the access gate's by the gate. A
// trail written before the act existed carries none on the signing gate and reads as the signature.
// A label standing on its own (a cell, a value) starts with a capital; inside a sentence it keeps the
// lower case it is written in. Only labels go through this, never a recorded value.
#let cap(s) = if type(s) == str and s.len() > 0 { upper(s.clusters().first()) + s.clusters().slice(1).join() } else { s }
#let clbl(group, code) = cap(lbl(group, code))

#let gate-lbl(e) = if e.gate == "SIGNING" { lbl("signing-act", if e.at("act", default: none) == none { "SIGN" } else { e.act }) } else { lbl("gate", e.gate) }

// Sources whose statements print their source next to the value, because the value carries a caveat
// (ADR-0072 section 2.4).
#let caveated = ("ROW_CURRENT", "INTEGRATOR_ASSERTION", "LOG_DERIVED")

// ---------------------------------------------------------------------------------------------
// Presentation helpers.
// ---------------------------------------------------------------------------------------------

#let dash = "\u{2014}"
#let gray = luma(95)
#let note(body) = text(fill: gray, size: 0.92em, body)
#let mono(s) = text(font: "DejaVu Sans Mono", size: 0.9em, s)

// "2026-09-21T08:34:28.665196+00:00" -> "2026-09-21 08:34:28". The JSON times are UTC, and the
// page says so once; the attachment keeps the microseconds.
#let when(s) = if s == none { dash } else { s.slice(0, 10) + " " + s.slice(11, 19) }

// A SHA-256 hex digest as four 16-character boxes. No character is added, but a line may break
// between two boxes when the column is narrower than 64 characters.
#let hex(s) = text(font: "DejaVu Sans Mono", size: 7.5pt, s.clusters().chunks(16).map(c => box(c.join())).join())

// A table header row in bold. It repeats on every page the table spans.
#let head(..cells) = table.header(..cells.pos().map(strong))

// Rows of label and value, with a row that is `none` left out.
// The label is centred on its value's height, so a value that spans lines or holds a table stays
// with its label.
// The label column fits the common labels; a long one wraps rather than widening every sheet.
#let kv(..rows) = grid(
  columns: (36mm, 1fr),
  column-gutter: 3mm,
  row-gutter: 2.2mm,
  align: (x, y) => if x == 0 { left + horizon } else { left + top },
  // A row whose label is `none` is a subtitle over the rows that follow it.
  ..rows.pos().filter(r => r != none).map(((k, v)) => if k == none {
    (grid.cell(colspan: 2, pad(top: 2mm, text(size: 7pt, tracking: 0.6pt, weight: "bold", fill: gray, upper(v)))),)
  } else { (text(fill: gray, k), v) }).flatten(),
)

// A small table inside a sheet's value column.
#let mini(columns, header, rows) = table(
  columns: columns,
  align: (x, y) => if header.at(x, default: []) in ([Lo ve], [Lo firma]) { center } else { left },
  inset: (x: 3pt, y: 2pt),
  table.header(..header.map(h => text(size: 7pt, weight: "bold", h))),
  ..rows.flatten().map(c => text(size: 7.5pt, c)),
)

// A contact in a table: the value alone, or why it is missing; the source goes under the table once.
#let contact-cell(c) = if c.stated { c.value } else { note(clbl("unstated-reason", c.reason)) }
#let sources-note(cs) = {
  let sources = cs.filter(c => c != none and c.stated and c.source in caveated).map(c => lbl("source", c.source)).dedup()
  if sources.len() > 0 { note[Contactos: #sources.join("; ").] }
}

// A statement: its value, with the source when the source carries a caveat; or "No consta" with
// the reason. `fmt` turns a stated value into what is printed.
#let stated(s, fmt: v => v) = {
  if s == none { return dash }
  if s.stated {
    let v = fmt(s.value)
    if s.source in caveated [#v #note[(#lbl("source", s.source))]] else [#v]
  } else {
    note[No consta: #lbl("unstated-reason", s.reason).]
  }
}

// A statement inside a group whose subtitle names its source: the value, with no caveat repeated.
#let bare(s, fmt: v => v) = if s == none { dash } else if s.stated { fmt(s.value) } else { note[No consta: #lbl("unstated-reason", s.reason).] }

// An actor: its kind, and its identifier when it has one.
#let actor(a) = if a == none { dash } else if a.id == none [#lbl("actor-kind", a.kind)] else [#lbl("actor-kind", a.kind) #mono(a.id)]

// Short references to parties and documents, in trail order: P1, P2...; D1, D2...
#let party-ref = {
  let refs = (:)
  let seen = (:)
  for p in trail.parties {
    let n = seen.at(str(p.step), default: 0) + 1
    seen.insert(str(p.step), n)
    refs.insert(p.recipient_id, if trail.envelope.step_count > 1 { str(p.step) + "." + str(n) } else { str(n) })
  }
  refs
}
#let document-ref = {
  let refs = (:)
  for (i, d) in trail.documents.enumerate() { refs.insert(d.document_id, "D" + str(i + 1)) }
  refs
}
// An unknown identifier is printed in full, never dropped.
#let pref(id) = if id == none { dash } else { party-ref.at(id, default: id) }
#let dref(id) = if id == none { dash } else { document-ref.at(id, default: id) }

#let env = trail.envelope

// ---------------------------------------------------------------------------------------------
// Document settings.
// ---------------------------------------------------------------------------------------------

#set document(
  title: "Registro de auditoría",
  // Typst takes a string or an array here, never `none`, so an empty label gives no author.
  author: if env.tenant_label.stated { env.tenant_label.value } else { () },
  keywords: ("f5sign", "registro de auditoría", env.envelope_id),
)
#let accent = rgb("#26272b")
#let brand = rgb("#d02a3c")
#let rule = luma(200)
#let zebra = rgb("#f3f5f8")
#let head-fill = rgb("#e4e9f0")
#let ok-ink = rgb("#1b6b3a")
#let ok-soft = rgb("#e6f4ea")
#let bad-ink = rgb("#a4161a")
#let bad-soft = rgb("#fbe9ea")

#set text(font: "DejaVu Sans", size: 8.5pt, lang: "es", region: "ES")
#set par(justify: false, leading: 0.6em)
#set page(
  paper: "a4",
  margin: (x: 16mm, top: 15mm, bottom: 20mm),
  header-ascent: 25%,
  header: context if counter(page).get().first() > 1 {
    set text(size: 7pt, fill: gray)
    grid(columns: (1fr, auto), [Registro de auditoría · #env.title], [Sobre #env.envelope_id])
    v(-2mm)
    line(length: 100%, stroke: 0.4pt + rule)
  },
  footer: context {
    set text(size: 7pt, fill: gray)
    line(length: 100%, stroke: 0.4pt + rule)
    v(-1mm)
    // The section this page belongs to: the last section heading on or before it.
    let page-no = here().page()
    // A page names the section it opens with, or else the one it continues.
    let all = query(heading.where(level: 2))
    let here-on = all.filter(h => h.location().page() == page-no)
    let started = all.filter(h => h.location().page() < page-no)
    let section = if here-on.len() == 0 and started.len() == 0 { [Resumen] } else {
      let h = if here-on.len() > 0 { here-on.first() } else { started.last() }
      [#str(all.position(x => x.location() == h.location()) + 1). #h.body]
    }
    // Within the recipients' section, the step this page shows.
    let steps = query(<step>).filter(m => m.location().page() <= page-no)
    let next-section = all.filter(h => h.location().page() <= page-no)
    if steps.len() > 0 and next-section.len() > 0 and next-section.last().body.text == "Destinatarios" {
      section = [#section · Paso #steps.last().value de #trail.envelope.step_count]
    }
    let docs = query(<document>).filter(m => m.location().page() <= page-no)
    if docs.len() > 0 and next-section.len() > 0 and next-section.last().body.text == "Documentos" {
      section = [#section · D#docs.last().value de #trail.documents.len()]
    }
    grid(columns: (1fr, auto), text(weight: "bold", fill: accent, section), [Página #counter(page).display() de #counter(page).final().first()])
  },
)
#set table(stroke: none, inset: (x: 4pt, y: 3pt), fill: (_, y) => if y == 0 { head-fill } else if calc.even(y) { zebra } else { none })
#show heading: set block(above: 1.4em, below: 0.7em)
#show heading.where(level: 1): it => { pagebreak(weak: true); block(below: 4mm, text(size: 16pt, fill: accent, weight: "bold", it.body)) }
// Each section opens a page, except the short ones that follow the section before them.
#let runs-on = ("Comprobaciones", "Limitaciones", "Generación de este documento")
#show heading.where(level: 2): it => {
  if it.body.text not in runs-on { pagebreak(weak: true) }
  block(above: 6mm, below: 3mm, width: 100%, stroke: (bottom: 0.8pt + accent), inset: (bottom: 1.5mm),
    context {
      let n = query(heading.where(level: 2).before(it.location())).len()
      text(size: 11pt, fill: accent, weight: "bold")[#str(n). #it.body]
    })
}
#show heading.where(level: 3): it => block(above: 4mm, below: 2mm, fill: zebra, width: 100%, inset: (x: 2mm, y: 1.5mm), radius: 2pt, text(size: 9pt, weight: "bold", it.body))
#let cover-heading(body) = block(above: 6mm, below: 2.5mm, text(size: 7pt, tracking: 1pt, weight: "bold", fill: accent, upper(body)))

#pdf.attach(
  // An absolute path resolves against the root, so the embedded name is bare.
  "/registro-" + env.envelope_id + ".json",
  trail-bytes,
  relationship: "data",
  mime-type: "application/json",
  description: "Registro de auditoría en formato legible por máquina (" + trail.schema + ")",
)

#metadata(labels) <labels>

// ---------------------------------------------------------------------------------------------
// The page.
// ---------------------------------------------------------------------------------------------

#let t = trail.terminal
#let agreed = t.outcome.kind == "AGREED"
#let leg-outcome = (SIGNED: "Firmó", DECLINED: "Rechazó", RELEASED: "Liberada sin actuar")
#let leg-at(o) = if o == none { none } else if o.kind == "SIGNED" { o.committed_at } else { o.at }

#let badge(body, ok) = box(
  fill: if ok { ok-soft } else { bad-soft },
  inset: (x: 7pt, y: 4pt),
  radius: 3pt,
  text(fill: if ok { ok-ink } else { bad-ink }, weight: "bold", size: 9pt, body),
)

// The value alone, for the cover; the detail pages carry each caveat.
#let plain(s, fmt: v => v) = if s == none or not s.stated { dash } else { fmt(s.value) }

#let fact-cell(label, value) = block(spacing: 0pt)[
  #text(size: 6.5pt, fill: gray, tracking: 0.4pt, upper(label)) \
  #v(1pt)
  #text(size: 8.5pt, value)
]

// Cover band.
#block(width: 100%, fill: accent, inset: (x: 8mm, y: 7mm), radius: 3pt)[
  #set text(fill: white)
  #grid(columns: (1fr, auto), column-gutter: 6mm, [
  #text(size: 7pt, tracking: 1.2pt, weight: "bold")[REGISTRO DE AUDITORÍA] \
  #v(2pt)
  #text(size: 17pt, weight: "bold", env.title) \
  #v(1pt)
  #text(size: 8.5pt, fill: luma(225))[#if env.tenant_label.stated [#env.tenant_label.value · ]Sobre #mono(env.envelope_id)]
  ], image("logo.svg", height: 5.5mm, alt: "F5Sign"))
]

#v(4mm)

#grid(
  columns: (auto, 1fr),
  column-gutter: 5mm,
  align: horizon,
  badge(lbl("outcome", t.outcome.kind), agreed),
  text(size: 9pt)[el #when(t.at) UTC#if t.outcome.kind == "NOT_AGREED" and t.outcome.ended_by_recipient_id != none [ · rechazado por #pref(t.outcome.ended_by_recipient_id)]#if t.outcome.kind == "NOT_AGREED" and t.outcome.end_reason != none and t.outcome.end_reason.stated [ · motivo: “#t.outcome.end_reason.value”]],
)

#v(4mm)

#block(width: 100%, stroke: 0.5pt + rule, radius: 3pt, inset: (x: 5mm, y: 4mm))[
  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    row-gutter: 4mm,
    column-gutter: 4mm,
    fact-cell("Creado", when(env.created_at)),
    fact-cell("Enviado", when(env.sent_at)),
    fact-cell("Finalizado", when(t.at)),
    fact-cell("Caducidad", plain(env.expiry.expires_at, fmt: when)),
    fact-cell("Flujo", clbl("workflow", env.workflow)),
    fact-cell("Modo de firma", clbl("signing-mode", env.signing_mode)),
    fact-cell("Destinatarios", str(trail.parties.len()) + " en " + str(env.step_count) + " pasos"),
    fact-cell("Documentos", str(trail.documents.len())),
  )
]

#cover-heading[Destinatarios y pasos]

#let mark(o) = if o == none { text(fill: gray, "…") } else if o.kind == "SIGNED" { text(fill: ok-ink, weight: "bold", "✓") } else if o.kind == "DECLINED" { text(fill: bad-ink, weight: "bold", "✗") } else { text(fill: gray, "–") }
#let how(p) = {
  let methods = if p.authentication == none { () } else { p.authentication.gates.map(g => lbl("auth-method", g.method)).dedup() }
  if p.route.kind == "DELEGATED" { "Delegada en el integrador" } else if methods.len() > 0 { cap(methods.join(", ")) } else if p.authentication != none and p.authentication.access_method_at_open != none { lbl("auth-method", p.authentication.access_method_at_open) } else { none }
}
#let person(p) = {
  let o = p.outcome
  let muted = o == none or o.kind == "RELEASED"
  block(width: 100%, fill: if o != none and o.kind == "DECLINED" { bad-soft } else { zebra }, radius: 2pt, inset: (x: 2.5mm, y: 2mm), below: 1.5mm)[
    #set text(fill: if muted { gray } else { black })
    #grid(columns: (auto, 1fr, auto), column-gutter: 1.5mm,
      text(weight: "bold", fill: if muted { gray } else { accent }, pref(p.recipient_id)),
      plain(p.personal.name),
      mark(o),
    )
    #v(-1.5mm)
    #text(font: "DejaVu Sans Mono", size: 5.6pt, fill: gray, p.recipient_id)
    #v(-1mm)
    #text(size: 6.8pt, fill: gray)[#clbl("role", p.role)#let h = how(p); #if h != none [ · #h]#if o != none [ · #if o.kind == "SIGNED" [Firmó] else if o.kind == "DECLINED" [Rechazó] else [Liberado] #when(leg-at(o)).slice(0, 16)]]
  ]
}
#let steps = trail.parties.map(p => p.step).dedup()
#let by-step(n) = trail.parties.filter(p => p.step == n)

#if steps.len() == 1 {
  grid(columns: (1fr, 1fr), column-gutter: 3mm, ..trail.parties.map(person))
} else if steps.len() <= 4 {
  grid(
    columns: steps.map(_ => 1fr).intersperse(5mm),
    ..steps.map(n => stack(
      text(size: 6.5pt, weight: "bold", fill: gray, tracking: 0.6pt, upper("Paso " + str(n))),
      v(1.5mm),
      ..by-step(n).map(person),
    )).intersperse(align(center, pad(top: 7mm, text(fill: gray, size: 11pt, "→")))),
  )
} else {
  for n in steps {
    grid(columns: (16mm, 1fr), column-gutter: 3mm,
      text(size: 6.5pt, weight: "bold", fill: gray, tracking: 0.6pt, upper("Paso " + str(n))),
      grid(columns: (1fr, 1fr), column-gutter: 3mm, ..by-step(n).map(person)),
    )
  }
}

#note[✓ firmó · ✗ rechazó · – liberado sin actuar · … sin terminar. Horas en UTC.]

#note[Nombres y caducidad: valor actual en la plataforma; el detalle indica la fuente de cada dato.]

#cover-heading[Documentos]

#table(
  columns: (auto, 1fr, auto),
  stroke: none,
  fill: (_, y) => if y == 0 { head-fill } else if calc.odd(y) { none } else { zebra },
  head[][Nombre][Huella SHA-256 del documento final],
  ..trail.documents.enumerate().map(((i, d)) => (
    text(weight: "bold", fill: accent, "D" + str(i + 1)),
    d.name,
    if d.final == none { note[sin versión final] } else { text(font: "DejaVu Sans Mono", size: 6.8pt, d.final.hex) },
  )).flatten(),
)

#let holds = trail.checks.filter(c => c.outcome == "HOLDS").len()
#let fails = trail.checks.filter(c => c.outcome == "FAILS")

#cover-heading[Integridad]

#grid(
  columns: (1fr, 1fr),
  column-gutter: 4mm,
  block(width: 100%, fill: if fails.len() == 0 { ok-soft } else { bad-soft }, radius: 3pt, inset: 4mm)[
    #text(weight: "bold", fill: if fails.len() == 0 { ok-ink } else { bad-ink })[#if fails.len() == 0 [✓ ] else [✗ ]#holds de #trail.checks.len() comprobaciones se cumplen] \
    #v(1pt)
    #text(size: 7.5pt)[#if fails.len() == 0 [Los documentos, las firmas y el registro de eventos concuerdan entre sí.] else [No se cumple: #fails.map(c => lbl("check-rule", c.rule)).join("; ")]]
  ],
  block(width: 100%, fill: zebra, radius: 3pt, inset: 4mm)[
    #text(weight: "bold")[Cadena de hechos (#trail.chain.algorithm)] \
    #v(1pt)
    #text(size: 7.5pt)[#trail.chain.leaves hechos encadenados. Raíz:] \
    #text(font: "DejaVu Sans Mono", size: 6.5pt, trail.chain.root.clusters().chunks(32).map(c => box(c.join())).join(linebreak()))
  ],
)

#v(3mm)
#note[
  Este documento está sellado por la plataforma y lleva adjunto el fichero
  #mono("registro-" + env.envelope_id + ".json") con los datos exactos de los que se generó. Todas
  las horas están en UTC. Las páginas siguientes detallan cada destinatario, documento y hecho; las
  limitaciones de este registro (#trail.limitations.len()) se enumeran al final.
]


== Datos del sobre

#let t = trail.terminal
#kv(
  ("Sobre", mono(env.envelope_id)),
  ("Título", env.title),
  ("Titular", [#stated(env.tenant_label) #note[Nombre con el que se dio de alta al titular en la plataforma; no es su razón social.]]),
  ("Creado por", if env.created_by == none { note[No consta.] } else { actor(env.created_by) }),
  ("Creado", if env.created_at == none { note[No consta.] } else { when(env.created_at) }),
  ("Enviado", if env.sent_at == none { note[No consta.] } else { when(env.sent_at) }),
  ("Flujo", clbl("workflow", env.workflow)),
  ("Modo de firma", clbl("signing-mode", env.signing_mode)),
  ("Pasos", str(env.step_count)),
  ("Caducidad", stated(env.expiry.expires_at, fmt: when)),
  ("Caducidad al enviar", stated(env.expiry.first_expires_at, fmt: when)),
  ("Prórrogas", if env.expiry.extensions.len() == 0 { [Ninguna.] } else {
    stack(spacing: 1.5mm, ..env.expiry.extensions.map(x => [#when(x.previous_expires_at) → #when(x.expires_at), por #actor(x.extended_by), el #when(x.at), hecho nº #str(x.position) del registro]))
  }),
  ("Estado final", [*#lbl("outcome", t.outcome.kind)* el #when(t.at), hecho nº #str(t.position) del registro]),
  if t.agreed_at != none { ("Acuerdo asegurado", when(t.agreed_at)) },
  if t.closed_at != none { ("Cerrado", when(t.closed_at)) },
  if t.outcome.kind == "AGREED" and t.outcome.ended_by != none { ("Cerrado por el remitente", actor(t.outcome.ended_by)) },
  if t.outcome.kind == "NOT_AGREED" and t.outcome.ended_by != none { ("Anulado por el remitente", actor(t.outcome.ended_by)) },
  if t.outcome.kind == "NOT_AGREED" and t.outcome.ended_by_recipient_id != none { ("Rechazado por", pref(t.outcome.ended_by_recipient_id)) },
  if t.outcome.kind == "NOT_AGREED" { ("Causa", stated(t.outcome.end_cause, fmt: c => clbl("end-cause", c))) },
  if t.outcome.kind == "NOT_AGREED" and t.outcome.end_reason != none { ("Motivo indicado", stated(t.outcome.end_reason)) },
  if t.outcome.kind == "NOT_AGREED" {
    ("Firmaron antes del cierre", if t.outcome.signed_before_close.len() == 0 { [Nadie.] } else { t.outcome.signed_before_close.map(pref).join(", ") })
  },
  ("Sesiones revocadas antes del final", if t.revocations.len() == 0 { [Ninguna.] } else { stack(spacing: 1.5mm, ..t.revocations.map(r => [#pref(r.recipient_id), #when(r.at)])) }),
)

== Comprobaciones

#note[
  Cada comprobación se evalúa sobre las fuentes de este registro. Una comprobación que no se cumple
  se indica aquí y no impide emitir el registro.
]

#table(
  columns: (1fr, 26mm),
  head[Comprobación][Resultado],
  ..trail.checks.map(c => (
    lbl("check-rule", c.rule),
    if c.outcome == "FAILS" { text(fill: rgb("#a4161a"), strong(clbl("check-outcome", c.outcome))) } else { clbl("check-outcome", c.outcome) },
  )).flatten(),
)

== Destinatarios

// The route: how the party was meant to sign, and what happened on that route.
#let route-rows(r) = {
  let rows = (("Vía de firma", clbl("route-kind", r.kind)),)
  if r.kind == "DELEGATED" {
    if r.commit == none {
      rows.push(("Firma delegada", note[El integrador no registró ninguna firma.]))
    } else {
      let c = r.commit
      rows += (
        ("Registrada por", actor(c.by)),
        ("IP del servidor del integrador", stated(c.observed_server_ip)),
        ("Navegador del servidor del integrador", stated(c.observed_server_user_agent, fmt: v => text(size: 7.5pt, v))),
      )
    }
  } else if r.kind == "CLAIMABLE" {
    // "Acceso al reclamar" describes a claim, so a slot nobody claimed states none (ADR-0083 section 2.9).
    if r.claim != none {
      rows.push(("Acceso al reclamar", if r.gate_was_open [Abierto: bastaba el enlace.] else [Con verificación.]))
    }
    rows.push(("Reclamación", if r.claim == none { note[Nadie reclamó la participación.] } else [#when(r.claim.at), por #actor(r.claim.by)]))
  }
  rows
}

// What the party could do with one assigned document: see it, sign it, or both. A party can be
// assigned to sign a document it is not shown.
#let assignment(a) = if a.signs and a.visible { "lo ve y lo firma" } else if a.signs { "lo firma sin verlo" } else if a.visible { "lo ve sin firmarlo" } else { "ni lo ve ni lo firma" }

// A gate's methods as a change of the party's gates declares them; `empty` names a gate that asks for none.
#let methods(list, empty) = if list.len() == 0 { empty } else { list.map(m => lbl("auth-method", m)).join(", ") }

// Each change of the party's gates before they entered, in log order (ADR-0083 section 2.9).
#let change-rows(changes) = changes.map(c => ("Cambio de verificación", [
  #when(c.at), por #actor(c.by): acceso #methods(c.access_before, "abierto") → #methods(c.access_after, "abierto")\; firma #methods(c.signing_before, "ninguna") → #methods(c.signing_after, "ninguna")#if c.access_opened [ #note[El acceso pasó de verificado a abierto.]]#if c.signing_dropped [ #note[La firma dejó de pedir verificación.]]
]))

// Each addition of a contact the party had none of, in log order; only the kinds, never a value (ADR-0084 section 2.9).
#let addition-rows(additions) = additions.map(c => ("Contacto añadido", [
  #when(c.at), por #actor(c.by): #c.added.map(k => if k == "email" { "correo electrónico" } else { "teléfono" }).join(", ")
]))

#let authentication-rows(a) = {
  if a == none { return (("Autenticación", note[El destinatario no llegó a abrir su sesión.]),) }
  (
    ("Primera apertura", when(a.first_opened_at)),
    // A session behind a declared access gate opens with no method: the recipient had proved nothing
    // yet. What it took to get in is the first access verification, shown with its method and time.
    ("Acceso", if a.access_method_at_open == none {
      let first = a.gates.filter(g => g.gate == "ACCESS")
      if first.len() > 0 {
        [*Con #lbl("auth-method", first.first().method):* tuvo que verificarse antes de ver los documentos; lo hizo a las #when(first.first().at).]
      } else {
        [*Con verificación:* se le pidió verificarse antes de ver los documentos y no llegó a hacerlo.]
      }
    } else if a.access_method_at_open == "DIRECT_LINK" {
      [*Solo con el enlace:* no se le pidió verificarse.]
    } else [*#upper(lbl("auth-method", a.access_method_at_open).first())#lbl("auth-method", a.access_method_at_open).slice(1).*]),
  )
}

// A declared text, set apart and printed as it was given.
#let verbatim(body) = block(inset: (left: 3mm), stroke: (left: 0.8pt + luma(150)), body)

#let reservation(r) = {
  if r.kind == "NOT_CAPTURED" {
    [No consta ninguna reserva. El canal de firma no recoge reservas, o registró el campo vacío, que no indica si el destinatario declaró no tenerlas. Su ausencia aquí no significa que el destinatario firmara sin reservas.]
  } else if r.kind == "DECLARED_NONE" {
    [El destinatario declaró no formular reservas. Si firmó como consignatario de la mercancía, la Ley 15/2009 (art. 60.1) presume, salvo prueba en contrario, que la mercancía llegó como se describe.]
  } else if r.kind == "WRITTEN" {
    [Reservas escritas por el destinatario, en su literalidad:
      #verbatim(r.text)]
  } else {
    r.kind
  }
}

// How the party's leg ended. A release is not an act: the envelope closed the leg without one.
#let outcome-rows(a, delegated: false) = {
  if a == none { return (("Resultado", note[No consta en este registro cómo terminó la participación del destinatario.]),) }
  if a.kind == "DECLINED" {
    return (
      ("Rechazo", when(a.at)),
      ("Motivo del rechazo, en su literalidad", verbatim(a.reason)),
    )
  }
  if a.kind == "RELEASED" {
    return (
      ("Liberada sin firmar ni rechazar", when(a.at)),
      ("Lo que consta del destinatario", clbl("release-reason", a.release_reason)),
      ("Lo que la liberó", clbl("released-by", a.released_by)),
    )
  }
  (
    ("Firma confirmada", when(a.committed_at)),
    ("Consentimiento", stated(a.consent, fmt: when)),
    ("Reservas", if a.reservation.kind != "NOT_CAPTURED" { reservation(a.reservation) } else if delegated {
      note[No constan: el integrador no envió reservas; la plataforma no sabe si se le ofreció indicarlas.]
    } else [*Sin reservas.* Se le ofreció indicarlas al firmar y no indicó ninguna.]),
  )
}

// One invitation: when, which, what became of it, and by what channel to which contact when it names one.
#let invitation(i) = [#when(i.at): #lbl("invitation-purpose", i.purpose), #lbl("invitation-outcome", i.outcome)#if i.channel != none [, por #lbl("channel", i.channel)]#if i.contact != none [, a #stated(i.contact)]]

#let personal-rows(p, recipient-id, route) = {
  let rows = (
    ("IP al firmar", stated(p.commit_ip)),
    ("Navegador al firmar", stated(p.commit_user_agent, fmt: v => text(size: 7.5pt, v))),
  )
  if p.at("decline_ip", default: none) != none {
    rows.push(("IP al rechazar", stated(p.decline_ip)))
  }
  if p.at("decline_user_agent", default: none) != none {
    rows.push(("Navegador al rechazar", stated(p.decline_user_agent, fmt: v => text(size: 7.5pt, v))))
  }
  if p.at("accept_language", default: none) != none {
    rows.push(("Idiomas del navegador", stated(p.accept_language)))
  }
  // Everything the integrator declared on a delegated act, under one subtitle that names the source.
  let c = if route.kind == "DELEGATED" { route.commit } else { none }
  if c != none or p.asserted != none {
    rows.push((none, "Declarado por el integrador · la plataforma no lo verificó"))
    if c != none {
      rows += (
        ("Método de verificación", bare(c.asserted_auth_method)),
        ("Consentimiento", when(c.asserted_consented_at)),
        ("Huellas de los documentos", stack(spacing: 1.5mm, ..c.asserted_digests.map(d => [#dref(d.document_id): #hex(d.digest.hex)]))),
      )
    }
    if p.asserted != none {
      rows += (
        ("Persona", bare(p.asserted.subject)),
        ("IP", bare(p.asserted.ip)),
        ("Navegador", bare(p.asserted.user_agent, fmt: v => text(size: 7.5pt, v))),
      )
    }
  }
  let r = p.at("reported", default: none)
  let nothing-sent(st) = not st.stated and st.reason == "NOT_REPORTED"
  if r != none and r.discarded.len() == 0 and nothing-sent(r.geolocation) and nothing-sent(r.reading) and r.device.values().all(nothing-sent) {
    // Nothing of the group was sent: one line, not one "not reported" row per field.
    rows.push(("Declarado por el navegador del firmante", note[No consta: el navegador no envió ningún dato.]))
  } else if r != none {
    // What the signer's browser declared at the act (TASK-045). Its source is stated once, in the heading, not on every row.
    rows.push((none, "Declarado por el navegador del firmante"))
    rows.push(("Ubicación", stated(r.geolocation, fmt: g => if g.status == "GRANTED" {
      let pos = g.position
      [#calc.round(pos.latitude, digits: 5), #calc.round(pos.longitude, digits: 5) (± #pos.accuracy_m m), #when(pos.captured_at)]
    } else { clbl("geolocation-status", g.status) })))
    let d = r.device
    rows += (
      ("Zona horaria", stated(d.timezone)),
      ("Idiomas", stated(d.languages, fmt: v => v.join(", "))),
      ("Pantalla", stated(d.screen, fmt: v => [#v.width × #v.height @ #v.pixel_ratio×])),
      ("Plataforma", stated(d.platform)),
      ("Versión de la plataforma", stated(d.platform_version)),
      ("Modelo", stated(d.model)),
      ("Táctil", stated(d.touch, fmt: v => if v { "Sí" } else { "No" })),
      ("Reloj del dispositivo", stated(d.client_clock_at_act, fmt: when)),
      ("Lectura", stated(r.reading, fmt: es => if es.len() == 0 { dash } else {
        stack(spacing: 1.5mm, ..es.map(e => {
          let doc = trail.documents.find(x => x.document_id == e.document_id)
          let name = if doc == none { dref(e.document_id) } else { doc.name }
          [#name — página #e.max_page_seen/#e.pages_total, #if e.read_to_end [hasta el final] else [sin llegar al final], visible #if e.visible_ms < 60000 [#calc.round(e.visible_ms / 1000) s] else [#calc.round(e.visible_ms / 60000, digits: 1) min]]
        }))
      })),
    )
    if r.discarded.len() > 0 {
      rows.push(("Descartado", stack(spacing: 1.5mm, ..r.discarded.map(x => [#mono(x.member): #clbl("discard-reason", x.reason)]))))
    }
  }
  rows
}

// The rows that tell how the recipient was reached and verified, in the order it happened.
#let reach-rows(p) = {
  let a = p.authentication
  let rows = ((none, "Invitación y verificación"),)
  rows.push({
    let p = p.personal
    ("Invitaciones", stated(p.invitations, fmt: v => if v.len() == 0 [Ninguna; no correspondía invitar a este destinatario] else {
      // A sent invitation is the ordinary case and says nothing more; any other outcome is stated in the
      // contact cell, in red when it did not go out.
      mini((31mm, 20mm, 40mm, 1fr), ([Fecha (UTC)], [Tipo], [Canal], [Contacto]), v.map(i => (
        when(i.at),
        clbl("invitation-purpose", i.purpose),
        if i.channel == none { dash } else { clbl("channel", i.channel) },
        {
          let contact = if i.contact == none { none } else { contact-cell(i.contact) }
          if i.outcome == "SENT" { if contact == none { dash } else { contact } } else {
            let failed = i.outcome in ("FAILED", "REFUSED", "NOT_SENT_NO_REACHABLE_CHANNEL")
            let what = text(fill: if failed { bad-ink } else { gray }, clbl("invitation-outcome", i.outcome))
            if contact == none { what } else [#contact \ #what]
          }
        },
      )))
      sources-note(v.map(i => i.contact))
    }))
  })
  rows += authentication-rows(a)
  rows.push({
    let recipient-id = p.recipient_id
    let p = p.personal
    // Each send is one AUTH_OTP_SENT fact of the recipient, in log order, so its time is that fact's.
    ("Códigos enviados", if p.contacts.len() == 0 { dash } else {
      let sent = trail.facts.filter(f => f.type == "AUTH_OTP_SENT" and f.recipient_id == recipient-id)
      mini((31mm, 20mm, 40mm, 1fr), ([Fecha (UTC)], [Verificación], [Método], [Contacto]), p.contacts.enumerate().map(((i, c)) => (
        if sent.len() == p.contacts.len() { when(sent.at(i).occurred_at) } else { dash },
        cap(gate-lbl(c)), clbl("auth-method", c.method), contact-cell(c.contact),
      )))
      sources-note(p.contacts.map(c => c.contact))
    })
  })
  if a != none {
    rows.push(("Verificaciones", if a.gates.len() == 0 { dash } else {
      mini((31mm, 20mm, 1fr), ([Fecha (UTC)], [Verificación], [Método]), a.gates.map(g => (when(g.at), cap(gate-lbl(g)), clbl("auth-method", g.method))))
    }))
    rows.push(("Nivel de garantía", if a.tier == none { dash } else { clbl("assurance-tier", a.tier) }))
  }
  rows
}

#let party-sheet(p) = [
  === #pref(p.recipient_id) · #plain(p.personal.name)#if p.role_label.stated [ · #p.role_label.value]

  #kv(
    ("Identificador", mono(p.recipient_id)),
    {
      let p = p.personal
  ("Nombre", stated(p.name))
    },
    ("Paso", str(p.step)),
    ("Papel en el sobre", clbl("role", p.role)),
    ("Etiqueta del integrador", stated(p.role_label)),
    // The same table as a document's "Asignado a", seen from the recipient: one row per document.
    ("Documentos asignados", if p.assignments.len() == 0 { dash } else {
      let tick(b) = if b { text(fill: ok-ink, weight: "bold", "✓") } else { text(fill: gray, "—") }
      mini((8mm, 1fr, 52mm, 14mm, 14mm), ([], [Documento], [Id], [Lo ve], [Lo firma]), p.assignments.map(a => {
        let d = trail.documents.find(x => x.document_id == a.document_id)
        (
          text(weight: "bold", fill: accent, dref(a.document_id)),
          if d == none { dash } else { d.name },
          text(font: "DejaVu Sans Mono", size: 6.4pt, a.document_id),
          align(center, tick(a.visible)),
          align(center, tick(a.signs)),
        )
      }))
    }),
    ..route-rows(p.route),
    ..change-rows(p.auth_requirement_changes),
    ..addition-rows(p.contact_additions),
    ..reach-rows(p),
    (none, "Resultado"),
    ..outcome-rows(p.outcome, delegated: p.route.kind == "DELEGATED"),
    ..personal-rows(p.personal, p.recipient_id, p.route),
  )
]

// A sheet that fits on a page is never split: it goes where it fits, or whole to the next page.
// One taller than a page has to break anyway, so it stays where it starts.
#let whole(body) = context {
  let height = measure(block(width: page.width - 32mm, body)).height
  if height <= page.height - 40mm { block(breakable: false, width: 100%, body) } else { body }
}

// Each step after the first opens a page, so a step reads as one turn of the flow. The marker
// tells the footer which step a page belongs to.
#for (i, n) in trail.parties.map(p => p.step).dedup().enumerate() {
  if trail.envelope.step_count > 1 {
    if i > 0 { pagebreak() }
    [#metadata(n) <step>]
    block(above: 6mm, below: 1mm, text(size: 7pt, tracking: 1pt, weight: "bold", fill: gray, upper("Paso " + str(n) + " de " + str(trail.envelope.step_count))))
  }
  for p in trail.parties.filter(p => p.step == n) { whole(party-sheet(p)) }
}

== Documentos

// A certificate: its subject, and the SHA-256 that names the exact certificate.
#let certificate(c) = [#c.subject #linebreak() #hex(c.sha256)]

// The fact number of a log position, or a note that no fact records it.
#let fact-no(p) = if p == none { note[No consta en el registro.] } else [Hecho nº #str(p) del registro]

#let seal-rows(s) = {
  if s == none { return (("Sello de la plataforma", note[El documento no tiene sello de la plataforma.]),) }
  let rows = (("Sello de la plataforma", fact-no(s.position)),)
  if not s.observation.stated {
    return rows + (("Lectura del sello", stated(s.observation)),)
  }
  let o = s.observation.value
  rows + (
    ("Nivel leído del sello", mono(o.level_read_back)),
    ("Certificado del sello", certificate(o.certificate)),
    ("Sellos de tiempo", if o.timestamps.len() == 0 { note[El sello no lleva sello de tiempo.] } else {
      stack(spacing: 1.5mm, ..o.timestamps.map(ts => [#ts.authority.subject, #when(ts.at)]))
    }),
    ("Validación del sello", [
      #clbl("validation-indication", o.validation_indication)
      #note[(#o.validation_indication#if o.validation_sub_indication != none [, #o.validation_sub_indication]; a la fecha de generación de este documento)]
    ]),
  )
}

// The party a revision names, and the time of the fact at a log position.
#let party-of(id) = trail.parties.find(p => p.recipient_id == id)
#let fact-at(pos) = if pos == none { none } else { trail.facts.find(f => f.position == pos) }
#let fact-when(pos) = { let f = fact-at(pos); if f == none { dash } else { when(f.occurred_at) } }

// How a revision was signed, in short labels: the declared mode, what the PDF shows, the image's digest.
// A drawn or typed signature always carries an image, so the mode is not repeated in the mark.
#let signed-mode = (SIMPLE: "Firma con un clic", DRAW: "Firma dibujada", TYPE: "Firma escrita")
#let how-signed(r) = {
  let parts = ()
  if r.signature_mode != none and r.signature_mode.stated {
    parts.push(signed-mode.at(r.signature_mode.value, default: clbl("signature-mode", r.signature_mode.value)))
  }
  let image = r.mark_image_sha256 != none and r.mark_image_sha256.stated
  if r.mark == none { parts.push("Firma invisible") } else if r.mark.stated {
    let m = r.mark.value
    parts.push(if m.name_drawn and image [Se ve: nombre e imagen] else if m.name_drawn [Se ve: nombre] else [Se ve: imagen])
    if m.delegated { parts.push("Puesta por el integrador") }
  }
  parts.join(" · ")
}

// One row of a document's history: what happened and by whom, how, and the digest after it; the step
// and the time sit in their own columns, centred on the row.
// What a seal validation means in words, beside the validator's own codes.
#let validation-words(o) = if o.validation_indication == "TOTAL_PASSED" [Válido.] else if o.validation_sub_indication == "NO_CERTIFICATE_CHAIN_FOUND" [
  No se pudo confirmar: el certificado del sello no enlaza con una autoridad de confianza.
] else [#clbl("validation-indication", o.validation_indication).]

#let validation-short(o) = if o.validation_indication == "TOTAL_PASSED" [Válida.] else if o.validation_sub_indication == "NO_CERTIFICATE_CHAIN_FOUND" [No confirmada: certificado sin autoridad de confianza.] else [#clbl("validation-indication", o.validation_indication).]

// A signature's type as read back from the PDF: its PAdES level and its timestamps, if any.
#let signature-type(o) = [#o.level_read_back · #if o.timestamps.len() == 0 [sin sello de tiempo] else [#o.timestamps.map(ts => [sello de tiempo de #ts.authority.subject, #when(ts.at)]).join("; ")]]

#let history-row(label, who, at, how, digest, id: none, image: none, cert: none, obs: none, obs-missing: false, fact: none) = (
  text(weight: "bold", label),
  [
    // The id follows the name when the line has room, and drops whole to the next line when not.
    #who#if id != none [ #h(1.5mm) #box(text(font: "DejaVu Sans Mono", size: 6.2pt, fill: gray, id))]
    #if how != none and how != "" [ \ #text(size: 7.5pt, fill: gray, how)]
    // The digests, labelled and aligned: the signature image's when the mark drew one, then the document's.
    #let tag(t) = text(size: 6.6pt, weight: "bold", fill: gray, t)
    #let hash(h) = text(font: "DejaVu Sans Mono", size: 6.6pt, h)
    #v(-1.6mm)
    #grid(columns: (auto, auto), column-gutter: 2mm, row-gutter: 0.9mm,
      ..if fact != none { (tag[Registro], text(size: 6.6pt)[Hecho nº #str(fact)]) } else { () },
      ..if obs != none { (
        tag[Tipo], text(size: 6.6pt, signature-type(obs)),
        tag[Validación], text(size: 6.6pt, [#validation-short(obs) #text(fill: gray)[(#obs.validation_indication)]]),
      ) } else if obs-missing { (
        // Prototype only: a signature's read-back is not kept by the trail yet (data task).
        tag[Tipo y validación], text(size: 6.6pt, fill: gray)[No consta: el registro aún no guarda la lectura de cada firma.],
      ) } else { () },
      ..if cert != none { (tag[Certificado], text(size: 6.6pt, cert.subject), tag[SHA-256 certificado], hash(cert.sha256)) } else { () },
      ..if image != none { (tag[SHA-256 imagen], hash(image)) } else { () },
      tag[SHA-256 documento], hash(digest),
    )
  ],
  text(size: 7.5pt, fill: gray, at),
)


// Each document after the first opens a page; the marker tells the footer which one it is.
#for (i, d) in trail.documents.enumerate() [
  #if i > 0 { pagebreak() }
  #metadata(i + 1) <document>
  === D#str(i + 1): #d.name

  // Who the document is assigned to: one row per recipient, with what each may do with it.
  #let assigned = trail.parties.map(p => (p, p.assignments.find(a => a.document_id == d.document_id))).filter(((p, a)) => a != none)
  #kv(
    ("Identificador", mono(d.document_id)),
    // The file as it was uploaded: kind, size, pages, and when and by whom. Shown once the trail keeps it.
    ..{ let f = d.at("file", default: none); if f == none { () } else { (
      ("Archivo", [#f.original_name #text(fill: gray)[· #f.mime_type · #calc.round(f.size_bytes / 1024) KB · #f.pages #if f.pages == 1 [página] else [páginas]]]),
      ("Subido", [#when(f.uploaded_at), por #actor(f.uploaded_by)]),
      ("Tamaño final", [#calc.round(f.final_size_bytes / 1024) KB]),
    ) } },
    ("Asignado a", if assigned.len() == 0 { dash } else {
      let tick(b) = if b { text(fill: ok-ink, weight: "bold", "✓") } else { text(fill: gray, "—") }
      mini((8mm, 1fr, 52mm, 14mm, 14mm), ([], [Destinatario], [Id], [Lo ve], [Lo firma]), assigned.map(((p, a)) => (
        text(weight: "bold", fill: accent, pref(p.recipient_id)),
        plain(p.personal.name),
        text(font: "DejaVu Sans Mono", size: 6.4pt, p.recipient_id),
        align(center, tick(a.visible)),
        align(center, tick(a.signs)),
      )))
    }),
  )


  #block(above: 4mm, below: 2mm, text(size: 7pt, tracking: 0.6pt, weight: "bold", fill: gray, upper("Historia del documento")))
  #let last = if d.seal != none { d.seal.after.hex } else if d.revisions.len() > 0 { d.revisions.last().after.hex } else { d.uploaded.hex }
  #table(
    columns: (17mm, 1fr, auto),
    inset: (x: 4pt, y: 3pt),
    align: (x, y) => if x == 1 { left + top } else { left + horizon },
    fill: (_, y) => if calc.odd(y) { zebra } else { none },
    ..history-row("Subido", [Documento original], "", none, d.uploaded.hex),
    ..d.revisions.map(r => {
      let p = party-of(r.by_recipient_id)
      history-row(
        "Firma " + str(r.seq),
        [#text(weight: "bold", fill: accent, pref(r.by_recipient_id)) #if p != none { plain(p.personal.name) }],
        fact-when(r.position),
        how-signed(r),
        r.after.hex,
        id: r.by_recipient_id,
        fact: r.position,
        cert: if r.signer_certificate.stated { r.signer_certificate.value } else { none },
        // Only once each signature keeps its read-back, as the seal does; until then this is empty.
        obs: { let o = r.at("observation", default: none); if o != none and o.stated { o.value } else { none } },
        obs-missing: r.at("observation", default: none) == none,
        image: if r.mark != none and r.mark_image_sha256 != none and r.mark_image_sha256.stated { r.mark_image_sha256.value },
      )
    }).flatten(),
    ..if d.seal != none {
      let o = if d.seal.observation.stated { d.seal.observation.value } else { none }
      history-row("Sello", [Sello de la plataforma], fact-when(d.seal.position), none, d.seal.after.hex,
        fact: d.seal.position, obs: o, cert: if o != none { o.certificate } else { none })
    } else { () },
    ..if last != d.final.hex { history-row("Final", [Documento final], "", none, d.final.hex) } else { () },
  )
  #note[«SHA-256 documento» es la huella del PDF completo tal como quedó tras ese paso; «SHA-256 imagen», la de la imagen de firma que el destinatario envió al firmar. Nombres: valor actual en la plataforma. El modo de firma lo declara el cliente; la plataforma no distingue una imagen dibujada de una escrita. La huella de cada imagen de firma se registró en el acto; el PDF la guarda recodificada, así que no se comprueba contra el documento.]

]

== Hechos registrados

#block(below: 3mm)[
  #text(size: 7pt, tracking: 0.6pt, weight: "bold", fill: gray, upper("Destinatarios de este registro"))
  #v(-1mm)
  #mini((8mm, 1fr, 52mm, 26mm), ([], [Nombre], [Id], [Papel]), trail.parties.map(p => (
    text(weight: "bold", fill: accent, pref(p.recipient_id)),
    plain(p.personal.name),
    text(font: "DejaVu Sans Mono", size: 6.4pt, p.recipient_id),
    clbl("role", p.role),
  )))
]

#note[
  Todos los hechos del registro de eventos del sobre hasta su estado final, en el orden del
  registro. El compromiso identifica el contenido de cada hecho; aquí se muestran sus 16 primeros
  caracteres y el adjunto lo lleva completo.
]

#text(size: 7.5pt, table(
  columns: (auto, auto, 1fr, auto, auto, auto),
  head[Hecho nº][Fecha y hora][Hecho][Destinatario][Actor][Compromiso],
  ..trail.facts.map(f => (
    align(right, str(f.position)),
    when(f.occurred_at),
    clbl("event-type", f.type),
    pref(f.recipient_id),
    clbl("actor-kind", f.actor.kind),
    mono(f.commitment.slice(0, calc.min(16, f.commitment.len()))),
  )).flatten(),
))

== Cadena de integridad

#kv(
  ("Algoritmo", mono(trail.chain.algorithm)),
  ("Hechos encadenados", str(trail.chain.leaves)),
  ("Raíz", hex(trail.chain.root)),
)

#if trail.chain.algorithm == "sha256-chain/1" [
  #note[
    Para comprobar la raíz: sea r#sub[0] = SHA-256("f5sign.audit-trail/1" seguido del identificador
    del sobre en minúsculas). Para cada hecho, en orden de número y, a igual número, en orden de
    compromiso, r#sub[i] = SHA-256(r#sub[i-1] seguido del número del hecho como entero de 8 bytes
    con signo, big-endian, la longitud del compromiso como entero de 4 bytes sin signo, big-endian,
    y el compromiso). La raíz es el último r#sub[i].
  ]
]

== Limitaciones

#for l in trail.limitations [
  - #lbl("limitation", l.code)
]
#if trail.parties.any(p => p.route.kind == "DELEGATED" and p.outcome != none and p.outcome.kind == "SIGNED" and p.outcome.reservation.kind == "NOT_CAPTURED") [
  - En una firma delegada, la plataforma no sabe si el sistema del integrador ofreció indicar reservas; que no consten no significa que se firmara sin ellas.
]

== Generación de este documento

#let g = trail.generation
#kv(
  ("Generado", when(g.at)),
  ("Versión de la aplicación", mono(g.app_version)),
  ("Versión de Typst", mono(g.typst_version)),
  ("Plantilla (SHA-256)", hex(g.template_hash)),
  ("Formato de los datos", mono(trail.schema)),
)
