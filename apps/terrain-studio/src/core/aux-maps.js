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
  soilDepth: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'planned', owner: 'S3.2' },
  sedimentDepth: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'planned', owner: 'S3.1' },
  sandDepth: { lens: 'state', kind: 'scalarRaster', unit: 'm', status: 'planned', owner: 'S7.3' },
  wetness: { lens: 'state', kind: 'scalarRaster', unit: 'none', status: 'planned', owner: 'S3.3' },

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
