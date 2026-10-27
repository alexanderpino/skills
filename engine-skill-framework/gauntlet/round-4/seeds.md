# Seed recall, round 4

| Seed | Critic | Target | Found by | Own critic found |
|---|---|---|---|---|
| S01 | K-ARCH | C-PRESENT | MISSED | no |
| S02 | K-RENDER | RND.PT.realtime | K-RENDER-1 | yes |
| S03 | K-SYSTEMS | PLAT.PAL.cpu-topology | MISSED | no |
| S04 | K-SIM | PHY.FLUID.gpu | K-SIM-9 | yes |
| S05 | K-NET | NET.TRANS.crypto | K-NET-4 | yes |
| S06 | K-TOOLS | ED.COLLAB.binaries | K-TOOLS-11 | yes |
| S07 | K-PLATFORM | rhi-vulkan | MISSED | no |
| S08 | K-PERF | PRF.METH.asymptotics | MISSED | no |
| S09 | K-PROD | M4 gate BLD.REL.rollback | MISSED | no |
| S10 | K-FUTURE | C-RHI | MISSED | no |
| S11 | K-COMPLETE | UI.A11Y.motion | K-GAMEPLAY-2 | no |
| S12 | K-LEGACY | CORE.FRAME.sim-schedule | K-ARCH-10, K-SIM-8, K-LEGACY-1 | yes |
| S13 | K-GAMEPLAY | AUD.CONTENT.dialogue | K-GAMEPLAY-1 | yes |
| S14 | K-TEST | M3 gate QA.RENDER.reference-validation | MISSED | no |
| S15 | K-SEC | chat-text | MISSED | no |

Overall recall: 7/15 (S02, S04, S05, S06, S11, S12, S13).

Missed: S01 (K-ARCH), S03 (K-SYSTEMS), S07 (K-PLATFORM), S08 (K-PERF), S09 (K-PROD), S10 (K-FUTURE), S14 (K-TEST), S15 (K-SEC). In every miss the owning critic also missed its own seed.

Per-critic notes:
- Own critic caught its seed: K-RENDER (S02), K-SIM (S04), K-NET (S05), K-TOOLS (S06), K-LEGACY (S12), K-GAMEPLAY (S13). That is 6 of 15 owners finding their own seed.
- K-COMPLETE's seed S11 (removed UI.A11Y.motion) was caught only by K-GAMEPLAY-2, not by K-COMPLETE itself.
- S12 was the most widely found (K-ARCH-10, K-SIM-8, K-LEGACY-1).
- Near misses judged not the same defect: K-PLATFORM-9 (rhi-vulkan headless, not the pc:macos tag, S07); K-PERF-3 (asymptotics gating circularity, not dropped replicated/connection dimension, S08); K-TEST-2 (generic circular validators, no mention of BLD.REL.rollback/soak or reference-validation/compat, S09/S14).
- Misses cluster on cross-file contract wording (S01, S10), platform tags (S07), gate validator swaps (S09, S14), and text-level edits to capability/registry rows (S03, S08, S15).
