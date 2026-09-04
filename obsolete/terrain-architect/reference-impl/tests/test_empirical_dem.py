"""Guard for `empirical_dem.py` — VALIDATION.md's rung 5, the real-DEM comparison.

⚠️ THIS MODULE SHIPPED UNTESTED, and it is not a peripheral one: it is the *entire* evidence for
the highest rung of `VALIDATION.md`'s ladder, the claim that our terrain's statistics fall inside
the range measured on real landscapes. `tests/test_empirical.py` exists and sounds like it covers
this — it does not; it tests emergent statistics of generated terrain and never imports this
module. The name collision is why the gap survived.

`fetch_dem` needs the network, so it cannot be exercised here beyond its documented failure path.
`metrics` can be, and it is the load-bearing half: the whole rung rests on it being **the same
estimator applied to both sides**, so what matters is which of its outputs are properties of the
terrain and which are properties of the measurement.
"""
import numpy as np
import pytest

import empirical_dem as E

CELLSIZE = 60.0


@pytest.fixture(scope="module")
def terrain():
    return E.our_terrain(n=100, cellsize=CELLSIZE, seed=0)


def test_hypsometric_integral_of_a_linear_ramp_is_exactly_one_half():
    """A decisive oracle, not a plausibility band.

    `HI = (mean − min)/(max − min)`, and a linear ramp has `mean = (min + max)/2`, so the answer
    is 0.5 by construction and any deviation is a defect in the estimator rather than a property
    of the surface. Measured: 0.5000000000.
    """
    ramp = np.tile(np.linspace(0.0, 1000.0, 120), (120, 1))
    hi, _theta, _hack = E.metrics(ramp.copy(), CELLSIZE)
    assert abs(hi - 0.5) < 1e-12, "linear ramp gives HI %.12f, not 0.5" % hi


def test_the_hypsometric_oracle_uses_a_surface_that_separates_mean_from_median():
    """⚠️ THE RAMP ABOVE CANNOT SEE THE MOST LIKELY DEFECT, so it does not stand alone.

    A linear ramp's mean and median are the same number, so replacing `h.mean()` with
    `np.median(h)` in `metrics` leaves the ramp oracle at exactly 0.5 and every other row in this
    file green. That mutation was run and passed 7/7 — the ramp is a real oracle for a scaling or
    offset error and a vacuous one for the mean/median confusion, which is the substitution most
    likely to be made by accident.

    A quadratic surface separates them: over `x_i = i/(n−1)` the mean of `x²` is `(2n−1)/(6(n−1))`
    — 0.334734 at n=120 — while the median is 0.250018. The closed form is written from `n`, not
    measured from the array, so this is an oracle rather than a restatement.
    """
    n = 120
    x = np.linspace(0.0, 1.0, n)
    quad = np.tile(x ** 2, (n, 1)) * 1000.0
    hi, _theta, _hack = E.metrics(quad.copy(), CELLSIZE)
    expected = (2.0 * n - 1.0) / (6.0 * (n - 1.0))       # mean of (i/(n-1))^2, min 0, max 1
    assert abs(hi - expected) < 1e-12, (
        "quadratic ramp gives HI %.12f; the closed form is %.12f. A median in place of the mean "
        "would give %.6f." % (hi, expected, float(np.median(x ** 2))))


def test_the_hypsometric_integral_is_invariant_under_vertical_rescaling(terrain):
    """HI is a shape statistic, so multiplying every elevation must not move it.

    This is the property that makes it comparable between a real DEM in metres and generated
    terrain in arbitrary units — the comparison `VALIDATION.md` rung 5 actually makes.
    """
    a = E.metrics(terrain.copy(), CELLSIZE)[0]
    b = E.metrics(terrain.copy() * 7.0, CELLSIZE)[0]
    assert abs(a - b) < 1e-12, "HI moved under a pure vertical rescale: %.12f -> %.12f" % (a, b)


def test_hacks_exponent_is_essentially_invariant_under_vertical_rescaling(terrain):
    """Hack's exponent relates channel length to area — pure geometry, no elevation in it.

    A uniform vertical scaling cannot change the flow routing, so it cannot change the lengths or
    the areas. Measured drift 2.1e-05, which is the channel mask moving by a few cells rather than
    the statistic responding to the scale.
    """
    a = E.metrics(terrain.copy(), CELLSIZE)[2]
    b = E.metrics(terrain.copy() * 7.0, CELLSIZE)[2]
    assert abs(a - b) < 1e-3, "Hack's exponent moved under a vertical rescale: %.6f -> %.6f" % (a, b)


def test_the_concavity_estimator_is_NOT_scale_invariant_and_this_pins_how_much(terrain):
    """⚠️ THE FINDING THIS FILE WAS WRITTEN TO RECORD. Read before trusting a theta comparison.

    `metrics` masks channels with `slope > 1e-4` — an ABSOLUTE threshold on a quantity that scales
    with relief. Multiply the terrain by 7 and theta moves from 0.6138 to 0.5715, a **6.9%** shift,
    while HI does not move at all and Hack's exponent moves by 2e-05.

    The mechanism is worse than the number suggests. The mask changes by only **four cells** out of
    ~395. They are the lowest-slope, largest-area cells, so they sit at the far end of the
    log-log regression and lever the fit out of proportion to their count.

    ⚠️ WHY THIS MATTERS FOR RUNG 5. The module's own docstring says the same estimator on both
    sides "is the only fair test (concavity in particular is measurement-sensitive)" — and it is
    right that concavity is measurement-sensitive. But calling one function on both sides does not
    make the measurement identical when the threshold inside it is absolute and the two sides have
    different relief. A real SRTM tile and a generated field with different vertical scales are
    measured with effectively different channel masks.

    This row does not assert the estimator is wrong — theta may still be the right thing to
    compare, and changing the threshold to a relative one would change every recorded number in
    `VALIDATION.md`. It pins the sensitivity so it cannot silently grow, and so the next reader
    meets it as a measured fact rather than discovering it.
    """
    a = E.metrics(terrain.copy(), CELLSIZE)[1]
    b = E.metrics(terrain.copy() * 7.0, CELLSIZE)[1]
    drift = abs(a - b) / a
    assert drift > 0.01, (
        "theta is now scale-invariant (%.6f vs %.6f). If the threshold was made relative, that is "
        "an improvement — but VALIDATION.md's recorded rung-5 numbers were measured with the "
        "absolute one and must be re-derived." % (a, b))
    assert drift < 0.15, (
        "theta's scale sensitivity has grown to %.1f%% (%.6f vs %.6f); it was 6.9%%. The rung-5 "
        "comparison degrades as this grows." % (100 * drift, a, b))


def test_our_terrain_is_deterministic_and_actually_uses_its_seed():
    """Rung 5 quotes specific numbers, which requires the generated side to be reproducible.

    Both halves matter: same seed must give the identical field, and different seeds must give a
    different one. A generator that ignored its seed would satisfy the first alone.
    """
    a = E.our_terrain(n=64, cellsize=CELLSIZE, seed=0)
    b = E.our_terrain(n=64, cellsize=CELLSIZE, seed=0)
    c = E.our_terrain(n=64, cellsize=CELLSIZE, seed=1)
    assert np.array_equal(a, b), "our_terrain is not deterministic at a fixed seed"
    assert not np.allclose(a, c), "our_terrain ignores its seed"


def test_metrics_returns_finite_values_on_generated_terrain(terrain):
    """The regressions take logs of slope and area; an empty or degenerate mask returns nan.

    A nan reaching `VALIDATION.md` as a recorded statistic is the failure this catches.
    """
    hi, theta, hack = E.metrics(terrain.copy(), CELLSIZE)
    for name, v in (("HI", hi), ("theta", theta), ("hack", hack)):
        assert np.isfinite(v), "%s came back %r" % (name, v)
    assert 0.0 <= hi <= 1.0, "HI outside [0,1]: %r" % hi


def test_fetch_dem_returns_none_on_failure_rather_than_raising(monkeypatch, tmp_path):
    """The documented contract: "None on network failure", so `main` can report and continue.

    Guarded because it is the branch that runs in every environment WITHOUT the network — that is,
    in CI and in this suite — so if it raised instead, rung 5 would fail loudly for the wrong
    reason and be disabled rather than fixed.
    """
    monkeypatch.setattr(E, "_CACHE", str(tmp_path / "cache"))

    def _boom(*_a, **_k):
        raise OSError("no network here")

    monkeypatch.setattr(E.urllib.request, "urlopen", _boom)
    assert E.fetch_dem("https://example.invalid/N00W000.hgt.gz") is None
