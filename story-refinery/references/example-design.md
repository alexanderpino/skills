# Designing the examples

Example Mapping tells you that every rule needs an example. It does not tell you
*which* examples, so in practice you write the two that came to mind and ship the
third branch unspecified. These techniques generate the set instead of recalling
it, and three of them are old enough to be boring `[P: Myers, The Art of Software
Testing, 1979]` - which is the point. They are the difference between examples
that illustrate and examples that cover.

Pick per criterion, in this order: partition the inputs, stand on the boundaries,
tabulate the combinations, then - only if history matters - map the states.

## 1. Equivalence partitioning

Split each input into classes whose members the system should treat identically.
One example per class is then evidence about the whole class; a second is
decoration.

For "a VAT number": valid, syntactically malformed, absent, syntactically valid
but rejected by VIES, syntactically valid but VIES unreachable. Five classes, and
the last two are the ones tickets always fold together - they have the same
*input shape* and completely different *causes*, which is exactly when an
implementer picks one behaviour for both.

The output is not the examples. It is the argument for why these classes and no
others, which is what a critic can attack.

*Tell that you skipped it:* `AC008` - the rule names alternatives ("missing,
malformed or unverifiable") and carries fewer examples than alternatives.

## 2. Boundary value analysis

Defects cluster at the edges of a partition, not in the middle of it `[P: Myers,
1979]`. For every boundary a rule names, write three examples: on it, one below,
one above. The one *on* the line is the one that settles whether the comparison
is `<` or `<=`, and it is the one nobody writes.

```
AC: Refunds above the daily limit of 100 EUR need supervisor approval.
  99.99 -> processed          (below)
  100.00 -> processed          (on the line: inclusive, and now it is decided)
  100.01 -> PENDING_APPROVAL  (above)
```

Boundaries hide in more than numbers: the empty collection, the single element,
the maximum page size, the first and last day of a period, the retry after the
timeout, zero and negative money.

Mark the example so it is visible: `{"case": "... (boundary)", "expect": "..."}`.
*Tell:* `AC009` - the rule draws a line and no example stands on it.

## 3. Decision tables

When the outcome depends on a *combination* of conditions, prose cannot be shown
to be complete and a table can `[F]`. This is the only form in this skill where
"we have covered everything" is a checkable claim rather than a feeling.

```json
"decision_table": {
  "conditions": [
    {"id": "customer",    "values": ["business", "consumer"]},
    {"id": "vat_number",  "values": ["valid", "invalid", "absent", "unverifiable"]},
    {"id": "destination", "values": ["nl", "eu_other"]}
  ],
  "rules": [
    {"when": {"customer": "business", "vat_number": "valid", "destination": "eu_other"},
     "then": "zero VAT, reason reverse-charge", "ac": "AC1"},
    {"when": {"customer": "consumer", "vat_number": "*", "destination": "*"},
     "then": "destination standard rate"}
  ],
  "impossible": []
}
```

`validate.py` enumerates the product of the condition values and names every
combination that neither a rule nor an `impossible` entry covers (`DT001`). Two
rules that match the same combination with different outcomes is a contradiction
(`DT003`), and it is nearly always a missing condition: the table is telling you
the behaviour depends on something you have not written down as a column.

How to use it well:

- **`*` is a claim, not shorthand.** `{"customer": "consumer", "vat_number": "*"}`
  asserts the VAT number is genuinely irrelevant for consumers. That is a
  statement someone can disagree with, which is what you want.
- **`impossible` is for states the system cannot reach**, with the reason. It is
  not a place to put combinations you would rather not think about; the whole
  value of the table is that it makes the difference visible.
- **A value you exclude is a scope decision.** The worked example drops non-EU
  destinations because they are a non-goal. Adding the column later re-opens the
  table - which is honest, and much cheaper than discovering it in production.
- **Width is a split signal.** Past `DT004`'s threshold the table is not telling
  you the story is complex; it is telling you it is several stories `[L]`.

Rows map to criteria via `ac`, so the table and the acceptance criteria stay one
artefact rather than two that drift.

## 4. State transition

Use when the outcome depends on what happened before, not on the input: an order
that can be paid, shipped, cancelled, refunded; a retry after a timeout; a
double-submitted form.

Draw state × event and fill every cell. The valuable cells are the ones nobody
specified - cancel-after-ship, pay-twice, refund-a-refund - because those are
where production incidents live and where an implementer will invent something.
Write the illegal transitions as criteria too ("cancelling a shipped order is
rejected with X"), or they become unhandled paths.

A state machine that only specifies the happy path is a state machine with an
undefined transition table `[F]`.

## Choosing

| The rule is about | Use |
|---|---|
| one input with several kinds of value | equivalence partitioning |
| a threshold, a limit, a size, a date range | boundary values |
| several conditions that interact | a decision table |
| something that depends on history or order | state transition |
| a single unconditional behaviour | one example, and move on |

Most stories need the first two. Rule-heavy domains - pricing, tax, permissions,
eligibility, discounts - need the third, and are exactly where "we discussed it
in refinement" fails at the third branch.

## Smells

**Illustrative examples.** Three examples that are all the same class with
different names. *Tell:* every example passes through the same code path. *Fix:*
partition first, then write one per class.

**No example on the line.** Every example is comfortably inside its partition.
*Tell:* `AC009`. *Fix:* the boundary is the specification; the middle of the
range is not.

**Prose combinatorics.** A rule with "and", "unless" and "except" in one
sentence. *Tell:* you cannot say how many cases the rule has without re-reading
it. *Fix:* it is a decision table. Write the table, then let the criteria cite
its rows.

**The table that agrees with itself.** Every combination covered, all outcomes
identical. *Tell:* one condition does no work in any rule. *Fix:* drop the
condition, or find the case where it matters - one of the two is true.
