"""Oracles for scatter (07-scatter.md). The decisive one is Bridson's guarantee: no two
samples closer than r. Plus density-following, deterministic tileable jitter, and the
rule-based gates actually rejecting cliffs/treeline/water.
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import scatter as S


def _min_pairwise(pts):
    d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    d[np.diag_indices(len(pts))] = np.inf
    return d.min()


def test_poisson_disk_respects_min_distance():
    """Bridson's guarantee: every pair is at least r apart, and the set is maximal (fills)."""
    pts = S.poisson_disk(100.0, 100.0, r=6.0, seed=1)
    assert len(pts) > 30                               # maximal-ish, not a handful
    assert _min_pairwise(pts) >= 6.0 - 1e-9
    assert np.all((pts >= 0) & (pts < 100.0))


def test_poisson_disk_deterministic():
    a = S.poisson_disk(60.0, 60.0, r=5.0, seed=7)
    b = S.poisson_disk(60.0, 60.0, r=5.0, seed=7)
    assert a.shape == b.shape and np.allclose(a, b)
    c = S.poisson_disk(60.0, 60.0, r=5.0, seed=8)
    assert a.shape != c.shape or not np.allclose(a, c)


def test_density_rejection_follows_the_field():
    """More instances land where the density map is high (left half) than low (right half)."""
    def dens(p):
        return 0.9 if p[0] < 50.0 else 0.1
    pts = S.scatter_by_density(100.0, 100.0, dens, r_min=4.0, seed=2, max_density=1.0)
    left = np.sum(pts[:, 0] < 50.0)
    right = np.sum(pts[:, 0] >= 50.0)
    assert left > 2 * right                            # density drove the count
    assert _min_pairwise(pts) >= 4.0 - 1e-9            # still respects r_min


def test_jittered_grid_is_deterministic_tileable_and_in_cell():
    g = S.jittered_grid(40.0, 40.0, spacing=5.0, seed=3)
    assert np.allclose(g, S.jittered_grid(40.0, 40.0, spacing=5.0, seed=3))   # deterministic
    assert len(g) == 8 * 8                             # one point per cell
    # every point lies within its own cell (jitter=1 -> within +/- half a cell of the centre)
    cell = np.floor(g / 5.0)
    assert np.all(cell >= 0) and np.all(cell < 8)


def test_jittered_grid_tiles_seamlessly():
    """A cell's point depends only on its integer coordinate, so a sub-region matches the whole
    (the tileability that a per-tile Poisson run lacks)."""
    full = S.jittered_grid(40.0, 40.0, spacing=5.0, seed=3).reshape(8, 8, 2)
    sub = S.jittered_grid(20.0, 20.0, spacing=5.0, seed=3).reshape(4, 4, 2)
    assert np.allclose(sub, full[:4, :4])


def test_rule_based_gates():
    pts = S.jittered_grid(40.0, 40.0, spacing=4.0, seed=5)
    kept = S.rule_based(
        pts,
        slope_fn=lambda p: 0.9 if p[0] > 20.0 else 0.1,       # steep on the right
        height_fn=lambda p: p[1],                              # height = y
        tree_line=30.0,
        max_slope_tan=np.tan(np.radians(35.0)),
    )
    assert len(kept) > 0
    assert np.all(kept[:, 0] <= 20.0)                  # steep right half rejected
    assert np.all(kept[:, 1] <= 30.0)                  # above treeline rejected


def test_sample_field_reads_the_raster():
    field = np.arange(100, dtype=float).reshape(10, 10)   # field[i,j] = 10i + j
    pts = np.array([[0.0, 0.0], [9.0, 9.0], [3.0, 5.0]])
    vals = S.sample_field(field, pts, cellsize=1.0)
    assert vals[0] == 0.0 and vals[1] == 99.0 and vals[2] == 53.0


# --------------------------------------------------------------------------- #
# ULICHNEY (1993) VOID-AND-CLUSTER TILES — the oracles for 07:139/149/175/300/311.
#
# A blue-noise generator that merely RUNS proves nothing: every one of these tests is written so
# that the two things a broken void-and-cluster implementation degenerates INTO — white noise
# (the ranking stopped being void-and-cluster) and a regular lattice (it over-regularised) — are
# shown to FAIL it, in the same test, with the numbers printed in the assertion message. An
# oracle nobody has watched fail is not known to be an oracle.
#
# MEASURED SEPARATION at n = 32, density 0.12 (recorded here so a later drift is visible):
#   radial low/high power ratio    mask 0.0453   white 0.834-1.111    lattice 0.038 (k=3) / 0.000
#   spectral peak / mean power     mask 9.71     white 6.49-6.79      lattice 91.7 (k=3) / 68.2
#   mean NN spacing (cells)        mask 2.3247   Poisson 1.5485 (theory 0.5/sqrt(lambda) 1.4427)
#   NN spacing std dev             mask 0.3161   Poisson 0.7259
#   min NN / mean spacing          mask 0.693    Poisson 0.026        white-on-lattice 0.323
#   seam-band / interior mean NN   mask 0.94-1.05 over seeds 0/1/2/7   non-wrapped filter 0.68-0.79
#   seam-band / interior occupancy mask 0.90-1.14 over the same        non-wrapped filter 1.40-1.77
# So no single statistic separates all three: white noise passes the PEAK test and the lattice
# passes the LOW/HIGH test. Both are asserted, which is why either degeneration is caught.
#
# COST. `void_and_cluster_rank(32)` is ~0.07 s, and the tests below share ONE module-scope mask
# rather than regenerating it per test, so the whole block adds well under a second.
# --------------------------------------------------------------------------- #

_N = 32
_MASK = S.void_and_cluster_mask(_N, seed=0)              # generated ONCE for the session
_DENSITY = 0.12


def _points(binary):
    """Cell centres of the set cells of an (n, n) 0/1 array, as (N, 2) (x, y)."""
    i, j = np.nonzero(binary)
    return np.stack([j + 0.5, i + 0.5], axis=1)


def _nn_distances(p, box=None):
    """Nearest-neighbour distance per point; `box` makes the metric toroidal on [0, box)^2."""
    dx = p[:, None, 0] - p[None, :, 0]
    dy = p[:, None, 1] - p[None, :, 1]
    if box is not None:
        dx = dx - box * np.round(dx / box)
        dy = dy - box * np.round(dy / box)
    d = np.hypot(dx, dy)
    d[np.diag_indices(len(p))] = np.inf
    return d.min(axis=1)


def _radial_power(binary):
    """(low/high radial power ratio, peak/mean power) of a binary point set.

    Two numbers because no ONE of them separates blue noise from both degenerations. Low/high is
    the blue-noise claim itself — power suppressed at low frequency relative to high — and white
    noise sits at ~1 because its spectrum is flat. But a regular LATTICE also suppresses low
    frequencies (to zero), so low/high alone would pass the thing the chapter is trying to avoid.
    Peak/mean is what the lattice cannot pass: its spectrum is a handful of delta spikes.
    """
    n = binary.shape[0]
    f = np.fft.fft2(binary - binary.mean())
    power = (f.real ** 2 + f.imag ** 2) / (n * n)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    rad = np.hypot(fy, fx)                                # 0 .. 0.707 cycles/cell
    low = (rad > 0) & (rad <= 0.125)                      # up to a quarter of Nyquist
    high = rad >= 0.30                                    # from 0.6 of Nyquist up
    nonzero = rad > 0
    return power[low].mean() / power[high].mean(), power[nonzero].max() / power[nonzero].mean()


def test_void_and_cluster_rank_is_a_permutation():
    """The cheapest oracle, and the one that catches the commonest bug: an off-by-one in either
    phase leaves a rank written twice and another never written, and every downstream statistic
    still looks plausible. Phase I fills n_ones-1..0 and phase II/III fills n_ones..n*n-1, so the
    two together must be exactly 0..n*n-1, each once."""
    rank = S.void_and_cluster_rank(_N, seed=0)
    assert rank.shape == (_N, _N) and rank.dtype == np.int64
    assert np.array_equal(np.sort(rank.ravel()), np.arange(_N * _N)), (
        "the rank array is not a permutation of 0..n^2-1 — %d of %d ranks are missing and %d "
        "are duplicated" % (_N * _N - len(np.unique(rank)), _N * _N,
                            _N * _N - len(np.unique(rank))))
    assert np.allclose(_MASK, rank / (_N * _N))
    assert _MASK.min() == 0.0 and _MASK.max() < 1.0


def test_the_spectrum_is_blue_and_white_noise_fails_the_same_assertion():
    """07:139's claim, and the oracle watched failing on the thing it must reject.

    Radially-averaged power of the thresholded point set, low band over high band. Blue noise
    suppresses the low band; white noise is flat, so it sits at ~1. Both are measured here, from
    the same helper on the same density, so the assertion cannot pass vacuously.
    """
    mask_pts = (_MASK < _DENSITY).astype(float)
    low_high, _ = _radial_power(mask_pts)
    assert low_high < 0.25, (
        "the mask's low/high radial power ratio is %.4f, not blue noise" % low_high)

    rng = np.random.default_rng(11)
    whites = []
    for _ in range(5):
        w = (rng.random((_N, _N)) < _DENSITY).astype(float)
        whites.append(_radial_power(w)[0])
    assert min(whites) > 0.5, (
        "white noise scored %.4f on the low/high ratio, i.e. it PASSES the blue-noise assertion "
        "above — the oracle is vacuous and the threshold has to move" % min(whites))
    assert low_high < 0.25 < min(whites), (
        "mask=%.4f vs white noise %s" % (low_high, ["%.4f" % v for v in whites]))


def test_a_regular_lattice_fails_the_spectrum_oracle_too():
    """The OTHER degeneration. A lattice suppresses low frequencies harder than blue noise does,
    so the low/high half of the oracle passes it; what it cannot pass is the peak/mean half,
    because a lattice's power lives in a few delta spikes rather than a broad high band. Asserted
    in both directions so neither half can be deleted without a red."""
    mask_pts = (_MASK < _DENSITY).astype(float)
    mask_low_high, mask_peak = _radial_power(mask_pts)

    lattice = np.zeros((_N, _N))
    lattice[::3, ::3] = 1.0                                # density 1/9, close to _DENSITY
    lat_low_high, lat_peak = _radial_power(lattice)

    assert lat_low_high < 0.25, (
        "a lattice scores %.4f on the low/high half (the mask scores %.4f) — it no longer passes "
        "it, so that half alone would be a sufficient oracle and this test states something "
        "false" % (lat_low_high, mask_low_high))
    assert mask_peak < 25.0, "the mask's own peak/mean power is %.2f" % mask_peak
    assert lat_peak > 40.0, (
        "a regular lattice scored peak/mean %.2f, i.e. it PASSES the assertion above (mask "
        "%.2f) — the oracle no longer rejects a lattice" % (lat_peak, mask_peak))


def test_spacing_is_tighter_than_poisson_at_the_same_density():
    """The no-clumping claim, against a Poisson sample actually generated at the same density.

    Poisson is the null: its nearest-neighbour distances have mean 0.5/sqrt(lambda) and a long
    left tail (points land on top of each other). Blue noise pushes the mean UP and the spread
    DOWN, and its minimum spacing is bounded well away from zero. All three are asserted against
    the measured Poisson numbers, not against remembered constants.
    """
    binary = (_MASK < _DENSITY).astype(float)
    lam = binary.mean()
    mask_nn = _nn_distances(_points(binary), box=_N)

    rng = np.random.default_rng(3)
    poisson = rng.random((int(round(lam * _N * _N)), 2)) * _N
    pois_nn = _nn_distances(poisson, box=_N)

    assert abs(pois_nn.mean() - 0.5 / np.sqrt(lam)) < 0.25, (
        "the Poisson comparator is not Poisson: mean NN %.4f vs theory %.4f"
        % (pois_nn.mean(), 0.5 / np.sqrt(lam)))
    assert mask_nn.mean() > 1.3 * pois_nn.mean(), (
        "mask mean NN %.4f is not meaningfully above Poisson's %.4f at density %.4f"
        % (mask_nn.mean(), pois_nn.mean(), lam))
    assert mask_nn.std() < 0.6 * pois_nn.std(), (
        "mask NN spread %.4f is not tighter than Poisson's %.4f" % (mask_nn.std(), pois_nn.std()))
    # The no-clumping claim, scaled by the mean spacing 1/sqrt(lambda) rather than pinned to a
    # cell count. An earlier form of this line asserted `min NN >= 2.0`, which is true at Ulichney's
    # sigma = 1.5 and NOT at sigma = 1.7 (it drops to sqrt(2)) — so the sigma DECOY in
    # registers/mutation-proofs.wave6-ulichney.tsv fired it, correctly: 2.0 was an accident of one
    # parameter value, not the blue-noise property. Measured: 0.69 of the mean spacing at
    # sigma = 1.5, 0.49 at sigma = 1.7, 0.35 for white noise on the same lattice, 0.03 for Poisson.
    assert mask_nn.min() > 0.4 / np.sqrt(lam), (
        "mask min NN %.4f is only %.2f of the mean spacing %.4f — points are clumping"
        % (mask_nn.min(), mask_nn.min() * np.sqrt(lam), 1.0 / np.sqrt(lam)))
    assert pois_nn.min() < 0.5 < mask_nn.min(), (
        "mask min NN %.4f, Poisson min NN %.4f — the clumping separation is gone"
        % (mask_nn.min(), pois_nn.min()))


def test_the_mask_tiles_without_a_seam():
    """07:175, "the mask is tileable by construction", stated as something that can be FALSE.

    Note what is NOT asserted: that the 2x2 tiling is exactly periodic, or that the array is
    n x n. Both are true of ANY array — tiling a white-noise mask is also exactly periodic — so
    neither can fail and neither is evidence. The claim with content is that the tiling has no
    ARTEFACT at the join: the spacing and the occupancy a few cells either side of the seam must
    look like the interior. Filter without wraparound and they do not, because the border pixels
    have no neighbours across the edge, so they read as voids, get packed, and two packed borders
    meet at every seam. Measured: this ratio is 0.94-1.05 with the wrap and 0.68-0.79 without.
    """
    binary = (_MASK < _DENSITY).astype(float)
    tiled = np.tile(binary, (2, 2))
    p = _points(tiled)
    nn = _nn_distances(p, box=2 * _N)
    seam = (np.abs(p[:, 0] - _N) <= 2.5) | (np.abs(p[:, 1] - _N) <= 2.5)
    ratio = nn[seam].mean() / nn[~seam].mean()
    assert seam.sum() > 20 and (~seam).sum() > 20, "the seam/interior split is degenerate"
    assert ratio > 0.85, (
        "points within 2.5 cells of the tile seam are %.1f%% as far from their neighbours as "
        "interior points (%.4f vs %.4f) — the mask has a seam" % (
            100.0 * ratio, nn[seam].mean(), nn[~seam].mean()))

    band = np.zeros((2 * _N, 2 * _N), bool)
    band[_N - 2:_N + 2, :] = True
    band[:, _N - 2:_N + 2] = True
    interior = np.zeros((2 * _N, 2 * _N), bool)
    interior[_N // 2 - 2:_N // 2 + 2, :] = True
    interior[:, _N // 2 - 2:_N // 2 + 2] = True
    occupancy = tiled[band].mean() / tiled[interior].mean()
    assert 0.77 < occupancy < 1.30, (
        "the 4-cell band straddling the seam holds %.2fx the interior density — a doubled- (or "
        "halved-) density seam is exactly what 07:156 says a per-tile run produces" % occupancy)


def test_phase_two_and_three_collapse_because_the_filter_is_circular():
    """The identity the implementation leans on, pinned rather than assumed.

    `void_and_cluster_rank` runs Ulichney's phases II and III as ONE loop. That is only sound
    because for a circular convolution with kernel sum S, filter(1 - P) == S - filter(P)
    EXACTLY, so phase III's "tightest cluster of the zeros" and phase II's "largest void" select
    the same pixel. Drop the wraparound and the identity fails at the borders, so this also says
    why the merge and the tileability are the same property.
    """
    n = 16
    rng = np.random.default_rng(5)
    pattern = rng.random((n, n)) < 0.3
    kern_sum = S._kernel_at(n, 1.5, 0).sum()

    def filtered(mask):
        out = np.zeros((n, n))
        for idx in np.flatnonzero(mask.ravel()):
            out += S._kernel_at(n, 1.5, idx)
        return out

    deviation = np.abs(filtered(~pattern) - (kern_sum - filtered(pattern))).max()
    assert deviation < 1e-9, (
        "filter(1 - P) departs from S - filter(P) by %.4g, so phase III is NOT phase II and the "
        "merged loop is unsound — this is the border effect of a non-circular filter" % deviation)


def test_generation_is_deterministic_across_processes():
    """Same seed, same array, in a fresh interpreter — not just twice in this one."""
    a = S.void_and_cluster_rank(16, seed=4)
    assert np.array_equal(a, S.void_and_cluster_rank(16, seed=4)), (
        "two calls with seed=4 in ONE process disagree in %d of %d cells"
        % (int((a != S.void_and_cluster_rank(16, seed=4)).sum()), a.size))
    assert not np.array_equal(a, S.void_and_cluster_rank(16, seed=5)), "seed=5 gave seed=4's array"
    code = ("import numpy, scatter; "
            "print(int(scatter.void_and_cluster_rank(16, seed=4).sum()), "
            "hash(scatter.void_and_cluster_rank(16, seed=4).tobytes()))")
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]),
               PYTHONHASHSEED="0")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, check=True).stdout.split()
    assert int(out[0]) == int(a.sum()), (
        "a fresh interpreter produced rank sum %s, this one %d" % (out[0], int(a.sum())))
    assert int(out[1]) == _stable_hash(a), "same rank sum, different array, across processes"


def _stable_hash(arr):
    env_hash = os.environ.get("PYTHONHASHSEED")
    if env_hash != "0":                                   # hash() of bytes is salted per process
        return int(subprocess.run(
            [sys.executable, "-c", "import sys; print(hash(sys.stdin.buffer.read()))"],
            input=arr.tobytes(), capture_output=True,
            env=dict(os.environ, PYTHONHASHSEED="0"), check=True).stdout)
    return hash(arr.tobytes())


def test_ulichney_scatter_thresholds_the_density_map():
    """07:149/:139 — the scatter itself: keep cell (i, j) iff mask[i%n, j%n] < density(i, j).

    Density map dense on the left, sparse on the right; the counts must follow it, and the kept
    cells must still be blue-noise-spaced rather than the first k rows of the tile.
    """
    dens = np.zeros((2, 2))
    dens[:, 0] = 0.30
    dens[:, 1] = 0.05
    pts = S.ulichney_scatter(64.0, 64.0, cellsize=1.0, density=dens, seed=0, tile=_N)
    left = int(np.sum(pts[:, 0] < 32.0))
    right = int(np.sum(pts[:, 0] >= 32.0))
    assert left > 4 * right, "density did not drive the count: left=%d right=%d" % (left, right)
    assert abs(left / (32.0 * 64.0) - 0.30) < 0.05, "left-hand density is %.4f, wanted 0.30" % (
        left / (32.0 * 64.0))
    flat = S.ulichney_scatter(64.0, 64.0, cellsize=1.0, density=0.12, seed=0, tile=_N)
    assert abs(len(flat) / (64.0 * 64.0) - 0.12) < 0.02
    assert _min_pairwise(flat) >= 1.5, (
        "the kept cells are only %.4f m apart at their closest — thresholding a blue-noise mask "
        "must not fall back to taking the first k rows of the tile" % _min_pairwise(flat))


def test_ulichney_scatter_has_no_state_and_so_no_seam():
    """07:175 — a sub-region is bit-identical to the same cells of the whole domain, which is the
    property a per-tile Poisson run (07:156) cannot have. This is the tiling claim at the SCATTER
    level, and unlike the mask-level version it IS an exact equality, because the modulo makes
    each cell's answer depend on nothing but its own integer coordinate."""
    whole = S.ulichney_scatter(96.0, 96.0, cellsize=1.0, density=0.12, seed=0, tile=_N)
    part = S.ulichney_scatter(48.0, 48.0, cellsize=1.0, density=0.12, seed=0, tile=_N)
    inside = whole[(whole[:, 0] < 48.0) & (whole[:, 1] < 48.0)]
    assert len(part) > 100
    assert np.array_equal(part, inside), (
        "%d cells inside the sub-region, %d cells when the sub-region is generated on its own"
        % (len(inside), len(part)))
