#!/usr/bin/env python3
"""The research ledger: sources -> evidence -> claims, as three JSONL files. Stdlib only.

    ledger.py init DIR --query "HR & payroll back-office studio" [--scope "..."]
    ledger.py add-source DIR --id ilo-payroll --title ... --publisher ... --url ... \
              --tier standard-body --type "standard" [--published 2021] [--lane roles]
    ledger.py add-evidence DIR --source ilo-payroll --quote "verbatim words" \
              --locator "section 4.2" --supports "what this quote shows" [--lane roles]
    ledger.py add-claim DIR --claim "..." --kind fact|synthesis|recommendation \
              --evidence E001,E004 [--status supported] [--lane roles]
    ledger.py add-evidence DIR ... --supersedes E010   # correct a wrong entry: the old one stays,
                                                        #   marked superseded, and may not be cited
    ledger.py not-sourceable DIR --claim "..." --reason "searched X, Y; nothing primary"
    ledger.py check DIR          # observations + VERDICT: PASS | CONCERNS | FAIL | NOT ASSESSED
    ledger.py show DIR C003      # the claim with its evidence and sources

Files in DIR: run_manifest.json, sources.jsonl, evidence.jsonl, claims.jsonl.

Research lanes run in parallel subagents; every append takes a lock on DIR/.lock, so ids
(E001…, C001…) are allocated once and never reused. A subagent writes ONLY through this
CLI — never by editing the files — so the shape is enforced at the point of entry.

TIERS (strongest first):
  primary        the thing itself: statute or regulator text, the vendor's own spec of its own
                 product, an employer's own vacancy, a standard's own text
  standard-body  ISO/IEC/IEEE, IIBA, OMG, W3C, OWASP, NIST, AXELOS… summaries and pages
  vendor-docs    product documentation and official guides
  practitioner   books, conference talks, engineering blogs by named practitioners
  unverified     anything not opened, or found only second-hand. May be recorded; may never
                 be the only support of a `supported` claim.

A claim's status:
  supported            backed by >=1 evidence line from a tier above `unverified`
                       (a `synthesis` needs >=2 lines from >=2 sources)
  supported-inference  a reasoned step from supported claims; names them in --evidence
  contested            sources disagree; both sides are in --evidence
  unverified           recorded, not usable as a proposal's only basis
  not-sourceable       searched for and not found — recorded so the gap is visible
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import fcntl
import json
import os
import re
import sys

TIERS = ["primary", "standard-body", "vendor-docs", "practitioner", "unverified"]
KINDS = ["fact", "synthesis", "recommendation"]
STATUSES = ["supported", "supported-inference", "contested", "unverified", "not-sourceable"]
FILES = ("sources.jsonl", "evidence.jsonl", "claims.jsonl")


def _p(d, name):
    return os.path.join(d, name)


def rows(d: str, name: str) -> list[dict]:
    path = _p(d, name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except ValueError as e:
                    raise SystemExit(f"{name}:{n}: not JSON ({e})")
    return out


@contextlib.contextmanager
def locked(d: str):
    with open(_p(d, ".lock"), "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _append(d: str, name: str, row: dict):
    with open(_p(d, name), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _next_id(existing: list[dict], key: str, prefix: str) -> str:
    n = 0
    for r in existing:
        m = re.fullmatch(prefix + r"(\d+)", str(r.get(key, "")))
        if m:
            n = max(n, int(m.group(1)))
    return f"{prefix}{n + 1:03d}"


def _need_init(d: str):
    if not os.path.exists(_p(d, "run_manifest.json")):
        raise SystemExit(f"{d} is not a ledger (no run_manifest.json); run `ledger.py init {d}` first")


def cmd_init(a):
    os.makedirs(a.dir, exist_ok=True)
    mp = _p(a.dir, "run_manifest.json")
    if os.path.exists(mp):
        print(f"ledger already initialised: {mp}")
        return 0
    man = {"schema": "ssb-ledger/1", "query": a.query, "scope": a.scope or "",
           "started": _dt.date.today().isoformat(), "lanes": [], "assumptions": []}
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=2)
        fh.write("\n")
    for f in FILES:
        open(_p(a.dir, f), "a").close()
    print(f"initialised ledger in {a.dir}")
    return 0


def cmd_add_source(a):
    _need_init(a.dir)
    if a.tier not in TIERS:
        raise SystemExit(f"--tier must be one of {', '.join(TIERS)}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", a.id):
        raise SystemExit("--id must be a lowercase slug (a-z, 0-9, -)")
    if a.tier != "unverified" and not a.url:
        raise SystemExit("a source above `unverified` needs --url (or the standard's own identifier as --url)")
    with locked(a.dir):
        if any(s["source_id"] == a.id for s in rows(a.dir, "sources.jsonl")):
            raise SystemExit(f"source {a.id} already exists")
        _append(a.dir, "sources.jsonl", {
            "source_id": a.id, "title": a.title, "publisher": a.publisher, "url": a.url or "",
            "published": a.published or "unspecified", "retrieved": a.retrieved or _dt.date.today().isoformat(),
            "tier": a.tier, "type": a.type, "lane": a.lane or ""})
    print(a.id)
    return 0


def cmd_add_evidence(a):
    _need_init(a.dir)
    if not a.quote.strip() or not a.locator.strip():
        raise SystemExit("--quote and --locator are both required and non-empty")
    with locked(a.dir):
        srcs = {s["source_id"] for s in rows(a.dir, "sources.jsonl")}
        if a.source not in srcs:
            raise SystemExit(f"unknown source {a.source}; add it first")
        ev = rows(a.dir, "evidence.jsonl")
        if a.supersedes and a.supersedes not in {e["evidence_id"] for e in ev}:
            raise SystemExit(f"--supersedes {a.supersedes}: no such evidence")
        eid = _next_id(ev, "evidence_id", "E")
        row = {"evidence_id": eid, "source_id": a.source, "quote": a.quote,
               "locator": a.locator, "supports": a.supports, "lane": a.lane or ""}
        if a.supersedes:
            row["supersedes"] = a.supersedes
        _append(a.dir, "evidence.jsonl", row)
    print(eid)
    return 0


def cmd_add_claim(a, status_override=None):
    _need_init(a.dir)
    status = status_override or a.status
    if a.kind not in KINDS:
        raise SystemExit(f"--kind must be one of {', '.join(KINDS)}")
    if status not in STATUSES:
        raise SystemExit(f"--status must be one of {', '.join(STATUSES)}")
    ids = [x.strip() for x in (a.evidence or "").split(",") if x.strip()]
    with locked(a.dir):
        known_e = {e["evidence_id"] for e in rows(a.dir, "evidence.jsonl")}
        claims = rows(a.dir, "claims.jsonl")
        known_c = {c["claim_id"] for c in claims}
        bad = [i for i in ids if i not in known_e and i not in known_c]
        if bad:
            raise SystemExit(f"unknown evidence/claim ids: {', '.join(bad)}")
        dead = {e.get("supersedes") for e in rows(a.dir, "evidence.jsonl")} & set(ids)
        if dead:
            raise SystemExit(f"superseded evidence may not be cited: {', '.join(sorted(dead))}")
        if status == "not-sourceable" and not (a.reason or "").strip():
            raise SystemExit("a not-sourceable claim needs --reason naming what was searched")
        cid = _next_id(claims, "claim_id", "C")
        _append(a.dir, "claims.jsonl", {"claim_id": cid, "claim": a.claim, "kind": a.kind, "evidence_ids": ids,
                                        "status": status, "reason": a.reason or "", "lane": a.lane or ""})
    print(cid)
    return 0


def check(d: str) -> tuple[str, list[str]]:
    """Return (verdict, observations), ranked FAIL (a broken chain) > NOT ASSESSED (no claims
    to judge) > CONCERNS (unverified claims carried) > PASS."""
    obs: list[str] = []
    if not os.path.exists(_p(d, "run_manifest.json")):
        return "NOT ASSESSED", [f"{d}: no run_manifest.json — no ledger here"]
    src, ev, cl = (rows(d, f) for f in FILES)
    if not cl:
        return "NOT ASSESSED", ["no claims recorded yet"]
    fail, concern = [], []
    sids = {}
    for s in src:
        if s.get("tier") not in TIERS:
            fail.append(f"source {s.get('source_id')}: tier {s.get('tier')!r} invalid")
        if s.get("tier") != "unverified" and not s.get("url"):
            fail.append(f"source {s.get('source_id')}: no url")
        if s.get("source_id") in sids:
            fail.append(f"source {s.get('source_id')}: duplicate id")
        sids[s.get("source_id")] = s
    eids = {}
    for e in ev:
        if e.get("source_id") not in sids:
            fail.append(f"evidence {e.get('evidence_id')}: unknown source {e.get('source_id')}")
        if not str(e.get("quote", "")).strip() or not str(e.get("locator", "")).strip():
            fail.append(f"evidence {e.get('evidence_id')}: empty quote or locator")
        eids[e.get("evidence_id")] = e
    cids = {c.get("claim_id"): c for c in cl}
    superseded = {e.get("supersedes") for e in ev if e.get("supersedes")}
    used_sources = set()
    counts = {s: 0 for s in STATUSES}
    for c in cl:
        st = c.get("status")
        if st not in STATUSES:
            fail.append(f"claim {c.get('claim_id')}: status {st!r} invalid")
            continue
        counts[st] += 1
        refs = c.get("evidence_ids", [])
        for r in refs:
            if r not in eids and r not in cids:
                fail.append(f"claim {c['claim_id']}: unknown reference {r}")
            if r in superseded:
                fail.append(f"claim {c['claim_id']}: cites superseded evidence {r}")
        evs = [eids[r] for r in refs if r in eids]
        for e in evs:
            used_sources.add(e["source_id"])
        strong = [e for e in evs if sids.get(e["source_id"], {}).get("tier") not in (None, "unverified")]
        if st == "supported":
            if not strong:
                fail.append(f"claim {c['claim_id']}: `supported` but no evidence above tier `unverified`")
            if c.get("kind") == "synthesis" and len({e['source_id'] for e in strong}) < 2:
                fail.append(f"claim {c['claim_id']}: a supported synthesis needs evidence from >=2 sources")
        if st == "supported-inference" and not any(r in cids for r in refs):
            fail.append(f"claim {c['claim_id']}: `supported-inference` must name the claims it reasons from")
        if st == "contested" and len(refs) < 2:
            fail.append(f"claim {c['claim_id']}: `contested` needs both sides' evidence")
        if st == "not-sourceable" and not c.get("reason"):
            fail.append(f"claim {c['claim_id']}: `not-sourceable` without a reason")
        if st == "unverified":
            concern.append(f"claim {c['claim_id']} is unverified: {c['claim'][:80]}")
    orphans = sorted(set(sids) - used_sources)
    tiers = {t: sum(1 for s in src if s.get("tier") == t) for t in TIERS}
    obs.append(f"sources={len(src)} evidence={len(ev)} claims={len(cl)}")
    obs.append("tiers: " + " ".join(f"{k}={v}" for k, v in tiers.items()))
    obs.append("claims: " + " ".join(f"{k}={v}" for k, v in counts.items()))
    if orphans:
        obs.append(f"sources cited by no claim: {', '.join(orphans)}")
    obs += fail + concern
    if fail:
        return "FAIL", obs
    if concern:
        return "CONCERNS", obs
    return "PASS", obs


def cmd_check(a):
    verdict, obs = check(a.dir)
    for o in obs:
        print(o)
    print(f"VERDICT: {verdict}")
    return {"PASS": 0, "CONCERNS": 0, "FAIL": 1, "NOT ASSESSED": 3}[verdict]


def cmd_show(a):
    src = {s["source_id"]: s for s in rows(a.dir, "sources.jsonl")}
    ev = {e["evidence_id"]: e for e in rows(a.dir, "evidence.jsonl")}
    cl = {c["claim_id"]: c for c in rows(a.dir, "claims.jsonl")}
    c = cl.get(a.id)
    if not c:
        raise SystemExit(f"no claim {a.id}")
    print(f"{c['claim_id']} [{c['kind']}, {c['status']}] {c['claim']}")
    if c.get("reason"):
        print(f"  reason: {c['reason']}")
    for r in c.get("evidence_ids", []):
        if r in ev:
            e = ev[r]
            s = src.get(e["source_id"], {})
            print(f"  {r}: \"{e['quote']}\" — {e['locator']}")
            print(f"      {s.get('title')} ({s.get('publisher')}, {s.get('tier')}) {s.get('url')}")
        elif r in cl:
            print(f"  {r}: (claim) {cl[r]['claim']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("dir"); p.add_argument("--query", required=True); p.add_argument("--scope")
    p = sub.add_parser("add-source"); p.add_argument("dir")
    for k in ("id", "title", "publisher", "tier", "type"):
        p.add_argument(f"--{k}", required=True)
    for k in ("url", "published", "retrieved", "lane"):
        p.add_argument(f"--{k}")
    p = sub.add_parser("add-evidence"); p.add_argument("dir")
    for k in ("source", "quote", "locator", "supports"):
        p.add_argument(f"--{k}", required=True)
    p.add_argument("--lane"); p.add_argument("--supersedes")
    p = sub.add_parser("add-claim"); p.add_argument("dir")
    p.add_argument("--claim", required=True); p.add_argument("--kind", required=True)
    p.add_argument("--evidence", default=""); p.add_argument("--status", default="supported")
    p.add_argument("--reason"); p.add_argument("--lane")
    p = sub.add_parser("not-sourceable"); p.add_argument("dir")
    p.add_argument("--claim", required=True); p.add_argument("--reason", required=True)
    p.add_argument("--kind", default="fact"); p.add_argument("--evidence", default=""); p.add_argument("--lane")
    p = sub.add_parser("check"); p.add_argument("dir")
    p = sub.add_parser("show"); p.add_argument("dir"); p.add_argument("id")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        return cmd_init(a)
    if a.cmd == "add-source":
        return cmd_add_source(a)
    if a.cmd == "add-evidence":
        return cmd_add_evidence(a)
    if a.cmd == "add-claim":
        return cmd_add_claim(a)
    if a.cmd == "not-sourceable":
        return cmd_add_claim(a, status_override="not-sourceable")
    if a.cmd == "check":
        return cmd_check(a)
    return cmd_show(a)


if __name__ == "__main__":
    sys.exit(main())
