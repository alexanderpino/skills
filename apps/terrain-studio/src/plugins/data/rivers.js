// rivers — S4.5, the Rivers node. Channel geometry as FIELDS; the ground is never moved.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run until
// the graph is evaluated, so the legacy<->plugin cycle is safe.
//
// WHY THIS NODE DOES NOT CARVE. Every shipping river node this project has looked at downcuts: it
// reads a flow field and subtracts a trench from the height, so the river is a hole in the terrain.
// Once that is baked in, changing the climate, the resolution or the discharge means re-carving, and
// the terrain before the river existed is gone. This node instead emits what the water IS — how wide
// the channel is, how deep the water in it is, how much of a cell it covers, where its free surface
// sits — and hands the bed back exactly as it arrived. The primary output is the same array object
// that came in, and `_verify_rivers.js` asserts it bitwise with a carve armed as the mutation.
//
// The physics lives in core/rivers.js so it can be checked under plain node. This file is wiring.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, cellSizeM } from '../../legacy.js'
import {
  riverFields, RIVER_PORTS, CHANNEL_HEAD_Q_M3PERS,
  DEFAULT_WIDTH_COEFFICIENT, DEFAULT_DEPTH_COEFFICIENT,
} from '../../core/rivers.js'

export default definePlugin({
  type: 'rivers',
  cat: 'data',
  name: 'Rivers',
  ins: ['Solid top', 'Discharge'],
  desc: 'Channel width, water depth, water surface and a sub-cell channel mask, all scaled on discharge by Leopold-Maddock hydraulic geometry. Emits fields about the water; never modifies the terrain.',
  params: [
    // Authored SI coefficients, in m/(m3/s)^0.5 and m/(m3/s)^0.4. Defaults are the midcontinent
    // bankfull values; they are not tuned after production output is seen.
    P.slider('kw', 'Width coefficient kw', 0.5, 12, DEFAULT_WIDTH_COEFFICIENT, 0.05),
    P.slider('kd', 'Depth coefficient kd', 0.05, 1.5, DEFAULT_DEPTH_COEFFICIENT, 0.01),
    // The relations take the channel-forming (bankfull) flood, not the mean annual flow. 1 means
    // "what is wired is already channel-forming"; raise it when the wired discharge is a mean.
    P.slider('bankfull', 'Bankfull / wired discharge', 1, 8, 1, 0.1),
    // Channel initiation is a threshold, not a fade. Log-scaled because the defensible range spans
    // two decades of support area (Montgomery & Dietrich, 1e3-1e5 m2).
    P.log('channelHeadQ', 'Channel head Q (m3/s)', 1e-6, 10, CHANNEL_HEAD_Q_M3PERS),
  ],

  // Copied, not aliased: the registry hangs `ports` metadata off the descriptors it is handed, and
  // two nodes sharing one descriptor array would share whatever gets written to it later.
  inputs: RIVER_PORTS.inputs.slice(),
  outputs: RIVER_PORTS.outputs.slice(),

  eval: (p, ins, node, ctx) => {
    const bed = ins[0]
    const discharge = ins[1]
    // The bed passes through whatever else happens, including when nothing is wired: a node that
    // dropped its terrain because an optional-looking input was missing would be a silent carve of
    // the worst kind.
    const solid = bed || newField()
    const values = new Map([['solidTop', solid]])
    if (!bed || !discharge) return { values }

    // Demand-driven: the geometry is one pass over the field, cheap, but a Rivers node parked in a
    // graph with only its bed port wired should still cost nothing beyond the pass-through.
    const demanded = ctx && ctx.demanded
    const wanted = !demanded
      || ['channelMask', 'channelWidth', 'waterDepth', 'waterSurface'].some(k => demanded.has(k))
    if (!wanted) return { values }

    const r = riverFields(solid, discharge, fieldW(), fieldH(), {
      widthCoefficient: Number(p.kw) || DEFAULT_WIDTH_COEFFICIENT,
      depthCoefficient: Number(p.kd) || DEFAULT_DEPTH_COEFFICIENT,
      bankfullFactor: Number(p.bankfull) || 1,
      channelHeadQM3PerS: Number(p.channelHeadQ) || 0,
      cellSizeM: cellSizeM(),
    })
    values.set('channelMask', r.channelMask)
    values.set('channelWidth', r.channelWidth)
    values.set('waterDepth', r.waterDepth)
    values.set('waterSurface', r.waterSurface)
    return { values }
  },

  note: '<b>Rivers</b> turns discharge into channel geometry without touching the terrain. <b>Width</b> and <b>Water depth</b> follow Leopold &amp; Maddock 1953 downstream hydraulic geometry — <code>w = kw&middot;Q<sup>0.5</sup></code> and <code>d = kd&middot;Q<sup>0.4</sup></code> — with <code>kw</code> and <code>kd</code> authored in SI units. These are the <i>downstream</i> exponents (how a river grows along its length), not the at-a-station ones (how one cross-section responds to a flood, where width goes as Q<sup>0.26</sup>); using the latter under-widens every large river.<br><br><b>Channel</b> is sub-cell coverage: the fraction of a cell the channel occupies, <code>min(1, width / cell size)</code>. On a coarse lattice a real creek covers a few percent of its cell, and a mask that stamped it as solid would make every river one cell wide whatever its discharge. <b>Channel head Q</b> is the channel-initiation threshold — below it, flow is unchannelised hillslope sheetwash and all four outputs are exactly zero. Its default is the flow that 10,000 m&sup2; of ground yields under 1000 mm/yr, the middle of Montgomery &amp; Dietrich\'s observed support-area range.<br><br><b>Bankfull / wired discharge</b> converts a mean annual flow into the channel-forming flood that actually sets a channel\'s size. It defaults to 1 — "what is wired is already channel-forming" — because no measured bankfull/mean ratio is on record here and a guessed one would silently resize every river.<br><br>This node <b>does not modify height</b>. <b>Solid top</b> is the bed exactly as it arrived, bitwise; <b>Water surface</b> is <code>bed + water depth</code>, so the water is added on top rather than dug out of the ground. If you want the channel incised, that is an explicit conditioning process wired downstream — a decision you can see and undo, not a side effect of asking how wide the river is.',
})
