"""Oracle tests for the lithology -> spatial-K stream-power coupling (11 / 04).

Stream power `dh/dt = U - K A^m S^n`. Making K a FIELD (or a callable K(p,h)) is the differential-
erosion coupling: at steady state slope S ~ (U/(K A^m))^(1/n), so relief scales as K^(-1/n) — hard
rock (low K) stands proud as caprock / cuestas / structural benches, soft rock cuts to valleys.
The mechanism extends the verified P-tier solver, so these are quantitative, not just invariants."""
import numpy as np

import erosion_streampower as SP
import landforms as L
import analysis as A


def test_scalar_K_equals_uniform_field():
    """Backward compatibility: a scalar K must give exactly the same result as a uniform field of
    that value (the scalar path just broadcasts). Protects every existing caller + the Landlab
    cross-validation."""
    rng = np.random.default_rng(0)
    h0 = rng.uniform(0.0, 1.0, (40, 40)) * 0.05
    a = SP.stream_power_evolve(h0, 1.0, 0.4, 0.5, 2.0, 120)
    b = SP.stream_power_evolve(h0, 1.0, np.full((40, 40), 0.4), 0.5, 2.0, 120)
    assert np.array_equal(a, b)


def test_lower_K_gives_more_relief():
    """The decisive scaling S ~ K^(-1/n): harder rock (lower K), same forcing, builds MORE relief."""
    rng = np.random.default_rng(1)
    h0 = rng.uniform(0.0, 1.0, (56, 56)) * 0.05
    soft = SP.stream_power_evolve(h0, 1.0, 1.0, 0.5, 2.0, 250)
    hard = SP.stream_power_evolve(h0, 1.0, 0.2, 0.5, 2.0, 250)
    assert np.ptp(hard[4:-4, 4:-4]) > 1.5 * np.ptp(soft[4:-4, 4:-4])


def test_spatial_K_hard_region_stands_proud():
    """A hard (low-K) half of the domain, under the same uplift as the soft half, ends up higher and
    with more relief — differential erosion at a scale where drainage-area noise can't mask it."""
    rng = np.random.default_rng(5)
    n = 56
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    K = np.full((n, n), 1.0)
    K[:, :n // 2] = 0.12                                   # left half hard
    h = SP.stream_power_evolve(h0, 1.0, K, 0.5, 2.0, 300)
    I = np.zeros((n, n), bool); I[4:-4, 4:-4] = True
    hard = I.copy(); hard[:, n // 2:] = False
    soft = I.copy(); soft[:, :n // 2] = False
    assert h[hard].mean() > 2.0 * h[soft].mean()          # hard half stands proud
    assert np.ptp(h[hard]) > np.ptp(h[soft])              # ...and carries more relief


def test_callable_K_is_reevaluated_on_the_surface():
    """K may be a callable K(h) re-evaluated each iteration — the faithful K(p,h) (beds fixed in the
    column, exposed as incision cuts down). It must (a) run and (b) differ from freezing K at the
    initial surface, proving the re-evaluation actually happens."""
    rng = np.random.default_rng(3)
    n = 48
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 5.0
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    table = [(200.0, 8e-2), (90.0, 8e-3)]
    K_of_h = lambda hh: L.bed_erodibility(L.strat_coord(hh, xx, yy), table)
    live = SP.stream_power_evolve(h0, 2.0, K_of_h, 0.5, 1000.0, 90, 50.0)
    frozen = SP.stream_power_evolve(h0, 2.0, K_of_h(h0), 0.5, 1000.0, 90, 50.0)   # K snapshot, fixed
    assert np.isfinite(live).all()
    assert not np.allclose(live, frozen)                  # live K(p,h) tracks the surface; frozen doesn't


def test_tilted_beds_make_the_topography_anisotropic():
    """Differential erosion of tilted beds imprints the strike direction on the terrain (cuestas),
    so the eroded surface is directionally biased where a uniform-K surface is isotropic."""
    rng = np.random.default_rng(0)
    n = 64
    h0 = rng.random((n, n)) * 5.0
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    table = [(600.0, 7e-2), (280.0, 6e-3)]
    Kfn = lambda hh: L.bed_erodibility(L.strat_coord(hh, xx * 50.0, yy * 50.0, tilt=(0.7, 0.25)), table)
    hk = SP.stream_power_evolve(h0, 3.0, Kfn, 0.5, 1000.0, 120, 50.0)
    hu = SP.stream_power_evolve(h0, 3.0, 3e-2, 0.5, 1000.0, 120, 50.0)
    I = np.s_[6:-6, 6:-6]
    # directional anisotropy of the gradient: |d/dx| vs |d/dy| are more unequal under tilted beds
    def aniso(z):
        gy, gx = np.gradient(z[I])
        return abs(np.abs(gx).mean() - np.abs(gy).mean()) / (np.abs(gx).mean() + np.abs(gy).mean() + 1e-9)
    assert aniso(hk) > aniso(hu)                           # tilted-bed terrain is more anisotropic
    assert np.ptp(hk[I]) > np.ptp(hu[I])                   # hard beds add relief (stand proud)
