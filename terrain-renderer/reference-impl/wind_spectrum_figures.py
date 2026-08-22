"""Wave 17's evidence: the slope statistics derived, and Cox & Munk as a limit.

Three figures, drawn with `beach_plot` into `evidence/` as
`s17-*.png`. Every number comes from `wind_spectrum.py`; nothing is read back
out of a PNG and nothing here computes physics of its own.

⚠️ NO BURNED-IN COMMENTARY. Axis labels, tick labels and legends only. The
contract's wave-11 finding was that captions inside the pixels defeat a blind
critic, so every word of interpretation lives in the `.caption.md` sidecars.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import beach_optics as BOP                                      # noqa: E402
import beach_plot as BP                                         # noqa: E402
import wind_spectrum as W                                       # noqa: E402

EV = os.environ.get('BEACH_OUT', os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'evidence'))

# a palette: one hue per cut-off, cool to warm as the instrument gets finer
CUT_COL = [(38, 70, 132), (32, 118, 160), (46, 150, 128), (170, 140, 40),
           (196, 96, 40), (170, 48, 60)]
CM_COL = (24, 26, 30)
BAND = (232, 228, 214)
PHIL = (120, 60, 150)
POOL = (196, 96, 40)
SEA = (38, 70, 132)
GREY = (150, 152, 158)

RATIO = W.u125_over_u10()
BIG = 1e12
K_TOP = 10.0 * W.K_M
CUTS = (11.0, 20.0, 95.0, 250.0, 370.0, K_TOP)
CUT_LAB = ('11 (L band)', '20 (C&M slick)', '95 (Ku band)', '250 (Ka band)',
           '370 (capillary)', '3700 (all)')


def _u10(u125):
    return u125 / RATIO


# ---------------------------------------------------------------- figure 1
def fig_mss_vs_cox_munk(path=None):
    """mss from the derivation against Cox & Munk over the wind range, with
    the cut-off dependence shown as a FAMILY rather than a line.

    THE FIGURE THE ROUND WAS ASKED FOR. The left panel is the control whose
    answer is known in advance; the right panel is why the control needs an
    argument before it has an answer at all."""
    img = BP.canvas(1500, 700)
    d = BP.ImageDraw.Draw(img)
    d.text((40, 26), 'Mean square slope: derived from the wind, against the '
                     '1954 fit', fill=BP.INK, font=BP.FONT_B)

    # ---- left: mss against wind, one curve per cut-off
    ax = BP.Axes(img, (90, 90, 700, 600), (0.0, 15.0), (0.0, 0.09),
                 title='against wind, at large fetch',
                 xlabel='U at 12.5 m, m/s', ylabel='mean square slope')
    ax.frame(xticks=[0, 3, 6, 9, 12, 15],
             yticks=[0.0, 0.02, 0.04, 0.06, 0.08], yfmt='%.2f')
    u = np.linspace(1.0, 14.0, 60)
    cm = W.cox_munk_total(u)
    ax.fill_between(u, cm - W.CM_SIGMA, cm + W.CM_SIGMA, BAND)
    for i, kc in enumerate(CUTS):
        y = [W.mss(_u10(uu), BIG, kc, n=4001) for uu in u]
        ax.line(u, y, CUT_COL[i], 2)
    ax.line(u, cm, CM_COL, 3)
    BP.legend(ax, [(CM_COL, 'Cox & Munk 1954, +- 0.004')]
              + [(CUT_COL[i], 'k_c = ' + CUT_LAB[i]) for i in range(len(CUTS))],
              0.4, 0.086)

    # ---- right: mss against the cut-off itself, at the scene's wind
    ax2 = BP.Axes(img, (830, 90, 1440, 600), (0.0, 3.7), (0.0, 0.045),
                  title='against the cut-off, at U = 6 m/s',
                  xlabel='log10 upper cut-off k_c, rad/m',
                  ylabel='mean square slope below k_c')
    ax2.frame(xticks=[0, 1, 2, 3], yticks=[0.0, 0.01, 0.02, 0.03, 0.04],
              yfmt='%.2f')
    kc = np.geomspace(1.0, K_TOP, 90)
    m = [W.mss(_u10(6.0), BIG, float(k), n=4001) for k in kc]
    cm6 = float(W.cox_munk_total(6.0))
    ax2.fill_between(np.array([0.0, 3.7]),
                     np.array([cm6 - W.CM_SIGMA] * 2),
                     np.array([cm6 + W.CM_SIGMA] * 2), BAND)
    ax2.hline(cm6, CM_COL, 2)
    ax2.line(np.log10(kc), m, SEA, 3)
    for i, k in enumerate(CUTS[:-1]):
        ax2.vline(math.log10(k), CUT_COL[i], 1)
        ax2.marker(math.log10(k), W.mss(_u10(6.0), BIG, k, n=4001),
                   CUT_COL[i], 5)
    BP.legend(ax2, [(CM_COL, 'Cox & Munk at 6 m/s'),
                    (SEA, 'derived mss below k_c')], 1.85, 0.008)
    BP.caption(img, ['scene-linear SI; wind converted 10 m -> 12.5 m by a '
                     'neutral log profile (x1.02117)'], 40, 650)
    return BP.save(img, path or os.path.join(EV, 's17-mss-vs-cox-munk.png'))


# ---------------------------------------------------------------- figure 2
def fig_curvature_spectrum(path=None):
    """B(k), the slope variance per unit ln k -- what the fitted constant was
    standing in for, and what fetch does and does not move."""
    img = BP.canvas(1500, 700)
    d = BP.ImageDraw.Draw(img)
    d.text((40, 26), 'The curvature spectrum B(k): slope variance per unit '
                     'ln k', fill=BP.INK, font=BP.FONT_B)

    kk = np.geomspace(0.02, K_TOP, 400)
    lk = np.log10(kk)

    # ---- left: four winds, against the flat constant the project shipped
    ax = BP.Axes(img, (90, 90, 700, 600), (-1.7, 3.7), (0.0, 0.017),
                 title='against wind, at large fetch',
                 xlabel='log10 wavenumber k, rad/m', ylabel='B(k)')
    ax.frame(xticks=[-1, 0, 1, 2, 3],
             yticks=[0.0, 0.005, 0.010, 0.015], yfmt='%.3f')
    winds = (3.0, 6.0, 10.0, 14.0)
    wcol = (CUT_COL[1], SEA, CUT_COL[3], CUT_COL[5])
    for i, uu in enumerate(winds):
        ax.line(lk, W.curvature(kk, _u10(uu), BIG), wcol[i], 2)
    kcap = float(BOP.K_CAP)
    kp_pm = float(BOP.pm_peak_wavenumber(6.0))
    b_code = float(W.cox_munk_total(6.0)) / math.log(kcap / kp_pm)
    ax.line(np.array([math.log10(kp_pm), math.log10(kcap)]),
            np.array([b_code, b_code]), PHIL, 3, (7, 5))
    BP.legend(ax, [(wcol[i], 'U = %g m/s' % winds[i]) for i in range(4)]
              + [(PHIL, 'flat Phillips B, back-solved at 6 m/s')],
              -1.55, 0.0165)

    # ---- right: one wind, four fetches
    ax2 = BP.Axes(img, (830, 90, 1440, 600), (-1.7, 3.7), (0.0, 0.010),
                  title='against fetch, at U = 6 m/s',
                  xlabel='log10 wavenumber k, rad/m', ylabel='B(k)')
    ax2.frame(xticks=[-1, 0, 1, 2, 3],
              yticks=[0.0, 0.002, 0.004, 0.006, 0.008, 0.010], yfmt='%.3f')
    f_edge = W.fetch_for_omega(_u10(6.0), W.OMEGA_MAX)
    fetches = ((BIG, 'large fetch (Omega_c = 0.84)', SEA),
               (1e5, '100 km', CUT_COL[2]),
               (1e4, '10 km', CUT_COL[3]),
               (f_edge, '204 m -- edge of the fitted domain', POOL))
    for fv, lab, col in fetches:
        ax2.line(lk, W.curvature(kk, _u10(6.0), fv), col, 2)
    ax2.line(lk, W.curvature(kk, _u10(6.0), 10.0), GREY, 2, (5, 4))
    BP.legend(ax2, [(c, l) for _, l, c in fetches]
              + [(GREY, '10 m basin -- EXTRAPOLATED, not a prediction')],
              -1.55, 0.0097)
    BP.caption(img, ['scene-linear SI; B(k) = k^3 S(k) is dimensionless and '
                     'mss = INT B(k) d ln k, so area under a curve IS slope '
                     'variance'], 40, 650)
    return BP.save(img, path or os.path.join(EV,
                                             's17-curvature-spectrum.png'))


# ---------------------------------------------------------------- figure 3
def fig_fetch_and_footprint(path=None):
    """Where the model stops having anything to say, and the measurement that
    separates a spectrum defect from a realisation defect."""
    img = BP.canvas(1500, 700)
    d = BP.ImageDraw.Draw(img)
    d.text((40, 26), 'The one place basin size enters, and what it does not '
                     'reach', fill=BP.INK, font=BP.FONT_B)

    # ---- left: inverse wave age against fetch
    ax = BP.Axes(img, (90, 90, 700, 600), (0.0, 7.0), (-0.2, 1.6),
                 title='inverse wave age against fetch',
                 xlabel='log10 fetch, m', ylabel='log10 Omega_c')
    ax.frame(xticks=[0, 1, 2, 3, 4, 5, 6, 7],
             yticks=[0.0, 0.5, 1.0, 1.5], yfmt='%.1f')
    ff = np.geomspace(1.0, 1e7, 300)
    ax.line(np.log10(ff), np.log10(W.omega_c(_u10(6.0), ff)), SEA, 3)
    ax.hline(math.log10(W.OMEGA_FD), CM_COL, 2, (6, 4))
    ax.hline(math.log10(W.OMEGA_MAX), POOL, 2, (6, 4))
    f_edge = W.fetch_for_omega(_u10(6.0), W.OMEGA_MAX)
    for fv, col in ((10.0, POOL), (25.0, POOL), (f_edge, CM_COL)):
        ax.vline(math.log10(fv), col, 1)
        ax.marker(math.log10(fv), math.log10(W.omega_c(_u10(6.0), fv)), col, 5)
    BP.legend(ax, [(SEA, 'Omega_c(fetch) at 6 m/s'),
                   (CM_COL, 'fully developed, 0.84'),
                   (POOL, 'Omega_c = 5, edge of the fitted domain')],
              0.25, 1.52)

    # ---- right: resolved mss against pixel footprint, two spectra
    ax2 = BP.Axes(img, (830, 90, 1440, 600), (-1.5, 0.7), (0.0, 0.04),
                  title='resolved mss against pixel footprint',
                  xlabel='log10 footprint, m',
                  ylabel='mss resolvable below k = pi/L')
    ax2.frame(xticks=[-1.5, -1.0, -0.5, 0.0, 0.5],
              yticks=[0.0, 0.01, 0.02, 0.03, 0.04], xfmt='%.1f', yfmt='%.2f')
    foots = np.geomspace(0.03, 5.0, 80)
    kres = np.array([W.resolvable_wavenumber(f) for f in foots])
    kcap = float(BOP.K_CAP)
    kp_pm = float(BOP.pm_peak_wavenumber(6.0))
    cm6 = float(W.cox_munk_total(6.0))
    e = [W.mss(_u10(6.0), BIG, float(k), n=4001) for k in kres]
    p = [W.phillips_mss_below(float(k), kp_pm, kcap, cm6) for k in kres]
    ax2.line(np.log10(foots), e, SEA, 3)
    ax2.line(np.log10(foots), p, PHIL, 3, (7, 5))
    ax2.hline(cm6, CM_COL, 2, (6, 4))
    ax2.hline(0.0013, POOL, 2)
    BP.legend(ax2, [(SEA, 'derived spectrum (ECKV)'),
                    (PHIL, 'flat Phillips, scaled to Cox & Munk'),
                    (CM_COL, 'total mss at 6 m/s'),
                    (POOL, "the render's resolved mss, 0.0013")],
              -1.42, 0.0385)
    BP.caption(img, ['scene-linear SI; k = pi/L is the box-filter Nyquist the '
                     'renderer already filters its realisation with'], 40, 650)
    return BP.save(img, path or os.path.join(EV,
                                             's17-fetch-and-footprint.png'))


ALL = (fig_mss_vs_cox_munk, fig_curvature_spectrum, fig_fetch_and_footprint)


if __name__ == '__main__':
    for fn in ALL:
        print(fn(), flush=True)
