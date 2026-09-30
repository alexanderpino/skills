# K-SIM: Physics and Simulation Critic, round 4

### K-SIM-1 · major · scale-down
- Target: PHY.2D.*, physics-2d, collision-detection, rigid-body-dynamics, PHY.COL.queries/filtering/ccd, PHY.DYN.joints/islands/kinematic, PHY.CTRL.platforms/sensing; configs indie-2d-client, sandbox-2d-client, fighting-2d-rollback-client, rts-2d-massim-client
- Finding: In every min2d configuration these capabilities are absent from the closure (checked with Model.cap_in_configuration): scene queries, filtering/layers, CCD, joints, sleeping, kinematic bodies, platform riding, ground/ledge sensing. physics-2d owns only dynamics, controllers, determinism, shape-gen and cellular. No capability covers tilemap colliders (composite/merged colliders, one-way platforms, slopes, runtime tile edits), 2D runtime collider regeneration for destructible bitmap terrain (Worms, Noita-style), 2D sensors/triggers, or 2D ropes/joints. PHY.2D.shape-gen covers sprites only.
- Evidence: Box2D v3 and Rapier2D ship queries, joints, sensors, CCD and one-way platforms as core features. Tilemap collision merging is the dominant 2D collision source (Unity CompositeCollider2D, Godot TileSet physics layers).
- Proposed change: add capabilities owned by physics-2d: PHY.2D.queries-filtering, PHY.2D.joints-ropes, PHY.2D.ccd-sensors, PHY.2D.tilemap-collision (E), PHY.2D.runtime-build (E, contributors terrain/destruction-fracture/render-2d-vector). Rename PHY.2D.dynamics to state what it includes. Add contributor render-2d-vector to the tilemap capability.

### K-SIM-2 · major · missing-contract
- Target: C-PHYS, C-MOVE, character-physics (provides nothing), PHY.CTRL.character/platforms/sensing, GAM.MOVE.networked
- Finding: character-movement consumes only C-PHYS, but the C-PHYS summary (bodies, shapes, queries, contact events, stepping) does not include a controller primitive. Collide-and-slide, step/slope/ledge, up-vector, moving-platform carry and push-vs-dynamic-body are owned by character-physics, which provides no contract. GAM.MOVE.networked needs a controller that can be re-stepped from an arbitrary snapshot, with a deterministic per-move step independent of the world step. Nothing states this, and the oracle author cannot write conformance for it.
- Evidence: Unreal CMC vs Mover, and Jolt CharacterVirtual vs PhysX CCT. Rollback movement needs stateless or snapshotable controller state and query-based moves.
- Proposed change: add contract C-CHARCTRL (layer 3, owner character-physics, requires C-PHYS, oracle_author simulation-validation, conformance: resimulate N moves from a snapshot reproduces state). C-MOVE requires it. Middleware backends implement it via PHY.ARCH.middleware-layer.

### K-SIM-3 · major · maturity-error
- Target: NET.PRED.physics (E), PHY.ARCH.rewind (E), PHY.CTRL.vehicle-net, C-PHYS conformance clause
- Finding: "Networked physics" is one E capability. Predicted general rigid-body physics with rollback and partial (island-limited) resimulation is not established. Middleware such as PhysX and Jolt does not restore solver warm-start caches or partial islands. Unreal's Chaos network-physics prediction is beta or experimental, and Rocket League's is a bespoke Bullet fork. Established approaches are: server-authoritative snapshot interpolation/extrapolation (Fiedler), deterministic lockstep, and rollback of characters plus a few vehicles. The C-PHYS conformance claim (restore + resimulate reproduces the hash) is asserted for any backend.
- Evidence: Rocket League GDC 2018 "It IS Rocket Science"; Fiedler "Networked Physics" series; Unreal Network Physics (UE 5.4/5.5, experimental); Jolt SaveState is full-state only.
- Proposed change: split NET.PRED.physics into (a) server-auth replicated dynamic bodies with interpolation/extrapolation and error smoothing (E), (b) predicted physics with rollback and partial resim (M, radar entry with fallback to (a)), (c) deterministic lockstep physics (E, only for backends declaring the deterministic level). Split PHY.ARCH.rewind into full snapshot/hash/collider history (E) and partial-island resim (M). Restrict the C-PHYS conformance clause to the declared level.

### K-SIM-4 · major · omission
- Target: replication (no C-PHYS consumption), NET.REP.state, NET.PRED.physics, PHY.ARCH.events, NET.ARCH.distributed-authority
- Finding: No capability or contract turns the physics active set into replicated state. replication consumes C-ECS/C-SPATIAL but not C-PHYS, and the principles say subsystem contracts are ECS-independent. Physics-body replication needs the sleeping flag, quantized pose/velocity, priority by significance, extrapolation of dynamic props, ownership hand-off of props and vehicles between clients and server, and bandwidth budgeting for debris. NET.PRED.physics is the only home, and it is a prediction skill with a "no physics solver" boundary.
- Evidence: Rocket League/Fiedler state-compression schemes, Halo Reach, Unreal Iris physics replication, Sea of Thieves ship replication.
- Proposed change: add capability NET.REP.physics-bodies (owner replication, contributors physics-architect and prediction-rollback). Add optional C-PHYS to replication.consumes, and have C-PHYS expose an active-set/change-set output (already implied by L36) for replication. Route vehicle and prop authority hand-off through NET.ARCH.distributed-authority with this feed.

### K-SIM-5 · major · scale-down
- Target: profiles of cloth-deformables, destruction-fracture, fluid-simulation, character-physics; configs lite-3d-*, online-3d-server, aaa server, rts-2d-massim-client, sandbox-2d-client
- Finding: Profile membership is skill-wide. Every lite3d build (mobile, portable, XR standalone) closes over cloth-deformables and destruction-fracture, so the minimum 3D configuration pays for cloth, hair, fracture and debris systems. Every server configuration includes cloth-deformables, although cloth and hair are cosmetic and have no authoritative role. Ropes and cables can be gameplay. 2D massim and sandbox configs pull fluid-simulation (3D SPH/FLIP) through the massim/sandbox tags, while their cellular fluid capability is owned by physics-2d.
- Evidence: Mobile 3D titles use bone-chain secondary motion instead of cloth. Dedicated servers strip cosmetic simulation (Fortnite, Overwatch). The radar already names "bone-chain dynamics" as the hair fallback.
- Proposed change: drop lite3d from cloth-deformables and destruction-fracture, and add an addon profile (for example "physfx"). Tag cosmetic capabilities (PHY.SOFT.cloth, hair-sim, softbody) as client-only through capability-level target tags. Keep ropes and structural destruction available on server. Retag fluid-simulation profiles to aaa and sandbox-3d only. Point the lite3d fallback at ANM secondary-motion springs.

### K-SIM-6 · major · wrong-owner
- Target: physics-architect (22 capabilities), PHY.ARCH.events/streaming/persistence/rewind/multi-world/debug-capture/fields/materials/middleware-layer/fixed-point-backend/gpu/async/lwc/local-frames
- Finding: The lead owns 22 capabilities against 9 to 11 for the experts. Half are implementation of the shared physics-world runtime (handles, batched event pipeline, streaming insertion, dehydrate/rehydrate, capture, force fields, middleware adapter, fixed-point backend, GPU offload). The lead is therefore the decider, the implementer and the middleware patch owner, and becomes the single-agent bottleneck for every physics change. That runs against the brief's "few orchestrators, many focused experts". PHY.ARCH.events also duplicates contact generation that collision-detection and rigid-body-dynamics implement.
- Evidence: Jolt, PhysX and Havok all separate architecture policy from the integration and runtime layer. Engines with a physics lead keep an "integration" team (UE Chaos integration vs Chaos core).
- Proposed change: add expert physics-runtime-integration (parent physics-architect, workstream simulation) owning world, events, streaming, persistence, rewind (mechanics), multi-world, debug-capture, fields, materials, middleware-layer, fixed-point-backend, gpu, async, lwc. The lead keeps build-integrate, determinism, lod, stepping policy, local-frames, tier-transitions, learned-surrogates and validation.

### K-SIM-7 · major · omission
- Target: CORE.SCALE.actuators, CORE.FRAME.fixed-step, PHY.ARCH.stepping, PHY.ARCH.lod, GAM.AI.mass, QA.SIM.stability-suite
- Finding: The actuator registry lists frame cap, dynres, significance, VFX, animation rate and workers. It has no simulation actuators (physics substeps/solver iterations, active-body cap, CCD/query budgets, cloth/fluid particle counts, mass-agent counts), and no simulation overrun policy. Nothing bounds fixed-step catch-up (max substeps, time dilation, the accumulator "spiral of death"). Only NET.SESS.overload registers server actuators. The governor cannot shed simulation load on a mobile or portable tier.
- Evidence: Fiedler "Fix Your Timestep"; Box2D and Jolt expose iteration and substep knobs for this purpose. Console titles cap substeps and dilate time.
- Proposed change: add PHY.ARCH.budget-degradation (owner physics-architect) with the actuator set registered into CORE.SCALE.actuators, and add a fixed-step overrun policy to CORE.FRAME.fixed-step or CORE.FRAME.time (bounded catch-up, dilation vs drop, determinism-safe for lockstep, where the cadence must not change). Crowd and systems-simulation register their own actuators.

### K-SIM-8 · major · other
- Target: CORE.FRAME.sim-schedule, CORE.FRAME.phases, CORE.FRAME.access-model, ANM.ARCH.sync
- Finding: CORE.FRAME.sim-schedule states "fixed sequence; declared access used only for validation". CORE.FRAME.phases, the access-model and design principle 00 line 90 say ordering is derived from declared access. The two regimes are never reconciled. Contributors omit ik-procedural-animation (ragdoll and IK are post-physics), cloth-deformables (post-animation, pre-render), vehicle-physics, destruction-fracture, crowd-simulation, ai-behavior-perception and gameplay-systems-toolkit. The schedule does not state the split coupling: pre-physics animation/root motion and kinematic bodies, then step, then post-physics IK/ragdoll/cloth/hit queries, then gameplay reactions. That split is where physics-animation-gameplay one-frame-lag bugs come from.
- Evidence: Unreal tick groups (PrePhysics, DuringPhysics, PostPhysics); Naughty Dog GDC "Parallelizing the Naughty Dog Engine"; Overwatch ECS GDC 2017.
- Proposed change: state in CORE.FRAME.sim-schedule and principle 00 that the simulation sub-schedule is a fixed, deterministic topological order (never derived by the scheduler), and that everything else is derived from access declarations. Add the missing contributors. Define named simulation slots (pre-physics animation, physics step, post-physics animation/cloth, gameplay reaction, replication extract) as a checked artifact.

### K-SIM-9 · minor · maturity-error
- Target: PHY.FLUID.gpu (E), PHY.FLUID.particles (M), PHY.FLUID.grid (M), radar entry "Particle & GPU fluids"
- Finding: GPU fluid solvers are E while the particle and grid fluids they run are M. The radar entry is titled "Particle & GPU fluids" but lists only particles and grid, so PHY.FLUID.gpu has no fallback or revisit trigger. An established GPU solver for emerging techniques is inconsistent.
- Evidence: Niagara Fluids is beta; the radar itself cites Flex titles only.
- Proposed change: set PHY.FLUID.gpu to M and add it to the radar entry, or merge it into particles/grid.

### K-SIM-10 · major · overlap
- Target: PHY.2D.cellular (physics-2d), GAM.SIM.fields (systems-simulation), PHY.FLUID.grid (fluid-simulation), systems-simulation non_responsibilities, voxel-worlds
- Finding: Three skills claim grid/cellular simulation. physics-2d owns falling-sand and liquid/gas/heat grids, GAM.SIM.fields owns diffusion and cellular spread, and fluid-simulation owns grid smoke and fire. The systems-simulation non-responsibility "Cellular fluids" points to fluid-simulation, but the capability is owned by physics-2d. 3D voxel cellular liquids (Minecraft-style flow, Teardown-style debris and smoke, Space Engineers) have no owner, because physics-2d is min2d only. sandbox-online-server (std3d+sandbox) has none of PHY.2D.cellular.
- Evidence: Noita (falling-sand engine, GDC 2019); Minecraft fluid update rules; Teardown voxel physics.
- Proposed change: create one owner for deterministic discrete grid/cellular simulation (systems-simulation) covering the 2D and 3D voxel cases, and move PHY.2D.cellular there. fluid-simulation keeps continuum and particle solvers. Fix the non-responsibility wording in systems-simulation and physics-2d.

### K-SIM-11 · major · other
- Target: untrusted-inputs "assets", "mods", "ugc-graphs"; PHY.COL.cook, PHY.COL.runtime-build, PHY.COL.decomposition, PHY.DEST.procedural, PHY.SOFT.*
- Finding: The registry has no input for collision and simulation data from mods and UGC. Runtime collision generation from UGC meshes and cooked collision blobs (BVH, convex hulls, heightfields, fracture/cloth assets) are consumed by the server and by peers. The generic assets limits (size/depth/count) do not bound geometric validity or cook time. Degenerate geometry can spin GJK/EPA, cooking or convex decomposition, and it can trigger huge hulls or unbounded contact counts. That is a DoS on an authoritative server.
- Evidence: PhysX and Bullet cooked-data and mesh-parsing CVEs; Havok and PhysX add hull vertex and triangle limits and validation for exactly this reason.
- Proposed change: add untrusted-input "physics-assets" (validating_owner collision-detection or physics-architect, parser_owners package-formats-vfs, trust hostile-remote for UGC, mode harness, limits hull vertices, triangle count, cook time budget, body/constraint count). Require runtime cook of UGC collision to be async, budgeted and sandboxed. Add a fuzz target for cooked-collision deserialization.

### K-SIM-12 · minor · omission
- Target: PRF.BENCH.*, PRF.METH.budgets, QA.SIM.stability-suite, PHY.ARCH.lod
- Finding: No capability owns simulation worst-case cost. QA.SIM.stability-suite measures penetration and energy drift, not step cost. PRF.BENCH.scale-content is generic synthetic worlds. Contact storms, pile-ups, explosion-to-debris bursts, query storms, mass-agent spikes and rollback-resim spikes are the tail-latency cases that break fixed-step budgets. PRF.NET.resim-cost covers resim only.
- Evidence: Physics hitches are dominated by tail cases (island wake-ups, CCD bursts). Jolt and Box2D publish worst-case benchmark scenes.
- Proposed change: add PRF.BENCH.sim-worst-case (owner perf-benchmarking, contributors physics-architect, crowd-simulation, destruction-fracture) and per-tier simulation step budgets in PRF.METH.budgets, tied to PHY.ARCH.budget-degradation.

### K-SIM-13 · minor · omission
- Target: data/legacy-patterns.json (only L36 and L30 cover physics and simulation)
- Finding: The catalogue has no legacy pattern for: discrete-only collision patched with speed caps and thick walls (tunnelling); an always-awake single global world without sleeping, active sets or simulation LOD; a rollback or lockstep design over a backend that cannot restore its solver caches; synchronous per-caller scene queries from AI, audio or gameplay (L36 mentions mid-step queries only for mutation).
- Evidence: Common in early Unity/Unreal-era projects; PHY.COL.ccd, PHY.DYN.islands and PHY.ARCH.lod carry the stances.
- Proposed change: add L75 "Discrete-only collision with speed clamps" (stance PHY.COL.ccd), L76 "Unbounded always-awake physics world" (PHY.DYN.islands, PHY.ARCH.lod, PHY.ARCH.tier-transitions), L77 "Rollback over non-restorable physics state" (PHY.ARCH.rewind, NET.PRED.sync-test), all with justification_owner physics-architect.

### K-SIM-14 · minor · missing-contract
- Target: RND.GRAPH.external-work, PHY.ARCH.gpu, PHY.FLUID.gpu, PHY.SOFT.cloth, RND.VFX.gpu-sim, C-RG
- Finding: The external-work arbiter registers streaming, decompression, scene deltas, AS builds and VT pages, but not GPU simulation producers (GPU fluids, cloth, GPU physics offload, crowd VAT). Nothing states when gameplay-relevant GPU simulation results are read back to the CPU, or that latency-tolerant asynchronous readback keeps determinism. Fluid and cloth consume C-RG optionally, so their async-compute placement and per-frame byte budgets are unowned.
- Evidence: PhysX GPU rigid-body and Flex pipelines; async readback latency of 2 to 3 frames on explicit APIs.
- Proposed change: add GPU simulation as registered producers in RND.GRAPH.external-work with priority, deadline and readback policy. State the gameplay-visible GPU results rule (tick-stamped, latched, not part of the deterministic state) in PHY.ARCH.gpu.
