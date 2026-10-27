"""Round-2 revision, part X: fixes surfaced by the new round-2 check rules once parts A–G were applied
(authoring paths, radar lineage, oracle authors, independence, registry clean-up). Each fix cites the finding
whose rule surfaced it."""


def apply(ed):
    # ---- authoring paths (K-TOOLS-10 rule)
    t = "K-TOOLS-10"
    for cid, name, owner in [
            ("GAM.TOOL.sim-debug", "Field/network simulation visualization & tuning", "systems-simulation"),
            ("GAM.TOOL.script-debugger", "Script & visual-script authoring integration and debugger",
             "scripting-runtime"),
            ("ANM.TOOL.deformers", "Deformer & modular-character setup tools", "deformation-skinning"),
            ("UI.TOOL.a11y-preview", "Accessibility preview (colorblind simulation, caption preview, "
             "screen-reader tree inspector)", "accessibility")]:
        ed.cap(cid, name, owner, tags=t)
        ed.use(owner, "C-EDCMD", "C-EDHOST", tool=True, tags=t)
    ed.use("deformation-skinning", "C-COOK", tool=True, tags=t)
    ed.cap_set("UI.TOOL.preview", add_contrib=["text-fonts"], tags=t)
    ed.cap_set("PHY.TOOL.controller-tuning", add_contrib=["character-movement"], tags=t)
    ed.cap_set("AUD.TOOL.profiler", add_contrib=["audio-dsp-mixing"], tags=t)
    for sid, why in (("spatial-transforms", "Transforms are edited through world-editor-viewport gizmos (C-EDVIEW)."),
                     ("persistence-save", "No designer-authored content; save inspection via visual-debugging-tools."),
                     ("modding-ugc", "Authoring through XC.EXT.mod-editor and XC.EXT.player-creation.")):
        ed.skill_set(sid, authoring=why, tags=t)

    t = "K-RENDER-9"
    ed.use("geometry-pipeline", "C-COOK", tool=True, tags=t)

    # ---- radar entries split so each is owned in the owner's lineage and holds one maturity class
    t = "K-FUTURE-11 K-RENDER-17"
    S = {s["id"]: s for s in ed.doc["skill"]["skills"]}
    caps = {c[0]: c for d in ed.doc["cap"]["domains"] for a in d["areas"] for c in a["caps"]}

    def lineage(sid):
        out = []
        while sid:
            out.append(sid)
            sid = S[sid]["parent"] if sid in S else None
        return out
    new = []
    for e in ed.doc["radar"]["entries"]:
        keep, moved = [], {}
        for cid in e.get("capabilities", []):
            c = caps[cid]
            if e.get("owner") in lineage(c[2]) and c[3] == e["class"]:
                keep.append(cid)
            else:
                owner = e["owner"] if e.get("owner") in lineage(c[2]) else c[2]
                moved.setdefault((owner, c[3]), []).append(cid)
        if moved:
            e["capabilities"] = keep
            for (owner, cls), cl in moved.items():
                ne = dict(e)
                ne.update({"tech": f"{e['tech']} ({', '.join(cl)})", "owner": owner, "class": cls, "capabilities": cl})
                new.append(ne)
            ed.note(t, f"radar '{e['tech']}' split by owner lineage/class: {sorted(moved)}")
    ed.doc["radar"]["entries"] = [e for e in ed.doc["radar"]["entries"]
                                  if e.get("capabilities") or e.get("non_goal")] + new

    # ---- oracle authors for contracts added after the K-TEST-1 assignment
    t = "K-TEST-1"
    consumers = {}
    for s in ed.doc["skill"]["skills"]:
        for d in s["consumes"] + s.get("tool_consumes", []):
            consumers.setdefault(d.split("@")[0].rstrip("?"), []).append(s["id"])
    for c in ed.doc["contract"]["contracts"]:
        if c["layer"] == "P" or c.get("oracle_author"):
            continue
        cands = sorted({x for x in consumers.get(c["id"], []) if x != c["owner"]})
        c["oracle_author"] = cands[0] if cands else "test-architect"
        ed.note(t, f"{c['id']} oracle_author = {c['oracle_author']}")

    # ---- independence pairs must not be co-hosted by workstream (K-ARCH-13 / K-PROD-2 rule)
    t = "K-PROD-2"
    ed.skill_set("architecture-governance", workstream="assurance", tags=t)
    ed.skill_set("reference-games", workstream="quality", tags=t)

    # ---- registry clean-up (K-SEC-1 rule): replication validates replicated state, not transport packets
    t = "K-SEC-1"
    s = ed.skill("replication")
    s["untrusted_inputs"] = [x for x in s["untrusted_inputs"] if x != "packets"]
    ed.note(t, "replication registers replicated-state only")

    # ---- accessibility runtime path (K-GAMEPLAY-1 rule)
    ed.use("online-services-liveops", "C-A11YRT?", tags="K-GAMEPLAY-1")
