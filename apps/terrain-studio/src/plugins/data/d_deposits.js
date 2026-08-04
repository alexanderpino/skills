// d_deposits — a PREDICTION of where loose material would pile up, with an explicit state override.
//
// WHAT IT IS, said plainly because the whole of S3.4 turns on it. This node does not know where any
// sediment is. It computes a grey morphological CLOSING of the surface and returns the depth of the
// hollows that closing filled, scaled against `refDepth` — a shape statistic of the current
// geometry, recomputed from scratch on every evaluation. It is a `DERIVED_PRODUCER`
// (src/core/doctrine.js:34) and it stays one. Carried cover depth is a different kind of thing: it
// is path-dependent state, it persists between passes, and it comes out of a transport solver.
//
// So the fallback is EXPLICIT, not silent. Wire the optional `Sediment state` port and this node
// returns that field byte-for-byte; leave it unwired and it computes the prediction. Which of the
// two ran is reported through `reportPredictionBranch`, because "never substituted silently" means
// the substitution is not silent — the node has to say which answer the caller got. The registry
// entry carries `prediction: true` and says "PREDICTION" in the description the inspector renders,
// so the label survives a reader that never evaluates the node at all.
//
// The legacy import is CALL-TIME only: these names are used inside `eval`, which does not run
// until the graph is evaluated, so the legacy<->plugin cycle is safe. Anything needed at
// module-evaluation time (the params array) comes from core/params.js, outside the cycle.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { reportPredictionBranch } from '../../core/cover-state.js'
import { depositsField, newField, resScale } from '../../legacy.js'

export default definePlugin({
  type: "d_deposits",
  cat: "data", name: "Deposits", ins: ["In", "Sediment state"],
  // The machine-readable half of the label. The mutation `deposits-not-labelled-prediction` strips
  // BOTH this flag and the word out of the prose, so neither channel alone can carry the claim.
  prediction: true,
  desc: "PREDICTION, not carried state: the depth loose material would pile into hollows "
    + "(morphological closing − surface). Wire Sediment state to return a real carried "
    + "sedimentDepth field instead — the node reports which of the two it used.",
  // refDepth is what keeps the mask PHYSICAL: the fill depth (metres) that saturates it.
  // The old normalize() output was identical for a terrain at any amplitude.
  params: [P.int("radius", "Radius", 1, 10, 3),
    P.slider("refDepth", "Full-mask depth", 5, 120, 25, 1, v => (v | 0) + " m")],
  // The typed ports for BOTH slots are declared in src/core/legacy-ports.js rather than here, and
  // that placement is deliberate. `_verify_port_contract.js:rosterFullyAdapted` asserts every one
  // of the 79 rostered types is served by the legacy adapter, and a type that declares its own
  // `inputs` opts out of the adapter (src/core/registry.js:98) — so declaring them here would drop
  // that count to 78 and, separately, drift `ins` away from the frozen LEGACY_INS_LABELS anchor.
  eval: (p, ins, nd) => {
    // The EXPLICIT override. Identity, not approximation: the exact bytes that arrived.
    const state = ins && ins[1]
    if (state && ArrayBuffer.isView(state)) {
      reportPredictionBranch(nd, false)
      return state
    }
    reportPredictionBranch(nd, true)
    return ins[0] ? depositsField(ins[0], {
      radius: Math.max(1, Math.round(p.radius * resScale())),
      refDepth: p.refDepth == null ? 25 : p.refDepth,
    }) : newField()
  },
})
