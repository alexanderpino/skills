# s12-bathy-pockets — a closed form, painted and drawn

Two panels, the same 62 m of the wave-cut bench (row j = 44, y = 0), the same
cells, the same numbers. Dark is bare rock, pale is sand.

- **Left — what waves 4–11 shipped.** `1 - sand_cover_fraction(regolith)` used
  as a *blending coefficient*: `bare = planed * (1 - cover)`. Every square
  metre reads a fraction rock.
- **Right — `beach.rock_bare_mask`.** The same closed form drawn as a surface.
  Sand fills each pocket from the bottom up, so the bare share is the top
  `1 - cover` of the rock's own height ordering.

**The two panels have the same mean: 0.1046 against 0.0975 over this window,
and the difference is sampling.** Nothing about *how much* rock shows changed —
`sand_cover_fraction`'s Gaussian ponding integral is untouched and is still
what decides it. Only *where* changed.

That is also why the defect survived eleven waves: the mean was always right.
`--bug pockets-as-blend` puts the left panel back and moves **not one** of the
five suite rows that check the bare share against the closed form. It moves
three other rows — the one that says the shader's mask is binary, and the two
that say the mask returns to its mean only when a pocket goes sub-pixel.

## Bar H1, and what this does not yet reach

Bar section H1 photographs the bench as *"deeply pocketed, with sand infilling
the hollows and dark weed on the wet rock"* and calls it *"a landform with a
formation mechanism, not scenery"*. This closes the **sand-in-the-hollows**
half, as a realisation of a volume book rather than as a texture.

It does **not** put that landform in a hero frame, and the reason is measured
rather than guessed: above the datum this bed's planed bench carries a median
regolith of **2.27 m against `ROCK_ROUGH` = 0.25 m** — nine times what
"infilling the hollows" means — so the subaerial bench is *buried* by the beach
wedge and reads as sand, cover = 1.000. The bare rock is all below the
waterline. The two landforms are separated by one declared `?`: the wedge needs
34.3 m³ per metre of coast and the loop delivers 206.1 at `SAND_FRACTION` =
0.10, so the bench emerges subaerially only below `SAND_FRACTION` ≈ 0.017.
There is no weed. Both are named in `gauntlet/sea/workbench.md` and neither is
claimed.

## The scale

`ROCK_POCKET = 2.0 m`, declared `?`, bracketed 0.7–6.0 m — the pockets'
correlation length, which is `ROCK_ROUGH` seen sideways (that is the relief's
amplitude, this its wavelength). The suite shows the bracket moves the *size*
of a pocket and **not** how much rock shows, because the mask's mean is the
closed form at any scale, so the unknown cannot leak into the volume book.

*Provenance: `beach_render.pockets_figure`, on the bed `s12-bathy-frame` was
rendered from.*
