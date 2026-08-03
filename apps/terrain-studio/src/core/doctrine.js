// Staged doctrine validators — ADR-002 S2.5.
//
// Pure and DOM-free; no legacy.js import. Takes a plain graph {nodes, edges} and a type lookup.
//
// STAGED, and the staging is the point. ADR-002 and the sprint plan are explicit that enforcement
// arrives with the sprint that makes it meaningful:
//   * typed and lens rules       — enforced NOW (S2.5)
//   * hydraulic co-evolution     — armed in S3, when cover state exists to co-update
//   * the Snow Rule              — armed in S5, when Moisture exists for snow to depend on
// Declaring a rule before the field it governs exists produces a validator that either passes
// vacuously or refuses legal graphs. Each stage below therefore records WHY it is not yet armed,
// so "not enforced" is a dated decision rather than an oversight.

export const DOCTRINE_STAGES = Object.freeze({
  typedPorts: { armed: true, sprint: 'S2.5', reason: 'typed descriptors exist' },
  lens: { armed: true, sprint: 'S2.5', reason: 'the aux registry declares a lens for every map' },
  legalOrder: { armed: true, sprint: 'S2.5', reason: 'derived-vs-height-writing is decidable from the registry' },
  hydraulicCoEvolution: { armed: false, sprint: 'S3', reason: 'no cover state to co-update yet — soilDepth/sedimentDepth land in S3.1/S3.2' },
  snowRule: { armed: false, sprint: 'S5.3', reason: 'no Moisture field yet, so "no moisture = no new snow" cannot be checked' },
})

export const DOCTRINE_CODES = Object.freeze([
  'ORDER_DERIVED_BEFORE_GEOMETRY', // analysis feeds something that later rewrites height
  'LENS_CARRIED_DERIVED',          // a derived map declared as carried state
  'CYCLE',                         // the graph is not a DAG
])

/**
 * Which node types produce a DERIVED geometry product — a pure function of the current surface.
 * Doctrine: "Analysis must run after the final geometry. Slope and curvature computed before
 * erosion describe a landscape that no longer exists."
 */
export const DERIVED_PRODUCERS = Object.freeze([
  'd_slope', 'd_curvature', 'd_occlusion', 'd_peaks', 'd_wear', 'd_flow', 'd_deposits',
  'aspect', 'normals',
])

/**
 * Which node types WRITE height — that is, produce a new surface rather than reading one.
 * Generators and the erosion/transport family. Filters are deliberately excluded: a filter
 * reshapes whatever it is given and is legal downstream of analysis when the analysis is being
 * used as a mask, which is the shipped idiom.
 */
export const HEIGHT_WRITERS = Object.freeze([
  'hydraulic', 'thermal', 'erosion2', 'streampower', 'hydrofix', 'fracture', 'canyon',
])

/**
 * Legal Order validation. Path-sensitive: walk downstream from every derived producer and report a
 * path that reaches a height-writing node, because that node will rewrite the surface the analysis
 * described.
 *
 * Returns { problems, stats }. It never throws: a graph the user is mid-way through authoring is
 * routinely invalid, and refusing to draw it would be worse than saying so.
 */
export function validateLegalOrder(graph, { typeOf } = {}) {
  const nodes = graph.nodes || [], edges = graph.edges || []
  const type = typeOf || (n => n.type)
  const byId = new Map(nodes.map(n => [n.id, n]))
  const downstream = new Map()
  for (const e of edges) {
    if (e.disabled) continue
    if (!downstream.has(e.from)) downstream.set(e.from, [])
    downstream.get(e.from).push(e.to)
  }

  const problems = []
  let pathsWalked = 0
  for (const start of nodes) {
    if (!DERIVED_PRODUCERS.includes(type(start))) continue
    // Depth-first from this producer, tracking the path so the report names the actual route.
    const stack = [[start.id, [start.id]]]
    const seen = new Set()
    while (stack.length) {
      const [id, path] = stack.pop()
      pathsWalked++
      for (const next of (downstream.get(id) || [])) {
        if (path.includes(next)) { problems.push({ code: 'CYCLE', at: next, path: path.concat(next) }); continue }
        const node = byId.get(next)
        if (!node) continue
        if (HEIGHT_WRITERS.includes(type(node))) {
          problems.push({
            code: 'ORDER_DERIVED_BEFORE_GEOMETRY',
            producer: start.id, producerType: type(start),
            writer: next, writerType: type(node),
            path: path.concat(next),
          })
          continue          // report the first crossing on this path, not every node beyond it
        }
        const key = next + '<' + id
        if (seen.has(key)) continue
        seen.add(key)
        stack.push([next, path.concat(next)])
      }
    }
  }
  return { problems, stats: { producers: nodes.filter(n => DERIVED_PRODUCERS.includes(type(n))).length, pathsWalked } }
}

/** Lens validation: a derived map may never be declared as carried state. */
export function validateLens(declarations, auxMaps) {
  const problems = []
  for (const { mapId, lens } of declarations || []) {
    const known = auxMaps[mapId]
    if (!known) continue
    if (known.lens === 'derived' && (lens === 'state' || lens === 'continued')) {
      problems.push({ code: 'LENS_CARRIED_DERIVED', mapId, declared: lens, expected: known.lens })
    }
  }
  return problems
}
