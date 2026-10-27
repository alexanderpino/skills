# G1 round 2 — planted seeds (unsealed after the round)

Planted by the orchestrator in a scratchpad copy before the critics ran (PROTOCOL.md, calibration). The real framework never contained them. `check.py` was green on the seeded copy.

| Seed | Mandate | Planted defect | Found by | Own critic found it |
|---|---|---|---|---|
| S01 | K-RENDER | RND.RECON.motion-vectors (motion vector/jitter/history contract capability) owned by post-color-hdr while C-TEMPORAL is owned by reconstruction-upscaling (wrong owner) | K-RENDER-2, K-ARCH-5 | yes |
| S02 | K-SYSTEMS | Safe memory reclamation (epochs/hazard pointers) capability deleted | K-SYSTEMS-5 | yes |
| S03 | K-SIM | Continuous collision detection capability deleted | — | no |
| S04 | K-NET | Lag compensation / server rewind capability deleted (seed-map remapped to prediction) | — | no |
| S05 | K-TOOLS | Command/transaction/undo-redo capability deleted (seed-map remapped to selection) | K-TOOLS-1, K-COMPLETE-8 | yes |
| S06 | K-PLATFORM | platform-console tagged platform 'pc' instead of 'console' | K-PLATFORM-1, K-ARCH-2, K-NET-20 | yes |
| S07 | K-PERF | Cross-pool memory/IO arbitration capability deleted | K-PERF-1, K-ARCH-1, K-SYSTEMS-2 | yes |
| S08 | K-GAMEPLAY | Plural/gender message formatting (ICU MessageFormat) capability deleted | K-GAMEPLAY-6 | yes |
| S09 | K-SEC | Signing-key/devkit-credential custody capability deleted | K-SEC-5 | yes |
| S10 | K-TEST | Golden-image rendering tests capability deleted (seed-map remapped to GPU matrix) | — | no |
| S11 | K-ARCH | Overlap: RND.ARCH.instance-data (render-architect) duplicates RND.GEO.gpu-scene / C-INSTANCES (geometry-pipeline) | K-RENDER-15, K-PERF-3, K-ARCH-6, K-LEGACY-15 | yes |
| S12 | K-LEGACY | Frame pipelining capability names a fixed game thread + render thread | K-SYSTEMS-1, K-SIM-1, K-PERF-2, K-ARCH-3, K-LEGACY-1 | yes |
| S13 | K-FUTURE | Work graphs labelled established (E) | K-RENDER-3, K-SYSTEMS-11, K-PERF-4, K-FUTURE-1, K-LEGACY-6 | yes |
| S14 | K-PROD | Delta/chunk patching capability deleted (seed-map remapped to DLC) | K-COMPLETE-9 | no |
| S15 | K-COMPLETE | Runtime animation retargeting capability deleted | K-COMPLETE-1 | yes |

**Recall: 12/15 = 80%** (threshold 80%) → round 2 **counts** as a calibrated round.

Own-mandate misses (first strike; a second consecutive miss means re-brief or replacement): K-SIM (S03 continuous collision), K-NET (S04 lag compensation), K-TEST (S10 golden-image tests). K-PLATFORM, K-GAMEPLAY, K-SEC, K-COMPLETE, K-TOOLS, K-SYSTEMS, K-RENDER, K-FUTURE, K-LEGACY, K-ARCH and K-PERF found their own seed. K-PROD (S14) was found only by K-COMPLETE.

Findings that hit a seed are dispositioned `seed`. Where such a finding also raised a real, non-seeded defect (for example a missing check rule that would have caught the seed), that residual is handled as an accepted change and the disposition reads `seed+residual`.
