"""Write the one-page ruling-18 answer for the s21 round, from the same JSON
the captions are written from. Integers only, off rendered buffers,
scene-linear, before the tone map."""
import json, os

OUT = '/home/user/skills/.claude/worktrees/agent-a1cc4b7b2b35ef515/gauntlet/sea/evidence'
M = json.load(open(os.path.join(OUT, 's21-hero-measurements.json')))


def n(v):
    return '{:,.0f}'.format(v).replace(',', ' ')


LAB = [('no_spectral', '`spectral_on`', 'wave 19 -- the transported bundle: '
        'the first-order surface becomes a 256-component realisation instead '
        'of one carrier phase'),
       ('no_subgrid', '`subgrid_on`', 'wave 18 -- `SlopeRealisation`: the '
        'sub-footprint wind sea is DRAWN and subtracted from the Cox & Munk '
        'density instead of left in it'),
       ('no_foam_realise', '`foam_realise`', 'wave 18 -- `coverage_field`: '
        'the foam is a Boolean realisation instead of its own expectation'),
       ('no_population', '`foam_population`', 'wave 19 -- '
        '`breaking_indicator` on the drawn envelope, rescaled by '
        '`rayleigh_exceedance`: WHICH waves broke, not E[breaking]'),
       ('carrier_deck', '`DECK_UNION`', 'wave 19 -- the foam deck is the '
        'union over the two offshore partitions instead of the carrier\'s '
        'alone; this is the second breaker bar')]

FR = {'J': 'bar frame J, the embayment overview',
      'K': 'bar frame K, open water and the glitter path',
      'F': '`main()`\'s frame F, the backlit face over open water'}

L = []
L.append('# s21-hero-reach — does the recent physics reach the pixels?')
L.append('')
L.append('**Ruling 18, answered in integers off rendered buffers.** Every '
         'number here is scene-linear and taken BEFORE the tone map. Each row '
         'is ONE branch switched off against the all-on baseline, on the SAME '
         'bed, from the SAME camera axis, at 360 x 480 — so the row measures '
         'the branch and nothing else. Produced by '
         '`gauntlet/sea/scout/s21-hero.py`; no physics was changed and '
         '`terrain-renderer/reference-impl/` was not modified.')
L.append('')
L.append('The three framings: **J** and **K** are the bar\'s own '
         '(`beach_camera.J_CONTENT` / `K_CONTENT`, built by '
         '`beach_render.hero_cameras`). **F** is `beach_render.main()`\'s '
         'backlit-face frame, included as a CONTROL rather than as a hero: it '
         'looks seaward over open water, contains neither partition '
         'breakpoint and carries almost no foam, so a feature that lives in '
         'the surf zone must read ~0 there. Standing ruling 14 — a near-zero '
         'measurement is worthless until zero has been shown to be reachable '
         '— and `DECK_UNION` reaches it: **3 pixels**.')
L.append('')
L.append('## The ladder')
L.append('')
L.append('| branch | frame | px changed | share of frame | share of water | '
         'max ΔL | px changed in 8-bit |')
L.append('|---|---|---:|---:|---:|---:|---:|')
for key, sym, _ in LAB:
    for f in ('J', 'K', 'F'):
        r = M['ablation'].get(f, {}).get(key)
        if not r:
            continue
        L.append('| %s | %s | %s | %.2f %% | %.2f %% | %.4g | %s |'
                 % (sym, f, n(r['n_changed']), r['pct_frame'],
                    r['pct_water'], r['max_dL'], n(r['n_8bit_changed'])))
L.append('')
L.append('## What each branch is')
L.append('')
for key, sym, what in LAB:
    L.append('- **%s** — %s' % (sym, what))
L.append('')
L.append('## The verdict, feature by feature')
L.append('')
L.append('**All five reach pixels in both bar framings.** The smallest is the '
         'second breaker bar, and it is the only one whose reach depends on '
         'the framing: **8.29 %** of frame K, **4.51 %** of frame J, '
         '**0.00 %** of frame F. That ordering is the bed\'s and not the '
         'renderer\'s — the two partitions break at x = 598 m and x = 676 m '
         'on the centre row, frame K\'s row reaches x = 704 m and contains '
         'both, frame J\'s row reaches only x = 626 m and contains the outer '
         'line alone, and frame F looks the other way and reaches neither.')
L.append('')
L.append('**But the argument that activates it is passed by nothing that '
         'draws a picture.** `grep -rn "run_bay(" *.py` finds one caller in '
         'the whole repository that passes `climate=`: '
         '`validate_beach.py:12254`, inside the suite. Not '
         '`beach_render.main`, not `main_wave8/9/10/12`, not any of the seven '
         '`*_evidence.py` drivers. The union deck therefore had never reached '
         'a rendered frame before this round — which is ruling 18\'s exact '
         'shape with the guard, rather than the module, as the sole caller.')
L.append('')
L.append('**And `beach_render.py` still does not import `beach_diffract`.** '
         'Ruling 18\'s third case is unchanged at wave 20: zero pixels of any '
         'of these three frames carry a diffracted edge.')
L.append('')
L.append('## Per-frame reach, off the 720 x 960 hero buffers')
L.append('')
L.append('| | frame J | frame K |')
L.append('|---|---:|---:|')
hj, hk = M['hero']['J']['after'], M['hero']['K']['after']
rows = [('water pixels', lambda r: n(r['n_water'])),
        ('wave population changes the covering measure at',
         lambda r: '%s px (%.2f %% of water)'
         % (n(r['population']['n_changed']), r['population']['pct_water'])),
        ('...of which move drawn coverage by > 0.02',
         lambda r: n(r['population']['n_cov_change_gt_002'])),
        ('`SlopeRealisation` writes a non-zero slope at',
         lambda r: '%s px (%.2f %% of frame)'
         % (n(r['subgrid']['n_nonzero']), r['subgrid']['pct_frame'])),
        ('...rms of the drawn slope magnitude', lambda r: '%.4f' % r['subgrid']['rms']),
        ('`coverage_field` foam visible at this footprint',
         lambda r: '%.2f %%' % (100.0 * r['foam_realise']['visible'])),
        ('foam deck > 0.25', lambda r: n(r['n_deck_gt_025'])),
        ('8-bit pixels differing from the BEFORE frame',
         lambda r: None)]
for lab, fn in rows[:-1]:
    L.append('| %s | %s | %s |' % (lab, fn(hj), fn(hk)))
pj, pk = M['hero']['J']['pair'], M['hero']['K']['pair']
L.append('| pixels differing from the BEFORE frame, scene-linear | %s (%.2f %%) '
         '| %s (%.2f %%) |'
         % (n(pj['n_changed_linear']), pj['pct_changed_linear'],
            n(pk['n_changed_linear']), pk['pct_changed_linear']))
L.append('| ...by more than 8 levels through the shared 8-bit encode | %.2f %% '
         '| %.2f %% |' % (pj['pct_8bit_gt_8'], pk['pct_8bit_gt_8']))
L.append('| high-frequency sd, after (17 px box, scene-linear) | %s | %s |'
         % ('/'.join('%.2f' % v for v in hj['frame']['hf_sd']),
            '/'.join('%.2f' % v for v in hk['frame']['hf_sd'])))
L.append('| high-frequency sd, before | %s | %s |'
         % ('/'.join('%.2f' % v for v in M['hero']['J']['before']['frame']['hf_sd']),
            '/'.join('%.2f' % v for v in M['hero']['K']['before']['frame']['hf_sd'])))
L.append('')
L.append('Render times, on an otherwise idle 4-core box with nothing else of '
         'this project running (100 %% of one core throughout — ruling 13 '
         'stays withdrawn): frame J after **%.0f s**, before **%.0f s**; '
         'frame K after **%.0f s**, before **%.0f s**. The ladder cost '
         '%.0f s for J, %.0f s for K and %.0f s for F.'
         % (hj['seconds'], M['hero']['J']['before']['seconds'],
            hk['seconds'], M['hero']['K']['before']['seconds'],
            sum(v['seconds'] for v in M['ablation']['J'].values()),
            sum(v['seconds'] for v in M['ablation']['K'].values()),
            sum(v['seconds'] for v in M['ablation']['F'].values())))
L.append('')

with open(os.path.join(OUT, 's21-hero-reach.md'), 'w') as f:
    f.write('\n'.join(L) + '\n')
print('wrote s21-hero-reach.md')
