"""A runnable terrain-graph demo: wire the reference-impl nodes into a DAG, evaluate it,
and render the result you can judge by eye.

This is the *sandbox* the rest of `reference-impl` was missing — a place to drop a new
algorithm in and actually look at what it does. It is a deliberately tiny model of the
substrate in `references/14-graph-runtime.md`:

  * a **node** is a pure function ``fn(params, inputs, ctx) -> field`` plus metadata —
    its locality (LOCAL / NEIGHBOURHOOD / GLOBAL, the tiling contract) and whether it is
    RESOLUTION_INVARIANT or _BOUND (the preview contract);
  * an **edge** is a world-space field (height in metres, drainage area in m^2);
  * the graph is **content-addressed cached** exactly as `14` describes — a node's key
    hashes its params *and its upstream cone*, so changing one node recomputes only its
    downstream cone and nothing else. That is what makes this usable for iteration: tweak
    the erosion node, the noise base is a cache hit.

The sample pipeline walks the **Legal Order** from `SKILL.md`:

    noise -> fluvial erosion -> thermal -> fill -> drainage area -> slope -> masks/materials
     01       04                05         03      03               06       06

and every analysis node (drainage area, slope, materials) runs on the *final* geometry, never
before — the two ordering laws `09` catches most often. Rendering uses the review modes in
`render.py`, including a material splatmap from the partitioned `06` masks.

The nodes are thin adapters over the verified modules (``noise``, ``flow``,
``erosion_droplet``, ``erosion_streampower``, ``erosion_thermal``, ``analysis``). The base
node normalises the chosen ``noise`` family to [0,1] for the demo, but the noise itself is
the verified `01` module — "noise is the initial condition, not the answer" (Doctrine). Run it:

    python graph_demo.py                          # droplet backbone, 96^2, -> out/
    python graph_demo.py --backbone streampower --size 128 --extent-km 120
    python graph_demo.py --seed 7 --sun-sweep 8   # 8 rotating-light frames (09 sun sweep)
    python graph_demo.py --cache-demo             # show the Merkle cache in action
"""
import argparse
import hashlib
import os
import time
from dataclasses import dataclass, field

import numpy as np

import analysis
import erosion_droplet
import erosion_streampower
import erosion_thermal
import flow
import noise
import render


# --------------------------------------------------------------------------- #
# base initial condition: real noise (01) sampled in WORLD coordinates (the seed
# contract). The `noise` module is the verified source; for the demo the field is
# normalised to [0,1] before scaling to metres, so `relief` means the same thing
# whichever noise type is chosen. Noise is the initial condition, not the answer.
# --------------------------------------------------------------------------- #
def _noise_coords(ctx, wavelength):
    """World-metre grid divided by the feature wavelength -> noise lattice coordinates."""
    idx = np.arange(ctx.resolution) * ctx.cellsize / wavelength
    return np.meshgrid(idx, idx)


# --------------------------------------------------------------------------- #
# the tiny graph runtime (a scale model of 14-graph-runtime.md)
# --------------------------------------------------------------------------- #
@dataclass
class Ctx:
    """EvalContext (14): everything an evaluation depends on that isn't a port."""
    cellsize: float                    # metres per cell
    resolution: int                    # cells per side
    root_seed: int

    def key(self):
        return (round(self.cellsize, 6), self.resolution, self.root_seed)


@dataclass
class Node:
    type_id: str                       # stable, versioned string ("erosion.droplet/1")
    fn: object                         # fn(params, inputs, ctx) -> np.ndarray
    inputs: tuple = ()                 # names of upstream nodes
    params: dict = field(default_factory=dict)
    locality: str = "LOCAL"            # LOCAL | NEIGHBOURHOOD | GLOBAL   (tiling contract)
    resolution: str = "RESOLUTION_INVARIANT"   # or RESOLUTION_BOUND     (preview contract)


def _canonical(params):
    """Params in a hashable, order-stable, float-quantised form (14: quantise floats
    before hashing, or a slider drag fills the cache with never-reused entries)."""
    out = []
    for k in sorted(params):
        v = params[k]
        out.append((k, round(v, 6) if isinstance(v, float) else v))
    return tuple(out)


def _validate(out, name):
    """The `09` validation sweep as a runtime option (14): catch NaN/Inf at the edge
    that produced it, before it spreads through the downstream cone."""
    if not np.all(np.isfinite(out)):
        raise ValueError(f"node '{name}' produced non-finite values (NaN/Inf)")


class Graph:
    """Demand-driven, memoised DAG evaluation with content-addressed caching."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.nodes = {}
        self._cache = {}
        self.evaluated = []            # nodes actually computed this session
        self.cache_hits = []           # nodes served from cache

    def add(self, name, type_id, fn, inputs=(), params=None,
            locality="LOCAL", resolution="RESOLUTION_INVARIANT"):
        self.nodes[name] = Node(type_id, fn, tuple(inputs), dict(params or {}),
                                locality, resolution)
        return name

    def key(self, name):
        """Merkle cache key: hashes the node's identity, params, *and upstream cone*,
        plus the relevant context — so a change anywhere invalidates exactly the
        downstream cone (14, content-addressed caching)."""
        node = self.nodes[name]
        parts = (node.type_id, _canonical(node.params),
                 tuple(self.key(i) for i in node.inputs), self.ctx.key())
        return hashlib.sha1(repr(parts).encode()).hexdigest()[:16]

    def evaluate(self, name):
        k = self.key(name)
        if k in self._cache:
            self.cache_hits.append(name)
            return self._cache[k]
        node = self.nodes[name]
        ins = [self.evaluate(i) for i in node.inputs]
        out = np.asarray(node.fn(node.params, ins, self.ctx), dtype=np.float64)
        _validate(out, name)
        self._cache[k] = out
        self.evaluated.append(name)
        return out


# --------------------------------------------------------------------------- #
# nodes: thin adapters over the verified reference-impl modules
# --------------------------------------------------------------------------- #
def _noise_fn(p, ins, ctx):
    xx, yy = _noise_coords(ctx, p["wavelength"])
    kind, oc, seed = p.get("noise", "perlin"), int(p["octaves"]), ctx.root_seed
    if kind == "value":
        f = noise.fbm(xx, yy, seed, octaves=oc, base=noise.value)
    elif kind == "ridged":
        f = noise.ridged_mf(xx, yy, seed, octaves=oc)
    elif kind == "hybrid":
        f = noise.hybrid_mf(xx, yy, seed, octaves=oc)
    elif kind == "warp":
        f, _, _ = noise.domain_warp(xx, yy, seed, warp=p.get("warp", 4.0), octaves=oc)
    else:                                                      # perlin fBm (default)
        f = noise.fbm(xx, yy, seed, octaves=oc, base=noise.perlin)
    f = (f - f.min()) / max(f.max() - f.min(), 1e-9)          # -> [0,1] for the demo
    return f * p["relief"]                                     # -> metres


def _droplet_fn(p, ins, ctx):
    return erosion_droplet.droplet_erode(
        ins[0], n_droplets=int(p["n_droplets"]), seed=ctx.root_seed,
        brush_radius=int(p.get("brush_radius", 2)))


def _streampower_fn(p, ins, ctx):
    uplift = np.full((ctx.resolution, ctx.resolution), p["uplift"], dtype=np.float64)
    return erosion_streampower.stream_power_evolve(
        ins[0], uplift, p["K"], p["m"], p["dt"], int(p["iters"]), cellsize=ctx.cellsize)


def _thermal_fn(p, ins, ctx):
    return erosion_thermal.thermal_erosion(
        ins[0], repose_slope=p["repose"], iters=int(p["iters"]), cellsize=ctx.cellsize)


def _fill_fn(p, ins, ctx):
    return flow.priority_flood_fill(ins[0])


def _area_fn(p, ins, ctx):
    if p.get("method", "d8") == "mfd":
        return flow.mfd_accumulation(ins[0], cellsize=ctx.cellsize)
    return flow.d8_accumulation(ins[0], cellsize=ctx.cellsize)


def _slope_fn(p, ins, ctx):
    return analysis.slope(ins[0], cellsize=ctx.cellsize)


def _materials_fn(p, ins, ctx):
    height, slope_tan, area = ins
    stack = analysis.derive_materials(height, slope_tan, area, ctx.cellsize,
                                      rng_seed=ctx.root_seed)
    return np.stack([m for _, m in stack], axis=0)       # (K, H, W) partitioned MaterialField


def build_graph(ctx, backbone="droplet", noise_kind="perlin"):
    """The sample pipeline, as a DAG in Legal Order. Returns the graph plus the names of
    the two output fields: (height, drainage_area)."""
    g = Graph(ctx)

    # 1-3  base shape: real noise (01) in world coordinates (the initial condition)
    g.add("base", f"noise.{noise_kind}/1", _noise_fn,
          params={"noise": noise_kind, "warp": 4.0,
                  "wavelength": ctx.cellsize * ctx.resolution * 0.45,
                  "octaves": 6, "relief": 200.0 if backbone == "droplet" else 1400.0},
          locality="LOCAL", resolution="RESOLUTION_INVARIANT")

    # 6  fluvial erosion — backbone chosen by extent (SKILL.md design procedure step 3)
    if backbone == "droplet":                                 # < 2 km: explicit particles
        g.add("fluvial", "erosion.droplet/1", _droplet_fn, inputs=("base",),
              params={"n_droplets": 8000, "brush_radius": 2},
              locality="NEIGHBOURHOOD", resolution="RESOLUTION_BOUND")   # fixed count
    else:                                                     # > 50 km: stream power
        g.add("fluvial", "erosion.streampower/1", _streampower_fn, inputs=("base",),
              params={"uplift": 0.001, "K": 3e-6, "m": 0.5, "dt": 2.0e4, "iters": 60},
              locality="GLOBAL", resolution="RESOLUTION_INVARIANT")

    # 7  hillslope erosion — thermal AFTER hydraulic (or it just re-steepens)
    g.add("relaxed", "erosion.thermal/1", _thermal_fn, inputs=("fluvial",),
          params={"repose": 0.7, "iters": 30},
          locality="NEIGHBOURHOOD", resolution="RESOLUTION_INVARIANT")

    # 4-5  analysis routing on the FINAL geometry: fill (mandatory) then accumulate
    g.add("filled", "flow.fill/1", _fill_fn, inputs=("relaxed",), locality="GLOBAL")
    g.add("area", "flow.accumulation/1", _area_fn, inputs=("filled",),
          params={"method": "d8"}, locality="GLOBAL")

    # 10-11  analysis -> masks -> materials, all on the final height (never before)
    g.add("slope", "analysis.slope/1", _slope_fn, inputs=("relaxed",), locality="LOCAL")
    g.add("materials", "analysis.materials/1", _materials_fn,
          inputs=("relaxed", "slope", "area"), locality="LOCAL")

    return g, ("relaxed", "area")


# --------------------------------------------------------------------------- #
# 09 quantitative checks — the numbers that make a bug loud
# --------------------------------------------------------------------------- #
def slope_degrees(h, cellsize):
    gy, gx = np.gradient(np.asarray(h, dtype=np.float64), cellsize)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def report_checks(base, height, area, cellsize):
    """Print the `09` checks the sample graph is meant to pass."""
    n = area.shape[0]
    fi, fj = np.unravel_index(int(np.argmax(area)), area.shape)
    on_edge = fi in (0, n - 1) or fj in (0, n - 1)
    slope = slope_degrees(height, cellsize)
    hist, edges = np.histogram(slope, bins=18, range=(0.0, 90.0))
    peak = 0.5 * (edges[hist.argmax()] + edges[hist.argmax() + 1])
    repose_deg = np.degrees(np.arctan(0.7))
    p99 = float(np.percentile(slope, 99))
    dv = (height.sum() - base.sum()) * cellsize * cellsize     # volume change, m^3
    capped = p99 <= repose_deg + 5.0                           # thermal caps at repose

    print("  09 checks")
    print(f"    check 1  flow reaches edge : outlet of max drainage at "
          f"({fi},{fj}) -> {'ON edge (good)' if on_edge else 'INTERIOR (suspect a pit)'}")
    print(f"    check 2  slope vs repose   : modal {peak:4.1f} deg, 99th-pct {p99:4.1f} deg "
          f"vs repose cap {repose_deg:.0f} deg -> {'capped (good)' if capped else 'OVER cap'}")
    print(f"    mass     erosion budget    : net volume change "
          f"{dv:+.3e} m^3 ({'≈ conserved' if abs(dv) < 0.02 * abs(base.sum()) * cellsize**2 else 'net cut/fill'})")


# --------------------------------------------------------------------------- #
# rendering the review-mode palette
# --------------------------------------------------------------------------- #
def render_all(height, area, cellsize, outdir, materials=None, sun_sweep=0):
    os.makedirs(outdir, exist_ok=True)
    written = []

    def emit(name, img):
        path = render.write_png(os.path.join(outdir, name), img)
        written.append(path)

    emit("01_height.png", render.greyscale(height))
    emit("02_hillshade.png", render.hillshade(height, cellsize))
    emit("03_slope_shade.png", render.slope_shade(height, cellsize))
    emit("04_flow_overlay.png", render.flow_overlay(height, area, cellsize))
    emit("05_hypsometric.png", render.hypsometric(height, cellsize))
    emit("06_clip.png", render.false_colour_clip(height))
    if materials is not None:                                  # 11: the splatmap preview
        emit("07_materials.png", render.material_rgb(materials, cellsize))

    for f in range(int(sun_sweep)):                            # 09: the sun sweep
        az = 360.0 * f / sun_sweep
        emit(f"sweep_{f:02d}_az{int(az):03d}.png",
             render.hillshade(height, cellsize, azimuth=az, altitude=35.0))
    return written


# --------------------------------------------------------------------------- #
# cache demonstration: change one downstream param, watch the cone recompute
# --------------------------------------------------------------------------- #
def cache_demo(ctx, backbone="droplet"):
    print("cache demo — evaluate, then bump only the thermal node's params:")
    g, (h_out, a_out) = build_graph(ctx, backbone)
    g.evaluate(a_out)
    print(f"  first pass   evaluated: {g.evaluated}")
    g.evaluated.clear()
    g.cache_hits.clear()
    g.nodes["relaxed"].params["iters"] += 4                    # a downstream edit
    g.evaluate(a_out)
    print(f"  after edit   recomputed: {g.evaluated}")
    print(f"               cache hits: {sorted(set(g.cache_hits))}")
    print("  -> only 'relaxed' and its downstream cone re-ran; 'fluvial' was a cache hit,")
    print("     so its upstream 'base' was never even revisited.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backbone", choices=("droplet", "streampower"), default="droplet",
                    help="erosion backbone; pick by extent (SKILL.md step 3)")
    ap.add_argument("--noise", choices=("perlin", "value", "ridged", "hybrid", "warp"),
                    default="perlin", help="base noise family (01)")
    ap.add_argument("--size", type=int, default=96, help="cells per side")
    ap.add_argument("--extent-km", type=float, default=None,
                    help="world extent in km (default 1 for droplet, 120 for streampower)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="out", help="output directory for PNGs")
    ap.add_argument("--sun-sweep", type=int, default=0,
                    help="also write N rotating-light hillshade frames (09 sun sweep)")
    ap.add_argument("--cache-demo", action="store_true",
                    help="demonstrate the content-addressed cache and exit")
    args = ap.parse_args(argv)

    extent_km = args.extent_km
    if extent_km is None:
        extent_km = 1.0 if args.backbone == "droplet" else 120.0
    cellsize = extent_km * 1000.0 / args.size
    ctx = Ctx(cellsize=cellsize, resolution=args.size, root_seed=args.seed)

    if args.cache_demo:
        cache_demo(ctx, args.backbone)
        return

    print(f"terrain graph: backbone={args.backbone}  noise={args.noise}  size={args.size}^2  "
          f"extent={extent_km} km  cellsize={cellsize:.1f} m  seed={args.seed}")
    g, (h_out, a_out) = build_graph(ctx, args.backbone, args.noise)

    t0 = time.time()
    height = g.evaluate(h_out)
    area = g.evaluate(a_out)
    materials = g.evaluate("materials")
    base = g._cache[g.key("base")]
    print(f"  evaluated in {time.time() - t0:.1f}s; order: {g.evaluated}")

    report_checks(base, height, area, cellsize)
    written = render_all(height, area, cellsize, args.out, materials, args.sun_sweep)
    print(f"  wrote {len(written)} renders to {args.out}/:")
    for p in written:
        print(f"    {p}")


if __name__ == "__main__":
    main()
