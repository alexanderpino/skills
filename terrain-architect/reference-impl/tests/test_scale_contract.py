"""Scale contract (08-output-contract.md): atom parameters must not be silently in CELL units.

A cell is not a unit — `cellSize = extent / n` is. An atom that takes a threshold, radius or count
in cells changes meaning whenever the grid changes, which is how a graph that looked right at
preview resolution comes out wrong at build resolution. `erosion_thermal.thermal_erosion` is the
worked example: it takes `repose_slope` (a slope) times `cellsize`, so it encodes an ANGLE.

This is the anti-drift guard for that rule. Every atom in the coverage manifest must either accept
`cellsize`, or be listed below with a REASON it is legitimately grid- or caller-relative. Adding an
atom with cell-unit parameters and no justification fails here.
"""
import importlib
import inspect

import numpy as np
import pytest

from test_atom_coverage import IMPLEMENTED


# Atoms that legitimately do NOT take `cellsize`, grouped by WHY. An atom is scale-explicit if it
# takes cellsize *or* falls in one of these categories — anything else is an unreviewed cell-unit
# parameter and fails the guard.
_CALLER_COORDS = (
    "sampled at caller-supplied coordinate arrays, so every length (frequency, radius, extent) is "
    "already in the caller's units — the grid never enters."
)
_VALUE_ONLY = (
    "a pure value mapping with no spatial extent at all: it transforms numbers, never distances, "
    "so there is nothing for cellsize to scale."
)
_SCALE_FREE = (
    "decided purely by comparison and ordering of elevations; no length scale enters the algorithm, "
    "so the result is identical under any cellsize."
)
PIXEL_OR_CALLER_SPACE = {
    **{("noise", f): _CALLER_COORDS for f in
       ("perlin", "value", "simplex", "worley", "fbm", "ridged_mf", "hybrid_mf",
        "gabor", "domain_warp", "curl")},
    **{("ops_filters", f): _CALLER_COORDS for f in
       ("sd_circle", "sd_box", "sd_convex_polygon", "sd_segment",
        "radial_gradient", "linear_gradient", "cone")},
    **{("ops_filters", f): _VALUE_ONLY for f in
       ("smin", "smax", "blend", "remap", "curve", "levels")},
    **{("placement", f): _VALUE_ONLY for f in ("apply_masked", "stamp")},
    ("flow", "priority_flood_fill"): _SCALE_FREE,
    ("meander", "migrate"):
        "evolves a centreline, not a grid: ds/dt/cutoff_dist are all in the caller's units, so the "
        "result is unit-agnostic; only rasterising it (burn_channel) needs cellsize.",
    ("erosion_droplet", "droplet_erode"):
        "cell-space particle walk (droplets step one cell, brush_radius counts cells). The exposure "
        "is documented on the function and `resolution_matched()` carries settings between grids.",
}


def _atoms():
    for module, names in IMPLEMENTED.items():
        mod = importlib.import_module(module)
        for name in names:
            fn = getattr(mod, name, None)
            if callable(fn):
                yield module, name, fn


def test_every_atom_is_scale_explicit():
    """Each atom takes `cellsize`, or is justified as grid-/caller-relative above."""
    unjustified = []
    for module, name, fn in _atoms():
        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            continue
        if "cellsize" in params:
            continue
        if (module, name) in PIXEL_OR_CALLER_SPACE:
            continue
        unjustified.append(f"{module}.{name}")
    assert not unjustified, (
        "atoms with no `cellsize` and no entry in PIXEL_OR_CALLER_SPACE — either thread cellsize "
        f"through or document why cells are the right unit: {unjustified}"
    )


def test_scale_exemptions_are_real_and_reasoned():
    """The allowlist may not rot: every entry must name a live atom and carry a real reason."""
    known = {(m, n) for m, n, _ in _atoms()}
    for key, reason in PIXEL_OR_CALLER_SPACE.items():
        assert key in known, f"exemption {key} is not an atom in the coverage manifest"
        assert len(reason) > 40, f"exemption {key} needs a real reason, got {reason!r}"


def test_droplet_resolution_matching_scales_density_and_length():
    """Droplet count is a DENSITY (~n^2); brush radius is a LENGTH (~n). Doubling the grid must
    quadruple the droplets and double the brush, or a finer build erodes less and stays rough."""
    import erosion_droplet

    base = dict(n_droplets=20000, brush_radius=2)
    up = erosion_droplet.resolution_matched(base_shape=(256, 256), shape=(512, 512), **base)
    assert up == {"n_droplets": 80000, "brush_radius": 4}
    down = erosion_droplet.resolution_matched(base_shape=(256, 256), shape=(128, 128), **base)
    assert down == {"n_droplets": 5000, "brush_radius": 1}
    same = erosion_droplet.resolution_matched(base_shape=(256, 256), shape=(256, 256), **base)
    assert same == base


def test_droplet_density_matching_holds_erosion_per_unit_area():
    """The behavioural half: matched settings erode a comparable FRACTION of the relief at two
    resolutions, where reusing the raw count does not."""
    import erosion_droplet
    import ops_filters

    rng = np.random.default_rng(0)
    coarse = ops_filters.gaussian(rng.random((64, 64)) * 10.0, sigma=2.0)
    fine = ops_filters.resample(coarse, (128, 128))

    def eroded_fraction(h, **kw):
        out = erosion_droplet.droplet_erode(h, seed=1, **kw)
        return float(np.abs(out - h).mean() / max(np.ptp(h), 1e-9))

    base = dict(n_droplets=4000, brush_radius=2)
    f_coarse = eroded_fraction(coarse, **base)
    f_naive = eroded_fraction(fine, **base)                       # same count on 4x the cells
    f_matched = eroded_fraction(
        fine, **erosion_droplet.resolution_matched(base_shape=coarse.shape, shape=fine.shape, **base))

    assert abs(f_matched - f_coarse) < abs(f_naive - f_coarse), (
        f"matching did not help: coarse={f_coarse:.4f} naive={f_naive:.4f} matched={f_matched:.4f}")
