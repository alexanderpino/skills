### K-COMPLETE-1 · major · omission
- Target: GAM.SYS (gameplay-systems-toolkit), CORE.FRAME.time, C-SAVE, C-DET, C-REPL
- Finding: No capability for a game-time timer / latent-action service (delays, cooldown timers, "wait N seconds" in level scripts, timers scaled by CORE.FRAME.time dilation/pause). "timer" appears only as PLAT.PAL.clocks (hardware timer precision). Without an owner, each system will hand-roll wall-clock timers, which break replay/rollback (XC.DET), are lost on save (GAM.SAVE.checkpoints), do not pause with menus, and are not replicated.
- Evidence: UE TimerManager/latent actions, Unity coroutines/Invoke, Godot Timer nodes are core modules in every shipped engine; the classic bug class is wall-clock timers desyncing replays.
- Sweep: (1) shipped module sets.
- Proposed change: add GAM.SYS.timers "Game-time timers & latent actions: time-domain aware, pausable, saveable, replicated/rewindable, deterministic order" owned by gameplay-systems-toolkit, contributors persistence-save, frame-orchestration, prediction-rollback; reference from GAM.SCR.level-scripting.

### K-COMPLETE-2 · minor · omission
- Target: CORE.SCALE.autodetect, GAM.SAVE.settings, OBS.CRASH, RND.RHI.crash
- Finding: No startup crash-loop detection / safe-mode boot with automatic rollback of player settings (graphics preset, driver-specific options, mods) to last-known-good. Device-lost recovery and settings persistence exist, but nothing owns the case where a settings combination crashes before any UI is reachable.
- Evidence: Shipped PC titles ship "reset graphics settings after crash" / launch-safe-mode paths; UE has -safe style flags; players otherwise cannot recover without deleting files, and it drives support cost.
- Sweep: (2) production pipeline post-launch, (3) PC hardware diversity.
- Proposed change: add CORE.SCALE.safe-boot (owner runtime-scalability; contributors persistence-save, crash-diagnostics): crash-marker at boot, N-strike rollback of settings snapshot, mod/plugin disable, telemetry event.

### K-COMPLETE-3 · minor · omission
- Target: ANM.CINE, RND.ARCH.multi-display, cinematics-sequencer expertise "virtual production"
- Finding: The skill lists "virtual production" expertise but no capability covers multi-machine synchronized rendering (frame lock / genlock / swap-lock, cluster sync of sim state) or timecode (LTC/SMPTE) sync for sequencer and live-link. RND.ARCH.multi-display is single-machine spanned output. It is not in the radar non-goals, so it is neither owned nor excluded.
- Evidence: UE nDisplay / ICVFX, simulators, location-based venues and arcade clusters; timecode/genlock are required for LED-wall and broadcast use.
- Sweep: (3) genres/use-cases, (1) UE5 module set.
- Proposed change: either add RND.ARCH.cluster-sync + ANM.CINE.timecode (X or M) or add an explicit radar non_goal "synchronized render clusters / genlock" and drop "virtual production" from the expertise list.

### K-COMPLETE-4 · minor · omission
- Target: BLD.SYS, GAM.SCR.debug, CORE.TYPES, XC.DX
- Finding: No capability for developer-IDE integration: compile_commands.json/project generation, debugger visualizers/pretty-printers (natvis, lldb/gdb formatters) for engine containers, handles, entity ids and strong types, and language-server support for script/data schemas. Only script DAP debugging is present. Autonomous agents and humans both depend on compilation databases and readable debugger views of ECS/handles.
- Evidence: UE ships natvis and IDE project generators; Godot ships LSP; clangd-based agents need compile_commands.json.
- Sweep: (5) engineering disciplines, (1) engines.
- Proposed change: add BLD.SYS.ide-integration (build-system-toolchains; contributors containers-core-types, scripting-runtime, developer-experience-docs) with a conformance check that every new handle/container type ships a visualizer.

### K-COMPLETE-5 · minor · omission
- Target: PLAT.LIVE.events, UI.LOC.cldr, PLAT.SVC.trusted-time
- Finding: Time-gated live events, daily/weekly resets and seasons have no owned calendar semantics: UTC vs player-local vs server-region time, DST, tz database updates on frozen/offline platforms, calendar systems. "timezone/calendar/daylight" appears nowhere in data or docs.
- Evidence: Daily-reset and event-boundary bugs around DST and clock changes are a standard live-service defect class; IANA tzdata changes several times per year and OS copies lag on consoles.
- Sweep: (4) platform/business, (2) live ops.
- Proposed change: extend PLAT.LIVE.events (or add PLAT.LIVE.calendar) to own time-zone/DST policy and tzdata delivery via C-CFG/remote config, with trusted-time as authority and UI.LOC.cldr for display.
