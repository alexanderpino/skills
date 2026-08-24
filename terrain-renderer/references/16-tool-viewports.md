---
type: Reference
title: "Tool Viewports: Interactive Preview Rendering for Terrain Authoring"
description: "Tool viewports: interactive preview rendering for terrain authoring, and why the editor path is not the runtime path."
tags: [terrain, tools, viewport, authoring]
status: stable
generated: { by: process:claude-code, at: 2026-07-30T05:01:00Z }
---
# Tool Viewports: Interactive Preview Rendering for Terrain Authoring

The generator's graph recooks in seconds to minutes; the viewport must answer in milliseconds and
must never lie about what will export. This chapter is the rendering half of a Gaea/World
Machine-class authoring tool: the preview mesh path, the GPU derived-field passes, the
shading-mode palette, the brush feedback loop, and the parity discipline that keeps "what the
artist sees" equal to "what the engine gets". It serves terrain-architect's graph substrate (its
`14`: preview pyramid, dirty propagation, content-addressed cache) and consumes its Output
Contract (its `08`/`27`); the heavy rendering machinery it borrows is this skill's `01`, `06`,
`07`, `12`.

Contents: [The viewport contract](#the-viewport-contract) ·
[The preview mesh path](#the-preview-mesh-path) ·
[Derived-field passes on the GPU](#derived-field-passes-on-the-gpu) ·
[The shading-mode palette](#the-shading-mode-palette) ·
[The edit feedback loop](#the-edit-feedback-loop) ·
[Cameras, light rigs & comparison](#cameras-light-rigs--comparison) ·
[Export parity testing](#export-parity-testing) ·
[Performance envelope](#performance-envelope) · [Pitfalls](#pitfalls) ·
[Sources & provenance](#sources--provenance)

## The viewport contract

Three promises, written down before any viewport code. Every defect in this chapter's pitfall
list is a violation of one of them.

**1. WYSIWYG: the preview consumes the contract, not a copy of it.** The viewport renders the
*same fields* the export will emit — the Output Contract's R32F height, waterSurface/depth, splat
weights, and cause-maps (terrain-architect `08`) — never a private derivation. Where feasible it
runs the *same shader code* as the runtime reference: the splat/height-blend functions of `07`
compiled into the preview material, not a hand-rolled "close enough" lerp. Blend math is where
previews lie first — height-blend vs linear-blend on the same weights produces visibly different
terrain, and an artist who tuned masks against the wrong one has authored for a renderer that
does not exist. Share the HLSL/GLSL include; make divergence a build error, not a code review
hope.

**2. The pyramid promise: show what is ready, refine asynchronously, label what is shown.** The
graph runtime cooks a resolution pyramid (terrain-architect `14`: Q0 drag feedback, Q1 working,
Q2 final). The viewport renders the finest tier *resident now* and swaps tiers in as cooks land —
it never blocks a frame on a cook. The resolution actually on screen is labeled in the viewport
chrome, always. RESOLUTION_BOUND nodes (droplet erosion with fixed counts, anything with a
cell-unit parameter) legitimately look different per tier; the substrate flags them, and the
viewport must surface that flag as a visible "preview differs at build resolution" badge rather
than hide it. This is exactly the posture shipping tools take — Gaea's docs separate preview
resolution from build resolution and warn that some effects change across resolutions; the honest
tool says so on screen, per node.

**3. Staleness is displayed, never concealed.** Between an edit and its recook landing, the
viewport is showing an approximation (old cook, or local brush echo — below). A stale viewport
carries a badge. Users forgive latency; they never forgive a preview that silently showed them
something the build contradicts — that trust, once lost, is lost for the product.

## The preview mesh path

The preview is a heightfield renderer with a small budget, not a shipped-game terrain system.
Take `01`'s machinery at its cheapest honest setting:

- **Geometry**: a CDLOD-style quadtree or a 3–4 ring clipmap over a flat grid, vertex-displaced
  from the height texture. Preview domains are one field, not a streamed world; 60–200k triangles
  covers a 4k terrain at working quality. Keep the crack contract anyway (morph or skirts) —
  cracks in a tool viewport read as *terrain* defects and send artists chasing graph bugs that do
  not exist.
- **Displacement source**: the pyramid tier's height texture, R32F (or R16F + scale/offset for
  iGPU bandwidth — but derive normals from the R32F, `09`-style precision paranoia is not needed
  at tool domain sizes).
- **Dirty-region reupload**: recooks and brush echoes invalidate *regions* (terrain-architect
  `14`'s region invalidation). Upload only tile-aligned sub-rects of the height/aux textures —
  partial texture updates, 64–256 px alignment to match the cook's tile grid. Full-texture
  reuploads on every stroke are why naive tool viewports hitch.
- **Upload ring**: stage uploads through a persistent ring buffer, double-buffered so the UI
  thread writes frame N+1's rects while the GPU consumes frame N's — the `06` upload doctrine
  scaled down. The UI thread never maps a buffer the GPU holds and never stalls on a fence;
  a viewport that stutters during a param drag has failed at its one job.
- **LOD freeze/pin**: a toggle that locks the LOD selection (freeze the selection camera, keep
  flying the view camera — the `11` debug staple). Mandatory for comparisons: an A/B of two graph
  versions must diff *fields*, not LOD state; without the pin, half of every "the erosion changed
  the silhouette" report is actually the quadtree cutting differently.

## Derived-field passes on the GPU

The generator ships analysis fields (flow, wetness, curvature — terrain-architect `08`; runtime
consumption in `14` of this skill), and the viewport *never re-derives what the contract already
carries*. But screen-rate derived data — normals after a brush stroke, hillshade under a dragged
sun — is viewport work: tiny compute/fragment passes, microseconds at preview resolutions.

**Height → normal (central differences).** The workhorse; also the most commonly botched pass:

```hlsl
// heights in METRES; cell = world metres per texel OF THE BOUND TIER, not of the export res
float hL = H(uv - float2(du,0)), hR = H(uv + float2(du,0));
float hD = H(uv - float2(0,dv)), hU = H(uv + float2(0,dv));
float3 n = normalize(float3((hL - hR) / (2*cell), 1.0, (hD - hU) / (2*cell)));
```

The gotchas, each a shipped bug in some tool:

- **World-space denominator.** `2*cell` is metres. Divide by texels ("/ 2.0") and slope becomes a
  function of texture resolution: the Q0 preview shows slopes 4–8× flatter than Q2, talus masks
  tuned in preview break at build. If height is a normalized 0–1 texture, multiply by the height
  scale in metres *before* the divide. This one error explains most "the preview lighting doesn't
  match the build" reports.
- **Half-texel alignment.** Heights are texel-center samples. The vertex displaced by texel
  (i,j) and the normal evaluated for it must use the same convention — `uv = (ij + 0.5)/N` both
  places — or shading shifts half a cell against geometry and every ridge lights up one texel to
  the side of its silhouette.
- **Tier changes change `cell`.** When the pyramid swaps Q0→Q1, the constant buffer's cell size
  must swap with it. Bind it per-draw from the tier descriptor, never bake it.
- **Sobel/Horn when noisy.** Central differences amplify single-texel noise (R16-quantized
  intermediates, droplet speckle). A 3×3 Sobel — Horn's method in GIS terms, weighted 3×3 sums
  over `8*cell` — is central differences plus cross-axis smoothing; use it for display normals,
  keep plain central differences when you want the speckle *visible* (it is a diagnostic).

**Hillshade.** Lambert of the normal against a sun from UI azimuth/elevation — the classic
cartographic read, defaults 315° azimuth / 45° altitude (the GIS convention; ESRI's published
formula is exactly `cos(zenith)·cos(slope) + sin(zenith)·sin(slope)·cos(azimuth − aspect)` —
which is N·L in slope/aspect form). Give the artist both angles as drags, and a **sun sweep** button:
animate azimuth through 360° over a few seconds. Grid-aligned artifacts — D8 stripes, terracing,
lattice anisotropy — *strobe* under a rotating sun and hide under a fixed one; this is the single
highest-value qualitative check in terrain review (terrain-architect `09` doctrine, rendered
here).

**Slope / aspect / curvature false-color.** Slope on a perceptual ramp, aspect as hue, curvature
on a *diverging* ramp centred at zero (sign matters: ridge vs valley). These are one-liner
fragment passes over the derived normal — but route curvature from the contract field when the
graph shipped one; re-deriving it invites the divergence rule below.

**Contour lines, in-shader, fwidth-antialiased.** Naive `fract(h/interval) < w` shimmers and
aliases — line width in *height* units maps to wildly varying screen widths. Normalize by the
screen-space derivative (the standard AA-grid construction):

```hlsl
float g = h / interval;                       // h in metres
float d = abs(frac(g + 0.5) - 0.5) / max(fwidth(g), 1e-6);   // distance to contour, in pixels-ish
float line = 1.0 - saturate(d);               // ~1 px AA line
line *= saturate(2.0 - 2.0*fwidth(g));        // fade out where contours pack below ~2 px apart
```

Fade is not optional: where spacing drops below pixel size, unfaded contours merge into flickering
noise on every cliff. Draw every 5th/10th contour heavier (index contours) for readability.

**Water overlay.** Preview water is `12`'s fullscreen-triangle machinery stripped to a data
overlay — not its ocean shading pipeline: one
vertex-ID triangle (three vertices, no buffers — the standard fullscreen-pass idiom), reconstruct
world position from the depth buffer, sample `waterSurface(x,z)` from the contract field, and
where `waterSurface > groundY` tint by `waterDepth` with a cheap exponential absorption. This
shows shoreline placement, lake levels, and river continuity at zero geometry cost and is honest
about what it is: a data overlay, not a water render. Route to `12` only when the tool offers a
"final look" mode.

**Aux overlays.** Flow (`log(A)`), wetness, AO, snow — alpha-composited over hillshade, straight
from the `14` aux textures at the resident tier, one shared overlay shader with a ramp LUT per
field. Log-scale flow or the network is invisible; diverging ramps for signed fields; and sample
these masks as **linear data, never sRGB** (below).

## The shading-mode palette

Modes are a first-class feature with hotkeys, not a debug leftover — this is the viewport-side
mirror of terrain-architect `09`'s review modes and this skill's `11` debug views. The doctrine is
**match the view to the defect**; a tool that only has "textured" has hidden every defect the
texture hides.

| Mode | Renders | Defect it exposes |
|---|---|---|
| **Clay / matcap** | Geometry only, neutral material, view-space normal lookup | Shape without material distraction; faceting, terracing, quantization combs |
| **Hillshade** | Lambert vs UI sun | Relief read, drainage texture; the default working mode |
| **Sun sweep** | Hillshade, azimuth animated | Grid-aligned artifacts strobe: D8 stripes, lattice anisotropy, terrace combs |
| **Textured** | The export material path (`07` shaders, contract splats) | What ships; material-band errors — but hides geometry defects, never review in it alone |
| **Per-map false color** | Any single contract/aux field on a ramp | Mask range/clipping, NaN flags (magenta), dead channels, sRGB damage |
| **Splat weights** | Weights as RGB(+overflow flag) | Weights not summing to 1, layer bleed, resolution mismatch vs height |
| **Checker / tiling** | World-space UV checker + detail-tile repeat | Texel density drift, tiling cadence, UV seams and stretching on slopes |
| **Seam inspection** | Tile borders highlighted; normals/height diffed across edges | Apron violations: lighting seams, one-texel height steps at tile edges |
| **Wireframe** | Triangle edges over clay | Preview mesh density, crack contract, sliver triangles on cliffs |
| **LOD bands** | LOD level as false color | Where the preview coarsens; must be checked with LOD pin before any A/B verdict |
| **Contours** | fwidth-AA isolines over any mode | Flat-area noise, dam/basin levels, absolute-height blunders |
| **Water/flow overlay** | Fullscreen composite of waterSurface / log-flow | Rivers that stop, shorelines off datum, disconnected basins |

Every mode renders *the contract fields*; none may modify them. Modes compose: contour overlay ×
hillshade × water overlay is the standard review stack.

## The edit feedback loop

**Cursor projection.** The brush ring must sit *on* the terrain. Two implementations: (a) GPU
picking — a 1×1 (or small) readback of height/ID under the cursor rendered into an offscreen
target, asynchronously, 1–2 frames latent (fine for a cursor; never stall the pipe for it — `08`
readback discipline); (b) CPU raymarch of the resident height tier — no latency, and the tool
already holds the field. Prefer (b) for heightfields; (a) generalizes to meshes and overhangs.
Draw the ring as a projected decal conforming to the surface (project in the shader against the
height texture), not a flat screen-space circle — artists judge brush radius against terrain
features.

**The two-speed echo.** A brush stroke must read back in the same frame, but the truth is a graph
recook that takes seconds. Run both, honestly:

```
FAST (this frame, <16 ms, preview tier only):
    splat brush kernel into previewHeight, dirty rect R
    recompute previewNormal over R ⊕ 1 texel          # the apron rule, again
    redraw; set viewport badge = APPROXIMATE
SLOW (async, authoritative):
    append stroke to the sculpt/stamp node's stroke list (a graph edit)
    dirty propagation recooks downstream (terrain-architect 14, region-limited where legal)
    on cook landing with generation ≥ latest edit:
        upload cooked rects via the dirty-region path; clear badge
```

The fast path is a *lie by omission* — it shows the brush and nothing downstream. If erosion,
snow, or flow nodes sit below the sculpt node, the final terrain will differ from the echo. The
honesty rule: the APPROXIMATE badge stays up until the authoritative cook replaces the echo, and
the replacement is atomic per region (swap the rect when its cook lands; never blend echo and
cook — the blend is a third terrain nobody authored). If the recook is cancelled or fails, roll
the echo back to the last cooked state; an echo that persists as if final is the worst lie in
this chapter.

The loop, both speeds at once:

```
                       brush stroke
                      /            \
    FAST — this frame, <16 ms       SLOW — async, authoritative
    splat kernel into the           append stroke to the sculpt node;
    preview tier; normals           dirty propagation recooks
    over R ⊕ 1 texel                downstream (seconds)
                      \                         |
                       v                        | cook lands with
             +-------------------+              | generation >= latest edit
             |     viewport      | <------------+
             | badge:APPROXIMATE |   atomic per-region swap of cooked
             +-------------------+   rects, badge clears — never blend
                                     echo and cook
```

**Normal apron on partial updates.** The `⊕ 1 texel` above is load-bearing: normals at the dirty
rect's border read neighbors outside it. Re-normal exactly the dirty rect and you fossilize a
one-texel lighting seam around every stroke — the tool-scale replay of the chunk-apron bug (`11`).
Dilate the normal pass by the derivative stencil radius (1 for central differences, 1 for Sobel).

**Undo.** Undo operates on *graph state* — parameters and stroke lists — never on viewport
pixels. Because cooks are content-addressed (terrain-architect `14`), the pre-edit result is
usually still cached and undo is a cache hit: instant, exact. This is the decisive argument
against letting the viewport's echo become the document; a tool that undoes by inverse-brushing
pixels drifts from the graph and can never re-cook to a matching state.

## Cameras, light rigs & comparison

- **Orbit/turntable**: default; pivot at a picked terrain point (use the cursor projection), not
  the domain center — orbiting a far-off center is the most-reported camera annoyance in terrain
  tools. **Fly**: WASD + mouselook, speed scaled by height-above-terrain so one binding serves
  valley and orbit. **Ortho top-down**: for stamp/mask placement and tiling checks — this is
  terrain-architect `09`'s plan-view doctrine (structure reads from above; seams and drainage
  errors are near-invisible in perspective). Ship all three; artists verify correctness in plan
  and conviction in perspective, and neither substitutes for the other.
- **Light rig presets**: raking NW (315°/45°, the cartographic default), low sun (10–20°
  elevation — relief and terracing), overhead (albedo/material check, kills shape), sweep
  (animated). One hotkey each; a light the artist won't move is a defect the artist won't find.
- **A/B wipe**: two cached cooks (graph version N vs N−1, or pre/post an erosion node), one
  camera, LOD pinned, a draggable split. Implement as two height/aux texture sets and a screen-x
  branch in the shaders — *not* two viewports, whose cameras desynchronize. Diff mode (signed
  difference on a diverging ramp) belongs beside the wipe; the wipe shows *where*, the diff shows
  *how much*.
- **Golden thumbnails**: on every node-parameter commit, render a fixed-camera, fixed-light,
  fixed-mode (hillshade) thumbnail of the node's output at Q0/Q1 and store it with the graph.
  This is the `11` golden-image regression discipline running continuously inside the tool: node
  history becomes visually diffable, and "this node changed output after the library update" is a
  thumbnail compare, not an investigation.

## Export parity testing

The final WYSIWYG enforcement: render the preview and the engine target **from the same exported
fields** and diff the images. Same camera transform, same sun, both outputs to linear float
targets, per-pixel diff with a tolerance band. This one harness catches quantization, Y-flips,
scaling, and blend divergence in minutes — defects that otherwise surface as artist bug reports
weeks after the graph shipped. Run it in CI on the validation-suite terrains (terrain-architect
`09`'s cone/step/extreme-range inputs are ideal: each classic importer bug has a signature on
them).

The classic importer gotchas the harness must cover — every one of these has shipped:

| Gotcha | Symptom in the diff | Root cause |
|---|---|---|
| Row order / Y-flip | Terrain mirrored N–S; diff is structured, huge | Image top-down vs field bottom-up convention |
| R16/PNG16 scaling | Uniform vertical scale error or terracing | 0–65535 mapped to wrong metre range; e.g. UE's Z-scale formula (`maxHeight_m × 100 × 0.001953125`) skipped or misapplied |
| Edge vertex ownership | One-cell drift accumulating across tiles | 2^n texels vs 2^n+1 vertices; shared border texel owned by both/neither tiles |
| Handedness / up-axis | Aspect-dependent lighting mismatch | Y-up tool vs Z-up engine; normal G-channel flip |
| Units | ~100× scale error | Metres (tool) vs centimetres (UE) |
| sRGB on data maps | Splats/masks brighter mid-range, blend weights wrong | Data textures imported with sRGB flag set |
| Half-texel registration | Everything offset half a cell; ghost ridges in the diff | Texel-center vs texel-corner disagreement between tool and importer |

Debug mismatches at the pixel: capture both renders in RenderDoc and use pixel picking / pixel
history on a disagreeing pixel — it identifies which pass and which input texture diverged far
faster than staring at the shaders. Quantization checks specifically: export, re-import the
exported R16, and render it in the viewport ("round-trip view"); the difference against the R32F
preview *is* the quantization the engine will see, made visible before shipping (terracing on the
0–20 km extreme-range control, concentric rings in AO).

## Performance envelope

Tools run on artist hardware: assume an integrated GPU and a 4k-display laptop as the floor, not
a 4090. Budgets (F-tier practice, assert per `11` discipline):

| Item | Budget (iGPU floor) |
|---|---|
| Viewport frame, working mode (hillshade, Q1 1024²) | ≤ 8 ms GPU |
| Derived passes (normal + hillshade + overlays, 1024²) | ≤ 0.5 ms |
| Brush echo (splat + re-normal + redraw) | ≤ 16 ms end-to-end |
| Dirty-rect upload per frame | ≤ 1–2 MB (ring-buffered) |
| Cursor picking readback latency | ≤ 2 frames, async only |

**Degrade order: resolution first, shading second, interactivity never.** Under load, drop the
rendered pyramid tier (Q1→Q0) or the render scale; then drop the shading mode (textured →
hillshade); never let input latency grow or frames queue. A crisp viewport at 512² beats a
stuttering one at 2048² for every authoring task; artists tolerate coarse, they cannot tolerate
laggy brushes.

**Cook/viewport GPU contention.** The graph cooks on the same GPU that draws the viewport, and an
unthrottled cook starves the redraw — the "everything freezes during erosion" complaint. Rules:
split cook dispatches into slices bounded to a few milliseconds (no 500 ms megakernels — they
also trip OS GPU watchdogs); submit cook work at lower priority or on an async compute queue
where the API offers one, but do not trust queue priority alone — timeslice regardless; monitor
the present interval and throttle *the cook* when it slips, never the viewport; keep cooks
cancellable between slices (terrain-architect `14`'s generation-counter cancellation) so a fresh
param drag preempts a stale cook instead of queueing behind it.

## Pitfalls

- **The preview that lies**: viewport blend/splat math diverges from the export target's; masks
  get tuned against the wrong renderer. Share shader source with the runtime reference (`07`);
  enforce with the parity harness, not policy.
- **Texel-unit normals**: derivative denominator in texels, not `2 × cell` metres — slopes
  visually wrong at every non-default resolution, and *differently* wrong per pyramid tier. Bind
  the tier's world cell size per draw.
- **Stale normal borders**: partial update re-normals exactly the dirty rect; one-texel lighting
  seams fossilize around every brush stroke. Dilate by the stencil radius — the apron rule.
- **sRGB'd data maps**: splat weights or masks bound as sRGB views; false-color ramps and blends
  silently nonlinear. All contract fields are linear data; assert view formats at bind time.
- **Contour shimmer**: `fract` threshold without fwidth normalization; lines alias, crawl under
  camera motion, and merge into noise on cliffs. Use the AA construction plus the density fade.
- **Echo divergence trusted**: brush echo (local splat) presented as final while downstream
  erosion/snow nodes will change the result; artist "fixes" terrain that was never broken. Badge
  until the recook lands; atomic per-region replacement; roll back on cancelled cooks.
- **Full-texture reupload per stroke**: viewport hitches exactly when the artist is mid-gesture.
  Tile-aligned dirty rects through a double-buffered staging ring, always.
- **Unpinned-LOD comparisons**: A/B verdicts contaminated by different quadtree cuts. LOD freeze
  is a precondition of every comparison mode, enforced by the tool, not remembered by the user.
- **Hidden resolution**: viewport silently showing Q0 while the artist judges detail; erosion
  "lost all its detail" reports that are just the pyramid tier. Label the shown resolution in the
  chrome, badge RESOLUTION_BOUND nodes.
- **Cook starves redraw**: monolithic GPU cook dispatches; viewport freezes, watchdog kills the
  device on big graphs. Timeslice, deprioritize, monitor present interval, throttle the cook.

## Sources & provenance

Most of this chapter is engineering practice: the conventions of shipped terrain tools (Gaea,
World Machine, Houdini heightfields, in-engine editors) and general real-time technique applied
to the authoring loop. That is **F-tier** by this skill's ledger — stated honestly below; the
externally-groundable pieces carry their sources. URLs listed were fetched and read for this
chapter.

| Tier | Source | Grounds | URL |
|---|---|---|---|
| **D** | Gaea docs, "Understanding Resolution" (QuadSpinner) | Preview vs build resolution split; official warning that some node effects change across resolutions — the "resolution-bound nodes preview differently" reality | https://docs.quadspinner.com/Guide/Using-Gaea/Resolutions.html |
| **P** | GPU Gems 3, ch. 1 (NVIDIA) | Normals as the normalized gradient of the field via central differences (±1 texel samples per axis) | https://developer.nvidia.com/gpugems/gpugems3/part-i-geometry/chapter-1-generating-complex-procedural-terrains-using-gpu |
| **D** | ESRI ArcGIS Pro, "How Hillshade works" | Hillshade formula (`cos z·cos s + sin z·sin s·cos(az−aspect)`), 315°/45° defaults, Horn-style 3×3 slope/aspect over `8 × cellsize` | https://doc.esri.com/en/arcgis-pro/latest/tool-reference/3d-analyst/how-hillshade-works.html |
| **F** | Evan Wallace, "Anti-Aliased Grid Shader" | The fract + fwidth screen-derivative AA-line construction used for contours; why naive fract lines shimmer | https://madebyevan.com/shaders/grid/ |
| **F** | Sascha Willems, fullscreen quad-without-buffers post | Vertex-ID fullscreen triangle (3 verts, no buffers) as the standard fullscreen-pass idiom, used here for the water/aux composite | https://www.saschawillems.de/blog/2016/08/13/vulkan-tutorial-on-rendering-a-fullscreen-quad-without-buffers/ |
| **D** | Unreal Engine docs, "Importing and Exporting Landscape Heightmaps" | 16-bit PNG/r16 import path; the Z-scale conversion (`maxHeight_m × 100 × 0.001953125`) cited in the importer-gotcha table | https://dev.epicgames.com/documentation/unreal-engine/importing-and-exporting-landscape-heightmaps-in-unreal-engine |
| **D** | RenderDoc docs, "How do I inspect a pixel value?" | Pixel picking and pixel history as the parity-debugging workflow | https://renderdoc.org/docs/how/how_inspect_pixel.html |
| **F** | — | Two-speed brush echo, staleness badging, upload-ring staging, LOD pin for comparisons, degrade order, cook timeslicing, golden thumbnails, the budget table: production tool-engineering practice with no single canonical citation; validate per `11` | — |
| **T/F** | — | Sun-sweep review (rotating azimuth strobes grid-aligned artifacts): community/GIS review practice, canonized in terrain-architect `09`; no primary citation fetched | — |
