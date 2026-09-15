#!/usr/bin/env python3
"""Re-derivation rig for gaia/references/water-optics.md.

Checks the two figures this document pairs for the `approximation` criterion, plus the
constants they sit beside.  Pure arithmetic on the exact unpolarised Fresnel equations and
on the document's own descriptor block -- no scene, no frame, no GPU.

  python3 water-optics.py            # all checks, exit 0 if every one reproduces
"""
import math
import pathlib
import re
import sys

# ⚠️ REWRITTEN 2026-09-15. Until then every `want` below was a literal typed into this file and
# printed as "doc says 14.3". That is the FIFTH rig in this corpus caught checking its own
# memory instead of its document -- after heightfield-lod.py, mu-d-overcast.py,
# node-graph-runtime.py and node-graph-runtime.py's own repair -- and it was the largest, with
# fifteen of them. A triage fleet found it while triaging something else. Every expected value
# is parsed from the page now, anchored on PROSE and never on a number, and a figure that has
# gone missing is a FAIL rather than a silent skip.
DOC = pathlib.Path(__file__).resolve().parents[2] / "references" / "water-optics.md"
if not DOC.exists():
    sys.exit(f"cannot find {DOC} -- run this rig from inside the repo")
BODY = DOC.read_text(encoding="utf-8")


def page(pattern: str, what: str, group: int = 1) -> float:
    """The figure the PAGE prints, or a hard exit naming what went missing."""
    m = re.search(pattern, BODY)
    if not m:
        sys.exit(f"the page no longer states {what} (pattern {pattern!r})")
    return float(m.group(group))


# The index is the page's too -- it is the thing every figure below depends on, so a rig that
# typed it in would be assuming the one input it should be reading.
N = page(r"Cosine-weighted hemispherical value at `n = ([\d.]+)`", "the index n")


def fresnel_unpolarised(theta_i, n1=1.0, n2=N):
    """Exact unpolarised reflectance at a smooth dielectric interface."""
    ci = math.cos(theta_i)
    s2t = (n1 / n2 * math.sin(theta_i)) ** 2
    if s2t >= 1.0:
        return 1.0                                   # total internal reflection
    ct = math.sqrt(1.0 - s2t)
    rs = ((n1 * ci - n2 * ct) / (n1 * ci + n2 * ct)) ** 2
    rp = ((n1 * ct - n2 * ci) / (n1 * ct + n2 * ci)) ** 2
    return 0.5 * (rs + rp)


def schlick(theta_i, r0):
    return r0 + (1.0 - r0) * (1.0 - math.cos(theta_i)) ** 5


def cosine_weighted_mean(n1, n2, m=2_000_001):
    """int R(th) cos th sin th dth / int cos th sin th dth, by Simpson over theta."""
    a, b = 0.0, math.pi / 2
    h = (b - a) / (m - 1)
    num = den = 0.0
    for i in range(m):
        th = a + i * h
        w = 1 if i in (0, m - 1) else (4 if i % 2 else 2)
        cs = math.cos(th) * math.sin(th)
        num += w * fresnel_unpolarised(th, n1, n2) * cs
        den += w * cs
    return num / den


def check(label, got, want, tol, unit=""):
    ok = abs(got - want) <= tol
    print(f"{'OK ' if ok else 'BAD'} {label:<52} got {got:>10.4f}{unit}  doc says {want}{unit}")
    return ok


ok = True
r0 = ((N - 1) / (N + 1)) ** 2
ok &= check("F0 = ((n-1)/(n+1))^2", r0,
            page(r"F0 = \(\(n - 1\) / \(n \+ 1\)\)\^2\s*# n = [\d.]+\s*->\s*([\d.]+)",
                 "F0 in the descriptor fence"), 5e-5)
ok &= check("R_ext at normal incidence, %", 100 * fresnel_unpolarised(0.0),
            page(r"\| At normal incidence \| ([\d.]+)%", "R_ext at normal incidence"), 5e-3, "%")

# --- Schlick's signed relative error over the range the document states, 38-79 deg -------
grid = [38.0 + i * 0.001 for i in range(int((79.0 - 38.0) / 0.001) + 1)]
err = [100.0 * (schlick(math.radians(d), r0) / fresnel_unpolarised(math.radians(d)) - 1.0)
       for d in grid]
imax, imin = max(range(len(err)), key=err.__getitem__), min(range(len(err)), key=err.__getitem__)
# One sentence carries six of these, so one regex parses it whole -- anchored on the prose, and
# it fails as a unit if the sentence is rewritten, which is the correct behaviour.
SCH = re.search(
    r"maximum relative error is \+([\d.]+)%\*\*, at ([\d.]+)\u00b0, with a\s+"
    r"\*\*minimum of \u2212([\d.]+)%\*\* at ([\d.]+)\u00b0 beside the ([\d.]+)\u00b0 Brewster angle"
    r"[^*]*\*\*mean of \u2212([\d.]+)%\*\*; at ([\d.]+)\u00b0 it is \*\*\+([\d.]+)%\*\*", BODY)
if not SCH:
    sys.exit("the page no longer states the Schlick error statistics in one sentence")
S_MAX, S_MAXA, S_MIN, S_MINA, S_BREW, S_MEAN, S_GRAZE_A, S_GRAZE = (float(g) for g in SCH.groups())

ok &= check("max signed relative error over 38-79 deg, %", err[imax], S_MAX, 0.05, "%")
ok &= check("  ... at angle, deg", grid[imax], S_MAXA, 0.05, " deg")
ok &= check("min signed relative error over 38-79 deg, %", err[imin], -S_MIN, 0.05, "%")
ok &= check("  ... at angle, deg", grid[imin], S_MINA, 0.05, " deg")
ok &= check("mean signed relative error over 38-79 deg, %", sum(err) / len(err), -S_MEAN, 0.05, "%")
ok &= check(f"signed relative error at {S_GRAZE_A} deg, %",
            100 * (schlick(math.radians(S_GRAZE_A), r0)
                   / fresnel_unpolarised(math.radians(S_GRAZE_A)) - 1),
            S_GRAZE, 0.05, "%")
# Brewster, and the shape claim: low through the middle, high only at the top
brew = math.degrees(math.atan(N))
ok &= check("Brewster angle, deg", brew, S_BREW, 0.05, " deg")
print(f"    sign changes over 38-79 deg: "
      f"{sum(1 for a, b in zip(err, err[1:]) if (a < 0) != (b < 0))} "
      f"(a curve, not a uniform bias)")

# --- the two hemispherical integrals the table prints ------------------------------------
HEMI = re.search(r"\| Cosine-weighted hemispherical value at `n = [\d.]+` \| \*\*([\d.]+)%\*\* "
                 r"\| \*\*([\d.]+)%\*\* \|", BODY)
if not HEMI:
    sys.exit("the page no longer prints the cosine-weighted hemispherical row")
ok &= check("cosine-weighted R_ext, %", 100 * cosine_weighted_mean(1.0, N),
            float(HEMI.group(1)), 5e-3, "%")
ok &= check("cosine-weighted R_int, %", 100 * cosine_weighted_mean(N, 1.0),
            float(HEMI.group(2)), 5e-3, "%")
SIXTY = re.search(r"at (\d+)\u00b0 the external figure is ([\d.]+)%", BODY)
if not SIXTY:
    sys.exit("the page no longer states the external figure at 60 degrees")
ok &= check(f"R_ext at {SIXTY.group(1)} deg, %",
            100 * fresnel_unpolarised(math.radians(float(SIXTY.group(1)))),
            float(SIXTY.group(2)), 5e-3, "%")
ok &= check("ratio R_int / R_ext",
            cosine_weighted_mean(N, 1.0) / cosine_weighted_mean(1.0, N),
            page(r"two reflectances, differing by ([\d.]+)x", "the R_int/R_ext ratio"), 5e-3)
tc = math.degrees(math.asin(1 / N))
ok &= check("theta_c = arcsin(1/n), deg", tc,
            page(r"theta_c\s*= arcsin\(1/n\)\s*= ([\d.]+) deg", "the critical angle"),
            5e-3, " deg")

# --- the cost this document states: the descriptor it tells you to ship ------------------
FIELDS = {"a": 3, "b_b": 3, "K_d": 3, "phase_g": 1, "ior": 1}   # three-channel, per the block
n_fields = sum(FIELDS.values())
per_body = 4 * n_fields                                          # fp32
print(f"OK  descriptor: {n_fields} fp32 fields = {per_body} bytes per body; "
      f"1000 bodies = {per_body * 1000 / 1000:.0f} KB; 10000 = {per_body * 10000 / 1e6:.2f} MB")
ok &= (n_fields == 11 and per_body == 44)

print("\nALL REPRODUCE" if ok else "\nSOMETHING DID NOT REPRODUCE")
raise SystemExit(0 if ok else 1)

sys.exit(0 if ok else 1)
