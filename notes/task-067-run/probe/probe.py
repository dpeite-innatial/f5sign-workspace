import sys, io, os, json, base64, time, subprocess, traceback
sys.argv = ['spike.py', 'B']
import spike
from spike import dss, N, generic, IncrementalPdfFileWriter, PdfFileReader, ALIAS
from PIL import Image, ImageDraw, ImageChops

OUT = '/w/out'; os.makedirs(OUT, exist_ok=True)
W, H = 595, 842

def base_pdf(rotate=0, crop=None):
    c = b'BT /F1 12 Tf 30 800 Td (probe page) Tj ET'
    objs = []
    def add(s): objs.append(s); return len(objs)
    font = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    s1 = add(b'<< /Length %d >>\nstream\n' % len(c) + c + b'\nendstream')
    extra = b''
    if crop: extra += b' /CropBox [%d %d %d %d]' % tuple(crop)
    if rotate: extra += b' /Rotate %d' % rotate
    pages = 4
    add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842]%s /Contents %d 0 R /Resources << /Font << /F1 %d 0 R >> >> >>' % (pages, extra, s1, font))
    add(b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
    cat = add(b'<< /Type /Catalog /Pages %d 0 R >>' % pages)
    out = io.BytesIO(); out.write(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n'); offs = []
    for i, o in enumerate(objs, 1):
        offs.append(out.tell()); out.write(b'%d 0 obj\n' % i + o + b'\nendobj\n')
    x = out.tell(); out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
    for o in offs: out.write(b'%010d 00000 n \n' % o)
    out.write(b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, cat, x))
    return out.getvalue()

DATA = {'f5s_a': (1, (30, 30, 130, 50)), 'f5s_b': (2, (30, 60, 130, 80))}

def prepare(pdf):
    w = IncrementalPdfFileWriter(io.BytesIO(pdf))
    helv = w.add_object(generic.DictionaryObject({N('/Type'): N('/Font'), N('/Subtype'): N('/Type1'), N('/BaseFont'): N('/Helvetica'), N('/Encoding'): N('/WinAnsiEncoding')}))
    pref = w.find_page_for_modification(0)[0]
    fields = generic.ArrayObject(); annots = generic.ArrayObject()
    for name, (owner, rect) in DATA.items():
        fd = generic.DictionaryObject({N('/FT'): N('/Tx'), N('/T'): generic.TextStringObject(name), N('/Ff'): generic.NumberObject(1)})
        fref = w.add_object(fd)
        fd.update({N('/Type'): N('/Annot'), N('/Subtype'): N('/Widget'), N('/P'): pref, N('/F'): generic.NumberObject(4),
                   N('/Rect'): generic.ArrayObject([generic.FloatObject(v) for v in rect]),
                   N('/AP'): generic.DictionaryObject({N('/N'): spike.text_ap(w, rect, 0, '', helv)})})
        fields.append(fref); annots.append(fref)
    pref.get_object()[N('/Annots')] = annots; w.mark_update(pref)
    w.root[N('/AcroForm')] = w.add_object(generic.DictionaryObject({N('/Fields'): fields, N('/DA'): generic.TextStringObject('/Helv 0 Tf 0 g'),
        N('/DR'): generic.DictionaryObject({N('/Font'): generic.DictionaryObject({N('/Helv'): helv})}), N('/SigFlags'): generic.NumberObject(3)}))
    w.update_root()
    o = io.BytesIO(); w.write(o); return o.getvalue()

MKR = int(os.environ.get('MKR', '0'))
def fill(pdf, values, sig=None):
    """sig = (name, rect, locked_fields)"""
    w = IncrementalPdfFileWriter(io.BytesIO(pdf))
    pref = w.find_page_for_modification(0)[0]
    if sig:
        name, rect, locked = sig
        sd = generic.DictionaryObject({N('/FT'): N('/Sig'), N('/T'): generic.TextStringObject(name), N('/Type'): N('/Annot'), N('/Subtype'): N('/Widget'),
            N('/P'): pref, N('/F'): generic.NumberObject(4), N('/Rect'): generic.ArrayObject([generic.FloatObject(v) for v in rect]),
            N('/Lock'): generic.DictionaryObject({N('/Type'): N('/SigFieldLock'), N('/Action'): N('/Include'), N('/Fields'): generic.ArrayObject([generic.TextStringObject(n) for n in locked])})})
        if MKR and name.endswith('_2'): sd[N('/MK')] = generic.DictionaryObject({N('/R'): generic.NumberObject(MKR)})
        sref = w.add_object(sd)
        pref.get_object()['/Annots'].append(sref); w.mark_update(pref)
        af = w.root.raw_get('/AcroForm'); af.get_object()['/Fields'].append(sref); w.mark_update(af)
    helv = w.root['/AcroForm']['/DR']['/Font'].raw_get('/Helv')
    for name, val in values.items():
        for ref in w.root['/AcroForm']['/Fields']:
            if ref.get_object().get('/T') == name:
                fd = ref.get_object(); fd[N('/V')] = generic.TextStringObject(val); w.mark_update(ref)
                rect = [float(v) for v in fd['/Rect']]
                fd[N('/AP')] = generic.DictionaryObject({N('/N'): spike.text_ap(w, rect, 0, val, helv)})
    o = io.BytesIO(); w.write(o); return o.getvalue()

def make_png():
    im = Image.new('RGBA', (200, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(2, 78), (30, 4), (60, 76), (90, 6), (120, 74), (150, 8), (180, 72), (198, 2)]
    d.line(pts, fill=(20, 20, 60, 255), width=3)
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()
PNG = make_png(); open('/w/out/sig.png', 'wb').write(PNG)

def sign(pdf, image_params, label):
    key = next(k for k in dss('GET', '/server-signing/keys') if k['alias'] == ALIAS)
    params = {'signingCertificate': key['certificate'], 'certificateChain': key.get('certificateChain', []),
        'signatureLevel': 'PAdES_BASELINE_B', 'signaturePackaging': 'ENVELOPED', 'digestAlgorithm': 'SHA256',
        'blevelParams': {'signingDate': int(time.time() * 1000)}}
    if image_params is not None: params['imageParameters'] = image_params
    doc = {'bytes': base64.b64encode(pdf).decode(), 'name': 'probe.pdf'}
    dtbs = dss('POST', '/signature/one-document/getDataToSign', {'parameters': params, 'toSignDocument': doc})
    sv = dss('POST', f'/server-signing/sign/{ALIAS}/SHA256', {'bytes': dtbs['bytes']})
    sd = dss('POST', '/signature/one-document/signDocument', {'parameters': params, 'toSignDocument': doc, 'signatureValue': sv})
    return base64.b64decode(sd['bytes'])

def img_params(field_id, text='Jane Signer', png=True, rect=None, rotation=None):
    p = {'fieldParameters': {'fieldId': field_id}}
    if rotation: p['fieldParameters']['rotation'] = rotation
    if png:
        p['image'] = {'bytes': base64.b64encode(PNG).decode(), 'name': 'signature.png'}
        p['imageScaling'] = 'ZOOM_AND_CENTER'
    if text is not None:
        p['textParameters'] = {'text': text, 'signerTextPosition': 'BOTTOM', 'padding': 3.0, 'size': 8} if png else \
            {'text': text, 'signerTextPosition': 'LEFT', 'signerTextVerticalAlignment': 'MIDDLE', 'padding': 3.0, 'size': 8}
    return p

def readback(pdf):
    r = PdfFileReader(io.BytesIO(pdf)); res = []
    page = r.root['/Pages']['/Kids'][0].get_object()
    cb = [float(v) for v in page['/CropBox']] if '/CropBox' in page else None
    sigs = []
    for a in page.get('/Annots', []):
        a = a.get_object()
        t = a.get('/T'); ft = a.get('/FT')
        if ft == '/Sig' or ('/Parent' in a and a['/Parent'].get_object().get('/FT') == '/Sig'):
            sigs.append({'T': str(t), 'Rect': [round(float(v), 2) for v in a['/Rect']], 'signed': '/V' in a, 'page': 1, 'Lock': bool('/Lock' in a)})
    af = [str(f.get_object().get('/T')) for f in r.root['/AcroForm']['/Fields']]
    emb = [s.field_name for s in r.embedded_signatures]
    return {'sig_widgets_on_page1': sigs, 'acroform_fields': af, 'embedded_sig_field_names': emb}

def walk(o, f):
    if isinstance(o, dict):
        f(o)
        for v in o.values(): walk(v, f)
    elif isinstance(o, list):
        for v in o: walk(v, f)

def validate(pdf, label):
    rep = dss('POST', '/validation/validateSignature', {'signedDocument': {'bytes': base64.b64encode(pdf).decode(), 'name': label + '.pdf'}})
    json.dump(rep, open(f'{OUT}/{label}.report.json', 'w'), indent=1)
    sr = rep['SimpleReport']; out = {'signatures': []}
    sigs = [s.get('Signature', s) for s in sr.get('signatureOrTimestampOrEvidenceRecord', [])]
    dd = rep['DiagnosticData'].get('Signature', [])
    for i, s in enumerate(dd):
        rev = s['PDFRevision']; md = rev.get('ModificationDetection') or {}
        om = md.get('ObjectModifications') or {}
        sf = rev['SignatureField'][0]
        simple = next((x for x in sigs if x.get('Id') == s['Id']), {})
        und = om.get('Undefined') or om.get('undefined') or []
        out['signatures'].append({'field': sf.get('name'), 'indication': simple.get('Indication'), 'sub': simple.get('SubIndication'),
            'SigFieldLock': sf.get('SigFieldLock'), 'FieldMDP': rev['PDFSignatureDictionary'].get('FieldMDP'),
            'mod_counts': {k: len(v) if isinstance(v, list) else v for k, v in om.items()},
            'undefined': json.dumps(und)[:400] if und else None,
            'visualDiff': md.get('VisualDifference'), 'pageDiff': md.get('PageDifference'), 'overlap': md.get('AnnotationOverlap')})
    # FieldMDP check results
    chk = []
    def f(o):
        if isinstance(o.get('Name'), dict) and 'Status' in o and any(k in (o['Name'].get('value') or '') for k in ('FieldMDP', 'locked', 'lock', 'visual', 'Visual', 'overlap')):
            chk.append((o['Status'], o['Name']['value']))
    walk(rep['DetailedReport'], f); out['checks'] = sorted(set(chk))
    return out

def render(pdf, name):
    pth = f'{OUT}/{name}.pdf'; open(pth, 'wb').write(pdf)
    subprocess.run(['pdftoppm', '-cropbox', '-r', '72', '-png', '-f', '1', '-l', '1', '-singlefile', pth, f'{OUT}/{name}'], check=True)
    return f'{OUT}/{name}.png'

def diffbox(png_before, png_after, thr=8):
    a = Image.open(png_before).convert('RGB'); b = Image.open(png_after).convert('RGB')
    d = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > thr else 0)
    return {'size_px': a.size, 'bbox_px_left_top_right_bottom': d.getbbox()}

def run(name, rotate, crop, sig2_rect, ip_builder, sig1_rect=(100, 100, 260, 140), want_render=True, field_id='f5s_sig_2'):
    res = {'case': name}
    try:
        p = prepare(base_pdf(rotate, crop))
        p = fill(p, {'f5s_a': 'Alice'}, ('f5s_sig_1', sig1_rect, ['f5s_a']))
        p = sign(p, img_params('f5s_sig_1', 'First Signer', png=False), name + '-s1')
        p = fill(p, {'f5s_b': 'Bob'}, ('f5s_sig_2', sig2_rect, ['f5s_b']))
        before = p
        res['sig2_rect_in'] = list(sig2_rect)
        try:
            after = sign(before, ip_builder(), name)
        except Exception as e:
            res['http'] = 'ERROR: ' + str(e)[:900]; return res
        res['http'] = 'ok'
        res['readback'] = readback(after)
        res['validation'] = validate(after, name)
        if want_render:
            pb = render(before, name + '-before'); pa = render(after, name + '-after')
            res['png'] = pa; res['diff'] = diffbox(pb, pa)
    except Exception as e:
        res['exception'] = traceback.format_exc()[-900:]
    return res

results = []
def go(*a, **k):
    r = run(*a, **k); results.append(r); print(json.dumps(r, indent=1, default=str)); sys.stdout.flush()
    json.dump(results, open('/w/out/results-' + os.environ.get('CASES','all').replace(',','') + '.json', 'w'), indent=1, default=str)

which = sys.argv_orig if hasattr(sys, 'argv_orig') else None
sel = os.environ.get('CASES', 'A,B,C,D').split(',')
INV = (0, 0, 0, 0)
if 'A' in sel:
    go('A1-invisible-fieldId-only', 0, None, INV, lambda: {'fieldParameters': {'fieldId': 'f5s_sig_2'}})
    go('A2-no-imageParameters', 0, None, INV, lambda: None)
    go('A3-fieldId-empty-text', 0, None, INV, lambda: {'fieldParameters': {'fieldId': 'f5s_sig_2'}, 'textParameters': {'text': '', 'size': 8}})
if 'B' in sel:
    go('B-png-text-fieldId', 0, None, (200, 600, 400, 690), lambda: img_params('f5s_sig_2'))
# displayed rect
dx, dy, dw, dh = 100, 50, 200, 80
def rot_rect(rot):
    if rot == 90:  return (dy, dx, dy + dh, dx + dw)
    if rot == 180: return (W - dx - dw, dy, W - dx, dy + dh)
    if rot == 270: return (W - dy - dh, H - dx - dw, W - dy, H - dx)
if 'C' in sel:
    for rot in (90, 180, 270):
        if os.environ.get('ROT') and str(rot) not in os.environ['ROT'].split(','): continue
        go(f'C{rot}-rotate', rot, None, rot_rect(rot), lambda: img_params('f5s_sig_2'))
if 'D' in sel:
    crop = (50, 60, 545, 782)
    go('D-cropbox', 0, crop, (crop[0] + dx, crop[3] - dy - dh, crop[0] + dx + dw, crop[3] - dy), lambda: img_params('f5s_sig_2'),
       sig1_rect=(100, 100, 260, 140))

if 'E' in sel:
    for rot in (90, 180, 270):
        go(f'E{rot}-rotate-fieldParams-AUTOMATIC', rot, None, rot_rect(rot), lambda: img_params('f5s_sig_2', rotation='AUTOMATIC'))
    go('E90-rotation-ROTATE_90', 90, None, rot_rect(90), lambda: img_params('f5s_sig_2', rotation='ROTATE_90'))
    go('E90-rotation-ROTATE_270', 90, None, rot_rect(90), lambda: img_params('f5s_sig_2', rotation='ROTATE_270'))
    go('E90-rotation-NONE', 90, None, rot_rect(90), lambda: img_params('f5s_sig_2', rotation='NONE'))
if 'F' in sel:
    go(f'F90-widget-MK-R-{MKR}', 90, None, rot_rect(90), lambda: img_params('f5s_sig_2'))
    go(f'F90-widget-MK-R-{MKR}-AUTOMATIC', 90, None, rot_rect(90), lambda: img_params('f5s_sig_2', rotation='AUTOMATIC'))
