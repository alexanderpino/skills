"""The hydraulic jump: white water that STANDS instead of travelling.

WHY THIS IS NOT A WAVE SECTION. Everything else in this skill describes water
that moves through the scene -- swell, surf, wakes, capillary rings. A rapid, a
weir and a spillway are the opposite: the water moves and the STRUCTURE does
not. A flow-mapped river surface scrolls texture over a bed and can never
produce one, so white water in rapids ends up hand-painted where it should fall
out of the flow field. Painted white water is the tell: it does not move when
the discharge changes, and it sits in the wrong place when the level does.

THE MECHANISM IN ONE SENTENCE. Where fast shallow flow (`Fr > 1`, supercritical
-- disturbances cannot travel upstream) meets slow deep flow (`Fr < 1`), the
transition cannot be gradual, because there is no steady profile connecting
them: the flow jumps, and the energy that cannot be carried across is dissipated
in place as turbulence and entrained air.

SOURCE. The momentum relation across the jump is Belanger's (`P`); the
conjugate-depth form below is its standard statement. ⚠️ It NEGLECTS BED
ROUGHNESS, and a rapid is the roughest bed there is -- so it gives the geometry
of the jump and overstates the energy that survives it. That limitation travels
with every number here.
"""
import numpy as np

G = 9.80665


def froude(u, depth, g=G):
    """`Fr = U / sqrt(g h)` -- flow speed against shallow-water wave speed.

    THE ONE NUMBER, and its meaning is kinematic rather than energetic: shallow
    water waves travel at `sqrt(g h)`, so `Fr > 1` means the flow outruns its
    own disturbances and nothing downstream can signal upstream. That is what
    makes the transition abrupt.
    """
    return np.asarray(u, float) / np.sqrt(float(g) * np.asarray(depth, float))


def critical_depth(q, g=G):
    """`h_c = (q^2/g)^(1/3)` for unit discharge `q` -- where `Fr = 1`."""
    return (np.asarray(q, float) ** 2 / float(g)) ** (1.0 / 3.0)


def conjugate_depth(h1, fr1):
    """Belanger: the depth downstream of a jump.

        `h2/h1 = (1/2) * (-1 + sqrt(1 + 8 Fr1^2))`

    DERIVED FROM MOMENTUM, NOT ENERGY, and that is the whole point. Energy is
    NOT conserved across a jump -- that is what a jump is for -- so the closure
    has to be the momentum flux plus pressure force, which survives the
    dissipation. A model that conserves energy here produces no jump at all and
    quietly returns the upstream depth.
    """
    h1 = np.asarray(h1, float)
    fr1 = np.asarray(fr1, float)
    return 0.5 * h1 * (-1.0 + np.sqrt(1.0 + 8.0 * fr1 * fr1))


def specific_energy(h, q, g=G):
    """`E = h + q^2/(2 g h^2)` -- depth plus velocity head, per unit weight."""
    h = np.asarray(h, float)
    return h + np.asarray(q, float) ** 2 / (2.0 * float(g) * h * h)


def energy_loss(h1, h2):
    """Energy dissipated across the jump, in metres of head.

        `dE = (h2 - h1)^3 / (4 h1 h2)`

    A CUBE, and that is the number that says why strong jumps are violent out
    of proportion to their size: doubling the depth ratio costs eight times the
    head. This is the term that feeds the aerated-water sections -- the
    dissipated head is what becomes entrained air, and it is a rate rather than
    a mask.
    """
    h1 = np.asarray(h1, float)
    h2 = np.asarray(h2, float)
    return (h2 - h1) ** 3 / (4.0 * h1 * h2)


def jump_class(fr1):
    """The standard classification by upstream Froude number.

    The classes are worth carrying because they are a LOOK, not a taxonomy:
    each one names what the surface does, and a renderer that draws the same
    white water for all of them is drawing one of five things.
    """
    fr = float(fr1)
    if fr < 1.0:
        return 'no jump (subcritical)'
    if fr < 1.7:
        return 'undular -- standing waves, no roller, little air'
    if fr < 2.5:
        return 'weak -- a smooth roller forms, surface stays fairly flat'
    if fr < 4.5:
        return 'oscillating -- the jet wanders, irregular surface waves travel down'
    if fr < 9.0:
        return 'steady -- well-defined roller, the classic rapid, strong aeration'
    return 'strong -- rough, violent, heavy spray'


def roller_length(h1, h2, c=6.0):
    """Length of the surface roller: `L ~ C (h2 - h1)`.

    The along-stream extent of the white water, which is what a foam mask needs
    and what a scrolling texture cannot know. `C` is an experimental constant
    near 6; it is an argument, and the suite checks the SCALING.
    """
    return float(c) * (np.asarray(h2, float) - np.asarray(h1, float))


def aeration_rate(h1, h2, q, g=G, rho=998.2):
    """Power dissipated per unit width, W/m -- the air-entrainment budget.

    `P = rho g q dE`. Handed to the foam sections as a SOURCE TERM rather than
    a coverage: the covering measure the whitecap machinery already sums grows
    at a rate this sets, so the white in a rapid comes out of the same model as
    the white in surf instead of being a second, unrelated mask.
    """
    return (float(rho) * float(g) * np.asarray(q, float)
            * energy_loss(h1, h2))
