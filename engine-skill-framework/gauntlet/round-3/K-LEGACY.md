# K-LEGACY · Anti-Legacy Critic · round 3

Scope: accidental legacy in capability wording, contracts, stances and the legacy catalogue. Nothing here repeats what check.py proves. check.py checks that each pattern's stance capabilities exist and that the justification owner is linked to them. It does not check whether the wording of a capability (a stance capability or any other) states the legacy pattern itself. Eleven capabilities do exactly that (findings 1–11).

### K-LEGACY-1 · major · wrong-boundary
- **Target:** CORE.OBJ.events, L19, C-ID, C-SEQ, entity-object-model
- **Finding:** The stance capability of L19 reads "global event bus with immediate synchronous listener dispatch by default". That is the legacy pattern L19 exists to forbid. It is the only stance capability for L19, and it sits in the L2 contract C-ID, which every gameplay skill consumes. C-SEQ also promises "event/track callbacks" with no deferral rule.
- **Evidence:** Synchronous observer dispatch runs listener code on the producer's worker while the producer is mid-update. This breaks declared access in C-FRAME, the premise of L01, L25 and CORE.FRAME.phase-violations. Listener order then becomes nondeterministic under work stealing (C-DET). Production precedent is the move away from immediate delegates toward deferred/batched messages: Bevy Events/Observers, which buffer and apply at command flush, and Unity DOTS, which uses no managed events in jobs.
- **Proposed change:** Reword CORE.OBJ.events to "Events & messaging: typed, deferred, batched event streams consumed at declared consumption points (C-FLOW mailboxes); immediate dispatch only within one owner's phase, by ADR; no process-global bus". Move events out of the C-ID summary into C-FLOW, or name it "deferred events". In C-SEQ, replace "event/track callbacks" with "track events delivered as deferred C-FLOW events".

### K-LEGACY-2 · major · obsolete-assumption
- **Target:** PHY.ARCH.stepping, L30, physics-architect
- **Finding:** PHY.ARCH.stepping reads "Variable-timestep stepping on the render frame delta & frame sync". That is L30 (frame-coupled variable-timestep simulation) stated as the physics default. It contradicts CORE.FRAME.fixed-step, PHY.ARCH.rewind/determinism and C-PHYS ("resimulate N ticks reproduces the state hash").
- **Evidence:** Rollback, lag compensation and lockstep need fixed ticks. Solver stability (TGS, XPBD) depends on dt, as in Gaffer "Fix Your Timestep". Box2D v3, Jolt and PhysX all recommend fixed substeps. Stepping on the render delta couples simulation to GPU load and refresh rate.
- **Proposed change:** Reword to "Fixed-step physics ticks (declared rate per C-FRAME cadence) with substepping and render interpolation; variable dt only for non-authoritative cosmetic layers, by ADR". Add PHY.ARCH.stepping to L30.stance_capabilities.

### K-LEGACY-3 · major · obsolete-assumption
- **Target:** CORE.JOBS.blocking, C-TASK, L16, L25, job-system-task-graph
- **Finding:** CORE.JOBS.blocking reads "Blocking & long-running tasks run inline on work-stealing workers (no dedicated lanes or compensating threads)". Blocking a work-stealing worker removes a core from the frame graph and can deadlock when every worker waits. This is the old "just call it from the job" habit.
- **Evidence:** TBB (task_arena, isolation), .NET ThreadPool hill-climbing and the Go runtime's handoff on syscalls all compensate or segregate blocking work. Naughty Dog fibers (GDC 2015) never block workers: they park the fiber. The framework's own CORE.JOBS.degenerate and RES.MGMT.no-stall demand no blocking waits.
- **Proposed change:** Reword to "Blocking policy: no blocking calls on work-stealing workers; waits suspend (fiber/coroutine) on completion tokens; unavoidable blocking or long-running work goes to declared long-running/IO lanes in the thread inventory (CORE.JOBS.thread-model); detection of blocking calls on workers in debug builds". Add a catalogue pattern (see K-LEGACY-12).

### K-LEGACY-4 · major · obsolete-assumption
- **Target:** CNT.COOK.ddc, C-COOK, content-pipeline-architect
- **Finding:** The derived-data cache is "keyed by source path & file modification time". That is make-era invalidation. It breaks on VCS checkout, where mtimes change and content does not, on renames, and on processor/toolchain version changes. It cannot be shared across machines or the cloud.
- **Evidence:** CNT.COOK.shared-cache, CNT.COOK.incremental-equivalence (L41) and C-COOK "cache keys, determinism class" all need content-addressed keys. Precedent: Bazel action keys, UE DDC keys (content hash + processor version GUID), and Unity Accelerator artifact hashes.
- **Proposed change:** Reword to "Content-addressed derived-data cache: key = hash(source content, processor id+version, settings, platform variant, dependency keys); no path or timestamp keys". Add a pattern L-new "Timestamp/path-keyed build and cook caches" with stance CNT.COOK.ddc and CNT.COOK.contract, owner content-pipeline-architect.

### K-LEGACY-5 · major · obsolete-assumption
- **Target:** RND.POST.effects, post-color-hdr, RND.POST.color, RND.POST.hdr-output
- **Finding:** The post chain (bloom, DoF, motion blur, lens) is "applied after tonemapping on display-referred output". That is the LDR/SDR-era pipeline. Physically based post must run on scene-referred linear HDR before display mapping. After tonemapping, bloom thresholds and energy are wrong, and HDR output (PQ/scRGB) then needs a separate chain.
- **Evidence:** Hable and Frostbite HDR (GDC 2017, "High Dynamic Range color grading and display in Frostbite"), ACES and OCIO pipelines, and UE/Unity HDRP all order post effects scene-referred before the output transform. Only grain and UI composition are display-referred.
- **Proposed change:** Reword to "Post chain on scene-referred linear HDR before display mapping; display-referred stage limited to output transform, grain/sharpen and UI composition". Add a pattern L-new "SDR/display-referred rendering pipeline" with stance RND.POST.color, RND.POST.effects and RND.POST.hdr-output, owner post-color-hdr.

### K-LEGACY-6 · major · obsolete-assumption
- **Target:** QA.STRAT.flaky, test-architect, L56, L57
- **Finding:** Flaky-test management is "automatic retry until green". This hides races and nondeterminism, the defect class that this framework's task-graph, lock-free and determinism stances make most likely. It also lets autonomous implementers pass gates by chance, which defeats QA.AGENT.test-integrity.
- **Evidence:** Google's flaky-test research (Micco, 2016; "De-Flake Your Tests") found retries mask real concurrency bugs. Retry-until-green is counted as a gate-weakening pattern. CORE.JOBS.test-modes and QA.ROBUST.concurrency exist to reproduce such failures, not to retry them away.
- **Proposed change:** Reword to "Flaky-test management: bounded reruns only for classification; any pass/fail disagreement is a defect attributed via seeded schedule replay (CORE.JOBS.test-modes); automatic quarantine with owner SLA; retries never convert red to green on a gate". Add a pattern L-new "Retry-until-green gates", owner test-architect.

### K-LEGACY-7 · major · obsolete-assumption
- **Target:** PRF.METH.budgets, performance-architect, C-BUDGET
- **Finding:** Budgets are "measured on the reference high-end PC and scaled proportionally to lower tiers". That is top-down, PC-first budgeting. It contradicts C-BUDGET ("per hardware tier × configuration × refresh class, derived from the performance model") and the scale-down mandate.
- **Evidence:** TBDR mobile, UMA consoles, handhelds and web do not scale linearly from a discrete-GPU PC. Bandwidth, thermal sustained clocks, tile memory and the CPU/GPU split differ in kind (Arm/Qualcomm mobile best-practice guides; Steam Deck 40 Hz/15 W modes). Budgets must be measured on each tier's reference device.
- **Proposed change:** Reword to "Budgets per tier measured on each tier's reference device (sustained thermal state), reconciled with PRF.METH.model; no proportional scaling from a higher tier". Add a pattern L-new "High-end-first budgets scaled down", owner performance-architect.

### K-LEGACY-8 · major · obsolete-assumption
- **Target:** BLD.REL.staged-rollout, packaging-release-patching, milestones (M-online exit)
- **Finding:** The capability id says staged rollout, but the wording says "Simultaneous global rollout to all players with post-release kill switches", which is a big-bang release. A milestone gate cites this capability.
- **Evidence:** Live titles and app stores use percentage and cohort rollout with health gating (Play staged rollouts, App Store phased release, canary server fleets per NET.SRV.lifecycle). Kill switches alone cannot undo client binaries already installed.
- **Proposed change:** Reword to "Staged/percentage rollout by cohort, region and platform with automated health gates (crash-free rate, perf, server errors), halt and rollback, plus post-release kill switches". Add a pattern L-new "Big-bang releases", owner packaging-release-patching.

### K-LEGACY-9 · major · other
- **Target:** NET.REP.compression, replication, C-REP
- **Finding:** The wording is "Delta compression against the previously sent snapshot". Over an unreliable channel the client may never have received the previous snapshot, so decoding fails or silently diverges under loss. Delta must be computed against the last snapshot the receiver acknowledged.
- **Evidence:** The Quake 3 network model, Gaffer "Snapshot Compression", Overwatch (GDC 2017) and UE Iris all use per-connection acked baselines. Because of this, O(changes) replication (L33) needs baseline bookkeeping per connection.
- **Proposed change:** Reword to "Delta compression against the last receiver-acknowledged baseline (per-connection baseline ring), quantization & bit packing". Add NET.REP.compression to L33.stance_capabilities.

### K-LEGACY-10 · major · obsolete-assumption
- **Target:** UI.LOC.strings, localization-i18n, GAM.NARR.lines
- **Finding:** String tables are "keyed by English source text". This is gettext-style keying. Fixing a typo in the source orphans every translation. Identical English strings with different meanings collide, and non-English source languages are impossible. GAM.NARR.lines already uses stable IDs, so the two formats disagree.
- **Evidence:** Production localization pipelines (UE FText namespace+key, XLIFF trans-unit ids) key on stable IDs, with source text, context and hash stored as metadata to detect stale translations.
- **Proposed change:** Reword to "String tables keyed by stable IDs with source text, context and source hash as metadata (stale-translation detection); any source language". Add a pattern L-new "Source-text-keyed localization", owner localization-i18n.

### K-LEGACY-11 · major · scale-down
- **Target:** PLAT.WEB.runtime, platform-web, CORE.JOBS.degenerate
- **Finding:** The wording "SharedArrayBuffer required; cross-origin isolation assumed on every host" makes WASM threads mandatory. Many web distribution hosts cannot send COOP/COEP headers: embedded iframes on portals, ad and SDK integrations, some CDNs. This contradicts CORE.JOBS.degenerate (0 workers) and the web/minimal configurations.
- **Evidence:** Browser portals and itch.io-style embeds commonly lack cross-origin isolation, and third-party iframes break under COEP. Unity and Godot web exports ship single-threaded builds because of this (Godot 4.3 restored the no-threads export).
- **Proposed change:** Reword to "WASM threads where cross-origin isolation is available; single-threaded inline mode (CORE.JOBS.degenerate) as a first-class shipping path; COI detection at startup; memory limits". Add a web configuration with no COI to milestones.

### K-LEGACY-12 · major · other
- **Target:** legacy-patterns.json (schema), check.py, ARCH.GOV.anti-legacy, docs/00 §6
- **Finding:** The catalogue only proves that stance capabilities exist. It cannot detect a capability, a contract, or even the stance capability itself (K-LEGACY-1) stating the legacy pattern. Eleven such contradictions passed three rounds. The catalogue also has no entries for the legacy stances in findings 3–8 and 10: blocking on workers, timestamp caches, display-referred post, retry-until-green, top-down budgets, big-bang release and source-text keys.
- **Evidence:** "0 errors, 0 warnings" from check.py, with CORE.OBJ.events and PHY.ARCH.stepping (stance-relevant to L19 and L30) contradicting their patterns.
- **Proposed change:** Add `contradiction_terms` (regexes) to each pattern, e.g. L19: `immediate synchronous|global event bus`; L30: `variable-timestep|render frame delta`. Have check.py scan capability names, contract summaries and skill purposes, and fail on a match unless an `adr_exceptions` entry names the capability. Add patterns L58–L64 for the stances above, with stance_capabilities CORE.JOBS.blocking, CNT.COOK.ddc, RND.POST.effects, QA.STRAT.flaky, PRF.METH.budgets, BLD.REL.staged-rollout and UI.LOC.strings, after they are reworded.

### K-LEGACY-13 · major · omission
- **Target:** legacy-patterns.json; WLD.SPACE.lwc, AUD.ARCH.engine, RND.SHADER.permutations, INP.ACT.mapping, GAM.SAVE.model, RND.RHI.present/CORE.FRAME.present-timeline, CORE.MEM.allocators, ARCH.STRUCT.platform-backends
- **Finding:** The catalogue omits several common runtime legacy patterns. Their modern stances exist only implicitly or not at all:
  - (a) float32 absolute world positions and whole-world origin rebasing;
  - (b) locks, allocation, IO or logging in the real-time audio callback (AUD.ARCH.engine says only "architecture & threading");
  - (c) combinatorial #ifdef über-shader permutation explosion;
  - (d) gameplay reading raw device state or key codes;
  - (e) saves as raw struct/memory dumps without a schema;
  - (f) fixed 30/60 Hz assumptions, sleep-based limiters and blocking vsync present;
  - (g) general-purpose heap allocation per item on hot paths;
  - (h) #ifdef platform sprawl instead of registered backends.
- **Evidence:** (a) UE5 moved to LWC doubles after UE4 origin rebasing (WorldComposition). (b) Ross Bencina, "Real-time audio programming 101"; the CORE.JOBS.thread-model "real-time thread rules" need a pattern to enforce them. (c) The UE/Unity shader-variant crises; RND.SHADER.permutation-budget exists without a pattern. (d) The Steam Input and GameInput action models. (e) GAM.SAVE.migration. (f) VRR/120 Hz, Reflex/Anti-Lag; PLAT.MOB.frame-pacing (Swappy). (g) CORE.MEM.allocators. (h) ARCH.STRUCT.platform-backends.
- **Proposed change:** Add eight patterns:

  | Pattern | Stance capabilities | Owner |
  |---|---|---|
  | (a) | WLD.SPACE.lwc, WLD.PART.lwc-policy | world-architect |
  | (b) | AUD.ARCH.engine, reworded "lock-free, allocation-free real-time audio render thread; control via lock-free queues", plus CORE.JOBS.thread-model | audio-architect |
  | (c) | RND.SHADER.permutation-budget, RND.SHADER.permutations | shader-system |
  | (d) | INP.ACT.mapping | input-system |
  | (e) | GAM.SAVE.model, GAM.SAVE.migration | persistence-save |
  | (f) | CORE.FRAME.present-timeline, CORE.FRAME.latency | frame-orchestration |
  | (g) | CORE.MEM.allocators, CORE.MEM.budget-enforcement | memory-allocators |
  | (h) | ARCH.STRUCT.platform-backends, PLAT.PAL.os | platform-architect |

### K-LEGACY-14 · major · wrong-boundary
- **Target:** L11 CORE.CONC.sync; L23/L40 ED.ARCH.separation; L31 RES.MGMT.dependencies; L36 PHY.ARCH.events; L37 ED.ARCH.process; L38 ED.ARCH.transactions; L39 WLD.MODEL.file-per-object; L42 NET.TRANS.reliability
- **Finding:** These stance capabilities have neutral names that do not state the stance. SKILL.md files are generated from capability wording, so the owning agents never see it. Examples:
  - ED.ARCH.process says "in-process vs out-of-process runtime", with nothing about async, cancellable jobs (L37).
  - ED.ARCH.transactions does not say diff-based (L38).
  - WLD.MODEL.file-per-object omits semantic merge (L39).
  - RES.MGMT.dependencies omits soft references (L31).
  - PHY.ARCH.events omits change sets and deferred commands (L36).
  - NET.TRANS.reliability omits UDP-class per-message classes (L42).
  - ED.ARCH.separation covers data only, while L23 is about editor code linked into shipping builds.
- **Evidence:** Compare the stances that are carried explicitly (GAM.FW.execution, CORE.REFL.static-default, UI.FW.architecture). Their wording contains the stance, and none of them regressed.
- **Proposed change:** Reword each capability to include its default stance:
  - CORE.CONC.sync: "no subsystem-wide locks on frame paths".
  - ED.ARCH.process: "asynchronous, cancellable editor jobs with progress; UI thread never blocks".
  - ED.ARCH.transactions: "serializable diff-based commands".
  - WLD.MODEL.file-per-object: "... with semantic merge".
  - RES.MGMT.dependencies: "soft references, budgeted dependency-aware loading".
  - PHY.ARCH.events: "... as batched change sets; queries batched, mutations deferred".
  - NET.TRANS.reliability: "unreliable-first channels with per-message reliability/ordering classes".
  - L23: add BLD.SYS.dev-surface-exclusion and ARCH.STRUCT.layering to stance_capabilities.

### K-LEGACY-15 · major · obsolete-assumption
- **Target:** L27, RND.RECON.framegen, RND.RECON.upscalers, PRF.LOAD.pacing-latency, C-BUDGET
- **Finding:** The new-dogma entry L27 covers only ECS and GPU-driven rendering. It misses the current industry crutch of treating upscaling and frame generation as the performance budget. Generated frames count toward "fps" while simulation rate and input latency degrade. No capability states that budgets and latency are judged on rendered, not generated, frames.
- **Evidence:** NVIDIA's DLSS Frame Generation guidance recommends a base frame rate of about 60 fps and pairing with Reflex. Digital Foundry and GDC 2024–25 discussion of titles shipped with frame gen or upscaling "required" for 60 fps targets. Console certification TRCs measure native frame pacing.
- **Proposed change:** Add a pattern L-new "Reconstruction/frame generation as budget substitute" (owner performance-architect), with stance RND.RECON.framegen, reworded "optional presentation layer; never counted toward simulation/latency budgets; minimum base rate per tier", plus PRF.LOAD.pacing-latency. Extend L27 detection to "virtualized geometry/VSM/RT mandated on tiers without workload evidence".

### K-LEGACY-16 · minor · other
- **Target:** docs/00-design-principles.md §6, legacy-patterns.json _doc
- **Finding:** §6 claims that every pattern names the capabilities carrying its stance "and check.py verifies them". check.py verifies existence and ownership, not the stance, so the claim overstates the guarantee (see K-LEGACY-1/2). The §6 table also has no row for fixed-step simulation, deferred events or content-addressed caches, although the capability data contradicts all three.
- **Evidence:** docs/00 line 86; the CORE.OBJ.events and PHY.ARCH.stepping wording.
- **Proposed change:** Change the sentence to "check.py verifies that they exist, are owned by the justification owner's subtree, and that no capability text matches a pattern's contradiction terms" (after K-LEGACY-12). Add §6 rows for L19/L30 (deferred events, fixed-step simulation) and for content-addressed derived data.
