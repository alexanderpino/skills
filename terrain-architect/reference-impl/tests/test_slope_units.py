"""Guard: nothing may apply a trig function to a quantity that is not an ANGLE.

THE DEFECT THIS CLOSES. `06` defines `slope = sqrt(dzdx² + dzdy²)` — the dimensionless gradient
magnitude, already equal to `tan θ` — and the shipped code agrees: `analysis.slope()` returns
`np.hypot(dzdx, dzdy)`, and `erosion_thermal.thermal_erosion` documents `repose_slope = tan(repose
angle)`. Three chapters then fed that ratio straight into a trig function:

    05  wet = min(1, K_w * A_specific / sin(slope))      # sine of a tangent
    05  FS  = (1 - wet * ρw/ρs) * tan(φ) / tan(slope)    # tangent of a tangent
    06  TWI = ln( A_specific / tan(slope) )              # tangent of a tangent
    17  flux = K_soli * frostCycles * soilMoisture * sin(slope)

`tan(slope)` is `tan(tan θ)`, which is not any physical quantity. The cost is measured in `05` and
every number there is recomputed below, in `test_05_*`.

WHY THE DEFAULT IS NOW INVERTED — the third rewrite, and the reason for it
--------------------------------------------------------------------------------
The previous version keyed the whole scan on the SPELLING of the argument: a trig call was a
defect if some identifier inside its argument contained the substring `slope`
(`_is_slope_symbol: "slope" in name.lower()`). That is the same class of hole this guard exists to
close, one level up, and it was measured:

    np.sin(slope)     -> 1 hit          np.tan(dzdx)   -> 0 hits
    np.sin(gradient)  -> 0 hits         np.sin(repose) -> 0 hits

`registers/guard-domains.tsv` records the consequence: the scan opened 151 files and could say
something about 111 of them (73.5%); of the 40 it could not, 12 discuss the very same physical
quantity under another name — gradient, grad, dzdx, tan θ, repose, dip — including `noise.py`,
`placement.py`, `hex_grid.py` and `references/01-noise.md`. And the codebase's own idiom drops the
word entirely: `analysis.py:261` and `:283` both read `s = slope(h, cellsize)`, after which the
tangent is called `s`. A live units bug written as `np.sin(s)` shipped with the suite green.

The guard's own coverage test was no help, because it asserted a FILE COUNT (`len(keys) >= 100`).
A file count is not a denominator: it measures how many files were opened, not how much of the
corpus the key can actually reach. Both numbers can be perfect while the key reaches nothing.

So the default is inverted. The scan no longer looks for a suspicious ARGUMENT NAME; it looks for
a trig CALL, and every one of them in the declared domain is a defect unless the argument is
positively shown to be an angle. There are exactly three ways to show that:

    (i)   the argument is a numeric or degree literal — `tan(35°)`, `tan(45deg)`, `cos(0.5)` — or
          is a multiple of π, which is a phase in radians by construction;
    (ii)  every symbol in it is registered in `ANGLE_REGISTER` for THIS file, with a sentence
          saying what the symbol holds;
    (iii) it passes through an angle-producing call — `atan`/`arctan`/`atan2`/`arctan2` recover the
          angle from a tangent, `radians`/`deg2rad` convert degrees to radians.

Nothing else passes. A spelling cannot save a call and a spelling cannot condemn one; the key is
the call, which is the same in every chapter and every module and does not depend on what anyone
named the variable. That is what lets the scan cover the chapters, which have no AST to consult.

The price is a one-time registration pass over the corpus's angle symbols — θ, φ, ψ, `ang`, `az`,
`azimuth`, `alt`, `rotation`, `phase` and the rest. That price is the design, not a side effect:
registering an angle costs a deliberate sentence, exactly as `PROSE_REGISTRY` below costs one, and
the whole set of claims is auditable in one read. A heuristic never is.

THREE TIERS.

  Tier 1 — CODE, zero tolerance. Fenced blocks in Markdown; executable statements in Python. That
  is the surface a reader implements from and the surface that actually runs. No line-level
  exemption exists for this tier at all — including the one that used to exist by accident, an
  argument longer than `ARG_LIMIT` characters, which was silently dropped and now raises.

  Tier 2 — PROSE, registry only. Markdown outside fences; Python comments and string literals.
  Prose legitimately NAMES the bad form in order to forbid it, so every such occurrence is listed
  in `PROSE_REGISTRY` as (file, exact line substring, one-line reason). A row must match EXACTLY
  ONE offending line in its file: matching "any line" meant a row written for a sentence that
  forbids the bug also pardoned a later sentence that prescribes it.

  Tier 3 — SYMBOLS, registry only, PER FILE. `ANGLE_REGISTER` says what a symbol holds and in
  which files that claim was checked. It is not global: the reasons are file-specific (`maxSlope`
  is an angle in `07-scatter.md`; nothing says anything about a `maxSlope` somewhere else), and a
  global registry would have let one justified row license every other file in the tree.

WHAT IT DELIBERATELY DOES NOT MATCH, and why:
  * `atan`, `arctan`, `atan2`, `arctan2` — recovering the ANGLE from the tangent. That is the
    correct direction and `09` and `render.py` both use it. `asin` of a tangent is precisely the
    bug, so it is forbidden and `atan`/`arctan` are the only survivors.
  * `radians(...)`/`deg2rad(...)` as the argument of a trig call: degrees in, radians out, so the
    result is an angle. The conversion call is itself scanned, so `radians(slope)` still fails —
    converting a ratio "to radians" is the same mistake wearing a different hat.
  * prose that names the bad form WITHOUT parentheses (`tan of slope`) — there is no call to find,
    and inventing a natural-language matcher is how the second version failed.
  * this file. Every forbidden form below is a test fixture; the module is the specification of the
    pattern, so it cannot also be subject to it. `test_only_this_file_is_excluded_from_the_scan`
    pins the exclusion at exactly one path so it cannot grow.

WHAT IT NEWLY DOES MATCH, that the substring key could not:
  * `np.sin(s)`, `np.sin(gradient)`, `np.tan(dzdx)`, `np.sin(repose)` — the same units error with
    the word removed. `test_the_pattern_catches_the_tangent_without_the_word` and
    `test_the_scan_reports_an_injection_into_analysis_wear` pin these.
  * `np.sin(slope + np.arctan(aspect))` — the old `ANGLE_CALL` was searched against the WHOLE
    argument, so one `arctan` anywhere inside pardoned everything beside it.
  * `np.sin(np.degrees(np.arctan(slope)))` — an angle correctly recovered, then converted to
    DEGREES, then fed to a radian sine. `degrees`/`rad2deg` are now degree-producing and are never
    a valid argument to a trig call.

COVERAGE. The scan covers `references/*.md`, the skill root's `SKILL.md` and `index.md`,
`reference-impl/*.md`, `reference-impl/*.py` and `reference-impl/tests/*.py`. What it REACHES
inside that domain — the denominator, not the file count — is asserted in
`test_the_scan_adjudicates_every_trig_call_in_the_domain`.
"""
import re
from pathlib import Path

import pytest

from _textscan import IDENT_UNICODE, complete_match, prose_line_numbers, py_prose_spans

REF = Path(__file__).resolve().parents[1]          # reference-impl/
SKILL = REF.parent                                 # terrain-architect/
CHAPTERS = SKILL / "references"
SELF = Path(__file__).resolve()

# Everything that mentions terrain physics and could be implemented from or executed. `evals/` is
# data and a validator; `*.png` obviously cannot carry the defect.
SCAN_GLOBS = (
    "references/*.md",
    "*.md",                      # SKILL.md, index.md
    "reference-impl/*.md",       # the audit documents
    "reference-impl/*.py",       # the code that actually runs
    "reference-impl/tests/*.py",
)

# ---------------------------------------------------------------------------- #
# the pattern
# ---------------------------------------------------------------------------- #
# Applying any of these to something that is not an angle is a units error. `sec/csc/cot` are here
# for completeness; `radians/degrees/deg2rad/rad2deg` are here because converting a ratio "to
# radians" is the same mistake wearing a different hat. `sinh/cosh/tanh` are here because
# `tanh(slope)` is the same error spelled hyperbolically — and because a `tanh` used as a
# saturating sigmoid has an argument that is a plain dimensionless number, which registers just as
# a symbol does, with a sentence saying so.
TRIG_ON_A_TANGENT = frozenset("""
    sin cos tan sec csc cot
    asin acos arcsin arccos
    sinh cosh tanh asinh acosh atanh arcsinh arccosh arctanh
    radians degrees deg2rad rad2deg
""".split())

# tangent -> angle. The one legitimate direction, and the reason `atan` is not in the set above.
ANGLE_FROM_TANGENT = frozenset(("atan", "arctan", "atan2", "arctan2"))
# degrees -> radians. The result is an angle, so a trig call may consume it.
DEGREES_TO_RADIANS = frozenset(("radians", "deg2rad"))
# radians -> degrees. The result is a NUMBER OF DEGREES, so a trig call may NOT consume it:
# `sin(degrees(x))` is `sin(57.3·x)`, which is the units error one conversion later.
RADIANS_TO_DEGREES = frozenset(("degrees", "rad2deg"))
ANGLE_PRODUCING = ANGLE_FROM_TANGENT | DEGREES_TO_RADIANS

# π is a numeric angle LITERAL, so it is not itself an offender — `np.cos(np.pi / 4)` needs no
# declaration. It is only a literal, though: a π FACTOR does not launder the symbol beside it.
# `np.sin(2 * np.pi * xx / 96.0)` is a phase because `xx` is a cell index, and that is a claim
# about `xx`, made in ANGLE_REGISTER, not something the π can assert on its behalf — otherwise
# `np.sin(2 * np.pi * gradient)` would walk straight through.
PI_NAMES = frozenset(("pi", "tau", "two_pi", "twopi", "TWO_PI", "TAU"))
PI_CHARS = "πτ"

# `np.sin(` and `math.sin(` both yield the head `sin`, because the lookbehind excludes only
# identifier characters and `.` is not one. `arcsin(` yields `arcsin`, not `sin`, because the
# lookbehind stops `sin` matching after `c`.
CALL_HEAD = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# Dotted names, Unicode-aware: the chapters write `θ_separate` and `α_min`, and under an ASCII
# identifier pattern those are not symbols at all — `θ_separate` decomposes into `_separate`.
DOTTED = re.compile(r"[^\W\d][\w]*(?:\s*\.\s*[^\W\d][\w]*)*", re.UNICODE)
NUMBER = re.compile(r"(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+)")
UNIT = re.compile(r"\s*(?:°|deg(?:s|rees?)?|rad(?:ians?)?)(?![^\W\d])", re.UNICODE)

ARG_LIMIT = 4000         # see `_argument`: exceeding this RAISES, it does not skip.
                         # The longest trig argument in the corpus is 86 characters
                         # (`landforms.py:397`), so the limit is a runaway-scan stop, not a
                         # threshold anything real is near.


class Unparseable(AssertionError):
    """A trig call whose argument cannot be delimited. Tier 1 has no line-level exemption, so this
    is raised rather than skipped: a silent skip IS a line-level exemption, and nobody wrote it
    down."""


def _argument(text, open_idx, where=""):
    """The text between `open_idx` (a `(`) and its balancing `)`.

    RAISES rather than returning None. The previous version returned None once the search passed
    `ARG_LIMIT = 400` characters and the caller silently dropped the call — an escape hatch that
    reads "put 400 characters inside the parentheses and the guard stops looking", available on
    every line of a tier whose stated contract is that no line-level exemption exists.
    """
    depth, i, stop = 0, open_idx, min(len(text), open_idx + ARG_LIMIT)
    while i < stop:
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i]
        i += 1
    raise Unparseable(
        "%sa trig call's parentheses do not close within %d characters, so the scan cannot see "
        "what it is applied to:\n    %s...\n"
        "This used to be skipped silently, which made a long argument a working bypass of a "
        "zero-tolerance tier. Either the text is malformed, or ARG_LIMIT is genuinely too small "
        "for this corpus and moving it is a deliberate, reviewable change."
        % (where and where + ": ", ARG_LIMIT, text[open_idx:open_idx + 90].replace("\n", " ")))


def _mentions_slope(name):
    """`06` names the tangent `slope`, so a name built on it inherits that meaning. This is NO
    LONGER THE KEY of the scan — nothing here decides anything. It is used once, by the coverage
    census, to count how many calls are adjudicated WITHOUT the word being present."""
    return "slope" in name.lower()


def _skip_keyword_value(arg, i):
    """From just after a `name=`, the offset of the next top-level `,` or the end.

    A keyword argument is an OPTION, not the quantity: `np.asarray(aspect, dtype=np.float64)` is an
    angle field however it is typed, and `noise.fbm(x, y, seed=seed, octaves=4)` says nothing about
    angles in its keywords.
    """
    depth, n = 0, len(arg)
    while i < n:
        c = arg[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif c == "," and depth == 0:
            break
        i += 1
    return i


def _offenders(arg, key):
    """Everything at the TOP LEVEL of `arg` that is not shown to be an angle.

    Top level only, and that is the point: the old guard searched the WHOLE argument for an
    `arctan`, so `np.sin(slope + np.arctan(aspect))` was pardoned by an `arctan` that applied to a
    different operand entirely. A nested CALL that is angle-producing settles ITS OWN subtree and
    nothing else; a nested call that is not is reported here and scanned in its own right when
    `CALL_HEAD` reaches it. A bare grouping parenthesis is transparent — `tan( (slope) )` is
    `tan(slope)` with extra punctuation, and the old scan missed exactly that spelling.

    Yields (kind, token) with kind in {"symbol", "call", "degrees"}.
    """
    out, i, n = [], 0, len(arg)
    stack, opaque = [], 0            # bracket frames; `opaque` counts CALL/INDEX frames only
    while i < n:
        c = arg[i]
        if c in "([{":
            if c == "(":
                k = i - 1
                while k >= 0 and arg[k] in " \t":
                    k -= 1
                is_call = k >= 0 and (arg[k].isalnum() or arg[k] in "_.)]")
            else:
                is_call = True       # `x[i]`, `{...}`: the contents are not the value
            stack.append(is_call)
            opaque += is_call
            i += 1
            continue
        if c in ")]}":
            if stack:
                opaque -= stack.pop()
            i += 1
            continue
        if opaque > 0:
            i += 1
            continue
        if c in PI_CHARS:
            i += 1
            continue
        m = NUMBER.match(arg, i)
        if m and (i == 0 or not (arg[i - 1].isalnum() or arg[i - 1] in "_.")):
            i = m.end()
            unit = UNIT.match(arg, i)          # `35deg`, `45 degrees`, `0.6 rad`
            if unit:
                i = unit.end()
            continue
        m = DOTTED.match(arg, i)
        if m:
            name = re.sub(r"\s+", "", m.group(0))
            tail = name.split(".")[-1]
            j = m.end()
            while j < n and arg[j] in " \t":
                j += 1
            if j < n and arg[j] == "(":                       # a call
                head = tail.lower()
                if head in RADIANS_TO_DEGREES:
                    out.append(("degrees", name))             # a NUMBER OF DEGREES, never valid
                elif head in ANGLE_PRODUCING:
                    pass                                      # settles its own subtree
                elif head in TRIG_ON_A_TANGENT:
                    pass                                      # judged in its own right, below;
                    # its RESULT is a dimensionless ratio, which is a legal factor of a phase.
                    # Reporting it here too would demand a registry row saying `cos` returns a
                    # cosine, and would hide the inner call's own verdict behind the outer one.
                elif not _registered_symbol(name, key):
                    out.append(("call", name))
                else:
                    # A registered wrapper is declared to PRESERVE units (`np.clip`, `max`,
                    # `np.asarray`), so the claim is about the wrapper, not about what is inside
                    # it. Descend: otherwise `np.sin(np.clip(slope, 0, 1))` would be pardoned by a
                    # row that only ever said clipping does not change units.
                    out.extend(_offenders(_argument(arg, j, where=key or ""), key))
                i = m.end()
                continue
            if j < n and arg[j] == "=" and arg[j:j + 2] != "==":
                i = _skip_keyword_value(arg, j + 1)           # a keyword argument name
                continue
            if tail in PI_NAMES or name in PI_NAMES:
                i = m.end()                                   # π is an angle literal
                continue
            if not _registered_symbol(name, key):
                out.append(("symbol", name))
            i = m.end()
            continue
        i += 1
    return out


def _hits(text, key=None):
    """Every trig-like call that is not shown to apply to an angle.

    Yields (offset, fn, kind, token, argument). `key` is the scanned file's path relative to the
    skill root; `ANGLE_REGISTER` rows are honoured only in the files they name, so a bare string
    (`key=None`) is judged with no registrations at all.
    """
    for m in CALL_HEAD.finditer(text):
        fn = m.group(1)
        if fn.lower() not in TRIG_ON_A_TANGENT:
            continue
        arg = _argument(text, m.end() - 1, where=key or "")
        for kind, token in _offenders(arg, key):
            yield m.start(), fn, kind, token, arg


# ---------------------------------------------------------------------------- #
# tier split: what is code, what is prose
# ---------------------------------------------------------------------------- #
# Both models come from `_textscan`, which exists because this file and `test_atom_coverage.py`
# had privately diverged on the first of them: this file recognised a fence at any indentation and
# that file only in column 0, so a block fenced under a list item was pseudocode to one guard and
# prose to the other. Four chapters in this tree fence exactly that way.


def _scan(path, key=None):
    """(code_offenders, prose_offenders); each a list of (line, text, fn, kind, token).

    `key` overrides the file's identity, which is what lets a fixture copy a shipped module into
    `tmp_path`, mutate it, and still have it judged with that module's own registrations."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    starts = []                                  # offset of each line start
    off = 0
    for line in lines:
        starts.append(off)
        off += len(line) + 1

    key = key or _key(path)
    if path.suffix == ".py":
        spans = py_prose_spans(text, path)

        def is_prose(lineno, col):
            return any(a <= col < b for a, b in spans.get(lineno, ()))
    else:
        prose_lines = prose_line_numbers(text)

        def is_prose(lineno, col):
            return lineno in prose_lines

    code, prose = [], []
    for pos, fn, kind, token, _arg in _hits(text, key):
        lineno = text.count("\n", 0, pos) + 1
        col = pos - starts[lineno - 1]
        row = (lineno, lines[lineno - 1].strip(), fn, kind, token)
        (prose if is_prose(lineno, col) else code).append(row)
    return code, prose


def _scanned_files():
    seen, out = set(), []
    for pattern in SCAN_GLOBS:
        for p in sorted(SKILL.glob(pattern)):
            p = p.resolve()
            if p == SELF or p in seen or not p.is_file():
                continue
            seen.add(p)
            out.append(p)
    return out


def _key(path):
    """The scanned file's identity: its path under the skill root, or its bare name for the
    synthetic documents the fixtures write into `tmp_path`."""
    p = Path(path).resolve()
    try:
        return p.relative_to(SKILL).as_posix()
    except ValueError:
        return p.name


# ---------------------------------------------------------------------------- #
# THE REGISTRIES — the whole escape hatch, in one auditable block
# ---------------------------------------------------------------------------- #
# ⚠️ Adding a row here is a claim, not a suppression. Write the reason. Every row is checked
# against the live text by the staleness tests below, so a row whose line has been fixed or
# deleted FAILS rather than quietly accumulating.
#
# (file, exact substring of the offending line, why that occurrence is correct)
PROSE_REGISTRY = (
    ("references/05-erosion-thermal-aeolian.md",
     "Writing `tan(slope)` computes `tan(tan θ)`, and `sin(slope)` likewise",
     "Names both bad forms in the sentence that forbids them; this is the chapter's units note."),
    ("references/05-erosion-thermal-aeolian.md",
     "`tan(slope)` ✗ | FS error",
     "Header of the measured-cost table; the ✗ columns ARE the defective forms, quantified."),
    ("references/05-erosion-thermal-aeolian.md",
     "`sin(slope) > sin θ`",
     "True statement about magnitudes — sine of the tangent exceeds sine of the angle — and it is "
     "the reason the tan and sin errors oppose instead of compounding. Recomputed in "
     "test_05_the_two_errors_oppose_as_the_chapter_claims."),
    ("references/05-erosion-thermal-aeolian.md",
     "while the `tan(slope)` version fails",
     "Names the defective variant whose threshold shift is being measured; "
     "test_05_the_threshold_band_recomputes checks the angles it quotes."),
    ("references/05-erosion-thermal-aeolian.md",
     "on the nose. The `tan(slope)` version",
     "Names the defective variant in the dry-slope check; its 31.4° is recomputed in "
     "test_05_the_dry_critical_angle_recomputes."),
    ("references/06-analysis-masks.md",
     "**Never write `sin(slope)`, `tan(slope)`, or `cos(slope)`.**",
     "The definition-site prohibition. Deleting it is what "
     "test_06_defines_slope_as_a_tangent_and_says_so exists to catch."),
    ("references/06-analysis-masks.md",
     "`tan(slope)` is `tan(tan θ)`, which is not any quantity.",
     "The one-line explanation of why the forbidden form is meaningless."),
    ("references/06-analysis-masks.md",
     "Writing `ln(A_specific / tan(slope))` computes `tan(tan θ)` and biases TWI low by",
     "Names the wrong TWI form to contrast it with Beven & Kirkby's `ln(a / tan β)`, where β is "
     "an angle. The nats it quotes are recomputed in test_06_the_twi_bias_in_nats_recomputes."),
    ("references/06-analysis-masks.md",
     "`tan(<the symbol slope>)` = bug.",
     "Contrasts the legal threshold form with the illegal one; the word `slope` inside the "
     "placeholder is the point of the sentence."),
    ("references/06-analysis-masks.md",
     "`tan(<a number in degrees>)` = fine;",
     "The legal half of the same contrast. Its argument is an English placeholder, not a symbol, "
     "so there is nothing to declare in ANGLE_REGISTER — the sentence is the declaration."),
    ("references/17-periglacial.md",
     "Writing `sin(slope)` would apply a sine to a quantity that",
     "Solifluction's units note, naming the bad form it forbids."),
    ("references/17-periglacial.md",
     "rather than `sin(slope)`",
     "Offers the exact identity `slope / sqrt(1 + slope²)` as the replacement, naming what it "
     "replaces."),
    ("reference-impl/analysis.py",
     "(the way water leaves)",
     "A docstring sentence in English; `leaves)` is not a call and `water` is not a symbol. The "
     "scan cannot tell an English parenthetical from a call argument, and inventing a "
     "natural-language matcher is how the second version of this guard failed."),
    ("reference-impl/crater.py",
     "in degrees (0 → travelling toward +x = downrange)",
     "An English parenthetical in a docstring describing the azimuth convention; `toward +x` is "
     "prose, not an expression. The quantity it describes IS an angle, in degrees, as it says."),
    ("reference-impl/noise.py",
     "`K·exp(-pi·a^2·r^2)·cos(2pi·F0·(x·cos w + y·sin w))`",
     "The module docstring transcribing the Gabor kernel in plain ASCII: `cos w` and `sin w` are "
     "written WITHOUT parentheses, so there is no call to judge and the identifiers `cos`/`sin` "
     "are read as bare symbols. The formula it states is the one `_gabor` implements, and that "
     "code is adjudicated on its own line."),
    ("references/25-planetary-spherical.md",
     "spreading rate ∝ sin(angular",
     "English inside the parentheses: `sin(angular distance from the pole)` is a sentence about "
     "the Euler-pole law, not an expression. The argument named is an arc angle."),
    ("references/25-planetary-spherical.md",
     "rate ∝ sin(distance)), boundary type from relative velocity",
     "The same Euler-pole law restated in the chapter's summary row; `distance` there is the "
     "angular distance from the pole, i.e. an angle."),
    ("references/99-papers.md",
     "spreading rate ∝ sin(angular distance from it)",
     "The bibliography's one-line statement of the same Euler-pole law, in English."),
    ("references/00-index.md",
     "transform faults on small circles, spreading rate ∝ sin(distance)",
     "The index row for the same law; `distance` is the angular distance from the Euler pole."),
)

# Occurrences that are still WRONG and are not being fixed here, each pinned to its own line. The
# old version of this registry stored a COUNT per chapter, which meant fixing `09:319` and
# introducing a different offender in `09` left both tests green. Rows name the line now.
KNOWN_UNFIXED = (
    ("references/09-verification.md",
     "| Wetness index → Inf | `tan(slope) → 0` on flats |",
     "Genuinely the same units error, in a failure-mode table row. The adjacent remedy is already "
     "phrased correctly ('clamp slope'), so it is a stale formula rather than something a reader "
     "executes. `09` is outside the file ownership of the change that wrote this guard and needs "
     "an owner. Drop this row when it is fixed."),
)

# ---------------------------------------------------------------------------- #
# TIER 3 — what each symbol HOLDS, per file
# ---------------------------------------------------------------------------- #
# (symbol, files where this claim was checked, what the symbol holds and how that is known)
#
# ⚠️ THE SCOPE IS THE CLAIM. This register used to be a global `{name: reason}` whose reasons named
# specific files — `maxSlope` "in 07-scatter.md's placement gate", `shoreSlope` "12-glacial-coastal
# writes ...". A global row backed by a file-specific reason licenses every OTHER file in the tree
# on evidence that was never gathered there: writing `tan(maxSlope)` in `analysis.py`, where no
# `maxSlope` had ever existed, passed. A row is now honoured only in the files it names.
ANGLE_REGISTER = (
    # --- the chapters -------------------------------------------------------- #
    ("θ", ("references/05-erosion-thermal-aeolian.md", "references/06-analysis-masks.md"),
     "`06` defines θ as the slope ANGLE and `slope` as its tangent, in the same three lines. θ is "
     "the angle throughout both chapters; that is the whole distinction this guard enforces."),
    ("φ", ("references/05-erosion-thermal-aeolian.md", "references/12-glacial-coastal.md"),
     "The internal friction angle in the factor-of-safety formula (`05` writes `φ ≈ internal "
     "friction ≈ repose`). `tan(φ)` is the endorsed way to build the threshold `slope` is "
     "compared against. In `12` the same letter is the WAVE PHASE of the second-harmonic shape "
     "`η = a[cos φ + r cos(2φ + ψ)]`; a phase is an angle in radians."),
    ("θ_separate", ("references/05-erosion-thermal-aeolian.md",),
     "The lee-face flow-separation ANGLE (`05` quotes ≈ 10–14°); the pseudocode compares "
     "`slope_w > tan(θ_separate)`, tangent on the left, angle inside the tangent."),
    ("talusAngle", ("references/05-erosion-thermal-aeolian.md",),
     "The angle of repose, named as an angle; `dLimit = tan(talusAngle) * dist` turns it into the "
     "per-neighbour height limit, which is the endorsed direction."),
    ("α", ("references/04-erosion-hydraulic.md", "references/00-index.md",
           "references/09-verification.md", "references/99-papers.md",
           "references/05-erosion-thermal-aeolian.md", "reference-impl/README.md"),
     "`04` writes `α = local tilt angle` on the line itself; everywhere else α is the runout REACH "
     "ANGLE of the Corominas rule `L = H/tan(α)`, an angle by definition of the rule."),
    ("α_min", ("references/04-erosion-hydraulic.md",),
     "The floor applied to that same tilt angle to keep `sin α` off zero on flats — same quantity "
     "as α, same units."),
    ("angle", ("references/06-analysis-masks.md", "references/12-glacial-coastal.md",
               "reference-impl/crater.py", "reference-impl/ops_filters.py",
               "reference-impl/analysis.py", "reference-impl/erosion_thermal.py",
               "reference-impl/tests/test_thermal.py"),
     "Named for what it holds. In `06` it is the slope angle in the comment defining `slope = "
     "tan(angle)`; in `12` it is the wave approach angle of the CERC `sin(2·angle)` law; in "
     "`crater.py` and `ops_filters.py` it is a parameter documented in degrees and radians "
     "respectively; in the last three it is the English word inside `tan(repose angle)` / "
     "`tan(angle)`, prose stating the very distinction this guard enforces."),
    ("elev", ("references/06-analysis-masks.md", "reference-impl/hero.py"),
     "Elevation ANGLE above the horizon — the sky-view integrand in `06`, the camera elevation "
     "converted by `np.radians(elev)` in `hero.py`. Not a height."),
    ("width", ("references/06-analysis-masks.md",),
     "`aspectSel(a, dir, width)`'s half-width is an ANGULAR width in radians: `cos(width)` is "
     "compared against a dot product of unit vectors, which only type-checks as an angle."),
    ("maxSlope", ("references/07-scatter.md",),
     "`07`'s placement gate writes `if s > tan(maxSlope)` with `s = slope(p)`: the tangent is on "
     "the left and `maxSlope` is the angle whose tangent forms the threshold — the endorsed "
     "comparison form from `06`."),
    ("shoreSlope", ("references/12-glacial-coastal.md",),
     "`12` writes `intertidalWidth = tidalRange / tan(shoreSlope)`. That is the run for a given "
     "rise, so `shoreSlope` is the beach ANGLE; substituting a tangent there would give a width "
     "in the wrong units."),
    ("omega0", ("references/01-noise.md",),
     "The Gabor kernel's orientation, in radians: `cos(2π·F0·(x·cos(omega0) + y·sin(omega0)))` "
     "rotates the carrier, which is only meaningful for an angle."),
    ("θ_loc", ("references/12-glacial-coastal.md",),
     "The local wave approach angle relative to the shore normal, in the CERC longshore flux "
     "`Q ∝ sin(2·θ_loc)`; the chapter states `Q = 0 ⟺ θ_loc = 0`, i.e. shore-normal incidence."),
    ("ψ", ("references/12-glacial-coastal.md",),
     "The biphase of the second-harmonic wave shape, `η = a[cos φ + r cos(2φ + ψ)]` — an angle in "
     "radians, and the quantity the skewness/asymmetry pair is a function of."),
    ("psi", ("references/12-glacial-coastal.md", "reference-impl/crater.py",
             "reference-impl/crater_demo.py", "reference-impl/tests/test_crater.py"),
     "The ASCII spelling of the same biphase in `12`'s transcribed formulas; in the crater modules "
     "it is the azimuth of a cell about the impact point, measured from the downrange direction "
     "(`down = 0.5 + 0.5*cos(psi)` is 1 downrange and 0 up-range, which only holds for an angle)."),
    ("I_k", ("references/12-glacial-coastal.md",),
     "The saturating irradiance of the coral growth law `growth ∝ tanh(I(z)/I_k)`. Here `tanh` is "
     "a SIGMOID, not a trig function: its argument is the dimensionless ratio I/I_k, which is "
     "neither an angle nor a tangent."),
    ("z", ("references/12-glacial-coastal.md",),
     "Depth, the argument of the irradiance profile inside that same saturating `tanh(I(z)/I_k)`; "
     "it never reaches the sigmoid except through the dimensionless ratio."),
    ("cell.depth", ("references/12-glacial-coastal.md",),
     "The same depth in the pseudocode's cell form, in the same saturating `tanh(I(...)/I_k)`."),
    ("f", ("references/12-glacial-coastal.md",),
     "The normalised frequency in the rotation table `cos(π f/2)`; the argument is a multiple of "
     "π, i.e. a phase, and `f` runs 0..1 across the table's own columns."),
    ("p", ("references/11-geological.md",),
     "The world-space position fed to `sin(dot(p, foldDir) * foldFreq)`. Position times a spatial "
     "frequency is a PHASE in radians — that product is the angle, and `p` never reaches the sine "
     "on its own."),
    ("dir", ("references/11-geological.md",),
     "The unit direction of the bedding-fold axis in that same phase product."),
    ("foldDir", ("references/11-geological.md",),
     "The same fold axis under its longer name in the bedding-plane listing."),
    ("freq", ("references/11-geological.md", "reference-impl/landforms.py"),
     "The spatial frequency (radians per unit length) that turns a position into a phase; it is "
     "one factor of an angle, never an argument on its own."),
    ("foldFreq", ("references/11-geological.md",),
     "The same spatial frequency under its longer name in the bedding-plane listing."),
    ("phase", ("references/11-geological.md", "reference-impl/capability_grid.py",
               "reference-impl/landforms.py"),
     "A phase offset, in radians, added to a position-times-frequency product. The word states the "
     "quantity: a phase is an angle."),
    ("theta", ("references/11-geological.md", "reference-impl/runout.py",
               "reference-impl/tests/test_dimensional.py", "reference-impl/landforms.py"),
     "The angular coordinate about the cone in `11`; in `runout.py` and the dimensional test the "
     "ramp/bed inclination whose `ρ·g·L·sin(theta)` shear stress is the equation's own definition "
     "of an angle; in `landforms.py` the polar coordinate about the volcano that the barranco "
     "count multiplies."),
    ("fbm", ("references/11-geological.md",),
     "The fractal noise field that perturbs that angular coordinate; it enters only through "
     "`2·pi·fbm`, i.e. as a fraction of a turn."),

    # --- the reference implementation ---------------------------------------- #
    ("phi", ("reference-impl/analysis.py",),
     "`analysis.aspect` returns a direction in RADIANS and `phi` is that direction; "
     "`dr, dc = np.sin(phi), np.cos(phi)` decomposes it into row/column components, which is only "
     "defined for an angle."),
    ("d", ("reference-impl/analysis.py", "reference-impl/tests/test_chapter_numbers.py",
           "reference-impl/tests/test_landforms.py"),
     "A number of DEGREES on its way through `radians`/`deg2rad` in all three: "
     "`np.tan(np.radians(d))` builds a slope threshold from an angle, which is the endorsed "
     "direction, and the two tests sweep the same conversion over a list of degree values."),
    ("aspect_field", ("reference-impl/analysis.py",),
     "The aspect field produced by `analysis.aspect`, documented one line above as being in "
     "radians; `northness` takes its sine to get the north-facing component."),
    ("aspect", ("references/06-analysis-masks.md", "reference-impl/analysis.py",
                "reference-impl/capability_grid.py", "reference-impl/tests/test_analysis.py"),
     "The downslope-facing DIRECTION in radians (`06` and `analysis.aspect` agree). The sign "
     "discussion these lines carry — `-sin(aspect)`, not `+sin(aspect)` — is about which way row 0 "
     "points, and presupposes that the argument is an angle."),
    ("ang", ("reference-impl/anisotropy_anatomy.py", "reference-impl/archetypes.py",
             "reference-impl/capability_grid.py", "reference-impl/crater_anatomy.py",
             "reference-impl/landforms.py", "reference-impl/scatter.py",
             "reference-impl/screen_worlds.py", "reference-impl/tectonics.py"),
     "The repo's short name for an angle in radians. In every one of these files it is consumed as "
     "`(cos(ang), sin(ang))` — a unit vector from an angle — or as a rotation of a sampling "
     "offset, and in `landforms.py` it is assigned from `np.arccos(...)`."),
    ("th", ("reference-impl/anisotropy_anatomy.py", "reference-impl/tests/test_meander.py"),
     "The same angle under a shorter name: assigned from `math.radians(deg)` in "
     "`anisotropy_anatomy.py`, and a `np.linspace` sweep round a circle in `test_meander.py`, "
     "where `(R·cos(th), R·sin(th))` traces the arc."),
    ("a", ("reference-impl/crater.py", "reference-impl/crater_demo.py", "reference-impl/hero.py",
           "reference-impl/landforms.py", "reference-impl/ops_filters.py",
           "reference-impl/tests/test_landforms.py", "reference-impl/tests/test_ops_filters.py",
           "reference-impl/tests/test_winds.py"),
     "A rotation angle in radians, assigned from `np.radians(azimuth)` / `np.deg2rad(...)` or "
     "swept over literal radian values, and consumed as the 2×2 rotation `(cos a, sin a)` in every "
     "one of these files."),
    ("e", ("reference-impl/hero.py",),
     "The camera ELEVATION angle, assigned on the same line as `a` from `np.radians(elev)`; "
     "`(cos e · sin a, sin e, cos e · cos a)` is the standard spherical eye vector."),
    ("az", ("reference-impl/hero.py", "reference-impl/render.py"),
     "The light/camera AZIMUTH in radians, assigned from `np.radians(azimuth)` in both files."),
    ("alt", ("reference-impl/render.py",),
     "The light ALTITUDE angle in radians, assigned from `np.radians(altitude)`; the hillshade "
     "direction `(cos(alt)·sin(az), ...)` is the textbook form."),
    ("azimuth", ("reference-impl/crater.py", "reference-impl/crater_demo.py",
                 "reference-impl/render.py"),
     "The public parameter these modules document as being in DEGREES, converted on the spot by "
     "`np.radians(azimuth)`. Converting degrees to radians is the endorsed direction."),
    ("altitude", ("reference-impl/render.py",),
     "The public light-altitude parameter in DEGREES, converted by `np.radians(altitude)` on the "
     "same line."),
    ("rotation", ("reference-impl/placement.py",),
     "The per-instance placement ROTATION in radians; `c, s = np.cos(-rotation), np.sin(-rotation)` "
     "builds the inverse rotation matrix that maps a footprint into local space."),
    ("j", ("reference-impl/landforms.py",),
     "The lobe-axis angle in radians inside the fan builder — `lu, lv` are the rotated axis "
     "components `(cos j, -sin j)`, not an index, despite the name."),
    ("rn", ("reference-impl/landforms.py",),
     "The vector norm used to normalise a dot product before `np.arccos`; the ratio is a cosine, "
     "and `arccos` is an angle-producing call whose own argument is dimensionless by construction."),
    ("fold_freq", ("reference-impl/landforms.py",),
     "The spatial frequency of the bedding folds, the Python spelling of `11`'s `foldFreq`; it "
     "multiplies a position to make a phase."),
    ("spread_deg", ("reference-impl/landforms.py",),
     "A fan opening angle in DEGREES, converted immediately by `np.radians(spread_deg) / 2.0`."),
    ("om", ("reference-impl/noise.py",),
     "The Gabor carrier orientation in radians — the Python spelling of `01`'s `omega0`, used the "
     "same way: `cos(two_pi·F0·(dx·cos(om) + dy·sin(om)))`."),
    ("fovy_deg", ("reference-impl/hero.py",),
     "The vertical field of view in DEGREES, converted by `np.radians(fovy_deg)` before the "
     "half-angle cotangent that forms the projection matrix."),
    ("ax", ("reference-impl/isostasy.py",),
     "The flexural profile's dimensionless argument `x/α` (α = flexural parameter, a LENGTH), "
     "which is a phase: the analytic plate solution is `e^{-ax}(cos ax + sin ax)`, so `ax` is an "
     "angle in radians by construction of that solution."),
    ("exposure", ("reference-impl/snow.py",),
     "A dimensionless 0..1 wind-exposure fraction. `np.tanh(5.0 * exposure)` is a SATURATING "
     "SIGMOID, not a trig call — there is no angle and no tangent anywhere in it."),
    ("shed_lo_deg", ("reference-impl/snow.py",),
     "The lower snow-shedding threshold in DEGREES, turned into a slope tangent by "
     "`np.tan(np.radians(shed_lo_deg))` and then compared against `slope` — the endorsed "
     "threshold form from `06`, in full."),
    ("shed_hi_deg", ("reference-impl/snow.py",),
     "The upper end of the same shedding band, built the same way and compared the same way."),
    ("snow_repose_deg", ("reference-impl/snow.py",),
     "The snow angle of repose in DEGREES; `np.tan(np.radians(snow_repose_deg))` produces the "
     "`repose_slope` tangent that `thermal_on_layer` documents it wants."),
    ("sd", ("reference-impl/tectonics.py",),
     "The SIGNED DISTANCE to the fault trace, in cells. `np.tanh(sd / width)` is a saturating "
     "sigmoid that feathers the offset across the fault — a smoothstep spelled `tanh`, with no "
     "angle in it."),
    ("width", ("reference-impl/tectonics.py",),
     "The feathering half-width, in cells, in the denominator of that same sigmoid."),
    ("cellsize", ("reference-impl/tectonics.py", "reference-impl/tests/test_winds.py"),
     "The metres-per-cell factor: in `tectonics.py` it puts the feathering width into world units "
     "inside a saturating `tanh`; in the wind test it converts a cell count into the domain "
     "length that divides a position to make a phase."),
    ("repose", ("reference-impl/erosion_thermal.py", "reference-impl/tests/test_thermal.py"),
     "Prose in both places: the docstring and the test comment both write `tan(repose angle)` in "
     "English to say what `repose_slope` IS. The parenthesis is not a call, and the sentence "
     "states exactly the distinction this guard enforces."),
    ("tilt", ("reference-impl/erosion_pipe.py",),
     "The local bed inclination ANGLE in the transport-capacity docstring `C = "
     "capacity·sin(tilt)·|v|`; the pipe model's capacity law is written with the angle, and the "
     "shipped code uses the exact `slope/sqrt(1+slope²)` identity for it."),
    ("alpha", ("reference-impl/runout.py", "reference-impl/tests/test_runout.py",
               "reference-impl/tests/test_dimensional.py"),
     "The Corominas reach ANGLE: the docstrings say `tan(alpha) = mu` and `L = H / tan(alpha)`, "
     "which is the endorsed direction (angle in, tangent out) and the ASCII spelling of α."),
    ("S", ("reference-impl/tests/test_dimensional.py",),
     "The docstring is arguing that `ln(a/tan(S))` is dimensionally illegal — it NAMES the "
     "defective TWI form in order to reject it, which is exactly what the prose tier is for; the "
     "test itself asserts the correct dimensionless form."),

    # --- the test corpus ------------------------------------------------------ #
    ("deg", ("reference-impl/tests/test_anisotropy.py",),
     "A number of DEGREES swept by the test, converted on the next line by `math.radians(deg)`."),
    ("axis_deg", ("reference-impl/tests/test_winds.py",),
     "The wind-axis orientation in DEGREES, converted by `np.deg2rad(axis_deg)`."),
    ("xx", ("reference-impl/tests/test_landforms.py", "reference-impl/tests/test_mask_partition.py",
            "reference-impl/tests/test_render.py", "reference-impl/tests/test_snow.py",
            "reference-impl/landforms.py"),
     "A cell-index grid divided by a period (`xx / 5.0`, `0.1 * xx`, `xx / 9.0`) to make the "
     "phase of a synthetic corrugation, or the noise coordinate that wobbles a barranco count. "
     "The quotient is the angle; `xx` never reaches the sine alone."),
    ("yy", ("reference-impl/tests/test_mask_partition.py", "reference-impl/tests/test_render.py",
            "reference-impl/tests/test_snow.py", "reference-impl/landforms.py"),
     "The other axis of exactly the same constructions."),
    ("seed", ("reference-impl/landforms.py",),
     "The RNG seed handed to `noise.fbm` positionally. It selects which noise field is drawn, not "
     "any quantity in it, and cannot carry units at all."),
    ("k", ("reference-impl/hex_anatomy.py", "reference-impl/tests/test_hex_grid.py",
           "reference-impl/landforms.py"),
     "A COUNT or index. In the hex modules it is the corner index 0..5 reaching the trig only "
     "through `math.radians(30 + 60 * k)` — degrees in, radians out; in `landforms.py` it is the "
     "number of control points in a `np.linspace(0, 3, k) * π` sweep, i.e. the sample count of a "
     "phase, not the phase."),
    ("lu", ("reference-impl/landforms.py",),
     "A component of the rotated lobe-axis UNIT VECTOR; `(dy·lu + dx·lv)/rn` is a normalised dot "
     "product, i.e. a cosine, which is what the surrounding `np.arccos` requires."),
    ("lv", ("reference-impl/landforms.py",),
     "The other component of that same unit axis, in the same normalised dot product."),
    ("out", ("reference-impl/tests/test_mask_partition.py",),
     "An RGB image in 0..255, clipped and divided by 255 to give a 0..1 fraction that is then "
     "multiplied by π — the chroma boost's half-turn phase. A colour channel, never an angle."),
    ("kx", ("reference-impl/tests/test_diffusion.py", "reference-impl/tests/test_isostasy.py"),
     "A WAVENUMBER in radians per cell. `kx * cs` and `kx * x` are wavenumber times length, i.e. a "
     "phase — this is the analytic Fourier mode whose exact decay rate the test checks."),
    ("cs", ("reference-impl/tests/test_diffusion.py",),
     "The cell size that completes that same `kx * cs` phase for the von-Neumann amplification "
     "factor."),
    ("t", ("reference-impl/tests/test_hex_grid.py", "reference-impl/tests/test_meander.py",
           "reference-impl/sims_illustrative.py"),
     "The parameter of a sweep: radians round the unit circle in the hex test (`(cos t, sin t)`), "
     "arclength along a meandering centreline in the next, and TIME in `tide_level`, where "
     "`2π·t/period` is the tidal phase."),
    ("period", ("reference-impl/sims_illustrative.py", "reference-impl/tests/test_meander.py"),
     "The wavelength of a synthetic wave, in cells; the argument is the ratio position/period "
     "times 2π, so the period is a divisor of a phase, never an angle itself."),
    ("n", ("reference-impl/tests/test_heightfield_io.py", "reference-impl/tests/test_winds.py"),
     "A grid SIZE. In the I/O test it is only `np.linspace(0, 6, n)`'s sample count — the 0..6 "
     "radian sweep is the angle; in the wind test it is the domain width that divides a position "
     "to make one full turn across the grid."),
    ("m", ("reference-impl/tests/test_heightfield_io.py", "reference-impl/tests/test_winds.py"),
     "The other grid dimension, used identically in both."),
    ("s", ("reference-impl/tests/test_meander.py",),
     "Arclength along the synthetic centreline, divided by a wavelength to form the phase of the "
     "sine that bends it."),
    ("v", ("reference-impl/tests/test_hex_grid.py",),
     "A unit VECTOR. It reaches `math.acos` only through a normalised dot product, i.e. a cosine, "
     "and `acos` of a cosine is the angle-producing direction."),
    ("w", ("reference-impl/tests/test_hex_grid.py",),
     "The other unit vector of that same normalised dot product."),
    ("c", ("reference-impl/tests/test_hex_grid.py",),
     "The clamped cosine passed to `math.acos` in the neighbour-angle check — a cosine, not an "
     "angle, which is what `acos` requires."),

    ("F0", ("references/01-noise.md", "reference-impl/noise.py"),
     "The Gabor carrier's spatial FREQUENCY. It reaches the cosine only as `2π·F0·(projected "
     "distance)` — frequency times length times 2π is a phase in radians, which is what the "
     "carrier's argument has to be."),
    ("cols", ("reference-impl/archetypes.py",),
     "A column-index grid divided by a period (`2π·cols/5.0`) to form the phase of the synthetic "
     "ripple stamped across the archetype; the quotient is the angle, the index is not."),
    ("xs", ("reference-impl/capability_grid.py", "reference-impl/meander.py"),
     "The sample positions along the channel/panel axis, divided by a wavelength and multiplied "
     "by 2π to make a phase. Positions, not angles, and they never reach a sine alone."),
    ("ox", ("reference-impl/meander.py",),
     "The phase origin subtracted from those positions before the division — an offset in the "
     "same units as `xs`."),
    ("lam", ("reference-impl/meander.py",),
     "The meander WAVELENGTH that divides that offset position; a length in the denominator of a "
     "phase, never an argument on its own."),
    ("fold_dir", ("reference-impl/landforms.py",),
     "The unit direction of the bedding folds, the Python spelling of `11`'s `foldDir`; "
     "`(fold_dir·p) * fold_freq` is the phase."),
    ("direction", ("reference-impl/landforms.py",),
     "The same fold/wave direction under its long name in the ridge builder's signature."),
    ("n_barrancos", ("references/11-geological.md", "reference-impl/landforms.py"),
     "The integer COUNT of radial gullies in `cos(n_barrancos·theta + 2π·fbm)`; it multiplies the "
     "angular coordinate θ, so the product is an angle and the count itself is not one."),
    ("x", ("reference-impl/tests/inputs.py", "reference-impl/tests/test_crossvalidate_landlab.py",
           "reference-impl/tests/test_isostasy.py", "reference-impl/tests/test_meander.py",
           "reference-impl/tests/test_winds.py", "references/01-noise.md",
           "reference-impl/landforms.py"),
     "A POSITION, never an angle. In the fixtures it is a `np.linspace` over a range measured in "
     "radians, or a position divided by a wavelength and multiplied by 2π; in the Gabor kernel "
     "and the fold generator it is a world coordinate projected onto a direction and multiplied "
     "by a spatial frequency. The product is the phase; `x` never reaches a sine alone."),
    ("y", ("reference-impl/tests/test_winds.py", "references/01-noise.md",
           "reference-impl/landforms.py"),
     "The other axis of exactly the same construction."),
    ("dx", ("reference-impl/noise.py", "reference-impl/landforms.py"),
     "An x OFFSET: from the Gabor kernel's centre in `noise.py`, projected onto the carrier "
     "direction by `dx·cos(om)` and turned into a phase by the `2π·F0` in front; from the fan "
     "apex in `landforms.py`, inside the normalised dot product `np.arccos` consumes."),
    ("dy", ("reference-impl/noise.py", "reference-impl/landforms.py"),
     "The y offset in exactly the same two constructions."),
    ("waveAngle", ("references/12-glacial-coastal.md",),
     "The deep-water wave approach ANGLE in the CERC longshore-drift pseudocode; the chapter says "
     "the flux peaks near 45° of it, which only parses as an angle."),
    ("shorelineNormal", ("references/12-glacial-coastal.md",),
     "The shore-normal bearing subtracted from it in the same expression, so the difference is "
     "the relative approach angle."),

    # --- opaque calls: what the wrapper returns ------------------------------- #
    ("np.asarray", ("reference-impl/analysis.py", "reference-impl/landforms.py",
                    "reference-impl/sims_illustrative.py"),
     "A pure type coercion: `np.asarray(X, dtype=...)` returns X unchanged, so the units of the "
     "argument are the units of the result. In every one of these the argument is registered "
     "above (`aspect_field`, `phase`) or is a π multiple."),
    ("np.clip", ("reference-impl/landforms.py", "reference-impl/tests/test_mask_partition.py"),
     "Clipping preserves units. In `landforms.py` the clip feeds `np.arccos`, which requires a "
     "cosine in [-1, 1] and produces the angle; in the mask test it bounds a π-multiple phase."),
    ("np.linspace", ("reference-impl/landforms.py",
                     "reference-impl/tests/test_heightfield_io.py"),
     "A ramp between two endpoints, so the endpoints carry the units: every one of these sweeps "
     "between literal radian bounds (`0` to `6`, `0` to `2π`)."),
    ("max", ("references/04-erosion-hydraulic.md", "reference-impl/tectonics.py",
             "reference-impl/tests/test_hex_grid.py"),
     "A floor, which cannot change units: `sin(max(α, α_min))` is the sine of an angle because "
     "both operands are angles, and the others floor a distance or a cosine that is registered "
     "above."),
    ("min", ("reference-impl/tests/test_hex_grid.py",),
     "A ceiling on the cosine handed to `math.acos`, clamping floating-point overshoot past 1.0 "
     "before the angle is recovered."),
    ("dot", ("references/11-geological.md",),
     "The pseudocode's dot product of a position with a unit fold direction — a projected LENGTH, "
     "which becomes a phase when multiplied by `foldFreq` on the same line."),
    ("I", ("references/12-glacial-coastal.md",),
     "The irradiance profile of the coral growth law; it enters only the saturating "
     "`tanh(I(z)/I_k)` sigmoid, as the numerator of a dimensionless ratio."),
    ("noise.fbm", ("reference-impl/landforms.py",),
     "Fractal noise in [-1, 1], used as a fraction of a turn: it is multiplied into an angular "
     "coordinate to wobble it, exactly as `11`'s `cos(n_barrancos·theta + 2·pi·fbm)` does."),
    ("np.linalg.norm", ("reference-impl/tests/test_hex_grid.py",),
     "A vector LENGTH, in the denominator that normalises the dot product `v @ w` into a cosine "
     "before `math.acos` recovers the angle from it."),
)


def _angle_index():
    """{(file_key, symbol): reason} — the register flattened to the pairs it actually licenses."""
    index = {}
    for symbol, files, reason in ANGLE_REGISTER:
        for f in files:
            index[(f, symbol)] = reason
    return index


ANGLE_INDEX = _angle_index()


def _registered_symbol(name, key):
    """Is `name` declared to hold an angle IN THIS FILE? A bare string (key None) has no file, so
    no registration applies to it — which is what makes the fixtures below meaningful."""
    if key is None:
        return False
    return (key, name) in ANGLE_INDEX or (key, name.split(".")[-1]) in ANGLE_INDEX


def _prose_offender_lines(key, path=None):
    """The DISTINCT prose-tier offender LINES of `key`, as [(lineno, text)], or None if the file
    is gone. Distinct lines, not distinct offenders: one sentence naming three bad forms is one
    line to pardon, and counting it three times would make every pardon look ambiguous."""
    path = Path(path) if path is not None else SKILL / key
    if not path.exists():
        return None
    _, prose = _scan(path)
    seen, out = set(), []
    for n, t, _fn, _kind, _tok in prose:
        if n not in seen:
            seen.add(n)
            out.append((n, t))
    return out


def _registry_matches(key, substring, path=None):
    """Every prose offender line in `key` that a registry row's substring matches."""
    lines = _prose_offender_lines(key, path)
    if lines is None:
        return None
    return [(n, t) for n, t in lines if substring in t]


def _registered(key, line_text, path=None):
    """Is this prose line pardoned? A row pardons a line only when the row is UNAMBIGUOUS — it
    matches exactly one offending line in the file. A row that matches two has stopped being a
    statement about a particular sentence."""
    for f, substring, _reason in PROSE_REGISTRY + KNOWN_UNFIXED:
        if f == key and substring in line_text and \
                len(_registry_matches(key, substring, path) or ()) == 1:
            return True
    return False


FIX_ADVICE = (
    "  `slope` is the DIMENSIONLESS gradient |grad h| = tan(theta), not an angle (06).\n"
    "  Use `slope` directly where the textbook form wants `tan theta`;\n"
    "  use `slope / sqrt(1 + slope**2)` where it wants `sin theta`;\n"
    "  use `atan(slope)` to recover the angle itself.\n"
    "  If the argument really IS an angle, say so: add a row to ANGLE_REGISTER naming this file.\n")


def _report(key, rows):
    return "".join("  %s:%d: %s(...) — %s %r is not shown to be an angle\n     %s\n"
                   % (key, n, fn, kind, tok, t) for n, t, fn, kind, tok in rows)


# ---------------------------------------------------------------------------- #
# TIER 1 — code, zero tolerance
# ---------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _scanned_files(), ids=_key)
def test_no_code_applies_trig_to_a_non_angle(path):
    """Fenced blocks and executable Python. There is no per-line registry for this tier: a reader
    implements from these and the interpreter runs them. The only escape is to declare what the
    SYMBOL holds, in ANGLE_REGISTER, for this file."""
    found, _ = _scan(path)
    assert not found, (
        "%s applies a trig function to something not shown to be an angle, in code:\n%s%s"
        % (_key(path), _report(_key(path), found), FIX_ADVICE))


# ---------------------------------------------------------------------------- #
# TIER 2 — prose, registry only
# ---------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _scanned_files(), ids=_key)
def test_every_prose_occurrence_is_registered(path):
    """Prose may NAME the bad form in order to forbid it — but each such line must be registered
    with a reason. No keyword makes a line legal."""
    _, found = _scan(path)
    key = _key(path)
    unregistered = [r for r in found if not _registered(key, r[1])]
    assert not unregistered, (
        "%s applies a trig function to a non-angle in prose, and the line is not in "
        "PROSE_REGISTRY:\n%s"
        "Either FIX it:\n%s"
        "or REGISTER it, by adding a row to PROSE_REGISTRY in %s:\n"
        "    (%r,\n"
        "     %r,\n"
        "     \"<one line saying why this occurrence is correct>\"),\n"
        % (key, _report(key, unregistered), FIX_ADVICE, SELF.name, key, unregistered[0][1][:80]))


# ---------------------------------------------------------------------------- #
# the registries police themselves
# ---------------------------------------------------------------------------- #
@pytest.mark.parametrize("key,substring,reason", PROSE_REGISTRY,
                         ids=["%s::%s" % (k.rsplit("/", 1)[-1], s[:28]) for k, s, _ in PROSE_REGISTRY])
def test_the_prose_registry_is_not_stale(key, substring, reason):
    """A registered exemption whose line no longer exists — fixed, reworded, or deleted — must
    FAIL, so the registry liquidates itself instead of accumulating dead pardons.

    EXACTLY ONE match, not "at least one". A row matched against ANY line meant the pardon written
    for a sentence that FORBIDS the bug also covered a sentence added later that PRESCRIBES it:
    delete the original line, add `Use `sin(slope)` here instead of the raw gradient.` containing
    the same fragment, and the suite stayed green. The line number is reported as advisory context
    rather than asserted, because a hard line-number assert breaks on every edit above it."""
    matches = _registry_matches(key, substring)
    assert matches is not None, "PROSE_REGISTRY names %s, which no longer exists" % key
    assert len(matches) == 1, (
        "PROSE_REGISTRY row for %s matches %d offending lines, and a pardon must name ONE.\n"
        "  substring: %r\n  matched: %s\n"
        "If it matches 0, the line was fixed or reworded — delete this row. If it matches 2+, one "
        "of them is being pardoned by a reason written for the other; lengthen the substring until "
        "it identifies a single line.\nReason on file: %s"
        % (key, len(matches),
           substring, ", ".join("line %d: %r" % (n, t[:60]) for n, t in matches), reason))


@pytest.mark.parametrize("key,substring,reason", KNOWN_UNFIXED,
                         ids=["%s::%s" % (k.rsplit("/", 1)[-1], s[:28]) for k, s, _ in KNOWN_UNFIXED])
def test_the_known_unfixed_registry_is_not_stale(key, substring, reason):
    """The tolerated-defect list names LINES, not counts. Fixing the line fails this test, which
    is the signal to drop the row — and, unlike a count, fixing one offender while introducing a
    different one in the same chapter no longer cancels out."""
    matches = _registry_matches(key, substring)
    assert matches is not None, "KNOWN_UNFIXED names %s, which no longer exists" % key
    assert len(matches) == 1, (
        "KNOWN_UNFIXED row for %s matches %d offending lines, not 1. If 0, it looks FIXED — "
        "delete the row. If 2+, the row is pardoning a second occurrence it was not written "
        "for.\n  substring: %r\nReason on file: %s" % (key, len(matches), substring, reason))


@pytest.mark.parametrize("symbol,files,reason", ANGLE_REGISTER,
                         ids=["%s@%s" % (s, len(f)) for s, f, _ in ANGLE_REGISTER])
def test_every_angle_registration_is_load_bearing(symbol, files, reason):
    """A declaration that no longer pardons anything is a standing invitation to name a tangent
    after it. Each (symbol, file) pair is checked by REMOVING it and requiring the file to fail:
    that is the only definition of "still needed" that cannot drift."""
    for f in files:
        path = SKILL / f
        assert path.exists(), (
            "ANGLE_REGISTER declares %r for %s, which does not exist. Delete the file from the "
            "row.\nReason on file: %s" % (symbol, f, reason))
        try:
            ANGLE_INDEX.pop((f, symbol))
            without = list(_hits(path.read_text(encoding="utf-8"), f))
        finally:
            ANGLE_INDEX[(f, symbol)] = reason
        assert any(tok == symbol or tok.split(".")[-1] == symbol for _p, _fn, _k, tok, _a in without), (
            "ANGLE_REGISTER declares %r for %s, but removing that declaration changes nothing "
            "there: the symbol no longer reaches any trig call in that file. Delete %s from the "
            "row.\nReason on file: %s" % (symbol, f, f, reason))


def test_the_angle_register_cannot_relabel_the_slope_tangent():
    """`06` names the tangent `slope`. Declaring `slope` — or anything built on it as a prefix —
    to be an angle would turn Tier 3 into the blanket bypass it replaced."""
    bad = [n for n, _f, _r in ANGLE_REGISTER if n.lower().startswith("slope")]
    assert not bad, (
        "ANGLE_REGISTER may not contain %s: a name beginning with `slope` inherits 06's "
        "definition of `slope` as the tangent. Rename the symbol for the angle it holds "
        "(e.g. `reposeAngle`) instead of declaring the tangent to be an angle." % bad)


def test_a_slope_named_registration_is_confined_to_one_file():
    """`maxSlope` and `shoreSlope` are angles in exactly one chapter each, on evidence gathered
    there. A `*Slope` row that named several files would be the old global registry back again."""
    wide = [(n, f) for n, f, _r in ANGLE_REGISTER if "slope" in n.lower() and len(f) != 1]
    assert not wide, (
        "a registration for a `*slope*` symbol must name exactly one file — the one whose text "
        "justifies it: %s" % wide)


def test_every_registry_entry_carries_a_reason():
    """The registry costs a sentence of thought, and that is the entire point of it over a
    keyword list. An empty or token reason defeats it."""
    thin = []
    for key, substring, reason in PROSE_REGISTRY + KNOWN_UNFIXED:
        if len(reason.strip()) < 40:
            thin.append("%s :: %r" % (key, substring))
    for symbol, files, reason in ANGLE_REGISTER:
        if len(reason.strip()) < 40:
            thin.append("ANGLE_REGISTER[%r]" % symbol)
    assert not thin, (
        "these registry rows have no real reason written on them, so nobody can audit them: %s"
        % thin)


def test_the_registries_have_no_duplicate_rows():
    """Two rows exempting the same line means one of them is already dead weight."""
    rows = [(k, s) for k, s, _ in PROSE_REGISTRY + KNOWN_UNFIXED]
    dupes = sorted({r for r in rows if rows.count(r) > 1})
    assert not dupes, "duplicated registry rows: %s" % dupes
    pairs = [(s, f) for s, files, _ in ANGLE_REGISTER for f in files]
    dupes = sorted({p for p in pairs if pairs.count(p) > 1})
    assert not dupes, "duplicated (symbol, file) angle registrations: %s" % dupes


# ---------------------------------------------------------------------------- #
# COVERAGE — the denominator, asserted in-file
# ---------------------------------------------------------------------------- #
# ⚠️ This is criterion J for this guard, and it replaces `len(keys) >= 100`. A file COUNT says how
# many files were opened. It is not a denominator: the previous key reached 111 of 151 files while
# opening all 151, because 40 of them never spell the word it was keyed on. What follows counts
# REACH — how many of the trig calls in the declared domain the scan actually adjudicates, and how
# many of those it adjudicates on evidence other than the spelling of the argument.
def _census():
    """(files, files_with_calls, calls, adjudicated, wordless) over the declared domain.

    `wordless` counts adjudicated calls whose whole argument contains no identifier spelling
    `slope` — the calls the previous key could say nothing at all about.
    """
    files = _scanned_files()
    with_calls = calls = adjudicated = wordless = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        here = 0
        for m in CALL_HEAD.finditer(text):
            if m.group(1).lower() not in TRIG_ON_A_TANGENT:
                continue
            calls += 1
            here += 1
            arg = _argument(text, m.end() - 1, where=_key(path))   # raises rather than skipping
            adjudicated += 1
            if not any(_mentions_slope(s) for s in IDENT_UNICODE.findall(arg)):
                wordless += 1
        if here:
            with_calls += 1
    return len(files), with_calls, calls, adjudicated, wordless


def test_the_scan_adjudicates_every_trig_call_in_the_domain():
    """DECLARED SCAN DOMAIN: SCAN_GLOBS, minus this file.
    POPULATION:  every trig-family call in that domain.
    MATCHED:     every one of them reaches a verdict — angle, or defect.
    FLOOR:       the identity below, plus a floor on the calls decided WITHOUT the word `slope`.

    The identity is what a file count could never assert. Before this rewrite the scan skipped any
    call whose parentheses ran past 400 characters and any call whose argument merely failed to
    spell `slope` — 111 of 151 files, and every trig call in `noise.py`, `placement.py`,
    `hex_grid.py` and `references/01-noise.md`. Those skips were invisible because nothing counted
    them.
    """
    files, with_calls, calls, adjudicated, wordless = _census()

    assert adjudicated == calls, (
        "%d of %d trig calls in the domain were skipped rather than judged. A skipped call is a "
        "line-level exemption nobody wrote down." % (calls - adjudicated, calls))
    assert files >= 145, (
        "the declared domain has shrunk to %d files; it held 151 when this was written, so a glob "
        "has been lost" % files)
    assert calls >= 340, (
        "only %d trig calls are visible in the domain (340+ when written) — either a glob or the "
        "call pattern has narrowed" % calls)
    assert with_calls >= 60, (
        "only %d files carry a trig call the scan can see; 66 did when this was written" % with_calls)

    # THE REACH FLOOR. This is the number the old key could not produce at all, and the number
    # that collapses the moment anyone re-keys the scan on an identifier spelling.
    assert wordless >= 300, (
        "only %d of %d adjudicated calls (%.1f%%) were decided WITHOUT the word `slope` appearing "
        "in the argument. 327 of 347 (94.2%%) were when this was written, against the previous "
        "key's 0. A drop means the scan "
        "has gone back to keying on a spelling, which is the exact defect this rewrite closed: "
        "`np.sin(gradient)`, `np.tan(dzdx)` and `np.sin(s)` are then invisible again."
        % (wordless, adjudicated, 100.0 * wordless / max(adjudicated, 1)))


def test_the_scan_reaches_the_files_that_carry_the_quantity_under_another_name():
    """`registers/guard-domains.tsv` names the files that discuss the slope tangent as gradient,
    grad, dzdx, tan θ or repose and therefore fell outside the old substring key. Each must now
    have its trig calls adjudicated — not merely be opened."""
    keys = {_key(p) for p in _scanned_files()}
    must_cover = {
        "reference-impl/analysis.py",          # slope() and twi() themselves
        "reference-impl/erosion_thermal.py",   # repose_slope = tan(repose angle)
        "reference-impl/render.py",            # atan(slope) shading
        "reference-impl/archetypes.py",        # np.degrees(np.arctan(slope percentile))
        "SKILL.md",
        "index.md",
        "references/05-erosion-thermal-aeolian.md",
        "references/06-analysis-masks.md",
        "references/09-verification.md",
        "references/17-periglacial.md",
        "reference-impl/SIMULATION-AUDIT.md",
    }
    assert must_cover <= keys, "the scan no longer reaches %s" % sorted(must_cover - keys)

    # The 12 the register calls unreachable-by-spelling. These carry trig calls and no `slope`.
    wordless_files = {
        "references/01-noise.md",
        "reference-impl/noise.py",
        "reference-impl/placement.py",
        "reference-impl/tectonics.py",
        "reference-impl/isostasy.py",
        "reference-impl/crater.py",
        "reference-impl/anisotropy_anatomy.py",
        "reference-impl/tests/test_hex_grid.py",
        "reference-impl/tests/test_meander.py",
    }
    assert wordless_files <= keys, "the scan no longer reaches %s" % sorted(wordless_files - keys)
    for k in sorted(wordless_files):
        text = (SKILL / k).read_text(encoding="utf-8")
        assert "slope" not in text.lower(), (
            "%s now spells `slope`, so it no longer demonstrates reach beyond the spelling; pick "
            "another file for this assertion" % k)
        seen = [m for m in CALL_HEAD.finditer(text) if m.group(1).lower() in TRIG_ON_A_TANGENT]
        assert seen, (
            "%s no longer contains a trig call, so it cannot demonstrate that the scan reaches "
            "past the word `slope`" % k)
        for m in seen:
            _argument(text, m.end() - 1, where=k)      # adjudicated, not skipped


def test_only_this_file_is_excluded_from_the_scan():
    """Self-exclusion is necessary — every forbidden form in this module is a fixture — but it is
    also the one hole in the coverage, so it is pinned at exactly one path."""
    everything = set()
    for pattern in SCAN_GLOBS:
        everything |= {p.resolve() for p in SKILL.glob(pattern) if p.is_file()}
    excluded = everything - set(_scanned_files())
    assert excluded == {SELF}, (
        "the scan skips more than this file: %s" % sorted(_key(p) for p in excluded))
    assert all(any(p.match(g) for g in ("*.md", "*.py")) for p in _scanned_files())


# ---------------------------------------------------------------------------- #
# the pattern, proved on both sides
# ---------------------------------------------------------------------------- #
# 33 realistic ways the units error comes back — every one of them spelling the word `slope`,
# which is exactly why they all passed while the defect below shipped. See
# REINTRODUCTIONS_WITHOUT_THE_WORD.
REINTRODUCTIONS = (
    "sin(slope)", "cos(slope)", "tan(slope)",
    "np.sin(slope)", "np.cos(slope)", "np.tan(slope)",
    "math.sin(slope)", "sin(slope_tan)", "tan(slope_w)",
    "asin(slope)", "acos(slope)",
    "arcsin(slope)", "arccos(slope)", "np.arcsin(slope)", "np.arccos(slope)",
    "sinh(slope)", "cosh(slope)", "tanh(slope)", "np.tanh(slope)",
    "radians(slope)", "degrees(slope)", "np.radians(slope)", "np.degrees(slope)",
    "deg2rad(slope)", "rad2deg(slope)",
    "sin(2*slope)", "sin(0.5 * slope)", "tan(slope * 2)",
    "tan(-slope)", "tan( (slope) )", "sin( slope )",
    "SIN(SLOPE)", "sin(localSlope)",
)

# ⚠️ THE FIXTURES THAT DID NOT EXIST. Every row above varies the CALL while holding the argument
# name constant, so the whole set is satisfied by a scan keyed on the argument's spelling — which
# is what the previous scan was, and why a rewrite explicitly about non-vacuity still shipped the
# hole. Each row below holds the same tangent under a name the word `slope` never appears in. They
# are drawn from how this codebase actually writes it: `analysis.py:261` and `:283` are
# `s = slope(h, cellsize)`, `06` defines `slope = sqrt(dzdx² + dzdy²)`, and
# `erosion_thermal.thermal_erosion` documents `repose_slope = tan(repose angle)`.
REINTRODUCTIONS_WITHOUT_THE_WORD = (
    "np.sin(s)",                       # the repo's own idiom after `s = slope(h, cellsize)`
    "np.sin(gradient)", "np.tan(gradient)", "np.cos(grad)",
    "np.tan(dzdx)", "np.sin(dzdy)", "np.tan(dz_dx)",
    "np.sin(repose)", "np.tan(repose_ratio)",
    "np.sin(riseOverRun)", "tan(rise_over_run)",
    "np.sin(g)", "np.tan(steepness)", "sin(dip)",
    "np.degrees(steepness)", "np.radians(gradmag)",
    "sinh(dzdx)", "np.tanh(dz)",
    "np.sin(2 * gradient)", "np.tan(-dzdx)", "sin( steepness )",
    "np.sin(np.hypot(dzdx, dzdy))",    # the definition of the tangent, inlined
    "np.sin(2 * np.pi * gradient)",    # a phase factor does not launder a ratio... see below
)


@pytest.mark.parametrize("form", REINTRODUCTIONS)
def test_the_pattern_catches_every_known_reintroduction(form):
    """A guard nobody has seen fail is a guard nobody should trust. Whitespace, sign, arithmetic on
    the argument, module prefix, case and the inverse/hyperbolic/conversion families are all ways
    the same units error comes back."""
    assert list(_hits("    x = %s   # units error" % form)), (
        "the scan misses %r, so that spelling of the defect ships silently" % form)


@pytest.mark.parametrize("form", REINTRODUCTIONS_WITHOUT_THE_WORD)
def test_the_pattern_catches_the_tangent_without_the_word(form):
    """The set the old key was blind to. Measured on the previous scan: `np.sin(slope)` -> 1 hit,
    `np.sin(gradient)` -> 0, `np.tan(dzdx)` -> 0, `np.sin(repose)` -> 0."""
    assert list(_hits("    x = %s   # units error" % form)), (
        "the scan misses %r — the same units error with the word `slope` removed, which is how it "
        "actually ships" % form)


def test_pi_is_a_literal_and_not_a_laundering_factor():
    """π is a numeric angle literal, so `cos(np.pi / 4)` needs no declaration. It stops there: a π
    FACTOR says nothing about the symbol beside it, and if it did, `np.sin(2 * np.pi * gradient)`
    — the same units error with a phase factor bolted on — would walk straight through."""
    assert not list(_hits("half = np.cos(np.pi / 4)")), "π alone is a literal angle"
    assert not list(_hits("quarter = np.sin(2 * np.pi / 8.0)")), "so is any arithmetic on π alone"
    for form in ("np.sin(2 * np.pi * slope)", "np.sin(2 * np.pi * slope_w / L)",
                 "np.sin(2 * np.pi * gradient)", "np.sin(np.pi * dzdx)"):
        assert list(_hits("x = " + form)), (
            "a π factor must not launder %r; the symbol still has to be declared" % form)
    key = "99-synthetic.md"
    ANGLE_INDEX[(key, "xx")] = "fixture"
    try:
        assert not list(_hits("wave = np.sin(2 * np.pi * xx / 96.0)", key)), (
            "once `xx` is declared, the corrugation is a phase and must pass")
    finally:
        ANGLE_INDEX.pop((key, "xx"))


def test_only_the_innermost_group_containing_the_symbol_is_credited():
    """The old `ANGLE_CALL` was searched against the WHOLE argument, so any `arctan` anywhere
    inside pardoned every other operand beside it, and a degrees conversion outside it pardoned
    everything."""
    assert list(_hits("shade = np.sin(slope + np.arctan(aspect))")), (
        "an `arctan` applied to a DIFFERENT operand must not pardon the bare tangent next to it")
    assert list(_hits("bug = np.sin(np.degrees(np.arctan(slope)))")), (
        "`degrees(...)` yields a number of degrees; feeding it to a radian sine is the units "
        "error one conversion later")
    assert not list(_hits("theta = np.degrees(np.arctan(slope))")), (
        "recovering the angle and printing it in degrees is the correct, shipped form")


def test_an_unclosed_trig_call_raises_instead_of_being_skipped():
    """`ARG_LIMIT` used to make a long argument a silent bypass of a tier whose contract is that
    no line-level exemption exists."""
    with pytest.raises(Unparseable):
        list(_hits("x = np.sin(slope" + " " * (ARG_LIMIT + 10)))
    with pytest.raises(Unparseable):
        list(_hits("x = np.sin(" + "a + " * 1200 + "slope)"))


LEGITIMATE = (
    "Plot the distribution of `atan(slope)` in degrees.",
    "| **Slope shade** | `atan(slope)` on a ramp | Steepness directly",
    "        return np.arctan(slope)",
    "p99 = np.degrees(np.arctan(np.percentile(slope, 99)))",
    "theta_deg = math.degrees(math.atan(slope))",
    "rockMask = smoothstep(tan(35deg), tan(45deg), slope)   # steep = exposed rock",
    "slopeSel(s, lo, hi, w) = smoothstep(lo-w, lo+w, s)     # s = tan, not degrees",
    "    sin_theta = slope / sqrt(1 + slope**2)             # exact, stays in the tangent",
    "screeSource = cliffMask * weatheringRate   # cliffMask = slope > ~55deg",
    "    thresh = np.tan(np.radians(35.0))                  # threshold from an angle literal",
    "    lo, hi = np.tan(np.radians(30)), np.tan(np.radians(45))",
)


@pytest.mark.parametrize("line", LEGITIMATE)
def test_the_pattern_does_not_flag_the_legitimate_forms(line):
    """The other half. A guard that cries wolf gets deleted — and the first one did cry wolf, on
    `05`'s correct `sin(slope) > sin θ` sentence. Every line here is legitimate WITHOUT any
    registration: literal angles, π multiples, and the tangent->angle direction."""
    assert not list(_hits(line)), "the scan flags a CORRECT form: %r" % line


# The forms that are correct only BECAUSE a symbol was declared. Under the inverted default these
# fail on their own — that is the whole point — and pass once the file that carries them says what
# the symbol holds. Both directions are asserted, so neither the flagging nor the registry can
# quietly stop working.
NEEDS_A_REGISTRATION = (
    ("    FS  = (1 - wet * rw/rs) * tan(phi) / slope     # factor of safety", "phi"),
    ("    a   = g*sin(theta) - mu*g*cos(theta)           # Voellmy: theta IS an angle", "theta"),
    ("  at `slope = tan(phi)` -- the critical angle is `phi` on the nose.", "phi"),
    ("    thresh = np.tan(np.radians(repose_deg))        # threshold from an angle", "repose_deg"),
    ("        if slope_w > tan(theta_separate): deposit UPWIND", "theta_separate"),
    ("    if s > tan(maxSlope): reject                   # 07, maxSlope is an angle", "maxSlope"),
    ("    intertidalWidth = tidalRange / tan(shoreSlope) # 12, shoreSlope is an angle", "shoreSlope"),
    ("    ripple = np.sin(2 * np.pi * cols / 5.0)         # a synthetic corrugation", "cols"),
    ("    half = np.cos(np.pi * f / 2)                    # a rotation weight", "f"),
)


@pytest.mark.parametrize("line,symbol", NEEDS_A_REGISTRATION,
                         ids=[s for _l, s in NEEDS_A_REGISTRATION])
def test_an_angle_named_symbol_is_flagged_until_it_is_registered(line, symbol):
    """`tan(phi)` is correct arithmetic and the scan cannot know that from the name — `phi` is a
    friction angle here and could be a porosity somewhere else. Under the inverted default it
    costs one sentence to say which, and until that sentence exists the call is a defect."""
    assert list(_hits(line)), (
        "%r must be flagged until %r is declared an angle: nothing about the name proves it"
        % (line, symbol))
    key = "99-synthetic.md"
    ANGLE_INDEX[(key, symbol)] = "fixture"
    try:
        assert not list(_hits(line, key)), (
            "declaring %r an angle in this file must clear the line; it did not" % symbol)
    finally:
        ANGLE_INDEX.pop((key, symbol))


def test_a_registration_is_not_honoured_in_a_file_that_did_not_justify_it():
    """The register used to be global while its reasons were file-specific, so `maxSlope`'s
    justification — one gate in `07-scatter.md` — licensed `tan(maxSlope)` in every module in the
    tree, including files where no such symbol had ever existed."""
    line = "    if s > tan(maxSlope): reject"
    assert not list(_hits(line, "references/07-scatter.md")), (
        "07-scatter.md is the file whose text justifies the maxSlope row")
    assert list(_hits(line, "reference-impl/analysis.py")), (
        "a registration justified in 07-scatter.md must NOT license the same symbol in "
        "analysis.py, where nothing was ever checked about it")
    assert list(_hits(line, "references/12-glacial-coastal.md")), (
        "nor in the other chapter that happens to carry a different *Slope angle")


def test_asin_is_forbidden_even_though_atan_is_allowed():
    """`atan(tan θ)` recovers θ; `asin(tan θ)` is the defect itself, and is undefined above 45°."""
    assert list(_hits("theta = asin(slope)")), "`asin(slope)` is the bug, not an exemption"
    assert list(_hits("theta = np.arcsin(slope)")), "`np.arcsin(slope)` is the bug"
    assert not list(_hits("theta = atan(slope)")), "`atan(slope)` is the correct inverse"
    assert not list(_hits("theta = np.arctan(slope)")), "`np.arctan(slope)` is the correct inverse"


# The eight lines a critic used to walk the old keyword hatch. Each contains a word from the
# fourteen NEGATION_CUES purely by accident of English, and each PRESCRIBES or ASSERTS the defect.
KEYWORD_BYPASSES = (
    "The formula `FS = tan(phi)/tan(slope)` computes the driving-to-resisting ratio directly.",
    "This cannot be simplified further: `TWI = ln(A / tan(slope))`.",
    "After unit conversion, use `FS = tan(phi)/tan(slope)` for the factor of safety.",
    "Use `sin(slope)` here instead of the raw gradient.",
    "The wetness term `wet = K_w * A / sin(slope)` would be evaluated once per cell.",
    "Never clamp the area before evaluating `TWI = ln(A / tan(slope))`.",
    "Compute the factor of safety as `FS = tan(phi)/tan(slope)` rather than by iteration.",
    "The saturation term `sin(slope)` biases the wetness index upward on steep ground.",
)


@pytest.mark.parametrize("line", KEYWORD_BYPASSES)
def test_the_keyword_bypasses_are_caught(line, tmp_path):
    """All eight escaped the cue list. Under the registry they are simply unregistered prose, so
    all eight fail — and registering one would require writing a reason that is not true."""
    doc = tmp_path / "99-synthetic.md"
    doc.write_text("Intro.\n" + line + "\n", encoding="utf-8")
    code, prose = _scan(doc)
    assert not code
    assert prose, "the bypass line still escapes the scan: %r" % line
    assert not _registered(_key(doc), prose[0][1]), "a synthetic bypass line must not be registered"


def test_a_prose_registration_pardons_one_line_and_not_a_second(tmp_path):
    """THE HIJACK. `_registered` used to match its substring against ANY line in the file, so a
    pardon written for a sentence that forbids the bug also covered a sentence added later that
    PRESCRIBES it — the file stayed green with the prescription in it."""
    doc = tmp_path / "99-synthetic.md"
    doc.write_text("Never write `sin(slope)`; it applies a sine to a ratio.\n", encoding="utf-8")
    assert len(_registry_matches(_key(doc), "write `sin(slope)`", doc) or ()) == 1

    doc.write_text("Never write `sin(slope)`; it applies a sine to a ratio.\n"
                   "Always write `sin(slope)` here, it is what the paper does.\n", encoding="utf-8")
    matches = _registry_matches(_key(doc), "write `sin(slope)`", doc)
    assert len(matches) == 2, (
        "both lines contain the registered fragment; the staleness test must see 2 and fail, "
        "instead of pardoning the second on the first one's reason. Got %s" % (matches,))
    _, prose = _scan(doc)
    key = _key(doc)
    assert not any(_registered(key, t, doc) for _n, t, _f, _k, _s in prose), (
        "an ambiguous registry row must pardon NEITHER line")


# ---------------------------------------------------------------------------- #
# the tier split, exercised
# ---------------------------------------------------------------------------- #
def test_the_markdown_tiers_separate_fenced_code_from_prose(tmp_path):
    doc = tmp_path / "99-synthetic.md"
    doc.write_text(
        "Intro paragraph.\n"                                          # 1
        "```\n"                                                       # 2
        "FS = tan(phi) / tan(slope)\n"                                # 3: fenced offender
        "```\n"                                                       # 4
        "Never write `sin(slope)`; it applies a sine to a ratio.\n"    # 5: prose, unregistered
        "| Wetness index | `tan(slope)` on flats | clamp |\n"          # 6: prose, unregistered
        "Use `atan(slope)` to recover the angle.\n"                    # 7: legitimate
        "A threshold is `slope > tan(35deg)`.\n",                      # 8: legitimate
        encoding="utf-8")
    code, prose = _scan(doc)
    assert sorted({n for n, *_ in code}) == [3], code
    assert sorted({n for n, *_ in prose}) == [5, 6], (
        "line 5 carried a negation cue and used to be exempt; under the registry it is prose like "
        "any other and must be listed, got %s" % prose)


def test_an_indented_fence_is_code_not_prose(tmp_path):
    """The divergence `_textscan` exists to end. This file recognised a fence at any indentation;
    `test_atom_coverage.py` recognised one only in column 0. Four chapters in this tree fence
    under a list item — `03:693`, `12:293`, `13:461`, `26:345` — and under the column-0 model
    their contents are prose, i.e. registrable, i.e. exempt from the zero-tolerance tier."""
    doc = tmp_path / "99-synthetic.md"
    doc.write_text(
        "- A list item:\n"                                            # 1
        "  ```\n"                                                     # 2
        "  FS = tan(phi) / tan(slope)\n"                              # 3: fenced offender
        "  ```\n"                                                     # 4
        "Trailing prose.\n",                                          # 5
        encoding="utf-8")
    code, prose = _scan(doc)
    assert sorted({n for n, *_ in code}) == [3], (
        "an indented fence must put its contents in the zero-tolerance CODE tier, got code=%s "
        "prose=%s" % (code, prose))
    assert not prose


def test_a_tilde_fence_is_code_not_prose(tmp_path):
    doc = tmp_path / "99-synthetic.md"
    doc.write_text("~~~python\nFS = tan(phi) / tan(slope)\n~~~\n", encoding="utf-8")
    code, prose = _scan(doc)
    assert sorted({n for n, *_ in code}) == [2], (code, prose)
    assert not prose


def test_the_python_tiers_separate_statements_from_comments_and_docstrings(tmp_path):
    mod = tmp_path / "synthetic_module.py"
    mod.write_text(
        '"""Module docstring: never write tan(slope), it is a units error."""\n'   # 1: prose
        "import numpy as np\n"                                                     # 2
        "\n"                                                                       # 3
        "def twi(area, slope_tan, cellsize=1.0):\n"                                # 4
        '    """ln(A / slope). Writing np.sin(slope_tan) here would be wrong."""\n' # 5: prose
        "    _bug = np.sin(slope_tan)          # the critic's injection\n"          # 6: CODE
        "    theta = np.arctan(slope_tan)      # legitimate\n"                      # 7: clean
        "    deg = np.degrees(np.arctan(slope_tan))   # legitimate\n"               # 8: clean
        "    return np.log(area / slope_tan) + _bug * 0 + theta * 0 + deg * 0\n",   # 9: clean
        encoding="utf-8")
    code, prose = _scan(mod)
    assert sorted({n for n, *_ in code}) == [6], (
        "the executable injection `np.sin(slope_tan)` must land in the zero-tolerance tier, got %s"
        % code)
    assert sorted({n for n, *_ in prose}) == [1, 5], (
        "a docstring naming the bad form is PROSE and must be registrable, got %s" % prose)


def test_a_module_that_does_not_tokenise_raises_rather_than_failing_open(tmp_path):
    """Both fail-open fallbacks — raw source, or no spans — silently move every match in the file
    between the two tiers."""
    mod = tmp_path / "broken_module.py"
    mod.write_text("def f(:\n    return np.sin(slope)\n", encoding="utf-8")
    with pytest.raises(AssertionError):
        _scan(mod)


# ---------------------------------------------------------------------------- #
# END TO END — the injection the old guard shipped green
# ---------------------------------------------------------------------------- #
def test_the_scan_reports_an_injection_into_analysis_wear(tmp_path):
    """The proof that the inversion is real, on the real module. `analysis.wear` computes a slope
    and then calls it `s` — `s = slope(h, cellsize)` — which is where the previous key went blind.
    Copy the shipped file, write the units bug into it in the codebase's own idiom, and require
    the scan to report it; then restore the copy and require silence."""
    src = (REF / "analysis.py").read_text(encoding="utf-8")
    assert "s = slope(h, cellsize)" in src, (
        "analysis.py no longer names the tangent `s`; this fixture is pinned to the idiom that "
        "made the old key blind, so pick the current one")

    key = "reference-impl/analysis.py"
    clean = tmp_path / "analysis.py"
    clean.write_text(src, encoding="utf-8")
    code, _ = _scan(clean, key)
    assert not code, "the unmodified module must be clean under the scan, got %s" % code

    injected = src.replace("    s = slope(h, cellsize)",
                           "    s = slope(h, cellsize)\n    out = conv * np.sin(s)", 1)
    assert injected != src
    (tmp_path / "analysis.py").write_text(injected, encoding="utf-8")
    code, _ = _scan(tmp_path / "analysis.py", key)
    assert any(tok == "s" and fn == "sin" for _n, _t, fn, _k, tok in code), (
        "`out = conv*np.sin(s)` written into analysis.wear must be reported. This is the exact "
        "injection that shipped with 1370 tests green. Got %s" % code)


def test_the_decoys_beside_that_injection_are_not_reported(tmp_path):
    """A guard that only ever fires is as broken as one that never does. The same neighbourhood,
    with the needle present but NOT as a defect: in a comment, in a docstring, and as the correct
    `atan` direction."""
    src = (REF / "analysis.py").read_text(encoding="utf-8")
    for decoy in (
            "    s = slope(h, cellsize)\n    # note: np.sin(s) here would be a units error",
            '    s = slope(h, cellsize)\n    """np.sin(s) is what we must never write."""',
            "    s = slope(h, cellsize)\n    theta = np.arctan(s)",
            "    s = slope(h, cellsize)\n    sin_theta = s / np.sqrt(1.0 + s * s)",
    ):
        mod = tmp_path / "analysis.py"
        mod.write_text(src.replace("    s = slope(h, cellsize)", decoy, 1), encoding="utf-8")
        code, _ = _scan(mod, "reference-impl/analysis.py")
        assert not code, "a decoy must not be reported as a code defect: %r -> %s" % (decoy, code)


# ---------------------------------------------------------------------------- #
# the chapters and the shipped code still agree
# ---------------------------------------------------------------------------- #
def test_06_defines_slope_as_a_tangent_and_says_so():
    """The fix is only durable if the DEFINITION site warns the next reader."""
    text = (CHAPTERS / "06-analysis-masks.md").read_text(encoding="utf-8")
    assert complete_match(text, "Never write `sin(slope)`"), (
        "06 has lost the explicit note saying what `slope` is and is not. That note is what stops "
        "the units error being reintroduced at a new call site.")
    assert complete_match(text, "sqrt(1 + slope²)"), (
        "06 has lost the exact tangent->sine identity, which is the escape hatch a reader needs "
        "when a textbook formula genuinely wants sin(theta).")


def test_the_shipped_slope_is_the_gradient_magnitude():
    """Everything above rests on `analysis.slope` being a tangent. Execute the claim."""
    import numpy as np

    import analysis

    for deg in (10.0, 25.0, 35.0, 45.0, 60.0):
        h = np.tile(np.arange(8, dtype=float) * np.tan(np.radians(deg)), (8, 1))
        assert analysis.slope(h, cellsize=1.0)[3, 3] == pytest.approx(np.tan(np.radians(deg))), (
            "analysis.slope no longer returns tan(theta) at %g deg" % deg)


def test_the_chapter_twi_formula_matches_the_shipped_twi():
    """`06`'s TWI formula disagreed with `analysis.twi` (and with its own pseudocode). Pin them."""
    import numpy as np

    import analysis

    text = (CHAPTERS / "06-analysis-masks.md").read_text(encoding="utf-8")
    assert re.search(r"TWI = ln\(\s*A_specific\s*/\s*slope\s*\)", text), (
        "06's TWI formula is no longer `ln(A_specific / slope)`. `analysis.twi` divides by the "
        "slope tangent directly.")
    for deg in (25.0, 35.0, 45.0):
        s = np.tan(np.radians(deg))
        got = analysis.twi(np.array([100.0]), np.array([s]), cellsize=1.0)[0]
        assert got == pytest.approx(np.log(100.0 / s)), (
            "analysis.twi no longer computes ln(A_specific / slope) at %g deg" % deg)


# ---------------------------------------------------------------------------- #
# F2 — every number `05` quotes, parsed out of the chapter and recomputed
# ---------------------------------------------------------------------------- #
# The chapter states its own assumptions, so all of it is reproducible. Nothing below is a
# hardcoded expectation: the values are READ from the chapter and checked against arithmetic, the
# way test_the_chapter_twi_formula_matches_the_shipped_twi reads the TWI formula.
CH05 = CHAPTERS / "05-erosion-thermal-aeolian.md"
CH06 = CHAPTERS / "06-analysis-masks.md"
MINUS = "\u2212"                     # the chapter uses U+2212 MINUS SIGN, not hyphen-minus
NUM = r"([0-9]+(?:\.[0-9]+)?)"
RHO_WATER = 1000.0                   # kg/m3, the ρw implied by `ρw/ρs` with ρs in kg/m3


def _c05():
    return CH05.read_text(encoding="utf-8")


def _find(pattern, text, what):
    m = re.search(pattern, text)
    assert m, ("05 no longer states %s — the pattern %r finds nothing, so the number that "
               "depends on it can no longer be checked." % (what, pattern))
    return m


def _rounds_to(computed, quoted_text, what):
    """`computed` must round to the number the chapter prints, at the chapter's own precision."""
    quoted = float(quoted_text)
    decimals = len(quoted_text.split(".")[1]) if "." in quoted_text else 0
    tol = 0.5 * 10.0 ** -decimals + 1e-9
    assert abs(computed - quoted) <= tol, (
        "05 prints %s for %s; recomputing from the chapter's own stated assumptions gives %.6f. "
        "The prose and the arithmetic must agree — fix whichever is wrong." %
        (quoted_text, what, computed))


def _assumptions():
    """K_w·A_specific, ρw/ρs, the held-fixed wetness, and φ — all read from `05`."""
    t = _c05()
    kw = float(_find(r"`K_w·A_specific = " + NUM + "`", t, "K_w·A_specific").group(1))
    rw_rs = float(_find(r"`ρw/ρs = " + NUM + "`", t, "ρw/ρs").group(1))
    wet = float(_find(r"`wet = " + NUM + r"` held fixed", t, "the held-fixed wetness").group(1))
    phi = float(_find(r"`φ = " + NUM + "°`", t, "the friction angle φ").group(1))
    return kw, rw_rs, wet, phi


TABLE_ROW = re.compile(
    r"^\| " + NUM + r"° \| " + NUM + r" \| " + NUM + r" \| \*\*" + MINUS + NUM + r"%\*\* \| "
    + NUM + r" \| " + NUM + r" \| " + MINUS + NUM + r"% \|$", re.M)


def _table():
    rows = TABLE_ROW.findall(_c05())
    assert len(rows) == 3, (
        "05's measured-cost table no longer parses as three rows of "
        "`| θ° | tan θ | tan(slope) | **−FS%%** | sin θ | sin(slope) | −wet%% |`; got %d. "
        "The table is the chapter's evidence and must stay machine-checkable." % len(rows))
    return rows


@pytest.mark.parametrize("i", (0, 1, 2))
def test_05_the_measured_table_recomputes(i):
    """Every cell of the cost table, from the angle in its own first column."""
    import numpy as np

    deg, tan_q, tantan_q, fs_err_q, sin_q, sinatan_q, wet_err_q = _table()[i]
    theta = np.radians(float(deg))
    s = np.tan(theta)

    _rounds_to(s, tan_q, "tan %s deg" % deg)
    _rounds_to(np.tan(s), tantan_q, "tan(slope) at %s deg" % deg)
    _rounds_to(np.sin(theta), sin_q, "sin %s deg" % deg)
    _rounds_to(np.sin(s), sinatan_q, "sin(slope) at %s deg" % deg)
    # FS is proportional to 1/denominator, so the error is slope/tan(slope) - 1.
    _rounds_to(-(s / np.tan(s) - 1.0) * 100.0, fs_err_q, "the FS error at %s deg" % deg)
    # wet is proportional to 1/sin, so the error is sin(theta)/sin(slope) - 1.
    _rounds_to(-(np.sin(theta) / np.sin(s) - 1.0) * 100.0, wet_err_q,
               "the wetness error at %s deg" % deg)


def test_05_the_tan_only_percentages_equal_the_tables_fs_column():
    """The 'wetness held fixed' bullet claims to be *exactly* the table column. Check that it is,
    rather than trusting two independently typed triples."""
    m = _find(r"column above — \*\*" + MINUS + NUM + r"% / " + MINUS + NUM + r"% / " + MINUS
              + NUM + r"%\*\*\. No free parameter", _c05(), "the wetness-held-fixed percentages")
    quoted = list(m.groups())
    from_table = [row[3] for row in _table()]
    assert quoted == from_table, (
        "05 says the held-fixed FS error is *exactly* the table's FS column, but the bullet says "
        "%s and the table says %s." % (quoted, from_table))


def test_05_the_compounded_percentages_recompute():
    """The other branch: `wet` recomputed from the broken slope too, so the errors partially
    cancel. This is the pair the chapter says is a free parameter — and it states the pair, so it
    is checkable."""
    import numpy as np

    kw, rw_rs, _wet, phi_deg = _assumptions()
    m = _find(r"\*\*smaller\*\* — \*\*" + MINUS + NUM + r"% / " + MINUS + NUM + r"% / " + MINUS
              + NUM + r"%\*\* at", _c05(), "the compounded percentages")
    tan_phi = np.tan(np.radians(phi_deg))
    for quoted, (deg, *_rest) in zip(m.groups(), _table()):
        s = np.tan(np.radians(float(deg)))
        sin_theta = s / np.sqrt(1.0 + s * s)              # the chapter's exact identity
        wet_ok = min(1.0, kw / sin_theta)
        wet_bad = min(1.0, kw / np.sin(s))                # sin OF the tangent
        fs_ok = (1.0 - wet_ok * rw_rs) * tan_phi / s
        fs_bad = (1.0 - wet_bad * rw_rs) * tan_phi / np.tan(s)
        _rounds_to(-(fs_bad / fs_ok - 1.0) * 100.0, quoted,
                   "the compounded FS error at %s deg" % deg)


def test_05_the_two_errors_oppose_as_the_chapter_claims():
    """The registered sentence `sin(slope) > sin θ` is the reason the errors oppose. Execute it:
    the sine error must push FS UP while the tangent error pushes it DOWN, so the compounded
    figure is strictly smaller in magnitude than the tan-only one."""
    import numpy as np

    kw, rw_rs, _wet, phi_deg = _assumptions()
    tan_phi = np.tan(np.radians(phi_deg))
    for deg in (25.0, 35.0, 45.0):
        s = np.tan(np.radians(deg))
        sin_theta = s / np.sqrt(1.0 + s * s)
        assert np.sin(s) > sin_theta, (
            "05 states `sin(slope) > sin θ`; at %g deg sin(slope)=%.4f and sin θ=%.4f"
            % (deg, np.sin(s), sin_theta))
        tan_only = (np.tan(np.radians(phi_deg)) / np.tan(s)) / (tan_phi / s) - 1.0
        wet_ok, wet_bad = min(1.0, kw / sin_theta), min(1.0, kw / np.sin(s))
        compounded = (((1 - wet_bad * rw_rs) * tan_phi / np.tan(s))
                      / ((1 - wet_ok * rw_rs) * tan_phi / s)) - 1.0
        assert tan_only < compounded < 0.0, (
            "05 claims the two errors OPPOSE, so the compounded error must be smaller in "
            "magnitude than the tan-only error; at %g deg tan-only=%.4f compounded=%.4f"
            % (deg, tan_only, compounded))


def _band(rw_rs, wet, phi_deg):
    """(correct threshold angle, broken threshold angle, band width) in degrees."""
    import numpy as np

    k = (1.0 - wet * rw_rs) * np.tan(np.radians(phi_deg))   # FS = 1  =>  denominator = k
    correct = np.degrees(np.arctan(k))                      # slope       = k
    broken = np.degrees(np.arctan(np.arctan(k)))            # tan(slope)  = k
    return correct, broken, correct - broken


def test_05_the_threshold_band_recomputes():
    """The three band angles, and the assumptions the chapter says they depend on."""
    kw, rw_rs, wet, phi_deg = _assumptions()
    t = _c05()
    correct_q = _find(r"the correct mask fails above \*\*" + NUM + r"°\*\*", t,
                      "the correct threshold").group(1)
    broken_q = _find(r"above \*\*" + NUM + r"°\*\* — a \*\*" + NUM + r"°\*\*-wide band", t,
                     "the broken threshold and band width")
    correct, broken, band = _band(rw_rs, wet, phi_deg)
    _rounds_to(correct, correct_q, "the correct failure threshold")
    _rounds_to(broken, broken_q.group(1), "the `tan(slope)` failure threshold")
    _rounds_to(band, broken_q.group(2), "the width of the mispainted band")
    assert band > 0, "the broken threshold must sit BELOW the correct one (the mask over-predicts)"


def test_05_the_density_variant_recomputes():
    """The chapter states the band is sensitive to ρw/ρs and gives a second density to prove it.
    That second pair must recompute from the ρs it names."""
    t = _c05()
    rho_s = float(_find(r"`ρs = " + NUM + r" kg/m³`", t, "the alternative solid density").group(1))
    m = _find(r"moves to " + NUM + r"° and the band widens to " + NUM + r"°", t,
              "the density-variant threshold and band")
    _kw, _rw_rs, wet, phi_deg = _assumptions()
    correct, _broken, band = _band(RHO_WATER / rho_s, wet, phi_deg)
    _rounds_to(correct, m.group(1), "the failure threshold at rho_s = %g" % rho_s)
    _rounds_to(band, m.group(2), "the band width at rho_s = %g" % rho_s)


def test_05_the_dry_critical_angle_recomputes():
    """The identity that makes the units error self-evident: dry and cohesionless,
    `FS = tan(φ)/slope` crosses 1 at `slope = tan(φ)`, so the critical angle IS φ. The broken form
    crosses somewhere else, and `05` says where."""
    import numpy as np

    t = _c05()
    m = _find(r"crosses at " + NUM + r"° for `φ = " + NUM + r"°`, missing by " + NUM + "°", t,
              "the broken critical angle")
    broken_q, phi_q, miss_q = m.groups()
    phi_deg = float(phi_q)

    def critical_angle(denominator):
        lo, hi = 0.5, 89.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if np.tan(np.radians(phi_deg)) / denominator(np.tan(np.radians(mid))) > 1.0:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    correct = critical_angle(lambda s: s)
    assert correct == pytest.approx(phi_deg, abs=1e-6), (
        "the corrected form must put the dry critical angle exactly at the friction angle %g; "
        "got %.4f" % (phi_deg, correct))
    broken = critical_angle(np.tan)
    _rounds_to(broken, broken_q, "the `tan(slope)` critical angle")
    _rounds_to(correct - broken, miss_q, "the miss on the dry critical angle")


def test_06_the_twi_bias_in_nats_recomputes():
    """`06` quotes what `tan(slope)` costs TWI in nats. TWI is `ln(a/s)`, so the bias is just
    `ln(tan(slope)) - ln(slope)` and does not depend on `a` — check that, at the angles `06`
    names, rather than trusting three typed numbers."""
    import numpy as np

    t = CH06.read_text(encoding="utf-8")
    m = _find(r"biases TWI low by " + NUM + r" /\s*" + NUM + r" / " + NUM
              + r" nats at " + NUM + r"° / " + NUM + r"° / " + NUM + "°", t,
              "the TWI bias in nats")
    nats, degs = list(m.groups()[:3]), list(m.groups()[3:])
    for nat_q, deg_q in zip(nats, degs):
        s = np.tan(np.radians(float(deg_q)))
        _rounds_to(np.log(np.tan(s)) - np.log(s), nat_q, "the TWI bias at %s deg" % deg_q)


def test_06_echoes_the_same_numbers_as_05():
    """`06`'s definition-site note quotes `05`'s measured cost. Two independently typed copies of
    the same numbers drift; pin them to each other."""
    t = CH06.read_text(encoding="utf-8")
    m = _find(r"understated the factor of safety by \*\*" + NUM + r"% / " + NUM + r"% / " + NUM
              + r"% at " + NUM + r"° / " + NUM + r"° / " + NUM + r"°\*\*", t,
              "06's echo of 05's FS-error triple")
    fs_q, deg_q = list(m.groups()[:3]), list(m.groups()[3:])
    rows = _table()
    assert deg_q == [r[0] for r in rows], (
        "06 quotes the cost at %s deg but 05's table measures it at %s deg"
        % (deg_q, [r[0] for r in rows]))
    assert fs_q == [r[3] for r in rows], (
        "06 says the FS error is %s but 05's table says %s" % (fs_q, [r[3] for r in rows]))
    miss_q = _find(r"off the friction angle by " + NUM + "°", t, "06's echo of the angle miss")
    m05 = _find(r"missing by " + NUM + "°", _c05(), "05's angle miss")
    assert miss_q.group(1) == m05.group(1), (
        "06 says the dry critical angle is off by %s deg, 05 says %s"
        % (miss_q.group(1), m05.group(1)))
