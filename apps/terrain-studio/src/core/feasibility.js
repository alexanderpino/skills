// Creation feasibility preflight — ADR-007, story S9.2.
//
// Pure, DOM-free, and — the property that matters — ALLOCATION-FREE. This module computes whether a
// requested world can be created without allocating a single field to find out. That is the whole
// point: the current app has no preflight at all, so asking for 4096² simply allocates until the
// tab dies, and the user learns the answer by losing their work.
//
// Everything here is arithmetic on counts and byte sizes. If this file ever allocates a
// Float32Array, the story has been defeated — `_verify_new_terrain.js` spies on exactly that.

export const BYTES_PER_SAMPLE = 4                 // R32F, the working field format

export const FEASIBILITY = Object.freeze(['monolithic', 'gpu-required-paged', 'rejected'])

export const FEASIBILITY_CODES = Object.freeze([
  'FEASIBLE_MONOLITHIC', 'REQUIRES_PAGED', 'EXCEEDS_INDEX', 'EXCEEDS_BUDGET', 'DIMENSIONS_INVALID',
])

// A Float32Array is indexed by a signed 32-bit int in practice, and 2^31-1 samples is the hard
// ceiling regardless of how much memory the machine has. Naming it separately from the byte budget
// matters: one is a machine limit the user cannot buy their way out of, the other is a policy.
export const MAX_SAMPLES_PER_FIELD = 2 ** 31 - 1

/**
 * @param sampleCount {columns, rows}
 * @param liveFields  how many whole fields the demanded node cone holds at once. Measured, not
 *                    guessed: the caller counts the graph's simultaneous live buffers.
 * @param budgetBytes the authored monolithic budget.
 */
export function assessCreation({ sampleCount, liveFields = 1, budgetBytes = 1024 * 1024 * 1024 } = {}) {
  const cols = sampleCount && sampleCount.columns, rows = sampleCount && sampleCount.rows
  if (!Number.isInteger(cols) || !Number.isInteger(rows) || cols < 2 || rows < 2) {
    return { mode: 'rejected', code: 'DIMENSIONS_INVALID', samples: 0, bytesPerField: 0, totalBytes: 0,
      reason: `columns and rows must be integers >= 2 (got ${String(cols)} x ${String(rows)})` }
  }

  // Exact integer arithmetic. 16384*16384 is 268435456, well inside Number's safe range, and using
  // floats here would round the very numbers the decision turns on.
  const samples = cols * rows
  const bytesPerField = samples * BYTES_PER_SAMPLE
  const totalBytes = bytesPerField * Math.max(1, liveFields)

  if (samples > MAX_SAMPLES_PER_FIELD) {
    return { mode: 'rejected', code: 'EXCEEDS_INDEX', samples, bytesPerField, totalBytes,
      reason: `${samples} samples exceeds the ${MAX_SAMPLES_PER_FIELD} addressable by one typed array` }
  }
  if (totalBytes <= budgetBytes) {
    return { mode: 'monolithic', code: 'FEASIBLE_MONOLITHIC', samples, bytesPerField, totalBytes,
      reason: `${fmt(totalBytes)} for ${liveFields} live field(s) fits the ${fmt(budgetBytes)} budget` }
  }
  // Over budget is NOT a rejection. ADR-009 says the preflight selects gpu-required-paged whenever
  // the live cone will not fit monolithically — that is the mode's entire reason to exist. Only an
  // unaddressable raster is refused outright.
  return { mode: 'gpu-required-paged', code: 'REQUIRES_PAGED', samples, bytesPerField, totalBytes,
    reason: `${fmt(totalBytes)} for ${liveFields} live field(s) exceeds the ${fmt(budgetBytes)} budget; paged GPU evaluation required` }
}

/** Page decomposition for a paged world. Terminal pages may be partial — that is not an error. */
export function decomposePages({ sampleCount, coreCells = 256, posting = 'vertex' } = {}) {
  const cols = sampleCount.columns, rows = sampleCount.rows
  // Vertex posting: n samples span n-1 cells. This is the same off-by-one that `posting` exists to
  // keep honest in WorldDomain, and getting it wrong here mis-sizes every terminal page.
  const cellsX = posting === 'vertex' ? cols - 1 : cols
  const cellsY = posting === 'vertex' ? rows - 1 : rows
  const pagesX = Math.ceil(cellsX / coreCells)
  const pagesY = Math.ceil(cellsY / coreCells)
  const terminalX = cellsX - (pagesX - 1) * coreCells
  const terminalY = cellsY - (pagesY - 1) * coreCells
  return {
    cellsX, cellsY, pagesX, pagesY, pages: pagesX * pagesY,
    terminalCoreCells: { x: terminalX, y: terminalY },
    // A zero-area page means the arithmetic is wrong, not that the world has an empty edge.
    zeroAreaPage: terminalX <= 0 || terminalY <= 0,
  }
}

function fmt(bytes) {
  if (bytes >= 1024 ** 3) return (bytes / 1024 ** 3).toFixed(2) + ' GiB'
  if (bytes >= 1024 ** 2) return (bytes / 1024 ** 2).toFixed(1) + ' MiB'
  return (bytes / 1024).toFixed(0) + ' KiB'
}
export { fmt as formatBytes }
