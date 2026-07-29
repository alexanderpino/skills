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
