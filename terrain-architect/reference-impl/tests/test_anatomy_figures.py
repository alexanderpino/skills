"""Build guard for the labelled ANATOMY figures (`hex_anatomy.py`, `anisotropy_anatomy.py`).

These are diagrams rather than field renders, so `test_gallery`'s numeric-sanity check does not
apply. What can rot is different and just as silent: a figure that no longer builds after a
refactor, or one whose maths drifts from the chapter it illustrates. So this asserts the figures
construct at the expected size, and — the part that matters — that the geometry they DRAW still
matches the constants the chapters claim.
"""
import math

import numpy as np
import pytest

PIL = pytest.importorskip("PIL", reason="anatomy figures need Pillow")


def test_hex_anatomy_builds():
    import hex_anatomy
    img = hex_anatomy.build()
    assert img.size == (hex_anatomy.PAD * 2 + hex_anatomy.COLS * hex_anatomy.PANEL_W,
                        hex_anatomy.TOP + hex_anatomy.PAD + hex_anatomy.ROWS * hex_anatomy.PANEL_H)
    assert len(hex_anatomy.PANELS) == hex_anatomy.COLS * hex_anatomy.ROWS


def test_hex_anatomy_draws_the_geometry_the_chapter_claims():
    """The figure's own lattice helper must reproduce `26`'s constants — otherwise the diagram
    can drift into illustrating something the text does not say (the failure that made panel c
    necessary in the first place)."""
    import hex_anatomy
    s = 40.0
    centre, corners, cs = hex_anatomy._geom(s)
    assert math.isclose(cs, math.sqrt(3) * s)                       # cellSize = sqrt(3) * s
    o = np.array(centre(0, 0))
    for d in hex_anatomy.NB:                                        # all six neighbours at cellSize
        assert math.isclose(np.linalg.norm(np.array(centre(*d)) - o), cs, rel_tol=1e-9)
    for p in corners(0, 0):                                         # corner ring at radius s
        assert math.isclose(np.linalg.norm(np.array(p) - o), s, rel_tol=1e-9)

    # panel c's whole point: the ARRAY quad is four CENTRES, sqrt(3) larger and turned 30 deg
    # from the rhombille diamond, and is NOT one of them.
    quad = [np.array(centre(*qr)) for qr in [(0, 0), (1, 0), (1, 1), (0, 1)]]
    assert math.isclose(np.linalg.norm(quad[1] - quad[0]), cs, rel_tol=1e-9)     # side = cellSize
    long_d = np.linalg.norm(quad[2] - quad[0])
    assert math.isclose(long_d, math.sqrt(3) * cs, rel_tol=1e-9)                 # long diagonal
    az = math.degrees(math.atan2(*(quad[2] - quad[0])[::-1])) % 180
    assert math.isclose(az, 30.0, abs_tol=1e-6)                                  # turned 30 deg
    ring = {tuple(np.round(np.array(centre(*d)), 9)) for d in hex_anatomy.NB}
    corner_pts = {tuple(np.round(p, 9)) for p in corners(0, 0)}
    assert not (ring & corner_pts)                                  # centres are never corners


def test_anisotropy_anatomy_builds_and_reports_the_trap():
    import anisotropy_anatomy as A
    img = A.build()
    assert img.size[0] > 900 and img.size[1] > 700
    # the figure's captions quote these; keep them true
    assert A.error(A.axis_locked, math.radians(30)) > 0.07
    assert A.error(A.isotropic, math.radians(30)) < 0.03
    assert A.error(A.axis_locked, math.radians(90)) < 1e-12
