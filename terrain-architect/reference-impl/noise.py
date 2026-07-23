"""Procedural noise (01-noise.md). The initial condition, never a landform.

Continuous `noise(x, y)` families evaluated in WORLD coordinates (the only seam-free call):
Perlin (Improved 2002), value, Worley, and the fractal compositions over them — fBm, ridged
and hybrid multifractal, domain warp, and divergence-free curl. Each carries a decisive
oracle: Perlin is exactly 0 at every integer lattice point; single-octave fBm is the base
noise; curl noise has zero divergence by construction; fractal sums stay finite.

Deliberately NOT here: diamond-square. The chapter's verdict is "do not use", and structurally
`h(x, y)` doesn't exist for it — only a fixed grid does, so it isn't a sampleable noise at all.
OpenSimplex2's exact lattice is a port target in `references/22-open-source-grounding.md`, not
reconstructed here; `perlin` covers the axis-aligned-gradient-noise slot for the demo.
"""
import numpy as np


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _fade(t):
    """Quintic fade 6t^5-15t^4+10t^3 (Improved Perlin 2002) — C2, no lattice creases."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(a, b, t):
    return a + t * (b - a)


def _hash01(ix, iy, seed, salt=0):
    """Deterministic value in [0,1) per integer lattice cell; the wrap is intended."""
    mask = np.uint64(0xFFFFFFFFFFFFFFFF)
    s = np.uint64((int(seed) * 0x9E3779B97F4A7C15 + int(salt) * 0x632BE59BD9B4E019) & int(mask))
    ix_u = np.asarray(ix).astype(np.int64).astype(np.uint64)
    iy_u = np.asarray(iy).astype(np.int64).astype(np.uint64)
    with np.errstate(over="ignore"):
        h = (ix_u * np.uint64(0x9E3779B97F4A7C15)
             ^ iy_u * np.uint64(0xC2B2AE3D27D4EB4F) ^ s) & mask
        h ^= h >> np.uint64(33)
        h *= np.uint64(0xFF51AFD7ED558CCD)
        h ^= h >> np.uint64(33)
    return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)


def _perm(seed):
    """256-entry permutation shuffled by the seed, duplicated to 512 (Perlin). Seeding by
    shuffling P — never by offsetting coordinates, which just translates one pattern."""
    rng = np.random.default_rng(int(seed) & 0xFFFFFFFF)
    p = np.arange(256, dtype=np.int64)
    rng.shuffle(p)
    return np.concatenate([p, p])


_GRAD2 = np.array([(1, 1), (-1, 1), (1, -1), (-1, -1),
                   (1, 0), (-1, 0), (0, 1), (0, -1)], dtype=np.float64)


def _grad2(h, x, y):
    g = _GRAD2[np.asarray(h) & 7]
    return g[..., 0] * x + g[..., 1] * y


# --------------------------------------------------------------------------- #
# base noises
# --------------------------------------------------------------------------- #
def perlin(x, y, seed=0):
    """Improved Perlin gradient noise, roughly Gaussian and centred on 0. Because `_GRAD2` mixes
    magnitude-1 (axis) and magnitude-√2 (diagonal) gradients, the actual range reaches ≈[-1, 1]
    (not the ±0.707 of a unit-gradient set) — so **measure the range and remap** (the `01` doctrine);
    a remap keyed to 0.707 clips the tails. Exactly 0 at integer lattice points — threshold FBM, not
    raw Perlin, or you outline the grid."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    P = _perm(seed)
    xi = np.floor(x).astype(np.int64) & 255
    yi = np.floor(y).astype(np.int64) & 255
    xf, yf = x - np.floor(x), y - np.floor(y)
    u, v = _fade(xf), _fade(yf)
    aa = P[P[xi] + yi]
    ab = P[P[xi] + yi + 1]
    ba = P[P[xi + 1] + yi]
    bb = P[P[xi + 1] + yi + 1]
    x1 = _lerp(_grad2(aa, xf, yf), _grad2(ba, xf - 1, yf), u)
    x2 = _lerp(_grad2(ab, xf, yf - 1), _grad2(bb, xf - 1, yf - 1), u)
    return _lerp(x1, x2, v)


def value(x, y, seed=0):
    """Value noise in [0,1]: quintic-interpolated hashed lattice values. Cheap, but extrema
    sit ON the lattice so the grid shows; use only as an FBM component (01)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    xf, yf = x - x0, y - y0
    u, v = _fade(xf), _fade(yf)
    c00 = _hash01(x0, y0, seed)
    c10 = _hash01(x0 + 1, y0, seed)
    c01 = _hash01(x0, y0 + 1, seed)
    c11 = _hash01(x0 + 1, y0 + 1, seed)
    return _lerp(_lerp(c00, c10, u), _lerp(c01, c11, u), v)


def worley(x, y, seed=0, kind="f2f1"):
    """Worley/Voronoi cellular noise (one feature point per cell). `kind`: 'f1' (blobs),
    'f2f1' (cracks/mud-flats, ~0 at cell boundaries), 'inv_f1' (crater fields). Euclidean."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    cx, cy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    f1 = np.full(x.shape, np.inf)
    f2 = np.full(x.shape, np.inf)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            gx, gy = cx + di, cy + dj
            fx = gx + _hash01(gx, gy, seed, salt=1)
            fy = gy + _hash01(gx, gy, seed, salt=2)
            d = np.hypot(x - fx, y - fy)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            f1 = np.where(closer, d, f1)
    if kind == "f1":
        return f1
    if kind == "inv_f1":
        return 1.0 - f1
    return f2 - f1


# --------------------------------------------------------------------------- #
# fractal compositions
# --------------------------------------------------------------------------- #
def fbm(x, y, seed=0, octaves=6, lacunarity=2.03, gain=0.5, base=perlin):
    """Fractal Brownian motion: sum of octaves, amplitude-normalised so the result does not
    depend on octave count. Lacunarity slightly off 2 (2.03) breaks lattice reinforcement;
    each octave is seed-offset so zero-crossings don't stack into a grid of pinch points (01)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    total = np.zeros(np.broadcast(x, y).shape)
    amp, freq, norm = 1.0, 1.0, 0.0
    for i in range(int(octaves)):
        total = total + amp * base(x * freq, y * freq, seed + i * 1013)
        norm += amp
        freq *= lacunarity
        amp *= gain
    return total / norm


def ridged_mf(x, y, seed=0, octaves=6, lacunarity=2.03, gain=2.0, offset=1.0, H=1.0):
    """Musgrave ridged multifractal with weight feedback: sharp ridgelines, valleys stay
    smooth. Non-negative. Not differentiable at the ridge (the abs crease is the point) —
    take normals by finite difference on the final height, never analytically (01)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    signal = offset - np.abs(perlin(x, y, seed))
    signal = signal * signal
    result = signal.copy()
    freq = 1.0
    for i in range(1, int(octaves)):
        freq *= lacunarity
        weight = np.clip(signal * gain, 0.0, 1.0)                # weight is (re)set here each octave before use
        signal = offset - np.abs(perlin(x * freq, y * freq, seed + i * 1013))
        signal = signal * signal * weight
        result = result + signal * freq ** (-H)
    return result


def hybrid_mf(x, y, seed=0, octaves=6, lacunarity=2.03, H=0.25, offset=0.7):
    """Musgrave hybrid multifractal: plains stay smooth, mountains get rough (the correlation
    real topography shows). The min(weight, 1) clamp is mandatory — without it the product
    diverges to isolated spikes. Range not normalised; measure and remap (01)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    exps = [lacunarity ** (-i * H) for i in range(int(octaves))]
    result = (perlin(x, y, seed) + offset) * exps[0]
    weight = result.copy()
    freq = 1.0
    for i in range(1, int(octaves)):
        freq *= lacunarity
        weight = np.minimum(weight, 1.0)
        signal = (perlin(x * freq, y * freq, seed + i * 1013) + offset) * exps[i]
        result = result + weight * signal
        weight = weight * signal
    return result


def domain_warp(x, y, seed=0, warp=4.0, **fbm_kw):
    """Quilez domain warp: fbm(p + warp * (fbm(p+O1), fbm(p+O2))). Highest visual-improvement-
    to-cost ratio in the noise section. Returns (height, qx, qy); q is a free flow-aligned mask.
    A look, not erosion — it has the appearance of flow with none of the connectivity (01)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    qx = fbm(x + 5.2, y + 1.3, seed + 1, **fbm_kw)
    qy = fbm(x + 8.3, y + 2.8, seed + 2, **fbm_kw)
    h = fbm(x + warp * qx, y + warp * qy, seed, **fbm_kw)
    return h, qx, qy


def curl(x, y, seed=0, eps=1.0, **fbm_kw):
    """Divergence-free 2D vector field from the curl of an fBm potential psi: (dpsi/dy,
    -dpsi/dx). Divergence is 0 by construction, so warping by it preserves area — it swirls
    without pinching or tearing (Bridson 2007). Returns (vx, vy). eps ~ one cell."""
    def psi(px, py):
        return fbm(px, py, seed, **fbm_kw)
    dpdy = (psi(x, y + eps) - psi(x, y - eps)) / (2 * eps)
    dpdx = (psi(x + eps, y) - psi(x - eps, y)) / (2 * eps)
    return dpdy, -dpdx
