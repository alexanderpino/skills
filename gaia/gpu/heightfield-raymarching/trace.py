import importlib.util, math, sys
from pathlib import Path
RIG = Path(__file__).resolve().parents[2] / "rigs" / "approx" / "heightfield-raymarching.py"
spec = importlib.util.spec_from_file_location("hr_rig", RIG)
rig = importlib.util.module_from_spec(spec)
sys.argv = [str(RIG), "--gate"]
spec.loader.exec_module(rig)

h = rig._samples()
pyr = rig._pyramid(h, "level0")
rs = rig._rays(h)
ref = [rig._reference(h, o, d, t0, t1) for (o, d, t0, t1, _k) in rs]

# pick the worst primary ray (first one, o.y=37.99 in our dump)
idx = next(i for i,(o,d,t0,t1,k) in enumerate(rs) if k=="primary")
o,d,t0,t1,kind = rs[idx]
r = ref[idx]
print("ray", idx, "kind", kind, "o", o, "d", d, "t0", t0, "t1", t1, "ref", r)

def node_max_wrap(pyr, level, x, z):
    s = rig._S0 * (1 << level)
    n = len(pyr[level])
    return pyr[level][math.floor(z / s) % n][math.floor(x / s) % n]

def exit_distance(o, d, t, level):
    s = rig._S0 * (1 << level)
    out = math.inf
    for ax in (0, 2):
        if d[ax] == 0.0: continue
        c = math.floor((o[ax] + d[ax]*t) / s)
        bound = (c + (1 if d[ax] > 0 else 0)) * s
        out = min(out, (bound - o[ax]) / d[ax])
    return out

def refine_port(h, o, d, t0, t1, iters=6, scan=8):
    f = lambda t: (o[1] + d[1]*t) - rig._surface(h, o[0]+d[0]*t, o[2]+d[2]*t)
    flo = f(t0)
    if flo <= 0.0: return t0
    fhi = f(t1)
    lo, hi = t0, t1
    if not (fhi <= 0.0):
        prev_t, prev_f, found = t0, flo, False
        for si in range(1, scan+1):
            tt = t0 + (t1-t0)*si/scan
            ft = f(tt)
            if prev_f > 0.0 and ft <= 0.0:
                lo, hi, found = prev_t, tt, True
                break
            prev_t, prev_f = tt, ft
        if not found: return None
    for _ in range(iters):
        m = 0.5*(lo+hi)
        if f(m) > 0.0: lo = m
        else: hi = m
    return 0.5*(lo+hi)

def my_march_port(h, pyr, o, d, t_enter, t_exit, iters=6, trace=False, cap=20000):
    level, t, steps = len(pyr)-1, t_enter, 0
    while t < t_exit:
        node = node_max_wrap(pyr, level, o[0]+d[0]*t, o[2]+d[2]*t)
        t_exit_node = min(exit_distance(o, d, t, level), t_exit)
        h0, h1 = o[1]+d[1]*t, o[1]+d[1]*t_exit_node
        candidate = min(h0, h1) < node
        t_before, level_before = t, level
        if trace and steps < 40:
            print(f"  step={steps:3d} t={t:10.5f} level={level} node={node:8.4f} texN={t_exit_node:10.5f} "
                  f"h0={h0:8.4f} h1={h1:8.4f} cand={candidate}")
        if candidate:
            if level == 0:
                hit = refine_port(h, o, d, t, t_exit_node, iters)
                if hit is not None:
                    return ("HIT", hit, steps)
            else:
                if d[1] < 0.0:
                    tCross = (node - o[1]) / d[1]
                    t = max(t, tCross)
                level = level - 1
        if (not candidate) or level == level_before:
            t = max(t, t_exit_node) * (1.0 + 2.38418579e-7)
            level = min(level+1, len(pyr)-1)
        steps += 1
        if steps > cap:
            return ("CAP", steps, steps)
    return ("MISS", None, steps)

print("\n-- my Python port of the shader's logic, traced --")
res = my_march_port(h, pyr, o, d, t0, t1, trace=True)
print("RESULT:", res)

print("\n-- the rig's own _march, for comparison --")
real = rig._march(h, pyr, o, d, t0, t1, iters=6)
print("RIG RESULT:", real[:2])
