// Frozen legacy port table — one row per node type measured at the S2.1 sprint start.
//
// This is DATA, not derivation. Port ids are stable identifiers that a saved v2 document stores on
// every edge, so they are seeded ONCE from the measured `def.ins` labels and then never
// recomputed: a rule that regenerates them would silently rewrite every saved graph the day a
// display name changes. That is exactly what ADR-002 forbids — "Display names and array positions
// are never identifiers."
//
// Generated from src/plugins/**/*.js by scanning `type:`, `cat:`, `ins:`, `fieldSemantics:`,
// `passthrough:` and `referenceOnly:`, then committed as literals. Regenerating is a deliberate,
// reviewed act, not a build step.
//
// MEASURED at seeding time:
//   79 types; 17 pure generators with no inputs; exactly one type with no output port (`output`,
//   cat 'out' — matching the `def.cat!=="out"` gate in drawNode and portAt); 30 mask slots, every
//   one labelled exactly "Mask"; 13 types carrying fieldSemantics (11 preserve-primary, 2
//   temperature-pair) and 7 carrying passthrough — 20 deferred outputs in total; and
//   referenceOnly on drawmask slot 0 alone.
//
// WHY EVERY ADAPTED OUTPUT IS UNTYPED HERE (semantic defaults to relativeHeight, unit none):
// ADR-005 keeps legacy terrain typed as heightNormalized until an explicit measured-frame adapter
// exists, and S3/S5 own that migration field by field. Typing these outputs physically now would
// also refuse wiring the app ships today: 30 mask slots are `anyMask`, which requires a
// dimensionless source, so declaring a generator's output as height:m would make every
// generator-into-mask edge illegal. The physical semantics arrive with the stories that own the
// fields, not here.
//
// A deferred output (semanticFrom) resolves its semantic from its inputs at evaluation time, which
// is what fieldSemantics/passthrough already mean today. It declares no semantic or unit of its
// own; validatePortList rejects a port that declares both.

import { RANGE } from './ports.js'

/** Defaults applied to every row below, so the table stays readable and the rules stay in one place. */
export const LEGACY_INPUT_DEFAULTS = Object.freeze({
  kind: 'scalarRaster', storage: 'R32F', components: 1, unit: 'none',
  strictRange: false, required: false, role: 'data', default: null,
})

export const LEGACY_OUTPUT_DEFAULTS = Object.freeze({
  kind: 'scalarRaster', storage: 'R32F', components: 1, unit: 'none',
  semantic: 'relativeHeight', primary: true, group: null, lens: null,
})

const LEGACY_PORTS_RAW = {
  "add": {
    in: [
      { id: "a", name: "A", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "b", name: "B", semantic: "anyScalarRaster", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "aspect": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "blend": {
    in: [
      { id: "a", name: "A", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "b", name: "B", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'agree', ports: ['a', 'b'] } },
  },
  "blur": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "canyon": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "clampn": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "colorerosion": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "sediment", name: "Sediment", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "colormixer": {
    in: [
      { id: "layer1", name: "Layer 1", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "layer2", name: "Layer 2", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "layer3", name: "Layer 3", semantic: "anyScalarRaster", legacySlot: 2 },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'layer1' } },
  },
  "constant": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "crater": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "craterfield": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "curve": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_curvature": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_deposits": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      // S3.4 — the OPTIONAL explicit sediment-state override, and the one row in this table that
      // was ADDED after seeding rather than measured at it. Three notes, because "frozen" is a real
      // property of this file and adding to it needs its reasons on the record:
      //
      //   WHY HERE AND NOT IN THE PLUGIN. `rosterFullyAdapted` (_verify_port_contract.js:294)
      //   asserts all 79 rostered types are served by the adapter, and registry.js:98 opts a type
      //   out of the adapter the moment it declares its own `inputs`. LEGACY_INS_LABELS is DERIVED
      //   from these rows, so adding the slot here keeps the `ins`-drift anchor exact instead of
      //   breaking it. A rostered type that gains a port has to gain it in the adapter's own data.
      //
      //   WHY A PHYSICAL SEMANTIC IS LEGAL ON THIS ONE. The header gives two reasons adapted ports
      //   are untyped: ADR-005's unresolved height frame, and that typing an existing port would
      //   refuse wiring the app ships today. Neither applies — this is a NEW slot that no shipped
      //   document uses, and cover depth in metres is not the disputed elevation frame.
      //
      //   THIS IS NOT A REGENERATION. The header's freeze is against recomputing ids from display
      //   names, which would rewrite every saved edge. `sedimentState` is a new stable id.
      { id: "sedimentState", name: "Sediment state", semantic: "sedimentDepth", unit: "m",
        lens: "state", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_flow": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_heat": {
    in: [
      { id: "temperature", name: "Temperature", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "driver", name: "Driver", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_height": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_occlusion": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_peaks": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_slope": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_sunshadow": {
    in: [
      { id: "height", name: "Height", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_temperature": {
    in: [
      { id: "relativeHeight", name: "Relative height", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "sunVisibility", name: "Sun visibility", semantic: "anyScalarRaster", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_texture": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_wear": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_wind": {
    in: [
      { id: "height", name: "Height", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "d_windmodify": {
    in: [
      { id: "wind", name: "Wind", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "driver", name: "Driver", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "deflate": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "dilate": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "directionalwarp": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "driver", name: "Driver", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "drawmask": {
    in: [
      { id: "reference", name: "Reference", semantic: "anyScalarRaster", legacySlot: 0, role: 'reference' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "erosion2": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "flip": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "fold": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "fracture": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "gradient": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "heightmask": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "histeq": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "hydraulic": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
      // S3.3 — the explicit cover and forcing inputs. Added after seeding, for the same three
      // reasons `d_deposits.sedimentState` above was: the adapter's own data is where a ROSTERED
      // type has to gain a port (registry.js:98 drops a type out of the adapter the moment it
      // declares `inputs:`, and _verify_port_contract.js's `insDrift` anchor is DERIVED from these
      // rows, so adding here keeps the anchor exact); a physical semantic is legal because these
      // are NEW slots no shipped document uses and cover thickness in metres is not ADR-005's
      // disputed elevation frame; and stable new ids are not a regeneration of the frozen ones.
      //
      // OPTIONAL, not required, and that is a decision rather than an oversight. Every hydraulic
      // node in every saved graph has these slots unwired, and a required input would refuse them
      // all. Unwired means "this graph carries no cover", which is bare bedrock — the honest
      // reading, and the one that keeps an unwired graph byte-identical to the pre-S3.3 build.
      // The selectors' `MISSING_REQUIRED_INPUT` rule (core/cover-state.js) is about a node whose
      // ONLY job is to carry a state; hydraulic's job is transport, and it has a defined answer
      // with no cover.
      { id: "soilDepth", name: "Soil depth", semantic: "soilDepth", unit: "m",
        lens: "state", legacySlot: 2 },
      { id: "sedimentDepth", name: "Sediment depth", semantic: "sedimentDepth", unit: "m",
        lens: "state", legacySlot: 3 },
      // ADR-005: "Precipitation remains mm/yr". The unit is the authored one, not metres, because
      // the interesting numbers live at 1e2..1e3 mm/yr and authoring them in m/yr puts a typo below
      // the eye's resolution — the same argument ports.js records for the `mmPerYr` unit itself.
      { id: "precipitation", name: "Precipitation", semantic: "precipitation", unit: "mmPerYr",
        lens: "derived", legacySlot: 4 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "hydrofix": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "import": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "invert": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "island": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "layout": {
    in: [
      { id: "base", name: "Base", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "levels": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "match": {
    in: [
      { id: "source", name: "Source", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "target", name: "Target", semantic: "anyScalarRaster", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "maxmin": {
    in: [
      { id: "a", name: "A", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "b", name: "B", semantic: "anyScalarRaster", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'agree', ports: ['a', 'b'] } },
  },
  "mountain": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "mountainside": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "normalizen": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "output": {
    in: [
      { id: "height", name: "Height", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: null,
  },
  "perlin": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "ridged": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "rugged": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "satmap": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "driver", name: "Driver", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "satmapblend": {
    in: [
      { id: "a", name: "A", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "b", name: "B", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'a' } },
  },
  "sculpt": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "shape": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "sharpen": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "simplex": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "slopemask": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "smax": {
    in: [
      { id: "a", name: "A", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "b", name: "B", semantic: "anyScalarRaster", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "smin": {
    in: [
      { id: "a", name: "A", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "b", name: "B", semantic: "anyScalarRaster", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "snow": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "temperature", name: "Temperature", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "wind", name: "Wind", semantic: "anyScalarRaster", legacySlot: 2 },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "softclip": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "stampn": {
    in: [
      { id: "base", name: "Base", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "patch", name: "Patch", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "streampower": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "uplift", name: "Uplift", semantic: "anyScalarRaster", legacySlot: 1 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 2, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "surface": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "tectonic": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "tempmask": {
    in: [
      { id: "temperature", name: "Temperature", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "terrace": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "thermal": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
      // S3.5 — the explicit cover inputs, added for exactly the three reasons the `hydraulic` row
      // above records: a ROSTERED type has to gain a port in the adapter's own data (registry.js:98
      // drops a type out of the adapter the moment it declares `inputs:`, and LEGACY_INS_LABELS —
      // the `insDrift` anchor — is DERIVED from these rows); a physical semantic is legal because
      // these are NEW slots no shipped document uses and cover thickness in metres is not ADR-005's
      // disputed elevation frame; and stable new ids are not a regeneration of the frozen ones.
      //
      // OPTIONAL, for the same measured reason: every thermal node in every saved graph has these
      // slots unwired, and unwired means "this graph carries no cover", which is bare bedrock.
      // Talus relaxation has a defined answer with no cover, so a REQUIRED input here would refuse
      // every document that ships.
      //
      // Thermal takes no `precipitation`: dry mass-wasting past the angle of repose has no rain
      // term in either kernel (src/legacy.js:2277/2300, src/core/gpu.js:206), and declaring a port
      // nothing consumes is the "declared but never filled" half-gate this sprint already found.
      { id: "soilDepth", name: "Soil depth", semantic: "soilDepth", unit: "m",
        lens: "state", legacySlot: 2 },
      { id: "sedimentDepth", name: "Sediment depth", semantic: "sedimentDepth", unit: "m",
        lens: "state", legacySlot: 3 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "threshold": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
    ],
    out: { id: 'out', name: 'Out' },
  },
  "transform": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "transpose": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "volcano": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
  "warp": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "water": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "temperature", name: "Temperature", semantic: "anyScalarRaster", legacySlot: 1 },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "weathering": {
    in: [
      { id: "in", name: "In", semantic: "anyScalarRaster", legacySlot: 0 },
      { id: "mask", name: "Mask", semantic: "anyMask", legacySlot: 1, role: 'mask' },
    ],
    out: { id: 'out', name: 'Out', semanticFrom: { mode: 'inherit', port: 'in' } },
  },
  "worley": {
    in: [],
    out: { id: 'out', name: 'Out' },
  },
}

/** Materialise a row into full descriptors, applying the defaults above. */
const hydrate = row => ({
  in: row.in.map(port => Object.freeze({ ...LEGACY_INPUT_DEFAULTS, range: RANGE.unbounded(), ...port })),
  out: row.out === null ? null : Object.freeze(
    // A deferred output must not carry a semantic or unit of its own.
    row.out.semanticFrom
      ? { ...LEGACY_OUTPUT_DEFAULTS, semantic: undefined, unit: undefined, range: RANGE.unbounded(), ...row.out }
      : { ...LEGACY_OUTPUT_DEFAULTS, range: RANGE.unbounded(), ...row.out }
  ),
})

export const LEGACY_PORTS = Object.freeze(Object.fromEntries(
  Object.entries(LEGACY_PORTS_RAW).map(([type, row]) => [type, Object.freeze(hydrate(row))])
))

/** The exact type roster measured at seeding time. Membership decides adapter eligibility. */
export const LEGACY_ROSTER = Object.freeze(Object.keys(LEGACY_PORTS_RAW))

/** The exact measured def.ins arrays — the bit-identity anchor for the rebuild-ins mutation. */
export const LEGACY_INS_LABELS = Object.freeze(Object.fromEntries(
  Object.entries(LEGACY_PORTS_RAW).map(([type, row]) => [type, Object.freeze(row.in.map(p => p.name))])
))
