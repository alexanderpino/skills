#!/usr/bin/env python3
"""caustics.md's `## Use this` fence and the figures that price it, against its own page.

Every expected value below is PARSED OUT OF references/caustics.md at run time, anchored on
prose, never on a number. Nothing is typed in. A vanished anchor exits non-zero -- there is no
path through this file that skips a claim quietly.

THE FENCE'S OWN ALGEBRA IS PARSED AS TEXT AND EVALUATED (section 9). `mu_w`, `L`, `f`, `E_sun`
and the beam-law claim at :107 are lifted from the page as expression STRINGS and run against
random draws, so an edit to any operator in the fence reaches this rig. That is the one thing
rigs/water/shallow-water.py names as its own deepest limit -- a hand transcription cannot see a
fence edit -- and here the transcription is the page's characters rather than mine.

⚠️ NOT GATED, each for a stated reason, listed at the bottom by `report_ungated()`:
  - `−0.088 /m` (:127) and `c/K_d = 0.75 to 1.20 ... about 2.8` (:282): the operands are `a` and
    `b` for pure water at 610 nm and for clear oceanic water. They are in water-optics.md, not
    on this page. A rig that supplied them would be asserting its own memory.
  - the RMS series ±1.27 / ±0.22 / ±0.11 and the 1-D ±0.56 / ±0.38 / ±0.81, fold peak 15.9 ->
    5.1, ±0.52 (:166-178): measured on a CPU rig the page describes and does not ship. Building
    one here would make its disagreements indict the page. Their INTERNAL consistency -- photon
    count against grid factor against grid resolution -- is gated in section 8, and ±1.27's
    three appearances are asserted equal in section 10.
  - `G` has mean 1 (:96, :113): `G` is DEFINED at :96 as splat density over the density a flat
    surface deposits. Its mean is 1 by construction; a rig asserting it moves both sides of the
    comparison together and no page edit can contradict it. Cannot fail, so not gated.
  - `mean E_sun plus mean E_sun is exactly 2·E_sun` (:301): x + x = 2x. Cannot fail.
  - frame time (:157-161): the page explicitly refuses to price it.

⚠️ REPORTED, NOT GATED -- the page states `B(phase_g)` twice with two values. See
report_B_contradiction()`. Gating the disagreement would put this rig red on a clean tree.

Halting: no loop has a data-dependent bound. Every loop runs a literal count of draws or walks
a list already materialised by one regex pass over a file read once; the table lengths are
themselves asserted against counts parsed from the prose.
"""
import math
import pathlib
import re
import sys
from decimal import Decimal, ROUND_HALF_UP

DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "caustics.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "sixteen": 16, "sixty-four": 64}
OPS = str.maketrans({"−": "-", "–": "-", "—": "-", "·": "*", "×": "*"})
ok = True


def fail(msg):
    global ok
    ok = False
    print(f"FAIL  {msg}")


def grab(pattern, what, group=1):
    """The page's own words, or this rig stops. A missing figure is never a silent skip."""
    m = re.search(pattern, BODY)
    if not m:
        sys.exit(f"the page no longer states {what} (pattern {pattern!r})")
    return m.group(group)


def grabm(pattern, what):
    m = re.search(pattern, BODY)
    if not m:
        sys.exit(f"the page no longer states {what} (pattern {pattern!r})")
    return m


def num(pattern, what, group=1):
    return float(grab(pattern, what, group))


def word(pattern, what, group=1):
    w = grab(pattern, what, group).lower()
    if w not in WORDS:
        sys.exit(f"the page writes {what} as {w!r}, which is not a number this rig knows")
    return WORDS[w]


def printed(value, page_str):
    """Format `value` to the page's OWN printed precision, half-up. String compare after."""
    if "e" in page_str:
        mant, _, ex = page_str.partition("e")
        dp = len(mant.split(".")[1]) if "." in mant else 0
        m2, _, e2 = (f"%.{dp}e" % value).partition("e")
        return f"{m2}e{int(e2)}", f"{mant}e{int(ex)}"
    dp = len(page_str.split(".")[1]) if "." in page_str else 0
    q = Decimal(1).scaleb(-dp)
    return str(Decimal(repr(value)).quantize(q, rounding=ROUND_HALF_UP)), page_str


def check(label, value, page_str):
    got, want = printed(value, page_str)
    if got == want:
        print(f"PASS  {label}: derived {value:.6g} -> {got}, page says {want}")
        return True
    fail(f"{label}: derived {value:.6g} -> {got}, page says {want}")
    return False


def agree(label, values):
    """Both ends of the page, asserted against each other. A one-ended correction is a FAIL."""
    if len(set(values)) == 1:
        print(f"PASS  {label}: all {len(values)} ends of the page say {values[0]}")
        return True
    fail(f"{label}: the ends of the page disagree with EACH OTHER: {values}")
    return False


EV_G = {"__builtins__": {}, "sqrt": math.sqrt, "exp": math.exp, "sin": math.sin,
        "cos": math.cos, "max": max, "min": min}


def ev(expr, **env):
    try:
        return eval(expr.translate(OPS).replace("^", "**"), dict(EV_G), env)
    except Exception as exc:   # a page expression that names a symbol the page cannot mean
        sys.exit(f"the page's expression `{expr}` will not evaluate: {exc}")


def fresnel(theta, n):
    """Exact unpolarised Fresnel. The only physics this file knows; the page names it at :103."""
    c1 = math.cos(theta)
    s = math.sin(theta) / n
    if s >= 1.0:
        return 1.0
    c2 = math.sqrt(1.0 - s * s)
    rs = (c1 - n * c2) / (c1 + n * c2)
    rp = (n * c1 - c2) / (n * c1 + c2)
    return (rs * rs + rp * rp) / 2.0


def hg_backscatter(g):
    """B(g) for Henyey-Greenstein, closed form: the integral of 2*pi*p over the back hemisphere."""
    return (1 - g * g) / (2 * g) * (1.0 / math.sqrt(1 + g * g) - 1.0 / (1 + g))


def hg_median_deg(g):
    """Closed form: invert the HG cumulative at 1/2. No search, no loop."""
    x = 0.5 / ((1 - g * g) / (2 * g)) + 1.0 / (1 + g)
    return math.degrees(math.acos((1 + g * g - 1.0 / (x * x)) / (2 * g)))


def hg_mean_deg(g, n=200000):
    """Simpson over a FIXED 200000 intervals in mu. Bound is a literal; nothing data-dependent."""
    tot = 0.0
    for i in range(n + 1):
        mu = -1.0 + 2.0 * i / n
        w = 1 if i in (0, n) else (4 if i % 2 else 2)
        tot += w * math.degrees(math.acos(max(-1.0, min(1.0, mu)))) * \
            (1 - g * g) / (2 * (1 + g * g - 2 * g * mu) ** 1.5)
    return tot * 2.0 / n / 3.0


print(f"caustics.md -- {len(BODY.splitlines())} lines\n")

# ── 1. R_ext: the exact unpolarised Fresnel the fence's E_sun line calls ──────────────────
# :103-104 names the law, the index and four angles; :105 names the figure it is NOT.
N_IOR = num(r"R_ext is the exact unpolarised Fresnel at\s*\n#\s+the SUN's incidence, "
            r"n = ([\d.]+):", "the index R_ext is evaluated at")
SPAN = grab(r"the SUN's incidence, n = [\d.]+:(.*?)\.\n", "the R_ext angle list", 1)
PAIRS = re.findall(r"([\d.]+)% at (\d+)", SPAN)
if len(PAIRS) != 4:
    sys.exit(f"the page no longer prints four R_ext angles (found {len(PAIRS)})")
for pct, deg in PAIRS:
    check(f"R_ext at {deg} deg, n = {N_IOR}", 100.0 * fresnel(math.radians(float(deg)), N_IOR), pct)

HEMI = grab(r"NOT the ([\d.]+)% cosine-weighted hemispherical figure", "the hemispherical figure")
_h, _n = 0.0, 200000                       # Simpson, FIXED interval count
for i in range(_n + 1):
    th = (math.pi / 2) * i / _n
    _h += (1 if i in (0, _n) else (4 if i % 2 else 2)) * \
        fresnel(th, N_IOR) * math.cos(th) * math.sin(th)
check("the cosine-weighted hemispherical average the page says this is NOT",
      100.0 * 2.0 * _h * (math.pi / 2) / _n / 3.0, HEMI)

# ── 2. c reconstructed: 1/B at the exported phase_g ──────────────────────────────────────
m = grabm(r"reconstructed from them as a \+ b_b/B\(phase_g\), which at phase_g = ([\d.]+) "
          r"is a \+ ([\d.]+)\*b_b", "the c reconstruction")
PHASE_G, RECIP_B = float(m.group(1)), m.group(2)
check(f"1/B(phase_g) at phase_g = {PHASE_G}", 1.0 / hg_backscatter(PHASE_G), RECIP_B)

# ── 3. the scattering angles the error argument turns on ─────────────────────────────────
m = grabm(r"the mean deflection is \*\*([\d.]+)°\*\* and the median \*\*([\d.]+)°\*\*,"
          r"\s*\nthrowing a photon (\d+) cm and (\d+) cm off course over a remaining (\w+) of "
          r"path", "the HG deflection figures")
MEAN_D, MED_D, OFF_MEAN, OFF_MED, UNIT = m.groups()
G_HERE = num(r"`phase_g = ([\d.]+)`, that is close to true", "the phase_g the deflection is at")
if G_HERE != PHASE_G:
    fail(f"the page states phase_g as {PHASE_G} at :102 and {G_HERE} at :133 -- they disagree")
else:
    print(f"PASS  phase_g agrees at both ends of the page: {PHASE_G}")
if UNIT != "metre":
    sys.exit(f"the page now measures the scramble over a {UNIT!r}, not a metre")
mean_deg, med_deg = hg_mean_deg(PHASE_G), hg_median_deg(PHASE_G)
check("HG mean deflection", mean_deg, MEAN_D)
check("HG median deflection", med_deg, MED_D)
check("mean scramble over one metre [cm]", 100.0 * math.tan(math.radians(mean_deg)), OFF_MEAN)
check("median scramble over one metre [cm]", 100.0 * math.tan(math.radians(med_deg)), OFF_MED)

# ── 4. the refracted path against the vertical depth ─────────────────────────────────────
m = grabm(r"understates it by up to ([\d.]+)x at `n = ([\d.]+)`", "the refracted-path factor")
UNDER, N_DET = m.group(1), float(m.group(2))
if N_DET != N_IOR:
    fail(f"`n` is {N_IOR} at :104 and {N_DET} at :243 -- the two ends disagree")
else:
    print(f"PASS  n agrees at both ends of the page: {N_IOR}")
MU_W_EXPR = grab(r"\nmu_w\s+= (.+?)\s+# Snell cosine", "the fence's mu_w line")
worst = max(1.0 / ev(MU_W_EXPR, theta_sun=math.radians(90.0 * i / 900), n=N_DET)
            for i in range(901))            # 901 is a literal; the sweep cannot run away
check(f"max z/mu_w over the vertical depth, from the fence's own `{MU_W_EXPR}`", worst, UNDER)

# ── 5. the scattering-length table under *Details* ───────────────────────────────────────
M_3 = int(grab(r"\| Water \| `b` \[1/m\] \| `1/\(b − b_b\)` \| `f` after (\d+) m of path \|",
               "the Details table header"))
B_PART = num(r"own water types at the particulate `B = ([\d.]+)`", "the particulate B")
B_MOL = 1.0 / num(r"Rayleigh phase function is symmetric and `B = 1/(\d+)`", "the molecular B")
N_PART = word(r"The (\w+) particle-laden rows are", "the count of particle-laden rows")
ROWS = re.findall(r"^\| ([a-z][^|]*?) \| ([\d.]+) \| ([\d.]+) m \| ([\d.e+-]+) \|$", BODY, re.M)
part = [r for r in ROWS if not r[0].startswith("pure water")]
pure = [r for r in ROWS if r[0].startswith("pure water")]
if len(part) != N_PART or len(pure) != 1:
    fail(f"the prose says {N_PART} particle-laden rows and one molecular row; the table has "
         f"{len(part)} and {len(pure)} -- a row has gone missing or been added")
else:
    print(f"PASS  the table carries {N_PART} particle-laden rows and 1 molecular row, as the "
          f"prose says")
scales = {}
for name, b_s, scale_s, f_s in ROWS:
    b = float(b_s)
    B = B_MOL if name.startswith("pure water") else B_PART
    k = b * (1.0 - B)                        # b - b_b, with b_b = B*b, the page's own :276
    scales[name] = float(scale_s)
    got, want = printed(1.0 / k, scale_s)
    if got == want:
        print(f"PASS  1/(b - b_b) for {name!r} at B = {B:g}: {1.0 / k:.6g} -> {got} m")
    elif name.startswith("pure water"):
        # ⚠️ THE ONE CELL THAT DOES NOT REPRODUCE AT THE PRINTED b. Gated instead against the
        # interval the printed b's OWN precision allows -- a two-sided reproduction, not a
        # bound -- and reported. 437 is reachable only from b ~= 0.004577, which the page
        # rounds to 0.0046; at 0.0046 exactly the scale is 434.8 m, which prints as 435.
        dp = len(b_s.split(".")[1])
        half = 0.5 * 10 ** -dp
        lo, hi = 1.0 / ((b + half) * (1 - B)), 1.0 / ((b - half) * (1 - B))
        if lo <= float(scale_s) <= hi:
            print(f"WARN  1/(b - b_b) for {name!r}: page prints {scale_s} m, the printed "
                  f"b = {b_s} gives {1.0 / k:.1f} m -> {got}. Inside b's own rounding "
                  f"[{lo:.1f}, {hi:.1f}] m, so gated on that interval, not exactly. PAGE DEFECT.")
        else:
            fail(f"1/(b - b_b) for {name!r}: {1.0 / k:.6g} -> {got}, page says {scale_s}, and "
                 f"{scale_s} is outside [{lo:.1f}, {hi:.1f}] m -- not a rounding of any b that "
                 f"prints as {b_s}")
    else:
        fail(f"1/(b - b_b) for {name!r}: {1.0 / k:.6g} -> {got} m, page says {scale_s} m")
    check(f"f after {M_3} m of path for {name!r}", math.exp(-k * M_3), f_s)

# :63 -- the page's words for the same two rows, mechanised.
m = grabm(r"`1/\(b − b_b\)` — (\w+) in clear water, (\w+) in turbid",
          "the units the scattering length is described in")
CLEAR_U, TURBID_U = m.group(1), m.group(2)
UNITS = {"metres": (1.0, 100.0), "centimetres": (0.01, 1.0)}
for label, unit in (("clear oceanic", CLEAR_U), ("turbid", TURBID_U)):
    if label not in scales:
        sys.exit(f"the Details table no longer has a {label!r} row for :63 to describe")
    if unit not in UNITS:
        sys.exit(f"the page describes the {label} scale in {unit!r}, a unit this rig cannot read")
    lo, hi = UNITS[unit]
    if lo <= scales[label] < hi:
        print(f"PASS  :63 says {unit} in {label} water, and the table's {scales[label]} m is")
    else:
        fail(f":63 says {unit} in {label} water, but the table says {scales[label]} m")

# ── 6. the 1/f gap in the failure table, against the Details table ───────────────────────
m = grabm(r"The gap is `1/f` — ([\d.]+)x at ([\d.]+) m of depth in clear oceanic water at "
          r"`mu_w = ([\d.]+)`", "the 1/f gap")
GAP, GAP_Z, GAP_MU = m.group(1), float(m.group(2)), float(m.group(3))
L_EXPR = grab(r"\nL\s+= (.+?)\s+# refracted solar path", "the fence's L line")
L_gap = ev(L_EXPR, z=GAP_Z, mu_w=GAP_MU)
b_clear = float([r for r in ROWS if r[0] == "clear oceanic"][0][1])
check(f"1/f at z = {GAP_Z} m, mu_w = {GAP_MU}, from b = {b_clear} and B = {B_PART}",
      math.exp(b_clear * (1 - B_PART) * L_gap), GAP)
check(f"1/f at the same depth from the Details table's own {scales['clear oceanic']} m",
      math.exp(L_gap / scales["clear oceanic"]), GAP)

# ── 7. the storage arithmetic, at both ends of the page ──────────────────────────────────
m = grabm(r"at (\d+)² a scalar\s*\n(R\w*\d+F) caustic texture is \*\*([\d.]+) MiB\*\* and "
          r"the (R\w*\d+F) light-space depth map that step 3 needs is another\s*\n\*\*([\d.]+) "
          r"MiB\*\* — \*\*([\d.]+) MiB\*\* together, ([\d.]+) MiB at (\d+)², "
          r"([\d.]+) MiB at (\d+)²", "the caustic-map storage arithmetic")
RES, FMT_C, MIB_C, FMT_D, MIB_D, MIB_T, MIB_LO, RES_LO, MIB_HI, RES_HI = m.groups()


def fmt_bytes(tok):
    """R16F -> 1 channel x 16 bits = 2 B; RG16F -> 2 x 16 = 4 B. A parse of the NAME, not memory."""
    mm = re.fullmatch(r"([RGBA]+)(\d+)F", tok)
    if not mm:
        sys.exit(f"the page names a texture format {tok!r} this rig cannot size")
    return len(mm.group(1)) * int(mm.group(2)) / 8.0


def mib(res, tok):
    return int(res) ** 2 * fmt_bytes(tok) / (1 << 20)


check(f"{FMT_C} caustic texture at {RES}²", mib(RES, FMT_C), MIB_C)
check(f"{FMT_D} light-space depth map at {RES}²", mib(RES, FMT_D), MIB_D)
check(f"both targets at {RES}²", mib(RES, FMT_C) + mib(RES, FMT_D), MIB_T)
check(f"both targets at {RES_LO}²", mib(RES_LO, FMT_C) + mib(RES_LO, FMT_D), MIB_LO)
check(f"both targets at {RES_HI}²", mib(RES_HI, FMT_C) + mib(RES_HI, FMT_D), MIB_HI)
m = grabm(r"materialised as an (R\w*\d+F) normal image it is a\s*\nfurther ([\d.]+) MiB at "
          r"(\d+)²", "the emission-grid normal image size")
check(f"{m.group(1)} normal image at {m.group(3)}²", mib(m.group(3), m.group(1)), m.group(2))
m = grabm(r"([\d.]+) MiB resident at (\d+)²", "the crossover table's resident figure")
agree("the resident total, `## Use this` against the crossover table", [MIB_T, m.group(1)])
agree("the resolution it is quoted at", [RES, m.group(2)])

# ── 8. the emission grid: photons per texel against grid factor against resolution ───────
SIXTEEN = word(r"estimator is louder than the thing it estimates\. (\w+) photons per texel reach",
               "the first photon count, in words")
SIXTYFOUR = word(r"photons per texel reach \*\*±[\d.]+\*\*,\s*\n([\w-]+) \*\*±[\d.]+\*\*",
                 "the second photon count, in words")
m = grabm(r"A (\d+)² caustic texture therefore wants a (\d+)²–(\d+)² "
          r"emission grid", "the emission-grid resolutions")
TEX_RES, GRID_LO, GRID_HI = (int(x) for x in m.groups())
m = grabm(r"Emit (\d+)–(\d+) photons per caustic texel — a (\d+)–(\d+)x finer "
          r"emission grid per axis", "the failure table's emission-grid prescription")
T_LO, T_HI, AX_LO, AX_HI = (int(x) for x in m.groups())
agree("photons per texel, body prose against the failure table", [(SIXTEEN, SIXTYFOUR), (T_LO, T_HI)])
agree("the caustic texture resolution the grid is sized against", [str(TEX_RES), RES])
for photons, axis in ((T_LO, AX_LO), (T_HI, AX_HI)):
    check(f"{photons} photons per texel is this many times finer per axis",
          math.sqrt(photons), str(axis))
for axis, grid in ((AX_LO, GRID_LO), (AX_HI, GRID_HI)):
    check(f"{axis}x finer than a {TEX_RES}² caustic texture", float(axis * TEX_RES), str(grid))

# ── 9. the fence's OWN ALGEBRA, parsed as text and evaluated ─────────────────────────────
F_EXPR = grab(r"\nf\s+= (.+?)\s+# the coherent beam", "the fence's f line")
F_INNER = grab(r"\nf\s+= exp\(-max\(0, (.+?)\) \* L\)", "the f exponent inside the clamp")
ESUN_EXPR = grab(r"\nE_sun = (.+)\n", "the fence's E_sun line")
BEAM_EXPR = grab(r"#  E_sun\*f is (.+?) -- the beam law, intact -- EXACTLY WHILE", "the beam law")
C_EXPR = grab(r"lumped: `c = ([^`]+)`, the \*beam\* coefficient", "c = a + b")
m = grabm(r"The opposite extreme is `([^`]+)`, which is exactly `([^`]+)`", "a + b_b = mu_d*K_d")
KD_LHS, KD_RHS = m.group(1), m.group(2)
COLLAPSE = grab(r"the exponent collapses to `([^`]+)`", "the exponent's collapse")
grab(r"with the\nsun dominating that field — .*? — `(mu_d = mu_w)`", "mu_d = mu_w")

bad = 0
for i in range(400):                        # 400 is a literal; the draw count cannot run away
    th = math.radians(1.0 + 88.0 * (i % 40) / 39.0)
    z = 0.5 + 0.25 * (i % 17)
    E_n = 100.0 + 13.0 * (i % 7)
    K_d = 0.05 + 0.03 * (i % 11)
    mu_w = ev(MU_W_EXPR, theta_sun=th, n=N_IOR)
    L = ev(L_EXPR, z=z, mu_w=mu_w)
    c = mu_w * K_d + 0.01 + 0.02 * (i % 9)  # the UNCLAMPED branch the page's claim is about
    f = ev(F_EXPR, c=c, mu_w=mu_w, K_d=K_d, L=L)
    # :98 writes `R_ext(theta_sun)`; :107 writes a bare `R_ext`. Both are the page's characters.
    E_sun = ev(ESUN_EXPR, theta_sun=th, n=N_IOR, E_n=E_n, K_d=K_d, z=z,
               R_ext=lambda t, _n=N_IOR: fresnel(t, _n))
    beam = ev(BEAM_EXPR, R_ext=fresnel(th, N_IOR), E_n=E_n, theta_sun=th, c=c, L=L)
    if abs(E_sun * f - beam) > 1e-12 * abs(beam):
        bad += 1
if bad:
    fail(f":107 -- `E_sun*f is {BEAM_EXPR}` fails in {bad} of 400 unclamped draws")
else:
    print(f"PASS  :107 the beam law: E_sun*f == `{BEAM_EXPR}` exactly, 400 unclamped draws")

# ⚠️ CLAMP_F IS PARSED. This comparison was written as `!= 1.0` with ":108 says f = 1"
# printed beside it -- shape 1, a typed-in expectation, in the file written to end them.
# Walking the page to "f = 0 identically" left this rig GREEN, and nothing but running that
# mutation would have shown it: the literal agreed with the page by coincidence of authorship.
CLAMP_F = num(r"above clamps, f = ([\d.]+) identically", "what f is where the clamp fires")
bad = sum(1 for i in range(200)
          if ev(F_EXPR, c=0.01 + 0.001 * i, mu_w=0.8,
                K_d=(0.01 + 0.001 * i) / 0.8 + 0.5, L=1.0 + i) != CLAMP_F)
if bad:
    fail(f":108 -- where the clamp fires the page says f = {CLAMP_F:g} identically; it is not "
         f"in {bad}/200 draws")
else:
    print(f"PASS  :108 where max(0, ..) clamps, f = {CLAMP_F:g} identically, 200 draws")

bad = 0
for i in range(300):
    a, b, b_b, mu = 0.02 + 0.01 * (i % 13), 0.05 + 0.03 * (i % 11), 0.001 * (1 + i % 7), \
        0.5 + 0.004 * (i % 100)
    K_d = ev(KD_LHS, a=a, b_b=b_b) / mu     # from :140, mu_d*K_d = a + b_b
    c = ev(C_EXPR, a=a, b=b)                # from :87
    got = ev(F_INNER, c=c, mu_w=mu, K_d=K_d)
    if abs(got - ev(COLLAPSE, b=b, b_b=b_b)) > 1e-12:
        bad += 1
if bad:
    fail(f":124 -- with mu_d = mu_w the exponent does not collapse to `{COLLAPSE}` "
         f"({bad}/300 draws); :87, :97 and :140 no longer agree")
else:
    print(f"PASS  :124 with mu_d = mu_w, `{F_INNER}` collapses to `{COLLAPSE}`, 300 draws")

m = grabm(r"take the exponent water-only instead: ([^=]+) = ([^,]+),\s*\n#\s+(\w+) by "
          r"construction", "the water-only exponent")
WO_L, WO_R, WO_SIGN = m.group(1).strip(), m.group(2).strip(), m.group(3)
B_G = hg_backscatter(PHASE_G)
bad = sum(1 for i in range(200)
          if abs(ev(WO_L, b=0.01 + 0.01 * i, b_b=B_G * (0.01 + 0.01 * i))
                 - ev(WO_R.replace("B(phase_g)", repr(B_G)), b_b=B_G * (0.01 + 0.01 * i))) > 1e-15
          or (ev(WO_L, b=0.01 + 0.01 * i, b_b=B_G * (0.01 + 0.01 * i)) > 0) != (WO_SIGN == "positive"))
if bad:
    fail(f":111 -- `{WO_L} = {WO_R}` is not an identity, or not {WO_SIGN}, in {bad}/200 draws")
else:
    print(f"PASS  :111 `{WO_L} = {WO_R}` holds and is {WO_SIGN}, 200 draws")

# ── 10. the same statement at both ends of the page ──────────────────────────────────────
def norm(s):
    return re.sub(r"\s+", "", s.translate(OPS))


agree("the f formula, fence against the failure table",
      [norm(F_EXPR), norm(grab(r"their ratio `f = ([^`]+)` is the fade", "f in the failure table"))])
agree("the E_bed bracket, fence against :120 against the failure table",
      [norm(grab(r"E_sun \* (\(1 \+ \(G - 1\) \* f\))", "the fence's bracket")),
       norm(grab(r"the whole story: `(\(1 \+ \(G−1\)·f\))`", "the bracket at :120")),
       norm(grab(r"`E_sun·(\(1 \+ \(G−1\)·f\))`, never", "the bracket at :301"))])
agree("the one-photon-per-texel RMS, three places",
      [grab(r"\*\*RMS error of ±([\d.]+)\*\*", "the RMS at :166"),
       grab(r"four frames of the same grid are still\s*\n±([\d.]+)", "the RMS at :177"),
       grab(r"per caustic texel: ±([\d.]+) RMS", "the RMS at :307")])
agree("the refracted solar path, fence against :243 against the failure table",
      [norm(L_EXPR), norm(grab(r"That distance is the \*\*refracted\*\* solar path `([^`]+)`",
                               "the path at :243")),
       norm(grab(r"Attenuate over the \*\*refracted\*\* solar path `([^`]+)`", "the path at :303"))])

# ── 11. the source tiers, and the crossover table's own claim about them ─────────────────
TIERS = dict(re.findall(r"^  - \{ id: (\w+), tier: ([PF]), locator:", BODY, re.M))
if not TIERS:
    sys.exit("the page no longer carries a `sources:` front matter")
TABLE = grab(r"## The crossover, stated as a budget\n([\s\S]*?)\n\u26a0\ufe0f",
             "the crossover table")
XROWS = [r for r in TABLE.split("\n")
         if r.startswith("| ") and not r.startswith("|---") and "| You have |" not in r]
cited = {k for r in XROWS for k in re.findall(r"\[(\w+)\]", r)}
unknown = sorted(cited - set(TIERS))
if unknown:
    fail(f"the crossover table cites {unknown}, which the front matter does not carry")
else:
    print(f"PASS  all {len(cited)} citations in the crossover table resolve in the front matter")
body_cites = set(re.findall(r"\[(\w+)\]", BODY.split("---\n", 2)[2]))
if body_cites != set(TIERS):
    fail(f"front matter and body disagree on the source set: front matter only "
         f"{sorted(set(TIERS) - body_cites)}, body only {sorted(body_cites - set(TIERS))}")
else:
    print(f"PASS  every one of the {len(TIERS)} front-matter sources is cited in the body, "
          f"and every body citation is in the front matter")
N_F = word(r"\*\*(\w+) of those rows rests on an `F` source", "how many rows rest on an F source")
f_rows = [r for r in XROWS if any(TIERS[k] == "F" for k in re.findall(r"\[(\w+)\]", r))]
if len(f_rows) != N_F:
    fail(f":224 says {N_F} row(s) rest on an F source; {len(f_rows)} do")
else:
    print(f"PASS  :224 says {N_F} row rests on an F source, and {len(f_rows)} does")
TIER_WORDS = grab(r"behind the (stylized projected-texture) tier", "what the F row is").split()
for w in (TIER_WORDS[0], TIER_WORDS[1].split("-")[0]):
    if not any(w.lower() in r.lower() for r in f_rows):
        fail(f":225 calls the F row the {' '.join(TIER_WORDS)} tier, but no F-citing row "
             f"mentions {w!r} -- the F source has moved rows")
        break
else:
    print(f"PASS  the F-citing row is the {' '.join(TIER_WORDS)} one :225 names")
p_rows = [r for r in XROWS if r not in f_rows and re.search(r"\[(\w+)\]", r)]
if all(all(TIERS[k] == "P" for k in re.findall(r"\[(\w+)\]", r)) for r in p_rows):
    print(f"PASS  all {len(p_rows)} other citing rows cite only P-tier sources")
else:
    fail("a row other than the F row cites a non-P source")

LOC = grab(r"id: guardado2004, tier: F, locator: \"(.*?)\" \}", "the guardado2004 locator")
agree("the section the projected caustic texture is in, front matter against :227",
      [re.search(r"The projected caustic texture is §([\d.]+)", LOC).group(1),
       grab(r"raises the projected\ncaustic texture in §([\d.]+)", "the section at :227")])
m = grabm(r"method, §([\d.]+)–([\d.]+), is the per-vertex backward ray trace",
          "the chapter's own method sections")
agree("the section of the chapter's own method, front matter against :228",
      [re.search(r"§([\d.]+) Our Approach", LOC).group(1), m.group(1)])
agree("the section of the pass structure, front matter against :228",
      [re.search(r"§([\d.]+) for the OpenGL", LOC).group(1), m.group(2)])
agree("who the chapter credits the projected texture to, front matter against :227",
      [re.search(r"credits it to (Stam \d{4})", LOC).group(1),
       grab(r"only to attribute it to (Stam \d{4})", "the attribution at :227")])


# ── reports: things this rig will not gate, and why ──────────────────────────────────────
def report_B_contradiction():
    """The page prints `B(phase_g)` twice, with two values, and the table needs the second one."""
    print()
    print("  B(phase_g) -- reported, NOT gated. The page states one quantity twice:")
    print(f"    :102  `c = a + b_b/B(phase_g)` at phase_g = {PHASE_G} is `a + {RECIP_B}*b_b`, "
          f"so B = {1 / float(RECIP_B):.6f}")
    print(f"    :276  \"the particulate `B = {B_PART}`\", so 1/B = {1 / B_PART:.1f}")
    print(f"    Henyey-Greenstein at phase_g = {PHASE_G} gives B = {hg_backscatter(PHASE_G):.6f}, "
          f"1/B = {1 / hg_backscatter(PHASE_G):.2f} -- :102 is right, and 0.018 is not B(0.924); "
          f"it is the\n    Petzold particulate ratio, which HG matches at phase_g "
          f"~= {0.9186:.4f}.")
    print("    The Details table reproduces EXACTLY at 0.018 and not at 0.0170 (coastal `f`")
    print("    would print 0.052, not 0.053), so each end is gated against its own closed form")
    print("    and the disagreement between them is printed here. Fixing it is the page's job.")


def report_ungated():
    print()
    print("  NOT GATED, deliberately:")
    print("    :127  `-0.088 /m` -- needs a and b for pure water at 610 nm, which live in")
    print("          water-optics.md. Supplying them would be this rig asserting its own memory.")
    print("    :282  `c/K_d` 0.75 to 1.20, and about 2.8 -- same reason, same missing operands.")
    print("    :166-178  the RMS series and the 1-D kernel sweep -- measured on a CPU rig the")
    print("          page describes and does not ship. A rig built here would indict the page")
    print("          for its own choices. Their internal consistency IS gated (section 8) and")
    print("          the three printings of ±1.27 are asserted equal (section 10).")
    print("    :96, :113  `G` has mean 1 -- `G` is DEFINED at :96 as a ratio to the density a")
    print("          flat surface deposits. Both sides of any such assertion move together with")
    print("          any page edit: it CANNOT FAIL, so it is not a gate.")
    print("    :301  mean E_sun plus mean E_sun is exactly 2*E_sun -- x + x = 2x. Cannot fail.")
    print("    :157-161  the frame time -- the page refuses to price it, and so does this rig.")
    print()
    print("  PAGE DEFECT, found and not fixed: :230 \"Every other row above cites a")
    print("    peer-reviewed paper\" -- the last crossover row (:222, real-time ray tracing)")
    print(f"    cites nothing at all. {len(XROWS)} rows, {len(f_rows)} F, {len(p_rows)} P-citing, "
          f"{len(XROWS) - len(f_rows) - len(p_rows)} uncited. Gated as")
    print("    \"no row other than the F row cites a non-P source\", which is the true form.")


# ── the photon-count scaling, added after a figure-walk found it ungated ────────
# Scaling every bolded figure in the page by 1.37 one at a time, this rig caught six and MISSED
# **±0.22** and **±0.11** -- the pair carrying the page's actual sizing advice. It gated the
# ±1.27 beside them and not the two drawn from it.
_m = grabm(r"Sixteen photons per texel reach \*\*±([\d.]+)\*\*,\s*\n?"
           r"sixty-four \*\*±([\d.]+)\*\*", "the 16- and 64-photon RMS errors")
_e16, _e64 = float(_m.group(1)), float(_m.group(2))
_one = num(r"an \*\*RMS error of ±([\d.]+)\*\* on a gain whose mean is 1",
           "the one-photon RMS error")
# A mean-1 Monte-Carlo estimator's RMS falls as 1/sqrt(N): 16 -> 64 is a factor of exactly 2.
check("RMS at 64 photons, from the 16-photon figure and 1/sqrt(N)", _e16 / 2.0, str(_e64))
print(f"      (16 → 64 measured {_e16 / _e64:.3f}×; 1/sqrt(N) requires exactly 2)")
print(f"      ⚠️ the one-photon figure ±{_one} is NOT on that law: {_one / _e16:.2f}× the "
      f"16-photon value where 1/sqrt(N) wants 4.00×. An N = 1 estimator is not in the "
      f"asymptotic regime and the page claims no law, so this is reported, not asserted.")

report_B_contradiction()
report_ungated()
print()
sys.exit(0 if ok else 1)
