"""Oracle/invariant tests for glacial erosion (glacier.py / 12).

Illustrative-morphological tier: the SIA ice flow is the Halfar-validated transport of
`sims_illustrative.glacier_sia`; the bed erosion (glacierStep step 4, Argudo 2020) is held to
invariants, not a certified erosion-rate oracle. Checked: it reduces to the ice-only sim when K_g=0;
it only ever carves (never raises); erosion is confined to the ice (bare ground stays pristine); the
eroded volume is conserved into the moraine field; and thick trunk ice erodes far more than thin ice
(the arête / hanging-valley result). The idealised parabolic U is an L-tier emergent form, NOT
asserted here."""
import numpy as np

import glacier
import sims_illustrative as sims


def _capped(n=50):
    """A radial ice CAP (beta=0: ice only flows and thins) on a gently tilted bed. The cap stays
    well inside the domain, so the corners are a guaranteed never-glaciated region."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bed = 1500.0 - 6.0 * yy + 3.0 * np.abs(xx - n / 2)
    H0 = np.maximum(260.0 - 16.0 * np.hypot(xx - n / 2, yy - n / 2), 0.0)   # radius ~16 cells
    return bed, H0


def _valley(n=50):
    """A steep regional slope with a V cross-section: the top accumulates a trunk glacier, the lower
    slope is an ablation zone. Grown from zero ice by mass balance."""
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    bed = 2600.0 - 40.0 * yy + 16.0 * np.abs(xx - n / 2)
    return bed, np.zeros((n, n))


_CAP = dict(beta=0.0, K_g=3e-3, dt=40.0)
_VAL = dict(ela=1700.0, beta=0.004, b_max=0.5, K_g=1e-3, dt=50.0)


def test_transport_reduces_to_glacier_sia_when_not_carving():
    """With K_g=0 and no mass balance, glacier_carve's ice evolution equals glacier_sia's exactly
    (identical SIA transport) and the bed is untouched — carving is a strict ADD-ON."""
    n = 40
    bed, H0 = _capped(n)
    bed = np.zeros((n, n))
    Hs = sims.glacier_sia(bed, H0, 6, A=2.4e-24, dt=1.0e6, cellsize=100.0, beta=0.0)
    bc, Hc, mor = glacier.glacier_carve(bed, H0, 6, A=2.4e-24, dt=1.0e6, cellsize=100.0,
                                        beta=0.0, K_g=0.0)
    assert np.allclose(Hs, Hc)
    assert np.array_equal(bc, bed)
    assert mor.sum() == 0.0


def test_carve_only_and_mass_budget():
    """The bed is only ever LOWERED, and every metre removed is accounted for in the moraine field."""
    bed0, ice0 = _capped()
    bed, H, moraine = glacier.glacier_carve(bed0, ice0, 8, **_CAP)
    assert np.all(bed <= bed0 + 1e-9)                            # carve-only
    assert abs((bed0 - bed).sum() - moraine.sum()) < 1e-3       # eroded volume == moraine


def test_erosion_confined_to_the_ice():
    """The ice cap never reaches the domain corners, so those must be pristine — glacial erosion is
    confined to the ice, it does not touch bare ground."""
    bed0, ice0 = _capped()
    bed, H, moraine = glacier.glacier_carve(bed0, ice0, 8, **_CAP)
    ero = bed0 - bed
    corners = np.concatenate([ero[:6, :6].ravel(), ero[:6, -6:].ravel(),
                              ero[-6:, :6].ravel(), ero[-6:, -6:].ravel()])
    assert corners.max() < 1e-6


def test_thick_ice_erodes_more_than_thin_ice():
    """The H^(n+1) velocity law concentrates erosion under thick trunk ice — deep valleys deepen,
    thin-ice margins barely erode. This differential is what produces arêtes and hanging valleys."""
    bed0, ice0 = _valley()
    bed, H, moraine = glacier.glacier_carve(bed0, ice0, 8, **_VAL)
    ero = bed0 - bed
    thick = H > 0.5 * H.max()
    thin = (H > 3.0) & (H < 0.2 * H.max())
    assert ero[thick].mean() > 5.0 * (ero[thin].mean() + 1e-9)


def test_wall_abrasion_removes_more_and_stays_carve_only():
    """The optional F-tier trough-widener lowers oversteepened walls under ice: it removes MORE bed
    than abrasion alone, stays carve-only, and never touches the never-glaciated corners."""
    bed0, ice0 = _capped()
    _, _, m0 = glacier.glacier_carve(bed0, ice0, 8, wall_abrasion=0.0, **_CAP)
    bed_w, H_w, m_w = glacier.glacier_carve(bed0, ice0, 8, wall_abrasion=5e3, **_CAP)
    ero_w = bed0 - bed_w
    corners = np.concatenate([ero_w[:6, :6].ravel(), ero_w[-6:, -6:].ravel()])
    assert m_w.sum() > m0.sum()                                 # walls additionally lowered
    assert np.all(bed_w <= bed0 + 1e-9)                         # still carve-only
    assert corners.max() < 1e-6                                 # never-glaciated corners still pristine
    assert np.isfinite(bed_w).all()
