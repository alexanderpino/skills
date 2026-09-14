"""cd4 -- what the cross-class rejection test actually costs per candidate.

The document claimed it is O(1). It is not: with ONE grid at the largest class' d_max,
a 3x3 scan sweeps 9 * d_max^2 of ground, and the number of clasts in there is
density * 9 * d_max^2. Counted here, not argued.
"""
import math, random, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-skills/041d794d-2927-5ffb-83af-919282824aad/scratchpad/clasts')
from cd1_bridson import bridson

W = H = 10.0; SEED = 11; B = 2.5
CLASSES = [("boulder", 0.256, 1.024), ("cobble", 0.064, 0.256), ("pebble", 0.004, 0.064)]

def draw_d(rng, lo, hi, b):
    u = rng.random(); lo_b, hi_b = lo**(-b), hi**(-b)
    return (lo_b - u*(lo_b - hi_b))**(-1.0/b)

def run(per_class_grids):
    rng = random.Random(SEED)
    # one bucket map per class when per_class_grids, else a single map at 1.024
    if per_class_grids:
        cells = {c[0]: c[2] for c in CLASSES}           # each class' own d_max
    else:
        cells = {c[0]: 1.024 for c in CLASSES}
    buckets = {c[0]: {} for c in CLASSES}
    amax = {c[0]: c[2]/2 for c in CLASSES}
    tests = 0; kept = 0; cand = 0
    for cls, dlo, dhi in CLASSES:
        for p in bridson(W, H, dhi, k=30, seed=SEED + 17*[c[0] for c in CLASSES].index(cls))[0]:
            cand += 1
            a = draw_d(rng, dlo, dhi, B)/2.0
            ok = True
            for ocls in buckets:
                gc = cells[ocls]
                # scan radius must cover a + a_max(ocls); in cells of size gc that is
                reach = int(math.ceil((a + amax[ocls]) / gc))
                bx, by = int(p[0]/gc), int(p[1]/gc)
                for yy in range(by-reach, by+reach+1):
                    for xx in range(bx-reach, bx+reach+1):
                        for q in buckets[ocls].get((xx, yy), ()):
                            tests += 1
                            if math.hypot(q[0]-p[0], q[1]-p[1]) < q[2] + a:
                                ok = False; break
                        if not ok: break
                    if not ok: break
                if not ok: break
            if ok:
                buckets[cls].setdefault((int(p[0]/cells[cls]), int(p[1]/cells[cls])), []).append((p[0],p[1],a))
                kept += 1
    return cand, kept, tests

for label, pcg in (("ONE grid at the largest class' d_max", False),
                   ("one grid PER CLASS, at that class' d_max", True)):
    cand, kept, tests = run(pcg)
    print(f"{label}")
    print(f"   candidates {cand:>6}  kept {kept:>6}  pairwise tests {tests:>10,}  "
          f"{tests/cand:9.1f} per candidate")
print()
print("== the arithmetic the measurement is checking ==")
dens = 13338/100.0
print(f"  final density {dens:.2f} clasts/m^2")
print(f"  one grid: 3x3 cells of 1.024 m = {9*1.024**2:.2f} m^2 -> {dens*9*1.024**2:,.0f} clasts in reach")
