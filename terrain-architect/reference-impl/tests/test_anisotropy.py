"""The rotation test that separates LATTICE anisotropy from FIELD anisotropy (`09`).

"Anisotropy" names two different things and the skill's position is that they must never be
conflated: the lattice printing through the discretisation (always a defect, the direction
belongs to the array) versus real directional structure carried by a field (strike/dip, wind,
ice flow — legitimate, the direction belongs to a cause). The discriminator is equivariance
under rotation: rotate the domain, run the operator, rotate back, and compare. Physical
anisotropy rotates with the terrain; lattice anisotropy stays welded to the axes.

The operators come from `anisotropy_anatomy.py`, so this guards exactly what the figure draws.
It pins the two claims `09` quotes: the separation is about an order of magnitude against an
isotropic control, and a 90-degree rotation is a SYMMETRY of the square lattice, so testing at
90 degrees reports a perfect score for an operator that is grossly axis-locked.
"""
import math

import numpy as np

from anisotropy_anatomy import (N, _X, _Y, _xx, _yy, axis_locked, cone, error, field_smear,
                                isotropic, rotate)


def test_rotation_separates_lattice_anisotropy_from_the_interpolation_floor():
    """At an angle that is NOT a lattice symmetry, an axis-locked operator scores about an
    order of magnitude worse than the isotropic control that measures the noise floor."""
    for deg in (23, 30, 45):
        th = math.radians(deg)
        locked, floor = error(axis_locked, th), error(isotropic, th)
        assert floor < 0.03, f"control floor unexpectedly high at {deg} deg: {floor:.4f}"
        assert locked > 0.07, f"axis-locked operator scored clean at {deg} deg: {locked:.4f}"
        assert locked > 5 * floor, f"separation collapsed at {deg} deg: {locked:.4f} vs {floor:.4f}"


def test_ninety_degrees_is_a_lattice_symmetry_and_hides_the_defect():
    """THE TRAP. 90 degrees maps the square lattice onto itself, so a grossly axis-locked
    operator is exactly equivariant under it and the test reports a perfect score. The angle
    must not be a symmetry of the lattice under test (90 deg for square, 60 deg for hex)."""
    err = error(axis_locked, math.radians(90))
    assert err < 1e-12, f"expected exact equivariance at 90 deg, got {err:.3e}"
    # ...while the very same operator fails plainly at 30 degrees:
    assert error(axis_locked, math.radians(30)) > 0.07


def test_field_carried_anisotropy_tracks_the_control_not_the_lattice():
    """An operator whose direction comes from a FIELD is equivariant once the field is rotated
    with the terrain — which is the whole distinction, made measurable."""
    th = math.radians(30)
    strike = np.full((N, N), math.radians(20.0))      # a uniform strike field is still a FIELD
    h = cone()
    a = rotate(field_smear(rotate(h, -th), rotate(strike, -th) - th), th)
    b = field_smear(h, strike)
    m = np.hypot(_X, _Y) < N // 3
    field_err = float(np.abs(a - b)[m].mean() / (np.abs(b)[m].mean() + 1e-12))
    locked = error(axis_locked, th)
    assert field_err < locked / 2, (
        f"field-carried anisotropy should track the floor, not the lattice: "
        f"{field_err:.4f} vs axis-locked {locked:.4f}")


def test_the_input_carries_no_direction_of_its_own():
    """The control that makes the whole figure valid: a cone is radially symmetric, so any
    direction in an output was put there by the operator or the grid, never by the input."""
    h = cone()
    for deg in (17, 30, 61):
        r = rotate(h, math.radians(deg))
        m = np.hypot(_X, _Y) < N // 3
        assert np.abs(r - h)[m].mean() / h[m].mean() < 0.01, f"cone not rotation-invariant at {deg}"
