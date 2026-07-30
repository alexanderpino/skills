// The plugin registry.
//
// A node type is a manifest plus a pure function - `{cat, name, ins, params, eval}` - which is what
// `TYPES` in legacy.js has always been. This module gives that shape a name and a place to live, so
// the 60 entries can move out one category at a time instead of in one unreviewable commit.
//
// THE IMPORT SHAPE, and why it is what it is. A plugin module looks like:
//
//     import { P } from '../../core/params.js';     // ACYCLIC - read at module-evaluation time
//     import { blendField } from '../../legacy.js'; // cyclic  - read at CALL time only
//     export default definePlugin({ ... params: [P.slider(...)], eval: (p, ins) => blendField(...) })
//
// Those two imports are not the same kind of thing, and the difference decides the whole design:
//
//   * `params:` is evaluated when the module body runs. In the legacy<->plugin cycle the PLUGIN
//     evaluates first, as a dependency, so anything it touches at top level must come from a module
//     outside the cycle. That is the entire reason params.js was extracted before this file.
//   * `eval:` is a closure. Its body does not run until the graph is evaluated, by which time
//     legacy.js has finished initialising. A cyclic import used only inside a function body is
//     therefore safe, and this was measured before being relied on - a four-file fixture with the
//     same shape returns the right value through the cycle.
//
// The long-term direction is that `eval` bodies stop importing from legacy.js at all and take their
// helpers from src/core/ instead. That cannot happen yet: the field primitives (newField, and
// through it fieldW/fieldH/latticeRows/terrainDef) are the most entangled thing in the file, and
// pulling them out first was measured to be the worst available first cut. So the cycle is a
// deliberate, bounded intermediate state, not an accident.

/** Every registered node type, keyed by its `type` string. */
export const PLUGINS = {}

/**
 * Register a node type. Returns the definition so a module can `export default definePlugin({...})`
 * and stay a single expression.
 *
 * Duplicate registration is a hard error rather than a silent overwrite. A duplicate means two
 * modules claim the same node type, and whichever loaded last would win - the same class of defect
 * as the duplicate `pointSegmentDistance` that blocked the module split, where a later declaration
 * quietly shadowed an earlier one and nothing said so.
 */
export function definePlugin(def) {
  if (!def || typeof def !== 'object') throw new Error('definePlugin: expected a definition object')
  const { type } = def
  if (!type || typeof type !== 'string') throw new Error('definePlugin: a plugin needs a string `type`')
  if (Object.prototype.hasOwnProperty.call(PLUGINS, type)) {
    throw new Error(`definePlugin: "${type}" is already registered — two modules claim the same node type`)
  }
  for (const k of ['cat', 'name', 'eval']) {
    if (!(k in def)) throw new Error(`definePlugin("${type}"): missing required key "${k}"`)
  }
  if (typeof def.eval !== 'function') throw new Error(`definePlugin("${type}"): eval must be a function`)
  PLUGINS[type] = def
  return def
}

/**
 * Fold the registered plugins into the legacy TYPES object.
 *
 * Asserts that no plugin silently replaces an entry that is still declared inline. During the
 * migration both forms coexist, and an extraction that leaves the inline copy behind would look
 * like it worked - the digest would still pass, because the surviving inline entry produces the
 * same output - while the plugin module sat unused. That is a migration that reports progress it
 * has not made.
 */
export function mergePlugins(inlineTypes) {
  const clash = Object.keys(PLUGINS).filter((t) => Object.prototype.hasOwnProperty.call(inlineTypes, t))
  if (clash.length) {
    throw new Error(`mergePlugins: ${clash.length} type(s) exist BOTH as a plugin and inline in TYPES `
      + `— the inline copy was not removed: ${clash.join(', ')}`)
  }
  return { ...inlineTypes, ...PLUGINS }
}
