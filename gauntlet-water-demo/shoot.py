#!/usr/bin/env python3
"""Inspection path: render water.html and capture one frame.

Usage: python3 shoot.py gauntlet/shots/w1-r1.png

Fails loudly rather than writing a blank frame — a harness that quietly
produces an image of nothing is the inspection-rot failure this whole
mechanism exists to prevent (`11`).
"""
import sys
import pathlib
from playwright.sync_api import sync_playwright

out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "shot.png")
out.parent.mkdir(parents=True, exist_ok=True)
page_url = "file://" + str(pathlib.Path(__file__).parent.joinpath("water.html").resolve())

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium",
                          args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader",
                                "--disable-gpu-sandbox"])
    pg = b.new_page(viewport={"width": 900, "height": 600})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append("console." + m.type + ": " + m.text)
          if m.type == "error" else None)
    pg.goto(page_url)
    pg.wait_for_timeout(1800)          # let the shader compile and animate a little

    state = pg.evaluate("""() => {
        const c = document.querySelector('canvas');
        if (!c) return {ok: false, why: 'no canvas element'};
        const gl = c.getContext('webgl2') || c.getContext('webgl');
        if (!gl) return {ok: false, why: 'no webgl context'};
        // Read a few pixels: an all-black or all-one-colour frame means the
        // shader failed even though the page "loaded".
        const px = new Uint8Array(4 * 9);
        const pts = [[0.2,0.3],[0.5,0.3],[0.8,0.3],[0.2,0.5],[0.5,0.5],
                     [0.8,0.5],[0.2,0.8],[0.5,0.8],[0.8,0.8]];
        let i = 0, uniq = new Set();
        for (const [u,v] of pts) {
            const b = new Uint8Array(4);
            gl.readPixels(Math.floor(u*c.width), Math.floor(v*c.height), 1, 1,
                          gl.RGBA, gl.UNSIGNED_BYTE, b);
            uniq.add(b.join(','));
            i++;
        }
        return {ok: true, distinct: uniq.size, sample: [...uniq].slice(0,3),
                w: c.width, h: c.height};
    }""")

    pg.screenshot(path=str(out))
    b.close()

if errors:
    print("PAGE ERRORS:", *errors, sep="\n  ", file=sys.stderr)
if not state.get("ok"):
    sys.exit("inspection path broken: " + state.get("why", "unknown"))
if state.get("distinct", 0) < 3:
    sys.exit(f"inspection path suspect: only {state['distinct']} distinct pixel "
             f"values sampled — the shader is probably not drawing. {state['sample']}")
print(f"wrote {out} ({state['w']}x{state['h']}, {state['distinct']}/9 distinct samples)")
if errors:
    sys.exit("page reported errors (above) — fix before trusting the frame")
