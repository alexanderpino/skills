// Parameter defaults that a plugin needs at MODULE-EVALUATION time.
//
// Why these cannot live in legacy.js: a plugin's `params:` array is built when its module body
// runs, and in the legacy<->plugin cycle the plugin runs FIRST, while every legacy binding is still
// in its temporal dead zone. A default read from there throws "Cannot access X before
// initialization" and the whole module graph fails to load.
//
// So anything a params array reads directly — a curve shape, a preset table, a default array —
// belongs here, outside the cycle, alongside params.js. `eval` bodies are a different matter: they
// run long after legacy.js has finished, and may import from it freely.
//
// scripts/check-plugin-tdz.cjs enforces this mechanically: it walks every plugin outside any
// function body and fails on a reference to a legacy import. Run it after every extraction batch —
// `vite build` will NOT catch this, because bundling flattens the graph into one scope where
// hoisting resolves what native ESM does not.

/**
 * Default skirt profile for the Mountain generator: the falloff from peak (0) to base (1).
 *
 * A function rather than a shared array on purpose — the curve editor mutates what it is given, so
 * handing every Mountain node the same array object would make one node's edit change all of them.
 */
export const mountainSkirtDefault = () => [
  [0, 1], [.08, .975], [.18, .90], [.31, .72], [.44, .655], [.60, .40], [.78, .15], [.94, 0], [1, 0],
]
