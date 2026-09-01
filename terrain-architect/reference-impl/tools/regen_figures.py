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
    return problems


def rebuild(stem: str, workdir: Path) -> Path:
    """Run the producer's __main__ with workdir as CWD, and return the PNG it wrote."""
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", metavar="STEM")
    args = ap.parse_args()

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

    drifted = []
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for stem in todo:
            produced = rebuild(stem, work)
            delta = pixels_differ(produced, REF / f"{stem}.png")
            print(f"  {stem:22s} {'ok' if delta is None else 'DRIFT: ' + delta}")
            if delta is not None:
                drifted.append(stem)
                produced.rename(work.parent / f"{stem}.rebuilt.png")

    if drifted:
        print(f"\n{len(drifted)} figure(s) no longer match their producer: {drifted}")
        print("Either the producer changed and the PNG was not recommitted, or the PNG was "
              "edited by hand. Rerun the producer and commit its output.")
        return 1
    print(f"\n{len(todo)} figure(s) reproduce exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
