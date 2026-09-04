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
# SIMULATION-AUDIT.md — the "Ours" column, which is where this document lied five times
#
# ⚠️ THIS FILE GUARDED THE WRONG DOCUMENT FOR MONTHS. `CLAIMABLE` above covers only
# NODE-PARITY-AUDIT.md, so SIMULATION-AUDIT.md's scorecard was unguarded, and five of
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
#   Flow routing — said "D8 + MFD + priority-flood", omitting `flow.hybrid_accumulation`:
#                the one-pass MFD-on-hillslope / D8-once-channelised router that `03`
#                actually recommends, that `flow_anatomy` panel c is built on, and that the
#                node graph exposes. Found by a harsh-critic pass AFTER the four above had
#                been fixed and this guard written — because the row was never MAPPED, and
#                an unmapped row is a row this file does not look at. See the mapping note.
#
# All five are the SAME failure and it is the expensive one: a reader planning work off
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
# So the primary row asserts the literal attribute name appears in the cell, and it fails on
# all five historical defects. `_CLAIMS_NOTHING` is kept behind it as belt-and-braces —
# widened, and matched against a NORMALISED cell — with the escape table pinned below as a
# parametrised negative test, so a future narrowing of the matcher fails immediately.
#
# ⚠️ BUT NAMING THE CALLABLE IS NECESSARY, NOT SUFFICIENT, AND THIS COMMENT USED TO CLAIM
# OTHERWISE ("there is no pattern to maintain"). A cell can name the callable IN ORDER TO
# DENY IT, and every such cell satisfied both guards: `` `lava_flow` is not implemented ``,
# `` no `lava_flow` yet ``, `` TODO: write `lava_flow` ``, `` gap; `lava_flow` would go here ``
# and four more are pinned in `_DENIALS_THAT_NAME_THE_CALLABLE` below. `_CLAIMS_NOTHING`
# cannot help: it is anchored `^...$`, so it only fires on a cell that is ENTIRELY a
# nothing-phrase, and none of these are. The negation patterns are exactly what the
# "no pattern to maintain" claim failed to see — so there IS one now, `_NEGATION`, and it is
# far smaller than the `_NOTHING`/`_ONLY` pair.
#
# ⚠️ AND IT IS SCOPED PER CLAUSE, NOT PER CELL, BECAUSE HONEST ROWS NEGATE THINGS. A blanket
# "no negation word anywhere in the cell" would fail the karst row, whose
# "**surface karst only** … **no subsurface conduits**" is the most precise cell in the
# document, and the coastal row's "what is absent is the rate law". The distinction is which
# clause the negation sits in: a row is dishonest when the negation binds to the CALLABLE, and
# honest when it binds to something else the row is careful to exclude. So the cell is split
# into clauses and only the clause NAMING the attribute is searched.
#
# ⚠️ AND HERE IS WHAT THAT DELIBERATELY CANNOT CATCH, SO NOBODY READS MORE INTO IT THAN IT
# DOES. A denial moved into a NEIGHBOURING clause is indistinguishable, by shape alone, from
# karst's honest qualifier: `` `lava_flow` — never finished `` and `` gap; `lava_flow` goes
# here `` both pass, and so they must, because `` `landforms.karst_sinkholes` … ; **no
# subsurface conduits** `` is the same construction with the negation about a different noun.
# Which noun a negation is about is a judgement, and judgement stays with the reader here as
# it does in the Verdict column. What the guard buys is the eight cells pinned below — every
# one of which denies the callable INSIDE the clause that names it, and every one of which
# passed both of the older guards.
#
# ⚠️ AND THE VERDICT IS STILL LEFT TO A HUMAN. A **gap** verdict can be perfectly honest
# while something adjacent ships — karst is exactly that case: the surface expression exists,
# the 3-D conduit network genuinely does not, and forcing that row to stop saying "gap" would
# replace one false statement with another. The inventory is mechanical; the judgement is not.
#
# ⚠️ AN UNMAPPED ROW IS AN UNGUARDED ROW, AND THAT IS HOW THE FIFTH DEFECT SURVIVED. The
# first version of this dict held only the four rows that had already been caught being
# wrong, which made the guard a record of past corrections rather than a check on the
# scorecard. "Flow routing / hydrology" was never in it, so nothing noticed that it omitted
# `flow.hybrid_accumulation`. EVERY row of the Part 2 scorecard is now mapped, and
# `test_every_scorecard_row_is_mapped` fails if a new row is added without one — a row this
# file does not look at is a row that can say anything.
#
# The mapping names ONE callable per row, the one the row is principally about; where a row
# covers several (tectonics, flow routing) the cell names them all and the mapped one is the
# anchor. If a row ever genuinely ships nothing, the guard already handles it: `_exists`
# returns False and the row SKIPS, so the honest "—" stays legal and only becomes a failure
# on the day the callable lands. That is the property that makes mapping every row safe.

SIMAUDIT_OURS = {
    # row subject                      -> (module, attribute) the "Ours" cell must NAME
    "Lava flow": ("sims_illustrative", "lava_flow"),
    "Karst caves": ("landforms", "karst_sinkholes"),
    "Hydraulic (detail/interactive)": ("erosion_pipe", "pipe_erode"),
    "Coastal": ("sims_illustrative", "coastal_retreat"),
    "Sediment / deposition": ("erosion_pipe", "pipe_erode"),
    "Aeolian (dunes + abrasion)": ("aeolian", "yardang"),
    "Glacial": ("glacier", "glacier_carve"),
    "Flow routing / hydrology": ("flow", "hybrid_accumulation"),
    "Fluvial (large-scale)": ("erosion_streampower", "stream_power_evolve"),
    "Thermal / hillslope": ("erosion_thermal", "thermal_erosion"),
    "Tectonic / orogeny": ("tectonics", "plate_uplift"),
    "Debris runout": ("runout", "voellmy_runout"),
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


# Words that turn a MENTION of a callable into a DENIAL of it. Kept deliberately short: this is
# the whole "pattern to maintain" that the primary guard's docstring used to claim it had none of.
_NEGATION = re.compile(
    r"\b(?:not|no|none|never|planned|todo|backlog|would|yet|unlike|absent|missing|gap)\b", re.I)

# Clause boundaries. A negation binds to the clause it sits in, so this is what makes
# "**no subsurface conduits**" legal in a cell that also names `karst_sinkholes`. `\s-\s` is a
# hyphen used as a dash; a hyphen inside a word (`wave-cut`, `thermo-rheological`) is not a break.
_CLAUSE_SPLIT = re.compile(r"[;,()\[\]%s]|--+|\.\s|\s-\s" % _DASHES)


def _clauses(cell):
    """The cell split into clauses, with markdown emphasis and code ticks removed.

    ⚠️ THIS MUST NOT STRIP `_`, and `_plain` above does. The thing being searched for here is a
    PYTHON IDENTIFIER, and `re.sub(r"[*_`]", "", cell)` rewrites `lava_flow` as `lavaflow`, which
    no attribute name can ever match — so every check built on it passes unconditionally. That is
    not hypothetical: the first draft of this helper reused that character class and all eight
    pinned denials below came back clean, which is the failure mode this whole file exists to
    stop. `test_a_cell_that_names_the_callable_to_deny_it_is_rejected` is what caught it, and
    its `assert "lava_flow" in cell` line is there so a fixture can never go vacuous the same way.
    """
    return [p for p in _CLAUSE_SPLIT.split(re.sub(r"[*`]", "", cell)) if p.strip()]


def _denial_naming(attr, cell):
    """`(token, clause)` if the cell names `attr` only to DENY it, else `None`.

    Scoped per clause on purpose — see the block comment above. The question is never "does this
    cell contain the word 'no'", it is "does the clause that names the callable deny it".
    """
    for clause in _clauses(cell):
        if attr in clause:
            hit = _NEGATION.search(clause)
            if hit:
                return hit.group(0), clause.strip()
    return None


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

    Asserting the literal attribute name is what makes the first half robust: `ejecta CA only`,
    `Lagrangian droplet (Beyer/Lague)`, `**—**`, `&mdash;`, `docs only` and every other spelling
    of "we have nothing" fail it identically.

    ⚠️ AND IT IS ONLY HALF. `attr in ours` is necessary, not sufficient: a cell can name the
    callable IN ORDER TO DENY IT, and `` `lava_flow` is not implemented `` satisfies this row and
    the belt-and-braces row below it while denying shipped code. So the cell must ALSO not negate
    the callable in the clause that names it — scoped per clause, because the karst row's
    "**no subsurface conduits**" and the coastal row's "what is absent is the rate law" are
    precise, honest statements that a cell-wide negation test would destroy.
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
        denial = _denial_naming(attr, ours)
        assert denial is None, (
            "SIMULATION-AUDIT.md's %r row names %s.%s and then denies it: %r in the clause %r. "
            "That callable exists and is callable. Naming a thing in order to say we do not have "
            "it is the same drift as omitting it, and costs a reader the same rebuilt module. If "
            "the negation is about something genuinely absent, put it in its OWN clause (the "
            "karst row's '**no subsurface conduits**' is the model); if it is about the callable, "
            "it is wrong." % (subject, module_name, attr, denial[0], denial[1]))


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


# Cells that NAME the callable and satisfy `attr in ours` — and deny it in the same breath.
# All eight passed both guards before `_denial_naming` existed. The sixth is the pre-fix lava
# cell plus four words, which is how small the edit is that turns a caught defect loose again.
_DENIALS_THAT_NAME_THE_CALLABLE = [
    "`lava_flow` is not implemented",
    "unlike `lava_flow`, we have none",
    "— (see `lava_flow` in the backlog)",
    "no `lava_flow` yet",
    "gap; `lava_flow` would go here",
    "ejecta CA only (`lava_flow` is planned)",
    "TODO: write `lava_flow`",
    "prose only — `lava_flow` not built",
]


@pytest.mark.parametrize("cell", _DENIALS_THAT_NAME_THE_CALLABLE)
def test_a_cell_that_names_the_callable_to_deny_it_is_rejected(cell):
    """The positive control for `_denial_naming`: every one of these must be caught.

    Fixtures rather than the live document, deliberately — this pins the MATCHER, so narrowing
    `_NEGATION` or `_CLAUSE_SPLIT` fails here immediately instead of months later on a real row,
    which is the failure mode that produced this file in the first place.
    """
    assert "lava_flow" in cell, "fixture is broken: it must satisfy the `attr in ours` half"
    assert _denial_naming("lava_flow", cell) is not None, (
        "%r names `lava_flow` only to deny it, but the guard reads it as an honest claim; a "
        "scorecard row spelled that way would deny shipped code unguarded" % cell)


# The other side of the same line: honest rows that negate something OTHER than the callable.
# The karst shape is the one that matters — it is the most precise cell in the document, and a
# cell-wide (rather than clause-scoped) negation test would reject it.
_SCOPED_QUALIFIERS_THAT_MUST_PASS = [
    ("karst_sinkholes",
     "**surface karst only** — `landforms.karst_sinkholes` (dolines on soluble rock, returning "
     "the `sink_mask` of pits `03` must *not* fill); **no subsurface conduits**"),
    ("coastal_retreat",
     "**the full loop ships** — `sims_illustrative.coastal_retreat` iterates notch → collapse → "
     "retreat. **What is absent is the rate law**"),
    ("hybrid_accumulation",
     "`flow.hybrid_accumulation` — MFD on the hillslope, D8 once a cell channelises; "
     "D-infinity is deliberately not reimplemented"),
    ("pipe_erode",
     "**now: `erosion_pipe.pipe_erode`** (Mei-2007, conserved); SPL still has no "
     "transport-limited closure"),
]


@pytest.mark.parametrize("attr,cell", _SCOPED_QUALIFIERS_THAT_MUST_PASS,
                         ids=[a for a, _c in _SCOPED_QUALIFIERS_THAT_MUST_PASS])
def test_a_scoped_qualifier_beside_a_named_callable_still_passes(attr, cell):
    """The negative control: a negation in a DIFFERENT clause is a row being careful, not lying."""
    assert attr in cell, "fixture is broken: it must name the callable"
    assert _denial_naming(attr, cell) is None, (
        "%r names %s and qualifies something else, but the guard reads it as a denial: %r. "
        "Precision is what these cells are for; a guard that punishes it teaches writers to "
        "delete the qualifier." % (cell, attr, _denial_naming(attr, cell)))


def test_every_scorecard_row_is_mapped():
    """An unmapped row is an unguarded row — and that is how the flow-routing defect survived.

    The four rows this file was written for were all mapped; "Flow routing / hydrology" was not,
    so its "D8 + MFD + priority-flood" cell could omit `flow.hybrid_accumulation` indefinitely
    with the suite green. Mapping every row is what turns this file from a record of past
    corrections into a check on the scorecard, and this row is what keeps it that way when
    somebody adds a process.

    A row that genuinely ships nothing is fine here: `_exists` fails and the guards SKIP, so an
    honest "—" stays legal until the callable lands.
    """
    unmapped = sorted({subj for subj, _ours in _simaudit_rows()} - set(SIMAUDIT_OURS))
    assert not unmapped, (
        "these SIMULATION-AUDIT.md Part 2 scorecard rows have no SIMAUDIT_OURS entry, so nothing "
        "checks what they claim we ship: %s. Add `subject: (module, attr)` naming the callable "
        "the row is principally about — if none ships yet, map the one that WOULD and the guard "
        "will skip until it does." % unmapped)


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


# --------------------------------------------------------------------------------------
# NUMERIC CLAIMS — the family this file could not see, over a domain taken from disk
#
# ⚠️ WHAT WAS BROKEN. Everything above reads FOUR documents, named as literals at the top of the
# file: NODE-PARITY-AUDIT.md, VALIDATION.md, SIMULATION-AUDIT.md and README.md. `reference-impl/`
# holds ELEVEN. Seven were outside this file: ARCHETYPES, ATOM-COVERAGE, CANON-COMPARISON,
# GALLERY, GROUNDING, HYPERREALISM and REVIEW-BRIEF. (ATOM-COVERAGE has its own harness in
# `tests/test_atom_coverage.py`; the other six had nothing.) A hand-written list is a domain that
# does not grow when the directory does — which is the same defect, one level up, as a guard keyed
# on a literal string.
#
# ⚠️ AND WITHIN THE FOUR, ONLY ONE NUMBER WAS EVER CHECKED.
# `test_validation_ledger_quotes_the_real_test_count` matches `"(\d+) tests pass"` — one sentence,
# in one document. Measured, on this
# tree: rewriting `VALIDATION.md:31`'s "**530** is the number of `def test` **functions**" to
# **9999** left `tests/test_audit_drift.py` at **94 passed**. The same figure appears one screen
# up inside the quoted phrase, so the ONE guarded spelling still said 530 and the row stayed
# green while the document contradicted itself eight lines apart. A number that only one of its
# two spellings is checked on is not guarded; it is lucky.
#
# WHAT THIS ADDS. The document set is `REF.glob("*.md")` — derived, not written — with its
# denominator asserted below so it cannot go stale in silence. Over that set, two mechanical
# families of numeric claim:
#
#   * COUNT CLAIMS, where a sentence quotes a quantity this repo can recount from disk. Each
#     pattern names both the quantity it binds to and its own tolerance. The suite-size figures
#     keep the original row's 10 % band, because they are rhetorical scale claims made in service
#     of an argument, and a test that fails on ±1 teaches people to delete the number rather than
#     requote it. "44 `.py` files on disk" gets 0 %: it is a count, not a scale.
#   * SUM IDENTITIES, where a document states its own arithmetic — `19 + 12 + 13 = the 44 files on
#     disk`, `183 nodes / 9 families (Primitive 23, Terrain 14, …)`. These need no oracle at all:
#     the claim carries its own check, and corrupting either side breaks it.
#
# WHAT IT DELIBERATELY DOES NOT DO. It does not try to check every numeral. Most numbers in these
# documents are citations, measured constants, or figures attributed to a named past commit, and a
# guard that guessed at those would fail on true statements — which is how a guard gets edited
# away. The claim is only that the numbers a document asserts about THIS tree, in a shape that
# names what they count, are recomputed; `registers/numeric-claims.tsv` is where the rest is
# enumerated and none of it is claimed as guarded here.
# --------------------------------------------------------------------------------------

AUDIT_DOCUMENTS = tuple(sorted(REF.glob("*.md")))

# The denominator, asserted in-file so that adding a twelfth audit document is a decision. The
# names are pinned too: a count alone is satisfied by a swap.
AUDIT_DOCUMENT_COUNT = 11
AUDIT_DOCUMENT_NAMES = frozenset({
    "ARCHETYPES.md", "ATOM-COVERAGE.md", "CANON-COMPARISON.md", "GALLERY.md", "GROUNDING.md",
    "HYPERREALISM.md", "NODE-PARITY-AUDIT.md", "README.md", "REVIEW-BRIEF.md",
    "SIMULATION-AUDIT.md", "VALIDATION.md",
})


def _normalised(document):
    """Whitespace-flattened, with markdown emphasis and code ticks removed.

    Flattened for the reason `_flat` gives — these are hard-wrapped documents and every claim
    below spans a wrap somewhere. Emphasis stripped because `**530**` and `530` are the same
    claim, and a matcher that has to know both spellings will be defeated by the third.
    """
    return re.sub(r"[*`]", "", _flat(document.read_text(encoding="utf-8")))


# ---- the oracles: quantities this repo can recount from disk ----------------------------

def _count_test_functions():
    return sum(
        len(re.findall(r"^def test", p.read_text(encoding="utf-8"), re.M))
        for p in sorted((REF / "tests").glob("test_*.py"))
    )


def _count_reference_impl_py_files():
    return len(list(REF.glob("*.py")))


RECOUNTABLE = {
    "test functions": _count_test_functions,
    "reference-impl .py files": _count_reference_impl_py_files,
}

# (pattern name, regex with ONE numeric group, quantity, tolerance as a fraction, why that band)
#
# Applied to every one of the eleven documents, not to a named few. The tolerance is 10 % on the
# suite-size figures, matching the row this generalises: they are scale claims made in service of
# an argument about rigour, and requiring exactness would make an honest paragraph fail on the day
# somebody adds a test. It is 0 on "files on disk", which is a count, not a scale.
COUNT_CLAIM_PATTERNS = (
    ("suite-size-quoted", r'"(\d+) tests pass"', "test functions", 0.10,
     "a rhetorical scale figure; the original row's band, kept"),
    ("suite-size-parenthetical", r"suite \((\d+) tests?\) pass(?:es)?", "test functions", 0.10,
     "same claim, written as an aside instead of a quotation"),
    ("def-test-function-count", r"(\d+) is the number of def test functions",
     "test functions", 0.10,
     "the document names the exact quantity it is quoting, so it binds to the same oracle"),
    ("py-files-on-disk", r"(\d+) \.py files on disk", "reference-impl .py files", 0.0,
     "a count of files, with no rhetorical latitude: it is either right or wrong"),
)


def _count_claims(document):
    """(pattern, quantity, quoted, tolerance) for every count claim a document makes."""
    text = _normalised(document)
    found = []
    for name, pattern, quantity, tolerance, _why in COUNT_CLAIM_PATTERNS:
        for match in re.finditer(pattern, text):
            found.append((name, quantity, int(match.group(1)), tolerance))
    return found


# ---- the oracles a document carries with it: its own arithmetic --------------------------

# `19 imported + 12 undrawn operators + 13 scripts = the 44 files on disk`, and `1231 + 6 = 1237`.
# Words are allowed between a term and the `+` because these are sentences, not expressions.
_ADDITION = re.compile(
    r"(?<![\w.])(\d+)"
    r"((?:\s+[A-Za-z][\w./-]*){0,4}"
    r"(?:\s*\+\s*\d+(?:\s+[A-Za-z][\w./-]*){0,4})+)"
    r"\s*=\s*(?:the\s+)?(\d+)")

# `183 nodes / 9 families (Primitive 23, Terrain 14, …)` — an inventory that states its own total
# and its own group count, then lists the groups.
_INVENTORY = re.compile(
    r"(?<![\w.])(~?)(\d+)\s+([A-Za-z][\w]*)\s*/\s*(\d+)\s+([A-Za-z][\w]*)\s*\(([^()]*)\)")


def _sum_identities(document):
    """(kind, description, claimed, actual) for every self-checking arithmetic claim."""
    text = _normalised(document)
    identities = []
    for match in _ADDITION.finditer(text):
        terms = [int(n) for n in re.findall(r"\d+", match.group(1) + match.group(2))]
        identities.append(("addition", match.group(0), int(match.group(3)), sum(terms)))
    for match in _INVENTORY.finditer(text):
        approx, total, _noun, groups, _gnoun, body = match.groups()
        items = [part.strip() for part in body.split(",") if part.strip()]
        identities.append(("group count", match.group(0), int(groups), len(items)))
        numbers = [int(n) for n in re.findall(r"(?<![\w.])\d+", body)]
        # An approximate total (`~90`) states no exact identity, and a list with no numbers in it
        # is a list of names — neither carries a sum to check.
        if numbers and not approx:
            identities.append(("inventory total", match.group(0), int(total), sum(numbers)))
    return identities


# ---- the guards --------------------------------------------------------------------------

def test_the_audit_document_domain_is_derived_from_disk_and_declares_its_denominator():
    """The domain is `glob`, and the denominator is written down so it cannot rot in silence.

    Both halves matter. Deriving from disk is what stops a twelfth document joining the directory
    unguarded; declaring the count and the names is what stops the derivation quietly returning
    fewer documents than the file believes it is reading — a glob that matches nothing passes
    every loop built on it.
    """
    names = {p.name for p in AUDIT_DOCUMENTS}
    assert len(AUDIT_DOCUMENTS) == AUDIT_DOCUMENT_COUNT, (
        "reference-impl/ holds %d markdown documents, not the %d this guard declares. Adding an "
        "audit document is a decision: raise AUDIT_DOCUMENT_COUNT and add it to "
        "AUDIT_DOCUMENT_NAMES, having checked what in it is claimable."
        % (len(AUDIT_DOCUMENTS), AUDIT_DOCUMENT_COUNT))
    assert names == AUDIT_DOCUMENT_NAMES, (
        "the audit document set has changed: on disk but not declared %s; declared but not on "
        "disk %s" % (sorted(names - AUDIT_DOCUMENT_NAMES), sorted(AUDIT_DOCUMENT_NAMES - names)))


def test_every_audit_document_is_read_by_this_guard():
    """Coverage, measured rather than asserted: all eleven are opened, not five.

    `registers/guard-domains.tsv` records this file at 5 of 11 (45.5 %). This row is the thing
    that makes the number self-correcting — it re-derives the read set by actually running the
    scan, so the coverage claim can never be a comment that drifted.
    """
    # "read" here means exactly what the scan does: `_normalised` is the read step every claim
    # extractor goes through, and it is applied to each document by the parametrised rows below.
    # A document that yields no text yields no claims, which is indistinguishable from not being
    # in the domain — so an unreadable document must fail here rather than pass quietly.
    read = {d.name for d in AUDIT_DOCUMENTS if _normalised(d)}
    assert read == AUDIT_DOCUMENT_NAMES, (
        "these audit documents are in the domain but are not read: %s"
        % sorted(AUDIT_DOCUMENT_NAMES - read))


def test_a_document_that_names_this_guard_as_its_verifier_is_actually_read():
    """An OKF header that claims a verifier the verifier does not read is a false provenance line.

    ⚠️ THIS IS HOW THE GAP WAS FOUND. `REVIEW-BRIEF.md` carries
    `verified: { by: process:test_audit_drift.py, at: 2026-08-24T11:51:35Z }` in its frontmatter,
    and this file had never opened it. A reader checking whether a document is guarded reads that
    header; it was a claim about a check that did not exist.
    """
    lying = []
    for document in AUDIT_DOCUMENTS:
        header = re.search(r"^verified:\s*\{\s*by:\s*process:([^,\s}]+)",
                           document.read_text(encoding="utf-8"), re.M)
        if not header or header.group(1) != "test_audit_drift.py":
            continue
        # Being READ is necessary and not sufficient: opening a file and checking nothing in it
        # is the shape of every guard in `registers/guard-domains.tsv` that this wave exists to
        # correct. So the bar is that the document yields at least one claim this file actually
        # re-derives — a recountable figure or a stated identity.
        if not _count_claims(document) and not _sum_identities(document):
            lying.append(document.name)
    assert not lying, (
        "these documents name test_audit_drift.py as their verifier, but this file re-derives no "
        "claim in them — the provenance line promises a check that does not happen: %s. Either "
        "the document lost the claim that was being checked (restore or requote it), or the "
        "header should not name this process." % lying)


@pytest.mark.parametrize("document", AUDIT_DOCUMENTS, ids=[d.name for d in AUDIT_DOCUMENTS])
def test_every_recountable_claim_matches_the_tree(document):
    """A number a document quotes about THIS tree must survive being recounted from it."""
    wrong = []
    for name, quantity, quoted, tolerance in _count_claims(document):
        actual = RECOUNTABLE[quantity]()
        if abs(quoted - actual) > tolerance * actual:
            wrong.append(
                "%s: quotes %d %s (pattern %r); this tree has %d — %.1f %% off, band is %.0f %%"
                % (document.name, quoted, quantity, name, actual,
                   100.0 * abs(quoted - actual) / actual, 100.0 * tolerance))
    assert not wrong, (
        "stale numeric claims:\n  " + "\n  ".join(wrong)
        + "\nRequote the figure against a measured run, or drop the number.")


@pytest.mark.parametrize("document", AUDIT_DOCUMENTS, ids=[d.name for d in AUDIT_DOCUMENTS])
def test_every_stated_sum_identity_holds(document):
    """Arithmetic a document states about itself must close. No oracle needed; it brought one."""
    broken = []
    for kind, description, claimed, actual in _sum_identities(document):
        if claimed != actual:
            broken.append("%s: %s — states %d as the %s, but the parts give %d"
                          % (document.name, description, claimed, kind, actual))
    assert not broken, "arithmetic that does not close:\n  " + "\n  ".join(broken)


def test_the_numeric_claim_scan_is_not_vacuous():
    """A scan that matches nothing passes forever, which is the defect this whole file is about.

    Two floors and one per-pattern liveness check. The per-pattern half is the important one: a
    reworded sentence that no longer matches its pattern must FAIL here, loudly, rather than
    quietly removing a number from the guarded set — which is exactly what "keyed on a literal
    heading" did to the scorecard rows before `690fba1`.
    """
    # Per-pattern liveness first, because it is the diagnostic that names WHICH claim went quiet;
    # the aggregate floors below only say that something did.
    dead = []
    for name, pattern, _quantity, _tolerance, _why in COUNT_CLAIM_PATTERNS:
        if not any(re.search(pattern, _normalised(d)) for d in AUDIT_DOCUMENTS):
            dead.append(name)
    assert not dead, (
        "these count-claim patterns match nothing in the corpus, so whatever they were guarding "
        "is now unguarded: %s. Either the sentence was reworded (re-key the pattern) or the claim "
        "was deleted (delete the pattern deliberately)." % dead)

    claims = [c for d in AUDIT_DOCUMENTS for c in _count_claims(d)]
    identities = [i for d in AUDIT_DOCUMENTS for i in _sum_identities(d)]
    assert len(claims) >= 5, "only %d recountable claims matched" % len(claims)
    assert len(identities) >= 7, "only %d sum identities matched" % len(identities)

    documents_with_claims = {d.name for d in AUDIT_DOCUMENTS if _count_claims(d)}
    assert len(documents_with_claims) >= 4, (
        "recountable claims were found in only %d documents (%s); the scan has narrowed"
        % (len(documents_with_claims), sorted(documents_with_claims)))


@pytest.mark.parametrize("text,expected", [
    # the shapes that are real in this corpus
    ("19 imported + 12 undrawn operators + 13 scripts = the 44 files on disk", [("addition", 44, 44)]),
    ("And 1231 + 6 = 1237, not 1236", [("addition", 1237, 1237)]),
    # the corruption: one term edited, the total left alone
    ("19 imported + 12 undrawn operators + 9 scripts = the 44 files on disk", [("addition", 44, 40)]),
    # an inventory states two things and both are checked
    ("183 nodes / 9 families (Primitive 23, Terrain 14, Modify 146)",
     [("group count", 9, 3), ("inventory total", 183, 183)]),
    # an approximate total states no identity, and a list of names carries no sum
    ("~90 Devices / 9 categories (a, b, c, d, e, f, g, h, i)", [("group count", 9, 9)]),
    # prose that merely contains numerals is not an identity
    ("the suite had grown to 530 / 1236 by then", []),
])
def test_sum_identity_recogniser_fixtures(text, expected, tmp_path):
    """Fixtures, not the corpus: this pins the RECOGNISER so narrowing it fails here first."""
    document = tmp_path / "fixture.md"
    document.write_text(text, encoding="utf-8")
    assert [(kind, claimed, actual)
            for kind, _d, claimed, actual in _sum_identities(document)] == expected


@pytest.mark.parametrize("text,expected", [
    ('So "530 tests pass" is self-consistency.', [("suite-size-quoted", 530)]),
    ("The whole suite (334 tests) passes; the core is cross-validated",
     [("suite-size-parenthetical", 334)]),
    ("**530** is the number of `def test` **functions** across `tests/`",
     [("def-test-function-count", 530)]),
    ("against **44 `.py` files on disk** — 25 of which", [("py-files-on-disk", 44)]),
    # ⚠️ the negative controls. Every one of these quotes a count of an OLDER tree and says so;
    # a matcher that bound them to today's oracle would fail on true sentences, which is how a
    # guard gets deleted. They are outside the patterns by shape, not by an exclusion list.
    ('That figure said 117 for a long time, against a suite that had already grown past 400', []),
    ('it previously quoted "436 `def test` functions" and a run of "617 passed, 6 skipped"', []),
    ("`27f6cf7`, whose suite defined **463** functions and collected **713**", []),
    ("its 10 tests are removed from *collection* entirely", []),
    ("nothing deselects 90 tests", []),
])
def test_count_claim_recogniser_fixtures(text, expected, tmp_path):
    """The other half: what must match, and what must not."""
    document = tmp_path / "fixture.md"
    document.write_text(text, encoding="utf-8")
    assert [(name, quoted) for name, _q, quoted, _t in _count_claims(document)] == expected
