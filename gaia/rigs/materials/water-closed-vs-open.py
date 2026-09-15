#!/usr/bin/env python3
"""The `## Use this` body-type enumeration of water-closed-vs-open.md, against its own page.

⚠️ This block was called a bare taxonomy -- "a one-line type declaration, no numeric claim" --
and excluded from criterion 2 on that basis by an earlier verifier. It has a real gate, and the
gate is the page's own imperative: **"Bind every value to a column before you ship the table …
a value left unbound is a default nobody chose."** That sentence is a rule about the document
that can be mechanised exactly, and nothing was checking it.

Two claims, both parsed from the page:

  1. COUNT -- the alternation has as many members as the prose says it has. The prose writes the
     number as a WORD ("nine values"), so the rig reads a word and converts it, the way
     rigs/networks/hydraulic_geometry.py reads "one four-hundredth".
  2. BINDING -- the table below the fence binds every member exactly once. A member missing from
     the table is the unbound default the page warns about; a token in the table that is not in
     the fence is a column for a type that does not exist; a member appearing twice is two
     columns claiming the same value. All three are failures and each is named separately.

Halting: two regex passes and a set comparison. No loop with a data-dependent bound.
"""
import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "water-closed-vs-open.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")

WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
ok = True


def fail(msg: str) -> None:
    global ok
    ok = False
    print(f"FAIL  {msg}")


# ── the fence itself ─────────────────────────────────────────────────────────────────────
m = re.search(r"^bodyType = (.+)$", BODY, re.M)
if not m:
    sys.exit("the page no longer declares `bodyType = ...`")
members = [x.strip() for x in m.group(1).split("|")]
if len(set(members)) != len(members):
    fail(f"the alternation repeats a member: {members}")

# ── 1. the count the prose states, in words ──────────────────────────────────────────────
cm = re.search(r"Two columns do not resolve\s+(\w+)\s+values", BODY)
if not cm:
    sys.exit("the page no longer states how many values the columns must resolve")
want = WORDS.get(cm.group(1).lower())
if want is None:
    fail(f"the page says {cm.group(1)!r} values, which is not a number this rig knows")
elif len(members) != want:
    fail(f"the fence declares {len(members)} members; the prose says {cm.group(1)} ({want})")
else:
    print(f"PASS  the alternation has {len(members)} members, and the prose says "
          f"{cm.group(1)} ({want})")

# ── 2. every member bound to exactly one column ──────────────────────────────────────────
# The binding table's first column, after the header and separator rows.
rows = re.findall(r"^\|\s*((?:`[a-z]+`(?:,\s*)?)+)\s*\|", BODY, re.M)
bound: list[str] = []
for cell in rows:
    bound.extend(re.findall(r"`([a-z]+)`", cell))

if not bound:
    fail("no binding table found under the fence -- every value is an unbound default")
else:
    dupes = sorted({b for b in bound if bound.count(b) > 1})
    missing = sorted(set(members) - set(bound))
    extra = sorted(set(bound) - set(members))
    if dupes:
        fail(f"bound to more than one column: {dupes} -- two columns claim the same value")
    if missing:
        fail(f"declared but NEVER BOUND: {missing} -- the page's own words, "
             f"'a default nobody chose'")
    if extra:
        fail(f"bound but not declared: {extra} -- a column for a type the fence does not have")
    if not (dupes or missing or extra):
        print(f"PASS  all {len(members)} members bound exactly once, across "
              f"{len(rows)} table rows")

print()
sys.exit(0 if ok else 1)
