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
                    "linear_gradient", "cone", "smin", "smax", "blend", "remap", "curve", "levels"],
    "flow": ["priority_flood_fill", "d8_receivers", "d8_accumulation", "mfd_accumulation"],
    "erosion_streampower": ["stream_power_evolve"],
    "erosion_droplet": ["droplet_erode"],
    "erosion_thermal": ["thermal_erosion"],
    "diffusion": ["hillslope_diffuse"],
    "erosion_pipe": ["pipe_water", "pipe_erode"],
    "shallow_water": ["simulate"],
    "meander": ["migrate", "burn_channel"],
    "braided": ["braided_river"],
    "glacier": ["glacier_carve"],
    "snow": ["snow_step", "thermal_on_layer"],
    "aeolian": ["yardang"],
    "tectonics": ["fault_scarp", "fault_weakness", "plate_uplift"],
}

# ops_filters also carries a filter/morphology TOOLBOX that is not a generative atom — excluded from
# the surface check so it isn't mistaken for an undocumented atom.
_OPS_NON_ATOM = {"gaussian", "box_filter", "median", "bilateral", "guided_filter", "perona_malik",
                 "dilate", "erode", "opening", "closing", "tophat", "bothat", "twist", "bend",
                 "unsharp", "histogram_equalize", "resample", "at_feature_scale"}

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
    be added (or kept) as code-only. (Existence here; the load-bearing CONSTANTS are checked separately
    by test_key_constant_agrees_between_chapter_and_code below.)"""
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


# --------------------------------------------------------------------------- #
# FAITHFULNESS: the chapter pseudocode and the code must agree on the key physical CONSTANTS.
# The tests above prove an atom exists and is named in its chapter; they do NOT prove the numbers
# match. This closes that gap for the physically-load-bearing constants (the ones whose value IS
# the correctness of the atom): each is triangulated — the literal must appear in the reference
# MODULE source AND its documented value/statement must appear in the CHAPTER (or the citation
# ledger). Change one side without the other and this fails, forcing a synchronised edit — the
# contributor rule, mechanised. Sampled (the load-bearing constants), not exhaustive; a defect here
# is prose-vs-code DRIFT, not numeric wrongness (the oracle/benchmark/cross-val tests cover that).
FAITHFUL = [
    # (module, code literal in the module source, chapter/doc file, string that must be in that doc, what)
    ("dunes.py", "shadow_tan=0.268", "references/05-erosion-thermal-aeolian.md", "tan(15",
     "Werner lee shadow line = 15deg flow-separation angle (tan 15 = 0.268)"),
    ("dunes.py", "repose=2", "references/99-papers.md", "33.7",
     "sand angle of repose 33.7deg = atan(2/3), the 2-slab drop under the 1:3 slab aspect"),
    ("landforms.py", "(1.0 - rn) ** 2.2", "references/11-geological.md", "2.2",
     "stratovolcano concave-up flank profile exponent (Karatson 2010)"),
    ("landforms.py", "0.2 * D", "references/11-geological.md", "0.2",
     "impact-crater depth/diameter ~= 0.2 (Pike 1977)"),
    ("landforms.py", "0.04 * D", "references/11-geological.md", "0.04",
     "impact-crater rim height ~= 0.04 D"),
    ("landforms.py", "(-3.0)", "references/11-geological.md", "r⁻³",
     "impact-crater ejecta blanket thins as r^-3 (McGetchin 1973)"),
    ("glacier.py", "rho=917.0", "references/12-glacial-coastal.md", "917",
     "glacier ice density 917 kg/m^3"),
    ("glacier.py", "n=3", "references/12-glacial-coastal.md", "n = 3",
     "Glen flow-law exponent n = 3"),
    ("landforms.py", "concavity=1.7", "references/16-arid-desert.md", "concave",
     "alluvial-fan concave (steep-apex, gentle-distal) downfan profile (Blair & McPherson 1994)"),
    ("flow.py", "p=1.1", "references/03-flow-routing.md", "1.1",
     "MFD multiple-flow-direction exponent p = 1.1 (Freeman 1991)"),
    ("isostasy.py", "nu=0.25", "references/02-macro-tectonics.md", "0.25",
     "crustal Poisson ratio nu = 0.25 in flexural rigidity D = E*Te^3 / 12(1-nu^2)"),
    ("snow.py", "shed_lo_deg=50.0", "references/13-climate-ecosystem.md", "tan(50",
     "snow sheds off ground steeper than 50deg (smoothstep 50->60deg; Cordonnier 2018)"),
    ("snow.py", "shed_hi_deg=60.0", "references/13-climate-ecosystem.md", "tan(60",
     "snow fully shed by 60deg"),
    ("tectonics.py", "k_fault=6.0", "references/02-macro-tectonics.md", "weak",
     "fault-as-K SIGN: a fault trace is WEAK rock -> HIGHER erodibility, so valleys follow structure"),
]


@pytest.mark.parametrize("module,code_lit,doc,doc_str,what", FAITHFUL, ids=[e[0] + ":" + e[1] for e in FAITHFUL])
def test_key_constant_agrees_between_chapter_and_code(module, code_lit, doc, doc_str, what):
    """A load-bearing physical constant must read the same in the code and in its chapter (faithfulness,
    not just existence). Fails on prose<->code drift, so neither side can move alone."""
    src = (REF / module).read_text(encoding="utf-8")
    assert code_lit in src, f"{what}: code literal {code_lit!r} missing from reference-impl/{module} " \
                            f"(the code constant changed — update the code, or fix this manifest AND the chapter)"
    chap = (SKILL_ROOT / doc).read_text(encoding="utf-8")
    assert doc_str in chap, f"{what}: {doc_str!r} missing from {doc} " \
                            f"(the chapter drifted from the code constant {code_lit!r} — resync the pseudocode)"
