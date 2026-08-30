"""Flow-routing ANATOMY — the figure for `03`'s central choice: D8, MFD, or the hybrid.

WHY THIS CHAPTER NEEDED A FIGURE AND HAD NONE. `03` is the routing spine, and its two load-bearing
claims are about SHAPE, which is the one thing prose cannot deliver:

  - **D8's parallel-lines artefact.** A single receiver per cell means every flow path is one of
    eight directions, so on a smooth slope the paths do not braid or wander -- they run in stripes
    at the lattice angles and print straight into anything driven by drainage area.
  - **MFD's mirror weakness.** Splitting to every lower neighbour means flow never fully
    converges, so channels "stay diffuse and rivers look like broad damp smears rather than lines".

You can write both sentences. You cannot make a reader SEE that they are opposite failures of the
same quantity until the two accumulations sit side by side, and that is what panels a and b do.

Panel c is the fix the chapter recommends -- MFD on the hillslope, D8 once `A` clears a
channelisation threshold -- and panel d stops the whole thing being an opinion: it sweeps the
relief and plots the concentration statistic for both routers, so "concentrated" and "smeared"
become a curve rather than two adjectives. (The FIRST measurement tried was a transect width; it
returned the claim backwards. `half_drainage_cells` records why.)

⚠️ TWO STATISTICS, BECAUSE ONE CANNOT SEE A HYBRID. `half_drainage_cells` is dominated by the
trunk, which is exactly where the hybrid runs D8 -- so it scores the hybrid as D8 and reports no
difference. `hillslope_wetted` covers the other half: the share of cells receiving anything from
upslope, where the hybrid scores as MFD. Both are drawn, because the pair IS the claim.

⚠️ WHAT THIS FIGURE DELIBERATELY DOES NOT DRAW. `03` also derives Quinn's contour-length weighting
(`w = L·s`, `L = 0.354·cellSize` diagonal against `0.5·cellSize` cardinal) and notes that dropping
`L` over-weights diagonals by ~40%. `flow.py` ships FREEMAN's form (`slope^p`, the diagonal
correction inside the slope), not Quinn's, so drawing that panel would be illustrating pseudocode
this skill does not run -- an illustration, not evidence. The house rule is that a figure is drawn
from the implementation, and the rule is worth more than the panel.

The numpy half carries no Pillow dependency, so `tests/test_flow_anatomy.py` imports the
measurements from here and guards exactly what the figure draws. Writes `flow_anatomy.png`.
Run: `python flow_anatomy.py`.
"""
import numpy as np

import flow
import noise

SEED = 0
N = 160
CELLSIZE = 30.0

# The channelisation threshold for the hybrid, in cells of contributing area. `03` gives the rule
# ("D8 or D-infinity where A exceeds a channelisation threshold") and not the number, so it is a
# parameter here rather than a constant, and the figure states the value it drew with.
CHANNEL_CELLS = 60.0


# --------------------------------------------------------------------------- #
# the terrain and the three routings (numpy only -- importable without Pillow)

def terrain(n=N, seed=SEED):
    """A ramped fBm basin: a regional slope with texture on it.

    THE RAMP IS THE POINT. On pure fBm both routings look busy and neither artefact is legible;
    it is a smooth regional gradient that makes D8's eight-direction quantisation visible as
    stripes, which is exactly the situation a real terrain generator is in after tectonic uplift.
    """
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    f = noise.fbm(xx / n * 4.0, yy / n * 4.0, seed, octaves=6, base=noise.perlin)
    ramp = (n - yy) / n                     # drains toward +y
    h = 200.0 * ramp + 28.0 * f
    return flow.priority_flood_fill(h)


def routings(dem, cellsize=CELLSIZE, channel_cells=CHANNEL_CELLS):
    """The three accumulations the chapter contrasts, from the shipped routers.

    ⚠️ PANEL C USED TO BE A SPLICE, AND A SPLICE IS NOT A ROUTING. The first version read

        hybrid = np.where(d8 >= channel_cells * cellarea, d8, mfd)

    -- run both routers to completion, then pick a value per cell. It looks like the chapter's
    rule and it is not: accumulation is CUMULATIVE, so choosing between two finished totals
    invents water at every boundary where the chosen field is the larger one. Measured against
    the domain total (D8 = 1.000 by construction), the splice summed to **1.583** -- 58% of the
    drainage conjured by the compositing step itself. It also cannot be what `03` describes,
    because the chapter's rule switches on the accumulation being built, which a finished field
    no longer has.

    A hybrid has to be ONE pass: walk the cells in the routing order once, and at each cell
    decide from the area accumulated SO FAR whether to split MFD-style or send everything to the
    steepest neighbour. That is `flow.hybrid_accumulation`, and it sums to 1.018 -- the small
    excess is MFD's genuine dispersion off the domain edge, the same effect that puts pure MFD at
    1.109, not a compositing artefact.
    """
    d8 = flow.d8_accumulation(dem, cellsize)
    mfd = flow.mfd_accumulation(dem, cellsize)
    hybrid = flow.hybrid_accumulation(dem, cellsize, channel_cells=channel_cells)
    return d8, mfd, hybrid


def half_drainage_cells(acc):
    """How many cells it takes to carry half the total drainage.

    THE MEASUREMENT THAT TURNS TWO ADJECTIVES INTO A NUMBER, and the second one tried. The first
    counted cells above half the peak on one row; on a distribution this skewed almost nothing
    clears that bar, so it returned 2 cells for D8 against 1 for MFD -- the claim BACKWARDS, in a
    figure whose whole purpose is that claim. A width at a fraction of a peak measures the peak,
    not the spread.

    Sorting the field and walking down to half the total measures what "converged" actually means:
    a routing that concentrates puts half the water in few cells, one that disperses needs many.
    It is a Lorenz-style concentration statistic, it has no threshold to tune, and it moves in the
    direction the chapter claims.
    """
    a = np.sort(np.asarray(acc, float).ravel())[::-1]
    c = np.cumsum(a)
    return int(np.searchsorted(c, 0.5 * c[-1]) + 1)


def lorenz(acc, points=220):
    """Cumulative share of drainage against share of cells, richest first."""
    a = np.sort(np.asarray(acc, float).ravel())[::-1]
    c = np.cumsum(a) / a.sum()
    idx = np.unique(np.linspace(0, c.size - 1, points).astype(int))
    return idx / float(c.size - 1), c[idx]


def relief_sweep(amps=(4.0, 8.0, 12.0, 18.0, 28.0, 40.0), n=120, cellsize=CELLSIZE):
    """Concentration against relief, for both routers.

    ⚠️ THE CROSSOVER AT LOW RELIEF IS A REAL RESULT, NOT NOISE, and it is the reason this sweep is
    in the figure rather than a single pair of numbers. At ordinary relief D8 concentrates far
    harder than MFD, exactly as `03` says. Below a few metres of texture on a regional ramp the
    order REVERSES: with almost nothing to steer them, D8's paths run as parallel stripes at the
    lattice angles and never merge, so the routing that is supposed to converge stops converging.
    The stripe artefact and the concentration statistic are the same phenomenon seen two ways.
    """
    out = []
    for amp in amps:
        yy, xx = np.mgrid[0:n, 0:n].astype(float)
        f = noise.fbm(xx / n * 4.0, yy / n * 4.0, SEED, octaves=6, base=noise.perlin)
        dem = flow.priority_flood_fill(200.0 * (n - yy) / n + amp * f)
        d8 = flow.d8_accumulation(dem, cellsize)
        mfd = flow.mfd_accumulation(dem, cellsize)
        tot = float(n * n)
        out.append((amp, half_drainage_cells(d8) / tot,
                    half_drainage_cells(mfd) / tot))
    return out


def diagonal_share(dem):
    """Fraction of D8 receivers that leave along a diagonal.

    A NUMBER THAT SAYS "QUANTISED" WITHOUT LOOKING AT THE PICTURE. Steepest descent corrects for
    the diagonal's longer step, so a router that is not biased by the lattice lands near a half.
    It is reported rather than asserted to be any particular value.

    ⚠️ `d8_receivers` RETURNS `(rec, slope)` WITH `rec[i, j] = (ri, rj)` -- an (n, m, 2) array
    inside a 2-tuple, not two (n, m) arrays. Unpacking it as `ri, rj = ...` binds `ri` to the whole
    receiver array and `rj` to the slopes, which broadcasts into nonsense. It raised rather than
    returning a plausible fraction, which is the good failure.
    """
    dem = np.asarray(dem, float)
    rec, _slope = flow.d8_receivers(dem, 1.0)
    ri, rj = rec[..., 0], rec[..., 1]
    n, m = dem.shape
    ii, jj = np.mgrid[0:n, 0:m]
    moved = (ri >= 0) & (rj >= 0) & ((ri != ii) | (rj != jj))
    diag = (np.abs(ri - ii) == 1) & (np.abs(rj - jj) == 1) & moved
    return float(diag.sum()) / float(max(moved.sum(), 1))


def hillslope_wetted(acc, cellsize=CELLSIZE):
    """Share of cells receiving ANY water from upslope — the hillslope half of the claim.

    ⚠️ THIS EXISTS BECAUSE `half_drainage_cells` IS STRUCTURALLY BLIND TO IT. The concentration
    statistic is dominated by the trunk, since that is where the water is; the hybrid runs D8 in
    the trunk by construction, so it scores as D8 (1.48% against 1.47%) and the statistic reports
    "no difference". The difference is real and lives on the hillslope, where the hybrid runs MFD
    and D8 leaves a quarter of all cells carrying nothing but their own area.

    One statistic answering "is it D8?" with yes and another answering "is it MFD?" with yes is
    not a contradiction — it is what a hybrid IS, and it takes two statistics to show.
    """
    a = np.asarray(acc, float)
    return float((a > 1.001 * cellsize * cellsize).mean())


def measurements(dem=None):
    """Everything the figure prints, in one call the test can re-run."""
    dem = terrain() if dem is None else dem
    d8, mfd, hybrid = routings(dem)
    tot = float(dem.size)
    return {
        'd8_half': half_drainage_cells(d8),
        'mfd_half': half_drainage_cells(mfd),
        'hybrid_half': half_drainage_cells(hybrid),
        'd8_frac': half_drainage_cells(d8) / tot,
        'mfd_frac': half_drainage_cells(mfd) / tot,
        'hybrid_frac': half_drainage_cells(hybrid) / tot,
        'ratio': half_drainage_cells(mfd) / max(half_drainage_cells(d8), 1),
        'd8_wet': hillslope_wetted(d8),
        'mfd_wet': hillslope_wetted(mfd),
        'hybrid_wet': hillslope_wetted(hybrid),
        'diagonal_share': diagonal_share(dem),
    }


# --------------------------------------------------------------------------- #
# drawing
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                                          # pragma: no cover
    Image = None

PANEL_W, PANEL_H = 300, 380
COLS, ROWS = 4, 1
PAD, TOP = 26, 92

BG = (250, 249, 246)
INK = (28, 30, 36)
MUTED = (120, 122, 128)
RED = (176, 60, 36)
BLU = (38, 76, 158)
GRN = (26, 106, 68)


def _font(sz, bold=False):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'
              % ('-Bold' if bold else ''),):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def _log_image(acc, gamma=0.45):
    """Accumulation as a greyscale, log-compressed.

    ⚠️ LOG, AND THE FIGURE SAYS SO. Drainage area spans four decades across one tile, so a linear
    ramp shows the trunk and nothing else -- both artefacts this figure exists to contrast live in
    the low decades. A compression that hides the subject is not a neutral choice.
    """
    a = np.log10(np.maximum(np.asarray(acc, float), 1e-9))
    a = (a - a.min()) / max(a.max() - a.min(), 1e-12)
    v = (255 * (1.0 - a ** gamma)).astype(np.uint8)
    return Image.fromarray(np.dstack([v, v, v]), 'RGB')


def build():
    if Image is None:                                        # pragma: no cover
        raise SystemExit('flow_anatomy needs Pillow:  pip install pillow')
    dem = terrain()
    d8, mfd, hybrid = routings(dem)
    m = measurements(dem)
    sweep = relief_sweep()
    # The crossing, found from the data rather than eyeballed. Hoisted above the canvas
    # because the caption quotes it and the canvas is now sized FROM the caption.
    cross = next((a for (a, x, y) in sweep if x < y), None)

    W = PAD * 2 + COLS * PANEL_W
    # ⚠️ Sized from the caption it actually has, not from a hand-tuned constant. The sibling
    # figure `halfar_anatomy.py` shipped with `+ 196` here, the caption outgrew it, and the
    # last line — the one carrying the result — was silently clipped off the canvas.
    caption = caption_lines(m, cross)
    H = CAP_TOP + len(caption) * CAP_LEADING + CAP_MARGIN
    img = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(img)
    f_t, f_h, f_s, f_b = _font(26, True), _font(15, True), _font(13), _font(13, True)

    d.text((PAD, 22), 'Flow routing — one quantity, two opposite failures', INK, font=f_t)
    d.text((PAD, 54), 'chapter 03 · %d×%d cells at %.0f m · %d-cell sweep · drawn from flow.py'
           % (N, N, CELLSIZE, 120), MUTED, font=f_s)

    side = PANEL_W - 34
    panels = [
        ('a.  D8 — one receiver', d8, RED, 'converges hard; stripes at the lattice angles',
         'half in %.1f%% of cells · %.1f%% wetted'
         % (100 * m['d8_frac'], 100 * m['d8_wet'])),
        ('b.  MFD — every lower neighbour', mfd, BLU, 'never fully converges',
         'half in %.1f%% — %.1f× · %.1f%% wetted'
         % (100 * m['mfd_frac'], m['ratio'], 100 * m['mfd_wet'])),
        ('c.  hybrid — MFD, D8 past A', hybrid, GRN,
         'threshold %.0f cells · ONE pass, not a splice' % CHANNEL_CELLS,
         'half in %.1f%% like D8 · %.1f%% wetted like MFD'
         % (100 * m['hybrid_frac'], 100 * m['hybrid_wet'])),
    ]
    for k, (title, acc, col, sub, meas) in enumerate(panels):
        x0 = PAD + k * PANEL_W
        d.text((x0, TOP - 26), title, col, font=f_h)
        img.paste(_log_image(acc).resize((side, side), Image.NEAREST), (x0, TOP))
        d.rectangle([x0, TOP, x0 + side, TOP + side], outline=MUTED)
        d.text((x0, TOP + side + 8), sub, MUTED, font=f_s)
        d.text((x0, TOP + side + 26), meas, col, font=f_b)

    # --- panel d: concentration against relief, where the order reverses ------
    x0 = PAD + 3 * PANEL_W
    d.text((x0, TOP - 26), 'd.  and it reverses at low relief', INK, font=f_h)
    ax = (x0 + 30, TOP, x0 + side, TOP + side - 22)
    d.rectangle(list(ax), outline=MUTED)
    amps = [a for a, _, _ in sweep]
    lo_a, hi_a = min(amps), max(amps)
    ys = [v for _, a, b in sweep for v in (a, b)]
    lo_y, hi_y = 0.0, max(ys) * 1.10

    def px(a):
        return ax[0] + (a - lo_a) / (hi_a - lo_a) * (ax[2] - ax[0])

    def py(v):
        return ax[3] - (v - lo_y) / (hi_y - lo_y) * (ax[3] - ax[1])

    for tick in (0.0, 0.1, 0.2, 0.3):
        if tick <= hi_y:
            d.line([ax[0], py(tick), ax[2], py(tick)], fill=(222, 220, 214))
            d.text((ax[0] - 6, py(tick)), '%d%%' % int(tick * 100), MUTED,
                   font=f_s, anchor='rm')
    for idx, (name, col) in enumerate((('D8', RED), ('MFD', BLU))):
        pts = [(px(a), py(v[idx])) for a, *v in sweep]
        d.line([c for p in pts for c in p], fill=col, width=3)
        for p in pts:
            d.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=col)
        d.text((pts[-1][0] - 4, pts[-1][1] - 16), name, col, font=f_b, anchor='rs')
    if cross is not None:
        d.line([px(cross), ax[1], px(cross), ax[3]], fill=(150, 60, 130), width=1)
        d.text((px(cross) + 4, ax[1] + 4), 'D8 wins above here', (150, 60, 130),
               font=f_s)
    for a in (lo_a, 12.0, 28.0, hi_a):
        d.line([px(a), ax[3], px(a), ax[3] + 4], fill=MUTED)
        d.text((px(a), ax[3] + 6), '%.0f' % a, MUTED, font=f_s, anchor='ma')
    d.text((ax[0], ax[3] + 22), 'fBm relief on the ramp, m', MUTED, font=f_s)
    d.text((ax[0], ax[3] + 38), 'y: share of cells carrying half the drainage',
           MUTED, font=f_s)
    # The y meaning lives under the axis, not above it: at TOP it landed on the
    # frame and the 30 % tick, which is the one place a label must not be.
    d.text((x0 + 30, TOP + side + 42), 'below ~%.0f m the order reverses'
           % (cross if cross else 0), INK, font=f_b)

    for i, line in enumerate(caption):
        d.text((PAD, CAP_TOP + i * CAP_LEADING), line, INK if i == 0 else MUTED, font=f_s)
    return img


CAP_TOP = TOP + PANEL_H + 10
CAP_LEADING = 17
CAP_MARGIN = 20


def caption_lines(m, cross):
    """The caption, as a list, so `build` can size the canvas from it."""
    return [
        'D8 AND MFD FAIL IN OPPOSITE DIRECTIONS ON THE SAME QUANTITY, which is why `03` recommends neither alone. D8 gives every cell a single',
        'receiver, so flow can only leave in one of eight directions; it converges hard — %.1f%% of cells carry half the drainage — and prints stripes'
        % (100 * m['d8_frac']),
        'at the lattice angles into anything driven by drainage area. MFD splits to every lower neighbour, so it never fully converges and needs',
        '%.1f× as many cells for the same half. The hybrid in c runs MFD on the hillslope and switches to D8 past a channelisation threshold —'
        % m['ratio'],
        'in ONE pass, deciding from the area accumulated so far. ⚠️ It is NOT `where(A > threshold, d8, mfd)`: picking between two FINISHED',
        'accumulations invents water at every boundary, and that splice — which this panel used to draw — summed to 1.58× the domain\'s drainage.',
        '⚠️ AND IT TAKES TWO STATISTICS TO SEE A HYBRID. The concentration number is dominated by the trunk, where the hybrid is D8 by',
        'construction, so it reports %.1f%% against D8\'s %.1f%% — no difference. The difference is on the hillslope: %.1f%% of cells receive water'
        % (100 * m['hybrid_frac'], 100 * m['d8_frac'], 100 * m['hybrid_wet']),
        'from upslope under the hybrid and %.1f%% under MFD, against only %.1f%% under D8. Answering "is it D8?" yes and "is it MFD?" yes is not a'
        % (100 * m['mfd_wet'], 100 * m['d8_wet']),
        'contradiction — it is what a hybrid is, and one statistic could not have shown it.',
        'Panel d is the part prose keeps missing: sweep the relief and the order REVERSES below about %.0f m, because with almost nothing to steer'
        % (cross if cross else 0),
        'them D8\'s parallel paths never merge — the stripe artefact and the concentration statistic are the same phenomenon seen twice.',
        '%.0f%% of D8 receivers leave diagonally here. Drawn from flow.py — the shipped routers — and guarded by tests/test_flow_anatomy.py.'
        % (100.0 * m['diagonal_share']),
    ]


if __name__ == '__main__':
    build().save('flow_anatomy.png')
    print('wrote flow_anatomy.png')
