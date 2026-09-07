---
type: Technique
title: Shader craft — the fetch, the derivative, and the depth token
description: "Seven heightfield-specific shader hazards no general PBR or engine text teaches, four of them undefined behaviour by specification and all seven compiling: derivatives at LOD seams and inside a divergent march, explicit-LOD fetch in a max-mip traversal, virtual-texture gradient scaling and feedback bias, depth-output direction under both depth conventions, divergent resource indices, and the grazing terms — pow on a negative base, normalize of a vector that vanishes in fp16, and the saturate/clamp NaN semantics HLSL and GLSL do not share."
tags: [rendering, rasterizer, shading, hlsl, glsl, real-time, near-real-time]
status: draft
generated: { by: process:claude-code, at: 2026-09-06T00:00:00Z }
sources:
  - { id: d3d11spec, tier: F, locator: "§16.2 for the 2x2 block as the minimum atom of shader execution and the dummy invocations off the edge of a primitive; §16.8.1 for what makes a loop varying flow control; §16.8.2 (a) for the derivative and implicit-LOD instructions forbidden there and (b) for sample_l and sample_d being unrestricted; §16.9.2 for oDepth disabling early z; §16.9.3 and §16.9.3.1 for conservative output depth and which comparison mode each token is compatible with; §16.9.3.2 for the clamp implementations may apply; §16.13 for helper invocations, their outputs being valid but ignored, and the UAV-into-a-derivative rule; §3.1.5 for full float16 mandating round-to-nearest-even and preserved denorms, against §7.20.2.2.1 where 16-bit MIN-precision arithmetic may flush float16 denorms to 0 and may truncate instead of rounding; §22.19.1 for _sat as min(1.0f, max(0.0f, value)) and sat(NaN) = 0, over the min and max instructions of §22.10.11 and §22.10.10" }
  - { id: glsl460, tier: F, locator: "§7.1.5 Fragment Shader Special Variables, gl_HelperInvocation — helper invocations exist to evaluate derivatives, 'computed implicitly in the built-in function texture()'; §8.2 Exponential Functions — pow, 'Results are undefined if x < 0'; §8.3 Common Functions — clamp as min(max(x, minVal), maxVal), and min/max defined by a bare comparison with no NaN carve-out; §8.14.1 Derivative Functions — 'Derivatives are undefined within non-uniform control flow', and the forward/backward-differencing definition over the 2x2 stamp" }
  - { id: nonuniform_idx, tier: F, locator: "the Resource Binding document's § 'Divergence and derivatives' — the LOD-undefined sentence, the compiler's uniformity assumption, the undefined result without the intrinsic, and 'sufficient to apply NonUniformResourceIndex to any index'; its § 'Shader Derivatives and Divergent Indexing' for the per-lookup cost; the GL_EXT_nonuniform_qualifier extension's Mapping to SPIR-V section, 'nonuniformEXT -> NonUniformEXT decoration on variables'; and the SPIR-V core grammar spirv.core.grammar.json, Decoration value 5300, enumerant NonUniform with NonUniformEXT as an alias, version 1.5, extension SPV_EXT_descriptor_indexing" }
  - { id: tevs2008, tier: P, locator: "§3.1 Data Structure for the max-reduce mipmap whose texels this document forbids filtering; §3.2 Intersection Algorithm for the traversal loop whose fetch must be explicit-LOD" }
  - { id: mittring2008, tier: F, locator: "§2.3.6 Computing the Local LOD, and §2.3.6.4 the feedback pre-pass; §2.3.2.2 Efficient Filtering Through Borders for the 1-texel and 4-texel border widths (1 for bilinear, 4 for DXT block compression, verbatim -- never a 2-4 range). ⚠️ That section DECLINES anisotropic filtering outright ('we haven't done any implementation so we skip it here'), so it does not carry an aniso cap and is not cited for one" }
  - { id: barrett2008, tier: F, locator: "the software page-table indirection and the feedback loop whose resolution the mip request has to be corrected for" }
  - { id: reed2015, tier: F, locator: "the section The Effects of Roundoff Error — the simulated indistinguishable-and-swap error table, whose reversed-Z float32 row is the zero-error one" }
  - { id: bruneton2010, tier: P, locator: "§5.2 eq. 26, the roughness-aware Fresnel fit — the grazing term whose `pow` base is the one that goes negative" }
---
# Shader craft — the fetch, the derivative, and the depth token

**Tier: real-time rasteriser and near-real-time march — one list serves both.** Every rendering
document in this corpus is written for someone who already writes shaders. They say *which* fetch,
*which* derivative and *which* depth convention, and they do not teach the craft around it. This
document is that craft, and only the part of it that belongs to nobody else.

**Scope, stated as two exclusions rather than left to inference.** Microfacet BRDF theory — the
rendering equation, the distribution, geometry and Fresnel terms, material models, and the display
transform — belongs to the **physically-based-rendering** skill, and nothing here restates it; the
one BRDF expression that appears below appears only because its `pow` base is the one that goes
negative. The frame budget, its profiling, the frame graph and GPU-driven rendering in general
belong to the **game-engine-guru** skill, and nothing here prints a per-stage millisecond split.
Read both. What is left over is heightfield-specific and is what follows: seven hazards, five of
them already sitting in the failure table of one or more of the eleven rendering documents and
harvested here rather than invented, so those eleven can cite one place. ⚠️ **The other two are
not harvested, and are marked where they appear**: the fp16 `normalize` collapse and the cross-API
`saturate`/`clamp` divergence are derived here against the specifications, and no document in the
corpus carries either. **Four of the seven are undefined behaviour by specification** — the
derivative inside varying flow control, `pow` on a negative base, a divergent resource index
without the qualifier, a broken conservative-depth promise — and every one of the seven compiles.

## Use this

**Take every texture fetch inside a loop, and every fetch at a ray hit, off the implicit-derivative
path — explicit LOD or explicit gradients, always — and name the depth-output direction against
your depth convention rather than against the word "conservative".** Those are the two that take
judgement. Everything else below is a closed form, a token or a qualifier, and is checkable by
reading the shader. Eight lines for the seven hazards — the derivative one needs two, because
inside the loop and at the hit are different failures with different fixes:

```
1. In a loop with a per-pixel iteration count: SampleLevel or Load. Never Sample, never
   SampleBias, never CalculateLevelOfDetail.        [d3d11spec] §16.8.2, [glsl460] §8.14.1
2. At a ray hit: SampleGrad with ray-differential gradients. Never ddx/ddy of the hit.
3. Max-mip traversal: Load, or SampleLevel with a POINT sampler. A bilinear tap under-states
   the max bound, and the safe-skip test then walks past hits.
4. Virtual texture: gradients from VIRTUAL UVs, scaled by s = virtualSize/(poolSize*2^pageMip).
5. Feedback pass: request mip = computeMip(virtualUV) - log2(feedbackScale).
6. Depth output: SV_DepthLessEqual under reversed-Z. SV_DepthGreaterEqual under standard Z.
7. Per-pixel material or page index: NonUniformResourceIndex (HLSL) / nonuniformEXT (GLSL).
8. Grazing terms: saturate BOTH ends of a pow base; branch AROUND a normalize whose vector
   can vanish. In fp16 it vanishes at 1.7e-4 per component at BEST, and at 7.8e-3 where
   float16 denorms are flushed -- 45x worse.             [d3d11spec] §3.1.5, §7.20.2.2.1
```

**What it beats.** *Reading the two sibling skills and assuming the rest transfers* — both are
correct and neither says a word about an explicit-LOD fetch inside a divergent traversal, because
neither is about heightfields. *A global negative texture LOD bias* — the standard response to
"the terrain looks blurry", which treats the symptom of an unscaled gradient and poisons weight
maps, ID maps and page tables on the way past; `virtual-texturing.md` carries that as its own
failure row. *Compiling on one API and looking at the frame* — the four undefined-behaviour hazards
named above all compile, and are warned about on at most one of the two APIs; choosing the wrong
depth token produces no error, no warning and no visual difference whatever, only the loss of the
performance you thought you were buying; and one hazard is *hidden* on D3D by a `saturate` that
eats the NaN, and exposed the moment the same shader runs through GLSL. *Leaving them in eleven failure
tables* — still the right place for each hazard's context, and this document does not replace
them: it collects the shader-level rows so that a reader who opened one document does not have to
have opened the other ten.

## The derivative is a property of the quad, not of the surface

A screen-space derivative is a difference taken across the 2×2 stamp the hardware shades together.
[glsl460] §8.14.1 defines it exactly that way — forward or backward differencing over neighbouring
fragments, with `dx ≤ 1.0` under single-sample rasterization — and [d3d11spec] §16.13 says the
lanes that make that possible exist whether or not they are covered: "sometimes helper Pixel
Shader invocations need to exist to support derivatives in 2×2 stamps", and their outputs are
"valid but ignored".

Two consequences that between them explain most reported derivative bugs on terrain.

**First: the derivative is of the interpolated attribute, not of the surface.** Any quantity that
jumps *within* one quad hands the hardware a difference across the jump. On a heightfield the four
routine sources are: a `frac`-wrapped detail UV, which steps by a full tile in the one quad on each
tile boundary; a triplanar projection whose dominant axis flips mid-quad, so the two lanes are
differencing two different UV sets; a virtual texture's `physUV`, which jumps at every page
boundary because the page table is a lookup and not a function — `virtual-texturing.md` owns that
one and its fix; and any value read back from a UAV, which [d3d11spec] §16.13 forbids outright as a
derivative input ("It is invalid for any result dependent on an access to UAV memory to contribute
to a derivative calculation in a Pixel Shader"). In a GPU-driven pipeline the page table and the
chunk record are often exactly that UAV.

**Second, and the one that gets misdiagnosed: under a rasterizer, at a LOD seam the derivative is
never taken across the seam.** Quads are generated per primitive, and the sentence that says so is
[d3d11spec] §16.2: the minimum atom of shader execution is a 2×2 block, so "there may be **dummy
invocations off the edge of a primitive** to fill out the minimum 2×2 size." Two terrain chunks at
different LODs are two draws and two triangles, so they never put lanes in one quad; the far lanes
belong to *this* triangle. The seam-crossing derivative readers go hunting for does not exist.
⚠️ **That those lanes carry this triangle's own attributes extrapolated past its edge is correct
hardware behaviour cited to nothing here**: §16.2 says the invocations exist, §16.13 that their
outputs are "valid but ignored", neither states the extrapolation — and the conclusion does not
need it, because §16.2 alone closes the seam question.
⚠️ **The exception is the one path that does not rasterize the shading**: a visibility-buffer pass
shades screen tiles in compute, where a quad swizzle *does* pair neighbouring pixels from
different chunks, and there the seam-crossing derivative is real. That is precisely why
`gpu-driven-culling.md` lists "analytic derivatives for mip selection" among the reconstruction
costs of that path rather than treating it as free.

What *does* exist on the raster path is that the two sides feed **different inputs** to
their own correct derivatives — a different heightmap mip under `heightfield-lod.md`'s morph, a
per-LOD detail-UV scale, a different resident page mip — and the reader sees one filtering
discontinuity along every LOD band and blames the derivative. The fix is never to "fix the
derivative"; it is to make the LOD-dependent inputs agree across the band, or to take the
derivative from a quantity that does not depend on LOD at all. Screen-space world XZ is that
quantity for terrain, and virtual UVs are the same idea one level up [mittring2008].

## Inside a divergent march, `ddx`/`ddy` are undefined, not merely noisy

A ray march has a per-pixel iteration count. That is not a performance property; it is a language
property with a stated consequence at both ends:

- [glsl460] §8.14.1: *"Derivatives are undefined within non-uniform control flow."* One sentence,
  no qualification, no accuracy claim.
- [d3d11spec] §16.8.1 is sharper about what counts. A `loop` containing a `break`, `breakc`,
  `continue`, `continuec`, `ret` or `retc` puts its **entire contents** inside varying flow
  control — so a march that exits early on a hit, on a miss, or on a step cap is *wholly* inside
  it, including the iterations every lane still agrees on. §16.8.2 (a) then makes the derivative
  instructions and the implicit-LOD `sample` illegal there when the operand is a shader-computed
  temporary, which the ray position always is. Since D3D11.2 the compiler only warns.

So `Sample`, `SampleBias` and `CalculateLevelOfDetail` inside the loop — and GLSL's `texture()`,
whose derivative [glsl460] §7.1.5 says is *"computed implicitly"* by the very existence of helper
invocations — are forbidden on one API and undefined on the other, and they compile on both.
**What to use instead is in the same section of the
same specification**: [d3d11spec] §16.8.2 (b) lists `sample_l` as carrying no flow-control
restriction at all — *"here the application provides LOD as an operand, so no derivative
calculation is required, and there is no issue with flow control"* — and `sample_d` for the same
reason with gradients supplied. `SampleLevel` and `SampleGrad` are those two instructions.

**And after the loop, a defined derivative is still the wrong number.** Once the march has
converged the flow is uniform again and `ddx` of the hit position is perfectly legal — and
useless, because neighbouring pixels hit different terrain across a silhouette.
`heightfield-raymarching.md` states this as a rule about the pixel quad rather than about normals,
and the wording is load-bearing: *"`ddx/ddy` of anything derived from the hit position is garbage
across a silhouette, so a plain `Sample` there is the same defect wearing a mip-noise costume
instead of a normal-noise one."* It covers albedo, splat weights and detail UVs, not only the
normal. The replacement it names is `SampleGrad` with gradients built from **ray differentials** —
the neighbouring pixel's ray evaluated at this hit's distance — a quantity the marcher has and the
quad does not. Normals come from analytic central differences at a footprint-matched mip, not from
the quad at all.

These are two different failures and they need saying separately, because the second survives
fixing the first: hoisting the fetch out of the loop makes it *defined*, and it is still taken
across a silhouette.

## Explicit-LOD fetch in a max-mip traversal, and why `Sample` breaks the bound

`heightfield-raymarching.md`'s traversal block carries the rule inline — `texelAt(rayPos(t),
level)` is an *"explicit-LOD fetch: SampleLevel or Load, never Sample"* — and the flow-control
argument above is only half of why. The other half is that a max-reduce pyramid [tevs2008] §3.1 is
not a filterable quantity.

The traversal's safe-skip test asks whether the ray stays above `node.maxH` across the node's
footprint. `node.maxH` is a **bound**, and the test is sound only while the value fetched is at
least the true maximum over the texel the ray is in. Bilinear filtering returns a convex
combination of that texel's maximum and three neighbours' — non-negative weights summing to one —
so the result is at or **below** the largest of the four and, whenever the ray's own texel is the
largest, strictly below the value the test needs. **The precondition is that the sample lands off
the texel centre**, and it always does: the traversal's position is `pos.xz / s_L`, a continuous
ray parameter, which coincides with a texel centre only by accident. So a filtered fetch
under-states the bound, the skip branch fires on a node that can contain a hit, and the traversal
misses it — the same class of failure as the ascending-ray crossing test that document already
documents, arriving by a different route. It is silent, it is geometry-dependent, and it looks
like "occasional holes in the shadows".

Three practical consequences:

- **`Load` is the safest spelling**, because it takes an integer texel coordinate and a mip index,
  has no sampler, and therefore cannot filter, cannot wrap and cannot clamp behind your back. It
  also puts `heightfield-raymarching.md`'s registration convention — `texelAt` is
  `floor(pos.xz / s_L)`, *"never a rounded texel-centre lookup"* — in the shader text where a
  reviewer can see it, rather than in a sampler state object where nobody looks.
- **`SampleLevel` is fine with a point sampler and wrong with a linear one**, and the sampler is
  usually inherited from whatever else the pass binds. If you use it, assert the filter.
- **The level is chosen by the traversal, not by the footprint.** There is no footprint to choose
  from: the pyramid *is* the LOD [tevs2008] §3.2. A shader that reaches for
  `CalculateLevelOfDetail` here is answering a question the algorithm did not ask, and doing it
  inside varying flow control, where §16.8.2 (a) lists `lod` alongside `sample` as restricted
  [d3d11spec].

## Virtual-texture gradients: one scale factor, one bias, neither optional

Both numbers are `virtual-texturing.md`'s and are restated here rather than re-derived, because a
second derivation is a second chance to disagree.

**The scale.** Gradients must be taken from *virtual* UVs, or they measure the page table's jump
instead of the surface. That is only half the rule, because `SampleGrad` measures its gradients
against the texture being **sampled** — the pool, not the virtual texture. Inside a page the
virtual→physical map is linear, so the chain rule is one constant:

```
s = virtualSize / (poolSize * 2^pageMip)         // the resident page's virtual resolution
                                                 // over the pool's
SampleGrad(pool, physUV, ddx(virtualUV) * s, ddy(virtualUV) * s)
```

Dropped, the LOD error is `pageMip − log2(virtualSize/poolSize)` levels — negative on the fine
pages the near field uses, positive once `pageMip` passes `log2(virtualSize/poolSize)`, and
**exactly zero at that one page mip**, which is how a single test view passes. A 256k² virtual over
a 16k² pool gives `s = 16` at `pageMip = 0`, so unscaled gradients state a footprint 16× too small,
`log2 16 = 4` levels too fine. The anisotropic half does not clamp the way the LOD half does — the
ratio is scale-invariant, so the hardware takes the right number of taps and spreads them across
`1/s` of the footprint they should cover, at the grazing angles anisotropy exists to serve.
⚠️ [mittring2008] §2.3.2.2 bounds a tap's reach — 1 texel bilinear, 4 for DXT — but **declines
anisotropy explicitly**, so no aniso cap is sourced here and none is claimed.

**The bias.** A feedback pass renders (pageID, mip) at reduced resolution [barrett2008]. With
`feedbackScale = fullResWidth / feedbackWidth`, adjacent pixels of that buffer stand
`feedbackScale` full-res pixels apart, so its `ddx(virtualUV)` is that much larger and the mip it
computes is `log2(feedbackScale)` too coarse for what the main pass will sample. Request
`mip = computeMip(virtualUV) − log2(feedbackScale)`. ⚠️ **Derived here, not sourced:** [mittring2008] §2.3.6.4 gives [barrett2008]'s tile-id pre-pass and its read-back latency, with no reduced-resolution buffer and no bias term, so it cannot carry this. At quarter resolution
that is 2 mips, which is **6.25% of the areal texel density the main pass needs**, and over a fixed
screen area about 6.25% of the pages — the same factor twice. Left uncorrected it is not a
transient: the finest page the table can serve stays `log2(feedbackScale)` mips coarser than the
pixel wants, permanently. A deliberate coarse bias for working-set control sits *on top of* this
term, never instead of it.

## Depth output: one promise, two tokens, and a silent tax for choosing wrong

Writing depth from a pixel shader — a ray-marched hit, a POM-displaced surface — has a stated
cost: *"Enabling oDepth in a pixel shader disables early z culling"* [d3d11spec] §16.9.2. The
conservative-depth tokens buy it back by letting the shader promise a direction. §16.9.3:

| Token | The promise | Early cull survives when the depth comparison is |
|---|---|---|
| `SV_DepthGreaterEqual` | never writes a value **smaller** than the rasterized depth | `less` or `less or equal` — i.e. **standard Z** |
| `SV_DepthLessEqual` | never writes a value **larger** than the rasterized depth | `greater` or `greater or equal` — i.e. **reversed-Z** |

This corpus mandates reversed-Z: `planetary-precision.md` maps near to 1 and far to 0 and says
*"flip the comparison, clear to zero"*, on the storage evidence in [reed2015]. So **the token this
corpus's renderers want is `SV_DepthLessEqual`**, and `heightfield-raymarching.md` says exactly
that — *"`SV_DepthLessEqual` under reversed-Z — this corpus's mandate — and `SV_DepthGreaterEqual`
under standard depth, the two being opposite tokens for one promise."*

**Why the wrong one is silent.** §16.9.3.1 says using either "is valid with any depth mode, but the
early depth cull will be disabled" when the declared direction is not compatible with it. Not an
error, not a warning, not a validation-layer message, and not a pixel of visual difference: the
shader is legal, the image is correct, and the entire reason you declared conservative depth is
gone. It reads as "conservative depth didn't help on this hardware". Under reversed-Z,
`SV_DepthGreaterEqual` is the token that spells "no". Two ways to catch it, both cheap: assert the
token against the pipeline's depth comparison function at pipeline-creation time, since both are
already there; and measure the pass with and without the declaration — if the numbers match, the
token is inert.

⚠️ **Both tokens are promises the hardware believes, and breaking one is undefined behaviour**
[d3d11spec] §16.9.3. §16.9.3.2 records that implementations *may* clamp the written depth against
the rasterizer's centroid depth, and then records that most never implemented the clamp — so do
not plan on being caught. `heightfield-raymarching.md` names the precondition that makes the
promise true and it is not automatic: the proxy must be a **max-height** surface, the marcher's own
max-reduce hull, so its depth is at or nearer than the hit for every pixel it covers. A mean-height
or raster-LOD proxy sits behind the hit somewhere in every frame, and the hardware culls pixels
that should have drawn.

## Divergent resource indices: the wave-uniformity the compiler assumes

Terrain in a GPU-driven pipeline indexes descriptors by data: a material ID from a splat map, a
page or physical-slice index from a page table, a chunk record. Those indices are **per-pixel, not
per-wave**, and [nonuniform_idx] states what the compiler does about it: *"The HLSL compiler assumes
resource index expressions to be uniform, as this is the most typical usage case"*, and if the
index may be non-uniform — *"meaning varying anywhere within a draw or dispatch call — instancing
counts as varying"* — the intrinsic is mandatory, *"otherwise, the result is undefined"*.
`gpu-driven-culling.md` carries the same rule as a bindless bullet and names its symptom: the
compiler *"may assume uniformity and broadcast one lane's index to the wave — the classic bug that
renders correctly on one vendor and ships."*

```hlsl
// HLSL
float4 albedo = matTex[NonUniformResourceIndex(materialId)].SampleGrad(samp, uv, dx, dy);
```
```glsl
// GLSL + Vulkan: #extension GL_EXT_nonuniform_qualifier : require
vec4 albedo = textureGrad(matTex[nonuniformEXT(materialId)], uv, dx, dy);
```

Three details that are not in the folklore version of this rule:

- **The two spellings are one decoration, not two dialects — checked rather than assumed.**
  `nonuniformEXT` maps to the SPIR-V `NonUniformEXT` decoration on the variable, and the SPIR-V
  core grammar gives Decoration **5300** as enumerant `NonUniform` with `NonUniformEXT` as an
  *alias*, core since version 1.5 via `SPV_EXT_descriptor_indexing` [nonuniform_idx]. So
  `gpu-driven-culling.md`, which names it the SPIR-V `NonUniform` decoration, and the GLSL
  extension, which writes `NonUniformEXT`, are the same value under two names.
- **For a multi-dimensional resource array, one index is enough** — *"it is sufficient to apply
  NonUniformResourceIndex to any index"* [nonuniform_idx]. Wrapping every subscript is harmless
  and wrapping none is undefined.
- **A divergent index degrades the derivative, not only the throughput.** The same document says
  that when the index diverges across a quad "the hardware-computed derivative and derived
  quantities such as LOD may be undefined … similar to computing derivatives in divergent control
  flow". This is the third route to the same defect as the two above, and it has the same fix: an
  explicit LOD or explicit gradients, which need no per-lane derivative at all. A per-pixel
  material index and an implicit-LOD `Sample` are a bad pair even with the intrinsic in place.

## The grazing terms: two ways to write a NaN, and two languages that disagree about it

Grazing angles are where a terrain and water shader spends its subtlety, and they are also where
the arguments to `pow`, `sqrt` and `normalize` approach the edges of their domains. ⚠️ **Only the
first hazard below is harvested**: it is `water-rendering.md`'s and is quoted from it. The second
and third are the document's own, derived here against the specifications — the second is a cousin
of that document's `mediump` degenerate-divide guard by a different mechanism, and the third is not
a way to *make* a NaN at all, but the reason one API shows you the ones you made and the other does
not.

**`pow` with a negative base is undefined, and clamping one end is the trap.** [glsl460] §8.2:
*"Results are undefined if x < 0."* `water-rendering.md` measured what that costs on the
roughness-aware Fresnel fit [bruneton2010] and the finding is quoted, not re-derived: a normal
blended from a detail map and left unrenormalized makes `dot(N, V)` exceed 1 near normal incidence
— *"an additive blend on essentially every sample"*, and even a renormalised fp32 pair lands above
it, at `max dot = 1.000000238` — **two** ULP, the binary32 step above 1.0 being `2^-23` and one ULP
being `1.0000001`. (⚠️ `water-rendering.md`:125 writes "one ULP" against that same value: the value
is the measurement, the count is the slip, and that document is not this one's to edit.) So
`1 − cosThetaV` goes negative and the band around the mirror direction goes NaN.
Clamping only the top, `max(1.0 − cosThetaV, 0.0)`, removes the NaN and
leaves the other end open: a back-facing `dot(N, V) = −1` gives `1 − cos = 2`, and at
`sigma_v = 0.12` that is `m = 6.3` and **`F = 6.2`**, on **8.8%** of pixels at an 85° view.
`saturate` closes both ends. **Renormalise at the fetch as well**, or every other term still reads
the bad normal.

**`normalize` of a near-zero vector is `0/0`, and in fp16 "near zero" is much larger than you
think — and how much larger is the target's choice, not the format's.** The arithmetic is read
straight off IEEE 754 binary16, as `planetary-precision.md` reads its ULP table off binary32; but
binary16 alone does not fix the answer, and the two specifications that do give opposite ones. For
**full** float16, [d3d11spec] §3.1.5 mandates the forgiving regime — unfused operations round to
nearest even at 0.5 ULP, and *"16-bit floating point numbers must preserve denorms"*. For the
**minimum-precision** type this hazard lives in, `min16float` and GLSL ES `mediump`, §7.20.2.2.1
hands that back: *"Float16 arithmetic operations within the shader may or may not flush float16
denorm to 0, and may either round to nearest even or truncate to a representable number."*

Smallest normal `2^-14 = 6.104e-5`, smallest subnormal `2^-24 = 5.960e-8`. Rounding to nearest
even, a **square** is lost at or below `2^-25` — half the smallest subnormal, the tie going to the
even significand, zero. Truncating, once below `2^-24`. Flushing subnormal results, once below the
smallest **normal**, `2^10` sooner. Square-root each for the component bound, and the value at it:

| Regime, all three conforming under §7.20.2.2.1 | Component bound | Largest value there | As a slope | Height across a 2 m cell |
|---|---|---|---|---|
| round to nearest even, subnormals preserved — the **floor**, and all §3.1.5 permits | `\|x\| ≤ 2^-12.5` | `1.7262e-4` | `0.0099°` | `0.35 mm` |
| truncate, subnormals preserved | `\|x\| < 2^-12` | `2.4402e-4` | `0.0140°` | `0.49 mm` |
| subnormal **products** flushed to zero, under either rounding | `\|x\| < 2^-7` | `7.8087e-3` | `0.447°` | `15.6 mm` |

A vector — two components or three, no difference — all of whose components sit at or under the
threshold in force has `dot(v, v) == 0` exactly, so `normalize(v)` is `0/0`. Measured, not only
derived: an exhaustive sweep over all `31743` positive finite binary16 values under each regime
returns exactly those three as the largest giving `dot(v,v) == 0`, 2-vector and 3-vector alike.

**What is *not* the mechanism, stated narrowly because the wide version is wrong.** Every threshold
is far above the smallest normal — `2.83×` at the floor, `128×` at the top — so each **component**
is an ordinary normal number and the collapse is never an artefact of denormal *inputs*. Flushing
decides the fate of the **products**, and the squares land in the subnormal range by construction,
so a target that flushes them loses the dot `45×` earlier. ⚠️ The boundary moves with it: one step
above the floor, at `2^-12 = 2.441e-4`, three squares sum to `3·2^-24 = 1.788e-7` and the normalize
succeeds — *on a target that preserves float16 denorms*. Where they are flushed, `2^-24` **is** the
smallest subnormal, each product goes to zero alone, the sum is `0.0`, and the normalize fails here
too.

⚠️ **Three target decisions move this threshold and not one is visible in the source.** The collapse
needs each product rounded to binary16 *before* it is accumulated, which is what a
`mediump`/`min16float` dot does when the multiply-add is not fused and the accumulator is not
widened — the one direction that helps, since an FMA or an fp32 accumulator means the products
never round and there is no collapse at all. The other two make it worse: truncation by `1.41×`,
flushed subnormal products by `45×`, and `water-rendering.md` already records that flush-to-zero is
*"the default on many mobile parts"*, on exactly the `mediump` this section names. Which you get
can change between driver versions, so **size the hazard at `7.8e-3`, not `1.7e-4`** — and the
guard below is the right code in every regime, and free.

The heightfield instance is `normalize(N.xz)`, a slope aspect or flow direction taken straight from
the horizontal gradient, `N.xz ≈ (−∂h/∂x, −∂h/∂z)`. ⚠️ **No document in this corpus writes that
expression today**, so the warning is conditional, not a citation: `terrain-analysis-masks.md`
builds aspect as an *angle*, `atan2(-dzdy, -dzdx)`, and reconstructs a unit vector from it — a
different mechanism, degenerate at `atan2(0,0)`, needing a different guard, which the argument
above does not reach. Any shader taking a direction from the horizontal gradient by `normalize` is
exposed, and the table sizes the exposure: at best a slope under `0.0099°`, `0.35 mm` across a 2 m
cell, which is plains; at worst `0.447°` and `15.6 mm`, which is not plains at all but ordinary
gentle terrain, and a great deal of any heightfield. In fp32 the same collapse
needs components below `2^-75 ≈ 2.6e-23`, so there the expression fails only on an exactly-flat
cell; this is an fp16 hazard specifically.

⚠️ **The obvious guard does not work.** `normalize(v) * (dot(v,v) > 0.0)` still evaluates the
divide, and `NaN * 0` is `NaN` — the multiply cannot un-poison a value the divide already made.
The guard has to keep the divide from happening at all, and it has to name what to return instead,
because there is no correct direction to return on a flat cell:

```hlsl
float  d   = dot(v, v);                 // one dot, reused
float2 dir = (d > 0.0) ? v * rsqrt(d)   // rsqrt, not normalize: the branch owns the divide
                       : fallbackDir;   // an authored constant, NOT (0,0) -- see below
```

Returning `(0,0)` moves the NaN one step downstream into whatever consumes the direction; pick a
fallback the consumer can survive — for aspect, any fixed compass direction, since a flat cell has
no aspect and every answer is equally wrong. ⚠️ **An epsilon has to be on the right quantity.** `d`
has already collapsed to exactly `0`, so `d > 0.0` catches every regime with no epsilon at all, and
one on `d` — or on an fp16 `length(v)`, which is `sqrt(0)` — adds nothing. The epsilon that fails
is the one on the *components*, or on a magnitude taken at fp32 while the divide runs at fp16: to
catch this it must exceed the threshold in force, up to `7.8e-3`, not the `1e-6` fp32 suggests.

⚠️ **`saturate` and `clamp` do not agree about NaN across the two APIs, and the safe-looking one is
the one that hides the bug.** [d3d11spec] §22.19.1 defines `_sat` as `min(1.0f, max(0.0f, value))`
over the min and max *instructions*, and §22.10.11 and §22.10.10 define those to return the other
operand when one is NaN — so the spec states the result outright: *"sat(NaN) returns 0, by the
rules for min and max."* HLSL `clamp(x, 0, 1)` lowers to those same two instructions, and lands on
`0` or `1` depending on which order the compiler emits them — `min(max(NaN,0),1) = 0`,
`max(min(NaN,1),0) = 1` — so it is not a NaN either, and which of the two you get is not yours to
choose. [glsl460] §8.3 defines `clamp` as `min(max(x, minVal), maxVal)` and defines `min` and `max`
by a bare comparison — *"Returns y if y < x; otherwise it returns x"* — with **no NaN carve-out**:
read literally, with `x = NaN` every comparison is false, both calls return their first argument,
and the NaN survives. The consequence is a porting failure in the direction nobody expects. Author
on D3D and the NaN is eaten — the term collapses to a finite `0` or `1`, TAA history stays clean,
and nothing is reported. Ship the same shader through GLSL or SPIR-V and the NaN reaches the colour
target, where — `water-rendering.md`'s words — it *"is absorbed permanently into TAA history"*, and
one pixel poisons it. So: **a `saturate` that is load-bearing is a bug the D3D build is hiding.**
Fix the source of the NaN. And do not go the other way and lean on `min`/`max` to absorb one:
`hydraulic-erosion.md` measured that trap on the CPU/GPU boundary and its rule stands unweakened
here — *"never rely on `min` to absorb a NaN"* — because the guarantee above is D3D's shader
instruction set, not a property of the two languages, and argument order alone changes the answer
under [glsl460] §8.3.

## How this fails, and what it looks like

| Symptom | Mechanism | Fix |
|---|---|---|
| Mip noise or blocky texture LOD only where the march is expensive, and it moves with the camera | `Sample` inside a loop with a per-pixel iteration count. [glsl460] §8.14.1 makes the derivative undefined; [d3d11spec] §16.8.1 puts the *whole* loop body inside varying flow control the moment it can `break` | `SampleLevel`, or `SampleGrad` with ray-differential gradients — §16.8.2 (b) lists both as unrestricted |
| Normals, albedo or splat weights dissolve into noise at silhouettes, with a defined derivative and no warning | The flow is uniform again after the loop, so `ddx` is legal — and still a difference across pixels that hit different terrain | Ray differentials into `SampleGrad`; analytic central differences at a footprint-matched mip for the normal (`heightfield-raymarching.md`) |
| Shadow or occlusion rays leak through terrain that the primary march draws correctly | The traversal filtered a max-reduce texel: a bilinear tap is a convex combination and lands at or **below** the true bound, so the skip test passes on a node holding the hit | `Load`, or `SampleLevel` with an asserted point sampler [tevs2008] |
| A one-pixel dark or blurred line along every detail-texture tile repeat | `frac`-wrapped UV steps a full tile inside the one straddling quad, so the derivative is of the wrap | Take the derivative from the unwrapped UV, or fetch with explicit gradients |
| A filtering discontinuity along every LOD band, and "fixing the derivative" changes nothing | No quad spans two chunks — the far lanes are helper invocations from this triangle. The two sides fed *different inputs* to their own correct derivatives: heightmap mip, detail-UV scale or resident page mip | Make the LOD-dependent inputs agree across the band, or derive gradients from a LOD-independent quantity (world XZ, virtual UVs) |
| Derivatives go wrong only after a pass starts reading a GPU-written page table or chunk record | A UAV read feeding a derivative — invalid by [d3d11spec] §16.13, enforced by the compiler only "to the extent possible" | Copy to an SRV, or move to explicit LOD |
| Correct on one vendor, garbage material or page on another, in the same frame | A per-pixel material or page index left unwrapped; the compiler assumes uniformity and may broadcast one lane's index [nonuniform_idx] | `NonUniformResourceIndex` / `nonuniformEXT`; one index suffices on a multi-dimensional array |
| Aliasing on near pages, over-blur on far ones, and one distance where it looks right | Virtual-UV gradients handed to `SampleGrad` unscaled — an error of `pageMip − log2(virtualSize/poolSize)` levels that passes through zero at one page mip | Scale both gradients by `s = virtualSize/(poolSize·2^pageMip)`; test a view holding several page mips at once (`virtual-texturing.md`) |
| Permanent blur with a quiet IO queue and long eviction ages | The feedback pass's own downscale was not subtracted, so requests are `log2(feedbackScale)` mips too coarse — 6.25% of the areal density at quarter res | `mip = computeMip(virtualUV) − log2(feedbackScale)` [mittring2008] |
| Conservative depth declared, image correct, and the pass costs exactly what it did before | The token is the wrong one for the depth convention. §16.9.3.1: valid with any depth mode, "but the early depth cull will be disabled" — no error, no warning, no visual change | `SV_DepthLessEqual` under reversed-Z, `SV_DepthGreaterEqual` under standard Z; assert the token against the pipeline's comparison function |
| Pixels missing from a depth-writing march, worst where the proxy is coarse | The conservative-depth promise was broken; §16.9.3.2's clamp is optional and mostly absent | The proxy must be a **max-height** hull (`heightfield-raymarching.md`), not a mean-height or raster-LOD one |
| A NaN band around the mirror direction on water, permanent in TAA history | `pow` with a negative base — undefined per [glsl460] §8.2 — from `1 − dot(N, V)` on an unrenormalized blended normal | `saturate` **both** ends, and renormalise at the fetch; the one-sided `max(·, 0)` leaves `F = 6.2` on back-facing normals (`water-rendering.md`) |
| Aspect, flow direction or triplanar weights speckle with NaN on flat ground — in `mediump`, on some targets and not others | `normalize(N.xz)` where both components sit under the threshold: their **squares** vanish in binary16, so `dot(v,v) == 0` and the divide is `0/0`. The threshold is the target's, not the format's — [d3d11spec] §7.20.2.2.1 permits three regimes for min-precision float16 and they span `45×`: `1.726e-4` rounding to nearest even with subnormals preserved, `2.440e-4` truncating, `7.809e-3` where subnormal products are flushed. The components are normal numbers in all three, so denormal *inputs* are not the cause; the *products* are. An FMA or an fp32 accumulator suppresses it entirely, which is why it is target-dependent | Branch **around** the divide — `d = dot(v,v); (d > 0) ? v*rsqrt(d) : fallbackDir` — with a named fallback. `normalize(v) * (dot(v,v) > 0)` does not work: `NaN * 0` is `NaN`. Size it at `7.8e-3`, not `1.7e-4`; an epsilon on `d` adds nothing and one on the components must beat that same number; `highp` moves the threshold to `2^-75` |
| A shader that is clean on D3D and speckles on Vulkan, or the reverse | `saturate`/`clamp` NaN semantics: [d3d11spec] §22.19.1 states `sat(NaN) = 0`, [glsl460] §8.3 defines `clamp` over comparisons with no NaN carve-out and propagates it | Fix the NaN at its source; treat a load-bearing `saturate` as a bug the D3D build is hiding, and never rely on `min` to absorb one (`hydraulic-erosion.md`) |
