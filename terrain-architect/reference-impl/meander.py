"""Lateral fluvial migration — meandering & bank erosion (03-flow-routing.md).

A river does NOT erode its banks with waves; it migrates by FLOW CURVATURE. The outer, concave
bank of a bend is the cut bank (erosion); the inner, convex bank is the point bar (deposition).
Meandering lives at the low-slope end of the channel spectrum — on the floodplain, after the
valley exists — and it runs on a CENTRELINE representation (a polyline): an agent model (07), NOT
a per-cell height-field sim. The height field is edited only at the end (`burn_channel` / point
bars); the migration physics never touches `h`.

The physics is P-tier. Near-bank excess velocity depends on UPSTREAM curvature, exponentially
lagged (Ikeda, Parker & Sawai 1981; Howard & Knutson 1984) — NOT on local curvature alone. Local
curvature alone grows symmetric, stationary bends; the exponential upstream lag is the whole thing
— it skews meanders downstream and lets them sharpen and overturn (the characteristic look). Drop
it and you get sine waves, not meanders. The terrain realisation (burning the channel, point bars,
oxbow scars) is the honest F-tier "look" layered on top.

Pseudocode ↔ code map (chapter 03):
    meanderStep       -> migrate
    curvature         -> curvature
    u_b upstream lag   -> near_bank_velocity
    neck cutoff/oxbow  -> _neck_cutoff  (migrate returns the abandoned arcs)
    burnChannel        -> burn_channel  (sdPolyline -> sd_polyline)
    depositPointBars   -> deposit_point_bars

Convention: signed curvature C>0 is a LEFT turn (toward the +N left normal N=(-Ty,Tx)); the centre
of curvature is then on the +N side and the outer/cut bank on -N, so migration is -E*u_b*N (toward
the outer bank), which grows the bend. Coordinates are world metres; a cell (row, col) maps to
world (x, y) = origin + (col, row)*cellsize.
"""
import numpy as np

import ops_filters


def _smoothstep(lo, hi, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - lo) / (hi - lo + 1e-30), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------- #
# Centreline geometry
# --------------------------------------------------------------------------- #
def resample(centreline, ds):
    """Reparameterise the polyline to ~uniform node spacing `ds` by arc length (keeps the two
    endpoints). Called every step so migration can't bunch or thin the nodes (03: `resample`)."""
    p = np.asarray(centreline, dtype=np.float64)
    seg = np.diff(p, axis=0)
    seglen = np.hypot(seg[:, 0], seg[:, 1])
    s = np.concatenate([[0.0], np.cumsum(seglen)])            # arc length at each node
    total = float(s[-1])
    if total < ds:                                            # too short to resample meaningfully
        return p.copy()
    n_new = max(int(round(total / ds)) + 1, 2)
    s_new = np.linspace(0.0, total, n_new)
    return np.column_stack([np.interp(s_new, s, p[:, 0]),
                            np.interp(s_new, s, p[:, 1])])


def _frame(p):
    """Unit downstream tangent T and left normal N=(-Ty,Tx) per node (central differences)."""
    d = np.gradient(p, axis=0)                                # central diff; one-sided at the ends
    t = d / (np.hypot(d[:, 0], d[:, 1])[:, None] + 1e-30)
    n = np.column_stack([-t[:, 1], t[:, 0]])
    return t, n


def curvature(centreline):
    """Signed discrete curvature per node (1/radius). >0 = left turn (toward +N). Menger curvature
    κ = 2·cross(v1,v2)/(|v1||v2||chord|) with the sign of the turning cross-product (03: `C[i]`).
    Endpoints get 0 (they are the pinned inflow/outflow)."""
    p = np.asarray(centreline, dtype=np.float64)
    C = np.zeros(len(p))
    if len(p) < 3:
        return C
    v1 = p[1:-1] - p[:-2]
    v2 = p[2:] - p[1:-1]
    cross = v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0]
    l1 = np.hypot(v1[:, 0], v1[:, 1])
    l2 = np.hypot(v2[:, 0], v2[:, 1])
    chord = np.hypot(p[2:, 0] - p[:-2, 0], p[2:, 1] - p[:-2, 1])
    C[1:-1] = 2.0 * cross / (l1 * l2 * chord + 1e-30)
    return C


def near_bank_velocity(C, ds, L_adj):
    """Upstream-lagged near-bank excess velocity (Ikeda, Parker & Sawai 1981; 03):

        u_b[i] = Σ_{k≥0} C[i-k] · exp(-k·ds / L_adj)

    computed as the causal exponential (IIR) filter u[i] = C[i] + α·u[i-1] with α = exp(-ds/L_adj),
    which equals that sum exactly. Normalised by (1-α) so the DC gain is 1 (u_b of a constant-
    curvature arc equals that curvature). The exponential lag over L_adj (≈ several channel widths)
    is what puts the migration peak DOWNSTREAM of the curvature peak — the whole reason meanders
    skew and overturn instead of standing still as sine waves."""
    C = np.asarray(C, dtype=np.float64)
    alpha = float(np.exp(-ds / max(L_adj, 1e-9)))
    u = np.empty_like(C)
    acc = 0.0
    for i in range(len(C)):                                   # causal: accumulate downstream
        acc = C[i] + alpha * acc
        u[i] = acc
    return u * (1.0 - alpha)


def sinuosity(centreline):
    """Path length / straight-line end-to-end distance (≥1; higher = more meandering)."""
    p = np.asarray(centreline, dtype=np.float64)
    seg = np.diff(p, axis=0)
    path = float(np.hypot(seg[:, 0], seg[:, 1]).sum())
    ends = float(np.hypot(*(p[-1] - p[0])))
    return path / (ends + 1e-30)


# --------------------------------------------------------------------------- #
# Neck cutoff -> oxbow
# --------------------------------------------------------------------------- #
def _neck_cutoff(p, cutoff_dist, min_sep):
    """Short-circuit any loop whose neck has narrowed below `cutoff_dist`; the abandoned arc becomes
    an oxbow (03: neck cutoff). Only non-adjacent pairs — index-separated by ≥ `min_sep` nodes — so a
    straight reach's neighbours don't trivially 'cut off'. Returns (spliced_centreline, [oxbow_arc…])."""
    p = np.asarray(p, dtype=np.float64)
    oxbows = []
    while len(p) > 2 * min_sep:
        n = len(p)
        diff = p[:, None, :] - p[None, :, :]                  # pairwise separations
        dist = np.hypot(diff[..., 0], diff[..., 1])
        ii, jj = np.indices((n, n))
        mask = (jj - ii >= min_sep) & (dist < cutoff_dist)    # non-adjacent, neck below cutoff
        if not mask.any():
            break
        cand = np.argwhere(mask)                              # pick smallest i, then smallest j
        i, j = cand[np.lexsort((cand[:, 1], cand[:, 0]))[0]]
        oxbows.append(p[i:j + 1].copy())                      # the abandoned loop
        p = np.vstack([p[:i + 1], p[j:]])                     # river short-circuits across the neck
    return p, oxbows


# --------------------------------------------------------------------------- #
# The step (meanderStep)
# --------------------------------------------------------------------------- #
def migrate(centreline, *, steps=1, dt=1.0, ds=1.0, L_adj=8.0, E=0.02,
            cutoff_dist=None, min_sep=8, pin_ends=True, collect_oxbows=True):
    """Evolve a centreline by `steps` iterations of meanderStep (03). Deterministic (no RNG).
    Returns (centreline, oxbows) where oxbows is the list of abandoned arcs from neck cutoffs.

    dt           time step; E·dt·u_b is the migration distance per step (keep ≪ ds for stability)
    ds           target node spacing (the line is resampled to this each step)
    L_adj        adjustment length for the upstream lag (≈ several channel widths)
    E            bank erodibility
    cutoff_dist  neck-cutoff threshold; default 2·ds
    min_sep      channel-index separation a pair needs before it can cut off
    pin_ends     hold the two endpoints fixed (inflow/outflow) — else the belt walks off-grid
    """
    p = resample(np.asarray(centreline, dtype=np.float64), ds)
    if cutoff_dist is None:
        cutoff_dist = 2.0 * ds
    oxbows = []
    for _ in range(int(steps)):
        p = resample(p, ds)
        C = curvature(p)
        u_b = near_bank_velocity(C, ds, L_adj)
        _, N = _frame(p)
        # Migrate toward the OUTER (cut) bank: for a left turn (C>0) the outer bank is on the -N
        # side, so disp = -E·u_b·dt·N moves the channel outward and amplifies the bend.
        disp = (-E * dt) * u_b[:, None] * N
        if pin_ends:
            disp[0] = 0.0
            disp[-1] = 0.0
        p = p + disp
        p, cut = _neck_cutoff(p, cutoff_dist, min_sep)
        if collect_oxbows:
            oxbows.extend(cut)
    return p, oxbows


# --------------------------------------------------------------------------- #
# Height-field realisation (F-tier look): burnChannel + point bars
# --------------------------------------------------------------------------- #
def sd_polyline(px, py, centreline):
    """Distance from each point to the polyline = min over segments (sd_segment, 10). Used by
    `burn_channel` as `sdPolyline`."""
    p = np.asarray(centreline, dtype=np.float64)
    d = np.full(np.shape(px), np.inf)
    for a, b in zip(p[:-1], p[1:]):
        d = np.minimum(d, ops_filters.sd_segment(px, py, a[0], a[1], b[0], b[1]))
    return d


def _project_polyline(px, py, p):
    """Per point: (distance to polyline, arc-length s* of the nearest point, nearest x, nearest y).
    s* is what `thalwegElev` is interpolated against so the bed slopes downstream, not undulating."""
    seg = np.diff(p, axis=0)
    seglen = np.hypot(seg[:, 0], seg[:, 1])
    s0 = np.concatenate([[0.0], np.cumsum(seglen)])           # arc length at each segment start
    shape = np.broadcast(px, py).shape
    best_d = np.full(shape, np.inf)
    best_s = np.zeros(shape)
    best_x = np.zeros(shape)
    best_y = np.zeros(shape)
    for k in range(len(seg)):
        ax, ay = p[k]
        bax, bay = seg[k]
        h = np.clip(((px - ax) * bax + (py - ay) * bay) / (bax * bax + bay * bay + 1e-30), 0.0, 1.0)
        cx, cy = ax + bax * h, ay + bay * h
        d = np.hypot(px - cx, py - cy)
        take = d < best_d
        best_d = np.where(take, d, best_d)
        best_s = np.where(take, s0[k] + h * seglen[k], best_s)
        best_x = np.where(take, cx, best_x)
        best_y = np.where(take, cy, best_y)
    return best_d, best_s, best_x, best_y


def _world_grid(shape, cellsize, origin):
    ox, oy = origin
    xs = ox + np.arange(shape[1]) * cellsize
    ys = oy + np.arange(shape[0]) * cellsize
    return np.meshgrid(xs, ys)                                # (px, py), each (nrow, ncol)


def _node_arclength(p):
    seg = np.diff(p, axis=0)
    return np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])


def _sample(h, xy, cellsize, origin):
    col = (xy[0] - origin[0]) / cellsize
    row = (xy[1] - origin[1]) / cellsize
    r = int(np.clip(round(row), 0, h.shape[0] - 1))
    c = int(np.clip(round(col), 0, h.shape[1] - 1))
    return float(h[r, c])


def burn_channel(h, centreline, *, half_width, depth, bank_width, cellsize=1.0,
                 thalweg_elev=None, origin=(0.0, 0.0)):
    """Carve the channel into the height field (03: `burnChannel`). The cross-section is a function
    of the SDF (so it has a shape, not a stamped groove); the bed elevation is the long profile,
    ARC-LENGTH interpolated (so it slopes downstream, no pools); the bank is feathered (no hard rim);
    and it is CARVE-ONLY — `h` is only ever lowered, never raised. Returns a new height field.

        d   = sdPolyline(p)                          # ≥0 metres from the centreline
        t   = clamp(d / halfWidth, 0, 1)
        bed = thalwegElev(p) + depth · t²            # parabola
        w   = 1 - smoothstep(halfWidth, halfWidth+bankWidth, d)
        h  -= w · max(0, h - bed)

    `thalweg_elev` is the per-node bed elevation; default = the surface sampled at the two endpoints,
    linear in arc length, minus `depth` (a clean channel of relief `depth` that slopes downstream)."""
    h = np.asarray(h, dtype=np.float64).copy()
    p = np.asarray(centreline, dtype=np.float64)
    px, py = _world_grid(h.shape, cellsize, origin)
    d, s_star, _, _ = _project_polyline(px, py, p)
    node_s = _node_arclength(p)
    if thalweg_elev is None:
        z0 = _sample(h, p[0], cellsize, origin) - depth
        z1 = _sample(h, p[-1], cellsize, origin) - depth
        thalweg_elev = z0 + (z1 - z0) * (node_s / max(node_s[-1], 1e-9))
    z_bed = np.interp(s_star, node_s, np.asarray(thalweg_elev, dtype=np.float64))
    t = np.clip(d / half_width, 0.0, 1.0)
    bed = z_bed + depth * t * t
    w = 1.0 - _smoothstep(half_width, half_width + bank_width, d)
    return h - w * np.maximum(0.0, h - bed)


def deposit_point_bars(h, centreline, *, half_width, bar_height, bank_width, cellsize=1.0,
                       origin=(0.0, 0.0)):
    """Raise the inner (convex) bank of each bend — the point bar (03: `depositPointBars`; F-tier
    look). The inner bank is the +N (centre-of-curvature) side where C>0, so a cell is on the inner
    bank when sign((cell-nearest)·N) == sign(C). Aggradation scales with |C| (sharper bends build
    bigger bars).

    The deposition band is concentrated on the CONVEX BANK — zero in the thalweg, rising to a peak at
    the bank and fading into the floodplain — so it reads as the scroll-bar ridge and, critically,
    SURVIVES if the active channel is carved through the same corridor. Call AFTER `burn_channel` (the
    cut-bank-erodes / point-bar-deposits pair): burning first eats a bar laid inside the wetted channel,
    which is why the belt used to read as carve-only. Returns a new height field."""
    h = np.asarray(h, dtype=np.float64).copy()
    p = np.asarray(centreline, dtype=np.float64)
    C = curvature(p)
    _, N = _frame(p)
    node_s = _node_arclength(p)
    px, py = _world_grid(h.shape, cellsize, origin)
    d, s_star, cx, cy = _project_polyline(px, py, p)
    Ci = np.interp(s_star, node_s, C)
    Nx = np.interp(s_star, node_s, N[:, 0])
    Ny = np.interp(s_star, node_s, N[:, 1])
    side = np.sign((px - cx) * Nx + (py - cy) * Ny)           # +1 on the +N (centre) side
    inner = side == np.sign(Ci)
    cref = float(np.percentile(np.abs(C), 90)) + 1e-9
    # bump centred on the convex bank: 0 at the thalweg -> 1 near d=half_width -> 0 in the floodplain
    band = (_smoothstep(0.25 * half_width, half_width, d)
            * (1.0 - _smoothstep(half_width, half_width + bank_width, d)))
    amt = bar_height * np.clip(np.abs(Ci) / cref, 0.0, 1.5) * band
    return h + np.where(inner & (d < half_width + bank_width), amt, 0.0)


# --------------------------------------------------------------------------- #
# Composite node: the whole meander belt in one call
# --------------------------------------------------------------------------- #
def seed_wave(shape, cellsize, *, origin=(0.0, 0.0), amp_frac=0.031, wavelength_frac=0.19,
              overhang_frac=0.22, n=240, y_frac=0.5):
    """A convenient default centreline for `meander_belt`: a low-amplitude sinusoid running left→right
    across the grid that extends OFF both ends (so the pinned inflow/outflow coil off-frame) and TAPERS
    to straight ends (zero curvature, no coiling in view). Migration amplifies it into the belt. Returns
    an (n, 2) polyline in world metres."""
    nrow, ncol = shape
    W = ncol * cellsize
    ox, oy = origin
    ycen = oy + y_frac * nrow * cellsize
    x0, x1 = ox - overhang_frac * W, ox + (1.0 + overhang_frac) * W
    xs = np.linspace(x0, x1, n)
    lam = wavelength_frac * W
    win = _smoothstep(x0, ox + 0.11 * W, xs) * (1.0 - _smoothstep(ox + 0.89 * W, x1, xs))
    ys = ycen + win * (amp_frac * W * np.sin(2.0 * np.pi * (xs - ox) / lam)
                       + 0.32 * amp_frac * W * np.sin(2.0 * np.pi * (xs - ox) / (0.58 * lam) + 0.6))
    return np.column_stack([xs, ys])


def meander_belt(h, centreline=None, *, cellsize=1.0, origin=(0.0, 0.0),
                 steps=300, dt=1.0, ds=6.0, L_adj=40.0, E=16.0, cutoff_dist=None, min_sep=10,
                 half_width=10.0, depth=7.5, bank_width=16.0,
                 bar_height=3.5, bar_bank_width=14.0, oxbow_depth=5.0, deposit=True):
    """Composite **meander-belt node** (chapter 03) — the building block a composite/archetype drops in
    for a floodplain river. A MACRO over the meander atoms: migrate the centreline (P-tier upstream-lag
    physics), then realise it into the height field (F-tier look) — carve the active channel, drop each
    abandoned loop as an **oxbow lake**, and (deposit=True) build **point/scroll bars** on the inner
    banks. Because the bars go on AFTER the carve and sit on the convex bank, the belt shows the full
    cut-bank-erodes / point-bar-deposits asymmetry, not just an incised groove.

    `centreline` defaults to `seed_wave(h.shape, cellsize, origin=origin)`. Returns a dict:
        height     : the edited height field
        water      : bool mask of open water (active channel + oxbow lakes)
        channel    : bool mask of the active channel
        oxbows     : list of abandoned-arc centrelines (the oxbow lakes)
        centreline : the final migrated centreline
    """
    h = np.asarray(h, dtype=np.float64).copy()
    if centreline is None:
        centreline = seed_wave(h.shape, cellsize, origin=origin)
    belt, oxbows = migrate(centreline, steps=steps, dt=dt, ds=ds, L_adj=L_adj, E=E,
                           cutoff_dist=cutoff_dist, min_sep=min_sep)
    h = burn_channel(h, belt, half_width=half_width, depth=depth, bank_width=bank_width,
                     cellsize=cellsize, origin=origin)
    for a in oxbows:                                          # abandoned arcs -> shallow oxbow lakes
        if len(a) >= 2:
            h = burn_channel(h, a, half_width=half_width * 0.7, depth=oxbow_depth,
                             bank_width=bank_width * 0.7, cellsize=cellsize, origin=origin)
    if deposit:                                               # point/scroll bars AFTER the carve
        h = deposit_point_bars(h, belt, half_width=half_width, bar_height=bar_height,
                               bank_width=bar_bank_width, cellsize=cellsize, origin=origin)
    gx, gy = _world_grid(h.shape, cellsize, origin)
    channel = sd_polyline(gx, gy, belt) < half_width * 1.1
    water = channel.copy()
    for a in oxbows:
        if len(a) >= 2:
            water = water | (sd_polyline(gx, gy, a) < half_width * 0.8)
    return {"height": h, "water": water, "channel": channel,
            "oxbows": oxbows, "centreline": belt}
