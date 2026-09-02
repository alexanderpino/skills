# Handover rubric

`validate.py` decides whether a bundle is *well-formed*. It cannot tell whether
the refinement is any *good*. Score yourself on these seven dimensions before
handover, report the total, and **name the weakest dimension out loud** even when
the total is high. A refinement handed over with an unnamed weak spot is how the
weak spot reaches the implementer.

Score each 0-3. A dimension at 0 or 1 means say so rather than shipping quietly.

---

## 1. Evidence

| | |
|---|---|
| 3 | Every technical claim carries `repo/path:line` plus a symbol name. Files were read, not inferred. Cross-repo seams identified with named contracts. Budget exhaustion, missing repos and stale indexes are reported. |
| 2 | Main paths cited, a few secondary claims uncited. |
| 1 | Some paths named, none verified by reading. |
| 0 | Plausible-sounding paths. This is fabrication, not evidence. |

## 2. Criteria

| | |
|---|---|
| 3 | Every rule observable, binary, bounded and falsifiable today. Inputs partitioned, with one example per class and one standing on every boundary. Where conditions interact, a decision table whose combinations are all covered or explicitly impossible. Non-functional answered with numbers or an explicit "unchanged". |
| 2 | Rules testable, boundary cases thin, some NFR categories blank. |
| 1 | Criteria restate the title in more words. |
| 0 | Criteria specify a mechanism instead of an outcome. |

## 3. Decisions and questions

| | |
|---|---|
| 3 | Every fork surfaced with options and trade-offs. Locked decisions carry a rationale someone could argue with. Deferred decisions are held options: a timeboxed spike, what they wait for, and the event at which they expire. Risks come from a premortem and each carries a detection signal. Questions have named owners. |
| 2 | Decisions recorded, one or two rationales thin. |
| 1 | Decisions stated as facts, no options shown. |
| 0 | Zero questions on a non-trivial story - the gaps were filled by assumption. |

## 4. Decomposition

| | |
|---|---|
| 3 | Slices leave the system working. One repo, one PR, one owner per file. Dependencies exist only where output genuinely blocks input, and the wave plan is wide. Contract producers precede consumers. |
| 2 | Sound decomposition, over-serialised graph. |
| 1 | Layer split with nothing demonstrable until the end, unintentionally. |
| 0 | Subtasks named "Testing", "Integration", "Misc". |

## 5. Dual audience

| | |
|---|---|
| 3 | Human text within budget and free of anything a colleague already knows. Briefs prevent all four agent failure modes: wandering, scope creep, convention drift, false completion. Conventions cited from real code. Both sides agree. |
| 2 | Briefs complete, `forbidden` and `out_of_scope` thin. |
| 1 | The brief is the human text reformatted as JSON. |
| 0 | The two sides disagree, or the brief contains the implementation. |

## 6. Honesty

| | |
|---|---|
| 3 | The item's own labels, links and priority were read and their consequences applied or explicitly overruled. Intake verdict recorded and every gap classified as missing, assumed or answered. Assumptions labelled. Unverified tracker details marked `[?]`. Scope added beyond the original ask is called out. The weakest part of the refinement is named. Not-ready is reported as not-ready. |
| 2 | Mostly candid, a couple of soft claims. |
| 1 | Uncertainty smoothed over. |
| 0 | Readiness theatre: gates ticked with questions still open. |

## 7. Opposition

| | |
|---|---|
| 3 | Blind critics with distinct mandates read the artefact, not the reasoning. Findings carry a resolving locator and a named downstream failure. Every one ends fixed, accepted with a written risk and an accepter, or rebutted from the bundle. The stamp matches the content that was reviewed. |
| 2 | The panel ran and bit, but a mandate or two came back thin. |
| 1 | Rubber-ducked only, on a story that warranted the panel; or critics who saw the rationale. |
| 0 | No opposition, or critique theatre: findings recorded, everything accepted, bundle unchanged. |

---

## Reading the total

| Total | Meaning |
|---|---|
| 19-21 | Hand over. Name the weakest dimension anyway. |
| 14-18 | Usable. Say which dimension is weak and what would fix it. |
| 9-13 | Hand over the questions, not the plan. The refinement is not the deliverable yet. |
| < 9 | Something upstream is missing - usually Phase 2 evidence or a stakeholder answer. Say what you need. |

Two failure modes when self-scoring `[N]`: rating your own thoroughness rather
than the artefact, and rating the effort rather than the result. Score what a
sceptical reviewer would find in the bundle, not what you remember doing.
