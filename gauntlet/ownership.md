# File ownership — one file, one owner, per wave

| Lane | Owns | Must not touch |
|---|---|---|
| **surface** | `terrain-renderer/reference-impl/field.py`, `terrain-renderer/reference-impl/wake.py` | anything under `references/`, `render.py` |
| **optics** | `terrain-renderer/reference-impl/render.py` | `field.py`, `wake.py`, anything under `references/` |
| **chapter** | `terrain-renderer/references/12-water-rendering.md` | all of `reference-impl/` |

`README.md` in reference-impl is the lead agent's; builders leave it alone and the
smoother updates it at the end of a wave if the interfaces moved.

The interface between surface and optics is frozen for the run:
`field.surface_normal_grid(xs, ys)` and `field.surface_normal_points(x, y)` both
return `(nx, ny, nz)`. A builder that needs it changed asks the lead agent rather
than reaching across the line.

## Contract, as confirmed

- **Goal** — the pool model is physically correct and the render makes a viewer
  wonder whether it is a photograph; the chapter documenting it holds up against
  the rest of this repo.
- **Bar** — `gauntlet/bar/photo-spec.md`, frozen from three reference photographs.
- **Dimensions** — `physics`, `visual`, `prose`.
- **Budget** — 6 waves, then stop and offer an extension. Never self-extend.
- **Stop** — `bar-met` at ≥ 9.5 with a clean streak per dimension; `budget` armed.
- **Autonomy** — run unattended; report when a stop fires.
- **Inspection** — critics run `render.py` and read the PNG; physics critics read
  the derivations and re-run the diagnostics; prose critics read the chapter
  against its sibling chapters.
- **Honesty** — visual rounds are logged `--mode rubric`, not `--mode blind`: the
  critics judge against a written spec because they cannot open the photographs.
