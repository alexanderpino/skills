"""Oracles for the geological landforms (11-geological.md). Craters hit Pike/Melosh numbers
(depth/D, rim, r^-3 ejecta, a central peak when complex, and the gravity pi-scaling); strata
is a periodic material coordinate; terracing quantises to flat treads; folding is a sinusoid;
karst carves pits only on soluble rock and marks them do-not-fill.

The last section guards something different in kind: the MONTAGE `landforms.main()` composes out of
these primitives, including the droplet+thermal panel that no primitive test reaches. See the
section comment there.
"""
import functools

import numpy as np
import asserts
import inputs
import landforms as L


def test_crater_diameter_scales_inversely_with_gravity():
    """Melosh pi-scaling: the same energy digs a BIGGER crater at lower gravity (Moon > Earth)."""
    e = 1e12
    assert L.crater_diameter(e, g=1.62) > L.crater_diameter(e, g=9.81)
    assert L.crater_diameter(2 * e, g=9.81) > L.crater_diameter(e, g=9.81)   # more energy, bigger


def test_simple_crater_morphology():
    """Bowl depth ~ D/5, a rim raised above the surroundings, no central peak."""
    h = inputs.flat(81)
    D = 40.0
    c = L.impact_crater(h, 40, 40, D, cellsize=1.0, complex_D=1e9)
    assert abs(-c.min() / D - 0.2) < 0.03                  # depth/diameter ~ 0.2
    assert c[40, 40] == c.min()                            # centre is the deepest (no peak)
    rim = c[40, 58:63].max()                               # near r = R = 20
    assert rim > 0.03 * D                                  # raised rim


def test_crater_ejecta_thins_as_r_cubed():
    h = inputs.flat(101)
    D, R = 40.0, 20.0
    c = L.impact_crater(h, 50, 50, D, cellsize=1.0, complex_D=1e9)
    col = np.arange(78, 90)                                # r in (1.4R, 2R), past the rim ring
    r = col - 50.0
    ej = c[50, col]
    assert np.all(ej > 0)
    slope = np.polyfit(np.log(r), np.log(ej), 1)[0]
    assert abs(slope + 3.0) < 0.3                          # ejecta ~ r^-3


def test_complex_crater_has_central_peak():
    h = inputs.flat(81)
    c = L.impact_crater(h, 40, 40, D=40.0, cellsize=1.0, complex_D=10.0)   # force complex
    assert c[40, 40] > c[40, 50]                           # rebound peak stands above the floor


def test_terrace_snaps_to_flat_treads():
    ramp = (np.linspace(0.0, 1.0, 200)[None, :] * np.ones((4, 1)))
    levels = 5
    t = L.terrace(ramp, levels=levels, sharpness=8.0)
    row = t[0]
    assert np.all(np.diff(row) >= -1e-9)                   # monotonic
    assert t.min() >= -1e-9 and t.max() <= 1.0 + 1e-9
    nearest = np.round(row * levels) / levels              # the discrete tread values
    assert np.mean(np.abs(row - nearest) < 0.02) > 0.6     # most cells sit on a tread


def test_fault_block_butte_flat_top_cliff_and_talus():
    n, cell, bh = 80, 10.0, 300.0
    b = L.fault_block_butte((n, n), n / 2, n / 2, 0.22 * n, bh, cell, seed=1, fault=0.0)
    assert b.shape == (n, n) and np.all(np.isfinite(b))
    c = n // 2
    assert abs(b[c, c] - bh) < 0.06 * bh                   # flat structural top near full height at the centre
    assert b.min() >= 0.0 and b.max() <= bh * 1.1          # height-above-plain, capped near bh
    # a horizontal profile through the centre: flat top -> steep cliff -> gentler talus -> plain
    row = b[c]
    top = row >= 0.94 * bh
    apron = (row > 0.02 * bh) & (row < 0.35 * bh)          # the talus band exists (break of slope)
    assert top.any() and apron.any()
    # the footprint is joint-bounded (a straight edge), so the top is a compact block, not a disc
    assert top.sum() < 0.5 * n                             # a bounded tableland, not filling the row


def test_fault_block_butte_is_deterministic():
    a = L.fault_block_butte((48, 48), 24, 24, 10.0, 200.0, 10.0, seed=5, fault=0.3)
    b = L.fault_block_butte((48, 48), 24, 24, 10.0, 200.0, 10.0, seed=5, fault=0.3)
    assert np.array_equal(a, b)


def test_mountain_primitive_is_a_dissected_massif():
    h = L.mountain((80, 80), 30.0, seed=1, n_ridges=3, height=1600.0)
    assert h.shape == (80, 80) and np.all(np.isfinite(h))
    assert 800.0 < np.ptp(h) < 4000.0                                    # relief near the requested height
    assert h.max() > h.mean() + 0.25 * np.ptp(h)                         # a real high massif, not flat noise
    margin = np.concatenate([h[0], h[-1], h[:, 0], h[:, -1]]).mean()     # a defined envelope: crest high, edges low
    assert margin < h.mean()


def test_mountain_is_organized_not_isotropic_noise():
    """The Voronoi ridge network + baked drainage must dissect the massif into VALLEYS well below the
    local crest — the structure that reads as an eroded mountain, not noise on a lump. We check the
    interior carries deep incision: a healthy spread of local relief inside the massif footprint."""
    h = L.mountain((96, 96), 30.0, seed=4, height=1700.0, style="eroded")
    core = h[24:72, 24:72]                                               # inside the footprint (skip low margins)
    # drainage incision: the interior spans a large fraction of the peak (deep valleys next to high spurs)
    assert np.ptp(core) > 0.4 * h.max()


def _rotational_correlation(f, degs=(30, 60, 90, 120, 150)):
    """Correlate the field with itself rotated about its own summit. A SOLID OF REVOLUTION —
    a cone, a bell, a tent — is invariant under that rotation and scores ~1.0. Nearest-neighbour
    sampling, applied identically to the field and the controls."""
    n = f.shape[0]
    bi = int(np.argmax(f))
    by, bx = bi // n, bi % n
    ii, jj = np.mgrid[0:n, 0:n]
    dy, dx = ii - by, jj - bx
    keep = np.hypot(dy, dx) < 0.45 * n
    out = []
    for d in degs:
        a = np.deg2rad(d)
        sy = np.rint(by + dy * np.cos(a) - dx * np.sin(a)).astype(int)
        sx = np.rint(bx + dy * np.sin(a) + dx * np.cos(a)).astype(int)
        ok = keep & (sy >= 0) & (sy < n) & (sx >= 0) & (sx < n)
        a1, a2 = f[ii[ok], jj[ok]], f[sy[ok], sx[ok]]
        out.append(1.0 if a1.std() < 1e-12 or a2.std() < 1e-12
                   else float(np.corrcoef(a1, a2)[0, 1]))
    return float(np.mean(out))


def _radial_residual(f):
    """Fraction of the field's variance a best-fit RADIAL PROFILE about the summit cannot
    explain. A cone ~0.02 (a radial profile IS the cone); pure noise ~0.97."""
    n = f.shape[0]
    bi = int(np.argmax(f))
    by, bx = bi // n, bi % n
    ii, jj = np.mgrid[0:n, 0:n]
    r = np.hypot(ii - by, jj - bx)
    nb = 48
    b = np.clip((r / (0.5 * n) * nb).astype(int), 0, nb - 1)
    prof = np.array([f[b == k].mean() if (b == k).any() else 0.0 for k in range(nb)])
    return float((f - prof[b]).std() / (f.std() + 1e-12))


def test_mountain_is_not_a_solid_of_revolution():
    """The failure mode this pins is a cone with grooves cut in it — the "tipi tent". It is worth
    a dedicated test because the OTHER mountain assertions above (relief in range, summit above
    the mean, margins below the mean, deep interior incision) are ALL satisfied by a smooth cone,
    so they cannot catch it. The controls are asserted too: if the metric ever stops separating a
    cone from noise, this test fails on the control rather than passing vacuously.

    What keeps `mountain` off the cone is that its envelope is a wandering crest-line POLYLINE
    SDF, not a radial falloff. If anyone ever "simplifies" that to `(1-r)**k`, this test is what
    should stop them. Measured at n=192: rotational correlation 0.073-0.337 across the five
    styles (cone 1.000, noise 0.092); radial residual 0.79-0.91 (cone 0.022, noise 0.965)."""
    n = 96
    ii, jj = np.mgrid[0:n, 0:n]
    cone = np.maximum(0.0, 1.0 - np.hypot(ii - n / 2, jj - n / 2) / (0.45 * n))
    rng = np.random.default_rng(0)
    pure = rng.normal(size=(n, n))

    assert _rotational_correlation(cone) > 0.95, "control broken: a cone must read as revolved"
    assert _radial_residual(cone) < 0.15, "control broken: a radial profile must explain a cone"
    assert _rotational_correlation(pure) < 0.30, "control broken: noise must not read as revolved"

    for style in ("basic", "eroded", "alpine", "old", "strata"):
        h = L.mountain((n, n), 30.0, seed=7, n_ridges=3, style=style)
        rc, rr = _rotational_correlation(h), _radial_residual(h)
        assert rc < 0.60, f"{style}: rotationally symmetric (corr {rc:.3f}) — it is a cone"
        assert rr > 0.55, f"{style}: a radial profile explains it (residual {rr:.3f}) — it is a cone"


def test_mountain_styles_are_distinct():
    """Gaea's presets are genuinely different landforms: 'old' is subdued/rounded (less rough) than the
    sharp 'alpine', and every style is a distinct field."""
    fields = {s: L.mountain((72, 72), 30.0, seed=5, height=1600.0, style=s)
              for s in ("basic", "eroded", "alpine", "old", "strata")}
    for a in fields:                                                     # all five styles differ
        for b in fields:
            if a < b:
                assert not np.array_equal(fields[a], fields[b])
    rough = lambda f: np.mean(np.abs(np.diff(f, axis=0))) + np.mean(np.abs(np.diff(f, axis=1)))
    assert rough(fields["old"]) < rough(fields["alpine"])               # 'old' is smoother than 'alpine'


def test_mountain_deterministic():
    assert np.array_equal(L.mountain((40, 40), 30.0, seed=2), L.mountain((40, 40), 30.0, seed=2))
    assert not np.array_equal(L.mountain((40, 40), 30.0, seed=2), L.mountain((40, 40), 30.0, seed=3))


def test_ridge_is_a_linear_asymmetric_crest():
    """The Ridge node (hogback): a real crest with ASYMMETRIC flanks — a steep scarp and a gentle dip
    slope. The asymmetry shows as a markedly steeper max slope on the scarp side than a symmetric arête."""
    import analysis
    h = L.ridge((90, 90), 30.0, seed=2, height=900.0, asymmetry=0.6)
    assert np.all(np.isfinite(h)) and 400.0 < np.ptp(h) < 1600.0
    assert h.max() > h.mean() + 0.30 * np.ptp(h)                          # a real crest, not flat noise
    ms = lambda a: analysis.slope(L.ridge((90, 90), 30.0, seed=2, height=900.0,
                                          asymmetry=a, angle=1.4), 30.0).max()
    assert ms(0.6) > 1.3 * ms(0.0)                                        # steep scarp >> symmetric flanks


def test_ridge_crest_is_rounded_not_a_razor_cut():
    """The crest is a smooth-min blend (Quilez smin), NOT a hard mathematical plane-cut: more crest
    rounding lowers the peak slope. (This is the fix for the razor-crest failure.)"""
    import analysis
    ms = lambda cr: analysis.slope(L.ridge((90, 90), 30.0, seed=2, height=900.0, angle=1.4,
                                           detail=0.0, crest_round=cr), 30.0).max()
    assert ms(0.30) < ms(0.02)                                            # rounder crest -> gentler peak


def test_volcano_has_summit_crater_and_concave_cone():
    """The Volcano node: a radial edifice, a summit crater depression, and (strato) a steeper summit
    than the shield type."""
    n, cell = 120, 30.0
    c = n // 2
    strato = L.volcano((n, n), c, c, radius=n * 0.42 * cell, height=1600.0, cellsize=cell, seed=1, kind="strato")
    shield = L.volcano((n, n), c, c, radius=n * 0.42 * cell, height=1600.0, cellsize=cell, seed=1, kind="shield")
    R = n * 0.42
    summit = strato[c, c:c + int(0.3 * n)]                                # radial profile out from the centre
    assert strato[c, c] < summit.max()                                   # crater floor sits below the crater rim
    assert strato.min() >= 0.0                                            # height-above-base
    # strato must be CONCAVE-UP: the edifice flank (crater excluded) is STEEPEST near the summit and
    # flares to a gentle base. Measured along +x, outside the crater. (Exponent<1 would invert this — the
    # bug the audit caught; a summit-vs-shield check alone did NOT test concavity.)
    prof = strato[c, c:]
    slope = np.abs(np.diff(prof))
    r = np.arange(len(slope))
    upper = slope[(r > 0.28 * R) & (r < 0.5 * R)].mean()                  # upper flank, above the crater
    lower = slope[(r > 0.6 * R) & (r < 0.85 * R)].mean()                  # lower flank / apron
    assert upper > lower                                                  # summit-steepest == concave-up


def test_canyon_incises_a_plateau():
    """The Canyon node: a high plateau cut by a deep gorge — most of the field near the rim, a thin
    deep floor far below."""
    h = L.canyon((120, 120), 30.0, seed=3, rim=1000.0, depth=750.0)
    assert np.all(np.isfinite(h))
    hi, lo = np.percentile(h, 90), np.percentile(h, 2)
    assert hi - lo > 500.0                                                # a real gorge, not a dimple
    assert np.median(h) > 1000.0 - 0.2 * 750.0                            # plateau dominates; the gorge is a minority
    assert np.mean(h < 1000.0 - 0.5 * 750.0) > 0.02                       # but a genuine deep floor exists
    assert np.array_equal(L.canyon((40, 40), 30.0, seed=3), L.canyon((40, 40), 30.0, seed=3))  # deterministic


def test_strat_coord_horizontal_tilt_and_fold():
    h = inputs.cone(32, height=5.0)
    yy, xx = np.mgrid[0:32, 0:32].astype(float)
    assert np.allclose(L.strat_coord(h, xx, yy), h)                       # horizontal beds
    assert np.allclose(L.strat_coord(h, xx, yy, tilt=(0.5, 0.0)) - h, 0.5 * xx)
    folded = L.strat_coord(h, xx, yy, fold_amp=2.0, fold_dir=(1.0, 0.0), fold_freq=0.1) - h
    assert np.allclose(folded, 2.0 * np.sin(0.1 * xx))


def test_bed_erodibility_is_periodic():
    strat = np.linspace(0.0, 30.0, 300)
    table = [(2.0, 1.0), (3.0, 0.2)]                       # period = 5
    k = L.bed_erodibility(strat, table)
    k_shift = L.bed_erodibility(strat + 5.0, table)
    assert np.allclose(k, k_shift)
    assert set(np.unique(k)) <= {1.0, 0.2}


def test_fold_is_a_sinusoid():
    yy, xx = np.mgrid[0:20, 0:40].astype(float)
    f = L.fold(0.0, xx, yy, amp=3.0, direction=(1.0, 0.0), freq=0.2)
    assert np.allclose(f, 3.0 * np.sin(0.2 * xx))


def test_karst_carves_pits_only_on_soluble_rock():
    """The depression-handling exception (03): sinkholes only where soluble, marked do-not-fill."""
    h = inputs.flat(64)
    soluble = np.zeros((64, 64))
    soluble[:, :32] = 1.0                                  # left half soluble
    hk, sink = L.karst_sinkholes(h, soluble, cellsize=1.0, spacing=8.0, depth=5.0,
                                 radius=3.0, seed=0)
    assert hk.min() < 0.0                                  # some doline carved
    assert np.all(hk[:, 40:] == 0.0)                       # dry (insoluble) half untouched
    assert not np.any(sink[:, 40:]) and np.any(sink[:, :32])


def test_karst_size_var_gives_a_doline_size_distribution():
    """size_var makes the dolines lognormal in size (Williams 1972), not one radius: the per-pit
    depths spread out, deeper pits appear, and the soluble-only contract still holds."""
    h = inputs.flat(96)
    soluble = np.zeros((96, 96)); soluble[:, :64] = 1.0
    uni = L.karst_sinkholes(h, soluble, cellsize=1.0, spacing=11.0, depth=5.0, radius=3.0, seed=0)[0]
    var = L.karst_sinkholes(h, soluble, cellsize=1.0, spacing=11.0, depth=5.0, radius=3.0, seed=0,
                            size_var=0.7)[0]
    assert np.all(var[:, 70:] == 0.0)                      # still carves only on soluble rock
    # varied field has a wider spread of pit depths AND digs deeper than the single-radius field
    assert var.min() < uni.min() - 1e-6                    # a lognormal tail -> some doline deeper than uniform
    assert var[var < 0].std() > uni[uni < 0].std()         # depths are genuinely distributed, not one value


# --------------------------------------------------------------------------------------------
# THE MONTAGE `landforms.main()` ACTUALLY DRAWS.
#
# Everything above tests a PRIMITIVE in isolation. The figure is a composition of nine panels at
# n=200 / cell=26 m, and one of them — the bottom-left "REAL hydraulic+thermal pass", i.e.
# `erosion_thermal.thermal_erosion(erosion_droplet.droplet_erode(mountain(...)))` — was touched by
# no test at any resolution. `landforms` is also the figure that drifted furthest in CI (145 469 px
# between two runs on identical dependency versions), and `tools/regen_figures.py` now gates it on
# "tests/test_landforms.py" instead of on pixels, so those invariants have to be here.
#
# WHAT IS GUARDED AND WHAT IS NOT. Every assertion below is a conservation law, a sign, an ordering
# or an exact geometric identity, because those are the only things that survive numpy dispatching
# a different SIMD kernel on a different CPU. Nothing pins a relief, a roughness or a pixel value
# to a remembered number: those are precisely the quantities that moved between the two CI runs.
#
# COST AND RESOLUTION. The shipped montage is n=200 (the droplet solver alone is ~12 s there,
# because `n_droplets = 55*n`). These guards build the SAME composition ONCE at n=64 with the cell
# size scaled so the PHYSICAL EXTENT is unchanged (64 x 81.25 m == 200 x 26 m == 5.2 km), which
# keeps `thermal_erosion`'s `repose_slope * cellsize` talus threshold and `volcano`'s
# `radius = n*0.42*cell` in the metres the figure gives them. Measured at n = 48, 56, 64, 72, 96
# and the shipped 200, every ordering asserted below holds at every one of them, and the
# conservation law closes to <= 3.4e-16 relative at all six. The one place the reduction is
# GENEROUS rather than conservative is the "thermal relaxes below the input" ordering, whose margin
# is widest at small n (roughness 131.9 -> 77.7 at n=64) and narrowest at the shipped n=200
# (43.30 -> 39.82, an 8% margin); it still holds there, and it is recorded here so nobody has to
# rediscover that the guard's headroom is not the figure's.
_MONTAGE_N = 64
_MONTAGE_CELL = 200 * 26.0 / _MONTAGE_N            # same 5.2 km extent as the shipped figure


@functools.lru_cache(maxsize=1)
def _montage():
    """The figure's composition, built once and shared by every guard in this section."""
    return L._montage(n=_MONTAGE_N, cell=_MONTAGE_CELL)


def test_the_montage_erosion_panel_conserves_volume():
    """THE CONSERVATION LAW OF THE UNGUARDED PANEL. `erosion_droplet.droplet_erode` promises "total
    volume is conserved (leftover sediment is deposited at end of life)" and
    `erosion_thermal.thermal_erosion` promises "mass conserved exactly". Composed, they must still
    close — and composing them is exactly where the promise can be lost, because the droplet pass
    hands the thermal pass a field it never validated.

    This is the check the primitives' own suites cannot make: `tests/test_droplet.py` and
    `tests/test_thermal.py` each run their solver on their own input, so a droplet pass that
    leaked its sediment payload off the grid edge only where the *mountain* primitive puts steep
    ground would pass both and fail here. Volume is stated in m3 (`sum(h) * cell**2`), the unit the
    law holds in.

    NOTE the failure mode this is aimed at is a LEAK, not a blow-up: `thermal_erosion`'s own
    docstring records that a diverging field "stays mass conserved, so the explosion hides from a
    mass test". That is why the relief and roughness orderings in the next test exist alongside
    this one; neither check subsumes the other.

    TOLERANCE, DERIVED. Measured |V_out - V_in| / V_in at n = 48, 56, 64, 72, 96, 200: 0.0, 1.68e-16,
    1.68e-16, 3.36e-16, 1.68e-16, 0.0 — worst 3.4e-16, i.e. one or two float64 ulps on a sum of
    n**2 heights, which is the floor and not a measurement of the solvers. 1e-9 sits ~6.5 decades
    above that floor (headroom for a machine that associates the reduction differently) and orders
    of magnitude below any real leak: a single droplet abandoning its full sediment load is O(1e-6)
    of the total, and an edge policy that dropped payloads systematically is O(1e-2).
    """
    _image, facts = _montage()
    e = facts["erosion"]
    asserts.assert_mass_conserved(e["volume_in_m3"], e["volume_hydraulic_m3"], tol=1e-9,
                                  msg="montage erosion panel: droplet pass")
    asserts.assert_mass_conserved(e["volume_hydraulic_m3"], e["volume_out_m3"], tol=1e-9,
                                  msg="montage erosion panel: thermal pass")
    asserts.assert_mass_conserved(e["volume_in_m3"], e["volume_out_m3"], tol=1e-9,
                                  msg="montage erosion panel: droplet + thermal composed")


def test_the_montage_erosion_panel_incises_then_relaxes():
    """WHAT THE CAPTION CLAIMS THE PANEL IS: "Mountain(basic) then a REAL hydraulic+thermal pass".
    Mass conservation alone cannot tell that panel from the uneroded Mountain beside it — an
    erosion stage wired to a no-op conserves mass perfectly. These are the orderings that say the
    two passes did their opposite jobs, and none of them needs a tolerance:

      * the HYDRAULIC pass INCISES, so it leaves the field rougher than it found it (droplets cut
        channels; roughness 131.9 -> 167.8 at n=64, and 43.3 -> 98.8 at the shipped n=200 — the
        margin grows with resolution, so the guard runs at the harder end);
      * the THERMAL pass then RELAXES the over-steepened result past where it started, which is
        what a talus angle does (167.8 -> 77.7 at n=64; 98.8 -> 39.8 at n=200, still below the
        input's 43.3);
      * eroded relief is LOWER than uneroded relief — the plainest statement of "this panel has
        been eroded" (2317 -> 1717 m at n=64; 2384 -> 2227 m at n=200).

    Reversing the composition order, dropping either stage, or setting `factor`/`iters` to a no-op
    breaks at least one of the three. A change of SIMD kernel breaks none of them: each is a
    comparison between two numbers computed on the same machine in the same run.

    ⚠️ WHAT THESE THREE DO NOT CATCH, said out loud rather than papered over with a band. A SCALE
    SLIP in the montage's thermal call — `thermal_erosion(hd, 0.7, 14, cell, ...)` losing its `cell`
    argument and falling back to `cellsize=1.0`, so the talus threshold becomes 0.7 m instead of
    0.7 x 81.25 m — conserves mass and makes every ordering above MORE true, not less. Measured:
    that mutation leaves this whole file green (25 passed). Bounding it needs a roughness BAND, and
    no band derived from measurement separates it from a legitimate retuning of `factor` or `iters`,
    so none is invented here. It is recorded as a known gap in
    `registers/mutation-proofs.wave7-hero.tsv`.
    """
    _image, facts = _montage()
    e = facts["erosion"]
    assert e["roughness_hydraulic"] > e["roughness_in"], (
        f"the droplet pass did not incise: roughness {e['roughness_in']:.2f} -> "
        f"{e['roughness_hydraulic']:.2f}")
    assert e["roughness_out"] < e["roughness_hydraulic"], (
        f"the thermal pass did not relax the incised field: {e['roughness_hydraulic']:.2f} -> "
        f"{e['roughness_out']:.2f}")
    assert e["roughness_out"] < e["roughness_in"], (
        f"the composed panel is not smoother than its input: {e['roughness_in']:.2f} -> "
        f"{e['roughness_out']:.2f}")
    assert 0.0 < e["relief_out_m"] < e["relief_in_m"], (
        f"eroded relief {e['relief_out_m']:.0f} m is not below uneroded {e['relief_in_m']:.0f} m")


def test_every_montage_panel_is_finite_and_none_is_degenerate():
    """`render.hillshade` NORMALISES each panel before drawing it, so a field that has gone flat,
    constant or non-finite still renders as a perfectly plausible grey tile — the check the eye
    cannot make, which is why `gallery.py` keeps a `_track()` trace and why `_montage()` now
    returns one. The panel NAMES are asserted too: a panel quietly dropped from the composition
    would otherwise leave eight guarded fields and a caption still promising nine.
    """
    _image, facts = _montage()
    names = tuple(name for name, _lo, _hi, _ok in facts["panels"])
    assert names == ("mountain:basic", "mountain:eroded", "mountain:alpine", "mountain:old",
                     "mountain:strata", "erode", "ridge", "volcano", "canyon")
    for name, lo, hi, finite in facts["panels"]:
        assert finite, f"montage panel {name!r} contains NaN or Inf"
        assert hi > lo, f"montage panel {name!r} is constant ({lo:.6g}) — hillshade would hide it"


def test_the_montage_geometry_is_the_layout_the_caption_describes():
    """The composition's own arithmetic, checked exactly rather than by eye: five tiles over four,
    5 px of background between neighbours and between the rows, and the short bottom row padded out
    to the top row's width. Every number here is an identity in `n` and the pad width, so it is
    machine-independent — and it is the one thing a pixel comparison used to cover that no field
    invariant does. A panel added, dropped, or hstacked in the wrong order changes the width.
    """
    image, facts = _montage()
    n, pad = facts["resolution"], facts["layout"]["pad"]
    top_w = facts["layout"]["top"] * n + (facts["layout"]["top"] - 1) * pad
    bottom_w = facts["layout"]["bottom"] * n + (facts["layout"]["bottom"] - 1) * pad
    assert image.shape == (2 * n + pad, top_w, 3) and image.dtype == np.uint8
    bg = facts["background"]
    assert np.all(image[n:n + pad] == bg), "the row gap is not background"
    assert np.all(image[n + pad:, bottom_w:] == bg), "the bottom row's filler is not background"
    for k in range(facts["layout"]["top"] - 1):                      # the inter-tile pads, top row
        assert np.all(image[:n, k * (n + pad) + n:(k + 1) * (n + pad)] == bg)
    for k in range(facts["layout"]["top"]):                          # and no tile is a flat fill
        assert image[:n, k * (n + pad):k * (n + pad) + n].std() > 0.0
    for k in range(facts["layout"]["bottom"]):
        assert image[n + pad:, k * (n + pad):k * (n + pad) + n].std() > 0.0
