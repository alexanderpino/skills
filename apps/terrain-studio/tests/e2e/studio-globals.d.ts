/**
 * Ambient declarations for the globals that terrain-architect/studio/index.html exposes to page
 * context, so `page.evaluate(() => nodes.length)` type-checks in an editor.
 *
 * Two different kinds of global live here and both are reachable by a bare identifier:
 *   - top-level `let`/`const` in the app's single classic <script> (`nodes`, `cam`, `RES`, …),
 *     which land in the global LEXICAL environment, not on `window`;
 *   - named-element globals (`topbar`, `fileMenu`, …), which the HTML parser puts on `window`.
 *
 * `declare global { var … }` is the one form that types both for a bare reference. These are
 * intentionally loose — this file documents the surface the specs touch, it does not model the app.
 */
export {}

type StudioNode = {
  id: number
  type: string
  params: Record<string, unknown>
  _field?: unknown
  _dirty?: boolean
  _thumb?: unknown
}

declare global {
  // --- graph document ---------------------------------------------------------
  var nodes: StudioNode[]
  var edges: Array<{ from: number; to: number; slot: number }>
  var selected: StudioNode | null
  var undoStack: unknown[]
  var redoStack: unknown[]
  var historyReady: boolean
  function outputNode(): StudioNode | null
  function evalGraph(): void
  function buildIndex(): void
  var TYPES: Record<string, { params: Array<Record<string, any>> }>
  function buildField(param: Record<string, any>): HTMLElement

  // --- build profile ----------------------------------------------------------
  var RES: number
  var TARGET_RES: number
  var AUTO: boolean

  // --- viewport / camera ------------------------------------------------------
  var cam: { az: number; el: number; dist: number; target: [number, number, number] }
  var planView: boolean
  var gl: WebGL2RenderingContext
  function cameraEye(): [number, number, number]
  function cameraNear(): number
  function surfaceHeight(x: number, z: number): number

  // --- named elements ---------------------------------------------------------
  var topbar: HTMLElement
  var fileMenu: HTMLElement
  var mainMenu: HTMLElement
  var compactFile: HTMLElement
  var buildSettings: HTMLElement
  var commandMenu: HTMLElement
  var commandBtn: HTMLElement
  var resSel: HTMLSelectElement
  var profileRes: HTMLElement
  var profileDetail: HTMLElement
}
