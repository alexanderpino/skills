### K-PLATFORM-1 · major · omission
- Target: C-TARGETPLAT, platform-architect, platform-desktop/console/mobile/web/server-host, PLAT.CON.devkit, PLAT.PAL.devlink
- Finding: C-TARGETPLAT (cook format variants, shader backend hook, packager, deploy/launch/debug) is a needs_implementer contract, but no capability names its content. The only related rows are PLAT.CON.devkit and PLAT.PAL.devlink. No row covers Android/iOS device deploy and debug, web dev-server and hosting, or per-platform cook-format selection (texture format, endianness, alignment, shader targets). Console shader offline compilers appear nowhere (RND.SHADER.toolchain lists DXC, Slang, SPIR-V and Metal only).
- Evidence: platform-desktop, -mobile, -web and -server-host list C-TARGETPLAT in implements but own no tool-side capability, so the "tools closure per target_platform" proof is satisfied by an empty implementation. Unreal's platform extension modules (UBT platform, cooker platform, deploy) and Unity's platform build targets are first-class, separate work items.
- Proposed change: add PLAT.PAL.target-tools (E, platform-architect, contract semantics) and per-platform rows PLAT.DESK/MOB/WEB/SRV.target-tools and PLAT.CON.target-tools (cook variants, shader-target hook, packager hook, deploy/run/debug). Add console shader-compiler ownership under PLAT.CON with rhi-console as contributor.

### K-PLATFORM-2 · major · wrong-boundary
- Target: platform-services, PLAT.SVC.identity/achievements/entitlements/privileges/social/leaderboards/capture/age-region, C-SVC, PLAT.CON.confidential-slots
- Finding: doc 00 says platform-services is "NDA SDKs plus certification", yet it has no access class and no platform tag. Console first-party SDK code (trophies and achievements, privileges and parental controls, entitlement checks, presence, activities) is implemented inside a non-NDA skill. platform-console implements only the user-model slot of C-SVC. check.py confines NDA skills to platform-console and rhi-console only, so this leak is invisible.
- Evidence: console platform-holder NDAs forbid exposing SDK material to non-licensed parties. Agents are staffed per skill, so one platform-services agent would need every holder's documentation.
- Proposed change: split the console-specific PLAT.SVC implementations into holder-partitioned rows (PLAT.CON.svc-*, access nda:per-platform-holder, owner platform-console) behind the public C-SVC interface. Keep platform-services as owner of the interface, PC/mobile stores and the emulator. Add platform-console to the C-SVC implementers with full scope.

### K-PLATFORM-3 · major · wrong-boundary
- Target: BLD.REL.packaging, BLD.REL.submission, BLD.REL.patching, BLD.REL.on-demand, BLD.CI.device-lanes, BLD.CI.build-distribution, QA.CERT.prechecks, PLAT.CON.confidential-slots
- Finding: console packaging and signing tools, submission validators, mandated patch and DLC formats and size rules, devkit CI lanes and pre-submission checkers are NDA material. They are owned by packaging-release-patching, ci-cd-automation and certification-compliance, none of which carry an access class. PLAT.CON.confidential-slots enumerates runtime slots only (IO, audio, save, crash, keyboard, entitlements, pad, sockets, XR) and has no packaging, submission, patching or devkit-CI slot. C-CERT already has a holder-partition mechanism, but only for requirement text.
- Evidence: console packaging (package generators and signing), submission validation tools and console patch constraints (chunking and intelligent-delivery-class rules) ship only in licensed SDKs. The same reasoning as K-PLATFORM-2 applies.
- Proposed change: add confidential slots PLAT.CON.packaging, PLAT.CON.submission, PLAT.CON.patch-format and PLAT.CON.ci-lane (owner platform-console, with packaging-release-patching and ci-cd-automation as contributors), and add the tool-side confidential-slot sentence to BLD.REL.packaging and BLD.REL.submission. Consider a check that any capability contributed to by an nda skill has a public-stub statement.

### K-PLATFORM-4 · major · scale-down
- Target: platform_variants.xr-standalone, xr-standalone-client, all tools configurations' target_platforms, xr-runtime, PLAT.XR.*
- Finding: (a) no tools configuration lists xr-standalone in target_platforms, so cook, deploy and preview for standalone XR are never proven closed. (b) xr-standalone variants are android-xr and visionos only. The dominant standalone platforms (Meta Horizon OS/Quest, and PICO) are absent. Their differences are entitlements and platform SDK (identity, IAP, cert), OpenXR vendor extensions, and store review.
- Evidence: Quest is an Android-derived OS with its own store, Platform SDK and mandatory technical requirements, all different from Android XR. QA.CERT.programs names Steam Deck Verified and store review but no headset store program. The doc mentions Quest only as content.
- Proposed change: add horizon-os and pico-os variants (or a deliberate non-goal in radar with a revisit trigger). Add an xr-standalone-tools configuration (profiles lite3d+xr, target tools, target_platforms [xr-standalone]) claimed in M5. Add Horizon/PICO store programs to QA.CERT.programs.

### K-PLATFORM-5 · major · scale-down
- Target: configurations lite-3d-mobile-client, lite-3d-mobile-online-client, lite-3d-portable-console-client; profile lite3d; openworld; PLAT.WEB.webgpu-target
- Finding: (a) no configuration combines lite3d with openworld, so streaming, world partition and memory arbitration on mobile (iOS/Android process memory kill limits) or portable console are never proven closed. (b) PLAT.WEB.webgpu-target ("WebGPU-class 3D", M) and rhi-webgpu are exercised only by 2D web configurations (no lite3d@web).
- Evidence: mobile open-world action games and portable-console open-world titles are among the highest-grossing and most-shipped 3D genres, and are the hardest memory-budget case. The gap analysis A9 lists mobile GPU-driven rendering as thin evidence but no configuration tests it.
- Proposed change: add lite-3d-mobile-openworld-online-client (lite3d+openworld+online, mobile), lite-3d-portable-openworld-client (lite3d+openworld, console) and lite-3d-web-client (lite3d, web). Claim them in M4/M5.

### K-PLATFORM-6 · major · omission
- Target: PLAT.SVC.*, QA.CERT.store-policy, platform_variants.pc, BLD.REL.packaging, ARCH.REQ.platform-matrix
- Finding: the platform matrix promises "OS × ISA × API × store", but there is no store axis in platform_variants, and no capability owns PC storefront SDK adapters (Steamworks, Epic Online Services, GOG Galaxy, Microsoft Store/GDK-PC), per-store build variants and depots, or Steam Input and overlay rules. platform-services is defined as "first-party" only. Steam appears only as a transport and Deck-Verified mention.
- Evidence: most indie and PC AAA titles ship multi-store SKUs with differing identity, entitlement, achievement, overlay, packaging (Steam depots, MSIX, Epic BuildPatchTool) and rating rules. The Windows/Linux-native store layer is the largest PC integration surface.
- Proposed change: add PLAT.SVC.pc-storefronts (E, platform-services, contributors platform-desktop, packaging-release-patching) covering the adapter set behind C-SVC. Add BLD.REL.store-variants. Add a store field to configurations or platform_variants.

### K-PLATFORM-7 · minor · other
- Target: platform_variants, ARCH.REQ.platform-matrix, rhi-console, platform-console
- Finding: platform_variants defines variants for pc, mobile, xr-standalone and server-host only. Console and web have none, so the generated matrix cannot express holder families (with their differing GPU APIs, RT and decompression hardware, and portable versus fixed-console class) or browser engines (WebGPU support differs by browser and OS).
- Evidence: the design already says "instances: one agent per platform-holder family", but nothing in data enumerates the families.
- Proposed change: add console holder family variants (anonymized ids are acceptable) and web browser variants (chromium, webkit, gecko) to platform_variants, and reference them in rhi-console and platform-web variants.

### K-PLATFORM-8 · minor · wrong-owner
- Target: UI.A11Y.screen-reader, UI.TXT.ime, ARCH.STRUCT.platform-backends, platform-desktop, platform-mobile, platform-web
- Finding: the backend-slot registry names an "IME/a11y bridge". Only the console version has a named owner (PLAT.CON.confidential-slots). For desktop, mobile and web the OS accessibility bridges (UIA, NSAccessibility, AT-SPI, UIAccessibility/TalkBack, and on web the ARIA/DOM shadow tree that canvas content requires) sit in accessibility and text-fonts with platform-architect as a mere contributor. The platform implementers are not on the row.
- Evidence: each bridge is a distinct OS API with its own lifecycle and threading rules. Web canvas apps are inaccessible without an explicit DOM mirror. The EAA and CVAA obligations tracked in QA.CERT.a11y-law depend on these bridges.
- Proposed change: add PLAT.DESK/MOB/WEB.a11y-ime-bridge rows (owner the platform skill, contributors accessibility and text-fonts), or state in UI.A11Y.screen-reader that accessibility writes all non-console OS bridges.

### K-PLATFORM-9 · minor · omission
- Target: platform-server-host, PLAT.SRV.pal, headless-client configurations, render-validation
- Finding: platform-server-host is defined as "no display or GPU". A headless GPU host (Linux GPU nodes without a display or swapchain, running offscreen render, GPU bake or texture encode, GPU cook, path-traced reference validation and cloud rendering) has no platform description. rhi-vulkan's platforms exclude server-host.
- Evidence: QA.RENDER.reference-validation, QA.RENDER.matrix, the cloud cook and device-farm cost ledger, and PLAT.PAL.cloud-hybrid all imply GPU compute without a display.
- Proposed change: add PLAT.SRV.headless-gpu (offscreen/headless surfaces, container GPU passthrough, driver pinning) and allow rhi-vulkan (and the D3D12 variant, if applicable) to declare server-host with a headless-GPU feature flag.

### K-PLATFORM-10 · minor · maturity-error
- Target: ML.RT.npu, ML.RT.os-models, C-ML
- Finding: ML.RT.npu (NPU backends via platform ML APIs) is marked X. Shipped platform NPU paths (Core ML and Neural Engine, Windows ML/DirectML on Copilot+ PCs, Android NNAPI successors) are in production for OS-level features. Meanwhile ML.RT.os-models is M. The row also has no platform implementer slot, so per-OS ML accelerator backends have no platform owner.
- Evidence: platform vendors ship these APIs. The uncertainty concerns game-loop scheduling, not API availability.
- Proposed change: split into ML.RT.npu-backends (M, with platform-desktop and platform-mobile as contributors) and keep NPU-in-frame scheduling as X. Add the PAL accelerator-discovery capability to PLAT.PAL.capability-tiers.
