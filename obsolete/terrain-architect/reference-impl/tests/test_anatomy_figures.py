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


def test_crater_anatomy_builds_and_still_draws_the_uprange_asymmetry(tmp_path):
    """`VALIDATION.md` rung 4 stakes a corrected morphology on this figure — a grazing impact is
    deeper UP-RANGE (first contact / peak energy; Schultz / Anderson et al., arXiv 2308.01876), not
    down-range — and the figure was the only artifact carrying that claim with no build guard in
    any environment. It could stop building, or start drawing the deepest point down-range again
    (the exact defect rung 4 corrected), and nothing would fail.

    WHAT THIS ADDS OVER `test_crater.test_grazing_crater_is_deeper_uprange`, which is the MODEL's
    oracle: that one calls `crater_demo.stamp_impact_natural` directly at angle=3 deg on a 400-cell
    grid and reads a 3-row mean. The FIGURE runs different parameters (angle=2 deg, N=460, its own
    cellsize, a 5-row mean, seed 5) and then draws a "deepest = UP-RANGE" leader at the column it
    found. A morphology that survives one parameter set and not the other would leave the picture
    captioning itself wrongly with the model oracle still green, so the figure asserts its own
    numbers. `build()` returns them for exactly this reason rather than making a guard re-derive
    them from pixels.

    NO TIGHTER BOUND THAN THE SIGN IS PINNED on how far up-range the floor sits (it is 14 columns
    of 460 on the shipped parameters). The angle, grid size and seed here are presentational and a
    later figure may legitimately move them; the SIDE OF CENTRE is the claim the document makes.
    What is pinned alongside it is that the deepest point lies between the two rim crests — i.e.
    inside the cavity, so the row is reading the crater floor and not a notch in the ejecta.
    """
    import crater_anatomy
    out = tmp_path / "crater_anatomy.png"
    img, facts = crater_anatomy.build(str(out))
    assert out.exists() and out.stat().st_size > 0, "the figure did not reach disk"
    assert img.size[0] > 900 and img.size[1] > 700

    assert facts["deepest_col"] < facts["centre"], (
        "the trajectory cross-section's deepest point is no longer up-range (col %d vs centre %d): "
        "that is the rung-4 defect returning, and the figure's own 'deepest = UP-RANGE' leader now "
        "points at a down-range column while VALIDATION.md rung 4 still claims the correction"
        % (facts["deepest_col"], facts["centre"]))
    assert facts["uprange_rim_col"] < facts["deepest_col"] < facts["downrange_rim_col"], (
        "the deepest column (%d) is outside the rim crests (%d..%d), so the cross-section's minimum "
        "is not the crater floor — the figure would be labelling the wrong feature"
        % (facts["deepest_col"], facts["uprange_rim_col"], facts["downrange_rim_col"]))
    assert facts["ellipticity"] > 1.5, (
        "a grazing cavity is elongated along the track, not circular (ellipticity %.2f); the map "
        "panel's 'broken ellipse' and its up-range/down-range leaders assume it"
        % facts["ellipticity"])
