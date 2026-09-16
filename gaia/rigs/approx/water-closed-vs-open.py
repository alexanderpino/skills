#!/usr/bin/env python3
"""Re-derivation of every figure gaia/references/water-closed-vs-open.md's
approximation pair rests on.

RIG: CPython 3 double-precision arithmetic, closed forms only.  Deterministic,
no seed, no randomness.  WHAT THIS IS NOT: nothing here is timed.  There is no
benchmark, no runtime, no GPU frame cost in this file.  The MB/GB figures are a
STORAGE COUNT -- cells * bytes-per-cell -- not a measured allocation.
"""
from math import pi, sqrt, exp

sigma, rho, g, nu = 0.0728, 1000.0, 9.81, 1.0e-6   # N/m, kg/m^3, m/s^2, m^2/s

def omega(k):  return sqrt(g * k + sigma * k**3 / rho)
def cg(k):     return (g + 3 * sigma * k**2 / rho) / (2 * omega(k))
def efold(lam):                       # Lamb tau = 1/(2 nu k^2); distance = cg * tau
    k = 2 * pi / lam
    return cg(k) / (2 * nu * k**2)

print("== capillary-gravity constants (document lines 68-71) ==")
c_min = (4 * g * sigma / rho) ** 0.25
lam_min = 2 * pi * sqrt(sigma / (rho * g))
print(f"c_min   = {c_min:.6f} m/s      printed 0.2312")
print(f"lam_min = {lam_min:.6f} m      printed 0.01712")

print("\n== the circulating pair 23.1 cm/s at 1.73 cm (document line 73-76) ==")
s_from_c = rho * 0.231**4 / (4 * g)
s_from_l = rho * g * (0.0173 / (2 * pi))**2
print(f"sigma from 0.231 m/s  = {s_from_c:.7f} N/m")
print(f"sigma from 0.0173 m   = {s_from_l:.7f} N/m")
print(f"apart                 = {100*(s_from_l/s_from_c - 1):.3f} %   printed 2.5%")

print("\n== e-folding distances, Lamb clean surface (document lines 130-136, 142) ==")
for lam, printed in ((0.165, 90.0), (0.05, 5.7), (0.03, 2.0)):
    L = efold(lam)
    print(f"lam={lam*100:5.1f} cm  L = {L:10.5f} m   printed {printed:5.1f} m"
          f"   printed is {100*(printed/L - 1):+7.3f} %")
L165, L5, L3 = efold(0.165), efold(0.05), efold(0.03)
print(f"L(16.5cm)/8 m pool    = {L165/8:.2f} lengths        printed 'eleven'")
print(f"exp(-8/L5)            = {exp(-8/L5)*100:.2f} %             printed 24%")
print(f"exp(-1/L5)            = {exp(-1/L5)*100:.2f} %             printed 84%")
print(f"exp(-8/L165)          = {exp(-8/L165)*100:.2f} %             printed 91%")
print(f"far-wall contrast     = {exp(-8/L165)/exp(-8/L5):.4f} x            printed 'about 4x'")
print(f"e^-1                  = {exp(-1)*100:.2f} %             printed 37%")

print("\n== AUDIT-2026-09-05 X30: inextensible-film term, damping x20 (PLAUSIBLE, unverified) ==")
print(f"L(16.5 cm)/20         = {L165/20:.4f} m           audit prints ~4.4 m")
print(f"                        = {L165/20/8:.3f} pool lengths")

print("\n== storage floor: one fp32 height per cell, 2 samples per 5 cm wavelength ==")
cell = 0.05 / 2
BPC = 4                                    # bytes per cell, fp32 height, nothing else
for name, extent in (("closed: 8 m pool", 8.0), ("open: 1 km patch", 1000.0)):
    n = round(extent / cell)
    cells = n * n
    b = cells * BPC
    print(f"{name:18s} cell {cell*100:.1f} cm  {n} x {n} = {cells:,} cells"
          f"  -> {b:,} B = {b/1e6:.4f} MB = {b/1e9:.4f} GB")
n_c, n_o = round(8.0/cell), round(1000.0/cell)
print(f"ratio                = {(n_o/n_c)**2:,.0f} x   ( = (1000/8)^2 = {125**2} )")
