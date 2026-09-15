# virtual-texturing — declared out of the lighter pass, and why

No `measure.mjs` here. This is a declared boundary, not an oversight.

`virtual-texturing.md`'s central numeric claims (page/pool/virtual-texture sizes, bytes per
texel, feedback-buffer scale) are exact integer and rational arithmetic over fixed constants
the page already states — `rigs/approx/virtual-texturing.py` covers this exhaustively, and
none of it depends on runtime input or GPU execution: there is nothing a shader can tell you
about `128 * 128 * 1` that Python does not already say exactly.

The page has exactly one claim that is genuinely GPU-relevant: `SampleGrad`'s gradient-scaling
correction (`:105-111`) — scale both gradients by `s = virtualSize/(poolSize x 2^pageMip)`
before the sample, because unscaled gradients read the pool's footprint against its own size
and land `pageMip - log2(virtualSize/poolSize)` LOD levels off. Testing the underlying `log2`
arithmetic in a shader adds negligible confidence over confirming it in Python -- it is not
GPU-specific arithmetic. Testing the claim *for real* means probing an actual driver's implicit
LOD selection: building a mip-tagged texture (each level a distinguishable constant), sampling
it with `textureGrad` at controlled gradient magnitudes, and reading back which level the
driver's own LOD heuristic selected -- meaningfully more engineering than the other three
documents in this pass (`caustics/`, `water-rendering/`, `gpu-driven-culling/`), none of which
needed a real mipmapped texture or a driver's own filtering heuristic.

Declared, not built, per the lighter-pass scope agreed for this round. If a deeper pass is
ever justified for a specific document, this is the one with the clearest, most concrete next
step: a `textureGrad` probe against a mip-tagged texture.
