# Terrain Studio — node-based WebGL terrain generator

A self-contained, single-file terrain generator that runs in the browser: a **node graph** drives a
live **WebGL 3D viewport**. It's the interactive companion to this skill's pure-NumPy `reference-impl/`
atoms — the same algorithms (fractal noise, domain warp, thermal & hydraulic erosion, histogram
equalisation, slope/height masks, real-DEM import) exposed as a graph you build and tune by eye.

**Open `index.html`** in any modern browser — no build step, no server, no dependencies. Everything
(UI, terrain kernels, WebGL renderer) is inline in that one file.

![Terrain Studio](../reference-impl/gallery.png)

## What it does

- **Node graph** (the core): drag nodes, wire outputs into inputs, and every node shows a live
  hill-shaded **thumbnail** of its own output — so you read the pipeline at a glance.
- **Live 3D viewport** with **multi-stage rendering**: WebGL2 lit terrain mesh (hypsometric / slope /
  grey shading, orbit + zoom, wireframe), rendered in two passes —
  1. **Opaque terrain + snow** — a snow-accumulation stage that settles snow on high, gentle ground
     and leaves steep faces bare, with a specular snow sheen (the ❄ SNOW toggle + line slider).
  2. **Translucent water** — a separate alpha-blended pass with depth-based colour (shallow teal →
     deep blue), a Fresnel edge, animated ripples, and shoreline foam. It uses a **hydrologically
     correct water surface**, not a flat cut through the heightmap:
     - **Lakes** (**FLOW** on) fill each closed basin to its own **spill level** via a
       **priority-flood depression fill** (Barnes 2014) — flat lakes whose edges follow the basin
       rim, at the right elevation for each basin.
     - **Rivers** (**FLOW** slider) are the **flow-accumulation** drainage network (D8 on the filled
       DEM): a thin water film that **follows the terrain downhill**, widening with catchment.
     - **Sea** (**≈ SEA** toggle + level) adds an optional flat global ocean for coastlines,
       combined with the lakes/rivers by taking the higher surface.
     The water-surface normal is computed from that surface (flat in lakes, sloped along rivers), and
     it's depth-tested against the terrain so everything clips cleanly at the shore. This is the same
     `priority_flood_fill` + `d8_accumulation` pair the reference-impl uses.
- **Real heightmaps as a base**: the **Import DEM** node has a one-click **Use real SRTM sample**
  (a real public-domain USGS/SRTM crop of the Colorado Plateau, embedded in the page) *and* loads your
  own PNG or square 16-bit `.r16` raw — including real USGS/SRTM tiles exported from
  `reference-impl/heightfield_io.py`. So you can add erosion and effects to real-world areas, then
  **Export** the result as a heightmap PNG. (An in-browser live fetch of the USGS/SRTM buckets isn't
  possible — they send no CORS headers — which is why `heightfield_io.py` does the fetching and the
  Studio imports the file, plus the embedded sample for zero-setup real terrain.)

### Node library (mirrors the reference-impl atoms)

| Group | Nodes |
|---|---|
| **Generator** | Perlin fBm · Ridged MF · Voronoi (F1/F2−F1) · Gradient (linear/radial) · Constant · **Import DEM** (file *or* one-click real SRTM sample) |
| **Combine** | Blend (factor or mask) · Combine (add/sub/mul) · Max/Min · Smooth Min (Quilez `smin`) |
| **Filter** | Warp (domain warp) · Terrace · Levels · Curve (bias/gain) · **Histogram EQ** · Blur · Clamp · Invert |
| **Erosion** | Thermal (talus) · Hydraulic (droplet sim, brush-distributed scour) |
| **Mask** | Slope select · Height select |
| **Output** | Output (drives the viewport / export) |

## Controls

- **Double-click** empty canvas (or **＋ Add node**) to add a node.
- Drag a node's **right port** into another node's **left port** to wire them (cycles are rejected).
- Click a node to edit its parameters on the right; **Duplicate** / **Delete** or press <kbd>Del</kbd>.
- Pan with **middle-drag** / space-drag / empty-drag; **wheel** to zoom the graph.
- In the 3D view: **drag** to orbit, **wheel** to zoom, <kbd>F</kbd> to frame.
- **Auto** recomputes on every edit; turn it off and use **Build** for heavy graphs.

## Design — learning from Gaea, World Machine and Houdini

The brief was to learn from the strengths *and* weaknesses of the three baselines:

- **Adopted — Gaea:** a per-node **live preview thumbnail** and beautiful, sensible defaults, so the
  graph is legible and the first result already looks like terrain.
- **Adopted — World Machine:** a clean, single-window **device-graph** model — generators → filters →
  erosion → output — with an explicit Output node, easy to reason about.
- **Adopted — Houdini:** real **procedural depth** (physically-motivated erosion, masks, warps that
  compose arbitrarily) rather than a fixed pipeline.
- **Avoided:** Houdini's learning cliff (approachable palette grouped by category, no network of
  wrangles to learn), World Machine's dated UI (a modern, calm dark theme with a considered
  hypsometric-amber accent), and node sprawl (a curated, meaningful node set — every node maps to a
  grounded atom, nothing decorative).

The palette is cool deep-slate grounds with a single warm **hypsometric sand/amber** accent (elevation
/ contour, from topographic cartography) and a restrained water-teal for flow; monospace, tabular
readouts give it the feel of a precision instrument. Light and dark themes are both first-class.

## How it relates to the rest of the skill

Compute runs on the **CPU** (deterministic `Float32Array` heightfields) so it mirrors the verified
`reference-impl/` algorithms exactly; the **WebGL** layer is the 3D render. It is a *look-and-feel*
authoring tool — the numerically-validated implementations, oracles and cross-checks live in
`reference-impl/`. Verified headless with Playwright (graph eval, WebGL init, all interactions,
import/export — no console/page errors) during development.
