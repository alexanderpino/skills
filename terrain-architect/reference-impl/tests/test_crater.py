"""Oracles for the parameterised impact (crater.py). The SIZE physics is decisive (Collins/
Melosh/Marcus 2005 π-scaling exponents; the 1/g transition); the SHAPE-under-obliquity checks
are morphological (elongation onset, downrange ejecta asymmetry) matched to the experiments.
"""
import numpy as np
import crater as C


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


def test_finite_and_complex_has_central_peak():
    h, info = C.stamp_impact(np.zeros((300, 300)), 150, 150, cellsize=300.0, L=4000.0,
                             v=20000.0, angle=90.0)
    assert np.all(np.isfinite(h)) and info["complex"] is True
    assert h[150, 150] > h[150, 165]                          # central peak above the floor
