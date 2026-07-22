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
