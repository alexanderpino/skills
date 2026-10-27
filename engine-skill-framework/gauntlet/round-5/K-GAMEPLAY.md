### K-GAMEPLAY-1 · major · obsolete-assumption
- Target: UI.FW.architecture, legacy-patterns (stringly-typed/polling UI binding), CORE.REFL.static-default, C-UI
- Finding: The capability row text says "retained UI with view models refreshed by per-frame property polling through string-keyed bindings". That is exactly the legacy pattern the catalogue bans; skill purpose, C-UI and the catalogue stance say change-notified view models with load-time-resolved bindings. The generated docs/01 propagates the wrong text; an agent briefed from the row builds polling.
- Evidence: Unreal UMG property bindings poll every frame; Unity UI Toolkit/Noesis-style MVVM and Slate use change notification. CORE.REFL.static-default forbids string lookup on runtime paths.
- Proposed change: rewrite the row to "Retained UI; view models exposed via reflection with change notification, bindings resolved at load/compile time to IDs/offsets; polling only as an explicit opt-in adapter for non-notifying sources".

### K-GAMEPLAY-2 · major · missing-contract
- Target: GAM.AI.links, GAM.AI.following, GAM.MOVE.modes, C-NAV, C-MOVE, navigation-pathfinding
- Finding: Nav produces intents and off-mesh "special movement" but no row or contract connects it to character movement. GAM.AI.links has no contributor and nav does not consume C-MOVE/C-CHARCTRL. Nothing owns the nav-agent profile (radius, height, step, slope, climb/jump reach) that must equal the controller capsule/modes, nor AI as a move-request source through the same resimulatable move API (needed for server-authoritative prediction parity). Mantle, climb and jump links have no executor.
- Evidence: Unreal NavAgentProps synced with CharacterMovement and smart-link traversal via movement modes; Recast agent params must match the capsule or agents clip or stall.
- Proposed change: add GAM.MOVE.ai-drive (owner character-movement; contributors navigation-pathfinding, ai-behavior-perception) for steering-intent to move-request and link traversal by movement mode. Add GAM.AI.agent-profiles (owner navigation-pathfinding, contributors character-movement, character-physics) derived from movement/capsule data. Add character-movement as contributor of GAM.AI.links and GAM.AI.following. Document the C-NAV intents to C-MOVE flow in C-MOVE.

### K-GAMEPLAY-3 · major · omission
- Target: GAM.SAVE.settings, ED.UI.settings-editor, UI.FW.*, CORE.SCALE.profiles, INP.ACT.remapping
- Finding: Runtime player-facing settings have a store and an editor-side schema editor but no capability for the settings screen model: schema-driven categories from C-CFG entries, per-setting apply/needs-restart/dependency rules, display-mode change with timed revert, hardware-detected defaults, benchmark/auto-detect, reset-to-default, per-scope (device/user) presentation, and device-specific hiding (console-only, handheld). Every shipped game needs this; each game team would rebuild it and diverge on cert behaviours.
- Evidence: Unreal GameUserSettings plus Lyra settings registry; Unity has none and every title builds one; console TRC/XR rules on display-mode revert and safe defaults.
- Proposed change: add UI.FW.settings-model (owner ui-architect; contributors persistence-save, runtime-scalability, accessibility, input-system, audio-architect) plus a UI.TOOL.settings preview. Require GAM.SAVE.settings and CORE.SCALE.profiles to expose metadata (range, restart, dependency, platform visibility) on C-CFG entries.

### K-GAMEPLAY-4 · major · omission
- Target: UI.LOC.strings, UI.LOC.assets, UI.LOC.language-packs, AUD.CONTENT.dialogue, UI.TXT.fonts, PLAT.PAL.system-events
- Finding: No capability owns runtime active-locale management: OS/user locale detection, separate text, VO and subtitle language selection, fallback chains (regional to base, missing VO to text-only), live switch without restart with re-resolution of localized assets, fonts, VO packs and cached formatted text, and persisted choice. Rows cover tables, variants and packs, not the state machine that binds them.
- Evidence: Common cert/store requirement to honour system language; games ship "text EN, VO JP"; Unreal culture/asset-localization switching.
- Proposed change: add UI.LOC.runtime-locale (owner localization-i18n; contributors persistence-save, audio-content-runtime, text-fonts, resource-streaming-architect, platform-architect). Define the locale-change event and reload obligations in C-LOC.

### K-GAMEPLAY-5 · major · omission
- Target: GAM.FW.local-players, INP.ACT.local-mp, UI.FW.focus, GAM.SAVE.settings, AUD.ARCH.listeners, C-UI, C-CAMERA
- Finding: Local multiplayer is contracted (C-UI per-local-player roots and focus owners, C-CAMERA per-player rigs) but the capabilities implementing it are absent. GAM.FW.local-players lists only input-system as contributor, no ui-architect, gameplay-camera, persistence-save or accessibility. No row owns per-viewport HUD layout and per-player safe area, per-player subtitle placement, or multi-focus navigation with one focus owner per player. GAM.SAVE.settings scopes are device/user/cloud, with no per-local-player accessibility, controls or subtitle preferences (player 2 is a guest or a second platform user). Shared-screen menu ownership after a player disconnects is unowned.
- Evidence: Couch co-op titles (Overcooked, Halo split-screen, Mario Kart) need per-player HUD/viewport, per-player rebinding and assists, and controller-to-user pairing.
- Proposed change: add UI.FW.local-player-ui (owner ui-architect; contributors gameplay-architect, gameplay-camera, render-architect, accessibility) covering viewport-relative HUD, per-player focus and subtitles. Add contributors ui-architect, gameplay-camera, persistence-save, accessibility to GAM.FW.local-players. Add a per-local-player scope to GAM.SAVE.settings and C-A11YRT settings.

### K-GAMEPLAY-6 · major · dependency-error
- Target: skills tool_consumes for text-fonts, facial-animation, cinematics-sequencer, ik-procedural-animation, animation-runtime, gameplay-data, ui-architect, crowd-simulation
- Finding: Several skills own cook-time builders, importers or viewport tools but declare no contract for them; check.py only requires any tool contract. text-fonts owns UI.TXT.font-subsetting (asset-cook-processors contributes) and has empty tool_consumes; facial-animation owns ANM.FACE.capture (import) and per-locale lip-sync bake without C-IMPORT/C-COOK; cinematics-sequencer owns take-recorder import, movie render and preload manifests without C-COOK/C-IMPORT or C-EDVIEW; gameplay-data owns CSV/Sheets round-trip and table cook without C-IMPORT/C-COOK; ANM.TOOL.rigging (ik-procedural), ANM.TOOL.2d-rigging (animation-runtime), ANM.TOOL.sequencer-editor and ANM.TOOL.facial edit in viewports (gizmos, picking, scrub) without C-EDVIEW; UI.TOOL.preview lacks C-EDPREVIEW.
- Evidence: The framework's own rule "format owner owns the builder, pipeline hosts it through C-COOK". Without the edge, the tools configuration proof cannot show the builder reaches the cook host, and agents get no contract to file change requests against.
- Proposed change: add C-COOK to text-fonts, facial-animation, cinematics-sequencer, gameplay-data and crowd-simulation (lane and flow-field bake); C-IMPORT to facial-animation, cinematics-sequencer and gameplay-data; C-EDVIEW to ik-procedural-animation, animation-runtime, facial-animation and cinematics-sequencer; C-EDPREVIEW to ik-procedural-animation, facial-animation and ui-architect. Extend check.py so each TOOL capability's contributors imply the matching contract edge.

### K-GAMEPLAY-7 · major · omission
- Target: ANM.CINE.sequencer, ANM.CINE.validation, GAM.NARR.scenes, ANM.FACE.lipsync, C-SEQ
- Finding: Only generated dialogue scenes get per-locale retiming (GAM.NARR.scenes). Hand-authored cutscenes with VO tracks have no capability for locale variant tracks or durations, locale-specific subtitle timing, per-locale lip-sync curves, or shot-length reconciliation when localized VO is longer. Validation lists only "timing conflicts". C-SEQ consumes C-LOC only optionally.
- Evidence: Localized German/Russian VO routinely exceeds English timing; Unreal Sequencer localized audio and subtitle tracks, Cyberpunk 2077 per-language lip-sync.
- Proposed change: add ANM.CINE.localized-tracks (owner cinematics-sequencer; contributors localization-i18n, audio-content-runtime, facial-animation, narrative-dialogue): per-locale audio, subtitle and viseme variants, duration policy (hold, stretch, extend shot) and a validation hook per locale. Make C-LOC a non-optional consumption for the sequencer's tools side.

### K-GAMEPLAY-8 · major · omission
- Target: GAM.AI.navmesh, GAM.AI.pathfinding, WLD.*, GAM.SYS.building, PHY.DEST.propagation, C-NAV
- Finding: Navigation data as a streamed, world-partitioned layer has no row: per-cell navmesh cook and streaming with world cells, cross-cell stitching and hierarchical graphs, server-side residency without rendering, invoker-style regional generation, and dynamic invalidation from destruction, building and voxel edits. GAM.AI.navmesh has no contributors and C-NAV consumes C-WORLD only optionally. PHY.DEST.propagation states a destruction-to-navigation update with no receiving capability.
- Evidence: Unreal World Partition navmesh streaming and nav invokers; Horizon and Assassin's Creed large-world nav tiles.
- Proposed change: add GAM.AI.nav-streaming (owner navigation-pathfinding; contributors world-architect, world-data-model, destruction-fracture, voxel-worlds, resource-streaming-architect), tagged openworld and sandbox. Add contributors to GAM.AI.navmesh and a dynamic-invalidation input to C-NAV.

### K-GAMEPLAY-9 · minor · missing-contract
- Target: INP.ACT.glyphs, UI.TXT.rich, UI.LOC.messageformat, INP.ACT.confirm-swap
- Finding: Localized text that embeds an input action (for example "Press {Jump} to vault") must resolve at runtime to a per-device glyph or a per-locale key name and re-resolve on device change. INP.ACT.glyphs has no contributors; UI.TXT.rich and UI.LOC.messageformat do not mention an action-glyph argument type.
- Evidence: Prompt glyph placeholders are standard (Unreal Common UI input actions in rich text, Steam Input glyph APIs).
- Proposed change: add contributors ui-architect, text-fonts and localization-i18n to INP.ACT.glyphs, and a typed input-action argument in UI.LOC.messageformat and UI.TXT.rich that gather and validation tools understand.

### K-GAMEPLAY-10 · minor · omission
- Target: AUD.DSP.dynamics, AUD.DSP.mixer, UI.A11Y.requirements, GAM.SAVE.settings
- Finding: No capability covers the player-facing audio mix options that XAG audio guidance and platform loudness rules expect: per-category volume presets, mono downmix, speech-priority/dialogue boost, dynamic-range profiles per output (TV, headphones, handheld speakers), and speaker-layout selection. UI.A11Y rows cover captions and visualization only.
- Evidence: Xbox Accessibility Guidelines (audio), Dolby/EBU R128 device profiles, console loudness targets, The Last of Us Part II audio accessibility options.
- Proposed change: add AUD.DSP.user-mix (owner audio-dsp-mixing; contributors accessibility, persistence-save, platform-architect) exposing these as C-CFG settings, with a UI.A11Y.validation check.

### K-GAMEPLAY-11 · minor · scale-down
- Target: ANM.FACE.lipsync, facial-animation profiles, ANM.RT.2d, GAM.NARR.lines
- Finding: The `minimal` profile is defined as narrative-centric games, but facial-animation ships only in lite3d/std3d. Visual-novel and 2D portraits or sprite mouth-flap driven by dialogue lines, per-locale, have no owner.
- Evidence: 2D dialogue-driven games use viseme-driven sprite or Spine swaps (Live2D, Spine attachments).
- Proposed change: add ANM.RT.2d-speech (owner animation-runtime; contributors facial-animation, narrative-dialogue, audio-content-runtime) tagged minimal and min2d, driven by C-DIALOGUE line timing/visemes.

### K-GAMEPLAY-12 · minor · overlap
- Target: UI.A11Y.motion, GAM.CAM.comfort, UI.FW.animation, RND.POST.colorblind, GAM.SYS.cues
- Finding: "Motion reduction & photosensitivity" (accessibility) and "Camera comfort & accessibility motion options" (gameplay-camera) describe overlapping settings. UI.A11Y.motion has no contributors, although the consumers include camera shake, UI transitions, post effects (motion blur, flashes), VFX and cue flash and hit-stop. No single canonical reduced-motion/flash-limit setting contract is stated.
- Evidence: Xbox and Game Accessibility Guidelines; WCAG 2.3 flash thresholds; C-VIEW already assigns shake scaling to C-CAMERA, so the split is partial.
- Proposed change: make UI.A11Y.motion the sole setting owner, with contributors gameplay-camera, ui-architect, post-color-hdr, vfx-particles and gameplay-systems-toolkit. Reword GAM.CAM.comfort to camera-side consumption of that setting, and add a runtime flash-limiter hook (luminance-change budget) tested by QA.CERT.photosensitivity.
