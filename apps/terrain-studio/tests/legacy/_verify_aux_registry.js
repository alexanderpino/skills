// S2.4 — the auxiliary-map registry and the side-channel debt ledger.
//
// A ledger that is merely written down is documentation, and documentation drifts. The gate that
// makes this one real is that it is compared against a LIVE SCAN of the plugin sources on every
// run: a new `nd._something = ...` appears in the scan, not in the ledger, and the run goes red.
// Without that, the debt ADR-002 exists to drain could quietly grow while the file claimed it was
// shrinking.
//
// Two independent halves:
//   Node side  — static scan of src/plugins/**\/*.js, and the digest's own AUX/SCALARS tables
//   Page side  — the registry as the app actually loaded it
const { chromium } = require('playwright-core')
const path = require('path')
const fs = require('fs')

const EXE = process.env.STUDIO_CHROME || (process.platform === 'win32'
  ? 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'
  : '/opt/pw-browsers/chromium-1194/chrome-linux/chrome')
const URL = process.env.STUDIO_URL || ('file://' + path.resolve(__dirname, '../../index.html'))
const APP = path.resolve(__dirname, '../..')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'undeclared-side-channel', // a new nd._x = ... that the ledger does not know about
  'ledger-grew',             // the ledger gains a row instead of shrinking
  'gated-flag-wrong',        // a row claims gated where the digest's AUX table disagrees
  'lens-conflict-allowed',   // a derived map accepted as continued
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// The measured scan. This regex is the definition of "side channel" for this gate.
function scanSideChannels() {
  const rows = []
  const base = path.join(APP, 'src/plugins')
  for (const cat of fs.readdirSync(base)) {
    const dir = path.join(base, cat)
    if (!fs.statSync(dir).isDirectory()) continue
    for (const file of fs.readdirSync(dir)) {
      if (!file.endsWith('.js') || file === 'index.js') continue
      const src = fs.readFileSync(path.join(dir, file), 'utf8')
      const type = (src.match(/type:\s*["']([a-z0-9_]+)["']/i) || [])[1]
      if (!type) continue
      const re = /\b(?:nd|node)\.(_[A-Za-z0-9]+)\s*=(?!=)/g
      const seen = new Set()
      let m
      while ((m = re.exec(src))) seen.add(m[1])
      for (const ch of [...seen].sort()) rows.push(`${type}.${ch}`)
    }
  }
  if (mutation === 'undeclared-side-channel') rows.push('perlin._smuggledField')
  return rows.sort()
}

// The digest's own AUX/SCALARS tables — the authority for whether a channel is gated.
function scanDigestGated() {
  const src = fs.readFileSync(path.join(APP, 'tests/legacy/_verify_digest.js'), 'utf8')
  const gated = new Set()
  for (const table of ['AUX', 'SCALARS']) {
    const i = src.indexOf(`const ${table} = {`)
    if (i < 0) continue
    const body = src.slice(i, src.indexOf('};', i))
    const re = /(\w+):\s*\[([^\]]*)\]/g
    let m
    while ((m = re.exec(body))) {
      for (const raw of m[2].split(',')) {
        const name = raw.trim().replace(/^['"]|['"]$/g, '')
        if (!name) continue
        gated.add(`${m[1]}.${name.split('.')[0]}`)
      }
    }
  }
  return gated
}

;(async () => {
  const scanned = scanSideChannels()
  const digestGated = scanDigestGated()

  const browser = await chromium.launch({ executablePath: EXE,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'] })
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const errors = []
  page.on('pageerror', e => { if (e.message !== 'WebSocket closed without opened.') errors.push(e.message) })
  await page.goto(URL, { waitUntil: 'load' })
  await page.waitForTimeout(1400)

  const reg = await page.evaluate(mutation => {
    const { AUX_MAPS, SIDE_CHANNEL_LEDGER, AUX_LENSES, semanticDebt, debtByOwner, validateAuxDeclaration } = AUXMAPS
    const ledger = SIDE_CHANNEL_LEDGER.map(r => ({ ...r }))
    if (mutation === 'ledger-grew') ledger.push({ node: 'perlin', channel: '_new', lens: 'semantic', targetPort: null, gated: false, owner: 'none' })
    if (mutation === 'gated-flag-wrong') { const r = ledger.find(x => x.node === 'snow' && x.channel === '_snowLayer'); if (r) r.gated = false }
    const lensProblems = validateAuxDeclaration('slope', { lens: 'continued' }).map(p => p.code)
    return {
      mapCount: Object.keys(AUX_MAPS).length,
      lenses: AUX_LENSES.slice(),
      lensCounts: AUX_LENSES.map(l => [l, Object.values(AUX_MAPS).filter(m => m.lens === l).length]),
      ledger,
      ledgerKeys: ledger.map(r => `${r.node}.${r.channel}`).sort(),
      semanticDebt: semanticDebt().length,
      debtByOwner: Object.entries(debtByOwner()).map(([k, v]) => [k, v.length]),
      // A derived map declared continued must be refused; a derived map declared derived accepted.
      lensConflictDetected: mutation === 'lens-conflict-allowed' ? false : lensProblems.includes('AUX_LENS_CONFLICT'),
      lensAgreementAccepted: validateAuxDeclaration('snowDepth', { lens: 'continued' }).length === 0,
      unknownMapRefused: validateAuxDeclaration('notAMap').map(p => p.code).includes('AUX_UNKNOWN_MAP'),
    }
  }, mutation)

  // The ledger must describe exactly what the sources do — no more, no less.
  const undeclared = scanned.filter(k => !reg.ledgerKeys.includes(k))
  const stale = reg.ledgerKeys.filter(k => !scanned.includes(k))
  // Every row claiming `gated` must actually appear in the digest's AUX/SCALARS tables, and every
  // channel that IS in those tables must be marked gated. Both directions, because a row wrongly
  // marked gated blocks a migration that is safe, and one wrongly unmarked invites a silent drift.
  const gatedWrong = reg.ledger.filter(r => {
    const key = `${r.node}.${r.channel}`
    return !!r.gated !== digestGated.has(key)
  }).map(r => `${r.node}.${r.channel} ledger=${r.gated} digest=${digestGated.has(`${r.node}.${r.channel}`)}`)

  const gates = {
    ledgerMatchesSources: undeclared.length === 0 && stale.length === 0,
    // Frozen. This number may only ever go DOWN, as stories migrate fields to real ports.
    ledgerHasNotGrown: reg.ledger.length <= 25,
    gatedFlagsMatchDigest: gatedWrong.length === 0,
    everyMapHasAKnownLens: reg.lensCounts.reduce((a, [, n]) => a + n, 0) === reg.mapCount,
    lensConflictRefused: reg.lensConflictDetected === true,
    lensAgreementAccepted: reg.lensAgreementAccepted === true,
    unknownMapRefused: reg.unknownMapRefused === true,
    // Absence of evidence is failure: a scan that matched nothing proves nothing.
    evidenceNonEmpty: scanned.length > 0 && reg.mapCount > 0 && digestGated.size > 0,
  }

  let ok = Object.values(gates).every(Boolean) && !errors.length
  if (mutation) {
    if (ok) console.error(`FAIL mutation ${mutation} was not detected — that gate is vacuous`)
    ok = false
  }
  const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)
  console.log(`${ok ? 'PASS' : 'FAIL'}  aux registry maps=${reg.mapCount} ledger=${reg.ledger.length} scanned=${scanned.length} `
    + `semanticDebt=${reg.semanticDebt} gatedInDigest=${digestGated.size} failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
  console.log(JSON.stringify({ mutation, scanned, undeclared, stale, gatedWrong, reg, gates, errors, ok }, null, 2))
  await browser.close()
  process.exit(ok ? 0 : 1)
})().catch(error => { console.error('FATAL', error.stack || error); process.exit(2) })
