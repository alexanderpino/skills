import numpy as np
import analytic as A


def test_tephra_log_linear():
    """log(thickness) is linear in distance with slope -k (Pyle 1989)."""
    r = np.linspace(1.0, 50.0, 60)
    T0, k = 100.0, 0.08
    T = A.tephra_thickness(r, T0, k)
    slope, intercept = np.polyfit(r, np.log(T), 1)
    assert abs(slope - (-k)) < 1e-9
    assert abs(np.exp(intercept) - T0) < 1e-6


def test_age_depth_sqrt_law():
    assert abs(A.seafloor_depth_hsc(0.0) - 2500.0) < 1e-9
    assert abs(A.seafloor_depth_hsc(100.0) - (2500.0 + 350.0 * 10.0)) < 1e-9
    ages = np.linspace(0.0, 70.0, 50)
    d = A.seafloor_depth_hsc(ages)
    assert np.all(np.diff(d) > 0)  # monotonically deepening with age


def test_gdh1_continuous_and_flattens():
    lo = 2600.0 + 365.0 * np.sqrt(20.0)
    hi = 5651.0 - 2473.0 * np.exp(-0.0278 * 20.0)
    assert abs(lo - hi) < 60.0                       # continuous across the 20-Myr join
    assert abs(A.seafloor_depth_gdh1(1e4) - 5651.0) < 1.0  # old-crust plateau


def test_energy_cone_runout():
    assert abs(A.energy_cone_runout(1000.0, 0.2) - 5000.0) < 1e-9


def test_pdc_inundates_within_runout_and_stops_beyond():
    topo = np.zeros((201, 201))
    inun = A.pdc_inundated(topo, (100, 100), collapse_height=10.0, mu=0.2, cellsize=1.0)
    # runout radius = Hc/mu = 50 cells
    assert inun[100, 100]
    assert inun[100, 100 + 40]        # inside runout
    assert not inun[100, 100 + 60]    # beyond runout


def test_pdc_blocked_by_ridge():
    topo = np.zeros((201, 201))
    topo[:, 130:] = 100.0             # a tall wall 30 cells downrange (energy line ~ 4 m there)
    inun = A.pdc_inundated(topo, (100, 100), collapse_height=10.0, mu=0.2, cellsize=1.0)
    assert not inun[100, 140]         # the ridge is above the energy line -> not inundated


def test_superelevation_and_trigger():
    assert abs(A.superelevation(11.0, 10.0, 1.0) - 1.0) < 1e-12
    assert A.avulses(11.0, 10.0, 1.0, flood_overtops=True)      # setup + trigger
    assert not A.avulses(10.5, 10.0, 1.0, flood_overtops=True)  # SE=0.5 < 1: no setup
    assert not A.avulses(12.0, 10.0, 1.0, flood_overtops=False)  # no trigger
