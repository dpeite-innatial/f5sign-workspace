# probe-067: DSS 6.4 signing into a pre-existing field (fieldId), measured 2026-10-21

Stack: eu-dss (healthy), pyHanko 0.29.0 image f5spike-pyhanko:1, network f5sign-net. Script: /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/probe.py (adapted from spike.py).
Raw per-case data: /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/results-*.json (run1 = results-run1.json: A, B, C), DSS reports /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/<case>.report.json, PDFs/PNGs alongside.

Every case (same shape): revision 1 creates read-only data fields f5s_a, f5s_b; revision 2 fills f5s_a and creates f5s_sig_1 (/Lock Include [f5s_a], rect [100 100 260 140], same on all cases) ; sig 1 by DSS into f5s_sig_1 (text only, fieldId); revision 3 fills f5s_b and creates TARGET f5s_sig_2 (/Lock Include [f5s_b]); sig 2 by DSS into it (the case). So every case is a SECOND signature (chaining). Payload shapes as DssPayloadMapper (signingCertificate/chain from server-signing key, PAdES_BASELINE_B, ENVELOPED, SHA256, blevelParams, imageParameters; image = {bytes,name}, imageScaling ZOOM_AND_CENTER, text BOTTOM size 8 padding 3.0). Four calls: GET server-signing/keys, getDataToSign, server-signing/sign, signDocument. All HTTP calls succeeded in every case (no DSS error text anywhere).

Validation common to all: both signatures INDETERMINATE/NO_CERTIFICATE_CHAIN_FOUND (dev seal, as in the spike). Sig 1 (chained, the earlier one): Undefined 0 in every case; its modifications are SignatureOrFormFill 6, AnnotationChange 0 (A2: SignatureOrFormFill 7, AnnotationChange 1, still Undefined 0). "Is signature valid against /FieldMDP dictionary?" OK wherever present. The only other WARNING is X.509 chain (and the overlap one noted below).

## Case A: invisible, field /Rect [0 0 0 0], page 1, unrotated

| Variant | imageParameters | Signature ended in field | Extra field by DSS | FieldMDP/lock in diag data | Rect after / page | Undefined (sig1 / sig2) | PNG |
|---|---|---|---|---|---|---|---|
| A1 | {fieldParameters:{fieldId}} only | f5s_sig_2 (embedded sig names: f5s_sig_1, f5s_sig_2) | no (AcroForm: f5s_a f5s_b f5s_sig_1 f5s_sig_2) | yes: SigFieldLock and FieldMDP, Action INCLUDE, Field [f5s_b] | [0 0 0 0], page 1 | 0 / 0 (sig2 has no later revision; mod counts empty) | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/A1-invisible-fieldId-only-after.png (page unchanged: diff bbox None) |
| A2 | none | **Signature1** (new field made by DSS); our f5s_sig_2 left UNSIGNED (no /V) | **yes: Signature1** | sig2 (Signature1): lock None, FieldMDP None; our f5s_sig_2 /Lock never applied | Signature1 [0 0 0 0], page 1; f5s_sig_2 [0 0 0 0] unsigned | 0 / 0 | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/A2-no-imageParameters-after.png |
| A3 | {fieldParameters:{fieldId}, textParameters:{text:"", size:8}} | f5s_sig_2 | no | yes: Include [f5s_b], FieldMDP written | [0 0 0 0], page 1 | 0 / 0 | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/A3-fieldId-empty-text-after.png (diff bbox None) |

A3 note: I did not find another DSS 6.4 parameter that names an existing field. The WADL/OpenAPI URLs I tried (services/rest?_wadl, swagger-ui/index.html) returned no usable document, so the search of the REST model was not done beyond that; A3 is therefore my own variant (fieldId + empty text), not a distinct parameter.
Fact: DSS 6.4 puts an invisible signature INTO our existing zero-rect field with FieldMDP from our /Lock when fieldParameters.fieldId is sent (A1, A3); without imageParameters (A2) it ignores our field and creates its own, with no lock.

## Case B: PNG 200x80 + text below, into our field (page unrotated)

Field rect [200 600 400 690] (200x90 pt). imageParameters = {image, imageScaling ZOOM_AND_CENTER, fieldParameters{fieldId}, textParameters{text "Jane Signer", signerTextPosition BOTTOM, size 8, padding 3.0}}.
Signed into f5s_sig_2, no extra field, FieldMDP/SigFieldLock Include [f5s_b], rect unchanged [200 600 400 690], page 1, Undefined 0 for sig1. Mark bbox (pixels at 72 dpi, left/top/right/bottom) 201,158,401,239; intended displayed box 200,152,400,242 (y = 842-690 .. 842-600). PNG: /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/B-png-text-fieldId-after.png (before: B-png-text-fieldId-before.png).
Note: bbox is the drawn pixels (scribble touches the PNG's corners), not the box edge.

## Case C: /Rotate 90, 180, 270 (MediaBox 0 0 595 842)

Intended DISPLAYED rect (top-left, y-down, as the viewer shows it): x=100 y=50 w=200 h=80 (displayed pixel box x 100..300, y 50..130). Conversion to user space (W=595, H=842; dx,dy,dw,dh = 100,50,200,80), derived from where the unrotated bottom-left origin ends up:
- /Rotate 90 (displayed 842x595): displayed x = user y, displayed y(down) = user x. Rect = [dy, dx, dy+dh, dx+dw] = [50 100 130 300]
- /Rotate 180 (displayed 595x842): displayed x = W - user x, displayed y(down) = user y. Rect = [W-dx-dw, dy, W-dx, dy+dh] = [295 50 495 130]
- /Rotate 270 (displayed 842x595): displayed x = H - user y, displayed y(down) = W - user x. Rect = [W-dy-dh, H-dx-dw, W-dy, H-dx] = [465 542 545 742]
Each sig2 was signed with the Case B payload. The pixel bbox is the diff of page 1 rendered before vs after sig 2 (pdftoppm -r 72, poppler honours /Rotate), so it isolates mark 2.

| Case | fieldParameters | Field rect after / page | Signed into | Extra field | FieldMDP Include | Undefined sig1 | Mark bbox px (l,t,r,b) vs intended 100,50,300,130 | Orientation in PNG | PNG |
|---|---|---|---|---|---|---|---|---|---|
| C90 | fieldId | [50 100 130 300] / 1 | f5s_sig_2 | no | [f5s_b] | 0 | 103,50,221,130 (squeezed to 118 px wide) | image and text turned 90 deg, sideways | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/C90-rotate-after.png |
| C180 | fieldId | [295 50 495 130] / 1 | f5s_sig_2 | no | [f5s_b] | 0 | 100,52,299,128 (offsets l0 t+2 r-1 b-2) | position right, content UPSIDE DOWN | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/C180-rotate-after.png |
| C270 | fieldId | [465 542 545 742] / 1 | f5s_sig_2 | no | [f5s_b] | 0 | 179,50,297,130 (squeezed 118 wide) | image and text turned 90 deg, sideways | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/C270-rotate-after.png |

Extra variants (not asked, run because C turned the content): same fields, fieldParameters = {fieldId, rotation}. Same checks (signed into f5s_sig_2, no extra field, FieldMDP [f5s_b], Undefined sig1 0, rect unchanged):

| Case | rotation | Mark bbox px (l,t,r,b) vs 100,50,300,130 | Orientation | PNG |
|---|---|---|---|---|
| E90 | AUTOMATIC | 101,52,301,130 (l+1 t+2 r+1 b0) | upright, text below image | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/E90-rotate-fieldParams-AUTOMATIC-after.png |
| E180 | AUTOMATIC | 101,52,301,127 (l+1 t+2 r+1 b-3) | upright | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/E180-rotate-fieldParams-AUTOMATIC-after.png |
| E270 | AUTOMATIC | 101,52,301,127 (l+1 t+2 r+1 b-3) | upright | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/E270-rotate-fieldParams-AUTOMATIC-after.png |
| E90 | ROTATE_90 | 100,52,299,128 | turned 180 deg (upside down) | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/E90-rotation-ROTATE_90-after.png |
| E90 | ROTATE_270 | 101,52,301,130 | not viewed | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/E90-rotation-ROTATE_270-after.png |
| E90 | NONE | 103,50,221,130 | same as no rotation (sideways) | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/E90-rotation-NONE-after.png |
| F90 | widget /MK /R 90 on our field, no rotation param | 103,50,221,130 | same as without /MK (DSS ignores it): sideways | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/F90-widget-MK-R-90-after.png |
| F90 | /MK /R 90 + AUTOMATIC | 101,52,301,130 | upright | /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/F90-widget-MK-R-90-AUTOMATIC-after.png |

Ambiguity: on the /Rotate 90 cases (C90, E90, F90) DSS's validation shows "Is no element overlapping detected" WARNING with Overlap [{Page 1}] on both signatures. In my fixture sig1's rect [100 100 260 140] overlaps the target [50 100 130 300] in user space (x 100..130, y 100..140), so this is probably my fixture, not DSS. Not re-run with a disjoint sig1.

## Case D: CropBox offset

MediaBox 0 0 595 842, CropBox [50 60 545 782]. Intended rect x=100 y=50 w=200 h=80 measured from the CropBox top-left. Conversion: user x0 = cropX0 + dx = 150; x1 = x0 + dw = 350; y1 = cropY1 - dy = 782 - 50 = 732; y0 = y1 - dh = 652. Rect = [150 652 350 732]. Signed with fieldId only (Case B payload, no rotation).
Result: signed into f5s_sig_2, no extra field, rect unchanged [150 652 350 732], page 1, FieldMDP/lock [f5s_b], sig1 Undefined 0. Rendered with pdftoppm -cropbox (495x722 px): mark bbox 101,52,301,127 vs intended 100,50,300,130 (l+1 t+2 r+1 b-3), upright. PNG: /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/D-cropbox-after.png.
Ambiguity: my first D run rendered without -cropbox (MediaBox origin): bbox 151,112,351,187 = intended + (50,60) as expected from the CropBox origin; kept in /tmp/claude-1002/-var-www-html-factor5-others-f5sign-f5sign-backend/f09342ff-5331-4a03-af2c-57a844860ce0/scratchpad/probe-067/out/run1-D-mediabox-render/. The -cropbox run above is the one to read.

## Fixture and method caveats
- Marks measured as non-white pixel diff of drawn content, so offsets of 1-3 px at the edges are the scribble/text inset, not box error.
- One page, one rotation per case; sig1 is always in the unrotated-space rect [100 100 260 140] with text only and fieldId (no rotation param), so its own appearance is sideways/upside-down on rotated pages in the PNGs.
- Cases are a second signature; first-signature-only was not run separately.
- Validator is DSS only; as the spike found, DSS does not enforce FieldMDP on later edits, so "FieldMDP present" here means written, not enforced.
