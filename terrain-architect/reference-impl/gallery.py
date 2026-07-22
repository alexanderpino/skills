"""Visual reference gallery — render every algorithm on ONE shared canonical base and tile
the results into a contact sheet (`gallery.png`).

The `09` doctrine is that the quantitative oracle decides correctness and the eye is the
*complementary* check ("don't sign off from one hero shot"). Every module here already has its
oracle in `tests/`; this is the by-eye pass that sits alongside them — and the regression
baseline (a rendered algorithm that changes shape is a prompt to look).

All terrain-consuming panels share the SAME seed-0 fBm base, so differences between panels are
the *operator*, not the input — the right use of a common noise base (the oracle tests keep
their analytic inputs, which is what makes them decisive). Run: `python gallery.py`.
"""
import numpy as np

import analysis
import analytic
import diffusion
import dunes
import erosion_droplet
import erosion_pipe
import erosion_streampower
import erosion_thermal
import flow
import isostasy
import landforms
import noise
import ops_filters
import render
import scatter
import sims_illustrative as sims
import winds

TILE = 96
SEED = 0
CELLSIZE = 20.0                                    # metres/cell for the base (extent ~1.9 km)

# Numeric sanity trace: per-view rendering NORMALISES, so a numerically degenerate field
# (e.g. an erosion blow-up) still renders "fine". We record raw ranges and flag any field
# whose relief is absurd or non-finite — the check the eye cannot make.
_REPORT = []


def _track(name, field):
    a = np.asarray(field, dtype=np.float64)
    _REPORT.append((name, float(np.nanmin(a)), float(np.nanmax(a)), bool(np.all(np.isfinite(a)))))
    return field


def _coords(n, wavelength):
    idx = np.arange(n) * CELLSIZE / wavelength
    return np.meshgrid(idx, idx)


def _base(relief=300.0):
    xx, yy = _coords(TILE, wavelength=TILE * CELLSIZE * 0.45)
    f = noise.fbm(xx, yy, SEED, octaves=6, base=noise.perlin)
    f = (f - f.min()) / (f.max() - f.min())
    return f * relief                              # metres of relief


def _diverging(field):
    """Diverging grey ramp centred at 0 — for curvature (negative dark, positive light)."""
    a = np.asarray(field, dtype=np.float64)
    s = np.max(np.abs(a)) + 1e-12
    return render._grey(0.5 + 0.5 * a / s)


def panels():
    """(label, RGB tile) for every algorithm, all on the shared base where terrain is input."""
    base = _track("base", _base())
    xx, yy = _coords(TILE, wavelength=TILE * CELLSIZE * 0.45)
    out = []

    # --- 01 noise (each its own field; greyscale) ---
    out.append(("noise perlin", render.greyscale(noise.perlin(xx, yy, SEED))))
    out.append(("noise value", render.greyscale(noise.value(xx, yy, SEED))))
    out.append(("noise worley F2-F1", render.greyscale(noise.worley(xx, yy, SEED))))
    out.append(("noise fbm", render.greyscale(noise.fbm(xx, yy, SEED))))
    out.append(("noise ridged", render.greyscale(noise.ridged_mf(xx, yy, SEED))))
    out.append(("noise hybrid", render.greyscale(noise.hybrid_mf(xx, yy, SEED))))
    out.append(("noise warp", render.greyscale(noise.domain_warp(xx, yy, SEED)[0])))
    vx, vy = noise.curl(xx, yy, SEED)
    out.append(("noise curl |v|", render.greyscale(np.hypot(vx, vy))))

    # --- the shared base, then 10 ops/filters on it ---
    out.append(("BASE (hillshade)", render.hillshade(base, CELLSIZE)))
    out.append(("gaussian", render.hillshade(ops_filters.gaussian(base, 2.0), CELLSIZE)))
    spiked = base.copy()
    spiked[TILE // 3, TILE // 3] = base.max() + 400.0
    out.append(("median despike", render.hillshade(ops_filters.median(spiked, 1), CELLSIZE)))
    out.append(("bilateral", render.hillshade(ops_filters.bilateral(base, 2.0, 30.0), CELLSIZE)))
    out.append(("perona-malik", render.hillshade(ops_filters.perona_malik(base, 30.0, 15), CELLSIZE)))
    out.append(("morphology tophat", render.greyscale(ops_filters.tophat(base, 2))))
    yy2, xx2 = np.mgrid[0:TILE, 0:TILE].astype(float)
    a = ops_filters.cone(xx2 - 32, yy2 - 32, 30, 200.0)
    b = ops_filters.cone(xx2 - 60, yy2 - 60, 30, 200.0)
    out.append(("smin (two cones)", render.hillshade(ops_filters.smin(a, b, 40.0), CELLSIZE)))
    out.append(("SDF box", render.greyscale(ops_filters.sd_box(xx2 - 48, yy2 - 48, 20, 12))))

    # --- erode the base with the CORRECT backbone for the extent (<2 km -> droplet), then
    #     06 analysis on the FINAL height. (Using stream power here would be the wrong backbone
    #     for the scale and blows up — see the streampower panel below for its proper regime.) ---
    eroded = erosion_droplet.droplet_erode(base, n_droplets=8000, seed=SEED, brush_radius=2)
    eroded = _track("eroded", erosion_thermal.thermal_erosion(eroded, 0.7, 25, CELLSIZE))
    filled = flow.priority_flood_fill(eroded)
    area = flow.d8_accumulation(filled, CELLSIZE)
    slope = analysis.slope(eroded, CELLSIZE)
    out.append(("eroded (hillshade)", render.hillshade(eroded, CELLSIZE)))
    out.append(("slope shade", render.slope_shade(eroded, CELLSIZE)))
    out.append(("curvature", _diverging(analysis.curvature(eroded, CELLSIZE, "profile"))))
    out.append(("horizon AO", render.greyscale(analysis.horizon_ao(eroded, CELLSIZE))))
    out.append(("TWI", render.greyscale(analysis.twi(area, slope, CELLSIZE))))
    out.append(("flow overlay", render.flow_overlay(eroded, area, CELLSIZE)))
    stack = analysis.derive_materials(eroded, slope, area, CELLSIZE, rng_seed=SEED)
    out.append(("materials", render.material_rgb(np.stack([m for _, m in stack]), CELLSIZE)))
    dens = analysis.smoothstep(np.tan(np.radians(18)), np.tan(np.radians(35)), slope)
    pts = scatter.scatter_by_density(TILE * CELLSIZE, TILE * CELLSIZE,
                                     lambda p: float(scatter.sample_field(dens, [p], CELLSIZE)[0]),
                                     r_min=CELLSIZE * 3, seed=SEED)
    out.append(("scatter", render.scatter_overlay(render.hillshade(eroded, CELLSIZE), pts,
                                                  CELLSIZE, color=(210, 60, 40))))

    # stream power in its PROPER regime — a continental extent (cellsize 2 km, ~200 km domain),
    # which is the backbone rule from SKILL.md (>50 km). Here it converges and stays bounded.
    cont = _base(relief=1500.0)
    sp = erosion_streampower.stream_power_evolve(cont, np.full((TILE, TILE), 3e-4),
                                                 1e-5, 0.45, 1e3, 60, cellsize=2000.0)
    out.append(("streampower (200km)", render.hillshade(_track("streampower", sp), 2000.0)))

    # --- 11 landforms ---
    flat = np.zeros((TILE, TILE))
    out.append(("crater simple", render.hillshade(
        landforms.impact_crater(flat, 48, 48, 600.0, CELLSIZE, complex_D=1e9), CELLSIZE)))
    out.append(("crater complex", render.hillshade(
        landforms.impact_crater(flat, 48, 48, 900.0, CELLSIZE, complex_D=400.0), CELLSIZE)))
    nb = (base - base.min()) / (base.max() - base.min())
    out.append(("terrace", render.hillshade(
        landforms.terrace(nb, 6, 8.0, warp_amp=0.05, cellsize=CELLSIZE) * 300.0, CELLSIZE)))
    folded = landforms.fold(base, xx2 * CELLSIZE, yy2 * CELLSIZE, 120.0, (1.0, 0.3), 0.004)
    out.append(("fold", render.hillshade(folded, CELLSIZE)))
    sol = np.zeros((TILE, TILE))
    sol[:, :TILE // 2] = 1.0
    hk, _ = landforms.karst_sinkholes(base, sol, CELLSIZE, spacing=CELLSIZE * 6,
                                      depth=60.0, radius=CELLSIZE * 2, seed=SEED)
    out.append(("karst (left soluble)", render.hillshade(hk, CELLSIZE)))

    # --- 12/19 illustrative sims ---
    bed_l, L, T, _ = sims.lava_flow(base * 0.2, (48, 40), 60, cool=150.0, cellsize=CELLSIZE)
    out.append(("lava (illustrative)", render.hillshade(_track("lava bed", bed_l), CELLSIZE)))
    cap = 200.0 * np.exp(-((xx2 - 48) ** 2 + (yy2 - 48) ** 2) / (2 * 16.0 ** 2))
    H = sims.glacier_sia(base, cap, 1, cellsize=CELLSIZE, dt=5e6)
    out.append(("glacier ice H (illus.)", render.greyscale(_track("glacier H", H))))
    coast = sims.coastal_retreat(base, base.mean(), 8, k_coast=2.0, notch=8.0, cellsize=CELLSIZE)
    out.append(("coastal (illustrative)", render.hillshade(_track("coastal", coast), CELLSIZE)))
    inter = sims.intertidal_mask(base, base.mean(), 60.0).astype(float)
    out.append(("tides intertidal (illus.)", render.greyscale(inter)))

    # --- the remaining verified modules: diffusion, dunes, pipe, flexure, wind, tephra, PDC, seafloor ---
    out.append(("diffusion (Culling)", render.hillshade(
        diffusion.hillslope_diffuse(base, 50.0, diffusion.stable_dt(50.0, CELLSIZE), 30, CELLSIZE),
        CELLSIZE)))
    sand = 5.0 + 3.0 * noise.value(xx * 2, yy * 2, 1)
    out.append(("dunes (Werner)", render.hillshade(
        _track("dunes", dunes.werner_dunes(sand, 300, seed=SEED, wind=(0, 1))), CELLSIZE)))
    out.append(("pipe water depth", render.greyscale(erosion_pipe.pipe_water(
        base, np.full((TILE, TILE), 2.0), 120, rain=0.0, dt=0.01, cellsize=CELLSIZE))))
    mtn = 800.0 * np.exp(-((xx2 - 48) ** 2 + (yy2 - 48) ** 2) / (2 * 15.0 ** 2))
    Dr = isostasy.flexural_rigidity(7e10, 20000.0)
    out.append(("flexure (200 km)", render.greyscale(
        _track("flexure", isostasy.flexure_fft(mtn * 2700 * 9.81, Dr, 3300.0, cellsize=2000.0)))))
    sx, sy = analysis.gradient(base, CELLSIZE)
    uu, vv = winds.mass_consistent(1.0 - 20.0 * sx, 0.3 - 20.0 * sy, CELLSIZE)
    out.append(("wind speed |v|", render.greyscale(np.hypot(uu, vv))))
    rr = np.hypot(xx2 - 48, yy2 - 48) * CELLSIZE
    out.append(("tephra fallout", render.greyscale(
        _track("tephra", analytic.tephra_thickness(rr + 1.0, 100.0, 0.002)))))
    pdc = analytic.pdc_inundated(base, (48, 48), 500.0, 0.55, CELLSIZE).astype(np.float64)
    hs = render.hillshade(base, CELLSIZE).astype(np.float64)
    tint = hs * (1 - 0.5 * pdc[..., None]) + np.array([220, 90, 40]) * 0.5 * pdc[..., None]
    out.append(("PDC inundation", np.clip(tint, 0, 255).astype(np.uint8)))
    age = (xx2 / TILE) * 100.0
    out.append(("seafloor age-depth", render.greyscale(
        _track("age-depth", analytic.seafloor_depth_hsc(age + 0.1)))))
    return out


def montage(tiles, cols=6, pad=3, bg=30):
    n = len(tiles)
    rows = (n + cols - 1) // cols
    h = w = TILE
    out = np.full((rows * (h + pad) + pad, cols * (w + pad) + pad, 3), bg, dtype=np.uint8)
    for k, (_, tile) in enumerate(tiles):
        r, c = divmod(k, cols)
        y0 = pad + r * (h + pad)
        x0 = pad + c * (w + pad)
        out[y0:y0 + h, x0:x0 + w] = tile
    return out


def main():
    tiles = panels()
    img = montage(tiles)
    render.write_png("gallery.png", img)
    print(f"wrote gallery.png ({len(tiles)} panels, {img.shape[1]}x{img.shape[0]})")
    for k, (label, _) in enumerate(tiles):
        print(f"  {k:2d} [{k // 6},{k % 6}]  {label}")

    # numeric sanity — what the normalised renders cannot show. Per-view rendering hides a
    # blown-up field (this caught a stream-power-at-the-wrong-scale explosion once); the trace
    # makes it loud.
    print("\nfield ranges (relief the render normalises away):")
    base_relief = next(hi - lo for n, lo, hi, _ in _REPORT if n == "base")
    suspect = 0
    for name, lo, hi, finite in _REPORT:
        relief = hi - lo
        ok = finite and relief < 50 * base_relief
        suspect += 0 if ok else 1
        print(f"  {name:14s} [{lo:11.2f}, {hi:11.2f}]  relief={relief:11.2f}"
              f"{'' if ok else '   <-- SUSPECT'}")
    print(f"\nSANITY: {suspect} suspect field(s).")
    return suspect


if __name__ == "__main__":
    main()
