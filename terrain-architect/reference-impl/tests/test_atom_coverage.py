"""Anti-drift harness for the atomic bases (see `ATOM-COVERAGE.md`). Keeps three artifacts from
silently diverging: the chapter PSEUDOCODE (`references/`), the executable REFERENCE IMPL, and the
SCOPE STATEMENT (`ATOM-COVERAGE.md`). It does NOT prove the atoms are numerically correct — the
per-atom oracle tests (test_noise, test_ops_filters, the solver tests) do that. It proves the *set*
is consistent: nothing is claimed-but-missing, built-but-undocumented, or deferred-but-secretly-present
(the class of gap that had let Simplex/Gabor sit in the pseudocode with no implementation)."""
import importlib
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]                 # reference-impl/
SKILL_ROOT = REF.parent                                    # terrain-architect/
COVERAGE = (REF / "ATOM-COVERAGE.md").read_text(encoding="utf-8")

# The manifest is the source of truth: module -> the atoms the skill claims to IMPLEMENT.
IMPLEMENTED = {
    "noise": ["perlin", "value", "simplex", "worley", "fbm", "ridged_mf", "hybrid_mf",
              "gabor", "domain_warp", "curl"],
    "ops_filters": ["sd_circle", "sd_box", "sd_convex_polygon", "sd_segment", "radial_gradient",
                    "cone", "smin", "smax", "blend", "remap"],
    "flow": ["priority_flood_fill", "d8_receivers", "d8_accumulation", "mfd_accumulation"],
    "erosion_streampower": ["stream_power_evolve"],
    "erosion_droplet": ["droplet_erode"],
    "erosion_thermal": ["thermal_erosion"],
    "diffusion": ["hillslope_diffuse"],
    "erosion_pipe": ["pipe_water", "pipe_erode"],
    "shallow_water": ["simulate"],
    "meander": ["migrate", "burn_channel"],
    "glacier": ["glacier_carve"],
    "snow": ["snow_step", "thermal_on_layer"],
    "aeolian": ["yardang"],
    "tectonics": ["fault_scarp", "fault_weakness"],
}

# ops_filters also carries a filter/morphology TOOLBOX that is not a generative atom — excluded from
# the surface check so it isn't mistaken for an undocumented atom.
_OPS_NON_ATOM = {"gaussian", "box_filter", "median", "bilateral", "guided_filter", "perona_malik",
                 "dilate", "erode", "opening", "closing", "tophat", "bothat", "twist", "bend"}

# Atoms discussed in the pseudocode but deliberately NOT implemented: {name: chapter it's discussed in}.
DEFERRED = {"OpenSimplex2": "references/01-noise.md", "Wavelet": "references/01-noise.md"}

_ATOMS = [(m, f) for m, fns in IMPLEMENTED.items() for f in fns]

# Landform GENERATORS (macros over the atoms) must stay DOCUMENTED in their chapter — an existence guard
# against adding/keeping a generator with no backing pseudocode (the Simplex/Gabor drift class, for the
# generator family). This checks the generator is named in the chapter; it does NOT verify that the
# pseudocode's CONSTANTS match the code (e.g. a profile exponent) — prose-vs-code constant drift is caught
# by the review/faithfulness passes, not here.
GENERATORS = {
    "mountain": "references/11-geological.md",
    "ridge": "references/11-geological.md",
    "volcano": "references/11-geological.md",
    "canyon": "references/11-geological.md",
    "fault_block_butte": "references/11-geological.md",
    "alluvial_fan": "references/16-arid-desert.md",
}


def _public_callables(module_name):
    mod = importlib.import_module(module_name)
    return {n for n in vars(mod)
            if not n.startswith("_")
            and callable(getattr(mod, n))
            and getattr(getattr(mod, n), "__module__", None) == module_name}


@pytest.mark.parametrize("module,fn", _ATOMS)
def test_every_documented_atom_is_implemented(module, fn):
    """Each atom the manifest/scope-doc claims as implemented must exist as a callable (catches a
    documented-but-missing atom, or an implementation removed out from under the docs)."""
    mod = importlib.import_module(module)
    assert callable(getattr(mod, fn, None)), f"{module}.{fn} is claimed implemented but missing"


@pytest.mark.parametrize("module,fn", _ATOMS)
def test_scope_doc_lists_every_implemented_atom(module, fn):
    """The scope statement must name every implemented atom (doc <-> manifest stay in sync)."""
    assert fn in COVERAGE, f"{module}.{fn} implemented but not listed in ATOM-COVERAGE.md"


def test_noise_surface_has_no_undocumented_atom():
    """Reverse drift: every public function in noise.py must be in the manifest, so a new noise atom
    cannot be added to the code without being documented (this is exactly how Simplex/Gabor slipped)."""
    undocumented = _public_callables("noise") - set(IMPLEMENTED["noise"])
    assert not undocumented, f"undocumented noise atoms in code: {sorted(undocumented)}"


def test_ops_surface_is_fully_accounted_for():
    """Every public ops_filters function is either a listed atom or an explicit non-atom filter."""
    unaccounted = _public_callables("ops_filters") - set(IMPLEMENTED["ops_filters"]) - _OPS_NON_ATOM
    assert not unaccounted, f"ops_filters functions neither atom nor listed non-atom: {sorted(unaccounted)}"


@pytest.mark.parametrize("fn,chapter", GENERATORS.items())
def test_landform_generators_are_documented(fn, chapter):
    """Each landform generator must exist AND be named in its chapter's pseudocode — so a generator can't
    be added (or kept) as code-only. (Existence only; constant-level faithfulness is a review concern.)"""
    lf = importlib.import_module("landforms")
    assert callable(getattr(lf, fn, None)), f"landforms.{fn} missing"
    assert fn in (SKILL_ROOT / chapter).read_text(encoding="utf-8"), f"landforms.{fn} not documented in {chapter}"


@pytest.mark.parametrize("name,chapter", DEFERRED.items())
def test_deferred_atoms_are_discussed_but_absent(name, chapter):
    """A deferred atom must be genuinely absent from the code, yet actually discussed in its chapter
    and listed in the scope doc — so 'deferred' is an honest, checked status, not a silent gap."""
    mod = importlib.import_module("noise")
    assert not hasattr(mod, name.lower()), f"{name} is listed deferred but exists in noise"
    assert name in (SKILL_ROOT / chapter).read_text(encoding="utf-8"), f"{name} not discussed in {chapter}"
    assert name in COVERAGE, f"deferred {name} not listed in ATOM-COVERAGE.md"
