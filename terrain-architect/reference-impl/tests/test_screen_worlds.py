"""Invariant checks for the screen-world compositions (screen_worlds.py) — fictional planets as
re-dressed Earth archetypes. Same discipline as the archetypes: finite, bounded (nothing blows up),
plus the couple of tells that make each recognisable. Low resolution for speed."""
import numpy as np

import screen_worlds as S

N = 48


def test_screen_worlds_all_finite_and_not_blown_up():
    for label, fn, *_ in S.SCREEN:
        h = fn(n=N)
        assert h.shape == (N, N), label
        assert np.all(np.isfinite(h)), label
        assert 0.0 < (h.max() - h.min()) < 5e4, f"{label}: relief {(h.max() - h.min()):.2e} — blown up?"


def test_screen_world_signatures():
    # drowned worlds: the sea (z<0) actually invades
    assert (S.skull_island(n=N) < 0.0).any()          # Ha Long towers stand IN the sea
    assert (S.miller(n=N) < 0.0).any()                # a shoreless shallow ocean

    # Crait / Salar de Uyuni — a dead-flat playa
    c = S.crait(n=N)
    assert (c.max() - c.min()) < 20.0

    # Monument Valley — buttes stand well above the plain
    assert (S.monument_valley(n=N).max() - S.monument_valley(n=N).min()) > 120.0

    # Miller's world — a mountainous tidal wave rises above the shallow seabed
    assert S.miller(n=N).max() > 60.0


def test_screen_worlds_render_photoreal():
    """Each world renders to a valid, non-flat RGB tile through the shared photoreal composite
    (or its snow/salt custom); drowned worlds come out predominantly blue."""
    for label, fn, family, sea in S.SCREEN:
        img = S._render(fn(n=N), family, sea)
        assert img.shape == (N, N, 3) and img.dtype == np.uint8, label
        assert int(img.reshape(-1, 3).std(axis=0).sum()) > 3, f"{label}: render is a flat colour"
    sea_img = S._render(S.skull_island(n=N), "temperate", True)   # Ha Long: mostly sea
    r, g, b = sea_img.reshape(-1, 3).mean(0)
    assert b > r and b > g, "drowned coast should read blue"


# =========================================================================================== #
# The `09` signature bands for the screen worlds, AT THE FIGURE'S OWN TILE SIZE
#
# WHAT WENT WRONG. `screen_worlds.main()` printed one number per world (relief) and returned
# nothing, and the only assertion on any of them was `monument_valley relief > 120.0` at line 29
# -- run at N=48 while the figure renders at TILE=96. Monument Valley's relief then moved
# 259 -> 268 m between two CI runners and sat 130 m deep inside that band; the drift was caught
# only by the pixel-exact rebuild in `tools/regen_figures.py`, which is unsound across machines
# and has been retired for this figure (`INVARIANT_GATED["screen_worlds"]` names THIS file as
# what guards it instead).
#
# THE MECHANISM AND THE DERIVATION are one story shared with `tests/test_archetypes.py`, whose
# header carries it in full: numpy's transcendental ufunc loops (pow/exp/log1p/tan/arctan) differ
# by exactly 1 ULP between SIMD dispatch levels, `erosion_droplet.droplet_erode` amplifies that by
# ~1e14 through discrete steepest-descent ties, and running this repo with AVX512 enabled vs
# disabled reproduces both published CI runs exactly -- Monument Valley relief 258.60 (AVX512) /
# 267.64 (AVX2) against the reported 259 / 268. Each band below is
#     [min(46 samples) * 0.98, max(46 samples) * 1.02]
# rounded outward to 4 significant figures, where the samples are 44 Monte-Carlo trials that nudge
# every noise result and every droplet input by a random -1/0/+1 ULP, plus the two real dispatch
# regimes; the 2% margin is the largest measured residual under-coverage (1.9351%) rounded up.
#
# ⚠️ WOULD THESE BANDS HAVE CAUGHT THE OBSERVED DRIFT? No -- and that is the finding, not a
# shortfall in the derivation. A guard has to be green on both runners, so it cannot tell them
# apart:
#     Monument Valley relief  drift  3.43%   band +- 5.09%   NOT caught
#     Monument Valley HI      drift  8.26%   band +- 9.09%   NOT caught
#     Monument Valley pit     drift 18.01%   band +-22.34%   NOT caught
#     Beggar's Canyon pit     drift 20.52%   band +-56.24%   NOT caught
# Monument Valley and Beggar's Canyon erode with `k * n` droplets and their pit-storage cannot be
# guarded tightly at any tolerance an honest measurement supports. The other six worlds have no
# chaotic amplifier -- measured envelope ~1e-13% of value -- and close to +-2%.
#
# Rows are (relief_m, p99_slope_deg, hypsometric_integral, pit_storage_m3), each a (lo, hi).
# =========================================================================================== #
N_FIG = S.TILE                       # 96 -- the figure's own tile size, not the cheaper N=48

BANDS = {
    "Arrakis (Wadi Rum)":      ((610.9, 635.9), (81.52, 84.86), (0.541, 0.5632), (2.833e+06, 3.027e+06)),
    #   1-ULP envelope, % of value: 1.124e-08 0.003652 9.116e-09    2.615
    "Monument Valley":         ((253.4, 280.6), (71.67, 74.73), (0.2759, 0.3311), (3.835e+05, 6.042e+05)),
    #   1-ULP envelope, % of value:    6.164   0.1742    14.18    40.85
    "Pandora (Zhangjiajie)":   ((460.5, 479.4), (82.06, 85.42), (0.5096, 0.5305), (4.28e+07, 4.456e+07)),
    #   1-ULP envelope, % of value:        0        0 8.54e-14 4.947e-13
    "Hoth (Norway ice)":       ((646.5, 673), (71.26, 74.18), (0.2786, 0.2901), (1.284e+07, 1.337e+07)),
    #   1-ULP envelope, % of value: 3.446e-14 3.908e-14 7.809e-14 1.99e-13
    "Skull Is. (Ha Long)":     ((303.8, 316.2), (82.29, 85.66), (0.06997, 0.07283), (79250, 82500)),
    #   1-ULP envelope, % of value:        0 1.692e-14 2.916e-13 9.537e-13
    "Beggar's Canyon":         ((273.9, 309.8), (68.96, 73.25), (0.7285, 0.7774), (1.954e+06, 6.976e+06)),
    #   1-ULP envelope, % of value:    8.293    2.018     2.48    109.7
    "Crait (Salar Uyuni)":     ((3.92, 4.08), (0.8757, 0.9116), (0.5162, 0.5374), (5.45e+05, 5.674e+05)),
    #   1-ULP envelope, % of value:        0 2.36e-13        0 1.675e-13
    "Miller's world (sandur)": ((111.3, 116), (50.79, 52.87), (0.09447, 0.09834), (2.365e+05, 2.463e+05)),
    #   1-ULP envelope, % of value:        0 1.371e-14        0 4.822e-14
}

_SIG_CACHE = {}


def _sig():
    if not _SIG_CACHE:
        _SIG_CACHE.update(S.signatures(n=N_FIG, cell=S.CELL))
    return _SIG_CACHE


def test_signature_bands_cover_every_screen_world():
    """The denominator: 8 worlds in SCREEN, 8 rows here, no extras."""
    labels = [label for label, _, _, _ in S.SCREEN]
    assert sorted(BANDS) == sorted(labels), (
        f"unbanded: {sorted(set(labels) - set(BANDS))}; stale: {sorted(set(BANDS) - set(labels))}")
    for label, row in BANDS.items():
        assert len(row) == 4, label
        for lo, hi in row:
            assert lo < hi, label


def test_signatures_defaults_to_the_figure_tile_size():
    """`S.signatures()` must default to the size `screen_worlds.png` renders at: `arrakis` and
    `monument_valley` erode with `k * n` droplets, so 48 is a different run from the figure's."""
    assert N_FIG == S.TILE == 96
    assert S.signatures.__defaults__[0] == S.TILE


def test_screen_world_signatures_within_measured_bands_at_figure_resolution():
    """Every world's four `09` numbers at TILE=96, inside a band derived from the measured
    +-1 ULP envelope. This is what replaces the pixel-exact rebuild for `screen_worlds.png`."""
    sig = _sig()
    keys = ("relief_m", "p99_slope_deg", "hypsometric_integral", "pit_storage_m3")
    for label, row in BANDS.items():
        f = sig[label]
        for (lo, hi), key in zip(row, keys):
            v = f[key]
            assert lo <= v <= hi, (
                f"{label}: {key} = {v:.6g} is outside its measured band [{lo:.6g}, {hi:.6g}] "
                f"({(v - (lo + hi) / 2) / ((lo + hi) / 2) * 100:+.2f}% from band centre)")


def test_monument_valley_relief_is_guarded_narrowly_not_by_a_floor():
    """The specific hole this figure fell through. `assert relief > 120.0` passed a 259 -> 268 m
    move with 130 m to spare. The band is two-sided and 27 m wide, so a change that leaves the
    butte-series recognisable but resizes it is now visible -- and it is checked at 96, where the
    figure lives, not at 48."""
    lo, hi = BANDS["Monument Valley"][0]
    assert hi - lo < 30.0, "the Monument Valley relief band has been widened past its derivation"
    relief = _sig()["Monument Valley"]["relief_m"]
    assert lo <= relief <= hi, f"Monument Valley relief {relief:.1f} m outside [{lo}, {hi}]"
