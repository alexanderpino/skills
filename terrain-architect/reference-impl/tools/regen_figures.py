"""Criterion H's executor: every committed figure, rebuilt from its producer and diffed.

The point is the DENOMINATOR, not the diff. `GALLERY.md` carries a regenerate-command table
for FOUR anatomy figures; fourteen PNGs are committed. A checker that walks the table would
certify four and stay silent about ten -- the same shape of hole criterion J exists to catch
(a guard whose scan domain is a hand-written list cannot see what the list forgot). So the
enumeration here starts from the files on disk: every `*.png` under `reference-impl/` is
either rebuilt and compared, or named in EXEMPT with a reason, and a PNG that is in neither
is a hard failure.

Comparison is PIXEL-exact, not byte-exact. PNG bytes carry encoder state (zlib level, filter
choice, ancillary chunks) that can differ between Pillow builds without a single pixel moving;
pixels are the claim the figure actually makes. Verified byte-identical on this machine for
`hex_anatomy` and `anisotropy_anatomy`, so pixel-exact is not a loosened bar here -- it is the
same bar stated in terms of the thing being asserted.

Each producer is executed with the scratch directory as CWD, because every one of them ends in
`build().save("<name>.png")` with a RELATIVE path. Running them in the repo would overwrite the
committed figure with the thing being compared against it, which passes unconditionally.

    python tools/regen_figures.py            # check all, non-zero exit on any drift
    python tools/regen_figures.py --only hex_anatomy flow_anatomy
"""
from __future__ import annotations

import argparse
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REF = Path(__file__).resolve().parents[1]          # reference-impl/

# figure stem -> producing module stem. The two differ only where the module builds a contact
# sheet under a different name, which is why this is a map and not `stem + '.py'`.
PRODUCERS: dict[str, str] = {
    "anisotropy_anatomy": "anisotropy_anatomy",
    "archetypes": "archetypes",
    "capability_grid": "capability_grid",
    "crater_anatomy": "crater_anatomy",
    "crater_matrix": "crater_demo",     # crater_demo.py:166 render.write_png("crater_matrix.png")
    "erosion_pipe": "erosion_pipe",
    "erosion_streampower": "erosion_streampower",
    "flow_anatomy": "flow_anatomy",
    "gallery": "gallery",
    "halfar_anatomy": "halfar_anatomy",
    "hero": "hero",
    "hex_anatomy": "hex_anatomy",
    "landforms": "landforms",
    "screen_worlds": "screen_worlds",
}

# A figure may sit here only with a reason that is about the figure, never about the effort of
# checking it. Empty today, deliberately: nothing is exempt, so the denominator is 14/14.
EXEMPT: dict[str, str] = {}


def committed_figures() -> list[str]:
    """Stems of the PNGs GIT tracks under reference-impl/ -- not what happens to be on disk.

    An untracked PNG is a build artefact from someone's last run; demanding that it match a
    committed original would fail for the wrong reason.
    """
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.png"],
        cwd=REF, capture_output=True, text=True, check=True,
    ).stdout
    return sorted(Path(p).stem for p in out.split("\0") if p)


def check_enumeration(figures: list[str]) -> list[str]:
    """Criterion J in miniature: the domain is asserted before anything is compared."""
    problems = []
    for stem in figures:
        if stem not in PRODUCERS and stem not in EXEMPT:
            problems.append(f"{stem}.png is committed but has no producer and no exemption")
    for stem in PRODUCERS:
        if stem not in figures:
            problems.append(f"PRODUCERS names {stem}, which git does not track -- stale entry")
    for stem in EXEMPT:
        if stem not in figures:
            problems.append(f"EXEMPT names {stem}, which git does not track -- stale exemption")
    both = set(PRODUCERS) & set(EXEMPT)
    problems += [f"{s} is both produced and exempt" for s in sorted(both)]

    # A stale INVARIANT_GATED entry silently un-gates a figure: the name stops matching anything,
    # the figure quietly returns to pixel enforcement (or vanishes), and nobody is told.
    for stem in INVARIANT_GATED:
        if stem not in figures:
            problems.append(
                f"INVARIANT_GATED names {stem}, which git does not track -- stale entry")
        elif stem not in PRODUCERS:
            problems.append(f"INVARIANT_GATED names {stem}, which has no producer")

    # Moving a figure here is only legitimate if something else guards it. Each reason must name
    # the test file that took over, and that file must exist -- otherwise "invariant-gated" is a
    # euphemism for ungated, which is exactly how capability_grid came to have no test at all.
    for stem, reason in INVARIANT_GATED.items():
        named = [w.strip(" .,") for w in reason.split() if w.startswith("tests/")
                 or w.endswith("measurements()")]
        if not named:
            problems.append(
                f"INVARIANT_GATED[{stem}] does not name what guards it instead of the pixels")
            continue
        for guard in named:
            if guard.startswith("tests/") and not (REF / guard).exists():
                problems.append(
                    f"INVARIANT_GATED[{stem}] names {guard}, which does not exist")
    return problems


# Figures that READ another committed figure off disk. capability_grid's hero panel is
# `Image.open("hero.png")` with a silent `except: return gray(_terr)` fallback, so in a bare
# scratch directory it does not fail -- it quietly draws SOMETHING ELSE, and this checker would
# then report an unfixable 200x200 drift forever while CI stayed red for a reason no one could
# act on. It also means the figures have a BUILD ORDER: capability_grid must be rebuilt after
# hero, which an alphabetical loop gets wrong.
READS_FIGURES = {"capability_grid": ("hero",)}


# --------------------------------------------------------------------------------------------
# WHY PIXEL IDENTITY IS NOT ENFORCED FOR EVERY FIGURE.
#
# This checker originally failed on any pixel difference, and criterion H was ticked on that
# basis. CI disproved the premise. Three runs of the same workflow:
#
#     run 18  e8cca44  success, 14/14
#     run 20  bc03bf2  FAILURE -- archetypes, capability_grid, halfar_anatomy, landforms,
#                      screen_worlds drifted; landforms by 145469 px at max |delta| 254
#     run 21  c52087c  success, 14/14   <- the SAME CONTENT as run 20, merged to main
#
# Both runs installed identical versions (numpy 2.4.6, pillow 12.3.0, pytest 9.1.1,
# CPython 3.11.16, ubuntu-latest), and the local container matches. So this is neither PNG
# encoding nor dependency drift: the producers printed DIFFERENT NUMBERS.
#
#     canyon + strata pit-storage   5.22e+06 m3   vs   4.16e+06 m3
#     badlands relief / p99 slope   261 m / 35.3  vs   259 m / 35.2
#     Monument Valley relief        259 m         vs   268 m
#
# numpy 2.x dispatches SIMD kernels at runtime, GitHub's runner fleet is heterogeneous, and
# floating-point addition is not associative -- so reductions associate differently and the
# iterative erosion/flow loops amplify a last-bit difference into a visibly different field.
#
# halfar_anatomy has NO RNG AT ALL and still drifted (53 px). So "deterministic algorithm" is
# not the dividing line. The dividing line is how much the pipeline amplifies a last-bit
# difference, which is a property to be MEASURED, not reasoned about.
#
# A gate that is red or green depending on which runner picked up the job is not a weak gate,
# it is an unsound one: it does not test what it claims. So pixel identity is enforced only
# where it has been observed to hold, and the rest are gated on INVARIANTS -- assertions on
# the quantities the producers compute, which survive a change of kernel.
#
# ⚠️ THE EVIDENCE FOR THE PIXEL_EXACT SET IS WEAK AND SAYS SO. Nine figures holding across
# three runs is three samples, not a proof. `--sample` exists to accumulate more, and a figure
# is moved OUT of this set the first time it is observed to drift -- never back in without
# evidence.
INVARIANT_GATED: dict[str, str] = {
    "archetypes": "drifted run 20; pit-storage moved 20% (5.22e+06 -> 4.16e+06 m3). Guarded by "
                  "tests/test_archetypes.py on the facts _signature() computes.",
    "capability_grid": "drifted run 20, 173548 px. Guarded by tests/test_capability_grid.py.",
    "halfar_anatomy": "drifted run 20, 53 px -- no RNG anywhere in it, pure FP reduction order. "
                      "Guarded by halfar_anatomy.measurements() and its 25-test suite.",
    "landforms": "drifted run 20, 145469 px, the largest. Guarded by tests/test_landforms.py.",
    "screen_worlds": "drifted run 20, 9969 px; Monument Valley relief moved 259 -> 268 m. "
                     "Guarded by tests/test_screen_worlds.py.",
}


def rebuild(stem: str, workdir: Path) -> Path:
    """Run the producer's __main__ with workdir as CWD, and return the PNG it wrote.

    Every committed figure EXCEPT the one being rebuilt is copied in first, so a producer that
    reads one sees the same input a repo-CWD build would. The one being rebuilt is withheld on
    purpose: a producer that read its own committed output would reproduce it trivially, and the
    comparison would prove nothing.
    """
    for other in REF.glob("*.png"):
        if other.stem == stem:
            continue
        shutil.copy2(other, workdir / other.name)
    module = PRODUCERS[stem]
    if str(REF) not in sys.path:
        sys.path.insert(0, str(REF))
    cwd = os.getcwd()
    try:
        os.chdir(workdir)
        runpy.run_module(module, run_name="__main__")
    finally:
        os.chdir(cwd)
    produced = workdir / f"{stem}.png"
    if not produced.exists():
        wrote = sorted(p.name for p in workdir.glob("*.png"))
        raise AssertionError(
            f"{module}.py ran but did not write {stem}.png (it wrote {wrote or 'nothing'})")
    return produced


def pixels_differ(a: Path, b: Path) -> str | None:
    """None when identical; otherwise the first difference stated in pixels, not bytes."""
    import numpy as np
    from PIL import Image

    ia, ib = Image.open(a), Image.open(b)
    if ia.size != ib.size:
        return f"size {ia.size} rebuilt vs {ib.size} committed"
    if ia.mode != ib.mode:
        return f"mode {ia.mode} rebuilt vs {ib.mode} committed"
    na, nb = np.asarray(ia).astype(np.int32), np.asarray(ib).astype(np.int32)
    d = np.abs(na - nb)
    if not d.any():
        return None
    ys, xs = np.nonzero(d.max(axis=2) if d.ndim == 3 else d)
    return (f"{len(ys)} pixel(s) differ, max |delta| = {int(d.max())}, "
            f"first at (x={int(xs[0])}, y={int(ys[0])})")


def describe_machine() -> None:
    """What the pixels are being blamed on, printed so a drift can be correlated with hardware.

    The whole reason this mode exists: two runs with identical package versions disagreed, and
    without the CPU and the dispatched SIMD path in the log there was no way to test the
    obvious hypothesis. Print the evidence next to the result, every time.
    """
    import platform
    import numpy as np

    print("== machine " + "=" * 66)
    print(f"  platform   {platform.platform()}")
    print(f"  python     {platform.python_version()}  ({platform.machine()})")
    print(f"  numpy      {np.__version__}")
    try:
        from PIL import Image as _I
        print(f"  pillow     {_I.__version__ if hasattr(_I, '__version__') else 'unknown'}")
    except Exception:
        pass
    # numpy dispatches SIMD kernels at runtime; this names the ones it chose, which is the
    # hypothesis for why two runners disagree.
    try:
        simd = np.lib.introspect.opt_func_info()
        # {func: {dtype_char: {'current': 'X86_V4', 'available': 'X86_V4 X86_V3 baseline(...)'}}}
        # `current` is the kernel actually dispatched on THIS cpu -- the thing that differs
        # between runners and the reason two identical checkouts disagree.
        current = sorted({v["current"] for f in simd.values() for v in f.values()
                          if isinstance(v, dict) and "current" in v})
        avail = sorted({v["available"] for f in simd.values() for v in f.values()
                        if isinstance(v, dict) and "available" in v})
        print(f"  numpy dispatching: {', '.join(current) or '(none reported)'}")
        print(f"  numpy available  : {'; '.join(avail) or '(none reported)'}")
    except Exception as e:
        print(f"  numpy SIMD targets unavailable ({type(e).__name__})")
    try:
        model = [l.split(":", 1)[1].strip() for l in
                 Path("/proc/cpuinfo").read_text().splitlines() if l.startswith("model name")]
        if model:
            print(f"  cpu        {model[0]}  x{len(model)}")
        flags = [l for l in Path("/proc/cpuinfo").read_text().splitlines()
                 if l.startswith("flags")]
        if flags:
            interesting = [f for f in ("avx2", "avx512f", "avx512_vnni", "fma", "sse4_2")
                           if f" {f} " in flags[0] + " "]
            print(f"  cpu flags  {', '.join(interesting) or '(none of interest)'}")
    except Exception:
        pass
    print("=" * 77)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", metavar="STEM")
    ap.add_argument("--sample", action="store_true",
                    help="report the machine and every pixel delta, and ALWAYS exit 0. This is "
                         "evidence gathering, not a gate: run it on many runners to find out "
                         "which figures actually reproduce across hardware.")
    args = ap.parse_args()

    if args.sample:
        describe_machine()

    figures = committed_figures()
    problems = check_enumeration(figures)
    if problems:
        for p in problems:
            print(f"ENUMERATION: {p}")
        return 1
    print(f"enumeration: {len(figures)} committed figure(s), "
          f"{len(PRODUCERS)} produced, {len(EXEMPT)} exempt")

    todo = [s for s in figures if s in PRODUCERS]
    if args.only:
        unknown = sorted(set(args.only) - set(todo))
        if unknown:
            print(f"--only names unknown figure(s): {unknown}")
            return 1
        todo = [s for s in todo if s in args.only]

    # Build order: anything read by another figure goes first, so a rebuild never consumes a
    # stale copy of its input. Alphabetical order put capability_grid before hero and produced
    # exactly that bug -- a committed figure embedding the previous hero.
    needed_first = [d for deps in READS_FIGURES.values() for d in deps]
    todo.sort(key=lambda s: (s not in needed_first, s))

    drifted, tolerated = [], []
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for stem in todo:
            produced = rebuild(stem, work)
            delta = pixels_differ(produced, REF / f"{stem}.png")
            if delta is None:
                print(f"  {stem:22s} ok")
            elif stem in INVARIANT_GATED:
                print(f"  {stem:22s} differs (invariant-gated, not a failure): {delta}")
                tolerated.append(stem)
            else:
                print(f"  {stem:22s} DRIFT: {delta}")
                drifted.append(stem)
                produced.rename(work.parent / f"{stem}.rebuilt.png")

    if tolerated:
        print(f"\n{len(tolerated)} invariant-gated figure(s) differ in pixels: {tolerated}")
        print("Not a failure HERE -- these are the figures whose pixels are known to depend on "
              "the machine. What guards them is their invariant tests, which run in the suite.")
        print("But a difference on the SAME machine that built the PNG is still a real signal: "
              "if you see this locally after changing a producer, recommit the figure.")

    if args.sample:
        differing = sorted(set(drifted) | set(tolerated))
        print(f"\nSAMPLE: {len(differing)} of {len(todo)} differ on this machine: "
              f"{differing or 'none'}")
        print("Exit 0 regardless -- this mode gathers evidence, it does not judge. Record the "
              "machine block above beside the result; a figure that differs on hardware A and "
              "not on hardware B is the finding.")
        return 0

    if drifted:
        print(f"\n{len(drifted)} figure(s) no longer match their producer: {drifted}")
        print("Either the producer changed and the PNG was not recommitted, or the PNG was "
              "edited by hand. Rerun the producer and commit its output.")
        print("If this figure has now been observed to drift ACROSS MACHINES rather than "
              "because of a real change, move it to INVARIANT_GATED with the evidence -- and "
              "give it an invariant guard first, or the move is a silent loss of coverage.")
        return 1
    print(f"\n{len(todo) - len(tolerated)} figure(s) reproduce exactly; "
          f"{len(tolerated)} gated on invariants instead.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
