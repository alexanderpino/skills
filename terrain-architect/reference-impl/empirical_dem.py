"""Real-DEM empirical validation (VALIDATION.md rung 5, full coverage).

Downloads real SRTM tiles (AWS open Terrain Tiles, no auth), measures terrain statistics on
real drainage basins, and compares our generated terrain — the SAME estimator on both sides,
which is the only fair test (concavity in particular is measurement-sensitive). Requires
network; gracefully reports and exits if the fetch fails. Cached under `.dem_cache/`.

Recorded results (2026-07) are in VALIDATION.md. Run: `python empirical_dem.py`.
"""
import gzip
import os
import urllib.request

import numpy as np

import erosion_streampower as SP
import erosion_thermal as TH
import flow
import noise

TILES = {  # AWS open Terrain Tiles (skadi format, gzipped .hgt, no auth)
    "Colorado Plateau (N36W113)": "https://elevation-tiles-prod.s3.amazonaws.com/skadi/N36/N36W113.hgt.gz",
    "Great Smoky Mtns (N35W083)": "https://elevation-tiles-prod.s3.amazonaws.com/skadi/N35/N35W083.hgt.gz",
}
_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dem_cache")


def fetch_dem(url):
    """Return a 3601x3601 float array of a real SRTM1 tile, cached. None on network failure."""
    os.makedirs(_CACHE, exist_ok=True)
    path = os.path.join(_CACHE, url.rsplit("/", 1)[-1].replace(".gz", ""))
    if not os.path.exists(path):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                raw = gzip.decompress(r.read())
        except Exception as e:                             # noqa: BLE001
            print(f"  network unavailable ({e.__class__.__name__}); skipping {url}")
            return None
        with open(path, "wb") as fh:
            fh.write(raw)
    dem = np.fromfile(path, dtype=">i2").reshape(3601, 3601).astype(np.float64)
    dem[dem < -1000] = np.nan
    return dem


def metrics(h, cellsize):
    """(hypsometric integral, slope-area concavity θ, Hack's-law exponent h) with a fixed
    channel threshold — the identical estimator used on real and generated terrain."""
    h = np.nan_to_num(h, nan=np.nanmin(h))
    n = h.shape[0]
    hi = (h.mean() - h.min()) / (h.max() - h.min())
    hf = flow.priority_flood_fill(h)
    ri, rj, slope, dd = SP.receivers(hf, cellsize)
    A = SP.drainage_area(hf, ri, rj, cellsize * cellsize)
    interior = np.zeros((n, n), dtype=bool)
    interior[2:-2, 2:-2] = True
    chan = interior & (A > 100 * cellsize * cellsize) & (slope > 1e-4)
    theta = -np.polyfit(np.log(A[chan]), np.log(slope[chan]), 1)[0]
    Lp = np.zeros((n, n))
    for idx in np.argsort(hf.ravel())[::-1]:
        i, j = idx // n, idx % n
        r, c = ri[i, j], rj[i, j]
        if r >= 0:
            Lp[r, c] = max(Lp[r, c], Lp[i, j] + dd[i, j])
    cl = interior & (A > 100 * cellsize * cellsize) & (Lp > 0)
    hack = np.polyfit(np.log(A[cl]), np.log(Lp[cl]), 1)[0]
    return hi, theta, hack


def our_terrain(n=180, cellsize=60.0, seed=0):
    idx = np.arange(n) * cellsize / (n * cellsize * 0.45)
    xx, yy = np.meshgrid(idx, idx)
    f = noise.fbm(xx, yy, seed, octaves=6, base=noise.perlin)
    base = (f - f.min()) / (f.max() - f.min()) * 900.0
    h = SP.stream_power_evolve(base, np.full((n, n), 3e-4), 1e-5, 0.45, 1e3, 80, cellsize)
    return TH.thermal_erosion(h, 0.6, 10, cellsize)


def main():
    print("real-DEM empirical comparison (same estimator both sides)\n")
    fmt = "  {:28s}  HI={:.3f}  concavity θ={:.3f}  Hack h={:.3f}"
    lo = {"hi": 9, "th": 9, "hk": 9}
    hi_r, th_r, hk_r = [], [], []
    for name, url in TILES.items():
        dem = fetch_dem(url)
        if dem is None:
            continue
        for k, (r0, c0) in enumerate([(1200, 1200), (1800, 1400), (2000, 1000)]):
            w = dem[r0:r0 + 360, c0:c0 + 360][::2, ::2]
            hi, th, hk = metrics(w, 60.0)
            hi_r.append(hi); th_r.append(th); hk_r.append(hk)
            print(fmt.format(f"REAL {name}" if k == 0 else "  \"", hi, th, hk))

    hi_o, th_o, hk_o = metrics(our_terrain(), 60.0)
    print("\n" + fmt.format("OURS stream power", hi_o, th_o, hk_o))
    if hi_r:
        print(f"\n  real ranges: HI [{min(hi_r):.2f},{max(hi_r):.2f}]  "
              f"θ [{min(th_r):.2f},{max(th_r):.2f}]  Hack [{min(hk_r):.2f},{max(hk_r):.2f}]")
        inside = (min(hi_r) <= hi_o <= max(hi_r) and min(th_r) <= th_o <= max(th_r)
                  and min(hk_r) <= hk_o <= max(hk_r))
        print(f"  ours falls inside the real range on all three: {inside}")


if __name__ == "__main__":
    main()
