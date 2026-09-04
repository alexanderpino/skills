#!/usr/bin/env python3
"""Add OKF v0.2 frontmatter to the water-physics and terrain-renderer docs.

    python3 tools/okf_apply.py            # write the headers
    python3 tools/okf_apply.py --dry-run  # print what would change

⚠️ HISTORICAL. This is a one-shot migration that has already been applied, and its
~150 hard-coded paths are PRE-MOVE: `terrain-architect/...` and `terrain-renderer/...`
are now under `obsolete/`. The paths are left as they were rather than rewritten,
because they record which files this migration actually touched and when. Re-running
it as-is will find nothing. If it is ever needed again, prefix the two skill roots
with `obsolete/` at that point rather than editing this record now.

WHAT OKF IS. The Open Knowledge Format, version 0.2 -- a vendor-neutral
convention for knowledge as plain markdown with YAML frontmatter, published by
Google Cloud. Only `type` is required (SPEC section 11); `title`,
`description`, `resource` and `tags` are recommended; and v0.2 adds the
optional provenance / trust / lifecycle families this file uses.

⚠️ THE CANONICAL HOME MOVED, and this file cited the old one for a round.
The spec now lives at github.com/GoogleCloudPlatform/open-knowledge-format,
`SPEC.md` at the repository root -- not `knowledge-catalog/okf/SPEC.md`, which
still resolves today and is where this was first read. The two are
byte-identical as of 2026-08-24, so nothing read from the old path was wrong;
the citation was simply pointing at a location that is no longer canonical,
which is the kind of rot a reader cannot detect from the text.

WHY IT FITS HERE WITH ALMOST NOTHING NEW. This project already had the SUBSTANCE
of everything v0.2 added and only lacked the frontmatter to say it:

    OKF v0.2                         what already existed here
    ------------------------------   -------------------------------------
    sources + credibility signals    the P/T/D/F/N/? tiers and 12b
    verified: {by, at}               the suites and their guarded rows
    section 10, attested computation validate_chapter.py, near-exactly
    status / lifecycle               the gap register

⚠️ THE ONE RULE THIS FILE ENFORCES ABOVE THE SPEC. `verified` is written ONLY
where something actually verifies the DOCUMENT -- not where a suite verifies
code the document happens to describe. Exactly one file qualifies:
`12-water-physics.md`, whose quoted numbers `validate_chapter.py` re-derives.
Everything else is left with no `verified` key, which OKF section 5.3 reads as
the trust tier **unverified**, and that is the honest answer. Stamping
`verified` on twenty-eight documents nothing checks would turn a real signal
into decoration, which is the failure this whole project is built against.

⚠️ ON `generated.by`. The actor convention (section 7) wants `<producer>/<version>`
for agents. This repository's own rule forbids putting a model identifier in
anything pushed to it, so the automated-process form `process:<id>` is used
instead. It is accurate -- these documents were produced by an agent session --
and it carries no version claim that would go stale or leak.

TIMESTAMPS ARE NOT INVENTED. `generated.at` is each file's own last commit
time, read from git, not the moment this script happened to run.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

AGENT = 'process:claude-code'
# When validate_chapter.py was last run green over the document it guards.
VERIFIED_AT = '2026-08-24T11:51:35Z'

# type, title, description, tags, and any genuine `sources` entries.
# Descriptions are written per document rather than templated: a description is
# what a consumer sees in a search snippet, and a generic one is worse than none.
DOCS = {
 'water-physics/SKILL.md': dict(
   type='Skill', tags=['water', 'rendering', 'physics', 'optics'],
   description='Entry point to the water-physics skill: what it warrants, which of its four suites arbitrates each claim, and where every number is derived.',
   sources=[('chapter', '/references/12-water-physics.md', 'The water chapter'),
            ('provenance', '/references/12b-water-provenance.md', 'Sources and tiers')]),
 'water-physics/references/12-water-physics.md': dict(
   type='Reference', tags=['water', 'optics', 'waves', 'foam', 'caustics'],
   description='The mechanism side of water: the interface and its two Fresnel constants, where a body colour comes from, shoaling and breaking, foam as a covering measure, and the six axes the rest of the chapter is a point on.',
   verified=[('process:validate_chapter.py', VERIFIED_AT)],
   sources=[('derivations', '/references/12a-water-derivations.md', 'The algebra behind each number'),
            ('provenance', '/references/12b-water-provenance.md', 'Every source and tier'),
            ('impl', '/reference-impl/', 'The implementations the numbers were measured on')]),
 'water-physics/references/12a-water-derivations.md': dict(
   type='Reference', tags=['water', 'derivations', 'pseudocode'],
   description='The derivations behind every number the water chapter quotes in a line, each naming the test that guards it or stating that none does.',
   sources=[('impl', '/reference-impl/', 'The executable form of the same material')]),
 'water-physics/references/12b-water-provenance.md': dict(
   type='Provenance', tags=['water', 'sources', 'citations', 'tiers'],
   description='Every source, tier and unverified mark behind the water chapters, restated so it reads alone. Read before citing anything out of this skill.'),
 'water-physics/references/12c-uncovered.md': dict(
   type='Gap Register', tags=['water', 'gaps', 'method'],
   description='The six gaps this skill knew it had and how each closed: five by finding a missing axis, one by finding a missing source.'),
 'water-physics/reference-impl/README.md': dict(
   type='Implementation Notes', tags=['water', 'pool', 'optics', 'suite'],
   description='The pool: a 1.40 m domestic basin used as the cleanest available optics laboratory, its modules, and what its suite establishes.'),
 'water-physics/reference-impl/README-beach.md': dict(
   type='Implementation Notes', tags=['water', 'coast', 'waves', 'foam', 'suite'],
   description='The open coast at Aljezur: bathymetry and the morphodynamic loop, the wave transform, diffraction, foam as a realisation, and the camera.'),
 'water-physics/reference-impl/evidence/README.md': dict(
   type='Evidence', tags=['water', 'frames'],
   description='Frames written by the pool renderer, kept as the visual record its suite rows refer to.'),
 'water-physics/reference-impl/photos/README.md': dict(
   type='Evidence', tags=['water', 'photographs', 'licences'],
   description='Nine openly-licensed reference photographs and the full licence trail for each.'),
 'water-physics/raster-impl/README.md': dict(
   type='Implementation Notes', tags=['water', 'screen-space', 'raster', 'suite'],
   description='The real-time screen-space pass, its LUT and its wave surface: the only place in this skill where approximation error can be measured at all.'),
 'water-physics/raster-impl/evidence/README.md': dict(
   type='Evidence', tags=['water', 'frames'],
   description='Frames written by the screen-space raster pass.'),

 # --- terrain-architect ------------------------------------------------------
 # ⚠️ SEVEN OF THESE CARRY `verified`, AGAINST ONE IN WATER-PHYSICS, AND THE
 # DIFFERENCE IS REAL RATHER THAN GENEROUS. This skill's harnesses check
 # DOCUMENTS, not only code: test_atom_coverage fails when ATOM-COVERAGE.md and
 # the modules disagree, test_audit_drift when an audit's claims outrun the
 # code, test_pseudocode_drift when a chapter's pseudocode defaults do, and the
 # two anatomy harnesses when a figure stops drawing the geometry its chapter
 # claims. Every other document here is left `unverified`, which is the honest
 # reading of a chapter nothing re-derives.
 'terrain-architect/SKILL.md': dict(
   type='Skill', tags=['terrain', 'generation', 'procedural', 'heightfield'],
   description='Entry point to the terrain-architect skill: the algorithm index, the provenance tiers, and the reference implementation each claim is measured on.',
   sources=[('index', '/references/00-index.md', 'The algorithm index'),
            ('validation', '/reference-impl/VALIDATION.md', 'The validity evidence ledger')]),
 'terrain-architect/evals/README.md': dict(
   type='Evals', tags=['terrain', 'evals'],
   description='How the capability and trigger evals are structured and what each axis is meant to probe.'),
 'terrain-architect/reference-impl/README.md': dict(
   type='Implementation Notes', tags=['terrain', 'reference-impl', 'atoms'],
   description='The reference implementation: what each module owns, how the pieces compose into a generator, and which audit answers which question.',
   verified=[('process:test_audit_drift.py', VERIFIED_AT)]),
 'terrain-architect/reference-impl/VALIDATION.md': dict(
   type='Provenance', tags=['terrain', 'validity', 'benchmarks'],
   description='The validity evidence ledger: five rungs from dimensional consistency to agreement with real DEMs, kept explicit about what each rung does and does not prove.',
   verified=[('process:test_audit_drift.py', VERIFIED_AT)]),
 'terrain-architect/reference-impl/ATOM-COVERAGE.md': dict(
   type='Coverage Register', tags=['terrain', 'atoms', 'scope'],
   description='Which atomic bases are implemented, which are documented but deliberately deferred, and the harness that keeps the list honest against the modules.',
   verified=[('process:test_atom_coverage.py', VERIFIED_AT)]),
 'terrain-architect/reference-impl/NODE-PARITY-AUDIT.md': dict(
   type='Audit', tags=['terrain', 'parity', 'gaea', 'world-machine', 'houdini'],
   description='What Gaea, World Machine and Houdini ship node by node, and which atomic capabilities are genuinely missing here after composites are excluded.',
   verified=[('process:test_audit_drift.py', VERIFIED_AT)]),
 'terrain-architect/reference-impl/SIMULATION-AUDIT.md': dict(
   type='Audit', tags=['terrain', 'sota', 'simulation'],
   description='A per-process SOTA scorecard against both the commercial and the academic frontier, with the metrics that would settle each verdict.'),
 'terrain-architect/reference-impl/CANON-COMPARISON.md': dict(
   type='Audit', tags=['terrain', 'canon', 'comparison'],
   description='Every atom judged side by side against a canonical published output of the same algorithm, with per-atom verdicts.'),
 'terrain-architect/reference-impl/GROUNDING.md': dict(
   type='Provenance', tags=['terrain', 'grounding', 'sources'],
   description='Where each sandbox behaviour comes from and which cross-check covers it, node by node.'),
 'terrain-architect/reference-impl/HYPERREALISM.md': dict(
   type='Audit', tags=['terrain', 'realism', 'roadmap'],
   description='What each archetype would still need to read as real, and where the numpy sandbox honestly tops out.'),
 'terrain-architect/reference-impl/ARCHETYPES.md': dict(
   type='Implementation Notes', tags=['terrain', 'archetypes'],
   description='The archetype compositions: which atoms each named landscape is built from, in order.'),
 'terrain-architect/reference-impl/GALLERY.md': dict(
   type='Evidence', tags=['terrain', 'figures'],
   description='The committed visual reference montages and the script that regenerates each one.'),
 'terrain-architect/reference-impl/REVIEW-BRIEF.md': dict(
   type='Review Brief', tags=['terrain', 'review'],
   description='The standing brief an external reviewer works from, and the capability grid it refers to.',
   verified=[('process:test_audit_drift.py', VERIFIED_AT)]),

 'terrain-architect/references/00-index.md': dict(
   type='Index', tags=['index', 'routing', 'tiers'],
   description="The skill's map of its own knowledge: every mechanism, its provenance tier, and the chapter that owns it."),
 'terrain-architect/references/01-noise.md': dict(
   type='Reference', tags=['noise', 'fbm', 'fractal'],
   description='Noise as the base layer: Perlin, value, simplex, Worley and Gabor, the fractal compositions over them, and the lattice pinch points that make lacunarity exactly 2 a defect.',
   verified=[('process:test_pseudocode_drift.py', VERIFIED_AT)]),
 'terrain-architect/references/02-macro-tectonics.md': dict(
   type='Reference', tags=['tectonics', 'uplift', 'isostasy'],
   description='Continental form before erosion: plate uplift, fault scarps and the isostatic response that decides what the erosion runs on.'),
 'terrain-architect/references/03-flow-routing.md': dict(
   type='Reference', tags=['flow', 'd8', 'mfd', 'drainage'],
   description='Depression filling and the routing family — D8, D-infinity, MFD and the hybrid — with the concentration statistic that separates them and reverses at low relief.',
   verified=[('process:test_flow_anatomy.py', VERIFIED_AT)]),
 'terrain-architect/references/04-erosion-hydraulic.md': dict(
   type='Reference', tags=['erosion', 'stream-power', 'droplet'],
   description='Stream power, droplet and pipe erosion: what each one is a model OF, and which is right for a given scale.'),
 'terrain-architect/references/05-erosion-thermal-aeolian.md': dict(
   type='Reference', tags=['erosion', 'thermal', 'aeolian', 'dunes'],
   description='Talus and mass wasting by angle of repose, and the Bagnold-grounded aeolian transport that builds dunes.'),
 'terrain-architect/references/06-analysis-masks.md': dict(
   type='Reference', tags=['analysis', 'masks', 'curvature'],
   description='Deriving slope, curvature, aspect and flow-based masks from a heightfield, and the estimator errors each one carries.'),
 'terrain-architect/references/07-scatter.md': dict(
   type='Reference', tags=['scatter', 'poisson', 'placement'],
   description='Blue-noise and density-driven scatter, layer interactions, and why variable density is the hard case.'),
 'terrain-architect/references/08-output-contract.md': dict(
   type='Reference', tags=['output', 'contract', 'export'],
   description='What a generator must export and in what units: the field registry, precision doctrine, and the tiling and seam rules.'),
 'terrain-architect/references/09-verification.md': dict(
   type='Reference', tags=['verification', 'metrics', 'anisotropy'],
   description='How each mechanism is checked: the estimator ladder, the controls that make a metric evidence, and the lattice-anisotropy trap that scores a broken operator perfectly.',
   verified=[('process:test_anatomy_figures.py', VERIFIED_AT)]),
 'terrain-architect/references/10-primitives-ops-filters.md': dict(
   type='Reference', tags=['primitives', 'sdf', 'filters', 'warp'],
   description='The SDF and gradient primitives, the combiners, and the three distinct roles a curve plays — the distinction that costs the most rebuilds when missed.'),
 'terrain-architect/references/11-geological.md': dict(
   type='Reference', tags=['geology', 'strata', 'karst'],
   description='Strata, lithology contrast, karst, duricrust and relief inversion: structure the erosion inherits rather than invents.'),
 'terrain-architect/references/12-glacial-coastal.md': dict(
   type='Reference', tags=['glacial', 'coastal', 'surf', 'sia'],
   description='Glacial carving on the shallow-ice approximation, and the coastal chain from radiation stress through nearshore currents to the bar and rip system.'),
 'terrain-architect/references/13-climate-ecosystem.md': dict(
   type='Reference', tags=['climate', 'biome', 'moisture'],
   description='Insolation, moisture and temperature fields, and the biome assignment that reads them.'),
 'terrain-architect/references/14-graph-runtime.md': dict(
   type='Reference', tags=['graph', 'runtime', 'scheduling'],
   description='The node graph as an executable object: evaluation order, the resolution pyramid, memory and scheduling.'),
 'terrain-architect/references/15-gpu-realtime.md': dict(
   type='Reference', tags=['gpu', 'realtime', 'determinism'],
   description='What moves to the GPU and what cannot, and the determinism the runtime path has to preserve.'),
 'terrain-architect/references/16-arid-desert.md': dict(
   type='Reference', tags=['arid', 'desert', 'fans'],
   description='Inselbergs, alluvial fans, evaporite crusts and wadis: the arid assemblage and what each one requires upstream.'),
 'terrain-architect/references/17-periglacial.md': dict(
   type='Reference', tags=['periglacial', 'permafrost'],
   description='Patterned ground, thermokarst and pingos, on the Kessler & Werner sorting model.'),
 'terrain-architect/references/18-materials.md': dict(
   type='Reference', tags=['materials', 'splat'],
   description='Deriving a material stack from slope, curvature and drainage rather than painting one.'),
 'terrain-architect/references/19-lava.md': dict(
   type='Reference', tags=['lava', 'volcanic', 'rheology'],
   description='Lava as a Bingham fluid: the driving stress, the yield behaviour, and the flow-length limit that follows.'),
 'terrain-architect/references/20-archetypes.md': dict(
   type='Reference', tags=['archetypes', 'blueprints'],
   description='Named landscapes as ordered compositions of atoms, each with the geomorphology it still owes.'),
 'terrain-architect/references/21-clean-room-implementation.md': dict(
   type='Reference', tags=['implementation', 'clean-room', 'licensing'],
   description='How to reimplement these algorithms in an engine without copying source, and where the licence boundary actually sits.'),
 'terrain-architect/references/22-open-source-grounding.md': dict(
   type='Provenance', tags=['grounding', 'open-source'],
   description='Which open-source implementations each algorithm was checked against, and which remain port targets rather than reimplementations.'),
 'terrain-architect/references/23-generator-blueprint.md': dict(
   type='Reference', tags=['blueprint', 'pipeline'],
   description='The whole pipeline assembled: pre-cooked and runtime paths, and the handoffs between them.'),
 'terrain-architect/references/24-voxel-streaming-generation.md': dict(
   type='Reference', tags=['voxel', 'streaming', 'chunks'],
   description='Generation for volumetric worlds: chunk-local determinism, caves and overhangs as a separate paradigm from the heightfield.'),
 'terrain-architect/references/25-planetary-spherical.md': dict(
   type='Reference', tags=['planetary', 'sphere', 'projection'],
   description='Cube-sphere and geodesic parameterisations, their distortion, and what changes when the domain has no edges.'),
 'terrain-architect/references/26-hexagonal-grids.md': dict(
   type='Reference', tags=['hex', 'grid', 'tiling'],
   description='The hexagonal working grid: two vertex classes, the rhombille tiling, the three meshes over one field, and what corner-only sampling costs.',
   verified=[('process:test_anatomy_figures.py', VERIFIED_AT)]),
 'terrain-architect/references/27-engine-data-handoff.md': dict(
   type='Reference', tags=['handoff', 'auxiliary-maps', 'registry'],
   description='What the generator hands the renderer, as a registry with units and lifetimes rather than a folder of images.'),
 'terrain-architect/references/28-liquids.md': dict(
   type='Reference', tags=['liquids', 'optics', 'cdom'],
   description='Per-body water identity from its causes: CDOM darkens and sediment brightens, and the constants a renderer needs follow from the catchment.'),
 'terrain-architect/references/99-papers.md': dict(
   type='Bibliography', tags=['papers', 'bibliography'],
   description='Every source this skill cites, with the tier at which it was read.'),

 'terrain-renderer/SKILL.md': dict(
   type='Skill', tags=['terrain', 'rendering', 'lod', 'streaming'],
   description='Entry point to the terrain-renderer skill: the paradigms, the routing table from a symptom on screen to a mechanism, and where each claim is warranted.',
   sources=[('index', '/references/00-index.md', 'The technique index')]),
 'terrain-renderer/references/00-index.md': dict(
   type='Index', tags=['terrain', 'index', 'routing'],
   description='The technique index: every mechanism in this skill, its tier, and the chapter that owns it.'),
 'terrain-renderer/references/01-heightfield-lod.md': dict(
   type='Reference', tags=['terrain', 'lod', 'clipmap', 'cdlod', 'cbt'],
   description='Heightfield level of detail from geomipmapping to concurrent binary trees, with the screen-space error metric that orders them.'),
 'terrain-renderer/references/02-cluster-virtualized-geometry.md': dict(
   type='Reference', tags=['terrain', 'nanite', 'meshlet', 'clusters'],
   description='Cluster and meshlet virtualized geometry applied to terrain, and where the Nanite family stops being the right answer.'),
 'terrain-renderer/references/03-engine-terrain-unreal.md': dict(
   type='Reference', tags=['terrain', 'unreal', 'landscape', 'engine'],
   description='Engine-native terrain systems: Unreal Landscape, Nanite Landscape and Mesh Terrain, and what each one fixes the shape of.'),
 'terrain-renderer/references/04-voxel-blocky.md': dict(
   type='Reference', tags=['terrain', 'voxel', 'blocky', 'greedy-meshing'],
   description='Blocky voxel rendering: meshing, face culling, greedy merging and the streaming shape the Minecraft family settled on.'),
 'terrain-renderer/references/05-voxel-smooth-isosurface.md': dict(
   type='Reference', tags=['terrain', 'voxel', 'isosurface', 'marching-cubes', 'dual-contouring'],
   description='Smooth voxel terrain: isosurface extraction, the marching-cubes case count and its ambiguous faces, dual methods, and LOD across chunk seams.'),
 'terrain-renderer/references/06-tiled-streaming.md': dict(
   type='Reference', tags=['terrain', 'streaming', 'tiles', 'budget'],
   description='Tiled worlds and streaming: residency budgets, prefetch radius, and the arithmetic that decides whether a tile arrives in time.'),
 'terrain-renderer/references/07-materials-virtual-texturing.md': dict(
   type='Reference', tags=['terrain', 'materials', 'splatting', 'virtual-texturing'],
   description='Terrain materials, splatting and virtual texturing, including the cache-invalidation traps that runtime state walks into.'),
 'terrain-renderer/references/08-gpu-driven-culling.md': dict(
   type='Reference', tags=['terrain', 'culling', 'gpu-driven', 'hiz'],
   description='GPU-driven culling and submission: the hierarchical depth pyramid, its mip selection rule, and indirect draw construction.'),
 'terrain-renderer/references/09-planetary-precision.md': dict(
   type='Reference', tags=['terrain', 'planetary', 'precision', 'reversed-z', 'float32'],
   description='Planetary rendering and numerical precision: the float32 binade staircase, reversed-Z, camera-relative transforms and cube-sphere mappings.'),
 'terrain-renderer/references/10-lighting-shadows.md': dict(
   type='Reference', tags=['terrain', 'lighting', 'shadows', 'cascades', 'sky'],
   description='Lighting, shadows and terrain integration: cascade snapping, the sky illuminant, receiver weights and the azimuth fold about solar noon.'),
 'terrain-renderer/references/11-verification-failures.md': dict(
   type='Reference', tags=['terrain', 'verification', 'profiling', 'failures'],
   description='Verification, profiling and the failure catalogue: how each mechanism in this skill is checked, and the symptoms that say it is not.'),
 'terrain-renderer/references/12-water-rendering.md': dict(
   type='Reference', tags=['terrain', 'water', 'rendering', 'architecture'],
   description='The render-side architecture of water: surface LOD, pass ordering, engine-native systems and shoreline integration. Routes to water-physics for every number it quotes.',
   sources=[('physics', '../../water-physics/references/12-water-physics.md', 'The physics this chapter routes to')]),
 'terrain-renderer/references/13-snow-weather-surface-state.md': dict(
   type='Reference', tags=['terrain', 'snow', 'weather', 'surface-state'],
   description='Snow, weather and dynamic surface state as a runtime state machine: its storage, its writers and its readers.'),
 'terrain-renderer/references/14-auxiliary-maps-runtime.md': dict(
   type='Reference', tags=['terrain', 'maps', 'runtime', 'handoff'],
   description='Auxiliary maps at runtime: consuming the generator field registry without re-deriving it in the sampling shader.'),
 'terrain-renderer/references/15-vegetation-scatter.md': dict(
   type='Reference', tags=['terrain', 'vegetation', 'scatter', 'instancing'],
   description='Vegetation and scatter rendering: instancing, impostors, density fields and the LOD boundary where a plant stops being geometry.'),
 'terrain-renderer/references/16-tool-viewports.md': dict(
   type='Reference', tags=['terrain', 'tools', 'viewport', 'authoring'],
   description='Tool viewports: interactive preview rendering for terrain authoring, and why the editor path is not the runtime path.'),
 'terrain-renderer/references/17-roads-decals-physics.md': dict(
   type='Reference', tags=['terrain', 'roads', 'decals', 'physics'],
   description='Roads, decals, runtime modification and the physics handoff, including the replayable stamp list that keeps them cache-safe.'),
 'terrain-renderer/references/18-heightfield-raymarching.md': dict(
   type='Reference', tags=['terrain', 'raymarching', 'relief-mapping'],
   description='Heightfield ray marching from Voxel Space to relief mapping, and the step-count arithmetic that decides whether it is affordable.'),
 'terrain-renderer/references/19-fluid-simulation.md': dict(
   type='Reference', tags=['terrain', 'fluid', 'simulation', 'shallow-water'],
   description='Real-time fluid simulation on terrain: shallow-water and pipe models, their stability limits, and what each one cannot represent.'),
}


# ⚠️ FROZEN, NOT LOOKED UP, AND THE LOOKUP WAS WRONG. `generated.at` is defined
# by SPEC section 5.2 as "the content's last meaningful change". An earlier
# version read it live from `git log -1 -- <path>`, which means the moment this
# header was added BECOMES the answer -- and every future header-only edit
# moves it again, so a purely cosmetic commit would keep claiming the content
# had just changed. The times below were taken once, from the history as it
# stood immediately before the header commit, and they are literals now: a
# content change should move them, and a header change must not.
CONTENT_TIME = {
    'terrain-architect/SKILL.md':
        '2026-08-23T08:47:50Z',
    'terrain-architect/evals/README.md':
        '2026-07-29T13:19:50+02:00',
    'terrain-architect/reference-impl/README.md':
        '2026-08-30T14:13:37Z',
    'terrain-architect/reference-impl/VALIDATION.md':
        '2026-08-30T14:13:37Z',
    'terrain-architect/reference-impl/ATOM-COVERAGE.md':
        '2026-07-28T20:51:26Z',
    'terrain-architect/reference-impl/NODE-PARITY-AUDIT.md':
        '2026-08-30T14:13:37Z',
    'terrain-architect/reference-impl/SIMULATION-AUDIT.md':
        '2026-07-25T19:04:00Z',
    'terrain-architect/reference-impl/CANON-COMPARISON.md':
        '2026-07-25T06:11:37Z',
    'terrain-architect/reference-impl/GROUNDING.md':
        '2026-07-25T06:11:37Z',
    'terrain-architect/reference-impl/HYPERREALISM.md':
        '2026-07-25T06:11:37Z',
    'terrain-architect/reference-impl/ARCHETYPES.md':
        '2026-07-25T06:11:37Z',
    'terrain-architect/reference-impl/GALLERY.md':
        '2026-07-28T21:24:36Z',
    'terrain-architect/reference-impl/REVIEW-BRIEF.md':
        '2026-07-25T06:11:37Z',
    'terrain-architect/references/00-index.md':
        '2026-08-16T09:19:11Z',
    'terrain-architect/references/01-noise.md':
        '2026-08-30T15:58:16Z',
    'terrain-architect/references/02-macro-tectonics.md':
        '2026-08-05T18:01:57Z',
    'terrain-architect/references/03-flow-routing.md':
        '2026-08-30T14:39:04Z',
    'terrain-architect/references/04-erosion-hydraulic.md':
        '2026-07-30T20:29:13Z',
    'terrain-architect/references/05-erosion-thermal-aeolian.md':
        '2026-07-28T20:51:26Z',
    'terrain-architect/references/06-analysis-masks.md':
        '2026-07-29T12:53:41Z',
    'terrain-architect/references/07-scatter.md':
        '2026-07-29T13:19:50+02:00',
    'terrain-architect/references/08-output-contract.md':
        '2026-08-05T17:55:10Z',
    'terrain-architect/references/09-verification.md':
        '2026-08-05T12:21:21Z',
    'terrain-architect/references/10-primitives-ops-filters.md':
        '2026-08-05T18:35:04Z',
    'terrain-architect/references/11-geological.md':
        '2026-07-28T13:10:16Z',
    'terrain-architect/references/12-glacial-coastal.md':
        '2026-08-21T14:22:53Z',
    'terrain-architect/references/13-climate-ecosystem.md':
        '2026-07-29T13:07:20Z',
    'terrain-architect/references/14-graph-runtime.md':
        '2026-07-30T20:39:48Z',
    'terrain-architect/references/15-gpu-realtime.md':
        '2026-07-29T13:07:20Z',
    'terrain-architect/references/16-arid-desert.md':
        '2026-07-28T11:16:00Z',
    'terrain-architect/references/17-periglacial.md':
        '2026-07-28T21:14:16Z',
    'terrain-architect/references/18-materials.md':
        '2026-07-25T06:11:37Z',
    'terrain-architect/references/19-lava.md':
        '2026-07-28T20:51:26Z',
    'terrain-architect/references/20-archetypes.md':
        '2026-07-25T06:11:37Z',
    'terrain-architect/references/21-clean-room-implementation.md':
        '2026-07-20T16:01:56+02:00',
    'terrain-architect/references/22-open-source-grounding.md':
        '2026-07-20T16:01:56+02:00',
    'terrain-architect/references/23-generator-blueprint.md':
        '2026-07-29T13:07:20Z',
    'terrain-architect/references/24-voxel-streaming-generation.md':
        '2026-07-21T12:24:27+02:00',
    'terrain-architect/references/25-planetary-spherical.md':
        '2026-07-28T13:10:16Z',
    'terrain-architect/references/26-hexagonal-grids.md':
        '2026-07-28T21:24:36Z',
    'terrain-architect/references/27-engine-data-handoff.md':
        '2026-08-13T16:58:14Z',
    'terrain-architect/references/28-liquids.md':
        '2026-08-14T08:04:02Z',
    'terrain-architect/references/99-papers.md':
        '2026-08-05T12:21:21Z',
    'terrain-renderer/SKILL.md':
        '2026-08-23T18:35:25Z',
    'terrain-renderer/references/00-index.md':
        '2026-08-23T18:38:25Z',
    'terrain-renderer/references/01-heightfield-lod.md':
        '2026-07-30T09:56:09+02:00',
    'terrain-renderer/references/02-cluster-virtualized-geometry.md':
        '2026-07-30T09:56:09+02:00',
    'terrain-renderer/references/03-engine-terrain-unreal.md':
        '2026-08-23T18:38:25Z',
    'terrain-renderer/references/04-voxel-blocky.md':
        '2026-07-30T04:53:08Z',
    'terrain-renderer/references/05-voxel-smooth-isosurface.md':
        '2026-08-23T18:35:25Z',
    'terrain-renderer/references/06-tiled-streaming.md':
        '2026-08-23T18:38:25Z',
    'terrain-renderer/references/07-materials-virtual-texturing.md':
        '2026-08-23T18:38:25Z',
    'terrain-renderer/references/08-gpu-driven-culling.md':
        '2026-07-30T09:56:09+02:00',
    'terrain-renderer/references/09-planetary-precision.md':
        '2026-08-23T08:47:50Z',
    'terrain-renderer/references/10-lighting-shadows.md':
        '2026-08-23T08:47:50Z',
    'terrain-renderer/references/11-verification-failures.md':
        '2026-08-23T18:35:25Z',
    'terrain-renderer/references/12-water-rendering.md':
        '2026-08-23T20:31:24Z',
    'terrain-renderer/references/13-snow-weather-surface-state.md':
        '2026-08-23T21:30:44Z',
    'terrain-renderer/references/14-auxiliary-maps-runtime.md':
        '2026-08-04T19:10:29Z',
    'terrain-renderer/references/15-vegetation-scatter.md':
        '2026-07-30T09:56:09+02:00',
    'terrain-renderer/references/16-tool-viewports.md':
        '2026-07-30T05:01:00Z',
    'terrain-renderer/references/17-roads-decals-physics.md':
        '2026-07-30T09:56:09+02:00',
    'terrain-renderer/references/18-heightfield-raymarching.md':
        '2026-07-30T09:56:09+02:00',
    'terrain-renderer/references/19-fluid-simulation.md':
        '2026-08-23T08:47:50Z',
    'water-physics/SKILL.md':
        '2026-08-24T09:31:02Z',
    'water-physics/raster-impl/README.md':
        '2026-08-23T08:47:50Z',
    'water-physics/raster-impl/evidence/README.md':
        '2026-08-23T08:47:50Z',
    'water-physics/reference-impl/README-beach.md':
        '2026-08-23T08:47:50Z',
    'water-physics/reference-impl/README.md':
        '2026-08-24T09:31:02Z',
    'water-physics/reference-impl/evidence/README.md':
        '2026-08-23T08:47:50Z',
    'water-physics/reference-impl/photos/README.md':
        '2026-08-23T15:52:23Z',
    'water-physics/references/12-water-physics.md':
        '2026-08-24T09:31:02Z',
    'water-physics/references/12a-water-derivations.md':
        '2026-08-24T09:31:02Z',
    'water-physics/references/12b-water-provenance.md':
        '2026-08-23T08:47:50Z',
    'water-physics/references/12c-uncovered.md':
        '2026-08-24T09:31:02Z',
}


def git_time(path):
    """The frozen content time for a document."""
    t = CONTENT_TIME.get(path)
    if not t:
        raise SystemExit('%s has no frozen content time; add one deliberately'
                         % path)
    return t


def title_of(path):
    """The document's own H1, read from the BODY.

    ⚠️ THE FRONTMATTER IS SKIPPED, and skipping it is the whole point. This
    scanned the raw file for the first line starting with "# " -- and a YAML
    comment starts with "# " too, so on the second run it read this script's
    own marker line and wrote
    `title: --- okf v0.2, written by tools/okf_apply.py ---`
    into every document. A helper that reads plausibly and returns garbage is
    worse than one that raises.
    """
    src = open(path, encoding='utf-8').read()
    if src.startswith('---\n'):
        end = src.find('\n---\n', 3)
        if end >= 0:
            src = src[end + 5:]
    for line in src.split('\n'):
        if line.startswith('# '):
            return line[2:].strip()
    raise SystemExit('%s has no H1 in its body to take a title from' % path)


def yaml_quote(s):
    if any(c in s for c in ':#\'"[]{}&*?|>%@`') or s.strip() != s:
        return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')
    return s


BEGIN = '# --- okf v0.2, written by tools/okf_apply.py -----------------------'
END = '# --- end okf v0.2 ----------------------------------------------------'


def build(relpath, spec):
    """Return (path, new_text, old_text) for one document.

    ⚠️ IDEMPOTENT, AND THE FIRST VERSION WAS NOT. It re-emitted whatever
    frontmatter it found and then appended its own keys, so a second run
    produced `type:` twice and a third produced it three times. The script is
    committed and reads as safe to re-run, which is the worst combination: a
    tool that corrupts what it wrote the first time, silently, on the exact
    operation a maintainer would reach for. The generated keys now live
    between two marker comments and are REPLACED, not appended; anything
    outside the markers -- the loader's own `name` and `description` on a
    SKILL.md -- is preserved untouched.
    """
    full = os.path.join(ROOT, relpath)
    src = open(full, encoding='utf-8').read()
    foreign, body = '', src
    if src.startswith('---\n'):
        end = src.find('\n---\n', 3)
        if end < 0:
            raise SystemExit('%s has an unterminated frontmatter block' % relpath)
        block, body = src[4:end + 1], src[end + 5:]
        # Drop a previously generated region, keep everything else verbatim.
        if BEGIN in block and END in block:
            block = block[:block.index(BEGIN)] + block[block.index(END) + len(END) + 1:]
        foreign = block.strip('\n')

    gen = [BEGIN, 'type: %s' % yaml_quote(spec['type'])]
    # `title` and `description` are only written when the document does not
    # already carry them: a SKILL.md's `description` belongs to the loader.
    if 'title:' not in foreign:
        gen.append('title: %s' % yaml_quote(title_of(full)))
    if 'description:' not in foreign:
        gen.append('description: %s' % yaml_quote(spec['description']))
    if spec.get('tags'):
        gen.append('tags: [%s]' % ', '.join(spec['tags']))
    gen.append('status: stable')
    gen.append('generated: { by: %s, at: %s }' % (AGENT, git_time(relpath)))
    for by, at in spec.get('verified', []):
        gen.append('verified: { by: %s, at: %s }' % (by, at))
    if spec.get('sources'):
        gen.append('sources:')
        for sid, res, title in spec['sources']:
            gen.append('  - id: %s' % sid)
            gen.append('    resource: %s' % res)
            gen.append('    title: %s' % yaml_quote(title))
    gen.append(END)

    # ⚠️ THE GENERATED BLOCK GOES AFTER ANY EXISTING KEYS, NOT BEFORE, and a
    # test in another skill is why. terrain-architect asserts a strict
    # line-by-line frontmatter contract -- `name` on line 1, `description: >-`
    # on line 2 -- which keeps its SKILL.md greppable and diffable. YAML is
    # unordered, so OKF does not care where its keys sit; the local contract
    # does, and the local contract is the one with a test behind it. Putting
    # the block first broke it immediately.
    lines = ['---'] + ([foreign] if foreign else []) + gen + ['---']
    return full, '\n'.join(lines) + '\n' + body, src


def write_index(bundle):
    """Write the bundle-root `index.md` that SPEC sections 8 and 12 describe.

    Two jobs. First, progressive disclosure: a reader or agent sees what is in
    the bundle before opening anything. Second, and the reason this exists at
    all, it is THE ONLY PLACE A BUNDLE MAY DECLARE ITS OWN OKF VERSION
    (section 12) -- `okf_version` in a bundle-root index is the sole exception
    to "index files carry no frontmatter". Without it a consumer has to guess
    which revision these documents target, and guessing is the thing the whole
    format exists to remove.

    Descriptions are read back out of each concept's own frontmatter rather
    than restated, so this file cannot disagree with the documents it lists.
    """
    root = os.path.join(ROOT, bundle)
    groups = {}
    for rel in sorted(DOCS):
        if not rel.startswith(bundle + '/'):
            continue
        inner = rel[len(bundle) + 1:]
        if inner == 'index.md':
            continue
        block, _ = read_frontmatter(os.path.join(ROOT, rel))
        desc = scalar(block, 'description') or ''
        title = scalar(block, 'title') or inner
        group = inner.split('/')[0] if '/' in inner else 'Entry point'
        groups.setdefault(group, []).append((title, inner, desc))
    out = ['---', 'okf_version: "0.2"', '---',
           '# %s' % bundle,
           '',
           'An OKF v0.2 knowledge bundle. Every document below carries its own',
           '`type`, `status` and provenance in frontmatter; the trust tier a',
           'consumer derives from `verified` is deliberately **unverified** on',
           'all but the documents a checker actually re-derives.',
           '']
    for g in sorted(groups):
        out.append('# %s' % g)
        out.append('')
        for title, inner, desc in sorted(groups[g]):
            out.append('* [%s](%s)%s' % (title, inner, ' - ' + desc if desc else ''))
        out.append('')
    path = os.path.join(root, 'index.md')
    open(path, 'w', encoding='utf-8').write('\n'.join(out).rstrip('\n') + '\n')
    return path


def read_frontmatter(path):
    src = open(path, encoding='utf-8').read()
    if not src.startswith('---\n'):
        return '', src
    end = src.find('\n---\n', 3)
    return (src[4:end + 1], src[end + 5:]) if end >= 0 else ('', src)


def scalar(block, name):
    """A top-level scalar, including YAML block scalars.

    ⚠️ BLOCK SCALARS ARE FOLDED HERE, and ignoring them produced visible
    nonsense. A SKILL.md writes its description as `description: >-` followed
    by indented continuation lines; a naive same-line read returns the literal
    ">-" and the generated index listed the skill as
    `[Water Physics](SKILL.md) - >-`. The marker is not the value.
    """
    import re as _re
    m = _re.search(r'^%s:[ \t]*(.*)$' % _re.escape(name), block, _re.M)
    if not m:
        return None
    v = m.group(1).strip()
    if v[:1] in ('>', '|'):
        fold = v[0] == '>'
        lines = block[m.end():].split('\n')[1:]
        out = []
        for line in lines:
            if line.strip() and not line[:1].isspace():
                break                      # dedented: the next top-level key
            out.append(line.strip())
        text = (' ' if fold else '\n').join(x for x in out if x)
        return text.strip()
    return v[1:-1] if len(v) > 1 and v[0] == v[-1] == '"' else v


def main(argv):
    dry = '--dry-run' in argv
    changed = 0
    for rel in sorted(DOCS):
        full, new, old = build(rel, DOCS[rel])
        if new == old:
            continue
        changed += 1
        if dry:
            print('=== %s' % rel)
            print('\n'.join(new.split('\n')[:16]))
            print('...')
        else:
            open(full, 'w', encoding='utf-8').write(new)
    print('%d of %d documents %s' % (changed, len(DOCS),
                                     'would change' if dry else 'written'))
    if not dry:
        for bundle in sorted({r.split('/')[0] for r in DOCS}):
            print('  index: %s' % os.path.relpath(write_index(bundle), ROOT))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
