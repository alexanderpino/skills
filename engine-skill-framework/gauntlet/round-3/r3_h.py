"""Round-3 revision, part H: adjudication overturns (K-GAMEPLAY-7, K-TEST-6; K-ARCH-3 is a docs wording fix)."""


def apply(ed):
    t = "K-GAMEPLAY-7"
    c = ed.contract("C-LOC")
    ed.contract_set("C-LOC", summary="String IDs, formatting, locale switching; term references (per-locale grammatical "
                    "attributes of substituted terms such as items, characters and places: gender, animacy, case forms, "
                    "articles, particles) resolved for agreement in messages (UI.LOC.terms).", tags=t)
    t = "K-TEST-6"
    c = ed.contract("C-ORCH")
    s = c["summary"].replace("access classes per skill (public | nda:<holder>)",
                             "access classes per skill and per path (public | nda:<holder> | sealed:oracle)")
    s = s.replace("read-only (oracle-ro) for implementers;",
                  "read-only (oracle-ro) for implementers; sealed holdouts, gate-time seeds and expected outputs live under "
                  "access class sealed:oracle, readable only by oracle_author agents and CI runners and never by an "
                  "implementer of that contract (BLD.CI.sealed-suites, QA.AGENT.holdout);")
    ed.contract_set("C-ORCH", summary=s, tags=t)
