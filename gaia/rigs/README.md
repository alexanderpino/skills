# rigs — the measurement scripts behind this corpus's numbers

Every figure in a gaia technique document traces to one of three channels: **(a)** it was already
in the document or its sources, **(b)** it was measured, or **(c)** the page says plainly that it is
unpriced and why. This directory is the evidence for **(b)**.

These scripts were written as each document was repaired, in the sitting that produced its figures.
They live here rather than in a scratch directory because **59 register rows point at them**, and a
register row citing a path that no longer exists is a claim nobody can check — this corpus has
already recorded one such row (`pseudocode-execution.tsv:188`, whose "ALL REPRODUCE" rests on four
`w3/*.py` scripts that no longer exist anywhere).

    approx/   one rig per technique document, named after it, plus saved run output
    clasts/   the boulder/pebble rigs: Bridson sampling, class placement, instance budgets

## Running them

    python3 gaia/rigs/approx/<document>.py

Each is self-contained, seeded, and prints its own rig banner. Several save a `.run.txt` beside them
so a later reader can diff rather than re-derive.

## What these numbers are, and what they are not

They are **CPython/NumPy measurements on one container core**. They are *not* GPU frame costs, not
shipping timings, and not a benchmark of any engine. Each document that quotes one says so on the
page. The algorithmic content — iteration counts, byte counts, ratios, error bounds — is what
survives a port; **absolute wall-clock does not**, and this session measured the same rig at
38.1–46.9× across three containers to prove it.

Where a figure is deterministic (a byte count, an exact arithmetic result, a seeded error bound) it
reproduces byte-for-byte and several documents state it to four or more digits. Where it is
wall-clock, quote the ratio.

`optics/` — one rig, added 2026-09-15. `mu-d-overcast.py` computes `mu_d` just below a flat
surface for a uniform (isotropic) sky and for the CIE standard overcast sky, from Snell and
unpolarised Fresnel at `n = 1.335`. It exists because `water-optics.md` printed 0.86 and called
it *uniform*; 0.86 is the standard overcast sky and uniform is 0.84. Unlike most rigs here it
asserts nothing against the page — it computes two numbers and prints a convergence table, an
`n`-sensitivity table and a no-Fresnel control, and the page was corrected to match.

`networks/` — one rig, added 2026-09-15. `hydraulic_geometry.py` re-derives the ten sections
`river-networks.md` cites as `hydraulic_geometry.py §1..§10` — eleven citations to a file that
had never been committed, so eleven numeric derivations had no artefact and no register row. It
is the second rig here to assert against its page rather than against a transcript: every
expected value is parsed out of `river-networks.md`, and a figure that has gone missing is a
FAIL, not a silent skip. 23 checks, exit 0, and red under four separate mutations of the page.
