import sys, io, json, logging
logging.disable(logging.CRITICAL)
from pyhanko.pdf_utils.reader import PdfFileReader
data = open(sys.argv[1], 'rb').read()
r = PdfFileReader(io.BytesIO(data), strict=False)
def values(rd):
    out = {}
    for f in rd.root['/AcroForm']['/Fields']:
        f = f.get_object()
        if f.get('/FT') != '/Sig': out[str(f['/T'])] = str(f.get('/V', ''))
    return out
print('final document  :', values(r))
for emb in r.embedded_signatures:
    br = emb.sig_object['/ByteRange']; end = br[2] + br[3]
    rev = PdfFileReader(io.BytesIO(data[:end]), strict=False)   # exactly the bytes this signature covers
    print(f'{emb.field_name} covers bytes 0..{end}:', values(rev))
# the DSS report: signed length per signature and the post-signature modifications it lists
rep = json.load(open(sys.argv[2]))
for s in rep['DiagnosticData']['Signature']:
    rv = s['PDFRevision']; print('DSS', rv['SignatureField'][0]['name'], 'ByteRange', rv['PDFSignatureDictionary']['SignatureByteRange'],
      '| /V modifications after it:', [m['value'].split(' R ')[-2] + ' R /V' for m in rv['ModificationDetection']['ObjectModifications']['SignatureOrFormFill'] if m['value'].endswith('/V') and m['action']=='MODIFICATION'] if rv.get('ModificationDetection') else [])
