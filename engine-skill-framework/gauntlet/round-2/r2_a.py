"""Round-2 revision, part A: the five round-1 findings the adjudicator overturned
(gauntlet/round-1/adjudication.md). Each change implements the adjudicator's 'Required change'."""


def apply(ed):
    # ---- K-GAMEPLAY-15 (overturned): generated-text localization, conversational memory, competence, §7 check
    t = "K-GAMEPLAY-15"
    ed.cap("UI.LOC.generated", "Locale & culturalization of runtime-generated text (generative/templated output: target "
           "locale, plural/gender agreement, culturalization review hooks)", "localization-i18n", "M",
           contrib=["ai-behavior-perception"], tags=t)
    ed.cap_set("GAM.AI.llm", name="LLM-driven NPC dialogue & behavior (via C-AIAGENT; guardrails per XC.SEC.genai; "
               "generated text localized per UI.LOC.generated; conversational memory persisted via C-SAVE with "
               "retention limits)", add_contrib=["persistence-save", "localization-i18n"], tags=t)
    for e in ed.doc["radar"]["entries"]:
        if "GAM.AI.llm" in e.get("capabilities", []):
            e["capabilities"].append("UI.LOC.generated")
            ed.note(t, f"radar '{e['tech']}' += UI.LOC.generated")
    ed.use("ai-behavior-perception", "C-SAVE?", tags=t)
    s = ed.skill("ai-behavior-perception")
    ed.skill_set("ai-behavior-perception", expertise=s["expertise"] + ["ML policy & LLM integration (latency, cost, "
                 "moderation, fallback)"], tags=t)
    c = ed.contract("C-AIAGENT")
    ed.contract_set("C-AIAGENT", summary=c["summary"].rstrip(".") + "; conversational memory persisted through C-SAVE "
                    "with retention and PII limits; generated text routed through localization.", tags=t)
    for cid in ("C-ML", "C-MLGPU", "C-RT", "C-AIAGENT"):
        ed.contract_set(cid, gated=True, tags=t)
    ed.note(t, "check.py: gated contracts may only be consumed optionally in runtime code; M/X/S radar entries need a fallback")
    for e in ed.doc["radar"]["entries"]:
        if e["class"] in ("M", "X", "S") and not e.get("non_goal") and not e.get("fallback"):
            e["fallback"] = "Controller/mouse input only; gaze remains an optional C-DEVICE channel" \
                if "Eye tracking" in e["tech"] else "Feature disabled on unsupported tiers"
            ed.note(t, f"radar '{e['tech']}' fallback added")

    # ---- K-LEGACY-7 (overturned): owner competence and critic check match the first-class CPU path
    t = "K-LEGACY-7"
    ed.skill_set("geometry-pipeline", expertise=["GPU culling", "mesh shaders", "ExecuteIndirect",
                 "CPU culling & instanced batching", "TBDR/mobile GPU submission best practice (Mali/Adreno/Apple)"],
                 tags=t)
    for k in ed.doc["critic"]["critics"]:
        if k["id"] == "K-RENDER":
            k["checks"] = [("no draw-call-centric or DX11-era assumptions on capable tiers; CPU-batched submission on "
                            "TBDR/lite3d follows RND.ARCH.submission-strategy") if x.startswith("no draw-call") else x
                           for x in k["checks"]]
            ed.note(t, "K-RENDER check qualified per tier")

    # ---- K-QUALITY-6 (overturned): conformance flag is now checked; provider changes gated by consumer cases
    t = "K-QUALITY-6"
    c = ed.contract("C-TEST")
    ed.contract_set("C-TEST", summary=c["summary"].rstrip(".") + "; a provider change merges only when the contract's "
                    "conformance suite, including consumer-contributed cases, passes.", tags=t)
    ed.note(t, "check.py: code contract without conformance suite is an error (+selftest mutation)")

    # ---- K-SYSTEMS-13 (overturned): one thermal control loop; frame-rate cap and P/E placement are actuators
    t = "K-SYSTEMS-13"
    ed.cap_set("PLAT.MOB.thermal", name="Mobile thermal/power signal backends (ADPF thermal headroom, performance-hint "
               "sessions, iOS thermal state) feeding CORE.SCALE.governor; no independent control loop",
               add_contrib=["runtime-scalability"], tags=t)
    s = ed.skill("platform-mobile")
    ed.skill_set("platform-mobile", purpose=s["purpose"].replace(
        "thermal/power adaptivity", "thermal/power signal backends for the runtime governor"), tags=t)
    ed.cap_set("CORE.SCALE.actuators", name="Actuator registry (frame-rate cap/refresh selection, dynres, "
               "significance, VFX, animation rate, worker count & P/E placement)",
               add_contrib=["frame-orchestration", "platform-mobile", "job-system-task-graph"], tags=t)

    # ---- K-TOOLS-12 (overturned): contract path from blockout to geometry operations
    t = "K-TOOLS-12"
    ed.use("world-editor-viewport", "C-COOK", tool=True, tags=t)
    c = ed.contract("C-COOK")
    ed.contract_set("C-COOK", summary=c["summary"].rstrip(".") + "; interactive, editor-invoked geometry operations "
                    "(boolean/remesh/UV) for blockout.", tags=t)
    s = ed.skill("world-editor-viewport")
    ed.skill_set("world-editor-viewport", purpose=s["purpose"].rstrip(".") + ", blockout and in-editor modeling "
                 "(geometry kernels via C-COOK).", expertise=s["expertise"] + ["mesh editing / geometry processing"],
                 tags=t)
