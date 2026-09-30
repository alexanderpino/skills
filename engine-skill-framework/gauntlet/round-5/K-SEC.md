# K-SEC (Security Critic), round 5

Sweep: all 76 registry inputs, every XC.SEC.*, XC.EXT.* and confidential-territory row were read. Owners, key custody, agent boundary, sensitive-paths, independence and ugc-integrity are well covered and are not re-reported.

### K-SEC-1 · major · wrong-owner
- Target: untrusted-inputs user-images, replicated-state, client-rpcs, replays, cloud-saves; RND.TEX.runtime-decode, texture-streaming-vt, ui-architect
- Finding: user-images is validated by ui-architect, but the decoder (RND.TEX.runtime-decode) is owned by texture-streaming-vt, which has no untrusted_inputs and is not a parser_owner. Image limits (dimensions, decompression bombs, ICC, animated formats, GPU upload size) cannot be enforced by a UI framework skill. Likewise replicated-state, client-rpcs, replays and cloud-saves are deserialized through serialization-schema (CORE.SER.untrusted) but list no parser owner, unlike packets and saves, so the co-located fuzz harness is not required of the deserializer.
- Evidence: libwebp CVE-2023-4863 and the stb/libpng-class decoder bugs were reached via player-supplied images; the parser must carry the harness.
- Proposed change: set user-images validating_owner to texture-streaming-vt (ui-architect as consumer/parser_owner) and add it to that skill's untrusted_inputs. Add serialization-schema as parser_owner of replicated-state, client-rpcs, replays and cloud-saves.

### K-SEC-2 · major · wrong-boundary
- Target: untrusted-inputs cloud-saves (semi-trusted-signed), GAM.SAVE.integrity, GAM.SAVE.cloud, XC.SEC.key-custody
- Finding: "semi-trusted-signed" is wrong if the signer is the client or a client-derivable key, since the local user can re-sign edited saves. GAM.SAVE.integrity says only "signing & tamper policy" and never states where the key lives or that signed progress is not an authority for online economy or ranked state.
- Evidence: Client-side HMAC keys have been extracted in every major save-editor scene; Diablo III and Destiny moved progression server-side for exactly this reason.
- Proposed change: label cloud-saves hostile-local unless the signature comes from a server-held key under XC.SEC.key-custody. Add to GAM.SAVE.integrity a rule that client-signed saves are tamper-evident only, and that any online-relevant field is server-authoritative via NET.SRV.persistence. Add anti-cheat-integrity as contributor.

### K-SEC-3 · major · omission
- Target: RND.SHADER.untrusted, RND.MEM.residency, gpu-memory-resources, ugc-graphs
- Finding: GPU-side memory safety is missing. RND.SHADER.untrusted covers only GPU-DoS limits. There is no capability for zero-initialization of freshly allocated VRAM and transient/aliased render-graph resources, enforced bounds-checked (robust) buffer and image access for untrusted shaders, or device-lost/TDR recovery after a UGC-triggered hang. Aliased memory and uninitialized allocations leak previous frame or other-process content.
- Evidence: WebGPU mandates zero-init and robust access. LeftoverLocals (2023) leaked GPU local memory across processes. Vulkan robustBufferAccess2 exists for this purpose. Render-graph aliasing (frame graph) reuses memory without clears.
- Proposed change: add RND.MEM.zero-init-robust-access (owner gpu-memory-resources; contributors shader-system, render-graph-scheduling, security-engineering). Extend ugc-graphs limits with "device-lost recovery, robust access". Add a UGC-hang device-lost scenario to the M6 sandbox gate.

### K-SEC-4 · major · omission
- Target: PLAT.PAL.cloud-render-host, untrusted-inputs, XC.SEC.hardening
- Finding: the cloud render host has a video/input back-channel and multi-tenant GPU packing, but the remote input stream, session-control messages and tenant identity are absent from the registry, so no validating owner, limits or fuzz target exist. Tenant isolation is only a side-channel row in XC.SEC.hardening.
- Evidence: cloud-gaming hosts (GeForce NOW, Xbox Cloud Gaming) treat remote input and session control as pre-auth network input with per-session isolation.
- Proposed change: add registry input "remote-play-input" (hostile-remote, validating owner platform-architect, parser_owners input-system and network-transport, limits rate/schema/session-token). Add tenant isolation (per-session process/GPU context, no shared memory) as an explicit XC.SEC.hardening obligation of the capability.

### K-SEC-5 · major · omission
- Target: BLD.SYS.third-party, untrusted-inputs third-party-source, ARCH.STRUCT.build-buy
- Finding: BLD.SYS.third-party is a single line. Dependency admission by autonomous agents is not specified: no internal mirror or registry allow-list, no lockfile and hash pinning, no human gate for adding a new dependency or maintainer change, and no review of upstream diffs on update. Agents that hallucinate package names create a squatting path.
- Evidence: package-name hallucination ("slopsquatting", 2025 studies), the xz-utils backdoor (2024) and the event-stream and dependency-confusion incidents (Birsan, 2021).
- Proposed change: extend BLD.SYS.third-party with an admission policy (mirror-only egress, hash-pinned lockfile, new-dependency and maintainer-change human gate registered in ARCH.ORG.human-gates, vendored-diff review). Contributors: ci-cd-automation, program-orchestration.

### K-SEC-6 · major · omission
- Target: CORE.MATH.random, CORE.TYPES.crypto, anti-cheat-integrity, PLAT.COMM.disclosure, NET.SRV.transactions
- Finding: no capability governs security-relevant gameplay randomness. CORE.MATH.random is counter-based and deterministic for parallel and lockstep use. Nothing states that server-authoritative loot, shuffle, matchmaking-seed or gacha outcomes must come from an unpredictable CSPRNG, that seeds are never replicated before use, or that odds are auditable.
- Evidence: seed-recovery attacks on Mersenne-Twister-class generators against online games and gacha; the PLAT.COMM.disclosure odds obligation is unenforceable without an audit log.
- Proposed change: add XC.SEC.gameplay-rng (owner anti-cheat-integrity; contributors security-runtime, math-simd-numerics, server-scaleout-persistence, determinism-replay). Rule: outcomes affecting economy or ranking use server CSPRNG with an audit record. Deterministic streams are used only where C-DET requires them, and their seeds are not disclosed early.

### K-SEC-7 · minor · omission
- Target: untrusted-inputs chat-text, server-list-entries, UI.TXT.bidi, text-fonts
- Finding: player-controlled identity strings (display names, clan tags, lobby and world names, UGC titles) are not a registered input. chat-text limits are only length/rate. Nothing mandates normalization (NFC), stripping of bidi override and zero-width controls, confusable checks, or escaping when rendered into UI, logs and filenames.
- Evidence: Unicode bidi spoofing (Trojan Source, CVE-2021-42574) and homoglyph impersonation; name-based injection bugs in game lobbies.
- Proposed change: add input "player-profile-strings" (hostile-remote, validating owner online-services-liveops, parser_owners text-fonts and ui-architect, limits length, normalization and control-character allow-list, output-context escaping).

### K-SEC-8 · minor · omission
- Target: NET.SRV.persistence, XC.SEC.data-rights, PLAT.LIVE.support-tools
- Finding: player data at rest is not covered. There is no capability for encryption at rest, backup and point-in-time-restore retention, or for propagating erasure requests through backups and analytics stores. ED.COLLAB.backup covers only development infrastructure. Support-tools "restoration" implies backups exist, but nothing owns them.
- Evidence: GDPR Art. 17 erasure and Art. 32 security of processing apply to backups.
- Proposed change: add NET.SRV.backup-retention (owner server-scaleout-persistence; contributors privacy-data-protection, security-engineering, online-services-liveops), including deletion-through-backup semantics and KMS-backed encryption, referenced from XC.SEC.data-rights.

### K-SEC-9 · minor · omission
- Target: untrusted-inputs crash-uploads, telemetry-batches, OBS.CRASH.pipeline, OBS.CRASH.symbolication
- Finding: the registry gives limits ("size", "size/rate") but the server-side ingestion, minidump processing and symbolication services parse hostile-remote input while holding symbols, builds and internal credentials. No capability requires isolating them (sandboxed workers, no source or secret access, separate from the symbol store).
- Evidence: minidump-stackwalk and Breakpad processor parser CVEs; Crashpad server ingestion is conventionally sandboxed.
- Proposed change: add to OBS.CRASH.pipeline an obligation that the processors run as sandboxed, least-privilege, ephemeral workers. Add crash-diagnostics and observability-telemetry as parser_owners and set the limits to "size/rate; sandboxed processing".
