# Chrome CDP Bridge: Apigee Developer Portal Access

Full guide, security notes, and scripts live in the **`iplan-developer`** skill:

* Doc: `iplan-developer/references/apigee.md`
* Scripts: `iplan-developer/scripts/apigee_sync_sources.py`, `apigee_run_sync.sh`
  (plus the shared `cdp_bridge.py` helper, also used by the Bluebook bridge)

Not duplicated here — I-Plan skills (`iplan-developer`, `principal-architect`,
`confluence-drawio-sync`, `rgn-kibana`) are always installed together as a set via
`npx skills add -g`, so `iplan-developer` is guaranteed to be present alongside this skill.
Read its `references/apigee.md` for the Chrome CDP bridge used to pull Apigee Developer
Portal content past corporate SSO — including the security constraints, and the important
DTA-vs-PRD two-portal distinction (§0 of that doc) before concluding an API isn't
Apigee-published.
