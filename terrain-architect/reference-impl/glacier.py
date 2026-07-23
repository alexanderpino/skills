"""Glacial erosion — U-valley carving by ice (12-glacial-coastal.md).

The SIA glacier in `sims_illustrative.py` evolves ICE only; it never touches the bed. This module
adds the morphological half — the `glacierStep` bed erosion of chapter 12 (grounded on Argudo et al.
2020; Glen flow law + SIA per Cuffey & Paterson 2010):

    ū   = -(2A/(n+2))(ρg)^n H^(n+1) |∇s|^(n-1) ∇s        # depth-averaged velocity on the ICE surface
    u_b = f · |ū|         (0 where thin / cold-based)      # basal sliding
    ė   = K_g · |u_b|^l                                    # abrasion (Hallet-style; l≈1, K_g≈1e-4)
    bed -= ė · Δt          (+ plucking where steep)        # eroded volume -> a moraine field

The `H^(n+1)` velocity law concentrates ice into fast trunk streams, so basal erosion deepens the
glaciated valleys and leaves the interfluves as **arêtes**; a trunk glaciated harder than its
tributary leaves a **hanging valley** — "you don't author it; it falls out." That trunk-concentrated
incision is what this module computes and what its tests verify.

Honesty note (tier). Abrasion ∝ basal sliding is P/F-tier physics. The idealised PARABOLIC U
cross-section is an **L-tier** emergent landform (chapter 12's table): a vertically-integrated SIA
concentrates erosion at the thalweg and does not by itself reproduce the textbook parabola — that
needs a higher-order ice model or the cross-valley sliding distribution of Harbor (1992). The optional
`wall_abrasion` term is an honest F-tier "look": it lowers glacially-oversteepened walls toward a
smoother profile (carve-only, mass -> moraine), widening the trough toward a U. This module is
illustrative-morphological — invariant-checked (mass budget, carve-only-under-ice, differential
deepening), NOT a certified erosion-rate oracle.

Units: pass `A` and `dt` in a consistent system. The defaults are in YEARS (`A` in Pa⁻³ yr⁻¹, `dt`
in yr, `beta` in m/m/yr) so mass balance is well-posed; the transport reduces to
`sims_illustrative.glacier_sia` for any matched `A·dt` when `K_g=0, beta=0`.
"""
import numpy as np

import diffusion

_SEC_PER_YR = 3.156e7
_A_YR = 2.4e-24 * _SEC_PER_YR             # Glen A at 0 °C in Pa^-3 yr^-1 (Cuffey & Paterson 2010)


def glacier_carve(bed, H, steps, *, A=_A_YR, n=3, rho=917.0, g=9.81, dt=60.0, cellsize=100.0,
                  ela=None, beta=0.0, b_max=1.5, f_slide=0.6, K_g=8e-4, l=1.0, H_min=3.0,
                  K_pluck=0.0, fracture=None, pluck_slope=0.5, wall_abrasion=0.0,
                  max_erode_frac=0.3, max_substeps=900):
    """Evolve ice thickness `H` on bedrock `bed` and CARVE the bed under the ice (12). Returns
    `(bed, H, moraine)` — the eroded bedrock, the final ice, and the eroded-volume (moraine) field.

    beta, ela      mass balance (accumulate above the ELA, melt below); `beta=0` freezes the ice mass
    f_slide        basal sliding fraction of the depth-averaged velocity (0 where cold-based)
    K_g, l         abrasion law ė = K_g·|u_b|^l (Argudo 2020; `l≈1`)
    H_min          ice thinner than this is cold-based / stagnant and does not erode
    K_pluck, fracture  optional plucking ė_pluck = K_pluck·|u_b|·fracture where the bed is steep
    wall_abrasion  optional F-tier trough-widening: lower oversteepened walls under ice (carve-only)
    """
    bed = np.asarray(bed, dtype=np.float64).copy()
    H = np.asarray(H, dtype=np.float64).copy()
    moraine = np.zeros_like(bed)
    c = 2.0 * A / (n + 2) * (rho * g) ** n
    for _ in range(int(steps)):
        if beta and ela is not None:                              # 1. mass balance (climate, 13)
            s = bed + H
            H = np.maximum(H + np.clip(beta * (s - ela), None, b_max) * dt, 0.0)

        remaining = dt                                            # 2-3. subcycled SIA transport
        subs = 0
        while remaining > 1e-6 * dt and subs < max_substeps:
            s = bed + H
            sy, sx = np.gradient(s, cellsize)
            gradmag = np.hypot(sx, sy)
            with np.errstate(over="ignore", invalid="ignore"):
                D = c * H ** (n + 2) * gradmag ** (n - 1)         # flux diffusivity on the ice surface
            D = np.nan_to_num(D, nan=0.0, posinf=0.0)            # defensive on stiff/rough terrain
            dmax = float(D.max())
            if not np.isfinite(dmax) or dmax <= 0.0:
                break
            sub = min(remaining, 0.2 * cellsize * cellsize / dmax)
            Dx = 0.5 * (D[:, :-1] + D[:, 1:]); Fx = Dx * (s[:, :-1] - s[:, 1:]) / cellsize
            Dy = 0.5 * (D[:-1, :] + D[1:, :]); Fy = Dy * (s[:-1, :] - s[1:, :]) / cellsize
            dH = np.zeros_like(H)
            dH[:, :-1] -= Fx; dH[:, 1:] += Fx
            dH[:-1, :] -= Fy; dH[1:, :] += Fy
            H = np.maximum(H + sub / cellsize * dH, 0.0)
            remaining -= sub
            subs += 1

        # 4. bed erosion at the base (abrasion + optional plucking)
        s = bed + H
        sy, sx = np.gradient(s, cellsize)
        gradmag = np.hypot(sx, sy)
        with np.errstate(over="ignore", invalid="ignore"):
            u_bar = c * H ** (n + 1) * gradmag ** n               # |depth-averaged velocity|
        u_bar = np.nan_to_num(u_bar, nan=0.0, posinf=0.0)        # defensive: no inf/nan into the bed
        u_b = f_slide * u_bar * (H > H_min)                      # basal sliding; 0 where thin/cold
        ero = K_g * np.abs(u_b) ** l * dt
        if K_pluck and fracture is not None:                     # quarrying at steep, fractured beds
            steep = gradmag > pluck_slope
            ero = ero + K_pluck * np.abs(u_b) * np.asarray(fracture, dtype=np.float64) * steep * dt
        ero = np.minimum(ero, max_erode_frac * H)                # can't out-erode the ice per step:
        bed = bed - ero                                          # bounds the deepen->steepen->slide
        moraine = moraine + ero                                  # feedback (else it runs away)

        if wall_abrasion > 0.0:                                  # F-tier: widen the trough (carve-only)
            bd = diffusion.hillslope_diffuse(bed, wall_abrasion, 0.2, 4, cellsize)
            cut = np.where((H > H_min) & (bd < bed), bed - bd, 0.0)
            bed = bed - cut
            moraine = moraine + cut
    return bed, H, moraine
