# G1 round 3 — planted seeds (unsealed after the round)

Planted by an **independent seed-author agent** in a fresh context (PROTOCOL round-2 amendment), sealed in `seeded/seeds.sealed.json` until all 15 critics had reported. `check.py` was green on the seeded copy.

| Seed | Mandate | Planted defect | Found by | Own critic found it |
|---|---|---|---|---|
| S01 | K-ARCH | C-PHYS contract summary now also claims character controllers (movement modes, move requests, root-motion hand-off), duplicating C-MOVE owned by character-movement (boundary overlap) | K-ARCH-6, K-SIM-3 | yes |
| S02 | K-RENDER | Post chain (bloom/DoF/motion blur/lens) stated as applied after tonemapping on display-referred output instead of scene-linear HDR before tonemap | K-RENDER-1, K-LEGACY-5 | yes |
| S03 | K-SYSTEMS | Blocking/long-running tasks run inline on work-stealing workers with no dedicated lanes or compensating threads (starvation/deadlock risk) | K-ARCH-10, K-LEGACY-3, K-PERF-2, K-SYSTEMS-1 | yes |
| S04 | K-SIM | Physics stepping is variable-timestep on the render frame delta (non-deterministic, unstable; contradicts fixed-step/rewind) | K-ARCH-8, K-SIM-1, K-LEGACY-2, K-SYSTEMS-3 | yes |
| S05 | K-NET | Delta compression against the previously sent snapshot instead of the last acknowledged baseline (breaks under packet loss) | K-LEGACY-9 | no |
| S06 | K-TOOLS | Derived-data cache keyed by source path & mtime instead of content hash / content-addressed (stale/poisoned cache, non-shareable) | K-ARCH-9, K-SEC-3, K-TOOLS-2, K-LEGACY-4, K-PERF-4 | yes |
| S07 | K-PLATFORM | Web runtime requires SharedArrayBuffer threads and assumes cross-origin isolation on every host; no-threads fallback removed | K-ARCH-11, K-SEC-14, K-FUTURE-10, K-PLATFORM-4, K-LEGACY-11, K-PERF-11, K-SYSTEMS-4 | yes |
| S08 | K-PERF | Performance budgets measured on the high-end reference PC and scaled proportionally to lower tiers instead of per tier x configuration x refresh class | K-ARCH-13, K-LEGACY-7, K-PERF-1, K-SYSTEMS-8 | yes |
| S09 | K-PROD | Staged/canary rollout replaced by simultaneous global rollout with only post-release kill switches | K-ARCH-20, K-SEC-2, K-TEST-12, K-PLATFORM-5, K-LEGACY-8, K-PROD-2 | yes |
| S10 | K-FUTURE | Relightable/dynamic Gaussian splats relabelled established (E) and moved into std3d; its radar entry deleted (while static splats remain M) | K-RENDER-7, K-FUTURE-3 | yes |
| S11 | K-COMPLETE | Cascaded shadow maps capability deleted; lite3d/mobile tiers have no directional-shadow technique (VSM/RT shadows are std3d-only) | K-RENDER-2, K-COMPLETE-1 | yes |
| S12 | K-LEGACY | Events default is a global event bus with immediate synchronous listener dispatch (legacy observer/global bus), contradicting L-pattern stance | K-ARCH-7, K-LEGACY-1, K-PERF-3, K-SYSTEMS-2 | yes |
| S13 | K-GAMEPLAY | Localization string tables keyed by English source text rather than stable IDs | K-ARCH-12, K-GAMEPLAY-1, K-LEGACY-10, K-PROD-7 | yes |
| S14 | K-TEST | Flaky tests auto-retried until green and quarantined by the owning skill; governed approval/expiry and test-integrity link removed | K-ARCH-14, K-TEST-5, K-LEGACY-6 | yes |
| S15 | K-SEC | Local save files registered as trusted-local instead of hostile-local (save-file exploit vector) | K-SEC-1, K-TEST-11, K-PLATFORM-11 | yes |

**Recall: 15/15 = 100%** (threshold 80%) → round 3 **counts** as a calibrated round.

Own-mandate: 14/15. **K-NET missed its own seed for the second consecutive round** (round 2: lag compensation; round 3: delta compression against the last-sent instead of last-acknowledged baseline, found only by K-LEGACY) → K-NET is re-briefed for round 4 (PROTOCOL.md). K-SIM and K-TEST, which missed in round 2, found their seeds this round.

Findings that hit a seed are dispositioned `seed`, or `seed+residual` when they also name a real defect that is fixed. Findings that merely mention a seeded item while raising a different defect (for example K-LEGACY-12 on detecting legacy wording) are dispositioned on their own merits.
