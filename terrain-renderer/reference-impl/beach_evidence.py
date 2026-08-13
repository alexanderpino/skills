"""The beach scene's visual evidence, into `gauntlet/sea/evidence/` as `s1-*`.

    python3 beach_evidence.py [outdir]

Standing ruling: every wave produces visual evidence, and the pool loop
under-delivered on it. These figures are diagnostics, not renders -- they are
here to be READ, not admired. Everything plotted is scene-linear SI computed by
`beach.py`; nothing is measured back off a PNG.

The minimum the wave was asked for is the first three: a plan-view depth field,
a cross-shore profile with the bar on it, and the wave-height transform across
it. The rest are the rows of the suite that are easier to believe as a picture.
"""
import math
import os
import sys

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)

import beach as B                                               # noqa: E402
import beach_plot as P                                          # noqa: E402
import optics as OPT                                            # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, '..', '..', 'gauntlet', 'sea', 'evidence')

SAND = (208, 190, 158)
SEA = (36, 92, 122)
BAR = (196, 84, 58)
WAVE = (24, 84, 168)
GREY = (110, 112, 118)
GREEN = (32, 128, 96)
PURPLE = (124, 72, 168)


def _ticks(lo, hi, n=6):
    step = (hi - lo) / n
    mag = 10.0 ** math.floor(math.log10(step))
    for m in (1, 2, 2.5, 5, 10):
        if mag * m >= step:
            step = mag * m
            break
    t0 = math.ceil(lo / step) * step
    return [t0 + i * step for i in range(int((hi - t0) / step) + 1)]


# ------------------------------------------------------------------ figure 1
def fig_profile(sc, sc_storm, path):
    x, h, hd = sc['x'], sc['h'], sc['h_dean']
    tr = sc['tr']
    cr = B.bar_crest(x, h, hd)
    th = B.trough(x, h, hd, cr['i'])
    b = B.breaker_state(tr)
    d_pred = b['H_b'] / B.GAMMA_B

    img = P.canvas(1180, 640)
    ax = P.Axes(img, (90, 60, 1130, 470), (0, 500), (-9, 1),
                title='The bar is a product: Dean ramp in, bar out',
                xlabel='cross-shore distance, m (shoreward ->)',
                ylabel='bed elevation, m (datum = still water)')
    ax.frame(_ticks(0, 500), _ticks(-9, 1))
    ax.fill_between(x, np.full_like(x, -9.0), h, (232, 224, 206))
    ax.line(x, np.zeros_like(x), (150, 170, 190), 1)
    ax.line(x, hd, GREY, 2, dash=(7, 6))
    ax.line(x, sc_storm['h'], PURPLE, 2)
    ax.line(x, h, SAND if False else (120, 92, 48), 3)
    ax.hline(-d_pred, BAR, 1, (5, 5))
    ax.marker(cr['x'], cr['h'], BAR, 5)
    ax.text(cr['x'] + 8, cr['h'] + 0.55,
            'crest  x=%.0f m  d=%.2f m' % (cr['x'], cr['d']), BAR)
    ax.text(6, -d_pred + 0.18, 'H_b/gamma = %.2f m  (chapter 12\'s prediction)'
            % d_pred, BAR)
    if th:
        ax.marker(th['x'], th['h'], GREEN, 4)
        ax.text(th['x'] + 8, th['h'] - 0.45,
                'trough  x=%.0f m  d=%.2f m' % (th['x'], th['d']), GREEN)
    P.legend(ax, [(GREY, 'initial bed: Dean ramp, h = -A x^(2/3), A = %.2f'
                   % B.DEAN_A),
                  ((120, 92, 48), 'after %d steps of the loop (%.0f h), H_0 = %.1f m'
                   % (B.N_STEPS, B.N_STEPS * B.DT_MORPH / 3600, B.H0_SWELL)),
                  (PURPLE, 'the same loop at H_0 = %.1f m (storm)' % B.H0_STORM),
                  (BAR, 'depth H_b/gamma')], 20, -6.2)
    P.caption(img, [
        'Nothing in the loop knows where a bar goes. The initial bed is one monotone curve with one parameter; the ridge is where the',
        'onshore skewness flux and the offshore undertow flux converge, which is the break point, which is an output of the transform.',
        'Measured crest depth %.3f m against H_b/gamma = %.3f m (ratio %.3f). Storm case: crest %.0f m further offshore, %.2f m deeper.'
        % (cr['d'], d_pred, cr['d'] / d_pred,
           cr['x'] - B.bar_crest(x, sc_storm['h'], hd)['x'],
           B.bar_crest(x, sc_storm['h'], hd)['d'] - cr['d'])])
    return P.save(img, path)


# ------------------------------------------------------------------ figure 2
def fig_transform(sc, path):
    x, h, tr = sc['x'], sc['h'], sc['tr']
    cr = B.bar_crest(x, h, sc['h_dean'])
    img = P.canvas(1180, 860)

    ax = P.Axes(img, (90, 60, 1130, 350), (200, 500), (0, 3.2),
                title='The wave-height transform across the bar it built',
                ylabel='H and gamma*d, m')
    ax.frame(_ticks(200, 500), _ticks(0, 3.2))
    for x0, x1 in B.break_lines(tr):
        ax.band(max(x0 - 1, 200), min(x1 + 1, 500), (250, 232, 226))
    ax.line(x, B.GAMMA_B * tr['d'], BAR, 2, dash=(6, 5))
    ax.line(x, B.GAMMA_STABLE * tr['d'], GREEN, 1, dash=(4, 4))
    ax.line(x, tr['H'], WAVE, 3)
    ax.vline(cr['x'], GREY, 1, (3, 4))
    P.legend(ax, [(WAVE, 'H(x), shoaled, refracted, broken'),
                  (BAR, 'gamma*d  (gamma = %.2f, the shared breaker index)'
                   % B.GAMMA_B),
                  (GREEN, 'Gamma*d  (Dally stable height, breaking stops here)')],
             210, 3.05)

    ax2 = P.Axes(img, (90, 450, 1130, 680), (200, 500), (0, 1.0),
                 title='H/d: crossed at the bar, un-crossed in the trough behind it',
                 xlabel='cross-shore distance, m (shoreward ->)',
                 ylabel='H / d')
    ax2.frame(_ticks(200, 500), [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax2.line(x, tr['H'] / np.maximum(tr['d'], 0.1), WAVE, 3)
    ax2.hline(B.GAMMA_B, BAR, 2, (6, 5))
    ax2.hline(B.GAMMA_STABLE, GREEN, 1, (4, 4))
    ax2.vline(cr['x'], GREY, 1, (3, 4))
    ax2.text(cr['x'] + 5, 0.93, 'bar crest', GREY)
    ons = B.break_lines(tr)
    for x0, _ in ons:
        ax2.marker(x0, B.GAMMA_B, BAR, 4)
    P.caption(img, [
        'H/d reaches gamma over the bar the loop built (onset at %s) and falls to %.3f behind it: the wave stops being at the breaking'
        % (', '.join('%.0f m' % o[0] for o in ons),
           float((tr['H'] / np.maximum(tr['d'], .1))[cr['i']:cr['i'] + 100].min())),
        'limit in the trough, which is section B\'s crossing. It does NOT fall below the Dally stable ratio %.2f, so the wave never fully'
        % B.GAMMA_STABLE,
        'reforms and the surf zone stays continuous instead of showing a second, separate breaking line. Recorded as a miss, not rounded',
        'up: it is the one criterion of section B this wave did not reach, and the suite carries it as an OPEN row. See README-beach.md.'])
    return P.save(img, path)


# ------------------------------------------------------------------ figure 3
def fig_flux(sc, path):
    x, h, tr = sc['x'], sc['h'], sc['tr']
    fl = B.sediment_flux(tr)
    cr = B.bar_crest(x, h, sc['h_dean'])
    b = B.breaker_state(tr)
    s = 1e6
    img = P.canvas(1180, 840)
    lim = float(np.percentile(np.abs(fl['q'][200:-4] * s), 99.5)) * 1.25

    ax = P.Axes(img, (95, 60, 1130, 400), (200, 500), (-lim, lim),
                title='The two fluxes, and where they converge',
                ylabel='sediment flux q, 1e-6 m2/s  (+ = shoreward)')
    ax.frame(_ticks(200, 500), _ticks(-lim, lim))
    ax.hline(0.0, (60, 60, 60), 1, (3, 4))
    ax.line(x, fl['q_on'] * s, GREEN, 2)
    ax.line(x, -fl['q_off'] * s, PURPLE, 2)
    ax.line(x, fl['q'] * s, (20, 20, 24), 3)
    ax.vline(cr['x'], BAR, 2, (5, 5))
    ax.vline(b['x'], WAVE, 1, (3, 4))
    P.legend(ax, [(GREEN, 'onshore: skewness, k_q Sk u_orb^3'),
                  (PURPLE, 'offshore: undertow, k_q lam u_orb^2 u_u'),
                  ((20, 20, 24), 'net q, including the slope term'),
                  (BAR, 'bar crest'), (WAVE, 'break onset')], 210, lim * 0.92)

    dq = np.gradient(fl['q'], tr['dx'])
    dh = -dq / (1.0 - B.POROSITY) * 3600.0 * 1000.0
    lim2 = float(np.percentile(np.abs(dh[200:-5]), 99.5)) * 1.3
    ax2 = P.Axes(img, (95, 500, 1130, 700), (200, 500), (-lim2, lim2),
                 title='Exner: flux convergence is the bar',
                 xlabel='cross-shore distance, m (shoreward ->)',
                 ylabel='dh/dt, mm/h')
    ax2.frame(_ticks(200, 500), _ticks(-lim2, lim2, 4))
    ax2.hline(0.0, (60, 60, 60), 1, (3, 4))
    ax2.line(x, dh, (20, 20, 24), 2)
    ax2.vline(cr['x'], BAR, 2, (5, 5))
    ax2.text(202, lim2 * 0.8, 'clipped at the 99.5th percentile: the peak rate '
             'at the crest is %.0f mm/h' % float(np.abs(dh[200:-5]).max()),
             GREY)
    P.caption(img, [
        'q > 0 seaward of the break: the shoaling wave is skewed, its crest stroke is short and sharp, and the third moment carries sand',
        'shoreward. q < 0 landward: the wave has broken, its skewness has gone into the bore front, and the undertow carries the stirred',
        'sand back out. The crossing is the break point and the convergence there is the bar. Both terms are computed; neither is placed.'])
    return P.save(img, path)


# ------------------------------------------------------------------ figure 4
def fig_plan(sc, path, ny=241, y_half=360.0):
    x, h, hd = sc['x'], sc['h'], sc['h_dean']
    y = np.linspace(-y_half, y_half, ny)
    h2, centres = B.bed_2d(x, y, h, hd)
    d2 = np.maximum(-h2, 0.0)

    # Depth shading through the SHARED optics module: a sand bed seen through a
    # column of clear water, two-way Beer-Lambert with the file's own
    # absorption triple. It is a diagnostic ramp that happens to be physical --
    # no Fresnel, no sky, no scattering, and no claim to be a render. The point
    # is that even the evidence figure imports the pool's water rather than
    # inventing a colormap.
    alb = np.array([0.62, 0.58, 0.48])
    rgb = (alb[None, None, :] * np.exp(-2.0 * OPT.ABS[None, None, :]
                                       * d2[:, :, None]))
    rgb = rgb + np.array([0.02, 0.06, 0.11])[None, None, :] * (d2[:, :, None] > 0)
    dry = d2 <= 0.0
    img_arr = np.clip(rgb, 0, 1) ** (1 / 2.2)
    img_arr[dry] = np.array([0.84, 0.78, 0.65])
    pix = (img_arr * 255).astype(np.uint8)

    # depth contours, drawn on the field itself
    for lev, col in ((1.0, (255, 255, 255)), (2.0, (255, 240, 210)),
                     (3.0, (200, 220, 235)), (5.0, (150, 180, 205))):
        mask = (np.abs(d2 - lev) < 0.06) & (~dry)
        pix[mask] = col

    img = P.canvas(1180, 640)
    ax = P.Axes(img, (90, 60, 1130, 480), (0, 500), (-y_half, y_half),
                title='Plan view: the computed bar, with rip channels stamped through it',
                xlabel='cross-shore distance, m (shoreward ->)',
                ylabel='alongshore, m')
    ax.image(pix[::-1])
    ax.frame(_ticks(0, 500), _ticks(-y_half, y_half, 6))
    cr = B.bar_crest(x, h, hd)
    for cy in centres:
        if -y_half + 20 < cy < y_half - 20:
            ax.text(cr['x'] + 14, cy, 'rip', (250, 246, 240), anchor='lm')
    P.caption(img, [
        'The CROSS-SHORE profile is computed -- it is the Exner equilibrium of figure 1, inserted unchanged at every alongshore station.',
        'The ALONGSHORE rhythm is stamped, exactly as chapter 12\'s ripSystem pseudocode stamps it, at %.0f m spacing with jitter'
        % 120.0,
        '(the chapter gives O(100 m), field values 50-500 m, and insists on quasi-rhythmic rather than periodic). A 2DH solve that grows',
        'the rhythm from an instability is out of scope by the chapter\'s own declaration, and this figure says which half is which.',
        'Contours at 1, 2, 3, 5 m. Depth shading is two-way Beer-Lambert through optics.ABS -- the pool\'s water, imported, not a colormap.'])
    return P.save(img, path)


# ------------------------------------------------------------------ figure 5
def fig_rays(sc, path, ny=321, y_half=480.0, y_view=240.0):
    x, h, hd = sc['x'], sc['h'], sc['h_dean']
    y = np.linspace(-y_half, y_half, ny)
    h2, centres = B.bed_2d(x, y, h, hd)
    img = P.canvas(1180, 680)
    ax = P.Axes(img, (90, 60, 1130, 500), (0, 500), (-y_view, y_view),
                title='Refraction over a curved contour: rays converge on the bar, spread over the rip',
                xlabel='cross-shore distance, m (shoreward ->)',
                ylabel='alongshore, m')
    d2 = np.maximum(-h2, 0.0)
    j0 = int(np.argmin(np.abs(y + y_view)))
    j1 = int(np.argmin(np.abs(y - y_view))) + 1
    shade = np.clip(1.0 - d2[j0:j1] / 8.5, 0, 1)
    pix = np.empty(shade.shape + (3,), np.uint8)
    for c in range(3):
        pix[..., c] = (np.array([224, 236, 246])[c] * (0.52 + 0.48 * shade)
                       ).astype(np.uint8)
    for lev in (1.5, 2.1, 2.6, 3.2, 4.5):
        pix[np.abs(d2[j0:j1] - lev) < 0.045] = (128, 155, 180)
    ax.image(pix[::-1])
    ax.frame(_ticks(0, 500), _ticks(-y_view, y_view, 6))

    # Rays are launched far enough down-drift that the ones crossing the frame
    # at the shoreward end entered outside it: at 20 deg a ray covers 180 m
    # alongshore over the domain, so launching only inside the window would
    # empty the shoreward half of the picture and look like the rays stopped.
    # Launched at the LOCAL angle: at the offshore boundary the water is 8.2 m
    # deep and Snell has already turned the 20 deg deep-water crest to 12.5 deg.
    # Starting the ray at 20 deg would draw the right law from the wrong initial
    # condition -- which is a mistake this project made in the suite first.
    om = 2.0 * math.pi / B.T_SWELL
    c_start = om / B.wavenumber(om, max(-h[0], B.D_MIN))
    th_start = math.asin(float(c_start) / B.deep_celerity(B.T_SWELL)
                         * math.sin(B.THETA0_SWELL))
    y0s = np.linspace(-y_half + 5, y_view - 5, 41)
    ends, starts = [], []
    for y0 in y0s:
        r = B.trace_ray(x, y, h2, B.T_SWELL, 2.0, y0, th_start, ds=1.0,
                        n_max=1200)
        ax.line(r[:, 0], r[:, 1], (24, 60, 120), 1)
        if r[-1, 0] > 470.0:
            ends.append(r[-1, 1])
            starts.append(y0)
    sep = np.diff(np.array(ends)) / np.diff(np.array(starts))
    P.caption(img, [
        'Rays enter at one deep-water angle (%.0f deg) and are integrated with dtheta/ds = (sin.dc/dx - cos.dc/dy)/c. Snell is NOT in the'
        % math.degrees(B.THETA0_SWELL),
        'integrator; the suite checks the two against each other on the alongshore-uniform bed and they agree to 3e-3 rad. Here the bed is',
        'not uniform: the bar\'s contours are curved, and the ray tube width at the shoreward end runs %.2f to %.2f of its offshore value'
        % (float(sep.min()), float(sep.max())),
        '-- convergent where the bar is shallow, divergent over the rip channels. Straight contours cannot show this, and a refraction test',
        'on straight contours passes by construction, which is the whole reason the bar makes it a real test.'])
    return P.save(img, path)


# ------------------------------------------------------------------ figure 6
def fig_green(path):
    x = B.make_grid(2000.0, 2.0)
    h = -np.maximum(0.02 + 0.005 * (2000.0 - x), 0.02)
    tr = B.transform(x, h, 60.0, 0.4, 0.0, breaking=False)
    m = (tr['d'] > 0.15) & (tr['k'] * tr['d'] < 0.6)
    d, H = tr['d'][m], tr['H'][m]
    tr2 = B.transform(B.make_grid(), B.dean_bed(B.make_grid()), B.T_SWELL,
                      B.H0_SWELL, 0.0, breaking=False)
    m2 = tr2['d'] > 0.4
    img = P.canvas(1000, 620)
    lx = np.log10(d)
    ly = np.log10(H / H[0])
    lx2 = np.log10(tr2['d'][m2])
    ly2 = np.log10(tr2['H'][m2] / tr2['H'][m2][0])
    ax = P.Axes(img, (95, 60, 960, 470),
                (min(lx.min(), lx2.min()) - 0.1, max(lx.max(), lx2.max()) + 0.1),
                (-0.15, 0.45),
                title="Green's law is an asymptote, and this beach does not reach it",
                xlabel='log10 depth, m', ylabel='log10 (H / H_ref)')
    ax.frame([-1, -0.5, 0, 0.5, 1], [-0.1, 0, 0.1, 0.2, 0.3, 0.4])
    ref_x = np.array([lx.min() - 0.1, lx.max() + 0.1])
    ax.line(ref_x, -0.25 * (ref_x - lx[0]), BAR, 2, dash=(7, 6))
    ax.line(lx, ly, WAVE, 3)
    ax.line(lx2, ly2, GREEN, 3)
    slope = float(np.polyfit(lx, ly, 1)[0])
    slope2 = float(np.polyfit(lx2, ly2, 1)[0])
    P.legend(ax, [(BAR, "Green's law, slope -1/4 exactly"),
                  (WAVE, 'T = 60 s on a 1:200 ramp: kd down to 0.02, fitted %.4f'
                   % slope),
                  (GREEN, 'this scene, T = 9 s on the Dean ramp: fitted %.4f'
                   % slope2)], ref_x[0] + 0.05, 0.40)
    P.caption(img, [
        'Green is the kd -> 0 limit of energy-flux conservation, so it is only recovered where kd is small. Pushed there deliberately',
        '(a 60 s wave on a 1:200 ramp) the transform reproduces -1/4 to %.4f. On the actual scene the shallowest unbroken water is'
        % abs(slope + 0.25),
        'kd ~ 0.3 and the measured exponent is %.3f -- not an error but the O((kd)^2) term, and it is reported as the measurement it is.'
        % slope2])
    return P.save(img, path)


# ------------------------------------------------------------------ figure 7
def fig_storm(path, h0s=(1.0, 1.5, 2.0, 2.5, 3.0)):
    xs, ds, preds, amps = [], [], [], []
    for H0 in h0s:
        sc = B.run_scene(H0=H0)
        cr = B.bar_crest(sc['x'], sc['h'], sc['h_dean'])
        b = B.breaker_state(sc['tr'])
        xs.append(cr['x'])
        ds.append(cr['d'])
        amps.append(cr['amp'])
        preds.append(b['H_b'] / B.GAMMA_B)
    img = P.canvas(1080, 620)
    ax = P.Axes(img, (95, 60, 1040, 430), (0.8, 3.2), (0, 5.0),
                title='The crest depth tracks H_b/gamma across a factor of three in wave height',
                xlabel='offshore wave height H_0, m',
                ylabel='depth over the bar crest, m')
    ax.frame([1.0, 1.5, 2.0, 2.5, 3.0], _ticks(0, 5.0))
    ax.line(h0s, preds, BAR, 2, dash=(7, 6))
    ax.line(h0s, ds, WAVE, 3)
    for a, b_, c in zip(h0s, ds, xs):
        ax.marker(a, b_, WAVE, 4)
        ax.text(a, b_ - 0.28, 'x=%.0f m' % c, GREY, anchor='ma')
    P.legend(ax, [(BAR, 'H_b/gamma, chapter 12\'s prediction'),
                  (WAVE, 'measured crest depth')], 0.9, 4.6)
    P.caption(img, [
        'One loop, one set of constants, five sea states. The bar migrates seaward and deepens as H_0 rises -- the chapter\'s own',
        'verification item ("migrates seaward when H_b is raised") -- and the crest depth stays within %.0f%% of H_b/gamma throughout.'
        % (100 * max(abs(np.array(ds) / np.array(preds) - 1))),
        'Ratios: ' + '  '.join('%.2f' % (a / b_) for a, b_ in zip(ds, preds))])
    return P.save(img, path)


# ------------------------------------------------------------------ figure 8
def fig_evolution(path):
    x = B.make_grid()
    hd = B.dean_bed(x)
    h, tr, hist = B.evolve(x, hd, B.T_SWELL, B.H0_SWELL, B.THETA0_SWELL)
    img = P.canvas(1180, 600)
    ax = P.Axes(img, (90, 60, 1130, 430), (250, 500), (-5, 0.5),
                title='The bar emerging: the same loop, sampled as it runs',
                xlabel='cross-shore distance, m (shoreward ->)',
                ylabel='bed elevation, m')
    ax.frame(_ticks(250, 500), _ticks(-5, 0.5))
    n = len(hist)
    for i, (step, hh) in enumerate(hist):
        f = i / max(n - 1, 1)
        col = (int(150 - 110 * f), int(160 - 80 * f), int(200 - 130 * f))
        ax.line(x, hh, col, 2 if i == n - 1 else 1)
    ax.line(x, hd, GREY, 2, dash=(7, 6))
    P.caption(img, [
        'Steps %s ... of %d, pale to dark. The ramp is dashed. The ridge grows at the break point, deepens the trough behind it, and'
        % (', '.join(str(s) for s, _ in hist[:4]), B.N_STEPS),
        'walks slowly seaward as it steepens the water in front of it -- which is the feedback, not a drift: each new crest breaks the',
        'wave a little further out, and the next convergence lands a little further out with it.'])
    return P.save(img, path)


# ================================================================ wave 2, s2-*
# The second wave's question was one number: why H/d bottoms at 0.456 behind the
# bar against the 0.40 the wave needs to stop breaking. These four figures are
# the answer and the three things that were eliminated on the way to it.
def fig_reform_map(sc, path):
    """The reform boundary in (relief, back-slope length), and where the loop
    sits on it. THE figure of this wave: the shortfall is a distance."""
    x, h, hd, tr = sc['x'], sc['h'], sc['h_dean'], sc['tr']
    cr = B.bar_crest(x, h, hd)
    th = B.trough(x, h, hd, cr['i'])
    Ls = np.arange(8.0, 81.0, 1.0)
    reliefs = np.arange(0.3, 2.61, 0.02)
    d_c = float(tr['d'][cr['i']])

    img = P.canvas(1180, 700)
    ax = P.Axes(img, (95, 62, 1130, 520), (8, 80), (0.3, 2.6),
                title='The second breaking line is a DISTANCE condition, not a relief one',
                xlabel='crest-to-trough distance L, m',
                ylabel='crest-to-trough relief, m')
    ax.frame(_ticks(8, 80), _ticks(0.3, 2.6))
    # the marched transform's own boundary, probed cell by cell -- a second route
    probe_L, probe_R = [], []
    for L in (10, 12, 15, 18, 20, 25, 30, 35, 40, 47, 55, 65, 75):
        lo, hi = 0.3, 2.6
        for _ in range(9):
            mid = 0.5 * (lo + hi)
            hp = B.probe_back_slope(x, h, hd, cr['i'], L, mid)
            tp = B.transform(x, hp, B.T_SWELL, B.H0_SWELL, B.THETA0_SWELL)
            if len(B.surf_zone_spans(tp)) >= 2:
                hi = mid
            else:
                lo = mid
        probe_L.append(float(L))
        probe_R.append(hi)
    pL = np.array(probe_L)
    pR = np.array(probe_R)
    for i in range(pL.size - 1):
        ax.d.rectangle([float(ax.px(pL[i])), float(ax.py(2.6)),
                        float(ax.px(pL[i + 1])), float(ax.py(min(pR[i], 2.6)))],
                       fill=(222, 238, 228))
    need = np.array([B.reform_relief(d_c, float(L)) for L in Ls])
    ax.line(Ls, np.clip(need, 0.3, 2.6), GREEN, 3)
    ax.line(pL, np.clip(pR, 0.3, 2.6), PURPLE, 3)
    for L, r in zip(probe_L, probe_R):
        ax.marker(L, r, PURPLE, 4)
    L_bar = th['x'] - cr['x']
    ax.marker(L_bar, float(tr['d'][th['i']]) - d_c, BAR, 7)
    ax.text(L_bar + 3, float(tr['d'][th['i']]) - d_c - 0.14,
            'the loop: L = %.0f m, relief %.2f m' % (L_bar, float(tr['d'][th['i']]) - d_c),
            BAR)
    ax.text(46, 2.30, 'the wave UN-BREAKS above this line', GREEN)
    ax.text(46, 0.52, 'one continuous surf zone below it', GREY)
    P.legend(ax, [(GREEN, 'closed form: Gamma(d_t) = gamma_s from '
                          'G = G_eq + (G_c-G_eq)(d/d_c)^-a,  a = K/m + 5/2'),
                  (PURPLE, 'the marched transform, bisected -- a second route '
                           'with no closed form in it'),
                  (BAR, 'where the morphodynamic loop actually lands')],
             11, 2.52)
    P.caption(img, [
        'Purple is the boundary the Dally march actually draws, bisected on relief at each L; green is the closed form, which has no march',
        'in it. They agree in shape and in the 1/L character, and green sits 0.15-0.25 m low throughout -- it assumes a STRAIGHT back slope',
        'and shallow water, and the probe bed has a filtered crest and finite kd. Recorded as the systematic offset it is. The loop lands',
        'below the boundary and to the LEFT of it, and the left is what binds: keep',
        'its own %.2f m of relief, move the trough from %.0f m to about %.0f m (33 m by the march), and the wave reforms. The exponent carries'
        % (float(tr['d'][th['i']]) - d_c, L_bar,
           B._reform_length(d_c, float(tr['d'][th['i']]) - d_c)),
        'K/m, so the decay is paid for in travel DISTANCE and not in depth gained: doubling the relief over 15 m buys far less than doubling L.'])
    return P.save(img, path)


def fig_hd_transect(sc, path):
    """H/d along the transect with the 0.40 line on it -- and the same transect
    on the probe bed, where the wave does reform."""
    x, h, hd, tr = sc['x'], sc['h'], sc['h_dean'], sc['tr']
    cr = B.bar_crest(x, h, hd)
    th = B.trough(x, h, hd, cr['i'])
    d_c = float(tr['d'][cr['i']])
    L_need = int(round(B._reform_length(d_c, float(tr['d'][th['i']]) - d_c)))
    hp = B.probe_back_slope(x, h, hd, cr['i'], L_need, th['d'] - cr['d'])
    tp = B.transform(x, hp, B.T_SWELL, B.H0_SWELL, B.THETA0_SWELL)
    r = tr['H'] / np.maximum(tr['d'], 0.1)
    rp = tp['H'] / np.maximum(tp['d'], 0.1)
    m = np.gradient(tr['d'], tr['dx'])
    geq = np.asarray(B.saturated_ratio(m), float)

    img = P.canvas(1180, 880)
    ax = P.Axes(img, (95, 60, 1130, 400), (300, 500), (0, 1.0),
                title='H/d on the bed the loop built: the 0.40 line is never reached',
                ylabel='H / d')
    ax.frame(_ticks(300, 500), [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    for x0, x1 in B.surf_zone_spans(tr):
        ax.band(max(x0, 300), min(x1, 500), (250, 232, 226))
    geq_show = np.where(tr['brk'] & (geq < 0.95), geq, np.nan)
    ax.line(x, geq_show, PURPLE, 2, dash=(6, 5))
    ax.line(x, r, WAVE, 3)
    ax.hline(B.GAMMA_B, BAR, 2, (6, 5))
    ax.hline(B.GAMMA_STABLE, GREEN, 2, (4, 4))
    ax.vline(cr['x'], GREY, 1, (3, 4))
    ax.text(392, B.GAMMA_STABLE - 0.075, 'gamma_s = 0.40  -- breaking stops here', GREEN)
    ax.text(392, B.GAMMA_B + 0.03, 'gamma = 0.78  -- breaking starts here', BAR)
    ax.marker(th['x'], float(r[th['i']]), (20, 20, 24), 5)
    ax.text(th['x'] + 6, float(r[th['i']]) - 0.10,
            'trough minimum %.3f' % float(r[cr['i']:cr['i'] + 60].min()), (20, 20, 24))
    P.legend(ax, [(WAVE, 'H/d, marched'),
                  (PURPLE, 'GAMMA_eq = gamma_s/sqrt(1 + (5/2)(dd/dx)/K), '
                           'the closed-form saturated ratio'),
                  ((250, 232, 226), 'the wave is breaking here')], 305, 0.30)

    ax2 = P.Axes(img, (95, 470, 1130, 760), (300, 500), (0, 1.0),
                 title='The same transform, the same relief, spread over %d m instead of %.0f'
                       % (L_need, th['x'] - cr['x']),
                 xlabel='cross-shore distance, m (shoreward ->)', ylabel='H / d')
    ax2.frame(_ticks(300, 500), [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    for x0, x1 in B.surf_zone_spans(tp):
        ax2.band(max(x0, 300), min(x1, 500), (250, 232, 226))
    ax2.line(x, rp, WAVE, 3)
    ax2.hline(B.GAMMA_B, BAR, 2, (6, 5))
    ax2.hline(B.GAMMA_STABLE, GREEN, 2, (4, 4))
    sp = B.surf_zone_spans(tp)
    if len(sp) >= 2:
        ax2.text(0.5 * (sp[0][1] + sp[1][0]) - 26, 0.86, 'calm water', GREY)
    P.caption(img, [
        'Top: one continuous surf zone. H/d falls to %.3f behind the crest and stops there, because on a SHOALING bed the Dally decay'
        % float(r[cr['i']:cr['i'] + 60].min()),
        'has a fixed point ABOVE gamma_s -- the dashed purple curve, closed form, %.3f on this inner slope. The wave can only un-break'
        % float(geq[min(cr['i'] + 80, x.size - 1)]),
        'where the bed DEEPENS. Bottom: the same transform, the same %.2f m of relief, the same constants, the trough moved from %.0f m'
        % (th['d'] - cr['d'], th['x'] - cr['x']),
        'to %d m behind the crest. Two breaking lines with calm water between them. THE MODEL HAS THE MEMORY; the bar has not the width.'
        % L_need])
    return P.save(img, path)


def fig_ratio_resolved(path):
    """d_bar/(H_b/gamma) across sea states and across grids: the trend wave 1
    reported as falsifiable is the grid."""
    img = P.canvas(1180, 700)
    H0s = (1.0, 1.5, 2.0, 2.5, 3.0)
    raw, filt = [], []
    for H0 in H0s:
        sc = B.run_scene(H0=H0)
        cr = B.bar_crest(sc['x'], sc['h'], sc['h_dean'])
        b = B.breaker_state(sc['tr'])
        raw.append(B.crest_depth_ratio(sc['tr'], cr, b, field='bed'))
        filt.append(B.crest_depth_ratio(sc['tr'], cr, b, field='wave'))
    ax = P.Axes(img, (95, 62, 600, 480), (0.8, 3.2), (0.75, 1.08),
                title='across sea states', xlabel='offshore H_0, m',
                ylabel='d_bar / (H_b/gamma)')
    ax.frame(_ticks(0.8, 3.2, 5), [0.8, 0.85, 0.9, 0.95, 1.0, 1.05])
    ax.hline(1.0, GREY, 1, (4, 4))
    ax.line(H0s, raw, BAR, 3)
    ax.line(H0s, filt, GREEN, 3)
    for a, b_ in zip(H0s, raw):
        ax.marker(a, b_, BAR, 4)
    for a, b_ in zip(H0s, filt):
        ax.marker(a, b_, GREEN, 4)
    P.legend(ax, [(BAR, 'raw bed depth at the crest  (wave 1\'s number)'),
                  (GREEN, 'the depth the wave broke in')], 0.85, 1.06)

    dxs = (2.0, 1.0, 0.5, 0.25)
    rawg, filtg = [], []
    for dx in dxs:
        dt = min(300.0, 0.6 * dx * dx / (2.0 * 6.7e-4))
        sc = B.run_scene(dx=dx, dt=dt, n_steps=int(round(2000 * 300.0 / dt)))
        cr = B.bar_crest(sc['x'], sc['h'], sc['h_dean'])
        b = B.breaker_state(sc['tr'])
        rawg.append(B.crest_depth_ratio(sc['tr'], cr, b, field='bed'))
        filtg.append(B.crest_depth_ratio(sc['tr'], cr, b, field='wave'))
    ax2 = P.Axes(img, (655, 62, 1130, 480), (0, 2.1), (0.75, 1.08),
                 title='across grids, at one sea state',
                 xlabel='grid spacing dx, m', ylabel='')
    ax2.frame([0, 0.5, 1.0, 1.5, 2.0], [0.8, 0.85, 0.9, 0.95, 1.0, 1.05])
    ax2.hline(1.0, GREY, 1, (4, 4))
    ax2.line(dxs, rawg, BAR, 3)
    ax2.line(dxs, filtg, GREEN, 3)
    for a, b_ in zip(dxs, rawg):
        ax2.marker(a, b_, BAR, 4)
    for a, b_ in zip(dxs, filtg):
        ax2.marker(a, b_, GREEN, 4)
    P.caption(img, [
        'LEFT is what wave 1 reported and offered as a falsifiable prediction: the crest sits consistently shallower than H_b/gamma and',
        'converges on it as the waves grow. RIGHT is the same quantity with the sea state held and the GRID refined, and it is the same',
        'curve. The two are one artefact: H_b and d_b come out of the transform, which reads the wavelength-filtered depth, while the raw',
        'bed is shallower at a sharp crest -- and a bigger bar is a broader bar, so a fixed filter takes proportionally less off it. Read',
        'in one depth field the relation holds to 1-3% at every sea state and every grid. Chapter 12\'s d_bar ~ H_b/gamma is not asymptotic.'])
    return P.save(img, path)


def fig_saturated_gamma(path):
    """The saturated H/d against bed slope: closed form, march, and the field
    measurement neither was written from."""
    img = P.canvas(1180, 660)
    slopes = np.array([1 / 200., 1 / 150., 1 / 100., 1 / 80., 1 / 60., 1 / 40.,
                       1 / 30., 1 / 25., 1 / 20.])
    meas = []
    for tb in slopes:
        xp = np.arange(0.0, 1400.0, 1.0)
        hp = np.minimum(-(9.0 - tb * xp), -0.05)
        tp = B.transform(xp, hp, B.T_SWELL, 1.5, 0.0)
        ok = tp['brk'] & (tp['d'] > 0.6)
        idx = np.nonzero(ok)[0]
        meas.append(float((tp['H'] / tp['d'])[idx[len(idx) // 2:]].mean())
                    if idx.size > 6 else np.nan)
    fine = np.linspace(0.002, 0.058, 400)
    cf = np.asarray(B.saturated_ratio(-fine), float)

    ax = P.Axes(img, (95, 62, 1130, 470), (0, 0.062), (0, 1.15),
                title='A broken wave does not decay to 0.40 -- it decays to a ratio the SLOPE sets',
                xlabel='bed slope tan(beta)  (shoaling)', ylabel='saturated H / d')
    ax.frame([0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06],
             [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.d.rectangle([float(ax.px(0)), float(ax.py(1.0)),
                    float(ax.px(0.062)), float(ax.py(0.2))],
                   outline=(200, 208, 216))
    ax.text(0.0015, 1.03, 'Raubenheimer, Guza & Elgar (1996): 0.2 to 1.0 on a '
                          'natural beach, correlated with local slope', GREY)
    ax.line(fine, np.clip(cf, 0, 1.15), GREEN, 3)
    for tb, mv in zip(slopes, meas):
        ax.marker(float(tb), mv, PURPLE, 5)
    ax.hline(B.GAMMA_STABLE, BAR, 2, (5, 5))
    ax.text(0.0225, B.GAMMA_STABLE - 0.075,
            'gamma_s = 0.40 -- the FLAT-BED limit of the family, not a surf zone', BAR)
    ax.vline(B.saturation_slope_limit(), (20, 20, 24), 2, (4, 4))
    ax.text(B.saturation_slope_limit() - 0.0135, 0.90, '2K/5 = %.3f'
            % B.saturation_slope_limit(), (20, 20, 24))
    P.legend(ax, [(GREEN, 'closed form GAMMA_eq = gamma_s/sqrt(1 + (5/2)(dd/dx)/K)'),
                  (PURPLE, 'the marched Dally transform on plane slopes'),
                  ((20, 20, 24), 'the slope above which NO saturated state exists')],
             0.0015, 0.30)
    P.caption(img, [
        'The fixed point of the Dally march on a plane slope, in closed form, against the march itself. They agree to 3% out to 1:60 and',
        'to 9% at 1:30, where the shallow-water flux the closed form assumes stops being true. Three consequences: a surf zone saturates',
        'ABOVE gamma_s and the excess is the slope; the saturated gamma RISES with slope, which is what Raubenheimer et al. measured in the',
        'field eleven years after Dally and did not attribute to it; and past tan(beta) = 2K/5 there is no saturated state at all -- the',
        'shoaling gain outruns the breaking loss and the wave surges. That is the reflective end of Wright & Short arriving unbidden.'])
    return P.save(img, path)


def fig_forcing(path):
    """The three ways to widen a bar, and all three lower the relief."""
    x = B.make_grid()
    hd = B.dean_bed(x)
    cases = []
    h, _ = B.evolve_forced(x, hd, B.T_SWELL, B.THETA0_SWELL)
    cases.append(('steady, monochromatic', h, (120, 92, 48)))
    h, _ = B.evolve_forced(x, hd, B.T_SWELL, B.THETA0_SWELL,
                           z_of_t=lambda t: 1.0 * math.sin(
                               2.0 * math.pi * t / (12.42 * 3600.0)))
    cases.append(('+-1.0 m semidiurnal tide', h, WAVE))
    h, _ = B.evolve_forced(x, hd, B.T_SWELL, B.THETA0_SWELL,
                           h0_of_t=lambda t: 2.0 + 1.0 * math.sin(
                               2.0 * math.pi * t / (5 * 24 * 3600.0)))
    cases.append(('storm/calm, H_0 = 1-3 m over 5 d', h, PURPLE))
    h, _ = B.evolve_forced(x, hd, B.T_SWELL, B.THETA0_SWELL, n_quantiles=5)
    cases.append(('Rayleigh height distribution, 5 quantiles', h, GREEN))

    img = P.canvas(1180, 680)
    ax = P.Axes(img, (95, 62, 1130, 470), (250, 460), (-5.2, -0.5),
                title='Every way to widen the bar lowers it -- cause 4 reverses',
                xlabel='cross-shore distance, m (shoreward ->)',
                ylabel='bed elevation, m')
    ax.frame(_ticks(250, 460), _ticks(-5.2, -0.5))
    ax.line(x, hd, GREY, 2, dash=(7, 6))
    for _, hh, col in cases:
        ax.line(x, hh, col, 3)
    P.legend(ax, [(GREY, 'the initial Dean ramp')]
             + [(c, n) for n, _, c in cases], 255, -0.75)
    lines = []
    for n, hh, _ in cases:
        cr = B.bar_crest(x, hh, hd)
        th = B.trough(x, hh, hd, cr['i'])
        lines.append('%-42s crest %.2f m amp %.2f m   trough %s   relief %s'
                     % (n, cr['d'], cr['amp'],
                        ('%.2f m' % th['d']) if th else 'none found',
                        ('%.2f m' % (th['d'] - cr['d'])) if th else '-'))
    P.caption(img, lines + [
        'Chapter 12 says the profile "breathes on a storm/calm cycle", and a moving break point is the obvious way to build the wide bar',
        'section B needs. It is the wrong way round in 1-D: cycling walks the convergence across the profile and smears it into a terrace.',
        'The Rayleigh average is the physically right mechanism for bar WIDTH and it works -- 15 m of crest-to-trough becomes 23 -- but it',
        'pays for every metre in relief. Nothing tried in this wave widens the trough without flattening the bar, which is why the gap holds.'])
    return P.save(img, path)


def main():
    os.makedirs(OUT, exist_ok=True)
    print('evidence -> %s' % os.path.abspath(OUT))
    sc = B.run_scene()
    sc_storm = B.run_scene(H0=B.H0_STORM)
    for fn, args in ((fig_profile, (sc, sc_storm, 's1-profile-bar.png')),
                     (fig_transform, (sc, 's1-wave-transform.png')),
                     (fig_flux, (sc, 's1-flux-convergence.png')),
                     (fig_plan, (sc, 's1-plan-depth.png')),
                     (fig_rays, (sc, 's1-refraction-rays.png')),
                     (fig_green, ('s1-shoaling-green.png',)),
                     (fig_storm, ('s1-storm-migration.png',)),
                     (fig_evolution, ('s1-evolution.png',)),
                     (fig_reform_map, (sc, 's2-reform-map.png')),
                     (fig_hd_transect, (sc, 's2-hd-transect.png')),
                     (fig_ratio_resolved, ('s2-ratio-resolved.png',)),
                     (fig_saturated_gamma, ('s2-saturated-gamma.png',)),
                     (fig_forcing, ('s2-forcing-history.png',))):
        a = list(args)
        a[-1] = os.path.join(OUT, a[-1])
        print('   %s' % os.path.basename(fn(*a)))


if __name__ == '__main__':
    main()
