#!/usr/bin/env python3
"""Re-derivation rig for gaia/references/water-optics.md.

Checks the two figures this document pairs for the `approximation` criterion, plus the
constants they sit beside.  Pure arithmetic on the exact unpolarised Fresnel equations and
on the document's own descriptor block -- no scene, no frame, no GPU.

  python3 water-optics.py            # all checks, exit 0 if every one reproduces
"""
import math

N = 1.335                      # the one index this document uses throughout


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
ok &= check("F0 = ((n-1)/(n+1))^2", r0, 0.0206, 5e-5)
ok &= check("R_ext at normal incidence, %", 100 * fresnel_unpolarised(0.0), 2.06, 5e-3, "%")

# --- Schlick's signed relative error over the range the document states, 38-79 deg -------
grid = [38.0 + i * 0.001 for i in range(int((79.0 - 38.0) / 0.001) + 1)]
err = [100.0 * (schlick(math.radians(d), r0) / fresnel_unpolarised(math.radians(d)) - 1.0)
       for d in grid]
imax, imin = max(range(len(err)), key=err.__getitem__), min(range(len(err)), key=err.__getitem__)
ok &= check("max signed relative error over 38-79 deg, %", err[imax], 14.3, 0.05, "%")
ok &= check("  ... at angle, deg", grid[imax], 78.9, 0.05, " deg")
ok &= check("min signed relative error over 38-79 deg, %", err[imin], -22.8, 0.05, "%")
ok &= check("  ... at angle, deg", grid[imin], 51.3, 0.05, " deg")
ok &= check("mean signed relative error over 38-79 deg, %", sum(err) / len(err), -8.9, 0.05, "%")
ok &= check("signed relative error at 83.8 deg, %",
            100 * (schlick(math.radians(83.8), r0) / fresnel_unpolarised(math.radians(83.8)) - 1),
            11.4, 0.05, "%")
# Brewster, and the shape claim: low through the middle, high only at the top
brew = math.degrees(math.atan(N))
ok &= check("Brewster angle, deg", brew, 53.2, 0.05, " deg")
print(f"    sign changes over 38-79 deg: "
      f"{sum(1 for a, b in zip(err, err[1:]) if (a < 0) != (b < 0))} "
      f"(a curve, not a uniform bias)")

# --- the two hemispherical integrals the table prints ------------------------------------
ok &= check("cosine-weighted R_ext, n = 1.335, %", 100 * cosine_weighted_mean(1.0, N), 6.67, 5e-3, "%")
ok &= check("cosine-weighted R_int, n = 1.335, %", 100 * cosine_weighted_mean(N, 1.0), 47.63, 5e-3, "%")
ok &= check("R_ext at 60 deg, %", 100 * fresnel_unpolarised(math.radians(60)), 6.01, 5e-3, "%")
ok &= check("ratio R_int / R_ext",
            cosine_weighted_mean(N, 1.0) / cosine_weighted_mean(1.0, N), 7.14, 5e-3)
tc = math.degrees(math.asin(1 / N))
ok &= check("theta_c = arcsin(1/n), deg", tc, 48.51, 5e-3, " deg")

# --- the cost this document states: the descriptor it tells you to ship ------------------
FIELDS = {"a": 3, "b_b": 3, "K_d": 3, "phase_g": 1, "ior": 1}   # three-channel, per the block
n_fields = sum(FIELDS.values())
per_body = 4 * n_fields                                          # fp32
print(f"OK  descriptor: {n_fields} fp32 fields = {per_body} bytes per body; "
      f"1000 bodies = {per_body * 1000 / 1000:.0f} KB; 10000 = {per_body * 10000 / 1e6:.2f} MB")
ok &= (n_fields == 11 and per_body == 44)

print("\nALL REPRODUCE" if ok else "\nSOMETHING DID NOT REPRODUCE")
raise SystemExit(0 if ok else 1)
