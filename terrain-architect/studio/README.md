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
- **AAA deferred-PBR surface + SatMap colour** (the Gaea-class look): the terrain renders through a
  **true deferred pipeline**. The terrain pass writes only **albedo** (SatMap colour + rock on steeps
  + snow) and a per-material **smoothness** into a G-buffer; a single fullscreen composite then does
  *all* the lighting from the height field:
  - **per-pixel surface normals** reconstructed from central differences of the height texture
    (finer than the mesh vertex normals),
  - **sun** (Lambert) **+ hemispheric sky-irradiance ambient** — a warm ground-bounce → cool sky-dome
    gradient, so shadowed faces read *blue* instead of flat grey (the single biggest realism lever),
  - **GGX microfacet specular** driven by material smoothness (soil rough, rock glossier, snow sheen)
    with a Schlick Fresnel,
  - **soft ray-marched cast shadows** toward a **movable sun** (azimuth + elevation sliders) and
    **horizon ambient occlusion** (crevice darkening), folded into the same pass,
  - a richer **analytic sky** (horizon→zenith gradient, sun disk, aureole, near-sun horizon scatter)
    and distance-tinted **aerial perspective**, resolved through **ACES** tone mapping and
    **supersampled** for anti-aliased silhouettes.
- **SatMaps genuinely derived from real satellite imagery** (not hand-picked): pick from ~13 palettes
  in the viewport (Temperate, Alpine, Verdant, Canyon, Arid, Dune, Volcanic, Mars, Lunar, Arctic,
  Tundra, plus **Estuary** and **Dusk** traced from Gaea SatMap-editor gradient strips — a per-column
  median of the bar, Dusk being the selected in-range window). **Seven are extracted from real
  public-domain top-down satellite/aerial imagery** — the
  source image is ordered by luminance into an elevation ramp by the skill's own `reference-impl`
  `extract_satmap`, the same method Gaea describes for its SatMap library, done reproducibly rather
  than by eye. Derived: **Alpine** (Ligurian Alps), **Dune** (Rub′ al Khali / Terra), **Verdant**
  (Amazon / Landsat), **Volcanic** (Icelandic lava / ESA), **Arctic** (Greenland), **Tundra**
  (Iceland / ESA), **Lunar** (LROC). The pipeline (`satmaps/extract_satmaps.py`) fetches from
  Wikimedia Commons (satellite-image categories guarantee orbital framing — no sky to pollute the
  ramp), masks out space + open ocean, and rejects false-colour / off-biome frames with a hue guard;
  provenance and licences are recorded in `satmaps/derived.json` (NASA/USGS = public domain, ESA =
  CC BY). Temperate/Canyon/Arid/Mars stay authored (labelled as such) where no on-biome true-colour
  source was found.
  - **Make your own in-app — SatMap Studio** (the **＋LUT** button). A **SatMap LUT is a 1-D colour
    gradient** — low elevation on the left → high on the right, baked to a 256-px strip and indexed by
    each point's normalised height. SatMap Studio is a **gradient editor** in a full-width bottom sheet
    (the 3D viewport stays visible above and **recolours live** as you edit):
    - **Drag stops** along the bar to set their elevation, **click the bar** to add one, **click a stop
      then pick its colour**, and remove with **－ Stop**. The **current terrain's elevation histogram**
      is drawn behind the bar, so a stop's position maps to how much of the surface it paints.
    - **Start from…** a built-in SatMap and tweak; toggle **Smooth ↔ Bands** interpolation; **Reverse**
      the ramp; and apply global **hue / brightness / contrast / saturation**.
    - **From image…** opens a photo panel: **Auto-extract** orders the whole image by luminance into a
      ramp (the same method as the derived built-ins), or click the image to **eyedrop** the selected
      stop's colour.
    - **Apply** bakes the LUT into the SatMap list and selects it. (Ordering is by brightness, the usual
      elevation proxy; the colour picker and eyedropper let you override any stop.)
- **Live 3D viewport** with **multi-stage rendering**: WebGL2 lit terrain mesh (SatMap / slope /
  grey shading, orbit + zoom, wireframe), rendered in two passes —
  1. **Opaque terrain + snow** — a snow-accumulation stage that settles snow on high, gentle ground
     and leaves steep faces bare, with a specular snow sheen (driven by a **Snow** effect node).
  2. **Translucent water** — a separate alpha-blended pass with depth-based colour (shallow teal →
     deep blue), a Fresnel edge, animated ripples, and shoreline foam. It uses a **hydrologically
     correct water surface**, not a flat cut through the heightmap:
     - **Lakes** (**FLOW** on) fill each closed basin to its own **spill level** via a
       **priority-flood depression fill** (Barnes 2014) — flat lakes whose edges follow the basin
       rim, at the right elevation for each basin.
     - **Rivers** (**River flow** param) are the **flow-accumulation** drainage network (D8 on the
       filled DEM): a thin water film that **follows the terrain downhill**, widening with catchment.
     - **Sea level** mode instead lays a flat ocean at a chosen level — the simple, level-based water.
     The water-surface normal is computed from that surface (flat in lakes, sloped along rivers). This
     is the same `priority_flood_fill` + `d8_accumulation` pair the reference-impl uses.

  **Screen-space (deferred) compositing — the fullscreen-triangle technique.** On WebGL2 the water and
  sky are drawn *without geometry*, the same way a skydome is rendered from one fullscreen triangle:
  the terrain renders into an offscreen **colour + depth** G-buffer, then a single fullscreen triangle
  reconstructs each pixel's world position from the depth texture and composites analytically —
  **sky** on the background, and **water** by sampling the water-height texture. Because it has the
  depth buffer and the terrain colour, the water gets **refraction** (the lakebed sampled with a
  normal-based offset), **Beer–Lambert depth absorption** from the real view-ray thickness, a
  **Fresnel** sky reflection, sun glint and soft foam — quality a forward transparent plane can't
  reach. (WebGL1 falls back to the forward geometry-water pass; wireframe uses it too. The one
  tradeoff is that terrain silhouettes lose the forward MSAA, softened by the device-pixel-ratio
  supersample on hi-dpi displays.)
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
| **Effect** | **Water** (Hydrology = lakes + rivers, or Sea = a flat level) · **Snow** · **SatMap** (colour LUT node) · **SatMap Blend** (merge two colour branches) |
| **Output** | Output (drives the viewport / export) |

**Water, snow and colour are nodes, not global switches.** Add a **Water**, **Snow** or **SatMap** node and
wire it into the pipeline (e.g. `… → erosion → Snow → Water → SatMap → Output`); the viewport picks up
whichever effect nodes feed the Output. The **Water** node's **Mode** is either **Hydrology** (basin lakes +
downhill rivers) or the simple **Sea level** (a flat ocean at a level). Effect nodes pass the height through
unchanged — they add a scene layer, so deleting one removes just that effect.

**The SatMap node — Gaea's colouring model.** In Gaea a SatMap is a *node* that colours a terrain through a
gradient, driven by **whatever grayscale you feed it** (not only height). This node mirrors that: it takes
an **In** (the height, passed through unchanged), an optional **Driver** input, and an optional **Mask**
input, with **Driven by** = *Driver ▸ / Height*, *Height*, or *Slope*. So you can colour by **elevation**
(the classic SatMap), by **slope** (cliffs one colour, benches another), or by **any field you wire into
Driver** (flow, a mask, a Blend). It picks a **Gradient** from the library (including ones you author in
SatMap Studio) and applies **Reverse**, **Range** (use just a slice of the gradient) and **Shift** (offset
the lookup) — the same transforms Gaea's SatMap node exposes.

- **Colour flows through the graph — branch, blend and stack.** Colour is resolved by walking the graph:
  a SatMap **composites its ramp over the colour already coming down its In chain** (so chaining
  `… → SatMap(base) → SatMap(rock) → Output` stacks them, each with **Opacity**, **Blend**
  (Normal / Multiply / Screen) and an optional **Mask**); a **SatMap Blend** node **merges two separate
  SatMap branches** — wire `SatMap A → A`, `SatMap B → B`, a mask into **Mask** — exactly Gaea's
  SatMap-combine; and any other node (erosion, filter) just passes colour through. So you can build a real
  colour graph — e.g. an elevation SatMap and a flow-driven SatMap blended by a slope mask. It's resolved
  per-vertex on the CPU into the terrain's albedo.
- **2D biome (altitude × slope).** Switch **Mode** to *2D biome* and the node blends **two** gradients — a
  flat-ground **Gradient** and a steep-ground **Steep gradient** — by slope: green valleys and gentle
  ground read from the first, cliffs and scree from the second. That's the classic 2D terrain LUT
  (altitude on one axis, slope on the other), built from two 1-D ramps.

With no SatMap node in the graph, the viewport falls back to the global SatMap dropdown driven by elevation.

## Controls

- **Double-click** empty canvas (or **＋ Add node**) to add a node.
- Drag a node's **right port** into another node's **left port** to wire them (cycles are rejected).
- Click a node to edit its parameters on the right; **Duplicate** / **Delete** or press <kbd>Del</kbd>.
  Deleting a mid-chain node **auto-bridges** its neighbours (its input source reconnects to its outputs)
  when the input is unambiguous, so the pipeline stays connected.
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
