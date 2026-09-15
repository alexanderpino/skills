"""cd1 -- Bridson's algorithm as published, measured against its own claims.

Claims under test, all from bridson2007b:
  (1) cell size r/sqrt(n) => at most one sample per cell
  (2) candidates from the spherical annulus between r and 2r
  (3) step 2 executed exactly 2N-1 times to produce N samples
  (4) O(k) per iteration, so linear in N
Plus the property the paper's own guarantee gives: min pairwise distance >= r.
"""
import math, random, time

def bridson(width, height, r, k=30, seed=0, count_steps=True):
    rng = random.Random(seed)
    cell = r / math.sqrt(2.0)
    gw, gh = int(math.ceil(width / cell)), int(math.ceil(height / cell))
    grid = [-1] * (gw * gh)
    samples, active = [], []
    steps = 0

    def gidx(p):
        return int(p[0] / cell), int(p[1] / cell)

    def ok(p):
        if not (0.0 <= p[0] < width and 0.0 <= p[1] < height):
            return False
        gx, gy = gidx(p)
        for yy in range(max(0, gy - 2), min(gh, gy + 3)):
            for xx in range(max(0, gx - 2), min(gw, gx + 3)):
                s = grid[yy * gw + xx]
                if s != -1:
                    q = samples[s]
                    if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < r * r:
                        return False
        return True

    p0 = (rng.uniform(0, width), rng.uniform(0, height))
    samples.append(p0); gx, gy = gidx(p0); grid[gy * gw + gx] = 0; active.append(0)

    while active:
        steps += 1
        ai = rng.randrange(len(active))
        i = active[ai]
        found = False
        for _ in range(k):
            # uniform ON THE ANNULUS between r and 2r: area element is rho*d(rho),
            # so rho = sqrt(U*(4r^2 - r^2) + r^2), NOT a uniform draw in [r, 2r].
            th = rng.uniform(0, 2 * math.pi)
            rho = math.sqrt(rng.uniform(r * r, 4 * r * r))
            q = samples[i]
            p = (q[0] + rho * math.cos(th), q[1] + rho * math.sin(th))
            if ok(p):
                samples.append(p)
                gx, gy = gidx(p); grid[gy * gw + gx] = len(samples) - 1
                active.append(len(samples) - 1)
                found = True
                break
        if not found:
            active[ai] = active[-1]; active.pop()
    return samples, steps, (grid, gw, gh, cell)

def min_sep(pts, cellsize=None):
    # brute force is O(N^2); grid it for the big runs
    n = len(pts)
    if n < 2:
        return float('inf')
    c = cellsize or 1.0
    buckets = {}
    for idx, p in enumerate(pts):
        buckets.setdefault((int(p[0] / c), int(p[1] / c)), []).append(idx)
    best = float('inf')
    for (bx, by), ids in buckets.items():
        near = []
        for yy in range(by - 1, by + 2):
            for xx in range(bx - 1, bx + 2):
                near.extend(buckets.get((xx, yy), ()))
        for a in ids:
            for b in near:
                if a < b:
                    d2 = (pts[a][0]-pts[b][0])**2 + (pts[a][1]-pts[b][1])**2
                    if d2 < best:
                        best = d2
    return math.sqrt(best)

print("== CLAIM 1: cell size r/sqrt(2) holds at most one sample ==")
print("== CLAIM 3: step 2 runs exactly 2N-1 times ==")
print("== min separation >= r ==")
print(f"{'domain':>10} {'r':>6} {'N':>7} {'steps':>8} {'2N-1':>8} {'match':>6} "
      f"{'maxpercell':>11} {'minsep/r':>9} {'ms':>9}")
rows = []
for (W, H, r) in [(100, 100, 4.0), (100, 100, 2.0), (200, 200, 2.0), (400, 400, 2.0), (100, 100, 1.0)]:
    t0 = time.perf_counter()
    pts, steps, (grid, gw, gh, cell) = bridson(W, H, r, k=30, seed=7)
    ms = (time.perf_counter() - t0) * 1e3
    # occupancy per cell recomputed from the sample list, not from the grid array
    occ = {}
    for p in pts:
        key = (int(p[0] / cell), int(p[1] / cell))
        occ[key] = occ.get(key, 0) + 1
    maxocc = max(occ.values())
    ms_sep = min_sep(pts, cellsize=r)
    N = len(pts)
    rows.append((W * H, r, N, ms))
    print(f"{W}x{H:<6} {r:>6} {N:>7} {steps:>8} {2*N-1:>8} {str(steps == 2*N-1):>6} "
          f"{maxocc:>11} {ms_sep/r:>9.6f} {ms:>9.2f}")

print()
print("== CLAIM 4: linear in N -- microseconds per sample across a 22x range in N ==")
for area, r, N, ms in rows:
    print(f"  area {area:>7}  r {r:>4}  N {N:>7}  {ms*1e3/N:8.2f} us/sample")

print()
print("== the annulus draw: uniform-in-radius is NOT uniform on the annulus ==")
rng = random.Random(1)
M = 400000
# correct: rho = sqrt(U(r^2, 4r^2)); naive: rho = U(r, 2r)
mean_correct = sum(math.sqrt(rng.uniform(1.0, 4.0)) for _ in range(M)) / M
mean_naive = sum(rng.uniform(1.0, 2.0) for _ in range(M)) / M
exact_correct = (2.0/3.0) * (8.0 - 1.0) / (4.0 - 1.0)   # integral rho*rho drho / integral rho drho
print(f"  mean radius, area-uniform : {mean_correct:.4f} r   (exact {exact_correct:.4f} r)")
print(f"  mean radius, uniform in rho: {mean_naive:.4f} r   (exact 1.5000 r)")
print(f"  the naive draw pulls candidates {100*(exact_correct-1.5)/exact_correct:.1f}% closer in")
