// Sediment depth selector — story S3.4. Reads carried `sedimentDepth` state off a connected typed
// port. See s_soildepth.js for why the contract lives in src/core/cover-state.js.
//
// NOT the same field as the Deposits node. `d_deposits` computes a morphological PREDICTION of
// where loose material would collect; this returns the thickness that a transport pass actually
// deposited and carried forward. ports.js keeps them as separate semantics (`sediment` is a
// transport quantity, `sedimentDepth` is a layer thickness) so the two can never be wired
// interchangeably.
import { definePlugin } from '../../core/registry.js'
import { coverSelector, selectCoverState } from '../../core/cover-state.js'
import { newField } from '../../legacy.js'

// The literal id below is what keeps this file visible to the side-channel scan — see
// s_soildepth.js for the measurement.
export default definePlugin({
  ...coverSelector('sedimentDepth', 's_sedimentDepth'),
  type: 's_sedimentDepth',
  eval: (p, ins, nd) => selectCoverState('sedimentDepth', ins, nd, newField),
})
