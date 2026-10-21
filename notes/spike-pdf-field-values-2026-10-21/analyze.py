import json, sys, re
def walk(o, out):
    if isinstance(o, dict):
        if 'Name' in o and 'Status' in o and isinstance(o['Name'], dict):
            out.append((o['Name'].get('value'), o['Status'], (o.get('Error') or o.get('Warning') or {}).get('value') if isinstance(o.get('Error') or o.get('Warning'), dict) else None))
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
for f in sys.argv[1:]:
    rep = json.load(open(f)); print('#####', f.split('/')[-1])
    for s in rep['DiagnosticData']['Signature']:
        rev = s['PDFRevision']; md = rev.get('ModificationDetection') or {}
        om = md.get('ObjectModifications') or {}
        print(' sig', rev['SignatureField'][0]['name'], 'lock=', rev['SignatureField'][0].get('SigFieldLock'), 'FieldMDP=', rev['PDFSignatureDictionary'].get('FieldMDP'), 'DocMDP=', rev['PDFSignatureDictionary'].get('DocMDP'))
        print('   cats:', {k: (len(v) if isinstance(v, list) else v) for k, v in om.items()}, 'visualDiff', md.get('VisualDifference'), 'pageDiff', md.get('PageDifference'), 'overlap', md.get('AnnotationOverlap'))
    cons = []; walk(rep.get('DetailedReport'), cons)
    seen = set()
    for n, st, msg in cons:
        if re.search(r'(?i)modif|mdp|lock|permi|overlap|visual|page diff|form', n or '') and (n, st) not in seen:
            seen.add((n, st)); print('   chk', st, '|', n, '|', msg or '')
