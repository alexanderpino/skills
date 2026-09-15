#!/usr/bin/env python3
"""The ten derivations `river-networks.md` cites as `hydraulic_geometry.py §1..§10`.

⚠️ WHY THIS EXISTS. The page cited this file eleven times and the file was never committed.
An independent rating panel found it: eleven numeric derivations -- two unit conversions, a
least-squares refit, six scaling ratios and a worked threshold -- with no artefact to re-run and
no row in `pseudocode-execution.tsv`, so there was not even a claim to reproduce. Written
2026-09-15 from the page's stated inputs, NOT from its stated outputs.

⚠️ HOW IT CHECKS. Every expected value is PARSED OUT OF THE PAGE, never typed in here. The
sibling rig `approx/heightfield-lod.py` spent its life comparing arithmetic against literals
transcribed when it was written, printing "document says 134" beside a 134 in its own source; it
would have passed through any edit to its document. A figure this rig cannot find on the page is
a FAIL, not a silent skip.

NOT a measurement: no seed, no timing, no simulation. Closed-form arithmetic over figures the
page states, plus one least-squares fit over five counts the page quotes from Strahler's fig. 3.

Halting: straight-line arithmetic and one fixed five-point fit. No loop with a data-dependent
bound.
"""
import math
import pathlib
import re
import sys

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "river-networks.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
TEXT = DOC.read_text(encoding="utf-8")

FT = 0.3048          # metres per foot, exact by definition
CFS = 0.028316846592  # cubic metres per cubic foot, exact: FT**3

ok = True


def page(anchor: str, pattern: str, group: int = 1) -> float | None:
    """The number the PAGE prints for this figure: find `anchor`, then `pattern` after it."""
    i = TEXT.find(anchor)
    if i < 0:
        return None
    m = re.search(pattern, TEXT[i:i + 700])
    return float(m.group(group)) if m else None


def check(sec: str, label: str, got: float, want: float | None, tol: float = 0.01) -> None:
    global ok
    if want is None:
        ok = False
        print(f"FAIL  §{sec} {label}: derived {got:.6g}, but the page no longer prints this figure")
        return
    good = abs(got - want) <= tol * max(abs(want), 1e-12)
    ok = ok and good
    print(f"{'PASS' if good else 'FAIL'}  §{sec} {label}: derived {got:.6g}, page says {want:.6g}")


# ── §1 the two exponent triples must close, because Q = w*d*v ────────────────────────────
# Parsed from the two table rows, so a mistyped exponent is caught rather than re-asserted.
rows = re.findall(r"\|\s*\*?\*?(?:at a station|downstream)\*?\*?[^|]*\|"
                  r"\s*\*?\*?([\d.]+)\*?\*?\s*\|\s*\*?\*?([\d.]+)\*?\*?\s*\|"
                  r"\s*\*?\*?([\d.]+)\*?\*?\s*\|", TEXT, re.I)
if len(rows) != 2:
    ok = False
    print(f"FAIL  §1: found {len(rows)} exponent triple rows on the page, want 2")
else:
    for name, triple in zip(("at-a-station", "downstream"), rows):
        b, f, m = (float(x) for x in triple)
        check("1", f"{name} b+f+m", b + f + m, 1.0, tol=1e-9)
    B, F, M = (float(x) for x in rows[1])

# ── §2 lambda = 6.5*w^1.1 in FEET -> the metric coefficient ──────────────────────────────
# lambda_m = FT * 6.5 * (w_m/FT)^1.1 = 6.5 * FT^(1-1.1) * w_m^1.1
C_FT = page("p. 59 fits", r"`λ = ([\d.]+)\\?·w\^([\d.]+)`")
EXP = page("p. 59 fits", r"`λ = [\d.]+\\?·w\^([\d.]+)`")
if C_FT is None or EXP is None:
    ok = False
    print("FAIL  §2: the page no longer prints `lambda = C*w^e` in feet")
else:
    c_m = C_FT * FT ** (1 - EXP)
    check("2", "metric coefficient", c_m, page("Converted (", r"lambda = ([\d.]+) \* w"))

# ── §3 the braiding line, cfs -> SI ──────────────────────────────────────────────────────
# S = 0.06*Q_cfs^-0.44 and Q_cfs = Q_si/CFS, so S = 0.06*CFS^0.44 * Q_si^-0.44
C_CFS = page("braided above", r"S = ([\d.]+)\\?·Q\^−?-?([\d.]+)")
E_Q = page("braided above", r"S = [\d.]+\\?·Q\^−?-?([\d.]+)")
if C_CFS is None or E_Q is None:
    ok = False
    print("FAIL  §3: the page no longer prints the braiding line in cfs")
else:
    c_si = C_CFS * CFS ** E_Q
    check("3", "SI coefficient", c_si, page("In SI that line is", r"S = ([\d.]+)\\?·Q"))

# ── §4 the worked example: 800 cfs through the SI line ───────────────────────────────────
q_cfs = page("Fed into the SI line", r"([\d,]+) cfs")
if q_cfs is None:
    ok = False
    print("FAIL  §4: the page no longer prints the worked discharge")
else:
    q_si = q_cfs * CFS
    check("4", "800 cfs in m3/s", q_si,
          page("Fed into the SI line", r"is\s+([\d.]+)\s*m³/s"))
    s_crit = c_si * q_si ** -E_Q      # §3's DERIVED line, not the page's printed one
    check("4", "S_crit", s_crit, page("Fed into the SI line", r"`S_crit = ([\d.]+)`"))

# ── §5 the two published width chains, normalised at 1 km2 ───────────────────────────────
E_AREA = page("uses `w ∝ A^", r"uses `w ∝ A\^([\d.]+)`")
E_CHAIN = page("gives\n`w ∝ A^", r"`w ∝ A\^([\d.]+)` instead") or \
          page("into `w ∝ Q^0.5` gives", r"`w ∝ A\^([\d.]+)` instead")
if E_AREA is None or E_CHAIN is None:
    ok = False
    print("FAIL  §5: the page no longer prints both width-chain exponents")
else:
    d = E_AREA - E_CHAIN
    check("5", "disagreement at 10 km2", 10 ** d,
          page("Normalised to agree", r"differ by\s+([\d.]+)×\s*at\s*10"))
    check("5", "disagreement at 1000 km2", 1000 ** d,
          page("Normalised to agree", r"and\s+([\d.]+)×\s*at\s*1000"))

# ── §6 a fixed-shape template against the downstream exponents ───────────────────────────
# A_xs = Q/v, v ~ Q^M, so A_xs ~ Q^(1-M); a fixed shape splits that evenly.
if len(rows) == 2:
    e_area = 1 - M
    e_fixed = e_area / 2
    decades = 3
    check("6", "fixed-shape w and d exponent", e_fixed,
          page("template of **fixed shape**", r"`w ∝ d ∝ Q\^([\d.]+)`"), tol=1e-9)
    check("6", "error over three decades", 10 ** (decades * (B - e_fixed)),
          page("`w ∝ Q^0.5` and", r"([\d.]+)×\s*too\s*narrow"))
    check("6", "w/d growth over three decades", 10 ** (decades * (B - F)),
          page("should grow as `Q^0.1` (a", r"factor of ([\d.]+)\)"))

# ── §6b using the FEET coefficient with METRES ───────────────────────────────────────────
if C_FT is not None and EXP is not None:
    understatement = 1 - C_FT / (C_FT * FT ** (1 - EXP))
    check("6b", "understatement using 6.5 with metres", 100 * understatement,
          page("Using 6.5 with metres", r"understates every wavelength by ([\d.]+)%"))

# ── §7 refit Strahler fig. 3 (Smith 1953): counts per order, least squares on log10 N ─────
counts = re.search(r"gives counts ([\d, ]+) for orders 1–(\d)", TEXT)
if not counts:
    ok = False
    print("FAIL  §7: the page no longer prints Strahler's per-order counts")
else:
    n = [float(x) for x in counts.group(1).split(",")]
    x = list(range(1, len(n) + 1))
    y = [math.log10(v) for v in n]
    mx, my = sum(x) / len(x), sum(y) / len(y)
    slope = (sum((a - mx) * (b - my) for a, b in zip(x, y))
             / sum((a - mx) ** 2 for a in x))
    check("7", "least-squares slope b", -slope,
          page("refitting those by least squares", r"reproduces `b\n?= ([\d.]+)`")
          or page("refitting those by least squares", r"`b\s*=\s*([\d.]+)`"), tol=0.002)
    check("7", "bifurcation ratio r_b", 10 ** (-slope),
          page("refitting those by least squares", r"`r_b = ([\d.]+)`"), tol=0.003)
    # the page's own claim that Strahler's two printed numbers do not correspond
    printed_b = page("against the paper's printed", r"printed ([\d.]+)")
    if printed_b is not None:
        check("7", "10^(Strahler's printed slope)", 10 ** printed_b,
              page("10^0.541", r"=\s*([\d.]+)`"), tol=0.002)

# ── §8 where the width stops existing ────────────────────────────────────────────────────
anchor_w = page("a river anchored at", r"anchored at (\d+) cells wide")
stop_w = page("a river anchored at", r"reaches (\d+) cells")
if anchor_w is None or stop_w is None or E_CHAIN is None:
    ok = False
    print("FAIL  §8: the page no longer prints the anchor width, the stop width, or the chain")
else:
    area_ratio = (stop_w / anchor_w) ** (1 / E_CHAIN)
    _stated = page("a river anchored at",
                   r"at\s+([\d.]+)×10⁻³\s*of\s*the\s*anchor")
    check("8", "drainage-area fraction", area_ratio,
          _stated if _stated is None else _stated * 1e-3, tol=0.02)
    frac = re.search(r"one ([a-z\-]+)(?:th|st|nd|rd) of the anchor's basin", TEXT)
    WORDNUM = {"four-hundred": 400, "three-hundred": 300, "five-hundred": 500,
               "two-hundred": 200, "thousand": 1000}
    if not frac or frac.group(1) not in WORDNUM:
        ok = False
        print("FAIL  §8: the page no longer names the fraction in words")
    else:
        check("8", "one over that, in the page's words", 1 / area_ratio,
              float(WORDNUM[frac.group(1)]), tol=0.05)

# ── §9 thread count from the bar mode ────────────────────────────────────────────────────
# m ~ W^1.5 * S^0.5 * Q^-0.5, and B_i = (m-1)/2 + 1
m_double = 2 ** 1.5
check("9", "doubling belt width multiplies m by", m_double,
      page("Doubling the belt width", r"multiplies `m` by ([\d.]+)"))
check("9", "resulting B_i from m = 1", (m_double - 1) / 2 + 1,
      page("that lands at `B_i` =", r"`B_i` = ([\d.]+)"), tol=0.02)
undo = m_double ** 2      # Q^-0.5 must cancel m_double, so Q must rise by m_double^2
fold = re.search(r"it takes an (\w+)-fold increase in discharge", TEXT)
WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
if not fold or WORDS.get(fold.group(1).lower()) is None:
    ok = False
    print("FAIL  §9: the page no longer names the fold increase in words")
else:
    check("9", "the page's word for it", undo, float(WORDS[fold.group(1).lower()]), tol=1e-9)

# ── §10 width variation within one reach, constant width per channel ─────────────────────
if E_CHAIN is not None:
    for factor, pat in ((1.32, r"a reach spanning a factor ([\d.]+) in drainage area varies\s+(\d+)%"),
                        (2.0, r"a factor (2)\s+varies\s+(\d+)%"),
                        (10.0, r"a factor (10)\s+varies\s+(\d+)%")):
        m = re.search(pat, TEXT)
        if not m:
            ok = False
            print(f"FAIL  §10: the page no longer prints the variation at a factor {factor}")
            continue
        f, pct = float(m.group(1)), float(m.group(2))
        check("10", f"width variation at area factor {f:g}", 100 * (f ** E_CHAIN - 1), pct, tol=0.05)

print()
sys.exit(0 if ok else 1)
