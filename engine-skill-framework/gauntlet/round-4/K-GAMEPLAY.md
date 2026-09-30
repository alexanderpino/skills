# K-GAMEPLAY — Game Systems and Content Critic, round 4

### K-GAMEPLAY-1 · major · wrong-owner
- Target: AUD.CONTENT.dialogue; narrative-dialogue; audio-content-runtime; facial-animation
- Finding: AUD.CONTENT.dialogue ("VO playback & ducking for C-DIALOGUE lines") is owned by narrative-dialogue. narrative-dialogue lists "VO playback -> audio-content-runtime" as a non-responsibility, and facial-animation says "Dialogue playback -> audio-content-runtime". audio-content-runtime's purpose includes "dialogue and VO". narrative-dialogue does not consume C-AUDIO, so its owner could not implement the row. check.py cannot see this.
- Evidence: the skill's own non_responsibilities contradict the capability row. Wwise/FMOD dialogue systems and UE dialogue waves put playback, voice priority and ducking in the audio layer. The line database stays in narrative.
- Proposed change: set AUD.CONTENT.dialogue owner to audio-content-runtime with contributors [narrative-dialogue, localization-i18n]. Add C-DIALOGUE to audio-content-runtime consumes (already there, optional) and keep narrative-dialogue free of C-AUDIO.

### K-GAMEPLAY-2 · major · omission
- Target: accessibility (purpose); UI.A11Y.*; QA.CERT.photosensitivity; post-color-hdr; vfx-particles; cinematics-sequencer
- Finding: accessibility's purpose claims "motion and photosensitivity options". No capability implements them. The only photosensitivity row is QA.CERT.photosensitivity, which is late certification testing. There is no runtime flash/luminance/pattern limiter or reduced-flash mode. Nothing owns the authoring-time flash analysis of VFX, cutscenes and UI, and no contract lets VFX, sequencer and UI honour a "reduced flashing" setting.
- Evidence: Harding/ITU-R BT.1702 and WCAG 2.3.1 are the cited basis (docs/07). XAG 117 and GAG both call for flash reduction. Shipped titles (Fortnite, TLOU2, Forza) ship reduced-flash or flash-limit options because retrofitting is expensive.
- Proposed change: add UI.A11Y.photosensitivity (owner accessibility; contributors post-color-hdr, vfx-particles, cinematics-sequencer, ui-architect, certification-compliance). It covers the runtime luminance-flash and red-flash limiter plus the C-A11YRT setting. Add UI.TOOL.flash-analysis and a CNT.VAL validator that runs on cooked sequences and VFX. Keep QA.CERT.photosensitivity as the sign-off.

### K-GAMEPLAY-3 · major · omission
- Target: narrative-dialogue; gameplay-data; cinematics-sequencer; gameplay-camera; input-system; CNT.VAL.submit-gate
- Finding: ANM, AUD, PHY, NAV/AI, UI and A11Y each have a *.validation capability. The content-heavy domains have none: dialogue and narrative graphs, gameplay data, sequencer, camera and action maps. Missing checks include dead-end and unreachable dialogue nodes, soft-lock detection, fact/flag define-use consistency, and per-locale VO, caption and loc-key coverage. Also missing are data-table referential and range integrity, sequencer binding and missing-track checks, camera collision and clipping sweeps, and unbound-action and conflicting-context checks. CNT.VAL.submit-gate says "domain validators registered via hooks", but nothing registers these.
- Evidence: shipped narrative pipelines (articy, Ink and Yarn linters, Baldur's Gate 3 dialogue tooling) treat branch-coverage and flag-consistency checking as basic. Soft-locks are a leading defect class in narrative RPGs.
- Proposed change: add GAM.NARR.validation (narrative-dialogue; contributors localization-i18n, audio-content-runtime, accessibility). Add GAM.DATA.validation, ANM.CINE.validation, GAM.CAM.validation and INP.ACT.validation. Each registers with CNT.VAL.submit-gate and is oracle-authored outside its owner.

### K-GAMEPLAY-4 · major · omission
- Target: CORE.FRAME.time; GAM.SYS.impacts; GAM.SYS.abilities; C-ABILITY; animation-runtime; audio-content-runtime; vfx-particles; gameplay-camera
- Finding: two feedback ("game feel") concerns have no owner.
  - Local time scale. CORE.FRAME.time covers only global real, game, dilation and pause. There is no per-entity or per-team time scale (hit-stop, bullet-time on a subset, slow-mo on the hit pair) that animation, physics, VFX, audio, abilities and movement all obey consistently. In fighting-2d-rollback it must also be deterministic frame data.
  - Gameplay cues. SYS.impacts routes only surface-type impacts. There is no replicated, predicted, cosmetic-only "gameplay cue" channel that fans out from an effect or ability to VFX, audio, animation, camera shake, haptics and decals, with relevancy, LOD and dedupe under prediction rollback.
- Evidence: UE's Gameplay Cues (Lyra, GDC "Lyra" and GAS docs) are the shipped reference. Hit-stop is standard in action and fighting titles (Street Fighter 6 frame data; Sakurai's game-feel talks). Without an owner each subsystem invents its own timescale.
- Proposed change: add CORE.FRAME.local-time-scale (frame-orchestration; contributors animation-architect, physics-architect, audio-content-runtime, vfx-particles, gameplay-architect) and GAM.SYS.cues (gameplay-systems-toolkit; contributors prediction-rollback, replication, gameplay-camera, input-devices-haptics). Extend C-ABILITY with the cue interface.

### K-GAMEPLAY-5 · major · omission
- Target: C-ANIM; ANM.RT.blending; ANM.GRAPH.graph; ANM.TOOL.asset-editor; GAM.SYS.abilities; GAM.SYS.hit-detection
- Finding: C-ANIM promises "action/montage requests", and ANM.TOOL.asset-editor authors montages. No runtime capability names or owns montages: gameplay-driven one-shot clips, slots layered into graphs, sections and jumps, blend in/out, root-motion policy inside a montage, or net-predicted and replicated montage state. Ability activation, hit windows (SYS.hit-detection frame data) and motion warping all depend on it. An authoring tool exists with no runtime owner.
- Evidence: UE AnimMontage and slots, Unity Animator override and playable-graph triggers, Frostbite/ACL-class runtime "action" layers. GAS AbilityTask_PlayMontage is the standard consumer.
- Proposed change: add ANM.GRAPH.actions (owner animation-graphs; contributors animation-runtime, prediction-rollback, character-movement, gameplay-systems-toolkit). It covers action/montage playback, slots, sections, notify-window ownership and replication participation. Reference it from ANM.TOOL.asset-editor.

### K-GAMEPLAY-6 · major · scale-down
- Target: facial-animation profiles [lite3d, std3d]; ANM.FACE.lipsync; ANM.RT.2d; narrative-dialogue; minimal and min2d configurations
- Finding: FACE.lipsync (per-locale) lives only in facial-animation, which is tagged lite3d/std3d. The minimal profile ("narrative-centric") and min2d have VO, C-DIALOGUE and per-locale VO packs but no audio-driven mouth or expression driving for 2D portraits and sprites. There are also no dialogue staging or portrait-layer capabilities (speaker portraits, expression layers, text reveal synced to VO). Visual novels, 2D RPGs and Live2D-style games would rebuild this per game, and per-locale retiming is unsolved for them.
- Evidence: Ren'Py, Live2D Cubism SDK lip-sync parameters (LipSync via audio RMS), Spine mouth-shape slots. This is standard in the mobile and indie VN market that the minimal profile targets.
- Proposed change: add ANM.FACE.lipsync-2d (owner facial-animation with profile add for min2d and minimal, or owner animation-runtime; contributors audio-content-runtime, narrative-dialogue). Add GAM.NARR.staging-2d (portrait/expression layers and text reveal timing). Widen the facial-animation profiles or split the 2D slice.

### K-GAMEPLAY-7 · minor · omission
- Target: GAM.FW.rules; GAM.AI.search; NET.ARCH.async; minimal profile; character-movement
- Finding: the minimal profile targets card and narrative games. Async and turn-based play is a named add-on, and AI.search needs "clonable rule state". No capability defines a turn/phase/command-log substrate. Missing pieces are ordered commands, undo and history, deterministic rules-state cloning, and command-log replay shared by the AI, the async validator and the save. No grid or tile discrete-movement mode exists either (MOVE.platformer is the only 2D mode). NET.ARCH.async-validation re-simulates "submitted async results" against nothing owned.
- Evidence: 4X, tactics, roguelike, card (Slay the Spire, Hearthstone) and mobile async titles all sit on a command/turn queue. Only game team code provides it today, so the AI, validator and replay each invent it.
- Proposed change: add GAM.FW.turns (gameplay-architect; contributors determinism-replay, ai-behavior-perception, persistence-save, online-services-liveops) for the turn/phase/command log with a clonable state API. Add GAM.MOVE.grid (character-movement).

### K-GAMEPLAY-8 · major · omission
- Target: GAM.SAVE.model; GAM.SAVE.platform; GAM.SAVE.migration; XC.EXT; ugc configurations
- Finding: the persistence rows cover model, migration, atomicity, platform, cloud and integrity. Not covered: (a) preserving or tolerating unknown content when a mod or DLC that wrote data is absent or removed; (b) a save-slot catalogue with locale-independent metadata (playtime, thumbnail, version) for load UIs and cross-platform portability; (c) binding save ownership to the platform user, guests and split-screen locals, which is only a contributor line on PLAT.SVC.user-model. The ugc configurations (aaa, indie-2d-online-moddable) claim mods with no save-compat rule.
- Evidence: Skyrim and Fallout 4 script-baked saves (orphaned mod data corrupts saves), Minecraft and Factorio unknown-block and mod-mismatch handling, Bethesda Creation Club problems. Console cert (TRC) requires per-user save handling.
- Proposed change: add GAM.SAVE.unknown-content (unknown-record preservation and quarantine, mod/DLC dependency manifest in each save; contributors modding-ugc, serialization-schema) and GAM.SAVE.slots (metadata and thumbnails, per-user ownership, portability; contributors platform-services, ui-architect). Add both to QA.FUNC.compat-corpus scope.

### K-GAMEPLAY-9 · minor · omission
- Target: gameplay-systems-toolkit; GAM.SYS.volumes; GAM.AI.smart-objects; INP.ACT.glyphs; UI.FW.world-ui
- Finding: there is no interaction and target-selection system: interactable discovery and focus (look-at or proximity), hold and long-press interact, contextual prompts with the active device glyph and localized text, soft target and lock-on selection, and interaction arbitration among multiple candidates and local players. Aim-assist, volumes, markers and AI smart objects exist, but the player-facing counterpart of smart objects (input, UI prompt, animation and motion-warp handshake) is unowned. Each game rebuilds it across input, UI and abilities.
- Evidence: UE Lyra Interaction system and Game Feature plugins, Unity Interaction Toolkit (XR), Naughty Dog-style contextual interaction. Lock-on is core to action-RPGs.
- Proposed change: add GAM.SYS.interaction (gameplay-systems-toolkit; contributors input-system, ui-architect, animation-runtime, gameplay-camera). It covers candidate scoring, prompt model and lock-on target set, and is server-validated for online configurations.

### K-GAMEPLAY-10 · minor · omission
- Target: AUD.ARCH.devices; AUD.ARCH.listeners; PLAT.PAL.system-events; INP.DEV.haptics
- Finding: AUD.ARCH.devices is a single line. Not named: endpoint change and hot-swap (headset unplug, Bluetooth, HDMI) with sample-rate and channel-layout renegotiation; multi-endpoint output (main mix plus a per-local-player controller speaker or headset, used for split-screen and couch co-op); and OS interruption and focus policy (calls, minimize, console suspend, mute-in-background). PLAT.PAL.system-events lists audio endpoints as an event source, but no audio owner consumes the events. Its contributors do not include platform-architect.
- Evidence: PS5 DualSense speaker and headset routing; Xbox per-user audio endpoints and GameInput; iOS AVAudioSession interruptions, mandatory for cert. Common source of stuck-silent audio bugs.
- Proposed change: add AUD.ARCH.routing (audio-architect; contributors platform-architect, platform-console, input-devices-haptics, gameplay-architect) and list it as a consumer of PLAT.PAL.system-events.

### K-GAMEPLAY-11 · minor · omission
- Target: UI.TXT.ime; UI.TXT.bidi; UI.LOC.cldr
- Finding: text input is a single row ("Text input & IME integration"). The editing model is unowned: caret, selection, extended grapheme clusters (UAX #29, with emoji ZWJ and Indic conjuncts), bidi caret movement, password and character-limit fields. TXT.bidi lists UAX #9 and #14 only. UI.LOC.cldr is named "formatting" while collation, case folding, normalization and search-ignoring accents (sorting item lists, friends and names) are unassigned.
- Evidence: Slack and Discord-class chat fields, Unicode UAX #29 and #10 (collation). Truncating by code unit or byte breaks emoji and Hindi text.
- Proposed change: add UI.TXT.editing (owner text-fonts; contributors ui-architect, platform-architect, accessibility), UI.TXT.segmentation (UAX #29) and UI.LOC.collation (localization-i18n).

### K-GAMEPLAY-12 · minor · omission
- Target: legacy-patterns.json (L72 stance_capabilities; new patterns); navigation-pathfinding; text-fonts
- Finding: the legacy catalogue has no entries for four recurring stances in these domains.
  - ASCII, bitmap-font or code-unit text with no shaping, bidi or grapheme handling.
  - Sentence assembly by string concatenation. L72's stance names "plural/gender rules", but its stance_capabilities lists only UI.LOC.strings, not UI.LOC.messageformat or UI.LOC.terms.
  - Synchronous per-agent path requests and main-thread navmesh rebuilds. C-NAV promises batching, but nothing flags the legacy form.
  - Designer tunables as code constants requiring a rebuild.
- Evidence: the concatenation and code-unit failures are the classic localization failures (Unicode CLDR and ICU guidance). Detour and recast and Mass AI use batched, budgeted queries. Hard-coded tunables are the antithesis of GAM.DATA.tuning.
- Proposed change: add L75 (text without shaping or grapheme awareness; UI.TXT.shaping, UI.TXT.bidi), L76 (sentence concatenation; UI.LOC.messageformat, UI.LOC.terms), L77 (sync per-request pathfinding and rebuild; GAM.AI.pathfinding, GAM.AI.navmesh) and L78 (hard-coded tunables; GAM.DATA.tuning). Fix L72's stance_capabilities.

### K-GAMEPLAY-13 · minor · wrong-boundary
- Target: gameplay-systems-toolkit (purpose); GAM.DATA.tags; gameplay-data (purpose); UI.FW.maps; accessibility (purpose)
- Finding: purpose text and ownership diverge, so generated SKILL.md files would conflict.
  - gameplay-systems-toolkit's purpose lists "gameplay tags", but GAM.DATA.tags is owned by gameplay-data (toolkit is only a contributor). gameplay-data's purpose omits tags.
  - The toolkit's purpose omits most owned rows: hit detection, projectiles, building, aim assist, volumes, impacts and markers.
  - UI.FW.maps needs a cook step and a top-down capture, but its contributors (world-architect, gameplay-systems-toolkit) omit asset-cook-processors and render-architect.
- Evidence: skills.json purpose strings versus capabilities.json owners and contributors.
- Proposed change: move "gameplay tags" from the toolkit purpose to gameplay-data (add the tag registry to its purpose) and rewrite the toolkit purpose to cover its owned areas. Add asset-cook-processors and render-architect as contributors to UI.FW.maps. If the toolkit becomes too broad, split combat systems (hit-detection, projectiles, aim-assist) from world systems (volumes, markers, building, impacts).

### K-GAMEPLAY-14 · minor · missing-contract
- Target: UI.A11Y.assists; GAM.DATA.tuning; GAM.SYS.aim-assist; XC.SEC.score-integrity
- Finding: A11Y.assists ("assist & difficulty hooks") and DATA.tuning ("difficulty variants") share territory with no mutual contributor entry. Nothing defines how per-player assists (extended timers, auto-aim, skip-QTE, invulnerability) are scoped in multiplayer: server-authoritative versus local, allowed in competitive queues, and flagged on leaderboards or achievements. Assists that change simulation must be replicated and validated.
- Evidence: The Last of Us Part II and Celeste assist modes; competitive modes disable some assists. XAG guideline 106 (difficulty) and 117 (co-op) apply.
- Proposed change: add gameplay-data as contributor of UI.A11Y.assists and accessibility as contributor of GAM.DATA.tuning. Extend UI.A11Y.assists with an assist-class attribute (cosmetic, input-only, simulation-affecting) and a rule that simulation-affecting assists are replicated and recorded, with a score-integrity flag consumed by XC.SEC.score-integrity.
