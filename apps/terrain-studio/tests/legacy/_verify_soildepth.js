// S3.2 — the regolith producer: `soilDepth` state, in metres, from the Heimsath law.
//
// RED-FIRST, ON PURPOSE. Sprint 3's Ready condition (docs/plan/sprint-03-cover-layer.md:84-85)
// requires the Heimsath analytic fixture to be OBSERVED RED before the producer exists. A gate
// first seen green is a gate that has never been seen to fail, and this project has found seven of
// those. So this file must fail TODAY — but it must fail by a NAMED GATE, printing its whole gate
// table, never by throwing. Every access to something that does not exist yet is guarded and every
// eval is wrapped, so an absent producer reads as `failed=[producerRegistered,...]` rather than as
// a ReferenceError, which would prove only that the test is broken.
//
// WHAT IS PINNED HERE, and why it is pinned rather than discovered.
// An acceptance gate written before the implementation has to state the contract, or it is
// unimplementable. This one states it in CONTRACT below and then measures production against a
// DOUBLE-PRECISION evaluation of the same law computed in this file — never against whatever
// production returns.
//
// THE LAW. Reference chapter 11 / Heimsath et al. 1997 gives the soil-production function
//
//     P(H) = P0 * exp(-H / hStar)                       [P0 in mm/yr, H and hStar in metres]
//
// and the sprint locks P0 = sqrt(0.05*0.3) = 0.122474... mm/yr (geometric midpoint of the cited
// 0.05-0.3 range, because it is a rate) and hStar = 0.4 m (arithmetic midpoint of 0.3-0.5).
//
// The update over a duration is the EXACT INTEGRAL of that ODE, not an Euler step:
//
//     dH/dt = c * P0m * exp(-H/hStar)   =>   H(t) = hStar * ln( exp(H0/hStar) + c*P0m*t/hStar )
//
// with P0m = P0 * 1e-3 (metres per year) and c the optional dimensionless climate multiplier.
// Three reasons this and not `H0 + P(H0)*t`:
//   * it is unconditionally non-negative and monotone in t, so "the analytic update cannot produce
//     negative depth" (sprint line 46) is a property of the closed form rather than a clamp;
//   * it is unconditionally stable — a 10 kyr duration cannot overshoot the way an Euler step can;
//   * it separates the `constant-production-rate` mutation AT H = 0 as well as at depth. Under
//     Euler the two agree exactly at H = 0 and the named mutation would survive a third of the
//     fixture. Under the integral, H(0) = 0.1068 m against a constant rate's 0.1225 m.
//
// THE UNIT TRAP, asserted by NUMBERS and not by a label. A millimetre/metre confusion is a 1000x
// error that still looks like terrain. So the oracle computes all three rival readings —
// metres-from-mm/yr (correct), the same value left in millimetres, and P0 mistaken for m/yr — and
// requires production to match the first and to MISS the other two. A gate that only read
// `port.unit === 'm'` would pass on every one of them.
//
// WHAT THIS DELIBERATELY DOES NOT TOUCH. soilDepth is its own field in metres. It does not depend
// on the unresolved height-frame question (autolevel vs stable datum, ADR-005), so nothing here
// reads bedrock elevation, and the "no eligible substrate" zero-control named at sprint line 131 is
// replaced by two controls that need no bedrock: zero duration, and a zero climate multiplier.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'constant-production-rate',    // the depth-dependence is dropped: P = P0, no exp term
  'zero-duration-nonzero-soil',  // the named defect: `durationYears || 1`, so 0 and missing both become 1 yr
  'depth-in-millimetres',        // the 1000x unit error that still looks like terrain
  'climate-modulation-required', // the optional dimensionless multiplier becomes a mandatory model
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// ------------------------------------------------------------------------------------------------
// THE CONTRACT S3.2 MUST SATISFY — stated here because an acceptance gate written before the code
// has to be implementable. Discovery is by PORT SEMANTIC first (`outputs[].semantic === 'soilDepth'`),
// so the node's type string is the implementer's choice; the candidate ids below are only a fallback.
// ------------------------------------------------------------------------------------------------
const CONTRACT = {
  candidateTypes: ['regolith', 'soilproduction', 'regolithproduction', 'soilproduce'],
  outputPortId: 'soilDepth',       // scalarRaster, unit 'm', lens 'state', semantic 'soilDepth'
  soilInputId: 'soilDepth',        // optional carried state; absent means H0 = 0
  climateInputId: 'climate',       // OPTIONAL dimensionless multiplier, unit 'none', required falsy
  missingDurationCode: 'REGOLITH_DURATION_REQUIRED',
  badDurationCode: 'REGOLITH_DURATION_INVALID',
}

// The locked constants, from docs/plan/sprint-03-cover-layer.md:42-44.
const P0_LO = 0.05, P0_HI = 0.3          // mm/yr, the cited hard range
const HSTAR_LO = 0.3, HSTAR_HI = 0.5     // m, the cited hard range
const P0_INIT = Math.sqrt(P0_LO * P0_HI) // 0.12247448713915890 mm/yr — geometric midpoint of a rate
const HSTAR_INIT = (HSTAR_LO + HSTAR_HI) / 2   // 0.4 m — arithmetic midpoint of a length
const YEARS = 1000                       // the authored duration for the main fixture

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(([mutation, CONTRACT, K]) => {
    USE_GPU = false
    terrainDef.lattice = 'square'
    terrainDef.scale = 5000              // the 5 km measured fixture (sprint line 133)
    const out = { mutation: mutation || null }

    // ---------- the double-precision oracle: nothing below reads production for its answer -------
    // gamma_n = (n * 2^-24) / (1 - n * 2^-24) — the standard Float32 forward-error factor. Eight
    // terms, as ADR-002's reduction bound and sprint line 135 both use. NOT a chosen tolerance:
    // change the operation count and the bound moves with it.
    const gamma = n => (n * Math.pow(2, -24)) / (1 - n * Math.pow(2, -24))
    const G8 = gamma(8)
    // H(t) = hStar * ln( exp(H0/hStar) + c*P0m*t/hStar ), P0m = P0mm * 1e-3.
    const heimsath = (h0, p0mm, hStar, years, c) => {
      const x = (c * p0mm * 1e-3 * years) / hStar
      return hStar * Math.log(Math.exp(h0 / hStar) + x)
    }
    // The magnitudes that flow through the chain, so the bound is derived from the fixture rather
    // than picked. At zero production this collapses to 0 and the comparison becomes bit-for-bit,
    // which is exactly what the sprint's zero-control asks for.
    const boundFor = (h0, p0mm, hStar, years, c) => {
      const want = heimsath(h0, p0mm, hStar, years, c)
      const x = (c * p0mm * 1e-3 * years) / hStar
      return G8 * (Math.abs(want) + Math.abs(h0) + hStar * x)
    }

    // ---------- find the producer -----------------------------------------------------------------
    // By port semantic first: the type string is the implementer's business, the contract is not.
    const registry = (typeof TYPES === 'object' && TYPES) ? TYPES : {}
    const bySemantic = Object.entries(registry).filter(([, d]) => d && Array.isArray(d.outputs)
      && d.outputs.some(p => p && p.semantic === 'soilDepth'))
    const byName = CONTRACT.candidateTypes.filter(t => registry[t])
    // A SEMANTIC IS NOT AN IDENTITY. Discovery by `outputs[].semantic === 'soilDepth'` was
    // unambiguous when this oracle was written and stopped being so inside the same sprint: S3.4's
    // selectors publish soilDepth too, so `bySemantic[0]` started returning whichever the registry
    // happened to iterate first and the gate reported the producer missing while it sat there
    // registered and digesting. Nothing was wrong with either node.
    //
    // A producer INTEGRATES OVER TIME; a selector reads a wire. The duration parameter is the thing
    // only the producer can have — the contract already requires it to exist with no default — so
    // it is the discriminator, with the name list as a fallback and first-match as a last resort.
    // DECLARED, not inferred. This discovery has now collapsed twice on heuristics: `bySemantic[0]`
    // broke when S3.4's selectors republished soilDepth, and the /duration/i discriminator that
    // replaced it broke when S3.5c gave erosion2 both a soilDepth output and a duration slider. A
    // producer now SAYS it is one (`producerOf`), and the heuristics survive only as a fallback for
    // a build where nothing declares — which is itself reported, so the fallback cannot hide.
    const declaredProducers = Object.entries(registry).filter(([, d]) => d && Array.isArray(d.producerOf)
      && d.producerOf.includes('soilDepth'))
    const hasDuration = d => Array.isArray(d.params)
      && d.params.some(pr => pr && typeof pr.key === 'string' && /duration/i.test(pr.key))
    const inferred = bySemantic.filter(([, d]) => hasDuration(d))
    const producers = declaredProducers.length ? declaredProducers : inferred
    const T = producers.length ? producers[0][0]
      : (byName[0] || (bySemantic.length ? bySemantic[0][0] : null))
    const DEF = T ? registry[T] : null
    out.discovery = {
      bySemantic: bySemantic.map(([t]) => t),
      byName,
      type: T,
      // Count PRODUCERS, not publishers. `bySemantic.length` was the count when only a producer
      // could publish soilDepth; S3.4's selectors republish it on their outputs, legitimately, so
      // that number is now "how many nodes carry the semantic" and says nothing about uniqueness of
      // the thing under test. Both are reported: the gate wants exactly one producer, and a rising
      // publisher count is information rather than a failure.
      producerCount: producers.length,
      declaredProducers: declaredProducers.map(([t]) => t),
      discoveredBy: declaredProducers.length ? 'declared' : (inferred.length ? 'inferred' : 'fallback'),
      publisherCount: bySemantic.length,
      producers: producers.map(([t]) => t),
      registrySize: Object.keys(registry).length,
    }

    // The story forbids reusing the colour-only Weathering plugin (sprint lines 125-127).
    const weath = registry.weathering
    out.weathering = {
      present: !!weath,
      passthrough: !!(weath && weath.passthrough),
      declaresSoil: !!(weath && Array.isArray(weath.outputs)
        && weath.outputs.some(p => p && p.semantic === 'soilDepth')),
      isTheProducer: T === 'weathering',
    }

    // The aux registry is production state, not documentation: S3.2 owns soilDepth and must flip it
    // from 'planned' to a real typed port.
    const aux = (typeof AUXMAPS === 'object' && AUXMAPS && AUXMAPS.AUX_MAPS) ? AUXMAPS.AUX_MAPS.soilDepth : null
    out.aux = aux ? { lens: aux.lens, kind: aux.kind, unit: aux.unit, status: aux.status, owner: aux.owner } : null
    const sem = (typeof PORTS === 'object' && PORTS && PORTS.SEMANTICS) ? PORTS.SEMANTICS.soilDepth : null
    out.semantic = sem ? { kind: sem.kind, defaultUnit: sem.defaultUnit, continuous: sem.continuous } : null

    // ---------- port and parameter descriptors ----------------------------------------------------
    const portsOf = node => {
      if (!DEF) return { inputs: [], outputs: [] }
      try {
        if (typeof DEF.resolvePorts === 'function') {
          const r = DEF.resolvePorts(node) || {}
          return { inputs: r.inputs || [], outputs: r.outputs || [] }
        }
      } catch (e) { /* a resolvePorts that throws is reported through the empty table below */ }
      return { inputs: DEF.inputs || [], outputs: DEF.outputs || [] }
    }
    const paramList = (DEF && Array.isArray(DEF.params)) ? DEF.params : []
    const findParam = re => paramList.find(p => p && typeof p.key === 'string' && re.test(p.key)) || null
    const pP0 = findParam(/p0/i)
    const pHStar = findParam(/hstar|h_star/i)
    const pDur = findParam(/duration|years/i)
    const KEY_P0 = pP0 ? pP0.key : 'p0MmPerYr'
    const KEY_HSTAR = pHStar ? pHStar.key : 'hStarM'
    const KEY_DUR = pDur ? pDur.key : 'durationYears'
    const desc = p => p ? { key: p.key, min: p.min, max: p.max, def: p.def, unit: p.unit == null ? null : String(p.unit) } : null
    out.params = { p0: desc(pP0), hStar: desc(pHStar), duration: desc(pDur), count: paramList.length }

    const probeNode = { id: 9001, type: T || 'absent', params: {} }
    const declared = portsOf(probeNode)
    const outPort = (declared.outputs || []).find(p => p && (p.id === CONTRACT.outputPortId || p.semantic === 'soilDepth')) || null
    const soilIn = (declared.inputs || []).find(p => p && (p.id === CONTRACT.soilInputId || p.semantic === 'soilDepth')) || null
    const climIn = (declared.inputs || []).find(p => p && p.id === CONTRACT.climateInputId) || null
    const idxOf = port => port ? (declared.inputs || []).indexOf(port) : -1
    const SOIL_SLOT = idxOf(soilIn) >= 0 ? idxOf(soilIn) : 0
    const CLIM_SLOT = idxOf(climIn) >= 0 ? idxOf(climIn) : 1
    out.ports = {
      inputIds: (declared.inputs || []).map(p => p && p.id),
      outputIds: (declared.outputs || []).map(p => p && p.id),
      output: outPort ? { id: outPort.id, kind: outPort.kind, unit: outPort.unit, semantic: outPort.semantic, lens: outPort.lens } : null,
      soilInput: soilIn ? { id: soilIn.id, unit: soilIn.unit, semantic: soilIn.semantic, required: !!soilIn.required } : null,
      climateInput: climIn ? { id: climIn.id, unit: climIn.unit, semantic: climIn.semantic, required: !!climIn.required } : null,
      soilSlot: SOIL_SLOT, climateSlot: CLIM_SLOT,
    }

    // ---------- MUTATIONS: every one perturbs PRODUCTION -------------------------------------------
    // None of them writes to a value this file later compares against. The oracle's answers come out
    // of `heimsath` above, computed from the sprint's constants in double precision, and no control
    // can reach it. Each control below replaces something in the LIVE registry and then records
    // whether the registry actually moved — a control that silently failed to apply (a frozen
    // descriptor written through, say) is itself reported and gated.
    const realEval = DEF ? DEF.eval : null
    const mLog = { name: mutation || null, applied: false, note: DEF ? 'not applied' : 'producer absent — nothing to perturb' }
    const asField = r => {
      if (!r) return null
      if (ArrayBuffer.isView(r)) return r
      if (r.values && typeof r.values.get === 'function') {
        return r.values.get(CONTRACT.outputPortId) || [...r.values.values()][0] || null
      }
      return null
    }
    if (mutation && DEF && typeof realEval === 'function') {
      if (mutation === 'constant-production-rate') {
        // The depth-dependence is gone: production runs at P0 regardless of how thick the soil is.
        // This is a whole wrong evaluator in the registry, not a doctored number.
        DEF.eval = (p, ins, nd, ctx) => {
          const src = ins && ins[SOIL_SLOT]
          const clim = ins && ins[CLIM_SLOT]
          const w = fieldW(), h = fieldH(), o = new Float32Array(w * h)
          const years = Number(p[KEY_DUR]), p0 = Number(p[KEY_P0]), hStar = Number(p[KEY_HSTAR])
          if (!Number.isFinite(years)) { const e = new Error('duration required'); e.code = CONTRACT.missingDurationCode; throw e }
          for (let i = 0; i < o.length; i++) {
            const h0 = src ? src[i] : 0
            const c = clim ? clim[i] : 1
            o[i] = h0 + c * p0 * 1e-3 * years          // no exp(-H/hStar)
          }
          return o
        }
        mLog.applied = DEF.eval !== realEval
        mLog.note = 'TYPES[' + T + '].eval replaced with a depth-independent producer'
      }
      if (mutation === 'zero-duration-nonzero-soil') {
        // The exact named defect: an absent or zero duration is silently assumed to be 1 year.
        DEF.eval = (p, ins, nd, ctx) => realEval({ ...p, [KEY_DUR]: Number(p[KEY_DUR]) || 1 }, ins, nd, ctx)
        mLog.applied = DEF.eval !== realEval
        mLog.note = 'TYPES[' + T + '].eval now defaults duration to 1 year'
      }
      if (mutation === 'depth-in-millimetres') {
        // The 1000x error that still looks like terrain: the port still says metres.
        DEF.eval = (p, ins, nd, ctx) => {
          const f = asField(realEval(p, ins, nd, ctx))
          if (!f) return f
          const o = new Float32Array(f.length)
          for (let i = 0; i < f.length; i++) o[i] = f[i] * 1000
          return o
        }
        mLog.applied = DEF.eval !== realEval
        mLog.note = 'TYPES[' + T + '].eval now emits millimetres behind a metres-labelled port'
      }
      if (mutation === 'climate-modulation-required') {
        // Two halves, because "optional becomes mandatory" is both a descriptor and a behaviour.
        // The descriptor is REPLACED rather than written through: a frozen port object would make
        // `port.required = true` a silent no-op under sloppy-mode page.evaluate, and the registry
        // move is asserted immediately below rather than assumed.
        const before = DEF.inputs
        DEF.inputs = (DEF.inputs || []).map(p => (p && p.id === CONTRACT.climateInputId)
          ? { ...p, required: true } : p)
        const moved = DEF.inputs !== before
          && (DEF.inputs || []).some(p => p && p.id === CONTRACT.climateInputId && p.required === true)
        DEF.eval = (p, ins, nd, ctx) => {
          if (!(ins && ins[CLIM_SLOT])) { const e = new Error('climate required'); e.code = 'REGOLITH_CLIMATE_REQUIRED'; throw e }
          return realEval(p, ins, nd, ctx)
        }
        mLog.applied = moved && DEF.eval !== realEval
        mLog.registryMoved = moved
        mLog.note = 'climate input descriptor replaced with required:true and eval refuses an absent multiplier'
      }
    }

    // RE-READ THE DESCRIPTORS. out.ports above was snapshotted BEFORE the mutation block, so a
    // control that replaces DEF.inputs — `climate-modulation-required` does exactly that — left the
    // snapshot showing the pre-mutation value. climateModulationIsOptional's `required === false`
    // clause could therefore never fail, and a build declaring climate required while its eval
    // still tolerated an absent field would have passed. The behavioural half of that control was
    // armed, so the row read ARMED and the descriptor half was silently unmeasured: half a gate,
    // which is the shape this project keeps finding.
    {
      const post = portsOf({ id: 9002, type: T || 'absent', params: {} })
      const climPost = (post.inputs || []).find(p => p && p.id === CONTRACT.climateInputId) || null
      const soilPost = (post.inputs || []).find(p => p && (p.id === CONTRACT.soilInputId || p.semantic === 'soilDepth')) || null
      out.ports.climateInput = climPost
        ? { id: climPost.id, unit: climPost.unit, semantic: climPost.semantic, required: !!climPost.required } : null
      out.ports.soilInput = soilPost
        ? { id: soilPost.id, unit: soilPost.unit, semantic: soilPost.semantic, required: !!soilPost.required } : null
      out.ports.rereadAfterMutation = true
    }

    // ---------- calling production ------------------------------------------------------------------
    const call = (params, ins) => {
      if (!DEF || typeof DEF.eval !== 'function') return { err: 'PRODUCER_ABSENT', field: null }
      try {
        const f = asField(DEF.eval(params, ins, { id: 9001, type: T, params }))
        return { err: f ? null : 'NO_FIELD_RETURNED', field: f }
      } catch (e) {
        return { err: (e && e.code) || ('THROW:' + String((e && e.message) || e)).slice(0, 90), field: null }
      }
    }
    const mkParams = (years, p0 = K.P0_INIT, hStar = K.HSTAR_INIT) => {
      const p = { [KEY_P0]: p0, [KEY_HSTAR]: hStar }
      if (years !== undefined) p[KEY_DUR] = years
      return p
    }

    // The H0 corpus. Exactly 0, hStar and 2*hStar are present and named — the three points sprint
    // line 80 requires — plus a spread so a fixture cannot be a lucky single reading.
    const H0_SET = [0, 0.25, 0.5, 1, 1.5, 2, 3, 5].map(k => k * K.HSTAR_INIT)
    const IDX = { zero: 0, oneHStar: 3, twoHStar: 5 }   // H0 = 0, hStar, 2*hStar — sprint line 80

    const buildH0 = (w, h) => {
      const a = new Float32Array(w * h)
      for (let i = 0; i < a.length; i++) a[i] = H0_SET[i % H0_SET.length]
      return a
    }

    // One fixture reading: set the lattice and resolution, build H0, run production, and compare
    // every sample against the double-precision law evaluated at the SAME float32 H0 that
    // production was handed — so input quantisation is not in the error budget.
    const fixture = ({ res, lattice, years, climate, p0 = K.P0_INIT, hStar = K.HSTAR_INIT, withSoil = true }) => {
      terrainDef.lattice = lattice
      RES = res; TARGET_RES = res
      const w = fieldW(), h = fieldH()
      const h0 = withSoil ? buildH0(w, h) : null
      let clim = null
      if (climate != null) { clim = new Float32Array(w * h); clim.fill(climate) }
      const ins = []
      ins[SOIL_SLOT] = h0
      ins[CLIM_SLOT] = clim
      const r = call(mkParams(years, p0, hStar), ins)
      const res_ = {
        res, lattice, w, h, cellSizeM: cellSizeM(), err: r.err,
        length: r.field ? r.field.length : 0,
        expectLength: w * h,
        samples: [], maxAbsErr: null, maxRelErr: null, worstIndex: -1,
        minValue: null, maxValue: null, nonFinite: 0, belowInput: 0, distinctH0: new Set(H0_SET).size,
        volumeM3: null, matchesMetres: null, matchesMillimetres: null, matchesP0AsMetresPerYr: null,
      }
      if (!r.field) return res_
      const f = r.field
      const c = climate == null ? 1 : climate
      let worst = -1, worstAbs = -1, mn = Infinity, mx = -Infinity, sum = 0
      let okMetres = f.length > 0, okMm = f.length > 0, okP0m = f.length > 0
      for (let i = 0; i < f.length; i++) {
        const v = f[i]
        if (!Number.isFinite(v)) { res_.nonFinite++; continue }
        const start = h0 ? Number(h0[i]) : 0
        const want = heimsath(start, p0, hStar, years, c)
        const bound = boundFor(start, p0, hStar, years, c)
        const abs = Math.abs(v - want)
        if (abs > bound) { okMetres = false }
        // The same bound, scaled by the same 1000: if production were emitting millimetres this
        // reading — and not the metres one — is the one that would hold.
        if (Math.abs(v - want * 1000) > bound * 1000) okMm = false
        // P0 mistaken for m/yr — the missing 1e-3.
        const wantP0m = heimsath(start, p0 * 1000, hStar, years, c)
        if (Math.abs(v - wantP0m) > boundFor(start, p0 * 1000, hStar, years, c)) okP0m = false
        if (abs > worstAbs) { worstAbs = abs; worst = i }
        if (v < mn) mn = v
        if (v > mx) mx = v
        if (h0 && v < start - bound) res_.belowInput++
        sum += v
      }
      res_.maxAbsErr = worstAbs
      res_.worstIndex = worst
      res_.minValue = mn === Infinity ? null : mn
      res_.maxValue = mx === -Infinity ? null : mx
      res_.matchesMetres = okMetres
      res_.matchesMillimetres = okMm
      res_.matchesP0AsMetresPerYr = okP0m
      // Lattice cell AREA differs: square s^2, hex sqrt(3)/2 * s^2. A soil VOLUME reported with the
      // square area on a hex field overstates it by 2/sqrt(3).
      const s = cellSizeM()
      const area = lattice === 'hex' ? (Math.sqrt(3) / 2) * s * s : s * s
      res_.volumeM3 = sum * area
      res_.cellAreaM2 = area
      // The three named points, reported with their own bounds.
      for (const [name, k] of Object.entries(IDX)) {
        const start = h0 ? Number(h0[k]) : 0
        const want = heimsath(start, p0, hStar, years, c)
        res_.samples.push({
          name, index: k, h0: start, got: f[k], want,
          absErr: Math.abs(f[k] - want), bound: boundFor(start, p0, hStar, years, c),
          within: Math.abs(f[k] - want) <= boundFor(start, p0, hStar, years, c),
        })
      }
      let relMax = 0
      for (const s2 of res_.samples) if (s2.want !== 0) relMax = Math.max(relMax, s2.absErr / Math.abs(s2.want))
      res_.maxRelErr = relMax
      return res_
    }

    // ---------- the readings ------------------------------------------------------------------------
    out.square = fixture({ res: 64, lattice: 'square', years: K.YEARS })
    out.square128 = fixture({ res: 128, lattice: 'square', years: K.YEARS })
    out.hex = fixture({ res: 64, lattice: 'hex', years: K.YEARS })

    // Resolution consistency: the law is pointwise, so the same H0 must give the SAME depth at 64
    // and at 128. An implementation that folded cellSizeM into the rate fails here and nowhere else.
    out.resolution = {
      rows64: out.square.h, rows128: out.square128.h,
      cell64: out.square.cellSizeM, cell128: out.square128.cellSizeM,
      cellsDiffer: out.square.cellSizeM !== out.square128.cellSizeM,
      identical: out.square.samples.length > 0 && out.square128.samples.length === out.square.samples.length
        && out.square.samples.every((s, i) => s.got === out.square128.samples[i].got),
    }
    out.latticeIndependent = out.square.samples.length > 0 && out.hex.samples.length === out.square.samples.length
      && out.square.samples.every((s, i) => s.got === out.hex.samples[i].got)

    // Zero controls, neither of which needs a bedrock elevation.
    terrainDef.lattice = 'square'; RES = 64; TARGET_RES = 64
    const W = fieldW(), H = fieldH()
    const zeroDurNoSoil = call(mkParams(0), [])
    const zeroDurWithSoil = fixture({ res: 64, lattice: 'square', years: 0 })
    const zeroClimate = call(mkParams(K.YEARS), (() => { const a = []; a[SOIL_SLOT] = null; a[CLIM_SLOT] = new Float32Array(W * H); return a })())
    const allExactlyZero = f => !!f && f.length > 0 && Array.prototype.every.call(f, v => v === 0)
    out.zeroControls = {
      zeroDurationNoSoil: { err: zeroDurNoSoil.err, length: zeroDurNoSoil.field ? zeroDurNoSoil.field.length : 0,
        allZero: allExactlyZero(zeroDurNoSoil.field) },
      zeroDurationWithSoil: { err: zeroDurWithSoil.err, within: zeroDurWithSoil.samples.every(s => s.within),
        maxAbsErr: zeroDurWithSoil.maxAbsErr, samples: zeroDurWithSoil.samples },
      zeroClimate: { err: zeroClimate.err, length: zeroClimate.field ? zeroClimate.field.length : 0,
        allZero: allExactlyZero(zeroClimate.field) },
    }

    // Climate modulation is OPTIONAL. c = 1 must be bit-identical to no connection at all, and
    // c = 0.5 must move the answer to the analytic half-rate result — otherwise "optional
    // multiplier" is a port nothing reads.
    const noClimate = fixture({ res: 64, lattice: 'square', years: K.YEARS })
    const climateOne = fixture({ res: 64, lattice: 'square', years: K.YEARS, climate: 1 })
    const climateHalf = fixture({ res: 64, lattice: 'square', years: K.YEARS, climate: 0.5 })
    out.climate = {
      absentErr: noClimate.err, oneErr: climateOne.err, halfErr: climateHalf.err,
      oneIsIdentity: noClimate.samples.length > 0 && climateOne.samples.length === noClimate.samples.length
        && noClimate.samples.every((s, i) => s.got === climateOne.samples[i].got),
      halfMatchesAnalytic: climateHalf.samples.length > 0 && climateHalf.samples.every(s => s.within),
      halfMoved: climateHalf.samples.length > 0 && noClimate.samples.length === climateHalf.samples.length
        && climateHalf.samples.every((s, i) => s.got !== noClimate.samples[i].got),
      halfGot: climateHalf.samples.map(s => s.got), noneGot: noClimate.samples.map(s => s.got),
    }

    // Duration is REQUIRED AUTHORED DATA. Missing must be a typed error, not an assumed 1; and a
    // negative duration must be refused rather than run backwards into negative depth.
    const missing = call(mkParams(undefined), [])
    const nullDur = call({ [KEY_P0]: K.P0_INIT, [KEY_HSTAR]: K.HSTAR_INIT, [KEY_DUR]: null }, [])
    const negative = call(mkParams(-500), [])
    const nanDur = call(mkParams(NaN), [])
    out.duration = {
      missingCode: missing.err, missingReturnedField: !!missing.field,
      nullCode: nullDur.err, nullReturnedField: !!nullDur.field,
      negativeCode: negative.err, negativeReturnedField: !!negative.field,
      nanCode: nanDur.err,
      // If a build DID assume 1 year, this is what it would have produced at H0 = 0 — non-zero, so
      // "returned no field" is not the only evidence available.
      assumedOneWouldGive: heimsath(0, K.P0_INIT, K.HSTAR_INIT, 1, 1),
      declaredDefault: pDur ? pDur.def : undefined,
    }

    // Non-negativity across the whole corpus, plus a long duration where an unstable step would
    // overshoot and a naive clamp would hide it.
    const long = fixture({ res: 64, lattice: 'square', years: 100000 })
    out.longRun = { err: long.err, min: long.minValue, max: long.maxValue, nonFinite: long.nonFinite,
      belowInput: long.belowInput, within: long.samples.every(s => s.within) }

    out.mutationLog = mLog
    out.constants = {
      P0_INIT: K.P0_INIT, HSTAR_INIT: K.HSTAR_INIT, YEARS: K.YEARS,
      wantZero: heimsath(0, K.P0_INIT, K.HSTAR_INIT, K.YEARS, 1),
      wantOneHStar: heimsath(K.HSTAR_INIT, K.P0_INIT, K.HSTAR_INIT, K.YEARS, 1),
      wantTwoHStar: heimsath(2 * K.HSTAR_INIT, K.P0_INIT, K.HSTAR_INIT, K.YEARS, 1),
      gamma8: G8,
      corpusSize: H0_SET.length, distinctH0: new Set(H0_SET).size,
    }
    terrainDef.lattice = 'square'; RES = 64; TARGET_RES = 64
    return out
  }, [mutation, CONTRACT, { P0_INIT, HSTAR_INIT, YEARS }])

  const sq = report.square, hx = report.hex, zc = report.zeroControls, cn = report.constants
  const p0d = report.params.p0, hsd = report.params.hStar, durd = report.params.duration
  const near = (a, b) => Number.isFinite(a) && Number.isFinite(b) && Math.abs(a - b) <= 1e-12 * Math.max(1, Math.abs(b))

  const gates = {
    // --- the node exists at all. RED TODAY: this is the story's named absence. -------------------
    producerRegistered: report.discovery.type !== null && report.discovery.producerCount === 1
      && report.discovery.discoveredBy === 'declared'
      && report.discovery.publisherCount >= report.discovery.producerCount,
    soilDepthSemanticRegistered: !!report.semantic && report.semantic.kind === 'scalarRaster'
      && report.semantic.defaultUnit === 'm',
    soilDepthIsAStatePortInMetres: !!report.ports.output && report.ports.output.unit === 'm'
      && report.ports.output.kind === 'scalarRaster' && report.ports.output.lens === 'state'
      && report.ports.output.semantic === 'soilDepth',
    auxRegistryPromotesSoilDepthToAPort: !!report.aux && report.aux.status === 'port'
      && report.aux.lens === 'state' && report.aux.unit === 'm',
    producerIsNotTheColourWeatheringNode: report.weathering.present === true
      && report.weathering.isTheProducer === false && report.weathering.declaresSoil === false
      && report.weathering.passthrough === true,

    // --- the authored contract: units and the derived initial values -------------------------------
    p0AuthoredInMmPerYrOverTheCitedRange: !!p0d && near(p0d.min, 0.05) && near(p0d.max, 0.3)
      && near(p0d.def, cn.P0_INIT) && /mm\s*\/?\s*(yr|year)/i.test(String(p0d.unit || '')),
    hStarAuthoredInMetresOverTheCitedRange: !!hsd && near(hsd.min, 0.3) && near(hsd.max, 0.5)
      && near(hsd.def, cn.HSTAR_INIT) && /^m$/i.test(String(hsd.unit || '').trim()),

    // --- the law itself, against a double-precision evaluation of the same equation ---------------
    heimsathMatchesAnalyticAtZeroOneAndTwoHStar: sq.err === null && sq.samples.length === 3
      && sq.samples.every(s => s.within === true) && sq.nonFinite === 0,
    // The 1000x trap, decided by the numbers: the correct reading must match and both rivals must not.
    depthIsMetresNotMillimetres: sq.matchesMetres === true && sq.matchesMillimetres === false
      && sq.matchesP0AsMetresPerYr === false,
    productionIsDepthDependent: sq.samples.length === 3
      && sq.samples[0].got !== sq.samples[1].got && sq.samples[1].got !== sq.samples[2].got
      // self-limiting: thicker soil gains less. A constant rate makes these three increments equal.
      && (sq.samples[0].got - sq.samples[0].h0) > (sq.samples[1].got - sq.samples[1].h0)
      && (sq.samples[1].got - sq.samples[1].h0) > (sq.samples[2].got - sq.samples[2].h0),

    // --- zero production, and never negative --------------------------------------------------------
    zeroDurationProducesZeroSoilBitForBit: zc.zeroDurationNoSoil.err === null
      && zc.zeroDurationNoSoil.length > 0 && zc.zeroDurationNoSoil.allZero === true,
    zeroDurationAddsNothingToExistingSoil: zc.zeroDurationWithSoil.err === null
      && zc.zeroDurationWithSoil.within === true,
    zeroClimateProducesZeroSoilBitForBit: zc.zeroClimate.err === null
      && zc.zeroClimate.length > 0 && zc.zeroClimate.allZero === true,
    depthNeverGoesNegative: sq.minValue !== null && sq.minValue >= 0 && hx.minValue !== null && hx.minValue >= 0
      && report.longRun.min !== null && report.longRun.min >= 0 && report.longRun.nonFinite === 0
      && sq.belowInput === 0 && report.longRun.belowInput === 0 && report.longRun.within === true,

    // --- duration has NO default ---------------------------------------------------------------------
    durationHasNoProductionDefault: !!durd && durd.def == null,
    missingDurationIsATypedError: report.duration.missingCode === CONTRACT.missingDurationCode
      && report.duration.missingReturnedField === false
      && report.duration.nullCode === CONTRACT.missingDurationCode
      && report.duration.nullReturnedField === false,
    invalidDurationIsRefusedNotRunBackwards: report.duration.negativeCode === CONTRACT.badDurationCode
      && report.duration.negativeReturnedField === false
      && report.duration.nanCode === CONTRACT.badDurationCode,

    // --- climate modulation is optional, and is genuinely read when supplied -------------------------
    climateModulationIsOptional: report.ports.rereadAfterMutation === true
      && !!report.ports.climateInput && report.ports.climateInput.required === false
      && report.ports.climateInput.unit === 'none' && report.climate.absentErr === null,
    climateOneIsIdenticalToNoClimate: report.climate.oneErr === null && report.climate.oneIsIdentity === true,
    climateMultiplierActuallyModulates: report.climate.halfErr === null
      && report.climate.halfMatchesAnalytic === true && report.climate.halfMoved === true,

    // --- lattice and resolution -----------------------------------------------------------------------
    hexFieldHasHexRowsAndTheSameLaw: hx.err === null && hx.h !== hx.res && hx.length === hx.expectLength
      && hx.samples.length === 3 && hx.samples.every(s => s.within === true) && hx.nonFinite === 0,
    squareFieldIsFullLength: sq.length === sq.expectLength && sq.length > 0,
    depthDoesNotDependOnCellSizeOrLattice: report.resolution.cellsDiffer === true
      && report.resolution.identical === true && report.latticeIndependent === true,

    // --- a named mutation must actually have perturbed production ---------------------------------------
    mutationPerturbedProduction: !mutation || report.mutationLog.applied === true,

    // --- absence of evidence is a failure ----------------------------------------------------------------
    evidenceNonEmpty: report.discovery.registrySize > 40 && cn.corpusSize >= 5 && cn.distinctH0 === cn.corpusSize
      && sq.samples.length === 3 && sq.length > 0 && hx.length > 0
      && cn.wantZero > 0 && cn.wantOneHStar > cn.wantZero && cn.wantTwoHStar > cn.wantOneHStar,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  const got = sq.samples.length ? sq.samples.map(s => Number(s.got).toPrecision(9)).join(',') : 'absent'
  const want = [cn.wantZero, cn.wantOneHStar, cn.wantTwoHStar].map(v => v.toPrecision(9)).join(',')
  console.log(`${ok ? 'PASS' : 'FAIL'}  soildepth producer=${report.discovery.type || 'none'} outUnit=${report.ports.output ? report.ports.output.unit : 'none'} `
    + `auxStatus=${report.aux ? report.aux.status : 'none'} H0=[0,hStar,2hStar] got=[${got}] want=[${want}] `
    + `maxRelErr=${sq.maxRelErr === null ? 'n/a' : sq.maxRelErr} gamma8=${cn.gamma8.toExponential(3)} `
    + `metres=${sq.matchesMetres}/mm=${sq.matchesMillimetres} zeroDur=${zc.zeroDurationNoSoil.allZero} `
    + `durationErr=${report.duration.missingCode} hexRows=${hx.h}x${hx.w} minDepth=${sq.minValue} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
