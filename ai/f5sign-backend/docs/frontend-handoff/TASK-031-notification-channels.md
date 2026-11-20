# Handoff to the dashboard and the integrators — each recipient declares the channels that reach them

| | |
|---|---|
| **Origin** | branch `feat/channel-selection` (from `develop` `bbeb256c`), **not merged, not deployed** · commit: see `git log feat/channel-selection`; the last one that touches `src/` is the one that counts · [TASK-031](../tasks/TASK-031-channel-selection-beyond-email.md), [ADR-0077](../adr/ADR-0077-a-recipient-declares-the-channels-that-reach-them.md) |
| **Date** | 2026-10-13 |
| **Repos affected** | the sender **dashboard** (recipient authoring and the envelope view) and **integrators** that author recipients through the API (`factor5-dashboard`) |
| **Nature** | **breaking**: `notification_channels` is now required on add-recipient, and the correction answers `200` with a body instead of `204`. Additive otherwise: one new route, three new members per recipient on the envelope read, new refusal codes. One code is retired |
| **Action required** | send `notification_channels` on every add-recipient · read the correction's `200 {warnings}` · show `warnings` · handle the new codes · drop `RECIPIENT_HAS_NO_ADDRESS` |
| **Deployed** | not yet |
| **Status** | Pending |

## What changed in the contract

### Phones are E.164

Every `phone` is sent in international form with its country code: `+34600123456`, `+351912345678`. A number with
no `+` is refused `400 INVALID_PHONE_NUMBER`. ⚠ A country code typed wrong is not caught as a format error: a
Portuguese mobile written with Spain's code (`+34 912 345 678`) is a valid Madrid landline, so it is accepted as a
phone and then refused for SMS (`422 RECIPIENT_CANNOT_RECEIVE_METHOD`). Show the number back to the person who
typed it.

### Add a recipient: `POST /api/v1/envelopes/{id}/recipients`

Two members in the body:

| Member | Rule |
|---|---|
| `notification_channels` | **Required.** An ordered list of `EMAIL` and `SMS`, each at most once. `[]` is allowed and means the platform sends this recipient no notification (see below). Leaving it out, or sending `null`, is `422 VALIDATION_ERROR` naming the member. There is no default |
| `notification_mode` | `IN_ORDER` or `ALL_AT_ONCE`. Required with two channels, refused with one or none |

What each declaration does:

- `["EMAIL"]` or `["SMS"]`: every notification goes on that channel.
- `["SMS", "EMAIL"]` with `IN_ORDER`: the first channel is sent; the next is tried only if the provider refuses the
  first or its retries run out. ⚠ **A message the provider accepts and then loses is not followed by the next
  channel**: bounces are not read (BL-390). Most mail servers accept a message for an address that does not exist
  and bounce it later, so an `EMAIL` first in the list rarely falls back on a wrong address.
- `["SMS", "EMAIL"]` with `ALL_AT_ONCE`: both are sent at once. It means the channels listed, never every channel
  the platform has.
- `[]`: the platform sends no invitation, resend, ending notice or sealed copy. You deliver the link yourself
  (`POST /api/v1/signing-tokens`). Every one-time code the recipient's gates require is **still** sent.

One list governs every notification to the recipient. One-time codes never read it: an `OTP_SMS` code goes by SMS
and an `OTP_EMAIL` code by email, whatever the list says. A recipient who signs by `MACHINE_KEY` is never invited;
they receive only the ending notices, on their list.

Each channel needs its contact: `email` for `EMAIL`, a mobile `phone` for `SMS`. `SMS` also needs the tenant enabled
for SMS and a deployment that sends SMS.

The `201` body gains `warnings` (always present, `[]` when none):

```json
{ "id": "…", "warnings": [ { "code": "LINK_AND_CODE_SHARE_A_CHANNEL", "channel": "SMS", "method": "OTP_SMS" } ] }
```

`LINK_AND_CODE_SHARE_A_CHANNEL`: the invitation may travel on `channel`, and a gate sends its `method` code on the
same channel, so whoever holds that phone or mailbox holds both factors. It is allowed, not refused: the eCMR
carrier has one phone. Show it to the sender.

#### Two factors, and the three empty lists (ADR-0077 §2.9)

The configuration that gives two factors:

```json
{
  "email": "carrier@example.com",
  "phone": "+34600123456",
  "notification_channels": ["EMAIL"],
  "auth": { "access_methods": ["OTP_SMS"], "signing_methods": ["OTP_SMS"] }
}
```

Three lists sit on the recipient and their empty values mean three different things:

| List | Its empty value |
|---|---|
| `auth.access_methods: []` | opens the document with no code, as read back; add-recipient no longer accepts the empty list and writes an open gate `DIRECT_LINK` ([ADR-0082](../adr/ADR-0082-the-access-gate-is-always-declared.md), accepted 2026-10-20) |
| `auth.signing_methods: []` | signs with no code |
| `notification_channels: []` | sends no notification while still sending every code the gates require |

#### New `422` codes on add-recipient

| `code` | Meaning | What to do |
|---|---|---|
| `NOTIFICATION_CHANNELS_REFUSED` | a channel named twice, or `notification_mode` missing with two channels or given with fewer | fix the list or the mode |
| `SMS_NOT_AVAILABLE_ON_DEPLOYMENT` | `SMS` declared, and this deployment sends no SMS. Checked first | declare another channel; this deployment cannot help |
| `SMS_NOT_ENABLED_FOR_TENANT` | `SMS` declared, and your tenant is not enabled for SMS | declare another channel, or ask the operator to enable SMS for the tenant |
| `RECIPIENT_CANNOT_RECEIVE_METHOD` | already existed for auth methods; now also a declared channel with nowhere to go: `EMAIL` with no address, `SMS` with no phone, or a phone for `SMS` that is a landline (whatever the mode). Under `IN_ORDER` a missing contact is refused only when no channel in the list has one | add the contact, or change the channels |
| `PHONE_COUNTRY_NOT_SUPPORTED` | the phone (declared for `SMS`, or for an `OTP_SMS` gate) is a mobile in a country this deployment does not text. The body carries `country` (ISO 3166-1 alpha-2, or `null`) and `supported_countries`, a list of `{country}` records: `[{"country": "ES"}, {"country": "PT"}]` | show the supported countries; use another channel or a phone in one of them |

For a claimable slot (`claimable: true`), the two contact checks (`RECIPIENT_CANNOT_RECEIVE_METHOD`,
`PHONE_COUNTRY_NOT_SUPPORTED`) wait for the claim, which answers them with the same codes. The two SMS availability
codes do not wait.

### The correction: `POST …/recipients/{recipientId}/corrections` now answers `200`

It answered `204` with no body. It now answers `200 {"warnings": [...]}`, the same `warnings` as add-recipient, as
they hold after the correction. A correction that would leave the declared channels without the contacts they need
is refused **before** it spends one of the three corrections: `422 RECIPIENT_CANNOT_RECEIVE_METHOD`, or
`422 PHONE_COUNTRY_NOT_SUPPORTED` for a phone declared for `SMS` in a country this deployment does not text. The
correction does not change the channels.

### New route: `PUT /api/v1/envelopes/{id}/recipients/{recipientId}/notification-channels`

Replaces the recipient's `notification_channels` and `notification_mode`. Machine API key, like the other authoring
routes.

- Body: `{"notification_channels": [...], "notification_mode": ...}`, same rules and same `422` codes as add-recipient.
  A missing list is `422 VALIDATION_ERROR`.
- `200 {"warnings": [...]}`.
- It is **not** a correction: it spends none of the three and records no correction.
- If the recipient's step is active and their invitation was not sent, was refused, or was left to you (`[]`), they
  are invited again on the new channels. After an invitation was sent, only later notices change.
  ⚑ **Since 2026-10-21 ([TASK-065](TASK-065-dashboard-correction-reaches-the-changed-contact.md), ADR-0084 §2.11):** after
  an invitation, a change that **removes** a channel also retires the earlier links and re-invites on the new
  channels; a change that only adds channels still changes later notices only.
- Allowed until the envelope is closed: `409 CONFLICT` after, `409 ENVELOPE_EXPIRED` once `expires_at` has passed.

### Resend: `POST …/recipients/{recipientId}/resends`

`RECIPIENT_HAS_NO_ADDRESS` is **retired**. The resend now asks whether anything would be sent, not whether there is
an email. Three new `409` codes:

| `code` | Meaning | What to do |
|---|---|---|
| `RECIPIENT_NOTIFIED_BY_INTEGRATOR` | the recipient declared `[]`, so the platform sends them nothing | mint a new link with `POST /api/v1/signing-tokens` |
| `RECIPIENT_HAS_NO_REACHABLE_CHANNEL` | none of the declared channels can reach them now | correct a contact or change the channels; retrying does not help |
| `RECIPIENT_SIGNS_BY_DELEGATION` | the recipient signs by `MACHINE_KEY`, so they are never sent an invitation | nothing to resend |

### Envelope read: `GET /api/v1/envelopes/{id}`

Each recipient carries three new members:

| Member | What it is |
|---|---|
| `notification_channels` | the declared list, in the declared order |
| `notification_mode` | `IN_ORDER`, `ALL_AT_ONCE`, or `null` with fewer than two channels |
| `warnings` | the same entries as the write routes, for as long as the condition holds. `[]` when none |

A recipient that existed before this version reads `["EMAIL"]` and `null`.

`invitation_state` (TASK-056) can now read `DELIVERED_BY_INTEGRATOR`: the recipient declared `[]`, and the platform
did not write. And `release_reason` can now read `INTEGRATOR_DELIVERED_NOT_OPENED`.

### Event log

- `RECIPIENT_NOTIFICATION_CHANNELS_CHANGED` (new): one per channel change, with `notification_channels_before`,
  `notification_mode_before`, `notification_channels_after`, `notification_mode_after` and `reinvites`.
- `IDENTITY_TENANT_SMS_NOTIFICATIONS_CHANGED` (new): the operator switched a tenant's SMS on or off.
- `channel` on `RECIPIENT_INVITATION_OUTCOME_RECORDED` and `RECIPIENT_DESTINATION_REFUSED` is now a **closed** set,
  `EMAIL` or `SMS` (`null` on an outcome with no channel). The values did not change.

## What the dashboard and the integrators have to do

1. **Send `notification_channels` on every add-recipient.** A client that does not is refused `422`.
2. **Read the correction's `200` body.** A client that expects `204` exactly breaks.
3. **Show `warnings`** wherever the sender authors or views a recipient.
4. **Handle the new codes** with the remedies above, and drop `RECIPIENT_HAS_NO_ADDRESS`.
5. **Offer the channel change** as its own action, not as a correction.
6. **Ask for phones in E.164** and show the number back.

## What is NOT ready yet

- Delivery receipts and bounces: `SENT` is the ceiling, and `IN_ORDER` does not fall back on a later bounce (BL-390).
- SMS spend guards (a spend limit, a resend cap, an alert): TASK-057.
- `OTP_SMS` is not gated by the tenant's SMS capability, only by the deployment (BL-391).
- Preferences set by the recipient: the declaration is the sender's.

## How to verify it from the front end

Do not adopt the change until the `doc.json` of the deployment serving you lists `notification_channels` as required
on the add-recipient body and publishes the `notification-channels` route. Then: add a recipient with
`["EMAIL"]` and read it back; add one without the member and get `422 VALIDATION_ERROR`; correct a contact and get
`200` with `warnings`.
