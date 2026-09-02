# Complexity: an estimate you can take apart

Read this at the decision gate and before handover. `complexity.py` produces a
card; this file says what is on it and why those metrics and not others.

## Why a card and not a number

Story points compress everything into one figure and then get argued about as if
the figure were the fact. The card goes the other way: every metric is
**derived from the bundle** - nobody types it in - and the band is **the highest
level any metric reaches**, with the metrics at that level named as the
drivers. No weighted sum. A weighted sum is an opinion with decimals; a card is
a list of reasons, each of which someone can look at and say "that one is
wrong, and here is why".

```bash
python scripts/complexity.py assess --bundle bundle.json --config refinery.yaml          # the card
python scripts/complexity.py assess --bundle bundle.json --config refinery.yaml --write  # record it
```

`--write` puts it in `story.complexity`. It is derived data, like the coverage
map: `CPX001` asks for it on a decomposed story, `CPX002` reports one that no
longer matches the bundle. `summary.py` prints the one-line form under
**Complexity.**; the rendered ticket carries the same line.

## The metrics

Each one names where in the bundle it comes from, so a reader can check it.

| Metric | Where from | Why it predicts effort |
|---|---|---|
| **projects touched** | `subtasks[].repo`, `blast_radius.repos` | every repo is a build, a review queue, a deploy, and usually a team `[F]` |
| **code paths changed** | distinct `entry_points` (path, symbol) across briefs | the number of places behaviour changes is a better proxy than lines - one path changed in ten files is one thing to understand; ten paths in one file is ten `[F: change-impact analysis]` |
| **files written** | `change_surface` create/modify/delete | review and merge surface |
| **files to hold in context** | `read_first` + `entry_points` + `change_surface` | what an implementer must load before writing; for an agent, what must fit one window `[P: Pocock, to-tickets]` |
| **contracts crossed / breaking** | `evidence.contracts`, `blast_radius.breaking_contracts` | coupling across a boundary is where sequencing and rollout risk live `[F]` |
| **owning teams** | `evidence.owners`, `blast_radius.owner_teams` | each extra team is a conversation and a wait |
| **decision-table combinations** | product of `decision_table.conditions[].values` | the rule space is the closest thing a story has to cyclomatic complexity `[P: McCabe, 1976]`: every combination is a path someone must decide and someone must test |
| **design forks / deferred** (`forks`, `deferred`) | `decisions[]`, `status: deferred` | a deferred decision is a spike and a wait; three of them is a story that is not decided yet `[P: Real Options]` |
| **blocking unknowns** | blocking `open_questions`, `evidence.pending`, `links[blocked_by]` | each is a dependency on a person or on code that does not exist |
| **irreversible steps** | `kind: migration`, `rollback.irreversible` | a step you cannot undo changes how carefully everything before it is done |
| **critical path** | longest `depends_on` chain | elapsed time and the number of hand-offs, independent of total days |
| **Cynefin domain** | `story.intake.domain` | complicated is knowable; complex is only knowable by probing, which no count captures `[P: Snowden & Boone]` |
| **greenfield** | `evidence.greenfield` | nothing to cite: every convention, contract and deployment is an open fork until the skeleton lands |

Absent on purpose: **lines of code** (a proxy for typing, not for thinking),
**story points** (the thing this replaces), and **estimated days** (they are
already on the subtasks and the card must not be circular).

## Levels and bands

Three thresholds per metric in `complexity.thresholds` (value ≥ t → low,
medium, high). The defaults are in `assets/refinery.example.yaml`; a house that
sizes differently changes the thresholds, never the method.

- **S** - nothing reaches medium.
- **M** - the highest level is medium.
- **L** - one or two metrics are high.
- **XL** - three or more are high, or the domain is complex and two others are
  high. An XL is usually a story that should be split (`SPL001` will often agree)
  or a research item that has not admitted it (`CYN001`).

Greenfield counts as medium on its own, before any count.

## How to read it in a refinement

- **Drivers are the conversation.** "L, driven by 2 breaking contracts and 3
  deferred decisions" tells the room what to talk about; "8 points" does not.
- **A driver you can remove is a plan.** Two repos becoming one by moving the
  seam; three deferred decisions becoming one spike; a rule space of 48 becoming
  12 by dropping a condition nobody asked for. The card is the cheapest place to
  find scope to cut.
- **Compare across stories, not against a calendar.** The card is consistent
  within a house; that is its use. It is not a delivery date.
- **The critics see it.** The sequencer's packet includes it; a plan whose card
  says L and whose waves look like a weekend is a finding.

## Smells

**Sized by feel.** A decomposed story with no card. *Tell:* `CPX001`. *Fix:* run
it; if the card disagrees with the feel, the feel is what needs the explanation.

**The hand-edited card.** *Tell:* `CPX002`. *Fix:* regenerate. A card that says
what the author wanted is a story point with a table around it.

**High everything.** Six metrics at high. *Tell:* XL. *Fix:* this is not one
story - `references/decomposition.md` §2 has the splitting patterns.
