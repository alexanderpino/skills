// Water regimes — S4.9. Which body is this sample, and what is its surface doing?
//
// Pure and DOM-free, like hydrology.js and water-waves.js: it never imports legacy.js, so an oracle
// can evaluate it under plain node in double precision with no browser. It DOES import
// water-waves.js, deliberately — the shoaling law and the fold detector live there and there must be
// one copy of each, not a second one here that drifts.
//
// WHY THIS EXISTS. The renderer currently has one water surface and one wave preset. Every body gets
// the same swell, foam is whatever a noise function produced, and a frozen lake still ripples,
// because nothing in the pipeline ever says WHAT a given wet sample is. The story's failure list is
// exactly that: "ocean waves on rivers", "random foam", ice that does not suppress motion.
//
// THE PARTITION IS THE CONTRACT. Every wet sample lands in exactly one regime and every regime is
// reachable. That is a property an oracle can assert and a broken classifier violates immediately —
// the classic way to get this wrong is five independent `if` tests in a shader, where a shallow
// river cell is both "shore" and "river" and gets shaded twice.
//
// WHAT DECIDES EACH REGIME, and every one of them is a physical criterion rather than a look-up:
//
//   ICE     the phase transition has completed. Continuous in temperature, exactly 1 below the
//           solid point, and it suppresses liquid motion to exactly zero there.
//   FOAM    the flow is supercritical. Froude number >= 1 is the DEFINITION of critical flow, not a
//           tuned constant: past it a hydraulic jump forms and the surface is aerated whitewater.
//   RIVER   discharge reaches the authored channel-forming value, i.e. the water is going somewhere.
//   SHORE   the bottom is felt. Same criterion as `shoalAmplitude`'s deep-water reference — half the
//           longest wavelength — so the shore band and the shoaling band are ONE definition.
//   LAKE    wet, standing, and deep enough that the bottom is not felt.
//
// Precedence runs in that order and the numeric codes are in that order too, so "the first matching
// regime wins" and "the lowest code wins" are the same statement.
import { GRAVITY, SHOAL_BREAK_RATIO, shoalAmplitude } from './water-waves.js'

export const WATER_REGIME_VERSION = 1

/** DRY is deliberately outside [0, REGIME_COUNT): it is the absence of a regime, not one of them. */
export const REGIME = Object.freeze({ DRY: -1, ICE: 0, FOAM: 1, RIVER: 2, SHORE: 3, LAKE: 4 })
export const REGIME_NAMES = Object.freeze(['ice', 'foam', 'river', 'shore', 'lake'])
export const REGIME_COUNT = REGIME_NAMES.length

const clamp01 = v => (v <= 0 ? 0 : v >= 1 ? 1 : v)
/** Cubic smoothstep on an already-normalised argument. C1 at both ends, exactly 0 and exactly 1. */
const smooth01 = u => (u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u))
/** Read a field that may be a raster, a scalar, or absent. */
const at = (f, i, dflt = 0) => (f == null ? dflt : (typeof f === 'number' ? f : f[i]))

// --- phase transition ---------------------------------------------------------------------------

// Fresh water freezes at 0 °C, so the ONSET is physics. The width is authored: a surface at exactly
// 0 °C is slush, and full cover needs sustained sub-zero, so the transition is spread over four
// degrees rather than switched. A binary threshold is what makes a lake snap from open water to
// mirror between two adjacent frames of a temperature animation.
export const ICE_ONSET_C = 0
export const ICE_SOLID_C = -4

/**
 * Fraction of the surface that has frozen. 0 at and above the onset, exactly 1 at and below the
 * solid point, smooth between.
 *
 * Smoothstep rather than a linear ramp because the derivative matters at the ENDS: a linear ramp
 * has a slope discontinuity exactly where a temperature field crosses the threshold, and that reads
 * as a hard line across the ice edge in the very place the transition is supposed to be invisible.
 */
export function iceFraction(temperatureC, { iceOnsetC = ICE_ONSET_C, iceSolidC = ICE_SOLID_C } = {}) {
  if (!Number.isFinite(temperatureC)) return 0
  // A degenerate authored range (solid at or above onset) has no interval to interpolate over.
  // Falling back to a step here is not a hidden default: it is the only meaning the numbers carry.
  if (!(iceSolidC < iceOnsetC)) return temperatureC <= iceOnsetC ? 1 : 0
  return smooth01((iceOnsetC - temperatureC) / (iceOnsetC - iceSolidC))
}

// --- open-channel flow --------------------------------------------------------------------------

// Chow (1959) table 5-6, "natural stream, clean and winding with some pools and stones": n = 0.033
// to 0.040. 0.035 sits in that band. It is authored, visible, and the one number a user tunes when
// their rivers look too fast.
export const MANNING_N_DEFAULT = 0.035

/**
 * Depth-averaged flow speed from Manning's equation, in m/s.
 *
 * v = (1/n) R^(2/3) S^(1/2), with the hydraulic radius R taken as the DEPTH. That substitution is
 * the standard wide-channel approximation and it is exact in the limit width >> depth, which is the
 * case for every channel a terrain lattice can resolve: a 10 m cell cannot hold a gorge narrower
 * than it is deep.
 *
 * `constriction` is the width ratio referenceWidth/localWidth. Continuity says Q = w*d*v, so at
 * fixed Q and d, halving the width doubles the speed — the constriction multiplies v directly. This
 * is the term that makes a narrows foam and a pool not.
 *
 * Zero gradient gives EXACTLY zero speed, and zero depth gives exactly zero speed. Standing water
 * does not move, and that has to be exact rather than small: "no rapids on a lake" is a claim about
 * zero, and a lake surface creeping at 1e-9 m/s would advect the river detail bands across it.
 */
export function manningVelocity(depthM, slope, { manningN = MANNING_N_DEFAULT, constriction = 1 } = {}) {
  if (!(depthM > 0) || !(slope > 0)) return 0
  const n = Math.max(manningN, 1e-6)
  const c = Math.max(constriction, 0)
  return (Math.pow(depthM, 2 / 3) * Math.sqrt(slope) / n) * c
}

/**
 * Froude number: inertia over gravity wave speed, Fr = v / sqrt(g d).
 *
 * This is the quantity that decides what a water surface LOOKS like, and it is dimensionless, so it
 * needs no calibration. Below 1 the flow is subcritical and disturbances travel upstream — a smooth
 * river. At 1 it is critical. Above 1 it is supercritical, upstream information is cut off, and the
 * return to subcritical happens through a hydraulic jump, which is a standing wall of aerated water.
 * Whitewater is not a rendering style; it is Fr crossing 1.
 */
export function froudeNumber(speedMps, depthM) {
  if (!(depthM > 0) || !(speedMps > 0)) return 0
  return speedMps / Math.sqrt(GRAVITY * depthM)
}

// --- foam, from three named causes ----------------------------------------------------------------

// Surface disturbance becomes visible well before the jump itself, so the ramp opens at 0.6 (an
// authored onset) and saturates at 1.0 (critical flow, which is not authored — it is the definition).
export const FOAM_FROUDE_ONSET = 0.6
export const FOAM_FROUDE_FULL = 1.0
// Above this the surface is aerated rather than open water, so the sample is a FOAM sample rather
// than a river sample carrying some foam. Authored: it is where the render swaps material, not a
// physical boundary.
export const FOAM_REGIME_MIN = 0.5
// The horizontal Jacobian is 1 on flat water and falls toward 0 as a Gerstner crest compresses.
// Air entrainment starts when the surface has been squeezed to about half its rest area.
export const CREST_JACOBIAN_ONSET = 0.5

/** Whitewater from supercritical flow. EXACTLY zero at or below the onset, so still water is still. */
export function rapidFoam(froude, { foamFroudeOnset = FOAM_FROUDE_ONSET, foamFroudeFull = FOAM_FROUDE_FULL } = {}) {
  if (!(froude > foamFroudeOnset)) return 0
  return smooth01((froude - foamFroudeOnset) / Math.max(foamFroudeFull - foamFroudeOnset, 1e-9))
}

/**
 * Breaking surf, expressed as how close the wave is to its own breaking limit.
 *
 * `shoalAmplitude` already clamps amplitude to SHOAL_BREAK_RATIO * depth, so the ratio of the
 * shoaled amplitude to that limit is 1 exactly in the band where the wave is breaking and less than
 * 1 everywhere else. Reading the foam off the existing law rather than adding a second shore
 * function is the point: there is one place that decides where surf is, and both the amplitude and
 * the foam come out of it.
 *
 * It falls back to zero at the waterline because the law's dry taper does — surf rears up, breaks,
 * and runs out. And it is exactly zero on dry ground.
 */
export function shoreFoam(ampM, depthM, refM) {
  if (!(depthM > 0) || !(ampM > 0)) return 0
  const a = shoalAmplitude(ampM, depthM, refM)
  if (!(a > 0)) return 0
  return clamp01(a / (SHOAL_BREAK_RATIO * depthM))
}

/**
 * Crest foam from the horizontal Jacobian of the Gerstner map — the SAME fold detector ADR-006
 * already gates the preset with. Where the map compresses, neighbouring water converges and air is
 * entrained; that is a cause, computed from the wave the renderer actually drew.
 */
export function crestFoam(jacobian, { crestJacobianOnset = CREST_JACOBIAN_ONSET } = {}) {
  const onset = Math.max(crestJacobianOnset, 1e-9)
  if (!(jacobian < onset)) return 0
  return smooth01((onset - jacobian) / onset)
}

/**
 * The combined foam intensity at one sample.
 *
 * MAX, not sum: the three causes are alternatives, not contributions. A rapid under a breaking wave
 * is not twice as white as either. Taking the max also keeps the result in [0,1] without a clamp
 * that would silently hide a cause that had gone out of range.
 *
 * Ice suppresses foam by the same factor it suppresses displacement, so a frozen rapid is exactly as
 * still as a frozen lake.
 */
export function foamIntensity({ froude = 0, ampM = 0, depthM = 0, refM = 0, jacobian = 1, ice = 0 } = {}, opts = {}) {
  if (!(depthM > 0)) return 0
  const f = Math.max(rapidFoam(froude, opts), shoreFoam(ampM, depthM, refM), crestFoam(jacobian, opts))
  return f * (1 - clamp01(ice))
}

// --- how much the liquid surface moves ------------------------------------------------------------

/**
 * Fetch per body kind, in metres.
 *
 * Sverdrup-Munk-Bretschneider / JONSWAP fetch-limited growth: at a fixed wind, significant wave
 * height rises as the SQUARE ROOT of fetch. That single law is what makes a lake restrained and a
 * river flat without anybody authoring three amplitude sliders — a 2 km lake carries sqrt(2e3/5e5)
 * = 0.063 of an open-ocean sea, which is why lakes chop and do not swell.
 *
 * A river's fetch is ZERO on purpose. It is not "very small": the story's armed failure is ocean
 * Gerstner displacement appearing on rivers, and the only value that makes that structurally
 * impossible is exact zero. River surface motion is advection of the detail bands, below.
 */
export const BODY_FETCH_M = Object.freeze({ ocean: 5e5, lake: 2e3, river: 0 })

/** Amplitude scale relative to the reference body, from the sqrt(fetch) law. */
export function fetchAmplitudeScale(bodyKind, { referenceKind = 'ocean', fetchM = null } = {}) {
  const f = fetchM != null ? Number(fetchM) : (BODY_FETCH_M[bodyKind] != null ? BODY_FETCH_M[bodyKind] : 0)
  const ref = BODY_FETCH_M[referenceKind] || 1
  if (!(f > 0)) return 0
  return Math.sqrt(f / ref)
}

/**
 * Ambient wave amplitude actually applied at one sample, in metres.
 *
 * Three multiplications, and each one is a separate exactness claim the gate checks:
 *   fetch scale   ocean > lake > river, and river is exactly 0
 *   shoaling      grows into shallow water, breaks, and is exactly 0 on dry ground
 *   ice           continuous in the phase fraction and exactly 0 at full ice
 */
export function regimeAmplitude(bodyKind, ampM, depthM, refM, ice = 0, opts = {}) {
  const s = fetchAmplitudeScale(bodyKind, opts)
  if (!(s > 0)) return 0
  return shoalAmplitude(ampM * s, depthM, refM) * (1 - clamp01(ice))
}

// --- river surface: advected detail bands ---------------------------------------------------------

/**
 * Two detail bands, phase-offset along the flow so their crests never coincide.
 *
 * `scale` is the band's spatial frequency multiplier and `offsetM` shifts it upstream. The offset is
 * not a multiple of any band wavelength, so the pair never re-synchronises into one pattern — the
 * same argument water-waves.js makes for keeping the twelve Gerstner wavelengths non-harmonic.
 */
export const RIVER_DETAIL_BANDS = Object.freeze([
  Object.freeze({ scale: 1.0, offsetM: 0 }),
  Object.freeze({ scale: 0.43, offsetM: 3.7 }),
])

/**
 * Where to sample a river detail band at time `t`, in metres.
 *
 * The pattern is carried BY the flow, so the sample point moves upstream at the physical flow speed:
 * p - u*(v*t). Two consequences the gate asserts exactly, because both are things a hand-written
 * shader gets wrong:
 *
 *   * reversing the flow field reverses the travel, exactly. Advecting by |v| along a fixed axis
 *     looks identical on a straight reach and sends the whole river backwards on the return bend.
 *   * zero speed is a static pattern, exactly. Not "slow" — a river with no discharge must not crawl.
 */
export function riverAdvect(px, pz, tSeconds, flowX, flowZ, speedMps, bandIndex = 0) {
  const band = RIVER_DETAIL_BANDS[bandIndex] || RIVER_DETAIL_BANDS[0]
  const len = Math.hypot(flowX, flowZ)
  const ux = len > 0 ? flowX / len : 0
  const uz = len > 0 ? flowZ / len : 0
  const travel = speedMps * tSeconds + band.offsetM
  return { u: (px - ux * travel) * band.scale, v: (pz - uz * travel) * band.scale }
}

// Below this Froude number the surface is glass; above FOAM_FROUDE_ONSET it is breaking up. Between
// them it is a rippled but coherent surface. Authored, and the three weights are what the shader
// cross-fades — they are NOT the regime partition, which is per-cell and integral.
export const RIPPLE_FROUDE_ONSET = 0.15

/**
 * Calm / ripple / turbulent blend weights for a river surface, as a partition of unity.
 *
 * `calm` is computed as the remainder rather than as its own ramp, so the three cannot drift out of
 * sum together — a blend whose weights total 1.06 brightens the water for no reason anybody can find.
 */
export function riverSurfaceWeights(froude, opts = {}) {
  const rippleOnset = opts.rippleFroudeOnset != null ? opts.rippleFroudeOnset : RIPPLE_FROUDE_ONSET
  const foamOnset = opts.foamFroudeOnset != null ? opts.foamFroudeOnset : FOAM_FROUDE_ONSET
  const turbulent = rapidFoam(froude, opts)
  const rise = smooth01((froude - rippleOnset) / Math.max(foamOnset - rippleOnset, 1e-9))
  const ripple = rise * (1 - turbulent)
  return { calm: 1 - (turbulent + ripple), ripple, turbulent }
}

// --- the classifier -------------------------------------------------------------------------------

// Authored default: below this discharge there is no persistent channel at terrain resolution, only
// sheet flow that a rain event erases. The plan calls the same quantity "channel-forming/bankfull Q"
// and hands it to Leopold-Maddock for width and depth; this is the same number used as a threshold.
export const CHANNEL_FORMING_Q_M3S = 0.1
// Fallback when the caller states neither a shore depth nor a deep-water reference.
export const SHORE_DEPTH_DEFAULT_M = 8

/**
 * The depth below which the bottom is felt.
 *
 * Defaults to the wave preset's deep-water reference — half the longest wavelength — because that is
 * already the definition `shoalAmplitude` uses to decide where shoaling starts. Two definitions of
 * "shallow" in one water system is how the foam ends up in a different place from the surf.
 */
export function shoreDepth(opts = {}) {
  if (opts.shoreDepthM != null) return Math.max(0, Number(opts.shoreDepthM))
  if (opts.refM != null) return Math.max(0, Number(opts.refM))
  return SHORE_DEPTH_DEFAULT_M
}

/** The authored channel-forming discharge. */
export function channelFormingQ(opts = {}) {
  return opts.channelFormingQM3S != null ? Math.max(0, Number(opts.channelFormingQM3S)) : CHANNEL_FORMING_Q_M3S
}

/**
 * Classify ONE sample and return everything derived on the way.
 *
 * The intermediate quantities come back rather than being thrown away because they are what the
 * renderer needs next — speed drives advection, the Froude number drives the surface blend, the ice
 * fraction drives suppression — and because a quantity worth computing is worth asserting.
 *
 * The chain is a single ordered `if` cascade with ONE return per branch. That shape is the exclusivity
 * guarantee: there is no arrangement of inputs that reaches two branches.
 */
export function classifyCell(sample = {}, opts = {}) {
  const depthM = Number(sample.depthM) || 0
  const out = {
    regime: REGIME.DRY, ice: 0, speedMps: 0, froude: 0, foam: 0, depthM,
  }
  if (!(depthM > 0)) return out

  out.ice = iceFraction(sample.temperatureC != null ? Number(sample.temperatureC) : 20, opts)
  out.speedMps = manningVelocity(depthM, Number(sample.slope) || 0, {
    manningN: opts.manningN,
    constriction: sample.constriction != null ? Number(sample.constriction) : 1,
  })
  out.froude = froudeNumber(out.speedMps, depthM)
  out.foam = foamIntensity({
    froude: out.froude,
    ampM: opts.ampM != null ? Number(opts.ampM) : 0,
    depthM,
    refM: opts.refM != null ? Number(opts.refM) : SHORE_DEPTH_DEFAULT_M,
    jacobian: sample.jacobian != null ? Number(sample.jacobian) : 1,
    ice: out.ice,
  }, opts)

  // ICE FIRST. A frozen surface is a solid, and nothing about the liquid underneath decides what is
  // drawn. Only FULL cover claims the regime: a partly frozen lake is still a lake whose motion is
  // damped, which is what makes the transition continuous instead of a snap at one isotherm.
  if (out.ice >= 1) { out.regime = REGIME.ICE; return out }

  // AERATED SURFACE next, and it is the RAPID cause alone rather than the combined intensity. Surf
  // on a beach is a shore sample with foam on it; a hydraulic jump is a different body state, and
  // conflating them would swallow the entire shore band into a foam regime.
  if (rapidFoam(out.froude, opts) >= FOAM_REGIME_MIN) { out.regime = REGIME.FOAM; return out }

  if ((Number(sample.dischargeM3S) || 0) >= channelFormingQ(opts)) { out.regime = REGIME.RIVER; return out }
  if (depthM < shoreDepth(opts)) { out.regime = REGIME.SHORE; return out }
  out.regime = REGIME.LAKE
  return out
}

/**
 * Classify a whole field.
 *
 * `fields` members may each be a raster, a single number, or absent — a uniform temperature is a
 * legitimate authored input and forcing the caller to allocate N copies of it is waste.
 *
 * `counts` is returned because absence of evidence is a failure: a fixture that produced no river
 * cells has proved nothing about rivers, and the count is how the oracle notices.
 */
export function classifyRegimes(fields = {}, N = 0, opts = {}) {
  const regime = new Int32Array(N)
  const foam = new Float64Array(N)
  const ice = new Float64Array(N)
  const speed = new Float64Array(N)
  const froude = new Float64Array(N)
  const counts = { dry: 0, ice: 0, foam: 0, river: 0, shore: 0, lake: 0 }
  let wet = 0
  for (let i = 0; i < N; i++) {
    const r = classifyCell({
      depthM: at(fields.depthM, i, 0),
      dischargeM3S: at(fields.dischargeM3S, i, 0),
      temperatureC: at(fields.temperatureC, i, 20),
      slope: at(fields.slope, i, 0),
      constriction: at(fields.constriction, i, 1),
      jacobian: at(fields.jacobian, i, 1),
    }, opts)
    regime[i] = r.regime
    foam[i] = r.foam
    ice[i] = r.ice
    speed[i] = r.speedMps
    froude[i] = r.froude
    if (r.regime === REGIME.DRY) counts.dry++
    else { counts[REGIME_NAMES[r.regime]]++; wet++ }
  }
  return { regime, foam, ice, speed, froude, counts, wet, N }
}

/**
 * One indicator mask per regime.
 *
 * ONE-HOT FROM THE CODE, never five independent predicates. Five independent tests is how this is
 * normally written in a shader and it is precisely how a shallow, fast, cold cell ends up shaded as
 * shore AND river AND ice at once. Deriving the masks from the single classification makes the
 * partition property structural rather than something the author has to remember.
 */
export function regimeMasks(fields = {}, N = 0, opts = {}) {
  const classified = classifyRegimes(fields, N, opts)
  const masks = {}
  for (const name of REGIME_NAMES) masks[name] = new Float64Array(N)
  for (let i = 0; i < N; i++) {
    const r = classified.regime[i]
    if (r >= 0 && r < REGIME_COUNT) masks[REGIME_NAMES[r]][i] = 1
  }
  masks.classified = classified
  return masks
}
