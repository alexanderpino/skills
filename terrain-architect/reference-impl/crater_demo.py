"""Impact matrix — asteroid impacts across SIZE (rows) and ANGLE (columns), rendered as a
contact sheet (`crater_matrix.png`). Trajectory travels left→right, so downrange is to the
RIGHT of each tile. Each tile is normalised to the crater's own size, so the panels compare
SHAPE (simple bowl → complex central peak; circular → elongated; symmetric → butterfly ejecta),
not absolute size. Run: `python crater_demo.py`.
"""
import numpy as np

import crater
import render

TILE = 150
V = 20000.0                                                # 20 km/s, a typical impact speed
SIZES = [("60 m impactor", 60.0), ("1 km impactor", 1000.0), ("10 km impactor", 10000.0)]
ANGLES = [90.0, 45.0, 20.0, 8.0]                           # from horizontal


def panel(L, angle):
    D = crater.final_crater(crater.transient_crater_diameter(L, V, angle=angle))[0]
    cs = D / (TILE * 0.32)                                 # crater ~1/3 of the tile, room for ejecta
    h, info = crater.stamp_impact(np.zeros((TILE, TILE)), TILE // 2, TILE // 2, cs,
                                  L=L, v=V, angle=angle, azimuth=0.0)   # +x = downrange
    return render.hillshade(h, cs, azimuth=315, altitude=40), info


def main():
    rows, pad = [], 3
    for label, L in SIZES:
        for angle in ANGLES:
            tile, info = panel(L, angle)
            rows.append(tile)
            print(f"  {label:16s} @ {angle:4.0f}°  D_final={info['D_final'] / 1000:6.2f} km  "
                  f"{'complex' if info['complex'] else 'simple '}  ecc={info['ellipticity']:.2f}")
    cols = len(ANGLES)
    n = len(rows)
    nr = n // cols
    out = np.full((nr * (TILE + pad) + pad, cols * (TILE + pad) + pad, 3), 30, dtype=np.uint8)
    for k, t in enumerate(rows):
        r, c = divmod(k, cols)
        out[pad + r * (TILE + pad):pad + r * (TILE + pad) + TILE,
            pad + c * (TILE + pad):pad + c * (TILE + pad) + TILE] = t
    render.write_png("crater_matrix.png", out)
    print(f"\nwrote crater_matrix.png  rows=sizes {[s for s, _ in SIZES]}  cols=angles {ANGLES}°"
          f"  (downrange → right)")


if __name__ == "__main__":
    main()
