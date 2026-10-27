# K-GAMEPLAY · Game Systems & Content Critic · Round 1

Scope: animation, audio, AI, gameplay framework, scripting, input actions, UI, text, localization, accessibility, cinematics, camera, persistence, and the authoring paths game teams need. Findings are based on data/*.json, 00-design-principles.md and 06-gap-analysis.md. All configuration memberships quoted below were computed with the `in_configuration` rule in `scripts/model.py`.

### K-GAMEPLAY-1 · blocker · omission
- Target: AUD.CONTENT.dialogue (audio-content-runtime), UI.A11Y.subtitles (accessibility), ANM.FACE.lipsync (facial-animation), UI.LOC.strings (localization-i18n), GAM.AI.llm (ai-behavior-perception), cinematics-sequencer; 06-gap-analysis §"Game-specific systems"
- Finding: No skill owns the dialogue line model: line ID, speaker, text per locale, VO asset per locale, subtitle timing, lip-sync data, conditions and branching. It also has no contract. 06-gap-analysis moves "dialogue trees, quests" to game code, but at least six engine skills already consume or produce dialogue lines:
  - audio-content-runtime (VO playback)
  - accessibility (subtitles and speaker identification)
  - facial-animation (per-line lip sync)
  - localization-i18n (string and VO gathering)
  - cinematics-sequencer (lines on the timeline)
  - ai-behavior-perception (barks and LLM lines)

  Each of these agents will define its own line record, which is territory overlap with no arbiter. Narrative state (facts and flags) also needs to be saved (C-SAVE) and replicated (C-NET), and neither contract can express it without an owner.
- Evidence: Production engines treat the line and VO model as engine data and leave quest content to the game:
  - UE Dialogue Wave and Dialogue Voice assets, used by the subtitle and localization gather.
  - Source 2 / Left 4 Dead response-rules system (Ruskin, GDC 2012, "AI-driven Dynamic Dialog").
  - REDengine quest and dialogue editors, Anvil and Snowdrop dialogue tooling.
  - Middleware integrations with Ink, Yarn Spinner and articy:draft.

  The VO pipeline also needs one line ID shared by recording scripts, localization vendors and the audio middleware. Examples are Wwise External Sources and Dialogue Events, and FMOD programmer sounds keyed by line.
- Proposed change:
  - Add expert skill `narrative-dialogue` under gameplay-architect (profiles: client, server) that provides new contract `C-DIALOGUE` (layer 4: line records, speaker, conditions, playback requests, narrative fact store).
  - Give it these capabilities:
    - GAM.NARR.lines (dialogue line and VO line database)
    - GAM.NARR.branching (branching dialogue runtime, Ink/Yarn-class import)
    - GAM.NARR.facts (narrative fact and flag store with save and replication participation)
    - GAM.NARR.barks (contextual barks and response rules)
    - GAM.NARR.authoring (dialogue editor, screenplay and articy import; contributor graph-editor-framework)
    - GAM.NARR.vo-script (recording scripts, placeholder TTS VO; contributors audio-content-runtime, localization-i18n)
  - Keep quest and objective *content* as game code, but add GAM.FW.objectives (objective/quest state extension point with save and replication hooks) to gameplay-architect.
  - Reword AUD.CONTENT.dialogue to "VO playback & ducking for C-DIALOGUE lines".
  - Make UI.A11Y.subtitles consume C-DIALOGUE.
  - Rewrite 06 §2 to say "quest content is game code; the dialogue line model and narrative state are engine".

### K-GAMEPLAY-2 · major · dependency-error
- Target: input-devices-haptics, input-system, C-INPUT, INP.DEV.haptics, AUD.CONTENT.haptics, GAM.FW.local-players
- Finding: The input layering is inverted, and the haptics output path has no contract.
  - `input-devices-haptics` (the device layer) provides no contract and consumes `C-INPUT` (the action layer above it).
  - `input-system` consumes only C-PAL, C-FRAME and C-A11Y, so it has no interface through which to read devices.
  - Haptics output has no contract. Gameplay rumble, audio-to-haptics (AUD.CONTENT.haptics in audio-content-runtime) and adaptive-trigger effects cannot reach INP.DEV.haptics except by calling the internals of another skill, which 00 §3 forbids.
  - Haptic effects as authored assets (DualSense trigger and HD-haptic clips) have no owner.
- Evidence: Every modern input stack separates the device layer from the action layer, with the action layer consuming the device layer. Examples are the GameInput → action layer path, SDL3 → Unity Input System, and UE Enhanced Input over IInputDevice. Haptics are an output channel with their own scheduling and latency needs; PS5 trigger effects are authored assets with platform certification requirements.
- Proposed change:
  - Add contract `C-DEVICE` (layer 2: device enumeration, raw state, timestamps, user pairing, haptic/trigger/LED output) owned by input-devices-haptics.
  - Make input-system consume `C-DEVICE`, and remove `C-INPUT` from input-devices-haptics.
  - Add INP.DEV.haptic-assets "Authored haptic and trigger-effect assets & playback" to input-devices-haptics, with contributor audio-content-runtime.
  - Make audio-content-runtime and gameplay-systems-toolkit consume `C-DEVICE?`.

### K-GAMEPLAY-3 · major · wrong-boundary
- Target: input-system (profile `client`), C-INPUT, dedicated-server configuration, prediction-rollback, gameplay-architect
- Finding: `dedicated-server` does not include input-system, so C-INPUT (action values, timestamps, device and user association) does not exist on the server. Server-authoritative prediction, lockstep, rollback and INP.ACT.recording all need the action *schema* and command-frame serialization on the server, which receives, validates and re-simulates client inputs. Today prediction-rollback and gameplay-architect only consume `C-INPUT?`, so the server builds and silently lacks the type its netcode is built around. Each netcode agent will then invent its own input-command format.
- Evidence: Authoritative-server and rollback models transmit input commands rather than state for owned pawns:
  - Overwatch (Ford, GDC 2017)
  - GGPO
  - Rocket League (Cone, GDC 2018)
  - UE Network Prediction and CharacterMovement ServerMove
  - Photon Quantum input structs

  The server must deserialize and apply the same action type.
- Proposed change:
  - Split C-INPUT into two contracts:
    - `C-INPUT` (layer 3, profiles all): action definitions, action values, input-command frames and serialization.
    - Device-to-action mapping, contexts and rebinding, which stay client-only.
  - Tag input-system `all`, and make its client-only capabilities (INP.ACT.remapping, INP.ACT.glyphs, INP.ACT.ui-routing) degrade out on `server`.
  - Change prediction-rollback's `C-INPUT?` to a required `C-INPUT`.

### K-GAMEPLAY-4 · major · missing-contract
- Target: GAM.SYS.camera (gameplay-systems-toolkit), ANM.CINE.cameras (cinematics-sequencer), GAM.SYS.photo, RND.POST.camera (post-color-hdr), PLAT.XR.* (xr-runtime), RND.ARCH.multiview, WLD.PART.sources, C-AUDIO listener, C-RSCENE "views"
- Finding: Six skills own parts of "the camera", and no contract arbitrates which camera drives each view. Nothing defines:
  - blending gameplay camera ↔ cinematic camera ↔ photo mode ↔ XR head pose;
  - per-local-player views for split-screen;
  - camera shake and FOV kick, and accessibility reduction of them;
  - the camera-relative origin for large-world coordinates;
  - the streaming source and audio listener derived from the active view.

  `gameplay-systems-toolkit` provides **no** contract at all, so cinematics-sequencer (which does not consume C-GAME) and render-architect cannot consume the camera system except by reaching into it. The audio side has the same gap: there is no capability for multiple listeners or split-screen audio, although RND.ARCH.multiview and GAM.FW.local-players exist.
- Evidence: UE's PlayerCameraManager, view-target blending and Sequencer camera-cut takeover, and Unity Cinemachine's CinemachineBrain priority and blending, are exactly this arbitration layer. Split-screen audio (listener-per-player weighting, as in Wwise multi-listener) is a known certification and usability issue for local co-op.
- Proposed change:
  - Add contract `C-CAMERA` (layer 3: view descriptors per local player, including transform, projection and physical-camera parameters; priority and blend stack; shake channel; LWC origin) owned by gameplay-systems-toolkit.
  - Add capability GAM.SYS.camera-arbitration.
  - Make these skills consume C-CAMERA: render-architect (views), cinematics-sequencer (provides a camera source), xr-runtime (override), world-architect (streaming source), audio-architect (listeners), accessibility (shake and FOV limits).
  - Add AUD.ARCH.listeners "Multiple listeners & split-screen mixing" to audio-architect.

### K-GAMEPLAY-5 · major · missing-contract
- Target: C-UI (layer 3), ui-architect, gameplay-architect, gameplay-systems-toolkit, GAM.FW.flow, C-SCRIPT (layer 4)
- Finding: The gameplay↔UI connection is absent, and the layering makes it impossible to add later.
  - GAM.FW.flow owns "menus, loading screens", but gameplay-architect does not consume C-UI. No gameplay skill consumes C-UI at all.
  - C-UI is layer 3 and C-GAME and C-SCRIPT are layer 4, so UI cannot bind to gameplay state and UI logic cannot be scripted. The workflow every UI team uses (a view-model exposed by gameplay, bound in a designer tool, with logic in script or visual script) has no owner and no legal edge.
  - ui-architect does not consume C-AUDIO?, so UI sound feedback has no path either.
  - Loading screens need to render while loading runs on other threads, and nobody owns that.
- Evidence:
  - UE UMG with the MVVM plugin (view-models owned by game code).
  - Unity UI Toolkit runtime data binding.
  - Coherent Gameface/Prysm data-binding models.
  - Scaleform's ActionScript/Lua logic layer.

  In all of these, gameplay publishes view-models and UI binds to them via reflection. Reflection is the one path the layering here allows, but no one owns the gameplay side of it.
- Proposed change:
  - Add GAM.FW.ui-binding "Gameplay view-model exposure for HUD & menus (reflected, change-notifying)" to gameplay-architect, and make gameplay-architect consume `C-UI?`.
  - Add UI.FW.logic "UI logic hosting (script / visual-script callbacks via reflection-invoked handlers)" to ui-architect, which the scripting runtime registers through C-REFL. This avoids an upward C-SCRIPT edge.
  - Move "loading screens" out of GAM.FW.flow into a new capability UI.FW.loading-screens "Non-blocking loading/boot screens & movie playback" owned by ui-architect, with contributor resource-streaming-architect.
  - Add `C-AUDIO?` to ui-architect's consumes.

### K-GAMEPLAY-6 · major · missing-contract
- Target: C-A11Y (layer P, not universal), accessibility, ui-architect, text-fonts, audio-content-runtime, cinematics-sequencer, gameplay-systems-toolkit, post-color-hdr, vfx-particles, UI.A11Y.screen-reader
- Finding: Accessibility is not built in; it is bolted on.
  - C-A11Y is a process contract, but only input-system (required) and certification-compliance (optional) consume it. The player-facing owners do not: ui-architect, text-fonts, audio-content-runtime, cinematics-sequencer, gameplay-architect and toolkit, post-color-hdr, vfx-particles, render-2d-vector.
  - accessibility is `runtime: true` and owns runtime features (subtitles, screen-reader and TTS hooks), yet it provides no *runtime* contract. No skill has an API to submit a caption, announce text, or query a11y settings.
  - The semantic accessibility tree for game UI (widget roles, names and states exposed to screen readers or narrated menus) is not a capability anywhere.
  - Speech-to-text and text-to-speech for text and voice chat, which CVAA requires for communication features, have no owner. There is not even a text-chat runtime capability.
- Evidence:
  - CVAA §716 (communication accessibility in games, in force since 2019).
  - EAA 2025.
  - Xbox Accessibility Guidelines XAG 104 and 106 (text-to-speech and speech-to-text for chat), XAG 101 (text display).
  - AccessKit and UIA/NSAccessibility-style trees, as used by UE Slate's accessibility layer.
  - The Last of Us Part II's 60+ options needed hooks in camera, audio, UI and gameplay, not in one module.
- Proposed change:
  - Mark C-A11Y `universal: "client-runtime"`, or add it to the consumes list of every player-facing client skill named above.
  - Add runtime contract `C-A11Y-RT` (layer 3: caption and subtitle submission, screen-reader announcements, a11y setting queries and change events) owned by accessibility.
  - Add UI.FW.a11y-tree "Semantic accessibility tree for game UI" to ui-architect, with contributor accessibility.
  - Add UI.A11Y.chat "Text/voice chat TTS & STT transcription", plus a text-chat runtime capability PLAT.SVC.text-chat owned by platform-online-services (moderation is already there).

### K-GAMEPLAY-7 · major · omission
- Target: character-vehicle-physics non-responsibility "Movement gameplay logic → gameplay-systems-toolkit"; motion-synthesis non-responsibility "Locomotion gameplay → gameplay-systems-toolkit"; PHY.CTRL.character; NET.PRED.prediction; ANM.ARCH.sync
- Finding: Two skills point "movement/locomotion gameplay" at gameplay-systems-toolkit, but the toolkit owns no movement capability. Character movement is therefore unowned. That covers:
  - movement modes (walk, sprint, crouch, swim, climb, mantle, fly, glide);
  - the networked movement component with prediction and correction;
  - root-motion vs capsule authority;
  - vehicle-possession and mount transitions;
  - 2D platformer movement (coyote time, input buffering).

  This is the most-touched gameplay system in most action games, and it sits at the four-way junction of animation, physics, network and input.
- Evidence: UE CharacterMovementComponent and the newer Mover plugin, the Unity Character Controller plus netcode samples, Overwatch's movement prediction (GDC 2017) and Valve's Source multiplayer networking docs all treat movement as its own system. PHY.CTRL.character is only the collision-constrained controller primitive.
- Proposed change:
  - Add GAM.SYS.movement "Character movement modes & networked movement (predicted, reconciled, root-motion aware)" owned by gameplay-systems-toolkit, with contributors character-vehicle-physics, prediction-rollback and motion-synthesis.
  - Make gameplay-systems-toolkit consume `C-PHYS` and `C-ANIM`.
  - Fix both non-responsibility pointers so they reference the new capability.

### K-GAMEPLAY-8 · major · missing-contract
- Target: C-ANIM ("Animation pose output"), prediction-rollback (NET.PRED.lagcomp), animation-architect, replication, ANM.ARCH.sync
- Finding: Three gaps in the animation contract:
  - **Server rewind cannot see bones.** Lag compensation (NET.PRED.lagcomp) must rewind hitboxes that are driven by bone poses, but prediction-rollback does not consume C-ANIM.
  - **No networking path.** animation-architect does not consume `C-NET?`. So none of the following has a declared owner or edge: replicating animation state and montages, predicting animation-driven actions such as ability montages and root-motion moves, server-side pose evaluation at hit-validation LOD, and deterministic animation for rollback.
  - **C-ANIM is output-only.** It has no input side (graph parameters, slot or montage play requests, per-entity animation instances). Gameplay, AI, abilities, cinematics and motion-synthesis will each invent a way to drive animation.
- Evidence:
  - Server-rewind hit validation on bone-driven hitboxes (Valve lag compensation; Overwatch GDC 2017).
  - UE's replicated montages and root-motion sources in CharacterMovement.
  - Rollback fighting games rolling animation state back with simulation (GGPO integrations, Mortal Kombat/Injustice netcode GDC 2018).
- Proposed change:
  - Extend the C-ANIM summary to "pose output **and** control input: parameters, action/montage requests, instance lifetime, pose history for rewind".
  - Add ANM.ARCH.net "Animation replication, prediction & server evaluation policy" to animation-architect, with contributors replication and prediction-rollback.
  - Add `C-NET?` to animation-architect's consumes and `C-ANIM?` to prediction-rollback's consumes.
  - Add ANM.RT.pose-history "Pose history buffer for rewind" to animation-runtime.

### K-GAMEPLAY-9 · major · omission
- Target: ANM.* (no authoring capabilities), ANM.IK.physical, GAM.AI.*, AUD.CONTENT.authoring, crosscutting "tooling" obligation
- Finding: Authoring paths for animators, technical animators, AI designers and sound designers are not capabilities. Environment features own their tool logic (WLD.ENV.terrain-tools), and UI owns UI.FW.authoring, but these have no owner:
  - an animation editor or preview (skeleton, sockets, notify and curve editing, montage and slot editing);
  - an animation-graph and blend-space editor (graph-editor-framework explicitly disclaims each domain's semantics);
  - a retarget-rig editor;
  - a physics-asset / ragdoll-body and constraint editor (between ik-procedural-animation and rigid-body-dynamics, owned by neither);
  - a pose-asset and facial-rig tool;
  - a behavior-tree, state-tree or EQS editor and debugger (ai-behavior-perception does not even consume `C-GRAPH?` or `C-EDCMD?`);
  - a sound-designer tool (event, container, randomization, snapshot and live mixing) for the "own audio" branch of the AUD.ARCH.middleware decision. AUD.CONTENT.authoring covers only *integration* with an external tool.

  The cross-cutting line "declare authoring path" makes this an obligation but gives it no owner, so the editor agents and domain agents will both build it, or neither will.
- Evidence: UE Persona, the IK Retargeter and the Physics Asset Editor; Unity Animator and Animation Rigging; Frostbite/ANT and Decima animation tooling; UE Behavior Tree and StateTree editors with the Gameplay Debugger; UE MetaSounds and Wwise authoring as the bar for sound design. The brief requires "production tooling as thorough as runtime".
- Proposed change: Apply the end-to-end ownership pattern from 00 §4. Each capability goes to the named owner, consuming `C-EDCMD?`/`C-GRAPH?`:
  - ANM.TOOLS.asset-editor and ANM.TOOLS.retarget-editor → animation-runtime
  - ANM.GRAPH.authoring → animation-graphs
  - ANM.IK.physics-asset "Physics asset / ragdoll authoring" → ik-procedural-animation, with contributor rigid-body-dynamics
  - ANM.FACE.tools → facial-animation
  - GAM.AI.authoring and GAM.AI.debug → ai-behavior-perception, with contributor visual-debugging-tools
  - AUD.CONTENT.designer-tool "In-engine sound design & live mixing tool (own-audio path)" → audio-content-runtime

### K-GAMEPLAY-10 · major · omission
- Target: GAM.* (none), CORE.MATH.curves, PLAT.SVC.remote-config, reflection-metadata
- Finding: Data-driven gameplay has no owner. Nobody owns:
  - typed data tables and row references;
  - curve tables and designer-authored curve assets (CORE.MATH.curves is interpolation math, not assets);
  - gameplay config and tuning assets with inheritance and overrides;
  - spreadsheet round-trip (CSV, Google Sheets, Excel import and export);
  - balancing tooling (formula sheets, simulated combat and economy runs);
  - live tuning of these assets through remote config.

  This is what designers use most. Without an owner, abilities, AI, loot and economy code will each grow a private data format.
- Evidence: UE DataTable, CurveTable and DataAsset; Unity ScriptableObjects; Frostbite's schema-driven data; CastleDB and Google Sheets pipelines used in many live games; Riot and Blizzard GDC talks on data-driven tuning and hotfixable balance data.
- Proposed change: Add GAM.DATA.tables, GAM.DATA.curves, GAM.DATA.tuning (inheritance/overrides, per-platform and difficulty variants), GAM.DATA.spreadsheets and GAM.DATA.balance-sim to gameplay-systems-toolkit, with contributors serialization-schema and platform-online-services (live overrides). Alternatively, create a skill `gameplay-data` if the count justifies it.

### K-GAMEPLAY-11 · major · omission
- Target: ED.WORLD.*, GAM.FW.*, scripting-runtime
- Finding: Level designers have no authoring path. None of the following is a capability:
  - greybox/blockout geometry tools (in-editor modeling, CSG-free);
  - trigger volumes and gameplay volumes;
  - gameplay markers (spawn points, cover points, patrol paths, POIs);
  - level-bound scripting and event wiring;
  - designer-placed encounters.

  ED.WORLD covers only gizmos, placement and splines.
- Evidence: UE Modeling Mode and Cube Grid, Unity ProBuilder, Hammer 2 (Source 2) mesh tools; trigger/volume actors and level blueprints in UE, level scripting in id Tech and Frostbite; the "blockout" stage in every level-design pipeline (e.g. GDC "Level Design Workshop" series).
- Proposed change:
  - Add ED.WORLD.blockout "Greybox/blockout modeling tools" to world-editor-viewport.
  - Add GAM.SYS.volumes "Trigger & gameplay volumes, gameplay markers" to gameplay-systems-toolkit.
  - Add GAM.SCR.level-scripting "Level-bound script/event wiring" to scripting-runtime, with contributor world-data-model.

### K-GAMEPLAY-12 · major · scale-down
- Target: indie-2d configuration, RND.2D.tilemaps, ANM.RT.2d, physics-2d, asset-cook-processors
- Finding: The 2D configuration gets runtime pieces but no authoring or pipeline, and asset-cook-processors owns only textures and meshes. Nobody owns:
  - a tilemap editor with auto-tiling and rule tiles;
  - sprite slicing and editing, sprite-sheet and atlas packing in the cook;
  - 2D skeletal-animation import (Spine/DragonBones-class) and 2D IK constraints (ik-procedural-animation is std3d-only);
  - 2D collision-shape generation from sprites;
  - pixel-perfect camera and parallax;
  - 2D lights and shadows.

  A small 2D team would have to build these inside a 3D-oriented editor with no owner.
- Evidence: Unity 2D Tilemap, Sprite Editor, 2D Animation and 2D Lights packages; Godot TileMap and TileSet editors; Spine runtimes with IK and mesh constraints; Tiled/LDtk import. The brief requires scaling down efficiently with first-class modularity.
- Proposed change:
  - Add RND.2D.tile-tools and RND.2D.lights to render-2d-vector.
  - Add CNT.COOK.atlas "Sprite atlas packing" to asset-cook-processors (this also fixes its "microscopic" warning).
  - Add ANM.RT.2d-import "2D skeletal import (Spine-class) incl. IK/mesh constraints" to animation-runtime.
  - Add PHY.2D.shape-gen to physics-2d.
  - Add a 2D camera mode to the proposed C-CAMERA (see K-GAMEPLAY-4).
  - Add a critic check "indie-2d has an authoring path for every 2D runtime capability".

### K-GAMEPLAY-13 · major · scale-down
- Target: profile tags of ik-procedural-animation (`std3d`), facial-animation (`aaa`), spatial-audio-acoustics (`mobile3d,std3d,xr`), crowd-simulation (`openworld`), motion-synthesis (`aaa`)
- Finding: Wrong profile tags remove established, cheap features from configurations that need them:
  - **mobile-3d** has no IK, foot placement, look-at or ragdoll (ANM.IK.* including ANM.IK.physical).
  - **standard-3d, open-world and online-3d** have no lip sync or facial rigs at all, so every non-AAA 3D narrative game ships without phoneme lip sync.
  - **indie-2d** has no *panning and distance attenuation* (AUD.SPAT.panning), which every 2D game uses.
  - **Every configuration except open-world and AAA** (including dedicated-server for server-side NPCs) has no local avoidance (GAM.AI.avoidance, ORCA/RVO) and no flow fields. That leaves out RTS, colony-sim and "large-scale simulation", which the brief names.
  - **Motion matching** (E maturity) is locked to AAA.
- Evidence:
  - Foot IK and ragdolls are standard in mobile 3D titles (Genshin Impact, PUBG Mobile).
  - Phoneme and viseme lip sync (Oculus Lipsync, Annosoft-class) is cheap and established.
  - Detour crowd avoidance ships as part of Recast/Detour's basic toolkit.
  - Motion matching ships as a default UE 5.4+ feature, and was used in For Honor (Clavet, GDC 2016).
- Proposed change:
  - ik-procedural-animation → `mobile3d,std3d,server` (server for authoritative ragdoll and hit reactions), with 2D IK per K-GAMEPLAY-12.
  - facial-animation → `mobile3d,std3d`, keeping ANM.FACE.lipsync's ML variant behind `C-ML?`.
  - Move AUD.SPAT.panning to audio-dsp-mixing (a base capability) or tag spatial-audio-acoustics `client`.
  - Move GAM.AI.avoidance to navigation-pathfinding, or tag crowd-simulation `mobile3d,std3d,server`, keeping GAM.AI.mass for openworld/aaa.
  - motion-synthesis → `std3d`.
  - Add a `sim` add-on profile (large-scale simulation) and a configuration that uses it.

### K-GAMEPLAY-14 · major · scale-down
- Target: C-GAME `requires: [C-ECS, C-PHYS, C-ANIM, C-WORLD]`, gameplay-architect consumes (`C-PHYS`, `C-ANIM`, `C-WORLD`, `C-SAVE` required), C-NAV requires C-PHYS, ai-behavior-perception consumes C-PHYS
- Finding: The gameplay framework contract hard-requires physics, skeletal animation and world partition/streaming cells. As a result, a visual novel, card game, turn-based puzzle game or UI-only game must carry the physics lead, the animation lead and world-architect. The closure proof passes only because those leads are tagged `all`. For the same reason, grid pathfinding and AI decisions in a 2D tactics game cannot exist without a physics world. 00 §5 claims scale-down is proven, but the proof here is circular: the tags were widened so that closure holds.
- Evidence: Genre-agnostic frameworks do not require physics or animation. Godot's SceneTree game loop and Unity's core player loop both run without them, and the brief says "not every configuration needs every subsystem".
- Proposed change:
  - Change C-GAME requires to `[C-ECS]`, and gameplay-architect consumes to `C-PHYS?`, `C-ANIM?`, `C-WORLD?`, `C-SAVE?`.
  - Change C-NAV requires to `[C-SPATIAL]` and its consumption of physics to `C-PHYS?` (a grid or navmesh can be baked from level geometry through C-COOK).
  - Change ai-behavior-perception's physics dependency to `C-PHYS?`.
  - Add a configuration `minimal-2d` (e.g. visual novel or card game) to check.py so this stays proven.

### K-GAMEPLAY-15 · major · maturity-error
- Target: GAM.AI.learned (X), GAM.AI.llm (X), ai-behavior-perception consumes, 06-gap-analysis A12
- Finding: 06 A12 says LLM NPCs are allowed "only behind an optional contract with moderation (platform-online-services), a budget, and an offline fallback". The data implements none of this.
  - ai-behavior-perception (profile `all`, an established skill) owns both experimental capabilities directly and consumes neither `C-ML?` nor `C-SVC?`.
  - There is no extension point, so 00 §7's rule that experimental work is reached only via an optional contract is violated and not machine-checked.
  - These concerns have no owner: generated-text localization and TTS voicing, rating and certification exposure (with a contributor from certification-compliance), player-data privacy, and persistence of conversational memory (C-SAVE).
  - The skill's expertise list has no ML competence.
- Evidence: Public demos (NVIDIA ACE, Inworld integrations, Ubisoft NEO NPC, 2024) all use cloud or GPU inference with latency, cost and safety constraints. Age ratings (ESRB/PEGI) and platform policies treat unmoderated generated content as UGC-class risk.
- Proposed change:
  - Add optional contract `C-AIAGENT` (layer 4: decision-provider extension point with budget, timeout and fallback) owned by ai-behavior-perception, and add `C-ML?` and `C-SVC?` to its consumes.
  - Move GAM.AI.llm and GAM.AI.learned behind that extension, and add GAM.AI.llm-guardrails with contributors security-engineering, certification-compliance and localization-i18n.
  - Add a check.py rule that an X/S capability owned by a skill tagged `all` or `client` requires a `?` contract.

### K-GAMEPLAY-16 · major · missing-contract
- Target: cinematics-sequencer (consumes C-ANIM, C-AUDIO, C-RSCENE, C-RES, C-EDCMD?; profile `client`), ANM.CINE.*
- Finding: The sequencer has no edge to any of the systems it must take over or drive during a cutscene:
  - gameplay (`C-GAME`: player possession, input blocking, skippable cutscenes, gameplay events on the timeline, blending in and out of gameplay);
  - UI (`C-UI`: letterboxing, subtitles, fades);
  - localization (`C-LOC`: per-language VO length changes timing);
  - networking (`C-NET`: synchronized in-game sequences in multiplayer);
  - camera (C-CAMERA from K-GAMEPLAY-4).

  Its `client` tag also excludes the sequencer from dedicated servers. Server-authoritative scripted sequences (boss intros, moving set pieces, timed world events) then have no timeline. Separately, the sequencer is the engine's general-purpose timeline, used also for UI and gameplay animation, yet it is filed only as "cinematics".
- Evidence: UE Level Sequence replication and in-game sequence actors; Destiny and MMO scripted world events running on servers; localized cutscene timing in Witcher 3/Cyberpunk (dialogue-driven cinematics that REDengine generates per language).
- Proposed change:
  - Add `C-GAME?`, `C-UI?`, `C-LOC?`, `C-NET?` and `C-CAMERA` to cinematics-sequencer's consumes.
  - Change its profile to `all`, with rendering and audio tracks degrading out on server.
  - Add ANM.CINE.gameplay-takeover and ANM.CINE.net-sync capabilities.
  - Rename the sequencer capability to "Timeline/sequencer (cinematic, gameplay and UI tracks)".

### K-GAMEPLAY-17 · major · overlap
- Target: INP.DEV.hotplug "Hotplug & device-user pairing" (input-devices-haptics), PLAT.CON.user-model "Console multi-user model & user/device pairing" (platform-console), INP.ACT.local-mp (input-system), GAM.FW.local-players (gameplay-architect)
- Finding: Four capabilities in four skills own overlapping pieces of the player ↔ platform user ↔ device association:
  - Two of them literally both say "user/device pairing".
  - The certification-critical flows split across them: controller disconnect and reconnect prompts, sign-in and user switching, the guest user, and engagement ("press start" assigns the user).

  The domain has no single owner and no contract.
- Evidence: Xbox and PlayStation certification requirements on user/controller pairing and controller-disconnect handling, and the Switch controller-applet requirements, are among the most frequent cert failures. They are handled in one "local player / user" subsystem in production engines (UE ULocalPlayer + IPlatformInputDeviceMapper).
- Proposed change:
  - Make platform-console (via C-PAL/C-SVC) own platform-user identity only.
  - Make input-devices-haptics own device↔platform-user pairing through the new `C-DEVICE` (K-GAMEPLAY-2).
  - Make input-system own local-player↔device assignment (INP.ACT.local-mp).
  - Make gameplay-architect own only player objects built on top.
  - Reword each capability to say which of these four it owns.
  - Add UI/flow capability GAM.FW.engagement "Engagement, sign-in change & controller-disconnect flows" to gameplay-architect, with contributor certification-compliance.

### K-GAMEPLAY-18 · major · omission
- Target: ui-architect, UI.FW.layout, UI.FW.world-ui, INP.ACT.glyphs, xr-runtime, localization-i18n, text-fonts, packaging-release-patching
- Finding: Platform and locale presentation requirements for game UI and localization are missing:
  - TV safe zones and title-safe areas, and mobile notch and cutout safe areas. No "safe" capability exists anywhere.
  - The confirm/cancel button swap for Japan.
  - Platform-mandated dialogs (saving indicator, system keyboard / virtual keyboard entry).
  - RTL *layout mirroring*. UI.TXT.bidi covers text only, not widget layout.
  - Text-expansion auto-fit and overflow validation.
  - VR UI interaction (laser pointer, poke and hand-tracking input into focus). xr-runtime and UI.FW.focus do not connect.
  - Per-locale font subsetting and font-pack chunking. CJK fonts are tens of MB.
  - On-demand VO language packs, which need a localization-to-packaging edge that does not exist (localization-i18n does not consume C-PKG or C-VFS).
- Evidence: Console TRCs on safe area and system keyboards; Android and iOS safe-area insets; the Arabic and Hebrew localization of UI layouts (e.g. UE's FlowDirection and Unity UI Toolkit direction); console "install language pack" features in large titles (Call of Duty, Forza) and chunked VO downloads.
- Proposed change:
  - Add UI.FW.safe-area and UI.FW.rtl-mirroring to ui-architect.
  - Add UI.FW.xr-interaction, with contributor xr-runtime.
  - Add UI.FW.platform-dialogs, with contributor certification-compliance.
  - Add INP.ACT.confirm-swap to input-system.
  - Add UI.TXT.font-subsetting, with contributor asset-cook-processors.
  - Add UI.LOC.language-packs, with contributor packaging-release-patching, and give localization-i18n `C-VFS?`.
  - Add UI.LOC.overflow-validation, with contributor content-pipeline-architect.

### K-GAMEPLAY-19 · major · omission
- Target: persistence-save, input-system (INP.ACT.remapping), accessibility, C-CFG, GAM.FW.flow
- Finding: Player settings and options have no owner. Nobody owns the options model and its persistence: graphics, scalability, audio, a11y, remapped bindings, subtitles, language. That includes pre-profile first-boot settings (a11y options must be available before sign-in), per-user versus per-device scope, and the options-menu data that UI binds to. C-CFG is developer configuration and cvars, and C-SAVE is game progress. Remapping, a11y, audio and graphics agents will each persist separately.
- Evidence: XAG 107 (settings persistence and first-boot availability), and CVAA practice of exposing accessibility settings before any gameplay. UE UGameUserSettings and the Lyra settings registry show the need for a single owner.
- Proposed change: Add GAM.SAVE.settings "Player settings/options model, scopes (device/user/cloud) & first-boot availability" to persistence-save, with contributors input-system, accessibility and performance-architect (scalability). Expose it through C-SAVE, and have GAM.FW.ui-binding (K-GAMEPLAY-5) publish it to the options UI.

### K-GAMEPLAY-20 · minor · overlap
- Target: UI.FW.architecture "(… immediate for dev UI)" (ui-architect), ED.UI.imgui "Immediate-mode developer UI" (editor-ui-framework), ED.DEBUG.menus "Debug menus & overlays" (visual-debugging-tools)
- Finding: Three skills claim immediate-mode or developer UI. The profiles make it worse: editor-ui-framework is `client`, while visual-debugging-tools is `all`. Server debug overlays and remote debug menus therefore sit on a UI implementation that does not exist in the server configuration.
- Evidence: 00 §8 already merges 2D draw backends to avoid duplicate renderers. The same reasoning applies here.
- Proposed change: Remove "immediate for dev UI" from UI.FW.architecture. Make ED.UI.imgui the single owner of the immediate-mode toolkit, and make it runtime-capable (`client`, with a remote/web front end for server). visual-debugging-tools consumes it for ED.DEBUG.menus.

### K-GAMEPLAY-21 · minor · obsolete-assumption
- Target: GAM.FW.rules "Game rules, players & possession", gameplay-architect non-responsibility "Game-specific code (the game team) → engine-architect", GAM.SYS.abilities, 00 §6 defaults table
- Finding:
  - "Possession" imports UE's Pawn/Controller/GameMode vocabulary as a capability name, and the defaults table in 00 §6 has no row stopping an inherited actor → pawn → character model in the gameplay framework. The ECS row covers only bulk simulation.
  - The non-responsibility routes game code to engine-architect, which neither owns nor writes game code.
  - No capability validates the framework against real games: there are no reference or sample games per configuration beyond XC.DX.templates.
- Evidence: Data-oriented gameplay frameworks exist (Overwatch ECS, GDC 2017; Unity DOTS/Netcode for Entities; Bevy). UE's own Lyra, GameFeatures and Mover rework shows the pawn/controller model is being unwound.
- Proposed change:
  - Rename to GAM.FW.control "Control binding (input source/AI → controlled entity), data-oriented".
  - Add a 00 §6 row, "gameplay framework is composition of components/systems plus services, not an actor inheritance chain", and add it to ARCH.GOV.anti-legacy's flagged patterns.
  - Change the non-responsibility target to "game team (out of engine scope, consumes C-GAME/C-SCRIPT)".
  - Add GAM.FW.reference-games "Reference game slices per configuration for framework validation", with contributor test-architect.

### K-GAMEPLAY-22 · minor · omission
- Target: navigation-pathfinding, crowd-simulation, ai-behavior-perception
- Finding: Three AI variants that open-world and action games depend on have no capability:
  - vehicle and traffic navigation: road and lane graphs, racing lines, traffic rules (GAM.AI.volumes covers only flying);
  - tactical and cover systems (cover generation, tactical point evaluation);
  - squad and group coordination.
- Evidence: UE ZoneGraph and MassTraffic (City Sample); Forza Drivatar and racing lines; cover systems in Gears/The Division (GDC talks on tactical AI). EQS alone does not generate cover data.
- Proposed change:
  - Add GAM.AI.lanes "Lane/road graphs & vehicle navigation" to navigation-pathfinding, with contributor crowd-simulation for traffic.
  - Add GAM.AI.tactical "Cover/tactical point generation & squad coordination" to ai-behavior-perception.

Counts: 1 blocker, 19 major, 2 minor.
