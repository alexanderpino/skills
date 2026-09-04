"""The lattice pinch-point artefact, and the guard on `01`'s lacunarity claim.

WHAT THIS EXISTS FOR. Gradient noise is *identically zero at every lattice point*. At lacunarity
exactly 2 every octave's lattice coincides with the coarsest one's, so at those shared points all
octaves are zero at once and the sum is too — a grid of hard zeros printed through anything derived
from the height. `noise.py` ships `lacunarity=2.03` for that reason and cites `01` for it, and `01`
warned about it in prose while its four pseudocode blocks all carried `lacunarity=2.0` as their
default. A reader implementing from the block got the artefact; the caveat sat one paragraph too
late to prevent it.

⚠️ TWO MEASUREMENTS THAT DID NOT FIND IT, RECORDED BECAUSE THEY LOOK RIGHT. Spectral axis energy
(18.6% at 2.0 against 18.8% at 2.03) and inter-octave correlation (max 0.033 either way) both
separate the two values by nothing at all. Neither is wrong as a statistic; both are the wrong
statistic. The artefact is not correlation between octaves and not directional energy — it is a
coincidence of ZERO SETS, and it is invisible to any measure that does not evaluate ON the shared
lattice. A claim tested with a plausible instrument that cannot see it reads as disproven.
"""
import numpy as np
import pytest

import noise

OCTAVES = 6
GAIN = 0.5


def _fbm_at(px, py, lacunarity, octaves=OCTAVES, seed_offset=True):
    """`noise.fbm`'s own summation, evaluated at single points rather than on a grid.

    Written out here rather than called through `noise.fbm` so the test can vary the seed-offset
    independently — which is what separates the two defences the module stacks.
    """
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for k in range(int(octaves)):
        s = k * 1013 if seed_offset else 0
        total += amp * float(noise.perlin(np.array([px * freq]),
                                          np.array([py * freq]), s)[0])
        norm += amp
        freq *= lacunarity
        amp *= GAIN
    return total / norm


def _on_and_off_lattice(lacunarity, reps=400, seed_offset=True):
    rng = np.random.RandomState(7)
    on, off = [], []
    for _ in range(reps):
        i, j = rng.randint(3, 120, 2)
        on.append(abs(_fbm_at(float(i), float(j), lacunarity, seed_offset=seed_offset)))
        off.append(abs(_fbm_at(i + rng.rand() * 0.8 + 0.1,
                               j + rng.rand() * 0.8 + 0.1,
                               lacunarity, seed_offset=seed_offset)))
    return np.array(on), np.array(off)


def test_lacunarity_two_gives_exactly_zero_on_the_shared_lattice():
    """The artefact `01` describes, at full strength: not small, exactly zero."""
    on, off = _on_and_off_lattice(2.0)
    assert on.max() == 0.0, (
        "expected identically zero at shared lattice points, got max %.3e" % on.max())
    assert off.mean() > 0.05, (
        "the off-lattice control is too quiet to make the comparison mean anything: %.4f"
        % off.mean())


def test_the_shipped_lacunarity_removes_it():
    """2.03 lifts the shared points well clear of zero — a mitigation, not a cure."""
    on, off = _on_and_off_lattice(2.03)
    assert on.mean() > 0.02, (
        "detuned lacunarity should not leave a pinch grid: mean |fbm| %.5f" % on.mean())
    ratio = on.mean() / off.mean()
    assert 0.2 < ratio < 0.9, (
        "expected a partial residual deficit, got on/off = %.3f" % ratio)


def test_the_seed_offset_does_not_fix_it():
    """⚠️ THE ROW THAT STOPS THE TWO DEFENCES BEING CONFLATED.

    `noise.fbm` both detunes the lacunarity and offsets the seed per octave, and it would be
    natural to assume either handles this. The seed offset does not, and cannot: the zeros come
    from the lattice geometry, which the seed does not move. Without this row, someone tidying the
    module could drop the detuning on the reasoning that the offset already covers it.
    """
    on_off, _ = _on_and_off_lattice(2.0, reps=120, seed_offset=False)
    on_on, _ = _on_and_off_lattice(2.0, reps=120, seed_offset=True)
    assert on_off.max() == 0.0 and on_on.max() == 0.0, (
        "the pinch grid should survive the seed offset: %.3e / %.3e"
        % (on_off.max(), on_on.max()))


def test_shipped_fbm_default_is_detuned():
    """The module default must stay off 2, or the chapter's claim stops describing the code."""
    import inspect
    for name in ("fbm", "ridged_mf", "hybrid_mf"):
        sig = inspect.signature(getattr(noise, name))
        lac = sig.parameters["lacunarity"].default
        assert lac != 2.0, "%s ships lacunarity exactly 2.0" % name
        assert 1.9 < lac < 2.1, "%s ships lacunarity %r, outside the sane band" % (name, lac)


@pytest.mark.parametrize("octaves", [3, 6, 9])
def test_the_artefact_does_not_wash_out_with_more_octaves(octaves):
    """Adding octaves cannot rescue it: every added octave is zero there too."""
    rng = np.random.RandomState(3)
    vals = [abs(_fbm_at(float(i), float(j), 2.0, octaves=octaves))
            for i, j in rng.randint(3, 90, (60, 2))]
    assert max(vals) == 0.0, (
        "%d octaves at lacunarity 2 should still pinch: max %.3e" % (octaves, max(vals)))
