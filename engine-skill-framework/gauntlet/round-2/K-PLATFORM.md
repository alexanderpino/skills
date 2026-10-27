# K-PLATFORM — Round 2 findings (Platform Critic, blind)

### K-PLATFORM-1 · blocker · wrong-boundary
- Target: platform-console (skills.json `platforms`), configurations xr-pc-client, rts-2d-massim-client, rts-3d-massim-client, indie-2d-tools, standard-3d-tools, aaa-open-world-online-tools
- Finding: `platform-console` is tagged `platforms: ["pc"]`. Its purpose, capabilities (PLAT.CON.*) and the C-RHI console backends it implements all run only on consoles. With this tag, `Model.in_configuration` puts the NDA console module, including its C-RHI implementation, into every PC-only configuration (xr-pc-client, both RTS clients, all tools builds). It is included in pc+console configurations only because they also list `pc`. A console-only configuration would contain no console platform module and no console RHI, and the gate would stay green because `rhi-d3d12`/`rhi-vulkan` satisfy C-RHI.
- Evidence: skills.json record `platform-console.platforms = ["pc"]`, while every sibling uses its real token (`platform-mobile` has `["mobile","xr-standalone"]`, `platform-web` has `["web"]`). NDA SDKs forbid distributing console code or headers in non-licensed builds, and PLAT.PAL.confidential-extensions exists to prevent exactly that leak. check.py cannot see the error because platform tags only filter membership.
- Proposed change: set `platform-console.platforms = ["console"]`. Add a check.py rule: a skill whose owned capabilities all sit in a `PLAT.<X>` area with a platform meaning must carry that platform token (map PLAT.CON→console, PLAT.MOB→mobile, PLAT.WEB→web, PLAT.DESK→pc). Add a self-test mutation that retags a platform skill.

### K-PLATFORM-2 · major · dependency-error
- Target: check.py configuration closure, contracts with `needs_implementer` (C-RHI), docs/00 §4
- Finding: docs/00 says "`check.py` proves that every configuration contains [an implementer] for each of its platforms". The code only checks that some member implements the contract: `not any(cid in m.skill(x)["implements"] for x in members)`. A configuration for pc+console+mobile+web passes with the D3D12 backend alone. So the scale-down proof says nothing about per-platform backends, and K-PLATFORM-1 is invisible to the gate.
- Evidence: check.py configuration-closure loop. The claim and the implementation disagree. This is exactly the class of defect the gate is meant to exclude.
- Proposed change: for each configuration platform `p` and each `needs_implementer` contract `C`, require a member with `C` in `implements` and (`platforms` is null or `p` in `platforms`), excluding platform-neutral implementers (null `platforms`) from counting for a platform-specific slot. Add a self-test mutation that removes `web` from `rhi-webgpu.platforms`. Correct docs/00 if the rule is not implemented.

### K-PLATFORM-3 · major · missing-contract
- Target: C-PAL, platform-architect, platform-desktop, platform-mobile, platform-web, platform-console, ARCH.STRUCT.platform-backends, PLAT.PAL.*
- Finding: the "registered platform backend slot" rule exists only as prose (C-PAL summary; ARCH.STRUCT.platform-backends). C-PAL has no `needs_implementer`, and every per-platform skill *consumes* C-PAL instead of implementing it. As a result, the lead `platform-architect` owns the per-OS implementation of all 24 PAL capabilities (windowing, threads, clocks, display, power, permissions, HTTP/TLS, fs-watch). The OS experts (`platform-desktop` "Windows/Linux/SteamOS/macOS integration", `platform-mobile` "iOS/Android integration") own overlapping integration territory, and nothing says who writes Win32 windowing versus who writes the PAL windowing interface. Two agents will both write that code.
- Evidence: contracts.json C-PAL (no `needs_implementer`); skills.json `consumes: ["C-PAL"]` on all four platform skills; PLAT.PAL.windowing/display/power are owned by platform-architect while PLAT.DESK.os-integration and PLAT.MOB.os are owned by the experts. C-RHI already uses the correct owner/implementer pattern, and C-PAL should follow it.
- Proposed change: mark C-PAL `needs_implementer: true`. Make platform-desktop, platform-console, platform-mobile, platform-web and a server-host implementer (K-PLATFORM-4) `implements: ["C-PAL"]`. Relabel the PLAT.PAL.* capabilities as "interface & policy" owned by platform-architect, and add per-platform "PAL implementation" capabilities to each expert. Add a `slots` list on ARCH.STRUCT.platform-backends in data (RHI, IO, audio endpoint, device input, sockets, crash, save storage, service SDK, IME/a11y bridge) with the interface owner for each. The per-platform rule from K-PLATFORM-2 then proves each configuration has a PAL backend per platform.

### K-PLATFORM-4 · major · omission
- Target: server-host platform, platform-desktop, dedicated-server, NET.SRV.host-os; configurations *-server, online-3d-bot-client
- Finding: no skill carries the `server-host` token. `platform-desktop` claims "server host OS" in its purpose but is tagged `["pc"]`, so it is excluded from all five server-host configurations. NET.SRV.host-os ("Linux, ARM64 hosts, containers") is owned by a networking skill (`dedicated-server`), and its declared contributor `platform-desktop` is not in any build that needs it. Linux server-host PAL behavior (cgroup CPU/memory quotas seen as hardware topology, SIGTERM/pre-stop drain, no display/GPU, NUMA on large instances, ARM64 Graviton/Ampere ISA dispatch, orchestrator health probes such as Agones/GameLift SDK) therefore has no platform owner in the builds that run it.
- Evidence: skills.json platform tags; the configuration list shows `server-host` only on server and bot configurations. Hosting fleets run containerized Linux, and CPU-quota-unaware thread pools are a well-known cause of oversubscription on k8s (container-aware runtimes such as the JVM's and .NET's added cgroup detection for this reason).
- Proposed change: either tag `platform-desktop.platforms = ["pc","server-host"]` and rename it "Desktop, Handheld PC & Server Host", or add an expert `platform-server-host` (platforms `["server-host"]`, targets server/headless-client) that implements C-PAL. Move NET.SRV.host-os to that owner with `dedicated-server` as contributor, and add capability `PLAT.SRV.container-topology` (cgroup-aware CPU/memory discovery feeding PLAT.PAL.cpu-topology).

### K-PLATFORM-5 · major · wrong-boundary
- Target: platform-console, PLAT.CON.rhi-backends, rhi-core, gpu-platform-architect, docs/00 §8
- Finding: console graphics backends are folded into the OS/lifecycle/cert skill `platform-console`, which contradicts the stated rule "one skill per graphics API backend" (each API has its own spec, validation and cadence). The non-responsibilities also contradict each other. `platform-console` lists "Console graphics API backend → rhi-core", `rhi-core` lists "Per-API backend code → … platform-console", and `gpu-platform-architect` lists only the four public backends. Console GPU APIs (the Sony AGC-class API, NVN-class, the Xbox D3D12 variant) are as different from each other as D3D12 is from Metal, and they need GPU-API expertise, not OS-integration expertise.
- Evidence: skills.json non_responsibilities on the three skills; PLAT.CON.rhi-backends; docs/00 §8 rows 5–6.
- Proposed change: create confidential backend skills `rhi-console-<holder>` (one per platform-holder family) under `gpu-platform-architect`, with platforms `["console"]`, `implements: ["C-RHI"]`, and access class set per K-PLATFORM-6. Move PLAT.CON.rhi-backends to them (split per holder), remove `C-RHI` from `platform-console.implements`, and fix the three non-responsibility entries.

### K-PLATFORM-6 · major · omission
- Target: platform-console, async-io-storage (RES.IO.backends "console APIs", RES.IO.hw-decompress), audio-architect (AUD.ARCH.devices), persistence-save (GAM.SAVE.platform), crash-diagnostics, text-fonts (UI.TXT.ime), PLAT.PAL.confidential-extensions, C-ORCH access classes
- Finding: NDA access is per platform holder (Sony, Microsoft and Nintendo agreements are separate, and a contractor licensed for one may not see another). The framework has one `platform-console` agent spanning every holder. Registered-slot implementations that touch confidential SDKs (console IO and decompression units, audio endpoints, save storage, crash upload, IME/system keyboard, entitlement SDKs) are owned by domain skills that have no access class. The C-ORCH ledger has "access classes", but no skill or capability declares one, so program-orchestration cannot route NDA work or keep it away from uncleared agents.
- Evidence: capabilities listed above; skills.json has no access/confidentiality field; PLAT.PAL.confidential-extensions describes the mechanism but nothing binds to it. docs/06 §"Parameters behind NDAs" admits console content cannot be filled yet, but the *structure* (who may touch it) must exist before phase 2.
- Proposed change: add `access_class` to skills (`public` | `nda:<holder>`) and a `confidential_slots` list on capabilities. Split `platform-console` into `platform-console-<holder>` experts (or a parameterized template skill instantiated per holder) under a console lead. For each slot, have the domain skill own the public interface and stub, and have the holder skill implement the confidential variant. Add a check.py rule that no `public` skill owns a capability marked `nda:*`.

### K-PLATFORM-7 · major · omission
- Target: configurations indie-2d-tools, standard-3d-tools, aaa-open-world-online-tools; model axis "platforms"
- Finding: tools configurations list only the host platform (`["pc"]`). They cannot express the platforms the tools *target*. Cooking textures and shaders to console/mobile formats, platform packaging, devkit deploy/run/debug (PLAT.CON.devkit) and store submission need platform-specific, often NDA, tool-side modules (for example console shader compilers, texture swizzlers and packagers). Today these enter tools builds only by accident, because platform-console is mis-tagged `pc` (K-PLATFORM-1). Once that is fixed, no tools configuration can contain console cook/deploy code, and nothing proves a toolchain exists for each shipping platform.
- Evidence: skills.json configurations; model.py `in_configuration` filters on a single platform list. Production engines distinguish host platform from target platform (for example UE's `TargetPlatform` modules loaded by the editor/cooker per SDK installed).
- Proposed change: add `target_platforms` to tools configurations (for example aaa-open-world-online-tools: host `["pc"]`, target `["pc","console","mobile"]`). Include platform-tagged skills whose `targets` contain `tools` when the tag matches either list. Require per-target implementers of a new tool contract `C-TARGETPLAT` (cook formats, shader backend compiler, packager, deploy/launch) from each platform skill.

### K-PLATFORM-8 · major · wrong-owner
- Target: PLAT.CON.user-model, platform-console, C-SVC, C-DEVICE, GAM.SAVE.platform, INP.DEV.hotplug
- Finding: "Platform-user identity model" is owned by the console-only skill, yet the concept is cross-platform. GDK on Windows uses the same XUser model, Steam/Epic users exist on PC, Game Center and Play Games on mobile, and local multi-profile support exists on some OSes. C-DEVICE ("device↔platform-user pairing"), save scopes (GAM.SAVE.settings device/user/cloud) and privileges all depend on a platform-user handle. When platform-console is correctly tagged, non-console configurations lose the owner of that handle type.
- Evidence: capabilities PLAT.CON.user-model, INP.DEV.hotplug (contributor platform-console), GAM.SAVE.platform (contributor platform-console); C-SVC summary lists identity tokens but no user-handle/sign-in-change model.
- Proposed change: move the platform-user model (user handle, sign-in/out and user-change events, primary-user rules, guest users) to `platform-services` as part of C-SVC, or to C-PAL as a slot. Keep a console-specific implementation capability under the console skill(s).

### K-PLATFORM-9 · major · omission
- Target: xr-runtime, rhi-metal, platform-mobile, xr-standalone configuration; PLAT.XR.openxr
- Finding: XR platform coverage assumes OpenXR on Android-class standalone headsets. Missing:
  - Apple visionOS: standalone XR on Metal plus Compositor Services, not OpenXR. `rhi-metal` is not tagged `xr-standalone`, and `platform-mobile` covers only "Android-based standalone XR".
  - Console-tethered XR (the PS VR2 class, proprietary API on a console): there is no xr+console configuration, and xr-runtime names OpenXR only.
  - Android XR, which is OpenXR but ships with Play-store and permission specifics.
  The radar cites visionOS as evidence while no owner or backend can ship it.
- Evidence: skills.json platform tags; PLAT.XR.* capability names; radar entry for XR scene understanding ("visionOS").
- Proposed change: add capability `PLAT.XR.runtime-backends` (OpenXR, visionOS Compositor Services, console XR SDK as a confidential slot) owned by xr-runtime, with a C-XRVIEW implementer slot. Tag `rhi-metal.platforms` with `xr-standalone`. Extend platform-mobile's purpose (or add visionOS to platform-desktop's Apple coverage) to cover visionOS app lifecycle. Add configuration `xr-console-client` (std3d+xr, platforms console).

### K-PLATFORM-10 · major · overlap
- Target: PLAT.PAL.device-db, PLAT.PAL.capability-tiers, RND.RHI.caps, RND.RHI.driver-policy, RND.GPU.tiers, ARCH.REQ.hardware-tiers, PRF.METH.scalability, C-SCALE
- Finding: five skills define "tiers", and two maintain deny-lists. The device DB (platform-architect) has "hardware → tier mapping, deny-lists, remote updates". RHI driver policy (rhi-core) has "minimum/known-bad drivers, deny-lists". Tier definitions appear in engine-architect (hardware tiers), performance-architect ("tier definitions & knob budgets"), platform-architect (platform capability tiers), gpu-platform-architect (GPU feature tiers) and rhi-core (GPU capability tiers). No contract states which tier key the device DB emits or who resolves a device to a scalability profile. As a result, two agents will each build a deny-list and a device→tier table.
- Evidence: capability names quoted above. Production engines keep one device-profile database (for example UE DeviceProfiles plus Android GPU family matching) whose output keys feed both RHI workarounds and scalability.
- Proposed change: make PLAT.PAL.device-db the single store of device records, including driver deny-lists and remote updates. Change RND.RHI.driver-policy to "driver policy rules evaluated against C-PAL device records" (policy only). Define the key chain in C-PAL/C-GPUTIER/C-SCALE summaries as: device record → GPU feature tier (C-GPUTIER) + platform capability tier → performance tier (performance-architect) → knob set (C-SCALE). Make ARCH.REQ.hardware-tiers the only definition of the tier *names*.

### K-PLATFORM-11 · minor · scale-down
- Target: `console` platform token, PLAT.CON.portable, configurations
- Finding: `console` lumps together high-end home consoles and portable consoles (Switch-class: ARM, mobile-class GPU, docked/handheld modes). No configuration pairs `lite3d` or `min2d`-at-3D-tier with a console target, so nothing proves the lite3d/CPU-submission tier closes on a console. The console backend and platform skills are only exercised under std3d.
- Evidence: skills.json configurations; PLAT.CON.portable and PLAT.PAL.performance-modes (docked/handheld) exist without a configuration.
- Proposed change: add configuration `lite-3d-portable-console-client` (profiles lite3d, target client, platforms console). Optionally split the token into `console` and `console-portable` so platform tags can select portable-specific modules.

### K-PLATFORM-12 · minor · wrong-boundary
- Target: platform-mobile, platform-console (targets), platform-web (targets)
- Finding: `platform-mobile` and `platform-console` list targets `headless-client` and `server`, and `platform-web` lists `tools`. No mobile/console server or web-hosted tools exist in any configuration. The tags would pull these modules into a hypothetical console server build and blur what "server-host" means.
- Evidence: skills.json targets.
- Proposed change: `platform-mobile.targets = ["client"]`, `platform-console.targets = ["client"]` (plus tools-side modules via K-PLATFORM-7), `platform-web.targets = ["client"]`.

### K-PLATFORM-13 · minor · omission
- Target: PLAT.PAL.cloud-streaming, C-PRESENT (cloud encoder presenter), platform-architect
- Finding: cloud streaming cannot be expressed as a platform (there is no token), and the radar fallback is "treat as a PC target". C-PRESENT, however, names an interposed "cloud encoder" presenter that no skill implements, and streaming-specific obligations have no owner:
  - touch-overlay control layouts (xCloud class)
  - network-latency-aware input and latency markers
  - session suspend on disconnect
  - ephemeral local storage
  - resolution changes driven by the stream
- Evidence: contracts.json C-PRESENT; radar entry "Cloud game streaming targets".
- Proposed change: either remove "cloud encoder" from C-PRESENT, consistent with the PC-target fallback, or add a capability `PLAT.PAL.cloud-streaming-integration` (touch overlays, streaming signals, storage policy) owned by platform-desktop with input-system as contributor, and list the platform-service obligations in C-CERT.

### K-PLATFORM-14 · minor · scale-down
- Target: BLD.CI.devices (profile `team-large`), BLD.CI.build-distribution, QA.CERT.prechecks
- Finding: device-farm/devkit test orchestration is gated to `team-large`. The indie-2d and lite-3d mobile configurations ship on console and mobile, which still require on-device runs of cert pre-checks, performance lanes and functional smoke tests. For a small team this means a handful of devkits or a cloud device lab. Below team-large, running tests on target devices has no owner.
- Evidence: capabilities.json BLD.CI.devices profile tag; configurations indie-2d-client and lite-3d-mobile-client list console/mobile.
- Proposed change: split into `BLD.CI.device-lanes` (untagged: run test lanes on attached devkits/phones or cloud device labs) and `BLD.CI.device-farm` (team-large: fleet scheduling, pooling).

### K-PLATFORM-15 · minor · omission
- Target: input-system (INP.ACT.remapping, INP.ACT.glyphs), input-devices-haptics
- Finding: OS- and store-level input remapping layers are not represented: Steam Input action sets (required for correct glyphs under Steam Deck Verified), console system-level button remapping, and iOS/macOS GameController remapping. The engine's action and glyph system must query or cooperate with these layers, or prompts will show the wrong glyphs and double remapping will occur. QA.CERT.programs cites Steam Deck Verified but has no runtime capability behind it.
- Evidence: capability lists for INP.ACT.*; Steam Deck Verified criteria require that glyphs match the actual controller.
- Proposed change: add `INP.ACT.platform-remap` ("integration with OS/store input remapping layers: action-set APIs, system remap queries, origin→glyph resolution") owned by input-system, with platform-desktop and platform-console as contributors.

### K-PLATFORM-16 · minor · other
- Target: radar entry "WebGPU backend & web 3D", milestone M5, platform-web
- Finding: (a) The WebGPU fallback "WebGL-class 2D only" names a backend no skill owns, and the legacy catalogue does not justify it. (b) `platform-web` and `rhi-webgpu` are placed in M5, whose configuration (aaa-open-world-online-client, platforms pc/console, profile std3d) contains neither, so no milestone proves the web configuration closes. The web target also arrives four milestones after indie-2d-client, which already lists `web`.
- Evidence: radar.json; milestones.json M5; `platform-web.profiles` excludes std3d.
- Proposed change: change the fallback to "web target limited to WebGPU-capable browsers; no WebGL backend (non-goal)", or add an owned `rhi-webgl2` entry to the legacy catalogue with a justification. Move `platform-web` and `rhi-webgpu` to M1 or a dedicated web milestone whose `configuration` is `minimal-client`, or add a web-only indie-2d configuration.
