set -e
PDF=$(mktemp --suffix=.pdf)
trap "rm -f $PDF" EXIT
API=http://localhost:8000/api/v1
T=11111111-1111-1111-1111-111111111111
U=22222222-2222-2222-2222-222222222222
H=(-H "Content-Type: application/json" -H "X-Tenant-Id: $T" -H "X-Acting-User-Id: $U")
HF=(-H "X-Tenant-Id: $T" -H "X-Acting-User-Id: $U")
J='python3 -c import sys,json'

ENV_ID=$(curl -s "${H[@]}" -X POST $API/envelopes -d '{"title":"Signer payload check","workflow_type":"SIGN_ORDERED","signing_mode":"SEQUENTIAL_PADES"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
DOC_ID=$(curl -s "${H[@]}" -X POST $API/envelopes/$ENV_ID/documents -d '{"name":"c.pdf","display_name":"Contract","mime_type":"application/pdf"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
curl -s -o /dev/null "${H[@]}" -X POST $API/envelopes/$ENV_ID/steps -d '{"ordinal":1}'
REC_ID=$(curl -s "${H[@]}" -X POST $API/envelopes/$ENV_ID/recipients -d '{"step_ordinal":1,"role":"SIGNER","email":"ana@example.com","full_name":"Ana Firma"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

# minimal valid PDF
printf '%%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\ntrailer<</Root 1 0 R>>\n%%%%EOF\n' > "$PDF"
echo "upload: $(curl -s -o /dev/null -w '%{http_code}' "${HF[@]}" -X POST $API/envelopes/$ENV_ID/documents/$DOC_ID/content -F "file=@$PDF;type=application/pdf")"

curl -s -o /dev/null -w "assign:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/document-assignments \
  -d "{\"assignments\":[{\"recipient_id\":\"$REC_ID\",\"document_id\":\"$DOC_ID\",\"sign\":true,\"view\":true,\"placements\":[{\"page\":1,\"origin_x\":100,\"origin_y\":600,\"width\":180,\"height\":60}]}]}"

curl -s -o /dev/null -w "field_text:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/fields \
  -d "{\"document_id\":\"$DOC_ID\",\"recipient_id\":\"$REC_ID\",\"type\":\"TEXT\",\"required\":true,\"label\":\"NIF\",\"placement\":{\"page\":1,\"origin_x\":80,\"origin_y\":300,\"width\":200,\"height\":24},\"options\":{\"validation\":{\"max_length\":9,\"pattern\":\"^[0-9]{8}[A-Z]$\",\"pattern_message\":\"NIF invalido\"}}}"

curl -s -o /dev/null -w "field_radio:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/fields \
  -d "{\"document_id\":\"$DOC_ID\",\"recipient_id\":\"$REC_ID\",\"type\":\"RADIO\",\"required\":false,\"label\":\"Envio\",\"placement\":{\"page\":1,\"origin_x\":80,\"origin_y\":360,\"width\":160,\"height\":48},\"options\":{\"choices\":[{\"value\":\"URG\",\"label\":\"Urgente\"},{\"value\":\"STD\",\"label\":\"Estandar\"}]}}"

curl -s -o /dev/null -w "send:%{http_code}\n" "${H[@]}" -X POST $API/envelopes/$ENV_ID/send -d '{}'

TOKEN=$(curl -s "${H[@]}" -X POST $API/signing-tokens -d "{\"envelope_id\":\"$ENV_ID\",\"recipient_id\":\"$REC_ID\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
curl -s -o /dev/null -w "session_start:%{http_code}\n" -H "Authorization: Bearer $TOKEN" -X POST $API/signing/session
echo "--- GET /signing/session ---"
curl -s -H "Authorization: Bearer $TOKEN" $API/signing/session | python3 -m json.tool
echo "ENVELOPE=$ENV_ID RECIPIENT=$REC_ID"
echo "SIGNER_URL=http://localhost:3001/s/$TOKEN"
