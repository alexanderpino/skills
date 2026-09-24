# Chrome CDP Bridge: x-one Bluebook Access

Full guide, security notes, and scripts live in the **`iplan-developer`** skill:

* Doc: `iplan-developer/references/bluebook.md`
* Scripts: `iplan-developer/scripts/bluebook_sync_sources.py`, `bluebook_run_sync.sh`
  (plus the shared `cdp_bridge.py` helper, also used by the Apigee bridge)

Not duplicated here — I-Plan skills (`iplan-developer`, `principal-architect`,
`confluence-drawio-sync`, `rgn-kibana`) are always installed together as a set via
`npx skills add -g`, so `iplan-developer` is guaranteed to be present alongside this skill.
Read its `references/bluebook.md` for the Chrome CDP bridge used to pull x-one Bluebook
content past corporate SSO — including the security constraints (no `--remote-allow-origins`
wildcard, dedicated single-purpose Chrome profile, cache output kept outside any git
repository).
