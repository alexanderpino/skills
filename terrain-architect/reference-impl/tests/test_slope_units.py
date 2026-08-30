"""Guard: `slope` is a TANGENT, so nothing may apply a trig function to it.

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

WHY THIS FILE WAS REWRITTEN. The first version of this guard was broken in BOTH directions and both
directions were demonstrated by execution:

  * FALSE POSITIVE. It allowed the bad form in prose only on a line carrying one of fourteen
    hardcoded "negation cues". `05`'s sentence "`sin(slope) > sin θ` makes `wet` come out low" is
    CORRECT explanatory prose — the sine of the tangent genuinely does exceed the sine of the angle,
    which is exactly why the two errors oppose — and it was flagged purely for containing none of
    the fourteen words. The tree shipped red.
  * FALSE NEGATIVE. Eight prose lines that REINTRODUCE the bug all slipped through, because
    ordinary English contains the cues by accident: "computes", "cannot" (`not `), "conversion"
    (`version`), "instead", "would", "never", "rather than", "biases". One of the eight
    ("Use `sin(slope)` here instead of the raw gradient") PRESCRIBES the defect. And the cue list
    could not simply be shortened: seven legitimate lines in `05`/`06`/`17` survived only through
    "computes", "version", "would", "never" and "rather than".

A keyword heuristic cannot separate "prescribes the bug" from "warns about the bug"; the two are
lexically identical. So the hatch is now an EXPLICIT REGISTRY — the pattern this repo already uses
for exactly this situation (`ACCEPTED_CLIPS` in the water-physics figure script). Registering costs
a sentence of deliberate thought instead of an accidental word, and the whole set of exemptions is
auditable in one read, which a heuristic never is.

THREE TIERS.

  Tier 1 — CODE, zero tolerance. Fenced blocks in Markdown; executable statements in Python. That
  is the surface a reader implements from and the surface that actually runs. No line-level
  exemption exists for this tier at all.

  Tier 2 — PROSE, registry only. Markdown outside fences; Python comments and string literals.
  Prose legitimately NAMES the bad form in order to forbid it, so every such occurrence is listed
  in `PROSE_REGISTRY` as (file, exact line substring, one-line reason). Anything unregistered
  fails, naming file, line and text, and telling the author to fix it or register it.

  Tier 3 — SYMBOLS, registry only. `07` writes `s > tan(maxSlope)` and `12` writes
  `tidalRange / tan(shoreSlope)`, both inside fenced blocks, and both are CORRECT because those two
  symbols are angles, not tangents. The old guard let them through with a blanket rule — the
  argument had to start with lowercase `slope` — which made "rename your variable to `localSlope`"
  a universal bypass and enforced nothing about what camelCase `*Slope` names actually mean. They
  are now `ANGLE_VALUED_SYMBOLS` entries. That keeps Tier 1 at genuine zero tolerance (there is no
  per-line escape) while making the load-bearing claim — *this symbol is an angle* — explicit,
  reviewable, and staleness-checked, instead of implied by capitalisation.

WHAT THE SCAN MATCHES. Any call to a trig-like function (`sin cos tan sec csc cot asin acos arcsin
arccos sinh cosh tanh asinh acosh atanh arcsinh arccosh arctanh radians degrees deg2rad rad2deg`,
case-insensitive, with or without an `np.`/`math.` prefix) whose argument mentions an identifier
containing "slope" and does not pass through an angle-producing call. So `sin(2*slope)`,
`tan(-slope)`, `tan( (slope) )`, `SIN(SLOPE)`, `asin(slope)`, `radians(slope)`, `degrees(slope)`
and `sin(localSlope)` are all caught — the old regex missed every one of them.

WHAT IT DELIBERATELY DOES NOT MATCH, and why:
  * `atan`, `arctan`, `atan2`, `arctan2` — recovering the ANGLE from the tangent. That is the
    correct direction and `09` and `render.py` both use it. The old docstring claimed the pattern
    also let `asin` through on purpose; `asin` of a tangent is precisely the bug, so it is now
    forbidden and `atan`/`arctan` are the only survivors.
  * an argument that passes through an angle-producing call — `np.degrees(np.arctan(slope))` in
    `archetypes.py` is a slope histogram in degrees, and correct.
  * `tan(35°)`, `tan(φ)`, `tan(θ_separate)` — trig of an angle literal or an angle-named symbol.
    A threshold is built by taking the tangent of the angle and comparing it to `slope`; that is
    the endorsed form.
  * prose that names the bad form WITHOUT parentheses (`tan of slope`) — there is no call to find,
    and inventing a natural-language matcher is how the last version failed.
  * a trig call whose parentheses do not close within 400 characters — treated as unparseable
    rather than guessed at.
  * this file. Every forbidden form below is a test fixture; the module is the specification of the
    pattern, so it cannot also be subject to it. `test_only_this_file_is_excluded_from_the_scan`
    pins the exclusion at exactly one path so it cannot grow.

COVERAGE. The old guard globbed `references/*.md` only, and so scanned nothing that runs: a critic
inserted `_bug = np.sin(slope_tan)` into `analysis.twi` and all 71 tests passed. The scan now
covers `references/*.md`, the skill root's `SKILL.md` and `index.md`, `reference-impl/*.md`,
`reference-impl/*.py` and `reference-impl/tests/*.py` — see `test_the_scan_reaches_the_code_that_runs`.
"""
import io
import re
import tokenize
from pathlib import Path

import pytest

REF = Path(__file__).resolve().parents[1]          # reference-impl/
SKILL = REF.parent                                 # terrain-architect/
CHAPTERS = SKILL / "references"
SELF = Path(__file__).resolve()

# Everything that mentions `slope` and could be implemented from or executed. `evals/` is data and
# a validator that never names slope; `*.png` obviously cannot carry the defect.
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
# Applying any of these to a tangent is a units error. `sec/csc/cot` are here for completeness;
# `radians/degrees/deg2rad/rad2deg` are here because converting a ratio "to radians" is the same
# mistake wearing a different hat.
TRIG_ON_A_TANGENT = frozenset("""
    sin cos tan sec csc cot
    asin acos arcsin arccos
    sinh cosh tanh asinh acosh atanh arcsinh arccosh arctanh
    radians degrees deg2rad rad2deg
""".split())

# The ONLY legitimate direction: tangent -> angle.
ANGLE_FROM_TANGENT = frozenset(("atan", "arctan", "atan2", "arctan2"))

# `np.sin(` and `math.sin(` both yield the head `sin`, because the lookbehind excludes only
# identifier characters and `.` is not one. `arcsin(` yields `arcsin`, not `sin`, because the
# lookbehind stops `sin` matching after `c`.
CALL_HEAD = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
ANGLE_CALL = re.compile(r"(?<![A-Za-z0-9_])(?:atan2?|arctan2?)\s*\(", re.IGNORECASE)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

ARG_LIMIT = 400          # a trig call whose parens do not close inside this is not a trig call


def _argument(text, open_idx):
    """The text between `open_idx` (a `(`) and its balancing `)`, or None."""
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
    return None


def _is_slope_symbol(name):
    """An identifier that mentions `slope` is the TANGENT unless it is registered as an angle.
    Presuming tangent is the safe default: `06` names the tangent `slope`, so a name built on it
    inherits that meaning until someone writes down why it does not."""
    return "slope" in name.lower() and name not in ANGLE_VALUED_SYMBOLS


def _hits(text):
    """Every trig-like call applied to the slope tangent. Yields (offset, fn, symbol, argument)."""
    for m in CALL_HEAD.finditer(text):
        fn = m.group(1)
        if fn.lower() not in TRIG_ON_A_TANGENT:
            continue
        arg = _argument(text, m.end() - 1)
        if arg is None or ANGLE_CALL.search(arg):
            continue                       # the argument is an angle, not the raw tangent
        symbols = [s for s in IDENT.findall(arg) if _is_slope_symbol(s)]
        if symbols:
            yield m.start(), fn, symbols[0], arg


# ---------------------------------------------------------------------------- #
# tier split: what is code, what is prose
# ---------------------------------------------------------------------------- #
def _markdown_prose_lines(text):
    """Line numbers OUTSIDE fenced blocks. Indented (4-space) code blocks are not recognised as
    fences by this skill's chapters, which fence everything explicitly."""
    prose, in_fence = set(), False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            prose.add(n)
    return prose


def _python_prose_spans(text, path):
    """{line: [(col_start, col_end), ...]} for comments and string literals. A match inside one of
    these is Python PROSE — a docstring or a comment — and goes to Tier 2; anything else is an
    executable statement and goes to Tier 1."""
    spans = {}
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise AssertionError("%s does not tokenise, so the slope-units scan cannot classify it: %s"
                             % (path, exc))
    for tok in tokens:
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        (r0, c0), (r1, c1) = tok.start, tok.end
        if r0 == r1:
            spans.setdefault(r0, []).append((c0, c1))
        else:
            spans.setdefault(r0, []).append((c0, 1 << 30))
            for r in range(r0 + 1, r1):
                spans.setdefault(r, []).append((0, 1 << 30))
            spans.setdefault(r1, []).append((0, c1))
    return spans


def _scan(path):
    """(code_offenders, prose_offenders); each a list of (line, text, fn, symbol)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    starts = []                                  # byte offset of each line start
    off = 0
    for line in lines:
        starts.append(off)
        off += len(line) + 1

    if path.suffix == ".py":
        spans = _python_prose_spans(text, path)

        def is_prose(lineno, col):
            return any(a <= col < b for a, b in spans.get(lineno, ()))
    else:
        prose_lines = _markdown_prose_lines(text)

        def is_prose(lineno, col):
            return lineno in prose_lines

    code, prose = [], []
    for pos, fn, symbol, _arg in _hits(text):
        lineno = text.count("\n", 0, pos) + 1
        col = pos - starts[lineno - 1]
        row = (lineno, lines[lineno - 1].strip(), fn, symbol)
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
    return Path(path).resolve().relative_to(SKILL).as_posix()


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
    ("references/17-periglacial.md",
     "Writing `sin(slope)` would apply a sine to a quantity that",
     "Solifluction's units note, naming the bad form it forbids."),
    ("references/17-periglacial.md",
     "rather than `sin(slope)`",
     "Offers the exact identity `slope / sqrt(1 + slope²)` as the replacement, naming what it "
     "replaces."),
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

# Identifiers that mention `slope` but hold an ANGLE, so trig on them is correct. This is the only
# way a fenced code block may carry a trig call on a `*slope*` name, and it is a statement about
# the symbol, not a pardon for a line.
ANGLE_VALUED_SYMBOLS = {
    "maxSlope":
        "07-scatter.md's placement gate writes `if s > tan(maxSlope)` with `s = slope(p)`: the "
        "tangent is on the left and `maxSlope` is the angle whose tangent forms the threshold — "
        "the endorsed comparison form from 06.",
    "shoreSlope":
        "12-glacial-coastal.md writes `intertidalWidth = tidalRange / tan(shoreSlope)`. That is "
        "the run for a given rise, so `shoreSlope` is the beach angle; substituting a tangent "
        "there would give a width in the wrong units.",
}


def _registered(key, line_text):
    for f, substring, _reason in PROSE_REGISTRY + KNOWN_UNFIXED:
        if f == key and substring in line_text:
            return True
    return False


FIX_ADVICE = (
    "  `slope` is the DIMENSIONLESS gradient |grad h| = tan(theta), not an angle (06).\n"
    "  Use `slope` directly where the textbook form wants `tan theta`;\n"
    "  use `slope / sqrt(1 + slope**2)` where it wants `sin theta`;\n"
    "  use `atan(slope)` to recover the angle itself.\n")


# ---------------------------------------------------------------------------- #
# TIER 1 — code, zero tolerance
# ---------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _scanned_files(), ids=_key)
def test_no_code_applies_trig_to_the_slope_tangent(path):
    """Fenced blocks and executable Python. There is no registry for this tier: a reader
    implements from these and the interpreter runs them."""
    found, _ = _scan(path)
    assert not found, (
        "%s applies a trig function to the slope TANGENT in code:\n%s%s"
        % (_key(path),
           "".join("  %s:%d: %s(%s)  ->  %s\n" % (_key(path), n, fn, sym, t) for n, t, fn, sym in found),
           FIX_ADVICE))


# ---------------------------------------------------------------------------- #
# TIER 2 — prose, registry only
# ---------------------------------------------------------------------------- #
@pytest.mark.parametrize("path", _scanned_files(), ids=_key)
def test_every_prose_occurrence_is_registered(path):
    """Prose may NAME the bad form in order to forbid it — but each such line must be registered
    with a reason. No keyword makes a line legal."""
    _, found = _scan(path)
    key = _key(path)
    unregistered = [(n, t, fn, sym) for n, t, fn, sym in found if not _registered(key, t)]
    assert not unregistered, (
        "%s applies a trig function to the slope TANGENT in prose, and the line is not in "
        "PROSE_REGISTRY:\n%s"
        "Either FIX it:\n%s"
        "or REGISTER it, by adding a row to PROSE_REGISTRY in %s:\n"
        "    (%r,\n"
        "     %r,\n"
        "     \"<one line saying why this occurrence is correct>\"),\n"
        % (key,
           "".join("  %s:%d: %s(%s)  ->  %s\n" % (key, n, fn, sym, t)
                   for n, t, fn, sym in unregistered),
           FIX_ADVICE, SELF.name, key, unregistered[0][1][:80]))


# ---------------------------------------------------------------------------- #
# the registries police themselves
# ---------------------------------------------------------------------------- #
def _prose_offender_lines(key):
    path = SKILL / key
    if not path.exists():
        return None
    _, prose = _scan(path)
    return [t for _n, t, _fn, _sym in prose]


@pytest.mark.parametrize("key,substring,reason", PROSE_REGISTRY,
                         ids=["%s::%s" % (k.rsplit("/", 1)[-1], s[:28]) for k, s, _ in PROSE_REGISTRY])
def test_the_prose_registry_is_not_stale(key, substring, reason):
    """A registered exemption whose line no longer exists — fixed, reworded, or deleted — must
    FAIL, so the registry liquidates itself instead of accumulating dead pardons."""
    lines = _prose_offender_lines(key)
    assert lines is not None, "PROSE_REGISTRY names %s, which no longer exists" % key
    assert any(substring in line for line in lines), (
        "PROSE_REGISTRY row for %s is STALE: no prose line containing a trig call on `slope` "
        "still contains %r. If the line was fixed or reworded, delete this row.\nReason on file: %s"
        % (key, substring, reason))


@pytest.mark.parametrize("key,substring,reason", KNOWN_UNFIXED,
                         ids=["%s::%s" % (k.rsplit("/", 1)[-1], s[:28]) for k, s, _ in KNOWN_UNFIXED])
def test_the_known_unfixed_registry_is_not_stale(key, substring, reason):
    """The tolerated-defect list names LINES, not counts. Fixing the line fails this test, which
    is the signal to drop the row — and, unlike a count, fixing one offender while introducing a
    different one in the same chapter no longer cancels out."""
    lines = _prose_offender_lines(key)
    assert lines is not None, "KNOWN_UNFIXED names %s, which no longer exists" % key
    assert any(substring in line for line in lines), (
        "KNOWN_UNFIXED row for %s looks FIXED — no offending line still contains %r. "
        "Delete the row.\nReason on file: %s" % (key, substring, reason))


def test_the_angle_symbol_registry_is_not_stale():
    """A symbol declared angle-valued must still be used somewhere, or the declaration is a
    standing invitation to name a tangent after it."""
    declared = set(ANGLE_VALUED_SYMBOLS)
    used = set()
    for path in _scanned_files():
        text = path.read_text(encoding="utf-8")
        for m in CALL_HEAD.finditer(text):
            if m.group(1).lower() not in TRIG_ON_A_TANGENT:
                continue
            arg = _argument(text, m.end() - 1)
            if arg is None:
                continue
            used |= declared & set(IDENT.findall(arg))
    assert declared <= used, (
        "ANGLE_VALUED_SYMBOLS declares %s, which no longer appears in any trig call in the scanned "
        "tree. Delete the entry." % sorted(declared - used))


def test_the_angle_symbol_registry_cannot_relabel_the_slope_tangent():
    """`06` names the tangent `slope`. Declaring `slope` — or anything built on it as a prefix —
    to be an angle would turn Tier 3 into the blanket bypass it replaced."""
    bad = [n for n in ANGLE_VALUED_SYMBOLS if n.lower().startswith("slope")]
    assert not bad, (
        "ANGLE_VALUED_SYMBOLS may not contain %s: a name beginning with `slope` inherits 06's "
        "definition of `slope` as the tangent. Rename the symbol for the angle it holds "
        "(e.g. `reposeAngle`) instead of declaring the tangent to be an angle." % bad)


def test_every_registry_entry_carries_a_reason():
    """The registry costs a sentence of thought, and that is the entire point of it over a
    keyword list. An empty or token reason defeats it."""
    thin = []
    for key, substring, reason in PROSE_REGISTRY + KNOWN_UNFIXED:
        if len(reason.strip()) < 40:
            thin.append("%s :: %r" % (key, substring))
    for name, reason in ANGLE_VALUED_SYMBOLS.items():
        if len(reason.strip()) < 40:
            thin.append("ANGLE_VALUED_SYMBOLS[%r]" % name)
    assert not thin, (
        "these registry rows have no real reason written on them, so nobody can audit them: %s"
        % thin)


def test_the_registries_have_no_duplicate_rows():
    """Two rows exempting the same line means one of them is already dead weight."""
    rows = [(k, s) for k, s, _ in PROSE_REGISTRY + KNOWN_UNFIXED]
    dupes = sorted({r for r in rows if rows.count(r) > 1})
    assert not dupes, "duplicated registry rows: %s" % dupes


# ---------------------------------------------------------------------------- #
# coverage: what the guard actually reaches
# ---------------------------------------------------------------------------- #
def test_the_scan_reaches_the_code_that_runs():
    """The old guard globbed `references/*.md` only, so `np.sin(slope_tan)` could be inserted into
    `analysis.twi` with every test still green. Pin the surface explicitly."""
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
    assert len(keys) >= 100, (
        "the scan covers only %d files; it reached 100+ when written, so a glob has been lost"
        % len(keys))
    assert all(any(p.match(g) for g in ("*.md", "*.py")) for p in _scanned_files())


def test_only_this_file_is_excluded_from_the_scan():
    """Self-exclusion is necessary — every forbidden form in this module is a fixture — but it is
    also the one hole in the coverage, so it is pinned at exactly one path."""
    everything = set()
    for pattern in SCAN_GLOBS:
        everything |= {p.resolve() for p in SKILL.glob(pattern) if p.is_file()}
    excluded = everything - set(_scanned_files())
    assert excluded == {SELF}, (
        "the scan skips more than this file: %s" % sorted(_key(p) for p in excluded))


# ---------------------------------------------------------------------------- #
# the pattern, proved on both sides
# ---------------------------------------------------------------------------- #
# 33 realistic ways the units error comes back. The previous regex caught 11 of these.
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


@pytest.mark.parametrize("form", REINTRODUCTIONS)
def test_the_pattern_catches_every_known_reintroduction(form):
    """A guard nobody has seen fail is a guard nobody should trust. Whitespace, sign, arithmetic on
    the argument, module prefix, case and the inverse/hyperbolic/conversion families are all ways
    the same units error comes back."""
    assert list(_hits("    x = %s   # units error" % form)), (
        "the scan misses %r, so that spelling of the defect ships silently" % form)


LEGITIMATE = (
    "Plot the distribution of `atan(slope)` in degrees.",
    "| **Slope shade** | `atan(slope)` on a ramp | Steepness directly",
    "        return np.arctan(slope)",
    "p99 = np.degrees(np.arctan(np.percentile(slope, 99)))",
    "theta_deg = math.degrees(math.atan(slope))",
    "rockMask = smoothstep(tan(35deg), tan(45deg), slope)   # steep = exposed rock",
    "slopeSel(s, lo, hi, w) = smoothstep(lo-w, lo+w, s)     # s = tan, not degrees",
    "    FS  = (1 - wet * rw/rs) * tan(phi) / slope         # factor of safety",
    "    a   = g*sin(theta) - mu*g*cos(theta) - g*v*v/xi    # Voellmy: theta IS an angle",
    "    sin_theta = slope / sqrt(1 + slope**2)             # exact, stays in the tangent",
    "  at `slope = tan(phi)` -- the critical angle is `phi` on the nose.",
    "screeSource = cliffMask * weatheringRate   # cliffMask = slope > ~55deg",
    "    thresh = np.tan(np.radians(repose_deg))            # threshold from an angle",
    "        if slope_w > tan(theta_separate): deposit UPWIND",
    "    if s > tan(maxSlope): reject                       # 07, maxSlope is an angle",
    "    intertidalWidth = tidalRange / tan(shoreSlope)     # 12, shoreSlope is an angle",
    "`tan(<a number in degrees>)` = fine;",
)


@pytest.mark.parametrize("line", LEGITIMATE)
def test_the_pattern_does_not_flag_the_legitimate_forms(line):
    """The other half. A guard that cries wolf gets deleted — and the last one did cry wolf, on
    `05`'s correct `sin(slope) > sin θ` sentence."""
    assert not list(_hits(line)), "the scan flags a CORRECT form: %r" % line


def test_asin_is_forbidden_even_though_atan_is_allowed():
    """The old docstring claimed the lookbehind existed to let `atan`/`arctan`/`asin` through.
    `atan(tan θ)` recovers θ; `asin(tan θ)` is the defect itself, and is undefined above 45°."""
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
    assert not _registered(_key(doc) if (SKILL in doc.parents) else "99-synthetic.md", prose[0][1]), (
        "a synthetic bypass line must not be pre-registered")


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
    assert [n for n, _t, _f, _s in code] == [3], code
    assert [n for n, _t, _f, _s in prose] == [5, 6], (
        "line 5 carried a negation cue and used to be exempt; under the registry it is prose like "
        "any other and must be listed, got %s" % prose)


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
    assert [n for n, _t, _f, _s in code] == [6], (
        "the executable injection `np.sin(slope_tan)` must land in the zero-tolerance tier, got %s"
        % code)
    assert [n for n, _t, _f, _s in prose] == [1, 5], (
        "a docstring naming the bad form is PROSE and must be registrable, got %s" % prose)


# ---------------------------------------------------------------------------- #
# the chapters and the shipped code still agree
# ---------------------------------------------------------------------------- #
def test_06_defines_slope_as_a_tangent_and_says_so():
    """The fix is only durable if the DEFINITION site warns the next reader."""
    text = (CHAPTERS / "06-analysis-masks.md").read_text(encoding="utf-8")
    assert "Never write `sin(slope)`" in text, (
        "06 has lost the explicit note saying what `slope` is and is not. That note is what stops "
        "the units error being reintroduced at a new call site.")
    assert "sqrt(1 + slope²)" in text, (
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
