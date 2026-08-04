// Auxiliary-map registry and the side-channel debt ledger — ADR-002 S2.4, doctrine chapter 27.
//
// Pure and DOM-free; no legacy.js import.
//
// WHAT THIS IS FOR. Climate, geology, hydrology and geometry maps are first-class fields of the
// DAG, not afterthoughts. Today most of them are not fields at all: thirteen plugins stash values
// on the node instance (`nd._temperatureC = ...`) and downstream code reaches in and reads them.
// That is a side channel — invisible to the graph, untyped, unorderable, and impossible to demand
// or cache per output. ADR-002 freezes that inventory so it can be migrated to real ports and
// DRAINED, one field at a time, by the sprint that owns each field.
//
// THE THREE LENSES, and why the distinction is not bookkeeping:
//
//   derived    A pure function of the CURRENT geometry. Recomputed, never carried. Slope, aspect,
//              curvature, occlusion, normals. Carrying one is a bug: a slope map computed before
//              erosion describes a landscape that no longer exists.
//   state      Path-dependent. Carried between steps and co-updated in the same pass by anything
//              that moves material. Soil depth, sediment depth, snow depth, wetness. A node that
//              lowers height without co-updating these is discarding history no later pass can
//              recover — the co-evolution rule.
//   continued  Carried across evaluations or epochs, with its own version identity. Snow across a
//              season, an erosion sim resumed from a prior state.
//
// A map's lens decides whether it may be cached, whether it must be invalidated when geometry
// changes, and who is allowed to write it. Getting it wrong is why "recompute everything" and
// "cache everything" are both wrong.

export const AUX_LENSES = Object.freeze(['derived', 'state', 'continued'])

/**
 * The standard map catalogue. `status` is honest about what exists TODAY:
 *   'port'         already a real typed port
 *   'sideChannel'  still a node-instance stash, listed in the ledger below
 *   'planned'      named by a later sprint, no implementation yet
 */
export const AUX_MAPS = Object.freeze({
  // --- geometry, all derived -----------------------------------------------------------------
  normal: { lens: 'derived', kind: 'vectorRaster', unit: 'none', status: 'port', owner: 'S2.6' },
  slope: { lens: 'derived', kind: 'scalarRaster', unit: 'none', status: 'port', owner: 'S1' },
  aspect: { lens: 'derived', kind: 'scalarRaster', unit: 'rad', status: 'port', owner: 'S1.5' },
  curvature: { lens: 'derived', kind: 'scalarRaster', unit: 'none', status: 'port', owner: 'S1' },
  occlusion: { lens: 'derived', kind: 'scalarRaster', unit: 'none', status: 'port', owner: 'S1' },

  // --- climate -------------------------------------------------------------------------------
  temperature: { lens: 'derived', kind: 'scalarRaster', unit: 'degC', status: 'sideChannel', owner: 'S5.1' },
  solarExposure: { lens: 'derived', kind: 'scalarRaster', unit: 'none', status: 'sideChannel', owner: 'S5.1' },
  solarShadow: { lens: 'derived', kind: 'scalarRaster', unit: 'none', status: 'sideChannel', owner: 'S5.1' },
  wind: { lens: 'derived', kind: 'vectorRaster', unit: 'mPerS', status: 'sideChannel', owner: 'S5.1' },
  moisture: { lens: 'derived', kind: 'scalarRaster', unit: 'none', status: 'planned', owner: 'S5.2' },

  // --- cover, all state: path-dependent and co-updated -----------------------------------------
  // S3.2 landed this one: `regolith` declares a real typed `soilDepth` output — scalarRaster,
  // metres, state lens — so the row is no longer a plan. `status` is a claim about production and
  // _verify_soildepth.js checks it against the live registry, so it cannot be promoted early.
  soilDepth: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'port', owner: 'S3.2' },
  // S3.4 promoted these two from `planned` to `port`. `status` is a claim about what EXISTS, not
  // about who fills it: the explicit state selectors (`s_sedimentDepth`, `s_sandDepth`) declare
  // real typed scalarRaster/metre/state ports for both, and d_deposits now takes `sedimentDepth`
  // on a typed slot. `owner` is unchanged and deliberately so — it names the sprint that owns the
  // PRODUCER, and neither has one yet. This row used to name S3.1 and that was wrong, discovered
  // when S3.1 shipped: the hydraulic solver emits `sediment`, which is a TRANSPORT quantity — how
  // much material a pass moved — and ports.js is explicit that `sedimentDepth` is a LAYER
  // THICKNESS, how much is lying there. They are different fields and conflating them is precisely
  // what the two separate semantics exist to prevent. The thing that turns transport into a change
  // in cover thickness is S3.3's cover-aware deposition, so S3.3 owns this row. S7.3 is the first
  // thing that will deposit sand. A named port with no producer is exactly the state this row
  // should describe, and calling it `planned` while three plugins declare it would be the registry
  // disagreeing with the registry.
  sedimentDepth: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'port', owner: 'S3.3' },
  sandDepth: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'port', owner: 'S7.3' },
  // OWNER CORRECTED IN S3.5, and the row stays `planned` on purpose. It named S3.3, and S3.3 has
  // shipped without it — a row naming a sprint that came and went is the registry disagreeing with
  // the tree. The candidate producer was hydraulic: its pipe solver carries a per-cell water column
  // that S3.1's atlas already reads back, so publishing it would have cost no second sync point.
  // Measured before deciding, and it is not this field. The column is a rain-accumulation transient
  // — mean 0.00888 at 8 iterations to 0.07870 at 360, tracking the no-flow `(w+rain)*evap` recursion
  // to within 1%, and only 51.3% converged at the shipped 48 — whose spatial pattern also moves with
  // the slider (Pearson r 0.176 between the 48- and 360-iteration fields) and with Res Lock. It is
  // additionally a DEPTH in normalised height units, which is `waterDepth` below, not a
  // dimensionless index; normalising it would need a reference depth nobody has measured, the same
  // fabricated constant hydraulic's `precipitation` port refuses. And two of hydraulic's three
  // engines have no cell water field at all.
  //
  // WHAT THIS ROW IS STILL FOR is the SPLIT sprint-02:194-195 and BACKLOG §2 require: the state map
  // is path-dependent SATURATION, its derived companion is TWI, and "a plugin declaring one does not
  // satisfy the other". The plan's producer for that is Sprint 5 — sprint-05:26 gives S5.3
  // "meltwater/wetness", :27 and :165 give S5.4 "melt co-updates wetness", :172 closes it with a
  // melt ledger — so `owner` names S5.3, the first story that can fill it.
  wetness: { lens: 'state', kind: 'scalarRaster', unit: 'none', status: 'planned', owner: 'S5.3' },

  // --- hydrology -------------------------------------------------------------------------------
  waterSurface: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'planned', owner: 'S4.4' },
  waterDepth: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'planned', owner: 'S4.4' },
  flowVelocity: { lens: 'derived', kind: 'vectorRaster', unit: 'mPerS', status: 'planned', owner: 'S4.2' },
  discharge: { lens: 'derived', kind: 'scalarRaster', unit: 'none', status: 'planned', owner: 'S4.2' },
  basinId: { lens: 'derived', kind: 'labelRaster', unit: 'none', status: 'planned', owner: 'S4.4' },

  // --- transient -------------------------------------------------------------------------------
  // Snow is CONTINUED, not state: it carries an epoch across evaluations, which is exactly why
  // S5.3 has to version it rather than recompute it.
  snowDepth: { lens: 'continued', kind: 'scalarRaster', unit: 'm', status: 'sideChannel', owner: 'S5.3' },
})

/**
 * THE DEBT LEDGER — the measured side-channel inventory, frozen.
 *
 * Produced by scanning `\b(nd|node)\.(_[A-Za-z0-9]+)\s*=(?!=)` over src/plugins/**\/*.js excluding
 * index.js. Measured 25 channels across 13 plugins. This is not ADR-002's illustrative six-plugin
 * table; it is what the code actually does.
 *
 * `lens` here classifies the CHANNEL, and four values are not maps at all:
 *   semantic          a real field that belongs on a port — the actual debt
 *   alias-of-primary  the same array object the eval already returned; not an independent product
 *   compat-render     renderer-only, but folded into the gated digest, so it cannot just be deleted
 *   graph-input       an input value written back onto the node, not an output
 *   ui                presentation state
 *
 * `gated` is measured against _verify_digest.js's AUX/SCALARS tables, never guessed: a gated
 * channel cannot be removed without moving a digest, so S2.3+ must migrate it rather than drop it.
 *
 * THE RULE: this ledger may only SHRINK. A story that migrates a field to a port removes its rows;
 * nothing may add one. `_verify_aux_registry.js` asserts the count, so a new side channel is a
 * failing gate rather than a quiet regression.
 */
export const SIDE_CHANNEL_LEDGER = Object.freeze([
  { node: 'colorerosion', channel: '_height', lens: 'alias-of-primary', targetPort: null, gated: false, owner: 'none' },
  { node: 'colorerosion', channel: '_mask', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  { node: 'colorerosion', channel: '_sediment', lens: 'semantic', targetPort: 'sedimentDepth', gated: false, owner: 'S3.1' },
  { node: 'd_heat', channel: '_inputError', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  // gated:false, and it was worth checking rather than pattern-matching. d_temperature and
  // d_sunshadow both have _solarExposure in the digest's AUX table; d_heat does NOT — its only
  // gated channel is _temperatureC. So this one can be migrated without moving a digest, and the
  // other two cannot.
  { node: 'd_heat', channel: '_solarExposure', lens: 'semantic', targetPort: 'solarExposure', gated: false, owner: 'S5.1' },
  { node: 'd_heat', channel: '_solarShadow', lens: 'semantic', targetPort: 'solarShadow', gated: false, owner: 'S5.1' },
  { node: 'd_heat', channel: '_temperatureC', lens: 'semantic', targetPort: 'temperature', gated: true, owner: 'S5.1' },
  { node: 'd_sunshadow', channel: '_solarExposure', lens: 'semantic', targetPort: 'solarExposure', gated: true, owner: 'S5.1' },
  { node: 'd_sunshadow', channel: '_solarShadow', lens: 'alias-of-primary', targetPort: null, gated: false, owner: 'none' },
  { node: 'd_temperature', channel: '_solarExposure', lens: 'semantic', targetPort: 'solarExposure', gated: true, owner: 'S5.1' },
  { node: 'd_temperature', channel: '_solarShadow', lens: 'semantic', targetPort: 'solarShadow', gated: true, owner: 'S5.1' },
  { node: 'd_temperature', channel: '_temperatureC', lens: 'semantic', targetPort: 'temperature', gated: true, owner: 'S5.1' },
  { node: 'd_wind', channel: '_wind', lens: 'semantic', targetPort: 'wind', gated: true, owner: 'S5.1' },
  { node: 'd_windmodify', channel: '_inputError', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  { node: 'd_windmodify', channel: '_wind', lens: 'semantic', targetPort: 'wind', gated: true, owner: 'S5.1' },
  { node: 'drawmask', channel: '_reference', lens: 'graph-input', targetPort: 'reference', gated: false, owner: 'S2.2' },
  { node: 'layout', channel: '_shapeCount', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  { node: 'satmap', channel: '_driver', lens: 'compat-render', targetPort: 'colorDriver', gated: true, owner: 'S2.6' },
  { node: 'satmap', channel: '_mask', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  { node: 'satmapblend', channel: '_mask', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  { node: 'snow', channel: '_inputError', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  { node: 'snow', channel: '_snowLayer', lens: 'semantic', targetPort: 'snowDepth', gated: true, owner: 'S5.3' },
  { node: 'transform', channel: '_xfMode', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
  { node: 'weathering', channel: '_height', lens: 'alias-of-primary', targetPort: null, gated: false, owner: 'none' },
  { node: 'weathering', channel: '_mask', lens: 'ui', targetPort: null, gated: false, owner: 'none' },
])

/** Rows that are genuine migration debt — a real field that belongs on a port. */
export const semanticDebt = () => SIDE_CHANNEL_LEDGER.filter(r => r.lens === 'semantic')

/** Debt grouped by the sprint that must close it, so a sprint can assert its own row count reached zero. */
export function debtByOwner() {
  const out = {}
  for (const row of semanticDebt()) (out[row.owner] = out[row.owner] || []).push(row)
  return out
}

/**
 * Validate an auxiliary-map declaration at registration time.
 * A `derived` map may never be declared `continued` or carried, and a map whose lens contradicts
 * the catalogue is a declaration error rather than a preference.
 */
export function validateAuxDeclaration(mapId, { lens } = {}) {
  const problems = []
  const known = AUX_MAPS[mapId]
  if (!known) { problems.push({ code: 'AUX_UNKNOWN_MAP', mapId }); return problems }
  if (lens != null && !AUX_LENSES.includes(lens)) problems.push({ code: 'AUX_LENS_UNKNOWN', mapId, lens })
  if (lens != null && lens !== known.lens) problems.push({ code: 'AUX_LENS_CONFLICT', mapId, declared: lens, expected: known.lens })
  return problems
}
