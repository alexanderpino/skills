"""Grazing-impact ANATOMY — a labelled figure of a very oblique (~2°) hypervelocity impact,
documenting the morphology this skill settled on after checking the primary sources:

  * the CAVITY is elongated (only <~12°; Bottke 2000 / Elbeshausen 2013) but the excavation is
    still an explosion, so the hole is a broken ellipse, not a scraped trench;
  * it is DEEPER UP-RANGE — deepest point and steepest wall on the up-range side (first contact /
    peak energy; Schultz, arXiv 2308.01876) — shallowing down-range where material is plowed out;
  * the UP-RANGE rim is a depressed 'forbidden' arc; maximum rim uplift is TRANSVERSE to the path;
  * ejecta forms a cross-range BUTTERFLY (<~5° lab, ~10° lunar obs) with collimated DOWN-RANGE
    rays (at true grazing the projectile ricochets to a downrange companion — Messier A — which
    this single-stamp model does not create).

Top panel: map (hillshade). Bottom panel: elevation cross-section along the trajectory axis.
Writes `crater_anatomy.png`. The terrain is numpy-only; the LABELS need Pillow (pip install
pillow). Run: `python crater_anatomy.py`.
"""
import numpy as np

import crater
import crater_demo
import render

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                                                    # pragma: no cover
    raise SystemExit("crater_anatomy needs Pillow for the labels:  pip install pillow")

ANGLE, L, SEED = 2.0, 200.0, 5
N = 460                                                                 # crater render size (px)
INK = (25, 27, 32)
ACCENT = (150, 40, 30)


def _font(sz):
    return ImageFont.load_default(size=sz)


def _text(dr, xy, s, sz=17, fill=INK, anchor="la"):
    dr.text(xy, s, font=_font(sz), fill=fill, anchor=anchor)


def _leader(dr, tx, ty, px, py, fill=INK):
    """A thin leader line from a label anchor (tx,ty) to a feature point (px,py), dot at the tip."""
    dr.line([(tx, ty), (px, py)], fill=fill, width=2)
    dr.ellipse([px - 4, py - 4, px + 4, py + 4], fill=ACCENT)


def _arrow(dr, x0, y0, x1, y1, fill=INK, w=4):
    dr.line([(x0, y0), (x1, y1)], fill=fill, width=w)
    ang = np.arctan2(y1 - y0, x1 - x0)
    dr.polygon([(x1, y1),
                (x1 - 15 * np.cos(ang - 0.4), y1 - 15 * np.sin(ang - 0.4)),
                (x1 - 15 * np.cos(ang + 0.4), y1 - 15 * np.sin(ang + 0.4))], fill=fill)


def build():
    # --- terrain -------------------------------------------------------------------
    D = crater.final_crater(crater.transient_crater_diameter(L, 20000.0, angle=ANGLE))[0]
    cs = D * crater._ellipticity(ANGLE) / (N * 0.60)
    h, info = crater_demo.stamp_impact_natural(np.zeros((N, N)), N // 2, N // 2, cs,
                                               L=L, v=20000.0, angle=ANGLE, azimuth=0.0, seed=SEED)
    depth = info["depth"]
    shade = render.hillshade(h / depth, cellsize=1.0, azimuth=315, altitude=38, z_factor=6.0)
    crater_img = Image.fromarray(shade)

    # --- canvas: map panel on top, cross-section below -----------------------------
    W = 1000
    map_h, xs_h = 500, 340
    canvas = Image.new("RGB", (W, map_h + xs_h + 30), (247, 245, 240))
    dr = ImageDraw.Draw(canvas)
    mx, my = (W - N) // 2, 30                                           # map image top-left
    canvas.paste(crater_img, (mx, my))
    cxp, cyp = mx + N // 2, my + N // 2                                 # crater centre on canvas

    _text(dr, (W // 2, 6), "Grazing hypervelocity impact  (~2 deg from horizontal)  -  anatomy",
          sz=20, anchor="ma")
    # trajectory arrow across the top of the map
    _arrow(dr, mx + 20, my + 24, mx + N - 20, my + 24, fill=(60, 60, 70), w=4)
    _text(dr, (mx + N // 2, my + 6), "impactor path  (up-range -> down-range)", sz=15,
          fill=(60, 60, 70), anchor="ma")

    R = 0.5 * D / cs                                                    # crater radius (px)
    # labels + leaders (down-range = +x = right)
    _text(dr, (12, my + 150), "UP-RANGE end:", sz=17, fill=ACCENT)
    _text(dr, (12, my + 170), "deeper floor,", sz=15)
    _text(dr, (12, my + 188), "steeper wall", sz=15)
    _leader(dr, 120, my + 175, int(cxp - 0.45 * R), cyp)

    _text(dr, (12, my + 250), "up-range rim:", sz=17, fill=ACCENT)
    _text(dr, (12, my + 270), "depressed", sz=15)
    _text(dr, (12, my + 288), "'forbidden' arc", sz=15)
    _leader(dr, 130, my + 275, int(cxp - 1.02 * R * crater._ellipticity(ANGLE)), cyp)

    _text(dr, (W - 12, my + 150), "DOWN-RANGE end:", sz=17, fill=ACCENT, anchor="ra")
    _text(dr, (W - 12, my + 170), "shallower,", sz=15, anchor="ra")
    _text(dr, (W - 12, my + 188), "plowed out", sz=15, anchor="ra")
    _leader(dr, W - 150, my + 175, int(cxp + 0.5 * R), cyp)

    _text(dr, (W - 12, my + 250), "down-range ejecta", sz=17, fill=ACCENT, anchor="ra")
    _text(dr, (W - 12, my + 270), "(collimated; real", sz=15, anchor="ra")
    _text(dr, (W - 12, my + 288), "impacts ricochet to", sz=15, anchor="ra")
    _text(dr, (W - 12, my + 306), "a 2nd crater)", sz=15, anchor="ra")
    _leader(dr, W - 175, my + 275, int(cxp + 1.5 * R * crater._ellipticity(ANGLE)), cyp - 10)

    _text(dr, (mx + N // 2, my + N - 4),
          "transverse butterfly wings  (max rim uplift + ejecta across the path)",
          sz=15, fill=ACCENT, anchor="ma")
    _leader(dr, mx + N // 2 - 120, my + N - 12, cxp, int(cyp - 1.05 * R))
    _leader(dr, mx + N // 2 + 120, my + N - 12, cxp, int(cyp + 1.05 * R))

    # --- cross-section along the trajectory axis (row through the centre) ----------
    x0, x1 = 70, W - 70
    yb, yt = map_h + 30 + xs_h - 40, map_h + 30 + 34                    # bottom / top of plot
    prof = h[N // 2 - 2:N // 2 + 3].mean(axis=0) / depth                # elevation in units of depth
    e_hi, e_lo = 0.55, float(prof.min()) - 0.1
    def X(col): return x0 + col / (N - 1) * (x1 - x0)
    def Y(e): return yt + (e_hi - e) / (e_hi - e_lo) * (yb - yt)

    dr.rectangle([x0, yt - 6, x1, yb], outline=(200, 196, 188), width=1)
    # h = 0 datum
    for xx in range(int(x0), int(x1), 10):
        dr.line([(xx, Y(0)), (xx + 5, Y(0))], fill=(120, 120, 120), width=1)
    _text(dr, (x1 + 4, Y(0)), "original", sz=12, fill=(120, 120, 120), anchor="lm")
    _text(dr, (x1 + 4, Y(0) + 13), "ground", sz=12, fill=(120, 120, 120), anchor="lm")
    # filled terrain cross-section
    pts = [(X(c), Y(prof[c])) for c in range(N)]
    dr.polygon([(X(0), yb)] + pts + [(X(N - 1), yb)], fill=(222, 210, 190))
    dr.line(pts, fill=(70, 55, 40), width=3)

    imin = int(np.argmin(prof))
    _leader(dr, X(imin) - 60, Y(prof[imin]) + 26, X(imin), Y(prof[imin]))
    _text(dr, (X(imin) - 66, Y(prof[imin]) + 28), "deepest = UP-RANGE", sz=14, fill=ACCENT, anchor="ra")
    # rim crests: highest point each side of centre
    lc = int(np.argmax(prof[:N // 2])); rc = N // 2 + int(np.argmax(prof[N // 2:]))
    _text(dr, (X(lc), Y(prof[lc]) - 18), "up-range rim (low)", sz=13, anchor="ma")
    _text(dr, (X(rc), Y(prof[rc]) - 18), "down-range rim", sz=13, anchor="ma")
    _text(dr, (x0, yb + 8), "UP-RANGE", sz=14, fill=(90, 90, 90), anchor="la")
    _text(dr, (x1, yb + 8), "DOWN-RANGE", sz=14, fill=(90, 90, 90), anchor="ra")
    _text(dr, (W // 2, map_h + 30 + 8),
          "Elevation cross-section along the trajectory  (vertical exaggeration ~6x)",
          sz=15, anchor="ma")

    canvas.save("crater_anatomy.png")
    print(f"wrote crater_anatomy.png   D={D/1000:.2f} km  ecc={info['ellipticity']:.2f}  "
          f"deepest col={imin} (centre {N//2}) -> {'up-range' if imin < N//2 else 'down-range'}")


if __name__ == "__main__":
    build()
