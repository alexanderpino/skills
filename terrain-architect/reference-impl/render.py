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


# water, snow, rock, sand, grass — order matches analysis.MATERIAL_NAMES
_MATERIAL_PALETTE = [
    (40, 90, 170), (240, 244, 250), (120, 118, 116), (200, 178, 120), (96, 132, 72),
]


def material_rgb(masks, cellsize=1.0, palette=None, shade=True):
    """Colour a material stack. `masks` is either a partitioned `(K, H, W)` weight stack
    (blended by weight — the splatmap preview) or a categorical `(H, W)` index map. Palette
    order must match the mask order. With `shade`, modulate by hillshade for relief."""
    masks = np.asarray(masks, dtype=np.float64)
    pal = np.asarray(palette if palette is not None else _MATERIAL_PALETTE, dtype=np.float64)
    if masks.ndim == 2:                            # categorical index map -> one-hot
        idx = np.clip(np.rint(masks).astype(int), 0, len(pal) - 1)
        rgb = pal[idx]
    else:                                          # (K,H,W) soft weights -> weighted blend
        k = masks.shape[0]
        rgb = np.tensordot(np.moveaxis(masks, 0, -1), pal[:k], axes=([2], [0]))
    return np.clip(rgb, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------- #
# photoreal composite  (HYPERREALISM.md Part 1 — the shared render pipeline)
# --------------------------------------------------------------------------- #
def sun_sky_shade(h, cellsize=1.0, azimuth=315.0, altitude=45.0, z_factor=1.0, sky=0.30):
    """Two-light diffuse shade in [0,1]: a directional *sun* Lambert plus a flat hemispheric
    *sky* fill so shadows are lifted, never crushed to black (the single-hillshade tell). `sky`
    is the ambient floor; the remaining (1-sky) is the sun's contribution. Pure — takes only h."""
    gx, gy = _gradient(h, cellsize)
    gx *= z_factor
    gy *= z_factor
    nz = 1.0 / np.sqrt(gx * gx + gy * gy + 1.0)
    nx, ny = -gx * nz, -gy * nz
    az, alt = np.radians(azimuth), np.radians(altitude)
    lx = np.cos(alt) * np.sin(az)
    ly = -np.cos(alt) * np.cos(az)
    lz = np.sin(alt)
    lambert = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)
    return np.clip(sky + (1.0 - sky) * lambert, 0.0, 1.0)


def photoreal(material_rgb, h, cellsize=1.0, *, ao=None, rivers=None,
              azimuth=315.0, altitude=45.0, sky=0.30, ao_strength=0.45,
              aerial_strength=0.5, aerial_band=0.28, aerial_rgb=(170, 184, 206),
              water_rgb=(74, 116, 168), sea_level=None):
    """Composite a photoreal read from a **material-colour** image and the height field
    (HYPERREALISM.md Part 1): `material × (sun + sky) × AO`, blue rivers painted in, then
    aerial perspective hazing the low/distant ground toward atmosphere. Kept dependency-free
    — the caller supplies the already-computed `material_rgb` (a splatmap, `material_rgb(...)`),
    the horizon `ao` occlusion field (`analysis.horizon_ao`, 0=open…1=occluded) and a `rivers`
    strength map (e.g. from log drainage area); each is optional. This is the largest, cheapest
    realism jump over grey hillshade: colour + soft two-light + creased AO + depth haze."""
    mat = np.asarray(material_rgb, dtype=np.float64)
    shade = sun_sky_shade(h, cellsize, azimuth, altitude, sky=sky)
    lit = mat * shade[..., None]
    if ao is not None:                                       # darken sky-occluded creases/valleys
        occl = np.clip(np.asarray(ao, dtype=np.float64), 0.0, 1.0)
        lit *= (1.0 - ao_strength * occl)[..., None]
    if rivers is not None:                                   # paint the biggest channels blue
        r = np.clip(np.asarray(rivers, dtype=np.float64), 0.0, 1.0)[..., None]
        lit = lit * (1.0 - 0.6 * r) + np.array(water_rgb, dtype=np.float64) * 0.6 * r
    if aerial_strength > 0.0:                                # low ground desaturates toward sky
        hh = np.asarray(h, dtype=np.float64)
        base = float(sea_level) if sea_level is not None else float(hh.min())
        span = max(float(hh.max()) - base, 1e-6)
        hn = np.clip((hh - base) / span, 0.0, 1.0)
        haze = (np.clip(aerial_band - hn, 0.0, aerial_band) / aerial_band) * aerial_strength
        lit = lit * (1.0 - haze[..., None]) + np.array(aerial_rgb, dtype=np.float64) * haze[..., None]
    return np.clip(lit, 0, 255).astype(np.uint8)


def scatter_overlay(base_rgb, points, cellsize=1.0, color=(20, 20, 20), radius=1):
    """Draw a PointSet (07) over a base RGB image as small filled discs. `points` are world
    metres (x, y); converts to pixels via cellsize."""
    img = np.ascontiguousarray(base_rgb, dtype=np.uint8).copy()
    n, m = img.shape[:2]
    col = np.array(color, dtype=np.uint8)
    for x, y in np.asarray(points, dtype=np.float64):
        ci, cj = int(round(y / cellsize)), int(round(x / cellsize))
        for di in range(-radius, radius + 1):
            for dj in range(-radius, radius + 1):
                if di * di + dj * dj <= radius * radius:
                    i, j = ci + di, cj + dj
                    if 0 <= i < n and 0 <= j < m:
                        img[i, j] = col
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
