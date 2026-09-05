"""check_repudiation -- does an end still prescribe what the body withdrew?

Two signals, both cheap:
  (a) PHRASE: a repudiation sentence sharing >=3 content 3-grams with `## Use this` or the
      failure table.
  (b) NUMBER: a value the body explicitly says it "used to say", still present at an end.
Code fences are stripped from both sides -- they caused every false positive in v1.
"""
import re
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

def unfence(t):
    return re.sub(r"```.*?```", " ", t, flags=re.S)

def words(s):
    return [w for w in re.findall(r"[a-z0-9][a-z0-9.~-]*", s.lower()) if w not in STOP]

def grams(s, n=3):
    w = words(s); return {tuple(w[i:i+n]) for i in range(len(w)-n+1)}

def anchor(h):
    return h.lower().startswith(("use this", "how this fails", "when it fails"))

hits = 0
for p in sorted(ROOT.glob("*.md")):
    if p.name.startswith("papers") or p.name in ("index.md", "coverage.md"):
        continue
    parts = re.split(r"^## +(.+?)\s*$", unfence(p.read_text(encoding="utf-8")), flags=re.M)
    secs = list(zip(parts[1::2], parts[2::2]))
    ends = " ".join(b for h, b in secs if anchor(h))
    body = " ".join(b for h, b in secs if not anchor(h))
    if not ends:
        continue
    eg, enums = grams(ends), set(NUM.findall(ends))
    for sent in re.split(r"(?<=[.!?])\s+", body):
        if not REPUD.search(sent):
            continue
        ov = grams(sent) & eg
        retracted = {n for n in NUM.findall(sent) if n.replace(" ", "") in
                     {e.replace(" ", "") for e in enums}}
        if len(ov) >= 3 or retracted:
            hits += 1
            why = []
            if len(ov) >= 3: why.append(f"{len(ov)} shared 3-grams")
            if retracted:    why.append(f"retracted value(s) {sorted(retracted)} still at an end")
            print(f"{p.name}  [{'; '.join(why)}]")
            print(f"    {sent.strip()[:170]}")
            print()
print(f"{hits} candidate(s) corpus-wide.")
