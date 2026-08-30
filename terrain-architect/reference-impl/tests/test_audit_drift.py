"""Anti-drift harness for the audit documents (`NODE-PARITY-AUDIT.md`, `VALIDATION.md`).

WHY THIS EXISTS, AND THE DEFECT THAT CAUSED IT. `ATOM-COVERAGE.md` cannot go
stale, because `test_atom_coverage.py` fails when its list and the modules
disagree. The other audit documents had no such link, and one of them drifted
exactly as you would predict: `NODE-PARITY-AUDIT.md` named
**braided / anastomosing river channels** as the single remaining node-level
gap and recommended Murray & Paola (1994) as "the next atom" -- while
`braided.braided_river` had already shipped, on that very model, with four
tests and an entry in the coverage manifest.

Nobody was wrong when it was written. An audit is a SNAPSHOT, and a snapshot
with nothing pointing at the code it describes rots the moment the code moves.
A reader planning work off that page would have rebuilt what already existed.

WHAT THIS PROVES, AND WHAT IT DOES NOT. It proves the audits' *claims about
presence and absence* still hold against the modules. It does not prove the
audits' judgements are right -- whether our stream-power really is ahead of
Gaea's is not a thing a test can settle, and this file does not pretend to.
"""
import importlib
import re
from pathlib import Path

REF = Path(__file__).resolve().parents[1]                 # reference-impl/
PARITY_RAW = (REF / "NODE-PARITY-AUDIT.md").read_text(encoding="utf-8")
VALIDATION_RAW = (REF / "VALIDATION.md").read_text(encoding="utf-8")


def _flat(text):
    """Whitespace-normalised text, for needles that must survive a re-wrapped line.

    These audits are hard-wrapped prose. `"spectral band"` NEVER matched, because the phrase
    falls either side of a line break ("...remain a spectral\\nband terrain filter..."), so the
    row that guards `ops_filters.spectral_band` could not fire whatever the code did. Matching a
    multi-word phrase against hard-wrapped text is matching against the wrap, not the words:
    every phrase needle in this file goes through here.
    """
    return " ".join(text.split())


PARITY = _flat(PARITY_RAW)
VALIDATION = _flat(VALIDATION_RAW)

# The audit's blanket "nothing is missing" sentence. Kept as one constant because two rows below
# key off it, and because it is exactly the sentence a well-meaning edit would re-word.
_NO_GAP = re.compile(r"\*\*no\*\*\s+genuine[^.;]*?\bis missing\b", re.I)

# Capabilities the parity audit may claim as missing. Each maps to the callable
# that would exist if it were built, so "missing" is checkable rather than
# asserted. Adding a row here is how a future gap gets guarded.
CLAIMABLE = {
    "braided": ("braided", "braided_river"),
    "anastomosing": ("braided", "braided_river"),
    "spectral band": ("ops_filters", "spectral_band"),
    "tileable": ("ops_filters", "wrap_tileable"),
}


def _exists(module_name, attr):
    try:
        mod = importlib.import_module(module_name)
    except ImportError:
        return False
    return callable(getattr(mod, attr, None))


def test_parity_audit_does_not_claim_a_gap_that_is_already_built():
    """A capability named as missing must genuinely be absent from the code.

    This is the row that would have caught the braided-river drift on the day
    the module landed, instead of a reader catching it months later.

    ⚠️ THIS ROW WAS DEAD TWO WAYS AND IS THE REASON THE FILE IS THE WAY IT IS.
    (a) it was guarded by `"no** genuine" not in claim`, and the claim paragraph
    OPENS with "**no** genuine ... is missing" -- so the condition was false for
    every phrase and the body never ran; (b) even with the guard gone, the needle
    `"spectral band"` straddles a line break in the source, so it could not match.
    A whole-paragraph exemption was the wrong shape anyway: this paragraph both
    denies a genuine gap AND names two follow-ups in the next sentence, so one
    sentence was switching off the check on the other. The exemption is now
    per SENTENCE -- a denial only excuses the capability named in the same
    sentence as the denial, and can never disable the row wholesale.
    """
    bottom = PARITY[PARITY.index("## Bottom line"):]
    # Only the sentences that state what is missing, not the historical note
    # that records the correction -- the note deliberately names the capability.
    claim = bottom.split("⚠️")[0].lower()
    sentences = [s for s in re.split(r"(?<=[.;])\s+", claim) if s.strip()]
    still_wrong = []
    for phrase, (module_name, attr) in CLAIMABLE.items():
        named_as_gap = [s for s in sentences if phrase in s and not _NO_GAP.search(s)]
        if named_as_gap and _exists(module_name, attr):
            still_wrong.append("%s is named as a gap but %s.%s exists"
                               % (phrase, module_name, attr))
    assert not still_wrong, (
        "NODE-PARITY-AUDIT.md is stale:\n  " + "\n  ".join(still_wrong))


def test_parity_audit_bottom_line_matches_the_code():
    """If the audit says nothing is missing, the guarded capabilities must be there.

    The needle is a whole sentence and the audit is hard-wrapped, so it is matched against the
    whitespace-flattened text: re-wrapping that paragraph must not silently turn this row into a
    no-op by sending it down the `return`.
    """
    bottom = PARITY[PARITY.index("## Bottom line"):]
    if not _NO_GAP.search(bottom):
        return                       # it claims a gap; the row above judges it
    missing = [
        "%s.%s" % (m, a) for m, a in
        {CLAIMABLE[k] for k in ("braided", "anastomosing")}
        if not _exists(m, a)
    ]
    assert not missing, (
        "NODE-PARITY-AUDIT.md claims full node-level parity, but these are "
        "absent: " + ", ".join(sorted(missing)))


def test_validation_ledger_quotes_the_real_test_count():
    """`VALIDATION.md` illustrates its point with this suite's own size.

    ⚠️ IT QUOTED 117 WHILE THE SUITE HELD 379. The number is rhetorical -- the
    sentence is about self-consistency being weaker than validity -- but a
    reference implementation that misreports its own scale by a factor of three
    undercuts the very argument the sentence is making. Counting the test
    functions is cheap; leaving the figure to rot is not.

    Read from the whitespace-flattened text: `"379 tests pass"` is a five-token
    needle in hard-wrapped prose, and a wrap between the number and the words
    would otherwise trip the "no longer quotes a count" branch (or, worse, hide a
    stale figure) purely because a paragraph was reflowed.
    """
    quoted = re.findall(r'"(\d+) tests pass"', VALIDATION)
    assert quoted, 'VALIDATION.md no longer quotes a test count; update this row'
    actual = sum(
        len(re.findall(r"^def test", p.read_text(encoding="utf-8"), re.M))
        for p in sorted((REF / "tests").glob("test_*.py"))
    )
    for q in quoted:
        assert abs(int(q) - actual) <= 0.1 * actual, (
            'VALIDATION.md quotes "%s tests pass"; this suite defines %d test '
            "functions. Requote it or drop the number." % (q, actual)
        )


def test_every_audit_document_is_reachable_from_the_readme():
    """An audit nobody can find is an audit nobody re-runs.

    Needle is a single unbroken token (a filename), so line wrapping cannot split it; read raw.
    """
    readme = (REF / "README.md").read_text(encoding="utf-8")
    audits = sorted(p.name for p in REF.glob("*.md") if p.name != "README.md")
    unlinked = [a for a in audits if a not in readme]
    assert not unlinked, (
        "these audit documents are not linked from reference-impl/README.md: "
        + ", ".join(unlinked))


def test_the_eval_readme_axis_table_matches_evals_json():
    """`evals/README.md` lists id ranges per axis. Those ranges rot.

    ⚠️ THREE OF FIVE ROWS WERE STALE and one axis was missing entirely. The table is the
    document a maintainer reads to know what the suite covers, and the release bar in that same
    README is defined PER AXIS — so a row that under-reports its ids under-reports the coverage
    the bar is computed on. A harsh-critic pass found this; nothing in the repo would have.

    The check is deliberately on MEMBERSHIP rather than on the exact range string: `1-3` and
    `1, 2, 3` are the same claim, and a test that fails on formatting teaches people to edit the
    test.

    This one deliberately does NOT flatten whitespace: it matches markdown TABLE ROWS, which are
    one-per-line by construction, and flattening would merge them. Its needles inside a row
    (`evals.json`, `(ids`) are single unbroken tokens, so there is nothing here for a wrap to
    split.
    """
    import json
    root = REF.parent
    evals = json.loads((root / "evals" / "evals.json").read_text(encoding="utf-8"))["evals"]
    readme = (root / "evals" / "README.md").read_text(encoding="utf-8")

    by_axis = {}
    for e in evals:
        by_axis.setdefault(e["axis"], set()).add(int(e["id"]))

    problems = []
    for axis, ids in sorted(by_axis.items()):
        # the table row naming this axis, matched on the `evals.json (ids ...)` cell
        rows = [ln for ln in readme.splitlines()
                if ln.startswith("|") and "evals.json" in ln and "(ids" in ln
                and axis.split("-")[0].lower() in ln.lower()]
        if not rows:
            problems.append("axis %r has no row in the README table" % axis)
            continue
        cell = re.search(r"\(ids ([^)]*)\)", rows[0]).group(1)
        listed = set()
        for part in cell.replace("\u2013", "-").split(","):
            part = part.strip()
            if "-" in part:
                lo, hi = part.split("-")
                listed.update(range(int(lo), int(hi) + 1))
            elif part.isdigit():
                listed.add(int(part))
        missing = sorted(ids - listed)
        extra = sorted(listed - ids)
        if missing:
            problems.append("axis %r: ids %s are in evals.json but not in the README row"
                            % (axis, missing))
        if extra:
            problems.append("axis %r: ids %s are in the README row but not on that axis"
                            % (axis, extra))
    assert not problems, "evals/README.md's axis table is stale:\n  " + "\n  ".join(problems)
