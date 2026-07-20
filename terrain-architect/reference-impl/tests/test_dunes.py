import numpy as np
import asserts
import dunes


def _seed_field(n=40, base=4, seed=0):
    rng = np.random.default_rng(seed)
    return np.full((n, n), base, dtype=np.int64) + rng.integers(0, 2, (n, n))


def test_slabs_conserved_exactly():
    s0 = _seed_field()
    s = dunes.werner_dunes(s0, iters=8, seed=1)
    assert int(s.sum()) == int(s0.sum())          # discrete transport creates/destroys nothing
    assert np.all(s >= 0)


def test_dunes_form_only_when_psand_exceeds_pbare():
    """The instability IS the p_sand > p_bare asymmetry. When it holds, slabs travel over
    bare ground and stop on sand, so sand is SWEPT into tall dunes separated by bare
    corridors (high inequality). Equal probabilities deposit anywhere -> an even sheet, no
    sweeping. This is the skill's 'dunes never form; flat sand sheet' failure mode."""
    s0 = _seed_field(seed=2)                          # starts uniform (min 4, no bare cells)
    unstable = dunes.werner_dunes(s0.copy(), iters=30, seed=3, p_sand=0.75, p_bare=0.25)
    neutral = dunes.werner_dunes(s0.copy(), iters=30, seed=3, p_sand=0.5, p_bare=0.5)
    # instability sweeps ground bare between dunes; the neutral sheet stays mostly covered
    assert (unstable == 0).mean() > 0.10                      # real sweeping occurred
    assert (unstable == 0).mean() > (neutral == 0).mean() + 0.10


def test_deterministic():
    s0 = _seed_field(n=24, seed=4)
    asserts.assert_deterministic(lambda: dunes.werner_dunes(s0, iters=6, seed=42))
