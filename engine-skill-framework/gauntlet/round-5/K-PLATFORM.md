### K-PLATFORM-1 · major · wrong-owner
- Target: ARCH.STRUCT.platform-backends, UI.TXT.ime, UI.A11Y.screen-reader, AUD.ARCH.devices, INP.DEV.abstraction, PLAT.DESK.pal, PLAT.MOB.pal, PLAT.WEB.pal, PLAT.CON.confidential-slots
- Finding: The registered backend slots (audio endpoint, input, sockets, crash, save storage, service SDK, IME/a11y bridge) have an explicit per-platform implementer only on console (PLAT.CON.confidential-slots). On PC, mobile and web the OS-specific implementations (TSF/IBus/NSTextInputClient/UITextInput/InputConnection/DOM composition; UIA/AT-SPI/NSAccessibility/UIAccessibility/TalkBack/ARIA; WASAPI/CoreAudio/AAudio/WebAudio; evdev/GameInput/GCController/Gamepad API) sit in platform-neutral domain skills, while the PAL implementation capabilities list only "OS services, windowing, threads, clocks, IO, display, power, events". No platform-tagged skill owns them.
- Evidence: check.py only enforces platform tags for PLAT.* areas, so the gap is invisible. Production engines (Unreal per-platform IMPLEMENT modules, SDL/Unity platform layers) keep these in per-OS platform layers.
- Proposed change: add PLAT.DESK/MOB/WEB.backend-slots capabilities (input, audio endpoint, IME, a11y bridge, save storage, sockets) owned by the platform skill, with the domain skill as contributor and owner of the slot interface. Mark the slot contracts needs_implementer so per-platform closure is checked.

### K-PLATFORM-2 · major · missing-contract
- Target: C-SVC, platform-services, platform-mobile, platform-web, PLAT.SVC.pc-storefronts, PLAT.COMM.iap
- Finding: C-SVC is not needs_implementer and has no platform list. Only platform-console implements it. PC has named adapters (PLAT.SVC.pc-storefronts). Nothing names mobile store/service adapters (StoreKit, Play Billing, Game Center, Play Games, Sign in with Apple) or web-portal SDK adapters (itch, Poki, CrazyGames-class: saves, ads, achievements). Configurations such as indie-2d-client (pc, console, mobile, web) and mobile-async-client pass closure without any mobile or web C-SVC backend. PLAT.WEB.audience-share already assumes portal SDKs.
- Evidence: Real mobile and web ship paths depend on these adapters; no closure proves them.
- Proposed change: set C-SVC needs_implementer with per-platform backends. Add PLAT.MOB.svc-stores (implemented by platform-mobile) and PLAT.WEB.svc-portals (platform-web), or a per-store backend variant of platform-services. Add a null/emulator implementer per platform so closure proves the slot.

### K-PLATFORM-3 · major · wrong-boundary
- Target: PLAT.PAL.confidential-extensions, BLD.SYS.platform-sdks, BLD.SYS.toolchains, RND.SHADER.toolchain, BLD.REL.archival, ARCH.REQ.hardware-tiers, PLAT.PAL.device-db, C-BUDGET, OBS.CRASH.symbolication, QA.CERT.platform, QA.CERT.prechecks, PLAT.CON.submission
- Finding: NDA handling covers console code and CI results only (the CONFIDENTIAL regex matches only "confidential" and "console API/SDK"). Confidential data and process territory is owned by non-NDA skills. This includes console SDK versions and cert-mandated minimum dates (BLD.SYS.platform-sdks), console compiler and toolchain matrix, tier records and per-tier budgets with console memory reservations, device-db console SKU records, DDC/cooked console derived data, symbols and dumps, and perf captures. QA.CERT.prechecks (non-NDA) also overlaps PLAT.CON.submission "pre-submission checkers".
- Evidence: Console memory reservations, SDK versions and TRC text are NDA-covered; the shared register, budget file and DDC are readable by every agent.
- Proposed change: add data-class rules to PLAT.PAL.confidential-extensions: per-holder sealed partitions for tier/budget numbers, DDC, symbols and captures, with a public envelope and sanitized summaries. Split BLD.SYS.platform-sdks into a public part and PLAT.CON.sdk-toolchain (platform-console, NDA). Make QA.CERT.prechecks consume PLAT.CON.submission for holder rules and own only the public and non-console checks. Extend the regex or add a checker for these classes.

### K-PLATFORM-4 · major · other
- Target: skills.json platform-desktop, platform-mobile, platform-web, platform-server-host, platform-console, xr-runtime, rhi-d3d12; check.py variant closure
- Finding: Only RHI backends declare variants. Every PAL/C-TARGETPLAT implementer has variants None, and the closure test treats "variants is None" as satisfying every variant, so PAL closure for win-arm64, macos, ios, horizon-os, pico-os, visionos and the webkit/gecko variants is vacuous. platform-desktop covers four unrelated OS lineages, and the Apple family is split across platform-desktop (macOS) and platform-mobile (iOS/visionOS) although rhi-metal spans all three. rhi-d3d12 is tagged platforms ["pc","mobile"] with no mobile variant. Console classes are never bound to any skill variant.
- Evidence: check.py lines 273-278 (null variants = wildcard).
- Proposed change: give every PAL/C-TARGETPLAT implementer explicit variants and make omission an error for skills of a multi-variant platform. Split or instance platform-desktop (Windows, Linux/SteamOS, Apple-desktop) and consider an apple-platform skill. Remove "mobile" from rhi-d3d12. Bind console variants to platform-console and rhi-console instances.

### K-PLATFORM-5 · major · omission
- Target: PLAT.PAL.cloud-render-host, platform-server-host, rhi-vulkan variants, configurations
- Finding: The cloud render host (headless GPU render, HW encode, multi-tenant GPU packing) is an implementation capability owned by the lead platform-architect. platform-server-host is defined as "no display or GPU". rhi-vulkan has no server-host variant. No configuration or milestone exercises it. RND.RHI.software-device covers CI only. This M capability is unclosed and unproven.
- Evidence: Unreal Pixel Streaming and Unity Render Streaming both need a GPU Linux/Windows host with low-latency NVENC/AMF; xCloud, Luna and GeForce NOW run per-tenant GPU packing.
- Proposed change: add the variant server-host:linux-x64-gpu (and a Windows GPU host if required), tag rhi-vulkan for it, and add PLAT.SRV.gpu-host (owner platform-server-host). Move cloud-render-host implementation there, leaving policy with platform-architect. Add a configuration such as cloud-render-host-server claimed at a milestone, or demote to X until closed.

### K-PLATFORM-6 · minor · scale-down
- Target: platform_variants (pc, server-host), NET.SRV.community-hosting, PLAT.DESK.os-integration, PLAT.DESK.os-security
- Finding: The pc variants are win-x64, win-arm64, linux-steamos, macos, so generic Linux desktop (Wayland/X11, proprietary drivers, Flatpak) has no variant. Native-Linux versus Windows-build-under-Proton is not a decided or owned strategy, though Steam Deck Verified is tracked. server-host is Linux-only, but NET.SRV.community-hosting (a redistributable server build) is normally shipped as a Windows binary.
- Evidence: Valheim, Palworld and ARK ship Windows community servers; the Steam Deck ecosystem is Proton-first.
- Proposed change: add a PLAT.DESK.compat-layers capability (Proton/Wine validation ADR and CI lane), a pc:linux-desktop variant or an explicit non-goal, and a server-host:win-x64 variant or an explicit radar non-goal for community hosting.

### K-PLATFORM-7 · minor · other
- Target: milestones M2, M7, QA.CERT.platform, PLAT.CON.submission, PLAT.CON.packaging
- Finding: M2 claims console shipping with only a "TRC/store-review dry run". The first real holder submission is at M7, after suspend, user-model and save assumptions are frozen across M3-M6. Real holder feedback then arrives after everything depends on the assumptions.
- Evidence: Console cert failures cluster in lifecycle, user-change and save handling (the PLAT.CON.suspend, PLAT.SVC.user-model areas).
- Proposed change: require an actual holder pre-submission or partner review on a console configuration at M3 or M4, gated by ARCH.ORG.external-dependencies start-by dates, and keep M7 as the final pass.

### K-PLATFORM-8 · minor · wrong-boundary
- Target: xr-runtime (no platforms tag), PLAT.XR area, PLAT.XR.mobile-ar, PLAT.XR.runtime-backends
- Finding: xr-runtime has no platform tags, and PLAT.XR is not in PLATFORM_AREAS. Per-XR-OS specifics (Horizon OS, PICO, Android XR, visionOS runtimes, SteamVR/WMR on PC) are unvalidated by the platform check. PLAT.XR.mobile-ar (ARKit/ARCore) lives outside platform-mobile.
- Evidence: OpenXR runtime and vendor extension sets differ per OS (the framework already declares rhi variants for them).
- Proposed change: tag xr-runtime platforms ["pc","xr-standalone","mobile","console"] with variants. Add PLAT.XR to the platform-area check, or place mobile-AR backends under platform-mobile as contributor.
