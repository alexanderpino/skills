// S9.1 — versioned world-domain schema and legacy migration.
//
// The migration's job is to change the SCHEMA without changing the TERRAIN. A document saved before
// this story must open with numerically identical output, which is why `posting: legacy-cell`
// exists at all: legacy spacing spans n cells, vertex posting spans n-1 intervals, and confusing
// the two shifts every sample by half a cell. That is asserted numerically here, not asserted of.
//
// The other property worth a gate is HONESTY about rounding. Spacing mode must derive an integral
// sample count, so the achieved spacing is almost never the requested one, and ADR-007 specifically
// forbids displaying the request as though it were achieved.
const { chromium } = require('playwright-core')
const path = require('path')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'legacy-becomes-vertex',
  'silent-rounding',
  'square-height-forced',
  'accept-single-sample-axis',
  'domain-not-persisted',
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
    USE_GPU = false; RES = 256; TARGET_RES = 256; terrainDef.lattice = 'square'
    const out = { mutation: mutation || null }
    const D = DOMAIN

    // --- legacy migration preserves the numbers -----------------------------------------------
    let legacy = D.domainFromLegacy({ scale: 5000, height: 2600, baseElevation: 0, lattice: 'square' }, 512)
    if (mutation === 'legacy-becomes-vertex') legacy = { ...legacy, posting: 'vertex' }
    const intervals = legacy.posting === 'vertex' ? 511 : 512
    out.legacy = {
      posting: legacy.posting,
      spacing: legacy.resolution.actualSpacingM.x,
      // The current evaluator's spacing is exactly scale/RES. Anything else is a moved sample.
      matchesLegacyEvaluator: Math.abs(legacy.resolution.actualSpacingM.x - 5000 / 512) < 1e-12,
      derivedMatches: Math.abs(5000 / intervals - legacy.resolution.actualSpacingM.x) < 1e-12,
      problems: D.validateDomain(legacy).length,
      verticalRange: legacy.vertical.rangeM,
      datumKind: legacy.vertical.datum.kind,
    }

    // Hex is truthfully rectangular: rows sit sqrt(3)/2 apart, so its metre height is NOT `scale`.
    const rows = Math.round(512 * 2 / Math.sqrt(3))
    let hex = D.domainFromLegacy({ scale: 5000, height: 2600, baseElevation: 0, lattice: 'hex' }, 512, rows)
    if (mutation === 'square-height-forced') hex = { ...hex, extentM: { width: 5000, height: 5000 } }
    out.hex = {
      rows: hex.resolution.sampleCount.rows,
      height: hex.extentM.height,
      // Squashing hex rows to keep a square footprint is silent metric anisotropy.
      rectangular: Math.abs(hex.extentM.height - 5000) > 1,
      problems: D.validateDomain(hex).length,
    }

    // --- arbitrary dimensions, the point of the story -----------------------------------------
    const arb = {
      version: 1, originM: { x: 0, y: 0 }, extentM: { width: 15720, height: 137880 },
      authoringUnits: { horizontal: 'm', vertical: 'm' }, lattice: 'square', posting: 'vertex',
      resolution: { mode: 'explicit-samples', sampleCount: { columns: 1573, rows: 13789 }, actualSpacingM: { x: 10, y: 10 } },
      vertical: { datum: { kind: 'unknown', offsetM: 0 }, rangeM: { min: 0, max: 2600 } },
    }
    const derived = D.deriveResolution(arb)
    out.arbitrary = {
      columns: derived.sampleCount.columns, rows: derived.sampleCount.rows,
      spacingX: derived.actualSpacingM.x, spacingY: derived.actualSpacingM.y,
      independentAxes: derived.sampleCount.columns !== derived.sampleCount.rows,
      problems: D.validateDomain(arb).length,
    }
    // 16384 square must also express cleanly.
    const big = { ...arb, extentM: { width: 163830, height: 163830 }, resolution: { mode: 'explicit-samples', sampleCount: { columns: 16384, rows: 16384 }, actualSpacingM: { x: 10, y: 10 } } }
    out.sixteenK = { problems: D.validateDomain(big).length, spacing: D.deriveResolution(big).actualSpacingM.x }

    // --- honesty about rounding ----------------------------------------------------------------
    const sp = { ...arb, resolution: { mode: 'spacing', requestedSpacingM: { x: 7, y: 7 }, actualSpacingM: { x: 0, y: 0 } } }
    const spDerived = D.deriveResolution(sp)
    sp.resolution.actualSpacingM = spDerived.actualSpacingM
    let flagged = D.spacingWasRounded(sp)
    if (mutation === 'silent-rounding') flagged = false
    out.rounding = {
      requested: 7, actual: spDerived.actualSpacingM.x, flagged,
      integralSamples: Number.isInteger(spDerived.sampleCount.columns) && Number.isInteger(spDerived.sampleCount.rows),
      // An exact division must NOT be flagged, or the warning means nothing.
      exactNotFlagged: (() => {
        const ex = { ...arb, resolution: { mode: 'spacing', requestedSpacingM: { x: 10, y: 10 }, actualSpacingM: { x: 0, y: 0 } } }
        ex.resolution.actualSpacingM = D.deriveResolution(ex).actualSpacingM
        return D.spacingWasRounded(ex) === false
      })(),
    }

    // --- validation ----------------------------------------------------------------------------
    let oneSample = D.validateDomain({ ...arb, resolution: { mode: 'explicit-samples', sampleCount: { columns: 1, rows: 4 }, actualSpacingM: { x: 1, y: 1 } } }).map(p => p.code)
    if (mutation === 'accept-single-sample-axis') oneSample = []
    out.validation = {
      oneSample,
      negativeExtent: D.validateDomain({ ...arb, extentM: { width: -1, height: 10 } }).map(p => p.code),
      invertedVertical: D.validateDomain({ ...arb, vertical: { datum: { kind: 'unknown', offsetM: 0 }, rangeM: { min: 10, max: 0 } } }).map(p => p.code),
      unknownLattice: D.validateDomain({ ...arb, lattice: 'triangular' }).map(p => p.code),
    }

    // --- persistence and the v2 -> v3 migration ------------------------------------------------
    blankGraph()
    let text = saveProjectText()
    const parsed = JSON.parse(text)
    out.persistence = { version: parsed.schemaVersion, hasDomain: !!parsed.domain }
    // Build a v2 document by hand — what every graph saved before this story looks like.
    const v2 = JSON.parse(text)
    v2.schemaVersion = 2
    delete v2.domain
    if (mutation === 'domain-not-persisted') delete parsed.domain
    let migErr = null, migrated = null
    try { loadProjectText(JSON.stringify(v2, null, 2) + '\n'); migrated = JSON.parse(saveProjectText()) }
    catch (e) { migErr = e.code || String(e) }
    out.migration = {
      err: migErr,
      version: migrated ? migrated.schemaVersion : null,
      posting: migrated && migrated.domain ? migrated.domain.posting : null,
      gainedDomain: !!(migrated && migrated.domain),
      // The upgraded document must be numerically the legacy one: legacy-cell posting.
      preservesPosting: !!(migrated && migrated.domain && migrated.domain.posting === 'legacy-cell'),
      domainPersisted: mutation === 'domain-not-persisted' ? false : !!parsed.domain,
    }
    return out
  }, mutation)

  const gates = {
    legacySpacingMatchesEvaluator: report.legacy.matchesLegacyEvaluator === true && report.legacy.derivedMatches === true,
    legacyPostingIsLegacyCell: report.legacy.posting === 'legacy-cell',
    legacyDomainValid: report.legacy.problems === 0,
    unknownDatumStaysUnknown: report.legacy.datumKind === 'unknown',
    hexIsTruthfullyRectangular: report.hex.rectangular === true && report.hex.problems === 0,
    arbitraryDimensionsExpressible: report.arbitrary.problems === 0 && report.arbitrary.independentAxes === true
      && report.arbitrary.columns === 1573 && report.arbitrary.rows === 13789,
    sixteenKExpressible: report.sixteenK.problems === 0,
    roundingIsFlagged: report.rounding.flagged === true && report.rounding.integralSamples === true,
    exactSpacingNotFlagged: report.rounding.exactNotFlagged === true,
    singleSampleAxisRefused: report.validation.oneSample.includes('DOMAIN_SAMPLES_INVALID'),
    negativeExtentRefused: report.validation.negativeExtent.includes('DOMAIN_EXTENT_INVALID'),
    invertedVerticalRefused: report.validation.invertedVertical.includes('DOMAIN_VERTICAL_INVALID'),
    unknownLatticeRefused: report.validation.unknownLattice.includes('DOMAIN_LATTICE_UNKNOWN'),
    domainPersisted: report.persistence.hasDomain === true && report.persistence.version === 3
      && report.migration.domainPersisted === true,
    v2MigratesAndPreservesPosting: report.migration.gainedDomain === true && report.migration.version === 3
      && report.migration.preservesPosting === true,
    evidenceNonEmpty: report.legacy.spacing > 0 && report.arbitrary.spacingX > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  world domain legacySpacing=${report.legacy.spacing} posting=${report.legacy.posting} `
    + `arb=${report.arbitrary.columns}x${report.arbitrary.rows} rounded=${report.rounding.actual} `
    + `v2->v3=${report.migration.version} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ ...report, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
