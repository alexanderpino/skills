"""Oracles for the braided-river atom (Murray & Paola 1994). A braided river is defined by MULTIPLE
threads per cross-section (braiding index > 1); the pattern is caused by SUPER-LINEAR sediment
transport (qs ~ Q^m, m>1) — so a near-linear transport must braid far less. Sediment is conserved to
the downstream export, and the run is deterministic.
"""
import numpy as np
import braided


def _valley(n=120, m=100, slope=0.5, seed=0):
    yy, xx = np.mgrid[0:n, 0:m].astype(float)
    rng = np.random.default_rng(seed)
    return 200.0 - slope * yy + rng.standard_normal((n, m)) * 2.0     # downstream-sloping, faint roughness


def test_it_braids_multiple_threads():
    """The defining property: more than one active channel per cross-section on average."""
    _, Q = braided.braided_river(_valley(), 90, K=0.04, m_exp=2.5, erode_rate=0.15,
                                 lateral=0.28, sed_feed=1.0, Q0=1.0, rain=0.03)
    assert braided.braiding_index(Q) > 1.5                            # genuinely multi-thread


def test_superlinear_transport_is_what_braids():
    """Murray & Paola's central result: braiding is driven by the super-linearity of transport in
    discharge. Linear transport (m=1) concentrates far less, so it braids much less than m=2.5."""
    kw = dict(steps=90, K=0.04, erode_rate=0.15, lateral=0.28, sed_feed=1.0, Q0=1.0, rain=0.03)
    _, q_braid = braided.braided_river(_valley(), m_exp=2.5, **kw)
    _, q_lin = braided.braided_river(_valley(), m_exp=1.0, **kw)
    assert braided.braiding_index(q_braid) > braided.braiding_index(q_lin) + 0.4


def test_sediment_is_conserved_to_the_export():
    """Erosion adds to the load, deposition removes it, lateral transport is a strict flux form —
    so the net change in bed mass equals what was fed in minus what left the downstream edge."""
    bed, Q, b = braided.braided_river(_valley(seed=1), 40, K=0.04, m_exp=2.5, erode_rate=0.2,
                                      lateral=0.25, sed_feed=0.9, Q0=1.0, rain=0.03, return_budget=True)
    assert np.all(np.isfinite(bed))
    assert abs(b["bed_change"] - (b["fed"] - b["exported"])) < 1e-6 * (abs(b["fed"]) + 1.0)


def test_deterministic():
    a = braided.braided_river(_valley(seed=2), 30, K=0.04)[0]
    b = braided.braided_river(_valley(seed=2), 30, K=0.04)[0]
    assert np.array_equal(a, b)
