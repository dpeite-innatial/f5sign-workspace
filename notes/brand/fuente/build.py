"""Build F5Sign logo proposals from the traced Factor5 wordmark.

Coordinates live in the trace's pixel space (cover of the manual at 300ppi).
New glyphs are drawn upright ("deskewed") on the measured Factor5 grid and then
sheared by the measured 12.5 degree slant, so they share the italic of F and 5.
"""
import json
import math
import os
import sys

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

OUT = sys.argv[1]
RED = '#9c1623'  # manual 1.2
INK = '#1d1d1b'
T = math.tan(math.radians(12.5))
BASE = 262.0  # baseline row used for the shear
KAPPA = 0.5523

tr = json.load(open(os.path.join(os.path.dirname(__file__), 'traced.json')))
SH = tr['shapes']
# contour indices from the trace: 0 = F (stem + top bar), 7 = F mid bar, 1 = the 5
F_SHAPES = [SH[0], SH[7]]
FIVE = SH[1]


def shear(x, y):
    return (x + (BASE - y) * T, y)


def deskew_x(x, y):
    return x - (BASE - y) * T


# ---------- traced glyphs --------------------------------------------------
def poly_d(pts):
    return 'M' + ' L'.join('%.1f %.1f' % tuple(p) for p in pts) + ' Z'


def five_at_cap(left_deskewed):
    """The 5 scaled uniformly to the F's cap height, placed on the grid."""
    top, bottom = 20.0, 261.5
    y0, y1 = min(p[1] for p in FIVE), max(p[1] for p in FIVE)
    s = (bottom - top) / (y1 - y0)
    pts = [(x * s, top + (y - y0) * s) for x, y in FIVE]
    dx = left_deskewed - min(deskew_x(x, y) for x, y in pts)
    return [(x + dx, y) for x, y in pts]


# ---------- constructed glyphs --------------------------------------------
def rounded(points, radii, dx, dy):
    """Rectilinear polygon (upright) with per-vertex radii -> sheared path d."""
    n = len(points)
    segs = []
    for i in range(n):
        p0, p1, p2 = points[i - 1], points[i], points[(i + 1) % n]
        r = radii[i]
        l1 = math.dist(p0, p1)
        l2 = math.dist(p1, p2)
        r = min(r, l1 / 2, l2 / 2)
        a = (p1[0] + (p0[0] - p1[0]) * r / l1, p1[1] + (p0[1] - p1[1]) * r / l1)
        b = (p1[0] + (p2[0] - p1[0]) * r / l2, p1[1] + (p2[1] - p1[1]) * r / l2)
        c1 = (a[0] + (p1[0] - a[0]) * KAPPA, a[1] + (p1[1] - a[1]) * KAPPA)
        c2 = (b[0] + (p1[0] - b[0]) * KAPPA, b[1] + (p1[1] - b[1]) * KAPPA)
        segs.append((a, c1, c2, b))

    def P(q):
        x, y = shear(q[0] + dx, q[1] + dy)
        return '%.1f %.1f' % (x, y)

    d = 'M' + P(segs[0][3])
    for a, c1, c2, b in segs[1:] + segs[:1]:
        d += ' L' + P(a) + ' C' + P(c1) + ' ' + P(c2) + ' ' + P(b)
    return d + ' Z'


# Small-cap grid measured on ACTOR: 261 wide, 177 tall, stems 81.
W, H, ST = 261.0, 177.0, 81.0
R, r = 45.0, 6.0
SC_TOP = 84.5  # small-cap top row; baseline at SC_TOP + H = 261.5


def glyph_S(dx):
    b, g = 40.0, 28.5  # three bars need thinner horizontals than ACTOR's 48
    y1, y2, y3, y4 = b, b + g, 2 * b + g, 2 * b + 2 * g
    pts = [(0, 0), (W, 0), (W, y1), (ST, y1), (ST, y2), (W, y2), (W, H), (0, H),
           (0, y4), (W - ST, y4), (W - ST, y3), (0, y3)]
    rad = [R, r, r, r, r, R, R, r, r, r, r, R]
    return [rounded(pts, rad, dx, SC_TOP)]


def glyph_I(dx):
    pts = [(0, 0), (ST, 0), (ST, H), (0, H)]
    return [rounded(pts, [r] * 4, dx, SC_TOP)]


def glyph_G(dx):
    mouth, spur = 48.0, 129.0  # top bar ends at 48, the spur sits on ACTOR's mid band
    pts = [(0, 0), (W, 0), (W, mouth), (ST, mouth), (ST, spur), (150, spur), (150, 80),
           (W, 80), (W, H), (0, H)]
    rad = [R, r, r, r, r, r, r, r, R, R]
    return [rounded(pts, rad, dx, SC_TOP)]


def glyph_N(dx):
    pts = [(0, 0), (W, 0), (W, H), (W - ST, H), (W - ST, 48), (ST, 48), (ST, H), (0, H)]
    rad = [R, R, r, r, r, r, r, r]
    return [rounded(pts, rad, dx, SC_TOP)]


ADV_GAP = 29.0  # measured gap between ACTOR glyphs


def wordmark_B():
    """F5 at cap height + SIGN in small caps, all in the Factor5 construction."""
    parts = {'f5': [poly_d(s) for s in F_SHAPES], 'sign': []}
    x = 18.0 + W + ADV_GAP  # the F occupies deskewed 18..278
    parts['f5'].append(poly_d(five_at_cap(x)))
    x += W + ADV_GAP
    parts['sign'] += glyph_S(x); x += W + ADV_GAP
    parts['sign'] += glyph_I(x); x += ST + ADV_GAP
    parts['sign'] += glyph_G(x); x += W + ADV_GAP
    parts['sign'] += glyph_N(x); x += W
    return parts, x


# ---------- corporate type (Arial-metric Liberation Sans) as outlines -------
def text_d(text, font_path, cap_px, x, baseline, tracking=0.0):
    font = TTFont(font_path)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    cap = font['OS/2'].sCapHeight or 1409
    s = cap_px / cap
    hmtx = font['hmtx']
    d = []
    for ch in text:
        name = cmap[ord(ch)]
        rec = DecomposingRecordingPen(gs)
        gs[name].draw(TransformPen(rec, (s, 0, 0, -s, x, baseline)))
        for op, args in rec.value:
            if op == 'moveTo':
                d.append('M%.1f %.1f' % args[0])
            elif op == 'lineTo':
                d.append('L%.1f %.1f' % args[0])
            elif op == 'qCurveTo':
                # TrueType implied on-curve points -> explicit quadratic segments
                pts = list(args)
                for i in range(len(pts) - 1):
                    c = pts[i]
                    end = pts[i + 1] if i == len(pts) - 2 else (
                        (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2)
                    d.append('Q%.1f %.1f %.1f %.1f' % (c[0], c[1], end[0], end[1]))
            elif op == 'curveTo':
                d.append('C' + ' '.join('%.1f %.1f' % p for p in args))
            elif op in ('closePath', 'endPath'):
                d.append('Z')
        x += hmtx[name][0] * s + tracking
    return ' '.join(d), x


LIB = '/usr/share/fonts/truetype/liberation/'


def svg(paths, pad=24, extra_h=0):
    xs, ys = [], []
    import re
    for d, _ in paths:
        nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
        xs += nums[0::2]
        ys += nums[1::2]
    x0, y0, x1, y1 = min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad
    body = '\n'.join('  <path fill="%s" fill-rule="evenodd" d="%s"/>' % (c, d) for d, c in paths)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.0f %.0f %.0f %.0f">\n%s\n</svg>\n'
            % (x0, y0, x1 - x0, y1 - y0, body))


os.makedirs(OUT, exist_ok=True)
parts, right = wordmark_B()
f5 = ' '.join(parts['f5'])
sign = ' '.join(parts['sign'])

# B1: everything red, like FACTOR5
open(f'{OUT}/f5sign-b-rojo.svg', 'w').write(svg([(f5, RED), (sign, RED)]))
# B2: F5 red, SIGN ink
open(f'{OUT}/f5sign-b-bicolor.svg', 'w').write(svg([(f5, RED), (sign, INK)]))
# B lockup with tagline, the way FACTOR5 carries "Logistica de otra manera"
tag, _ = text_d('Firma electrónica', LIB + 'LiberationSans-Regular.ttf', 74, 24, 382)
open(f'{OUT}/f5sign-b-lema.svg', 'w').write(svg([(f5, RED), (sign, RED), (tag, INK)]))

# A: F5 in the Factor5 construction + "Sign" in the corporate sans (Arial family)
sign_txt, _ = text_d('Sign', LIB + 'LiberationSans-BoldItalic.ttf', 241, 18 + 2 * (W + ADV_GAP) + 30, 261.5)
open(f'{OUT}/f5sign-a.svg', 'w').write(svg([(f5, RED), (sign_txt, INK)]))

# Icon: F5 in white on the corporate red, for favicon / home-screen icon
import re
nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', f5)]
fx0, fx1 = min(nums[0::2]), max(nums[0::2])
fy0, fy1 = min(nums[1::2]), max(nums[1::2])
side = (fx1 - fx0) * 1.3
cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
icon = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%.1f %.1f %.1f %.1f">\n'
        '  <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s"/>\n'
        '  <path fill="#ffffff" fill-rule="evenodd" d="%s"/>\n</svg>\n'
        % (cx - side / 2, cy - side / 2, side, side, cx - side / 2, cy - side / 2, side, side,
           side * 0.22, RED, f5))
open(f'{OUT}/f5sign-icono.svg', 'w').write(icon)

# The traced FACTOR5 wordmark itself (red part), handy as a vector reference
allred = ' '.join(poly_d(s) for s in SH)
open(f'{OUT}/factor5-traza.svg', 'w').write(svg([(allred, RED)]))
print('ok', right)


# ---------- icons that carry SIGN ------------------------------------------
def bbox(ds):
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', ' '.join(ds))]
    return min(nums[0::2]), min(nums[1::2]), max(nums[0::2]), max(nums[1::2])


def placed(d, box, width, cx, top, fill=None, stroke=None, stroke_px=0):
    x0, y0, x1, y1 = box
    s = width / (x1 - x0)
    tx, ty = cx - (x0 + x1) / 2 * s, top - y0 * s
    if stroke:
        attrs = 'fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"' % (stroke, stroke_px / s)
    else:
        attrs = 'fill="%s" fill-rule="evenodd"' % fill
    return ('  <g transform="matrix(%.5f 0 0 %.5f %.2f %.2f)"><path %s d="%s"/></g>\n'
            % (s, s, tx, ty, attrs, d)), (y1 - y0) * s


SIDE = 512
F5_BOX, SIGN_BOX = bbox([f5]), bbox([sign])


def icon_svg(bg, body, border=None, full_bleed=False):
    edge = ' stroke="%s" stroke-width="4"' % border if border else ''
    if full_bleed:  # iOS masks the corners itself and wants no transparency
        rect = '  <rect width="%d" height="%d" fill="%s"/>\n' % (SIDE, SIDE, bg)
    else:
        rect = ('  <rect x="2" y="2" width="%d" height="%d" rx="%d" fill="%s"%s/>\n'
                % (SIDE - 4, SIDE - 4, SIDE * 0.22, bg, edge))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">\n%s%s</svg>\n'
            % (SIDE, SIDE, rect, body))


def stacked(f5_fill, sign_fill, width=356, gap=30):
    f5_h = (F5_BOX[3] - F5_BOX[1]) * width / (F5_BOX[2] - F5_BOX[0])
    sign_h = (SIGN_BOX[3] - SIGN_BOX[1]) * width / (SIGN_BOX[2] - SIGN_BOX[0])
    top = (SIDE - (f5_h + gap + sign_h)) / 2
    a, _ = placed(f5, F5_BOX, width, SIDE / 2, top, fill=f5_fill)
    b, _ = placed(sign, SIGN_BOX, width, SIDE / 2, top + f5_h + gap, fill=sign_fill)
    return a + b


open(f'{OUT}/f5sign-icono-apilado.svg', 'w').write(icon_svg(RED, stacked('#ffffff', '#ffffff')))
open(f'{OUT}/f5sign-icono-apilado-blanco.svg', 'w').write(
    icon_svg('#ffffff', stacked(RED, INK), border='#e2e8f0'))

# F5 over a signature stroke: the same hand the signer's home page draws
SIG = ('M44 128 C 52 104, 62 92, 66 104 C 70 116, 58 134, 64 133 C 72 132, 76 112, 84 114 '
       'C 90 116, 84 130, 92 129 C 100 128, 104 114, 111 116 C 117 118, 112 130, 120 128 '
       'C 131 125, 136 102, 143 108 C 148 112, 141 131, 151 128 C 162 124, 170 116, 184 117 '
       'C 196 118, 202 112, 210 104 M58 136 C 96 131, 146 132, 196 124')
SIG_BOX = (44, 92, 210, 136)
w = 350
f5_h = (F5_BOX[3] - F5_BOX[1]) * w / (F5_BOX[2] - F5_BOX[0])
sig_h = (SIG_BOX[3] - SIG_BOX[1]) * 330 / (SIG_BOX[2] - SIG_BOX[0])
top = (SIDE - (f5_h + 26 + sig_h)) / 2
a, _ = placed(f5, F5_BOX, w, SIDE / 2, top, fill='#ffffff')
b, _ = placed(SIG, SIG_BOX, 330, SIDE / 2 + 6, top + f5_h + 26, stroke='#ffffff', stroke_px=16)
open(f'{OUT}/f5sign-icono-firma.svg', 'w').write(icon_svg(RED, a + b))
print('icons ok')


# ---------- files for f5sign-signer/public ----------------------------------
PUB = os.environ.get('PUB')
if PUB:
    os.makedirs(f'{PUB}/brand', exist_ok=True)
    open(f'{PUB}/brand/f5sign-bicolor.svg', 'w').write(svg([(f5, RED), (sign, INK)], pad=2))
    open(f'{PUB}/brand/f5sign-rojo.svg', 'w').write(svg([(f5, RED), (sign, RED)], pad=2))
    open(f'{PUB}/favicon.svg', 'w').write(icon_svg(RED, a + b))
    open(os.environ['FULL_BLEED'], 'w').write(icon_svg(RED, a + b, full_bleed=True))
    print('public ok')
