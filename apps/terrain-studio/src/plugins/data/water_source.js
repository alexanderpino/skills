// water_source — S4.3, the Water Sources node.
//
// NOT YET REGISTERED. `src/plugins/data/index.js` is owned by another process, so this file is not
// imported anywhere and cannot reach the running app until that one line lands. The story report
// asks for it. Every port declared below validates against today's `src/core/ports.js` — the oracle
// runs `validatePortList` over the real descriptors — so registration is a one-line change and not a
// change that brings a semantic with it.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run until
// the graph is evaluated, so the legacy<->plugin cycle is safe.
//
// WHY THIS NODE EXISTS ALONGSIDE `flow_physical`. That node routes rain. It has no way to express a
// river that arrives from off-map, a spring, or a karst resurgence, because its only water input is a
// precipitation raster — and a desert with a big river through it is precisely the case where the
// rain over the domain is not where the water came from. `03:679-682`: "This is the one change that
// lets a big river cross a dry region without pretending the desert it flows through fed it — the
// Nile and the Colorado are exactly this."
//
// IT IS THE SAME ACCUMULATION. `mfdWeights` and `mfdAccumulate` here are the same functions
// `flow_physical` calls, with the same arguments, in the same order. The only difference is the
// supply array handed to them: rain, plus the authored source term. There is no second router to keep
// in step and no source-aware branch inside the routing to get wrong.
//
// IT NEVER WRITES HEIGHT. The primary output is the routing surface exactly as it arrived — the same
// array object, not a copy — and the oracle compares the caller's array bitwise across a full seed
// and route with a discharge stamp armed as the mutation. `03:702-707`: a spring is a source term in
// the flow field, not a bump in the height field.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField, fieldW, fieldH, cellSizeM, isHex } from '../../legacy.js'
import { mfdWeights, mfdAccumulate, cellAreaM2, precipToSupply } from '../../core/hydrology.js'
import {
  sourceSupply, combineSupply, waterFeatureRecords, normalizeWaterFeatures, parseFeatureText,
} from '../../core/water-sources.js'

/** Merge the features arriving on the port with the ones authored in the text block. IDs are
 *  document-wide, so a collision between the two is refused rather than silently resolved: which of
 *  two features answering to one id wins is not a decision this node should be making. */
function collectFeatures(portRecords, text) {
  const fromPort = Array.isArray(portRecords)
    ? portRecords
    : (portRecords && Array.isArray(portRecords.features) ? portRecords.features : [])
  const authored = parseFeatureText(text)
  return normalizeWaterFeatures({
    sources: [...fromPort.filter(r => r && r.feature !== 'riverGuide' && !Array.isArray(r.points)), ...authored.sources],
    guides: [...fromPort.filter(r => r && (r.feature === 'riverGuide' || Array.isArray(r.points))), ...authored.guides],
  })
}

export default definePlugin({
  type: 'water_source',
  cat: 'data',
  name: 'Water Sources',
  ins: ['Routing', 'Precip', 'Features'],
  desc: 'Authored springs, boundary inflows and river guides. Their discharge in m3/s seeds the same accumulation as drainage area, so a big river can cross a desert. Never modifies terrain.',
  params: [
    // ZERO IS THE DEFAULT, unlike flow_physical's 1000. This node's headline case is a desert: with
    // no rain and no sources the discharge must be exactly zero everywhere, and a non-zero default
    // would mean every graph starts with water nobody asked for and a source's contribution can only
    // ever be read as a ratio against it.
    P.slider('precipMmYr', 'Uniform precip (mm/yr)', 0, 4000, 0, 10),
    // Authored features, one record per line. Present so the node works before a placement tool
    // exists; the port is the document-owned path and takes precedence in the sense that both are
    // merged and a duplicate id between them is refused.
    P.text('features', 'Sources and guides', '', 8),
    // Opt-in. A guide states where a river should run; turning that into water out of nowhere is a
    // much larger claim and has to be one the author made on purpose.
    P.toggle('guideTargets', 'Seed guide target flow at the head', false),
  ],

  inputs: [
    // A ROUTING SURFACE, not terrain. Wire this from a Depression Policy node: seeding a source into
    // an unconditioned hollow terminates its river one cell downstream of the spring.
    { id: 'surface', name: 'Routing', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'routingSurface', unit: 'none', role: 'data', required: true },
    { id: 'precipitation', name: 'Precip', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'precipitation', unit: 'mmPerYr', role: 'data', required: false },
    { id: 'features', name: 'Features', kind: 'featureSet', storage: 'RECORDS', components: 1,
      semantic: 'feature', unit: 'none', role: 'data', required: false },
  ],
  outputs: [
    // Primary is the routing surface exactly as it arrived. Anything downstream that wants the
    // surface gets it unchanged and has to ask explicitly for water — guardrail 1 in the ports.
    { id: 'routingSurface', name: 'Routing', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'routingSurface', unit: 'none', primary: true, lens: 'continued' },
    // Routed discharge: rain plus sources, through the same MFD stack drainage area uses.
    { id: 'discharge', name: 'Discharge', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'discharge', unit: 'm3PerS', lens: 'derived' },
    // The UNROUTED source term — what was injected, before anything moved. It is m3/s at a cell, so
    // `discharge` is the honest semantic available today, but it is NOT a discharge: wiring it into
    // a Rivers node would size channels from the injection rather than from the accumulated flow,
    // and no type check today can refuse that. The story report asks ports.js for a `waterSupply`
    // semantic, and the oracle holds a tripwire that fires the day it lands.
    { id: 'sourceSupply', name: 'Supply', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'discharge', unit: 'm3PerS', lens: 'derived' },
    { id: 'sources', name: 'Sources', kind: 'featureSet', storage: 'RECORDS', components: 1,
      semantic: 'feature', unit: 'none', lens: 'derived' },
    { id: 'guides', name: 'Guides', kind: 'featureSet', storage: 'RECORDS', components: 1,
      semantic: 'feature', unit: 'none', lens: 'derived' },
  ],

  eval: (p, ins, node, ctx) => {
    const src = ins[0]
    // The input array by identity, not a copy. A copy would satisfy a bitwise comparison just as well
    // and would hide an accidental write behind an extra allocation per evaluation.
    const surface = src || newField()
    const values = new Map([['routingSurface', surface]])
    if (!src) return { values }

    const demanded = ctx && ctx.demanded
    const want = k => !demanded || demanded.has(k)
    const products = ['discharge', 'sourceSupply', 'sources', 'guides']
    if (demanded && !products.some(k => demanded.has(k))) return { values }

    const w = fieldW(), hgt = fieldH(), N = w * hgt
    const hex = isHex()
    const cs = cellSizeM()

    let features = null, seeded = null, err = null
    try {
      features = collectFeatures(ins[2], p.features)
      seeded = sourceSupply(surface, w, hgt, features, {
        cellSizeM: cs, hex, includeGuideTargets: !!p.guideTargets,
      })
    } catch (e) {
      // A malformed feature set is reported AS malformed. Swallowing it would leave the author
      // looking at an empty river that means "no sources authored" and "your sources were rejected"
      // at the same time, and only one of those is something they can act on.
      err = { feature: 'waterFeatureError', id: 'error', code: e && e.code ? e.code : 'FEATURE_SHAPE', message: String((e && e.message) || e) }
    }

    if (err) {
      if (want('discharge')) values.set('discharge', newField())
      if (want('sourceSupply')) values.set('sourceSupply', newField())
      if (want('sources')) values.set('sources', [err])
      if (want('guides')) values.set('guides', [])
      return { values }
    }

    if (want('sourceSupply')) {
      const out = newField()
      for (let i = 0; i < N; i++) out[i] = seeded.supply[i]
      values.set('sourceSupply', out)
    }
    if (want('discharge')) {
      const area = cellAreaM2(cs, hex)
      const precip = ins[1]
      // The rain term, converted exactly once by hydrology.js. Both of its factors are armed by the
      // S4.2 gate; re-deriving them here would put the same physics in two files.
      const rain = precip
        ? precipToSupply(precip, area, N)
        : precipToSupply(Number(p.precipMmYr) || 0, area, N)
      const weights = mfdWeights(surface, w, hgt, { hex, cellSizeM: cs })
      const q = mfdAccumulate(surface, combineSupply(rain, seeded.supply), w, hgt, weights)
      const out = newField()
      for (let i = 0; i < N; i++) out[i] = q[i]
      values.set('discharge', out)
    }
    if (want('sources') || want('guides')) {
      const records = waterFeatureRecords(features)
      // Placements ride on the source records: which cell a source landed in, how its footprint was
      // split, and what elevation it sits at are the three things an author checks first when a
      // river does not appear where they put the spring.
      const byIdPlacement = new Map(seeded.placements.map(pl => [pl.id, pl]))
      if (want('sources')) {
        values.set('sources', records.sources.map(r => {
          const pl = byIdPlacement.get(r.id)
          return pl
            ? { ...r, col: pl.col, row: pl.row, cellIndex: pl.index, footprintCells: pl.cells.length, qPerCellM3PerS: pl.qPerCellM3PerS, surfaceValue: pl.surfaceValue }
            : r
        }))
      }
      if (want('guides')) values.set('guides', records.guides)
    }
    return { values }
  },

  note: '<b>Water Sources</b> places authored water as a <i>source term in the flow field</i>, never as a bump in the height field. A source carries <b>discharge</b> in m&sup3;/s, an optional <b>temperature</b>, and a <b>kind</b> from the standard set — distributed rain, boundary inflow, spring, karst resurgence, oasis, glacial/snowmelt. That discharge seeds the <i>same</i> accumulation as drainage area: no new algorithm, a different seed. Under uniform rain with no sources, <code>Q &prop; A</code> and nothing changes; with a source they diverge, and <code>Q</code> is the physically correct driver — stream power is <code>K&middot;Q<sup>m</sup>&middot;S<sup>n</sup></code>, and river width and depth scale on <code>Q</code>.<br><br>Author features one per line:<br><code>source id=nileHead kind=spring x=200 z=320 q=1200 t=24</code><br><code>guide id=nileCourse intent=channel q=1200 200,320 500,330 900,340</code><br>Coordinates are <b>world metres</b>. <code>r=</code> gives a source a footprint radius, which <code>kind=distributedRain</code> requires; a <code>boundaryInflow</code> must sit on a domain edge, because that is what "a river entering off-map" means. IDs are stable handles: they survive a move, a save and a reload, and a pasted copy gets a fresh one.<br><br><b>Uniform precip</b> defaults to <b>0</b> — a desert. With no rain and no sources the discharge is <i>exactly</i> zero everywhere, so any water you see is water you authored. <b>Seed guide target flow</b> is off by default: a guide says where a river should run, and turning that into water out of nowhere is a separate decision.<br><br>This node <b>does not modify height</b>. <b>Routing</b> is the surface exactly as it arrived, bitwise. Salinity is deliberately absent — it stays a proposed registry extension until its unit, advection and export contract are decided.',
})
