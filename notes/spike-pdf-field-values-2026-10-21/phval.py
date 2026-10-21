import sys, logging
logging.disable(logging.CRITICAL)
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.settings import KeyUsageConstraints
from pyhanko_certvalidator import ValidationContext
for f in sys.argv[1:]:
    r = PdfFileReader(open(f, 'rb'), strict=False)
    print('#', f)
    for emb in r.embedded_signatures:
        vc = ValidationContext(trust_roots=[emb.signer_cert], allow_fetching=False, revocation_mode='soft-fail')
        st = validate_pdf_signature(emb, vc, key_usage_settings=KeyUsageConstraints(key_usage=set(), match_all_key_usages=False))
        dr = emb.diff_result
        print('  ', emb.field_name, '| intact', st.intact, '| coverage', st.coverage.name, '| modification', st.modification_level.name if st.modification_level else None,
              '| docmdp_ok', st.docmdp_ok, '|', type(dr).__name__, (str(dr) if type(dr).__name__ == 'SuspiciousModification' else ''))
