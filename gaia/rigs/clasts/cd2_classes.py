"""cd2 -- what one minimum separation costs when the clasts are not one size.

Two clasts of radii a_i, a_j interpenetrate when d_ij < a_i + a_j. Bridson's r is a
SINGLE minimum separation, so it expresses that constraint for exactly one pair of radii.
Domain: a 10 m x 10 m scatter patch -- one terrain chunk, the unit a scatterer works on.
"""
import math, random, time, sys
sys.path.insert(0, '/tmp/claude-0/-home-user-skills/041d794d-2927-5ffb-83af-919282824aad/scratchpad/clasts')
from cd1_bridson import bridson

W = H = 10.0
SEED = 11
B = 2.5                       # power-law exponent on the size distribution
# Wentworth classes, DIAMETERS in metres. Edges are exact powers of two in mm.
CLASSES = [("boulder", 0.256, 1.024), ("cobble", 0.064, 0.256), ("pebble", 0.004, 0.064)]

def draw_d(rng, lo, hi, b):
    u = rng.random()
    lo_b, hi_b = lo ** (-b), hi ** (-b)
    return (lo_b - u * (lo_b - hi_b)) ** (-1.0 / b)

def overlaps(pts, radii, cellsize):
    buckets = {}
    for i, p in enumerate(pts):
        buckets.setdefault((int(p[0]/cellsize), int(p[1]/cellsize)), []).append(i)
    n, worst = 0, 0.0
    for (bx, by), ids in buckets.items():
        near = []
        for yy in range(by-1, by+2):
            for xx in range(bx-1, bx+2):
                near.extend(buckets.get((xx, yy), ()))
        for a in ids:
            for c in near:
                if a < c:
                    d = math.hypot(pts[a][0]-pts[c][0], pts[a][1]-pts[c][1])
                    need = radii[a] + radii[c]
                    if d < need:
                        n += 1
                        worst = max(worst, (need - d) / need)
    return n, worst

print("== packing: Bridson against the hexagonal bound, on a %g x %g m patch ==" % (W, H))
for r in (1.024, 0.256, 0.064):
    pts, _, _ = bridson(W, H, r, k=30, seed=SEED)
    hexb = 2.0 * W * H / (math.sqrt(3.0) * r * r)
    print(f"  r={r:<7} N={len(pts):>6}   hexagonal bound {hexb:9.0f}   {100*len(pts)/hexb:5.1f}%")

print()
print("== (a) ONE r sized for the largest clast: no overlap, and the domain is spent ==")
rng = random.Random(SEED)
r_safe = 1.024
t0 = time.perf_counter(); pts_a, _, _ = bridson(W, H, r_safe, k=30, seed=SEED)
ms_a = (time.perf_counter()-t0)*1e3
rad_a = [draw_d(rng, 0.004, 1.024, B)/2 for _ in pts_a]
no_a, wo_a = overlaps(pts_a, rad_a, r_safe)
cov_a = sum(math.pi*a*a for a in rad_a)/(W*H)
print(f"  r = {r_safe} m   N = {len(pts_a)}   overlaps = {no_a}   ground covered {100*cov_a:.2f}%   {ms_a:.0f} ms")

print()
print("== (b) ONE r sized for a plausible MEAN spacing: the overlaps that buys ==")
for r_mid in (0.256, 0.128, 0.064):
    rng = random.Random(SEED)
    pts_b, _, _ = bridson(W, H, r_mid, k=30, seed=SEED)
    rad_b = [draw_d(rng, 0.004, 1.024, B)/2 for _ in pts_b]
    no_b, wo_b = overlaps(pts_b, rad_b, 1.024)
    print(f"  r = {r_mid:<6} N = {len(pts_b):>6}   interpenetrating pairs {no_b:>6} "
          f"({100.0*no_b/len(pts_b):5.1f} per 100 clasts)   worst {100*wo_b:4.0f}% of the contact radius")

print()
print("== (c) STRATIFIED, largest class first, each pass rejecting against every earlier one ==")
def stratified(seed, b=B, verbose=True):
    rng = random.Random(seed)
    placed = []
    gc = 1.024                              # >= the largest diameter, so a 3x3 scan suffices
    buckets = {}
    def clear(p, a):
        bx, by = int(p[0]/gc), int(p[1]/gc)
        for yy in range(by-1, by+2):
            for xx in range(bx-1, bx+2):
                for i in buckets.get((xx, yy), ()):
                    q = placed[i]
                    if math.hypot(q[0]-p[0], q[1]-p[1]) < q[2] + a:
                        return False
        return True
    stats = []
    t0 = time.perf_counter()
    for ci, (cls, dlo, dhi) in enumerate(CLASSES):
        r_cls = dhi                          # 2 * a_max within this class
        cand, _, _ = bridson(W, H, r_cls, k=30, seed=seed + 17*ci)
        kept = 0
        for p in cand:
            a = draw_d(rng, dlo, dhi, b) / 2.0
            if clear(p, a):
                placed.append((p[0], p[1], a, cls))
                buckets.setdefault((int(p[0]/gc), int(p[1]/gc)), []).append(len(placed)-1)
                kept += 1
        stats.append((cls, r_cls, len(cand), kept))
        if verbose:
            print(f"  {cls:<8} r={r_cls:<6} candidates {len(cand):>6}  kept {kept:>6}  "
                  f"({100.0*kept/len(cand):5.1f}% survive the earlier classes)")
    return placed, (time.perf_counter()-t0)*1e3, stats

placed, ms_c, stats = stratified(SEED)
pts_c = [(p[0], p[1]) for p in placed]; rad_c = [p[2] for p in placed]
no_c, wo_c = overlaps(pts_c, rad_c, 1.024)
cov_c = sum(math.pi*a*a for a in rad_c)/(W*H)
print(f"  TOTAL N = {len(placed)}   interpenetrating pairs = {no_c}   "
      f"ground covered {100*cov_c:.2f}%   {ms_c:.0f} ms ({ms_c*1e3/len(placed):.1f} us/clast)")

print()
print("== where the count goes, and where the AREA goes, against the exponent b ==")
print(f"{'b':>5} " + ' '.join(f"{c[0][:7]:>9}" for c in CLASSES) + "   |  " +
      ' '.join(f"{c[0][:7]:>9}" for c in CLASSES))
print(f"{'':>5} " + ' '.join(f"{'count%':>9}" for c in CLASSES) + "   |  " +
      ' '.join(f"{'area%':>9}" for c in CLASSES))
for b in (1.0, 1.5, 2.0, 2.5, 3.0):
    rng = random.Random(5)
    M = 200000
    ds = [draw_d(rng, 0.004, 1.024, b) for _ in range(M)]
    cnt = [0]*3; ar = [0.0]*3
    for d in ds:
        for i, (cls, lo, hi) in enumerate(CLASSES):
            if lo <= d < hi or (i == 0 and d >= lo):
                cnt[i] += 1; ar[i] += math.pi*(d/2)**2
                break
    tc, ta = sum(cnt), sum(ar)
    print(f"{b:>5.1f} " + ' '.join(f"{100*c/tc:9.4f}" for c in cnt) + "   |  " +
          ' '.join(f"{100*a/ta:9.4f}" for a in ar))
