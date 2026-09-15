"""cd3 -- the instance budget. Exact arithmetic on the cd2 measurements.

Measured on a 10 x 10 m patch, stratified largest-first, seed 11, exponent b = 2.5:
    boulder  67, cobble 840, pebble 12431, TOTAL 13338, 0 interpenetrating pairs.
"""
COUNTS = {"boulder": 67, "cobble": 840, "pebble": 12431}
PATCH = 100.0          # m^2
TOTAL = sum(COUNTS.values())

# One instance, the smallest honest transform an engine can carry per scattered rock:
#   position   3 x float32                        12 B
#   rotation   1 packed quaternion (uint32)        4 B
#   scale      1 x float32                         4 B
#   mesh id    1 x uint16 + 2 B pad                4 B
BYTES = 12 + 4 + 4 + 4
print(f"one instance = {BYTES} bytes (pos 3xf32, quat packed u32, scale f32, mesh id u16+pad)")
print()
print(f"{'class':<9}{'per patch':>10}{'per m^2':>10}{'per km^2':>14}{'bytes/km^2':>14}{'':>4}")
for cls, n in COUNTS.items():
    per_m2 = n / PATCH
    per_km2 = per_m2 * 1e6
    b = per_km2 * BYTES
    print(f"{cls:<9}{n:>10}{per_m2:>10.2f}{per_km2:>14,.0f}{b/1e6:>12.1f} MB")
per_m2 = TOTAL / PATCH
per_km2 = per_m2 * 1e6
print(f"{'TOTAL':<9}{TOTAL:>10}{per_m2:>10.2f}{per_km2:>14,.0f}{per_km2*BYTES/1e9:>12.2f} GB")
print()
cum = 0
for cls in ("boulder", "cobble", "pebble"):
    cum += COUNTS[cls]
    print(f"  down to {cls:<8}: {cum/PATCH*1e6:>13,.0f} instances/km^2 = "
          f"{cum/PATCH*1e6*BYTES/1e6:>9.1f} MB")
print()
print("== density error: sizing r from the hexagonal packing bound ==")
# measured: N / hexbound = 0.608, 0.547, 0.538 at r = 1.024, 0.256, 0.064
for r, N, hexb in ((1.024, 67, 110), (0.256, 964, 1762), (0.064, 15153, 28191)):
    print(f"  r={r:<7} N={N:<7} bound={hexb:<7} achieved {100*N/hexb:5.1f}%  "
          f"-> a count planned off the bound comes out {100*(1 - N/hexb):4.1f}% low")
print()
print("== budget error: planning per-class passes independently ==")
CAND = {"boulder": 67, "cobble": 961, "pebble": 15075}
tot_c = sum(CAND.values())
print(f"  independent per-class Poisson passes predict {tot_c:,} clasts")
print(f"  stratified rejection against the earlier classes yields {TOTAL:,}")
print(f"  a budget planned that way comes out {100*(tot_c-TOTAL)/tot_c:.1f}% high")
print()
print("== ground coverage, from the same run ==")
print("  17.60% of the patch is under a clast at b = 2.5")
