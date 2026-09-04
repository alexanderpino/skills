"""The terrain-aware wind FLOW FIELD (13-climate-ecosystem.md).

Wind is a vector field over the grid — a per-cell SPEED and DIRECTION, not a global constant —
because every consumer (dunes `05`, orographic precipitation `13`, snow drift and cornices `13`,
wave fetch `12`, fire spread `13`) reads it locally. `wind_field` is the chapter's four-step
`windField` recipe end to end:

    1. terrain_speedup   crest / windward speed-up          Jackson & Hunt 1975
    2. lee_shelter       lee shadow zone slows the flow      Werner's dune shadow at hill scale (05)
    3. valley_channel    direction rotates to the valley axis where relief confines the flow
    4. mass_consistent   project onto a divergence-free field   Sherman 1978 (MATHEW)

Steps 1-3 (`terrain_adjust`) are the F-tier "look": they make the field terrain-AWARE, and they are
what the constant vector every consumer used to take cannot do — a valley-floor dune field points
along the valley, not along the regional wind. Step 4 is the one with a closed form, below.

Convention: `(u, v)` are the (x/column, y/row) components, matching `dunes`, `snow` and `aeolian`,
and the domain is PERIODIC throughout (the same assumption the spectral solve makes).

Mass-consistent adjustment (Sherman 1978, MATHEW). Project a terrain-adjusted wind field onto a
divergence-free field by solving a Poisson equation for the scalar potential lambda (the
Helmholtz-Hodge projection): remove the curl-free (divergent) part so streamlines wrap terrain
instead of piling into it.

Solved spectrally (periodic BCs) with the SAME wavenumber grid as the isostasy flexure
solve. Using spectral derivatives throughout makes the projection exact: the corrected
field's (spectral) divergence is zero to machine precision — on ANY grid, because the
odd-order (first-derivative) i*k operator ZEROES the Nyquist mode. On an even-length axis the
Nyquist frequency is its own conjugate, so i*k*(Nyquist) has an imaginary part that np.real
silently drops; leaving it in place would let a real field carry a spurious residual divergence
at the grid scale. Zeroing it (the standard spectral-derivative rule) and using the SAME zeroed
wavenumbers for the Laplacian keeps the projection identity div_new = div - k^2*lambda exact.
"""
import numpy as np

import ops_filters


def _wavenumbers(shape, cellsize, zero_nyquist=False):
    """2-D angular wavenumber grids. `zero_nyquist` drops the Nyquist mode on each even-length
    axis — required for the ODD-order i*k derivative (div/grad); leave it False for the EVEN-order
    Laplacian k^2 (where the Nyquist term is real and well-defined)."""
    n, m = shape
    ky = 2.0 * np.pi * np.fft.fftfreq(n, d=cellsize)
    kx = 2.0 * np.pi * np.fft.fftfreq(m, d=cellsize)
    if zero_nyquist:
        if n % 2 == 0:
            ky[n // 2] = 0.0
        if m % 2 == 0:
            kx[m // 2] = 0.0
    KX, KY = np.meshgrid(kx, ky)
    return KX, KY


def _unit(u, v):
    mag = np.hypot(u, v) + 1e-30
    return u / mag, v / mag


def _smoothstep(lo, hi, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - lo) / (hi - lo + 1e-30), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def sample_bilinear(field, y, x):
    """Bilinear sample of `field` at fractional (row, col) coordinates, wrapping periodically —
    the sampler the upwind walks below need, since a wind direction is rarely axis-aligned."""
    field = np.asarray(field, dtype=np.float64)
    n, m = field.shape
    y0 = np.floor(y).astype(np.int64)
    x0 = np.floor(x).astype(np.int64)
    fy, fx = y - y0, x - x0
    y0, x0 = y0 % n, x0 % m
    y1, x1 = (y0 + 1) % n, (x0 + 1) % m
    return ((field[y0, x0] * (1.0 - fx) + field[y0, x1] * fx) * (1.0 - fy) +
            (field[y1, x0] * (1.0 - fx) + field[y1, x1] * fx) * fy)


def upwind_slope(h, base_dir, *, cellsize=1.0, fetch=12):
    """The hill aspect ratio H/L seen looking UPWIND from each cell — the SECANT slope over the
    whole fetch, (h[p] - h[p - fetch*dir]) / (fetch*cellsize): "how far have I climbed above the
    ground one fetch upwind".

    Not the one-cell along-wind gradient, and the difference is the whole point. A local gradient
    is largest at the windward INFLECTION and exactly zero at the CREST, so a gradient-driven
    speed-up puts the fastest wind halfway up the hill — while Jackson & Hunt's perturbation scales
    with the hill's H/L, a fetch-scale quantity that is largest at the crest, which is where
    anemometers, snow scour and flattened dune crests all say the wind actually peaks. Neither does
    a max over intermediate k work: that is >= the local gradient everywhere, so the inflection
    always wins.

    **`fetch` is a scale choice, and it must span the upwind hill** — `fetch * cellsize` greater
    than about twice the hill's half-length. Too short and the maximum slides back down onto the
    flank (the failure above, in a subtler form); much too long and the rise is divided by an
    over-long L, which merely UNDER-states the speed-up — the graceful direction, and the physically
    right answer for a low bump on a wide plain. Negative in the lee (a descent), which is why the
    caller clips at 0 and leaves the lee to `lee_shelter`."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    ux, uy = _unit(*base_dir)
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    k = float(fetch)
    up = sample_bilinear(h, yy - uy * k, xx - ux * k)
    return (h - up) / (k * cellsize)


def terrain_speedup(h, base_dir, *, cellsize=1.0, k_speedup=1.5, max_speedup=2.0, fetch=12):
    """Fractional speed-up over windward slopes and crests (Jackson & Hunt 1975): the perturbation
    scales with the hill's aspect ratio (delta_u/u ~ H/L) and PEAKS AT THE CREST. Returns a
    multiplier field in [1, max_speedup]; `k_speedup` ~ 1.5 gives the chapter's ~1.5-2x at steep
    crests. Lee slopes get no speed-up here — the slowdown is `lee_shelter`'s job, so the two
    multipliers stay separable."""
    return np.clip(1.0 + k_speedup * np.clip(upwind_slope(h, base_dir, cellsize=cellsize,
                                                          fetch=fetch), 0.0, None),
                   1.0, max_speedup)


def lee_shelter(h, base_dir, *, cellsize=1.0, shadow_tan=0.268, reach=12, shelter=0.35,
                blend_height=None):
    """Shelter multiplier in the lee of upwind obstacles — Werner's 15-degree dune shadow zone (`05`)
    applied at landscape scale. Walk `reach` cells UPWIND; a cell is sheltered when some upwind
    caster stands above the shadow line of slope `shadow_tan` drawn downwind from it. The chapter's
    test is binary; here the depth below that line is smoothstepped over `blend_height` so a
    landscape-scale field has no hard shelter edge (a binary cut prints the reach as a visible
    terrace). Returns a multiplier in [shelter, 1]."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    ux, uy = _unit(*base_dir)
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    excess = np.zeros_like(h)
    for k in range(1, int(reach) + 1):
        caster = sample_bilinear(h, yy - uy * k, xx - ux * k)          # k cells upwind
        excess = np.maximum(excess, caster - h - shadow_tan * k * cellsize)
    if blend_height is None:
        blend_height = 0.5 * shadow_tan * cellsize                     # sub-cell: nearly the hard test
    f = _smoothstep(0.0, blend_height, excess)                         # 0 = exposed, 1 = fully sheltered
    return 1.0 - f * (1.0 - shelter)


def terrain_axis(h, *, cellsize=1.0, relief_radius=8.0):
    """The local LINEAR AXIS of the terrain and how coherent it is, from the structure tensor
    J = smooth(grad h (x) grad h) of the terrain smoothed at `relief_radius`. Returns
    (ax, ay, coherence): the unit eigenvector of the SMALLER eigenvalue — the direction along which
    the height varies least, i.e. the valley's (or ridge's) long axis — and the anisotropy
    (l_max - l_min)/(l_max + l_min) in [0,1], which is ~1 in a straight canyon and ~0 in a circular
    basin or on a plain.

    Why not just the contour direction (perpendicular to grad h)? Because ON the valley floor the
    gradient vanishes by symmetry, so the contour direction is undefined exactly where channelling
    matters most — the flow would snap back to the regional wind along the thalweg. Averaging
    grad (x) grad over a neighbourhood is sign-blind (the two opposing walls reinforce instead of
    cancelling), so the tensor stays well-conditioned on the floor."""
    h = np.asarray(h, dtype=np.float64)
    sigma = max(relief_radius / 3.0, 0.5)
    hs = ops_filters.gaussian(h, sigma)
    gy, gx = np.gradient(hs, cellsize)
    jxx = ops_filters.gaussian(gx * gx, sigma)
    jyy = ops_filters.gaussian(gy * gy, sigma)
    jxy = ops_filters.gaussian(gx * gy, sigma)
    half = 0.5 * (jxx + jyy)
    root = np.sqrt(np.maximum((0.5 * (jxx - jyy)) ** 2 + jxy ** 2, 0.0))
    l_max, l_min = half + root, half - root
    # eigenvector of l_min; the two forms below degenerate on different cells, so take the longer
    ax1, ay1 = jxy, l_min - jxx
    ax2, ay2 = l_min - jyy, jxy
    use1 = (ax1 ** 2 + ay1 ** 2) >= (ax2 ** 2 + ay2 ** 2)
    ax = np.where(use1, ax1, ax2)
    ay = np.where(use1, ay1, ay2)
    mag = np.hypot(ax, ay)
    flat = mag < 1e-12                                                 # isotropic: no axis at all
    ax = np.where(flat, 1.0, ax / (mag + 1e-30))
    ay = np.where(flat, 0.0, ay / (mag + 1e-30))
    coherence = np.where(l_max > 1e-30, (l_max - l_min) / (l_max + l_min + 1e-30), 0.0)
    return ax, ay, np.clip(coherence, 0.0, 1.0)


def valley_channel(h, base_dir, *, cellsize=1.0, relief_radius=8.0, slope_ref=0.2, k_channel=1.0):
    """Rotate the wind toward the local VALLEY AXIS where relief confines the flow. Three pieces:

    - **the axis** — `terrain_axis` above, sign-flipped to point downwind (an axis is a line, not
      an arrow; the wind picks the end it was already heading for).
    - **the confinement** — the CROSS-WIND concavity of the smoothed terrain, a second difference
      over +/- `relief_radius` cells. Walls on BOTH sides (a canyon) give a large positive value; a
      plain or a single hillside gives ~0; a RIDGE gives a negative one, and is excluded — air is
      deflected AROUND a ridge, not channelled along it, so only concave relief steers. Multiplying
      by the sampling length turns it into a dimensionless cross-slope, compared against `slope_ref`
      (the cross-slope that counts as fully confining).
    - **the coherence**, which vetoes rotation where there is no linear structure to rotate toward
      (a round basin is concave in every direction but has no axis).

    Returns unit (dx, dy): the base direction blended toward the axis by confinement * coherence."""
    h = np.asarray(h, dtype=np.float64)
    n, m = h.shape
    ux, uy = _unit(*base_dir)
    hs = ops_filters.gaussian(h, max(relief_radius / 3.0, 0.5))
    ax, ay, coherence = terrain_axis(h, cellsize=cellsize, relief_radius=relief_radius)
    sign = np.where(ax * ux + ay * uy < 0.0, -1.0, 1.0)                # ...pointing downwind
    ax, ay = ax * sign, ay * sign

    cx, cy = -uy, ux                                                   # cross-wind axis
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    L = float(relief_radius)
    left = sample_bilinear(hs, yy + cy * L, xx + cx * L)
    right = sample_bilinear(hs, yy - cy * L, xx - cx * L)
    d2 = (left + right - 2.0 * hs) / ((L * cellsize) ** 2)             # cross-wind concavity, 1/length
    conf = np.clip(k_channel * d2 * (L * cellsize) / slope_ref, 0.0, 1.0)   # -> dimensionless slope
    conf = conf * coherence

    dx, dy = (1.0 - conf) * ux + conf * ax, (1.0 - conf) * uy + conf * ay
    return _unit(dx, dy)


def terrain_adjust(h, base_dir, base_speed=1.0, *, cellsize=1.0, k_speedup=1.5, max_speedup=2.0,
                   fetch=12, shadow_tan=0.268, reach=12, shelter=0.35, relief_radius=8.0,
                   slope_ref=0.2, k_channel=1.0):
    """Steps 1-3 of the chapter's `windField`: speed-up, lee shelter, valley channelling. Returns
    (u, v) in (col, row) components, magnitude in the units of `base_speed`. Still DIVERGENT — run
    `mass_consistent` (step 4) on the result, or just call `wind_field` for all four."""
    s = (terrain_speedup(h, base_dir, cellsize=cellsize, k_speedup=k_speedup,
                         max_speedup=max_speedup, fetch=fetch)
         * lee_shelter(h, base_dir, cellsize=cellsize, shadow_tan=shadow_tan, reach=reach,
                       shelter=shelter))
    dx, dy = valley_channel(h, base_dir, cellsize=cellsize, relief_radius=relief_radius,
                            slope_ref=slope_ref, k_channel=k_channel)
    return s * base_speed * dx, s * base_speed * dy


def wind_field(h, base_dir, base_speed=1.0, *, cellsize=1.0, project=True, **kwargs):
    """The whole chapter recipe: terrain-adjust the regional wind, then (step 4) project it onto a
    divergence-free field so streamlines wrap the terrain instead of piling into it. Returns the
    (u, v) flow field that `aeolian`, `dunes` and `snow` consume per cell.

    `fetch`, `reach` and `relief_radius` are the three LENGTH SCALES, and they are in CELLS by
    construction — each is the span of a discrete walk over the grid. Set them from the terrain, not
    from habit: `fetch` must span the upwind hill (see `upwind_slope`), `reach` the length of the lee
    shadow you want resolved, `relief_radius` the half-width of a channelling valley. Multiply by
    `cellsize` to read them in metres."""
    u, v = terrain_adjust(h, base_dir, base_speed, cellsize=cellsize, **kwargs)
    return mass_consistent(u, v, cellsize) if project else (u, v)


def speed(u, v):
    """Per-cell wind speed |(u, v)| — the scalar the transport law in `aeolian` is cubic in."""
    return np.hypot(np.asarray(u, dtype=np.float64), np.asarray(v, dtype=np.float64))


def divergence(u, v, cellsize=1.0):
    """Central-difference divergence (periodic), for user-facing diagnostics."""
    du = (np.roll(u, -1, 1) - np.roll(u, 1, 1)) / (2.0 * cellsize)
    dv = (np.roll(v, -1, 0) - np.roll(v, 1, 0)) / (2.0 * cellsize)
    return du + dv


def divergence_spectral(u, v, cellsize=1.0):
    KX, KY = _wavenumbers(u.shape, cellsize, zero_nyquist=True)   # i*k derivative -> zero Nyquist
    d_hat = 1j * KX * np.fft.fft2(u) + 1j * KY * np.fft.fft2(v)
    return np.real(np.fft.ifft2(d_hat))


def mass_consistent(u0, v0, cellsize=1.0):
    """Return (u, v): the divergence-free field closest to (u0, v0). Solves
    nabla^2 lambda = div(u0) spectrally, then u = u0 - grad(lambda)."""
    u0 = np.asarray(u0, dtype=np.float64)
    v0 = np.asarray(v0, dtype=np.float64)
    # ONE zeroed-Nyquist i*k operator used for divergence, the Laplacian, AND the gradient update,
    # so the projection cancels exactly (div_new = div_hat + k2*lam_hat = 0) on any grid.
    KX, KY = _wavenumbers(u0.shape, cellsize, zero_nyquist=True)
    U, V = np.fft.fft2(u0), np.fft.fft2(v0)
    div_hat = 1j * KX * U + 1j * KY * V           # spectral divergence
    k2 = KX ** 2 + KY ** 2                          # SAME (zeroed) wavenumbers -> consistent Laplacian
    zero = k2 == 0.0                                # DC and every zeroed-Nyquist mode (div_hat==0 there too)
    k2 = np.where(zero, 1.0, k2)                    # avoid /0; those modes are left unprojected next
    lam_hat = -div_hat / k2                         # nabla^2 lambda = div  ->  -k^2 lam_hat = div_hat
    lam_hat[zero] = 0.0                             # gauge (DC) + unforced Nyquist modes -> no correction
    U -= 1j * KX * lam_hat                          # u = u0 - d(lambda)/dx
    V -= 1j * KY * lam_hat
    return np.real(np.fft.ifft2(U)), np.real(np.fft.ifft2(V))
