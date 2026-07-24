"""Heightfield I/O — bring a real / external heightmap in as a base, write results back (08).

Every atom in this sandbox operates on a plain float `(n, m)` NumPy array of elevations, so a
**real-world DEM is a first-class base**: load it, then run the same erosion / thermal / analysis
atoms on it that you would on procedural noise — "add erosion and other effects to real areas". This
is the *File Input / File Output* node the baseline tools ship (Gaea **File**, World Machine **File
Input/Output**, Houdini **HeightField File**), which the node-parity audit had scoped out as "I/O"
but which is exactly what makes real-world workflows possible.

Formats — the interchange formats the tools actually exchange, all pure NumPy/stdlib (+ PIL for PNG):
  * **`.npy`**            — NumPy's own float array (lossless; the native format here).
  * **`.png`**           — 16-bit greyscale heightmap (Gaea/World Machine/Unreal export/import).
  * **`.r16` / `.raw`**  — raw little-endian uint16, square or with an explicit `shape`
                           (Unreal Landscape, World Machine RAW).
  * **`.r32` / `.f32`**  — raw little-endian float32.
  * **`.hgt` / `.hgt.gz`** — SRTM / USGS "skadi" tiles: big-endian int16 metres, square
                           (3601 = SRTM1 1-arc-sec, 1201 = SRTM3). Voids (−32768) → NaN.

`fetch_srtm` pulls a real SRTM1 tile from the AWS Terrain Tiles open bucket (no auth) and caches it,
so `python heightfield_io.py` can demonstrate erosion applied to an actual mountain range end-to-end.
"""
import gzip
import math
import os
import urllib.request

import numpy as np

try:
    from PIL import Image
except Exception:                                          # noqa: BLE001 — PNG path is optional
    Image = None

_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dem_cache")
_SRTM_BUCKET = "https://elevation-tiles-prod.s3.amazonaws.com/skadi"


def load_heightfield(path, *, shape=None, vmin=0.0, vmax=None, dtype="<u2"):
    """Load a heightfield as a float `(n, m)` array. Format is chosen by extension (see module doc).

    For the integer image/raw formats, the stored 0…max range is rescaled to `[vmin, vmax]` when
    `vmax` is given (so a 16-bit PNG becomes metres); with `vmax=None` the raw integer values are
    returned as floats. `.hgt` and `.npy` are already in physical units and ignore vmin/vmax. Raw
    `.r16/.r32` need a `shape` unless the file is exactly square. `dtype` sets the raw integer type."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".npy":
        return np.load(path).astype(np.float64)
    if ext in (".hgt", ".gz") or path.lower().endswith(".hgt.gz"):
        raw = gzip.decompress(open(path, "rb").read()) if path.lower().endswith(".gz") else open(path, "rb").read()
        a = np.frombuffer(raw, dtype=">i2").astype(np.float64)
        n = int(round(math.sqrt(a.size)))
        if n * n != a.size:
            raise ValueError(f"{path}: {a.size} samples is not a square SRTM tile")
        a = a.reshape(n, n)
        a[a <= -32768] = np.nan                            # SRTM void marker
        return a
    if ext == ".png":
        if Image is None:
            raise RuntimeError("PIL is required to read PNG heightfields")
        a = np.asarray(Image.open(path)).astype(np.float64)
        if a.ndim == 3:                                    # collapse an accidental RGB(A) export to luminance
            a = a[..., :3].mean(axis=2)
        full = 65535.0 if a.max() > 255 else 255.0
        return _rescale(a, full, vmin, vmax)
    if ext in (".r16", ".raw", ".r32", ".f32"):
        raw_dtype = np.dtype("<f4") if ext in (".r32", ".f32") else np.dtype(dtype)
        a = np.fromfile(path, dtype=raw_dtype).astype(np.float64)
        a = _to_shape(a, shape, path)
        if raw_dtype.kind == "f":
            return a
        full = float(np.iinfo(np.dtype(dtype)).max)
        return _rescale(a, full, vmin, vmax)
    raise ValueError(f"unsupported heightfield extension: {ext!r}")


def save_heightfield(path, h, *, vmin=None, vmax=None, bits=16):
    """Write a float heightfield. `.npy` is lossless; `.png` and `.r16/.raw` quantise the value range
    `[vmin, vmax]` (defaults to the data's own min/max) to full-scale unsigned integers; `.r32/.f32`
    write raw float32. Returns the `(vmin, vmax)` actually used, so a later `load_heightfield` can
    invert the scaling exactly."""
    ext = os.path.splitext(path)[1].lower()
    h = np.asarray(h, dtype=np.float64)
    if ext == ".npy":
        np.save(path, h)
        return float(np.nanmin(h)), float(np.nanmax(h))
    if ext in (".r32", ".f32"):
        h.astype("<f4").tofile(path)
        return float(np.nanmin(h)), float(np.nanmax(h))
    lo = float(np.nanmin(h)) if vmin is None else vmin
    hi = float(np.nanmax(h)) if vmax is None else vmax
    q = np.clip((np.nan_to_num(h, nan=lo) - lo) / (hi - lo + 1e-12), 0.0, 1.0)
    if ext == ".png":
        if Image is None:
            raise RuntimeError("PIL is required to write PNG heightfields")
        if bits == 16:
            Image.fromarray((q * 65535 + 0.5).astype(np.uint16)).save(path)
        else:
            Image.fromarray((q * 255 + 0.5).astype(np.uint8), mode="L").save(path)
    elif ext in (".r16", ".raw"):
        (q * 65535 + 0.5).astype("<u2").tofile(path)
    else:
        raise ValueError(f"unsupported heightfield extension: {ext!r}")
    return lo, hi


def window(dem, r0, c0, size, stride=1):
    """Crop a `size×size` working window from a big DEM (optionally decimating by `stride`) — real
    tiles are 1201–3601 px, far larger than an erosion solver wants to chew per run."""
    return np.asarray(dem, dtype=np.float64)[r0:r0 + size, c0:c0 + size][::stride, ::stride].copy()


def fetch_srtm(tile="N36W113", *, cache_dir=_CACHE):
    """Fetch a real SRTM1 tile (metres) from the AWS Terrain Tiles open bucket, cached. `tile` is the
    1°×1° cell name, e.g. 'N36W113' (Colorado Plateau) or 'N35W083' (Great Smokies). Returns a float
    array with voids as NaN, or None if the network is unavailable (so callers degrade gracefully)."""
    os.makedirs(cache_dir, exist_ok=True)
    lat = tile[:3]
    url = f"{_SRTM_BUCKET}/{lat}/{tile}.hgt.gz"
    path = os.path.join(cache_dir, f"{tile}.hgt")
    if not os.path.exists(path):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                raw = gzip.decompress(r.read())
        except Exception as e:                             # noqa: BLE001
            print(f"  network unavailable ({e.__class__.__name__}); could not fetch {tile}")
            return None
        with open(path, "wb") as fh:
            fh.write(raw)
    return load_heightfield(path)


def _rescale(a, full, vmin, vmax):
    if vmax is None:
        return a
    return vmin + (a / full) * (vmax - vmin)


def _to_shape(a, shape, path):
    if shape is not None:
        return a.reshape(shape)
    n = int(round(math.sqrt(a.size)))
    if n * n != a.size:
        raise ValueError(f"{path}: {a.size} samples is not square — pass shape=(rows, cols)")
    return a.reshape(n, n)


def main():
    """Demonstrate the whole point: pull a REAL mountain DEM and add our erosion to it."""
    import erosion_thermal as TH
    import erosion_streampower as SP
    import render

    dem = fetch_srtm("N36W113")                            # Colorado Plateau (real USGS/SRTM elevations)
    if dem is None:
        print("no network / cached tile; skipping the real-DEM demo")
        return
    base = window(dem, 1400, 1200, 400, stride=2)          # a 200×200 working crop, real metres
    base = np.nan_to_num(base, nan=float(np.nanmin(base)))
    print(f"loaded real DEM crop {base.shape}, {base.min():.0f}–{base.max():.0f} m")
    eroded = SP.stream_power_evolve(base, np.zeros_like(base), 1.5e-5, 0.45, 1e3, 25, 60.0)
    eroded = TH.thermal_erosion(eroded, 0.6, 8, 60.0)      # gently sharpen fluvial incision + add talus
    render.write_png("dem_real_base.png", render.hillshade(base, 60.0))
    render.write_png("dem_real_eroded.png", render.hillshade(eroded, 60.0))
    save_heightfield("dem_real_eroded.r16", eroded, vmin=float(base.min()), vmax=float(base.max()))
    print("wrote dem_real_base.png, dem_real_eroded.png (before/after hillshades) + dem_real_eroded.r16")


if __name__ == "__main__":
    main()
