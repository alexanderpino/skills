import importlib.util, sys
import numpy as np
from pathlib import Path
RIG = Path(__file__).resolve().parents[2] / "rigs" / "approx" / "heightfield-raymarching.py"
spec = importlib.util.spec_from_file_location("hr_rig", RIG)
rig = importlib.util.module_from_spec(spec)
sys.argv = [str(RIG), "--gate"]
spec.loader.exec_module(rig)

f32 = np.float32
def F(x): return f32(x)

h = rig._samples()
pyr = rig._pyramid(h, "level0")
rs = rig._rays(h)
idx = next(i for i,(o,d,t0,t1,k) in enumerate(rs) if k=="primary")
o,d,t0,t1,kind = rs[idx]
ref = rig._reference(h, o, d, t0, t1)

# cast everything to fp32 up front, matching how it enters the shader as a uniform/texture
o32 = [F(x) for x in o]
d32 = [F(x) for x in d]
t0_32, t1_32 = F(t0), F(t1)
S0_32 = F(rig._S0)
pyr32 = [[[F(v) for v in row] for row in level] for level in pyr]

def node_max32(level, x, z):
    s = S0_32 * F(1 << level)
    n = len(pyr32[level])
    # GLSL mod(a,b) = a - b*floor(a/b); Python's % on floats matches this for b>0
    ix = int(f32(np.floor(f32(x / s)))) % n
    iz = int(f32(np.floor(f32(z / s)))) % n
    return pyr32[level][iz][ix]

def exit_distance32(o, d, t, level):
    s = S0_32 * F(1 << level)
    out = F(1.0e30)
    for ax in (0, 2):
        if d[ax] == F(0.0): continue
        pos = F(o[ax] + d[ax] * t)
        c = f32(np.floor(f32(pos / s)))
        bound = F((c + F(1.0 if d[ax] > 0 else 0.0)) * s)
        cand = F((bound - o[ax]) / d[ax])
        out = F(min(out, cand))
    return out

def surface32(x, z):
    base = pyr32[0]  # NOTE: level 0 here is the DILATED base in `pyr`; the real base (undilated)
    # is a separate array in the rig -- use the rig's own undilated samples for `_surface`
    return None  # placeholder, real one below uses the true undilated field

field32 = [[F(v) for v in row] for row in h]
NG = rig._NG
def surface_real32(x, z):
    u = F(x / S0_32 - F(0.5))
    v = F(z / S0_32 - F(0.5))
    i = int(f32(np.floor(u))); j = int(f32(np.floor(v)))
    p = F(u - F(i)); q = F(v - F(j))
    i0, j0 = i % NG, j % NG
    i1, j1 = (i+1) % NG, (j+1) % NG
    a = F(field32[j0][i0] + F(field32[j0][i1] - field32[j0][i0]) * p)
    b = F(field32[j1][i0] + F(field32[j1][i1] - field32[j1][i0]) * p)
    return F(a + F(b - a) * q)

def refine32(o, d, t0, t1, iters, scan=8):
    def f(t):
        t = F(t)
        return F(F(o[1] + d[1]*t) - surface_real32(F(o[0]+d[0]*t), F(o[2]+d[2]*t)))
    flo = f(t0)
    if flo <= F(0.0): return True, t0
    fhi = f(t1)
    lo, hi = t0, t1
    if not (fhi <= F(0.0)):
        prev_t, prev_f, found = t0, flo, False
        for si in range(1, scan+1):
            tt = F(t0 + F(t1-t0) * F(si) / F(scan))
            ft = f(tt)
            if prev_f > F(0.0) and ft <= F(0.0):
                lo, hi, found = prev_t, tt, True
                break
            prev_t, prev_f = tt, ft
        if not found: return False, F(-1.0)
    for _ in range(iters):
        m = F(F(0.5) * F(lo + hi))
        if f(m) > F(0.0): lo = m
        else: hi = m
    return True, F(F(0.5) * F(lo + hi))

def march32(o, d, t_enter, t_exit, iters=6, cap=20000, trace_upto=None):
    level = len(pyr32) - 1
    t = F(t_enter)
    steps = 0
    while t < t_exit:
        node = node_max32(level, F(o[0]+d[0]*t), F(o[2]+d[2]*t))
        texn = F(min(exit_distance32(o, d, t, level), t_exit))
        h0 = F(o[1] + d[1]*t); h1 = F(o[1] + d[1]*texn)
        candidate = F(min(h0, h1)) < node
        t_before, level_before = t, level
        if trace_upto is not None and steps <= trace_upto:
            print(f"  fp32 step={steps:3d} t={t!r} level={level} node={node!r} texN={texn!r} cand={candidate}")
        if candidate:
            if level == 0:
                found, hit = refine32(o, d, t, texn, iters)
                if found:
                    return ("HIT", hit, steps)
            else:
                if d[1] < F(0.0):
                    tCross = F((node - o[1]) / d[1])
                    t = F(max(t, tCross))
                level = level - 1
        if (not candidate) or level == level_before:
            t = F(F(max(t, texn)) * F(1.0 + 2.38418579e-7))
            level = min(level + 1, len(pyr32) - 1)
        steps += 1
        if steps > cap:
            return ("CAP", steps, steps)
    return ("MISS", None, steps)

print("ray:", o, d, "t0", t0, "t1", t1, "ref", ref)
print()
res = march32(o32, d32, t0_32, t1_32, trace_upto=20)
print("\nfp32-emulated Python result:", res)
print("GPU (SwiftShader GLSL) result was: t=82.61137390136719, steps=49")
