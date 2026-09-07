"""check_repudiation -- does an end still prescribe what the body withdrew?

Two signals, both cheap:
  (a) PHRASE: a repudiation sentence sharing >=3 content 3-grams with `## Use this` or the
      failure table.
  (b) NUMBER: a value the body explicitly says it "used to say", still present at an end.
Code fences are stripped from both sides -- they caused every false positive in v1.

WHAT IT MEASURED, with the snapshots the numbers came from (re-run any of them with --root
against a `git archive <commit> gaia/references` checkout; every figure below was produced that
way, not from memory):

  * `c257351` (2026-09-05 11:48), a snapshot that reproduces the audit's run exactly and the
    last commit before the Phase 1/2 sittings, so ALL NINE confirmed inversions are live in it
    (86dd06b and 6b5a157 give the same output, so this is a snapshot that reproduces it, not
    provably the one the audit ran):
        4 candidates, 2 of them real (X8 atmosphere, X56 seamless) -- PRECISION 2/4 = 50%,
        matching the audit's own "4 candidates, 2 confirmed defects".
        RECALL 2/9 = 22%. The population examined to find them was 41 body repudiation
        sentences over 37 documents -- body-only, because the ends are never scanned for
        repudiations; the whole-document count is 49 and is NOT this guard's denominator.
        FIVE of the nine inversion documents contained ZERO body repudiation sentences at that
        snapshot (X7 gpu-driven-culling, X12 caustics, X17 node-graph-runtime, X29 sea-ice,
        X52 mask-to-material), so this guard could not look at them at all: it sees only an
        inversion whose body ANNOUNCES the withdrawal, and most inversions do not. TWO more
        were looked at and missed -- X26 wave-models (5 body sentences) and X38 tectonic-uplift
        (1) -- every one of them scoring 0 shared 3-grams and no retracted number, because they
        retract something other than the inversion.
  * HEAD (2026-09-07), after the sittings closed X8 and X56:
        4 candidates, 0 of them real -- PRECISION 0/4 = 0%, FALSE-POSITIVE RATE 4/4 = 100%,
        from a population of 45 body repudiation sentences across 39 documents
        (whole-document count 54, again not this guard's denominator).
        All four are triaged with their reasons. The driver-fields one is recorded in
        registers/corrections.tsv, row `guard triage`; the other three were triaged by
        agent-inversion-triage and their rows are awaiting a verifier, so do not read this
        docstring as a claim that four rows are already in the register.

THE LIMIT THAT MUST SHIP WITH IT, and the reason the second row of numbers is not a regression:
the guard cannot tell a SURVIVING retraction from a CORRECTLY LANDED one. A correction that
lands at both ends necessarily leaves the end quoting the repudiation sentence's own wording, or
naming the retracted number to say it is not the answer -- which is exactly signal (a) and signal
(b). Precision therefore FALLS as the corpus is repaired, and 0/4 today is what a fixed corpus
looks like, not a broken guard. Never a gate (PLAN.md:320): a green run proves nothing and a red
run is a reading list.

FIXED HERE (the bug the corpus recorded at PLAN.md:191 and never fixed): `words()` was
`[a-z0-9][a-z0-9.~-]*`, which is greedy over `.` `~` `-` and so KEPT trailing punctuation --
`elevation.` at the end of a sentence never matched `elevation` in a table cell. One full stop
broke a shingle. Measured on HEAD: 5126 of 166861 tokens (3.07%) carried trailing punctuation,
1952 distinct forms, `it.` `eq.` `p.` `fig.` the most common. The replacement requires the last
character to be alphanumeric; it is token-count preserving (verified across the 39 scanned
documents), so it can only change a token's VALUE, never split or merge one. What changed:
  * on HEAD the candidate SET is unchanged -- the same 4 sentences -- and one of them gains
    evidence, volumetric-clouds' depth-operator sentence going 3 -> 4 shared 3-grams, because
    the failure row's `standard depth.` now matches the body's `standard depth`;
  * on `c257351` the set is likewise unchanged (4), with the same sentence going 3 -> 4;
  * the difference the fix actually buys is BRITTLENESS. Take `c257351`, where X8 is live, and
    change ONE punctuation mark in the failure row that carries the withdrawn prescription --
    `sun elevation. Roughly 1.03 ms` -> `sun elevation - roughly 1.03 ms`, leaving the
    prescription itself untouched -- and the old tokeniser goes SILENT on X8 (4 candidates ->
    3) while the fixed one still reports it (4). That mutation is fixture `a-brittle` in
    --selftest, which fails if `words()` is reverted.

Usage:  python3 repudiation-prototype.py [--root DIR] [--selftest]
"""
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/user/skills/gaia/references")
REPUD = re.compile(r"(an earlier (?:revision|version)|used to (?:say|state|print|call|claim|read)"
                   r"|this (?:line|table|document|file) (?:once|used to)|was withdrawn)", re.I)
STOP = set("""the a an and or of to it is was that this these those on in at for with by as be are
were from into not no but so than then also which what when where how why does do did you your we
our they them their there here one per each every any all more most less least same other another
about over under after before said say says would will can may might should must have has had
using use used make makes made get gets given give gives take takes only its it's""".split())
NUM = re.compile(r"\b\d+(?:\.\d+)?\s*%")
# A token starts alphanumeric and must END alphanumeric. The inner `.~-` are kept because
# `1.03`, `multi-scattering` and `K_d~` are single tokens; the trailing ones are not part of the
# word. The old form omitted the closing `[a-z0-9]` and kept `elevation.` -- see the docstring.
WORD = re.compile(r"[a-z0-9](?:[a-z0-9.~-]*[a-z0-9])?")
# The bug, kept so --selftest can prove the fix is load-bearing rather than assert it.
LEGACY_WORD = re.compile(r"[a-z0-9][a-z0-9.~-]*")


def unfence(t):
    return re.sub(r"```.*?```", " ", t, flags=re.S)


def words(s, pattern=None):
    return [w for w in (pattern or WORD).findall(s.lower()) if w not in STOP]


def grams(s, n=3, pattern=None):
    w = words(s, pattern)
    return {tuple(w[i:i+n]) for i in range(len(w)-n+1)}


def anchor(h):
    return h.lower().startswith(("use this", "how this fails", "when it fails"))


def scan(root, pattern=None, min_overlap=3):
    """Return one record per candidate: (filename, overlap-count, retracted numbers, sentence).

    `min_overlap=0` returns every repudiation sentence with its measured overlap instead of only
    the candidates -- used by --selftest so it can print a number it actually took.
    """
    out = []
    for p in sorted(Path(root).glob("*.md")):
        if p.name.startswith("papers") or p.name in ("index.md", "coverage.md"):
            continue
        parts = re.split(r"^## +(.+?)\s*$", unfence(p.read_text(encoding="utf-8")), flags=re.M)
        secs = list(zip(parts[1::2], parts[2::2]))
        ends = " ".join(b for h, b in secs if anchor(h))
        body = " ".join(b for h, b in secs if not anchor(h))
        if not ends:
            continue
        eg = grams(ends, pattern=pattern)
        enums = {e.replace(" ", "") for e in NUM.findall(ends)}
        for sent in re.split(r"(?<=[.!?])\s+", body):
            if not REPUD.search(sent):
                continue
            ov = grams(sent, pattern=pattern) & eg
            retracted = {n for n in NUM.findall(sent) if n.replace(" ", "") in enums}
            if len(ov) >= min_overlap or retracted:
                out.append((p.name, len(ov), sorted(retracted), sent.strip()))
    return out


def report(root):
    hits = scan(root)
    for name, nov, retracted, sent in hits:
        why = []
        if nov >= 3:
            why.append(f"{nov} shared 3-grams")
        if retracted:
            why.append(f"retracted value(s) {retracted} still at an end")
        print(f"{name}  [{'; '.join(why)}]")
        print(f"    {sent[:170]}")
        print()
    print(f"{len(hits)} candidate(s) corpus-wide.")
    print("Candidates, not defects: this guard cannot tell a surviving retraction from a "
          "correctly-landed one. Triage every one and record the reason in "
          "registers/corrections.tsv. Never a gate.")
    return hits


# --- selftest -----------------------------------------------------------------------------
# Four fixtures, each asserting a different direction. `a-brittle` is the one that fails if the
# `words()` fix is reverted: it is the X8 shape with the full stop that hid it replaced by a
# dash, so the buggy tokeniser scores 2 shared 3-grams (below threshold) and says nothing while
# the withdrawn prescription is still standing at the end. `c-clean` is what stops the selftest
# passing by flagging everything.
FIXTURES = {
    "a-brittle.md": """## Use this

Bake transmittance at load - gate multi-scattering on one degree of sun elevation - 1.03 ms.

## The rebuild policy

An earlier revision of this table said to gate multi-scattering on one degree of sun elevation.
""",
    "b-landed.md": """## Use this

Reduce toward the farthest depth. Write the quantity, not the operator, because the operator
flips with the depth convention.

## The march

Write the quantity, not the operator, because the operator flips with the depth convention - and
an earlier version of this line got it backwards.
""",
    "c-clean.md": """## Use this

March the volume front to back and composite with premultiplied alpha.

## History

An earlier revision of this document recommended a stored 3-D texture instead.
""",
    "d-number.md": """## How this fails, and what it looks like

| Seam at deep levels | wrong by up to 42% of relief at 250 (the L = 3 cell; 22% is the L = 2 cell) | Pick a multiple |

## The decimation lattice

This line used to say 22%, which is the L = 2 cell, a sample quoted as the maximum.
""",
}

EXPECTED = {
    # file          flagged  why it is in the set
    "a-brittle.md": (True,  "a LIVE inversion the pre-fix tokeniser scored below threshold "
                            "because one token ended in a full stop -- the recorded bug"),
    "b-landed.md":  (True,  "a correction that landed at BOTH ends and is flagged anyway -- the "
                            "documented wording false positive"),
    "c-clean.md":   (False, "a repudiation with no shared wording and no number: the guard must "
                            "be able to say no"),
    "d-number.md":  (True,  "the retracted number named at the end to say it is NOT the answer "
                            "-- the documented number false positive"),
}


def selftest():
    with tempfile.TemporaryDirectory() as d:
        for name, text in FIXTURES.items():
            (Path(d) / name).write_text(text, encoding="utf-8")
        hits = {h[0]: h for h in scan(d)}
        legacy = {h[0]: h for h in scan(d, pattern=LEGACY_WORD)}
        ok = True
        for name, (want, why) in EXPECTED.items():
            got = name in hits
            good = got == want
            ok &= good
            detail = ""
            if got:
                detail = f" ({hits[name][1]} grams, retracted {hits[name][2]})"
            print(f"  {'PASS' if good else 'FAIL'}  {name:14} flagged={got} expected={want}"
                  f"{detail}  -- {why}")
        # THE REGRESSION GATE. Not "a-brittle scores >= 3" -- that passes with the bug restored,
        # which is how this fixture was caught passing by design the first time it was written.
        # The assertion is DIFFERENTIAL: the same fixture must be visible to the fixed tokeniser
        # and invisible to the recorded bug. Revert WORD and the two runs agree, so this fails.
        a_fixed = "a-brittle.md" in hits
        a_legacy = "a-brittle.md" in legacy
        good = a_fixed and not a_legacy
        ok &= good
        # Measure the legacy overlap rather than defaulting it to 0 when the fixture is not a
        # legacy candidate -- a printed figure has to come from somewhere.
        seen = {h[0]: h for h in scan(d, pattern=LEGACY_WORD, min_overlap=0)}
        n_fixed = {h[0]: h for h in scan(d, min_overlap=0)}["a-brittle.md"][1]
        n_legacy = seen["a-brittle.md"][1]
        print(f"  {'PASS' if good else 'FAIL'}  {'a-brittle.md':14} fixed tokeniser scores "
              f"{n_fixed} shared 3-grams and flags it; the pre-fix tokeniser scores {n_legacy} "
              f"and does not -- the recorded bug, reproduced")
        # a-brittle must be flagged BY THE GRAM SIGNAL, not by a stray number, or the fixture
        # would pass for the wrong reason.
        if a_fixed and hits["a-brittle.md"][1] < 3:
            print("  FAIL  a-brittle.md was flagged by the number signal, not the gram signal")
            ok = False
    print("selftest:", "green" if ok else "RED")
    return 0 if ok else 1


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--selftest" in argv:
        sys.exit(selftest())
    root = ROOT
    if "--root" in argv:
        root = Path(argv[argv.index("--root") + 1])
    report(root)
