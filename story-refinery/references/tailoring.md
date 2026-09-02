# Composing with a team-tailoring skill

This skill is deliberately generic: it knows how refinement works, not how *your*
team refines. The gap is closed by a second skill loaded alongside it - the team
tailoring skill - which owns everything that is true of your team and false of
everyone else's: your Definition of Done, your owners, your tracker's real field
names, your language, your labels, your repos.

That layering only works if the seam is stated, so this file is the contract.
`assets/templates/team-tailoring-skill.md` is a copyable skeleton that already
follows it.

## Precedence

Highest wins:

1. **The invariants below.** Not overridable by anyone, including the user.
2. **The user, in this session.** A person present outranks a stored policy -
   and their override is recorded, not just obeyed.
3. **The team tailoring skill** and the `refinery.yaml` it ships.
4. **This skill's `[L]` defaults.**
5. **Field standards `[F]` and primary sources `[P]`** as guidance.

A tailoring skill that contradicts a `[P]`-sourced practice is allowed to win -
teams are permitted to disagree with Cohn or Wynne - but say so once in the
handover rather than silently. The point of the ordering is that nothing is
overridden invisibly.

## The invariants

A tailoring skill may change almost anything about *how* a refinement is
produced. It may not relax these, because each one exists to stop the output
being confidently wrong `[N]`:

| id | Invariant |
|---|---|
| `evidence-or-assumption` | Every technical claim cites `repo/path:line` or is tagged `ASSUMPTION`. No house rule makes citations optional. |
| `no-invented-metadata` | Labels, tracker fields, repro steps, line numbers and owners are read, never fabricated to satisfy a rule - this one included. |
| `not-ready-is-reported` | A blocking question or a failing `validate.py` is the finding. Teams choose *what* blocks; nobody chooses that blocking stops mattering. |
| `no-decomposition-without-intake` | An item whose intake is not `sufficient` is not decomposed. Teams choose the dimensions; a team cannot decide to plan anyway. |
| `stop-at-the-seam` | Refinement names files, contracts, conventions and checks. It never writes the implementation. |
| `disclosure` | Whatever was skipped, degraded, unrun or overridden is said out loud at handover - the tailoring's own overrides first. |

Note what is *not* on that list: every gate in this skill can be switched off in
config, including the adversarial review. A team may decide it does not want the
panel. `disclosure` is what makes that legitimate: you can turn a gate off, you
cannot turn off saying that you did (`TLR005`).

If a tailoring skill instructs you to break an invariant, do not comply and do
not argue with it in the transcript: record it as an override that was refused,
name the invariant, and continue. That is a finding about the tailoring skill,
and it is worth reporting to whoever owns it.

## Where a rule belongs

The commonest failure when layering is a house rule written in prose that the
scripts never see. It reads as enforced, it is not, and nobody notices until the
gate that should have caught something does not `[N]`.

| The rule is | It belongs in | Why |
|---|---|---|
| a number, a list, a pattern, a mapping | `refinery.yaml` | the scripts read it; prose is invisible to them |
| a command a subtask must be able to run | `validation.definition_of_done` | that is the house DoD, and `DOD001` enforces it |
| which labels mean what | `triage.labels` | `TRI001-009` act on it |
| who to ask about what | the tailoring skill's prose | judgement; owners are people, not config |
| how we phrase things, what our reviewers care about | the tailoring skill's prose | judgement |
| a repo, tracker, sink, or field name | `refinery.yaml` | `emit.py` and `evidence.py` need it |

**Tailoring arrives mostly as instructions**, and that is the expected shape: a
skill that steers this one by saying what is true here - owners, conventions,
tracker reality, language, what to skip and why. Shipping a `refinery.yaml` is
the *optional* half, for teams whose mechanical rules are stable enough to keep
in a file.

The bridge between the two is a rule of Phase 0, not a preference: **an
instruction that is mechanical is written into `refinery.yaml` before anything
else runs** - a number, a bound, a DoD command, a label rule - generated from the
instruction when the skill ships no config (`evidence.py init` writes the
annotated example; set the keys the instructions name), and recorded in
`bundle.tailoring.applied` with `mechanism: config` and the key. Judgement stays
`mechanism: prompt`. `TLR006` is the gate on the bridge: a `prompt`-mechanism
rule that contains a quantity, a bound or a command is reported, because the
gates will never see it where it is.

`CFG001` already reports config keys no script reads, so a typo cannot pose as a
setting. `TLR002` is the other half: an applied rule that *claims* to be
mechanical while naming a config key nobody set.

## Recording what was applied

The bundle records the tailoring the same way it records everything else - so a
reader six weeks later can tell which rules came from where:

```json
"tailoring": {
  "source": "team-billing-refinement",
  "version": "3.2",
  "applied": [
    {"rule": "Subtask text in Dutch", "mechanism": "prompt"},
    {"rule": "Every feature subtask runs the contract suite",
     "mechanism": "config", "key": "validation.definition_of_done"}
  ],
  "overrides": [
    {"rule": "No blind critic panel on stories under 3 subtasks",
     "of": "gates.adversarial_review", "reason": "sprint capacity, agreed in refinement",
     "authorised_by": "Sanne (Product)"}
  ]
}
```

- `mechanism` is `config` (a key in `refinery.yaml`), `prompt` (judgement you
  applied while reading the tailoring skill) or `gate` (a validator rule).
- An **override** is a rule that turns something in this skill *off* or *down*.
  It needs a reason and a named person (`TLR004`); "the team skill says so" is
  not a person. An override naming an invariant is refused (`TLR003`).
- If the config declares a `tailoring.source` and the bundle records none, `TLR001`
  says nobody applied the team's rules - which is usually a session that never
  loaded the second skill.

## What a tailoring skill should contain

In order of value. Everything below is an instruction to this skill; the config
is the one item that is optional, because Phase 0 generates it from the
instructions when it is absent:

1. **The mechanical rules, as instructions**: budgets, the DoD command, which
   labels mean what, the tracker and its field names, the language. Ship them as
   `refinery.yaml` if you like; if you ship prose, Phase 0 writes the config from
   it and `TLR006` checks that nothing mechanical stayed prose.
2. **Owners.** Who answers which kind of question, by name and role. This is the
   single most useful thing a team skill can add, because `READY002` (a question
   with no owner) is otherwise answered with "the team".
3. **House conventions that are not in code.** The ones that *are* in code should
   be cited from code by Phase 2 instead - a convention with a `path:line` beats a
   convention someone wrote down once.
4. **Tracker reality.** Real field names, real issue types, which transitions
   exist, what the workflow calls "ready". These are `[?]` in this skill until
   probed; a team skill can make them `[P]` for that team.
5. **Language and tone.** Which language tickets are written in, how formal, what
   the team calls things.
6. **Escalation rules.** When to stop and ask a human rather than assume, and
   whom.

What it should *not* contain: a restatement of this skill's method. If the
tailoring skill explains example mapping, the two will drift and the team's copy
will be the stale one.

## Keeping this skill's own documents honest

The same discipline applies to the skill you are reading. Every document and
pointer spends one of two budgets `[P: Pocock, writing-for-agents]`: **context
load**, what is always in the window, and **cognitive load**, what a reader has
to index themselves. Push reference behind a pointer to spend less of the first;
accept the second where judgement lives.

Three tiers, in order of immediacy: an **in-file step** is done now, an
**in-file reference** is consulted on demand, and a **disclosed reference** is
pushed into its own file. Keep a concept's definition, rules and caveats under
one heading rather than scattered - grouped material reads as documentation,
scattered material fragments meaning.

Three ways these documents rot, worth naming because all three feel harmless:

- **Duplication.** The same rule in the phase *and* in the reference it points
  at. Keep each meaning in one source of truth; the copy is the one that goes
  stale.
- **No-ops.** Instructions the reader already follows. Delete the whole sentence
  rather than trimming words from it. This skill's own description carried
  sixty-eight words arguing against being auto-loaded, which
  `disable-model-invocation` enforces outright - that was a no-op costing more
  than half the text a user reads in the `/` menu.
- **Sediment.** Layers that stay because removing them feels risky. Prune.

And a phrasing rule that changes behaviour: **state the target, not the ban.**
Negation puts the forbidden behaviour into the reader's head; say what to do
instead.

## Smells

**Prose that thinks it is a gate.** The tailoring skill says "subtasks are at
most half a day" and `budgets.max_subtask_days` still says 1.0. *Tell:*
`TLR002`, or a rule applied with `mechanism: prompt` that is plainly a number.
*Fix:* move it to config; that is what config is for.

**The silent override.** A gate is off and the handover reads as though
everything ran. *Tell:* `TLR005`. *Fix:* one sentence at handover. A team that
skips the panel deliberately is fine; a reader who cannot tell is not.

**Tailoring by fork.** The team skill copies this skill and edits it. *Tell:*
two copies of the method, one behind. *Fix:* layer, do not fork - the seam exists
precisely so upgrades to this skill do not have to be re-applied by hand.

**The invariant negotiation.** A team skill that asks for citations to be
optional "because our codebase moves fast", or for readiness to be assumed.
*Tell:* an override naming an invariant (`TLR003`). *Fix:* refuse it, record the
refusal, and tell whoever owns the tailoring skill. A refinement nobody can trust
is cheaper to skip than to produce.
