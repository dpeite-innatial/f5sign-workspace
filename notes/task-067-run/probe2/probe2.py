import os, sys, json, base64, io, subprocess
os.environ['CASES'] = 'none'
import probe
from probe import *
RECT = (100, 600, 280, 670)   # 180x70, unrotated A4
OX, OY = 100, 842 - 670       # DSS top-left convention
def mk(var):
    base = img_params('f5s_sig_1', rotation='AUTOMATIC')
    fp = base['fieldParameters']
    if var == 'V0': pass
    elif var == 'V1': base['fieldParameters'] = {'page': 1, 'originX': OX, 'originY': OY, 'width': 180, 'height': 70, 'rotation': 'AUTOMATIC'}
    elif var == 'V2': fp.update(width=180, height=70)
    elif var == 'V3': fp.update(page=1, originX=OX, originY=OY, width=180, height=70)
    elif var == 'V4a': base['textParameters']['size'] = 6
    elif var == 'V4b': base['dpi'] = 72
    elif var == 'V4c': base['textParameters']['signerTextPosition'] = 'BOTTOM'; base['textParameters']['padding'] = 0.0
    elif var == 'V4d': base['imageScaling'] = 'CENTER'
    elif var == 'V4e': base['imageScaling'] = 'STRETCH'
    return base
def ap_info(pdf):
    r = PdfFileReader(io.BytesIO(pdf)); out = []
    page = r.root['/Pages']['/Kids'][0].get_object()
    for a in page.get('/Annots', []):
        a = a.get_object()
        if a.get('/FT') == '/Sig' or ('/Parent' in a and a['/Parent'].get_object().get('/FT') == '/Sig'):
            t = a.get('/T') or a['/Parent'].get_object().get('/T')
            d = {'T': str(t), 'Rect': [round(float(v), 2) for v in a['/Rect']]}
            n = a.get('/AP', {}).get('/N') if '/AP' in a else None
            if n is not None:
                n = n.get_object()
                d['BBox'] = [round(float(v), 2) for v in n['/BBox']]
                d['Matrix'] = [round(float(v), 4) for v in n['/Matrix']] if '/Matrix' in n else None
            else: d['BBox'] = None
            d['Lock'] = '/Lock' in a
            v = a.get('/V') or (a['/Parent'].get_object().get('/V') if '/Parent' in a else None)
            if v is not None:
                v = v.get_object(); refs = v.get('/Reference')
                d['sigdict_FieldMDP_ref'] = json.dumps([{k: str(x) for k, x in rr.get_object().items() if k != '/TransformParams'} | {'TP': {k: str(x) for k, x in rr.get_object()['/TransformParams'].items()} if '/TransformParams' in rr.get_object() else None} for rr in refs]) if refs else None
            out.append(d)
    return out
res = []
variants = os.environ.get('VARS', 'V0,V1,V2,V3').split(',')
for var in variants:
    p = prepare(base_pdf())
    p = fill(p, {'f5s_a': 'Alice'}, None if var=='V1' else ('f5s_sig_1', RECT, ['f5s_a']))
    pb = render(p, f'{var}-before')
    ip = mk(var)
    r = {'var': var, 'imageParameters_sans_bytes': json.loads(json.dumps(ip).replace(base64.b64encode(PNG).decode(), '<png>'))}
    try:
        after = sign(p, ip, var)
    except Exception as e:
        r['http'] = 'ERROR ' + str(e)[:600]; res.append(r); print(json.dumps(r, default=str)); continue
    r['http'] = 'ok'
    r['readback'] = readback(after); r['ap'] = ap_info(after)
    r['validation'] = validate(after, var)
    pa = render(after, f'{var}-after'); r['diff'] = diffbox(pb, pa)
    im = Image.open(pa).convert('RGB')
    im.crop((80, 842-690, 300, 842-580)).resize((660, 330)).save(f'{OUT}/{var}-mark.png')
    res.append(r); print(json.dumps(r, default=str, indent=1)); sys.stdout.flush()
json.dump(res, open(f'{OUT}/results-{os.environ.get("TAG","main")}.json', 'w'), indent=1, default=str)
