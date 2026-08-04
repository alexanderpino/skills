// Sand depth selector — story S3.4. Reads carried `sandDepth` state off a connected typed port.
// See s_soildepth.js for why the contract lives in src/core/cover-state.js.
//
// NOTHING PRODUCES SAND YET, and the selector is still the right thing to ship. S7.3 owns the
// producer; until it lands this node's required port is the only place `sandDepth` exists as a real
// typed port rather than a row in a plan. A state that cannot be named cannot be wired, and the
// solid-stack identity S3.3 has to close — solidTop = bedrockHeight + soilDepth + sedimentDepth +
// sandDepth — needs all four terms nameable even while one of them is uniformly zero.
import { definePlugin } from '../../core/registry.js'
import { coverSelector, selectCoverState } from '../../core/cover-state.js'
import { newField } from '../../legacy.js'

// The literal id below is what keeps this file visible to the side-channel scan — see
// s_soildepth.js for the measurement.
export default definePlugin({
  ...coverSelector('sandDepth', 's_sandDepth'),
  type: 's_sandDepth',
  eval: (p, ins, nd) => selectCoverState('sandDepth', ins, nd, newField),
})
