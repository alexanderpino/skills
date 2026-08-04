// water_conflict — S4.6, the Guide Conflict node.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run until
// the graph is evaluated, so the legacy<->plugin cycle is safe.
//
// WHAT THIS NODE IS FOR. An author draws a river guide. The terrain underneath it may not agree —
// the line may climb, or run backwards up its own drainage. This node measures that disagreement
// and hands back where it is and how deep it goes. It is the only node in the water family whose
// output is an ARGUMENT rather than a field to render.
//
// IT HAS NO HEIGHT OUTPUT, AND THAT IS THE POINT. `BACKLOG D5`: conflicts are surfaced, not
// corrected. A node that could both detect a problem and write terrain would eventually be asked to
// do both in one step, and the author would stop being told. The repair is described — see
// `proposeConditioningBranch` in the core module — and creating it is the caller's explicit,
// undoable act. The only node in this app permitted to write terrain for drainage reasons remains
// `hydrofix`, and the proposal says so in as many words when that is the branch offered.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, cellSizeM, isHex, terrainDef, HEX_ROW } from '../../legacy.js'
import { analyzeGuideConflict, proposeConditioningBranch, flowFromVectorRaster, CONDITIONING_BRANCHES } from '../../core/water-conflict.js'

/**
 * Read guides out of the featureSet port, falling back to the authored text block.
 *
 * The record shape is `{ id, points: [{x, z}, ...] }` in world metres — the shape S4.3's guide
 * feature set has to produce. S4.3 has not landed, so this reads any record carrying `points` and
 * ignores the rest rather than assuming a schema that does not exist yet. A record with fewer than
 * two points is not a short guide, it is not a guide, and it is dropped rather than padded.
 */
function collectGuides(featureSet, text) {
  const out = []
  const records = Array.isArray(featureSet) ? featureSet : (featureSet && Array.isArray(featureSet.features) ? featureSet.features : null)
  if (records) {
    for (const r of records) {
      const pts = r && Array.isArray(r.points) ? r.points : null
      if (!pts || pts.length < 2) continue
      out.push({ id: (r && r.id) || `guide${out.length}`, points: pts })
    }
  }
  if (out.length) return out
  // The text fallback exists so this node is usable before S4.3's editable splines exist, and so a
  // gate can drive it without a document. One `x,z` pair per line, world metres; a blank line
  // starts the next guide; `#` comments are ignored.
  const blocks = String(text || '').split(/\n\s*\n/)
  for (const block of blocks) {
    const pts = []
    for (const raw of block.split('\n')) {
      const s = raw.split('#')[0].trim()
      if (!s) continue
      const m = s.split(/[,\s]+/).map(Number)
      if (m.length >= 2 && Number.isFinite(m[0]) && Number.isFinite(m[1])) pts.push({ x: m[0], z: m[1] })
    }
    if (pts.length >= 2) out.push({ id: `authored${out.length}`, points: pts })
  }
  return out
}

export default definePlugin({
  type: 'water_conflict',
  cat: 'data',
  name: 'Guide Conflict',
  ins: ['Routing', 'Flow', 'Guides'],
  desc: 'Where and by how much an authored river guide fights the terrain: per-sample elevation deficit in metres, and where the guide runs against the routed flow. Reports the conditioning branch that would fix it; never applies it.',
  params: [
    P.select('branch', 'Offered branch', [
      ['breach', 'Depression Policy — breach an outlet'],
      ['fill', 'Depression Policy — fill to spill'],
      ['hydrofix', 'HydroFix — writes terrain height'],
    ], 'breach'),
    // Present so the node can be driven before S4.3's spline editor exists. Not a substitute for it:
    // these coordinates are not document-owned features and carry no stable IDs.
    P.text('guide', 'Guide points (x,z metres per line)', '', 6),
  ],

  inputs: [
    // A ROUTING SURFACE, not terrain. Wire this from a Depression Policy node: a guide judged
    // against unconditioned ground reports every closed hollow along it as a conflict, which is
    // true but useless — the author wants to know about the hollows the policy will not resolve.
    { id: 'surface', name: 'Routing', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'routingSurface', unit: 'none', role: 'data', required: true },
    { id: 'flowDirection', name: 'Flow', kind: 'vectorRaster', storage: 'RGB32F', components: 3,
      semantic: 'flowDirection', unit: 'none', role: 'data', required: false },
    { id: 'guides', name: 'Guides', kind: 'featureSet', storage: 'RECORDS', components: 1,
      semantic: 'feature', unit: 'none', role: 'data', required: false },
  ],
  outputs: [
    // SIGNED, and negative by construction: this is the cut an explicit conditioning branch WOULD
    // make, in the same sign convention S4.1's conditioningDelta uses (positive fill, negative cut).
    // It is a report, not an instruction — nothing downstream applies it.
    //
    // The natural unit here is metres, and there is no scalarRaster semantic for a conflict depth in
    // the S2.1 vocabulary yet. Emitting `conditioningDelta` in normalized height is the honest
    // choice available today; the metre figures ride on the conflict records, which are the primary
    // product of this node anyway. See the story report for the ports.js addition this wants.
    { id: 'conditioningDelta', name: 'Deficit', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'conditioningDelta', unit: 'none', primary: true, lens: 'derived' },
    { id: 'conflicts', name: 'Conflicts', kind: 'featureSet', storage: 'RECORDS', components: 1,
      semantic: 'feature', unit: 'none', lens: 'derived' },
  ],

  eval: (p, ins, node, ctx) => {
    const src = ins[0]
    if (!src) return { values: new Map([['conditioningDelta', newField()]]) }
    const w = fieldW(), hgt = fieldH(), N = w * hgt
    const hex = isHex()
    const cs = cellSizeM()
    // terrainDef.height is the metre span of one unit of normalized height — the same factor
    // thermal.js divides by to turn a repose angle into a normalized slope. Without it every deficit
    // would be a fraction nobody can compare to a hillside.
    const heightScaleM = terrainDef.height

    const guides = collectGuides(ins[2], p.guide)
    const delta = newField()
    const records = []
    const branch = CONDITIONING_BRANCHES[p.branch] ? p.branch : 'breach'
    // Only unpack the direction raster when one is wired. A missing flow input must stay reportable
    // AS missing: `flowSupplied:false` is a different claim from "the guide agrees with the flow",
    // and folding them together is how an unrouted graph starts reading as a clean one.
    const flow = ins[1] && ins[1].length >= N * 3 ? flowFromVectorRaster(ins[1], N, 3) : null

    for (const g of guides) {
      let rep
      try {
        rep = analyzeGuideConflict(src, w, hgt, g.points, { cellSizeM: cs, heightScaleM, hex, flow, resolution: w })
      } catch (e) {
        // A malformed guide is reported as a malformed guide. Swallowing it would leave the author
        // looking at an empty conflict list that means "nothing wrong" and "nothing measured" at
        // the same time.
        records.push({ id: g.id, kind: 'waterGuideConflict', error: String(e.message || e), conflicts: [] })
        continue
      }
      // Stamp the cut a repair would make at the nearest cell of each sample, deepest wins. Nearest,
      // not spread: the deficit is a property of one point on the guide, and blurring it across a
      // footprint is the smoothing this story forbids, applied to the raster instead of the array.
      const rowPitch = cs * (hex ? HEX_ROW : 1)
      for (let i = 0; i < rep.count; i++) {
        if (!(rep.deficit[i] > 0)) continue
        const r = Math.min(hgt - 1, Math.max(0, Math.round(rep.z[i] / rowPitch)))
        const c = Math.min(w - 1, Math.max(0, Math.round(rep.x[i] / cs - (hex && (r & 1) ? 0.5 : 0))))
        const k = r * w + c
        if (-rep.deficit[i] < delta[k]) delta[k] = -rep.deficit[i]
      }
      records.push({
        id: g.id, kind: 'waterGuideConflict',
        samples: rep.count, spacingM: rep.spacingM, lengthM: rep.lengthM,
        flowSupplied: rep.flowSupplied,
        maxDeficitM: rep.maxDeficitM, maxAtM: rep.maxAtM,
        conflictCount: rep.conflictCount, opposedCount: rep.opposedCount, unroutedCount: rep.unroutedCount,
        conflicts: rep.conflicts,
        // The offer. `null` when the guide is fine — an offer to fix nothing trains the author to
        // accept offers without reading them.
        proposal: proposeConditioningBranch(rep, { mode: branch }),
      })
    }

    const values = new Map([['conditioningDelta', delta]])
    const demanded = ctx && ctx.demanded
    if (!demanded || demanded.has('conflicts')) values.set('conflicts', records)
    return { values }
  },
})
