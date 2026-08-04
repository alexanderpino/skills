// S9.3 — import identity and provenance. Gate for src/core/height-source.js.
//
// No browser. The module under test is pure, DOM-free and zero-dependency, so this oracle runs
// under plain node like _verify_shapescan.js. That is not just faster: a Playwright run would put
// a canvas between this gate and the bytes, and a canvas is precisely the component that destroys
// the evidence S9.3 has to report.
//
// ---------------------------------------------------------------------------------------------
// WHERE THE ANSWERS COME FROM — every one of them is external to the module under test
//
//   SHA-256      the published FIPS 180-4 / NIST CSRC example vectors ("", "abc", the 448-bit and
//                896-bit multi-block messages, one million 'a'), plus padding-boundary lengths
//                54,55,56,57,63,64,65,119,120,121 whose digests were taken from Python's hashlib.
//                Not one of them is computed by this file.
//
//   REAL DEM     src/legacy.js's REAL_DEM_SAMPLE constant — a real SRTM extract that already ships.
//                Measured with Python (base64 + struct unpack of the IHDR at its spec-defined
//                offsets): 9327 bytes, sha256 98a23a24…, 128x128, bit depth 8, colour type 0,
//                interlace 0. Those numbers are pinned below and this file never recomputes them.
//
//   FIXTURES     tests/legacy/fixtures/*, written by Pillow 12.2 and by a hand-rolled Adam7
//                encoder, then READ BACK WITH PILLOW and compared pixel-for-pixel before being
//                accepted — so interlaced8.png is a genuinely interlaced PNG and dem8be.tif is a
//                genuinely big-endian TIFF, not a header with a flipped byte. Their byte lengths,
//                digests and IHDR fields were measured by the same Python struct unpack.
//
// A note on WHY a 16-bit fixture is worth carrying: dem16.png holds 6912 distinct sample levels
// (measured with numpy). An 8-bit canvas readback can represent 256. The information the bit-depth
// field describes is real, and the shipped decode path really does throw it away.
//
// ---------------------------------------------------------------------------------------------
// HOW THE CONTROLS PERTURB PRODUCTION
//
// A recent audit of this suite found eleven controls that mutated the ORACLE'S OWN COPY of the
// answer and therefore proved nothing. Nothing of that shape is allowed here. Every --mutate
// rewrites the PRODUCTION SOURCE of src/core/height-source.js — reproducing a defect that has
// really shipped, or that S9.3 names — and the gates below then read what that defective module
// actually does. No gate's expected value is ever assigned by a mutation.
//
// The rewrite is kept honest by `harnessModelsProduction`, which runs on EVERY invocation: the
// same loader, given the UNPATCHED source, must produce the same export names, the same digest and
// the same record as `require()`ing the real file. If the transform ever stopped modelling
// production, that gate goes red before any verdict is printed.
const fs = require('fs')
const path = require('path')

const APP_ROOT = path.resolve(__dirname, '../../')
const MODULE_PATH = path.join(APP_ROOT, 'src/core/height-source.js')
const LEGACY_PATH = path.join(APP_ROOT, 'src/legacy.js')
const FIXTURE_DIR = path.join(__dirname, 'fixtures')

const mutation = (process.argv.find(v => v.startsWith('--mutate=')) || '').slice(9) || process.env.MC_MUTATION || null
const MUTATIONS = [
  'sha-truncates-tail',        // hash only byteLength>>>2 words — the shape that shipped in subgraph.js:149
  'format-from-extension',     // dispatch on the filename instead of the magic number
  'bitdepth-from-canvas',      // report 8 unconditionally, as a Uint8ClampedArray readback would
  'default-labelled-embedded', // a Terrain Studio default claims it was read from the file
  'ihdr-defaults-on-malformed',// an unreadable header yields defaults instead of a refusal
  'physical-fields-guessed',   // fabricate cell spacing and a datum no PNG carries
  'geotiff-guessed-as-png',    // a TIFF is reported as a supported PNG rather than refused
]
if (mutation && !MUTATIONS.includes(mutation)) { console.error(`Unknown mutation ${mutation}`); process.exit(2) }

// ---------------------------------------------------------------------------------------------
// The patches. Each `find` is asserted to occur EXACTLY ONCE in production, so a mutation can
// never silently apply to nothing (a no-op patch would read as coverage and is the thing gate.py
// calls NOT ARMED).
// ---------------------------------------------------------------------------------------------
const PATCHES = {
  // fieldKey (src/core/subgraph.js:149) hashes `new Uint32Array(buffer, offset, byteLength >>> 2)`
  // — whole 32-bit words only. Any tail shorter than a word is dropped. Reproduce that here.
  'sha-truncates-tail': {
    find: 'export function sha256Hex(bytes) {\n  const view = asByteView(bytes)\n  const len = view.length',
    replace: 'export function sha256Hex(bytes) {\n  const full = asByteView(bytes)\n'
      + '  const view = full.subarray(0, (full.byteLength >>> 2) * 4)\n  const len = view.length',
  },
  // The pre-fix import path branched on `name.endsWith(".r16")` etc (src/legacy.js:4588) and never
  // looked at a magic number at all.
  'format-from-extension': {
    find: '  const sniff = sniffFormat(b)',
    replace: "  const ext = String(filename || '').toLowerCase().split('.').pop()\n"
      + "  const sniff = ext === 'png'\n"
      + "    ? Object.freeze({ format: 'png', supported: true, reason: null, byteOrder: 'big', magic: '(extension)', magicLength: 8 })\n"
      + "    : (ext === 'tif' || ext === 'tiff')\n"
      + "      ? Object.freeze({ format: 'tiff', supported: false, reason: 'GEOTIFF_UNSUPPORTED', byteOrder: 'little', magic: '(extension)', magicLength: 4 })\n"
      + "      : Object.freeze({ format: 'unknown', supported: false, reason: 'UNRECOGNISED_MAGIC', byteOrder: null, magic: '(extension)', magicLength: 1 })",
  },
  // What the shipped canvas readback effectively reports for every file it decodes.
  'bitdepth-from-canvas': {
    find: '  const bitDepth = b[IHDR_FIELD_AT.bitDepth]',
    replace: '  const bitDepth = 8',
  },
  // S9.3\'s named armed failure: a value Terrain Studio chose, labelled as read from the file.
  'default-labelled-embedded': {
    find: "    heightEncoding: defaultFact('luminance-normalised-0-1',",
    replace: "    heightEncoding: embeddedFact('luminance-normalised-0-1',",
  },
  // Swallow the refusal and hand back plausible numbers — the exact behaviour readPngHeader's
  // contract exists to forbid.
  'ihdr-defaults-on-malformed': {
    find: 'export function readPngHeader(bytes) {',
    replace: 'export function readPngHeader(bytes) {\n'
      + '  try { return readPngHeaderStrict(bytes) }\n'
      + '  catch (e) { return Object.freeze({ width: 256, height: 256, bitDepth: 8, colorType: 0, compression: 0, filter: 0, interlace: 0 }) }\n'
      + '}\n'
      + 'function readPngHeaderStrict(bytes) {',
  },
  // Fabricated geospatial facts, stamped 'embedded' with a citation that points at bytes which say
  // nothing of the kind. This is the failure the provenance rule exists for.
  'physical-fields-guessed': {
    find: '  for (const [key, why] of Object.entries(PHYSICAL_UNKNOWNS)) record[key] = unknownFact(why)',
    replace: '  for (const [key, why] of Object.entries(PHYSICAL_UNKNOWNS)) record[key] = unknownFact(why)\n'
      + "  record.cellSpacing = embeddedFact(30, { from: 'IHDR', at: IHDR_FIELD_AT.width, length: 4 })\n"
      + "  record.verticalDatum = embeddedFact('EGM96', { from: 'IHDR', at: IHDR_FIELD_AT.width, length: 4 })",
  },
  // Guess rather than refuse.
  'geotiff-guessed-as-png': {
    find: "      format: 'tiff', supported: false, reason: 'GEOTIFF_UNSUPPORTED',",
    replace: "      format: 'png', supported: true, reason: null,",
  },
}

// ---------------------------------------------------------------------------------------------
// Loading production, patched or not
// ---------------------------------------------------------------------------------------------
const EXPORT_RE = /^export\s+(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)/gm

function exportedNames(src) {
  const names = []
  EXPORT_RE.lastIndex = 0
  let m
  while ((m = EXPORT_RE.exec(src))) names.push(m[1])
  return names
}

/**
 * Evaluate the module's own source as a CommonJS-visible namespace. The module imports nothing, so
 * stripping the `export` keyword off its declarations is a complete transform — and the fidelity
 * gate proves that claim on every run rather than asserting it here.
 */
function loadFromSource(src) {
  const names = exportedNames(src)
  const body = src.replace(/^export\s+(?=(?:const|let|var|function|class)\b)/gm, '')
  return new Function(`"use strict";\n${body}\nreturn { ${names.join(', ')} };`)()
}

const setupProblems = []
const SRC = fs.readFileSync(MODULE_PATH, 'utf8')
const REAL = require('../../src/core/height-source.js')

let patchApplied = null
let PROD = REAL
if (mutation) {
  const patch = PATCHES[mutation]
  const hits = SRC.split(patch.find).length - 1
  if (hits !== 1) {
    setupProblems.push(`patch anchor for ${mutation} matched ${hits} times, expected exactly 1`)
  } else {
    const patched = SRC.split(patch.find).join(patch.replace)
    if (patched === SRC) setupProblems.push(`patch for ${mutation} changed nothing`)
    patchApplied = { chars: patched.length - SRC.length }
    PROD = loadFromSource(patched)
  }
}

// ---------------------------------------------------------------------------------------------
// Corpus
// ---------------------------------------------------------------------------------------------

// Measured with Python, NOT with the module under test. See the header for the method.
const REAL_DEM = { byteLength: 9327, sha256: '98a23a24a00642958f2e553c64a75b63dcd6c39b9afd76cfcaf31dce22b7e3c0',
  format: 'png', width: 128, height: 128, bitDepth: 8, colorType: 0, interlace: 0 }

const FIXTURES = {
  'dem16.png': { byteLength: 898, sha256: '99f1f9e3471fc85bc38e82119715bb8599709e2cff0b91db77eaffaf1ad6b511',
    format: 'png', width: 96, height: 72, bitDepth: 16, colorType: 0, interlace: 0 },
  'dem8rgb.png': { byteLength: 2972, sha256: '440841cf32d800b5b8ccfff9b4403b990c770d50861e267b24f4f0397b9ea8ce',
    format: 'png', width: 40, height: 24, bitDepth: 8, colorType: 2, interlace: 0 },
  'interlaced8.png': { byteLength: 666, sha256: '7c326a0d7edf2e9da6a53f580bdf159c287bef3b6a3e4a3b855ad2399d371a0b',
    format: 'png', width: 28, height: 20, bitDepth: 8, colorType: 0, interlace: 1 },
  'dem16le.tif': { byteLength: 914, sha256: '677ebe6e15fb0582203d097eca03d4cfbf06730dff920892f3cfd70233fa5a44',
    format: 'tiff', byteOrder: 'little' },
  'dem8be.tif': { byteLength: 314, sha256: '4bc3b66231f9315d412749ca15e64b7e6c94c79264b2cec90e87cd4786beea30',
    format: 'tiff', byteOrder: 'big' },
}

const corpus = new Map()
let legacySrc = ''
try {
  legacySrc = fs.readFileSync(LEGACY_PATH, 'utf8')
  const m = legacySrc.match(/const REAL_DEM_SAMPLE\s*=\s*"data:image\/png;base64,([A-Za-z0-9+/=]+)"/)
  if (!m) setupProblems.push('REAL_DEM_SAMPLE not found in src/legacy.js — the corpus lost its real DEM')
  else corpus.set('REAL_DEM_SAMPLE', new Uint8Array(Buffer.from(m[1], 'base64')))
} catch (e) { setupProblems.push('could not read src/legacy.js: ' + e.message) }

for (const name of Object.keys(FIXTURES)) {
  try { corpus.set(name, new Uint8Array(fs.readFileSync(path.join(FIXTURE_DIR, name)))) }
  catch (e) { setupProblems.push(`fixture ${name} unreadable: ${e.message}`) }
}

const expected = name => (name === 'REAL_DEM_SAMPLE' ? REAL_DEM : FIXTURES[name])

// ---------------------------------------------------------------------------------------------
// Oracle-side helpers. These are the INDEPENDENT readers: they re-derive from raw bytes what the
// module claims, using arithmetic written here, so a citation can be checked against reality
// rather than against the module's own opinion.
// ---------------------------------------------------------------------------------------------
const be32 = (b, at) => ((b[at] << 24) | (b[at + 1] << 16) | (b[at + 2] << 8) | b[at + 3]) >>> 0
const PNG_SIG = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]

let CRC_TABLE = null
function crc32(bytes, from, to) {
  if (!CRC_TABLE) {
    CRC_TABLE = new Uint32Array(256)
    for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1); CRC_TABLE[n] = c >>> 0 }
  }
  let c = 0xffffffff
  for (let i = from; i < to; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8)
  return (c ^ 0xffffffff) >>> 0
}
/** Rewrite an IHDR byte and repair the chunk CRC, so the SPEC check is what fires, not the CRC one. */
function withIhdrByte(src, offset, value) {
  const b = src.slice()
  b[offset] = value
  const crc = crc32(b, 12, 29)
  b[29] = (crc >>> 24) & 255; b[30] = (crc >>> 16) & 255; b[31] = (crc >>> 8) & 255; b[32] = crc & 255
  return b
}
const bytesOf = s => new Uint8Array(Buffer.from(s, 'utf8'))
const thrown = fn => { try { fn(); return null } catch (e) { return e.code || e.name || String(e) } }

const report = { mutation: mutation || null, patchApplied, setupProblems }

// ---------------------------------------------------------------------------------------------
// 0. HARNESS FIDELITY — the loader must model production before anything it loads is believed
// ---------------------------------------------------------------------------------------------
const REPLAY = loadFromSource(SRC)
const demBytes = corpus.get('REAL_DEM_SAMPLE') || new Uint8Array([0])
const namesMatch = JSON.stringify(Object.keys(REAL).sort()) === JSON.stringify(Object.keys(REPLAY).sort())
const digestMatch = REPLAY.sha256Hex(bytesOf('abc')) === REAL.sha256Hex(bytesOf('abc'))
const recordMatch = JSON.stringify(REPLAY.describeSource({ bytes: demBytes, filename: 'a.png' }))
  === JSON.stringify(REAL.describeSource({ bytes: demBytes, filename: 'a.png' }))
report.harness = { exportCount: Object.keys(REAL).length, namesMatch, digestMatch, recordMatch }

// ---------------------------------------------------------------------------------------------
// 1. CORPUS — absence of evidence is a failure
// ---------------------------------------------------------------------------------------------
const digests = [...corpus.keys()].map(k => expected(k).sha256)
const lengthsAgree = [...corpus.entries()].every(([k, b]) => b.length === expected(k).byteLength)
// The tail pair for `sha-truncates-tail`: the real DEM and a copy differing ONLY in its last byte.
// 9327 % 4 === 3, so the last three bytes fall outside the whole 32-bit words a `byteLength >>> 2`
// hash would read. A length that is a multiple of 4 would make the defect invisible — that is
// exactly why it survived in subgraph.js, and why the pair is built from this file and not another.
const tailA = demBytes
const tailB = demBytes.slice(); tailB[tailB.length - 1] ^= 0xff
let diffCount = 0, diffAt = -1
for (let i = 0; i < tailA.length; i++) if (tailA[i] !== tailB[i]) { diffCount++; diffAt = i }
report.corpus = {
  files: corpus.size,
  distinctDigests: new Set(digests).size,
  lengthsAgree,
  tailPair: { length: tailA.length, mod4: tailA.length % 4, diffCount, diffAt, lastIndex: tailA.length - 1 },
}

// ---------------------------------------------------------------------------------------------
// 2. SHA-256 against published vectors
// ---------------------------------------------------------------------------------------------
const NIST = [
  ['', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'],
  ['abc', 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'],
  ['abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq',
    '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1'],
  ['abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu',
    'cf5b16a778af8380036ce59e7b0492370b249b11e8f07a51afac45037afee9d1'],
]
const nistResults = NIST.map(([msg, want]) => ({ len: msg.length, want, got: PROD.sha256Hex(bytesOf(msg)) }))
const millionA = new Uint8Array(1000000).fill(0x61)
const millionGot = PROD.sha256Hex(millionA)
const MILLION_A = 'cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0'

// Padding-block boundaries, digests from Python hashlib. 55/56 straddle the point where the length
// no longer fits the final block; 63/64/65 and 119/120/121 straddle block ends.
const BOUNDARY = {
  54: 'a3f01b6939256127582ac8ae9fb47a382a244680806a3f613a118851c1ca1d47',
  55: '9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318',
  56: 'b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a',
  57: 'f13b2d724659eb3bf47f2dd6af1accc87b81f09f59f2b75e5c0bed6589dfe8c6',
  63: '7d3e74a05d7db15bce4ad9ec0658ea98e3f06eeecf16b4c6fff2da457ddc2f34',
  64: 'ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb',
  65: '635361c48bb9eab14198e76ea8ab7f1a41685d6ad62aa9146d301d4f17eb0ae0',
  119: '31eba51c313a5c08226adf18d4a359cfdfd8d2e816b13f4af952f7ea6584dcfb',
  120: '2f3d335432c70b580af0e8e1b3674a7c020d683aa5f73aaaedfdc55af904c21c',
  121: 'e9615320128cc7a3d6078e9af05603188e5ccbf0d07d8b735d3df5e8e0c1281f',
}
const boundaryBad = Object.entries(BOUNDARY)
  .filter(([n, want]) => PROD.sha256Hex(new Uint8Array(Number(n)).fill(0x61)) !== want)
  .map(([n]) => Number(n))

const hashA = PROD.sha256Hex(tailA), hashB = PROD.sha256Hex(tailB)
report.sha = {
  nist: nistResults.map(r => ({ len: r.len, ok: r.got === r.want })),
  nistAllOk: nistResults.every(r => r.got === r.want),
  millionAOk: millionGot === MILLION_A,
  boundaryBad,
  tail: { a: hashA.slice(0, 16), b: hashB.slice(0, 16), differ: hashA !== hashB },
  widerViewRefused: thrown(() => PROD.sha256Hex(new Float32Array(4))),
  demDigestOk: PROD.sha256Hex(demBytes) === REAL_DEM.sha256,
}

// ---------------------------------------------------------------------------------------------
// 3. FORMAT BY MAGIC, NOT BY NAME
// ---------------------------------------------------------------------------------------------
const tiffLe = corpus.get('dem16le.tif') || new Uint8Array([0])
const tiffBe = corpus.get('dem8be.tif') || new Uint8Array([0])
const pngNamedRaw = PROD.describeSource({ bytes: demBytes, filename: 'elevation.raw' })
const tiffNamedPng = PROD.describeSource({ bytes: tiffLe, filename: 'srtm_n39_w109.png' })
const pngNoName = PROD.describeSource({ bytes: demBytes, filename: '' })
report.format = {
  pngNamedRaw: pngNamedRaw.format.value,
  tiffNamedPng: tiffNamedPng.format.value,
  pngNoName: pngNoName.format.value,
  sniffPng: PROD.sniffFormat(demBytes).format,
  tiffLe: PROD.sniffFormat(tiffLe),
  tiffBe: PROD.sniffFormat(tiffBe),
  // A refused TIFF must volunteer nothing about the ground it covers.
  tiffFactsUnknown: ['sourceWidth', 'sourceHeight', 'bitDepth', 'cellSpacing', 'crs', 'verticalDatum']
    .every(k => tiffNamedPng[k] === undefined || !PROD.isKnown(tiffNamedPng[k])),
  unknownMagic: PROD.sniffFormat(bytesOf('RIFF....WEBPVP8 not a heightmap at all')),
}

// ---------------------------------------------------------------------------------------------
// 4. IHDR — pinned against the externally measured corpus
// ---------------------------------------------------------------------------------------------
const headerRows = []
for (const [name, bytes] of corpus) {
  const want = expected(name)
  if (want.format !== 'png') continue
  let got = null, err = null
  try { got = PROD.readPngHeader(bytes) } catch (e) { err = e.code || String(e) }
  headerRows.push({
    name, err,
    ok: !!got && got.width === want.width && got.height === want.height
      && got.bitDepth === want.bitDepth && got.colorType === want.colorType && got.interlace === want.interlace,
    got: got && { w: got.width, h: got.height, bd: got.bitDepth, ct: got.colorType, il: got.interlace },
    want: { w: want.width, h: want.height, bd: want.bitDepth, ct: want.colorType, il: want.interlace },
  })
}
const dem16 = corpus.get('dem16.png') || new Uint8Array([0])
const rec16 = PROD.describeSource({ bytes: dem16, filename: 'dem16.png' })
report.png = {
  rows: headerRows,
  allOk: headerRows.length > 0 && headerRows.every(r => r.ok),
  interlacedSeen: headerRows.some(r => r.want.il === 1),
  depth16Seen: headerRows.some(r => r.want.bd === 16),
  // The whole reason bit depth must come from IHDR: the file says 16, the shipped pipeline
  // delivers 8, and those are two different facts with two different provenances.
  sixteenBit: {
    bitDepth: rec16.bitDepth.value, bitDepthProvenance: rec16.bitDepth.provenance,
    decodePrecision: rec16.decodePrecision.value, decodeProvenance: rec16.decodePrecision.provenance,
  },
}

// Refusals. Each input is a real fixture deliberately damaged; the expected answer comes from the
// PNG specification, not from the module.
const rgb = corpus.get('dem8rgb.png') || new Uint8Array(64)
const truncated = rgb.slice(0, 20)
const badSig = rgb.slice(); badSig[1] = 0x51
const notIhdr = rgb.slice(); notIhdr[12] = 0x49; notIhdr[13] = 0x48; notIhdr[14] = 0x44; notIhdr[15] = 0x58
const crcBroken = rgb.slice(); crcBroken[17] ^= 0x01   // inside the IHDR data, CRC left stale
const wrongLength = rgb.slice(); wrongLength[11] = 14  // IHDR declares 14 bytes; the spec fixes 13
const zeroWidth = withIhdrByte(rgb, 19, 0)          // width low byte -> 40 becomes 0
const illegalDepth = withIhdrByte(rgb, 24, 1)       // bit depth 1 is illegal for colour type 2
const badColorType = withIhdrByte(rgb, 25, 7)       // 7 is not a defined colour type
const refusals = {
  truncated: thrown(() => PROD.readPngHeader(truncated)),
  badSignature: thrown(() => PROD.readPngHeader(badSig)),
  firstChunkNotIhdr: thrown(() => PROD.readPngHeader(notIhdr)),
  ihdrCrc: thrown(() => PROD.readPngHeader(crcBroken)),
  declaredLength: thrown(() => PROD.readPngHeader(wrongLength)),
  zeroWidth: thrown(() => PROD.readPngHeader(zeroWidth)),
  illegalDepthForColourType: thrown(() => PROD.readPngHeader(illegalDepth)),
  undefinedColourType: thrown(() => PROD.readPngHeader(badColorType)),
}
// A damaged PNG must also leave the RECORD without invented dimensions.
const damagedRecord = PROD.describeSource({ bytes: illegalDepth, filename: 'damaged.png' })
report.refusals = {
  ...refusals,
  allRefused: Object.values(refusals).every(Boolean),
  damaged: {
    supported: damagedRecord.supported,
    bitDepth: damagedRecord.bitDepth.value,
    width: damagedRecord.sourceWidth.value,
    problems: damagedRecord.problems.map(p => p.code),
  },
}

// ---------------------------------------------------------------------------------------------
// 5. PROVENANCE
// ---------------------------------------------------------------------------------------------
const demRecord = PROD.describeSource({ bytes: demBytes, filename: 'srtm_colorado.png' })
const facts = Object.entries(demRecord).filter(([, f]) => f && typeof f === 'object' && 'provenance' in f)

const vocabularyBad = facts.filter(([, f]) =>
  !(f.provenance === null || PROD.PROVENANCE.includes(f.provenance))
  || (f.provenance === null) !== (f.value === PROD.UNKNOWN)).map(([k]) => k)

// Every 'embedded' fact must cite a byte range inside the file...
const citationBad = facts.filter(([, f]) => {
  if (f.provenance !== 'embedded') return false
  const c = f.cite
  return !c || typeof c.from !== 'string' || !c.from || !Number.isInteger(c.at) || c.at < 0
    || !Number.isInteger(c.length) || c.length <= 0 || c.at + c.length > demBytes.length
}).map(([k]) => k)

// ...and the CITED BYTES must actually produce the reported value. This is read here, from the raw
// array, with arithmetic written in this file — the module's answer is never its own witness.
const reread = {
  format: () => PNG_SIG.every((v, i) => demBytes[i] === v) ? 'png' : 'not-png',
  sourceWidth: c => be32(demBytes, c.at),
  sourceHeight: c => be32(demBytes, c.at),
  bitDepth: c => demBytes[c.at],
  colorType: c => demBytes[c.at],
  interlace: c => demBytes[c.at],
  byteLength: () => demBytes.length,
}
const citationMismatch = Object.entries(reread)
  .filter(([k, read]) => {
    const f = demRecord[k]
    return !f || f.provenance !== 'embedded' || !f.cite || read(f.cite) !== f.value
  })
  .map(([k]) => k)

const PHYSICAL = ['horizontalExtent', 'cellSpacing', 'verticalDatum', 'elevationRange', 'crs']
const physicalLeaked = PHYSICAL.filter(k => !demRecord[k] || demRecord[k].value !== PROD.UNKNOWN
  || demRecord[k].provenance !== null)
const DEFAULTS = ['heightEncoding', 'decodePrecision']
const defaultsMislabelled = DEFAULTS.filter(k => !demRecord[k] || demRecord[k].provenance !== 'inferred-default')

report.provenance = {
  factCount: facts.length,
  vocabularyBad, citationBad, citationMismatch, physicalLeaked, defaultsMislabelled,
  filenameProvenance: demRecord.filename.provenance,
  problems: demRecord.problems.map(p => p.code),
  // The module's own validator must agree that a deliberately mislabelled record is broken. Built
  // here, from production's own constructors, so the validator is what decides.
  validatorCatchesMislabel: PROD.validateSourceRecord({
    byteLength: PROD.embeddedFact(9327, { from: 'file', at: 0, length: 9327 }),
    guessed: PROD.embeddedFact(30, null),
  }).some(p => p.code === 'PROV_EMBEDDED_WITHOUT_CITATION'),
  validatorAcceptsClean: PROD.validateSourceRecord(demRecord).length === 0,
  line: PROD.formatSourceLine(demRecord),
}

// ---------------------------------------------------------------------------------------------
// 6. THE PREMISE — this module only earns its keep while legacy's decode really is 8-bit
// ---------------------------------------------------------------------------------------------
report.premise = {
  legacyBytes: legacySrc.length,
  canvasReadback: /getImageData\([^)]*\)\s*\.\s*data/.test(legacySrc),
  noIhdrParserInLegacy: !/IHDR/.test(legacySrc),
}

// ---------------------------------------------------------------------------------------------
// GATES
// ---------------------------------------------------------------------------------------------
const gates = {
  harnessModelsProduction: report.harness.namesMatch && report.harness.digestMatch
    && report.harness.recordMatch && report.harness.exportCount >= 12,
  setupClean: setupProblems.length === 0,
  fixtureCorpusNonEmpty: corpus.size === 6 && report.corpus.lengthsAgree === true,
  fixturesGenuinelyDiffer: report.corpus.distinctDigests === corpus.size
    && report.corpus.tailPair.diffCount === 1
    && report.corpus.tailPair.diffAt === report.corpus.tailPair.lastIndex
    && report.corpus.tailPair.mod4 !== 0,

  shaMatchesPublishedVectors: report.sha.nistAllOk === true && report.sha.millionAOk === true,
  shaMatchesPaddingBoundaries: report.sha.boundaryBad.length === 0,
  shaSeesTheFinalByte: report.sha.tail.differ === true,
  shaIdentityMatchesMeasuredDem: report.sha.demDigestOk === true,
  shaRefusesWiderViews: report.sha.widerViewRefused === 'SHA_INPUT_NOT_BYTES',

  formatFromMagicNotFilename: report.format.pngNamedRaw === 'png'
    && report.format.tiffNamedPng === 'tiff'
    && report.format.pngNoName === 'png'
    && report.format.sniffPng === 'png',
  geotiffRefusedNotGuessed: report.format.tiffLe.format === 'tiff' && report.format.tiffLe.supported === false
    && report.format.tiffLe.reason === 'GEOTIFF_UNSUPPORTED' && report.format.tiffFactsUnknown === true,
  bothTiffByteOrdersRecognised: report.format.tiffLe.byteOrder === 'little'
    && report.format.tiffBe.format === 'tiff' && report.format.tiffBe.byteOrder === 'big',
  unrecognisedMagicRefused: report.format.unknownMagic.format === 'unknown'
    && report.format.unknownMagic.supported === false,

  pngHeadersMatchMeasuredCorpus: report.png.allOk === true,
  corpusExercisesDepthAndInterlace: report.png.depth16Seen === true && report.png.interlacedSeen === true,
  bitDepth16SurvivesFromIhdr: report.png.sixteenBit.bitDepth === 16
    && report.png.sixteenBit.bitDepthProvenance === 'embedded',
  fileDepthDistinctFromDecodePrecision: report.png.sixteenBit.decodePrecision === 8
    && report.png.sixteenBit.decodeProvenance === 'inferred-default'
    && report.png.sixteenBit.bitDepth !== report.png.sixteenBit.decodePrecision,

  malformedHeadersRefused: report.refusals.allRefused === true
    && report.refusals.truncated === 'PNG_TRUNCATED'
    && report.refusals.badSignature === 'PNG_BAD_SIGNATURE'
    && report.refusals.firstChunkNotIhdr === 'PNG_IHDR_MISSING'
    && report.refusals.ihdrCrc === 'PNG_IHDR_CRC',
  damagedFileYieldsNoInventedDimensions: report.refusals.damaged.supported === false
    && report.refusals.damaged.bitDepth === PROD.UNKNOWN && report.refusals.damaged.width === PROD.UNKNOWN,

  provenanceVocabularyClosed: report.provenance.vocabularyBad.length === 0,
  embeddedFactsCiteRealBytes: report.provenance.citationBad.length === 0,
  citedBytesReproduceTheValue: report.provenance.citationMismatch.length === 0,
  physicalFieldsStayUnknown: report.provenance.physicalLeaked.length === 0,
  defaultsCarryInferredProvenance: report.provenance.defaultsMislabelled.length === 0,
  filenameIsUserSupplied: report.provenance.filenameProvenance === 'user-override',
  cleanRecordHasNoProblems: report.provenance.problems.length === 0 && report.provenance.validatorAcceptsClean === true,
  validatorCatchesMislabelledDefault: report.provenance.validatorCatchesMislabel === true,

  shippedDecodePathIsStillEightBit: report.premise.legacyBytes > 100000
    && report.premise.canvasReadback === true && report.premise.noIhdrParserInLegacy === true,
}

let ok = Object.values(gates).every(Boolean)
if (mutation) {
  if (ok) console.error(`FAIL mutation ${mutation} was not detected — this probe is vacuous`)
  ok = false
}
const failed = Object.entries(gates).filter(([, v]) => !v).map(([k]) => k)

console.log(`${ok ? 'PASS' : 'FAIL'}  height-source  fixtures=${corpus.size} facts=${report.provenance.factCount} `
  + `dem=${report.png.rows.length ? report.png.rows[0].got && report.png.rows[0].got.w : '?'}x`
  + `${report.png.rows.length ? report.png.rows[0].got && report.png.rows[0].got.h : '?'}@${REAL_DEM.bitDepth}bit `
  + `sha=${String(PROD.sha256Hex(demBytes)).slice(0, 12)} depth16=${report.png.sixteenBit.bitDepth} `
  + `decode=${report.png.sixteenBit.decodePrecision} tailDiffer=${report.sha.tail.differ} `
  + `failed=[${failed.join(',')}] mutation=${mutation || 'none'}`)
console.log(JSON.stringify({ ...report, gates, ok }, null, 2))
process.exit(ok ? 0 : 1)
