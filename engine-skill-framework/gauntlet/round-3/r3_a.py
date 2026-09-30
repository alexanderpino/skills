"""Round-3 revision, part A: the four round-2 findings the adjudicator overturned (gauntlet/round-2/adjudication.md)."""


def _append(ed, cid, text, tags):
    c = ed.contract(cid)
    ed.contract_set(cid, summary=c["summary"].rstrip(".") + "; " + text, tags=tags)


def apply(ed):
    t = "K-GAMEPLAY-12"
    ed.use("ai-behavior-perception", "C-REP?", tags=t)
    _append(ed, "C-REP", "per-faction visibility registers as a relevancy filter through the relevancy hooks "
            "(basis of XC.SEC.info-hiding).", t)
    _append(ed, "C-AI", "per-faction visibility and explored-state queries; the visibility field is published to fog "
            "rendering and maps through a declared C-FLOW channel.", t)
    _append(ed, "C-UI", "marker-source interface for the map service (implemented by gameplay marker registries).", t)
    ed.use("gameplay-systems-toolkit", "C-UI?", tags=t)
    _append(ed, "C-ABILITY", "marker registry (POIs) published to C-UI marker sources.", t)

    t = "K-LEGACY-7 K-TOOLS-8"
    ed.note(t, "check.py: tool-side vocabulary broadened (cook/bake/editor/SDK tooling/modder editor/authoring tool) with "
               "an explicit runtime-protocol exemption list and a selftest")

    t = "K-PLATFORM-6"
    ed.cap_set("RES.IO.backends", name="Async IO backends (io_uring, IOCP, DirectStorage; console variants via "
               "PLAT.CON.confidential-slots)", tags=t)
    ed.cap_set("PLAT.XR.runtime-backends", name="XR runtime backends: OpenXR, visionOS Compositor Services (console XR "
               "SDK slot in PLAT.CON.confidential-slots)", rm_contrib=["platform-console"], tags=t)
    ed.cap_set("PLAT.CON.confidential-slots", name="Confidential implementations of registered slots (IO/decompression "
               "units, audio endpoints, save storage, crash upload, system keyboard, entitlement SDK, console XR SDK) "
               "behind public interfaces owned by domain skills", add_contrib=["xr-runtime"], tags=t)
    ed.note(t, "check.py: capabilities naming confidential/console API or SDK territory must be owned by an NDA skill")

    t = "K-TOOLS-8"
    ed.cap("XC.EXT.runtime-graphs", "Runtime compilation of UGC-authored graphs in client targets (restricted node set, "
           "validation, shader/VM compile under RND.SHADER.untrusted limits; C-GRAPH node/pin model as shared schema)",
           "modding-ugc", contrib=["shader-system", "graph-editor-framework", "scripting-runtime"],
           profiles=["ugc"], tags=t)
    _append(ed, "C-EDIT", "runtime graph authoring and compilation (XC.EXT.runtime-graphs; node/pin schema shared "
            "with C-GRAPH).", t)
    ed.use("modding-ugc", "C-SHADER?", tags=t)
