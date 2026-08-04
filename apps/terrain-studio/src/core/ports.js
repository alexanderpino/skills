// Typed port descriptors and the connection-compatibility matrix — ADR-002, story S2.1.
//
// Pure and DOM-free, and it must stay that way: it never imports legacy.js, so it cannot join the
// legacy<->plugin cycle or trip the module-evaluation TDZ rule that `npm run plugins:tdz` enforces.
//
// S2.1 lands the VOCABULARY and the MATRIX only. It changes no UI, no edge schema, and no
// arithmetic: all pre-existing node types stay bit-identical with `skipped = 0`. Edges keep their
// `{from,to,slot}` shape until S2.2; demand-driven evaluation is S2.3.
//
// Three decisions here were corrected against measured production behaviour rather than taken
// from the story text, and each would have refused wiring the app ships today:
//
//   1. MASK INPUTS ARE GENERIC, NOT `mask`. Every mask slot accepts an arbitrary scalar field —
//      _verify_digest.js wires a plain `perlin` into ~25 mask slots and every one evaluates, and
//      `maskApply` validates nothing. Declaring `semantic:'mask'` would make all 25 a semantic
//      mismatch, and a [0,1] range contract would refuse every unbounded source. So mask slots are
//      `anyMask`: any semantic, but unit must be `none`, because every mask consumer multiplies
//      the field as a dimensionless weight. A slope or flow field into a mask slot is ordinary
//      use; a degC or m/s field into one is a real defect.
//
//   2. UNIT COMPATIBILITY IS IDENTITY, NOT DIMENSIONAL EQUALITY. ADR-002's descriptor section says
//      "dimensionally equal units" while its very next paragraph says "There are no implicit ...
//      unit conversions". Those conflict. Identity is the only reading under which rad->deg and
//      degC->K are refused, which is what "no implicit conversion" must mean. `dim` is recorded
//      for a future EXPLICIT converter node and is deliberately not consulted by canConnect.
//
//   3. A `semanticFrom` SOURCE IS DEFERRED AT CONNECT TIME, NOT RESOLVED. Today's
//      `fieldSemantics:'preserve-primary'` / `'temperature-pair'` / `passthrough:true` mean a
//      node's output semantic depends on what is wired INTO it, which is not known when the user
//      drags the wire. Such a source reports DEFERRED and is allowed; refusing it would break
//      shipped edges, and resolving it would require evaluating the graph to draw a line.

export const PORTS_VERSION = 1

export const VALUE_KINDS = Object.freeze(['scalarRaster', 'vectorRaster', 'labelRaster', 'scalar', 'featureSet'])

export const STORAGE = Object.freeze({
  R32F: Object.freeze({ kind: 'scalarRaster', ctor: 'Float32Array', components: 1 }),
  RG32F: Object.freeze({ kind: 'vectorRaster', ctor: 'Float32Array', components: 2 }),
  RGB32F: Object.freeze({ kind: 'vectorRaster', ctor: 'Float32Array', components: 3 }),
  I32: Object.freeze({ kind: 'labelRaster', ctor: 'Int32Array', components: 1 }),
  F64: Object.freeze({ kind: 'scalar', ctor: 'number', components: 1 }),
  RECORDS: Object.freeze({ kind: 'featureSet', ctor: 'Array', components: 1 }),
})

// `dim` exists for a future explicit converter node. canConnect does NOT read it — see note 2.
export const UNITS = Object.freeze({
  none: { dim: '1' }, m: { dim: 'L' }, mPerCell: { dim: 'L/cell' }, m3: { dim: 'L^3' },
  degC: { dim: 'Theta' }, K: { dim: 'Theta' }, mPerS: { dim: 'L/T' },
  rad: { dim: 'A' }, deg: { dim: 'A' }, percent: { dim: '1' }, days: { dim: 'T' },
  // Sprint 3. Regolith production is cited in mm/yr (Heimsath et al. 1997) and authoring it in
  // metres per year would put the interesting numbers at 1e-4, where a typo is invisible. `yr` is
  // required authored data for the production law and has no default: a duration nobody stated is
  // not a duration of 1.
  mmPerYr: { dim: 'L/T' }, yr: { dim: 'T' },
})

export const SEMANTICS = Object.freeze({
  height: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  // Not `height`: d_height is normalize(ins[0]) — "0 = tile minimum, 1 = tile maximum" — and the
  // shipped showcase wires it into d_temperature's slot labelled "Relative height".
  relativeHeight: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  mask: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  temperature: { kind: 'scalarRaster', defaultUnit: 'degC', continuous: true },
  sunVisibility: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  solarExposure: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  windSpeed: { kind: 'scalarRaster', defaultUnit: 'mPerS', continuous: true },
  wind: { kind: 'vectorRaster', defaultUnit: 'mPerS', continuous: true },
  // A surface normal is a unit 3-vector per sample, interleaved xyz. It is NOT a scalar raster
  // that happens to have three of them: interpolating or tonemapping it is meaningless, which is
  // why it needs a vectorRaster port and could not ship in Sprint 1.
  normal: { kind: 'vectorRaster', defaultUnit: 'none', continuous: true },
  velocity: { kind: 'vectorRaster', defaultUnit: 'mPerS', continuous: true },
  aspect: { kind: 'scalarRaster', defaultUnit: 'rad', continuous: true },
  slope: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  curvature: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  flow: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  occlusion: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  deposits: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  wear: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  peaks: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  texture: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  uplift: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  sediment: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  // --- Sprint 3: the solid stack as explicit STATE, in metres --------------------------------
  // `sediment` above is a transport quantity — how much material a pass moved. These are LAYER
  // THICKNESSES, which is a different thing: they persist between passes, they are what a
  // transport node consumes cover from, and solidTop = bedrockHeight + soilDepth + sedimentDepth
  // + sandDepth is the identity S3.3 has to close. Naming one of them `sediment` would have made
  // "how much moved" and "how much is lying there" the same port.
  soilDepth: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  sedimentDepth: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  sandDepth: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  solidTop: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  // The STABLE physical frame, distinct from `relativeHeight` (autolevel, field-dependent) and
  // from `height`. The decision on record is two named frames: the viewport keeps autolevel, and
  // physical nodes take metres from a stable datum through an explicit adapter. An absolute
  // elevation that moves when the field's range moves cannot carry a conservation identity.
  bedrockHeight: { kind: 'scalarRaster', defaultUnit: 'm', continuous: true },
  precipitation: { kind: 'scalarRaster', defaultUnit: 'mmPerYr', continuous: true },
  regolithProduction: { kind: 'scalarRaster', defaultUnit: 'mmPerYr', continuous: true },
  colorDriver: { kind: 'scalarRaster', defaultUnit: 'none', continuous: true },
  color: { kind: 'vectorRaster', defaultUnit: 'none', continuous: true },
  basinId: { kind: 'labelRaster', defaultUnit: 'none', continuous: false },
  feature: { kind: 'featureSet', defaultUnit: 'none', continuous: false },
})

// Legal on INPUTS only. An output may never declare a generic: a producer must say what it makes.
export const GENERICS = Object.freeze({
  anyScalarRaster: { kind: 'scalarRaster', admits: '*', unitPolicy: 'any' },
  anyMask: { kind: 'scalarRaster', admits: '*', unitPolicy: 'none-only' },
  anySignedDriver: { kind: 'scalarRaster', admits: '*', unitPolicy: 'any' },
})

export const NO_LABEL = -1

export const RANGE = Object.freeze({
  unbounded: () => ({ type: 'unbounded', finite: true }),
  unit: () => ({ type: 'unit', finite: true }),
  closed: (lo, hi) => ({ type: 'closed', lo, hi, finite: true }),
  angle: (lo, hi) => ({ type: 'angle', lo, hi, wrap: true, finite: true }),
  labels: (min, max, noLabel = NO_LABEL) => ({ type: 'labels', min, max, noLabel, finite: true }),
})

export const PORT_ERROR_CODES = Object.freeze([
  'PORT_ID_INVALID', 'PORT_ID_DUPLICATE', 'PORT_KIND_UNKNOWN', 'PORT_SEMANTIC_UNKNOWN',
  'PORT_UNIT_UNKNOWN', 'PORT_STORAGE_UNKNOWN', 'PORT_STORAGE_KIND_MISMATCH',
  'PORT_COMPONENTS_MISMATCH', 'PORT_GENERIC_ON_OUTPUT', 'PORT_PRIMARY_COUNT',
  'PORT_SEMANTIC_FROM_CONFLICT', 'PORT_GROUP_TOO_SMALL', 'PORT_LABEL_INVARIANT',
  'PORT_LENS_UNKNOWN',
])

export class PortError extends Error {
  constructor(code, message, detail) { super(message); this.name = 'PortError'; this.code = code; this.detail = detail }
}

const PORT_ID_RE = /^[a-z][A-Za-z0-9]*$/
const LENSES = Object.freeze(['derived', 'state', 'continued'])

const problem = (out, code, message, detail) => { out.push({ code, message, detail }); return out }

/** Validate one port descriptor. `side` is 'input' or 'output'. Returns an array of problems. */
export function validatePort(port, side, problems = []) {
  if (!port || typeof port !== 'object') return problem(problems, 'PORT_ID_INVALID', 'port must be an object')
  if (typeof port.id !== 'string' || !PORT_ID_RE.test(port.id)) {
    problem(problems, 'PORT_ID_INVALID', `port id ${JSON.stringify(port.id)} must match ${PORT_ID_RE}`, { id: port.id })
  }
  if (!VALUE_KINDS.includes(port.kind)) {
    problem(problems, 'PORT_KIND_UNKNOWN', `unknown value kind ${JSON.stringify(port.kind)}`, { id: port.id, kind: port.kind })
  }
  const storage = STORAGE[port.storage]
  if (!storage) {
    problem(problems, 'PORT_STORAGE_UNKNOWN', `unknown storage ${JSON.stringify(port.storage)}`, { id: port.id, storage: port.storage })
  } else if (storage.kind !== port.kind) {
    problem(problems, 'PORT_STORAGE_KIND_MISMATCH', `storage ${port.storage} is ${storage.kind}, port declares ${port.kind}`, { id: port.id })
  } else if ((port.components ?? 1) !== storage.components) {
    problem(problems, 'PORT_COMPONENTS_MISMATCH', `storage ${port.storage} has ${storage.components} components, port declares ${port.components}`, { id: port.id })
  }

  const deferred = side === 'output' && port.semanticFrom != null
  if (deferred) {
    // A deferred output resolves its semantic and unit from inputs at evaluation time, so
    // declaring them here would be a second, unreconcilable source of truth.
    if (port.semantic !== undefined || port.unit !== undefined) {
      problem(problems, 'PORT_SEMANTIC_FROM_CONFLICT', `port ${port.id} declares semanticFrom and also semantic/unit`, { id: port.id })
    }
  } else {
    const generic = GENERICS[port.semantic]
    if (generic && side === 'output') {
      problem(problems, 'PORT_GENERIC_ON_OUTPUT', `output ${port.id} may not declare the generic ${port.semantic}; a producer must say what it makes`, { id: port.id })
    }
    if (!generic && !SEMANTICS[port.semantic]) {
      problem(problems, 'PORT_SEMANTIC_UNKNOWN', `unknown semantic ${JSON.stringify(port.semantic)}`, { id: port.id, semantic: port.semantic })
    }
    if (!UNITS[port.unit]) {
      problem(problems, 'PORT_UNIT_UNKNOWN', `unknown unit ${JSON.stringify(port.unit)}`, { id: port.id, unit: port.unit })
    }
  }

  if (port.lens != null && !LENSES.includes(port.lens)) {
    problem(problems, 'PORT_LENS_UNKNOWN', `unknown lens ${JSON.stringify(port.lens)}`, { id: port.id, lens: port.lens })
  }

  if (port.kind === 'labelRaster') {
    const r = port.range
    const bad = port.storage !== 'I32' || port.unit !== 'none' || !r || r.type !== 'labels'
      || !Number.isInteger(r.min) || !Number.isInteger(r.max) || r.min > r.max
      || !Number.isInteger(r.noLabel) || (r.noLabel >= r.min && r.noLabel <= r.max)
    if (bad) {
      problem(problems, 'PORT_LABEL_INVARIANT',
        `labelRaster ${port.id} requires storage I32, unit none, a labels range with integer min<=max, and a noLabel sentinel outside [min,max]`,
        { id: port.id })
    }
  }
  return problems
}

/**
 * Validate a plugin's whole port block at registration time.
 * `source` is 'legacy-adapter' (a type carried over by the adapter) or 'declared' (a plugin that
 * authored its own ports). Adapted types must name exactly one primary output, because a v1
 * document's edges resolve their source to it. A newly declared plugin has no v1 document, so
 * ADR-002 allows at most one.
 */
export function validatePortList({ inputs = [], outputs = [], source = 'declared', groups = {} } = {}) {
  const problems = []
  for (const side of [['input', inputs], ['output', outputs]]) {
    const [name, list] = side
    const seen = new Set()
    for (const port of list) {
      validatePort(port, name, problems)
      if (port && typeof port.id === 'string') {
        if (seen.has(port.id)) problem(problems, 'PORT_ID_DUPLICATE', `duplicate ${name} port id ${port.id}`, { id: port.id })
        seen.add(port.id)
      }
    }
  }
  const primaries = outputs.filter(p => p && p.primary)
  if (source === 'legacy-adapter' && outputs.length && primaries.length !== 1) {
    problem(problems, 'PORT_PRIMARY_COUNT', `an adapted type must declare exactly one primary output (found ${primaries.length})`, { count: primaries.length })
  }
  if (source === 'declared' && primaries.length > 1) {
    problem(problems, 'PORT_PRIMARY_COUNT', `at most one primary output (found ${primaries.length})`, { count: primaries.length })
  }
  for (const [groupId, members] of Object.entries(groups || {})) {
    if (!Array.isArray(members) || members.length < 2) {
      problem(problems, 'PORT_GROUP_TOO_SMALL', `atomic output group ${groupId} needs at least two members`, { groupId, members })
    }
  }
  return problems
}

/**
 * Can a source output be wired to a destination input?
 * Returns { ok, reason, code, deferred }. `deferred` means the source's semantic is not knowable
 * until evaluation (see note 3) — the connection is permitted and S2.3 revalidates with the
 * resolved semantic.
 */
export function canConnect(sourcePort, destPort) {
  if (!sourcePort || !destPort) return { ok: false, code: 'PORT_ID_INVALID', reason: 'missing port descriptor' }

  // KIND ADAPTS ONLY WHERE A PORT SAYS IT DOES. `kindFrom` marks a port that carries whatever
  // arrives rather than one fixed kind — the typed identity nodes of S8.1, whose whole contract is
  // that output kind, semantic and unit equal the input's. Its story requires "scalar AND vector
  // fixtures", and without this a Route declaring scalarRaster would refuse the only vectorRaster
  // in the registry the moment connection-time checking arrived, which is exactly what happened.
  //
  // This is NOT a wildcard for ordinary nodes: a port must opt in, an input's `kindFrom` says "I
  // adapt", and an output's says "my kind is not knowable until evaluation" — the same deferral
  // `semanticFrom` already uses, applied to the kind axis. Both sides skip the components check
  // with it, because a 3-component vector through a nominally 1-component identity is the case.
  const destAdaptsKind = destPort.kindFrom != null
  const srcDefersKind = sourcePort.kindFrom != null
  if (!destAdaptsKind && !srcDefersKind) {
    if (sourcePort.kind !== destPort.kind) {
      return { ok: false, code: 'KIND_MISMATCH', reason: `${sourcePort.name || sourcePort.id} carries ${sourcePort.kind}, ${destPort.name || destPort.id} expects ${destPort.kind}` }
    }
    if ((sourcePort.components ?? 1) !== (destPort.components ?? 1)) {
      return { ok: false, code: 'COMPONENTS_MISMATCH', reason: `${sourcePort.components ?? 1}-component source into a ${destPort.components ?? 1}-component input` }
    }
  }

  const generic = GENERICS[destPort.semantic]
  const deferred = sourcePort.semanticFrom != null

  // A categorical field may never flow into a destination that will interpolate or tonemap it:
  // averaging two basin IDs produces a third basin that does not exist.
  //
  // NOT REACHABLE IN S2.1, and saying so is the point. The only categorical semantics today are
  // basinId (labelRaster) and feature (featureSet), and every continuous destination is
  // scalarRaster or vectorRaster — so the kind check above always refuses first. This branch can
  // only fire once something declares a labelRaster-kind destination with a continuous semantic,
  // which S4.4's basin products and S2.6's aux migration are the first candidates for. It is kept
  // because ADR-002 requires the rule, not because it is currently exercised: counting it as
  // covered would be the vacuous-gate mistake in a new place.
  const destSem = generic ? null : SEMANTICS[destPort.semantic]
  if (!deferred) {
    const srcSem = SEMANTICS[sourcePort.semantic]
    if (srcSem && srcSem.continuous === false) {
      const destContinuous = generic ? true : (destSem ? destSem.continuous : true)
      if (destContinuous) {
        return { ok: false, code: 'LABEL_INTO_CONTINUOUS', reason: `${sourcePort.semantic} is categorical and cannot pass through a continuous input` }
      }
    }
  }

  if (generic) {
    // `anyMask` admits any semantic but insists the field is dimensionless, because every mask
    // consumer multiplies it as a weight.
    if (generic.unitPolicy === 'none-only' && !deferred && sourcePort.unit !== 'none') {
      return { ok: false, code: 'UNIT_MISMATCH', reason: `a mask input takes a dimensionless field; ${sourcePort.name || sourcePort.id} is in ${sourcePort.unit}` }
    }
    return { ok: true, deferred }
  }

  if (deferred) {
    // Unresolved until evaluation. Permitted here; S2.3 revalidates once the semantic is known.
    return { ok: true, deferred: true }
  }

  if (sourcePort.semantic !== destPort.semantic) {
    return { ok: false, code: 'SEMANTIC_MISMATCH', reason: `${sourcePort.name || sourcePort.id} carries ${sourcePort.semantic}, ${destPort.name || destPort.id} expects ${destPort.semantic}` }
  }
  // Identity, not dimensional equality — see note 2. rad->deg and degC->K are refusals.
  if (sourcePort.unit !== destPort.unit) {
    return { ok: false, code: 'UNIT_MISMATCH', reason: `${sourcePort.unit} into ${destPort.unit}; there are no implicit unit conversions` }
  }
  if (destPort.strictRange) {
    const s = sourcePort.range, d = destPort.range
    const bounded = s && (s.type === 'unit' || s.type === 'closed' || s.type === 'angle' || s.type === 'labels')
    if (!bounded) {
      return { ok: false, code: 'RANGE_CONTRACT_UNSATISFIED', reason: `${destPort.name || destPort.id} requires a bounded ${d ? d.type : 'bounded'} source; ${sourcePort.name || sourcePort.id} is ${s ? s.type : 'unspecified'}` }
    }
  }
  return { ok: true, deferred: false }
}
