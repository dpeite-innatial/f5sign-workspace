set -e
API=http://localhost:8000/api/v1
T=11111111-1111-1111-1111-111111111111
U=22222222-2222-2222-2222-222222222222
H=(-H "Content-Type: application/json" -H "X-Tenant-Id: $T" -H "X-Acting-User-Id: $U")

ENV_ID=$(curl -s "${H[@]}" -X POST $API/envelopes -d '{"title":"Smoke field entity","workflow_type":"SIGN_ORDERED","signing_mode":"SEQUENTIAL_PADES"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "envelope=$ENV_ID"

DOC_ID=$(curl -s "${H[@]}" -X POST $API/envelopes/$ENV_ID/documents -d '{"name":"contract.pdf","display_name":"Contract","mime_type":"application/pdf"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "document=$DOC_ID"

curl -s -o /dev/null -w "add_step:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/steps -d '{"ordinal":1}'

REC_ID=$(curl -s "${H[@]}" -X POST $API/envelopes/$ENV_ID/recipients -d '{"step_ordinal":1,"role":"SIGNER","email":"signer@example.com","full_name":"Ana Firma"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
echo "recipient=$REC_ID"

echo "--- POST /document-assignments ---"
curl -s -w "\nHTTP:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/document-assignments \
  -d "{\"assignments\":[{\"recipient_id\":\"$REC_ID\",\"document_id\":\"$DOC_ID\",\"sign\":true,\"view\":true,\"placements\":[]}]}"

echo "--- POST /fields (SIGNATURE) ---"
curl -s -w "\nHTTP:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/fields \
  -d "{\"document_id\":\"$DOC_ID\",\"recipient_id\":\"$REC_ID\",\"type\":\"SIGNATURE\",\"required\":true,\"placement\":{\"page\":1,\"origin_x\":100,\"origin_y\":200,\"width\":180,\"height\":60}}"

echo "--- POST /fields (DROPDOWN with options) ---"
curl -s -w "\nHTTP:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/fields \
  -d "{\"document_id\":\"$DOC_ID\",\"recipient_id\":\"$REC_ID\",\"type\":\"DROPDOWN\",\"required\":true,\"label\":\"Modalidad\",\"placement\":{\"page\":1,\"origin_x\":100,\"origin_y\":300,\"width\":150,\"height\":24},\"options\":{\"choices\":[{\"value\":\"A\",\"label\":\"Opcion A\"},{\"value\":\"B\",\"label\":\"Opcion B\"}]}}"

echo "--- GET /envelopes/{id} ---"
curl -s "${H[@]}" $API/envelopes/$ENV_ID | python3 -m json.tool
