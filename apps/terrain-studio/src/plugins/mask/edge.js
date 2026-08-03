// Edge — extract the boundary of a mask (S8.1).
//
// Given a scalar mask, emit the ring of cells that sit ON the threshold boundary: a cell is a
// boundary cell when it is above the threshold and at least one legal neighbour is not. "Legal
// neighbour" is the lattice's own neighbourhood — 4 on square, 6 on hex — which is the whole
// reason this cannot be a fixed 3x3 stencil.
//
// The neighbourhood contract is fixed and stated rather than left to the implementation, because a
// boundary that silently used 8-neighbourhood on square would be one cell thick diagonally and two
// cells thick orthogonally, and nobody would notice until a downstream distance field was wrong.
//
// A constant field has no boundary and must come back empty. That is the story's negative control,
// and it is a real one: a naive gradient-magnitude implementation returns zero everywhere for a
// constant field too, so the discriminating case is the analytic disc, where the ring must be
// exactly one legal-neighbour ring at the declared threshold.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, isHex, hexNb } from '../../legacy.js'

export function edgeField(src, threshold) {
  const w = fieldW(), h = fieldH(), out = newField()
  const hex = isHex()
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x
      if (!(src[i] > threshold)) continue          // only cells INSIDE the mask can be its boundary
      let onBoundary = false
      if (hex) {
        // Odd-r offset: the six neighbour offsets depend on ROW PARITY, which is why hexNb takes
        // the row and returns six [dx,dy] pairs rather than a fixed stencil.
        const nb = hexNb(y)
        for (let k = 0; k < 6; k++) {
          const nx = x + nb[k][0], ny = y + nb[k][1]
          // Outside the domain counts as outside the mask: the rim of the world is a boundary.
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) { onBoundary = true; break }
          if (!(src[ny * w + nx] > threshold)) { onBoundary = true; break }
        }
      } else {
        // 4-neighbourhood on square, deliberately. See the header note on 8 vs 4.
        if (x === 0 || y === 0 || x === w - 1 || y === h - 1) onBoundary = true
        else if (!(src[i - 1] > threshold) || !(src[i + 1] > threshold)
          || !(src[i - w] > threshold) || !(src[i + w] > threshold)) onBoundary = true
      }
      if (onBoundary) out[i] = 1
    }
  }
  return out
}

export default definePlugin({
  type: 'edge',
  cat: 'mask',
  name: 'Edge',
  ins: ['Mask'],
  desc: 'The boundary ring of a mask: cells above the threshold with at least one legal neighbour below it.',
  params: [P.slider('threshold', 'Threshold', 0, 1, 0.5, 0.01)],
  inputs: [
    { id: 'mask', name: 'Mask', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'anyMask', unit: 'none', role: 'mask', required: true },
  ],
  outputs: [
    { id: 'out', name: 'Boundary', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', primary: true, lens: 'derived' },
  ],
  eval: (p, ins) => (ins[0] ? edgeField(ins[0], p.threshold) : newField()),
})
