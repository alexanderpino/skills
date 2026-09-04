import inspect
import re
from pathlib import Path

import numpy as np
import asserts
import dunes

CHAPTER = Path(__file__).resolve().parents[2] / "references" / "05-erosion-thermal-aeolian.md"


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


def test_constant_wind_field_matches_the_constant_vector():
    """`wind_field=(u, v)` as full fields of a constant must reproduce the `wind=(di, dj)` result
    exactly — so a graph can swap the regional constant for `winds.wind_field` without any other
    change. Note the convention shift the override handles: (u, v) is (col, row), `wind` is
    (di, dj) = (row, col)."""
    s0 = _seed_field()
    n, m = s0.shape
    kw = dict(iters=6, seed=3, p_sand=0.6, p_bare=0.2, hop=3)
    base = dunes.werner_dunes(s0.copy(), wind=(0, 1), **kw)
    field = dunes.werner_dunes(s0.copy(), wind_field=(np.ones((n, m)), np.zeros((n, m))), **kw)
    assert np.array_equal(base, field)


def test_slabs_follow_a_steered_wind_and_pile_at_a_convergence():
    """The point of a per-cell wind: transport paths BEND with the flow. Under a field whose two
    halves blow toward each other, slabs are carried to the convergence line and pile up there —
    a place a single regional wind vector could never single out. (This is the same steering that
    banks sand against an obstacle as an anchored dune, `05`.)"""
    s0 = _seed_field()
    n, m = s0.shape
    u = np.where(np.arange(m)[None, :] < m // 2, 1.0, -1.0) * np.ones((n, 1))
    out = dunes.werner_dunes(s0.copy(), iters=12, seed=1, p_sand=0.6, p_bare=0.2, hop=1,
                             wind_field=(u, np.zeros((n, m))))
    assert out.sum() == s0.sum()                      # slabs still conserved
    col = out.mean(axis=0)
    seam = m // 2
    near = col[seam - 3:seam + 3].mean()
    far = np.concatenate([col[:seam // 2], col[seam + m // 4:]]).mean()
    assert near > 1.5 * far                           # sand heaps on the convergence line


# --------------------------------------------------------------------------- #
# THE SALTATION HOP. `hop` was, until this wave, stated four different ways: 05:412's Werner
# pseudocode block said `~5 cells, fixed`, 05:399's runnable-reference note said `≈3 cells`,
# this module's docstring said `~5`, and the signature shipped `1`. Two of those four are inside
# ONE chapter, so the chapter contradicted itself before the module was consulted, and
# test_pseudocode_drift.py could not see it: that register reads FENCED BLOCKS only, and 05:399
# is prose. It is now 5 in all four places — Werner's published value, "a slab moves downwind to
# a new lattice site l (typically equal to 5) sites away" (Werner 1995, restated in Kok, Parteli,
# Michaels & Karam 2012, Rep. Prog. Phys. 75 106901 §3.2.2) — and the two guards below are what
# hold it there. The `werner-saltation-hop` row of KNOWN_DIVERGENCES was retired against them.

_PROSE_HOP = re.compile(r"`hop` is the saltation length[^\n]*?\*\*≈([0-9.]+) cells\*\*")
_BLOCK_HOP = re.compile(r"L = saltationHop[^\n]*~([0-9.]+) cells")


def test_chapter_note_quotes_the_shipped_hop():
    """05 must state the saltation hop ONCE. Both of the chapter's statements of it — the prose
    runnable-reference note at 05:399 and the pseudocode block at 05:412 — and the value this
    module actually ships must be the same number. This is the guard that replaces the retired
    `werner-saltation-hop` divergence row on its prose side; `test_pseudocode_drift.py`'s
    BLOCK_CONSTANTS row `dunes.hop` covers the block side. A reader implements from the chapter,
    and a chapter that gives one constant two values is worse than one that disagrees with the
    code, because there is no third artifact to break the tie."""
    text = CHAPTER.read_text(encoding="utf-8")
    prose = _PROSE_HOP.findall(text)
    block = _BLOCK_HOP.findall(text)
    assert len(prose) == 1, (
        "05's runnable-reference note no longer states the saltation hop as `**≈N cells**` "
        "(found %r). Either the note was reworded past this guard or the number is gone; both "
        "leave the constant unpinned on the prose side." % (prose,))
    assert len(block) == 1, "05's Werner block no longer states `~N cells` for L (found %r)" % (block,)
    shipped = inspect.signature(dunes.werner_dunes).parameters["hop"].default
    assert float(prose[0]) == float(block[0]) == float(shipped), (
        "05 states the saltation hop as %s in its prose note and %s in its pseudocode block, and "
        "dunes.werner_dunes ships hop=%s. These must be one number (Werner 1995: l = 5 cells)."
        % (prose[0], block[0], shipped))


def test_a_slab_hops_exactly_hop_cells():
    """`hop` means CELLS PER TRANSPORT STEP, not a speed or a scale factor. Start every slab on
    column 0 of a bare periodic field and let it deposit on first landing (p_sand = p_bare = 1,
    no shadow, no avalanche): every landing site is then exactly one hop downwind of the previous
    one, so sand can only ever occupy columns that are multiples of `hop` (mod m). Off-lattice
    sand means the hop was applied as something other than `hop` whole cells."""
    n, m, hop = 8, 20, 5                                  # m % hop == 0, so the lattice wraps cleanly
    s0 = np.zeros((n, m), dtype=np.int64)
    s0[:, 0] = 3
    out = dunes.werner_dunes(s0.copy(), iters=3, seed=0, p_sand=1.0, p_bare=1.0, hop=hop,
                             wind=(0, 1), shadow=False, avalanche=False)
    assert int(out.sum()) == int(s0.sum())
    occupied = set(np.flatnonzero(out.sum(axis=0)).tolist())
    assert occupied <= {0, 5, 10, 15}, (
        "slabs landed on columns %s; with hop=%d every landing must be a multiple of %d from the "
        "source column" % (sorted(occupied), hop, hop))
    assert len(occupied) > 1                              # and transport actually happened


def test_hop_sets_the_dune_wavelength():
    """The claim the constant carries — a longer saltation hop makes LONGER dunes — measured, not
    asserted. Same seed, same sheet, same everything else: the along-wind profile's spectral
    centroid wavelength is ~1.85x longer at the shipped hop=5 than at hop=1 (measured 1.84-1.98
    over five seeds; the bar here is a wide 1.35). This is why the constant is not a taste
    setting: changing it changes the landform, so the four artifacts that state it must agree."""
    n, m = 16, 96                                         # long along the wind (+j) -> resolvable FFT
    rng = np.random.default_rng(0)
    s0 = (rng.random((n, m)) * 3 + 1).astype(np.int64)

    def wavelength(hop):
        out = dunes.werner_dunes(s0.copy(), iters=40, seed=0, p_sand=0.6, p_bare=0.1,
                                 wind=(0, 1), hop=hop)
        assert int(out.sum()) == int(s0.sum())
        prof = out.mean(axis=0).astype(float)
        prof -= prof.mean()
        power = np.abs(np.fft.rfft(prof)) ** 2
        power[0] = 0.0
        k = np.arange(len(power))
        return m / (float(np.sum(power * k)) / float(np.sum(power)))   # spectral centroid

    short, long_ = wavelength(1), wavelength(5)
    assert long_ > 1.35 * short, (
        "hop=5 gave a dominant wavelength of %.1f cells and hop=1 gave %.1f — the hop is supposed "
        "to set the dune wavelength" % (long_, short))
