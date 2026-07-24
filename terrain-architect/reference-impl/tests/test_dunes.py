import numpy as np
import asserts
import dunes


def _seed_field(n=40, base=4, seed=0):
    rng = np.random.default_rng(seed)
    return np.full((n, n), base, dtype=np.int64) + rng.integers(0, 2, (n, n))


def _ridge_signal(sand):
    """Transverse-dune signal: with wind along +j, dune crests run across the wind (along i) and
    are spaced ALONG the wind, so the along-wind profile (mean over rows) develops periodic ridges.
    A flat sheet or unorganised speckle has a near-constant profile -> low std."""
    return float(sand.mean(axis=0).std())


def test_slabs_conserved_exactly():
    """Transport, shadow-zone capture and avalanching only MOVE slabs — none are created/destroyed."""
    s0 = _seed_field()
    s = dunes.werner_dunes(s0, iters=8, seed=1, hop=3)
    assert int(s.sum()) == int(s0.sum())
    assert np.all(s >= 0)


def test_deposition_instability_sweeps_only_when_psand_exceeds_pbare():
    """The MINIMAL variant's sole mechanism (shadow/avalanche off): p_sand > p_bare makes deposition
    self-reinforcing, so slabs travel over bare ground and stop on sand -> sand is swept into piles
    separated by bare corridors. Equal probabilities deposit anywhere -> an even sheet, no sweeping.
    (This is the skill's 'dunes never form; flat sand sheet' failure mode.)"""
    s0 = _seed_field(seed=2)
    kw = dict(iters=30, seed=3, shadow=False, avalanche=False)
    unstable = dunes.werner_dunes(s0.copy(), p_sand=0.75, p_bare=0.25, **kw)
    neutral = dunes.werner_dunes(s0.copy(), p_sand=0.5, p_bare=0.5, **kw)
    assert (unstable == 0).mean() > 0.10                          # real sweeping occurred
    assert (unstable == 0).mean() > (neutral == 0).mean() + 0.10


def test_shadow_zone_and_avalanching_organize_transverse_dunes():
    """The two ideas the minimal model omits — the lee SHADOW ZONE (captures slabs, builds the slip
    face) and AVALANCHING (repose relaxation) — are what turn clustered sand into organised transverse
    DUNES. So the full model develops a far stronger transverse-ridge signal than the minimal variant
    run at identical parameters (Werner 1995: the shadow zone alone drives dune organisation)."""
    rng = np.random.default_rng(0)
    s0 = (rng.random((90, 90)) * 3 + 1).astype(np.int64)         # thin sheet
    kw = dict(iters=60, seed=0, p_sand=0.6, p_bare=0.1, hop=3, wind=(0, 1))
    full = dunes.werner_dunes(s0.copy(), **kw)
    minimal = dunes.werner_dunes(s0.copy(), shadow=False, avalanche=False, **kw)
    assert int(full.sum()) == int(s0.sum())                      # still conserved with shadow + avalanche
    assert _ridge_signal(full) > 2.0 * _ridge_signal(minimal)    # shadow+avalanche organise real ridges
    assert _ridge_signal(full) > 0.9                             # and the ridges are pronounced


def test_deterministic():
    s0 = _seed_field(n=24, seed=4)
    asserts.assert_deterministic(lambda: dunes.werner_dunes(s0, iters=6, seed=42, hop=3))
