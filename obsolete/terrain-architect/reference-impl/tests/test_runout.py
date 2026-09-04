import numpy as np
import runout


def _ramp_then_flat(H, drop_per_cell, n=5, m=90):
    """h decreases by drop_per_cell each column until it hits 0, then stays flat.
    Constant in i, so steepest descent runs straight along +j (horizontal dist = j*cellsize)."""
    j = np.arange(m)[None, :]
    h1d = np.maximum(H - j * drop_per_cell, 0.0)
    return np.repeat(h1d, n, axis=0)


def test_runout_matches_angle_of_reach():
    """Pure-Coulomb limit (xi huge): total horizontal runout D = H/mu, i.e. reach angle
    alpha with tan(alpha) = mu (Corominas 1996). Start from rest at the crest."""
    H, drop, mu, cs = 5.0, 0.5, 0.1, 1.0
    h = _ramp_then_flat(H, drop, m=120)
    track = runout.voellmy_runout(h, start=(2, 0), mu=mu, xi=1e9, cellsize=cs, v0=0.0)
    D = (track[-1][1] - track[0][1]) * cs             # horizontal distance travelled
    expected = H / mu                                 # = 50
    assert abs(D - expected) < 2.0 * cs               # within a cell of the analytic reach


def test_higher_friction_shortens_runout():
    H, drop, cs = 5.0, 0.5, 1.0
    h = _ramp_then_flat(H, drop, m=120)
    far = runout.voellmy_runout(h, (2, 0), mu=0.1, xi=1e9, cellsize=cs)[-1][1]
    near = runout.voellmy_runout(h, (2, 0), mu=0.2, xi=1e9, cellsize=cs)[-1][1]
    assert near < far                                  # more friction -> shorter runout


def test_stops_on_a_flat_from_initial_velocity():
    """On a flat with turbulent drag negligible, a moving mass decelerates at mu*g and
    stops after D = v0^2 / (2 mu g)."""
    h = np.zeros((5, 200))
    mu, g, v0, cs = 0.1, 9.81, 10.0, 1.0
    track = runout.voellmy_runout(h, (2, 0), mu=mu, xi=1e12, cellsize=cs, g=g, v0=v0)
    D = (track[-1][1] - track[0][1]) * cs
    expected = v0 * v0 / (2 * mu * g)                  # ~ 50.97 m
    assert abs(D - expected) < 2.0 * cs
