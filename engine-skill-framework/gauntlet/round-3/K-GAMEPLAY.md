# K-GAMEPLAY — Game Systems and Content Critic, round 3

### K-GAMEPLAY-1 · major · obsolete-assumption
- **Target:** UI.LOC.strings, C-LOC, GAM.NARR.lines, localization-i18n
- **Finding:** UI.LOC.strings is "String tables keyed by English source text". That is the gettext-era msgid model. It contradicts C-LOC ("String IDs") and GAM.NARR.lines ("line database with stable IDs"), so the localization and narrative agents would build two incompatible key schemes.
- **Evidence:** When the source text is the key, every English typo fix or rewrite orphans all translations. Homographs collide: "Close" can be a verb for a door or a menu action, and "Fire" can mean shoot or flames, which forces msgctxt workarounds. VO file naming, lip-sync data and subtitle timing are all keyed per line and cannot follow a mutable key. Modern pipelines key strings by a stable ID (namespace plus key) and store the source text, a source hash for change detection and translator context as attributes. Unreal FText does this with namespace, key and source-string hash; Mozilla Fluent uses message IDs.
- **Proposed change:** Rename UI.LOC.strings to "String tables keyed by stable IDs (namespace + key), carrying source text, source-hash change detection, translator context/comments, max-length and screenshot references". Add a legacy-patterns.json entry, "Source-text-keyed string tables (gettext msgid)", with stance capability UI.LOC.strings and justification_owner localization-i18n.

### K-GAMEPLAY-2 · major · omission
- **Target:** audio-content-runtime, audio-dsp-mixing, AUD.DSP.codecs, CNT.COOK, facial-animation, narrative-dialogue, gameplay-data, ui-architect, text-fonts
- **Finding:** No capability owns cooking audio: per-platform codec encoding (Opus/Vorbis/ADPCM/hardware formats), sample-rate conversion, cook-time loudness normalization, bank or pack building, and streaming chunk/seek-table layout. CNT.COOK covers only textures, meshes and images. Neither audio skill has C-COOK in tool_consumes, and audio-dsp-mixing has no tool_consumes at all. The same gap hits other game-content types. Batch per-locale lip-sync baking (facial-animation), compiling dialogue scripts or Ink/Yarn (narrative-dialogue), validating and binarizing data tables (gameplay-data), and UI binding compilation ("compiled/resolved bindings" in UI.FW.architecture, ui-architect) all have no C-COOK path. text-fonts owns UI.TXT.font-subsetting but has an empty tool_consumes.
- **Evidence:** Every shipping engine has an audio cook stage: Unreal's per-platform audio compression settings and Wwise/FMOD SoundBank generation. VO can make up most of a narrative game's content, often tens of thousands of lines times the number of locales. Shipping raw PCM, or encoding at runtime, fails the size and IO budgets on mobile and web first, which is the scale-down case.
- **Proposed change:** Add AUD.TOOL.cook, "Audio cook processors: per-platform codec encoding, SRC, loudness normalization, bank/pack & stream-chunk layout, per-locale VO packs", owned by audio-content-runtime with contributors audio-dsp-mixing and asset-cook-processors. Add C-COOK to tool_consumes of audio-content-runtime, facial-animation (a new ANM.FACE.lipsync-bake capability), narrative-dialogue, gameplay-data, ui-architect and text-fonts.

### K-GAMEPLAY-3 · major · wrong-owner
- **Target:** GAM.SYS.tags, GAM.TOOL.tags-abilities, C-GAMEDATA, C-ABILITY, gameplay-data, gameplay-systems-toolkit
- **Finding:** The C-GAMEDATA summary (owner gameplay-data, layer 3) includes "gameplay tag registry and tag queries". But the capabilities GAM.SYS.tags ("Gameplay tags") and GAM.TOOL.tags-abilities ("Gameplay-tag dictionary") are owned by gameplay-systems-toolkit, which provides C-ABILITY at layer 4 and also lists "tag queries". Two skills claim the tag registry. gameplay-systems-toolkit is also the oracle author of C-GAMEDATA, so it would write the oracle for its own tag territory.
- **Evidence:** Tags are a low-level vocabulary. narrative-dialogue, AI, audio switches, UI, save data and data tables all use them, and several of those skills sit at layer 3 and cannot consume C-ABILITY at layer 4. Unreal's GameplayTags module sits below GameplayAbilities for the same reason.
- **Proposed change:** Move GAM.SYS.tags to gameplay-data and rename it GAM.DATA.tags, "Gameplay tag dictionary, hierarchical tag queries, tag redirects/renames". Split the dictionary editor out of GAM.TOOL.tags-abilities into GAM.TOOL.data. Remove "tag queries" from the C-ABILITY summary, replacing it with "consumes tag queries from C-GAMEDATA". Pick an independent oracle author for C-GAMEDATA, such as ai-behavior-perception.

### K-GAMEPLAY-4 · major · missing-contract
- **Target:** gameplay-camera, C-VIEW, gameplay-systems-toolkit, character-movement, narrative-dialogue, GAM.CAM.rigs
- **Finding:** gameplay-camera provides no contract. The systems that need to drive the gameplay camera therefore have no API to call it: abilities (aim or zoom modes), movement (mount and vehicle transitions, swimming), dialogue (conversation framing), vehicles, and game-team code. Today their only way in is to write to C-VIEW directly as their own view source, which skips the rig, collision and blending owner. C-VIEW also puts "shake/FOV channels" in spatial-transforms, while shake content and its accessibility scaling (GAM.CAM.comfort) belong to gameplay-camera.
- **Evidence:** Production camera systems expose a camera-mode stack or request API to gameplay. Examples are Lyra's ULyraCameraMode stack pushed by abilities, Unreal's camera modifiers and shake assets, Cinemachine priorities and impulse sources, and Mark Haigh-Hutchinson's *Real-Time Cameras* (camera hints). Without that API, every caller builds its own camera and the photosensitivity and shake options stop applying to all of them.
- **Proposed change:** Add C-CAMERA (layer 4, owner gameplay-camera): "camera mode/hint requests with priority and blend, per-local-player rig binding, shake/impulse assets scaled by a11y settings, framing targets". Add C-CAMERA? to consumes of gameplay-systems-toolkit, character-movement, narrative-dialogue, vehicle-physics and cinematics-sequencer (for blend-back). Limit C-VIEW's shake/FOV channels to the final composition of view sources.

### K-GAMEPLAY-5 · major · overlap
- **Target:** gameplay-systems-toolkit (purpose, expertise), gameplay-camera, GAM.CAM.photo, GAM.CAM.rigs
- **Finding:** The gameplay-systems-toolkit purpose still reads "camera system … photo mode", and its expertise lists "camera design". Both overlap the separate gameplay-camera skill, which owns GAM.CAM.rigs and GAM.CAM.photo. The toolkit's non_responsibilities route only cinematic cameras away, not the gameplay camera.
- **Evidence:** The purpose field becomes the SKILL.md charter. Two agents would each build a camera stack and photo mode, and check.py cannot see prose ownership.
- **Proposed change:** Remove "camera system" and "photo mode" from the gameplay-systems-toolkit purpose and "camera design" from its expertise. Add the non-responsibility ["Gameplay cameras & photo mode", "gameplay-camera"].

### K-GAMEPLAY-6 · major · omission
- **Target:** net-session, replication, GAM.FW.local-players, PLAT.SVC.user-model, INP.ACT.local-mp
- **Finding:** Split-screen is covered locally (input assignment, per-player views, UI roots and listeners), but nothing covers multiple local players sharing one network connection in online play. Missing are per-local-player sub-IDs and ownership in replication, per-player auth and privileges (including guests without accounts), players joining or leaving mid-session, and per-player relevancy and prediction.
- **Evidence:** Shipped split-screen online titles need this: Rocket League, Halo MCC/Infinite, Call of Duty and Fortnite (duos split-screen). Unreal models it as UChildConnection per extra local player. Console TRCs/XRs cover guest and secondary-user sign-in for online play. Without it, the coop-3d-listen-client and online-3d-console-client configurations can support split-screen only offline.
- **Proposed change:** Add NET.SESS.local-players, "Multiple local players per connection: sub-player IDs, per-player auth/guest privileges, per-player ownership & prediction, drop-in/drop-out mid-session", owned by net-session with contributors gameplay-architect, replication, platform-services and prediction-rollback. Mention per-local-player sub-IDs in the C-NETSESSION/C-REP summaries.

### K-GAMEPLAY-7 · major · omission
- **Target:** UI.LOC.messageformat, C-LOC, UI.LOC.gather, gameplay-data, radar.json
- **Finding:** Plurals and gender are covered only for the message itself (ICU MessageFormat class). Nothing covers grammatical agreement with substituted terms: item, character or place names inserted into sentences need per-locale gender, animacy, case forms, articles and elision. Item names in gameplay-data rows must carry these attributes, or sentences like "You picked up {item}" will be ungrammatical in Slavic, Germanic, Romance and Semitic languages.
- **Evidence:** Mozilla Fluent handles this with terms and attributes. Unicode MessageFormat 2.0 (final in CLDR/LDML 47, 2025) adds custom selectors and functions for it. Unreal needed argument-modifier functions ({Arg}|gender, |plural, |hpp for Korean postpositions). Loot-heavy RPGs routinely ship workarounds such as "Item: X" phrasing because the data model lacked these attributes. Retrofitting per-term grammatical attributes into data tables and the gather pipeline is expensive rework.
- **Proposed change:** Add UI.LOC.terms, "Localizable terms with per-locale grammatical attributes (gender, animacy, case/declension forms, articles, Korean/Japanese particles) and agreement in substituted messages", owned by localization-i18n with contributors gameplay-data and narrative-dialogue, maturity E. Add a radar entry for MessageFormat 2.0 syntax adoption (M) with fallback ICU MF1 plus term attributes. Extend C-LOC's summary to "term references with grammatical attributes".

### K-GAMEPLAY-8 · major · omission
- **Target:** character-movement, GAM.MOVE.*, C-GAMEDATA, GAM.TOOL
- **Finding:** Character movement is the main game-feel tuning surface, yet character-movement does not consume C-GAMEDATA, has empty tool_consumes and owns no GAM.TOOL capability. Designers have no data path for movement curves: acceleration, jump arcs, coyote and buffer windows, per-mode parameters and difficulty variants. There is also no movement debugger showing trajectory history, mode transitions, network corrections and resimulation divergence.
- **Evidence:** Unreal CharacterMovement exposes tunables as data and ships p.NetShowCorrections and movement visualizers. Mover 2.0 ships a rollback debugger. Platformer postmortems (Celeste, Hollow Knight) attribute feel to rapid tuning iteration. Networked movement bugs are diagnosed almost entirely through correction visualization.
- **Proposed change:** Add C-GAMEDATA to character-movement consumes, and C-EDCMD, C-EDHOST and C-EDVIEW to its tool_consumes. Add GAM.TOOL.movement, "Movement tuning assets & live tuning, trajectory/mode-history and network-correction visualization", owned by character-movement with contributors visual-debugging-tools and prediction-rollback.

### K-GAMEPLAY-9 · major · wrong-owner
- **Target:** INP.DEV.haptic-assets, AUD.CONTENT.haptics, input-devices-haptics, audio-content-runtime
- **Finding:** Authored haptic and trigger-effect assets and their playback (INP.DEV.haptic-assets) are owned by the layer-2 device skill. That skill has no tool_consumes, so no authoring or cook path, and it provides only C-DEVICE. Authored haptics need content-runtime features: an event and parameter model, priority and voice limiting, mixing of overlapping effects, looping, routing to the right local player's device, and syncing to the audio clock. Those features live in audio-content-runtime, which owns only audio-to-haptics.
- **Evidence:** DualSense haptics are driven as an audio stream, and Wwise and FMOD both ship DualSense haptic outputs. Sound designers author haptics in audio tools, for example Meta Haptics Studio and Apple Core Haptics AHAP, often alongside the sound. Splitting asset playback from audio-to-haptics produces two mixers for one actuator.
- **Proposed change:** Move INP.DEV.haptic-assets to audio-content-runtime (as AUD.CONTENT.haptic-assets), with input-devices-haptics as a contributor. Keep INP.DEV.haptics as the device endpoint (output channel, capabilities, per-user pairing). Add AUD.TOOL.haptics, "Haptic effect authoring & device preview", owned by audio-content-runtime.

### K-GAMEPLAY-10 · major · omission
- **Target:** narrative-dialogue, cinematics-sequencer, GAM.NARR, ANM.CINE, ANM.SYN.multi-actor
- **Finding:** No capability covers systemic dialogue scenes: generating and adjusting conversation shots, camera framing, gestures, look-ats and timing from dialogue lines, with a manual-override layer. The only dialogue-scene path is hand-keying each scene in the sequencer, which cannot scale to AAA RPG line counts across localized VO lengths.
- **Evidence:** "Behind the Scenes of the Cinematic Dialogues in The Witcher 3" (GDC 2016) describes about 2,400 dialogue scenes that were generated and then polished. The BioWare conversation systems (Mass Effect, Dragon Age) use the same approach. Localized VO changes line durations, so hand-keyed timing breaks per locale.
- **Proposed change:** Add GAM.NARR.scenes, "Systemic dialogue scene generation (shot/camera/gesture/look-at selection from line data, per-locale retiming, manual override into C-SEQ)", owned by narrative-dialogue with contributors cinematics-sequencer, gameplay-camera, motion-synthesis and facial-animation. Add C-SEQ? to narrative-dialogue consumes.

### K-GAMEPLAY-11 · minor · maturity-error
- **Target:** ANM.FACE.lipsync, radar "Audio-driven & ML lip sync"
- **Finding:** One M capability conflates established audio- and phoneme-driven lip sync with emerging ML lip sync. The radar fallback, "Phoneme/viseme lip sync", is effectively the capability itself.
- **Evidence:** FaceFX has shipped in AAA titles since the mid-2000s. JALI shipped Cyberpunk 2077 with procedural lip sync in 10 languages (2020). Only ML audio-to-face (for example NVIDIA Audio2Face) is emerging.
- **Proposed change:** Split into ANM.FACE.lipsync (E, "phoneme/viseme & procedural audio-driven lip sync, per-locale") and ANM.FACE.lipsync-ml (M, radar entry with fallback ANM.FACE.lipsync).

### K-GAMEPLAY-12 · minor · omission
- **Target:** UI.TXT.rich, UI.TXT.bidi, text-fonts
- **Finding:** CJK coverage lacks ruby annotation (furigana/zhuyin) and vertical text layout (UAX #50 orientation, tate-chū-yoko).
- **Evidence:** Furigana is standard in Japanese titles for younger audiences and in JRPGs and visual novels. Vertical layout is common in Japanese and Chinese visual novels and period titles. Both affect shaping, line breaking and layout, not just styling.
- **Proposed change:** Add UI.TXT.cjk-layout, "Ruby annotations and vertical text layout (UAX #50)", owned by text-fonts with contributor ui-architect.

### K-GAMEPLAY-13 · minor · scale-down
- **Target:** CORE.SCALE.profiles, CORE.SCALE.actuators, GAM.FW.local-players, RND.ARCH.multiview
- **Finding:** Split-screen view count is not a scalability input. Neither the knob registry nor the governor reacts to 2–4 active views, which multiply culling, draw and streaming cost.
- **Evidence:** Split-screen titles switch presets per player count. Mario Kart 8 drops to 30 fps at 3–4 players, and Forza Horizon and Halo lower draw distance, LOD and effects in split-screen.
- **Proposed change:** Extend CORE.SCALE.profiles to "device-profile application and per-context knob sets (active view count / split-screen, XR)", adding gameplay-architect and render-architect as contributors.

### K-GAMEPLAY-14 · minor · maturity-error
- **Target:** AUD.SPAT.propagation, radar "Wave-based acoustic propagation"
- **Finding:** Precomputed wave-based and ray-traced acoustic propagation is labeled M, although both have shipped in AAA for years.
- **Evidence:** Project Acoustics/Triton shipped in Gears of War 4 (2016), Gears 5 and Sea of Thieves. Steam Audio's ray-traced propagation has shipped in many titles. The radar's own evidence cites shipped systems.
- **Proposed change:** Relabel AUD.SPAT.propagation as E. If a frontier is needed, add AUD.SPAT.propagation-dynamic (M, "real-time GPU/RT wave or path propagation for dynamic geometry") with fallback AUD.SPAT.propagation.
