"""Spike: AcroForm fields filled across incremental PAdES revisions, signed by DSS or pyHanko.

Usage: python spike.py <chain>   chain in {A, B, C}
  A: fields prepared before sig1; DSS creates its own signature fields; no locks.
  B: fields + signature fields with /Lock prepared before sig1; DSS signs INTO the fields.
  C: as B, but pyHanko signs (self-signed dev key); DSS only validates.
Each chain ends with a tamper revision (rec1's locked value changed after sig2) for validation.
"""
import base64, io, json, sys, time, datetime
import requests
from pyhanko.pdf_utils import generic
from pyhanko.pdf_utils.generic import NameObject as N, pdf_name
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader

DSS = 'http://eu-dss:8080/services/rest'
ALIAS = 'certificate'
CHAIN = sys.argv[1]
FLAGS = set(sys.argv[2:])
MERGE = 'merge' in FLAGS
NEWAP = 'newap' in FLAGS
OUT = f'/w/out/{CHAIN}' + ''.join('-' + f for f in sorted(FLAGS))

# ---------------------------------------------------------------- base PDF (hand-built)
def base_pdf() -> bytes:
    objs = []
    def add(s): objs.append(s); return len(objs)
    font = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    c1 = b'BT /F1 18 Tf 72 760 Td (Page 1 - plain A4) Tj ET 0.8 g 60 600 m 535 600 l S'
    c2 = b'BT /F1 18 Tf 80 500 Td (Page 2 - Rotate 90, CropBox offset) Tj ET'
    s1 = add(b'<< /Length %d >>\nstream\n' % len(c1) + c1 + b'\nendstream')
    s2 = add(b'<< /Length %d >>\nstream\n' % len(c2) + c2 + b'\nendstream')
    pages = 6
    p1 = add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>' % (pages, s1, font))
    p2 = add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /CropBox [40 30 575 812] /Rotate 90 /Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>' % (pages, s2, font))
    assert add(b'<< /Type /Pages /Kids [%d 0 R %d 0 R] /Count 2 >>' % (p1, p2)) == pages
    cat = add(b'<< /Type /Catalog /Pages %d 0 R >>' % pages)
    out = io.BytesIO(); out.write(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n'); offs = []
    for i, o in enumerate(objs, 1):
        offs.append(out.tell()); out.write(b'%d 0 obj\n' % i + o + b'\nendobj\n')
    x = out.tell(); out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
    for o in offs: out.write(b'%010d 00000 n \n' % o)
    out.write(b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, cat, x))
    return out.getvalue()

# ---------------------------------------------------------------- appearance streams
def esc(t: str) -> bytes:
    return t.encode('cp1252', 'replace').replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')

def form_xobject(w, bbox_w, bbox_h, content: bytes, rotate: int, resources):
    d = {
        N('/Type'): N('/XObject'), N('/Subtype'): N('/Form'),
        N('/BBox'): generic.ArrayObject([generic.FloatObject(v) for v in (0, 0, bbox_w, bbox_h)]),
        N('/Resources'): resources,
    }
    if rotate == 90:
        d[N('/Matrix')] = generic.ArrayObject([generic.NumberObject(v) for v in (0, 1, -1, 0, 0, 0)])
    return w.add_object(generic.StreamObject(d, stream_data=content))

def visual_size(rect, rotate):
    rw, rh = rect[2] - rect[0], rect[3] - rect[1]
    return (rh, rw) if rotate == 90 else (rw, rh)

def text_ap_stream(rect, rotate, text, helv):
    class _W:
        def add_object(self, o): return o
    return text_ap(_W(), rect, rotate, text, helv)

def text_ap(w, rect, rotate, text, helv):
    vw, vh = visual_size(rect, rotate)
    body = b'/Tx BMC q 1 1 %f %f re W n BT /Helv 10 Tf 0 g 3 %f Td (%s) Tj ET Q EMC' % (vw - 2, vh - 2, (vh - 7) / 2, esc(text))
    res = generic.DictionaryObject({N('/Font'): generic.DictionaryObject({N('/Helv'): helv})})
    return form_xobject(w, vw, vh, body, rotate, res)

def box_ap(w, rect, rotate, helv, zadb, checked: bool):
    vw, vh = visual_size(rect, rotate)
    border = b'0.5 G 0.5 0.5 %f %f re S' % (vw - 1, vh - 1)
    mark = b' BT /ZaDb %f Tf 0 g %f %f Td (4) Tj ET' % (vh * 0.8, vw * 0.15, vh * 0.2) if checked else b''
    res = generic.DictionaryObject({N('/Font'): generic.DictionaryObject({N('/ZaDb'): zadb, N('/Helv'): helv})})
    return form_xobject(w, vw, vh, b'q ' + border + mark + b' Q', rotate, res)

# ---------------------------------------------------------------- the model
# name -> (type, owner, [(page_index, rect)], options)
FIELDS = {
    'f5s_name':    ('Tx',  1, [(0, (72, 700, 300, 720))], None),
    'f5s_agree':   ('Btn', 1, [(0, (72, 660, 86, 674))], None),
    'f5s_ref':     ('Tx',  1, [(0, (320, 700, 520, 720)), (1, (100, 300, 120, 500))], None),  # 2nd widget on rotated page
    'f5s_country': ('Ch',  2, [(0, (72, 620, 200, 640))], ['ES', 'PT', 'FR']),
}
VALUES = {1: {'f5s_name': 'José Núñez', 'f5s_agree': True, 'f5s_ref': 'CMR-2026-0042'},
          2: {'f5s_country': 'PT'}}
SIG_RECT = {1: (0, (330, 560, 530, 620)), 2: (0, (330, 480, 530, 540))}
READONLY = 1

def prepare(pdf: bytes, with_sig_fields: bool, prefill=None) -> bytes:
    prefill = prefill or {}
    w = IncrementalPdfFileWriter(io.BytesIO(pdf))
    helv = w.add_object(generic.DictionaryObject({N('/Type'): N('/Font'), N('/Subtype'): N('/Type1'), N('/BaseFont'): N('/Helvetica'), N('/Encoding'): N('/WinAnsiEncoding')}))
    zadb = w.add_object(generic.DictionaryObject({N('/Type'): N('/Font'), N('/Subtype'): N('/Type1'), N('/BaseFont'): N('/ZapfDingbats')}))
    page_refs = [w.find_page_for_modification(i)[0] for i in range(2)]
    annots = {0: [], 1: []}
    fields = generic.ArrayObject()
    for name, (ft, _owner, widgets, opts) in FIELDS.items():
        fdict = generic.DictionaryObject({N('/FT'): N('/' + ft), N('/T'): generic.TextStringObject(name), N('/Ff'): generic.NumberObject(READONLY | ((1 << 17) if ft == 'Ch' else 0))})
        if ft == 'Ch':
            fdict[N('/Opt')] = generic.ArrayObject([generic.TextStringObject(o) for o in opts])
        if ft == 'Btn':
            fdict[N('/V')] = N('/Yes') if prefill.get(name) else N('/Off')
        elif name in prefill:
            fdict[N('/V')] = generic.TextStringObject(prefill[name])
        fref = w.add_object(fdict)
        kids = generic.ArrayObject()
        for pi, rect in widgets:
            rot = 90 if pi == 1 else 0
            wd = generic.DictionaryObject({
                N('/Type'): N('/Annot'), N('/Subtype'): N('/Widget'), N('/Parent'): fref, N('/P'): page_refs[pi],
                N('/Rect'): generic.ArrayObject([generic.FloatObject(v) for v in rect]), N('/F'): generic.NumberObject(4),
                N('/MK'): generic.DictionaryObject({N('/R'): generic.NumberObject(rot)}),
            })
            if ft == 'Btn':
                wd[N('/AS')] = N('/Yes') if prefill.get(name) else N('/Off')
                wd[N('/AP')] = generic.DictionaryObject({N('/N'): (lambda d: d if 'directn' in FLAGS else w.add_object(d))(generic.DictionaryObject({
                    N('/Yes'): box_ap(w, rect, rot, helv, zadb, True), N('/Off'): box_ap(w, rect, rot, helv, zadb, False)}))})
            else:
                wd[N('/AP')] = generic.DictionaryObject({N('/N'): text_ap(w, rect, rot, prefill.get(name, ''), helv)})
            if MERGE and len(widgets) == 1:
                del wd[N('/Parent')]
                fdict.update(wd)
                annots[pi].append(fref); kids = None
                break
            wref = w.add_object(wd)
            kids.append(wref); annots[pi].append(wref)
        if kids is not None:
            fdict[N('/Kids')] = kids
        fields.append(fref)
    if with_sig_fields:
        for rec, (pi, rect) in SIG_RECT.items():
            locked = [n for n, f in FIELDS.items() if f[1] == rec]
            sd = generic.DictionaryObject({
                N('/FT'): N('/Sig'), N('/T'): generic.TextStringObject(f'f5s_sig{rec}'),
                N('/Type'): N('/Annot'), N('/Subtype'): N('/Widget'), N('/P'): page_refs[pi], N('/F'): generic.NumberObject(4),
                N('/Rect'): generic.ArrayObject([generic.FloatObject(v) for v in rect]),
                N('/Lock'): generic.DictionaryObject({N('/Type'): N('/SigFieldLock'), N('/Action'): N('/Include'),
                    N('/Fields'): generic.ArrayObject([generic.TextStringObject(n) for n in locked])}),
            })
            sref = w.add_object(sd); fields.append(sref); annots[pi].append(sref)
    for pi, refs in annots.items():
        pref = page_refs[pi]; pdict = pref.get_object()
        pdict[N('/Annots')] = generic.ArrayObject(refs); w.mark_update(pref)
    w.root[N('/AcroForm')] = w.add_object(generic.DictionaryObject({
        N('/Fields'): fields, N('/DA'): generic.TextStringObject('/Helv 0 Tf 0 g'),
        N('/DR'): generic.DictionaryObject({N('/Font'): generic.DictionaryObject({N('/Helv'): helv, N('/ZaDb'): zadb})}),
        N('/SigFlags'): generic.NumberObject(3)}))
    w.update_root()
    out = io.BytesIO(); w.write(out); return out.getvalue()

def find_field(w, name):
    for ref in w.root['/AcroForm']['/Fields']:
        if ref.get_object()['/T'] == name:
            return ref
    raise KeyError(name)

def add_sig_field(w, rec):
    pi, rect = SIG_RECT[rec]
    page_ref = w.find_page_for_modification(pi)[0]
    locked = [n for n, f in FIELDS.items() if f[1] == rec]
    sd = generic.DictionaryObject({
        N('/FT'): N('/Sig'), N('/T'): generic.TextStringObject(f'f5s_sig{rec}'),
        N('/Type'): N('/Annot'), N('/Subtype'): N('/Widget'), N('/P'): page_ref, N('/F'): generic.NumberObject(4),
        N('/Rect'): generic.ArrayObject([generic.FloatObject(v) for v in rect]),
        N('/Lock'): generic.DictionaryObject({N('/Type'): N('/SigFieldLock'), N('/Action'): N('/Include'),
            N('/Fields'): generic.ArrayObject([generic.TextStringObject(n) for n in locked])}),
    })
    sref = w.add_object(sd)
    pd = page_ref.get_object(); pd['/Annots'].append(sref); w.mark_update(page_ref)
    af_ref = w.root.raw_get('/AcroForm'); af_ref.get_object()['/Fields'].append(sref); w.mark_update(af_ref)

def fill(pdf: bytes, values: dict, sig_for=None) -> bytes:
    w = IncrementalPdfFileWriter(io.BytesIO(pdf))
    if sig_for: add_sig_field(w, sig_for)
    dr = w.root['/AcroForm']['/DR']['/Font']
    helv, zadb = dr.raw_get('/Helv'), dr.raw_get('/ZaDb')
    for name, value in values.items():
        fref = find_field(w, name); fd = fref.get_object()
        if fd['/FT'] == '/Btn':
            state = N('/Yes') if value else N('/Off')
            fd[N('/V')] = state; w.mark_update(fref)
            for kref in (fd['/Kids'] if '/Kids' in fd else [fref]):
                kref.get_object()[N('/AS')] = state; w.mark_update(kref)
            continue
        fd[N('/V')] = generic.TextStringObject(value); w.mark_update(fref)
        for kref in (fd['/Kids'] if '/Kids' in fd else [fref]):
            kd = kref.get_object()
            rect = [float(v) for v in kd['/Rect']]
            rot = int(kd['/MK']['/R']) if '/MK' in kd else 0
            # In-place appearance update: the widget dict is untouched, its /AP /N stream object is rewritten.
            if NEWAP:
                kd[N('/AP')] = generic.DictionaryObject({N('/N'): text_ap(w, rect, rot, value, helv)}); w.mark_update(kref)
                continue
            ap_ref = kd['/AP'].raw_get('/N')
            fresh = text_ap_stream(rect, rot, value, helv)
            stm = ap_ref.get_object()
            stm._data = fresh.data; stm._encoded_data = None
            for k in [k for k in stm.keys() if k not in ('/Length',)]: del stm[k]
            stm.update({k: v for k, v in fresh.items() if k != '/Length'})
            w.mark_update(ap_ref)
    out = io.BytesIO(); w.write(out); return out.getvalue()

# ---------------------------------------------------------------- DSS
def dss(method, path, body=None):
    r = requests.request(method, DSS + path, json=body, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f'{path} -> {r.status_code}: {r.text[:800]}')
    return r.json()

def dss_sign(pdf: bytes, rec: int, into_field: bool) -> bytes:
    key = next(k for k in dss('GET', '/server-signing/keys') if k['alias'] == ALIAS)
    pi, rect = SIG_RECT[rec]
    fp = {'fieldId': f'f5s_sig{rec}'} if into_field else {
        'page': pi + 1, 'originX': rect[0], 'originY': 842 - rect[3], 'width': rect[2] - rect[0], 'height': rect[3] - rect[1], 'rotation': 'AUTOMATIC'}
    params = {
        'signingCertificate': key['certificate'], 'certificateChain': key.get('certificateChain', []),
        'signatureLevel': 'PAdES_BASELINE_B', 'signaturePackaging': 'ENVELOPED', 'digestAlgorithm': 'SHA256',
        'blevelParams': {'signingDate': int(time.time() * 1000)},
        'imageParameters': {'fieldParameters': fp, 'textParameters': {'text': f'Signed by recipient {rec}', 'size': 10, 'padding': 3}},
    }
    doc = {'bytes': base64.b64encode(pdf).decode(), 'name': f'chain{CHAIN}.pdf'}
    dtbs = dss('POST', '/signature/one-document/getDataToSign', {'parameters': params, 'toSignDocument': doc})
    sv = dss('POST', f'/server-signing/sign/{ALIAS}/SHA256', {'bytes': dtbs['bytes']})
    signed = dss('POST', '/signature/one-document/signDocument', {'parameters': params, 'toSignDocument': doc, 'signatureValue': sv})
    return base64.b64decode(signed['bytes'])

def dss_validate(pdf: bytes, label: str) -> dict:
    rep = dss('POST', '/validation/validateSignature', {'signedDocument': {'bytes': base64.b64encode(pdf).decode(), 'name': label + '.pdf'}})
    json.dump(rep, open(f'{OUT}/{label}.report.json', 'w'), indent=1)
    return rep

# ---------------------------------------------------------------- pyHanko signer (chain C)
_signer = None
def ph_signer():
    global _signer
    if _signer: return _signer
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    from pyhanko.sign import signers
    k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nm = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'f5sign spike dev seal')])
    now = datetime.datetime.now(datetime.timezone.utc)
    c = (x509.CertificateBuilder().subject_name(nm).issuer_name(nm).public_key(k.public_key()).serial_number(1)
         .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=30))
         .add_extension(x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True)
         .sign(k, hashes.SHA256()))
    open('/tmp/k.pem', 'wb').write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    open('/tmp/c.pem', 'wb').write(c.public_bytes(serialization.Encoding.PEM))
    _signer = signers.SimpleSigner.load('/tmp/k.pem', '/tmp/c.pem')
    return _signer

def ph_sign(pdf: bytes, rec: int) -> bytes:
    from pyhanko.sign import signers, fields
    from pyhanko.stamp import TextStampStyle
    w = IncrementalPdfFileWriter(io.BytesIO(pdf))
    meta = signers.PdfSignatureMetadata(field_name=f'f5s_sig{rec}', md_algorithm='sha256', subfilter=fields.SigSeedSubFilter.PADES)
    pdf_signer = signers.PdfSigner(meta, signer=ph_signer(), stamp_style=TextStampStyle(stamp_text=f'Signed by recipient {rec}\n%(ts)s'))
    out = io.BytesIO(); pdf_signer.sign_pdf(w, output=out); return out.getvalue()

# ---------------------------------------------------------------- run
def summarize(rep: dict, label: str):
    sr = rep['SimpleReport']; dd = rep['DiagnosticData']
    rows = []
    for s in sr.get('signatureOrTimestampOrEvidenceRecord', []):
        s = s.get('Signature', s)
        rows.append((s.get('SignatureFormat'), s.get('Indication'), s.get('SubIndication'), s.get('SignedBy')))
    print(f'== {label}: {len(rows)} signatures')
    for r in rows: print('   simple:', r)
    for s in dd.get('Signature', []):
        rev = s.get('PDFRevision') or {}
        md = rev.get('ModificationDetection') or {}
        print('   diag sig', s['Id'][-8:], 'len', (rev.get('SignatureField') or [{}])[0] if isinstance(rev.get('SignatureField'), list) else '',
              'fieldMDP' if (rev.get('PDFSignatureDictionary') or {}).get('FieldMDP') else '', 'docMDP' if (rev.get('PDFSignatureDictionary') or {}).get('DocMDP') else '')
        print('      modifications:', json.dumps(rev.get('ModificationDetection'), ensure_ascii=False)[:600])
        print('      sigdict keys:', sorted((rev.get('PDFSignatureDictionary') or {}).keys()))

if __name__ == '__main__':
    import os; os.makedirs(OUT, exist_ok=True)
    sign = {'A': lambda p, r: dss_sign(p, r, False), 'B': lambda p, r: dss_sign(p, r, True), 'C': ph_sign}[CHAIN]
    steps = {}
    p = prepare(base_pdf(), with_sig_fields=CHAIN in 'BC' and 'late' not in FLAGS); steps['0-prepared'] = p
    if 'prefill' in FLAGS:
        p = prepare(base_pdf(), with_sig_fields=CHAIN in 'BC', prefill=VALUES[1])
    else:
        p = fill(p, VALUES[1], 1 if 'late' in FLAGS else None)
    steps['1-filled-r1'] = p
    p = sign(p, 1); steps['2-signed-r1'] = p
    p = p if 'nofill2' in FLAGS else fill(p, VALUES[2], 2 if 'late' in FLAGS else None); steps['3-filled-r2'] = p
    p = sign(p, 2); steps['4-signed-r2'] = p
    steps['5-tampered'] = fill(p, {'f5s_name': 'Mallory'})  # rec1's (locked) value changed after both signatures
    for k, v in steps.items(): open(f'{OUT}/{k}.pdf', 'wb').write(v)
    for k in ('4-signed-r2', '5-tampered'):
        summarize(dss_validate(steps[k], k), k)
