"""Domain-boundary oracles (03 *Domain boundaries*, 09).

What the domain edge does to a simulation is a decision, and the default -- a uniform open
perimeter, every edge cell an outlet -- prints a fringe of edge-perpendicular gullies and a
dome. These tests give that artefact a NUMBER (`asserts.boundary_influence_distance`, the knee
of the inset-ring profile) and then pin the number against both controls 09 demands: a field
with no boundary signature, where the metric must read 0, and an analytic case where the
influence distance is known in closed form.
"""
import numpy as np
import asserts
import inputs
import erosion_streampower as SP


def _dirichlet_diffuse(h, D, dt, iters, cellsize=1.0):
    """Explicit hillslope diffusion with FIXED-VALUE (Dirichlet) edges -- the open perimeter.

    `diffusion.hillslope_diffuse` is periodic (a torus has no edge, so no signature to find);
    this is the same 5-point stencil with the boundary ring pinned, which is the boundary
    condition fastscapelib's ADI path takes and the one that carries the artefact (04).
    """
    h = np.asarray(h, dtype=np.float64).copy()
    edge = h.copy()
    c = D * dt / (cellsize * cellsize)
    for _ in range(int(iters)):
        lap = np.zeros_like(h)
        lap[1:-1, 1:-1] = (-4.0 * h[1:-1, 1:-1]
                           + h[:-2, 1:-1] + h[2:, 1:-1]
                           + h[1:-1, :-2] + h[1:-1, 2:])
        h = h + c * lap
        h[0, :], h[-1, :], h[:, 0], h[:, -1] = edge[0, :], edge[-1, :], edge[:, 0], edge[:, -1]
    return h


# --------------------------------------------------------------------------- #
# The negative control: no edge policy, no signature.

def test_field_with_no_edge_influence_reads_zero():
    """09's rule that a metric needs a case which must FAIL. Interior noise on a flat field has
    no edge-referenced structure, so the knee must be 0 -- otherwise the metric is reading its
    own ring-binning noise and every later number it produces is meaningless."""
    rng = np.random.default_rng(0)
    h = inputs.flat(n=96) + rng.normal(0.0, 1.0, (96, 96))
    assert asserts.boundary_influence_distance(h) == 0


def test_periodic_domain_has_no_signature():
    """A torus has no edge. Diffusing the same field periodically leaves nothing for the
    boundary metric to find -- the control that separates 'the edge did something' from
    'the simulation did something'."""
    import diffusion
    rng = np.random.default_rng(1)
    h0 = inputs.flat(n=96, value=1.0) + rng.normal(0.0, 0.01, (96, 96))
    h = diffusion.hillslope_diffuse(h0, D=1.0, dt=0.2, iters=100)
    assert asserts.boundary_influence_distance(h) == 0


# --------------------------------------------------------------------------- #
# The analytic control: the knee IS the diffusion length.

def test_dirichlet_diffusion_knee_matches_the_diffusion_length():
    """The oracle that makes the metric usable for margin sizing. A plateau held at 0 on its
    perimeter relaxes inward as an error function, so the boundary's reach is the diffusion
    length sqrt(4*D*t) -- known in closed form. The measured knee must land on it.

    This is the whole argument for measuring a margin instead of guessing one: the number the
    metric returns is a real length scale, not an artefact of the binning.
    """
    D, dt, iters = 1.0, 0.2, 100
    t = dt * iters
    length = np.sqrt(4.0 * D * t)                          # ~8.9 cells

    h0 = np.ones((96, 96))
    h0[0, :] = h0[-1, :] = h0[:, 0] = h0[:, -1] = 0.0      # perimeter at base level
    h = _dirichlet_diffuse(h0, D=D, dt=dt, iters=iters)

    knee = asserts.boundary_influence_distance(h)
    assert 0.5 * length < knee < 3.0 * length, (
        f"knee {knee} cells vs diffusion length {length:.1f} -- the metric is not measuring "
        "the boundary's actual reach")


def test_diffusion_influence_grows_as_sqrt_of_time():
    """The same oracle differenced: run 4x longer and the reach must grow ~2x, not 4x. A knee
    that scaled linearly would mean the metric is tracking the front's numerical spread (1 cell
    per iteration) rather than the physical length scale."""
    def knee_after(iters):
        h = np.ones((160, 160))
        h[0, :] = h[-1, :] = h[:, 0] = h[:, -1] = 0.0
        return asserts.boundary_influence_distance(
            _dirichlet_diffuse(h, D=1.0, dt=0.2, iters=iters))

    short, long = knee_after(60), knee_after(240)
    assert 1.5 < long / short < 2.8, f"reach scaled {long / short:.2f}x for 4x time, expected ~2x"


# --------------------------------------------------------------------------- #
# The positive control: the artefact, in the sim that actually produces it.

def test_open_perimeter_stream_power_shows_the_ramp():
    """09's positive control for the domain edge: uniform uplift on a square with every edge
    open, run toward steady state, MUST show the boundary ramp -- `erosion_streampower` holds
    its edges at base level, which is exactly the uniform open perimeter.

    A metric that cannot see it here is not measuring anything (03).
    """
    n = 48
    rng = np.random.default_rng(2)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    h = SP.stream_power_evolve(h0, uplift=1.0, K=1.0, m_exp=0.5, dt=2.0, iters=300)

    asserts.assert_finite(h)
    prof = asserts.boundary_influence_profile(h)
    assert prof[0] < prof[-1], "no ramp: the open perimeter left no signature at all"

    # Monotone across the outer half only. Ring k holds 4*(n-1-2k) cells, so the innermost few
    # rings are a handful of cells each and their means wobble -- and the crest sits wherever the
    # network put the divide, not exactly at the centre. The ramp is the claim; the crest is not.
    ramp = prof[:len(prof) // 2]
    assert np.all(np.diff(ramp) > -1e-9), "the boundary ramp is not monotone inward"
    assert ramp[-1] - ramp[0] > 0.5 * (prof.max() - prof.min()), "ramp too weak to be the dome"


def test_stream_power_boundary_reach_is_not_bounded():
    """The caveat the doctrine rests on (03, fix 1). A margin removes the boundary's TEXTURE
    because that reach is bounded -- but for stream power `A` is global, so the SHAPE the edge
    imposes spans the domain. The knee must therefore sit deep inside, not in a thin outer band:
    cropping a margin relocates this dome's crest, it does not abolish it.

    If this ever fails, fix 1 in 03 is overclaiming and the text needs correcting with it.
    """
    n = 48
    rng = np.random.default_rng(3)
    h0 = rng.uniform(0.0, 1.0, (n, n)) * 0.05
    h = SP.stream_power_evolve(h0, uplift=1.0, K=1.0, m_exp=0.5, dt=2.0, iters=300)

    knee = asserts.boundary_influence_distance(h)
    assert knee > 0.25 * (n // 2), (
        f"knee {knee} of a {n // 2}-cell half-width reads as a thin edge band; stream power's "
        "boundary influence is supposed to be unbounded (08)")
