### K-LEGACY-1 · blocker · obsolete-assumption
- Target: RND.ARCH.scene-sync (stance capability of L14), docs/00 s6 row 8, C-RSCENE
- Finding: The capability text defines the per-object render proxy mirror ("per-frame mirrored copy of every scene object ... CPU cost O(scene objects)"), the exact legacy L14 replaces. It contradicts C-RSCENE ("no per-object proxy mirror; O(changes)") and docs/00.
- Evidence: UE4/5 proxy sync cost scales with object count; delta-tracked persistent GPU scenes (UE5 GPU Scene, Frostbite, Unity DOTS hybrid renderer) are O(changes).
- Proposed change: Reword to "Change-tracked simulation-to-render extraction: per-frame deltas into the persistent instance scene (C-INSTANCES); cost O(changes); no per-object mirror". Add contradiction_terms to L14.

### K-LEGACY-2 · major · obsolete-assumption
- Target: UI.FW.architecture (stance capability of L35)
- Finding: Says view models are "refreshed by per-frame property polling through string-keyed bindings", which is L35's legacy verbatim; sibling UI.FW.logic says the opposite.
- Evidence: Change-notified, compile-time-resolved bindings (Slint, Unreal MVVM, Unity UI Toolkit runtime bindings, Flutter/SwiftUI observation).
- Proposed change: "retained UI with change-notified view models and bindings resolved at load/compile time; polling only in dev overlays". Add contradiction_terms 'property polling|string-keyed binding'.

### K-LEGACY-3 · major · obsolete-assumption
- Target: ED.ARCH.transactions (L38)
- Finding: "each undo step stores a full copy of the affected scene or asset state" is snapshot-based undo; L38 stance is serializable diff-based commands. It also cannot scale to 10^6-object worlds (ED.UI.outliner) or collaboration journals (ED.COLLAB.session-server).
- Evidence: command/patch-based transactions in Unreal Transactor, Godot UndoRedo, Figma/Automerge-style operation logs.
- Proposed change: "serializable, diff-based commands/transactions with inverse ops, journaled for collaboration". Add snapshot terms ('full copy of the affected').

### K-LEGACY-4 · major · obsolete-assumption
- Target: C-PHYS summary, PHY.ARCH.events (L19, L36)
- Finding: C-PHYS states contact events are "delivered per body through step-time callbacks so gameplay can react and modify bodies during the step", i.e. immediate callbacks plus mid-step mutation, contradicting PHY.ARCH.events (batched change sets, deferred mutations), PHY.ARCH.async and determinism/rollback requirements.
- Evidence: PhysX contact-modify callbacks / Havok listeners force serialization and break parallel step; Jolt and Rapier use buffered contact lists; Rapier and Jolt document mid-step mutation as unsafe.
- Proposed change: Contract text: batched contact/change-set output consumed at a declared point; mutation via deferred command buffers; an ADR-gated optional narrow contact-modification hook for solver-time filtering only. Add terms 'step-time callbacks|modify bodies during the step'.

### K-LEGACY-5 · major · obsolete-assumption
- Target: CORE.JOBS.degenerate vs RES.MGMT.no-stall, L16
- Finding: Shipping inline mode allows "blocking waits on the host thread for IO completion", a synchronous-IO exemption contradicting no-stall ("no blocking waits on host/OS-bound threads"). On web the main thread cannot legally block (Atomics.wait disallowed) and browser IO is async only; on consoles and mobile it causes watchdog/ANR and hitches.
- Evidence: WASM/Emscripten asyncify guidance; Android ANR; frame-hitch policy.
- Proposed change: Restrict the exemption to headless/tool/boot-before-first-present contexts; in cooperative mode IO completion is a yielded continuation on the host event loop.

### K-LEGACY-6 · major · omission
- Target: legacy-patterns.json (contradiction_terms), check.py coverage
- Finding: Only about 40 of 88 patterns carry contradiction_terms; L01-L18, L20-L22, L33, L35 etc. have none, so K-LEGACY-1..4 passed check.py. The tripwire is absent exactly where stance capabilities were corrupted.
- Evidence: the four defects above are stance capabilities of L14, L35, L38, L36/L19 (L38/L36 have terms that are too narrow).
- Proposed change: Add terms: L14 'mirrored copy|proxy mirror|O\(scene objects\)'; L35 'property polling|string-keyed bindings'; L38 'full copy of the affected'; L36/L19 'step-time callbacks|during the step'; L16 'blocking waits on the host'; L02 'per-object tick'; L03 'game thread|render thread'; L21 'tracing gc'; L33 'per-connection polling'.

### K-LEGACY-7 · minor · obsolete-assumption
- Target: QA.STRAT.flaky (L69)
- Finding: "rerun-based clearing" of quarantined tests is retry-until-green; stance says root-cause policy. Quarantined tests drop out of gate results with no expiry or owner.
- Evidence: Google/Meta flaky-test practice: quarantine with owner and deadline, rerun only for classification.
- Proposed change: "classification by rerun; quarantine bounded by owner and expiry; cleared only after root cause fix and N clean seeded runs".

### K-LEGACY-8 · minor · obsolete-assumption
- Target: PRF.METH.budgets (L70)
- Finding: Budget lines include "average frame-time" beside percentile lines; the average is the legacy metric.
- Evidence: C-BUDGET already uses p50/p99/p99.9.
- Proposed change: Replace with "median and p99/p99.9 frame time; averages reported only as secondary".

### K-LEGACY-9 · minor · omission
- Target: legacy-patterns.json, docs/00 s6 row 10, RES.MGMT.arbitration
- Finding: docs/00 names "independent streaming pools that compete" as replaced legacy, but no pattern exists in the catalogue, so no owner or check enforces it.
- Evidence: per-subsystem fixed texture/audio/mesh pools thrash on UMA (consoles, Apple silicon).
- Proposed change: Add L89 "Independent per-domain streaming pools", stance "single arbitrated budget", owner resource-streaming-architect, stance_capabilities [RES.MGMT.arbitration, CORE.MEM.uma], terms 'independent (?:streaming )?pools'.

### K-LEGACY-10 · minor · obsolete-assumption
- Target: ANM.RT.events ("notifies")
- Finding: Animation notifies are the classic immediate-callback path (L19) and are not among L19's stance capabilities.
- Evidence: UE AnimNotify fires gameplay code from the animation evaluation thread.
- Proposed change: Reword to "curves and timeline events emitted as batched tick-stamped events" and add ANM.RT.events to L19 stance_capabilities.
