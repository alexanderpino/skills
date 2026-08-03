// Normals — the first genuinely multi-output, vector-raster node (S2.6).
//
// Sprint 1 deliberately deferred this. S1.5 shipped Aspect, which is a SCALAR (the compass
// direction of steepest descent), and said in as many words that "Normals require a vector-raster
// port and move to Sprint 2; do not smuggle them through node-instance side state". This is that
// port arriving.
//
// It is the pilot for three things the typed runtime claimed but nothing production exercised:
//   * a vectorRaster output — three interleaved components per sample, RGB32F;
//   * more than one output port on a real node, not a test probe;
//   * demand-driven allocation — the normal field costs 3N floats and is not computed at all when
//     nothing downstream asks for it.
//
// WHY THERE IS A HEIGHT PASSTHROUGH. `_field` aliases the primary SCALAR raster (ADR-002), and the
// thumbnail, the preview and collectScene all read it. A node whose only output were a vector would
// have no `_field` and would render as nothing. So the primary is the input passed through
// unchanged — the same shape S5.3's Snow uses — and the vector rides its own port.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, fieldLen, cellSizeM, terrainDef, isHex, HEX_ROW } from '../../legacy.js'

/**
 * Central-difference surface normal in WORLD space, returned interleaved xyz.
 *
 * The world spacing is what makes this a normal rather than a picture of one: dz/dx uses the real
 * metre spacing between posts, and on a hex lattice the row pitch is sqrt(3)/2 of the column
 * spacing, so using the raw index step would tilt every normal on hex by a constant factor. Height
 * is denormalised through terrainDef.height because the field is heightNormalized (ADR-005).
 */
export function normalField(src, strength) {
  const w = fieldW(), h = fieldH(), out = new Float32Array(fieldLen() * 3)
  const sx = cellSizeM(), sy = cellSizeM() * (isHex() ? HEX_ROW : 1)
  const vScale = (terrainDef.height || 1) * (strength || 1)
  for (let y = 0; y < h; y++) {
    const yUp = y > 0 ? y - 1 : y, yDn = y < h - 1 ? y + 1 : y
    const dyM = (yDn - yUp) * sy
    for (let x = 0; x < w; x++) {
      const xL = x > 0 ? x - 1 : x, xR = x < w - 1 ? x + 1 : x
      const dxM = (xR - xL) * sx
      // One-sided at the border rather than wrapping: the domain edge has no neighbour, and
      // wrapping would invent a slope across the seam.
      const dzdx = dxM ? (src[y * w + xR] - src[y * w + xL]) * vScale / dxM : 0
      const dzdy = dyM ? (src[yDn * w + x] - src[yUp * w + x]) * vScale / dyM : 0
      let nx = -dzdx, ny = -dzdy, nz = 1
      const len = Math.hypot(nx, ny, nz) || 1
      const i = (y * w + x) * 3
      out[i] = nx / len; out[i + 1] = ny / len; out[i + 2] = nz / len
    }
  }
  return out
}

export default definePlugin({
  type: 'normals',
  cat: 'data',
  name: 'Normals',
  ins: ['In'],
  desc: 'Surface normals as a true 3-component vector field, recomputed from final geometry. Height passes through unchanged.',
  params: [P.slider('strength', 'Strength', 0.1, 4, 1, 0.05)],

  // Declared ports — this plugin does NOT use the legacy adapter (ADR-002 forbids it for new nodes).
  inputs: [
    { id: 'in', name: 'In', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'anyScalarRaster', unit: 'none', role: 'data', required: true },
  ],
  outputs: [
    { id: 'height', name: 'Height', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'relativeHeight', unit: 'none', primary: true, lens: 'derived' },
    { id: 'normal', name: 'Normal', kind: 'vectorRaster', storage: 'RGB32F', components: 3,
      semantic: 'normal', unit: 'none', lens: 'derived' },
  ],

  eval: (p, ins, node, ctx) => {
    const src = ins[0]
    const height = src || newField()
    const values = new Map([['height', height]])
    // Demand-driven: 3N floats is three times the field, and a Normals node parked in a graph with
    // nothing wired to its vector port should cost nothing. An absent ctx means "compute it" so a
    // direct eval (the digest oracle, an ad-hoc probe) still sees the full result.
    const demanded = ctx && ctx.demanded
    if (src && (!demanded || demanded.has('normal'))) values.set('normal', normalField(src, p.strength))
    return { values }
  },
})
