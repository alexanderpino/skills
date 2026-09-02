# Triage: what the ticket already says about itself

An item arrives carrying more than its description. Labels, components, a
priority, an issue type, links to other issues, a reporter, an environment field -
each one is a decision somebody already made, usually before you opened it.
`production-issue` says this escaped to customers. `security` says someone
external may be waiting. `sev1` says refinement is not what this needs right now.
A blocking link says another team's ticket is downstream of your ordering.

Refining the description while ignoring that metadata produces a plan that is
internally correct and inapplicable - the most expensive kind, because it passes
every other gate in this skill `[N]`.

```bash
python scripts/triage.py apply --bundle bundle.json --config refinery.yaml --write
```

Read the metadata *before* the sufficiency gate: a label can change what
"sufficient" even means. A production finding needs `first_seen`, `frequency`,
`impact_scope` and `workaround` before anyone knows what to reproduce, and none
of those are in the feature dimension set.

## Capture it verbatim

`story.tracker_meta` holds what the tracker says, copied, not interpreted:

```json
"tracker_meta": {
  "issue_type": "Story", "status": "Refinement", "priority": "High",
  "labels": ["billing", "eu-vat", "compliance", "team-billing"],
  "components": ["checkout", "tax"],
  "reporter": "Marieke (Finance)",
  "links": [{"type": "blocks", "key": "ABC-131"}]
}
```

Two rules, both of which sound obvious and are broken constantly `[L]`:

1. **Never invent a label.** If you cannot see the ticket's metadata, say so and
   leave the block out; `TRI001` will note that nobody read it, which is the
   honest state. A guessed label is worse than a missing one because everything
   downstream treats it as fact.
2. **Never edit a label to make a rule match.** If the ticket is mislabelled, that
   is a finding to report - possibly the most useful one in the refinement - not
   something to quietly correct in your copy.

Capturing it also protects the push: `emit.py` carries existing labels into the
parent payload, so pushing a refinement does not silently delete the ones triage
put there.

## The policy

`triage.labels` in `refinery.yaml` maps patterns to consequences. Rules are
regexes matched against labels and components (a rule can set `field:` to look at
`issue_type`, `priority` or `status` instead). Every matching rule contributes;
lists merge, and for scalars the first matching rule wins - so **order in the file
is precedence**, incident rules first.

| Consequence | What it does | Gate |
|---|---|---|
| `route: incident` | refinement is not the instrument; do not decompose | `TRI002` |
| `kind` / `profile` | a production finding is a bug and takes the bugfix profile | `TRI005` |
| `require_dimensions` | extra intake dimensions before the item counts as sufficient | `TRI004` |
| `mandatory_subtask_kinds` | e.g. a reproducing test on an escaped defect | `TRI003` |
| `must_answer_nfr` | quality attributes that cannot be blank or "unchanged" here | `TRI006` |
| `add_critics` | extra critics on the Phase 8 panel: `operator`, `security` | `TRI008` |
| `ask` | questions the label raises, written into `open_questions` | - |

`TRI007` reports any label that no rule and no `triage.ignore` pattern covers.
That is the gate that keeps the policy alive: an unrecognised marker is either a
consequence nobody has encoded or noise nobody has admitted is noise, and both
deserve one line in the config rather than a memory of what `ops-2` meant.

`TRI009` fires when the labels no longer produce the triage on record - somebody
re-labelled the ticket while it sat in the backlog, which happens most often at
exactly the moment it starts mattering.

## What the common labels actually change

**`production-issue` / escaped defect.** The single most consequential label.
It changes:

- the *kind*: a bug, so the bugfix profile applies - failing test first, root
  cause as a recorded decision (see `references/decomposition.md`)
- what "enough information" means: since when, how often, how many affected, and
  is there a workaround - four questions the reporter can usually answer in a
  minute and nobody can answer later
- the criteria: the reported case *and* the class it belongs to. A fix verified
  only against the exact reported input is a fix for one customer
- the subtasks: a reproducing test is mandatory, and it lands first
- observability: if it escaped, something failed to detect it. That gap is a risk
  with its own detection signal, or an explicit accepted one
- the panel: the `operator` critic, who asks whether you could see it, stop it
  and undo it at 03:00

**`sev1` / `incident` / `outage`.** Route to incident. This is Cynefin's chaotic
domain wearing a tracker label `[P: Snowden & Boone, 2007]`: act to stabilise,
then refine what is left. A bundle that decomposes it anyway is refusing to read
the room, and `TRI002` fails it. The useful refinement output during an incident
is the *follow-up* item, written after.

**`security` / `vulnerability` / `pentest`.** Adds the `security` critic, forces
a real answer for the security attribute, and requires a test. Also: ask once
whether there is a disclosure deadline or an external reporter, because that
changes sequencing more than any technical fact in the ticket.

**`compliance` / `audit` / `gdpr`.** Someone signs this off, and they usually
need evidence that outlives the merge. The `data` and `security` attributes stop
being answerable with "unchanged", and the stakeholder critic joins the panel.

**`tech-debt` / `refactor`.** The missing dimension is nearly always the
*outcome*: what breaks, slows or stays risky if we do not do this. Without it the
item cannot be prioritised against anything and will lose every time.

**`spike` / `discovery`.** The deliverable is information. Require a `spike`
subtask, with a timebox and a named question - and check it is not a story in
disguise.

**Priority and status** are context, not consequence, most of the time. Two
exceptions worth encoding: a top priority with no `blocking` question is
suspicious (somebody wants it now and nobody asked what it needs), and an item
already `In Progress` while being refined means work started against an
unrefined plan - report it rather than refining around it.

**Links.** `blocks` and `is blocked by` are the ones that matter: they order work
across teams and neither the wave plan nor the dependency graph knows about them.
Read them, and say in the human text which external ticket the plan assumes.

## Smells

**Refining past the label.** A clean bundle for an item labelled `sev1`. *Tell:*
`TRI002`. *Fix:* the label is newer information than the description.

**Label laundering.** The triage block does not match the ticket. *Tell:*
`TRI009`, or a `tracker_meta` nobody can re-derive from the tracker. *Fix:*
re-run `triage.py`; the ticket is the source of truth for its own metadata.

**The mislabelled ticket refined as labelled.** A feature request carrying
`production-issue` because that was the fastest route onto the board. *Tell:* the
intake finds no repro, no first-seen, nothing to reproduce. *Fix:* report the
mismatch and ask for a re-label. Do not quietly refine it as a feature, and do not
invent a reproduction to satisfy `TRI004`.

**Policy rot.** Every refinement reports the same three unclassified labels.
*Tell:* recurring `TRI007`. *Fix:* one line in `triage.labels` or
`triage.ignore`. The gate exists to force that decision once instead of
re-deciding it silently every sprint.
