"""Anti-drift harness between the chapters' PSEUDOCODE and the shipped modules.

THE GAP THIS CLOSES. `test_atom_coverage.py` guards which atoms exist. Nothing guarded the
NUMBERS inside the chapters' pseudocode blocks, and the chapters are what a reader implements
from. `01`'s four fBm blocks carried `lacunarity=2.0` while `noise.py` ships `2.03` — the exact
value the prose one paragraph below warns against, and one that puts a grid of identically-zero
pinch points into the output (`test_noise_pinch.py`). Prose and code had drifted apart at the one
place where the drift is executable.

HOW IT WORKS, AND WHY IT IS A REGISTER RATHER THAN A SCAN. An automatic scan over every numeric
default in every chapter is mostly noise: generic parameter names (`radius`, `depth`, `angle`,
`height`) collide with ordinary prose, and a harness that cries wolf is one people delete. So the
pairs below are declared. Each entry says: this chapter's pseudocode quotes this parameter, and
this module's function is what ships it. Adding a row is cheap; the register is the point, because
it makes the correspondence explicit instead of hoping a regex finds it.

⚠️ WHAT A FAILURE HERE MEANS. Not necessarily that the code is wrong. It means the two artifacts
disagree, and *someone must decide which one moves* — exactly the judgement `ATOM-COVERAGE.md`
already forces for the atom set. Silently widening a tolerance is not available: these are exact
values on both sides.

THE FOUR REGISTERS, AND WHY THE LAST THREE EXIST. `PAIRS` and `BLOCK_CONSTANTS` are the agreeing
pairs — a signature default and a block-stated constant respectively. But a register of only the
pairs that happen to agree is a flattering one: it grows by adding the easy rows and says nothing
about the hard ones. So the disagreements are registered too. `KNOWN_DIVERGENCES` and
`KNOWN_FORM_DIVERGENCES` record, with both sides pinned, the places where chapter and module
genuinely say different things and a human has not yet decided which moves; resolving one FAILS its
row, which is how it leaves the register. `PRESCRIBED_NOT_IMPLEMENTED` records pseudocode with
numbers in it and no module behind it — nothing is guarded there, and implementing one FAILS its
entry so the new constants get pinned on the way in rather than never.

⚠️ THE SCOPE THIS FILE KEEPS. Numbers a reader would TYPE IN from a fenced block. Prose figures a
module can re-derive (percentages, fitted exponents, measured statistics) belong to
`test_chapter_numbers.py`, which holds them to their printed precision; the existence of an atom
belongs to `test_atom_coverage.py`. Every pattern here is matched against fenced blocks only, so
the three files cannot start guarding each other's ground by accident.
"""
import importlib
import inspect
import re
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]
CHAPTERS = REF.parent / "references"

# (chapter file, pseudocode signature name, module, function, parameter)
# The signature name is how the CHAPTER writes it; the function is how the MODULE does — the
# camelCase-to-snake_case crossing (`ridgedMF` -> `ridged_mf`, `poissonDisk` -> `poisson_disk`)
# is spelled out per row rather than derived, because the exceptions are real: `mfd` ships as
# `mfd_accumulation`, `werner` as `werner_dunes`. A derived mapping would quietly skip those.
PAIRS = [
    ("01-noise.md", "fbm", "noise", "fbm", "lacunarity"),
    ("01-noise.md", "fbm", "noise", "fbm", "gain"),
    ("01-noise.md", "ridgedMF", "noise", "ridged_mf", "lacunarity"),
    ("01-noise.md", "ridgedMF", "noise", "ridged_mf", "gain"),
    ("01-noise.md", "ridgedMF", "noise", "ridged_mf", "offset"),
    ("01-noise.md", "ridgedMF", "noise", "ridged_mf", "H"),
    ("01-noise.md", "hybridMF", "noise", "hybrid_mf", "lacunarity"),
    ("01-noise.md", "hybridMF", "noise", "hybrid_mf", "H"),
    ("01-noise.md", "hybridMF", "noise", "hybrid_mf", "offset"),
    # every other chapter whose pseudocode gives a parameter a numeric default in its SIGNATURE
    ("03-flow-routing.md", "mfd", "flow", "mfd_accumulation", "p"),
    ("05-erosion-thermal-aeolian.md", "voellmyRunout", "runout", "voellmy_runout", "g"),
    ("05-erosion-thermal-aeolian.md", "voellmyRunout", "runout", "voellmy_runout", "v0"),
    ("07-scatter.md", "poissonDisk", "scatter", "poisson_disk", "k"),
]

# The same guard for the numbers a block states in its BODY rather than its signature — the
# `# p_sand ≈ 0.6` and `# ~1.1` form, which is how most chapters actually write a default. The
# pattern must match INSIDE a fenced block: prose figures belong to `test_chapter_numbers.py`,
# which holds them to their printed precision; this file is about what a reader types in.
#
# The pattern is per row and explicit, for the reason the module docstring gives: a generic
# `name\s*=\s*NUMBER` sweep captures the wrong number the moment two constants share a line
# (`p_sand ≈ 0.6, p_bare ≈ 0.4` is one such line, and it is in this register twice).
#
# (chapter file, regex capturing the value in a fenced block, module, function, parameter, what)
BLOCK_CONSTANTS = [
    ("02-macro-tectonics.md", r"oceanic ≈ (-?[0-9.]+) m", "tectonics", "plate_uplift",
     "ocean_base", "oceanic plate base elevation"),
    ("02-macro-tectonics.md", r"continental ≈ \+([0-9.]+) m", "tectonics", "plate_uplift",
     "cont_base", "continental plate base elevation"),
    ("02-macro-tectonics.md", r"ρm ≈ ([0-9.]+) kg", "isostasy", "airy_root", "rho_m",
     "mantle density in the Airy root r = ρc·h/(ρm−ρc)"),
    ("03-flow-routing.md", r"depth = k_d \* pow\(Q, ([0-9.]+)\)", "hydrology", "water_surface",
     "depth_exp", "downstream hydraulic geometry: depth ∝ Q^0.4 (Leopold & Maddock 1953)"),
    ("03-flow-routing.md", r"if SE ≥ ([0-9.]+) and", "analytic", "avulses", "threshold",
     "avulsion setup: superelevation of one channel depth (Mohrig 2000)"),
    ("05-erosion-thermal-aeolian.md", r"p_sand ≈ ([0-9.]+)", "dunes", "werner_dunes", "p_sand",
     "Werner deposition probability over sand — p_sand > p_bare IS the instability"),
    ("05-erosion-thermal-aeolian.md", r"p_bare ≈ ([0-9.]+)", "dunes", "werner_dunes", "p_bare",
     "Werner deposition probability over bare ground"),
    ("05-erosion-thermal-aeolian.md", r"L = saltationHop[^\n]*~([0-9.]+) cells", "dunes",
     "werner_dunes", "hop",
     "Werner's fixed saltation length, l ≈ 5 cells — the hop that sets the emergent dune "
     "wavelength. THIS ROW REPLACES the retired `werner-saltation-hop` divergence (see the note "
     "at the head of KNOWN_DIVERGENCES): the constant used to be stated four ways and now reads 5 "
     "in all of them, so it is guarded here as an agreeing pair rather than recorded as a finding"),
    ("06-analysis-masks.md", r"stepGrowth[^\n]*~([0-9.]+)", "analysis", "horizon_ao",
     "step_growth", "exponential march ratio in the horizon sweep"),
    ("12-glacial-coastal.md", r"with n = ([0-9]+), A ≈", "glacier", "glacier_carve", "n",
     "Glen flow-law exponent n = 3"),
    ("12-glacial-coastal.md", r"l ≈ ([0-9.]+), K_g", "glacier", "glacier_carve", "l",
     "glacial abrasion velocity exponent in ė = K_g·|u_b|^l (its COEFFICIENT diverges — below)"),
    ("12-glacial-coastal.md", r"A ≈ ([0-9.e+-]+) Pa", "sims_illustrative", "glacier_sia", "A",
     "Glen rate factor at 0 °C, Pa^-3 s^-1 (the SIA sketch keeps the paper's units)"),
    ("12-glacial-coastal.md", r"d₀ ≈ ([0-9.]+) m", "analytic", "seafloor_depth_hsc", "d0",
     "half-space cooling: ridge-crest depth d₀ (Parsons & Sclater 1977)"),
    ("12-glacial-coastal.md", r"C ≈ ([0-9.]+) m/√Myr", "analytic", "seafloor_depth_hsc", "C",
     "half-space cooling: subsidence coefficient C"),
]


def _fenced(chapter):
    """Every fenced block of a chapter, concatenated — the pseudocode and nothing else."""
    text = (CHAPTERS / chapter).read_text(encoding="utf-8")
    return "\n".join(re.findall(r"```[^\n]*\n(.*?)```", text, re.S))


def _fenced_value(chapter, pattern):
    """The number a chapter's pseudocode states for a constant, or None."""
    m = re.search(pattern, _fenced(chapter))
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _chapter_default(chapter, signature, param):
    """The value a chapter's pseudocode signature gives a parameter, or None."""
    text = _fenced(chapter)
    # the signature line inside a fenced block: `name(... param=VALUE ...)`
    for m in re.finditer(r"^%s\(([^)]*)\)" % re.escape(signature), text, re.M):
        for part in m.group(1).split(","):
            k, _, v = part.partition("=")
            if k.strip() == param and v.strip():
                try:
                    return float(v.strip())
                except ValueError:
                    return None
    return None


def _module_default(module, function, param):
    fn = getattr(importlib.import_module(module), function)
    default = inspect.signature(fn).parameters[param].default
    return None if default is inspect.Parameter.empty else float(default)


def _module_source(module):
    return (REF / (module + ".py")).read_text(encoding="utf-8")


@pytest.mark.parametrize("chapter,signature,module,function,param", PAIRS)
def test_pseudocode_default_matches_the_module(chapter, signature, module,
                                               function, param):
    doc = _chapter_default(chapter, signature, param)
    code = _module_default(module, function, param)
    assert doc is not None, (
        "%s's `%s(...)` pseudocode no longer gives `%s` a default — either the block changed or "
        "this row is stale" % (chapter, signature, param))
    assert code is not None, "%s.%s has no default for %s" % (module, function, param)
    assert doc == code, (
        "%s pseudocode says %s=%s; %s.%s ships %s. One of the two must move — a reader "
        "implements from the chapter." % (chapter, param, doc, module, function, code))


@pytest.mark.parametrize("chapter,pattern,module,function,param,what", BLOCK_CONSTANTS,
                         ids=[r[2] + "." + r[4] for r in BLOCK_CONSTANTS])
def test_pseudocode_constant_matches_the_module(chapter, pattern, module, function, param, what):
    """A number a pseudocode BLOCK states must be the number the shipped parameter defaults to."""
    doc = _fenced_value(chapter, pattern)
    code = _module_default(module, function, param)
    assert doc is not None, (
        "%s's pseudocode no longer states %r (%s) — either the block changed or this row is "
        "stale" % (chapter, pattern, what))
    assert code is not None, "%s.%s has no default for %s" % (module, function, param)
    assert doc == code, (
        "%s pseudocode says %s (%s); %s.%s ships %s=%s. One of the two must move — a reader "
        "implements from the chapter." % (chapter, doc, what, module, function, param, code))


def test_the_register_still_points_at_things_that_exist():
    """A row naming a function that has been renamed would silently stop guarding anything."""
    missing = []
    rows = ([(m, f, p) for _c, _s, m, f, p in PAIRS]
            + [(m, f, p) for _c, _pat, m, f, p, _w in BLOCK_CONSTANTS])
    for module, function, param in rows:
        try:
            fn = getattr(importlib.import_module(module), function)
        except (ImportError, AttributeError):
            missing.append("%s.%s" % (module, function))
            continue
        if param not in inspect.signature(fn).parameters:
            missing.append("%s.%s(%s)" % (module, function, param))
    assert not missing, "the drift register points at things that do not exist: %s" % missing


# --------------------------------------------------------------------------- #
# UNRESOLVED DIVERGENCES — the rows that could NOT be made to agree.
#
# These are not exceptions granted to the code. They are findings: places where the chapter
# prescribes one number and the module ships another, recorded here with both sides pinned so the
# disagreement cannot be forgotten and cannot silently change shape. A row here is a piece of
# open work for a human, and the register is deliberately uncomfortable to leave lying around.
#
# ⚠️ THE STALENESS RULE. Each row asserts that BOTH sides still read exactly as recorded, and that
# they still differ. So: resolve the divergence (either side moves) and the row FAILS, telling you
# to delete it and add a real row above. Drift further and it also fails. The one thing that cannot
# happen is a divergence quietly becoming a different divergence.
#
# ⚠️ WHAT IS NOT ALLOWED HERE: moving a row down from PAIRS to make a failure go away. A row belongs
# here only when a human has looked at both sides and judged that neither can be moved right now.
#
# (id, chapter, fenced-block regex, chapter value, module, code literal, code value, verdict)
# RETIRED — `werner-saltation-hop` (05's Werner block ~5 cells vs `dunes.werner_dunes(hop=1)`).
# It was never a two-way disagreement: 05:412's block said ~5, 05:399's prose said ≈3, the
# docstring said ~5 and the signature shipped 1, so the CHAPTER contradicted itself before the
# module was consulted. Resolved at Werner's published value: a slab "moves downwind to a new
# lattice site l (typically equal to 5) sites away" (Werner 1995, as restated in Kok, Parteli,
# Michaels & Karam 2012, Rep. Prog. Phys. 75 106901 §3.2.2). 05:399 now reads ≈5 and the default
# is hop=5. The pin did not simply vanish: the block-vs-default half is a normal pinned pair in
# BLOCK_CONSTANTS above (`dunes.hop`), and the PROSE half — which no fenced-block register can
# see — is pinned by tests/test_dunes.py::test_chapter_note_quotes_the_shipped_hop. Both go red
# if either side moves again.
KNOWN_DIVERGENCES = [
    ("glacier-abrasion-K_g", "12-glacial-coastal.md", r"K_g ≈ ([0-9.e+-]+)", 1e-4,
     "glacier", "K_g=8e-4", 8e-4,
     "12's abrasion block quotes K_g ≈ 1e-4; glacier.glacier_carve ships 8x that, so a carve is "
     "visible in a short demo run. The exponent `l` beside it agrees (registered above), which is "
     "what makes the coefficient's disagreement look like drift rather than a different law. The "
     "CHAPTER is right — a reader implementing 12 should use 1e-4 — and the module's 8e-4 needs "
     "naming as a demo amplification in glacier.py rather than left reading as the physical "
     "value. (Same paragraph, same class, NOT registered because it is prose and so belongs to "
     "test_chapter_numbers.py: 12 says the sliding fraction is `f ≈ 0.5`; glacier_carve ships "
     "f_slide=0.6.)"),
    ("glacier-sia-substep", "12-glacial-coastal.md", r"Δt' = ([0-9.]+) cellSize", 0.25,
     "glacier", "0.2 * cellsize * cellsize", 0.2,
     "12 states the SIA explicit-diffusion stability limit as 0.25·cellSize²/max(D); both "
     "implementations subcycle at 0.2, i.e. an unstated 0.8 safety factor. The CODE is right to "
     "be conservative (0.25 is the limit, not a safe step); the chapter should say so, since a "
     "reader who implements 0.25 literally is stepping at the edge of stability."),
    ("crater-complex-transition", "11-geological.md", r"Dc = ([0-9.]+)·\(9\.81/g\)", 3200.0,
     "landforms", "complex_D=3000.0", 3000.0,
     "11's finalCrater block puts the simple→complex transition at 3200 m on Earth, and "
     "crater.transition_diameter ships exactly that; landforms.impact_crater independently "
     "defaults complex_D=3000.0. The two modules disagree with each other by 200 m and one of "
     "them disagrees with the chapter. The CHAPTER (and crater.py) is right; landforms should "
     "take its transition from crater.transition_diameter instead of a second literal."),
]


@pytest.mark.parametrize("name,chapter,pattern,doc_value,module,code_lit,code_value,verdict",
                         KNOWN_DIVERGENCES, ids=[d[0] for d in KNOWN_DIVERGENCES])
def test_known_divergence_is_still_exactly_as_recorded(name, chapter, pattern, doc_value,
                                                       module, code_lit, code_value, verdict):
    """An unresolved chapter-vs-code disagreement, pinned on both sides so it cannot drift."""
    doc = _fenced_value(chapter, pattern)
    assert doc == doc_value, (
        "%s: %s's pseudocode no longer reads %s (it reads %s). If the chapter was fixed, delete "
        "this row and add a matching row to the register above. Finding was: %s"
        % (name, chapter, doc_value, doc, verdict))
    assert code_lit in _module_source(module), (
        "%s: %s.py no longer contains %r. If the code was fixed, delete this row and add a "
        "matching row to the register above. Finding was: %s" % (name, module, code_lit, verdict))
    assert doc_value != code_value, (
        "%s is recorded as a divergence but both sides now read the same — move it up into the "
        "register above" % name)


# --------------------------------------------------------------------------- #
# The same thing one level up: places where the chapter prescribes a different FORM, not a
# different number, so there is no pair of defaults to compare. Pinned by marker strings on both
# sides for the same reason — a fix on either side must be noticed.
#
# (id, chapter, chapter markers, module, code markers, verdict)
KNOWN_FORM_DIVERGENCES = [
    ("lava-viscosity-and-cooling", "19-lava.md",
     ["η(T) = η_0 · exp(−b · (T − T_erupt))",
      "q  = k · (τ − τ_y(T)) · L² / η(T)",
      "T -= Δt · ε σ (T⁴ − T_env⁴) · lerp(1, insulation, crust) / (ρ c_p L)",
      "T -= Δt · conductionToBed(L)"],
     "sims_illustrative", ["eta=1e3", "/ eta", "T - cool * dt"],
     "19 prescribes an Arrhenius-style η(T) inside the Bingham flux and a RADIATIVE cooling term "
     "gated by crust insulation (plus conduction to the bed); sims_illustrative.lava_flow ships a "
     "constant `eta` and a uniform linear `cool*dt`, and has no `insulation` parameter at all — "
     "while 19's own parameter table calls insulation 'the look-critical one'. The CHAPTER is "
     "right and is deliberately prescribing more than this module implements: 19 is the spec, the "
     "module is an illustrative CA (its own docstring says the un-oracled regimes are held only to "
     "invariants). What is missing is the statement of that gap: neither 19's runnable-reference "
     "note nor lava_flow's docstring says the cooling law and η(T) are not the ones above, so the "
     "module currently reads as an implementation of the block when it is a sketch of it."),
]


@pytest.mark.parametrize("name,chapter,doc_markers,module,code_markers,verdict",
                         KNOWN_FORM_DIVERGENCES, ids=[d[0] for d in KNOWN_FORM_DIVERGENCES])
def test_known_form_divergence_is_still_exactly_as_recorded(name, chapter, doc_markers, module,
                                                            code_markers, verdict):
    """A prescribed-vs-shipped difference in FORM, pinned so a fix on either side is noticed."""
    text = (CHAPTERS / chapter).read_text(encoding="utf-8")
    for marker in doc_markers:
        assert marker in text, (
            "%s: %s no longer prescribes %r. If the chapter changed, re-adjudicate this row. "
            "Finding was: %s" % (name, chapter, marker, verdict))
    source = _module_source(module)
    for marker in code_markers:
        assert marker in source, (
            "%s: %s.py no longer contains %r. If the module now implements the chapter's form, "
            "delete this row. Finding was: %s" % (name, module, marker, verdict))


# --------------------------------------------------------------------------- #
# PRESCRIBED BUT NOT IMPLEMENTED — pseudocode with numbers in it and no module behind it.
#
# These are NOT drift and NOT a backlog: a skill chapter is allowed to specify more than the
# reference implementation ships, and several of these deliberately do. They are here because the
# register above must not be read as "everything with pseudocode is guarded". Nothing checks the
# constants in these blocks, and nothing can, because there is no second artifact to check against.
#
# ⚠️ THE ROT GUARD: each entry asserts the name is still discussed in its chapter AND still has no
# implementation. Ship one and the entry FAILS — which is the point. A newly-implemented process
# whose constants nobody pinned to its chapter is exactly the drift this file exists to stop, and
# the fix is to delete the entry and add a real row above.
#
# (pseudocode name, snake_case name a module would use, chapter, why it is unguardable today)
PRESCRIBED_NOT_IMPLEMENTED = [
    ("diamondSquare", "diamond_square", "01-noise.md",
     "documented as obsolete (non-continuous, non-tileable); kept for recognition, not for use"),
    ("dinf", "dinf", "03-flow-routing.md",
     "D-infinity facet routing — flow.py ships D8/MFD only; the facet α=π/4 constant is unpinned"),
    ("terraceStep", "terrace_step", "03-flow-routing.md",
     "fluvial terrace cut-and-fill cycle; landforms.terrace stamps the FORM, not the H_ref cycle"),
    ("retreatKnickpoints", "retreat_knickpoints", "04-erosion-hydraulic.md",
     "explicit knickpoint celerity C_kp = K·A^m; the SPL solver moves them implicitly instead"),
    ("failureMask", "failure_mask", "05-erosion-thermal-aeolian.md",
     "infinite-slope factor of safety FS<1 — no module computes it; runout.py starts from a scar"),
    ("anchoredDunes", "anchored_dunes", "05-erosion-thermal-aeolian.md",
     "echo/climbing dunes at an obstacle (θ_separate ≈ 60°); dunes.py has no obstacle branch"),
    ("insolation", "insolation", "06-analysis-masks.md",
     "sun-arc integration (declination, hour angles); analysis.py ships horizon AO, not insolation"),
    ("soilProduction", "soil_production", "11-geological.md",
     "humped/exponential soil production P0·exp(-d/h*) — no regolith depth field is simulated"),
    ("calderaCollapse", "caldera_collapse", "11-geological.md",
     "piston collapse geometry; archetypes.caldera composes a look from primitives instead"),
    ("inletStamp", "inlet_stamp", "12-glacial-coastal.md",
     "O'Brien tidal-prism inlet area A = C_OB·P^0.85 — the C_OB fit is unit-bound and unshipped"),
    ("profileStep", "profile_step", "12-glacial-coastal.md",
     "cross-shore energetics profile evolution; sims_illustrative.coastal_retreat is a notch+talus"),
    ("reefStep", "reef_step", "12-glacial-coastal.md",
     "subsidence + photic-zone coral growth (Darwin's sequence); nothing implements the loop"),
    ("coralCover", "coral_cover", "12-glacial-coastal.md",
     "per-cell coral form selection from light/energy masks; a 07 scatter rule, not shipped"),
    ("orographicPrecip", "orographic_precip", "13-climate-ecosystem.md",
     "windward-lift moisture depletion; winds.py ships the wind field, not the moisture budget"),
    ("wetnessStep", "wetness_step", "13-climate-ecosystem.md",
     "soak/dry wetness state; analysis.twi gives the static index, not the time-stepped field"),
    ("solifluction", "solifluction", "17-periglacial.md",
     "frost-gated downslope creep; diffusion.hillslope_diffuse is the ungated form"),
]


def _implemented_names():
    """Every function name defined by a reference-impl module, as a set."""
    names = set()
    for path in sorted(REF.glob("*.py")):
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"def ([A-Za-z_][A-Za-z0-9_]*)\(", line)
            if m:
                names.add(m.group(1))
    return names


@pytest.mark.parametrize("pseudo,snake,chapter,reason", PRESCRIBED_NOT_IMPLEMENTED,
                         ids=[e[0] for e in PRESCRIBED_NOT_IMPLEMENTED])
def test_prescribed_but_unimplemented_stays_that_way(pseudo, snake, chapter, reason):
    """Prescribed-only pseudocode: still discussed in its chapter, still with nothing behind it."""
    assert pseudo in (CHAPTERS / chapter).read_text(encoding="utf-8"), (
        "%s no longer discusses `%s` — this entry is stale (the chapter dropped the block, or "
        "renamed it)" % (chapter, pseudo))
    assert snake not in _implemented_names(), (
        "`%s` now ships as %s(): it is no longer prescribed-only. Delete this entry and add a "
        "row to PAIRS/BLOCK_CONSTANTS pinning its constants to %s — an implementation whose "
        "numbers nobody pinned to its chapter is exactly the drift this file exists to stop. "
        "(Recorded reason it was unimplemented: %s)" % (pseudo, snake, chapter, reason))


def test_no_pseudocode_block_still_ships_plain_lacunarity_two():
    """The specific regression this file was written for, stated as itself.

    Guarding the registered signatures is not quite enough: a NEW pseudocode block could
    reintroduce `lacunarity=2.0` without anyone adding a row for it. This scans every fenced block
    in `01` for that one value, because that one value has a measured artefact behind it.
    """
    text = (CHAPTERS / "01-noise.md").read_text(encoding="utf-8")
    offenders = re.findall(r"^\w+\([^)]*lacunarity\s*=\s*2\.0(?![0-9])[^)]*\)", text, re.M)
    assert not offenders, (
        "these pseudocode signatures ship lacunarity exactly 2.0, which puts a grid of "
        "identically-zero pinch points in the output (see test_noise_pinch.py): %s" % offenders)
