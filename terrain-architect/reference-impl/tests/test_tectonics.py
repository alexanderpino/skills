"""Invariant tests for faults (tectonics.py / 02).

`fault_scarp` is the faultIteration displacement fractal (a structural detail layer, no drainage).
`fault_weakness` is the geologically-correct coupling: an erodibility field with the fault traces set
MORE erodible, so when it drives stream power the valleys follow the fault structure — the decisive,
quantitative check here."""
import numpy as np

import tectonics as tec
import erosion_streampower as sp
import ops_filters


def test_fault_scarp_offsets_a_flat_field_finitely():
    flat = np.zeros((80, 80))
    h = tec.fault_scarp(flat, n_faults=6, displacement=60.0, width=5.0, seed=1)
    assert np.isfinite(h).all()
    assert np.ptp(h) > 10.0                          # faults built structural relief
    assert np.ptp(h) < 60.0 * 6                      # ...but each offset is bounded (feathered, not runaway)


def test_fault_scarp_is_deterministic():
    flat = np.zeros((60, 60))
    assert np.array_equal(tec.fault_scarp(flat, seed=3), tec.fault_scarp(flat, seed=3))


def test_fault_weakness_marks_traces_more_erodible():
    K = tec.fault_weakness((80, 80), n_faults=5, k_rock=1.0, k_fault=7.0, width=3.0, seed=2)
    assert np.isclose(K.min(), 1.0, atol=1e-6)       # background rock
    assert K.max() > 6.5                             # fault traces near k_fault (weak)
    assert np.all(K >= 1.0 - 1e-9)                   # never below the background


def test_faults_control_the_drainage():
    """The payoff (02): feed the fault-weakened K to stream power and the valleys exploit the fault
    traces — far more of the fault cells end up as valley floor than chance would give."""
    n = 100
    K = tec.fault_weakness((n, n), n_faults=5, k_rock=1.0, k_fault=8.0, width=3.0, seed=2)
    rng = np.random.default_rng(0)
    h = sp.stream_power_evolve(rng.random((n, n)) * 5.0, 3.0, K, 0.5, 1000.0, 120, 50.0)
    fault = K > 0.5 * (K.max() + K.min())
    valley = h < np.percentile(h, 30)                # the lowest 30% by elevation = valley floor
    frac_fault_are_valleys = (valley & fault).sum() / max(fault.sum(), 1)
    assert frac_fault_are_valleys > 0.55             # ...vs the 0.30 a random field would give


# --------------------------------------------------------------------------- #
# Plate-tectonic uplift field
# --------------------------------------------------------------------------- #
def test_plate_uplift_shape_finite_deterministic():
    E = tec.plate_uplift((90, 90), n_plates=10, seed=1, cellsize=6000.0)
    assert E.shape == (90, 90) and np.isfinite(E).all()
    assert np.array_equal(tec.plate_uplift((60, 60), seed=4), tec.plate_uplift((60, 60), seed=4))


def test_plate_field_has_oceans_and_continents():
    """Per-plate base elevation: some plates are oceanic (deep), some continental (near sea level)."""
    E = tec.plate_uplift((120, 120), n_plates=12, seed=1, cellsize=6000.0)
    assert E.min() < -2000.0            # a deep ocean plate
    assert (E > 0.0).mean() > 0.2       # a real fraction of the map is continental


def test_convergent_boundaries_build_orogens_at_the_boundaries():
    """The payoff of the plate step: mountain belts (the high ground) are raised AT plate boundaries
    (collision/subduction), diffused inland over the orogen width — not in plate interiors."""
    E, pid = tec.plate_uplift((120, 120), n_plates=12, seed=1, cellsize=6000.0, return_plates=True)
    assert E.max() > 200.0 + 1500.0     # orogens well above the continental base
    bnd = np.zeros_like(pid, dtype=bool)
    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        bnd |= np.roll(np.roll(pid, di, 0), dj, 1) != pid
    near = ops_filters.gaussian(bnd.astype(float), 2.0) > 0.1        # boundary band (orogens diffuse in)
    hi = E > np.percentile(E, 92)                                    # the highest ground = orogens
    assert (hi & near).sum() / hi.sum() > 2.0 * near.mean()         # far more boundary-concentrated than area


def test_orogen_uplift_adds_relief():
    kw = dict(n_plates=12, seed=1, cellsize=6000.0)
    flat = tec.plate_uplift((100, 100), amplitude=0.0, **kw)         # base steps only
    full = tec.plate_uplift((100, 100), **kw)                        # + orogens
    assert full.std() > flat.std()
