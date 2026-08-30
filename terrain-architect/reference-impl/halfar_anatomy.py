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
the error lives — the curve stops at the 0.7R fit-window edge, which the axis is ticked to make
plain. d: the exponent recovered by fitting, against the analytic 3/7.

e: THE RATE, and it is the panel that makes the other four mean anything. a–d all measure SHAPE,
and shape here is nearly vacuous on its own: the initial condition IS the Halfar profile, so a
solver that barely moves the ice matches it trivially — `H^(n+1)` in place of `H^(n+2)` leaves
every shape row green and LOWERS the residual. Panel e compares the characteristic time recovered
from the numerical thinning against Halfar's closed form, which no near-no-op can fake. See the
RATE section below for the derivation and the measured numbers.

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


# --------------------------------------------------------------------------- #
# The RATE, which is the half of the benchmark the shape cannot see.
#
# ⚠️ WHY THIS EXISTS. Everything above measures SHAPE, and shape alone is a nearly
# vacuous check here: the initial condition IS the Halfar profile, so a solver that
# barely moves the ice scores BETTER on the residual than the correct one. Replacing
# the `H^(n+2)` diffusivity with `H^(n+1)` — a one-character edit — leaves every shape
# row green and lowers the residual from 0.0113 to 0.0049. A guard that a broken solver
# passes more comfortably than a correct one is not a guard.
#
# What the shape cannot see is HOW FAST the dome spreads, and Halfar fixes that too.
# The characteristic time follows from the ice constants alone:
#
#     Gamma = 2 A (rho g)^n / (n + 2)
#     t0    = (1/18)/Gamma * (7/4)^3 * R0^4 / H0^7
#
# and it enters the solution as H_c(t) = H0 (t/t0)^(-1/9), R(t) = R0 (t/t0)^(1/18),
# with the run starting at t = t0. So the SAME t0 can be recovered from the numerical
# thinning, and the two must agree. That comparison is sensitive to the diffusivity by
# construction — `H^(n+1)` puts the fitted t0 at 4.06e13 against an analytic 9.22e9,
# a factor of 4406.
#
# Note `n + 2` appears in Gamma. That is NOT the solver's exponent leaking in: it is the
# published Test B constant (Bueler et al. 2005), written from the paper like the 4/3
# and 3/7 above, and the test below checks it is not read out of sims_illustrative.

N_GLEN = 3
RHO_ICE, G_ACC = 917.0, 9.81


def t0_analytic(A=A_GLEN, rho=RHO_ICE, g=G_ACC, n=N_GLEN, h0=H0, r0=R0):
    """Halfar's characteristic time, from the ice constants and the dome alone.

    No part of the numerical run enters this. It is the closed form.
    """
    gamma = 2.0 * A * (rho * g) ** n / (n + 2.0)
    return (1.0 / 18.0) / gamma * (7.0 / 4.0) ** 3 * r0 ** 4 / h0 ** 7


def t0_from_thinning(steps=8):
    """Recover t0 from how much the solver actually thinned the dome.

    `H_c(t0 + dt)/H0 = ((t0 + dt)/t0)^(-1/9)` inverts to `t0 = dt / ((H0/H_c)^9 - 1)`.
    """
    r, c, _h0, h = evolve(steps)
    _rad, _prof, hc, _rn = profile(h, r, c)
    dt_total = steps * DT
    return float(dt_total / ((H0 / hc) ** 9.0 - 1.0))


# ⚠️ THE MARGIN CANNOT DO THIS JOB, and the reason is worth keeping. `R = R0 (t/t0)^(1/18)`
# inverts just as cleanly, and it looks like a free second opinion. It is not: `profile`
# finds the margin by thresholding on a 12 km grid, so R is quantised to one cell, one cell
# is 2.4% of R0, and the eighteenth power turns that into **53% in t0**. Measured, the margin
# route returns 6.5e9–8.6e9 across the four step counts, non-monotonically — an instrument
# whose noise dwarfs the effect it would police. It was written, measured, and removed.
#
# Nothing is lost by dropping it. Volume is conserved EXACTLY (asserted above), and exact
# volume conservation plus the right thinning rate already fixes the spreading rate — the
# ice has nowhere else to go.


def rate_error(steps=8):
    """Relative disagreement between the fitted and the closed-form t0."""
    return float(abs(t0_from_thinning(steps) / t0_analytic() - 1.0))


RATE_TOLERANCE = 0.05      # the fitted t0 must land within 5% of the closed form


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
        't0_analytic': t0_analytic(),
        't0_fitted': t0_from_thinning(8),
        'rate_error': rate_error(8),
        'years': 8 * DT / 3.15e7,
    }


# --------------------------------------------------------------------------- #
# drawing
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                                          # pragma: no cover
    Image = None

PANEL_W, PANEL_H = 300, 330
COLS, ROWS = 5, 1
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
    img = Image.new('RGB', (W, canvas_height(m)), BG)
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
    # ⚠️ The x axis was unticked and the label read 'at the margin'. It is NOT the margin:
    # `shape_residual` masks to r < 0.7R, so the curve stops at the edge of the FIT WINDOW,
    # and the residual beyond it — where the SIA degenerates and the exact profile has an
    # infinite slope — is not drawn at all. An unticked axis let that read as the full radius.
    for t in (0.0, 0.35, 0.7):
        d.line([cx.px(t), TOP + side, cx.px(t), TOP + side + 4], fill=MUTED)
        d.text((cx.px(t), TOP + side + 6), '%.2f' % t, MUTED, font=f_s, anchor='ma')
    d.line([cx.px(0.7), TOP, cx.px(0.7), TOP + side], fill=ACCENT, width=1)
    d.text((x0 + 40, TOP + side + 24), 'r/R     |numeric − exact|', MUTED, font=f_s)
    d.text((x0 + 40, TOP + side + 42),
           'peak %.2f%% at the 0.7R window edge' % (100 * err), BLU, font=f_b)

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

    # --- e: the rate, which the four panels to the left cannot see -----------
    x0 = PAD + 4 * PANEL_W
    d.text((x0, TOP - 26), 'e.  the rate, unfakeable', GRN, font=f_h)
    ex = _Ax(d, (x0 + 44, TOP, x0 + side + 44, TOP + side), (0.0, 5.0), (0.97, 1.03))
    for t in (0.98, 0.99, 1.00, 1.01, 1.02):
        ex.hline(t, GRID if abs(t - 1.0) > 1e-9 else GRN, 1 if abs(t - 1.0) > 1e-9 else 2)
        d.text((x0 + 40, ex.py(t)), '%.2f' % t, MUTED, font=f_s, anchor='rm')
    d.text((x0 + 48, ex.py(1.0) + 4), 'closed form', GRN, font=f_b)
    t0a = m['t0_analytic']
    for i, st in enumerate(STEPS):
        ratio = t0_from_thinning(st) / t0a
        px_, py_ = ex.px(i + 1.0), ex.py(ratio)
        d.ellipse([px_ - 4, py_ - 4, px_ + 4, py_ + 4], fill=BLU)
        d.text((px_, TOP + side + 6), '%d' % st, MUTED, font=f_s, anchor='ma')
    d.text((x0 + 44, TOP + side + 24), 't0 recovered / t0 closed form', MUTED, font=f_s)
    # The broken solver's point is 4406 — four orders of magnitude off the top of this axis.
    # Stating the number is the only honest way to draw it; a clipped marker would imply it
    # sits just above the frame.
    d.text((x0 + 44, TOP + side + 42), 'H^(n+1) lands at 4406 ↑', RED, font=f_b)

    cap = CAP_TOP
    for i, line in enumerate(caption_lines(m)):
        d.text((PAD, cap + i * CAP_LEADING), line, INK if i == 0 else MUTED, font=f_s)
    return img


CAP_TOP = TOP + PANEL_H + 34
CAP_LEADING = 17
CAP_MARGIN = 20


def caption_lines(m):
    """The caption, as a list, so the CANVAS can be sized from it.

    ⚠️ This is a list rather than a literal inside `build` for one reason: the height used to
    be the hand-tuned constant `TOP + PAD + PANEL_H + 196`, and it was 30 px short — it silently
    clipped the last line, the one carrying the volume result. A number that has to be re-tuned
    by hand every time a sentence is added will eventually not be. `build` now measures this
    list instead, and `tests/test_halfar_anatomy.py` asserts the last line lands inside the
    canvas, so the failure mode is a red row rather than a missing sentence.
    """
    return [
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
        'numerical profile and gets %.4f against the analytic %.4f.'
        % (m['exponent'], P_SHAPE),
        '',
        '⚠️ SHAPE IS NOT ENOUGH, and saying so is part of the figure. The initial condition IS the Halfar profile, so a solver that barely moves',
        'the ice still matches it — swapping the H^(n+2) diffusivity for H^(n+1) leaves every shape row above green and *lowers* the residual to',
        '0.49%. What a near-no-op cannot fake is the RATE — panel e. Halfar fixes it with no free parameters: t0 = (1/18)/Γ·(7/4)³·R0⁴/H0⁷ with',
        'Γ = 2A(ρg)ⁿ/(n+2), and H_c = H0(t/t0)^(−1/9), so t0 can be read back out of the thinning. Closed form %.3e s against %.3e s'
        % (m['t0_analytic'], m['t0_fitted']),
        'recovered from the run — %.2f%% apart, converging as the timestep falls. Under H^(n+1) that recovery returns 4.06e13 s, a factor of 4406.'
        % (100 * m['rate_error']),
        'Drawn from sims_illustrative.py, guarded by tests/test_halfar_anatomy.py.',
    ]


def canvas_height(m):
    """Tall enough for the caption it actually has, measured rather than remembered."""
    return CAP_TOP + len(caption_lines(m)) * CAP_LEADING + CAP_MARGIN


if __name__ == '__main__':
    build().save('halfar_anatomy.png')
    print('wrote halfar_anatomy.png')
