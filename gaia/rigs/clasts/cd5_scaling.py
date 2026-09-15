"""cd5 -- (F9) what lowering a class' FLOOR actually costs, and (F10) timing per-class grids.

The page claimed: drop the pebble floor 4 mm -> 2 mm and candidates quadruple, rejection
work goes up ~16x. In the recommended construction r_cls = d_max(cls), so the FLOOR does
not enter the sampler at all. Measured, not argued.
"""
import math, random, time, sys
sys.path.insert(0,'/tmp/claude-0/-home-user-skills/041d794d-2927-5ffb-83af-919282824aad/scratchpad/clasts')
from cd1_bridson import bridson

W = H = 10.0; SEED = 11; B = 2.5

def draw_d(rng, lo, hi, b):
    u = rng.random(); lo_b, hi_b = lo**(-b), hi**(-b)
    return (lo_b - u*(lo_b - hi_b))**(-1.0/b)

def run(classes, per_class_grids, time_it=True):
    rng = random.Random(SEED)
    names = [c[0] for c in classes]
    cellsz = {c[0]: (c[2] if per_class_grids else max(x[2] for x in classes)) for c in classes}
    amax   = {c[0]: c[2]/2 for c in classes}
    buckets = {c[0]: {} for c in classes}
    tests = cand = kept = 0
    # sample first so the timing covers placement, not sampling
    pools = {c[0]: bridson(W, H, c[2], k=30, seed=SEED + 17*i)[0] for i, c in enumerate(classes)}
    t0 = time.perf_counter()
    for cls, dlo, dhi in classes:
        for p in pools[cls]:
            cand += 1
            a = draw_d(rng, dlo, dhi, B)/2.0
            ok = True
            for ocls in names:
                gc = cellsz[ocls]
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
                gc = cellsz[cls]
                buckets[cls].setdefault((int(p[0]/gc), int(p[1]/gc)), []).append((p[0],p[1],a))
                kept += 1
    ms = (time.perf_counter()-t0)*1e3
    return cand, kept, tests, ms

BASE   = [("boulder",0.256,1.024), ("cobble",0.064,0.256), ("pebble",0.004,0.064)]
FLOOR2 = [("boulder",0.256,1.024), ("cobble",0.064,0.256), ("pebble",0.002,0.064)]

print("== F9: lowering the PEBBLE FLOOR 4 mm -> 2 mm, r_cls unchanged at d_max ==")
for label, cls in (("floor 4 mm", BASE), ("floor 2 mm", FLOOR2)):
    for g, gl in ((True,"per-class grids"), (False,"one grid")):
        c,k,t,ms = run(cls, g)
        print(f"  {label:<11} {gl:<16} candidates {c:>6}  kept {k:>6}  tests {t:>9,}  "
              f"{t/c:7.1f}/cand")

print()
print("== F9: what a FINER CLASS costs -- candidates go as 1/d_max^2 ==")
for dmax in (0.064, 0.032, 0.016, 0.008, 0.004):
    n = len(bridson(W, H, dmax, k=30, seed=SEED)[0])
    print(f"  a class with d_max = {dmax*1000:6.1f} mm -> {n:>9,} candidates on the patch "
          f"({n/100*1e6*24/1e9:8.2f} GB/km^2 if all kept)")

print()
print("== F10: TIMING the two grid arrangements (placement only, sampling excluded) ==")
for g, gl in ((False,"one grid at the largest d_max"), (True,"one grid PER CLASS")):
    c,k,t,ms = run(BASE, g)
    print(f"  {gl:<32} {ms:8.0f} ms  {ms*1e3/k:7.1f} us/clast kept  ({t/c:.1f} tests/cand)")
