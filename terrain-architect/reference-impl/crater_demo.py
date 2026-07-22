"""Impact matrix — asteroid impacts across SIZE (rows) and ANGLE (columns), rendered as a
contact sheet (`crater_matrix.png`). Trajectory travels left→right, so downrange is to the
RIGHT of each tile. Each tile is normalised to the crater's own size, so the panels compare
SHAPE (simple bowl → complex central peak; circular → elongated; symmetric → butterfly ejecta),
not absolute size. Run: `python crater_demo.py`.

Tiles use a CUT/FILL tint about the undisturbed ground (h = 0): what was EXCAVATED reads cool
(blue), what was DEPOSITED as ejecta reads warm (tan→orange), modulated by hillshade for the
3-D form. So an oblique impact reads unmistakably — a blue bowl with the debris piled WARM and
forward, starved on the up-range side — rather than "just an oval".
"""
import numpy as np

import crater
import render

TILE = 150
V = 20000.0                                                # 20 km/s, a typical impact speed
SIZES = [("60 m impactor", 60.0), ("1 km impactor", 1000.0), ("10 km impactor", 10000.0)]
# columns chosen to walk the observed oblique-impact sequence (Gault & Wedekind 1978):
#   90° vertical → symmetric   ·   45° most-probable → mild downrange bias
#   20° → strong downrange lobe + up-range forbidden wedge (still ~circular; ellipse onset ~12°)
#   3°  → grazing: elongated, cross-range butterfly wings with BOTH forbidden zones
ANGLES = [90.0, 45.0, 20.0, 3.0]                           # from horizontal

_CUT = np.array([70, 120, 190], dtype=np.float64) / 255.0     # excavated  -> cool blue
_ZERO = np.array([176, 172, 162], dtype=np.float64) / 255.0   # undisturbed -> neutral
_FILL = np.array([205, 120, 55], dtype=np.float64) / 255.0    # deposited  -> warm tan


def cutfill(h, cellsize):
    """Diverging cut/fill tint about the h = 0 datum, modulated by hillshade. Excavation goes
    cool, deposition goes warm — the honest picture of where mass left and where it landed."""
    m = max(abs(float(h.min())), abs(float(h.max())), 1e-9)
    t = np.clip(h / m, -1.0, 1.0)[..., None]               # -1 deepest cut … +1 highest fill
    tint = np.where(t >= 0, _ZERO + t * (_FILL - _ZERO), _ZERO + (-t) * (_CUT - _ZERO))
    shade = render.hillshade(h, cellsize, azimuth=315, altitude=40).astype(np.float64) / 255.0
    shade = 0.45 + 0.55 * shade[..., :1]                   # keep colour in the shadows
    return np.clip(tint * shade * 255.0, 0, 255).astype(np.uint8)


def panel(L, angle):
    D = crater.final_crater(crater.transient_crater_diameter(L, V, angle=angle))[0]
    ecc = crater._ellipticity(angle)
    cs = D * ecc / (TILE * 0.40)              # frame by the MAJOR axis so ejecta always has room
    h, info = crater.stamp_impact(np.zeros((TILE, TILE)), TILE // 2, TILE // 2, cs,
                                  L=L, v=V, angle=angle, azimuth=0.0)   # +x = downrange
    return cutfill(h, cs), info


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
