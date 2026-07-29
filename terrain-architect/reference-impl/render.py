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
# SatMap + splatmap colour  (Gaea's Texture stage)
# --------------------------------------------------------------------------- #
# SatMaps: curated multi-stop colour gradients (a CLUT indexed by a driver, usually elevation) —
# Gaea's naturalistic "satellite" palettes, here a hand-tuned gradient per world. Stops are
# (position in [0,1], (r,g,b) in 0-255), low elevation -> high.
SATMAPS = {
    "temperate": [(0.00, (46, 78, 54)), (0.12, (72, 104, 66)), (0.34, (120, 138, 86)),
                  (0.54, (150, 140, 104)), (0.74, (126, 116, 102)), (0.90, (182, 178, 174)),
                  (1.00, (236, 240, 246))],
    "verdant":   [(0.00, (40, 72, 50)), (0.30, (64, 104, 60)), (0.62, (96, 128, 80)),
                  (0.86, (140, 150, 110)), (1.00, (210, 214, 206))],
    "arid":      [(0.00, (96, 54, 40)), (0.20, (150, 80, 52)), (0.44, (178, 120, 78)),
                  (0.68, (200, 168, 120)), (0.86, (214, 196, 166)), (1.00, (232, 222, 200))],
    "sand":      [(0.00, (150, 120, 84)), (0.40, (196, 168, 120)), (0.76, (216, 192, 150)),
                  (1.00, (230, 216, 188))],
    "volcanic":  [(0.00, (40, 36, 38)), (0.30, (78, 72, 72)), (0.54, (112, 86, 80)),
                  (0.76, (120, 112, 106)), (1.00, (218, 216, 216))],
    "mars":      [(0.00, (92, 50, 40)), (0.30, (140, 72, 50)), (0.58, (180, 104, 66)),
                  (0.80, (200, 140, 96)), (1.00, (214, 182, 152))],
    "lunar":     [(0.00, (64, 64, 68)), (0.40, (110, 110, 116)), (0.72, (150, 150, 156)),
                  (1.00, (200, 200, 206))],
    # EXTRACTED from real satellite imagery via `extract_satmap` (the SatMap-authoring path):
    # NASA Terra/ASTER, Rub' al Khali dune field ("Arabian Empty Quarter sand dunes imaged by
    # Terra (EOS AM-1)", Wikimedia Commons; NASA imagery, public domain). Interdune shadow-brown
    # -> sand -> bright crest.
    "desert_terra": [(0.00, (57, 27, 13)), (0.12, (75, 45, 26)), (0.21, (98, 68, 45)),
                     (0.29, (113, 86, 65)), (0.38, (122, 103, 85)), (0.46, (129, 116, 103)),
                     (0.54, (135, 127, 118)), (0.62, (143, 137, 129)), (0.71, (153, 147, 138)),
                     (0.79, (168, 161, 148)), (0.88, (195, 184, 163)), (1.00, (217, 204, 176))],
}


def extract_satmap(rgb, n_stops=12, smooth=1):
    """AUTHOR a SatMap gradient from a real satellite/aerial image — the step Gaea uses to build its
    SatMap library ("gradients extracted from satellite imagery"; the applied op itself is the
    standard gradient-map CLUT). Order the image's pixels by LUMINANCE — a proxy for elevation that
    holds in the imagery this is meant for (dunes, snow-capped ranges, deserts: valley floors and
    shadow dark, crests/snow bright) — average each luminance bin into a colour stop, and lightly
    smooth along the ramp. Returns [(pos, (r,g,b)), ...] ready for `satmap`. `rgb` is an (n,m,3)
    array in 0-255 (load the image however you like; this stays pure numpy on arrays)."""
    px = np.asarray(rgb, dtype=np.float64).reshape(-1, 3)
    lum = px @ np.array([0.2126, 0.7152, 0.0722])            # Rec.709 luminance
    order = np.argsort(lum, kind="stable")
    cols = np.array([px[b].mean(axis=0) for b in np.array_split(order, int(n_stops))])
    if smooth:
        k = 2 * int(smooth) + 1
        pad = np.pad(cols, ((smooth, smooth), (0, 0)), mode="edge")
        cols = np.stack([np.convolve(pad[:, c], np.ones(k) / k, mode="valid") for c in range(3)], 1)
    pos = (np.arange(int(n_stops)) + 0.5) / float(n_stops)
    pos[0], pos[-1] = 0.0, 1.0
    return [(float(p), (float(r), float(g), float(b))) for p, (r, g, b) in zip(pos, cols)]


def satmap(driver, stops):
    """A SatMap: colour a normalised driver field (in [0,1], typically elevation) through a curated
    multi-stop gradient — a colour lookup table, exactly Gaea's SatMap idea. `stops` is a name in
    `SATMAPS` or an explicit [(pos, (r,g,b)), ...] list. Returns float RGB in 0-255 (compose further
    with `splat_blend` before quantising)."""
    stops = SATMAPS[stops] if isinstance(stops, str) else stops
    v = np.clip(np.asarray(driver, dtype=np.float64), 0.0, 1.0)
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], dtype=np.float64)
    out = np.empty(v.shape + (3,), dtype=np.float64)
    for ch in range(3):
        out[..., ch] = np.interp(v, pos, cols[:, ch])
    return out


def satmap_2d(driver_a, driver_b, stops_a, stops_b):
    """A 2-D colour LUT: blend two elevation ramps by a SECOND driver. The classic pairing is
    altitude x slope — `driver_a` (usually height) indexes both ramps, `driver_b` (usually
    normalised slope) mixes between the flat-ground palette `stops_a` and the steep-ground palette
    `stops_b`, so gentle ground reads as soil/vegetation and cliffs as bare rock at the same
    elevation. This is the two-ramp form of the biome LUT: cheaper and easier to author than a full
    per-cell 2-D image, and it covers the usual altitude/slope and altitude/moisture cases.
    Returns float RGB in 0-255."""
    a = satmap(driver_a, stops_a)
    b = satmap(driver_a, stops_b)
    t = np.clip(np.asarray(driver_b, dtype=np.float64), 0.0, 1.0)[..., None]
    return a * (1.0 - t) + b * t


# Blend modes for compositing colour layers. `max`/`min` are the pair terrain tools lean on (a
# max-blend keeps whichever layer is brighter, which is how two SatMaps are usually merged).
BLEND_MODES = {
    "normal":   lambda d, s: s,
    "max":      lambda d, s: np.maximum(d, s),
    "min":      lambda d, s: np.minimum(d, s),
    "multiply": lambda d, s: d * s / 255.0,
    "screen":   lambda d, s: 255.0 - (255.0 - d) * (255.0 - s) / 255.0,
    "overlay":  lambda d, s: np.where(d < 127.5, 2.0 * d * s / 255.0,
                                      255.0 - 2.0 * (255.0 - d) * (255.0 - s) / 255.0),
}


def blend_rgb(base_rgb, over_rgb, mask=None, opacity=1.0, mode="normal"):
    """Composite one colour layer over another — the operation that lets SatMaps be *combined*
    rather than chosen. `mask` (in 0-1, broadcast over channels) times `opacity` is the blend
    weight, and `mode` is one of `BLEND_MODES`. Chain it to stack layers (a slope-driven rock
    SatMap over a height-driven ground SatMap, masked to the steeps), or call it once to merge two
    independent SatMap branches. Returns float RGB in 0-255."""
    d = np.asarray(base_rgb, dtype=np.float64)
    s = np.asarray(over_rgb, dtype=np.float64)
    try:
        blended = BLEND_MODES[mode](d, s)
    except KeyError:
        raise ValueError(f"unknown blend mode {mode!r}; expected one of {sorted(BLEND_MODES)}")
    w = float(opacity) if mask is None else \
        np.clip(np.asarray(mask, dtype=np.float64), 0.0, 1.0)[..., None] * float(opacity)
    return d + (blended - d) * w


def splat_blend(base_rgb, overlays):
    """Splatmap compositing (the Texture stage): over a base colour (e.g. a `satmap`), lay down
    per-material colours where their coverage MASK is high. `overlays` is an ordered list of
    (mask in [0,1], (r,g,b)); later overlays paint over earlier ones — snow over rock over sediment.
    The masks are the splat channels; drive them from slope, height, flow, curvature (06), which is
    how Gaea's splatmaps read as geology rather than a flat tint. Returns float RGB in 0-255."""
    out = np.array(base_rgb, dtype=np.float64)
    for mask, color in overlays:
        m = np.clip(np.asarray(mask, dtype=np.float64), 0.0, 1.0)[..., None]
        out = out * (1.0 - m) + np.array(color, dtype=np.float64) * m
    return out


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
