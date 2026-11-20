# TASK-045 — What the signer's browser reports travels with the act, and the audit trail states it

<!-- OFFREPO: this record is built on a proposal the `f5sign-signer` session left in the workspace notes,
`notes/HANDOFF-signing-evidence-capture-2026-09-21.md`, not committed on 2026-09-21. It records the maintainer's
choice of that day: *"el gps se tiene que enviar siempre que sea posible. Y tenemos que recoger todo lo posible
en plan ip, user agent, y demás cosas que puedan ayudar"*, narrowed from a list of four to geolocation (with its
denial), device context and document reading, and excluding the canvas/WebGL fingerprint. On 2026-10-13 the
maintainer widened the scope to the decline and to the audit trail's rendering.

It also relies on facts about the sibling repository `f5sign-signer`, read again on 2026-10-13 at its `develop`
tip `f2e2469`:
- `app/composables/useGeolocation.ts` builds a fallback of `{lat: 0, lng: 0, acc: 50000, source: GEO_IP}` when
  there is no fix, with no Geo-IP lookup behind it;
- `useDeviceFingerprint.ts` computes `webgl_hash` and `canvas_hash`;
- `useDocumentReadThrough.ts` keeps the deepest page per document and no visible time;
- the rich evidence flow is gated by `hasRichSignFlow()` (`useBackendCapabilities.ts`) and is off against the
  real backend.

Every fact used is restated where it is used. -->
<!-- OFFREPO: §2's statement about the proxy relies on the sibling repository `f5sign-infra`, read on
2026-10-13: `docker-compose.prod.yml` publishes Caddy's ports 80 and 443 directly, with Caddy's own
certificates, and `docker/caddy/Caddyfile` hands requests to PHP-FPM over a FastCGI transport. So `REMOTE_ADDR`
is the connecting client, and nothing in the compose sits in front of Caddy. Whatever an operator puts in front
of the host is not visible there, which is why §4 D9 makes declaring a proxy an explicit, tested act. -->

| Field | Value |
|-------|-------|
| **Status** | **Implemented on `feat/browser-reported-evidence`**, 2026-10-14 — full suite green on the branch merged with `develop` (`ace588b4`, which carries TASK-031): OK (7215 tests, 81141 assertions), with lint, deptrac and PHPStan clean, under the `wt-backend` lane of this worktree. Infection on the 44 changed `src/` files at `bd380545`: covered-MSI 95 %, MSI 87 %; every mutant left on a changed line is equivalent and named in §7. One intermittent failure seen once and not reproduced (`StorageLifecycleScenarioTest`, a bucket version still present after the promotion; it passed alone and on the merged run), unrelated to this diff. Left out: the rendered PDF's printed text has no test ([BL-416](../BACKLOG.md)), and the new session columns have no purge step ([BL-415](../BACKLOG.md)). |
| **Type** | **Forward build.** The commit and the decline gain an optional block of evidence that the browser reports. The server records one more value it observes itself, records its observed values at the decline too, and states how it trusts a proxy. The audit trail states all of it. |
| **Why** | The signer has captured geolocation and device data for months, and against the real backend all of it is discarded. `POST /api/v1/signing/commit` and `POST /api/v1/signing/decline` have no member for it, and the rich evidence route (`POST /signing/session/evidence`) does not exist. So the signer switched capture off where nothing receives it — yet the maintainer wants it to travel. A decline today records no IP address and no user agent on the session row ([BL-286](../BACKLOG.md)). |
| **Builds on** | Reused unchanged: [ADR-0055](../adr/ADR-0055-delegated-signature.md) (provenance in the name: what we observed is never mixed with what we were told), [ADR-0019](../adr/ADR-0019-database-schema-conventions.md) §5 (fixed shapes to typed columns, bounded collections to `jsonb`), [ADR-0075](../adr/ADR-0075-the-signing-gate-is-answered-on-the-act.md) §2.4 (a wrong signing code commits its charge). Extended inside its own foreseen slot: [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) §2.4 (*"the browser-reported evidence of TASK-045"* is a listed empty slot), §2.5 and §2.6. |
| **Scope** | **The normal commit route and the decline route.** The delegated route already carries its own `asserted_*` evidence (ADR-0055) and gains nothing. **The audit trail's model, its JSON form and its PDF state the evidence.** Out of scope:<br>• the canvas/WebGL fingerprint (§4 D2);<br>• stroke biometrics, which need their own consent ([TASK-053](TASK-053-the-recipients-drawn-signature-on-their-mark.md) receives the strokes without keeping them);<br>• enciphering (§4 D6);<br>• an anchor in the event log (§4 D7);<br>• server-side Geo-IP ([BL-274](../BACKLOG.md));<br>• checking a reported page count against the document's real one (§4 D8);<br>• the per-signer evidence document ([TASK-047](TASK-047-per-signer-evidence-document.md)), which will read what this task puts in the trail. **The `f5sign-signer` change is not in this repository**: this task writes its handoff (§3 #8). |
| **Decision record** | **[ADR-0032](../adr/ADR-0032-evidence-pii-custody.md) governs, and is `Proposed`.**<br>• Its target (decision 2) is evidence PII ciphered inline in the event log. Its own Counterpoint 3 records that what ships today is the interim: each producer keeps evidence on its own row, in the clear, as `signing_session.signer_ip` does.<br>• This task adds to that interim, by the maintainer's decision, and moves nothing about the target.<br>**[ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) is `Accepted`**, and this task fills a slot it lists; the additions are additive under its versioning rule (§4 D12), so its text gains them and no new ADR is written.<br>▶ **What would force one**: putting any of this into the event log, enciphering it before ADR-0032 is realized, deriving a location server-side from the IP, or changing the meaning of an existing trail JSON key. |
| **Delivery bar** | A commit carrying an `evidence` block with a granted position, a device context and a reading entry answers 200. The session row then holds each value under its `reported_*` column, and the issued audit trail states them with the browser as their source. A decline carrying the same block answers as a decline does today, and its row and trail hold the same values plus the IP address and user agent observed at the decline. A commit or decline carrying an **ill-formed** block **still answers as it would without one**, drops the ill-formed parts and records each drop by name and reason (§4 D4). |
| **Siblings** | [TASK-059](TASK-059-the-trail-shows-how-each-invitation-travelled.md) (not started on 2026-10-13; its record is being revised on `feat/trail-invitations`) will add to the same `PartyPersonal`, `TrailJson` and `trail.typ`; whichever is built second rebases on the other. TASK-044, TASK-046, TASK-052 and TASK-053 have landed on `develop`, so this task builds on their `CommitSignatureRequest`, `DeclineSignatureRequest` and signing-gate placement as they stand. |

---

## 1. Why this task exists

The rich signing screen (`/sign`) asks the browser for a position and for device details when the signer
presses *Firmar*. Against the real backend it sends none of it, because nothing receives it, and since
2026-09-21 it no longer captures it there at all.

On 2026-09-21 the maintainer asked for the opposite: the position should travel whenever the browser can give
it, and so should anything else that helps. From a list of four, they chose three:
- **geolocation**, including the fact that it was denied, which is evidence too;
- **device context**;
- **document reading**.

They left out the canvas/WebGL fingerprint. On 2026-10-13 they added two things: a decline carries the same
evidence as a signature, and the audit trail states it, in this task rather than later.

What makes this a design and not a field list is the difference between **observed** and **reported**:
- the server observes `signer_ip`, `signer_user_agent` and (new) `Accept-Language` itself;
- everything in the block is declared by the browser, and a tampered client can send any coordinate.

A record that mixes the two cannot be separated afterwards. ADR-0055 already paid that lesson once, with
`asserted_*`.

## 2. What already exists (reuse, do not rebuild)

- **Observed by the server at the commit**, with nothing asked of the client:
  - `signer_ip`, from `CommitSignatureController`'s `$request->getClientIp()`;
  - `signer_user_agent`, from the `User-Agent` header;
  - consent and its instant (`ConsentRecorded`, `completed_at`);
  - the method proved at each gate (`access_method_executed`, `AuthGatePassed`, `AuthVerificationPassed`);
  - the method chosen (`chosen_auth_method`), which ADR-0054 §2.6 keeps apart from the one proved.

  The values among them that are columns — `consent_given`, `completed_at`, `access_method_executed`,
  `chosen_auth_method`, `signer_ip`, `signer_user_agent` — are stored in the clear on `session.signing_session`;
  the others are facts in the event log.
- **At the decline the session row records neither the IP address nor the user agent.**
  `DeclineSignatureController` reads both, but passes them only to the signing gate, which stores them on the
  auth attempt when a gate is declared. `SigningSession::decline()` takes neither. So the trail shows no IP for a
  party who declined.
- **The provenance precedent.** `AssertedEvidence` (ADR-0055) keeps what an integrator *asserts* in its own
  `asserted_*` columns, added by `Version20260831000001`, beside and never inside the observed ones.
  - Its fixed-shape members are typed columns; `asserted_document_hashes` is a bounded `jsonb`.
  - It implements `Pii`, which classifies without enciphering.
  - [BL-214](../BACKLOG.md) records that its plaintext is a decision, not an omission.
- **The readable set is not on the act's path yet.**
  - `RecipientAuthContext`, which the commit and the decline read, carries the **signable** set
    (`signableDocumentDigests`, `signableDocumentSet`) and `documentIsWithheld`, not the documents the
    recipient may **read**.
  - The read side computes those (`EnvelopeContextView::documentsAccessibleTo()`).
  - So checking a `reading` entry means `RecipientAuthContextReader` gains one member: a wider read over a crossing
    that already exists, not a new dependency.
- **The audit trail reads Session's row values through one contract query.**
  `Session/Contract/Query/CommitEvidenceReader` returns a `CommitEvidenceView` per recipient (observed IP and
  user agent, and the delegated route's assertions). `TrailAssembler` puts them in `PartyPersonal`, the one
  `Pii` group of a party (ADR-0072 §2.6), and `TrailJson` writes them as `personal.commit_ip` and
  `personal.commit_user_agent`. `trail.typ` prints them as *"IP al firmar"* and *"Navegador al firmar"*. Every
  value carries its provenance: a `Source` (`LOG`, `ROW`, `INTEGRATOR_ASSERTION`, …) or an `UnstatedReason`.
  The trail's schema is `f5sign.audit-trail/1`; `TrailJson`'s docblock says adding a field keeps it, and
  removing a field or changing its meaning moves it.
- **`trusted_proxies` is not configured.**
  - `framework.trusted_proxies` falls back to `%env(default::SYMFONY_TRUSTED_PROXIES)%` (see
    `config/reference.php`), and no `.env*` file sets that variable.
  - Today that is harmless: Caddy is the edge and hands requests to PHP-FPM over FastCGI, so `REMOTE_ADDR` is the
    client (see the OFFREPO note).
  - The day a CDN or a load balancer is put in front, `signer_ip` becomes the proxy's address on every
    signature, with no error.
- **No unknown member is refused.** Request DTOs ignore unknown keys ([BL-177](../BACKLOG.md)). A signer that
  sends `evidence` to a backend that predates this task loses it silently, exactly as today.

## 3. What gets built

1. **Wire.** `POST /api/v1/signing/commit` and `POST /api/v1/signing/decline` gain the same optional `evidence`
   object. **Absent, `null`, or any member absent means "not collected"** and is always valid. Its members:
   - **`geolocation`** — taken whole: if any field is ill-formed, the whole member is dropped.
     - `status`: one of `GRANTED`, `DENIED`, `UNAVAILABLE`, `TIMEOUT`.
     - With `GRANTED`, and **only** with it, all four of:
       - `latitude`: a number in [-90, 90];
       - `longitude`: a number in [-180, 180];
       - `accuracy_m`: a number in [0, 1 000 000];
       - `captured_at`: an RFC 3339 date-time with an offset.
   - **`device`** — taken field by field: an ill-formed field is dropped, and the others are kept. Every field
     is optional:
     - `timezone`: 1 to 64 characters of `[A-Za-z0-9_+/-]` (an IANA name, checked for shape, not looked up);
     - `languages`: a list of 1 to 10 strings, each 2 to 35 characters of `[A-Za-z0-9-]` (BCP 47 tags);
     - `screen`: `width` and `height`, integers in [1, 32 768], and `pixel_ratio`, a number in (0, 16]. Taken
       whole, as one field;
     - `platform`: 1 to 32 characters;
     - `platform_version`: 1 to 32 characters;
     - `model`: 0 to 64 characters (user-agent client hints report an empty model on desktops);
     - `touch`: a boolean;
     - `client_clock_at_act`: an RFC 3339 date-time with an offset.

     Text fields take printable characters only; a control character makes the field ill-formed.
   - **`reading`** — a list of at most 100 entries, taken entry by entry. Each entry has:
     - `document_id`: a document the recipient may read (§4 D8);
     - `pages_total`: an integer in [1, 10 000];
     - `max_page_seen`: an integer in [1, `pages_total`];
     - `read_to_end`: a boolean;
     - `visible_ms`: an integer in [0, 86 400 000] (24 hours).

     An entry that repeats a `document_id` already kept is dropped.
   - The block is taken **leniently**, outside `#[MapRequestPayload]`'s all-or-nothing validation, as `mixed` on
     the request DTO, the shape `biometric_data` already uses (§4 D4).
2. **Domain.** A `ReportedEvidence` value object in Session, implementing `Pii`, beside `AssertedEvidence`. It is
   built from what survived normalization, and it carries the drops: a list of `{member, reason}`, where
   - `member` is a path from a closed set: `evidence`, `geolocation`, `device.<field>` for each device field,
     `reading`, `reading[<index>]`;
   - `reason` is one of `WRONG_TYPE`, `OUT_OF_RANGE`, `TOO_LONG`, `MISSING_FIELD`, `NOT_ALLOWED_FOR_STATUS`,
     `NOT_READABLE`, `DUPLICATE`, `TOO_MANY`.

   Neither ever holds a submitted value.
3. **Persistence.** One migration on `session.signing_session`, RLS unchanged, all columns nullable, written in
   the act's unit of work (§4 D1):

   | Column | Type | Holds |
   |---|---|---|
   | `reported_geo_status` | `text` (the PHP enum's four values) | `geolocation.status` |
   | `reported_geo_latitude` | `double precision` | |
   | `reported_geo_longitude` | `double precision` | |
   | `reported_geo_accuracy_m` | `double precision` | |
   | `reported_geo_captured_at` | `timestamptz` | |
   | `reported_device_timezone` | `text` | |
   | `reported_device_languages` | `jsonb` (array of strings) | |
   | `reported_device_screen_width` | `integer` | |
   | `reported_device_screen_height` | `integer` | |
   | `reported_device_screen_pixel_ratio` | `double precision` | |
   | `reported_device_platform` | `text` | |
   | `reported_device_platform_version` | `text` | |
   | `reported_device_model` | `text` | |
   | `reported_device_touch` | `boolean` | |
   | `reported_client_clock_at` | `timestamptz` | `device.client_clock_at_act` |
   | `reported_reading` | `jsonb` (array of entries) | |
   | `reported_evidence_dropped` | `jsonb` (array of `{member, reason}`) | the drops |
   | `signer_accept_language` | `text` | observed, §3 #4 |

   No CHECK carries the status's value set or the rule that the four coordinate columns are all set with
   `GRANTED` and all null otherwise: under ADR-0019 §7 both are domain invariants, so `ReportedEvidence` holds
   them and its hydration refuses a row that breaks them. `reported_evidence_dropped` is null when nothing was sent and `[]` when a block was sent and
   nothing was dropped, so the row tells "no block" from "a clean block". Update
   [`docs/LIVE_SCHEMA.md`](../LIVE_SCHEMA.md); the `signer_ip`, `signer_user_agent` row there now reads *"at the
   act that closed the leg (commit or decline)"*.
4. **Observed by the server:**
   - `Accept-Language`, stored at both acts in `signer_accept_language` when it is 1 to 256 printable
     characters, and not stored otherwise;
   - **at the decline, `signer_ip` and `signer_user_agent` too**, as the commit stores them today.
     `SigningSession::decline()` takes them, and a session closes by one act only, so the columns mean *the act
     that closed the leg*;
   - `framework.trusted_proxies` configured explicitly empty, and `framework.trusted_headers` set to
     `x-forwarded-for` and `x-forwarded-proto`, so declaring a proxy later is one variable
     (`SYMFONY_TRUSTED_PROXIES`) and never trusts a forwarded host ([BL-273](../BACKLOG.md), §4 D9).
5. **Nothing to the event log.** No member of `SignatureCommitted`, `SessionDeclined` or of any other fact
   changes (§4 D7). `RecipientAuthContext` gains the recipient's readable document ids, for §4 D8.
6. **The contract the trail reads.** `CommitEvidenceReader` and `CommitEvidenceView` become
   `ActEvidenceReader` and `ActEvidenceView`, because they now describe a decline as well (the repo's authoring
   rule 1 sweep applies). The view gains the `Accept-Language` and an `Option` of the reported evidence, as a
   Session `Contract/View` type that is `Pii`. A decline's values are read like a commit's.
7. **The audit trail** (ADR-0072's foreseen slot):
   - `Source` gains `BROWSER_REPORT` (*"declarado por el navegador del firmante"*); `UnstatedReason` gains
     `NOT_REPORTED` (the browser sent no such value) and `DISCARDED_ILL_FORMED` (it sent one, and it was
     dropped).
   - `PartyPersonal` gains, for a party whose leg closed by commit or decline on the normal route:
     - the decline's observed IP and user agent, beside the commit's;
     - the observed `Accept-Language`;
     - a `reported` group: the geolocation (its status always, its coordinates, accuracy and capture time only
       when granted), each device field, and each reading entry, every value a `Stated` with
       `BROWSER_REPORT` or an `Unstated` with one of the two new reasons.
   - `TrailJson` adds, under `personal`: `decline_ip`, `decline_user_agent`, `accept_language`, and `reported`
     (`geolocation`, `device`, `reading`, `discarded`). `commit_ip` and `commit_user_agent` keep their meaning:
     they stay empty for a decline. The schema stays `f5sign.audit-trail/1` (§4 D12).
   - `trail.typ` prints, in the party's personal section: *"IP al rechazar"*, *"Navegador al rechazar"*,
     *"Idiomas del navegador"*, and a block *"Declarado por el navegador del firmante"*. The position prints as
     latitude and longitude to 5 decimals with its accuracy in metres and its capture time; a denied, unavailable
     or timed-out position prints its status in words (*"Ubicación denegada por el firmante"*, …). Reading prints
     one line per document title. Dropped members print as *"enviado mal formado, descartado"*.
   - The delegated route's party gains nothing: its route has no browser of the signer.
8. **Records at landing:**
   - ADR-0072: §2.4's slot line points at what was built, §2.5 names the new `Source`, §2.6 lists the new members
     of the personal group, and its `Realized in` names this task;
   - ADR-0061 §2.12's census of personal data outside object storage gains the `reported_*` columns,
     `signer_accept_language`, and the decline's `signer_ip` and `signer_user_agent`;
   - [BL-171](../BACKLOG.md) adds them to the plaintext set;
   - ADR-0032's Counterpoint 3 interim gains three members;
   - [BL-286](../BACKLOG.md) is closed by this task; [BL-273](../BACKLOG.md) is closed by §3 #4.
9. **The signer handoff**, `docs/frontend-handoff/TASK-045-signer-browser-evidence.md`, written before the merge:
   - the block, its bounds, and that the same block goes on the commit and on the decline;
   - the lenient contract: a bad block never costs a signature, and the drop is recorded;
   - **remove the fake `GEO_IP` fallback** (§4 D5) and send a `status` instead;
   - no canvas/WebGL, so `useDeviceFingerprint.ts` stops sending its hashes;
   - measure the visible time per document, which `useDocumentReadThrough.ts` does not today;
   - a new capability flag to switch capture back on in real mode, set only once the deployed spec publishes
     the block (BL-177);
   - the privacy text must name location, device and reading data before capture is switched on (§6).

## 4. Key decisions

- **D1 — Inside the act, not a separate route.** It is written in the same unit of work as `SignatureCommitted`
  or `SessionDeclined`. There can be no evidence without an act, and no act that lost its evidence to a network
  failure between two calls, which is exactly the gap of the old evidence-then-complete design. Nothing to
  order, and no "evidence received, act pending" state.
  - Both acts draw their own unit with `UnitOfWork::own()`, and a wrong signing code is a refusal that
    **commits** that unit, so the charged attempt survives (ADR-0075 §2.4, landed with TASK-052). So the block is
    parsed before the unit, and the `reported_*` values, `signer_accept_language` and the decline's observed
    values are recorded only once the signing gate has passed: recorded earlier, they would be kept for an act
    that did not happen.
<!-- OFFREPO: D2 cites Directive 2002/58/EC (ePrivacy), art. 5.3, which requires consent for storing or reading information on a user's terminal; the fact is restated where it is used. -->
- **D2 — Provenance is in the name.** Everything the browser declares is `reported_*`, beside the observed
  columns and never in them, as `asserted_*` is (ADR-0055). The trail keeps the same line with its own `Source`.
  - The canvas/WebGL fingerprint is excluded: identifying a device by fingerprint needs consent under the
    ePrivacy Directive (art. 5.3), and it proves little. *Maintainer, 2026-09-21.*
- **D3 — A closed set, censused by a test.** Adding a member is a decision, not an accretion: the census fails on
  an unclassified key, on `ReportedEvidence`, on the drop paths and on the trail's `reported` group.
- **D4 — Evidence is never the reason someone cannot sign or decline.**
  - An ill-formed part is **dropped, and the drop is recorded** by path and reason, and logged at `warning`
    without values. The act goes on; a whole block that is not an object is handled the same way (`evidence`,
    `WRONG_TYPE`).
  - The unit that is dropped is fixed per member: **geolocation whole** (coordinates mean nothing without their
    status), **device per field** (a long `model` must not cost the timezone), **reading per entry**.
  - ⚠ **This departs from the proposal**, which asked for a strict 422 because an ill-formed block *"sería un bug
    de nuestro propio cliente"*. It also said the evidence *"nunca puede ser la razón de que alguien no pueda
    firmar"*, and the two cannot both hold: a strict 422 turns a client bug into signers who cannot sign.
  - The recorded drop keeps the bug visible without charging the signer for it. `status` with coordinates on
    anything but `GRANTED`, or `GRANTED` without all four, is an ill-formed geolocation.
- **D5 — Coordinates travel only with `GRANTED`, and the signer's fake fallback goes.** Today the signer's
  fallback fills latitude 0, longitude 0 and 50 km of accuracy, labelled `GEO_IP`, with no lookup behind it.
  Recorded as it stands, it would place a signer in the Gulf of Guinea. The server cannot tell that fake apart
  from a real reading, so the contract makes a missing fix a `status` and the handoff removes the fallback.
- **D6 — Plaintext for now, classified.** *Maintainer, 2026-09-21*, the same criterion as TASK-044's field
  values. `ReportedEvidence` is `Pii`, and the trail keeps it inside `PartyPersonal`. BL-171 records the choice.
  ADR-0032's target — ciphered inline in the log — is untouched.
- **D7 — Nothing to the event log, and no anchor of its own.** The log is permanent, and LOAD-BEARING §2 forbids
  plaintext personal data in it.
  **Amended 2026-11-04 by [ADR-0097](../adr/ADR-0097-the-log-is-the-documents-one-source.md) §2.8:** the report enters the log, with its personal values
  encrypted under `session.reported_evidence`, because an erasable keyring answers this reason.
  - If the reported evidence must be anchored, it joins the one commitment mechanism [BL-268](../BACKLOG.md)
    describes. That mechanism would cover TASK-044's field values, this evidence, and the trail's three-state
    reservations field, rather than adding a third member to `SignatureCommitted`. The sealed trail is,
    meanwhile, the first sealed artifact that holds these values.
- **D8 — `reading` is bounded by what the recipient may read.** An entry for a document outside that set is
  dropped (`NOT_READABLE`). The page counts are the browser's: the server does not check `pages_total` against
  the document, because a mismatch would only show a client that measures differently, and the trail labels the
  value as reported.
- **D9 — The server trusts no proxy until one is declared, and the declaration is tested.** Nothing sits in
  front of Caddy in the infra's compose, so the empty list is the true configuration today, not a placeholder.
  Declaring a proxy is setting `SYMFONY_TRUSTED_PROXIES`; the headers are fixed now, and `x-forwarded-host` is
  left out so a proxy can never rewrite the host the application sees ([BL-273](../BACKLOG.md)).
- **D10 — No server-side Geo-IP.** It needs a licensed database, and it would be a derived location, not a
  reading. If it ever comes, it is computed on the server, which has the IP, and is marked as derived
  ([BL-274](../BACKLOG.md)).
- **D11 — Deploy.** The block is additive and optional on both routes. The signer sends nothing until the
  deployed spec publishes it (BL-177). The migration only adds nullable columns, so no row is backfilled and the
  repo's authoring rule 6 has nothing to land on: an act before the deploy reads as "not reported" in the trail,
  which is true.
- **D12 — The trail grows additively, and keeps its schema.** Every trail key and enum case this task adds is
  new; `commit_ip` and `commit_user_agent` keep their meaning and stay empty for a decline rather than being
  renamed to `act_ip`. Renaming them would change a published key's meaning and move the schema to `/2`, for no
  reader's benefit. A trail issued before this task simply lacks the new keys.
- **D13 — The decline gets the commit's observed values.** *Maintainer, 2026-10-13*, which closes BL-286. A
  session closes by one act, so `signer_ip` and `signer_user_agent` take the decline's values without a second
  pair of columns; the trail tells which act they belong to by the leg's outcome and prints them under its own
  label.

## 5. Verification

- **Gates:** as TASK-044 §5.1, plus the audit trail's Typst render test.
- **Tests and sabotages:**
  - **Bounds:** one case per field and per bound — the bound kept, one past it dropped with the right reason.
    Sabotage each bound.
  - **Drop units:** `status: DENIED` with coordinates → geolocation dropped, device and reading kept; an over-long
    `device.model` → only `device.model` dropped, the other device fields kept; a second entry for one
    `document_id` → that entry dropped as `DUPLICATE`.
  - A whole block that is not an object → the act succeeds, nothing kept, `[{member: evidence, reason:
    WRONG_TYPE}]` recorded. No block at all → `reported_evidence_dropped` null.
  - A `reading` entry for a document the recipient may not read but another recipient may → dropped as
    `NOT_READABLE`. The fixture's readable and signable sets **disagree**, so a filter on the wrong one fails.
  - **The order with the signing gate** (D1), on both acts: a wrong code → the charge committed, and every
    `reported_*` column, `signer_accept_language` and the decline's `signer_ip` still null. Sabotage by moving
    the write before the gate, and check that this case fails, not an upstream one.
  - **The decline** records `signer_ip`, `signer_user_agent` and `signer_accept_language`, and the trail shows
    them under the decline's labels while `commit_ip` stays empty.
  - **Closed key sets:** on `ReportedEvidence` (a census that fails on an unclassified key), on the drop record
    (paths and reasons only, no value), on the trail JSON's `personal.reported` group, and on `SignatureCommitted`
    and `SessionDeclined` (unchanged).
  - **`trusted_proxies`:** with nothing declared, a request carrying `X-Forwarded-For` yields `REMOTE_ADDR`; with
    `SYMFONY_TRUSTED_PROXIES` naming the connecting address, it yields the forwarded address; with a different
    address declared, never the header; `X-Forwarded-Host` is never honoured.
  - **The log line of a drop** carries no value.
  - **The trail**, per party state: granted (coordinates stated with `BROWSER_REPORT`), denied (status stated, no
    coordinates), no block (`NOT_REPORTED`), dropped member (`DISCARDED_ILL_FORMED`), delegated (no `reported`
    group).
- **Acceptance:** over HTTP, a commit with all three members answers 200, the row holds them, and the issued
  trail's JSON holds them. The same commit with an over-long `device.model` answers 200 and records
  `device.model` as dropped. A decline with a denied position answers as a decline does and records the status
  and the observed IP.

## 6. Open follow-ups (track, don't solve here)

- **[BL-274](../BACKLOG.md): server-side Geo-IP**, deferred for its licence (D10).
- **[BL-268](../BACKLOG.md): one commitment mechanism** for field values, reported evidence and the three-state
  reservations, if the maintainer revives it (D7).
- **The privacy text.** The signer's notice has to name location, device and reading data before capture is
  switched back on. Whether that notice is sufficient is legal's question, as ADR-0032's decision 10 gate is for
  the rest of the evidence and BL-389 is for the drawn signature.
- **[TASK-047](TASK-047-per-signer-evidence-document.md)**, the per-recipient receipt ([ADR-0086](../adr/ADR-0086-a-recipient-who-acts-gets-a-sealed-receipt.md)), will read
  the recipient's `reported` evidence through `ActEvidenceReader`, as the trail does.
- **[BL-415](../BACKLOG.md): a purge step for the new `session.signing_session` columns** (`reported_*`, `signer_accept_language`, and the decline's `signer_ip` and `signer_user_agent`). [ADR-0061](../adr/ADR-0061-retention-deletion-and-purge.md) §2.12 lists them as covered by nothing.
- **[BL-416](../BACKLOG.md): a test of the trail PDF's printed text.** Today the collapse rule and the reading-time units are held by the render and a human read.
- **Closed by this task, 2026-10-14:** [BL-273](../BACKLOG.md) (`trusted_proxies`, §3 #4) and [BL-286](../BACKLOG.md) (evidence at the decline, D13).

## 7. Deviations & honest notes

### Scope
- None beyond the record. The diff stays in Session, Evidence & Audit, the framework's proxy settings, the published spec, the signer handoff and the records that state them. Nothing under Kernel/, Foundation/, deptrac, phpstan or the baseline changed.

### Decisions made during implementation
- Slice 14: the device carries eight keys, not the nine the slice text said; its own signature and test row had eight.
- Slice 01: reported times compare to the microsecond, unlike `AssertedEvidence`, since a browser reading carries milliseconds. Slice 05 binds them as `Y-m-d H:i:s.uP` text so the fractions survive a reload.
- Slice 02: `ReportedEvidence::equals()` compares reading entries in order and ignores submitted keys, because a stored value reads back keyed 0..n-1.
- Slice 03 (rulings): a device field sent as `null` is not collected and is not a drop; an empty array is an object for geolocation, device, screen and entries and a list for languages and reading, because the request decodes JSON to arrays; a duplicate is checked only on an otherwise well-formed entry. Three intake sabotages turn red through the value object's refusal, which backs the intake up.
- Slice 05: stricter than the slice and accepted: a row with coordinates and no geo status is refused, and reading and drop JSON entries must carry exactly their keys.
- Slice 11: the premise that Symfony 7.4 trusts `x-forwarded-host` by default is false, so no red was seen before the change; the host test is kept and its sabotage turns it red.
- Slice 16: the platform version has its own row; reading time prints in seconds under 60 s and in minutes with one decimal above; a report with nothing sent prints one line.
- Slice 18: the signer handoff is in Spanish, like its siblings.
- Slice 19: ADR-0032's interim is narrowed to what the tree shows: the browser report is classified `Pii`; the observed `Accept-Language` and the decline's IP and user agent are plain text beside `signer_ip`.
- Parallel slices 10 and 12 shared one index and a bare `git commit` swept staged renames into slice 10's commit; the orchestrator re-cut the two commits with the tip tree unchanged, and parallel briefs now require `git commit --only`.

### Decisions that needed an ADR
- None. [ADR-0072](../adr/ADR-0072-the-audit-trail-is-rendered-from-the-log.md) (Accepted) gained the browser-reported slot additively (§4 D12). [ADR-0032](../adr/ADR-0032-evidence-pii-custody.md) stays `Proposed`: this task adds to its interim and builds none of its target, so nothing exercises the decision. No ADR moves to `Accepted` here.

### Declared and unproven properties
- The trail PDF's printed text (the one-line collapse, the units of reading time, the decline's lines) has no test; it is held by the render and a human read. [BL-416](../BACKLOG.md).
- That the new columns are purged: nothing purges them. [BL-415](../BACKLOG.md).
- The proxy being declared in production: `SYMFONY_TRUSTED_PROXIES` is committed empty and `ObservedClientAddressTest` pins the empty case; what an operator puts in front of Caddy is not visible from this repository.
- `evidence` has no overall key-count or depth cap at the controller, only per-field bounds and the body-size limits of PHP and Caddy (security audit, low risk; the intake looks keys up and never iterates).
- Infection on the 44 changed `src/F5Sign` files, at `bd380545`: covered-MSI 95 %, MSI 87 % (bars 85/70). The changed-line gate's first run, at `cf7fe407`, left 65 escaped mutants on changed lines; two fix slices killed 48 of them with tests (`5964a09e`, `bd380545`, no production change). The 17 that remain are equivalent, each checked by a reviewer against the code:
  - `ReportedEvidenceIntake`: the geolocation loop's `break` → `continue` (every hit assigns the same `NOT_ALLOWED_FOR_STATUS`); the model's minimum length 0 → −1 (`mb_strlen` is never negative); the `CastFloat` on a number (the `float|Reason` return type widens an int under strict types); in the RFC 3339 parser, the offset index and the `strtoupper` around it (PHP's `P` reads `Z` and `z` as UTC) and the fraction's pad width (`u` reads its digits as a decimal fraction); and the four mutants on the `getLastErrors()` check (it is `false` unless a warning or error exists, and an error makes `createFromFormat` return `false` first).
  - `HydratesReportedEvidence`: the JSON depth 512 → 511/513 on the reading and the drops (a value nested that deep is refused either way; only the exception class differs, `JsonException` against `UnexpectedValueException`, and no caller tells them apart).
  - `DbalActEvidenceReader`: the unwrapped `array_values` (`ReportedEvidence::reading()` already returns a list).
  - `TrailAssembler`: the `explode` limit 2 → 3 (element `[0]` is the same string).
  - `TrailJson`: the unwrapped `array_map` over the discarded members (`DiscardedMember` is final, readonly and has exactly the two public string properties the array carries, so `json_encode` writes the same object).
- `HydratesReportedEvidence`'s refusal of a non-string language inside a list is reached by no test; Infection did not report it on a changed line.

### Debt left behind, and where it lives now
- Purge of the new personal-data columns: [BL-415](../BACKLOG.md), and the ADR-0061 §2.12 census row.
- Encipherment of those columns: [BL-171](../BACKLOG.md), whose row names them; declined for now by §4 D6.
- Trail PDF text test: [BL-416](../BACKLOG.md).
- Pre-existing, not this task: `DbalSigningSessionRepository::columnValues()`'s docblock contradicts `AssertedEvidencePersistenceTest`; the ADR index's ADR-0072 row disagrees with its Status about dev-stack exercise. Neither has a row yet.
- Low-confidence residue from the closing review, left as is: a doubled empty docblock line in `DeclineSignature`, and `CommitSignatureController`'s class docblock summarising the evidence without `Accept-Language`.

### Delegated work
- 19 slices: 12 on opus (critical), 7 on sonnet (standard), 8 review rounds in all; slices 01, 03, 05, 10, 12, 13, 16 and 18 took one round, the rest none.
- Replicator: slice 04, 20 call sites in 14 test files; slice 08, 7 `CommitSignature` calls in 6 test files; slice 13, 15 `ActEvidenceView` call sites. All three accepted without redoing by hand.
- Closing review: changes, routed to slice 20 (prose), landed at cf7fe407.

### Cost of the run
- Implementers: opus 1,758,109 tokens over 12 slices; sonnet 746,009 over 7 slices.
- Review rounds: 8; escalations: none recorded beyond the critical slices on opus.
- Baseline f0e4b7fb: 5394 tests; full suite at 1390ec05: 6799 tests, 77709 assertions.
- Reviewer, gate and close agents' tokens are not in run.log.
