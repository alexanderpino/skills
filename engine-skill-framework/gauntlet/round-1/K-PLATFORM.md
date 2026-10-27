# K-PLATFORM · Platform Critic · Round 1 (blind)

Scope reviewed: data/*.json (source of truth), docs/00-design-principles.md, check.py output (0 errors). The findings are ordered by severity.

### K-PLATFORM-1 · blocker · wrong-boundary
- Target: C-PAL, crosscutting.json concern "platform portability", C-RHI, C-IO, C-AUDIO, C-SVC, skills rhi-core, async-io-storage, audio-architect, input-devices-haptics, network-transport, persistence-save, crash-diagnostics, text-fonts, accessibility, memory-allocators
- Finding: The framework has two binding rules: C-PAL ("No platform #ifdefs above this line", layer 0) and the cross-cutting obligation "No platform code above the PAL". The map then assigns platform-specific implementations to skills in layers 1 to 3. RND.RHI.backends covers D3D12, Vulkan, Metal, console APIs and WebGPU. RES.IO.backends covers io_uring, IOCP, DirectStorage and console APIs. AUD.ARCH.devices, INP.DEV.abstraction (GameInput) and NET.TRANS.sockets ("platform network APIs") are also platform code, as are GAM.SAVE.platform, OBS.CRASH.capture, UI.TXT.ime, UI.A11Y.screen-reader and all of C-SVC (PSN, Xbox and Steam SDKs, layer 3). Under the stated rule every one of these is illegal. The only alternative is to move all of them into `platform-architect`, which lacks the D3D12, audio and IO expertise. No rule says which skill writes, for example, the PS5 audio-endpoint code, the Switch save-journal code or the Android AAudio backend. The platform experts (`platform-desktop/console/mobile-portable`) provide no contract, and they are modeled as *consumers* of C-PAL, not as its implementers. Agents will either fail the fitness function or write duplicate per-platform code in several places.
- Evidence: Shipping engines do not put all platform code in one layer. UE uses per-module `Platform/` subfolders plus the NDA `Platforms/<X>` extension tree, where each module owns its backend. Frostbite and id Tech keep API backends inside the renderer. What matters is a *declared* set of backend sites, not one layer.
- Proposed change: Add `ARCH.STRUCT.platform-backends` (owner `platform-architect`, contributors `architecture-governance`). It defines a closed list of **platform backend slots**: RHI backend, IO backend, audio endpoint, input device, socket/network stack, crash handler, save storage, service SDK adapter, IME/a11y bridge, VM/page primitives. The rule for each slot: the domain skill owns the slot interface and the backend code, and the matching platform expert (`platform-desktop`, `-console`, `-mobile`, `-web`) is mandatory contributor and reviewer. Rewrite the C-PAL summary and the crosscutting obligation to "platform code only in PAL or in a registered backend slot". Make the fitness function whitelist the slot directories. Give each platform expert a process contract (`C-PLAT-<target>`: platform requirements, constraints and review obligations) so that its relationship to the slot owners is a real edge.

### K-PLATFORM-2 · blocker · scale-down
- Target: skills.json profiles and configurations; platform-console `["std3d"]`, platform-mobile-portable `["mobile3d","min2d"]`, xr-runtime
- Finding: Profiles mix two independent axes, *game scale* and *target platform*, so configuration closure produces wrong platform ownership:
  - `indie-2d` and `indie-2d-online-moddable` contain no console skill, although 2D indies routinely ship on Switch, PlayStation and Xbox.
  - `mobile-3d` contains no console skill, so Switch/Switch 2 and other portable consoles get no console cert, user model or devkit ownership.
  - `standard-3d`, `open-world` and `aaa-open-world-online` contain no mobile skill, although AAA iOS ports on A17 Pro/M-class hardware exist.
  - `xr-3d` (std3d+xr) excludes `platform-mobile-portable`, but the dominant standalone headset class (Quest) is Android with a TBDR mobile GPU and tight thermals.
  
  The closure proof therefore certifies configurations that are unshippable on their real targets.
- Evidence: Examples include Hollow Knight/Celeste-class 2D titles on every console, Resident Evil Village/AC Mirage on iPhone, and Quest being Android (Snapdragon XR2, Adreno TBDR).
- Proposed change: Add an orthogonal `targets` axis to configurations: `pc`, `console`, `portable-console`, `mobile`, `web`, `xr-standalone`, `cloud`, `server-host`. Tag platform experts, `rhi-*` backends and `certification-compliance` sub-scopes by target, not by scale. Compute closure over (scale profile × targets) and add at least `indie-2d × {pc, console, mobile}` and `xr-3d × xr-standalone`. As a minimal interim fix, set platform-console profiles to `["min2d","mobile3d","std3d"]`, set platform-mobile-portable to `["min2d","mobile3d","std3d","xr"]`, and let the chosen targets prune them.

### K-PLATFORM-3 · major · omission
- Target: program-orchestration (C-ORCH), platform-console, rhi-core, build-system-toolchains, security-engineering
- Finding: Nothing represents NDA and confidential platform material. Console SDKs, console graphics APIs (AGC/GNM-class, NVN-class, D3D12.X), cert documents and devkit tools are licensed per developer and cannot live in the general repository or be visible to every agent. The framework assumes any agent can read and modify any platform code. It has no access-tier concept in the ownership ledger, no segregated platform-extension repository layout, and no rule for how a non-licensed agent (e.g. `render-graph-scheduling`) gets feedback on console behavior.
- Evidence: UE's restricted `Platforms/` extension model, platform-holder developer agreements (Sony, Microsoft ID@Xbox/GDK, Nintendo Developer Portal) and Sony's/Nintendo's public-repo restrictions.
- Proposed change: Add `PLAT.PAL.confidential-extensions` (owner `platform-architect`, contributors `build-system-toolchains`, `security-engineering`, `program-orchestration`). It covers segregated platform-extension modules and repositories, a public stub interface for each slot (K-PLATFORM-1), and CI jobs that run confidential tests and report only sanitized results. Extend C-ORCH with access tiers per ledger entry, so that only agents with platform clearance are assigned console-extension work.

### K-PLATFORM-4 · major · wrong-boundary
- Target: rhi-core, RND.RHI.backends, RND.RHI.caps
- Finding: A single expert owns abstraction design plus five or more backends (D3D12, Vulkan, Metal, WebGPU, console APIs), PSO caching, presentation, device-lost handling and driver workarounds. By the framework's own §1 split rule ("different literatures, change at different rates, validated separately") the backends are separate skills. Each has its own specification, validation layer and conformance suite, and its own release cadence. For example, the D3D12 Agility SDK brought enhanced barriers, work graphs, SM 6.8/6.9 (cooperative vectors, SER, OMM) and GPU upload heaps. Vulkan brought Roadmap 2024/2026 profiles, VK_EXT_descriptor_heap and the Android Baseline Profile. Metal 4 (2025) changed the command model (MTL4 command allocators, argument tables, residency sets, ML in shaders). One agent cannot track all of this, and parallel backend work collides in one territory. The map also has no capability for API *profiles and version baselines* (Vulkan profiles/ABP, D3D12 feature levels plus the minimum Agility SDK version, Metal GPU families, WebGPU limits and features).
- Evidence: UE (D3D12RHI/VulkanRHI/MetalRHI as separate modules and owners), The Forge, Diligent and bgfx all organize by backend. Khronos Vulkan Profiles; Microsoft Agility SDK release notes; Apple WWDC25 "Discover Metal 4".
- Proposed change: Split into `rhi-core` (abstraction, sync semantics, caps model, backend conformance test suite) plus experts `rhi-d3d12`, `rhi-vulkan`, `rhi-metal` and `rhi-webgpu`, with console backends living in confidential extensions (K-PLATFORM-3) under `rhi-core` review. Add `RND.RHI.api-baselines` (owner `rhi-core`): the minimum API version, profile and extension set per hardware tier. Add `BLD.REL.api-redist` (owner `packaging-release-patching`) for shipping the Agility SDK D3D12Core, the DXC/DXIL runtime and similar components.

### K-PLATFORM-5 · major · obsolete-assumption
- Target: RND.RHI.bindless, C-RHI, docs/00 §6 default stances, render-2d-vector, profiles min2d/mobile3d
- Finding: §6 makes "Bindless is the default binding model (`rhi-core`)" and justifies it by rejecting slot binding. Unlike GPU-driven rendering (RND.GEO.fallback), bindless has no declared fallback. WebGPU has no bindless in core (binding arrays are still a proposal) and has low per-stage storage-buffer and texture limits. Many active Android GPUs lack full descriptor indexing or have small descriptor limits. WebGPU also lacks async compute queues, timeline semaphores, mesh shaders and RT. `rhi-core` and `render-2d-vector` are tagged `client`, so `indie-2d` (web and mobile targets) inherits a bindless-only RHI.
- Evidence: W3C WebGPU spec limits (maxStorageBuffersPerShaderStage, default 8), the gpuweb "bindless" proposal status, the Android Baseline Profile 2022 (descriptor indexing not required) and Vulkan GPUInfo coverage data.
- Proposed change: Add `RND.RHI.binding-fallback` (owner `rhi-core`, maturity E). It defines a bounded-table or grouped binding path and a queue-model fallback (single queue, binary fences). C-RHI must state per-tier feature guarantees, and `render-2d-vector` must declare that it runs on the lowest tier. Revise the §6 row to read "bindless default on tiers that support it; tiered binding fallback required".

### K-PLATFORM-6 · major · omission
- Target: PLAT.PAL.web (owned by lead `platform-architect`, maturity M), job-system-task-graph, async-io-storage, network-transport, audio-architect, persistence-save
- Finding: The web target is one capability on the lead and is described as "evaluation of new targets". It has no expert, profile or target tag, and nothing states its constraints for other contracts. The web breaks several core assumptions:
  - Blocking the main thread is disallowed (no `Atomics.wait`). Threads need SharedArrayBuffer and cross-origin isolation (COOP/COEP).
  - WASM memory is limited to 4 GB (Memory64 is only emerging).
  - There is no synchronous or mapped file IO. Storage is OPFS/IndexedDB, with quotas and eviction.
  - There is no raw UDP. Networking is WebSocket, WebRTC data channels or WebTransport.
  - Audio runs through AudioWorklet and is blocked until a user gesture (autoplay policy).
  - Pointer lock and fullscreen require a user gesture.
  - Content is delivered over HTTP range and CDN streaming.
  
  RES.IO.mmap, the job system and NET.TRANS.sockets say nothing about any of this.
- Evidence: WebGPU shipped in Chrome/Edge (2023), Safari 26 (2025) and Firefox (2025, Windows). Unity Web and Godot 4 web exports hit exactly these constraints (Godot 4's threads/COOP-COEP deployment problems are well documented).
- Proposed change: Add expert `platform-web` (parent `platform-architect`, profiles min2d and mobile3d, target `web`). It owns `PLAT.WEB.runtime` (WASM threads, isolation, memory limits), `PLAT.WEB.storage` (OPFS/IndexedDB, quota; contributor persistence-save), `PLAT.WEB.delivery` (HTTP streaming, caching; contributor packaging-release-patching), `PLAT.WEB.io-gesture` (autoplay, pointer lock) and `PLAT.WEB.transport` (contributor network-transport). Keep PLAT.PAL.web as M only for WebGPU-class 3D. Require C-TASK, C-IO and network-transport to declare their web behavior.

### K-PLATFORM-7 · major · overlap
- Target: ARCH.REQ.hardware-tiers (engine-architect), PLAT.PAL.capability-tiers (platform-architect), RND.RHI.caps (rhi-core), PRF.METH.scalability "device profiles" (performance-architect), RND.ARCH.scalability (render-architect), CNT.COOK.variants, RND.RHI.workarounds
- Finding: Six owners have "tier" or "profile" capabilities, and the chain between them is undefined. Nothing owns the **device capability database**: the data mapping SoC/GPU/driver/OS/RAM to a tier, remotely updatable, with deny-lists and fed by telemetry hardware surveys. Nothing owns **driver policy** either: minimum and known-bad driver versions, user-facing "update your driver" handling, and vendor driver-profile interactions. Android fragmentation and PC driver issues make both mandatory. RND.RHI.workarounds covers code workarounds only.
- Evidence: UE DeviceProfiles.ini plus Android device-profile matching rules, Unity Adaptive Performance, and Google Play device catalog / Android Performance Tuner. Crash spikes after bad driver releases are routinely handled by deny-lists (Chrome GPU blocklist precedent).
- Proposed change: Add `PLAT.PAL.device-db` (owner `platform-architect`, contributors `rhi-core`, `performance-architect`, `observability-telemetry`, `platform-online-services` for remote update). Add `RND.RHI.driver-policy` (owner `rhi-core`, contributor `crash-diagnostics`). Document the chain once in C-PAL/C-BUDGET: raw caps (PAL/RHI) → device-db → tier → device profile knobs (performance-architect) → cook variants.

### K-PLATFORM-8 · major · omission
- Target: PLAT.CON.devkit ("Devkit workflows & SDK toolchains", platform-console) vs BLD.SYS.toolchains (build-system-toolchains)
- Finding: Console "SDK toolchains" is owned by platform-console, and the compiler matrix by build-system-toolchains. That is an overlap. Nobody owns **platform SDK version management** for all targets:
  - Pinning SDK versions: GDK, the console SDKs, Android NDK/SDK/AGP, Xcode/iOS SDK, Windows SDK, the Vulkan SDK.
  - Store- and cert-mandated minimums: Google Play target-API-level deadlines, App Store minimum Xcode/SDK, console cert minimum SDK versions.
  - OS-version support floors and deprecation.
  - Beta OS and firmware regression testing.
  - Cross-generation and backward-compatibility builds (PS4/PS5, Switch/Switch 2, Series X|S).
  
  These drive forced upgrades on fixed dates that cut across every skill.
- Evidence: Google Play annual targetSdk requirement. The Apple App Store requirement to build with the current Xcode/SDK from April each year. Console cert requirements on SDK version at submission. Switch 2 backward-compatibility behavior and PS5 PS4-BC.
- Proposed change: Add `BLD.SYS.platform-sdks` (owner `build-system-toolchains`, contributors all platform experts, `certification-compliance`) and reduce PLAT.CON.devkit to "devkit deploy/run/debug workflows". Add `PLAT.PAL.os-support-policy` (owner `platform-architect`) for supported OS versions, deprecation and beta-OS validation. Add `PLAT.CON.cross-gen` (owner `platform-console`) for cross-generation SKUs and backward-compatibility modes.

### K-PLATFORM-9 · major · missing-contract
- Target: certification-compliance (provides nothing), QA.CERT.platform, platform-console purpose ("platform requirements feeding certification")
- Finding: Certification requirements have no downstream contract. `certification-compliance` only tracks and pre-checks them, and consumes only C-SVC and C-A11Y. Real TRC/XR/Lotcheck-class requirements land in many skills:
  - The suspend deadline goes to frame-orchestration and persistence-save.
  - User sign-out and controller-disconnect handling go to input-system and platform-online-services.
  - Network-loss handling goes to network-transport.
  - The save-in-progress indicator goes to UI.
  - System error dialogs go to platform-online-services.
  - Title-safe area goes to UI.
  - Platform-correct button terminology and glyphs go to input-system.
  - Loading-screen activity and max-unresponsive time go to resource streaming.
  - Trophy/achievement rules go to platform-online-services.
  
  There is no requirement-to-owner mapping and no obligation on the owners. Non-console programs are also missing: Steam Deck Verified (default controller config, 1280×800 legibility, no launcher, on-screen keyboard), Xbox PC/Play Anywhere, Apple and Google store review. The framework already uses this pattern correctly for accessibility (C-A11Y).
- Evidence: Public summaries of Steam Deck Verified criteria (Valve), and the Xbox Requirements (XR), PlayStation TRC and Nintendo Lotcheck categories. Cert failures are routinely found late because no feature owner held the requirement.
- Proposed change: Add process contract `C-CERT` (owner `certification-compliance`): a register of external requirements per program (console cert, Steam Deck Verified, app-store review), each mapped to an owning capability. All client runtime skills plus `packaging-release-patching` consume it. Add `QA.CERT.programs` for the non-console verification programs. Clarify that platform-console *sources* console requirements into C-CERT and certification-compliance *owns* the register.

### K-PLATFORM-10 · major · omission
- Target: platform-online-services (PLAT.SVC.*), AUD.DSP.voip, PLAT.SVC.moderation, modding-ugc, PLAT.SVC.matchmaking
- Finding: The map has no capability for **platform privileges and social safety**, which are mandatory on consoles and mobile:
  - Communication and UGC privileges (e.g. Xbox privilege checks, PSN parental-control restrictions).
  - Block/mute lists that must be honored across crossplay.
  - Crossplay opt-out.
  - Cross-network communication restrictions.
  - Platform-mandated text filtering.
  - Child accounts, age gating and parental controls (spending, playtime).
  
  PLAT.SVC.identity mentions only crossplay *identity*. Voice chat, UGC and matchmaking agents will ship without these checks, which is a certain cert failure.
- Evidence: Xbox XR requirements on privileges and communication, PlayStation parental controls, the Nintendo parental-controls API, and Epic Online Services crossplay and social-overlay rules. Apple/Google child-account rules.
- Proposed change: Add `PLAT.SVC.privileges` (privilege and parental-control queries), `PLAT.SVC.social-safety` (block/mute/report sync, platform text filter) and `PLAT.SVC.crossplay-policy` (opt-in/out, cross-network comms policy), all owned by `platform-online-services`. Add them to C-SVC's summary and make `audio-dsp-mixing` (voip), `modding-ugc` and the UI chat consumers depend on them.

### K-PLATFORM-11 · major · omission
- Target: certification-compliance QA.CERT.*, UI.LOC.culturalization, platform-online-services
- Finding: Regional and legal coverage stops at ratings, privacy, accessibility law, licenses and photosensitivity. The following are missing:
  - **Store-policy compliance**: Apple in-app account deletion, App Tracking Transparency, IAP rules, EU DMA alternative stores and payments; Google Play policy and 64-bit/16 KB-page requirements; Steam content and AI-disclosure survey.
  - **Monetization law**: loot-box bans and restrictions (Belgium, Netherlands), mandatory odds disclosure (China, Korea, and Apple/Google policy).
  - **China-specific requirements**: ISBN licensing, real-name verification, minors' anti-addiction playtime limits, data localization.
  - **Online age-verification laws**: e.g. UK Online Safety Act 2023.
  - **Encryption export compliance**: US EAR self-classification, the App Store export-compliance declaration, and the French encryption declaration, all triggered by NET.TRANS.crypto and RES.PKG.crypto.
- Evidence: Belgian Gaming Commission ruling (2018), China NPPA minor-playtime notice (2021), Korean Game Industry Promotion Act probability disclosure (2024), Apple App Review Guidelines 5.1.1(v) and 3.1.
- Proposed change: Add `QA.CERT.store-policy`, `QA.CERT.monetization-law`, `QA.CERT.regional` (China/Korea regimes) and `QA.CERT.export-crypto` (owner `certification-compliance`; contributors `platform-online-services`, `security-engineering`). Add `PLAT.SVC.age-verification` and `PLAT.SVC.region-policy` (owner `platform-online-services`) for runtime enforcement: playtime limits, real-name checks, odds display data, region-locked features.

### K-PLATFORM-12 · major · wrong-boundary
- Target: platform-mobile-portable (PLAT.MOB.os "portable-console integration"), platform-console (PLAT.CON.*), platform-desktop (PLAT.DESK.handheld)
- Finding: Portable consoles are placed under the mobile skill. Their console concerns (cert, NDA SDK, devkits, multi-user model, suspend rules, platform-holder services) are owned by platform-console, so one device class has two owners with the boundary running through its OS. The map also has no **performance-mode switching** capability: docked/handheld clock and resolution changes (Switch/Switch 2), PS5 Pro enhanced mode, Series S vs X SKU targets, handheld-PC TDP profiles. Performance-mode switching is a runtime event that must reach performance-architect's device profiles.
- Evidence: Switch 2 is licensed and certified like a console (NVN-class API, Lotcheck), not like iOS or Android. Docked/handheld transitions are a runtime GPU-clock change that engines must handle live. The PS5 Pro requires separate "Pro Enhanced" validation.
- Proposed change: Move "portable-console integration" from PLAT.MOB.os to a new `PLAT.CON.portable` (owner `platform-console`) and rename platform-mobile-portable to `platform-mobile` (iOS, Android, standalone XR OS). Add `PLAT.PAL.performance-modes` (owner `platform-architect`, contributors `platform-console`, `platform-desktop`, `performance-architect`), surfaced as a C-PAL event consumed through C-BUDGET.

### K-PLATFORM-13 · major · omission
- Target: PLAT.DESK.display (platform-desktop), RND.RHI.present, RND.POST.hdr-output, ui-architect
- Finding: Display capability, HDR and VRR are owned only by the *desktop* expert. The map has no owner for:
  - **Console display**: system HDR calibration values (PS5/Xbox HDR settings exposed to titles), 120 Hz/VRR mode detection on TVs, and TV **title-safe area/overscan**, which is a cert item.
  - **Mobile display**: iOS EDR/ProMotion, Android refresh-rate selection and frame pacing (Swappy/ANativeWindow_setFrameRate, ADPF), display cutouts/notches and rounded corners, orientation changes, foldable resize and multi-window.
  
  Without these, `ui-architect` has no safe-area source and `post-color-hdr` has no platform calibration input.
- Evidence: Android Frame Pacing library (AGDK), Android Dynamic Performance Framework, the Apple EDR (Metal HDR) documentation, and the console cert requirements on safe area and HDR calibration usage.
- Proposed change: Move PLAT.DESK.display to `PLAT.PAL.display` (owner `platform-architect`, contributors all platform experts). Add `PLAT.PAL.safe-area` (title-safe area, cutouts, rounded corners; consumer ui-architect via C-PAL) and `PLAT.MOB.frame-pacing` (owner `platform-mobile`, contributor `frame-orchestration`). State in RND.POST.hdr-output that platform calibration comes from C-PAL.

### K-PLATFORM-14 · major · missing-contract
- Target: C-PAL summary, PLAT.PAL.lifecycle, CORE.MEM.virtual, CORE.MEM.oom
- Finding: The C-PAL summary covers only OS services, CPU/GPU discovery, windowing and lifecycle. The following system signals have no contract surface, so each consumer will call the OS directly, which breaks K-PLATFORM-1:
  - Power and thermal state (battery, low-power mode, thermal status).
  - Memory pressure and trim (Android onTrimMemory/LMK, iOS jetsam, console memory modes).
  - Network reachability and metered-connection changes.
  - Audio endpoint changes (headset hot-swap, per-user controller headsets on consoles).
  - Locale and time-zone changes.
  - OS accessibility settings (reduce motion, text size, screen reader active).
  - Overlay and focus loss (Steam overlay, console guide).
  - Low storage.
  - Virtual-memory page size.
  
  Page size is an obsolete-assumption trap. Google Play requires 16 KB page support for apps targeting Android 15+ from November 2025, and Apple silicon uses 16 KB pages. An allocator agent assuming 4 KB pages ships a broken build.
- Evidence: Android 16 KB page-size requirement (Android Developers, 2025), the Android ADPF thermal API, iOS `didReceiveMemoryWarning`/`os_proc_available_memory`, and GDK memory and PLM event models.
- Proposed change: Add `PLAT.PAL.system-events` (owner `platform-architect`) and extend the C-PAL summary with the system-event and system-query surface: power/thermal, memory pressure, network reachability, audio endpoint, locale, a11y settings, overlay/focus, storage, page size and granularity. Add consumers: performance-architect (thermal), memory-allocators (pressure, page size), network-transport, audio-architect, accessibility, localization-i18n.

### K-PLATFORM-15 · major · omission
- Target: platform-desktop, platform-mobile-portable, packaging-release-patching BLD.REL.packaging, persistence-save, shader-system RND.SHADER.cache, AUD.DSP.voip, anti-cheat-integrity
- Finding: No owner covers **OS security, sandbox and permission interaction**. On Windows this includes Defender real-time scanning, which stalls shader-cache and loose-file IO, and Controlled Folder Access blocking saves under Documents. It also includes SmartScreen reputation for new binaries. On macOS it includes Gatekeeper and notarization with the hardened runtime, and TCC prompts (microphone for voice chat, input monitoring). Mobile runtime permissions (microphone, notifications, Bluetooth controllers) and the Linux Steam Runtime/pressure-vessel container and Flatpak sandbox paths also lack an owner. So do kernel anti-cheat incompatibility with Proton/Linux (a Steam Deck blocker) and security software flagging executable memory or code injection by overlays. These are frequent causes of stutter, save loss and "doesn't launch" reports.
- Evidence: Microsoft Defender exclusions guidance for dev drives, the Windows Controlled Folder Access documentation, Apple notarization requirements (macOS 10.15+), and EAC/BattlEye Proton support opt-in (2021).
- Proposed change: Add `PLAT.DESK.os-security` (owner `platform-desktop`; contributors `async-io-storage`, `shader-system`, `persistence-save`, `anti-cheat-integrity`) and `PLAT.PAL.permissions` (runtime permission requests and rationale UI hooks; owner `platform-architect`, consumer AUD.DSP.voip). Name notarization and hardened runtime explicitly in BLD.REL.packaging.

### K-PLATFORM-16 · major · omission
- Target: ARCH.REQ.hardware-tiers, PLAT.PAL.cpu-topology, BLD.SYS.toolchains, ci-cd-automation, ARCH.STRUCT.build-buy
- Finding: The map has no **supported-target matrix**, meaning OS × ISA × GPU API × store × support tier (CI-gated and release-blocking vs best-effort). It also has no ADR slot for the key platform strategy choices. ARM64 Windows (Snapdragon X, ARM64EC, Prism x64 emulation for middleware without ARM64 builds), Apple silicon, ARM64 Linux servers (Graviton-class, material to server cost) and native Linux vs Proton-first each change the toolchain matrix, SIMD paths (NEON/SVE vs AVX2/AVX-512), middleware availability (build/buy input) and CI device needs. Without the matrix, "done" per platform is undefined and agents cannot tell which targets must be green.
- Evidence: Rust's platform support tiers are the canonical precedent for tiered platform support. Windows on ARM ARM64EC documentation. Middleware ARM64 availability gaps (e.g. anti-cheat and older audio middleware) blocked WoA game compatibility in 2024.
- Proposed change: Add `ARCH.REQ.platform-matrix` (owner `engine-architect`; contributors `platform-architect`, `build-system-toolchains`, `ci-cd-automation`, `certification-compliance`). It lists targets with support tier, ISA, API baseline (K-PLATFORM-4) and store. Require ADRs for "Linux: native vs Proton" and "Windows ARM64: native/ARM64EC". `BLD.CI.devices` must cover every tier-1 cell.

### K-PLATFORM-17 · minor · maturity-error
- Target: RES.IO.gpu-decompress (M), RES.PKG.compression (package-formats-vfs), async-io-storage
- Finding: Only GPU decompression (GDeflate, emerging) is represented. Fixed-function **hardware decompression** is established and ships on current consoles: the PS5 Kraken unit, the Xbox Series Velocity zlib/BCPack unit and the Switch 2 file-decompression engine. It dictates codec choice and block sizes, and is a distinct IO-backend concern. Codec selection in package-formats-vfs is not tied to the target's hardware decoder.
- Proposed change: Add `RES.IO.hw-decompress` (owner `async-io-storage`, maturity E, contributors `platform-console`, `package-formats-vfs`). Add to C-IO/C-VFS that the codec per target is constrained by the hardware decompressor available.

### K-PLATFORM-18 · minor · omission
- Target: NET.TRANS.sockets ("platform network APIs"), network-transport
- Finding: Platform networking requirements are not captured. Apple App Review requires working on IPv6-only (NAT64) networks. Mobile needs Wi-Fi/cellular handover and connection migration. Consoles have cert rules on network-loss and PSN/Xbox Live connectivity-state handling. Console platforms also have secure-socket and port requirements.
- Proposed change: Add `NET.TRANS.platform-requirements` (owner `network-transport`, contributors `platform-console`, `platform-mobile`, requirements via C-CERT): IPv6-only/NAT64, network change and migration, connectivity-state handling.

### K-PLATFORM-19 · minor · wrong-owner
- Target: PLAT.DESK.server-host (platform-desktop, contributor dedicated-server)
- Finding: Server host OS (Linux containers, ARM64 server hosts, Windows Server) is owned by the *desktop* expert. This pulls `platform-desktop` into the `dedicated-server` configuration only for this purpose, and puts container, cgroup and host-kernel expertise in the wrong skill.
- Proposed change: Move PLAT.DESK.server-host to `dedicated-server` (contributor `platform-desktop`), or add a `server-host` target (K-PLATFORM-2) with this capability owned by `dedicated-server`.

### K-PLATFORM-20 · minor · overlap
- Target: PLAT.MOB.storage ("Storage & download-size constraints", platform-mobile-portable) vs BLD.REL.on-demand / BLD.REL.packaging (packaging-release-patching) vs RES.PKG.install-layout
- Finding: Mobile download-size constraints overlap packaging ownership: store over-the-air limits, Android App Bundle plus Play Asset Delivery, iOS On-Demand Resources/Background Assets, and the initial install-size cap. Three skills can each claim "asset pack split for mobile store".
- Proposed change: Keep in PLAT.MOB.storage only the runtime storage constraints (free-space checks, OS purge of caches). Name AAB/Play Asset Delivery and iOS Background Assets explicitly under BLD.REL.on-demand, with contributor `platform-mobile`.
