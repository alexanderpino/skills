"""Halfar ANATOMY — the SIA solver against an EXACT analytic solution.

WHY THIS FIGURE IS DIFFERENT FROM THE OTHER TWO. `hex_anatomy` and `anisotropy_anatomy` draw
geometry; `flow_anatomy` draws a contrast between two routings. This one draws the top rung of
`VALIDATION.md`'s own evidence ladder: agreement with a **published exact solution**, which is the
only kind of check that can tell "the code solves its equation correctly" apart from "the equation
is right".

THE BENCHMARK. Halfar (1983), as standardised by Bueler et al. (2005) 'Test B': an isothermal ice
dome spreading on a flat bed with no mass balance has a self-similar exact profile

    H(r, t) = H_c(t) · [ 1 − (r/R(t))^(4/3) ]^(3/7)                for Glen n = 3

⚠️ **NEITHER EXPONENT APPEARS ANYWHERE IN THE SOLVER.** `4/3 = (n+1)/n` and `3/7 = n/(2n+1)` are
consequences of the analytic solution. `sims_illustrative.glacier_sia` contains an `H^(n+2)`
diffusivity and nothing else; grep it for `3/7` and there is no hit. So recovering the shape — and,
in panel d, the exponent itself by fitting — is an independent check of the diffusivity rather than
a restatement of it. That independence is the whole value, and it is the property most easily lost
by a well-meaning refactor that "simplifies" the benchmark to reuse a constant.

WHAT THE PANELS SHOW. a: the profile at t=0 and after 1600 model years, with the analytic shape at
the evolved radius on top of it. b: the same profiles at four times, each normalised by its OWN
centre height and radius, collapsing onto one curve — self-similarity is the claim, and a collapse
is what it looks like. c: the residual against radius with the 3% acceptance band, showing WHERE
the error lives. d: the exponent recovered by fitting, against the analytic 3/7.

The numpy half carries no Pillow dependency, so `tests/test_halfar_anatomy.py` imports the
measurements from here. Writes `halfar_anatomy.png`. Run: `python halfar_anatomy.py`.
"""
import numpy as np

import sims_illustrative as sims

N = 121
CELLSIZE = 12000.0                 # 12 km cells, ~1450 km domain
H0, R0 = 3000.0, 500e3             # initial dome: 3 km thick, 500 km radius
A_GLEN = 1e-16 / (365.25 * 24 * 3600)      # 1e-16 Pa^-3 a^-1 in SI
DT = 200.0 * 3.15e7                        # 200 model years per step
STEPS = (2, 4, 8, 16)

# The analytic exponents. Named here ONLY so the figure can label them; the solver
# never sees these values, which is the point of the whole comparison.
P_RADIAL = 4.0 / 3.0               # (n+1)/n
P_SHAPE = 3.0 / 7.0                # n/(2n+1)
SHAPE_TOLERANCE = 0.03             # the acceptance band test_benchmarks.py uses


def radius_field(n=N, cellsize=CELLSIZE):
    c = (n - 1) // 2
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    return np.hypot(xx - c, yy - c) * cellsize, c


def halfar(r, centre_height, radius):
    """The exact self-similar profile. Written from the paper, not from the solver."""
    s = np.clip(np.asarray(r, float) / radius, 0.0, 1.0)
    return centre_height * np.maximum(1.0 - s ** P_RADIAL, 0.0) ** P_SHAPE


def evolve(steps):
    """Run the shipped SIA solver from the exact profile for `steps` steps."""
    r, c = radius_field()
    h_init = halfar(r, H0, R0)
    h = sims.glacier_sia(np.zeros((N, N)), h_init, steps=int(steps), A=A_GLEN,
                         dt=DT, cellsize=CELLSIZE, beta=0.0, max_substeps=4000)
    return r, c, h_init, h


def profile(h, r, c):
    """A radial slice out from the dome centre, with its own centre height and margin."""
    rad, prof = r[c, c:], h[c, c:]
    margin = rad[prof > 1.0].max()
    return rad, prof, float(h[c, c]), float(margin)


def shape_residual(steps=8):
    """Max |numeric/H_c − analytic| over the interior, the quantity the suite bounds."""
    r, c, _h0, h = evolve(steps)
    rad, prof, hc, rn = profile(h, r, c)
    interior = (rad > 0) & (rad < 0.7 * rn)
    err = np.abs(prof[interior] / hc - halfar(rad[interior], 1.0, rn))
    return float(err.max()), rad[interior], err


def fitted_exponent(steps=8):
    """Recover `3/7` from the numerical profile by regression.

    `log(H/H_c) = p · log(1 − s^(4/3))`, so the slope IS the shape exponent. The fit window
    excludes the innermost cells (where `log(1 − s^(4/3))` → 0 and the regression is ill-conditioned)
    and the outer 30% (where the SIA degenerates at the margin and the exact solution has a
    singular slope).
    """
    r, c, _h0, h = evolve(steps)
    rad, prof, hc, rn = profile(h, r, c)
    m = (rad > 0.05 * rn) & (rad < 0.7 * rn) & (prof > 1.0)
    s = np.clip(rad[m] / rn, 0.0, 1.0)
    x = np.log(1.0 - s ** P_RADIAL)
    y = np.log(prof[m] / hc)
    return float(np.polyfit(x, y, 1)[0])


def volume_error(steps=8):
    """Relative change in total ice. With no mass balance this must be zero."""
    _r, _c, h_init, h = evolve(steps)
    return float(abs(h.sum() - h_init.sum()) / h_init.sum())


def measurements():
    """Everything the figure prints, in one call the test can re-run."""
    r, c, h_init, h = evolve(8)
    _rad, _prof, hc, rn = profile(h, r, c)
    err, _radius, _curve = shape_residual(8)
    return {
        'centre_initial': H0, 'centre_final': hc,
        'radius_initial': R0, 'radius_final': rn,
        'shape_error': err,
        'volume_error': volume_error(8),
        'exponent': fitted_exponent(8),
        'exponent_analytic': P_SHAPE,
        'years': 8 * DT / 3.15e7,
    }


# --------------------------------------------------------------------------- #
# drawing
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                                          # pragma: no cover
    Image = None

PANEL_W, PANEL_H = 300, 330
COLS, ROWS = 4, 1
PAD, TOP = 26, 92

BG = (250, 249, 246)
INK = (28, 30, 36)
MUTED = (120, 122, 128)
GRID = (222, 220, 214)
RED = (176, 60, 36)
BLU = (38, 76, 158)
GRN = (26, 106, 68)
ACCENT = (150, 60, 130)


def _font(sz, bold=False):
    try:
        return ImageFont.truetype(
            '/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'
            % ('-Bold' if bold else ''), sz)
    except OSError:                                          # pragma: no cover
        return ImageFont.load_default()


class _Ax(object):
    def __init__(self, d, box, xlim, ylim):
        self.d, self.box = d, box
        self.xlim, self.ylim = xlim, ylim
        d.rectangle(list(box), outline=MUTED)

    def px(self, x):
        lo, hi = self.xlim
        return self.box[0] + (x - lo) / (hi - lo) * (self.box[2] - self.box[0])

    def py(self, y):
        lo, hi = self.ylim
        return self.box[3] - (y - lo) / (hi - lo) * (self.box[3] - self.box[1])

    def line(self, xs, ys, col, width=2):
        pts = [c for x, y in zip(np.atleast_1d(xs), np.atleast_1d(ys))
               for c in (self.px(float(x)), self.py(float(y)))]
        if len(pts) >= 4:
            self.d.line(pts, fill=col, width=width)

    def hline(self, y, col, width=1):
        self.d.line([self.box[0], self.py(y), self.box[2], self.py(y)],
                    fill=col, width=width)


def build():
    if Image is None:                                        # pragma: no cover
        raise SystemExit('halfar_anatomy needs Pillow:  pip install pillow')
    m = measurements()
    W = PAD * 2 + COLS * PANEL_W
    # 8 caption lines at 17 px from `cap`, plus a bottom margin. The first
    # canvas was 30 px short and clipped the last line — the one carrying the
    # volume result.
    H = TOP + PAD + PANEL_H + 196
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    f_t, f_h, f_s, f_b = _font(26, True), _font(15, True), _font(13), _font(13, True)

    d.text((PAD, 22), 'The SIA solver against an exact solution — Halfar (1983)',
           INK, font=f_t)
    d.text((PAD, 54), 'chapter 12 · %d×%d cells at %.0f km · %.0f model years · '
                      'drawn from sims_illustrative.glacier_sia'
           % (N, N, CELLSIZE / 1e3, m['years']), MUTED, font=f_s)

    side = PANEL_W - 40
    r, c, h_init, h = evolve(8)
    rad, prof, hc, rn = profile(h, r, c)

    # --- a: the profiles ----------------------------------------------------
    x0 = PAD
    d.text((x0, TOP - 26), 'a.  the dome, before and after', INK, font=f_h)
    ax = _Ax(d, (x0 + 34, TOP, x0 + side + 34, TOP + side), (0.0, 700.0), (0.0, 3200.0))
    for t in (0, 1000, 2000, 3000):
        ax.hline(t, GRID)
        d.text((x0 + 30, ax.py(t)), '%d' % t, MUTED, font=f_s, anchor='rm')
    ax.line(rad / 1e3, h_init[c, c:], MUTED, 2)
    ax.line(rad / 1e3, prof, BLU, 3)
    ax.line(rad / 1e3, halfar(rad, hc, rn), RED, 2)
    d.text((x0 + 34, TOP + side + 8), 'radius, km        thickness, m', MUTED, font=f_s)
    d.text((x0 + 34, TOP + side + 26), 'grey t=0 · blue numeric · red exact', INK, font=f_b)

    # --- b: the self-similar collapse ---------------------------------------
    x0 = PAD + PANEL_W
    d.text((x0, TOP - 26), 'b.  self-similar collapse', GRN, font=f_h)
    bx = _Ax(d, (x0 + 34, TOP, x0 + side + 34, TOP + side), (0.0, 1.0), (0.0, 1.08))
    for t in (0.0, 0.5, 1.0):
        bx.hline(t, GRID)
        d.text((x0 + 30, bx.py(t)), '%.1f' % t, MUTED, font=f_s, anchor='rm')
    ss = np.linspace(0, 1, 200)
    bx.line(ss, halfar(ss, 1.0, 1.0), RED, 3)
    for st in STEPS:
        rr, cc, _hi, hh = evolve(st)
        ra, pr, hcc, rnn = profile(hh, rr, cc)
        keep = pr > 1.0
        bx.line(ra[keep] / rnn, pr[keep] / hcc, GRN, 1)
    d.text((x0 + 34, TOP + side + 8), 'r/R           H/H_c', MUTED, font=f_s)
    d.text((x0 + 34, TOP + side + 26), 'four times, one curve', GRN, font=f_b)

    # --- c: the residual ----------------------------------------------------
    x0 = PAD + 2 * PANEL_W
    d.text((x0, TOP - 26), 'c.  where the error lives', ACCENT, font=f_h)
    err, err_rad, err_curve = shape_residual(8)
    cx = _Ax(d, (x0 + 40, TOP, x0 + side + 40, TOP + side), (0.0, 0.72),
             (0.0, SHAPE_TOLERANCE * 1.15))
    for t in (0.0, 0.01, 0.02, 0.03):
        cx.hline(t, GRID)
        d.text((x0 + 36, cx.py(t)), '%.0f%%' % (t * 100), MUTED, font=f_s, anchor='rm')
    cx.hline(SHAPE_TOLERANCE, ACCENT, 2)
    d.text((x0 + 44, cx.py(SHAPE_TOLERANCE) + 3), 'suite bound, 3%', ACCENT, font=f_s)
    cx.line(err_rad / rn, err_curve, BLU, 2)
    d.text((x0 + 40, TOP + side + 8), 'r/R     |numeric − exact|', MUTED, font=f_s)
    d.text((x0 + 40, TOP + side + 26), 'peak %.2f%%, at the margin' % (100 * err),
           BLU, font=f_b)

    # --- d: the exponent, recovered -----------------------------------------
    x0 = PAD + 3 * PANEL_W
    d.text((x0, TOP - 26), 'd.  the exponent comes back', RED, font=f_h)
    dx = _Ax(d, (x0 + 40, TOP, x0 + side + 40, TOP + side), (0.0, 5.0), (0.38, 0.50))
    for t in (0.40, 0.4286, 0.46, 0.50):
        dx.hline(t, GRID if abs(t - P_SHAPE) > 1e-6 else RED,
                 1 if abs(t - P_SHAPE) > 1e-6 else 2)
        d.text((x0 + 36, dx.py(t)), '%.3f' % t, MUTED, font=f_s, anchor='rm')
    d.text((x0 + 44, dx.py(P_SHAPE) - 15), 'analytic 3/7', RED, font=f_b)
    for i, st in enumerate(STEPS):
        p = fitted_exponent(st)
        px_, py_ = dx.px(i + 1.0), dx.py(p)
        d.ellipse([px_ - 4, py_ - 4, px_ + 4, py_ + 4], fill=BLU)
        d.text((px_, TOP + side + 6), '%d' % st, MUTED, font=f_s, anchor='ma')
    d.text((x0 + 40, TOP + side + 24), 'steps of 200 model years', MUTED, font=f_s)
    d.text((x0 + 40, TOP + side + 42),
           'fitted %.4f vs 3/7 = %.4f' % (m['exponent'], P_SHAPE), RED, font=f_b)

    cap = TOP + PANEL_H + 34
    for i, line in enumerate([
        'THIS IS THE ONLY FIGURE IN THIS SKILL THAT CHECKS A SOLVER AGAINST AN EXACT SOLUTION, and it is the top rung of VALIDATION.md\'s own',
        'evidence ladder — the rung that separates "the code solves its equation correctly" from "the equation is right". Halfar (1983), as',
        'standardised by Bueler et al. (2005) Test B: an isothermal dome on a flat bed with no mass balance spreads self-similarly as',
        'H = H_c·[1 − (r/R)^(4/3)]^(3/7) for Glen n = 3. ⚠️ NEITHER EXPONENT APPEARS IN THE SOLVER — 4/3 = (n+1)/n and 3/7 = n/(2n+1) are',
        'consequences of the analytic solution, while glacier_sia carries an H^(n+2) diffusivity and nothing else. Over %.0f model years the'
        % m['years'],
        'centre thins %.0f → %.0f m while the margin advances %.0f → %.0f km, the interior shape holds to %.2f%% against the suite\'s 3%% bound,'
        % (m['centre_initial'], m['centre_final'], m['radius_initial'] / 1e3,
           m['radius_final'] / 1e3, 100 * m['shape_error']),
        'and ice volume is conserved EXACTLY — the relative change is 0.0, not merely small. Panel d fits the shape exponent out of the'
        if m['volume_error'] == 0.0 else
        'and ice volume is conserved to %.1e relative. Panel d fits the shape exponent out of the' % m['volume_error'],
        'numerical profile and gets %.4f against the analytic %.4f. Drawn from sims_illustrative.py, guarded by tests/test_halfar_anatomy.py.'
        % (m['exponent'], P_SHAPE),
    ]):
        d.text((PAD, cap + i * 17), line, INK if i == 0 else MUTED, font=f_s)
    return img


if __name__ == '__main__':
    build().save('halfar_anatomy.png')
    print('wrote halfar_anatomy.png')
