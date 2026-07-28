"""The rotation test that separates LATTICE anisotropy from FIELD anisotropy (`09`).

"Anisotropy" names two different things and the skill's position is that they must never be
conflated: the lattice printing through the discretisation (always a defect, the direction
belongs to the array) versus real directional structure carried by a field (strike/dip, wind,
ice flow — legitimate, the direction belongs to a cause). The discriminator is equivariance
under rotation: rotate the domain, run the operator, rotate back, and compare. Physical
anisotropy rotates with the terrain; lattice anisotropy stays welded to the axes.

This file pins the two claims `09` quotes: the separation is about an order of magnitude
against an isotropic control, and a 90-degree rotation is a SYMMETRY of the square lattice, so
testing at 90 degrees reports a perfect score for an operator that is grossly axis-locked.
"""
import math

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

N = 81
C = N // 2
_yy, _xx = np.mgrid[0:N, 0:N].astype(float)
_X, _Y = _xx - C, _yy - C


def _sample(a, sx, sy):
    """Bilinear sample at continuous coordinates. Used by BOTH the rotation and the
    field-carried operator below, so neither is handicapped by a cruder interpolant than the
    other — comparing them otherwise measures the sloppier sampler, not the principle."""
    x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
    fx, fy = sx - x0, sy - y0
    out = np.zeros_like(a)
    for dy in (0, 1):
        for dx in (0, 1):
            xi, yi = np.clip(x0 + dx, 0, N - 1), np.clip(y0 + dy, 0, N - 1)
            out += ((fx if dx else 1 - fx) * (fy if dy else 1 - fy)) * a[yi, xi]
    return out


def _rotate(a, th):
    """Bilinear rotation about the centre. Its interpolation error is the noise floor the
    isotropic control measures — which is exactly why the control is mandatory (`09`: a
    metric with no control is not evidence)."""
    ct, st = math.cos(th), math.sin(th)
    return _sample(a, ct * _X + st * _Y + C, -st * _X + ct * _Y + C)


def _cone():
    """A radially symmetric input has no direction of its own, so any direction in the output
    was put there by the operator or by the grid."""
    return np.maximum(0.0, 20.0 - np.hypot(_X, _Y))


def _axis_locked(h, k=6):
    """4-neighbour max: grows an L1 ball (a diamond) welded to the axes."""
    for _ in range(k):
        h = np.maximum.reduce([h, np.roll(h, 1, 0), np.roll(h, -1, 0),
                               np.roll(h, 1, 1), np.roll(h, -1, 1)])
    return h


def _isotropic(h, k=6):
    """Disc max: the same operation with a radially symmetric structuring element."""
    d = np.hypot(*np.mgrid[-k:k + 1, -k:k + 1]) <= k
    w = sliding_window_view(np.pad(h, k, mode="edge"), (2 * k + 1, 2 * k + 1))
    return (w * d).max(axis=(2, 3))


def _equivariance_error(F, th):
    """||rot(F(rot(h, -th)), th) - F(h)|| / ||F(h)||, measured on the interior."""
    h = _cone()
    a, b = _rotate(F(_rotate(h, -th)), th), F(h)
    m = np.hypot(_X, _Y) < N // 3
    return float(np.abs(a - b)[m].mean() / (np.abs(b)[m].mean() + 1e-12))


def test_rotation_separates_lattice_anisotropy_from_the_interpolation_floor():
    """At an angle that is NOT a lattice symmetry, an axis-locked operator scores about an
    order of magnitude worse than the isotropic control that measures the noise floor."""
    for deg in (23, 30, 45):
        th = math.radians(deg)
        locked = _equivariance_error(_axis_locked, th)
        floor = _equivariance_error(_isotropic, th)
        assert floor < 0.03, f"control floor unexpectedly high at {deg} deg: {floor:.4f}"
        assert locked > 0.07, f"axis-locked operator scored clean at {deg} deg: {locked:.4f}"
        assert locked > 5 * floor, f"separation collapsed at {deg} deg: {locked:.4f} vs {floor:.4f}"


def test_ninety_degrees_is_a_lattice_symmetry_and_hides_the_defect():
    """THE TRAP. 90 degrees maps the square lattice onto itself, so a grossly axis-locked
    operator is exactly equivariant under it and the test reports a perfect score. The angle
    must not be a symmetry of the lattice under test (90 deg for square, 60 deg for hex)."""
    err = _equivariance_error(_axis_locked, math.radians(90))
    assert err < 1e-12, f"expected exact equivariance at 90 deg, got {err:.3e}"
    # ...while the very same operator fails plainly at 30 degrees:
    assert _equivariance_error(_axis_locked, math.radians(30)) > 0.07


def test_field_carried_anisotropy_tracks_the_control_not_the_lattice():
    """An operator whose direction comes from a FIELD is equivariant once the field is
    rotated with the terrain — which is the whole distinction, made measurable."""
    def smear(h, ang, k=6):
        out = h.copy()
        for s in range(1, k + 1):
            out = np.maximum(out, _sample(h, _xx + s * np.cos(ang), _yy + s * np.sin(ang)))
        return out

    th = math.radians(30)
    strike = np.full((N, N), math.radians(20.0))          # a uniform strike field is still a FIELD
    h = _cone()
    a = _rotate(smear(_rotate(h, -th), _rotate(strike, -th) - th), th)
    b = smear(h, strike)
    m = np.hypot(_X, _Y) < N // 3
    field_err = float(np.abs(a - b)[m].mean() / (np.abs(b)[m].mean() + 1e-12))
    locked = _equivariance_error(_axis_locked, th)
    assert field_err < locked / 2, (
        f"field-carried anisotropy should track the floor, not the lattice: "
        f"{field_err:.4f} vs axis-locked {locked:.4f}")
