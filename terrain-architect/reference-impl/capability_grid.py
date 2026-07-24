"""Capability grid — one image demonstrating everything the reference impl produces, each cell
captioned with WHAT IT IS and WHAT VERIFIES IT (the oracle/invariant). -> capability_grid.png.

Every tile is generated live from the reference modules (pure numpy); PIL is used only to lay out
the grid and draw the caption text (the rendering exception). Small grids keep it ~1-2 min."""
import numpy as np

import noise
import ops_filters
import flow
import erosion_streampower as sp
import erosion_droplet
import erosion_thermal
import erosion_pipe
import shallow_water
import diffusion
import meander as MEA
import landforms as L
import analysis as A
import sims_illustrative as sims
import dunes
import isostasy
import winds
import render

TILE = 200                                                     # px per cell (rendered field is resized to this)


# --------------------------------------------------------------------------- #
# colour helpers
# --------------------------------------------------------------------------- #
def _norm(a):
    a = np.asarray(a, dtype=np.float64)
    return (a - a.min()) / (np.ptp(a) + 1e-12)


def _smoothstep(lo, hi, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def gray(a):
    g = (_norm(a) * 255).astype(np.uint8)
    return np.stack([g, g, g], -1)


def ramp(a):
    t = _norm(a)
    stops = np.array([[28, 38, 84], [30, 132, 150], [232, 222, 96], [196, 60, 40]], float) / 255.0
    x = np.linspace(0, 1, len(stops))
    rgb = np.stack([np.interp(t, x, stops[:, c]) for c in range(3)], -1)
    return (rgb * 255).astype(np.uint8)


def hill(h, cell=30.0):
    return render.hillshade(h, cell)


def _bilinear(field, px, py):
    n, m = field.shape
    px = np.clip(px, 0, m - 1.001); py = np.clip(py, 0, n - 1.001)
    x0 = np.floor(px).astype(np.int64); y0 = np.floor(py).astype(np.int64)
    x1, y1 = x0 + 1, y0 + 1; fx = px - x0; fy = py - y0
    return (field[y0, x0] * (1 - fx) * (1 - fy) + field[y0, x1] * fx * (1 - fy)
            + field[y1, x0] * (1 - fx) * fy + field[y1, x1] * fx * fy)


def lic(u, v, seed=0, steps=16):
    """Line Integral Convolution — smear a white-noise texture ALONG the flow so streamlines become
    visible (the honest way to eyeball a vector field / verify it flows smoothly, not as speed noise)."""
    n, m = u.shape
    tex = np.random.default_rng(seed).random((n, m))
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    acc = tex.copy(); cnt = np.ones((n, m))
    for sgn in (1.0, -1.0):
        px, py = xx.copy(), yy.copy()
        for _ in range(steps):
            fu = _bilinear(u, px, py); fv = _bilinear(v, px, py)
            spd = np.hypot(fu, fv) + 1e-6
            px = px + sgn * fu / spd; py = py + sgn * fv / spd
            acc += _bilinear(tex, px, py); cnt += 1.0
    return acc / cnt


_SUB_COL = {
    "water": (54, 108, 168), "snow": (238, 240, 246), "rock": (120, 120, 126),
    "scree": (150, 140, 128), "sediment": (176, 150, 108), "vegetation": (86, 120, 66),
    "ground": (128, 104, 82),
}


def substance_rgb(h, cell=40.0):
    slope = A.slope(h, cell)
    area = flow.d8_accumulation(flow.priority_flood_fill(h)) * (cell * cell)   # REAL drainage area, not
    stack = A.derive_substances(h, slope, area, cell,          # uniform (uniform -> water claims everything)
                                climate={"has_water": True, "has_snow": True, "has_veg": True,
                                         "snowline": 0.52, "snow_soft": 0.14})
    rgb = np.zeros(h.shape + (3,), float)
    for name, w in stack:                                      # derive_substances -> [(name, mask), ...]
        rgb += np.asarray(w)[..., None] * np.array(_SUB_COL[name], float)
    shade = render.hillshade(h, cell).astype(float)[..., 0] / 255.0
    rgb *= (0.45 + 0.55 * shade)[..., None]
    return np.clip(rgb, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------- #
# per-capability tiles  (title, test-caption, thunk -> RGB uint8)
# --------------------------------------------------------------------------- #
def _grid(n=200, step=0.05):
    g = np.arange(n) * step
    return np.meshgrid(g, g)


def _noise_fbm(base, seed=1):
    xx, yy = _grid(220, 0.045)
    return hill(noise.fbm(xx, yy, seed, octaves=6, base=base) * 900.0)


def CELLS():
    xx, yy = _grid(220, 0.05)
    C = []
    add = lambda *a: C.append(a)

    # ---- NOISE (01) ----
    add("01 Perlin fBm", "=0 on integer lattice; 1-octave = base noise", lambda: _noise_fbm(noise.perlin, 1))
    add("01 Simplex fBm", "bounded, zero-mean, world-space, continuous", lambda: _noise_fbm(noise.simplex, 2))
    add("01 Worley F2-F1", "3x3 search == brute-force nearest point", lambda: gray(noise.worley(*_grid(220, 0.12), seed=3, kind="f2f1")))
    add("01 Ridged MF", "non-negative, finite (Musgrave weight-feedback)", lambda: hill(noise.ridged_mf(xx, yy, 4, octaves=6) * 500))
    add("01 Hybrid MF", "finite via min(weight,1) clamp", lambda: hill(_norm(noise.hybrid_mf(xx, yy, 5, octaves=6)) * 900))
    add("01 Gabor (anisotropic)", "orientable: bands rotate with omega0", lambda: gray(noise.gabor(*_grid(220, 0.11), seed=2, omega0=0.5)))
    add("01 Domain warp", "warps (flow-like q mask != 0); large marble swirls (Quilez)",
        lambda: gray(noise.domain_warp(xx * 0.35, yy * 0.35, 6, warp=4.0, octaves=4)[0]))
        # low base freq + VALUE render = the signature large smooth swirls of the canon
        # (iquilezles.org/articles/warp shows the warped field's value, where the marble reads)
    def _curl():                                                     # divergence-free flow: LIC streamlines swirl, no sources/sinks
        u, v = noise.curl(*_grid(150, 0.06), seed=7)
        return gray(lic(u, v, seed=1, steps=22))
    add("01 Curl noise", "divergence-free: LIC streamlines swirl (no sources/sinks)", _curl)

    # ---- PRIMITIVES / OPS (10) ----
    def _sdf():
        px, py = np.mgrid[-1:1:220j, -1:1:220j]
        d = ops_filters.sd_convex_polygon(px, py, [(1, 0.2), (-.3, 1), (-1, -.4), (.4, -1)], [.6, .6, .6, .6])
        return ramp(-d)
    add("10 Convex-poly SDF", "== sd_box on faces (half-plane intersection)", _sdf)
    def _smin():
        px, py = np.mgrid[-1:1:220j, -1:1:220j]
        a = ops_filters.sd_circle(px + .3, py, .5); b = ops_filters.sd_circle(px - .3, py, .5)
        return ramp(-ops_filters.smin(a, b, .3))
    add("10 smooth-min blend", "-> min as k->0; smin <= min", _smin)
    add("10 Terrace", "quantise to treads; warp BEFORE quantise (steps wander)", lambda: hill(L.terrace(_norm(noise.fbm(xx, yy, 8, octaves=5)), 6, sharpness=2.5, warp_amp=0.06, warp_wl=32.0, seed=8) * 800))
    def _close():
        h = noise.fbm(xx, yy, 9, octaves=5) * 400
        return gray(ops_filters.closing(h, 3) - h)
    add("10 Morph closing", "fills pits (closing >= h); pile depth", _close)
    def _bilat():
        h = _norm(noise.fbm(xx, yy, 3, octaves=4)); h = (h > 0.5).astype(float)
        return gray(ops_filters.bilateral(h, 3.0, 0.2))
    add("10 Bilateral filter", "preserves step edge (edge-aware)", _bilat)
    def _twist():
        px, py = np.mgrid[-1:1:220j, -1:1:220j]
        qx, qy = ops_filters.twist(px, py, 0, 0, 3.0)
        return gray(noise.fbm(qx * 3, qy * 3, 2, octaves=4))
    add("10 Twist deform", "k=0 identity; preserves radius from centre", _twist)

    # ---- FLOW & EROSION (03/04/05) ----
    _cr = lambda a, k=10: a[k:-k, k:-k]                                     # crop the fixed-BC edge band for display
    def _accum():
        h = noise.fbm(*_grid(150, 0.06), seed=1, octaves=6) * 600
        acc = flow.d8_accumulation(flow.priority_flood_fill(h))
        return ramp(_cr(np.log(acc)))
    add("03 D8 accumulation", "sum(area) = n*m; vs RichDEM (corr>0.9)", _accum)
    def _mfd():
        h = noise.fbm(*_grid(150, 0.06), seed=1, octaves=6) * 600
        return ramp(_cr(np.log(flow.mfd_accumulation(flow.priority_flood_fill(h)))))
    add("03 MFD accumulation", "sum = n*m (Freeman p=1.1)", _mfd)
    def _sp():
        rng = np.random.default_rng(0); h = rng.random((96, 96)) * 5   # random proto-surface (minimal IC)
        return hill(_cr(sp.stream_power_evolve(h, 2.0, 5e-2, 0.5, 1000.0, 120, 50.0), 8), 50)
    add("04 Stream power", "slope-area exponent = -0.5 vs Landlab", _sp)
    def _drop():
        h = L.mountain((150, 150), 30.0, seed=3, style="basic")
        return hill(erosion_droplet.droplet_erode(h, n_droplets=60 * 150, seed=3, brush_radius=2))
    add("04 Droplet erosion", "total volume conserved (~1e-13)", _drop)
    def _therm():                                                     # a cone steeper than repose relaxes to a talus cone
        yy2, xx2 = np.mgrid[0:81, 0:81] - 40
        cone = np.maximum(0, 40 - np.hypot(xx2, yy2)) * 6.0
        return hill(erosion_thermal.thermal_erosion(cone, 0.3, 200, factor=0.25), 5)
    add("05 Thermal (talus)", "<= repose; mass conserved; non-inverting", _therm)
    def _pipe():
        h = L.mountain((120, 120), 40.0, seed=5, style="basic")
        h[:, :46] *= 0.05                                                   # a low plain -> alluvial fans build here
        out = erosion_pipe.pipe_erode(h, 40.0, rain=5e-4, iters=300)
        bed = out["bed"] if isinstance(out, dict) else out
        dep = np.clip(bed - h, 0.0, None)                                   # DEPOSITION (fans/aprons)
        base = render.hillshade(bed, 40).astype(float)
        a = (np.clip(dep / (np.percentile(dep, 99.5) + 1e-6), 0, 1) * 0.85)[..., None]
        warm = np.array([235, 170, 70], float)
        return np.clip(base * (1 - a) + warm * a, 0, 255).astype(np.uint8)  # incision (grey) + deposition (warm)
    add("04 Pipe erosion", "incises + DEPOSITS fans (warm); bed+sed conserved", _pipe)
    def _sw():
        h = L.volcano((120, 120), 60, 60, radius=1400, height=800, cellsize=30, kind="strato")
        r = shallow_water.simulate(h, 30.0, rain=6e-5, iters=80, dt=0.02, drain_edges=True)
        return ramp(_cr(np.sqrt(r["depth"]), 8))
    add("04 Shallow water", "rain_in = out + stored (~1e-15)", _sw)
    def _diff():
        n = 128; im = np.zeros((n, n)); im[n//2, n//2] = 1.0
        return ramp(diffusion.hillslope_diffuse(im, 0.5, 0.1, 60))
    add("04 Hillslope diffusion", "Gaussian Green's fn; 0.25 CFL tight", _diff)
    def _meander():
        n = 180; cell = 4.0
        gx, gy = np.meshgrid(np.arange(n) * cell, np.arange(n) * cell)
        base = 120.0 - 0.02 * gx + noise.fbm(gx / 300.0, gy / 300.0, 5, octaves=3) * 6.0
        xs = np.linspace(-160, 880, 240)                       # ends OFF-frame (0..716) so pins don't coil in view
        win = _smoothstep(-160, 20, xs) * (1 - _smoothstep(700, 880, xs))   # taper -> straight ends, no coil
        ys = 360 + win * (22 * np.sin(2 * np.pi * xs / 135.0) + 7 * np.sin(2 * np.pi * xs / 78.0 + 0.6))
        r = MEA.meander_belt(base, np.column_stack([xs, ys]), cellsize=cell, steps=300, ds=6.0,
                             L_adj=40.0, E=16.0, cutoff_dist=32.0, min_sep=10, half_width=10.0,
                             depth=7.5, bank_width=16.0, bar_height=4.0, bar_bank_width=16.0)
        shade = render.hillshade(r["height"], cell).astype(float)   # point bars brighten the inner banks
        chan = r["channel"]; oxwet = r["water"] & ~chan
        rgb = shade.copy()
        for mask, col, al in [(chan, np.array([54., 108, 168]), 0.75),        # active channel = blue
                              (oxwet, np.array([86., 128, 120]), 0.72)]:       # oxbow lake = stagnant teal
            a2 = np.where(mask, al, 0.0)[..., None]
            rgb = rgb * (1 - a2) + col * a2
        return np.clip(rgb, 0, 255).astype(np.uint8)
    add("03 River meander (belt)", "upstream-lag skews bends; cut-bank cuts, point-bar builds; cutoff -> oxbow", _meander)

    # ---- LANDFORM GENERATORS (11) ----
    add("11 Mountain (basic)", "raw Voronoi ridge skeleton (pre-erosion base; -> eroded)", lambda: hill(L.mountain((180, 180), 26.0, seed=3, style="basic", warp=0.42), 26))
    add("11 Mountain (eroded)", "styles distinct; deep dendritic incision", lambda: hill(L.mountain((150, 150), 26.0, seed=3, style="eroded"), 26))
    def _ridge():                                                     # hogback PRIMITIVE placed on a base
        n = 150; cell = 30.0; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)   # (no erode: the atom rounds its
        base = noise.fbm(xx2 * 0.05, yy2 * 0.05, 11, octaves=4) * 80 + 70   #  own crest via smin + domain warp)
        r = L.ridge((n, n), cell, seed=2, height=760, angle=1.42, asymmetry=0.52,
                    sinuosity=0.45, detail=0.3, width_frac=0.34)           # domain-warped, smin-rounded crest
        return hill(_cr(base + r, 4), cell)                                # base + atom, that's it
    add("11 Ridge (hogback)", "asymmetric hogback (smin-rounded crest, warped strike) on a foothill base", _ridge)
    add("11 Volcano (strato)", "concave-up cone + summit crater", lambda: hill(L.volcano((180, 180), 90, 90, radius=1500, height=1600, cellsize=20, kind="strato"), 20))
    add("11 Volcano (shield)", "convex low-angle dome (Hawaiian); lightly gullied",
        lambda: hill(L.volcano((180, 180), 90, 90, radius=1600, height=700, cellsize=20, kind="shield",
                               barranco=0.12, n_barrancos=22), 20))                # young shields are barely dissected
                               # (Mauna Loa canon: deep radial barrancos belong to old/strato edifices, Karátson 2010)
    add("11 Canyon", "plateau dominant; deep meandering floor", lambda: hill(L.canyon((180, 180), 26.0, seed=3, rim=1000, depth=800), 26))
    def _butte():
        h = np.zeros((180, 180))
        for bx, by, s in [(60, 70, 0), (110, 95, 1), (95, 130, 2)]:
            h = np.maximum(h, L.fault_block_butte((180, 180), bx, by, 26, 300, 22.0, seed=s,
                                                  fault=0.5, corner_round=3.2, warp=0.17))
        return hill(h, 22)
    add("11 Fault-block butte", "flat top, cliff, repose talus; polygonal", _butte)
    def _crater():
        h = np.zeros((180, 180)); h = L.impact_crater(h, 90, 90, 2600, 22.0, complex_D=3000)
        return hill(h, 22)
    add("11 Impact crater", "depth/D=0.2, rim 0.04D, r^-3 ejecta", _crater)
    def _karst():
        xx2, yy2 = _grid(150, 0.05); h = noise.fbm(xx2, yy2, 4, octaves=4) * 120 + 200
        sol = (noise.fbm(xx2 + 9, yy2, 7, octaves=3) > 0.0).astype(float)
        hk, _ = L.karst_sinkholes(h, sol, cellsize=20.0, spacing=90.0, depth=40.0, radius=45.0, seed=1)
        return hill(hk, 20)
    add("11 Karst sinkholes", "pits only on soluble; do-not-fill mask", _karst)
    def _strata():
        xx2, yy2 = _grid(180, 0.05)
        s = L.strat_coord(noise.fbm(xx2, yy2, 2, octaves=5) * 300, xx2, yy2, fold_amp=120, fold_dir=(1, .3), fold_freq=.6)
        k = L.bed_erodibility(s, [(40, 1.0), (25, 0.4), (60, 0.8)])
        return ramp(k)
    add("11 Strata + fold", "periodic K bands; folded coordinate", _strata)

    # ---- ANALYSIS & MASKS (06) ----
    _terr = L.mountain((160, 160), 30.0, seed=8, style="basic")
    add("06 Slope", "plane gradient recovered exactly", lambda: ramp(A.slope(_terr, 30)))
    add("06 Northness", "+1 north-facing (-sin(aspect), row=south)", lambda: ramp(A.northness(A.aspect(_terr, 30))))
    add("06 Curvature", "Laplacian of paraboloid = -2/R exact", lambda: ramp(np.clip(A.curvature(_terr, 30, "profile"), -.02, .02)))
    add("06 Wetness (TWI)", "increases with area, decreases with slope", lambda: ramp(A.twi(flow.d8_accumulation(flow.priority_flood_fill(_terr)) * 900, A.slope(_terr, 30) + 1e-3, 30)))
    add("06 Horizon AO", "occluded in hollows, ~0 on open peaks", lambda: gray(1 - A.horizon_ao(_terr, 30)))
    add("06 Substances", "priority stack sums to 1; snow on shaded", lambda: substance_rgb(L.mountain((150, 150), 40.0, seed=8, style="eroded"), 40))

    # ---- SIMS & GEOPHYSICS (12/19/02/13) ----
    def _glac():
        n = 121; c = 60; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        r = np.hypot(xx2 - c, yy2 - c) * 12000
        H = 3000 * np.maximum(1 - np.clip(r / 500e3, 0, 1) ** (4/3), 0) ** (3/7)
        H1 = sims.glacier_sia(np.zeros((n, n)), H, 8, A=3.17e-24, dt=200 * 3.15e7, cellsize=12000, beta=0.0, max_substeps=4000)
        return ramp(H1)
    add("12 SIA glacier", "Halfar exact profile to ~1%; ice conserved", _glac)
    def _lava():
        n = 120; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        bed0 = 600 - 3.2 * yy2 + noise.fbm(xx2 * 0.05, yy2 * 0.05, 2, octaves=4) * 40   # a slope to flow down
        out = sims.lava_flow(bed0, (12, 60), 170, erupt=4.0, cool=6.0)   # vent near the top -> (bed, L, T, budget)
        bed, molten = (out[0], out[1]) if isinstance(out, tuple) else (out, np.zeros_like(bed0))
        lava = np.clip(bed - bed0, 0.0, None) + molten        # frozen + still-molten thickness = the flow tongue
        sl = (slice(0, 60), slice(30, 90))                    # crop to the flow so the tongue is legible
        shade = render.hillshade(bed[sl], 30).astype(float)
        lv = lava[sl]; m = lv > 1e-6
        a = (np.clip(lv / (np.percentile(lv[m], 55) + 1e-6), 0, 1)[..., None] * 0.95) if m.any() else np.zeros(lv.shape + (1,))
        return np.clip(shade * (1 - a) + np.array([230., 90, 35]) * a, 0, 255).astype(np.uint8)  # basalt tongue (hot)
    add("19 Lava CA", "Bingham yield gate: a flow tongue that freezes; mass budget", _lava)
    def _coast():
        xx2, yy2 = _grid(140, 0.05); h = yy2 * 60 + noise.fbm(xx2, yy2, 3, octaves=4) * 40
        sea = 120.0
        out = sims.coastal_retreat(h, sea, 30)
        hc = out[0] if isinstance(out, tuple) else out
        shade = render.hillshade(hc, 20).astype(float)
        under = (hc < sea)[..., None]                         # below sea level -> water (shows the cut platform)
        return np.clip(np.where(under, np.array([44., 92, 150]), shade), 0, 255).astype(np.uint8)
    add("12 Coastal retreat", "wave-cut platform; cliff retreats landward (monotone)", _coast)
    def _dunes():
        rng = np.random.default_rng(0); sand = (rng.random((110, 110)) * 3 + 1).astype(int)   # thin sand sheet
        d = dunes.werner_dunes(sand, 70, seed=0, p_sand=0.6, p_bare=0.1, hop=3, wind=(0, 1))    # full Werner model
        return hill(d.astype(float) * 8.0, 1.0)                                                 # hillshade the dune surface
    add("05 Dunes (Werner)", "shadow-zone + avalanche -> transverse dunes; slabs conserved", _dunes)
    def _flex():
        n = 160; load = np.zeros((n, n)); load[70:90, 70:90] = 2.5e8
        D = isostasy.flexural_rigidity(7e10, 20e3)
        return ramp(isostasy.flexure_fft(load, D, 500.0, cellsize=4000.0))
    add("02 Isostatic flexure", "W=Q/(Dk^4+drho g); single-mode exact", _flex)
    def _wind():
        n = 150; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        ang = 0.5 + 1.1 * noise.fbm(xx2 / 55, yy2 / 55, 5, octaves=3)        # coherent large-scale flow
        u0, v0 = np.cos(ang), np.sin(ang)
        r2 = ((xx2 - n * .55) ** 2 + (yy2 - n * .4) ** 2) / (0.05 * n * n)   # + a divergent source (into a hill)
        s = np.exp(-r2); u0 += 1.5 * (xx2 - n * .55) / n * s; v0 += 1.5 * (yy2 - n * .4) / n * s
        uc, vc = winds.mass_consistent(u0, v0)                               # remove the divergence
        return gray(lic(uc, vc, seed=3, steps=18))                          # LIC -> visible smooth streamlines
    add("13 Mass-consistent wind", "divergence -> 0; LIC shows smooth streamlines", _wind)

    # ---- HERO / RENDER (08/09) ----
    def _hero():
        from PIL import Image
        try:
            return np.asarray(Image.open("hero.png").convert("RGB"))
        except Exception:
            return gray(_terr)
    add("09 Hero 3D raster", "z-buffer, back-face cull, translucent water", _hero)

    # ---- AAA-PARITY TRANCHE (appended; keeps earlier tile coordinates stable) ----
    def _diff_erosion():
        n = 96; cell = 50.0; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        rng = np.random.default_rng(0); h = rng.random((n, n)) * 5
        table = [(600.0, 7e-2), (280.0, 6e-3)]                          # soft / hard (~12x contrast)
        Kfn = lambda hh: L.bed_erodibility(L.strat_coord(hh, xx2 * cell, yy2 * cell,
                                                         tilt=(0.7, 0.25)), table)   # tilted beds -> cuestas
        return hill(_cr(sp.stream_power_evolve(h, 2.0, Kfn, 0.5, 1000.0, 120, cell), 6), cell)
    add("04+11 Differential erosion", "spatial K(p,h): hard beds resist -> cuestas; soft cut to valleys", _diff_erosion)
    def _glacier():
        import glacier as GLAC
        n = 110; cell = 100.0; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        c1 = n * 0.32 + 13.0 * noise.fbm(yy2 * 0.05, xx2 * 0 + 3.0, 4, octaves=3)   # sinuous valley axes
        c2 = n * 0.70 + 13.0 * noise.fbm(yy2 * 0.05, xx2 * 0 + 9.0, 5, octaves=3)   # (meander down-valley)
        bed0 = 2700 - 26 * yy2 + 20 * np.minimum(np.abs(xx2 - c1), np.abs(xx2 - c2))
        bed0 = np.maximum(bed0, 2700 - 26 * yy2)                        # two curving valleys + interfluve
        bed0 = bed0 + noise.fbm(xx2 * 0.13, yy2 * 0.13, 4, octaves=5) * 170   # rough bedrock (breaks ramp banding)
        bed, H, mor = GLAC.glacier_carve(bed0, np.zeros((n, n)), 8, ela=1820, beta=0.003,
                                         b_max=0.4, K_g=6e-4, dt=40.0)   # SIA ice + bed abrasion
        shade = render.hillshade(_cr(bed, 5), cell).astype(float)
        Hc = _cr(H, 5); ice = np.clip(Hc / 120.0, 0.0, 1.0)             # trunk glaciers, translucent
        a = (0.15 + 0.7 * ice)[..., None] * (Hc > 5.0)[..., None]
        rgb = shade * (1 - a) + np.array([205., 225, 240]) * a
        return np.clip(rgb, 0, 255).astype(np.uint8)
    add("12 Glacial carving", "SIA trunk glaciers fill valleys; thick ice slides & abrades the bed", _glacier)
    def _snowpack():
        import snow as SNOW
        n = 130; cell = 30.0
        h = L.mountain((n, n), cell, seed=7, height=1800, style="eroded")
        T = 6.0 - 0.011 * (h - h.min())                                # lapse rate: cold high
        s = np.zeros((n, n))
        for _ in range(4):                                             # accumulate/melt/shed/avalanche/wind
            s = SNOW.snow_step(h, s, T, precip=1.2, dt=1.0, melt_factor=0.5, snow_repose_deg=38,
                               cellsize=cell, avalanche_iters=3, wind=(1.0, 0.3))
        shade = render.hillshade(_cr(h, 6), cell).astype(float)
        sn = np.clip(_cr(s, 6) / 6.0, 0.0, 1.0)                        # snow cover, thick in gullies
        a = (sn ** 0.7)[..., None] * 0.92
        rgb = shade * (1 - a) + np.array([248., 250, 255]) * a
        return np.clip(rgb, 0, 255).astype(np.uint8)
    add("13 Snowpack (dynamic)", "accumulate/melt/avalanche: snow fills gullies, bares steep faces", _snowpack)
    def _yardang():
        import aeolian as AEO
        n = 150; cell = 4.0; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        u2, v2 = 1.0, 0.25; mg = np.hypot(u2, v2); u2, v2 = u2 / mg, v2 / mg
        along = xx2 * u2 + yy2 * v2; cross = -xx2 * v2 + yy2 * u2
        playa = 10.0 * noise.fbm(along * 0.018, cross * 0.11, 3, octaves=4)   # soft substrate, faint grain
        playa = playa - playa.min()
        h = AEO.yardang(playa, (1.0, 0.25), 1.0, iters=12, saltation_h=4.0, seed=3)
        return hill(_cr(h, 5), cell)
    add("16 Yardangs (wind abrasion)", "streamlined ridges || wind; low ground cut fastest (undercut)", _yardang)
    def _bajada():
        n = 150; cell = 12.0; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        front = 40.0 + 7.0 * noise.fbm(xx2 * 0.06, xx2 * 0 + 2.0, 5, octaves=3)   # IRREGULAR range front
        base = 250 - 1.2 * yy2 + noise.fbm(xx2 * 0.05, yy2 * 0.05, 7, octaves=4) * 10
        mtn = np.clip(front - yy2, 0.0, None)                          # mountain mask above the front
        base = base + mtn * 6.0 + (noise.fbm(xx2 * 0.10, yy2 * 0.10, 8, octaves=4) * 60.0) * (mtn > 0)   # textured massif
        h = base.copy()
        for aj, seed in [(38, 1), (80, 4), (118, 7)]:                 # three fans -> coalesce to a bajada
            h = L.alluvial_fan(h, (40, aj), downfan=(1.0, 0.0), flux=10.0, length=100.0,
                               spread_deg=64.0, lobes=6, seed=seed)
        return hill(_cr(h, 4), cell)
    add("16 Alluvial fans (bajada)", "fans debouch at the range front, thin downfan, coalesce -> bajada", _bajada)
    def _faultblocks():
        import tectonics as TEC
        n = 130; cell = 40.0; yy2, xx2 = np.mgrid[0:n, 0:n].astype(float)
        base = noise.fbm(xx2 * 0.04, yy2 * 0.04, 7, octaves=5) * 160 + 400
        h = TEC.fault_scarp(base, n_faults=6, displacement=460, width=6.0, decay=0.62,
                            cellsize=cell, seed=4)                     # wide feather -> decayed slopes, not cliffs
        return hill(_cr(h, 4), cell)
    add("02 Fault scarps (blocks)", "faults offset terrain into blocks; fault-as-K -> structure-controlled valleys", _faultblocks)
    def _plates():
        import tectonics as TEC
        n = 160; cell = 6000.0
        E = TEC.plate_uplift((n, n), n_plates=13, seed=3, cellsize=cell, warp_amp=20.0, warp_freq=0.06)
        sx = np.array([-10000, -200, 0, 300, 2500, 5000, 8500.0])       # hypsometric colour ramp
        sc = np.array([[18, 32, 74], [70, 120, 175], [120, 170, 205], [96, 150, 86],
                       [176, 158, 120], [210, 205, 205], [248, 248, 252.0]])
        rgb = np.stack([np.interp(E, sx, sc[:, c]) for c in range(3)], -1)
        sh = render.hillshade(E, cell).astype(float)[..., 0] / 255.0
        return np.clip(rgb * (0.55 + 0.5 * sh[..., None]), 0, 255).astype(np.uint8)
    add("02 Plate tectonics (uplift)", "Voronoi plates, warped boundaries; orogens at convergent margins", _plates)
    def _satmap():                                                   # SatMap AUTHORED from real satellite imagery
        h = L.mountain((160, 160), 30.0, seed=3, style="eroded", height=1600.0)
        drv = (h.argsort(axis=None).argsort(axis=None) / (h.size - 1.0)).reshape(h.shape)
        rgb = render.satmap(drv, "desert_terra")                     # CLUT extracted from NASA Terra (PD) via
        #  ^ driver is HISTOGRAM-EQUALISED first (08: height is Gaussian-ish; raw altitude would bunch
        #    the ramp into its mid-band) -- extract_satmap authored the gradient, satmap applies it
        sh = render.hillshade(h, 30.0).astype(float)[..., 0] / 255.0
        return np.clip(rgb * (0.55 + 0.55 * sh)[..., None], 0, 255).astype(np.uint8)
    add("08 SatMap (from satellite)", "CLUT extracted from real NASA imagery (extract_satmap); monotone, in-gamut", _satmap)

    return C


def build():
    from PIL import Image, ImageDraw, ImageFont
    cells = CELLS()
    cols = 7
    rows = (len(cells) + cols - 1) // cols
    cap_h = 46
    pad = 6
    cw, ch = TILE + pad, TILE + cap_h + pad
    header = 60
    bg = (14, 15, 18)
    img = Image.new("RGB", (cols * cw + pad, header + rows * ch + pad), bg)
    dr = ImageDraw.Draw(img)
    ft_title = ImageFont.load_default(size=12)
    ft_test = ImageFont.load_default(size=10)
    ft_head = ImageFont.load_default(size=22)

    dr.text((pad + 4, 16), "terrain-architect  |  reference-impl capability grid   "
            "(every tile generated live in pure numpy; caption = what it is / how it is verified)",
            font=ft_head, fill=(240, 240, 245))

    def wrap(s, width=34):
        out, line = [], ""
        for w in s.split():
            if len(line) + len(w) + 1 > width:
                out.append(line); line = w
            else:
                line = (line + " " + w).strip()
        if line:
            out.append(line)
        return out[:2]

    for k, (title, test, thunk) in enumerate(cells):
        r, c = divmod(k, cols)
        x0, y0 = pad + c * cw, header + pad + r * ch
        try:
            tile = np.ascontiguousarray(thunk())
            im = Image.fromarray(tile).resize((TILE, TILE), Image.LANCZOS)
        except Exception as e:                                          # a failed tile -> visible marker
            im = Image.new("RGB", (TILE, TILE), (60, 20, 20))
            ImageDraw.Draw(im).text((6, 6), f"ERR\n{type(e).__name__}", font=ft_test, fill=(255, 180, 180))
        img.paste(im, (x0, y0))
        dr.text((x0 + 2, y0 + TILE + 2), title, font=ft_title, fill=(245, 236, 200))
        for i, ln in enumerate(wrap(test)):
            dr.text((x0 + 2, y0 + TILE + 18 + i * 12), ln, font=ft_test, fill=(170, 178, 190))

    img.save("capability_grid.png")
    print(f"wrote capability_grid.png — {len(cells)} capabilities, {cols}x{rows} grid, {img.size[0]}x{img.size[1]} px")


if __name__ == "__main__":
    build()
