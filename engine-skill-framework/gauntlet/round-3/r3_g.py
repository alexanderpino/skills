"""Round-3 revision, part G: test, oracle and security findings
(K-TEST-1..4,6..10,13..17; K-SEC-4,5,7,9,10,11,13,16,17)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r3_d import _add, _append, _input, _radar, _unt  # noqa: E402
from r3_f import _cap  # noqa: E402

ORACLE_REF = {
    "C-PAL": "platform conformance suites per OS; syscall-behaviour differential runs",
    "C-BASE": "compiler/ABI conformance suites; static-assert corpora",
    "C-ERR": "error-model conformance scenarios; sanitizer corpora",
    "C-MOD": "dependency-graph reference cases; dlopen/loader edge cases per OS",
    "C-CFG": "layered-config golden cases; schema fuzz corpora",
    "C-MATH": "CORE-MATH / IEEE-754 reference vectors; arbitrary-precision differential runs",
    "C-MEM": "allocator stress and fragmentation corpora; ASan/Valgrind-class runs",
    "C-TYPES": "SMHasher and known-answer hash vectors; container model-based tests",
    "C-SYNC": "herd7/litmus tests for ARM64 and x86; model checking (loom/CDSChecker class); linearizability checkers",
    "C-TASK": "task-graph model checking; starvation/QoS scenario corpus; litmus lanes",
    "C-INSTR": "trace-format conformance corpus (Perfetto/Chrome trace importers)",
    "C-CRASH": "minidump/symbolication corpora per platform",
    "C-DET": "cross-platform golden state-hash traces",
    "C-PLUGIN": "malformed-plugin corpora; ABI conformance kits",
    "C-SIGN": "Wycheproof, ACVP and TUF vectors",
    "C-LIFETIME": "leak/lifetime torture corpora",
    "C-SCALE": "control-loop reference step-response cases",
    "C-TESTHOST": "host-conformance scenarios shipped with the runner",
    "C-FRAME": "frame-graph reference schedules; phase-violation corpus",
    "C-ID": "collision and generation-wrap corpora",
    "C-ECS": "ECS model-based tests against a naive reference implementation",
    "C-REFL": "reflection round-trip corpora against generated metadata",
    "C-SER": "malformed and versioned-blob corpora; protobuf/flatbuffers-class conformance suites",
    "C-IO": "fio-class workloads and per-platform IO conformance suites",
    "C-VFS": "path-normalisation and mount-ordering corpora",
    "C-ASSET": "asset-database consistency reference cases",
    "C-RES": "load-order and cancellation scenario corpora",
    "C-RELOAD": "hot-reload state-preservation scenario corpora",
    "C-SPATIAL": "analytic transform and large-world precision reference cases",
    "C-RHI": "Vulkan CTS, D3D12 conformance/WARP and Metal validation suites",
    "C-GPUMEM": "API validation layers; aliasing and residency reference cases",
    "C-GPUTIER": "tier capability tables from vendor conformance runs",
    "C-ML": "parity against a reference framework (ONNX Runtime/PyTorch) with tolerance tables",
    "C-IPC": "framing/TOCTOU fuzz corpora; transport conformance cases",
    "C-FLOW": "channel ordering and back-pressure reference cases",
    "C-PRESENT": "present-timeline captures with reference pacing metrics",
    "C-SNAPSHOT": "snapshot/restore round-trip and hash-equality corpora",
    "C-VIEW": "view-composition reference cases",
    "C-SIGNIF": "tier-transition scenario corpora",
    "C-DEVICE": "device-report corpora from real controllers",
    "C-NETLINK": "netem-class link-condition scenarios; wire-format corpora",
    "C-GOVERN": "closed-loop step-load and oscillation reference cases",
    "C-RTAS": "reference ray-query scenes with analytic hit results",
    "C-CMD": "command apply/invert/merge property tests",
}
FALLBACK = "analytic or differential oracle declared in the conformance suite"


def apply(ed):
    # ---------------------------------------------------------------- TEST-3/10/15/16 (C-TEST wording)
    t = "K-TEST-3 K-TEST-10 K-TEST-15"
    c = ed.contract("C-TEST")
    ed.contract_set("C-TEST", summary=c["summary"].replace(
        "conformance suites owned by contract owners with consumer-driven additions; a provider change merges only "
        "when the contract's conformance suite, including consumer-contributed cases, passes.",
        "conformance suites authored by the contract's oracle_author (the contract owner owns the specification text; "
        "consumers add cases by change request; implementers maintain only harness hooks); fuzz evidence is per-target "
        "coverage and reachability of the registered parser functions plus plateau evidence, harnesses are co-signed "
        "by robustness-fuzzing and fall under oracle change control; a provider change merges only when the "
        "contract's conformance suite, including consumer-contributed cases, passes."),
        evidence_bundle=["unit+acceptance results", "mutation score", "coverage",
                         "fuzz coverage/reachability of registered parser functions and plateau evidence",
                         "determinism lanes", "perf gate results", "validation-layer/sanitizer runs",
                         "holdout results", "test-integrity diff", "baseline/golden/tolerance change log",
                         "test-double conformance", "flake and quarantine events", "provenance attestation",
                         "compat-corpus results"], tags=t)
    for cid in ("RND.RHI.conformance", "ML.RT.validation", "RND.MAT.validation"):
        try:
            _, row = ed._find_cap(cid)
            ed.cap_set(cid, name=row[1].rstrip(".") + " (hooks only; suite authorship belongs to the contract's oracle_author)",
                       tags=t)
        except KeyError:
            pass
    ed.cap_set("QA.ROBUST.fuzzing", name="Fuzzing of every registered untrusted input (see fuzz_targets): per-target "
               "coverage and reachability thresholds, plateau evidence, structure-aware grammars; harnesses co-signed",
               tags=t)
    t = "K-TEST-16"
    _, row = ed._find_cap("ARCH.ORG.critic-calibration")
    ed.cap_set("ARCH.ORG.critic-calibration", name=row[1].rstrip(".") + "; a below-threshold critic blocks the stages "
               "in its scope (fail closed) until a recalibrated or replacement critic passes its canaries, with interim "
               "sign-off recorded under ARCH.ORG.human-gates", tags=t)

    # ---------------------------------------------------------------- TEST-4 oracle references
    t = "K-TEST-4"
    n = 0
    for c in ed.doc["contract"]["contracts"]:
        if c["layer"] in (0, 1, 2):
            c["oracle_reference"] = [ORACLE_REF.get(c["id"], FALLBACK)]
            n += 1
    ed.note(t, f"oracle_reference (external corpora) on {n} layer 0–2 contracts; check.py requires it; quality skills "
               "co-author oracles for crypto (security-engineering), lock-free/task (robustness-fuzzing) and ML parity")

    # ---------------------------------------------------------------- TEST-2 / SEC-5 independence
    t = "K-TEST-2 K-SEC-5"
    ed.doc["cross"]["independence"] += [
        ["security-engineering", "security-runtime", "reviewer vs implementer of crypto and trust-root code"],
        ["robustness-fuzzing", "owning-skill", "fuzz-harness co-signer vs parser owner"]]
    ed.note(t, "independence: per-contract oracle-author vs implementer pairs are machine-checked by workstream (check.py "
               "oracle rules); explicit pairs added for security-runtime and fuzz co-signing")

    # ---------------------------------------------------------------- TEST-6 sealed suites
    t = "K-TEST-6"
    _cap(ed, "BLD.CI.sealed-suites", "Sealed suites: holdouts, gate-time seeds and expected outputs readable only by oracle "
         "authors and CI runners (access class sealed:oracle); execution only inside CI, results reported as "
         "pass/fail plus failure category", "ci-cd-automation", contrib=["test-architect"], tags=t)
    ed.note(t, "access class sealed:oracle is a phase-2 SKILL.md obligation carried by BLD.CI.sealed-suites (partial)")

    # ---------------------------------------------------------------- TEST-7 / SEC-9 gates: r3_z
    ed.note("K-TEST-7 K-SEC-9", "M0 gates: test-integrity, holdout, mutation-gate, gate-canaries, agent-boundary, "
            "supply-chain, secrets, key-custody; M1: golden, stability-suite; M2: soak, data-rights, childrens-data, "
            "vuln-response; M7: release-criteria, compat-corpus (r3_z)")

    # ---------------------------------------------------------------- TEST-8
    t = "K-TEST-8"
    _cap(ed, "BLD.CI.merge-queue", "Serializing, batching and bisecting merge queue", "ci-cd-automation",
         contrib=["test-architect"], tags=t)
    _cap(ed, "BLD.CI.test-selection", "Test impact analysis and selection, with a periodic full run whose misses are "
         "measured", "ci-cd-automation", contrib=["test-architect"], tags=t)
    _cap(ed, "QA.STRAT.selection-policy", "Lanes that can never be skipped (holdouts, conformance, determinism) and "
         "selection-miss budgets", "test-architect", contrib=["ci-cd-automation"], tags=t)

    # ---------------------------------------------------------------- TEST-9
    t = "K-TEST-9"
    _cap(ed, "QA.ROBUST.distributed-faults", "Distributed-systems faults: partitions, process kills, clock skew, dependency "
         "outages, consistency and idempotency checking of transactions and entity migration", "robustness-fuzzing",
         contrib=["server-scaleout-persistence", "online-services-liveops", "dedicated-server"], tags=t)
    _cap(ed, "QA.SIM.server-dst", "Deterministic simulation testing of server clusters (single-process multi-node with "
         "fault schedules)", "simulation-validation", contrib=["server-scaleout-persistence"], tags=t)
    for cid in ("C-SHARD", "C-SRVDATA"):
        ed.contract_set(cid, boundary=True, test_double={"kind": "in-process multi-node simulator with fault injection",
                                                        "owner": "server-scaleout-persistence"}, tags=t)

    # ---------------------------------------------------------------- TEST-13
    t = "K-TEST-13"
    _cap(ed, "QA.RENDER.final-frame", "Final present capture including UI, text and HDR output (pixel-exact mode for "
         "pixel art, perceptual mode otherwise)", "render-validation",
         contrib=["render-2d-vector", "text-fonts", "post-color-hdr"], tags=t)
    ed.use("render-validation", "C-DRAW2D?", "C-TEXT?", "C-PRESENT", tags=t)

    # ---------------------------------------------------------------- TEST-14 / SEC-7 agent inputs
    t = "K-TEST-14 K-SEC-7"
    for iid, owner, parsers, limits in (
            ("triage-artifacts", "program-orchestration", ["ci-cd-automation", "crash-diagnostics"],
             "quarantined as data; triage agents may not change baselines or quarantine tests"),
            ("player-feedback", "crash-diagnostics", ["engine-product-management"],
             "quarantined as data; no instruction authority"),
            ("inter-agent-messages", "program-orchestration", [],
             "provenance-tagged; no instruction authority; findings and commit messages are data")):
        ed.doc["untrusted"]["inputs"].append({"id": iid, "validating_owner": owner, "parser_owners": parsers,
                                              "trust": "agent-input", "mode": "redteam", "limits": limits})
        for sid in [owner] + parsers:
            _unt(ed, sid, iid)
    ed.cap_set("XC.SEC.agent-redteam", add_contrib=["ci-cd-automation", "crash-diagnostics"], tags=t)
    ed.note(t, "agent-to-agent propagation is covered by the inter-agent-messages red-team entry")

    # ---------------------------------------------------------------- TEST-17
    t = "K-TEST-17"
    ed.cap_set("QA.AGENT.holdout", mat="M", tags=t)
    ed.cap_set("QA.AGENT.oracle-change-control", mat="M", tags=t)
    ed.cap_set("QA.AGENT.gate-canaries", mat="M", tags=t)
    for e in ed.doc["radar"]["entries"]:
        if e["tech"].startswith("Validation of autonomous-agent development"):
            e["capabilities"] = sorted(set(e["capabilities"]) | {"QA.AGENT.holdout", "QA.AGENT.oracle-change-control",
                                                                 "QA.AGENT.mutation-gate", "QA.AGENT.gate-canaries"})

    # ---------------------------------------------------------------- SEC
    t = "K-SEC-10"
    _cap(ed, "BLD.CI.hardening", "Hermetic, isolated, ephemeral runners; separation of untrusted agent pre-merge jobs "
         "from privileged release jobs; OIDC workload identity instead of static credentials", "ci-cd-automation",
         contrib=["security-engineering"], tags=t)
    _cap(ed, "BLD.SYS.provenance", "Build provenance (SLSA/in-toto attestations) and hermetic builds, verified at "
         "packaging", "build-system-toolchains", contrib=["security-engineering", "packaging-release-patching"], tags=t)
    _cap(ed, "NET.SRV.secrets-delivery", "Runtime secret injection for server hosts (no secrets in shipped artifacts)",
         "dedicated-server", contrib=["security-engineering"], tags=t)
    ed.doc["legacy"]["patterns"].append(
        {"id": "L74", "pattern": "Long-lived static CI/cloud credentials", "detection": "keys in CI variables or images",
         "default_stance": "OIDC workload identity, short-lived tokens, ephemeral runners",
         "justification_owner": "ci-cd-automation", "stance_capabilities": ["BLD.CI.hardening"],
         "contradiction_terms": [r"static (?:ci|cloud) credentials"]})

    t = "K-SEC-11"
    ed.doc["cross"]["concerns"].append({"concern": "personal data", "owner": "privacy-data-protection",
                                        "obligation": "Declare the personal data classes the skill collects, logs or "
                                                      "transmits, their purpose, retention, on-device default and "
                                                      "deletion path; feeds XC.SEC.data-rights."})
    ed.note(t, "cross-cutting concern 'personal data' added")

    t = "K-SEC-13"
    _cap(ed, "PLAT.COMM.revocation", "Refund, void and chargeback revocation with clawback of granted entitlements",
         "platform-services", contrib=["server-scaleout-persistence", "anti-cheat-integrity"], tags=t)
    _cap(ed, "PLAT.SVC.credential-storage", "Secure client token storage and system-browser/PKCE login with account linking",
         "platform-services", contrib=["security-runtime"], tags=t)
    _input(ed, "store-notifications", "platform-services", ["server-scaleout-persistence"], "hostile-remote",
           "signature verification, replay window, schema bounds")

    t = "K-SEC-16"
    s = ed.skill("security-engineering")
    s["purpose"] = s["purpose"].replace(", privacy engineering", "")
    s["expertise"] = [x for x in s["expertise"] if x != "privacy engineering"]
    ed.nonresp_add("security-engineering", "Privacy engineering", "privacy-data-protection", tags=t)
    ed.nonresp_add("security-engineering", "Crypto and signed-artifact code", "security-runtime", tags=t)

    t = "K-SEC-17"
    ed.cap_set("BLD.CI.build-distribution", name="Build distribution to QA, playtesters, betas & devkits: external builds "
               "pass dev-surface exclusion, carry per-recipient watermarking and expiring, revocable entitlement",
               add_contrib=["security-engineering", "build-system-toolchains"], tags=t)
    ed.cap_set("BLD.CI.leak-protection", add_contrib=["packaging-release-patching"], tags=t)
