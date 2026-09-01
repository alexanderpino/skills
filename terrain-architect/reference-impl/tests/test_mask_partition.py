"""The mask partition: `Σ ≤ 1` and `Σ = 1` are BOTH right, about different objects.

THE CONTRADICTION THIS RESOLVES. Four places in the chapters make what look like two
incompatible demands on the same quantity:

    06 "Masks must partition"                     — reads as Σ = 1
    08 "Splat weights must sum to 1"              — Σ = 1
    08 "Partitioned splat weights (must sum to 1)" — Σ = 1
    14 "assert Σ masks ≤ 1" · 00 the same         — Σ ≤ 1

A reader implementing the assertion cannot tell which to write, and `06` contradicted itself
inside one bullet: its headline said "partition" while its prescribed remedy is a priority
stack, `each subsequent mask multiplied by (1 − Σ previous)`, which produces Σ ≤ 1.

THEY ARE TWO ASSERTIONS AT TWO SITES, NOT ONE QUANTITY.

  1. RAW COVERAGE MASKS, straight off the simulations — snow, water, vegetation, debris. Each
     is an independent field in [0, 1] and NOTHING makes them sum to anything. `Σ > 1` means two
     simulations claim the same ground; `Σ < 1` is ordinary, and ANY shortfall is the base
     material's share. `Σ ≤ 1` is the assertion, and `14` puts it at the fan-in because that is
     the one place every mask passes through.

     ⚠️ `≤` AND NOT `<`. A well-formed stack that names its base as a channel reaches EXACTLY 1,
     and that is the ordinary case rather than an edge case — see
     `test_a_closed_stack_reaches_exactly_one`. Even without a closing channel,
     `[1.0, 0.6, 0.6]` and `[0.0, 0.0, 1.0]` both stack to exactly 1.0. Writing the strict form
     asserts a property of one example, not of the rule.

  2. A CLOSED STACK / `MaterialField` — a stack that has emitted its base as its own channel.
     These sum to exactly 1, and that `= 1` is a real check on the closure arithmetic. It is a
     SECOND assertion at a SECOND site, not a restatement of the first, and it is `08`'s "splat
     weights must sum to 1". `analysis.derive_materials` and `derive_substances` are both of this
     kind (`tests/test_analysis.py::test_material_masks_partition` asserts the `= 1` there); the
     over-composite arrives at the same place by construction rather than by arithmetic
     (`test_the_over_composite_partitions_by_construction`).

⚠️ AND THE REASON THE ASSERTION BELONGS UPSTREAM IS THAT ONE SHIPPING CONSUMER HIDES THE BUG
   ENTIRELY, WHILE THE OTHER REPORTS IT ONLY ON SOME DATA.

     This file used to say, flatly, that over-subscription "produces no artefact, no brightness
     error, no clue of any kind". That is FALSE as stated. It is true of exactly one operator:

       * `render.splat_blend`, an ordered over-composite (`out·(1−m) + colour·m`). Feed it masks
         summing to 1.8 and the effective weights still sum to 1.0000000000, the base absorbing
         `Π(1−mᵢ)`, and the result stays inside the convex hull of its inputs. THIS PATH CANNOT
         REPORT THE BUG — the compositing ORDER silently arbitrates the conflict.

       * `render.material_rgb`, the base-less weighted sum `Σ wᵢ·materialᵢ`, CAN report it — it
         has no base to absorb the excess, so the excess goes out of range. It ships in the same
         module, `GROUNDING.md` names it the DEFAULT colorizer, and `gallery.py` and
         `graph_demo.py` feed `06` masks straight into it with no compositing stage between.

         ⚠️ BUT IT REPORTS ONLY WHERE THE PALETTE HAS NO HEADROOM, AND THIS FILE OVERSTATED IT.
         The measurement below was made with `LIGHT_PALETTE` (min channel 200), where Σ = 1.8
         drives channels to [369 380 401] and clips to [255 255 255] — three symptoms at once.
         The SHIPPED call path passes NO palette (`gallery.py:117`, `graph_demo.py:434`), so it
         gets `render._MATERIAL_PALETTE`, where a cell of rock (max channel 120) stays in range
         until Σ = 2.13 and 4 of the 15 single-and-pair material combinations are SILENT at that
         same Σ = 1.8. `test_material_rgb_detects_over_subscription_only_where_the_palette_has_
         no_headroom` records the threshold per material on both shipped palettes, and
         `test_a_producer_bug_ships_entirely_in_gamut_through_the_shipped_palette` walks a real
         `derive_materials` bug (Σ = 2.00 everywhere) through to an export with 0 of 4096 pixels
         clipped. Note also that only the CLIP is self-evident: the "brightness error" half needs
         a reference image to be an error at all, and nobody exporting a splatmap has one.

     So whether the defect is visible depends on WHICH COMPOSITOR A CONSUMER PICKED — and, given
     the reporting one, on which palette it was handed. A producer cannot know either, which is
     precisely why the assertion belongs at the fan-in — one place, independent of the consumer —
     rather than in whichever compositor happens to be wired up. That argument is strictly
     stronger than both the old one (which rested on a claim the very next module falsifies) and
     the unconditional "and loudly" that replaced it: a detector that fires on some palettes and
     not others is an argument FOR checking upstream, not a substitute for it.

     ⚠️ AND `material_rgb` MUST NOT BE "FIXED" TO NORMALISE. Partial as it is, it is the only
     downstream detector of a partition bug anywhere in this tree. Normalising it would make the
     old "no artefact" sentence true by destroying the only signal that exists.
"""
import itertools

import numpy as np
import pytest

import analysis
import render

MASKS_SUMMING_OVER_ONE = (0.6, 0.6, 0.6)

# A realistic light-terrain palette: pale rock / snow / scree, the regime where over-brightening
# actually clips. A darker palette hides the defect behind headroom, which is the point —
# the bug's visibility is a property of the data as well as of the operator.
#
# ⚠️ AND THIS IS NOT THE PALETTE THE SHIPPED CALL PATH USES. `gallery.py:117` and
# `graph_demo.py:434` pass no palette at all, so they get `render._MATERIAL_PALETTE`, which is
# darker and therefore a weaker detector. Every row that quotes a number off LIGHT_PALETTE is
# quoting a best case; the shipped case is measured in
# `test_material_rgb_detects_over_subscription_only_where_the_palette_has_no_headroom`.
LIGHT_PALETTE = np.array([[205.0, 210.0, 220.0],
                          [210.0, 216.0, 228.0],
                          [200.0, 207.0, 221.0]])


def _sneaky_blend(base_rgb, overlays):
    """An over-composite plus a CHROMA-dependent nonlinearity — the identity on greys.

    ⚠️ THIS EXISTS TO PROVE THE SUPERPOSITION ROW BELOW IS LOAD-BEARING. `_effective_weights`
    probes with white-and-black sources over a black or white base, so every value it ever reads
    is a GREY, and it reads one channel of it. Any nonlinearity that vanishes on greys is
    therefore invisible to the probe: this operator reports weights identical to `splat_blend`'s
    to the last bit, and satisfies every row that reads those weights — while pushing a coloured
    composite outside the convex hull of its inputs.

    The probe recovers effective weights GIVEN that the operator is affine in colour. Without
    that premise it recovers only "what the operator does to greys", which is a much weaker
    statement than the rows above it are making.
    """
    out = render.splat_blend(base_rgb, overlays)
    chroma = out.max(axis=-1, keepdims=True) - out.min(axis=-1, keepdims=True)
    return out + 0.6 * chroma * np.sin(np.pi * np.clip(out, 0.0, 255.0) / 255.0)


def _effective_weights(masks, shape=(4, 4), op=render.splat_blend):
    """Recover each source's effective weight by probing the compositor with a unit basis.

    Measured through `splat_blend` itself rather than derived on paper, so the numbers describe
    the operator that ships. Probing with white for one source and black for the others reads
    that source's coefficient straight out of the composite.

    ⚠️ THE PROBE IS ONLY VALID FOR A COLOUR-AFFINE OPERATOR, AND THAT PREMISE IS MEASURED, NOT
    ASSUMED. It evaluates the operator at two colours (black and white) and reads one channel;
    that recovers a coefficient only if the operator is affine in colour and acts channelwise.
    `test_splat_blend_is_affine_in_colour_so_this_probe_recovers_weights` establishes exactly
    that for `render.splat_blend`, and `_sneaky_blend` above is the counterexample showing what
    the probe misses without it. Cite that row before trusting any number this function returns.
    """
    fields = [np.full(shape, m, dtype=float) for m in masks]
    w = []
    for k in range(len(fields)):
        probe = [(f, (255, 255, 255) if i == k else (0, 0, 0))
                 for i, f in enumerate(fields)]
        w.append(op(np.zeros(shape + (3,)), probe)[0, 0, 0] / 255.0)
    base = op(np.full(shape + (3,), 255.0),
              [(f, (0, 0, 0)) for f in fields])[0, 0, 0] / 255.0
    return w, base


def _composite(base_rgb, masks, colours, shape=(4, 4), op=render.splat_blend):
    fields = [np.full(shape, m, dtype=float) for m in masks]
    base = np.zeros(shape + (3,)) + np.asarray(base_rgb, dtype=float)
    return op(base, list(zip(fields, colours)))


def _superposition_residual(op, masks=MASKS_SUMMING_OVER_ONE, seed=0):
    """Max violation of `op(αX + βY) = α·op(X) + β·op(Y)` over the (base, colours) inputs."""
    rng = np.random.default_rng(seed)
    worst = 0.0
    for _ in range(24):
        a, b = rng.uniform(-1.5, 1.5, 2)
        base1, base2 = rng.uniform(0, 255, 3), rng.uniform(0, 255, 3)
        col1 = rng.uniform(0, 255, (len(masks), 3))
        col2 = rng.uniform(0, 255, (len(masks), 3))
        lhs = _composite(a * base1 + b * base2, masks, a * col1 + b * col2, op=op)
        rhs = (a * _composite(base1, masks, col1, op=op)
               + b * _composite(base2, masks, col2, op=op))
        worst = max(worst, float(np.abs(lhs - rhs).max()))
    return worst


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


def test_splat_blend_is_affine_in_colour_so_this_probe_recovers_weights():
    """⚠️ THE PREMISE `_effective_weights` RESTS ON, MEASURED RATHER THAN ASSUMED.

    The probe evaluates the compositor at black and white and reads one channel. That recovers a
    coefficient only if the operator is affine in colour and acts channel by channel — otherwise
    it recovers "what the operator does to greys" and the rows above it are asserting something
    much weaker than they appear to.

    Two things are established here. (1) SUPERPOSITION: with the masks held fixed,
    `op(αX + βY) = α·op(X) + β·op(Y)` over both the base and the overlay colours, so the operator
    is a linear map on colour and a probe with a unit basis reads its coefficients exactly.
    (2) CHANNEL SEPARABILITY: permuting the colour channels of every input permutes the output's
    channels, so reading channel 0 is reading the whole story.

    And the row is proved load-bearing rather than decorative: `_sneaky_blend` reports weights
    IDENTICAL to `splat_blend`'s — the probe cannot tell them apart — yet fails superposition by
    a wide margin. Every row that consumes `_effective_weights` would pass on it.
    """
    residual = _superposition_residual(render.splat_blend)
    assert residual < 1e-9, (
        "render.splat_blend is no longer affine in colour (worst superposition violation %.3e); "
        "_effective_weights probes it at two colours and reads one channel, which recovers "
        "weights ONLY for a colour-affine operator. Fix the probe, not this row." % residual)

    # channel separability: a permutation of the input channels permutes the output's
    rng = np.random.default_rng(7)
    base = rng.uniform(0, 255, 3)
    colours = rng.uniform(0, 255, (len(MASKS_SUMMING_OVER_ONE), 3))
    perm = [2, 0, 1]
    straight = _composite(base, MASKS_SUMMING_OVER_ONE, colours)[..., perm]
    permuted = _composite(base[perm], MASKS_SUMMING_OVER_ONE, colours[:, perm])
    assert np.abs(straight - permuted).max() < 1e-9, (
        "render.splat_blend mixes colour channels, so reading channel 0 of a grey probe no "
        "longer recovers a per-source weight")

    # the counterexample: identical weights, not affine
    w_real, base_real = _effective_weights(MASKS_SUMMING_OVER_ONE)
    w_fake, base_fake = _effective_weights(MASKS_SUMMING_OVER_ONE, op=_sneaky_blend)
    assert np.allclose(w_real, w_fake, atol=0, rtol=0) and base_real == base_fake, (
        "_sneaky_blend was supposed to be probe-indistinguishable from splat_blend; if it is "
        "not, this row no longer demonstrates that the probe needs the affinity premise")
    fake_residual = _superposition_residual(_sneaky_blend)
    assert fake_residual > 1.0, (
        "_sneaky_blend now satisfies superposition (%.3e), so it no longer demonstrates what "
        "the probe misses" % fake_residual)


def test_over_subscription_changes_the_composite_but_never_malforms_it():
    """⚠️ WHAT THE OVER-COMPOSITE ACTUALLY DOES WITH OVER-SUBSCRIBED MASKS.

    THIS ROW USED TO BE UNFALSIFIABLE. It asserted (a) that the effective weights sum to 1 and
    (b) that the composite stays inside the convex hull of its inputs — but both are THEOREMS
    about `splat_blend` for every input whatsoever: it clips `m` to [0, 1] and each step is a
    convex combination, so the result is inside the hull by construction. 200 000 random trials
    gave a worst hull violation of 0.000e+00. No mask set could ever have failed it, and it did
    not perform the comparison its own docstring described.

    What is actually worth asserting is the pair of facts that make the upstream assertion
    necessary: an over-subscribed mask set and its priority-stacked correction produce DIFFERENT
    PICTURES — so the bug does change the output — while BOTH remain perfectly well-formed under
    this operator, so nothing about either picture says which one you are looking at. The
    difference is arbitrated by compositing ORDER, a decision nobody made deliberately.

    The row that carries the real finding is
    `test_material_rgb_over_brightens_and_clips_when_the_masks_over_subscribe`: under a different
    shipping consumer the same defect is a hard clip.
    """
    colours = [(200, 40, 40), (40, 200, 40), (40, 40, 200)]
    base_rgb = (128, 128, 128)
    lo = min(min(c) for c in colours + [base_rgb])
    hi = max(max(c) for c in colours + [base_rgb])

    raw = MASKS_SUMMING_OVER_ONE
    stacked = _priority_stack(raw)
    assert sum(raw) > 1.0 and sum(stacked) <= 1.0 + 1e-12, "the fixture stopped being a fixture"

    over = _composite(base_rgb, raw, colours)
    fixed = _composite(base_rgb, stacked, colours)

    # 1. the defect DOES change the picture — over-subscription is not a no-op
    delta = float(np.abs(over - fixed).max())
    assert delta > 1.0, (
        "the over-subscribed composite (Σ=%.2f) is indistinguishable from its priority-stacked "
        "correction (Σ=%.2f): max channel difference %.6f. If the two really coincide there is "
        "no bug to assert against upstream, and `14`'s fan-in check should be removed."
        % (sum(raw), sum(stacked), delta))

    # 2. ...yet neither picture reports which one it is: both stay well-formed under THIS operator
    for masks, out, label in ((raw, over, "over-subscribed"), (stacked, fixed, "priority-stacked")):
        w, base = _effective_weights(masks)
        assert abs(sum(w) + base - 1.0) < 1e-12, (
            "%s masks summing to %.2f broke the partition" % (label, sum(masks)))
        assert out.min() >= lo - 1e-9 and out.max() <= hi + 1e-9, (
            "%s masks summing to %.2f pushed the composite outside the hull of its inputs "
            "[%.1f, %.1f] -> [%.3f, %.3f]" % (label, sum(masks), lo, hi, out.min(), out.max()))


def test_material_rgb_over_brightens_and_clips_when_the_masks_over_subscribe():
    """⚠️ THE ROW THAT JUSTIFIES THE ASSERTION EXISTING AT ALL — and it is not `splat_blend`.

    `render.material_rgb` is the base-less weighted sum `Σ wᵢ·materialᵢ`. `08` used to describe
    that shader as a hypothetical third case; it is not. It ships in `render.py` beside
    `splat_blend`, `GROUNDING.md` names it the DEFAULT colorizer, and `gallery.py:117` and
    `graph_demo.py:434` feed `06` masks straight into it with no compositing stage between.

    With a partition (Σ = 1) it is a convex combination and lands inside the palette's hull, with
    no clipping. Over-subscribed (Σ = 1.8) the same code drives every channel past 255 and the
    output clips — a rescale, a brightness error and an out-of-range value, the three things the
    chapters used to say could not happen.

    ⚠️ THIS ROW IS THE BEST CASE, NOT THE SHIPPED CASE, AND IT IS WHERE THIS FILE OVERSTATED
    ITSELF. It pins `LIGHT_PALETTE`, whose dimmest channel is 200, so every material in it is
    out of range by Σ = 1.28. The palette the shipped call path actually gets is darker and says
    nothing at this same Σ for several material mixes:
    `test_material_rgb_detects_over_subscription_only_where_the_palette_has_no_headroom` and
    `test_a_producer_bug_ships_entirely_in_gamut_through_the_shipped_palette` are the rows that
    scope this one. Read alone, this row reads as a guarantee it cannot give.

    ⚠️ THE FIX IS NOT TO NORMALISE `material_rgb`. Partial as it is, it is the only downstream
    detector of a partition bug in this tree; normalising it would make the old sentence true by
    destroying the only signal that exists. The masks are fixed upstream, at the fan-in, once.
    """
    shape = (4, 4)

    def stack(masks):
        return np.stack([np.full(shape, m, dtype=float) for m in masks])

    def unclipped(masks):
        s = np.moveaxis(stack(masks), 0, -1)
        return np.tensordot(s, LIGHT_PALETTE, axes=([2], [0]))

    normalised = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    over = MASKS_SUMMING_OVER_ONE

    u_norm = unclipped(normalised)
    s_norm = render.material_rgb(stack(normalised), palette=LIGHT_PALETTE)
    assert u_norm.max() <= 255.0 + 1e-9, (
        "the Σ=1 fixture already exceeds 255 (%.1f); pick a palette inside range or this row "
        "proves nothing" % u_norm.max())
    assert np.abs(u_norm - s_norm.astype(float)).max() <= 1.0, (
        "with Σ = 1.00 material_rgb should reproduce the weighted sum to within rounding: "
        "unclipped %s vs shipped %s" % (u_norm[0, 0], s_norm[0, 0]))
    assert LIGHT_PALETTE.min() - 1e-9 <= u_norm.min() and u_norm.max() <= LIGHT_PALETTE.max() + 1e-9, (
        "with Σ = 1.00 the weighted sum should be a convex combination, inside the palette hull")

    u_over = unclipped(over)
    s_over = render.material_rgb(stack(over), palette=LIGHT_PALETTE)
    assert abs(sum(over) - 1.8) < 1e-9, "the over-subscription fixture drifted off Σ = 1.8"
    assert u_over.min() > 255.0, (
        "masks summing to %.2f no longer drive material_rgb past 255 on this palette (min "
        "channel %.1f); the downstream detector is gone and `14`'s upstream assertion is now "
        "the only thing standing between a partition bug and the export"
        % (sum(over), u_over.min()))
    assert (s_over == 255).all(), (
        "the weighted sum reaches %s but material_rgb shipped %s without clipping — check "
        "whether it started normalising, which would destroy the only signal there is"
        % (u_over[0, 0], s_over[0, 0]))
    assert np.abs(u_over - s_over.astype(float)).max() > 50.0, (
        "clipping is supposed to LOSE information here; unclipped %s vs shipped %s"
        % (u_over[0, 0], s_over[0, 0]))

    # and the two rescale relative to one another: the same palette, a different brightness
    assert s_over.astype(float).mean() > s_norm.astype(float).mean() + 20.0, (
        "over-subscription no longer changes material_rgb's brightness (%.1f vs %.1f)"
        % (s_over.astype(float).mean(), s_norm.astype(float).mean()))

    # ⚠️ THE EXACT TRIPLES `06`, `08` AND `14` QUOTE. Pinned here so a palette tweak or a change
    # in material_rgb cannot leave three chapters quoting numbers nothing produces any more.
    assert np.allclose(np.round(u_norm[0, 0]), [205, 211, 223]), (
        "the chapters quote Σ=1.00 -> unclipped [205 211 223]; this palette now gives %s"
        % np.round(u_norm[0, 0], 1))
    assert list(s_norm[0, 0]) == [204, 211, 222], (
        "the chapters quote Σ=1.00 -> shipped [204 211 222]; got %s" % list(s_norm[0, 0]))
    assert np.allclose(np.round(u_over[0, 0]), [369, 380, 401]), (
        "the chapters quote Σ=1.80 -> unclipped [369 380 401]; this palette now gives %s"
        % np.round(u_over[0, 0], 1))
    assert list(s_over[0, 0]) == [255, 255, 255], (
        "the chapters quote Σ=1.80 -> shipped [255 255 255]; got %s" % list(s_over[0, 0]))


# --------------------------------------------------------------------------------------------- #
# THE SCOPE OF THE DETECTOR: the two rows below are what keeps the row above from overstating.
# --------------------------------------------------------------------------------------------- #
SHIPPED_PALETTES = (("render._MATERIAL_PALETTE", render._MATERIAL_PALETTE, analysis.MATERIAL_NAMES),
                    ("render._SUBSTANCE_PALETTE", render._SUBSTANCE_PALETTE, analysis.SUBSTANCE_NAMES))

# ⚠️ MEASURED, NOT COPIED. `_measure_clip_threshold` below re-derives every one of these numbers
# through `render.material_rgb` itself; they are recorded here so a palette edit that weakens the
# detector fails a row instead of quietly widening the blind spot. A cell made ENTIRELY of one
# material leaves 8-bit range at Σ = 255 / max(channel):
#
#     snow 1.02 · sediment/sand 1.28 · water 1.50 · scree 1.68 · vegetation/grass 1.93 ·
#     ground 2.06 · rock 2.13
#
# The headline Σ = 1.80 this file uses everywhere else is BELOW four of those seven thresholds.
CLIP_THRESHOLDS = {"water": 1.50, "snow": 1.02, "rock": 2.13, "sand": 1.28,
                   "grass": 1.93, "scree": 1.68, "sediment": 1.28, "vegetation": 1.93,
                   "ground": 2.06}


def _uniform_stack(weights, shape=(8, 8)):
    """A (K, H, W) stack of spatially uniform channels — one weight per palette row."""
    return np.stack([np.full(shape, w, dtype=float) for w in weights])


def _clips(weights, palette, shape=(8, 8)):
    """Does `material_rgb` land on 255 anywhere, i.e. does the detector fire? Measured through
    the shipped function, not through a re-implementation of it."""
    return bool((render.material_rgb(_uniform_stack(weights, shape),
                                     palette=np.asarray(palette, dtype=float)) == 255).any())


def _measure_clip_threshold(index, palette, eps=0.02):
    """Bracket the Σ at which an all-of-one-material cell starts clipping, through material_rgb."""
    k = len(palette)
    star = 255.0 / max(palette[index])
    below = [0.0] * k
    below[index] = star - eps
    above = [0.0] * k
    above[index] = star + eps
    assert not _clips(below, palette) and _clips(above, palette), (
        "the clip threshold for palette row %d is not at Σ = %.4f after all" % (index, star))
    return star


def test_material_rgb_detects_over_subscription_only_where_the_palette_has_no_headroom():
    """⚠️ THE HEDGE THAT BELONGS IN THE HEADER, NOT IN A FIXTURE COMMENT.

    `test_material_rgb_over_brightens_and_clips_when_the_masks_over_subscribe` measures the
    detector on `LIGHT_PALETTE`, a pale palette whose dimmest channel is 200. The SHIPPED call
    path — `gallery.py:117`, `graph_demo.py:434` — passes no palette at all and gets
    `render._MATERIAL_PALETTE` (or, for a seven-channel substance stack,
    `render._SUBSTANCE_PALETTE`). Those are terrain colours, not paper-white, and a weighted sum
    of them has headroom to spare.

    MEASURED HERE, through `material_rgb` itself. A cell of one material clips at
    Σ = 255 / max(channel):

        snow 1.02 · sand/sediment 1.28 · water 1.50 · scree 1.68 · grass/vegetation 1.93 ·
        ground 2.06 · rock 2.13

    So at this file's own headline Σ = 1.80, `rock`, `grass`, `water+grass` and `rock+grass` — 4
    of the 15 single-and-pair combinations of the five-material palette — produce NO clipped
    pixel at all. A partition bug on a rocky or grassy hillside is invisible to the detector this
    file calls loud, and rock is the single most common material `derive_materials` emits.

    On `LIGHT_PALETTE` all 3 singles and all 3 pairs clip at the same Σ = 1.80, which is exactly
    why the original measurement read as unconditional: it was taken on the best case available.

    This does not weaken the conclusion, it sharpens it. A detector whose sensitivity depends on
    the palette a consumer happened to pass is one more thing the producer cannot know — the same
    argument as `splat_blend`'s silence, one level in. The assertion still belongs at the fan-in.
    """
    for label, palette, names in SHIPPED_PALETTES:
        assert len(palette) == len(names), (
            "%s has %d colours but %s names %d substances; material_rgb selects the palette by "
            "channel count, so these must stay in step"
            % (label, len(palette), names, len(names)))
        for i, name in enumerate(names):
            star = _measure_clip_threshold(i, palette)
            assert abs(star - CLIP_THRESHOLDS[name]) < 0.01, (
                "%s: '%s' now clips at Σ = %.4f, not the recorded %.2f. Re-measure the table in "
                "this file, in `06`, `08` and `14` — a darker colour here widens the detector's "
                "blind spot and a brighter one narrows it."
                % (label, name, star, CLIP_THRESHOLDS[name]))

    # ...and the consequence at the headline Σ, enumerated over single materials and pairs.
    sigma = 1.80
    pal = render._MATERIAL_PALETTE
    names = analysis.MATERIAL_NAMES
    silent = []
    for combo in list(itertools.combinations(range(len(pal)), 1)) \
            + list(itertools.combinations(range(len(pal)), 2)):
        w = [0.0] * len(pal)
        for i in combo:
            w[i] = sigma / len(combo)
        if not _clips(w, pal):
            silent.append("+".join(names[i] for i in combo))
    assert silent == ["rock", "grass", "water+grass", "rock+grass"], (
        "the shipped palette's blind spot at Σ = %.2f moved: %s. The header, `06`, `08` and `14` "
        "all quote 'rock, grass, water+grass, rock+grass — 4 of 15'; re-measure them."
        % (sigma, silent))

    # the contrast that makes the point: on the pale palette the same Σ is caught every time
    light = [tuple(c) for c in LIGHT_PALETTE]
    light_silent = [c for c in (list(itertools.combinations(range(3), 1))
                                + list(itertools.combinations(range(3), 2)))
                    if not _clips([sigma / len(c) if i in c else 0.0 for i in range(3)], light)]
    assert light_silent == [], (
        "LIGHT_PALETTE stopped catching Σ = %.2f everywhere (%s); the row above it depends on "
        "this palette being the best case." % (sigma, light_silent))


def _steep_hillside(n=64, cellsize=10.0):
    """A uniformly 45° hillside falling south, with hillslope-scale drainage areas.

    Nothing exotic: rock claims almost every cell (`derive_materials` puts bedrock above 33°),
    a few cells drain enough to be water, and there is no snow (no relief for a snowline) and no
    sand (too steep). It is the most ordinary terrain in this file.
    """
    yy, _xx = np.mgrid[0:n, 0:n].astype(float)
    h = (n - 1 - yy) * cellsize * np.tan(np.radians(45.0))
    area = np.exp(np.random.default_rng(0).normal(0.0, 1.0, (n, n))) * cellsize * cellsize
    return h, analysis.slope(h, cellsize), area, cellsize


def _mixed_alpine(n=64, cellsize=30.0):
    """A peak with real drainage: snow above the snowline, rock on the faces, grass below."""
    import flow
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = (900.0 * np.exp(-(((xx - 32) ** 2 + (yy - 30) ** 2) / 700.0))
         + 260.0 * np.exp(-(((xx - 14) ** 2 + (yy - 44) ** 2) / 900.0))
         + 30.0 * np.sin(xx / 5.0) * np.cos(yy / 6.0) + rng.normal(0.0, 8.0, (n, n)))
    area = flow.d8_accumulation(flow.priority_flood_fill(h), cellsize)
    return h, analysis.slope(h, cellsize), area, cellsize


def _closing_channel_written_as_a_constant(stack, height):
    """THE BUG: `derive_materials`' closing channel written `1.0` instead of `1 − claimed`.

    One line, and the kind of line a reader writes from the prose rather than the arithmetic —
    "the base material takes the rest" misread as "the base material is everywhere". The priority
    stack above it is untouched and still sums to ≤ 1, so nothing upstream of the closure looks
    wrong; the stack simply stops being a partition.
    """
    return stack[:-1] + [(stack[-1][0], np.ones_like(height))]


def test_a_producer_bug_ships_entirely_in_gamut_through_the_shipped_palette():
    """⚠️ THE BLIND SPOT IS REACHABLE FROM THE REAL PRODUCER, NOT ONLY FROM A HAND-BUILT FIXTURE.

    `analysis.derive_materials` with its closing channel written as a constant `1.0` instead of
    `1 − claimed` over-subscribes by exactly 2.00× everywhere. Run that through the shipped call
    path — `material_rgb` with no palette, i.e. `render._MATERIAL_PALETTE` — on an ordinary steep
    hillside and the export is `[216 250 188]`, a pale sage: IN GAMUT, 0 of 4096 pixels clipped,
    nothing to see. Twice the correct mask weight, and the "loud" detector says nothing.

    The same bug on a mixed alpine fixture clips ~279 of 4096 pixels, and the clipped cells are
    the SNOW cells (mean snow weight 0.61 there against 0.011 elsewhere): snow's threshold is
    1.02, so any over-subscription at all shows on snow. Note the severity is inverted — the
    hillside is over-subscribed 2.00× and silent, the alpine 1.64× on average and loud. What the
    detector measures is the palette under the bug, not the size of the bug.

    That is the whole argument for the fan-in assertion, in one producer: the bug is the same,
    the export is the same code, and whether anyone ever sees it depends on what the terrain
    happened to be made of.
    """
    pal = np.asarray(render._MATERIAL_PALETTE, dtype=float)

    def broken(fixture):
        h, s, area, cs = fixture
        stack = _closing_channel_written_as_a_constant(
            analysis.derive_materials(h, s, area, cs, rng_seed=0), h)
        masks = np.stack([m for _, m in stack])
        unclipped = np.tensordot(np.moveaxis(masks, 0, -1), pal, axes=([2], [0]))
        shipped = render.material_rgb(masks)
        return dict(zip([n for n, _ in stack], masks)), masks, unclipped, shipped

    # 1. the ordinary hillside: a 2.00x partition bug, exported entirely in gamut
    named, masks, unclipped, shipped = broken(_steep_hillside())
    sigma = masks.sum(axis=0)
    assert abs(sigma.min() - 2.0) < 1e-9 and abs(sigma.max() - 2.0) < 1e-9, (
        "the fixture stopped over-subscribing by exactly 2.00x (Σ ∈ [%.4f, %.4f]); it is meant "
        "to be the WORST partition bug in this file, not a marginal one"
        % (sigma.min(), sigma.max()))
    assert named["snow"].max() == 0.0 and named["sand"].max() == 0.0, (
        "the hillside grew snow (%.3f) or sand (%.3f); those are the two materials with enough "
        "brightness to trip the detector, and this fixture exists to be the case without them"
        % (named["snow"].max(), named["sand"].max()))
    clipped = int((unclipped > 255.0).any(axis=-1).sum())
    assert clipped == 0, (
        "%d of %d pixels now clip on the shipped palette at Σ = 2.00. If that is a palette "
        "change it is an improvement — re-measure the thresholds table; if it is material_rgb "
        "normalising, the only detector in the tree is gone." % (clipped, sigma.size))
    assert unclipped.max() <= 255.0 and shipped.max() < 255, (
        "the in-gamut claim: the weighted sum peaks at %.1f and ships %d, so nothing about the "
        "exported image says the masks were doubled" % (unclipped.max(), shipped.max()))
    modal = list(shipped[shipped.shape[0] // 2, shipped.shape[1] // 2])
    assert modal == [216, 250, 188], (
        "the chapters quote the doubled rock+grass cell as the pale sage [216 250 188]; got %s"
        % modal)

    # 2. ...and the same bug where snow carries weight: loud, on the same palette
    named_a, masks_a, unclipped_a, _shipped_a = broken(_mixed_alpine())
    clip_mask = (unclipped_a > 255.0).any(axis=-1)
    n_clipped = int(clip_mask.sum())
    assert n_clipped > 0.05 * clip_mask.size, (
        "the alpine fixture clipped %d of %d pixels (measured: 279); with snow on the ground the "
        "detector is supposed to be strong, and if it is not, no palette catches this bug at all"
        % (n_clipped, clip_mask.size))
    assert named_a["snow"][clip_mask].mean() > 10.0 * named_a["snow"][~clip_mask].mean(), (
        "the clipped cells are no longer the snow cells (%.3f vs %.3f), so the explanation in "
        "this docstring — that snow's Σ = 1.02 threshold is what fires — no longer holds"
        % (named_a["snow"][clip_mask].mean(), named_a["snow"][~clip_mask].mean()))
    assert masks_a.sum(axis=0).mean() < sigma.mean(), (
        "the alpine fixture is now over-subscribed harder (%.3f) than the silent hillside "
        "(%.3f); the point of the pair is that the LESS broken one is the one that shows"
        % (masks_a.sum(axis=0).mean(), sigma.mean()))


def _priority_stack(raw):
    """`06`'s remedy: each mask multiplied by `(1 − Σ previous)`."""
    acc, stacked = 0.0, []
    for m in raw:
        w = m * (1.0 - acc)
        stacked.append(w)
        acc += w
    return stacked


# Mask sets whose priority stack lands on exactly 1.0, and sets that stay strictly below it.
# ⚠️ THE ROW BELOW USED TO ASSERT A STRICT `< 1.0` ON `[0.6, 0.6, 0.6]` ALONE. That is a property
# of the example, not of the prescription: `[1.0, 0.6, 0.6]` and `[0.0, 0.0, 1.0]` stack to
# exactly 1.0, because a mask of 1.0 anywhere claims the whole cell and leaves no remainder.
# Worse, the repo's own implementation of this prescription CLOSES to 1 deliberately —
# `analysis.derive_materials` appends `("grass", 1.0 - claimed)` — so `test_analysis.py`'s
# partition row asserted the opposite of this one, on the same object, in the same suite.
_STACKS_TO_EXACTLY_ONE = [
    (1.0, 0.6, 0.6),
    (0.0, 0.0, 1.0),
    (1.0,),
    (0.5, 1.0, 0.3),
]
_STACKS_STRICTLY_BELOW_ONE = [
    (0.6, 0.6, 0.6),
    (0.2, 0.2, 0.2),
    (0.99, 0.99),
    (0.0, 0.0, 0.0),
]


@pytest.mark.parametrize("raw", _STACKS_TO_EXACTLY_ONE + _STACKS_STRICTLY_BELOW_ONE)
def test_the_priority_stack_the_chapters_prescribe_yields_sum_le_one(raw):
    """`06`'s remedy — each mask multiplied by `(1 − Σ previous)` — produces Σ ≤ 1.

    This is the row that settles which of the two forms the chapters should state where, and the
    bound is `≤`, not `<`. Parametrised over sets that reach exactly 1.0 as well as sets that
    stay under it, so the assertion is about the prescription rather than about one example.
    """
    total = sum(_priority_stack(raw))
    assert total <= 1.0 + 1e-12, (
        "the priority stack over-subscribed for masks %s: %.15f" % (list(raw), total))


@pytest.mark.parametrize("raw", _STACKS_STRICTLY_BELOW_ONE)
def test_a_priority_stack_of_masks_all_below_one_leaves_a_remainder(raw):
    """The strict `< 1` holds only when EVERY mask is strictly below 1 — the base's share.

    Kept as a separate row over a separate fixture set, because that is the honest scope of the
    claim. Merging it back into the row above is how the `< 1.0` bug reappears.
    """
    assert all(m < 1.0 for m in raw), "fixture error: this set must be strictly below 1"
    total = sum(_priority_stack(raw))
    assert total < 1.0, (
        "the priority stack of %s summed to exactly 1 although no mask reaches 1; with the base "
        "implicit there should be a remainder left for it" % list(raw))


def test_a_closed_stack_reaches_exactly_one():
    """⚠️ THE SECOND ASSERTION, AT THE SECOND SITE — `Σ = 1` where the stack is CLOSED.

    `06` prescribes `Σ ≤ 1` at the mask fan-in, where the base is implicit. The moment a stack
    emits its base AS A CHANNEL it is a different object — `14`'s `MaterialField` — and the
    assertion becomes `Σ = 1`, a real check on the closure arithmetic rather than a restatement.
    `analysis.derive_materials` and `derive_substances` both do exactly that, appending
    `(base, 1 − claimed)`, so they reach 1.0 everywhere.

    Stating it as two assertions at two sites is what makes the two-stage claim CHECKABLE rather
    than rhetorical: this row and
    `test_the_priority_stack_the_chapters_prescribe_yields_sum_le_one` are both true, of
    different objects, and neither contradicts the other.
    """
    n, cs = 32, 20.0
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:n, 0:n].astype(float)
    h = 40.0 * np.exp(-((xx - 16) ** 2 + (yy - 16) ** 2) / 240.0) + rng.uniform(0, 4, (n, n))
    s = analysis.slope(h, cellsize=cs)
    area = np.abs(rng.normal(0, 1, (n, n))).cumsum().reshape(n, n) * cs * cs

    stacks = {
        "derive_materials": analysis.derive_materials(h, s, area, cs),
        "derive_substances": analysis.derive_substances(
            h, s, area, cs, climate={"has_water": True, "has_snow": True, "has_veg": True}),
    }
    for label, stack in stacks.items():
        total = sum(m for _name, m in stack)
        assert np.abs(total - 1.0).max() < 1e-9, (
            "%s is a CLOSED stack (it appends the base as a channel), so it must sum to exactly "
            "1; worst deviation %.3e. If it is meant to leave the base implicit, it belongs "
            "under the Σ ≤ 1 assertion instead — but it cannot be both."
            % (label, float(np.abs(total - 1.0).max())))

        # ...and the open stack it is built from — every channel but the closing one — is ≤ 1,
        # which is the SAME numbers satisfying the OTHER assertion. Two sites, one pipeline.
        open_total = sum(m for _name, m in stack[:-1])
        assert open_total.max() <= 1.0 + 1e-9, (
            "%s's stack before its closing channel over-subscribes (max %.9f)"
            % (label, float(open_total.max())))
