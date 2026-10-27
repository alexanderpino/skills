# Round 5 seed recall

| Seed | Critic | Target | Found by | Own critic found |
|---|---|---|---|---|
| S01 | K-ARCH | CORE.FRAME.channels | K-SYSTEMS-3 | no |
| S02 | K-RENDER | RND.GI.restir | K-RENDER-3, K-ARCH-19, K-FUTURE-5 | yes |
| S03 | K-SYSTEMS | CORE.JOBS.degenerate | K-SYSTEMS-1, K-ARCH-6, K-LEGACY-5 | yes |
| S04 | K-SIM | C-PHYS | K-SIM-1, K-ARCH-4, K-LEGACY-4 | yes |
| S05 | K-NET | C-SERVER | K-ARCH-18 | no |
| S06 | K-TOOLS | ED.ARCH.transactions | K-TOOLS-2, K-ARCH-3, K-LEGACY-3 | yes |
| S07 | K-PLATFORM | rhi-d3d12.platforms | K-PLATFORM-4, K-ARCH-20 | yes |
| S08 | K-PERF | PRF.METH.budgets | K-ARCH-7, K-LEGACY-8 | no |
| S09 | K-PROD | M4.exit | K-PERF-1 | no |
| S10 | K-FUTURE | RND.SHADER.neural | K-RENDER-2, K-ARCH-8 | no |
| S11 | K-COMPLETE | QA.SIM.navigation | MISSED | no |
| S12 | K-LEGACY | RND.ARCH.scene-sync | K-RENDER-1, K-ARCH-1, K-LEGACY-1 | yes |
| S13 | K-GAMEPLAY | UI.FW.architecture | K-GAMEPLAY-1, K-ARCH-2, K-LEGACY-2 | yes |
| S14 | K-TEST | QA.STRAT.flaky | K-TEST-6, K-ARCH-5, K-LEGACY-7 | yes |
| S15 | K-SEC | user-images.validating_owner | K-SEC-1 | yes |

Overall recall: 14/15 (missed: S11). Owning critic found its own seed: 9/15.

Per-critic notes:
- Owner missed own seed: K-ARCH (S01, caught by K-SYSTEMS-3), K-NET (S05, caught by K-ARCH-18 only in passing), K-PERF (S08, caught by K-ARCH/K-LEGACY), K-PROD (S09, caught by K-PERF-1), K-FUTURE (S10, caught by K-RENDER/K-ARCH), K-COMPLETE (S11, missed by all).
- K-ARCH and K-LEGACY were the broadest catchers (K-ARCH hit 11 seeds, K-LEGACY 7).
- S11 (removed QA.SIM.navigation) is an omission defect; no critic noticed the missing capability.
- S01 and S05 hits are partial: K-SYSTEMS-3 and K-ARCH-18 identify the overlap/duplication; K-ARCH-18 is one clause inside a broader finding.
