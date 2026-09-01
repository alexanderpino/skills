"""Anti-drift harness for the atomic bases (see `ATOM-COVERAGE.md`). Keeps three artifacts from
silently diverging: the chapter PSEUDOCODE (`references/`), the executable REFERENCE IMPL, and the
SCOPE STATEMENT (`ATOM-COVERAGE.md`). It does NOT prove the atoms are numerically correct — the
per-atom oracle tests (test_noise, test_ops_filters, the solver tests) do that. It proves the *set*
is consistent: nothing is claimed-but-missing, built-but-undocumented, or deferred-but-secretly-present
(the class of gap that had let Simplex/Gabor sit in the pseudocode with no implementation)."""
import ast
import functools
import importlib
import io
import re
import tokenize
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]                 # reference-impl/
SKILL_ROOT = REF.parent                                    # terrain-architect/

# --------------------------------------------------------------------------- #
# HOW EVERY ROW BELOW IS SEARCHED — AND WHY THE TWO SIDES SHARE ONE MATCHER.
#
# A needle that cannot miss is not a check. Four ways a needle goes vacuous, all of which had
# actually happened in this file:
#
#   1. FRONTMATTER. Every chapter opens with an OKF header written by `tools/okf_apply.py`, and
#      that header contains the literal text `okf v0.2`. The crater depth/diameter row searched
#      for the bare substring "0.2" — which the HEADER satisfies. Boilerplate the generator writes
#      is never evidence that a human documented anything, so it is stripped (`_body`) before any
#      search, and `test_no_searched_document_leaks_its_okf_header` proves the strip worked on
#      every document this file reads.
#   2. A NEEDLE THAT IS A SUBSTRING OF UNRELATED PROSE. "disc" is inside "discussed", "rect" is
#      inside "correctness", "0.2" is inside "g^(−0.22)". So no row here matches a bare substring.
#   3. A NEEDLE WITH NO TRAILING BOUNDARY. This is the same bug as (2) pointed the other way. It
#      survived TWO repairs. First the code side got a boundary and the doc side did not, so
#      `n = 3` still matched a chapter saying `n = 3.5` and `p = 1.1` matched `p = 1.15`; nine such
#      value drifts across six chapters left the suite green. The fix — one matcher, `_complete()`,
#      for both sides — closed that and left the boundary itself LOPSIDED: the lead excluded a sign
#      and the tail did not, so `n = 3` matched Cuffey's real range `n = 3-4` (and `n = 3–4`, and
#      `p = 1.1-1.5`), while a code literal `n=3` matched `def carve(H, n=3-1)`, which is 2. Worse,
#      an edge that was neither numeric nor wordish emitted NO tail at all, so `r⁻³` was satisfied
#      by `r⁻³·⁵`. A boundary on one side only is not a boundary: the two edges are now built from
#      ONE character set (`_NUM_EDGE`/`_WORD_EDGE`/`_MATH_EDGE`) so they cannot drift apart again.
#   4. A NAME FOUND IN PROSE RATHER THAN IN A LISTING. `hex_grid.ring` was satisfied by the
#      hyphenated English "one-ring" (the identifier scan does not treat `-` as part of a token)
#      and `noise.value` by "pure value maps". Listings in `ATOM-COVERAGE.md` live in backtick
#      code spans; prose does not. So the scope-doc rows read code spans only (`_code_spans`).
#   5. A NEEDLE SATISFIED BY AN UNRELATED SECTION. The document-wide search: `2650 kg/m³` was the
#      aeolian threshold's grain density, and the row passed on the SLOPE-STABILITY paragraph of
#      the same chapter, which quotes `ρs = 2650 kg/m³` for a landslide-mask worked example. Delete
#      the aeolian sentence entirely and the row stayed green. Same shape as (4) — evidence found
#      in the wrong place — and the same answer: every row names the one paragraph allowed to
#      satisfy it (`DOC_SECTION` for the scope rows, the `section` column for the faithfulness
#      rows), resolved by the one helper `_doc_paragraph`.
#
# Text is also whitespace-flattened before matching so a needle cannot be defeated by the chapter
# being re-wrapped across a line break, and `_complete` tolerates spacing differences *within* a
# needle (`n = 3` and `n=3` are the same claim) while still demanding the boundary.
#
# The matchers below are themselves unit-tested against fixture strings at the bottom of this
# file. A guard whose matcher has no tests is how this class of hole keeps recurring.

# Anchored on the END MARKER the generator writes, not on a bare `---`. A bare-`---` regex is
# right only by luck: a document with no frontmatter that opens with an hrule, or one whose block
# is closed by `----`, would have its whole first section (and every constant in it) DELETED
# before the search, and a document with two blocks would leak the boilerplate back.
_OKF_HEADER = re.compile(r"\A---\r?\n(?:[^\n]+\r?\n)*?# --- end okf v[0-9.]+ -+\r?\n---\r?\n")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CODE_SPAN = re.compile(r"`([^`]+)`")
_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.S | re.M)


def _body(path):
    """Doc text with the OKF frontmatter header removed (boilerplate is not documentation).

    If the header is not there in the exact shape the generator writes, NOTHING is removed —
    deleting a document's first real section is far worse than leaving a header in, and the
    corpus test below proves no searched document actually keeps one.
    """
    text = path.read_text(encoding="utf-8")
    m = _OKF_HEADER.match(text)
    return text[m.end():] if m else text


def _flat(text):
    """Whitespace-normalised, so a needle survives the chapter being re-wrapped."""
    return " ".join(text.split())


def _fenced(text):
    """Only the contents of ``` fenced blocks — i.e. the PSEUDOCODE, not the prose around it."""
    return "\n".join(_FENCE.findall(text))


def _code_spans(text):
    """Only the contents of `backtick` code spans — i.e. the LISTINGS, not the prose around them."""
    return " ".join(_CODE_SPAN.findall(text))


def _idents(text):
    """The whole identifiers in `text` — so "disc" is not found inside "discussed"."""
    return set(_IDENT.findall(text))


# --------------------------------------------------------------------------- #
# ONE completeness matcher, used by BOTH the code side and the doc side of a faithfulness row.

_WORDISH = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_."
_NUMERIC = "0123456789."
_TOKEN = re.compile(r"[A-Za-z0-9_.]+|\s+|[^\sA-Za-z0-9_.]+")

# THE CHARACTERS AN EDGE MAY NOT TOUCH — one set per kind of edge, used on BOTH sides of the
# literal. A lead-only exclusion is not a boundary: excluding a sign before the number while
# allowing one after it is what let `n = 3` match Cuffey's `n = 3-4` and a code literal `n=3` match
# `n=3-1`. Each set is therefore named once and spent twice, in `lead` and in `tail`.
#
# `_SIGNS` carries the ASCII sign, the six Unicode dashes U+2010..U+2015 (chapters write ranges with
# an EN DASH: `n = 3–4`) and the true MINUS SIGN U+2212 (the chapters use it: `g^(−0.22)`).
# `_SUPSUB` is the superscript/subscript block, which is how a chapter continues an exponent:
# `r⁻³` -> `r⁻³·⁵`, `D` -> `D₂`. `·` (U+00B7) is the DECIMAL POINT inside such a superscript, so it
# closes a `³`/`°`/`)` edge — but it is NOT in `_NUM_EDGE`, because next to an ordinary digit the
# same character is the chapters' MULTIPLICATION sign (`0.04·D`, `1.2·clip(...)`), and a constant
# that is multiplied by something is still that constant.
_SIGNS = "+\\-‐-―−"
_SUPSUB = "⁰-₟"
_NUM_EDGE = "0-9._" + _SIGNS + "°" + _SUPSUB          # `°`: `50` is not `50°`
_WORD_EDGE = "A-Za-z0-9_" + _SUPSUB
_MATH_EDGE = _SUPSUB + "·"                            # for an edge that is already punctuation


def _wordish(ch):
    return bool(ch) and ch in _WORDISH


def _numeric(ch):
    return bool(ch) and ch in _NUMERIC


@functools.lru_cache(maxsize=None)
def _pattern(literal):
    """Compile `literal` into a regex that matches it as a COMPLETE claim.

    Two jobs, and both sides of a faithfulness row need both:

    SPACING IS NOT MEANING. `n = 3` (PEP8), `n=3` and `KARMAN  =  0.4` (aligned) state the same
    constant, and a guard that rejects the spelling the author actually used turns the suite red
    with a message pointing at the wrong file. So each run of whitespace inside the literal becomes
    `\\s*` — or `\\s+` where dropping it would fuse two words ("MORE erodible").

    A PREFIX IS NOT A MATCH — AND NEITHER IS A SUFFIX. `n=3` must not be satisfied by `n=3.5`,
    `n=30`, `n=3e5` or `n=3_000`; `0.2 * D` must not be satisfied by the SIGN-FLIPPED `-0.2 * D`,
    and `n = 3` must not be satisfied by the RANGE `n = 3-4` or `n = 3–4` (Cuffey & Paterson quote
    Glen's exponent as 3-4; the code hardcodes 3, so a chapter widening it to a range is exactly
    the drift this row exists to catch). So the literal is bracketed by boundaries chosen from its
    own first and last characters, and the two edges use the SAME character set:

      * a numeric edge (`_NUM_EDGE`) may not touch another numeric char, an underscore/exponent/
        imaginary continuation, a sign or dash, a degree sign, or a superscript;
      * an identifier edge (`_WORD_EDGE`) may not touch another identifier char or a subscript;
      * an edge that is already punctuation (`(-3.0)`, `^2.2`, `r⁻³`, `33.7°`) carries most of its
        own boundary, so it gets only `_MATH_EDGE` — enough to stop a superscript being EXTENDED
        (`r⁻³` -> `r⁻³·⁵`), and no more, which is what lets the register keep literals that embed
        an operator without the sign rule fighting them.
    """
    toks = [t for t in _TOKEN.findall(literal) if t]
    parts, prev, gap = [], "", False
    for t in toks:
        if t.isspace():
            gap = True
            continue
        if parts:
            parts.append(r"\s+" if (gap and _wordish(prev[-1]) and _wordish(t[0])) else r"\s*")
        parts.append(re.escape(t))
        prev, gap = t, False
    if not parts:
        raise ValueError("empty literal")

    first, last = literal.strip()[0], literal.strip()[-1]
    if _numeric(first):
        lead = "(?<![A-Za-z" + _NUM_EDGE + "])"
    elif _wordish(first):                       # identifier start; `.` is allowed (`self.n=3`)
        lead = "(?<![" + _WORD_EDGE + "])"
    else:
        lead = "(?<![" + _MATH_EDGE + "])"
    if _numeric(last):
        tail = "(?![eEjJ" + _NUM_EDGE + "])"
    elif _wordish(last):
        tail = "(?![" + _WORD_EDGE + "])"
    else:
        tail = "(?![" + _MATH_EDGE + "])"
    return re.compile(lead + "".join(parts) + tail)


def _complete(text, literal):
    """True if `literal` occurs in `text` as a complete claim, not as a prefix of a longer one."""
    return _pattern(literal).search(text) is not None


def _strip_py_comments(src):
    """Source with comments and string literals blanked out (line/column layout preserved).

    A constant that appears only in a `#` comment or a docstring is prose, not code: the code side
    of a faithfulness row must not be satisfied by a module merely *talking* about the value it no
    longer uses.

    FAILURE IS LOUD, NOT SILENT. This used to `return src` unchanged when the source would not
    tokenise, under a `# pragma: no cover` — a note that the branch was untested, which is what an
    untested fallback usually is. Falling back to the raw source hands comments and docstrings back
    as searchable evidence, i.e. it disables exactly the thing this function exists to do, and the
    two `_CODE_REJECT` fixtures that pin it ("comment only", "docstring only") would stop holding
    without turning anything red. A reference module that does not parse is a defect in its own
    right, so it is raised — the same direction `test_slope_units.py` chose for the same call.
    """
    starts, off = [], 0
    for line in src.splitlines(keepends=True):
        starts.append(off)
        off += len(line)
    chars = list(src)

    def blank(a, b):
        for i in range(a, min(b, len(chars))):
            if chars[i] != "\n":
                chars[i] = " "

    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            name = tokenize.tok_name.get(tok.type, "")
            if name in ("COMMENT", "STRING") or name.startswith("FSTRING_MIDDLE"):
                (r1, c1), (r2, c2) = tok.start, tok.end
                blank(starts[r1 - 1] + c1, starts[r2 - 1] + c2)
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise AssertionError(
            f"source does not tokenise, so comments and docstrings cannot be stripped from it: "
            f"{exc}. Returning it unchanged would make prose searchable evidence again, which is "
            f"the hole this function exists to close — fix the module (or the fixture)") from exc
    return "".join(chars)


def _code_mentions(src, literal):
    """True if `literal` appears in module source as a COMPLETE literal, in CODE (not a comment)."""
    return _complete(_strip_py_comments(src), literal)


def _doc_states(chap, doc_str):
    """True if `doc_str` appears in the (flattened) chapter as a COMPLETE statement.

    The same matcher as `_code_mentions`, deliberately: the doc side having no boundary while the
    code side had one is exactly how nine value drifts crossed six chapters unnoticed.
    """
    return _complete(chap, doc_str)


COVERAGE_DOC = REF / "ATOM-COVERAGE.md"
COVERAGE = _body(COVERAGE_DOC)
# Listings live in code spans; prose does not. Deferred atoms are the one exception — they have no
# code to span, so they are named in bold prose, and only they are matched against the prose set.
COVERAGE_PROSE_NAMES = _idents(COVERAGE)

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
    "winds": ["wind_field", "terrain_adjust", "terrain_speedup", "upwind_slope", "lee_shelter",
              "valley_channel", "terrain_axis", "mass_consistent"],
    "aeolian": ["yardang", "shear_velocity", "threshold_shear", "saltation_flux",
                "transport_field", "saturate", "exner_step"],
    "tectonics": ["fault_scarp", "fault_weakness", "plate_uplift"],
    "hex_grid": ["basis", "cell_at", "sample", "ring", "disc", "laplacian6", "gradient6",
                 "hessian6"],
    "placement": ["disc", "rect", "capsule", "polygon", "path_mask", "apply_masked", "stamp",
                  "place_coords", "affine", "compose", "transform_coords", "sample_coords"],
}

# WHICH PARAGRAPH OF THE SCOPE DOC MUST CARRY EACH MODULE'S ATOMS.
#
# `test_scope_doc_lists_every_implemented_atom` used to assert `fn in <every name in the doc>`,
# with `module` used only in the failure message — so `placement.disc` was satisfied by hex_grid's
# listing and vice versa, and deleting the whole placement paragraph still left `placement.disc`
# passing on the hex line. The doc groups atoms by PROCESS, not by module (14 of the 18 modules
# have no paragraph naming their own `.py` file), so "one paragraph per module" would mean
# rewriting the doc. This register says instead, per module, WHICH paragraph is allowed to satisfy
# it — precise, and no doc edit. The paragraphs are blank-line separated; the anchor is matched
# against the flattened paragraph so a re-wrap cannot break it.
_SOLVERS = "Solver atoms (iterative, stateful"
DOC_SECTION = {
    "noise": "**Noise (`noise.py`",
    "ops_filters": "**SDF / gradient / combiner / tonal primitives (`ops_filters.py`",
    "placement": "**Placement & masking (`placement.py`",
    "hex_grid": "**Hexagonal working grid (`hex_grid.py`",
    "flow": _SOLVERS,
    "erosion_streampower": _SOLVERS,
    "erosion_droplet": _SOLVERS,
    "erosion_thermal": _SOLVERS,
    "diffusion": _SOLVERS,
    "erosion_pipe": _SOLVERS,
    "shallow_water": _SOLVERS,
    "meander": _SOLVERS,
    "braided": _SOLVERS,
    "glacier": _SOLVERS,
    "snow": _SOLVERS,
    "winds": _SOLVERS,
    "aeolian": _SOLVERS,
    "tectonics": _SOLVERS,
}

@functools.lru_cache(maxsize=None)
def _paragraphs(path):
    """A document's blank-line separated paragraphs, header-stripped and flattened.

    One implementation, used by BOTH registers that name a section — the scope rows' `DOC_SECTION`
    and the faithfulness rows' `section` column. The scope rows got this anchoring in the previous
    repair and the faithfulness rows did not, which is how `2650 kg/m³` went on being satisfied by
    a slope-stability worked example in another part of the same chapter.
    """
    return tuple(_flat(b) for b in re.split(r"\n[ \t]*\n", _body(path)) if b.strip())


def _doc_paragraph(path, anchor, why):
    """The ONE paragraph of `path` that `anchor` selects.

    Exactly one: an anchor that matches nothing is a row that can only fail, and an anchor that
    matches several has given back the document-wide search the column exists to remove. Either way
    the register — not the chapter — is what needs the edit, so say so.
    """
    hits = [p for p in _paragraphs(path) if anchor in p]
    assert len(hits) == 1, (
        f"the section register no longer resolves for {why}: {anchor!r} matches {len(hits)} "
        f"paragraphs of {path.name} (the document was restructured — move the anchor to the "
        f"paragraph that now carries the claim; do NOT widen it to match several)")
    return hits[0]


def _section(module):
    """The one paragraph of ATOM-COVERAGE.md that must carry `module`'s atoms."""
    return _doc_paragraph(COVERAGE_DOC, DOC_SECTION[module], module)


def _section_names(module):
    return _idents(_code_spans(_section(module)))


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
# generator family). This checks the generator is named as a ROUTINE IN THE PSEUDOCODE; it does NOT
# verify that the pseudocode's CONSTANTS match the code (e.g. a profile exponent) — prose-vs-code
# constant drift is caught by the review/faithfulness passes, not here.
#
# The chapters write routine names in camelCase (`alluvialFan`), the modules in snake_case — the same
# split `test_pseudocode_drift.py` handles with its own explicit name map. So each row declares BOTH
# names. Before this column existed, the `alluvial_fan` row had no pseudocode satisfier at all and was
# passing on one line of PROSE that happened to cite the Python name; deleting that prose failed the
# row while the pseudocode it is supposed to guard sat untouched.
#   python fn -> (chapter, pseudocode routine name)
GENERATORS = {
    "mountain": ("references/11-geological.md", "mountain"),
    "ridge": ("references/11-geological.md", "ridge"),
    "volcano": ("references/11-geological.md", "volcano"),
    "canyon": ("references/11-geological.md", "canyon"),
    "fault_block_butte": ("references/11-geological.md", "fault_block_butte"),
    "alluvial_fan": ("references/16-arid-desert.md", "alluvialFan"),
}
_GENERATOR_ROWS = [(fn, chapter, pseudo) for fn, (chapter, pseudo) in GENERATORS.items()]


def _public_callables(module_name):
    mod = importlib.import_module(module_name)
    return {n for n in vars(mod)
            if not n.startswith("_")
            and callable(getattr(mod, n))
            and getattr(getattr(mod, n), "__module__", None) == module_name}


def _norm_name(name):
    """`OpenSimplex2`, `open_simplex2` and `opensimplex2` are the same atom under different casings."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _ships_as(surface, target):
    """The names in `surface` under which the deferred atom `target` could have shipped.

    PREFIX, not equality, and only for the ABSENCE probe. Casing and underscores were normalised
    but VARIANT SUFFIXES were not, and the upstream names are `OpenSimplex2S` and `OpenSimplex2F`
    (smooth / fast) — the two spellings an author would actually write. Both normalise to something
    `!=` `opensimplex2`, so the atom could ship under its real name with this row still calling it
    absent, which is the same "deferred-but-secretly-present" gap the file opens by naming.

    This will also trip on a legitimately different `opensimplex2_gradient`, and that is the
    intended trade: a public name that close to a deferred atom is worth a human look, and the fix
    is one line in `DEFERRED` or `IMPLEMENTED`. The IMPLEMENTED cross-check below stays on
    EQUALITY — there the question is "is this the same atom", and a prefix would let an unrelated
    `simplex`-family entry answer it.
    """
    return sorted(n for n in surface if _norm_name(n).startswith(target))


@pytest.mark.parametrize("module,fn", _ATOMS)
def test_every_documented_atom_is_implemented(module, fn):
    """Each atom the manifest/scope-doc claims as implemented must exist as a callable (catches a
    documented-but-missing atom, or an implementation removed out from under the docs)."""
    mod = importlib.import_module(module)
    assert callable(getattr(mod, fn, None)), f"{module}.{fn} is claimed implemented but missing"


@pytest.mark.parametrize("module,fn", _ATOMS)
def test_scope_doc_lists_every_implemented_atom(module, fn):
    """The scope statement must name every implemented atom IN THAT MODULE'S OWN SECTION, as a
    code-span listing (doc <-> manifest stay in sync).

    Two ways this row used to be unable to fail, both fixed here:
      * MODULE-BLIND. It searched the whole document, so `placement.disc` passed on hex_grid's
        listing (and vice versa) and deleting the entire placement paragraph failed only 11 of its
        12 rows. It now searches only the paragraph `DOC_SECTION` assigns to the module.
      * PROSE. It searched every identifier in the doc, and the identifier scan does not treat `-`
        as part of a token, so `hex_grid.ring` was satisfied by the English "one-ring" and
        `noise.value` by "pure value maps". Listings live in backtick code spans; it now reads
        those only.
    """
    assert fn in _section_names(module), (
        f"{module}.{fn} implemented but not listed as `{fn}` in ATOM-COVERAGE.md's "
        f"{DOC_SECTION[module]!r} section (a listing elsewhere in the doc, or a mention in prose, "
        f"does not count — it is another module's claim)")


def test_no_two_modules_sharing_a_doc_section_can_satisfy_each_other():
    """What makes the shared solver paragraph safe, stated as itself.

    `DOC_SECTION` groups fourteen solver modules into one paragraph, so within that paragraph the
    scope-doc row is still name-based. That is sound only while no two of those modules ship an
    atom of the same NAME — otherwise one module's listing would silently satisfy the other's row,
    which is the very defect this register was written to close. Pin it.
    """
    collisions = {}
    for section in set(DOC_SECTION.values()):
        mods = [m for m in IMPLEMENTED if DOC_SECTION.get(m) == section]
        seen = {}
        for m in mods:
            for fn in IMPLEMENTED[m]:
                if fn in seen:
                    collisions.setdefault(section, []).append(f"{seen[fn]}.{fn} vs {m}.{fn}")
                seen[fn] = m
    assert not collisions, (
        "these modules share one ATOM-COVERAGE.md section AND an atom name, so each would satisfy "
        f"the other's listing row: {collisions}. Split the section, or qualify the listing.")


def test_noise_surface_has_no_undocumented_atom():
    """Reverse drift: every public function in noise.py must be in the manifest, so a new noise atom
    cannot be added to the code without being documented (this is exactly how Simplex/Gabor slipped)."""
    undocumented = _public_callables("noise") - set(IMPLEMENTED["noise"])
    assert not undocumented, f"undocumented noise atoms in code: {sorted(undocumented)}"


def test_ops_surface_is_fully_accounted_for():
    """Every public ops_filters function is either a listed atom or an explicit non-atom filter."""
    unaccounted = _public_callables("ops_filters") - set(IMPLEMENTED["ops_filters"]) - _OPS_NON_ATOM
    assert not unaccounted, f"ops_filters functions neither atom nor listed non-atom: {sorted(unaccounted)}"


@pytest.mark.parametrize("fn,chapter,pseudo", _GENERATOR_ROWS, ids=[r[0] for r in _GENERATOR_ROWS])
def test_landform_generators_are_documented(fn, chapter, pseudo):
    """Each landform generator must exist AND be called as a routine in its chapter's PSEUDOCODE — so a
    generator can't be added (or kept) as code-only. (Existence here; the load-bearing CONSTANTS are
    checked separately by test_key_constant_agrees_between_chapter_and_code below.)

    Searched inside ``` fenced blocks only, which is what "documented as a routine" has always meant.
    Over the whole chapter the row could not fail: `ridge`, `mountain` and `volcano` are ordinary
    English here (25, 3 and 12 occurrences), and the old `name\\s*(` pattern let prose-plus-parenthetical
    stand in for a call — "a freshly stripped ridge (thin soil)" and "blocked by a ridge (`09`)" both
    matched, so deleting the chapter's ONLY real `ridge(...)` routine header left the row green.
    A call has no space before its paren, so the `\\s*` is gone too.
    """
    lf = importlib.import_module("landforms")
    assert callable(getattr(lf, fn, None)), f"landforms.{fn} missing"
    blocks = _flat(_fenced(_body(SKILL_ROOT / chapter)))
    named = re.search(r"(?<![A-Za-z0-9_])" + re.escape(pseudo) + r"\(", blocks)
    assert named, (f"landforms.{fn} not documented as a routine (`{pseudo}(...)`) in a fenced "
                   f"pseudocode block of {chapter} — prose naming it does not count")


@pytest.mark.parametrize("fn,chapter,pseudo", _GENERATOR_ROWS, ids=[r[0] for r in _GENERATOR_ROWS])
def test_generator_pseudocode_names_are_declared_headers(fn, chapter, pseudo):
    """Companion to the row above: the DECLARED pseudocode name must be a routine HEADER, at the start
    of a line in a fenced block.

    This is what makes a rename fail loudly on either side rather than degrade into a prose match:
    rename the module function and `callable(...)` above fails; rename (or delete) the chapter's
    routine header and this fails; change one without updating this register and one of the two fails.
    """
    blocks = _fenced(_body(SKILL_ROOT / chapter))
    header = re.search(r"^[ \t]*" + re.escape(pseudo) + r"\(", blocks, re.M)
    assert header, (f"{chapter} has no `{pseudo}(...)` routine HEADER in a fenced block, but the "
                    f"register declares it as the pseudocode name of landforms.{fn} "
                    f"(renamed in the chapter? then rename it here and in landforms.py too)")


@pytest.mark.parametrize("name,chapter", DEFERRED.items())
def test_deferred_atoms_are_discussed_but_absent(name, chapter):
    """A deferred atom must be genuinely absent from the code, yet actually discussed in its chapter
    and listed in the scope doc — so 'deferred' is an honest, checked status, not a silent gap.

    Absence is probed against the module's whole public surface with BOTH sides case/underscore
    normalised and the surface side matched by PREFIX: the old `hasattr(mod, name.lower())` probed
    `opensimplex2`, while the name a Python author actually writes is `open_simplex2` — so the atom
    could ship, be listed as implemented, and still be called deferred here, with every row green.
    Normalising alone was not enough either: the upstream variants are `OpenSimplex2S`/`2F`, so
    equality still let the atom ship under its real name (see `_ships_as`). The manifest is
    cross-checked too: a name cannot honestly sit in both registers.
    """
    mod = importlib.import_module("noise")
    target = _norm_name(name)
    surface = [n for n in vars(mod) if not n.startswith("_")]
    shipped = _ships_as(surface, target)
    assert not shipped, (
        f"{name} is listed deferred but noise exposes it (as {shipped}) — it shipped; move it to "
        f"IMPLEMENTED and out of the deferred list. If that name is genuinely a DIFFERENT atom "
        f"that merely starts the same way, say so by renaming one of them: a public noise name "
        f"this close to a deferred atom is not something to resolve silently")
    both = [f"{m}.{f}" for m, fns in IMPLEMENTED.items() for f in fns if _norm_name(f) == target]
    assert not both, f"{name} is listed BOTH deferred and implemented ({both}) — pick one"
    assert name in _idents(_body(SKILL_ROOT / chapter)), f"{name} not discussed in {chapter}"
    assert name in COVERAGE_PROSE_NAMES, f"deferred {name} not listed in ATOM-COVERAGE.md"


# --------------------------------------------------------------------------- #
# FAITHFULNESS: the chapter pseudocode and the code must agree on the key physical CONSTANTS.
# The tests above prove an atom exists and is named in its chapter; they do NOT prove the numbers
# match. This closes that gap for the physically-load-bearing constants (the ones whose value IS
# the correctness of the atom): each is triangulated — the literal must appear in the reference
# MODULE source AND its documented value/statement must appear in the CHAPTER (or the citation
# ledger). Change one side without the other and this fails, forcing a synchronised edit — the
# contributor rule, mechanised. Sampled (the load-bearing constants), not exhaustive; a defect here
# is prose-vs-code DRIFT, not numeric wrongness (the oracle/benchmark/cross-val tests cover that).
#
# BOTH sides go through `_complete`. Carrying a SYMBOL or UNIT next to the number — which is all the
# doc side used to do — makes a needle longer, not complete: "n = 3" still matched a chapter saying
# "n = 3.5". The needle must be unique to the CLAIM, so it needs the symbol AND the boundary.
#
# WHAT BELONGS IN A CODE LITERAL, since `_complete` now rejects a leading sign. Write the literal as
# the assignment or expression the module actually contains, INCLUDING any operator that is part of
# the constant's meaning — `(-3.0)` and `(1.0 - rn) ** 2.2` are correct as written, and their
# punctuation edges are their own boundaries. What the sign rule forbids is a bare `0.2 * D` being
# satisfied by `-0.2 * D`: flipping a sign is a change of physics, not of spelling. Spacing is free
# — `n=3`, `n = 3` and `n  =  3` are all the same row.
#
# AND WHICH PARAGRAPH OF THE CHAPTER IS ALLOWED TO SATISFY THE DOC SIDE (the `section` column).
# Without it the doc side searched the WHOLE chapter, and six of these nineteen rows had more than
# one satisfier. Two of the six were not restatements of the claim at all but unrelated text that
# happened to contain the same characters:
#   * `2650 kg/m³` — the aeolian threshold's quartz density was ALSO satisfied by the SLOPE-
#     STABILITY paragraph's worked example ("at `ρs = 2650 kg/m³` instead, the correct threshold
#     moves to 29.60°"). Delete the aeolian sentence and the row passed on landslide-mask prose.
#   * `0.04·D` — the crater rim ratio had three satisfiers, one of them the `crater_demo.py`
#     PRESENTATION paragraph. Change the pseudocode's rim to `0.10·D` and the row passed on prose
#     describing a demo script.
# The other four (`n = 3` x3, `917 kg/m³` x2, `p = 1.1` x2, `tan(15°)` x2 in 13) ARE genuine
# restatements of one claim — but "genuine restatement" versus "unrelated text that happens to
# match" is a judgement made by eye, and a judgement made by eye is exactly what a register is for
# writing down. So every row is anchored, and the anchor names the paragraph that is the ROW'S OWN
# evidence: the pseudocode block or the sentence that defines the constant, not a later pointer.
FAITHFUL = [
    # (module, code literal in the module source, chapter/doc file, string that must be in that
    #  doc, anchor selecting the ONE paragraph allowed to carry it, what)
    ("dunes.py", "shadow_tan=0.268", "references/05-erosion-thermal-aeolian.md", "tan(15°)",
     "inShadowZone(h, p, windDir): for k",   # the routine, not the call site in the dune loop
     "Werner lee shadow line = 15deg flow-separation angle (tan 15 = 0.268)"),
    ("dunes.py", "repose=2", "references/99-papers.md", "33.7°",
     "The Physics of Blown Sand",
     "sand angle of repose 33.7deg = atan(2/3), the 2-slab drop under the 1:3 slab aspect"),
    ("landforms.py", "(1.0 - rn) ** 2.2", "references/11-geological.md", "^2.2",
     "VOLCANO — a radial edifice",
     "stratovolcano concave-up flank profile exponent (Karatson 2010)"),
    ("landforms.py", "0.2 * D", "references/11-geological.md", "d/D ~0.2",
     "crater(D): R = D/2",
     "impact-crater depth/diameter ~= 0.2 (Pike 1977)"),
    ("landforms.py", "0.04 * D", "references/11-geological.md", "0.04·D",
     "crater(D): R = D/2",              # the pseudocode's `rimCrest`, NOT crater_demo's prose
     "impact-crater rim height ~= 0.04 D"),
    ("landforms.py", "(-3.0)", "references/11-geological.md", "r⁻³",
     "**Simple crater** (small)",
     "impact-crater ejecta blanket thins as r^-3 (McGetchin 1973)"),
    ("glacier.py", "rho=917.0", "references/12-glacial-coastal.md", "917 kg/m³",
     "ice thickness evolves by mass conservation",
     "glacier ice density 917 kg/m^3"),
    ("glacier.py", "n=3", "references/12-glacial-coastal.md", "n = 3",
     "ε̇ = A · τⁿ",                     # the flow law itself, not the two paragraphs about it
     "Glen flow-law exponent n = 3"),
    ("landforms.py", "concavity=1.7", "references/16-arid-desert.md", "concave downfan",
     "landforms.alluvial_fan(",
     "alluvial-fan concave (steep-apex, gentle-distal) downfan profile (Blair & McPherson 1994)"),
    ("flow.py", "p=1.1", "references/03-flow-routing.md", "p = 1.1",
     "mfd(dem, c,",                     # the routine's own default, not the prose discussing it
     "MFD multiple-flow-direction exponent p = 1.1 (Freeman 1991)"),
    ("isostasy.py", "nu=0.25", "references/02-macro-tectonics.md", "ν ≈ 0.25",
     "(Young's modulus)",
     "crustal Poisson ratio nu = 0.25 in flexural rigidity D = E*Te^3 / 12(1-nu^2)"),
    ("winds.py", "shadow_tan=0.268", "references/13-climate-ecosystem.md", "tan(15°)",
     "The 15° shadow line is physics",  # not the closing `Runnable reference:` pointer
     "lee-shelter shadow line = the same 15deg flow-separation angle as Werner's dune shadow (05)"),
    ("aeolian.py", "A=0.1", "references/05-erosion-thermal-aeolian.md", "A ≈ 0.1",
     "for turbulent flow",
     "Bagnold threshold coefficient A ~ 0.1 for turbulent flow"),
    ("aeolian.py", "RHO_QUARTZ = 2650.0", "references/05-erosion-thermal-aeolian.md", "2650 kg/m³",
     "for turbulent flow",              # NOT the slope-stability worked example, which also says 2650
     "quartz grain density 2650 kg/m^3 in the threshold friction velocity"),
    ("aeolian.py", "RHO_AIR = 1.22", "references/05-erosion-thermal-aeolian.md", "1.22 kg/m³",
     "for turbulent flow",
     "sea-level air density 1.22 kg/m^3 in the threshold and the saltation flux"),
    ("aeolian.py", "KARMAN = 0.4", "references/13-climate-ecosystem.md", "κ = 0.4",
     "law of the wall",
     "von Karman constant 0.4 in the law of the wall converting wind SPEED to friction velocity"),
    ("snow.py", "shed_lo_deg=50.0", "references/13-climate-ecosystem.md", "tan(50°)",
     "Snow doesn't stick to steep ground",
     "snow sheds off ground steeper than 50deg (smoothstep 50->60deg; Cordonnier 2018)"),
    ("snow.py", "shed_hi_deg=60.0", "references/13-climate-ecosystem.md", "tan(60°)",
     "Snow doesn't stick to steep ground",
     "snow fully shed by 60deg"),
    ("tectonics.py", "k_fault=6.0", "references/02-macro-tectonics.md", "MORE erodible",
     "`fault_weakness` is the K(x,y) coupling",
     "fault-as-K SIGN: a fault trace is WEAK rock -> HIGHER erodibility, so valleys follow structure"),
]

# Every document this file searches — each must strip its OKF header cleanly (see F9 below).
_SEARCHED_DOCS = sorted({COVERAGE_DOC}
                        | {SKILL_ROOT / c for c in DEFERRED.values()}
                        | {SKILL_ROOT / c for c, _ in GENERATORS.values()}
                        | {SKILL_ROOT / e[2] for e in FAITHFUL},
                        key=lambda p: str(p))


@pytest.mark.parametrize("module,code_lit,doc,doc_str,section,what", FAITHFUL,
                         ids=[e[0] + ":" + e[1] for e in FAITHFUL])
def test_key_constant_agrees_between_chapter_and_code(module, code_lit, doc, doc_str, section, what):
    """A load-bearing physical constant must read the same in the code and in its chapter (faithfulness,
    not just existence). Fails on prose<->code drift, so neither side can move alone.

    The chapter is searched with its OKF frontmatter stripped and its whitespace flattened: header
    boilerplate must not be able to satisfy a row (it silently satisfied the crater d/D row), and a
    re-wrapped line must not be able to break one. BOTH sides use `_complete`, so a chapter that
    changes `n = 3` to `n = 3.5` — or to the range `n = 3-4` — fails here instead of quietly still
    matching.

    And the doc side reads ONE PARAGRAPH, the one the `section` column names. Over the whole
    chapter the row asks "does this string appear anywhere in thirty pages", which the aeolian
    grain density answered on a landslide-mask worked example and the crater rim ratio on a
    paragraph about a demo script — both rows survived deleting the claim they guard.
    """
    src = (REF / module).read_text(encoding="utf-8")
    assert _code_mentions(src, code_lit), \
        f"{what}: code literal {code_lit!r} missing from reference-impl/{module} " \
        f"(the code constant changed — update the code, or fix this manifest AND the chapter)"
    para = _doc_paragraph(SKILL_ROOT / doc, section, f"{module}:{code_lit}")
    assert _doc_states(para, doc_str), \
        f"{what}: {doc_str!r} missing from the {section!r} paragraph of {doc} " \
        f"(the chapter drifted from the code constant {code_lit!r} — resync the pseudocode. " \
        f"The same string elsewhere in the chapter does NOT count: this row's evidence is that " \
        f"paragraph, and a needle satisfiable by an unrelated section is not a check)"


def _assert_no_okf_leak(path):
    """`_body` must actually have removed the generator boilerplate from `path`.

    `_body` is deliberately conservative — a document whose header is not in the exact shape
    `tools/okf_apply.py` writes is left untouched rather than having its first section deleted. That
    safety has a cost: the strip could silently stop happening (a second frontmatter block ahead of
    the header, a reformatted end marker). So the outcome is asserted directly, and loudly.
    """
    body = _body(path)
    assert "okf v" not in body, (
        f"{path.name} still carries its OKF header after _body() — generator boilerplate is now "
        f"searchable evidence (the `okf v0.2` in it once satisfied the crater d/D row by itself)")
    assert not body.lstrip().startswith("---\n"), \
        f"{path.name} still opens with a frontmatter fence after _body()"


@pytest.mark.parametrize("path", _SEARCHED_DOCS, ids=[p.name for p in _SEARCHED_DOCS])
def test_no_searched_document_leaks_its_okf_header(path):
    """Corpus-wide: every document this file searches must strip its header cleanly."""
    _assert_no_okf_leak(path)


# =========================================================================== #
# UNIT TESTS FOR THE MATCHERS THEMSELVES.
#
# Every hole repaired above was a hole in one of these four functions, and each was found by a
# reader trying strings against them by hand — never by a test, because the matchers had none and
# were only ever exercised through the corpus, which by construction contains only strings that
# pass. These fixtures are the cases that broke them.

_DOC_ACCEPT = [
    ("n = 3", "with n = 3, A ≈ 2.4e-24 Pa⁻³ s⁻¹"),
    ("n = 3", "ε̇ = A · τⁿ with n=3 at 0 °C"),            # spacing is not meaning
    ("p = 1.1", "**`p = 1.1` is Freeman's calibrated value**"),
    ("d/D ~0.2", "bowl (paraboloid) to depth d(D) # d/D ~0.2 simple, less if complex"),
    ("A ≈ 0.1", "`A ≈ 0.1` for turbulent flow"),
    ("ν ≈ 0.25", "`ν ≈ 0.25` (Poisson), and `Te` the"),
    ("κ = 0.4", "von Karman `κ = 0.4` in the law of the wall"),
    ("^2.2", ": (1 - rn)^2.2 # strato: CONCAVE-UP sweep"),
    ("917 kg/m³", "with `ρ_ice ≈ 917 kg/m³`. Then ice thickness"),
    ("917 kg/m³", "| `ρ_ice` | 917 kg/m³ | | | `β` (mass balance) |"),   # a table cell
    ("33.7°", "angle of repose **33.7°** = tan⁻¹(2/3)"),
    ("concave downfan", "with a concave downfan thinning profile"),
    ("r⁻³", "thinning roughly as `r⁻³`; depth ≈ 1/5 of diameter"),
    ("0.04·D", "rimCrest ~ 0.04·D above the surroundings (Pike 1977 ratios)"),
    # The tail must not over-reach: `·` is the chapters' MULTIPLICATION sign next to a digit, and a
    # constant that is multiplied by something is still that constant.
    ("1.2", "ecc = 1 + 1.2·clip((12−angle)/12, 0, 1)"),
    ("0.88", "azw = 0.12 + 0.88·w"),
]

# HOW A CHAPTER ACTUALLY DRIFTS. Ten of these are the critic's original nine value drifts plus a
# word drift — a chapter edited to a NEARBY value, no code change — and every one used to pass
# because a bare `in` has no trailing boundary. The rest are the SECOND generation, which survived
# that repair because the boundary it added was one-sided: a range, a sign, a Unicode dash, a
# continued superscript. Appending a digit ten different ways is one fixture written ten times, and
# a fixture set that rehearses one drift proves the matcher against one drift.
_DOC_REJECT = [
    ("n = 3", "with n = 3.5, A ≈ 2.4e-24 Pa⁻³ s⁻¹"),          # Glen 3 -> 3.5
    ("n = 3", "with n = 30"),
    ("p = 1.1", "**`p = 1.15` is Freeman's calibrated value**"),   # Freeman 1.1 -> 1.15
    ("A ≈ 0.1", "`A ≈ 0.15` for turbulent flow"),                 # Bagnold 0.1 -> 0.15
    ("ν ≈ 0.25", "`ν ≈ 0.255` (Poisson)"),                        # Poisson 0.25 -> 0.255
    ("κ = 0.4", "von Karman `κ = 0.45` in the law of the wall"),   # von Karman 0.4 -> 0.45
    ("d/D ~0.2", "to depth d(D) # d/D ~0.25 simple"),             # crater d/D 0.2 -> 0.25
    ("^2.2", ": (1 - rn)^2.25 # strato: CONCAVE-UP sweep"),       # stratovolcano 2.2 -> 2.25
    ("917 kg/m³", "with `ρ_ice ≈ 9170 kg/m³`"),
    ("concave downfan", "with a concave downfanning profile"),
    # --- the drift the one-sided boundary let through. A RANGE is not the value: Cuffey & Paterson
    # quote Glen's exponent as 3-4 and Freeman's p as a band, while the code hardcodes one number.
    ("n = 3", "Glen's exponent n = 3-4 for real ice"),            # ASCII hyphen
    ("n = 3", "with n = 3–4 (Cuffey & Paterson)"),                # EN DASH, how a chapter writes it
    ("n = 3", "with n = 3−4 (Cuffey & Paterson)"),                # true MINUS SIGN U+2212
    ("p = 1.1", "p = 1.1-1.5 band"),
    ("A ≈ 0.1", "`A ≈ 0.1+0.02` for turbulent flow"),             # trailing sign, not just leading
    ("κ = 0.4", "von Karman `κ = 0.4°` (a different quantity)"),
    # --- ...and the same drift in a superscript, where NO tail was emitted at all.
    ("r⁻³", "ejecta thinning as `r⁻³·⁵` in the far field"),       # `·` = the decimal point up here
    ("r⁻³", "ejecta thinning as `r⁻³⁵`"),
    ("917 kg/m³", "with `ρ_ice ≈ 917 kg/m³⁴`"),
    ("0.04·D", "rimCrest ~ 0.04·D₂ above the surroundings"),      # subscripted variable
]


# WHAT IS STILL NOT CAUGHT, stated rather than left to be discovered: an operator separated from
# the constant by whitespace (`n = 3 - 1`, `n = 3 – 4`). The boundary is a lookaround on the
# adjacent character, and widening it across whitespace would fail the mirror-image case, where a
# constant legitimately FOLLOWS an operator — `azw = 0.12 + 0.88·w` would stop matching `0.88`.
# The corpus decides which risk is real: these chapters write ranges closed up (`~10–20 km`,
# `0.005–0.01 /yr`, `70–100 GPa`), which is the form that is now rejected.


@pytest.mark.parametrize("needle,text", _DOC_ACCEPT, ids=[n for n, _ in _DOC_ACCEPT])
def test_doc_states_accepts_the_real_chapter_wording(needle, text):
    assert _doc_states(text, needle), f"{needle!r} should be found in {text!r}"


@pytest.mark.parametrize("needle,text", _DOC_REJECT, ids=[n + " vs " + t[:24] for n, t in _DOC_REJECT])
def test_doc_states_rejects_a_drifted_value(needle, text):
    assert not _doc_states(text, needle), \
        f"{needle!r} must NOT be satisfied by the drifted {text!r} — a needle with no trailing " \
        f"boundary is how nine chapter drifts stayed green"


# `_code_mentions` used to be a prefix test with no left-hand sign rule, no comment stripping and a
# plain bug: `after not in "0123456789."` is False when `after == ""`, because `"" in s` is always
# True — so a literal at end-of-file was rejected.
_CODE_ACCEPT = [
    ("n=3", "def glacier_carve(bed, H, steps, *, A=_A_YR, n=3, rho=917.0):"),
    ("n=3", "n = 3\n"),                                   # PEP8 spacing
    ("n=3", "self.n=3\n"),                                # attribute assignment
    ("KARMAN = 0.4", "KARMAN  =  0.4  # aligned with the block below\n"),
    ("KARMAN = 0.4", "KARMAN=0.4\n"),
    ("0.2 * D", "depth = 0.2*D * scale\n"),               # spaces removed
    ("0.2 * D", "    depth = 0.2 * D * ((complex_D / D) ** 0.3)\n"),
    ("k_fault=6.0", "def fault_weakness(shape, *, k_fault=6.0)"),   # ... and at EOF:
    ("k_fault=6.0", "k_fault=6.0"),                       # no trailing newline: `after` is ""
    ("(-3.0)", "ejecta = rim * 0.5 * (np.maximum(r, R) / R) ** (-3.0)\n"),
    ("(1.0 - rn) ** 2.2", "prof = (1.0 - rn) ** 2.2\n"),
    ("(1.0 - rn) ** 2.2", "prof = (1.0-rn)**2.2\n"),
]

_CODE_REJECT = [
    ("n=3", "n=3_000\n"),                                 # underscore-grouped literal
    ("n=3", "n=3e5\n"),                                   # exponent
    ("n=3", "n=3.5\n"),
    ("n=3", "n=30\n"),
    ("0.2 * D", "depth = -0.2 * D\n"),                    # SIGN FLIP: not the same constant
    ("0.2 * D", "depth = 10.2 * D\n"),
    # The lead had a sign rule and the tail did not, so an arithmetic edit on the RIGHT of the
    # constant read as the constant: `n=3-1` is 2, and it satisfied `n=3`.
    ("n=3", "def carve(H, n=3-1):\n"),
    ("n=3", "def carve(H, n=3+1):\n"),
    ("n=3", "# the old default was n=3; we now ship 4\n"),          # comment only
    ("n=3", '"""Historically n=3 (Glen); this module no longer uses it."""\n'),   # docstring only
    ("KARMAN = 0.4", "KARMAN = 0.45\n"),
]


@pytest.mark.parametrize("lit,src", _CODE_ACCEPT, ids=[f"{l}|{s[:28]!r}" for l, s in _CODE_ACCEPT])
def test_code_mentions_accepts_the_spellings_authors_actually_write(lit, src):
    assert _code_mentions(src, lit), (
        f"{lit!r} should be found in {src!r} — a false REJECT here has no backstop and turns the "
        f"suite red with a message pointing at the wrong file")


@pytest.mark.parametrize("lit,src", _CODE_REJECT, ids=[f"{l}|{s[:28]!r}" for l, s in _CODE_REJECT])
def test_code_mentions_rejects_a_drifted_or_prose_only_constant(lit, src):
    assert not _code_mentions(src, lit), f"{lit!r} must NOT be satisfied by {src!r}"


def test_strip_py_comments_preserves_code_and_layout():
    src = 'A = 1  # A = 2\n"""A = 3"""\nB = 4\n'
    out = _strip_py_comments(src)
    assert _complete(out, "A = 1") and _complete(out, "B = 4")
    assert not _complete(out, "A = 2") and not _complete(out, "A = 3")
    assert out.count("\n") == src.count("\n")


def test_a_module_that_does_not_tokenise_fails_loudly_instead_of_searching_its_comments():
    """The direction the tokenise failure is handled in, pinned — because it used to be the other
    one, under a `# pragma: no cover`.

    `return src` on failure re-admits comments and docstrings as evidence: the source below states
    the constant ONLY in a comment, and the two `_CODE_REJECT` rows that pin comment-only and
    docstring-only prose would have gone on passing while this file's real job silently stopped.
    """
    prose_only = "# the old default was n=3; we now ship 4\nx = (\n"     # the `(` is unbalanced
    assert re.search("n=3", prose_only), "fixture states the constant in a COMMENT and nowhere else"
    with pytest.raises(AssertionError, match="does not tokenise"):
        _code_mentions(prose_only, "n=3")


def test_idents_does_not_split_a_hyphenated_word_into_atom_names():
    """The `_idents` behaviour that made `hex_grid.ring` unable to fail, stated as itself.

    `-` is not an identifier character, so the scan legitimately reports "one-ring" as {one, ring}.
    That is not a bug in `_idents`; it is a bug in using `_idents` over PROSE to answer "is this
    atom LISTED?". The fix is the input, not the matcher: listings are read from code spans.
    """
    assert _idents("gradient6 (one-ring world-space gradient)") >= {"one", "ring"}
    assert _idents("pure value maps") >= {"value"}
    # ...and the code-span reading, which is what the scope rows now use, sees neither.
    prose = "`gradient6` (one-ring world-space gradient), `laplacian6`, pure value maps"
    assert _idents(_code_spans(prose)) == {"gradient6", "laplacian6"}
    assert "ring" not in _idents(_code_spans(prose))
    assert "value" not in _idents(_code_spans(prose))


_OKF = ("---\n# --- okf v0.2, written by tools/okf_apply.py ---\n"
        "title: x\n# --- end okf v0.2 ---------\n---\n")


def test_body_strips_the_generator_header_and_nothing_else(tmp_path):
    p = tmp_path / "a.md"
    p.write_text(_OKF + "# Real title\n\nbody 0.2 here\n", encoding="utf-8")
    assert _body(p) == "# Real title\n\nbody 0.2 here\n"


# Each fixture is a document the bare-`---` regex DELETES the first section of — the constant below
# sits inside the region that regex swallows, so these cases fail against it and pass against the
# OKF-anchored one. (A fixture whose constant sits *after* the swallowed region passes either way and
# would pin nothing — which is the same mistake as a needle with no boundary, one level up.)
@pytest.mark.parametrize("text,why", [
    ("---\nconstant n = 3 lives here\n---\ntail\n",
     "a document with NO frontmatter that opens with an hrule"),
    ("---\ntitle: x\n----\nconstant n = 3 lives here\n---\ntail\n",
     "a frontmatter block closed by `----`, so the strip runs on to the next rule"),
])
def test_body_never_deletes_a_real_section(tmp_path, text, why):
    """`_body` anchored on a bare `---` was safe only by luck.

    It assumed the file opens with `---`, closes with exactly `---`, and has one block. Each shape
    here breaks one of those assumptions, and `\\A---\\r?\\n.*?\\r?\\n---\\r?\\n` answers by DELETING
    everything up to the next `---` line — every constant in it — so a faithfulness row would fail
    pointing at a chapter that says exactly what it should. Anchoring on the end marker the generator
    actually writes means an unrecognised header is left alone instead.
    """
    p = tmp_path / "b.md"
    p.write_text(text, encoding="utf-8")
    assert "constant n = 3 lives here" in _body(p), f"_body ate a real section: {why}"


def test_body_leaves_a_document_with_no_frontmatter_untouched(tmp_path):
    p = tmp_path / "c.md"
    p.write_text("# Title\n\nn = 3\n", encoding="utf-8")
    assert _body(p) == "# Title\n\nn = 3\n"


def test_a_leaked_okf_header_is_caught_loudly_rather_than_silently_searched(tmp_path):
    """The other half of F9: the conservative `_body` can leave a header in, and that must be LOUD.

    A second frontmatter block ahead of the OKF one defeats the `\\A` anchor, so `_body` returns the
    boilerplate — and boilerplate is searchable evidence (`okf v0.2` once satisfied the crater d/D
    row by itself). `_assert_no_okf_leak`, run over every searched document, is what turns that from
    a silent vacuous row into a failure.
    """
    p = tmp_path / "d.md"
    p.write_text("---\nfirst: block\n---\n\n" + _OKF + "body\n", encoding="utf-8")
    assert "okf v" in _body(p), "fixture should leak — _body is conservative, not magic"
    with pytest.raises(AssertionError, match="OKF header"):
        _assert_no_okf_leak(p)


def test_fenced_reads_pseudocode_only():
    doc = ("A freshly stripped ridge (thin soil) produces talus; blocked by a ridge (`09`).\n"
           "```\nridge(shape, asymmetry):\n    s0 = ...\n```\nmore prose about a ridge (really).\n")
    blocks = _fenced(doc)
    assert "ridge(shape" in blocks
    assert "thin soil" not in blocks and "really" not in blocks
    # the pattern the generator rows use: prose-plus-parenthetical is NOT a call
    call = r"(?<![A-Za-z0-9_])ridge\("
    assert re.search(call, _flat(blocks))
    assert not re.search(call, _flat("A freshly stripped ridge (thin soil) produces talus."))


def test_norm_name_sees_through_the_casing_a_deferred_atom_could_ship_under():
    assert _norm_name("OpenSimplex2") == _norm_name("open_simplex2") == "opensimplex2"
    assert _norm_name("Wavelet") == "wavelet"


def test_a_deferred_atom_cannot_ship_under_its_upstream_variant_name():
    """Casing was normalised; the VARIANT SUFFIX was not.

    `OpenSimplex2S` and `OpenSimplex2F` are the actual upstream names (smooth and fast), so they
    are what a contributor implementing the deferred atom would write — and under equality both
    answered "not present", leaving the atom shipped and still called deferred.
    """
    target = _norm_name("OpenSimplex2")
    for shipped_as in ("OpenSimplex2S", "OpenSimplex2F", "open_simplex2f", "opensimplex2"):
        assert _ships_as(["fbm", "perlin", shipped_as], target) == [shipped_as]
        # ...and equality, which is what the row used to use, sees none of the variants:
        assert (_norm_name(shipped_as) == target) is (shipped_as == "opensimplex2")
    # an unrelated atom is not swept up just for containing "simplex"
    assert _ships_as(["simplex", "value", "worley"], target) == []


# --------------------------------------------------------------------------- #
# A NEEDLE SATISFIED BY AN UNRELATED SECTION — the vacuity the fixture sets had no case for, and
# the reason the faithfulness rows carry a `section` column.

_TWO_SECTION_CHAPTER = (
    "## Threshold of motion\n\n"
    "`A ≈ 0.1` for turbulent flow, `ρ_s` ≈ 2650 kg/m³ (quartz), `ρ_a` ≈ 1.22 kg/m³, `d` = grain\n"
    "diameter.\n\n"
    "## Slope stability\n\n"
    "At `φ = 35°` and `ρs = 2650 kg/m³` instead, the correct threshold moves to 29.60°.\n")


def test_a_needle_satisfied_by_an_unrelated_section_is_not_evidence(tmp_path):
    """The exact shape of the aeolian grain-density row, on a two-paragraph fixture chapter.

    Both paragraphs contain `2650 kg/m³`, and only the first one is the row's claim — the second is
    a landslide-mask worked example that happens to quote the same density. So the document-wide
    search cannot tell the aeolian threshold being REWRITTEN to basalt from it being intact, and
    `_doc_paragraph` can.
    """
    intact, drifted = tmp_path / "intact.md", tmp_path / "drifted.md"
    intact.write_text(_TWO_SECTION_CHAPTER, encoding="utf-8")
    drifted.write_text(_TWO_SECTION_CHAPTER.replace("2650 kg/m³ (quartz)", "3300 kg/m³ (basalt)"),
                       encoding="utf-8")

    anchor = "for turbulent flow"
    assert _doc_states(_doc_paragraph(intact, anchor, "fixture"), "2650 kg/m³")

    # The claim is gone — the chapter now documents basalt — yet the whole document still says the
    # string, in the OTHER section. This is what the row used to be asked.
    assert _doc_states(_flat(_body(drifted)), "2650 kg/m³"), \
        "fixture must keep an unrelated satisfier, or it pins nothing"
    # Asked of the paragraph the register names, it fails, which is the point.
    assert not _doc_states(_doc_paragraph(drifted, anchor, "fixture"), "2650 kg/m³")


def test_an_anchor_that_stops_selecting_one_paragraph_fails_the_row(tmp_path):
    """`_doc_paragraph` must refuse ambiguity rather than pick a winner.

    An anchor matching two paragraphs is the document-wide search creeping back in, and an anchor
    matching none is a row that can only ever fail with a message blaming the chapter. Both are
    edits to the REGISTER, so both say so.
    """
    p = tmp_path / "amb.md"
    p.write_text("the same anchor here\n\nand the same anchor here too\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="matches 2 paragraphs"):
        _doc_paragraph(p, "the same anchor", "fixture")
    with pytest.raises(AssertionError, match="matches 0 paragraphs"):
        _doc_paragraph(p, "an anchor that is not there", "fixture")


# --------------------------------------------------------------------------- #
# THE ENUMERATION ITSELF — GLOBBED OFF THE FILESYSTEM, NOT HAND-WRITTEN.
#
# Every row above this line is keyed on `IMPLEMENTED`, a hand-maintained dict of 91 atom names
# across 18 modules, and a hand-written enumeration cannot see what it forgot. `reference-impl/`
# ships 44 modules; the register above reaches 21 of them (the 18 `IMPLEMENTED` keys, plus
# `landforms` via `GENERATORS` and `dunes`/`isostasy` via `FAITHFUL`) — 47.7%. The other 23 are
# outside the guard entirely: a module that is in neither dict is neither required to be documented
# nor reported as undocumented. Ship a new solver, leave it out of `ATOM-COVERAGE.md`, and every
# row above stays green. That is the hole this section closes, and it is the SIXTH way a needle
# goes vacuous, the one the five at the top of this file do not cover: not "the needle matches
# something it shouldn't" but "there is no needle at all, because the list forgot the file".
#
# So the module set is `REF.glob("*.py")`, and every one of the 44 must land in exactly one of
# three buckets — the classification rule, written down:
#
#   DOC_NAMED     DERIVED, not written: the module's own name appears inside an ATOM-COVERAGE.md
#                 BACKTICK CODE SPAN (`noise.py`, `flow.priority_flood_fill`). Prose does not
#                 count, for reason (4) at the top of this file. These are the modules the scope
#                 doc claims, so these are the modules that carry the symbol-level obligation
#                 below. Nothing hand-written selects them: document a module and it joins.
#   HARNESS       Infrastructure, figure and demo code — it renders a picture, drives a demo, moves
#                 bytes on and off disk, or is pytest plumbing. Not a terrain operator, so the atom
#                 register does not scope it. Explicit allow-list, one reason each.
#   OUT_OF_SCOPE  Terrain code the atom register deliberately does not scope. ATOM-COVERAGE.md
#                 opens by saying so: "a **curated core** … deliberately **not exhaustive**".
#                 Explicit allow-list, one reason each.
#
# THE TWO ALLOW-LISTS ARE MATCHED EXACTLY, IN BOTH DIRECTIONS. That is the whole mechanism:
#   * a NEW module nobody documented belongs to no bucket -> `test_every_module_on_disk_is_classified`
#     fails, and the only ways to silence it are to document the module or to write down a reason;
#   * an allow-list entry whose file is gone (renamed, deleted) -> `test_no_module_exemption_is_stale`
#     fails, because a stale exemption re-opens the hole it was written to keep visible;
#   * an allow-listed module that LATER gets documented -> `test_no_exempt_module_is_secretly_documented`
#     fails, because it must move into DOC_NAMED and take the symbol obligation with it.

_MODULE_PATHS = tuple(sorted(REF.glob("*.py"), key=lambda p: p.name))
MODULES_ON_DISK = tuple(p.stem for p in _MODULE_PATHS)

# The listing names of the scope doc — code spans only, same rule as `_section_names`.
COVERAGE_LISTED_NAMES = _idents(_code_spans(COVERAGE))

DOC_NAMED = tuple(m for m in MODULES_ON_DISK if m in COVERAGE_LISTED_NAMES)

# Infrastructure / figure / demo / plumbing. One line each, saying what it is instead of an atom.
HARNESS = {
    "anisotropy_anatomy": "builds the `09` anisotropy ANATOMY figure; a picture, not an operator",
    "capability_grid":    "builds the one-image capability grid; a picture, not an operator",
    "conftest":           "pytest plumbing: puts the package root on sys.path for the test run",
    "crater_anatomy":     "builds the grazing-impact ANATOMY figure; a picture, not an operator",
    "crater_demo":        "`crater_demo.py` impact-matrix demo script (size x angle panels)",
    "empirical_dem":      "VALIDATION rung-5 harness: fetches real DEMs and scores metrics",
    "flow_anatomy":       "builds the `03` flow-routing ANATOMY figure; a picture, not an operator",
    "gallery":            "renders GALLERY.md's panels on one shared base; a picture, not an operator",
    "graph_demo":         "runnable terrain-graph DAG demo (Ctx/Node/Graph wiring the atoms)",
    "halfar_anatomy":     "builds the Halfar SIA-vs-analytic ANATOMY figure; a picture, not an operator",
    "heightfield_io":     "heightmap file I/O and SRTM fetch — transport of a field, not a field op",
    "hero":               "software rasteriser for the 3-D hero view; a picture, not an operator",
    "hex_anatomy":        "builds the `26` hex-grid ANATOMY figure; a picture, not an operator",
    "screen_worlds":      "fictional-planet demo compositions (arrakis, hoth, …) for the gallery",
}

# Terrain code the ATOM register deliberately does not scope — the "curated core" clause.
OUT_OF_SCOPE = {
    "analytic":          "closed-form sims (tephra, HSC seafloor, energy-cone runout) used as ORACLES",
    "archetypes":        "PROVINCE-altitude compositions — macros over macros, above the atom layer",
    "crater":            "parameterised impact sizing/stamping — a landform generator, not an atom",
    "dunes":             "Werner slab CA — an illustrative bedform sim; its constants are pinned by FAITHFUL",
    "hydrology":         "discharge -> water-surface rendering inputs; a presentation layer over `flow`",
    "isostasy":          "flexure/Airy root fields; its constant is pinned by FAITHFUL, not by the atom list",
    "runout":            "Voellmy debris runout — a single-process sim, not a composable atom",
    "scatter":           "object distribution / point placement (07) — a PointSet layer, not a height op",
    "sims_illustrative": "the deliberately un-oracled illustrative regimes (12, 19) behind the figures",
}


@functools.lru_cache(maxsize=None)
def _public_symbols(module):
    """Module-level public `def`/`class` names, read with `ast`.

    PARSED, NOT IMPORTED and NOT REGEXED. Importing would run module-level figure code and would
    also hand back re-exports (`from x import y`) as if the module owned them; a regex over `^def `
    would count a nested `def` inside a function body as public surface. `ast.parse` + a walk of
    `tree.body` only is exactly "what this file declares at module level", which is what "public
    surface" means here. A leading underscore is the Python convention for "not part of the
    surface", so it is the boundary — the same one `_public_callables` above uses at runtime.
    """
    tree = ast.parse((REF / f"{module}.py").read_text(encoding="utf-8"))
    return tuple(n.name for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                 and not n.name.startswith("_"))


# --------------------------------------------------------------------------- #
# PUBLIC SYMBOLS IN A DOCUMENTED MODULE THAT ATOM-COVERAGE.md DOES NOT NAME.
#
# The scope doc's own guarantee is "the reference module's public surface must not contain an atom
# missing from this list". Above, that sentence is enforced for exactly TWO modules
# (`test_noise_surface_has_no_undocumented_atom`, `test_ops_surface_is_fully_accounted_for`). For
# the other 19 documented modules nothing checked it, and the sentence is in fact false for 57
# public symbols across 14 of them. Each of those 58 is written down here with the reason it is not
# an atom — because "58 undocumented public callables" is a fact about this repository that should
# be visible in the guard, not a fact the guard is unable to see.
#
# The list is matched EXACTLY (`test_no_symbol_exemption_is_stale`): delete or rename one of these
# and the row goes red rather than quietly shrinking, which is how a hand-list normally rots.
_MACRO = "landform MACRO over the atoms — the scope doc says the generators live in landforms.py"
_PASS = "diagnostic/visualisation render pass, not one of the colour-production atoms"

SYMBOL_EXEMPT = {
    "analysis": {
        "gradient":           "(dz/dx, dz/dy) primitive the documented channels are computed from",
        "slope":              "steepest-slope primitive consumed by the documented channels",
        "aspect":             "downslope-direction primitive consumed by the documented channels",
        "northness":          "aspect projected on north — a derived scalar view, not a channel",
        "normals":            "unit surface normals for shading; render consumes them",
        "laplacian":          "cheap convexity primitive behind the documented `curvature`",
        "smoothstep":         "Hermite smoothstep — a numeric helper, not a terrain operator",
        "band_select":        "soft band selector — a masking helper, not a terrain operator",
        "derive_materials":   "material-stack macro over the documented channels (06)",
        "dominant_material":  "argmax view of a material stack — categorical, not a channel",
        "derive_substances":  "substance-placement macro over the material stack",
    },
    "braided": {
        "braiding_index":     "measurement OF the solver output (the braiding metric), not a solver",
    },
    "diffusion": {
        "stable_dt":          "CFL timestep helper for `hillslope_diffuse`, not an atom itself",
    },
    "erosion_pipe": {
        "main":               "`python erosion_pipe.py` before/after demo entry point",
    },
    "erosion_streampower": {
        "receivers":          "module-local D8 helper; the documented atom is `flow.d8_receivers`",
        "drainage_area":      "module-local helper; the documented atom is `flow.d8_accumulation`",
        "main":               "`python erosion_streampower.py` D-sweep demo entry point",
    },
    "erosion_thermal": {
        "max_slope":          "diagnostic used to pick a timestep, not a terrain operator",
    },
    # flow: DELIBERATELY EMPTY, and it must stay that way until the doc is fixed. Two public
    # routing atoms — `breach_fill` (Lindsay 2016 least-cost breaching) and `hybrid_accumulation` —
    # appear nowhere in ATOM-COVERAGE.md, and chapter `03` calls the hybrid of the two "the right
    # default for terrain generation" (03-flow-routing.md:101). An exemption reading "a composition
    # of the documented atoms" was drafted here and then withdrawn: it would have been this guard
    # papering over the exact defect it was written to expose, on its first run, with prose. The
    # row below is RED on purpose. The fix is one code span per atom in ATOM-COVERAGE.md's solver
    # paragraph plus the two names in IMPLEMENTED["flow"] — a doc edit, not a test edit.
    "landforms": {
        "crater_diameter":    _MACRO + " (pi-scaling sizing formula feeding `impact_crater`)",
        "impact_crater":      _MACRO,
        "strat_coord":        _MACRO + " (stratigraphic coordinate for the bedding macros)",
        "bed_erodibility":    _MACRO + " (bed-table lookup for the bedding macros)",
        "terrace":            _MACRO,
        "fold":               _MACRO,
        "anticline":          _MACRO,
        "alluvial_fan":       _MACRO + " — guarded as a GENERATOR row above, chapter 16",
        "karst_sinkholes":    _MACRO,
        "main":               "`python landforms.py` generator-gallery entry point",
    },
    "meander": {
        "near_bank_velocity": "the Ikeda-Parker-Sawai kernel INSIDE the documented `migrate`",
        "sinuosity":          "measurement of a centreline, not a solver",
        "sd_polyline":        "polyline SDF helper over the documented `ops_filters.sd_segment`",
        "deposit_point_bars": "F-tier depositional companion to the documented `burn_channel`",
        "seed_wave":          "convenience default centreline for demos",
        "meander_belt":       "composite meander-belt NODE — a macro over `migrate`/`burn_channel`",
    },
    "ops_filters": {
        "box_filter":         "filter/morphology toolbox entry the scope doc excludes by name",
        "median":             "filter/morphology toolbox entry the scope doc excludes by name",
        "tophat":             "filter/morphology toolbox entry the scope doc excludes by name",
        "bothat":             "filter/morphology toolbox entry the scope doc excludes by name",
    },
    "placement": {
        "coords":             "object-space metre grid shared by the documented primitives",
        "coverage":           "signed-distance -> mask conversion shared by the documented primitives",
    },
    "render": {
        "greyscale":          _PASS,
        "hillshade":          _PASS,
        "slope_shade":        _PASS,
        "flow_overlay":       _PASS,
        "hypsometric":        _PASS,
        "false_colour_clip":  _PASS,
        "material_rgb":       _PASS,
        "sun_sky_shade":      _PASS,
        "photoreal":          _PASS,
        "scatter_overlay":    _PASS,
        "write_png":          "minimal stdlib PNG encoder — I/O, not colour production",
    },
    "snow": {
        "wind_redistribute":  "F-tier redistribution companion, not among the listed snow atoms",
        "dry_snow_attribution": "the chapter-`27` audit diagnostic over a snow field, not an operator",
    },
    "winds": {
        "sample_bilinear":    "bilinear sampling helper for the wind field",
        "speed":              "|(u, v)| scalar view of the documented wind field",
        "divergence":         "user-facing diagnostic of the field, not a stage of it",
        "divergence_spectral": "spectral companion diagnostic to `divergence`",
    },
}

# The denominator, asserted in-file so `registers/guard-domains.tsv` cannot go stale silently.
# BEFORE this section: 21 of 44 modules reached = 47.7% (the register says 23 / 52.3% — wrong; the
# reached set is the 18 IMPLEMENTED keys + landforms + dunes + isostasy, and 23 is the count of the
# modules NOT reached).
# AFTER: all 44 are enumerated and classified = 100.0%, of which the 21 the scope doc claims carry
# the symbol-level obligation (47.7% of modules at symbol depth, 0% before).
_TOTAL_MODULES = 44
_DOC_NAMED_COUNT = 21
_SYMBOL_EXEMPT_COUNT = 57


def test_every_module_on_disk_is_classified():
    """No `reference-impl/*.py` may sit outside the guard.

    This is the row the hand-written `IMPLEMENTED` dict could not be: it is keyed on the GLOB, so a
    module that ships tomorrow is in the denominator the moment it lands. Silencing it costs either
    a line in ATOM-COVERAGE.md (join DOC_NAMED) or a line here with a reason (join an allow-list) —
    and there is no third option, which is the point.
    """
    unclassified = sorted(set(MODULES_ON_DISK) - set(DOC_NAMED) - set(HARNESS) - set(OUT_OF_SCOPE))
    assert not unclassified, (
        f"these reference-impl modules are in neither ATOM-COVERAGE.md nor an exemption list: "
        f"{unclassified}. Either name the module in a BACKTICK code span of ATOM-COVERAGE.md (and "
        f"document its public atoms), or add it to HARNESS / OUT_OF_SCOPE here WITH A REASON. A "
        f"module that is in no bucket is a module no test can require to be documented.")


def test_no_module_exemption_is_stale():
    """A stale exemption silently re-opens the hole it was written to keep visible.

    Rename `runout.py` and the entry keeps excusing a file that no longer exists, while the new
    name walks in unclassified. Both halves must be loud, so this checks the allow-list against
    disk (the other half is the row above).
    """
    on_disk = set(MODULES_ON_DISK)
    gone = sorted((set(HARNESS) | set(OUT_OF_SCOPE)) - on_disk)
    assert not gone, (
        f"these modules are exempted here but no longer exist in reference-impl/: {gone}. Drop the "
        f"entry (or fix its spelling) — an exemption for a file that is gone excuses nothing and "
        f"hides the renamed file, which is now unclassified.")

    # Not subject-mutatable (the reasons live in this file, so no edit to a module or to the scope
    # doc can turn it red) — it pins the CONVENTION that an exemption states a reason, so that a
    # future entry cannot be a bare name.
    unreasoned = sorted(name for d in (HARNESS, OUT_OF_SCOPE) for name, why in d.items()
                        if len(why.split()) < 4)
    assert not unreasoned, f"exempted without a written reason: {unreasoned}"


def test_no_exempt_module_is_secretly_documented():
    """A module cannot be both exempted here and claimed by the scope doc.

    If ATOM-COVERAGE.md starts naming `gallery.py` as carrying atoms, the exemption is no longer
    true and, worse, the module would keep its symbol-level obligation waived. Documenting a module
    must MOVE it into DOC_NAMED, taking the obligation with it.
    """
    both = sorted((set(HARNESS) | set(OUT_OF_SCOPE)) & set(DOC_NAMED))
    assert not both, (
        f"ATOM-COVERAGE.md names {both} in a code span, but they are on an exemption list here. "
        f"Delete the exemption so the module joins DOC_NAMED and its public surface is checked — "
        f"or, if the doc mention is incidental, un-backtick it.")


def test_the_denominator_this_guard_claims_is_the_one_on_disk():
    """The coverage number, asserted in-file, so the register cannot drift from the tree.

    `registers/guard-domains.tsv` records this guard's reach as a number a human counted once. A
    number a human counted once is a number that goes stale the next time a module lands. Here it
    is recomputed from the glob and the scope doc every run.
    """
    assert len(MODULES_ON_DISK) == _TOTAL_MODULES, (
        f"reference-impl now ships {len(MODULES_ON_DISK)} modules, not {_TOTAL_MODULES}. Update "
        f"_TOTAL_MODULES and the guard-domains.tsv row together — the register's denominator is "
        f"the thing that just went stale.")
    assert len(DOC_NAMED) == _DOC_NAMED_COUNT, (
        f"ATOM-COVERAGE.md now claims {len(DOC_NAMED)} modules, not {_DOC_NAMED_COUNT} "
        f"({sorted(DOC_NAMED)}) — update _DOC_NAMED_COUNT and the register row together.")
    exempted = sum(len(v) for v in SYMBOL_EXEMPT.values())
    assert exempted == _SYMBOL_EXEMPT_COUNT, (
        f"{exempted} public symbols are excused as non-atoms, not {_SYMBOL_EXEMPT_COUNT}. That "
        f"count is the size of the gap between ATOM-COVERAGE.md's 'the public surface must not "
        f"contain an atom missing from this list' and the tree; it should be going DOWN.")

    # The two figures this guard replaces guard-domains.tsv's 44/23/52.3 with. 44 of 44 modules
    # classified = 100.0% enumerated (was 21 of 44 = 47.7% reached, NOT the 23/52.3 recorded — 23
    # is the size of the complement). Of the 44, the 21 the scope doc claims carry the symbol-level
    # obligation: 47.7% at symbol depth, where it was 2 modules (noise, ops_filters) before.
    classified = set(DOC_NAMED) | set(HARNESS) | set(OUT_OF_SCOPE)
    assert len(classified) == len(MODULES_ON_DISK), (
        f"{len(classified)} modules classified but {len(MODULES_ON_DISK)} on disk — the buckets "
        f"overlap or miss; see the two rows above, which say which.")
    assert round(100.0 * len(DOC_NAMED) / len(MODULES_ON_DISK), 1) == 47.7, (
        f"symbol-depth coverage is now "
        f"{round(100.0 * len(DOC_NAMED) / len(MODULES_ON_DISK), 1)}%, not 47.7% — say so in the "
        f"comment above and in registers/guard-domains.tsv, do not just re-tune the number.")


@pytest.mark.parametrize("module", DOC_NAMED)
def test_documented_module_has_no_undocumented_public_symbol(module):
    """Reverse drift at SYMBOL level, for every module the scope doc claims — not just noise/ops.

    `test_noise_surface_has_no_undocumented_atom` is this row for one module; this is that row for
    all 21, derived. A public callable added to a documented module must be named in an
    ATOM-COVERAGE.md code span, or be written down above with the reason it is not an atom. Adding
    a PRIVATE helper is free — the underscore is how a module says "not surface" — which is what
    keeps this from firing on ordinary refactoring.
    """
    exempt = SYMBOL_EXEMPT.get(module, {})
    undocumented = sorted(n for n in _public_symbols(module)
                          if n not in COVERAGE_LISTED_NAMES and n not in exempt)
    assert not undocumented, (
        f"{module}.py exposes {undocumented} publicly, and ATOM-COVERAGE.md names neither — the "
        f"doc claims 'the reference module's public surface must not contain an atom missing from "
        f"this list'. Either list it in a backtick code span in the doc, make it private (`_name`), "
        f"or add it to SYMBOL_EXEMPT[{module!r}] with the reason it is not an atom.")


def test_no_symbol_exemption_is_stale():
    """Every excused symbol must still be a public symbol of a documented module.

    Same failure mode as the module allow-list, one level down: delete `braided.braiding_index` and
    the entry goes on excusing nothing, so the next public symbol added under that name inherits an
    excuse nobody wrote for it.
    """
    dead = []
    for module, names in SYMBOL_EXEMPT.items():
        if module not in DOC_NAMED:
            dead.append(f"{module} (module is not named in ATOM-COVERAGE.md)")
            continue
        surface = set(_public_symbols(module))
        dead += [f"{module}.{n}" for n in sorted(names) if n not in surface]
    assert not dead, (
        f"these symbol exemptions no longer name a public symbol of a documented module: {dead}. "
        f"Drop the entry — an exemption for a symbol that is gone excuses nothing, and leaves the "
        f"name pre-excused if anything reclaims it.")
