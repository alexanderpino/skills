"""Render the skill library to `site/` — one index, one page per skill — and fail on drift.

    python3 tools/wiki.py            # write site/
    python3 tools/wiki.py --check    # fail if any page is stale, changing nothing

WHY THIS EXISTS

Ten live skills share this repository and nothing tells you what they are, how big they are,
or which of them carries any evidence for what it says. `obsolete/README.md` does that job by
hand for exactly two retired skills — and being hand-written it is a second end of every
figure it quotes, waiting to drift the way `gaia/registers/corrections.tsv` records 252 times.

So this is derived, on `gaia/scripts/ledger.py`'s pattern, which is `index.py`'s pattern:
one source of truth, a rendering, and a `--check` that fails when they diverge.

WHAT IT MEASURES, AND THE TRAP IN MEASURING IT

Counting registers and rigs per skill would rank a book-writing skill below a physics one for
lacking measurement rigs it has no use for. That is not a quality signal, it is a subject
signal, and publishing it as a league table would be dishonest.

So the band separates the two. RIGS AND REGISTERS ARE SUBJECT-DEPENDENT and are reported as
what they are: apparatus a skill making numeric claims needs and a skill making editorial ones
does not. EVALS ARE UNIVERSAL — every skill can be asked whether loading it improves an
answer — and are reported as the one comparable column.

NO TIMESTAMP, deliberately, for the reason `ledger.py` records: a stamp forces a normaliser
into `--check`, and `index.py`'s normaliser was wrong twice in ways that let a forged
verification banner through. Nothing volatile means nothing to normalise.
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site"
SKIP = {"obsolete", "scratchpad", "test_env", "tools", "site", ".git", ".github"}


def front_matter(p: Path) -> dict:
    t = p.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", t, re.S)
    fm: dict[str, str] = {}
    if not m:
        return fm
    body = m.group(1)
    for key in ("name", "description", "title", "type"):
        mm = re.search(rf"^{key}: *(?:>-\n((?:[ \t]+.*\n)+)|\"([^\"]*)\"|(.*))$", body, re.M)
        if not mm:
            continue
        v = mm.group(1) or mm.group(2) or mm.group(3) or ""
        fm[key] = re.sub(r"\s+", " ", v).strip()
    return fm


def count_lines(paths) -> int:
    n = 0
    for p in paths:
        try:
            n += len(p.read_text(encoding="utf-8").splitlines())
        except OSError:
            pass
    return n


def tsv_rows(p: Path) -> int:
    try:
        return sum(1 for l in p.read_text(encoding="utf-8").splitlines()
                   if l.strip() and not l.startswith("#"))
    except OSError:
        return 0


def survey() -> tuple[list[dict], list[str]]:
    problems: list[str] = []
    skills = []
    for sk in sorted(ROOT.glob("*/SKILL.md")):
        d = sk.parent
        if d.name in SKIP:
            continue
        fm = front_matter(sk)
        if not fm.get("name"):
            problems.append(f"{d.name}/SKILL.md has no parsable `name:` in its front matter")
            continue
        if not fm.get("description"):
            problems.append(f"{d.name}/SKILL.md has no parsable `description:` — a skill with "
                            f"no description cannot be selected, so this is not cosmetic")
        refs = sorted((d / "references").glob("*.md"))
        regs = sorted((d / "registers").glob("*.tsv"))
        rigs = sorted((d / "rigs").rglob("*.py"))
        evals = sorted((d / "evals").glob("*.json"))
        scripts = sorted((d / "scripts").glob("*.py"))
        n_eval = 0
        for e in evals:
            try:
                import json
                j = json.loads(e.read_text(encoding="utf-8"))
                n_eval += len(j.get("evals", j if isinstance(j, list) else []))
            except Exception:
                pass
        skills.append({
            "dir": d.name, "name": fm["name"], "desc": fm.get("description", ""),
            "skill_lines": len(sk.read_text(encoding="utf-8").splitlines()),
            "refs": len(refs), "ref_lines": count_lines(refs),
            "registers": len(regs), "register_rows": sum(tsv_rows(p) for p in regs),
            "rigs": len(rigs), "scripts": len(scripts),
            "eval_files": len(evals), "eval_cases": n_eval,
            "ref_names": [p.stem for p in refs],
        })
    obsolete = sorted(p.parent.name for p in ROOT.glob("obsolete/*/SKILL.md"))
    return skills, problems, obsolete


def css() -> str:
    return (ROOT / "site" / "wiki.css").read_text(encoding="utf-8")


def band(s: dict) -> str:
    """The evidence a skill carries. Evals are the comparable column; the rest is subject."""
    ev = s["eval_cases"]
    cells = [
        ("evals", f"{ev}" if ev else "none", "universal", "ok" if ev else "gap"),
        ("registers", f"{s['register_rows']:,} rows" if s["registers"] else "none", "subject", ""),
        ("rigs", f"{s['rigs']}" if s["rigs"] else "none", "subject", ""),
    ]
    return "".join(
        f'<div class="ev {cls}"><span class="evk">{html.escape(k)}</span>'
        f'<span class="evv">{html.escape(v)}</span>'
        f'<span class="evn">{html.escape(note)}</span></div>'
        for k, v, note, cls in cells)


def index_page(skills: list[dict], obsolete: list[str]) -> str:
    e = html.escape
    tot_ref = sum(s["ref_lines"] for s in skills)
    tot_sk = sum(s["skill_lines"] for s in skills)
    with_ev = sum(1 for s in skills if s["eval_cases"])
    rows = ""
    for s in sorted(skills, key=lambda x: -x["ref_lines"]):
        ratio = s["skill_lines"] / max(s["ref_lines"], 1)
        flag = ' <span class="warnpill">router heavier than its corpus</span>' if ratio > 0.6 else ""
        rows += f'''<a class="card" href="{e(s["dir"])}.html">
<header><h3>{e(s["name"])}</h3><span class="sz">{s["skill_lines"]} ln router
&middot; {s["refs"]} refs &middot; {s["ref_lines"]:,} ln</span></header>
<p class="cdesc">{e(s["desc"][:210])}{"&hellip;" if len(s["desc"]) > 210 else ""}</p>
<div class="evrow">{band(s)}</div>{flag}</a>'''
    obs = "".join(f"<li><code>{e(o)}</code></li>" for o in obsolete)
    return f'''<title>Skill Library</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
{css()}</style>
<div class="wrap">
<header class="top">
  <p class="eyebrow">skill library &middot; generated from the tree</p>
  <h1>{len(skills)} skills, and what each one can show for itself</h1>
  <p class="sub">{tot_sk:,} lines of router over {tot_ref:,} lines of reference. Every figure
  on this page is counted from the filesystem, never written by hand.</p>
</header>

<section class="limit">
  <h2>How to read the evidence band</h2>
  <p><strong>Evals are the comparable column.</strong> Every skill — a physics one, a writing
  one — can be asked whether loading it makes an answer better. {with_ev} of {len(skills)}
  carry any eval cases at all.</p>
  <p><strong>Registers and rigs are not comparable and are not a score.</strong> A skill whose
  claims are numeric needs apparatus to check them; a skill whose claims are editorial does
  not, and ranking the second below the first for lacking rigs it has no use for would be
  dishonest. They are reported as what they are: apparatus, where the subject calls for it.</p>
</section>

<section>
  <h2>The skills</h2>
  <div class="grid">{rows}</div>
</section>

<section>
  <h2>Retired</h2>
  <p class="lede">Kept for provenance, not for use.</p>
  <ul class="obs">{obs}</ul>
</section>

<footer><p>Generated by <code>tools/wiki.py</code>. <code>--check</code> fails if any page has
drifted from the tree it describes.</p></footer>
</div>
'''


def skill_page(s: dict) -> str:
    e = html.escape
    refs = "".join(f'<li><code>{e(n)}</code></li>' for n in s["ref_names"])
    ratio = s["skill_lines"] / max(s["ref_lines"], 1)
    note = ("<p class=\"limit-note\">The router is heavier than the corpus it routes to. "
            "Every token of it loads on every use, whether or not the question needs it.</p>"
            if ratio > 0.6 else "")
    return f'''<title>{e(s["name"])} &middot; skill</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
{css()}</style>
<div class="wrap">
<header class="top">
  <p class="eyebrow"><a href="index.html">&larr; skill library</a></p>
  <h1>{e(s["name"])}</h1>
  <p class="sub">{e(s["desc"])}</p>
  <div class="strip">
    <div class="cell"><span class="n">{s["skill_lines"]}</span><span class="k">lines of router, loaded every time</span></div>
    <div class="cell"><span class="n">{s["refs"]}</span><span class="k">reference documents</span></div>
    <div class="cell"><span class="n">{s["ref_lines"]:,}</span><span class="k">lines of reference, loaded on demand</span></div>
    <div class="cell"><span class="n">{s["eval_cases"] or "&mdash;"}</span><span class="k">eval cases</span></div>
  </div>
  {note}
</header>

<section>
  <h2>Evidence it carries</h2>
  <div class="evrow wide">{band(s)}</div>
</section>

<section>
  <h2>Reference documents</h2>
  <ul class="refs">{refs or "<li>none</li>"}</ul>
</section>

<footer><p>Generated by <code>tools/wiki.py</code> from <code>{e(s["dir"])}/</code>.</p></footer>
</div>
'''


def build() -> tuple[dict[Path, str], list[str]]:
    skills, problems, obsolete = survey()
    pages = {OUT / "index.html": index_page(skills, obsolete)}
    for s in skills:
        pages[OUT / f"{s['dir']}.html"] = skill_page(s)
    return pages, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if any page is stale")
    args = ap.parse_args()
    pages, problems = build()
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\n{len(problems)} problem(s); nothing written.")
        return 1
    if args.check:
        stale = [p for p, want in pages.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != want]
        extra = [p for p in OUT.glob("*.html") if p not in pages]
        if stale or extra:
            for p in stale:
                print(f"  STALE  site/{p.name}")
            for p in extra:
                print(f"  ORPHAN site/{p.name} — describes a skill that is no longer here")
            print("\nRun `python3 tools/wiki.py`.")
            return 1
        print(f"site/ is current ({len(pages)} pages).")
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    for p, want in pages.items():
        p.write_text(want, encoding="utf-8")
    for p in OUT.glob("*.html"):
        if p not in pages:
            p.unlink()
    print(f"wrote {len(pages)} pages to site/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
