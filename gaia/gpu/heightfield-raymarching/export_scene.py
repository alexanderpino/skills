"""Dump the EXACT scene `rigs/approx/heightfield-raymarching.py` runs -- the same field, the
same 110 rays, the same closed-form reference hit for each -- to JSON, so the GPU driver in
this directory runs the identical inputs through a real GLSL shader instead of CPython.

This is the whole point of the comparison: the ONLY thing that should differ between the two
runs is the execution engine (CPython vs a compiled fragment shader on SwiftShader). Isolating
that means neither reimplementing the field formula nor the ray generator in JavaScript --
both would be a second, independent source of disagreement, and a divergence then proves
nothing about which one (if either) is wrong. This script imports the rig as a module and
calls its own functions, so the exported scene is provably the rig's, not a paraphrase of it.

    python3 gaia/gpu/heightfield-raymarching/export_scene.py > scene.json
"""
import importlib.util
import json
import sys
from pathlib import Path

RIG = Path(__file__).resolve().parents[2] / "rigs" / "approx" / "heightfield-raymarching.py"
spec = importlib.util.spec_from_file_location("hr_rig", RIG)
rig = importlib.util.module_from_spec(spec)
sys.argv = [str(RIG), "--gate"]     # the module runs run_gate() at import unless this is set
spec.loader.exec_module(rig)

h = rig._samples()
rs = rig._rays(h)
ref = [rig._reference(h, o, d, t0, t1) for (o, d, t0, t1, _k) in rs]

out = {
    "S0": rig._S0, "NG": rig._NG, "AMP_X": rig._AMP_X, "KX": rig._KX,
    "AMP_Z": rig._AMP_Z, "KZ": rig._KZ, "NLevels": rig._N_EXP + 1,
    "field": h,   # NG x NG, row-major, h[j][i] = height at texel centre (i+0.5, j+0.5)*S0
    "rays": [
        {"o": o, "d": d, "t0": t0, "t1": t1, "kind": k, "ref": r}
        for (o, d, t0, t1, k), r in zip(rs, ref)
    ],
}
json.dump(out, sys.stdout)
sys.stderr.write(f"exported {len(rs)} rays over a {rig._NG}x{rig._NG} field, "
                 f"{sum(1 for r in ref if r is not None)} references present\n")
