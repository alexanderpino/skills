# Risks and open options

Two failures sit either side of the decision gate. Before it: risks that everyone
half-knew and nobody wrote down, because asking "any risks?" at the end of a
refinement reliably produces "not really". After it: decisions parked as
"we'll see", which is not deferral, it is forgetting.

Both have a technique with a mechanical output.

## The premortem

Do not ask what could go wrong. Ask what *did*:

> It is three months from now. This shipped, and it caused an incident serious
> enough that we are writing a postmortem. Write the postmortem.

Prospective hindsight - reasoning from an outcome that is stated as having
happened rather than as a possibility - produces more and more specific causes
than open-ended risk elicitation `[P: Klein, "Performing a Project Premortem",
HBR 2007]`. The framing does the work: "what might go wrong" invites a defence of
the plan, "it went wrong, explain how" invites an explanation.

Practicalities `[F]`:

- Two minutes, silently, in writing, before anyone speaks. The first spoken risk
  anchors the rest of the room.
- Run it after the evidence phase, not before. Refinement's best risks are the
  ones the code taught you: the retry that is not idempotent, the table with no
  index, the service with no timeout.
- Do it even alone. Write the postmortem to yourself; the value is in the
  articulation, exactly as it is with the duck.
- Ask a second round in the voice of the people it lands on: support, finance,
  the on-call engineer. They fail differently from the implementer.

Each cause becomes one entry in `story.risks`:

| Field | |
|---|---|
| `desc` | the cause, as it actually happens |
| `mitigation` | what reduces it. Without one it is a worry, not a plan (`RSK001`) |
| `detection` | the alert, metric or report that tells you it is happening |
| `severity` | low / medium / high |
| `source` | `premortem`, a critic finding, incident history |

**`detection` is the field that earns the premortem.** A mitigation says you
thought about it; a detection says you would find out. A `high` risk with no
detection signal (`RSK002`) is one you learn about from a customer, which for a
tax or money story means learning about it from an auditor.

What a risk is *not*:

- a question with an owner - that is `open_questions`
- work you have decided to do - that is a subtask
- a restatement of the story being hard - that is nothing

A story that crosses repos or ships behind a rollout and produced no risks at all
did not have a premortem run on it (`RSK003`).

## Real Options: deferring on purpose

Three rules `[P: Maassen & Matts, Commitment, 2013]`:

1. **Options have value.** Keeping a decision open is worth something, so
   deciding early has a cost even when the decision is right.
2. **Options expire.** That value is not permanent, and after the expiry you are
   not holding an option, you are living with a default someone else chose.
3. **Never commit early unless you know why.** The reason to decide now is that
   the option is about to expire, or that holding it is blocking work.

The decision gate already forces every fork to `locked` or `deferred`. Real
Options is what makes `deferred` an actual position rather than a shrug, and it
costs two fields:

```json
{"id": "D2", "status": "deferred", "spike": "S0",
 "waiting_for": "S0's measurement of VIES latency and revocation frequency",
 "expires": "before S1 merges - the branch reads the cache, so shipping it forces
             a default TTL whether or not anyone chose one"}
```

- **`waiting_for`** names the information that would decide it (`DEC008`). If you
  cannot name it, you are not waiting for anything and the decision is simply
  unmade - lock it with your best reasoning instead, where it can be challenged.
- **`expires`** names the event or date after which deferring costs more than
  deciding (`DEC007`). This is the *last responsible moment*: not the last
  possible one, but the last at which the option is still real.

### Finding the expiry

Ask what forces a default. Almost always it is a merge: the moment code ships
that assumes an answer, the answer is made, silently and by whoever wrote that
line. In the example above, S1 reads the cache - so S1 merging *is* the expiry,
and the spike must land before it. That also tells you where the spike belongs in
the wave plan, which is why the field pays for itself twice.

### Deferral or procrastination

| | Deferred option | Procrastination |
|---|---|---|
| What decides it | named in `waiting_for` | "when we know more" |
| When it ends | a specific event | never |
| Cost of waiting | understood and accepted | unexamined |
| Who decides if nobody does | nobody - the expiry stops it | the first implementer to touch it |

A spike is an option you bought: the timebox is the price, and it is only worth
paying when the information genuinely changes what you would build. A spike that
would not change any decision is research, and research is not a subtask on this
story.

## Smells

**Risk theatre.** Three risks, all "technical complexity", all mitigated by "be
careful". *Tell:* mitigations with no artefact - no flag, no alert, no test, no
subtask. *Fix:* run the premortem properly; a real cause names a mechanism.

**The undetectable risk.** Mitigation present, detection blank, severity high.
*Tell:* `RSK002`. *Fix:* if you cannot name the signal, the honest mitigation is
"we would not notice", which usually re-prioritises the risk on the spot.

**Eternal option.** A `deferred` decision whose expiry is "before go-live" on
every fork. *Tell:* identical expiries. *Fix:* each option expires at the moment
*its own* default gets baked in, and those differ.

**The decision that decided itself.** A fork parked as deferred while the work
that assumes an answer is already in wave 1. *Tell:* the spike depends on, or
runs alongside, the subtask that consumes its answer. *Fix:* order the spike
first, or accept the default explicitly and lock it.
