"""Writes a valid PDF of N pages; each page shows a random grayscale image (incompressible) plus text.

usage: genpdf.py out.pdf pages bytes_per_page_image
"""
import os
import sys
import zlib

out, pages, img_bytes = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

objs = []  # index i -> bytes for object i+1


def add(body: bytes) -> int:
    objs.append(body)
    return len(objs)


catalog = add(b'')
pages_obj = add(b'')
font = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
kids = []
for p in range(pages):
    if img_bytes > 0:
        side = max(1, int(img_bytes ** 0.5))
        raw = zlib.compress(os.urandom(side * side), 0)
        img = add(b'<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /DeviceGray '
                  b'/BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n' % (side, side, len(raw))
                  + raw + b'\nendstream')
        xo = b'/XObject << /Im1 %d 0 R >>' % img
        draw = b'q 400 0 0 400 100 300 cm /Im1 Do Q '
    else:
        xo, draw = b'', b''
    text = b''.join(b'BT /F1 9 Tf 50 %d Td (Line %d of page %d - lorem ipsum dolor sit amet) Tj ET ' % (780 - 12 * i, i, p + 1)
                    for i in range(60 if img_bytes == 0 else 3))
    content = draw + text
    c = add(b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream')
    pg = add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 %d 0 R >> %s >> '
             b'/Contents %d 0 R >>' % (pages_obj, font, xo, c))
    kids.append(pg)

objs[catalog - 1] = b'<< /Type /Catalog /Pages %d 0 R >>' % pages_obj
objs[pages_obj - 1] = b'<< /Type /Pages /Kids [%s] /Count %d >>' % (b' '.join(b'%d 0 R' % k for k in kids), len(kids))

with open(out, 'wb') as f:
    f.write(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n')
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(f.tell())
        f.write(b'%d 0 obj\n' % i + body + b'\nendobj\n')
    xref = f.tell()
    f.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
    for o in offsets:
        f.write(b'%010d 00000 n \n' % o)
    f.write(b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, catalog, xref))
