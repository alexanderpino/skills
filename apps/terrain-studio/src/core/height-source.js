// Imported height-source identity and provenance — story S9.3, first slice.
//
// Pure, DOM-free, zero-dependency. It reads BYTES and reports what the bytes say. It does not
// decode pixels, does not touch a canvas, does not import legacy.js, and — deliberately — does not
// infer one square metre of geography.
//
// ---------------------------------------------------------------------------------------------
// WHY THIS MODULE EXISTS AT ALL (measured, not assumed)
//
// S9.3 has to report an imported height source's format, source dimensions, bit depth and byte
// identity. Two of those four are unobtainable from the shipped import path:
//
//   BIT DEPTH. `buildDemFromSource` (src/legacy.js:4613) draws the decoded `Image` into a 2D
//   canvas and reads it back with `getImageData(...).data`, which is a Uint8ClampedArray. A 16-bit
//   PNG is therefore quantised to 256 levels BEFORE anything downstream can measure it — by the
//   time a field exists, the evidence is gone. The only place the true depth survives is byte 24
//   of the IHDR chunk in the raw file, so that is where this module reads it.
//
//   CHECKSUM. `fieldKey` (src/core/subgraph.js:147) is a 64-bit FNV-1a over FLOAT WORDS, built as
//   a cache key: it hashes `new Uint32Array(buffer, offset, byteLength >>> 2)`, i.e. whole 32-bit
//   words only, and any tail that does not fill a word is silently dropped. That is harmless for
//   the Float32Array fields it was written for and wrong for a file of arbitrary length. A content
//   checksum has to be a real cryptographic digest over every byte, so this module carries its own
//   synchronous SHA-256.
//
// SYNCHRONOUS ON PURPOSE. `crypto.subtle.digest` is a Promise, and the import handler
// (`$("#fileInput").onchange`, src/legacy.js:4586) runs inside a user-gesture path that already
// does `recordHistory()` and mutates the node synchronously. Making identity async would either
// split that transaction or force the whole import path to become a promise chain. A 9 KB DEM
// hashes in well under a millisecond; the complexity is not worth buying.
//
// ---------------------------------------------------------------------------------------------
// THE PROVENANCE RULE — the actual point of the story
//
// Every field is a FACT: a value plus where the value came from. Three origins, and only three:
//
//   'embedded'         read out of the file's own bytes
//   'inferred-default' Terrain Studio chose it because the file did not say
//   'user-override'    a human supplied it
//
// A default must never be labelled 'embedded'. That is not a style preference: an imported DEM
// that claims 30 m spacing "from the file" when Terrain Studio guessed it is a fabricated
// geospatial fact, and it will be believed by every downstream consumer — erosion calibration,
// real-scale export, the height-in-metres readout — none of which can tell the difference.
//
// The rule is made MECHANICAL rather than aspirational: an 'embedded' fact must cite the byte
// range it was read from (`{ from, at, length }`), and the citation must lie inside the file. A
// default has no byte range, so it cannot honestly produce one — mislabelling is then a structural
// error that `validateSourceRecord` catches, not a comment nobody reads.
//
// UNKNOWN IS A FIRST-CLASS ANSWER. Physical facts — extent, cell spacing, vertical datum, CRS,
// elevation range — are reported UNKNOWN here with provenance `null`, because nothing supplied
// them. Claiming an origin for a value you do not have is the same lie as labelling a default
// 'embedded'. UNKNOWN is a plain string rather than a Symbol precisely because these records are
// meant to be written into project files and printed in reports, and a Symbol vanishes through
// JSON.stringify — an absent field reads as "not implemented yet" instead of "not known".
//
// FILENAMES ARE USER INPUT, NOT EVIDENCE. `filename` carries provenance 'user-override': it is
// whatever text the file picker handed over. Format is decided by MAGIC NUMBER only. A DEM
// exported as `elevation.raw` that is really a PNG, or a GeoTIFF a pipeline renamed to `.png`,
// must be classified by its first bytes; dispatching on the extension is how an import silently
// reads the wrong decoder.

export const UNKNOWN = 'UNKNOWN'

/** The closed vocabulary. Anything outside it is a structural error, not a new category. */
export const PROVENANCE = Object.freeze(['embedded', 'inferred-default', 'user-override'])

export const HEIGHT_SOURCE_ERROR_CODES = Object.freeze([
  'SHA_INPUT_NOT_BYTES',
  'PNG_BAD_SIGNATURE', 'PNG_TRUNCATED', 'PNG_IHDR_MISSING', 'PNG_IHDR_MALFORMED', 'PNG_IHDR_CRC',
  'SOURCE_INPUT_NOT_BYTES',
])

export class HeightSourceError extends Error {
  constructor(code, message, detail) {
    super(message)
    this.name = 'HeightSourceError'
    this.code = code
    this.detail = detail
  }
}
const fail = (code, message, detail) => { throw new HeightSourceError(code, message, detail) }

// ---------------------------------------------------------------------------------------------
// Facts
// ---------------------------------------------------------------------------------------------

/**
 * A value read out of the file, with the byte range it was read from. The citation is REQUIRED —
 * that requirement is what makes "a default must never be labelled embedded" checkable by machine
 * instead of by review.
 */
export function embeddedFact(value, cite) {
  return Object.freeze({ value, provenance: 'embedded', cite: cite ? Object.freeze({ ...cite }) : null })
}

/** A value Terrain Studio chose because the file did not say. `because` is required for the same reason. */
export function defaultFact(value, because) {
  return Object.freeze({ value, provenance: 'inferred-default', because: because || '' })
}

/** A value a human supplied — including the filename, which is picker text, not file content. */
export function overrideFact(value, because) {
  return Object.freeze({ value, provenance: 'user-override', because: because || '' })
}

/** Not known. Provenance is null because nothing produced it; `because` says what would have. */
export function unknownFact(because) {
  return Object.freeze({ value: UNKNOWN, provenance: null, because: because || '' })
}

const isFact = f => !!f && typeof f === 'object' && 'value' in f && 'provenance' in f
export const isKnown = f => isFact(f) && f.value !== UNKNOWN

// ---------------------------------------------------------------------------------------------
// SHA-256 — FIPS 180-4, synchronous, over every byte
// ---------------------------------------------------------------------------------------------

const K256 = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
])

const rotr = (x, n) => (x >>> n) | (x << (32 - n))

/** A byte view or nothing. A number, a string or a Float32Array is a caller bug, not a message. */
function asByteView(bytes) {
  if (!ArrayBuffer.isView(bytes) || bytes.BYTES_PER_ELEMENT !== 1) {
    fail('SHA_INPUT_NOT_BYTES', 'sha256Hex needs a Uint8Array; a wider view would hash element '
      + 'values rather than bytes and would depend on host endianness', { got: typeof bytes })
  }
  return bytes
}

/**
 * SHA-256 of a byte array, lowercase hex. Consumes EVERY byte, including a tail that does not fill
 * a 32-bit word — that tail is exactly what `fieldKey`'s `byteLength >>> 2` throws away, and two
 * files differing only in their last byte must never collide here.
 */
export function sha256Hex(bytes) {
  const view = asByteView(bytes)
  const len = view.length

  // Message + 0x80 + at least 8 length bytes, rounded up to whole 64-byte blocks.
  const blocks = Math.ceil((len + 9) / 64)
  const total = blocks * 64
  const m = new Uint8Array(total)
  m.set(view)
  m[len] = 0x80
  // 64-bit big-endian bit length. Split rather than `len << 3` because the shift is a 32-bit
  // operation and would wrap silently at 512 MB of input.
  const bitsHi = Math.floor(len / 0x20000000)
  const bitsLo = (len * 8) >>> 0
  m[total - 8] = (bitsHi >>> 24) & 0xff; m[total - 7] = (bitsHi >>> 16) & 0xff
  m[total - 6] = (bitsHi >>> 8) & 0xff; m[total - 5] = bitsHi & 0xff
  m[total - 4] = (bitsLo >>> 24) & 0xff; m[total - 3] = (bitsLo >>> 16) & 0xff
  m[total - 2] = (bitsLo >>> 8) & 0xff; m[total - 1] = bitsLo & 0xff

  let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a
  let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19
  const w = new Uint32Array(64)

  for (let p = 0; p < total; p += 64) {
    for (let i = 0; i < 16; i++) {
      const j = p + i * 4
      w[i] = ((m[j] << 24) | (m[j + 1] << 16) | (m[j + 2] << 8) | m[j + 3]) >>> 0
    }
    for (let i = 16; i < 64; i++) {
      const x = w[i - 15], y = w[i - 2]
      const s0 = rotr(x, 7) ^ rotr(x, 18) ^ (x >>> 3)
      const s1 = rotr(y, 17) ^ rotr(y, 19) ^ (y >>> 10)
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0
    }
    let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7
    for (let i = 0; i < 64; i++) {
      const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
      const ch = (e & f) ^ (~e & g)
      const t1 = (h + S1 + ch + K256[i] + w[i]) >>> 0
      const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
      const maj = (a & b) ^ (a & c) ^ (b & c)
      const t2 = (S0 + maj) >>> 0
      h = g; g = f; f = e; e = (d + t1) >>> 0
      d = c; c = b; b = a; a = (t1 + t2) >>> 0
    }
    h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0
    h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0; h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0
  }

  const hex = v => v.toString(16).padStart(8, '0')
  return hex(h0) + hex(h1) + hex(h2) + hex(h3) + hex(h4) + hex(h5) + hex(h6) + hex(h7)
}

// ---------------------------------------------------------------------------------------------
// Format sniffing — magic number only
// ---------------------------------------------------------------------------------------------

const PNG_SIGNATURE = Object.freeze([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
const TIFF_LE = Object.freeze([0x49, 0x49, 0x2a, 0x00])   // "II*\0"
const TIFF_BE = Object.freeze([0x4d, 0x4d, 0x00, 0x2a])   // "MM\0*"

const startsWith = (bytes, sig) => {
  if (bytes.length < sig.length) return false
  for (let i = 0; i < sig.length; i++) if (bytes[i] !== sig[i]) return false
  return true
}

const hexBytes = (bytes, n) => Array.from(bytes.slice(0, n)).map(b => b.toString(16).padStart(2, '0')).join(' ')

/**
 * Classify by leading bytes. Never by filename: the name is user-supplied text (see the header
 * note), and an extension-keyed dispatch is how a renamed GeoTIFF gets handed to a PNG decoder.
 *
 * GeoTIFF is RECOGNISED and REFUSED in this sprint. That is the deliberate outcome: a TIFF's
 * geospatial payload lives in GeoKey directories this module does not read, and reporting a
 * plausible extent or datum from a file we have not parsed would be exactly the fabricated fact
 * the provenance rule exists to prevent. An explicit `supported: false` is an honest answer; a
 * guess is not.
 */
export function sniffFormat(bytes) {
  const view = asByteView(bytes)
  if (startsWith(view, PNG_SIGNATURE)) {
    return Object.freeze({
      format: 'png', supported: true, reason: null, byteOrder: 'big',
      magic: hexBytes(view, 8), magicLength: 8,
    })
  }
  if (startsWith(view, TIFF_LE) || startsWith(view, TIFF_BE)) {
    const little = startsWith(view, TIFF_LE)
    return Object.freeze({
      format: 'tiff', supported: false, reason: 'GEOTIFF_UNSUPPORTED',
      byteOrder: little ? 'little' : 'big',
      magic: hexBytes(view, 4), magicLength: 4,
    })
  }
  return Object.freeze({
    format: 'unknown', supported: false, reason: 'UNRECOGNISED_MAGIC', byteOrder: null,
    magic: hexBytes(view, Math.min(8, view.length)), magicLength: Math.min(8, view.length),
  })
}

// ---------------------------------------------------------------------------------------------
// PNG IHDR
// ---------------------------------------------------------------------------------------------

// Byte offsets are fixed by the PNG spec: signature 0..7, then the first chunk's 4-byte length,
// 4-byte type, 13-byte IHDR payload, 4-byte CRC. IHDR is required to be the FIRST chunk, so these
// are constants, not a search.
const IHDR_LENGTH_AT = 8
const IHDR_TYPE_AT = 12
const IHDR_DATA_AT = 16
const IHDR_DATA_LENGTH = 13
const IHDR_CRC_AT = IHDR_DATA_AT + IHDR_DATA_LENGTH
const IHDR_TOTAL = IHDR_CRC_AT + 4

export const IHDR_FIELD_AT = Object.freeze({
  width: IHDR_DATA_AT, height: IHDR_DATA_AT + 4, bitDepth: IHDR_DATA_AT + 8,
  colorType: IHDR_DATA_AT + 9, compression: IHDR_DATA_AT + 10,
  filter: IHDR_DATA_AT + 11, interlace: IHDR_DATA_AT + 12,
})

// Legal bit depths per colour type, PNG spec table 11.1. A depth outside its type's set is a
// malformed header, not something to normalise: silently accepting it means every later reading
// derived from it is invented.
const LEGAL_DEPTHS = Object.freeze({
  0: [1, 2, 4, 8, 16],   // greyscale
  2: [8, 16],            // truecolour
  3: [1, 2, 4, 8],       // indexed
  4: [8, 16],            // greyscale + alpha
  6: [8, 16],            // truecolour + alpha
})

let CRC_TABLE = null
function crc32(bytes, from, to) {
  if (!CRC_TABLE) {
    CRC_TABLE = new Uint32Array(256)
    for (let n = 0; n < 256; n++) {
      let c = n
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1)
      CRC_TABLE[n] = c >>> 0
    }
  }
  let c = 0xffffffff
  for (let i = from; i < to; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8)
  return (c ^ 0xffffffff) >>> 0
}

const be32 = (b, at) => ((b[at] << 24) | (b[at + 1] << 16) | (b[at + 2] << 8) | b[at + 3]) >>> 0

/**
 * Parse the IHDR chunk. THROWS on anything it cannot read — a missing signature, a truncated file,
 * a first chunk that is not IHDR, an out-of-spec field, a failing CRC.
 *
 * Refusing rather than defaulting is the whole contract. Returning `{ bitDepth: 8 }` for a header
 * we could not read is indistinguishable, downstream, from having measured 8 — and 8 is the exact
 * value the canvas path already fabricates. A gate built on that would be reading its own guess.
 */
export function readPngHeader(bytes) {
  const b = asByteView(bytes)
  if (!startsWith(b, PNG_SIGNATURE)) {
    fail('PNG_BAD_SIGNATURE', 'not a PNG: leading bytes are ' + hexBytes(b, Math.min(8, b.length)),
      { magic: hexBytes(b, Math.min(8, b.length)) })
  }
  if (b.length < IHDR_TOTAL) {
    fail('PNG_TRUNCATED', `PNG is ${b.length} bytes; IHDR alone needs ${IHDR_TOTAL}`,
      { byteLength: b.length, need: IHDR_TOTAL })
  }
  const type = String.fromCharCode(b[IHDR_TYPE_AT], b[IHDR_TYPE_AT + 1], b[IHDR_TYPE_AT + 2], b[IHDR_TYPE_AT + 3])
  if (type !== 'IHDR') {
    fail('PNG_IHDR_MISSING', `first chunk is "${type}", but PNG requires IHDR first`, { type })
  }
  const declared = be32(b, IHDR_LENGTH_AT)
  if (declared !== IHDR_DATA_LENGTH) {
    fail('PNG_IHDR_MALFORMED', `IHDR declares ${declared} bytes of data; the spec fixes it at 13`,
      { declaredLength: declared })
  }
  // The CRC covers the type plus the data. Checking it is what turns "the bytes at offset 24 say
  // 16" into "the file says 16": a flipped byte anywhere in the header is otherwise a plausible
  // number nobody can distinguish from a measurement.
  const want = be32(b, IHDR_CRC_AT)
  const got = crc32(b, IHDR_TYPE_AT, IHDR_CRC_AT)
  if (want !== got) {
    fail('PNG_IHDR_CRC', `IHDR CRC mismatch: file says ${want.toString(16)}, bytes compute ${got.toString(16)}`,
      { declared: want, computed: got })
  }

  const width = be32(b, IHDR_FIELD_AT.width)
  const height = be32(b, IHDR_FIELD_AT.height)
  const bitDepth = b[IHDR_FIELD_AT.bitDepth]
  const colorType = b[IHDR_FIELD_AT.colorType]
  const compression = b[IHDR_FIELD_AT.compression]
  const filter = b[IHDR_FIELD_AT.filter]
  const interlace = b[IHDR_FIELD_AT.interlace]

  if (width === 0 || height === 0) {
    fail('PNG_IHDR_MALFORMED', `IHDR gives a zero dimension (${width}x${height})`, { width, height })
  }
  const legal = LEGAL_DEPTHS[colorType]
  if (!legal) fail('PNG_IHDR_MALFORMED', `IHDR colour type ${colorType} is not one of 0,2,3,4,6`, { colorType })
  if (!legal.includes(bitDepth)) {
    fail('PNG_IHDR_MALFORMED', `bit depth ${bitDepth} is illegal for colour type ${colorType} (legal: ${legal.join(',')})`,
      { bitDepth, colorType, legal })
  }
  if (compression !== 0) fail('PNG_IHDR_MALFORMED', `compression method ${compression}; only 0 is defined`, { compression })
  if (filter !== 0) fail('PNG_IHDR_MALFORMED', `filter method ${filter}; only 0 is defined`, { filter })
  if (interlace !== 0 && interlace !== 1) fail('PNG_IHDR_MALFORMED', `interlace ${interlace}; only 0 and 1 are defined`, { interlace })

  return Object.freeze({ width, height, bitDepth, colorType, compression, filter, interlace })
}

// ---------------------------------------------------------------------------------------------
// The assembled record
// ---------------------------------------------------------------------------------------------

// Physical geography this layer refuses to invent. Each entry says what WOULD have supplied it, so
// a later story adding GeoTIFF GeoKey parsing or a user-entered extent has an obvious slot to fill
// and an obvious provenance to stamp on it.
const PHYSICAL_UNKNOWNS = Object.freeze({
  horizontalExtent: 'no raster format read here states ground extent; a GeoTIFF ModelPixelScale or a user entry would',
  cellSpacing: 'ground sample distance is not in a PNG; it comes from GeoTIFF tags or from the user',
  verticalDatum: 'a PNG carries no datum; EGM96/WGS84 must never be assumed',
  elevationRange: 'the file gives sample values, not metres; the mapping is a user decision',
  crs: 'no coordinate reference system is embedded in a PNG',
})

/**
 * The record S9.3 reports. Identity always; dimensions and depth when the format is one we can
 * actually read; physical geography never.
 *
 * Nothing throws: a GeoTIFF or a corrupt file must produce a record that SAYS so, because the
 * import UI has to show the user why their file was refused. Refusals land in `problems`.
 */
export function describeSource({ bytes, filename } = {}) {
  const b = asByteView(bytes)
  const byteLength = b.length
  const problems = []

  const sniff = sniffFormat(b)
  const record = {
    // Picker text. 'user-override' because that is literally its origin — a human chose this file
    // and its name. It is recorded for display and NEVER consulted to decide format.
    filename: overrideFact(typeof filename === 'string' ? filename : '', 'supplied by the file picker, not read from the bytes'),
    format: embeddedFact(sniff.format, { from: 'magic', at: 0, length: sniff.magicLength }),
    byteOrder: sniff.byteOrder === null
      ? unknownFact('byte order is a property of formats we recognised; this file is not one')
      : embeddedFact(sniff.byteOrder, { from: 'magic', at: 0, length: sniff.magicLength }),
    supported: sniff.supported,
    unsupportedReason: sniff.reason,
    byteLength: embeddedFact(byteLength, { from: 'file', at: 0, length: byteLength }),
    sha256: embeddedFact(sha256Hex(b), { from: 'file', at: 0, length: byteLength }),

    sourceWidth: unknownFact('no readable header'),
    sourceHeight: unknownFact('no readable header'),
    bitDepth: unknownFact('no readable header'),
    colorType: unknownFact('no readable header'),
    interlace: unknownFact('no readable header'),

    // Terrain Studio's own choices, labelled as such. `decodePrecision` is the honest record of
    // what the shipped pipeline actually delivers: src/legacy.js:4613 reads samples back out of a
    // 2D canvas as a Uint8ClampedArray, so a 16-bit file arrives at the field at 8 bits. Keeping
    // it as a SEPARATE fact from `bitDepth` is the point — the file's depth and the pipeline's
    // depth are different numbers, and collapsing them is how the loss became invisible.
    heightEncoding: defaultFact('luminance-normalised-0-1',
      'Terrain Studio maps samples to 0..1 by Rec.601 luminance (src/legacy.js:4616); no raster format states this'),
    decodePrecision: defaultFact(8,
      'the shipped canvas readback path is 8-bit (Uint8ClampedArray, src/legacy.js:4615) whatever the file carries'),
    problems,
  }

  if (sniff.format === 'png') {
    try {
      const h = readPngHeader(b)
      record.sourceWidth = embeddedFact(h.width, { from: 'IHDR', at: IHDR_FIELD_AT.width, length: 4 })
      record.sourceHeight = embeddedFact(h.height, { from: 'IHDR', at: IHDR_FIELD_AT.height, length: 4 })
      record.bitDepth = embeddedFact(h.bitDepth, { from: 'IHDR', at: IHDR_FIELD_AT.bitDepth, length: 1 })
      record.colorType = embeddedFact(h.colorType, { from: 'IHDR', at: IHDR_FIELD_AT.colorType, length: 1 })
      record.interlace = embeddedFact(h.interlace, { from: 'IHDR', at: IHDR_FIELD_AT.interlace, length: 1 })
    } catch (error) {
      // A PNG signature with an unreadable header stays UNKNOWN. It does not fall back to 8-bit
      // defaults, and the record reports it as unsupported so the UI can refuse the file.
      problems.push({ code: error.code || 'PNG_IHDR_MALFORMED', message: error.message })
      record.supported = false
      record.unsupportedReason = error.code || 'PNG_IHDR_MALFORMED'
    }
  } else if (sniff.format === 'tiff') {
    problems.push({
      code: 'GEOTIFF_UNSUPPORTED',
      message: 'TIFF/GeoTIFF recognised but not read in this sprint; its dimensions and geokeys stay UNKNOWN rather than being guessed',
    })
  } else {
    problems.push({ code: 'UNRECOGNISED_MAGIC', message: 'leading bytes match no format this build reads: ' + sniff.magic })
  }

  for (const [key, why] of Object.entries(PHYSICAL_UNKNOWNS)) record[key] = unknownFact(why)

  problems.push(...validateSourceRecord(record))
  return record
}

/**
 * Structural audit of a record's provenance. Returns problems rather than throwing so a UI can
 * show them all at once, matching validateVariables in src/core/variables.js.
 *
 * This is the enforcement arm of the provenance rule. Without it, "a default must never be
 * labelled embedded" is a comment; with it, mislabelling one is a code a gate can name.
 */
export function validateSourceRecord(record) {
  const problems = []
  for (const [key, f] of Object.entries(record || {})) {
    if (!isFact(f)) continue
    if (f.provenance === null) {
      if (f.value !== UNKNOWN) problems.push({ code: 'PROV_MISSING', field: key })
      continue
    }
    if (!PROVENANCE.includes(f.provenance)) {
      problems.push({ code: 'PROV_UNKNOWN_VOCABULARY', field: key, provenance: String(f.provenance) })
      continue
    }
    if (f.value === UNKNOWN) {
      problems.push({ code: 'PROV_UNKNOWN_WITH_ORIGIN', field: key, provenance: f.provenance })
      continue
    }
    if (f.provenance === 'embedded') {
      const c = f.cite
      if (!c || typeof c.from !== 'string' || !c.from
        || !Number.isInteger(c.at) || c.at < 0 || !Number.isInteger(c.length) || c.length <= 0) {
        // The named failure of this story. A value Terrain Studio chose has no byte range to cite,
        // so a default that claims 'embedded' cannot produce a citation and lands here.
        problems.push({ code: 'PROV_EMBEDDED_WITHOUT_CITATION', field: key })
        continue
      }
      const total = isKnown(record.byteLength) ? record.byteLength.value : null
      if (total !== null && c.at + c.length > total) {
        problems.push({ code: 'PROV_CITATION_OUT_OF_RANGE', field: key, at: c.at, length: c.length, byteLength: total })
      }
    } else if (!f.because) {
      problems.push({ code: 'PROV_ORIGIN_WITHOUT_REASON', field: key, provenance: f.provenance })
    }
  }
  return problems
}

/** Compact one-line rendering for logs and the import toast. */
export function formatSourceLine(record) {
  const v = f => (isKnown(f) ? f.value : UNKNOWN)
  const dims = isKnown(record.sourceWidth) ? `${v(record.sourceWidth)}x${v(record.sourceHeight)}` : UNKNOWN
  return `${v(record.format)} ${dims} ${v(record.bitDepth)}-bit  ${v(record.byteLength)}B  sha256=${String(v(record.sha256)).slice(0, 16)}…`
}
