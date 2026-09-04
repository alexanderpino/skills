"""ONE text-scanning model, shared by the guards that read this skill's prose and code.

WHY THIS MODULE EXISTS. Two guards were already reading the same corpus with two different
answers to the same question — "is this line code, or is it prose?"

  * `test_slope_units.py` recognised a fence with `line.lstrip().startswith("```")`, i.e. at any
    indentation.
  * `test_atom_coverage.py` recognised one with `re.compile(r"^```[^\\n]*\\n(.*?)^```", re.S | re.M)`,
    i.e. only in column 0.

On a block fenced under a list item — which is indented — the first guard sees pseudocode and
applies its zero-tolerance code tier to it, and the second sees nothing at all and applies its
"documented as a routine" search to a document it believes has no fenced blocks. Neither is wrong
about its own rule; they simply are not the same rule, and nothing in the tree said which one the
skill means. A drifting definition of "code" silently moves lines between a zero-tolerance tier
and a registry tier, which is the most consequential thing either guard decides.

So the fence model, the Python prose model, the identifier pattern and the completeness matcher
live here once. A guard that wants a different rule now has to change it here, in front of every
consumer, instead of privately.

WHAT IS DELIBERATE ABOUT EACH MODEL

  FENCES are indent-tolerant (the `lstrip` model wins) because Markdown itself is: a fence opened
  inside a list item is indented, and reading its contents as prose would put executable
  pseudocode into a tier that has a registry escape hatch. Tilde fences are recognised for the
  same reason — `~~~` is a fence in CommonMark and in every renderer this skill's docs pass
  through, and a guard that does not know that reads the whole block as prose. A fence is closed
  only by the SAME marker character, at least as long, with nothing after it, so a ``` line inside
  a ~~~ block (and a longer ```` fence wrapping a ``` example) stays content instead of toggling.

  PYTHON PROSE is one `tokenize` pass that RAISES on failure. A reference module that does not
  parse is a defect in its own right, and both known fail-open fallbacks — returning the raw
  source, or returning no spans — hand comments and docstrings back to the consumer as if they
  were executable code (or vice versa), i.e. they disable exactly the thing the call is for.

  `complete_pattern` is the completeness matcher: spacing is not meaning, but a prefix is not a
  match and neither is a suffix. It is used on both sides of a claim so the two sides cannot
  disagree about what "the literal is present" means.
"""
import functools
import io
import re
import tokenize
from collections import namedtuple

__all__ = [
    "IDENT", "IDENT_UNICODE",
    "Fence", "fenced_blocks", "fenced_text", "prose_line_numbers",
    "py_prose_spans", "blank_py_prose",
    "complete_pattern", "complete_match",
]

# --------------------------------------------------------------------------- #
# identifiers
# --------------------------------------------------------------------------- #
# ASCII Python identifier. This is byte-for-byte the pattern `test_slope_units.py` and
# `test_atom_coverage.py` each carried privately.
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# The same thing, Unicode-aware. The chapters write real Greek: `θ_separate`, `α_min`, `φ`. Under
# the ASCII pattern `θ_separate` is not a symbol at all — it decomposes into the token `_separate`,
# so a guard keyed on symbol names cannot say anything true about it. Python itself accepts these
# as identifiers, so a scanner that reads both chapters and modules needs the Unicode form.
IDENT_UNICODE = re.compile(r"[^\W\d][\w]*", re.UNICODE)


# --------------------------------------------------------------------------- #
# fences
# --------------------------------------------------------------------------- #
Fence = namedtuple("Fence", "marker info first_line last_line text closed")
#   marker      the run of ` or ~ that opened it (length matters for closing)
#   info        the info string on the opening line ("python", "text", "")
#   first_line  1-based line number of the OPENING marker line
#   last_line   1-based line number of the CLOSING marker line, or of the last line of the
#               document when the fence is never closed
#   text        the block contents, marker lines excluded
#   closed      False when the document ended inside the fence

_FENCE_LINE = re.compile(r"^[ \t]*(?P<marker>`{3,}|~{3,})(?P<info>.*)$")


def _fence_open(line):
    """(marker, info) if `line` can OPEN a fence, else None."""
    m = _FENCE_LINE.match(line)
    if not m:
        return None
    marker, info = m.group("marker"), m.group("info")
    # CommonMark: a backtick fence's info string may not contain a backtick. Without this, the
    # inline-code line ``` `a` and `b` and `c` ``` would open a fence and silently reclassify the
    # rest of the document.
    if marker[0] == "`" and "`" in info:
        return None
    return marker, info


def _fence_close(line, marker):
    """True if `line` closes a fence opened by `marker`.

    Same marker character, at least as long — so a ``` line inside a ~~~ block, or inside a
    longer ```` block, is content rather than a toggle.

    TRAILING TEXT ON THE CLOSING LINE IS TOLERATED, and that is a deliberate departure from
    CommonMark (which requires a bare closing fence). `references/10-primitives-ops-filters.md:106`
    is `` ``` `` followed by a trailing `#` comment that continues onto the next lines. Under the
    strict rule that line does not close, the fence runs on, and the parity of every fence after
    it inverts: 571 lines of that chapter change tier — prose read as pseudocode by the guard
    whose code tier has no escape hatch. The document plainly means it as a close, and both
    private models this one replaces read it that way.
    """
    m = _FENCE_LINE.match(line)
    if not m:
        return False
    got = m.group("marker")
    return got[0] == marker[0] and len(got) >= len(marker)


def fenced_blocks(text):
    """Every fenced block in `text`, in document order, as `Fence` records.

    An unclosed fence runs to the end of the document (CommonMark's rule) and is reported with
    `closed=False`, so a consumer that cares can say so rather than silently reading the tail of
    the document as prose.
    """
    lines = text.splitlines()
    out, i, n = [], 0, len(lines)
    while i < n:
        opened = _fence_open(lines[i])
        if opened is None:
            i += 1
            continue
        marker, info = opened
        start = i
        j = i + 1
        while j < n and not _fence_close(lines[j], marker):
            j += 1
        closed = j < n
        out.append(Fence(marker=marker, info=info.strip(), first_line=start + 1,
                         last_line=(j + 1) if closed else n,
                         text="\n".join(lines[start + 1:j]), closed=closed))
        i = j + 1 if closed else n
    return out


def fenced_text(text):
    """The contents of every fenced block, joined — i.e. the pseudocode and nothing else."""
    return "\n".join(b.text for b in fenced_blocks(text))


def prose_line_numbers(text):
    """1-based line numbers that are OUTSIDE every fenced block.

    Fence marker lines themselves belong to neither side and are excluded, which is what both
    previous private implementations did.
    """
    fenced = set()
    for b in fenced_blocks(text):
        fenced.update(range(b.first_line, b.last_line + 1))
    return {n for n in range(1, len(text.splitlines()) + 1) if n not in fenced}


# --------------------------------------------------------------------------- #
# python prose
# --------------------------------------------------------------------------- #
_PROSE_TOKENS = frozenset((tokenize.COMMENT, tokenize.STRING))


def py_prose_spans(source, path=None):
    """`{line: [(col_start, col_end), ...]}` covering comments and string literals.

    A match inside one of these spans is Python PROSE — a docstring, a comment, an f-string's
    literal text. Anything else is an executable statement.

    RAISES `AssertionError` if the source does not tokenise. `path` only decorates the message.
    """
    spans = {}
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        raise AssertionError(
            "%s does not tokenise, so its comments and docstrings cannot be told apart from its "
            "executable statements: %s. Every fallback here is a fail-open — it either hands "
            "prose to a zero-tolerance code check or hides code inside a registry tier — so a "
            "module that does not parse is raised on instead."
            % (path if path is not None else "<source>", exc)) from exc
    for tok in tokens:
        name = tokenize.tok_name.get(tok.type, "")
        if tok.type not in _PROSE_TOKENS and not name.startswith("FSTRING_MIDDLE"):
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


def blank_py_prose(source, path=None):
    """`source` with comments and string literals replaced by spaces, line/column layout intact.

    Same single model as `py_prose_spans`, expressed for a consumer that wants to SEARCH the code
    side rather than classify a position — a constant that appears only in a comment must not
    count as evidence that the module still uses it.
    """
    spans = py_prose_spans(source, path)
    lines = source.splitlines(keepends=True)
    for n, cols in spans.items():
        if not 1 <= n <= len(lines):
            continue
        chars = list(lines[n - 1])
        for a, b in cols:
            for i in range(a, min(b, len(chars))):
                if chars[i] != "\n":
                    chars[i] = " "
        lines[n - 1] = "".join(chars)
    return "".join(lines)


# --------------------------------------------------------------------------- #
# the completeness matcher
# --------------------------------------------------------------------------- #
_WORDISH = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_."
_NUMERIC = "0123456789."
_TOKEN = re.compile(r"[A-Za-z0-9_.]+|\s+|[^\sA-Za-z0-9_.]+")

# THE CHARACTERS AN EDGE MAY NOT TOUCH — one set per kind of edge, spent on BOTH sides of the
# literal. A lead-only exclusion is not a boundary: excluding a sign before the number while
# allowing one after it is what let `n = 3` match `n = 3-4`.
_SIGNS = "+\\-‐-―−"
_SUPSUB = "⁰-₟"
_NUM_EDGE = "0-9._" + _SIGNS + "°" + _SUPSUB
_WORD_EDGE = "A-Za-z0-9_" + _SUPSUB
_MATH_EDGE = _SUPSUB + "·"


def _wordish(ch):
    return bool(ch) and ch in _WORDISH


def _numeric(ch):
    return bool(ch) and ch in _NUMERIC


@functools.lru_cache(maxsize=None)
def complete_pattern(literal):
    """Compile `literal` into a regex that matches it as a COMPLETE claim.

    SPACING IS NOT MEANING: each run of whitespace becomes `\\s*`, or `\\s+` where dropping it
    would fuse two words. A PREFIX IS NOT A MATCH, AND NEITHER IS A SUFFIX: the literal is
    bracketed by boundaries chosen from its own first and last characters, with the same character
    set used at both edges, so `n=3` is not satisfied by `n=3.5`, `n=30`, `n=3e5`, `-n=3` or the
    range `n = 3-4`.
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
    elif _wordish(first):
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


def complete_match(text, literal):
    """True if `literal` occurs in `text` as a complete claim, not as part of a longer one."""
    return complete_pattern(literal).search(text) is not None
