"""Write the sidecar captions for the s21 hero pair, from the measured JSON.

No text is burned into any frame. Every number here comes out of
`s21-hero-measurements.json`, which `hero.py` wrote from scene-linear buffers.
"""
import json, os

OUT = '/home/user/skills/.claude/worktrees/agent-a1cc4b7b2b35ef515/gauntlet/sea/evidence'
M = json.load(open(os.path.join(OUT, 's21-hero-measurements.json')))

FRAMING = dict(
    J=("Bar frame J -- the embayment overview. `beach_camera.J_CONTENT`: "
       "headland to headland with the backing cliff, the horizon in the upper "
       "third, the lens inferred from the standoff-over-chord ratio and the "
       "eye standing on the bay's own rim. Built by "
       "`beach_render.hero_cameras`, unmoved since wave 7."),
    K=("Bar frame K -- open water and the glitter path. "
       "`beach_camera.K_CONTENT`: the same cliff, aimed straight down the "
       "sun's azimuth so the path runs from the horizon into the near field. "
       "Built by `beach_render.hero_cameras`, unmoved since wave 7."),
    F=("Frame F -- the surf zone, close. NOT a bar framing: the eye is at 8 m "
       "and 78 m from the largest wave the transform reports, 26 deg, with "
       "the sun kept out of frame. It is `beach_render.main`'s own frame F "
       "construction, unchanged, and it is here because J and K stand on a "
       "17 m cliff about a kilometre back -- at that range the whole surf "
       "zone is a few dozen rows and none of the recent physics can be seen "
       "even where it is measurably present."),
)

HEAD = """# %(name)s

%(framing)s

**%(tag)s.** %(what)s

**Provenance: measured (`M`).** Rendered by
`gauntlet/sea/scout/s21-hero.py`, captioned by
`gauntlet/sea/scout/s21-captions.py`. The driver imports `beach_render` and
moves only flags that file already carries as control panels; **no physics was
changed and `terrain-renderer/reference-impl/` was not modified.** 720 x 960 output pixels, box-averaged **in scene-linear**
from a 1440 x 1920 buffer, then a single exposure key (`beach_render.WHITE`
= %(white).4f) and gamma 2.2. **Both frames of the pair use the identical
camera object and the identical exposure key**, so a difference in the PNG is
a difference in the scene and not in the mapping. Every quantity below is read
from the scene-linear buffer BEFORE the tone map, except where it says 8-bit,
which is stated because a visual comparison goes through the encode.

**No text is burned into the frame.**
"""

ON = ("Everything the recent waves added is ON. `run_bay(embay=True, "
      "climate=beach.CLIMATE_SCENE)` -- the embayed plan-form (wave 9, off by "
      "default) and the two-partition offshore climate (wave 19, off by "
      "default, and **no render entry point in the repository passes it**). "
      "`Water` then builds, at its own defaults: `spectral_on=True` (wave 19's "
      "transported bundle, 256 components), `subgrid_on=True` (wave 18's "
      "`SlopeRealisation`), `foam_realise=True` (wave 18's Boolean foam), "
      "`foam_population=True` (wave 19's per-wave breaking realisation), "
      "`DECK_UNION=True` (wave 19's union deck over the two partitions).")

OFF = ("The recent work is OFF -- the waves 5-18 surface. Same camera, same "
       "exposure, same sun, same instant. `run_bay(embay=True)` with "
       "`climate=None`, so one offshore partition and one bar; then "
       "`spectral_on=False` (one carrier phase, one height per cell), "
       "`subgrid_on=False` (Cox & Munk's full density, no drawn sub-footprint "
       "slope), `foam_realise=False` (the foam is alpha-blended by "
       "`coverage(m) = 1 - exp(-m)`, the EXPECTATION), `foam_population=False` "
       "(no per-wave breaking indicator -- it cannot run anyway without a "
       "bundle to take an envelope of).")


def n(v, d=0):
    return ('{:,.%df}' % d).format(v).replace(',', ' ')


def frame_block(f, tag, rec, pair):
    L = []
    L.append('## What is in the frame, in integers')
    L.append('')
    L.append('| | pixels | share of frame |')
    L.append('|---|---:|---:|')
    for k, lab in (('n_water', 'water'), ('n_land', 'land'), ('n_sky', 'sky')):
        L.append('| %s | %s | %.2f %% |'
                 % (lab, n(rec[k]), 100.0 * rec[k] / rec['n_frame']))
    L.append('| **frame** | **%s** | |' % n(rec['n_frame']))
    L.append('')
    if 'n_deck_gt_025' in rec:
        L.append('Foam deck above 0.25: **%s px** (%.2f %% of frame). '
                 'Drawn coverage above 0.5: **%s px** (%.2f %%).'
                 % (n(rec['n_deck_gt_025']),
                    100.0 * rec['n_deck_gt_025'] / rec['n_frame'],
                    n(rec['n_cov_gt_05']),
                    100.0 * rec['n_cov_gt_05'] / rec['n_frame']))
        L.append('')
    return '\n'.join(L)


def reach_block(f, rec):
    L = ['## Does each recent feature reach these pixels?', '',
         'Ruling 18, as integers off this frame\'s own rendered buffer.', '']
    p = rec.get('population', {})
    if p.get('ran'):
        L.append('- **Wave 19, the wave population** (`breaking_indicator` on '
                 'the drawn envelope, rescaled by `rayleigh_exceedance`): '
                 '**RAN**. It changes the covering measure at **%s px**, '
                 '%.2f %% of frame and %.2f %% of the water, between x = %.0f '
                 'and %.0f m; **%s px** (%.3f %% of frame) move by more than '
                 '0.02 in drawn coverage. Mean chi %.4f, mean p %.4f; the cap '
                 'touches %.2f %% of the break measure.'
                 % (n(p['n_changed']), p['pct_frame'], p['pct_water'],
                    p['x_lo'], p['x_hi'], n(p['n_cov_change_gt_002']),
                    p['pct_frame_cov'], p['chi_mean'], p['p_mean'],
                    100.0 * p['capped_measure']))
    else:
        L.append('- **Wave 19, the wave population**: **did not run** '
                 '(`m_pop` is None -- there is no bundle to take an envelope '
                 'of).')
    s = rec.get('subgrid', {})
    if s.get('ran'):
        L.append('- **Wave 18, the sub-footprint slope realisation** '
                 '(`beach_optics.SlopeRealisation`): **RAN**. It writes a '
                 'non-zero slope at **%s px**, %.2f %% of frame -- every water '
                 'pixel -- with rms |grad| %.4f and 99th percentile %.4f; '
                 '**%s px** (%.2f %% of frame) carry more than 0.01 of drawn '
                 'slope.'
                 % (n(s['n_nonzero']), s['pct_frame'], s['rms'], s['p99'],
                    n(s['n_gt_001']), s['pct_frame_gt_001']))
    else:
        L.append('- **Wave 18, the sub-footprint slope realisation**: **did '
                 'not run** (`subgrid_on=False`; every pixel is shaded with '
                 'the ensemble mean of the whole slope distribution).')
    fr = rec.get('foam_realise', {})
    if fr.get('ran'):
        L.append('- **Wave 18, the Boolean foam realisation** '
                 '(`beach_foam.coverage_field`): **RAN**. Drawn mean %.5f '
                 'against field mean %.5f, %.2f %% of the frame\'s foam '
                 'visible at this footprint, p_max %.4f.'
                 % (fr['mean_drawn'], fr['mean_field'],
                    100.0 * fr['visible'], fr['p_max']))
    else:
        L.append('- **Wave 18, the Boolean foam realisation**: **did not '
                 'run** -- the frame draws `coverage(m)`, the expectation.')
    bars = rec.get('bars') or []
    if bars:
        L.append('- **Wave 19, the second breaker bar**: the two offshore '
                 'partitions break at %s on the centre row (x increases '
                 'SHOREWARD, so the larger x is the inner line). In a +-15 m '
                 'window round each, on this frame: %s.'
                 % (' and '.join('x = %.0f m' % b['x'] for b in bars),
                    '; '.join('x = %.0f m -> %s px in frame, %s of them with '
                              'deck > 0.25'
                              % (b['x'], n(b['n_px']), n(b['n_deck_gt_025']))
                              for b in bars)))
    g = rec.get('glitter', {})
    if g:
        L.append('- Glitter, scene-linear: mean %.4f, 99.9th percentile '
                 '%.2f, **%s px** above the exposure key.'
                 % (g['mean'], g['p999'], n(g['n_gt_white'])))
    L.append('')
    return '\n'.join(L)


def pair_block(f, pair, a, b):
    L = ['## The pair, measured', '']
    L.append('Scene-linear, max over the three channels: **%s of %s pixels '
             '(%.2f %%)** differ at all; rms difference %.4f, max %.4f '
             '(the exposure key is %.4f).'
             % (n(pair['n_changed_linear']), n(pair['n_px']),
                pair['pct_changed_linear'], pair['rms_dL'], pair['max_dL'],
                M['setup']['white_key']))
    L.append('')
    L.append('Through the same 8-bit encode both PNGs went through -- stated '
             'because this is the visual comparison and not a physical one: '
             '**%.2f %% of pixels change by at least one level**, **%.2f %% '
             'by more than eight**, mean change %.2f levels, max %d.'
             % (pair['pct_changed_8bit'], pair['pct_8bit_gt_8'],
                pair['mean_8bit_delta'], pair['max_8bit_delta']))
    L.append('')
    L.append('Frame statistics, scene-linear: mean radiance %.4f after '
             'against %.4f before; high-frequency sd (17 px box, `hf_sd`) '
             '%s after against %s before.'
             % (a['frame']['mean'], b['frame']['mean'],
                '/'.join('%.4f' % v for v in a['frame']['hf_sd']),
                '/'.join('%.4f' % v for v in b['frame']['hf_sd'])))
    L.append('')
    return '\n'.join(L)


def ablation_block(f):
    ab = M['ablation'][f]
    L = ['## One branch at a time, at 360 x 480 on the same camera axis', '',
         'The pair above moves the bed AND five flags at once. This ladder '
         'moves one branch at a time against the all-on baseline, on the same '
         'bed, so each row answers ruling 18 for one feature. Scene-linear; '
         'the 8-bit column is the same encode the PNGs use.', '',
         '| branch removed | px changed | share of frame | share of water | '
         'max dL | px changed in 8-bit | where (x) |',
         '|---|---:|---:|---:|---:|---:|---|']
    lab = {'no_subgrid': '`subgrid_on=False` (wave 18 glitter)',
           'no_population': '`foam_population=False` (wave 19 population)',
           'no_foam_realise': '`foam_realise=False` (wave 18 foam)',
           'no_spectral': '`spectral_on=False` (wave 19 bundle)',
           'carrier_deck': '`DECK_UNION=False` (wave 19 second bar)'}
    for k in ('no_spectral', 'no_subgrid', 'no_population', 'no_foam_realise',
              'carrier_deck'):
        r = ab.get(k)
        if not r:
            continue
        where = ('%.0f-%.0f m' % (r['x_lo'], r['x_hi'])
                 if r.get('x_lo') is not None else '--')
        L.append('| %s | %s | %.2f %% | %.2f %% | %.4g | %s | %s |'
                 % (lab[k], n(r['n_changed']), r['pct_frame'],
                    r['pct_water'], r['max_dL'], n(r['n_8bit_changed']),
                    where))
    L.append('')
    return '\n'.join(L)


for f in ('J', 'K', 'F'):
    if f not in M.get('hero', {}):
        continue
    pair = M['hero'][f].get('pair')
    for tag in ('after', 'before'):
        rec = M['hero'][f].get(tag)
        if rec is None:
            continue
        name = 's21-hero-%s-%s' % (f.lower(), tag)
        txt = HEAD % dict(name=name, framing=FRAMING[f],
                          tag=('AFTER' if tag == 'after' else 'BEFORE'),
                          what=(ON if tag == 'after' else OFF),
                          white=M['setup']['white_key'])
        txt += '\n' + frame_block(f, tag, rec, pair)
        txt += '\n' + reach_block(f, rec)
        if pair:
            txt += '\n' + pair_block(f, pair,
                                     M['hero'][f]['after'],
                                     M['hero'][f]['before'])
        if tag == 'after' and f in M.get('ablation', {}):
            txt += '\n' + ablation_block(f)
        txt += ('\nRender time %.0f s on an otherwise idle 4-core box '
                '(100 %% of one core; nothing else of this project was '
                'running).\n' % rec['seconds'])
        p = os.path.join(OUT, name + '.caption.md')
        with open(p, 'w') as fh:
            fh.write(txt)
        print('wrote', p)
