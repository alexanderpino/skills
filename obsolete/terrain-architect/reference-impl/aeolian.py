"""Aeolian transport and abrasion — what the wind FIELD does to the terrain (05, 16).

Two couplings, both driven by the per-cell wind field from `winds.wind_field` rather than by a
global constant vector:

- **Transport** (`shear_velocity`, `saltation_flux`, `exner_step`, `05` Bagnold 1941) — the wind's
  SPEED sets a sand flux that is THRESHOLD-gated and CUBIC in the friction velocity, and the
  DIVERGENCE of that flux is what raises or lowers the bed (sediment continuity, Exner). This is
  the chain that makes a terrain-aware wind field matter: the field speeds up over a windward slope
  (Jackson & Hunt, `winds`), so the flux rises going up the slope, so the windward face is
  STRIPPED; it decelerates in the lee, so the flux converges and sand is DEPOSITED. Neither
  happens under a spatially constant wind, where the flux is uniform and its divergence is zero.
- **Abrasion** (`yardang`, `16` Ward & Greeley 1984) — streamlined ridges cut from a soft substrate.

`dunes.py` is the DISCRETE (cellular-automaton) branch of the same physics; `exner_step` is the
CONTINUUM branch, and the one that couples directly to a wind field.

The yardang carve of chapter 16 (Ward & Greeley 1984): streamlined ridges
abraded from a soft, cohesive substrate (playa clay, loess, tuff), aligned with the prevailing wind
— the aeolian twin of a drumlin.

    yardang(h, windDir, softMask):
        align = anisotropic noise with its long axis ‖ windDir      # 01 domain-warp along the wind
        for iterations:
            abr = K_abr · windExposure(p, windDir) · softMask
            h -= abr · saltationWeight(heightAboveFloor(p))          # abrasion is BOTTOM-weighted
        # teardrop ridges: steep blunt nose upwind, tapering lee tail

The detail that sells it (Ward & Greeley): **abrasion is bottom-weighted** — saltating sand only
reaches ~1 m up, so yardangs are undercut at the base and the low ground is cut fastest. Here the
wind-aligned lanes are seeded by anisotropic fBm (long axis ‖ wind); erosion carves those lanes,
weighted toward each cell's height above its local floor, and only within `softMask`. F-tier "look",
invariant-checked: ridges elongate ‖ wind, only soft ground erodes, and the low ground (troughs)
is cut more than the crests (bottom-weighting → streamlined, undercut ridges).
"""
import numpy as np

import noise
import winds

KARMAN = 0.4                 # von Karman constant (law of the wall)
RHO_AIR = 1.22               # kg/m^3, sea level
RHO_QUARTZ = 2650.0          # kg/m^3
G = 9.81                     # m/s^2  (Kok et al. 2012: rescale g and rho_a for Mars/Venus/Titan)
D_REF = 250e-6               # m, Bagnold's reference grain size


def _as_field(wind, shape):
    """Accept either a constant `(u, v)` or a pair of (u, v) FIELDS, and return two arrays of
    `shape`. Every consumer takes wind this way, so a graph can swap a regional constant for the
    terrain-aware field from `winds.wind_field` without changing any call site."""
    u, v = wind
    return (np.broadcast_to(np.asarray(u, dtype=np.float64), shape).astype(np.float64),
            np.broadcast_to(np.asarray(v, dtype=np.float64), shape).astype(np.float64))


def shear_velocity(wind_speed, *, z=10.0, z0=1e-3):
    """Friction velocity u* from a wind speed measured at height `z` (law of the wall):

        U(z) = (u*/kappa) * ln(z/z0)   ->   u* = U(z) * kappa / ln(z/z0)

    This is the unit conversion the transport law needs: `winds` produces a SPEED, Bagnold's
    threshold and flux are both in u*. `z0` is the aerodynamic roughness length (~1e-3 m for a bare
    sand sheet, orders of magnitude larger over vegetation or blocky ground — which is exactly why
    vegetation cover suppresses transport, `13`)."""
    return np.asarray(wind_speed, dtype=np.float64) * KARMAN / np.log(z / z0)


def threshold_shear(d=D_REF, *, A=0.1, rho_s=RHO_QUARTZ, rho_a=RHO_AIR, g=G):
    """Bagnold's (1941) threshold friction velocity — below this NOTHING moves:

        u*_t = A * sqrt( ((rho_s - rho_a)/rho_a) * g * d )

    ~0.2 m/s for 250 um quartz sand in Earth air (roughly 5 m/s at 1 m height). `A ~ 0.1` for
    turbulent (fluid-threshold) flow. Scalar, and it is the reason averaging a wind field destroys
    the result: a field uniformly just below threshold moves nothing."""
    return A * np.sqrt(((rho_s - rho_a) / rho_a) * g * d)


def saltation_flux(u_star, *, d=D_REF, u_star_t=None, C=1.8, rho_a=RHO_AIR, g=G):
    """Bagnold's (1941) saltation flux — the CUBIC law, gated at the threshold:

        q = C * sqrt(d/D_ref) * (rho_a/g) * u*^3      for u* > u*_t,   else 0

    Mass flux per unit width per unit time (kg/m/s). The u*^3 is the whole point: doubling the wind
    moves EIGHT times the sand, so a linear wind-strength slider feels wrong and a terrain-aware
    field's modest speed-up over a crest is a large flux change. `C ~ 1.8` for naturally graded sand.
    (Owen 1964 / Lettau's q ~ u*^2 (u* - u*_t) is the smoother variant near threshold; the chapter
    cites Bagnold's cubic, so that is what this mirrors.)"""
    u_star = np.asarray(u_star, dtype=np.float64)
    if u_star_t is None:
        u_star_t = threshold_shear(d, rho_a=rho_a, g=g)
    q = C * np.sqrt(d / D_REF) * (rho_a / g) * u_star ** 3
    return np.where(u_star > u_star_t, q, 0.0)


def transport_field(wind, *, shape=None, d=D_REF, z=10.0, z0=1e-3, u_star_t=None, C=1.8,
                    rho_a=RHO_AIR, g=G):
    """The full speed -> flux chain over a wind field: (qx, qy), the sand flux VECTOR per cell,
    pointing downwind with the Bagnold cubic magnitude. Feed it `winds.wind_field(h, ...)` and the
    flux inherits the terrain's speed-up, shelter and channelling."""
    u, v = wind if shape is None else _as_field(wind, shape)
    u = np.asarray(u, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    q = saltation_flux(shear_velocity(np.hypot(u, v), z=z, z0=z0), d=d, u_star_t=u_star_t, C=C,
                       rho_a=rho_a, g=g)
    mag = np.hypot(u, v) + 1e-30
    return q * u / mag, q * v / mag


def saturate(qx, qy, wind, *, sat_length=0.0, cellsize=1.0, iters=None):
    """Relax the flux toward its saturated value along the wind over a SATURATION LENGTH `L_sat`
    (Sauermann et al. 2001, the continuum saltation model):

        dq/ds = (q_sat - q) / L_sat

    Sand does not reach its transport capacity instantly — the saltation cloud takes a few metres
    to spin up — and that lag is what gives dunes a MINIMUM SIZE (a bump shorter than L_sat cannot
    grow) and shifts the deposition maximum DOWNWIND of a crest, the aeolian twin of the orographic
    fallout lag (`13`). Integrated by iterated upwind sampling, so information propagates one cell
    per iteration; `iters` defaults to enough to cross the relaxation length. `sat_length=0` returns
    the input unchanged (instantaneous saturation — pure Bagnold)."""
    if sat_length <= 0.0:
        return np.asarray(qx, dtype=np.float64), np.asarray(qy, dtype=np.float64)
    qx = np.asarray(qx, dtype=np.float64)
    qy = np.asarray(qy, dtype=np.float64)
    n, m = qx.shape
    u, v = _as_field(wind, qx.shape)
    ux, uy = u / (np.hypot(u, v) + 1e-30), v / (np.hypot(u, v) + 1e-30)
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    ds = cellsize
    w = min(ds / sat_length, 1.0)                       # relaxation weight over one upwind step
    if iters is None:
        iters = max(1, int(np.ceil(3.0 * sat_length / ds)))
    sx, sy = qx.copy(), qy.copy()                       # q_sat, the target
    for _ in range(int(iters)):
        up_x = winds.sample_bilinear(qx, yy - uy, xx - ux)     # flux arriving from one cell upwind
        up_y = winds.sample_bilinear(qy, yy - uy, xx - ux)
        qx = up_x + w * (sx - up_x)
        qy = up_y + w * (sy - up_y)
    return qx, qy


def exner_step(bed, wind, *, sand=None, dt=1.0, cellsize=1.0, rho_bed=1600.0, sat_length=0.0,
               d=D_REF, z=10.0, z0=1e-3, u_star_t=None, C=1.8, rho_a=RHO_AIR, g=G,
               availability=None):
    """One step of aeolian sediment continuity (the Exner equation) under a wind FIELD:

        d(bed)/dt = -(1/rho_bed) * div(q)

    Flux DIVERGES (speeds up) -> the bed is deflated; flux CONVERGES (decelerates) -> sand is
    deposited. Everything the terrain-aware field does to the wind shows up here: the windward face
    of a hill is stripped because the flow accelerates up it, and the lee fills because the shadow
    zone stalls the flow. Under a spatially uniform wind div(q) = 0 and NOTHING happens — which is
    the honest statement of why the wind field is not optional.

    `sand` (optional) is the erodible layer in metres; deflation is limited to the sand actually
    present, so the wind cannot excavate bedrock (that is `yardang`'s abrasion, a much slower
    process). `availability` is an extra [0,1] gate (vegetation cover, crust, moisture, `13`).
    Returns (bed, sand) when `sand` is given, else the new bed. Mass is conserved to the flux
    through the periodic boundary."""
    bed = np.asarray(bed, dtype=np.float64).copy()
    u, v = _as_field(wind, bed.shape)
    qx, qy = transport_field((u, v), d=d, z=z, z0=z0, u_star_t=u_star_t, C=C, rho_a=rho_a, g=g)
    if availability is not None:
        gate = np.broadcast_to(np.asarray(availability, dtype=np.float64), bed.shape)
        qx, qy = qx * gate, qy * gate
    qx, qy = saturate(qx, qy, (u, v), sat_length=sat_length, cellsize=cellsize)
    dh = -(dt / rho_bed) * winds.divergence(qx, qy, cellsize)      # -div(q): erode where q grows
    if sand is None:
        return bed + dh
    sand = np.asarray(sand, dtype=np.float64).copy()
    dh = np.maximum(dh, -sand)                                     # can only deflate sand that is there
    return bed + dh, sand + dh


def yardang(h, wind, soft_mask, *, iters=10, K_abr=0.6, freq_along=0.018, freq_cross=0.11,
            saltation_h=6.0, floor_reach=3, octaves=4, seed=0):
    """Abrade wind-parallel streamlined ridges (yardangs) into a soft substrate `h`. `wind=(u, v)` in
    (col, row) components — a constant vector OR a pair of fields (`winds.wind_field`) — sets the
    ridge long axis. `soft_mask` (scalar or field in [0,1]) confines abrasion to erodible rock.
    Carve-only. Returns a new height field.

    Given a FIELD, the lane geometry is seeded from the field's RESULTANT direction (a yardang field
    records the long-term prevailing wind, so its lanes are straight even where the instantaneous
    flow bends), while the abrasion RATE follows the local wind speed cubed — the Bagnold scaling of
    `saltation_flux`, normalised to its mean so `K_abr` keeps its meaning. Sheltered ground therefore
    abrades slowly and exposed crests fast, which is the speed coupling a constant vector cannot
    express."""
    h = np.asarray(h, dtype=np.float64).copy()
    n, m = h.shape
    soft = np.broadcast_to(np.asarray(soft_mask, dtype=np.float64), (n, m))
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    uf, vf = _as_field(wind, (n, m))
    u, v = float(uf.mean()), float(vf.mean())                   # resultant direction sets the lanes
    mag = float(np.hypot(u, v)) + 1e-30
    u, v = u / mag, v / mag
    sp = np.hypot(uf, vf) ** 3                                  # local abrasion rate ~ speed^3 (Bagnold)
    rate = sp / (sp.mean() + 1e-30)
    along = xx * u + yy * v                                     # wind-parallel coordinate
    cross = -xx * v + yy * u                                    # wind-perpendicular coordinate
    # anisotropic seed: low frequency ALONG the wind (long features), higher ACROSS (narrow spacing)
    groove = noise.fbm(along * freq_along, cross * freq_cross, seed, octaves=octaves)
    pot = np.clip(-groove, 0.0, None)                          # carve the low-groove lanes (troughs)
    pot = pot / (pot.max() + 1e-9) * rate
    r = int(floor_reach)
    for _ in range(int(iters)):
        floor = np.minimum.reduce([np.roll(np.roll(h, di, 0), dj, 1)
                                   for di in (-r, 0, r) for dj in (-r, 0, r)])
        salt = np.exp(-np.maximum(h - floor, 0.0) / saltation_h)   # bottom-weighted saltation (~1 m)
        h = h - K_abr * pot * soft * salt
    return h
