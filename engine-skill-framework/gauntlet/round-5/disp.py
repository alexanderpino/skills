"""Round-4 dispositions that are not plain 'accept'."""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
SEED_HITS = {}
for sid, fids in json.load(open(os.path.join(_HERE, "seed_hits.json"))).items():
    for f in fids:
        SEED_HITS[f] = sid

OVERRIDES = {
    "K-ARCH-16": ("reject", "verifier: The purposes do omit provided contracts (modding-ugc, spatial-transforms, visual-debugging-tools and others), but SKILL.md generation also lists capabilities and contracts and check.py already requires leads to own a contract, so "),
    "K-ARCH-9": ("reject", "verifier: CORE.SER.commands (C-CMD) and ED.ARCH.transactions (C-EDCMD) are distinct capabilities under a deliberate contract-owner versus implementer split and C-EDCMD and C-EDIT already require C-CMD, so the real residue is duplicated summ"),
    "K-COMPLETE-1": ("reject", "verifier: XC.SEC.data-rights already exists (owner privacy-data-protection; contributors certification-compliance, observability-telemetry, crash-diagnostics, security-engineering; 'data inventory, per-class retention, data-subject request "),
    "K-COMPLETE-2": ("reject", "verifier: No physical-media/cartridge/disc/gold-master coverage exists, so the omission is real, but it is a niche SKU variant largely covered by confidential console packaging/patch stubs on BLD.REL.packaging; minor severity is right and i"),
    "K-FUTURE-4": ("reject", "verifier: No C-RENDER2D slot exists, but the WebGPU-only stance and its measurable reversal trigger are a recorded, reasoned decision in docs/00 and docs/09. Reserving a new contract slot for a hypothetical reversal of a non-goal is specula"),
    "K-LEGACY-10": ("reject", "verifier: ANM.RT.events is only worded 'Curves, events & notifies' and nothing in the data states an immediate callback, so the defect is speculative inference from UE practice, and adding it to L19 stance_capabilities has no demonstrated c"),
    "K-NET-14": ("reject", "verifier: The unpaired configs exist, but membership means may-be-built (docs/06 C4), the finding gives no failure mode, and a mandatory pairs_with rule would over-constrain existing client-only configs, so this is process preference."),
    "K-NET-3": ("reject", "verifier: Backend services and relay operation are a recorded scope decision (docs/06 C3, network-transport non-responsibility external:backend, docs/00), and the finding brings no new evidence to reverse it."),
    "K-NET-5": ("reject", "verifier: The duplicated definition is real, but C-PHYS already carries collider history and is needs_implementer, and prediction-rollback assembles C-REWIND from C-PHYS. The proposed physics-2d-to-C-REWIND edges would run against that laye"),
    "K-NET-9": ("reject", "verifier: The NET.TRANS.web row already lists WebRTC unreliable channels and WebSocket alongside WebTransport, so a fallback exists inside the row and the claim of no fallback is wrong."),
    "K-PERF-7": ("reject", "verifier: C-BUDGET already has a single input-to-photon latency line per refresh class and netcode family, and PRF.NET.latency already lists frame-orchestration as contributor, so the claimed split accounting with no shared line is largely "),
    "K-PERF-8": ("reject", "verifier: Maturity classes describe technique maturity (PMU and vendor GPU counters are established techniques, proxy metrics use instruction counts), while host availability is a platform-access constraint; relabeling to M would require ra"),
    "K-PROD-10": ("reject", "verifier: No marketplace, partner-programme or support-tier capability exists, but these are commercial and backend-service concerns that fall under the recorded scope decision that backend services are outside engine scope (docs/06 section"),
    "K-PROD-7": ("reject", "verifier: ARCH.ORG.scope-control already owns an ordered descope list per milestone envelope and ARCH.ORG.human-capacity covers capacity and SLA, while deferring M0 skills contradicts the checked walking-skeleton closure proof, so the findi"),
    "K-PROD-8": ("reject", "verifier: C-BUDGET is a process contract whose M0 exit explicitly says 'v0' and whose later per-tier lines are additive, so it is not a genuine frozen-contract break; at most a minor wording alignment, not major."),
    "K-PROD-9": ("reject", "verifier: XC.DX.* are indeed ungated and developer-experience-docs provides no contract, but its purpose already makes the sample ladder double as integration tests through the reference games and human-capacity already covers creator-panel"),
    "K-SEC-8": ("reject", "verifier: Backup/KMS/retention of server-side data is backend service operation, which docs/06 C.3 declares out of engine scope (engine owns only the integration boundary), and XC.SEC.data-rights already carries retention and data-subject r"),
    "K-SEC-9": ("reject", "verifier: Server-side ingestion workers are backend infrastructure per docs/06 C.3, and the proposal is unsound because crash-diagnostics already validates crash-uploads and observability-telemetry validates telemetry-batches, so naming the"),
    "K-SIM-6": ("reject", "verifier: Cross-platform float determinism is already an M capability (CORE.MATH.deterministic) with a radar entry citing A4, NET.PRED.physics-lockstep is gated to backends declaring the deterministic level, and fixed-point is the stated fa"),
    "K-TEST-12": ("reject", "verifier: ML.RT.validation already names 'backend & quantization conformance with tolerance tables; model-version regression', so the claim that only runtime numeric parity is covered is not fully accurate, and the remaining gap (per-featur"),
    "K-TEST-9": ("reject", "verifier: The contracts these capabilities sit under already have independent oracle authors (C-NET/C-REP sim-validation, C-A11YRT ui-text-conformance, C-PTREF/C-RHI/C-SHADER render-validation, C-COOK functional-automation-soak), QA.RENDER."),
    "K-TOOLS-1": ("reject", "verifier: C-CMD (the diff/journal/merge command core, requires C-SER/C-REFL, property-tested by functional-automation-soak) is already drafted at M0 and C-ECS freezes at M2 not M1, so the claim is partly wrong, and the M2 'indie 2D with too"),
    "K-TOOLS-11": ("reject", "verifier: The rows are indeed untagged, but tagging gizmos, splines and the outliner away from 2D/small projects would remove needed 2D gizmos, path tools and any outliner from indie configs (C-EDVIEW has a 2D/ortho mode), so the proposal i"),
    "K-TOOLS-7": ("reject", "verifier: The shared schema is C-CMD, which C-EDCMD requires and must therefore freeze no later than C-EDCMD, so freezing C-CMD at M5 would violate the never-freeze-before-requirements rule and the proposal is unsound."),
    "K-TOOLS-9": ("reject", "verifier: online-services-liveops carries an explicit authoring note that live-ops configuration is data through C-GAMEDATA tooling (gameplay-data consumes C-VCS/C-EDCMD, CNT.VAL.submit-gate exists), remote-config changes are on the human-g"),
    "K-NET-2": ("reject", "consistent with the round-4 adjudication of K-NET-6: input-only netcode families stay separate add-ons; relay/referee servers are external"),
    "K-RENDER-5": ("partial", "path-tracing leaves lite3d closures; no target-tagging of capabilities, no dev-only check"),
    "K-SYSTEMS-6": ("partial", "three of the four requires edges added; C-CFG→C-TYPES would close a bootstrap cycle"),
    "K-ARCH-14": ("partial", "no xl tier: tiers partition workstreams, the co-hosting unit"),
    "K-ARCH-17": ("partial", "named cases reconciled; no general informs check"),
    "K-PERF-2": ("partial", "M2 sustained-state gate added; thermal-signal backend gate left to M3"),
    "K-PERF-4": ("partial", "M0/M1 lab gates added; per-platform lab gates not added"),
    "K-PLATFORM-1": ("partial", "per-platform backend-slot rows added; no needs_implementer on slot contracts"),
    "K-PLATFORM-3": ("partial", "data-class rules added; BLD.SYS.platform-sdks not split"),
    "K-PLATFORM-5": ("partial", "PLAT.SRV.gpu-host added, cloud-render-host demoted to X; no new variant or configuration"),
    "K-PLATFORM-8": ("partial", "mobile-AR contributor added; no xr-runtime platform tags"),
    "K-FUTURE-1": ("partial", "five M rows reclassified to X; no numeric shipped_titles check"),
    "K-PROD-4": ("partial", "validator-milestone rule not added"),
    "K-PROD-5": ("partial", "validators constrained by the independence rule"),
    "K-TEST-2": ("partial", "golden/stability validators re-pointed; no exercised_by/known_red fields"),
    "K-TEST-6": ("accept", "carried from round 4"),
    "K-TEST-10": ("partial", "no freeze_requires fields"),
    "K-TEST-7": ("partial", "real_backend_lane field required on boundary contracts; differential lane text only"),
}
