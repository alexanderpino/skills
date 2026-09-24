# Architectural significance

Use this when Step 1 leaves you unsure whether a change needs an ADR and doc
updates, or whether it's just code. The goal is to spend documentation effort
where future readers will actually need the rationale.

## The core test

A change is **architecturally significant** if it is costly to reverse *and*
affects how the system is built or how well it meets its quality goals. Concretely,
treat it as significant if it touches any of:

1. **Structure** — adds, removes, splits, or merges a component / module / service,
   or changes a boundary between them.
2. **Interfaces & contracts** — introduces or changes a public interface, API,
   schema, message format, or file format others depend on.
3. **Dependencies** — adds a new external dependency, framework, library with
   lock-in, or a new integration with another system.
4. **Data** — changes the data model, ownership of data, persistence mechanism, or
   how data flows/propagates between parts.
5. **A quality attribute** — makes a deliberate trade that affects performance,
   scalability, security, availability, maintainability, or modifiability (i.e.
   anything tied to a `Q.xx` driver).
6. **Cross-cutting mechanism** — concurrency model, error-handling strategy,
   communication style (shared memory vs files vs network), build/deployment shape.
7. **Pattern or style** — adopts or drops an architectural style or pattern
   (e.g. facade, modular monolith, pipeline) across more than one component. *Choosing*
   one (with its trade-offs) is in `references/structure.md`.

If a change hits **none** of these, it is local or trivial — document lightly or
not at all (see the proportional-rigour table in SKILL.md).

## Quick decision flow

```
Did you choose between real alternatives, and is the choice expensive to undo?
        │
        ├── No  → No ADR. Update the SD if it now mis-describes behaviour.
        │
        └── Yes → Does it touch structure / interface / dependency / data /
                  quality / cross-cutting / pattern (the 7 above)?
                        │
                        ├── No  → Borderline. A short ADR is cheap insurance;
                        │         write one if anyone might later ask "why".
                        │
                        └── Yes → Write an ADR. Then update HLD (if shape changed)
                                  and PRD (if a driver changed), and add/refresh
                                  diagrams where they clarify.
```

## Signals you're under-documenting

- You're about to violate or quietly work around an existing `accepted` ADR.
- You found yourself reverse-engineering "why is it like this?" and the answer
  isn't written down — capture it now, even retroactively, as an ADR.
- Two reasonable engineers would plausibly have chosen differently.
- The change will surprise someone reading the code six months from now.

## Signals you're over-documenting

- The "decision" has exactly one sensible option (no alternatives → no ADR; just
  do it).
- You're writing an ADR for a naming choice, a formatting rule, or an internal
  helper with no external contract.
- The diagram restates what one sentence already says.
- You're documenting the slice you *didn't* touch just to be thorough. Document
  what you changed; don't retro-document the whole repo.

## Don't ignore the smells (lightweight)

While consulting docs, if you notice an emerging anti-pattern — a god object,
cyclic dependency between components, dense undecomposed structure, or
near-duplicate names for different things — note it in the relevant SD or HLD
"known issues / debt" section with the quality attribute it threatens. You don't
have to fix it; recording it stops it from being rediscovered repeatedly and lets
the team decide deliberately (a "we accept this for now" ADR is a legitimate
outcome).
