# Writing for agents

Almost every Markdown file in a studio is read by an **agent**, not by a person. An agent reads
a file at a specific moment, with no memory of the conversation that produced it, often with
little else in context, and then acts on it literally. Text written the way people write for
people — narrative, context first, implied steps, "as discussed" — makes agents guess, and a
guessing agent is inconsistent.

So every file has an **audience** and a **reading moment**, and is written for both.

## Who reads what, and when

| File | Reader | Reading moment | What that means for the text |
|---|---|---|---|
| frontmatter `description` (agents, skills) | the main session, choosing whom to spawn or which skill to load | **always in context**, among dozens of others | It is a trigger, not a summary: what it does + `Use when …` + `Not for …`, concrete nouns the user would say, ≤ ~60 words |
| `CLAUDE.md` + its `@` imports | every session | **every turn**, start to finish | Short. Only what applies to every task; everything else is a pointer to a file read on demand |
| `.claude/agents/<role>.md` body | the spawned subagent | once, at spawn, **knowing nothing else** | Self-contained: who it is, what to read first, how to work, what to return, what it must not do, whom to escalate to |
| `.claude/skills/<name>/SKILL.md` | the session that loaded the skill | when invoked | A procedure: numbered phases, exact commands, exact output format, a verdict vocabulary that includes NOT ASSESSED |
| `.claude/rules/<id>.md` | any agent editing a matching file | **loaded by path**, unannounced, mid-task | Short, checkable bullets about the code; no procedure, no background |
| `.claude/docs/gates/<ID>.md` | the reviewing agent | when a skill runs the gate | The question, the inputs, the only allowed words, the first-line format |
| `.claude/docs/templates/<artifact>.md` | the agent filling it in | when drafting the artifact | Headings it keeps; guidance comments addressed to *it* ("State …", "List …") |
| `.claude/docs/*.md` (roster, coordination, protocol) | agents, on demand | when a rule or brief points there | Reference tables an agent can grep by heading |
| `proposal.md`, `research/report.md`, the handover card | **the user** | when deciding | Written for a person: summaries, trade-offs, open questions |

The last row is the exception: those are for the human, and the rules below do not apply to
them in the same way.

## Rules for agent-facing text

1. **Lead with the action.** First sentence of every section says what to do or what is
   true. Background, if needed, follows in one short line.
2. **Imperative, second person.** "Read `X` first." "Return the verdict on line one." Not
   "It may be helpful to consider reading X."
3. **Self-contained.** A spawned agent has no conversation history. Never write "as
   discussed", "the above", "the usual way", "see earlier". Name the file, the path, the
   command.
4. **Exact over approximate.** Paths, commands, field names, verdict words and file formats
   appear literally, in backticks, exactly as the agent must type or match them.
5. **Specify the output.** Every skill, gate and agent says what it returns and in what
   shape — the first line of a verdict, the table columns, where the file is written.
   Downstream skills parse it.
6. **One instruction per bullet.** An agent may follow the first clause of a long sentence
   and drop the rest.
7. **Say why, briefly.** One clause of reason ("— a missing artifact is a finding, not a
   missing input") lets the agent handle the case the rule did not foresee. Heavy-handed
   capitals without a reason get followed rigidly or not at all.
8. **Unknowns have a word.** Tell the agent what to write when it cannot know or cannot
   check: `NOT SOURCEABLE — <what>`, `NOT ASSESSED — <why>`. Without a word for it, the gap
   gets filled with a guess.
9. **Stable, greppable headings.** Agents read long files by section (Grep `^#`, then Read
   with offset). Keep headings literal and unique; the checker and the hooks match some of
   them exactly.
10. **Budget the length by reading moment.** Always-loaded text costs on every turn:
    `CLAUDE.md` ≤ 150 lines, a `description` ≤ ~60 words, a rule ≤ 120 lines, an agent
    file ≤ 400, a skill ≤ 500 — and a pointer to a reference file beyond that.
11. **No placeholders left behind.** `{{…}}`, `[TBD]`, `TODO` in an agent-facing file are
    instructions the agent will try to follow or invent around.
12. **No decoration.** No emoji, marketing tone, or rhetorical questions; they cost tokens and
    carry nothing an agent can act on.

## Applying it in this skill

- **Proposal text is agent text.** A role's `description`, `responsibilities`, `standards`
  and `must_not`; a skill's `description` and `steps`; a rule's bullets; a gate's `prompt`;
  an artifact's section guidance — all are rendered verbatim into agent-facing files. Write
  them by the rules above while filling `proposal.json`, even though the user reviews them
  in `proposal.md`.
- **The renderers** (`generate.py`) wrap that text in agent-facing structure: every agent
  file gets a `### When You Are Spawned` section (read first, return format), every skill a
  `## Return` section, every template guidance comment addressed to the filling agent.
- **The checker** (`check_template.py` C13) measures what can be measured: description
  length and `Use when`, length budgets, leftover placeholders, conversation-dependent
  phrases ("as discussed", "see above"), and the spawn and return sections.
- **The validation stage** gives both reviewers this file: the refutation critic attacks
  agent-facing text that an agent arriving cold could not act on; the validator checks the
  user's request was met *in a form an agent can follow*.
