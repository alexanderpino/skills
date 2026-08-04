// Soil depth selector — story S3.4. Reads carried `soilDepth` state off a connected typed port.
//
// The whole contract lives in src/core/cover-state.js, because it is one contract with three
// instances and not three node implementations: the port block, the identity return, and the typed
// missing-input refusal are identical for soil, sediment and sand. What stays here is the one thing
// that cannot move — `newField` is a legacy binding, so it may only be read at CALL time, inside
// this closure. Reading it at module-evaluation time is the TDZ failure `npm run plugins:tdz` gates.
import { definePlugin } from '../../core/registry.js'
import { coverSelector, selectCoverState } from '../../core/cover-state.js'
import { newField } from '../../legacy.js'

// THE TYPE ID IS SPELLED LITERALLY BELOW AND THAT IS DELIBERATE, not leftover duplication.
// _verify_aux_registry.js's side-channel scan reads each plugin file's raw source, takes the node
// type from the first literal type key it finds, and SKIPS the file entirely when there is none
// (tests/legacy/_verify_aux_registry.js:41-42). A plugin whose manifest comes out of a factory has
// no such literal, so it would drop silently out of the one gate that keeps the debt ledger honest
// — a file nothing scans is a file anything can be hidden in. coverSelector() throws if the two
// spellings ever disagree, so this cannot drift.
export default definePlugin({
  ...coverSelector('soilDepth', 's_soilDepth'),
  type: 's_soilDepth',
  eval: (p, ins, nd) => selectCoverState('soilDepth', ins, nd, newField),
})
