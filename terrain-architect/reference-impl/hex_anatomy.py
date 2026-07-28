"""Hex grid ANATOMY — a labelled figure for chapter `26`, whose geometry is 700 lines of prose
with nothing to look at. Six panels, each settling something the text has to say twice:

  a. the LATTICE and its two vertex classes — N centres (degree 6) and 2N corners (degree 3),
     with the two lengths that are constantly confused: cellSize (centre->centre, the only
     neighbour distance) and s = cellSize/sqrt(3) (centre->corner, and the tile edge);
  b. the RHOMBILLE tiling — 3N diamonds, one per neighbour PAIR, vertices alternating
     centre/corner, in the three orientations that make the tumbling-blocks illusion;
  c. the two diamonds SIDE BY SIDE, because they are easy to conflate and I did: the rhombille
     diamond (side s, 2 centres + 2 corners) against the ARRAY diamond of the sheared 2D
     storage (side cellSize, FOUR centres) — same 60/120 shape, sqrt(3) larger, turned 30 deg;
  d. the three MESHES — dual (N verts, ~2N tris), 6-triangle centre fan (3N, 6N), corner-only
     (2N, 4N);
  e. the tile TRIANGULATIONS — the centre fan's six equilaterals (min angle 60) against the two
     corner-only families, whose min angle is 30 for all 14 of them;
  f. the H/3 result — a one-cell spike rendered by both tile meshes, in cross-section: the fan
     gives a cone at full H, corner-only gives a flat plateau at H/3, and a ramp cannot tell
     them apart.

Writes `hex_anatomy.png`. Drawn at 3x and downsampled, since ImageDraw has no antialiasing.
Needs Pillow (pip install pillow). Run: `python hex_anatomy.py`.
"""
import math

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                                                    # pragma: no cover
    raise SystemExit("hex_anatomy needs Pillow for the labels:  pip install pillow")

SS = 3                                        # supersample factor
PANEL_W, PANEL_H = 620, 470
COLS, ROWS = 3, 2
PAD, TOP = 26, 76

INK = (28, 30, 36)
FAINT = (176, 181, 190)
MID = (110, 116, 126)
CENTRE_C = (196, 62, 44)                      # the N centres — real samples
CORNER_C = (38, 96, 168)                      # the 2N corners — means of 3
RHOMB = [(236, 214, 176), (208, 176, 132), (176, 140, 100)]   # tumbling-blocks trio
ARRAY_C = (54, 132, 96)
WARN = (196, 62, 44)


# Pillow's built-in bitmap font has no glyph for the maths this figure needs (sqrt, subscripts,
# multiplication sign), and renders them as tofu. Prefer any system TrueType; fall back to the
# built-in, and ASCII-fold the risky glyphs so the figure is still correct when it does.
_TTF_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
)
_ASCII_FOLD = str.maketrans({"√": "v", "×": "x", "—": "-", "–": "-", "₄": "4", "·": "-", "≤": "<="})


def _ttf_path():
    import os
    for p in _TTF_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


_TTF = _ttf_path()


def _font(sz):
    if _TTF:
        return ImageFont.truetype(_TTF, sz * SS)
    return ImageFont.load_default(size=sz * SS)


def _text(dr, xy, s, sz=15, fill=INK, anchor="la"):
    if not _TTF:
        s = s.translate(_ASCII_FOLD)
    dr.text((xy[0] * SS, xy[1] * SS), s, font=_font(sz), fill=fill, anchor=anchor)


def _line(dr, p0, p1, fill=INK, w=1.4):
    dr.line([(p0[0] * SS, p0[1] * SS), (p1[0] * SS, p1[1] * SS)], fill=fill,
            width=max(1, int(round(w * SS))))


def _poly(dr, pts, fill=None, outline=None, w=1.4):
    q = [(p[0] * SS, p[1] * SS) for p in pts]
    dr.polygon(q, fill=fill, outline=outline, width=max(1, int(round(w * SS))))


def _dot(dr, p, r, fill):
    dr.ellipse([(p[0] - r) * SS, (p[1] - r) * SS, (p[0] + r) * SS, (p[1] + r) * SS], fill=fill)


# --------------------------------------------------------------------------- #
# lattice geometry (pointy-top axial), in panel-local pixels

def _geom(s):
    """s = circumradius (centre->corner) in px. Returns (centre_fn, corners_fn, cellsize)."""
    cs = math.sqrt(3) * s                                  # centre->centre
    B = np.array([[cs, cs * 0.5], [0.0, cs * math.sqrt(3) / 2]])

    def centre(q, r):
        v = B @ np.array([q, r], dtype=float)
        return float(v[0]), float(v[1])

    def corners(q, r):
        cx, cy = centre(q, r)
        return [(cx + s * math.cos(math.radians(30 + 60 * k)),
                 cy + s * math.sin(math.radians(30 + 60 * k))) for k in range(6)]

    return centre, corners, cs


NB = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def _cells(rq, rr):
    return [(q, r) for q in range(-rq, rq + 1) for r in range(-rr, rr + 1)]


def _off(pts, dx, dy):
    return [(p[0] + dx, p[1] + dy) for p in pts]


# --------------------------------------------------------------------------- #
# panels

def _panel_a(dr, ox, oy):
    _text(dr, (ox, oy), "a.  the lattice: two vertex classes, two lengths", 17)
    _text(dr, (ox, oy + 24), "N centres (degree 6, real samples) · 2N corners (degree 3, means of 3)",
          13, MID)
    s = 40.0
    centre, corners, cs = _geom(s)
    cx0, cy0 = ox + 300, oy + 215
    for q, r in _cells(2, 2):
        c = centre(q, r)
        if abs(c[0]) > 290 or abs(c[1]) > 148:
            continue
        _poly(dr, _off(corners(q, r), cx0, cy0), outline=FAINT, w=1.2)
    for q, r in _cells(2, 2):
        c = centre(q, r)
        if abs(c[0]) > 290 or abs(c[1]) > 148:
            continue
        for p in corners(q, r):
            _dot(dr, (p[0] + cx0, p[1] + cy0), 3.0, CORNER_C)
        _dot(dr, (c[0] + cx0, c[1] + cy0), 4.4, CENTRE_C)
    # the two lengths
    o = centre(0, 0)
    n = centre(*NB[0])
    _line(dr, (o[0] + cx0, o[1] + cy0), (n[0] + cx0, n[1] + cy0), CENTRE_C, 2.4)
    _text(dr, ((o[0] + n[0]) / 2 + cx0, (o[1] + n[1]) / 2 + cy0 - 16), "cellSize", 13, CENTRE_C, "ma")
    k = corners(0, 0)[1]
    _line(dr, (o[0] + cx0, o[1] + cy0), (k[0] + cx0, k[1] + cy0), CORNER_C, 2.4)
    _text(dr, (k[0] + cx0 + 6, k[1] + cy0 - 20), "s = cellSize/√3", 13, CORNER_C)
    _text(dr, (ox, oy + 400), "all 6 neighbours at ONE distance — the D4/D8 fork cannot be written",
          13, INK)
    _text(dr, (ox, oy + 422), "s is also the shared tile edge, and the corner ring radius", 13, MID)


def _panel_b(dr, ox, oy):
    _text(dr, (ox, oy), "b.  the rhombille tiling: 3N diamonds", 17)
    _text(dr, (ox, oy + 24), "one per neighbour PAIR — vertices alternate centre / corner", 13, MID)
    s = 46.0
    centre, corners, cs = _geom(s)
    cx0, cy0 = ox + 300, oy + 250
    seen = set()
    for q, r in _cells(2, 2):
        for k, (dq, dr_) in enumerate(NB):
            nb = (q + dq, r + dr_)
            key = frozenset([(q, r), nb])
            if key in seen:
                continue
            seen.add(key)
            A, Bc = centre(q, r), centre(*nb)
            if max(abs(A[0]), abs(Bc[0])) > 250 or max(abs(A[1]), abs(Bc[1])) > 180:
                continue
            ca, cb = corners(q, r), corners(*nb)
            shared = [p for p in ca if any(abs(p[0] - t[0]) < 1e-6 and abs(p[1] - t[1]) < 1e-6
                                           for t in cb)]
            if len(shared) != 2:
                continue
            quad = [A, shared[0], Bc, shared[1]]
            _poly(dr, _off(quad, cx0, cy0), fill=RHOMB[k % 3], outline=(255, 255, 255), w=1.2)
    # highlight one diamond and name its diagonals
    A, Bc = centre(0, 0), centre(1, 0)
    ca, cb = corners(0, 0), corners(1, 0)
    sh = [p for p in ca if any(abs(p[0] - t[0]) < 1e-6 and abs(p[1] - t[1]) < 1e-6 for t in cb)]
    _poly(dr, _off([A, sh[0], Bc, sh[1]], cx0, cy0), outline=INK, w=2.6)
    _line(dr, (A[0] + cx0, A[1] + cy0), (Bc[0] + cx0, Bc[1] + cy0), CENTRE_C, 2.2)
    _line(dr, (sh[0][0] + cx0, sh[0][1] + cy0), (sh[1][0] + cx0, sh[1][1] + cy0), CORNER_C, 2.2)
    _dot(dr, (A[0] + cx0, A[1] + cy0), 4.2, CENTRE_C)
    _dot(dr, (Bc[0] + cx0, Bc[1] + cy0), 4.2, CENTRE_C)
    for p in sh:
        _dot(dr, (p[0] + cx0, p[1] + cy0), 3.4, CORNER_C)
    _text(dr, (ox, oy + 392), "long diagonal = cellSize = the neighbour link", 13, CENTRE_C)
    _text(dr, (ox, oy + 412), "short diagonal = s = the shared tile edge", 13, CORNER_C)
    _text(dr, (ox, oy + 434), "3 orientations at 0°/60°/120° — the tumbling-blocks cube", 13, MID)


def _panel_c(dr, ox, oy):
    _text(dr, (ox, oy), "c.  two diamonds, easily conflated", 17)
    _text(dr, (ox, oy + 24), "same 60°–120° shape — but NOT the same tiling", 13, MID)
    s = 52.0
    centre, corners, cs = _geom(s)
    cx0, cy0 = ox + 300, oy + 200
    for q, r in _cells(2, 2):
        c = centre(q, r)
        if abs(c[0]) > 285 or abs(c[1]) > 132:
            continue
        _poly(dr, _off(corners(q, r), cx0, cy0), outline=FAINT, w=1.0)
        _dot(dr, (c[0] + cx0, c[1] + cy0), 3.4, CENTRE_C)
    # rhombille diamond: 2 centres + 2 corners
    A, Bc = centre(0, 0), centre(1, 0)
    ca, cb = corners(0, 0), corners(1, 0)
    sh = [p for p in ca if any(abs(p[0] - t[0]) < 1e-6 and abs(p[1] - t[1]) < 1e-6 for t in cb)]
    _poly(dr, _off([A, sh[0], Bc, sh[1]], cx0, cy0), fill=RHOMB[1], outline=INK, w=2.4)
    for p in sh:
        _dot(dr, (p[0] + cx0, p[1] + cy0), 3.4, CORNER_C)
    # array diamond: the index quad (q,r),(q+1,r),(q,r+1),(q+1,r+1) — FOUR centres
    quad = [centre(0, 0), centre(1, 0), centre(1, 1), centre(0, 1)]
    _poly(dr, _off(quad, cx0, cy0), outline=ARRAY_C, w=3.0)
    for p in quad:
        _dot(dr, (p[0] + cx0, p[1] + cy0), 4.2, ARRAY_C)
    _text(dr, (ox, oy + 372), "rhombille — 3N, side s, centre·corner·centre·corner", 13, INK)
    _text(dr, (ox, oy + 394), "array quad — N, side cellSize, FOUR centres", 13, ARRAY_C)
    _text(dr, (ox, oy + 420), "√3 larger, turned 30° — one per array element,", 13, MID)
    _text(dr, (ox, oy + 440), "and it is what makes the storage a sheared square array", 13, MID)


def _panel_d(dr, ox, oy):
    _text(dr, (ox, oy), "d.  three meshes over one field", 17)
    _text(dr, (ox, oy + 24), "per N cells — the fork is not about triangle count", 13, MID)
    s = 26.0
    centre, corners, cs = _geom(s)
    labels = [("dual mesh", "N verts · ~2N tris"),
              ("6-triangle fan", "3N · 6N"),
              ("corner-only", "2N · 4N")]
    for i, (title, sub) in enumerate(labels):
        cx0 = ox + 100 + i * 200
        cy0 = oy + 190
        cells = [(q, r) for q in range(-1, 2) for r in range(-1, 2)]
        if i == 0:                                        # dual: triangulate the centres
            for q, r in cells:
                A = centre(q, r)
                for dq, dr_ in [(1, 0), (0, 1), (-1, 1)]:
                    nb = (q + dq, r + dr_)
                    if nb in cells:
                        Bc = centre(*nb)
                        _line(dr, (A[0] + cx0, A[1] + cy0), (Bc[0] + cx0, Bc[1] + cy0), MID, 1.2)
            for q, r in cells:
                A = centre(q, r)
                _dot(dr, (A[0] + cx0, A[1] + cy0), 3.2, CENTRE_C)
        else:
            for q, r in cells:
                cc = corners(q, r)
                _poly(dr, _off(cc, cx0, cy0), outline=MID, w=1.2)
                if i == 1:                                # fan through the centre
                    A = centre(q, r)
                    for p in cc:
                        _line(dr, (A[0] + cx0, A[1] + cy0), (p[0] + cx0, p[1] + cy0), CENTRE_C, 1.0)
                    _dot(dr, (A[0] + cx0, A[1] + cy0), 3.0, CENTRE_C)
                else:                                     # corner-only: ear-and-core
                    for a, b in ((0, 2), (2, 4), (4, 0)):
                        _line(dr, (cc[a][0] + cx0, cc[a][1] + cy0),
                              (cc[b][0] + cx0, cc[b][1] + cy0), CORNER_C, 1.0)
                for p in cc:
                    _dot(dr, (p[0] + cx0, p[1] + cy0), 2.2, CORNER_C)
        _text(dr, (cx0, oy + 330), title, 14, INK, "ma")
        _text(dr, (cx0, oy + 352), sub, 13, MID, "ma")
    _text(dr, (ox, oy + 400), "the cell's own sample is a VERTEX in the first two, and", 13, INK)
    _text(dr, (ox, oy + 422), "absent from the third — which is what panel f measures", 13, INK)


def _panel_e(dr, ox, oy):
    _text(dr, (ox, oy), "e.  triangulating one visible tile", 17)
    _text(dr, (ox, oy + 24), "14 corner-only triangulations (Catalan C₄); 6 are fans", 13, MID)
    s = 74.0
    _, corners, _ = _geom(s)
    cc0 = corners(0, 0)
    for i, (title, diags, ang) in enumerate([
            ("centre fan", None, "min angle 60°"),
            ("ear-and-core", ((0, 2), (2, 4), (4, 0)), "min angle 30°"),
            ("corner fan", ((0, 2), (0, 3), (0, 4)), "min angle 30°")]):
        cx0 = ox + 105 + i * 200
        cy0 = oy + 175
        cc = _off(cc0, cx0, cy0)
        _poly(dr, cc, outline=INK, w=2.0)
        if diags is None:
            for p in cc:
                _line(dr, (cx0, cy0), p, CENTRE_C, 1.6)
            _dot(dr, (cx0, cy0), 4.0, CENTRE_C)
        else:
            for a, b in diags:
                _line(dr, cc[a], cc[b], CORNER_C, 1.6)
        for p in cc:
            _dot(dr, p, 3.0, CORNER_C)
        _text(dr, (cx0, oy + 278), title, 14, INK, "ma")
        _text(dr, (cx0, oy + 300), ang, 13, CENTRE_C if diags is None else MID, "ma")
    _text(dr, (ox, oy + 344), "the fan's six triangles are EQUILATERAL — the best any", 13, INK)
    _text(dr, (ox, oy + 366), "triangulation of this cell can do. Every corner-only one", 13, INK)
    _text(dr, (ox, oy + 388), "contains at least two 30°–120°–30° ears, so 30° is the", 13, INK)
    _text(dr, (ox, oy + 410), "ceiling for all 14. Ear-and-core keeps 3-fold symmetry;", 13, INK)
    _text(dr, (ox, oy + 432), "a corner fan keeps one mirror.", 13, INK)


def _panel_f(dr, ox, oy):
    _text(dr, (ox, oy), "f.  what corner-only costs: ×1/3", 17)
    _text(dr, (ox, oy + 24), "one-cell spike of height H, in cross-section", 13, MID)
    x0, ybase, w, hpx = ox + 62, oy + 300, 470, 190
    _line(dr, (x0, ybase), (x0 + w, ybase), MID, 1.4)
    _line(dr, (x0, ybase), (x0, ybase - hpx - 14), MID, 1.4)
    _text(dr, (x0 - 10, ybase - hpx), "H", 14, INK, "ra")
    _text(dr, (x0 - 10, ybase - hpx / 3.0), "H/3", 14, WARN, "ra")
    _line(dr, (x0, ybase - hpx), (x0 + w, ybase - hpx), FAINT, 1.0)
    _line(dr, (x0, ybase - hpx / 3.0), (x0 + w, ybase - hpx / 3.0), FAINT, 1.0)
    cxm = x0 + w / 2
    step = 74.0
    # 6-fan: corners at H/3, centre at H -> a cone
    fan = [(cxm - 2 * step, ybase), (cxm - step, ybase), (cxm - step / 2, ybase - hpx / 3.0),
           (cxm, ybase - hpx), (cxm + step / 2, ybase - hpx / 3.0), (cxm + step, ybase),
           (cxm + 2 * step, ybase)]
    for i in range(len(fan) - 1):
        _line(dr, fan[i], fan[i + 1], CENTRE_C, 2.6)
    # corner-only: all six corners at H/3, no centre vertex -> a flat plateau
    flat = [(cxm - 2 * step, ybase), (cxm - step, ybase), (cxm - step / 2, ybase - hpx / 3.0),
            (cxm + step / 2, ybase - hpx / 3.0), (cxm + step, ybase), (cxm + 2 * step, ybase)]
    for i in range(len(flat) - 1):
        _line(dr, flat[i], flat[i + 1], CORNER_C, 2.6)
    _dot(dr, (cxm, ybase - hpx), 4.2, CENTRE_C)
    _text(dr, (cxm + 12, ybase - hpx - 4), "6-fan: centre vertex IS the sample", 13, CENTRE_C)
    _text(dr, (cxm + 96, ybase - hpx / 3.0 - 24), "corner-only: flat plateau", 13, CORNER_C, "ma")
    _text(dr, (ox, oy + 342), "corners are means of 3 cells, so the spike reaches the", 13, INK)
    _text(dr, (ox, oy + 364), "surface only through them: (H+0+0)/3 at all six.", 13, INK)
    _text(dr, (ox, oy + 392), "Both meshes reproduce an AFFINE field exactly, so a ramp", 13, WARN)
    _text(dr, (ox, oy + 414), "cannot tell them apart — the detector is an impulse (`09`).", 13, WARN)


PANELS = [_panel_a, _panel_b, _panel_c, _panel_d, _panel_e, _panel_f]


def build():
    W = PAD * 2 + COLS * PANEL_W
    H = TOP + PAD + ROWS * PANEL_H
    img = Image.new("RGB", (W * SS, H * SS), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    _text(dr, (PAD, 16), "Hexagonal grids — anatomy", 25)
    _text(dr, (PAD, 46), "chapter 26 · pointy-top axial · s = cellSize/√3", 14, MID)
    for i, fn in enumerate(PANELS):
        ox = PAD + (i % COLS) * PANEL_W
        oy = TOP + (i // COLS) * PANEL_H
        fn(dr, ox, oy)
    return img.resize((W, H), Image.LANCZOS)


if __name__ == "__main__":
    build().save("hex_anatomy.png")
    print("wrote hex_anatomy.png")
