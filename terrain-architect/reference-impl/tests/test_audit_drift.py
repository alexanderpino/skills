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

import pytest

REF = Path(__file__).resolve().parents[1]                 # reference-impl/
PARITY_RAW = (REF / "NODE-PARITY-AUDIT.md").read_text(encoding="utf-8")
VALIDATION_RAW = (REF / "VALIDATION.md").read_text(encoding="utf-8")
SIMAUDIT_RAW = (REF / "SIMULATION-AUDIT.md").read_text(encoding="utf-8")


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


# --------------------------------------------------------------------------- #
# SIMULATION-AUDIT.md — the "Ours" column, which is where this document lied four times
#
# ⚠️ THIS FILE GUARDED THE WRONG DOCUMENT FOR MONTHS. `CLAIMABLE` above covers only
# NODE-PARITY-AUDIT.md, so SIMULATION-AUDIT.md's scorecard was unguarded, and four of
# its rows understated what ships:
#
#   Lava flow  — said "ejecta CA only ... **gap** ... upgrade: thermo-rheological CA",
#                while sims_illustrative.lava_flow IS a thermo-rheological CA with a
#                temperature-dependent Bingham yield stress. It is tested, dimensionally
#                audited, cited to Miyamoto & Sasaki 1997 and drawn as gallery panel 30.
#                The "ejecta CA" it credited us with does not exist at all.
#   Karst caves — said "— (prose only)", while landforms.karst_sinkholes ships dolines
#                with a lognormal size distribution and the sink_mask that 03 must not
#                fill, tested in test_landforms.py.
#   Hydraulic  — said "Lagrangian droplet ... solid, not SOTA ... don't make physical
#                claims on it", naming Mei 2007 as the SOTA it lacked — while
#                erosion_pipe.py IS Mei 2007, ships, and is tested by test_pipe.py, and
#                two other cells of this same document said so.
#   Coastal    — said "simple cliff retreat", understating a notch -> thermal collapse ->
#                retreat loop with a wave-cut platform (sims_illustrative.coastal_retreat).
#                Only the wave-energy-proportional rate law is genuinely absent.
#
# All four are the SAME failure and it is the expensive one: a reader planning work off
# this scorecard sets out to build something that already exists.
#
# ⚠️ WHY THE PRIMARY CHECK IS "DOES THE CELL NAME THE CALLABLE", NOT "DOES IT SAY NOTHING".
# The first guard here asked whether the "Ours" cell was empty. That is the wrong question
# twice over. It misses every cell that says something FALSE rather than nothing — the lava
# row's "ejecta CA only" and the hydraulic row's "Lagrangian droplet" both sail through it —
# and, on the empty case it does target, it is defeated by any spelling of a dash a writer
# might reach for: `**—**`, `*—*`, an en dash, a figure dash, `--`, a backticked dash,
# `&mdash;`, a trailing footnote marker, "docs only", "not implemented", "TBD". Only karst
# ever LOOKED like an empty cell; lava, hydraulic and karst are one failure mode.
#
# So the primary row asserts the literal attribute name appears in the cell. There is no
# regex to keep in step with a writer's imagination, and it fails on all four historical
# defects. `_CLAIMS_NOTHING` is kept behind it as belt-and-braces — widened, and matched
# against a NORMALISED cell — with the escape table pinned below as a parametrised negative
# test, so a future narrowing of the matcher fails immediately instead of silently.
#
# ⚠️ AND THE VERDICT IS STILL LEFT TO A HUMAN. A **gap** verdict can be perfectly honest
# while something adjacent ships — karst is exactly that case: the surface expression exists,
# the 3-D conduit network genuinely does not, and forcing that row to stop saying "gap" would
# replace one false statement with another. The inventory is mechanical; the judgement is not.

SIMAUDIT_OURS = {
    # row subject                      -> (module, attribute) the "Ours" cell must NAME
    "Lava flow": ("sims_illustrative", "lava_flow"),
    "Karst caves": ("landforms", "karst_sinkholes"),
    "Hydraulic (detail/interactive)": ("erosion_pipe", "pipe_erode"),
    "Coastal": ("sims_illustrative", "coastal_retreat"),
    "Sediment / deposition": ("erosion_pipe", "pipe_erode"),
    "Aeolian (dunes + abrasion)": ("aeolian", "yardang"),
    "Glacial": ("glacier", "glacier_carve"),
}

# Dash characters a writer might reach for where a plain hyphen was meant: hyphen, non-breaking
# hyphen, figure dash, en dash, em dash, horizontal bar, minus sign.
_DASHES = "‐‑‒–—―−"


def _plain(cell):
    """A scorecard cell with markdown emphasis, entities and dash spellings normalised away.

    ⚠️ THE OLD CODE DID `cells[0].strip("* ")`, which strips only the ENDS — a cell like
    `**gap** (see below)` kept its inner `**`, and `**—**` normalised to `—`, an em dash the
    matcher below did not list. Everything the matcher sees goes through here first, so the
    matcher only ever has to know one spelling of each word.
    """
    c = cell.replace("&mdash;", "-").replace("&ndash;", "-").replace("&#8212;", "-")
    c = re.sub(r"[*_`]", "", c)                       # markdown emphasis and code ticks
    for d in _DASHES:
        c = c.replace(d, "-")
    c = re.sub(r"-{2,}", "-", c)                      # `--`, `---`
    c = re.sub(r"\[\^?[\w\d]+\]", " ", c)             # footnote / link references
    c = re.sub(r"[()\[\]]", " ", c)                   # so "— (docs only)" reads as "- docs only"
    c = " ".join(c.split())                           # collapses "prose  only" too
    return c.strip(" .,;:!?")


def _strip_emphasis(cell):
    """Leading/trailing `**` only — for header and subject cells, where inner text is content."""
    return re.sub(r"^\**|\**$", "", cell.strip()).strip()


# Cells that assert we ship nothing, matched against `_plain(...)` of the "Ours" cell only.
# Deliberately generous: a false negative here is a scorecard row that lies unguarded.
_NOTHING = (r"(?:-|none(?:\s+yet)?|nil|nothing|n/?a|tbd|todo|planned|unimplemented"
            r"|not\s+implemented|not\s+built|absent|missing|gap)")
_ONLY = r"(?:(?:prose|docs?|documentation|text|paper|design|pseudocode)[\s-]*only)"
_CLAIMS_NOTHING = re.compile(
    r"^\s*%s?\s*%s?\s*%s?\s*$" % (_NOTHING, _ONLY, _NOTHING), re.I)

_SCORECARD_HEADING = "## Part 2 — Per-process simulation scorecard"


def _simaudit_rows():
    """(subject, ours_cell) for every DATA row of the Part 2 scorecard, and nothing else.

    ⚠️ THE OLD PARSE READ EVERY `|` LINE IN THE FILE. SIMULATION-AUDIT.md has three tables
    (Part 1 representation tiers, Part 2 the scorecard, Part 3 the metric vector) and only one
    of them has an "Ours" column, so `cells[1]` meant "Represents" in Part 1 and "Real-Earth
    target" in Part 3. It also parsed header rows as data. A false PASS was reachable in one
    edit: delete the karst scorecard row and write `| Karst caves | see Part 5 |` anywhere else
    in the document — the mapping-staleness row would still find a "row", and the "Ours" cell it
    checked would be prose from another table.

    So: bound the parse to the Part 2 section, take the first table in it, find the "Ours"
    column BY ITS HEADER, and fail loudly if no header cell is literally `Ours` — which is what
    a column reorder or a rename looks like, and is exactly what the staleness row was for.
    """
    start = SIMAUDIT_RAW.index(_SCORECARD_HEADING) + len(_SCORECARD_HEADING)
    section = SIMAUDIT_RAW[start:]
    nxt = section.find("\n## ")
    if nxt >= 0:
        section = section[:nxt]

    rows, ours_col, in_table = [], None, False
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if in_table:
                break                       # the table ended; ignore anything after it
            continue
        in_table = True
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue                        # `|---|---|` separator
        if ours_col is None:                # the header row, consumed not emitted
            headers = [_strip_emphasis(c) for c in cells]
            assert "Ours" in headers, (
                "SIMULATION-AUDIT.md's Part 2 scorecard has no column headed exactly 'Ours' "
                "(headers: %s). Either the table was reorganised or this parser is stale; "
                "both need a human, and guessing a column index is how the guard goes quiet."
                % headers)
            ours_col = headers.index("Ours")
            continue
        if len(cells) <= ours_col:
            continue
        rows.append((_strip_emphasis(cells[0]), cells[ours_col]))
    assert ours_col is not None, (
        "SIMULATION-AUDIT.md's Part 2 section contains no markdown table; the scorecard guard "
        "below would silently pass on an empty parse.")
    return rows


def _ours_cells(subject):
    matching = [ours for subj, ours in _simaudit_rows() if subj == subject]
    assert matching, (
        "SIMULATION-AUDIT.md's Part 2 scorecard no longer has a row for %r — either the "
        "scorecard changed or this mapping is stale. Both need a human." % subject)
    return matching


@pytest.mark.parametrize("subject", sorted(SIMAUDIT_OURS))
def test_the_ours_cell_names_the_callable_that_ships(subject):
    """⚠️ THE PRIMARY GUARD: an "Ours" cell must NAME the callable it is describing.

    This is the row that would have caught the lava scorecard on the day `lava_flow` landed,
    the karst row on the day `karst_sinkholes` did, and — unlike the "says nothing" matcher it
    replaces — the hydraulic row, whose cell was not empty at all but confidently named the
    wrong model while `erosion_pipe.pipe_erode` sat two rows below it.

    Asserting the literal attribute name is what makes this robust: `ejecta CA only`,
    `Lagrangian droplet (Beyer/Lague)`, `**—**`, `&mdash;`, `docs only` and every other
    spelling of "we have nothing" fail it identically, and there is no pattern to maintain.
    """
    module_name, attr = SIMAUDIT_OURS[subject]
    if not _exists(module_name, attr):
        pytest.skip("%s.%s does not exist, so the row's claim is honest" % (module_name, attr))
    for ours in _ours_cells(subject):
        assert attr in ours, (
            "SIMULATION-AUDIT.md's %r row describes what we ship as %r, which does not name "
            "%s.%s — a callable that exists, is tested, and is what the row is about. A reader "
            "planning work off this scorecard would rebuild it. Name the callable in the Ours "
            "cell; leave the Verdict cell to a human, since a gap can be honest while something "
            "adjacent exists." % (subject, ours, module_name, attr))


@pytest.mark.parametrize("subject", sorted(SIMAUDIT_OURS))
def test_simulation_audit_does_not_claim_we_ship_nothing_when_we_do(subject):
    """Belt-and-braces behind the row above: the cell must not read as "we have nothing".

    Kept because it fails with a different, blunter message, and because it still fires if a
    future edit drops the attribute name into an otherwise-empty cell (`— (`pipe_erode`)`).
    Matched against `_plain(...)`, so dash spellings and emphasis cannot smuggle a claim past.
    """
    module_name, attr = SIMAUDIT_OURS[subject]
    if not _exists(module_name, attr):
        pytest.skip("%s.%s does not exist, so the row's claim is honest" % (module_name, attr))
    for ours in _ours_cells(subject):
        assert not _CLAIMS_NOTHING.match(_plain(ours)), (
            "SIMULATION-AUDIT.md's %r row says we ship %r, but %s.%s exists and is callable. "
            "Describe what ships." % (subject, ours, module_name, attr))


# Every spelling of "we ship nothing" that the FIRST version of `_CLAIMS_NOTHING` let through.
# Fixture strings, not the corpus: this pins the matcher itself, so narrowing it fails here
# rather than months later on a real row.
_ESCAPES_THAT_MUST_BE_CAUGHT = [
    "—", "-", "–", "‒", "―", "−", "--", "---",
    "**—**", "*—*", "`—`", "**--**", "&mdash;", "&ndash;",
    "—.", "— ", " — ", "—[^1]",
    "prose only", "prose  only", "(prose only)", "**(prose only)**",
    "docs only", "doc only", "text only", "documentation only", "pseudocode only",
    "— (prose only)", "**—** (text only)", "&mdash; (docs only)",
    "not implemented", "Not Implemented", "none yet", "none", "nothing", "nil",
    "n/a", "N/A", "na", "planned", "TBD", "todo", "unimplemented", "missing", "absent",
    "",
]


@pytest.mark.parametrize("cell", _ESCAPES_THAT_MUST_BE_CAUGHT)
def test_the_claims_nothing_matcher_catches_every_known_escape(cell):
    """The negative half of the belt-and-braces matcher, against fixtures rather than the file."""
    assert _CLAIMS_NOTHING.match(_plain(cell)), (
        "%r reads as 'we ship nothing' but the matcher does not catch it; a scorecard row "
        "spelled that way would go unguarded" % cell)


@pytest.mark.parametrize("cell", [
    "`sims_illustrative.lava_flow` — thermo-rheological CA",
    "**now: `erosion_pipe.pipe_erode`** (Mei-2007 coupled flow+sediment, conserved)",
    "surface karst only — `landforms.karst_sinkholes`",
    "D8 + MFD + priority-flood",
    "ejecta CA only",                      # false, but it is a CLAIM — the row above catches it
])
def test_the_claims_nothing_matcher_does_not_swallow_a_real_claim(cell):
    """The other half: a cell that describes something must never read as empty."""
    assert not _CLAIMS_NOTHING.match(_plain(cell)), (
        "%r describes something we ship, but the matcher reads it as an empty cell; the "
        "belt-and-braces row would then fire on an honest row" % cell)


def test_the_simulation_audit_mapping_is_not_stale():
    """Every mapped subject must still name a row in the Part 2 scorecard.

    Without this the dict quietly rots into a set of no-ops the moment the table is
    reorganised — the same way `CLAIMABLE`'s "spectral band" needle sat dead for months.
    Bounded to the scorecard, so a `| Karst caves | ... |` line in some other table cannot
    stand in for the row that was deleted.
    """
    subjects = {subj for subj, _ours in _simaudit_rows()}
    missing = sorted(set(SIMAUDIT_OURS) - subjects)
    assert not missing, (
        "these SIMAUDIT_OURS keys name no row in SIMULATION-AUDIT.md's Part 2 scorecard: %s"
        % missing)
