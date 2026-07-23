"""Oracles for the geological landforms (11-geological.md). Craters hit Pike/Melosh numbers
(depth/D, rim, r^-3 ejecta, a central peak when complex, and the gravity pi-scaling); strata
is a periodic material coordinate; terracing quantises to flat treads; folding is a sinusoid;
karst carves pits only on soluble rock and marks them do-not-fill.
"""
import numpy as np
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
    """The Ridge node: a single high crest line with ASYMMETRIC flanks (steep scarp / gentle dip)."""
    h = L.ridge((90, 90), 30.0, seed=2, height=900.0, asymmetry=0.6)
    assert np.all(np.isfinite(h)) and 400.0 < np.ptp(h) < 1600.0
    assert h.max() > h.mean() + 0.30 * np.ptp(h)                          # a real crest, not flat noise
    # a symmetric arête has a narrower footprint above half-height than an asymmetric hogback
    frac = lambda a: np.mean(L.ridge((90, 90), 30.0, seed=2, height=900.0, asymmetry=a) > 450.0)
    assert frac(0.6) > frac(0.0)


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
