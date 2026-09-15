"""Dump a subset of rigs/approx/gpu-driven-culling.py's own Part 1 scene to JSON: the SAME
depth buffer and HiZ pyramid construction (build_scene/build_pyramid, imported and called, not
re-derived), plus a reduced trial set (300, not the rig's 20,000 -- a lighter pass validates
the four-corner-tap SHADER LOGIC against a same-construction scene; the rig's own fp64 run
already owns the large-N statistical claim).

    python3 gaia/gpu/gpu-driven-culling/export_scene.py > scene.json
"""
import importlib.util, json, random, sys
from pathlib import Path

RIG = Path(__file__).resolve().parents[2] / "rigs" / "approx" / "gpu-driven-culling.py"
spec = importlib.util.spec_from_file_location("cull_rig", RIG)
rig = importlib.util.module_from_spec(spec)
sys.argv = [str(RIG)]
spec.loader.exec_module(rig)

rng = random.Random(rig.SEED)
depth = rig.build_scene(rng)          # identical call, identical seed -> identical scene
mips = rig.build_pyramid(depth)

trials = []
rng2 = random.Random(rig.SEED + 1)    # a fresh, independent trial stream -- same distributions
N = 300
for _ in range(N):
    w = rng2.randint(4, 256)
    h = rng2.randint(4, 256)
    x0 = rng2.randint(0, rig.DIM - w)
    y0 = rng2.randint(0, rig.DIM - h)
    z_near = rng2.uniform(0.05, 0.95)
    t_max = rig.true_max(depth, x0, y0, w, h)
    base = rig.rule_mip(w, h)
    trials.append({"w": w, "h": h, "x0": x0, "y0": y0, "z_near": z_near,
                    "true_max": t_max, "base_mip": base})

out = {"DIM": rig.DIM, "n_levels": len(mips), "mips": mips, "trials": trials}
json.dump(out, sys.stdout)
sys.stderr.write(f"exported a {rig.DIM}x{rig.DIM} scene, {len(mips)} mip levels, "
                 f"{len(trials)} trials\n")
