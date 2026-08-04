// S4.4 — the Lake / Basin node.
//
// A lake is a basin filled to its SPILL LEVEL. Everything this gate checks follows from that one
// sentence, and each clause is separable so each can fail alone:
//
//   flat        the water surface is one value across the whole body — to exact Float32 identity,
//               not to a tolerance, because every wet cell is assigned the same number by the flood
//               rather than each computing its own. This is the defining property of standing water
//               and it is the first thing a "fill to a slider level" implementation still satisfies,
//               which is why flatness alone is not enough...
//   at spill    ...and the level must be bit-identical to the elevation of the basin's lowest rim
//               cell. That is the assertion a fixed-level fill cannot pass, and the story names it
//               as the armed failure.
//   depth       waterDepth = max(0, surface - solidTop), exactly, everywhere. Zero on land.
//   shore       signed distance to the waterline in METRES: exactly zero on the shoreline, positive
//               offshore, negative inland, exactly Euclidean, and matching the analytic circle of an
//               analytic circular basin.
//   no carve    the terrain field is bit-identical before and after. Guardrail 1, and the story
//               calls it the single most important assertion in the sprint.
//
// Pure-module: it imports src/core/lakes.js under plain node and checks the physics in double
// precision. No browser, no legacy.js, no framebuffer to read back as zeros.
//
// The plugin's PORT BLOCK is checked too, statically, because three of the semantics it declares are
// not in ports.js yet (that file is owned elsewhere and the additions are in the story report). The
// check validates every port ports.js already knows and pins the three pending ones to the exact kind
// and unit the report asks for, so the request and the code cannot drift while they wait.
const path = require('path')
const fs = require('fs')
const { pathToFileURL } = require('url')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'tilted-flat',               // use the ROUTING fill's 2e-7 flat tilt: the water surface is a ramp
  'fixed-level',               // fill to an authored level regardless of spill -- the story's named failure
  'spill-from-highest-rim',    // report the highest rim cell as the spill instead of the lowest
  'spill-ignores-escape',      // break rim ties by index alone: picks a shoreline cell, not the notch
  'unsigned-shore-distance',   // a plain EDT: land reads as positively far offshore
  'shore-distance-in-cells',   // forget the cell size: shore distance in cells, labelled metres
  'write-height',              // write the water surface back into the terrain -- guardrail 1
  'labels-flood-dry',          // basin labelling crosses dry ground, merging separate lakes
  'suppressed-lake-keeps-fill',// a suppressed puddle keeps its raised surface: depth identity breaks
  'edt-even-rows-only',        // the real defect this oracle caught: square EDT skips every odd row
  'hex-ignores-stagger',       // hex EDT ignores the half-column row offset
  'label-range-wrong',         // basinId port declares a noLabel sentinel inside its own label range
]
// Patches are applied to the CORE module or to the PLUGIN file, whichever the failure lives in.
const PATCHES = {
  'tilted-flat': { core: [[
    'return fillDepressions(solidTop, w, hgt, { hex, flatEpsilon: LAKE_FLAT_EPSILON })',
    'return fillDepressions(solidTop, w, hgt, { hex, flatEpsilon: 2e-7 })']] },
  'fixed-level': { core: [[
    'return fillDepressions(solidTop, w, hgt, { hex, flatEpsilon: LAKE_FLAT_EPSILON })',
    'const LEVEL = 55.37\n  const out = new Float32Array(solidTop.length)\n'
    + '  for (let i = 0; i < out.length; i++) out[i] = Math.max(solidTop[i], LEVEL)\n  return out']] },
  'spill-from-highest-rim': { core: [
    ['let spillIndex = -1, spillH = Infinity, spillOut = Infinity',
     'let spillIndex = -1, spillH = -Infinity, spillOut = Infinity'],
    ['if (rh > spillH) continue', 'if (rh < spillH) continue'],
    ['|| rh < spillH', '|| rh > spillH'],
  ] },
  'spill-ignores-escape': { core: [[
    '(rh === spillH && (out < spillOut || (out === spillOut && r < spillIndex)))',
    '(rh === spillH && r < spillIndex)']] },
  'unsigned-shore-distance': { core: [[
    'out[i] = depth[i] > 0 ? d : (d === 0 ? 0 : -d)', 'out[i] = d']] },
  'shore-distance-in-cells': { core: [[
    'const shore = signedShoreDistanceM(depth, w, hgt, { hex, cellSizeM })',
    'const shore = signedShoreDistanceM(depth, w, hgt, { hex })']] },
  'write-height': { core: [[
    'for (let i = 0; i < N; i++) depth[i] = Math.max(0, surface[i] - solidTop[i])',
    'for (let i = 0; i < N; i++) { depth[i] = Math.max(0, surface[i] - solidTop[i]); solidTop[i] = surface[i] }']] },
  'labels-flood-dry': { core: [[
    'if (depth[ni] <= 0 || lakeId[ni] !== NO_LAKE) continue', 'if (lakeId[ni] !== NO_LAKE) continue']] },
  'suppressed-lake-keeps-fill': { core: [[
    'for (const i of cells) { surface[i] = solidTop[i]; depth[i] = 0; lakeId[i] = NO_LAKE }',
    'for (const i of cells) { depth[i] = 0; lakeId[i] = NO_LAKE }']] },
  'edt-even-rows-only': { core: [['const rowStep = hex ? 2 : 1', 'const rowStep = 2']] },
  'hex-ignores-stagger': { core: [
    ['const srcShift = hex ? par * 0.5 * cellSizeM : 0', 'const srcShift = 0'],
    ['const qShift = hex && (y & 1) ? 0.5 * cellSizeM : 0', 'const qShift = 0'],
  ] },
  'label-range-wrong': { plugin: [[
    'range: RANGE.labels(0, 2147483646, -1)', 'range: RANGE.labels(0, 2147483646, 0)']] },
}
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

const CORE = path.resolve(__dirname, '../../src/core/lakes.js')
const HYDRO = path.resolve(__dirname, '../../src/core/hydrology.js')
const PORTS = path.resolve(__dirname, '../../src/core/ports.js')
const PLUGIN = path.resolve(__dirname, '../../src/plugins/data/lake.js')

function patch(text, pairs, label) {
  for (const [anchor, repl] of pairs) {
    const hits = text.split(anchor).length - 1
    if (hits !== 1) { console.error(`FATAL ${label} anchor for ${mutation} matched ${hits}, expected 1: ${anchor}`); process.exit(2) }
    text = text.replace(anchor, repl)
  }
  return text
}

// --- the fixtures, all analytic -----------------------------------------------------------------
const W = 96, H = 96, N = W * H, CELL = 10   // 10 m cells, 960 m square domain
const PLATEAU = 100, CONE = 4, SPILL = 60    // a cone bowl rising 4 m per cell into a 100 m plateau
const NOTCH_X = 63, NOTCH_Y = 48             // where the outlet channel meets the rim: r = 15 cells
const HEX_ROW = Math.sqrt(3) / 2

// Independent world-position formulas. The module has its own; if the two ever disagree the exact-
// Euclidean assertions below go red, which is the point of writing them out twice.
const wx = (x, y, hex) => x * CELL + (hex && (y & 1) ? 0.5 * CELL : 0)
const wy = (y, hex) => y * CELL * (hex ? HEX_ROW : 1)
const NB8 = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [1, 1], [-1, 1], [1, -1]]
const nb6 = y => { const o = y & 1 ? 1 : 0; return [[-1, 0], [1, 0], [o - 1, -1], [o, -1], [o - 1, 1], [o, 1]] }
const nbOf = (y, hex) => (hex ? nb6(y) : NB8)

/**
 * A cone bowl sunk into a plateau, with a single outlet channel notched through the rim and sloping
 * away to the domain edge. Every answer is known in closed form: the lake level is the notch mouth's
 * elevation (60 m), the shoreline is the circle r = 60/4 = 15 cells, and the spill is one named cell.
 */
function bowl(hex) {
  const h = new Float32Array(N)
  const cx = wx(48, 48, hex), cy = wy(48, hex)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const r = Math.hypot(wx(x, y, hex) - cx, wy(y, hex) - cy) / CELL
    h[y * W + x] = Math.min(PLATEAU, CONE * r)
  }
  // The channel starts exactly on the rim contour and falls 0.5 m per cell, so the notch mouth is the
  // unique rim cell with somewhere lower to go — every other cell at 60 m is on the shoreline ring.
  for (let x = NOTCH_X; x < W; x++) {
    const i = NOTCH_Y * W + x
    h[i] = Math.min(h[i], SPILL - 0.5 * (x - NOTCH_X))
  }
  return h
}

/**
 * The same bowl on the 0..1 `relativeHeight` scale the rest of the app works in.
 *
 * IT EXISTS BECAUSE OF A MEASUREMENT, not for variety. The routing fill tilts its flats by 2e-7 so a
 * router can cross a lake instead of terminating on it. At the metre-scale fixture above, the Float32
 * ulp at 60 m is 7.15e-6 — thirty-eight times LARGER than that tilt — so `60 + 2e-7` rounds straight
 * back to 60 and the tilt is not merely small, it is not there. Every flatness assertion in this file
 * passed with the routing fill substituted in, and the gate runner scored the mutation VACUOUS. At
 * 0.6 the ulp is 7.15e-8 and the tilt is fully representable, so this is the scale on which "the lake
 * surface came out of the ROUTING fill" is a visible defect at all.
 */
function bowlUnit() {
  const h = bowl(false)
  const out = new Float32Array(N)
  for (let i = 0; i < N; i++) out[i] = h[i] / PLATEAU
  return out
}

/** Two bowls with different spills, sharing a plateau. Separate water bodies with separate levels. */
function twin() {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    h[y * W + x] = Math.min(PLATEAU, 6 * Math.hypot(x - 26, y - 48), 6 * Math.hypot(x - 70, y - 48))
  }
  for (let x = 0; x <= 16; x++) { const i = 48 * W + x; h[i] = Math.min(h[i], 60 - 0.5 * (16 - x)) }
  for (let x = 77; x < W; x++) { const i = 48 * W + x; h[i] = Math.min(h[i], 40 - 0.5 * (x - 77)) }
  return h
}

/** A monotone plane. No closed depression anywhere, therefore no lake anywhere. */
function plane() {
  const h = new Float32Array(N)
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) h[y * W + x] = PLATEAU * (1 - x / W)
  return h
}

;(async () => {
  let M = null, loadErr = null, pluginSrc = null
  try {
    const p = mutation ? (PATCHES[mutation] || {}) : {}
    if (!p.core) {
      M = await import(pathToFileURL(CORE).href)
    } else {
      // A data: URL module cannot resolve './hydrology.js', so the relative import is rewritten to an
      // absolute file URL. The hydrology module itself is untouched — only how it is reached.
      let text = fs.readFileSync(CORE, 'utf8')
        .replace("from './hydrology.js'", `from '${pathToFileURL(HYDRO).href}'`)
      text = patch(text, p.core, 'core')
      M = await import('data:text/javascript;base64,' + Buffer.from(text, 'utf8').toString('base64'))
    }
    pluginSrc = fs.readFileSync(PLUGIN, 'utf8')
    if (p.plugin) pluginSrc = patch(pluginSrc, p.plugin, 'plugin')
  } catch (e) { loadErr = String(e.message || e).slice(0, 300) }

  const assertions = []
  const check = (name, cond, detail) => { assertions.push({ name, ok: !!cond, detail }); return !!cond }
  let level = NaN, volErr = NaN, edtErrSq = NaN, edtErrHex = NaN, analyticDev = NaN
  if (!check('module loads', M !== null, loadErr)) return report()

  // === the analytic bowl, square lattice =======================================================
  const solid = bowl(false)
  const before = Float32Array.from(solid)
  const r = M.lakes(solid, W, H, { cellSizeM: CELL })

  // --- GUARDRAIL 1: no height was written -------------------------------------------------------
  // The story calls this the single most important assertion in the sprint. Compared bitwise, not
  // within a tolerance: a lake node that "only rounds" the terrain has still written to it.
  let solidChanged = 0
  for (let i = 0; i < N; i++) if (solid[i] !== before[i]) solidChanged++
  check('the Lake node writes no height: the terrain field is bit-identical before and after',
    solidChanged === 0, { solidChanged })

  // --- the fixture actually produced a lake -----------------------------------------------------
  // Absence of evidence is a failure. Every assertion below measures something about a water body;
  // if there is no water body they are all vacuously true.
  check('the analytic bowl produced exactly one lake', r.lakeCount === 1, { lakeCount: r.lakeCount })
  check('the lake has wet cells and a shoreline to measure',
    r.wetCount > 100 && r.shoreCount > 20 && r.basins.length === 1 && r.spills.length === 1,
    { wetCount: r.wetCount, shoreCount: r.shoreCount, basins: r.basins.length, spills: r.spills.length })
  if (!r.basins.length) return report()

  const basin = r.basins[0], spill = r.spills[0]
  level = basin.level

  // --- FLAT AT SPILL ----------------------------------------------------------------------------
  // Float32 IDENTITY, not a tolerance. Every wet cell is assigned the same number by the flood, so
  // any spread at all means something computed a per-cell value — which is what the routing fill's
  // 2e-7 flat tilt does, and it is invisible to any tolerance loose enough to be called "flat".
  let notFlat = 0, wetSeen = 0, minS = Infinity, maxS = -Infinity
  for (let i = 0; i < N; i++) {
    if (r.lakeId[i] !== 0) continue
    wetSeen++
    if (r.surface[i] !== level) notFlat++
    if (r.surface[i] < minS) minS = r.surface[i]
    if (r.surface[i] > maxS) maxS = r.surface[i]
  }
  check('the lake surface is one Float32 value across the whole water body',
    wetSeen > 100 && notFlat === 0, { wetSeen, notFlat, minSurface: minS, maxSurface: maxS })
  check('the lake surface has zero spread', maxS - minS === 0, { spread: maxS - minS })

  // ...and that value is the SPILL, bit-identically. This is the assertion a fixed-level fill fails.
  check('the lake level is bit-identical to the spill feature elevation',
    level === spill.elevation && level === basin.spillElevation,
    { level, spillElevation: spill.elevation })
  check('the lake level is the analytic notch elevation', level === SPILL, { level, analytic: SPILL })

  // --- THE SPILL SITS ON THE LOWEST RIM ---------------------------------------------------------
  // The rim is recomputed here from the label raster with this file's own neighbour offsets, so the
  // module's own idea of the rim is not what is being asserted against.
  const rim = new Set()
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x
    if (r.lakeId[i] !== 0) continue
    for (const d of nbOf(y, false)) {
      const xx = x + d[0], yy = y + d[1]
      if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue
      const ni = yy * W + xx
      if (r.lakeId[ni] !== 0) rim.add(ni)
    }
  }
  let rimMin = Infinity
  for (const c of rim) if (solid[c] < rimMin) rimMin = solid[c]
  check('the rim was found', rim.size > 20, { rimCells: rim.size })
  check('the spill sits on the lowest rim cell',
    rim.has(spill.index) && solid[spill.index] === rimMin && rimMin === level,
    { onRim: rim.has(spill.index), spillSolid: solid[spill.index], rimMin, level })
  // Ninety cells of shoreline sit at exactly 60 m; only one of them has anywhere lower to go. The
  // spill is the outlet, not just any cell tied at the fill elevation.
  check('the spill is the notch the water actually leaves through',
    spill.x === NOTCH_X && spill.y === NOTCH_Y, { spillX: spill.x, spillY: spill.y, notch: [NOTCH_X, NOTCH_Y] })

  // --- DEPTH ------------------------------------------------------------------------------------
  // Recomputed from the two OTHER outputs, so a depth produced from anything else fails here.
  let depthViolations = 0, wetDepth = 0, dryNonZero = 0
  for (let i = 0; i < N; i++) {
    if (r.depth[i] !== Math.fround(Math.max(0, r.surface[i] - solid[i]))) depthViolations++
    if (r.lakeId[i] === 0) { if (r.depth[i] > 0) wetDepth++ }
    else if (r.depth[i] !== 0) dryNonZero++
  }
  check('waterDepth equals max(0, surface - solidTop) exactly, every cell',
    depthViolations === 0, { depthViolations, N })
  check('depth is exactly zero everywhere outside the water body', dryNonZero === 0, { dryNonZero })
  check('every wet cell carries positive depth', wetDepth === wetSeen, { wetDepth, wetSeen })
  check('the deepest point is the analytic cone floor',
    Math.abs(basin.maxDepth - SPILL) < 1e-4, { maxDepth: basin.maxDepth, analytic: SPILL })

  // --- VOLUME against the closed-form cone integral ----------------------------------------------
  // V = integral over r < S/A of (S - A r) 2 pi r dr, in cell^2, times the cell area. Nothing about
  // this number is tunable: the fixture's slope and spill fix it.
  const Rs = SPILL / CONE
  const vAnalytic = 2 * Math.PI * (SPILL * Rs * Rs / 2 - CONE * Rs * Rs * Rs / 3) * CELL * CELL
  volErr = Math.abs(basin.volumeM3 - vAnalytic) / vAnalytic
  check('lake volume matches the closed-form cone integral', volErr < 1e-2,
    { volumeM3: +basin.volumeM3.toFixed(1), analytic: +vAnalytic.toFixed(1), relErr: +volErr.toExponential(3) })

  // --- LABELS ------------------------------------------------------------------------------------
  let badLabel = 0, dryLabelled = 0
  for (let i = 0; i < N; i++) {
    if (r.depth[i] > 0) { if (!(r.lakeId[i] >= 0 && r.lakeId[i] < r.lakeCount)) badLabel++ }
    else if (r.lakeId[i] !== M.NO_LAKE) dryLabelled++
  }
  check('every wet cell carries a label inside [0, lakeCount)', badLabel === 0, { badLabel })
  check('every dry cell carries NO_LAKE', dryLabelled === 0, { dryLabelled })
  check('NO_LAKE is the ports.js noLabel sentinel', M.NO_LAKE === -1, { NO_LAKE: M.NO_LAKE })

  // --- SHORE DISTANCE ----------------------------------------------------------------------------
  // The shoreline is derived here independently: a DRY cell touching water. Its zero is exact by
  // construction rather than interpolated, because waterDepth is identically zero on land.
  const shoreIdx = []
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x
    if (r.depth[i] > 0) continue
    for (const d of nbOf(y, false)) {
      const xx = x + d[0], yy = y + d[1]
      if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue
      if (r.depth[yy * W + xx] > 0) { shoreIdx.push(i); break }
    }
  }
  check('an independent shoreline was found', shoreIdx.length > 20, { shoreCells: shoreIdx.length })

  const onShore = new Uint8Array(N)
  for (const i of shoreIdx) onShore[i] = 1
  let signBad = 0, zeroBad = 0, posCount = 0, negCount = 0, zeroCount = 0
  for (let i = 0; i < N; i++) {
    const v = r.shoreDistance[i]
    if (v > 0) posCount++; else if (v < 0) negCount++; else zeroCount++
    if (onShore[i]) { if (v !== 0) zeroBad++ }
    else if (r.depth[i] > 0) { if (!(v > 0)) signBad++ }
    else if (!(v < 0)) signBad++
  }
  check('shore distance is exactly zero on the shoreline and nowhere else',
    zeroBad === 0 && zeroCount === shoreIdx.length, { zeroBad, zeroCount, shoreCells: shoreIdx.length })
  check('shore distance is positive in water and negative on land',
    signBad === 0 && posCount === wetSeen, { signBad, posCount, negCount, wetSeen })

  // EXACTLY EUCLIDEAN, checked against brute force over the independently derived shoreline. This is
  // the assertion that caught the real defect in the first build of this module: the separable
  // transform took only even rows as sources, and the worst cell was 60.8 m out on a 10 m lattice
  // while every sign and zero assertion above still passed.
  edtErrSq = bruteForceError(r.shoreDistance, shoreIdx, false)
  check('shore distance is exactly Euclidean on the square lattice', edtErrSq === 0,
    { maxErrorM: edtErrSq })

  // --- the analytic circle -----------------------------------------------------------------------
  // Away from the notch, the shoreline is the circle r = SPILL/CONE. The discrete shoreline is the
  // ring of dry cells just outside it, so a sample's signed distance can differ from the continuous
  // answer by at most one lattice step; CELL*sqrt(2) is that step, not a fitted tolerance. Measured
  // here: 12.79 m against a bound of 14.14 m, and 135 m when the cell size is dropped.
  const Ra = Rs * CELL
  analyticDev = 0
  let sampled = 0
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const rho = Math.hypot(x - 48, y - 48) * CELL
    if (rho > 25 * CELL) continue                       // the bowl, not the far plateau
    if (Math.abs(y - NOTCH_Y) <= 1 && x > 48) continue  // the notch channel is not part of the circle
    const dev = Math.abs(r.shoreDistance[y * W + x] - (Ra - rho))
    if (dev > analyticDev) analyticDev = dev
    sampled++
  }
  check('the analytic circle was sampled', sampled > 1000, { sampled })
  check('shore distance matches the analytic circular shoreline within one lattice step',
    analyticDev <= CELL * Math.SQRT2, { maxDeviationM: +analyticDev.toFixed(3), boundM: +(CELL * Math.SQRT2).toFixed(3) })

  // === the same bowl on the NORMALISED height scale ==============================================
  // See bowlUnit(): this is the only scale in the suite on which the routing fill's 2e-7 flat tilt is
  // representable in Float32 at all, so it is the only place a lake surface built from the routing
  // fill can be caught. The quantum fact is asserted rather than left as a remark, because if it ever
  // stopped holding the fixture would silently stop covering anything.
  check('the routing flat tilt is below the Float32 quantum at metre scale but not at unit scale',
    Math.fround(SPILL + 2e-7) === Math.fround(SPILL) && Math.fround(0.6 + 2e-7) !== Math.fround(0.6),
    { ulpAt60: Math.fround(SPILL) * Math.pow(2, -23), ulpAt0p6: Math.fround(0.6) * Math.pow(2, -23), tilt: 2e-7 })

  const unitSolid = bowlUnit()
  const unitBefore = Float32Array.from(unitSolid)
  const ur = M.lakes(unitSolid, W, H, { cellSizeM: CELL })
  let unitChanged = 0
  for (let i = 0; i < N; i++) if (unitSolid[i] !== unitBefore[i]) unitChanged++
  check('the Lake node writes no height on the normalised fixture', unitChanged === 0, { unitChanged })
  check('the normalised bowl produced one lake with wet cells',
    ur.lakeCount === 1 && ur.wetCount > 100 && ur.basins.length === 1,
    { lakeCount: ur.lakeCount, wetCount: ur.wetCount })
  const unitLevel = ur.basins.length ? ur.basins[0].level : NaN
  let unitNotFlat = 0, unitWet = 0, unitDryDepth = 0
  for (let i = 0; i < N; i++) {
    if (ur.lakeId[i] === 0) { unitWet++; if (ur.surface[i] !== unitLevel) unitNotFlat++ }
    else if (ur.depth[i] !== 0) unitDryDepth++
  }
  check('the normalised lake surface is one Float32 value across the whole water body',
    unitWet > 100 && unitNotFlat === 0, { unitWet, unitNotFlat, unitLevel })
  check('the normalised lake has exactly zero depth outside the water body',
    unitDryDepth === 0, { unitDryDepth })
  check('the normalised lake level is bit-identical to its spill elevation',
    ur.spills.length === 1 && unitLevel === ur.spills[0].elevation
    && unitLevel === Math.fround(SPILL / PLATEAU),
    { unitLevel, spill: ur.spills.length ? ur.spills[0].elevation : null, analytic: Math.fround(SPILL / PLATEAU) })

  // === the same bowl on a HEX lattice ============================================================
  // Odd hex rows sit half a column across. A separable distance transform that ignores that offset is
  // wrong by up to half a cell everywhere, which no sign or zero assertion can see.
  const solidHex = bowl(true)
  const beforeHex = Float32Array.from(solidHex)
  const rh = M.lakes(solidHex, W, H, { hex: true, cellSizeM: CELL })
  let hexChanged = 0
  for (let i = 0; i < N; i++) if (solidHex[i] !== beforeHex[i]) hexChanged++
  check('the Lake node writes no height on the hex lattice either', hexChanged === 0, { hexChanged })
  check('the hex bowl produced one lake with wet cells',
    rh.lakeCount === 1 && rh.wetCount > 100, { lakeCount: rh.lakeCount, wetCount: rh.wetCount })
  let hexNotFlat = 0
  const hexLevel = rh.basins.length ? rh.basins[0].level : NaN
  for (let i = 0; i < N; i++) if (rh.lakeId[i] === 0 && rh.surface[i] !== hexLevel) hexNotFlat++
  check('the hex lake surface is one Float32 value across the body', hexNotFlat === 0, { hexNotFlat, hexLevel })

  const hexShore = []
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = y * W + x
    if (rh.depth[i] > 0) continue
    for (const d of nbOf(y, true)) {
      const xx = x + d[0], yy = y + d[1]
      if (xx < 0 || yy < 0 || xx >= W || yy >= H) continue
      if (rh.depth[yy * W + xx] > 0) { hexShore.push(i); break }
    }
  }
  check('an independent hex shoreline was found', hexShore.length > 20, { hexShoreCells: hexShore.length })
  edtErrHex = bruteForceError(rh.shoreDistance, hexShore, true)
  check('shore distance is exactly Euclidean on the hex lattice, stagger included',
    edtErrHex === 0, { maxErrorM: edtErrHex })

  // === two basins, two levels, two ids ===========================================================
  const twoSolid = twin()
  const twoBefore = Float32Array.from(twoSolid)
  const two = M.lakes(twoSolid, W, H, { cellSizeM: CELL })
  let twoChanged = 0
  for (let i = 0; i < N; i++) if (twoSolid[i] !== twoBefore[i]) twoChanged++
  check('the Lake node writes no height on the two-basin fixture', twoChanged === 0, { twoChanged })
  check('two separated basins are two lakes', two.lakeCount === 2 && two.basins.length === 2,
    { lakeCount: two.lakeCount })
  if (two.basins.length === 2) {
    const [a, b] = two.basins
    check('the two lakes sit at different levels, each at its own spill',
      a.level !== b.level && a.level === a.spillElevation && b.level === b.spillElevation,
      { levelA: a.level, levelB: b.level, spillA: a.spillElevation, spillB: b.spillElevation })
    check('the two lakes are at the analytic notch elevations',
      a.level === 60 && b.level === 40, { levelA: a.level, levelB: b.level })
    let flatA = 0, flatB = 0, nA = 0, nB = 0
    for (let i = 0; i < N; i++) {
      if (two.lakeId[i] === 0) { nA++; if (two.surface[i] !== a.level) flatA++ }
      if (two.lakeId[i] === 1) { nB++; if (two.surface[i] !== b.level) flatB++ }
    }
    check('each lake is separately flat at its own level',
      nA > 50 && nB > 50 && flatA === 0 && flatB === 0, { nA, nB, flatA, flatB })
    check('the two label sets are disjoint and cover both bodies',
      nA === a.cellCount && nB === b.cellCount, { nA, cellCountA: a.cellCount, nB, cellCountB: b.cellCount })
  } else {
    check('the two lakes sit at different levels, each at its own spill', false, { lakeCount: two.lakeCount })
    check('the two lakes are at the analytic notch elevations', false, null)
    check('each lake is separately flat at its own level', false, null)
    check('the two label sets are disjoint and cover both bodies', false, null)
  }

  // --- the puddle floor --------------------------------------------------------------------------
  // Suppressing a lake must also UNDO its fill, or `depth = max(0, surface - solidTop)` stops holding
  // for those cells while every other assertion still passes.
  const supSolid = twin()
  const sup = M.lakes(supSolid, W, H, { cellSizeM: CELL, minCells: 200 })
  let supViolations = 0, supRaised = 0
  for (let i = 0; i < N; i++) {
    if (sup.depth[i] !== Math.fround(Math.max(0, sup.surface[i] - supSolid[i]))) supViolations++
    if (sup.lakeId[i] === M.NO_LAKE && sup.surface[i] !== supSolid[i]) supRaised++
  }
  check('a lake below the cell floor is suppressed, the larger one is kept',
    sup.lakeCount === 1 && sup.basins.length === 1 && sup.basins[0].cellCount >= 200,
    { lakeCount: sup.lakeCount, cellCount: sup.basins.length ? sup.basins[0].cellCount : -1 })
  check('a suppressed lake leaves the surface back on the terrain', supRaised === 0, { supRaised })
  check('the depth identity still holds exactly after suppression', supViolations === 0, { supViolations })

  // === no depression at all ======================================================================
  const flat = plane()
  const flatBefore = Float32Array.from(flat)
  const fr = M.lakes(flat, W, H, { cellSizeM: CELL })
  let surfaceMoved = 0, anyDepth = 0, anyPositiveShore = 0
  for (let i = 0; i < N; i++) {
    if (fr.surface[i] !== flatBefore[i]) surfaceMoved++
    if (fr.depth[i] !== 0) anyDepth++
    if (fr.shoreDistance[i] >= 0) anyPositiveShore++
  }
  const farM = Math.hypot(W * CELL, H * CELL)
  check('a monotone plane has no lake', fr.lakeCount === 0 && fr.wetCount === 0 && fr.basins.length === 0,
    { lakeCount: fr.lakeCount, wetCount: fr.wetCount })
  check('with no depression the water surface is bit-identical to the terrain',
    surfaceMoved === 0 && anyDepth === 0, { surfaceMoved, anyDepth })
  check('with no water every cell reads as dry, clamped to the domain diagonal',
    anyPositiveShore === 0 && Math.abs(fr.shoreDistance[0] + farM) < 1e-3,
    { anyPositiveShore, sample: fr.shoreDistance[0], farM: +farM.toFixed(2) })

  // === the plugin's port block ====================================================================
  const Ports = await import(pathToFileURL(PORTS).href)
  check('the Lake plugin source was read', typeof pluginSrc === 'string' && pluginSrc.length > 1000,
    { bytes: pluginSrc ? pluginSrc.length : 0 })
  const stripped = pluginSrc.replace(/^\s*\/\/.*$/gm, '')
  const ins = literalAfter(stripped, 'inputs:'), outs = literalAfter(stripped, 'outputs:')
  const pars = literalAfter(stripped, 'params:')
  let inputs = null, outputs = null, params = null, parseErr = null
  try {
    inputs = new Function('RANGE', 'return ' + ins)(Ports.RANGE)
    outputs = new Function('RANGE', 'return ' + outs)(Ports.RANGE)
    params = new Function('P', 'return ' + pars)({ slider: (id) => ({ id }) })
  } catch (e) { parseErr = String(e.message || e).slice(0, 200) }
  check('the Lake plugin port block parses', Array.isArray(inputs) && Array.isArray(outputs) && Array.isArray(params),
    { parseErr, inputs: inputs && inputs.length, outputs: outputs && outputs.length })

  if (Array.isArray(inputs) && Array.isArray(outputs)) {
    check('the Lake plugin declares one input and seven outputs',
      inputs.length === 1 && outputs.length === 7, { inputs: inputs.length, outputs: outputs.length })
    const primary = outputs.filter(p => p.primary)
    check('the primary output is the untouched solid top, not water',
      primary.length === 1 && primary[0].id === 'solidTop' && primary[0].semantic === 'solidTop'
      && primary[0].unit === 'm' && primary[0].lens === 'continued',
      { primary: primary.map(p => p.id) })
    // NO WATER-LEVEL PARAMETER. The story's armed failure is a node that fills to a slider; the only
    // knob here is the puddle floor, and this refuses to let a level knob appear later unnoticed.
    check('the Lake node exposes no water-level parameter',
      params.length === 1 && params[0].id === 'minCells', { params: params.map(p => p.id) })

    // Everything ports.js already knows must validate for real, today. `waterSurface`, `waterDepth`
    // and `shoreDistance` are the three semantics the story report asks to be added; until they land,
    // they are pinned here to the exact kind and unit that request specifies.
    const PENDING = { waterSurface: 'm', waterDepth: 'm', shoreDistance: 'm' }
    const known = p => !!(Ports.SEMANTICS[p.semantic] || Ports.GENERICS[p.semantic])
    const live = outputs.filter(known)
    const pending = outputs.filter(p => !known(p))
    check('every Lake input validates against ports.js',
      Ports.validatePortList({ inputs, outputs: [], source: 'declared' }).length === 0,
      Ports.validatePortList({ inputs, outputs: [], source: 'declared' }))
    check('every Lake output whose semantic ports.js already knows validates',
      live.length >= 4 && Ports.validatePortList({ inputs: [], outputs: live, source: 'declared' }).length === 0,
      { liveOutputs: live.map(p => p.id), problems: Ports.validatePortList({ inputs: [], outputs: live, source: 'declared' }) })
    check('the pending semantics are exactly the three the report asks ports.js for',
      pending.length === Object.keys(PENDING).length
      && pending.every(p => PENDING[p.semantic] !== undefined),
      { pending: pending.map(p => p.semantic), expected: Object.keys(PENDING) })
    check('each pending port declares the kind and unit the report specifies',
      pending.every(p => p.kind === 'scalarRaster' && p.storage === 'R32F' && p.unit === PENDING[p.semantic]),
      pending.map(p => ({ id: p.id, semantic: p.semantic, kind: p.kind, unit: p.unit })))
  } else {
    for (const n of ['the Lake plugin declares one input and seven outputs',
      'the primary output is the untouched solid top, not water',
      'the Lake node exposes no water-level parameter',
      'every Lake input validates against ports.js',
      'every Lake output whose semantic ports.js already knows validates',
      'the pending semantics are exactly the three the report asks ports.js for',
      'each pending port declares the kind and unit the report specifies']) check(n, false, 'port block did not parse')
  }

  check('assertion inventory non-empty', assertions.length >= 45, assertions.length)
  report()

  /** Max absolute difference between the module's |shoreDistance| and a brute-force nearest-source
   *  search over the shoreline this file derived. Exact, not sampled: every cell against every
   *  shoreline cell. */
  function bruteForceError(field, sources, hex) {
    let worst = 0
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const px = wx(x, y, hex), py = wy(y, hex)
      let best = Infinity
      for (let k = 0; k < sources.length; k++) {
        const s = sources[k], sy = (s / W) | 0, sx = s - sy * W
        const ddx = px - wx(sx, sy, hex), ddy = py - wy(sy, hex)
        const d2 = ddx * ddx + ddy * ddy
        if (d2 < best) best = d2
      }
      const e = Math.abs(Math.abs(field[y * W + x]) - Math.fround(Math.sqrt(best)))
      if (e > worst) worst = e
    }
    return worst
  }

  function literalAfter(src, key) {
    const at = src.indexOf(key)
    if (at < 0) return 'null'
    const start = src.indexOf('[', at)
    let depth = 0
    for (let i = start; i < src.length; i++) {
      if (src[i] === '[') depth++
      else if (src[i] === ']') { depth--; if (depth === 0) return src.slice(start, i + 1) }
    }
    return 'null'
  }

  function report() {
    let ok = assertions.every(a => a.ok)
    if (mutation) {
      if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
      ok = false
    }
    const failed = assertions.filter(a => !a.ok).map(a => a.name)
    console.log(`${ok ? 'PASS' : 'FAIL'}  lake level=${level} volRelErr=${Number.isFinite(volErr) ? volErr.toExponential(2) : 'n/a'} `
      + `edtErrSquare=${edtErrSq} edtErrHex=${edtErrHex} analyticDevM=${Number.isFinite(analyticDev) ? analyticDev.toFixed(2) : 'n/a'} `
      + `assertions=${assertions.length} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
    if (!ok || process.env.MC_VERBOSE) console.log(JSON.stringify(assertions.filter(a => !a.ok), null, 2))
    process.exit(ok ? 0 : 1)
  }
})().catch(e => { console.error('FATAL', e.stack || e); process.exit(2) })
