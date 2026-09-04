"""Anisotropy ANATOMY — the figure for `09`'s position that the word names two different things.

LATTICE anisotropy is the discretisation printing through: always a defect, because the direction
it prefers belongs to the array and nothing in the world put it there. FIELD anisotropy is real
directional structure carried by a cause (strike/dip, wind, ice flow) and terrain without it looks
generic. The discriminator is equivariance under rotation — rotate the domain, run the operator,
rotate back, compare — and this figure is that test made visible, including the trap that makes it
report a perfect score on a grossly broken operator.

Panels: the radially symmetric input (no direction of its own, so any direction in the output was
put there by the operator or the grid); the axis-locked operator's L1 diamond against the isotropic
control's disc; the rotation residual for each at 30 degrees; and the 90-degree trap, where the same
axis-locked operator scores exactly zero because a quarter turn is a SYMMETRY of the square lattice.

The numpy half of this module carries no Pillow dependency, so `tests/test_anisotropy.py` imports
the operators from here and guards exactly what the figure draws. Writes `anisotropy_anatomy.png`.
Run: `python anisotropy_anatomy.py`.
"""
import math

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

N = 121
C = N // 2
_yy, _xx = np.mgrid[0:N, 0:N].astype(float)
_X, _Y = _xx - C, _yy - C


# --------------------------------------------------------------------------- #
# operators and the test (numpy only — importable without Pillow)

def sample(a, sx, sy):
    """Bilinear sample at continuous coordinates. Used by BOTH the rotation and the field-carried
    operator, so neither is handicapped by a cruder interpolant than the other — comparing them
    otherwise measures the sloppier sampler rather than the principle."""
    x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
    fx, fy = sx - x0, sy - y0
    out = np.zeros_like(a)
    for dy in (0, 1):
        for dx in (0, 1):
            xi, yi = np.clip(x0 + dx, 0, N - 1), np.clip(y0 + dy, 0, N - 1)
            out += ((fx if dx else 1 - fx) * (fy if dy else 1 - fy)) * a[yi, xi]
    return out


def rotate(a, th):
    """Bilinear rotation about the centre. Its interpolation error is the noise floor that the
    isotropic control measures — which is why the control is mandatory (`09`)."""
    ct, st = math.cos(th), math.sin(th)
    return sample(a, ct * _X + st * _Y + C, -st * _X + ct * _Y + C)


def cone(radius=30.0, height=30.0):
    """Radially symmetric: it has no direction of its own."""
    return np.maximum(0.0, height * (1.0 - np.hypot(_X, _Y) / radius))


def axis_locked(h, k=9):
    """4-neighbour max — grows an L1 ball (a diamond) welded to the axes."""
    for _ in range(k):
        h = np.maximum.reduce([h, np.roll(h, 1, 0), np.roll(h, -1, 0),
                               np.roll(h, 1, 1), np.roll(h, -1, 1)])
    return h


def isotropic(h, k=9):
    """Disc max — the same operation with a radially symmetric structuring element."""
    d = np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) <= k
    w = sliding_window_view(np.pad(h, k, mode="edge"), (2 * k + 1, 2 * k + 1))
    return (w * d).max(axis=(2, 3))


def field_smear(h, ang, k=9):
    """Anisotropy carried BY A FIELD: the direction comes from `ang`, so it co-rotates."""
    out = h.copy()
    for s in range(1, k + 1):
        out = np.maximum(out, sample(h, _xx + s * np.cos(ang), _yy + s * np.sin(ang)))
    return out


def residual(F, th, h=None):
    """rot(F(rot(h, -th)), th) - F(h): zero iff F commutes with rotation."""
    h = cone() if h is None else h
    return rotate(F(rotate(h, -th)), th) - F(h)


def error(F, th, h=None):
    h = cone() if h is None else h
    m = np.hypot(_X, _Y) < N // 3
    r, b = residual(F, th, h), F(h)
    return float(np.abs(r)[m].mean() / (np.abs(b)[m].mean() + 1e-12))


# --------------------------------------------------------------------------- #
# figure

_TTF_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:/Windows/Fonts/arial.ttf",
)
INK = (28, 30, 36)
MID = (110, 116, 126)
WARN = (196, 62, 44)
GOOD = (38, 96, 168)
TILE, PAD, TOP, GAP, CAP, FOOT = 300, 26, 82, 34, 74, 96


def _ramp_field(a):
    """Grey, normalised — the operator's output."""
    v = a / (a.max() + 1e-12)
    g = (245 - 190 * v).astype(np.uint8)
    return np.dstack([g, g, g])


def _ramp_residual(a, vmax):
    """White -> red, on a FIXED scale so panels are comparable (`09`: renders normalise per view,
    which is exactly how an anisotropy figure can lie about magnitude)."""
    v = np.clip(np.abs(a) / (vmax + 1e-12), 0, 1)[..., None]
    return (np.array([255, 255, 255]) * (1 - v) + np.array([196, 62, 44]) * v).astype(np.uint8)


def build():
    from PIL import Image, ImageDraw, ImageFont
    import os

    ttf = next((p for p in _TTF_CANDIDATES if os.path.exists(p)), None)
    fold = str.maketrans({"√": "v", "×": "x", "—": "-", "–": "-", "·": "-", "≈": "~"})

    def font(sz):
        return ImageFont.truetype(ttf, sz) if ttf else ImageFont.load_default(size=sz)

    def text(dr, xy, s, sz=14, fill=INK, anchor="la"):
        dr.text(xy, s if ttf else s.translate(fold), font=font(sz), fill=fill, anchor=anchor)

    th30, th90 = math.radians(30), math.radians(90)
    h = cone()
    r_locked30, r_iso30 = residual(axis_locked, th30), residual(isotropic, th30)
    r_locked90 = residual(axis_locked, th90)
    vmax = float(np.abs(r_locked30).max())

    panels = [
        (_ramp_field(h), "input: a cone", "radially symmetric — no direction of its own", MID, None),
        (_ramp_field(axis_locked(h)), "axis-locked operator", "4-neighbour max -> an L1 diamond", WARN, None),
        (_ramp_field(isotropic(h)), "isotropic control", "disc max -> a disc", GOOD, None),
        (_ramp_residual(r_locked30, vmax), "rotation residual, 30°",
         "the lattice stays welded to the axes", WARN, f"error {error(axis_locked, th30):.3f}"),
        (_ramp_residual(r_iso30, vmax), "the control, 30°",
         "interpolation floor — the scale for the others", GOOD, f"error {error(isotropic, th30):.3f}"),
        (_ramp_residual(r_locked90, vmax), "THE TRAP: same operator, 90°",
         "a quarter turn is a lattice SYMMETRY", WARN, f"error {error(axis_locked, th90):.3f}"),
    ]

    W = PAD * 2 + 3 * TILE + 2 * GAP
    H = TOP + PAD + 2 * (TILE + CAP) + GAP + FOOT
    img = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(img)
    text(dr, (PAD, 18), "Anisotropy — lattice or field?", 26)
    text(dr, (PAD, 52), "chapter 09 · rotate the domain: physical anisotropy rotates with the "
                        "terrain, lattice anisotropy does not", 14, MID)

    for i, (rgb, title, sub, col, num) in enumerate(panels):
        ox = PAD + (i % 3) * (TILE + GAP)
        oy = TOP + (i // 3) * (TILE + CAP + GAP)
        img.paste(Image.fromarray(rgb).resize((TILE, TILE), Image.NEAREST), (ox, oy))
        dr.rectangle([ox, oy, ox + TILE - 1, oy + TILE - 1], outline=(210, 214, 220))
        text(dr, (ox, oy + TILE + 10), title, 15, col)
        text(dr, (ox, oy + TILE + 32), sub, 13, MID)
        if num:
            text(dr, (ox + TILE, oy + TILE + 10), num, 15, col, "ra")

    y = TOP + 2 * (TILE + CAP) + GAP + 16
    text(dr, (PAD, y), "Residual panels share ONE colour scale. The axis-locked operator scores about "
                       "an order of magnitude above the control —", 14, INK)
    text(dr, (PAD, y + 22), "but at 90° it scores exactly 0.000, because a quarter turn maps the square "
                            "lattice onto itself. The test angle must", 14, WARN)
    text(dr, (PAD, y + 44), "not be a symmetry of the lattice under test: avoid multiples of 90° on "
                            "square, 60° on hex (`26`).", 14, WARN)
    return img


if __name__ == "__main__":
    build().save("anisotropy_anatomy.png")
    print("wrote anisotropy_anatomy.png")
