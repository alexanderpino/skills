// Regolith — physical soil production as STATE, from the Heimsath et al. (1997) law. Story S3.2.
//
// WHAT THIS IS NOT. It is not the shipping `weathering` node. That one is `cat:"effect"`,
// `passthrough:true`, and its entire evaluator is `const h=ins[0]||newField(); ...; return h` —
// it ages COLOUR and passes height through untouched (src/plugins/effect/weathering.js). Nothing
// downstream can consume a thickness from it because it never produces one. Sprint 3 is explicit
// that a Gaea-shaped *derived* Soil node would make the app look like it has soil while the
// accounting stays discarded (Guardrail 4), so this node produces a real carried field instead.
//
// THE LAW, and why the update is the exact integral rather than an Euler step.
// Reference chapter 11 / Heimsath et al. 1997 give the soil-production function
//
//     P(H) = P0 * exp(-H / hStar)          [P0 in mm/yr, H and hStar in metres]
//
// so soil thickens according to dH/dt = c * P0m * exp(-H/hStar), with P0m = P0 * 1e-3 m/yr and c
// the optional dimensionless climate multiplier. That ODE separates, and integrating it over a
// duration t gives a closed form:
//
//     H(t) = hStar * ln( exp(H0/hStar) + c * P0m * t / hStar )
//
// Three properties come free from the closed form that a clamped `H0 + P(H0)*t` only pretends to
// have:
//   * it is unconditionally NON-NEGATIVE and monotone in t, because ln of something >= 1 is >= 0
//     whenever H0 >= 0 — the sprint's "the analytic update cannot produce negative depth" is a
//     property of the expression, not a max(0, ...) hiding an unstable step;
//   * it is unconditionally stable — a 100 kyr duration cannot overshoot;
//   * it is self-limiting at every depth, not just for small t: thick soil genuinely gains less.
//
// UNITS ARE THE WHOLE GAME HERE. P0 is authored in mm/yr because the cited range is 0.05-0.3 mm/yr
// and authoring it in m/yr would put every interesting value at 1e-4, where a typo is invisible.
// The OUTPUT is metres, because the solid stack (bedrockHeight + soilDepth + sedimentDepth +
// sandDepth) is in metres. That conversion is one `* 1e-3` and getting it wrong is a 1000x error
// that still looks like terrain, which is why _verify_soildepth.js checks the numbers against all
// three rival readings rather than reading the port's unit label.
//
// WHY THERE IS NO BEDROCK INPUT. The law is a function of soil THICKNESS only; it never reads an
// absolute elevation. ADR-005's height-frame question (viewport autolevel vs a stable measured
// datum) is unresolved, and taking an elevation in before that decision lands would bake the
// unresolved frame into a physical field. S3.3 adds the frame adapter; this node does not need it.
//
// NO SIDE CHANNELS. Everything this node computes leaves through its declared port. The aux-map
// debt ledger (src/core/aux-maps.js) may only ever shrink, so stashing a field on the node instance
// here would be a new ledger row and a failing gate — correctly.
//
// A MEASURED NOTE ON THAT GATE, because it cost a red run: _verify_aux_registry.js finds side
// channels with a REGEX over the raw source, comments included. The first draft of the paragraph
// above spelled the forbidden assignment out literally as an example, and the scan counted the
// prose as a 26th channel. The scan is doing its job — a comment-blind scan cannot be fooled by
// a channel hidden in a template string either — but do not write the pattern in a comment.
import { definePlugin } from '../../core/registry.js'
import { P } from '../../core/params.js'
import { newField } from '../../legacy.js'

// The CITED HARD RANGES — docs/plan/sprint-03-cover-layer.md:42-44, from reference chapter 11.
export const P0_LO_MM_PER_YR = 0.05
export const P0_HI_MM_PER_YR = 0.3
export const HSTAR_LO_M = 0.3
export const HSTAR_HI_M = 0.5

// THE INITIAL VALUES ARE DERIVED FROM THOSE RANGES, NOT PICKED. A default nobody can re-derive is
// a magic number, and this file is the place the derivation has to be legible.
//   P0 is a RATE, so its midpoint is GEOMETRIC: sqrt(0.05 * 0.3) = 0.12247448713915890 mm/yr.
//     (The arithmetic midpoint 0.175 would sit 43% above the geometric one and would quietly
//     assert that the range is linear when it spans a factor of six.)
//   hStar is a LENGTH, so its midpoint is ARITHMETIC: (0.3 + 0.5) / 2 = 0.4 m.
export const P0_INIT_MM_PER_YR = Math.sqrt(P0_LO_MM_PER_YR * P0_HI_MM_PER_YR)
export const HSTAR_INIT_M = (HSTAR_LO_M + HSTAR_HI_M) / 2

// Duration is REQUIRED AUTHORED DATA. These are the two ways it can be wrong, and they are
// distinct on purpose: "you never said" is an authoring gap the inspector must surface, while
// "you said -500" is a value that would run the law backwards into negative depth.
export const REGOLITH_DURATION_REQUIRED = 'REGOLITH_DURATION_REQUIRED'
export const REGOLITH_DURATION_INVALID = 'REGOLITH_DURATION_INVALID'
export const REGOLITH_PARAM_INVALID = 'REGOLITH_PARAM_INVALID'

const refuse = (code, message) => { const e = new Error(message); e.code = code; throw e }

/**
 * The duration, in years, or a typed refusal. There is NO `|| 1` here and there must never be:
 * a duration nobody stated is not a duration of one year, and an assumed 1 yr is indistinguishable
 * from a deliberate 1 yr in every downstream reading.
 */
export function requireDurationYears(value) {
  if (value === undefined || value === null || value === '') {
    refuse(REGOLITH_DURATION_REQUIRED,
      'Regolith: Duration (years) is required authored data and has no default — state how long the surface weathered.')
  }
  const years = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(years) || years < 0) {
    refuse(REGOLITH_DURATION_INVALID,
      `Regolith: Duration must be a finite, non-negative number of years; received ${JSON.stringify(value)}.`)
  }
  return years
}

/**
 * H(t) = hStar * ln( exp(H0/hStar) + c*P0*1e-3*t/hStar ) — metres.
 *
 * `* 1e-3` and not `/ 1000`: they differ by up to an ulp in double precision and the acceptance
 * oracle evaluates the same expression, so the two are written the same way deliberately.
 */
export const heimsathDepthM = (h0M, p0MmPerYr, hStarM, years, climate) => {
  const x = (climate * p0MmPerYr * 1e-3 * years) / hStarM
  return hStarM * Math.log(Math.exp(h0M / hStarM) + x)
}

export default definePlugin({
  type: 'regolith',
  cat: 'surface',
  name: 'Regolith',
  ins: ['Soil', 'Climate'],
  desc: 'PHYSICAL soil production (Heimsath 1997): P = P0·exp(−H/h*) integrated over an authored '
    + 'duration, emitting carried soil thickness in metres. Not a colour pass — for preview ageing '
    + 'use Weathering. Duration is required; there is no default.',

  // Declared ports. This plugin does NOT use the legacy adapter — ADR-002 forbids it for new nodes.
  inputs: [
    // Carried state, OPTIONAL: an absent connection means bare rock, H0 = 0, which is the correct
    // physical reading and not a silent zero fallback for a missing required field. The semantic is
    // strict (`soilDepth`/metres) rather than `anyScalarRaster`: a carried layer thickness that
    // accepted any old [0,1] mask would make the metre frame unverifiable at the first hop.
    { id: 'soilDepth', name: 'Soil', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'soilDepth', unit: 'm', role: 'data', required: false, lens: 'state', legacySlot: 0 },
    // OPTIONAL dimensionless multiplier on the production rate, never a hidden required model.
    // `anyMask` is exactly ports.js's definition of this shape — "any semantic, but unit must be
    // none, because every mask consumer multiplies the field as a dimensionless weight" — so a
    // degC or mm/yr field into this slot is refused while a plain driver is ordinary use.
    { id: 'climate', name: 'Climate', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'anyMask', unit: 'none', role: 'mask', required: false, legacySlot: 1 },
  ],
  outputs: [
    { id: 'soilDepth', name: 'Soil depth', kind: 'scalarRaster', storage: 'R32F', components: 1,
      semantic: 'soilDepth', unit: 'm', primary: true, lens: 'state' },
  ],

  params: [
    P.number('p0MmPerYr', 'Bare-rock production P0', P0_LO_MM_PER_YR, P0_HI_MM_PER_YR,
      P0_INIT_MM_PER_YR, 0.001, 'mm/yr'),
    P.number('hStarM', 'e-folding depth h*', HSTAR_LO_M, HSTAR_HI_M, HSTAR_INIT_M, 0.005, 'm'),
    // def is null, deliberately and permanently. The inspector renders an empty field and the node
    // refuses to evaluate until it is authored.
    P.number('durationYears', 'Duration', 0, 1e6, null, 1, 'yr'),
  ],

  eval: (p, ins) => {
    const years = requireDurationYears(p.durationYears)
    const p0 = Number(p.p0MmPerYr)
    const hStar = Number(p.hStarM)
    if (!Number.isFinite(p0) || p0 < 0) {
      refuse(REGOLITH_PARAM_INVALID, `Regolith: P0 must be a finite, non-negative rate in mm/yr; received ${JSON.stringify(p.p0MmPerYr)}.`)
    }
    if (!Number.isFinite(hStar) || hStar <= 0) {
      refuse(REGOLITH_PARAM_INVALID, `Regolith: h* must be a finite, positive depth in metres; received ${JSON.stringify(p.hStarM)}.`)
    }

    const out = newField()
    const n = out.length
    // A field of the wrong length is a real defect (a stale raster from another resolution), and
    // reading it partially would produce a plausible-looking depth over part of the domain. Say so.
    const soil = ins[0] || null
    const climate = ins[1] || null
    if (soil && soil.length !== n) {
      refuse(REGOLITH_PARAM_INVALID, `Regolith: the Soil input is ${soil.length} samples but the field is ${n}.`)
    }
    if (climate && climate.length !== n) {
      refuse(REGOLITH_PARAM_INVALID, `Regolith: the Climate input is ${climate.length} samples but the field is ${n}.`)
    }

    // Written per-sample rather than hoisting `x`, because `c` is per-sample when a climate field is
    // connected. With no field, `c` is exactly 1 and `c * p0` is exact, so a connected uniform
    // multiplier of 1 is bit-identical to no connection at all — which is what makes "optional"
    // mean optional rather than "a slightly different code path".
    for (let i = 0; i < n; i++) {
      const h0 = soil ? soil[i] : 0
      const c = climate ? climate[i] : 1
      const x = (c * p0 * 1e-3 * years) / hStar
      out[i] = hStar * Math.log(Math.exp(h0 / hStar) + x)
    }
    return out
  },
})
