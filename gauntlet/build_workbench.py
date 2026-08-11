#!/usr/bin/env python3
"""Bake gauntlet/workbench.template.html into a single self-contained page.

The Artifact CSP blocks every external host, so each evidence PNG is downscaled,
re-encoded as JPEG and inlined as a data URI. Output is gitignored: the template
and this script are the source, the HTML is a build product.

    python3 gauntlet/build_workbench.py [out.html]
"""
import base64
import io
import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"

# marker -> (file in evidence/, max width in px, jpeg quality)
FIGURES = {
    "__IMG_POOL__": ("w4-optics-r1.png", 1200, 88),
    "__IMG_ZOOM__": ("w4-optics-r1-zoom.png", 1000, 88),
    "__IMG_W1__": ("w1-optics-r1.png", 720, 82),
    "__IMG_W2__": ("w2-optics-r2.png", 560, 82),
    "__IMG_W3__": ("w4-optics-r1.png", 560, 82),
    "__IMG_VOR__": ("physics-voronoi-vs-caustic.png", 1400, 82),
    "__IMG_WAKE__": ("physics-eikonal-wake.png", 1300, 86),
}


def data_uri(path: pathlib.Path, max_w: int, quality: int) -> tuple[str, int]:
    im = Image.open(path).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    raw = buf.getvalue()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii"), len(raw)


def main() -> int:
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "workbench.html"
    html = (HERE / "workbench.template.html").read_text(encoding="utf-8")

    total = 0
    for marker, (name, max_w, quality) in FIGURES.items():
        src = EVIDENCE / name
        if not src.exists():
            print(f"missing evidence: {src}", file=sys.stderr)
            return 1
        uri, nbytes = data_uri(src, max_w, quality)
        html = html.replace(marker, uri)
        total += nbytes
        print(f"  {name:38s} {nbytes / 1024:7.0f} KB")

    left = [m for m in FIGURES if m in html]
    if left:
        print(f"unreplaced markers: {left}", file=sys.stderr)
        return 1

    out.write_text(html, encoding="utf-8")
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB, {total / 1024:.0f} KB of it image)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
