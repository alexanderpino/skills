// flow_physical — S4.2, physical flow as typed products.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run until
// the graph is evaluated, so the legacy<->plugin cycle is safe.
//
// WHY THIS EXISTS ALONGSIDE `d_flow`. The `d_flow` node returns normalize(log1p(accumulation)) — a
// picture. It is the right thing for seeing where rivers go and useless for anything needing a
// quantity: you cannot ask it how many square metres drain to a point, or how many cubic metres per
// second pass through one. The plan is explicit that `d_flow` stays as the log-compressed
// visualisation and must not be relabelled as physical, so this is a separate node with real units.
//
// THIS NODE NEVER INVENTS RAIN. Discharge comes from a typed precipitation input, or — when nothing
// is wired — from an explicit uniform parameter the author can see. Generating rainfall internally
// would make the node's output depend on a number nobody chose and nobody can inspect, and would
// collide with S5's Orographic Moisture, which is the production spatial source.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, cellSizeM, isHex } from '../../legacy.js'
import { mfdWeights, mfdAccumulate, cellAreaM2, precipToSupply } from '../../core/hydrology.js'

export default definePlugin({
  type: 'flow_physical',
  cat: 'data',
  name: 'Physical Flow',
  ins: ['Surface', 'Precip'],
  desc: 'Flow direction, drainage area in m² and discharge in m³/s, routed with multiple-flow-direction weights. Physical quantities, not a normalized picture.',
  params: [
    // The fallback when no precipitation raster is wired. Visible and authored rather than implicit:
    // a discharge that came from a hidden constant is a number nobody can defend.
    P.slider('precipMmYr', 'Uniform precip (mm/yr)', 0, 4000, 1000, 10),
  ],

  inputs: [
    // Wire this from a Depression Policy node's routing surface. Routing over raw terrain means every
    // closed hollow terminates flow, which is why S4.1 exists and why this port accepts either.
    { id: 'surface', name: 'Surface', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'relativeHeight', unit: 'none', role: 'data', required: true },
    { id: 'precipitation', name: 'Precip', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'precipitation', unit: 'mmPerYr', role: 'data', required: false },
  ],
  outputs: [
    { id: 'drainageArea', name: 'Area', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'drainageArea', unit: 'm2', primary: true, lens: 'derived' },
    { id: 'discharge', name: 'Discharge', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'discharge', unit: 'm3PerS', lens: 'derived' },
    { id: 'flowDirection', name: 'Direction', kind: 'vectorRaster', storage: 'RGB32F', components: 3,
      semantic: 'flowDirection', unit: 'none', lens: 'derived' },
  ],

  eval: (p, ins, node, ctx) => {
    const src = ins[0]
    if (!src) return { values: new Map([['drainageArea', newField()]]) }
    const w = fieldW(), h = fieldH(), N = w * h
    const hex = isHex()
    const cs = cellSizeM()
    const area = cellAreaM2(cs, hex)
    const weights = mfdWeights(src, w, h, { hex, cellSizeM: cs })

    const values = new Map()
    const demanded = ctx && ctx.demanded
    const want = k => !demanded || demanded.has(k)

    if (want('drainageArea')) {
      // Each cell contributes its own area; accumulation carries it downslope. Units are m², so the
      // number a user reads off a river mouth is a catchment they can check against the domain.
      const acc = mfdAccumulate(src, new Float64Array(N).fill(area), w, h, weights)
      const out = newField()
      for (let i = 0; i < N; i++) out[i] = acc[i]
      values.set('drainageArea', out)
    }

    if (want('discharge')) {
      // A wired raster wins over the parameter. Nothing wired and a zero parameter must give exactly
      // zero, not a small number: the oracle asserts that, because "almost no rain" and "no rain"
      // are different claims and only one of them is checkable.
      const precip = ins[1]
      const supply = precip
        ? precipToSupply(precip, area, N)
        : precipToSupply(Number(p.precipMmYr) || 0, area, N)
      const q = mfdAccumulate(src, supply, w, h, weights)
      const out = newField()
      for (let i = 0; i < N; i++) out[i] = q[i]
      values.set('discharge', out)
    }

    if (want('flowDirection')) {
      // Packed as a 3-component vector raster with y left at zero: flow direction is horizontal by
      // construction, and carrying a slope component here would invite a consumer to treat it as a
      // 3-D velocity, which it is not.
      const dir = new Float32Array(N * 3)
      for (let i = 0; i < N; i++) { dir[i * 3] = weights.dirX[i]; dir[i * 3 + 2] = weights.dirZ[i] }
      values.set('flowDirection', dir)
    }

    return { values }
  },
})
