# K-PLATFORM — round 3 findings

### K-PLATFORM-1 · blocker · wrong-boundary
- **Target:** platform-console, rhi-console, certification-compliance, C-CERT, platform-services, xr-runtime (PLAT.XR.runtime-backends), input-devices-haptics, network-transport (NET.TRANS.local-network, NET.TRANS.nat), gpu-performance (PRF.GPU.tools), build-system-toolchains (BLD.SYS.platform-sdks), ci-cd-automation (BLD.CI.device-lanes), crash-diagnostics, accessibility (UI.A11Y.screen-reader), PLAT.CON.confidential-slots, ARCH.STRUCT.platform-backends, PLAT.PAL.confidential-extensions
- **Finding:** Confidentiality is modelled per skill, and only two skills carry it (platform-console and rhi-console). The gate also forbids an NDA class on any skill that is not tagged console-only. Yet much NDA material sits in untagged skills that have no access class:
  - console TRC/XR/Lotcheck text in certification-compliance, published to every skill through the universal C-CERT;
  - first-party service SDKs in platform-services (docs/00 §8 itself says "The first is NDA SDKs plus certification");
  - the console XR SDK in xr-runtime;
  - console pad and adaptive-trigger libraries in input-devices-haptics;
  - console socket, relay and ad-hoc libraries in network-transport;
  - console GPU profilers in gpu-performance;
  - console compilers and SDKs in build-system-toolchains;
  - devkit lanes in ci-cd-automation;
  - console dumps in crash-diagnostics;
  - console TTS/STT APIs in accessibility.

  The slot lists also disagree. ARCH.STRUCT.platform-backends names input, sockets and the IME/a11y bridge as backend slots, but PLAT.CON.confidential-slots omits all three. The result: either unlicensed agents receive NDA documents, or these capabilities have no owner who is allowed to build them for consoles.
- **Evidence:** Platform-holder developer agreements license documentation per named party and per holder. This is why production engines keep console code in separate, access-controlled platform-extension trees (UE's Platforms/ extension model with per-holder source access), and this framework's own PLAT.PAL.confidential-extensions describes the same idea. A register that every skill consumes cannot carry TRC wording.
- **Proposed change:**
  - Add a capability-level / module-level `access` field, e.g. cap row option `"access":"nda:<holder>"` and `implements: ["C-X@nda:<holder>"]`.
  - Allow confidential per-holder sub-instances inside non-console skills. Change the check rule from "NDA skill must be console-only" to "NDA-classed capabilities/modules are only in console-tagged instances".
  - Split C-CERT into a public register (requirement id, owning capability, sanitized paraphrase) and per-holder confidential partitions.
  - Add input/haptics, sockets/relay and IME/TTS/a11y bridge to PLAT.CON.confidential-slots, and add platform-console as a contributor to the owning capabilities.

### K-PLATFORM-2 · major · missing-contract
- **Target:** PLATFORMS (model.py), skills.json configurations, C-PAL, C-RHI, rhi-d3d12, rhi-vulkan, rhi-metal, rhi-console, platform-desktop, platform-mobile, ARCH.REQ.platform-matrix
- **Finding:** The platform axis is one coarse family tag, so the per-platform implementer proof passes when *any* implementer exists for the family:
  - `pc` covers Windows, Windows-on-ARM, Linux/SteamOS and macOS;
  - `mobile` covers iOS/iPadOS and Android;
  - `console` covers every holder;
  - `xr-standalone` covers Android-based headsets and visionOS.

  For example, a `pc` configuration is "closed" by rhi-d3d12 alone, although macOS needs Metal and Linux needs Vulkan. A `mobile` configuration is closed by rhi-vulkan alone, although iOS has no Vulkan. `console` is closed by one rhi-console skill, whatever holder instances actually exist. ARCH.REQ.platform-matrix (OS × ISA × GPU API × store) is described in a capability but is not machine data.
- **Evidence:** The closure rule in check.py (`p in m.skill(x)["platforms"]`) is evaluated at family granularity. MoltenVK/KosmicKrisp exist but are not what rhi-metal assumes. Each console holder has its own graphics API (D3D12.X, AGC-class, NVN-class).
- **Proposed change:**
  - Add `platform_variants` to skills.json, e.g. `pc:{win-x64, win-arm64, linux-steamos, macos}`, `mobile:{ios, android}`, `console:{holder-a, holder-b, holder-c}` (sealed names), `xr-standalone:{android-xr, visionos}`, `server-host:{linux-x64, linux-arm64}`.
  - Let implementers declare variants, and let configurations name variants or default to all of them.
  - Make needs_implementer closure per variant, and generate ARCH.REQ.platform-matrix from this data.

### K-PLATFORM-3 · major · dependency-error
- **Target:** milestones.json M0/M1 (contracts_frozen), C-PAL, C-RHI, C-IO, C-PRESENT, C-DEVICE, C-GPUTIER, C-TARGETPLAT; platform-mobile, platform-web, platform-console, rhi-webgpu, rhi-console
- **Finding:** Platform contracts freeze before the platforms that stress them exist:
  - C-PAL freezes at M0, when the only implementer is platform-desktop.
  - C-RHI, C-IO, C-PRESENT, C-DEVICE, C-GPUTIER and C-TARGETPLAT freeze at M1.
  - Every console, mobile and web implementer (platform-console/mobile/web, rhi-console, rhi-webgpu) arrives at M2.

  The freeze rule only asks for "owner + one consumer". It never asks for implementers across platform families, so the interfaces are proven only against Windows/Vulkan desktop.
- **Evidence:** The constraints that reshape these interfaces are exactly the non-desktop ones:
  - web forbids blocking on the main thread and synchronous storage outside workers (Atomics.wait is disallowed on the main thread; OPFS sync handles are worker-only);
  - Android destroys the window surface on background, which forces a swapchain/surface-recreation path in C-PRESENT/C-RHI;
  - WebGPU uses implicit sync and bind groups;
  - console suspend requires quiescing within a certification deadline;
  - console IO uses hardware decompression queues (C-IO).

  PC-first ports that retrofit these are a well-known source of rework.
- **Proposed change:**
  - Add a check rule: a needs_implementer contract freezes only after the milestone in which each platform family claimed by any configuration has an implementer, or a recorded conformance spike by it.
  - Move platform-mobile, platform-web and rhi-webgpu into M1 as draft implementers, and add a console spike (platform-console, rhi-console) as a required reviewer before the freeze.
  - Alternatively, move the C-PAL/C-RHI/C-IO/C-PRESENT/C-DEVICE freezes to M2.

### K-PLATFORM-4 · major · obsolete-assumption
- **Target:** PLAT.WEB.runtime, platform-web, CORE.JOBS.degenerate, BLD.SYS.configs, configurations minimal-client / indie-2d-client / indie-2d-online-web-client
- **Finding:** PLAT.WEB.runtime states "SharedArrayBuffer required; cross-origin isolation assumed on every host". Many hosts cannot provide COOP/COEP:
  - web game portals and embedding iframes;
  - ad-supported pages, where COEP require-corp breaks third-party ads and embeds;
  - messaging-platform instant games;
  - some itch.io-style hosts unless an opt-in toggle is set.

  Without isolation there is no SAB, and a threaded WASM binary will not run at all. The smallest configurations, which are the ones most likely to ship on portals, therefore fail. The framework already has a 0-worker inline mode (CORE.JOBS.degenerate), but no non-threaded web build variant or hosting-mode capability uses it.
- **Evidence:** Godot 4.3 (2024) reintroduced a single-threaded web export specifically because COOP/COEP made threaded exports unusable on many hosts. Unity's web builds default to non-threaded. The COEP `credentialless` mode is not universally supported.
- **Proposed change:**
  - Reword PLAT.WEB.runtime to "WASM threads where cross-origin isolated; isolation detected at load".
  - Add a new capability, PLAT.WEB.hosting-modes (owner platform-web, contributors job-system-task-graph, build-system-toolchains, audio-architect): non-isolated single-threaded WASM variant, COOP/COEP/credentialless detection, and an audio worklet without SAB.
  - Add a "web-nonisolated" build variant in BLD.SYS.configs.
  - Make M2 exit require indie-2d-client@web to run on a non-isolated host.

### K-PLATFORM-5 · major · other
- **Target:** BLD.REL.staged-rollout, milestones M4 gate
- **Finding:** The capability named "staged rollout" is defined as "Simultaneous global rollout to all players with post-release kill switches". That is the opposite of a staged rollout, and M4 gates on it, so the gate would validate an all-at-once release.
- **Evidence:** Google Play staged rollouts (percentage and halt), App Store phased release (7-day), Steam beta branches, and canary/rolling server deploys all stage releases. Console patch channels cannot be percentage-staged, so staging is done through server-side feature flags (PLAT.SVC.remote-config) and rolling server fleets. Every one of these limits blast radius before full exposure.
- **Proposed change:** Rename it to "Staged/phased rollout per channel (store percentage/phased release, beta branches, canary servers, flag-gated exposure where stores cannot stage) with halt criteria from crash/telemetry and kill switches". Contributors: online-services-liveops, platform-services, dedicated-server, crash-diagnostics.

### K-PLATFORM-6 · major · maturity-error
- **Target:** PLAT.PAL.cloud-streaming, radar entry "Cloud game streaming targets", platform-architect, platform-console, platform-desktop, input-system, ui-architect
- **Finding:** Cloud streaming is labelled emerging (M), owned only by the PAL lead, with the fallback "Treat as a PC target". This is wrong on both counts:
  - It is established. GeForce NOW (2020), Xbox Cloud Gaming (2020) and PlayStation cloud streaming have been live for years.
  - The two largest console services stream **console** builds, not PC builds.

  Engine-side obligations are also unowned:
  - detecting a streaming session (GFN SDK, console streaming APIs);
  - touch-control overlays for phone clients (Xbox Touch Adaptation Kit class);
  - a text-legibility/UI-scale tier for encoded video;
  - encode latency inside the latency budget;
  - device-kind changes mid-session.
- **Evidence:** Xbox GDK exposes streaming-session APIs and Touch Adaptation Kit bundles in the console package. The GeForce NOW SDK provides session detection and storefront integration for PC builds.
- **Proposed change:**
  - Set maturity to E and remove the radar entry (or reclassify it E).
  - Split the capability into PLAT.CON.cloud-streaming (platform-console) and PLAT.DESK.cloud-streaming (platform-desktop). Keep policy in PLAT.PAL.cloud-streaming with contributors input-system (touch-overlay actions), ui-architect (legibility tier), runtime-scalability and frame-orchestration.
  - Add a `cloud` variant under K-PLATFORM-2.

### K-PLATFORM-7 · major · missing-contract
- **Target:** C-SVC, platform-services, platform-desktop, platform-mobile, platform-web, ARCH.REQ.platform-matrix, configurations
- **Finding:** C-SVC is not `needs_implementer`. Only platform-console implements it. The storefront/service SDK backends for other platforms have no platform-tagged owner and no closure proof:
  - Steamworks, Epic Online Services/EGS, GOG Galaxy, Microsoft Store/GDK-on-PC;
  - GameKit/StoreKit and Google Play Games/Play Billing;
  - EU-DMA alternative app marketplaces;
  - web-portal SDKs.

  Storefront is also missing as a configuration axis. The same `pc` build differs per store in entitlements/DRM, overlay, achievements, packaging (depots vs MSIX) and submission.
- **Evidence:** ARCH.REQ.platform-matrix names "store" as a dimension, but no data carries it. QA.CERT.store-policy mentions alternative stores but has no implementer. Shipping PC titles routinely maintain three or more store backends.
- **Proposed change:**
  - Make C-SVC `needs_implementer` with a null/DRM-free backend.
  - Add `storefronts` to configurations.
  - Add capabilities PLAT.DESK.storefronts (platform-desktop), PLAT.MOB.storefronts (platform-mobile) and PLAT.WEB.portals (platform-web), each implementing C-SVC for its platform.
  - Keep platform-services as the owner of the cross-store model only.

### K-PLATFORM-8 · major · wrong-boundary
- **Target:** rhi-d3d12 (platforms ["pc"]), rhi-console, RND.RHI.console
- **Finding:** rhi-d3d12 is PC-only, and "each console graphics API" goes to rhi-console as an independent backend. The Xbox Series graphics API is a D3D12 superset that shares most backend code, DXC and the enhanced-barrier model with PC D3D12. As modelled, a second agent re-implements D3D12 in a separate NDA silo, and the two backends will drift. The GDK runtime shared by PC and console (GameInput, XGameRuntime) is split the same way.
- **Evidence:** Production engines keep one D3D12 backend with a confidential Xbox extension (UE's D3D12RHI plus console platform extension). Microsoft's own GDK positioning makes PC and console D3D12 a common base.
- **Proposed change:** Model the Xbox-class backend as a confidential module of rhi-d3d12 (`implements: ["C-RHI@nda:xbox"]`, access class per K-PLATFORM-1), with rhi-d3d12 as the base owner. Restrict rhi-console to non-D3D12 holder APIs. Apply the same pattern to GDK-shared PAL code between platform-desktop and platform-console.

### K-PLATFORM-9 · major · wrong-owner
- **Target:** C-PAL.oracle_author = accessibility
- **Finding:** The conformance oracle for the widest boundary contract in the engine is authored by accessibility. C-PAL covers OS services, thread QoS/affinity, clock-domain correlation, suspend/resume quiesce, memory pressure, display/HDR and five implementers, one of them NDA. Accessibility consumes only the OS accessibility-settings slice. It lacks the competence to write the lifecycle, clock and thread cases, and it has no NDA access for the certification-mandated lifecycle timings.
- **Evidence:** The framework already has a skill whose job is on-device conformance and event injection: test-runtime-harness (QA.HOST.runner, QA.HOST.fault-points), with PLAT.PAL.event-injection contributors test-runtime-harness and certification-compliance.
- **Proposed change:** Set oracle_author to test-runtime-harness. Require co-signature from certification-compliance (per-holder confidential partition, K-PLATFORM-1) for lifecycle and system-event cases, and from accessibility only for the accessibility-settings slice.

### K-PLATFORM-10 · major · scale-down
- **Target:** radar "GLES / WebGL backends" (class S, non_goal), radar "WebGPU backend & web 3D", configurations minimal-client, indie-2d-client, indie-2d-online-web-client
- **Finding:** WebGL2 is excluded as a non-goal, yet the smallest configurations claim `web`. Three problems follow:
  - **Reach.** WebGPU is still unavailable on Firefox for Android, on iOS/iPadOS before 26, and on Android devices outside Chrome's WebGPU allow-list (Android 12+ with specific GPU vendors). The 2D/minimal web audience (portals, low-end Android, school Chromebooks) is exactly where coverage is weakest.
  - **Unobservable trigger.** The revisit trigger ("device DB shows >10% of audience without WebGPU") can never fire. The device DB only records devices that can run the engine.
  - **Mislabel.** GLES/WebGL are established APIs, not speculative (S). The class hides that this is a scope decision.
- **Evidence:** Chrome WebGPU on Android shipped in Chrome 121 for Android 12+ on Qualcomm/ARM GPUs only. Safari shipped WebGPU in version 26 (2025). Firefox shipped it on Windows only in 141 (2025).
- **Proposed change:**
  - Reclassify the entry as E non-goal.
  - Replace the trigger with an external measure (browser-capability share from web analytics or portal SDK stats, gathered by platform-web).
  - Either add a min2d/minimal-only bounded WebGL2 path behind C-GPUTIER (render-2d-vector draw lists only), or drop `web` from minimal-client and indie-2d-client until the trigger is met, and say so in docs/00.

### K-PLATFORM-11 · major · other
- **Target:** untrusted-inputs.json "saves" (trust: trusted-local), persistence-save, GAM.SAVE.integrity
- **Finding:** Save files are registered as trusted-local, but players control them:
  - save editors;
  - saves shared online;
  - USB/cloud transfer.

  On consoles, save parsers are a known entry point for jailbreaks, and holders treat them as security incidents that need patches. The trust label invites unhardened parsing and treating signatures as the defence.
- **Evidence:** The Twilight Hack (Wii, 2008, a Zelda save exploit), the Splinter Cell/007 save exploits (original Xbox softmods), and mast1c0re (2022: an Okage: Shadow King PS2 save exploit on PS4/PS5).
- **Proposed change:** Set `saves` to hostile-local. Add limits "size/depth/count/version range". State in GAM.SAVE.integrity that the signature is tamper evidence only and the parser is hardened regardless. Add certification-compliance as a contributor for holder security-incident obligations.

### K-PLATFORM-12 · minor · wrong-boundary
- **Target:** platform-desktop (macOS), platform-mobile (iOS/iPadOS/visionOS), rhi-metal
- **Finding:** Apple support is split by form factor into two platform experts. The same frameworks would then be implemented twice: GameController, GameKit, StoreKit, CAMetalLayer surfaces, AVAudioSession/CoreAudio, code signing/notarization and TCC. tvOS is absent altogether.
- **Evidence:** Apple's game frameworks are shared across macOS, iOS and visionOS (Apple's "Bring your game to Mac" / Game Porting Toolkit guidance, and the WWDC game sessions).
- **Proposed change:** Add a shared module attribution, e.g. `apple-common` owned by platform-mobile, that platform-desktop consumes for macOS. Record tvOS as supported or as a non-goal in ARCH.REQ.platform-matrix.

### K-PLATFORM-13 · minor · omission
- **Target:** PLAT.MOB, PLAT.PAL.display, PLAT.PAL.lifecycle (contributors), platform-web
- **Finding:** Several platform behaviours have no capability:
  - resizable/multi-window mobile apps: iPadOS 26 deprecates UIRequiresFullScreen, plus Android foldable posture changes, ChromeOS and desktop modes;
  - dynamic HDR/EDR headroom that changes with brightness (Apple EDR, Android HDR headroom APIs);
  - browser lifecycle: page visibility, rAF throttling in background tabs, bfcache and tab discard. platform-web is not a contributor to PLAT.PAL.lifecycle.
- **Evidence:** Apple's iPadOS 26 windowing changes; Android large-screen/foldable guidance; the WHATWG Page Lifecycle.
- **Proposed change:**
  - Add PLAT.MOB.windowing ("resizable/multi-window, posture and aspect changes") owned by platform-mobile.
  - Extend PLAT.PAL.display to "…incl. dynamic HDR headroom events", with contributor post-color-hdr.
  - Add platform-web as a contributor to PLAT.PAL.lifecycle.

### K-PLATFORM-14 · minor · omission
- **Target:** untrusted-inputs.json; PLAT.PAL.device-db, PLAT.MOB.notifications, PLAT.PAL.pointer-shell
- **Finding:** Three platform-sourced inputs are missing from the registry:
  - The remotely updated device DB and driver deny-list, which can disable features or crash the whole fleet if wrong.
  - Push-notification payloads.
  - Clipboard and drag-and-drop content, which flows into chat, UI and the editor.
- **Evidence:** Remote device-profile/deny-list pushes are standard on Android titles. A malformed update is a fleet-wide incident. Pasted and dropped content is attacker-controllable.
- **Proposed change:**
  - Add `device-db-updates` (validating_owner platform-architect, semi-trusted-signed, limits "schema/rollback/staged").
  - Add `push-payloads` (platform-mobile, hostile-remote, "length/schema").
  - Add `clipboard-dragdrop` (platform-architect, hostile-local, "size/type allow-list").
