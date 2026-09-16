"""Render `site/errata.html` from the registers, and fail when it drifts.

    python3 gaia/scripts/ledger.py            # write site/errata.html
    python3 gaia/scripts/ledger.py --check    # fail if it is stale, changing nothing

WHY THIS IS GENERATED AND NEVER WRITTEN BY HAND

A published page describing this corpus is a SECOND END of every claim it repeats, and a
second end that nobody checks is the defect `corrections.tsv` records more than any other:
a correction lands at one end and the other keeps saying the old thing. A hand-maintained
site would be a third end, on the open web, where it is cited.

So the page is derived. It cannot claim a correction that is not in the register, cannot
miss one that is, and cannot describe the verification state differently from how the tree
reports it. `--check` in CI is what keeps that true -- a hand edit shows up as a diff rather
than as a slow divergence nobody notices. This is `index.py`'s idiom, deliberately reused
rather than reinvented: one mechanism in the repo, not two.

NO TIMESTAMP IS EMITTED, and that is a decision. `index.py` stamps its output and therefore
needs a normaliser in `--check` to stop the stamp failing every run -- and that normaliser
was wrong TWICE in ways that let a forged verification banner through (see its own comments).
A page with nothing volatile in it needs no normaliser, so there is nothing to get wrong.
The commit that generated a page is its date.

WHAT THIS PAGE MUST ALWAYS LEAD WITH: the fraction of the corpus a human has actually
verified. A reference that publishes its errata and buries its coverage is worse than one
that publishes neither, because the errata buy a credibility the coverage does not support.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registers"
REFS = ROOT / "references"
OUT = ROOT / "site" / "errata.html"

# A stamp covers `## Use this` and the failure table and nothing else; check.py owns the
# authoritative count and this script must not compute a second, differing one.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check as _check  # noqa: E402


def rows(path: Path, width: int) -> list[list[str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        f = line.split("\t")
        if len(f) >= width:
            out.append(f)
    return out


def clip(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:n] + ("…" if len(s) > n else "")


def docname(s: str) -> str:
    m = re.search(r"references/([\w\-.]+)\.md", s or "")
    return m.group(1) if m else clip(s, 40)


def collect() -> tuple[dict, list[str]]:
    problems: list[str] = []
    corr = rows(REG / "corrections.tsv", 8)
    src = rows(REG / "source-findings.tsv", 6)
    gp = rows(REG / "guard-proofs.tsv", 5)
    if not corr or not src or not gp:
        problems.append("a register came back empty; refusing to publish a page that "
                        "understates the corpus's own error count")

    # The header row of source-findings.tsv is a real row by shape, not by content. Dropping
    # it by INDEX would silently drop a real finding the day a row is inserted above it; drop
    # it by what it says instead, and fail loudly if it is no longer there to drop.
    head = [s for s in src if s[0].strip().lower() == "finding"]
    if len(head) > 1:
        problems.append(f"source-findings.tsv has {len(head)} header-shaped rows; expected 1")
    src = [s for s in src if s[0].strip().lower() != "finding"]

    t = _check.selfdescription_truth()
    pending = [c for c in corr if "pending" in c[6].lower()]
    done = [c for c in corr if "pending" not in c[6].lower()]
    if len(pending) != t["pending"]:
        problems.append(f"this script counts {len(pending)} pending corrections and check.py "
                        f"counts {t['pending']}; two counts of one fact is the defect this "
                        f"corpus keeps rediscovering")

    tiers = Counter(re.findall(r"tier: ([PFX?])",
                               "".join(p.read_text(encoding="utf-8")
                                       for p in sorted(REFS.glob("*.md")))))
    return {
        "corrections": len(corr), "pending": len(pending), "verified": len(done),
        "source_defects": len(src), "guard_proofs": len(gp), "tiers": dict(tiers),
        "documents": t["documents"], "body_lines": t["body_lines"],
        "stamped_docs": t["stamps"], "stamped_lines": t["signed_lines"],
        "per_doc": Counter(docname(c[1]) for c in corr).most_common(14),
        "pend_rows": pending[-14:], "done_rows": done[-10:], "src_rows": src[:12],
    }, problems


def _rec(kind: str, badge: str, head: list[str], body: list[tuple[str, str]]) -> str:
    e = html.escape
    hd = "".join(f'<span class="{c}">{e(v)}</span>' for c, v in zip(
        ("rid", "rdoc"), head)) if len(head) > 1 else f'<span class="rdoc">{e(head[0])}</span>'
    bd = f'<p class="rwhat">{e(body[0][1])}</p>' + "".join(
        f'<p class="rwhy"><span class="lbl">{e(k)}</span>{e(v)}</p>' for k, v in body[1:])
    return (f'<article class="rec {kind}"><header>{hd}'
            f'<span class="rstate">{e(badge)}</span></header>{bd}</article>')


def render(d: dict) -> str:
    T = d
    stamped_pct = T["stamped_lines"] / T["body_lines"] * 100
    tp, tf = T["tiers"].get("P", 0), T["tiers"].get("F", 0)
    pctP = tp / (tp + tf) * 100 if (tp + tf) else 0.0

    pend = "\n".join(_rec("pending", "open", [c[0], docname(c[1])], [
        ("", clip(c[2], 300)),
        ("why it is still open", clip(c[6], 220).replace("pending -- ", "")),
    ]) for c in T["pend_rows"])
    done = "\n".join(_rec("verified", "verified", [c[0], docname(c[1])], [
        ("", clip(c[2], 300)), ("verifier", clip(c[6], 200)),
    ]) for c in T["done_rows"])
    srcs = "\n".join(_rec("source", "source defect", [clip(s[1], 90)], [
        ("", clip(s[0], 200)),
        ("what is actually correct", clip(s[3], 320)),
        ("outcome", clip(s[5], 260)),
    ]) for s in T["src_rows"])

    mx = max(n for _, n in T["per_doc"]) or 1
    bars = "\n".join(
        f'<div class="bar"><span class="bname">{html.escape(n)}</span>'
        f'<span class="btrack"><span class="bfill" style="width:{c / mx * 100:.1f}%"></span></span>'
        f'<span class="bval">{c}</span></div>' for n, c in T["per_doc"])

    css = (ROOT / "site" / "errata.css").read_text(encoding="utf-8")
    return f"""<title>Gaia Errata</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
{css}</style>

<div class="wrap">
<header class="top">
  <p class="eyebrow">Gaia · terrain corpus · corrections register</p>
  <h1>Everything this corpus got wrong</h1>
  <p class="sub">A terrain and water reference for engines and authoring tools, published
  alongside its own errata. {T["corrections"]} corrections, each with both ends of the claim read.</p>
  <div class="strip">
    <div class="cell"><span class="n">{T["corrections"]}</span><span class="k">corrections recorded</span></div>
    <div class="cell warn"><span class="n">{T["pending"]}</span><span class="k">still awaiting a second hand</span></div>
    <div class="cell"><span class="n">{T["source_defects"]}</span><span class="k">defects found <em>in the sources</em></span></div>
    <div class="cell"><span class="n">{T["guard_proofs"]}</span><span class="k">proofs that a guard bites</span></div>
    <div class="cell warn"><span class="n">{stamped_pct:.2f}%</span><span class="k">of body lines checked by a human</span></div>
  </div>
</header>

<section class="limit">
  <h2>Read this before you trust anything below</h2>
  <p>A <code>verified:</code> stamp means a named person read the cited works and confirmed the
  page against them. <strong>{T["stamped_docs"]} of {T["documents"]} documents carry one</strong>,
  covering {T["stamped_lines"]} of {T["body_lines"]:,} body lines. No agent output substitutes for that stamp.</p>
  <div class="gauge"><i style="width:{max(stamped_pct, 0.6):.2f}%"></i></div>
  <p class="gnote"><span>{T["stamped_lines"]} lines stamped</span><span>{T["body_lines"] - T["stamped_lines"]:,} lines unstamped</span></p>
  <p>The machinery below — rigs that re-derive every printed figure from the page, guards that
  fail when two ends of a claim disagree — establishes that this corpus <em>does not contradict
  itself</em>. It does not establish that the physics is right. A page can be perfectly
  self-consistent and wrong, and that distinction is the reason this register exists.</p>
</section>

<section>
  <h2>Provenance, per claim</h2>
  <p class="lede">Every citation carries a tier. <strong>P</strong> means peer-reviewed and
  verified to contain the result attributed to it. <strong>F</strong> means a field source — a
  talk, a thesis, an engine's documentation — load-bearing but not peer-reviewed. Sources that
  could not be obtained are marked as unopened rather than quietly cited.</p>
  <div class="split">
    <div class="tier"><div class="n">{tp}</div><div class="k">tier <strong>P</strong> — peer-reviewed, verified ({pctP:.0f}% of citations)</div></div>
    <div class="tier"><div class="n">{tf}</div><div class="k">tier <strong>F</strong> — field source, named as such</div></div>
  </div>
</section>

<section>
  <h2>Which pages cost the most corrections</h2>
  <p class="lede">Corrections per document. A high bar is not a bad page — it is a page that has
  been looked at hard. The pages with no bar are the ones to be suspicious of.</p>
  <div class="chart">{bars}</div>
</section>

<section>
  <h2>Open questions</h2>
  <p class="lede">{T["pending"]} corrections are recorded but not yet re-derived by a second,
  independent hand. They are published in that state deliberately: a finding nobody has checked
  is worth more visible than hidden. Showing the most recent.</p>
  {pend}
</section>

<section>
  <h2>Defects found in the source material</h2>
  <p class="lede">Distilling a source reads it closely enough to find things a normal reader
  would not. These are errors located in the papers and reference material this corpus draws
  from — recorded here rather than silently corrected.</p>
  {srcs}
</section>

<section>
  <h2>Closed, with a verifier</h2>
  <p class="lede">Corrections re-derived by someone other than whoever proposed them. The rule is
  that a row with no verifier is not a finished correction.</p>
  {done}
</section>

<footer>
  <p>Generated by <code>gaia/scripts/ledger.py</code> from the corpus's own registers —
  <code>corrections.tsv</code>, <code>source-findings.tsv</code>, <code>guard-proofs.tsv</code>
  — so this page cannot drift from the documents it describes. <code>--check</code> fails if it
  does. Entry text is excerpted; the registers carry the full rows, each with the derivation and
  the command that checks it.</p>
</footer>
</div>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="fail if site/errata.html is stale; write nothing")
    args = ap.parse_args()

    data, problems = collect()
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        print(f"\n{len(problems)} problem(s); errata.html not written.")
        return 1

    want = render(data)
    if args.check:
        have = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if have != want:
            print("site/errata.html is out of date. Run `python3 gaia/scripts/ledger.py`.")
            return 1
        print(f"site/errata.html is current ({data['corrections']} corrections, "
              f"{data['pending']} pending).")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(want, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT.parent)} — {data['corrections']} corrections, "
          f"{data['pending']} pending, {data['source_defects']} source defects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
