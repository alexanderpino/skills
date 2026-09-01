"""Invariant checks for the archetype compositions (archetypes.py). Each blueprint in
`references/20-archetypes.md` carries a `09` verification signature; this asserts a robust,
generous version of a representative spread — and, above all, that NO composition blows up (the
guard that caught the thermal-erosion instability the alpine build hit). Integration tests over
already-oracle-verified blocks: they check *signatures*, not exact numbers. Run at low resolution
(the archetype functions are resolution-parametric) so the whole set is fast; the montage uses 96².
"""
import numpy as np

import analysis
import archetypes as A
import flow

N = 56


def _local_minima(h):
    c = h[1:-1, 1:-1]
    mn = np.ones_like(c, dtype=bool)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di or dj:
                mn &= c < h[1 + di:h.shape[0] - 1 + di, 1 + dj:h.shape[1] - 1 + dj]
    return int(mn.sum())


def _hi(h):
    return (h.mean() - h.min()) / max(h.max() - h.min(), 1e-9)


def test_archetypes_all_finite_and_not_blown_up():
    """Every archetype in every group: finite, right shape, bounded relief — the regression guard."""
    for name, group, fn, _ in A.ARCHETYPES:
        h = fn(n=N, cell=A.CELL)
        assert h.shape == (N, N), name
        assert np.all(np.isfinite(h)), name
        assert 0.0 < (h.max() - h.min()) < 5e4, f"{name}: relief {(h.max() - h.min()):.2e} — blown up?"


def test_archetype_signatures():
    b = {name: fn(n=N, cell=A.CELL) for name, _, fn, _ in A.ARCHETYPES}

    # orogen maturity: the old (appalachian) range is gentler than the young (alpine) one
    p99 = lambda h: np.degrees(np.arctan(np.percentile(analysis.slope(h, A.CELL), 99)))
    assert p99(b["appalachian (old)"]) < p99(b["alpine orogen"])

    # canyon / mesa: high ground with a deep cut / a flat cap -> high hypsometric integral
    assert _hi(b["canyon + strata"]) > 0.5

    # erg: aeolian -> low relief, slopes no steeper than the sand regime
    assert (b["erg dune sea"].max() - b["erg dune sea"].min()) < 130.0
    assert p99(b["erg dune sea"]) < 45.0

    # basin & range: mostly low basin floor (low HI) punctuated by ranges
    assert _hi(b["basin & range"]) < 0.45

    # tower karst: dissolution plain with residual towers -> low HI (mostly low ground)
    assert _hi(b["tower karst"]) < 0.35

    # stratovolcano: a single dominant central high -> the max sits near the centre
    vo = b["stratovolcano"]
    pk = np.unravel_index(int(np.argmax(vo)), vo.shape)
    assert abs(pk[0] - N / 2) < N * 0.25 and abs(pk[1] - N / 2) < N * 0.25

    # caldera: an ENCLOSED summit basin holds a lake (priority-flood finds real depth)
    ca = b["caldera lake"]
    assert float((flow.priority_flood_fill(ca) - ca).max()) > 20.0

    # fjord & sea cliffs: the sea (z<0) invades and reaches an edge
    for key in ("fjord coast", "sea cliffs & stacks"):
        below = b[key] < 0.0
        assert below.any() and (below[0].any() or below[-1].any() or below[:, 0].any() or below[:, -1].any()), key

    # lunar cratered: impact-dominated -> a field of pits
    assert _local_minima(b["lunar cratered"]) > 6

    # lunar maria: basaltic flood -> very low relief
    assert (b["lunar maria"].max() - b["lunar maria"].min()) < 120.0


def test_archetypes_deterministic():
    assert np.array_equal(A.cratered(seed=3, n=40), A.cratered(seed=3, n=40))
    assert not np.array_equal(A.cratered(seed=3, n=40), A.cratered(seed=4, n=40))


def test_render_tile_photoreal_composite():
    """Every archetype renders to a valid RGB tile via the shared photoreal path (render.photoreal):
    right shape/dtype, in-range, and not a flat single colour (colour + light actually happened)."""
    for name, group, fn, mode in A.ARCHETYPES:
        h = fn(n=N, cell=A.CELL)
        img = A.render_tile(h, name, mode, cell=A.CELL)
        assert img.shape == (N, N, 3) and img.dtype == np.uint8, name
        assert img.min() >= 0 and img.max() <= 255, name
        assert int(img.reshape(-1, 3).std(axis=0).sum()) > 3, f"{name}: render is a flat colour"


def test_satmap_and_splat_blend():
    """render.satmap is a monotone CLUT hitting its endpoint colours; splat_blend paints a mask's
    colour where the mask is 1 and leaves the base where it is 0."""
    import render
    d = np.linspace(0.0, 1.0, 50)
    rgb = render.satmap(d, "arid")
    assert rgb.shape == (50, 3)
    assert np.allclose(rgb[0], render.SATMAPS["arid"][0][1])          # low end == first stop
    assert np.allclose(rgb[-1], render.SATMAPS["arid"][-1][1])        # high end == last stop
    base = np.zeros((4, 4, 3)) + 10.0
    mask = np.array([[0.0, 1.0, 0.0, 1.0]] * 4)
    out = render.splat_blend(base, [(mask, (200, 100, 50))])
    assert np.allclose(out[mask == 1.0], (200, 100, 50))              # fully painted where mask=1
    assert np.allclose(out[mask == 0.0], 10.0)                        # untouched where mask=0


def test_extract_satmap_authors_a_valid_gradient_from_imagery():
    """render.extract_satmap (the SatMap-AUTHORING step — Gaea's gradients are extracted from
    satellite imagery): stops are luminance-ordered bin means of the SOURCE pixels, so the ramp
    (a) stays inside the source colour gamut, (b) brightens monotonically low->high, and (c) plugs
    straight into render.satmap. Deterministic. The shipped 'desert_terra' entry (from NASA Terra/
    ASTER Rub' al Khali, public domain) must satisfy the same contract."""
    import render
    rng = np.random.default_rng(7)                                    # synthetic "satellite" image:
    yy = np.linspace(0.0, 1.0, 64)[:, None] * np.ones((1, 64))        # dark valley -> bright crest
    img = np.stack([40 + 180 * yy + rng.normal(0, 6, (64, 64)),
                    30 + 150 * yy + rng.normal(0, 6, (64, 64)),
                    20 + 110 * yy + rng.normal(0, 6, (64, 64))], -1).clip(0, 255)
    stops = render.extract_satmap(img, n_stops=10)
    assert len(stops) == 10 and stops[0][0] == 0.0 and stops[-1][0] == 1.0
    pos = np.array([p for p, _ in stops]); cols = np.array([c for _, c in stops])
    assert np.all(np.diff(pos) > 0)                                   # ascending, satmap-ready
    assert cols.min() >= img.min() - 1e-9 and cols.max() <= img.max() + 1e-9   # inside source gamut
    lum = cols @ np.array([0.2126, 0.7152, 0.0722])
    assert np.all(np.diff(lum) > -1e-6) and lum[-1] > lum[0] + 40     # brightens low -> high
    assert render.satmap(np.linspace(0, 1, 9), stops).shape == (9, 3)  # plugs into the CLUT
    again = render.extract_satmap(img, n_stops=10)
    assert stops == again                                             # deterministic
    dt = render.SATMAPS["desert_terra"]                               # the shipped extracted ramp
    dpos = np.array([p for p, _ in dt]); dlum = np.array([c for _, c in dt]) @ np.array([0.2126, 0.7152, 0.0722])
    assert np.all(np.diff(dpos) > 0) and np.all(np.diff(dlum) > 0)


def test_substance_colour_is_material_not_elevation():
    """Colour comes from SUBSTANCES, not a height ramp: varied colour, and snow is placed by physics
    (a white substance) only on cold, holdable ground — never on the steep faces that shed it, and
    never on a warm desert."""
    hh = A.alpine(n=N, cell=A.CELL)
    col, area, surf = A.substance_color(hh, "temperate", A.CELL)
    assert col.shape == (N, N, 3)
    assert int(col.reshape(-1, 3).std(axis=0).sum()) > 12             # real material variation
    # substances PILE UP: the deposit surface only ever rises above bedrock, and it fills crevices
    assert np.all(surf >= hh - 1e-6)
    assert surf.max() > hh.max() - 1e-6 and np.any(surf > hh + 1e-6)  # something actually accumulated
    fill = A.analysis.deposit_fill(hh, radius=3)
    assert fill.min() >= -1e-9 and fill.max() > 0.0                   # fill is >=0, positive in hollows

    # snow (substance) placement: present on the alpine world, absent on the arid desert
    h = A.alpine(n=N, cell=A.CELL)
    slope = analysis.slope(h, A.CELL)
    area = flow.d8_accumulation(flow.priority_flood_fill(h), A.CELL)
    snow = dict(analysis.derive_substances(h, slope, area, A.CELL,
                                           climate=A.BIOME["temperate"]["climate"]))["snow"]
    assert snow.max() > 0.2                                           # snow accumulates somewhere high
    steep = slope > np.tan(np.radians(60))
    if steep.any():
        assert snow[steep].max() < 0.2                               # but not on the faces that shed it
    desert_snow = dict(analysis.derive_substances(A.mesa(n=N, cell=A.CELL),
                       analysis.slope(A.mesa(n=N, cell=A.CELL), A.CELL),
                       flow.d8_accumulation(flow.priority_flood_fill(A.mesa(n=N, cell=A.CELL)), A.CELL),
                       A.CELL, climate=A.BIOME["arid"]["climate"]))["snow"]
    assert desert_snow.max() < 1e-9                                  # no snow in a warm desert


def test_photoreal_two_light_floor_and_ao():
    """render.sun_sky_shade never crushes to black (sky floor) and stays <=1; AO only darkens."""
    import render
    h = A.alpine(n=N, cell=A.CELL)
    shade = render.sun_sky_shade(h, A.CELL, sky=0.3)
    assert shade.min() >= 0.3 - 1e-9 and shade.max() <= 1.0 + 1e-9
    flat = np.zeros((N, N, 3)) + 200.0
    occ = np.ones((N, N))                                  # fully occluded -> strictly darker
    lit = render.photoreal(flat, h, A.CELL, ao=occ, ao_strength=0.4, aerial_strength=0.0)
    assert lit.max() <= 200


# =========================================================================================== #
# The `09` signature bands, AT THE FIGURE'S OWN TILE SIZE
#
# WHAT WENT WRONG. `_signature()` computed relief, 99th-percentile slope, hypsometric integral
# and pit-storage for every archetype and `main()` only PRINTED them. Nothing returned or
# asserted them, so `archetypes.png`'s numbers were guarded by exactly one thing: the pixel-exact
# rebuild in `tools/regen_figures.py`. That gate is unsound across machines -- two CI runs with
# identical numpy 2.4.6 / pillow 12.3.0 / CPython 3.11 produced different montages -- and
# `canyon + strata` pit-storage moved 5.22e+06 -> 4.16e+06 m3 (-20%) with every assertion in this
# file green. The tests below also ran at N=56 while the montage renders at TILE=96, and droplet
# counts scale with `n`, so they were not even exercising the same erosion run.
#
# THE MECHANISM, REPRODUCED ON ONE MACHINE (not inferred). numpy dispatches its transcendental
# ufunc loops on the CPU's SIMD level at import time, and the loops are not bit-identical.
# Measured here with `NPY_DISABLE_CPU_FEATURES` over 10007 doubles in [0,1]:
#     pow(x,1.4) exp log1p tan arctan ... differ, max relative 2.22e-16 (exactly 1 ULP)
#     add mul sqrt sin hypot sum mean ... bit-identical
# Running this repo with AVX512 enabled vs disabled reproduces BOTH published CI runs exactly:
#     canyon relief   268.99 (AVX512) / 270.71 (AVX2)   <- CI reported 269 / 271
#     canyon pit    5.2169e6         / 4.1597e6         <- CI reported 5.22e6 / 4.16e6
#     badlands relief 260.52         / 258.63           <- CI reported 261 / 259
#     badlands p99     35.278        /  35.236          <- CI reported 35.3 / 35.2
# For `canyon` the divergence enters at `archetypes.py:83`, the `** 1.4` on the trunk profile:
# one ULP there, then `erosion_droplet.droplet_erode` amplifies it by ~1e14 because a droplet's
# steepest-descent step is a DISCRETE choice and a tie flips.
#
# HOW EACH BAND WAS DERIVED -- from measurement, and never widened to make a run pass.
#   1. The perturbation is known and bounded: +-1 ULP on any transcendental result.
#   2. So it was SAMPLED. Two Monte-Carlo passes at n=96 nudged every intercepted array by a
#      random -1/0/+1 ULP -- pass 1 (24 trials) at the droplet-erosion input, pass 2 (20 trials)
#      at the droplet input AND every `noise.fbm/perlin/ridged_mf/worley` result. 44 samples per
#      quantity, plus the two real SIMD regimes = 46.
#   3. VALIDATION that the model is the right one: the 46-sample envelope contains both real
#      regime values for all 96 quantities. Pass 1 alone did not -- a real regime value fell
#      outside the 24-sample envelope by at most 1.9351% of the value (Monument Valley HI).
#   4. band = [min(samples) * (1 - 0.02), max(samples) * (1 + 0.02)], rounded OUTWARD to 4
#      significant figures. The 2% margin is that measured 1.9351% residual under-coverage
#      rounded up -- it is the largest amount by which an independently-produced sample has been
#      observed to escape an envelope of this kind here, not a guess.
#   The measured envelope is recorded beside every row so the derivation is auditable, and so a
#   later widening has to argue with a number.
#
# ⚠️ WHAT THESE BANDS DO **NOT** CATCH -- stated plainly, because a band that the observed drift
# would pass is not a guard against that drift. A guard must be green on BOTH runners, so it
# cannot separate them: NONE of the 18 quantity-slots that actually differ between the two
# dispatch regimes is caught by its own band, by construction.
#     canyon pit-storage   drift 22.5%   band +-33.5%   NOT caught
#     canyon relief        drift 0.64%   band +- 4.1%   NOT caught
#     badlands pit         drift  5.2%   band +-17.1%   NOT caught
#     badlands relief      drift 0.73%   band +- 4.5%   NOT caught
# That is a finding about this figure, not a defect in the derivation: for these tiles the
# cross-machine spread IS the noise floor, and pit-storage on a droplet-eroded tile cannot be
# guarded tightly at all -- `canyon`'s band admits a 2.0x change and `Beggar's Canyon`'s a 3.6x
# one. What the bands do buy is the other 71 of 96 slots, where the envelope is ~1e-13% (no
# chaotic amplifier in the tile) and the band closes to +-2%: those catch any change above 2%,
# against `relief > 120` / `HI > 0.5` / `relief < 130` today.
#
# Rows are (relief_m, p99_slope_deg, hypsometric_integral, pit_storage_m3), each a (lo, hi).
# =========================================================================================== #
N_FIG = A.TILE                       # 96 -- the montage's own tile size, not a cheaper stand-in

BANDS = {
    "alpine orogen":         ((668.9, 711.7), (69.57, 72.68), (0.4574, 0.4869), (3.248e+07, 3.699e+07)),
    #   1-ULP envelope, % of value:    2.179   0.3525    2.224    8.956
    "appalachian (old)":     ((493.9, 532.3), (49.75, 52.84), (0.4425, 0.4816), (1.952e+07, 2.555e+07)),
    #   1-ULP envelope, % of value:    3.475    2.019    4.449    22.78
    "canyon + strata":       ((262.1, 284.2), (71.21, 74.73), (0.7297, 0.7681), (2.794e+06, 5.612e+06)),
    #   1-ULP envelope, % of value:    4.079   0.8078    1.119    63.45
    "mesa / tepui":          ((345.6, 359.8), (75.99, 79.1), (0.3018, 0.3142), (6358, 6618)),
    #   1-ULP envelope, % of value:        0        0 1.802e-14 3.589e-12
    "erg dune sea":          ((17.34, 18.06), (17.43, 18.15), (0.3982, 0.4145), (6.149e+05, 6.401e+05)),
    #   1-ULP envelope, % of value: 1.004e-13 3.993e-14 1.23e-13 1.113e-13
    "basin & range":         ((351.4, 365.9), (70.43, 73.32), (0.2782, 0.2896), (3.431e+05, 3.572e+05)),
    #   1-ULP envelope, % of value: 3.17e-14        0 9.777e-14 7.149e-13
    "badlands":              ((253.4, 277.2), (34.28, 37.12), (0.4761, 0.5208), (5.08e+05, 7.175e+05)),
    #   1-ULP envelope, % of value:    4.924    3.945     4.96    30.28
    "tower karst":           ((263.5, 274.3), (77.54, 80.71), (0.0733, 0.0763), (5311, 5528)),
    #   1-ULP envelope, % of value:        0 1.796e-14 2.412e-13 5.37e-13
    "stratovolcano":         ((846.6, 1012), (78.82, 82.65), (0.2672, 0.3734), (1.62e+06, 2.017e+06)),
    #   1-ULP envelope, % of value:    13.76   0.7402    29.21    17.83
    "caldera lake":          ((496, 516.3), (56.47, 58.78), (0.3638, 0.3788), (4.492e+06, 4.677e+06)),
    #   1-ULP envelope, % of value: 1.123e-14 1.233e-14 2.99e-14 1.016e-13
    "fjord coast":           ((1499, 1561), (81.04, 84.36), (0.5926, 0.6169), (8.397e+07, 8.741e+07)),
    #   1-ULP envelope, % of value: 5.943e-14 1.718e-14 3.672e-14 1.739e-13
    "sea cliffs & stacks":   ((388.5, 404.5), (36.83, 38.34), (0.4924, 0.5126), (5.043e+06, 5.25e+06)),
    #   1-ULP envelope, % of value: 4.301e-14 1.89e-14 2.209e-14 2.171e-13
    "ag terraces":           ((176.1, 183.3), (32.22, 33.54), (0.4885, 0.5086), (3.462e+06, 3.604e+06)),
    #   1-ULP envelope, % of value:        0        0 5.567e-14 5.009e-13
    "lunar cratered":        ((310.9, 323.7), (54.78, 57.03), (0.5433, 0.5656), (1.243e+07, 1.295e+07)),
    #   1-ULP envelope, % of value: 3.583e-14 3.813e-14 4.005e-14 1.174e-13
    "lunar maria":           ((46.5, 48.41), (9.675, 10.08), (0.4109, 0.4278), (1.102e+06, 1.148e+06)),
    #   1-ULP envelope, % of value: 2.995e-14 1.619e-13 2.648e-14 1.862e-13
    "mars relict":           ((240.5, 250.5), (54.18, 56.4), (0.5881, 0.6122), (9.647e+06, 1.005e+07)),
    #   1-ULP envelope, % of value: 2.315e-14 6.425e-14 1.85e-14 1.514e-13
}

_SIG_CACHE = {}


def _sig():
    """`A.signatures(n=96)` once per module: ~8.6 s, and four tests want it."""
    if not _SIG_CACHE:
        _SIG_CACHE.update(A.signatures(n=N_FIG, cell=A.CELL))
    return _SIG_CACHE


def test_signature_returns_the_facts_it_computes():
    """`_signature` must hand back the four `09` numbers AS DATA. It used to return a formatted
    string, which is why a 20% pit-storage move could happen with the suite green: a number that
    is only printed is asserted by nothing."""
    h = A.mesa(n=48, cell=A.CELL)
    f = A._signature("mesa / tepui", "C", h, A.CELL)
    assert isinstance(f, dict), "_signature returned a string again -- the facts are unassertable"
    for key in ("relief_m", "p99_slope_deg", "hypsometric_integral", "pit_storage_m3"):
        assert key in f and isinstance(f[key], float) and np.isfinite(f[key]), key
    assert f["relief_m"] == float(h.max() - h.min())
    assert A._signature_line(f).strip().startswith("[C] mesa / tepui")     # printing still works


def test_signature_bands_cover_every_archetype():
    """The denominator. A band table that silently omits an archetype is a guard whose scan domain
    is a hand-written list -- exactly the hole this repo has been closing. 16 archetypes, 16 rows,
    no extras, and every row four (lo, hi) pairs with lo < hi."""
    names = [name for name, _, _, _ in A.ARCHETYPES]
    assert sorted(BANDS) == sorted(names), (
        f"unbanded: {sorted(set(names) - set(BANDS))}; stale: {sorted(set(BANDS) - set(names))}")
    for name, row in BANDS.items():
        assert len(row) == 4, name
        for lo, hi in row:
            assert lo < hi, name


def test_signatures_defaults_to_the_figure_tile_size():
    """`A.signatures()` must default to the size the montage renders at. Droplet counts are
    `k * n`, so a signature at 56 is a different erosion run from the one in `archetypes.png`;
    that mismatch is why the old N=56 guards could not have seen the drift at all."""
    assert N_FIG == A.TILE == 96
    assert A.signatures.__defaults__[0] == A.TILE


def test_archetype_signatures_within_measured_bands_at_figure_resolution():
    """Every archetype's four `09` numbers, at TILE=96, inside a band derived from the measured
    +-1 ULP envelope (see the header). This is what replaces the pixel-exact rebuild."""
    sig = _sig()
    keys = ("relief_m", "p99_slope_deg", "hypsometric_integral", "pit_storage_m3")
    for name, row in BANDS.items():
        f = sig[name]
        for (lo, hi), key in zip(row, keys):
            v = f[key]
            assert lo <= v <= hi, (
                f"{name}: {key} = {v:.6g} is outside its measured band [{lo:.6g}, {hi:.6g}] "
                f"({(v - (lo + hi) / 2) / ((lo + hi) / 2) * 100:+.2f}% from band centre)")
