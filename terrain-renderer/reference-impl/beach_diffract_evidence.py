"""Wave 10's visual evidence: the diffracted field, the transport, the frame.

    python3 beach_diffract_evidence.py            # the three figures
    python3 beach_diffract_evidence.py --figures  # the two plan figures only

A FILE OF ITS OWN AND NOT A BRANCH IN `beach_render.py`. Three builders are
editing this tree at once this wave; the optics lane and the bathymetry lane own
paths in the renderer and this one owns none of them. So the frame here is
produced by IMPORTING the renderer and calling its existing camera, water and
shading exactly as `beach_evidence.py` does -- one code path, no fork, and no
line of the renderer changed.

Everything measured is measured in SCENE-LINEAR SI units before any tone map.
Nothing is read back out of a PNG.
"""
import math
import sys
import time

import numpy as np

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
sys.path.insert(0, HERE)

import beach as B                                            # noqa: E402
import beach_diffract as DF                                  # noqa: E402
import beach_plot as P                                       # noqa: E402

OUT = '../../gauntlet/sea/evidence'

C_INC = (44, 96, 176)          # incident / lit
C_SHA = (196, 84, 40)          # shadow
C_HALF = (18, 140, 96)         # the 1/2 line
C_FAN9 = (150, 92, 190)        # wave 9's hand fan
C_REQ = (90, 92, 100)          # the fan the geometry requires
C_DIFF = (196, 84, 40)


def _wrapcap(img, lines, width=196, x=40, y=None):
    """Caption lines, hard-wrapped to the canvas. A caption that runs off the
    right edge is a caption nobody read."""
    out = []
    for ln in lines:
        cur = ''
        for word in ln.split():
            if len(cur) + len(word) + 1 > width:
                out.append(cur)
                cur = '    ' + word
            else:
                cur = (cur + ' ' + word).strip() if cur else word
        out.append(cur)
        out.append('')
    P.caption(img, out[:-1], x=x, y=y)


def _ramp(v, lo, hi, a, b):
    """A two-colour scene-linear ramp to bytes, for the amplitude map. The
    quantity plotted is K_d, which is dimensionless and already linear; the
    only nonlinearity anywhere in this file is PIL writing 8-bit."""
    t = np.clip((np.asarray(v, float) - lo) / (hi - lo), 0.0, 1.0)[..., None]
    return (np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t)


# ---------------------------------------------------------------- figure one
def field_figure(path, n=280):
    """The diffracted amplitude and direction field in plan, behind the edge.

    Left: K_d over the plan domain from the edge at the plan-form's own pole,
    with the geometric shadow boundary drawn and the 1/2 annotated where it
    crosses. Right: the same for the edge at the TRUE headland tip, which is the
    route gap 3's text names and which turns out to shelter one row of the bay.
    Bottom: K_d along the shadow boundary against range, against the exact 1/2.
    """
    ep = B.equilibrium_plan()
    y = ep['y']
    k = DF.scene_wavenumber()
    img = P.canvas(1680, 1330)

    xs_pl = np.linspace(-900.0, 1000.0, n)
    ys_pl = np.linspace(-1500.0, 1500.0, n)
    XX, YY = np.meshgrid(xs_pl, ys_pl)

    for col, (where, ttl) in enumerate((
            ('pole', 'edge at the plan-form\'s own pole D'),
            ('headland', 'edge at the TRUE headland tip A1'))):
        e = DF.scene_edge(ep, where=where)
        kd = e.kd(XX, YY)
        ax = P.Axes(img, (90 + col * 800, 70, 750 + col * 800, 690),
                    (xs_pl[0], xs_pl[-1]), (ys_pl[0], ys_pl[-1]),
                    title='K_d = |u| in plan -- %s' % ttl,
                    xlabel='x, m (shoreward +)', ylabel='y, m (alongshore)')
        ax.image(np.flipud(_ramp(kd, 0.0, 1.25, (16, 24, 46),
                                 (252, 248, 232))).astype(np.uint8))
        ax.frame(xticks=[-800, -400, 0, 400, 800],
                 yticks=[-1200, -600, 0, 600, 1200])
        t = np.linspace(0.0, 3600.0, 200)
        sx, sy = e.shadow_boundary_line(t)
        ax.line(sx, sy, C_HALF, 2, dash=(9, 6))
        ax.marker(e.tip[0], e.tip[1], (255, 90, 60), 6)
        sd = e.tip + np.outer(np.linspace(0.0, 2400.0, 2), e.screen_dir)
        ax.line(sd[:, 0], sd[:, 1], (255, 255, 255), 3)
        # the shoreline, so the reader can see which coast is in the shadow
        ax.line(ep['x_s'], y, (255, 214, 120), 2)
        g = DF.geometric_shelter(ep, e)
        ax.text(xs_pl[0] + 40, ys_pl[-1] - 110,
                'tip (%.0f, %.0f) m   screen: white   shadow boundary: green'
                % (e.tip[0], e.tip[1]), (30, 34, 40))
        ax.text(xs_pl[0] + 40, ys_pl[-1] - 190,
                'shoreline stations in the GEOMETRIC shadow: %d of %d '
                '(%d of the bay\'s %d)'
                % (g['n'], g['n_rows'], g['n_bay'], g['n_bay_rows']),
                (30, 34, 40))
        # the direction field, as short segments on a coarse lattice
        gx = np.linspace(-800.0, 950.0, 16)
        gy = np.linspace(-1400.0, 1400.0, 22)
        GX, GY = np.meshgrid(gx, gy)
        th = e.direction(GX, GY)
        L = 105.0
        for a, b, t_ in zip(GX.ravel(), GY.ravel(), th.ravel()):
            ax.line([a, a + L * math.cos(t_)], [b, b + L * math.sin(t_)],
                    (120, 220, 255), 1)

    # ---- the 1/2 on the shadow boundary, against range
    e = DF.scene_edge(ep)
    rr = np.geomspace(30.0, 40000.0, 160)
    sx, sy = e.shadow_boundary_line(rr)
    kd = e.kd(sx, sy)
    ax = P.Axes(img, (110, 800, 760, 1060), (math.log10(30.0), math.log10(4e4)),
                (0.44, 0.66),
                title='K_d ON the geometric shadow boundary, against range',
                xlabel='log10( range from the tip, m )', ylabel='K_d = |u|')
    ax.frame(xticks=[1.5, 2, 2.5, 3, 3.5, 4], yticks=[0.45, 0.5, 0.55, 0.6])
    ax.hline(0.5, C_HALF, 2)
    ax.line(np.log10(rr), kd, C_SHA, 2)
    ax.text(math.log10(60.0), 0.508, 'exactly 1/2 -- Sommerfeld, and chapter '
            '12\'s K_d(0) = 0.5000', C_HALF)
    ax.text(math.log10(60.0), 0.63,
            'the approach is O((k r)^-1/2): the RESIDUAL is the reflected '
            'term, not an error', P.MUTED)

    # ---- K_d against the Fresnel parameter, against the chapter's four numbers
    v = np.linspace(-2.5, 3.0, 400)
    ax = P.Axes(img, (900, 800, 1590, 1060), (-2.5, 3.0), (0.0, 1.35),
                title='K_d against the Fresnel parameter v, against chapter '
                      '12\'s own four numbers',
                xlabel='v = b sqrt(2 / (lambda r)),  positive INTO the shadow',
                ylabel='K_d')
    ax.frame(xticks=[-2, -1, 0, 1, 2, 3], yticks=[0, 0.25, 0.5, 0.75, 1.0, 1.25])
    ax.line(v, DF.knife_edge_kd(v), C_SHA, 2)
    ax.vline(0.0, C_HALF, 1)
    for vv, ch in ((0.0, 0.5000), (0.5, 0.31), (1.0, 0.20), (2.0, 0.11)):
        ax.marker(vv, ch, C_INC, 5)
    ax.text(-2.4, 1.22, 'blue dots: the chapter\'s 0.5000 / 0.31 / 0.20 / '
            '0.11.  line: this file, 0.50000 / 0.30783 / 0.20267 / 0.11103',
            C_INC)
    ax.text(-2.4, 0.10, 'a RAY model says zero at all four', P.MUTED)

    _wrapcap(img, [
        's10-wavefield-diffraction  THE TERM NO RAY MODEL HAS, STAMPED AT TWO '
        'PLACES. DERIVED: Sommerfeld\'s exact half-plane solution (1896) in '
        'the form Penney & Price (1952) applied to water waves, with a rigid '
        '(Neumann) screen; Fresnel integrals built here from three routes '
        '(power series, Gauss-Legendre, asymptotic) because there is no scipy '
        'in this container.',
        'CITED: terrain-renderer references/12-water-rendering.md\'s '
        'diffraction section for K_d = 0.5000 on the shadow boundary and '
        '0.31 / 0.20 / 0.11 at v = 0.5 / 1 / 2 (blue dots, lower right) -- '
        'IMPORTED, not restated, and reproduced here to 0.50000 / 0.30783 / '
        '0.20267 / 0.11103 by an implementation that shares no line with the '
        'one that produced them.',
        'MEASURED, scene-linear, nothing read off a PNG: the K_d maps, the '
        'direction field (pale blue segments = grad(arg u), the local wave '
        'orthogonal, an OUTPUT), and the range plot. The green dashed line is '
        'the GEOMETRIC shadow boundary -- what a ray model believes -- and '
        'the field crosses it at exactly 1/2 with no discontinuity.',
        'THE FINDING IS THE RIGHT-HAND PANEL. Gap 3 prescribed "a Sommerfeld '
        'edge stamped at the headland tip". At this coast\'s 20 deg obliquity '
        'that edge shadows 5 shoreline stations of 89 and ONE of the bay\'s '
        '66, all of them on the headland\'s own updrift face. The prescription '
        'fails at the geometry, before any wave theory is reached.',
    ], x=40, y=1115)
    return P.save(img, path)


# ---------------------------------------------------------------- figure two
def transport_figure(path):
    """Wave 9's four rows and wave 10's two, and the fan that produced them."""
    t = DF.transport_table()
    ep = t['_ep']
    fan = t['_fan']
    y = ep['y']
    img = P.canvas(1680, 1330)

    order = [('straight', 'straight, plane crest', (150, 150, 156)),
             ('rotated', 'the closed-form zero-transport coast (THE FLOOR)',
              C_HALF),
             ('bay_plane', 'the bay, plane crest', (200, 160, 60)),
             ('bay_fan9', 'the bay, wave 9\'s hand-stated fan', C_FAN9),
             ('bay_diff_dir', 'the bay, DIFFRACTED direction only', (230, 150,
                                                                    110)),
             ('bay_diff', 'the bay, DIFFRACTED direction + K_d', C_DIFF)]

    # ---- panel 1: mean |theta_loc|
    ax = P.Axes(img, (110, 70, 780, 400), (-0.6, 5.6), (0.0, 7.0),
                title='mean |theta_loc| at the break, degrees',
                xlabel='', ylabel='degrees')
    ax.frame(yticks=[0, 1, 2, 3, 4, 5, 6, 7])
    for i, (kk, lab, col) in enumerate(order):
        v = math.degrees(t[kk]['th_mean'])
        ax.d.rectangle([float(ax.px(i - 0.34)), float(ax.py(v)),
                        float(ax.px(i + 0.34)), float(ax.py(0.0))], fill=col)
        ax.text(i, v + 0.18, '%.3f' % v, P.INK, anchor='ms')
    ax.hline(math.degrees(t['rotated']['th_mean']), C_HALF, 2)

    # ---- panel 2: Q rms over the spiral span, log
    ax = P.Axes(img, (900, 70, 1590, 400), (-0.6, 5.6), (-3.2, -0.7),
                title='Q rms over the spiral span, log10( m3/s )',
                xlabel='', ylabel='log10 Q rms')
    ax.frame(yticks=[-3, -2.5, -2, -1.5, -1])
    for i, (kk, lab, col) in enumerate(order):
        v = math.log10(t[kk]['Q_rms_span'])
        ax.d.rectangle([float(ax.px(i - 0.34)), float(ax.py(v)),
                        float(ax.px(i + 0.34)), float(ax.py(-3.2))], fill=col)
        ax.text(i, v + 0.07, '%.3e' % t[kk]['Q_rms_span'], P.INK, anchor='ms')
    ax.hline(math.log10(t['rotated']['Q_rms_span']), C_HALF, 2)
    P.legend(ax, [(c, l) for _, l, c in order], 2.55, -2.05)

    # ---- panel 3: the amplitude-free meter
    ax = P.Axes(img, (110, 490, 780, 790), (-0.6, 5.6), (0.0, 0.26),
                title='rms sin(2 theta_loc) -- the CERC closure with its '
                      'height and its coefficient divided out',
                xlabel='', ylabel='rms sin(2 theta_loc)')
    ax.frame(yticks=[0, 0.05, 0.1, 0.15, 0.2, 0.25])
    for i, (kk, lab, col) in enumerate(order):
        v = t[kk]['sin2_rms']
        ax.d.rectangle([float(ax.px(i - 0.34)), float(ax.py(v)),
                        float(ax.px(i + 0.34)), float(ax.py(0.0))], fill=col)
        ax.text(i, v + 0.006, '%.4f' % v, P.INK, anchor='ms')
    ax.hline(t['rotated']['sin2_rms'], C_HALF, 2)
    ax.text(2.0, 0.245, 'READ THIS PANEL FIRST. Q goes as H_b^(5/2), so a '
            'shadow that halves', P.INK)
    ax.text(2.0, 0.228, 'the height cuts Q by 5.7x whatever the shoreline is '
            'doing.', P.INK)
    ax.text(2.0, 0.211, 'This column has the height divided out and cannot be '
            'bought that way.', P.INK)

    # ---- panel 4: the three fans against the one the geometry requires
    req = B.required_fan(y, ep['x_s'])
    sl = slice(3, y.size - 3)
    ax = P.Axes(img, (900, 490, 1590, 790), (y[0], y[-1]), (-40.0, 40.0),
                title='the offshore wave direction, per alongshore row',
                xlabel='y, m (alongshore; the swell runs toward +y)',
                ylabel='theta_0, degrees')
    ax.frame(xticks=[-600, -300, 0, 300, 600],
             yticks=[-40, -20, 0, 20, 40])
    ax.hline(math.degrees(B.THETA0_SWELL), (150, 150, 156), 2)
    ax.line(y[sl], np.degrees(req['psi']), C_REQ, 2, dash=(7, 5))
    ax.line(y, np.degrees(B.fan_theta0(y, ep['x_s'], ep['D'])), C_FAN9, 2)
    ax.line(y, np.degrees(fan['theta0']), C_DIFF, 3)
    sh = fan['shadow']
    if sh.any():
        ax.vline(float(y[sh][-1]), C_HALF, 2)
        ax.text(float(y[sh][-1]) + 14, -34,
                'geometric shadow boundary', C_HALF)
    P.legend(ax, [((150, 150, 156), 'plane crest, theta_0 = 20 deg'),
                  (C_REQ, 'the fan the shoreline REQUIRES (geometry only)'),
                  (C_FAN9, 'wave 9: a stated radial fan from the pole'),
                  (C_DIFF, 'wave 10: grad(arg u), an OUTPUT')],
             y[0] + 40, 37.0)

    # ---- panel 5: K_d along the boundary, so the height column is visible
    ax = P.Axes(img, (110, 880, 1590, 1020), (y[0], y[-1]), (0.0, 1.25),
                title='K_d delivered to the offshore boundary, per row -- the '
                      'amplitude half of the same solution',
                xlabel='y, m (alongshore)', ylabel='K_d')
    ax.frame(xticks=[-600, -300, 0, 300, 600], yticks=[0, 0.5, 1.0])
    ax.hline(0.5, C_HALF, 1)
    ax.line(y, fan['kd'], C_DIFF, 2)
    ax.text(y[0] + 30, 1.12, 'K_d falls to %.3f at the sheltered end: the '
            'updrift limb of this bay has almost no wave in it, and the Q '
            'column above is partly reading that rather than an equilibrium.'
            % float(fan['kd'].min()), P.INK)

    _wrapcap(img, [
        's10-wavefield-transport  SIX FIELDS, ONE OFFSHORE SPECTRUM (H_0 = '
        '%.1f m, T = %.0f s, theta_0 = %.0f deg), one ramp, one transform, one '
        'CERC closure. MEASURED, scene-linear. The first four rows are wave '
        '9\'s, RECOMPUTED here rather than quoted, and they reproduce: '
        '%.4f / %.4f / %.4f / %.4f deg.'
        % (B.H0_SWELL, B.T_SWELL, math.degrees(B.THETA0_SWELL),
           math.degrees(t['straight']['th_mean']),
           math.degrees(t['rotated']['th_mean']),
           math.degrees(t['bay_plane']['th_mean']),
           math.degrees(t['bay_fan9']['th_mean'])),
        'DERIVED: the closed-form zero-transport coast (row 2) is the METER\'S '
        'FLOOR and it is why any of the rest means anything -- a near-zero '
        'reading is worthless until zero has been shown to be reachable. The '
        'bay under the diffracted fan reads %.4f deg and %.4e m3/s, against a '
        'floor of %.4f deg and %.4e.'
        % (math.degrees(t['bay_diff']['th_mean']),
           t['bay_diff']['Q_rms_span'],
           math.degrees(t['rotated']['th_mean']),
           t['rotated']['Q_rms_span']),
        'CITED: Komar & Inman 1970 for the sin(2 theta) closure (via '
        'terrain-architect 12); Krumbein / Yasso / Silvester for the log '
        'spiral; Sommerfeld 1896 and Penney & Price 1952 for the edge. OPEN: '
        'the screen bearing at the pole has no barrier behind it -- rotating '
        'it +-40 deg moves the answer by 0.05 deg, which is why it is reported '
        'rather than chased.',
        'THE HONEST READING. The angle meter is still %.1fx its floor and the '
        'amplitude-free meter %.1fx, so the bay is SMALL and not ZERO -- and '
        'wave 9\'s attribution of its residual to the ramp (0.71 deg) and the '
        'march (1.46 deg) is OVERTURNED, because the diffracted field gets '
        'under their sum with both of them untouched.'
        % (t['bay_diff']['th_mean'] / t['rotated']['th_mean'],
           t['bay_diff']['sin2_rms'] / t['rotated']['sin2_rms']),
    ], x=40, y=1115)
    return P.save(img, path)


# -------------------------------------------------------------- figure three
def frame_figure(path):
    """Bar section J's framing, on a bed whose wave field has diffraction in it.

    The renderer is IMPORTED and none of its paths are changed: same camera,
    same water, same optics, same land, same sun as s9-frame-J.png. ONE input
    differs -- the offshore boundary is Sommerfeld's field instead of a plane
    crest.
    """
    import beach_render as RND
    RND._set_runup()
    cs = B.run_coast()
    ep = B.equilibrium_plan(coast=cs)
    fan = DF.scene_fan(ep)
    bay = B.run_bay(embay=True, coast=cs, theta0=fan['theta0'], H0=fan['H0'])
    w = RND.Water(bay)
    ss = RND.SS_HERO
    cams = RND.hero_cameras(w, RND.W_HERO * ss, RND.H_HERO * ss, out=lambda
                            *a, **k: None)
    camJ, infJ = cams[3], cams[4]
    L, ex = RND.render(camJ, w)
    br = B.breaker_row(bay['tr'])
    th = np.degrees(br['theta'])
    ww = max(int(round(0.2 * th.size)) | 1, 3)
    sm = np.convolve(np.pad(th, ww // 2, mode='edge'), np.ones(ww) / ww,
                     mode='valid')
    swing = float(sm.max() - sm.min())
    RND._save(RND.downsample(L, ss), path, caption=[
        's10-wavefield-frame-J  BAR SECTION J\'S FRAMING, ON A WAVE FIELD WITH '
        'DIFFRACTION IN IT. The pair to s9-frame-J.png: same inferred '
        'viewpoint, same 0.5x ultrawide upright, same sun, same optics, same '
        'beach, same air, same plan-form. ONE INPUT CHANGED -- the offshore '
        'boundary is Sommerfeld\'s half-plane field instead of a plane crest.',
        'DERIVED: the per-row offshore direction and height are grad(arg u) '
        'and |u| of an exact wave solution stamped at the plan-form\'s own '
        'pole; nothing per-row is stated. The standing ruling holds -- the '
        'field still arrives from OUTSIDE with one spectrum (H_0 = %.1f m, '
        'T = %.0f s, theta_0 = %.0f deg) and everything shoreward is an output.'
        % (B.H0_SWELL, B.T_SWELL, math.degrees(B.THETA0_SWELL)),
        'MEASURED off the scene-linear buffer, never off this PNG: K_d across '
        'the frame runs %.3f to %.3f, so the updrift limb carries a %.2f m '
        'wave against %.2f m downdrift -- which is what a sheltered bay looks '
        'like and what a plane crest cannot produce. Bay-scale swing of the '
        'breaking crest azimuth %.2f deg.'
        % (float(fan['kd'].min()), float(fan['kd'].max()),
           B.H0_SWELL * float(fan['kd'].min()),
           B.H0_SWELL * float(fan['kd'].max()), swing),
        'STILL OPEN in this frame and unchanged by this wave: the illuminant '
        'is in the wrong half of the sky; ONE surf zone where bar J shows '
        'three to four separated lines; no airborne spray; the bed under the '
        'water reads bright. By "no placeholder in a hero frame" this is a '
        'DIAGNOSTIC and it is labelled as one.',
    ])
    return path, fan, swing


def main():
    t0 = time.time()
    print('WAVE 10 EVIDENCE -- the diffracted wave field')
    print(field_figure('%s/s10-wavefield-diffraction.png' % OUT))
    print(transport_figure('%s/s10-wavefield-transport.png' % OUT))
    if '--figures' not in sys.argv:
        p, fan, sw = frame_figure('%s/s10-wavefield-frame-J.png' % OUT)
        print(p)
    print('%.1f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
