import sys
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils import generic
r = PdfFileReader(open(sys.argv[1], 'rb'), strict=False)
xs = r.xrefs
for rev in range(xs.total_revisions):
    refs = sorted(xs.explicit_refs_in_revision(rev), key=lambda x: x.idnum)
    out = []
    for ref in refs:
        o = r.get_object(ref, revision=rev)
        if isinstance(o, generic.StreamObject): d = 'stream' + (('/' + str(o.get('/Subtype', ''))) if '/Subtype' in o else '')
        elif isinstance(o, generic.DictionaryObject):
            d = '/'.join(str(o.get(k)) for k in ('/Type', '/FT', '/T') if k in o) or 'dict:' + ','.join(list(o.keys())[:4])
        else: d = type(o).__name__
        out.append(f'{ref.idnum}={d}')
    print(f'rev{rev}:', ' '.join(out)[:900])
