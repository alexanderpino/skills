"""The mask partition: `Σ ≤ 1` and `Σ = 1` are BOTH right, about different objects.

THE CONTRADICTION THIS RESOLVES. Four places in the chapters make what look like two
incompatible demands on the same quantity:

    06 "Masks must partition"                     — reads as Σ = 1
    08 "Splat weights must sum to 1"              — Σ = 1
    08 "Partitioned splat weights (must sum to 1)" — Σ = 1
    14 "assert Σ masks ≤ 1" · 00 the same         — Σ ≤ 1

A reader implementing the assertion cannot tell which to write, and `06` contradicts itself
inside one bullet: its headline says "partition" while its prescribed remedy is a priority
stack, `each subsequent mask multiplied by (1 − Σ previous)`, which produces Σ ≤ 1.

THEY ARE TWO STAGES, NOT ONE QUANTITY.

  1. RAW COVERAGE MASKS, straight off the simulations — snow, water, vegetation, debris. Each
     is an independent field in [0, 1] and NOTHING makes them sum to anything. `Σ > 1` means two
     simulations claim the same ground; `Σ < 1` is ordinary, and the shortfall is the base
     material's share. `Σ ≤ 1` is the assertion, and `14` puts it at the fan-in because that is
     the one place every mask passes through.

  2. EFFECTIVE SPLAT WEIGHTS, after compositing. These sum to exactly 1 — not by convention but
     by construction, and `test_the_over_composite_partitions_by_construction` measures it.

⚠️ AND THE REASON THE ASSERTION IS NEEDED IS THAT STAGE 2 HIDES STAGE 1's BUG. The shipped
compositor, `render.splat_blend`, is an ordered over-composite (`out·(1−m) + colour·m`), not a
weighted sum. Feed it masks summing to 1.8 and it still returns effective weights summing to
1.0000000000, with the base absorbing `Π(1−mᵢ)`. So over-subscription produces no artefact, no
brightness error, no clue of any kind — the compositing ORDER silently arbitrates a conflict the
simulations should never have produced. That is exactly the failure that survives to ship, and
the only place it is visible is upstream, on the raw masks.

The shader case `08` describes is different again: a shader computing `Σ wᵢ · materialᵢ` has no
base layer to absorb a shortfall, so there `Σ = 1` is a real requirement on the data and not a
consequence of the operator.
"""
import numpy as np

import render

MASKS_SUMMING_OVER_ONE = (0.6, 0.6, 0.6)


def _effective_weights(masks, shape=(4, 4)):
    """Recover each source's effective weight by probing the compositor with a unit basis.

    Measured through `splat_blend` itself rather than derived on paper, so the numbers describe
    the operator that ships. Probing with white for one source and black for the others reads
    that source's coefficient straight out of the composite.
    """
    fields = [np.full(shape, m, dtype=float) for m in masks]
    w = []
    for k in range(len(fields)):
        probe = [(f, (255, 255, 255) if i == k else (0, 0, 0))
                 for i, f in enumerate(fields)]
        w.append(render.splat_blend(np.zeros(shape + (3,)), probe)[0, 0, 0] / 255.0)
    base = render.splat_blend(np.full(shape + (3,), 255.0),
                              [(f, (0, 0, 0)) for f in fields])[0, 0, 0] / 255.0
    return w, base


def test_the_over_composite_partitions_by_construction():
    """Effective weights sum to exactly 1 even from masks that do not."""
    w, base = _effective_weights(MASKS_SUMMING_OVER_ONE)
    total = sum(w) + base
    assert abs(total - 1.0) < 1e-12, (
        "the over-composite no longer partitions: effective weights %s plus base %.6f sum to "
        "%.12f" % (["%.6f" % x for x in w], base, total))


def test_the_base_absorbs_the_product_of_the_complements():
    """`w_base = Π(1 − mᵢ)` — the closed form behind the partition above.

    Checked separately because it is the part that explains WHY the sum is one, and a change to
    `splat_blend` could preserve the sum while changing the mechanism.
    """
    _w, base = _effective_weights(MASKS_SUMMING_OVER_ONE)
    predicted = float(np.prod([1.0 - m for m in MASKS_SUMMING_OVER_ONE]))
    assert abs(base - predicted) < 1e-12, (
        "base weight %.9f does not match Π(1−m) = %.9f" % (base, predicted))


def test_over_subscription_leaves_no_trace_in_the_output():
    """⚠️ THE ROW THAT JUSTIFIES THE ASSERTION EXISTING AT ALL.

    If over-subscribed masks produced a visible artefact, the assertion would be redundant —
    the picture would report the bug. They do not. Compare a set summing to 1.8 against a
    correctly normalised set with the SAME ordering and the same top mask: the composite is
    driven by the last mask either way, and nothing in the result records that the inputs were
    inconsistent. The conflict is resolved by compositing order, which is not a decision anyone
    made deliberately.
    """
    colours = [(200, 40, 40), (40, 200, 40), (40, 40, 200)]
    base_rgb = (128, 128, 128)
    lo = min(min(c) for c in colours + [base_rgb])
    hi = max(max(c) for c in colours + [base_rgb])

    for masks in ((0.2, 0.2, 0.2), (0.6, 0.6, 0.6), (1.0, 1.0, 1.0)):
        fields = [np.full((4, 4), m, dtype=float) for m in masks]
        out = render.splat_blend(np.full((4, 4, 3), base_rgb, dtype=float),
                                 list(zip(fields, colours)))
        w, base = _effective_weights(masks)
        # Nothing about the result distinguishes Σ = 0.6 from Σ = 3.0: the weights still sum to
        # one, and every channel still lands inside the convex hull of the colours that went in.
        # There is no out-of-range value, no dimming, no clipping — no signal at all.
        assert abs(sum(w) + base - 1.0) < 1e-12, (
            "masks summing to %.1f broke the partition" % sum(masks))
        assert out.min() >= lo - 1e-9 and out.max() <= hi + 1e-9, (
            "masks summing to %.1f pushed the composite outside the hull of its inputs "
            "[%.1f, %.1f] -> [%.3f, %.3f]; over-subscription would then be detectable "
            "downstream and the upstream assertion would be redundant"
            % (sum(masks), lo, hi, out.min(), out.max()))


def test_the_priority_stack_the_chapters_prescribe_yields_sum_le_one():
    """`06`'s remedy — each mask multiplied by `(1 − Σ previous)` — produces Σ ≤ 1, not Σ = 1.

    This is the row that settles which of the two forms the chapters should state where. The
    prescription in `06` is the `≤` form; only its headline reads as `=`.
    """
    raw = [0.6, 0.6, 0.6]
    acc, stacked = 0.0, []
    for m in raw:
        w = m * (1.0 - acc)
        stacked.append(w)
        acc += w
    total = sum(stacked)
    assert total <= 1.0 + 1e-12, "the priority stack over-subscribed: %.9f" % total
    assert total < 1.0, (
        "the priority stack summed to exactly 1 for masks %s; it should leave the remainder to "
        "the base material, which is the whole reason the chapters say ≤ and not =" % raw)
