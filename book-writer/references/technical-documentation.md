# Technical documentation — the four-quadrant discipline

## Why this reference exists

The book-writer skill, until now, has assumed each project has **one output mode**: a novel has chapters, a memoir has chapters, a history has chapters. The persona writes in one register; the reader engages with one kind of text. This assumption holds across every project type the skill has previously addressed — fiction, narrative non-fiction, pedagogical books, picture books — because in each case the work is read sequentially, voice consistency is a virtue, and the writer's relationship to the reader is stable across the manuscript.

Technical documentation breaks this assumption.

A complete technical documentation set for any non-trivial codebase or system requires **four different kinds of writing**, each with its own structure, voice, success criteria, and failure modes. They are not different chapters of the same book; they are four parallel works addressing the same subject from four orthogonal angles. A developer reading documentation does not read it cover to cover. They jump in at the angle they need: looking up an API method, learning a new system from scratch, solving a specific problem, or trying to understand why an architecture is shaped the way it is.

This reference exists to give the skill the discipline to write all four kinds well, to recognise which kind a given task requires, and to maintain consistency across them when one project produces all four.

The framework used here is **Diátaxis**, articulated by Daniele Procida and adopted by major documentation systems including the Django docs, the Rust standard library docs, and increasingly Microsoft Learn (the successor to MSDN). Diátaxis maps documentation onto two axes: *practical vs. theoretical*, and *learning vs. working*. The four quadrants that result are:

- **Tutorials** (learning + practical) — guided journeys for newcomers
- **How-to guides** (working + practical) — recipes for specific problems
- **Reference** (working + theoretical) — descriptive lookup material
- **Explanation** (learning + theoretical) — deeper understanding of concepts

Each quadrant serves a different reader-state and answers a different kind of question. Confusing them — putting reference content in a tutorial, putting explanation in a how-to, mixing tutorial pacing into reference — is the most common cause of bad technical documentation.

## When this discipline applies

This reference applies when any of the following are true:

- The project is documentation for an existing codebase, library, framework, SDK, or API
- The project is a developer-facing technical book that needs reference material alongside its narrative chapters
- The project is internal team documentation for a non-trivial system
- The project is a configuration, protocol, or format specification

It does **not** apply when the project is a pedagogical book *about* a technical topic that does not require lookup material (e.g. "Game Programming Patterns" by Robert Nystrom, which is conceptual throughout and has no reference component). For such projects, the existing skill disciplines (writer-persona, anti-AI-tells, language-naturalness) are sufficient.

For projects that mix — say, a book that teaches an engine and ships with reference docs as appendix or companion — this reference covers the documentation portions; the existing disciplines cover the narrative book.

---

## The four quadrants

### 1. Reference

**Purpose.** To describe the system completely and accurately so that a working developer can look up what they need and trust what they find.

**Reader-state.** The reader is *working*. They have a concrete task in front of them and they need to know how a specific item behaves. They are not reading sequentially. They have arrived at this page via search or via a link from another page, and they will leave once they have what they need.

**Question answered.** *What does this item do, exactly?*

**Structure.** Atomic per item. One page (or one logical section) per documentable unit: class, method, property, function, type, macro, configuration option, format field, protocol message. Each page follows a consistent template:

```
NAME
DECLARATION / SIGNATURE
DESCRIPTION (one paragraph, declarative)
PARAMETERS (for callable items)
RETURN VALUE (for callable items)
REMARKS (behaviour the description and parameters do not capture)
EXCEPTIONS / ERRORS
EXAMPLES (minimal working code)
SEE ALSO
VERSION INFO
```

Pages are dense but flat — no nested narrative structure, no chapters, no progression. The reader can land on any page and have a complete answer for that item.

**Voice discipline.**

- **Declarative, not narrative.** "Returns the number of elements," not "This method will return..." The reader does not need conversational softening; they need fact.
- **Present tense, third person.** "The function allocates memory" not "This will allocate memory."
- **Specific over abstract.** "Throws `std::out_of_range` if `index >= size()`" not "Throws an exception in some cases."
- **Voice is suppressed.** The writer's personality is invisible. Reference docs across a single project should be uniform regardless of which engineer-documenter wrote which page. A reader should not be able to tell.
- **No marketing.** "Useful for" and "powerful" and "convenient" are removed. Either the reader needs this item or they don't; description is not promotion.

**Anti-AI-tells specific to reference.**

- **Vague behaviour claims.** "Generally returns..." "Usually thread-safe..." Real reference is precise: it returns X under conditions Y, it is thread-safe with respect to Z but not W. AI generates hedge-language because it doesn't know the precise answer; the discipline is to look it up in the source rather than hedge.
- **Missing edge cases.** What if the parameter is null? What if the collection is empty? What about overflow? Real reference enumerates edge cases; AI tends to describe the happy path only.
- **Pseudo-code in examples.** Examples must be *working code* that compiles. AI gravitates toward pseudo-code or "example" code that omits headers, namespaces, error handling. The discipline is: every example must be runnable as written.
- **Fake confidence on threading and performance.** AI invents thread-safety claims and performance characteristics that are not verifiable from the source. The discipline is: if the source does not document threading guarantees, say "thread-safety not specified" rather than asserting "thread-safe" or "not thread-safe."
- **Citation-tourism.** Inserting cross-references that look right but don't actually relate. Every "See Also" link must serve the reader who has just finished this page.
- **Generic "Useful for" framing.** "This method is useful for cases where..." — the reader does not care whether it is useful; they care what it does. Remove.

**Example fragment** (already produced for `ComponentManager::Create` in the wi::ecs project):

```
Creates a new component associated with the specified entity and returns
a reference to it.

## Parameters

`entity` — Entity
The entity to associate the new component with. Must not be INVALID_ENTITY
(the value 0). The entity must not already have a component of this type
in this ComponentManager — only one component per type per entity is
permitted.

## Return Value

A non-const reference to the newly created component. The component is
default-constructed; the caller is expected to populate its fields after
creation.
```

Note the lack of conversational softening, the precise edge case (only one per type per entity), the explicit value of `INVALID_ENTITY`. This is reference voice.

### 2. How-to guides

**Purpose.** To walk a working developer through a specific task they have already decided to perform.

**Reader-state.** The reader is *working*. They have a concrete goal: "save and load a scene", "add a custom component type", "iterate components in parallel". They are looking for a recipe that gets them from where they are to where they want to be. They have enough background to follow along without being taught from scratch.

**Question answered.** *How do I do X?*

**Structure.** Goal-oriented. A how-to has:

- A title that names the goal precisely ("How to: Save and Load a Scene", not "Scene Persistence")
- A short statement of when to use this approach (and when not to)
- A list of prerequisites (assumed knowledge, required setup)
- Numbered steps from start to finish
- The complete working code, often shown in two forms: the assembled program and the key fragments
- Variations on the basic recipe ("If you want to do X instead, change step 3 to...")
- Common pitfalls and how to avoid them
- A short "See also" linking to related how-tos and reference material

The structure is sequential and complete. Unlike reference, the reader is meant to follow it from top to bottom.

**Voice discipline.**

- **Imperative or second-person.** "Call `Register<T>` to add a component manager." or "You call `Register<T>` to add a component manager." Not narrative third-person.
- **Goal-aware.** The text reminds the reader of the goal at decision points. "Now we have the component manager; the next step is to add components for our entities."
- **Variation acknowledged.** Real how-tos acknowledge that the reader's situation may differ. "If your scene already has a ComponentLibrary, use the existing one rather than creating a new one."
- **No teaching of fundamentals.** The reader has decided to do X; they don't need the lecture on why X exists. Save that for explanation.
- **Specific working code.** Every code block in a how-to should be either complete-and-runnable or clearly marked as a fragment from a larger complete example shown elsewhere on the page.

**Anti-AI-tells specific to how-to.**

- **Pseudo-code.** "// Set up the component manager here" instead of actual code. AI generates handwave-comments where real how-tos give working code. The discipline is: if you cannot give working code, the how-to should not exist yet.
- **Tutorial-creep.** AI tends to start a how-to by teaching what an ECS is, what a component is, how Wicked Engine is structured, before getting to the actual recipe. The reader of a how-to has already decided to do X; they did not arrive here for the introduction. The discipline: cut everything before the first step.
- **Reference-creep.** AI tends to enumerate every parameter of every function called, every alternative API, every related concept. The reader of a how-to wants the recipe; for full details they go to reference. The discipline: link to reference for completeness, do not duplicate.
- **Missing variations.** AI gives the recipe for the canonical case and stops. Real how-tos acknowledge "but what if your situation is X" and provide the variation. The reader who arrives with a slightly-different situation must not be left hanging.
- **No pitfalls.** AI tends to write the recipe as if it always works. Real how-tos warn about the things that go wrong: "Note: if you call Reserve before knowing the count, you may end up with too small a buffer; better to use the worst-case estimate."
- **Generic outro.** "Now you know how to save and load a scene. Happy coding!" — empty filler. Cut it. End on the last useful step or the variation section.

**Example fragment.**

```
## How to: Save and Load a Scene

This guide shows you how to serialize a scene to a file and load it
back. Use this approach for save games, level files, and editor
project files.

You should be familiar with wi::ecs ComponentManager and ComponentLibrary
before following this guide. For an introduction to those, see [Getting
started with wi::ecs].

### Prerequisites

- A scene with a populated ComponentLibrary
- Write access to the target file path

### Steps

1. Create a wi::Archive in write mode pointed at the target file:

       wi::Archive archive("savegame.wi", false);  // false = write mode

2. Create the EntitySerializer that will hold serialization state:

       wi::ecs::EntitySerializer seri;

3. Call Serialize on the ComponentLibrary:

       scene.componentLibrary.Serialize(archive, seri);

4. The archive flushes automatically when it goes out of scope. To
   force-flush earlier, allow the Archive to destruct.
```

Note the specific working code, the explicit prerequisites, the goal-oriented framing.

### 3. Explanation (conceptual)

**Purpose.** To help a reader understand *why* the system is the way it is — design rationale, trade-offs, alternatives considered, conceptual model.

**Reader-state.** The reader is *learning*, but in a specific mode: they want to understand, not to do. They may have already used the system practically and now want the deeper picture; or they may be evaluating the system before adopting it; or they may be debugging a confusing behaviour and need to understand the underlying model.

**Question answered.** *Why is this the way it is? What is the model? What are the trade-offs?*

**Structure.** Narrative-explanatory, but constrained. An explanation page has:

- A title naming the topic ("ECS Lookup Table Implementations", "Component Lifetime and Ownership")
- An opening that frames the problem the topic addresses
- The core explanation, often with diagrams, prose, and worked examples
- Discussion of trade-offs, alternatives, and design choices
- Pointers to related explanations and to reference / how-to material

Unlike how-to and tutorial, explanation is *not* sequential-as-recipe. It is sequential-as-argument. The reader follows the writer's reasoning.

**Voice discipline.**

- **Reasoned and authoritative.** Explanation pages should feel written by someone who has thought hard about the topic and chosen to share their understanding. The voice can be more present here than in reference or how-to, but it should never become personality-driven.
- **Specific about trade-offs.** "We chose linear arrays because cache behaviour during iteration matters more than insertion cost in our workload" — not "We chose linear arrays because they are powerful."
- **Honest about alternatives.** Real explanations acknowledge what was considered and rejected. "An alternative would be a sparse-set ECS like EnTT; the cost there is X, which we judged unacceptable for use case Y."
- **Diagrams allowed.** This is the only quadrant where ASCII diagrams or image references typically pull weight. Reference rarely needs them; how-to occasionally; tutorials sometimes. Explanation often does.
- **Long-form is acceptable.** Reference pages should be short; how-tos medium; tutorials sequential. Explanation can be long when the topic warrants — but never longer than the topic warrants.

**Anti-AI-tells specific to explanation.**

- **Empty abstractions.** "ECS is a powerful pattern that..." "This architecture provides flexibility..." AI gravitates toward marketing-flavoured generalities. Real explanation gives specific reasons grounded in the source material. The discipline: every claim must answer "why specifically" or be cut.
- **Missing trade-offs.** AI tends to praise the chosen design without acknowledging what it costs. Real explanation always contains the costs. The discipline: for every benefit claimed, name the corresponding cost.
- **Fake history.** AI invents historical claims about why a design exists. The discipline: if the source does not document the history, do not invent it. Either find the historical record (commit logs, blog posts, design docs) or describe the design as it exists without speculating on origins.
- **Citation-tourism into academic literature.** AI tends to drop in references to academic papers or industry articles that look authoritative but were not actually used in the design. Only cite sources that were actually used or that demonstrably engage with the same problem.
- **Pretentious depth.** AI sometimes performs depth — long sentences, abstract vocabulary, philosophical framing — for topics that don't warrant it. The discipline: depth is what the topic requires, not what makes the writer look serious.
- **Missing concrete grounding.** Even abstract explanation should include concrete code references. "The lookup table is implemented as a hash map of 64-item buckets (see `LookupTable::Block` in wiECS.h:680)" rather than "The lookup uses a hash-based approach."

**Example fragment.**

```
## ECS Lookup Table Implementations

The ComponentManager template includes four alternative implementations
of its internal entity-to-index lookup table, controlled by a single
#define at the top of the class:

    #define LOOKUP_BUCKET_HASH

The four options are LOOKUP_STRAIGHT, LOOKUP_SPARSE, LOOKUP_BUCKET_HASH
(the default), and LOOKUP_HASH. Each represents a different trade-off
between memory usage, lookup speed, and behaviour under sparse versus
dense entity ID distributions. This page explains each option and when
to use it.

### Why a lookup table is needed at all

The ComponentManager stores components in a tightly packed linear array
for cache-friendly iteration. The cost of this layout is that finding
a specific component by entity ID requires an indirection: entity ID
to array index. The lookup table provides this indirection.

The simplest approach — a linear scan of the entities array — is O(n)
and unacceptable for the typical case where a system queries thousands
of entities per frame. All four implementations provide effectively
constant-time lookup; they differ in their constants and their memory
behaviour.

### LOOKUP_STRAIGHT

LOOKUP_STRAIGHT stores a direct array indexed by entity ID, with each
slot containing the component's index in the linear array (or
INVALID_INDEX). It is the fastest lookup possible — a single array
access — but it wastes memory: if entity IDs are dense from 0 to N
the table is N entries; if entity IDs are sparse (say, IDs 1 and
1,000,000), the table grows to fit the largest ID, leaving most slots
empty.

The header comment is explicit:

    // !Use it only for performance testing of minimal lookup overhead!

In practice, this option exists to establish the speed ceiling for
benchmarking; the other options trade some lookup speed for sane
memory behaviour.
```

Note the specific reference to source line numbers, the explicit naming of the trade-off, the willingness to engage with the design choice rather than just describe its surface.

### 4. Tutorials

**Purpose.** To take a learner from "I don't know this system at all" to "I have built something working with it and understand the basic shape."

**Reader-state.** The reader is *learning*. They have arrived because they want to use the system but do not yet know how. They are willing to follow along step by step, willing to type code as instructed, willing to be patient. They have not yet committed to using the system in a real project; this tutorial is part of how they decide.

**Question answered.** *Where do I start?*

**Structure.** Sequential and pedagogical. A tutorial has:

- A title that names what will be built ("Getting started with wi::ecs: build your first component-based system")
- An opening that frames what the reader will accomplish and what they need
- A clear list of prerequisites (technical setup, assumed knowledge)
- A series of incremental steps, each adding something to a running example
- At each step, the working code so far and the new code being added
- Brief explanations between steps — what does this code do, why are we adding it now
- A finished result that demonstrates something tangible
- Pointers forward: what to read next once this tutorial is complete

The structure is sequential-as-progression. Unlike how-to (sequential-as-recipe) or reference (lookup-flat), the tutorial builds something cumulatively. The reader's mental model grows as the code grows.

**Voice discipline.**

- **Patient and inclusive.** Tutorials are the only quadrant where conversational warmth is appropriate. "We" is acceptable here ("we now have a component manager; let's add some components").
- **Hand-holding without condescension.** The reader chose this tutorial because they are starting from scratch. Treat them as capable adults who simply do not yet know this system.
- **Pacing controlled.** New ideas are introduced one at a time. Code complexity grows monotonically. Earlier code is referenced and reused, not abandoned.
- **Discoverable progress.** At each step the reader can run the code and see something. Long stretches of build-without-running break the learner's confidence.
- **Honest about scope.** A good tutorial is explicit about what it does not cover. "This tutorial does not cover serialization; for that, see [How to: Save and Load a Scene]."

**Anti-AI-tells specific to tutorials.**

- **Pacing failures (too fast).** AI tends to compress steps because it can hold the whole thing at once. Real tutorials slow down for the learner. The discipline: each step should introduce one concept and one or two new code constructs, not five.
- **Pacing failures (too slow).** The opposite failure: AI sometimes pads tutorial pacing with empty filler — "Now we are ready to take an exciting next step!" The discipline: every paragraph in a tutorial should add information or framing the learner needs.
- **Abandoning the learner mid-build.** AI sometimes shows code, calls it complete, and skips to the next concept without letting the learner verify their work. Real tutorials say "run this and you should see X" at every milestone.
- **Fake-friendly tone.** "Awesome! You did it!" — the saccharine register that AI uses when it thinks tutorials should be encouraging. Real tutorials are warm but adult. The discipline: write for an intelligent learner, not a child.
- **Hidden dependencies.** Tutorial code that requires setup not mentioned in the prerequisites. AI tends to skip over things like "you need a working build of Wicked Engine first." The discipline: list every prerequisite explicitly, including things the writer takes for granted.
- **Tutorial as reference dump.** AI sometimes writes "tutorials" that are really enumerations of API methods with brief examples for each. That's not a tutorial; it's a reference page formatted differently. The discipline: a tutorial builds *one specific thing*, not a tour of the API.
- **No closing arc.** AI tutorials sometimes end mid-stride without showing the learner the completed thing. Real tutorials end with "and this is what we built" — the result the learner can point at as evidence they have learned.

**Example fragment** (opening of a tutorial):

```
## Getting started with wi::ecs

In this tutorial we will build a small program that creates entities,
attaches components to them, iterates over those components, and
verifies the behaviour by printing results to the console. By the end
you will have a working ECS-based program in fewer than 100 lines of
code, and a clear sense of how wi::ecs is structured.

### What you need

- A working build of Wicked Engine (see [Building Wicked Engine] for
  setup instructions)
- A C++17 compiler
- About 30 minutes

### What we will build

A program that simulates 10 enemies on a 2D grid. Each enemy has a
position and a health value. The program will:

1. Create the 10 entities
2. Give each entity a Position and a Health component
3. Iterate over all positions and increment x by 1 (simulating a step)
4. Iterate over all healths and apply 5 damage
5. Print each entity's position and health

This is a deliberately small program — just enough to introduce the
core wi::ecs types without getting tangled in graphics, physics, or
serialization.

### Step 1: Define the components

Components in wi::ecs are plain C++ types. They have no required
base class; they are just data.
```

Note the specific scope statement, the time estimate, the explicit "what we will build" outcome, the immediate first-step.

---

## How the four quadrants relate

The quadrants are not independent. A complete documentation set is built so that each quadrant supports the others:

- **Tutorial** → **Reference**: a tutorial introduces an API method by using it, then links to reference for the full details.
- **Tutorial** → **Explanation**: a tutorial may introduce a concept, then link to explanation for the deeper background.
- **How-to** → **Reference**: how-tos show the API in use; reference is where the reader confirms each call's exact contract.
- **How-to** → **Explanation**: how-tos solve specific problems; explanation tells the reader why the solution is shaped the way it is.
- **Explanation** → **Reference**: explanation discusses design choices using specific API surface; reference documents that surface.
- **Reference** → **all three**: reference pages link to relevant tutorials, how-tos, and explanations for readers who want context.

The skill must produce these cross-links deliberately. Each page asks: which other pages does my reader need *next*?

A common failure pattern is when one quadrant tries to do another's work. Symptoms:

- A reference page tells you why something was designed this way (should be in explanation)
- A tutorial enumerates API methods (should be in reference)
- A how-to teaches the basics of the system (should be in tutorial)
- An explanation page provides step-by-step instructions (should be in how-to)

When a page starts drifting into another quadrant's territory, the question to ask is: *what is the reader doing right now? What state are they in?* If the answer doesn't match the current quadrant, the misplaced content should be moved or linked rather than included in place.

## Persona modalities for technical documentation

The skill's existing persona system assumes one persona writes a project. For technical documentation, this assumption needs adjustment. There are two viable patterns:

### Pattern A — One persona, four modes

A single engineer-documenter persona who writes in all four registers. The persona is one person — same name, same biography, same technical background — who happens to be skilled at switching between modes. This pattern works when the documentation set is small enough that consistency-of-author is achievable, or when the project genuinely has one technical writer.

For this pattern the persona document specifies all four modes:

```
- In reference mode: declarative, voice-suppressed, atomic per item
- In how-to mode: imperative, goal-aware, recipe-shaped
- In explanation mode: reasoned, trade-off-aware, narrative
- In tutorial mode: patient, paced, pedagogical
```

The persona's natural register is implicit; their mode shifts are deliberate.

### Pattern B — Four sub-personas under one project umbrella

Four distinct persona-modalities, each handled as a separate writing task. This pattern works for larger projects where the registers are written by different people on a team, or when one mode is so different from the others that pretending it's the same writer fails.

For this pattern there are four persona documents under one project:

```
project/
  writer/
    reference-persona.md       (engineer-documenter, voice-suppressed)
    howto-persona.md           (engineer-recipe-writer)
    explanation-persona.md     (engineer-explainer)
    tutorial-persona.md        (engineer-teacher)
```

Each persona has its own anti-AI-tells discipline, its own voice rules, its own examples-it-has-read.

### Choosing between patterns

Pattern A is simpler and produces more consistent voice across the docs set. Pattern B is more honest about the genuinely different registers. For most projects Pattern A is sufficient; for large enterprise documentation projects Pattern B may be warranted.

The default for the skill is **Pattern A with explicit mode-switching documented in the persona**.

## How this integrates with the skill phases

### Phase 0 — Persona

Build the engineer-documenter persona using Pattern A above. The persona must include:

- Technical background (what languages, what kinds of systems shipped, what documentation written before)
- Reading formation (which docs systems they admire — MSDN, Rust docs, Stripe docs, etc.)
- The four modes specified explicitly with discipline notes per mode
- Anti-AI-tells awareness for all four quadrants

### Phase 1 — Intake

Reading-level scope is "Adult specialist / academic" — disciplinary readers (developers in the relevant ecosystem). Cross-check that the user wants reference + how-to + explanation + tutorial, or only some subset. Many real projects need only a subset; the skill should not force a full quadrant set when only one or two are wanted.

Add to intake the **codebase-analysis question**: does the user have direct access to the source code for the documentation target? If yes, the skill can produce verifiable claims; if no, the skill can produce a conceptual draft with clearly-marked assumptions that need verification.

### Phase 2 — Codebase analysis (new for this register)

Before any documentation is drafted, the codebase must be analysed:

1. **Public API surface inventory.** List every documentable item: classes, methods, properties, free functions, types, macros. Source location for each.
2. **Dependency map.** Which items depend on which. This informs cross-references and tutorial ordering.
3. **Verification corpus.** A minimal build environment in which examples can be compiled and run. Without this, examples cannot be verified.
4. **Existing documentation review.** What already exists, what's good in it, what's missing or outdated.

The output of Phase 2 is a `docs-plan.md` that names every page to be produced, organized by quadrant, with cross-link plans.

### Phase 3 — (skipped or compressed)

Phase 3 (worldbuilding) does not apply to technical documentation in the traditional sense. The "world" is the codebase, which has been inventoried in Phase 2.

### Phase 4 — Writing

Each page is written in the appropriate quadrant's register. Per-page self-critique applies all standard checks (anti-AI-tells, language-naturalness) plus the quadrant-specific anti-AI-tells documented above. Reading-level for adult-specialist applies.

For projects of meaningful scope, work in **slices**:

- A slice is one tutorial + a few how-tos + the reference pages they touch + the explanations they invoke
- Complete one slice fully (all four quadrants for a coherent topic) before moving to the next
- This produces working documentation throughout the project rather than three completed quadrants and one unfinished one at the end

### Phase 5 — Manuscript finishing

Two finishing passes specific to technical documentation:

1. **Cross-reference validation.** Every "See Also" link, every link from how-to to reference, every link from tutorial to explanation, must point to a page that exists and that actually serves the reader at that moment. Broken links and "links to the wrong page" are the most common technical-doc bug.

2. **Correctness verification.** Every code example must be compiled and run in the verification corpus. Every type signature must match the actual source. Every claim about behaviour ("returns INVALID_INDEX if the entity is not present") must be verifiable from the source.

This pass is more demanding than the standard finishing passes for narrative work. Skipping it produces docs that are wrong; wrong docs are worse than no docs.

### Phase 6 — Assembly

Technical docs are typically assembled into a documentation site (Sphinx, Hugo, Docusaurus, Microsoft Docs, etc.) rather than a printable book. The skill should output content in a format the target site can ingest — usually Markdown with front-matter, sometimes reStructuredText or AsciiDoc. The user's choice of docs platform determines this.

For test projects without a target platform, plain Markdown with logical filenames and a manifest file (`docs-manifest.md` listing all pages with their quadrant and cross-links) is acceptable.

---

## A note on the limits

Technical documentation requires access to the source code or, failing that, very explicit marking of which claims are verifiable and which are inferential. The skill must not produce documentation that *looks* authoritative when in fact it is generated from speculation about how the code probably behaves.

When documenting code without source access, every page should carry an explicit caveat: "This documentation is based on inference from public interfaces and architectural descriptions; please verify against the actual implementation before relying on specific claims."

When documenting code *with* source access, this caveat is unnecessary, but the discipline of verification (compiling examples, checking signatures, validating behavioural claims) remains essential. AI-generated documentation that has not been verified against the source is — in the technical-writing community — reasonably regarded as worse than no documentation at all, because it carries the appearance of reliability without the substance.

The skill's standard for technical reference documentation should be: **every claim is either verified from the source, or marked as inferential**. There is no third category.
