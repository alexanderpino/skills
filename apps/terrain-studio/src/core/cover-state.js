// Cover-state reading — story S3.4. Pure and DOM-free; it never imports legacy.js, so it cannot
// join the legacy<->plugin cycle.
//
// THE CONTRACT, in one sentence: typed wires, never a graph-global hidden lookup. A node that needs
// cover state reads it from a CONNECTED TYPED PORT. A disconnected required state is a typed
// missing-input error — never silent zeros, and never a walk of the graph to find "a nearby
// producer".
//
// WHY SILENT ZEROS ARE THE NAMED FAILURE, and not merely untidy. A zero cover field is physically
// meaningful: it is bare bedrock, the state every `soilDepth` map starts in and the state a slope
// returns to once transport has stripped it. If "not wired" also renders as zeros, the two are
// indistinguishable, and every downstream mass balance silently attributes real bedrock exposure to
// a missing wire. So the two halves are one claim: a WIRED zero field is ordinary data and must
// evaluate clean, and a DISCONNECTED port must raise `MISSING_REQUIRED_INPUT` naming the port.
//
// WHY THE REFUSAL IS PUBLISHED ON THE NODE AND NOT ONLY THROWN, measured rather than assumed.
// evalGraph catches every exception out of `def.eval` and substitutes `newField()`
// (src/legacy.js:3467, `catch(err){console.error(...);f=newField();...}`; evalExact does the same
// at :3508). A typed error that is only ever THROWN therefore arrives at the graph as exactly the
// silent zero field this story exists to forbid. The refusal has to reach the caller as data, on
// the node, where the inspector already renders such things (src/legacy.js:4260 reads
// `_inputError`).
//
// WHY THAT ASSIGNMENT LIVES HERE IN core/ AND NOT IN THE PLUGIN FILES. Two reasons, one principled
// and one measured.
//
//   PRINCIPLED. "A required input must be connected" is a property of the PORT DECLARATION, not of
//   any one node's arithmetic. The right long-term home is the evaluator, which already knows which
//   slots have edges and already reads `required` off the descriptor; this module is the seam that
//   enforcement is lifted through when it moves there. Three copies of the same refusal pasted into
//   three plugin bodies would have to be un-pasted again.
//
//   MEASURED. `_verify_aux_registry.js` scans `\b(nd|node)\.(_[A-Za-z0-9]+)\s*=` over
//   src/plugins/**/*.js and requires the result to match SIDE_CHANNEL_LEDGER exactly, while
//   `ledgerHasNotGrown` caps that ledger at its current 25 rows. Those two together make it
//   structurally impossible for a PLUGIN FILE to publish anything on its node — including a
//   field-free diagnostic — because the ledger cannot absorb the row. src/legacy.js already writes
//   `water._inputError` (src/legacy.js:3362) with no ledger row, for exactly the same reason: the
//   scan's boundary is src/plugins, so core-owned node infrastructure has always sat outside it.
//   This is that same category — an error report, carrying no field and moving no data between
//   nodes — not a new side channel for semantic data.
import { AUX_MAPS } from './aux-maps.js'
import { SEMANTICS } from './ports.js'

/** The typed refusal code a disconnected required input raises. */
export const MISSING_REQUIRED_INPUT = 'MISSING_REQUIRED_INPUT'

/** The port id every cover-state selector uses, on both sides. */
export const STATE_PORT_ID = 'state'

/**
 * The cover stack, in the order the solid-stack identity states it:
 *   solidTop = bedrockHeight + soilDepth + sedimentDepth + sandDepth
 * `sandDepth` has no producer yet (S7.3 owns it) and a selector for it is still the right thing:
 * a state nobody can NAME cannot be wired, and the selector is what makes the port exist.
 */
export const COVER_STATES = Object.freeze(['soilDepth', 'sedimentDepth', 'sandDepth'])

const SELECTORS = Object.freeze({
  soilDepth: Object.freeze({
    type: 's_soilDepth', name: 'Soil depth',
    desc: 'Reads carried SOIL DEPTH state (metres) from its connected typed port and returns it '
      + 'unchanged. The input is required: a disconnected port is a typed missing-input error, '
      + 'never a field of zeros, because zero soil is bare bedrock and is real data.',
  }),
  sedimentDepth: Object.freeze({
    type: 's_sedimentDepth', name: 'Sediment depth',
    desc: 'Reads carried SEDIMENT DEPTH state (metres) from its connected typed port and returns '
      + 'it unchanged. This is deposited layer thickness, not the Deposits prediction — the input '
      + 'is required and a disconnected port is a typed missing-input error.',
  }),
  sandDepth: Object.freeze({
    type: 's_sandDepth', name: 'Sand depth',
    desc: 'Reads carried SAND DEPTH state (metres) from its connected typed port and returns it '
      + 'unchanged. No producer emits sand yet (S7.3 owns it), so today this port names the state '
      + 'rather than supplying it; a disconnected port is a typed missing-input error.',
  }),
})

/**
 * The typed port block for one cover-state selector.
 *
 * The semantic is the state's own (`soilDepth` / `sedimentDepth` / `sandDepth`), never
 * `anyScalarRaster`: a generic on a carried layer thickness is not a typed state port, it is the
 * absence of one, and it would accept any [0,1] mask and make the metre frame unverifiable at the
 * first hop. The three declarations below are cross-checked against the two registries that already
 * describe these fields, so a vocabulary edit that contradicts the port is a load-time throw rather
 * than a silently mistyped wire.
 */
export function coverSelectorPorts(mapId) {
  const sel = SELECTORS[mapId]
  if (!sel) throw new Error(`coverSelectorPorts: ${JSON.stringify(mapId)} is not a cover state`)
  const sem = SEMANTICS[mapId]
  if (!sem || sem.kind !== 'scalarRaster' || sem.defaultUnit !== 'm') {
    throw new Error(`coverSelectorPorts: SEMANTICS.${mapId} must be a scalarRaster in metres`)
  }
  const aux = AUX_MAPS[mapId]
  if (!aux || aux.lens !== 'state' || aux.unit !== 'm') {
    throw new Error(`coverSelectorPorts: AUX_MAPS.${mapId} must be the state lens in metres`)
  }
  const shape = { kind: 'scalarRaster', storage: 'R32F', components: 1, semantic: mapId, unit: 'm', lens: 'state' }
  return {
    inputs: [{ ...shape, id: STATE_PORT_ID, name: sel.name, role: 'data', required: true, legacySlot: 0 }],
    outputs: [{ ...shape, id: STATE_PORT_ID, name: sel.name, primary: true }],
  }
}

/**
 * Everything a cover-state selector plugin declares except its `eval`, which has to stay in the
 * plugin module because it reaches into the legacy field primitives at call time.
 *
 * `stateSelector` is the machine-readable claim "this node type selects <auxMapId>". The canonical
 * type ids (`s_soilDepth`, ...) say the same thing, and both are published deliberately: a reader
 * that resolves selectors by scanning the registry should not have to parse a name.
 */
export function coverSelector(mapId, expectedType) {
  const sel = SELECTORS[mapId]
  if (!sel) throw new Error(`coverSelector: ${JSON.stringify(mapId)} is not a cover state`)
  // The caller states the type id it believes it is registering, and this refuses a disagreement.
  // See the plugin modules for why the id is spelled there at all — it is not redundancy, it is
  // what keeps those files visible to the side-channel scan — and this check is what stops the two
  // spellings from ever drifting into a silent duplicate or a renamed node type.
  if (expectedType !== sel.type) {
    throw new Error(`coverSelector: ${mapId} registers as ${sel.type}, not ${JSON.stringify(expectedType)}`)
  }
  const { inputs, outputs } = coverSelectorPorts(mapId)
  return {
    type: sel.type,
    cat: 'surface',
    name: sel.name,
    stateSelector: mapId,
    ins: [sel.name],
    desc: sel.desc,
    params: [],
    inputs,
    outputs,
  }
}

/**
 * Publish a typed problem on the node so it survives the evaluator's catch-all and reaches both the
 * inspector and any caller that reads the node. Returns the problem, so a caller can put the same
 * object on its typed return without building it twice.
 */
export function publishNodeProblem(nd, problem) {
  if (nd && typeof nd === 'object') {
    nd._portProblem = problem
    nd._inputError = problem.message
  }
  return problem
}

/** Clear a previously published problem. Guarded, so it never invents the property on a clean node. */
export function clearNodeProblem(nd) {
  if (!nd || typeof nd !== 'object') return
  if (nd._portProblem) nd._portProblem = null
  if (nd._inputError) nd._inputError = null
}

/**
 * Read the required cover state off slot 0.
 *
 * CONNECTED  returns the input array ITSELF — identity, not approximation, not a copy. A selector
 *            that rebuilt the field would be indistinguishable from one that recomputed it.
 * ABSENT     returns a typed refusal `{ values, problems }` AND publishes it on the node. The
 *            `values` map still carries a blank field because the graph, the thumbnails and the
 *            viewport all expect a raster of the right length from every node; what makes that
 *            blank legal is that it is not silent — it arrives with a named problem attached, which
 *            is precisely the distinction between "bare bedrock" and "you did not wire this".
 *
 * `blank` is passed in rather than imported: newField() lives in the legacy cycle and this module
 * is outside it.
 */
export function selectCoverState(mapId, ins, nd, blank) {
  const sel = SELECTORS[mapId]
  if (!sel) throw new Error(`selectCoverState: ${JSON.stringify(mapId)} is not a cover state`)
  const value = ins && ins[0]
  if (value && ArrayBuffer.isView(value) && typeof value.length === 'number') {
    clearNodeProblem(nd)
    return value
  }
  const problem = {
    code: MISSING_REQUIRED_INPUT,
    port: STATE_PORT_ID,
    type: sel.type,
    message: `${sel.name}: the required "${sel.name}" input (port "${STATE_PORT_ID}") is not `
      + `connected. Wire a ${mapId} producer into it — a zero cover field means bare bedrock, so `
      + 'this node will not answer a missing wire with zeros.',
  }
  publishNodeProblem(nd, problem)
  return { values: new Map([[STATE_PORT_ID, blank()]]), problems: [problem] }
}

/**
 * Record which branch a prediction-with-override node took: `true` = it computed its prediction,
 * `false` = it returned the connected state byte-for-byte.
 *
 * "Never substituted silently" means the substitution is not silent — the node has to SAY. This is
 * the same node-report channel as the problem above and lives here for the same two reasons.
 */
export function reportPredictionBranch(nd, predicted) {
  const flag = predicted === true
  if (nd && typeof nd === 'object') nd._predicted = flag
  return flag
}
