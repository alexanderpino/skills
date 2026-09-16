#!/usr/bin/env python3
"""What the linear-light rule in mask-to-material.md COSTS, in bytes.

The document already prices how GOOD the recommendation is (dE00 up to 16.35, luminance
48.2% too dark, at :341). It never prices what it costs. This script computes the cost
side, and nothing else.

WHAT THE RIG IS, for sections A and B -- the only two that feed the page: exact
integer/format arithmetic. Bit layouts and IEEE-754 enumeration. No RNG, no seed, no wall
clock, no timing of any kind.
WHAT IT IS NOT: not a GPU measurement, not a bandwidth measurement, not a frame cost.
Every number A and B print is a STORAGE FOOTPRINT or a representable-level count -- the
same integer on every machine, which does not drift with container load. Do not print any
of it as a frame cost.

Sections C and D ARE Monte Carlo and DO use a seeded RNG (seeds in the code). They are
diagnostics; nothing they print goes on the page.

Section C is a DIAGNOSTIC ONLY, not a source for any figure on the page: it re-derives the
absent-material leak of the additive bias, because the body (:240) says 18.9% at Sum w = 0.5
and the failure table (:378) says 19.3% for what reads as the same quantity.
"""
import numpy as np

# --- A. bytes per cell, from bit layouts -------------------------------------------------
# Channel layouts as bit widths. RGBA8 UNORM, R11G11B10F (GL_EXT_packed_float / DXGI
# R11G11B10_FLOAT), RGBA16F (IEEE-754 binary16 x 4).
FORMATS = {
    "RGBA8 UNORM":   (8, 8, 8, 8),
    "R11G11B10F":    (11, 11, 10, 0),
    "RGBA16F":       (16, 16, 16, 16),
    "R8 UNORM":      (8, 0, 0, 0),
}
RES = 4096  # the resolution this corpus prices footprints at (coastal-erosion.md, flow-routing.md)
LUT_ENTRIES = 32  # the ramp length the document's palette table measures

print("=== A. bytes per cell (exact: sum of channel bit widths / 8) ===")
bpc = {}
for name, bits in FORMATS.items():
    total_bits = sum(bits)
    assert total_bits % 8 == 0, (name, total_bits)
    b = total_bits // 8
    bpc[name] = b
    mib = b * RES * RES / (1024 ** 2)
    print(f"  {name:<14} {total_bits:>2} bits = {b} bytes per cell"
          f"   |  {mib:8.1f} MiB at {RES}^2  |  {b * LUT_ENTRIES:>4} bytes for a {LUT_ENTRIES}-entry LUT")

print()
print("=== A2. the deltas the page states ===")
print(f"  RGBA16F - RGBA8      = {bpc['RGBA16F'] - bpc['RGBA8 UNORM']} bytes per cell"
      f"  (ratio {bpc['RGBA16F'] / bpc['RGBA8 UNORM']:.0f}x)")
print(f"  R11G11B10F - RGBA8   = {bpc['R11G11B10F'] - bpc['RGBA8 UNORM']} bytes per cell"
      f"  (ratio {bpc['R11G11B10F'] / bpc['RGBA8 UNORM']:.0f}x)")
print(f"  {LUT_ENTRIES}-entry LUT, RGBA16F - RGBA8 = "
      f"{(bpc['RGBA16F'] - bpc['RGBA8 UNORM']) * LUT_ENTRIES} bytes total")
print(f"  {LUT_ENTRIES}-entry LUT, R11G11B10F - RGBA8 = "
      f"{(bpc['R11G11B10F'] - bpc['RGBA8 UNORM']) * LUT_ENTRIES} bytes total")

# --- B. WHY 8-bit linear is not an option: representable levels in the dark third --------
# The document measures dE00 2.13 per LSB for an 8-bit LINEAR LUT and a median 0.94 across
# L* < 33. This is the mechanism behind that, and it needs no colour-difference formula.
# sRGB transfer function: icc_srgb sec A.8 encode / Part B decode, as printed at :306-:311.
def srgb_encode(L):
    return np.where(L <= 0.0031308, 12.92 * L, 1.055 * np.power(L, 1 / 2.4) - 0.055)

# CIELAB L* -> relative luminance Y (the standard inverse, L* > 8 branch).
L_DARK = 33.0
Y_DARK = ((L_DARK + 16.0) / 116.0) ** 3

print()
print("=== B. representable levels at or below L* = 33 (Y <= %.6f) ===" % Y_DARK)

# 8-bit linear UNORM: codes c/255 that are <= Y_DARK.
lin8 = int(np.floor(Y_DARK * 255)) + 1
# 8-bit sRGB UNORM: codes whose DECODED linear value is <= Y_DARK.
srgb8 = int(np.floor(float(srgb_encode(np.array(Y_DARK))) * 255)) + 1

def small_float_levels(exp_bits, man_bits, ceiling):
    """Count distinct non-negative representable values in [0, ceiling] for an unsigned
    packed float with the given exponent/mantissa widths and the IEEE bias 2^(e-1)-1."""
    bias = (1 << (exp_bits - 1)) - 1
    vals = {0.0}
    for e in range(0, (1 << exp_bits) - 1):        # exclude the all-ones (inf/nan) exponent
        for m in range(0, 1 << man_bits):
            if e == 0:
                v = (m / (1 << man_bits)) * 2.0 ** (1 - bias)   # subnormal
            else:
                v = (1.0 + m / (1 << man_bits)) * 2.0 ** (e - bias)
            if v <= ceiling:
                vals.add(v)
    return len(vals)

f11 = small_float_levels(5, 6, Y_DARK)   # R11/G11 channel
f10 = small_float_levels(5, 5, Y_DARK)   # B10 channel
f16 = int(np.sum(np.unique(np.frombuffer(
    np.arange(0, 0x7C00, dtype=np.uint16).tobytes(), dtype=np.float16)) <= Y_DARK))

print(f"  8-bit LINEAR  UNORM : {lin8:>6} levels")
print(f"  8-bit sRGB    UNORM : {srgb8:>6} levels   ({srgb8 / lin8:.1f}x the linear count)")
print(f"  10-bit float (B10)  : {f10:>6} levels")
print(f"  11-bit float (R/G11): {f11:>6} levels")
print(f"  16-bit float (fp16) : {f16:>6} levels")
print("  -> an 8-bit LINEAR buffer spends %d codes on the dark third that terrain is made of;"
      % lin8)
print("     the same 8 bits encoded sRGB spends %d. That is the whole of the banding story," % srgb8)
print("     and it is why the linear rule forces a wider format wherever the result is STORED.")

# --- C. DIAGNOSTIC ONLY: the absent-material leak, additive bias -------------------------
# Not a source for anything printed on the page. Body :240 says 18.9% at Sum w = 0.5;
# failure table :378 says 19.3%. Reported, not resolved from here.
print()
print("=== C. DIAGNOSTIC ONLY (not printed on the page): additive-bias leak ===")
rng = np.random.default_rng(20260914)   # seed fixed so this diagnostic reproduces
N, DEPTH = 4_000_000, 0.1
for sumw in (1.0, 0.5):
    # material A has weight exactly 0; B and C share sumw, flat Dirichlet over the present two
    g = rng.gamma(1.0, 1.0, size=(N, 2))
    w = np.zeros((N, 3))
    w[:, 1:] = sumw * g / g.sum(axis=1, keepdims=True)
    h = rng.random((N, 3))
    b = w + h                                   # the ADDITIVE bias, as [mishkinis2013] prints it
    m = b.max(axis=1) - DEPTH
    leak = float(np.mean(b[:, 0] > m))
    print(f"  Sum w = {sumw}, depth = {DEPTH}: {100 * leak:.2f}% of texels give the w=0 material a share"
          f"   (N = {N:,})")
print("  body :240 states 4.3% / 18.9%; failure table :378 states 19.3% for the Sum w = 0.5 end.")

# --- D. DIAGNOSTIC ONLY: does the leak figure depend on the seed, or on depth? -----------
print()
print("=== D. DIAGNOSTIC ONLY: seed sensitivity and depth sweep for section C ===")
for seed in (1, 2, 3, 20260914):
    r = np.random.default_rng(seed)
    n = 2_000_000
    row = []
    for sumw in (1.0, 0.5):
        g = r.gamma(1.0, 1.0, size=(n, 2))
        w = np.zeros((n, 3)); w[:, 1:] = sumw * g / g.sum(axis=1, keepdims=True)
        b = w + r.random((n, 3))
        row.append(100 * float(np.mean(b[:, 0] > b.max(axis=1) - 0.1)))
    print("  seed %-9d depth 0.1 -> Sum w = 1: %.3f%%   Sum w = 0.5: %.3f%%" % (seed, *row))
r = np.random.default_rng(7); n = 2_000_000
g = r.gamma(1.0, 1.0, size=(n, 2))
w = np.zeros((n, 3)); w[:, 1:] = 0.5 * g / g.sum(axis=1, keepdims=True)
b = w + r.random((n, 3))
for d in (0.09, 0.10, 0.11, 0.12, 0.20):
    print("  depth %.2f -> %.2f%% at Sum w = 0.5" % (d, 100 * float(np.mean(b[:, 0] > b.max(axis=1) - d))))
print("  CONCLUSION: the body's 4.3 / 18.9 / 26.5 all reproduce; 19.3% matches no depth and no")
print("  form in this document. The failure table end is the stale one.")
