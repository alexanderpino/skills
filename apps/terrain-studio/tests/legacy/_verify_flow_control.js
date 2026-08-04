// S8.1 — Route / Chokepoint identity and Edge boundary extraction.
//
// The negative control the story names for Edge is "a constant field is empty". That control is
// necessary but NOT discriminating on its own: a wrong implementation — gradient magnitude, say —
// also returns empty for a constant field. The case that separates right from wrong is the
// analytic disc, where the answer is known exactly: the boundary must be one legal-neighbour ring
// at the declared threshold, every cell of it inside the disc, and none of it in the interior.
// Both are asserted here; only the disc can fail a plausible-but-wrong Edge.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'route-drops-type',     // the story's named failure: Route loses source type/unit
  'route-copies-values',  // Route perturbs bytes instead of being identity
  'identity-refuses-vectors', // the identity ports stop adapting and refuse the vector fixture
  'edge-eight-neighbour', // square Edge uses 8-neighbourhood -> ring thickness is anisotropic
  'edge-fills-interior',  // Edge returns the whole mask instead of its boundary
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

;(async () => {
  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const report = await page.evaluate(mutation => {
    USE_GPU = false; RES = 128; TARGET_RES = 128; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null, lattices: {} }
    const w = () => RES, h = () => (terrainDef.lattice === 'hex' ? Math.round(RES * 2 / Math.sqrt(3)) : RES)

    // --- Route and Chokepoint: identity, exactly, for BOTH kinds -------------------------------
    // Both controls here used to assign the answer in this file — `routed = Float32Array.from(src)`
    // and `inheritsSemantic = mutation === 'route-drops-type' ? false : ...`. That proved the test
    // could edit a local and nothing whatever about the node. They now replace entries in the LIVE
    // registry, so everything measured below comes out of production's descriptors and eval.
    if (mutation === 'route-drops-type') {
      for (const t of ['route', 'chokepoint']) {
        TYPES[t].outputs = (TYPES[t].outputs || []).map(p => p.semanticFrom
          ? { ...p, semanticFrom: undefined, kindFrom: undefined, semantic: 'relativeHeight', unit: 'none' } : p)
      }
    }
    if (mutation === 'route-copies-values') {
      for (const t of ['route', 'chokepoint']) {
        const real = TYPES[t].eval
        TYPES[t].eval = (p, ins, n, c) => { const copy = Float32Array.from(real(p, ins, n, c)); copy[7] += 1e-6; return copy }
      }
    }
    if (mutation === 'identity-refuses-vectors') {
      for (const t of ['route', 'chokepoint']) {
        TYPES[t].inputs = (TYPES[t].inputs || []).map(p => ({ ...p, kindFrom: undefined }))
      }
    }

    const src = new Float32Array(w() * h())
    for (let i = 0; i < src.length; i++) src[i] = Math.sin(i * 0.017) * 0.5 + 0.5
    // S8.1 names "scalar and vector fixtures", so the vector case is measured, not assumed. Three
    // components per cell is what the registry's one vectorRaster (normals.normal) actually emits.
    const vec = new Float32Array(w() * h() * 3)
    for (let i = 0; i < vec.length; i++) vec[i] = Math.cos(i * 0.011)

    out.identity = {}
    for (const t of ['route', 'chokepoint']) {
      const scalarOut = TYPES[t].eval({}, [src], {})
      const vectorOut = TYPES[t].eval({}, [vec], {})
      const p = (TYPES[t].outputs || [])[0] || {}
      out.identity[t] = {
        sameLength: scalarOut.length === src.length,
        // Identity means the SAME object, not an equal copy — a copy would cost a field allocation
        // per evaluation for no reason.
        sameObject: scalarOut === src,
        byteIdentical: (() => { for (let i = 0; i < src.length; i++) if (scalarOut[i] !== src[i]) return false; return true })(),
        vectorSameObject: vectorOut === vec,
        vectorByteIdentical: (() => { for (let i = 0; i < vec.length; i++) if (vectorOut[i] !== vec[i]) return false; return true })(),
        nullInputSafe: TYPES[t].eval({}, [null], {}).length === src.length,
        // The typed identity: the output must INHERIT semantic and kind, never declare its own.
        inheritsSemantic: !!(p.semanticFrom && p.semanticFrom.mode === 'inherit') && p.semantic === undefined && p.unit === undefined,
        inheritsKind: !!(p.kindFrom && p.kindFrom.mode === 'inherit'),
      }
    }
    // Connection time, through production's canConnect: an identity node must ACCEPT the registry's
    // vectorRaster while an ordinary scalar input still refuses it. Without both halves this reads
    // as green under a build that simply stopped checking kinds.
    const vecPort = (TYPES.normals.outputs || []).find(p => p.kind === 'vectorRaster')
    out.wire = {
      vectorPortFound: !!vecPort,
      intoRoute: !!PORTS.canConnect(vecPort, (TYPES.route.inputs || [])[0]).ok,
      intoChokepoint: !!PORTS.canConnect(vecPort, (TYPES.chokepoint.inputs || [])[0]).ok,
      intoBlend: !!PORTS.canConnect(vecPort, (TYPES.blend.inputs || [])[0]).ok,
      blendCode: PORTS.canConnect(vecPort, (TYPES.blend.inputs || [])[0]).code || null,
    }

    // --- Edge: the analytic disc, on both lattices ---------------------------------------------
    for (const lattice of ['square', 'hex']) {
      terrainDef.lattice = lattice
      const W = w(), H = h()
      const cx = (W - 1) / 2, cy = (H - 1) / 2, R = Math.min(W, H) * 0.3
      const disc = new Float32Array(W * H)
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        disc[y * W + x] = Math.hypot(x - cx, y - cy) <= R ? 1 : 0
      }
      let ring = TYPES.edge.eval({ threshold: 0.5 }, [disc], {})
      if (mutation === 'edge-fills-interior') ring = disc
      if (mutation === 'edge-eight-neighbour' && lattice === 'square') {
        // A thicker, anisotropic ring: what an 8-neighbourhood would produce.
        const fat = new Float32Array(W * H)
        for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) {
          if (!(disc[y * W + x] > 0.5)) continue
          let edgeHere = false
          for (let dy = -1; dy <= 1 && !edgeHere; dy++) for (let dx = -1; dx <= 1; dx++) {
            if (!(disc[(y + dy) * W + x + dx] > 0.5)) { edgeHere = true; break }
          }
          if (edgeHere) fat[y * W + x] = 1
        }
        ring = fat
      }

      // The neighbourhood contract, asserted DIRECTLY rather than inferred from cell count.
      // Every boundary cell must have at least one LEGAL neighbour below the threshold — 4 on
      // square, 6 on hex. An 8-neighbourhood implementation admits cells whose only outside
      // neighbour is diagonal, and those fail here. Counting ring cells could not separate the two:
      // both produce a plausible-looking O(2*pi*R) ring, which is exactly why the first version of
      // this gate let the 8-neighbour mutation through.
      let illegalRingCells = 0
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (!(ring[y * W + x] > 0.5)) continue
        let hasLegalOutside = false
        if (lattice === 'hex') {
          const nb = hexNb(y)
          for (let k = 0; k < 6; k++) {
            const nx = x + nb[k][0], ny = y + nb[k][1]
            if (nx < 0 || ny < 0 || nx >= W || ny >= H) { hasLegalOutside = true; break }
            if (!(disc[ny * W + nx] > 0.5)) { hasLegalOutside = true; break }
          }
        } else {
          if (x === 0 || y === 0 || x === W - 1 || y === H - 1) hasLegalOutside = true
          else if (!(disc[y * W + x - 1] > 0.5) || !(disc[y * W + x + 1] > 0.5)
            || !(disc[(y - 1) * W + x] > 0.5) || !(disc[(y + 1) * W + x] > 0.5)) hasLegalOutside = true
        }
        if (!hasLegalOutside) illegalRingCells++
      }

      let ringCount = 0, outsideDisc = 0, interiorHits = 0, minR = 1e9, maxR = -1e9
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
        if (!(ring[y * W + x] > 0.5)) continue
        ringCount++
        const d = Math.hypot(x - cx, y - cy)
        if (d > R) outsideDisc++
        // "Interior" = comfortably inside; a correct one-cell ring never reaches here.
        if (d < R - 2.0) interiorHits++
        if (d < minR) minR = d
        if (d > maxR) maxR = d
      }
      // A constant field has no boundary.
      const constant = new Float32Array(W * H).fill(1)
      const constRing = TYPES.edge.eval({ threshold: 0.5 }, [constant], {})
      let constCount = 0
      // The domain rim IS a boundary by contract, so count only the interior of the constant field.
      for (let y = 1; y < H - 1; y++) for (let x = 1; x < W - 1; x++) if (constRing[y * W + x] > 0.5) constCount++

      out.lattices[lattice] = {
        ringCount, outsideDisc, interiorHits, constInteriorCount: constCount, illegalRingCells,
        minR: +minR.toFixed(2), maxR: +maxR.toFixed(2),
        // One legal-neighbour ring: every ring cell sits within one cell of the analytic radius.
        withinOneCell: (R - minR) <= 2.0 && (maxR - R) <= 1.0,
        // Perimeter sanity: a one-cell ring on a disc of radius R has O(2*pi*R) cells. Generous
        // bounds, because the point is to catch a filled disc or an empty result, not to grade pi.
        perimeterPlausible: ringCount > 2 * Math.PI * R * 0.5 && ringCount < 2 * Math.PI * R * 2.2,
      }
    }
    terrainDef.lattice = 'square'
    return out
  }, mutation)

  const sq = report.lattices.square, hx = report.lattices.hex
  const gates = {
    identityPreservesScalarBytes: ['route', 'chokepoint'].every(t => report.identity[t].sameObject === true
      && report.identity[t].byteIdentical === true && report.identity[t].sameLength === true
      && report.identity[t].nullInputSafe === true),
    identityPreservesVectorBytes: ['route', 'chokepoint'].every(t => report.identity[t].vectorSameObject === true
      && report.identity[t].vectorByteIdentical === true),
    identityInheritsTypeAndUnit: ['route', 'chokepoint'].every(t => report.identity[t].inheritsSemantic === true
      && report.identity[t].inheritsKind === true),
    identityPortsAdmitVectorsAndOrdinaryPortsDoNot: report.wire.vectorPortFound === true
      && report.wire.intoRoute === true && report.wire.intoChokepoint === true
      && report.wire.intoBlend === false && report.wire.blendCode === 'KIND_MISMATCH',
    edgeRingOnDiscSquare: sq.ringCount > 0 && sq.outsideDisc === 0 && sq.interiorHits === 0
      && sq.withinOneCell === true && sq.perimeterPlausible === true,
    edgeRingOnDiscHex: hx.ringCount > 0 && hx.outsideDisc === 0 && hx.interiorHits === 0
      && hx.withinOneCell === true && hx.perimeterPlausible === true,
    everyRingCellHasALegalNeighbourOutside: sq.illegalRingCells === 0 && hx.illegalRingCells === 0,
    constantFieldHasNoBoundary: sq.constInteriorCount === 0 && hx.constInteriorCount === 0,
    evidenceNonEmpty: sq.ringCount > 0 && hx.ringCount > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  flow control route=${report.identity.route.sameObject} choke=${report.identity.chokepoint.sameObject} vec=${report.wire.intoRoute}/${report.wire.intoBlend} `
    + `ringSq=${sq.ringCount} ringHex=${hx.ringCount} constSq=${sq.constInteriorCount} illegalSq=${sq.illegalRingCells} `
    + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
