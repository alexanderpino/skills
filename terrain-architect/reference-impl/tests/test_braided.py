"""Oracles for the braided-river atom (Murray & Paola 1994), a reduced-complexity cellular model.

What the model faithfully reproduces — and what these tests pin — is the *statistics* of braiding,
not a photoreal planform (see braided.py's tier note):
  1. multi-thread topology (braiding index > 1) on a gravel braidplain;
  2. the SUPER-LINEAR transport mechanism that IS braiding: when flow splits, per-branch capacity
     `K·(Q_k)^m` collapses super-linearly for m>1, so sediment is dropped as BARS instead of carried
     through — an m>1 reach therefore *retains* sediment (exports far less) than a near-linear (m=1)
     reach, which passes it through. This is a robust, deterministic mass-budget signature of the
     bar-building that a fragile emergent-thread count is not;
  3. sediment is conserved to the downstream export;
  4. the run is deterministic.
"""
import numpy as np
import braided


def _braidplain(n=120, m=160, grad=0.0022, seed=0, amp=0.9):
    """A wide, GENTLY downstream-sloping gravel plain with bar-scale roughness — the setting a
    braided reach occupies (steep beds funnel to a single thread; see braided.py)."""
    yy, xx = np.mgrid[0:n, 0:m].astype(float)
    rng = np.random.default_rng(seed)
    return 100.0 - grad * yy + rng.standard_normal((n, m)) * amp


def test_it_braids_multiple_threads():
    """The defining property: more than one active channel per cross-section on average."""
    _, Q = braided.braided_river(_braidplain(), 90)
    assert braided.braiding_index(Q) > 1.5                            # genuinely multi-thread


def test_superlinearity_builds_bars_not_export():
    """Murray & Paola's central result: braiding is driven by the super-linearity of transport in
    discharge. With m>1, splitting flow collapses the per-branch capacity, so sediment DEPOSITS as
    bars and far less leaves the downstream edge; with near-linear m=1 the capacity is preserved
    through splits and the sediment passes through. So the m=1 reach must export a larger fraction of
    what was fed than the m=2.5 reach — the mass-budget fingerprint of bar-building. Checked over
    several seeds so it does not hinge on one bed."""
    frac_lin, frac_braid = [], []
    for seed in range(3):
        bed = _braidplain(n=120, m=150, seed=seed, amp=0.5)
        _, _, b25 = braided.braided_river(bed, 80, m_exp=2.5, return_budget=True)
        _, _, b10 = braided.braided_river(bed, 80, m_exp=1.0, return_budget=True)
        frac_braid.append(b25["exported"] / b25["fed"])
        frac_lin.append(b10["exported"] / b10["fed"])
    # linear transport passes markedly more sediment through than super-linear (which banks it as bars)
    assert np.mean(frac_lin) > np.mean(frac_braid) * 3.0


def test_sediment_is_conserved_to_the_export():
    """Erosion adds to the load, deposition removes it, lateral transport is a strict flux form — so
    the net change in bed mass equals what was fed in minus what left the downstream edge (to the
    float roundoff accumulated by the scatter-adds)."""
    bed, Q, b = braided.braided_river(_braidplain(seed=1, amp=0.5), 40, return_budget=True)
    assert np.all(np.isfinite(bed))
    assert abs(b["bed_change"] - (b["fed"] - b["exported"])) < 1e-6 * (abs(b["fed"]) + 1.0)


def test_deterministic():
    a = braided.braided_river(_braidplain(seed=2), 30)[0]
    b = braided.braided_river(_braidplain(seed=2), 30)[0]
    assert np.array_equal(a, b)
