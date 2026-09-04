"""Oracles for the parameterised impact (crater.py). The SIZE physics is decisive (Collins/
Melosh/Marcus 2005 π-scaling exponents; the 1/g transition); the SHAPE-under-obliquity checks
are morphological (elongation onset, downrange ejecta asymmetry) matched to the experiments.
"""
import numpy as np
import crater as C
import crater_demo


# --- SIZE: π-scaling exponents (Collins/Melosh/Marcus 2005) ---
def test_angle_enters_as_sin_theta_one_third():
    """The decisive angle law: D_tc ∝ (sinθ)^(1/3) — a grazing impact digs a smaller crater."""
    d90 = C.transient_crater_diameter(200, 18000, angle=90)
    d30 = C.transient_crater_diameter(200, 18000, angle=30)
    assert abs(d90 / d30 - (1.0 / np.sin(np.radians(30))) ** (1 / 3)) < 1e-6
    assert abs(d90 / d30 - 2 ** (1 / 3)) < 1e-6                # sin30=0.5


def test_size_scaling_exponents():
    base = C.transient_crater_diameter(200, 18000, rho_i=3000, g=9.81, angle=45)
    assert abs(C.transient_crater_diameter(400, 18000, angle=45) / base - 2 ** 0.78) < 1e-6
    assert abs(C.transient_crater_diameter(200, 36000, angle=45) / base - 2 ** 0.44) < 1e-6
    assert abs(C.transient_crater_diameter(200, 18000, g=19.62, angle=45) / base - 2 ** -0.22) < 1e-6
    assert abs(C.transient_crater_diameter(200, 18000, rho_i=6000, angle=45) / base
               - 2 ** (1 / 3)) < 1e-6                         # density ratio ^(1/3)


def test_transition_scales_inversely_with_gravity():
    """Simple→complex transition ∝ 1/g — larger on the Moon (Melosh 1989)."""
    assert abs(C.transition_diameter(1.62) / C.transition_diameter(9.81) - 9.81 / 1.62) < 1e-6
    # a 10 km crater is complex on Earth but simple on the Moon
    assert C.final_crater(8000.0, g=9.81)[1] is True
    assert C.final_crater(8000.0, g=1.62)[1] is False


def test_final_crater_simple_vs_complex():
    small, cx1, d1 = C.final_crater(500.0, g=9.81)            # < 3.2 km transition
    assert cx1 is False and abs(small - 1.25 * 500.0) < 1e-9
    big, cx2, d2 = C.final_crater(20000.0, g=9.81)
    assert cx2 is True and d2 / big < d1 / small              # complex craters are shallower


# --- SHAPE under obliquity (morphological) ---
def test_crater_is_circular_above_threshold_elongated_below():
    assert C._ellipticity(45) == 1.0 and C._ellipticity(20) == 1.0
    assert C._ellipticity(6) > 1.0 and C._ellipticity(0) > C._ellipticity(6)


def _footprint(angle):
    flat = np.zeros((240, 240))
    h, info = C.stamp_impact(flat, 120, 120, cellsize=200.0, L=1500.0, v=20000.0,
                             angle=angle, azimuth=0.0)          # downrange = +x
    bowl = h < -0.1 * info["depth"]
    ys, xs = np.where(bowl)
    return (xs.max() - xs.min() + 1), (ys.max() - ys.min() + 1), h, info


def test_oblique_crater_elongates_downrange():
    wx, wy, _, _ = _footprint(45)
    assert abs(wx / wy - 1.0) < 0.15                          # ~circular at 45°
    wx2, wy2, _, _ = _footprint(5)
    assert wx2 / wy2 > 1.3                                    # elongated along the trajectory


def test_ejecta_is_downrange_asymmetric_when_oblique():
    n = 240
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    for angle, symmetric in [(90, True), (25, False)]:
        h, info = C.stamp_impact(np.zeros((n, n)), 120, 120, cellsize=200.0, L=1500.0,
                                 v=20000.0, angle=angle, azimuth=0.0)
        ej = np.maximum(h, 0.0)                               # ejecta (positive relief) + rim
        down = ej[xx > 120].sum()
        up = ej[xx < 120].sum()
        if symmetric:
            assert abs(down - up) < 0.05 * (down + up)        # vertical: symmetric
        else:
            assert down > 1.3 * up                            # oblique: downrange-loaded


def test_ejecta_conserves_excavated_mass():
    """The deposited ejecta volume is `deposit_fraction` of what the bowl excavated — mass is
    pushed OUT and piled back down, not conjured. (The rest bulks the floor / escapes.)"""
    for angle in (90.0, 45.0, 20.0, 8.0):
        _, info = C.stamp_impact(np.zeros((260, 260)), 130, 130, cellsize=200.0, L=1500.0,
                                 v=20000.0, angle=angle, azimuth=0.0, deposit_fraction=0.9)
        assert info["excavated"] > 0.0
        assert abs(info["deposited"] / info["excavated"] - 0.9) < 1e-6


def _cross_over_downrange(angle):
    n, c = 400, 200
    h, _ = C.stamp_impact(np.zeros((n, n)), c, c, cellsize=200.0, L=1500.0, v=20000.0,
                          angle=angle, azimuth=0.0)
    dep = np.maximum(h, 0.0)
    yy, xx = np.mgrid[0:n, 0:n] - c
    a = np.degrees(np.arctan2(yy, xx))
    down = dep[np.abs(a) < 30].sum()
    cross = dep[np.abs(np.abs(a) - 90) < 30].sum()
    return cross / (down + 1e-9)


def test_butterfly_only_at_grazing_not_premature():
    """The cross-range 'butterfly' must NOT appear at moderate obliquity — at 8° the ejecta is
    still a tight DOWNRANGE lobe. It emerges only near grazing (<~5°; Gault & Wedekind 1978),
    where the downrange sector itself goes forbidden and mass swings cross-range. This is the bug
    the earlier model had: it split into wings from ~15° down (butterfly onset was 15°, not 5°)."""
    assert _cross_over_downrange(8.0) < 0.3                   # moderate: downrange lobe, no wings
    assert _cross_over_downrange(2.0) > 0.9                   # grazing: genuine cross-range butterfly


def test_central_peak_offset_is_uprange_not_downrange():
    """Any central-peak offset points UP-RANGE (deepest-penetration side; Schultz 1996), never
    downrange — the direction the earlier model had backwards. (Magnitude is contested — Ekholm &
    Melosh 2001 — so we assert only the sign.)"""
    n, c = 300, 150
    h, info = C.stamp_impact(np.zeros((n, n)), c, c, cellsize=300.0, L=4000.0, v=20000.0,
                             angle=25.0, azimuth=0.0)                  # downrange = +x (+col)
    assert info["complex"] is True
    R = 0.5 * info["D_final"] / 300.0
    w = int(0.4 * R)
    peak_col = int(np.argmax(h[c, c - w:c + w + 1])) + (c - w)
    assert peak_col < c                                      # peak sits up-range of the centre


def test_natural_render_is_deterministic_textured_and_forward():
    """The presentation layer (crater_demo.stamp_impact_natural) is a *look*, not oracle physics,
    but it must still: be deterministic per seed, stay finite, excavate a bowl AND raise ejecta,
    leave the surrounding plain TEXTURED (not dead flat — the Gemini critique), and throw more
    ejecta downrange than up-range when oblique."""
    N = 160
    D = C.final_crater(C.transient_crater_diameter(500.0, 20000.0, angle=30.0))[0]
    cs = D / (N * 0.30)
    a, _ = crater_demo.stamp_impact_natural(np.zeros((N, N)), N // 2, N // 2, cs, L=500.0,
                                            angle=30.0, azimuth=0.0, seed=3)
    b, _ = crater_demo.stamp_impact_natural(np.zeros((N, N)), N // 2, N // 2, cs, L=500.0,
                                            angle=30.0, azimuth=0.0, seed=3)
    assert np.array_equal(a, b)                              # deterministic for a given seed
    assert np.all(np.isfinite(a))
    assert a.min() < 0 < a.max()                            # excavates a bowl and raises ejecta/rim
    assert a[:16, :16].std() > 0                            # plain is textured, not flat
    dep = np.maximum(a, 0.0)
    assert dep[:, N // 2:].sum() > dep[:, :N // 2].sum()    # mass pushed forward (downrange = +x)


def test_pseudocode_in_11_geological_matches_crater_py():
    """The `references/11-geological.md` oblique-impact pseudocode must stay in lock-step with the
    implementation. This re-implements that block verbatim and asserts it reproduces crater.py — so
    editing one without the other trips a red test (answers 'does the pseudocode still correspond?')."""
    clip = lambda x: np.clip(x, 0.0, 1.0)

    def ps_final(D_tc, g=9.81):
        Dc = 3200.0 * (9.81 / g)
        if 1.25 * D_tc < Dc:
            return 1.25 * D_tc, False, 0.20 * 1.25 * D_tc
        D = 1.17 * D_tc ** 1.13 / Dc ** 0.13
        return D, True, 0.20 * Dc * (D / Dc) ** 0.3

    ps_ecc = lambda a: 1.0 + 1.2 * clip((12.0 - a) / 12.0)

    def ps_azw(psi, a):
        d = clip((90.0 - a) / 85.0); p = 1.0 + 3.0 * clip((20.0 - a) / 20.0)
        bf = clip((5.0 - a) / 5.0); down = 0.5 + 0.5 * np.cos(psi)
        w = (1.0 - d) + d * down ** p
        w = (1.0 - bf) * w + bf * np.sin(psi) ** 2
        return 0.12 + 0.88 * np.clip(w, 0.0, 1.0)

    psis = np.linspace(0, 2 * np.pi, 13)
    for a in (90, 45, 30, 20, 12, 8, 5, 3):
        assert abs(ps_ecc(a) - C._ellipticity(a)) < 1e-12
        assert np.max(np.abs(ps_azw(psis, a) - C._ejecta_azimuth_weight(psis, a))) < 1e-12
    for D_tc in (300.0, 1500.0, 6000.0, 40000.0):
        pd, pc, pdep = ps_final(D_tc)
        cd, cc, cdep = C.final_crater(D_tc)
        assert pc is cc and abs(pd - cd) < 1e-9 and abs(pdep - cdep) < 1e-9


def test_grazing_crater_is_deeper_uprange():
    """A grazing crater's deepest point / steepest wall sits UP-RANGE (first contact / peak energy;
    Schultz, arXiv 2308.01876), shallowing down-range where material is plowed out. The plow used to
    deepen down-range (backwards) — this locks the corrected direction. (Presentation layer.)"""
    N, c = 400, 200
    D = C.final_crater(C.transient_crater_diameter(200.0, 20000.0, angle=3.0))[0]
    cs = D * C._ellipticity(3.0) / (N * 0.55)
    h, _ = crater_demo.stamp_impact_natural(np.zeros((N, N)), c, c, cs, L=200.0, v=20000.0,
                                            angle=3.0, azimuth=0.0, seed=5)      # downrange = +x
    profile = h[c - 1:c + 2].mean(axis=0)                                        # along the track
    deepest_col = int(np.argmin(profile))
    assert deepest_col < c                                                       # up-range of centre


def test_finite_and_complex_has_central_peak():
    h, info = C.stamp_impact(np.zeros((300, 300)), 150, 150, cellsize=300.0, L=4000.0,
                             v=20000.0, angle=90.0)
    assert np.all(np.isfinite(h)) and info["complex"] is True
    assert h[150, 150] > h[150, 165]                          # central peak above the floor
