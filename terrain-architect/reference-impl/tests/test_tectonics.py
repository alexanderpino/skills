"""Invariant tests for faults (tectonics.py / 02).

`fault_scarp` is the faultIteration displacement fractal (a structural detail layer, no drainage).
`fault_weakness` is the geologically-correct coupling: an erodibility field with the fault traces set
MORE erodible, so when it drives stream power the valleys follow the fault structure — the decisive,
quantitative check here."""
import numpy as np

import tectonics as tec
import erosion_streampower as sp


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
