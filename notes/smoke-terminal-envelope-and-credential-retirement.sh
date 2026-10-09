#!/usr/bin/env bash
#
# Manual smoke for TASK-038 (a voided envelope closes the ceremony) and TASK-039
# (retiring a credential whose holder stopped being legitimate).
#
# It drives the real HTTP surface against the dev stack, so it proves the wire
# contract the signer app will branch on — which is exactly what the suite cannot
# tell you, and what a green lane deliberately does not cover.
#
# Prerequisites
#   make -C ../f5sign-infra up
#   make -C ../f5sign-infra migrate
#   TENANT=$(make -C ../f5sign-infra sf cmd="app:identity:provision-tenant smoke-tenant" | tail -1)
#   make -C ../f5sign-infra sf cmd="app:identity:provision-api-client $TENANT smoke-client"
#     -> the last line printed is the key, shown once. Export it:
#   export F5_API_KEY=f5s_ak_...
#
# The X-Tenant-Id / X-Acting-User-Id headers older smoke scripts in this folder use
# are RETIRED: sender routes declare Authn::MACHINE_KEY and derive the tenant from
# the verified key, never from a header the caller supplies.
#
# Note on the reactor: the SessionStatus::REVOKED transition rides the event relay,
# so it needs `make -C ../f5sign-infra worker-up`. Every refusal below is synchronous
# and holds with the worker DOWN — that is the whole point of ADR-0059 §2.4's
# guarantee/reactor split, and running this with no worker is the cheapest way to see it.

set -euo pipefail

API=${API:-http://localhost:8000/api/v1}
KEY=${F5_API_KEY:?export F5_API_KEY with a provisioned f5s_ak_... key}

SENDER=(-H "Authorization: Bearer $KEY" -H "Content-Type: application/json")
SENDER_FORM=(-H "Authorization: Bearer $KEY")

jqv() { python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('$1',''))"; }

# Prints "<http_code> <code-member-or-->" for a recipient-facing GET/POST.
probe() {
  local body code out
  out=$(curl -s -w '\n%{http_code}' "$@")
  code=$(printf '%s' "$out" | tail -1)
  body=$(printf '%s' "$out" | sed '$d')
  printf '%s %s\n' "$code" "$(printf '%s' "$body" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("code","-"))
except Exception: print("-")' 2>/dev/null || echo -)"
}

# Builds a SENT envelope with one SIGNER and one assigned document.
# Echoes "<envelope_id> <recipient_id> <document_id>".
new_sent_envelope() {
  local pdf env doc rec
  pdf=$(mktemp --suffix=.pdf)
  printf '%%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\ntrailer<</Root 1 0 R>>\n%%%%EOF\n' > "$pdf"

  env=$(curl -s "${SENDER[@]}" -X POST "$API/envelopes" \
    -d '{"title":"smoke 038/039","workflow_type":"SIGN_ORDERED","signing_mode":"SEQUENTIAL_PADES"}' | jqv id)
  doc=$(curl -s "${SENDER[@]}" -X POST "$API/envelopes/$env/documents" \
    -d '{"name":"c.pdf","display_name":"Contract","mime_type":"application/pdf"}' | jqv id)
  curl -s -o /dev/null "${SENDER[@]}" -X POST "$API/envelopes/$env/steps" -d '{"ordinal":1}'
  rec=$(curl -s "${SENDER[@]}" -X POST "$API/envelopes/$env/recipients" \
    -d '{"step_ordinal":1,"role":"SIGNER","email":"ana@example.com","full_name":"Ana Firma"}' | jqv id)
  curl -s -o /dev/null "${SENDER_FORM[@]}" -X POST "$API/envelopes/$env/documents/$doc/content" \
    -F "file=@$pdf;type=application/pdf"
  curl -s -o /dev/null "${SENDER[@]}" -X POST "$API/envelopes/$env/document-assignments" \
    -d "{\"assignments\":[{\"recipient_id\":\"$rec\",\"document_id\":\"$doc\",\"sign\":true,\"view\":true,\"placements\":[{\"page\":1,\"origin_x\":100,\"origin_y\":600,\"width\":180,\"height\":60}]}]}"
  curl -s -o /dev/null "${SENDER[@]}" -X POST "$API/envelopes/$env/send" -d '{}'
  rm -f "$pdf"
  printf '%s %s %s\n' "$env" "$rec" "$doc"
}

mint_token() {  # <envelope> <recipient>
  curl -s "${SENDER[@]}" -X POST "$API/signing-tokens" \
    -d "{\"envelope_id\":\"$1\",\"recipient_id\":\"$2\"}" | jqv token
}

open_session() {  # <token> -> the access_credential, empty if none was minted
  curl -s -H "Authorization: Bearer $1" -X POST "$API/signing/session" | jqv access_credential
}

echo
echo "############ PART 1 — TASK-038: a void closes the READ half too ############"
read -r ENV REC DOC < <(new_sent_envelope)
TOKEN=$(mint_token "$ENV" "$REC")
CRED=$(open_session "$TOKEN")
echo "envelope=$ENV recipient=$REC"
echo "credential minted: $([ -n "$CRED" ] && echo yes || echo NO)"

echo "-- baseline, envelope alive (expect 200 / 200) --"
echo "  read-model : $(probe -H "Authorization: Bearer $CRED" "$API/signing/session")"
echo "  bytes      : $(probe -H "Authorization: Bearer $CRED" "$API/signing/session/documents/$DOC")"

echo "-- the sender voids it --"
curl -s -o /dev/null -w '  POST /void -> %{http_code}\n' "${SENDER[@]}" \
  -X POST "$API/envelopes/$ENV/void" -d '{"reason":"smoke"}'

echo "-- the SAME credential, now (this is the gap TASK-038 closed) --"
echo "  read-model : $(probe -H "Authorization: Bearer $CRED" "$API/signing/session")   <- expect 409 ENVELOPE_NO_LONGER_LIVE"
echo "  bytes      : $(probe -H "Authorization: Bearer $CRED" "$API/signing/session/documents/$DOC")   <- expect 404 - (bare, on purpose: ADR-0059 §2.5)"
echo "  commit     : $(probe -H "Authorization: Bearer $CRED" -H 'Content-Type: application/json' -X POST "$API/signing/commit" -d '{}')"

echo "-- and the front door: re-opening the link must MINT NOTHING --"
REOPEN=$(curl -s -w '\n%{http_code}' -H "Authorization: Bearer $TOKEN" -X POST "$API/signing/session")
echo "  POST /signing/session -> $(printf '%s' "$REOPEN" | tail -1)   <- expect 409 ENVELOPE_NO_LONGER_LIVE"
echo "  body: $(printf '%s' "$REOPEN" | sed '$d')"
echo "  ^ assert there is NO access_credential and NO refresh_credential in it."
echo "    Before this task the void left this route minting a fresh pair on every open,"
echo "    for the remaining seven days of the signing token's life."

echo
echo "############ PART 2 — TASK-039: retiring a credential whose holder changed ############"

echo
echo "--- CASE A: a corrected contact RETIRES (BL-152) ---"
read -r ENV_A REC_A DOC_A < <(new_sent_envelope)
TOK_A=$(mint_token "$ENV_A" "$REC_A")
CRED_A=$(open_session "$TOK_A")
echo "  baseline read-model : $(probe -H "Authorization: Bearer $CRED_A" "$API/signing/session")   <- expect 200"
curl -s -o /dev/null -w '  POST /corrections -> %{http_code}\n' "${SENDER[@]}" \
  -X POST "$API/envelopes/$ENV_A/recipients/$REC_A/corrections" -d '{"email":"la-buena@example.com"}'
echo "  read-model : $(probe -H "Authorization: Bearer $CRED_A" "$API/signing/session")   <- expect 401 CREDENTIAL_RETIRED"
echo "  bytes      : $(probe -H "Authorization: Bearer $CRED_A" "$API/signing/session/documents/$DOC_A")   <- expect 404 -"
echo "  commit     : $(probe -H "Authorization: Bearer $CRED_A" -H 'Content-Type: application/json' -X POST "$API/signing/commit" -d '{}')   <- refuses BEFORE the aggregate transitions"
echo "  old link   : $(probe -H "Authorization: Bearer $TOK_A" -X POST "$API/signing/session")   <- the superseded token"
echo "  ^ 401 and NOT 409, deliberately: a conflict tells the signer to stop and not retry,"
echo "    and here the remedy is to come back through the link (with the new code if one was reset)."

echo
echo "--- CASE B: a reset access code retires the CREDENTIAL, never the LINK (BL-158) ---"
read -r ENV_B REC_B DOC_B < <(new_sent_envelope)
TOK_B=$(mint_token "$ENV_B" "$REC_B")
CRED_B=$(open_session "$TOK_B")
echo "  baseline read-model : $(probe -H "Authorization: Bearer $CRED_B" "$API/signing/session")   <- expect 200"
curl -s -o /dev/null -w '  POST /access-code -> %{http_code}\n' "${SENDER[@]}" \
  -X POST "$API/envelopes/$ENV_B/recipients/$REC_B/access-code" -d '{}'
echo "  old credential : $(probe -H "Authorization: Bearer $CRED_B" "$API/signing/session")   <- expect 401 CREDENTIAL_RETIRED"
CRED_B2=$(open_session "$TOK_B")
echo "  same link re-opened, fresh credential: $([ -n "$CRED_B2" ] && echo yes || echo NO)   <- expect yes"
echo "  fresh credential : $(probe -H "Authorization: Bearer $CRED_B2" "$API/signing/session")   <- expect 200"
echo "  ^ this asymmetry IS the delivery bar: the signer is expected back through the same link."

echo
echo "--- CASE C: an auth unlock retires NOTHING (the exemption) ---"
read -r ENV_C REC_C DOC_C < <(new_sent_envelope)
TOK_C=$(mint_token "$ENV_C" "$REC_C")
CRED_C=$(open_session "$TOK_C")
echo "  baseline read-model : $(probe -H "Authorization: Bearer $CRED_C" "$API/signing/session")   <- expect 200"
curl -s -o /dev/null -w '  POST /auth-unlock -> %{http_code}\n' "${SENDER[@]}" \
  -X POST "$API/envelopes/$ENV_C/recipients/$REC_C/auth-unlock" -d '{}'
echo "  same credential : $(probe -H "Authorization: Bearer $CRED_C" "$API/signing/session")   <- expect 200, STILL WORKING"
echo "  ^ unlock lifts a lock imposed by SOMEONE ELSE's guessing. Evicting that signer would be"
echo "    the opposite of what the gesture is for, and it advances auth_generation while retiring"
echo "    nothing — which is why the anchor is an instant and not that counter."

echo
echo "############ what this script canNOT show you ############"
echo "  * The strict boundary. A credential minted in the SAME second as the anchor SURVIVES"
echo "    (comparison is strict, at second precision because 'agp' crosses the wire as a Unix"
echo "    integer). Curl cannot hit that window reliably; it is pinned in"
echo "    tests/F5Sign/Session/Application/Query/RecipientAuthContextRetirementTest.php."
echo "  * The reactor. SessionStatus::REVOKED needs the worker:"
echo "      make -C ../f5sign-infra worker-up"
echo "    then re-run PART 1 and query the session row. Every refusal above is synchronous and"
echo "    already held with the worker down — the reactor is the record, never the guarantee."
