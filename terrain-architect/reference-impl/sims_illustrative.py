"""ILLUSTRATIVE simulations — the deliberately un-oracled regimes (12, 19).

READ THIS FIRST. Every other module in `reference-impl` is pinned to a DECISIVE oracle — a
closed-form value or an independent library. The processes here are the ones the README's
"Coverage boundary" excludes precisely because they have **no decisive deterministic oracle**:
coastal cliff retreat and tides (12), the lava CA (19), and the transient SIA glacier (12).

They are included for completeness and to run, but they are held only to **invariants** — the
weaker checks that still exist: the field stays finite, the mass/energy budget closes, and
trends go the right way (a cliff retreats landward, a glacier spreads, lava cools and freezes,
the tide stays within its range). Passing those does NOT mean the numbers are quantitatively
right, only that nothing is grossly broken. Do not treat these as verified reference
implementations; treat them as sketches you can watch move. For production, take the paper-
derived pseudocode in `12`/`19` and validate against real morphometry, not against this file.
"""
import numpy as np

import erosion_thermal


_D8 = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0),
       (-1, -1, np.sqrt(2)), (-1, 1, np.sqrt(2)), (1, -1, np.sqrt(2)), (1, 1, np.sqrt(2))]


# --------------------------------------------------------------------------- #
# lava flow — Bingham grid CA with temperature (19). INVARIANT: mass conserved.
# --------------------------------------------------------------------------- #
def lava_flow(bed, source, steps, *, erupt=2.0, T_erupt=1400.0, T_env=25.0, T_solidus=1000.0,
              rho=2600.0, g=9.81, eta=1e3, tau_y0=1.0e3, tau_y_gain=30.0, cool=9.0,
              dt=0.1, cellsize=1.0, kflux=0.05):
    """Erupt lava at `source` (i, j) and let it flow downhill by a Bingham rule (flux only where
    the driving stress beats the temperature-dependent yield stress — the gate that gives lava
    its steep snout and stops it), cooling and freezing into new bedrock. Boundaries periodic.
    Returns (bed, L, T, budget). Invariant: erupted == still-molten + frozen-into-bed."""
    bed = np.asarray(bed, dtype=np.float64).copy()
    bed0 = bed.copy()
    L = np.zeros_like(bed)
    T = np.full_like(bed, T_env)
    si, sj = source
    erupted = 0.0
    for _ in range(int(steps)):
        L[si, sj] += erupt * dt
        T[si, sj] = T_erupt
        erupted += erupt * dt

        surf = bed + L
        tau_y = np.maximum(tau_y0 + tau_y_gain * (T_solidus - T), 1.0)   # rises as T falls
        outs, total = [], np.zeros_like(L)
        for di, dj, dist in _D8:
            surf_nb = np.roll(np.roll(surf, -di, 0), -dj, 1)
            dh = surf - surf_nb
            tau = rho * g * L * np.maximum(dh, 0.0) / (dist * cellsize)
            flux = np.where((dh > 0.0) & (tau > tau_y), kflux * (tau - tau_y) * L * L / eta, 0.0)
            dL = flux * dt / cellsize
            outs.append(dL)
            total += dL
        scale = np.where(total > 1e-12, np.minimum(1.0, L / (total + 1e-30)), 0.0)
        for (di, dj, _), dL in zip(_D8, outs):
            moved = dL * scale
            L = L - moved
            L = L + np.roll(np.roll(moved, di, 0), dj, 1)

        molten = L > 1e-9
        T = np.where(molten, T - cool * dt, T_env)
        T = np.maximum(T, T_env)
        frozen = molten & (T <= T_solidus)
        bed = bed + np.where(frozen, L, 0.0)
        L = np.where(frozen, 0.0, L)

    budget = {"erupted": erupted, "molten": float(L.sum()),
              "frozen": float((bed - bed0).sum())}
    return bed, L, T, budget


# --------------------------------------------------------------------------- #
# glacier — Shallow Ice Approximation (12). INVARIANT: transport conserves ice.
# --------------------------------------------------------------------------- #
def glacier_sia(bed, H, steps, *, A=2.4e-24, n=3, rho=917.0, g=9.81, dt=1.0e6,
                cellsize=100.0, ela=None, beta=0.0, b_max=5.0, max_substeps=300):
    """Evolve ice thickness `H` on bedrock `bed` by the SIA (Glen n=3): mass balance
    (accumulate above the ELA, melt below) plus ice transport as a diffusion of the ICE SURFACE
    (H^(n+2) diffusivity — thick ice flows far faster, so glaciers self-organise into trunks).
    The diffusion is stiff, so transport is explicit-subcycled at the CFL limit and capped at
    `max_substeps` (a geological `dt` would otherwise need hundreds of thousands of substeps —
    use an implicit solve for that; this is the illustrative sketch). Invariant: the transport
    step conserves total ice (divergence form); H stays >= 0."""
    bed = np.asarray(bed, dtype=np.float64)
    H = np.asarray(H, dtype=np.float64).copy()
    c = 2.0 * A / (n + 2) * (rho * g) ** n
    for _ in range(int(steps)):
        if beta and ela is not None:                       # 1. mass balance (climate, 13)
            s = bed + H
            H = np.maximum(H + np.clip(beta * (s - ela), None, b_max) * dt, 0.0)

        remaining = dt                                     # 2-3. subcycled transport
        subs = 0
        while remaining > 1e-6 * dt and subs < max_substeps:
            s = bed + H
            sy, sx = np.gradient(s, cellsize)
            gradmag = np.hypot(sx, sy)
            D = c * H ** (n + 2) * gradmag ** (n - 1)
            dmax = float(D.max())
            if dmax <= 0.0:
                break
            sub = min(remaining, 0.2 * cellsize * cellsize / dmax)
            Dx = 0.5 * (D[:, :-1] + D[:, 1:])
            Fx = Dx * (s[:, :-1] - s[:, 1:]) / cellsize    # flux left-cell -> right-cell
            Dy = 0.5 * (D[:-1, :] + D[1:, :])
            Fy = Dy * (s[:-1, :] - s[1:, :]) / cellsize
            dH = np.zeros_like(H)
            dH[:, :-1] -= Fx
            dH[:, 1:] += Fx
            dH[:-1, :] -= Fy
            dH[1:, :] += Fy
            H = np.maximum(H + sub / cellsize * dH, 0.0)
            remaining -= sub
            subs += 1
    return H


# --------------------------------------------------------------------------- #
# coastal cliff retreat — notch / collapse / deposit (12). INVARIANT: retreat.
# --------------------------------------------------------------------------- #
def coastal_retreat(h, sea_level, steps, *, exposure=1.0, k_coast=0.5, notch=1.0,
                    repose=0.7, cellsize=1.0):
    """Iterate notch -> collapse -> retreat: erode a band AT sea level (a wave notch), then let
    thermal (05) collapse the undercut cliff. Planes the terrain off at sea level (a wave-cut
    platform) and drives the shoreline landward. `exposure` is a [0,1] field (or scalar).
    Invariant: land area above sea level shrinks (the cliff retreats); the field stays finite."""
    h = np.asarray(h, dtype=np.float64).copy()
    exposure = np.asarray(exposure, dtype=np.float64)
    for _ in range(int(steps)):
        band = np.exp(-((h - sea_level) ** 2) / (2.0 * notch * notch))
        h = h - k_coast * exposure * band
        h = erosion_thermal.thermal_erosion(h, repose_slope=repose, iters=1, cellsize=cellsize)
    return h


# --------------------------------------------------------------------------- #
# tides — an authored oscillation of the water plane (12). The solid is untouched.
# --------------------------------------------------------------------------- #
def tide_level(t, mean_sea_level, tidal_range, period=12.42):
    """Water-surface height at time t (semidiurnal by default). The tide is authored, not
    simulated — the astronomy is a look. Bounded in [msl - range/2, msl + range/2]."""
    return mean_sea_level + 0.5 * tidal_range * np.sin(2.0 * np.pi * np.asarray(t) / period)


def wet_mask(solid_top, water_level):
    """Cells below the current water plane. Water is a FLUID LAYER over the solid — this never
    modifies `solid_top` (08 layer stack)."""
    return np.asarray(solid_top, dtype=np.float64) < water_level


def intertidal_mask(solid_top, mean_sea_level, tidal_range):
    """The strip swept between high and low water — wet at high tide, dry at low. A material/
    ecology band (06), not a new height; its width is tidal_range / shore_slope."""
    solid_top = np.asarray(solid_top, dtype=np.float64)
    lo = mean_sea_level - 0.5 * tidal_range
    hi = mean_sea_level + 0.5 * tidal_range
    return (solid_top >= lo) & (solid_top < hi)     # wet at high tide, dry at low (== the swept strip)
