# K-ARCH · Engine Architecture Critic · Round 3

### K-ARCH-1 · major · other
- **Target:** contracts.json `oracle_author` (40 of 110 code contracts, e.g. C-TYPES, C-MOD, C-MEM, C-SYNC, C-ID, C-RHI, C-SHADER, C-MATIF, C-RT, C-INSTANCES, C-GEOLOD, C-VT, C-LIGHT, C-GI, C-COLOR, C-TRANSLUCENT, C-NETLINK, C-REP, C-PREDICT, C-SERVER, C-SHARD, C-NAV, C-SCRIPT, C-SAVE, C-GAMEDATA, C-ABILITY, C-AI, C-AIAGENT, C-CROWD, C-EDIT, C-A11YRT, C-DEVUI, C-VCS, C-AUTOMATION, C-BUILD, C-PKG, C-TESTHOST, C-PCG, C-GPUTIER, C-ANIM); crosscutting.json `independence`; ARCH.ORG.independence; ARCH.ORG.staffing; docs/00 §2.
- **Finding:** docs/00 §2 says implementer-vs-oracle-author independence "is enforced by keeping each pair in different workstreams", because the workstream is the co-hosting unit. The data does not do this. In 40 contracts the oracle author sits in the same workstream as the owner or implementers. In some cases the oracle author is the implementer's own lead: C-TYPES→core-runtime-architect, C-TESTHOST→test-architect, C-PKG→build-release-architect, C-AUTOMATION→editor-architect, C-CROWD→gameplay-architect. For C-RHI, all five backends and the oracle author (gpu-memory-resources) are in `rendering`. The independence matrix only lists the sentinel pair (test-architect, owning-skill). check.py only rejects "oracle == sole implementer". Under ARCH.ORG.staffing, a small organization co-hosts a whole workstream in one agent, so that agent writes both the implementation and the acceptance suite that judges it.
- **Evidence:** This contradicts the framework's own anti-gaming premise (§6 last row, QA.AGENT.oracle-independence). Agents grading work they control is exactly the failure mode that QA.AGENT.* exists to stop, and a small co-hosted setup produces it by construction.
- **Proposed change:** Expand the independence matrix per contract: generate pairs (oracle_author, owner) and (oracle_author, each implementer) and have check.py require different workstreams. Reassign the 40 same-workstream oracle authors, preferably to quality-workstream validators (see K-ARCH-2). Correct the §2 sentence until the data matches it.

### K-ARCH-2 · major · wrong-owner
- **Target:** contracts.json oracle_author for C-PAL (accessibility), C-EDHOST (fluid-simulation), C-SIGN (modding-ugc), C-ML (anti-cheat-integrity), C-RTAS (spatial-audio-acoustics), C-VEHICLE (audio-content-runtime), C-ECS (audio-architect), C-RES (audio-dsp-mixing), C-DET (character-movement), C-FRAME (ai-behavior-perception), C-MATH (animation-runtime), C-INTEGRITY (platform-services), C-GPUMEM (async-io-storage).
- **Finding:** These oracle authors look chosen to satisfy "not the sole implementer", not for expertise. Each is a peripheral consumer that uses one slice of the contract and lacks its domain. Some examples:
  - The PAL conformance suite (suspend/resume quiesce, clock-domain correlation, thread QoS) is written by accessibility.
  - The editor-host suite is written by a fluid solver.
  - Crypto and signature conformance (C-SIGN) is written by modding-ugc.
  - Determinism conformance (C-DET, the float and ordered-reduction rules) is written by a gameplay movement skill.
  - The whole-engine frame scheduler (C-FRAME) is judged by the AI skill.
- **Evidence:** Consumer-driven contract testing (Pact-style) adds cases from consumers. It does not make one arbitrary consumer the acceptance authority. Crypto conformance needs known-answer and Wycheproof-class vectors, which modding has no mandate to know. C-TEST already says consumer-contributed cases are merged into the owner's suite. A single consumer as oracle author will leave out everything its slice does not use.
- **Proposed change:** Pick oracle authors by domain competence plus independence:
  - rendering contracts → render-validation;
  - physics, animation, audio, network, C-DET, C-SNAPSHOT and C-REPLAY → simulation-validation;
  - C-SIGN → security-engineering;
  - L0–L2 foundation contracts (C-PAL, C-MEM, C-TASK, C-FRAME, C-ECS, C-RES, C-IO, C-GPUMEM) → a new quality-workstream expert, `foundation-conformance`, or robustness-fuzzing plus test-architect;
  - editor contracts → functional-automation-soak.
  Consumers keep a `consumer_cases` list per contract.

### K-ARCH-3 · major · other
- **Target:** ARCH.ORG.escalation, docs/00 §2 ("A dispute inside one lead's subtree is settled by that lead. Only cross-workstream disputes reach engine-architect"), skills.json workstreams.
- **Finding:** Six workstreams contain more than one lead or cross-cutting subtree:
  - rendering: render-architect, gpu-platform-architect;
  - simulation: physics-architect, animation-architect;
  - content: content-pipeline-architect, resource-streaming-architect;
  - quality: test-architect, security-engineering;
  - online: network-architect, security-engineering (anti-cheat-integrity);
  - foundation: core-runtime-architect plus four cross-cutting skills.
  A dispute between two leads in the same workstream is neither inside one subtree nor cross-workstream, so no arbiter is named. These are the highest-friction seams:
  - ragdoll/root-motion (physics vs animation);
  - ray-tracing-infrastructure sits under gpu-platform-architect but binds C-RSCENE, C-INSTANCES and C-MATIF from render-architect;
  - cook vs runtime format (content vs streaming);
  - anti-cheat validators vs replication.
- **Evidence:** Across ~150 agents, an unrouted dispute class either stalls or defaults to engine-architect. That makes the root the arbiter for intra-workstream fights and defeats delegated arbitration.
- **Proposed change:** Add `arbiter` to each workstream in skills.json (e.g. rendering→render-architect, simulation→physics-architect with animation-architect as co-signer for sim-schedule, content→resource-streaming-architect for runtime and content-pipeline-architect for cook). Alternatively, state in ARCH.ORG.escalation that same-workstream cross-lead disputes go to engine-architect, and have check.py require that every workstream with more than one lead declares its arbiter.

### K-ARCH-4 · major · wrong-boundary
- **Target:** ui-architect (21 capabilities, UI.FW.*), content-pipeline-architect (20: CNT.ID.*, CNT.COOK.architecture/ddc/distributed/shared-cache/world-build/on-demand/gpu-steps, CNT.VAL.*), physics-architect (18: PHY.ARCH.rewind/streaming/async/events/fields/multi-world/local-frames/tier-transitions), platform-architect (27).
- **Finding:** Several leads are also the main implementers of large runtime or tool subsystems. ui-architect owns the whole retained UI runtime (layout engine, styling, animation, world UI, maps service, loading screens, subtitle presentation), and no UI-runtime expert exists. content-pipeline-architect owns the DDC, distributed cooking, cook server and world-build graph. physics-architect owns rewind, streaming insertion, force fields, multi-world and local simulation frames. The lead then arbitrates disputes in its own subtree while being a party to them: text-fonts or localization vs UI layout, asset-cook-processors vs the cook host, rigid-body-dynamics vs physics-architect on rewind. It also concentrates implementation load where arbitration is needed.
- **Evidence:** This violates the brief's "few orchestrators, many focused experts" and the framework's own decider-vs-party separation. Production UI stacks (Coherent Gameface/Prysm, Noesis, Slate/UMG, UI Toolkit) are staffed as subsystems in their own right. DDC and distributed cook (the Unreal Zen server, the FASTBuild-class cache) is an infrastructure specialty separate from cook architecture.
- **Proposed change:**
  - Create `ui-runtime-framework` (expert, ui workstream) owning UI.FW.layout, styling, animation, world-ui, performance, maps, loading-screens, subtitles and validation. ui-architect keeps architecture, C-UI and designer-tool policy.
  - Create `cook-infrastructure` (tool expert) owning CNT.COOK.ddc, distributed, shared-cache, on-demand and world-build.
  - Create `physics-world-runtime` (expert) owning PHY.ARCH.rewind, streaming, async, events, fields, multi-world, local-frames and tier-transitions.
  - Each lead keeps policy and contract ownership.

### K-ARCH-5 · major · overlap
- **Target:** gameplay-systems-toolkit (purpose), gameplay-camera, GAM.CAM.rigs, GAM.CAM.photo, C-VIEW (oracle_author, consumes).
- **Finding:** gameplay-systems-toolkit's purpose still claims "camera system … photo mode". Those territories are owned by gameplay-camera (GAM.CAM.rigs, GAM.CAM.photo). gameplay-systems-toolkit's non-responsibilities route only cinematic cameras away, not gameplay cameras. It also consumes C-VIEW as a mandatory dependency and is C-VIEW's oracle author, which is a leftover of the old ownership. Two agents will generate SKILL.md files that both claim camera rigs and photo mode.
- **Evidence:** The SKILL.md is generated from the purpose, so wording overlap becomes real double ownership. check.py sees only capability rows.
- **Proposed change:** Remove "camera system" and "photo mode" from gameplay-systems-toolkit's purpose. Add the non-responsibility ["Gameplay cameras & photo mode", "gameplay-camera"]. Make C-VIEW optional for it (`C-VIEW?`). Move C-VIEW's oracle_author to a non-consumer validator (per K-ARCH-2).

### K-ARCH-6 · major · wrong-boundary
- **Target:** C-PHYS summary, C-MOVE, GAM.MOVE.modes, GAM.MOVE.root-motion, character-physics, character-movement.
- **Finding:** C-PHYS (L3, physics-architect) says it contains "character controllers (movement modes, move requests, root-motion hand-off)". Movement modes and root-motion authority belong to character-movement (GAM.MOVE.modes, GAM.MOVE.root-motion, C-MOVE L4). character-physics' non-responsibility says "Movement modes & networked movement → character-movement". So the physics contract carries a gameplay-layer concept, and two contracts define the move request and root-motion hand-off.
- **Evidence:** This follows the classic split (Unreal: CharacterMovementComponent as gameplay vs the physics character controller; Jolt: CharacterVirtual as a primitive). The physics contract exposes the collide-and-slide primitive (desired displacement in, resolved displacement and ground state out). Movement modes are a layer above.
- **Proposed change:** Rewrite the C-PHYS text as "character controller primitive: desired displacement → resolved displacement, ground/step/slope sensing, platform interaction". Move "movement modes, move requests, root-motion hand-off" to C-MOVE only.

### K-ARCH-7 · major · obsolete-assumption
- **Target:** CORE.OBJ.events, C-ID summary ("events"), entity-object-model purpose, legacy-patterns L19, C-FLOW, CORE.OBJ.world-instances, GAM.SYS.messages.
- **Finding:** CORE.OBJ.events reads "global event bus with immediate synchronous listener dispatch by default". That contradicts L19, the legacy pattern whose stance capability is this row ("Deferred batched events at declared consumption points"). It also contradicts C-FLOW as the default data path, the no-hidden-globals and multiple-world-instances stances (a global bus is process-global state), and ARCH.STRUCT.binding (no per-item dispatch across contracts). GAM.SYS.messages builds on it, so the legacy behavior spreads into gameplay.
- **Evidence:** Immediate cross-subsystem callbacks run on the producer's thread in the middle of an update. That serializes the task graph and hides data races. This is why modern engines use deferred, phase-drained event queues (Bevy Events/Observers drained at schedule points; Unity DOTS command buffers; Unreal Mass signals).
- **Proposed change:** CORE.OBJ.events → "Events & messaging: world-scoped, typed, batched event channels drained at declared C-FRAME consumption points; synchronous dispatch only intra-subsystem, by ADR". Update the C-ID summary to match.

### K-ARCH-8 · major · obsolete-assumption
- **Target:** PHY.ARCH.stepping, physics-architect purpose, CORE.FRAME.fixed-step, legacy L30, C-PHYS conformance.
- **Finding:** PHY.ARCH.stepping says "Variable-timestep stepping on the render frame delta". L30 lists exactly this as legacy, with the stance "fixed/declared step with interpolation" (CORE.FRAME.fixed-step). The C-PHYS conformance clause ("restore + resimulate N ticks reproduces the state hash") cannot hold if dt depends on the render frame. So do NET.PRED.rollback, lockstep and PHY.ARCH.rewind.
- **Evidence:** "Fix Your Timestep" (Fiedler), plus Jolt, Havok and PhysX guidance and every rollback title: a variable dt changes stacking stability and makes the simulation irreproducible.
- **Proposed change:** PHY.ARCH.stepping → "Fixed-step (or declared-step) physics on the C-FRAME simulation clock, substepping, and interpolation/extrapolation to render time". Add PHY.ARCH.stepping to L30's stance_capabilities.

### K-ARCH-9 · major · other
- **Target:** CNT.COOK.ddc, content-pipeline-architect purpose, CNT.COOK.incremental-equivalence, CNT.COOK.shared-cache, untrusted-inputs `shared-ddc`, C-COOK.
- **Finding:** CNT.COOK.ddc says "Derived-data cache keyed by source path & file modification time". This contradicts:
  - the owner's purpose ("derived-data cache and content-addressed store");
  - C-COOK "cache keys";
  - the untrusted-input registry ("shared-ddc: content-addressed/verified");
  - CNT.COOK.incremental-equivalence (incremental equals clean cook).
  Keys based on path and mtime are not reproducible across machines, so a shared or cloud DDC returns stale or wrong artifacts after checkout, clock skew or a processor version change.
- **Evidence:** Unreal DDC keys (processor version GUID plus hashed inputs), Bazel/Buck2 action keys and Zen storage are all content-addressed with processor version and parameters in the key.
- **Proposed change:** CNT.COOK.ddc → "Derived-data cache keyed by content hash of all inputs + processor version + parameters + target platform (content-addressed; path/mtime only as a local stat-cache accelerator)".

### K-ARCH-10 · major · obsolete-assumption
- **Target:** CORE.JOBS.blocking, C-TASK ("blocking rules"), RES.MGMT.no-stall, CORE.JOBS.pinned, CORE.JOBS.priorities.
- **Finding:** CORE.JOBS.blocking says "Blocking & long-running tasks run inline on work-stealing workers (no dedicated lanes or compensating threads)". A blocking call on a worker removes that core from the frame graph. With N workers, N blocked tasks deadlock or starve the frame. This contradicts the latency-critical lanes in CORE.JOBS.priorities, the pinned lanes, and RES.MGMT.no-stall.
- **Evidence:** Production schedulers isolate blocking work: TBB arenas/task_group isolation, .NET thread-pool hill-climbing injection, Unreal background/named-thread priorities, and fiber-based waits that yield (Naughty Dog, GDC 2015). A blocking-work policy is also in the task-model ADR B2.
- **Proposed change:** CORE.JOBS.blocking → "Blocking policy: frame tasks never block; waits yield (fiber/coroutine) or go to a bounded long-running/blocking lane with its own thread budget in the thread inventory; OS-blocking calls only on declared lanes".

### K-ARCH-11 · major · scale-down
- **Target:** PLAT.WEB.runtime, CORE.JOBS.degenerate, platform-web purpose.
- **Finding:** PLAT.WEB.runtime says "SharedArrayBuffer required; cross-origin isolation assumed on every host". CORE.JOBS.degenerate exists specifically to run the same task graph on 0–2 workers for the web. The platform capability makes threads mandatory, so the single-threaded web path has no owner on the platform side.
- **Evidence:** COOP/COEP headers are unavailable on many distribution hosts (embedded portals, iframes on game portals, some CDNs), and third-party embeds break under COEP. Unity and Godot 4.3+ ship a no-threads web export for this reason.
- **Proposed change:** PLAT.WEB.runtime → "WASM threads when cross-origin isolated; single-threaded (0-worker inline) build variant otherwise; host capability detection". Add a web configuration without threads (for example indie-2d-client on web, no-COI) as a checked point.

### K-ARCH-12 · major · other
- **Target:** UI.LOC.strings, C-LOC ("String IDs"), crosscutting `localizability` obligation ("use stable string IDs"), GAM.NARR.lines.
- **Finding:** UI.LOC.strings reads "String tables keyed by English source text". That contradicts C-LOC, the localizability obligation owned by the same skill, and the stable line IDs in narrative-dialogue. Keys based on source text break every translation when an English typo is fixed and collide on homographs ("Close" as the verb vs the adjective).
- **Evidence:** Production pipelines key by stable IDs with source text as a field (Unreal FText namespace+key, Unity Localization key tables, XLIFF resname).
- **Proposed change:** UI.LOC.strings → "String tables keyed by stable IDs (namespace + key) with source text, context and max-length metadata".

### K-ARCH-13 · major · other
- **Target:** PRF.METH.budgets, C-BUDGET, performance-architect purpose.
- **Finding:** PRF.METH.budgets says budgets are "measured on the reference high-end PC and scaled proportionally to lower tiers". C-BUDGET and the owner's purpose define budgets per hardware tier × configuration × refresh class. Proportional scaling is wrong for scale-down: TBDR bandwidth, UMA memory, thermal throttling and different binding tiers make cost ratios non-linear. The web and mobile paths even use different code (CPU-submitted tier).
- **Evidence:** Mobile studios (Arm, Qualcomm guidance; Genshin/CoD Mobile talks) budget on target devices at sustained thermal state. Console budgets come from the console, not from PC.
- **Proposed change:** PRF.METH.budgets → "Budgets derived per tier from the performance model and validated on each tier's reference device (sustained/thermal state), never scaled from another tier".

### K-ARCH-14 · major · other
- **Target:** QA.STRAT.flaky, QA.AGENT.test-integrity, QA.AGENT.gate-canaries.
- **Finding:** QA.STRAT.flaky says "automatic retry until green; the owning skill quarantines persistent offenders". Retrying until green turns every non-deterministic failure (races, uninitialized memory, ordering bugs) into a pass. The owning skill is the implementer, so it decides whether its own test gets quarantined. This undermines test-integrity and oracle independence.
- **Evidence:** Google's flaky-test research and Chromium/Mozilla practice: a bounded retry records the flake, quarantine is decided by the test owner or oracle author, and flake rate is tracked as a defect signal.
- **Proposed change:** QA.STRAT.flaky → "Bounded retry that records the flake as a failure signal; quarantine decided by the contract's oracle_author/test-architect with an expiry; flake rate is a gate metric".

### K-ARCH-15 · minor · overlap
- **Target:** C-GAMEDATA summary, GAM.SYS.tags, GAM.TOOL.tags-abilities, C-ABILITY.
- **Finding:** C-GAMEDATA (gameplay-data) claims "gameplay tag registry and tag queries". The tags capability and tag dictionary tooling are owned by gameplay-systems-toolkit, whose C-ABILITY also offers "tag queries". Two contracts define the tag registry.
- **Evidence:** A tag registry is one shared namespace (Unreal GameplayTagsManager). Two owners produce two tag spaces.
- **Proposed change:** Remove "gameplay tag registry and tag queries" from C-GAMEDATA. Tags are defined only in C-ABILITY. Alternatively, move GAM.SYS.tags and GAM.TOOL.tags-abilities (tag dictionary part) to gameplay-data and drop tags from C-ABILITY. Pick one.

### K-ARCH-16 · minor · overlap
- **Target:** global-illumination purpose vs RND.RT.sdf-scene; fluid-simulation purpose vs WLD.ENV.water-interaction; perf-benchmarking purpose / PRF.BENCH.regression vs BLD.CI.bisection; C-TYPES summary vs CORE.TYPES.crypto / C-SIGN; C-NETLINK summary ("Sessions") vs C-NETSESSION; C-AI "environment query service" vs C-ENV.
- **Finding:** These are residual overlaps in purpose or summary wording that check.py cannot see:
  - global-illumination claims "SDF scene representations", but the SDF tracing scene is owned by ray-tracing-infrastructure.
  - fluid-simulation claims "shallow-water simulation", but water-ocean owns WLD.ENV.water-interaction.
  - perf-benchmarking claims bisection, although ARCH.ORG.triage names BLD.CI.bisection the single bisection engine.
  - C-TYPES still mentions a crypto primitives wrapper (garbled as "hashinggraphic"), which now belongs to security-runtime.
  - C-NETLINK calls itself "Network links & sessions".
  - C-AI and C-ENV both call themselves an "environment query service".
- **Evidence:** Purposes and summaries become SKILL.md and contract text, so each item is a second claim on the same territory.
- **Proposed change:** Edit the wording:
  - GI: "consumes SDF/software ray queries via C-RTAS".
  - fluid-simulation: drop "shallow-water".
  - PRF.BENCH.regression: "regression detection (bisection via BLD.CI.bisection)".
  - C-TYPES: drop crypto.
  - C-NETLINK: rename to "Network links & channels".
  - C-AI: "AI environment/tactical queries (EQS class)".

### K-ARCH-17 · minor · other
- **Target:** non_responsibilities of robustness-fuzzing, ml-inference-runtime, gpu-platform-architect, research-evidence, certification-compliance, gpu-performance, render-validation.
- **Finding:** These route to a real skill (so check.py passes) but to the wrong one:
  - robustness-fuzzing: "Fixing parsers → serialization-schema". The registry has more than 40 validating owners, so this should route to owning-skill.
  - ml-inference-runtime: "GPU queue/budget arbitration of C-MLGPU work → gpu-platform-architect". No gpu-platform-architect capability covers queue arbitration; RND.GRAPH.async and RND.GRAPH.external-work (render-graph-scheduling) do.
  - gpu-platform-architect's list of individual API backends omits rhi-console.
  - research-evidence: "Making the decision (the owning skill does…) → architecture-governance" contradicts its own text.
  - certification-compliance: "Implementing platform features → platform-architect". This belongs to the platform experts or owning-skill.
  - gpu-performance: "Shader authoring for features → render-architect". render-validation: "Fixing rendering features → render-architect". Both should route to owning-skill.
- **Evidence:** Misroutes send work to leads or skills without the territory, which becomes escalation noise across about 150 agents.
- **Proposed change:** Retarget as described. Have check.py require that a non-responsibility targeting a specific skill names a skill that owns or leads a capability matching the routed text's area, or use `owning-skill`.

### K-ARCH-18 · minor · overlap
- **Target:** PLAT.MOB.frame-pacing, CORE.SCALE.actuators ("frame-rate cap/refresh selection"), CORE.FRAME.latency, CORE.FRAME.present-timeline.
- **Finding:** Three owners claim refresh-rate or frame-rate selection and pacing: platform-mobile ("Mobile frame pacing & refresh-rate selection"), runtime-scalability (the actuator) and frame-orchestration (pacing). PLAT.MOB.thermal was already reduced to "signal backends, no independent control loop", but frame pacing was not.
- **Evidence:** Swappy/Android Frame Pacing and CADisplayLink preferred rates are PAL mechanisms. The decision belongs to one loop (the governor) and the timeline to C-PRESENT.
- **Proposed change:** PLAT.MOB.frame-pacing → "Mobile present-rate/pacing backends (Swappy, preferredFrameRateRange) implementing C-PRESENT/C-PAL; no independent selection".

### K-ARCH-19 · minor · scale-down
- **Target:** fluid-simulation profiles ['aaa','sandbox','massim'], PHY.FLUID.cellular, systems-simulation non-responsibility "Cellular fluids → fluid-simulation".
- **Finding:** PHY.FLUID.cellular is explicitly "2D-capable, deterministic", the falling-sand/Noita class of game. Its skill is included only with aaa, sandbox or massim. A min2d game needing it must add `sandbox`, which is described as voxel/buildable worlds and pulls in voxel-worlds (a 3D chunked-block skill with mandatory C-WORLD, C-PHYS and C-PCG).
- **Evidence:** The brief asks for scale-down. Cellular simulation is a defining mechanic of several 2D indie titles.
- **Proposed change:** Add `min2d` (with capability-level profiles `aaa`/`sandbox` on PHY.FLUID.particles/grid/gpu) to fluid-simulation, or move PHY.FLUID.cellular into systems-simulation (whose GAM.SIM.fields is the same substrate) and add a min2d configuration that uses it.

### K-ARCH-20 · minor · other
- **Target:** BLD.REL.staged-rollout.
- **Finding:** The capability id says "staged-rollout" but the text says "Simultaneous global rollout to all players with post-release kill switches". Kill switches only limit damage after every player is already exposed. Id and text contradict each other.
- **Evidence:** Store-supported percentage rollouts (Google Play staged rollouts, App Store phased release) and canary server fleets are standard practice for live titles.
- **Proposed change:** BLD.REL.staged-rollout → "Staged/percentage rollouts (store phased release, canary server fleets) with health gates, halt/rollback and kill switches".
