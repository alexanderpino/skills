#!/usr/bin/env python3
"""Add OKF v0.2 frontmatter to the water-physics and terrain-renderer docs.

    python3 tools/okf_apply.py            # write the headers
    python3 tools/okf_apply.py --dry-run  # print what would change

WHAT OKF IS. The Open Knowledge Format, version 0.2 -- a vendor-neutral
convention for knowledge as plain markdown with YAML frontmatter, published by
Google Cloud at github.com/GoogleCloudPlatform/knowledge-catalog (`okf/SPEC.md`,
read 2026-08-24). Only `type` is required (SPEC section 11); `title`,
`description`, `resource` and `tags` are recommended; and v0.2 adds the
optional provenance / trust / lifecycle families this file uses.

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
   sources=[('chapter', 'references/12-water-physics.md', 'The water chapter'),
            ('provenance', 'references/12b-water-provenance.md', 'Sources and tiers')]),
 'water-physics/references/12-water-physics.md': dict(
   type='Reference', tags=['water', 'optics', 'waves', 'foam', 'caustics'],
   description='The mechanism side of water: the interface and its two Fresnel constants, where a body colour comes from, shoaling and breaking, foam as a covering measure, and the six axes the rest of the chapter is a point on.',
   verified=[('process:validate_chapter.py', VERIFIED_AT)],
   sources=[('derivations', 'references/12a-water-derivations.md', 'The algebra behind each number'),
            ('provenance', 'references/12b-water-provenance.md', 'Every source and tier'),
            ('impl', 'reference-impl/', 'The implementations the numbers were measured on')]),
 'water-physics/references/12a-water-derivations.md': dict(
   type='Reference', tags=['water', 'derivations', 'pseudocode'],
   description='The derivations behind every number the water chapter quotes in a line, each naming the test that guards it or stating that none does.',
   sources=[('impl', 'reference-impl/', 'The executable form of the same material')]),
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

 'terrain-renderer/SKILL.md': dict(
   type='Skill', tags=['terrain', 'rendering', 'lod', 'streaming'],
   description='Entry point to the terrain-renderer skill: the paradigms, the routing table from a symptom on screen to a mechanism, and where each claim is warranted.',
   sources=[('index', 'references/00-index.md', 'The technique index')]),
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


def git_time(path):
    """Last commit time of a file, ISO 8601. Never the moment this script ran."""
    out = subprocess.run(['git', 'log', '-1', '--format=%cI', '--', path],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if not out:
        raise SystemExit('%s is untracked; refusing to stamp a made-up time' % path)
    # git gives +02:00 offsets; OKF wants ISO 8601, which that is. Normalise
    # to UTC 'Z' form only when the offset is already zero.
    return out.replace('+00:00', 'Z')


def title_of(path):
    """The document's own H1 -- never invented, never derived from the filename."""
    for line in open(path, encoding='utf-8'):
        if line.startswith('# '):
            return line[2:].strip()
    raise SystemExit('%s has no H1 to take a title from' % path)


def yaml_quote(s):
    if any(c in s for c in ':#\'"[]{}&*?|>%@`') or s.strip() != s:
        return '"%s"' % s.replace('\\', '\\\\').replace('"', '\\"')
    return s


def build(relpath, spec):
    full = os.path.join(ROOT, relpath)
    src = open(full, encoding='utf-8').read()
    existing = ''
    if src.startswith('---\n'):
        end = src.find('\n---\n', 3)
        if end < 0:
            raise SystemExit('%s has an unterminated frontmatter block' % relpath)
        existing = src[4:end + 1]
        body = src[end + 5:]
    else:
        body = src

    lines = ['---', 'type: %s' % yaml_quote(spec['type'])]
    # ⚠️ EXISTING KEYS ARE KEPT, NOT REPLACED. The SKILL.md files carry the
    # loader's own `name` and `description`; OKF says consumers must tolerate
    # unknown keys, and the converse matters more here -- dropping `name` would
    # break the skill. Existing keys are re-emitted verbatim after `type`.
    if existing:
        lines.append(existing.rstrip('\n'))
    else:
        lines.append('title: %s' % yaml_quote(title_of(full)))
        lines.append('description: %s' % yaml_quote(spec['description']))
    if spec.get('tags'):
        lines.append('tags: [%s]' % ', '.join(spec['tags']))
    lines.append('status: stable')
    lines.append('generated: { by: %s, at: %s }' % (AGENT, git_time(relpath)))
    for by, at in spec.get('verified', []):
        lines.append('verified: { by: %s, at: %s }' % (by, at))
    if spec.get('sources'):
        lines.append('sources:')
        for sid, res, title in spec['sources']:
            lines.append('  - id: %s' % sid)
            lines.append('    resource: %s' % res)
            lines.append('    title: %s' % yaml_quote(title))
    lines.append('---')
    return full, '\n'.join(lines) + '\n' + body, src


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
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
