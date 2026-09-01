"""Scale contract (08-output-contract.md): atom parameters must not be silently in CELL units.

A cell is not a unit — `cellSize = extent / n` is. An atom that takes a threshold, radius or count
in cells changes meaning whenever the grid changes, which is how a graph that looked right at
preview resolution comes out wrong at build resolution. `erosion_thermal.thermal_erosion` is the
worked example: it takes `repose_slope` (a slope) times `cellsize`, so it encodes an ANGLE.

This is the anti-drift guard for that rule. Every atom in the coverage manifest must either accept
`cellsize` **and read it**, or be listed below with a REASON it is legitimately grid- or
caller-relative. Adding an atom with cell-unit parameters and no justification fails here.

⚠️ "ACCEPT" USED TO BE THE WHOLE TEST, AND A DECLARATION IS NOT A FACT. This guard asked
`"cellsize" in inspect.signature(fn).parameters` and credited the answer as scale-explicitness. A
parameter that is declared and never read satisfies that exactly — and the dead-parameter census in
`tests/test_render.py` found four functions in this tree carrying precisely that, two of them atoms
in the coverage manifest (`aeolian.yardang`, `tectonics.fault_weakness`). So for two atoms the
scale contract was being met by an argument no line of their body reads, which is worse than not
declaring one: the signature tells a caller the atom is resolution-aware, the exemption list stays
short, and nothing anywhere is checking. The guard now asks the census whether the parameter is
READ, and the two atoms are moved into the exemption table below with the reason they belong there.
"""
import importlib
import inspect
from pathlib import Path

import numpy as np
import pytest

from test_atom_coverage import IMPLEMENTED
from test_render import parameter_census                  # the dead-parameter census (criterion G1)


def _dead_parameters():
    """{(module, function, parameter)} for every declared-but-never-read parameter in the tree."""
    ref = Path(__file__).resolve().parents[1]
    dead = set()
    for path in sorted(ref.glob("*.py")):
        _, _, rows, _ = parameter_census(path.read_text(encoding="utf-8"), path.stem)
        dead |= {(m, q, p) for m, q, p, _ in rows}
    return dead


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
_SI_POINTWISE = (
    "point physics in SI units, evaluated per cell with no spatial derivative or neighbourhood: "
    "grain size in metres, speed in m/s, flux in kg/m/s. There is no distance for cellsize to "
    "convert — the grid first enters at `exner_step`, which differentiates the flux and does take "
    "cellsize. (Rescaling these for another world is a matter of `g` and `rho_a`, not of cell size.)"
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
    **{("placement", f): _CALLER_COORDS for f in
       ("place_coords", "affine", "compose", "transform_coords", "sample_coords")},
    **{("aeolian", f): _SI_POINTWISE for f in
       ("shear_velocity", "threshold_shear", "saltation_flux", "transport_field")},
    ("flow", "priority_flood_fill"): _SCALE_FREE,
    # ⚠️ THE TWO ATOMS THAT USED TO PASS ON A DEAD `cellsize`. They still DECLARE one — it cannot
    # be deleted while `tests/test_gallery_doc.py` passes it, which is a file this wave does not
    # own — but it is read by nothing, so they are exempted on their real grounds instead of
    # credited for a parameter that does nothing. Both are recorded in registers/OPEN-ITEMS.md
    # with the exact removal patch, and in test_render.DEAD_PARAMETER_EXEMPTIONS.
    ("aeolian", "yardang"):
        "abrasion lanes are laid out in INDEX space: `freq_along`/`freq_cross` are per-cell "
        "frequencies and `floor_reach` counts cells, while the one metric quantity `saltation_h` "
        "is already in metres. The `cellsize` in its signature is DEAD (test_render census) and is "
        "not evidence of anything; making the frequencies per-metre needs their defaults "
        "re-baselined against chapter 16.",
    ("tectonics", "fault_weakness"):
        "fault traces are placed and feathered in index space and `width` is a Gaussian half-width "
        "in CELLS; the result is a dimensionless erodibility field K, so no length enters. The "
        "`cellsize` in its signature is DEAD (test_render census); implementing it would make the "
        "4.0 default sub-cell at any realistic resolution and silently return a uniform K.",
    ("meander", "migrate"):
        "evolves a centreline, not a grid: ds/dt/cutoff_dist are all in the caller's units, so the "
        "result is unit-agnostic; only rasterising it (burn_channel) needs cellsize.",
    ("erosion_droplet", "droplet_erode"):
        "cell-space particle walk (droplets step one cell, brush_radius counts cells). The exposure "
        "is documented on the function and `resolution_matched()` carries settings between grids.",
    **{("hex_grid", f):
       "pure lattice topology in index space — cell adjacency and hex graph distance, which no "
       "cellsize can change (the metric enters only through `basis`, and every hex_grid function "
       "that touches world space does take cellsize)."
       for f in ("ring", "disc")},
}


def _atoms():
    for module, names in IMPLEMENTED.items():
        mod = importlib.import_module(module)
        for name in names:
            fn = getattr(mod, name, None)
            if callable(fn):
                yield module, name, fn


def test_every_atom_is_scale_explicit():
    """Each atom takes `cellsize` AND READS IT, or is justified as grid-/caller-relative above."""
    dead = _dead_parameters()
    unjustified = []
    for module, name, fn in _atoms():
        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            continue
        if "cellsize" in params and (module, name, "cellsize") not in dead:
            continue                                       # declared AND read: genuinely scale-explicit
        if (module, name) in PIXEL_OR_CALLER_SPACE:
            continue
        unjustified.append(
            f"{module}.{name}"
            + ("  [declares `cellsize` but never reads it]"
               if (module, name, "cellsize") in dead else ""))
    assert not unjustified, (
        "atoms with no LIVE `cellsize` and no entry in PIXEL_OR_CALLER_SPACE — either thread "
        "cellsize through (and read it), or document why cells are the right unit. A parameter "
        f"that is accepted and ignored does not satisfy this guard: {unjustified}"
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


def test_a_declared_but_unread_cellsize_does_not_satisfy_the_scale_contract():
    """⚠️ THE MUTATION THIS GUARD WAS BLIND TO, AS A FIXTURE RATHER THAN AS A CLAIM.

    Before the census was wired in, an atom could satisfy `test_every_atom_is_scale_explicit` by
    writing `cellsize` into its signature and never using it. The two fixtures below are the same
    atom with and without the one division that makes the parameter real, and the guard's input
    must separate them. Beneath it, the two atoms this actually caught: they still declare a dead
    `cellsize` (deletion is blocked by a call site this wave does not own), so they now sit in the
    exemption table on their real grounds — index-space geometry — rather than passing on a
    parameter no line of their body reads.
    """
    dead_atom = "def atom(h, cellsize=1.0, radius=3):\n    return h * radius\n"
    _, _, dead, _ = parameter_census(dead_atom, "fixture")
    assert ("fixture", "atom", "cellsize") in {(m, q, p) for m, q, p, _ in dead}

    live_atom = "def atom(h, cellsize=1.0, radius=3):\n    return h * radius / cellsize\n"
    _, _, still_dead, _ = parameter_census(live_atom, "fixture")
    assert still_dead == [], (
        "a cellsize that IS read must not be reported dead, or every scale-explicit atom in the "
        "manifest false-fails: %s" % still_dead)

    for atom in (("aeolian", "yardang"), ("tectonics", "fault_weakness")):
        assert atom in PIXEL_OR_CALLER_SPACE, (
            "%s used to satisfy the scale contract with a dead `cellsize`; if it now reads one, "
            "delete its exemption — do not leave both" % (atom,))
        assert atom in {(m, n) for m, n, _ in _atoms()}
