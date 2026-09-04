"""Closed-form / analytic sims — each verified against exact expected values.

Mirrors the pseudocode in:
  - 11-geological.md  : tephra fallout (Pyle 1989), PDC energy cone (Malin & Sheridan 1982)
  - 12-glacial-coastal: seafloor age-depth (Parsons & Sclater 1977; Stein & Stein 1992)
  - 03-flow-routing   : avulsion superelevation criterion (Mohrig et al. 2000)
"""
import numpy as np


# --- Tephra fallout: Pyle 1989 exponential thinning (11) ---------------------
def tephra_thickness(dist, T0, k):
    """T(r) = T0 * exp(-k*r). Deposit thins exponentially with distance from vent.
    dist: distance(s) from the vent; T0: thickness at the vent; k: thinning coeff."""
    return T0 * np.exp(-k * np.asarray(dist, dtype=np.float64))


# --- Seafloor age-depth (12) -------------------------------------------------
def seafloor_depth_hsc(age_myr, d0=2500.0, C=350.0):
    """Half-space cooling (Parsons & Sclater 1977): d = d0 + C*sqrt(age).
    Valid for young crust (age <~ 70 Myr). Depth below the ridge crest, metres."""
    return d0 + C * np.sqrt(np.asarray(age_myr, dtype=np.float64))


def seafloor_depth_gdh1(age_myr):
    """Plate model GDH1 (Stein & Stein 1992): flattens for old crust."""
    age = np.asarray(age_myr, dtype=np.float64)
    young = 2600.0 + 365.0 * np.sqrt(age)
    old = 5651.0 - 2473.0 * np.exp(-0.0278 * age)
    return np.where(age <= 20.0, young, old)


# --- PDC energy cone: Malin & Sheridan 1982 (11) -----------------------------
def energy_cone_runout(collapse_height, mu):
    """Runout on flat ground: L = Hc / mu, with mu = H/L the Heim coefficient."""
    return collapse_height / mu


def pdc_inundated(topo, vent_ij, collapse_height, mu, cellsize=1.0):
    """A cell is inundated where the energy line
        z_EL(x) = z_vent + Hc - mu*dist
    stays above the ground. Ponds in valleys, blocked by ridges."""
    topo = np.asarray(topo, dtype=np.float64)
    n, m = topo.shape
    yy, xx = np.mgrid[0:n, 0:m].astype(np.float64)
    d = np.hypot(xx - vent_ij[1], yy - vent_ij[0]) * cellsize
    z_el = topo[vent_ij[0], vent_ij[1]] + collapse_height - mu * d
    return z_el > topo


# --- Avulsion superelevation criterion: Mohrig et al. 2000 (03) --------------
def superelevation(belt_elev, floodplain_elev, channel_depth):
    """SE = (channel-belt elevation - floodplain elevation) / channel depth.
    Avulsion becomes likely when SE >~ 1 (belt perched ~one channel depth up)."""
    return (belt_elev - floodplain_elev) / channel_depth


def avulses(belt_elev, floodplain_elev, channel_depth, flood_overtops, threshold=1.0):
    """Avulsion needs BOTH setup (SE >= threshold) and a trigger (a flood overtops)."""
    se = superelevation(belt_elev, floodplain_elev, channel_depth)
    return bool(se >= threshold) and bool(flood_overtops)
