// water_regimes — S4.9, the Water Regimes node.
//
// NOT YET REGISTERED. `src/plugins/data/index.js` is owned by another process; the one line it needs
// is written out in the story report. Everything here validates against today's `src/core/ports.js`
// vocabulary — the oracle runs `validatePortList` over these descriptors — so the file is ready to
// register without a ports change.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run until
// the graph is evaluated, so the legacy<->plugin cycle is safe.
//
// WHY FIVE MASKS AND NOT ONE LABEL RASTER. A regime code is categorical and `labelRaster` is exactly
// the port kind for that, but the only label semantic in the vocabulary today is `basinId`, and a
// regime is not a basin. Emitting the classification through five `mask` ports is honest with the
// vocabulary that exists, and it is what a shader wants anyway. The report asks for a `waterRegime`
// label semantic so a later version can publish the code itself.
//
// THIS NODE NEVER WRITES HEIGHT. Guardrail 1. It has no height port, it never returns one, and the
// primary output is the water DEPTH it was handed, by identity. The oracle asserts both.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH } from '../../legacy.js'
import {
  regimeMasks, REGIME_NAMES, MANNING_N_DEFAULT, CHANNEL_FORMING_Q_M3S,
  SHORE_DEPTH_DEFAULT_M,
} from '../../core/water-regimes.js'

export default definePlugin({
  type: 'water_regimes',
  cat: 'data',
  name: 'Water Regimes',
  ins: ['Depth', 'Discharge', 'Temperature', 'Slope', 'Direction'],
  desc: 'Classify every wet sample as ice, rapid, river, shore or lake from depth, discharge, temperature and gradient. Emits one mask per regime, a causal foam field and the depth-averaged flow velocity. Never modifies terrain.',
  params: [
    // Chow (1959) "natural stream, clean and winding": n = 0.033 to 0.040. The one number a user
    // reaches for when their rivers run too fast.
    P.slider('manningN', "Manning's n", 0.010, 0.100, MANNING_N_DEFAULT, 0.001),
    // Below this discharge there is no persistent channel at terrain resolution, only sheet flow.
    // Log-scaled: the defensible range spans decades.
    P.log('channelQ', 'Channel-forming Q (m3/s)', 1e-4, 100, CHANNEL_FORMING_Q_M3S),
    // The depth at which the bottom starts to be felt — the same deep-water reference the shoaling
    // law uses, so the shore band and the shoaling band are one definition.
    P.slider('shoreDepth', 'Shore depth (m)', 0.5, 80, SHORE_DEPTH_DEFAULT_M, 0.5),
    // Standing water is whatever the author says it is. 'lake' is the default because defaulting to
    // open ocean would put a 500 km fetch on every pond.
    P.select('standing', 'Standing water', ['lake', 'ocean'], 'lake'),
    // The ambient sea the standing water carries, in metres. Rivers receive exactly zero of it by
    // construction — their fetch is zero — which is the story's "no ocean waves on rivers".
    P.slider('swellM', 'Swell amplitude (m)', 0, 6, 1.5, 0.05),
    P.slider('chopM', 'Chop amplitude (m)', 0, 2, 0.35, 0.01),
  ],

  inputs: [
    // Metres of water column, zero on dry land — from Lake or Rivers. The classification is over WET
    // samples, so this is the input that decides which samples exist at all.
    { id: 'waterDepth', name: 'Depth', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'waterDepth', unit: 'm', role: 'data', required: true },
    { id: 'discharge', name: 'Discharge', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'discharge', unit: 'm3PerS', role: 'data', required: false },
    { id: 'temperature', name: 'Temperature', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'temperature', unit: 'degC', role: 'data', required: false },
    // The water-surface gradient that drives Manning's equation. Dimensionless rise over run.
    { id: 'slope', name: 'Slope', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'slope', unit: 'none', role: 'data', required: false },
    // Horizontal unit vector from Physical Flow. Direction only — the SPEED is computed here from
    // depth and gradient, because a unit direction's length is 1 everywhere there is any flow at
    // all, including on a dead-flat lake.
    { id: 'flowDirection', name: 'Direction', kind: 'vectorRaster', storage: 'RGB32F', components: 3,
      semantic: 'flowDirection', unit: 'none', role: 'data', required: false },
  ],
  outputs: [
    // Primary is the UNTOUCHED input depth. Anything downstream that just wants the water column
    // gets it by default and has to ask explicitly for a regime.
    { id: 'waterDepth', name: 'Depth', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'waterDepth', unit: 'm', primary: true, lens: 'continued' },
    // Causal foam: the maximum of supercritical flow, breaking surf and crest folding, damped by ice.
    // Not a noise field — the oracle arms a noise mutation against exactly that.
    { id: 'foam', name: 'Foam', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', lens: 'derived' },
    // The partition, one indicator per regime. Mutually exclusive and exhaustive over wet samples:
    // they sum to exactly 1 where there is water and exactly 0 where there is not.
    { id: 'ice', name: 'Ice', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', lens: 'derived' },
    { id: 'rapids', name: 'Rapids', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', lens: 'derived' },
    { id: 'river', name: 'River', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', lens: 'derived' },
    { id: 'shore', name: 'Shore', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', lens: 'derived' },
    { id: 'lake', name: 'Lake', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'mask', unit: 'none', lens: 'derived' },
    // Depth-averaged flow velocity in m/s, carried as a horizontal 3-vector with y zero — the same
    // packing `flowDirection` uses, so no consumer mistakes it for a 3-D velocity.
    { id: 'velocity', name: 'Velocity', kind: 'vectorRaster', storage: 'RGB32F', components: 3,
      semantic: 'velocity', unit: 'mPerS', lens: 'derived' },
  ],

  eval: (p, ins, node, ctx) => {
    const depth = ins[0]
    // The input array by identity, not a copy. A copy would satisfy a bitwise comparison just as
    // well and would hide an accidental write behind an extra allocation per evaluation.
    const src = depth || newField()
    const values = new Map([['waterDepth', src]])
    if (!depth) return { values }

    const w = fieldW(), h = fieldH(), N = w * h
    const demanded = ctx && ctx.demanded
    const want = k => !demanded || demanded.has(k)
    const wanted = ['foam', 'velocity', ...REGIME_NAMES, 'rapids'].some(want)
    if (!wanted) return { values }

    const opts = {
      manningN: Number(p.manningN) || MANNING_N_DEFAULT,
      channelFormingQM3S: Number(p.channelQ) || 0,
      shoreDepthM: Number(p.shoreDepth) || SHORE_DEPTH_DEFAULT_M,
      refM: Number(p.shoreDepth) || SHORE_DEPTH_DEFAULT_M,
      standingKind: p.standing === 'ocean' ? 'ocean' : 'lake',
      ampM: Number(p.swellM) || 0,
      chopAmpM: Number(p.chopM) || 0,
    }
    const masks = regimeMasks({
      depthM: src,
      dischargeM3S: ins[1] || 0,
      temperatureC: ins[2] || 20,
      slope: ins[3] || 0,
    }, N, opts)
    const cls = masks.classified

    // 'foam' the REGIME mask is published as 'rapids' so it cannot be confused with 'foam' the
    // intensity. Two ports called foam, one categorical and one continuous, is a wiring trap.
    const portFor = { ice: 'ice', foam: 'rapids', river: 'river', shore: 'shore', lake: 'lake' }
    for (const name of REGIME_NAMES) {
      const port = portFor[name]
      if (!want(port)) continue
      const out = newField()
      for (let i = 0; i < N; i++) out[i] = masks[name][i]
      values.set(port, out)
    }
    if (want('foam')) {
      const out = newField()
      for (let i = 0; i < N; i++) out[i] = cls.foam[i]
      values.set('foam', out)
    }
    if (want('velocity')) {
      // Direction from the wired flow field, magnitude from Manning. With nothing wired the vector
      // is zero everywhere rather than an invented direction — an unrouted graph has no velocity.
      const dir = ins[4]
      const vel = new Float32Array(N * 3)
      if (dir) {
        for (let i = 0; i < N; i++) {
          const s = cls.speed[i]
          if (s === 0) continue
          vel[i * 3] = dir[i * 3] * s
          vel[i * 3 + 2] = dir[i * 3 + 2] * s
        }
      }
      values.set('velocity', vel)
    }
    return { values }
  },

  note: '<b>Water Regimes</b> answers the question nothing upstream asks: <i>what is this wet sample?</i> Every sample with water on it lands in exactly one of five regimes, and the five masks sum to 1 wherever there is water and 0 wherever there is not — so a shallow, fast, cold cell can never be shaded as shore <i>and</i> river <i>and</i> ice at once.<br><br>The criteria are physical, not look-up. <b>Ice</b> is the completed phase transition, smooth from 0&nbsp;&deg;C to &minus;4&nbsp;&deg;C and exactly 1 below it. <b>Rapids</b> is supercritical flow: the Froude number <code>v/&radic;(gd)</code> crossing 1 is the definition of whitewater, and <code>v</code> comes from Manning&rsquo;s equation on the wired depth and gradient. <b>River</b> is discharge at or above the channel-forming value. <b>Shore</b> is water shallow enough to feel the bottom; <b>Lake</b> is everything deeper.<br><br><b>Foam</b> has three named causes and takes the largest: supercritical flow, breaking surf, and Gerstner crest folding. It is never noise. Still water carries exactly zero foam, and ice damps foam by the same factor it damps displacement, so a frozen rapid is exactly as still as a frozen lake.<br><br>Rivers and rapids receive <b>no ambient swell at all</b>: their fetch is zero, so the fetch-limited amplitude law returns exact zero rather than something small. A lake at 2&nbsp;km fetch carries <code>&radic;(2000/500000) = 0.063</code> of an open-ocean sea, which is why lakes chop and do not swell.<br><br>This node <b>does not modify height</b> and has no height port. <b>Depth</b> comes back bitwise as it arrived.',
})
