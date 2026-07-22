"""Heightfield render modes (09-verification.md, "Visual review modes").

Turn a heightfield (and its companion fields) into images you can judge by eye.
Every function here *renders* an `06`/`08` field and returns an ``(H, W, 3)`` uint8
RGB array; none of them modifies the terrain. The set mirrors the review-mode table
in `references/09-verification.md`:

    greyscale        height, per-view normalised          — range, clipping, blunders
    hillshade        Lambert of the normal vs a low sun    — relief, the overall read
    slope_shade      atan(slope) on a ramp                 — steepness, repose faces
    flow_overlay     log(A) over hillshade                 — the channel network (check 1)
    hypsometric      elevation tint * hillshade            — the "hero" read
    false_colour_clip  height with NaN/Inf/out-of-range flagged

Deliberately dependency-free: pure numpy plus a ~30-line stdlib-``zlib`` PNG writer,
so the demo runs with exactly the `reference-impl` requirements (numpy) and nothing
else. `09`'s discipline — *bake review renders from R32F, never the quantised export* —
is the caller's job: pass the working float field, not an R16 round-trip.
"""
import struct
import zlib

import numpy as np


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _normalise(field, lo=None, hi=None):
    """Map a field to [0, 1] using finite values only (NaN/Inf -> 0)."""
    f = np.asarray(field, dtype=np.float64)
    finite = np.isfinite(f)
    if lo is None:
        lo = float(f[finite].min()) if finite.any() else 0.0
    if hi is None:
        hi = float(f[finite].max()) if finite.any() else 1.0
    if hi <= lo:
        hi = lo + 1.0
    out = np.clip((f - lo) / (hi - lo), 0.0, 1.0)
    return np.where(finite, out, 0.0)


def _grey(v01):
    """[0,1] scalar image -> (H,W,3) uint8 grey."""
    g = np.clip(np.asarray(v01) * 255.0, 0, 255).astype(np.uint8)
    return np.stack([g, g, g], axis=-1)


def _gradient(h, cellsize):
    """(dz/dx, dz/dy) in metres/metre. x = column (axis 1), y = row (axis 0)."""
    h = np.asarray(h, dtype=np.float64)
    gy, gx = np.gradient(h, cellsize)          # np.gradient returns d/d(axis0), d/d(axis1)
    return gx, gy


def _ramp(v01, stops):
    """Piecewise-linear colour ramp. `stops` = [(pos, (r,g,b)), ...] with pos in [0,1]
    and channels in [0,1]. Returns (H,W,3) float in [0,1]."""
    v = np.clip(np.asarray(v01, dtype=np.float64), 0.0, 1.0)
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], dtype=np.float64)
    out = np.empty(v.shape + (3,), dtype=np.float64)
    for ch in range(3):
        out[..., ch] = np.interp(v, pos, cols[:, ch])
    return out


# --------------------------------------------------------------------------- #
# render modes
# --------------------------------------------------------------------------- #
def greyscale(h):
    """Height, per-view normalised. Reads absolute range / clipping / gross blunders;
    blind to shape (a canyon and a shallow dip look identical) — pair with hillshade."""
    return _grey(_normalise(h))


def hillshade(h, cellsize=1.0, azimuth=315.0, altitude=45.0, z_factor=1.0):
    """Lambert shading of the surface normal against a low sun. `azimuth` is the light
    direction in degrees measured clockwise from the top of the image (315 = NW, the GIS
    default); `altitude` is the sun's height above the horizon. `z_factor` exaggerates
    relief for the review light only. Returns grey in [0,1]-mapped uint8."""
    gx, gy = _gradient(h, cellsize)
    gx *= z_factor
    gy *= z_factor
    nz = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    nx, ny = -gx * nz, -gy * nz
    az = np.radians(azimuth)
    alt = np.radians(altitude)
    # light points *toward* the surface from the sun; azimuth clockwise from -y (top).
    lx = np.cos(alt) * np.sin(az)
    ly = -np.cos(alt) * np.cos(az)
    lz = np.sin(alt)
    lambert = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)
    return _grey(lambert)


def slope_shade(h, cellsize=1.0):
    """atan(slope) on a ramp — steepness read directly (steeper = darker). Pairs with the
    slope histogram (09 check 2); after thermal, faces should cluster near the repose
    angle, not at 0 or 90 degrees. Blind to convex/concave: slope is unsigned."""
    gx, gy = _gradient(h, cellsize)
    slope = np.arctan(np.hypot(gx, gy))        # [0, pi/2]
    return _grey(1.0 - slope / (np.pi / 2.0))


def flow_overlay(h, area, cellsize=1.0, azimuth=315.0, altitude=45.0,
                 channel_quantile=0.85, tint=(0.15, 0.45, 0.95)):
    """log(drainage area) composited over hillshade — the highest-value structural check
    (09 check 1): rivers must form a connected network that reaches the domain edge, not
    stop mid-map. `area` is the drainage-area field A (m^2) from flow routing; the top
    `channel_quantile` of log(A) is painted as the channel network."""
    base = hillshade(h, cellsize, azimuth, altitude).astype(np.float64) / 255.0
    w = _normalise(np.log(np.asarray(area, dtype=np.float64) + 1.0))
    thr = float(np.quantile(w, channel_quantile))
    strength = np.clip((w - thr) / max(1e-9, 1.0 - thr), 0.0, 1.0)
    out = base.copy()
    for ch in range(3):
        out[..., ch] = base[..., ch] * (1.0 - strength) + tint[ch] * strength
    return np.clip(out * 255.0, 0, 255).astype(np.uint8)


# blue water -> green lowland -> tan -> brown -> white peaks
_HYPSO = [
    (0.00, (0.16, 0.30, 0.50)),
    (0.04, (0.20, 0.42, 0.62)),
    (0.06, (0.36, 0.55, 0.34)),
    (0.30, (0.52, 0.62, 0.36)),
    (0.55, (0.62, 0.54, 0.36)),
    (0.78, (0.52, 0.40, 0.30)),
    (0.92, (0.78, 0.76, 0.74)),
    (1.00, (1.00, 1.00, 1.00)),
]


def hypsometric(h, cellsize=1.0, azimuth=315.0, altitude=45.0, sea_level=None):
    """Elevation tint modulated by hillshade — the "hero" read (does it look like a
    place). Everything at or below `sea_level` (default: the minimum) reads as water."""
    hh = np.asarray(h, dtype=np.float64)
    if sea_level is not None:
        hh = np.where(hh < sea_level, sea_level, hh)
    tint = _ramp(_normalise(hh), _HYPSO)
    shade = hillshade(h, cellsize, azimuth, altitude).astype(np.float64) / 255.0
    shade = 0.35 + 0.65 * shade[..., :1]       # keep some colour in the shadows
    return np.clip(tint * shade * 255.0, 0, 255).astype(np.uint8)


def false_colour_clip(h, lo=None, hi=None):
    """Height with the pathologies flagged loudly: NaN/Inf -> magenta, below `lo` -> blue,
    above `hi` -> red, everything valid -> grey. Catches the corruptions *before* they
    spread through the graph (09)."""
    f = np.asarray(h, dtype=np.float64)
    finite = np.isfinite(f)
    lo = float(f[finite].min()) if lo is None and finite.any() else (lo or 0.0)
    hi = float(f[finite].max()) if hi is None and finite.any() else (hi or 1.0)
    img = _grey(_normalise(f, lo, hi)).astype(np.uint8)
    img[~finite] = (255, 0, 255)               # NaN / Inf
    img[finite & (f < lo)] = (30, 60, 220)     # below range
    img[finite & (f > hi)] = (220, 40, 30)     # above range
    return img


# --------------------------------------------------------------------------- #
# PNG writer  (truecolour 8-bit, no external deps)
# --------------------------------------------------------------------------- #
def _chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def write_png(path, rgb):
    """Write an (H, W, 3) uint8 array as a PNG. Minimal encoder (stdlib zlib only)."""
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"expected (H, W, 3) RGB, got {rgb.shape}")
    h, w = rgb.shape[:2]
    # each scanline is prefixed with filter-type byte 0 (None)
    raw = np.hstack([np.zeros((h, 1), np.uint8), rgb.reshape(h, w * 3)]).tobytes()
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(raw, 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)
    return path
