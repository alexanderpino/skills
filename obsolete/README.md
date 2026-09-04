# Obsolete — superseded skills, kept for provenance

The skills in here are **retired**. They are not maintained, and they are not the answer to a
question about terrain any more. Use [`gaia/`](../gaia/) instead.

| Skill | Superseded by | Why |
|---|---|---|
| [`terrain-architect`](terrain-architect/) | [`gaia/`](../gaia/) | Terrain generation — noise, erosion, flow routing, stratigraphy |
| [`terrain-renderer`](terrain-renderer/) | [`gaia/`](../gaia/) | Terrain rendering — LOD, raymarching, water, atmosphere |

## Why they are still here

Gaia was distilled from them, and three things in them did not survive distillation:

- **`terrain-architect/reference-impl/`** is an executable Python reference implementation with its
  own CI suite, which still runs. Gaia ships no code — it cites sources and states what was
  measured. If you need something that executes, it is here and not there.
- **The long derivations.** Gaia is capped at 450 lines per document and states results with a
  locator; the working that produced some of them is here.
- **Provenance.** Gaia's registers record defects found *in* these skills while distilling them, and
  cite paths inside them as they were at the time. Deleting these directories would break that
  record.

## What to expect if you read them

They were written to a different standard than Gaia. Gaia grades every source with a provenance
tier, declares which artefacts were never opened, and records where it has been wrong — see
[`gaia/STATE.md`](../gaia/STATE.md) for exactly what has and has not been audited. These skills do
not do that. `gaia/registers/source-findings.tsv` lists specific defects found in them, including
claims that turned out to be wrong.

Prefer Gaia. Reach in here for the code, the derivations, or to check what a Gaia claim was
distilled from.
