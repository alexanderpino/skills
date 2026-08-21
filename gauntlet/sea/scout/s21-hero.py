"""s21: the hero pair. Renders bar frames J and K (and a surf-zone frame F)
with the recent physics ON and with it OFF, from ONE camera per framing and
ONE exposure key, and measures whether each recent feature reaches pixels.

Nothing here changes physics. Every flag it moves is a control panel the
renderer already carries (`spectral_on`, `subgrid_on`, `foam_realise`,
`foam_population`, `DECK_UNION`) plus `run_bay`'s own `climate` argument.
"""
import sys, os, time, math, json
IMPL = '/home/user/skills/.claude/worktrees/agent-a1cc4b7b2b35ef515/terrain-renderer/reference-impl'
OUT = '/home/user/skills/.claude/worktrees/agent-a1cc4b7b2b35ef515/gauntlet/sea/evidence'
sys.path.insert(0, IMPL)
import numpy as np
import beach as B
import beach_render as RND
import beach_foam as FM
import beach_optics as BO
from beach_render import Camera

T0 = time.time()
M = {}          # everything measured, dumped to JSON as it goes
_MISSING = object()


def log(*a):
    print('[%7.1fs] ' % (time.time() - T0) + ' '.join(str(x) for x in a),
          flush=True)


def dump():
    with open(os.path.join(OUT, 's21-hero-measurements%s.json' % ('-smoke' if os.environ.get('S21_SMOKE') else '')), 'w') as f:
        json.dump(M, f, indent=1, sort_keys=True, default=float)


def _resume():
    """RESUMABLE, because one frame costs 45 minutes and the container is not
    promised to survive that. Nothing is recomputed that is already on disk;
    nothing on disk is ever a DIFFERENT render, because the bed, the camera
    and every flag are the same on every pass."""
    p = os.path.join(OUT, 's21-hero-measurements.json')
    if os.path.exists(p) and not os.environ.get('S21_SMOKE'):
        try:
            M.update(json.load(open(p)))
            return True
        except Exception:
            pass
    return False


W_OUT, H_OUT = RND.HERO_WH          # 720 x 960 output pixels
SS = RND.HERO_SS                    # supersampled 2x, box-averaged in linear
W_AB, H_AB = 360, 480               # the ablation ladder's own pitch
SMOKE = os.environ.get('S21_SMOKE')
RESUMED = _resume()
LADDER_FRAMES = tuple(x for x in os.environ.get('S21_LADDER', 'J,K,F').split(',') if x)
HERO_FRAMES = tuple(x for x in os.environ.get('S21_HERO', 'J,K,F').split(',') if x)
if SMOKE:                           # a shape-and-code-path rehearsal only
    W_OUT, H_OUT, SS, W_AB, H_AB = 60, 80, 2, 48, 64

# --------------------------------------------------------------- the two beds
RND._set_runup()
log('runup: xi = %.3f, R = %.2f m' % (RND._XI, RND.RUNUP))
log('CLIMATE_SCENE =', B.CLIMATE_SCENE)

SCRATCH = '/tmp/claude-0/-home-user-skills/35a89dec-7c98-5eae-adfa-45a8f04b4bd9/scratchpad'


def cached_bay(tag, **kw):
    """A DISK CACHE ON THE BED AND NOTHING ELSE. `run_bay` is deterministic and
    costs 70-145 s; caching it means a crash in the render loop does not pay
    for the morphodynamic loop twice. Nothing about the bed changes."""
    import pickle
    p = os.path.join(SCRATCH, 'bay_%s.pkl' % tag)
    if os.path.exists(p):
        t = time.time()
        with open(p, 'rb') as f:
            bay = pickle.load(f)
        log('bay %-6s loaded from cache in %.1f s' % (tag, time.time() - t))
        return bay
    t = time.time()
    bay = B.run_bay(**kw)
    log('bay %-6s (%s) built in %.1f s'
        % (tag, ', '.join('%s=%s' % (k, 'CLIMATE_SCENE' if k == 'climate' else v)
                          for k, v in kw.items()), time.time() - t))
    with open(p, 'wb') as f:
        pickle.dump(bay, f, protocol=4)
    return bay


bay_new = cached_bay('after', embay=True, climate=B.CLIMATE_SCENE)
bay_old = cached_bay('before', embay=True)

t = time.time(); w_new = RND.Water(bay_new)
log('Water AFTER  built in %.1f s (spectral_on=%s, subgrid_on=%s, bundle=%s)'
    % (time.time() - t, w_new.spectral_on, w_new.subgrid_on,
       None if w_new.bundle is None else w_new.bundle['a'].shape))
RND.SPECTRAL_ON = False
t = time.time(); w_old = RND.Water(bay_old)
RND.SPECTRAL_ON = True
w_old.spectral_on = False
w_old.bundle = None
w_old.subgrid_on = False
w_old.foam_realise = False
w_old.foam_population = False
log('Water BEFORE built in %.1f s' % (time.time() - t))

M['setup'] = dict(
    climate=[list(c) for c in B.CLIMATE_SCENE],
    hero_wh=[W_OUT, H_OUT], hero_ss=SS, ablation_wh=[W_AB, H_AB],
    white_key=float(RND.WHITE), gamma=2.2,
    deck_max_after=float(w_new.deck.max()), deck_max_before=float(w_old.deck.max()),
    mss_swell=w_new.mss_swell,
    bundle_MB=float(w_new.bundle['nbytes']) / 1e6,
)
dump()

# --------------------------------------------------- where the two bars break
jc = bay_new['h'].shape[0] // 2
xb = []
for trp in bay_new['tr_parts']:
    bp = B.breakpoints(B.row_slice(trp, jc))
    if bp:
        xb.append(float(bp[0]['x']))
xb = sorted(xb)
bp1 = B.breakpoints(B.row_slice(bay_old['tr'], jc))
M['breakpoints'] = dict(after_partitions=xb,
                        before_carrier=[float(p['x']) for p in bp1[:3]])
log('partition breakpoints (centre row): %s m; single-carrier bed: %s m'
    % (['%.0f' % x for x in xb], ['%.0f' % p['x'] for p in bp1[:3]]))
dump()

# ------------------------------------------------------------- three cameras
def cams(Wp, Hp):
    c = RND.hero_cameras(w_new, Wp, Hp, out=lambda *a, **k: None)
    camJ, camK = c[3], c[5]
    # F: the surf-zone frame, the eye at 8 m 55 m shoreward-alongshore of the
    # largest wave in the bed, 26 deg, looking down-sun-ish but with the sun
    # out of frame. This is `main()`'s own frame F construction, unchanged.
    ib = int(np.argmax(np.max(w_new.H, axis=0)))
    jb = int(np.argmax(w_new.H[:, ib]))
    x_f = float(w_new.x[ib]) + 55.0
    y_f = float(w_new.y[jb]) + 55.0
    camF = Camera((x_f, y_f, 8.0), (x_f - 75.0, y_f - 75.0, 0.0), 26.0, Wp, Hp)
    return dict(J=camJ, K=camK, F=camF)


CAMS = cams(W_OUT * SS, H_OUT * SS)
CAMS_AB = cams(W_AB, H_AB)
for k, c in CAMS.items():
    log('cam %s: eye %s  fwd %s  fov_v %.2f deg'
        % (k, np.round(c.pos, 1), np.round(c.f, 4), 2.0 * math.degrees(math.atan(c.tan))))
M['cameras'] = {k: dict(pos=[float(v) for v in c.pos],
                        fwd=[float(v) for v in c.f], fov_v=float(2.0 * math.degrees(math.atan(c.tan))))
                for k, c in CAMS.items()}
dump()


# ------------------------------------------------------ per-frame reach maths
def reach(ex, w):
    """Integers, off the rendered buffer, scene-linear, before the tone map."""
    n_frame = int(ex['sky_mask'].size)
    r = dict(n_frame=n_frame,
             n_water=int(ex.get('water_mask', np.zeros(1, bool)).sum()),
             n_land=int(ex.get('land_mask', np.zeros(1, bool)).sum()),
             n_sky=int(ex['sky_mask'].sum()))
    if 'water' not in ex:
        return r
    sh = ex['water']
    x = ex['water_P'][..., 0].reshape(-1)
    y = ex['water_P'][..., 1].reshape(-1)

    # --- the FOAM DECK, and how much of it the frame carries
    deck = np.asarray(sh['deck'], float).reshape(-1)
    r['n_deck_gt_025'] = int((deck > 0.25).sum())
    r['n_deck_gt_001'] = int((deck > 0.01).sum())

    # --- WAVE 19, THE WAVE POPULATION. `m_pop` is None when the branch did not
    # run. When it did, the pre-population covering measure is recomputed from
    # the SAME stored fields the shader used, so the difference is exact.
    if sh.get('m_pop') is None:
        r['population'] = dict(ran=False)
    else:
        mp = sh['m_pop']
        _, m_pre = FM.surface_foam(np.asarray(sh['deck'], float), w.T_wave,
                                   np.asarray(sh['age'], float), BO.U10,
                                   w.tau_foam)
        m_pre = m_pre.reshape(-1)
        m_post = np.asarray(sh['m_cov'], float).reshape(-1)
        d = np.abs(m_post - m_pre)
        hit = d > 1e-6
        cov_pre = FM.coverage(m_pre)
        cov_post = FM.coverage(m_post)
        dcov = np.abs(cov_post - cov_pre)
        big = dcov > 0.02
        r['population'] = dict(
            ran=True, n_changed=int(hit.sum()),
            pct_frame=100.0 * hit.sum() / n_frame,
            pct_water=100.0 * hit.sum() / max(r['n_water'], 1),
            n_cov_change_gt_002=int(big.sum()),
            pct_frame_cov=100.0 * big.sum() / n_frame,
            max_dm=float(d.max()), max_dcov=float(dcov.max()),
            x_lo=float(x[hit].min()) if hit.any() else None,
            x_hi=float(x[hit].max()) if hit.any() else None,
            chi_mean=float(mp['chi_mean']), p_mean=float(mp['p_mean']),
            capped_measure=float(mp['capped_measure']),
            capped_pixels=float(mp['capped_pixels']),
            chi_zero_px=int((np.asarray(mp['chi'], float).reshape(-1) <= 0).sum()),
            chi_one_px=int((np.asarray(mp['chi'], float).reshape(-1) >= 1).sum()))

    # --- WAVE 18, THE SUB-FOOTPRINT SLOPE REALISATION
    if sh.get('sub') is None:
        r['subgrid'] = dict(ran=False)
    else:
        zx = np.asarray(sh['sub']['zx'], float).reshape(-1)
        zy = np.asarray(sh['sub']['zy'], float).reshape(-1)
        mag = np.hypot(zx, zy)
        r['subgrid'] = dict(
            ran=True, n_nonzero=int((mag > 0).sum()),
            pct_frame=100.0 * (mag > 0).sum() / n_frame,
            n_gt_001=int((mag > 0.01).sum()),
            pct_frame_gt_001=100.0 * (mag > 0.01).sum() / n_frame,
            rms=float(np.sqrt((mag ** 2).mean())),
            p99=float(np.percentile(mag, 99)),
            x_lo=float(x[mag > 0].min()) if (mag > 0).any() else None,
            x_hi=float(x[mag > 0].max()) if (mag > 0).any() else None)

    # --- WAVE 18, THE FOAM BOOLEAN REALISATION
    fs = sh.get('foam_stats') or {}
    r['foam_realise'] = dict(
        ran=bool(np.isfinite(fs.get('mean_drawn', float('nan')))),
        visible=float(fs.get('visible', float('nan'))),
        p_max=float(fs.get('p_max', float('nan'))),
        mean_drawn=float(fs.get('mean_drawn', float('nan'))),
        mean_field=float(fs.get('mean_field', float('nan'))))
    cov = np.asarray(sh['cov'], float).reshape(-1)
    r['n_cov_gt_05'] = int((cov > 0.5).sum())
    r['n_cov_gt_001'] = int((cov > 0.01).sum())
    r['cov_mean'] = float(cov.mean())

    # --- WAVE 19, THE TWO BARS: is there white at BOTH partitions' breakpoints?
    r['bars'] = []
    for xbk in xb:
        m = (np.abs(x - xbk) <= 15.0)
        r['bars'].append(dict(x=float(xbk), n_px=int(m.sum()),
                             n_deck_gt_025=int((m & (deck > 0.25)).sum()),
                             n_cov_gt_05=int((m & (cov > 0.5)).sum())))

    # --- the glitter, scene-linear
    lg = np.asarray(sh['L_glit'], float).reshape(-1, 3)[..., 1]
    r['glitter'] = dict(mean=float(lg.mean()), p999=float(np.percentile(lg, 99.9)),
                        n_gt_white=int((lg > RND.WHITE).sum()))
    return r


def frame_stats(L):
    a = np.asarray(L, float)
    return dict(mean=float(a.mean()), p50=float(np.median(a)),
                p999=float(np.percentile(a, 99.9)),
                clipped_px=int((a / RND.WHITE >= 1.0).all(-1).sum()),
                hf_sd=[float(v) for v in RND.hf_sd(a)])


def eight_bit(L):
    img = np.clip(np.asarray(L, float) / RND.WHITE, 0.0, 1.0) ** (1.0 / 2.2)
    return (img * 255.0 + 0.5).astype(np.uint8)


# =============================================== stage 1: the ablation ladder
# Cheap, at 360 x 480, because ruling 18 outranks the pictures and this is the
# question it asks: does each branch change the buffer?
log('--- ablation ladder at %d x %d ---' % (W_AB, H_AB))
carrier_deck = FM.deck_source(bay_new['tr'])
union_deck = w_new.deck.copy()
M.setdefault('ablation', {})
WANT = ('all', 'no_subgrid', 'no_population', 'no_foam_realise',
        'no_spectral', 'carrier_deck')
for fname in LADDER_FRAMES:
    cam = CAMS_AB[fname]
    base = None
    M['ablation'].setdefault(fname, {})
    if all(k in M['ablation'][fname] for k in WANT):
        log('  %s ladder already complete, skipped' % fname)
        continue
    variants = [
        ('all', {}),
        ('no_subgrid', dict(subgrid_on=False)),
        ('no_population', dict(foam_population=False)),
        ('no_foam_realise', dict(foam_realise=False)),
        ('no_spectral', dict(spectral_on=False)),
        ('carrier_deck', 'deck'),
    ]
    for name, flags in variants:
        saved = {}
        if flags == 'deck':
            w_new.deck = carrier_deck
        else:
            for k, v in flags.items():
                saved[k] = getattr(w_new, k, _MISSING)
                setattr(w_new, k, v)
        t = time.time()
        L, ex = RND.render(cam, w_new)
        dt = time.time() - t
        if flags == 'deck':
            w_new.deck = union_deck
        else:
            for k, v in saved.items():
                if v is _MISSING:
                    delattr(w_new, k)
                else:
                    setattr(w_new, k, v)
        rec = dict(seconds=dt)
        if name == 'all':
            base = L.copy()
            base_ex = ex
            rec.update(reach(ex, w_new))
        else:
            d = np.abs(L - base).max(-1)
            hit = d > 1e-9
            xw = base_ex['water_P'][..., 0].reshape(-1)
            mw = base_ex['water_mask']
            hw = hit[mw]
            rec.update(n_changed=int(hit.sum()),
                       pct_frame=100.0 * hit.sum() / hit.size,
                       n_changed_water=int(hw.sum()),
                       pct_water=100.0 * hw.sum() / max(int(mw.sum()), 1),
                       max_dL=float(d.max()),
                       mean_dL_over_changed=float(d[hit].mean()) if hit.any() else 0.0,
                       rel_max=float(d.max() / RND.WHITE),
                       x_lo=float(xw[hw].min()) if hw.any() else None,
                       x_hi=float(xw[hw].max()) if hw.any() else None,
                       n_8bit_changed=int((np.abs(eight_bit(L).astype(int)
                                                  - eight_bit(base).astype(int))
                                           .max(-1) > 0).sum()))
        M['ablation'][fname][name] = rec
        log('  %s / %-16s %6.1f s  %s' % (fname, name, dt,
            ('%d px changed (%.2f%% of frame), max dL %.4g'
             % (rec.get('n_changed', -1), rec.get('pct_frame', 0.0),
                rec.get('max_dL', 0.0))) if name != 'all' else 'baseline'))
        dump()

# ======================================================= stage 2: the heroes
log('--- hero frames at %d x %d output, %dx supersampled ---' % (W_OUT, H_OUT, SS))
M.setdefault('hero', {})
for fname in HERO_FRAMES:
    cam = CAMS[fname]
    for tag, w in (('after', w_new), ('before', w_old)):
        npy = os.path.join(SCRATCH, 's21_%s_%s.npy' % (fname, tag))
        done = M.get('hero', {}).get(fname, {}).get(tag)
        if done is not None and os.path.exists(npy):
            log('  %s %-6s already on disk (%.0f s when it was rendered)'
                % (fname, tag, done.get('seconds', 0.0)))
            continue
        t = time.time()
        L, ex = RND.render(cam, w)
        dt = time.time() - t
        Ld = RND.downsample(L, SS)
        path = os.path.join(OUT if not SMOKE else SCRATCH, 's21-hero-%s-%s.png' % (fname.lower(), tag))
        RND._save(Ld, path)
        rec = dict(seconds=dt, path=os.path.basename(path))
        rec.update(reach(ex, w))
        rec['frame'] = frame_stats(Ld)
        M['hero'].setdefault(fname, {})[tag] = rec
        np.save('/tmp/claude-0/-home-user-skills/35a89dec-7c98-5eae-adfa-45a8f04b4bd9/scratchpad/s21_%s_%s.npy' % (fname, tag), Ld.astype(np.float32))
        log('  %s %-6s %7.1f s -> %s' % (fname, tag, dt, os.path.basename(path)))
        dump()
    # the pair, measured in scene-linear and then, separately, through the
    # SAME 8-bit encode both PNGs went through
    A = np.load('/tmp/claude-0/-home-user-skills/35a89dec-7c98-5eae-adfa-45a8f04b4bd9/scratchpad/s21_%s_after.npy' % fname).astype(float)
    Bf = np.load('/tmp/claude-0/-home-user-skills/35a89dec-7c98-5eae-adfa-45a8f04b4bd9/scratchpad/s21_%s_before.npy' % fname).astype(float)
    d = np.abs(A - Bf).max(-1)
    q = np.abs(eight_bit(A).astype(int) - eight_bit(Bf).astype(int)).max(-1)
    M['hero'][fname]['pair'] = dict(
        n_px=int(d.size),
        n_changed_linear=int((d > 1e-9).sum()),
        pct_changed_linear=100.0 * (d > 1e-9).sum() / d.size,
        rms_dL=float(np.sqrt((d ** 2).mean())),
        max_dL=float(d.max()),
        n_changed_8bit=int((q > 0).sum()),
        pct_changed_8bit=100.0 * (q > 0).sum() / q.size,
        n_8bit_gt_8=int((q > 8).sum()),
        pct_8bit_gt_8=100.0 * (q > 8).sum() / q.size,
        mean_8bit_delta=float(q.mean()), max_8bit_delta=int(q.max()))
    log('  %s pair: %.2f%% of pixels differ in 8-bit, %.2f%% by more than 8 levels'
        % (fname, M['hero'][fname]['pair']['pct_changed_8bit'],
           M['hero'][fname]['pair']['pct_8bit_gt_8']))
    dump()

log('DONE in %.1f s' % (time.time() - T0))
